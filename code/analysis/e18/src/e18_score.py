"""E18 GPU worker: one process per GPU (receiver only), preflight -> cross-rank gate -> production.

Forward code = E10 R-path rescoring (P2_R4_E10.../src/e10_exec.py RT.__init__ and RT.rescore):
same tokenizer/model path, chat-template hash check, bf16, sdpa, tf32 off, seeds, prompt from the frozen
e10_prompts.receiver_only_messages rendered with enable_thinking=False, prompt ids = tok(rendered),
one forward `model(input_ids=x, use_cache=False)`.  Input = [prompt ids ; stored E10 generated ids].
Generated token i (1-based) is predicted by the logits at index P + i - 2.

Stored per row: split, question_id, L (content tokens, EOS/end-of-turn excluded), n_gen_tokens,
argmax matches over positions 1..min(32, L), and d_i = 1 - max_v p_i(v) for i = 1..min(64, L),
in float64 as -expm1(max log_softmax(logits.double())).
NO GOLD IS READ: only E10 records (no gold fields), split id lists, question texts, frozen config.
"""
import os, sys, json, time, math, hashlib, argparse, glob, datetime
sys.dont_write_bytecode = True
from pathlib import Path

ROOT = Path('$DATA_DIR')
E10 = ROOT / 'P2_R4_E10_20260920T225954Z'
STAGE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(E10 / 'src'))
import e10_prompts as PR
CFG = json.loads((ROOT / 'P2_R3_E9BC_20260920T061042Z/large/frozen_config.json').read_text())['native']
SPEC = CFG['models']['receiver']
EOS = set(CFG['receiver_generation_config']['eos_token_id'])
K_STORE, K_MATCH = 64, 32

# ---- preflight (b) rule = PREREG_E18.md "Preflight" (D1 = A, D2 = A): u and s3 <= 1e-4 on every preflight row,
# from the single pass over the stored tokens; row gsm8k_train_05081 (not aligned with E10's re-scoring input)
# from one extra pass over E10's own re-scoring input.  s2 max |diff| is reported, not gated.
PREFLIGHT_RULE = {'name': 'PREREG_E18_D1A_D2A', 'tol_u_s3': 1e-4, 'tol_s2': None, 's2_gates': False,
                  'nonaligned_rows': 'e10_retokenized_pass'}   # 'fail' | 'exclude' | 'e10_retokenized_pass'
MATCH_MIN = 0.99

ap = argparse.ArgumentParser()
ap.add_argument('--rank', type=int, required=True)
ap.add_argument('--nranks', type=int, required=True)
ap.add_argument('--out', default=str(STAGE / 'records'))
ap.add_argument('--dry-run', action='store_true', help='no model weights; exercises the data path only')
a = ap.parse_args()
OUT = Path(a.out); OUT.mkdir(parents=True, exist_ok=True)

def utc():
    return datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

def save(p, v):
    p = Path(p); t = p.with_suffix(p.suffix + '.tmp')
    t.write_text(json.dumps(v, indent=1, allow_nan=False) + '\n'); t.replace(p)

# ---------------------------------------------------------------- inputs (no gold)
REC = {}
for f in sorted(glob.glob(str(E10 / 'records/main_rank*.jsonl'))):
    for line in open(f):
        if line.strip():
            r = json.loads(line)
            if r['action'] == 'R':
                REC[(r['split'], r['id'])] = r
SPL = {s: json.loads((E10 / f'splits/gsm8k_{s}_ids.json').read_text()) for s in ['fit', 'cal', 'dev']}
QUERIES = {}
for line in open(E10 / 'inputs/gsm8k_queries.jsonl'):
    q = json.loads(line); QUERIES[q['id']] = q['question']
ALL = [(s, i) for s in ['fit', 'cal', 'dev'] for i in SPL[s]]
assert len(ALL) == 1800 and all(k in REC for k in ALL)
PRE = [('fit', i) for i in SPL['fit'][:16]] + [('fit', i) for i in SPL['fit'][16:] if REC[('fit', i)]['u'] > 0]

