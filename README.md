# Safe to Omit, Worth Omitting? — code and records

Anonymous code and records for the ICLR 2027 submission "Safe to Omit, Worth Omitting? Keeping
the Answer and Cutting Latency When an LLM Agent Skips Another's Message". Authors are anonymous
for double-blind review.

## What the paper does

A helper LLM agent sends one message to a receiver LLM agent before the receiver answers a
question. The message is either natural-language text (Text: the helper writes up to 256 tokens
of background knowledge) or a latent projection of the helper's key-value cache into the receiver
(Cache-to-Cache, C2C, with the official pretrained fusers). A policy skips the message when the
receiver's own confidence is high: one receiver prefill gives u = 1 - (largest label probability)
(the ProbeMax score), and the message is skipped when u <= tau.

The threshold tau is certified in the Learn-then-Test style: 20 candidate thresholds are
fit-split quantiles of u, and each is tested on a separate calibration split with an exact
one-sided binomial test of H0: rho >= 0.05, where rho is the share of skipped questions whose
answer differs from the deployed system's answer (per-candidate level delta = 0.001, 0.02 per
setting by Bonferroni). If no candidate passes, the system falls back to always sending the
message. The paper then asks whether skipping is worth it (end-to-end latency at batch size one)
and tests the frozen policies on sealed or held-out questions.

Models (verified against [configs/model_identities.json](configs/model_identities.json) and the
medium-pair freeze): three Qwen helper -> receiver pairs — small Qwen2.5-0.5B-Instruct ->
Qwen3-0.6B, medium Qwen2.5-1.5B-Instruct -> Qwen3-1.7B, large Qwen2.5-7B-Instruct -> Qwen3-8B —
plus cross-family settings with an OLMo-2-1124-7B-Instruct receiver, a Llama-3.2-1B-Instruct
helper, and a Llama-3.1-8B-Instruct receiver. The C2C fusers are the official `nics-efc/C2C_Fuser`
checkpoints. Benchmarks: OpenBookQA, ARC-Challenge, MMLU-Pro, SQuAD and GSM8K. The SQuAD setting comes from
a label-free pilot over eight candidates — SQuAD and Natural Questions with passages
(`SQuAD`, `NQ-passage`), TriviaQA and NQ-Open closed-book (`TriviaQA`, `NQ-Open`), each with a
Qwen3-8B and a Llama-3.1-8B receiver, all eight in
[results/e20_pilot/PILOT_STATS.csv](results/e20_pilot/PILOT_STATS.csv). The rule selected SQuAD
with the Llama-3.1-8B receiver, and only that setting was run in full
([results/e20_full/](results/e20_full/)).

## One-minute check (CPU)

