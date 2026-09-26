"""Learned control D for all 14 settings (POST-HOC, reviewer R1), CPU on the login node. Writes results/d_certification*.csv.

Code: P2_R1_CPU_20260919T045556Z/src (data_r1.load_pair_dataset, disagreement, ledger_from_scores, deploy, route_mask, GRID, LABEL)
and the frozen LR of P2_RISK_CALIBRATION_BINARY frozen_config.json (as fit_head.py / P2_R1_CPU item4.py): fit split only,
target 1[o_R != o_b], thresholds = fit-split order statistics, certification alpha=.05, per-candidate p<=.001.
 - 8 settings computed in P2_R1_CPU (small, large x OBQA, ARC x Text, C2C): deployed q, fit threshold and cal n/k are kept
   unchanged from P2_R1_CPU results/item4_learned_D.csv. large/OBQA dev metrics are kept unchanged. For the 6 settings whose dev
   status was 'pending features', dev metrics are NEW: the saved P2_R1_CPU models (results/models/D_*.joblib) are applied to the
   ClusterA E2b dev features.
 - 6 NEW settings (medium x OBQA, ARC x Text, C2C; large MMLU-Pro x Text, C2C): refit exactly as item4.py on the ClusterA E2b
   fit features; calibration on E2b cal features; dev on E2b dev features.
"""
import sys
sys.dont_write_bytecode = True
import json, csv, pathlib, time, warnings
import numpy as np
NEW = pathlib.Path(__file__).resolve().parents[2]
CPU = NEW.parent / 'P2_R1_CPU_20260919T045556Z'
sys.path.insert(0, str(CPU / 'src'))
from data_r1 import *            # P2_R1_CPU helpers (read-only use; nothing is written under P2_R1_CPU)
import joblib
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score

t0 = time.time()
RES = NEW / 'results'; OUTM = RES / 'd_models'; OUTM.mkdir(exist_ok=True)
LR = read(BIN / 'frozen_config.json')['LR']
assert LR == {'penalty': 'l2', 'C': 1, 'solver': 'lbfgs', 'max_iter': 1000, 'random_state': 0, 'class_weight': None}
OLD = {(r['pair'], r['task'], r['reference']): r for r in csvread(CPU / 'results/item4_learned_D.csv')}
E2B = RES / 'e2b'


def e2b_feats(pair, setting):
    out = {}
    for f in sorted((E2B / pair / 'features' / setting).glob('*.npz')):
        with np.load(f, allow_pickle=False) as a:
            m = json.loads(str(a['meta'])); z = a['z'].copy()
        assert m['id'] not in out and z.dtype == np.float32 and np.isfinite(z).all()
        out[m['id']] = z
    return out


def X(feat, ids):
    missing = [i for i in ids if i not in feat]; assert not missing, missing[:5]
    return np.stack([feat[i] for i in ids])


def dev_metrics(model, Xd, dd, q, t):
    sd = model.predict_proba(Xd)[:, 1]
    m = route_mask(sd, q, t); n = int(m.sum()); k = int(dd[m].sum())
    return dict(dev_N=len(dd), dev_omitted=n, dev_changed=k, dev_coverage_pct=round(100 * n / len(dd), 2),
                dev_changed_over_omitted=f'{k}/{n}' if q > 0 else 'N/A (fallback)', dev_AUROC=round(float(roc_auc_score(dd, sd)), 4))


