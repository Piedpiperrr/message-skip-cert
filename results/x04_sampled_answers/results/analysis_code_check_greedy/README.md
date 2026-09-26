Code check of src/analyze_x4.py before any X4 production output (2026-09-21, scratch copy with ROOT pinned to the repo): synthetic "sampled"
outputs set equal to the stored greedy V2 labels (o_R, o_T) for all 5,626 rows. Results equal the recorded values:
- greedy certification reproduces the paper: large/OBQA/Text q = .80, large/ARC/Text q = .95 (input_checks.csv);
- dev u == 0: 354/742 and 217/299 (paper / E14-2);
- E14-2 split at the frozen q (u0_split_E14_2.csv dev rows) = P2_R6_E14.../results/E14_2_zero_u.csv: OBQA n 572, k 19, n0 354, k0 2, n+ 218, k+ 17;
  ARC n 284, k 9, n0 217, k0 0, n+ 67, k+ 9;
- added disagreement 0 with bootstrap interval [0, 0] (identical labels), as it must be.
