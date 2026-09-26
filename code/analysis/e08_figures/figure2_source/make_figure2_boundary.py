"""Figure 2 (V6): empirical omission boundary across receiver/reference regimes.

Pure rendering of already frozen outcomes; nothing is computed here. Cell states are copied from
the V5 manuscript (numerically cross-checked against frozen CSVs in V5 TEX_VALIDATION.json):
  deploy/fallback : V5 tab_dev_full.tex, column q (0 = fallback)
  economic marker : V5 tab_e2e_sealed.tex, paired mean E2E saving 95% interval
                    ("+"  = interval above zero; "?" = interval crosses zero)
      medium OBQA C2C 79.7 [48.1, 129.1]    medium ARC C2C 100.7 [74.5, 133.1]
      large OBQA Text 517.1 [447.8, 583.6]  large OBQA C2C 36.6 [18.0, 56.8]
      large ARC Text 717.6 [670.6, 763.2]   large ARC C2C 110.9 [82.0, 142.8]
      large MMLU Text 346.3 [249.8, 443.0]  large MMLU C2C 8.2 [-20.5, 44.0]
  sealed          : large/ARC Text and C2C policies, project-sealed ARC-Challenge test (V5 Section 4.3)
  E8              : small and medium pairs on MMLU-Pro, all four settings fallback
                    (P2_R2_E8_20260920T012544Z/analysis/deployments/deployment_configs.json,
                     0 of 80 calibration tests accepted; no cell is "not evaluated" any more)
"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "paper_active", "figures")
plt.rcParams.update({"pdf.fonttype": 42, "ps.fonttype": 42, "font.family": "STIXGeneral",
                     "mathtext.fontset": "stix", "font.size": 7.5, "axes.linewidth": 0.0})

INK, MUTED, FAINT = "#1A1A1A", "#555555", "#767676"
DEPLOY = "#1F5FA8"          # same blue as the omission path in Figure 1
FALL_FILL, FALL_EDGE = "#E6E6E6", "#BDBDBD"
COST = "#B8520A"            # same orange as the cost annotations in Figure 1

F, NE, POS, UNC = "fallback", "n/e", "deploy+", "deploy?"
ROWS = [  # name, receiver/helper sizes, cells (OBQA T, OBQA C, ARC T, ARC C, MMLU T, MMLU C), count
    ("small",  "0.5B $\\rightarrow$ 0.6B", [F, F, F, F, F, F], "0/4 + 0/2"),
    ("medium", "1.5B $\\rightarrow$ 1.7B", [F, POS, F, POS, F, F], "2/4 + 0/2"),
    ("large",  "7B $\\rightarrow$ 8B",     [POS, POS, POS, POS, POS, UNC], "4/4 + 2/2"),
]
TASKS = ["OBQA", "ARC", "MMLU-Pro"]

W, H = 5.5, 1.50
fig = plt.figure(figsize=(W, H))
ax = fig.add_axes([0, 0, 1, 1])
ax.set_xlim(0, W); ax.set_ylim(0, H); ax.set_aspect("equal"); ax.axis("off")

X0 = 1.14          # grid left edge
CW, RH = 0.52, 0.245
GAPX = 0.10        # extra gap between benchmark groups
TOP = H - 0.37     # top of first row
PAD = 0.017


def cell_x(j):
    return X0 + j * CW + (j // 2) * GAPX


def t(x, y, s, fs=7.5, color=INK, ha="center", va="center", **kw):
    ax.text(x, y, s, ha=ha, va=va, fontsize=fs, color=color, **kw)


def check(cx, cy, r, color, lw=0.9):
    ax.plot([cx - 0.55 * r, cx - 0.12 * r, cx + 0.6 * r], [cy + 0.02 * r, cy - 0.45 * r, cy + 0.5 * r],
            color=color, lw=lw, solid_capstyle="round", solid_joinstyle="round")


def badge(cx, cy, kind, r=0.058):
    ax.add_patch(Circle((cx, cy), r, fc="white", ec="none"))
    if kind == POS:
        check(cx, cy, r * 0.95, DEPLOY)
    else:
        t(cx, cy - 0.004, "?", fs=7.4, color=COST, weight="bold")


# headers
for g, task in enumerate(TASKS):
    xl, xr = cell_x(2 * g), cell_x(2 * g + 1) + CW
    t((xl + xr) / 2, TOP + 0.265, task, fs=8.0, weight="bold")
    ax.plot([xl + 0.03, xr - 0.03], [TOP + 0.195, TOP + 0.195], color=FAINT, lw=0.5)
    for k, ref in enumerate(["Text", "C2C"]):
        t(cell_x(2 * g + k) + CW / 2, TOP + 0.10, ref, fs=7.2, color=MUTED)
XC = cell_x(5) + CW + 0.12
t(XC, TOP + 0.10, "deployed", fs=7.0, color=MUTED, ha="left")
t(X0 - 0.07, TOP + 0.10, "helper $\\rightarrow$ receiver", fs=6.6, color=MUTED, ha="right")

for i, (name, sizes, cells, count) in enumerate(ROWS):
    yb = TOP - (i + 1) * RH
    yc = yb + RH / 2
    t(0.02, yc, name, fs=8.0, weight="bold", ha="left")
    t(X0 - 0.07, yc, sizes, fs=6.6, color=MUTED, ha="right")
    for j, c in enumerate(cells):
        x = cell_x(j)
        rect = dict(xy=(x + PAD, yb + PAD), width=CW - 2 * PAD, height=RH - 2 * PAD)
        if c == F:
            ax.add_patch(Rectangle(**rect, fc=FALL_FILL, ec="none"))
            t(x + CW / 2, yc, "fallback", fs=6.8, color=MUTED, style="italic")
        elif c == NE:
            ax.add_patch(Rectangle(**rect, fc="white", ec=FALL_EDGE, lw=0.5, ls=(0, (2.0, 1.4))))
            ax.text(x + CW / 2, yc, "not\nevaluated", ha="center", va="center", fontsize=6.2, color=FAINT, linespacing=0.9)
        else:
            ax.add_patch(Rectangle(**rect, fc=DEPLOY, ec="none"))
            t(x + CW / 2 - 0.066, yc, "deploy", fs=6.9, color="white", weight="bold")
            if (name, j) == ("large", 0):  # R1: superscript double dagger after "deploy" (large / OBQA / Text), clear of the badge
                ax.annotate("‡", xy=(1, 0), xycoords=ax.texts[-1], xytext=(-0.22, 5.14), textcoords="offset points",
                            ha="left", va="baseline", fontsize=4.8, color="white", weight="bold")
            if (name, j) == ("medium", 1):  # R2: superscript asterisk after "deploy" (medium / OBQA / C2C), same rule as the dagger
                ax.annotate("*", xy=(1, 0), xycoords=ax.texts[-1], xytext=(-0.22, 5.14), textcoords="offset points",
                            ha="left", va="baseline", fontsize=4.8, color="white", weight="bold")
            badge(x + CW - 0.098, yc, c)
    t(XC, yc, count, fs=7.6, weight="bold", ha="left")

# sealed test bracket under large/ARC
yb_last = TOP - 3 * RH
xl, xr = cell_x(2) + PAD, cell_x(3) + CW - PAD
ys = yb_last - 0.04
ax.plot([xl, xl, xr, xr], [ys + 0.028, ys, ys, ys + 0.028], color=INK, lw=0.6)
t((xl + xr) / 2, ys - 0.08, "sealed test", fs=6.5, color=INK)

# legend: one row at the bottom, laid out from measured text widths and centered
ly = 0.075
sw, sh = 0.17, 0.12
entries = [("deploy", "omission deployed"), ("pos", "95% CI above 0"),
           ("unc", "saving not established"), ("fall", "fallback to fixed $b$")]
renderer = fig.canvas.get_renderer()
widths = []
for _, label in entries:
    tmp = ax.text(0, 0, label, fontsize=6.8)
    bb = tmp.get_window_extent(renderer=renderer)
    widths.append(bb.width / fig.dpi)
    tmp.remove()
SPACE = 0.14
total = sum(sw + 0.05 + w for w in widths) + SPACE * (len(entries) - 1)
sx = (W - total) / 2
for (kind, label), w in zip(entries, widths):
    if kind in ("deploy", "pos", "unc"):
        ax.add_patch(Rectangle((sx, ly - sh / 2), sw, sh, fc=DEPLOY, ec="none"))
        if kind != "deploy":
            badge(sx + sw / 2, ly, POS if kind == "pos" else UNC, r=0.05)
    elif kind == "fall":
        ax.add_patch(Rectangle((sx, ly - sh / 2), sw, sh, fc=FALL_FILL, ec="none"))
    else:
        ax.add_patch(Rectangle((sx, ly - sh / 2), sw, sh, fc="white", ec=FALL_EDGE, lw=0.5, ls=(0, (2.0, 1.4))))
    t(sx + sw + 0.05, ly, label, fs=6.8, color=INK, ha="left")
    sx += sw + 0.05 + w + SPACE

os.makedirs(OUT, exist_ok=True)
fig.savefig(os.path.join(OUT, "figure2_boundary.pdf"), metadata={"Creator": "make_figure2_boundary.py"})
fig.savefig(os.path.join(OUT, "figure2_boundary.png"), dpi=300)
fig.savefig(os.path.join(HERE, "figure2_boundary_600dpi.png"), dpi=600)
print("wrote figure2_boundary.{pdf,png}")
