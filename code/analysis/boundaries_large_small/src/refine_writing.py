"""Editorial assembly from the already frozen summary tables; no new numerical tests."""
from common import *
def table(h,rows):return '| '+' | '.join(h)+' |\n| '+' | '.join(['---']*len(h))+' |\n'+'\n'.join('| '+' | '.join(map(str,r))+' |' for r in rows)+'\n'
intro='''主要新增检验 small/OBQA/C2C 没有可部署的通过点：dev AUROC=.700，但最低q的cal仅65组、2次改变，CP .999上界16.10%。同一128题panel上，事后答案一致参照毛节省29.493ms，小于32.879ms探针费，计费后净节省−3.386ms；这只是预定的零改变一致性参照，不是5%风险约束下的最优上界。

large四层均通过选择性校准，small四层均保留各自参考回退。large/OBQA在完全相同分数和572个R路由下，Text/C2C净节省分别518.891/28.175ms；参考费用差异因此是边界的一部分，不能只归因于模型规模。两C2C大模型部署分别保留605/742、267/299正确，仍低于各自已有最佳固定Text的645/742、274/299；相对自身参考的改善不等于全动作准确率最优。

所有q=1检验均未通过。large/ARC/Text固定R的cal分歧率已低至12/448=2.68%，但p=.010802仍高于.001；选择性q=.95通过，说明基率接近参考与严格有限样本校准须分别考察。small/ARC的低q校准子集本身经验风险仍超过5%，不能将其回退全部归因于cal样本较少，也不能把AUROC约.64解释成完全没有排序信息。

四个large部署的panel成本差描述区间均支持正净节省；效用差仍有不确定性：large/OBQA/Text与large/ARC/C2C的ΔU区间跨零。large/OBQA/C2C的ΔU=.008929，描述区间[.000546,.025084]；它是已曝光panel上的模型条件结果，不是总体胜出、八层联合保证或独立确认。small回退产生[0,0]差值区间，是同一固定策略逐题相同的代数结果，不是统计等价证明。
'''
f=P/'P2_CONFIDENCE_REFERENCE_BOUNDARIES_REPORT_ZH.md';s=f.read_text();at=s.index('## 八个冻结部署');s=s[:at]+intro+'\n'+s[at:]
# Move each selected-calibration sentence underneath its own section title.
import re
s=re.sub(r'冻结选择的cal：([^\n]+)\n\n(### [^\n]+)',r'\2\n\n冻结选择的cal：\1',s)
f.write_text(s)
act=csvread(P/'summary/V2_action_summary_reused.csv');cs=read(P/'summary/panel_source_checks.json');diag=read(P/'summary/probe_diagnostics.json')
fixedrows=[]
for pair in PAIRS:
 for ds in DATASETS:
  rr=[r for r in act if r['pair']==pair and r['dataset']==ds and r['population']=='full' and r['split']!='train'];dd={r['action']:r for r in rr}
  fixedrows.append([pair+'/'+ds.upper(),dd['receiver_only']['n']]+[dd[a]['V2_correct'] for a in ['receiver_only','text','c2c','acw']])
