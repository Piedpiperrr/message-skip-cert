"""两作业终止后生成中文交付；不执行任何模型或 E2E。"""
import sys
from pathlib import Path
sys.dont_write_bytecode=True
sys.path.insert(0,str(Path(__file__).resolve().parent/'src'))
from common import *
import collections
ledger=read(P/'RESOURCE_LEDGER.json');assert ledger['both_terminal']
validate_freeze()
complete=(P/'ANALYSIS_COMPLETE.json').exists()
if complete:
    validation=read(P/'NUMERICAL_VALIDATION.json');assert validation['status']=='PASS'
    table=read(P/'summary/compact_table.json');deploy=read(P/'deployments/deployment_configs.json')['deployments']
    count=validation['MMLU_PRO_DEPLOY_COUNT'];status='COMPLETE_MMLU_PRO_STAGE1'
    allcounts=dict(R=12032,T=12032,C=12032,P=12032);fullrows=12032
else:
    allcounts=collections.Counter();seen=set();perid=collections.defaultdict(set);outfiles=[];bad=[]
    qh=read(P/'protocol/QUERY_IDENTITIES.json')
    for shard in ['1','2']:
        s=P/f'shards/{shard}'
        for path in sorted([*s.glob('actions/*.jsonl'),*s.glob('probes/*.jsonl')]):
            with path.open() as f:
                for line in f:
                    try:r=json.loads(line)
                    except json.JSONDecodeError:bad.append(dict(path=str(path),reason='incomplete_json_line'));continue
                    assert r['key'] not in seen and r['query_sha256']==qh[r['id']]==queryhash(r['query'])
                    seen.add(r['key']);allcounts[r['action']]+=1;perid[r['id']].add(r['action'])
            outfiles.append(dict(path=str(path.resolve()),sha256=sha(path)))
    fullrows=sum(v==set('RTCP') for v in perid.values())
    status='PARTIAL_MMLU_PRO_STAGE1' if seen else 'BLOCKED_MMLU_PRO_STAGE1';count=None
    save(P/'summary/successful_request_keys.json',sorted(seen))
    save(P/'summary/complete_raw_IDs.json',sorted(k for k,v in perid.items() if v==set('RTCP')))
    save(P/'summary/missing_requests.json',{k:[a for a in 'RTCP' if a not in perid.get(k,set())] for k in qh if perid.get(k,set())!=set('RTCP')})
    save(P/'summary/OUTPUT_SOURCE_INDEX.json',outfiles)
    save(P/'NUMERICAL_VALIDATION.json',dict(status='INCOMPLETE_NO_SCIENTIFIC_ANALYSIS',utc=utc(),full_rows=fullrows,expected_rows=12032,
        action_counts={a:allcounts[a] for a in 'RTCP'},expected_actions=36096,expected_probes=12032,unique_request_keys=len(seen),
        incomplete_lines=bad,missing_is_not_fallback=True,scientific_analysis_performed=False))
    for directory,name in [('thresholds','fit_thresholds'),('calibration','40_test_ledger'),('deployments','deployment_configs'),
        ('development','split_summaries'),('development','category_summaries'),('development','K_summaries'),('summary','compact_table')]:
        save(P/directory/(name+'_NOT_COMPUTED.json'),dict(status='NOT_COMPUTED',reason='Full-population completeness gate not met',missing_is_not_fallback=True))
def pct(x):return 'NA' if x is None else f'{100*x:.3f}%'
def num(x):return 'NA' if x is None else f'{x:.6f}' if isinstance(x,float) else str(x)
joblines=['| shard | PBS ID | 提交 UTC | 开始 | 结束 | terminal / exit | 实际 GPUh | R / Text / C2C / ProbeMax |',
    '|---|---|---|---|---|---|---:|---|']
for shard,j in ledger['jobs'].items():
    pg=j.get('progress') or {};cc=pg.get('counts',{})
    joblines.append(f"| {shard} | {j['job_id']} | {j['submission_utc']} | {j['start']} | {j['end']} | {j['job_state']} / {j['terminal_exit_status']} | {num(j.get('actual_GPUh'))} | {' / '.join(str(cc.get(a,0)) for a in 'RTCP')} |")
