from common import *
compute();assert (P/'DEV_ROUTES_FREEZE.json').exists()
import numpy as np
from scipy.stats import spearmanr,beta
from sklearn.metrics import roc_auc_score,average_precision_score
CFG=read(P/'frozen_config.json');DEP=read(P/'models/deployment.json');ids=read(P/'splits/dev_ids.json');N=len(ids)
def csvread(p):return list(csv.DictReader(Path(p).open()))
def typed(r):
 out={}
 for k,v in r.items():
  if v=='':out[k]=None
  elif v in ['True','False']:out[k]=v=='True'
  else:
   try:out[k]=float(v)
   except (ValueError,TypeError):out[k]=v
 return out
# First association of this run's routes with old fixed outputs and gold.
labels=jl(OLD/'records/dev_evaluation_labels.jsonl');assert [r['id'] for r in labels]==ids
fixed={};evidence=[]
request_ix={(r['id'],r['action']):r for r in csvread(P/'inputs/DEV_FIXED_REQUEST_INDEX.csv')}
for action in ['R','T']:
 rows=[]
 for i in ids:
  ix=request_ix[i,action];assert sha(ix['path'])==ix['sha256'];r=read(ix['path']);assert r['id']==i and r['policy']==action and not r['runtime_error'];rows.append(r)
 fixed[action]=rows
for j,i in enumerate(ids):
 R,T=fixed['R'][j],fixed['T'][j]
 assert R['gold']==T['gold'] and R['y']==labels[j]['y_R'] and T['y']==labels[j]['y_T']
 assert (R['parsed']['answer'] or 'INVALID')==labels[j]['o_R'] and (T['parsed']['answer'] or 'INVALID')==labels[j]['o_T']
 evidence.append({**labels[j],'gold':R['gold']})
writejl(P/'records/dev_evaluation_labels.jsonl',evidence)
yR=np.array([r['y_R'] for r in labels]);yT=np.array([r['y_T'] for r in labels]);d=np.array([r['o_R']!=r['o_T'] for r in labels])
cr=np.array([r['latency_ms'] for r in fixed['R']]);ct=np.array([r['latency_ms'] for r in fixed['T']]);assert d.sum()==72 and yT.sum()==645
routes=jl(P/'records/dev_scored_routes.jsonl');assert [r['id'] for r in routes]==ids
grid=jl(P/'records/dev_grid_routes.jsonl');thr=read(P/'thresholds/new_thresholds.json')
oldmain={r['family']:typed(r) for r in csvread(OLD/'summary/main_dev.csv')}
main=[{**oldmain[f],'family':g,'result_identity':'reused frozen reference'} for f,g in [('D','D'),('R','R2100')]]
oldper=jl(OLD/'records/dev_per_question.jsonl');refper={f:[r for r in oldper if r['family']==f] for f in ['D','R','Fixed_R','Fixed_Text']}
for f,rows in refper.items():assert [r['id'] for r in rows]==ids
writejl(P/'records/reused_reference_per_question.jsonl',[{**r,'family':'R2100' if f=='R' else f} for f,rows in refper.items() for r in rows])
def metrics(mask,c):
 n=int(mask.sum());changed=mask&d;k=int(changed.sum());y=np.where(mask,yR,yT)
 return {'N':N,'n_R':n,'coverage':float(mask.mean()),'changed':k,'conditional_risk':float(k/n) if n else None,'marginal_change':k/N,'benefit':int((changed&(yR>yT)).sum()),'harm':int((changed&(yR<yT)).sum()),'neutral_change':int((changed&(yR==yT)).sum()),'correct':int(y.sum()),'accuracy':float(y.mean()),'accuracy_diff_Text':float((y-yT).mean()),'mean_cost_ms':float(c.mean()),'median_cost_ms':float(np.median(c)),'p95_cost_ms':float(np.quantile(c,.95)),'net_saving_vs_Text_ms':float((ct-c).mean()),'net_saving_vs_Text_fraction':float((ct-c).mean()/ct.mean()),'U':float(y.mean()-.01*c.mean()/262.462515),'risk_CP95_descriptive_low':float(beta.ppf(.025,k,n-k+1)) if n and k else 0. if n else None,'risk_CP95_descriptive_high':float(beta.ppf(.975,k+1,n-k)) if n and k<n else 1. if n else None}
