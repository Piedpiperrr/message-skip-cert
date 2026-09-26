# E21 deviations and interpretation choices (P2_R9_E21_20260922T065220Z)

1. Exposure (PREREG sentence "no calibration lost-correction count is known to the authors"). REPRO (h) found one earlier result that
   contains calibration lost-correction counts, for large/OBQA/Text+fact only: `P2_R2_GPU_20260919T220941Z/e6/E6_RESULTS.md` line 44 and
   `e6/analysis/E6_RESULTS.json` (`/cal/at_deployed_q/corrective_on_omitted` = 18 at q = .75; whole calibration split corrective = 122,
   i.e. k_L at the q = 1.00 candidate). E21-1 recomputes k_L(tau_frozen) = 18 for Text+fact. The PREREG text is kept verbatim. The paper's
   exposure statement needs amending for Text+fact, which is already flagged nominal.
2. E21-2 (iii)/(iv) on held-out OBQA 744: not computed ("not stored"). The E16-3 score m comes from bf16 label logits, and E16-3 stored
   those for fit/cal/dev units only. The held-out records (E9b) store only float32 p_labels. A p_labels-based log non-max mass would be a
   different score, so it was not substituted (see NEEDS in the report).
3. Interpretation choices, fixed before the corresponding numbers were seen:
   - D_seq: "the first REJECTED candidate in increasing order" means the first candidate rejected by the L-test at that eps (the L-test is
     the one the PREREG says forms a prefix). D_dep = N/A when q_joint = NONE. For the two infeasible cases (ARC, N = 448 at eps = .01),
     every L-test rejects, so the first rejected candidate is q = .05 and D_seq = D_need = its disagreements (0 in both ARC settings).
   - C \ X: both the frozen change-rate test and the L-test are recomputed on C \ X with N' = |C \ X|, using the same 20 frozen thresholds.
     X is `e11_common.exposed_ids` (341 ids: 208 OBQA, 133 ARC). All of them are calibration representatives, so N' = 1158 (OBQA) and 315 (ARC).
     MMLU-Pro has no X, so C \ X = C.
   - "Counted": eps <= G_dev / 2 is evaluated exactly (fractions of correct counts over N_dev), with dev coverage >= 20% at tau_joint.
   - E21-1 out-of-sample and panel: frozen-policy rows are reported next to the joint rows for comparison (descriptive). On sealed ARC,
     acc(R) and retention are N/A. On held-out 744 and the E16 ARC test, R is stored for all questions, so retention is reported there.
   - Panel: the policy request's logged u (probe.ProbeMax) and route are used as in E19-1. Questions routed to R at the frozen tau with
     u > tau_joint get saving -probe_i (logged per request, `parts_ms.probe_ms` or `parts_ms.online_probe_ms`). No fallback was needed.
     Route mismatches vs u <= tau_frozen: 0 on every panel.
   - E21-2 (ii) bootstrap: `default_rng(0).integers(0, n, (2000, n))` over the u > 0 questions; single-class resamples dropped and counted
     (0 dropped everywhere); percentile interval. AUROC = `e17_common.auroc` (sklearn; ties 1/2). SQuAD "u = 0" means s2 == 0.0.
   - E21-3a: R = the saved receiver-only answer of the dev representatives (frozen V2 labels, INVALID-normalized). Parseable-only = neither
     R nor V1 INVALID. Missing V1 records: 0 in every population. Supplementary lines (not in the PREREG, not used by the rule): V0 (the same
     job's unchanged receiver-only replay) vs saved R, 0 changes in all 7 populations.
4. Exposure scan scope: the stage scan (scripts/step0h_exposure_scan.py) reads result-type text files (.csv/.json/.md/.txt/.tex <= 5 MB).
   It skips raw model-record .jsonl files, whose fields are per-question outputs, not computed counts. A first broader scan that included
   .jsonl was stopped after ~7 min for the CPU budget.
5. Not caused by this stage: during the run, another session's stage `P2_R9_E21B_20260922T065040Z` (created 06:50:40Z, PBS job 7643984)
   was active, and `P2_10_20260911T122423Z/__pycache__/runtime.cpython-310.pyc` / `scoring.cpython-310.pyc` were rewritten at 06:53Z. None
   of this stage's runs imported a P2_10 module (logs/*_run.json files_read contain no P2_10 .py file), and this stage wrote only under its own
   folder (plus the session scratchpad).

6. Exposure statement (authors' wording, added 2026-09-22T08:12:09Z after the report): The PREREG exposure sentence was incomplete: E6 (P2_R2_GPU_20260919T220941Z/e6/E6_RESULTS.md, line 44) had reported Text+fact's calibration lost-correction count at q=.75 (18 of 999 omitted) and over the whole split (122); it was not among the numbers used when fixing eps, the coverage bar, or the gain condition, but it was on record.
   Also per the authors: E21-2 (iii)/(iv) on held-out OBQA 744 stay "not stored" (no substitute m).
