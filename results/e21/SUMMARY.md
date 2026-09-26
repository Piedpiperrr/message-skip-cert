# E21 SUMMARY (P2_R9_E21_20260922T065220Z)

Post hoc analyses of stored outputs (ClusterA login node, CPU only; no model forward pass). E21 creates no deployment and changes no count in the paper.

## Timeline and hashes

- Step 0 REPRO 2026-09-22T06:56:57Z - 2026-09-22T06:58:41Z ((a)-(g) 89/89 PASS; (h) search, see REPRO.md).
- PREREG.md sha256 `5c18a86e88210ddd3bda73d3226405212e3b77ef871c7296a0909ef797054185` written/hashed 2026-09-22T07:08:42Z (verbatim; the one "[frozen q]" replaced by [.40, tau = 3.838539123535156e-05], cited in INPUTS.md).
- First E21 statistic: 2026-09-22T07:11:48Z (start of scripts/e21_1_cert.py).
- CERT.json sha256 `96b5bc7092c77d3988c232a8a43c2545a8b6885b6690383b9e80d4e185a46445` hashed 2026-09-22T07:12:11Z; E21-1 evaluation 2026-09-22T07:13:37Z - 2026-09-22T07:15:12Z (verified CERT hash first).
- E21-2 2026-09-22T07:16:36Z - 2026-09-22T07:19:02Z; E21-3a 2026-09-22T07:21:12Z - 2026-09-22T07:22:26Z.
- Script hashes: SCRIPT_HASHES.md.

## E21-1 label-light certificate of the accuracy loss

**Writing rule branch: (a).** Quoted sentence with the numbers filled in (Sec. 4.3):

> With gold labels on at most 7-12 calibration questions (the lowest-uncertainty receiver-reference disagreements), the same test also certifies, at a threshold no higher than the deployed one, an accuracy loss of at most one point for 3 of the six helpful Text paths (2 of them nominal), at 45.0-62.0% development coverage, retaining 98.1-106.1% of the gain (App. X).

Deciding numbers: counted at eps = .01 = large/OBQA/Text, large/OBQA/Text+fact, Llama-3.1-8B/OBQA/Text (A = 3; B = 2 nominal: large/OBQA/Text and Text+fact); K = range of D_need over them = 7-12 (D_need [8, 7, 12]); dev coverage 62.0%, 53.6%, 45.0%; retention 100.0%, 98.1%, 106.1%; no counted setting has dev or out-of-sample k_L/N > eps (none). Abstract: at most one clause, authors' choice.

"Counted" per setting x eps (joint certificate, dev coverage >= 20%, eps <= G_dev/2):

- large/OBQA/Text eps=0.01: counted True (cov 0.6199 (>= .20: True); G_dev 3.774 pts (eps <= G/2: True))
- large/OBQA/Text eps=0.02: counted False (cov 0.7224 (>= .20: True); G_dev 3.774 pts (eps <= G/2: False))
- large/ARC/Text eps=0.01: counted False (no joint certificate)
- large/ARC/Text eps=0.02: counted False (cov 0.7793 (>= .20: True); G_dev 2.007 pts (eps <= G/2: False))
- large/MMLU-Pro/Text eps=0.01: counted False (cov 0.4048 (>= .20: True); G_dev 1.401 pts (eps <= G/2: False))
- large/MMLU-Pro/Text eps=0.02: counted False (cov 0.4048 (>= .20: True); G_dev 1.401 pts (eps <= G/2: False))
- large/OBQA/Text+fact eps=0.01: counted True (cov 0.5364 (>= .20: True); G_dev 7.143 pts (eps <= G/2: True))
- large/OBQA/Text+fact eps=0.02: counted True (cov 0.6644 (>= .20: True); G_dev 7.143 pts (eps <= G/2: True))
- Llama-3.1-8B/OBQA/Text eps=0.01: counted True (cov 0.4501 (>= .20: True); G_dev 4.447 pts (eps <= G/2: True))
- Llama-3.1-8B/OBQA/Text eps=0.02: counted True (cov 0.5903 (>= .20: True); G_dev 4.447 pts (eps <= G/2: True))
- Llama-3.1-8B/ARC/Text eps=0.01: counted False (no joint certificate)
- Llama-3.1-8B/ARC/Text eps=0.02: counted True (cov 0.4080 (>= .20: True); G_dev 7.023 pts (eps <= G/2: True))

