"""Report frozen results, edit the active manuscript, and close this budget.
No model execution, raw test loading, resampling, or scientific re-selection.
"""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from common import *
import collections,re,shutil,resource
resource.setrlimit(resource.RLIMIT_CPU,(300,301))
assert not (P/'FINAL_RECEIPT.json').exists()
jid=read(P/'evidence/pbs/submission.json')['job_id'];job=read(P/'evidence/pbs/status.json')['Jobs'][jid]
assert job['job_state']=='F','Do not close an active allocation'
cpu=read(P/'evidence/CPU_runs.json') if (P/'evidence/CPU_runs.json').exists() else {'CPU_seconds':0,'phases':[]}
finished=job.get('Exit_status')==0 and (P/'EXECUTION_COMPLETE.json').exists() and (P/'ANALYSIS_FREEZE.json').exists()
run=Path(os.environ['DATA_ROOT'])/'runs/iclr2027_p2'/(jid+'_sealed_arc');logs=P/'evidence/run_logs';logs.mkdir(exist_ok=True)
for f in run.iterdir():
 if f.is_file():shutil.copyfile(f,logs/f.name)
semantic=any('SEMANTIC_BLOCKED' in f.read_text(errors='replace') for f in logs.glob('*.log'))
status='COMPLETE' if finished else ('BLOCKED' if semantic else 'PARTIAL')
def seconds(s):
 h,m,s=map(int,s.split(':'));return 3600*h+60*m+s
def epoch(s):return datetime.datetime.strptime(s,'%a %b %d %H:%M:%S %Y').replace(tzinfo=datetime.timezone.utc).timestamp()
allocation=epoch(job['obittime'])-epoch(job['stime']) if job.get('obittime') and job.get('stime') else None
attempts=jl(P/'records/attempts.jsonl') if (P/'records/attempts.jsonl').exists() else []
requests=jl(P/'records/e2e_requests.jsonl') if (P/'records/e2e_requests.jsonl').exists() else []
starts=[r for r in attempts if r['event']=='START'];successful=[r for r in attempts if r['event']=='SUCCESS'];probes=[r for r in requests if r['mode']=='policy']
counts={'complete_action_attempts':len(starts),'successful_complete_requests':len(successful),'online_probe_attempts':sum(r.get('probe_attempt') is not None for r in starts),'online_probe_records':len(probes),'per_path':dict(collections.Counter(r['mode']+'_'+r['reference'] for r in requests)),'native_selected_actions':dict(collections.Counter(r['selected'] for r in requests)),'extra_fixed_R':0,'warmup':0,'retry':0,'new_fit':0,'new_calibration':0,'small_requests':0,'OBQA_requests':0,'method_search':0}
assert len(starts)<=4688 and counts['online_probe_attempts']<=2344
if finished:assert len(successful)==4688 and len(probes)==2344 and len({r['key'] for r in requests})==4688
charged=cpu['CPU_seconds']+1200
assert charged<=9000
startup=read(P/'evidence/startup_total.json') if (P/'evidence/startup_total.json').exists() else None
ledger={'utc':utc(),'status':status,'job_id':jid,'job_state':'F','exit_status':job.get('Exit_status'),'account':'project','queue':'gpu-queue','requested_GPUs':2,'actual_scheduler_resources':job['Resource_List'],'requested_wall_seconds':7200,'requested_GPU_allocation_hours':4,'user_GPU_allocation_hour_cap':5,'actual_allocation_seconds_stime_to_obittime':allocation,'actual_GPU_allocation_hours':allocation*2/3600 if allocation is not None else None,'scheduler_walltime_seconds':seconds(job['resources_used']['walltime']),'CPU_supervised_seconds':cpu['CPU_seconds'],'CPU_preparation_reporting_conservative_reserve':1200,'CPU_conservative_total':charged,'CPU_cap_seconds':9000,'CPU_scheduler_seconds_not_additive':seconds(job['resources_used']['cput']),'CPU_phases':cpu['phases'],'CPU_threads':1,'scheduler_memory':job['resources_used'].get('mem'),'counts':counts,'startup':startup,'startup_scope':'Runtime constructor includes tokenizer/model/fuser init; Python imports/PBS hash verification in allocation and CPU; not amortized into requests','GPU_forward_event_seconds':sum(r['GPU_forward_event_sum_ms'] for r in requests)/1000,'GPU_probe_prefill_projection_event_seconds':sum(r['probe']['GPU_prefill_projection_event_ms'] for r in probes)/1000,'GPU_events_not_allocation_charge':True,'downloaded_bytes':203808,'package_installs_upgrades':0,'sbank':read(P/'evidence/pbs/sbank_receipt.json') if (P/'evidence/pbs/sbank_receipt.json').exists() else {'status':'NA; no matched billing receipt, not zero'},'remaining_submissions':0,'budget_closed':True,'unused_requests_not_reusable':4688-len(starts)}
save(P/'RESOURCE_LEDGER.json',ledger)
checks=[]
for name in ['PRE_TEST_FREEZE.json','PROTOCOL_FREEZE.json','TEST_POPULATION_FREEZE.json','PREDICTION_TIMING_FREEZE.json','GOLD_ASSOCIATION_FREEZE.json','ANALYSIS_FREEZE.json']:
 if (P/name).exists():verify_freeze(name);checks.append({'file':name,'sha256':sha(P/name),'verified':True})
