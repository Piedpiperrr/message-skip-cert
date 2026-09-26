from numerics import *
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
rows=list(csv.DictReader((P/'summary/main_new15.csv').open()));summ=list(csv.DictReader((P/'summary/budget_summary.csv').open()));refs={r['display_family']:r for r in csv.DictReader((P/'summary/frozen_references.csv').open())}
plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'pdf.fonttype':42})
fig,axs=plt.subplots(2,2,figsize=(10,7))
panels=[('delta_U_D','Utility difference vs D',0,float(refs['R2100']['U'])-float(refs['D']['U'])),('coverage','R coverage',float(refs['D']['coverage']),float(refs['R2100']['coverage'])),('mean_cost_ms','Recomposed mean cost (ms)',float(refs['D']['mean_cost_ms']),float(refs['R2100']['mean_cost_ms'])),('correct','Correct answers / 742',643,644)]
colors=['#0072B2','#D55E00','#009E73','#CC79A7','#8C6D31']
for ax,(field,title,dline,rline) in zip(axs.flat,panels):
 for rep in range(5):
  rr=sorted([r for r in rows if int(r['repeat'])==rep],key=lambda r:int(r['B']));x=[int(r['B']) for r in rr];y=[float(r[field]) for r in rr]
  ax.plot(x,y,color=colors[rep],lw=1.2,alpha=.65)
  for r,xx,yy in zip(rr,x,y):ax.scatter(xx,yy,s=42,color=colors[rep] if r['mode']=='selective' else 'white',edgecolors=colors[rep],zorder=5)
 ax.plot([32,128,512],[float(r[field+'_median']) for r in summ],color='black',lw=2.4,label='Median of five subsets')
 ax.axhline(dline,color='#555555',lw=1.4,ls='--');ax.axhline(rline,color='#7851A9',lw=1.4,ls=':');ax.set_xscale('log',base=4);ax.set_xticks([32,128,512],['32','128\n(primary)','512']);ax.set(title=title,xlabel='Unique gold answers B');ax.grid(alpha=.16)
handles=[Line2D([0],[0],color='black',lw=2,label='Median; thin colored lines: same subset repeat'),Line2D([0],[0],color='#555555',ls='--',label='Frozen D (0 gold)'),Line2D([0],[0],color='#7851A9',ls=':',label='Frozen R2100'),Line2D([0],[0],marker='o',color='none',markerfacecolor='white',markeredgecolor='black',label='Open point: Text fallback')]
fig.legend(handles=handles,loc='lower center',ncol=2,fontsize=9,bbox_to_anchor=(.5,-.005));fig.suptitle('Gold-budget crossover: all five label-subset repeats',fontsize=13);fig.tight_layout(rect=(0,.085,1,.96))
for ext in ['png','pdf']:fig.savefig(P/f'figures/gold_budget_crossover.{ext}',dpi=180,bbox_inches='tight')
plt.close(fig)
# Save numerical source and insertable full table, including every repeat.
lines=[r'\begin{tabular}{rrrrrrrrcc}',r'\toprule',r'$B$ & $r$ & $q$ & R & Changes & Correct & Mean ms & $\Delta U_D$ & U match & C/A match \\',r'\midrule']
for r in sorted(rows,key=lambda r:(int(r['B']),int(r['repeat']))):
 lines.append(f"{r['B']} & {r['repeat']} & {float(r['cal_q']):.2f} & {r['n_R']} & {r['changed']} & {r['correct']} & {float(r['mean_cost_ms']):.3f} & {float(r['delta_U_D']):+.6f} & "+('yes' if r['utility_crossover']=='True' else 'no')+' & '+('yes' if r['cost_accuracy_crossover']=='True' else 'no')+r' \\')
lines +=[r'\bottomrule',r'\end{tabular}'];(P/'paper/table_gold_budget_all15.tex').write_text('\n'.join(lines)+'\n')
lines=[r'\begin{tabular}{rrrrrr}',r'\toprule',r'$B$ & Selective / 5 & U matches / 5 & C/A matches / 5 & Median $\Delta U_D$ & Range \\',r'\midrule']
for r in summ:lines.append(f"{r['B']} & {r['selective_accepted_count']} & {r['utility_crossover_count']} & {r['cost_accuracy_crossover_count']} & {float(r['delta_U_D_median']):+.6f} & [{float(r['delta_U_D_min']):+.6f}, {float(r['delta_U_D_max']):+.6f}] "+r'\\')
lines +=[r'\bottomrule',r'\end{tabular}'];(P/'paper/table_gold_budget_summary.tex').write_text('\n'.join(lines)+'\n')
freeze('FIGURES_COMPLETE.json',[P/'figures/gold_budget_crossover.png',P/'figures/gold_budget_crossover.pdf',P/'paper/table_gold_budget_all15.tex',P/'paper/table_gold_budget_summary.tex'],data_sha256=sha(P/'summary/main_new15.csv'),five_repeats_not_confidence_intervals=True)
