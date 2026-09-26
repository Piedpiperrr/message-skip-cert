"""E10 GPU driver: one shard per GPU (helper + receiver both on the single visible device).

Phases, in order, inside one job:
  preflight  reproduce 16 stored OBQA fit rows (receiver-only and Text) bit for bit, using the
             UNCHANGED frozen code paths (64-token cap, frozen MC prompts).
  smoke      2 GSM8K fit questions per rank (16 total) through all three generations; gate on
             the INVALID count; also runs the re-scoring/generation log-probability check.
  main       fit R -> cal R -> cal T -> dev R -> dev T, in that priority order, resumable.

No gold is read in any phase: the GSM8K answer column is never opened, and the stored OBQA rows
are projected to the fields needed for byte comparison.
"""
import os, sys, json, time, math, hashlib, argparse, traceback
from pathlib import Path
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
STAGE = HERE.parent
sys.path.insert(0, str(HERE))
import torch
from e10_extract import extract, equal, INVALID
import e10_prompts as PR

ROOT = Path('$DATA_DIR')
P10 = ROOT / 'P2_10_20260911T122423Z'
BOUND = ROOT / 'P2_CONFIDENCE_REFERENCE_BOUNDARIES_20260914T165012Z'
CFG = json.loads((ROOT / 'P2_R3_E9BC_20260920T061042Z/large/frozen_config.json').read_text())['native']

HELPER_MAX_NEW = 256     # frozen
RECEIVER_MAX_NEW = 320   # PREREG_E10, raised from 64

ap = argparse.ArgumentParser()
ap.add_argument('--rank', type=int, required=True)
ap.add_argument('--nranks', type=int, required=True)
ap.add_argument('--phase', required=True, choices=['preflight', 'smoke', 'main', 'all'])
ap.add_argument('--deadline-epoch', type=float, default=float('inf'))
a = ap.parse_args()

def utc():
    import datetime
    return datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

def save(p, v):
    p = Path(p); p.parent.mkdir(parents=True, exist_ok=True)
    t = p.with_suffix(p.suffix + '.tmp')
    t.write_text(json.dumps(v, ensure_ascii=False, indent=2, allow_nan=False) + '\n')
    t.replace(p)

def jl(p):
    with Path(p).open() as f:
        return [json.loads(s) for s in f if s.strip()]

# ---------------------------------------------------------------- runtime (single GPU)
sys.path.insert(0, str(P10))
import legacy_methods as lm
import protocol_min
# The frozen large-pair runtime (native_adapter.py) imports this adapter, which rebinds
# format_openbook to the P2-8 v2 formatter reading 'choice_text' with a variable option count.
# The stored OBQA rows were produced through it, so the preflight must load it too.  It touches
# nothing the GSM8K paths use: those build their prompts from e10_prompts directly.
import arc_runtime_adapter  # noqa: F401
from protocol_min import apply_generation_config, receiver_prompt_tensors, generate_receiver
sys.path.remove(str(P10))
lm.cuda_wall_stage = lambda fn, device: (fn(), 0., 0.)
lm.wall_stage = lambda fn: (fn(), 0.)
lm.extract_prediction = lambda text: None

from transformers import AutoModelForCausalLM, AutoTokenizer

