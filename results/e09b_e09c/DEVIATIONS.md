# Deviations — P2_R3_E9BC_20260920T061042Z

| UTC | Change | Reason | Model output existed? |
|---|---|---|---|
| 2026-09-20T06:21:01Z | `PROTOCOL_FREEZE_E9B.md` written and hashed (`d211e4ad…d0bbe`). Its gate failed; E9b stopped. | Freeze before any output. | No |
| 2026-09-20T06:22:06Z | `PROTOCOL_FREEZE_E9C.md` written and hashed (`38c4a26b…6c0df`). | Freeze before any output. | No |
| 2026-09-20T06:44:34Z | `PROTOCOL_AMENDMENT_E9B.md` written and hashed (`bd951a3f…5506`). Replaces the E9B gate with checks C1/C2 and fixes the population wording. `PROTOCOL_FREEZE_E9B.md` itself is unmodified. | Authors' decision, taken before any E9B model output existed, to run E9B on the same 744 questions reported as a held-out test that is **not** sealed. C1 and C2 both PASS. | **No** |
| 2026-09-20T07:05Z | **E9C execution geometry only:** `PROTOCOL_FREEZE_E9C.md` §7 says "one ClusterA debug job, `select=1`, 4 lanes (1 A100 each)". E9C now runs as phase 2 of a single `select=2` job shared with E9B. | The amended task requires E9B and E9C to be packed into as few debug jobs as possible, and E9B's frozen runtimes need 2 GPUs per slot. E9C still runs **exactly** its frozen 4-lane `LANE_PLAN.json`, one GPU per lane; `src/e9c_plan.py`, `src/e9c_prefill.py` and `src/e9c_analyze.py` are unchanged and still match the hashes in `PROTOCOL_FREEZE_E9C.md` §6. Nothing scientific changes: same score, same populations, same certification, same panels. | **No** — no E9C model output existed at this time. |

## Notes

- The E9B q=.50 threshold for medium/OBQA/C2C was resolved to its concrete frozen value
  `2.384185791015625e-07` from `P2_R2_CPU_20260919T220412Z/followup/results/f1c_medium_obqa_C2C_dev.json`
  (row `q=0.5`, "largest clean-accepted q (E5-a, exposure removed)") before any E9B output existed.
  No threshold is refitted anywhere in E9B.

## Harness defect observed in job 7638751 (no scientific effect)

| UTC | What happened |
|---|---|
| 2026-09-20T10:01Z | In `7638751` phase 1, rank 1 (large pair, shard 1 of 3) died during `native_adapter.Runtime.__init__` with `FileNotFoundError` renaming `large/evidence/model_load_<PBS_JOBID>.json.tmp`. |

Cause: the frozen `native_adapter.Runtime.__init__` writes one evidence file named only by `PBS_JOBID`,
via `common.save()`'s write-tmp-then-rename. Ranks 0 and 1 shared host `compute-node` and raced on that
single filename; the loser's rename found its `.tmp` already consumed. It is a bookkeeping collision in a
frozen file, not a model, prompt, decoding or scoring problem, and it is why the slot guard exists: rank 1
skipped its main phase instead of corrupting anything, and ranks 0, 2, 3 were unaffected.

Effect: E9B large had 496 of 744 rows after `7638751`; medium had all 744; E9C was complete.
Remedy: job `7638821` reruns **only** large shard 1 with a single rank per node, so the filename cannot
collide. No frozen file was edited. The executor's resume logic appends only rows not already on disk,
and the retry repeats the same bit-for-bit validation before running.

## E9C extension to the four E8 settings (2026-09-20)

E8 finished all 32 lanes (cleanup job 7639377), so the E9C freeze's own condition "small/medium MMLU-Pro
**if** E8 has finished" is now met. `src/e9c_plan.py` was re-run unchanged; as the freeze anticipates, it
added exactly three tasks to lane 0 and three to lane 1 (MMLU-Pro fit/cal/dev, 23,282 new prefills) and
left lanes 2 and 3 untouched. Previous plan kept as `jobs/LANE_PLAN_prev.json`.

| UTC | Change | Reason | Model output existed? |
|---|---|---|---|
| 2026-09-20T19:47:00Z | `src/e9c_analyze.py` `frozen_q()`: added a key fallback so the E8 deployment file can be read. Old hash `aa1f0bbd…5be7` (in `PROTOCOL_FREEZE_E9C.md` §6), new hash `12693965cbc0e0ca7bb822015786db5eec783c77c9e4b2ffa0a37606bcc2c203`. Previous version kept verbatim as `src/e9c_analyze_v1.py.bak`. | E8 names its deployments `small/Text`, `small/C2C`, `medium/Text`, `medium/C2C`, while `P2_MMLU_PRO_BREADTH_STAGE1` uses `T`/`C`. The hashed lookup `dep[ref]` raises `KeyError` on the E8 file, which would abort the whole analysis. | Yes for the original 7 populations — **but** this lookup only sets the *displayed* frozen q and the derived `newly_deployed_under_sG` / `lost_deployment_under_sG` flags. It enters no AUROC, no certification, no coverage and no changed/omitted value. Re-running the patched script reproduces the 2026-09-20 seven-population results exactly; this is checked and recorded below. |

All four E8 settings carry frozen q = 0.0 (`mode: fixed_reference`), so each one falls back under
ProbeMax and any of them that certifies under s_G is a newly deployed setting under protocol E9C.

### Verdict field on the enlarged set

`e9c_analyze.py` computes `criterion_count_met` as `len(both) == 7 and larger >= 5` and derives
`verdict` from it. With nine populations that guard is False, so `E9C_RESULTS.json` now carries
`"verdict": "INCOMPLETE"`. That is the hashed script refusing to apply a rule that was prespecified
for seven populations to a set of nine — **not** a failed hypothesis. `criterion_mean_met` is True and
Text exceeds C2C in 9 of 9. The prespecified seven-population verdict is preserved unchanged in
`analysis/E9C_RESULTS_7pop_original.json` and is **SUPPORTED**. The nine-population figures are
reported separately and labelled an extension; no prespecified rule is restated over nine populations.