Tested on this login node in a fresh virtual environment:

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
bash verify/run_all.sh
```

Expected output (also in [verify/EXPECTED_OUTPUT.txt](verify/EXPECTED_OUTPUT.txt)):

- the certification test reproduces the deployed thresholds q = 0.80 (large/OBQA/Text),
  0.95 (large/ARC/Text) and 0.55 (medium/OBQA/C2C) from the released calibration records;
- the rate-matched null ratio for large/OBQA/Text is 0.547 (Appendix F);
- Table 2, row large/ARC/Text: 284 of 299 development questions skipped (95.0%), 9 of 284 changed.

Measured wall time for all three checks: **1.0 second** (Python 3.11.15, numpy 2.2.6,
scipy 1.15.3). The checks read only files in this repository; no GPU and no downloads.

## Repository layout

| folder | what it holds | size |
|---|---|---|
| [code/](code/) | the frozen pipeline (`code/pipeline/`), the per-experiment analysis scripts (`code/analysis/`), the figure scripts (`code/figures/`; Figures 3–11 in `code/figures/appendix/`) and the dataset downloader (`code/data/`) | 7.5 MB |
| [configs/](configs/) | frozen configurations: thresholds, the 20-point q grid, seeds, alpha and delta, probe protocol and chat templates, model revisions and checkpoint hashes | 0.7 MB |
| [splits/](splits/) | question IDs per split and benchmark, group members, representatives | 0.9 MB |
| [records/](records/) | per-question records: answers (parsed and raw), ProbeMax scores, routes, per-request timings, calibration ledgers | 184.7 MB |
| [results/](results/) | one folder per experiment: PREREG, SUMMARY, DEVIATIONS, CSV/JSON results, CERT and MANIFEST files | 49.2 MB |
| [figures/](figures/) | Figure 2 and the nine appendix figures (Figures 3–11), regenerated from data by `code/figures/fig2_boundary.py` and `code/figures/appendix/run_all.sh` | 0.2 MB |
| [verify/](verify/) | the three CPU checks and their expected output | 24 KB |
| [docs/](docs/) | the full paper map, the details the appendix leaves out, and the full record list | 36 KB |
| [third_party/](third_party/) | code the authors did not write, under its own licence | 28 KB |

Large `.jsonl`, `.csv` and array files are gzipped in place (`*.gz`); every reader in this
repository opens both forms. Experiment folders use the authors' internal IDs (E3 … E22,
X1 … X4); the paper map below links them to the paper.

## Paper map

Full table, every element: [docs/PAPER_MAP.md](docs/PAPER_MAP.md). Main text and the appendices
a reviewer is most likely to check:

| paper element | what it shows | results folder(s) | script | CPU time |
|---|---|---|---|---|
| Fig. 1 | schematic of message skipping | — | — | no data |
| Table 1 | oracle headroom and the rate-matched null | [results/e09a/](results/e09a/), [results/e22/](results/e22/) | `code/analysis/e09a/scripts/e9a_main.py`, `code/analysis/e22/scripts/e22_1.py` | not re-run in this release |
| Fig. 2 | certification boundary over all settings | — (values transcribed from Tables 4 and 7 and Appendices G.2–G.3) | [code/figures/fig2_boundary.py](code/figures/fig2_boundary.py) | ~1 s |
| Table 2 | every deployed policy: skipped share, changes, level, delta-accuracy, G, kept, saving | [results/frozen_pipeline/](results/frozen_pipeline/), [results/sealed_arc_test/](results/sealed_arc_test/), [results/e09b_e09c/](results/e09b_e09c/), [results/e16/](results/e16/), [results/e20_full/](results/e20_full/), [results/e21/](results/e21/) | `code/pipeline/confidence_boundaries/analyze.py`, `code/pipeline/dev_e2e_replay/analyze.py` | one row re-derived by `verify/verify_c_table2_row.py`, <1 s |
| App. F, Tables 13–15, Figs. 7–8 | matched null and rate-matched null | [results/e09a/](results/e09a/), [results/e22/](results/e22/) | `code/analysis/e22/scripts/e22_1.py`, `e22_2.py` | ratio re-derived by `verify/verify_b_e22_ratio.py`, <1 s |
| App. C, Tables 4–8, Figs. 3–4 | development boundary, calibration statistics, same-target baselines, post-hoc variants, MMLU-Pro | [results/frozen_pipeline/confidence_boundaries/](results/frozen_pipeline/confidence_boundaries/), [results/e13/](results/e13/), [results/e08/](results/e08/), [results/mmlu_pro_breadth/](results/mmlu_pro_breadth/) | `code/pipeline/confidence_boundaries/analyze.py` | three settings of Table 5 re-derived by `verify/verify_a_certification.py`, <1 s |
| App. E, Tables 10–12, Fig. 6 | gain retention; lost corrections; label-light certificate | [results/e13/](results/e13/), [results/e21/](results/e21/) | `code/analysis/e13/scripts/`, `code/analysis/e21/scripts/` | not re-run in this release |
| App. H, Tables 18–22, Fig. 9 | latency replays, busy-GPU time, repeats, reuse, panel check | [results/frozen_pipeline/dev_e2e_replay/](results/frozen_pipeline/dev_e2e_replay/), [results/e15/](results/e15/), [results/e03_repeat1/](results/e03_repeat1/), [results/e07/](results/e07/) | `code/pipeline/dev_e2e_replay/analyze.py`, `code/analysis/e15/scripts/e15_2.py` | not re-run in this release (GPU replay) |
| App. I, Tables 23–25, Fig. 10 | held-out OBQA, later out-of-sample tests, option rotation, sealed ARC | [results/e09b_e09c/](results/e09b_e09c/), [results/e16/](results/e16/), [results/e21b/](results/e21b/), [results/sealed_arc_test/](results/sealed_arc_test/) | `code/analysis/e16/src/analyze_e16_oos.py`, `code/pipeline/sealed_arc_confirmation/analyze.py` | not re-run in this release |

Figures 3–11 are regenerated, with every plotted number checked against the paper and the records,
by `bash code/figures/appendix/run_all.sh` (CPU, about 45 s). Details that the appendix leaves out
for length are listed with their records in [docs/APPENDIX_DETAILS.md](docs/APPENDIX_DETAILS.md).

## Where the records the paper cites are

Full list with a path for every item: [docs/RECORDS.md](docs/RECORDS.md). In short:

- **Calibration**: every prespecified grid test of every setting, including rejected thresholds
  and fallback settings, with routed *n*, changed *k*, exact binomial *p* and the
  Clopper-Pearson 0.999 upper bound — 860 ledger rows, 820 distinct tests
  ([results/frozen_pipeline/confidence_boundaries/calibration_all_160.csv](results/frozen_pipeline/confidence_boundaries/calibration_all_160.csv)
  and the per-stage ledgers).
- **Splits**: OBQA fit 2,100 / calibration 1,366 / development 742, ARC 670 / 448 / 299, and the
  MMLU-Pro, sealed-ARC and timing-panel IDs, in [splits/](splits/).
- **Identities**: model and tokenizer revisions, checkpoint hashes, label-token sets, prefix and
  template hashes, first-request checks, in [configs/](configs/).
- **Per question**: ProbeMax scores and routes, receiver-only / Text / C2C answers (parsed labels
  and raw text), per-request timings and hash manifests, in [records/](records/).
- **Prompts and parser**: [results/e13/PROMPTS_AND_PARSER.md](results/e13/PROMPTS_AND_PARSER.md).

## Reproducing from stored records (CPU)

The pattern is one analysis script per experiment folder, reading that experiment's records and
writing the CSV/JSON in its `results/`. The three scripts in [verify/](verify/) are the worked
examples: each is self-contained, states its inputs at the top, and re-derives a published number
from the released records alone.

Worked example that was run for this release — recompute the deployed thresholds from the
calibration ledgers and compare them with the frozen deployments:

```bash
python3 verify/verify_a_certification.py
```

It reads [configs/confidence_boundaries/frozen_config.json](configs/confidence_boundaries/frozen_config.json)
for alpha and the cutoff, the per-setting `*_tests.csv` ledgers and the medium-pair ledger, applies
the exact binomial test to each of the 20 candidates, takes the largest accepted q, and checks it
against the stored deployment. It prints `PASS` for all three settings and also reports that the
recomputed accept/reject flags agree with the stored ones on 20/20 candidates per setting.

The per-experiment analysis scripts are reproduced as they were run: their path constants at the
top of each `common*.py` point at the original multi-stage layout, not at this repository. The
`verify/` scripts show how to feed the released records to those same unmodified analysis classes
(`verify_b_e22_ratio.py` imports E9-a's own `Inst` class rather than reimplementing the null model).

## Rerunning the experiments (GPU)

**None of this section was re-run in this release**: the machine used to build it is a login node
with no GPU. The commands are the ones the stages record.

- **Models.** Public Hugging Face IDs with pinned revisions are in
  [configs/model_identities.json](configs/model_identities.json) (small and large pairs) and in
  the medium-pair freeze under
  [results/boundaries_medium/](results/boundaries_medium/); checkpoint file hashes are in
  [configs/integrity/model_checkpoints/](configs/integrity/model_checkpoints/). The official C2C
  fusers are `nics-efc/C2C_Fuser` (subfolders `qwen3_8b+qwen2.5_7b_Fuser/final`,
  `qwen3_1.7b+qwen2.5_1.5b_Fuser/final`, `qwen3_0.6b+qwen2.5_0.5b_Fuser/final`). Weights are not
  redistributed here.
- **Datasets.** No question text is redistributed. Fetch the public datasets at the pinned
  revisions in [configs/dataset_identities.json](configs/dataset_identities.json) and rebuild the
  text for the released split IDs:

  ```bash
  python3 code/data/prepare_datasets.py --out $DATA_DIR --revision-from-config
  ```

- **Pipeline order.** (1) helper messages for Text and the C2C fusion, (2) receiver answers for
  receiver-only, Text and C2C on the fit, calibration and development splits, (3) ProbeMax scores
  from one receiver prefill per question, (4) certification and fallback over the 20-candidate
  grid, (5) end-to-end latency replays on two A100 40GB GPUs at batch size one, with the policy
  interleaved with its fixed reference. The driver for each stage is the `run_*.py` / `execute.py`
  in that experiment's `code/analysis/<experiment>/` or in `code/pipeline/`; the exact arguments
  are recorded in each stage's `PREREG.md` and `SUMMARY.md`.
- **Software.** Python 3.10.18, torch 2.6.0, transformers 4.52.4, tokenizers 0.21.4,
  safetensors 0.8.0, and the CPU packages pinned in [requirements.txt](requirements.txt)
  (numpy 2.2.6, scipy 1.15.3, matplotlib 3.10.5). `requirements.txt` lists only what the released
  code imports; torch and transformers are needed only to regenerate model outputs.

## Protocols and provenance

Each `results/<experiment>/` folder holds a `PREREG.md` with a `PREREG.sha256` (the protocol,
hashed before the outputs it covers), a `SUMMARY.md`, a `DEVIATIONS.md` and a manifest of file
hashes. Appendix B (Table 3) of the paper states, for every part of the evidence, when its
protocol was fixed and whether the data were development, held out or sealed.

Anonymization replaced paths, user names and cluster-specific names (scheduler queue and
resource names, a CPU model) inside some files; where such a file has a stored SHA-256 value,
that value no longer matches the released copy; `verify/check_hashes.py` lists which files verify,
which were altered by anonymization, and which were not shipped. The counts are in
[docs/CHECKSUMS.md](docs/CHECKSUMS.md). The unanonymized originals will be released with the
camera-ready version.

Both commands below were run for this release:

```bash
python3 verify/check_hashes.py     # add --list-altered to see the altered files

