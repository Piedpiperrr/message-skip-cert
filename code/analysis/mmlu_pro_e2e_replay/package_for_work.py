"""Stage2 结束后的 CPU 交付封装；不执行推理、调度或新科学分析。"""
import sys, shutil, zipfile
from pathlib import Path
sys.dont_write_bytecode=True
sys.path.insert(0,str(Path(__file__).resolve().parent/'src'))
from common import P,DATA_ROOT,read,save,sha,utc,verify_freeze

assert sha(P/'MMLU_PRO_E2E_STAGE2_FREEZE.json')=='e13529cf9eff820fef94639530bf750aa6ed8140d853e8d119e03a62d9969ea6'
verify_freeze()
assert read(P/'NUMERICAL_VALIDATION.json')['status']=='PASS'
assert read(P/'evidence/FINAL_NUMERICAL_AUDIT.json')['status']=='PASS'
state=read(P/'FINAL_STATE.json');assert state['status']=='COMPLETE_MMLU_PRO_STAGE2'
resource=read(P/'RESOURCE_LEDGER.json');assert resource['job_state']=='F' and resource['exit_status']==0
run=DATA_ROOT/'runs/iclr2027_p2'/f"{resource['job_id']}_mmlu_stage2"
logdir=P/'evidence/runtime_logs';logdir.mkdir(exist_ok=True)
logindex=[]
for name in ['entry.log','outer.log','job_exit.txt','home_space_check.log']:
    source=run/name;target=logdir/name
    shutil.copy2(source,target)
    assert sha(source)==sha(target)
    logindex.append(dict(source=str(source),copy=str(target.relative_to(P)),sha256=sha(target),bytes=target.stat().st_size))
save(P/'evidence/RUNTIME_LOG_INDEX.json',logindex)
resource['allocation_accounting_note_zh']='以 PBS stime 至 obittime 的574秒乘实际分配2 GPUs，保守核算为0.3188888888888889 GPUh。原始 resources_used.walltime 为566秒，ngpus字段为0；GPU分配以 exec_vnode 和 CUDA 设备数为准，原始字段不改写。'
save(P/'RESOURCE_LEDGER.json',resource)
save(P/'evidence/FINAL_EDITORIAL_REVIEW.json',dict(utc=utc(),status='PASS',
    frozen_sources_verified_again=True,numerical_results_unchanged=True,
    changes_zh=['明确 paired median saving 为负及其含义','解释 allocation GPUh 与 PBS 原始使用量字段','将 identity 差异计数写为0/256以免误读','更新完成状态并封装交付'],
    inference_requests_added=0,PBS_submissions_added=0,policy_selection_added=False,analysis_gate_changed=False,
    V4_modified=False,supplement_modified=False,next_task_started=False))
guide='''# Work 交付阅读顺序

最终状态：COMPLETE_MMLU_PRO_STAGE2。

1. HANDOFF_ZH.md：结论和资源摘要。
2. REPORT_ZH.md：冻结身份、计时、数值、限制与五个回答。
3. summary/mmlu_pro_e2e_summary.csv 与 paired_latency_bootstrap.csv：两种 reference 的完整主指标。
4. NUMERICAL_VALIDATION.json 与 evidence/FINAL_NUMERICAL_AUDIT.json：完整性和独立复核。
5. MMLU_PRO_E2E_STAGE2_FREEZE.json、protocol/、inputs/：结果前固定身份。
6. records/：512 条四臂请求、256 条独立 probe，以及后验 gold 关联和配对数据。
7. evidence/：PBS、模型加载、原始 runtime logs 和冻结来源检查。

归档 P2_MMLU_PRO_STAGE2_WORK_BUNDLE.zip 包含上述文件、源代码和 ARTIFACT_SHA256SUMS。records 在工作目录是 sharedfs run 的链接，在 ZIP 中为实际文件。未打包模型权重、整个父项目或全量数据集；外部依赖的精确路径/hash 见 source indexes。

ARTIFACT_SHA256SUMS 不包含其自身、归档、归档校验文件、DELIVERY_RECEIPT.json 或进程锁文件；归档校验和与交付回执置于归档外，避免循环引用。归档经过逐成员 SHA256 与 ZIP CRC 验证。

仅交付本轮 Stage2。Text 正收益，C2C 未通过正收益门槛，二者均完整报告。停止并交回 Work，不启动后续任务。
'''
(P/'README_DELIVERY_ZH.md').write_text(guide)
for name in ['REPORT_ZH.md','HANDOFF_ZH.md']:
    f=P/name;s=f.read_text()
    if 'P2_MMLU_PRO_STAGE2_WORK_BUNDLE.zip' not in s:
        s+='\n交付包：`P2_MMLU_PRO_STAGE2_WORK_BUNDLE.zip`；阅读顺序见 `README_DELIVERY_ZH.md`，逐文件校验见 `ARTIFACT_SHA256SUMS`。\n'
        f.write_text(s)
archive=P/'P2_MMLU_PRO_STAGE2_WORK_BUNDLE.zip'
excluded={'ARTIFACT_SHA256SUMS',archive.name,archive.name+'.sha256','DELIVERY_RECEIPT.json'}
files={}
for root in [P,P/'records']:
    for f in root.rglob('*'):
        if f.is_file() and f.name not in excluded and f.suffix!='.lock' and '__pycache__' not in f.parts:
            files[str(f.relative_to(P))]=f
assert 'records/four_arm_requests.jsonl' in files and 'records/two_policy_probes.jsonl' in files
hashes={rel:sha(f) for rel,f in sorted(files.items())}
manifest=P/'ARTIFACT_SHA256SUMS'
manifest.write_text(''.join(f'{h}  {rel}\n' for rel,h in hashes.items()))
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    for rel,f in sorted(files.items()):z.write(f,rel)
    z.write(manifest,manifest.name)
import hashlib
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None
    assert len(z.namelist())==len(set(z.namelist()))==len(files)+1
    for rel,h in hashes.items():assert hashlib.sha256(z.read(rel)).hexdigest()==h,rel
    assert z.read(manifest.name)==manifest.read_bytes()
archive_hash=sha(archive)
(P/(archive.name+'.sha256')).write_text(f'{archive_hash}  {archive.name}\n')
save(P/'DELIVERY_RECEIPT.json',dict(utc=utc(),status='PASS',archive=archive.name,sha256=archive_hash,
    bytes=archive.stat().st_size,member_count=len(files)+1,hashed_artifacts=len(hashes),
    zip_CRC_verified=True,all_member_SHA256_verified=True,records_materialized_in_archive=True,
    stage2_status=state['status'],MMLU_TEXT_E2E=state['MMLU_TEXT_E2E'],MMLU_C2C_E2E=state['MMLU_C2C_E2E'],
    no_additional_inference=True,no_additional_PBS=True,next_task_started=False))
print('交付封装及校验通过：',archive.name,archive.stat().st_size,'bytes;',len(files)+1,'files; SHA256',archive_hash)
