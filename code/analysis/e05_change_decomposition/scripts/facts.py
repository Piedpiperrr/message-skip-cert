"""Facts F1-F4 from project records (read-only)."""
from r2_common import *
H = '$HOME_DIR/analysis/channel_selection_gate2/gate2b_labelblind_staging_hardened_gpu_v2_20260726'
G = '$DATA_DIR/gate2c_train_dev_question_staging_v1_20260727'
rows = [
 dict(fact='F1', question='How the 4,208-question OBQA pool was drawn from the 4,957-question official training split',
      answer=('Two steps, both label-blind. (1) Exclusion: 5 of 4,957 rows removed as DUPLICATE_EXACT_CONTENT_WITHIN_TRAIN '
              '(exact-content aliases; each maps to a retained row), leaving 4,952 eligible rows. '
              '(2) Deterministic hash split, no RNG: per row split_digest = SHA256(b"gate2b-split-v1\\0" + row_fingerprint_bytes); '
              'rows sorted by (split_digest, dataset_id, raw example_id); first floor(70%) -> router_train (3,466), '
              'next floor(15%) -> router_dev (742), remainder -> untouched_final_holdout (744). '
              'The 4,208-question pool = router_train + router_dev; the 744 holdout rows are excluded from it. '
              'It is a deterministic content-hash partition, not a random sample and not a difficulty/answer filter.'),
      sources=f'{H}/gate2b_staging_report.md (section "Deterministic split"); {H}/split_summary.tsv; {H}/excluded_rows.tsv (5 rows); '
              f'{G}/source_access_receipt.json (source_parquet_rows 4957, train_dev_rows_selected 4208); '
              f'$DATA_DIR/gate2d_final_holdout_evaluation_20260727/final_holdout_report.md (3466/742/744, excluded 5); '
              f'staged into P2 via P2_5_20260910T072811Z/prepare_p2_5.py (reads router_{{train,dev}}_questions.arrow)'),
 dict(fact='F2', question='Why MMLU-Pro was run for the large pair only',
      answer=('Decision record exists: Plan C (large pair only) was chosen on GPU budget and calendar grounds, then authorized by the user. '
              'Stage1 cost: Plan A (small+medium+large) 154.40 GPUh / 77.20 wall h, Plan B 105.96 / 52.98, Plan C 52.14 / 26.07, Plan D 155.39 / 77.69; '
              'only C was rated MODERATE_RISK, A/B/D HIGH_RISK, and only C fit before the deadline. C keeps the complete population '
              '(12,032 rows / 11,641 groups) and 6,000 calibration groups rather than shrinking calibration to pay for more pairs. '
              'The recorded cost of C: it uses the already-stronger large regime and therefore cannot speak to cross-scale behaviour on MMLU-Pro. '
              'Authorization: "Work user instruction: GO MMLU-Pro Plan C, exactly two Stage1 PBS jobs, no E2E".'),
      sources='P2_MMLU_PRO_BREADTH_PROTOCOL_AND_COST_REVIEW_20260915T224801Z/POPULATION_PLAN_COMPARISON.md (size, benefit/weakness and cost tables); '
              'P2_MMLU_PRO_BREADTH_STAGE1_20260916T002337Z/MMLU_PRO_STAGE1_PROTOCOL_FREEZE.json (field "authorization")'),
 dict(fact='F3', question='Why thinking was disabled, with the file/line that sets it',
      answer=('Inherited verbatim from the official C2C evaluator, which renders every chat prompt with enable_thinking=False; '
              'the project protocol copies that setting so its prompts stay byte-identical to the official pipeline. '
              'Official: script/evaluation/unified_evaluator.py:427 (also 856, 868, 926). '
              'Project runtimes: P2_5_20260910T072811Z/protocol_min.py:249 and P2_10_20260911T122423Z/protocol_min.py:249 '
              '(apply_chat_template(..., add_generation_prompt=True, enable_thinking=False)); medium '
              'P2_MEDIUM_PAIR_.../execution_retry1_.../src/native_runtime.py:124 and :143; MMLU-Pro '
              'P2_MMLU_PRO_BREADTH_STAGE1_.../src/native_runtime.py:153 and :172; cross-family P2_R1_XFAM_.../src/run_x2.py:85-86. '
              'Recorded as a frozen config field enable_thinking=false (P2_5_20260910T072811Z/frozen_config.json:92).'),
      sources='$DATA_DIR/c2c_reproduction_assets/official_C2C/script/evaluation/unified_evaluator.py:427; '
              'P2_5_20260910T072811Z/protocol_min.py:249; P2_5_20260910T072811Z/frozen_config.json:92'),
 dict(fact='F4', question='HF model revisions (commit hashes) of the small-pair and large-pair helpers and receivers',
      answer=('small helper Qwen/Qwen2.5-0.5B-Instruct @ 7ae557604adf67be50417f59c2c2f167def9a775; '
              'small receiver Qwen/Qwen3-0.6B @ c1899de289a04d12100db370d81485cdf75e47ca; '
              'large helper Qwen/Qwen2.5-7B-Instruct @ a09a35458c702b33eeacc393d103063234e8bc28; '
              'large receiver Qwen/Qwen3-8B @ b968826d9c46dd6066d109eabc6255188de91218. '
              'C2C fuser (large/MMLU-Pro) nics-efc/C2C_Fuser @ f01fc3258b305e280e04c7238f4f2cf31b7dc70d; '
              'small-pair fuser config recorded as qwen3_0.6b+qwen2.5_0.5b_Fuser__8704f555c6b4a60b764de7d755e6f1daf21a57ef.'),
      sources='P2_5_20260910T072811Z/frozen_config.json ("models"); P2_6_20260910T164138Z/frozen_config.json ("models"); '
              'P2_MMLU_PRO_BREADTH_STAGE1_20260916T002337Z/MODEL_SOURCE_INDEX.json; '
              'P2_R1_EXP_20260919T050555Z/records/fuser_configs/'),
]
for r in rows: r['label'] = LABEL
csvout(RES / 'facts_F1_F4.csv', rows)
for r in rows: print(r['fact'], '-', r['answer'][:150], '...')
