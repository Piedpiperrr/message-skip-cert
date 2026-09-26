"""Appendix figure from existing E17-5 outputs (plotting only, no new computation).
Heatmap: E17_5c_grid.csv P_certify (cells centred on the grid points, shading='nearest'); black line: the stored P = .5 contour
points of E17_5c_contour.csv (grid-interpolated values, connected; entries '<= 0.6' / '> 0.98' have no point in range);
markers: E17_5b_binormal.csv (x = cal disagreement, y = dev AUROC), each in the panel of its own (N_fit, N_cal)."""
import csv
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.lines import Line2D

ST = Path(__file__).resolve().parents[1]; R = ST / 'results'
rd = lambda n: list(csv.DictReader(open(R / n)))
plt.rcParams.update({'font.size': 8, 'axes.labelsize': 8, 'xtick.labelsize': 8, 'ytick.labelsize': 8, 'legend.fontsize': 8,
                     'pdf.fonttype': 42, 'ps.fonttype': 42, 'axes.linewidth': .6, 'xtick.major.width': .6, 'ytick.major.width': .6})
grid, cont, pts = rd('E17_5c_grid.csv'), rd('E17_5c_contour.csv'), rd('E17_5b_binormal.csv')
SIZES = [(670, 448), (2100, 1366), (3000, 6000)]
cmap = LinearSegmentedColormap.from_list('g', plt.get_cmap('Greys')(np.linspace(.03, .6, 256)))
BLUE, ORANGE = '#1f77b4', '#ff7f0e'

fig, axes = plt.subplots(1, 3, figsize=(5.5, 1.9), sharey=True)
fig.subplots_adjust(left=.085, right=.905, bottom=.285, top=.905, wspace=.13)
for ax, (nf, nc) in zip(axes, SIZES):
    g = [r for r in grid if (int(r['N_fit']), int(r['N_cal'])) == (nf, nc)]
    P = sorted({float(r['prevalence']) for r in g}); A = sorted({float(r['AUROC']) for r in g})
    Z = np.full((len(A), len(P)), np.nan)
    for r in g: Z[A.index(float(r['AUROC'])), P.index(float(r['prevalence']))] = float(r['P_certify'])
    assert not np.isnan(Z).any()
    im = ax.pcolormesh(P, A, Z, shading='nearest', cmap=cmap, vmin=0, vmax=1, rasterized=False, edgecolors='face', linewidth=.2)
    c = sorted((float(r['prevalence']), float(r['AUROC_at_P50_value'])) for r in cont
               if (int(r['N_fit']), int(r['N_cal'])) == (nf, nc) and r['AUROC_at_P50_value'] not in ('', 'None'))
    ax.plot([x for x, _ in c], [y for _, y in c], color='black', lw=1.0, solid_capstyle='butt')
    for r in pts:
        if (int(r['N_fit']), int(r['N_cal'])) != (nf, nc): continue
        col = ORANGE if r['setting'].endswith('/C2C') else BLUE          # Text and Text+fact -> blue
        dep = r['observed'] == 'certify'
        ax.plot(float(r['prevalence_cal']), float(r['AUROC_dev']), marker='o', ms=3.6, mew=.8, color=col,
                mfc=col if dep else 'white', mec=col, ls='none', clip_on=False, zorder=5)
    ax.set_xlim(0, .60); ax.set_ylim(.60, 1.00)
    ax.set_xticks([0, .2, .4, .6]); ax.set_xticklabels(['0', '.2', '.4', '.6'])
    ax.set_yticks([.6, .7, .8, .9, 1.0]); ax.set_yticklabels(['.6', '.7', '.8', '.9', '1'])
    ax.tick_params(length=2, pad=1.5)
    ax.set_title(f'$N_{{fit}}$ = {nf}, $N_{{cal}}$ = {nc}', fontsize=8, pad=2.5)   # panel header (no figure title)
axes[0].set_ylabel('AUROC (dev)', labelpad=1.5)
axes[1].set_xlabel('disagreement rate (cal)', labelpad=1.5)
cax = fig.add_axes([.918, .285, .012, .62])
cb = fig.colorbar(im, cax=cax, ticks=[0, .5, 1]); cb.ax.set_yticklabels(['0', '.5', '1']); cb.ax.tick_params(length=2, pad=1.5, width=.6)
cb.solids.set_rasterized(False); cb.solids.set_edgecolor('face'); cb.outline.set_linewidth(.6); cb.set_label('P(certify)', labelpad=1.5)
H = [Line2D([], [], marker='o', ls='none', color=BLUE, mfc=BLUE, ms=3.6, label='Text'),
     Line2D([], [], marker='o', ls='none', color=ORANGE, mfc=ORANGE, ms=3.6, label='C2C'),
     Line2D([], [], marker='o', ls='none', color='0.3', mfc='0.3', ms=3.6, label='deployed'),
     Line2D([], [], marker='o', ls='none', color='0.3', mfc='white', ms=3.6, label='fallback'),
     Line2D([], [], color='black', lw=1.0, label='P(certify) = .5')]
fig.legend(handles=H, loc='lower center', ncol=5, frameon=False, bbox_to_anchor=(.5, 0.0), handletextpad=.3, columnspacing=1.0,
           borderaxespad=.1)
out = R / 'figure_binormal_grid.pdf'
fig.savefig(out, format='pdf', metadata={'CreationDate': None, 'ModDate': None, 'Creator': None, 'Producer': None})
print(out)
