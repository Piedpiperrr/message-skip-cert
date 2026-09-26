#!/bin/bash
# First main job only: rank 1 runs task 2(b), the unchanged large-pair control, in its own
# process before joining the collection. Every other rank goes straight to collection.
set -u
GR="${PALS_RANKID:-${PMI_RANK:-0}}"
if [ "$GR" = "1" ]; then
  E8_FORCE_PAIR=large bash "$E8_DIR/src/slot.sh" "$E8_DIR/src/validate_large_control.py" || echo "LARGE_CONTROL_FAILED rc=$?"
fi
exec bash "$E8_DIR/src/slot.sh" "$E8_DIR/src/execute_e8.py"
