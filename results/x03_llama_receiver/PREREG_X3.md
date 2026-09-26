X3 preregistration. Written before any X3 model output. Nothing below changes after seeing outputs.
Receiver: meta-llama/Llama-3.1-8B-Instruct at revision 0e9e39f249a16976918f6564b8830bc894c89659; selected by availability and label tokenization only
(first choice; this account had no HF access at the Step 0 check (403), requested access, and was granted it on Sep 21 before any X3 model output).
Design: identical to X2 except the receiver. Helper = the stored Qwen2.5-7B-Instruct Text messages of the large
pair (hash-checked, not regenerated). Benchmarks: OBQA and ARC-Challenge with the paper's fit/cal/dev splits and
question IDs. Reference: Text only (no C2C fuser exists for this receiver). Same user-message content as X2,
rendered with the receiver's own default chat template and no added system prompt. Greedy decoding, bf16,
batch 1, at most 64 new receiver tokens. Parser V2 unchanged; INVALID handled as in the paper (two INVALID
labels count as agreement). ProbeMax with the X2 answer prefix and label-token rule.
Certification: 20 fit-quantile candidates, exact binomial test on cal, alpha = .05, per-test delta = .001,
Bonferroni within each setting; the two settings (40 tests) form their own family. Both settings are reported
whatever the outcome. No other receiver, benchmark, reference path, score, threshold rule or parser will be
tried after seeing X3 outputs.
Paper rules:
(0) The preregistered smoke check fails on INVALID: no production run; the paper reports the failed smoke check
    (counts) in the cross-family appendix and in one clause of Sec. 4.3; no other receiver is tried.
(1) Both settings fall back: the paper reports nine cross-family settings, all falling back; Sec. 4.3 gives one
    sentence with the new receiver's dev disagreement, AUROC, INVALID rates, and whether the both-parse diagnostic
    certifies; the paper's scope statements stay as they are.
(2) At least one setting deploys: the paper states that certification extends to this non-Qwen receiver on that
    benchmark, with dev coverage, change rate [CI] and the re-split agreement rate; if re-split agreement is below
    .80 the result is called split-sensitive; the scope sentences say "these pairs" instead of naming only Qwen
    pairs; the replay classification is reported if the replay ran, otherwise the paper says latency was not
    measured for this pair.
(3) In every case the two X3 settings are added to the disagreement-vs-AUROC figure and to all setting counts, and
    the provenance table records X3 as a post hoc extension added in response to review, after X1/X2 fell back.
    The paper states that AUROC near .80 separated deployment from fallback in the earlier settings. An X3 setting
    conforms if it deploys with dev AUROC > .80 or falls back with dev AUROC < .80. Conforming settings are added to
    the count of settings evaluated after that pattern was written; a non-conforming setting is named in the text
    as an exception.
(4) Results not complete by Tue Sep 22 18:00 CDT (replay: 22:00 CDT) are not used in the paper; if the replay
    misses its cutoff, the paper says latency was not measured for this pair.
