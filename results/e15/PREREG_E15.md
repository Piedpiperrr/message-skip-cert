E15 preregistration. Written before any E15 computation. Nothing below changes after seeing numbers. If an item
cannot be computed exactly as written, the agent stops before computing it and reports options.

E15-1 Predicting certification from the fit split alone.
- Scope: the 25 settings with fit-split reference outputs (8 deploy, 17 fall back). The prediction uses the fit
  split's receiver and reference outputs and ProbeMax scores (shadow runs, no gold labels) and no calibration data.
- Plug-in rule, fixed now, with no fitted parameter (so leave-one-setting-out is unnecessary): for candidate j with
  frozen fit threshold tau_j, m_j = number of fit questions with u <= tau_j (m = N_fit for q = 1) and d_j = the
  number of those with o_R != o_b. Rescale to the calibration size with rounding half up:
  n_hat_j = round(N_cal * m_j / N_fit); k_hat_j = round(n_hat_j * d_j / m_j) (0 if m_j = 0).
  Predicted acceptance: Pr[Bin(n_hat_j, .05) <= k_hat_j] <= .001 (n_hat_j = 0 gives p = 1). Predicted q_hat =
  largest predicted-accepted q, else predicted fallback. Predicted coverage = m_j / N_fit at q_hat.
- Saving model for the eight replayed policies, labelled "fit-predicted coverage times measured development latency
  gap": kappa_hat * (mean c_b - mean c_R) - mean c_s, with c_b and c_R the development component latencies of the
  reference and of R, and c_s the component probe cost, all from the component accounting records (not from the
  replay being predicted). The gap is unconditional (not Eq. 4's gap conditional on omission). If a policy is
  predicted to fall back, its predicted saving is 0. Also report the same formula with the actual panel coverage,
  to separate coverage error from latency-model error.
- Report per setting: actual outcome and q; predicted outcome and q_hat; for settings where both deploy, the
  difference in grid steps and |actual dev coverage - predicted coverage|; for the eight policies, predicted
  saving (both versions) vs measured Table 2 saving. Summaries: agreement separately for the 8 deployed settings
  (x/8 predicted to deploy) and the 17 fallback settings (y/17 predicted to fall back); median and max |q_hat - q|
  in grid steps and median coverage error over settings where both deploy; median |predicted - measured| saving
  in ms and median of |predicted - measured| / |measured| over the eight policies.
- Paper rule: an appendix table with every row, and one main-text sentence (Sec. 5) that names "the 25 settings
  with fit-split reference outputs", says the prediction uses shadow reference outputs but no labels, and gives
  x/8, y/17, the median grid-step error, the median coverage error and the median saving error. The sentence says
  the fit split "predicts" the boundary only if x >= 7, y >= 15 and the median |q_hat - q| <= 1 grid step;
  otherwise it gives the same numbers and says the fit split "does not reliably predict" the boundary.

E15-2 Busy GPU time saved.
- Definition: per query, the sum over both GPUs of the wall time of GPU-side stages (probe prefill; helper
  generation or helper prefill; C2C fuser projection; receiver prefill and decoding), excluding tokenization,
  parsing, routing and transfers.
- A source qualifies for a policy only if every listed stage that the policy or its fixed reference runs is timed
  separately, per request, with CUDA synchronization. Source preference, applied per the whole set of eight:
  use the single highest-preference source that qualifies for all eight: (a) original-configuration replays;
  (b) second-configuration replays (E3 repeats or E7). Component accounting records are not a replay and are
  reported only descriptively, compared against the component-recomposed saving.
- For a qualifying replay source, per policy: mean busy-time saving (fixed - policy) and the paired difference
  D = busy-time saving - latency saving of the same replay, each with a paired bootstrap 95% interval over the same
  questions (seed 0, 2,000). The ratio busy/latency saving is reported only for policies whose latency saving
  interval lies above zero.
- Paper rule:
  (1) A replay source qualifies for all eight: an appendix table; in Sec. 7, "We measure latency, not the helper
      compute omission also saves," is replaced by a clause giving the range of busy-time savings for Text and for
      C2C policies. If D's interval lies above zero for any C2C policy, Sec. 4.4 states that under busy GPU time
      C2C omission saves more, with the numbers; if D's interval lies below zero for any policy, Sec. 4.4 states
      that it saves less, with the numbers; otherwise Sec. 4.4 is unchanged. In every case the Sec. 7 clause
      "and the same-target baselines have component estimates only" is kept.
  (2) No replay source qualifies for all eight: the appendix reports what is available; in Sec. 7 the phrase is
      replaced by "busy GPU time is available for X of eight policies (Appendix)", keeping the baselines clause.
- Nothing else in the paper changes because of E15.
