"""Frozen baseline evaluation and train OOF summaries. Execute only in bounded PBS."""
import os,json,csv,hashlib
from pathlib import Path
import numpy as np
from sklearn.metrics import roc_auc_score,average_precision_score
from fit_stage import O,P10,A,cfg,freeze,readlabels,ymat,sha,save
S=O/'summary'
METHODS=cfg['OOF']['methods']+['query_independent']

def table(name,rows):
 rows=list(rows);assert rows,name
 p=S/name;p.parent.mkdir(parents=True,exist_ok=True);tmp=p.with_suffix('.tmp')
 with tmp.open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]),extrasaction='raise');w.writeheader()
  for r in rows:w.writerow({k:('NA' if v is None or isinstance(v,(float,np.floating)) and not np.isfinite(v) else v) for k,v in r.items()})
 tmp.replace(p)
 return len(rows)

def rate(y):return float(np.mean(y)) if len(y) else None

def flip_metrics(y,p):
 n=len(y);pos=int(y.sum());two=n and 0<pos<n
 if n:
  q=np.clip(np.asarray(p,dtype=np.float64),1e-15,1-1e-15)
  loss=float(-np.mean(y*np.log(q)+(1-y)*np.log1p(-q)))
 else:loss=None
 return {'n':n,'positive':pos,'positive_rate':rate(y),'ROC_AUC':float(roc_auc_score(y,p)) if two else None,'AP':float(average_precision_score(y,p)) if two else None,'log_loss':loss,'NA_reason':'' if two else ('single_class_evaluation' if n else 'empty_scope')}

def baseline():
 labels=readlabels('full_development_P2_SCORING_V2.jsonl');panel_labels=readlabels('panel_development_P2_SCORING_V2.jsonl')
 rows=[];changed=[];panels=[]
 for asset in cfg['baseline_assets']:
  pair,ds,family=[asset[k] for k in ['pair','dataset','family']];d=O/'baseline'/pair/ds;src=P10/'results'/pair/ds
  new=dict(np.load(d/(family+'_dev_predictions.npz'),allow_pickle=False));old=dict(np.load(src/('dev_predictions_'+family+'.npz'),allow_pickle=False))
  assert np.array_equal(new['ids'],old['ids']) and np.array_equal(new['lambdas'],cfg['lambdas']) and np.array_equal(old['lambdas'],cfg['lambdas'])
  assert np.array_equal(new['probabilities'][:,[0,1,3]],old['probabilities'][:,[0,1,3]])
  assert np.allclose(new['predicted_ms'],old['predicted_ms'],rtol=1e-12,atol=1e-12)
  ids=new['ids'].tolist();n=len(ids);y=ymat(labels,pair,ds,ids,'y');idx=np.arange(n);lookup={i:j for j,i in enumerate(ids)}
  dv='dev' if ds=='obqa' else 'validation';pc=dict(np.load(src/(dv+'_cost_panel_matrix.npz'),allow_pickle=False));panel_idx=np.array([lookup[i] for i in pc['ids']]);py=ymat(panel_labels,pair,ds,pc['ids'],'y');assert np.array_equal(py,y[panel_idx]);pn=len(panel_idx)
  for na in [3,4]:
   for li,l in enumerate(cfg['lambdas']):
    c0=old['choices'+str(na)][:,li];c1=new['choices'+str(na)][:,li];s0=y[idx,c0];s1=y[idx,c1]
    base={'pair':pair,'dataset':ds,'family':family,'n_actions':na,'lambda':l,'n':n}
    row={**base,'old_V2_rescored_accuracy':rate(s0),'updated_V2_accuracy':rate(s1),'accuracy_change':rate(s1-s0),'changed_selections':int((c0!=c1).sum()),'C_probability_mean_change':rate(new['probabilities'][:,2]-old['probabilities'][:,2])}
    for a in range(na):row['old_select_'+A[a]]=rate(c0==a);row['updated_select_'+A[a]]=rate(c1==a)
    # Stable columns across the three-/four-action views; excluded A is structurally NA.
    for a in A:
     row.setdefault('old_select_'+a,None);row.setdefault('updated_select_'+a,None)
    rows.append(row)
    for i in np.flatnonzero(c0!=c1):changed.append({**base,'id':ids[i],'old_action':A[c0[i]],'updated_action':A[c1[i]],'old_correct':int(s0[i]),'updated_correct':int(s1[i])})
    for name,ch in [('old_V2_rescored',c0),('updated_V2',c1)]:
     choice=ch[panel_idx];panels.append({**base,'n':pn,'version':name,'panel_accuracy':rate(py[np.arange(pn),choice]),'action_cost_replay_ms':rate(pc['latency_ms'][np.arange(pn),choice]),'cost_scope':'old panel action-only replay; new router overhead unmeasured; not new full latency'})
  for a in range(4):
   panels.append({'pair':pair,'dataset':ds,'family':family,'n_actions':4,'lambda':'NA','n':pn,'version':'fixed_'+A[a],'panel_accuracy':rate(py[:,a]),'action_cost_replay_ms':rate(pc['latency_ms'][:,a]),'cost_scope':'old panel action-only replay; fixed action'})
 table('baseline_update_summary.csv',rows)
 if changed:table('baseline_changed_selections.csv',changed)
 else:
  (S/'baseline_changed_selections.csv').write_text('pair,dataset,family,n_actions,lambda,n,id,old_action,updated_action,old_correct,updated_correct\n')
 table('baseline_panel_replay.csv',panels)
 return rows