# ---------------------------------------------------------------- runtime (the E10 loader, receiver only)
from transformers import AutoTokenizer
tok = AutoTokenizer.from_pretrained(SPEC['path'], local_files_only=True)
assert hashlib.sha256(tok.chat_template.encode()).hexdigest() == SPEC['chat_template_sha256']
if tok.pad_token is None: tok.pad_token = tok.eos_token
if not a.dry_run:
    import torch
    from transformers import AutoModelForCausalLM
    assert torch.cuda.device_count() == 1, torch.cuda.device_count()
    torch.set_num_threads(1); torch.set_num_interop_threads(1)
    torch.manual_seed(0); torch.cuda.manual_seed_all(0)
    torch.backends.cuda.matmul.allow_tf32 = False; torch.backends.cudnn.allow_tf32 = False
    t0 = time.perf_counter()
    MODEL = AutoModelForCausalLM.from_pretrained(SPEC['path'], local_files_only=True, torch_dtype=torch.bfloat16,
                                                 attn_implementation='sdpa').to('cuda:0').eval().requires_grad_(False)
    torch.cuda.synchronize(); LOAD_S = time.perf_counter() - t0
    GPU = torch.cuda.get_device_name(0)
else:
    LOAD_S, GPU = None, 'DRY-RUN (no weights)'
print('E18 rank=%d up on %s gpu=%s load=%s s' % (a.rank, os.uname().nodename, GPU, LOAD_S), flush=True)

def prompt_ids(qid):
    rendered = tok.apply_chat_template(PR.receiver_only_messages(QUERIES[qid]), tokenize=False,
                                       add_generation_prompt=True, enable_thinking=False)
    return tok(rendered, return_tensors=None)['input_ids']

def forward(ids):
    """E10 RT.rescore forward: one pass, batch 1, no cache, no mask. Returns bf16 logits [T, V]."""
    import torch
    with torch.inference_mode():
        x = torch.tensor([ids], device='cuda:0')
        return MODEL(input_ids=x, use_cache=False).logits[0]

def score_row(key, preflight=False):
    split, qid = key
    r = REC[key]
    g = r['generated_token_ids']
    pid = prompt_ids(qid)
    assert len(pid) == r['receiver_input_tokens'], (qid, len(pid), r['receiver_input_tokens'])
    P, Lall = len(pid), len(g)
    L = Lall - (1 if g and g[-1] in EOS else 0)
    k64, k32 = min(K_STORE, L), min(K_MATCH, L)
    out = {'split': split, 'question_id': qid, 'L': L, 'n_gen_tokens': Lall, 'n_pos_32': k32}
    if a.dry_run:
        out.update({'argmax_match_32': -1, 'one_minus_maxp': [-1.0] * k64, 'DRY_RUN': True})
        return out, None
    import torch
    lg = forward(pid + g)[P - 1:P - 1 + Lall]                     # row i-1 predicts generated token i
    assert lg.shape[0] == Lall
    mx = torch.log_softmax(lg[:k64].double(), -1).max(-1).values
    out['one_minus_maxp'] = [float(v) for v in (-torch.expm1(mx)).cpu().tolist()]
    tg = torch.tensor(g, device=lg.device)
    out['argmax_match_32'] = int((lg[:k32].argmax(-1) == tg[:k32]).sum().item())
    if not preflight:
        return out, None
    # ---- preflight (b): E10's own definitions, float32 log_softmax as in e10_exec.py
    lp = torch.log_softmax(lg.float(), -1).gather(1, tg[:, None])[:, 0].tolist()
    s2 = float(1 - math.exp(sum(lp) / len(lp)))                   # e10_exec.scores_from, all generated tokens
    rs = r['rescore']
    cat = rs['prefix_token_ids'] + rs['answer_token_ids']
    aligned = cat == g[:len(cat)]
    d = {'id': qid, 'L': L, 'argmax_match_32': out['argmax_match_32'], 'n_pos_32': k32, 'aligned_with_e10_rescore': aligned,
         's2_e10': r['s2'], 's2_tf': s2, 'abs_diff_s2': abs(s2 - r['s2']), 'u_e10': r['u'], 's3_e10': r['s3']}
    if aligned:
        n0 = len(rs['prefix_token_ids']); la = lp[n0:n0 + len(rs['answer_token_ids'])]
        d['u_tf'] = float(1 - math.exp(sum(la) / len(la))); d['s3_tf'] = float(1 - math.exp(la[0]))
    else:
        # D1 = A (gated): E10 RT.rescore input verbatim ([prompt ; tok(text[:start]) ; tok(a)]), a second pass
        lg2 = forward(pid + cat)
        n0 = P + len(rs['prefix_token_ids'])
        lp2 = torch.log_softmax(lg2[n0 - 1:len(pid + cat) - 1].float(), -1)
        la = lp2.gather(1, torch.tensor(rs['answer_token_ids'], device=lg2.device)[:, None])[:, 0].tolist()
        d['u_e10_retok_pass'] = float(1 - math.exp(sum(la) / len(la))); d['s3_e10_retok_pass'] = float(1 - math.exp(la[0]))
    for k in ['u', 's3']:
        v = d.get(k + '_tf', d.get(k + '_e10_retok_pass'))
        d['abs_diff_' + k] = abs(v - d[k + '_e10'])
    return out, d

