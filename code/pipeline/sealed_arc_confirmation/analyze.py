from common import *
import numpy as np
import pyarrow.parquet as pq
from scipy.stats import beta
compute();verify_freeze('PRE_TEST_FREEZE.json');verify_freeze('PREDICTION_TIMING_FREEZE.json');verify_freeze('TEST_POPULATION_FREEZE.json')
assert not (P/'GOLD_ACCESS_RECEIPT.json').exists(),'No repeated raw test gold access'
queries=jl(P/'inputs/test_queries_no_gold.jsonl');ids=[r['id'] for r in queries]
rows=jl(P/'records/e2e_requests.jsonl');assert len(rows)==4688 and len({r['key'] for r in rows})==4688
probes=jl(P/'records/probe_timing_2344.jsonl');assert len(probes)==2344
rr={(r['id'],r['reference'],r['mode']):r for r in rows}
assert len({r['job_id'] for r in rows})==1 and sum(r['cold_first_request'] for r in rows)==1
for r in rows:
 assert not r['runtime_failure'] and abs(sum(r['parts_ms'].values())-r['latency_ms'])<1e-7
 if r['mode']=='policy':assert r['selected']==('R' if r['probe']['ProbeMax']<=CFG['thresholds'][r['reference']]['threshold'] else r['reference'])
save(P/'GOLD_ACCESS_RECEIPT.json',{'utc':utc(),'event':'immediately before first gold-column projection','columns':['id','answerKey'],'prediction_timing_freeze_sha256':sha(P/'PREDICTION_TIMING_FREEZE.json'),'pre_test_freeze_sha256':sha(P/'PRE_TEST_FREEZE.json'),'all_4688_raw_parsed_timing_and_2344_probe_records_hashed':True,'job_id':os.environ['PBS_JOBID']})
grows=pq.read_table(CFG['population']['local_file'],columns=['id','answerKey'],use_threads=False).to_pylist()
assert [r['id'] for r in grows]==ids
gold={};ev=[]
for q,g in zip(queries,grows):
 assert isinstance(g['answerKey'],str) and g['answerKey'] in q['display_label_map'],'SEMANTIC_BLOCKED: gold mapping undefined'
 gold[q['id']]=q['display_label_map'][g['answerKey']]
 ev.append({'id':q['id'],'gold':gold[q['id']],'original_answer_key':g['answerKey'],'original_to_display':q['display_label_map']})
writejl(P/'inputs/evaluation_gold_after_prediction_freeze.jsonl',ev)
freeze('GOLD_ASSOCIATION_FREEZE.json',[P/'GOLD_ACCESS_RECEIPT.json',P/'inputs/evaluation_gold_after_prediction_freeze.jsonl'],predictions_changed=False)
representatives=read(P/'inputs/representative_ids.json');G=len(representatives)
idx=np.random.default_rng(0).integers(0,G,size=(2000,G))
np.savez_compressed(P/'summary/paired_bootstrap_indices.npz',ids=np.array(representatives),indices=idx,seed=0)
paired=[];primary=[];raw_summary=[];bootstrap=[];diagnostics=[]
def cp(k,n):
 if n==0:return [None,None]
 return [0. if k==0 else float(beta.ppf(.025,k,n-k+1)),1. if k==n else float(beta.ppf(.975,k+1,n-k))]
