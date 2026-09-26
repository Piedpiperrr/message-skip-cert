General. Paper conventions unchanged: parser V2; two unparseable answers = agreement, exactly one = change;
alpha=.05; delta=.001 per candidate; 20-candidate fit-quantile grid and the frozen selection rule (deploy the
largest accepted q); CP = two-sided 95% Clopper-Pearson; exact binomial p for H0 rho >= .05. All analyses descriptive
unless stated; nothing here changes a deployed policy.

E17-1 "Omit iff u = 0" baseline. Rows: the 9 certified Qwen policies (large OBQA Text [nominal], large OBQA C2C
 [nominal], large ARC Text, large ARC C2C, large MMLU-Pro Text, large MMLU-Pro C2C, medium OBQA C2C q=.55 [plus a q=.50
 row], medium ARC C2C, Text+fact q=.75) and the 2 Llama policies (n0 = 0; print "n/a" for rates). Report: cal
 n0 = #{u == 0}, k0, k0/n0 [CP], p; dev n0/N (coverage), k0/n0 [CP]; next to the certified policy's dev coverage and
 changed/omitted [CP]. Also list, per setting, which grid q have tau = 0 on fit and whether each was accepted in the
 original certification (where tau = 0 was a grid candidate, the u = 0 rule was already tested; otherwise its p is
 descriptive only). Writing: appendix table; Sec 7 one clause giving the dev coverage range and change-rate range of
 the u = 0 rule next to the certified policies'.

E17-2 Certification on u > 0 questions only. For each certified Qwen setting (8 settings + Text+fact): restrict fit,
 cal, dev to {u > 0}; candidates = the 20 grid quantiles of u over fit questions with u > 0; test on cal questions with
 u > 0; same alpha, delta, Bonferroni and selection rule. Report: deployed q+ or fallback, cal n/k/p at q+, dev
 coverage within {u > 0} and as a share of all dev, dev changed/omitted [CP]. Writing: if at least one setting
 certifies -> appendix + Sec 7 clause "on questions with u > 0 alone, the test still certifies X of 9 settings";
 if none -> Sec 7 clause "on questions with u > 0 alone no setting certifies; these certificates rest on the u = 0
 questions", next to the Llama-3.1 fact that a receiver with no u = 0 questions is still certified.

E17-3 ARC split comparison (official train -> fit and cal; validation -> dev; test -> sealed test).
 Settings (10): small T, small C, medium T, medium C, large T, large C, X1 Text, X1 C2C (Llama-3.2-1B -> Qwen3-0.6B),
 X2 OLMo Text, X3 Llama-3.1-8B Text. Test = the sealed test outputs of large T and large C only (other pairs' test
 outputs are produced separately in E16 and are not part of E17). Per setting x split (fit, cal, dev, test where it
 exists): N, disagreement d = #(o_R != o_b)/N [CP], R INVALID, reference INVALID, median u, share u == 0.
 Descriptive tests per setting: Fisher exact two-sided for cal vs dev, fit vs cal (a same-split control), and
 fit+cal vs test where available; number of settings with d_cal < d_dev; Mantel-Haenszel common OR for cal vs dev.
 Decision test (one contrast, cal vs dev): for each ARC question in cal or dev, x_i = mean disagreement indicator over
 the 10 settings; statistic = mean(x | dev) - mean(x | cal); two-sided permutation p from 10,000 permutations of the
 split labels (seed 0). Same for fit vs cal as a control.
 Also, for the 4 certified ARC policies (large T, large C, medium C, Llama-8B T): change rate at the frozen tau on
 cal, dev, and test (large only) [CP].
 Definition: SYSTEMATIC = permutation p < .05 with mean(x | cal) < mean(x | dev).
 Writing: SYSTEMATIC -> Sec 7 sentence stating the direction, the statistic and p, the count of settings with
 d_cal < d_dev, that the certificates assume exchangeable splits, and the sealed test (official test split) change
 rates; not SYSTEMATIC -> appendix sentence with the same numbers. If mean(x | cal) > mean(x | dev) with p < .05,
 report it the same way (Sec 7), since it also breaks exchangeability.

