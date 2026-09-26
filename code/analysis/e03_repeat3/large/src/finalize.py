"""Terminal receipts and document/source checks only; no replay or resampling."""
from common import *
import shutil,ast,re,collections
jid=read(P/'evidence/pbs/submission.json')['job_id'];j=read(P/'evidence/pbs/status.json')['Jobs'][jid]
assert j['job_state']=='F';assert not (P/'FINAL_RECEIPT.json').exists()
cpu=read(P/'evidence/CPU_runs.json') if (P/'evidence/CPU_runs.json').exists() else {'CPU_seconds':0,'phases':[],'status':'NO_COMPUTE'}
finished=j.get('Exit_status')==0 and (P/'EXECUTION_COMPLETE.json').exists() and (P/'NUMERICAL_VALIDATION.json').exists() and (P/'RENDER_COMPLETE.json').exists()
status='COMPLETE' if finished else 'PARTIAL'
def epoch(s):return datetime.datetime.strptime(s,'%a %b %d %H:%M:%S %Y').replace(tzinfo=datetime.timezone.utc).timestamp()
def seconds(s):
 h,m,s=map(int,s.split(':'));return 3600*h+60*m+s
allocation=epoch(j['obittime'])-epoch(j['stime']) if j.get('obittime') and j.get('stime') else None
attempts=jl(P/'records/attempts.jsonl') if (P/'records/attempts.jsonl').exists() else []
requests=jl(P/'records/e2e_requests.jsonl') if (P/'records/e2e_requests.jsonl').exists() else []
starts=[r for r in attempts if r['event']=='START'];success=[r for r in attempts if r['event']=='SUCCESS'];probes=[r for r in requests if r['mode']=='policy']
counts={'complete_action_attempts':len(starts),'successful_complete_requests':len(success),'online_probe_attempts':sum(r.get('probe_attempt') is not None for r in starts),'online_probe_records':len(probes),'fixed_reference_records':sum(r['mode']=='reference' for r in requests),'paired_rows':512 if finished else None,'new_fits':0,'new_calibration':0,'new_gold':0,'warmup':0,'retry':0,'prior_probe_reacquisition':0}
assert len(starts)<=1024 and counts['online_probe_attempts']<=512
if finished:assert len(success)==1024 and len(probes)==512 and len({r['key'] for r in requests})==1024
run=Path(os.environ['DATA_ROOT'])/'runs/iclr2027_p2'/(jid+'_frozen_policy_e2e');dest=P/'evidence/run_logs';dest.mkdir(exist_ok=True)
for f in run.iterdir():
 if f.is_file():shutil.copyfile(f,dest/f.name)
bank=read(P/'evidence/pbs/sbank_receipt.json') if (P/'evidence/pbs/sbank_receipt.json').exists() else {'status':'NA; unavailable matched facility charge, not zero'}
charged=cpu['CPU_seconds']+180
r={'utc':utc(),'status':status,'job_id':jid,'job_state':'F','exit_status':j.get('Exit_status'),'account':'project','queue':'gpu-queue','requested_select':2,'actual_scheduler_select':j['Resource_List']['select'],'GPU_count':2,'single_node':int(j['Resource_List']['nodect'])==1,'requested_wall_seconds':1800,'requested_GPU_allocation_hours':1.,'actual_allocation_seconds_stime_to_obittime':allocation,'actual_GPU_allocation_hours':allocation*2/3600 if allocation is not None else None,'scheduler_walltime_seconds':seconds(j['resources_used']['walltime']),'CPU_supervised_seconds':cpu['CPU_seconds'],'CPU_reserve_preparation_reporting':180,'CPU_conservative_total':charged,'CPU_cap':1500,'CPU_remaining_closed':1500-charged,'CPU_scheduler_seconds_not_additive':seconds(j['resources_used']['cput']),'CPU_threads':1,'CPU_phases':cpu['phases'],'scheduler_memory':j['resources_used'].get('mem'),'counts':counts,'native_action_counts':dict(collections.Counter(v['selected'] for v in requests)),'GPU_forward_event_seconds':sum(v['GPU_forward_event_sum_ms'] for v in requests)/1000,'GPU_probe_prefill_projection_event_seconds':sum(v['probe']['GPU_prefill_projection_event_ms'] for v in probes)/1000,'event_scope':'forward device-event intervals, not allocation hours or pure kernel active time; nested native receiver backbone excluded from sum','startup':read(P/'evidence/startup_total.json') if (P/'evidence/startup_total.json').exists() else None,'startup_scope':'Runtime constructor: tokenizer/model/fuser initialization and checks; Python imports and PBS entry verification are recorded in allocation/phase wall but not separately timed','startup_CPU':'included in execution phase, not separately instrumented','model_load':read(P/f'evidence/model_load_{jid}.json') if (P/f'evidence/model_load_{jid}.json').exists() else None,'new_downloads_or_installs':0,'sbank':bank,'all_old_budgets_closed':True,'this_budget_closed':True,'remaining_submissions':0,'unused_attempts_not_reusable':1024-len(starts),'ARC_test_read':False}
assert charged<=1500
save(P/'RESOURCE_LEDGER.json',r)
engines={k:shutil.which(k) for k in ['pdflatex','xelatex','lualatex','tectonic','latexmk']}
checks=[]
for src in read(P/'SOURCE_INDEX.json'):
 assert Path(src['path']).stat().st_size==src['bytes'],src['path']
 if src['sha256']:assert sha(src['path'])==src['sha256'],src['path']
