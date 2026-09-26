# E19 pre-registration (P2_R8_E19_20260921T224942Z)

Written on the ClusterA login node after the Step 0 reproduction checks (REPRO.md, 49/49 PASS) and before any E19 computation.
Nothing below changes after numbers are seen. Deviations go to DEVIATIONS.md.

=== PRE-REGISTRATION BLOCK (verbatim, as issued) ===

----- BEGIN PREREG BLOCK -----
E19 (CPU, stored outputs only).
E19-1 (saving decomposition). For each deployed policy with a 128-question panel replay (the eight large/medium Qwen policies in the
configuration that Table 2 reports; Llama OBQA/ARC and Text+fact in the second configuration), and for the full 2,641-question MMLU-Pro C2C
replay, split the paired mean saving (1/N) * sum_i (fixed_i - policy_i), all requests kept, into three parts: omitted questions with
u == 0.0 (as stored), omitted questions with u > 0, routed questions; report each part in ms and its question count. State the source of
u and of the route, and report the number of questions whose logged route differs from 1[u <= tau]. Also report a recomposed "omit only if
u == 0" saving: for omitted questions with u > 0, replace policy_i by fixed_i + probe_i, where probe_i is that request's logged probe stage
time if logged per request, otherwise the median of (policy_i - fixed_i) over routed questions in the same run (state which); 95% interval
by paired bootstrap over questions (seed 0, 2,000); labeled recomposed. In the same table, add the coverage and change rate of the u = 0
part and of the u > 0 increment on dev, held-out and sealed data from E14-2 / E17-1 (no recomputation).
Share definition: gross share = (u > 0 part) / (u = 0 part + u > 0 part); also report the u > 0 part as a share of the net total.
Writing rule: an appendix table; the main text gives the range of the gross share across the nine Qwen-receiver policies whose net-saving
interval excludes 0 (others reported separately); if the gross share is >= 50% for any such policy, the main text names that policy.
E19-2 (INVALID among certified changes). For each deployed policy and each available split (dev; held-out OBQA; sealed ARC; the E16
out-of-sample tests) plus a pooled out-of-sample row per policy, split the changes among omitted questions into: both parse and differ /
only R INVALID / only the reference INVALID (two INVALIDs count as agreement, the paper's convention). Writing rule: if for any policy
>= 50% of the changes among omitted questions involve exactly one INVALID, on dev or pooled out of sample, the main text names that policy
and says so next to the C2C redundancy sentence (or the corresponding Text sentence); otherwise one appendix sentence with the range.
E19-3 (panel representativeness). For each policy with a panel: panel vs full development population on question length (receiver
tokenizer), helper message length (helper tokenizer; Text only), receiver-only output length, reference output length (receiver
tokenizer), u == 0 share and coverage (share omitted at the deployed threshold); means, medians, standardized mean difference
(difference of means divided by the SD of the full population). Latency: compare panel vs full population only within one run of one
configuration where full-population per-request end-to-end latencies (fixed and policy) exist, e.g. the panel's rows inside the full
2,641-question MMLU-Pro C2C replay vs all rows of that same run; otherwise state "lengths only". Also give the Eq. 4 saving computed with the
component means of the Table 2 panel replay and (i) the panel coverage, (ii) the full-population coverage. Writing rule: if any policy has
|coverage difference| > 10 points or |SMD| > 0.2 on a length variable, the appendix names it and Sec. 4.4 adds a caveat; otherwise one
appendix sentence that the panels match the full populations on these variables.
E19-4 (prospective prediction). Apply the frozen E15-1 fit-split plug-in predictor (verify its code hash; change input paths only) to the
Llama OBQA/ARC settings and the two stronger-helper settings (E16-5); add Text+fact and GSM8K as N/A rows (no fit reference outputs).
Report predicted vs actual deploy/fallback (primary definition of "correct"), the q difference in grid steps and the coverage error
(saving only where component latencies exist). Record the E15 PREREG time and each setting's first output time; a prediction counts as
prospective only if the predictor was hashed before that setting's first output. Do the same timing check for the E17-5 binormal model
and the E16-5 settings. Writing rule: Sec. 5 reports "k of n prospective predictions correct" for each predictor, with non-prospective
ones reported separately.
E19-5 (pass criteria). Quote verbatim, with file path and hash, the sentences that define "pass" in the hashed protocols of the held-out
OBQA tests (E9b and its amendment, including its separate p <= .001 sentence for large OBQA Text), the sealed ARC test, and the E16
out-of-sample tests. List all ten out-of-sample tests on their original populations and the frozen parser (e.g. sealed Text 20/1100, C2C
11/1047) with n, k, exact binomial p (H0: rate >= .05), two-sided 95% Clopper-Pearson upper bound, pass at p <= .001 (yes/no), pass at
CP upper < 5% (yes/no), and which criterion its own protocol specified. Writing rule: Sec. 4.5 states each protocol's criterion as quoted.
If any protocol specified p <= .001 (or anything other than CP upper < 5%), every test failing its own criterion is named as failing in
Sec. 4.5 and the abstract's out-of-sample sentence is amended.
E19-6 (prompts and parser). Copy E13's PROMPTS_AND_PARSER.md; check that every prompt template in it matches the frozen prompt-building
code and that the parser rules match the frozen parser V2 (report code hashes). List any prompt used in the paper that the file lacks
(e.g. MMLU-Pro A-J variant, Llama/OLMo receiver templates, Text+fact helper line, helper-aware prefill, GSM8K prompts) and append those
templates verbatim, extracted from the frozen code as strings (not code). Add one fully rendered example per path (helper Text prompt,
receiver-only, receiver-with-message, probe, for Qwen3, Llama-3.1 and OLMo receivers) produced with the tokenizer's apply_chat_template on
one fit question, showing the chat-template and system strings (including Qwen3's enable_thinking=False markers and Llama's default system
header). Re-run an anonymity scan (user names, /lus paths, allocation or machine names, e-mail addresses). Save as PROMPTS_FOR_APPENDIX.md.
E19-7 (other receivers). Search all project output directories for any model output produced with a Mistral or Granite model (or any
non-Qwen receiver other than OLMo-2 and Llama-3.1-8B). Report what exists (tokenizer/template loading in X3 Step 0 is not an output).
Writing rule: if none, Appendix N says no other receiver produced outputs; otherwise it lists them.
----- END PREREG BLOCK -----

=== RESOLVED PATHS AND OPERATIONAL BINDINGS (fixed now, before any E19 computation) ===

Paths are relative to the project root `iclr2027_p2/`. Labels everywhere: frozen parser V2
(`P2_SCORING_V2_20260912T191445Z/scoring_v2.py`, SHA-256 d05978f4...c2f9), unparseable = `INVALID`, two INVALIDs = agreement.
No gold field is used by any E19 computation. (Some frozen record files that the reused loaders open also carry a gold column,
e.g. `P2_SCORING_V2_.../labels/full_*_P2_SCORING_V2.jsonl`, `P2_6_.../results/dev_cases.jsonl`; that column is never read into
any E19 quantity.) Bootstrap everywhere: `numpy.random.default_rng(0).integers(0, N, (2000, N))` over questions in panel-id order,
interval = `np.quantile(means, [.025, .975])` (the replays' own method; Step 0 (b) reproduces the stored intervals with it).

Reused loaders (imported unchanged): `P2_R7_E17_20260921T183100Z/scripts/e17_common.py` (dev/cal/fit arrays of the 10 Qwen rows via
E13 -> E11 loaders, and X3 Llama-3.1-8B records), `P2_R6_E15_20260921T072336Z/scripts/e15_common.py` (`original_replay`,
`component_dev`), `P2_R4_E11_20260920T224016Z/scripts/e11_common.py` (`raw`, dev raw outputs).

Policy rows (12): large OBQA Text q=.80 [nominal], large OBQA C2C q=.80 [nominal], large ARC Text q=.95, large ARC C2C q=.90,
large MMLU-Pro Text q=.40, large MMLU-Pro C2C q=.40, medium OBQA C2C q=.55 (+ q=.50 sensitivity row), medium ARC C2C q=.60,
large OBQA Text+fact q=.75, Llama-3.1-8B OBQA Text q=.60, Llama-3.1-8B ARC Text q=.70. Frozen tau = stored numeric thresholds
(Step 0 (a)).

E19-1
- Replays (paired by question id; fixed_i, policy_i = `latency_ms` of the fixed-reference and policy requests):
  - Table 2 / original configuration: large OBQA/ARC x Text/C2C `P2_FROZEN_POLICY_E2E_VALIDATION_20260914T174120Z/records/e2e_requests.jsonl`
    (panels `inputs/{obqa,arc}_panel_ids.json`); medium OBQA/ARC C2C `P2_MEDIUM_PAIR_E2E_STAGE2_20260915T205303Z/records/e2e_requests.jsonl`
    (panels `inputs/{obqa,arc}_panel_ids.json`); large MMLU-Pro Text/C2C `P2_MMLU_PRO_E2E_STAGE2_20260916T212147Z/records/four_arm_requests.jsonl`
    (panel = `protocol/bootstrap_indices.npz` ids). Selection exactly as `e15_common.original_replay`.
  - Second configuration: Llama OBQA/ARC `P2_R7_E16_20260921T184114Z/replay_llama/records/e2e_requests.jsonl` (panels
    `replay_llama/inputs/{obqa,arc}_panel_ids.json`); Text+fact `P2_R2_E7_20260919T231531Z/e6replay/records_e6/e6_replay_requests.jsonl`
    (panel `e6replay/inputs/obqa_panel_ids.json`, arms fixed_TF / policy_TF).
  - Full MMLU-Pro C2C: `P2_R1_E3POL_MMLU_C2C_FULL_20260919T075315Z/records/four_arm_requests.jsonl` (arms fixed_C / policy_C;
    order = `protocol/bootstrap_indices.npz` ids; N = 2,641).
- u = the policy request's logged online probe `probe.ProbeMax` (as stored, FP32 value). Route = the policy request's logged
  `selected` (omitted iff `selected == 'R'`). tau = the frozen numeric threshold of the policy (the record's own `threshold` field
  where present, otherwise the deployment file; both must agree where both exist). Route mismatches = #{i: (selected_i == 'R') != (u_i <= tau)}.
- Parts: A0 = (1/N) sum over omitted with u == 0 of (fixed_i - policy_i); A+ = same over omitted with u > 0; B = same over routed.
  Net = A0 + A+ + B. Gross share = A+ / (A0 + A+) (undefined if A0 + A+ = 0); A+ / Net also reported. Net 95% interval by the bootstrap.
- probe_i = the policy request's logged probe stage time: `parts_ms.probe_ms` (large original, Llama, Text+fact) or
  `parts_ms.online_probe_ms` (medium, MMLU-Pro, full MMLU-Pro C2C). All replays log it per request, so the "median over routed"
  fallback is not needed (stated per row). Recomposed saving = (1/N) sum_i s'_i with s'_i = -probe_i for omitted u > 0 and
  s'_i = fixed_i - policy_i otherwise; 95% bootstrap interval; labelled "recomposed".
- u = 0 part / u > 0 increment coverage and change rate (no recomputation): dev, held-out 744 OBQA and sealed ARC rows of
  `P2_R6_E14_20260921T052241Z/results/E14_2_zero_u.csv` (coverage n0/N and n+/N; change rates k0/n0 and k+/n+); Llama dev rows of
  `P2_R7_E17_20260921T183100Z/results/E17_1_u0_rule.csv` (n0 = 0). Llama held-out/ARC-test u = 0 counts are added, labelled, from
  `P2_R7_E16_20260921T184114Z/results/analysis_oos/OOS_RESULTS.json`; the u > 0 increment there = the whole omitted set (stored n, k).
- "Nine Qwen-receiver policies" = the eight Table 2 policies + Text+fact. "Net-saving interval excludes 0" = the 95% bootstrap interval
  of Net (all requests) lies entirely above or below 0.

E19-2
- Changes among omitted questions (omitted = at or below the frozen tau), classified: both parse and differ (o_R != o_b, neither
  INVALID); only R INVALID (o_R = INVALID, o_b a label); only reference INVALID (o_b = INVALID, o_R a label). Share with exactly
  one INVALID = (only R + only ref) / k.
- Splits and sources: dev = the reused loaders (all 12 rows); held-out 744 OBQA = `P2_R3_E9BC_20260920T061042Z/analysis/SEALED_ROUTES.jsonl`
  (`R_answer`, `reference_answer`, `omitted`; 5 rows: large OBQA Text/C2C, medium OBQA C2C q=.55/.50, Text+fact); sealed ARC =
  `P2_FINAL_SEALED_ARC_CONFIRMATION_20260914T211958Z/records/paired_sealed_2344.jsonl` (`policy_answer` on routed = o_R,
  `reference_answer`; large ARC Text/C2C); E16 out-of-sample = `P2_R7_E16_20260921T184114Z/results/analysis_oos/routes_{llama_obqa,
  llama_arc,medium_arc_C}.jsonl` (`o_R`, `o_ref`, `omitted`). Each split's k must equal its stored changed count (checked).
- Pooled out-of-sample row per policy = sum over that policy's out-of-sample splits (held-out, sealed, E16); "none" for large
  MMLU-Pro Text/C2C (no out-of-sample test).
- Writing-rule rows: the 11 deployed policies (medium OBQA C2C at q = .55); the q = .50 row is reported but does not trigger.

E19-3
- Panels: the E19-1 panel ids of each of the 11 policies with a panel. Full development population = the policy's dev split
  (742 OBQA / 299 ARC / 2,641 MMLU-Pro representatives, as loaded). Every panel id must be in the dev population (checked).
- Tokenizers (local files only, no weights): receiver Qwen3-8B `hf_cache/hub/models--Qwen--Qwen3-8B/snapshots/b968826d...`;
  Qwen3-1.7B `P2_MEDIUM_PAIR_E2E_STAGE2_20260915T205303Z/assets/receiver`; Llama-3.1-8B `hf_cache/hub/models--meta-llama--Llama-3.1-8B-Instruct/snapshots/0e9e39f2...`;
  helper Qwen2.5-7B-Instruct `P2_6_20260910T164138Z/assets/Qwen2.5-7B-Instruct` (all Text policies, including Llama and Text+fact,
  read Qwen2.5-7B messages).
- Question length = token count (receiver tokenizer, `add_special_tokens=False`) of the question block
  `question_stem + "\n\nChoices:\n" + choices_block(choice_text)` (choices_block from `P2_R1_EXP_20260919T050555Z/src/receiver_prompt.py`).
  Question sources (no gold): OBQA/ARC `P2_CONFIDENCE_REFERENCE_BOUNDARIES_20260914T165012Z/inputs/{obqa,arc}_dev_queries.jsonl`;
  MMLU-Pro the `query` field of `P2_MMLU_PRO_BREADTH_STAGE1_20260916T002337Z/shards/2/actions/dev.jsonl`.
- Helper message length (Text policies) = token count (Qwen2.5-7B tokenizer, no special tokens) of the stored helper message of that dev
  question: large OBQA/ARC `helper_message` of the Text record behind the V2 `source_T` pointer; MMLU-Pro `output.helper_message` of the
  T record; Text+fact `helper_message` in `P2_R2_GPU_20260919T220941Z/e6/main/e6_shard*.jsonl`; Llama = the large pair's stored Text
  message (asserted equal to the X3 record's `T.helper_message_sha256`).
- Receiver-only / reference output length = token count (receiver tokenizer, no special tokens) of the stored dev raw outputs
  (`e11_common.raw(s, 'dev', ids)`; Llama: X3 `R.raw` / `T.raw`).
- u == 0 share and coverage: dev stored u (u == 0.0; u <= tau). Summaries: mean, median, and SMD = (mean_panel - mean_full) / SD_full
  (population SD, ddof = 0, of the full dev population; the panel is included in the full population).
- Latency: only the full MMLU-Pro C2C run qualifies: panel rows (the 128 MMLU-Pro panel ids) vs all 2,641 rows of that run: mean
  fixed, mean policy, mean saving, median saving. All other policies: "lengths only".
- Eq. 4 (paper eq:saving): kappa * mean_{omitted}(c_b - c_R) - mean_{all}(c_s), with the Table 2 (or second-configuration, for Llama
  and Text+fact) panel replay's per-request components: c_b = fixed latency, c_R = policy latency - probe_i on omitted panel
  questions, c_s = probe_i on all panel questions; (i) kappa = replay panel coverage (omitted/128); (ii) kappa = full dev coverage.

E19-4
- Predictor: `P2_R6_E15_20260921T072336Z/scripts/e15_1.py` executed byte-identical (its SHA-256 is recorded and must equal the value
  recorded here at hash time: d6bfc055f3db73af06e8c8e61bfcc9d277c54125ae74c5ed6db622c3e26ab485) via exec of its source with a
  substitute `e15_common` module whose inputs are redirected (settings list, loaders, output writer); nothing else changes. Verification:
  the same harness with the original 25 settings must reproduce E15's stored `e15_1_candidates.csv` and `e15_1_per_setting.csv`
  predicted columns exactly.
- New settings: Llama OBQA/ARC Text (X3 fit/cal/dev via `e17_common.load`; stored cuts = fit order statistics; actual q .60/.70);
  strong-helper OBQA/ARC Text (E16-5: `P2_R7_E16_20260921T184114Z/results/e16_5/shard*.jsonl` T.parsed; R answers and ProbeMax from
  `P2_MEDIUM_PAIR_BOUNDARY_EXTENSION_STAGE1_20260915T144407Z/execution_retry1_20260915T164957Z/{actions,probes}/{ds}_{split}.jsonl`;
  units = medium `splits/{ds}_{split}_representatives.json`; thresholds = medium `thresholds/{ds}.json`; actual: fallback on both).
  Text+fact and GSM8K: N/A rows.
- Correct = predicted deploy/fallback equals actual. Grid steps = (q_hat - q) * 20 where both deploy. Coverage error = |actual dev
  coverage - predicted fit coverage|. Saving (only where component latencies exist): Llama: c_b, c_R, c_s = dev means of X3 `T.latency_ms`,
  `R.latency_ms`, `P.latency_ms`; measured = E16-4 replay mean (all requests); E15 formula (fit-predicted coverage x gap - c_s).
- Timing: predictor hash time = `PREREG_E15.md` hashed 2026-09-21T07:23:54Z (the rule is fully specified there); the code file's
  mtime is also reported. First output time per setting = min `utc` over that setting's model-output records (X3
  `results/runs/chain_*.jsonl` per dataset; E16-5 `results/e16_5/shard*.jsonl` per dataset; Text+fact `e6/main`; GSM8K E10 records).
  Prospective iff predictor hash time < first output time. Binormal (E17-5): hash time = E17 `PREREG.md` 2026-09-21T18:31:26Z vs the
  E16-5 settings' first output times; its E16-5 predictions read from `results/analysis_e16_5/E17_5_on_E16_5_binormal.csv`.

E19-5
- Protocol files: E9b `P2_R3_E9BC_20260920T061042Z/PROTOCOL_FREEZE_E9B.md` (+ `.sha256`, `.utc`) and `PROTOCOL_AMENDMENT_E9B.md`;
  sealed ARC `P2_FINAL_SEALED_ARC_CONFIRMATION_20260914T211958Z/USER_PROMPT_ZH.md` (hashed in `PROTOCOL_FREEZE.json`); E16
  `P2_R7_E16_20260921T184114Z/PREREG.md` (+ `PREREG.sha256`). Quotes are copied from these files and their SHA-256 recomputed;
  if a protocol contains no sentence defining "pass", that is reported as such (no sentence is supplied from elsewhere).
- The ten tests: held-out OBQA large Text, large C2C, medium C2C q=.55, medium C2C q=.50, Text+fact (E9b); sealed ARC large Text,
  large C2C; E16-1 Llama OBQA (744), E16-1 Llama ARC (1,172), E16-2 medium ARC C2C (1,172). n, k from the stored per-row files
  (E19-2 sources); p = P[Bin(n, .05) <= k]; CP upper = two-sided 95% Clopper-Pearson.

E19-6
- Copy `P2_R5_E13_20260921T031606Z/PROMPTS_AND_PARSER.md`. Frozen code checked: helper instruction `P2_10_20260911T122423Z` legacy_methods
  (BACKGROUND_PROMPT), receiver `P2_R1_EXP_20260919T050555Z/src/receiver_prompt.py`, probe prefix `P2_CONFIDENCE_REFERENCE_BOUNDARIES_.../src/run_boundaries.py`,
  Text+fact `P2_R2_GPU_20260919T220941Z/e6/PROTOCOL_FREEZE_E6.md` and e6 code, Llama/OLMo `P2_R6_X3_20260921T052602Z/src/{xfam_common,run_x3}.py`
  and `P2_R1_XFAM_20260919T095058Z/src`, helper-aware prefill `P2_R3_E9BC_20260920T061042Z/src/e9c_prefill.py`, GSM8K
  `P2_R4_E10_20260920T225954Z/src/e10_prompts.py`; parser `scoring_v2.py`. Templates extracted as strings from these files.
- Rendered examples: OBQA fit question 14-1371 (as E13), tokenizers Qwen3-8B / Qwen2.5-7B, Llama-3.1-8B, OLMo-2-1124-7B-Instruct
  (`hf_cache/hub/models--allenai--OLMo-2-1124-7B-Instruct/snapshots/470b1fba...`), `apply_chat_template(..., add_generation_prompt=True)`
  (`enable_thinking=False` for Qwen3), exactly as the frozen code calls it.
- Anonymity scan of PROMPTS_FOR_APPENDIX.md: case-insensitive for `user`, `user`, `/lus`, `/home`, `sharedfs`, `project`,
  `ClusterA`, `ClusterB`, `the-cluster`, `cluster.invalid`, `<redacted-site>`, and e-mail addresses (`[\w.+-]+@[\w-]+\.[\w.]+`).

E19-7
- Search every directory under the project root (all `*.jsonl`, `*.json`, `*.csv`, `*.md`, `*.txt`, `*.log` files) for
  `mistral` and `granite` (case-insensitive), and every record's receiver/model field for values other than Qwen*, Llama-3.1-8B,
  Llama-3.2-1B (X1 helper), OLMo-2; classify each hit as model output / tokenizer-template check / download manifest / text mention.
  Also list the hf_cache model directories present.