def wait_for(pattern, want, timeout):
    t = time.time()
    while time.time() - t < timeout:
        if len(glob.glob(str(OUT / pattern))) >= want:
            return True
        time.sleep(3)
    return False

# ---------------------------------------------------------------- preflight
mine = [k for j, k in enumerate(PRE) if j % a.nranks == a.rank]
det = [score_row(k, preflight=True)[1] for k in mine]
save(OUT / f'preflight_rank{a.rank}.json', {'rank': a.rank, 'utc': utc(), 'rows': det, 'gpu': GPU,
                                            'load_seconds': LOAD_S, 'dry_run': a.dry_run, 'gold_read': False})
if not wait_for('preflight_rank*.json', a.nranks, 1200):
    print('E18 rank=%d preflight gather TIMEOUT' % a.rank, flush=True); sys.exit(6)
rows = [x for p in sorted(glob.glob(str(OUT / 'preflight_rank*.json'))) for x in json.loads(Path(p).read_text())['rows']]
if a.dry_run:
    ok, rep = True, {'DRY_RUN': True, 'n_rows': len(rows)}
else:
    R = PREFLIGHT_RULE
    match, npos = sum(x['argmax_match_32'] for x in rows), sum(x['n_pos_32'] for x in rows)
    al = [x for x in rows if x['aligned_with_e10_rescore']]
    na = [x for x in rows if not x['aligned_with_e10_rescore']]
    us_rows = al if R['nonaligned_rows'] in ('fail', 'exclude') else rows
    mx = {k: max(x['abs_diff_' + k] for x in (rows if k == 's2' else us_rows)) for k in ['s2', 'u', 's3']}
    ok_a = match / npos >= MATCH_MIN
    ok_b = (mx['u'] <= R['tol_u_s3'] and mx['s3'] <= R['tol_u_s3']
            and (not R['s2_gates'] or mx['s2'] <= R['tol_s2'])
            and not (na and R['nonaligned_rows'] == 'fail'))
    ok = bool(ok_a and ok_b)
    rep = {'utc': utc(), 'rule': R, 'n_rows': len(rows), 'row_ids': [x['id'] for x in rows],
           'a_argmax_match': [match, npos], 'a_rate': match / npos, 'a_PASS': ok_a,
           'b_max_abs_diff': mx, 'b_nonaligned_rows': [x['id'] for x in na], 'b_PASS': ok_b,
           'max_abs_diff_s2_all_rows': max(x['abs_diff_s2'] for x in rows),
           'PASS': ok, 'detail': rows, 'gold_read': False}
if a.rank == 0:
    save(OUT / 'PREFLIGHT.json', rep)
print('E18 PREFLIGHT rank=%d pass=%s %s' % (a.rank, ok, {k: rep[k] for k in rep if k in ('a_argmax_match', 'b_max_abs_diff', 'b_nonaligned_rows')}), flush=True)
if not ok:
    print('E18 rank=%d PREFLIGHT FAILED; production not run' % a.rank, flush=True); sys.exit(4)

# ---------------------------------------------------------------- production: every fit, cal, dev R row
todo = [k for j, k in enumerate(ALL) if j % a.nranks == a.rank]
t0 = time.time(); n = 0
with (OUT / f'scores_rank{a.rank}.jsonl').open('w') as f:
    for k in todo:
        f.write(json.dumps(score_row(k)[0], allow_nan=False) + '\n'); n += 1
        if n % 100 == 0:
            f.flush(); print('E18 rank=%d %d/%d %.0fs' % (a.rank, n, len(todo), time.time() - t0), flush=True)
save(OUT / f'scores_rank{a.rank}.status.json', {'rank': a.rank, 'utc': utc(), 'rows': n, 'expected': len(todo),
                                               'complete': n == len(todo), 'seconds': time.time() - t0,
                                               'dry_run': a.dry_run, 'gold_read': False})
print('E18 rank=%d production done %d/%d' % (a.rank, n, len(todo)), flush=True)
