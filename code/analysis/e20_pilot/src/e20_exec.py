"""E20-pilot GPU driver: one process per GPU (8 per job), sharded by question. No gold is read anywhere (the pilot files carry no answers).

Rank 0, before anyone generates E20 outputs (GATE):
  (i)  preflight: the reused frozen Text pipeline (helper Qwen2.5-7B + receiver Qwen3-8B on one GPU, 64-token frozen paths, the E10 preflight
       code) must reproduce 16 stored large-pair OBQA fit rows bitwise on receiver-only and Text; the reused X3 Llama path (add_special_tokens
       =False, saved helper message) must reproduce 16 stored X3 OBQA rows bitwise on R and T. Decode tokens/s measured. Job B skips (i) if
       records/jobA/PREFLIGHT.json says PASS.
  (ii) smoke: first 8 pilot questions of each dataset, receiver-only E20 path, Qwen3 and Llama: a dataset is dropped if, for either receiver,
       > 2/8 outputs are INVALID or the median answer length (words of the normalized answer; INVALID = 0) is > 10.
  Projection: elapsed + measured load times + worst case (256 helper tokens, 32 receiver tokens per generation) at the measured rates for this
  rank's shard; if > 45 min, every rank uses the first 300 pilot questions of each dataset (recorded in GATE.json -> DEVIATIONS.md).
  Writes PREFLIGHT.json, smoke_rank0.jsonl, GATE.json. Other ranks wait for GATE.json and stop unless it says PASS.
All ranks: (iii) helper writes all messages of the shard, freed; (iv) Qwen3-8B receiver-only + receiver-with-message, freed; (v) Llama same.
Receiver E20 path: rendered chat template (enable_thinking=False) -> tokenizer(add_special_tokens=False) -> greedy generate (32 new tokens,
the frozen generate_receiver arguments) with output_logits=True; per position float64 chosen-token log-prob and 1 - max p (total non-argmax
probability) from the raw logits; extraction and s1/s2/s3 by e20_extract. Rows appended with fsync as they are produced.
usage: e20_exec.py --job {A,B} --rank R --nranks N --job-start EPOCH --deadline-epoch EPOCH [--dry-run --dry-limit K]
"""
import os, sys, json, time, math, argparse, traceback, gc, hashlib, types, statistics
sys.dont_write_bytecode = True
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from e20_exec_common import *
import e20_prompts as PR
from e20_extract import extract, scores, INVALID

ap = argparse.ArgumentParser()
ap.add_argument('--job', required=True, choices=['A', 'B'])
ap.add_argument('--rank', type=int, required=True)
ap.add_argument('--nranks', type=int, required=True)
ap.add_argument('--job-start', type=float, required=True)
ap.add_argument('--deadline-epoch', type=float, required=True)
ap.add_argument('--dry-run', action='store_true')
ap.add_argument('--dry-limit', type=int, default=0)
a = ap.parse_args()
DS = JOBS[a.job]
BASE = (STAGE / 'notes/dryrun') if a.dry_run else (STAGE / 'records')
OUT = BASE / f'job{a.job}'; OUT.mkdir(parents=True, exist_ok=True)
PROJ_LIMIT_S, N_FULL, N_REDUCED, N_SMOKE = 45 * 60, 400, 300, 8


def log(*x): print(f'[{utc()}] rank={a.rank}', *x, flush=True)


if not a.dry_run:   # code/input freeze written with PREREG_E20P.md
    fz = json.loads((STAGE / 'notes/CODE_FREEZE.json').read_text())
    bad = [f for f, h in fz['files'].items() if sha(STAGE / f) != h]
    assert not bad, f'CODE_FREEZE mismatch: {bad}'

import torch
from transformers import AutoModelForCausalLM, AutoConfig, GenerationConfig
torch.manual_seed(0); torch.cuda.manual_seed_all(0)
torch.backends.cuda.matmul.allow_tf32 = False; torch.backends.cudnn.allow_tf32 = False
torch.set_num_threads(1)
if not a.dry_run:
    assert torch.cuda.is_available() and torch.cuda.device_count() == 1, torch.cuda.device_count()
