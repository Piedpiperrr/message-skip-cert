# X4 results: large pair, Text reference, receiver answers sampled (T .7, top_p .8, top_k 20, min_p 0, rep. 1.0), OBQA + ARC

Sources:
- `src/analyze_x4.py` (2026-09-21) on `results/runs/chain_00..07.jsonl` (job 7642101). `MANIFEST.sha256` verified 16/16 first.
- Certification and all gold-free results were hashed in `CERT_HASHES.json` at 07:40:10.64Z; gold was decoded after (`X4_RESULTS.json`).
- Stored ProbeMax and frozen fit thresholds were used unchanged. `input_checks.csv`: greedy labels reproduce the paper's q .80 / .95 and dev u == 0 counts 354/742 and 217/299; seeds verified.

| setting | cal dis. | dev dis. sampled (greedy) | added dis. [boot95] | dev AUROC | q (cal k/n, p) | Min UCB | dev coverage | dev changed/omitted [CP95] |
|---|---|---|---|---|---|---|---|---|
| OBQA/Text sampled (nominal) | 137/1366 | 70/742 = .0943 (72 = .0970) | −.0027 [−.0094, +.0040] | .8672 | .80 (19/1064, 3.44e-8) | .0126 | 77.1% (572/742) | 19/572 = .0332 [.0201, .0514] |
| ARC/Text sampled | 13/448 | 14/299 = .0468 (15 = .0502) | −.0033 [−.0100, .0000] | .9561 | .95 (4/422, 4.80e-6) | .0202 | 95.0% (284/299) | 8/284 = .0282 [.0122, .0547] |

- **Ledger** (`certification_ledger_40.csv`): OBQA accepts q .05–.80; ARC accepts q .05–.95.
- **Sampled vs greedy labels on dev:**
  - R: 6/742 (OBQA), 0/299 (ARC).
  - Text: 2/742 (OBQA), 1/299 (ARC).
- **INVALID, sampled** (`invalid_sampled.csv`):
  - OBQA: R cal 3/1366, dev 0/742; Text cal 0/1366, dev 0/742.
  - ARC: 0 on both paths.
- **u == 0 split at the deployed q** (E14-2; `u0_split_E14_2.csv`, dev):
  - OBQA: 354/572 omitted have u = 0 (.619). k0/n0 = 2/354 [.0007, .0203]; k+/n+ = 17/218 [.0461, .1219].
  - ARC: 217/284 (.764). k0/n0 = 0/217 [0, .0169]; k+/n+ = 8/67 [.0530, .2218].
- **Re-splits, seeds 1–200** (`resplit.csv`): certification rate 1.00 / 1.00; agreement with X4's outcome 1.00 / 1.00; median q .80 / .90.
- **Dev accuracy** (`accuracy_per_split.csv`, gold last): sampled R 617/742 (.8315) and Text 646/742 (.8706) on OBQA; sampled R 268/299 (.8963) and Text 275/299 (.9197) on ARC.