for b in ['T','C']:
 v=[]
 for q in queries:
  i=q['id'];p=rr[i,b,'policy'];r=rr[i,b,'reference'];o_p=normalized_answer(p['parsed']);o_r=normalized_answer(r['parsed'])
  yp=int(p['parsed']['valid'] and o_p==gold[i]);yr=int(r['parsed']['valid'] and o_r==gold[i]);saving=r['latency_ms']-p['latency_ms'];routed=p['selected']=='R';changed=o_p!=o_r
  z={'id':i,'ordinal':q['ordinal'],'group':q['group_representative'],'primary':q['primary'],'reference':b,'route':p['selected'],'routed':int(routed),'ProbeMax':p['probe']['ProbeMax'],'policy_answer':o_p,'reference_answer':o_r,'gold':gold[i],'policy_valid':p['parsed']['valid'],'reference_valid':r['parsed']['valid'],'answer_changed':int(changed),'omission_changed':int(routed and changed),'reference_route_changed':int(not routed and changed),'policy_correct':yp,'reference_correct':yr,'accuracy_diff':yp-yr,'benefit':int(yp>yr),'harm':int(yp<yr),'neutral':int(yp==yr),'neutral_both_correct':int(yp==yr==1),'neutral_both_incorrect':int(yp==yr==0),'policy_ms':p['latency_ms'],'reference_ms':r['latency_ms'],'net_saving_ms':saving,'policy_U':yp-.01*p['latency_ms']/CFG['c_ref']['arc'],'reference_U':yr-.01*r['latency_ms']/CFG['c_ref']['arc'],'delta_U':yp-yr+.01*saving/CFG['c_ref']['arc'],'probe_ms':p['parts_ms']['probe_ms'],'selector_ms':p['parts_ms']['selector_ms'],'online_probe_selector_ms':p['parts_ms']['probe_ms']+p['parts_ms']['selector_ms'],'all_online_control_ms':p['latency_ms']-p['parts_ms']['action_ms'],'policy_action_ms':p['parts_ms']['action_ms'],'cold_pair':p['cold_first_request'] or r['cold_first_request'],'policy_record_key':p['key'],'reference_record_key':r['key']}
  v.append(z);paired.append(z)
 for population,data in [('primary_groups',[z for z in v if z['primary']]),('raw_rows',v)]:
  N=len(data)
  def arr(k):return np.array([z[k] for z in data],dtype=float)
  def mean(k):return float(arr(k).mean())
  def count(k):return int(arr(k).sum())
  n=count('routed');k=count('omission_changed');interval=cp(k,n)
  s={'reference':b,'population':population,'test_N':1172,'independent_group_N':G,'N_used':N,'q':CFG['thresholds'][b]['q'],'threshold':CFG['thresholds'][b]['threshold'],'routed':n,'coverage':n/N,'changed_among_routed':k,'conditional_answer_change':k/n if n else None,'conditional_CP95_low':interval[0],'conditional_CP95_high':interval[1],'marginal_omission_answer_change':k/N,'total_policy_reference_changed':count('answer_changed'),'total_policy_reference_answer_change':mean('answer_changed'),'reference_route_changed':count('reference_route_changed'),'reference_correct':count('reference_correct'),'reference_accuracy':mean('reference_correct'),'policy_correct':count('policy_correct'),'policy_accuracy':mean('policy_correct'),'accuracy_diff':mean('accuracy_diff'),'benefit':count('benefit'),'harm':count('harm'),'neutral':count('neutral'),'neutral_both_correct':count('neutral_both_correct'),'neutral_both_incorrect':count('neutral_both_incorrect'),'policy_mean_ms':mean('policy_ms'),'policy_median_ms':float(np.median(arr('policy_ms'))),'reference_mean_ms':mean('reference_ms'),'reference_median_ms':float(np.median(arr('reference_ms'))),'net_saving_ms':mean('net_saving_ms'),'probe_mean_ms':mean('probe_ms'),'probe_median_ms':float(np.median(arr('probe_ms'))),'selector_mean_ms':mean('selector_ms'),'online_probe_selector_mean_ms':mean('online_probe_selector_ms'),'all_online_control_mean_ms':mean('all_online_control_ms'),'policy_U':mean('policy_U'),'reference_U':mean('reference_U'),'delta_U':mean('delta_U'),'lambda':.01,'c_ref_ms':CFG['c_ref']['arc'],'policy_invalid':sum(not z['policy_valid'] for z in data),'reference_invalid':sum(not z['reference_valid'] for z in data),'cold_pairs_retained':sum(z['cold_pair'] for z in data)}
  assert s['benefit']+s['harm']+s['neutral']==N
  assert s['policy_correct']-s['reference_correct']==s['benefit']-s['harm']
  assert abs(s['delta_U']-(s['accuracy_diff']+.01*s['net_saving_ms']/CFG['c_ref']['arc']))<1e-12
  if population=='primary_groups':
   assert [z['id'] for z in data]==representatives
   boot_values={metric:arr(field)[idx].mean(axis=1) for metric,field in [('net_saving_ms','net_saving_ms'),('accuracy_diff','accuracy_diff'),('delta_U','delta_U'),('coverage','routed'),('marginal_answer_change','omission_changed')]}
   denom=arr('routed')[idx].sum(axis=1);numer=arr('omission_changed')[idx].sum(axis=1)
   boot_values['conditional_answer_change']=np.divide(numer,denom,out=np.full(2000,np.nan),where=denom>0)
   np.savez_compressed(P/f'summary/{b}_bootstrap_replicates.npz',**boot_values)
   for metric,vals in boot_values.items():
    valid=vals[np.isfinite(vals)];ci=[float(x) for x in np.quantile(valid,[.025,.975])] if len(valid) else [None,None]
    bootstrap.append({'reference':b,'metric':metric,'CI95_low':ci[0],'CI95_high':ci[1],'seed':0,'replicates':2000,'undefined_replicates':2000-len(valid),'groups':G,'indices_sha256':sha(P/'summary/paired_bootstrap_indices.npz'),'interpretation':'paired descriptive percentile interval; not calibration'})
    s[metric+'_CI95_low'],s[metric+'_CI95_high']=ci
   s['empirical_risk_within_5pct']=bool(n and 20*k<=n) if n else None
   s['positive_mean_saving']=s['net_saving_ms']>0
   s['saving_interval_position']='above_zero' if s['net_saving_ms_CI95_low']>0 else ('below_zero' if s['net_saving_ms_CI95_high']<0 else 'includes_zero')
   primary.append(s);save(P/f'summary/large_arc_{b}_primary.json',s)
  else:raw_summary.append(s)
 diagnostics.append({'reference':b,'N':1172,'both_invalid':sum(not z['policy_valid'] and not z['reference_valid'] for z in v),'policy_only_invalid':sum(not z['policy_valid'] and z['reference_valid'] for z in v),'reference_only_invalid':sum(z['policy_valid'] and not z['reference_valid'] for z in v),'runtime_failure_count':0,'reference_route_answer_changes':[z['id'] for z in v if z['reference_route_changed']],'cold_pairs':[z['id'] for z in v if z['cold_pair']],'probe_record_count':sum(r['reference']==b for r in probes)})
