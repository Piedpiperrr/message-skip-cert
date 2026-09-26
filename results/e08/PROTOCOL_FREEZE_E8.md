# PROTOCOL_FREEZE_E8 — MMLU-Pro column for the SMALL and MEDIUM pairs

Stage: `$DATA_DIR/P2_R2_E8_20260920T012544Z`  
Written (UTC): **2026-09-20T01:38:26.858840+00:00** — before any new model output exists for this stage.  
Family: E8. Four settings: small/MMLU-Pro/Text, small/MMLU-Pro/C2C, medium/MMLU-Pro/Text, medium/MMLU-Pro/C2C.

## 1. Pre-registered protocol (verbatim)

> Settings: small/MMLU-Pro/Text, small/MMLU-Pro/C2C, medium/MMLU-Pro/Text, medium/MMLU-Pro/C2C. Everything is identical to the frozen
> large-pair MMLU-Pro protocol except the helper, receiver, and fuser of each pair: same population, groups, splits, prompts, generation
> limits (helper 256, receiver 64 tokens), greedy decoding, bf16/SDPA, batch 1, thinking disabled, frozen parser V2, INVALID handling,
> ProbeMax with the question’s own legal labels, 20 fit-quantile candidates (19 quantiles plus q=1), alpha=.05, per-candidate p<=.001,
> deploy the largest accepted q, otherwise fall back. The four settings form a separate 80-test family. All four are reported whatever
> their outcome. If a setting deploys, its policy is replayed end to end on the frozen 128-question MMLU-Pro panel on this hardware with
> the E3 protocol (fixed reference vs policy, rotated by question ordinal, no warmup, cold requests kept, versions (a) and (b)), and only
> its class is reported (not compared with the original hardware). Descriptive extras: development accuracy of R, Text, C2C; INVALID
> rates; the oracle over R/Text/C2C and its gain over the best fixed action and over R; stability over 200 re-drawn fit/calibration
> splits (hash-salt re-seeding as in E5); and labels under the earlier parser D1.

## 2. Models and fusers (the only scientific difference from the frozen large-pair run)

| pair | role | repo | revision | local path |
|---|---|---|---|---|
| small | helper | `Qwen/Qwen2.5-0.5B-Instruct` | `7ae557604adf67be50417f59c2c2f167def9a775` | `$DATA_DIR/c2c_reproduction_assets/models/Qwen--Qwen2.5-0.5B-Instruct` |
| small | receiver | `Qwen/Qwen3-0.6B` | `c1899de289a04d12100db370d81485cdf75e47ca` | `$DATA_DIR/c2c_reproduction_assets/models/Qwen--Qwen3-0.6B` |
| small | fuser | `nics-efc/C2C_Fuser` (`qwen3_0.6b+qwen2.5_0.5b_Fuser/final`) | `8704f555c6b4a60b764de7d755e6f1daf21a57ef` | `$DATA_DIR/c2c_reproduction_assets/fusers/nics-efc--C2C_Fuser/qwen3_0.6b+qwen2.5_0.5b_Fuser/final` |
| medium | helper | `Qwen/Qwen2.5-1.5B-Instruct` | `989aa7980e4cf806f80c7fef2b1adb7bc71aa306` | `$DATA_DIR/P2_MEDIUM_PAIR_BOUNDARY_EXTENSION_STAGE1_20260915T144407Z/execution_20260915T152640Z/assets/helper` |
| medium | receiver | `Qwen/Qwen3-1.7B` | `70d244cc86ccca08cf5af4e1e306ecf908b1ad5e` | `$DATA_DIR/P2_MEDIUM_PAIR_BOUNDARY_EXTENSION_STAGE1_20260915T144407Z/execution_20260915T152640Z/assets/receiver` |
| medium | fuser | `nics-efc/C2C_Fuser` (`qwen3_1.7b+qwen2.5_1.5b_Fuser/final`) | `f01fc3258b305e280e04c7238f4f2cf31b7dc70d` | `$DATA_DIR/P2_MEDIUM_PAIR_BOUNDARY_EXTENSION_STAGE1_20260915T144407Z/execution_20260915T152640Z/assets/fuser/qwen3_1.7b+qwen2.5_1.5b_Fuser/final` |

