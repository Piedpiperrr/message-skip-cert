"""Finalize existing validated results and preserve append-only project history."""
from pathlib import Path
import json,hashlib,datetime,csv,ast,tarfile,resource
O=Path(__file__).resolve().parent
now=datetime.datetime.now(datetime.timezone.utc).isoformat()
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def save(p,x):Path(p).write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
validation=json.loads((O/'NUMERICAL_VALIDATION.json').read_text());assert validation['passed']
res=json.loads((O/'RESOURCE_RECEIPT.json').read_text());assert res['CPU_budget_charged_seconds']<3600 and res['fit_attempts']==288 and res['PBS_submissions']==2 and res['total_requested_walltime_seconds']==7200
freeze=json.loads((O/'PROTOCOL_FREEZE.json').read_text())
for file,key in [('frozen_config.json','config_sha256'),('folds/group_folds.csv','folds_sha256'),('folds/groups.csv','groups_sha256'),('folds/target_counts.csv','target_counts_sha256'),('evidence/source_manifest.json','source_manifest_sha256')]:assert sha(O/file)==freeze[key]
metric=json.loads((O/'METRICS_COMPLETE.json').read_text())
for name,h in metric['tables_sha256'].items():assert sha(O/'summary'/name)==h,name
for f in ['run_bounded.py','pbs_entry.py','fit_stage.py','analyze_stage.py','validate_stage.py','submit_stage.py','finalize_reporting.py','finalize_delivery.py']:ast.parse((O/f).read_text())
# This is source/report verification, not a rerun of numerical analysis.
for f in (O/'paper').glob('*.tex'):
 t=f.read_text();assert t.count(r'\begin{tabular}')==t.count(r'\end{tabular}'),f
 assert t.count(r'\begin{equation}')==t.count(r'\end{equation}'),f
 assert 'have not been executed' not in t and 'has not been established' not in t,f
assert 'COMPLETE_BOUNDED_E0_VALIDATED' in (O/'P2_V2_BASELINES_FFR_E0_REPORT_ZH.md').read_text()
change=json.loads((O/'evidence/EXECUTION_CHANGELOG.json').read_text())
change['finalized_utc']=now
change['final_code_sha256']={f:sha(O/f) for f in ['run_bounded.py','pbs_entry.py','fit_stage.py','analyze_stage.py','validate_stage.py','run_p2_v2_ffr_e0.pbs','run_p2_v2_ffr_e0_resume.pbs','submit_stage.py','finalize_reporting.py','finalize_delivery.py']}
change['targeted_startup_fixes']=['evidence/pbs/STARTUP_FAILURE_AND_TARGETED_RESUME.json','evidence/pbs/clearance_format_fix.json']
change['model_or_scientific_protocol_changes']=False
save(O/'evidence/EXECUTION_CHANGELOG.json',change)
statepath=Path(json.loads((O/'evidence/state_sync_receipt.json').read_text())['path']);before=statepath.read_bytes()
append=f'''\n<!-- BEGIN P2-V2-BASELINES-FFR-E0-COMPLETE {O.name} -->
## V2基线＋FFR-E0完成（{now}，ClusterB/the execution agent）

- 状态：**COMPLETE_BOUNDED_E0_VALIDATED**。8/8个C头、280/280个OOF头，288次LR拟合、无收敛警告；固定开发评价、全部λ/三四动作/每折与pooled、翻转与INVALID、方向代入、固定/常数参照、配对差和开销表全部完成，并通过数值核验。
- 原目录 `{O}`；中文报告 `P2_V2_BASELINES_FFR_E0_REPORT_ZH.md`；资源 `RESOURCE_RECEIPT.json`；论文 `paper/03_current_status.tex`、`04_results_tables.tex`、`05_results_and_limitations.tex`；模型 `MODEL_INDEX.tsv`；交付轻量包 `P2_V2_BASELINES_FFR_E0_COMPLETED_LIGHT_BUNDLE.tar.gz`。
- config SHA256 `{freeze['config_sha256']}`，fold SHA256 `{freeze['folds_sha256']}`，保持冻结。原PARTIAL历史及原回执保留；独立RESOURCE_ADDENDUM覆盖PBS执行限制，不改科学规则。
- 科学证据：小C翻转有弱预测信号；小OBQA semantic A全样本AUC0.6345但双方有效诊断降至0.4577。FFR在若干点超过IndepLR，但小模型λ=.01全部固定选C，与常数翻转/查询无关参照相同。真实翻转代入在该点反而降低小模型决策质量，显示常数方向限制；不是一般路由上界。大OBQA word λ=.01仅约18ms正代理余量，未测在线完整开销；全λ均报告，无最佳点显著性或项目去留断言。
- PBS185606已F/127（myquota启动依赖缺失），185607已F/0（完成全部数值工作），不再在途；只用两次请求，walltime合计7200秒。CPU累计计账{res['CPU_budget_charged_seconds']:.6f}/3600秒；RSS峰值399360KiB；单线程nice10。GPU计算0，1个共享GPU配额累计分配区间123秒（scheduler walltime口径113秒），不是独占整节点。sbank暂未找到收费条目，记NA，原始PBS账单已保存。
- 无ARC test、LLM/tokenizer、新语义提取、环境安装或新增GPU实验。科学执行已完成；**交回Work审议下一科学任务，不自动E1/confidence/feedback，不直接据本E0决定项目去留。**
<!-- END P2-V2-BASELINES-FFR-E0-COMPLETE {O.name} -->
'''
marker='BEGIN P2-V2-BASELINES-FFR-E0-COMPLETE '+O.name
if marker not in before.decode():
 with statepath.open('ab') as f:f.write(append.encode())
