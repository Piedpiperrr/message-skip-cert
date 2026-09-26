import sys
from pathlib import Path
sys.dont_write_bytecode=True
sys.path.insert(0,str(Path(__file__).resolve().parent/'src'))
from common import *
import collections
resource=read(P/'RESOURCE_LEDGER.json');assert resource['job_state']=='F'
cfg=verify_freeze();panel=read(P/'protocol/PANEL_MANIFEST.json')
complete=(P/'ANALYSIS_COMPLETE.json').exists() and read(P/'NUMERICAL_VALIDATION.json')['status']=='PASS'
def n(x):return 'NA' if x is None else f'{x:.6f}' if isinstance(x,float) else str(x)
if complete:
    assert read(P/'evidence/FINAL_NUMERICAL_AUDIT.json')['status']=='PASS'
    summary=read(P/'summary/mmlu_pro_e2e_summary.json');status='COMPLETE_MMLU_PRO_STAGE2';N=512;NP=256
    gates={r['reference']:r['classification'] for r in summary}
else:
    rr=[]
    if (P/'records/four_arm_requests.jsonl').exists():
        for line in (P/'records/four_arm_requests.jsonl').read_text().splitlines():
            try:rr.append(json.loads(line))
            except json.JSONDecodeError:pass
    N=len(rr);NP=sum(r['probe'] is not None for r in rr);status='PARTIAL_MMLU_PRO_STAGE2' if N else 'BLOCKED_MMLU_PRO_STAGE2'
    gates={'Text':'NOT_EVALUATED','C2C':'NOT_EVALUATED'}
    save(P/'records/successful_request_keys.json',[r['key'] for r in rr])
    expected={f'mmlu_pro|{i}|{arm}' for i in read(P/'inputs/candidate_e2e128_ids.json') for arm in ARMS}
    save(P/'records/missing_request_keys.json',sorted(expected-{r['key'] for r in rr}))
    save(P/'NUMERICAL_VALIDATION.json',dict(utc=utc(),status='INCOMPLETE_NO_E2E_CLASSIFICATION',complete_requests=N,expected_requests=512,
        online_probes=NP,expected_probes=256,missing_not_negative_result=True,second_submission_forbidden=True))
    for name in ['mmlu_pro_e2e_summary','paired_latency_bootstrap','runtime_diagnostics','output_identity_checks']:
        csvout(P/f'summary/{name}.csv',[dict(status='NOT_EVALUATED',reason='Full 512 request / 256 probe completeness gate not met')])
