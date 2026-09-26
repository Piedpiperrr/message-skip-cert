# Step 6 (latency replay) feasibility — written 2026-09-21 before any X3 model output

Rule (task): the replay is allowed only if the E3 driver can switch the receiver by model id + chat template and passes a 16-row check like Step 2.

E3 driver inspected: `P2_R1_E3POL_REPEAT1_20260919T075315Z/large/src/native_adapter.py` (Runtime.__init__, probe) with its frozen `large/protocol/*` and `frozen_config.json`.
- `Runtime.__init__` always builds the C2C bundles for the receiver: `C2CSharerHelperBundle` and `C2CReceiverSideFuserBundle`, with the Qwen3-8B+Qwen2.5-7B fuser from `cfg['fuser']`. That fuser has no counterpart for a Llama/Mistral receiver.
- It asserts the frozen Qwen3-8B receiver generation config, the chat-template SHA-256, the label-token sets (`protocol/label_token_sets.json`) and the prefix ids (`protocol/prefix_ids.json`).
- Its probe tokenizes with `tok(rendered)`, which would give Llama-3.1 and Mistral-v0.3 a double BOS (see DEVIATIONS D2).
Switching the receiver would therefore need code changes: remove the C2C/fuser construction, apply the BOS change in the probe, and regenerate the protocol files. That is more than model id + chat template.
**Assessment: Step 6 would not be run ("replay not run") even if an X3 setting deploys**, unless the requesters decide otherwise.