E17-4 Audit of the 44 sealed-ARC label differences between parser V2 and the official C2C extraction (E14-1).
 For each: id, which side (R or C2C) differs, raw output, V2 label, official label, option texts. Mechanical checks on
 the raw output: (i) after leading whitespace it starts with exactly one option letter A-D followed by '.', ')' or ':';
 (ii) the text after that letter equals that option's text after whitespace/case normalization, or starts with it;
 (iii) no second option-letter pattern ('A.' 'B)' etc.) appears; (v) the V2 label equals the letter found by (i);
 (iv) what the official extractor returned and why (unparseable, or a different letter).
 Report counts meeting (i), (i)+(ii), (i)+(ii)+(iii)+(v); list every row failing any check. Write the full table to
 E17_4_audit.csv (for the supplementary).
 E17-4b Official extraction for the Text certificates: k/n [CP] under the official extraction for the held-out
 large OBQA Text and Text+fact policies (E9b populations; A-D items only), next to the V2 numbers; the sealed ARC Text
 figure from E14-1 (20/1097) is restated.
 Writing: if all 44 pass (i)+(ii)+(iii)+(v) -> App I and one clause in Sec 4.5 ("in all 44, the output names one option
 letter followed by that option's own text; the official extractor rejects it"). If any row is one where the official
 label matches the output's stated option better than V2 does -> list it in App I and state in Sec 4.5 that the sealed
 C2C result depends on these rows. E17-4b goes into App I; any Text policy whose official-extraction CP upper >= 5% is
 named in Sec 4.5.

E17-5 Feasibility and a binormal model of the boundary.
 (a) Population feasibility (Uddin, Khider & Bauer, arXiv:2603.14623): for each of the 28 settings, pi = 1 - cal
     disagreement, C = (1 - pi)(1 - alpha)/(pi alpha); for each of the 20 candidates with n > 0, empirical TPR = share
     of agreeing cal questions omitted, FPR = share of disagreeing cal questions omitted (FPR = 0 -> ratio "inf");
     report max TPR/FPR, C, and whether max >= C (equivalently some candidate has k/n <= .05). The 2 E16-5 settings
     are not part of E17; they are added later from E16 outputs with the same code.
 (b) Binormal model: agreeing questions' score ~ N(0,1), disagreeing ~ N(mu,1), mu = sqrt(2) * Phi^-1(AUROC) (higher
     score = more likely to disagree), disagreement prevalence = cal disagreement rate. For each setting simulate the
     frozen procedure with its own N_fit and N_cal (for MMLU-Pro, N_cal = the n of the certificate's q = 1 test):
     draw fit scores, take the 20 grid quantiles as thresholds, draw a calibration sample, run the 20 exact binomial
     tests, apply the selection rule. 2,000 simulations, seed 0. Main run uses the dev AUROC; sensitivity run uses the
     cal AUROC. Report P(certify), modal deployed q, and median coverage when certified (coverage = population share
     of questions below the selected tau); prediction = certify iff P(certify) >= .5; count agreement with the observed
     outcome (x/28) and list every disagreement with its P(certify), prevalence, AUROC, N_cal, and share of u == 0.
     Also report, for each setting's (prevalence, N_fit, N_cal), the AUROC at which P(certify) = .5 (bisection over
     AUROC, 1,000 simulations per step), and the range of these values across the 28 settings (does .80 fall in it?).
 (c) Grid for a figure: prevalence in {.02,.03,.05,.075,.10,.15,.20,.30,.40,.50,.60} x AUROC in {.60,.65,...,.95,.98}
     for (N_fit, N_cal) = (670, 448), (2100, 1366), (3000, 6000); 1,000 simulations per cell, seed 0; CSV of
     P(certify) and the P = .5 contour.
 Writing: agreement >= 24/28 -> Sec 5: "a binormal score with each setting's disagreement rate and AUROC reproduces X
 of 28 outcomes; the boundary is what the test implies given these two numbers, and the empirical content is where each
 path falls" + name the exceptions; < 24/28 -> "disagreement rate and AUROC alone reproduce X of 28 outcomes; the rest
 depends on the shape of the score distribution" + name them. Either way (a) is summarized in Sec 6 and (c) goes to
 an appendix figure.

E17-6 MMLU-Pro per category (large Text and large C2C only). For each of the 14 categories: category-specific fit
 quantiles (same grid), category calibration questions, same alpha/delta/Bonferroni/selection rule. Report per
 category: N_cal, cal disagreement, deployed q or fallback, dev coverage and changed/omitted [CP]; number of
 categories certified per path; also the count if delta is further divided by 14. Writing: App K one sentence with
 both counts; nothing in the main text.