| pair | receiver layers | helper layers | projectors | projector_config mapping | fuser strict load |
|---|---|---|---|---|---|
| small | 28 | 24 | 28 | non-identity (24 source layers -> 28 projectors) | PASS, strict=True, 477848056 parameters |
| medium | 28 | 28 | 28 | identity i->(i,i) | PASS, strict=True, 485188088 parameters |

Login-node CPU feasibility receipt: `feasibility/CPU_FEASIBILITY.json`. Both fusers load for their own pair through the
MMLU-Pro runtime path (`legacy_methods.load_c2c_fusers`), with strict `load_state_dict`, finite weights, and the head-dim /
kv-head assertions of the official loader. For both receivers the frozen prefix `The correct answer is` encodes to
`[785, 4396, 4226, 374]` and every A–J label token set decodes back to its own label.
The derived generation configs are byte-identical to the frozen large-pair and medium-pair stage configs.

## 3. Unchanged from the frozen large-pair MMLU-Pro stage

- Population and splits: 12,032 MMLU-Pro test rows; fit/cal/dev = 3,093/3,000, 6,196/6,000, 2,743/2,641 rows/groups;
  smallest-ID representative per normalized question. Files copied byte-for-byte from `$DATA_DIR/P2_MMLU_PRO_BREADTH_STAGE1_20260916T002337Z/splits`.
- Queries: `$DATA_DIR/P2_MMLU_PRO_BREADTH_STAGE1_20260916T002337Z/inputs/queries_only.jsonl` (sha256 `a777b14d54e0773a0f3a7182ea8fde22c06f7111707aeefd51ea0cfda9a7fff6`), used through a symlink; no gold column is present in it.
- Prompts: `protocol/receiver_prompt.py` (sha256 `868a4760d92b123127b347a9e5e69dec2f00855d17e2eee0eec4876d7cb21c66`), dynamic A–J labels.
- Parser: frozen P2_SCORING_V2 2.0.0, `protocol/scoring_v2.py` (sha256 `d05978f400cf69aa6bddc56168a260ac3ea9158abaa640e9331602dc9bfcc2f9`).
- ProbeMax: `protocol/prefix_ids.json` (`ce218af11405dd5893ab42576be6829b89fc5ca3857c64b66337cb0d8f88418a`), `protocol/label_token_sets.json` (`6020e8383b77d175a0c9873113715c030570ff971f02f1387ca8a272041a5285`); ProbeMax over the question’s own K labels.
- Native C2C/Text implementation: `$DATA_DIR/P2_10_20260911T122423Z/runtime.py` (`a6888586a8bd5f13c62ccc17079f4bd86e34bfa1ada2d804a4d502dfec726514`), `$DATA_DIR/P2_10_20260911T122423Z/legacy_methods.py` (`91b03c146f56fe151dc399c4202411974afb61c4a195080cf8c54abd584bffdf`), `$DATA_DIR/P2_10_20260911T122423Z/protocol_min.py` (`23c702e16ff5b2bb164ab25ef4e35f4105ac81becb83747c138d222faab2cd35`).
- Risk rule and analysis: `$DATA_DIR/P2_MMLU_PRO_BREADTH_STAGE1_20260916T002337Z/src/risk.py` (`ff70ae8735a191e347a7d7117d3baadf591989fe73f172524aacbed3b2f371e7`) and `$DATA_DIR/P2_MMLU_PRO_BREADTH_STAGE1_20260916T002337Z/src/analyze.py` (`70500f66ae03cdbb968d7845625416f2046ba4d740e6802d28f51c711a691bb4`).
- Re-split stability: `$DATA_DIR/P2_R2_CPU_20260919T220412Z/scripts/e5b.py`; D1 parser: `$DATA_DIR/P2_SCORE_SENSITIVITY_20260912T055929Z/diagnostic_parser_v1.py`.
- E2E panel: `splits/candidate_e2e128_ids.json` (`0aff4667135fd51c63ecf0dc22099c1d36394537ba972ca7f51b11c5005a933d`), 128 frozen MMLU-Pro questions.

