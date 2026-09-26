from numerics import *
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
rows=list(csv.DictReader((P/'summary/grid_curves.csv').open()));deps=read(P/'models/deployment.json')
colors={'D':'#0072B2','R':'#D55E00','Diff':'#009E73','H':'#CC79A7','Random':'#777777'}
labels={'D':'Disagreement','R':'Correctness R','Diff':'Correctness difference','H':'Harm','Random':'Uniform random'}
plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'pdf.fonttype':42})
fig,axes=plt.subplots(1,2,figsize=(11,4.4),sharex=True,sharey=True)
for ax,split in zip(axes,['cal','dev']):
 for f in CFG['families']:
  rr=[r for r in rows if r['split']==split and r['family']==f];x=np.array([float(r['coverage']) for r in rr]);y=np.array([float(r['conditional_risk']) if r['conditional_risk'] else np.nan for r in rr]);accepted=np.array([r['cal_accepted']=='True' for r in rr]);selected=np.array([r['final_deployment']=='True' for r in rr])
  ax.plot(x,y,color=colors[f],lw=1.5,label=labels[f]);ax.scatter(x[~accepted],y[~accepted],s=24,facecolors='white',edgecolors=colors[f],zorder=3);ax.scatter(x[accepted],y[accepted],s=28,color=colors[f],zorder=4);ax.scatter(x[selected],y[selected],s=160,marker='*',color=colors[f],edgecolors='black',linewidths=.5,zorder=5)
 ax.axhline(.05,color='black',linestyle='--',lw=1);ax.set(title='Calibration (n=1366)' if split=='cal' else 'Exposed development (n=742)',xlabel='R coverage');ax.set_xlim(0,1.02);ax.set_ylim(bottom=0);ax.grid(alpha=.15)
axes[0].set_ylabel('Conditional parsed-answer change rate')
axes[1].legend(fontsize=9,loc='upper left')
legend=[Line2D([0],[0],marker='o',color='none',markeredgecolor='black',markerfacecolor='white',label='Not accepted on calibration'),Line2D([0],[0],marker='o',color='none',markerfacecolor='black',label='Accepted on calibration'),Line2D([0],[0],marker='*',markersize=12,color='none',markerfacecolor='black',label='Frozen deployment')]
fig.legend(handles=legend,loc='lower center',ncol=3,bbox_to_anchor=(.5,-.01),fontsize=9)
fallback=', '.join(labels[f] for f in CFG['families'] if deps[f]['mode']=='fixed_T')
fig.suptitle('Predeclared binary FFR threshold families',fontsize=13)
fig.text(.5,.06,'Text fallbacks (coverage 0; conditional risk NA): '+(fallback or 'none'),ha='center',fontsize=8)
fig.tight_layout(rect=(0,.1,1,.96))
for ext in ['pdf','png']:fig.savefig(P/f'figures/risk_coverage.{ext}',dpi=180,bbox_inches='tight')
plt.close(fig)
# Publication-ready compact source-backed tables.
main=list(csv.DictReader((P/'summary/main_dev.csv').open()));cal=list(csv.DictReader((P/'summary/calibration_100.csv').open()))
def fnum(s,d=3):return f'{float(s):.{d}f}' if s not in ['',None] else '--'
lines=[r'\begin{tabular}{lrrrrrrr}',r'\toprule',r'Score & $q$ & R / 742 & Changes / R & Correct & Mean ms & Saved ms & $U$ \\',r'\midrule']
for r in main:
 q=fnum(r['q'],2);risk=f"{r['changed']}/{r['n_R']}" if int(r['n_R']) else 'NA'
 lines.append(f"{r['family'].replace('_',' ')} & {q} & {r['n_R']} & {risk} & {r['correct']} & {fnum(r['mean_cost_ms'],2)} & {fnum(r['net_saving_vs_Text_ms'],2)} & {fnum(r['U'],6)} "+r'\\')
lines +=[r'\bottomrule',r'\end{tabular}']
(P/'paper/table_main.tex').write_text('\n'.join(lines)+'\n')
lines=[r'\begin{tabular}{lrrrrr}',r'\toprule',r'Score & Accepted $q$ & Selected $q$ & $k/n$ & $p$ & CP upper \\',r'\midrule']
for f in CFG['families']:
 p=deps[f];c=p['calibration'];aq=', '.join(f'{q:.2f}' for q in p['accepted_q']) or 'none'
 lines.append(f"{labels[f]} & {aq} & {p['q']:.2f} & "+(f"{c['changed']}/{c['n_R']} & {c['p_value']:.6g} & {c['CP_upper_0_999']:.4f}" if c else 'NA & -- & --')+r'\\')
lines +=[r'\bottomrule',r'\end{tabular}'];(P/'paper/table_calibration.tex').write_text('\n'.join(lines)+'\n')
freeze('FIGURES_COMPLETE.json',[P/'figures/risk_coverage.pdf',P/'figures/risk_coverage.png',P/'paper/table_main.tex',P/'paper/table_calibration.tex'],source=sha(P/'summary/grid_curves.csv'),final_points_from='models/deployment.json')
