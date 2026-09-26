#!/bin/bash
# X1 text chain 02 (1407 rows, est 18.8 min)
CUDA_VISIBLE_DEVICES=$G "$PY" run_x1_helper.py --mode run --rows $DATA_DIR/P2_R1_XFAM_20260919T095058Z/x1/records/work/run/P2R1_XFAM_X1RUN_chain_02.jsonl --out "$OUT/helper_chain_02.jsonl" && CUDA_VISIBLE_DEVICES=$G "$PY" run_x1_receiver.py --mode run --rows $DATA_DIR/P2_R1_XFAM_20260919T095058Z/x1/records/work/run/P2R1_XFAM_X1RUN_chain_02.jsonl --messages "$OUT/helper_chain_02.jsonl" --out "$OUT/text_chain_02.jsonl"
echo "EXIT chain_02 $?"
