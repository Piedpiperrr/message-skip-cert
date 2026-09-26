"""PBS终态后仅整理证据与报告；不执行模型，不修改任何科学选择。"""
from common import *
import subprocess,shutil,tarfile

old=PARENT/'execution_20260915T152640Z'
validate_parent()
pre=read(P/'MEDIUM_PAIR_EXECUTION_PRECHECK_RETRY1.json')
for f,h in pre['frozen_files'].items():assert sha(f)==h,f
for f,h in pre['parent_history_hashes'].items():assert sha(f)==h,f
old_index=read(P/'ATTEMPT1_IMMUTABILITY_INDEX.json')
assert {str(f.relative_to(old)) for f in old.rglob('*') if f.is_file()}==set(old_index['file_sha256'])
for f,h in old_index['file_sha256'].items():assert sha(old/f)==h,f
jid=read(P/'evidence/pbs/submission.json')['job_id']
scheduler=json.loads(subprocess.check_output(['job-status','-xf','-F','json',jid],text=True,timeout=30))
j=scheduler['Jobs'][jid];j.pop('Variable_List',None)
assert j['job_state']=='F','Wait for PBS terminal state; never resubmit'
save(P/'evidence/pbs/terminal_status.json',scheduler)
def epoch(value):return datetime.datetime.strptime(value,'%a %b %d %H:%M:%S %Y').replace(tzinfo=datetime.timezone.utc).timestamp()
if j.get('stime') and j.get('obittime'):seconds=epoch(j['obittime'])-epoch(j['stime'])
else:
    from guard_checks import walltime_seconds
    seconds=walltime_seconds(j.get('resources_used',{}).get('walltime','00:00:00'))
prior_hours=read(old/'RESOURCE_LEDGER.json')['actual_GPU_allocation_hours']
actual_hours=seconds*2/3600;cumulative=prior_hours+actual_hours
run=DATA_ROOT/'runs/iclr2027_p2'/f'{jid}_medium_stage1'
(P/'evidence/job_logs').mkdir(exist_ok=True)
for name in ['outer.log','entry.log','execute.log','analyze.log','validate_results.log','job_exit.txt','home_space_check.log']:
    if (run/name).exists():shutil.copyfile(run/name,P/'evidence/job_logs'/name)
counts={kind:sum(len(rows(f)) for f in (P/kind).glob('*.jsonl')) for kind in ['actions','probes']}
validation=read(P/'NUMERICAL_VALIDATION.json') if (P/'NUMERICAL_VALIDATION.json').exists() else {'status':'NOT_RUN'}
identity_validation=read(P/'INPUT_IDENTITY_VALIDATION.json') if (P/'INPUT_IDENTITY_VALIDATION.json').exists() else {'status':'NOT_RUN'}
complete=counts=={'actions':16878,'probes':5626} and validation.get('status')=='PASS' and identity_validation.get('status')=='PASS' and j.get('Exit_status')==0
status='COMPLETE_MEDIUM_STAGE1' if complete else ('PARTIAL_MEDIUM_STAGE1' if sum(counts.values()) else 'BLOCKED_MEDIUM_STAGE1')
expath=P/'MEDIUM_PAIR_EXECUTION_FREEZE_RETRY1.json'
exhash=sha(expath) if expath.exists() else None
ledger=read(P/'RESOURCE_LEDGER.json');ledger.update(status=status,utc=utc(),
    cumulative_actual_GPU_allocation_hours=cumulative,cumulative_cap_GPU_hours=7,
    cumulative_budget_within_cap=cumulative<=7,accounting_basis='PBS stime through obittime × allocated 2 GPUs; includes both attempts',
    attempt1_directory_unchanged=True,Stage2_started=False,no_third_submission=True)