rows, ledg, checks = [], [], []
for pair, task in [('small', 'OBQA'), ('small', 'ARC'), ('medium', 'OBQA'), ('medium', 'ARC'), ('large', 'OBQA'), ('large', 'ARC'), ('large', 'MMLU-Pro')]:
    D = load_pair_dataset(pair, task); ds = {'OBQA': 'obqa', 'ARC': 'arc', 'MMLU-Pro': 'mmlu_pro'}[task]
    for ref in ['Text', 'C2C']:
        s = (pair, task, ref)
        base = dict(pair=pair, task=task, reference=ref, variant='learned_D',
                    historically_tested='historically tested (P2_RISK_CALIBRATION_BINARY D)' if s == ('large', 'OBQA', 'Text') else '')
        if s in OLD:                                            # computed in P2_R1_CPU: keep q, threshold, cal n/k unchanged
            o = OLD[s]
            q = float(o['deployed_q']); t = o['fit_threshold'] or None
            row = dict(base, deployed_q=q, fit_threshold=t, cal_n=o['cal_n'] or '-', cal_k=o['cal_k'] or '-', accepted_q=o['accepted_q'],
                       status_q_cal='P2_R1_CPU (unchanged)')
            if o['dev_status'] == 'evaluated':
                row.update({k: o[k] for k in ['dev_N', 'dev_omitted', 'dev_changed', 'dev_coverage_pct', 'dev_changed_over_omitted', 'dev_AUROC']},
                           status_dev='P2_R1_CPU (unchanged; ClusterB dev features)')
            else:
                model = joblib.load(CPU / f'results/models/D_{pair}_{ds}_{ref}.joblib')
                feat = e2b_feats(pair, f'{pair}_{ds}_dev')
                Xd = X(feat, D['dev']['ids']); dd = disagreement(D['dev'], ref)
                row.update(dev_metrics(model, Xd, dd, q, float(t) if t else None),
                           status_dev=f'NEW: P2_R1_CPU saved model on ClusterA E2b dev features (results/e2b/{pair}/features/{pair}_{ds}_dev)')
        else:                                                   # NEW setting: refit exactly as item4.py
            ff, fc, fd = (e2b_feats(pair, f'{pair}_{ds}_{sp}') for sp in ['fit', 'cal', 'dev'])
            Xf, Xc, Xd = X(ff, D['fit']['ids']), X(fc, D['cal']['ids']), X(fd, D['dev']['ids'])
            yf = disagreement(D['fit'], ref).astype(int); cd = disagreement(D['cal'], ref); dd = disagreement(D['dev'], ref)
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter('always'); model = LogisticRegression(**LR).fit(Xf, yf)
            joblib.dump(model, OUTM / f'D_{pair}_{ds}_{ref}.joblib')
            sf, sc = model.predict_proba(Xf)[:, 1], model.predict_proba(Xc)[:, 1]
            cuts, led = ledger_from_scores(sf, sc, cd)
            q, acc = deploy(led)
            sel = next((r for r in led if r['q'] == q), None) if q > 0 else None
            t = cuts[GRID.index(q)] if q > 0 else None
            row = dict(base, deployed_q=q, fit_threshold=t, cal_n=sel['n'] if sel else '-', cal_k=sel['k'] if sel else '-',
                       accepted_q=';'.join(f'{x:g}' for x in acc), status_q_cal='NEW (this analysis; ClusterA E2b fit/cal features)')
            row.update(dev_metrics(model, Xd, dd, q, t), status_dev='NEW (ClusterA E2b dev features)')
            checks.append(dict(pair=pair, task=task, reference=ref, N_fit=len(yf), fit_positive=int(yf.sum()), N_cal=len(cd), cal_positive=int(cd.sum()),
                               N_dev=len(dd), dev_positive=int(dd.sum()), feature_dim=Xf.shape[1], n_iter=int(model.n_iter_.max()),
                               converged=bool(model.n_iter_.max() < LR['max_iter']), fit_warnings=len(w), cal_AUROC=round(float(roc_auc_score(cd, sc)), 4)))
            for r in led:
                ledg.append(dict(pair=pair, task=task, reference=ref, score='learned_D', **r, label=LABEL))
        row['label'] = LABEL
        rows.append(row)
        print(s, {k: v for k, v in row.items() if k not in ('label', 'accepted_q')}, f'{time.time() - t0:.0f}s', flush=True)
csvout(RES / 'd_certification.csv', rows)
csvout(RES / 'd_certification_new_ledgers.csv', ledg)
csvout(RES / 'd_certification_new_fit_checks.csv', checks)
print('done', f'{time.time() - t0:.0f}s')
