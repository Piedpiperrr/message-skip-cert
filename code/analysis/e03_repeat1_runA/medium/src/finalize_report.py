"""Chinese delivery and actual PBS allocation accounting; never launches work."""
from common import *
import math,shutil,tarfile
from guard_checks import walltime_seconds
jid=read(P/'evidence/pbs/submission.json')['job_id']
terminal=read(P/'evidence/pbs/terminal_status.json');job=terminal['Jobs'][jid]
assert job['job_state']=='F','Do not finalize a live job'
run=DATA_ROOT/f'runs/iclr2027_p2/{jid}_medium_stage2'
logs=P/'evidence/job_logs';logs.mkdir(exist_ok=True)
for name in ['entry.log','outer.log','job_exit.txt','home_space_check.log']:
    if (run/name).exists():shutil.copy2(run/name,logs/name)
def parse_time(value):
    if value is None:return None
    if isinstance(value,(int,float)):return float(value)
    try:return datetime.datetime.strptime(value,'%a %b %d %H:%M:%S %Y').replace(tzinfo=datetime.timezone.utc).timestamp()
    except ValueError:return datetime.datetime.fromisoformat(value.replace('Z','+00:00')).timestamp()
start_epoch=parse_time(job.get('stime'));exit_epoch=None
if (run/'job_exit.txt').exists():
    fields=dict(line.split('=',1) for line in (run/'job_exit.txt').read_text().splitlines())
    exit_epoch=parse_time(fields['ended_utc'])
wall=walltime_seconds(job.get('resources_used',{}).get('walltime','00:00:00'))
end_candidates=[parse_time(job.get('obittime')),exit_epoch]
observed=[math.ceil(t-start_epoch) for t in end_candidates if t is not None and start_epoch is not None]
allocation_seconds=max([wall]+observed)
allocation_GPUh=allocation_seconds*2/3600
ledger=read(P/'RESOURCE_LEDGER.json');ledger.update(status='TERMINAL',job_id=jid,terminal_state='F',exit_status=job.get('Exit_status'),
    PBS_requested_walltime=job['Resource_List']['walltime'],requested_GPU_allocation_hours=.5,
    scheduler_resources_used=job.get('resources_used'),scheduler_wall_seconds=wall,PBS_stime=job.get('stime'),
    PBS_obittime=job.get('obittime'),shell_exit_epoch=exit_epoch,conservative_allocation_wall_seconds=allocation_seconds,
    actual_GPU_allocation_hours=allocation_GPUh,allocation_GPU_count=2,
    accounting_rule='2 allocated GPUs times max(scheduler wall, PBS start-to-shell-exit, PBS start-to-obittime); resources_used.ngpus is not allocation count',
    max_submissions=1,submissions=1,retries=0,second_submission_allowed=False,
    historical_Stage1_budget_not_reopened=True,actual_billing_GPUh=None,actual_billing_note='scheduler allocation accounting only; no billing receipt queried',utc=utc())
save(P/'RESOURCE_LEDGER.json',ledger)
def cs(name):return list(csv.DictReader((P/'summary'/name).open()))
def table(headers,rr):return '\n'.join(['| '+' | '.join(headers)+' |','| '+' | '.join(['---']*len(headers))+' |']+['| '+' | '.join(map(str,r))+' |' for r in rr])
def f(v,d=3):return format(float(v),'.'+str(d)+'f')
def pc(v):return format(float(v)*100,'.2f')+'%'
records=rows(P/'records/e2e_requests.jsonl') if (P/'records/e2e_requests.jsonl').exists() else []
is_complete=(P/'NUMERICAL_VALIDATION.json').exists() and read(P/'NUMERICAL_VALIDATION.json')['status']=='PASS' and len(records)==512
status='COMPLETE_MEDIUM_STAGE2' if is_complete else 'PARTIAL_MEDIUM_STAGE2' if records else 'BLOCKED_MEDIUM_STAGE2'
if not is_complete:
    failure=read(P/'JOB_FAILURE.json') if (P/'JOB_FAILURE.json').exists() else dict(error='See terminal/log receipts')
    report=f'''# Medium Stage 2 → Work

**{status}**

唯一作业 `{jid}` 已结束，PBS F / exit {job.get('Exit_status')}。完整请求保存 {len(records)}/512，policy probe 保存 {sum(r.get('probe') is not None for r in records)}/256。成功 IDs/keys 原样保留在 records；没有第二次提交。

失败证据：`JOB_FAILURE.json`、`REQUEST_FAILURE.json`（若产生）、`evidence/job_logs/`、`evidence/pbs/terminal_status.json`。

原因：{failure.get('error')}。阶段：{failure.get('phase')}。

两项 E2E classification 均 N/A（未完整，不能把缺失记为阴性或fallback）。实际GPU allocation {allocation_GPUh:.6f}/0.5 GPUh；不扩大预算。

原Stage1 freeze与阈值未修改；无ARC test、Text replay、新calibration/router/threshold/gold、论文或supplement修改。停止并交回Work，不自动下一任务。
'''
    (P/'REPORT_ZH.md').write_text(report);(P/'HANDOFF_ZH.md').write_text(report)
    if not (P/'NUMERICAL_VALIDATION.json').exists():save(P/'NUMERICAL_VALIDATION.json',dict(status='INCOMPLETE',saved_requests=len(records),no_claims_from_partial=True))
    save(P/'FINAL_RECEIPT.json',dict(status=status,job_id=jid,saved_requests=len(records),second_submission=False,utc=utc()))
