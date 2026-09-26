"""E20-full GPU driver: one process per GPU (8 per job), sharded by question. Derived from the pilot's frozen src/e20_exec.py
(P2_R8_E20P_20260921T224653Z; diff in CODE_DIFF.patch). The pilot functions log, sync, FakeModel, load_model, free, special_ids, e20_helper and
e20_receiver are copied VERBATIM (asserted at start-up against the pilot file), and the pilot modules e20_prompts, e20_extract and
e20_exec_common are imported from the pilot directory unmodified: prompts, extraction, normalization, scores and decoding are the pilot's.
Pre-authorized changes only: SQuAD and the Llama-3.1-8B receiver (no Qwen3); items from inputs/FULL_<split>.jsonl; fit questions get helper
messages and receiver-with-message outputs too (E1); a new preflight; a per-job plan so a later job continues the remainder by question id.
Phases: fitcal = fit + cal (job 1); devtest = dev, and test only if CERT_E20F.json (hash verified) deployed a threshold (job 2).
Rank 0 first reruns the first 16 pilot SQuAD questions (PILOT_squad.jsonl) with this code and requires bitwise equality with the pilot's stored
rows (results/E20P_jobA_rows.jsonl): helper-message token IDs, receiver-only and receiver-with-message token IDs, s1/s2/s3 of both; then writes
PLAN_j<tag>.json (PASS + per-rank question ids of every question without a stored receiver row). Other ranks wait for the plan; no production
on FAIL. Per rank: helper -> messages for its questions -> freed; Llama -> receiver-only + receiver-with-message -> freed. Rows appended with
fsync; no new question is started after the deadline (job start + 48 min). No gold is read anywhere.
usage: e20f_exec.py --phase {fitcal,devtest} --job-tag TAG --rank R --nranks N --job-start EPOCH --deadline-epoch EPOCH
                    [--dry-run --dry-limit K]"""
import os, sys, json, time, math, argparse, traceback, gc, hashlib, types, statistics, ast
sys.dont_write_bytecode = True
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import e20f_common as FC                             # inserts the pilot src directory into sys.path
from e20_exec_common import *                        # pilot module (MODELS, CFG, load_tokenizer, utc, jl, save, append, PILOT, ...)
import e20_prompts as PR                             # pilot module
from e20_extract import extract, scores, INVALID     # pilot module

ap = argparse.ArgumentParser()
ap.add_argument('--phase', required=True, choices=['fitcal', 'devtest'])
ap.add_argument('--job-tag', required=True)
ap.add_argument('--rank', type=int, required=True)
ap.add_argument('--nranks', type=int, required=True)
ap.add_argument('--job-start', type=float, required=True)
ap.add_argument('--deadline-epoch', type=float, required=True)
ap.add_argument('--dry-run', action='store_true')
ap.add_argument('--dry-limit', type=int, default=0)
a = ap.parse_args()
TAG = a.job_tag
OUT = FC.base(a.dry_run) / 'records' / a.phase; OUT.mkdir(parents=True, exist_ok=True)
VERBATIM = ['log', 'sync', 'FakeModel', 'load_model', 'free', 'special_ids', 'e20_helper', 'e20_receiver']


def _segments(path):
    t = Path(path).read_text(); out = {}
    for n in ast.parse(t).body:
        if isinstance(n, (ast.FunctionDef, ast.ClassDef)) and n.name in VERBATIM:
            s = min([d.lineno for d in n.decorator_list] + [n.lineno]); out[n.name] = '\n'.join(t.split('\n')[s - 1:n.end_lineno])
    return out


_mine, _pilot = _segments(__file__), _segments(FC.PILOT_DIR / 'src/e20_exec.py')
assert set(_mine) == set(VERBATIM) and all(_mine[k] == _pilot[k] for k in VERBATIM), 'verbatim pilot functions differ'
if not a.dry_run:
    FC.check_freezes()
