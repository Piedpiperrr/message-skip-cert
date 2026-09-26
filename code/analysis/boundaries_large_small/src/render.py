from common import *
compute();assert (P/'ANALYSIS_FREEZE.json').exists()
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

def typed(r):
 out={}
 for k,v in r.items():
  if v=='':out[k]=None
  elif v in ['True','False']:out[k]=v=='True'
  else:
   try:out[k]=float(v)
   except (ValueError,TypeError):out[k]=v
 return out

def loadcsv(n):return [typed(r) for r in csvread(P/f'summary/{n}.csv')]
main=loadcsv('main_dev');pan=loadcsv('panel_cost');rank=loadcsv('ranking');base=loadcsv('disagreement_base_rates');boot=loadcsv('paired_bootstrap');curves=loadcsv('risk_coverage_curves');tests=loadcsv('calibration_all_160');dep=read(P/'deployments/all.json');cd=read(P/'summary/calibration_diagnostics.json')
fmt=lambda x,n=3:'NA' if x is None else f'{x:.{n}f}'
pct=lambda x:fmt(100*x,2) if x is not None else 'NA'
name=lambda b:'Text' if b=='T' else 'C2C'
combo=lambda r:r['pair']+'/'+r['dataset'].upper()
tag=lambda r:key(r['pair'],r['dataset'],r['reference'])

def table(headers,rows):return '| '+' | '.join(headers)+' |\n| '+' | '.join(['---']*len(headers))+' |\n'+'\n'.join('| '+' | '.join(map(str,r))+' |' for r in rows)+'\n'

def latex(path,headers,rows):
 def esc(x):return str(x).replace('_',r'\_').replace('%',r'\%')
 (P/'paper'/path).write_text('\\begin{tabular}{'+ 'l'*len(headers)+'}\n\\toprule\n'+' & '.join(map(esc,headers))+r' \\'+'\n\\midrule\n'+'\n'.join(' & '.join(map(esc,row))+r' \\' for row in rows)+'\n\\bottomrule\n\\end{tabular}\n')
mainrows=[[combo(r),name(r['reference']),fmt(r['q'],2),f"{int(r['n_R'])}/{int(r['N_groups'])}",f"{int(r['changed'])}/{int(r['n_R'])}" if r['n_R'] else 'NA',f"{int(r['correct'])}/{int(r['N_groups'])}",pct(r['accuracy_diff_reference']),f"[{pct(r['CI95_accuracy_low'])}, {pct(r['CI95_accuracy_high'])}]",pct(r['accuracy_diff_best_fixed'])] for r in main]
selected=[r for r in pan if r['policy']=='ProbeMax']
panrows=[[combo(r),name(r['reference']),f"{int(r['correct'])}/128",fmt(r['gross_saving_ms']),fmt(r['probe_selector_ms']),fmt(r['net_saving_ms']),fmt(r['total_ms']),fmt(r['U'],6),fmt(r['delta_U'],6)] for r in selected]
latex('boundary_main_table.tex',['Pair/task','Ref.','q','R/N','Changed/R','Correct/N',r'$\Delta$ acc. pp','95\% interval',r'$\Delta$ best pp'],mainrows)
latex('boundary_panel_table.tex',['Pair/task','Ref.','Correct','Gross ms','Probe ms','Net ms','Total ms','U',r'$\Delta U$'],panrows)
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':9,'axes.spines.top':False,'axes.spines.right':False,'pdf.fonttype':42})
fig,axes=plt.subplots(2,4,figsize=(13.5,6.2),sharex=True,sharey='row',layout='constrained');colors={'T':'#2467A0','C':'#D48228'}
for col,(pair,ds) in enumerate(( (p,d) for p in PAIRS for d in DATASETS)):
 ax=axes[0,col];ax.set_title(pair+'/'+ds.upper())
 for b in REFS:
  cal=[r for r in tests if (r['pair'],r['dataset'],r['reference'])==(pair,ds,b)];dev=[r for r in curves if (r['pair'],r['dataset'],r['reference'],r['split'])==(pair,ds,b,'dev')];q=dep[key(pair,ds,b)]['q']
  for row,rr,field in [(0,cal,'CP_upper_0_999'),(1,dev,'conditional_risk')]:
   a=axes[row,col];a.plot([100*r['coverage'] for r in rr],[100*r[field] if r[field] is not None else np.nan for r in rr],color=colors[b],linestyle='-' if b=='T' else '--',marker='o' if b=='T' else '^',markersize=3,label=name(b))
   chosen=next((r for r in rr if r['q']==q),None)
   if chosen:a.scatter([100*chosen['coverage']],[100*chosen[field]],s=120,marker='*',color=colors[b],edgecolors='black',linewidths=.5,zorder=5)
  if not q:axes[1,col].text(.04,.95 if b=='T' else .85,name(b)+': fallback',transform=axes[1,col].transAxes,color=colors[b],va='top')
 for row in [0,1]:
  axes[row,col].axhline(5,color='#555555',ls=':',lw=1);axes[row,col].grid(alpha=.17);axes[row,col].set_xlim(0,101);axes[row,col].set_ylim(bottom=0)
 axes[1,col].set_xlabel('Receiver-only coverage (%)')
