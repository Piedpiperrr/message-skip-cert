"""E10 step 6 (CPU, login node): verify the seal, THEN open the GSM8K gold answers and compute
accuracies.  Run only after src/e10_seal.py has written analysis/SEAL_RECEIPT.json."""
import json, hashlib, datetime, sys
from pathlib import Path
import numpy as np
import pyarrow.parquet as pq
sys.path.insert(0, str(Path(__file__).resolve().parent))
from e10_extract import normalize, fmt

STAGE = Path(__file__).resolve().parents[1]
OUT = STAGE / 'analysis'

def sha(p):
    h = hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()

rec = json.loads((OUT / 'SEAL_RECEIPT.json').read_text())
for f, h in rec['files'].items():
    assert sha(OUT / f) == h, 'seal broken: ' + f
for f, h in rec['records'].items():
    assert sha(STAGE / 'records' / f) == h, 'records changed after seal: ' + f
assert sha(STAGE / 'PREREG_E10.md') == rec['prereg_sha256']
assert sha(STAGE / 'src/e10_extract.py') == rec['extractor_sha256']
print('seal verified, sealed at', rec['utc'])
GOLD_UTC = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
print('opening gold at', GOLD_UTC)

# ---------------------------------------------------------------- gold (first read)
freeze = json.loads((STAGE / 'SPLIT_FREEZE_E10.json').read_text())
tb = pq.read_table(freeze['train_parquet'], columns=['answer'])
ANS = tb.column('answer').to_pylist()
queries = {r['id']: r for r in (json.loads(s) for s in open(STAGE / 'inputs/gsm8k_queries.jsonl'))}

def gold_of(qid):
    """GSM8K gold is the text after the '####' marker; normalized with the same rule as the
    frozen extractor's normalization (this is dataset parsing, not model-output extraction)."""
    raw = ANS[queries[qid]['row']]
    assert '####' in raw
    d = normalize(raw.split('####')[-1].strip())
    assert d is not None, raw
    return fmt(d)

sealed = json.loads((OUT / 'E10_SEALED.json').read_text())
scores = [json.loads(s) for s in open(OUT / 'SEALED_SCORES.jsonl')]
routes = [json.loads(s) for s in open(OUT / 'SEALED_DEV_ROUTES.jsonl')]

def acc_block(rr, split):
    g = np.array([gold_of(r['id']) for r in rr])
    R = np.array([r['answer_R'] for r in rr]); T = np.array([r['answer_T'] for r in rr])
    okR = (R == g).astype(int); okT = (T == g).astype(int)
    return {'N': len(rr), 'accuracy_receiver_only': float(okR.mean()),
            'accuracy_Text': float(okT.mean()),
            'accuracy_oracle_receiver_or_Text': float(np.maximum(okR, okT).mean()),
            'both_correct': int((okR & okT).sum()), 'neither_correct': int(((1 - okR) & (1 - okT)).sum()),
            'receiver_only_correct_Text_wrong': int((okR & (1 - okT)).sum()),
            'Text_correct_receiver_only_wrong': int((okT & (1 - okR)).sum())}

acc = {s: acc_block([r for r in scores if r['split'] == s], s) for s in ['cal', 'dev']}
acc['fit_receiver_only'] = {'N': sum(r['split'] == 'fit' for r in scores),
                            'accuracy_receiver_only': float(np.mean(
                                [r['answer_R'] == gold_of(r['id']) for r in scores if r['split'] == 'fit']))}

# policy vs the Text reference on dev, paired bootstrap (seed 0, 2000 resamples)
g = np.array([gold_of(r['id']) for r in routes])
pol = np.array([r['policy_answer'] for r in routes]) == g
ref = np.array([r['reference_answer'] for r in routes]) == g
rng = np.random.default_rng(0)
idx = rng.integers(0, len(routes), size=(2000, len(routes)))
diffs = pol[idx].mean(1) - ref[idx].mean(1)
policy = {'N': len(routes), 'omitted': int(sum(r['omitted'] for r in routes)),
          'accuracy_policy': float(pol.mean()), 'accuracy_reference_Text': float(ref.mean()),
          'accuracy_diff': float(pol.mean() - ref.mean()),
          'boot95_lo': float(np.quantile(diffs, .025)), 'boot95_hi': float(np.quantile(diffs, .975)),
          'bootstrap': {'seed': 0, 'resamples': 2000, 'paired': True, 'unit': 'dev question'}}

res = {'utc': GOLD_UTC, 'seal_receipt_utc': rec['utc'], 'seal_verified': True,
       'gold_source': freeze['train_parquet'], 'gold_column': 'answer',
       'gold_rule': "text after '####', normalized by the frozen normalizer",
       'accuracy': acc, 'policy_vs_reference_dev': policy,
       'deployment': sealed['deployment'], 'dev': sealed['dev'], 'dev_AUROC': sealed['dev_AUROC'],
       'cal_disagreement_rate': sealed['cal_disagreement_rate'],
       'dev_disagreement_rate': sealed['dev_disagreement_rate'],
       'invalid_counts': sealed['invalid_counts'], 'u_eq_1_from_INVALID': sealed['u_eq_1_from_INVALID'],
       'extract_routes': sealed['extract_routes'], 'generation_length': sealed['generation_length'],
       'row_counts': sealed['row_counts'], 'complete': sealed['complete']}
Path(OUT / 'E10_RESULTS.json').write_text(json.dumps(res, indent=2) + '\n')
Path(OUT / 'GOLD_DECODE.utc').write_text(GOLD_UTC + '\n')
print(json.dumps({'accuracy': acc, 'policy': policy}, indent=2))
