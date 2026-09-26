"""E18 G6: rerun the E10 certification arithmetic (src/e18_cert.py) on the stored u; compare with E10's sealed outputs.
Stored values only; no gold (E10_RESULTS.json is not opened)."""
import sys, json
sys.dont_write_bytecode = True
from pathlib import Path
HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / 'src'))
import numpy as np
import e18_cert as C
by, spl = C.load_e10()
u = {i: by[(s, 'R', i)]['u'] for s in spl for i in spl[s]}
res = C.certify(u, by, spl)
sealed_tests = [json.loads(l) for l in open(C.E10 / 'analysis/SEALED_CAL_TESTS.jsonl')]
sealed = json.loads((C.E10 / 'analysis/E10_SEALED.json').read_text())
chk = {}
chk['tests_identical_to_SEALED_CAL_TESTS'] = res['tests'] == sealed_tests
chk['thresholds_identical'] = res['thresholds'] == sealed['thresholds']
chk['deployment_identical'] = res['deployment'] == sealed['deployment']
chk['dev_summary_identical'] = res['dev'] == sealed['dev']
chk['p_all_1'] = all(t['p_value'] == 1.0 for t in res['tests'])
chk['p_values_3dp'] = sorted({'%.3f' % t['p_value'] for t in res['tests']})
chk['n_thresholds_exactly_0'] = sum(1 for t in res['thresholds'] if t != 'Infinity' and float(t) == 0.0)
chk['thresholds_19_20'] = res['thresholds'][18:]
chk['dev_disagreement'] = res['dev_disagreement']
chk['cal_disagreement'] = res['cal_disagreement']
chk['cal_disagreement_rate'] = res['cal_disagreement'][0] / res['cal_disagreement'][1]
dev_ids = res['dev_ids']; dd = res['dev_disagree']
chk['dev_AUROC'] = {k: C.auroc([by[('dev', 'R', i)][k] for i in dev_ids], dd) for k in ['u', 's2', 's3']}
chk['dev_AUROC_sealed'] = sealed['dev_AUROC']
chk['fit_u_eq_0'] = sum(by[('fit', 'R', i)]['u'] == 0.0 for i in spl['fit'])
s2 = [by[(s, 'R', i)]['s2'] for s in spl for i in spl[s]]
chk['s2_range_all_R'] = [min(s2), max(s2)]
chk['deployed'] = res['deployment']['mode']
chk['PASS'] = (chk['tests_identical_to_SEALED_CAL_TESTS'] and chk['p_values_3dp'] == ['1.000']
               and chk['n_thresholds_exactly_0'] == 18 and chk['dev_disagreement'] == [77, 400]
               and round(chk['cal_disagreement_rate'], 3) == .174
               and round(chk['dev_AUROC']['u'], 4) == .5795 and round(chk['dev_AUROC']['s2'], 4) == .6444)
(HERE / 'gate/G6.json').write_text(json.dumps(chk, indent=1) + '\n')
print(json.dumps(chk, indent=1))
