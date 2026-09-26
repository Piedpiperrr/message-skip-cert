# PREREG_E18 — frozen test of a pre-answer (derivation-prefix) score on the E10 GSM8K split

Stage: `P2_R8_E18_20260922T003446Z` (project root `$DATA_DIR`). Step 0 gates: `GATE.md` (ClusterB login node, shared filesystem);
dry run repeated on the ClusterA login node (`dryrun_ClusterA/`, PASS). The block below is the PREREG block of the original E18 prompt,
verbatim, with exactly two replacements (the "Preflight" paragraph, and the title sentence in "Writing rules"), set by the paper's
writing side (decisions D1 = A, D2 = A) before this file was written.

----- BEGIN PREREG BLOCK -----
E18: one frozen test of a pre-answer score on the E10 GSM8K split. It is the second pre-specified score tested on this split; it was
specified after the first (E10) fell back, and it tests the alternative that the paper itself names in Appendix P.
Population and frozen items: the E10 fit/cal/dev question IDs; the stored E10 R and Text outputs; the frozen E10 extractor and the stored
change indicator 1[o_R != o_b] (no re-extraction); alpha = .05; per-candidate delta = .001; the same 20 fit-quantile candidate grid,
tie conventions and acceptance rule as E10 (the E10 certification function is reused with only the score column replaced); deploy the
largest accepted quantile, otherwise fallback. E18 is its own family of 20 tests. With the E10 family on the same split (tested first,
E18 run only because E10 fell back), the family-wise false-deployment bound across both GSM8K families is at most .04; any GSM8K
certificate is stated at that level.
Score (fixed now): for each question, run ONE teacher-forced forward pass of the E10 receiver (same model, revision, bf16, prompt, chat
template and forward code as the E10 R-path rescoring) over [R prompt ; stored R generated tokens]. For generated positions i = 1..K with
K = 32 (all positions if the output is shorter; EOS / end-of-turn excluded), let p_i be the distribution from which generated token i was
chosen (the logits at the input position immediately before token i). Compute 1 - max_v p_i(v) in float64 from the logits as the total
probability of all non-argmax tokens (e.g. -expm1(max log-softmax)), which avoids saturation. The score is s_D = mean_i (1 - max_v p_i(v)).
Larger = more uncertain. Omit iff s_D <= tau.
Preflight (in the job, before production; no gold): on the first 16 fit rows in E10 order plus every fit row with u > 0: (a) the
teacher-forced argmax must equal the stored generated token at >= 99% of positions 1..32 pooled; (b) u and s3, computed with E10's own
definitions from this forward pass, must match E10's stored u and s3 with max absolute difference <= 1e-4; for row gsm8k_train_05081,
whose E10 re-scoring input differs from the stored generated tokens at index 315, u and s3 are checked with one extra pass over E10's
own re-scoring input. E10's s2 came from generate() scores during cached decoding, so its max absolute difference from this pass is
reported but not gated. If (a) or (b) fails, stop; production is not run. These preflight terms were set after the login-node gates
and before this PREREG was written; no E18 score existed.
Report regardless of outcome: the 20 candidates (quantile, tau, n, k, p, accepted); deployed q or fallback; dev AUROC of s_D for
disagreement (ties 1/2); if deployed, dev coverage, dev change rate with two-sided 95% Clopper-Pearson interval, and accuracy of policy vs
Text path; the share of questions whose extractor-matched final answer (the "answer is" pattern plus its number) already appears inside the
decoded first 32 generated tokens (primary), and the share whose final number appears anywhere in them (secondary); the share of outputs
shorter than 32 tokens; the share of rows with s_D exactly 0. Descriptive only (not tested, not deployable): dev AUROC for K in {1, 8, 16, 64}
and for the within-window max of (1 - max p) at K = 32.
Writing rules (Paper A). E18 is a second score on an existing setting; it does not add a setting to any count (the 30 certification
outcomes, the Sec. 5 later-settings count, the binormal count). E18 alone never changes the title; the title is decided by the rules of the E20 experiments.
(1) Deployed with dev coverage >= 10% and dev change-rate CP lower bound <= 5%: the abstract's GSM8K sentence says the answer-token score
    falls back but a second pre-specified score on the first derivation tokens, tested on the same split after the first fell back,
    certifies at the two-family level .04 (with dev coverage and change rate); Sec. 7 Scope, the conclusion and Appendix P are revised the
    same way. Value is not replayed. An Eq. 4 estimate may be given only from stored per-row timings, with the probe cost defined as the time
    of the first min(32, L) receiver decode steps (paid on routed queries, reused on omitted ones), labeled as an estimate.
