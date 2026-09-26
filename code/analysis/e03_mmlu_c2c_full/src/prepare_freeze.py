"""E3 FULL: new pre-request freeze + model-free CPU preflight for the 2,641-question two-arm C2C replay.
Adapted from the original Stage2 prepare_freeze.py: panel = all development group representatives in frozen Stage1
order; arms fixed_C/policy_C alternating first per question; bootstrap default_rng(0).integers(0,N,(2000,N));
counts derived from the list length; q=.40 threshold unchanged. No model load, forward, gold or outcome read."""
from common import *
import ast,collections,subprocess
import numpy as np
from transformers import AutoTokenizer
assert not os.environ.get('CUDA_VISIBLE_DEVICES','') and not FREEZE.exists()
assert ARMS==['fixed_C','policy_C']
print('RESOLVED_PATHS',json.dumps(resolved_paths()),flush=True)
assert sha(STAGE1/'MMLU_PRO_STAGE1_PROTOCOL_FREEZE.json')==PARENT_HASH
parent=read(STAGE1/'MMLU_PRO_STAGE1_PROTOCOL_FREEZE.json');assert read(STAGE1/'NUMERICAL_VALIDATION.json')['status']=='PASS'
assert read(STAGE1/'FINAL_STATE.json')['status']=='COMPLETE_MMLU_PRO_STAGE1'
groups_path=STAGE1/'splits/dev_groups.json';gh=sha(groups_path)
assert gh==parent['frozen_files']['splits/dev_groups.json'],'dev_groups.json must be the Stage1-frozen split'
dev_groups=read(groups_path);ii=[g['representative_id'] for g in dev_groups];N=len(ii)
assert N==len(set(ii))==2641
groups={g['representative_id']:g for g in dev_groups}
meta={r['id']:r for r in rows(STAGE1/'inputs/queries_only.jsonl') if r['source_split']=='test'}
qh=read(STAGE1/'protocol/QUERY_IDENTITIES.json');manifest=[];queries=[]
for ordinal,ident in enumerate(ii):
    r=meta[ident];q={k:r[k] for k in ['id','question_stem','choice_labels','choice_text']}
    assert queryhash(q)==qh[ident]
    g=groups[ident];assert ident==min(g['members'],key=lambda x:int(x.split(':')[1]))
    manifest.append(dict(ordinal=ordinal,id=ident,question_id=r['question_id'],representative_id=ident,group_hash=g['group_hash'],
        category=r['category'],K=r['K'],query_sha256=qh[ident]));queries.append(q)
assert len({r['group_hash'] for r in manifest})==N
(P/'inputs').mkdir(exist_ok=True);save(P/'inputs/panel_ids.json',ii);write_rows(P/'inputs/panel_queries.jsonl',queries)
save(P/'protocol/PANEL_MANIFEST.json',dict(status='E3_FULL_ALL_DEVELOPMENT_GROUP_REPRESENTATIVES',N=N,IDs=ii,rows=manifest,
    category_counts=dict(sorted(collections.Counter(r['category'] for r in manifest).items())),K_distribution=dict(sorted(collections.Counter(r['K'] for r in manifest).items())),
    source=str(groups_path),source_sha256=gh,order='frozen Stage1 dev_groups.json representative order',
    selection='all development group representatives; no subset selection',selection_changed=False,Stage1_score_route_correctness_used_for_selection=False))
schedule=[dict(ordinal=i,id=ident,arms=order_for(i)) for i,ident in enumerate(ii)]
save(P/'protocol/ARM_SCHEDULE.json',schedule)
assert [r['arms'] for r in schedule[:2]]==[['fixed_C','policy_C'],['policy_C','fixed_C']]
first_counts={arm:sum(r['arms'][0]==arm for r in schedule) for arm in ARMS};assert max(first_counts.values())-min(first_counts.values())<=1
idx=np.random.default_rng(0).integers(0,N,size=(2000,N));np.savez_compressed(P/'protocol/bootstrap_indices.npz',ids=np.array(ii),indices=idx,seed=0)
deps=read(P/'protocol/Stage1_deployment_configs.json')['deployments']
assert sha(P/'protocol/Stage1_deployment_configs.json')==sha(STAGE1/'deployments/deployment_configs.json')
assert deps['C']['q']==.4 and deps['C']['threshold']==THRESHOLD and deps['C']['mode']=='selective'
assert sha(P/'src/native_runtime.py')==sha(STAGE1/'src/native_runtime.py')
for file in (P/'protocol').glob('*'):
    if (STAGE1/'protocol'/file.name).is_file():assert sha(file)==sha(STAGE1/'protocol'/file.name)
