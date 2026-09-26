# P2_R8_E20F_20260922T003652Z — E20-full (SQuAD | Llama-3.1-8B receiver | score s2), Paper A

Status 2026-09-22T03:32Z: DONE. PREREG_E20F.md 4c63e4ab… (03:09:28Z). Job 1 7643654 (fit + cal, 03:09:41-03:23:30Z), CERT_E20F.json 3a370c00…
(03:24:08Z; deployed q = .35), job 2 7643669 (dev + test, 03:24:21-03:30:26Z), STATS_E20F.json / ROUTES_E20F.json (03:30:55Z), gold 03:31:13Z,
RESULTS_E20F.md (writing-rule branch (1); rule (5) triggered). Never resubmit either job.

Files: GATE.md (Step 0), PREREG_E20F.md + .sha256, DEVIATIONS.md, CODE_DIFF.patch, notes/CODE_FREEZE_E20F.json, inputs/FULL_{fit,cal,dev,test}.jsonl,
pool/ (byte-identical pilot pool rebuild), records/{fitcal,devtest}/ (per-rank rows, PREFLIGHT_j*, PLAN_j*), results/ (merged rows, MERGE_*, OUTPUTS_HASH_*,
ACCURACY_E20F.json), CERT_E20F.json, STATS_E20F.json, ROUTES_E20F.json (+ .sha256), RESULTS_E20F.md. notes/dryrun/ is FAKE (see its README).
Code: src/e20f_exec.py (GPU driver; pilot functions verbatim), e20f_merge.py, e20f_cert.py (paper functions), e20f_cert_run.py (Step 4),
e20f_stats.py (Step 6), e20f_gold.py (Step 7), e20f_results.py; jobs/e20f_{fitcal,devtest}.pbs, jobs/e20f_slot.sh.