(1a) Deployed with dev coverage < 10%: reported as a certificate with trivial coverage; the abstract is not changed; Sec. 7 and Appendix P
    report it as such.
(1b) Deployed with dev change-rate CP lower bound > 5%: reported as a certificate that fails its development check; the abstract is not
    changed; Sec. 7 and Appendix P report both numbers.
(2) Fallback: Sec. 7 adds one clause that a second pre-specified score, on the first 32 derivation tokens and tested on the same split,
    also falls back (dev AUROC X). If X < .80, the conclusion's forward-looking sentence says that going past multiple choice needs a score
    that ranks disagreements before the answer is written, and that neither the answer tokens nor the first derivation tokens do (AUROC
    .58 and X). If X >= .80, it says instead that the first derivation tokens rank disagreements (AUROC X) but not well enough to certify at
    this disagreement rate with this calibration size. Appendix P gets a paragraph with all reported numbers.
(3) If the primary answer-in-window share exceeds 10%, the paper does not call s_D a pre-answer score without that share next to the claim.
(4) Preflight failure, or no result by Sep 22 18:00 CDT: no test is reported; the provenance table records that a planned second GSM8K
    score was not completed.
(5) In every branch that produces a test, the provenance table in Appendix A gets a row (run after the first GSM8K fallback, testing the
    alternative named in the paper, same split, no new model outputs, teacher forcing), and Appendix P notes that the score is computed by
    teacher forcing over the stored outputs.
----- END PREREG BLOCK -----

Gate facts recorded before this PREREG: the E10 s2 range over all 1,800 R rows is .0099 to .2285 (.0163 to .1952 on fit); 0/1800 outputs are shorter than 32 tokens; E10 stored only total per-row latency_ms.

## Resolved paths and hashes (Step 0)

- E10 stage: `P2_R4_E10_20260920T225954Z` (read-only). PREREG_E10 sha256 a07185d35c84533e8a4d5c9054a60ab868a11a709c3f9ffb15276de532e0d785; frozen extractor sha256 c7f5a0f2452da787c7af1620da668f3a9824094046b3d8766b58c81831ba984c.
- Receiver: Qwen/Qwen3-8B @ b968826d9c46dd6066d109eabc6255188de91218 (local snapshot in the frozen config), bf16, sdpa, tf32 off,
  chat template sha256 a55ee1b1660128b7098723e0abcd92caa0788061051c62d51cbe87d9cf1974d8, enable_thinking=False,
  prompt = `e10_prompts.receiver_only_messages(question)`; forward = E10 `RT.rescore` (`model(input_ids=x, use_cache=False)`).
- Rows: fit R 400; cal R 1000 + T 1000; dev R 400 + T 400 (`records/main_rank{0..7}.jsonl`). Token source: stored
  `generated_token_ids` (1800/1800). Change indicator: stored frozen-extractor answers, `R.answer != T.answer` (as E10 `e10_seal.py`).
