"""E5-e: cross-family INVALID decomposition and a valid-only diagnostic (descriptive, NOT deployable)."""
from r2_common import *
import numpy as np
import data_r1
from common_r1 import tv
from sklearn.metrics import roc_auc_score

x2 = load_x2()
x1 = load_x1()


def xcuts(csvpath, setting):
    return [r['threshold'] for r in csvread(csvpath) if r['setting'] == setting]


def get(s):
    pair, task, ref = s
    ds = BENCH[task]
    if pair == 'X2-OLMo':
        D = x2[ds]
        pick = lambda sp: (D[sp]['ids'], np.array(D[sp]['u']), D[sp]['oR'], D[sp]['oT'])
        return ds, pick, xcuts(XFAM / 'results/analysis/certification_ledger_60.csv', f'{ds}/Text')
    D = x1[ds]
    key = 'oT' if ref == 'Text' else 'oC'
    pick = lambda sp: (D[sp]['ids'], np.array(D[sp]['u']), D[sp]['oR'], D[sp][key])
    return ds, pick, xcuts(X1 / 'results/analysis/certification_ledger_80.csv', f'{ds}/{ref}')


split_rows, diag_rows, grid = [], [], []
for s in XSETTINGS:
    ds, pick, cuts = get(s)
    rec = {}
    for sp in ['cal', 'dev']:
        ids, u, oR, ob = pick(sp)
        oR = np.array(oR, object); ob = np.array(ob, object)
        dis = oR != ob
        bothvalid = (oR != INV) & (ob != INV)
        onlyR = (oR == INV) & (ob != INV)
        onlyB = (oR != INV) & (ob == INV)
        bothinv = (oR == INV) & (ob == INV)
        split_rows.append(dict(setting=sname(s), split=sp, N=len(ids), disagreements=int(dis.sum()),
                               both_valid_and_different=int((dis & bothvalid).sum()),
                               only_R_INVALID=int(onlyR.sum()), only_reference_INVALID=int(onlyB.sum()),
                               both_INVALID_counted_as_agreement=int(bothinv.sum()),
                               R_INVALID=int((oR == INV).sum()), ref_INVALID=int((ob == INV).sum()),
                               R_INVALID_pct=f'{100 * (oR == INV).mean():.2f}', ref_INVALID_pct=f'{100 * (ob == INV).mean():.2f}',
                               disagreement_rate=f'{dis.mean():.4f}', label=LABEL))
        rec[sp] = (u, dis, bothvalid)
    # valid-only diagnostic: frozen fit thresholds, 20 tests on valid-only calibration questions
    ucal, dcal, vcal = rec['cal']
    led = ledger_rows(ucal, dcal, cuts, vcal)
    acc = [r['q'] for r in led if r['accepted']]
    q = acc[-1] if acc else 0.
    for r in led:
        grid.append(dict(setting=sname(s), q=r['q'], n=r['n'], k=r['k'], p=f"{r['p']:.6g}", accepted=r['accepted'], label=LABEL))
    udev, ddev, vdev = rec['dev']
    dv, uv = ddev[vdev], udev[vdev]
    auc = roc_auc_score(dv, uv) if 0 < dv.sum() < len(dv) else float('nan')
    cov = ''
    if q > 0:
        t = cuts[GRID.index(q)]
        md = data_r1.route_mask(uv, q, t) if False else (uv <= tv(t))
        cov = f'{100 * md.mean():.1f}'
    diag_rows.append(dict(setting=sname(s), N_cal=len(ucal), N_cal_valid_only=int(vcal.sum()),
                          valid_only_deployed_q=q, valid_only_accepted_q=';'.join(f'{x:g}' for x in acc) or 'none',
                          N_dev=len(udev), N_dev_valid_only=int(vdev.sum()),
                          dev_disagreement_valid_only=f'{dv.mean():.4f}', dev_disagreements_valid_only=f'{int(dv.sum())}/{len(dv)}',
                          dev_disagreement_all=f'{ddev.mean():.4f}', valid_only_AUROC=f'{auc:.3f}',
                          valid_only_dev_coverage_pct=cov, deployable=False, label=LABEL))
    print(f"{sname(s):24s} cal {int(vcal.sum())}/{len(ucal)} valid  q_valid_only={q}  dev dis {dv.mean():.4f} (all {ddev.mean():.4f})  AUROC {auc:.3f}")

csvout(RES / 'e5e_disagreement_split.csv', split_rows)
csvout(RES / 'e5e_valid_only_diagnostic.csv', diag_rows)
csvout(RES / 'e5e_valid_only_grid.csv', grid)
