"""Document formatting of already computed PBS results; no fitting/statistical work."""
from common import *
assert (P/'ANALYSIS_COMPLETE.json').exists()
def csvread(p):return list(csv.DictReader(Path(p).open()))
def val(x,d=3):return 'NA' if x is None or x=='' else f'{float(x):.{d}f}'
def integer(x):return str(int(float(x)))
def pct(x,d=2):return 'NA' if x is None or x=='' else f'{100*float(x):.{d}f}'
def pvalue(x):return 'NA' if x is None or x=='' else f'{float(x):.6g}'
def md(headers,rows):return '| '+' | '.join(headers)+' |\n| '+' | '.join(['---']*len(headers))+' |\n'+'\n'.join('| '+' | '.join(map(str,r))+' |' for r in rows)+'\n'
def tex(headers,rows,spec):return '\\begin{tabular}{'+spec+'}\n\\toprule\n'+' & '.join(headers)+r' \\'+'\n\\midrule\n'+'\n'.join(' & '.join(map(str,r))+r' \\' for r in rows)+'\n\\bottomrule\n\\end{tabular}\n'
main=csvread(P/'summary/main_dev.csv');mm={r['family']:r for r in main};dep=read(P/'models/deployment.json');diag=read(P/'summary/calibration_diagnostics.json')
rank=csvread(P/'summary/ranking.csv');rankdev={r['family']:r for r in rank if r['split']=='dev'}
names={'Fixed_Text':'Text','Fixed_R':'R (fixed)'}
rows=[[names.get(r['family'],r['family']),val(r['q'],2),integer(r['n_R']),pct(r['coverage']),('NA' if not float(r['n_R']) else integer(r['changed'])+'/'+integer(r['n_R'])),integer(r['correct']),val(r['mean_cost_ms']),val(r['U'],6)] for r in main]
(P/'paper/table_main.tex').write_text(tex(['Score','$q$','R/$742$','Coverage (\\%)','Changes/R','Correct','Mean ms','$U$'],rows,'lrrrrrrr'))
text='# 冻结结果完整表\n\n组件重组成本；不是新端到端测量。Text条件风险NA、边际改变0。主对照ProbeMax，其余两个新分数为辅助。\n\n'+md(['族','q','R/742','覆盖%','改变/R','正确','mean ms','U'],rows)
rows=[]
for f in FAMILIES:
 p=dep[f];a=p['calibration'];best=next(r for r in diag if r['family']==f)['minimum_p_test'];r=a or best
 rows.append([f,','.join(f'{q:.2f}' for q in p['accepted_q']) or 'none',val(p['q'],2),'selected' if a else 'min-p diagnostic',integer(r['n_R']),integer(r['changed']),pvalue(r['p_value']),val(r['CP_upper_0_999'],6)])
text+='\n校准：回退族列出的n/k/p/CP为最小p的预设网格项诊断，不是已接受部署；全部100项见CSV。\n\n'+md(['族','接受q集合','部署q','该行身份','cal n','cal k','p','CP .999'],rows)
texcal=[]
for row in rows:
 r=list(row);qs=dep[r[0]]['accepted_q'];r[1]=(f'{qs[0]:.2f}--{qs[-1]:.2f}' if len(qs)>1 else f'{qs[0]:.2f}' if qs else 'none');r[3]='selected' if qs else 'min-$p$';texcal.append(r)
