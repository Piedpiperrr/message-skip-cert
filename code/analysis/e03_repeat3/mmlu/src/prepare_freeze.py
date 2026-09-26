from common import *
import ast,collections,subprocess
import numpy as np
from transformers import AutoTokenizer
assert not os.environ.get('CUDA_VISIBLE_DEVICES','') and not FREEZE.exists()
print('RESOLVED_PATHS',json.dumps(resolved_paths()),flush=True)
assert sha(STAGE1/'MMLU_PRO_STAGE1_PROTOCOL_FREEZE.json')==PARENT_HASH
parent=read(STAGE1/'MMLU_PRO_STAGE1_PROTOCOL_FREEZE.json');assert read(STAGE1/'NUMERICAL_VALIDATION.json')['status']=='PASS'
assert read(STAGE1/'FINAL_STATE.json')['status']=='COMPLETE_MMLU_PRO_STAGE1'
original=REVIEW/'candidates/PLAN_C/candidate_e2e128_ids.json';panelpath=P/'inputs/candidate_e2e128_ids.json';ph=sha(panelpath)
assert ph==sha(original)==sha(STAGE1/'splits/candidate_e2e128_ids.json')==parent['frozen_files']['splits/candidate_e2e128_ids.json']
assert ph==read(REVIEW/'candidates/PLAN_C/MANIFEST.json')['hashes']['candidate_e2e128_ids.json']
ii=read(panelpath);assert len(ii)==len(set(ii))==128
groups={g['representative_id']:g for g in read(STAGE1/'splits/dev_groups.json')};assert set(ii)<=set(groups)
meta={r['id']:r for r in rows(STAGE1/'inputs/queries_only.jsonl') if r['source_split']=='test'}
qh=read(STAGE1/'protocol/QUERY_IDENTITIES.json');manifest=[];queries=[]
for ordinal,ident in enumerate(ii):
    r=meta[ident];q={k:r[k] for k in ['id','question_stem','choice_labels','choice_text']}
    assert queryhash(q)==qh[ident]
    g=groups[ident];assert ident==min(g['members'],key=lambda x:int(x.split(':')[1]))
    manifest.append(dict(ordinal=ordinal,id=ident,question_id=r['question_id'],representative_id=ident,group_hash=g['group_hash'],
        category=r['category'],K=r['K'],query_sha256=qh[ident]));queries.append(q)
assert len({r['group_hash'] for r in manifest})==128
write_rows(P/'inputs/panel_queries.jsonl',queries)
first=min(read(STAGE1/f'shards/{i}/OUTCOMES_OBSERVED.json')['utc'] for i in [1,2])
mtime=datetime.datetime.fromtimestamp(original.stat().st_mtime,datetime.timezone.utc).isoformat()
review_created=read(REVIEW/'CANDIDATE_RECOMMENDATION_MANIFEST.json')['created_at_utc']
assert mtime<first and review_created<first and parent['utc']<first
save(P/'protocol/PANEL_MANIFEST.json',dict(status='FROZEN_EXISTING_CANDIDATE_NOW_AUTHORIZED_STAGE2',N=128,IDs=ii,rows=manifest,
    category_counts=dict(sorted(collections.Counter(r['category'] for r in manifest).items())),K_distribution=dict(sorted(collections.Counter(r['K'] for r in manifest).items())),
    original_candidate_path=str(original),candidate_sha256=ph,original_candidate_mtime_utc=mtime,review_recommendation_created_utc=review_created,
    parent_freeze_utc=parent['utc'],first_MMLU_Pro_outcome_utc=first,
    pre_outcome_identity_evidence='candidate hash already embedded in immutable Stage1 pre-outcome freeze and original review Plan C manifest; mtime is additional evidence',
    selection_changed=False,Stage1_score_route_correctness_used_for_selection=False))