class RT:
    """The frozen loader of P2_10 runtime.Runner, with both roles on the one visible device."""
    def __init__(self):
        assert torch.cuda.device_count() == 1, torch.cuda.device_count()
        torch.set_num_threads(1); torch.set_num_interop_threads(1)
        torch.manual_seed(0); torch.cuda.manual_seed_all(0)
        torch.backends.cuda.matmul.allow_tf32 = False; torch.backends.cudnn.allow_tf32 = False
        self.dev = 'cuda:0'; self.load = {}
        for role in ['helper', 'receiver']:
            t = time.perf_counter(); spec = CFG['models'][role]
            tok = AutoTokenizer.from_pretrained(spec['path'], local_files_only=True)
            assert hashlib.sha256(tok.chat_template.encode()).hexdigest() == spec['chat_template_sha256'], role
            if tok.pad_token is None: tok.pad_token = tok.eos_token
            m = AutoModelForCausalLM.from_pretrained(spec['path'], local_files_only=True,
                    torch_dtype=torch.bfloat16, attn_implementation='sdpa').to(self.dev).eval().requires_grad_(False)
            apply_generation_config(m, {'do_sample': False, 'max_new_tokens': 64})
            setattr(self, role, m); setattr(self, role + '_tok', tok)
            torch.cuda.synchronize(); self.load[role] = time.perf_counter() - t
        assert self.receiver.generation_config.to_dict() == CFG['receiver_generation_config']
        lm.HELPER_CONFIG = self.helper.config; lm.RECEIVER_CONFIG = self.receiver.config
        self.th = lm.T2THelperBundle(self.helper, self.helper_tok)     # frozen helper, 256 tokens
        self.tr = lm.T2TReceiverBundle(self.receiver, self.receiver_tok)
        self.eos = self.receiver.generation_config.eos_token_id
        self.pad = self.receiver.generation_config.pad_token_id

    # ---- frozen OBQA paths, used only by the preflight (64-token cap, unchanged code) ----
    @torch.inference_mode()
    def obqa_receiver_only(self, row):
        _, _, tn = receiver_prompt_tensors(self.receiver_tok, row, self.dev)
        text, ids = generate_receiver(self.receiver, self.receiver_tok, tn)
        return text, ids.cpu().tolist()

    @torch.inference_mode()
    def obqa_text(self, row):
        msg = self.th.run(row)
        res = self.tr.consume(row, msg['helper_body'], msg['helper_message'])
        return res['generated_text'], res['generated_token_ids']

    # ---- E10 GSM8K paths ----
    @torch.inference_mode()
    def gsm_helper(self, question):
        prompt = PR.helper_prompt(question)
        inp = self.helper_tok.apply_chat_template([{'role': 'user', 'content': prompt}],
                tokenize=True, add_generation_prompt=True, return_tensors='pt',
                enable_thinking=False).to(self.dev)
        out = self.helper.generate(inp, max_new_tokens=HELPER_MAX_NEW, do_sample=False)
        gen = out[:, inp.shape[-1]:]
        text = self.helper_tok.batch_decode(gen, skip_special_tokens=True,
                                            clean_up_tokenization_spaces=False)[0]
        return {'helper_message': text, 'helper_generated_token_ids': gen[0].cpu().tolist(),
                'helper_input_tokens': int(inp.shape[1])}

    def _render(self, messages):
        return self.receiver_tok.apply_chat_template(messages, tokenize=False,
                add_generation_prompt=True, enable_thinking=False)

    @torch.inference_mode()
    def gsm_receiver(self, messages, want_scores):
        """Greedy receiver generation at the E10 320-token cap; mirrors protocol_min
        .generate_receiver argument for argument apart from max_new_tokens."""
        rendered = self._render(messages)
        tn = self.receiver_tok(rendered, return_tensors='pt')
        tn = {k: v.to(self.dev) for k, v in tn.items()}
        out = self.receiver.generate(input_ids=tn['input_ids'], attention_mask=tn['attention_mask'],
                do_sample=False, max_new_tokens=RECEIVER_MAX_NEW, use_cache=True,
                pad_token_id=self.pad, eos_token_id=self.eos,
                return_dict_in_generate=True, output_scores=want_scores)
        seq = out.sequences
        gen = seq[0, tn['input_ids'].shape[1]:]
        text = self.receiver_tok.decode(gen, skip_special_tokens=True).strip('\n')
        lp = None
        if want_scores:
            lp = []
            for step, sc in enumerate(out.scores):
                lp.append(float(torch.log_softmax(sc[0].float(), -1)[gen[step]].item()))
        return {'text': text, 'gen_ids': gen.cpu().tolist(), 'prompt_ids': tn['input_ids'][0].cpu().tolist(),
                'rendered': rendered, 'gen_logprobs': lp,
                'receiver_input_tokens': int(tn['input_ids'].shape[1])}

    @torch.inference_mode()
    def rescore(self, rendered, text, start, end):
        """PREREG_E10 score: tokenize the prompt, the generation up to `start`, and `a` itself;
        concatenate; one forward pass; read the log-probabilities at the positions of a's tokens."""
        tk = self.receiver_tok
        pid = tk(rendered, return_tensors=None)['input_ids']
        pre = tk(text[:start], add_special_tokens=False)['input_ids'] if start > 0 else []
        ans = tk(text[start:end], add_special_tokens=False)['input_ids']
        if not ans:
            return None
        ids = pid + pre + ans
        x = torch.tensor([ids], device=self.dev)
        logits = self.receiver(input_ids=x, use_cache=False).logits[0]
        n0 = len(pid) + len(pre)
        lp = torch.log_softmax(logits[n0 - 1:len(ids) - 1].float(), -1)
        tgt = torch.tensor(ans, device=self.dev)
        tok_lp = lp.gather(1, tgt[:, None])[:, 0].tolist()
        return {'answer_token_ids': ans, 'answer_token_logprobs': [float(v) for v in tok_lp],
                'prefix_token_ids': pre, 'prompt_tokens': len(pid)}

