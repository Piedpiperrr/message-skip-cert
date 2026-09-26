# E12-b: STOPPED before submission — no batched serving path exists in the deployed implementation

**Status: not submitted. This is not a queue problem.** `job-status -u user` was empty at
2026-09-20T22:59Z and again before this report: both ClusterA debug positions (1 running + 1 queued)
were free, and E10 held neither. The block is in the code, not the allocation.

## Why

The prereg's batch-8 arm requires "the probe is batched over the group, and the reference is then
batched over whichever members of that group are routed". The deployed implementation has no batched
path at any of the three levels, and all three are inside the frozen/certified code:

1. **The probe** (`P2_R2_E7_20260919T231531Z/large/src/native_adapter.py:85` `Runtime.probe`) is
   hard-wired to one sequence. It asserts `pos == n-1`, `int(mask.sum()) == n` (so no padding), and
   on the first formal request asserts the LM-head input shape is exactly `[[1,1,4096]]`. Its frozen
   `probe_ids_sha256` is taken over a `(1, n)` tensor. Batching changes all four.

2. **The action** goes through the vendor runtime `runner.request(row, action)`
   (`P2_10_20260911T122423Z/runtime.py:69`), which takes **one row**. All three paths are single-row:
   `receiver_only` calls `receiver_prompt_tensors(tokenizer, example: dict, device)`
   (`protocol_min.py:243`, a single example); `text` calls `self.th.run(row)` then
   `self.tr.consume(row, ...)`; `c2c` calls `self.ch.run(row)`, `cache_to_stacked(...)`,
   `self.cr.prepare_base(row)`, `self.cr.fuse_and_generate(base, cache)`.

3. **The C2C fuser** (`P2_10_20260911T122423Z/legacy_methods.py:465` `fuse_and_generate`) is the
   binding constraint. `instruction_length` is a **scalar** used to slice
   `source_key[:, :, :instruction_length, :]`; the per-layer projector loop indexes
   `base[target_layer, 0].unsqueeze(0)` and unwraps `projected_key[0]`; and `receiver_kv_shape(
   instruction_length)` raises unless the KV tensor has the exact single-sequence shape. A routed
   group has a **different `instruction_length` per member**, so batching it means replacing the
   scalar slice with padded KV plus a per-row mask and changing the shape contract that
   `receiver_kv_shape` enforces.

A repo-wide search found no batched serving entry point: the only `batch_size` hits outside batch-1
serving are in **training** code (`runtime_source/rosetta/train/dataset_adapters.py`). The frozen
protocol note in `P2_10_20260911T122423Z/report_p2_10.py:46` records `batch1` as part of the
deployed implementation itself.

## Why I did not write it anyway

Two ground rules apply. "Make the smallest change that produces the result. Reuse the existing
replay driver" — there is nothing to reuse here; item 3 is a re-implementation of the official C2C
fuser. And "if anything is ambiguous, broken, or would need substantial new code, STOP and report
options." The budget is one debug job / 50 minutes; this is well past both.

There is also a correctness trap specific to the prereg's own check. Step 3b says that if more than
1 of 8 questions differ between the batch-8 and batch-1 paths, that is a reportable finding, because
"a batch-size-dependent output would mean the certification does not cover this implementation".
But padded batched attention does not reproduce unpadded single-sequence logits bit-for-bit, so a
freshly written batched path would **fail that check by construction**. The failure would be a
property of code written today, not of the deployed system, and reporting it as evidence about the
certification would be wrong.

## Options (need a decision)

1. **Report E12-a only.** The prereg already covers this: "If the job cannot run before the deadline
   below: the paper reports E12-a only, and Section 7 keeps the existing statement that latency is
   measured at batch size one." Costs nothing, changes no frozen text, and the reviewer's second
   gap is answered by an explicit scope statement rather than by data. Recommended given Sep 25.

2. **Batch only the `R` (receiver-only) and `T` (text) paths, and drop `large/MMLU-Pro/C2C`.**
   Those two paths are ordinary HF generate calls and could be batched with left padding in roughly
   one debug job. This keeps `large/OBQA/Text` (the largest-saving policy) and abandons the C2C
   policy, i.e. exactly the setting the prereg picked for being "not established". It also changes
   the prereg's chosen settings, so it needs an explicit amendment before running.

3. **Batch the full C2C path.** Correct but not a one-job task: a batched fuser, batched sharer, a
   padded-KV shape contract, and a re-certification that the batched path reproduces the frozen
   single-row outputs. Not feasible before Sep 25 and it touches certified code.

I did not start any of these. Option 1 needs no run; options 2 and 3 need an approved prereg
amendment first, since both change what the prereg fixed in advance.