assert statepath.read_bytes().startswith(before)
(O/'P2_STATE_COMPLETION_APPEND.md').write_text(append)
save(O/'evidence/state_completion_sync_receipt.json',{'path':str(statepath),'only_append':True,'original_prefix_preserved':True,'before_sha256':hashlib.sha256(before).hexdigest(),'after_sha256':sha(statepath),'final_state':'COMPLETE_BOUNDED_E0_VALIDATED'})
final={'status':'COMPLETE_BOUNDED_E0_VALIDATED','stage':str(O),'completed_utc':now,'task_complete':True,'completion_meaning':'Frozen experiment and deliverables complete; not a method-success gate or project continuation decision','protocol_frozen':True,'config_sha256':freeze['config_sha256'],'fold_table_sha256':freeze['folds_sha256'],'baseline_C_heads_completed':8,'baseline_C_heads_planned':8,'OOF_heads_completed':280,'OOF_heads_planned':280,'LR_attempts':288,'max_LR_attempts':320,'LR_fit_failures':0,'convergence_warnings':0,'new_dev_evaluation_done':True,'OOF_prediction_done':True,'OOF_question_prediction_rows':18340,'all_frozen_metrics_and_diagnostics_done':True,'numerical_implementation_checked':True,'numerical_validation':'NUMERICAL_VALIDATION.json','report':'P2_V2_BASELINES_FFR_E0_REPORT_ZH.md','paper_results':['paper/03_current_status.tex','paper/04_results_tables.tex','paper/05_results_and_limitations.tex'],'paper_tex_compiled':False,'paper_compile_reason':'No TeX installation or project rebuild requested; source/environment-delimiter checks only','paper_new_scientific_results':True,'model_index':'MODEL_INDEX.tsv','historical_PARTIAL_preserved':True,'historical_receipt':'history/resource_resume_20260913/FINAL_RECEIPT.json','historical_receipt_sha256':sha(O/'history/resource_resume_20260913/FINAL_RECEIPT.json'),'resource_addendum':'RESOURCE_ADDENDUM.json','resource_receipt':'RESOURCE_RECEIPT.json','CPU_budget_charged_seconds':res['CPU_budget_charged_seconds'],'CPU_budget_remaining_seconds':res['CPU_budget_remaining_seconds'],'peak_RSS_KiB':res['measured_process_peak_RSS_KiB'],'PBS_submissions':2,'PBS_job_ids':[j['job_id'] for j in res['jobs']],'PBS_all_finished':True,'GPU_compute_usage':0,'GPU_quota_occupancy_seconds':res['GPU_quota_occupancy_seconds_stime_to_obittime'],'GPU_quota_occupancy_scheduler_walltime_seconds':res['GPU_quota_occupancy_seconds_scheduler_walltime_basis'],'sbank_charge':None,'sbank_charge_status':res['sbank_charge_status'],'LLM_forward':0,'tokenizer_loads':0,'semantic_extractions':0,'ARC_test_reads':0,'environment_installs':0,'scientific_conclusions':'Heterogeneous weak flip signal; INVALID-associated A signal; many FFR-vs-IndepLR gains reproduced by fixed actions; constant-direction and unmeasured deployment cost limitations. Restricted to this E0 setting.','remaining_experiment_work':[],'not_performed_and_not_required':['TeX compilation/layout validation','new-router online overhead measurement','new budget-matched mixtures','ARC test or E1 follow-on'],'P2_STATE_path':str(statepath),'next_action':'Return to Work for review of the next scientific task; no automatic follow-on experiment'}
save(O/'FINAL_RECEIPT.json',final)
save(O/'PROGRESS.json',{'status':final['status'],'task_complete':True,'updated_utc':now,'baseline_C_heads_completed':8,'OOF_heads_completed':280,'completed_heads':288,'LR_attempts':288,'metrics_complete':True,'report_complete':True,'paper_results_complete':True,'P2_STATE_appended':True,'CPU_budget_charged_seconds':res['CPU_budget_charged_seconds'],'CPU_remaining_seconds':res['CPU_budget_remaining_seconds'],'PBS_job_ids':final['PBS_job_ids'],'PBS_all_finished':True,'next':final['next_action']})
(O/'HANDOFF_ZH.md').write_text(f'''P2 V2基线＋FFR-E0：完成交接（{now}）

状态：COMPLETE_BOUNDED_E0_VALIDATED；8/8基线C头、280/280 OOF头，288拟合无收敛警告。正式评价、冻结诊断、全部λ、中文报告、英文LaTeX结果与P2_STATE追加均完成。
目录：{O}
先读：FINAL_RECEIPT.json、P2_V2_BASELINES_FFR_E0_REPORT_ZH.md、RESOURCE_RECEIPT.json、NUMERICAL_VALIDATION.json。源配置/折表哈希与原冻结值完全相同；原PARTIAL历史保留在history/resource_resume_20260913/与P2_STATE。
PBS：185606已F/127（计算节点myquota缺失，未拟合）；185607已F/0，在ClusterB-gpu-04完成全部数值工作。两次申请合计2小时，本阶段无在途，不能再提交第三作业。
资源：累计计账{res['CPU_budget_charged_seconds']:.6f}/3600 CPU秒，峰值399360KiB，线程1/nice10，GPU计算0；1个共享GPU配额分配区间累计123秒，调度器walltime口径113秒。sbank收费尚未找到条目，保留NA，不能称PBS成本0。
结果：小C翻转有弱信号；小OBQA语义A AUC0.6345在双方有效诊断降至0.4577。FFR相对IndepLR的局部优势常可由固定动作复现；小模型λ=.01完全固定选C。真实翻转代入可能变差，暴露常数方向限制，非一般路由上界。大OBQA word λ=.01约18ms代理余量，尚无完整在线成本实测。全部原λ已报告，未选最佳点宣称显著。
产物：baseline/、oof/、MODEL_INDEX.tsv、summary/、paper/03/04/05；P2_V2_BASELINES_FFR_E0_COMPLETED_LIGHT_BUNDLE.tar.gz供Work审阅（不含模型实体，模型在原sharedfs目录）。方法/协议沿用，TeX未编译，未安装环境或读ARC test。
原评分V2、原答和语义缓存直接复用；禁止重新评分/重划/从头重启。仅由一个正式写入者维护状态。
本轮执行任务无剩余工作。交回Work审议下一科学任务；E0仅约束本轮设定，不自动决定项目去留，不启动E1/confidence/feedback/新GPU实验。
''')
# Preserve metric-generation receipt as historical stage output; attach its validation.
metric['final_status']='METRICS_COMPLETE_VALIDATED';metric['validation_receipt']='NUMERICAL_VALIDATION.json';save(O/'METRICS_COMPLETE.json',metric)
summary=json.loads((O/'summary/RESULTS_SUMMARY.json').read_text());summary['status']='METRICS_COMPLETE_VALIDATED';save(O/'summary/RESULTS_SUMMARY.json',summary)
# Hash index excludes itself and archives to avoid circular self-hashes.
indexed=[]
for p in sorted(O.rglob('*')):
 if not p.is_file() or p.is_symlink() or p.suffix=='.gz' or p.name in ['FILE_INDEX.tsv','BUNDLE_VALIDATION.json','BUNDLE_RECEIPT.json'] or p.name.endswith('.lock'):continue
 indexed.append({'path':str(p.relative_to(O)),'size_bytes':p.stat().st_size,'sha256':sha(p)})