Infeasible (N < N_min): large/ARC/Text (N = 448) at eps = 0.01; Llama-3.1-8B/ARC/Text (N = 448) at eps = 0.01.
Out-of-sample CP upper end >= eps (appendix): large/OBQA/Text+fact eps=0.02 held-out OBQA 744: k_L/N = 8/744 CP95 upper 0.0211.
Family-wise error of each joint certificate <= .04 per setting and eps (.02 change-rate family + .02 L family), .06 per setting if both eps are read. large/OBQA/Text and Text+fact are nominal (their calibration labels were used when ProbeMax was selected). Exposure: as the PREREG states, and REPRO (h) found that an earlier result file (E6_RESULTS.md / E6_RESULTS.json) already contained the Text+fact calibration lost-correction count at the deployed q = .75 (18 of 999 omitted) and over the whole split (122); the recomputed k_L at tau_frozen is 18. No such count exists for the other five settings. Exposure statement (authors' wording, added after the report): The PREREG exposure sentence was incomplete: E6 (P2_R2_GPU_20260919T220941Z/e6/E6_RESULTS.md, line 44) had reported Text+fact's calibration lost-correction count at q=.75 (18 of 999 omitted) and over the whole split (122); it was not among the numbers used when fixing eps, the coverage bar, or the gain condition, but it was on record.

Appendix table (all 6 settings x 2 eps; also results/E21_1_appendix_table.csv; D = D_all/D_seq/D_dep/D_need; dAcc = acc(pi) - acc(b); panel = recomposed mean saving vs the fixed reference, not a replay):

- large/OBQA/Text [nominal] eps=0.01: N 1366 | N_min 688 (feasible) | q_frozen 0.8 | q_L 0.65 | q_joint 0.65 | D 143/8/4/8 | dev cov 62.0% | dev L/W 3/3 | dAcc +0.00 pts [-0.67, +0.67] | G_dev 3.77 pts | retention 1.000 | OOS held-out OBQA 744: N 744 cov 65.2% k_L/N 2/744 = 0.27% [0.03%, 0.97%] (<eps True) W 1 dAcc -0.13 [-0.54, +0.27] ret 0.966 | panel 393.4 ms [310.3, 468.8] (frozen 517.1 [447.8, 583.6]; 20/97 re-routed) | C\X (N 1158, change-test q 0.8): q_joint 0.6 | counted: True
- large/OBQA/Text [nominal] eps=0.02: N 1366 | N_min 342 (feasible) | q_frozen 0.8 | q_L 0.75 | q_joint 0.75 | D 143/18/12/18 | dev cov 72.2% | dev L/W 9/6 | dAcc -0.40 pts [-1.48, +0.54] | G_dev 3.77 pts | retention 0.893 | OOS held-out OBQA 744: N 744 cov 75.0% k_L/N 4/744 = 0.54% [0.15%, 1.37%] (<eps True) W 2 dAcc -0.27 [-0.94, +0.40] ret 0.931 | panel 490.0 ms [411.9, 560.5] (frozen 517.1 [447.8, 583.6]; 5/97 re-routed) | C\X (N 1158, change-test q 0.8): q_joint 0.75 | counted: False
- large/ARC/Text eps=0.01: N 448 | N_min 688 (infeasible at eps) | q_frozen 0.95 | q_L NONE | q_joint NONE | D 12/0/N/A/0 | dev N/A (q_joint NONE) | OOS N/A (q_joint NONE) | panel N/A | C\X (N 315, change-test q 0.95): q_joint NONE | counted: False
- large/ARC/Text eps=0.02: N 448 | N_min 342 (feasible) | q_frozen 0.95 | q_L 0.8 | q_joint 0.8 | D 12/1/0/1 | dev cov 77.9% | dev L/W 0/0 | dAcc +0.00 pts [+0.00, +0.00] | G_dev 2.01 pts | retention 1.000 | OOS sealed ARC 1,172: N 1172 cov 79.0% k_L/N 0/1172 = 0.00% [0.00%, 0.31%] (<eps True) W 0 dAcc +0.00 [+0.00, +0.00] ret N/A | panel 588.6 ms [522.4, 656.1] (frozen 717.6 [670.6, 763.2]; 21/120 re-routed) | C\X (N 315, change-test q 0.95): q_joint NONE | counted: False
- large/MMLU-Pro/Text eps=0.01: N 6000 | N_min 688 (feasible) | q_frozen 0.4 | q_L 0.45 | q_joint 0.4 | D 1295/153/67/67 | dev cov 40.5% | dev L/W 12/14 | dAcc +0.08 pts [-0.30, +0.45] | G_dev 1.40 pts | retention 1.054 | OOS N/A (MMLU-Pro: no unused data) | panel 346.3 ms [249.8, 443.0] (frozen 346.3 [249.8, 443.0]; 0/48 re-routed) | C\X (N 6000, change-test q 0.4): q_joint 0.4 | counted: False
- large/MMLU-Pro/Text eps=0.02: N 6000 | N_min 342 (feasible) | q_frozen 0.4 | q_L 0.6 | q_joint 0.4 | D 1295/361/67/67 | dev cov 40.5% | dev L/W 12/14 | dAcc +0.08 pts [-0.30, +0.45] | G_dev 1.40 pts | retention 1.054 | OOS N/A (MMLU-Pro: no unused data) | panel 346.3 ms [249.8, 443.0] (frozen 346.3 [249.8, 443.0]; 0/48 re-routed) | C\X (N 6000, change-test q 0.4): q_joint 0.4 | counted: False
- large/OBQA/Text+fact [nominal] eps=0.01: N 1366 | N_min 688 (feasible) | q_frozen 0.75 | q_L 0.55 | q_joint 0.55 | D 170/7/3/7 | dev cov 53.6% | dev L/W 1/0 | dAcc -0.13 pts [-0.40, +0.00] | G_dev 7.14 pts | retention 0.981 | OOS held-out OBQA 744: N 744 cov 54.3% k_L/N 2/744 = 0.27% [0.03%, 0.97%] (<eps True) W 0 dAcc -0.27 [-0.67, +0.00] ret 0.967 | panel 245.1 ms [195.7, 293.1] (frozen 343.4 [297.7, 386.0]; 24/92 re-routed) | C\X (N 1158, change-test q 0.75): q_joint 0.55 | counted: True
- large/OBQA/Text+fact [nominal] eps=0.02: N 1366 | N_min 342 (feasible) | q_frozen 0.75 | q_L 0.7 | q_joint 0.7 | D 170/22/16/22 | dev cov 66.4% | dev L/W 6/0 | dAcc -0.81 pts [-1.48, -0.27] | G_dev 7.14 pts | retention 0.887 | OOS held-out OBQA 744: N 744 cov 70.2% k_L/N 8/744 = 1.08% [0.47%, 2.11%] (<eps False) W 2 dAcc -0.81 [-1.61, +0.00] ret 0.900 | panel 306.2 ms [259.2, 352.0] (frozen 343.4 [297.7, 386.0]; 9/92 re-routed) | C\X (N 1158, change-test q 0.75): q_joint 0.65 | counted: True
- Llama-3.1-8B/OBQA/Text eps=0.01: N 1366 | N_min 688 (feasible) | q_frozen 0.6 | q_L 0.45 | q_joint 0.45 | D 217/12/7/12 | dev cov 45.0% | dev L/W 1/3 | dAcc +0.27 pts [-0.27, +0.81] | G_dev 4.45 pts | retention 1.061 | OOS held-out OBQA 744 (E16-1): N 744 cov 44.0% k_L/N 1/744 = 0.13% [0.00%, 0.75%] (<eps True) W 0 dAcc -0.13 [-0.40, +0.00] ret 0.950 | panel 218.1 ms [164.1, 273.4] (frozen 318.6 [261.1, 372.1]; 22/76 re-routed) | C\X (N 1158, change-test q 0.5): q_joint 0.35 | counted: True
- Llama-3.1-8B/OBQA/Text eps=0.02: N 1366 | N_min 342 (feasible) | q_frozen 0.6 | q_L 0.6 | q_joint 0.6 | D 217/32/21/21 | dev cov 59.0% | dev L/W 2/4 | dAcc +0.27 pts [-0.40, +0.94] | G_dev 4.45 pts | retention 1.061 | OOS held-out OBQA 744 (E16-1): N 744 cov 59.1% k_L/N 3/744 = 0.40% [0.08%, 1.17%] (<eps True) W 0 dAcc -0.40 [-0.94, +0.00] ret 0.850 | panel 318.6 ms [261.1, 372.1] (frozen 318.6 [261.1, 372.1]; 0/76 re-routed) | C\X (N 1158, change-test q 0.5): q_joint 0.5 | counted: True
- Llama-3.1-8B/ARC/Text eps=0.01: N 448 | N_min 688 (infeasible at eps) | q_frozen 0.7 | q_L NONE | q_joint NONE | D 40/0/N/A/0 | dev N/A (q_joint NONE) | OOS N/A (q_joint NONE) | panel N/A | C\X (N 315, change-test q 0.55): q_joint NONE | counted: False
- Llama-3.1-8B/ARC/Text eps=0.02: N 448 | N_min 342 (feasible) | q_frozen 0.7 | q_L 0.45 | q_joint 0.45 | D 40/1/0/1 | dev cov 40.8% | dev L/W 0/0 | dAcc +0.00 pts [+0.00, +0.00] | G_dev 7.02 pts | retention 1.000 | OOS ARC test 1,172 (E16-1): N 1172 cov 44.3% k_L/N 2/1172 = 0.17% [0.02%, 0.62%] (<eps True) W 2 dAcc +0.00 [-0.34, +0.34] ret 1.000 | panel 199.0 ms [144.6, 254.9] (frozen 418.9 [361.7, 473.7]; 43/88 re-routed) | C\X (N 315, change-test q 0.55): q_joint NONE | counted: True

Frozen-policy dev numbers for comparison are in results/E21_1_dev.csv (policy = frozen) and the appendix CSV (frozen_dev_*); frozen out-of-sample rows in results/E21_1_oos.csv.

## E21-2 AUROC on unsaturated questions

**Writing rule branch: otherwise (.70 <= median(ii) < .80).** Sec. 6 (always): Sec. 6 (u = 0 paragraph): AUROC on u > 0 over the nine policies ranges 0.739-0.827 (median 0.774); AUROC of the float64 score m on all dev questions has median 0.884.

> on unsaturated questions alone the AUROC is 0.739-0.827 (median 0.774), lower than on all questions (median 0.883)

Deciding numbers: median (ii) = 0.7743 (range 0.7388 medium/OBQA/C2C q=.55 - 0.8271 large/ARC/C2C); median (i) = 0.8826; median (iii) = 0.8843. (i) reproduces the paper to 5e-4 for all 9 policies and 3 controls; (vi) = 0.00-2.18% over the nine policies, reproducing E17-1 (n0/k0 match E17_1_u0_rule.csv).

- medium/OBQA/C2C q=.55: (i) 0.8401 | (ii) 0.739 [0.690, 0.789] 124/421 | (iii) 0.848 | (iv) 0.777 7/321 | (v) u=0 share 43.3%, dis. with u>0 94.7% | (vi) 2.18%
- medium/ARC/C2C: (i) 0.9097 | (ii) 0.748 [0.658, 0.837] 47/125 | (iii) 0.913 | (iv) 0.682 1/174 | (v) u=0 share 58.2%, dis. with u>0 97.9% | (vi) 0.57%
- large/OBQA/Text: (i) 0.8727 | (ii) 0.769 [0.707, 0.826] 70/388 | (iii) 0.876 | (iv) 0.753 2/354 | (v) u=0 share 47.7%, dis. with u>0 97.2% | (vi) 0.56%
- large/OBQA/C2C: (i) 0.8826 | (ii) 0.779 [0.724, 0.831] 59/388 | (iii) 0.884 | (iv) 0.697 1/354 | (v) u=0 share 47.7%, dis. with u>0 98.3% | (vi) 0.28%
- large/ARC/Text: (i) 0.9519 | (ii) 0.796 [0.686, 0.896] 15/82 | (iii) 0.952 | (iv) N/A 0/217 | (v) u=0 share 72.6%, dis. with u>0 100.0% | (vi) 0.00%
- large/ARC/C2C: (i) 0.9088 | (ii) 0.827 [0.673, 0.954] 11/82 | (iii) 0.931 | (iv) 0.861 1/217 | (v) u=0 share 72.6%, dis. with u>0 91.7% | (vi) 0.46%
- large/MMLU-Pro/Text: (i) 0.8215 | (ii) 0.757 [0.734, 0.778] 553/1996 | (iii) 0.822 | (iv) 0.723 8/645 | (v) u=0 share 24.4%, dis. with u>0 98.6% | (vi) 1.24%
- large/MMLU-Pro/C2C: (i) 0.8464 | (ii) 0.774 [0.753, 0.795] 751/1996 | (iii) 0.847 | (iv) 0.938 5/645 | (v) u=0 share 24.4%, dis. with u>0 99.3% | (vi) 0.78%
- large/OBQA/Text+fact: (i) 0.8886 | (ii) 0.781 [0.728, 0.832] 75/388 | (iii) 0.892 | (iv) 0.983 1/354 | (v) u=0 share 47.7%, dis. with u>0 98.7% | (vi) 0.28%
- Llama-3.1-8B/OBQA/Text [control, dev]: (i) 0.8745 (86/742) | (v) u=0 share 0.0%, dis. with u>0 100.0%
- Llama-3.1-8B/ARC/Text [control, dev]: (i) 0.8804 (37/299) | (v) u=0 share 0.0%, dis. with u>0 100.0%
- SQuAD/Llama (s2) [control, dev]: (i) 0.8109 (154/1000) | (v) u=0 share 0.0%, dis. with u>0 100.0%
- medium/OBQA/C2C q=.55 [held-out OBQA 744]: (i) 0.8582 | (ii) 0.770 [0.722, 0.815] 125/438 | (iii) not stored | (iv) not stored (5/306 in u=0) | (v) u=0 share 41.1%, dis. with u>0 96.2%
- large/OBQA/Text [held-out OBQA 744]: (i) 0.9086 | (ii) 0.837 [0.785, 0.887] 60/398 | (iii) not stored | (iv) not stored (1/346 in u=0) | (v) u=0 share 46.5%, dis. with u>0 98.4%
- large/OBQA/C2C [held-out OBQA 744]: (i) 0.8987 | (ii) 0.839 [0.787, 0.885] 60/398 | (iii) not stored | (iv) not stored (2/346 in u=0) | (v) u=0 share 46.5%, dis. with u>0 96.8%
- large/OBQA/Text+fact [held-out OBQA 744]: (i) 0.8826 | (ii) 0.771 [0.714, 0.826] 81/398 | (iii) not stored | (iv) not stored (1/346 in u=0) | (v) u=0 share 46.5%, dis. with u>0 98.8%
- Llama-3.1-8B/OBQA/Text [control, held-out OBQA 744 (E16-1)]: (i) 0.8930 (89/744)

Held-out (iii)/(iv): not stored (authors' decision: no substitute m). E16-3 prefilled bf16 label logits only for fit/cal/dev units; the held-out records store float32 p_labels only.

## E21-3a option-rotation stability at u = 0

**Gate: PASS.** Code/protocol: `P2_R1_EXP_.../PROTOCOL_FREEZE.md` sec. 6 ("V1 perm: the option list is rotated by one position, so original option i sits at position (i+1) mod K, and labels are re-assigned by position"; "The parsed displayed label at position p maps back to the original label at index (p-1) mod K. INVALID stays INVALID"); `src/prepare_populations.py` rotate() (only choice_text / choices.text change, labels fixed, back map); `src/e4_null.py` (V1 = `runner.request(v1_query, "receiver_only")`, the same call as the unchanged V0 replay; generation config asserted equal to the frozen receiver config, greedy, max_new_tokens 64). Programmatic checks (results/E21_3a_gate_checks.csv): 25/25 PASS: every population row is a pure one-position rotation of option contents with labels, stem and other fields unchanged; every V1 record maps back with its own map; rendered V1 prompts equal V0 prompts with option contents rotated; one generation config. V1 records carry no probe score, so the share of u = 0 questions that stay at u = 0 under rotation is not stored.

**Writing rule branch: otherwise (>= 1 of the five u = 0 CP upper ends >= 5%).** Failing populations (u = 0 CP upper >= 5%): medium/OBQA, medium/ARC, large/MMLU-Pro.

> Sec. 6 gives the numbers (medium/OBQA: 19/321 = 5.9% [CP upper 9.1%]; medium/ARC: 11/174 = 6.3% [CP upper 11.0%]; large/OBQA: 9/354 = 2.5% [CP upper 4.8%]; large/ARC: 4/217 = 1.8% [CP upper 4.7%]; large/MMLU-Pro: 23/645 = 3.6% [CP upper 5.3%]), names medium/OBQA, medium/ARC, large/MMLU-Pro; Limitations adds "part of the receiver's confident answers follow option position; the certificate covers the deployed prompt format".

Neither branch is used to argue about training-data contamination.

- small/OBQA: u=0 n 0, 0, N/A | u>0 n 742, 558, 75.2% [71.9%, 78.3%] | all n 742, 558, 75.2% [71.9%, 78.3%] | parseable-only all n 696, 521, 74.9% [71.5%, 78.0%] | V0 vs R (drift) 0/742
- small/ARC: u=0 n 0, 0, N/A | u>0 n 299, 209, 69.9% [64.4%, 75.0%] | all n 299, 209, 69.9% [64.4%, 75.0%] | parseable-only all n 258, 180, 69.8% [63.8%, 75.3%] | V0 vs R (drift) 0/299
- medium/OBQA: u=0 n 321, 19, 5.9% [3.6%, 9.1%] | u>0 n 421, 164, 39.0% [34.3%, 43.8%] | all n 742, 183, 24.7% [21.6%, 27.9%] | parseable-only all n 732, 176, 24.0% [21.0%, 27.3%] | V0 vs R (drift) 0/742
- medium/ARC: u=0 n 174, 11, 6.3% [3.2%, 11.0%] | u>0 n 125, 42, 33.6% [25.4%, 42.6%] | all n 299, 53, 17.7% [13.6%, 22.5%] | parseable-only all n 297, 51, 17.2% [13.1%, 22.0%] | V0 vs R (drift) 0/299
- large/OBQA: u=0 n 354, 9, 2.5% [1.2%, 4.8%] | u>0 n 388, 128, 33.0% [28.3%, 37.9%] | all n 742, 137, 18.5% [15.7%, 21.4%] | parseable-only all n 739, 134, 18.1% [15.4%, 21.1%] | V0 vs R (drift) 0/742
- large/ARC: u=0 n 217, 4, 1.8% [0.5%, 4.7%] | u>0 n 82, 16, 19.5% [11.6%, 29.7%] | all n 299, 20, 6.7% [4.1%, 10.1%] | parseable-only all n 299, 20, 6.7% [4.1%, 10.1%] | V0 vs R (drift) 0/299
- large/MMLU-Pro: u=0 n 645, 23, 3.6% [2.3%, 5.3%] | u>0 n 1996, 891, 44.6% [42.4%, 46.9%] | all n 2641, 914, 34.6% [32.8%, 36.5%] | parseable-only all n 2631, 906, 34.4% [32.6%, 36.3%] | V0 vs R (drift) 0/2641
- medium/OBQA/C2C q=.55 omitted dev (the receiver's own answer change under rotation, not the policy's change rate): 34/390 = 8.7% [6.1%, 12.0%]; u=0 19/321; u>0 15/69 = 21.7%
- medium/ARC/C2C omitted dev (the receiver's own answer change under rotation, not the policy's change rate): 12/189 = 6.3% [3.3%, 10.8%]; u=0 11/174; u>0 1/15 = 6.7%
- large/OBQA/Text omitted dev (the receiver's own answer change under rotation, not the policy's change rate): 57/572 = 10.0% [7.6%, 12.7%]; u=0 9/354; u>0 48/218 = 22.0%
- large/OBQA/C2C omitted dev (the receiver's own answer change under rotation, not the policy's change rate): 57/572 = 10.0% [7.6%, 12.7%]; u=0 9/354; u>0 48/218 = 22.0%
- large/ARC/Text omitted dev (the receiver's own answer change under rotation, not the policy's change rate): 12/284 = 4.2% [2.2%, 7.3%]; u=0 4/217; u>0 8/67 = 11.9%
- large/ARC/C2C omitted dev (the receiver's own answer change under rotation, not the policy's change rate): 9/270 = 3.3% [1.5%, 6.2%]; u=0 4/217; u>0 5/53 = 9.4%
- large/MMLU-Pro/Text omitted dev (the receiver's own answer change under rotation, not the policy's change rate): 96/1069 = 9.0% [7.3%, 10.9%]; u=0 23/645; u>0 73/424 = 17.2%
- large/MMLU-Pro/C2C omitted dev (the receiver's own answer change under rotation, not the policy's change rate): 96/1069 = 9.0% [7.3%, 10.9%]; u=0 23/645; u>0 73/424 = 17.2%
- large/OBQA/Text+fact omitted dev (the receiver's own answer change under rotation, not the policy's change rate): 47/536 = 8.8% [6.5%, 11.5%]; u=0 9/354; u>0 38/182 = 20.9%

## Files

- PREREG.md / PREREG.sha256, INPUTS.md, REPRO.md, CERT.json / CERT.sha256, DEVIATIONS.md, SCRIPT_HASHES.md
- results/: step0_repro_checks.csv, step0_recomputed_calibration_ledgers.csv, step0h_exposure_hits.json, E21_1_cert_candidates.csv, E21_1_cert_summary.csv, E21_1_dev.csv, E21_1_oos.csv, E21_1_panel.csv, E21_1_appendix_table.csv, E21_1_writing_rule.json, E21_2_auroc.csv, E21_2_checks.csv, E21_2_writing_rule.json, E21_3a_gate_checks.csv, E21_3a_rotation.csv, E21_3a_writing_rule.json
- logs/: one log and one *_run.json (start/end UTC, script and common-module sha256, every file read) per script
