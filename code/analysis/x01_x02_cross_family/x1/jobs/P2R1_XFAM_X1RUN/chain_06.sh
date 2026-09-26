#!/bin/bash
# X1 c2c chain 06 (1418 rows, est 16.5 min)
"$PY" run_x1_c2c.py --mode run --dataset arc --rows $DATA_DIR/P2_R1_XFAM_20260919T095058Z/x1/records/work/run/P2R1_XFAM_X1RUN_chain_06.jsonl --gpu $G --workdir "$OUT/c2c_chain_06_work" --out "$OUT/c2c_chain_06.jsonl"
echo "EXIT chain_06 $?"