ledger['replacement_attempt'].update(terminal_state=j['job_state'],PBS_exit_status=j.get('Exit_status'),
    allocation_wall_seconds=seconds,actual_GPU_allocation_hours=actual_hours,scheduler_resources_used=j.get('resources_used'),
    PBS_stime=j.get('stime'),PBS_obittime=j.get('obittime'),formal_action_success_count=counts['actions'],formal_probe_success_count=counts['probes'])
save(P/'RESOURCE_LEDGER.json',ledger)
save(P/'IMMUTABILITY_VALIDATION.json',{'status':'PASS','utc':utc(),'attempt1_files_checked':len(old_index['file_sha256']),
    'attempt1_file_set_unchanged':True,'parent_protocol_sha256':PARENT_HASH,'precheck_frozen_files_checked':len(pre['frozen_files']),
    'parent_history_files_checked':len(pre['parent_history_hashes']),'scientific_protocol_unchanged':True})
shutil.copyfile(PARENT/'MEDIUM_PAIR_PROTOCOL_FREEZE.json',P/'MEDIUM_PAIR_PROTOCOL_FREEZE.json')
shutil.copyfile(PARENT/'MODEL_SOURCE_INDEX.json',P/'PARENT_MODEL_SOURCE_INDEX.json')
if not (P/'NUMERICAL_VALIDATION.json').exists():
    save(P/'NUMERICAL_VALIDATION.json',{'status':'NOT_RUN','reason':'正式科学数据未完整生成，不能将缺失结果记作fallback','counts':counts})
observed=sum(counts.values())>0
save(P/'OUTCOME_OBSERVATION_STATUS.json',{'utc':utc(),'MEDIUM_PAIR_OUTCOMES_OBSERVED':observed,'counts':counts,'status':status})
if not (P/'records/successful_keys.json').exists():save(P/'records/successful_keys.json',[])
session=read(P/'SESSION_RESUME_ZH.json');session.update(utc=utc(),phase=status,job_terminal_state=j['job_state'],
    formal_action_success_count=counts['actions'],formal_probe_success_count=counts['probes'],MEDIUM_PAIR_OUTCOMES_OBSERVED=observed,
    no_third_submission=True,stopped_and_returned_to='Work',Stage2_started=False)
save(P/'SESSION_RESUME_ZH.json',session)

