from numerics import *
from sklearn.metrics import roc_auc_score,average_precision_score
from scipy.stats import spearmanr,hypergeom
assert (P/'DEV_ROUTES_FREEZE.json').exists()
ids=read(P/'inputs/dev_ids.json');N=len(ids);assert N==742
oldrows=jl(OLD/'records/dev_per_question.jsonl');oldpq={}
for r in oldrows:
 if r['family'] in ['D','R','Fixed_R','Fixed_Text']:oldpq.setdefault(r['family'],{})[r['id']]=r
oldmain={r['family']:r for r in csv.DictReader((OLD/'summary/main_dev.csv').open())}
oldscore=jl(OLD/'records/dev_scored_routes.jsonl');assert [r['id'] for r in oldscore]==ids
lab=jl(OLD/'records/dev_evaluation_labels.jsonl');assert [r['id'] for r in lab]==ids
uD=np.array([r['scores']['D'] for r in oldscore]);u2100=np.array([r['scores']['R'] for r in oldscore]);d=np.array([r['o_R']!=r['o_T'] for r in lab],bool);yR=np.array([r['y_R'] for r in lab]);yT=np.array([r['y_T'] for r in lab]);iR=np.array([r['invalid_R'] for r in lab],bool);iT=np.array([r['invalid_T'] for r in lab],bool)
feature=np.array([r['feature_ms'] for r in oldscore]);headR=np.array([r['head_selector_ms_measured']['R'] for r in oldscore]);headD=np.array([r['head_selector_ms_measured']['D'] for r in oldscore]);cR=np.array([oldpq['Fixed_R'][i]['total_cost_ms'] for i in ids]);cT=np.array([oldpq['Fixed_Text'][i]['total_cost_ms'] for i in ids]);cD=np.array([oldpq['D'][i]['total_cost_ms'] for i in ids]);c2100=np.array([oldpq['R'][i]['total_cost_ms'] for i in ids]);yD=np.array([oldpq['D'][i]['y'] for i in ids]);y2100=np.array([oldpq['R'][i]['y'] for i in ids]);UD=np.array([oldpq['D'][i]['U'] for i in ids]);U2100=np.array([oldpq['R'][i]['U'] for i in ids]);dU=float(oldmain['D']['U'])
assert np.all(yT-yR<=d.astype(int));assert abs(UD.mean()-dU)<1e-12
pol=read(P/'models/deployment.json');fits={r['name']:r for r in csv.DictReader((P/'models/MODEL_INDEX.csv').open())};caltests=list(csv.DictReader((P/'summary/calibration_new_300.csv').open()))
metrics=[];perq=[];matched=[];grids=[];arrays={};labelsets={};cal_scores_d=np.array([r['d'] for r in jl(OLD/'inputs/candidate_cal.jsonl')],bool)
def perf(mask,c):
 n=int(mask.sum());ch=mask&d;k=int(ch.sum());y=np.where(mask,yR,yT);lo,hi=risk_interval(n,k)
 return {'N':N,'n_R':n,'coverage':float(mask.mean()),'changed':k,'conditional_risk':float(k/n) if n else None,'marginal_change':k/N,'benefit':int((ch&(yR>yT)).sum()),'harm':int((ch&(yR<yT)).sum()),'neutral_change':int((ch&(yR==yT)).sum()),'correct':int(y.sum()),'accuracy':float(y.mean()),'accuracy_difference_Text':float((y-yT).mean()),'INVALID':int(np.where(mask,iR,iT).sum()),'both_INVALID_routed':int((mask&iR&iT).sum()),'R_only_INVALID_routed':int((mask&iR&~iT).sum()),'T_only_INVALID_routed':int((mask&~iR&iT).sum()),'risk_CP95_descriptive_low':lo,'risk_CP95_descriptive_high':hi,'mean_cost_ms':float(c.mean()),'median_cost_ms':float(np.median(c)),'p95_cost_ms':float(np.quantile(c,.95)),'net_saving_Text_ms':float((cT-c).mean()),'net_saving_Text_fraction':float((cT-c).mean()/cT.mean()),'U':float(y.mean()-.01*c.mean()/262.462515)}
