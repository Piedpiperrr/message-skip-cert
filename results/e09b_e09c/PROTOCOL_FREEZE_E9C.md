# PROTOCOL FREEZE — E9c (helper-aware gate score s_G)

Paper A (ICLR 2027), ClusterA. Stage `P2_R3_E9BC_20260920T061042Z`.
Frozen on the ClusterA login node **before any E9c model output existed**. Any later change is a
deviation, recorded in `DEVIATIONS.md` with a UTC timestamp before any E9c calibration or development
result is read. E9c is additive: it writes only inside this stage and modifies no frozen file.

## 1. Protocol (verbatim, as issued)

Hypothesis H: receiver confidence ranks C2C-induced answer changes better than Text-induced ones because
Text-induced changes follow the helper's own answer, which the receiver cannot see. Prediction: adding a
helper-agreement gate raises the development AUROC for Text-induced changes more than for C2C-induced
changes (mean change in AUROC over the 7 populations larger for Text, and larger in at least 5 of 7
populations). Score: s_G(x) = u_R(x) + 1[argmax_H(x) != argmax_R(x)], where argmax_H comes from one helper
prefill of the question and options in the helper's own chat template followed by the separately encoded
literal "The correct answer is", with the same label-token rule and renormalization over the displayed
labels as ProbeMax, and argmax_R is the frozen ProbeMax argmax. Certification is otherwise the main
protocol: 20 fit-quantile candidates of s_G (19 quantiles plus q=1), alpha=.05, per-candidate p<=.001,
largest accepted q, separate family. Settings: the 14 main settings; the large Text+fact setting (helper
prefill without the fact; the variant with the fact is descriptive); and small/medium MMLU-Pro if E8 has
finished. Report per setting: development AUROC of s_G and of u_R for receiver-reference disagreement and
their difference; certified q, development coverage, and changed/omitted under s_G; the mean component
latency of the helper prefill on the frozen replay panels. Any setting that falls back under ProbeMax but
deploys under s_G gets one end-to-end replay on this hardware (the policy runs both probes; frozen panel;
E3 replay protocol), reported by class only. All outcomes are reported; the analysis is labeled post hoc.

## 2. Score definition, made concrete

- `u_R(x)` = the **frozen, saved** `ProbeMax` of the receiver probe = `1 - max_l p_l`, where `p` is the
  FP32 `log_softmax` over the per-question displayed labels of the label-token logsumexps. Verified:
  `ProbeMax == 1 - max(p_labels)` on the frozen records.
- `argmax_R(x)` = the **frozen, saved** `argmax_probe_label`. Neither is recomputed.
- `argmax_H(x)` = the argmax of the same construction run on the **helper of the same pair**:
  `apply_chat_template([{role:user, content: receiver_prompt(row)}], tokenize=False,
  add_generation_prompt=True, enable_thinking=False)`, then the separately encoded literal
  `"The correct answer is"` (`add_special_tokens=False`, no trailing space) concatenated as token ids;
  one forward of `lm.model`, `use_cache=False`, logits of the last valid position through `lm.lm_head`,
  cast to FP32; per displayed label a `logsumexp` over that label's token set; `log_softmax` over the K
  displayed labels; `argmax` of the result. bf16, `attn_implementation='sdpa'`, batch 1, no generation.
- Label-token rule (unchanged): own tokenizer, non-special single tokens whose
  `decode(...).strip()` equals the actual displayed label; dynamic K per question; renormalization over
  that question's K labels only.
- `s_G(x) = u_R(x) + 1[argmax_H(x) != argmax_R(x)]`. Because `u_R in [0,1]`, a helper that disagrees with
  the receiver probe lifts the question above every finite threshold at or below 1, i.e. the gate stops
  omitting the reference on exactly those questions.

The prompt reconstruction used for the helper was verified on the login node to reproduce the frozen
receiver probes **bit for bit**: for 5 large/OBQA fit rows, both `rendered_sha256` and `probe_ids_sha256`
match `P2_ZERO_GOLD_CONTROLS_20260914T065145Z/records/probe_records.jsonl` exactly.

## 3. Certification (the main protocol, score replaced)

- Thresholds: the 19 fit quantiles of `s_G` by integer rank `vals[ceil(j*N_fit/20)-1]`, FP32 ties
  retained, plus `q=1` -> `Infinity`.
- Calibration: omit set `{i : s_G_i <= threshold}`; `changed` `k = sum 1[o_R != o_b]`;
  `p = BinomialCDF(k; n, .05)`; accept iff `p <= .001`; Clopper-Pearson upper at .999 reported.
- Deployment: the largest accepted q; `fixed_R` at q=1; fallback to the fixed reference if none accepted.
- Separate family: 20 candidates per setting, alpha=.05, not pooled with the frozen ProbeMax family.
- Verified before freezing: with `argmax_H := argmax_R` (so `s_G == u_R`) this code reproduces the frozen
  deployed q of **all 14 main settings** exactly (0, 0, 0, 0, 0, .55, 0, .6, .8, .8, .95, .9, .4, .4).

## 4. Settings and populations

7 populations x 2 references = the 14 main settings:
small/OBQA, small/ARC, medium/OBQA, medium/ARC, large/OBQA, large/ARC, large/MMLU-Pro, each with
reference `T` (Text) and `C` (C2C). Plus `large/OBQA/Text+fact` (frozen q=.75), whose **primary** helper
prefill is taken without the fact and is therefore literally the large/OBQA prefill; the with-fact prefill
is run as a descriptive variant only. small/MMLU-Pro and medium/MMLU-Pro are included **iff** every E8
lane has written `LANE_COMPLETE.json` at plan time; otherwise they are reported as not available.

