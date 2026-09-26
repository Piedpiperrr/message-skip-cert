"""E16-1 / E16-2 analysis (CPU, login node), exactly as PREREG.md. Order: (0) verify results/MANIFEST_jobA.sha256; (1) routes, changes, test,
official-extraction change rate, INVALID and u == 0 counts from outputs only -> results/analysis_oos/*.json + routes files, sealed in
SEAL_RECEIPT.json (sha256 + UTC); (2) only then the answer key: OBQA held-out = allenai--openbookqa main/train parquet columns id, answerKey
(as E9b e9b_decode.py); ARC test = sealed run inputs/evaluation_gold_after_prediction_freeze.jsonl field gold (display labels).
Policies (frozen numeric tau, u <= tau omits): Llama OBQA/Text (X3 q=.60), Llama ARC/Text (X3 q=.70), medium ARC/C2C (stage-1 q=.60).
Change = o_R != o_ref with INVALID an ordinary label. p = P[Bin(n, .05) <= k]. CP = two-sided 95% Clopper-Pearson.
Delta acc = policy - reference, paired bootstrap default_rng(0).integers(0, N, (2000, N)), 2.5/97.5% quantiles."""
import sys
sys.dont_write_bytecode = True
import csv, collections, importlib.util
from xfam_common import *
import numpy as np
from scipy.stats import binom, beta
A = X / 'results/analysis_oos'; A.mkdir(parents=True, exist_ok=True)
INV = 'INVALID'
# ---- (0) manifest
man = X / 'results/MANIFEST_jobA.sha256'; bad = []
for line in man.read_text().splitlines():
    if line.strip() and not line.startswith('#'):
        h, p = line.split(None, 1)
        if sha(X / 'results' / p.strip()) != h: bad.append(p)
assert not bad, bad
spec = importlib.util.spec_from_file_location('parsers_r2', ROOT / 'P2_R2_CPU_20260919T220412Z/scripts/parsers_r2.py'); PR = importlib.util.module_from_spec(spec)
sys.path.insert(0, str(ROOT / 'P2_R2_CPU_20260919T220412Z/scripts')); spec.loader.exec_module(PR)
parse = parser()
assert sha(MED.parent / 'protocol/scoring_v2.py') == PARSER_SHA   # the medium runtime's parser copy is the frozen V2 parser


def cp95(k, n): return (float(beta.ppf(.025, k, n - k + 1)) if k > 0 else 0.0, float(beta.ppf(.975, k + 1, n - k)) if k < n else 1.0) if n else (float('nan'),) * 2


xt = {r['setting']: r for r in csv.DictReader(open(X3 / 'results/analysis/dev_table_pre_gold.csv'))}
assert sha(X3 / 'results/analysis/dev_table_pre_gold.csv') == read(X3 / 'results/analysis/CERT_HASHES.json')['files']['dev_table_pre_gold.csv']
dep = read(MED / 'deployments/arc_C.json')
# stored development / calibration context
medcal = jl(MED / 'calibration/arc_C_observations.jsonl'); medA = {(r['id'], r['action']): r for r in jl(MED / 'actions/arc_dev.jsonl')}
med_dev_ids = read(MED.parent / 'splits/arc_dev_ids.json'); med_routes = jl(MED / 'development/arc_C_routes.jsonl')
POL = {
    'Llama-3.1-8B OBQA/Text (q=.60) on 744 held-out OBQA': dict(files=sorted((X / 'results/e16_1').glob('shard*.jsonl')), split='holdout744', ref='T', tau=float(xt['X3 obqa/Text']['threshold']),
        dev=(int(xt['X3 obqa/Text']['dev_omitted']), int(xt['X3 obqa/Text']['N_dev'])), cal=(int(xt['X3 obqa/Text']['cal_disagreements']), int(xt['X3 obqa/Text']['N_cal'])),
        devdis=(int(xt['X3 obqa/Text']['dev_disagreements']), int(xt['X3 obqa/Text']['N_dev'])), key='llama_obqa'),
    'Llama-3.1-8B ARC/Text (q=.70) on 1,172 ARC test': dict(files=sorted((X / 'results/e16_1').glob('shard*.jsonl')), split='arc_test', ref='T', tau=float(xt['X3 arc/Text']['threshold']),
        dev=(int(xt['X3 arc/Text']['dev_omitted']), int(xt['X3 arc/Text']['N_dev'])), cal=(int(xt['X3 arc/Text']['cal_disagreements']), int(xt['X3 arc/Text']['N_cal'])),
        devdis=(int(xt['X3 arc/Text']['dev_disagreements']), int(xt['X3 arc/Text']['N_dev'])), key='llama_arc'),
    'medium ARC/C2C (q=.60) on 1,172 ARC test': dict(files=[X / 'results/e16_2/e16_2_medium_arc_test.jsonl'], split=None, ref='C', tau=float(dep['threshold']),
        dev=(sum(r['selected'] == 'R' for r in med_routes), len(med_routes)), cal=(sum(r['disagreement'] for r in medcal), len(medcal)),
        devdis=(sum(medA[(i, 'R')]['answer'] != medA[(i, 'C')]['answer'] for i in med_dev_ids), len(med_dev_ids)), key='medium_arc_C')}