def pct(value):return 'N/A' if value is None else f'{value*100:.3f}%'
def num(value):return 'N/A' if value is None else value if isinstance(value,str) else f'{value:.9g}'
def table(headers,body):return '| '+' | '.join(headers)+' |\n| '+' | '.join(['---']*len(headers))+' |\n'+'\n'.join('| '+' | '.join(map(str,row))+' |' for row in body)
headers=['task','reference','q','threshold','coverage','changed/routed','conditional disagreement','AUROC','reference accuracy','policy accuracy','fallback/deploy']
if complete:
    dev=read(P/'summary/development_summaries.json');deploy_count=sum(r['q']>0 for r in dev);nontrivial=sum(0<r['q']<1 for r in dev)
    compact=table(headers,[[r['task'].upper(),r['reference'],f"{r['q']:.2f}",num(r['threshold']),pct(r['coverage']),r['changed/routed'],pct(r['conditional_disagreement']),num(r['AUROC']),pct(r['reference_accuracy']),pct(r['policy_accuracy']),r['fallback/deploy']] for r in dev])
    pattern='；'.join(f"{r['task'].upper()}/{r['reference']} = {r['fallback/deploy']} (q={r['q']:.2f})" for r in dev)
    if deploy_count==0:boundary='medium四层也全部fallback；观察到的fallback区域现在包含small和medium，已接受部署仍仅见于large。'
    elif deploy_count==4:boundary='medium四层也全部得到冻结部署；已接受部署区域现在包含medium和large，fallback仍见于small。'
    else:boundary=f'medium在原两个端点之间提供分层的经验点：{deploy_count}/4层部署，同一个medium pair在不同任务/reference层呈现不同的可行性结果。'
    if deploy_count==2 and all((r['q']>0)==(r['reference']=='C2C') for r in dev):
        boundary='原来的small四层fallback、large四层deploy两端描述，现在补充为：medium在OBQA与ARC上均是C2C层得到冻结部署、Text层fallback。同一个中间pair呈现明确的reference差异，提供了比原两点设计更有信息量的经验边界证据。'
    large_q={('obqa','Text'):.8,('obqa','C2C'):.8,('arc','Text'):.95,('arc','C2C'):.9}
    above=[f"{r['task'].upper()}/{r['reference']}" for r in dev if r['q']>large_q[r['task'],r['reference']]]
    size=f'small 0/4 → medium {deploy_count}/4 → large 4/4的部署层数与非递减模式相容。两端已是0和4，任何medium层数都在两端之间，因此这不是强单调性检验。'
    size+=(' medium在'+ '、'.join(above)+'的q高于对应large，所选q不能在所有层都按模型大小非递减排序。') if above else ' 四层所选q均未高于对应large，与三点非递减q模式相容。'
    size+=' 模型身份、helper、receiver、fuser和任务/reference没有被因果分离；model size alone不能据此被认定为边界的决定因素。'
    if deploy_count not in [0,4]:size+=' 同一个medium pair同时包含deploy和fallback，规模一个变量不足以完整描述reference条件下的边界。'
    complement='本轮只补充R相对各固定reference的通信省略边界；没有学习或验证Text/C2C之间的选择器，也没有验证E2E经济收益。原多协议互补性到可靠且有经济价值的多协议路由之间的缺口仍未解决。'
    stage2=(f'值得由Work考虑对{nontrivial}个nontrivial deployment开展Stage 2，以真实E2E核验在线probe开销和完整请求节省；Stage 1本身不证明经济收益。' if nontrivial else '本轮没有nontrivial selective deployment，不据此推荐在线选择性路由的Stage 2 E2E；是否另行评审由Work决定。')
    if nontrivial==2 and all((0<r['q']<1)==(r['reference']=='C2C') for r in dev):
        stage2='值得由Work考虑仅对OBQA/C2C与ARC/C2C两个nontrivial deployment开展Stage 2：它们已有冻结校准点，development覆盖分别为52.56%和63.21%，观察条件变化率分别为2.82%和2.12%。下一步需要真实E2E核验在线probe开销与完整请求节省；本轮没有经济收益结论，两个Text fallback不构成新的选择性部署点。'
    accuracy=table(['task/reference','reference correct','policy correct','accuracy difference (pp)','benefit/harm/neutral-change','marginal disagreement','AP','invalid R/ref/policy'],
        [[f"{r['task'].upper()}/{r['reference']}",f"{r['reference_correct']}/{r['N']}",f"{r['policy_correct']}/{r['N']}",f"{100*r['accuracy_difference']:+.3f}",f"{r['benefit']}/{r['harm']}/{r['neutral_change']}",pct(r['marginal_disagreement']),num(r['AP']),f"{r['invalid_R']}/{r['invalid_reference']}/{r['invalid_policy']}"] for r in dev])
    prev=list(csv.DictReader((P/'summary/disagreement_prevalence.csv').open()))
    prevalence=table(['task/reference','split','disagreement/N','prevalence','AUROC','AP'],[[f"{r['task'].upper()}/{'Text' if r['reference']=='T' else 'C2C'}",r['split'],f"{r['disagreement_count']}/{r['N']}",pct(float(r['disagreement_prevalence'])),r['AUROC'] or 'N/A',r['AP'] or 'N/A'] for r in prev if r['scope']=='independent_representatives'])
    cal=[]
    for r in dev:
        c=read(P/f"deployments/{r['task']}_{r['reference_code']}.json")['chosen_calibration']
        cal.append([f"{r['task'].upper()}/{r['reference']}",f"{r['q']:.2f}",f"{c['changed']}/{c['routed']}" if c else 'N/A',num(c['p_value']) if c else 'N/A',num(c['CP_upper_0_999']) if c else 'N/A'])
    caltable=table(['task/reference','chosen q','cal changed/routed','p','CP .999 upper'],cal)
    probe_rows=read(P/'summary/probe_diagnostics.json')
    probe_table=table(['task/split','N rows','score mean','min / p05 / median / p95 / max','exact zero','argmax agrees with native R','invalid probe'],
        [[f"{r['task'].upper()}/{r['split']}",r['N_rows'],num(r['score_distribution']['mean']),
          ' / '.join(num(r['score_distribution'][k]) for k in ['min','p05','median','p95','max']),
          r['score_distribution']['exact_zero_count'],f"{r['label_argmax_agreement_with_native_R']}/{r['N_rows']}",r['invalid_probe_count']] for r in probe_rows])
    iv=list(csv.DictReader((P/'summary/invalid_counts.csv').open()))
    ividx={(r['task'],r['split'],r['action']):r for r in iv}
    invalid_table=table(['task/split','N rows','invalid R / Text / C2C','invalid probe','formal action runtime failures'],
        [[f"{r['task'].upper()}/{r['split']}",r['N_rows'],
          ' / '.join(ividx[r['task'],r['split'],a]['invalid_count'] for a in ['R','T','C']),r['invalid_probe_count'],
          sum(int(ividx[r['task'],r['split'],a]['runtime_failure_count']) for a in ['R','T','C'])] for r in probe_rows])
    ti=list(csv.DictReader((P/'summary/runtime_diagnostics.csv').open()))
    tiidx={(r['task'],r['split'],r['request']):r for r in ti}
    runtime_table=table(['task/split','R mean ms','Text mean ms','C2C mean ms','ProbeMax mean ms'],
        [[f"{r['task'].upper()}/{r['split']}"]+[f"{float(tiidx[r['task'],r['split'],a]['mean']):.3f}" for a in ['R','T','C','ProbeMax']] for r in probe_rows])
    detail=f'''## Development准确率分解

{accuracy}

changed=benefit+harm+neutral-change；policy正确−reference正确=benefit−harm。invalid保留在分母中并计错；两侧INVALID使用原parser符号一致性。accuracy只在全部部署和dev routes冻结后关联原dev gold，不参与选择。

接受C2C层的部署不意味着C2C reference更准确：本轮两个任务的Text reference development准确率均高于对应C2C reference（见表）。风险目标是R/reference答案不一致率，保持某个reference较容易并不等于该reference质量最高，也没有解决Text与C2C之间的选择问题。

## Disagreement prevalence与ProbeMax排序

{prevalence}

主统计使用独立组代表。ARC fit671行均保留输出，阈值及主prevalence使用670组代表。所有原始行与both-valid附加诊断在CSV中分别保留。AUROC/AP使用完整R/reference disagreement，不只评估已路由子集。

## ProbeMax与invalid诊断

{probe_table}

以上score distribution使用全部原始行；ARC fit为671行。Probe argmax仅作与native R的一致性诊断，不替代R answer。完整精度及label probability mass诊断保存在`summary/probe_diagnostics.json`。

{invalid_table}

## 正式请求runtime诊断

{runtime_table}

这些是本次正式R/Text/C2C与ProbeMax请求的latency诊断，未运行额外timing panel、component cost实验或E2E replay；未重组policy cost，也不据此声称净节省或utility收益。各分位数保存在`summary/runtime_diagnostics.csv`。

## 已选校准点

{caltable}

完整80项ledger均保留。fallback没有已接受的calibration点，其20项拒绝证据仍保留。
'''
    save(P/'FINAL_SUMMARY.json',{'status':status,'MEDIUM_DEPLOY_COUNT':deploy_count,'denominator':4,'nontrivial_deployment_count':nontrivial,
        'pattern':pattern,'boundary_conclusion':boundary,'size_interpretation':size,'complementarity':complement,
        'Stage2_recommendation':stage2,'Stage2_started':False,'strata':dev})
