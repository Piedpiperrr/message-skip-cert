E5-a (parser exposure). X = the calibration questions whose raw outputs were reviewed with gold labels during parser rule development
(the 355 of the A8 audit), reconstructed from the provenance records. Remove X from the calibration set of every setting of the same
benchmark. For all 21 settings (14 main + 7 cross-family) redo the 20 tests on C \ X with the frozen fit thresholds, alpha=.05,
per-candidate cutoff p<=.001. Primary check: is the originally deployed q still accepted on C \ X? Reporting: if every originally
deployed q is still accepted, the paper states that the guarantee holds on the exposure-free calibration subset and adds the clean
n/k/p; nothing else changes. If a deployed q is not accepted, that setting is reported as "not certified without the exposed
questions" (counts, figure, contributions, abstract updated; development coverage/change recomputed at the largest clean-accepted q or
fallback; original replay numbers kept and labeled as belonging to the original threshold). New passes in fallback settings are
reported descriptively and never deployed. If X was selected by output content rather than at random, this is stated and the
disagreement rates in X and C \ X are reported.
E5-b (re-split stability). For each benchmark, re-draw fit/calibration from fit U calibration with seeds 1..200 (original = seed 0),
same grouping, sizes, and shuffle rule; all settings of a benchmark share the same re-splits; development unchanged. Per setting:
certification rate, share of re-splits reproducing the original deploy/fallback outcome, median/IQR of deployed q, median development
coverage and change rate over deploying re-splits. An outcome recurring in >=80% of re-splits is "stable", otherwise
"split-sensitive". The medium-pair statement "only C2C can be omitted" is written as a property of the pair only if medium C2C is
stable-deploy on both OBQA and ARC and medium Text is stable-fallback on both; otherwise it is rewritten with the rates. Fallbacks are
always worded "not certified at alpha=.05 with n calibration questions".
E5-c (null control). Per population: absolute oracle counts and gain over R for {R,Text,C2C} and {R,V1,V2}; per action vs R: changed,
corrective (R wrong -> action correct), harmful (R correct -> action wrong), neutral. Rate-matched null as specified in task E5-c,
1,000 draws, seed 0. rho = mean matched-null gain over R / real gain over R. If rho >= 0.8 in >= 4 of 7 populations, contribution 1
keeps its claim with "rate-matched content-free perturbations reproduce most of the headroom (median rho)"; otherwise contribution 1
and the abstract are rewritten to "reproduce X% (median) of the headroom" and the "six of seven" statement is removed. In both cases
the main-text null comparison uses gain over R and absolute counts.
E5-e (cross-family INVALID). Disagreement decomposition and a valid-only diagnostic (not deployable). If an OLMo benchmark certifies on
valid-only questions, the paper states that its fallback is driven by answer format and withdraws the size statement for it;
otherwise the paper says "not accuracy or size alone" and reports the INVALID share.