axes[0,0].set_ylabel('Calibration CP .999 upper (%)');axes[1,0].set_ylabel('Development change / routed (%)');axes[0,0].legend(frameon=False)
fig.savefig(P/'figures/reference_boundaries.pdf');fig.savefig(P/'figures/reference_boundaries.png',dpi=170);plt.close(fig)
report=['# P2_CONFIDENCE_REFERENCE_BOUNDARIES 中文主报告','本轮为固定 ProbeMax 分数与校准规则的八分层开发复验；主要新增检验为 small/OBQA/C2C。D 已降为学习型对照，普通置信度不改称原创方法。两参考在同一模型、题目、分数下分别检验；每次仅 R/b 二选一，没有 Text/C2C 选择器。','## 八个冻结部署：完整开发人口',table(['组合','参考','q','R/组数','改变/R','正确/组数','Δ参考 pp','描述95%区间 pp','Δ已有最佳固定 pp'],mainrows),'完整人口 OBQA 742、ARC 299 行且各自无重复组；全部原 id 正确数与主统计一致。回退的条件风险为 NA，固定参考不支付在线探针。准确率差均为固定策略相对该分层参考；最佳固定四动作比较是描述项，不是选择新参考。','## 独立128题 panel：成本与准确率',table(['组合','参考','正确','毛节省ms','探针+selector ms','净节省ms','总ms','U','ΔU'],panrows),'U = panel准确率 − .01 × panel总均时 / 该组合原train256题R均时。费用为新/复用探针组件加旧完整动作请求，非新端到端重放。全量正确率不与128题均时拼接。两参考的每个独立选择性部署均支付完整探针费；固定R或回退删除探针。无R请求KV/prefill抵扣，探针argmax不替代R生成。','## 四类限制逐层解释']
find=lambda rows,p,d,b,**kw:next(r for r in rows if (r['pair'],r['dataset'],r['reference'])==(p,d,b) and all(r[k]==v for k,v in kw.items()))
for r in main:
 pair,ds,b=r['pair'],r['dataset'],r['reference'];c=next(x for x in cd if tag(x)==tag(r));br=[find(base,pair,ds,b,split=s) for s in ['fit','cal','dev']];rk=find(rank,pair,ds,b,split='dev',scope='all');rv=find(rank,pair,ds,b,split='dev',scope='both_valid');pc=find(pan,pair,ds,b,policy='ProbeMax');oracle=find(pan,pair,ds,b,policy='Posthoc_agreement_no_probe');oraclep=find(pan,pair,ds,b,policy='Posthoc_agreement_with_probe');q1=c['q1'];best=c['min_p_point']
 selected_cal=c['selected_calibration']
 if selected_cal:report.append(f"冻结选择的cal：{combo(r)}/{name(b)} n={selected_cal['n_R']}、k={selected_cal['changed']}、p={float(selected_cal['p_value']):.6g}、CP={float(selected_cal['CP_upper_0_999']):.6f}。")
 reason=('q=1通过，固定R已满足规则；不能归为逐题门控增益。' if r['q']==1 else '存在通过校准的选择性点。' if r['q'] else '没有通过点，固定参考回退。')
 if not r['q']:
  if c['max_empirical_risk_at_most_alpha_n']>0:reason+=f" 有经验风险≤5%的子集，但最大规模仅{c['max_empirical_risk_at_most_alpha_n']}组；严格CP/单项门槛余量不足。"
  else:reason+=' 全部预定q的经验风险均高于5%，不是仅放宽置信界即可解释的近失。'
 if rk['AUROC'] is not None:reason+=f" 开发AUROC={rk['AUROC']:.3f}仅作排序诊断，结合基率与有限cal规模解释，不能由回退单独推断不可迁移。"
 report += [f"### {combo(r)} / {name(b)}",f"fit/cal/dev 分歧基率依次为 {' / '.join(str(int(x['d_count']))+'/'+str(int(x['N_groups']))+' ('+pct(x['disagreement_rate'])+'%)' for x in br)}。固定R的q=1检验：n={q1['n_R']}、k={q1['changed']}、p={float(q1['p_value']):.6g}、CP={float(q1['CP_upper_0_999']):.6f}，接受={q1['accepted']}。",f"接受集合={c['accepted_q']}；选择q={r['q']:.2f}。最小p描述点 q={float(best['q']):.2f}、n={best['n_R']}、k={best['changed']}、p={float(best['p_value']):.6g}；全网格最小CP={c['min_CP']:.6f}，相对.05余量={c['CP_margin_alpha_minus_min']:+.6f}。{reason}",f"开发AUROC/AP={fmt(rk['AUROC'],4)}/{fmt(rk['AP'],4)}；双方有效子集N={int(rv['N'])}，AUROC/AP={fmt(rv['AUROC'],4)}/{fmt(rv['AP'],4)}。主分析保留所有INVALID；获益/伤害/中性改变={int(r['benefit'])}/{int(r['harm'])}/{int(r['neutral_change'])}，边际改变={pct(r['marginal_change'])}%。",f"在相同128题panel中，毛节省{pc['gross_saving_ms']:.3f}ms，探针费{pc['probe_selector_ms']:.3f}ms，净节省{pc['net_saving_ms']:.3f}ms。事后答案一致参照省通信覆盖{pct(oracle['coverage'])}%，不计探针总成本{oracle['total_ms']:.3f}ms、计探针{oraclep['total_ms']:.3f}ms。该参照须同时知道两个解析答案，不能部署，也不是允许5%条件改变的成本或覆盖最优上界。"]
