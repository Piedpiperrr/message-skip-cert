"""Lightweight rendering/accounting only; no models, labels, or numerical analysis."""
from pathlib import Path
import json,csv,datetime,hashlib
O=Path(__file__).resolve().parent
S=O/'summary'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,x):Path(p).write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def rows(name):return list(csv.DictReader((S/name).open()))
def fmt(x,percent=False,digits=3):return 'NA' if x=='NA' or x is None else f'{float(x)*(100 if percent else 1):.{digits}f}'
def md_table(headers,body):return '\n'.join(['| '+' | '.join(headers)+' |','| '+' | '.join(['---']*len(headers))+' |']+['| '+' | '.join(map(str,r))+' |' for r in body])
now=datetime.datetime.now(datetime.timezone.utc).isoformat()
validation=json.loads((O/'NUMERICAL_VALIDATION.json').read_text());assert validation['passed']
freeze=json.loads((O/'PROTOCOL_FREEZE.json').read_text())
assert sha(O/'frozen_config.json')==freeze['config_sha256'] and sha(O/'folds/group_folds.csv')==freeze['folds_sha256']
ledger=json.loads((O/'evidence/CPU_runs.json').read_text())
original=json.loads((O/'history/resource_resume_20260913/FINAL_RECEIPT.json').read_text())
allowance=json.loads((O/'evidence/resume_preparation_allowance.json').read_text())['CPU_seconds_charged']
charged=original['CPU_budget_charged_seconds']+allowance+sum(r['cpu_seconds'] for r in ledger)
jobrows=[]
def parse(t):return datetime.datetime.strptime(t,'%a %b %d %H:%M:%S %Y').replace(tzinfo=datetime.timezone.utc)
def seconds(t):
 h,m,s=map(int,t.split(':'));return h*3600+m*60+s
for jid in ['185606','185607']:
 path=O/'evidence/pbs'/('finished_'+jid+'.json');full=json.loads(path.read_text());name,j=next(iter(full['Jobs'].items()));assert j['job_state']=='F'
 jobrows.append({'job_id':name,'exit_status':j['Exit_status'],'queue':j['queue'],'account':j['Account_Name'],'host':j['exec_host'],'requested_walltime_seconds':seconds(j['Resource_List']['walltime']),'queue_seconds_qtime_to_stime':(parse(j['stime'])-parse(j['qtime'])).total_seconds(),'allocation_interval_seconds_stime_to_obittime':(parse(j['obittime'])-parse(j['stime'])).total_seconds(),'scheduler_resources_used':j['resources_used'],'scheduler_reported_walltime_seconds':seconds(j['resources_used']['walltime']),'scheduler_CPU_seconds':seconds(j['resources_used']['cput']),'allocated_GPU_quota':int(j['Resource_List']['ngpus']),'GPU_compute_usage':0,'allocated_ncpus':int(j['Resource_List']['ncpus']),'allocated_mem':j['Resource_List']['mem'],'placement':j['Resource_List']['place'],'raw_evidence':str(path),'raw_evidence_sha256':sha(path)})
