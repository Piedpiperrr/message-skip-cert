# Script hashes (sha256) of every script run for E21

| script | sha256 | run |
|---|---|---|
| scripts/e21_1_cert.py | b4eedf0220b4be47d83a237ef78a41f2fc2423234c9e401cb8e268b05243d151 | 2026-09-22T07:11:48Z - 2026-09-22T07:12:11Z |
| scripts/e21_1_eval.py | 23ec658ad4ce01b51c873eada3e6c92240e27f729f924f627420bf6b9f72e828 | 2026-09-22T07:13:37Z - 2026-09-22T07:15:12Z |
| scripts/e21_2.py | 2a51ef7cc1b6361a2850b84cf364303f1d71763fe374082e6cbc0a99c6008a78 | 2026-09-22T07:16:36Z - 2026-09-22T07:19:02Z |
| scripts/e21_3a.py | 7d72ad299b7d2d3df4046274a6840f7aad5436a9d0616c604e8b09cfb3468159 | 2026-09-22T07:21:12Z - 2026-09-22T07:22:26Z |
| scripts/e21_common.py | 76c4ba0fac920779654eb4bdf3379289f7086a778cc467f0a49947fb4724005f | see note |
| scripts/make_summary.py | d6d9cdf046ec76db87f780cd7009bc553019c53f79da0f1088b0b9232b0a04c8 | see note |
| scripts/step0_repro.py | cb91868f4381a9da3f11bcf4b64109a58f4e6896c8f864d214a45b6009bbc750 | 2026-09-22T06:56:57Z - 2026-09-22T06:58:41Z |
| scripts/step0h_exposure_scan.py | 876cdb412a44aae0ea31b1c81dd094f9436f94328da76bea906ed48ef5cdabb7 | see note |

Notes
- scripts/e21_common.py is imported by every stage script; each logs/*_run.json records its sha256 (all runs: 76c4ba0f...005f, unchanged since Step 0).
- scripts/step0h_exposure_scan.py ran 2026-09-22T06:59:13.374097+00:00 - 2026-09-22T07:01:55.086548+00:00 (python3, no numpy); output results/step0h_exposure_hits.json, log logs/step0h.log.
- scripts/make_summary.py (reads this stage's outputs only; no statistic) built SUMMARY.md, results/E21_1_appendix_table.csv and this file.
- scripts/e21_3a.py first run (07:20:46Z) stopped with a Python TypeError right after the gate checks (keyword clash in a helper), before any
  statistic; the helper argument was renamed and the script re-run (07:21:12Z). The hash above is the re-run version (its run log agrees).
- scripts/e21_1_eval.py was patched (R accuracy where R is stored for all questions; exceed-eps clause inside the sentence) before its only run.
- Scratchpad (outside the project; not part of the results): explore1.py sha256 478193941ecf967e04d551ff2bd8bf2a4f0289960df543a450158c8e6c466595 (06:45Z, before PREREG: loaded
  calibration/dev sizes, thresholds and |X| only; no gold, no E21 statistic); exposure_scan.py sha256 50256c506ed171e2067c8d29f76b107ba4954ac6869b5e0c35943019df576ea1 (first exposure scan including raw
  .jsonl record files; stopped after ~7 min for the CPU budget, no output used).
- Inline shell/python one-liners were used only to inspect earlier files and this stage's CSV outputs, to render REPRO.md (a)-(g) from
  results/step0_repro_checks.csv, and to insert full sha256 values into INPUTS.md; none computed an E21 statistic.
