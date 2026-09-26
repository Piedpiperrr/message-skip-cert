"""Deliver only the completed preparation, preserving an explicit PARTIAL status."""
import os,json,csv,hashlib,shutil,tarfile,datetime,resource,ast
from pathlib import Path
O=Path(__file__).resolve().parent
P=Path('$DATA_DIR');T=P/O.name
STATE=P/'P2_1_20260910T041720Z/P2_STATE.md';V2=P/'P2_SCORING_V2_20260912T191445Z'
resource.setrlimit(resource.RLIMIT_AS,(512*1024*1024,512*1024*1024));resource.setrlimit(resource.RLIMIT_CPU,(30,31))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(name,obj):
    p=O/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
assert not (O/'fit_receipts.jsonl').exists() and not (O/'FITTING_COMPLETE.json').exists()
freeze=json.loads((O/'PROTOCOL_FREEZE.json').read_text());assert sha(O/'frozen_config.json')==freeze['config_sha256']
assert sha(O/'folds/group_folds.csv')==freeze['folds_sha256']
for p in O.glob('*.py'):ast.parse(p.read_text())
for p in (O/'paper').glob('*.tex'):
    s=p.read_text();assert s.count('{')==s.count('}') and s.count('\\begin{equation}')==s.count('\\end{equation}')
save('paper/inherited_V2_fragments.json',[{'path':str(p),'sha256':sha(p),'role':'completed V2 evidence, reused without rescoring'} for p in sorted((V2/'paper').glob('*.tex'))])
save('evidence/method_source_index.json',[{'path':str(p),'sha256':sha(p),'authority_note':'current user prompt overrides draft hyperparameters, gates, costs and evaluation split'} for p in [P/'P2_11_20260911T152130Z/P2_11_METHOD_DESIGN_REPORT.md',P/'P2_11_20260911T152130Z/P2_11_NEXT_EXPERIMENT_DRAFT.md']])
assets=json.loads((O/'frozen_config.json').read_text())['baseline_assets']
with (O/'MODEL_INDEX.tsv').open('w') as f:
    w=csv.writer(f,delimiter='\t');w.writerow(['pair','dataset','family','original_bundle','original_sha256','new_C_head_status','new_bundle_status'])
    for a in assets:w.writerow([a['pair'],a['dataset'],a['family'],a['source_bundle']['path'],a['source_bundle']['sha256'],'NOT_FITTED','NOT_CREATED'])
