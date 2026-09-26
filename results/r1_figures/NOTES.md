# P2_R1_FIG: Figure 2 with a double dagger on the large / OBQA / Text cell

Login node, CPU only; c2c_official env (matplotlib 3.10.5). No existing P2_* folder or record was modified.

## Source

- Script: `P2_STRENGTHEN_20260918T205058Z/v2/figure2_source/make_figure2_boundary.py` (sha256 a259fd90a02d686d46dbeb97e123fdff135de0424019f657fb64e71c5f3190e1); the STRENGTHEN v2 hotfix of the V6.1 script (only change there: legend "omission deployed").
- Current paper figure: `P2_STRENGTHEN_20260918T205058Z/v2/paper/figures/figure2_boundary.pdf` (sha256 46b939699d2b637ea0449f52697ec532f5763351c9fce305a6645fc01de10e60); the same file is `figures/figure2_boundary.pdf` in `P2_STRENGTHEN_20260918T205058Z/v2/delivery/P2_STRENGTHENED_SOURCE_V2.zip`.
- Reproduction: an unchanged copy of the script (`repro_original/`) regenerates that PDF byte for byte except the /CreationDate field.

## Change (one): `diffs/make_figure2_boundary.diff`

- After the "deploy" label of the large / OBQA / Text cell only: a superscript U+2021 (double dagger), white (the cell text color), STIXGeneral bold (same font as "deploy"),
  4.8 pt (0.7 x the 6.9 pt label); anchored to the label's own text box (annotate, xycoords = the label): 0.22 pt left of its right edge, baseline 3.7 pt above the label baseline.
- Every other element, position, size, font, color and the page size (396 x 108 pt) is unchanged.

## Checks (`CHECK_figure2_dagger.json`, from pdftoppm rasters of the original and new PDFs)

- 600 dpi full page: 234 changed pixels, all within x 1.467-1.497 in, y 0.537-0.593 in, inside the large / OBQA / Text cell.
- 2400 dpi: dagger ink clearance 1.15 pt to the white check-mark disc, 0.81 pt to the "deploy" ink, 2.21 pt to the cell top edge.
- Fonts embedded: STIXGeneral Regular / Bold / Italic, same as the original; no warnings at render time.

## Outputs and SHA-256

| file | sha256 |
|---|---|
| `figure2_source/make_figure2_boundary.py` | 91250c8c6013d8dd97929ad5832dfbcce66a1945ad987a6a1d97db00fded510e |
| `figure2_source/check_figure2_dagger.py` | 3d2596690f1139fb524fc8e2a13f15dde72c0f420008347bf06c270a146fc1dd |
| `diffs/make_figure2_boundary.diff` | ec76a1dcbf6dd6515daa5702187bcd1c15115abbda9db3f27514dba592960bf5 |
| `paper_active/figures/figure2_boundary.pdf` | d394e93e9f7b448270d9ed346780f5d8ec7936044b07c025a76ace632244f42d |
| `paper_active/figures/figure2_boundary.png` | b1f301755205f806b931dcb0dde403932f11dfd7c22a79707f015578e5110530 |
| `figure2_source/figure2_boundary_600dpi.png` | 8fa13dc704c6894f378feed7829917eefbdbcc234af841432320e0dcb397cf1d |
| `figure2_boundary_preview_200dpi.png` | f7a87bd9ab34e0efd0b174f497509e5adf78a34f46b5fe2a61aa1361058553e7 |
| `CHECK_figure2_dagger.json` | af92ecc700cb00be7b7d75edb76cf4fcaaf809811d31ec19047abf30d37c405c |
| `repro_original/figure2_source/make_figure2_boundary.py` | a259fd90a02d686d46dbeb97e123fdff135de0424019f657fb64e71c5f3190e1 |
| `repro_original/paper_active/figures/figure2_boundary.pdf` | 621b64d85309d0efd8df7f3a28131c5d74bc9a4a8c91269ea629fccc74283fde |