resources={'stage':O.name,'finalized_utc':now,'CPU_budget_seconds':3600,'CPU_budget_charged_seconds':charged,'CPU_budget_remaining_seconds':3600-charged,'prior_charged_CPU_seconds':original['CPU_budget_charged_seconds'],'this_continuation_lightweight_work_allowance_seconds':allowance,'startup_failures_conservative_CPU_seconds':2,'PBS_numerical_supervisor_measured_CPU_seconds':ledger[-1]['cpu_seconds'],'measured_process_peak_RSS_KiB':max(r['peak_RSS_KiB'] for r in ledger),'RSS_limit_GiB':4,'fit_attempts':validation['LR_attempts'],'max_fit_attempts':320,'threads':1,'nice':10,'GPU_compute_usage':0,'GPU_quota_occupancy_seconds_stime_to_obittime':sum(j['allocation_interval_seconds_stime_to_obittime']*j['allocated_GPU_quota'] for j in jobrows),'GPU_quota_occupancy_seconds_scheduler_walltime_basis':sum(j['scheduler_reported_walltime_seconds']*j['allocated_GPU_quota'] for j in jobrows),'PBS_submissions':len(jobrows),'total_requested_walltime_seconds':sum(j['requested_walltime_seconds'] for j in jobrows),'scheduler_CPU_seconds_total':sum(j['scheduler_CPU_seconds'] for j in jobrows),'jobs':jobrows,'occupancy_interpretation':'One GPU quota per shared allocation. stime-to-obittime includes scheduler startup/teardown and targeted startup repair wait; resources_used.walltime is also retained. Neither is exclusive whole-node use.','sbank_charge':None,'sbank_charge_status':'Official sbank queries using numeric and full IDs returned identifier(s) not found; monetary/allocation-unit charge unavailable at finalization, never recorded as zero.','sbank_evidence':['evidence/pbs/sbank_jobs_185606_185607.txt','evidence/pbs/sbank_jobs_full_ids.txt'],'LLM_forward':0,'tokenizer_loads':0,'new_semantic_features':0,'ARC_test_reads':0,'environment_installs':0,'experiment_numeric_work_on_login_node':False}
save(O/'RESOURCE_RECEIPT.json',resources)
base=rows('baseline_update_summary.csv');flips=rows('flip_metrics.csv');decision=rows('decision_metrics.csv');paired=rows('paired_method_differences.csv');heads=rows('overhead_headroom.csv')
basetable=md_table(['模型对','数据集','动作数','旧头/V2评分准确率%','更新C头准确率%','选择变化题数'],[[r['pair'],r['dataset'].upper(),r['n_actions'],fmt(r['old_V2_rescored_accuracy'],True),fmt(r['updated_V2_accuracy'],True),r['changed_selections']] for r in base if r['family']=='word' and r['lambda']=='0.01'])
fliptable=md_table(['模型对','数据集','表征','动作','翻转率%','OOF AUC','OOF AP','log loss'],[[r['pair'],r['dataset'].upper(),r['family'],r['action'],fmt(r['positive_rate'],True),fmt(r['ROC_AUC']),fmt(r['AP']),fmt(r['log_loss'],digits=4)] for r in flips if r['fold']=='pooled' and r['scope']=='all' and r['predictor']=='FFR_E0'])
def k(r):return (r['pair'],r['dataset'],r['family'])
dd={(k(r),r['method']):r for r in decision if r['fold']=='pooled' and r['n_actions']=='4' and r['lambda']=='0.01'}
hh={k(r):r for r in heads if r['fold']=='pooled' and r['n_actions']=='4' and r['lambda']=='0.01' and r['left']=='FFR_E0' and r['right']=='query_independent'}
pt=[r for r in paired if r['fold']=='pooled' and r['n_actions']=='4' and r['lambda']=='0.01' and r['left']=='FFR_E0' and r['right']=='IndepLR']
comp=md_table(['模型对/数据集','表征','FFR准确率%','IndepLR准确率%','常数翻转/固定参照准确率%','FFR−IndepLR ΔU','FFR对固定参照余量ms'],[[r['pair']+'/'+r['dataset'].upper(),r['family'],fmt(dd[k(r),'FFR_E0']['accuracy'],True),fmt(dd[k(r),'IndepLR']['accuracy'],True),fmt(dd[k(r),'query_independent']['accuracy'],True),fmt(r['proxy_utility_difference'],digits=6),fmt(hh[k(r)]['admissible_added_ms'])] for r in pt])
jobtable=md_table(['PBS作业','退出码','排队秒','分配区间秒','调度器walltime秒','调度器CPU秒','GPU配额'],[[r['job_id'].split('.')[0],r['exit_status'],r['queue_seconds_qtime_to_stime'],r['allocation_interval_seconds_stime_to_obittime'],r['scheduler_reported_walltime_seconds'],r['scheduler_CPU_seconds'],r['allocated_GPU_quota']] for r in jobrows])
report=f'''# P2 V2基线定向更新与FFR-E0：完成报告

**状态：COMPLETE_BOUNDED_E0_VALIDATED。8/8个C头、280/280个OOF头、冻结评价与诊断、科学报告和英文LaTeX结果已完成。** 本状态表示本轮实验执行完成，不表示方法获得统一有效性证明或项目通过下一阶段门槛。更新时间：{now}。

本轮证据是异质且受限的：小模型对的C翻转有较弱预测信号；最醒目的小OBQA语义A翻转信号主要依赖INVALID相关样本。FFR在若干设定优于同表征IndepLR，但大部分优势可以由查询无关固定动作复现。全局方向常数暴露了限制，真实翻转代入既可能改善，也可能恶化决策。仅少数设定保留正代理开销余量，尚未验证新router在线成本。因此不能写成普遍无效、普遍有效、一般路由上界或项目去留结论。

## 冻结协议、来源与历史

阶段目录：`{O}`。配置SHA256 `{freeze['config_sha256']}`；折表SHA256 `{freeze['folds_sha256']}`。`PROTOCOL_FREEZE.json`、`frozen_config.json`、组折表、类别计数与来源索引均保持原哈希。评分V2、原答、标签和既有语义缓存直接复用；未重评分或重复原297项评分检查。

本次独立 `RESOURCE_ADDENDUM.json` 引用原冻结回执，只覆盖原PBS=0与登录节点例外要求，允许实际PBS分配内运行。原PARTIAL报告、回执、PROGRESS、交接和代码保存在 `history/resource_resume_20260913/`；`P2_STATE`只追加状态，不追改PARTIAL历史。

四组合×word/semantic两表征，LR固定L2、C=1、class_weight=None、lbfgs、max_iter=1000、random_state=0，全部λ为0/.01/.03/.1/.3/1/3；同分按R/T/C/A。没有网格、换种子、重划折、挑OOF最佳点或跨组合显著性检验。三动作仅排除A并复用同一组头。FFR只做train OOF，不进入开发集训练、选择或λ筛选。

OBQA共3466题，五折694/693/693/693/693；ARC共1119题、1118组，五折224/224/224/224/223。登记重复对仍共同位于ARC折0。TF-IDF只在fit折拟合并由两模型对和两方法共享；语义缓存逐ID对齐，无新提取或标准化。OOF所有七头均在当前训练折全新拟合，未复用任何见过完整train的旧正确率头。每个模型对/表征内每题恰有一次折外预测。

## 基线C头更新与固定开发评价

8个C头已完成，24个旧R/T/A正确率头、全部成本Ridge、c_ref和原vectorizer按组件哈希验证保留。更新产物位于 `baseline/`，原模型路径与新模型校验值见 `MODEL_INDEX.tsv`。固定开发评价仅应用预先规定策略，未根据结果调λ。

原重点word、λ=.01的完整开发集结果如下；旧列表示旧头在V2标签下评价，和更新后列使用相同题目与评分。其余原λ与semantic全部保存在 `summary/baseline_update_summary.csv`，逐题选择变化见 `baseline_changed_selections.csv`，没有只报告有利点。

{basetable}

这里完整开发集只解释准确率。`summary/baseline_panel_replay.csv`另给原128题开发panel的动作成本离线重放：例如word四动作λ=.01，大OBQA更新后panel准确率86.71875%、动作成本776.028 ms；小OBQA为50.78125%、452.145 ms。它们不是新策略全人口实测延迟，未叠加旧router开销冒称新router完整成本。原混合概率与旧B_train继续保留历史身份，新预算匹配混合没有另行冻结或运行。

## 翻转能否预测

下表是全部样本的pooled OOF点估计，AUC/AP均未基于选择阈值计算。每折及双方解析有效诊断子集另完整列于 `summary/flip_metrics.csv`；单类评价AUC/AP为NA，log loss按固定epsilon=1e-15计算。

{fliptable}

小模型C翻转在OBQA的word/semantic AUC为0.551/0.559，在ARC为0.577/0.590，存在弱排序信号。相应semantic log loss：OBQA 0.6883，对折内常数率0.6919；ARC 0.6756，对常数0.6893。大模型翻转稀少，信号不稳定；大ARC的A总共只有8个翻转，其折4为0/223，按冻结规则AUC/AP记NA，未重划或删题。不能只凭类别稀少导致的低log loss称预测有效。

常数参照在每个评价折内是常数，但不同折的fit率可以不同，因此其pooled AUC不必等于0.5；这不表示它使用了题目特征。完整折级指标可检验这一人口构成效应，不能把pooled分数与全局固定0.5简单等同。

## INVALID分析

小OBQA semantic A的全样本AUC=0.6345、AP=0.1142，看起来较强；限制到R和A均有效的3128题后，仅58个翻转，AUC降至0.4577、AP=0.0170。全样本240个A翻转中，179个来自A无效而R有效，另3个来自R无效而A有效；双方无效的156题不发生解析结果翻转。因而该信号不能直接解释为有效选项之间、能带来收益的通信变化预测。

小ARC A在全样本有140个翻转，其中双方有效部分仅31个；semantic AUC从0.5641变为0.5225。小C翻转在双方有效子集仍有弱信号（OBQA semantic AUC=0.5386，ARC=0.5634），但绝对水平仍有限。`summary/invalid_analysis.csv`保留所有分区的题数、翻转、改善、伤害和零收益翻转；正式策略没有排除INVALID题。分区计数已独立对账。

## FFR相对IndepLR、常数率和固定参照

为与原操作点便于对照，下表展示四动作λ=.01切片；这是固定λ的描述性展示，**没有为OOF选择最佳λ或宣称显著性**。`decision_metrics.csv`、`paired_method_differences.csv`和论文附表保留全部7个λ、两种动作数及每折/pooled结果；所有单独固定动作亦已报告。ΔU是未计新router开销的准确率减折内成本代理。

{comp}

这个切片下，小OBQA两种表征、小ARC两种表征的FFR均逐题选择C，且与常数翻转率和查询无关参照完全相同。因此小OBQA word相对IndepLR的+2.308个百分点准确率、+0.025837代理效用，不能归因于学到了有效的逐题路由。小ARC semantic同一点反而低于IndepLR，ΔU=-0.005108。大ARC FFR近乎全部选择R，λ=.01也不优于IndepLR。

大OBQA word四动作λ=.01相对IndepLR有+1.558个百分点准确率、ΔU=+0.006376；对固定T参照却是准确率低0.087个百分点、ΔU仅+0.000719，依赖减少部分昂贵动作调用。这是更弱且有成本条件的证据。semantic在同一任务相对IndepLR为小正ΔU，但对固定参照为负。

全λ结果并不保持统一排序。word小模型对在若干低/中λ点相对IndepLR有正代理差；semantic在小ARC低λ和两小组合λ=1可为负。λ=3时本轮相对IndepLR的差为0，不能写成额外正信号。λ=0只解释准确率，效用及开销格均为NA。

三/四动作没有额外拟合。在λ=.01，FFR两种动作数在各组合/表征的准确率一致；大OBQA四动作仅少量选择A，word约0.346%、semantic约0.202%，其他组合此点不选A。完整三/四动作成本与配对差在表中保留，不据此泛化为A永远无用。

## 方向常数与真实翻转代入

方向常数为(改善−伤害)/(翻转+2)，是向0收缩的有符号收益近似，**不是标准Beta二项后验**。零收益翻转保留。大模型两任务的C在全部训练折方向为负；大OBQA仍有74次C改善与144次伤害，大ARC有16次改善与24次伤害。负的全局方向无法识别这类动作内部的获益子人群。小模型A各折也均为负，但仍分别存在33次和19次A改善；这些改善没有因净收益为负而消失。`direction_diagnostics.csv`完整列出fold方向、fit gain/harm/flip以及heldout诊断。

用评价折真实翻转替换预测翻转仍保留原折内方向与成本。四动作λ=.01：小OBQA准确率从52.048%降至50.144%，代理效用差-0.020982；小ARC从59.964%降至55.496%，差-0.047506。这说明即使知道是否翻转，也不足以支持该常数方向下的跨动作选择。特别是当C不翻转时，真实翻转规则可能转选T，而被C不翻转条件筛出的子集不保证遵循全局T方向；仅改善翻转预测不能保证决策改善。

大ARC同一点真实翻转代入将准确率从91.242%提高到92.583%；大OBQA主要改善代理效用而非准确率。λ=1的小模型诊断又可能明显改善，故代入结果不是单调的预测器上界，也不是一般路由上界。结论仅为本轮分解与方向近似存在可见限制，不能从这一诊断反推一般路由算法的可达性能或项目去留。

## 代理开销能否支持部署

两种方法、查询无关参照和固定动作均使用当前fit折train panel的动作均值；c_ref为同批R均值。评价折panel成员排除，均值来源逐折可查。FFR对固定参照的统一新增毫秒容许值为ΔU/[λ·mean(1/c_ref_i)]；每折值采用ΔU_k·c_ref_k/λ，均保存于 `overhead_headroom.csv`。负数表示没有非负开销余量，0表示无正余量，λ=0为NA，未裁剪负值。

大OBQA word λ=.01的余量仅约18.263 ms（三动作）或18.149 ms（四动作）；同任务word λ=.03为-1.023 ms。小ARC λ=1存在约3.274 ms（word）和0.875 ms（semantic）的正代理余量；这只是已冻结全λ表中的描述，不能据此选为显著最佳点。小模型在λ=.01相对固定C的余量为0。其余表中零或负余量均原样保留。

这些数值仅能回答“若所有成本代理和人口分布保持成立，还能容纳多少统一新增时间”。18 ms可能允许某些廉价实现，但本轮没有测量TF-IDF变换、语义编码、相应方法的3个或4个头推断、数据搬运或路由调度的完整在线开销，无法判定实际实现是否满足。语义缓存复用消除了本次训练阶段的编码计算，不能在部署账本中默认编码免费。还缺同一人口、同一执行条件下的新router端到端accuracy–cost实测和正式预算匹配对照。

## 数值验证与执行修正

`NUMERICAL_VALIDATION.json`通过：配置/组折/来源哈希不变；首个正式C头sigmoid与predict_proba核对、所有头有限概率检查；首个正式OOF折独立标量决策、训练IDF、成本成员与均值和方向公式验证；每个完整决策/配对表回算、跨不等长折按题加权、开销恒等式及INVALID分区对账。没有额外smoke模型。288次LR拟合全部成功，无数值重拟合或收敛警告。

执行层变更见 `evidence/EXECUTION_CHANGELOG.json` 与 `evidence/pbs/`。首作业185606在Python前因计算节点myquota缺失退出127；续接185607先暴露了cgroup数值ID路径格式兼容错误，在同一分配内按实际`/jobs/185607`路径修正，再通过owner/host/nodefile/cgroup和sharedfs环境读写核验生成真实许可。没有登录节点伪造allowed、删除检查或寻找登录计算例外。训练与数值汇总/验证全部在ClusterB-gpu-04执行；登录端仅提交、轻量状态与文稿/回执整理。

## 资源与调度回执

{jobtable}

两次申请时长合计7200秒，第一作业F后才提交第二作业；当前两作业均F，未操作其他阶段作业。每次分配为gpu-queue select=1，调度器实际给32 CPU配额、120gb内存、1个GPU配额，place=pack:shared。实际计算绑定一个CPU、nice10、BLAS/OpenMP线程1，GPU计算使用为0，调度器resources_used.ngpus也为0。[ClusterB官方队列规则](https://docs.cluster.invalid/ClusterB/queueing-and-running-jobs/running-jobs/)。

GPU配额占用按stime至obittime区间计合计123秒；调度器resources_used.walltime口径合计113秒，差异含启动/退出等调度阶段，两个口径均保留。这是一个共享GPU配额的占用，不是独占整个节点，也不因为实际GPU计算为0而把PBS/分配成本记0。官方sbank以短ID和完整ID查询均返回identifier not found；具体收费金额/分配计费单位当前不可获得，记NA并保存查询原文，不冒填0。

正式数值监督器计量CPU为38.164606秒（含拟合、首次正式产物验证、汇总、最终核验和监督开销）；前期31.608204秒完整继承。本次轻量读取、代码/文稿编写、语法检查、状态查询与打包另保守计60秒，两个启动失败各保守计1秒，**累计计账{charged:.6f}/3600 CPU秒**，剩余{3600-charged:.6f}秒。调度器CPU计量合计39秒，是独立粗粒度口径；不与过程计量重复相加。过程峰值RSS为399360 KiB（390 MiB），低于4 GiB。完整账本、各阶段CPU、原始调度记录及解释见 `RESOURCE_RECEIPT.json` 与 `evidence/CPU_runs.json`。

LLM前向、tokenizer载入、新语义特征、ARC test读取、环境安装、CUDA计算均为0；没有E1/confidence/feedback或新增GPU实验。

## 交付、可复核性与下一步边界

- `baseline/`：8个C头和8个更新bundle；`oof/`：280头、折内TF-IDF和40组正式折外预测NPZ。
- `MODEL_INDEX.tsv`：296个模型/更新bundle条目及哈希；旧24个头保留证明在各baseline COMPLETE回执。
- `summary/`：112行基线更新、944行变化选择、256行panel重放、18340行逐题OOF、576行翻转指标、5712行决策、5712行配对差、5712行开销、720行INVALID与120行方向诊断。
- `paper/01`沿用方法，`02`沿用冻结协议，`03_current_status.tex`更新完成与证据状态，`04_results_tables.tex`保留全部λ，`05_results_and_limitations.tex`提供英文正文。未安装TeX、未重建论文工程，尚未编译或做版面验证。
- `FINAL_RECEIPT.json`、`RESOURCE_RECEIPT.json`、`PROGRESS.json`和精简handoff给出真实完成状态，`P2_STATE`保留并追加原PARTIAL历史。轻量包包含可审阅源码、固定协议、CSV、回执与论文片段，模型实体保留在原sharedfs目录。

本轮E0执行已完成。可支持的结论是“部分翻转有预测信号，但净新增逐题路由价值有限且依赖设定；方向假设和在线成本证据仍是主要限制”。**交回Work审议下一科学任务，不自动启动后续实验，也不以本轮结果直接决定项目去留。**
'''
(O/'P2_V2_BASELINES_FFR_E0_REPORT_ZH.md').write_text(report)
# Preserve existing method/protocol content; change only the obsolete status comment.
p=O/'paper/02_exploratory_protocol.tex';t=p.read_text();t=t.replace('% Prospective frozen protocol only; no new fit or OOF evaluation has been executed.','% Protocol frozen before execution; scientific settings unchanged in the completed run.');p.write_text(t)
(O/'paper/03_current_status.tex').write_text(r'''% Evidence status after the completed, frozen, training-only experiment.
\paragraph{Current evidence status.}
The targeted update of all eight C correctness heads and all 280 fold-specific
OOF heads has been completed under the frozen protocol on a ClusterB PBS
compute allocation. All 288 logistic fits succeeded without convergence
warnings. The fixed development evaluation, all prespecified operating
points, and the numerical consistency checks are complete.
The original configuration and duplicate-isolated folds are unchanged.
These exploratory OOF results show heterogeneous flip predictability,
limited incremental routing value beyond query-independent references,
and limitations of the constant-direction approximation. They do not
establish a general routing upper bound, statistical significance at a
selected operating point, or measured online accuracy--cost gains.
FFR has not been used for development-set selection or evaluated on ARC test.
''')
(O/'paper/05_results_and_limitations.tex').write_text(r'''\paragraph{Targeted baseline correction.}
We refitted the eight C correctness heads using the revised labels while
preserving all 24 R/T/A heads, cost regressors, reference costs, and frozen
feature components. At the inherited word-feature operating point
$\lambda=0.01$, four-action development accuracy changed from 86.388\% to
86.253\% on large-pair OpenBookQA, remained 89.967\% on large-pair ARC and
48.787\% on small-pair OpenBookQA, and changed from 51.171\% to 51.505\% on
small-pair ARC. These are fixed evaluations, not operating-point selection.
All original $\lambda$ values and both feature families are reported.
Development-panel costs are replays of original action measurements;
new-router end-to-end latency was not measured.

\paragraph{Predictability is heterogeneous and partly linked to invalid outputs.}
For the small model pair, C-flip pooled OOF AUC was 0.551/0.559 on
OpenBookQA and 0.577/0.590 on ARC for word/semantic features, respectively.
The semantic log losses were 0.6883 and 0.6756, compared with 0.6919 and
0.6893 for the corresponding fold-training flip-rate predictors.
The small-pair OpenBookQA A head had semantic AUC 0.6345 and AP 0.1142 on
all examples. However, on the diagnostic subset where both R and A were
valid, AUC fell to 0.4577 and AP to 0.0170, with only 58 flips among 3,128
examples. Of 240 A flips in the full population, 179 involved invalid A
and valid R, and another three involved invalid R and valid A.
Thus this ranking signal cannot be identified with beneficial changes
between valid options. No examples were removed from the main evaluation.
Large-pair flips were rare and inconsistently predictable. Large-pair ARC
had only eight A flips overall; its prespecified held-out fold 4 had none,
so that fold's AUC and AP are NA. Its fold assignment was not changed.
A fold-training constant predictor is constant within a fold but may differ
across folds, so its pooled AUC need not equal 0.5.

\paragraph{Comparison with matched correctness heads and fixed references.}
We report all seven frozen operating points as exploratory paired point
estimates. The four-action $\lambda=0.01$ slice is shown for comparability
with the inherited operating point, without selecting an OOF optimum.
On large-pair OpenBookQA with word features, FFR exceeded matched IndepLR
by 1.558 accuracy percentage points and 0.006376 proxy utility. Against
the query-independent reference, however, FFR lost 0.087 accuracy points
and gained only 0.000719 proxy utility by reducing some costly calls.
On small-pair OpenBookQA, word FFR exceeded IndepLR by 2.308 accuracy points
and 0.025837 proxy utility, but FFR, the constant-flip predictor, and the
query-independent reference all chose C for every question.
The same fixed-C equality held for both feature families on both small-pair
tasks at this operating point. Such improvements over IndepLR do not show
added value from query-dependent flip predictions. Small-pair ARC semantic
FFR instead had a proxy-utility deficit of 0.005108 relative to IndepLR;
large-pair ARC also showed no improvement at this point.
Across the complete sweep the rankings changed with representation and
cost weight; equality at high cost weights is not additional positive
evidence. Three- and four-action FFR had identical accuracy at
$\lambda=0.01$ in these comparisons, with only sparse A selection on
large-pair OpenBookQA. This is a local ablation result, not a claim that A
is universally unnecessary.

\paragraph{The direction approximation can limit selection.}
The fold-training direction for C was negative in all large-pair folds,
although C produced 74 improvements and 144 harms on OpenBookQA and
16 improvements and 24 harms on ARC. A negative global direction cannot
represent action-specific subpopulations with positive benefit.
The estimator $(N^+-N^-)/(N^{\mathrm{flip}}+2)$ retains zero-gain flips
and shrinks signed gain toward zero; it is not a standard binary Beta
posterior. Substituting true held-out flip indicators while retaining
these directions and costs was not monotonic in decision quality.
At four-action $\lambda=0.01$, the substitution reduced small-pair
OpenBookQA accuracy from 52.048\% to 50.144\% and ARC accuracy from
59.964\% to 55.496\%, with proxy-utility changes of $-0.020982$ and
$-0.047506$. When C does not flip, switching to another flipping action
conditions on a different subset for which its global direction need not
be valid. Conversely, on large-pair ARC, true-flip substitution improved
accuracy from 91.242\% to 92.583\%; at larger cost weights, it could also
improve the small-pair results. This non-deployable diagnostic exposes
limitations of the constant-direction decision rule, and must not be
interpreted as a general routing upper bound.

\paragraph{Proxy headroom is limited and online evidence remains missing.}
All OOF costs are action means from the current fold's training-panel
members, with the corresponding R mean as the reference. New routing
overhead is excluded. Relative to the query-independent reference, the
pooled allowance for uniform additional milliseconds is
\begin{equation}
h_{\max}=\frac{\Delta\overline U}
 {\lambda\,\frac{1}{n}\sum_i c_{\mathrm{ref},i}^{-1}},\qquad \lambda>0.
\end{equation}
Negative values mean that no nonnegative additional overhead is supported.
For large-pair OpenBookQA word FFR at $\lambda=0.01$, the allowance was
18.263 ms with three actions and 18.149 ms with four; at $\lambda=0.03$
it was $-1.023$ ms. Small-pair ARC at $\lambda=1$ had allowances of
3.274 ms (word) and 0.875 ms (semantic), while the fixed-C-equivalent
small-pair policies at $\lambda=0.01$ had zero positive allowance.
These are descriptive entries from the complete frozen sweep, not
post-selected significant operating points. At $\lambda=0$, only accuracy
is interpreted and utility/headroom entries are NA.
The allowances are conditional proxy quantities, not measured feasibility:
feature transformation or encoding, head inference, data movement, and
routing orchestration still require measurement on the same population.
Reusing cached semantic embeddings during this experiment does not make
online encoding free. End-to-end accuracy--cost measurements and a
separately frozen budget-matched comparison are still needed.

\paragraph{Scope of the evidence.}
The experiment used one CPU thread with niceness 10 and no CUDA, language
model inference, tokenizer loading, or new semantic feature extraction.
The eight baseline updates, 280 OOF heads, and all numerical summaries were
completed and checked on the compute node. All frozen operating points,
folds, invalid-output partitions, and successful artifacts are retained.
The results constrain this exploratory E0 specification; they neither
automatically reject the project nor authorize a subsequent experiment.
''')
# Split the generated baseline table into 16 seven-row blocks for downstream insertion.
p=O/'paper/04_results_tables.tex';t=p.read_text();first,rest=t.split(r'\paragraph{Pooled OOF flip prediction (all examples).}',1)
blocks=[r'% Rendered from validated CSVs; all original lambda values retained.']
for pair,ds in json.loads((O/'frozen_config.json').read_text())['combinations']:
 for family in ['word','semantic']:
  for na in ['3','4']:
   blocks += [r'\paragraph{Fixed development evaluation: '+f'{pair}, {ds.upper()}, {family}, {na} actions.'+'}',r'\begin{tabular}{rrr}',r'$\lambda$ & Old acc. (\%) & Updated acc. (\%) \\']
   for r in base:
    if (r['pair'],r['dataset'],r['family'],r['n_actions'])==(pair,ds,family,na):blocks.append(' & '.join([r['lambda'],fmt(r['old_V2_rescored_accuracy'],True),fmt(r['updated_V2_accuracy'],True)])+r' \\')
   blocks.append(r'\end{tabular}')
