from common import *
compute();assert (P/'ALL_ROUTES_FREEZE.json').exists()
import numpy as np
from scipy.stats import beta
from sklearn.metrics import roc_auc_score,average_precision_score
CFG=read(P/'frozen_config.json');DEP=read(P/'deployments/all.json')
for f,h in read(P/'ALL_ROUTES_FREEZE.json')['files'].items():assert sha(P/f)==h
full={s:{(r['pair'],r['dataset'],r['id']):r for r in jl(V2/f'labels/{name}_SCORING_V2.jsonl')} for s,name in [('train','full_train'),('dev','full_development'),('panel','panel_development')]}
probes={('large','obqa',r['id']):r for r in jl(OLD/'records/probe_records.jsonl')}
new=jl(P/'records/probe_records.jsonl');probes.update({(r['pair'],r['dataset'],r['id']):r for r in new});assert len(probes)==11252
main=[];ranking=[];curves=[];panel=[];perq=[];panelper=[];invalid=[];diagnostics=[];boot=[];base=[];fixed=[];disagreements=[];timings=[];sourcechecks=[];caldiag=[];acquisition=[]
tests=csvread(P/'summary/calibration_all_160.csv')
def met(rows,mask,b):
 n=len(rows);m=np.asarray(mask,bool);d=np.array([r['o_R']!=r['o_'+b] for r in rows]);yr=np.array([r['y_R'] for r in rows]);yb=np.array([r['y_'+b] for r in rows]);y=np.where(m,yr,yb);changed=m&d;k=int(changed.sum());nr=int(m.sum())
 best=max(sum(r['y_'+a] for r in rows) for a in 'RTCA')
 return dict(N=n,n_R=nr,coverage=nr/n,changed=k,conditional_risk=k/nr if nr else None,marginal_change=k/n,correct=int(y.sum()),accuracy=float(y.mean()),reference_correct=int(yb.sum()),accuracy_diff_reference=float((y-yb).mean()),best_fixed_correct=best,accuracy_diff_best_fixed=float(y.mean()-best/n),benefit=int((changed&(yr>yb)).sum()),harm=int((changed&(yr<yb)).sum()),neutral_change=int((changed&(yr==yb)).sum()),risk_CP95_low=float(beta.ppf(.025,k,nr-k+1)) if nr and k else 0. if nr else None,risk_CP95_high=float(beta.ppf(.975,k+1,nr-k)) if nr and k<nr else 1. if nr else None),y,d

def rank(rows,u,b):
 d=np.array([r['o_R']!=r['o_'+b] for r in rows]);return dict(N=len(d),d_count=int(d.sum()),disagreement_rate=float(d.mean()) if len(d) else None,AUROC=float(roc_auc_score(d,u)) if len(set(d))==2 else None,AP=float(average_precision_score(d,u)) if len(set(d))==2 else None)
def ci(arr,idx):return [float(x) for x in np.quantile(arr[idx].mean(axis=1),[.025,.975])]
def dist(x):
 a=np.array(x,float);return {'N':len(a),'mean':float(a.mean()),'min':float(a.min()),'p05':float(np.quantile(a,.05)),'median':float(np.median(a)),'p95':float(np.quantile(a,.95)),'max':float(a.max()),'sum':float(a.sum())}