(P/'paper/table_calibration.tex').write_text(tex(['Score','Accepted $q$','$q^*$','Row','$n$','$k$','$p$','CP upper'],texcal,'llllrrrr'))
rows=[[r['family'],val(r['AUROC_disagreement'],6),val(r['AP_disagreement'],6),val(r['Spearman_D'],6)] for r in rank if r['split']=='dev']
text+='\n统一以d为目标的开发排序\n\n'+md(['族','AUROC(d)','AP(d)','Spearman(D)'],rows)
(P/'paper/table_ranking.tex').write_text(tex(['Score','AUROC($d$)','AP($d$)','Spearman(D)'],rows,'lrrr'))
rows=[[names.get(r['family'],r['family']),pct(r['conditional_risk'],3),pct(r['marginal_change'],3),integer(r['benefit'])+'/'+integer(r['harm'])+'/'+integer(r['neutral_change']),pct(r['accuracy_diff_Text'],3),val(r['median_cost_ms']),val(r['p95_cost_ms']),val(r['net_saving_vs_Text_ms'])] for r in main]
text+='\n开发改变、正确率与费用完整诊断\n\n'+md(['族','条件改变%','边际改变%','获益/伤害/中性','准确率差Text pp','median ms','p95 ms','净省Text ms'],rows)
(P/'paper/table_dev_diagnostics.tex').write_text('\\begin{table}[ht]\n\\centering\\scriptsize\n'+tex(['Score','Cond. \\%','Marg. \\%','B/H/N','$\\Delta$acc. (pp)','Median ms','p95 ms','Saving ms'],rows,'lrrrrrrr')+'\\caption{Frozen development diagnostics. Changes compare selected R with reference Text; neutral means changed option with unchanged correctness.}\n\\end{table}\n')
boot=csvread(P/'summary/bootstrap_new_vs_D.csv');rows=[[r['policy'],r['metric'],val(r['difference'],6),'['+val(r['CI95_descriptive_low'],6)+', '+val(r['CI95_descriptive_high'],6)+']'] for r in boot]
text+='\n每个新策略减D；一个seed0、2000次联合逐题bootstrap，模型/阈值固定，已曝光人口描述区间\n\n'+md(['新策略','指标','差值','描述95%区间'],rows)
texrows=[[r[0],r[1].replace('_',r'\_'),r[2],r[3]] for r in rows]
(P/'paper/table_bootstrap.tex').write_text('\\begin{table}[ht]\n\\centering\\small\n'+tex(['New policy','Metric','$\\Delta$ vs D','Descriptive 95\\% interval'],texrows,'llrr')+'\\caption{One shared seed-0 question bootstrap with 2000 replicates, conditional on frozen models and thresholds, on the exposed population. These are not equivalence or noninferiority tests.}\n\\end{table}\n')
acq=csvread(P/'summary/supervision_acquisition.csv');rows=[[r['family'],integer(r['unique_fit_gold']),integer(r['machine_fit_d']),integer(r['machine_cal_d']),integer(r['complete_learning_protocol_requests']),integer(r['offline_probe_questions']),integer(r['offline_E1_questions']),integer(r['offline_word_questions'])] for r in acq]
text+='\n独立学习流程的监督/采集需求（实际新人工gold和R/Text请求均0）\n\n'+md(['族','唯一fit gold','fit机器d','cal机器d','完整协议请求','offline probe','offline E1','offline word'],rows)
(P/'paper/table_acquisition.tex').write_text(tex(['Score','Fit gold','Fit $d$','Cal $d$','Requests','Probes','E1','Word'],rows,'lrrrrrrr'))
rows=[[r['family'],val(r['estimated_historical_protocol_seconds']),val(r['historical_E1_measured_seconds'])] for r in acq]
text+='\n历史协议时间按原panel均值估算；E1列为继承实测特征，不是设施收费\n\n'+md(['族','历史请求估算秒','历史实测E1秒'],rows)
matched=csvread(P/'summary/coverage_matched_descriptive.csv');rows=[[r['anchor_frozen_family'],r['family'],integer(r['n_R']),integer(r['changed_at_exact_n']),pct(r['risk_at_exact_n'],3)] for r in matched]
text+='\n精确前n排名仅作匹配覆盖诊断，固定dev顺序破并列，不是新策略\n\n'+md(['锚点族','排序族','精确n','改变数','改变率%'],rows)
(P/'REPORT_TABLES_ZH.md').write_text(text)
alltests=csvread(P/'summary/calibration_comparison_100.csv');rows=[[r['family'],val(r['q'],2),integer(r['n_R']),integer(r['changed']),pvalue(r['p_value']),val(r['CP_upper_0_999'],6),r['accepted'],r['calculation_identity']] for r in alltests]
table='\\begin{longtable}{lrrrrrll}\n\\caption{All 100 calibration items: 40 directly reused references and 60 new tests.}\\\\\n\\toprule\nScore & $q$ & $n$ & $k$ & $p$ & CP upper & Accept & Source\\\\\n\\midrule\\endhead\n'+'\n'.join(' & '.join(r)+r' \\' for r in rows)+'\n\\bottomrule\n\\end{longtable}\n'
(P/'paper/table_calibration_all.tex').write_text(table)
old=csvread(P/'summary/historical_e2e_reference.csv');rows=[[r['path'].replace('_',r'\_'),integer(r['correct_or_expected_correct']),val(r['mean_latency_ms']),val(r['U'],6)] for r in old]
(P/'paper/table_historical_e2e.tex').write_text('\\begin{table}[ht]\n\\centering\\small\n'+tex(['Historical policy','Correct','E2E mean ms','$U$'],rows,'lrrr')+'\\caption{Original end-to-end measurements, retained under their original identity. They are not new measurements of the calibrated binary strategies or controls.}\n\\end{table}\n')
print('Document tables rendered from frozen PBS summaries.')