DEV = 'cpu' if a.dry_run else 'cuda:0'

# ---- frozen paper modules (preflight paths only)
sys.path.insert(0, str(P10))
import protocol_min
import legacy_methods as lm
ORIG_FMT = protocol_min.format_openbook            # X3 used this for OBQA (captured before the adapter, as in run_x3.py)
import arc_runtime_adapter  # noqa: F401            # the large-pair runtime (and E10's preflight) loaded this adapter
ADAPT_FMT = protocol_min.format_openbook
from protocol_min import apply_generation_config, generate_receiver
sys.path.remove(str(P10))
assert ADAPT_FMT is not ORIG_FMT and lm.BACKGROUND_PROMPT == PR.BACKGROUND_PROMPT
lm.cuda_wall_stage = lambda fn, device: (fn(), 0., 0.)
lm.wall_stage = lambda fn: (fn(), 0.)
lm.extract_prediction = lambda text: None


def use_fmt(f): protocol_min.format_openbook = f; lm.format_openbook = f


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


# ------------------------------------------------------------------------------------------------ E20 paths
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


# ------------------------------------------------------------------------------------------------ preflight (frozen paths)
def preflight_obqa(h, htok, q, qtok):
    """E10 phase_preflight, unchanged in substance: 16 stored P2_10 large OBQA fit rows, receiver-only and Text, bitwise."""
    use_fmt(ADAPT_FMT)
    lm.HELPER_CONFIG = h.config; lm.RECEIVER_CONFIG = q.config
    th = lm.T2THelperBundle(h, htok); tr = lm.T2TReceiverBundle(q, qtok)
    fit = json.loads((BOUND / 'splits/obqa_fit_representatives.json').read_text())
    qs = {r['id']: r for r in jl(BOUND / 'inputs/obqa_train_queries.jsonl')}
    rows = jl(P10 / 'results/large/obqa/train_historical_rtc.jsonl')
    rep, rate = {}, dict(helper_tokens=0, helper_s=0., receiver_tokens=0, receiver_s=0.)
    for act, native in [('R', 'receiver_only'), ('T', 'text')]:
        by = {r['id']: {'raw_answer': r['raw_answer'], 'generated_token_ids': r['generated_token_ids']}
              for r in rows if r['action'] == native}       # gold_answer deliberately not projected
        ids = [i for i in fit if i in by][:16]
        det = []
        for i in ids:
            row = {k: (list(qs[i][k]) if isinstance(qs[i][k], list) else qs[i][k]) for k in ['question_stem', 'choice_labels', 'choice_text']}
            with torch.inference_mode():
                if act == 'R':
                    sync(); t = time.perf_counter()
                    _, _, tn = protocol_min.receiver_prompt_tensors(qtok, row, q.device)
                    text, g = generate_receiver(q, qtok, tn); gids = g.cpu().tolist()
                    sync(); rate['receiver_s'] += time.perf_counter() - t; rate['receiver_tokens'] += len(gids)
                else:
                    sync(); t = time.perf_counter(); msg = th.run(row); sync()
                    rate['helper_s'] += time.perf_counter() - t; rate['helper_tokens'] += len(msg['helper_generated_token_ids'])
                    res = tr.consume(row, msg['helper_body'], msg['helper_message']); text, gids = res['generated_text'], res['generated_token_ids']
            ok = text == by[i]['raw_answer'] and list(gids) == list(by[i]['generated_token_ids'])
            det.append(dict(id=i, match=ok, got=text, expected=by[i]['raw_answer'], token_ids_match=list(gids) == list(by[i]['generated_token_ids'])))
        rep[act] = dict(n=len(ids), mismatches=sum(not d['match'] for d in det), rows=det)
        log('PREFLIGHT OBQA', act, rep[act]['n'], 'mismatches', rep[act]['mismatches'])
    return dict(source='P2_10 results/large/obqa/train_historical_rtc.jsonl (first 16 fit representatives present)', per_action=rep,
                n=sum(v['n'] for v in rep.values()), matched=sum(v['n'] - v['mismatches'] for v in rep.values()),
                PASS=all(v['n'] == 16 and v['mismatches'] == 0 for v in rep.values())), rate