## 4. E8 code (hashes recorded before any new model output)

| file | sha256 |
|---|---|
| `protocol/receiver_prompt.py` | `868a4760d92b123127b347a9e5e69dec2f00855d17e2eee0eec4876d7cb21c66` |
| `protocol/scoring_v2.py` | `d05978f400cf69aa6bddc56168a260ac3ea9158abaa640e9331602dc9bfcc2f9` |
| `protocol/prefix_ids.json` | `ce218af11405dd5893ab42576be6829b89fc5ca3857c64b66337cb0d8f88418a` |
| `protocol/label_token_sets.json` | `6020e8383b77d175a0c9873113715c030570ff971f02f1387ca8a272041a5285` |
| `protocol/POPULATION_IDENTITY.json` | `808d33192af2bce65b4a1c04daa053f65a64e967f3e5aeab01334a3b9f552d85` |
| `protocol/QUERY_IDENTITIES.json` | `b2d32b3a896605a81228777c7b130ef48004616ddf33e2255cdcb2a08b544515` |
| `protocol/generation_configs_small.json` | `c81c48a34803a515a693d04f2523aa82a277b1e3960b583f4ebe81b3b5443d35` |
| `protocol/generation_configs_medium.json` | `c81c48a34803a515a693d04f2523aa82a277b1e3960b583f4ebe81b3b5443d35` |
| `MODEL_SOURCE_INDEX_small.json` | `e0070a3fac181c9a8ac9e662ef449fac53ffecd46233649e7fa12ed63f849b3c` |
| `MODEL_SOURCE_INDEX_medium.json` | `7912f0e799fe637b803061bde1815ce7ead19285927546d310126abcffba3798` |
| `splits/fit_ids.json` | `ed3e0862c7b2b50ab86e3c393d00db9553be3e309832381634a1527bea9c0852` |
| `splits/cal_ids.json` | `b49a9b9e1468382990fa292cb402f6a630bcf87c6db8365783b708b1b98b82a0` |
| `splits/dev_ids.json` | `040e556d520d94b1840712658e2fe8989e6103e3d3f891e1765c1e2145cd0707` |
| `splits/fit_groups.json` | `0a03684d33083a2a5b22914e0600ab3f3c1a92971853b775e2ffb5102df21cb6` |
| `splits/cal_groups.json` | `f6ecbfb4c2190b993c3f4888b061dd47d4d3809e028f880df5da9bfe8d89cbfa` |
| `splits/dev_groups.json` | `848be2786457c2aa169281a7f2fc33b95988b5f6753bd830085e5894882642cd` |
| `splits/candidate_e2e128_ids.json` | `0aff4667135fd51c63ecf0dc22099c1d36394537ba972ca7f51b11c5005a933d` |
| `splits/MANIFEST.json` | `a309f5d54f6c7478fcf5b9514ea4f8521e14b48175836a2f65d9bdfd8dccb6cc` |
| `splits/E8_LANES.json` | `7787d691c3f1df356c72b47366b17d2bbe62f32ceb6fff803c90a7e28180c28f` |
| `src/common_e8.py` | `3fe1626d47c402484c2c3c3c37ccf487e3018522e337330c27a03b0ffc260587` |
| `src/native_runtime_e8.py` | `bf95d37148db6ead74bd241637cdb495fe307c7e1d85145f1fc56ded492c5766` |
| `src/execute_e8.py` | `7486e2bda08129d10f0e4a3b76a061083bf9ee473762f883ce85611aadb3a213` |
| `src/validate_smoke.py` | `d82978cd93550f94ee52cc7365c550752c2ccdf6d7773a5bdf8df5fb6c808653` |
| `src/feasibility_cpu.py` | `75155d4c1f386f0847b505e2cd1b1317d59020e761a23dbd25b6452c942ce326` |
| `src/budget_estimate.py` | `c757f8202832246f29f283dd60415a2a85eba70dda28902843dc629b8a197ea5` |
| `src/slot.sh` | `c1c5a556ad000ef0841e0f62584b2dcf950b100e43e9e48d3a3b74c6aac8f2e3` |
| `src/slot_validate.sh` | `15b332dda4ad84faa20da19447b433ebb0c87818e09f7cc2bc2a8ab2c7b66e42` |
| `run_validate.pbs` | `fb675bbcdaa90e4e22a0dcfa71ed77f423cbba36319252d31243cf847306f302` |
| `run_main.pbs` | `28cb2c8d6373bdd7514c2a4aca5a17f4c0755983b0ec83892b9a9b0ac3330af9` |