pops = {'holdout744': [r['id'] for r in jl(X / 'records/populations/holdout744.jsonl')], 'arc_test': [r['id'] for r in jl(X / 'records/populations/arc_test.jsonl')]}
legal = {r['id']: r['legal_labels'] for f in ['holdout744', 'arc_test'] for r in jl(X / f'records/populations/{f}.jsonl')}
res, routes_files, U = {}, [], {}
for name, c in POL.items():
    recs = {r['id']: r for f in c['files'] for r in jl(f) if c['split'] is None or r['split'] == c['split']}
    ids = pops[c['split'] or 'arc_test']; missing = [i for i in ids if i not in recs]; errs = [i for i in ids if i in recs and recs[i].get('runtime_error')]
    assert not missing and not errs, (name, len(missing), len(errs))
    if c['ref'] == 'T':
        oR = np.array([recs[i]['R']['parsed'] for i in ids], object); ob = np.array([recs[i]['T']['parsed'] for i in ids], object)
        rawR = [recs[i]['R']['raw'] for i in ids]; rawB = [recs[i]['T']['raw'] for i in ids]
    else:
        oR = np.array([recs[i]['R']['answer'] for i in ids], object); ob = np.array([recs[i]['C']['answer'] for i in ids], object)
        rawR = [recs[i]['R']['raw'] for i in ids]; rawB = [recs[i]['C']['raw'] for i in ids]
        v2chk = sum((lambda p: p['answer'] if p['valid'] else INV)(parse(x, legal[i])) == y for x, i, y in zip(rawR + rawB, ids + ids, list(oR) + list(ob)))
    u = np.array([recs[i]['P']['ProbeMax'] for i in ids], float); om = u <= c['tau']; d = oR != ob
    N, n, k = len(ids), int(om.sum()), int(d[om].sum()); lo, hi = cp95(k, n); p = float(binom.cdf(k, n, .05)) if n else 1.0
    app = np.array([PR.official_applicable(legal[i]) for i in ids])
    oRo = np.array([PR.label_official(x or '', legal[i]) if a else None for x, i, a in zip(rawR, ids, app)], object)
    obo = np.array([PR.label_official(x or '', legal[i]) if a else None for x, i, a in zip(rawB, ids, app)], object)
    mo = om & app; ko, no = int((oRo[mo] != obo[mo]).sum()), int(mo.sum()); olo, ohi = cp95(ko, no)
    r = dict(policy=name, reference='Text' if c['ref'] == 'T' else 'C2C', frozen_tau=c['tau'], N=N, omitted_n=n, coverage=n / N, dev_omitted=c['dev'][0], dev_N=c['dev'][1], dev_coverage=c['dev'][0] / c['dev'][1],
             changed_k=k, change_rate=k / n if n else float('nan'), CP95_lo=lo, CP95_hi=hi, p_single_test=p, p_le_001=p <= .001, p_le_025=p <= .025,
             branch='passes (CP upper < 5%)' if hi < .05 else ('fails (CP lower > 5%)' if lo > .05 else 'inconclusive'),
             always_omit_change_rate=float(d.mean()), always_omit_changes=int(d.sum()), cal_disagreement=c['cal'][0] / c['cal'][1], cal_disagreements=f"{c['cal'][0]}/{c['cal'][1]}",
             dev_disagreement=c['devdis'][0] / c['devdis'][1], dev_disagreements=f"{c['devdis'][0]}/{c['devdis'][1]}",
             INVALID_R=int((oR == INV).sum()), INVALID_ref=int((ob == INV).sum()), INVALID_R_omitted=int((oR[om] == INV).sum()), INVALID_ref_omitted=int((ob[om] == INV).sum()),
             u0_all=int((u == 0).sum()), u0_omitted=int(((u == 0) & om).sum()),
             official_AD_items=int(app.sum()), official_omitted_n=no, official_changed_k=ko, official_rate=ko / no if no else float('nan'), official_CP95_lo=olo, official_CP95_hi=ohi,
             medium_parser_recheck=(v2chk if c['ref'] == 'C' else None))
    res[name] = r; U[name] = dict(ids=ids, om=om, oR=oR, ob=ob)
    rf = A / f"routes_{c['key']}.jsonl"
    with open(rf, 'w') as f:
        for i, uu, m, a_, b_ in zip(ids, u, om, oR, ob): f.write(json.dumps(dict(id=i, u=float(uu), omitted=bool(m), o_R=a_, o_ref=b_, changed=bool(m and a_ != b_))) + '\n')
    routes_files.append(rf)