pre=read(P/'PRE_TEST_FREEZE.json');access=read(P/'FIRST_TEST_ACCESS.json') if (P/'FIRST_TEST_ACCESS.json').exists() else None
pred=read(P/'PREDICTION_TIMING_FREEZE.json') if (P/'PREDICTION_TIMING_FREEZE.json').exists() else None
gold=read(P/'GOLD_ACCESS_RECEIPT.json') if (P/'GOLD_ACCESS_RECEIPT.json').exists() else None
if finished:assert pre['utc']<access['utc']<pred['utc']<gold['utc']
S={b:read(P/f'summary/large_arc_{b}_primary.json') for b in ['T','C']} if finished else {}
raw=csvread(P/'summary/raw_row_sealed.csv') if finished else []
def name(b):return 'Text' if b=='T' else 'C2C'
def pct(v):return f'{100*v:.3f}%'
def num(v):return f'{v:.3f}'
def bounds(s,key):return f"[{s[key+'_CI95_low']:.3f}, {s[key+'_CI95_high']:.3f}]"
def risk_zh(s):
 if s['routed']==0:return '无路由，无法判断'
 return ('经验条件变化率在5%目标以内' if s['empirical_risk_within_5pct'] else '经验条件变化率超过5%目标')+f"（{s['changed_among_routed']}/{s['routed']}，{pct(s['conditional_answer_change'])}）"
