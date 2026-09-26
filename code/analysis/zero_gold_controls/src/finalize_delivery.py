"""Metadata, document/source validation and packaging only; no scientific re-evaluation."""
from common import *
import ast,re,subprocess,tarfile,shutil
for src in (P/'src').glob('*.py'):ast.parse(src.read_text())
freeze_names=['PROTOCOL_FREEZE.json','SPLIT_FREEZE.json','IMPLEMENTATION_FREEZE.json','WORD_MODEL_FREEZE.json','PROBE_PROTOCOL_FREEZE.json','FIT_CAL_PROBES_FREEZE.json','THRESHOLDS_FREEZE.json','DEPLOYMENT_FREEZE.json','PROBES_COMPLETE.json','DEV_ROUTES_FREEZE.json','ANALYSIS_COMPLETE.json']
checked=[]
for n in freeze_names:
 r=read(P/n)
 for f,h in r['files'].items():assert sha(P/f)==h,(n,f);checked.append({'freeze':n,'file':f,'sha256':h})
for r in csv.DictReader((P/'SOURCE_INDEX.csv').open()):assert sha(r['path'])==r['sha256'],r['path']
ids={s:read(P/f'splits/{s}_ids.json') for s in ['fit','cal','dev']}
records=jl(P/'records/probe_records.jsonl');attempts=jl(P/'records/probe_attempts.jsonl');expected=ids['fit']+ids['cal']+ids['dev']
assert [r['id'] for r in records]==[r['id'] for r in attempts]==expected and len(expected)==len(set(expected))==4208
for s in ids:assert [r['id'] for r in jl(P/f'records/probe_{s}.jsonl')]==ids[s]
assert len(jl(P/'records/fit_attempts.jsonl'))==1 and len(jl(P/'records/calibration_new.jsonl'))==60
assert len(jl(P/'records/dev_per_question_new.jsonl'))==2226
assert len(list(csv.DictReader((P/'summary/calibration_comparison_100.csv').open())))==100
assert len(list(csv.DictReader((P/'summary/calibration_reused_40_original.csv').open())))==40
assert [r['id'] for r in jl(P/'records/dev_scored_routes.jsonl')]==ids['dev']
texfiles=list((P/'paper').glob('*.tex'));labels=[];refs=[];citations=[];bib=(P/'paper/refs_binary.bib').read_text();inputs=[]
for p in texfiles:
 text=p.read_text();labels+=re.findall(r'\\label\{([^}]+)\}',text);refs+=re.findall(r'\\(?:ref|eqref)\{([^}]+)\}',text);citations+=re.findall(r'\\cite\{([^}]+)\}',text)
 stack=[]
 for kind,env in re.findall(r'\\(begin|end)\{([^}]+)\}',text):
  if kind=='begin':stack.append(env)
  else:assert stack and stack.pop()==env,(p.name,env)
 assert not stack,(p.name,stack)
 for f in re.findall(r'\\input\{([^}]+)\}',text):
  q=P/'paper'/f;assert q.exists(),(p.name,f);inputs.append({'source':p.name,'input':f,'sha256':sha(q)})
 for f in re.findall(r'\\includegraphics(?:\[[^]]*\])?\{([^}]+)\}',text):assert (P/'paper'/f).exists(),f
assert len(labels)==len(set(labels)) and all(r in labels for r in refs)
for cs in citations:
 for c in cs.split(','):assert '{'+c+',' in bib,c