handoff=f'''P2 V2基线+FFR-E0 精简交接

状态：PARTIAL_PREPARED_NODE_CLEARANCE_REQUIRED。目录 `{T}`。
已完成：配置/组折/输出计划冻结，54项来源登记，类别计数，续接拟合代码AST检查，英文方法/协议片段。
未完成：8个C头更新0/8；OOF头0/280；拟合尝试0；新开发评价与OOF指标均未运行，不能称E0失败或方法有效。
节点：cluster-host，无PBS分配。官方一般指南不支持登录节点计算；尚未取得允许本规模任务的ClusterB适用例外。用户要求条件不足时只做准备，不自行PBS，已遵守。限制证据见 evidence/node_policy.json。
冻结配置/折表已在训练前保存。OBQA折694/693/693/693/693，ARC折224/224/224/224/223；指定重复对同折0。所有训练目标有两类；大ARC heldout折4的f_A正例0，AUC/AP预定NA，不重划。
继续时先解决实际节点使用条件，再在此目录复用 PROTOCOL_FREEZE.json、frozen_config.json、folds/。现有sharedfs环境c2c_official；run_bounded.py有节点依据检查，fit_stage.py逐头/逐折保存并复用。代码尚未数值运行；需完成定向首次验证和后续指标汇总，不能仅凭预测文件宣告完成。
新授权预算3600CPU秒/4GiB/单线程nice10，拟合最多320；当前消耗见 FINAL_RECEIPT.json。旧评分/297检查/原答/语义特征不得重跑。GPU/PBS/训练/ARC test读均0。
paper/方法与探索协议已准备，实际结果段明确未执行。P2_STATE只追加PARTIAL。此处是资源受限交接，不是科学阶段通过；Work决定资源或续接方式，不自动E1/GPU，不要求ClusterB和Work同步换会话。
'''
(O/'HANDOFF_ZH.md').write_text(handoff)
now=datetime.datetime.now(datetime.timezone.utc).isoformat()
prep=json.loads((O/'evidence/preparation_resources.json').read_text())
receipt={'status':'PARTIAL_PREPARED_NODE_CLEARANCE_REQUIRED','prepared_utc':now,'stage':str(T),'task_complete':False,
 'protocol_frozen':True,'config_sha256':freeze['config_sha256'],'fold_table_sha256':freeze['folds_sha256'],
 'baseline_C_heads_completed':0,'baseline_C_heads_planned':8,'OOF_heads_completed':0,'OOF_heads_planned':280,'LR_attempts':0,'max_LR_attempts':320,
 'new_dev_evaluation_done':False,'OOF_prediction_done':False,'scientific_conclusions':'undetermined; no execution, not negative E0 evidence',
 'code_AST_checked':True,'numerical_implementation_checked':False,'LR_models_created':0,'new_features_created':0,
 'metered_preparation_CPU_seconds':prep['cpu_seconds'],'unmetered_reads_authoring_checks_packaging_CPU_reserved_seconds':30,
 'CPU_budget_charged_seconds':prep['cpu_seconds']+30,'CPU_budget_remaining_seconds':3600-prep['cpu_seconds']-30,
 'measured_preparation_peak_RSS_KiB':prep['max_RSS_KiB'],'preparation_address_space_limit_MiB':512,
 'GPU_use':0,'PBS_submissions':0,'LLM_forward':0,'semantic_extractions':0,'ARC_test_reads':0,'environment_installs':0,
 'node':'cluster-host','actual_node_execution_eligibility':'not established for this scale; pending applicable exception/allowed execution conditions',
 'blocker_origin':'user condition on actual-node permitted scale, assessed against official the-cluster guide; not an auto-review rejection',
 'paper_tex_compiled':False,'paper_new_scientific_results':False,'remaining_work':['resolve actual-node eligibility','execute 8 C-head refits','fixed baseline dev comparison','280 OOF head fits','OOF metrics and paired decisions','scientific report/results LaTeX','completed-state synchronization'],
 'next_action':'Return to Work with frozen preparation; do not regenerate folds or launch scheduler/FFR/E1 automatically.'}