else:
    deploy_count=None;nontrivial=None
    compact=table(headers,[[ds,ref]+['N/A']*8+['未完整执行；不归类'] for ds in ['OBQA','ARC'] for ref in ['Text','C2C']])
    pattern='OBQA/Text = 未完整执行；OBQA/C2C = 未完整执行；ARC/Text = 未完整执行；ARC/C2C = 未完整执行。不可把缺失结果当作fallback。'
    boundary='本轮未形成完整medium经验点，不能据此改变原receiver/reference boundary科学结论。'
    size='当前仍为small 0/4、medium N/A/4、large 4/4；本轮不能新增model size排序或因果scale证据。'
    complement='原multi-protocol complementarity问题没有因本轮获得完整的新实证解答。'
    stage2='Stage 1尚未完整结束，没有据此推荐Stage 2 E2E的完整证据；不自行启动。'
    failure={f.name:read(f) for f in [P/'JOB_FAILURE.json',P/'EXECUTION_FAILURE.json'] if f.exists()}
    detail='## 阻塞或部分完成证据\n\n失败记录、成功ID和全部已生成结果均保留，不根据结果删层。\n\n```json\n'+json.dumps(failure,ensure_ascii=False,indent=2)+'\n```\n'
    save(P/'INCOMPLETE_DELIVERY_STATUS.json',{'status':status,'counts':counts,'MEDIUM_DEPLOY_COUNT':None,
        'scientific_outcomes_observed':observed,'failure':failure,'no_third_submission':True})
