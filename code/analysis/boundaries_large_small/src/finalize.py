"""Lightweight receipt, source integrity, document checks, append-only status and packaging."""
from common import *
import ast,re,subprocess,tarfile,shutil
jid=read(P/'evidence/pbs/submission.json')['job_id']; j=read(P/'evidence/pbs/status.json')['Jobs'][jid]
assert j['job_state']=='F'
finished=(P/'EXECUTION_COMPLETE.json').exists() and (P/'NUMERICAL_VALIDATION.json').exists() and j.get('Exit_status')==0
status='COMPLETE' if finished else 'PARTIAL'
def epoch(s):return datetime.datetime.strptime(s,'%a %b %d %H:%M:%S %Y').replace(tzinfo=datetime.timezone.utc).timestamp()
def sec(s):
 h,m,ss=map(int,s.split(':'));return 3600*h+60*m+ss
cpu=read(P/'evidence/CPU_runs.json') if (P/'evidence/CPU_runs.json').exists() else {'CPU_seconds':0,'phases':[]};charged=cpu['CPU_seconds']+150
allocation=epoch(j['obittime'])-epoch(j['stime']) if j.get('stime') and j.get('obittime') else None
counts={name:sum(1 for l in (P/path).open() if l.strip()) if (P/path).exists() else 0 for name,path in [('attempts','records/probe_attempts.jsonl'),('success','records/probe_records.jsonl'),('new_cal','records/calibration_new.jsonl'),('new_evaluations','records/deployment_evaluations_new_3422.jsonl')]}
run=Path(os.environ['DATA_ROOT'])/'runs/iclr2027_p2'/(jid+'_ref_bounds');dest=P/'evidence/run_logs';dest.mkdir(exist_ok=True)
if run.exists():
 for f in run.iterdir():
  if f.is_file():shutil.copyfile(f,dest/f.name)
bank=read(P/'evidence/pbs/sbank_receipt.json') if (P/'evidence/pbs/sbank_receipt.json').exists() else {'status':'NA: no facility billing receipt available; not zero'}
r={'utc':utc(),'status':status,'job_id':jid,'job_state':j['job_state'],'exit_status':j.get('Exit_status'),'account':'project','queue':'gpu-queue','GPU_allocation_count':1,'requested_seconds':1800,'requested_GPU_allocation_hours':.5,'actual_allocation_seconds_stime_to_obittime':allocation,'actual_GPU_allocation_hours':allocation/3600 if allocation else None,'scheduler_walltime_seconds':sec(j['resources_used']['walltime']),'CPU_supervised_seconds':cpu['CPU_seconds'],'CPU_preparation_reporting_reserve':150,'CPU_charged_seconds':charged,'CPU_cap':900,'CPU_scheduler_seconds_not_additive':sec(j['resources_used']['cput']),'CPU_threads':1,'scheduler_memory':j['resources_used'].get('mem'),'CPU_phases':cpu['phases'],'counts':counts,'reused_probe_records':4208,'reused_tests':20,'reused_evaluations':742,'fits':0,'helper':0,'answer_generation':0,'new_protocol_requests':0,'new_downloads_or_installs':0,'sbank':bank,'this_budget_closed':True,'all_old_budgets_closed':True,'remaining_submissions':0,'unused_probe_attempts_not_reusable':7044-counts['attempts'],'unused_CPU_not_reusable':900-charged,'unused_wall_seconds_not_reusable':1800-allocation if allocation else None}
assert counts['attempts']<=7044 and counts['new_cal']<=140 and counts['new_evaluations']<=3422 and charged<=900
r['model_startup']={pair:read(P/f'evidence/{pair}_model_startup.json') for pair in PAIRS if (P/f'evidence/{pair}_model_startup.json').exists()}
if (P/'summary/probe_timing.csv').exists():r['new_GPU_prefill_projection_event_seconds']=sum(float(x['sum']) for x in csvread(P/'summary/probe_timing.csv') if x['identity']=='new' and x['component']=='GPU_prefill_projection_event_ms')/1000
r['startup_CPU_separate']=None;r['startup_CPU_note']='included in supervised phase CPU; separate startup CPU not instrumented'
save(P/'RESOURCE_RECEIPT.json',r)
if not finished:
 save(P/'FINAL_RECEIPT.json',{'status':'PARTIAL','job_id':jid,'counts':counts,'resource_sha256':sha(P/'RESOURCE_RECEIPT.json'),'remaining_submissions':0,'error':cpu.get('error'),'next_action':'Return to Work; never resubmit or rerun successful ids'})
