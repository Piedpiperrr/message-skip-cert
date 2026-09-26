# P2_R2_E7: the E7 four-arm replay and the conditional E6 replay

Frozen protocols: `P2_R2_GPU_20260919T220941Z/e7/PROTOCOL_FREEZE_E7.md` (E7) and
`.../e6/PROTOCOL_FREEZE_E6.md` section 6 (E6 replay). Nothing in either freeze was edited.

## Layout

`large/`, `medium/`, `mmlu/` are stage copies of the corresponding sub-stages of
`P2_R1_E3POL_REPEAT1_20260919T075315Z` (inputs, protocol, deployment files, freeze files,
`SOURCE_INDEX.json`, `src/`, and the medium asset symlinks), with that run's `records/`, `evidence/`,
`run_logs/` and completion markers left behind. `e6replay/` is a copy of `large/` plus the E6
deployment file. The originals are read-only throughout.

## Additive-only changes

Per stage, two new files and nothing else:

- `src/e7_arms.py` — `probe_keep_cache` (the frozen ProbeMax computation with `use_cache=True`, then
  `cache.crop(len(R)-1)`) and `generate_R_from_cache`. New code only.
- `src/execute_e7.py` — the four-arm driver. The frozen `Runtime.probe` and `Runtime.action` of each
  stage (`native_adapter.py` for large/e6replay, `native_runtime.py` for medium/mmlu) are **imported
  and called unchanged**; arms 1 (FIXED) and 2 (ORIGINAL) build the query dict and call probe/action
  exactly as that stage's frozen `execute.py` does, and the frozen `execute.py` is neither used nor
  modified. `e6replay/src/execute_e6replay.py` is the E6 two-arm driver; its Text+fact action adds one
  `Useful fact: <fact1>` line to the **helper's** question block through a new flag on the prompt
  builder (default off, byte-identical when off), and rebuilds the receiver's first user turn from the
  original fact-free block, so the receiver prompt stays byte-identical to the frozen Text prompt.

## Arms, rotation, counts

`['fixed', 'original', 'reuse', 'argmax']`, rotated per question as `arms[k:] + arms[:k]`,
`k = ordinal mod 4` (32 questions per (arm, position) cell). 512 requests per deployed policy.
Node A = large OBQA (Text, C2C) + large ARC (Text, C2C) = 2048. Node B = MMLU-Pro (Text, C2C) 1024 +
medium OBQA (C2C) + medium ARC (C2C) 1024, then the E6 replay's 2 arms x 128 = 256.
ARGMAX uses `q_A` / `threshold_A` from `e7/E7_ARGMAX_RECERT.json`; all eight policies have `q_A > 0`,
so all eight have an ARGMAX arm.

## Pre-replay checks (job 7638020, debug, 1 node, 00:40:00)

- `validation/E7_VALIDATION2_{large,medium}.json` — the 16-row fit validation, run **through the new
  driver's `run_one`**. Qwen3-8B (references T and C) and Qwen3-1.7B (reference C): FIXED 0 mismatches,
  ORIGINAL 0, ARGMAX 0, REUSE 0 (large, both references) and 1 of 16 (medium, inside the frozen
  "at most 1 of 16 per receiver" rule); the cached probe's ProbeMax, `probe_ids_sha256` and route are
  identical to the frozen probe on every row. No gold read.
- `smoke/` — 4 questions per panel, all arms, all five panels plus the E6 replay, one 1-node job:
  large 64/64, medium 32/32, MMLU-Pro 32/32, E6 8/8, no runtime errors; online frozen-probe identity
  checked on 48/48 large panel requests with 0 failures.

## Formal replay (job 7638030, debug, 2 nodes, 00:50:00)

Records under `<stage>/records_e7/` (`e7_requests.jsonl`, `attempts.jsonl`) and
`e6replay/records_e6/`; completion markers `E7_REPLAY_COMPLETE.json` / `E6R_REPLAY_COMPLETE.json`.
Single run, zero retries, no warm-up, one model residency per stage process, GPUs 0-1 only.
No gold is read by the replay. The analysis comes in a later prompt.

## Replay outcome (job 7638030, 2026-09-19T23:32:55Z - 23:57:51Z, 25 min of the 50-min walltime)

`MPIEXEC_EXIT=0`; node A `RC_large=0`; node B `RC_mmlu=0 RC_medium=0 RC_e6replay=0`. Integrity check
`jobs/verify_replay.py` -> `REPLAY_VERIFICATION.json`:

| stage | requests | marker | arms | (arm, position) cells per policy | online frozen-probe identity | INVALID | runtime failures | gold read |
|---|---|---|---|---|---|---|---|---|
| large | 2048/2048 | COMPLETE | 512 each | 32 each (64 cells) | 1536 checked, **0 failures** | 0 | 0 | no |
| mmlu | 1024/1024 | COMPLETE | 256 each | 32 each (32 cells) | n/a (no expected-route file) | 4 | 0 | no |
| medium | 1024/1024 | COMPLETE | 256 each | 32 each (32 cells) | n/a (no expected-route file) | 24 | 0 | no |
| e6replay | 256/256 | COMPLETE | 128 each | 64 each (2 arms) | — | 0 | 0 | no |

Omitted per arm: large 429/512 (ORIGINAL, REUSE and ARGMAX identical); MMLU-Pro 96/256 (all three);
medium 143/256 for ORIGINAL and REUSE and 138/256 for ARGMAX (`q_A = .50 < q = .55` on medium/OBQA).
E6 replay: 92 of 128 policy questions omitted (71.9%), 36 ran Text+fact.

**REUSE outputs differing from the native R output** (freeze section 3), `REUSE_OUTPUT_DIFFERENCES.csv`:
**13 of 668** omitted REUSE requests — 10 large, 3 medium, 0 MMLU-Pro. All 13 are a trailing full stop
(`The correct answer is C` vs `The correct answer is C.`); **all 13 parse to the same V2 label**, so no
routed answer changes.

Mean per-request latency (ms), for orientation only — the analysis is a later prompt:

| stage | fixed | original | reuse | argmax |
|---|---|---|---|---|
| large | 571.9 | 290.7 | 291.0 | 117.9 |
| MMLU-Pro | 684.5 | 544.6 | 541.1 | 463.8 |
| medium | 332.0 | 268.0 | 268.0 | 174.6 |
| e6replay | 726.5 (fixed Text+fact) | 383.1 (Text+fact policy) | — | — |
