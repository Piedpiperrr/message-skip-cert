# PREREG_E20F.md — E20-full (Paper A)

Stage P2_R8_E20F_20260922T003652Z. Written 2026-09-22T03:09:28.440909+00:00, before any E20-full output and before job 1. The block between
the markers is verbatim from the task; everything after it is resolved detail.

----- BEGIN PREREG BLOCK -----
E20-full. Setting (frozen by the pilot's selection): SQuAD v1.1 train pool (passages <= 300 words, deduplicated, SHA order), helper
Qwen2.5-7B-Instruct at the pilot's revision writing the Text message (max 256 tokens), receiver Llama-3.1-8B-Instruct @ 0e9e39f2 (default
chat template, no system prompt, one BOS), prompts exactly as PROMPTS_E20.md, greedy bf16 batch 1, receiver max 32 new tokens, the pilot's
frozen extraction and SQuAD normalization (INVALID = empty; two INVALIDs agree), change = 1[normalized o_R != normalized o_b], score s2
exactly as the pilot code computes it. The system's output is the normalized answer; the certificate covers changes of it only.
Splits (frozen by the pilot): fit 500, calibration 2,000, dev 1,000, the next items after the 400 pilot ids in the frozen SHA order.
Extensions added here, before any E20-full output: (E1) fit questions also get helper messages and receiver-with-message outputs, used
only for re-splits and descriptive fit statistics; certification reads only fit s2. (E2) a test split of the next 1,000 questions.
Certification: the paper's function, unchanged: tau_q is its q-quantile of the 500 fit s2 values for q in {.05, ..., .95}; q = 1 is the
fixed-receiver endpoint (omit every question), as in the paper; omit iff s2 <= tau; p = P[Bin(n, .05) <= k], with p = 1 when n = 0; accept
if p <= .001; deploy the largest accepted q, otherwise fallback. One family of 20 tests.
Order: job 1 produces fit and calibration outputs; CERT_E20F.json is computed from them and hashed BEFORE any dev or test output exists.
Job 2 then produces dev outputs, and test outputs only if a threshold was deployed. Dev and test statistics are computed and hashed
(STATS_E20F.json, ROUTES_E20F.json) before gold answers are read, which happens only for accuracy.
Report regardless of outcome:
- calibration: the 20 candidates (q, tau, n, k, p, accepted, .999 Clopper-Pearson upper bound); deployed q or fallback; disagreement
  k/2,000; INVALID for R and reference; always-omit change rate; max empirical TPR/FPR against C(pi, alpha); if fallback, the calibration
  size the paper's rule says would be needed;
- dev: disagreement rate d [two-sided 95% CP]; AUROC of s2 for disagreement (ties 1/2) with bootstrap 95% interval (seed 0, 2,000);
  coverage; change rate among omitted questions [CP]; the split of those changes into both-parse / only-R-INVALID / only-reference-INVALID;
  INVALID for R and reference; the E17-5 binormal P(certify) from dev (d, AUROC) at N_cal 2,000 and the dev AUROC against .80;
- surface form (descriptive, never certified): among omitted dev questions, the change rate on raw extracted strings before
  normalization, and with "one normalized answer contains the other" counted as agreement; the share of changes with containment; the
  median token-F1 between the two answers among changes; the share of outputs where extraction did more than normalization;
- lengths: median answer words and 32-token cap hits for R and reference; helper message tokens (median; share at the 256 cap);
- test (only if deployed): omitted n, changed k, change rate [CP], exact binomial p of the single test at the frozen threshold, coverage.
  Pass rule: two-sided 95% CP upper bound below 5% = pass; CP lower bound above 5% = fail; otherwise inconclusive; also state whether
  p <= .001;
- accuracy (exact match against any gold answer after the same normalization) of R, Text and the policy on dev and test, as x/1000 with
  paired bootstrap 95% intervals (seed 0, 2,000); G = acc(Text) - acc(R) with interval; kappa*alpha (dev coverage times 5 points) against
  G; among changes, how many the reference corrects and breaks;
- 200 re-splits of fit + calibration (seeds 1 to 200, same sizes; dev and test fixed): share with the original outcome, median deployed q,
  median dev coverage (descriptive);
- the pilot's binormal prediction (P = .975 at N_cal 2,000; conservative .081) next to the outcome, as a prospective test;
- value estimate (only if deployed; not a replay): per dev question, 1[omit] * (helper + receiver-with-message time) - receiver-only
  time, since s2 needs the receiver-only answer, which is served when omitted and wasted when routed; mean with paired bootstrap interval;
  also the always-omit estimate and the component means, with the pilot code's wall-clock definition. Sequential execution is assumed,
  which is conservative against running the helper in parallel; the times come from ClusterA, not from the paper's main replay hardware.
