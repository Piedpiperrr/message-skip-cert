"""Administrative consolidation of measured receipts; no statistical recomputation."""
from common import *
import shutil
jid=read(P/'evidence/pbs/submission.json')['job_id'];j=read(P/'evidence/pbs/status.json')['Jobs'][jid]
assert j['job_state']=='F' and j['Exit_status']==0
def epoch(s):return datetime.datetime.strptime(s,'%a %b %d %H:%M:%S %Y').replace(tzinfo=datetime.timezone.utc).timestamp()
def seconds(s):
 h,m,ss=map(int,s.split(':'));return 3600*h+60*m+ss
cpu=read(P/'evidence/CPU_runs.json');done=read(P/'CONTROLS_COMPLETE.json');comp=read(P/'summary/computation_ledger.json')
allocation=epoch(j['obittime'])-epoch(j['stime']);charged=cpu['CPU_seconds']+120
bank=read(P/'evidence/pbs/sbank_receipt.json');assert all(not q['stdout'].strip() and 'not found' in q['stderr'] for q in bank['queries'])
bank['status']='NA: official queries found neither short nor full identifier; not zero charge';save(P/'evidence/pbs/sbank_receipt.json',bank)
comp['actual_facility_charge']='NA: official lookup found no entry; see RESOURCE_RECEIPT.json; not zero charge';save(P/'summary/computation_ledger.json',comp)
r={'status':'COMPLETE','job_id':jid,'job_state':'F','exit_status':0,'account':'project','queue':'gpu-queue','GPU_allocation_count':1,'requested_seconds':1800,'requested_GPU_allocation_hours':.5,'actual_allocation_seconds_stime_to_obittime':allocation,'actual_GPU_allocation_hours':allocation/3600,'scheduler_walltime_seconds':seconds(j['resources_used']['walltime']),'CPU_supervised_seconds':cpu['CPU_seconds'],'CPU_preparation_reporting_reserve':120,'CPU_charged_seconds':charged,'CPU_cap':900,'CPU_scheduler_seconds_not_additive':seconds(j['resources_used']['cput']),'scheduler_memory':j['resources_used']['mem'],'CPU_BLAS_threads':1,'CPU_affinity':'one allowed core','prefill_attempts':4208,'probe_success':4208,'actual_LR_fits':1,'fit_attempts':1,'new_cal_tests':60,'reused_cal_tests':40,'new_frozen_dev_policy_question_evaluations':2226,'new_human_gold':0,'new_protocol_requests':0,'helper_forwards':0,'answer_generation':0,'new_model_downloads':0,'new_environment_installs':0,'TeX_compiled':False,'sbank':bank,'component_compute':comp,'all_old_budgets_closed':True,'this_budget_closed':True,'remaining_prefill_attempts':0,'remaining_fit_attempts':0,'remaining_calibration_tests':0,'remaining_frozen_dev_evaluations':0,'remaining_submissions':0,'unused_CPU_before_budget_closure':900-charged,'unused_requested_wall_allocation_seconds_not_reusable':1800-allocation,'execution_timestamp_note':'EXECUTION_COMPLETE.utc inherited CONTROLS_COMPLETE.utc through dictionary expansion; actual analysis/plot end times are in evidence/CPU_runs.json; final closure timestamp here is authoritative','utc':utc()}
assert charged<=900 and allocation<=1800 and len(jl(P/'records/probe_attempts.jsonl'))==4208
save(P/'RESOURCE_RECEIPT.json',r)
run=Path('$DATA_DIR/runs/iclr2027_p2')/(jid+'_zero_gold');dest=P/'evidence/run_logs';dest.mkdir(exist_ok=True)
for path in run.iterdir():
 if path.is_file():shutil.copyfile(path,dest/path.name)
save(P/'paper/TEX_ENVIRONMENT.json',{'compiled':False,'checked_engines':{k:shutil.which(k) for k in ['pdflatex','xelatex','lualatex','tectonic']},'installations':0,'status':'No installed TeX compiler on PATH; integrated source and independently rendered PDF/PNG figure delivered'})
save(P/'evidence/FIGURE_VISUAL_CHECK.json',{'utc':utc(),'file':'figures/risk_coverage_cost.png','viewed':True,'assessment':'Three readable panels; percent axes and cost units correct; five fixed score families; alpha=.05; stars for deployments and WordD Text fallback square; no material clipping. Curves are descriptive only.','source_rows':['summary/calibration_comparison_100.csv','summary/grid_curves_dev.csv','summary/main_dev.csv']})
fig=read(P/'FIGURES_COMPLETE.json');fig['visual_inspection']='root viewed PNG; passed; see evidence/FIGURE_VISUAL_CHECK.json';save(P/'FIGURES_COMPLETE.json',fig)
print({k:r[k] for k in ['actual_allocation_seconds_stime_to_obittime','actual_GPU_allocation_hours','CPU_charged_seconds','job_state','exit_status']})
