#!/bin/bash
set -u
GR="${PALS_RANKID:-${PMI_RANK:-0}}"
CFG="$E8_DIR/REPLAY_E8/protocol/RANK_${GR}.env"
[ -f "$CFG" ] || { echo "no replay work for rank $GR"; exit 0; }
. "$CFG"                       # sets E8_FORCE_PAIR and E8_REPLAY_REFS
export E8_FORCE_PAIR E8_REPLAY_REFS
exec bash "$E8_DIR/src/slot.sh" "$E8_DIR/src/replay_e8.py"