jobtable='\n'.join(joblines)
header=f'''# MMLU-Pro large pair Stage1 中文报告

最终状态：**{status}**

本轮仅执行获授权的 Stage1。未启动 E2E，未修改 V4 manuscript 或 supplement，未提交第三个正式作业。

## 1. 定位和冻结身份

这是 **post-hoc benchmark breadth extension, protocol-frozen before observing MMLU-Pro model outcomes**。MMLU-Pro test 被项目内部划为 fit/cal/dev，因此整个新增 benchmark 均为 development evidence。它不是 sealed confirmation、independent test、preregistered benchmark study、third-scale replication 或 open-ended generalization。

- 数据：`TIGER-Lab/MMLU-Pro`，revision `b189ec765aa7ed75c8acfea42df31fdae71f97be`。
- 原始 test parquet SHA256：`0e24a191921c2f453518a537a8b2117bd137e7714d4ef1565e9ba06c1ecb9ad8`。
- 总人口 12,032 raw rows，14 categories，K=3–10；没有删行或重分 split。
- fit：3,093 rows / 3,000 groups；cal：6,196 / 6,000；dev：2,743 / 2,641。
- 分组采用冻结的空白归一化题干，代表为每组最小数值 question_id；主分析只使用 11,641 个代表。非代表行保留正式输出和描述统计，不增加独立 n。
- helper `Qwen2.5-7B-Instruct` revision `a09a35458c702b33eeacc393d103063234e8bc28`；receiver `Qwen3-8B` revision `b968826d9c46dd6066d109eabc6255188de91218`；official fuser revision `f01fc3258b305e280e04c7238f4f2cf31b7dc70d`。逐文件哈希见 `MODEL_SOURCE_INDEX.json`。
- 正式冻结 SHA256：`{sha(P/'MMLU_PRO_STAGE1_PROTOCOL_FREEZE.json')}`。原 review/candidate 文件保留不变。

两个固定脚本先 held 提交，双提交确认后统一放行。候选 shard 文件的旧分析时序元数据按本次 Work 指令明确覆盖：两个作业只采集，均终止后才允许统一完整性检查和分析；IDs/group/split 均未改变。

## 2. 执行、资源和完整性

{jobtable}

资源授权上限为 56 GPU allocation hours，实际合计 **{num(ledger.get('actual_GPUh'))} GPUh**；实际值按 PBS stime→obittime × 实际分配 GPU 数计算。每个作业申请 2 GPU、14:00:00，计费包括机械检查、模型加载及退出阶段。

完整 raw rows：**{fullrows}/12,032**。成功 R/Text/C2C actions：**{sum(allcounts.get(a,0) for a in 'RTC')}/36,096**；ProbeMax：**{allcounts.get('P',0)}/12,032**。

每个作业在正式题目前检查 scheduler allocation、CUDA count=2、exact model/fuser load、非 benchmark 合成输入的原生 R/Text/C2C 路径及动态标签。机械收据位于 `shards/<n>/`；PBS、失败及资源证据位于 `evidence/pbs/`、`RESOURCE_LEDGER.json`。

## 3. 不变的方法

ProbeMax 仍为 `u=1-max p`：thinking off、独立完整 prefill、最后有效位置 lm_head 投影；各 label 聚合所有满足 `decode(token).strip()==label` 的非特殊 token variants，然后仅在该题合法 K 个 labels 上 FP32 归一化。没有 probe KV reuse，同 query 只 probe 一次，argmax 仅诊断。

Text 保持原 background-message helper 语义及三消息 receiver consume；C2C 保持 large official fuser/native KV path。适配仅为 schema、动态 options/合法 labels，原 V2 parser 原样支持 A–J。receiver max_new_tokens=64、Text helper=256、greedy 均未改变。

q=.05,.10,…,1.00；fit threshold 为 `ceil(j*Nfit/20)` integer order statistic，保留全部 ties；q=1 为 fixed R。每 reference 独立按 `BinomialCDF(k;n,.05)<=.001` 选最大 accepted q，并报告 CP .999 upper；无接受才是 q=0 fixed-reference fallback。accuracy 不参与选择。invalid 统一为 `INVALID`，两 invalid 相等；runtime failure/缺失不能当 fallback。

新增 2 strata × 20 q =40 tests，per-stratum ideal Bonferroni bound≤.02，本 extension ideal bound≤.04；不与历史 large/OBQA 100-test 或 medium 80-test families 合并成共同 FWER。
'''
if complete:
    lines=['| reference | q | threshold | dev coverage | changed/routed | conditional disagreement | AUROC | reference accuracy | policy accuracy | 状态 |',
        '|---|---:|---:|---:|---|---:|---:|---:|---:|---|']
    for r in table:lines.append(f"| {r['reference']} | {r['q']:.2f} | {num(r['threshold'])} | {pct(r['coverage'])} | {r['changed_over_routed']} | {pct(r['conditional_disagreement'])} | {num(r['AUROC'])} | {pct(r['reference_accuracy'])} | {pct(r['policy_accuracy'])} | {'deploy' if r['q']>0 else 'fallback'} |")
    compact='\n'.join(lines)
    text='\n## 4. 主结果：dev 冻结组代表（N=2,641）\n\n'+compact+f'\n\n**MMLU_PRO_DEPLOY_COUNT = {count} / 2**\n\n'
    for ref in ['T','C']:
        d=deploy[ref];r=next(z for z in table if z['reference']==d['reference']);chosen=d['chosen_calibration']
        text+=f"### {d['reference']}\n\n"
        text+=(f"calibration：routed={chosen['routed']}/6,000，changed={chosen['changed']}，p={chosen['p_value']:.9g}，CP .999 upper={chosen['CP_upper_0_999']:.9g}。\n\n" if chosen else '20 个候选全部未通过 calibration，因此固定 reference；这不是缺失导致的 fallback。\n\n')
        text+=f"dev：AP={num(r['AP'])}；marginal disagreement={pct(r['marginal_disagreement'])}；reference correct={r['reference_correct']}，policy correct={r['policy_correct']}，accuracy difference={pct(r['accuracy_difference'])}；benefit/harm/neutral-change={r['benefit']}/{r['harm']}/{r['neutral_change']}。\n\n"
    text+='14-category 与 K=3…10 统计仅为描述，不用于改变 threshold。raw-row 对照不用于独立风险推断；AUROC/AP 为点估计。主 calibration 与 selection 完全使用冻结代表。\n\n'
    answer1=(f'新增结果使 large development 的部署层数成为 {4+count}/6（既有 4/4，加本轮 {count}/2），仍需按 reference 和 benchmark 判断 boundary。' if count else '本轮两层均 fallback，使 large development 成为 4/6 可部署；这限制了 large regime 的跨 benchmark 外推，不能继续暗示 large 必然可部署。')
    answer2='有，本轮至少一个 reference 获得非零 omission；其含义是校准规则通过，不等于已测得 E2E 净节省。' if count else '没有。本轮完整人口和冻结风险规则下，两 reference 均没有获接受的非零 omission。'
    answer3=('部署/回退状态一致，但具体 q、覆盖率、分歧与准确率仍应分别报告。' if count in [0,2] else '不一致：一个 reference 可部署，另一个 fallback；这直接强化 reference-conditioned boundary 的表述。')
    answer4='值得把已部署 reference 的 Stage2 E2E 交由 Work 决定；Stage1 不能证明真实 E2E 正节省，当前没有 E2E 执行授权。' if count else '当前不值得为 omission 部署启动 Stage2 E2E，因为两 reference 均 fallback；返回 Work。'
    text+='## 5. 返回 Work 的六个回答\n\n'+f'1. **是否改变当前 boundary 结论？** {answer1}\n2. **large 在新 benchmark 上仍有部署吗？** {answer2}\n3. **Text/C2C 是否一致？** {answer3}\n4. **是否值得 Stage2 E2E？** {answer4}\n5. **discrete-choice limitation 如何变化？** 可以把人口描述扩大为 two four-choice science QA benchmarks plus a harder broad-domain variable-choice benchmark；增加 domain breadth 与答案选项数范围，但 evaluation remains discrete-choice，不能宣称 open-ended generality；harder 是 benchmark 定位，不由本轮直接估计跨数据集难度因果差异。\n6. **是否自动启动下一任务？** 否。任务止于 Stage1，交 Work；不启动 E2E，不改论文。\n\n'
    text+='完整执行结果必须进入最终论文或 appendix，无论 deployment/fallback 是否支持既有 story。Work 只决定展示位置，不决定是否隐去。\n'
