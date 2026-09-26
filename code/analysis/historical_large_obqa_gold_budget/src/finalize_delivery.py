from common import *
import tarfile,ast
r=read(P/'RESOURCE_RECEIPT.json');assert r['job_state']=='F' and r['exit_status']==0
freezes=['SUBSETS_FREEZE.json','PROTOCOL_FREEZE.json','IMPLEMENTATION_FREEZE.json','LABEL_INTERFACES_FREEZE.json','MODELS_FREEZE.json','THRESHOLDS_FREEZE.json','DEPLOYMENT_FREEZE.json','DEV_ROUTES_FREEZE.json','ANALYSIS_COMPLETE.json','FIGURES_COMPLETE.json']
for n in freezes:
 for f,h in read(P/n)['files'].items():assert sha(P/f)==h,(n,f)
for x in csv.DictReader((P/'SOURCE_INDEX.csv').open()):assert sha(x['path'])==x['sha256'],('old source changed',x['path'])
for f in (P/'src').glob('*.py'):ast.parse(f.read_text(),filename=str(f))
assert len(list((P/'subsets').glob('R*.json')))==15
assert len(list((P/'models').glob('R*.joblib')))==15
assert len(list(csv.DictReader((P/'summary/calibration_new_300.csv').open())))==300
assert len(jl(P/'records/dev_per_question_new.jsonl'))==11130
# Verify reference rows are directly inherited; no numerical recalculation.
original={(x['family'],x['q']):x for x in csv.DictReader((OLD/'summary/calibration_100.csv').open()) if x['family'] in ['D','R']}
for x in csv.DictReader((P/'comparisons/shared_reference_40.csv').open()):
 src=original['R' if x['family']=='R2100' else 'D',x['q']]
 for key in src:
  if key!='family':assert x[key]==src[key],(key,x)