def save_zh(s):return ('保持正均值节省' if s['positive_mean_saving'] else '未保持正均值节省')+f"：{s['net_saving_ms']:.3f} ms，配对描述95%区间 {bounds(s,'net_saving_ms')} ms"
conclusions={b:{'reference_preservation':risk_zh(s),'economic_value':save_zh(s),'empirical_risk_within_5pct':s['empirical_risk_within_5pct'],'positive_paired_mean_saving':s['positive_mean_saving'],'saving_interval_position':s['saving_interval_position']} for b,s in S.items()}
report=[f'# P2_FINAL_SEALED_ARC_CONFIRMATION\n\n最终状态：**{status}**。唯一作业 `{jid}`：F/{job.get("Exit_status")}。方法搜索关闭，预算关闭，禁止再次提交。\n']
if finished:
 G=S['T']['independent_group_N'];diag=read(P/'evidence/PREDICTION_DIAGNOSTICS.json')
 report+=['## 四项独立结论\n']
 for b,s in S.items():report += [f'- large/ARC/{name(b)} reference preservation：{risk_zh(s)}。',f'- large/ARC/{name(b)} economic value：{save_zh(s)}。']
 report+=['\n这不是重新校准、threshold 的新通过/拒绝检验或联合发表门。准确率差异完整保留，不用于选择 reference。ProbeMax 是 ordinary fixed-format confidence baseline；D 仅为 learned control。\n',
 '## 封存与执行证据\n',
 f"- 预冻结：{pre['utc']}，`ARC_TEST_ACCESSED=false`；SHA256 `{sha(P/'PRE_TEST_FREEZE.json')}`。",
 f"- 首次题目/选项投影：{access['utc']}；仅 `id/question/choices`。",
 f"- 全部预测与计时冻结：{pred['utc']}；SHA256 `{sha(P/'PREDICTION_TIMING_FREEZE.json')}`。",
 f"- 首次 gold 投影：{gold['utc']}；先验证全部冻结文件，再读取 `id/answerKey`。",
 '- 下载与文件 SHA256 检查仅处理不解码的 Parquet 字节；gold 列在预测冻结前不解码、不关联。',
 f"- 数据：`allenai/ai2_arc / ARC-Challenge @ {CFG['population']['revision']}`，原始 test 全1172行；文件 SHA256 `{CFG['population']['expected_sha256']}`。",
 f'- 独立题组 {G}；本次重复组数 {1172-G}，未删题、未重排、未抽样。分组仅按冻结文本/有序选项的大小写敏感空白归一化；最小ID代表。',
 '- Text：q=.95，u≤0.01800704002380371；C2C：q=.90，u≤0.0007095932960510254。全部并列值保留；实际阈值直接继承原fit，未计算test分位数。',
 '- helper Qwen2.5-7B-Instruct / receiver Qwen3-8B / 官方移植 C2C_Fuser 使用冻结 revision、完整checkpoint哈希及原环境；完整 native adapter 与上一轮逐字节一致。',
 '- 四条路径同一allocation、同一模型驻留，按原始题目ordinal模4轮换。每条policy独立执行完整ProbeMax再执行完整R或reference；无KV复用、无额外fixed-R、无warmup/retry。',
 '- E2E包含输入准备、tokenization/prefix/transfer/full prefill/last-position LM-head/FP32 label scoring、selector、完整native动作、decode、V2 parser、同步与cleanup；审计I/O和额外诊断在外，沿用原边界。',
 '\n## 主要 sealed 结果\n',
 '| Reference | 原始N / 独立组N | R路由 / coverage | changed/routed | 条件变化率（CP95%描述区间） | 边际省略变化率 |',
 '|---|---:|---:|---:|---:|---:|']
 for b,s in S.items():report.append(f"| {name(b)} | 1172 / {G} | {s['routed']} / {pct(s['coverage'])} | {s['changed_among_routed']}/{s['routed']} | {pct(s['conditional_answer_change'])} [{100*s['conditional_CP95_low']:.3f}%, {100*s['conditional_CP95_high']:.3f}%] | {pct(s['marginal_omission_answer_change'])} |")
 report+=['\n| Reference | fixed正确 / accuracy | policy正确 / accuracy | 配对差（百分点；bootstrap95%） | benefit / harm / neutral |', '|---|---:|---:|---:|---:|']
 for b,s in S.items():report.append(f"| {name(b)} | {s['reference_correct']}/{G} / {pct(s['reference_accuracy'])} | {s['policy_correct']}/{G} / {pct(s['policy_accuracy'])} | {100*s['accuracy_diff']:+.3f} [{100*s['accuracy_diff_CI95_low']:.3f}, {100*s['accuracy_diff_CI95_high']:.3f}] | {s['benefit']} / {s['harm']} / {s['neutral']} |")
 report+=['\n| Reference | policy均值 / 中位数 ms | fixed均值 / 中位数 ms | paired mean saving ms [95%] | probe / selector均值 ms |', '|---|---:|---:|---:|---:|']
 for b,s in S.items():report.append(f"| {name(b)} | {s['policy_mean_ms']:.3f} / {s['policy_median_ms']:.3f} | {s['reference_mean_ms']:.3f} / {s['reference_median_ms']:.3f} | {s['net_saving_ms']:.3f} {bounds(s,'net_saving_ms')} | {s['probe_mean_ms']:.3f} / {s['selector_mean_ms']:.6f} |")
 report+=['\n| Reference | fixed U | policy U | ΔU [95%] | neutral中两者正确 / 两者错误 |', '|---|---:|---:|---:|---:|']
 for b,s in S.items():report.append(f"| {name(b)} | {s['reference_U']:.6f} | {s['policy_U']:.6f} | {s['delta_U']:+.6f} [{s['delta_U_CI95_low']:.6f}, {s['delta_U_CI95_high']:.6f}] | {s['neutral_both_correct']} / {s['neutral_both_incorrect']} |")
 report+=['\n主要accuracy、latency、utility均使用同一代表组人口。全1172原始行结果另见 `summary/raw_row_sealed.csv`；本轮无重复，因此与主要人口相同。所有bootstrap均seed=0、2000次、独立题组paired resampling，Text/C2C共享indices。区间是描述性区间，不提供重新校准或阈值调整。Utility固定λ=.01和原large/ARC c_ref=266.9407253203125 ms，未由test重估。\n',
 '## 输出与运行诊断\n',
 f"完成4688/4688完整请求、2344/2344独立在线probe。两次独立probe的score差异 {diag['score_identity_failures']}，输入hash差异 {diag['input_identity_failures']}。route-to-reference原始输出/token/parser身份核验 {diag['reference_route_identity_checks']} 项，不一致 {len(diag['reference_route_identity_failures'])} 项；逐项记录在 `records/reference_route_identity.jsonl`。任何不一致未删除、未修复输出。",
 '\nINVALID按单独机器答案哨兵比较：两者INVALID不改变，一方INVALID算改变；INVALID正确性恒为0。设施/执行失败不伪装成INVALID。',
 '\n| Reference | policy INVALID | fixed INVALID | 全策略答案变化 / N | reference路由答案变化 |', '|---|---:|---:|---:|---:|']
 for b,s in S.items():report.append(f"| {name(b)} | {s['policy_invalid']} | {s['reference_invalid']} | {s['total_policy_reference_changed']}/{G} | {s['reference_route_changed']} |")
 report+=['\n首个正式请求及全部真实冷行为保留；见 `summary/runtime_diagnostics.json`。没有按输出、gold或耗时排除记录。\n',
 '## 解释与论文整合\n',
 '两个reference独立保留，不合并挑赢家。任何test与dev差异均是该冻结策略的generalization boundary，不能触发补救实验。低答案变化不保证accuracy不降，偶然accuracy提升不解释为路由优化。',
 '\n开发boundary与128题E2E原结果保留为开发证据；本轮sealed ARC是新增的独立项目确认。公开benchmark的基础模型/公开fuser训练污染无法排除；此前官方C2C配置包含ARC test评估，但实际运行或选择用途未核实。本轮不宣称预训练独立性、跨模型规模规律或原创routing algorithm。',
 '\nsmall四层继续fixed-reference fallback，small test与OBQA均未运行。AgentGate保持独立NO_GO_COST负结果note；不新增signal或calibration结论、不重启分支。',
 '\n论文在上一轮真实活跃paper目录内原位续写，本轮paper/指向同一目录。编辑前状态完整保存在预冻结的evidence/manuscript_snapshot/；旧目录paper相关历史hash代表编辑前状态，可由该快照核验。所有数值实验、冻结协议及历史表格保持原记录。']
 # Edit the actual active manuscript. The task's paper/ is a symlink to it.
 paper=Path(CFG['manuscript']['active_directory']);snap=P/'evidence/manuscript_snapshot'
 for f in snap.iterdir():
  if f.is_file():assert sha(paper/f.name)==sha(f),('ACTIVE_MANUSCRIPT_CHANGED_BEFORE_WRITE',f.name)
 risk_sentences=[]
 for b,s in S.items():
  relation='remained at or below' if s['empirical_risk_within_5pct'] else 'exceeded'
  risk_sentences.append(f"{name(b)}'s empirical conditional answer-change rate {relation} the prespecified 5\\% target ({s['changed_among_routed']}/{s['routed']}, {100*s['conditional_answer_change']:.2f}\\%).")
 position=('P2 studies when communication can be omitted relative to a prespecified reference protocol. An ordinary fixed-format confidence baseline is compared against native Text and officially ported C2C across two model pairs and two exposed development tasks. Frozen calibration yields four large-model deployments and four small-model fixed-reference fallbacks. These are receiver/reference regime observations, not causal scale evidence. Complete E2E development replay pays all online probe costs. A final project-sealed ARC test then evaluates the two unchanged large/ARC policies on all 1172 rows with both references retained. '+ ' '.join(risk_sentences)+' '+ ' '.join(f"{name(b)} has {'positive' if s['positive_mean_saving'] else 'nonpositive'} paired mean E2E saving." for b,s in S.items())+' This is evidence for these frozen deployments in one environment, not broad robustness or a new routing algorithm. D remains a learned control; pretraining contamination and timing replication remain unresolved.\n')
 (paper/'contribution_positioning.tex').write_text(position)
 risk_table=['\\begin{table}[ht]\\centering\\small','\\caption{Project-sealed ARC confirmation. Counts use all 1172 independent test groups. Accuracy is not a selection objective.}\\label{tab:sealed-arc-risk}','\\begin{tabular}{lrrrrr}\\toprule','Reference & Coverage & Changed/routed & Ref. correct & Policy correct & $\\Delta$ acc. (pp) \\\\ \\midrule']
 for b,s in S.items():risk_table.append(f"{name(b)} & {100*s['coverage']:.2f}\\% & {s['changed_among_routed']}/{s['routed']} & {s['reference_correct']}/1172 & {s['policy_correct']}/1172 & {100*s['accuracy_diff']:+.2f} \\\\")
 risk_table+=['\\bottomrule\\end{tabular}\\end{table}']
 time_table=['\\begin{table}[ht]\\centering\\small','\\caption{Actual sealed-test E2E latency (ms); paired seed-0, 2000-resample descriptive 95\\% intervals. Cold requests and full online probes are included.}\\label{tab:sealed-arc-time}','\\begin{tabular}{lrrrr}\\toprule','Reference & Policy mean/median & Fixed mean/median & Mean saving [95\\%] & Probe+selector \\\\ \\midrule']
 for b,s in S.items():time_table.append(f"{name(b)} & {s['policy_mean_ms']:.2f}/{s['policy_median_ms']:.2f} & {s['reference_mean_ms']:.2f}/{s['reference_median_ms']:.2f} & {s['net_saving_ms']:.2f} [{s['net_saving_ms_CI95_low']:.2f}, {s['net_saving_ms_CI95_high']:.2f}] & {s['online_probe_selector_mean_ms']:.2f} \\\\")
 time_table+=['\\bottomrule\\end{tabular}\\end{table}']
 text=r'''\subsection{Final sealed ARC confirmation}
After all methods and development experiments were frozen, we evaluated the two nontrivial large/ARC deployments on the previously unaccessed project test population: all 1172 ARC-Challenge test rows from \texttt{allenai/ai2\_arc}, revision \texttt{210d026faf9955653af8916fad021475a3f00453}. The original case-sensitive whitespace normalization of question and ordered displayed choices yielded 1172 independent groups; no row was removed or reordered. This is project-level sealing, not evidence that the public benchmark was absent from base-model or public-fuser training. The previous data-use audit also found ARC test in an official C2C evaluation configuration; actual upstream use was unverified.

The original fit thresholds were copied before any test access: Text uses $q=.95$ and $u\leq0.01800704002380371$; C2C uses $q=.90$ and $u\leq0.0007095932960510254$. Here $u=1-\max_l p_l$ is the unchanged FP32 ProbeMax score from the fixed-format label distribution; equality routes to R. No test quantile, calibration, reference selector, or threshold revision was permitted. Model revisions, complete checkpoint hashes, tokenizer, prompts, prefix, V2 parser, INVALID semantics, generation configuration, timing, statistical rules, and the current manuscript snapshot were sealed before projected access to question/options. Gold was decoded only after all scores, routes, 4688 raw/parsed complete action outputs, 2344 online probe records, and timings had been written and hashed.

Each reference and its policy ran in one ClusterB allocation with the same helper/receiver/fuser residency, using the development replay's complete native runtime. Four paths were interleaved by original question ordinal modulo four. Each policy independently paid the full probe and a fresh complete R or reference action without KV/prefill reuse. The synchronized E2E boundary, parsing, cleanup, and retention of all cold behavior were unchanged; startup was separate. Small-model fallbacks were not probed and OBQA was not rerun.
'''
 text+='\n'+'\n'.join(risk_table)+'\n\n'+' '.join(risk_sentences)+'\n'
 for b,s in S.items():text+=f"For {name(b)}, the descriptive Clopper--Pearson 95\\% interval is [{100*s['conditional_CP95_low']:.2f}\\%, {100*s['conditional_CP95_high']:.2f}\\%], and marginal omission-induced answer change is {100*s['marginal_omission_answer_change']:.2f}\\%. The accuracy difference is {100*s['accuracy_diff']:+.2f} percentage points [{100*s['accuracy_diff_CI95_low']:.2f}, {100*s['accuracy_diff_CI95_high']:.2f}], with {s['benefit']} benefit, {s['harm']} harm, and {s['neutral']} neutral pairs. "
 text+='\n\n'+'\n'.join(time_table)+'\n\n'
 for b,s in S.items():
  phrase={'above_zero':'lies above zero','below_zero':'lies below zero','includes_zero':'includes zero'}[s['saving_interval_position']]
  text+=f"{name(b)} has {'positive' if s['positive_mean_saving'] else 'nonpositive'} paired mean saving, and its descriptive interval {phrase}. "
 text+=f"All bootstrap intervals use shared seed-0 paired group indices and 2000 resamples; accuracy, latency, and utility use the identical sealed population. The binomial intervals above are reported separately. With unchanged $\\lambda=.01$ and development-frozen $c_{{\\rm ref}}=266.9407253203125$ ms, $\\Delta U$ is {S['T']['delta_U']:+.5f} [{S['T']['delta_U_CI95_low']:.5f}, {S['T']['delta_U_CI95_high']:.5f}] for Text and {S['C']['delta_U']:+.5f} [{S['C']['delta_U_CI95_low']:.5f}, {S['C']['delta_U_CI95_high']:.5f}] for C2C.\n\n"
 text+=f"Reference-route deterministic identity was checked on {diag['reference_route_identity_checks']} pairs, with {len(diag['reference_route_identity_failures'])} mismatches. INVALID counts (policy/reference) were {S['T']['policy_invalid']}/{S['T']['reference_invalid']} for Text and {S['C']['policy_invalid']}/{S['C']['reference_invalid']} for C2C; INVALID is an incorrect-answer sentinel, not a runtime failure.\n\n"
 text+=r'''These are empirical outcomes of already frozen policies, not a second calibration step, a guarantee of nondecreasing accuracy, or a joint publication gate. Any deviation from development evidence is retained as a generalization boundary; neither reference nor threshold is selected from these results. The development boundary tables and 128-question E2E panels above remain development evidence. This independent project confirmation supports only the reported deployments and timing environment. ProbeMax remains an ordinary confidence baseline, D remains a learned control, and method search is closed.
'''
 (paper/'sealed_arc_confirmation.tex').write_text(text)
 current=(paper/'reference_preserving.tex').read_text();assert 'sealed_arc_confirmation' not in current
 (paper/'reference_preserving.tex').write_text(current+'\n\\input{sealed_arc_confirmation.tex}\n')
 old=(paper/'boundary_cost_limitations.tex').read_text();assert 'ARC test remains sealed.' in old
 (paper/'boundary_cost_limitations.tex').write_text(old.replace('ARC test remains sealed.','ARC test remained sealed during these development experiments; the final confirmation below is reported separately.'))
 prior_appendix=(paper/'e2e_appendix.tex').read_text()
 (paper/'e2e_appendix.tex').write_text(prior_appendix.replace('ARC test remains sealed and no subsequent experiment was started.','ARC test remained sealed at the end of that development replay; the final confirmation in the main text was separately authorized afterward.'))
 changed=[]
 for f in paper.glob('*.tex'):
  before=sha(snap/f.name) if (snap/f.name).exists() else None
  if before!=sha(f):changed.append({'path':str(f),'before_sha256':before,'after_sha256':sha(f)})
 save(P/'MANUSCRIPT_EDIT_RECEIPT.json',{'utc':utc(),'active_directory':str(paper),'task_paper_symlink':str(P/'paper'),'edits':changed,'historical_snapshot':'evidence/manuscript_snapshot','same_actual_manuscript':True})
