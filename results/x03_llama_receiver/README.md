# P2_R6_X3_20260921T052602Z — X3 (non-Qwen receiver, OBQA + ARC, Text only)

Status 2026-09-21T07:10Z: production 7641947 done (exit 0, 5,626/5,626 rows, manifest 16/16 OK). Step 5 done: see results/analysis/X3_SUMMARY.md
(certification hashed 07:07:19.8Z before gold). Both settings deploy (OBQA q=.60, ARC q=.70). Replay not run (D14).

Earlier status 2026-09-21T06:45Z: smoke job 7641942 done: Step 2 PASS 16/16, Llama smoke PASS (INVALID R 0/16, Text 0/16, BOS 1).
Production job 7641947 (P2R6_X3_RUN, debug, 2 nodes, 00:30, 8 chains, 5,626 rows) submitted 06:43:18Z. Step 5 analysis: src/analyze_x3.py 'results/runs/chain_*.jsonl'
(only after the user says the job has finished; verifies results/runs/MANIFEST.sha256 first).

Earlier status 2026-09-21T06:40Z: receiver = meta-llama/Llama-3.1-8B-Instruct @ 0e9e39f249a16976918f6564b8830bc894c89659 (own-token download, all files
verified; DEVIATIONS D10). PREREG_X3.md hashed 06:36:04Z (8a2f6c6d...). Smoke job 7641942 (debug, 1 node, 00:20) submitted 06:37Z:
Step 2 Qwen3-8B check on 16 OBQA fit rows, then (on PASS) Llama smoke on the same rows. Gold not read.

Earlier status 2026-09-21T06:25Z: user decision received: "A if HF access is granted by Mon Sep 21 14:00 CDT, else B" (Llama via user's own token only;
else Mistral-7B-Instruct-v0.3 with the run-dir sentencepiece add-on). Driver, smoke job, shard builder and analysis are prepared (see DEVIATIONS.md).
A single access check runs automatically at 19:00:00Z (14:00 CDT) -> logs/access_check_1400CDT.log, manifests/DOWNLOAD_llama31_8b.json.
No PREREG_X3.md yet; no X3 model output exists; no job submitted; no gold read.

Earlier status 2026-09-21T05:31Z: BLOCKED at Step 0 (receiver selection).

Step 0 evidence (tokenizer/config files only):
- `src/step0_receiver_check.py` -> `notes/STEP0_RECEIVER_CHECK.json`, `logs/step0_receiver_check.log` (access, shared-filesystem copies + blob/size check vs HF metadata, label-token rule)
- `src/step0_template_check.py` -> `notes/STEP0_TEMPLATE_CHECK.json`, `logs/step0_template_check.log` (rendered templates, BOS counts; Mistral via a scratch sentencepiece overlay, env unchanged)

Open question: does criterion (a) "cached on the shared filesystem" cover readable copies in OTHER users' areas of the project project?
- meta-llama/Llama-3.1-8B-Instruct @ 0e9e39f249a16976918f6564b8830bc894c89659: HF download DENIED for user (403, gated manual).
  Complete copies (all file sizes and blob names equal the HF metadata) exist only in otheruser1/hf_cache, otheruser2/BenchmarkDir/.hf-cache, otheruser3/.
  Label rule passes (A-E single tokens 32-36). Paper R path gives 2 BOS -> needs add_special_tokens=False (equals native ids).
- mistralai/Mistral-7B-Instruct-v0.3 @ c170c708c41dac9275d15a8fff4eca08d52bab71: downloadable (not gated). Tokenizer does not load in c2c_official
  (add_prefix_space -> from_slow -> needs sentencepiece, not installed). With sentencepiece 0.2.2 overlay: label rule passes (A-E 1098,1133,1102,1152,1181). 2 BOS in paper R path.
- ibm-granite/granite-3.1-8b-instruct @ 4009206d5fc95d2e65a7b7633e159d6e97e25d35: downloadable; label rule passes (A-E 51-55); default template injects a
  system prompt with the run date (strftime_now) and "You are Granite, developed by IBM...".
Downloads so far: config/tokenizer/generation_config files of Mistral and Granite -> $DATA_ROOT/hf_cache/hub (no weights).