save(A / 'OOS_PRE_GOLD.json', dict(utc=utc(), results=res))
save(A / 'SEAL_RECEIPT.json', dict(utc=utc(), note='routes, changes, tests and all output files hashed before the answer key is read', answer_key_read=False,
                                   files={str(p.relative_to(X)): sha(p) for p in routes_files + [A / 'OOS_PRE_GOLD.json'] + sorted((X / 'results/e16_1').glob('*.jsonl')) + [X / 'results/e16_2/e16_2_medium_arc_test.jsonl']}))
print('SEALED', json.dumps(res, indent=1, default=str), flush=True)
# ---- (2) answer key (only after SEAL_RECEIPT.json)
import pyarrow.parquet as pq
save(A / 'GOLD_ACCESS.json', dict(utc=utc(), event='answer key read after SEAL_RECEIPT.json', seal_receipt_sha256=sha(A / 'SEAL_RECEIPT.json')))
tb = pq.read_table(DATA_ROOT / 'c2c_reproduction_assets/datasets/allenai--openbookqa/main/train-00000-of-00001.parquet', columns=['id', 'answerKey'])
G = dict(zip(tb.column('id').to_pylist(), tb.column('answerKey').to_pylist()))
G.update({r['id']: r['gold'] for r in jl(SEALED / 'inputs/evaluation_gold_after_prediction_freeze.jsonl')})
for name, x in U.items():
    y = np.array([G[i] for i in x['ids']], object); pol = np.where(x['om'], x['oR'], x['ob'])
    aR, aB, aP = (x['oR'] == y).astype(float), (x['ob'] == y).astype(float), (pol == y).astype(float)
    N = len(y); idx = np.random.default_rng(0).integers(0, N, (2000, N)); dlt = aP - aB; boot = dlt[idx].mean(axis=1); blo, bhi = [float(v) for v in np.quantile(boot, [.025, .975])]
    res[name].update(acc_R=float(aR.mean()), acc_ref=float(aB.mean()), acc_policy=float(aP.mean()), correct_R=int(aR.sum()), correct_ref=int(aB.sum()), correct_policy=int(aP.sum()),
                     delta_acc=float(dlt.mean()), delta_acc_boot95_lo=blo, delta_acc_boot95_hi=bhi)
save(A / 'OOS_RESULTS.json', dict(utc=utc(), results=res))
with open(A / 'oos_results.csv', 'w', newline='') as fh:
    w = csv.DictWriter(fh, fieldnames=list(next(iter(res.values())).keys())); w.writeheader(); w.writerows(res.values())
print('GOLD', json.dumps({k: {a: v[a] for a in ['acc_R', 'acc_ref', 'acc_policy', 'delta_acc', 'delta_acc_boot95_lo', 'delta_acc_boot95_hi']} for k, v in res.items()}, indent=1))