for repeat in range(5):assert len(list(csv.DictReader((P/f'comparisons/r{repeat}_100.csv').open())))==100
save(P/'evidence/DELIVERY_VALIDATION.json',{'passed':True,'freeze_manifests_verified':len(freezes),'parent_sources_unchanged':True,'new_models':15,'new_calibration_rows':300,'dev_policy_rows':11130,'old_reference_test_fields_exactly_reused':True,'syntax_verified':True,'figure_checked':'evidence/FIGURE_VISUAL_CHECK.json','paper_source_checked':'paper/SOURCE_VALIDATION.json','preparation_deviation_disclosed':True,'pre_list_perfect_label_blinding':False,'no_new_numerical_run':True,'utc':utc()})
summ=list(csv.DictReader((P/'summary/budget_summary.csv').open()))
final={'status':'COMPLETE','task':'P2_GOLD_BUDGET_CROSSOVER','stage':P.name,'utc':utc(),'new_models':15,'LR_fits':15,'fit_attempts':15,'constant_fallbacks':0,'new_calibration_tests':300,'reused_tests':40,'distinct_model_grid_items':340,'comparison_views':5,'new_dev_evaluations':11130,'dev_population':742,'new_GPU_compute_seconds':0,'new_backbone_tokenizer_loads':0,'new_prefills':0,'new_helper_forwards':0,'new_generation':0,'new_protocol_requests':0,'new_human_labels':0,'crossover_counts':[{k:x[k] for k in ['B','selective_accepted_count','utility_crossover_count','cost_accuracy_crossover_count','delta_U_D_median','delta_U_D_min','delta_U_D_max']} for x in summ],'job_id':r['job_id'],'job_state':'F','exit_status':0,'CPU_charged_seconds':r['CPU_charged_seconds'],'GPU_requested_allocation_hours':1/6,'GPU_actual_allocation_hours':r['actual_GPU_allocation_hours'],'config_sha256':sha(P/'frozen_config.json'),'freeze_sha256':{n:sha(P/n) for n in freezes},'preparation_deviation':'evidence/PREPARATION_DEVIATION.json; two old schema rows before subset materialization, user-specified rule unchanged','historical_exposure_preserved':True,'TeX_compiled':False,'sbank_charge':None,'budget_closed':True,'next_action':'Return to Work; no automatic new experiment'}
save(P/'FINAL_RECEIPT.json',final)
state=ROOT/'P2_1_20260910T041720Z/P2_STATE.md';before=state.read_bytes();mark=f'<!-- COMPLETE {P.name} -->';assert mark.encode() not in before
entry=f'''\n\n{mark}
## {utc()} — {P.name} COMPLETE，交回Work

- P2_GOLD_BUDGET_CROSSOVER完成：15少gold correctness-R头、15次LR尝试且全部收敛、0常数fallback；300新cal检验+40原D/R2100共享项=340不同模型—网格项，5张每重复100项视图；15×742=11130条新dev策略题评价全完成。原fit/cal/dev2100/1366/742与全部z/计时/参照只读复用。
- 预定两标记结果（效用追平/成本—准确率同时追平）：B32为2/5、1/5；主B128为1/5、1/5，仅r0；B512为3/5、2/5。B128 ΔU_D中位−.000548575、范围[−.004262678,+.001225704]。少量gold在部分子集已能竞争，不能从2100-gold对照推出必须2100；128未稳定追平，不能推普遍最低标签量。D仍有无需正确性标签的可行性价值，不支持独有排序、已成立新方法或总体采集费更低。
- D/R2100原身份不变。每重复100项、alpha=.05/delta=.10/M100/p≤.001；五重复非独立或总体FWER=.10联合搜索，未挑seed或新部署点。bootstrap仅主B128、模型条件描述；成本仍为父feature与同结构R-head逐题费用代理加历史完整请求，0计时敏感追平。
- 单R128学习流程需2860协议请求对D6932，均需3466 offline z；15配置3360标签位置但唯一gold并集1579，B128并集566。新增人工标注/协议请求/特征/GPU计算/backbone或tokenizer加载/prefill/helper/生成均0。
- 准备偏差透明登记：子集物化前预览两行旧标签schema（14-1371、14-97）；用户随机规则事先固定且未变。两行均不属任何B32/128子集，部分B512包含；正式B题接口及统计在冻结后。不能声称完美清单前盲化，报告/论文/回执均披露，未据此删题或重抽。
- 唯一作业{r['job_id']}已F/0；申请gpu-queue/select1/600s=1/6 GPU allocation hour，实际分配110s=.030556 GPU hour（scheduler104s），CPU含30s准备报告预留共59.785303/300s。旧185721预算未恢复，本轮预算关闭，无第二作业。sbank收费NA；TeX无环境未编译。
- 新目录 `{P}`，配置SHA256 `{sha(P/'frozen_config.json')}`。中文主报告/HANDOFF、英文paper/16–17/表图、15子集/头、全部检验/逐题预测、成本/标签/资源账、源码、SHA256SUMS与轻量包齐备；z留原ClusterB，包内仅索引/路径/哈希。原状态前缀和父资产哈希保持不变。
- 停止交回Work决定后续论文定位；不自动新增预算点、seed、模型、数据集、动作或实验。
'''
with state.open('ab') as f:f.write(entry.encode())
assert state.read_bytes()[:len(before)]==before
save(P/'evidence/P2_STATE_APPEND_RECEIPT.json',{'path':str(state),'before_sha256':hashlib.sha256(before).hexdigest(),'before_bytes':len(before),'after_sha256':sha(state),'prefix_unchanged':True,'marker':mark,'utc':utc()})
(P/'SESSION_RESUME_ZH.md').write_text('本轮P2_GOLD_BUDGET_CROSSOVER已COMPLETE；唯一PBS185731已F/0，预算关闭，无剩余提交权。禁止恢复185721旧预算或重做本轮成功模型。\n15头/300新cal/11130dev评价完成，GPU/LLM/新人工均0。B128仅r0追平，完整预算/重复结果见HANDOFF与FINAL_RECEIPT。\n冻结哈希见FINAL_RECEIPT，资源见RESOURCE_RECEIPT。两行旧schema预览偏差必须保留；原随机规则未变。\n报告、英文16–17、表图、源码和轻量包齐备；TeX无环境未编译，sbank收费NA。完成交回Work，不自动下一实验。\n')
def exclude(p):return '__pycache__' in p.parts or 'matplotlib-cache' in p.parts or p.suffix in ['.lock','.tmp'] or p.name in ['SHA256SUMS','DELIVERY_RECEIPT.json'] or p.name.endswith('.tar.gz')
files=[f for f in sorted(P.rglob('*')) if f.is_file() and not exclude(f)]
assert not any(f.suffix=='.npz' and 'features' in f.parts for f in files)
(P/'SHA256SUMS').write_text(''.join(f'{sha(f)}  {f.relative_to(P)}\n' for f in files));files.append(P/'SHA256SUMS')
bundle=P/(P.name+'_WORK_LIGHT.tar.gz')
with tarfile.open(bundle,'w:gz') as t:
 for f in files:t.add(f,arcname=str(Path(P.name)/f.relative_to(P)),recursive=False)
expected={str(Path(P.name)/f.relative_to(P)):sha(f) for f in files}
with tarfile.open(bundle,'r:gz') as t:
 for m in t.getmembers():assert hashlib.sha256(t.extractfile(m).read()).hexdigest()==expected[m.name]
save(P/'DELIVERY_RECEIPT.json',{'status':'COMPLETE','bundle':str(bundle),'sha256':sha(bundle),'bytes':bundle.stat().st_size,'file_count':len(files),'member_hashes_verified':True,'manifest_sha256':sha(P/'SHA256SUMS'),'z_included':False,'large_model_weights_included':False,'whole_old_experiment_included':False,'train_z_index':str(P/'inputs/TRAIN_FEATURE_INDEX.csv'),'dev_z_index':str(P/'inputs/DEV_FEATURE_INDEX.csv'),'utc':utc()})
print(json.dumps(read(P/'DELIVERY_RECEIPT.json'),indent=2))
