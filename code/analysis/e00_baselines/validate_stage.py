"""Numerical checks on actual formal heads/folds and independent table consistency."""
import os,json,csv,collections,hashlib
from pathlib import Path
import numpy as np
import joblib,sklearn,scipy
from fit_stage import O,P10,A,cfg,freeze,sha,save,ymat,readlabels

def validate_first_fold(z,labels,pair,ds,family,k,ids,tr,te,vec,texts):
 assert set(tr).isdisjoint(te) and len(tr)+len(te)==len(ids)
 held=[ids[i] for i in te];fitids=[ids[i] for i in tr]
 y=ymat(labels,pair,ds,ids,'y');f=ymat(labels,pair,ds,ids,'f')[:,1:]
 assert np.array_equal(z['y'],y[te]) and np.array_equal(z['f'],f[te])
 assert np.all((y[:,1:]!=y[:,[0]]) <= f)
 deltas=[]
 for j in range(3):
  g=sum(int(y[i,j+1]>y[i,0]) for i in tr);h=sum(int(y[i,j+1]<y[i,0]) for i in tr);fl=sum(int(f[i,j]) for i in tr)
  assert g==z['fit_gain'][j] and h==z['fit_harm'][j] and fl==z['fit_flip_n'][j] and fl>=g+h
  deltas.append((g-h)/(fl+2))
 assert np.allclose(deltas,z['delta'],rtol=0,atol=1e-15)
 pc=dict(np.load(P10/'results'/pair/ds/'train_cost_panel_matrix.npz',allow_pickle=False));fitset=set(fitids)
 take=[j for j,i in enumerate(pc['ids']) if i in fitset]
 assert set(z['fit_panel_ids'])=={str(pc['ids'][j]) for j in take} and not set(z['fit_panel_ids']).intersection(held)
 manual_cost=np.array([sum(float(pc['latency_ms'][i,a]) for i in take)/len(take) for a in range(4)])
 assert np.allclose(manual_cost,z['cost_proxy_ms'],atol=1e-9,rtol=1e-12)
 for name in cfg['OOF']['methods']+['query_independent']:
  for na in [3,4]:
   for li,l in enumerate(cfg['lambdas']):
    # Scalar implementation checks every choice in the first required held-out fold.
    for i in range(len(te)):
     if name=='FFR_E0':g=[0]+[float(z['m'][i,j]*deltas[j]) for j in range(3)]
     elif name=='IndepLR':g=[float(z['p'][i,j]-z['p'][i,0]) for j in range(4)]
     elif name=='FFR_constant_flip_rate':g=[0]+[float(z['constant_flip_rate'][j]*deltas[j]) for j in range(3)]
     elif name=='FFR_true_flip_DIAGNOSTIC':g=[0]+[float(z['f'][i,j]*deltas[j]) for j in range(3)]
     else:g=y[tr].mean(0).tolist()
     score=[g[a]-l*float(z['cost_proxy_ms'][a])/float(z['c_ref_ms']) for a in range(na)]
     choice=max(range(na),key=lambda a:score[a]);saved=z[name+'_choices'+str(na)]
     actual=saved[li] if name=='query_independent' else saved[i,li]
     assert choice==actual,(name,na,li,i,choice,actual)
 if vec is not None:
  analyzer=vec.build_analyzer();df=collections.Counter()
  for i in tr:df.update(set(analyzer(texts[i])))
  manual=np.array([np.log((1+len(tr))/(1+df[t]))+1 for t,j in sorted(vec.vocabulary_.items(),key=lambda x:x[1])])
  assert np.allclose(manual,vec.idf_,rtol=1e-12,atol=1e-12)
  assert all(df[t]>=cfg['tfidf']['min_df'] for t in vec.vocabulary_)
 return {'passed':True,'pair':pair,'dataset':ds,'family':family,'fold':k,'formal_fold_reused':True,'head_probability_checks':'each official head receipt','split_disjoint':True,'labels_and_direction_recomputed':True,'cost_panel_membership_and_mean_checked':True,'all_first_fold_choices_scalar_verified':True,'training_only_IDF_recomputed_without_refitting':vec is not None,'no_new_fit':True,'CPU_in_main_ledger':True}