SPLITS = FC.phase_splits(a.phase, a.dry_run)
ITEMS = [(sp, it) for sp in SPLITS for it in FC.split_items(sp)]
assert all(len([1 for s, _ in ITEMS if s == sp]) == FC.N_SPLIT[sp] for sp in SPLITS)

import torch
from transformers import AutoModelForCausalLM, AutoConfig, GenerationConfig
torch.manual_seed(0); torch.cuda.manual_seed_all(0)
torch.backends.cuda.matmul.allow_tf32 = False; torch.backends.cudnn.allow_tf32 = False
torch.set_num_threads(1)
if not a.dry_run:
    assert torch.cuda.is_available() and torch.cuda.device_count() == 1, torch.cuda.device_count()
DEV = 'cpu' if a.dry_run else 'cuda:0'

# ---- frozen paper module for the loader (as in the pilot)
sys.path.insert(0, str(P10))
import protocol_min
import legacy_methods as lm
from protocol_min import apply_generation_config
sys.path.remove(str(P10))
assert lm.BACKGROUND_PROMPT == PR.BACKGROUND_PROMPT


def log(*x): print(f'[{utc()}] rank={a.rank}', *x, flush=True)


def sync():
    if not a.dry_run: torch.cuda.synchronize()


class FakeModel:
    """--dry-run only: no weights. Returns fixed strings and random logits whose argmax is the emitted token."""
    VAR = ['Paris', 'Answer: the Eiffel Tower.\nIt is in Paris.', '**1889**', '  \n', 'The answer is Gustave Eiffel', 'Ünïcödé naïve café.']

    def __init__(self, role, tok):
        self.config = AutoConfig.from_pretrained(MODELS[role]['path'], local_files_only=True)
        self.generation_config = GenerationConfig.from_pretrained(MODELS[role]['path'], local_files_only=True)
        self.device = torch.device('cpu'); self.tok = tok; self.role = role; self.calls = 0

    def generate(self, inputs=None, input_ids=None, max_new_tokens=64, return_dict_in_generate=False, output_logits=False, **kw):
        x = input_ids if input_ids is not None else inputs
        self.calls += 1
        s = 'Background: dry-run helper message.' if self.role == 'helper' else self.VAR[self.calls % len(self.VAR)]
        eos = self.generation_config.eos_token_id; eos = eos[0] if isinstance(eos, list) else eos
        ids = (self.tok(s, add_special_tokens=False)['input_ids'] + [eos])[:max_new_tokens]
        seq = torch.cat([x.cpu(), torch.tensor([ids], dtype=x.dtype)], 1)
        if not return_dict_in_generate: return seq
        g = torch.Generator().manual_seed(self.calls); lg = []
        for t in ids:
            l = torch.randn(1, self.config.vocab_size, generator=g) * 3; l[0, t] = l.max() + 2.0; lg.append(l.float())
        return types.SimpleNamespace(sequences=seq, logits=tuple(lg))


def load_model(role):
    t = time.perf_counter(); tok = load_tokenizer(role)
    if a.dry_run:
        m = FakeModel(role, tok)
    else:
        m = AutoModelForCausalLM.from_pretrained(MODELS[role]['path'], local_files_only=True, torch_dtype=torch.bfloat16,
                                                 attn_implementation='sdpa').to(DEV).eval().requires_grad_(False)
    apply_generation_config(m, {'do_sample': False, 'max_new_tokens': 64})          # frozen loader (runtime.Runner / X3)
    if role == 'qwen3' and not a.dry_run:
        assert m.generation_config.to_dict() == CFG['receiver_generation_config']
    sync(); dt = time.perf_counter() - t
    log('loaded', role, f'{dt:.1f}s')
    return m, tok, dt


def free(*ms):
    for m in ms: del m
    gc.collect()
    if not a.dry_run: torch.cuda.empty_cache()


def special_ids(tok, model):
    s = set(tok.all_special_ids) | {i for i, t in tok.added_tokens_decoder.items() if t.special}
    e = model.generation_config.eos_token_id
    s |= set(e if isinstance(e, list) else [e])
    return s


