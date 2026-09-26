# Render already computed CSV/JSON into documentation; no fitting, matrix or inference.
from common import *
main=list(csv.DictReader((P/'summary/main_dev.csv').open()));mm={r['family']:r for r in main};pop=read(P/'summary/populations.json');pol=read(P/'models/deployment.json');res=read(P/'RESOURCE_RECEIPT.json');comp=res['compute_components'];rank=list(csv.DictReader((P/'summary/ranking.csv').open()))
def num(v,d=3):return f'{float(v):.{d}f}' if v not in ['',None] else 'NA'
def pct(v,d=2):return num(float(v)*100,d)+'%' if v not in ['',None] else 'NA'
def table(headers,rows):return '| '+' | '.join(headers)+' |\n| '+' | '.join(['---']*len(headers))+' |\n'+''.join('| '+' | '.join(map(str,r))+' |\n' for r in rows)
md='''# P2_RISK_CALIBRATION_BINARY_PILOT 中文主报告

**完成状态：COMPLETE，交回 Work，停止本轮执行。** 本轮分歧监督具有本人口内可观察的查询级排序信号；统一校准返回了可用工作点，计入特征费后仍有组件重组节省。但同规则 correctness-R 基线覆盖更高、成本更低、观测效用更高，故不支持分歧监督优于 gold 监督。定位仍是二元 FFR 的监督与校准变体，不主张新策略族或已成立原创贡献。

- **排序是否有信号：有探索性支持。** 候选 dev AUROC=0.763143、AP=0.281858（dev 分歧基率0.097035）。冻结候选的230题中改变6题；覆盖匹配的均匀随机子集期望22.318题改变，超几何描述范围15–30。该比较描述本人口，不是独立显著性检验，也不恢复未曝光身份。
- **校准是否返回有用工作点：是。** 候选q=.30，cal为6/380，p=.000409609，100项校正后的单侧CP上界.046781≤.05。dev覆盖230/742=31.00%，条件改变率6/230=2.609%。dev描述性95%区间为[0.963%,5.591%]，不是校准证书，不能写成这批历史数据获得无条件90%部署保证。
- **计特征费后是否仍省：在本轮组件重组口径下，是。** 候选平均797.166ms，比Text少178.598ms（18.30%）；新特征平均约40.0846ms/题全额计入，每题另计该候选单头和选择器。正确数643，相对Text的645少2题（−0.2695个百分点）；不是答案完全不变或实际正确数保证。
- **与同规则gold基线相比：不支持候选更优。** correctness-R路由291题、改变7题、正确644、平均740.087ms、U=.839727；候选U=.836204。候选比harm节省更多且正确数相同；Diff和随机族均按规则回退Text。所有方法本轮新增人工标注为0；算法所需gold分别记账，不能把现有gold称为新节省的人工费用。

## 协议、人口和隔离

只有large/OBQA、参考Text、动作R/Text。未执行LDR、C/A新头、其他任务/数据集、选层、PCA、超参数搜索、多seed或ARC test。原冻结目录只读，原端到端结果保持原身份。唯一状态写入为本轮事实追加。

题目规范化沿用项目定义：把Question和按原顺序的标签/选项文本拼接后合并空白，不用id前缀。标签无关代表规则为完整id字典序最小者；排序代表后用Python random.Random(0)打乱，前2100个fit，其余cal。先保存清单和SPLIT_FREEZE，再统计人口。原train3466行=3466唯一题，dev742行=742唯一题，未发现跨train/dev重复；均未删题或重抽seed。

'''
md+=table(['人口','N','d分歧数/基率','R正确','Text正确','双INVALID','仅R INVALID','仅Text INVALID'],[[s,r['N'],f"{r['d_count']}/{r['N']} ({pct(r['d_rate'])})",r['R_correct'],r['Text_correct'],r['both_INVALID'],r['R_only_INVALID'],r['Text_only_INVALID']] for s,r in pop.items()])
md+='''
这里的dev基率72/742=9.7035%由本轮路由哈希冻结后新完成的评价得到，不是把train346/3466套到dev。d为冻结V2解析选项差异，保留INVALID；两个INVALID按相同处理，本轮fit/cal/dev双INVALID均为0。没有重评分或重跑297项旧检查。

复用3466条8192维train E1 z；Qwen3-8B checkpoint b968826d9c46dd6066d109eabc6255188de91218、原receiver提示、thinking off、BF16/SDPA；model.layers[25]输出和model.norm输出最后有效token分别FP32 L2归一化，eps=1e-12，拼接除sqrt(2)。dev按同定义采742条，第一条与第26层输入及最终backbone输出作定向核对，未增加prefill。

四头统一L2 LogisticRegression(C=1, lbfgs, max_iter=1000, random_state=0, class_weight=None)，无额外标准化，只有fit进入拟合。4次拟合、4头收敛、0警告、0常数伪装拟合。候选拟合进程只读id/z/d，cal接口也只有id/z/d；baseline_fit单独含y_R/y_T/harm，没有cal gold。cal/dev正确性只在部署与dev路由冻结后用于报告。cal选阈值不选模型，旧OOF/全train头未复用。

新划分仅隔离这一次计算。历史train/dev已经多次参与研究决策，Text参考也借助过历史正确率，不能称整个研究从未接触gold或本轮获得未曝光独立确认集。

## 理论对象与校准

共同评分器下逐题有 $y_T-y_\\pi\\le 1[o_\\pi\\ne o_T]$，故 $E[y_T-y_\\pi]\\le\\kappa V$，其中 $V=P(o_\\pi\\ne o_T\\mid\\pi=R)$，$\\kappa=P(\\pi=R)$。这是总体期望准确率差与改变风险的关系，不是742题实际正确数的确定性下界；不保证原始文本或语义等价。全Text的V=NA，边际改变率0。

每学习分数20个预定q=.05,.10,…,1；q<1阈值为fit排序第ceil(q*n_fit)值，u≤阈值路由R、并列整体纳入；q=1为+∞、严格固定R。随机族使用独立PCG64(0)随机流，按已冻cal列表后dev列表各取一次Uniform，原币值落盘，不看答案、不重选；在线含义为每个新请求独立掷币。

所有阈值、随机流在校准器读取cal分歧前冻结。100个假设统一检验H:V≥.05，p=BinomialCDF(k;n,.05)，n=0时p=1；接受p≤.10/100=.001。上界BetaQuantile(.999;k+1,n−k)，n=0或k=n时置1。M始终100，不因重复阈值改变。每族取最大的已接受q；没有接受项则固定Text，不补中间点、插值或改检验。固定R/Text只作描述参照，不额外增加搜索。

条件于固定fit模型与有限策略族，且cal/未来请求独立同分布时，二项p值与union bound支持接受集合FWER≤.10。该程序属于既有[LTT框架](https://arxiv.org/html/2110.01052v5)的具体实例化，不是新理论。本轮历史曝光限制其确认证据地位，程序返回接受不等于这批历史数据建立无条件90%部署保证。

'''
md+=table(['分数族','接受q集合','冻结q / 模式','cal路由n','cal改变k/n','p','校正CP上界'],[[f,','.join(f'{q:.2f}' for q in r['accepted_q']) or '无',f"{r['q']:.2f} / {r['mode']}",r['calibration']['n_R'] if r['calibration'] else 0,f"{r['calibration']['changed']}/{r['calibration']['n_R']}" if r['calibration'] else 'NA',num(r['calibration']['p_value'],9) if r['calibration'] else '1（空路由约定）',num(r['calibration']['CP_upper_0_999'],6) if r['calibration'] else '1（非接受项）'] for f,r in pol.items()])
md+='''
完整100项见summary/calibration_100.csv。必要边界均通过：空路由p=1/上界1；全部改变p=1/上界1；0/134的p=.001035054不接受，0/135的p=.000983302接受。并未根据这些诊断换规则。

Diff没有接受项，不能解释为没有排序信号：其cal/dev AUROC=.754484/.754789；cal q=.05为0/69，样本小，q=.20为4/279，经验风险1.434%，但p=.001548458、上界5.201%仍不通过。其低风险子集与100项校正下的样本量/风险余量不足并存，无法从这一次数据区分更深的成因。随机族cal各q经验风险均超过5%，最小p约.99948；这与其查询无关性质及本人口10.469%分歧基率相符，不应套用“所有不接受都是功效不足”的解释。D的低q也有零改变132题而不能通过；Bonferroni避免了这种首点不接受阻断后续全部策略。

## 冻结部署点与成本主表

**主表身份：新增特征计时 + 历史固定完整请求的组件重组成本；不是新策略端到端实测。** D=disagreement；R=correctness-R分数（不是Fixed_R动作）；Diff=p_T−p_R；H=harm；Random=查询无关随机族。

'''
md+=table(['策略','R路由n/742','条件改变k/n','边际改变k/742','获益/伤害/中性','正确数','Δ准确率(pp)','mean ms','median ms','p95 ms','净节省 ms','U'],[[r['family'],f"{r['n_R']}/742",f"{r['changed']}/{r['n_R']} ({pct(r['conditional_risk'])})" if int(r['n_R']) else 'NA',f"{r['changed']}/742",f"{r['benefit']}/{r['harm']}/{r['neutral_change']}",r['correct'],num(float(r['accuracy_diff_Text'])*100,4),num(r['mean_cost_ms']),num(r['median_cost_ms']),num(r['p95_cost_ms']),num(r['net_saving_vs_Text_ms']),num(r['U'],6)] for r in main])
md+='''
全部dev R/Text输出有效，七个描述/部署策略的INVALID均为0，路由子集双INVALID、仅R INVALID、仅Text INVALID也均为0；完整fit/cal/dev每个策略的组成、准确率和cal p/上界在附表REPORT_TABLES_ZH.md及summary/deployment_all_populations.csv。Diff/Random回退Text，去掉不存在的特征及头费用；采特征仅供排序诊断的消耗仍计实验资源账。

D的6次改变为2获益、4伤害、0中性，实际准确率差−2/742。其dev条件风险95%描述区间[.009632,.055913]；correctness-R为[.009725,.048932]，H为[.011553,.066774]。这些区间没有100项校正、不是对dev的同一风险证书；报告风险低于5%的点估计不等于已确认未来约束。

每题费用为实测feature_ms + 本策略实际所需head/selector_ms + 被选历史完整固定请求latency_ms。D、R、H各一头，Diff两头分别计时；候选没有承担另三头的诊断费用。所有选择性学习策略在每题付E1费；R与Text答案请求均完整计费，不用“反正要prefill”抵扣。q=1或Text回退的常数策略删除无须执行的特征/头。随机不付E1费。

'''
md+=table(['新增/复用计算项目','数值','口径'],[['新dev特征',f"{comp['new_feature_wall_seconds']:.6f}s / 742 = {comp['new_feature_wall_seconds']*1000/742:.6f}ms/题",'包含首题冷启动；不含模型加载和存盘'],['D单头+selector',f"{comp['head_selector_measured_seconds_by_family']['D']*1000/742:.6f}ms/题",'逐题实测、候选单独计'],['R单头+selector',f"{comp['head_selector_measured_seconds_by_family']['R']*1000/742:.6f}ms/题",'逐题实测'],['Diff两头+selector',f"{comp['head_selector_measured_seconds_by_family']['Diff']*1000/742:.6f}ms/题",'诊断实测；部署回退不收费'],['H单头+selector',f"{comp['head_selector_measured_seconds_by_family']['H']*1000/742:.6f}ms/题",'逐题实测'],['Random coin+selector',f"{comp['head_selector_measured_seconds_by_family']['Random']*1000/742:.6f}ms/题",'诊断实测；部署回退不收费'],['新receiver加载',f"{comp['new_model_load_wall_seconds']:.6f}s",'实验startup资源；不算每题稳态特征费'],['新四头拟合',f"{comp['new_fit_CPU_seconds']:.6f}s CPU",'导入、IO、其余计算另在总CPU账'],['历史train E1特征',f"3466条 / {comp['historical_train_feature_wall_seconds']:.6f}s",'原meta累计，复用、非新采'],['历史train R/T请求',f"6932次 / 估计{comp['historical_train_RT_request_seconds_estimated_from_256_panel_means']:.3f}s",'由旧256题panel均值折算，非完整train逐题实测总时']])
md+='''
固定lambda=.01、c_ref=262.462515ms，U=accuracy−lambda*mean_cost/c_ref，没有用dev重估。新的receiver特征在一张A100分配下测量，旧完整R/T请求来自两张GPU常驻配置；组件相加无法反映新的真实端到端交互、缓存、设备与时间漂移。单线程CPU测头的顺序固定为D/R/Diff/H/Random，逐题首用和运行波动保留，较小的头计时差不能当算法优势。所有特征被多族诊断复用仅为实验计算，重组在线策略各付自身的全额特征费。

## 相同覆盖、相同约束与探索性差异

'''
matched=list(csv.DictReader((P/'summary/coverage_matched_descriptive.csv').open()))
md+=table(['覆盖锚点','n','D改变','R改变','Diff改变','H改变','冻结随机排序前n改变','均匀子集期望','超几何95%范围'],[[r['anchor_frozen_family'],r['n_R'],r['D_changes_at_exact_n'],r['R_changes_at_exact_n'],r['Diff_changes_at_exact_n'],r['H_changes_at_exact_n'],r['Random_changes_at_exact_n'],num(r['random_expected_changes']),f"{r['random_hypergeom95_low']}–{r['random_hypergeom95_high']}"] for r in matched if int(r['n_R'])])
md+='''
该表仅把各分数按dev固定顺序稳定排序取前n，用于相同覆盖的排序诊断；不把这些次序点变成新的阈值或部署策略。均匀子集期望用真实dev基率72/742，范围使用超几何分布，不是新增2000次随机拟合，也不是推进门槛。候选不是“比覆盖率匹配随机覆盖率更高”，而是在同覆盖下观察到更少改变；在相同校准规则下，候选返回31.00%的dev覆盖而随机回退Text。

![全部预定q的校准/开发风险—覆盖曲线](figures/risk_coverage.png)

图中实心点为cal接受项、空心为未接受项、星号为最终部署点；dev仅按cal身份标记，没有重新接受或选点。无R路由的Text回退写为NA而非在图上伪造零条件风险。所有q数值见summary/grid_curves.csv。

配对bootstrap固定所有模型/阈值，在742题联合重采样一次（seed=0、2000次、百分位95%描述区间）。D−Text准确率差−.002695，区间[−.009434,.004043]；mean成本差−178.598ms，区间[−203.913,−153.137]；ΔU=.004109，区间[−.002693,.010457]。D−correctness-R的ΔU=−.003522，区间[−.006624,−.001731]；D−H的ΔU=.001420，区间[.000960,.001895]。后两者区间虽未跨零，也只属于已曝光人口、固定策略和成本重组的探索描述；不据此挑配置、挑赢家或确认H2。其余9组×3指标完整列在summary/paired_bootstrap.csv（共9组，不是另加9组）。

本次支持查询级排序信号和一个能省费的冻结工作点，不能证明分歧监督胜过gold监督，也没有把“未拒绝H2”等价于“H2成立”。没有执行正式独立H1/H2确认性检验。

## 事后两答案诊断与历史参照

cal若事后仅在o_R=o_T时走R，可覆盖1223/1366=89.53%；dev可覆盖670/742=90.30%，保留645正确、0解析改变。dev被选动作组件平均323.489ms，比Text少652.275ms。它先看两条在线不可同时免费获得的答案，所报组件不计获得两答案的费，因而只是本人口、这两个动作的机会空间，不可部署、不是一般路由上界。cal的623.329ms节省仅由旧动作均值估计。

旧端到端表保持原身份，只复用冻结记录，不重拟合、不重跑、不用本轮分数替换旧阈值：

'''
hist=list(csv.DictReader((E/'summary/main_results.csv').open()));hist=[r for r in hist if r['path'] in ['FFR_E1','FFR_E1_D','IndepLR_E1']];csvout(P/'summary/historical_e2e_reference.csv',hist)
md+=table(['旧路径','正确','mean完整请求ms','median ms','p95 ms','U','动作组成'],[[r['path'],r['correct_or_expected_correct'],num(r['mean_latency_ms']),num(r['median_latency_ms']),num(r['p95_latency_ms']),num(r['U'],6),'185R/528T/29A' if r['path']=='IndepLR_E1' else '83R/659T' if r['path']=='FFR_E1' else '90R/652T'] for r in hist])
md+='''
旧头用了全3466 train及不同的监督/选择规则，新头只用2100 fit；该历史参照不是控制变量一致比较。旧FFR/FFR-D省Text的83/90题解析答案均相同，仍保持645/742。5.87%/27.8%是旧均值的一阶估算，分别谈特征费盈亏与匹配IndepLR平均节时，均不保证部署或效用优势。全部审议修订与来源见ERRATA_ZH.md。

## 标签账与资源账

'''
label=list(csv.DictReader((P/'summary/label_ledger.csv').open()))
md+=table(['族','算法fit唯一gold','衍生动作正确性值','harm目标','fit机器d','cal机器d','cal gold','本轮新增人工'],[[r['family'],r['algorithm_fit_unique_gold_questions'],r['derived_action_correctness_values'],r['harm_training_targets'],r['machine_disagreement_fit_labels'],r['machine_disagreement_cal_labels'],r['cal_gold_required'],r['new_human_annotations_this_round']] for r in label])
md+='''
correctness两头共用2100题gold，不能计为4200人工标注；harm也共用这批gold，4200衍生动作正确性值与2100harm目标不是新增人工答案。基线间共享标签不累计收费。候选fit/cal共3466机器d、0 gold；仍需两动作的历史输出。所有方法cal只用1366个d、不用cal gold；dev742个gold均在路由冻结后评价。历史6932协议请求登记为复用，不能等同LLM前向次数。整个研究设计曾接触gold，本轮所有方法新增人工标注都是0。

'''
md+=table(['完成/资源项目','实际'],[['四个新头 / 拟合尝试','4 / 4，均收敛'],['校准项 / 预定部署点','100 / 5（3选择性、2固定Text）'],['dev完成 / prefill尝试 / 成功 / 缓存复用','742 / 742 / 742 / 0'],['新helper forward / 答案生成 / 新协议请求','0 / 0 / 0'],['唯一PBS',res['job_id']+'，F/0'],['申请', 'gpu-queue select=1，00:30:00，0.5 GPU allocation hour'],['实际分配（stime→obittime）',f"{res['actual_allocation_seconds_stime_to_obittime']:.0f}s = {res['actual_GPU_allocation_hours_stime_to_obittime']:.6f} GPU allocation hour"],['scheduler walltime',f"{res['scheduler_walltime_seconds']}s（另一计量口径）"],['prefill CUDA event',f"{comp['new_prefill_CUDA_event_seconds']:.6f}s，非纯kernel总时"],['监督进程累计CPU',f"{res['CPU_supervised_seconds']:.6f}s"],['CPU保守计账 / 上限',f"{res['CPU_charged_with_60s_preparation_reporting_reserve']:.6f}s / 1200s（含60s准备报告预留）"],['PBS cput / mem',f"{res['CPU_scheduler_seconds_separate_not_additive']}s / {res['resource_used_mem']}；不与进程CPU重复加总"],['sbank真实收费','NA：短/完整job id均未查到条目，非零费用'],['TeX','PATH无编译器；英文源文件已交付，未编译']])
md+='''
A阶段GPU计算为0也占用GPU分配区间。CPU/BLAS均单线程、进程固定单核；资源账含模型加载、定向检查和全部诊断。申请按GPU小时而非整节点小时；实际收费未获得设施可解释条目，保留原查询。ClusterB队列含义见[官方指南](https://docs.cluster.invalid/ClusterB/queueing-and-running-jobs/running-jobs/)。未提交第二作业、未延长walltime、未借旧余额。科学执行已完成；工程剩余限制只有TeX未编译和设施收费暂NA，不把它们当科学失败。

## 冻结链和交付

SPLIT_FREEZE → PROTOCOL_FREEZE/IMPLEMENTATION_FREEZE → RANDOM_FREEZE/TARGET_INTERFACE_FREEZE → THRESHOLDS_FREEZE → DEPLOYMENT_FREEZE → DEV_FEATURES_COMPLETE → DEV_ROUTES_FREEZE → ANALYSIS_COMPLETE/FIGURES_COMPLETE。路径、日期与SHA256均留在回执，阈值/随机流/部署先于相应结果读取。SHA256SUMS提供交付文件清单。

- 中文：本报告、REPORT_TABLES_ZH.md、HANDOFF_ZH.md、ERRATA_ZH.md。
- 英文：paper/13–15方法、协议/限制和结果片段，表格、BibTeX、fragments_preview.tex；figures/风险—覆盖PNG/PDF。
- 模型/数据：四个joblib头、MODEL_INDEX、划分、阈值/接受集合/随机流、逐题分数/路由/重组指标、100项完整校准和全部预定q曲线。
- 可追溯性：源码、SOURCE_INDEX、资源/数值/可视化回执、作业日志、冻结哈希。
- Work轻量包不含大模型checkpoint或全量历史资产；新dev z留ClusterB的features/dev，包内保留DEV_FEATURE_INDEX.csv及SHA256。不要从换会话重新提取成功id或恢复本轮已关闭预算。

本轮停止，交回Work；不自动扩展四动作、改校准器或启动下一实验。
'''
(P/'P2_RISK_CALIBRATION_BINARY_REPORT_ZH.md').write_text(md)
# Full frozen policy population tables, including invalid composition.
r=list(csv.DictReader((P/'summary/deployment_all_populations.csv').open()));out='# 冻结策略完整人口附表\n\n原始未舍入数据：summary/deployment_all_populations.csv。只有dev成本是新特征计时加历史完整请求重组；fit/cal正确性均为冻结部署后的描述，不用于选择。\n\n'
for split in ['fit','cal','dev']:
 rr=[x for x in r if x['split']==split];out+=f'## {split}\n\n'+table(['族','n/N','k/n','k/N','获益/伤害/中性','正确','Δacc(pp)','输出INVALID','路由双/仅R/仅T INVALID','cal p','cal校正CP上界'],[[x['family'],f"{x['n_R']}/{x['N']}",f"{x['changed']}/{x['n_R']}" if int(x['n_R']) else 'NA',f"{x['changed']}/{x['N']}",f"{x['benefit']}/{x['harm']}/{x['neutral_change']}",x['correct'],num(float(x['accuracy_diff_Text'])*100,4),x['INVALID_selected'],f"{x['routed_both_INVALID']}/{x['routed_R_only_INVALID']}/{x['routed_Text_only_INVALID']}",num(x['calibration_p_value'],9),num(x['calibration_CP_upper_0_999'],6)] for x in rr])+'\n'
out+='固定Text/回退的空路由边界约定p=1、CP上界1；表中NA表示没有选中校准检验项，不声称接受。固定R只作描述参照，其同一策略在预定网格q=1已计入原M=100，不增加搜索。\n'
(P/'REPORT_TABLES_ZH.md').write_text(out)
print('中文主报告及完整人口表已从冻结结果生成。')