for conf in CFG['configs']:
 stop();name=conf['name'];rows=jl(P/f'records/{name}_dev_routes.jsonl');assert [r['id'] for r in rows]==ids
 u=np.array([r['u'] for r in rows]);mask=np.array([r['route']=='R' for r in rows]);p=pol[name];fr=fits[name];active=p['mode']=='selective'
 feat=feature if active else np.zeros(N);head=headR if active else np.zeros(N);action=np.where(mask,cR,cT);c=feat+head+action;y=np.where(mask,yR,yT);U=y-.01*c/262.462515
 m=perf(mask,c);cal=p['calibration'];rho=None if np.all(u==u[0]) else float(spearmanr(u,uD).statistic)
 calu=np.array([r['u'] for r in jl(P/f'records/{name}_cal_scores.jsonl')]);calauc=float(roc_auc_score(cal_scores_d,calu));calap=float(average_precision_score(cal_scores_d,calu))
 eligible=active and cal is not None and m['conditional_risk'] is not None and m['conditional_risk']<=.05
 uc=bool(eligible and m['U']>=dU);ca=bool(eligible and m['correct']>=643 and m['mean_cost_ms']<=797.166236)
 alternative_cost=c+(headD-headR if active else np.zeros(N));alternative_U=float(y.mean()-.01*alternative_cost.mean()/262.462515)
 altuc=bool(eligible and alternative_U>=dU);altca=bool(eligible and m['correct']>=643 and alternative_cost.mean()<=797.166236)
 m={**conf,'fit_correct':int(fr['fit_correct']),'fit_incorrect':int(fr['fit_incorrect']),'model_kind':fr['kind'],'LR_fit_performed':fr['LR_fit_performed'],'fit_converged':fr['converged'],'cal_q':p['q'],'mode':p['mode'],'cal_accepted_q':p['accepted_q'],'cal_n_R':cal['n_R'] if cal else 0,'cal_changed':cal['changed'] if cal else 0,'cal_p_value':cal['p_value'] if cal else 1.,'cal_CP_upper_0_999':cal['CP_upper_0_999'] if cal else 1.,'cal_minimum_grid_p':p['minimum_grid_p'],'cal_maximum_zero_change_n':p['maximum_zero_change_n'],'cal_maximum_n_empirical_risk_le_alpha':p['maximum_n_empirical_risk_le_alpha'],'cal_AUROC_disagreement':calauc,'cal_AP_disagreement':calap,'dev_AUROC_disagreement':float(roc_auc_score(d,u)),'dev_AP_disagreement':float(average_precision_score(d,u)),'dev_Spearman_D':rho,**m,'delta_U_D':float((U-UD).mean()),'delta_U_R2100':float((U-U2100).mean()),'delta_cost_D_ms':float((c-cD).mean()),'delta_cost_R2100_ms':float((c-c2100).mean()),'delta_accuracy_D':float((y-yD).mean()),'delta_accuracy_R2100':float((y-y2100).mean()),'utility_crossover':uc,'cost_accuracy_crossover':ca,'crossover_eligibility':eligible,'head_timing_sensitive_utility':bool(uc and not altuc),'head_timing_sensitive_cost_accuracy':bool(ca and not altca),'equal_D_head_timing_U':alternative_U,'equal_D_head_timing_cost_ms':float(alternative_cost.mean()),'cost_identity':'parent feature timing + parent same-structure correctness-R head/selector timing proxy + parent complete action request'}
 metrics.append(m);arrays[name]={'y':y,'c':c,'U':U};labelsets[name]=set(read(P/conf['subset_file']))
 for j,i in enumerate(ids):perq.append({'id':i,'name':name,'B':conf['B'],'repeat':conf['repeat'],'u':float(u[j]),'route':rows[j]['route'],'d':int(d[j]),'changed':int(mask[j]&d[j]),'y':int(y[j]),'feature_ms':float(feat[j]),'head_selector_proxy_ms':float(head[j]),'historical_full_request_ms':float(action[j]),'total_cost_ms':float(c[j]),'U':float(U[j]),'delta_accuracy_D':int(y[j]-yD[j]),'delta_accuracy_R2100':int(y[j]-y2100[j]),'delta_cost_D_ms':float(c[j]-cD[j]),'delta_cost_R2100_ms':float(c[j]-c2100[j]),'delta_U_D':float(U[j]-UD[j]),'delta_U_R2100':float(U[j]-U2100[j])})
 # Exact coverage comparisons at the new frozen point and fixed D/R2100 coverages.
 for anchor,n in [('new_frozen',m['n_R']),('D_frozen',230),('R2100_frozen',291)]:
  out={**conf,'anchor':anchor,'n_R':n,'coverage':n/N,'random_expected_changes':float(n*d.mean()),'random_hypergeom95_low':int(hypergeom.ppf(.025,N,int(d.sum()),n)),'random_hypergeom95_high':int(hypergeom.ppf(.975,N,int(d.sum()),n))}
  for label,v in [('new',u),('D',uD),('R2100',u2100)]:
   ix=np.argsort(v,kind='stable')[:n];k=int(d[ix].sum());out[label+'_changes']=k;out[label+'_risk']=float(k/n) if n else None
  matched.append(out)
 localcal=[r for r in caltests if r['name']==name]
 for qi,q in enumerate(CFG['q_grid']):
  route=np.array([r['grid_routes'][qi] for r in rows],bool);gc=np.where(route,cR,cT)+(feature+headR if q<1 else np.zeros(N));cp=localcal[qi];assert float(cp['q'])==q
  grids.append({**conf,'q':q,'cal_accepted':cp['accepted']=='True','final_deployment':q==p['q'],**perf(route,gc)})