for receipt in ['PROTOCOL_FREEZE.json','IMPLEMENTATION_FREEZE.json','PANEL_VALIDATION_FREEZE.json','REPLAY_COMPLETE.json','ANALYSIS_FREEZE.json']:
 if (P/receipt).exists():
  for f,h in read(P/receipt)['files'].items():assert sha(P/f)==h,(receipt,f);checks.append({'freeze':receipt,'path':f,'sha256':h})
S=csvread(P/'summary/e2e_summary.csv') if finished else []
confirmed=[x['dataset'].upper()+'/'+('Text' if x['reference']=='T' else 'C2C') for x in S if x['confirmed_descriptive_positive_saving']=='True'];unconfirmed=[x['dataset'].upper()+'/'+('Text' if x['reference']=='T' else 'C2C') for x in S if x['confirmed_descriptive_positive_saving']!='True']
if finished:
 assert read(P/'evidence/FIGURE_VISUAL_CHECK.json')['viewed']
 appendix=f'''\\section{{Frozen-policy E2E execution details}}
The only new job, {jid.split('.')[0]}, finished F/0 on one ClusterB node with two resident GPUs. It requested 1800 seconds (1 GPU allocation hour), used {allocation:.0f} seconds of allocation ({r['actual_GPU_allocation_hours']:.6f} GPU allocation hours), and recorded {r['scheduler_walltime_seconds']} seconds of scheduler walltime. Supervised CPU was {cpu['CPU_seconds']:.6f} seconds; adding the conservative 180-second preparation/reporting reserve gives {charged:.6f}/1500 seconds. Startup walltime was {r['startup']['wall_seconds']:.3f} seconds and was never amortized into per-question latency. This is Runtime initialization; Python imports and PBS entry checks are included in allocation and phase wall, without a separate duration. Startup CPU is included in phase CPU, without a separate startup CPU measurement. The online probe prefill/projection device-event sum was {r['GPU_probe_prefill_projection_event_seconds']:.3f} seconds; events are not allocation charges. Billing status is recorded separately and unavailable billing is NA, not zero.

There were 1024 complete native action attempts and successes, including 512 policy requests with independent online probes and 512 fixed-reference requests. No warmup, retry, refit, recalibration, new gold acquisition, or previous probe reacquisition occurred. The policy-side input hashes, FP32 scores, and route decisions matched the frozen per-ID records on every replay. No probe cache survived into a native action. First formal requests, per-action cold flags, raw outputs, V2 parse reasons, model forward traces, latency components, and original source hashes are retained. Runtime failures and INVALID parses are distinct.

The two original panels each contain 128 independent question groups. A seed-0 array of 2000 paired resamples is shared by Text and C2C within each task. Utility is computed on the same panel with the frozen original train-panel receiver cost (OBQA 252.35370575390624 ms; ARC 266.9407253203125 ms) and $\\lambda=.01$. No full-development accuracy is combined with panel latency. The accounting identity for E2E-minus-component saving is reference-time shift minus selected-action-time shift minus online-control-time shift. It does not identify causal hardware or residency effects. TeX compilation is unavailable; active inputs and figure files were checked without installing software. ARC test remains sealed and no subsequent experiment was started.
'''
 (P/'paper/e2e_appendix.tex').write_text(appendix)
 p=P/'paper/manuscript.tex';s=p.read_text();p.write_text(s.replace('\\end{document}','\\input{e2e_appendix.tex}\n\\end{document}'))
 seen=set();links=[]
 def walk(p):
  p=p.resolve()
  if p in seen:return
  seen.add(p);s=p.read_text();stack=[]
  for kind,env in re.findall(r'\\(begin|end)\{([^}]+)\}',s):
   if kind=='begin':stack.append(env)
   else:assert stack and stack.pop()==env,(p.name,env)
  assert not stack,(p.name,stack)
  for name in re.findall(r'\\input\{([^}]+)\}',s):
   q=p.parent/name;assert q.exists();links.append({'source':p.name,'target':name,'sha256':sha(q)});walk(q)
  for name in re.findall(r'\\includegraphics(?:\[[^]]*\])?\{([^}]+)\}',s):assert (p.parent/name).exists()
 walk(P/'paper/manuscript.tex')
 save(P/'paper/TEX_VALIDATION.json',{'compiled':False,'engines':engines,'reason':'No compiler on PATH; source topology and environments checked; no installation','active_inputs':links,'figure_rendered_and_viewed':True})
 assert not any(engines.values()),'Compiler appeared; report actual availability instead of claiming unavailable'
 word_count=len((P/'paper/contribution_positioning.tex').read_text().split());assert 100<=word_count<=150
 with (P/'REPORT_ZH.md').open('a') as f:f.write(f'\n最终状态 COMPLETE：唯一作业 `{jid}` 已 F/0。申请双GPU×1800秒=1 GPU allocation hour；实际分配 {allocation:.0f} 秒（{r["actual_GPU_allocation_hours"]:.6f} GPU小时），scheduler walltime {r["scheduler_walltime_seconds"]} 秒。实际监督 CPU {cpu["CPU_seconds"]:.6f} 秒；含180秒准备/报告保守预留为 {charged:.6f}/1500 秒。Runtime模型/组件startup {r["startup"]["wall_seconds"]:.3f} 秒单独报告（Python导入与PBS入口核验含于分配/阶段wall，未单独计时），probe prefill/projection 设备事件共 {r["GPU_probe_prefill_projection_event_seconds"]:.3f} 秒。资源分配、设备事件、CPU/wall 与 facility 收费不混同；sbank 若无匹配回执为 NA，不是零费用。TeX 未编译（无编译器），不安装；活跃正文结构和 PDF/PNG 图已检查。全部冻结源hash核验通过，预算关闭。\n')
