#!/bin/bash
# X1 c2c chain 04 (2104 rows, est 24.5 min)
"$PY" run_x1_c2c.py --mode run --dataset obqa --rows $DATA_DIR/P2_R1_XFAM_20260919T095058Z/x1/records/work/run/P2R1_XFAM_X1RUN_chain_04.jsonl --gpu $G --workdir "$OUT/c2c_chain_04_work" --out "$OUT/c2c_chain_04.jsonl"
echo "EXIT chain_04 $?"