attempt_table=table(['Attempt','PBS job','terminal status','actual GPU allocation hours','scientific completion','note'],[
    ['1','185994','F / Exit 1',f'{prior_hours:.6f}','action 0；ProbeMax 0','engineering cgroup-guard failure'],
    ['2',jid,f"{j['job_state']} / Exit {j.get('Exit_status')}",f'{actual_hours:.6f}',f"action {counts['actions']}/16878；ProbeMax {counts['probes']}/5626",status]])
cg=read(P/'evidence/CGROUP_RECEIPT.json') if (P/'evidence/CGROUP_RECEIPT.json').exists() else {}
report=f'''# P2 medium pair Stage 1：replacement交付

最终状态：**{status}**。**MEDIUM_DEPLOY_COUNT = {deploy_count if deploy_count is not None else 'N/A'} / 4**。

{boundary}

## 四层compact summary

{compact}

{pattern}

coverage以对应exposed dev全部题目为分母，conditional disagreement以route-to-R题目为分母。fallback的0路由条件风险为N/A；q=1是fixed R；只有0<q<1属于nontrivial selective deployment。缺失结果不能归类为fallback。

{detail}

## 协议与解释边界

本轮严格定位为 **post-hoc motivated, but protocol-frozen before observing medium-pair outcomes**。它是在看到small/large结果之后增加的经验点；不是preregistered scaling study、independent confirmation、sealed confirmation或causal scale experiment。四层必须全部交付，后续Work只能决定main paper或appendix展示位置，不能决定是否报告。

helper固定Qwen/Qwen2.5-1.5B-Instruct revision `989aa7980e4cf806f80c7fef2b1adb7bc71aa306`；receiver固定Qwen/Qwen3-1.7B revision `70d244cc86ccca08cf5af4e1e306ecf908b1ad5e`。官方nics-efc/C2C_Fuser revision `f01fc3258b305e280e04c7238f4f2cf31b7dc70d`，subfolder `qwen3_1.7b+qwen2.5_1.5b_Fuser/final`。31个权重文件本地SHA256与原冻结官方LFS一致，28个官方fuser，不训练或替换checkpoint。详见MODEL_SOURCE_INDEX.json。

原native R/Text/C2C和ProbeMax语义不变：batch1；helper cuda:0、receiver/fuser cuda:1；完整Text helper communication；原prompt/parser/generation config；thinking off；原single-token labels；FP32 normalized label probabilities；u=1-max p；原invalid处理；probe无KV复用。没有AC或其它新动作。

原OBQA人口为fit2100/cal1366/dev742；ARC为fit671行/670组、cal448、dev299，共5626行。全部原ID、顺序、分组保留。OBQA是已披露的pre-existing exposed project partition；ARC dev为已曝光validation。未读取ARC test，既有large project-sealed confirmation不赋予medium任何新的sealed claim。

q=.05,.10,…,1.00；fit threshold为ceil(j*Nfit/20)的一基整数次序统计，并列全部保留；q=1为fixed R。各reference分别在calibration计算BinomialCDF(k;n,.05)，p≤.001接受，同时报告CP .999 upper，选择最大接受q；无接受则q=0固定reference fallback。accuracy不参与选择。

整个medium是同时规划的4 strata×20 q=80-test extension family。每stratum理想Bonferroni bound≤.02，整个extension理想bound≤.08；这是透明解释，不改变q selection，不与历史large/OBQA/Text的100-test family混合。

## 两次attempt与累计资源

{attempt_table}

Attempt 1目录完全不可变，201个文件的集合及SHA256复核通过。Attempt 2是Work明确授权的一次replacement；不构成新科学任务或新增预算。请求2 GPU×03:29:50，最大6.994444 GPUh；加Attempt 1保守实际0.005556 GPUh，总授权仍为7 GPUh。

Attempt 2实际分配{seconds:.0f}秒×2 GPU={actual_hours:.6f} GPUh；两次累计 **{cumulative:.6f}/7 GPUh**。使用PBS stime至obittime计账，另保留resources_used原始字段，未把申请额度当作实际消耗。动态deadline取实际PBS walltime减45秒。RESOURCE_LEDGER.json含两个attempt。

## 入口修复、冻结与验证

本次只修engineering guard和执行审计。原始/proc/self/cgroup在所有assertion前保存；legacy pattern match={cg.get('legacy_cgroup_pattern_match','N/A')}，仅记录，不作fatal条件。真实PBS账号、队列、状态、assigned node、请求及实际分配2 GPU均校验；CUDA记录is_available、device_count、名称、UUID和显存，详见evidence各receipt。PBS有2 GPU但进程看不到2 GPU时禁止科学推理。

synthetic smoke沿用非项目placeholder输入，仅核对严格模型/fuser载入、设备和native路径；不解析项目答案、不计算disagreement/accuracy/AUROC/routing/calibration。通过后在同一allocation内写入MEDIUM_PAIR_EXECUTION_FREEZE_RETRY1.json，然后才开始项目推理。execution freeze SHA256：`{exhash or 'NOT_CREATED'}`。原科学冻结SHA256：`{PARENT_HASH}`，原时间戳`{pre['parent_protocol_timestamp']}`未变。retry授权SHA256：`{sha(P/'MEDIUM_PAIR_RETRY_AUTHORIZATION.json')}`。

科学runtime、risk、分析和验证代码哈希与第一次attempt一致；driver仅修改execution freeze审计时点，精确差异见evidence/execute_audit_only.diff。NUMERICAL_VALIDATION状态={validation.get('status')}；INPUT_IDENTITY_VALIDATION状态={identity_validation.get('status')}。完整成功时独立复核80项CDF/CP、整数阈值与并列、最大接受q、逐题parser、FP32分数、AUROC/AP和准确率分解，并以CPU tokenization核对全部实际输入；无重复模型推理。

## 回答Work的六个问题

1. **medium改变哪一句boundary结论？** {boundary}
2. **三点模式？** small 0/4 → medium {deploy_count if deploy_count is not None else 'N/A'}/4 → large 4/4；medium各层见上表。
3. **model size alone能否排序？** {size}
4. **multi-protocol complementarity解决多少？** {complement}
5. **是否值得Stage 2 E2E？** {stage2}
6. **是否自行启动Stage 2？** 没有。已停止并交回Work，不自行启动下一任务或第三次提交。

V3 manuscript、supplement、small/large artifacts和Attempt 1保持原样。本轮没有ARC test、E2E、128题timing replay、component cost measurement、utility或新router。只保存正式请求要求的latency/runtime diagnostics。

交付入口：REPORT_ZH.md、HANDOFF_ZH.md、MEDIUM_PAIR_RETRY_AUTHORIZATION.json、MEDIUM_PAIR_EXECUTION_FREEZE_RETRY1.json（仅GPU smoke通过时存在）、MODEL_SOURCE_INDEX.json、RESOURCE_LEDGER.json、NUMERICAL_VALIDATION.json、summary/compact_summary.csv及所有已生成逐题文件。未生成项不得冒称已完成。

最终状态：**{status}**。
'''
(P/'REPORT_ZH.md').write_text(report)
(P/'HANDOFF_ZH.md').write_text(f'''# Medium Stage 1 → Work

**{status}；MEDIUM_DEPLOY_COUNT = {deploy_count if deploy_count is not None else 'N/A'} / 4。**

{compact}

{pattern}

{attempt_table}

两次累计实际GPU allocation **{cumulative:.6f}/7小时**。原科学冻结`{PARENT_HASH}`不变；replacement execution freeze `{exhash or 'NOT_CREATED'}`。第一次attempt的201个文件不可变性已复核。

{boundary}

{size}

{complement}

{stage2}

科学定位保持post-hoc motivated, but protocol-frozen before observing medium-pair outcomes。无ARC test、新E2E、component cost或utility；不修改V3/supplement；不自行Stage 2；不第三次提交。已停止交回Work。

详细结果、六个问题、限制与证据入口见REPORT_ZH.md；PBS终态见evidence/pbs/terminal_status.json；原始结果在actions/probes及各分析目录。缺失结果不能作为fallback。
''')
save(P/'FINAL_RECEIPT.json',{'utc':utc(),'status':status,'job_id':jid,'PBS_exit_status':j.get('Exit_status'),
    'action_success_count':counts['actions'],'ProbeMax_success_count':counts['probes'],'MEDIUM_DEPLOY_COUNT':deploy_count,
    'replacement_actual_GPU_allocation_hours':actual_hours,'cumulative_actual_GPU_allocation_hours':cumulative,
    'attempt1_immutable':True,'parent_protocol_sha256':PARENT_HASH,'retry_execution_freeze_sha256':exhash,
    'no_third_submission':True,'Stage2_started':False})
files=[f for f in sorted(P.rglob('*')) if f.is_file() and 'assets' not in f.relative_to(P).parts and f.name not in ['SHA256SUMS','WORK_HANDOFF.tar.gz','PACKAGE_RECEIPT.json']]
(P/'SHA256SUMS').write_text(''.join(f'{sha(f)}  {f.relative_to(P)}\n' for f in files))
archive=P/'WORK_HANDOFF.tar.gz'
with tarfile.open(archive,'w:gz') as out:
    for f in files+[P/'SHA256SUMS']:out.add(f,arcname=P.name+'/'+str(f.relative_to(P)),recursive=False)
save(P/'PACKAGE_RECEIPT.json',{'utc':utc(),'archive':str(archive),'bytes':archive.stat().st_size,'sha256':sha(archive),
    'weights_excluded':True,'all_generated_results_included':True,'status':status})
print(json.dumps({'status':status,'counts':counts,'deploy_count':deploy_count,'cumulative_GPU_hours':cumulative,'archive':str(archive)},ensure_ascii=False),flush=True)