writejl(P/'records/paired_sealed_2344.jsonl',paired)
for name,data in [('primary_sealed',primary),('raw_row_sealed',raw_summary),('paired_bootstrap',bootstrap),('output_diagnostics',diagnostics)]:csvout(P/f'summary/{name}.csv',data)
csvout(P/'summary/accuracy_decomposition.csv',[{k:r[k] for k in ['reference','population','N_used','reference_correct','reference_accuracy','policy_correct','policy_accuracy','accuracy_diff','benefit','harm','neutral','neutral_both_correct','neutral_both_incorrect']} for r in primary+raw_summary])
csvout(P/'summary/e2e_latency_utility.csv',[{k:r[k] for k in ['reference','population','N_used','policy_mean_ms','policy_median_ms','reference_mean_ms','reference_median_ms','net_saving_ms','probe_mean_ms','selector_mean_ms','online_probe_selector_mean_ms','all_online_control_mean_ms','policy_U','reference_U','delta_U','lambda','c_ref_ms']} for r in primary+raw_summary])
save(P/'summary/runtime_diagnostics.json',{'prediction_diagnostics':read(P/'evidence/PREDICTION_DIAGNOSTICS.json'),'output_diagnostics':diagnostics,'startup':read(P/'evidence/startup_total.json'),'all_raw_rows':1172,'primary_groups':G,'cold_request':[{k:r[k] for k in ['key','attempt','latency_ms','parts_ms']} for r in rows if r['cold_first_request']]})
save(P/'NUMERICAL_VALIDATION.json',{'utc':utc(),'complete':True,'raw_rows':1172,'groups':G,'complete_actions':4688,'online_probes':2344,'unique_request_keys':4688,'same_allocation_one_residency':True,'all_timing_parts_sum':True,'all_decompositions_sum':True,'predictions_hashed_before_gold':True,'thresholds_changed':False,'cold_requests_removed':0,'rows_deleted':0,'same_population_accuracy_latency_utility':True,'bootstrap_seed':0,'bootstrap_replicates':2000,'no_method_search':True})
freeze('ANALYSIS_FREEZE.json',list((P/'summary').glob('*'))+[P/'records/paired_sealed_2344.jsonl',P/'NUMERICAL_VALIDATION.json',P/'GOLD_ASSOCIATION_FREEZE.json'])
print(json.dumps(primary),flush=True)
