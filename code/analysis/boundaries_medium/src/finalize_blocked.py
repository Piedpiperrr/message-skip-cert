"""独立复核预算/来源/人口，并生成中文阻塞交付。无科学 outcome 计算。"""
import csv
import hashlib
import json
from decimal import Decimal
from datetime import datetime, timezone
from pathlib import Path

P = Path(__file__).resolve().parents[1]
def read(p): return json.loads(p.read_text())
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p, data): p.write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + '\n')
def utc(): return datetime.now(timezone.utc).isoformat()
freeze = read(P / 'MEDIUM_PAIR_PROTOCOL_FREEZE.json')
sources = read(P / 'SOURCE_INDEX.json')
ledger = read(P / 'RESOURCE_LEDGER.json')
models = read(P / 'MODEL_SOURCE_INDEX.json')
checks = {}
checks['frozen_file_hashes_match'] = all(sha(P / f) == h for f, h in freeze['frozen_files'].items())
checks['source_copies_and_originals_match'] = all(sha(P / r['local_path']) == r['sha256'] == sha(Path(r['source_path'])) for r in sources['sources'])
checks['state_unchanged'] = sha(Path(sources['state_read_only']['path'])) == sources['state_read_only']['sha256']
checks['model_index_frozen'] = sha(P / 'MODEL_SOURCE_INDEX.json') == freeze['model_source_index_sha256']
checks['80_test_family'] = len(freeze['q_grid']) == 20 and 4 * len(freeze['q_grid']) == 80
checks['multiple_testing_arithmetic'] = Decimal('0.001') * 20 == Decimal('0.02') and Decimal('0.001') * 80 == Decimal('0.08')
checks['population_request_counts'] = sum(p['rows'] for p in freeze['populations']) == 5626 and 5626 * 3 == 16878
checks['no_outcomes_no_PBS'] = freeze['MEDIUM_PAIR_OUTCOMES_OBSERVED'] is False and ledger['formal_jobs_submitted'] == ledger['formal_action_attempts'] == ledger['formal_probe_attempts'] == 0
checks['official_config_tokenizer_hashes'] = all(sha(P / f['path']) == f['sha256'] for m in models['models'].values() for f in m['verified_local_config_tokenizer_files'])
checks['no_weight_files_downloaded'] = not list(P.rglob('*.safetensors')) and not list(P.rglob('*.pt'))
checks['no_runnable_PBS_submission_artifact'] = not list(P.rglob('*.pbs'))
panel = list(csv.DictReader((P / 'evidence/historical_throughput/panel_cost.csv').open()))
probe = list(csv.DictReader((P / 'evidence/historical_throughput/probe_timing.csv').open()))
independent = []
for pair in ['small', 'large']:
    total = Decimal(0)
    for ds, count in [('obqa', 4208), ('arc', 1418)]:
        vals = {}
        for row in panel:
            if row['pair'] != pair or row['dataset'] != ds: continue
            if row['policy'] == 'Fixed_R' and row['reference'] == 'T': vals['R'] = Decimal(row['action_ms'])
            if row['policy'] == 'Fixed_reference': vals[row['reference']] = Decimal(row['reference_ms'])
        assert set(vals) == {'R', 'T', 'C'}
        probe_total = sum(Decimal(row['sum']) for row in probe if row['pair'] == pair and row['dataset'] == ds and row['component'] in ['probe_core_ms', 'ProbeMax_score_ms'])
        total += (count * sum(vals.values()) + probe_total) / 1000
    est = next(x for x in ledger['projection_scenarios'] if x['historical_pair'] == pair)
    error = abs(float(total) - est['projected_inference_wall_seconds'])
    assert error < 1e-8
    independent.append({'pair': pair, 'independent_decimal_wall_seconds': str(total), 'float_error_seconds': error,
        'inference_GPU_hours': str(total * 2 / 3600), 'conservative_GPU_hours': str((total * Decimal('1.15') + 300) * 2 / 3600)})