schedule=[dict(ordinal=i,id=ident,arms=order_for(i)) for i,ident in enumerate(ii)]
save(P/'protocol/FOUR_ARM_SCHEDULE.json',schedule)
for arm in ARMS:assert [sum(r['arms'][pos]==arm for r in schedule) for pos in range(4)]==[32]*4
idx=np.random.default_rng(0).integers(0,128,size=(2000,128));np.savez_compressed(P/'protocol/bootstrap_indices.npz',ids=np.array(ii),indices=idx,seed=0)
deps=read(P/'protocol/Stage1_deployment_configs.json')['deployments']
assert sha(P/'protocol/Stage1_deployment_configs.json')==sha(STAGE1/'deployments/deployment_configs.json')
for ref in ['T','C']:assert deps[ref]['q']==.4 and deps[ref]['threshold']==THRESHOLD and deps[ref]['mode']=='selective'
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
# Exercise wrapper accounting with artificial placeholder data and fake calls;
# no model loading, forward, project answer, gold or benchmark score is used.
from execute import timed_arm
class Dummy:
    def __init__(self,u):self.u=u;self.calls=[]
    def check_hooks(self):pass
    def probe(self,q):self.calls.append('probe');return {'ProbeMax':self.u}
    def action(self,q,a):self.calls.append(a);return {'synthetic':True}
dummyq=dict(id='SYNTHETIC',question_stem='Placeholder.',choice_labels=list('ABCDEFGHIJ'),choice_text=['placeholder']*10)
for u in [0.,THRESHOLD,THRESHOLD+1e-8,1.]:
    for arm in ARMS:
        rt=Dummy(u);chosen,probe,res,parts,elapsed=timed_arm(rt,dummyq,arm,THRESHOLD,lambda:None)
        expected=('R' if u<=THRESHOLD else arm[-1]) if arm.startswith('policy') else arm[-1]
        assert chosen==expected and rt.calls==(['probe',expected] if arm.startswith('policy') else [expected])
        assert abs(sum(parts.values())-elapsed)<1e-8
source=read(P/'RUNTIME_SOURCE_INDEX.json')
for rel in ['MMLU_PRO_STAGE1_PROTOCOL_FREEZE.json','MODEL_SOURCE_INDEX.json','deployments/deployment_configs.json','src/native_runtime.py',
    'splits/candidate_e2e128_ids.json','splits/dev_groups.json','protocol/QUERY_IDENTITIES.json','FINAL_STATE.json','ARTIFACT_SHA256SUMS']:
    source[str(STAGE1/rel)]=sha(STAGE1/rel)
source[str(original)]=ph;source[str(REVIEW/'candidates/PLAN_C/MANIFEST.json')]=sha(REVIEW/'candidates/PLAN_C/MANIFEST.json')
for directory in ['actions','probes']:
    path=STAGE1/f'shards/2/{directory}/dev.jsonl';expected=read(STAGE1/'shards/2/INFERENCE_COMPLETE.json')['files'][directory+'/dev.jsonl']
    assert sha(path)==expected;source[str(path)]=expected
for path,h in source.items():assert sha(path)==h,path
save(P/'SOURCE_INDEX.json',dict(parent_Stage1=str(STAGE1),source_hashes=source))
save(P/'evidence/CPU_PREFLIGHT.json',dict(utc=utc(),status='PASS',model_loads=0,model_forwards=0,GPU_calls=0,
    panel_group_reps=128,panel_ids_unchanged=True,pre_outcome_manifest_verified=True,rotation_positions_each_arm=[32]*4,
    synthetic_wrapper_cases=16,native_runtime_byte_identical=True,parser_token_checks='K=3..10 PASS',paths=resolved_paths()))
