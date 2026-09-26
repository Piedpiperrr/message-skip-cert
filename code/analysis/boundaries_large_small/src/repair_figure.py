"""Document-only figure repair from already frozen curve rows; no statistics rerun."""
from common import *
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
T=csvread(P/'summary/calibration_all_160.csv');D=csvread(P/'summary/risk_coverage_curves.csv');dep=read(P/'deployments/all.json')
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':9,'axes.spines.top':False,'axes.spines.right':False,'pdf.fonttype':42})
fig,axs=plt.subplots(2,4,figsize=(13.5,6.2),sharex=True,sharey=True,layout='constrained');colors={'T':'#2467A0','C':'#D48228'}
for col,(pair,ds) in enumerate(( (p,d) for p in PAIRS for d in DATASETS)):
 axs[0,col].set_title(pair+'/'+ds.upper())
 for b in REFS:
  label='Text' if b=='T' else 'C2C';q=dep[key(pair,ds,b)]['q']
  for row,source,field in [(0,T,'CP_upper_0_999'),(1,D,'conditional_risk')]:
   rr=[r for r in source if (r['pair'],r['dataset'],r['reference'])==(pair,ds,b) and (row==0 or r['split']=='dev')]
   xs=[100*float(r['coverage']) for r in rr];ys=[100*float(r[field]) if r[field] else float('nan') for r in rr]
   assert all(0<=y<=70 or y!=y for y in ys),'Frozen display range must include every point'
   axs[row,col].plot(xs,ys,color=colors[b],ls='-' if b=='T' else '--',marker='o' if b=='T' else '^',ms=3,label=label)
   chosen=next((r for r in rr if float(r['q'])==q),None)
   if chosen:axs[row,col].scatter([100*float(chosen['coverage'])],[100*float(chosen[field])],s=120,marker='*',color=colors[b],edgecolors='black',linewidths=.5,zorder=5)
  if not q:axs[1,col].text(.04,.96 if b=='T' else .88,label+': fallback',transform=axs[1,col].transAxes,color=colors[b],va='top',bbox={'facecolor':'white','edgecolor':'none','alpha':.85,'pad':1})
 for row in [0,1]:
  axs[row,col].axhline(5,color='#555555',ls=':',lw=1);axs[row,col].grid(alpha=.17);axs[row,col].set_xlim(0,101)
 axs[1,col].set_xlabel('Receiver-only coverage (%)')
# Set the common limits AFTER adding all panels; no hidden high-risk curves.
axs[0,0].set_ylim(0,70);axs[0,0].set_yticks([0,5,10,20,30,40,50,60,70])
axs[0,0].set_ylabel('Calibration CP .999 upper (%)');axs[1,0].set_ylabel('Development change / routed (%)');axs[0,0].legend(frameon=False,loc='upper left')
fig.savefig(P/'figures/reference_boundaries.pdf');fig.savefig(P/'figures/reference_boundaries.png',dpi=170);plt.close(fig)
save(P/'evidence/FIGURE_REPAIR.json',{'utc':utc(),'issue':'initial shared y limits stopped autoscaling after first column and clipped small curves','repair':'common0to70 percent axis set after all curves; every finite point asserted in range','new_statistics':0,'source_hashes':{'calibration':sha(P/'summary/calibration_all_160.csv'),'curves':sha(P/'summary/risk_coverage_curves.csv')},'computation_role':'lightweight document rendering using frozen reviewed values; covered by preparation/reporting CPU reserve'})