perq=[];arrays={};curves=[]
for f in NEW:
 mask=np.array([r['route'][f]=='R' for r in routes]);overhead=np.array([r['required_overhead_ms'][f] for r in routes]);action=np.where(mask,cr,ct);c=action+overhead;y=np.where(mask,yR,yT)
 arrays[f]=np.column_stack([y,c,y-.01*c/262.462515])
 cal=DEP[f]['calibration'];main.append({'split':'dev','family':f,'q':DEP[f]['q'],'mode':DEP[f]['mode'],**metrics(mask,c),'calibration_p_value':cal['p_value'] if cal else None,'calibration_CP_upper_0_999':cal['CP_upper_0_999'] if cal else None,'result_identity':'new control + historical complete requests; component recomposition'})
 for j,i in enumerate(ids):
  D=refper['D'][j]
  perq.append({'id':i,'family':f,'route':'R' if mask[j] else 'T','d':int(d[j]),'changed':int(mask[j]&d[j]),'y':int(y[j]),'y_Text':int(yT[j]),'overhead_ms':float(overhead[j]),'historical_full_request_ms':float(action[j]),'total_cost_ms':float(c[j]),'U':float(arrays[f][j,2]),'accuracy_difference_D':int(y[j]-D['y']),'cost_difference_D_ms':float(c[j]-D['total_cost_ms']),'U_difference_D':float(arrays[f][j,2]-D['U'])})
 for qi,q in enumerate(CFG['q_grid']):
  m=np.array([r['routes'][f][qi] for r in grid],bool);assert np.array_equal(m,np.array([r['scores'][f]<=threshold_value(thr[f][qi]) for r in routes]))
  cgrid=np.where(m,cr,ct)+(np.array([r['measured_selective_overhead_ms'][f] for r in routes]) if q<1 else 0)
  curves.append({'split':'dev','family':f,'q':q,'cal_accepted':q in DEP[f]['accepted_q'],'final_deployment':q==DEP[f]['q'],**metrics(m,cgrid),'identity':'prespecified descriptive curve; never used for selection'})
for f in ['Fixed_R','Fixed_Text']:main.append({**oldmain[f],'result_identity':'reused fixed reference'})
assert len(perq)==2226;writejl(P/'records/dev_per_question_new.jsonl',perq);csvout(P/'summary/main_dev.csv',main)
for r in csvread(OLD/'summary/grid_curves.csv'):
 if r['family'] in ['D','R'] and r['split']=='dev':curves.append({**typed(r),'family':'R2100' if r['family']=='R' else r['family'],'identity':'reused descriptive curve'})
csvout(P/'summary/grid_curves_dev.csv',curves)
# Scores are fixed; all ranking measures predict the same machine disagreement target.
newscore={s:jl(P/f'records/{s}_scores.jsonl') for s in ['fit','cal']}
newscore['dev']=[{'id':r['id'],**r['scores']} for r in routes]
oldscore={s:jl(OLD/f'records/{s}_scores.jsonl') for s in ['fit','cal']}
oldscore['dev']=[{'id':r['id'],**r['scores']} for r in jl(OLD/'records/dev_scored_routes.jsonl')]
ds={'fit':np.array([r['d'] for r in jl(P/'inputs/candidate_fit.jsonl')]),'cal':np.array([r['d'] for r in jl(P/'inputs/candidate_cal.jsonl')]),'dev':d}
ranking=[];allscore={};oldrank={(r['split'],r['family']):typed(r) for r in csvread(OLD/'summary/ranking.csv')}
for s in ['fit','cal','dev']:
 assert [r['id'] for r in newscore[s]]==[r['id'] for r in oldscore[s]]
 allscore[s]={f:np.array([r[f] for r in newscore[s]]) for f in NEW}
 allscore[s].update({f:np.array([r[g] for r in oldscore[s]]) for f,g in [('D','D'),('R2100','R')]})
 for f,vals in allscore[s].items():
  rho=float(spearmanr(vals,allscore[s]['D']).statistic)
  r=oldrank[s,'R' if f=='R2100' else f] if f in ['D','R2100'] else {'N':len(vals),'d_count':int(ds[s].sum()),'AUROC_disagreement':float(roc_auc_score(ds[s],vals)),'AP_disagreement':float(average_precision_score(ds[s],vals)),'AP_random_baseline':float(ds[s].mean()),'in_sample':s=='fit'}
  ranking.append({**r,'split':s,'family':f,'Spearman_D':rho})
csvout(P/'summary/ranking.csv',ranking)
matched=[]
for anchor in FAMILIES:
 n=int(next(r for r in main if r['family']==anchor)['n_R'])
 for f in FAMILIES:
  ix=np.argsort(allscore['dev'][f],kind='stable')[:n]
  matched.append({'anchor_frozen_family':anchor,'family':f,'n_R':n,'coverage':n/N,'changed_at_exact_n':int(d[ix].sum()),'risk_at_exact_n':float(d[ix].mean()) if n else None,'tie_rule':'frozen dev order; diagnosis only'})