p.write_text('\n'.join(blocks)+'\n'+r'\paragraph{Pooled OOF flip prediction (all examples).}'+rest)
(O/'paper/README_ZH.md').write_text('''# 论文片段放置与状态

- 01_motivation_and_candidate.tex：沿用动机与方法定义，向0收缩的有符号方向近似不称Beta二项后验。
- 02_exploratory_protocol.tex：原冻结科学协议，未改变模型、数据、折表、λ或统计规则；只更新过时的未执行注释。
- 03_current_status.tex：真实完成状态与证据边界。
- 05_results_and_limitations.tex：英文LaTeX正文，覆盖翻转可预测性、与IndepLR/固定参照比较、INVALID、方向限制和在线成本缺口。
- 04_results_tables.tex：全部原λ的基线开发与OOF附表、pooled翻转指标；以分块表格供现有论文工程插入。每折、有效性子集、方向、配对与开销完整数值在summary/CSV。

数据来源是本阶段计算节点已验证的CSV；没有挑OOF最佳λ、显著性或方法普遍成功主张。既有V2片段沿inherited_V2_fragments.json继续引用。未安装TeX、未重建论文工程、未编译或验证最终版面。
''')
# Root links satisfy the original output-plan names without duplicating growing CSVs.
for p in S.glob('*.csv'):
 target=O/p.name
 if not target.exists():target.symlink_to(Path('summary')/p.name)
print(json.dumps({'report_written':True,'paper_written':True,'resources':resources},ensure_ascii=False,indent=2))