startup=read(P/'evidence/STARTUP.json') if (P/'evidence/STARTUP.json').exists() else {}
asset=read(P/'evidence/ASSET_HASH_RECHECK.json') if (P/'evidence/ASSET_HASH_RECHECK.json').exists() else {}
header=f'''# MMLU-Pro E2E Stage2 中文报告

**{status}**

MMLU_TEXT_E2E = **{gates['Text']}**

MMLU_C2C_E2E = **{gates['C2C']}**

## 1. 本轮范围与定位

本轮只验证 Stage1 冻结的 Text / C2C omission deployment 相对于各自 fixed reference 的真实完整在线 latency。科学定位为 **post-hoc benchmark breadth extension 上的 exposed development-panel E2E evidence**。MMLU-Pro 官方 test 已被项目内部划成 fit/cal/dev；本轮不是 sealed confirmation、independent test、test confirmation、calibration、threshold selection 或 open-ended generalization。

两个 policy 均直接使用 q=.40、threshold=`3.838539123535156e-05`，按 `u<=threshold` 路由 native R，否则分别路由 native Text/C2C。没有计算 panel quantile，没有新的 policy selection，没有重新校准。

## 2. 结果前冻结 panel 与执行身份

严格使用原 protocol/cost review 的 `candidate_e2e128_ids.json`，原顺序保留。128 IDs 均为冻结 dev normalized-question group representatives，128 个 group 互异；没有按 Stage1 分数、route、correctness、category、K、长度或 invalid 重新选题或删题。

- candidate SHA256：`{panel['candidate_sha256']}`。
- 原文件 mtime：{panel['original_candidate_mtime_utc']}；review recommendation 创建时间：{panel['review_recommendation_created_utc']}。
- 原候选 hash 已被 Stage1 结果前的正式 freeze 固定；Stage1 首个 outcome 时间为 {panel['first_MMLU_Pro_outcome_utc']}。时间和 hash 两条证据均支持 panel 先于模型结果。
- 每题 ID、representative、group hash、category、K、query hash 见 `protocol/PANEL_MANIFEST.json`。
- Stage1 parent freeze SHA256：`{PARENT_HASH}`。
- Stage2 freeze SHA256：`{sha(FREEZE)}`；冻结时间 {cfg['utc']}。
- helper `Qwen2.5-7B-Instruct` revision `a09a35458c702b33eeacc393d103063234e8bc28`；receiver `Qwen3-8B` revision `b968826d9c46dd6066d109eabc6255188de91218`；official C2C fuser revision `f01fc3258b305e280e04c7238f4f2cf31b7dc70d`。模型逐文件 hash、36 个 fuser 及 runtime source hashes 已记录并核对。

Stage1 native runtime 文件逐字节复用；dynamic legal labels、thinking off、FP32 ProbeMax、V2 parser、native Text/C2C、batch1 与生成设置保持原样。helper 在 cuda:0，receiver/fuser 在 cuda:1。两个 policy 各自做完整独立 online ProbeMax，没有共享 probe、KV 或 prefill，没有用 probe argmax 代替 native R。

## 3. 执行、顺序与计时边界

四条 arm 为 fixed Text、Text policy、fixed C2C、C2C policy。同 allocation、同模型 residency、同 runtime，原题目 ordinal modulo 4 对基础 arm 顺序做循环左移。每条 arm 在每个相对位置各 32 次；执行前已冻结，未按 runtime 结果调整。

唯一正式 PBS：`{resource['job_id']}`。提交 {resource['submission_utc']}；开始 {resource['start']}；结束 {resource['end']}；terminal={resource['job_state']}，exit={resource['exit_status']}。申请 **2 GPUs × 01:00:00**，上限 **2 GPUh**，实际 **{n(resource['actual_GPUh'])} GPUh**（PBS stime→obittime × allocated GPUs）。没有第二次提交。

成功完整 action requests：**{N}/512**；成功在线 ProbeMax：**{NP}/256**。startup 与 asset-hash check 分开报告，均不摊入单题 latency。

权威 latency 是同一 outer wall timer：input preparation → policy 独立 ProbeMax 的 tokenization/transfer/full prefill/最后有效位置 lm_head/FP32 label aggregation 与归一化 → selector → 完整 native selected action → decode/V2 parser → cleanup 和双 GPU synchronization。fixed arm 完整执行其 native reference。开始 timer 前先同步清空前序工作；磁盘日志/JSON 序列化、gold/identity 分析不计入 latency。不是 Stage1 latency 拼接。

- startup（runtime import + 模型/fuser 加载）共 {n(startup.get('startup_total_including_runtime_import_seconds'))} 秒。
- 模型/fuser 分项加载秒数：`{json.dumps(startup.get('model_and_fuser_load_seconds',{}),ensure_ascii=False)}`。
- allocation 内 asset-hash recheck 为 {n(asset.get('wall_seconds'))} 秒，另列为执行前身份检查。
- warmup=0、synthetic model forwards=0；第一正式请求保留，不删除冷启动、长 latency、invalid 或 identity mismatch 行。
'''
if complete:
    compact=['| reference | N | R count / coverage | policy / fixed correct | policy / fixed mean ms | paired mean saving ms | paired median saving ms | 描述性 95% CI ms | 分类 |',
        '|---|---:|---|---|---|---:|---:|---|---|']
    detail=['| reference | policy median ms | fixed median ms | probe mean ms | selector mean ms | accuracy difference（百分点） | fixed / policy invalid | identity mismatch |',
        '|---|---:|---:|---:|---:|---:|---|---:|']
    for r in summary:
        compact.append(f"| {r['reference']} | 128 | {r['route_to_R_count']} / {100*r['coverage']:.3f}% | {r['policy_correct']} / {r['fixed_reference_correct']} | {r['policy_mean_ms']:.3f} / {r['fixed_mean_ms']:.3f} | {r['paired_mean_saving_ms']:.3f} | {r['paired_median_saving_ms']:.3f} | [{r['descriptive_bootstrap95_low_ms']:.3f}, {r['descriptive_bootstrap95_high_ms']:.3f}] | {r['classification']} |")
        detail.append(f"| {r['reference']} | {r['policy_median_ms']:.3f} | {r['fixed_median_ms']:.3f} | {r['probe_mean_ms']:.3f} | {r['selector_mean_ms']:.6f} | {r['accuracy_difference_pp']:+.6f} | {r['fixed_invalid']} / {r['policy_invalid']} | {r['identity_mismatches']} |")
    compact='\n'.join(compact)
    body='\n## 4. 主结果\n\n'+compact+'\n\n'+'\n'.join(detail)+'\n\n'
    body+='paired saving 定义为每题 `fixed - policy`。positive gate 对每个 reference 独立应用：paired mean saving>0 且 paired descriptive bootstrap 95% lower>0 才为 E2E_POSITIVE；否则为 E2E_UNCERTAIN_OR_NEGATIVE。Bootstrap 固定 seed=0、2,000 次、question-level paired resampling、128 个原题目；区间为 mean saving 的 percentile 95%，不是独立 test 推断或总体保证。accuracy difference 只作描述，不用于 policy 或 gate 选择。\n\n'
    body+='## 5. Identity、invalid 与失败诊断\n\n'
    identities=list(csv.DictReader((P/'summary/output_identity_checks.csv').open()))
    bad=[r for r in identities if r['required_output_identity_pass']=='False']
    body+=f"route-to-reference 与同轮 fixed reference 比较；route-to-R 与保存的 Stage1 native R 比较。对 raw answer、canonical parsed answer、完整 parser record、generated token IDs（Text reference 路由另核对 helper message）共 256 个 policy 请求逐一检查；required output identity mismatch={len(bad)}。任何差异都保留，没有重跑至一致。\n\n"
    if bad:
        body+='存在输出 identity 差异，详见 `summary/output_identity_checks.csv`；它们不触发删题、重跑、重选 policy 或改 gate。解释 reference-preserving 行为时必须同时保留这些差异证据。\n\n'
    else:body+='所有必需的输出 identity 比较均一致。完整 probe score/input hash、Stage1 route 与 fixed-vs-Stage1 诊断亦保存于 identity 表。\n\n'
    diagkeys=['fixed_vs_Stage1_raw_match','fixed_vs_Stage1_parsed_match','online_probe_equals_Stage1','online_probe_input_hash_matches_Stage1','online_route_matches_Stage1']
    body+='补充 identity 诊断的差异计数：'+ '；'.join(k+'='+str(sum(r[k]=='False' for r in identities)) for k in diagkeys)+'。\n\n'
    body+='runtime failures=0、retries=0；INVALID 是解析结果，单独计数并按 incorrect 关联 gold，始终保留在 latency 配对和 bootstrap 内。完整逐题数据见 `records/four_arm_requests_with_correctness.jsonl`、`records/two_policy_probes.jsonl`、`summary/paired_per_question.csv`。\n\n'
    positive=[r['reference'] for r in summary if r['classification']=='E2E_POSITIVE']
    ans1=('Text 和 C2C 都获得 Stage1 风险规则下的部署，且本轮都满足 E2E_POSITIVE。' if len(positive)==2 else 'Stage1 的两种部署风险资格保持不变；本轮经济 positive gate 仅由 '+('、'.join(positive) if positive else '无 reference')+' 通过。')
    ans1+='“safe”仅指 Stage1 整体 population 上 conditional R/reference answer-disagreement 的冻结校准语义，不是 gold accuracy 不下降、每 category/K 保证或开放式安全性；“worth omitting”仅按本 exposed 128-panel 的真实在线 latency 证据解释。'
    ans2='分类一致，均为 '+gates['Text']+'；节省量仍应分别报告。' if gates['Text']==gates['C2C'] else '不一致：Text='+gates['Text']+'，C2C='+gates['C2C']+'；不能合并成所有 reference 均有正收益。'
    answers='\n## 7. 返回 Work 的五个回答\n\n'+f'1. **是否既 safe 又 worth omitting？** {ans1}\n2. **Text/C2C 经济结果是否一致？** {ans2}\n3. **是否加强 cross-domain/variable-choice breadth？** 是，真实执行证据来自原结果前冻结、覆盖 14 类且具有不同选项数的 MMLU-Pro panel；经济结论按各 reference 的实际 gate 报告，仍是 post-hoc development evidence。\n4. **为什么不是 open-ended generality？** 所有任务仍在有限合法 answer labels 上作离散选择；FP32 ProbeMax 和 parser 也围绕这些 labels 定义，没有验证开放式生成。\n5. **下一任务？** 不自动启动。Stage2 完成后停止并交回 Work；V4、supplement 均不修改。\n'
