from numerics import *
from scipy.stats import hypergeom
from sklearn.metrics import roc_auc_score,average_precision_score
import collections
assert (P/'DEV_ROUTES_FREEZE.json').exists()
policies=read(P/'models/deployment.json');thresholds=read(P/'models/thresholds.json');families=CFG['families'];qgrid=CFG['q_grid']
train_labels={r['id']:r for r in jl(CFG['train_labels_source'])};ids=read(P/'splits/dev_ids.json')
# First dev answer/gold association in the new computation, AFTER scored routes hash.
gold={r['id']:r for r in jl(CFG['dev_gold_source'])}
source_index={(r['phase'],r['id'],r['policy']):r for r in csv.DictReader((E/'REQUEST_INDEX.csv').open())}
dev_labels=[];cr=[];ct=[];source_receipt=[]
for j,i in enumerate(ids):
 pair=[]
 for a in ['R','T']:
  p=E/f'records/dev/{j:04d}_{a}.json';r=read(p)
  assert r['id']==i and r['policy']==a and not r['runtime_error'] and r['config_sha256']==sha(E/'frozen_config.json')
  assert r['parsed']['parser_sha256']==CFG['parser_sha256'] if isinstance(r['parsed'],dict) and 'parser_sha256' in r['parsed'] else True
  ix=source_index['dev',i,a];assert sha(p)==ix['sha256']
  source_receipt.append({'id':i,'action':a,'path':str(p),'sha256':sha(p)})
  pair.append(r)
 R,T=pair
 # frozen records already contain the V2 parsed option and y; no rescoring.
 def opt(r):return (r['parsed']['answer'] or 'INVALID') if isinstance(r['parsed'],dict) else r['parsed']
 assert R['gold']==T['gold']
 g=gold[i].get('gold',gold[i].get('answerKey',gold[i].get('answer')));assert g==R['gold']
 dev_labels.append({'id':i,'o_R':opt(R),'o_T':opt(T),'y_R':int(R['y']),'y_T':int(T['y']),'invalid_R':int(R['INVALID']),'invalid_T':int(T['INVALID'])})
 cr.append(R['latency_ms']);ct.append(T['latency_ms'])
writejl(P/'records/dev_evaluation_labels.jsonl',dev_labels);csvout(P/'inputs/DEV_FIXED_REQUEST_INDEX.csv',source_receipt)
cr=np.array(cr);ct=np.array(ct);new=jl(P/'records/dev_scored_routes.jsonl');assert [r['id'] for r in new]==ids
grid_routes=jl(P/'records/dev_grid_routes.jsonl')
caltests=list(csv.DictReader((P/'summary/calibration_100.csv').open()));calmap={(r['family'],float(r['q'])):r for r in caltests}
populations={};labels={};scores={}
for split in ['fit','cal','dev']:
 ix=read(P/f'splits/{split}_ids.json');rows=dev_labels if split=='dev' else [train_labels[i] for i in ix]
 yR=np.array([r['y_R'] for r in rows]);yT=np.array([r['y_T'] for r in rows]);d=np.array([r['o_R']!=r['o_T'] for r in rows]);vR=np.array([r['invalid_R'] for r in rows],bool);vT=np.array([r['invalid_T'] for r in rows],bool)
 assert np.all(yT-yR<=d.astype(int));assert np.all(yT[~d]==yR[~d])
 labels[split]=(yR,yT,d,vR,vT)
 populations[split]={'split':split,'N':len(ix),'d_count':int(d.sum()),'d_rate':float(d.mean()),'R_correct':int(yR.sum()),'Text_correct':int(yT.sum()),'both_INVALID':int((vR&vT).sum()),'R_only_INVALID':int((vR&~vT).sum()),'Text_only_INVALID':int((vT&~vR).sum()),'both_valid':int((~vR&~vT).sum()),'Text_to_R_benefit':int(((yR>yT)&d).sum()),'Text_to_R_harm':int(((yR<yT)&d).sum()),'neutral_change':int(((yR==yT)&d).sum())}
 if split=='dev':scores[split]={f:np.array([r['scores'][f] for r in new]) for f in families}
 else:
  sr=jl(P/f'records/{split}_scores.jsonl');assert [r['id'] for r in sr]==ix
  scores[split]={f:np.array([r[f] for r in sr]) for f in families if f in sr[0]}
 # Fit coins were not prespecified and are not invented post hoc; query-free expectation shown instead.
csvout(P/'summary/populations.csv',populations.values());save(P/'summary/populations.json',populations)