csvout(P/'summary/main_new15.csv',metrics);writejl(P/'records/dev_per_question_new.jsonl',perq);csvout(P/'summary/coverage_matched.csv',matched);csvout(P/'summary/dev_grid300.csv',grids)
# Parent references are copied, never re-fitted, re-scored, re-timed or recalibrated.
refs=[]
for f,display in [('D','D'),('R','R2100'),('Fixed_R','Fixed_R'),('Fixed_Text','Text')]:refs.append({**oldmain[f],'display_family':display,'source':str(OLD/'summary/main_dev.csv'),'new_model':False})
csvout(P/'summary/frozen_references.csv',refs)
# Median/min/max across all five repetitions; ranges are not confidence intervals.
summary=[]
fields=['cal_q','n_R','coverage','changed','conditional_risk','correct','accuracy','mean_cost_ms','median_cost_ms','p95_cost_ms','net_saving_Text_ms','U','delta_U_D','delta_U_R2100','delta_accuracy_D','delta_cost_D_ms','dev_AUROC_disagreement','dev_AP_disagreement','dev_Spearman_D']
for B in CFG['budgets']:
 rr=[r for r in metrics if r['B']==B];out={'B':B,'repeats':5,'selective_accepted_count':sum(r['mode']=='selective' for r in rr),'utility_crossover_count':sum(r['utility_crossover'] for r in rr),'cost_accuracy_crossover_count':sum(r['cost_accuracy_crossover'] for r in rr),'timing_sensitive_count':sum(r['head_timing_sensitive_utility'] or r['head_timing_sensitive_cost_accuracy'] for r in rr),'range_identity':'observed subset repeats, not 95% confidence interval'}
 for f in fields:
  vals=[r[f] for r in rr if r[f] is not None];out[f+'_non_NA']=len(vals)
  for stat,func in [('median',np.median),('min',np.min),('max',np.max)]:out[f+'_'+stat]=float(func(vals)) if vals else None
 summary.append(out)