def collect(pair,ds,family):
 chunks=[];directions=[]
 for k in range(5):
  d=O/'oof'/ds/family/('fold'+str(k))/pair;rec=json.loads((d/'COMPLETE.json').read_text());assert rec['prediction_sha256']==sha(d/'predictions.npz')
  z=dict(np.load(d/'predictions.npz',allow_pickle=False));n=len(z['ids'])
  chunk={key:z[key] for key in ['ids','fold','y','f','valid','m','p']}
  for key in ['constant_flip_rate','delta','cost_proxy_ms']:chunk[key]=np.broadcast_to(z[key],(n,len(z[key])))
  chunk['c_ref_ms']=np.full(n,float(z['c_ref_ms']))
  for method in METHODS:
   for na in [3,4]:
    key=method+'_choices'+str(na);chunk[key]=np.broadcast_to(z[key],(n,len(cfg['lambdas'])))
  chunks.append(chunk)
  for j,a in enumerate(A[1:]):
   change=z['y'][:,j+1]-z['y'][:,0];fl=z['f'][:,j].astype(bool)
   directions.append({'pair':pair,'dataset':ds,'family':family,'fold':k,'action':a,'fit_gain':int(z['fit_gain'][j]),'fit_harm':int(z['fit_harm'][j]),'fit_flips':int(z['fit_flip_n'][j]),'fit_zero_gain_flips':int(z['fit_flip_n'][j]-z['fit_gain'][j]-z['fit_harm'][j]),'delta_shrunk':float(z['delta'][j]),'fit_flip_rate':float(z['constant_flip_rate'][j]),'heldout_flips':int(fl.sum()),'heldout_gain':int((change>0).sum()),'heldout_harm':int((change<0).sum()),'heldout_zero_gain_flips':int((fl&(change==0)).sum()),'heldout_signed_gain_per_flip_DIAGNOSTIC':float(change.sum()/fl.sum()) if fl.sum() else None,'fit_panel_n':len(z['fit_panel_ids']),'c_ref_ms':float(z['c_ref_ms']),'cost_proxy_ms':float(z['cost_proxy_ms'][j+1])})
 b={key:np.concatenate([c[key] for c in chunks]) for key in chunks[0]};assert len(b['ids'])==len(set(b['ids']))==cfg['dataset_inputs'][ds]['n']
 return b,directions