report+=['## Text 与 C2C 的配对边界','以下比较只改变预先列定参考。不同模型规模间的两点差异不识别因果规模效应。']
for pair in PAIRS:
 for ds in DATASETS:
  t=find(main,pair,ds,'T');c=find(main,pair,ds,'C');pt=find(pan,pair,ds,'T',policy='ProbeMax');pc=find(pan,pair,ds,'C',policy='ProbeMax')
  report.append(f"- {pair}/{ds.upper()}：Text q={t['q']:.2f}、覆盖{pct(t['coverage'])}%，C2C q={c['q']:.2f}、覆盖{pct(c['coverage'])}%；净节省分别{pt['net_saving_ms']:.3f}/{pc['net_saving_ms']:.3f}ms。同分数面对不同分歧目标与参考费用，不能把这些差异全部归为模型规模。")
report+=['## 协议、人口与保证边界','OBQA 原 fit2100/cal1366 ID、顺序和组完全复用。ARC train1119行/1118组，组代表最小id，排序后Python random.Random(0)打乱，前670组fit，其余448组cal：实际fit671行/cal448行。重复对 MEA_2011_8_8 / MEA_2012_5_8 位于fit，后者只保留原始行，不用于次序统计或二项检验。旧五折表不改。dev如有重复将按代表统计，本次两个dev均无重复组。分组不看gold、分歧或正确性。','20个q用整数次序统计ceil(j*Nfit/20)，FP32零分并列全部纳入；q1固定R。先冻结fit阈值，再投影cal机器分歧，分别作BinomialCDF(k;n,.05)和CP .999；p≤.001接受，最大已接受q部署。n0的p与CP为1，k=n的CP为1。每层20项给理想条件下Bonferroni≤.02，继承delta=.10每层上限；不声称八层合并FWER≤.10。20项large/OBQA/Text检验复用，140项新增，共160。旧D/R2100接受集合和五族M100结论原样保留。','固定格式探针沿用原native prompt、thinking-off模板，再追加单独编码且无尾随空格的 The correct answer is；BF16/SDPA/batch1，FP32标签logsumexp/softmax，u=1−max p。各tokenizer独立遍历非特殊单token并按实际展示标签匹配；仅在该题K个标签归一化。每receiver首个正式样本完成模板/最后位置检查并收费，无额外warmup。概率和argmax仅诊断，不是P(正确)。质量/argmax诊断见summary/probe_diagnostics.json，原始值不裁剪、不筛题、不改分数。','各参考独立校准流程需2Ncal协议请求；同一模型人口同时比较T/C物理唯一请求为3Ncal，R共享。OBQA分别2732/4098，ARC分别896/1344。分位数fit只需probe，无新gold或分歧头；本轮旧机器输出复用，实际新生成协议请求为0。实验共享probe不意味着在线免收费。','每个分层相对各自参考一次seed0、2000次配对bootstrap，按独立题组；同模型/任务T/C共享索引。panel成本/效用区间仅重采样对应panel组。区间为曝光人口上的描述，不含训练不确定性；不作等价、非劣、独立确认或跨规模因果解释。路由/校准不需正确性标签不等于整个项目未用gold；此前gold比较和开发曝光保留。ARC test1172未读取。','## 历史身份与论文贡献','large/OBQA/Text原742题：q=.80，572路由、19改变、638正确、460.936752ms。D原230路由、6改变、643正确、797.166236ms；ProbeMax−D ΔU=.006072027，描述区间跨零，不能说全面支配或等价。该整表及旧完整E2E FFR/IndepLR继续按原来源保留，不混入新的128题表。ProbeEntropy历史辅助不替代主分数；WordD固定Text回退且不重拟合。D退出当前主方法候选，失败不能概括为所有通信路由无效。','本轮关注普通置信度下通信省略的实际风险、覆盖与计费边界，成功不包装为新算法，负结果与参考回退均保留。跨场景开发复验不等于封存测试通过。硬件、采集时段、组件交互仍未由新E2E排除。','## 交付与执行状态','数值核验见NUMERICAL_VALIDATION.json；7044条新probe及计时、4208条旧引用索引、140新cal+20复用、8部署/路由冻结与3422新评价齐备。资源最终值与作业终态见RESOURCE_RECEIPT.json及HANDOFF_ZH.md。图源与PDF/PNG在figures/；英文正文paper/reference_preserving.tex。TeX编译状态由最终交付记录确认，不安装环境。', '![预定参考比较图](figures/reference_boundaries.png)','图中星号为冻结部署，线仅连接预定q描述点；回退无条件风险点。cal CP界与dev经验风险含义不同，不能视为八层共同保证。']
(P/'P2_CONFIDENCE_REFERENCE_BOUNDARIES_REPORT_ZH.md').write_text('\n\n'.join(report)+'\n')
# Supporting complete CSV-backed tables in the Chinese report appendix.
appendix=['# 完整附表','## 160项校准',table(['组合','参考','q','n/k','p','CP .999','接受','身份'],[[combo(r),name(r['reference']),fmt(r['q'],2),f"{int(r['n_R'])}/{int(r['changed'])}",f"{r['p_value']:.6g}",fmt(r['CP_upper_0_999'],6),r['accepted'],r['calculation_identity']] for r in tests]),'## 全部panel策略',table(['组合','参考','策略','正确','覆盖%','总ms','毛节省ms','探针ms','净节省ms','U'],[[combo(r),name(r['reference']),r['policy'],int(r['correct']),pct(r['coverage']),fmt(r['total_ms']),fmt(r['gross_saving_ms']),fmt(r['probe_selector_ms']),fmt(r['net_saving_ms']),fmt(r['U'],6)] for r in pan]),'## 配对描述区间',table(['组合','参考','人口','指标','差值','95%下界','95%上界'],[[combo(r),name(r['reference']),r['population'],r['metric'],fmt(r['difference'],6),fmt(r['CI95_low'],6),fmt(r['CI95_high'],6)] for r in boot])]
(P/'APPENDIX_TABLES_ZH.md').write_text('\n\n'.join(appendix)+'\n')
contrib='''P2 examines when communication can be omitted while preserving a prespecified reference protocol. Using an ordinary fixed-format confidence baseline, we compare receiver-only substitution against native Text and an officially ported C2C protocol across two model pairs and two exposed development tasks. The score, quantile grid, calibration rule, and references are fixed before the new evaluations. We distinguish disagreement prevalence, ranking quality, finite calibration support, and probe costs, and report every frozen deployment, including reference fallbacks. Matched action-cost panels separate communication savings from measurement overhead without combining different populations. These results characterize practical opportunities and boundaries rather than introduce a new routing algorithm. D remains a learned comparison, not a current main-method candidate. Independent sealed-test evidence, end-to-end policy timing, and broader robustness remain missing; development replication does not establish causal effects of model scale.'''
assert 100<=len(contrib.split())<=150
(P/'paper/contribution_positioning.tex').write_text(contrib+'\n')
methods=r'''\section{Selective omission relative to a fixed reference}
We study independent binary decisions between native receiver-only $R$ and a
prespecified reference $b\in\{\mathrm{Text},\mathrm{C2C}\}$. Each reference
is evaluated separately; no Text/C2C selector or new multi-action algorithm
is learned. C2C denotes the official port, not AC or a historical hidden-prefix
protocol. ProbeMax is an ordinary confidence baseline, and D is a learned
comparison rather than a current main-method candidate.

For frozen V2 parsed outputs, $d_b=\mathbf1[o_R\ne o_b]$. INVALID is the
existing shared special value; two INVALID outputs agree. All questions
remain in the main analysis, while parsing invalidity and runtime failures
are distinguished. Correctness labels are associated only after every
new development route is frozen. This computation requires no correctness
labels for its score or calibration, but historical project decisions have
used gold and exposed development outcomes.

We reuse the previous large/OBQA probe unchanged. New probes use the exact
receiver checkpoint and native question/options/chat template with thinking
disabled, followed by the separately encoded literal \texttt{The correct
answer is}, without trailing space or label. Each tokenizer independently
collects non-special single tokens whose standalone decoding, after stripping
whitespace, equals a displayed legal label. Normalization uses only the
question's actual $K$ labels, including three- and five-option ARC questions.
One BF16/SDPA backbone prefill projects only the last valid hidden position;
FP32 label log-sum-exp and softmax define $u=1-\max_l p_l$. Exact zero ties
are retained. This fixed-format conditional label distribution is not
$P(\mathrm{correct})$, nor the actual native R answer. No helper, generation,
extra warmup, model fitting, or KV reuse is introduced.

Both OBQA pairs reuse the original 2100/1366 fit/calibration order. ARC's
new risk-calibration split groups whitespace-normalized questions and ordered
options, chooses the smallest ID per group, sorts and shuffles representatives
with Python random.Random(0), and assigns the first $\lfloor.60G\rfloor$
complete groups to fit. The 1119 rows form 1118 groups: fit has 671 rows/670
groups, calibration 448 rows/448 groups. The registered duplicate remains
in fit; only its minimum-ID representative enters thresholds and binomial
tests. The old five-fold table is unchanged. Development has 742 OBQA and
299 ARC independent groups, equal to row counts.

For $j=1,\ldots,19$, the threshold is fit order statistic
$\lceil jN_{\rm fit}/20\rceil$, with all ties included. $q=1$ is fixed R.
Fit thresholds freeze before reading calibration disagreement. On routed
calibration groups, $p=\Pr\{\operatorname{Bin}(n,.05)\le k\}$ and
$U_{\rm CP}=\operatorname{BetaQuantile}(.999;k+1,n-k)$; $n=0$ gives both
values one, and $k=n$ gives upper bound one. Accept $p\le.001$ and deploy
the largest accepted $q$, otherwise fixed $b$. Twenty predetermined tests
per stratum give an ideal Bonferroni upper bound .02, within the inherited
per-stratum .10 limit. We do not claim eight-stratum joint FWER at most .10.
The original 20 large/OBQA/Text tests and deployment are reused; 140 tests
are new. Historical five-family $M=100$ claims retain their original scope.
'''
(P/'paper/boundary_methods.tex').write_text(methods)
results=[r'\section{Prespecified reference-boundary results}',r'All eight frozen deployments are reported, including fixed-reference fallbacks. Full-population accuracy and risk are separated from the 128-question matched action-cost panels. The primary new stratum is small/OBQA/C2C; the others are predeclared boundary comparisons.',r'\begin{table}[t]\centering\scriptsize\resizebox{\linewidth}{!}{\input{boundary_main_table.tex}}\caption{Full exposed development populations. R/N is omission coverage, changed/R is conditional answer-change risk, and accuracy differences are percentage points. Zero q denotes reference fallback; its conditional risk is undefined. Intervals are descriptive paired group bootstrap intervals.}\end{table}',r'\begin{table}[t]\centering\scriptsize\resizebox{\linewidth}{!}{\input{boundary_panel_table.tex}}\caption{Separate original 128-question panels. Gross savings minus the complete required probe and selector fee gives net savings; positive net means faster. U uses panel correctness and the corresponding train-panel R cost scale. These are component recompositions, not new end-to-end measurements.}\end{table}']
for r in main:
 c=next(x for x in cd if tag(x)==tag(r));pc=find(pan,r['pair'],r['dataset'],r['reference'],policy='ProbeMax');rk=find(rank,r['pair'],r['dataset'],r['reference'],split='dev',scope='all')
 results.append(f"\\paragraph{{{combo(r)} / {name(r['reference'])}.}} The frozen deployment selects $q={r['q']:.2f}$, routes {int(r['n_R'])}/{int(r['N_groups'])} groups, changes {int(r['changed'])} answers, and retains {int(r['correct'])} correct answers. Development disagreement AUROC/AP are {fmt(rk['AUROC'],3)}/{fmt(rk['AP'],3)}. The minimum calibration CP bound over the predetermined grid is {c['min_CP']:.4f}; this diagnostic does not change the selected point. On its separate panel, gross savings of {pc['gross_saving_ms']:.3f} ms and a {pc['probe_selector_ms']:.3f} ms probe fee yield {pc['net_saving_ms']:.3f} ms net savings.")