External sources this stage reads but never modifies are hashed in `FREEZE_INDEX_E8.json`.

## 5. Execution plan and its one deviation from the Stage1 executor

ClusterA debug queue only: `-q debug -l select<=2 -l walltime<=00:50:00 -l fsreq=<fs>`, 4x A100 40GB per node,
one run per GPU pair (helper on the first visible GPU, receiver + fuser on the second), at most one running and one queued job.

**Deviation, recorded in advance.** The frozen Stage1 executor ran one shard to completion in a single 14 h ClusterB job and forbade
resumption. A 12,032-row pair cannot fit in a 50-minute debug job, so the work order is frozen into 16 contiguous lanes per pair
(`splits/E8_LANES.json`, order sha256 `8b48f395e05f33b809bf7c4871257125ea5df3a3efa7a2e761cc92912deb7f81`), a slot claims a lane
with an exclusive lock, and a lane may be resumed by a later job. The scientific invariant is preserved: every
`(pair, split, id, action)` key is written at most once, no key is recomputed once it has a record, decoding is greedy so no
re-execution can change a recorded outcome, and any runtime error is fatal and is not retried. Lane boundaries carry no
scientific meaning; requests are independent and the runtime asserts no cross-request KV reuse.

## 6. Budget, recorded before submission

Estimated from the two prescribed logs (`feasibility/GPU_HOUR_ESTIMATE.json`): the large-pair MMLU-Pro Stage1 run
(2.0539 s/row over 12032 rows, 13.90 allocated GPU-h) and the medium-pair OBQA/ARC run
(0.4116 s/request over 22504 requests, 5.23 allocated GPU-h), rescaled per action by the cross-pair timing table measured on the same OBQA/ARC rows.

| pair | projected s/row | projected pair-wall h | productive GPU-h (2 GPUs) |
|---|---|---|---|
| small | 2.157 | 7.21 | 14.419 |
| medium | 1.967 | 6.575 | 13.151 |
| **both** | | **13.785** | **27.57** |

At `select=2` (4 GPU pairs per job) this is **5 main debug jobs**;
counted as every GPU in the reservation times the 00:50:00 cap that is **33.33 allocated GPU-h**.
The stop rule for this stage is: >30 GPU-h or >6 debug jobs on the refined estimate means do not submit the main runs and report instead.
The refined estimate uses the measured seconds/row from the authorized validation+smoke job.

## 7. Reporting commitments

- All four settings are reported whatever their outcome; the family is 4 settings x 20 candidates = 80 tests, separate from every earlier family.
- Gold is opened only after the deployment configuration of every setting is written.
- Smoke and validation read no gold; validation compares only model outputs and ProbeMax values.
- Deadline: work that cannot finish by 2026-09-21 20:00 CDT (2026-09-22T01:00Z) is stopped and reported as unfinished.