@torch.inference_mode()
def e20_helper(model, tok, ds, item):
    """Frozen T2THelperBundle.run with the E20 helper body (options removed; passage block for passage datasets)."""
    sync(); t = time.perf_counter()
    inp = tok.apply_chat_template(PR.helper_messages(ds, item), tokenize=True, add_generation_prompt=True, return_tensors='pt',
                                  enable_thinking=False).to(DEV)
    out = model.generate(inp, max_new_tokens=HELPER_MAX_NEW, do_sample=False)
    gen = out[:, inp.shape[-1]:]
    text = tok.batch_decode(gen, skip_special_tokens=True, clean_up_tokenization_spaces=False)[0]
    sync()
    return dict(dataset=ds, id=item['id'], helper_message=text, helper_message_sha256=hashlib.sha256(text.encode()).hexdigest(),
                helper_generated_token_ids=gen[0].cpu().tolist(), helper_input_tokens=int(inp.shape[1]), wall_ms=(time.perf_counter() - t) * 1000)


@torch.inference_mode()
def e20_receiver(model, tok, messages, SPECIAL):
    sync(); t = time.perf_counter()
    rendered = tok.apply_chat_template(messages, tokenize=False, add_generation_prompt=True, enable_thinking=False)
    tn = tok(rendered, return_tensors='pt', add_special_tokens=False)
    tn = {k: v.to(DEV) for k, v in tn.items()}
    gcfg = model.generation_config
    out = model.generate(input_ids=tn['input_ids'], attention_mask=tn['attention_mask'], do_sample=False, max_new_tokens=RECEIVER_MAX_NEW,
                         use_cache=True, pad_token_id=gcfg.pad_token_id if gcfg.pad_token_id is not None else tok.pad_token_id,
                         eos_token_id=gcfg.eos_token_id if gcfg.eos_token_id is not None else tok.eos_token_id,
                         return_dict_in_generate=True, output_logits=True)
    n0 = tn['input_ids'].shape[1]
    gen = out.sequences[0, n0:]; ids = gen.cpu().tolist()
    assert len(out.logits) == len(ids), (len(out.logits), len(ids))
    L = torch.stack([x[0] for x in out.logits], 0).to(torch.float64)                 # raw logits (T, V) in float64
    lse = torch.logsumexp(L, -1)
    idx = torch.tensor(ids, device=L.device)
    logp = (L.gather(1, idx[:, None])[:, 0] - lse)
    am = L.argmax(-1)
    P = torch.exp(L - lse[:, None]); P.scatter_(1, am[:, None], 0.0)
    nonmax = P.sum(-1)                                                                 # 1 - max p = total non-argmax probability
    logp, nonmax, am = logp.cpu().tolist(), nonmax.cpu().tolist(), am.cpu().tolist()
    text = tok.decode(ids, skip_special_tokens=True, clean_up_tokenization_spaces=False)
    texts = [tok.decode([i], skip_special_tokens=False, clean_up_tokenization_spaces=False) for i in ids]
    isp = [i in SPECIAL for i in ids]
    ex = extract(text); sc = scores(texts, isp, logp, nonmax)
    sync()
    iid = tn['input_ids'][0].cpu().tolist()
    return dict(raw=text, extracted=ex['extracted'], answer=ex['answer'], invalid=ex['answer'] == INVALID, words=ex['words'], **sc,
                generated_token_ids=ids, token_texts=texts, is_special=isp, logp=logp, nonmax=nonmax,
                argmax_ne_chosen=sum(int(x != y) for x, y in zip(am, ids)), n_gen_tokens=len(ids), input_tokens=n0,
                bos_count=iid.count(tok.bos_token_id) if tok.bos_token_id is not None else 0,
                input_ids_sha256=hashlib.sha256(json.dumps(iid).encode()).hexdigest(), wall_ms=(time.perf_counter() - t) * 1000)