- Preflight rows: first 16 fit IDs + 21 further fit rows with u > 0 = 37 rows (22 fit rows have u > 0, one of them among the first 16).
- Certification: `src/e18_cert.py` (E10 `e10_seal.py` arithmetic, score column as parameter; reproduces E10's sealed tests, G6).

```
4fce806e4b928b8ac1c6fa74bfa59eef67a9ea42c88af2675eb16300bb7d2719  P2_R3_E9BC_20260920T061042Z/large/frozen_config.json
a07185d35c84533e8a4d5c9054a60ab868a11a709c3f9ffb15276de532e0d785  P2_R4_E10_20260920T225954Z/PREREG_E10.md
87fa87423daff217af6702411ceb83cad26285992b2951fecbc6f935b6ff0e9c  P2_R4_E10_20260920T225954Z/SPLIT_FREEZE_E10.json
a500dcc56b7364d0a0a53ea6004227b0bd7d22ef5ed90fcf343d9df06773aec7  P2_R4_E10_20260920T225954Z/splits/gsm8k_fit_ids.json
ae437bcf08aacca4e0589a8e3a756a64e6332f924fafd27c615ee33cfbb94c5a  P2_R4_E10_20260920T225954Z/splits/gsm8k_cal_ids.json
88357c81cd21ce24c66669fb4ef5c64b690cf52cc49734742b26a5f6e4403edf  P2_R4_E10_20260920T225954Z/splits/gsm8k_dev_ids.json
0bc013d2ba8713aadb6aa802c61aa0c044374a727b3dcb2afab703ff8e276d27  P2_R4_E10_20260920T225954Z/inputs/gsm8k_queries.jsonl
0b937bf8ec7dfadb41452b3f950e3c82b59dbaa0e70b455ffdb1d4a9e39bb825  P2_R4_E10_20260920T225954Z/records/main_rank0.jsonl
19e4ee3ec775b85e49f6c3875be2d6001714bbed118b7adff72541c3db642bf1  P2_R4_E10_20260920T225954Z/records/main_rank1.jsonl
287ee0b8caf98691c9f36b3809d0dd1103b0581b01423473f09701419e8c6c6d  P2_R4_E10_20260920T225954Z/records/main_rank2.jsonl
f5a6f3e947dcf1920635b9379baeb876d96fa4ecece376812a87b3a24458737e  P2_R4_E10_20260920T225954Z/records/main_rank3.jsonl
bce0628ae491de6d4a7b22e0aaa9438a176503402efcdb7c71b7ff5999131636  P2_R4_E10_20260920T225954Z/records/main_rank4.jsonl
685c3f9e4e1c18b137f3343f1ae09e326a362df626edc4c51dd36434262e465b  P2_R4_E10_20260920T225954Z/records/main_rank5.jsonl
e82611511ccfa724dcabf828e3f165e38a616216716813041f98cfee0e88a085  P2_R4_E10_20260920T225954Z/records/main_rank6.jsonl
28ea536ae97c5f53ddd39e8570a2d332fa211bfe345cd7b3e5420e2a14434e9d  P2_R4_E10_20260920T225954Z/records/main_rank7.jsonl
8cdc038b10fc45452d94c087f0ce1061da4c1aba50f8f5f6f80657eb88232620  P2_R4_E10_20260920T225954Z/src/e10_exec.py
8d5809beb9451e1670a468a3213ccc8435fdc24694c0ddf8d7742c2a86c2afc7  P2_R4_E10_20260920T225954Z/src/e10_prompts.py
c7f5a0f2452da787c7af1620da668f3a9824094046b3d8766b58c81831ba984c  P2_R4_E10_20260920T225954Z/src/e10_extract.py
d3e28226777cccd6565dce9473b8354d6608ad022e990a936f0b9a0e0dfa0aa0  P2_R4_E10_20260920T225954Z/src/e10_seal.py
53229ac1574d2168599af2441ad6bc106a74d30ffe88bc25b4bbc608bbd0bce7  P2_R8_E18_20260922T003446Z/src/e18_cert.py
2fc0991c2973a40031ea9c25e28906766c38f12e10c11c0d1d90c3a68ea6806a  P2_R8_E18_20260922T003446Z/GATE.md
17b3df3c38eb8c912e7d1dc21a6967eac38d1c486b1b5137888d439cf2f1e81a  P2_R8_E18_20260922T003446Z/gate/G1_G3.json
d90fdc581d4795220c4acf464c713ac749fbb3a7af743ad3696d27100e575934  P2_R8_E18_20260922T003446Z/gate/G3_divergence.json
fdbdca1badc919e95404cb2afd65f2abdb70c8378ae5f489bcf0aa60e2f86dc0  P2_R8_E18_20260922T003446Z/gate/G6.json
```
