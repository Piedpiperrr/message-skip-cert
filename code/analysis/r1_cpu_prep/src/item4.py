"""Item 4 (POST-HOC): learned control D refit per setting/reference exactly as P2_RISK_CALIBRATION_BINARY fit_head.py
(E1 z features, LogisticRegression(**frozen LR), fit split only, target 1[o_R != o_b]); thresholds/certification as item 3(c)."""
import time, hashlib, warnings, joblib
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from data_r1 import *

t0 = time.time()
CFG = read(BIN / 'frozen_config.json'); LR = CFG['LR']
assert LR == {'penalty': 'l2', 'C': 1, 'solver': 'lbfgs', 'max_iter': 1000, 'random_state': 0, 'class_weight': None}
FIDX = {(r['pair'], r['dataset'], r['id']): r for r in csvread(E1 / 'FEATURE_INDEX.csv')}
DIDX = {r['id']: r for r in csvread(BIN / 'features/DEV_FEATURE_INDEX.csv')}


def sha(p):
    h = hashlib.sha256(); h.update(Path(p).read_bytes()); return h.hexdigest()


def feats(index, keys):
    X = []
    for k in keys:
        r = index[k]; f = Path(r['path']); assert sha(f) == r['sha256']
        with np.load(f, allow_pickle=False) as a: z = a['z']; m = json.loads(str(a['meta']))
        assert m['id'] == (k[2] if isinstance(k, tuple) else k) and z.dtype == np.float32 and np.isfinite(z).all()
        X.append(z)
    return np.stack(X)


L = ledgers()
results, ledg, checks = [], [], []
for pair in ['small', 'large']:
    for task in ['OBQA', 'ARC']:
        D = load_pair_dataset(pair, task); ds = task.lower()
        Xf = feats(FIDX, [(pair, ds, i) for i in D['fit']['ids']]); Xc = feats(FIDX, [(pair, ds, i) for i in D['cal']['ids']])
        has_dev = (pair, ds) == ('large', 'obqa')
        if has_dev:
            assert D['dev']['ids'] == read(BIN / 'splits/dev_ids.json'); Xd = feats(DIDX, D['dev']['ids'])
        for ref in ['Text', 'C2C']:
            s = (pair, task, ref)
            yf = disagreement(D['fit'], ref).astype(int); cd = disagreement(D['cal'], ref)
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter('always'); model = LogisticRegression(**LR).fit(Xf, yf)
            joblib.dump(model, P / f'results/models/D_{pair}_{ds}_{ref}.joblib') if (P / 'results/models').exists() else None
            sf, sc = model.predict_proba(Xf)[:, 1], model.predict_proba(Xc)[:, 1]
            cuts, rows = ledger_from_scores(sf, sc, cd)
            q, acc = deploy(rows)
            chk = dict(pair=pair, task=task, reference=ref, N_fit=len(yf), fit_positive=int(yf.sum()), feature_dim=Xf.shape[1],
                       n_iter=int(model.n_iter_.max()), converged=bool(model.n_iter_.max() < LR['max_iter']), fit_warnings=len(w),
                       cal_AUROC=roc_auc_score(cd, sc))
            if s == ('large', 'OBQA', 'Text'):  # compare with the historical frozen head
                hist = joblib.load(BIN / 'models/disagreement.joblib')
                hd = [r['d'] for r in jl(BIN / 'inputs/candidate_fit.jsonl')]
                chk.update(target_equals_historical=hd == yf.tolist(),
                           max_abs_prob_diff_vs_historical_fit=float(np.abs(hist.predict_proba(Xf)[:, 1] - sf).max()),
                           max_abs_prob_diff_vs_historical_cal=float(np.abs(hist.predict_proba(Xc)[:, 1] - sc).max()),
                           thresholds_equal_historical=[str(a) for a in cuts] == [str(b) for b in read(BIN / 'models/thresholds.json')['D']])
                hl = [r for r in csvread(BIN / 'summary/calibration_100.csv') if r['family'] == 'D']
                chk['ledger_equals_historical'] = all((int(h['n_R']), int(h['changed'])) == (m['n'], m['k']) for h, m in zip(hl[-20:], rows))
            sel = next((r for r in rows if r['q'] == q), None) if q > 0 else None
            row = dict(pair=pair, task=task, reference=ref, variant='learned_D', deployed_q=q, fit_threshold=cuts[GRID.index(q)] if q > 0 else None,
                       cal_n=sel['n'] if sel else None, cal_k=sel['k'] if sel else None, accepted_q=';'.join(f'{x:g}' for x in acc))
            if has_dev:
                sd = model.predict_proba(Xd)[:, 1]; dd = disagreement(D['dev'], ref)
                m = route_mask(sd, q, cuts[GRID.index(q)] if q > 0 else None); n = int(m.sum()); k = int(dd[m].sum())
                row.update(dev_N=len(dd), dev_omitted=n, dev_changed=k, dev_coverage_pct=100 * n / len(dd),
                           dev_changed_over_omitted=f'{k}/{n}' if q > 0 else 'N/A', dev_AUROC=roc_auc_score(dd, sd), dev_status='evaluated')
            else:
                row.update(dev_status='pending features (no dev E1 features saved)')
            row['historically_tested'] = 'historically tested (P2_RISK_CALIBRATION_BINARY D)' if s == ('large', 'OBQA', 'Text') else ''
            row['label'] = LABEL
            results.append(row); checks.append(chk)
            for r in rows: ledg.append(dict(pair=pair, task=task, reference=ref, score='learned_D', **r, label=LABEL))
            print(s, {k: v for k, v in row.items() if k not in ('label', 'accepted_q')}, chk, f'{time.time()-t0:.0f}s', flush=True)
csvout(P / 'results/item4_learned_D.csv', results)
csvout(P / 'results/item4_learned_D_ledgers.csv', ledg)
csvout(P / 'results/item4_fit_checks.csv', checks)
print('done', f'{time.time()-t0:.0f}s')
