# X3 results: Llama-3.1-8B-Instruct receiver @ 0e9e39f2; saved Qwen2.5-7B large-pair Text messages; reference Text

Sources:
- Written by `src/analyze_x3.py` on 2026-09-21 from `results/runs/chain_00..07.jsonl` (job 7641947). `MANIFEST.sha256` was verified 16/16 before analysis.
- Certification and all gold-free diagnostics were hashed in `CERT_HASHES.json` at 07:07:19.8Z. Gold was decoded afterwards (`X3_RESULTS.json`, 07:07:23Z).
- PREREG_X3.md SHA-256 8a2f6c6d…, hashed 06:36:04Z.

| setting | N fit/cal/dev | cal dis. | dev dis. | dev AUROC (MW, ties ½) | q (cal k/n, p) | min p (q, k/n) | dev coverage | dev changed/omitted [CP95] |
|---|---|---|---|---|---|---|---|---|
| X3 OBQA/Text | 2100/1366/742 | 217/1366 (.1589) | 86/742 (.1159) | .8745 | .60 (21/800, 5.74e-4) | 2.07e-8 (.35, 2/457) | 59.0% (438/742) | 7/438 = .0160 [.0064, .0327] |
| X3 ARC/Text | 670/448/299 (671 rows in fit) | 40/448 (.0893) | 37/299 (.1237) | .8804 | .70 (4/320, 3.15e-4) | 2.71e-5 (.45, 0/205) | 68.9% (206/299) | 4/206 = .0194 [.0053, .0490] |

- **Ledger:** `certification_ledger_40.csv`, 40 tests.
  - Accepted q: OBQA .15–.60 (10 of 20); ARC .35–.70 (8 of 20). Both settings deploy.
- **INVALID** (`invalid_and_disagreement_split.csv`):
  - OBQA: R cal 0/1366, dev 1/742; Text cal 1/1366, dev 0/742.
  - ARC: 0 on both paths in both splits.
- **Disagreement split** (both parseable / only R INVALID / only Text INVALID):
  - OBQA cal 216/0/1, dev 85/1/0.
  - ARC cal 40/0/0, dev 37/0/0.
- **Diagnostics** (descriptive, not deployable):
  - **Both-parse** (`diag_bothparse.csv`): OBQA q .60 (cal 1365/1366 kept); ARC q .70 (448/448 kept). Both certify.
  - **Re-splits, seeds 1–200** (`diag_resplit.csv`; seed 0 reproduces the frozen split):
    - certification rate 1.00 / 1.00; agreement with the original outcome 1.00 / 1.00;
    - median q .60 / .70; median dev coverage .593 / .662.
  - **Share of dev questions with u == 0:** 0/742, 0/299.
  - **Argmax recertification** (`diag_argmax_recert.csv`): q_A = .60 / .70. o_A agrees with R on cal .9956 / .9933.
- **Accuracy** (`accuracy_per_split.csv`, gold decoded last):
  - dev R 603/742 (.8127) vs Text 636/742 (.8571) on OBQA; R 239/299 (.7993) vs Text 260/299 (.8696) on ARC.
  - Policy vs fixed Text correct on dev: OBQA 638 vs 636; ARC 258 vs 260 (`dev_table.csv`).
- **Replay (Step 6):** not run. The E3 driver cannot switch the receiver by model id + chat template (`notes/STEP6_FEASIBILITY.md`; DEVIATIONS D14).