extra=['## 固定四动作：V2原表直接引用',table(['组合','原id数/组数','R正确','Text正确','C2C正确','AC正确'],fixedrows),'来源：summary/V2_action_summary_reused.csv，原V2 action_summary.csv的full开发行；没有调用解析器重评分。AC只作已有最佳固定动作对照，不进入本轮R/b路由。','## 各组合原train256的R计费标尺',table(['组合','c_ref ms','dev panel组数'],[[r['pair']+'/'+r['dataset'].upper(),f"{r['c_ref_train256_R_ms']:.9f}",r['panel_groups']] for r in cs]),'全部panel源raw answer SHA与V2匹配，四动作同题block/job核验通过；各组合panel与全量同id答案差异计数均0。','## Probe与原生R：dev描述诊断',table(['组合','argmax一致/原id数','FP32零分数','标签总质量min','质量median','质量max'],[[r['pair']+'/'+r['dataset'].upper(),f"{r['argmax_agreement_count']}/{r['N_rows']}",r['exact_zero_count'],f"{r['label_mass']['min']:.9f}",f"{r['label_mass']['median']:.9f}",f"{r['label_mass']['max']:.9f}"] for r in diag if r['split']=='dev']),'所有fit/cal/dev标签质量、计时分布与argmax一致性见summary/probe_diagnostics.json和probe_timing.csv。双方INVALID仍作为共同特殊值，主分析不丢弃；全train/dev运行失败计数为0，解析INVALID单独列下表。','## INVALID分解',table(['组合','参考','子集','N','分歧','路由R','改变','运行失败'],[[r['pair']+'/'+r['dataset'].upper(),r['reference'],r['subset'],r['N'],r['d_count'],r['n_R'],r['changed'],r['runtime_failure_rows']] for r in csvread(P/'summary/invalid_decomposition.csv')]),'## 固定R/参考的全量风险及正确数',table(['组合','参考','策略','正确/N','改变/R','覆盖'],[[r['pair']+'/'+r['dataset'].upper(),r['reference'],r['policy'],r['correct']+'/'+r['N'],r['changed']+'/'+r['n_R'] if int(r['n_R']) else 'NA',r['coverage']] for r in csvread(P/'summary/fixed_reference_risk.csv')])]
with (P/'APPENDIX_TABLES_ZH.md').open('a') as f:f.write('\n\n'+'\n\n'.join(extra)+'\n')
# Add numerical interpretation to the English narrative, retaining every prespecified result.
p=P/'paper/boundary_results.tex';s=p.read_text();pos=s.index('\\begin{table}')
s=s[:pos]+r'''The primary new small/OBQA/C2C stratum falls back to C2C. Its development
AUROC is .700, but the lowest-q calibration subset contains only 65 groups
and two changes (3.08\%); its CP .999 upper bound is 16.10\%. Thus observable
ranking does not supply a sufficiently supported low-risk subset. On the
matched panel, even the stipulated post-hoc agreement reference saves only
29.493 ms before a 32.879 ms probe fee, giving -3.386 ms net savings. This
undeployable zero-change reference is not a bound for 5\%-risk optimization.

All four large strata admit selective deployments and all four small strata
fall back. Within large/OBQA, the identical 572 routed questions yield
518.891 ms net savings against Text but 28.175 ms against C2C. Reference cost
is therefore a distinct limitation. The C2C-relative correct counts of
605/742 and 267/299 remain below the corresponding best fixed Text counts
of 645/742 and 274/299. Improvement relative to one reference does not imply
best accuracy among all fixed actions.

No q=1 test passes. In large/ARC/Text, fixed R already has calibration
change rate 12/448 (2.68\%), yet p=.010802 exceeds .001; q=.95 passes.
In small/ARC, low-q subsets still have empirical risk above 5\%, so limited
calibration size alone does not explain failure. Modest AUROC is also not
evidence of no ranking information whatsoever.

All four large panel cost-difference intervals indicate positive net savings,
conditional on the component measurements. Utility-difference intervals
cross zero for large/OBQA/Text and large/ARC/C2C. Large/OBQA/C2C has
$\Delta U=.008929$ with descriptive interval $[.000546,.025084]$, not an
eight-stratum or untouched-confirmation guarantee. Zero-width difference
intervals for fallbacks reflect identical per-question fixed strategies,
not an equivalence test.

'''+s[pos:];p.write_text(s)
# Appendix: exact fixed table and probe diagnostics from existing summaries.
app=[r'\section{Inherited fixed actions and probe diagnostics}',r'\begin{center}\begin{tabular}{llrrrr}\toprule Pair/task & N & R & Text & C2C & AC\\\midrule']
app += [' & '.join(map(str,r))+r' \\' for r in fixedrows];app += [r'\bottomrule\end{tabular}\end{center}',r'Correct counts are copied from the V2 full-development action summary; no answer is reparsed. AC is a historical fixed comparison, never an action in this experiment.',r'\begin{center}\begin{tabular}{lrrr}\toprule Pair/task & Argmax agreement/N & Exact zeros & Min label mass\\\midrule']
for r in diag:
 if r['split']=='dev':app.append(f"{r['pair']}/{r['dataset'].upper()} & {r['argmax_agreement_count']}/{r['N_rows']} & {r['exact_zero_count']} & {r['label_mass']['min']:.9f}"+r' \\')
app += [r'\bottomrule\end{tabular}\end{center}',r'No diagnostic changes membership, prompt, precision, or ranking. All full train/development runtime-failure counts are zero; parsing INVALID is retained separately. Complete probability and timing distributions remain in the source tables.',r'The original train256 R cost scales (ms) are 252.353705754 for large/OBQA, 266.940725320 for large/ARC, 319.453341469 for small/OBQA, and 341.146390922 for small/ARC. These differ from the historical 742-question large/OBQA component table scale.']
with (P/'paper/boundary_appendix.tex').open('a') as f:f.write('\n'+'\n'.join(app)+'\n')
# A concise result-led Work handoff; resource closure is appended by finalize.py.
p=P/'HANDOFF_ZH.md';s=p.read_text();pos=s.index('唯一作业：');s=s[:pos]+'''**数值已完整完成。主要新增small/OBQA/C2C回退；P2继续作为通信省略的价值与边界研究。**

- small/OBQA/C2C：dev AUROC .700；最低q cal为2/65，CP .999上界.160967，没有接受项。事后答案一致参照计probe后panel净节省−3.386ms，非5%约束最优上界。
- large/OBQA T/C均q=.80，572路由，改变19/13、正确638/605；统一128题panel净节省518.891/28.175ms。
- large/ARC T/C为q=.95/.90，284/270路由，改变9/3、正确270/267；panel净节省697.130/101.198ms。
- small四层全部固定参考回退，正确数OBQA T/C=346/366，ARC T/C=126/155；在线probe费及策略差值均0，因为策略相同，不是等价证明。
- large/OBQA/C2C panel ΔU=.008929，描述区间[.000546,.025084]；large/ARC/C2C与large/OBQA/Text ΔU区间跨零。没有跨层联合保证、独立封存确认、因果规模效应或新算法宣称。

'''+s[pos:];s+='\n元数据透明补充：large/OBQA原4208文件含旧dev行整体读入，新C2C校准未用dev分数；原dev_probes_read=false字段不准确，补充说明保留其原hash，见evidence/EXPOSURE_CLARIFICATION_ZH.md。\n';p.write_text(s)
print('EDITORIAL_REFINEMENT_COMPLETE')