paths=[*P.glob('src/*.py'),*P.glob('protocol/*'),*P.glob('inputs/*'),P/'run_mmlu_stage2.pbs',P/'MODEL_SOURCE_INDEX.json',P/'DATASET_SOURCE_INDEX.json',P/'RUNTIME_SOURCE_INDEX.json',P/'SOURCE_INDEX.json',P/'evidence/CPU_PREFLIGHT.json']
cfg=dict(task='P2_MMLU_PRO_E2E_STAGE2',status='PASS',utc=utc(),MMLU_PRO_STAGE2_RESULTS_OBSERVED=False,
    parent_Stage1_protocol_freeze_sha256=PARENT_HASH,Stage1_deployment_sha256=sha(STAGE1/'deployments/deployment_configs.json'),
    deployments={ref:dict(reference=deps[ref]['reference'],q=.4,threshold=THRESHOLD,comparison='u<=threshold; no panel quantile') for ref in ['T','C']},
    candidate_e2e128_manifest_sha256=ph,panel_manifest_sha256=sha(P/'protocol/PANEL_MANIFEST.json'),panel_manifest=read(P/'protocol/PANEL_MANIFEST.json'),
    models={role:{k:v for k,v in m.items() if k!='files'} for role,m in read(P/'MODEL_SOURCE_INDEX.json')['models'].items()},model_file_hash_index_sha256=sha(P/'MODEL_SOURCE_INDEX.json'),
    source_hashes=source,Stage1_native_runtime_file_unchanged=True,model_and_generation_semantics='exact Stage1 dynamic-K R/Text/C2C and FP32 ProbeMax, V2 parser, thinking off, receiver64/helper256 greedy',
    topology=dict(GPUs=2,helper='cuda:0',receiver_fuser='cuda:1',batch=1,one_residency=True,same_allocation=True),
    execution_order=dict(question_order='verbatim pre-outcome candidate ID order',arms=ARMS,rotation='left rotation by question ordinal modulo 4; each arm each position exactly 32 times',schedule_sha256=sha(P/'protocol/FOUR_ARM_SCHEDULE.json')),
    expected_counts=dict(questions=128,complete_action_requests=512,each_arm=128,online_ProbeMax=256,online_ProbeMax_each_policy=128,warmup=0,synthetic_forwards=0,retries=0),
    timing_boundary='authoritative outer perf_counter: input preparation and entry hooks; independent unchanged online ProbeMax with tokenization/transfer/full prefill/last-position lm_head/FP32 label aggregation and diagnostics; selector; complete selected native R/Text/C2C generation/decode/V2 parser/hook removal; final cleanup and two-GPU sync. Pre-request drain sync precedes timer. Disk logging/JSON serialization, gold/identity analysis and startup are excluded; startup reported separately. No KV/prefill reuse, no shared policy probe.',
    bootstrap=dict(seed=0,resamples=2000,N=128,unit='question-level paired fixed-policy saving',indices='protocol/bootstrap_indices.npz',indices_sha256=sha(P/'protocol/bootstrap_indices.npz'),generator='numpy.random.default_rng(0).integers(0,128,size=(2000,128)); same draws for the two reference-specific paired comparisons',interval='numpy.quantile(mean_savings,[.025,.975],method=linear); descriptive percentile 95%',numpy_version=np.__version__),
    positive_gate='per reference E2E_POSITIVE iff paired mean(fixed-policy)>0 and descriptive bootstrap 95% lower>0; otherwise E2E_UNCERTAIN_OR_NEGATIVE; not population guarantee',
    metrics=['N','route-to-R count and coverage','policy/fixed correct and descriptive accuracy difference','policy/fixed mean and median ms','paired saving mean and median','paired mean saving descriptive bootstrap95','probe mean ms','selector mean ms','startup separate','invalid separate from runtime failure','category/K panel distribution only'],
    identity='route reference compares same-round fixed reference; route R compares saved Stage1 native R; raw/parsed/tokens retained; differences reported without reruns; gold only linked after complete replay',
    reporting='retain first formal request and all invalid/long/mismatched items, all results positive or negative; no policy selection/calibration/subgroup guarantee/headroom analysis',
    positioning='post-hoc benchmark breadth extension; exposed development-panel E2E evidence; not sealed/independent/test confirmation/calibration/threshold selection/open-ended generalization',
    budget=dict(max_formal_PBS_jobs=1,GPUs=2,walltime='01:00:00',max_GPU_allocation_hours=2,resubmission_allowed=False),
    PBS_script_sha256=sha(P/'run_mmlu_stage2.pbs'),manuscript_or_supplement_changes=False,
    frozen_files={str(path.relative_to(P)):sha(path) for path in sorted(paths) if path.is_file()})
save(FREEZE,cfg);save(P/'evidence/FREEZE_RECEIPT.json',dict(utc=utc(),freeze_sha256=sha(FREEZE),MMLU_PRO_STAGE2_RESULTS_OBSERVED=False))
save(P/'RESOURCE_LEDGER.json',dict(status='PREPARED',utc=utc(),max_formal_PBS_jobs=1,formal_PBS_submissions=0,GPUs=2,max_GPUh=2,walltime='01:00:00'))
print('CPU_PREFLIGHT_AND_STAGE2_FREEZE_PASS',sha(FREEZE),flush=True)