def preflight_x3(m, tok):
    """X3 run_x3.py R and T paths for Llama-3.1-8B (OBQA uses the pre-adapter format_openbook, R tokenized with add_special_tokens=False)."""
    use_fmt(ORIG_FMT)
    tr = lm.T2TReceiverBundle(m, tok)
    inp = [r for r in jl(X3 / 'records/work/run/chain_00.jsonl') if r['dataset'] == 'obqa'][:16]
    exp = {r['id']: r for r in jl(X3 / 'results/runs/chain_00.jsonl') if r['dataset'] == 'obqa'}
    det, rate = [], dict(receiver_tokens=0, receiver_s=0.)
    for r in inp:
        e = exp[r['id']]; qq = r['query']
        assert e['runtime_error'] is None and hashlib.sha256(r['helper_message'].encode()).hexdigest() == r['helper_message_sha256']
        with torch.inference_mode():
            sync(); t = time.perf_counter()
            prompt = protocol_min.format_openbook(qq, use_template=True)
            rendered = tok.apply_chat_template([{"role": "user", "content": prompt}], tokenize=False, add_generation_prompt=True, enable_thinking=False)
            tn = tok(rendered, return_tensors='pt', add_special_tokens=False); tn = {k: v.to(DEV) for k, v in tn.items()}
            textR, g = generate_receiver(m, tok, tn); gR = g.cpu().tolist()
            sync(); rate['receiver_s'] += time.perf_counter() - t; rate['receiver_tokens'] += len(gR)
            res = tr.consume(qq, protocol_min.format_openbook(qq, use_template=False), r['helper_message'])
        okR = textR == e['R']['raw'] and gR == e['R']['generated_token_ids']
        okT = res['generated_text'] == e['T']['raw'] and res['generated_token_ids'] == e['T']['generated_token_ids']
        det.append(dict(id=r['id'], R_match=okR, T_match=okT, R_got=textR, R_expected=e['R']['raw'], T_got=res['generated_text'], T_expected=e['T']['raw']))
    n = len(det); mR = sum(not d['R_match'] for d in det); mT = sum(not d['T_match'] for d in det)
    log('PREFLIGHT X3 n', n, 'R mismatches', mR, 'T mismatches', mT)
    return dict(source='P2_R6_X3 records/work/run/chain_00.jsonl -> results/runs/chain_00.jsonl (first 16 OBQA rows)', n=n,
                R_mismatches=mR, T_mismatches=mT, rows_all_equal=n - sum(not (d['R_match'] and d['T_match']) for d in det), rows=det,
                PASS=n == 16 and mR == 0 and mT == 0), rate


def smoke(m, tok, recv, pilot, fh):
    SPECIAL = special_ids(tok, m); res = {}; toks, secs = 0, 0.
    for ds in DS:
        outs = []
        for it in pilot[ds][:N_SMOKE]:
            r = e20_receiver(m, tok, PR.receiver_only_messages(ds, it), SPECIAL)
            toks += r['n_gen_tokens']; secs += r['wall_ms'] / 1000
            append(fh, dict(stage='smoke', dataset=ds, id=it['id'], receiver=recv, utc=utc(), R=r)); outs.append(r)
        inv = sum(o['invalid'] for o in outs); med = statistics.median(o['words'] for o in outs)
        res[ds] = dict(n=len(outs), invalid=inv, median_words=med, fail=inv > 2 or med > 10, answers=[o['answer'] for o in outs])
        log('SMOKE', recv, ds, 'INVALID', inv, '/', len(outs), 'median words', med)
    return res, (toks / secs if secs else None)