checks['independent_budget_recalculation'] = True
checks['two_GPU_budget_exceeded_without_margin'] = all(float(r['inference_GPU_hours']) > 4 for r in independent)
assert all(checks.values()), checks

ledger['downloaded_config_tokenizer_bytes'] = sum(f['size'] for m in models['models'].values() for f in m['verified_local_config_tokenizer_files'])
ledger['metadata_fetch_attempts'] = 2
ledger['metadata_fetch_note'] = '第一次校验把 receiver tokenizer.json 的 LFS pointer blob ID 当成内容 Git hash，立即停止；第二次按 API 明示的 LFS SHA256 校验，保留第一份日志，未重下载既有内容；不涉及任何模型/题目重试。'
save(P / 'RESOURCE_LEDGER.json', ledger)
save(P / 'NUMERICAL_VALIDATION.json', {'status': 'PASS_PREFLIGHT_VALIDATION_ONLY', 'utc': utc(),
    'checks': checks, 'independent_budget_calculation': independent,
    'scientific_outcome_validation': 'NOT_APPLICABLE_NOT_EXECUTED',
    'local_checkpoint_weight_validation': 'NOT_EXECUTED', 'strict_C2C_GPU_runtime_validation': 'NOT_EXECUTED',
    'accuracy_disagreement_AUROC_routing_calculated': False,
    'scope': '只核验准备阶段的文件/人口/计数/预算算术，不表示 Stage 1 数值完成。'})
rows = []
for task in ['OBQA', 'ARC']:
    for ref in ['Text', 'C2C']:
        rows.append({'reference': ref, 'task': task, 'q': None, 'coverage': None, 'changed/routed': None,
            'conditional_disagreement': None, 'reference_accuracy': None, 'policy_accuracy': None,
            'AUROC': None, 'fallback/deploy': 'NOT_EXECUTED', 'AP': None,
            'actual_threshold': None, 'invalid_counts': None, 'reason': '提交前预算门槛未通过'})
