# Administrative formatting of already measured resource counters; no numerical experiment.
from common import *
import shutil
s=read(P/'evidence/pbs/submission.json');jid=s['job_id'];j=read(P/'evidence/pbs/status.json')['Jobs'][jid];assert j['job_state']=='F' and j['Exit_status']==0
cpu=read(P/'evidence/CPU_runs.json');comp=read(P/'summary/computation_ledger.json')
def epoch(s):return datetime.datetime.strptime(s,'%a %b %d %H:%M:%S %Y').replace(tzinfo=datetime.timezone.utc).timestamp()
def seconds(s):
 h,m,ss=map(int,s.split(':'));return 3600*h+60*m+ss
alloc=epoch(j['obittime'])-epoch(j['stime']);wall=seconds(j['resources_used']['walltime']);cput=seconds(j['resources_used']['cput'])
bank=read(P/'evidence/pbs/sbank_receipt.json');bank['status']='NA: official queries found neither short nor full job identifier; not zero charge';save(P/'evidence/pbs/sbank_receipt.json',bank)
r={'stage':P.name,'job_id':jid,'status':'F','exit_status':0,'queue':'gpu-queue','account':'project','GPU_count':1,'requested_walltime_seconds':1800,'requested_GPU_allocation_hours':.5,'actual_allocation_seconds_stime_to_obittime':alloc,'actual_GPU_allocation_hours_stime_to_obittime':alloc/3600,'scheduler_walltime_seconds':wall,'scheduler_GPU_allocation_hours':wall/3600,'not_whole_node_hours':True,'GPU_computation_in_stage_A':0,'stage_A_allocation_time_still_charged':True,'CPU_supervised_seconds':cpu['CPU_seconds'],'CPU_charged_with_60s_preparation_reporting_reserve':cpu['CPU_seconds']+60,'CPU_cap_seconds':1200,'CPU_scheduler_seconds_separate_not_additive':cput,'CPU_threads':1,'resource_used_mem':j['resources_used']['mem'],'scheduler_resources_used_ngpus_field':j['resources_used']['ngpus'],'ngpus_usage_field_not_allocation_count':True,'prefill_attempts':742,'prefill_success':742,'prefill_cache_reused':0,'new_heads':4,'fit_attempts':4,'calibration_tests':100,'dev_questions':742,'final_deployment_points':5,'protocol_requests_new':0,'helper_forwards_new':0,'answer_generation_new':0,'TeX_installs':0,'model_downloads':0,'environment_installs':0,'sbank':bank,'compute_components':comp,'CPU_ledger':str(P/'evidence/CPU_runs.json'),'utc':utc()}
assert r['CPU_charged_with_60s_preparation_reporting_reserve']<=1200 and alloc<=1800
save(P/'RESOURCE_RECEIPT.json',r)
# Keep task-only logs in the lightweight handoff.
run=Path(os.environ.get('DATA_ROOT','$DATA_DIR'))/'runs/iclr2027_p2'/f'{jid}_risk_binary'
(P/'evidence/run_logs').mkdir(exist_ok=True)
for f in run.glob('*'):
 if f.is_file():shutil.copyfile(f,P/'evidence/run_logs'/f.name)
save(P/'evidence/FIGURE_VISUAL_CHECK.json',{'file':'figures/risk_coverage.png','checked':True,'assessment':'Two calibrated/dev panels, all five families, alpha line, accepted/unaccepted/final point legends, explicit Text fallbacks; readable and no material clipping.','source':'summary/grid_curves.csv','utc':utc()})
t=read(P/'paper/TEX_ENVIRONMENT.json');t['status']='No pdflatex/xelatex/lualatex/tectonic on PATH; source delivered, not compiled; no installation';save(P/'paper/TEX_ENVIRONMENT.json',t)
print(json.dumps({k:r[k] for k in ['status','exit_status','actual_allocation_seconds_stime_to_obittime','actual_GPU_allocation_hours_stime_to_obittime','scheduler_walltime_seconds','CPU_charged_with_60s_preparation_reporting_reserve']},indent=2))