def oof():
 flips=[];decisions=[];paired=[];overheads=[];invalid=[];dirs=[];itemrows=[]
 for pair,ds in cfg['combinations']:
  for family in cfg['features']:
   b,direction=collect(pair,ds,family);dirs+=direction;n=len(b['ids']);base={'pair':pair,'dataset':ds,'family':family}
   for i in range(n):
    r={**base,'id':str(b['ids'][i]),'fold':int(b['fold'][i]),'c_ref_ms':float(b['c_ref_ms'][i])}
    for j,a in enumerate(A):
     for key in ['y','valid','p','cost_proxy_ms']:r[key+'_'+a]=float(b[key][i,j])
     if j:
      for key in ['f','m','constant_flip_rate','delta']:r[key+'_'+a]=float(b[key][i,j-1])
    for method in METHODS:
     for na in [3,4]:
      for li,l in enumerate(cfg['lambdas']):r[method+'_a'+str(na)+'_lambda'+str(l)]=A[int(b[method+'_choices'+str(na)][i,li])]
    itemrows.append(r)
   for scope,mask in [('pooled',np.ones(n,bool))]+[(str(k),b['fold']==k) for k in range(5)]:
    y=b['y'][mask];f=b['f'][mask];v=b['valid'][mask].astype(bool);n0=len(y);index=np.arange(n0);ref=b['c_ref_ms'][mask];cost=b['cost_proxy_ms'][mask];common={**base,'fold':scope}
    for j,a in enumerate(A[1:]):
     for sub,keep in [('all',np.ones(n0,bool)),('both_R_and_action_valid_diagnostic_only',v[:,0]&v[:,j+1])]:
      for model,p in [('FFR_E0',b['m'][mask,j]),('constant_flip_rate',b['constant_flip_rate'][mask,j])]:
       flips.append({**common,'action':a,'scope':sub,'predictor':model,**flip_metrics(f[keep,j],p[keep])})
     partitions={'all':np.ones(n0,bool),'both_valid':v[:,0]&v[:,j+1],'R_invalid_only':~v[:,0]&v[:,j+1],'action_invalid_only':v[:,0]&~v[:,j+1],'both_invalid':~v[:,0]&~v[:,j+1]}
     change=y[:,j+1]-y[:,0]
     for name,keep in partitions.items():
      invalid.append({**common,'action':a,'validity_scope':name,'n':int(keep.sum()),'flip_count':int(f[keep,j].sum()),'flip_rate':rate(f[keep,j]),'gain_count':int((change[keep]>0).sum()),'harm_count':int((change[keep]<0).sum()),'zero_gain_flip_count':int(((change[keep]==0)&(f[keep,j]==1)).sum()),'R_accuracy':rate(y[keep,0]),'action_accuracy':rate(y[keep,j+1])})
    for na in [3,4]:
     for li,l in enumerate(cfg['lambdas']):
      outcomes={}
      names=METHODS+['fixed_'+a for a in A[:na]]
      for name in names:
       choice=np.full(n0,A.index(name[-1])) if name.startswith('fixed_') else b[name+'_choices'+str(na)][mask,li]
       acc=y[index,choice];ms=cost[index,choice];utility=acc-l*ms/ref;change=acc-y[:,0]
       outcomes[name]=(choice,acc,ms,utility)
       row={**common,'n_actions':na,'lambda':l,'method':name,'n':n0,'accuracy':rate(acc),'proxy_utility':rate(utility) if l>0 else None,'proxy_action_ms':rate(ms),'gain_count_vs_R':int((change>0).sum()),'harm_count_vs_R':int((change<0).sum()),'accuracy_gain_vs_R':rate(change),'invalid_selected_count':int((~v[index,choice]).sum()),'invalid_selected_rate':rate(~v[index,choice]),'new_router_overhead_ms':None}
       for a in range(4):row['select_'+A[a]]=rate(choice==a) if a<na else None
       decisions.append(row)
      comparisons=[('FFR_E0','IndepLR'),('FFR_true_flip_DIAGNOSTIC','FFR_E0'),('FFR_E0','FFR_constant_flip_rate'),('FFR_E0','query_independent'),('IndepLR','query_independent')]+[('FFR_E0','fixed_'+a) for a in A[:na]]
      for left,right in comparisons:
       c1,a1,m1,u1=outcomes[left];c0,a0,m0,u0=outcomes[right];du=u1-u0
       row={**common,'n_actions':na,'lambda':l,'left':left,'right':right,'n':n0,'accuracy_difference':rate(a1-a0),'proxy_utility_difference':rate(du) if l>0 else None,'proxy_action_ms_difference':rate(m1-m0),'selection_disagreement':rate(c1!=c0),'left_correct_right_wrong':int(((a1==1)&(a0==0)).sum()),'left_wrong_right_correct':int(((a1==0)&(a0==1)).sum())}
       paired.append(row)
       headroom=float(np.mean(du)/(l*np.mean(1/ref))) if l>0 else None
       overheads.append({**common,'n_actions':na,'lambda':l,'left':left,'right':right,'n':n0,'proxy_utility_difference':rate(du) if l>0 else None,'mean_inverse_c_ref_per_ms':rate(1/ref),'admissible_added_ms':headroom,'has_positive_headroom':bool(headroom>0) if headroom is not None else None,'interpretation':'common added milliseconds for left relative to right; optimistic proxy; not measured overhead' if l else 'lambda=0 accuracy only'})
 table('oof_predictions.csv',itemrows);table('flip_metrics.csv',flips);table('decision_metrics.csv',decisions);table('paired_method_differences.csv',paired);table('overhead_headroom.csv',overheads);table('invalid_analysis.csv',invalid);table('direction_diagnostics.csv',dirs)
 return flips,decisions,paired,overheads,dirs

