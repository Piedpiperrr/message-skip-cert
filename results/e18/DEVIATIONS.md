# E18 — changes relative to the original E18 prompt (all made before any E18 score existed)

1. PREREG block: two replacements, set by the paper's writing side after the login-node gates (GATE.md "Decision needed":
   D1 = A, D2 = A) and before PREREG_E18.md was written: the "Preflight" paragraph (u/s3 gated at 1e-4; row gsm8k_train_05081
   checked with one extra pass over E10's own re-scoring input; s2 reported, not gated) and the title sentence in "Writing rules".
   Both are part of the hashed PREREG_E18.md; they are not deviations from it.
2. Machine: Step 0 gates ran on the ClusterB login node (shared filesystem, no weights, no job). On ClusterA the dry run was repeated
   (dryrun_ClusterA/: 4/4 ranks exit 0, 37 preflight rows, merge 1800 x 70; placeholder hash identical to the ClusterB dry run).
3. Code after the gates (before the job-code hash CODE_E18.sha256): src/e18_score.py PREFLIGHT_RULE set to the PREREG rule;
   the s2 term of the gate reordered to `not s2_gates or ...` (with tol_s2 = None the old order would raise a TypeError);
   job.sh: PBS directives added to the header (, -q debug, select=1, walltime 00:40:00,
   fsreq=<fs>; same values as the documented submit-job command). Nothing else changed.