# ------------------------------------------------------------------------------------------------ E20F preflight, plan, production
PILOT_ROWS = FC.PILOT_DIR / 'results/E20P_jobA_rows.jsonl'


def preflight():
    """First 16 pilot SQuAD questions through this code; bitwise vs the pilot's stored rows."""
    stored = {r['id']: r for r in jl(PILOT_ROWS) if r['dataset'] == 'squad'}
    items = jl(PILOT('squad'))[:16]
    pf = dict(job=TAG, phase=a.phase, utc_start=utc(), n=len(items), pilot_rows=str(PILOT_ROWS), pilot_rows_sha256=sha(PILOT_ROWS), rows=[])
    h, htok, lh = load_model('helper'); pf['first_output_utc'] = utc()
    msgs = {it['id']: e20_helper(h, htok, 'squad', it) for it in items}
    free(h); del h
    m, tok, ll = load_model('llama'); SPECIAL = special_ids(tok, m)
    for it in items:
        P = stored[it['id']]; hm = msgs[it['id']]
        R = e20_receiver(m, tok, PR.receiver_only_messages('squad', it), SPECIAL)
        T = e20_receiver(m, tok, PR.receiver_with_message_messages('squad', it, hm['helper_message']), SPECIAL)
        c = dict(id=it['id'], helper_ids=hm['helper_generated_token_ids'] == P['helper']['helper_generated_token_ids'],
                 helper_text=hm['helper_message'] == P['helper']['helper_message'],
                 R_ids=R['generated_token_ids'] == P['llama']['R']['generated_token_ids'],
                 T_ids=T['generated_token_ids'] == P['llama']['T']['generated_token_ids'],
                 s123=all(X[s] == P['llama'][k][s] for X, k in [(R, 'R'), (T, 'T')] for s in ('s1', 's2', 's3')),
                 logp_nonmax=all(X[f] == P['llama'][k][f] for X, k in [(R, 'R'), (T, 'T')] for f in ('logp', 'nonmax')),
                 answers=R['answer'] == P['llama']['R']['answer'] and T['answer'] == P['llama']['T']['answer'],
                 wall_ms=dict(helper=hm['wall_ms'], R=R['wall_ms'], T=T['wall_ms']))
        c['all'] = c['helper_ids'] and c['R_ids'] and c['T_ids'] and c['s123']
        pf['rows'].append(c)
    free(m); del m
    for k in ['helper_ids', 'helper_text', 'R_ids', 'T_ids', 's123', 'logp_nonmax', 'answers', 'all']:
        pf[f'n_{k}'] = sum(c[k] for c in pf['rows'])
    pf.update(load_seconds=dict(helper=lh, llama=ll), PASS=len(pf['rows']) == 16 and pf['n_all'] == 16, utc_end=utc())
    log('PREFLIGHT', {k: pf[f'n_{k}'] for k in ['helper_ids', 'R_ids', 'T_ids', 's123', 'all']}, 'PASS', pf['PASS'])
    return pf


def ok_rows(pat):
    d = {}
    for f in sorted(OUT.glob(pat)):
        for r in jl(f):
            if r.get('runtime_error') is None: d.setdefault(r['id'], r)
    return d


def over(): return time.time() > a.deadline_epoch


t0 = time.time()
PLANF = OUT / f'PLAN_j{TAG}.json'
if a.rank == 0:
    try:
        pf = preflight()
    except Exception:
        pf = dict(PASS=False, reason='exception in preflight', traceback=traceback.format_exc()); log(pf['traceback'])
    save(OUT / f'PREFLIGHT_j{TAG}.json', pf)
    plan = dict(job=TAG, phase=a.phase, splits=SPLITS, dry_run=a.dry_run, preflight_PASS=pf.get('PASS'), PASS=bool(pf.get('PASS')) or a.dry_run,
                utc=utc())
    if plan['PASS']:
        hdone, rdone = set(ok_rows('helper_*.jsonl')), set(ok_rows('recv_llama_*.jsonl'))
        todo = [x for x in ITEMS if x[1]['id'] not in rdone]
        plan.update(n_items=len(ITEMS), n_done_before=len(ITEMS) - len(todo), n_todo=len(todo),
                    assign={str(r): [it['id'] for _, it in todo[r::a.nranks]] for r in range(a.nranks)},
                    helper_needed=sorted(it['id'] for _, it in todo if it['id'] not in hdone))
    save(PLANF, plan)
