"""E11-a: INVALID decomposition (4 cells) on calibration and development for all 26 settings,
plus the NOT-DEPLOYABLE both-parse diagnostic (frozen fit thresholds, 20 exact binomial tests)."""
from e11_common import *

cells, diag, grid = [], [], []
for s in ALL26:
    D = load(s)
    rec = {}
    for sp in ['cal', 'dev']:
        oR = np.array(D[sp]['oR'], object); ob = np.array(D[sp]['ob'], object)
        iR = oR == INV; ib = ob == INV
        both = iR & ib
        one = iR ^ ib
        bothparse = ~iR & ~ib
        c1 = bothparse & (oR != ob)          # both parse, labels differ -> disagreement
        c2 = bothparse & (oR == ob)          # both parse, labels agree   -> agreement
        c3 = one                             # exactly one INVALID        -> disagreement (frozen convention)
        c4 = both                            # both INVALID               -> agreement    (frozen convention)
        dis = oR != ob                       # frozen convention: c1 | c3
        assert (dis == (c1 | c3)).all() and (~dis == (c2 | c4)).all()
        cells.append(dict(setting=sname(s), split=sp, N=len(oR),
                          cell1_bothparse_differ=int(c1.sum()), cell2_bothparse_agree=int(c2.sum()),
                          cell3_exactly_one_INVALID=int(c3.sum()), cell4_both_INVALID=int(c4.sum()),
                          disagreements_frozen=int(dis.sum()),
                          cell3_share_of_disagreements=f'{c3.sum() / dis.sum():.4f}' if dis.sum() else '',
                          receiver_only_INVALID=int(iR.sum()), receiver_only_INVALID_pct=f'{100 * iR.mean():.2f}',
                          reference_INVALID=int(ib.sum()), reference_INVALID_pct=f'{100 * ib.mean():.2f}',
                          only_receiver_INVALID=int((iR & ~ib).sum()), only_reference_INVALID=int((~iR & ib).sum()),
                          disagreement_rate_frozen=f'{dis.mean():.5f}',
                          both_INVALID_treated_as='agreement (frozen convention)', label=LABEL))
        rec[sp] = (D[sp]['u'], dis, bothparse)

    # ---- both-parse diagnostic: frozen thresholds, questions in cells (1) and (2) only
    ucal, dcal, kcal = rec['cal']
    led = ledger_rows(ucal, dcal, D['cuts'], kcal)
    q, acc = largest_accepted(led)
    for r in led:
        grid.append(dict(setting=sname(s), q=r['q'], threshold=r['threshold'], n=r['n'], k=r['k'],
                         p=f"{r['p']:.6g}", CP999=f"{r['CP']:.6g}", accepted=r['accepted'],
                         deployable=False, label=LABEL))
    udev, ddev, kdev = rec['dev']
    dv, uv = ddev[kdev], udev[kdev]
    cov = covall = chg = ''
    if q > 0:
        m = uv <= tv(D['cuts'][GRID.index(q)])
        cov = f'{100 * m.mean():.2f}'; covall = f'{100 * m.sum() / len(udev):.2f}'
        chg = f'{dv[m].mean():.5f}' if m.sum() else ''
        chgtxt = f'{int(dv[m].sum())}/{int(m.sum())}'
    else:
        chgtxt = ''
    diag.append(dict(setting=sname(s), original_q=D['q0'],
                     N_cal=len(ucal), N_cal_bothparse=int(kcal.sum()),
                     N_dev=len(udev), N_dev_bothparse=int(kdev.sum()),
                     bothparse_accepted_q=q if q > 0 else 'no candidate accepted',
                     bothparse_all_accepted_q=';'.join(f'{x:g}' for x in acc) or 'none',
                     dev_disagreement_bothparse=f'{dv.mean():.5f}', dev_disagreements_bothparse=f'{int(dv.sum())}/{len(dv)}',
                     dev_disagreement_frozen_all=f'{ddev.mean():.5f}',
                     dev_AUROC_bothparse=f'{auroc(dv, uv):.5f}',
                     dev_coverage_pct_of_bothparse=cov, dev_coverage_pct_of_all_dev=covall,
                     conditional_change_rate_at_q=chg, changed_over_omitted=chgtxt,
                     outcome_vs_original=('unchanged' if (q > 0) == (D['q0'] > 0) else
                                          ('certifies under both-parse (was fallback)' if q > 0 else
                                           'LOSES certification under both-parse')),
                     deployable=False, diagnostic_note='NOT DEPLOYABLE: the both-parse filter reads the reference output',
                     label=LABEL))
    print(f"{sname(s):26s} cal bothparse {int(kcal.sum())}/{len(ucal)}  q_bp={q!s:<5} (orig {D['q0']})  "
          f"dev dis {dv.mean():.4f} (frozen {ddev.mean():.4f})  AUROC {auroc(dv, uv):.4f}")

csvout(RES / 'E11a_invalid_decomposition.csv', cells)
csvout(RES / 'E11a_bothparse_diagnostic.csv', diag)
csvout(RES / 'E11a_bothparse_grid.csv', grid)

# ---- aggregate shares of disagreement driven by exactly one INVALID
def share(group, split):
    rr = [r for r in cells if r['split'] == split and sname_in(r['setting'], group)]
    v = [float(r['cell3_share_of_disagreements']) for r in rr if r['cell3_share_of_disagreements']]
    tot_d = sum(r['disagreements_frozen'] for r in rr); tot_c3 = sum(r['cell3_exactly_one_INVALID'] for r in rr)
    return min(v), max(v), tot_c3 / tot_d, len(rr)


def sname_in(nm, group): return nm in {sname(s) for s in group}


agg = []
for nm, group in [('18 main settings', MAIN18), ('7 cross-family settings', XSET), ('Text+fact (E6)', [FACT])]:
    for split in ['cal', 'dev']:
        lo, hi, pooled, n = share(group, split)
        agg.append(dict(group=nm, split=split, n_settings=n, min_cell3_share=f'{lo:.4f}', max_cell3_share=f'{hi:.4f}',
                        pooled_cell3_share=f'{pooled:.4f}', label=LABEL))
        print(f'{nm:26s} {split}: cell-3 share range {lo:.4f}-{hi:.4f}, pooled {pooled:.4f}')
csvout(RES / 'E11a_cell3_share_aggregate.csv', agg)