csvout(P/'summary/coverage_matched_descriptive.csv',matched)
caltests=[typed(r) for r in csvread(P/'summary/calibration_comparison_100.csv')];diagnostics=[]
for f in FAMILIES:
 tests=[r for r in caltests if r['family']==f];best=min(tests,key=lambda r:r['p_value'])
 diagnostics.append({'family':f,'accepted_q':DEP[f]['accepted_q'],'deployed_q':DEP[f]['q'],'minimum_p_test':best,'max_zero_change_n':int(max([r['n_R'] for r in tests if r['changed']==0]+[0])),'max_empirical_risk_le_alpha_n':int(max([r['n_R'] for r in tests if r['conditional_risk'] is not None and r['conditional_risk']<=.05]+[0])),'zero_change_min_n_for_acceptance':135})
save(P/'summary/calibration_diagnostics.json',diagnostics)
# Use one shared seed0 index array. Old D bootstrap means and old D/R intervals are reused.
oldboot=np.load(OLD/'summary/bootstrap_joint_means.npz',allow_pickle=False);paths=oldboot['paths'].tolist();Dboot=oldboot['means'][:,paths.index('D'),:]
assert oldboot['seed']==0 and oldboot['replicates']==2000
bootidx=np.random.default_rng(0).integers(0,N,size=(2000,N));diffs=[];bootnew=[]
Dobs=np.array([[r['y'],r['total_cost_ms'],r['U']] for r in refper['D']]).mean(axis=0)
for f in NEW:
 means=arrays[f][bootidx].mean(axis=1);bootnew.append(means);diff=means-Dboot;obs=arrays[f].mean(axis=0)-Dobs
 for k,metric in enumerate(['accuracy','mean_cost_ms','U']):
  lo,hi=np.quantile(diff[:,k],[.025,.975]);diffs.append({'policy':f,'reference':'D','metric':metric,'difference':float(obs[k]),'CI95_descriptive_low':float(lo),'CI95_descriptive_high':float(hi),'replicates':2000,'seed':0,'interpretation':'descriptive on exposed population; fixed models/thresholds; no equivalence/noninferiority'})
csvout(P/'summary/bootstrap_new_vs_D.csv',diffs)
np.savez_compressed(P/'summary/bootstrap_new_joint_means.npz',families=np.array(NEW),means=np.stack(bootnew,axis=1),seed=0,replicates=2000,index_sha256=hashlib.sha256(bootidx.tobytes()).hexdigest())
csvout(P/'summary/bootstrap_reused_D_R2100.csv',[r for r in csvread(OLD/'summary/paired_bootstrap.csv') if r['policy']=='D' and r['reference']=='R'])
save(P/'summary/BOOTSTRAP_PROVENANCE.json',{'old_means_path':str(OLD/'summary/bootstrap_joint_means.npz'),'old_means_sha256':sha(OLD/'summary/bootstrap_joint_means.npz'),'index_sha256':hashlib.sha256(bootidx.tobytes()).hexdigest(),'replicates':2000,'seed':0,'new_bootstrap_models':NEW,'old_D_R_comparison_recomputed':False,'joint_question_order_sha256':sha(P/'splits/dev_ids.json')})
def dist(a):
 a=np.array(a,float);return {'n':len(a),'mean':float(a.mean()),'min':float(a.min()),'p05':float(np.quantile(a,.05)),'median':float(np.median(a)),'p95':float(np.quantile(a,.95)),'max':float(a.max()),'sum':float(a.sum())}
probes=jl(P/'records/probe_records.jsonl');assert len(probes)==4208
train_native={r['id']:r['o_R'] for r in jl(read(OLD/'frozen_config.json')['train_labels_source'])}
native={**train_native,**{r['id']:r['o_R'] for r in labels}}
probe_diag={};agreement_rows=[];timing=[]
for s in ['fit','cal','dev','all']:
 rows=[r for r in probes if s=='all' or r['split']==s];agreement=[r['argmax_probe_label']==native[r['id']] for r in rows]
 probe_diag[s]={'N':len(rows),'argmax_agrees_native_R_count':int(sum(agreement)),'argmax_agrees_native_R_fraction':sum(agreement)/len(rows),'label_union_mass':dist([r['label_union_mass'] for r in rows]),'probe_core_ms':dist([r['probe_core_ms'] for r in rows])}
