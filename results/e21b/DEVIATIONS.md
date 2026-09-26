# E21B deviations and notes

- **D1: job wrappers counted separately from the 60-line limit on driver changes.**
  - The driver `src/e21b_exec.py` differs from E9B `e9b_exec.py` by 22 added and 7 removed lines (29 changed; limit 60).
  - The job wrappers were counted separately: `src/slot_e21b.sh` is +42 / -18 against E9B `slot_e9b.sh`, and `jobs/e21b_job1.pbs` is +14 / -37 against E9B `run_e9bc.pbs` (diffs in `diffs/`).
  - The wrappers only launch processes: per-rank preflight parts, a file barrier, the gate verdict, and production shards.
  - P1 identity rotation reproduced every stored output byte for byte, so the wrappers do not change outputs. Every arm was identical on 16/16 rows per population; R was identical on 32/32; u was bitwise equal on 32/32; probe input IDs and prompt lengths matched the stored values on every row (`preflight/PREFLIGHT_GATE.json`).
- **D2: one job instead of two.** The cost estimate from the stored per-request timings was 3,614 slot-seconds (INPUTS.md §7). All work fit in debug job 7643984 (walltime used 00:19:18), so job 2 was never submitted and no resubmission was used.