else:
    while not PLANF.exists():
        if over(): log('no plan before the deadline'); sys.exit(6)
        time.sleep(5)
    time.sleep(1); plan = json.loads(PLANF.read_text())
if not plan['PASS']:
    log('preflight not PASS; no production on this rank'); sys.exit(5)

BYID = {it['id']: (sp, it) for sp, it in ITEMS}
mine = [BYID[i] for i in plan['assign'][str(a.rank)]]
if a.dry_run and a.dry_limit: mine = mine[:a.dry_limit]
need_h = set(plan['helper_needed'])
status = dict(rank=a.rank, job=TAG, phase=a.phase, n_items=len(mine), n_helper_needed=sum(it['id'] in need_h for _, it in mine),
              utc_start=utc(), stages={}, errors=[], stopped_early=False)
log('shard', len(mine), 'items;', status['n_helper_needed'], 'need helper messages')

# (iii) helper
hitems = [x for x in mine if x[1]['id'] in need_h]
if hitems:
    h, htok, lt = load_model('helper'); t = time.time(); done = 0
    with open(OUT / f'helper_j{TAG}_rank{a.rank}.jsonl', 'a') as fh:
        for sp, it in hitems:
            if over(): status['stopped_early'] = True; break
            try:
                append(fh, dict(**e20_helper(h, htok, 'squad', it), split=sp, utc=utc(), runtime_error=None)); done += 1
            except Exception:
                status['errors'].append(dict(stage='helper', id=it['id'], tb=traceback.format_exc()[-1500:]))
                append(fh, dict(dataset='squad', id=it['id'], split=sp, utc=utc(), runtime_error=traceback.format_exc()[-1500:]))
    status['stages']['helper'] = dict(load_s=lt, done=done, seconds=time.time() - t); free(h); del h
    log('helper done', done)
MSG = ok_rows('helper_*.jsonl')

# (v) Llama-3.1-8B receiver
if not over():
    m, tok, lt = load_model('llama'); SPECIAL = special_ids(tok, m); t = time.time(); done = 0
    with open(OUT / f'recv_llama_j{TAG}_rank{a.rank}.jsonl', 'a') as fh:
        for sp, it in mine:
            if over(): status['stopped_early'] = True; break
            hm = MSG.get(it['id'])
            rec = dict(dataset='squad', id=it['id'], split=sp, receiver='llama', utc=utc(), runtime_error=None,
                       helper_message_sha256=hm.get('helper_message_sha256') if hm else None)
            try:
                rec['R'] = e20_receiver(m, tok, PR.receiver_only_messages('squad', it), SPECIAL)
                rec['T'] = e20_receiver(m, tok, PR.receiver_with_message_messages('squad', it, hm['helper_message']), SPECIAL)
                done += 1
            except Exception:
                rec['runtime_error'] = traceback.format_exc()[-1500:]
                status['errors'].append(dict(stage='llama', id=it['id'], tb=rec['runtime_error']))
            append(fh, rec)
    status['stages']['llama'] = dict(load_s=lt, done=done, seconds=time.time() - t, special_ids=sorted(SPECIAL)); free(m); del m
    log('llama done', done)
else:
    status['stopped_early'] = True
status.update(utc_end=utc(), wall_s=time.time() - t0,
              complete=status['stages'].get('llama', {}).get('done') == len(mine) and not status['errors'])
save(OUT / f'status_j{TAG}_rank{a.rank}.json', status)
log('END complete', status['complete'], 'errors', len(status['errors']))
