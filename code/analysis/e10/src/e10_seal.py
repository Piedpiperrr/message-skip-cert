"""E10 steps 4-5 (CPU, login node): scores -> fit thresholds -> calibration disagreement ->
20 exact binomial tests -> routing decision -> hash everything.  NO GOLD IS READ HERE.

The certification arithmetic is the frozen one, copied from
P2_CONFIDENCE_REFERENCE_BOUNDARIES_20260914T165012Z/src/run_boundaries.py lines 26 and 50-54:
  thresholds[j] = sorted_fit_scores[ceil(j*N_fit/20) - 1] for j = 1..19, and +Infinity for j = 20
  n = #{cal : u <= tau}, k = #{those that disagree}
  p = Binom(n, .05).cdf(k);  accepted iff p <= .001;  chosen = largest accepted q
  no candidate accepted -> fall back to always communicating (the Text reference)
"""
import json, glob, hashlib, datetime, math, sys
from pathlib import Path
import numpy as np
from scipy.stats import binom, beta

STAGE = Path(__file__).resolve().parents[1]
OUT = STAGE / 'analysis'; OUT.mkdir(exist_ok=True)
Q = [j / 20 for j in range(1, 21)]
ALPHA, DELTA = .05, .001

def utc():
    return datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

def sha(p):
    h = hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()

rows = []
for f in sorted(glob.glob(str(STAGE / 'records/main_rank*.jsonl'))):
    for line in open(f):
        line = line.strip()
        if line:
            rows.append(json.loads(line))
by = {}
for r in rows:
    by[(r['split'], r['action'], r['id'])] = r
splits = {s: json.loads((STAGE / f'splits/gsm8k_{s}_ids.json').read_text()) for s in ['fit', 'cal', 'dev']}
want = {('fit', 'R'): 400, ('cal', 'R'): 1000, ('cal', 'T'): 1000, ('dev', 'R'): 400, ('dev', 'T'): 400}
have = {k: sum(1 for i in splits[k[0]] if (k[0], k[1], i) in by) for k in want}
complete = {k: have[k] == want[k] for k in want}
print('row counts:', {'%s %s' % k: '%d/%d' % (have[k], want[k]) for k in want})
if not all(complete.values()):
    print('WARNING: incomplete; analysing the intersection that exists', file=sys.stderr)

def usable(split):
    """ids with every record this split needs (R for fit; R and T for cal/dev)."""
    need = ['R'] if split == 'fit' else ['R', 'T']
    return [i for i in splits[split] if all((split, a, i) in by for a in need)]