csvout(P/'summary/budget_summary.csv',summary)
# One joint resampling index for five predeclared B=128 models vs unchanged D.
names=[f'R128_r{r}' for r in range(5)];rng=np.random.default_rng(0);idx=rng.integers(0,N,size=(2000,N));np.save(P/'summary/bootstrap_indices_seed0.npy',idx);paired=[];boots=[]
for name in names:
 a=arrays[name];vals=np.column_stack([a['y']-yD,a['c']-cD,a['U']-UD]);b=vals[idx].mean(axis=1);boots.append(b)
 for j,f in enumerate(['accuracy','mean_cost_ms','U']):
  lo,hi=np.quantile(b[:,j],[.025,.975]);paired.append({'name':name,'B':128,'repeat':int(name[-1]),'reference':'D','metric':f,'difference':float(vals[:,j].mean()),'CI95_descriptive_low':float(lo),'CI95_descriptive_high':float(hi),'bootstrap_seed':0,'replicates':2000,'uncertainty_scope':'questions conditional on fixed labels/model/threshold; not label-subset uncertainty'})
np.savez_compressed(P/'summary/bootstrap_differences.npz',names=np.array(names),values=np.stack(boots,axis=1));csvout(P/'summary/bootstrap_B128_vs_D.csv',paired)
# Algorithm needs vs reused historical assets vs this experiment's unique union.
fitn=2100;caln=1366;means=read(E/'COST_FREEZE.json')['cost_ms'];rmean,tmean=means[:2];fitfeat=read(P/'summary/fit_pool_feature_cost.json');calfeat=read(P/'summary/cal_pool_feature_cost.json');offlinefeat=fitfeat['feature_wall_seconds_reused']+calfeat['feature_wall_seconds_reused'];labelrows=[]
for name,B in [('D',0),('R2100',2100)]+[(f'R{B}',B) for B in CFG['budgets']]:
 req=2*fitn+2*caln if name=='D' else B+2*caln;fitcost=fitn*(rmean+tmean) if name=='D' else B*rmean
 labelrows.append({'method':name,'algorithm_unique_fit_gold':B,'derived_y_R_targets':B,'machine_fit_d':fitn if name=='D' else 0,'machine_cal_d':caln,'fit_R_requests':fitn if name=='D' else B,'fit_Text_requests':fitn if name=='D' else 0,'cal_R_requests':caln,'cal_Text_requests':caln,'total_protocol_requests_needed':req,'protocol_seconds_estimated_from_old_train_means':float((fitcost+caln*(rmean+tmean))/1000),'full_unlabeled_fit_z_required':fitn,'cal_z_required':caln,'offline_z_count':3466,'offline_feature_wall_seconds_reused':offlinefeat,'new_human_labels':0,'new_protocol_requests':0,'new_features':0,'cost_identity':'old mean protocol estimate plus actual historical feature timings; not new expense, not LLM forward count'})