else:
    compact='| reference | q / threshold / coverage / changed / AUROC / accuracy | 状态 |\n|---|---|---|\n| Text | NOT_COMPUTED | 缺失；不是 fallback |\n| C2C | NOT_COMPUTED | 缺失；不是 fallback |'
    text='\n## 4. 未完成：不计算科学结果\n\n'+compact+'\n\n**MMLU_PRO_DEPLOY_COUNT = NOT_EVALUATED / 2**。完整性门槛未满足，未构造 fit thresholds、未执行 calibration、未选择部署、未做 dev/category/K 科学分析。\n\n'
    for shard,j in ledger['jobs'].items():
        failure=j.get('failure')
        if failure:text+=f"- shard {shard}：phase={failure.get('phase')}；error=`{failure.get('error')}`。原始 traceback 已保留。\n"
    text+='\n## 5. 返回 Work 的六个回答\n\n1. 未获得完整 MMLU-Pro 科学证据，不能改变现有 reference-conditioned boundary 结论。\n2. large 在 MMLU-Pro 是否有可部署 omission 尚未评估。\n3. Text/C2C 是否一致尚未评估，不能将缺失记成共同 fallback。\n4. 目前没有支持 Stage2 E2E 的完整 Stage1 证据；本次也未授权 E2E。\n5. protocol/data 审计支持跨领域、variable-choice 的人口定位，但当前失败/部分执行不能作为完整 benchmark 结果；evaluation remains discrete-choice 的 limitation 不变。\n6. 停止并返回 Work，不自动追加第三个 Stage1 作业或启动下一任务。\n'