with (P / 'summary/compact_summary.csv').open('w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
save(P / 'summary/four_strata_status.json', {'MEDIUM_DEPLOY_COUNT': None, 'denominator': 4, 'strata': rows})

budget_lines = '\n'.join(f"| {x['historical_pair']} | {x['projected_inference_wall_seconds']/3600:.3f} | {x['two_GPU_allocation_hours_without_margin']:.3f} | {x['conservative_two_GPU_allocation_hours']:.3f} |" for x in ledger['projection_scenarios'])
pattern = '\n'.join(f'- {r["task"]}/{r["reference"]} = 未执行（不能判定 fallback/deploy）' for r in rows)
summary_table = '\n'.join(f'| {r["reference"]} | {r["task"]} | — | — | — | — | — | — | — | 未执行 |' for r in rows)
report = f'''# P2 medium pair Stage 1：提交前预算阻塞报告

**最终状态：BLOCKED_MEDIUM_STAGE1。正式作业未提交；medium outcome 为零。停止并交回 Work。**

## 1. 阻塞原因与预算证据

用户第15节要求：“如预测会超过，提交前先返回 Work，不得自行扩大。”本轮沿用已验证的双 GPU 驻留：helper cuda:0，receiver/fuser cuda:1，逐题 batch1。完整 population 共5626行，需要16878次完整R/Text/C2C动作及5626次独立ProbeMax。

既有 confidence-boundary 的 dev128 panel 保存了同驻留完整原生请求计时。这里只读取这些历史数值进行提交前预算估计，没有新 E2E、component cost measurement 或 medium 试跑。动作采用对应 task 的历史R/Text/C2C均值，probe采用各fit/cal/dev历史计时总和。两个独立参照情景如下：

| 历史吞吐参照 | 预计纯推理墙钟小时 | 双GPU allocation hours（无余量） | 加15%余量与300秒启动/I/O预留 |
|---|---:|---:|---:|
{budget_lines}

公式：每个task的N × (R均时 + Text均时 + C2C均时) + 该task历史全量ProbeMax时间；最后乘2 GPU。4 GPU小时在双GPU下只允许7200秒墙钟。两个历史外推即使不计任何余量均超预算。详见 `summary/budget_projection.csv` 和 `RESOURCE_LEDGER.json`，Decimal独立复算见 `NUMERICAL_VALIDATION.json`。

**局限：这是历史吞吐外推，不是medium实测、下界或对所有实现不可行的证明。** medium更小并不提供本环境已测的加速系数；本轮没有以未经测量的速度折扣申报一个预估不足的作业。未验证单GPU实现；本次保留现有runtime的双设备映射与传输路径。单GPU同驻留或执行调度调整可能改变资源估计，应由Work审议；本轮不据此自行启动新执行路线。

PBS只读查询已成功且无当前用户在途作业；初次沙箱DNS失败在正常网络权限下已解决，不是本轮最终阻塞原因。正式作业提交数0，申请GPU小时0，实际分配GPU小时0，smoke0、推理0、训练0、题目重试0。

## 2. 官方来源与验证边界

官方仓库明确列出指定pair：[thu-nics/C2C](https://github.com/thu-nics/C2C)。本地既有官方源码revision为 `113c3a9b2538cbf096a0477e1ec99ae2a2e0d12a`；原native runtime相关源文件已只读复制并记录hash。

- helper：[Qwen/Qwen2.5-1.5B-Instruct](https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct/tree/989aa7980e4cf806f80c7fef2b1adb7bc71aa306)，revision `989aa7980e4cf806f80c7fef2b1adb7bc71aa306`。
- receiver：[Qwen/Qwen3-1.7B](https://huggingface.co/Qwen/Qwen3-1.7B/tree/70d244cc86ccca08cf5af4e1e306ecf908b1ad5e)，revision `70d244cc86ccca08cf5af4e1e306ecf908b1ad5e`。
- fuser：[nics-efc/C2C_Fuser](https://huggingface.co/nics-efc/C2C_Fuser/tree/f01fc3258b305e280e04c7238f4f2cf31b7dc70d/qwen3_1.7b%2Bqwen2.5_1.5b_Fuser/final)，revision `f01fc3258b305e280e04c7238f4f2cf31b7dc70d`，subfolder `qwen3_1.7b+qwen2.5_1.5b_Fuser/final`。

`MODEL_SOURCE_INDEX.json` 保存每个权重文件的官方LFS SHA256、大小和仓库revision，以及已下载tokenizer/config的本地SHA256及官方Git/LFS校验。预算门槛未通过后未下载任何权重；28个fuser checkpoint仅核验了官方清单，**没有本地权重哈希复算、strict state_dict加载或GPU运行成功证据**。不得把“官方已提供”写成“本环境已严格运行”。

元数据获取第一次因将LFS tokenizer的pointer blob ID作为内容Git hash而停止，随后按官方LFS SHA256完成正确校验；两份日志均保留。未修改官方文件，不涉及medium outcome或模型重跑。

## 3. Population及协议冻结

所有query-only输入与精确ID/顺序/group文件直接复制父boundary产物，hash一致；没有抽样或重建split，没有读gold。

| task | fit 行/独立组 | calibration 行/独立组 | development 行/独立组 |
|---|---:|---:|---:|
| OBQA | 2100/2100 | 1366/1366 | 742/742 |
| ARC | 671/670 | 448/448 | 299/299 |

ARC重复对保留在fit；正式动作与probe本应覆盖两行，但阈值/风险统计只用最小ID组代表。OBQA来自论文已披露的pre-existing exposed project partition。ARC test内容未读取；它已用于此前large pair project-sealed confirmation，medium永远不能产生新的sealed claim。

`MEDIUM_PAIR_PROTOCOL_FREEZE.json` 冻结模型官方来源、tokenizer/config hashes、population hashes、native Text/C2C协议、原parser/generation config、ProbeMax、q grid、风险检验、分析指标及报告规则。冻结时 `MEDIUM_PAIR_OUTCOMES_OBSERVED = false`。

该文件的性质是**科学协议与官方来源冻结**，`execution_ready=false`；它不是已完成本地权重/runtime验证的执行许可。解除预算阻塞前不得提交，且本地权重实测校验、strict mechanical loading和完整执行driver仍未完成。后续若Work授权继续，必须保留本文件及时间戳，在任何medium outcome前补齐独立执行冻结，不覆盖原件。

ProbeMax保持原生thinking-off固定格式prompt；追加无尾空格的`The correct answer is`；按receiver自身tokenizer独立构造single-token合法label集合，FP32 logsumexp/log_softmax.exp归一化，u=1-max p；完整prefill只投影最后位置，无KV复用。argmax只是诊断，不替代R。invalid处理沿用原断言和parser，不过滤分母。

q固定为.05,.10,…,1.00；j<20时用ceil(j*Nfit/20)整数次序统计，并列整体保留，q=1为fixed R。每个reference独立使用BinomialCDF(k;n,.05)，p≤.001接受，报告CP .999上界，选择最大接受q；无接受则q=0 fixed-reference fallback。accuracy不参与选择。

多重检验族为本轮同时规划的4×20=80项：每层20项理想Bonferroni bound≤.02，整个extension理想bound≤.08；这只是透明解释，不改变选择，也不混入历史large/OBQA/Text的100-test family。

## 4. 四层完整状态表

| reference | task | q | coverage | changed/routed | conditional disagreement | reference accuracy | policy accuracy | AUROC | fallback/deploy |
|---|---|---|---|---|---|---|---|---|---|
{summary_table}

**MEDIUM_DEPLOY_COUNT = N/A / 4（未执行，不是0/4）**

{pattern}

action outputs、ProbeMax scores、fit thresholds、80项calibration ledgers、deployment configs、development summaries、prevalence、AUROC/AP和accuracy decomposition均尚未产生。对应目录的STATUS文件及成功ID空清单明确标注原因；未伪造空结果为fallback。`NUMERICAL_VALIDATION.json` 的PASS仅表示准备/来源/预算算术检查通过，绝不表示科学结果完成。

## 5. 定位、强制报告规则与Work问题

定位原文：**“post-hoc motivated, but protocol-frozen before observing medium-pair outcomes”**。本轮动机来自已见small/large结果；不是preregistered scaling study、independent validation或sealed confirmation。

协议已固定：一旦完整执行，0/4、1/4、2/4、3/4、4/4或杂乱模式全部必须进入最终交付；Work只决定main paper或appendix展示位置，不能决定是否报告。此时无medium结果可用于论证单调性或任何因果scale law。

1. **是否提供比原two-pair design更有信息量的boundary evidence？** 尚未产生新的经验点，当前不能作肯定判断；设计上增加一个intermediate receiver/reference regime，实际信息量需完整执行后评估。
2. **是否存在至少一个nontrivial deployment？** 未知，四层都没有校准结果。
3. **是否值得进入Stage 2 E2E？** 当前不能据此建议进入；应先由Work解决Stage 1预算/runtime执行方案并获得完整四层结果。
4. **是否自行启动Stage 2？** 没有，也不会自动启动。

## 6. 交付和停止边界

独立目录：`{P}`。主要入口：本报告、`HANDOFF_ZH.md`、`MEDIUM_PAIR_PROTOCOL_FREEZE.json`、`MODEL_SOURCE_INDEX.json`、`RESOURCE_LEDGER.json`、`NUMERICAL_VALIDATION.json`、`summary/compact_summary.csv`、`SOURCE_INDEX.json`、`SHA256SUMS`。

V3 manuscript、当前supplement及已有artifact均未修改；没有small/large重跑，没有ARC test读取、新E2E、component测量、utility、AC或其他feature/模型训练。准备文件全部位于sharedfs独立目录；未安装环境。已停止并交回Work，不自动提交或启动Stage 2。

最终状态：**BLOCKED_MEDIUM_STAGE1**。
'''
(P / 'REPORT_ZH.md').write_text(report)
handoff = f'''# P2_MEDIUM_PAIR_BOUNDARY_EXTENSION_STAGE1 → Work

**最终状态：BLOCKED_MEDIUM_STAGE1。提交前预算门槛不通过，已停止。**

- 既有双GPU runtime的历史吞吐外推：纯推理约5.25–5.31 GPU allocation hours；加15%余量与300秒预留约6.20–6.27，超过本轮4小时。详见REPORT_ZH.md及summary/budget_projection.csv。
- 正式PBS提交0、分配GPU小时0、smoke0、R/Text/C2C生成0、ProbeMax0；MEDIUM_PAIR_OUTCOMES_OBSERVED=false。未读取ARC test、未做E2E/utility/component测量，论文及旧artifact未修改。
- 官方helper/receiver/fuser固定revision与LFS checkpoint清单已记录，tokenizer/config已做本地哈希校验；**权重未下载，本地权重校验及严格GPU加载未完成**。不能声称medium fuser已经严格运行，也没有证据声称它无法运行。
- 精确population文件原样继承：OBQA2100/1366/742；ARCfit671行/670组、cal448、dev299。未重抽、未读gold。
- MEDIUM_PAIR_PROTOCOL_FREEZE.json为科学协议与来源冻结，execution_ready=false，不能作为提交许可。后续执行driver、本地权重/strict loading及执行冻结仍待Work决定后的独立续行；不得覆盖原冻结。
- MEDIUM_DEPLOY_COUNT=N/A/4；OBQA/Text、OBQA/C2C、ARC/Text、ARC/C2C全部未执行，不能记0/4或fallback。结果目录只有状态与成功ID空清单，没有科学结果。
- 定位：post-hoc motivated, but protocol-frozen before observing medium-pair outcomes。一旦完整执行，四层全部必须报告；Work只能决定main/appendix位置。
- 目前无新empirical boundary evidence，nontrivial deployment未知，尚不能建议Stage 2。**不自动启动Stage 2，也不自动提交Stage 1。**

需要Work审议：在4 GPU小时硬上限下是否另行规定并验证单GPU或其他执行驻留；本次双GPU外推不证明单GPU必然超预算。任何资源/执行变更均不得依据medium结果调整科学协议。

交付目录：{P}
入口：REPORT_ZH.md、MEDIUM_PAIR_PROTOCOL_FREEZE.json、MODEL_SOURCE_INDEX.json、RESOURCE_LEDGER.json、NUMERICAL_VALIDATION.json、summary/compact_summary.csv、SHA256SUMS。
'''
(P / 'HANDOFF_ZH.md').write_text(handoff)
save(P / 'FINAL_RECEIPT.json', {'status': 'BLOCKED_MEDIUM_STAGE1', 'utc': utc(),
    'protocol_sha256': sha(P / 'MEDIUM_PAIR_PROTOCOL_FREEZE.json'), 'REPORT_sha256': sha(P / 'REPORT_ZH.md'),
    'HANDOFF_sha256': sha(P / 'HANDOFF_ZH.md'), 'GPU_allocation_hours': 0,
    'outcomes_observed': False, 'MEDIUM_DEPLOY_COUNT': None, 'stopped_and_returned_to': 'Work'})
files = [p for p in sorted(P.rglob('*')) if p.is_file() and p.name != 'SHA256SUMS']
(P / 'SHA256SUMS').write_text(''.join(f'{sha(p)}  {p.relative_to(P)}\n' for p in files))
print(json.dumps({'status': 'BLOCKED_MEDIUM_STAGE1', 'checks': checks, 'files_indexed': len(files), 'protocol_sha256': sha(P / 'MEDIUM_PAIR_PROTOCOL_FREEZE.json')}, ensure_ascii=False))