Writing rules (Paper A). The pilot PREREG's rules, restated, with the title rule and the test condition narrowed here, before any
E20-full output (narrowing recorded in DEVIATIONS.md and in the paper's order of events):
(1) Certified with dev coverage >= 10%, dev change-rate CP lower bound <= 5%, and the held-out test passing: the abstract says
    certification extends to extractive short-answer question answering (SQuAD, Llama-3.1-8B receiver), the one of eight pilot settings
    the label-free rule selected; the title becomes exactly "Safe to Omit, Worth Omitting? Risk and Cost Boundaries of Skipping
    Communication Between Two LLM Agents on Multiple-Choice and Extractive Questions"; the main text reports d, AUROC, q, coverage, change
    rate [CI], G with kappa*alpha against G, the both-parse vs exactly-one-INVALID split, and the test result.
(1a) As (1) but the test is inconclusive: the main text reports the certificate and the inconclusive test; the abstract may state the
    certificate with "held-out test inconclusive"; the title is exactly "Safe to Omit, Worth Omitting? Risk and Cost Boundaries of Skipping
    Communication Between Two LLM Agents on Multiple Choice".
(1b) As (1) but the test fails: the main text says it fails its held-out test next to the certificate; abstract unchanged; title
    "... on Multiple Choice" as in (1a).
(2) Certified with dev coverage < 10%, or with dev CP lower bound > 5%: reported as such in Sec. 4 and the appendix; abstract unchanged;
    title "... on Multiple Choice".
(3) Fallback: Sec. 7 reports it in one sentence with d and AUROC; title "... on Multiple Choice"; no test is scored.
(4) Always (pilot PREREG, verbatim in substance): the full-run setting joins the certification-outcome count and is reported as a
    prospective test of the binormal prediction; the pilot settings are not certification outcomes; an appendix reports every pilot
    setting, the selection rule and the order of events; the provenance table gets a row (later extension, run after the GSM8K fallback,
    label-free pilot on disjoint questions, rule hashed before selection); the main text notes that the selected setting's predicted P is
    inflated by choosing the best of eight and that the four Qwen3-receiver settings were not eligible.
(5) Redundancy: if G's interval includes 0 or G <= kappa*alpha, the main text says the certificate finds the helper's message redundant
    on SQuAD, so an operator with labels could retire it.
(6) Value is reported only as an estimate from recorded per-row times.
(7) Deadline: the run is complete when fit/calibration/dev outputs, CERT and the dev statistics exist. If that is not the case by Sep 23
    06:00 CDT, the paper reports the pilot only, states that the full run was not completed, and the title is "... on Multiple Choice". A
    late test does not make the run incomplete; it is reported only if finished before the paper is frozen.
Precedence: these rules decide the title. The E18 PREREG's clause that the title keeps "on Multiple Choice" means only that E18 alone never
changes it.
----- END PREREG BLOCK -----

## Resolved hashes

- Pilot: PREREG_E20P.md `c02cf958a7c972c6c976da4100d02293fcd81ba91b5f614d02b3cf0a1ab7adb5`; SELECTION_E20P.json `4fdee068d98de22cf2cf463b65668ac992049405b94de4b4e9ab463c5b6cad33`; PROMPTS_E20.md `6ed439e8c320c9c9bb62bb3fad969564219168976f134db7e3199db674c6814e`;
  notes/CODE_FREEZE.json `5dc333c88cc55741a9d6323fcab4b2147525c1f13a8b878a7905e64f42cdf895` (27 files, all verified: notes/G1_VERIFY.json; re-checked by every GPU rank).
- Helper Qwen/Qwen2.5-7B-Instruct @ a09a35458c702b33eeacc393d103063234e8bc28; receiver meta-llama/Llama-3.1-8B-Instruct @ 0e9e39f249a16976918f6564b8830bc894c89659.
- SQuAD rajpurkar/squad @ 7b6d24c440a36b6815f21b70d25016731768db1f; pool 86,830; POOL_ORDER_squad.txt `9754449546d370e2ab7c690ee99f44a50c240230850574f195f596664ffab7f3` (= pilot).
- Splits (id, question, passage only): fit 500 `a3ac3e0cff3a78c973de46e5701fc7e3e9e68efa4ea66f5613623edd8d32ae57`; cal 2000 `bf25118bbaae4da88cc651a71c994a7a0cea0684adaee3553cf5836cf5886553`; dev 1000 `13a98e661a2011c3cb7e0a765929a9ba41da9ea09146213d4c3e71f89d73c3a4`; test 1000 `1ba0a728f908f4dd42ed79285e3af35572020e6f4f51a3ac0c095f988b6f119e`.
- Certification functions: common_r1.py / data_r1.py / analyze_x3.py ledger_rows (hashes in notes/G4_CERT_REPRO.json), wrapper src/e20f_cert.py `3d713d9163ed746f29724fd1a70289913bfe48a3fb27021b8fc18c581f12a702`;
  X3 OBQA reproduction q = .60, 21/800, p = 5.735e-4 (PASS). Frozen E17-5 binormal code e17_5.py `ef1537c7289b30d7a0adfe5b9180fc9a53a35bf6cb6aba1021ebf6759dde2b6b`.
- DEVIATIONS.md at PREREG time `8990ec2f2c9e92939ce1948dbfeb9b6028100495f8c1cf6bc54a1e6c9ed9da51`. GATE.md `d4d5fce7cb60f09bcb91b876336843a19ec44ff5b6706b73616d1273e2fbcd0c`; CODE_DIFF.patch `c8fa57cc1c9fc788e03fcd3f955df05fe9d51853962cf6084efedec5f88f1430`; notes/CODE_FREEZE_E20F.json `33b1d53b535e00394fa16b9d8f9c44c41c0268f87fea9a0a5eda7c19de9c6000` (29 files,
  checked by every GPU rank at start-up).

## Full-run scripts and job scripts

| file | sha256 |
|---|---|
| src/e20f_cert.py | `3d713d9163ed746f29724fd1a70289913bfe48a3fb27021b8fc18c581f12a702` |
| src/e20f_cert_run.py | `4c56ffb036990cbb336199a3e1bfe29ae3f9a257f661e02b7aca3ee2a9e58f45` |
| src/e20f_common.py | `1290e781443dd96a0adcb2ce2d846805d817ddb069f1b921000f199cf7b1db70` |
| src/e20f_exec.py | `d40ec2538ad5fe566b053d52f27a1c9958989450199e7a4df4830d49ba86097e` |
| src/e20f_g1_verify.py | `02c5624f89610e217f58af5812937af3dea9c6ee0bdb829c34e79285afc53759` |
| src/e20f_gold.py | `c3fb0ee1f88fa5b375bcc07b60f43555c4461978b2fef62efd56a203414d4d55` |
| src/e20f_merge.py | `0712c70508ebec27a39c6ecfc363e92cc9e886c79c0ee789e495f32afebb99ff` |
| src/e20f_results.py | `d22e9c46075f786d53de71eaeeb4c5a3590eadda22edf10e4b96b3117f6eb341` |
| src/e20f_splits.py | `3b8bc926452ca9988f4cb172f277a955e03ca5717185b67762688f52408d553b` |
| src/e20f_stats.py | `19fecce231ce4899bc1e36818ec4dbfeea9caa93a7191d8eb4e34ec1a06cd74a` |
| jobs/e20f_devtest.pbs | `eec7305c8bffc1411ad5711c80b1cd5246df47add33fc0142f73d872abacb217` |
| jobs/e20f_fitcal.pbs | `1a4e9ddf7713874ce475d2804cefd0911e2dc2b3d2636d8525d0f1d335d7544c` |
| jobs/e20f_slot.sh | `138aaf2a1e7e28a1723342e7732ec574c4b32b6ce18deb3a454a01dc28fe995d` |
| pool/src/e20_extract.py | `d9c30fa611218ff2decdf498349f3a1eefbdaada89dbed171b1d40fed9342be0` |
| pool/src/e20_pool.py | `53413dc7ec8dab1a53b1cae9b043347d8f4086263ef437891f8f00ca3a60bee7` |

## Implementation choices where the block leaves a detail open (fixed in the hashed code before any output)

1. Preflight (every job, rank 0): the first 16 pilot SQuAD questions (PILOT_squad.jsonl) through src/e20f_exec.py; PASS iff for all 16 the helper
   token IDs, receiver-only and receiver-with-message token IDs, and s1/s2/s3 of both paths equal the pilot rows (results/E20P_jobA_rows.jsonl).
2. Continuation: rank 0 writes PLAN_j<PBS job number>.json; every question of the phase without an error-free receiver row is assigned
   round-robin; a question counts once (first error-free row). Certification and statistics require every question of their splits.
3. CERT: src/e20f_cert_run.py; always-omit change rate = the q = 1 row; TPR/FPR vs C as in E17-5(a) over the 20 candidates; needed N_cal
   (fallback only) = the E5-b needed_m rule (verbatim from analyze_e16_5.py).
4. Stats: src/e20f_stats.py docstring (AUROC = explicit Mann-Whitney ties 1/2; bootstrap default_rng(0), 2,000, percentile; binormal with
   the pilot settings N_fit 500, 1,000 simulations, seed 0; surface / length / test / re-split / value definitions). A test that is not
   complete is reported as incomplete (rule 7).
5. Gold: src/e20f_gold.py (SQuAD answers.text; paired bootstrap default_rng(0), 2,000; corrections / breakages among all changes and among
   omitted changes); RESULTS_E20F.md and the writing-rule branch: src/e20f_results.py.