def metrics(split,mask):
 yR,yT,d,vR,vT=labels[split];n=int(mask.sum());change=mask&d;k=int(change.sum());y=np.where(mask,yR,yT);vr=np.where(mask,vR,vT)
 low,high=risk_interval(n,k)
 return {'N':len(d),'n_R':n,'coverage':float(mask.mean()),'changed':k,'conditional_risk':float(k/n) if n else None,'marginal_change':float(k/len(d)),'benefit':int((change&(yR>yT)).sum()),'harm':int((change&(yR<yT)).sum()),'neutral_change':int((change&(yR==yT)).sum()),'correct':int(y.sum()),'accuracy':float(y.mean()),'accuracy_diff_Text':float((y-yT).mean()),'INVALID_selected':int(vr.sum()),'routed_both_INVALID':int((mask&vR&vT).sum()),'routed_R_only_INVALID':int((mask&vR&~vT).sum()),'routed_Text_only_INVALID':int((mask&~vR&vT).sum()),'routed_both_valid':int((mask&~vR&~vT).sum()),'risk_CP95_descriptive_low':low,'risk_CP95_descriptive_high':high}
def deploymask(split,f):
 p=policies[f];n=populations[split]['N']
 if p['mode']=='fixed_T':return np.zeros(n,bool)
 if p['mode']=='fixed_R':return np.ones(n,bool)
 return scores[split][f]<=threshold_value(p['threshold'])
def coststats(c,y):return {'mean_cost_ms':float(np.mean(c)),'median_cost_ms':float(np.median(c)),'p95_cost_ms':float(np.quantile(c,.95)),'net_saving_vs_Text_ms':float(np.mean(ct-c)),'net_saving_vs_Text_fraction':float(np.mean(ct-c)/ct.mean()),'U':float(np.mean(y)-.01*np.mean(c)/262.462515)}
main=[];allpop=[];perq=[];route_arrays={};cost_arrays={};accuracy_arrays={};ranking=[];curves=[];match=[]
for split in ['fit','cal','dev']:
 yR,yT,d,vR,vT=labels[split];N=len(d)
 for f,vals in scores[split].items():
  ranking.append({'split':split,'family':f,'N':N,'d_count':int(d.sum()),'AUROC_disagreement':float(roc_auc_score(d,vals)),'AP_disagreement':float(average_precision_score(d,vals)),'AP_random_baseline':float(d.mean()),'in_sample':split=='fit'})
 for f in families+['Fixed_R','Fixed_Text']:
  if f=='Random' and split=='fit' and policies[f]['mode']=='selective':continue
  mask=np.ones(N,bool) if f=='Fixed_R' else np.zeros(N,bool) if f=='Fixed_Text' else deploymask(split,f)
  cal=policies[f]['calibration'] if f in families else None
  m={'split':split,'family':f,'q':policies[f]['q'] if f in families else None,'mode':policies[f]['mode'] if f in families else f,**metrics(split,mask),'calibration_p_value':cal['p_value'] if cal else None,'calibration_CP_upper_0_999':cal['CP_upper_0_999'] if cal else None,'calibration_accepted':bool(cal),'cost_identity':'new feature timing + historical fixed full request component recomposition' if split=='dev' else 'NA'}
  if split=='dev':
   feat=np.array([r['feature_ms_charged'][f] for r in new]) if f in families else np.zeros(N)
   head=np.array([r['head_selector_ms_charged'][f] for r in new]) if f in families else np.zeros(N)
   action=np.where(mask,cr,ct);c=feat+head+action;y=np.where(mask,yR,yT)
   m.update(coststats(c,y));main.append(m);route_arrays[f]=mask;cost_arrays[f]=c;accuracy_arrays[f]=y
   for j,i in enumerate(ids):perq.append({'id':i,'family':f,'route':'R' if mask[j] else 'T','d':int(d[j]),'changed':int(mask[j]&d[j]),'y':int(y[j]),'y_Text':int(yT[j]),'feature_ms':float(feat[j]),'head_selector_ms':float(head[j]),'historical_full_request_ms':float(action[j]),'total_cost_ms':float(c[j]),'saving_vs_Text_ms':float(ct[j]-c[j]),'U':float(y[j]-.01*c[j]/262.462515)})
  allpop.append(m)
 for f,vals in scores[split].items():
  for qi,q in enumerate(qgrid):
   mask=vals<=threshold_value(thresholds[f][qi]);n=int(mask.sum());k=int((mask&d).sum());accepted=calmap[f,q]['accepted']=='True';selected=policies[f]['q']==q
   r={'split':split,'family':f,'q':q,'threshold':thresholds[f][qi],'cal_accepted':accepted,'final_deployment':selected,**metrics(split,mask)}
   if split=='dev':
    assert np.array_equal(mask,np.array([z['routes'][f][qi] for z in grid_routes],bool))
    # Each diagnostic grid policy pays only its own required features/head; q=1 is constant.
    feat=np.array([z['feature_ms'] for z in new]) if f!='Random' and q<1 else np.zeros(N)
    head=np.array([z['head_selector_ms_measured'][f] for z in new]) if q<1 else np.zeros(N)
    r.update(coststats(np.where(mask,cr,ct)+feat+head,np.where(mask,yR,yT)))
    r.update(random_expected_changes=float(n*d.mean()),random_hypergeom95_low=int(hypergeom.ppf(.025,N,int(d.sum()),n)),random_hypergeom95_high=int(hypergeom.ppf(.975,N,int(d.sum()),n)))
   curves.append(r)
