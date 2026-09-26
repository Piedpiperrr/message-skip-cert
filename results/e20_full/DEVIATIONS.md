# DEVIATIONS.md — E20-full (P2_R8_E20F_20260922T003652Z)

Recorded before any E20-full output (with PREREG_E20F.md):

- Against the pilot PREREG_E20P.md full-run design:
  - (E1) fit questions also get helper messages and receiver-with-message outputs (pilot: "fit 500 (receiver-only outputs only)"); they are used only
    for re-splits and descriptive fit statistics; certification reads only fit s2.
  - (E2) a test split of the next 1,000 questions (pool positions 3,900-4,899) is added; scored only if a threshold is deployed.
  - Writing rules: the title rule and the test condition are narrowed (PREREG_E20F.md block rules (1), (1a), (1b), (7)).
  - "Nothing is edited after seeing the pilot": the full-run driver is src/e20f_exec.py, derived from the pilot's src/e20_exec.py with only the
    pre-authorized changes (SQuAD + Llama only, full-run split files, E1, a 16-row preflight against the pilot's stored rows, a per-job plan that
    continues the remainder by question id). The pilot modules e20_prompts / e20_extract / e20_exec_common are imported unmodified and the
    helper / receiver / scoring functions are verbatim (asserted); every change is in CODE_DIFF.patch.
- Implementation details fixed here where the blocks leave them open are listed in PREREG_E20F.md ("Implementation choices").

After the run (2026-09-22T03:32Z): no deviation from PREREG_E20F.md. Job 1 (7643654) and job 2 (7643669) each completed their phase in one job
(no leftover job, no resubmission); both preflights 16/16 bitwise; CERT hashed 03:24:08Z before job 2 was submitted (03:24:18Z); STATS / ROUTES
hashed 03:30:55-56Z; gold first opened 03:31:13Z.