def gate_rank0(pilot):
    g = dict(job=a.job, dry_run=a.dry_run, utc_start=utc(), datasets=DS)
    pf_path = OUT / 'PREFLIGHT.json'
    pa = BASE / 'jobA/PREFLIGHT.json'
    skip = a.job == 'B' and pa.exists() and json.loads(pa.read_text()).get('PASS') is True
    if a.job == 'B' and pa.exists() and json.loads(pa.read_text()).get('PASS') is False:
        g.update(PASS=False, reason='job A preflight FAILED (records/jobA/PREFLIGHT.json); job B stops'); save(OUT / 'GATE.json', g); return g
    fh = open(OUT / 'smoke_rank0.jsonl', 'a')
    pf = dict(job=a.job, skipped=skip)
    loads = {}
    if skip:
        A = json.loads(pa.read_text()); pf.update(skipped_because='records/jobA/PREFLIGHT.json PASS', jobA_rates=A['rates'])
        helper_tps = A['rates']['helper_tokens_per_s']
        q, qtok, loads['qwen3'] = load_model('qwen3'); loads['helper'] = loads['qwen3']
    else:
        h, htok, lh = load_model('helper'); q, qtok, lq = load_model('qwen3'); loads['helper'], loads['qwen3'] = lh, lq
        pf['first_output_utc'] = utc()
        pf['obqa'], r1 = preflight_obqa(h, htok, q, qtok)
        free(h); del h
        helper_tps = r1['helper_tokens'] / r1['helper_s']
        pf['rates'] = dict(helper_tokens_per_s=helper_tps, qwen3_frozen_R_tokens_per_s=r1['receiver_tokens'] / r1['receiver_s'], **r1)
        if not pf['obqa']['PASS'] and not a.dry_run:
            pf['PASS'] = False; save(pf_path, pf); g.update(PASS=False, reason='OBQA preflight failed'); save(OUT / 'GATE.json', g); return g
    sm = {}
    sm['qwen3'], qtps = smoke(q, qtok, 'qwen3', pilot, fh); free(q); del q
    lm_, ltok, loads['llama'] = load_model('llama')
    if not skip:
        pf['x3'], r2 = preflight_x3(lm_, ltok)
        pf['rates']['llama_frozen_R_tokens_per_s'] = r2['receiver_tokens'] / r2['receiver_s']
        pf['PASS'] = pf['obqa']['PASS'] and pf['x3']['PASS']
        pf['load_seconds'] = loads
        save(pf_path, pf)
        if not pf['x3']['PASS'] and not a.dry_run:
            g.update(PASS=False, reason='X3 preflight failed'); save(OUT / 'GATE.json', g); return g
    else:
        save(pf_path, pf)
    sm['llama'], ltps = smoke(lm_, ltok, 'llama', pilot, fh); free(lm_); del lm_
    fh.close()
    kept = [ds for ds in DS if not (sm['qwen3'][ds]['fail'] or sm['llama'][ds]['fail'])]
    nq = math.ceil(N_FULL * len(kept) / a.nranks)
    el = time.time() - a.job_start
    proj = el + loads['helper'] + loads['qwen3'] + loads['llama'] + nq * HELPER_MAX_NEW / helper_tps + 2 * nq * RECEIVER_MAX_NEW / qtps \
        + 2 * nq * RECEIVER_MAX_NEW / ltps
    n_use = N_FULL if proj <= PROJ_LIMIT_S else N_REDUCED
    g.update(PASS=bool(kept) and (pf.get('PASS', False) or skip or a.dry_run), preflight_PASS=pf.get('PASS'), preflight_skipped=skip,
             smoke=sm, datasets_kept=kept, datasets_dropped=[ds for ds in DS if ds not in kept], n_per_dataset=n_use,
             reduced_to_300=n_use == N_REDUCED,
             projection=dict(elapsed_s=el, load_s=loads, helper_tokens_per_s=helper_tps, qwen3_e20_tokens_per_s=qtps, llama_e20_tokens_per_s=ltps,
                             questions_per_rank=nq, worst_case_projected_total_s=proj, limit_s=PROJ_LIMIT_S), utc_gate=utc())
    if not kept: g['reason'] = 'all datasets dropped by the smoke'
    save(OUT / 'GATE.json', g)
    log('GATE', g['PASS'], 'kept', kept, 'n', n_use, f'projection {proj / 60:.1f} min')
    return g