for r in probes:agreement_rows.append({'id':r['id'],'split':r['split'],'argmax_probe_label':r['argmax_probe_label'],'o_R':native[r['id']],'agrees':r['argmax_probe_label']==native[r['id']],'label_union_mass':r['label_union_mass']})
writejl(P/'records/probe_native_R_diagnostics.jsonl',agreement_rows);save(P/'summary/probe_diagnostics.json',probe_diag)
for s in ['fit','cal','dev']:
 rows=[r for r in probes if r['split']==s]
 for key in ['tokenization_prefix_ms','prepare_transfer_ms','prefill_projection_ms','label_distribution_ms','probe_core_ms','ProbeMax_score_ms','ProbeEntropy_score_ms','diagnostic_mass_ms']:
  timing.append({'split':s,'component':key,**dist([r[key] for r in rows])})
 words=jl(P/f'records/word_{s}_scores.jsonl')
 for key in ['text_ms','vectorize_ms','LR_ms','feature_head_ms']:
  timing.append({'split':s,'component':'WordD_'+key,**dist([r[key] for r in words])})
for f in NEW:timing.append({'split':'dev','component':f+'_measured_selective_overhead_ms',**dist([r['measured_selective_overhead_ms'][f] for r in routes])})
csvout(P/'summary/component_timing.csv',timing)
oldcost=read(E2E/'COST_FREEZE.json');rmean,tmean=oldcost['cost_ms'][:2];historical=read(OLD/'summary/computation_ledger.json')
ledger=[]
for f in FAMILIES:
 probe=f.startswith('Probe');gold=f=='R2100';fitreq=0 if probe else 2100 if gold else 4200
 ledger.append({'family':f,'unique_fit_gold':2100 if gold else 0,'machine_fit_d':2100 if f in ['D','WordD'] else 0,'machine_cal_d':1366,'fit_R_Text_protocol_requests':fitreq,'cal_R_Text_protocol_requests':2732,'complete_learning_protocol_requests':fitreq+2732,'offline_probe_questions':3466 if probe else 0,'offline_E1_questions':3466 if f in ['D','R2100'] else 0,'offline_word_questions':3466 if f=='WordD' else 0,'estimated_historical_protocol_seconds':(1366*(rmean+tmean)+(0 if probe else 2100*rmean if gold else 2100*(rmean+tmean)))/1000,'historical_E1_measured_seconds':historical['historical_train_feature_wall_seconds'] if f in ['D','R2100'] else 0,'new_human_gold':0,'new_R_Text_protocol_requests':0,'request_count_is_not_forward_count':True})
csvout(P/'summary/supervision_acquisition.csv',ledger)
save(P/'summary/computation_ledger.json',{'new_prefill_attempts':4208,'new_probe_success':4208,'new_LR_fit_attempts':1,'new_calibration_tests':60,'reused_reference_tests':40,'new_frozen_dev_policy_question_evaluations':2226,'descriptive_grid_policy_question_rows':60*742,'new_human_annotations':0,'new_protocol_requests':0,'helper_forward':0,'answer_generation':0,'new_probe_core_seconds':sum(r['probe_core_ms'] for r in probes)/1000,'new_probe_GPU_prefill_projection_event_seconds':sum(r['GPU_prefill_projection_event_ms'] for r in probes)/1000,'new_probe_score_seconds':{f:sum(r[f+'_score_ms'] for r in probes)/1000 for f in NEW[:2]},'new_probe_diagnostic_mass_seconds':sum(r['diagnostic_mass_ms'] for r in probes)/1000,'startup':read(P/'evidence/model_startup.json'),'word_fit':read(P/'models/WordD_receipt.json'),'word_feature_head_seconds':{s:sum(r['feature_head_ms'] for r in jl(P/f'records/word_{s}_scores.jsonl'))/1000 for s in ['fit','cal','dev']},'full_protocol_estimate_source':str(E2E/'COST_FREEZE.json'),'actual_facility_charge':'pending lookup; not inferred from component sums','timing_identity':'Each probe deployment pays its own entire core+score+selector; shared experimental distribution is not online free; fixed policies remove unnecessary features'})
csvout(P/'summary/historical_e2e_reference.csv',csvread(OLD/'summary/historical_e2e_reference.csv'))
assert [r for r in main if r['family']=='D'][0]['correct']==643 and [r for r in main if r['family']=='R2100'][0]['correct']==644
assert all(len([r for r in perq if r['family']==f])==742 for f in NEW)
freeze('ANALYSIS_COMPLETE.json',[P/'summary/main_dev.csv',P/'summary/ranking.csv',P/'summary/bootstrap_new_vs_D.csv',P/'records/dev_per_question_new.jsonl',P/'summary/probe_diagnostics.json'],evaluations=2226,cal_tests_new=60,original_reference_working_points_unchanged=True)
print(json.dumps(main,ensure_ascii=False),flush=True)
