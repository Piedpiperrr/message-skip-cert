# P2_R8_E20P_20260921T224653Z — E20-pilot (label-free short-answer pilot), Paper A

Status 2026-09-22T00:05Z: DONE. PREREG_E20P.md hashed 2026-09-21T23:30:43Z. Job A 7643426 (23:31:00-23:46:32Z) and job B 7643430
(23:46:42-23:58:00Z) complete, 1,600/1,600 questions, no runtime errors; preflight OBQA 32/32 + X3 16/16 bitwise. Steps 4-5: PILOT_STATS.csv,
SELECTION_E20P.json hashed 23:58:59Z (4fdee068...): selected SQuAD | Llama-3.1-8B | s2 | N_cal 2,000. Step 6 (gold first opened 23:59:26Z):
results/ACCURACY_E20P.json. Never resubmit either job.

Files: GATE.md (Step 0: datasets, revisions, pool sizes, hashes, prompt checks, dry run), PREREG_E20P.md + .sha256 (Step 1), PROMPTS_E20.md (G4),
DEVIATIONS.md, notes/CODE_FREEZE.json (checked by every GPU rank), inputs/ (POOL_ORDER_*.txt, PILOT_*.jsonl: id, question, passage only).
Code: src/e20_pool.py (G2), src/e20_prompts.py, src/e20_extract.py (extractor + scores), src/e20_render.py (G4), src/e20_exec.py (GPU driver;
--dry-run), src/e20_merge.py (per job), src/e20_analyze.py (Steps 4-5), src/e20_accuracy.py (Step 6, only after SELECTION_E20P.json is hashed).
Jobs: jobs/e20_jobA.pbs (SQuAD + NQ-passage), jobs/e20_jobB.pbs (TriviaQA + NQ-Open), jobs/e20_slot.sh. Per-rank outputs: records/job{A,B}/;
merged: results/E20P_job{A,B}_rows.jsonl, results/MERGE_job*.json, results/OUTPUTS_HASH_job*.txt. notes/dryrun/ is FAKE (see its README).

After both jobs (login node): `python src/e20_analyze.py` (verifies OUTPUTS_HASH_job*.txt, writes OUTPUTS_HASH.txt, PILOT_STATS.csv,
SELECTION_E20P.json + .sha256), then `python src/e20_accuracy.py`.