fit_ids = usable('fit')
fit_u = sorted(by[('fit', 'R', i)]['u'] for i in fit_ids)
n_fit = len(fit_u)
thresholds = [fit_u[(j * n_fit + 19) // 20 - 1] if j < 20 else 'Infinity' for j in range(1, 21)]

def tv(t):
    return float('inf') if t == 'Infinity' else float(t)

def disagree(i, split):
    """PREREG_E10 change indicator: normalized exact match between the receiver-only answer and
    the Text answer.  Both records already store the canonical normalized string, so string
    equality is exactly the preregistered equality (INVALID == INVALID, else equal Decimals)."""
    return by[(split, 'R', i)]['answer'] != by[(split, 'T', i)]['answer']

cal_ids = usable('cal')
cu = np.array([by[('cal', 'R', i)]['u'] for i in cal_ids], float)
cd = np.array([disagree(i, 'cal') for i in cal_ids], int)
tests = []
for q, t in zip(Q, thresholds):
    mask = cu <= tv(t)
    n, k = int(mask.sum()), int(cd[mask].sum())
    pv = float(binom.cdf(k, n, ALPHA)) if n else 1.
    cp = float(beta.ppf(.999, k + 1, n - k)) if n and k < n else 1.
    tests.append({'q': q, 'threshold': t, 'N_cal': len(cu), 'n': n, 'changed': k,
                  'conditional_change_rate': (k / n) if n else None, 'p_value': pv,
                  'CP_upper_0_999': cp, 'accepted': pv <= DELTA, 'coverage': n / len(cu)})
acc = [t for t in tests if t['accepted']]
chosen = acc[-1] if acc else None
best = min(tests, key=lambda t: t['p_value'])
deployment = {'q': chosen['q'] if chosen else 0.0,
              'threshold': chosen['threshold'] if chosen else None,
              'mode': ('fixed_R' if chosen['q'] == 1 else 'selective') if chosen else 'fixed_reference',
              'accepted_q': [t['q'] for t in acc], 'calibration': chosen,
              'smallest_p_value': best['p_value'], 'smallest_p_candidate': best['q'],
              'smallest_p_n': best['n'], 'smallest_p_k': best['changed'],
              'alpha': ALPHA, 'delta_per_test': DELTA, 'tests': 20,
              'family_wise_bound': 20 * DELTA,
              'rule': 'largest accepted q; no acceptance -> always communicate (Text)'}

dev_ids = usable('dev')
du = np.array([by[('dev', 'R', i)]['u'] for i in dev_ids], float)
dd = np.array([disagree(i, 'dev') for i in dev_ids], int)

def auroc(score, label):
    s, y = np.asarray(score, float), np.asarray(label, int)
    if y.sum() == 0 or y.sum() == len(y):
        return None
    r = np.empty(len(s), float)
    order = np.argsort(s, kind='mergesort')
    ss = s[order]; i = 0
    while i < len(ss):
        j = i
        while j + 1 < len(ss) and ss[j + 1] == ss[i]:
            j += 1
        r[order[i:j + 1]] = (i + j) / 2.0 + 1
        i = j + 1
    n1 = int(y.sum()); n0 = len(y) - n1
    return float((r[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0))

ds2 = np.array([by[('dev', 'R', i)]['s2'] for i in dev_ids], float)
ds3 = np.array([by[('dev', 'R', i)]['s3'] for i in dev_ids], float)
aur = {'u': auroc(du, dd), 's2': auroc(ds2, dd), 's3': auroc(ds3, dd)}

tau = tv(deployment['threshold']) if deployment['threshold'] is not None else -float('inf')
omit = du <= tau
dev_route = []
for j, i in enumerate(dev_ids):
    o = bool(omit[j])
    dev_route.append({'id': i, 'u': float(du[j]), 'omitted': o,
                      'policy_answer': by[('dev', 'R', i)]['answer'] if o else by[('dev', 'T', i)]['answer'],
                      'reference_answer': by[('dev', 'T', i)]['answer'],
                      'receiver_answer': by[('dev', 'R', i)]['answer'],
                      'changed': bool(disagree(i, 'dev'))})
n_om = int(omit.sum()); k_om = int(dd[omit].sum())
dev_summary = {'N': len(dev_ids), 'coverage': n_om / len(dev_ids) if dev_ids else None,
               'omitted': n_om, 'changed_among_omitted': k_om,
               'conditional_change_rate': (k_om / n_om) if n_om else None,
               'CP95': ([float(beta.ppf(.025, k_om, n_om - k_om + 1)) if k_om else 0.0,
                         float(beta.ppf(.975, k_om + 1, n_om - k_om)) if k_om < n_om else 1.0]
                        if n_om else None),
               'always_omit_change_rate': float(dd.mean()) if len(dd) else None}

inv = {}
for s in ['fit', 'cal', 'dev']:
    for a in (['R'] if s == 'fit' else ['R', 'T']):
        ids = usable(s)
        inv['%s_%s' % (s, a)] = {'n': len(ids), 'invalid': sum(by[(s, a, i)]['invalid'] for i in ids)}
u1 = {s: sum(by[(s, 'R', i)].get('u_is_invalid', False) for i in usable(s)) for s in ['fit', 'cal', 'dev']}
routes = {}
for s in ['fit', 'cal', 'dev']:
    for a in (['R'] if s == 'fit' else ['R', 'T']):
        for i in usable(s):
            routes.setdefault('%s_%s' % (s, a), {}).setdefault(by[(s, a, i)]['extract_route'], 0)
            routes['%s_%s' % (s, a)][by[(s, a, i)]['extract_route']] += 1
trunc = {}
for s in ['fit', 'cal', 'dev']:
    for a in (['R'] if s == 'fit' else ['R', 'T']):
        ids = usable(s)
        trunc['%s_%s' % (s, a)] = {'at_cap_320': sum(by[(s, a, i)]['n_gen_tokens'] >= 320 for i in ids),
                                   'mean_gen_tokens': float(np.mean([by[(s, a, i)]['n_gen_tokens'] for i in ids])) if ids else None}

def wjl(p, rr):
    with Path(p).open('w') as f:
        for r in rr:
            f.write(json.dumps(r, ensure_ascii=False, allow_nan=False) + '\n')

wjl(OUT / 'SEALED_DEV_ROUTES.jsonl', dev_route)
wjl(OUT / 'SEALED_CAL_TESTS.jsonl', tests)
wjl(OUT / 'SEALED_SCORES.jsonl',
    [{'split': s, 'id': i, 'u': by[(s, 'R', i)]['u'], 's2': by[(s, 'R', i)]['s2'],
      's3': by[(s, 'R', i)]['s3'], 'answer_R': by[(s, 'R', i)]['answer'],
      'answer_T': by[(s, 'T', i)]['answer'] if s != 'fit' else None,
      'invalid_R': by[(s, 'R', i)]['invalid'],
      'u_is_invalid': by[(s, 'R', i)].get('u_is_invalid', False)}
     for s in ['fit', 'cal', 'dev'] for i in usable(s)])
pre = {'utc': utc(), 'row_counts': {'%s %s' % k: [have[k], want[k]] for k in want},
       'complete': all(complete.values()),
       'N_fit': n_fit, 'thresholds': thresholds, 'q_grid': Q,
       'fit_scores_sha256': hashlib.sha256(json.dumps(
           [(i, by[('fit', 'R', i)]['u']) for i in fit_ids]).encode()).hexdigest(),
       'deployment': deployment, 'dev': dev_summary, 'dev_AUROC': aur,
       'cal_disagreement_rate': float(cd.mean()) if len(cd) else None,
       'dev_disagreement_rate': float(dd.mean()) if len(dd) else None,
       'invalid_counts': inv, 'u_eq_1_from_INVALID': u1,
       'extract_routes': routes, 'generation_length': trunc,
       'gold_read': False}
Path(OUT / 'E10_SEALED.json').write_text(json.dumps(pre, indent=2) + '\n')
files = ['E10_SEALED.json', 'SEALED_DEV_ROUTES.jsonl', 'SEALED_CAL_TESTS.jsonl', 'SEALED_SCORES.jsonl']
rec = {'utc': utc(), 'stage': STAGE.name,
       'prereg_sha256': sha(STAGE / 'PREREG_E10.md'),
       'extractor_sha256': sha(STAGE / 'src/e10_extract.py'),
       'prompts_sha256': sha(STAGE / 'src/e10_prompts.py'),
       'records': {Path(p).name: sha(p) for p in sorted(glob.glob(str(STAGE / 'records/main_rank*.jsonl')))},
       'files': {f: sha(OUT / f) for f in files},
       'gold_read': False,
       'note': 'step 5 of PREREG_E10 order of operations; no gold answer has been opened'}
Path(OUT / 'SEAL_RECEIPT.json').write_text(json.dumps(rec, indent=2) + '\n')
print('SEAL', rec['utc'], 'receipt sha256', hashlib.sha256(
    Path(OUT / 'SEAL_RECEIPT.json').read_bytes()).hexdigest())
print('accepted q:', deployment['accepted_q'], '-> chosen', deployment['q'], deployment['mode'])
print('smallest p %.3e at q=%s (n=%d k=%d)' % (best['p_value'], best['q'], best['n'], best['changed']))
print('cal disagreement %.4f  dev disagreement %.4f  AUROC %s' %
      (cd.mean(), dd.mean(), {k: (round(v, 4) if v is not None else None) for k, v in aur.items()}))
