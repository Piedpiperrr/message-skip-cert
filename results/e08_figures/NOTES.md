# P2_R2_FIG_E8: Figure 2 redrawn after E8 — the four MMLU-Pro cells stop being "not evaluated"

Login node, CPU only; c2c_official env (matplotlib, pdf.fonttype 42). No existing P2_* folder or
frozen result file was modified; this stage only reads `P2_R2_FIG_20260919T233556Z` and the E8
deployment file. No queue submission.

## Base

- Script: `P2_R2_FIG_20260919T233556Z/figure2_source/make_figure2_boundary.py` — the version with the
  sealed-test bracket, the medium/OBQA/C2C asterisk and the large/OBQA/Text double dagger.
  Copied unchanged to `base_r2/figure2_source/`.
- Base PDF copied to `base_r2/paper_active/figures/` and used as the pixel-diff reference.

## Result source

`P2_R2_E8_20260920T012544Z/analysis/deployments/deployment_configs.json`: all four E8 settings
fall back (q = 0), 0 of 80 calibration tests accepted. Re-split certification rate 0.000 over 200
seeds for each, so the fallback is not a borderline artefact.

## Changes (exactly four) — `diffs/make_figure2_boundary.diff`

1. **Docstring provenance.** The `not evaluated` line is replaced by an `E8` line naming the
   deployment file and the 0/80 outcome. No rendering effect.
2. **small row.** cells `[F, F, F, F, NE, NE]` -> `[F, F, F, F, F, F]`; count `"0/4"` -> `"0/4 + 0/2"`.
3. **medium row.** cells `[F, POS, F, POS, NE, NE]` -> `[F, POS, F, POS, F, F]`;
   count `"2/4"` -> `"2/4 + 0/2"`.
4. **large row count and legend.** count `"6/6"` -> `"4/4 + 2/2"`; the legend entry
   `("ne", "not evaluated")` is dropped, leaving four entries that the existing width-measuring
   layout re-centres on its own.

The `NE` constant and its drawing branch are left in place but are now unreachable. Geometry
constants, colours, fonts, badge and check-mark drawing, the dagger and asterisk blocks, the
sealed-test bracket, the page size (396 x 108 pt) and the `savefig` calls are unchanged.

## Note on the large-row count

The request described the column as currently reading `0/4, 2/4, 4/4 + 2/2` and asked for
`4/4 + 2/2` on the large row. The R2 stage had changed that label from `"4/4 + 2/2"` to `"6/6"` on
2026-09-19 (its change 1). This stage restores `"4/4 + 2/2"` as requested, which reverts that R2
change. Flagged to Work; a one-word edit returns it to `"6/6"` if that was not intended.

## Checks

- `figure2_source/check_figure2_e8.py` -> `CHECK_figure2_e8.json`: all 18 cells verified against the
  truth table supplied with the request, including which cell carries the dagger and which the
  asterisk; deployed labels; legend contents; PDF text layer; page size. **STATUS PASS**, 0 failures.
  10 fallback cells, 8 deploy cells, 0 "not evaluated".
- `PIXELDIFF_e8.json`: 600 dpi rasters of base and new, 8.22% of pixels changed, confined to three
  regions — the four MMLU-Pro cells (x 3.43-4.45 in), the legend row (re-centred), and the three
  deployed-count labels. Nothing else on the page differs.

## Files

- `paper_active/figures/figure2_boundary.pdf` — 396 x 108 pt, same as the base
- `paper_active/figures/figure2_boundary.png` — 300 dpi
- `figure2_source/figure2_boundary_600dpi.png` — 600 dpi
- `figure2_boundary_preview_200dpi.png`, `base_preview_200dpi.png` — side-by-side checking previews