else:
 assert counts=={'attempts':7044,'success':7044,'new_cal':140,'new_evaluations':3422}
 # Verify frozen source/data identities, not numerical recomputation on login.
 checked=[]
 for code in (P/'src').glob('*.py'):ast.parse(code.read_text(),filename=str(code))
 for p in [P/'PROTOCOL_FREEZE.json',P/'SPLIT_FREEZE.json',P/'IMPLEMENTATION_FREEZE.json',P/'ALL_ROUTES_FREEZE.json',P/'PROBES_COMPLETE.json',P/'ANALYSIS_FREEZE.json']+list((P/'deployments').glob('*FREEZE.json'))+list((P/'thresholds').glob('*FREEZE.json'))+list((P/'protocol').glob('*/PROBE_PROTOCOL_FREEZE.json')):
  for f,h in read(p)['files'].items():assert sha(P/f)==h,(p.name,f);checked.append({'freeze':str(p.relative_to(P)),'file':f,'sha256':h})
 for src in csvread(P/'SOURCE_INDEX.csv'):assert sha(src['path'])==src['sha256'],src['path']
 # Correct a double-escaped percent in the generated header, a typography-only repair.
 tf=P/'paper/boundary_main_table.tex';before_tex=tf.read_text();after_tex=before_tex.replace(r'95\\% interval',r'95\% interval');tf.write_text(after_tex)
 save(P/'paper/FORMAT_REPAIR.json',{'utc':utc(),'file':str(tf.relative_to(P)),'changed':before_tex!=after_tex,'reason':'normalize escaped percent in table header; no data or scientific changes'})
 # State the ideal sampling assumptions and the reused-file metadata correction explicitly.
 pp=P/'paper/boundary_cost_limitations.tex'
 with pp.open('a') as f:f.write('\nThe ideal calibration bound requires independent, identically distributed calibration groups with the score and fit thresholds fixed independently of their disagreement outcomes. Historical exposure, unrecognized dependence, and distribution shift limit that interpretation. The reused large/OBQA file, including its old development scores, was loaded before the new C2C calibration; only fit scores and calibration disagreement enter that calibration. An accompanying metadata clarification corrects the imprecise dev-probes-read flag without changing the frozen record.\n')
 # Follow only the active manuscript topology; historical fragments remain source history.
 seen=set();inputs=[]
 def checktex(p):
  p=p.resolve()
  if p in seen:return
  seen.add(p);txt=p.read_text();stack=[]
  for kind,env in re.findall(r'\\(begin|end)\{([^}]+)\}',txt):
   if kind=='begin':stack.append(env)
   else:assert stack and stack.pop()==env,(p.name,env)
  assert not stack,(p.name,stack)
  for f in re.findall(r'\\input\{([^}]+)\}',txt):
   q=p.parent/f;assert q.exists(),(p.name,f);inputs.append({'source':p.name,'target':f,'sha256':sha(q)});checktex(q)
  for f in re.findall(r'\\includegraphics(?:\[[^]]*\])?\{([^}]+)\}',txt):assert (p.parent/f).exists()
 with (P/'paper/boundary_appendix.tex').open('a') as f:
  f.write(f'\n\\paragraph{{Actual execution receipt.}} The sole ClusterB job {jid.split(".")[0]} finished with exit status 0. It requested one GPU allocation for 1800 seconds (0.5 GPU allocation hours); actual allocation was {allocation} seconds ({allocation/3600:.6f} GPU allocation hours), with scheduler walltime {r["scheduler_walltime_seconds"]} seconds. Supervised CPU use was {cpu["CPU_seconds"]:.6f} seconds; including a conservative 150-second preparation/reporting reserve gives {charged:.6f}/900 seconds. The new prefill/projection device-event sum was {r.get("new_GPU_prefill_projection_event_seconds",0):.6f} seconds. Startup CPU is included in supervised CPU but not separately instrumented; model and tokenizer startup wall times are in the model receipts. There were 7044 successful probes from 7044 attempts, 140 new calibration items and 3422 new frozen deployment evaluations, with no fitting, helper forward, answer generation, new protocol request, download, or installation. No matched facility billing entry was returned, so charge is NA, not zero. One document-only figure repair used already frozen curve values and the reporting reserve. TeX compilation was unavailable; only active source structure and independently rendered PDF/PNG figures were checked. The budget is closed.\n')
 checktex(P/'paper/manuscript.tex')
 engines={k:shutil.which(k) for k in ['pdflatex','xelatex','lualatex','tectonic','latexmk']};tex={'compiled':False,'engines':engines,'installations':0,'reason':'No TeX compiler available on PATH; no compilation claimed','active_inputs':inputs,'environment_nesting_checked':True}
 save(P/'paper/TEX_VALIDATION.json',tex)
 words=len((P/'paper/contribution_positioning.tex').read_text().split());assert 100<=words<=150
 assert read(P/'evidence/FIGURE_VISUAL_CHECK.json')['viewed']
 save(P/'VALIDATION_RECEIPT.json',{'utc':utc(),'status':'PASS','source_integrity_checks':checked,'all_indexed_parent_sources_unchanged':True,'active_tex_sources_checked':True,'contribution_words':words,'TeX_compiled':False,'figure_visually_checked':True,'numerical_validation_source':'NUMERICAL_VALIDATION.json','not_new_statistical_recomputation':True})
 save(P/'FINAL_RECEIPT.json',{'status':'COMPLETE','task':'P2_CONFIDENCE_REFERENCE_BOUNDARIES','stage':P.name,'job_id':jid,'utc':utc(),'counts':counts,'reused':{'probe':4208,'cal':20,'deployment_rows':742},'deployment_q':{k:v['q'] for k,v in read(P/'deployments/all.json').items()},'resource_sha256':sha(P/'RESOURCE_RECEIPT.json'),'config_sha256':sha(P/'frozen_config.json'),'all_routes_sha256':sha(P/'ALL_ROUTES_FREEZE.json'),'CPU_charged_seconds':charged,'actual_GPU_allocation_hours':r['actual_GPU_allocation_hours'],'TeX_compiled':False,'contribution_words':words,'budget_closed':True,'remaining_submissions':0,'next_action':'Return to Work; no automatic E2E/final test or new algorithm claim'})
 # Append explicit iid assumptions and the preserved-receipt metadata correction.
 with (P/'P2_CONFIDENCE_REFERENCE_BOUNDARIES_REPORT_ZH.md').open('a') as f:f.write('\n独立校准限制：理想二项/Bonferroni解释需要独立同分布的校准题组，以及分数和fit阈值不依赖cal分歧结果。历史曝光、未识别依赖和分布漂移不由本轮冻结消除。large/OBQA旧文件含dev行已整体读入，C2C新校准仅使用fit分数和cal分歧；原回执dev_probes_read=false字段不准确，已在evidence/EXPOSURE_CLARIFICATION_ZH.md纠正事实并保留原hash，不宣称重新盲化。\n')
 # Append the actual closed resource state to the Chinese report.
 with (P/'P2_CONFIDENCE_REFERENCE_BOUNDARIES_REPORT_ZH.md').open('a') as f:f.write(f'\n## 最终资源与编译回执\n\n唯一作业{jid}为F/{j.get("Exit_status")}；申请.5 GPU allocation hour，实际分配{allocation}秒（{r["actual_GPU_allocation_hours"]:.6f} GPU小时），scheduler walltime {r["scheduler_walltime_seconds"]}秒。CPU含150秒准备/报告保守预留为{charged:.6f}/900秒。新增probe尝试/成功7044/7044，新cal140、复用20，新冻结评价3422、复用742；0拟合、helper、答案生成或新协议请求。费用见RESOURCE_RECEIPT；sbank未返回可确认收费时为NA而非0。TeX未编译，环境无编译器；活跃正文输入与环境嵌套已检查，独立PDF/PNG图已渲染和视觉核对。预算关闭，禁止第二提交。\n')
