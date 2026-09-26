"""QA for the R2 Figure 2 change: every changed pixel must lie in one of the three intended regions.

Regions are derived from the figure script's own geometry constants, not measured from the image:
  A  medium / OBQA / C2C cell            (the new white superscript asterisk)
  B  large-row "deployed" count label    ("4/4 + 2/2" -> "6/6")
  C  bracket label under large / ARC     ("project-sealed confirmation" -> "sealed test")
Changed pixels are grouped into connected components so each cluster can be attributed to one region.
usage: check_figure2_r2.py <full600_base.png> <full600_new.png> <cell2400_base.png> <cell2400_new.png> <out.json>
"""
import sys, json
import numpy as np
from PIL import Image
from scipy import ndimage
from scipy.spatial import cKDTree

W, H = 5.5, 1.50
X0, CW, RH, GAPX, PAD = 1.14, 0.52, 0.245, 0.10, 0.017
TOP = H - 0.37
cell_x = lambda j: X0 + j * CW + (j // 2) * GAPX
row_yb = lambda i: TOP - (i + 1) * RH
XC = cell_x(5) + CW + 0.12

ast_x, ast_yb = cell_x(1), row_yb(1)                       # medium row, OBQA/C2C cell
cnt_yc = row_yb(2) + RH / 2                                # large row centre
br_xl, br_xr = cell_x(2) + PAD, cell_x(3) + CW - PAD
br_y = row_yb(2) - 0.04 - 0.08                             # bracket label baseline-ish centre

REGIONS = {
    'A_medium_OBQA_C2C_cell': dict(x=[ast_x + PAD, ast_x + CW - PAD], y=[ast_yb + PAD, ast_yb + RH - PAD]),
    'B_large_row_count_label': dict(x=[XC - 0.03, XC + 0.75], y=[cnt_yc - 0.09, cnt_yc + 0.09]),
    'C_sealed_test_bracket_label': dict(x=[br_xl - 0.12, br_xr + 0.12], y=[br_y - 0.08, br_y + 0.08]),
}

load = lambda p: np.asarray(Image.open(p).convert('RGB')).astype(int)
a, b = load(sys.argv[1]), load(sys.argv[2])
assert a.shape == b.shape, (a.shape, b.shape)
D = 600
mask = np.abs(a - b).max(-1) > 0
lab, n = ndimage.label(mask, structure=np.ones((3, 3)))
clusters = []
for k in range(1, n + 1):
    ys, xs = np.nonzero(lab == k)
    box = dict(x_in=[xs.min() / D, (xs.max() + 1) / D],
               y_in=[H - (ys.max() + 1) / D, H - ys.min() / D], pixels=int(len(xs)))
    box['region'] = next((name for name, r in REGIONS.items()
                          if box['x_in'][0] >= r['x'][0] and box['x_in'][1] <= r['x'][1]
                          and box['y_in'][0] >= r['y'][0] and box['y_in'][1] <= r['y'][1]), None)
    clusters.append(box)
# merge clusters that belong to the same region for the summary
per_region = {}
for name in list(REGIONS) + ['UNATTRIBUTED']:
    cc = [c for c in clusters if (c['region'] or 'UNATTRIBUTED') == name]
    if cc:
        per_region[name] = dict(clusters=len(cc), pixels=sum(c['pixels'] for c in cc),
                                x_in=[min(c['x_in'][0] for c in cc), max(c['x_in'][1] for c in cc)],
                                y_in=[min(c['y_in'][0] for c in cc), max(c['y_in'][1] for c in cc)])

# asterisk geometry in the medium / OBQA / C2C cell, at 2400 dpi
A, B = load(sys.argv[3]), load(sys.argv[4])
D2, ox, oy = 2400, int(round((ast_x + PAD) * 2400)), int(round((H - (ast_yb + RH - PAD)) * 2400))
to_in = lambda r_, c_: ((c_ + ox + 0.5) / D2, H - (r_ + oy + 0.5) / D2)
rr, cc = np.nonzero(np.abs(A - B).max(-1) > 64)
dx, dy = to_in(rr, cc)
rr0, cc0 = np.nonzero(A.min(-1) > 128)
wx, wy = to_in(rr0, cc0)
cx, cy, r = ast_x + CW - 0.098, ast_yb + RH / 2, 0.058
cell = dict(left=ast_x + PAD, right=ast_x + CW - PAD, bottom=ast_yb + PAD, top=ast_yb + RH - PAD)
keep = (np.hypot(wx - cx, wy - cy) > r + 0.002) & (wx > cell['left']) & (wx < cell['right']) \
       & (wy > cell['bottom']) & (wy < cell['top'])
dep = cKDTree(np.c_[wx[keep], wy[keep]])
pt = 72.0
res = dict(
    full_page_600dpi=dict(changed_pixels=int(mask.sum()), clusters=len(clusters),
                          all_changes_inside_intended_regions=all(c['region'] for c in clusters),
                          per_region=per_region, cluster_detail=clusters),
    regions_in=REGIONS,
    asterisk_2400dpi=dict(ink_pixels=int(len(dx)),
                          ink_x_in=[float(dx.min()), float(dx.max())], ink_y_in=[float(dy.min()), float(dy.max())],
                          clearance_to_badge_pt=float((np.hypot(dx - cx, dy - cy).min() - r) * pt),
                          clearance_to_deploy_ink_pt=float(dep.query(np.c_[dx, dy])[0].min() * pt),
                          margin_to_cell_top_pt=float((cell['top'] - dy.max()) * pt),
                          cell=cell, badge_centre=[cx, cy], badge_r=r))
json.dump(res, open(sys.argv[5], 'w'), indent=1)
print(json.dumps({k: v for k, v in res['full_page_600dpi'].items() if k != 'cluster_detail'}, indent=1))
print(json.dumps(res['asterisk_2400dpi'], indent=1))
