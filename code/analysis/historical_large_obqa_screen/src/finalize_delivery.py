# Light packaging/metadata validation only. Does not execute numerical methods.
from common import *
import tarfile,shutil,ast
assert read(P/'EXECUTION_COMPLETE.json')['dev']==742
res=read(P/'RESOURCE_RECEIPT.json');assert res['status']=='F' and res['exit_status']==0
# Freeze manifest validation, source syntax, row-key/count checks; no refit/recalibration/bootstrap.
freezes=['SPLIT_FREEZE.json','PROTOCOL_FREEZE.json','IMPLEMENTATION_FREEZE.json','RANDOM_FREEZE.json','TARGET_INTERFACE_FREEZE.json','THRESHOLDS_FREEZE.json','DEPLOYMENT_FREEZE.json','DEV_FEATURES_COMPLETE.json','DEV_ROUTES_FREEZE.json','ANALYSIS_COMPLETE.json','FIGURES_COMPLETE.json']
for name in freezes:
 for f,h in read(P/name)['files'].items():assert sha(P/f)==h,(name,f)
for f in (P/'src').glob('*.py'):ast.parse(f.read_text(),filename=str(f))
for f,n in [('records/dev_scored_routes.jsonl',742),('records/dev_grid_routes.jsonl',742),('records/dev_per_question.jsonl',5194)]:assert len(jl(P/f))==n,f
features=list(csv.DictReader((P/'features/DEV_FEATURE_INDEX.csv').open()));assert len(features)==742
for row in features:assert sha(row['path'])==row['sha256']
assert len(list(csv.DictReader((P/'summary/calibration_100.csv').open())))==100
assert len(list(csv.DictReader((P/'models/MODEL_INDEX.csv').open())))==4
sourcehashes={r['path']:r['sha256'] for r in csv.DictReader((P/'SOURCE_INDEX.csv').open())}
for p,h in sourcehashes.items():assert sha(p)==h,('historical source changed',p)
metadata={'status':'COMPLETE','task':'P2_RISK_CALIBRATION_BINARY_PILOT','stage':P.name,'utc':utc(),'heads':4,'calibration_tests':100,'dev':742,'prefill_attempts':742,'prefill_success':742,'dev_cache_reused':0,'deployments':5,'new_protocol_requests':0,'new_helper_forward':0,'new_generation':0,'job_id':res['job_id'],'job_state':'F','exit_status':0,'CPU_charged_seconds':res['CPU_charged_with_60s_preparation_reporting_reserve'],'GPU_requested_allocation_hours':.5,'GPU_actual_allocation_hours':res['actual_GPU_allocation_hours_stime_to_obittime'],'scientific_scope':'exploratory supervision/calibration variant of binary FFR','config_sha256':sha(P/'frozen_config.json'),'freeze_sha256':{f:sha(P/f) for f in freezes},'TeX_compiled':False,'sbank_charge':None,'budget_closed':True,'no_second_job':True,'next_action':'Return to Work; no automatic new experiment'}
save(P/'FINAL_RECEIPT.json',metadata)
save(P/'evidence/DELIVERY_VALIDATION.json',{'utc':utc(),'freeze_manifests_verified':len(freezes),'all_742_dev_feature_hashes_verified':True,'old_indexed_source_hashes_unchanged':True,'syntax_checked':True,'row_counts_checked':True,'numerical_validation':'evidence/NUMERICAL_VALIDATION.json','visual_check':'evidence/FIGURE_VISUAL_CHECK.json','TeX_status':'source only, unavailable engine','no_new_numerical_run':True})
# Append only, preserve prior state byte-for-byte and verify the prefix.
state=ROOT/'P2_1_20260910T041720Z/P2_STATE.md';before=state.read_bytes();before_hash=hashlib.sha256(before).hexdigest()
marker=f'<!-- COMPLETE {P.name} -->'
assert marker.encode() not in before
entry=f'''\n\n{marker}
## {utc()} — {P.name} COMPLETE，交回Work

- 唯一授权二元任务完成：4新LR头/4拟合、100项Bonferroni校准、742dev、742prefill尝试/742成功/0dev缓存复用、5冻结部署点（D/R/H选择性，Diff/Random固定Text）；无helper前向、答案生成或新协议请求。复用3466train E1特征和6932历史R/T协议请求，后者不是LLM前向次数。
- 新划分fit2100/cal1366，规范化题干+有序选项无train/dev内或跨集合重复；seed0不看d/gold。alpha=.05、delta=.10、M100，阈值fit分位数，cal接受最大q。原历史曝光身份不变，非未曝光确认集。
- D冻结q=.30，cal 6/380、p=.000409609、校正CP上界.046781；dev 230/742路由、6改变、643正确，组件重组797.166ms/题，比Text净省178.598ms，U=.836204。correctness-R q=.40，291路由、7改变、644正确、740.087ms、U=.839727。支持分歧监督查询排序及可用成本工作点，不支持优于同规则gold基线或已成立原创贡献。
- 主要风险只为条件解析答案改变率；dev72/742真实分歧基率由新统计得到。主要成本为新特征时间+历史完整固定请求组件重组，不替换旧E2E身份；全部描述区间保留历史曝光/选择限制。
- 作业 {res['job_id']} 已F/0。申请gpu-queue select1×1800s=.5 GPU allocation hour；实际分配298s=.082778 GPU allocation hour（scheduler wall292s）。CPU保守计账{res['CPU_charged_with_60s_preparation_reporting_reserve']:.6f}/1200s（含60s准备报告预留），预算关闭。sbank收费NA，TeX环境不可用未编译。禁止第二作业、续预算、重复成功id。
- 新目录 `{P}`。配置SHA256 `{sha(P/'frozen_config.json')}`；FINAL_RECEIPT、中文报告/HANDOFF、英文paper/、风险覆盖图、四头、逐题数据、资源账、源码、SHA256SUMS与轻量包齐备。新dev z留ClusterB，轻量包仅含其路径/索引/哈希。原冻结目录和历史状态前缀保持不变。
- 停止本轮执行，交回Work；不自动四动作、改校准器、换数据集或下一实验。
'''
with state.open('ab') as f:f.write(entry.encode())
after=state.read_bytes();assert after[:len(before)]==before
save(P/'evidence/P2_STATE_APPEND_RECEIPT.json',{'path':str(state),'before_sha256':before_hash,'before_bytes':len(before),'after_sha256':sha(state),'after_bytes':len(after),'prefix_unchanged':True,'marker':marker,'utc':utc()})
(P/'SESSION_RESUME_ZH.md').write_text('本轮COMPLETE，唯一PBS185721已F/0，预算关闭；不续跑、不重采成功id。\n入口HANDOFF_ZH.md、FINAL_RECEIPT.json、RESOURCE_RECEIPT.json。已完成4头/100校准/742dev，prefill尝试=成功=742。\n所有阶段冻结哈希见FINAL_RECEIPT；新dev z路径及哈希见features/DEV_FEATURE_INDEX.csv。剩余本轮授权作业数0，禁止换会话恢复旧预算。\n英文片段与中文主报告已完成；TeX不可用未编译，sbank收费NA。完成交回Work，不自动下一实验。\n')
# Full-stage integrity manifest includes ClusterB-only dev vectors. Exclude manifest itself and delivery artifacts.
def excluded(p):return '__pycache__' in p.parts or 'matplotlib-cache' in p.parts or p.suffix in ['.lock','.tmp'] or p.name in ['SHA256SUMS','DELIVERY_RECEIPT.json','WORK_BUNDLE_SHA256SUMS'] or p.name.endswith('.tar.gz')
allfiles=[p for p in sorted(P.rglob('*')) if p.is_file() and not excluded(p)]
(P/'SHA256SUMS').write_text(''.join(f'{sha(p)}  {p.relative_to(P)}\n' for p in allfiles))
# Index explicitly enumerates omitted vectors for the portable artifact.
portable=[p for p in allfiles if not (p.parent==P/'features/dev')]
bundle=P/(P.name+'_WORK_LIGHT.tar.gz')
portable.append(P/'SHA256SUMS')
(P/'WORK_BUNDLE_SHA256SUMS').write_text(''.join(f'{sha(p)}  {p.relative_to(P)}\n' for p in portable))
portable.append(P/'WORK_BUNDLE_SHA256SUMS')
with tarfile.open(bundle,'w:gz') as tar:
 for p in portable:tar.add(p,arcname=str(Path(P.name)/p.relative_to(P)),recursive=False)
with tarfile.open(bundle,'r:gz') as tar:
 members=tar.getmembers();assert not any('/features/dev/' in m.name for m in members);assert all(m.size<100*1024**2 for m in members)
 expected={str(Path(P.name)/p.relative_to(P)):sha(p) for p in portable}
 for m in members:assert hashlib.sha256(tar.extractfile(m).read()).hexdigest()==expected[m.name]
save(P/'DELIVERY_RECEIPT.json',{'status':'COMPLETE','bundle':str(bundle),'bytes':bundle.stat().st_size,'sha256':sha(bundle),'portable_file_count':len(portable),'bundle_content_hashes_verified':True,'full_manifest_sha256':sha(P/'SHA256SUMS'),'portable_manifest_sha256':sha(P/'WORK_BUNDLE_SHA256SUMS'),'full_manifest_includes_omitted_ClusterB_dev_z':True,'portable_manifest_only_bundle_members':True,'omitted_dev_z_files':742,'dev_feature_index':str(P/'features/DEV_FEATURE_INDEX.csv'),'large_model_checkpoints_included':False,'utc':utc()})
print(json.dumps(read(P/'DELIVERY_RECEIPT.json'),indent=2));print('STATE_APPEND_PREFIX_UNCHANGED',before_hash)
