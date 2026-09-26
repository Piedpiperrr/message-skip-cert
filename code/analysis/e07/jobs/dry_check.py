"""Login-node dry check: import the E7 driver of one stage and resolve everything that does not
need a GPU (policies, panels, frozen thresholds, q_A, rotation, arm counts).  No model is loaded."""
import os, sys, json
from pathlib import Path
sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(sys.argv[1]) / 'src'))
os.chdir(sys.argv[1])
import execute_e7 as D

out = {'kind': D.KIND, 'policies': D.POLICIES, 'records_dir': str(D.OUTD), 'npanel': D.NPANEL, 'arms': D.ARMS}
tot = 0
for ds, b in D.POLICIES:
    rows = D.panel_rows(ds)
    s = D.SETTING % (ds, b)
    rec = D.recert[s]
    n = len(rows) * 4
    tot += n
    out.setdefault('settings', []).append(dict(setting=s, task=ds, reference=b, panel=len(rows),
        threshold=D.threshold_for(ds, b), q=D.deployed_q(ds, b), q_A=rec['q_A'],
        threshold_A=rec['threshold_A'], requests=n,
        first_query_id=rows[0]['id'], n_choices=len(rows[0]['choice_text'])))
rot = {}
for o in range(8):
    k = o % 4
    rot[o] = D.ARMS[k:] + D.ARMS[:k]
out['rotation_first_8'] = rot
out['total_requests'] = tot
out['q_build_example'] = sorted(D.build_q(D.panel_rows(D.POLICIES[0][0])[0]))
print(json.dumps(out, indent=1))