def readtable(name):return list(csv.DictReader((O/'summary'/name).open()))
def number(v):return None if v=='NA' else float(v)
def main():
 assert os.environ.get('P2_BOUNDED_SUPERVISED')==O.name and os.environ.get('PBS_JOBID')
 checks=[]
 for path,key in [('frozen_config.json','config_sha256'),('folds/group_folds.csv','folds_sha256'),('folds/groups.csv','groups_sha256'),('folds/target_counts.csv','target_counts_sha256'),('evidence/source_manifest.json','source_manifest_sha256')]:assert sha(O/path)==freeze[key]
 checks.append('All frozen hashes unchanged')
 folds=list(csv.DictReader((O/'folds/group_folds.csv').open()));groups=collections.defaultdict(set)
 for r in folds:groups[r['dataset'],r['group_id']].add(int(r['fold']))
 assert all(len(v)==1 for v in groups.values())
 checks.append('Duplicate groups remain disjoint across folds')
 receipts=[json.loads(s) for s in (O/'fit_receipts.jsonl').read_text().splitlines()];starts=[r for r in receipts if r['event']=='START_LR'];heads={r['key']:r for r in receipts if r['event']=='HEAD_COMPLETE'}
 assert sum(k.startswith('baseline/') for k in heads)==8 and sum(k.startswith('OOF/') for k in heads)==280 and len(starts)<=320
 assert all(r['numerical_probability_check'] and r['protocol_sha256']==freeze['config_sha256'] for r in heads.values())
 for r in csv.DictReader((O/'MODEL_INDEX.tsv').open(),delimiter='\t'):assert sha(r['path'])==r['sha256']
 assert json.loads((O/'evidence/first_baseline_numerical_validation.json').read_text())['probability_sigmoid_check']
 assert json.loads((O/'evidence/first_oof_numerical_validation.json').read_text())['passed']
 checks.append('8 baseline and 280 OOF formal heads and their hashes/first numerical checks verified')
 tables={name:readtable(name) for name in ['baseline_update_summary.csv','baseline_panel_replay.csv','oof_predictions.csv','flip_metrics.csv','decision_metrics.csv','paired_method_differences.csv','overhead_headroom.csv','invalid_analysis.csv','direction_diagnostics.csv']}
 expected={'baseline_update_summary.csv':112,'baseline_panel_replay.csv':256,'oof_predictions.csv':18340,'flip_metrics.csv':576,'decision_metrics.csv':5712,'paired_method_differences.csv':5712,'overhead_headroom.csv':5712,'invalid_analysis.csv':720,'direction_diagnostics.csv':120}
 for name,n in expected.items():assert len(tables[name])==n,(name,len(tables[name]),n)
 checks.append('All planned combinations/folds/actions/lambdas/scopes and table counts complete')
 keys=[(r['pair'],r['dataset'],r['family'],r['id']) for r in tables['oof_predictions.csv']];assert len(keys)==len(set(keys))
 foldlookup={(r['dataset'],r['id']):int(r['fold']) for r in folds}
 for r in tables['oof_predictions.csv']:assert int(r['fold'])==foldlookup[r['dataset'],r['id']]
 checks.append('One held-out prediction per question and representation/model pair')
 flip=tables['flip_metrics.csv'];na=[r for r in flip if r['pair']=='large' and r['dataset']=='arc' and r['fold']=='4' and r['action']=='A' and r['scope']=='all']
 assert len(na)==4 and all(r['ROC_AUC']==r['AP']=='NA' and r['positive']=='0' and r['log_loss']!='NA' for r in na)
 checks.append('Frozen large ARC fold 4 f_A has AUC/AP NA and finite log loss')
 from analyze_stage import collect
 drows=tables['decision_metrics.csv'];prows=tables['paired_method_differences.csv'];hrows=tables['overhead_headroom.csv']
 def key(r):return (r['pair'],r['dataset'],r['family'],r['fold'],r['n_actions'],r['lambda'])
 dm={(key(r),r['method']):r for r in drows}
 for pair,ds in cfg['combinations']:
  for family in cfg['features']:
   b,_=collect(pair,ds,family)
   for r in [x for x in drows if x['pair']==pair and x['dataset']==ds and x['family']==family]:
    mask=np.ones(len(b['ids']),bool) if r['fold']=='pooled' else b['fold']==int(r['fold']);l=float(r['lambda']);li=cfg['lambdas'].index(l);na0=int(r['n_actions']);name=r['method'];n=int(mask.sum())
    choice=np.full(n,A.index(name[-1])) if name.startswith('fixed_') else b[name+'_choices'+str(na0)][mask,li]
    correct=b['y'][mask][np.arange(n),choice];cost=b['cost_proxy_ms'][mask][np.arange(n),choice];ref=b['c_ref_ms'][mask]
    assert abs(float(r['accuracy'])-sum(int(v) for v in correct)/n)<1e-12
    assert int(r['gain_count_vs_R'])-int(r['harm_count_vs_R'])==int(correct.sum()-b['y'][mask,0].sum())
    assert abs(sum(float(r['select_'+a]) for a in A[:na0])-1)<1e-12
    if l:assert abs(float(r['proxy_utility'])-sum(float(c)-l*float(m)/float(q) for c,m,q in zip(correct,cost,ref))/n)<1e-12
    else:assert r['proxy_utility']=='NA'
 for r in prows:
  a=dm[key(r),r['left']];b=dm[key(r),r['right']];n=int(r['n'])
  assert abs(float(r['accuracy_difference'])-(float(a['accuracy'])-float(b['accuracy'])))<1e-12
  assert abs(float(r['accuracy_difference'])-(int(r['left_correct_right_wrong'])-int(r['left_wrong_right_correct']))/n)<1e-12
  if float(r['lambda']):assert abs(float(r['proxy_utility_difference'])-(float(a['proxy_utility'])-float(b['proxy_utility'])))<1e-12
 for r in hrows:
  l=float(r['lambda'])
  if l:assert np.isclose(float(r['admissible_added_ms'])*l*float(r['mean_inverse_c_ref_per_ms']),float(r['proxy_utility_difference']),rtol=1e-10,atol=1e-12)
  else:assert r['admissible_added_ms']=='NA'
 checks.append('Every decision/paired difference recomputed from official predictions and all overhead identities verified')
 # Pooled estimands must be question-weighted, not averages of unequal fold means.
 for r in [x for x in drows if x['fold']=='pooled']:
  subset=[dm[((r['pair'],r['dataset'],r['family'],str(k),r['n_actions'],r['lambda']),r['method'])] for k in range(5)]
  for metric in ['accuracy','proxy_action_ms']+(['proxy_utility'] if float(r['lambda']) else []):assert abs(float(r[metric])-sum(float(x[metric])*int(x['n']) for x in subset)/int(r['n']))<1e-9
 checks.append('Pooled metrics weighted by question counts across unequal folds')
 inv=tables['invalid_analysis.csv']
 for r in [x for x in inv if x['validity_scope']=='all']:
  part=[x for x in inv if all(x[k]==r[k] for k in ['pair','dataset','family','fold','action']) and x['validity_scope']!='all']
  for field in ['n','flip_count','gain_count','harm_count','zero_gain_flip_count']:assert sum(int(x[field]) for x in part)==int(r[field])
 checks.append('INVALID partition counts reconcile without dropped questions')
 warnings=[{'key':k,'warnings':v['warnings'],'iterations':v['iterations']} for k,v in heads.items() if v['warnings']]
 result={'status':'NUMERICAL_VALIDATION_PASSED','passed':True,'job_id':os.environ['PBS_JOBID'],'checks':checks,'table_rows':expected,'LR_attempts':len(starts),'completed_baseline_C_heads':8,'completed_OOF_heads':280,'warnings':warnings,'versions':{'numpy':np.__version__,'scipy':scipy.__version__,'sklearn':sklearn.__version__,'joblib':joblib.__version__},'paper_compiled':False,'no_significance_testing_or_point_selection':True}
 save(O/'NUMERICAL_VALIDATION.json',result);print(json.dumps(result,ensure_ascii=False),flush=True)
if __name__=='__main__':main()
