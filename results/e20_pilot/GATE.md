# GATE.md — E20-pilot Step 0 (login node; no model weights)

Written 2026-09-21T23:27:49.336935+00:00. Stage: P2_R8_E20P_20260921T224653Z. No gold answer column was read (pyarrow column projection; notes/POOL_E20P.json lists the columns read).

## G1 — datasets, revisions, split sizes (all 4 available; none dropped)

| dataset | HF repo | config | split | revision (HF commit) | raw rows | after subset | after <=300-word filter | pool after dedup | pilot | reserve for full run |
|---|---|---|---|---|---|---|---|---|---|---|
| SQuAD | rajpurkar/squad | plain_text | train | `7b6d24c440a36b6815f21b70d25016731768db1f` | 87,599 | — | 87038 | 86,830 | 400 | 86,430 |
| NQ-passage | mrqa-workshop/mrqa | plain_text, subset == NaturalQuestionsShort | train | `f3178d9888471dfb2b67c93de14f0ddf499a8d9f` | 516,819 | 104071 | 98413 | 98,071 | 400 | 97,671 |
| TriviaQA | mandarjoshi/trivia_qa | rc.nocontext | train | `0f7faf33a3908546c6fd5b73a660e0f8ff173c2f` | 138,384 | — | n/a (closed-book) | 76,341 | 400 | 75,941 |
| NQ-Open | google-research-datasets/nq_open | nq_open | train | `5dd9790a83002ad084ddeb7c420dc716852c6f28` | 87,925 | — | n/a (closed-book) | 87,145 | 400 | 86,745 |

Train parquet files and SHA-256: notes/DOWNLOAD_MANIFEST.json (downloaded with the the-cluster proxy via huggingface_hub, pinned revisions).

Notes: TriviaQA rc.nocontext train has 138,384 rows but 76,523 distinct question_id values (repeated ids); removing duplicates by normalized
question text (first copy in SHA order, ties by file row) removes 62,043 rows. MRQA markup: all 26 markup token types present in the
NaturalQuestionsShort contexts are standalone whitespace-separated tags (<Td>, <Tr>, <P>, <Table>, <Li>, <Ul>, <Th>, <Dd>, <Dt>, <Dl>, <Ol>, <H2>, <H3>
and closing forms; 0 tags attached to words); they are removed before counting and prompting. Pilot passage lengths: SQuAD 27-282 words,
NQ-passage 2-299 words.

## G2 — pool order and pilot files (hashes)

| file | SHA-256 |
|---|---|
| inputs/POOL_ORDER_squad.txt | `9754449546d370e2ab7c690ee99f44a50c240230850574f195f596664ffab7f3` |
| inputs/PILOT_squad.jsonl | `bcf2b0e2de5756a179893d7e4b711a667006007321842f325ac47b4d43937d9d` |
| inputs/POOL_ORDER_nqp.txt | `ba6525fb9dd6693cfc88f3497dc300db10749e4e50d7b4e292121f04a5888036` |
| inputs/PILOT_nqp.jsonl | `eddf08f0701f08ca3fbcc08455a36273ab0fd251c4dd992ff03dc7884292088b` |
| inputs/POOL_ORDER_triviaqa.txt | `3457e6978a7942344299c30859679c2103cf906b522790622a6e304386534b7e` |
| inputs/PILOT_triviaqa.jsonl | `fb0fe5a72f53f3bb38277380264c29387bb009abe7d3b6d0fe4a683af29f0a84` |
| inputs/POOL_ORDER_nqopen.txt | `f7ec7dfca52f2443f704a822dec14fb2690c841782fee1fe9d7190840558e6bf` |
| inputs/PILOT_nqopen.jsonl | `7cc1e18170835e8789a9583a7dd056a3e637af421882cfcbcceafb0f48394a91` |

Rule (src/e20_pool.py): id = dataset id field (SQuAD id, MRQA qid, TriviaQA question_id; NQ-Open: SHA-256 of the raw question string);
order = SHA-256 of "<dataset>|<id>" with dataset in {SQuAD, NQ-passage, TriviaQA, NQ-Open}; dedup by normalized question (passage datasets:
(passage, normalized question)); pilot = first 400. Pilot files hold only id, question (stripped), passage (null for closed-book). The jobs
read only these files. Full run continues the same order: next 500 = fit, next N_cal = calibration, next 1,000 = dev.

## G4 — prompts

PROMPTS_E20.md SHA-256 `6ed439e8c320c9c9bb62bb3fad969564219168976f134db7e3199db674c6814e`; source src/e20_prompts.py `c4b0be5dea890f56ed4a86f820045775743504556cb22b6f332b760f50c0c900`.

Checks on all 1,600 pilot prompts (notes/PROMPT_CHECKS.json): tokenizer(rendered, add_special_tokens=False) == apply_chat_template(tokenize=True)
for helper, receiver-only and receiver-with-message of both receivers (all true); BOS count Llama = 1, Qwen = 0 (no double BOS).

| dataset | helper prompt tokens median/max | Qwen3 R median/max | Llama R median/max |
|---|---|---|---|
| squad | 226.5/476 | 240.5/490 | 258.0/478 |
| nqp | 191.0/1215 | 205.0/1229 | 224.0/807 |
| triviaqa | 73.0/164 | 94.0/185 | 116.0/203 |
| nqopen | 68.0/78 | 89.0/99 | 112.0/121 |

## Dry run of the job data path (no weights) — PASS

notes/dryrun/ (all outputs there are FAKE; stub models return fixed strings and random logits). Exercised: code-path imports of the frozen
P2_10 modules, pilot loading, 8-rank question sharding for jobs A and B, real tokenizers and chat templates for helper/Qwen3/Llama, rank-0
preflight code paths (stored OBQA and X3 rows loaded and compared; mismatches expected with stubs), smoke + GATE.json + projection, job-B
preflight-skip path, float64 per-position log-prob / 1-max p computation from logits, extraction, s1/s2/s3, per-rank row writing with fsync,
merge + OUTPUTS_HASH, Step 4-5 analysis and selection on synthetic rows (bootstrap, frozen E17-5 binormal, bisection, ranking, N_cal), and
Step 6 accuracy on synthetic gold parquets (checked against an independent recomputation; a guard refuses the real gold files in dry-run mode).
Extractor/score sanity cases: notes/EXTRACTOR_SANITY.txt (14/14 extraction cases, score spans as specified).

Time projection basis: E10 on ClusterA measured ~31 decode tokens/s (Qwen3-8B, bf16, batch 1); worst case per rank (100 questions, 256
helper + 4 x 32 receiver tokens each) is ~21 min of decoding plus loads and the rank-0 gate (~5-8 min), under the 45-min limit.