csvout(P/'summary/algorithm_label_cost_ledger.csv',labelrows)
union=set.union(*labelsets.values());unions={B:set.union(*[v for n,v in labelsets.items() if n.startswith(f'R{B}_')]) for B in CFG['budgets']}
writejl(P/'records/gold_union_ids.jsonl',({'id':i} for i in sorted(union)))
preview=read(P/'evidence/PREPARATION_DEVIATION.json')['ids'];save(P/'evidence/preview_membership.json',{'preview_ids':preview,'membership':{i:[n for n,s in labelsets.items() if i in s] for i in preview},'rule_changed':False,'no_resampling':True})
save(P/'summary/experiment_ledger.json',{'algorithm_configuration_label_positions':sum(c['B'] for c in CFG['configs']),'new_models_unique_gold_union':len(union),'gold_union_per_budget':{str(B):len(s) for B,s in unions.items()},'single_model_needs_separate':'algorithm_label_cost_ledger.csv','all_experiment_reference_D_R2100_gold_already_existing':2100,'new_human_annotations':0,'new_head_experiment_unique_fit_R_requests_reused':len(union),'shared_cal_R_Text_requests_reused':2732,'new_head_experiment_unique_protocol_requests_reused':len(union)+2732,'shared_original_D_reference_learning_protocol_requests':6932,'old_reference_learning_cost_not_new_execution':True,'actual_script_queries_R_output_text':False,'script_uses_inherited_y_R_targets':True,'unique_train_z_reused':3466,'unique_dev_z_reused':742,'offline_feature_wall_seconds_reused':offlinefeat,'dev_feature_wall_seconds_reused':float(feature.sum()/1000),'new_feature_wall_seconds':0,'new_GPU_compute_seconds':0,'new_backbone_or_tokenizer_loads':0,'new_prefills':0,'new_helper_forwards':0,'new_generation':0,'new_fit_CPU_seconds':sum(float(r['fit_CPU_seconds']) for r in fits.values()),'head_proxy_mean_ms':float(headR.mean()),'D_head_mean_ms':float(headD.mean()),'mean_head_difference_D_minus_R_ms':float((headD-headR).mean()),'original_cost_estimate_source':str(E/'COST_FREEZE.json'),'original_R_mean_ms':rmean,'original_Text_mean_ms':tmean,'CPU_total_ledger':'evidence/CPU_runs.json plus 30 second preparation/report reserve'})
# Directed invariants only. All new numerical work stays within this PBS process.
assert len(metrics)==15 and len(perq)==11130 and len(caltests)==300 and len(grids)==300 and len(paired)==15
for r in metrics:
 assert r['benefit']+r['harm']+r['neutral_change']==r['changed'];assert r['correct']==int(yT.sum())+r['benefit']-r['harm']
 passed=[float(x['q']) for x in caltests if x['name']==r['name'] and x['accepted']=='True'];assert r['cal_q']==(max(passed) if passed else 0)
 if r['mode']=='fixed_T':assert abs(r['mean_cost_ms']-cT.mean())<1e-10
 if r['mode']=='fixed_R':assert abs(r['mean_cost_ms']-cR.mean())<1e-10
for repeat in range(5):
 assert labelsets[f'R32_r{repeat}']<labelsets[f'R128_r{repeat}']<labelsets[f'R512_r{repeat}']
 view=list(csv.DictReader((P/f'comparisons/r{repeat}_100.csv').open()));assert len(view)==100 and sum(x['source_identity']=='new_test' for x in view)==60
save(P/'evidence/NUMERICAL_VALIDATION.json',{'passed':True,'new_models':15,'new_tests':300,'distinct_model_grid_items':340,'per_repeat_views':5,'new_dev_records':11130,'subset_nesting':True,'cal_selection_rule':True,'reference_records_reused_unchanged':True,'marker_thresholds_frozen':True,'cost_U_and_direction_reconciled':True,'single_bootstrap_index_sha256':sha(P/'summary/bootstrap_indices_seed0.npy'),'no_GPU_or_LLM_calls':True,'utc':utc()})
freeze('ANALYSIS_COMPLETE.json',[P/'summary/main_new15.csv',P/'summary/budget_summary.csv',P/'summary/coverage_matched.csv',P/'summary/bootstrap_B128_vs_D.csv',P/'records/dev_per_question_new.jsonl',P/'summary/algorithm_label_cost_ledger.csv',P/'summary/experiment_ledger.json',P/'evidence/NUMERICAL_VALIDATION.json'],new_models=15,new_cal_tests=300,new_dev_evaluations=11130)
print('ANALYSIS_COMPLETE',json.dumps([{k:r[k] for k in ['B','selective_accepted_count','utility_crossover_count','cost_accuracy_crossover_count','delta_U_D_median','delta_U_D_min','delta_U_D_max']} for r in summary]),flush=True)
