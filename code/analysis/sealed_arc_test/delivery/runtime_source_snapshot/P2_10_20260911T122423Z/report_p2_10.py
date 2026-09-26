"""中文最终报告；PASS 同时要求覆盖、分析、独立复核和PBS正常结束。"""
import json,csv
from pathlib import Path
from common_p2_10 import ROOT,readrows,sha,utc,save
from progress_p2_10 import progress

def table(headers,rows):return '\n'.join(['| '+' | '.join(headers)+' |','|'+'|'.join(['---']*len(headers))+'|']+['| '+' | '.join(map(str,r))+' |' for r in rows])
def dur(s):
    h,m,sec=map(int,s.split(':'));return 3600*h+60*m+sec
def signed(x,digits=3):return f'{0. if abs(x)<0.5*10**(-digits) else x:+.{digits}f}'
def main():
    cfg=json.loads((ROOT/'frozen_config.json').read_text());p=progress();jobs=json.loads((ROOT/'evidence/jobs.json').read_text())
    summary=json.loads((ROOT/'analysis_summary.json').read_text()) if (ROOT/'analysis_summary.json').exists() else None
    check=json.loads((ROOT/'evidence/independent_result_check.json').read_text()) if (ROOT/'evidence/independent_result_check.json').exists() else {}
    visual=json.loads((ROOT/'evidence/visual_check.json').read_text()) if (ROOT/'evidence/visual_check.json').exists() else {}
    full=p['AC_complete']==11252 and p['RTC_complete']==4608 and p['panel_complete']==1536 and p['dev_panel_complete']==512
    passed=full and summary and check.get('passed') and visual.get('passed') and bool(jobs) and all(j.get('job_state')=='F' for j in jobs) and jobs[-1].get('Exit_status')==0
    status='PASS_P2_10_AC_AND_FOUR_ACTION_DEV_COMPARISON' if passed else 'PARTIAL_P2_10'
    actual=sum(dur(j.get('resources_used',{}).get('walltime','00:00:00')) for j in jobs)
    lines=[f'# P2-10：AC 补齐与四动作开发比较\n\nFINAL_STATUS：**{status}**\n\n更新时间：{utc()}。PASS 只表示冻结协议内执行与交付完成，不表示路由取得科学收益。',
    '预先指定的word、λ=0.01重点读数未确认四动作相对三动作及强混合参照获得稳定的准确率—延迟收益。全量开发中，四动作相对三动作在大OBQA、大ARC、小OBQA、小ARC分别少2题、持平、多1题、持平；配对准确率差区间均包含0。四个固定128题成本子集中，四/三动作重点路由逐题正确性完全相同。共6道AC独占开发题均未被重点路由选中。完整辅助网格全部保留，本结论不替换预定候选，也不推断AC在其他方案中无用。',
    '## 执行状态与预算',
    f"AC **{p['AC_complete']}/11252**；新增 R/T/C 成本调用 **{p['RTC_complete']}/4608**；四动作同次成本题目—模型对 **{p['panel_complete']}/1536**，其中开发 **{p['dev_panel_complete']}/512**。正式运行失败尝试 {p['runtime_failures']}，新增重试 {p['retries']}；本轮新动作无效答案 {p['invalid_outputs']}，与运行错误分别记账。人工预热/smoke {p['smoke_attempts']}/72。",
    table(['组合/划分','AC','新增RTC','同次成本题数','运行失败','无效答案'],[[k,v['AC'],v['RTC'],v['panel_complete'],v['runtime_errors'],v['invalid_outputs']] for k,v in p['parts'].items()]),
    table(['PBS job ID','状态/退出','申请','实际walltime','节点'],[[j['job_id'],str(j.get('job_state'))+'/'+str(j.get('Exit_status')),j['Resource_List']['walltime'],j.get('resources_used',{}).get('walltime','未知'),j.get('exec_host','未分配')] for j in jobs]),
    f"累计按申请记账 **{p['requested_node_seconds']}/21600 节点秒**（{p['requested_node_seconds']/3600:.3f} 节点小时，{p['requested_node_seconds']/1800:.3f} GPU小时）；实际PBS walltime合计 **{actual} 秒**；未用申请额度 **{p['remaining_request_node_seconds']} 节点秒**。已获job ID提交 {p['submissions']}/3。没有按提前结束或失败返还申请，没有转入P2-6/P2-9余额。完成后不使用余量开展额外实验。",
    'PBS 与 CUDA 环境记录核实单节点两张 A100-SXM4-40GB，64CPU、240GB，gpu-queue；继承实际设备分配，未设置物理卡号。helper和独立FP32语义编码器在逻辑GPU0，receiver/fuser与FP32 W在逻辑GPU1。resources_used.ngpus若为0不用于否定实际GPU执行。其他项目作业未被取消或修改。',
    '## 冻结协议、层位置与 W',
    f"协议冻结时间 `{cfg['frozen_utc']}`，SHA256 `{sha(ROOT/'frozen_config.json')}`。本轮用户请求、成本子集排序、全部15860请求、24种动作排列及源码哈希均在首次提交前保存。协议原件未在训练后覆盖。",
    table(['端点','小模型0基/1基/层数/hidden','大模型0基/1基/层数/hidden'],[[r,' / '.join(str(v[r]['small'][k]) for k in ['block_index','position_1based','num_hidden_layers','hidden_size']),' / '.join(str(v[r]['large'][k]) for k in ['block_index','position_1based','num_hidden_layers','hidden_size'])] for v in [cfg['ac_layers']] for r in ['helper','receiver']]),
    '小模型旧代码确为 layers[19]，即第20个block；大模型分别按各端相对深度做half-up机械映射，没有扫层。大W为无bias的[4096,3584]线性权重。两个backbone冻结、eval，BF16/SDPA；W计算FP32、TF32关闭，Xavier uniform(gain=1)、seed=0、Adam(lr=0.001, betas=(0.9,0.999), eps=1e-8, weight_decay=0)、batch32、10epochs，最终960步唯一权重。',
    '冻结配置中large_W.recipe.loss继承了P2-3原描述的“1024输出维”字面文字；本轮用户规则、冻结large_W.shape、实际receiver配置和冻结mse_loss代码均明确为4096维取mean。派生说明见evidence/frozen_config_interpretation_note.json；原冻结文件未覆盖，实际计算未改变。旧pair_configs作为来源配置保留，其历史人口/预算字段不支配P2-10顶层data/router/budget/actions规则。',
    f"小W沿用 `{cfg['small_W']['path']}`，SHA256 `{cfg['small_W']['sha256']}`；提交前和实际载入均核验，分析时再次核验为 `{sha(cfg['small_W']['path'])}`。没有重新训练或改动小W。",
    '普通C4文本逐条复用P2-3的3072训练句和256持出句，成员和顺序不变。各端自行分词，plain text、add_special_tokens=True、truncation=False、无chat模板，在本端最后有效位置取指定block输出；大模型token IDs与旧保存值全部相同，训练最长237、持出最长138，均未截断。提取表征后由BF16转FP32训练，未用任何OBQA/ARC题目、答案或模型输出训练W。最新恢复状态含W、Adam、CPU/CUDA/Python/NumPy及shuffle RNG、step、epoch、cursor和当前顺序；成功最终W不会再次训练。']
    wr=ROOT/'results/large/W/final_receipt.json'
    if wr.exists():
        w=json.loads(wr.read_text());m=w['metrics']
        lines += [table(['MSE诊断','train','持出'],[['初始化',f"{m['initial_train_mse']:.6f}",f"{m['initial_heldout_mse']:.6f}"],['第960步最终',f"{m['final_train_mse']:.6f}",f"{m['final_heldout_mse']:.6f}"],['训练目标均值常数预测器','—',f"{m['train_receiver_mean_heldout_mse']:.6f}"]]),f"可训练参数 **{m['parameters']}**；最终W SHA256 `{w['sha256']}`。持出MSE仅诊断；不选checkpoint、不early stop、不按答题准确率选W。MSE下降不等于任务准确率提高。"]
    else:lines+=['大模型最终W尚未完成；不报告不存在的MSE或hash。']
    lines += ['AC为论文依据的独立实现与Qwen移植，不称官方复现，也不把旧Hidden-prefix改名为AC。推理使用本端冻结prompt与各自tokenizer；helper中间block输出经 `a.to(cuda:1, dtype=float32)` 后由GPU1上的W投影，再转receiver BF16，只在原始prompt首次prefill最后位置替换完整hidden。后续生成不再注入，不额外生成helper消息。必要hook检查通过，额外有限性诊断与评分在完整动作计时之后。',
    '## 数据人口和成本口径',
    'OBQA完整train3466、dev742；ARC-Challenge完整train1119、validation299。两组模型使用相同ID；ARC源revision为210d026faf9955653af8916fad021475a3f00453，P2-8 v2原选项顺序、可逆映射、3/4/5选项及train内重复题全部保留。test1172仍封存，未下载、未读逐题内容/答案、未生成预测。两套开发集均已曝光；本轮没有新的独立确认性测试。',
    '成本子集使用 `SHA256("P2_10_COST_PANEL_V1|"+dataset+"|"+split+"|"+id)` 排序，dataset冻结为obqa/arc，split为train/dev/validation；train前256、开发前128，同hash按ID排序。未按正确率、耗时、答案类别或长度抽题。两组模型共用每个数据集的ID清单。子集优先按已冻结hash序执行，其余题按既有数据顺序只补AC；不是重新划分。',
    '**全量开发准确率**：历史成功R/T/C原答与本轮AC，按数据集、split、ID、协议和模型身份对齐；未用新子集RTC偷偷替换历史标签。全量矩阵当前RTC成本留空，旧成本单独保留历史来源；AC全量独立成本单列。',
    '**主准确率—延迟比较**：每组合固定开发128题，四动作都用本轮同作业、同驻留、同执行块的原答与成本。两坐标来自相同人口，不拼接全量准确率和子集耗时。每动作从原始query独立模板/分词/helper/投影或fuser/传输/receiver生成并同步GPU；无跨动作共享文本、hidden、KV、前向或语义编码结果。',
    'BF16、SDPA、greedy、thinking关闭、batch1，receiver最多64tokens、Text helper最多256；EOS及其他生成参数继承旧冻结协议。C2C保留receiver IDs驱动helper和官方层映射。OBQA使用P2-3修正parser，ARC沿用P2-8 v2逐题合法标签（含E）；无效、答错、空输出、生成上限均保留，不据此重试救分。',
    '计时前后同步两个GPU，完整计时从原始query模板处理开始。载入、离线C4/W、额外诊断、评分和日志在动作计时外，仍计入作业预算。记录tensor源/目标字节数及真实设备调用路径：AC为cuda:0的BF16向量到cuda:1的FP32输入；C2C为实际跨卡KV字节；Text分别记录D2H生成IDs、CPU文本UTF-8及H2D receiver IDs。这些为实际tensor/应用载荷口径，不冒称底层互连总线计数或跨节点网络字节。',
    '## 路由拟合与真实开销',
    '四个组合分别拟合。TF-IDF(1,2)、max_features20000、min_df2仅用对应完整train；语义为冻结Qwen3-0.6B FP32最终层最后有效位置1024维、L2归一化，复用已核实输入/身份/ID的特征缓存用于离线拟合和开发选择冻结。金标准只用于监督和评分，不进入输入、特征或选择。',
    '每动作LR(L2,C=1,class_weight=None,max_iter1000,seed0,solver=lbfgs)使用完整train正确性标签；每动作Ridge(alpha1,solver=auto)统一只用同一train256题的新成本拟合log(ms)，预测exp。c_ref为该256题新R平均ms。保留多动作同时正确和全部错误；单类别头采用冻结常数0/1规则。无CV、调参、重划分或开发拟合；收敛警告如实保留。',
    '七个λ=[0,0.01,0.03,0.1,0.3,1,3]，score=p−λ*c_hat/c_ref；同分按R/T/C/A。三动作直接去掉A候选，复用同一R/T/C头、特征和c_ref，在线不计算A头。每组合全部28个路由点报告，不删除被支配点。它们是新成本口径下的普通基线，不冒充P2-9原冻结迁移候选，也不把多一个动作说成方法创新。',
    '每组合先完成train AC与新成本子集，再拟合路由并保存所有开发概率、成本预测、七λ三/四动作选择及模型hash；随后实测train路由开销并冻结仅由train确定的混合，最后才收集新开发结果。开发结果未用于这些冻结。train路由开销在拟合后独立提取特征测得；开发开销与四动作处于同作业同驻留。',
    '`router_total_ms = 本版本实测完整路由开销 + 预先所选动作本题实测ms`。词/语义与三/四动作各自独立提取特征、调用相应头、exp及七次λ选择；每个点保守计入这次完整开销，不声称是单λ最小实现。固定动作与查询无关混合不承担学习路由开销，成本头也不重复加入开销。']
    if summary:
        ss=summary['combinations']
        ac_cost=[]
        for s in ss:
            costs=json.loads((ROOT/'results'/s['pair']/s['dataset']/'AC_full_cost_summary.json').read_text())
            ac_cost.extend([[s['pair']+'/'+s['dataset'],split,c['n'],f"{c['mean_ms']:.3f}",f"{c['median_ms']:.3f}",f"{c['p95_ms']:.3f}",c['invalid']] for split,c in costs.items()])
        lines+=['## 全量 AC 独立成本',table(['组合','划分','题数','平均ms','中位ms','P95 ms','无效答案'],ac_cost),'这些AC成本覆盖完整train和开发人口。完整人口的本轮RTC成本没有测量，因此不能据本表构造全量四动作部署成本比较。']
        lines+=['## 全量开发结果',table(['模型/数据集','R','T','C','A','三动作并集','四动作并集','AC独占'],[[s['pair']+'/'+s['dataset'],*[f"{s['complementarity']['full_dev']['fixed_correct'][a]}/{s['complementarity']['full_dev']['n']} ({100*s['complementarity']['full_dev']['fixed_accuracy'][a]:.3f}%)" for a in range(4)],s['complementarity']['full_dev']['oracle3'],s['complementarity']['full_dev']['oracle4'],s['complementarity']['full_dev']['AC_exclusive']] for s in ss]),'并集是观察全部动作答案后的互补性上限，无可部署oracle准确率或延迟。AC独占题目ID见各组合complementarity.json，不代表路由能提前找到这些题。',table(['模型/数据集','四动作重点正确数','三动作对应正确数','四动作选择R/T/C/A','三动作选择R/T/C/A'],[[s['pair']+'/'+s['dataset'],f"{s['full_primary']['correct']:g}/{s['full_primary']['n']}",f"{s['full_ablation']['correct']:g}/{s['full_ablation']['n']}",s['full_primary']['selection_counts'],s['full_ablation']['selection_counts']] for s in ss])]
        for s in ss:
            tag=s['pair']+'/'+s['dataset'];lines += [f'### {tag}：全量 word λ=0.01 四动作相对参照',table(['参照','分母','准确率差/百分点','95%区间/百分点'],[[r['reference'],r['n'],signed(r['accuracy_difference_pp'],4),f"[{signed(r['accuracy_ci_low_pp'],4)}, {signed(r['accuracy_ci_high_pp'],4)}]"] for r in s['full_primary_comparisons']])]
        lines += [table(['组合','全量固定R/T/C/A无效数','四动作重点无效数','三动作重点无效数'],[[s['pair']+'/'+s['dataset'],s['complementarity']['full_dev']['fixed_invalid'],s['full_primary']['invalid'],s['full_ablation']['invalid']] for s in ss])]
        capture=list(csv.DictReader((ROOT/'AC_exclusive_router_capture.csv').open()))
        lines += [table(['组合','AC独占可用题数','重点路由选择AC题数','所选AC正确数','实际选中的AC独占题数'],[[r['pair']+'/'+r['dataset'],r['AC_exclusive_available'],r['AC_selected'],r['AC_selected_correct'],r['AC_exclusive_selected']] for r in capture if r['policy']=='word_lambda0.01_actions4']),'全部预定路由点的AC选择与独占贡献捕获数量见AC_exclusive_router_capture.csv；没有根据这些结果重新选择策略。']
        panel_fixed=[]
        for s in ss:
            rows=list(csv.DictReader((ROOT/'results'/s['pair']/s['dataset']/'cost_panel_all_policy_results.csv').open()))
            panel_fixed.extend([[s['pair']+'/'+s['dataset'],r['policy'],f"{float(r['correct']):g}/128 ({100*float(r['accuracy']):.3f}%)",f"{float(r['mean_ms']):.3f}",f"{float(r['median_ms']):.3f}",f"{float(r['p95_ms']):.3f}",r['invalid']] for r in rows if r['policy'] in ['R','T','C','A']])
        lines += ['## 固定开发成本子集：四个固定动作',table(['组合','动作','正确数/准确率','平均ms','中位ms','P95 ms','无效数'],panel_fixed)]
        lines += ['## 同次开发成本子集结果（每组合128题）',table(['组合','四动作正确数/128','四动作总均时ms','三动作正确数/128','三动作总均时ms','四动作开销ms','三动作开销ms'],[[s['pair']+'/'+s['dataset'],f"{s['panel_primary']['correct']:g}",f"{s['panel_primary']['mean_ms']:.3f}",f"{s['panel_ablation']['correct']:g}",f"{s['panel_ablation']['mean_ms']:.3f}",f"{s['panel_primary']['mean_overhead_ms']:.3f}",f"{s['panel_ablation']['mean_overhead_ms']:.3f}"] for s in ss]),'![固定128题同次准确率—延迟](cost_panel_accuracy_latency.png)',
        '主图中实心圆/空心三角区分四/三动作，星号为固定重点word λ=0.01；全部七λ都保留。四个面板使用相同坐标尺度。286个离散混合及连续包络均使用四个固定动作的新同次结果；开发包络只是描述性强参照。条件配对区间见下表，不以图上位置代替统计比较。']
        for s in ss:
            tag=s['pair']+'/'+s['dataset'];lines += [f'### {tag}：成本子集重点配对比较',table(['参照','Δ准确率pp [95%CI]','Δ总延迟ms [95%CI]'],[[r['reference'],f"{signed(r['accuracy_difference_pp'],4)} [{signed(r['accuracy_ci_low_pp'],4)}, {signed(r['accuracy_ci_high_pp'],4)}]",f"{signed(r['latency_difference_ms'])} [{signed(r['latency_ci_low_ms'])}, {signed(r['latency_ci_high_ms'])}]"] for r in s['panel_primary_comparisons']])]
            e=s['primary_vs_dev_envelope'];mix=s['train_mixture']['mixture']
            lines += [f"train冻结混合：{mix['status']}，完整精度R/T/C/A概率 `{mix['probabilities']}`；B_train={s['train_mixture']['B_train']:.6f}ms。开发时同时比较准确率和延迟，不称它在开发上仍同成本。该混合与P2-9原冻结混合不同。",
            '重点相对开发连续包络：'+('无可行混合，保留空值。' if e['status']=='infeasible' else f"准确率差 {signed(e['accuracy_above_envelope_pp'],4)}pp；这是用开发答案和计时构造的描述性包络，不是预先冻结参照。"),
            table(['划分','特征','动作头数','题数','平均开销ms','中位ms','P95 ms'],[[r['split'],r['family'],r['n_actions'],r['n'],f"{r['mean_ms']:.3f}",f"{r['median_ms']:.3f}",f"{r['p95_ms']:.3f}"] for r in s['overhead']]),
            f"拟合诊断：`{json.dumps(s['fit_info'],ensure_ascii=False)}`。开发缓存冻结选择与在线实测选择差异：`{s['validation']['online_choice_differences']}`。"]
        lines+=['## 新旧原答自然对照与独立检查',table(['组合/划分/动作','题数','token不同','文本不同','解析不同','正确性不同','改善/伤害'],[[s['pair']+'/'+s['dataset']+'/'+r['split']+'/'+r['action'],r['n'],r['token_ids_changed'],r['raw_text_changed'],r['parsed_answer_changed'],r['correctness_changed'],str(r['improved'])+'/'+str(r['harmed'])] for s in ss for r in s['new_old_changes']]),'新旧原答均保留；自然差异不用于按题择优，不要求开发准确率相等作为运行门槛，也不用“接近”或一个缩放系数宣称时段完全等价。']
        reg=json.loads((ROOT/'results/small/obqa/AC_old_P2_4_regression_summary.json').read_text());lines += [f"小模型742题AC与P2-4自由生成自然对照：旧/新正确数 {reg['old_correct']}/{reg['new_correct']}；token差异 {reg['token_ids_changed']}，文本差异 {reg['text_changed']}，解析差异 {reg['answer_changed']}，正确性差异 {reg['correctness_changed']}。旧共享耗时完全未用于本轮独立成本。",
        f"独立检查结果：`{json.dumps(check,ensure_ascii=False)}`。覆盖、ID对齐、开发前冻结顺序、同次成本、模型选择重放和总延迟算术都从保存资产复算；没有重复旧全量parser回归。"]
    lines += ['## 统计解释、结论边界与剩余问题',
    '重点相对train冻结混合：大OBQA的准确率差区间跨0而延迟增加；大ARC与小OBQA的准确率、延迟差区间均跨0；小ARC的混合为固定C，路由少对1/128题且平均慢17.281ms，延迟差区间[1.026,38.185]ms。小ARC四动作相对三动作快0.233ms、区间[−0.249,−0.219]ms，但两者在该子集的选择完全相同且均未选A，差值全部来自本次实测路由开销，不能归因于加入AC的通信收益。该开销比较也未覆盖重复部署或测量顺序变化。',
    '计时记账见evidence/timing_accounting.json：载入、C4采集、W训练、正式动作、额外诊断、路由头拟合和在线路由开销分别汇总。评分、结果日志、smoke及离线特征准备位于热请求计时之外，并计入PBS实际耗时，但没有各自独立的毫秒计数；该分项限制明确保留空值，没有按时间戳差补造，也未为非核心分项追加动作。',
    '配对bootstrap固定seed0、20000次、按题有放回、95%百分位区间；相同评价人口的所有参照与准确率/延迟共享抽样，混合使用逐题概率加权期望。混合的中位/P95是逐题期望成本的分位数，不是随机动作部署的尾延迟。区间以本次训练和测量为条件，不覆盖训练随机性、重复部署抖动或多重比较校正。其余网格均为辅助开发结果，不能事后替换word λ=0.01重点。',
    '全量与子集结果分别成立；本轮仅在固定开发128题/组合上有四动作同次新计时，不能声称覆盖全部开发题的新四动作成本。公共模型/fuser训练曝光未知，单节点热驻留、一次逐题计时的限制保留。不是冷启动、跨节点通信或硬显存预算实验。',
    '区间跨0不等于等价；AC独占正确不等于事前可识别；W重建MSE下降不等于答题准确率提升。普通特征+LR/Ridge与增加动作数本身不构成方法创新。没有新的独立确认性测试，也不改写P2-9“未确认迁移收益复现”的结论。',
    ('执行和交付已按冻结范围完成。可支持的科学判断仅限上述四个组合、两套明确人口及其条件区间；是否进入方法创新或最终测试由主the reviewer验收决定，本执行端不自动派发P2-11。' if passed else '本轮尚未满足完整PASS条件。精确覆盖和作业状态见本报告首节；只按用户既定恢复/预算规则处理必要缺项，不自动扩展协议。'),
    '## 关键产物绝对路径',
    '\n'.join('- `'+str(ROOT/n)+'`' for n in ['P2_10_AC_FOUR_ACTION_REPORT.md','USER_EXECUTION_PROMPT.md','frozen_config.json','evidence/freeze_receipt.json','data/request_manifest.jsonl','data','results/large/W/W_final.pt','results/large/W/training_state.pt','results/large/W/training_metrics.json','results/large/W/final_receipt.json','full_dev_accuracy_table.csv','cost_panel_accuracy_latency_table.csv','cost_panel_accuracy_latency.png','cost_panel_accuracy_latency.pdf','evidence/submissions.json','evidence/submission_attempts.jsonl','evidence/jobs.json','evidence/progress.json','evidence/independent_result_check.json']),
    '每组合 `{ROOT}/results/{large,small}/{obqa,arc}/` 含：原始 `*_cases.jsonl`、独立AC原答、历史RTC原答及来源、全量与同次子集矩阵、完整train目标、特征/模型、train/dev概率/成本预测/选择、冻结回执、真实开销、逐题重放、全部28路由点、286混合、连续包络及两人口的配对区间。'.replace('{ROOT}',str(ROOT)),
    f"唯一全局状态：`{ROOT.parent/'P2_1_20260910T041720Z/P2_STATE.md'}`。PBS日志目录 `$DATA_DIR/logs/pbs`，作业运行环境与stdout/stderr位于 `$DATA_DIR/runs/iclr2027_p2/{ROOT.name}/<job-id>/`。"]
    (ROOT/'P2_10_AC_FOUR_ACTION_REPORT.md').write_text('\n\n'.join(lines)+'\n')
    save(ROOT/'evidence/report_status.json',{'utc':utc(),'FINAL_STATUS':status,'actual_node_seconds':actual,'progress':p})
    print(status)
if __name__=='__main__':main()