else:
    compact='未达到 512 requests / 256 probes 完整性门槛；Text/C2C 均 NOT_EVALUATED，缺失不能分类为负收益。'
    body='\n## 4. 未完成及保留证据\n\n'+compact+'\n\n'
    failure=resource.get('failure') or (read(P/'REQUEST_FAILURE.json') if (P/'REQUEST_FAILURE.json').exists() else {})
    body+='失败信息：`'+json.dumps(failure,ensure_ascii=False)+'`。成功 keys、缺失 keys 和原始输出全部保存。没有第二次提交，没有补跑至一致。\n'
    answers='\n## 7. 返回 Work 的五个回答\n\n1. Stage1 风险资格不变，但本轮缺少完整 E2E 证据，不能判断 worth omitting。\n2. Text/C2C 经济结果尚不能比较，未完成不等于负收益。\n3. 保留原 panel 的跨领域/variable-choice 身份，但不能把部分执行当完整 E2E breadth 结果。\n4. 仍是有限合法 labels 的 discrete-choice，没有验证 open-ended generality。\n5. 停止并返回 Work；不重提第二个作业，不启动下一任务，不修改 V4 或 supplement。\n'
distribution='\n## 6. 原 panel 的 category/K 分布\n\n| category | N |\n|---|---:|\n'+''.join(f'| {k} | {v} |\n' for k,v in panel['category_counts'].items())
distribution+='\n| K | N |\n|---|---:|\n'+''.join(f'| {k} | {v} |\n' for k,v in panel['K_distribution'].items())
distribution+='\n原 panel 没有 K=3/5/6/7 行；没有为覆盖这些 K 重新抽题。runtime 的动态 label 协议仍支持 K=3…10。这里只报告人口分布，不做 category-specific routing calibration、K-specific threshold 或新 subgroup guarantee；Stage1 总体风险校准仍只按整体 population 解释。\n'
tail='''
## 8. 交付索引

- `MMLU_PRO_E2E_STAGE2_FREEZE.json`：parent freeze/deployment/panel/model/runtime/rotation/timing/bootstrap/PBS/budget 的完整固定身份。
- `RESOURCE_LEDGER.json`：唯一作业提交、开始、结束、exit、实际 GPUh 和完整计数。
- `NUMERICAL_VALIDATION.json` 与 `evidence/FINAL_NUMERICAL_AUDIT.json`：完整性、数值与来源复核（完整执行时）。
- `records/four_arm_requests.jsonl`：512 条实际原始/parsed outputs、routes、outer/component latencies、input identity。
- `records/two_policy_probes.jsonl`：256 条独立在线 ProbeMax。
- `records/four_arm_requests_with_correctness.jsonl`：执行完成后关联 gold 与 correctness。
- `summary/mmlu_pro_e2e_summary.csv`、`paired_latency_bootstrap.csv`、`runtime_diagnostics.csv`、`output_identity_checks.csv`：要求的汇总。
- `protocol/bootstrap_indices.npz` 与 `summary/bootstrap_resample_means.csv`：冻结的 2,000 次 paired draws 及每次 mean saving。
- `protocol/PANEL_MANIFEST.json`：全部 128 个代表 ID/group/category/K/query hash；候选原文件完整复制，未重新选人口。

无新 router、benchmark、small/medium MMLU-Pro、threshold、calibration、ARC test、oracle/headroom 分析或稿件修改。无论 E2E 正负均完整交付。**任务停止，交回 Work，不自动启动下一任务。**
'''
(P/'REPORT_ZH.md').write_text(header+body+distribution+answers+tail)
(P/'HANDOFF_ZH.md').write_text(f'''# MMLU-Pro E2E Stage2 → Work

**{status}**

MMLU_TEXT_E2E = **{gates['Text']}**

MMLU_C2C_E2E = **{gates['C2C']}**

{compact}

唯一 PBS `{resource['job_id']}`：F / exit={resource['exit_status']}；实际 {n(resource['actual_GPUh'])}/2 GPUh。完整 requests={N}/512；online ProbeMax={NP}/256。没有第二次提交。

原结果前冻结 128 题 panel 原顺序、原 group representatives；q=.40、threshold=3.838539123535156e-05 原样继承。四臂同 allocation/residency，ordinal 轮换，每条 arm 每个位置各32次；两个 policy 各自计费独立完整 probe。第一正式请求保留，startup 单列，未用 Stage1 latency 拼接。

这是 exposed development-panel E2E evidence，非 sealed/independent/test confirmation 或新 policy selection。safe 仅沿用 Stage1 整体 conditional R/reference disagreement 校准；经济分类只是本 panel paired mean saving 与描述 bootstrap95 lower 的 gate。仍是 discrete-choice，不能称 open-ended generality。

完整五个回答、分布、identity 与 invalid 诊断见 REPORT_ZH.md。冻结身份、全逐题输出和四个 summary CSV 均已保存。

**停止并交回 Work。不启动下一任务，不修改 V4 或 supplement。**
''')
save(P/'FINAL_STATE.json',dict(utc=utc(),status=status,MMLU_TEXT_E2E=gates['Text'],MMLU_C2C_E2E=gates['C2C'],
    complete_requests=N,online_probes=NP,formal_PBS_submissions=1,actual_GPUh=resource['actual_GPUh'],policy_selection=False,
    calibration=False,manuscript_modified=False,supplement_modified=False,next_task_started=False))
print(status,json.dumps(gates,ensure_ascii=False),flush=True)