save('FINAL_RECEIPT.json',receipt);save('PROGRESS.json',{'status':receipt['status'],'completed_heads':0,'LR_attempts':0,'task_complete':False,'freeze':'PROTOCOL_FREEZE.json','next':receipt['next_action']})
block=f'''
<!-- BEGIN P2-V2-BASELINES-FFR-E0-PREP {O.name} -->
## V2基线＋FFR-E0准备（{now}，ClusterB/the execution agent）

- 状态：**PARTIAL_PREPARED_NODE_CLEARANCE_REQUIRED**，不是方法实验完成。目录 `{T}`；主报告 `P2_V2_BASELINES_FFR_E0_REPORT_ZH.md`，交接 `HANDOFF_ZH.md`。
- 已在任何新拟合/新开发评价前冻结本轮配置、共享重复组隔离5折、输出计划和来源。config SHA256 `{freeze['config_sha256']}`，fold SHA256 `{freeze['folds_sha256']}`。OBQA各折694/693/693/693/693，ARC224/224/224/224/223，MEA_2011_8_8/MEA_2012_5_8同折0。无结果驱动分层/挪样本。
- 8个C头更新 **0/8**，OOF头 **0/280**，LR尝试 **0**；原router仍全部旧标签训练。训练折七目标均有两类；大ARC评价折4的f_A为0/223，预定AUC/AP=NA，不重划折。
- 资源限制：当前cluster-host，无PBS分配；官方the-cluster一般指导不支持登录节点计算，未确认允许本次288拟合/3600CPU秒规模的ClusterB适用例外。仅完成轻量准备，未自行提交PBS/连接计算节点，未操作他人作业。见 evidence/node_policy.json。不是管理员单独拒绝或工具自动审批拒绝。
- 当前CPU预算计账{receipt['CPU_budget_charged_seconds']:.3f}/3600秒（含30秒未计量准备/打包预留）；GPU/PBS/LLM前向/新语义特征/ARC test/安装均0。评分V2/297检查/原答未重跑。
- 可续接代码 fit_stage.py、run_bounded.py 仅通过AST检查，尚未数值验证。共享折内TF-IDF、全新OOF七头、折内train panel均值成本、固定λ全报、常数翻转/真实翻转代入均按本轮用户修订协议定义；无C网格/G1G2/开发FFR。paper/已有英文候选及前瞻协议，无新效果主张。
- 下一步：Work解决实际节点条件后接续此冻结目录，完成拟合、指标与论文结果；不重划、不重评分、不把PARTIAL写成完成。当前资源受限交接不证明E0无效；不自动E1/GPU，不要求ClusterB与Work同步迁移。
<!-- END P2-V2-BASELINES-FFR-E0-PREP {O.name} -->
'''
(O/'P2_STATE_APPEND.md').write_text(block)
# Synchronize only this new stage and append the precise status block to the sole state file.
for p in O.rglob('*'):
    if p.is_file() and p.suffix not in ['.gz']:
        d=T/p.relative_to(O);d.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,d);assert sha(p)==sha(d)
before=STATE.read_bytes();marker=('<!-- BEGIN P2-V2-BASELINES-FFR-E0-PREP '+O.name+' -->').encode()
assert marker not in before,'Already appended; reuse receipt rather than append duplicate'
with STATE.open('ab') as f:f.write(block.encode());f.flush();os.fsync(f.fileno())
after=STATE.read_bytes();assert after==before+block.encode()
save('evidence/state_sync_receipt.json',{'only_append':True,'original_prefix_preserved':True,'before_sha256':hashlib.sha256(before).hexdigest(),'after_sha256':hashlib.sha256(after).hexdigest(),'path':str(STATE)})
shutil.copy2(O/'evidence/state_sync_receipt.json',T/'evidence/state_sync_receipt.json')
files=[p for p in T.rglob('*') if p.is_file() and p.name not in ['FILE_INDEX.tsv','BUNDLE_VALIDATION.json'] and p.suffix!='.gz']
for root in [O,T]:
    with (root/'FILE_INDEX.tsv').open('w') as f:
        w=csv.writer(f,delimiter='\t');w.writerow(['path','bytes','sha256'])
        for p in sorted(files):w.writerow([str(p.relative_to(T)),p.stat().st_size,sha(p)])
files.append(T/'FILE_INDEX.tsv');bundle=T/'P2_V2_BASELINES_FFR_E0_PREPARATION_BUNDLE.tar.gz'
with tarfile.open(bundle,'w:gz') as tar:
    for p in sorted(files):tar.add(p,arcname=str(p.relative_to(T)),recursive=False)
with tarfile.open(bundle,'r:gz') as tar:
    for m in tar.getmembers():assert hashlib.sha256(tar.extractfile(m).read()).hexdigest()==sha(T/m.name)
save('BUNDLE_VALIDATION.json',{'path':str(bundle),'sha256':sha(bundle),'bytes':bundle.stat().st_size,'members':len(files),'contains_models_or_features':False,'stage_is_partial':True})
shutil.copy2(O/'BUNDLE_VALIDATION.json',T/'BUNDLE_VALIDATION.json');shutil.copy2(bundle,O/bundle.name)
print(json.dumps({'status':receipt['status'],'report':str(T/'P2_V2_BASELINES_FFR_E0_REPORT_ZH.md'),'bundle':str(bundle),'CPU_charged_seconds':receipt['CPU_budget_charged_seconds'],'fit_attempts':0,'state_appended':True},ensure_ascii=False,indent=2))