words=len((P/'paper/contribution_positioning.tex').read_text().split());assert 100<=words<=150 and words==132
save(P/'paper/SOURCE_VALIDATION.json',{'utc':utc(),'TeX_compiled':False,'AST_all_python':True,'local_inputs_resolved':inputs,'TeX_environment_nesting_passed':True,'labels_unique_and_references_resolved':True,'bibliography_keys_resolved':True,'contribution_words':words,'scope':'source structure, not TeX layout compilation; independent rendered figure visually checked'})
write_sources=[GOLD/'paper/table_gold_budget_all15_readable.tex',GOLD/'evidence/PREPARATION_DEVIATION.json',GOLD/'evidence/preview_membership.json',Path(read(OLD/'frozen_config.json')['train_labels_source'])]
csvout(P/'WRITING_SOURCE_INDEX.csv',[{'path':str(p),'sha256':sha(p),'role':'directly indexed inherited appendix/evaluation source'} for p in write_sources])
save(P/'VALIDATION_RECEIPT.json',{'utc':utc(),'frozen_assets_checked':checked,'all_indexed_parent_sources_unchanged':True,'probe_order_matches_fit_cal_dev':True,'unique_probe_success':4208,'attempts':4208,'one_fit_attempt':True,'new_cal_tests':60,'reused_cal_tests':40,'frozen_dev_evaluations':2226,'old_scores_models_not_refitted':True,'validation_identity':'metadata, hashes, order and source structure; no new statistical experiment','TeX_compiled':False,'figure_visually_checked':True})
resource=read(P/'RESOURCE_RECEIPT.json');assert resource['job_state']=='F' and resource['exit_status']==0
final={'status':'COMPLETE','task':'P2_ZERO_GOLD_CONTROLS','stage':P.name,'utc':utc(),'primary':'ProbeMax versus D','new_probe_success':4208,'prefill_attempts':4208,'new_LR_fits':1,'new_calibration_tests':60,'reused_tests':40,'new_frozen_dev_evaluations':2226,'dev_population':742,'new_human_gold':0,'new_protocol_requests':0,'helper_forwards':0,'answer_generation':0,'deployment_q':{f:read(P/'models/deployment.json')[f]['q'] for f in FAMILIES},'config_sha256':sha(P/'frozen_config.json'),'freeze_sha256':{f:sha(P/f) for f in freeze_names},'probe_protocol_sha256':sha(P/'PROBE_PROTOCOL_FREEZE.json'),'job_id':resource['job_id'],'job_state':'F','exit_status':0,'CPU_charged_seconds':resource['CPU_charged_seconds'],'GPU_requested_allocation_hours':.5,'GPU_actual_allocation_hours':.13,'sbank_charge':None,'sbank_status':resource['sbank']['status'],'TeX_compiled':False,'integrated_paper_entry':'paper/reference_preserving.tex','contribution_words':words,'historical_exposure_preserved':True,'inherited_two_row_preview_disclosed':True,'old_gold_budget_closed_and_not_rerun':True,'budget_closed':True,'remaining_submissions':0,'remaining_prefill_attempts':0,'remaining_fit_attempts':0,'remaining_new_calibration':0,'remaining_dev_evaluations':0,'next_action':'Return to Work; no automatic new experiment or method claim'}
save(P/'FINAL_RECEIPT.json',final)
save(P/'SESSION_RESUME_ZH.json',{'stage':'COMPLETE_STOPPED','job_id':resource['job_id'],'successful_ids_source':'records/probe_records.jsonl','success':4208,'budget_closed':True,'remaining_submissions':0,'remaining_prefill_attempts':0,'remaining_fit_attempts':0,'remaining_new_calibration':0,'remaining_dev_evaluations':0,'freeze_sha256':final['freeze_sha256'],'note':'交回Work；不得重跑成功id或恢复旧预算'})
(P/'SESSION_RESUME_ZH.md').write_text('本轮P2_ZERO_GOLD_CONTROLS已COMPLETE并停止。唯一PBS185737已F/0，预算关闭，无剩余提交/forward/拟合/cal/dev授权。\n4208probe、1WordD拟合、60新cal、2226新冻结dev策略题评价完成；源成功id及逐题哈希在records/probe_records.jsonl，各冻结哈希在FINAL_RECEIPT.json。\nProbeMax q=.80，572路由/19改变/638正确/460.936752ms；D230路由/6改变/643正确/797.166236ms。覆盖成本更优但少5正确，Delta U描述区间跨零；WordD回退Text。主对照未换成Entropy。\n整合英文正文和132词定位段已交付，TeX未编译，图已渲染核对，设施收费NA。历史曝光、成本代理及旧两行预览偏差保留。停止交回Work。\n')
shutil.copyfile(P/'PROGRESS.json',P/'evidence/PROGRESS_NUMERICAL_COMPLETE.json')
save(P/'PROGRESS.json',{'phase':'COMPLETE_STOPPED','job_id':resource['job_id'],'utc':utc(),'budget_closed':True,'actual_counts':{'probes':4208,'fits':1,'new_calibration':60,'new_dev_evaluations':2226},'CPU_charged':resource['CPU_charged_seconds'],'all_remaining_execution_allowances':0,'unused_CPU_reserve_not_reusable':900-resource['CPU_charged_seconds']})
state=ROOT/'P2_1_20260910T041720Z/P2_STATE.md';before=state.read_bytes();marker='<!-- COMPLETE '+P.name+' -->'
assert marker.encode() not in before,'Completion state already appended; do not duplicate'
entry=f'''\n\n{marker}
## {utc()} — {P.name} COMPLETE，交回Work

- 唯一P2_ZERO_GOLD_CONTROLS完成：4208次probe prefill尝试/4208成功、1次WordD LR拟合且14步收敛、60项新cal+40项直接复用参照、2226=3×742条新冻结dev策略题评价。新增人工gold/R或Text协议请求/helper/答案生成均0；无重复成功id、第二作业、安装或数据集/分数扩展。原fit/cal/dev2100/1366/742顺序、V2与D/R2100冻结资产不变。
- 预设主对照ProbeMax q=.80，dev572路由(77.09%)、19改变(3.32%)、638正确、组件重组460.936752ms、U=.842276272。D原q=.30、230路由、6改变、643正确、797.166236ms、U=.836204245保持。ProbeMax少5正确、均时减336.229484ms、Delta U=+.006072027，描述95%区间[-.005660304,+.018319751]；不是成本—准确率全面支配、独立确认或等价。
- 辅助Entropy q=.80，572路由、18改变、639正确、460.712185ms、U=.843632537；没有改称主比较。WordD虽然开销.405004ms，cal/dev AUROC=.524547/.537604，无接受项，完整评价Text回退。
- 普通无gold固定格式置信度已有更大低风险覆盖、更强观察排序与更多组件节省；未建立D对该主对照的独有排序、效用或总体采集成本优势。D保留无正确性标签的可行工作点及本点较多正确数。探针非P(正确)，原生R argmax dev一致740/742、全4190/4208，差异保留；精确前n排名仅诊断，FP32大块零分并列真实部署整体纳入。
- 原gold支线保持关闭：128仅1/5追平、32/512效用2/5和3/5；不能说必须2100或128稳定追平。D/R2100 Spearman=.986981520；两行历史预览偏差保留，Work按既定随机规则验证全15子集，无删题/重抽/重跑。
- D/WordD独立学习均需6932机器协议请求；两探针各需2732校准请求+3466离线probe；R2100需4832请求及2100唯一gold。新增控制+历史完整请求的组件成本身份、原端到端FFR/IndepLR身份及曝光限制全部保留，不等同实际总体费用。
- 唯一run011已F/0。gpu-queue/select1申请1800秒=.5 GPU allocation hour；实际468秒=.13 GPU小时（scheduler463秒）；CPU含120秒保守预留为362.105893/900秒。sbank收费NA不是0，预算关闭，禁止再次提交或借旧预算。
- 中文主报告/HANDOFF、连续整合英文paper/reference_preserving.tex及132词定位段、完整表/风险—覆盖—成本PDF与PNG、4208逐题probe协议/映射/hash/时延、WordD模型/向量器、冻结部署/路由、逐项检验、采集资源账、源码和SHA256SUMS齐备。TeX未实际编译（无编译器）；独立图已渲染及视觉核对。
- 目录 `{P}`；配置SHA256 `{sha(P/'frozen_config.json')}`。停止交回Work决定候选方法定位和后续跨场景/论文任务，不自动新实验。
'''
with state.open('a') as f:f.write(entry)
assert state.read_bytes().startswith(before)
save(P/'STATE_APPEND_RECEIPT.json',{'utc':utc(),'path':str(state),'prefix_bytes':len(before),'prefix_sha256':hashlib.sha256(before).hexdigest(),'append_sha256':hashlib.sha256(entry.encode()).hexdigest(),'append_only_verified':True})
# Enumerate only this new deliverable, excluding runtime caches and the package itself.
files=[P/x for x in subprocess.check_output(['rg','--files','--hidden','-g','!evidence/matplotlib-cache/**','-g','!**/__pycache__/**','-g','!*.tar.gz','-g','!SHA256SUMS','-g','!DELIVERY_RECEIPT.json'],cwd=P,text=True).splitlines()]
files=sorted(f for f in files if f.is_file())
(P/'SHA256SUMS').write_text(''.join(sha(f)+'  '+str(f.relative_to(P))+'\n' for f in files))
archive=P/(P.name+'_WORK_LIGHT.tar.gz')
with tarfile.open(archive,'w:gz',compresslevel=6) as tar:
 for f in files+[P/'SHA256SUMS']:tar.add(f,arcname=P.name+'/'+str(f.relative_to(P)),recursive=False)
with tarfile.open(archive,'r:gz') as tar:assert len(tar.getmembers())==len(files)+1
save(P/'DELIVERY_RECEIPT.json',{'utc':utc(),'status':'COMPLETE','archive':str(archive),'archive_sha256':sha(archive),'archive_bytes':archive.stat().st_size,'files_in_manifest':len(files),'SHA256SUMS_sha256':sha(P/'SHA256SUMS'),'excluded':['model weights','full-vocabulary per-question logits','all-layer hidden states','all old assets','E1 z','runtime matplotlib cache'],'self_reference_note':'archive and this receipt are outside the internal SHA256SUMS; archive contains that manifest','TeX_compiled':False,'budget_closed':True})
print(read(P/'DELIVERY_RECEIPT.json'))