for f in (P/'src').glob('*.py'):ast.parse(f.read_text())
subprocess.run(['bash','-n',str(P/'run_mmlu_stage2.pbs')],check=True)
parser=load_module(P/'protocol/scoring_v2.py','preflight_parser');tok=AutoTokenizer.from_pretrained(read(P/'MODEL_SOURCE_INDEX.json')['models']['receiver']['path'],local_files_only=True)
sets=read(P/'protocol/label_token_sets.json')
for K in range(3,11):
    labels=list('ABCDEFGHIJ')[:K]
    for label in labels:
        assert len(tok.encode(label,add_special_tokens=False))==1
        assert parser.parse_answer('The correct answer is '+label,labels)['answer']==label
        assert all(tok.decode([i],skip_special_tokens=False,clean_up_tokenization_spaces=False).strip()==label for i in sets[label])
    assert not parser.parse_answer('The correct answer is '+chr(65+K),labels)['valid']
    assert not parser.parse_answer('The correct answer is A or B',labels)['valid']
from execute import timed_arm
class Dummy:
    def __init__(self,u):self.u=u;self.calls=[]
    def check_hooks(self):pass
    def probe(self,q):self.calls.append('probe');return {'ProbeMax':self.u}
    def action(self,q,a):self.calls.append(a);return {'synthetic':True}
dummyq=dict(id='SYNTHETIC',question_stem='Placeholder.',choice_labels=list('ABCDEFGHIJ'),choice_text=['placeholder']*10)
cases=0
for u in [0.,THRESHOLD,THRESHOLD+1e-8,1.]:
    for arm in ARMS:
        rt=Dummy(u);chosen,probe,res,parts,elapsed=timed_arm(rt,dummyq,arm,THRESHOLD,lambda:None)
        expected=('R' if u<=THRESHOLD else arm[-1]) if arm.startswith('policy') else arm[-1]
        assert chosen==expected and rt.calls==(['probe',expected] if arm.startswith('policy') else [expected])
        assert abs(sum(parts.values())-elapsed)<1e-8;cases+=1
source=read(P/'RUNTIME_SOURCE_INDEX.json')
for rel in ['MMLU_PRO_STAGE1_PROTOCOL_FREEZE.json','MODEL_SOURCE_INDEX.json','deployments/deployment_configs.json','src/native_runtime.py',
    'splits/dev_groups.json','protocol/QUERY_IDENTITIES.json','inputs/queries_only.jsonl','FINAL_STATE.json','ARTIFACT_SHA256SUMS']:
    source[str(STAGE1/rel)]=sha(STAGE1/rel)
for directory in ['actions','probes']:
    path=STAGE1/f'shards/2/{directory}/dev.jsonl';expected=read(STAGE1/'shards/2/INFERENCE_COMPLETE.json')['files'][directory+'/dev.jsonl']
    assert sha(path)==expected;source[str(path)]=expected
for path,h in source.items():assert sha(path)==h,path
save(P/'SOURCE_INDEX.json',dict(parent_Stage1=str(STAGE1),source_hashes=source))
save(P/'evidence/CPU_PREFLIGHT.json',dict(utc=utc(),status='PASS',model_loads=0,model_forwards=0,GPU_calls=0,
    panel_group_reps=N,panel_order='frozen Stage1 dev_groups representative order',first_arm_counts=first_counts,
    synthetic_wrapper_cases=cases,native_runtime_byte_identical=True,parser_token_checks='K=3..10 PASS',paths=resolved_paths()))
