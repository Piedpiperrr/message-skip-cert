# E18 — result: PREFLIGHT FAILED, production not run (writing rule 4)

PREREG_E18.md sha256 afcf7e18aa22dc85763f27759a37d4bbbaaf37a080f477cb8b4bbeec56e9a9fa (utc 2026-09-22T02:48:57Z).
Job code CODE_E18.sha256 (utc 2026-09-22T02:50:47Z). Job 7643632 (ClusterA debug, select=1, walltime 00:40:00):
start 2026-09-22T02:51:00Z, model load 91 s per rank, PREFLIGHT.json 02:52:57Z, all 4 ranks exit 4, end 02:53:01Z.
`records/PREFLIGHT.json` sha256 9afdbb3bc0a23ce6a7e0ad360e3cd776196ad057d6812d2ccb8a9fc43e58f5f6.

No s_D was computed on any row (production did not start); no SCORES_E18.parquet, no CERT_E18.json; no gold was read.
Per the PREREG ("If (a) or (b) fails, stop; production is not run") and writing rule (4): no test is reported; the provenance
table records that a planned second GSM8K score was not completed. A preflight failure is a PREREG stop, not a non-scientific
failure, so the one allowed resubmission does not apply.

## Preflight (37 fit rows: first 16 in E10 order + 21 further rows with u > 0)

- (a) teacher-forced argmax = stored token at positions 1..32 pooled: 1177/1184 = 99.41% (>= 99%) — PASS.
- (b) u and s3 vs E10 stored, tolerance 1e-4 — FAIL: max |diff| u 0.03918, s3 0.06028. 2/37 rows exceed 1e-4:
  - gsm8k_train_05894: u .21105 (E10) vs .25023 (E18 pass); s3 .37756 vs .43784.
  - gsm8k_train_02750: u .03515 vs .04409; s3 .13304 vs .16458.
  - The other 35 rows are within 1e-4 (34 with |diff| 0; gsm8k_train_06251 1.27e-05).
  - Row gsm8k_train_05081 (extra pass over E10's own re-scoring input): |diff| u 0, s3 0.
- s2 (reported, not gated): max |diff| 0.002823 over the 37 rows.

## Diagnostic (after the stop, from stored token counts only; not a test)

Both failing rows are 320-token capped outputs whose E18 input runs 15 tokens past the end of E10's re-scoring input
(E10 stopped at the answer). The 6 matched rows with u > 1e-3 checked on the stored-token pass run 1-3 tokens past it
(up to 60 on rows with u < 1e-3).
This fits the residual risk recorded before the PREREG (bf16 logits at the answer positions depend on the input length),
but it was not tested further.
