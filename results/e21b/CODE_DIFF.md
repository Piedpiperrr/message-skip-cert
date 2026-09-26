# E21B code changes

The frozen runtime, prompt builders, parser, probe and V1 rotation are used unchanged. The full unified diffs are in
`diffs/`, and the SHA-256 of every script is recorded in `PREREG.sha256`.

## 1. Driver: `src/e21b_exec.py` = E9B `large/src/e9b_exec.py` + 22 added / 7 removed lines (29 changed lines; limit 60)

Diff: `diffs/e21b_exec_vs_e9b_exec.diff`. Every changed line carries an `# E21B` comment.

| change | lines | purpose |
|---|---|---|
| import `common`/`native_adapter` from `$E21B_STAGE/src` (a per-slot byte-identical copy of the E9B large stage) | 1 | Two slots per node would otherwise race on the frozen adapter's single evidence filename, the E9B job 7638751 defect. There is no code change in the adapter. |
| E9B helpers path (`e9b_common`: 744 population, facts) | 1 | read-only import from the E9B folder |
| load E4 `labels`/`rotate` from `prepare_populations.py` via `ast` after a hash assert | 4 | V1 rotation, unchanged code |
| `--population`, `--transform {v1, identity}`, `--ids` | 3 + 1 | identity = preflight P1 (same wrapper with the identity permutation) |
| `q, back = TRANSFORM(q)` before any action | 1 | rotation applied before every frozen prompt builder (probe, R, Text helper and receiver, C2C, Text+fact) |
| record `answer_original = back[answer]` (INVALID stays INVALID), `back`, `choice_text_used`, `helper_generated_token_ids` | 5 | label mapping back to the original option index; P1 first-differing-token reports |
| sealed ARC population file; `--ids` filter | 3 | population selection |
| record `dataset`, `population`, `transform`, `utc` | 3 | manifest (the per-record UTC decides rule (4)) |

Unchanged:
- `Runtime()` construction, `rt.probe`, `rt.action`, parser call, decoding, and the E6 Text+fact wrapper (`format_openbook_e6`, fact line prepended to the helper body).
- The resume logic and the per-row deadline stop.
- The validate mode, which exists in the file but is never called.

## 2. Byte-identical copies (0 changed lines)

- `large_s0` … `large_s3`: `src/common.py`, `src/native_adapter.py`, `src/receiver_prompt.py`, `frozen_config.json`
  and `protocol/*` are copied from `P2_R3_E9BC_20260920T061042Z/large/` (hashes in `PREREG.sha256`).
  `common.py` locates the stage by its own path, so each slot writes its model-load evidence into its own `large_s<k>/evidence/`.
- `src/gpu_preflight2.py` is a copy of E9B `src/gpu_preflight2.py` (`24eda5aa…`, GPU usability guard).

## 3. Job wrappers (shell, not model or prompt code)

| file | derived from | diff |
|---|---|---|
| `src/slot_e21b.sh` (49 lines) | E9B `src/slot_e9b.sh` | +42 / -18 (`diffs/slot_e21b_vs_slot_e9b.diff`) |
| `jobs/e21b_job1.pbs` (27 lines) | E9B `run_e9bc.pbs` | +14 / -37 (`diffs/e21b_job1_vs_run_e9bc.diff`) |

The slot script adds the preflight part per rank and a file barrier. Rank 0 then runs the gate and the other ranks
wait for its verdict. Production runs only on a PASS verdict. These lines are counted separately from the 60-line
driver limit.

## 4. Statistics and checks: `src/e21b_stats.py` (new, 497 lines; excluded from the limit)

| subcommand | what it does |
|---|---|
| `select` | chooses the preflight rows (see INPUTS.md §6) |
| `gate` | P1, P2 and P3 exactly as in the task |
| `manifest` | checks every question x arm exactly once and records the first/last output UTC before any statistic |
| `stats` | computes the PREREG statistics, writes the CSVs and picks the writing-rule branch |

`gate` details:
- **P1 identity rotation versus the stored outputs.** The prompt-token-ID checks must pass on all rows:
  - frozen-builder token IDs on the original question equal those on the wrapper's question, for the receiver-only, probe, Text-helper and Text+fact-helper prompts;
  - the probe input-ID SHA-256 equals both the stored value and the CPU re-render;
  - the builder-determined input lengths equal the stored ones.
- P1 also requires u within 1e-6 and R byte-identical on all rows, and Text helper, Text, C2C, Text+fact helper and Text+fact byte-identical on >= 15/16 rows. Each mismatch is reported with its first differing token.
- **P2** on the P1 rows plus the 28 sealed-ARC K != 4 or non-letter questions:
  - the rendered receiver, probe and helper prompts contain the V1-permuted original option block exactly once and not the original-order block;
  - the Text+fact helper equals the fact line followed by the rotated helper body;
  - mapping back recovers the original index at every position;
  - on the P3 rows, the probe input IDs actually run equal the frozen builder on the rotated question.
- **P3**: INVALID counts per arm on the 16 rotated rows, STOP if > 2/16.

It reads no gold file.

## 5. Login-node test (before hashing; no model loaded, no model output)

The driver, slot script, gate, manifest and stats were run on the ClusterA login node in the session scratchpad
(outside this folder). The run used a stub `native_adapter.Runtime` that returns fixed strings and computes prompts
and probe input IDs with the real frozen builders.

Findings:
- **Gate on synthetic P1 records holding the stored values: 0 hard failures.** This confirms that the CPU re-render reproduces the stored probe input hashes and the R, C2C, Text-helper and Text+fact-helper input lengths on all 32 P1 rows.
- **P2**: 0 failures on 44 ARC rows and 16 OBQA rows.
- **Stub mismatch path**: the gate stopped on the stub's outputs, as designed, and reported first differing tokens.
- **Slot barrier**: 4 simulated ranks ran both the STOP path (no production) and a forced-PASS path (production shards 4 x 293 ARC and 4 x 186 OBQA). The manifest then counted 4,688 + 3,720 records, complete.
- **Stats**: recomputed the stored original-format k/n (20/1100, 11/1047, 12/595, 13/595, 16/558).

After these tests, the only files left in this folder are `preflight/ROWS.json` and `preflight/ids_{arc,obqa}.json`
from `select`; the tests wrote nothing else here. Stray `src/__pycache__` from `py_compile` was deleted before hashing.