csvout(P/'summary/deployment_all_populations.csv',allpop);csvout(P/'summary/main_dev.csv',main);csvout(P/'summary/ranking.csv',ranking);csvout(P/'summary/grid_curves.csv',curves);writejl(P/'records/dev_per_question.jsonl',perq)
# Same-coverage ranking diagnostic, exact n, stable tie handling: never a deployment rule.
d=labels['dev'][2];N=len(d)
for f in families:
 n=int(route_arrays[f].sum());r={'anchor_frozen_family':f,'n_R':n,'coverage':n/N,'random_expected_changes':n*float(d.mean()),'random_hypergeom95_low':int(hypergeom.ppf(.025,N,int(d.sum()),n)),'random_hypergeom95_high':int(hypergeom.ppf(.975,N,int(d.sum()),n))}
 for g in families:
  inds=np.argsort(scores['dev'][g],kind='stable')[:n];r[g+'_changes_at_exact_n']=int(d[inds].sum());r[g+'_risk_at_exact_n']=float(d[inds].mean()) if n else None
 match.append(r)
csvout(P/'summary/coverage_matched_descriptive.csv',match)
# Nondeployable, two-answer hindsight opportunity, both INVALID remain agreement.
oracles=[]
for split in ['cal','dev']:
 mask=~labels[split][2];r={'split':split,'rule':'R iff frozen parsed R==Text; requires both unavailable online answers',**metrics(split,mask)}
 if split=='dev':r.update(coststats(np.where(mask,cr,ct),labels[split][1]));r['cost_identity']='selected historical component opportunity only; cost to obtain both answers excluded, not realizable online'
 else:r['estimated_net_saving_ms']=float(mask.mean()*(958.6743937070423-262.4625149028361));r['cost_identity']='old panel mean estimate, no per-cal request timing'
 oracles.append(r)
csvout(P/'summary/hindsight_opportunity.csv',oracles)
# One joint bootstrap across only the predeclared deployment points and fixed references.
paths=families+['Fixed_R','Fixed_Text'];rng=np.random.default_rng(0);bootidx=rng.integers(0,N,size=(2000,N));boot=np.empty((2000,len(paths),3))
for j,f in enumerate(paths):
 vals=np.column_stack([accuracy_arrays[f],cost_arrays[f],accuracy_arrays[f]-.01*cost_arrays[f]/262.462515]);boot[:,j,:]=vals[bootidx].mean(axis=1)
np.savez_compressed(P/'summary/bootstrap_joint_means.npz',paths=np.array(paths),means=boot,seed=0,replicates=2000)
comparisons=[(f,'Fixed_Text') for f in families]+[('D',f) for f in ['R','Diff','H','Random']];paired=[]
for a,b in comparisons:
 j=paths.index(a);k=paths.index(b);diff=boot[:,j,:]-boot[:,k,:]
 for t,label in enumerate(['accuracy','mean_cost_ms','U']):
  observed=[float((accuracy_arrays[a]-accuracy_arrays[b]).mean()),float((cost_arrays[a]-cost_arrays[b]).mean()),float((accuracy_arrays[a]-accuracy_arrays[b]-.01*(cost_arrays[a]-cost_arrays[b])/262.462515).mean())][t]
  lo,hi=np.quantile(diff[:,t],[.025,.975]);paired.append({'policy':a,'reference':b,'metric':label,'difference':observed,'CI95_descriptive_low':float(lo),'CI95_descriptive_high':float(hi),'replicates':2000,'seed':0})
csvout(P/'summary/paired_bootstrap.csv',paired)
# Labels are shared, not added across heads. No newly collected human labels.
labelrows=[]
for f,g,targets,machines in [('D',0,0,2100),('R',2100,2100,0),('Diff',2100,4200,0),('H',2100,4200,0),('Random',0,0,0)]:
 labelrows.append({'family':f,'algorithm_fit_unique_gold_questions':g,'derived_action_correctness_values':targets,'harm_training_targets':2100 if f=='H' else 0,'machine_disagreement_fit_labels':machines,'machine_disagreement_cal_labels':len(read(P/'splits/cal_ids.json')),'cal_gold_required':0,'dev_gold_posthoc_only':742,'new_human_annotations_this_round':0,'shared_gold_not_summed':True})