final=read(P/'FINAL_RECEIPT.json')
save(P/'SESSION_RESUME_ZH.json',{'stage':status+'_STOPPED','job_id':jid,'successful_ids_source':'records/probe_records.jsonl','successful_ids_sha256':sha(P/'records/probe_records.jsonl') if counts['success'] else None,'counts':counts,'config_sha256':sha(P/'frozen_config.json'),'budget_closed':True,'remaining_submissions':0,'remaining_execution_authorization':0,'next_action':'交回Work；禁止重新提交或重采成功id'})
with (P/'HANDOFF_ZH.md').open('a') as f:f.write(f'\n最终状态：{status}，唯一作业{jid}为F/{j.get("Exit_status")}。实际分配{allocation}秒，CPU保守计账{charged:.6f}/900秒。预算关闭；禁止再次提交。完整资源、原始计时及来源hash见RESOURCE_RECEIPT.json / FINAL_RECEIPT.json / SHA256SUMS。TeX未编译，不安装环境。\n')
state=ROOT/'P2_1_20260910T041720Z/P2_STATE.md';before=state.read_bytes();marker=f'<!-- {status} {P.name} -->';assert marker.encode() not in before
entry=f'\n\n{marker}\n## {utc()} — {P.name} {status}，交回Work\n\n- 唯一任务P2_CONFIDENCE_REFERENCE_BOUNDARIES；作业{jid}已F/{j.get("Exit_status")}。新增probe尝试{counts["attempts"]}/成功{counts["success"]}，新cal{counts["new_cal"]}、新冻结部署题评价{counts["new_evaluations"]}；原4208probe/20项Text检验/742评价身份复用。零拟合/helper/答案生成/新协议请求，ARC test仍封存。\n- D已降为学习型对照，退出当前主方法候选；ProbeMax是普通基线。本轮每次R/b二选一，Text和官方C2C各为预定固定参考，不学习两参考选择器；成功不称新算法，回退/负结果不推断所有通信路由无效。\n- ARC新风险划分fit671行/670组、cal448行/448组，重复对保留在fit且只用最小id检验；旧五折和OBQA原划分不改。分层20项p≤.001，仅每层理想Bonferroni≤.02，不作八层联合FWER≤.10。\n- 全量开发风险/正确性和128题同批panel成本/U分开；按各自train256 R均值计U，无KV抵扣、无新E2E、无因果规模效应或独立封存确认。历史large/OBQA/Text460.936752ms与D797.166236ms原身份保留，ΔU=.006072027描述区间跨零，非全面支配或等价。\n- 申请30分钟/.5 GPU allocation hour；实际{allocation}秒，CPU含150秒预留{charged:.6f}/900秒。预算关闭，无第二提交或旧预算恢复。TeX未编译；中文报告和英文正文及源图/回执见`{P}`。\n'
if finished:
 main=csvread(P/'summary/main_dev.csv');pans=[x for x in csvread(P/'summary/panel_cost.csv') if x['policy']=='ProbeMax']
 entry+='- 八层结果：'+ '; '.join(f'{x["pair"]}/{x["dataset"]}/{x["reference"]} q={x["q"]}, R={x["n_R"]}, 改变={x["changed"]}, 正确={x["correct"]}' for x in main)+'。\n'
 entry+='- 128题panel净节省ms：'+ '; '.join(f'{x["pair"]}/{x["dataset"]}/{x["reference"]} {float(x["net_saving_ms"]):.3f}' for x in pans)+'。完整描述区间见paired_bootstrap.csv；不以点估计作总体胜出保证。\n'