oldper={r['id']:r for r in jl(OLD/'records/dev_per_question_new.jsonl') if r['family']=='ProbeMax'}
for pair in PAIRS:
 for ds in DATASETS:
  stop();ids={s:read(P/f'splits/{ds}_{s}_ids.json') for s in ['fit','cal','dev']};reps={s:read(P/f'splits/{ds}_{s}_representatives.json') for s in ids}
  gm={r['id']:r['representative'] for r in csvread(P/f'splits/{ds}_group_members.csv') if r['split']=='dev'}
  thresholds=read(P/f'thresholds/{pair}_{ds}.json')['thresholds']
  rows_by={s:[full['dev' if s=='dev' else 'train'][pair,ds,i] for i in reps[s]] for s in ids}
  allrows=[full['dev'][pair,ds,i] for i in ids['dev']];rows=rows_by['dev'];rrids=reps['dev'];n=len(rows)
  # One frozen resampling index shared by both references; primary unit is representative group.
  idx=np.random.default_rng(0).integers(0,n,size=(2000,n));np.savez_compressed(P/f'summary/{pair}_{ds}_full_bootstrap_indices.npz',ids=np.array(rrids),indices=idx,seed=0)
  dv='dev' if ds=='obqa' else 'validation';pids=read(P/f'inputs/{ds}_panel_ids.json')['dev'];trainids=read(P/f'inputs/{ds}_panel_ids.json')['train']
  costfile=P10/f'results/{pair}/{ds}/{dv}_cost_panel_matrix.npz';cost=np.load(costfile,allow_pickle=False);traincost=np.load(P10/f'results/{pair}/{ds}/train_cost_panel_matrix.npz',allow_pickle=False)
  assert cost['ids'].tolist()==pids and traincost['ids'].tolist()==trainids and len(pids)==128
  assert cost['actions'].tolist()==['receiver_only','text','c2c','acw'];cm=cost['latency_ms'];cref=float(traincost['latency_ms'][:,0].mean());assert np.isfinite(cm).all() and (cm>0).all()
  prow=[full['panel'][pair,ds,i] for i in pids];pcorr=np.array([[r['y_'+a] for a in 'RTCA'] for r in prow]);pans=np.array([[r['o_'+a] for a in 'RTCA'] for r in prow]);pm={i:j for j,i in enumerate(pids)}
  # Validate original records, complete-step costs, same question blocks, and V2 source identity.
  raw=jl(P10/f'results/{pair}/{ds}/{dv}_cost_panel_originals.jsonl'); rawmap={(r['id'],r['action']):r for r in raw}
  for j,i in enumerate(pids):
   block=[rawmap[i,a] for a in cost['actions'].tolist()];assert len({r['block_id'] for r in block})==1 and len({r['job_id'] for r in block})==1
   for ai,r in enumerate(block):assert r['runtime_error'] is None and r['latency_ms']==float(cm[j,ai]);assert hashlib.sha256(r['raw_answer'].encode()).hexdigest()==prow[j]['source_'+ 'RTCA'[ai]]['raw_sha256']
  pg=sorted({gm[i] for i in pids});pgroupidx=[[pm[i] for i in pids if gm[i]==g] for g in pg]
  pidx=np.random.default_rng(0).integers(0,len(pg),size=(2000,len(pg)));np.savez_compressed(P/f'summary/{pair}_{ds}_panel_bootstrap_indices.npz',groups=np.array(pg),indices=pidx,seed=0)
  def pci(v):return ci(np.array([np.mean(v[ix]) for ix in pgroupidx]),pidx)
  sourcechecks.append({'pair':pair,'dataset':ds,'panel_rows':128,'panel_groups':len(pg),'c_ref_train256_R_ms':cref,'source_cost':str(costfile),'cost_sha256':sha(costfile),'same_block_four_actions':True,'raw_sha_matches_V2':True,'original_action_names':cost['actions'].tolist(),'cost_definition':'full call incl tokenization/transfer/generation/decode/sync; excludes scoring/validation diagnostic; startup separate','full_vs_panel_answer_changed_rows':{a:sum(full['dev'][pair,ds,i]['o_'+a]!=r['o_'+a] for i,r in zip(pids,prow)) for a in 'RTCA'}})
  for a in 'RTCA':
   fixed.append({'pair':pair,'dataset':ds,'action':a,'population':'full_dev','N_rows':len(allrows),'N_groups':n,'correct_all_ids':sum(r['y_'+a] for r in allrows),'correct_groups':sum(r['y_'+a] for r in rows),'accuracy':sum(r['y_'+a] for r in rows)/n,'identity':'direct V2 correctness aggregation; no rescoring'})
  for s in ids:
   pp=[probes[pair,ds,i] for i in ids[s]];rr=[full['dev' if s=='dev' else 'train'][pair,ds,i] for i in ids[s]]
   diagnostics.append({'pair':pair,'dataset':ds,'split':s,'N_rows':len(pp),'N_groups':len(reps[s]),'argmax_agreement_count':sum(p['argmax_probe_label']==r['o_R'] for p,r in zip(pp,rr)),'argmax_agreement_fraction':sum(p['argmax_probe_label']==r['o_R'] for p,r in zip(pp,rr))/len(pp),'label_mass':dist([p['label_union_mass'] for p in pp]),'exact_zero_count':sum(p['ProbeMax']==0 for p in pp),'score_dist':dist([p['ProbeMax'] for p in pp]),'legal_label_counts':sorted({len(p['p_labels']) for p in pp})})
   for field in ['tokenization_prefix_ms','prepare_transfer_ms','prefill_projection_ms','label_distribution_ms','probe_core_ms','ProbeMax_score_ms','GPU_prefill_projection_event_ms','diagnostic_mass_ms']:
    timings.append({'pair':pair,'dataset':ds,'split':s,'component':field,'identity':'reused' if (pair,ds)==('large','obqa') else 'new',**dist([p[field] for p in pp])})
  for b in REFS:
   tag=key(pair,ds,b);dep=DEP[tag];routes=jl(P/f'records/{tag}_routes.jsonl');assert [r['id'] for r in routes]==ids['dev'];rmap={r['id']:r for r in routes};mask=np.array([rmap[i]['route']=='R' for i in rrids]);metrics,y,d=met(rows,mask,b)
   # Each strata diagnostic uses same scores/ids and its own predeclared machine reference.
   for s in ids:
    sr=rows_by[s];u=np.array([probes[pair,ds,i]['ProbeMax'] for i in reps[s]]);valid=np.array([r['valid_R'] and r['valid_'+b] for r in sr],bool)
    bas=rank(sr,u,b);base.append({'pair':pair,'dataset':ds,'reference':b,'split':s,'N_rows':len(ids[s]),'N_groups':len(sr),**bas})
    for scope,ss,uu in [('all',sr,u),('both_valid',[r for r,v in zip(sr,valid) if v],u[valid])]:ranking.append({'pair':pair,'dataset':ds,'reference':b,'split':s,'scope':scope,**rank(ss,uu,b)})
    for q,t in zip(CFG['q_grid'],thresholds):
     mt,_,_=met(sr,u<=tv(t),b);curves.append({'pair':pair,'dataset':ds,'reference':b,'split':s,'q':q,'selected':q==dep['q'],'cal_accepted':q in dep['accepted_q'],**mt,'identity':'predeclared descriptive curve; no dev selection'})
   ci_acc=ci(y-np.array([r['y_'+b] for r in rows]),idx)
   boot.append({'pair':pair,'dataset':ds,'reference':b,'population':'full_dev','metric':'accuracy_diff_reference','difference':metrics['accuracy_diff_reference'],'CI95_low':ci_acc[0],'CI95_high':ci_acc[1],'seed':0,'replicates':2000,'unit':'independent group representative','index_sha256':hashlib.sha256(idx.tobytes()).hexdigest()})
   am,_,_=met(allrows,[r['route']=='R' for r in routes],b)
   main.append({'pair':pair,'dataset':ds,'reference':b,'q':dep['q'],'mode':dep['mode'],'N_rows':len(allrows),'N_groups':n,**metrics,'correct_all_ids':am['correct'],'CI95_accuracy_low':ci_acc[0],'CI95_accuracy_high':ci_acc[1],'evaluation_identity':'reused frozen742' if tag=='large_obqa_T' else 'new frozen deployment'})
   for policy,m in [('Fixed_R',np.ones(n,bool)),('Fixed_reference',np.zeros(n,bool))]:
    mm,_,_=met(rows,m,b);disagreements.append({'pair':pair,'dataset':ds,'reference':b,'policy':policy,**mm})
   for r,rr in zip(allrows,routes):
    i=r['id'];a=rr['route'];z={'pair':pair,'dataset':ds,'reference':b,'id':i,'group':gm[i],'primary':i==gm[i],'q':dep['q'],'route':a,'d':int(r['o_R']!=r['o_'+b]),'changed':int(a=='R' and r['o_R']!=r['o_'+b]),'o_R':r['o_R'],'o_b':r['o_'+b],'y_R':r['y_R'],'y_b':r['y_'+b],'y':r['y_'+a],'valid_R':r['valid_R'],'valid_b':r['valid_'+b],'runtime_failure':r['runtime_failure'],'evaluation_identity':rr['identity'],'source_R':r['source_R'],'source_b':r['source_'+b]}
    if tag=='large_obqa_T':
     orig=oldper[i];assert z['y']==orig['y'] and z['changed']==orig['changed'] and z['route']==orig['route'];z['original_evaluation_source']=str(OLD/'records/dev_per_question_new.jsonl')
    perq.append(z)
   for subset in ['both_valid','R_invalid_only','reference_invalid_only','both_invalid']:
    ix=[j for j,r in enumerate(rows) if ('both_invalid' if not r['valid_R'] and not r['valid_'+b] else 'R_invalid_only' if not r['valid_R'] else 'reference_invalid_only' if not r['valid_'+b] else 'both_valid')==subset]
    invalid.append({'pair':pair,'dataset':ds,'reference':b,'subset':subset,'N':len(ix),'d_count':int(d[ix].sum()),'n_R':int(mask[ix].sum()),'changed':int((mask[ix]&d[ix]).sum()),'correct':int(y[ix].sum()),'runtime_failure_rows':sum(rows[j]['runtime_failure'] for j in ix)})
   ts=[r for r in tests if (r['pair'],r['dataset'],r['reference'])==(pair,ds,b)];q1=next(r for r in ts if float(r['q'])==1);best=min(ts,key=lambda r:float(r['p_value']))
   caldiag.append({'pair':pair,'dataset':ds,'reference':b,'accepted_q':dep['accepted_q'],'selected_q':dep['q'],'selected_calibration':dep['calibration'],'q1':q1,'min_p_point':best,'min_CP':min(float(r['CP_upper_0_999']) for r in ts),'CP_margin_alpha_minus_min':.05-min(float(r['CP_upper_0_999']) for r in ts),'max_zero_change_n':max([int(r['n_R']) for r in ts if int(r['changed'])==0]+[0]),'max_empirical_risk_at_most_alpha_n':max([int(r['n_R']) for r in ts if r['conditional_risk'] and float(r['conditional_risk'])<=.05]+[0]),'zero_error_min_n_to_accept':135})
   ai='RTCA'.index(b);pmask=np.array([rmap[i]['route']=='R' for i in pids]);measured=np.array([rmap[i]['measured_selective_overhead_ms'] for i in pids]);overhead=np.array([rmap[i]['required_overhead_ms'] for i in pids]);pd=pans[:,0]!=pans[:,ai]
   policies=[('Fixed_R',np.ones(128,bool),np.zeros(128)),('Fixed_reference',np.zeros(128,bool),np.zeros(128)),('ProbeMax',pmask,overhead),('Posthoc_agreement_no_probe',~pd,np.zeros(128)),('Posthoc_agreement_with_probe',~pd,measured)]
   for policy,m,oh in policies:
    actioncost=np.where(m,cm[:,0],cm[:,ai]);costs=actioncost+oh;py=np.where(m,pcorr[:,0],pcorr[:,ai]);ut=py-.01*costs/cref;refut=pcorr[:,ai]-.01*cm[:,ai]/cref;mm,yy,dd=met(prow,m,b);assert np.array_equal(yy,py)
    panel.append({'pair':pair,'dataset':ds,'reference':b,'policy':policy,'q':dep['q'] if policy=='ProbeMax' else None,'N_rows':128,'N_groups':len(pg),**mm,'c_ref_train_R_ms':cref,'reference_ms':float(cm[:,ai].mean()),'action_ms':float(actioncost.mean()),'gross_saving_ms':float((cm[:,ai]-actioncost).mean()),'probe_selector_ms':float(oh.mean()),'total_ms':float(costs.mean()),'net_saving_ms':float((cm[:,ai]-costs).mean()),'U':float(ut.mean()),'delta_U':float((ut-refut).mean()),'deployable':not policy.startswith('Posthoc'),'cost_identity':'component recomposition on original128 same-job action panel'})
    if policy=='ProbeMax':
     for name,arr in [('accuracy_diff_reference',py-pcorr[:,ai]),('cost_diff_reference_ms',costs-cm[:,ai]),('U_diff_reference',ut-refut)]:
      lo,hi=pci(arr);boot.append({'pair':pair,'dataset':ds,'reference':b,'population':'panel128','metric':name,'difference':float(arr.mean()),'CI95_low':lo,'CI95_high':hi,'seed':0,'replicates':2000,'unit':'independent panel group','index_sha256':hashlib.sha256(pidx.tobytes()).hexdigest()})
    for j,i in enumerate(pids):panelper.append({'pair':pair,'dataset':ds,'reference':b,'id':i,'group':gm[i],'policy':policy,'route':'R' if m[j] else b,'d':int(pd[j]),'changed':int(m[j]&pd[j]),'y':int(py[j]),'y_b':int(pcorr[j,ai]),'historical_action_ms':float(actioncost[j]),'probe_selector_ms':float(oh[j]),'total_ms':float(costs[j]),'U':float(ut[j]),'source_R':prow[j]['source_R'],'source_b':prow[j]['source_'+b]})
   acquisition.append({'pair':pair,'dataset':ds,'reference':b,'N_fit_representatives':len(reps['fit']),'N_cal_representatives':len(reps['cal']),'independent_machine_protocol_requests':2*len(reps['cal']),'offline_probe_rows':len(ids['fit'])+len(ids['cal']),'gold_for_thresholds':0,'actual_new_protocol_requests':0})
