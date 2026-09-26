"""E9B shared: the 744-row population, the frozen policies, and the validation reference records."""
import json, hashlib
from pathlib import Path

R = Path('$DATA_DIR')
STAGE = Path(__file__).resolve().parents[1]
BOUND = R / 'P2_CONFIDENCE_REFERENCE_BOUNDARIES_20260914T165012Z'
ZERO  = R / 'P2_ZERO_GOLD_CONTROLS_20260914T065145Z'
P10   = R / 'P2_10_20260911T122423Z'
MEDS  = R / 'P2_MEDIUM_PAIR_BOUNDARY_EXTENSION_STAGE1_20260915T144407Z'
MED   = MEDS / 'execution_retry1_20260915T164957Z'
E6    = R / 'P2_R2_GPU_20260919T220941Z/e6'

def rd(p): return json.loads(Path(p).read_text())
def jl(p):
    with Path(p).open() as f: return [json.loads(s) for s in f if s.strip()]

def population():
    """The 744 held-out OBQA questions, id/question/choices only (never sealed; see the amendment)."""
    return jl(STAGE / 'inputs/holdout_744_queries.jsonl')

def facts():
    return rd(STAGE / 'inputs/obqa_fact1.json')

# Frozen policies under test. Thresholds are NOT refitted.
POLICIES = [
 {'key': 'medium_obqa_C_q55',   'pair': 'medium', 'action': 'C',  'q': 0.55,
  'threshold': 1.3113021850585938e-06, 'source': str(MED / 'deployments/obqa_C.json')},
 {'key': 'medium_obqa_C_q50',   'pair': 'medium', 'action': 'C',  'q': 0.50,
  'threshold': 2.384185791015625e-07, 'source': str(R / 'P2_R2_CPU_20260919T220412Z/followup/results/f1c_medium_obqa_C2C_dev.json'),
  'note': 'exposure-free q=.50 threshold, reported alongside q=.55'},
 {'key': 'large_obqa_T_q80',    'pair': 'large',  'action': 'T',  'q': 0.80,
  'threshold': 1.170039176940918e-03, 'source': str(BOUND / 'deployments/large_obqa_T.json')},
 {'key': 'large_obqa_C_q80',    'pair': 'large',  'action': 'C',  'q': 0.80,
  'threshold': 1.170039176940918e-03, 'source': str(BOUND / 'deployments/large_obqa_C.json')},
 {'key': 'large_obqa_TF_q75',   'pair': 'large',  'action': 'TF', 'q': 0.75,
  'threshold': 2.611875534057617e-04, 'source': str(E6 / 'analysis/E6_RESULTS.json')},
]

ACTIONS = {'large': ['probe', 'R', 'T', 'C', 'TF'], 'medium': ['probe', 'R', 'C']}

# ---------------- validation references (saved OBQA fit rows) ----------------
_NATIVE = {'R': 'receiver_only', 'T': 'text', 'C': 'c2c'}

def fit_ids(n=None):
    ids = rd(BOUND / 'splits/obqa_fit_representatives.json')
    return ids[:n] if n else ids

def reference_rows(pair, action, n=8):
    """Saved outputs for the first n OBQA fit rows of this pair+action, for bit-for-bit checking."""
    want = fit_ids()
    if pair == 'large':
        if action == 'probe':
            by = {r['id']: r for r in jl(ZERO / 'records/probe_records.jsonl') if r['split'] == 'fit'}
        elif action == 'TF':
            by = {r['id']: r for r in jl(E6 / 'smoke/e6_smoke.jsonl')}
        else:
            by = {r['id']: r for r in jl(P10 / 'results/large/obqa/train_historical_rtc.jsonl')
                  if r['action'] == _NATIVE[action]}
    else:
        if action == 'probe':
            by = {r['id']: r for r in jl(MED / 'probes/obqa_fit.jsonl')}
        else:
            by = {r['id']: r for r in jl(MED / 'actions/obqa_fit.jsonl') if r['action'] == action}
    ordered = [i for i in want if i in by][:n]
    return [(i, by[i]) for i in ordered]

def expected_text_and_ids(pair, action, rec):
    """(raw_answer, generated_token_ids) of a saved record, across the differing record schemas."""
    if action == 'probe':
        return None, None
    if pair == 'medium':
        out = rec['output'] if isinstance(rec['output'], dict) else json.loads(rec['output'].replace("'", '"'))
        return out['raw_answer'], out['generated_token_ids']
    if action == 'TF':
        return rec['raw_answer'], rec['generated_token_ids']
    return rec['raw_answer'], rec['generated_token_ids']