paths=[*P.glob('src/*.py'),*P.glob('protocol/*'),*P.glob('inputs/*'),P/'run_mmlu_stage2.pbs',P/'MODEL_SOURCE_INDEX.json',P/'DATASET_SOURCE_INDEX.json',P/'RUNTIME_SOURCE_INDEX.json',P/'SOURCE_INDEX.json',P/'evidence/CPU_PREFLIGHT.json']
cfg=dict(task='P2_R1_E3_MMLU_C2C_FULL',status='PASS',utc=utc(),MMLU_PRO_STAGE2_RESULTS_OBSERVED=False,
    parent_Stage1_protocol_freeze_sha256=PARENT_HASH,Stage1_deployment_sha256=sha(STAGE1/'deployments/deployment_configs.json'),
    deployments={'C':dict(reference=deps['C']['reference'],q=.4,threshold=THRESHOLD,comparison='u<=threshold; no panel quantile')},
    panel_source_sha256=gh,panel_manifest_sha256=sha(P/'protocol/PANEL_MANIFEST.json'),
    models={role:{k:v for k,v in m.items() if k!='files'} for role,m in read(P/'MODEL_SOURCE_INDEX.json')['models'].items()},model_file_hash_index_sha256=sha(P/'MODEL_SOURCE_INDEX.json'),
    source_hashes=source,Stage1_native_runtime_file_unchanged=True,model_and_generation_semantics='exact Stage1 dynamic-K R/C2C and FP32 ProbeMax, V2 parser, thinking off, receiver64 greedy',
    topology=dict(GPUs=2,helper='cuda:0',receiver_fuser='cuda:1',batch=1,one_residency=True,same_allocation=True,node='exclusive node-queue 8-GPU node; GPUs 2-7 idle'),
    execution_order=dict(question_order='frozen Stage1 dev_groups representative order (all development group representatives)',arms=ARMS,rotation='alternating per question ordinal: even fixed_C first, odd policy_C first',schedule_sha256=sha(P/'protocol/ARM_SCHEDULE.json')),
    expected_counts=dict(questions=N,complete_action_requests=N*len(ARMS),each_arm=N,online_ProbeMax=N,online_ProbeMax_each_policy=N,warmup=0,synthetic_forwards=0,retries=0),
    timing_boundary='authoritative outer perf_counter: input preparation and entry hooks; independent unchanged online ProbeMax with tokenization/transfer/full prefill/last-position lm_head/FP32 label aggregation and diagnostics; selector; complete selected native R/Text/C2C generation/decode/V2 parser/hook removal; final cleanup and two-GPU sync. Pre-request drain sync precedes timer. Disk logging/JSON serialization, gold/identity analysis and startup are excluded; startup reported separately. No KV/prefill reuse, no shared policy probe.',
    bootstrap=dict(seed=0,resamples=2000,N=N,unit='question-level paired fixed-policy saving',indices='protocol/bootstrap_indices.npz',indices_sha256=sha(P/'protocol/bootstrap_indices.npz'),generator=f'numpy.random.default_rng(0).integers(0,{N},size=(2000,{N}))',interval='numpy.quantile(mean_savings,[.025,.975],method=linear); descriptive percentile 95%',numpy_version=np.__version__),
    positive_gate='E2E_POSITIVE iff paired mean(fixed-policy)>0 and descriptive bootstrap 95% lower>0; otherwise E2E_UNCERTAIN_OR_NEGATIVE; not population guarantee',
    identity='route C compares same-round fixed C2C; route R compares saved Stage1 native R; raw/parsed/tokens retained; differences reported without reruns; gold only linked after complete replay',
    reporting='records only inside the job; retain first formal request and all invalid/long/mismatched items; analysis later on the login node',
    positioning='E3 reviewer request: full development-population E2E for the C2C reference; exposed development data; not sealed/test confirmation',
    budget=dict(max_formal_PBS_jobs=1,queue='node-queue',select=1,replay_GPUs=2,walltime='01:00:00',resubmission_allowed=False),
    PBS_script_sha256=sha(P/'run_mmlu_stage2.pbs'),manuscript_or_supplement_changes=False,
    frozen_files={str(path.relative_to(P)):sha(path) for path in sorted(paths) if path.is_file()})
save(FREEZE,cfg);save(P/'evidence/FREEZE_RECEIPT.json',dict(utc=utc(),freeze_sha256=sha(FREEZE),MMLU_PRO_STAGE2_RESULTS_OBSERVED=False))
save(P/'RESOURCE_LEDGER.json',dict(status='PREPARED',utc=utc(),max_formal_PBS_jobs=1,formal_PBS_submissions=0,queue='node-queue',select=1,walltime='01:00:00'))
print('CPU_PREFLIGHT_AND_E3_FULL_FREEZE_PASS',N,sha(FREEZE),flush=True)