def scores_from(res, ex, rs):
    """u (certification), s2 and s3 (descriptive), per PREREG_E10."""
    s2 = None
    if res['gen_logprobs']:
        s2 = float(1 - math.exp(sum(res['gen_logprobs']) / len(res['gen_logprobs'])))
    if ex['answer'] == INVALID or rs is None:
        return {'u': 1.0, 's2': s2, 's3': 1.0,
                'u_is_invalid': ex['answer'] == INVALID,
                'u_is_rescore_empty': ex['answer'] != INVALID and rs is None}
    lps = rs['answer_token_logprobs']
    u = float(1 - math.exp(sum(lps) / len(lps)))
    s3 = float(1 - math.exp(lps[0]))
    return {'u': u, 's2': s2, 's3': s3, 'u_is_invalid': False, 'u_is_rescore_empty': False}

# ---------------------------------------------------------------- phases
REC = STAGE / 'records'; REC.mkdir(exist_ok=True)
QUERIES = {r['id']: r for r in jl(STAGE / 'inputs/gsm8k_queries.jsonl')}
SPL = {s: json.loads((STAGE / f'splits/gsm8k_{s}_ids.json').read_text()) for s in ['fit', 'cal', 'dev']}

def do_receiver_only(rt, qid, want_scores=False):
    q = QUERIES[qid]['question']
    t0 = time.perf_counter()
    res = rt.gsm_receiver(PR.receiver_only_messages(q), want_scores=True)
    ex = extract(res['text'])
    rs = rt.rescore(res['rendered'], res['text'], ex['start'], ex['end']) if ex['answer'] != INVALID else None
    sc = scores_from(res, ex, rs)
    dt = (time.perf_counter() - t0) * 1000
    out = {'id': qid, 'action': 'R', 'latency_ms': dt, 'raw_answer': res['text'],
           'generated_token_ids': res['gen_ids'], 'n_gen_tokens': len(res['gen_ids']),
           'receiver_input_tokens': res['receiver_input_tokens'],
           'answer': ex['answer'], 'invalid': ex['answer'] == INVALID, 'extract_route': ex['route'],
           'answer_raw': ex['raw'], 'answer_start': ex['start'], 'answer_end': ex['end'],
           **sc, 'rescore': rs, 'gold_read': False}
    if want_scores:
        out['gen_logprobs'] = res['gen_logprobs']
    return out

def do_text(rt, qid):
    q = QUERIES[qid]['question']
    t0 = time.perf_counter()
    h = rt.gsm_helper(q)
    res = rt.gsm_receiver(PR.receiver_with_message_messages(q, h['helper_message']), want_scores=False)
    ex = extract(res['text'])
    dt = (time.perf_counter() - t0) * 1000
    return {'id': qid, 'action': 'T', 'latency_ms': dt, 'raw_answer': res['text'],
            'generated_token_ids': res['gen_ids'], 'n_gen_tokens': len(res['gen_ids']),
            'receiver_input_tokens': res['receiver_input_tokens'],
            'helper_message': h['helper_message'], 'helper_input_tokens': h['helper_input_tokens'],
            'n_helper_tokens': len(h['helper_generated_token_ids']),
            'answer': ex['answer'], 'invalid': ex['answer'] == INVALID, 'extract_route': ex['route'],
            'gold_read': False}

def phase_preflight(rt):
    fit = json.loads((BOUND / 'splits/obqa_fit_representatives.json').read_text())
    qs = {r['id']: r for r in jl(BOUND / 'inputs/obqa_train_queries.jsonl')}
    rows = jl(P10 / 'results/large/obqa/train_historical_rtc.jsonl')
    rep = {}
    for act, native in [('R', 'receiver_only'), ('T', 'text')]:
        by = {r['id']: {'raw_answer': r['raw_answer'], 'generated_token_ids': r['generated_token_ids']}
              for r in rows if r['action'] == native}       # gold_answer deliberately not projected
        ids = [i for i in fit if i in by][:16]
        mism, det = 0, []
        for i in ids:
            row = {k: (list(qs[i][k]) if isinstance(qs[i][k], list) else qs[i][k])
                   for k in ['question_stem', 'choice_labels', 'choice_text']}
            text, gids = rt.obqa_receiver_only(row) if act == 'R' else rt.obqa_text(row)
            ok = (text == by[i]['raw_answer'] and list(gids) == list(by[i]['generated_token_ids']))
            mism += (not ok)
            det.append({'id': i, 'match': ok, 'got': text, 'expected': by[i]['raw_answer'],
                        'token_ids_match': list(gids) == list(by[i]['generated_token_ids'])})
        rep[act] = {'n': len(ids), 'mismatches': mism, 'rows': det}
        print('PREFLIGHT rank=%d %s n=%d mismatches=%d' % (a.rank, act, len(ids), mism), flush=True)
    rep = {'rank': a.rank, 'utc': utc(), 'host': os.uname().nodename,
           'criterion': 'bit-for-bit raw_answer and generated_token_ids vs stored P2_10 rows',
           'per_action': {k: {'n': v['n'], 'mismatches': v['mismatches']} for k, v in rep.items()},
           'detail': rep, 'PASS': all(v['mismatches'] == 0 for v in rep.values()),
           'gold_read': False, 'load_seconds': rt.load,
           'gpu': torch.cuda.get_device_name(0)}
    save(REC / f'preflight_rank{a.rank}.json', rep)
    return rep['PASS']