results += [r'\begin{figure}[t]\centering\includegraphics[width=\linewidth]{../figures/reference_boundaries.pdf}\caption{Same-score comparison of predeclared Text and C2C references. Curves connect only the 20 predetermined quantiles. Stars mark frozen deployments; fallbacks have no conditional-risk point. Calibration CP .999 bounds and exposed-development empirical risks have different inferential identities. The dotted line is 5\%.}\end{figure}',r'\paragraph{Interpretation.} Fixed-R disagreement and the q=1 test separate query-independent closeness from per-question gating. Ranking diagnostics must be considered jointly with prevalence and calibration support: a fallback alone does not demonstrate failed transfer, especially for the smaller ARC calibration population. Comparisons between Text and C2C hold the model, question population, and score fixed. Two model scales do not identify a causal scale effect. Complete valid-only ranking, INVALID decomposition, accepted sets, calibration margins, and all predetermined curves are retained in the appendix and source tables.',r'\paragraph{Descriptive agreement reference.} After observing both parsed answers, an undeployable reference chooses R on every agreement and b otherwise. We report its panel cost both without a probe fee and with the complete measured probe fee. It has zero answer changes on that panel but requires both outputs. It is not an optimal cost or coverage bound under an allowed 5\% conditional change rate.']
(P/'paper/boundary_results.tex').write_text('\n\n'.join(results)+'\n')
cost=r'''\section{Cost, supervision, and evidence boundaries}
Each selective strategy independently pays tokenization and prefix construction,
transfer, full prefill, last-position projection, label probabilities, score,
selector, and synchronization. Startup, audit I/O, and probability-mass
diagnostics are recorded separately. Fixed R and reference fallbacks remove
unnecessary online probes. The selected historical complete action request
is added without a KV or prefill discount. Original requests include all
native Text/C2C communication and generation steps; scoring and additional
validation diagnostics lie outside their historical timing boundary.

Cross-combination costs use exactly the original 128-question development
panels and their V2 correctness. With each combination's original train256
R mean $c_{\rm ref}$ and fixed $\lambda=.01$,
$U=\overline y_{\rm panel}-.01\overline c_{\rm panel}/c_{\rm ref}$.
No full-population accuracy is paired with panel timing. Different acquisition
times, hardware placement, residency, and component interactions remain
limitations because this is not an end-to-end policy replay.

A standalone R/b calibration workflow needs $2N_{\rm cal}$ machine requests;
comparing both references on one population needs $3N_{\rm cal}$ physical
unique requests with R shared. Quantile fitting needs probes but no new gold
or disagreement head. All machine outputs are reused here: actual new
protocol requests, helper forwards, answer generation, and fitted heads are
zero. Shared experimental probes do not make deployment probes free.

For each stratum minus its reference, one seed-0 set of 2000 paired bootstrap
resamples gives a descriptive accuracy interval. Text/C2C within a combination
share group indices. Panel accuracy, cost, and utility differences use only
the corresponding panel groups. Models, scores, and thresholds remain fixed;
these intervals omit training uncertainty and support neither equivalence,
noninferiority, independent confirmation, nor post-hoc winner guarantees.
ARC test remains sealed. Gold exposure and historical reference comparisons
prevent treating these development results as an untouched confirmation.

\paragraph{Historical large/OBQA identity.}
The earlier 742-question Text point remains q=.80, 572 routed, 19 changes,
638 correct, and 460.936752 ms. D remains 230 routed, six changes, 643 correct,
and 797.166236 ms. ProbeMax minus D has $\Delta U=.006072027$ with descriptive
interval $[-.005660304,.018319751]$. This does not establish cost--accuracy
domination or equivalence. These complete-population component results and
the older complete E2E FFR/IndepLR measurements retain their original sources;
they are not merged with the new unified panels. ProbeEntropy remains
historical auxiliary evidence and WordD retains its Text fallback without
refitting. D's failures do not show that all communication routing is useless.

\paragraph{Current contribution and missing evidence.}
\input{contribution_positioning.tex}
'''
(P/'paper/boundary_cost_limitations.tex').write_text(cost)
(P/'paper/reference_preserving.tex').write_text('\\input{boundary_methods.tex}\n\\input{boundary_results.tex}\n\\input{boundary_cost_limitations.tex}\n')
# Self-contained manuscript with complete calibration and diagnostics appendix.
(P/'paper/manuscript.tex').write_text(r'''\documentclass[11pt]{article}
\usepackage[margin=0.7in]{geometry}
\usepackage{amsmath,amssymb,booktabs,graphicx,longtable,hyperref}
\title{When Can Communication Be Omitted? Confidence and Fixed-Reference Boundaries}
\author{}\date{}
\begin{document}\maketitle
\input{reference_preserving.tex}
\appendix\input{boundary_appendix.tex}
\end{document}
''')
app=[r'\section{Complete calibration ledger}',r'Twenty items are reused and 140 are newly computed. All values preserve the fixed score, split, and grid. The ledger is per stratum, not a joint eight-stratum guarantee.',r'\scriptsize\begin{longtable}{llllrrrll}\toprule Pair/task & Ref & q & n/k & p & CP & Coverage & Accept & Identity\\\midrule\endhead']
for r in tests:app.append(f"{combo(r)} & {name(r['reference'])} & {r['q']:.2f} & {int(r['n_R'])}/{int(r['changed'])} & {r['p_value']:.3g} & {r['CP_upper_0_999']:.4f} & {100*r['coverage']:.1f} & {r['accepted']} & {r['calculation_identity']}"+r' \\')
app += [r'\bottomrule\end{longtable}\normalsize',r'\section{Panel policies and undeployable agreement reference}',r'\scriptsize\begin{longtable}{lllrrrrr}\toprule Pair/task & Ref & Policy & Correct & Gross ms & Probe ms & Total ms & U\\\midrule\endhead']
for r in pan:app.append(f"{combo(r)} & {name(r['reference'])} & {r['policy'].replace('_', ' ')} & {int(r['correct'])} & {r['gross_saving_ms']:.2f} & {r['probe_selector_ms']:.2f} & {r['total_ms']:.2f} & {r['U']:.5f}"+r' \\')
app += [r'\bottomrule\end{longtable}\normalsize',r'\section{Valid-only rankings and INVALID decomposition}',r'\scriptsize\begin{longtable}{llllrrrr}\toprule Pair/task & Ref & Split & Scope & N & d & AUROC & AP\\\midrule\endhead']
for r in rank:app.append(f"{combo(r)} & {name(r['reference'])} & {r['split']} & {r['scope'].replace('_',' ')} & {int(r['N'])} & {int(r['d_count'])} & {fmt(r['AUROC'])} & {fmt(r['AP'])}"+r' \\')
app += [r'\bottomrule\end{longtable}',r'\begin{longtable}{lllrrrr}\toprule Pair/task & Ref & Subset & N & d & R & Changed\\\midrule\endhead']
for r in loadcsv('invalid_decomposition'):app.append(f"{combo(r)} & {name(r['reference'])} & {r['subset'].replace('_',' ')} & {int(r['N'])} & {int(r['d_count'])} & {int(r['n_R'])} & {int(r['changed'])}"+r' \\')
app += [r'\bottomrule\end{longtable}\normalsize',r'\section{Paired uncertainty}',r'\scriptsize\begin{longtable}{llllrrr}\toprule Pair/task & Ref & Population & Difference & Estimate & Lower & Upper\\\midrule\endhead']
for r in boot:app.append(f"{combo(r)} & {name(r['reference'])} & {r['population'].replace('_',' ')} & {r['metric'].replace('_',' ')} & {r['difference']:.6f} & {r['CI95_low']:.6f} & {r['CI95_high']:.6f}"+r' \\')
app += [r'\bottomrule\end{longtable}\normalsize',r'\section{Reproducibility and resources}',r'Exact model/tokenizer identities, dynamic label token sets, prefix/template hashes, first formal request checks, per-question timing, split/group tables, and immutable route receipts accompany the source package. Raw full-vocabulary logits and model weights are excluded. Resource and compilation receipts are provided separately; no unmeasured facility charge is treated as zero.']
(P/'paper/boundary_appendix.tex').write_text('\n'.join(app)+'\n')
save(P/'RENDER_RECEIPT.json',{'utc':utc(),'figure_generated':True,'formats':['pdf','png'],'contribution_words':len(contrib.split()),'tex_compiled':False,'visual_inspection':'pending root inspection'})
print('RENDER_COMPLETE',flush=True)