assert len(perq)==4164 and sum(r['evaluation_identity']=='new' for r in perq)==3422
# Directly retain original four-action V2 table instead of invoking any parser.
csvout(P/'summary/V2_action_summary_reused.csv',csvread(V2/'action_summary.csv'))
csvout(P/'summary/historical_e2e_reference_reused.csv',csvread(OLD/'summary/historical_e2e_reference.csv'))
save(P/'summary/historical_e2e_source.json',{'path':str(OLD/'summary/historical_e2e_reference.csv'),'sha256':sha(OLD/'summary/historical_e2e_reference.csv'),'identity':'historical E2E FFR/IndepLR; never merged with panel128'})
for filename,rows in [('main_dev',main),('panel_cost',panel),('ranking',ranking),('risk_coverage_curves',curves),('invalid_decomposition',invalid),('paired_bootstrap',boot),('disagreement_base_rates',base),('fixed_full_dev',fixed),('fixed_reference_risk',disagreements),('probe_timing',timings),('acquisition',acquisition)]:csvout(P/f'summary/{filename}.csv',rows)
writejl(P/'records/deployment_evaluations_all.jsonl',perq);writejl(P/'records/deployment_evaluations_new_3422.jsonl',[r for r in perq if r['evaluation_identity']=='new']);writejl(P/'records/panel_per_question.jsonl',panelper)
save(P/'summary/probe_diagnostics.json',diagnostics);save(P/'summary/calibration_diagnostics.json',caldiag);save(P/'summary/panel_source_checks.json',sourcechecks)
physical=[{'pair':pair,'dataset':ds,'N_cal':len(read(P/f'splits/{ds}_cal_representatives.json')),'physical_unique_machine_requests_R_T_C':3*len(read(P/f'splits/{ds}_cal_representatives.json')),'actual_new_requests':0} for pair in PAIRS for ds in DATASETS]
save(P/'summary/collection_accounting.json',{'independent_flows':acquisition,'simultaneous_two_references':physical,'actual_new_generation':0,'new_prefill_attempts':7044,'reused_prefills':4208,'helper':0,'heads_fit':0,'fit_gold':0,'new_calibration':140,'reused_calibration':20,'new_deployment_evaluations':3422,'reused_deployment_evaluations':742})
save(P/'NUMERICAL_VALIDATION.json',{'utc':utc(),'complete':True,'all_7044_probes_unique':len({(r['pair'],r['dataset'],r['id']) for r in new})==7044,'all_160_tests':len(tests),'reused_Text_742_identity_checked':True,'panels_complete_and_V2_hash_matched':True,'all_curves_predeclared':True,'gold_association_after_all_routes':True,'new_evaluations':3422,'runtime_failure_rows_full':sum(r['runtime_failure'] for v in [rows for s,rows in full.items() if s in ['train','dev']] for r in v.values()),'FP32_scores_unchanged':True})
freeze('ANALYSIS_FREEZE.json',list((P/'summary').glob('*'))+[P/'NUMERICAL_VALIDATION.json',P/'records/deployment_evaluations_all.jsonl',P/'records/panel_per_question.jsonl'])
print('ANALYSIS_COMPLETE',[(r['pair'],r['dataset'],r['reference'],r['q'],r['correct']) for r in main],flush=True)
