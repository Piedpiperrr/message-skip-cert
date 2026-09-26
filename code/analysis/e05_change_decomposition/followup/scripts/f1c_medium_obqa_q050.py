"""E5 follow-up (c): medium/OBQA/C2C on development at the largest clean-accepted q = .50.

Same quantities as the paper's reference-correction table (tab:omit_keep) plus omitted, changed and
the correct-answer counts of the policy and of the fixed reference.  The original deployed q = .55 is
computed by the same code as a check that it reproduces the published row.  Read-only.
"""
import json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE.parent / 'scripts'))
sys.dont_write_bytecode = True
import numpy as np  # noqa: E402
from r2_common import ROOT, INV, LABEL, GRID, csvout, jl, read, load_main, route_mask, csvread  # noqa: E402

P210 = ROOT / 'P2_10_20260911T122423Z'
RES = HERE / 'results'
SETTING = ('medium', 'OBQA', 'C2C')
PUBLISHED_Q55 = dict(omitted=390, N=742, lost=1, corrections=44, kept=43, gained=7, net=6, other=11,
                     unused_omit=12, unused_keep=89)

gold = {r['id']: r['gold_answer'] for r in jl(P210 / 'data/obqa_dev.jsonl')}
D = load_main()[SETTING[0], SETTING[1]]['dev']
ids = D['ids']
u = D['scores']['ProbeMax']
g = np.array([gold[i] for i in ids], dtype=object)
oR = np.array([x if x is not None else INV for x in D['ans']['R']], dtype=object)
oC = np.array([x if x is not None else INV for x in D['ans']['C']], dtype=object)
oT = np.array([x if x is not None else INV for x in D['ans']['T']], dtype=object)
cuts = load_main()[SETTING[0], SETTING[1]]['stored_thresholds']
thr = dict(zip(GRID, cuts))
yR, yC, yT = (oR == g), (oC == g), (oT == g)

# the largest clean-accepted q comes from the pre-registered E5-a exposure-removal analysis
clean = {r['setting']: r for r in csvread(HERE.parent / 'results/e5a_clean_tests.csv')}
clean_q = float(clean['medium/OBQA/C2C']['largest_clean_accepted_q'])

rows = []
for q in (0.55, clean_q):
    m = route_mask(u, q, thr[q])
    policy = np.where(m, oR, oC)
    yP = (policy == g)
    corrections = yC & ~yR                       # reference corrects R
    lost = corrections & m                       # omitted -> the correction is lost
    kept = corrections & ~m                      # the policy runs the reference
    gained = m & yR & ~yC                        # omitted and R is right where the reference is wrong
    other = m & ~yR & ~yC & yT                   # omitted, both wrong, the other action is right
    some = yR | yC | yT
    unused_omit = int((m & some & ~yP).sum())
    unused_keep = int((~m & some & ~yP).sum())
    rows.append(dict(
        setting='medium/OBQA/C2C', q=q, source=('ORIGINAL frozen deployment' if q == 0.55 else
                                                'largest clean-accepted q (E5-a, exposure removed)'),
        threshold=thr[q], N=len(ids), omitted=int(m.sum()), kept_count=int((~m).sum()),
        coverage_pct=round(100 * float(m.mean()), 2),
        changed_on_omitted=int((oR[m] != oC[m]).sum()),
        changed_all=int((oR != oC).sum()),
        correct_policy=int(yP.sum()), correct_reference_C2C=int(yC.sum()), correct_R=int(yR.sum()),
        correct_Text=int(yT.sum()),
        policy_minus_reference=int(yP.sum()) - int(yC.sum()),
        reference_corrections=int(corrections.sum()), lost=int(lost.sum()), kept=int(kept.sum()),
        gained=int(gained.sum()), net=int(gained.sum()) - int(lost.sum()), other=int(other.sum()),
        unused_omit=unused_omit, unused_keep=unused_keep,
        identity_holds=bool(int(yP.sum()) - int(yC.sum()) == int(gained.sum()) - int(lost.sum())),
        label=LABEL))

check = rows[0]
reproduces = all(check[k] == v for k, v in
                 [('omitted', PUBLISHED_Q55['omitted']), ('N', PUBLISHED_Q55['N']),
                  ('lost', PUBLISHED_Q55['lost']), ('reference_corrections', PUBLISHED_Q55['corrections']),
                  ('kept', PUBLISHED_Q55['kept']), ('gained', PUBLISHED_Q55['gained']),
                  ('net', PUBLISHED_Q55['net']), ('other', PUBLISHED_Q55['other']),
                  ('unused_omit', PUBLISHED_Q55['unused_omit']), ('unused_keep', PUBLISHED_Q55['unused_keep'])])

RES.mkdir(parents=True, exist_ok=True)
csvout(RES / 'f1c_medium_obqa_C2C_dev.csv', rows)
(RES / 'f1c_medium_obqa_C2C_dev.json').write_text(json.dumps(
    dict(label=LABEL, clean_q=clean_q, published_q55_row=PUBLISHED_Q55,
         reproduces_published_q55_row=reproduces, rows=rows), indent=2) + '\n')
for r in rows:
    print(json.dumps({k: r[k] for k in ['q', 'threshold', 'omitted', 'N', 'coverage_pct',
                                        'changed_on_omitted', 'correct_policy', 'correct_reference_C2C',
                                        'correct_R', 'reference_corrections', 'lost', 'kept', 'gained',
                                        'net', 'other', 'unused_omit', 'unused_keep', 'identity_holds']}))
print('reproduces published q=.55 row:', reproduces)
