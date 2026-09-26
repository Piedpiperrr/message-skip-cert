"""Paper/report tables from frozen V2 outputs; no further statistical selection."""
import csv,json,datetime,hashlib
from pathlib import Path
from rescore_answers import O,P,P10,ACTIONS,LETTERS,SCHEMES,sha,table,save
from rescore_routers import PRIMARY,ABL
def read(n):return list(csv.DictReader((O/n).open()))
def md(head,rows):return '| '+' | '.join(head)+' |\n| '+' | '.join(['---']*len(head))+' |\n'+''.join('| '+' | '.join(map(str,r))+' |\n' for r in rows)
def f(x,d=3):
    x=float(x)
    if abs(x)<1e-10:x=0
    return f'{x:.{d}f}'
def count(x):return str(int(float(x))) if float(x).is_integer() else f(x)
def trip(r,met):return ' / '.join(count(r[v+'_'+met]) for v in SCHEMES)
def cn(pair,ds):return ('大' if pair=='large' else '小')+' '+('OBQA' if ds=='obqa' else 'ARC')
COMBOS=[('large','obqa'),('large','arc'),('small','obqa'),('small','arc')]
def main():
    assert (O/'evidence/output_validation.json').exists()
    acc=read('action_summary.csv');comp=read('complementarity.csv');flips=read('flip_summary.csv');agree=read('pairwise_agreement.csv')
    pol=read('frozen_policy_rescoring.csv');paired=read('primary_paired_comparisons.csv');changes=read('population_changes.csv')
    freeze=json.loads((O/'RULE_FREEZE_V2.json').read_text());lm=json.loads((O/'labels/LABEL_MANIFEST.json').read_text())
    total=lambda population,comparison,met:sum(int(r[met]) for r in changes if r['population']==population and r['comparison']==comparison)
    getcomp=lambda population,pair,ds,train=False:next(r for r in comp if r['population']==population and r['pair']==pair and r['dataset']==ds and (r['split']=='train')==train)
    getpol=lambda population,pair,ds,policy:next(r for r in pol if r['population']==population and r['pair']==pair and r['dataset']==ds and r['split']!='train' and r['policy']==policy)
    getpair=lambda population,pair,ds,ref:next(r for r in paired if r['population']==population and r['pair']==pair and r['dataset']==ds and r['reference']==ref)
    inv=[]
    for pair,ds in COMBOS:
        for a,letter in zip(ACTIONS,LETTERS):
            r=next(x for x in acc if x['population']=='full' and x['split']=='train' and x['pair']==pair and x['dataset']==ds and x['action']==a)
            changed=int(r['old_to_V2_correct_improved'])+int(r['old_to_V2_correct_harmed'])
            for family in ['word','semantic']:
                inv.append(dict(asset=str(P10/'results'/pair/ds/'models'/(family+'.joblib')),component=letter+'_correctness_head',pair=pair,dataset=ds,family=family,
                    old_correct=r['old_correct'],D1_correct=r['D1_correct'],V2_correct=r['V2_correct'],changed_train_y=changed,
                    decision='needs_refit_before_claiming_V2_trained' if changed else 'training_target_unchanged_reusable',refit_this_stage=False))
    table('refit_inventory.csv',inv)
    poptable=[]
    for population in ['full','panel']:
        for before in ['old','D1']:
            poptable.append([population,before+'→V2',total(population,before+'_to_V2','action_records'),total(population,before+'_to_V2','answer_changed'),
                total(population,before+'_to_V2','correctness_improved'),total(population,before+'_to_V2','correctness_harmed')])
    comptable=[]
    for pair,ds in COMBOS:
        r=getcomp('full',pair,ds);a=next(x for x in agree if x['population']=='full' and x['pair']==pair and x['dataset']==ds and x['split']!='train' and x['a']=='receiver_only' and x['b']=='acw')
        comptable.append([cn(pair,ds),r['n'],*[r['V2_'+x+'_correct'] for x in ACTIONS],r['V2_union4'],r['V2_gap'],f(r['V2_gap_pp']),r['V2_AC_exclusive'],a['V2_equal_including_INVALID']+'/'+r['n'],a['V2_equal_both_valid']+'/'+a['V2_both_valid']])
    fulltable=[];paneltable=[]
    for pair,ds in COMBOS:
        for policy,lab in [(ABL,'word λ=.01 三动作'),(PRIMARY,'word λ=.01 四动作'),('train_frozen_mixture','旧 train 冻结混合')]:
            r=getpol('full',pair,ds,policy);fulltable.append([cn(pair,ds),lab,r['n'],trip(r,'correct'),f(100*float(r['V2_accuracy'])),f(r['V2_gain_over_R']),f(r['V2_harm_vs_R'])])
            r=getpol('panel',pair,ds,policy);paneltable.append([cn(pair,ds),lab,trip(r,'correct'),f(100*float(r['V2_accuracy'])),f(r['mean_ms']),f(r['mean_original_router_overhead_ms'])])
    cit=[]
    for pair,ds in COMBOS:
        r=getpair('panel',pair,ds,'train_frozen_mixture')
        cit.append([cn(pair,ds),f(r['V2_accuracy_delta_pp']),f"[{f(r['V2_ci_low_pp'])}, {f(r['V2_ci_high_pp'])}]",f(r['original_latency_delta_ms']),f"[{f(r['latency_ci_low_ms'])}, {f(r['latency_ci_high_ms'])}]"])
    fliptable=[]
    for pair,ds in COMBOS:
        r=next(x for x in flips if x['population']=='full' and x['pair']==pair and x['dataset']==ds and x['split']=='train' and x['action']=='c2c')
        fliptable.append([cn(pair,ds),r['n'],trip(r,'f'),r['old_to_V2_f_changed'],trip(r,'invalid_flip'),trip(r,'gain'),trip(r,'harm'),trip(r,'zero_gain'), ' / '.join(f(r[v+'_historical_direction_diagnostic'],4) for v in SCHEMES)])
    ctable=[]
    for r in acc:
        if r['population']=='full' and r['action']=='c2c':ctable.append([cn(r['pair'],r['dataset']),r['split'],r['n'],trip(r,'valid'),trip(r,'correct'),
            ' / '.join(f(100*float(r[v+'_accuracy'])) for v in SCHEMES)])
    labeltable=[[x['relative_path'],x['question_rows'],x['size_bytes'],x['sha256']] for x in lm]
    text=f'''# P2_SCORING_V2 正式评分与冻结路由重评

**科学结论：评分修正没有改变 P2-10 原重点尚未确认实际 accuracy–cost 优势的判断；但旧 C2C 正确率头和翻转目标不能视为 V2 训练产物。** 四个 full 开发人口中，四动作相对三动作仍是 −2、0、+1、0 题；四个同作业 panel 仍逐题同分，原重点仍未捕获 6 道 AC 独占正确题。大模型 OBQA 的 full 相对旧混合有正的准确率差条件区间，然而对应 panel 延迟更高；两个不同人口不能拼接为优势点。

**V2 相对 D1 的新增影响有限且位于训练数据。** full 新增 4 条解析变化，其中正确性改善 3、下降 0；panel 另有不同来源的同题 1 条改善。两种人口所有开发评分都与 D1 相同。相对旧评分，full 共改变 158 条输出、正确性改善 129、下降 0；panel 改变 29 条、改善 25、下降 0。两人口不能相加。V2 是审阅已曝光案例后的正式协议修订，不是将 D1 改名。

**下一步交回 Work 主线作有限方法验证审议。** 已交付正式冻结规则、版本化 train/开发标签、旧策略重评分与论文片段；本轮没有拟合新头、重选混合、FFR/E0/E1、模型推理、GPU、PBS 或 ARC test 读取。若批准下一轮，最小直接更新对象是 P2-10 四组合 × word/semantic 的 **8 个 C 正确率头**；其余 24 个 R/T/A 正确率头训练目标未变，可保留。是否验证方法由主线决定，此会话到交付停止。

## 1. 正式版本、曝光事实和验证

目录：`{P/O.name}`。规则 [P2_SCORING_V2_RULES_ZH.md](P2_SCORING_V2_RULES_ZH.md)，代码 [scoring_v2.py](scoring_v2.py)，冻结回执 [RULE_FREEZE_V2.json](RULE_FREEZE_V2.json)。版本 `P2_SCORING_V2` / 实现 `2.0.0`，UTC 冻结时间 `{freeze['frozen_utc']}`，早于本阶段 V2 总体统计。规则 SHA256 `{freeze['rules_sha256']}`；解析源码 SHA256 `{freeze['code_sha256']}`。

规则采用“明确的单一合法选项”：接受可靠首部、正向答案声明、通用嵌入选择句法；保留引用/假设/否定、单位/变量的区分。完整合法标签集合之后唯一无条件单选可消解集合复述；普通冲突仍需明确修订关系。解释续句不作新选择。无字母语义、数字序号均不映射选项。所有来源/动作/组合/split 调用同一函数，入口只有 raw_answer、legal_labels，gold 比较在外部进行。

本协议修订之前已经阅读了旧评分、D1、已曝光边界和相关正确性结果，**不能声称全程未见 gold 或结果**。规则不以某方法获益为条件。297 项定向检查通过，详见 [targeted_validation.json](evidence/targeted_validation.json)：包含 24 种字母排列、单位/公式替换、正确/错误选择对称、真实多选/非法标签/矛盾/引用/否定保护及主线指定原文。冻结后 parser **0 次修订**，没有按准确率选版本。

冻结前的置换测试脚本曾错误替换单词 Answer 的 A，已修正为仅置换独立标签，保留 `evidence/pre_freeze_harness_failure.json`。统计输出过程另修正了旧 reason=null 的排序问题；默认系统 Python 没有 NumPy，随后使用 P2-10 已登记的现有 sharedfs 环境完成路由数组读取。两项都不是 parser 规则修订，未安装包，未加载模型。

## 2. 来源、人口和增量

复用敏感性阶段登记的 49,616 条来源记录。旧 parser 回放不一致 0 和版本验证沿用既有证据，不重新执行旧 parser。D1 从已保存逐题变更重建，并与其全套动作正确/有效/无效汇总精确匹配。原输入哈希与登记值一致。full 为历史 R/T/C 加 P2-10 AC；panel 使用 P2-10 同作业四动作，各 train256、开发128。共享的 1,536 条 AC 保留两个人口身份而非重复增加独立证据。

{md(['人口','比较','动作记录数','输出改变','正确性改善','正确性下降'],poptable)}
full 为 9,170 train 和 2,082 已曝光开发题—模型对；panel 为 1,024 train 和 512 开发题—模型对。模型对分别为 Qwen2.5-7B-Instruct → Qwen3-8B、Qwen2.5-0.5B-Instruct → Qwen3-0.6B；任务为 OBQA 和 ARC-Challenge（validation）。每个模型对共享任务题目，不将其当作跨组合独立题目总体。

V2 新增的 full 变化为 small/OBQA/c2c 的 14-324、1952，以及 small/ARC/c2c 的 MCAS_1998_4_17、Mercury_LBS10444；其中 14-324 提取 A 仍错，后三者正确。panel 的 MCAS_1998_4_17/c2c 单独恢复正确。同题 receiver_only/acw 的原样多选仍无效。这些是通用规则产生的结果，不是按题号改分。

V2 full 有效 43,572、无效 1,436：多选 1,365、无明确选项 4、拒答 2、空输出 65。panel 有效 5,940、无效 204：多选 187、无明确选项 2、空输出 15。未出现的非法/冲突类别计数为零并不表示取消该守卫；定向检查覆盖它们。来源中的运行失败为 0，单列 `runtime_failures.csv`。无字母说明是格式不合规，不能把全部 INVALID 都解释为推理错误。

## 3. 两模型对 × 两任务互补性

以下仅为 full 已曝光开发人口的 V2 正确数。一致率以分子/分母展示，双方有效分母单独列出。

{md(['组合','N','R','T','C','A','四并集','gap题数','gap pp','AC独占','R/A一致含INVALID','双方有效一致'],comptable)}
四并集相对旧评分、D1 都不变：670/742、281/299、501/742、206/299。最佳固定动作仍是大模型 T、小模型 C；小 OBQA 固定 C 从旧 365 变成 366，使 gap 从 136/742 降至 135/742。小模型明显更大的可观察互补空间及 A≈R 描述保留。并集是观察全部动作后的上界，不能当作可部署路由收益。全量 train 仅大 ARC 的并集比旧增加 1；V2 相对 D1 的并集均不变。

R/A 的含 INVALID 一致数在三个版本之间均不变，开发双方有效条件数也不变。训练有一个明确例外：大 ARC 的 A 从错误字母变为 INVALID，使 full 双方有效分母旧1117→D1/V2 1116，一致分子仍1111（99.463%→99.552%）；同题 panel 为分母256→255、分子仍254（99.219%→99.608%）。V2 相对 D1 无新增 R/A 变化。小模型双无效不能解释为相同的正确选项。完整 train/panel、六组配对和独占正确见 `complementarity.csv`、`pairwise_agreement.csv`、`action_summary.csv`。

C2C 的正式分数如下，三列顺序固定为 **旧 / D1 / V2**；其他动作正确数全部不变，仅大 ARC train A 有 1 条旧错误字母转 INVALID，正确性不变。

{md(['组合','split','N','有效数 旧/D1/V2','正确数 旧/D1/V2','accuracy % 旧/D1/V2'],ctable)}

## 4. 稀有翻转标签与方法含义

以合法字母或 INVALID 定义 o，`f_a=1[o_a≠o_R]`。改善为 a 对 R 错，伤害为 R 对 a 错，零收益为输出不同但正确性相同；INVALID 翻转另列。以下是 full train 的 C|R，仍按旧 / D1 / V2 排列。

{md(['组合','N','翻转','旧→V2 f改变','INVALID翻转','改善','伤害','零收益','历史方向常数'],fliptable)}
旧→V2 的 C|R 二元标签共改变 **116** 个（51、60、2、3）。大 ARC 的 60 个变化占旧 112 次翻转的 **53.57%**；大 OBQA 为 51/338=15.09%。以全动作平均改分比例概括影响会掩盖稀有目标的变化。大模型 C 的不少旧“通信翻转”和伤害来自格式评分失败；这是确定计数及其解释，不是本轮显著性检验或 FFR 可学习性证明。

V2 相对 D1 新改变 full 的 f 共 3 个（小 OBQA 1、小 ARC 2）；其余输出变化也可能改变 INVALID 标记而不改变 f。T|R 与 A|R 的二元 f、改善/伤害方向不变；大 ARC train A 涉及 INVALID 的翻转由旧 2 变为 V2 3，不能只看 f 是否改变。完整类别、来源键和三版本在 `flip_summary.csv`、`changed_flip_labels.csv`。

方向常数严格标为 **P2-11 历史公式诊断** `(改善−伤害)/(翻转+2)`。本轮未审定它是标准 Beta 二项后验；没有训练/验证 FFR。评分修正是评价协议维护，不是主方法贡献或 novelty 证据。

## 5. 已冻结路由：重评分，不是重拟合

恢复范围无缺项：每组合原 28 个 word/semantic 三/四动作网格、4 个固定动作、1 个 train 冻结混合；对 full/panel 和 train/开发共 **528 行**重评分。train 行仅为样本内诊断。另有原 286 混合/组合及旧开发描述性包络中可恢复的固定概率，共 **1,273 行**重评；未重选 V2 开发最佳点，也未把这些固定旧概率称为 V2 优化包络。

保存动作选择与 panel 原在线选择一致；旧开发正确数重建与 P2-10 原表完全一致，所有 panel 原动作时延、开销、总时延和汇总均精确匹配。未读取模型/特征文件、未预测或拟合。所有旧混合概率保持不变。full 表没有时延列：

{md(['组合','旧冻结策略','N','正确数 旧/D1/V2','V2 accuracy %','V2改善vsR','V2伤害vsR'],fulltable)}

panel 使用自身 128 道题的原答与原计时，正确数顺序仍为旧 / D1 / V2。混合正确数与成本均为概率加权期望，非随机部署的实测成功数。

{md(['组合','旧冻结策略','正确数/128 旧/D1/V2','V2 accuracy %','原均值ms','原路由开销ms'],paneltable)}

原重点四动作相对旧 train 冻结混合的 panel 条件配对区间：

{md(['组合','V2准确率差pp','95%区间pp','原延迟差ms','95%区间ms'],cit)}

采用原设计：seed0、20,000 次按题有放回配对 bootstrap、95% 百分位区间，共享人口内抽样；本阶段仅重算派生区间，不改原计时。区间以旧训练、一次部署和已曝光人口为条件，不涵盖训练随机性、多重比较或独立确认性测试。小 ARC 四/三动作平均差 −0.233ms 来自原开销差且选择完全相同，不能归因于 AC 通信收益。

大 OBQA full 四动作对混合的 V2 准确率差为 +1.148pp，95% 条件区间 [0.134,2.158]pp，旧评分下也如此；这只是相应人口准确率。对应 panel 为 +1.581pp、区间跨零，且平均慢 113.632ms。不能以 full 准确率和 panel 延迟构造一点。其余 panel 也未确认稳定优势，因此原主结论保持。

辅助网格中只有小 OBQA full 的 12 个 word 点各增加 1 题；112 个开发 panel 路由点的正确数全部不变。此结果不将某个辅助开发点提升为重点。`saved_head_pairwise_discrimination.csv` 重算旧保存概率差的配对正确性 AUC；它是旧头在 V2 标签上的诊断，不是已重拟合头的性能。P2-11 旧 C 翻转检测 AUC 的具体代理分数实验未在本轮扩展重做，不能将其旧标签结果当作 V2 已验证可学习性。

## 6. 哪些资产需要下一轮重拟合或更新

- **P2-10：8 个 C 正确率头需要重拟合才能称为 V2 训练。** 四组合 train y_C 变化分别为 44/3466、56/1119、2/3466、4/1119；word/semantic 各一头。三/四动作路由共用 R/T/C 头，两个动作集的策略都会受到新拟合的潜在影响。`refit_inventory.csv` 给出每个模型文件及组件。
- **R/T/A 的 24 个正确率头训练 y 不变；查询特征、TF-IDF、语义缓存、成本 Ridge、c_ref 和原计时无需因评分更版而重做。** 旧模型 bundle 中仍包含旧 C 头，所以整体不能标为 V2 已训练。AC 的输出有效性标记需采用新标签，但其正确性头不因此重拟合。
- **P2-5/6/9 的 C 头和涉及 C 的旧训练比较** 使用本轮同一登记训练原答；若继续作为正式 V2 方法证据，也需定向更新相应 C 头/结果。P2-7A/7B 中涉及 C 的不一致题集合、方向/成对目标以及基于旧正确性组合的 OOF 划分解释受到影响；若论文保留这些论据，下一轮需按既定方案有限重评/必要重拟合，不能直接沿用旧分数。无需重做全部历史阶段。
- **混合参照：先保留本轮重评分，再由主线决定是否更新训练冻结。** 旧 train panel 的 C 正确数在大 OBQA 206→209、大 ARC 224→236、小 ARC 155→157，小 OBQA 131不变；前三个训练混合优化输入已变。本轮四个概率向量均未重求。若路由 C 头重拟合使训练预算 B_train 改变，混合预算及冻结参照也须按原协议更新。开发包络的 C 坐标也可能改变，旧概率重评不等于 V2 最优包络。
- **FFR 当前只有设计与标签，无已训练 FFR 可重拟合。** 本轮给出新 f、改善/伤害/零收益、INVALID 和方向诊断，替代旧目标作为待审议输入；不能称已验证 FFR、E0、E1。W/C2C fuser、生成原答和缓存特征不因 parser 更版而重训练或重生成。

## 7. 文件、论文和状态交接

版本标签包含每题 `o_R/T/C/A`、`valid_*`、`y_*`、`f_*`、改善/伤害/零收益、INVALID/INVALID翻转、split、版本/哈希、各动作原来源路径/行号/ID/原答哈希。train 与已曝光开发文件分开，full 与 panel 分开；共享题目和 AC 不得相加。`scoring_records.csv` 保留 49,616 条来源的旧/D1/V2 三列及原计时；标签本身没有训练特征或完整原答。

标签绝对根路径：`{P/O.name}`；下表哈希为完整 SHA256。大标签不进入资料包。

{md(['相对路径','题—模型对行数','字节','SHA256'],labeltable)}

可直接插入论文的英文片段在 `paper/`：评价协议、两对×两任务互补表、稀有标签/方法意义、旧冻结路由的 full/panel 分离结果及未验证边界。中文放置说明为 `paper/README_ZH.md`。P2_STATE 没有明确登记现存论文工程，故不搜索或重建论文项目。P2_STATE 只追加本次版本、路径、重评状态与下一步，保留历史段落。

本任务在 ClusterB 登录节点单线程、nice=10，地址空间硬上限 768MiB；新增分析/验证 CPU、失败尝试和资源预留全部见 `evidence/resource_ledger.json`，最终汇总见 `FINAL_RECEIPT.json`。模型/tokenizer 加载、特征提取、训练、GPU、PBS 提交和节点作业均为 0；ARC test 未读。CPU 分析时间从不计入在线路由开销。

交付以 `HANDOFF_ZH.md`、`P2_SCORING_V2_BUNDLE.tar.gz`、`FILE_INDEX.tsv` 为轻量入口；包只含报告、规则、冻结/验证回执、代码、小表、论文片段及标签路径/哈希，不含完整原答、大标签或模型数组。完成后停止，交回 Work 审议方法验证，不自动启动下一阶段。
'''
    (O/'P2_SCORING_V2_REPORT_ZH.md').write_text(text)
    # LaTeX uses ordinary table/tabular and no project-specific macros.
    (O/'paper/01_evaluation_protocol.tex').write_text(r'''% Evidence: ../RULE_FREEZE_V2.json; ../evidence/targeted_validation.json
\paragraph{Evaluation protocol.}
We score generated responses using \texttt{P2\_SCORING\_V2}, an explicit-single-option protocol.
The parser receives only the raw response and the displayed legal labels; gold answers,
item identities, model pairs, action identities, and option semantics are excluded from its inputs.
An explicit leading option or an unconditional positive selection is accepted, including a
selection embedded in a sentence. Units and formulas do not invalidate an explicit option
(e.g., ``C. 70 km/h''), and a temperature-unit suffix does not create a new option.
Explanatory continuations do not introduce a conflicting choice. A restatement of the complete
legal label set may be resolved by a subsequent unique positive selection; conflicting single
choices require an explicit final-answer or correction relation. Unresolved multiple choices,
illegal labels, negations, and quoted or hypothetical selections are not converted into a choice.
We do not map option text or numeric indices to labels. Invalid responses count as incorrect,
with separate reasons for refusal, empty output, multiple options, illegal labels, unresolved
conflicts, and absence of an explicit option; runtime failures are recorded separately.
Thus, invalid formatting is not uniformly interpreted as a reasoning error.

\paragraph{Protocol revision and exposure.}
V2 was specified after review of exposed examples and previous scoring results, including
correctness information; the revision process was not globally blinded to gold or outcomes.
Its rules, implementation, and hashes were frozen before computing aggregate V2 scores,
and 297 targeted checks covered syntax boundaries, label permutations, unit/formula changes,
and symmetric treatment of correct and incorrect selections. The frozen parser was not
subsequently revised or selected by aggregate accuracy. D1 remains a separate historical
sensitivity analysis. This correction is evaluation maintenance, not a routing-method contribution.
''')
    latex=[r'% Evidence: ../complementarity.csv and ../pairwise_agreement.csv; full exposed development only.',r'\begin{table}[t]',r'\centering\small',r'\begin{tabular}{llrrrrrrrr}',r'\hline',r'Pair & Task & $N$ & R & T & C & A & Union & Gap & A-only \\',r'\hline']
    for pair,ds in COMBOS:
        r=getcomp('full',pair,ds)
        latex.append(' & '.join([pair.capitalize(),ds.upper(),r['n'],*[r['V2_'+a+'_correct'] for a in ACTIONS],r['V2_union4'],r['V2_gap'],r['V2_AC_exclusive']])+r' \\')
    latex += [r'\hline',r'\end{tabular}',r'\caption{V2 correct counts on exposed development data. Large: Qwen2.5-7B-Instruct $\rightarrow$ Qwen3-8B; small: Qwen2.5-0.5B-Instruct $\rightarrow$ Qwen3-0.6B. R/T/C/A denote receiver-only, text, C2C, and AC(W). OBQA uses dev and ARC-Challenge uses validation. Union is the hindsight four-action union; gap subtracts the best fixed action, and A-only counts AC-exclusive correctness. No latency is attached to this population.}',r'\label{tab:p2-v2-complementarity}',r'\end{table}',
        r'\paragraph{Observed complementarity.} The V2 union-minus-best-fixed gaps are 3.37 and 2.34 percentage points for the large pair, versus 18.19 and 17.06 points for the small pair. These observations preserve the larger complementarity of the small pair, but hindsight unions do not establish executable routing gains. Receiver/AC agreement including INVALID is 732/742, 298/299, 682/742, and 261/299; conditioned on both being valid it is 732/739, 298/299, 658/678, and 231/239. These agreements are unchanged across old scoring, D1, and V2.']
    (O/'paper/02_complementarity.tex').write_text('\n'.join(latex)+'\n')
    (O/'paper/03_flip_labels.tex').write_text(r'''% Evidence: ../flip_summary.csv (population=full, split=train, action=c2c).
\paragraph{Scoring affects rare routing targets.}
Let $o_a$ be the parsed legal option or $\mathrm{INVALID}$, $v_a$ its validity,
$y_a$ its correctness, and $f_a=\mathbf{1}[o_a\ne o_R]$.
We distinguish improvements $(y_a,y_R)=(1,0)$, harms $(0,1)$,
zero-gain flips with equal correctness, and flips involving INVALID.
Compared with old scoring, V2 changes 116 training C2C-versus-receiver flip labels:
51/3466 and 60/1119 for large-pair OBQA and ARC, and 2/3466 and 3/1119 for the small pair.
For large-pair ARC, flips decrease from 112 to 52, harms from 79 to 24,
and flips involving INVALID from 66 to 3. The 60 changed binary targets amount to
53.57\% of the original 112 flips, despite a small overall response-change rate.
Relative to D1, V2 changes four full-population training responses (three correctness
improvements), plus one separately sourced panel response; development scoring is identical.
These changes caution against interpreting every former format failure as a communication-induced
content change. They motivate regenerating supervised targets before evaluating a flip-based
router; they do not establish that such targets are predictable or that FFR is effective.
The earlier diagnostic $(G-H)/(F+2)$ is retained only as a historical direction formula,
not as an established Beta--binomial posterior or a validated estimator.
''')
    latex=[r'% Evidence: ../frozen_policy_rescoring.csv; ../primary_paired_comparisons.csv.',r'\paragraph{Rescoring frozen routers.}',
        r'We retain all previously saved action selections, parameters, and train-frozen mixture probabilities. The designated comparison remains the word router with $\lambda=0.01$ and three versus four actions. All these routers were trained with old labels; V2 rescoring is not V2 retraining.',
        r'\begin{table}[t]',r'\centering\small',r'\begin{tabular}{llrrrr}',r'\hline',r'Pair & Task & $N$ & Three-action & Four-action & Frozen mix \\',r'\hline']
    for pair,ds in COMBOS:
        rr=[getpol('full',pair,ds,x) for x in [ABL,PRIMARY,'train_frozen_mixture']]
        latex.append(' & '.join([pair.capitalize(),ds.upper(),rr[0]['n'],*[count(r['V2_correct']) for r in rr]])+r' \\')
    latex += [r'\hline',r'\end{tabular}',r'\caption{V2 correct counts for old-trained frozen policies on full exposed development populations; mixtures give expected counts. Accuracy only: no latency from the smaller panel is paired with these values.}',r'\label{tab:p2-v2-full-routing}',r'\end{table}',
        r'\begin{table}[t]',r'\centering\small',r'\begin{tabular}{llrrrrrr}',r'\hline',r'& & \multicolumn{2}{c}{Three-action} & \multicolumn{2}{c}{Four-action} & \multicolumn{2}{c}{Frozen mix} \\',r'Pair & Task & Correct & ms & Correct & ms & Correct & ms \\',r'\hline']
    for pair,ds in COMBOS:
        vals=[pair.capitalize(),ds.upper()]
        for x in [ABL,PRIMARY,'train_frozen_mixture']:
            r=getpol('panel',pair,ds,x);vals.extend([count(r['V2_correct']),f(r['mean_ms'],1)])
        latex.append(' & '.join(vals)+r' \\')
    latex += [r'\hline',r'\end{tabular}',r'\caption{Separate same-job panel results ($N=128$ per combination). Accuracy and latency use the same panel responses and original per-question measurements. Router latency includes original measured overhead; mixture values are expectations, not sampled deployment tail latency.}',r'\label{tab:p2-v2-panel-routing}',r'\end{table}',
        r'Four-minus-three correct-count differences on full development remain $-2,0,+1,0$; on the panels, correctness is identical per question and no designated router captures the six full-population AC-exclusive correct cases. The small-pair OBQA full three/four routers each gain one correct response versus old scoring. The large-pair OBQA full accuracy advantage over the frozen mixture remains positive under the conditional paired interval (+1.148 pp, 95\% interval [0.134,2.158]), but its separate panel latency is higher. Across the four panels, accuracy-difference intervals versus the frozen mixtures include zero; these results do not establish stable accuracy--cost gains. We preserve 20,000 paired question bootstrap resamples with seed 0 and percentile 95\% intervals, conditional on the old fitted policies and original single measurement. The small ARC three/four timing difference comes entirely from saved overhead with identical choices.',
        r'\paragraph{Remaining validation.} All four C2C training correctness targets change, requiring eight C2C correctness heads (two feature families per combination) to be refitted before claiming a V2-trained baseline. Receiver/text/AC correctness targets, query features, cost heads, and original measurements are unchanged. Training mixture inputs and budgets require reconsideration under any newly fitted router. Neither FFR/E0/E1 nor an independent held-out test is evaluated here; no method novelty is claimed.']
    (O/'paper/04_frozen_routing.tex').write_text('\n'.join(latex)+'\n')
    (O/'paper/README_ZH.md').write_text('''# 正文插入位置与证据边界

1. `01_evaluation_protocol.tex` 放入实验设置/评价协议。明确承认已曝光案例后的修订，不能写成从未看过 gold；297 项是定向检查，不是语义理解完整性证明。
2. `02_complementarity.tex` 放入四动作互补性/动机部分。两模型对×两任务均为 full 已曝光开发人口；并集是事后上界，不能当方法收益。
3. `03_flip_labels.tex` 放入目标定义之后或评价敏感性段落。区分格式失败和推理错误；P2-11 方向常数只作历史诊断，不冒称标准 Beta 二项后验。
4. `04_frozen_routing.tex` 放入已有基线路由结果与限制。full/panel 分两张表；所有策略仍按旧标签训练，V2 仅重评分。不得把辅助网格重新挑成重点或把 parser 维护当贡献。

各 LaTeX 文件首行给出相对证据路径，所有表格数值由当前 CSV 程序化生成。只用普通 table/tabular，无自定义宏；当前节点无 pdflatex，因此本轮完成语法/表格数值检查，未编译 PDF 或验证排版。接入实际 ICLR 模板时再处理浮动位置与列宽。

P2_STATE 未明确登记当前论文工程目录；本阶段不全盘搜索、不重建论文项目，仅交付这些可插入片段。D1 保留历史身份。FFR 效果、独立测试收益和 novelty 均未验证。
''')
    state=f'''
<!-- BEGIN P2-SCORING-V2 {O.name} -->
## 正式评分更版 P2_SCORING_V2（2026-09-12，ClusterB/the execution agent）

- 状态：**COMPLETE_SCORING_V2_READY_FOR_MAINLINE_REVIEW**。目录 `{P/O.name}`；报告 `P2_SCORING_V2_REPORT_ZH.md`，精简交接 `HANDOFF_ZH.md`。本次由接任 P2 唯一写入者完成，旧会话已交付停止。
- 正式版本 P2_SCORING_V2 / 2.0.0，冻结 UTC `{freeze['frozen_utc']}`；parser SHA256 `{freeze['code_sha256']}`。297 项定向检查通过，冻结后0次修改。审阅已曝光案例/结果后更版，不能声称全程盲于 gold；原 parser/配置/原答/历史报告/D1 均保留。
- 复用49,616来源记录；旧评分回放不一致0的既有验证未重做。full45,008动作与panel6,144动作分别重评，共享1,536条AC不相加。V2相对旧full改变158输出、正确性+129/-0；相对D1 full改变4条train输出、+3/-0，panel另1条+1；开发V2=D1。
- 标签目录 `{P/O.name/'labels'}`；`full_train_P2_SCORING_V2.jsonl` 9170行、`full_development_P2_SCORING_V2.jsonl` 2082行，panel train1024/开发512行。来源、split、版本和o/valid/y/f/改善/伤害/零收益/INVALID齐全，完整哈希见 LABEL_MANIFEST.json。
- 已保存P2-10策略重评无缺项：528行固定/路由/旧train混合，含原wordλ=.01三/四动作；另1273行旧固定混合概率。没有重拟合、改变选择/参数/混合概率或原时延。full开发四−三仍−2/0/+1/0题；panel仍逐题同分，原重点未捕获6道AC独占正确题。未确认稳定accuracy–cost优势的原主结论不变。
- 所有现有router仍由旧标签训练。四组合C正确性目标变化44/56/2/4，word/semantic共8个C头待有限重拟合；R/T/A共24头目标未变，查询特征/成本头/W不需因评分更版重做。旧C翻转训练标签变化51/60/2/3；方向常数仅P2-11历史诊断，不是审定Beta二项后验或FFR验证。受影响历史C比较/训练混合参照的下一轮范围见报告，不重做全部P2。
- 论文交付 `{P/O.name/'paper'}`：4个英文LaTeX片段+中文放置说明；状态未登记既有论文工程，未全盘搜索/重建。仅CPU单线程nice10、RSS<1GiB/累计CPU<600s，细目见最终回执；GPU/PBS/节点作业/模型载入/生成/特征/训练/ARC test读取均0。
- 下一步：交回Work主线审议有限V2基线更新与方法验证；本阶段完成即停止，不自动启动FFR/E0/E1/GPU。此交付是自然阶段迁移节点，ClusterB已冻结，可保留当前会话供核对；Work是否续用或另开由其自身上下文决定，不要求同步迁移。
<!-- END P2-SCORING-V2 {O.name} -->
'''
    (O/'P2_STATE_APPEND.md').write_text(state)
    (O/'HANDOFF_ZH.md').write_text(f'''P2 正式评分 V2 精简交接

状态：已完成评分冻结、标签重建、已冻结路由重评分和论文片段；GPU/PBS/训练/FFR/E0/E1为0。目录 `{P/O.name}`。
先读 P2_SCORING_V2_REPORT_ZH.md 首屏、RULE_FREEZE_V2.json、FINAL_RECEIPT.json。
V2比D1仅新增full训练4条解析变化/3条正确性改善，panel另1条改善；开发V2=D1。旧→V2 full正确性+129/-0。原重点四−三仍−2/0/+1/0；panel同分；实际accuracy–cost主判断未改。
现有router仍由旧标签训练：P2-10的8个C正确率头待批准的有限重拟合；24个R/T/A头目标不变。新C|R训练f相对旧改变116个，大ARC60/旧112；不能继续把旧格式失败解释为纯通信内容翻转。FFR未训练/未验证。
正式入口 scoring_v2.py；完整标签与哈希见 labels/LABEL_MANIFEST.json，train/dev和full/panel已分开；旧策略表 frozen_policy_rescoring.csv。不要重复生成、提特征、训练、提交PBS或重启已结束作业。
paper/已有4个英文正文片段，P2_STATE只追加本次状态。完成后已交回Work审议下一步，不自动启动方法验证。当前适合阶段交接；无需假定ClusterB与Work同步迁移。如上下文压缩，只从本交接和最终回执接续，不能重启已完成任务。
''')
    # Per-file brace and tabular arity checks; no claim of rendered/compiled LaTeX.
    for path in (O/'paper').glob('*.tex'):
        s=path.read_text();assert s.count('{')==s.count('}')
        assert s.count('\\begin{table}')==s.count('\\end{table}')
        assert s.count('\\begin{tabular}')==s.count('\\end{tabular}')
    save('evidence/paper_receipt.json',{'status':'SOURCE_AND_SYNTAX_CHECKED','files':[{'path':str(p.relative_to(O)),'sha256':sha(p)} for p in sorted((O/'paper').glob('*'))],
        'tables_generated_from_current_CSV':True,'tex_compiled':False,'limitation':'pdflatex unavailable; layout reviewed when inserted into manuscript template',
        'existing_manuscript_registered_in_P2_STATE':False})
    print('REPORT_PAPER_AND_STATE_APPEND_READY')
if __name__=='__main__':main()