# ------------------------------------------------------------------------------------------------ main
pilot = {ds: jl(PILOT(ds)) for ds in DS}
assert all(len(v) == N_FULL for v in pilot.values())
t0 = time.time()
if a.rank == 0:
    try:
        G = gate_rank0(pilot)
    except Exception:
        G = dict(PASS=False, reason='exception in gate', traceback=traceback.format_exc()); save(OUT / 'GATE.json', G); log(G['traceback'])
else:
    while not (OUT / 'GATE.json').exists():
        if time.time() > a.deadline_epoch: log('no GATE before deadline'); sys.exit(6)
        time.sleep(5)
    time.sleep(1); G = json.loads((OUT / 'GATE.json').read_text())
if not G.get('PASS'):
    log('GATE not PASS; no E20 generation on this rank:', G.get('reason')); sys.exit(5)

items = [(ds, it) for ds in G['datasets_kept'] for it in pilot[ds][:G['n_per_dataset']]]
mine = items[a.rank::a.nranks]
if a.dry_run and a.dry_limit: mine = mine[:a.dry_limit]
status = dict(rank=a.rank, job=a.job, n_items=len(mine), utc_start=utc(), stages={}, errors=[], stopped_early=False)
log('shard', len(mine), 'items')


def over(): return time.time() > a.deadline_epoch


# (iii) helper
hp = OUT / f'helper_rank{a.rank}.jsonl'
h, htok, lt = load_model('helper'); t = time.time(); done = 0
with open(hp, 'a') as fh:
    for ds, it in mine:
        if over(): status['stopped_early'] = True; break
        try:
            append(fh, dict(**e20_helper(h, htok, ds, it), utc=utc(), runtime_error=None)); done += 1
        except Exception:
            status['errors'].append(dict(stage='helper', dataset=ds, id=it['id'], tb=traceback.format_exc()[-1500:]))
            append(fh, dict(dataset=ds, id=it['id'], utc=utc(), runtime_error=traceback.format_exc()[-1500:]))
status['stages']['helper'] = dict(load_s=lt, done=done, seconds=time.time() - t); free(h); del h
log('helper done', done)
MSG = {(r['dataset'], r['id']): r for r in jl(hp)}

# (iv) Qwen3-8B, (v) Llama-3.1-8B
for recv in RECEIVERS:
    if over(): status['stopped_early'] = True; break
    m, tok, lt = load_model(recv); SPECIAL = special_ids(tok, m); t = time.time(); done = 0
    with open(OUT / f'recv_{recv}_rank{a.rank}.jsonl', 'a') as fh:
        for ds, it in mine:
            if over(): status['stopped_early'] = True; break
            hm = MSG.get((ds, it['id']))
            rec = dict(dataset=ds, id=it['id'], receiver=recv, utc=utc(), runtime_error=None,
                       helper_message_sha256=hm.get('helper_message_sha256') if hm else None)
            try:
                rec['R'] = e20_receiver(m, tok, PR.receiver_only_messages(ds, it), SPECIAL)
                rec['T'] = e20_receiver(m, tok, PR.receiver_with_message_messages(ds, it, hm['helper_message']), SPECIAL)
                done += 1
            except Exception:
                rec['runtime_error'] = traceback.format_exc()[-1500:]
                status['errors'].append(dict(stage=recv, dataset=ds, id=it['id'], tb=rec['runtime_error']))
            append(fh, rec)
    status['stages'][recv] = dict(load_s=lt, done=done, seconds=time.time() - t, special_ids=sorted(SPECIAL))
    free(m); del m
    log(recv, 'done', done)
status.update(utc_end=utc(), wall_s=time.time() - t0, complete=all(status['stages'].get(s, {}).get('done') == len(mine) for s in ['helper'] + RECEIVERS))
save(OUT / f'status_rank{a.rank}.json', status)
log('END complete', status['complete'], 'errors', len(status['errors']))
