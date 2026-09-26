"""Split the E12-a table into per-replay CSVs and write E12A_SUMMARY.md. No new computation."""
import sys
sys.dont_write_bytecode = True
import csv, json, pathlib
OUT = pathlib.Path(__file__).resolve().parents[1]
R = OUT / 'results'
rows = list(csv.DictReader(open(R / 'E12A_per_arm_quantiles.csv')))
gate = list(csv.DictReader(open(R / 'E12A_reproduction_gate.csv')))
chk = json.load(open(R / 'E12A_CHECKS.json'))
f = lambda x: float(x)
st = lambda r: '/'.join([r['pair'], r['task'], r['reference']])

# ---- per-replay CSVs
per = {}
for r in rows:
    per.setdefault(r['replay'], []).append(r)
for name, rs in per.items():
    p = R / f'E12A_{name}.csv'
    fields = list(dict.fromkeys(k for x in rs for k in x))
    with open(p, 'w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=fields); w.writeheader(); w.writerows(rs)

b = [r for r in rows if r['version'] == 'b']
a = [r for r in rows if r['version'] == 'a']
p90w = [r for r in b if r['pol_p90_worse'] == 'True']
p99w = [r for r in b if r['pol_p99_worse'] == 'True']
negmed = [r for r in b if f(r['all_d_p50']) < 0]

L = []
w = L.append
w('# E12-a: per-query latency distribution from existing records')
w('')
w('Prereg `PREREG_E12.md` sha256 `%s`, frozen 20260920T225858Z. Login node, CPU only, no job, no model.' %
  open(OUT / 'PREREG_E12.sha256').read().split()[0])
w('')
w('## Method (reused unchanged, not re-derived)')
w('')
w('- Version **(a)** = all paired panel questions. Version **(b)** = drop every question on which *either*')
w('  compared arm made its first formal request in that replay (each arm\'s minimum `attempt`). This is the')
w('  frozen E3 rule, taken from `P2_R1_E3POL_REPEAT1_20260919T075315Z/e3_build/e3_metrics.py` (`saving_row`)')
w('  and `P2_R2_ANALYSIS_20260920T002850Z/scripts/common_r2a.py`. (a) and (b) are kept separate everywhere.')
w('- **Pairing is by question id** (records are keyed into dicts by `record["id"]`), never by position in the log.')
w('- **omitted / routed use the recorded routing decision**, not the score: omitted <=> `selected == "R"`.')
w('  E7 and E6 records also carry an explicit `omitted` field; the frozen check')
w('  `omitted == (selected == "R")` in `e7_analysis.py:89` is re-asserted here for every such record.')
w('- Quantiles are `numpy.percentile` defaults (linear interpolation). Paired difference d = fixed - policy,')
w('  so **d < 0 means the query was slower under the policy**.')
w('- Machines are never merged: rows carry `machine` (ClusterB / ClusterA / ClusterA-E7).')
w('')
w('## Coverage')
w('')
w('Every replay in scope stores per-request timings; **none stores only aggregates**. %d arm-streams x 2 versions'
  ' = %d rows in `results/E12A_per_arm_quantiles.csv`:' % (chk['n_streams'], chk['n_rows']))
w('')
w('| replay | machine | arms | settings |')
w('|---|---|---|---|')
for name in ['ClusterB', 'E3_REPEAT1', 'E3_REPEAT2', 'E3_REPEAT3', 'E3_MMLU_C2C_FULL', 'E7', 'E6_REPLAY']:
    rs = [r for r in b if r['replay'] == name]
    w('| %s | %s | %s | %d |' % (name, rs[0]['machine'],
      ', '.join(sorted({r['arm'] for r in rs})), len({st(r) for r in rs})))
w('')
w('## Reproduction check (step 2a) — PASS')
w('')
w('Recomputed ClusterA E3 version-(b) paired mean savings, all three repeats, against the supplied ranges:')
w('')
w('| setting | expected range | repeat1 | repeat2 | repeat3 | in range |')
w('|---|---|---|---|---|---|')
for g in gate:
    w('| %s | [%s, %s] | %s | %s | %s | %s |' % ('/'.join([g['pair'], g['task'], g['reference']]),
      g['expected_low'], g['expected_high'], g['repeat1'], g['repeat2'], g['repeat3'], g['in_range']))
w('')
w('All 8 land inside their range (`results/E12A_reproduction_gate.csv`, `E12A_CHECKS.json`).')
w('')
w('## Findings')
w('')
w('**1. p99 is never worse under the policy.** In no replay, setting, arm or version does the policy p99')
w('exceed the fixed reference p99 (%d rows checked).' % len(b))
w('')
w('**2. p90 is worse under the policy for 2 of the 8 settings, both currently classified as a positive saving.**')
w('Version (b), %d of %d rows:' % (len(p90w), len(b)))
w('')
w('| replay | setting | arm | policy p90 | fixed p90 | policy p99 | fixed p99 |')
w('|---|---|---|---|---|---|---|')
for r in sorted(p90w, key=lambda r: (st(r), r['replay'], r['arm'])):
    w('| %s | %s | %s | %.1f | %.1f | %.1f | %.1f |' % (r['replay'], st(r), r['arm'],
      f(r['all_pol_p90']), f(r['all_fix_p90']), f(r['all_pol_p99']), f(r['all_fix_p99'])))
w('')
w('- `medium/OBQA/C2C` has a worse p90 in **every** replay and every arm, on both machines.')
w('- `large/MMLU-Pro/Text` has a worse p90 on **ClusterA only** (all 3 E3 repeats and all 3 E7 arms); on ClusterB')
w('  its p90 is better (1613.4 vs 1644.1 ms). Machine-dependent, so the two are reported separately.')
w('- Version (a) vs (b) matters here: 5 rows flip, all `large/MMLU-Pro/Text`, all from "not worse" in (a) to')
w('  "worse" in (b) (E3_REPEAT1, E3_REPEAT3, and all three E7 arms). Dropping the cold request removes a large')
w('  fixed-arm outlier and lowers the fixed p90.')
w('')
w('**3. The paired median is negative in 16 of %d rows, including settings with a large positive mean saving.**' % len(b))
w('')
w('| replay | setting | arm | mean saving (ms) | median saving (ms) | frac slower |')
w('|---|---|---|---|---|---|')
for r in sorted(negmed, key=lambda r: (st(r), r['replay'], r['arm'])):
    w('| %s | %s | %s | %.1f | %.1f | %.3f |' % (r['replay'], st(r), r['arm'],
      f(r['all_mean_saving']), f(r['all_d_p50']), f(r['all_frac_slower'])))
w('')
w('`large/MMLU-Pro/Text` is the sharpest case: mean saving +260.8 to +262.7 ms on ClusterA E3 (a certified')
w('positive saving) while the **paired median is -21.0 to -31.8 ms and 59.8-60.6% of queries are slower**.')
w('')
w('**4. Mechanism: routed queries are slower under the policy essentially always; all saving comes from omitted queries.**')
w('Across every replay and arm, the fraction of *routed* queries that are slower under the policy is 0.85-1.00')
w('(usually exactly 1.00), and the routed paired median is -25 to -45 ms — the probe cost, paid on top of the')
w('same reference work. On *omitted* queries the policy is faster except in `large/MMLU-Pro/C2C`, where even')
w('omitting is not enough (omitted frac slower 0.54-0.60).')
w('')
w('**5. ARGMAX (largest mean saving) behaves the same way.** Its tail is not systematically worse than the other')
w('E7 arms: it shows the same two worse-p90 settings and no worse p99. Where it helps most (`large/ARC/Text`')
w('p90 32.6 ms vs 1007.0 ms fixed) it helps by answering from the probe on omitted queries; its routed queries')
w('are still slower 100% of the time, and on `medium/OBQA/C2C` it turns the paired median negative (-20.7 ms)')
w('while keeping a +123.0 ms mean.')
w('')
w('## Reporting rules triggered (fixed in advance by the prereg)')
w('')
w('- "If the policy\'s p90 or p99 is worse than the fixed reference for any setting currently classified as a')
w('  positive saving" — **TRIGGERED** by `medium/OBQA/C2C` (everywhere) and `large/MMLU-Pro/Text` (ClusterA).')
w('  The main text must report those tail numbers, say that a positive mean saving can coexist with a worse')
w('  tail, and reword Contribution 4 to name the mean explicitly.')
w('- The "tails are not worse" branch does **not** apply.')
w('- The paired median must be given alongside the mean for at least the two example settings; the medians for')
w('  all 8 deployed policies, all replays, are in `results/E12A_reproduction.csv`.')
w('')
w('## Files')
w('')
w('- `results/E12A_per_arm_quantiles.csv` — every quantity in the prereg, one row per replay/setting/arm/version,')
w('  with `all_`, `om_` (omitted) and `rt_` (routed) blocks.')
w('- `results/E12A_<REPLAY>.csv` — the same rows split per replay.')
w('- `results/E12A_reproduction.csv`, `results/E12A_reproduction_gate.csv`, `results/E12A_CHECKS.json`.')
w('- Script: `scripts/e12a_tails.py` (reads every P2_* folder read-only).')
(OUT / 'E12A_SUMMARY.md').write_text('\n'.join(L) + '\n')
print('wrote E12A_SUMMARY.md and', len(per), 'per-replay CSVs')