# one protocol on its own (each .sha256 ends with a 'hashed_utc:' line, so select the hash line):
cd results/e15 && grep -E '^[0-9a-f]{64} ' PREREG_E15.sha256 | sha256sum -c -   # PREREG_E15.md: OK
```

## What is not included

- Model weights and tokenizer payloads (fetch them at the pinned revisions).
- Full-vocabulary logits — the records keep only the renormalised distribution over each
  question's legal option labels.
- Benchmark question text (public datasets; the split IDs and the downloader are here instead).
- Hidden-state feature vectors used to train the learned control (600 MB).
- Scheduler job records, run logs, caches, core dumps and intermediate work files.
- One item the paper cites is **not** a file in this repository: the AUROC pattern behind the
  small-sample check was first stated in the authors' manuscript draft, not in a stage. What is
  here is the E13 item-4 output that records the later result files' timestamps and fixes the
  0.80 cut in its hashed protocol — see [docs/RECORDS.md](docs/RECORDS.md), item 8.

All 460 tests ever run on the 1,366 large/OBQA/Text calibration questions are included: the
declared family of 100 (60 new — ProbeMax, ProbeEntropy, WordD — and 40 reused — D, R) in
[results/zero_gold_controls/](results/zero_gold_controls/), the earlier screen's other 60
(Diff, H, Random) in [results/historical_large_obqa_screen/](results/historical_large_obqa_screen/),
and the 300 correctness-trained heads under label budgets (R32/R128/R512 x r0-r4) in
[results/historical_large_obqa_gold_budget/](results/historical_large_obqa_gold_budget/). The
screen's `README.md` sets the three parts side by side.

## Answer parser and prompts

Every prompt template and the answer parser are given verbatim in Appendix L of the paper and in
[results/e13/PROMPTS_AND_PARSER.md](results/e13/PROMPTS_AND_PARSER.md); the parser file is
[code/pipeline/answer_scoring_v2/scoring_v2.py](code/pipeline/answer_scoring_v2/scoring_v2.py)
(SHA-256 `d05978f400cf69aa6bddc56168a260ac3ea9158abaa640e9331602dc9bfcc2f9`).

## License

MIT for the authors' code ([LICENSE](LICENSE)). Third-party code keeps its own license:

| folder | source project | license |
|---|---|---|
| [third_party/official_c2c_rosetta/](third_party/official_c2c_rosetta/) — vendored at `code/pipeline/native_action_runtime/runtime_source/rosetta/` and in the sealed-test snapshot | the official Cache-to-Cache project, commit `113c3a9` | Apache-2.0 |

Benchmark datasets and model weights are not redistributed.

## Citation

Anonymous authors. Safe to Omit, Worth Omitting? Keeping the Answer and Cutting Latency When an
LLM Agent Skips Another's Message. Under review at ICLR 2027. (No BibTeX with names during review.)