def phase_smoke(rt):
    ids = SPL['fit'][a.rank * 2:(a.rank + 1) * 2]
    out, chk = [], []
    for qid in ids:
        r = do_receiver_only(rt, qid, want_scores=True)
        t = do_text(rt, qid)
        out += [r, t]
        # re-scoring vs generation log-probabilities, where the token sequences overlap
        if r['rescore']:
            cat = r['rescore']['prefix_token_ids'] + r['rescore']['answer_token_ids']
            g = r['generated_token_ids']
            k = 0
            while k < min(len(cat), len(g)) and cat[k] == g[k]:
                k += 1
            n0 = len(r['rescore']['prefix_token_ids'])
            diffs = [abs(r['rescore']['answer_token_logprobs'][j - n0] - r['gen_logprobs'][j])
                     for j in range(n0, min(k, len(g), n0 + len(r['rescore']['answer_token_ids'])))]
            chk.append({'id': qid, 'gen_tokens': len(g), 'retokenized_tokens': len(cat),
                        'common_prefix_tokens': k, 'exact_retokenization': cat == g[:len(cat)],
                        'overlapping_answer_tokens': len(diffs),
                        'max_abs_logprob_diff': max(diffs) if diffs else None})
    with (REC / f'smoke_rank{a.rank}.jsonl').open('w') as f:
        for r in out:
            f.write(json.dumps(r, ensure_ascii=False, allow_nan=False) + '\n')
    save(REC / f'smokecheck_rank{a.rank}.json',
         {'rank': a.rank, 'utc': utc(), 'ids': ids, 'rescore_vs_generation': chk,
          'invalid_R': sum(r['invalid'] for r in out if r['action'] == 'R'),
          'invalid_T': sum(r['invalid'] for r in out if r['action'] == 'T'),
          'empty_helper_message': sum(not r['helper_message'].strip() for r in out if r['action'] == 'T'),
          'n_gen_tokens_R': [r['n_gen_tokens'] for r in out if r['action'] == 'R'],
          'n_gen_tokens_T': [r['n_gen_tokens'] for r in out if r['action'] == 'T'],
          'gold_read': False})
    print('SMOKE rank=%d done ids=%s' % (a.rank, ids), flush=True)
    return True

def phase_main(rt):
    tasks = []
    for split, act in [('fit', 'R'), ('cal', 'R'), ('cal', 'T'), ('dev', 'R'), ('dev', 'T')]:
        grp = [(split, act, qid) for j, qid in enumerate(SPL[split]) if j % a.nranks == a.rank]
        tasks += grp
    out = REC / f'main_rank{a.rank}.jsonl'
    have = set()
    if out.exists():
        for line in out.open():
            line = line.strip()
            if not line: continue
            try: r = json.loads(line)
            except Exception: continue
            have.add((r['split'], r['action'], r['id']))
    todo = [t for t in tasks if t not in have]
    print('MAIN rank=%d tasks=%d resumed=%d todo=%d' % (a.rank, len(tasks), len(have), len(todo)), flush=True)
    done, errs, stopped = 0, [], False
    with out.open('a') as f:
        for split, act, qid in todo:
            if time.time() > a.deadline_epoch:
                stopped = True; print('DEADLINE rank=%d after %d' % (a.rank, done), flush=True); break
            try:
                r = do_receiver_only(rt, qid) if act == 'R' else do_text(rt, qid)
                f.write(json.dumps({'split': split, **r, 'job_id': os.environ.get('PBS_JOBID')},
                                   ensure_ascii=False, allow_nan=False) + '\n')
                f.flush()
            except BaseException as e:
                errs.append({'id': qid, 'split': split, 'action': act, 'error': repr(e),
                             'traceback': traceback.format_exc()[-1500:]})
                if len(errs) > 20:
                    print('too many errors, stopping rank', a.rank, flush=True); stopped = True; break
            done += 1
            if done % 50 == 0:
                print('PROGRESS rank=%d %d/%d %.1f min left' %
                      (a.rank, done, len(todo), (a.deadline_epoch - time.time()) / 60), flush=True)
    save(REC / f'main_rank{a.rank}.status.json',
         {'rank': a.rank, 'utc': utc(), 'tasks': len(tasks), 'resumed': len(have), 'todo': len(todo),
          'done': done, 'errors': errs, 'stopped_early': stopped,
          'complete': done == len(todo) and not errs, 'job_id': os.environ.get('PBS_JOBID'),
          'gold_read': False})
    print('MAIN rank=%d done=%d/%d errors=%d' % (a.rank, done, len(todo), len(errs)), flush=True)