csvout(P/'summary/label_ledger.csv',labelrows)
_,train_meta=load_features(read(P/'splits/fit_ids.json')+read(P/'splits/cal_ids.json'))
featureidx=list(csv.DictReader((P/'features/DEV_FEATURE_INDEX.csv').open()))
save(P/'summary/computation_ledger.json',{'historical_train_RT_protocol_requests_reused':6932,'protocol_requests_are_not_forward_counts':True,'historical_train_RT_request_seconds_estimated_from_256_panel_means':3466*(262.4625149028361+958.6743937070423)/1000,'historical_train_features_reused':3466,'historical_train_feature_wall_seconds':sum(r['feature_ms'] for r in train_meta)/1000,'new_protocol_requests':0,'new_helper_forward':0,'new_answer_generation':0,'new_prefill_attempts':read(P/'DEV_FEATURES_COMPLETE.json')['attempts'],'new_prefill_success':read(P/'DEV_FEATURES_COMPLETE.json')['new_success'],'dev_cached_reused':read(P/'DEV_FEATURES_COMPLETE.json')['cached'],'new_feature_wall_seconds':sum(float(r['feature_ms']) for r in featureidx)/1000,'new_prefill_CUDA_event_seconds':sum(float(r['GPU_prefill_event_ms']) for r in featureidx)/1000,'new_model_load_wall_seconds':read(P/'evidence/model_load.json')['load_wall_seconds'],'new_fit_wall_seconds':sum(read(P/f'models/{h}_receipt.json')['fit_wall_seconds'] for h in CFG['heads']),'new_fit_CPU_seconds':sum(read(P/f'models/{h}_receipt.json')['fit_CPU_seconds'] for h in CFG['heads']),'head_selector_measured_seconds_by_family':{f:sum(r['head_selector_ms_measured'][f] for r in new)/1000 for f in families},'all_diagnostic_features_charged_to_experiment_even_if_fallback':True,'historical_resources_references':[str(E/'RESOURCE_RECEIPT.json'),str(D/'RESOURCE_RECEIPT.json')],'allocation_ledger':'evidence/CPU_runs.json and RESOURCE_RECEIPT.json; distinct from component compute times'})
# Summarize observable nonacceptance mechanisms without equating no rejection with no signal.
diags=[]
for f in families:
 r=[x for x in caltests if x['family']==f]
 diags.append({'family':f,'accepted_q':policies[f]['accepted_q'],'minimum_p':min(float(x['p_value']) for x in r),'n_max_empirical_risk_le_alpha':max([int(x['n_R']) for x in r if x['conditional_risk'] and float(x['conditional_risk'])<=.05] or [0]),'n_max_zero_change':max([int(x['n_R']) for x in r if int(x['changed'])==0] or [0]),'zero_change_min_required_n':135})
save(P/'summary/calibration_power_diagnostics.json',diags)
# Reconcile prescribed invariants, not the old 297 parser checks.
assert len(caltests)==100 and len(new)==742 and len(main)==7 and len(perq)==7*742
for f in families:
 passed=[float(r['q']) for r in caltests if r['family']==f and r['accepted']=='True'];assert policies[f]['q']==(max(passed) if passed else 0.)
for m in main:
 assert m['changed']==m['benefit']+m['harm']+m['neutral_change'];assert m['correct']-populations['dev']['Text_correct']==m['benefit']-m['harm']
 assert abs(m['U']-(m['accuracy']-.01*m['mean_cost_ms']/262.462515))<1e-12
save(P/'evidence/NUMERICAL_VALIDATION.json',{'passed':True,'checks':['100 tests with M fixed','largest accepted q or fixed Text','742 route IDs frozen before answer/gold linkage','historical complete request SHA256','feature identity and dimension','pointwise correctness inequality','direction accounting','component cost and U reconciliation','one joint seed0 2000 bootstrap','0/134 rejects acceptance; 0/135 accepts'],'no_old_parser_checks_rerun':True})
freeze('ANALYSIS_COMPLETE.json',[P/'summary/main_dev.csv',P/'summary/populations.json',P/'summary/ranking.csv',P/'summary/grid_curves.csv',P/'summary/paired_bootstrap.csv',P/'records/dev_per_question.jsonl',P/'evidence/NUMERICAL_VALIDATION.json'],N=742,heads=4,calibration_tests=100,deployments=5)
print('ANALYSIS_COMPLETE');print(json.dumps(populations['dev']));print(json.dumps([{k:r[k] for k in ['family','q','n_R','changed','correct','mean_cost_ms','net_saving_vs_Text_ms','U']} for r in main]))
