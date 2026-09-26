from common import *
import shutil
jid=read(P/'evidence/pbs/submission.json')['job_id'];j=read(P/'evidence/pbs/status.json')['Jobs'][jid];assert j['job_state']=='F' and j['Exit_status']==0
cpu=read(P/'evidence/CPU_runs.json');done=read(P/'EXECUTION_COMPLETE.json')
def ep(s):return datetime.datetime.strptime(s,'%a %b %d %H:%M:%S %Y').replace(tzinfo=datetime.timezone.utc).timestamp()
def sec(s):
 h,m,t=map(int,s.split(':'));return 3600*h+60*m+t
allocation=ep(j['obittime'])-ep(j['stime']);bank=read(P/'evidence/pbs/sbank_receipt.json');bank['status']='NA: official sbank found neither short nor full identifier; not zero charge';save(P/'evidence/pbs/sbank_receipt.json',bank)
r={'status':'COMPLETE','job_id':jid,'job_state':'F','exit_status':0,'account':'project','queue':'gpu-queue','GPU_allocation_count':1,'requested_seconds':600,'requested_GPU_allocation_hours':1/6,'actual_allocation_seconds_stime_to_obittime':allocation,'actual_GPU_allocation_hours':allocation/3600,'scheduler_walltime_seconds':sec(j['resources_used']['walltime']),'CPU_supervised_seconds':cpu['CPU_seconds'],'CPU_preparation_reporting_reserve':30,'CPU_charged_seconds':cpu['CPU_seconds']+30,'CPU_cap':300,'CPU_scheduler_seconds_not_additive':sec(j['resources_used']['cput']),'scheduler_memory':j['resources_used']['mem'],'CPU_BLAS_threads':1,'CPU_affinity':'one allowed core','GPU_compute_seconds':0,'backbone_loads':0,'tokenizer_loads':0,'prefill_attempts':0,'helper_forwards':0,'answer_generation':0,'new_features':0,'new_protocol_requests':0,'model_outcomes':15,'actual_LR_fits':done['actual_LR_fits'],'constant_fallbacks':done['constant_fallbacks'],'fit_attempts':len(jl(P/'records/fit_attempts.jsonl')),'new_cal_tests':300,'old_shared_cal_tests':40,'distinct_model_grid_items':340,'new_dev_evaluations':11130,'dev_population':742,'all_old_budgets_closed':True,'this_budget_closed':True,'new_environment_installs':0,'new_model_downloads':0,'TeX_compiled':False,'sbank':bank,'utc':utc()}
assert r['CPU_charged_seconds']<=300 and allocation<=600 and r['fit_attempts']<=15
save(P/'RESOURCE_RECEIPT.json',r)
run=Path('$DATA_DIR/runs/iclr2027_p2')/(jid+'_gold_budget');(P/'evidence/run_logs').mkdir(exist_ok=True)
for f in run.iterdir():
 if f.is_file():shutil.copyfile(f,P/'evidence/run_logs'/f.name)
save(P/'evidence/FIGURE_VISUAL_CHECK.json',{'file':'figures/gold_budget_crossover.png','checked':True,'source':'summary/main_new15.csv','assessment':'Four readable panels; all five repeat paths, medians, immutable D/R2100 references, primary B128 and Text fallback points. Some equal observations overlap; full table retains all repeats.','utc':utc()})
t=read(P/'paper/TEX_ENVIRONMENT.json');t['status']='No TeX engine on PATH; sources and rendered figure supplied, not compiled; no install';save(P/'paper/TEX_ENVIRONMENT.json',t)
print(json.dumps(r,indent=2))