with state.open('a') as f:f.write(entry)
assert state.read_bytes().startswith(before)
save(P/'STATE_APPEND_RECEIPT.json',{'utc':utc(),'path':str(state),'prefix_bytes':len(before),'prefix_sha256':hashlib.sha256(before).hexdigest(),'append_sha256':hashlib.sha256(entry.encode()).hexdigest(),'append_only_verified':True})
# Light package contains this run only, no weights, logits or old bulk assets.
files=sorted(f for f in P.rglob('*') if f.is_file() and not any(x in f.parts for x in ['__pycache__','matplotlib-cache']) and f.suffix not in ['.gz'] and f.name not in ['SHA256SUMS','DELIVERY_RECEIPT.json','finalize_stdout.json'])
(P/'SHA256SUMS').write_text(''.join(sha(f)+'  '+str(f.relative_to(P))+'\n' for f in files))
archive=P/(P.name+'_WORK_LIGHT.tar.gz')
with tarfile.open(archive,'w:gz',compresslevel=4) as tar:
 for f in files+[P/'SHA256SUMS']:tar.add(f,arcname=P.name+'/'+str(f.relative_to(P)),recursive=False)
save(P/'DELIVERY_RECEIPT.json',{'utc':utc(),'archive':str(archive),'bytes':archive.stat().st_size,'sha256':sha(archive),'file_count':len(files)+1,'status':status})
print(json.dumps({'status':status,'resource':r,'archive':str(archive)},ensure_ascii=False))
