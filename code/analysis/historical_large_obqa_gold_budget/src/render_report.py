from common import *
rows=list(csv.DictReader((P/'summary/main_new15.csv').open()));rows.sort(key=lambda r:(int(r['B']),int(r['repeat'])))
summ=list(csv.DictReader((P/'summary/budget_summary.csv').open()));pol=read(P/'models/deployment.json');ledger=read(P/'summary/experiment_ledger.json');resource=read(P/'RESOURCE_RECEIPT.json');paired=list(csv.DictReader((P/'summary/bootstrap_B128_vs_D.csv').open()))
def n(v,d=3):return f'{float(v):.{d}f}' if v not in ['',None] else 'NA'
def pc(v,d=2):return n(float(v)*100,d)+'%' if v not in ['',None] else 'NA'
def yn(v):return '是' if v is True or v=='True' else '否'
def tab(head,rr):return '| '+' | '.join(head)+' |\n| '+' | '.join(['---']*len(head))+' |\n'+''.join('| '+' | '.join(map(str,r))+' |\n' for r in rr)
def span(r,f,d=6):return f"{n(r[f+'_median'],d)} [{n(r[f+'_min'],d)}, {n(r[f+'_max'],d)}]"
md='''# P2_GOLD_BUDGET_CROSSOVER 中文主报告

**COMPLETE，停止并交回 Work。少量 gold 在部分子集已能追平；主预算128 gold并未在多数重复中追平。** 128的两项预定标记都仅r=0满足（1/5），其余四个重复效用低于D。32的效用追平2/5、成本—准确率同时追平1/5；512分别3/5、2/5。因此不能从旧对照用了2100 gold推成它需要2100才能追平，也不能声称128 gold已稳定消除候选的性能空间。

**候选保留的独立价值是无需正确性标签即可得到有用的参考保持门控；不是独有的排序信号、已确立的少样本优势或更低的总体采集费。** 在本固定模型、三个预算和五个标签子集下，D的U高于四个128配置，但32和128均已有追平例子，512多数重复达到效用标记。D需要更多fit机器协议输出：6932次请求对一个R128配置2860次，特征人口同为3466题。这削弱“普通方法需接近全量gold才可竞争”和“0 gold等于总体更便宜”的叙事；不建立普遍标签复杂度，也不说明其他普通方法必需更多gold。

## 主结果与追平定义

本轮严格区分两个预定描述标记：

1. 效用追平：cal返回选择性工作点，dev条件改变率点估计≤.05，且U≥D的原冻结U（内部比较用原值.8362042446443797，非展示舍入值）。
2. 成本—准确率同时追平：相同cal/dev风险条件，正确数≥643且组件重组mean≤797.166236ms。

两个标记都不是显著性、非劣或等价检验，不是新部署选择规则。回退Text不满足标记；无R路由时条件风险NA，边际改变为0。各预算均报告全部五次，未选最佳r或最有利预算。

'''
md+=tab(['B','cal选择性/5','效用追平/5','成本—准确率追平/5','ΔU_D 中位数 [最小,最大]','U 中位数 [最小,最大]'],[[r['B'],r['selective_accepted_count'],r['utility_crossover_count'],r['cost_accuracy_crossover_count'],span(r,'delta_U_D'),span(r,'U')] for r in summ])
md+='''
这些极差是五个标签子集的观察范围，不是95%置信区间，也不是五个独立实验。32是出现追平的最小**已测**预算，但只在2/5次满足效用、1/5次同时满足成本—准确率；不能称32是最低所需gold。预算增加时个别重复表现并不单调，不能只截取有利一段。

下表是15个完整固定配置。**全部成本均为历史组件重组代理，不是新增端到端测量**；新头费用复用原correctness-R同结构逐题head/selector代理。

'''
md+=tab(['B/r','q（0=Text）','dev R/742','改变k/n','获益/伤害/中性','正确','mean ms','median ms','p95 ms','净省Text ms','U','ΔU_D','效用/成本准确率追平'],[[f"{r['B']}/{r['repeat']}",n(r['cal_q'],2),r['n_R'],f"{r['changed']}/{r['n_R']} ({pc(r['conditional_risk'])})" if int(r['n_R']) else 'NA',f"{r['benefit']}/{r['harm']}/{r['neutral_change']}",r['correct'],n(r['mean_cost_ms']),n(r['median_cost_ms']),n(r['p95_cost_ms']),n(r['net_saving_Text_ms']),n(r['U'],6),n(r['delta_U_D'],6),yn(r['utility_crossover'])+'/'+yn(r['cost_accuracy_crossover'])] for r in rows])
md+='''
主预算128的r0保持D的643正确、条件改变6/265，比D少32.170ms、ΔU=+.001226；r1未接受并回退Text；r2/r4分别因节省不足未达到效用标记；r3有640正确，虽然条件改变点估计3.139%仍在5%以内，准确率损失使ΔU为−.004263。解析改变约束只给总体期望准确率差的保守关系，不保证这742题的实际正确数。

32/r1有646正确、比D多3题，虽然更慢仍满足效用标记，不能称其成本—准确率同时追平。512/r2也因比D多1题而满足效用，均值815.235ms却高于D，故不满足第二标记。这两例说明两种“追平”不能混写。512的五个U为.837683/.834259/.836864/.838556/.835610，效用追平r0/r2/r3、成本—准确率追平r0/r3。所有新配置的观测U均低于冻结R2100的.839727，但这不是新定义的检验标记。

'''
md+=tab(['B','覆盖率中位数[最小,最大]','正确数中位数[最小,最大]','mean ms中位数[最小,最大]','有条件风险值的重复数'],[[r['B'],span(r,'coverage',4),span(r,'correct',0),span(r,'mean_cost_ms',3),r['conditional_risk_non_NA']] for r in summ])
md+='''
每个指标的中位数分别计算，不拼成虚构的“中位部署策略”。summary/budget_summary.csv还提供全部预定指标的中位数、最小、最大及非NA数量。

![所有五次标签子集的预算曲线](figures/gold_budget_crossover.png)

图中蓝/橙/绿/粉/棕分别为r0/r1/r2/r3/r4；同色细线连接同一r的嵌套预算，黑粗线为各预算中位数，空点表示cal回退Text。相同值可能重叠，表中仍保留全部重复。图线不是置信区间，也不据图选择新点。

## 固定参照、标签子集和拟合隔离

D/R2100/Text参照完全承接父实验，不重新拟合、评分、计时或改阈值：D是q=.30、cal6/380、dev230路由/6改变/643正确、797.166236ms、U=.836204245；R2100是q=.40、cal11/523、dev291路由/7改变/644正确、740.087265ms、U=.839726701；Text645正确、975.763976ms、U=.832094967。固定R为617正确、72/742改变、252.089194ms、U=.821931619，仅作描述参照。

Work已提供D与u_R的Spearman .986981520，R路由交集228、仅D2、仅R2100为63；正确性相同741题、R2100独胜1题。本轮仅引用这项事后描述，没有另开审计或将其写成监督等价证明。

原fit/cal/dev=2100/1366/742、规范化重复组定义和原身份不变；未重新划分、评分或读取ARC test。train/dev E1 8192维z全部复用，原checkpoint、prompt、BF16/SDPA、层25和final norm、FP32归一化定义不变，没有任何backbone/tokenizer加载。

每个r独立random.Random(r)打乱按完整id字典序排序的原fit2100题，取嵌套前32/128/512题。子集随机种子为0..4，LR种子始终0。未按gold分层、补齐类别、重抽seed或更换子集。新头仅接收自己B题的id/z/y_R；没有其余fit的y_R/y_T/d、cal正确性、旧头软标签或初始化。拟合后，完整fit2100题仅以无标签z作各新头共同的阈值参考池。每个head L2 LR(C=1,lbfgs,max_iter=1000,class_weight=None)，不额外标准化、调参。实际15次LR拟合、15次尝试，全部收敛，无警告、无constant fallback。

**准备时序偏差须保留：** 为核对旧标签接口，子集文件落盘前预览了旧baseline_fit的两行样例（14-1371、14-97，各y_R=1；显示中也带有旧y_T/harm字段）。随机规则此前已由用户完整指定，没有因预览改seed、排序或列表。15个正式标签接口及类别统计均在SUBSETS_FREEZE之后生成。事后成员记录显示两行均未进入任何B32或B128子集，只分布在部分B512子集中；不能据此删除或重采。本轮不能声称完美的清单物化前标签盲化，这一偏差不隐瞒。见evidence/PREPARATION_DEVIATION.json及preview_membership.json。

## 校准强度及全部部署选择

所有头先冻结，再以完整fit2100得分取20个q=.05,.10,…,1阈值：q<1用inverse empirical CDF的第ceil(q*2100)值，u≤阈值走R且并列整体纳入；q=1为+∞、严格固定R。所有阈值先于新cal选择冻结，所有cal选择先于dev路由冻结，dev路由先于答案/gold及费用关联。没有显著性放行或最低覆盖门槛，15配置全部评价。

每个重复内五族{D,R2100,R32_r,R128_r,R512_r}×20=100项，固定alpha=.05、delta=.10、M=100、p≤.001。复用原二项p=BinomialCDF(k;n,.05)及单侧CP上界BetaQuantile(.999;k+1,n−k)，n=0时p=1，上界在n=0或k=n时置1。最大已接受q部署；否则固定Text。没有插值、未接受阈值、放宽alpha或缩小M。D/R2100的40条检验引用旧记录且结果不变，300条新检验，340个不同模型—网格项；五张100行表的500行只是共享40参照的比较视图，不是500次新检验。

'''
md+=tab(['配置','fit正/误','模型','全部接受q','部署q','cal k/n','p','校正CP上界'],[[r['name'],r['fit_correct']+'/'+r['fit_incorrect'],'LR/收敛',','.join(n(q,2) for q in pol[r['name']]['accepted_q']) or '无',n(r['cal_q'],2),r['cal_changed']+'/'+r['cal_n_R'] if int(r['cal_n_R']) else 'NA（Text）',n(r['cal_p_value'],9),n(r['cal_CP_upper_0_999'],6)] for r in rows])
md+='''
Text回退的p=1、CP=1是空路由约定，没有任何被接受的检验项；其条件风险仍为NA。所有cal网格点和接受标记见summary/calibration_new_300.csv，五个重复视图见comparisons/r0_100.csv至r4_100.csv，40项参照见shared_reference_40.csv。

在独立fit/固定策略族及iid校准—未来请求假设下，FWER≤.10只针对每个重复内100项。五次重复共用cal、嵌套及重叠gold/特征，并非彼此独立，也不是一个总体FWER=.10的联合搜索。不能从dev或重复间挑一个模型后继承全局保证。历史train/cal/dev曝光仍在，本轮不产生新的独立确认集或部署证书。继承LTT、二元FFR阈值族与E1特征均不称本轮贡献。

## 排序、校准功效与同覆盖率

'''
md+=tab(['配置','cal AUROC(d)','dev AUROC(d)','dev AP(d)','dev Spearman(D)','条件风险','边际改变'],[[r['name'],n(r['cal_AUROC_disagreement'],6),n(r['dev_AUROC_disagreement'],6),n(r['dev_AP_disagreement'],6),n(r['dev_Spearman_D'],6),pc(r['conditional_risk'],3),f"{r['changed']}/742 ({pc(r['marginal_change'],3)})"] for r in rows])
md+='''
AP同一目标d的dev基率参照为72/742=.097035。三预算Spearman(D)中位数分别.844413/.941417/.982409，AUROC中位数.715962/.744548/.759287；B512的分数排序已接近D，但校准阈值和少数获益/伤害仍造成效用差。不能将高相关度直接写成相同决策或监督等价。

在固定D覆盖n=230时，B128五个新分数的前230题改变数为6/7/6/7/7（D=6，R2100=5）；对应风险为2.609%/3.043%/2.609%/3.043%/3.043%。统一随机子集期望22.318，超几何描述95%范围15–30。该排序仅描述同覆盖率，按冻结dev顺序稳定破并列，没有把排名前n改成新部署点。其余预算以及各新部署覆盖和R2100覆盖的比较全部在summary/coverage_matched.csv。

三个回退具有不同可观察迹象：

- R128/r1的cal AUROC=.754461、dev=.736443，仍有排序信号；最有利的cal点2/211，经验风险.948%，但p=.001464971、CP上界5.2068%未过固定门槛，零改变子集最多65题。这呈现校正余量/样本功效不足，不能归因于完全无信号。
- R32/r2的cal/dev AUROC=.702983/.723051；最小p=.055793来自4/177，上界8.107%。存在预测信号，但预设低风险子集在这批cal上不足以通过严格检验。
- R32/r4排序较弱（cal/dev AUROC=.619124/.598735），又只有最多71题零改变；最小p=.019345来自1/115，上界7.7478%。排序弱与低风险样本不足同时可见，不能仅凭这次结果唯一归因。

各模型类别比例与题目组成未人为修正。当前观察无法把标签抽样、排序变化、阈值离散性和校准样本波动完全拆开，也不把不接受等同于没有信号。

## 主预算的配对描述区间

B128五头对D使用同一份seed0、2000次逐题联合bootstrap索引，只运行一次。固定子集、模型和阈值；这些95%百分位区间仅描述条件于模型的题目抽样，不覆盖标签子集抽样不确定性。32/512未另做bootstrap搜索。

'''
md+=tab(['128重复','Δaccuracy [描述95%区间]','Δmean ms [描述95%区间]','ΔU [描述95%区间]'],[[str(rep)]+[f"{n(r['difference'],6 if metric!='mean_cost_ms' else 3)} [{n(r['CI95_descriptive_low'],6 if metric!='mean_cost_ms' else 3)}, {n(r['CI95_descriptive_high'],6 if metric!='mean_cost_ms' else 3)}]" for metric in ['accuracy','mean_cost_ms','U'] for r in paired if int(r['repeat'])==rep and r['metric']==metric] for rep in range(5)])
md+='''
r0的ΔU区间不跨零也不授权选它作新的全局部署模型；其他r完整保留。主预算ΔU中位−.000548575、范围[−.004262678,+.001225704]表示子集敏感性，不是非劣/等价结论。逐题对D及R2100的accuracy、cost、U差值均在records/dev_per_question_new.jsonl。

## 在线费用与独立学习流程所需监督/采集

新策略费用=原每题feature_ms + 原correctness-R每题head/selector_ms + 所选旧固定R/Text完整请求。各选择性策略每题支付完整E1费，固定R/Text删除无须执行的特征/头。D保持原自身head费用，R2100保持原成本结果；没有新计时或免费共享在线特征。固定lambda=.01、c_ref=262.462515ms，U=accuracy−.01*mean_cost/c_ref。

复用的R头费用平均.099911ms，D为.117592ms，差.017681ms。将新头代理统一替换为D自己的逐题head时间后，没有任何已满足的追平标记消失（计时敏感标记0/15）。不把此微小差异当方法优势，也未扩展性能工程。

'''
algo=list(csv.DictReader((P/'summary/algorithm_label_cost_ledger.csv').open()))
md+=tab(['独立学习流程','唯一fit gold / y_R目标','fit机器d','cal机器d','fit R/Text请求','cal R/Text请求','总协议请求','协议时间估计(s)','offline z人口/旧实测(s)'],[[r['method'],r['algorithm_unique_fit_gold']+'/'+r['derived_y_R_targets'],r['machine_fit_d'],r['machine_cal_d'],r['fit_R_requests']+'/'+r['fit_Text_requests'],r['cal_R_requests']+'/'+r['cal_Text_requests'],r['total_protocol_requests_needed'],n(r['protocol_seconds_estimated_from_old_train_means']),f"{r['offline_z_count']} / {n(r['offline_feature_wall_seconds_reused'])}"] for r in algo])
md+='''
D fit需要2100对R/Text输出生成d；R_B只需要B个R输出和B个gold衍生y_R，不需要fit Text输出。两者cal都需要1366对R/Text生成d且不需要cal gold。所有头仍使用完整2100题无标签fit参考池和1366题cal的z，所以离线特征费不随B缩成B题。

协议秒数由原冻结256题train均值R=262.462514903ms、Text=958.674393707ms估算，不是全train逐题新测量；feature秒数来自原每题实测meta。R128预计1701.668s协议时间对D4232.461s，另同有139.444s离线E1，说明无需gold不等于更低总体采集成本。此处不假设人工标注价格、也不虚构实际省钱。所有结果仍受原两GPU完整请求与另一时点特征测量的组件相加限制，不能替代端到端测量。

单配置需求、实验并集与实际新增严格分列：15配置共有3360个标签位置，但唯一gold id并集1579；B32/B128/B512跨五次的并集分别159/566/1579，重复间标签重叠不重复收费。新头实验逻辑复用1579个fit R请求及2732个cal请求，共4311个唯一题—动作请求；代码直接消费已存y_R及d而不重执行这些协议。若将D/R2100原学习流程纳入历史支持，D已有6932请求可覆盖其所需题—动作，不能再累加成新执行账。包括冻结R2100的全实验已存在gold支持为2100唯一fit题，新15头实际训练标签并集仍是1579。

实际复用3466条train z、742条dev z（dev特征历史29.742794s），实际新增人工标注0、新协议请求0、新特征0。请求数不等于LLM forward次数。本轮新增计算是15头拟合/矩阵评分/校准/分析的CPU，总账如下。

## 执行、资源、可追溯性

'''
md+=tab(['项目','实际'],[['新模型/拟合尝试/收敛/常数fallback','15/15/15/0'],['新cal/共享旧cal/不同模型—网格项','300/40/340；五张100项视图'],['新dev策略题评价','15×742=11130，全部完成'],['GPU计算/backbone或tokenizer加载/prefill/helper/生成','全部0'],['本轮唯一作业',resource['job_id']+'，F/0'],['申请','gpu-queue select1，600秒=1/6 GPU allocation hour'],['实际GPU分配',f"{n(resource['actual_allocation_seconds_stime_to_obittime'],0)}秒={n(resource['actual_GPU_allocation_hours'],6)} GPU allocation hour"],['scheduler walltime',str(resource['scheduler_walltime_seconds'])+'秒（单独口径）'],['CPU监督进程实际',n(resource['CPU_supervised_seconds'],6)+'秒'],['CPU保守计账/上限',f"{n(resource['CPU_charged_seconds'],6)}/300秒，含30秒准备/报告预留"],['PBS cput / mem',str(resource['CPU_scheduler_seconds_not_additive'])+'秒 / '+resource['scheduler_memory']+'，不与进程CPU重复加总'],['设施收费','sbank短/完整job id均未找到，NA，非0收费'],['TeX','无可用编译器；英文源检查、图表已渲染，未编译']])
md+='''
GPU计算为0也占用所申请的GPU分配区间。CPU/BLAS单线程并限制单核，预算覆盖拟合、评分、校准、bootstrap及预留；没有第二作业、没有读取或恢复185721旧预算。所有结果正常完成，没有工程阻塞伪装成科学结论；准备预览偏差已单独披露。

冻结链：SUBSETS_FREEZE → LABEL_INTERFACES_FREEZE → MODELS_FREEZE → THRESHOLDS_FREEZE → DEPLOYMENT_FREEZE → DEV_ROUTES_FREEZE → ANALYSIS_COMPLETE/FIGURES_COMPLETE。配置、源码和输入身份在PROTOCOL/IMPLEMENTATION/SOURCE_INDEX中；原父目录来源哈希保持不变。

- 本报告、HANDOFF_ZH.md、REPORT_TABLES_ZH.md；英文paper/16–17与表格、预算图PDF/PNG。
- 15子集清单、15个LR模型、输入标签接口、阈值/接受集合/部署回执、300新检验、5张比较视图、逐题预测/风险/费用/对照差值。
- summary/包含全量结果、每预算中位/最小/最大、排序与同覆盖、主预算bootstrap、标签/采集/资源账。
- 所有z留原ClusterB路径；inputs/TRAIN_FEATURE_INDEX.csv与DEV_FEATURE_INDEX.csv给路径及哈希。轻量包不重复z、大模型或整个旧实验。
- SHA256SUMS和FINAL/DELIVERY_RECEIPT供核验；P2_STATE只追加本轮完成与论文结论。

完成后停止交回Work。是否继续候选、转为基线/机制分析及下一论文任务由Work决定；不自动新增预算点、seed、模型、动作或数据集。
'''
(P/'P2_GOLD_BUDGET_CROSSOVER_REPORT_ZH.md').write_text(md)
# A compact machine-linked appendix covers all required columns without truncation.
appendix='# P2 gold预算完整附表\n\n原始精度以summary/main_new15.csv为准；所有费用为历史组件重组代理。\n\n'
appendix+=tab(['配置','dev AP','边际改变','相对D Δacc','相对R2100 Δacc','相对D Δms','相对R2100 Δms','相对R2100 ΔU','净省比例','INVALID'],[[r['name'],n(r['dev_AP_disagreement'],6),pc(r['marginal_change'],4),n(r['delta_accuracy_D'],6),n(r['delta_accuracy_R2100'],6),n(r['delta_cost_D_ms']),n(r['delta_cost_R2100_ms']),n(r['delta_U_R2100'],6),pc(r['net_saving_Text_fraction']),r['INVALID']] for r in rows])
appendix+='\n每预算统计：各指标单独取中位数、最小值、最大值；不是组合成一个策略，不是95%区间。条件风险只对非NA配置汇总。\n\n'
for s in summ:
 appendix+=f"## B={s['B']}\n\n"+tab(['指标','中位数','最小值','最大值','非NA重复'],[[f,n(s[f+'_median'],6),n(s[f+'_min'],6),n(s[f+'_max'],6),s[f+'_non_NA']] for f in ['cal_q','n_R','coverage','changed','conditional_risk','correct','accuracy','mean_cost_ms','median_cost_ms','p95_cost_ms','net_saving_Text_ms','U','delta_U_D','delta_U_R2100','delta_accuracy_D','delta_cost_D_ms','dev_AUROC_disagreement','dev_AP_disagreement','dev_Spearman_D']])+'\n'
(P/'REPORT_TABLES_ZH.md').write_text(appendix)
print('中文报告及全指标附表已生成。')