with (O/'FILE_INDEX.tsv').open('w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=['path','size_bytes','sha256'],delimiter='\t');w.writeheader();w.writerows(indexed)
bundle=O/'P2_V2_BASELINES_FFR_E0_COMPLETED_LIGHT_BUNDLE.tar.gz'
paths=[]
for p in sorted(O.rglob('*')):
 if not p.is_file() or p.is_symlink():continue
 rel=p.relative_to(O)
 if p.suffix in ['.gz','.joblib','.npz','.npy'] or p.name.endswith('.lock') or p.name in ['BUNDLE_VALIDATION.json','BUNDLE_RECEIPT.json']:continue
 if rel.parts[0]=='evidence' and p.name.startswith('own_jobs_'):continue
 paths.append(p)
print('Artifact destination:',bundle,'source_bytes:',sum(p.stat().st_size for p in paths),flush=True)
with tarfile.open(bundle,'w:gz',compresslevel=3) as tar:
 for p in paths:tar.add(p,arcname=str(Path(O.name)/p.relative_to(O)),recursive=False)
with tarfile.open(bundle,'r:gz') as tar:
 names=set(tar.getnames())
 required=['FINAL_RECEIPT.json','RESOURCE_ADDENDUM.json','RESOURCE_RECEIPT.json','PROTOCOL_FREEZE.json','frozen_config.json','folds/group_folds.csv','summary/oof_predictions.csv','summary/decision_metrics.csv','NUMERICAL_VALIDATION.json','MODEL_INDEX.tsv','P2_V2_BASELINES_FFR_E0_REPORT_ZH.md','HANDOFF_ZH.md','paper/05_results_and_limitations.tex','history/resource_resume_20260913/FINAL_RECEIPT.json']
 for name in required:
  member=str(Path(O.name)/name);assert member in names
  assert hashlib.sha256(tar.extractfile(member).read()).hexdigest()==sha(O/name)
assert all(sha(O/r['path'])==r['sha256'] for r in indexed)
check={'status':'DELIVERY_VALIDATED','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'frozen_hashes_unchanged':True,'numerical_validation_passed':True,'all_metric_csv_hashes_preserved':True,'source_AST_and_TeX_environment_delimiters_checked':True,'TeX_compiled':False,'indexed_files':len(indexed),'bundle_members':len(paths),'bundle_path':str(bundle),'bundle_bytes':bundle.stat().st_size,'bundle_sha256':sha(bundle),'required_members_verified':required,'P2_STATE_original_prefix_preserved':True,'final_receipt_sha256':sha(O/'FINAL_RECEIPT.json'),'report_sha256':sha(O/'P2_V2_BASELINES_FFR_E0_REPORT_ZH.md'),'light_bundle_excludes_models_and_binary_feature_prediction_files':True,'models_and_raw_NPZ_remain_in_original_sharedfs_stage':True,'light_rendering_packaging_CPU_seconds':resource.getrusage(resource.RUSAGE_SELF).ru_utime+resource.getrusage(resource.RUSAGE_SELF).ru_stime,'light_rendering_packaging_CPU_accounting':'covered by separately charged 60-second continuation allowance'}
save(O/'BUNDLE_VALIDATION.json',check);save(O/'BUNDLE_RECEIPT.json',{'path':str(bundle),'sha256':check['bundle_sha256'],'size_bytes':check['bundle_bytes'],'validated':True})
print(json.dumps(check,ensure_ascii=False,indent=2))
