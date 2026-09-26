#!/bin/bash
set -u
GR="${PALS_RANKID:-${PMI_RANK:-0}}"
if [ "$GR" = "0" ]; then export E8_FORCE_PAIR=small; else export E8_FORCE_PAIR=medium; export E8_RUN_LARGE=1; fi
exec bash "$E8_DIR/src/slot.sh" "$E8_DIR/src/validate_smoke.py"
