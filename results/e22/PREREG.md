E22-PREREG v1 (Paper A, round 10). Post hoc analyses of stored development outputs. Reported whatever the result.
Exposure: development gold labels have been read before. The authors know the unstratified per-reference ratios, the
stratified-joint medians (.849 gain over R, .967 best fixed), the large-pair OBQA change directions (Text 46 wrong->right
and 18 right->wrong; C2C 16 and 35; V1 48 and 66), and a reviewer's rough approximation that stratification moves the
large-pair OBQA ratios to about .79 (Text) and 1.06 (C2C). No stratified per-reference ratio has been computed.
Populations: the seven development populations of the null analysis (small, medium, large pair on OBQA and ARC; large pair
on MMLU-Pro). References: Text and C2C, each separately (14 reference-population cells).

E22-1 Per-reference stratified null (primary).
 Strata: S+ = questions with o_R = gold; S- = questions with o_R != gold (INVALID counts as wrong).
 For reference b and stratum s: n_s(b) = #{x in s: o_b(x) != o_R(x)} (two INVALIDs agree; exactly one INVALID = change).
 P(x) exactly as in E9a: the SET of answers of V1 (mapped back) and V2 at x that differ from o_R(x) (V1 = V2 counts once;
 INVALID included or excluded exactly as E9a does; record which in REPRO.md).
 In each stratum, draw min(n_s(b), elig_s) questions uniformly without replacement among stratum-s questions with
 nonempty P(x) (elig_s = their number), and give each a uniform draw from P(x); elsewhere the null keeps o_R. Pool the two
 strata into one null action.
 Gain over R: real = #correct(oracle over {R, b}) - #correct(R); null = the same with the null in place of b.
 Ratio = mean null gain over 1,000 draws / real gain.
 Only draws on S- affect the gain over R, so under-matching on S+ does not affect it. Check: the mean null gain equals
 min(n_-, elig_-) * g_-, where g_- = mean over eligible S- questions of |P(x) intersect {gold}| / |P(x)|, within 3 Monte
 Carlo standard errors; otherwise STOP E22-1 and report.
 Under-matching on S- (elig_- < n_-(b)) makes the ratio a lower bound: such a cell is "undetermined", is excluded from
 M, K, T_sig and C_sig below, and is named wherever those counts are reported; the appendix also reports
 ratio * n_-(b) / elig_-.
 The best-fixed headroom ratio is not computed for this design (with S+ fully matched it is at most 1 by construction
 for a reference more accurate than R).
 Intervals: E9a's procedure (2,000 bootstrap resamples of questions, 100 null draws each, percentile 95%). In each
 resample, questions are resampled without regard to stratum, copies are distinct units, and S+/S-, n_s(b), elig_s and
 the real gain are recomputed; resamples with a real gain of 0 are handled as in E9a, and their count per cell is
 reported. For medians over populations, each population is resampled separately. Seed: E9a's seed if stored, else 0
 (record which).
 Report per cell: n_+(b), n_-(b), elig_+, elig_-, undetermined flag, real gain, mean null gain, g_-, stratified ratio [95%];
 next to it the stored unstratified E9a ratio [95%] from tab:null_matched. Medians with intervals: Text over the seven
 populations; C2C over the seven populations; C2C over the five medium/large cells.
 Summary quantities (gain over R; the unstratified values are the stored E9a ratios and intervals printed in
 tab:null_matched; the rerun in REPRO 0a is only a check), each reported as "x of the d determined cells":
  M = # populations where Text's ratio < 1 under BOTH the unstratified and the stratified per-reference design;
  K = # populations where Text's 95% upper end < 1 under BOTH designs;
  T_sig = # populations where Text's stratified upper end < 1;
  C_sig = # of the five medium/large C2C cells whose upper end < 1 under EITHER design;
  ranges of the stratified ratios for Text (7) and for the five medium/large C2C cells.

E22-2 Direction of changes (descriptive, no randomness).
 For each population and each A in {Text, C2C, V1, V2}: changes on S- (o_A != o_R, o_R wrong), split into wrong->right
 (o_A = gold) and wrong->wrong, with a two-sided 95% Clopper-Pearson interval on the wrong->right share; changes on S+
 (right->wrong); and the number of S- and S+ changes whose answer is INVALID. For the null: g_- (defined in E22-1),
 printed next to each reference's wrong->right share. Must reproduce E5 / the paper for large OBQA (Text 46/18, C2C 16/35,
 V1 48/66); else STOP E22-2 and report.

Writing rules (content constraints for the paper; the authors choose the wording):
 (R1) Always: an appendix table with every E22-1 cell (both designs side by side, undetermined cells flagged), an
      appendix table of E22-2; Sec. 4.1 gives, in one sentence, the stratified ranges for Text and for the five
      medium/large C2C paths with T_sig and C_sig (as "x of the d determined"); the main-text table that carries the
      per-path ratios (currently Table 1) shows both designs in every cell, with both medians.
 (R2) Scope: every sentence outside the E22 appendix tables that compares one path with the per-reference null. This
      covers the abstract; Contribution 1's title and text; the Sec. 4.1 heading and paragraph; Sec. 4.3 "on exactly the
      paths whose complementarity the null matches"; Sec. 6 "A certified path may add nothing beyond answer volatility";
      the conclusion; and Table 1's Text and C2C columns. Each such sentence must hold under both designs, and any quoted
      range spans both.
      - Text: "exceeds the null" is allowed only for the M populations and "significantly" only for K. If M < 7, the
        sentence names the other populations with their ratios.
      - C2C: "at the null's level" or "nothing beyond answer volatility" is allowed only for cells whose upper end is at
        least 1 under both designs; excluded paths are named. "Matches or exceeds" or "reach" is allowed only if all five
        point ratios are at least 1 under both designs; otherwise use "are not significantly below". "Intervals above 1"
        is allowed only for cells whose lower end is above 1 under both designs.
      - Small-pair C2C is given under both designs wherever it is given.
      - The abstract keeps one sentence on the per-path null in every branch.
 (R3) "The null separates the paths" (and the Sec. 4.1 heading, and "these are the C2C paths that omission certifies as
      redundant") stays only if K >= 4 and C_sig = 0. If K >= 4 and C_sig is 1 or 2, write "separates Text from
      (5 - C_sig) of the five certified C2C paths" and name the others. Otherwise the abstract, Contribution 1 (title
      included), the Sec. 4.1 heading and the conclusion state that whether the null separates Text from C2C depends on
      how it is matched, giving K, C_sig and both ranges.
 (R4) E22-2 may be cited in the main text only as ranges over all seven populations for each of Text, C2C, V1, V2 and the
      null (no selected population or arm).
 (R5) For each item, outputs not all written by 2026-09-23 18:00 CDT (judged by the manifest's last output timestamp,
      recorded before any statistic is read) -> no number from that item in the paper; the provenance table gets
      "<item>: not completed (<reason>)". Late outputs are still analysed under this PREREG and go into the supplementary
      material.
 (R6) Any choice made after an E22 statistic exists (including answers to NEEDS FROM US) goes to DEVIATIONS.md with its
      UTC time and is disclosed in the appendix.
END E22-PREREG