else:
    summary=cs('medium_e2e_summary.csv');proxy=cs('proxy_vs_e2e.csv');checks=cs('output_identity_checks.csv');diag=cs('runtime_diagnostics.csv')
    startup=read(P/'evidence/STARTUP.json');validation=read(P/'NUMERICAL_VALIDATION.json');cfg=read(FREEZE)
    assert allocation_GPUh<=.5
    both_positive=all(r['classification']=='E2E_POSITIVE' for r in summary)
    main_table=table(['task','q / 精确threshold','R覆盖','policy / C2C正确','policy / C2C mean ms','paired mean saving ms','95%描述区间 ms','分类'],[
        [r['task'].upper(),r['q']+' / '+r['threshold'],r['route_to_R_count']+'/128 ('+pc(r['coverage'])+')',
        r['policy_correct']+' / '+r['fixed_C2C_correct'],f(r['policy_mean_latency_ms'])+' / '+f(r['fixed_C2C_mean_latency_ms']),
        f(r['paired_mean_saving_ms']),'['+f(r['descriptive_CI95_low_ms'])+', '+f(r['descriptive_CI95_high_ms'])+']',r['classification']] for r in summary])
    out=['# Medium pair Stage 2：真实在线 C2C omission E2E',
        '**COMPLETE_MEDIUM_STAGE2；已停止并交回 Work。**',
        '## 1. 主结论\n\n'+('两个预定 medium/C2C 层均满足预先冻结的正节省 gate：paired mean saving > 0，且 paired bootstrap 描述性95%区间下界 > 0。' if both_positive else '两个预定 medium/C2C 层的完整结果如下；未通过 gate 的结果同样保留。')+'\n\n'+main_table,
        '这是 **development-panel E2E evidence**。面板已曝光，不能称 sealed confirmation、independent test 或新 policy selection。所有数值来自本轮实际完整在线路径；没有用 Stage 1 action latency 拼成 E2E 结果。',
        '## 2. Panel 与冻结 identity\n\nOBQA128、ARC128 都逐项复用 P2-10 / confidence-boundary / 既有 large E2E 的原始 ID 顺序，128个独立题目组，无抽样、删题或根据 medium outcome 选子集。历史 panel freeze 时间为2026-09-14，早于 medium outcomes。small 的历史 timing panel 也是同一 identity；原 small fallback 未被称为做过选择性 E2E。\n\n'+
        table(['task','panel ID 文件 SHA256','query文件 SHA256'],[[ds.upper(),cfg['panels'][ds]['ids_sha256'],cfg['panels'][ds]['query_sha256']] for ds in ['obqa','arc']]),
        f"Stage 1 scientific freeze SHA256：`{cfg['parent_Stage1_scientific_freeze_sha256']}`。Stage 2 freeze SHA256：`{sha(FREEZE)}`，时间 `{cfg['utc']}`，在提交和任何正式请求之前生成，`MEDIUM_STAGE2_RESULTS_OBSERVED=false`。Stage 1 deployment config hash、两个完整精度 threshold、model/fuser revisions/local hashes、runtime hashes、PBS script hash、rotation、bootstrap和预算均在其中。没有重新计算 panel quantile。",
        '## 3. 真实执行边界与资源\n\n同一 ClusterB PBS allocation、同一 model residency：helper cuda:0，receiver/fuser cuda:1，batch1。exact Stage 1 native runtime 文件保持逐字同hash。helper/receiver加载无missing/unexpected/mismatched keys；官方28个fuser strict加载。沿用原prompt/tokenizer/parser/generation；thinking off、FP32 ProbeMax、u<=冻结threshold、并列全部保留。\n\n原question order不变；偶数ordinal fixed C2C→policy，奇数ordinal policy→fixed C2C，每task两种路径顺序各64题。两个task按OBQA→ARC执行。没有warmup或synthetic forward，第一正式请求保留。\n\nfixed路径执行完整native C2C；policy先完整在线ProbeMax，再实际执行完整native R或C2C。probe使用use_cache=False，输出KV不进入action；probe argmax不作为R答案。\n\n权威计时为外层同步wall timer，覆盖input preparation、probe tokenization/transfer/full prefill/last-position projection/FP32概率、selector、selected完整native action、decode、V2 parser、hook cleanup和最终双GPU synchronization。原native运行诊断也在外层计时内。磁盘记录、之后的gold关联/identity比较不在单题计时内。启动不摊入单题。',
        f"唯一作业 `{jid}`：PBS **F / Exit_status={job.get('Exit_status')}**；分配 `{job.get('exec_vnode')}`。申请2 GPUs×15分钟=0.5 GPUh，实际保守分配 {allocation_seconds} 秒×2 = **{allocation_GPUh:.6f} GPUh**。计入startup、入口hash核对和收尾；PBS resources_used.ngpus不替代allocation卡数。正式完整请求512/512、policy probe256/256，失败0、重试0。无第二提交。",
        '### startup 单列\n\n'+table(['项目','秒'],[[role,f(t)] for role,t in startup['load_seconds'].items()]+[
            ['strict模型/runtime初始化总计',f(startup['startup_wall_seconds'])],['native runtime import',f(startup['runtime_import_seconds'])],
            ['含import startup总计',f(startup['startup_total_including_runtime_import_seconds'])]]),
        '## 4. 完整主指标\n\n'+table(['task','policy median ms','fixed C2C median ms','paired saving median ms','mean saving占C2C','accuracy Δpp','policy / C2C invalid','online probe / selector mean ms'],[
            [r['task'].upper(),f(r['policy_median_latency_ms']),f(r['fixed_C2C_median_latency_ms']),f(r['paired_median_saving_ms']),pc(r['paired_mean_saving_fraction']),
             f(r['accuracy_difference_pp']),r['policy_invalid']+' / '+r['fixed_C2C_invalid'],f(r['ProbeMax_outer_mean_latency_ms'])+' / '+f(r['selector_mean_latency_ms'],6)] for r in summary]),
        'paired saving定义为每题fixed C2C−policy；median saving是逐题差的中位数，不是两个median相减。bootstrap按paired question、seed0、2,000次、百分位95%区间，第一题与INVALID全保留。描述性classification不提供总体安全/收益保证。\n\n完整字段含probe+selector均值和accuracy见 `summary/medium_e2e_summary.csv`；bootstrap及固定indices另存。',
        '### 首个正式请求保留\n\n'+table(['task/arm','首题ID','首请求 ms'],[[r['task'].upper()+'/'+r['arm'],r['first_request_id'],f(r['first_request_ms'])] for r in diag])+\
        '\n\nOBQA首题fixed C2C约3.269秒、policy约0.814秒，二者都进入主均值和bootstrap。该显著首请求差异是本次按冻结顺序执行的观测，不应把报告直接解释成反复请求的纯稳态速度保证；没有删首题、截尾或重跑以改变结果。模型加载仍在startup另计。',
        '## 5. 输出与分数 identity 完整性']
    identity_rows=[]
    for ds in ['obqa','arc']:
        r=[r for r in checks if r['task']==ds]
        def count(prefix):
            vals=[x[prefix] for x in r if x[prefix]!=''];return str(sum(v=='True' for v in vals))+'/'+str(len(vals))
        identity_rows.append([ds.upper(),count('policy_C_vs_same_round_fixed_C_raw_match'),count('policy_C_vs_same_round_fixed_C_parsed_match'),
            count('policy_R_vs_Stage1_R_raw_match'),count('policy_R_vs_Stage1_R_parsed_match'),count('online_ProbeMax_exactly_matches_Stage1'),count('online_route_matches_Stage1')])
    out += [table(['task','routeC raw一致','routeC parsed一致','routeR/Stage1 raw一致','routeR/Stage1 parsed一致','ProbeMax精确一致','route一致'],identity_rows),
        f"共 {validation['identity_mismatch_rows']} 个identity诊断差异行。route C 对同轮fixed C2C，route R 对Stage1保存的native R；raw、parsed、token IDs均保存比较。另记录fixed C2C与Stage1 C2C及probe输入hash。任何差异保留，不筛题、不为匹配而重跑；原始输出和解析均可逐题追溯。runtime failure与INVALID分开，INVALID计错且留在分母。",
        '## 6. 与既有 arithmetic proxy 比较\n\n'+table(['task','旧full-dev proxy ms','actual panel E2E saving ms','actual−proxy ms','方向说明'],[
            [r['task'].upper(),f(r['prior_proxy_ms']),f(r['actual_E2E_mean_saving_ms']),f(r['actual_minus_proxy_ms']),r['directional_description']] for r in proxy]),
        '旧proxy的公开四舍五入值为OBQA +68.32、ARC +105.38 ms/题；主表保留来源完整精度，CSV另列相对公开值的差。旧proxy用完整dev742/299上的保存latency与冻结route，本轮是历史panel128的真实两臂在线执行。两者不是同批次、同人口、同计时边界的控制实验；差值只描述proxy与actual的位置，不归因于硬件或模型规模。',
        '## 7. 回答 Work 的解释问题',
        '### 1）是否不仅 safe，而且 worth omitting？\n\n'+('在本报告限定意义下，两项均支持worth omitting：Stage1已有原有限样本conditional answer-disagreement风险门的冻结部署，Stage2在已曝光panel上又得到正latency saving及正描述区间下界。' if both_positive else 'worth omitting必须逐task看上述gate，不能把Stage1风险门通过自动转换成经济收益。')+'这里safe仅指原R/reference答案分歧风险协议，不是gold准确率不降、事实正确、安全性或总体保证。accuracy差异如实单列，未参与任何新选择。',
        '### 2）OBQA/ARC是否一致？\n\n'+('两任务的E2E方向和gate一致，均为E2E_POSITIVE；覆盖、节省大小和accuracy变化仍按各自人口报告。' if both_positive else '两任务分类如主表，完整报告差异，不删除不利结果。'),
        '### 3）与large C2C E2E相比，支持什么boundary story？']
    large=list(csv.DictReader((P/'inputs/large_C2C_E2E_summary.csv').open()))
    comparison=[]
    for r in summary:
        l=next(z for z in large if z['dataset']==r['task'])
        comparison.append([r['task'].upper(),pc(r['coverage']),f(r['paired_mean_saving_ms']),pc(l['coverage']),f(l['net_saving_ms']),
            '['+f(l['CI95_saving_low'])+', '+f(l['CI95_saving_high'])+']'])
    out += [table(['task','medium覆盖','medium saving ms','large覆盖','历史large saving ms','历史large95%区间 ms'],comparison),
        '同一历史panel identity上，small四层fallback，medium只C2C两层nontrivial、Text仍fallback，large两reference四层均deploy。'+
        ('本轮进一步表明medium两个C2C部署也有已曝光panel的正E2E节省，因而补足了中间receiver/reference regime从风险可行到经济可行的一个经验点。' if both_positive else '本轮为中间regime补充经济边界，显示风险可行与经济可行必须分别检验。')+
        '这比仅有small/large两端更完整，但不构成Text/C2C多协议selector的验证，Text fallback不重放。',
        '### 4）不作跨规模因果速度规律\n\nmedium/large虽复用panel，运行时间、allocation、权重、helper/receiver/fuser身份和记录仪器仍不同；绝不根据mean saving排序推出模型规模导致速度或省略可行性。仅描述reference-conditioned empirical regimes。',
        '### 5）停止\n\nStage 2是本轮唯一授权E2E。无ARC test1172、无Text选择性重放、无small/large重跑、无新router/calibration/threshold/gold、无utility search、无V3/supplement修改。停止并交回Work，不自动启动下一任务。',
        '## 8. 数值核验与交付\n\n`NUMERICAL_VALIDATION.json`：PASS。用独立标量加总/百分位插值复核paired bootstrap；核对512唯一request、256probe、各128个pair、rotation64/64、精确阈值应用、计时parts求和、correctness、identity差异计数和所有来源hash/mtime不变。\n\n- `records/e2e_requests.jsonl`：真实原始请求、output、parsed answer、probe、route、latency、输入ID和运行证据。\n- `records/fixed_C2C_requests_with_correctness.jsonl`、`policy_requests_with_correctness.jsonl`：重放完成后关联既有gold。\n- `summary/medium_e2e_summary.csv`、`paired_latency_bootstrap.csv`、`proxy_vs_e2e.csv`、`runtime_diagnostics.csv`、`output_identity_checks.csv`：五个规定summary。\n- `summary/probe_timing.csv`、`paired_per_question.csv`、bootstrap indices与源码：可复核配套。\n- `MEDIUM_PAIR_E2E_STAGE2_FREEZE.json`、`SOURCE_INDEX.json`、`RESOURCE_LEDGER.json`、PBS回执、`SHA256SUMS`：冻结/资源/完整性。',
        '\n'.join(r['task'].upper()+'_C2C_E2E = '+r['classification'] for r in summary)+'\n\n**COMPLETE_MEDIUM_STAGE2**']
    (P/'REPORT_ZH.md').write_text('\n\n'.join(out)+'\n')
    handoff=f'''# Medium Stage 2 → Work

**COMPLETE_MEDIUM_STAGE2**。唯一作业 `{jid}` 已F / exit {job.get('Exit_status')}；实际保守GPU allocation **{allocation_GPUh:.6f}/0.5 GPUh**。512/512完整请求、256/256在线ProbeMax；0失败、0重试、无第二提交。

{main_table}

两任务均使用结果前已有的原128题panel及原顺序；阈值直接来自Stage1完整精度JSON。Stage2 freeze SHA256：`{sha(FREEZE)}`。同allocation同residency、helper cuda:0 / receiver-fuser cuda:1、batch1；每题交替两路径顺序，第一正式请求保留。完整计时包括online probe、selector、真实selected native action、decode/parser和同步清理；startup单列。不是Stage1 latency拼接。

identity诊断差异行：{validation['identity_mismatch_rows']}；routeC对同轮fixed C2C，routeR对Stage1 native R，任何差异保留、不筛题不重跑。

'''+table(['task','旧proxy ms','actual−proxy ms'],[[r['task'].upper(),f(r['prior_proxy_ms']),f(r['actual_minus_proxy_ms'])] for r in proxy])+'''

旧proxy来自full dev742/299，新结果来自128题实际E2E；差异混合人口、批次和计时边界，不能硬件因果归因。

本轮是development-panel E2E evidence，非sealed confirmation、independent test或policy selection。safe仅沿用Stage1 conditional R/reference answer-disagreement协议，非gold准确率不降保证。

'''+('两个C2C层在暴露panel上均有正mean saving和正描述95%下界，支持worth omitting。结合small fallback、medium C2C deploy/Text fallback、large四层deploy，为reference-conditioned boundary补充一个有风险与经济证据的经验点。' if both_positive else '按task逐项保留gate结果；风险可行不能自动推出经济可行。')+'''

不作跨规模因果速度规律；没有验证multi-protocol selector。无ARC test、Text replay、新calibration/threshold/router/gold、utility、V3/supplement修改。

入口：[REPORT_ZH.md](REPORT_ZH.md)、五个summary CSV、[NUMERICAL_VALIDATION.json](NUMERICAL_VALIDATION.json)、逐题完整请求、源码、freeze和资源账。独立数值核验PASS。

'''+ '\n\n'.join(r['task'].upper()+'_C2C_E2E = '+r['classification'] for r in summary)+'''

**停止并交回Work；不自动启动下一任务。**
'''
    (P/'HANDOFF_ZH.md').write_text(handoff)
    save(P/'FINAL_RECEIPT.json',dict(status=status,utc=utc(),job_id=jid,terminal_state='F',exit_status=job.get('Exit_status'),
        actual_GPU_allocation_hours=allocation_GPUh,complete_requests=512,online_probes=256,freeze_sha256=sha(FREEZE),
        classifications={r['task']:r['classification'] for r in summary},NUMERICAL_VALIDATION='PASS',next_task_started=False))
# Archive source/receipts/output only; never follow assets/ model symlinks.
paths_to_pack=[x for x in P.rglob('*') if x.is_file() and 'assets' not in x.relative_to(P).parts and x.name not in ['SHA256SUMS','WORK_HANDOFF.tar.gz']]
(P/'SHA256SUMS').write_text(''.join(sha(x)+'  '+str(x.relative_to(P))+'\n' for x in sorted(paths_to_pack)))
with tarfile.open(P/'WORK_HANDOFF.tar.gz','w:gz') as tf:
    for x in paths_to_pack+[P/'SHA256SUMS']:tf.add(x,arcname=str(x.relative_to(P)))
print(json.dumps(read(P/'FINAL_RECEIPT.json'),ensure_ascii=False,indent=2))