def wait_for(pattern, want, timeout):
    import glob
    t = time.time()
    while time.time() - t < timeout:
        n = len(glob.glob(str(REC / pattern)))
        if n >= want:
            return True
        time.sleep(5)
    print('GATE TIMEOUT rank=%d %s have=%d want=%d' % (a.rank, pattern, n, want), flush=True)
    return False

def gate_decision():
    """Same aggregation on every rank; rank 0 also writes records/GATE.json."""
    import glob
    pre = [json.loads(Path(p).read_text()) for p in sorted(glob.glob(str(REC / 'preflight_rank*.json')))]
    sm = [json.loads(Path(p).read_text()) for p in sorted(glob.glob(str(REC / 'smokecheck_rank*.json')))]
    mis = {k: sum(r['per_action'][k]['mismatches'] for r in pre) for k in ['R', 'T']}
    nn = {k: sum(r['per_action'][k]['n'] for r in pre) for k in ['R', 'T']}
    iR = sum(r['invalid_R'] for r in sm); iT = sum(r['invalid_T'] for r in sm)
    nsm = sum(len(r['ids']) for r in sm)
    ok = bool(pre and sm and all(r['PASS'] for r in pre) and mis['R'] == 0 and mis['T'] == 0
              and iR <= 2 and iT <= 2)
    g = [x for r in sm for x in r['n_gen_tokens_R'] + r['n_gen_tokens_T']]
    rep = {'utc': utc(), 'ranks_preflight': len(pre), 'ranks_smoke': len(sm),
           'obqa_rows_checked': nn, 'obqa_mismatches': mis, 'smoke_questions': nsm,
           'smoke_invalid_R': iR, 'smoke_invalid_T': iT,
           'empty_helper_messages': sum(r['empty_helper_message'] for r in sm),
           'gen_tokens_R': [x for r in sm for x in r['n_gen_tokens_R']],
           'gen_tokens_T': [x for r in sm for x in r['n_gen_tokens_T']],
           'rescore_check': [c for r in sm for c in r['rescore_vs_generation']],
           'criterion': 'all 16 stored OBQA rows reproduce bit for bit on both paths; '
                        'INVALID <= 2/16 on receiver-only and on Text',
           'GATE_PASS': ok, 'gold_read': False}
    if a.rank == 0:
        save(REC / 'GATE.json', rep)
    print('GATE rank=%d pass=%s obqa_mismatch=%s invalid R=%d T=%d n=%d gen_tok mean=%.0f max=%d'
          % (a.rank, ok, mis, iR, iT, nsm, (sum(g) / len(g)) if g else -1, max(g) if g else -1),
          flush=True)
    return ok

t0 = time.perf_counter(); rt = RT()
print('E10 rank=%d runtime up in %.1f s on %s' % (a.rank, time.perf_counter() - t0, os.uname().nodename), flush=True)
if a.phase == 'preflight':
    sys.exit(0 if phase_preflight(rt) else 4)
if a.phase == 'smoke':
    sys.exit(0 if phase_smoke(rt) else 4)
if a.phase == 'main':
    phase_main(rt); sys.exit(0)

# --- phase "all": one model load, preflight -> smoke -> cross-rank gate -> main ---
if not phase_preflight(rt):
    print('E10 rank=%d PREFLIGHT FAILED; no generation on this rank' % a.rank, flush=True)
    sys.exit(4)
phase_smoke(rt)
if not (wait_for('preflight_rank*.json', a.nranks, 900) and wait_for('smokecheck_rank*.json', a.nranks, 900)):
    sys.exit(6)
if not gate_decision():
    print('E10 rank=%d GATE REFUSED; main not run' % a.rank, flush=True)
    sys.exit(5)
phase_main(rt)