else:
 (P/'REPORT_ZH.md').write_text(f'# P2 冻结策略 E2E：PARTIAL\n\n唯一作业 {jid} 已 F/{j.get("Exit_status")}，完成 {len(success)} 个请求、尝试 {len(starts)} 个。失败证据见 records/failures.jsonl 和 evidence/run_logs，资源见 RESOURCE_LEDGER.json。无第二提交，不重跑成功 ID，不改变冻结策略。未完成分层不能确认真实E2E节省。保留当前真实英文正文与boundary组件结果，未写入虚构E2E数字。交回Work；ARC test未打开。\n')
final={'status':status,'task':CFG['task'],'stage':P.name,'job_id':jid,'job_state':'F','exit_status':j.get('Exit_status'),'utc':utc(),'counts':counts,'confirmed_descriptive_savings':confirmed,'unconfirmed':unconfirmed,'meaning':'paired mean saving and lower descriptive 95% bound positive on exposed original128 panel; not independent population confirmation','resource_sha256':sha(P/'RESOURCE_LEDGER.json'),'config_sha256':sha(P/'frozen_config.json'),'budget_closed':True,'remaining_submissions':0,'ARC_test_read':False,'TeX_compiled':False,'next_action':'Return to Work; stop; do not start another experiment'}
save(P/'FINAL_RECEIPT.json',final);save(P/'VALIDATION_RECEIPT.json',{'status':'PASS' if finished else 'PARTIAL','frozen_checks':checks,'parent_sources_unchanged':True,'numerical_validation':'NUMERICAL_VALIDATION.json' if finished else None,'TeX_compiled':False})
(P/'HANDOFF_ZH.md').write_text(f'''# P2_FROZEN_POLICY_E2E_VALIDATION

状态：{status}。唯一作业 `{jid}`：F/{j.get('Exit_status')}，预算关闭，禁止第二提交。

四个large策略固定 q=.80/.80/.95/.90，原P2-10两个128题panel；small四层仍fallback。真实policy执行完整ProbeMax再走完整R/Text/C2C，无KV复用；fixed参考同作业同驻留重放。完成请求 {len(success)}/1024，在线probe记录 {len(probes)}/512；无拟合/校准/新增gold/旧probe重采/warmup/retry。

已曝光panel描述标准确认正节省：{'、'.join(confirmed) or '无'}；未确认：{'、'.join(unconfirmed) or ('无' if finished else '尚未完成评价')}。不能扩展为总体保证或因果规模效应。D是learned control，ProbeMax是ordinary confidence baseline。

入口：REPORT_ZH.md；summary/e2e_summary.csv；summary/component_vs_e2e.csv；records/e2e_requests.jsonl（逐请求原始记录）；records/paired_e2e_512.jsonl（四分层配对）；paper/manuscript.tex → reference_preserving.tex（保留boundary组件表并追加真E2E）；RESOURCE_LEDGER.json；SOURCE_INDEX.json；FINAL_RECEIPT.json；SHA256SUMS。

实际分配 {allocation} 秒、CPU保守计账 {charged:.6f}/1500 秒。TeX未编译，不安装。轻量包不含权重或完整词表logits。停止并交回Work；不打开ARC test、不自动启动下一任务。
''')
save(P/'evidence/SESSION_RESUME.json',{'stage':status+'_STOPPED','job_id':jid,'successful_count':len(success),'successful_ids':[x['key'] for x in success],'records_sha256':sha(P/'records/e2e_requests.jsonl') if requests else None,'config_sha256':sha(P/'frozen_config.json'),'resource_sha256':sha(P/'RESOURCE_LEDGER.json'),'budget_closed':True,'remaining_submissions':0,'remaining_execution_authorization':0,'do_not_restart':True})
state=ROOT/'P2_1_20260910T041720Z/P2_STATE.md';before=state.read_bytes();marker=f'<!-- {status} {P.name} -->';assert marker.encode() not in before
entry=f'\n\n{marker}\n## {utc()} — {P.name} {status}，交回Work\n唯一作业 {jid} F/{j.get("Exit_status")}；原两个128题panel，四large冻结R/b策略与fixed Text/C2C同驻留真实E2E。完整动作{len(success)}/{len(starts)}成功/尝试，在线probe{len(probes)}，无旧probe重采/拟合/新cal/gold/warmup/retry，small四层fallback未重放。D仅learned control，ProbeMax普通baseline；receiver/reference regime的经验边界，非因果scale效应。\n'
if finished:entry+='真实E2E净节省ms（描述95%区间）：'+'；'.join(f'{x["dataset"]}/{x["reference"]} {float(x["net_saving_ms"]):.3f} [{float(x["CI95_saving_low"]):.3f},{float(x["CI95_saving_high"]):.3f}]' for x in S)+'。原组件表保留；经济价值与risk/coverage可行性分开。\n'
entry+=f'实际分配{allocation}秒、CPU含180秒预留{charged:.6f}/1500秒，预算关闭，无第二提交。真实英文正文活跃续稿 `{P}/paper/reference_preserving.tex`；TeX未编译。ARC test仍封存，不自动下一实验；已停止交回Work。\n'
with state.open('a') as f:f.write(entry)
assert state.read_bytes().startswith(before)
save(P/'STATE_APPEND_RECEIPT.json',{'utc':utc(),'path':str(state),'prefix_bytes':len(before),'prefix_sha256':hashlib.sha256(before).hexdigest(),'append_sha256':hashlib.sha256(entry.encode()).hexdigest(),'append_only_verified':True})
print(json.dumps(final))