tail='''
## 6. 交付索引

- 正式身份与约束：`MMLU_PRO_STAGE1_PROTOCOL_FREEZE.json`、`DATASET_SOURCE_INDEX.json`、`MODEL_SOURCE_INDEX.json`、`splits/`、两个 `run_shard<n>.pbs`。
- 逐题原始/解析答案、invalid、latency、实际 native input token IDs、ProbeMax 概率与 input identity：`shards/<n>/actions/<split>.jsonl`、`shards/<n>/probes/<split>.jsonl`；索引见 `summary/OUTPUT_SOURCE_INDEX.json`。
- 资源、PBS 时间、终止状态与完成计数：`RESOURCE_LEDGER.json`、`evidence/pbs/`。
- 数值门槛：`NUMERICAL_VALIDATION.json`；完整执行时 `thresholds/`、`calibration/`、`deployments/`、`development/`、`summary/compact_table.csv` 提供正式分析。
- 不变性验证：`evidence/FROZEN_SOURCE_VERIFICATION.json`；涵盖 V4 91 文件、16 个选定既有科学来源及 9 个候选 manifests。
- `candidate_e2e128_ids.json` 仅保留候选身份，未执行。
'''
(P/'REPORT_ZH.md').write_text(header+text+tail)
(P/'HANDOFF_ZH.md').write_text(f'''# MMLU-Pro Stage1 → Work

**{status}**

MMLU_PRO_DEPLOY_COUNT = {count if count is not None else 'NOT_EVALUATED'} / 2

{compact}

完整行 {fullrows}/12,032；R/Text/C2C {sum(allcounts.get(a,0) for a in 'RTC')}/36,096；ProbeMax {allcounts.get('P',0)}/12,032。正式 PBS 仅 186115、186116，各 2 GPU / 14h；实际总资源 {num(ledger.get('actual_GPUh'))} GPUh，上限 56 GPUh。

主统计以冻结 normalized-question group representative 为单位（fit/cal/dev=3,000/6,000/2,641）。全部证据定位为 post-hoc benchmark breadth extension / development。缺失不是 fallback。

正式协议 SHA256：`{sha(P/'MMLU_PRO_STAGE1_PROTOCOL_FREEZE.json')}`。双 held 提交确认后放行，两个 shard 结束之前只监控进度与失败。冻结代码/ID/模型/生成配置不变。

完整结果无论方向均必须进入最终论文或 appendix，Work 只决定展示位置。科学解释、六个问题及数值证据见 `REPORT_ZH.md`；资源见 `RESOURCE_LEDGER.json`，完整性见 `NUMERICAL_VALIDATION.json`。

**不自动启动下一任务。E2E 未执行；V4 与 supplement 未修改；无第三个正式 job。**
''')
save(P/'FINAL_STATE.json',dict(utc=utc(),status=status,MMLU_PRO_DEPLOY_COUNT=count,strata=2,formal_PBS_jobs=2,
    actual_GPUh=ledger.get('actual_GPUh'),E2E_jobs=0,manuscript_modified=False,supplement_modified=False,next_task_started=False))
print(status,flush=True)