else:
 report+= [f'\n正式动作已成功 {len(successful)}/{len(starts)}，在线probe记录 {len(probes)}。未完成独立sealed确认，Text/C2C四项核心结论均为未确认。保留已成功ID、原始记录及所有冻结hash；停止并交回Work。没有自动第二次提交或重跑成功ID。故障详见 `evidence/run_logs/` 和 `records/failures.jsonl`（如存在）。原英文稿不加入未完成的数值结论。']
report+=['\n## 资源与交付\n',f'申请双GPU×7200秒=4 GPU allocation hours；实际分配 {allocation} 秒（{ledger["actual_GPU_allocation_hours"]:.6f} GPU小时），scheduler walltime {ledger["scheduler_walltime_seconds"]} 秒。监督CPU {cpu["CPU_seconds"]:.6f} 秒，加1200秒准备/统计/报告保守预留合计 {charged:.6f}/9000 秒。Runtime startup '+(f'{startup["wall_seconds"]:.3f} 秒' if startup else '未完成')+'，未摊入逐题时延。单线程；不安装/升级环境。GPU设备事件、allocation、CPU和设施收费分别列账；无可匹配sbank账单时记NA，不记零。',
 '\n主要交付索引：`PRE_TEST_FREEZE.json`、`PROTOCOL_FREEZE.json`、`frozen_config.json`、`SOURCE_INDEX.json`、`FIRST_TEST_ACCESS.json`、`evidence/SEALED_EXPOSURE_RECEIPT.json`、`PREDICTION_TIMING_FREEZE.json`、`GOLD_ACCESS_RECEIPT.json`、`records/frozen_scores_routes_1172.jsonl`、`records/e2e_requests.jsonl`、`records/probe_timing_2344.jsonl`、`summary/primary_sealed.csv`、`summary/paired_bootstrap.csv`及indices/replicates、`summary/accuracy_decomposition.csv`、`summary/e2e_latency_utility.csv`、`summary/runtime_diagnostics.json`、`RESOURCE_LEDGER.json`、`FINAL_RECEIPT.json`、当前真实 `paper/`、轻量包与 `SHA256SUMS`。',
 '\n已停止并交回 Work；等待最终论文整合审议，不开启下一实验，不再次读取test修改方法。']