def index_models():
 rows=[]
 for asset in cfg['baseline_assets']:
  pair,ds,family=[asset[k] for k in ['pair','dataset','family']]
  for kind,p in [('baseline_C',O/asset['output_C_head']),('baseline_bundle',O/asset['output_bundle'])]:rows.append({'role':kind,'pair':pair,'dataset':ds,'family':family,'fold':'NA','path':str(p),'sha256':sha(p),'source':asset['source_bundle']['path'],'status':'COMPLETE'})
 for ds in ['obqa','arc']:
  for family in cfg['features']:
   for k in range(5):
    for pair in ['large','small']:
     for head in ['FFR_'+a for a in A[1:]]+['IndepLR_'+a for a in A]:
      p=O/'oof'/ds/family/('fold'+str(k))/pair/(head+'.joblib');rows.append({'role':head,'pair':pair,'dataset':ds,'family':family,'fold':k,'path':str(p),'sha256':sha(p),'source':'frozen train fold only','status':'COMPLETE'})
 with (O/'MODEL_INDEX.tsv').open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]),delimiter='\t');w.writeheader();w.writerows(rows)
 return len(rows)

def fmt(x,percent=False):return 'NA' if x is None else f'{x*(100 if percent else 1):.3f}'
def tex_escape(x):return str(x).replace('_',r'\_')
def manuscript_tables(baselines,flips,decisions,paired,overheads):
 text=[r'% Generated from the complete frozen results. All lambda values retained.',r'\paragraph{Targeted baseline update (fixed development evaluation).}',r'\begin{tabular}{lllrrrr}',r'Pair & Task & Features & Actions & $\lambda$ & Old acc. (\%) & Updated acc. (\%) \\']
 for r in baselines:text.append(' & '.join([r['pair'],r['dataset'].upper(),r['family'],str(r['n_actions']),str(r['lambda']),fmt(r['old_V2_rescored_accuracy'],True),fmt(r['updated_V2_accuracy'],True)])+r' \\')
 text += [r'\end{tabular}',r'\paragraph{Pooled OOF flip prediction (all examples).}',r'\begin{tabular}{llllrrrrr}',r'Pair & Task & Features & Action & Rate & AUC & AP & Log loss & Constant log loss \\']
 lookup={(r['pair'],r['dataset'],r['family'],r['action']):r for r in flips if r['fold']=='pooled' and r['scope']=='all' and r['predictor']=='constant_flip_rate'}
 for r in flips:
  if r['fold']=='pooled' and r['scope']=='all' and r['predictor']=='FFR_E0':
   c=lookup[r['pair'],r['dataset'],r['family'],r['action']];text.append(' & '.join([r['pair'],r['dataset'].upper(),r['family'],r['action']]+[fmt(r[k]) for k in ['positive_rate','ROC_AUC','AP','log_loss']]+[fmt(c['log_loss'])])+r' \\')
 text += [r'\end{tabular}',r'\paragraph{Complete pooled OOF operating points.}',r'All costs are fold-training panel proxies; new router overhead is unmeasured. The true-flip substitution is a non-deployable diagnostic, not a general routing upper bound. At $\lambda=0$, utility and overhead entries are NA and only accuracy is interpreted.']
 key=lambda r:(r['pair'],r['dataset'],r['family'],r['n_actions'],r['lambda'])
 dmap={(key(r),r['method']):r for r in decisions if r['fold']=='pooled'}
 hmap={key(r):r for r in overheads if r['fold']=='pooled' and r['left']=='FFR_E0' and r['right']=='query_independent'}
 for pair,ds in cfg['combinations']:
  for family in cfg['features']:
   for na in [3,4]:
    text += [r'\paragraph{'+f'{pair}, {ds.upper()}, {family}, {na} actions.'+'}',r'\begin{tabular}{rrrrrrrr}',r'$\lambda$ & FFR acc. & IndepLR acc. & Const. acc. & True-flip acc. & Fixed-ref. acc. & $\Delta U_{\rm FFR-Indep}$ & Headroom (ms) \\']
    for l in cfg['lambdas']:
     k=(pair,ds,family,na,l);dd=[dmap[k,m] for m in METHODS];f,i,c,t,q=dd
     diff=f['proxy_utility']-i['proxy_utility'] if l>0 else None
     text.append(' & '.join([str(l)]+[fmt(x['accuracy'],True) for x in dd]+[fmt(diff),fmt(hmap[k]['admissible_added_ms'])])+r' \\')
    text.append(r'\end{tabular}')
 (O/'paper/04_results_tables.tex').write_text('\n'.join(text)+'\n')


