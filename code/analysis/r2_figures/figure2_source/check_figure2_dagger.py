"""QA for the R1 Figure 2 change (CPU; reads rasters made with pdftoppm from the original and modified PDFs).
1) 600 dpi full page: all changed pixels lie inside the large / OBQA / Text cell (the dagger only).
2) 2400 dpi crop of that cell: dagger ink clearance to the white check-mark badge disc (geometry from the script:
   centre (x + CW - 0.098, yc), r = 0.058 in), to the "deploy" ink, and to the cell's top edge.
usage: check_figure2_dagger.py <full600_orig.png> <full600_new.png> <cell2400_orig.png> <cell2400_new.png> <out.json>"""
import sys, json
import numpy as np
from PIL import Image
from scipy.spatial import cKDTree
W, H = 5.5, 1.50; X0, CW, RH, GAPX, PAD = 1.14, 0.52, 0.245, 0.10, 0.017; TOP = H - 0.37
x = X0; yb = TOP - 3 * RH; yc = yb + RH / 2; cx, r = x + CW - 0.098, 0.058
cell = dict(left=x + PAD, right=x + CW - PAD, bottom=yb + PAD, top=yb + RH - PAD)
load = lambda p: np.asarray(Image.open(p).convert("RGB")).astype(int)
a, b = load(sys.argv[1]), load(sys.argv[2]); assert a.shape == b.shape
ys, xs = np.nonzero(np.abs(a - b).max(-1) > 0); D = 600
chg = dict(changed_pixels=int(len(xs)), x_in=[xs.min() / D, (xs.max() + 1) / D], y_in=[H - (ys.max() + 1) / D, H - ys.min() / D])
chg["inside_cell"] = bool(chg["x_in"][0] >= cell["left"] and chg["x_in"][1] <= cell["right"] and chg["y_in"][0] >= cell["bottom"] and chg["y_in"][1] <= cell["top"])
A, B = load(sys.argv[3]), load(sys.argv[4]); D2, ox, oy = 2400, 2700, 2050          # crop offsets used with pdftoppm
to_in = lambda r_, c_: ((c_ + ox + 0.5) / D2, H - (r_ + oy + 0.5) / D2)
rr, cc = np.nonzero(np.abs(A - B).max(-1) > 64); dx, dy = to_in(rr, cc)                # dagger ink (changed, > 25% step)
rr0, cc0 = np.nonzero(A.min(-1) > 128); wx, wy = to_in(rr0, cc0)                      # white ink in the original crop
keep = (np.hypot(wx - cx, wy - yc) > r + 0.002) & (wx > cell["left"]) & (wx < cell["right"]) & (wy > cell["bottom"]) & (wy < cell["top"])
dep = cKDTree(np.c_[wx[keep], wy[keep]])                                               # "deploy" ink (white, outside the badge)
pt = 72.0
res = dict(full_page_600dpi=chg,
           cell_2400dpi=dict(dagger_ink_pixels=int(len(dx)), dagger_ink_x_in=[float(dx.min()), float(dx.max())], dagger_ink_y_in=[float(dy.min()), float(dy.max())],
                             clearance_to_badge_pt=float((np.hypot(dx - cx, dy - yc).min() - r) * pt),
                             clearance_to_deploy_ink_pt=float(dep.query(np.c_[dx, dy])[0].min() * pt),
                             margin_to_cell_top_pt=float((cell["top"] - dy.max()) * pt)),
           geometry_in=dict(cell=cell, badge_centre=[cx, yc], badge_r=r))
json.dump(res, open(sys.argv[5], "w"), indent=1); print(json.dumps(res, indent=1))