Splits and sizes (fit / cal / dev representatives): OBQA 2100/1366/742; ARC 670/448/299;
MMLU-Pro 3000/6000/2641. Helper prefills are computed on the union of the three representative sets.

## 5. Sources bound by this freeze

| role | path | identity |
|---|---|---|
| receiver probes, large/OBQA | `P2_ZERO_GOLD_CONTROLS_20260914T065145Z/records/probe_records.jsonl` | 4,208 rows |
| receiver probes, small+large OBQA/ARC | `P2_CONFIDENCE_REFERENCE_BOUNDARIES_20260914T165012Z/records/{pair}_{ds}_{split}_probes.jsonl` | |
| receiver probes, medium | `P2_MEDIUM_PAIR_BOUNDARY_EXTENSION_STAGE1_20260915T144407Z/execution_retry1_20260915T164957Z/probes/` | |
| receiver probes, large/MMLU-Pro | `P2_MMLU_PRO_BREADTH_STAGE1_20260916T002337Z/shards/{1,2}/probes/` | |
| machine answers, small+large | `P2_SCORING_V2_20260912T191445Z/labels/full_{train,development}_P2_SCORING_V2.jsonl`, fields `o_R,o_T,o_C` only | parser SHA-256 `d05978f4…cf2f9` |
| machine answers, medium / MMLU-Pro / E8 | the `actions/` files of the stages above | |
| Text+fact answers | `P2_R2_GPU_20260919T220941Z/e6/main/e6_shard{0..3}.jsonl` | 2,108 rows, cal+dev |
| fact1 | `allenai--openbookqa/additional/train-00000-of-00001.parquet` | |
| helper, small | Qwen/Qwen2.5-0.5B-Instruct @ `7ae557604adf67be50417f59c2c2f167def9a775` | |
| helper, medium | Qwen/Qwen2.5-1.5B-Instruct @ `989aa7980e4cf806f80c7fef2b1adb7bc71aa306` | |
| helper, large | Qwen/Qwen2.5-7B-Instruct @ `a09a35458c702b33eeacc393d103063234e8bc28` | |
| helper chat template (all three) | | SHA-256 `cd8e9439f0570856fd70470bf8889ebd8b5d1107207f67a5efb46e342330527f` |
| replay panels | `…BOUNDARIES…/inputs/{obqa,arc}_panel_ids.json` key `dev` (128 each); `…MMLU_PRO_BREADTH_STAGE1…/splits/candidate_e2e128_ids.json` (128) | each a subset of the dev representatives, so panel latency is read from the main batch-1 records |

## 6. Code frozen by this file

| file | SHA-256 |
|---|---|
| `src/e9_common.py` | `538247a5b8556fd123a355672ef53de3be0d3b98832c4d1e3d8c2c6862c29da9` |
| `src/e9c_plan.py` | `b3fd7a55b3ad8f0cfc5a513e2a18c37731679977417519b837b0d425784cb1c7` |
| `src/e9c_prefill.py` | `64989beba5af58654a3b623afc97ded9d722a4bb905ae9d9fc3e749edccb1076` |
| `src/e9c_analyze.py` | `aa1f0bbda6a2c1079380defe82d51cb75d86bf80d2d17124c310b3069e4d5be7` |
| `src/gpu_preflight.py` | `664dab46be01fec8fbc896b91e8ddb24132260909a330b46c2932f2dcaedd882` |
| `src/slot.sh` | `43dc762840c1209059c4ddcddfaa4e542648c760f56cb21cee05f61da27fb23d` |
| `run_e9c.pbs` | `65bd5367b02553616dad006305deb3cc5d56ff6746632034a71b530f9280ecdf` |
| `jobs/LANE_PLAN.json` (at freeze time) | `8d1669718c92cac8c4737227186b05025bea5782e59e594c5abd5cbb17b5c6b2` |

`jobs/LANE_PLAN.json` is a derived artifact of `src/e9c_plan.py`; its only run-to-run input is whether
every E8 lane has completed. If it is regenerated before submission the new hash is recorded in
`jobs/SUBMISSION.json`; the builder itself is frozen by the hash above.

## 7. Execution and reporting rules

- One ClusterA debug job, `select=1`, `walltime=00:50:00`, `fsreq=<fs>`, 4 lanes (1 A100 each).
  The lane is shared with E8: if a running and a queued job are already held, nothing is submitted.
- Validation runs first **inside** the job: 16 fit rows per pair, reporting the argmax label distribution
  and any failure. No gold.
- Required populations run before the descriptive and conditional ones, so a walltime overrun can only
  cost the with-fact variant or the E8-dependent populations. Skipped work is recorded, not estimated.
- No gold label, no correctness field, no generation, no receiver forward and no fuser is loaded anywhere
  in E9c. The analysis projects only `o_R`, `o_T`, `o_C` (and `o_Tf` from E6).
- Latency is the mean of the batch-1 helper-prefill component timings on the frozen replay panel rows.
- Every setting is reported whatever its outcome, including settings that lose their deployment under
  s_G. The whole analysis is labeled **post hoc**.
- A setting that falls back under ProbeMax but deploys under s_G gets one end-to-end replay under the E3
  replay protocol on the frozen 128-question panel, reported by class (+ / - / ?) only.