def main():
 assert os.environ.get('P2_BOUNDED_SUPERVISED')==O.name and os.environ.get('PBS_JOBID')
 assert (O/'FITTING_COMPLETE.json').exists()
 S.mkdir(exist_ok=True)
 base=baseline();flips,decisions,paired,heads,dirs=oof();model_n=index_models();manuscript_tables(base,flips,decisions,paired,heads)
 summary={'status':'METRICS_COMPLETE_VALIDATION_PENDING','baseline_focus_word_lambda_001':[r for r in base if r['family']=='word' and r['lambda']==.01],
  'pooled_flip_metrics':[r for r in flips if r['fold']=='pooled' and r['scope']=='all'],
  'pooled_FFR_minus_IndepLR':[r for r in paired if r['fold']=='pooled' and r['left']=='FFR_E0' and r['right']=='IndepLR'],
  'pooled_true_flip_minus_learned':[r for r in paired if r['fold']=='pooled' and r['left']=='FFR_true_flip_DIAGNOSTIC'],
  'pooled_FFR_vs_query_independent_headroom':[r for r in heads if r['fold']=='pooled' and r['left']=='FFR_E0' and r['right']=='query_independent'],
  'direction_constants':dirs,'model_index_rows':model_n,'all_lambdas_reported':True,'new_overhead_measured':False,'ARC_test_read':False,'exploratory_point_estimates_only':True}
 save(S/'RESULTS_SUMMARY.json',summary)
 counts={p.name:sum(1 for _ in p.open())-1 for p in S.glob('*.csv')}
 save(O/'METRICS_COMPLETE.json',{'status':'METRICS_COMPLETE_VALIDATION_PENDING','table_rows':counts,'protocol_sha256':freeze['config_sha256'],'tables_sha256':{p.name:sha(p) for p in S.glob('*.csv')}})
 print(json.dumps({'METRICS_COMPLETE':True,'table_rows':counts},ensure_ascii=False),flush=True)
if __name__=='__main__':main()
