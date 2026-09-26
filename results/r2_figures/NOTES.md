# P2_R2_FIG: Figure 2, three label changes on top of the R1 double-dagger version

Login node, CPU only; c2c_official env (matplotlib 3.10.5, pdf.fonttype 42). No existing P2_* folder
or record was modified; this stage only reads `P2_R1_FIG_20260919T205809Z`.

## Base

- Script: `P2_R1_FIG_20260919T205809Z/figure2_source/make_figure2_boundary.py`
  (sha256 `91250c8c6013d8dd97929ad5832dfbcce66a1945ad987a6a1d97db00fded510e`) — the version **with** the
  double dagger on the large / OBQA / Text cell. Copied unchanged to `base_r1/figure2_source/`.
- Base PDF: `P2_R1_FIG_20260919T205809Z/paper_active/figures/figure2_boundary.pdf`
  (sha256 `d394e93e9f7b448270d9ed346780f5d8ec7936044b07c025a76ace632244f42d`), copied to
  `base_r1/paper_active/figures/` and used as the pixel-diff reference.

## Changes (exactly three) — `diffs/make_figure2_boundary.diff`

1. **Right-hand column labels.** `ROWS` line for the large pair: `"4/4 + 2/2"` -> `"6/6"`.
   The small and medium labels (`"0/4"`, `"2/4"`) are byte-identical to the base.
2. **Bracket label.** `"project-sealed confirmation"` -> `"sealed test"` (same call, same anchor
   `((xl+xr)/2, ys-0.08)`, same `fs=6.5`, same colour `INK`). The bracket rule itself is unchanged.
   The comment one line above was updated to match the new wording.
3. **New superscript asterisk.** A white `*` after the `"deploy"` label of the **medium / OBQA / C2C**
   cell, added by the same placement rule as the R1 dagger: `ax.annotate` anchored to the label's own
   text box (`xycoords=ax.texts[-1]`, `xy=(1, 0)`), `xytext=(-0.22, 5.14)` offset points,
   `ha="left"`, `va="baseline"`, `fontsize=4.8`, `color="white"`, `weight="bold"` — identical
   parameters to the dagger block, only the cell selector and the glyph differ.

Nothing else was touched: geometry constants, colours, fonts, badge and check-mark drawing, legend
layout, page size (396 x 108 pt) and the `savefig` calls are unchanged.

## Pixel-diff check — `CHECK_figure2_r2.json` (`figure2_source/check_figure2_r2.py`)

600 dpi rasters (pdftoppm) of the base and new PDFs, changed pixels grouped into connected
components, each cluster attributed to a region derived from the script's own geometry constants:

| region | clusters | changed px | x (in) | y (in) |
|---|---|---|---|---|
| A medium / OBQA / C2C cell (new asterisk) | 1 | 168 | 1.988-2.015 | 0.808-0.838 |
| B large-row "deployed" count label | 6 | 3518 | 4.582-4.980 | 0.485-0.565 |
| C bracket label under large / ARC | 23 | 8782 | 2.300-3.297 | 0.233-0.315 |
| **unattributed** | **0** | **0** | — | — |

`all_changes_inside_intended_regions = true`; total changed pixels 12468 of 2 970 000.

2400 dpi crop of the medium / OBQA / C2C cell: asterisk ink 1886 px, clearance 1.95 pt to the white
check-mark disc, 2.01 pt to the `"deploy"` ink, 2.21 pt to the cell top edge (the R1 dagger's
corresponding clearances were 1.15 / 0.81 / 2.21 pt). Render produced no warnings
(`render_stderr.txt` is empty); embedded fonts are STIXGeneral Regular / Bold / Italic as before.

## Outputs

`paper_active/figures/figure2_boundary.pdf` (the figure for the paper),
`paper_active/figures/figure2_boundary.png` (300 dpi), `figure2_boundary_preview_200dpi.png`
(200 dpi preview), `figure2_source/figure2_boundary_600dpi.png`, `diffs/make_figure2_boundary.diff`,
`CHECK_figure2_r2.json`, `zooms/` (600 dpi crops of the three changed regions).
SHA-256 of every file: `SHA256SUMS.txt`.