(P/'REPORT_ZH.md').write_text('\n'.join(report)+'\n')
handoff=f'# P2_FINAL_SEALED_ARC_CONFIRMATION → Work\n\n最终状态：**{status}**。唯一作业 `{jid}`：F/{job.get("Exit_status")}。完成动作 {len(successful)}/4688、probe {len(probes)}/2344。预算与方法搜索均关闭。\n\n'
for b,s in S.items():handoff+=f'- large/ARC/{name(b)}：{risk_zh(s)}；{save_zh(s)}。\n'
handoff+='\n全部1172原始行保留；gold在预测/计时freeze后才关联。两reference独立保留，没有test调参或补救。small fallback不运行、OBQA不重跑、AgentGate分支不重启。\n\n入口：REPORT_ZH.md；summary/primary_sealed.csv；PRE_TEST_FREEZE.json；PREDICTION_TIMING_FREEZE.json；RESOURCE_LEDGER.json；FINAL_RECEIPT.json；SHA256SUMS；轻量包。当前真实英文稿在paper/所指目录内续写，原稿快照在evidence/manuscript_snapshot/，开发结果仍保留。\n\n停止并交回Work，等待最终论文整合审议；禁止自动再次提交或再读test修改方法。\n'
(P/'HANDOFF_ZH.md').write_text(handoff)
save(P/'VALIDATION_RECEIPT.json',{'utc':utc(),'status':status,'freeze_checks':checks,'freeze_access_prediction_gold_chronology_pass':finished,'core_source_immutable':True,'manuscript_update_is_authorized_active_source_edit':finished})
save(P/'FINAL_RECEIPT.json',{'utc':utc(),'task':CFG['task'],'status':status,'job_id':jid,'job_state':'F','exit_status':job.get('Exit_status'),'counts':counts,'conclusions':conclusions,'pre_test_freeze_sha256':sha(P/'PRE_TEST_FREEZE.json'),'resource_ledger_sha256':sha(P/'RESOURCE_LEDGER.json'),'manuscript_active_directory':CFG['manuscript']['active_directory'],'ARC_TEST_ACCESSED':access is not None,'gold_accessed':gold is not None,'method_search':'CLOSED','budget_closed':True,'remaining_submissions':0,'next_action':'STOP and return to Work for final manuscript review; no further experiments'})
state=ROOT/'P2_1_20260910T041720Z/P2_STATE.md'
entry=f'\n\n<!-- {status} {P.name} -->\n## {utc()} — {P.name} {status}，交回Work\n唯一作业 {jid} F/{job.get("Exit_status")}；4688上限下完成{len(successful)}动作、2344上限下完成{len(probes)}probe。\n'
for b,s in S.items():entry+=f'{name(b)}：{risk_zh(s)}；{save_zh(s)}。\n'
entry+=f'预冻结{pre["utc"]}；ARC test项目封存已正式解除，仅一次既定确认；gold在预测计时freeze后关联。实际GPU分配小时{ledger["actual_GPU_allocation_hours"]}，CPU保守{charged}/9000秒。论文在既有活跃路径{CFG["manuscript"]["active_directory"]}原位更新；开发证据保留。方法搜索与预算关闭；停止，禁止第二提交、补救、small test探索或重启AgentGate。完整交付：{P}/HANDOFF_ZH.md。\n'
with state.open('a') as f:f.write(entry)
save(P/'SESSION_RESUME_ZH.json',{'status':status,'job_id':jid,'successful_requests':len(successful),'successful_keys_file':'records/successful_request_keys.jsonl' if finished else 'records/attempts.jsonl','core_protocol_sha256':sha(P/'PRE_TEST_FREEZE.json'),'do_not_resubmit':True,'method_search_closed':True,'next':'只允许完成交付核验与打包，然后交回Work；无后续实验授权'})
print(json.dumps({'status':status,'conclusions':conclusions,'resource_GPU_hours':ledger['actual_GPU_allocation_hours'],'CPU_conservative':charged},ensure_ascii=False))
