X4 preregistration. Written before any X4 model output. Nothing below changes after seeing outputs.
Design: large pair (Qwen2.5-7B-Instruct helper, Qwen3-8B receiver), Text reference, OBQA and ARC-Challenge with the
paper's fit/cal/dev splits and question IDs. The helper's stored greedy Text messages are reused unchanged
(hash-checked). The receiver's answers on both paths (receiver alone, path "R"; receiver after the Text message,
path "Text") are sampled with the Qwen3 model card's non-thinking settings, passed explicitly so that no
generation_config default applies: do_sample=True, temperature 0.7, top_p 0.8, top_k 20, min_p 0,
repetition_penalty 1.0; thinking disabled; at most 64 new tokens; bf16; batch 1. One sample per question and path.
Seed = int(sha256(("X4|" + question_id + "|" + path).encode("utf-8")).hexdigest()[:8], 16), applied with
torch.manual_seed and torch.cuda.manual_seed_all immediately before each generation; the two paths therefore use
independent draws. Everything else is unchanged: prompts and chat template, parser V2, INVALID convention (two
INVALID labels agree), the stored ProbeMax scores and frozen fit thresholds, 20 candidates, alpha = .05, per-test
delta = .001, Bonferroni within each setting; the two settings (40 tests) form their own family. Both settings are
reported whatever the outcome. No other temperature, sampling setting, model, benchmark or reference will be tried
after seeing X4 outputs. No latency replay (the question is safety, not value).
Status note fixed now: the OBQA calibration questions and greedy labels were used when ProbeMax was chosen, so an
OBQA certification in X4 is nominal, like the paper's large/OBQA development certificates; ARC is not affected.
Paper rules (Sec. 7 target sentence: "The test stays valid for sampled outputs, but sampling adds disagreement";
the rest of that sentence, on thinking, is kept):
(1) At least one setting deploys: the target sentence is replaced by one stating, for each benchmark, whether
    omission is certified with sampled receiver answers (temperature .7), with q, dev coverage and dev change rate
    [CI] for a deploying benchmark (marked nominal if it is OBQA) and the added disagreement from sampling [CI];
    if re-split agreement is below .80 for a deploying benchmark, it is called split-sensitive. An appendix
    section gives all numbers.
(2) Both settings fall back: the target sentence is replaced by one stating that with sampled receiver answers no
    threshold is certified, and the added disagreement from sampling [CI]; an appendix section gives all numbers.
(3) The smoke check fails on INVALID: the appendix reports the failed preregistered check; Sec. 7 is unchanged.
(4) X4 is not run or not completed by Tue Sep 22 18:00 CDT for any other reason (mismatch in smoke (a)/(b), runtime
    error, queue): Sec. 7 is unchanged and the paper does not mention X4.
