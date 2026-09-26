# GATE.md — E20-full Step 0 (login node; no model weights; no gold)

Written 2026-09-22T03:07:57.414320+00:00. Stage P2_R8_E20F_20260922T003652Z. Pilot: P2_R8_E20P_20260921T224653Z (read-only).

## G1 — pilot files verified: PASS (32/32 checks)

PREREG_E20P.md c02cf958a7c972c6c976da4100d02293fcd81ba91b5f614d02b3cf0a1ab7adb5 (= stored .sha256 and task value); SELECTION_E20P.json = stored
SELECTION_E20P.sha256 (4fdee068...); PROMPTS_E20.md and notes/CODE_FREEZE.json = the hashes written in PREREG_E20P.md; all 27 CODE_FREEZE files
match. Evidence: notes/G1_VERIFY.json (src/e20f_g1_verify.py).

## G2 — pool rebuild and full-run splits: PASS

Byte-identical copies of the frozen pilot e20_pool.py / e20_extract.py / DOWNLOAD_MANIFEST.json run in pool/ (the pilot directory is not written).
SQuAD (rajpurkar/squad @ 7b6d24c440a36b6815f21b70d25016731768db1f): pool 86,830 (required 86,830); POOL_ORDER_squad.txt 9754449546d370e2ab7c690ee99f44a50c240230850574f195f596664ffab7f3 = pilot; the other three pools and all four PILOT files also reproduce byte for byte (logs/pool_rebuild.log).
src/e20f_splits.py reads only id, question, context (answers never read), rebuilds items as e20_pool.py does, checks that the first 400 serialize
byte-identically to the pilot file, and writes (id, question, passage only):

| split | pool positions | n | file | sha256 |
|---|---|---|---|---|
| fit | [400, 900) | 500 | inputs/FULL_fit.jsonl | `a3ac3e0cff3a78c973de46e5701fc7e3e9e68efa4ea66f5613623edd8d32ae57` |
| cal | [900, 2900) | 2000 | inputs/FULL_cal.jsonl | `bf25118bbaae4da88cc651a71c994a7a0cea0684adaee3553cf5836cf5886553` |
| dev | [2900, 3900) | 1000 | inputs/FULL_dev.jsonl | `13a98e661a2011c3cb7e0a765929a9ba41da9ea09146213d4c3e71f89d73c3a4` |
| test | [3900, 4900) | 1000 | inputs/FULL_test.jsonl | `1ba0a728f908f4dd42ed79285e3af35572020e6f4f51a3ac0c095f988b6f119e` |

Pairwise intersections of pilot / fit / cal / dev / test: all 0 (all_disjoint = True). Evidence: notes/SPLITS_E20F.json.

## G3 — no model output exists for the 4,500 ids: PASS

`grep -rlF -f notes/FULL_IDS_4500.txt` over the whole project tree except this stage (02:52:51-03:05:57Z, exit 0, empty stderr;
notes/G3_GREP_run3_status.txt): one file matches, P2_R8_E20P_20260921T224653Z/inputs/POOL_ORDER_squad.txt, which is the pilot pool order (id
list, not a model output). (An earlier identical run gave the same single hit but its exit status was lost; run 2 was interrupted.)

## G4 — the paper's certification function reproduces X3: PASS

Functions: P2_R1_CPU_20260919T045556Z/src/common_r1.py (thresholds, pval, cp999, deploy; sha 61a4b20b876897427c3e02d5c5ed3a8a8c7771d27be3ede6ef9fa8cd97a37038),
data_r1.py route_mask (sha 619c4496c0352c6987a3c352bb55395662c4a60802a16fdae63529ad0dcba2d3), ledger_rows verbatim from P2_R6_X3.../src/analyze_x3.py
(sha 5953c24b73cb99f36f3bf91237e9ab0b0a5a158cd790f36e84c39e54522e9c4f; copy asserted), wrapped in src/e20f_cert.py (sha 3d713d9163ed746f29724fd1a70289913bfe48a3fb27021b8fc18c581f12a702).
On the stored X3 Llama-8B OBQA fit (2100) + calibration (1366) records: deployed q = 0.6, 21 changes among 800 omitted,
p = 0.0005735; all 20 ledger rows equal results/analysis/certification_ledger_40.csv (n, k, p repr). Evidence: notes/G4_CERT_REPRO.json.

## G5 — helper revision, time estimate, job plan

Helper Qwen/Qwen2.5-7B-Instruct @ a09a35458c702b33eeacc393d103063234e8bc28 (pilot PREREG_E20P.md); receiver meta-llama/Llama-3.1-8B-Instruct @
0e9e39f249a16976918f6564b8830bc894c89659. Pilot SQuAD per-row wall-clock (400 rows): helper mean 832 ms (median 795, max 2,672; median 36
tokens, max 65), Llama receiver-only mean 166 ms, receiver-with-message mean 182 ms -> 1.18 s per question. Loads: 140-161 s cold, 10-77 s warm.
Job 1 (fitcal, 2,500 questions, ~313 per GPU): rank-0 preflight ~5.5 min, then ~6-7 min decoding + loads -> ~12-17 min. CERT on the login node.
Job 2 (devtest: dev 1,000, plus test 1,000 only if deployed; ~250 per GPU): ~12-14 min. A third job only for leftovers; 1 resubmission for a
non-scientific failure. Each job stops starting questions at T+48 min. Queue at 02:51Z: E18 job 7643632 running (submitted 02:50:56Z),
so E18 is submitted and E20F uses at most one further debug position at a time.

## Dry run (no weights) — PASS

notes/dryrun/ (FAKE; see its README): 8-rank fitcal job with stub models (verbatim-function check, pilot preflight code path,
plan, helper and receiver stages, merge), a continuation job (plan excluded the 16 done questions; 2,484 assigned, 0 overlap), synthetic
completion -> e20f_cert_run (CERT + hash; refuses if dev/test outputs exist) -> devtest job with stub models (test planned only because the
CERT deployed) -> merge -> e20f_stats (STATS + ROUTES hashed) -> e20f_gold on a synthetic parquet (guard refuses the real gold in dry-run
mode) -> e20f_results.

## Code — CODE_DIFF.patch sha256 c8fa57cc1c9fc788e03fcd3f955df05fe9d51853962cf6084efedec5f88f1430

Against the pilot CODE_FREEZE: e20f_exec.py (from e20_exec.py), e20f_merge.py (from e20_merge.py), jobs from e20_jobA.pbs / e20_slot.sh; new:
e20f_common, e20f_cert, e20f_cert_run, e20f_stats, e20f_gold, e20f_results, e20f_g1_verify, e20f_splits. Prompts, extraction, normalization,
scores and decoding are the pilot modules, imported unmodified.
