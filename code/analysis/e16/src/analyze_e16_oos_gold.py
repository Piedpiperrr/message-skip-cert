"""E16-1/E16-2 gold stage only (the sealed stage of analyze_e16_oos.py completed and wrote SEAL_RECEIPT.json 19:11:41Z and GOLD_ACCESS.json
19:11:44Z; its process then aborted inside pyarrow's threaded parquet read on the login node). This script verifies every sealed file against
SEAL_RECEIPT.json, reloads the routes (o_R, o_ref, omitted) from the sealed routes files, reads the answer key single-threaded, and writes
OOS_RESULTS.json / oos_results.csv. Nothing sealed is rewritten."""
import sys
sys.dont_write_bytecode = True
import csv
from xfam_common import *
import numpy as np
import pyarrow.parquet as pq
A = X / 'results/analysis_oos'; seal = read(A / 'SEAL_RECEIPT.json')
for p, h in seal['files'].items(): assert sha(X / p) == h, p
res = read(A / 'OOS_PRE_GOLD.json')['results']
key = {'Llama-3.1-8B OBQA/Text (q=.60) on 744 held-out OBQA': 'llama_obqa', 'Llama-3.1-8B ARC/Text (q=.70) on 1,172 ARC test': 'llama_arc', 'medium ARC/C2C (q=.60) on 1,172 ARC test': 'medium_arc_C'}
tb = pq.read_table(DATA_ROOT / 'c2c_reproduction_assets/datasets/allenai--openbookqa/main/train-00000-of-00001.parquet', columns=['id', 'answerKey'], use_threads=False)
G = dict(zip(tb.column('id').to_pylist(), tb.column('answerKey').to_pylist()))
G.update({r['id']: r['gold'] for r in jl(SEALED / 'inputs/evaluation_gold_after_prediction_freeze.jsonl')})
for name, k in key.items():
    R = jl(A / f'routes_{k}.jsonl'); ids = [r['id'] for r in R]
    om = np.array([r['omitted'] for r in R]); oR = np.array([r['o_R'] for r in R], object); ob = np.array([r['o_ref'] for r in R], object)
    y = np.array([G[i] for i in ids], object); pol = np.where(om, oR, ob)
    aR, aB, aP = (oR == y).astype(float), (ob == y).astype(float), (pol == y).astype(float)
    N = len(y); idx = np.random.default_rng(0).integers(0, N, (2000, N)); dl = aP - aB; boot = dl[idx].mean(axis=1); lo, hi = [float(v) for v in np.quantile(boot, [.025, .975])]
    res[name].update(acc_R=float(aR.mean()), acc_ref=float(aB.mean()), acc_policy=float(aP.mean()), correct_R=int(aR.sum()), correct_ref=int(aB.sum()), correct_policy=int(aP.sum()),
                     delta_acc=float(dl.mean()), delta_acc_boot95_lo=lo, delta_acc_boot95_hi=hi)
save(A / 'OOS_RESULTS.json', dict(utc=utc(), seal_receipt_utc=seal['utc'], gold_first_access_utc=read(A / 'GOLD_ACCESS.json')['utc'], results=res))
with open(A / 'oos_results.csv', 'w', newline='') as fh:
    w = csv.DictWriter(fh, fieldnames=list(next(iter(res.values())).keys())); w.writeheader(); w.writerows(res.values())
print('GOLD_DONE')
