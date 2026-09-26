# P2_R6_X4_20260921T072448Z — X4 (sampled receiver answers; large pair Qwen2.5-7B -> Qwen3-8B; Text reference; OBQA + ARC)

Status 2026-09-21T07:45Z: production 7642101 done (exit 0, 5,626 rows, manifest 16/16); Step 4 done -> results/analysis/X4_SUMMARY.md.
Earlier status 2026-09-21T07:32Z: PREREG_X4.md hashed 07:24:48Z (9f3a4ce0...). Smoke job 7642097 PASS ((a) greedy path = stored 16/16, (b) sampled rerun
identical 16/16, (c) sampled vs greedy: R 0/16 labels, Text 0/16 labels (2/16 texts); INVALID 0/0). Production job 7642101 (P2R6_X4_RUN, debug,
2 nodes, 00:30, 8 chains, 5,626 rows, both paths sampled) submitted 07:30:57Z. Step 4: src/analyze_x4.py 'results/runs/chain_*.jsonl' only after
the user says the job has finished (verifies results/runs/MANIFEST.sha256 first; certification hashed before gold).
Code: src/run_x4.py = X3 driver + sampling wrapper (diffs/run_x4_vs_run_x3.diff); see DEVIATIONS.md.
