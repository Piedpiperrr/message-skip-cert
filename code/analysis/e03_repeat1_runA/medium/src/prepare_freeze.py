"""Read-only provenance/local hash validation and pre-request Stage 2 freeze."""
from common import *
import shutil,ast
assert not FREEZE.exists(),'Never overwrite the Stage 2 freeze'
assert not (P/'records/attempts.jsonl').exists()
print('RESOLVED_PATHS',json.dumps(paths()),flush=True)
start=time.perf_counter();sources={}
def source(path,role):
    path=Path(path).resolve();sources[str(path)]=dict(path=str(path),sha256=sha(path),bytes=path.stat().st_size,
        mtime_ns=path.stat().st_mtime_ns,role=role)
    return path
B=ROOT/'P2_CONFIDENCE_REFERENCE_BOUNDARIES_20260914T165012Z'
E2E=ROOT/'P2_FROZEN_POLICY_E2E_VALIDATION_20260914T174120Z'
AUDIT=ROOT/'P2_COMPLEMENTARITY_HEADROOM_AUDIT_20260915T201741Z'
assert sha(source(PARENT/'MEDIUM_PAIR_PROTOCOL_FREEZE.json','parent scientific freeze'))==PARENT_HASH
source(STAGE1/'MODEL_SOURCE_INDEX.json','parent official model manifest plus prior local verification')
old_ex=read(source(STAGE1/'MEDIUM_PAIR_EXECUTION_FREEZE_RETRY1.json','successful original runtime identity'))
c10=read(source(NATIVE/'frozen_config.json','original historical timing panel IDs only'))
old_freeze=read(source(E2E/'PROTOCOL_FREEZE.json','historical pre-medium E2E panel freeze'))
assert old_freeze['utc']<read(PARENT/'MEDIUM_PAIR_PROTOCOL_FREEZE.json')['utc']
deps={};panels={};expected=[];gold=[]
for ds,q in [('obqa',.55),('arc',.60)]:
    oldids=read(source(B/f'inputs/{ds}_panel_ids.json','pre-medium small/large historical panel identity'))['dev']
    ids=read(source(E2E/f'inputs/{ds}_panel_ids.json','large E2E exact 128-panel order'))
    assert ids==oldids==c10['cost_panel'][ds]['dev' if ds=='obqa' else 'validation']['ids'] and len(set(ids))==128
    shutil.copy2(E2E/f'inputs/{ds}_panel_ids.json',P/f'inputs/{ds}_panel_ids.json')
    pp=rows(source(E2E/f'inputs/{ds}_queries.jsonl','gold-free original panel questions in original order'))
    assert [r['id'] for r in pp]==ids and all(set(r)=={'id','question_stem','choice_labels','choice_text'} for r in pp)
    qm={r['id']:r for r in rows(source(PARENT/f'inputs/{ds}_dev_queries.jsonl','medium full-dev query identity only'))}
    assert all(all(r[k]==qm[r['id']][k] for k in ['id','question_stem','choice_labels','choice_text']) for r in pp)
    signatures=[' '.join((r['question_stem']+' '+' '.join(r['choice_text'])).split()) for r in pp]
    assert len(set(signatures))==128
    shutil.copy2(E2E/f'inputs/{ds}_queries.jsonl',P/f'inputs/{ds}_queries.jsonl')
    dep_path=source(STAGE1/f'deployments/{ds}_C.json','frozen C2C deployment; full precision threshold')
    d=read(dep_path);assert d['mode']=='selective' and d['q']==q
    assert d['threshold']=={'obqa':1.3113021850585938e-6,'arc':3.5762786865234375e-7}[ds]
    shutil.copy2(dep_path,P/f'protocol/{ds}_C_deployment.json')
    deps[ds]=dict(q=d['q'],threshold=d['threshold'],comparison='u <= threshold; all ties',source=str(dep_path),source_sha256=sha(dep_path))
    panels[ds]=dict(N=128,IDs=ids,order='verbatim historical list',ids_sha256=sha(P/f'inputs/{ds}_panel_ids.json'),
        query_sha256=sha(P/f'inputs/{ds}_queries.jsonl'),historical_E2E_source=str(E2E/f'inputs/{ds}_panel_ids.json'),
        original_P2_10_and_boundary_and_E2E_identity_match=True,independent_question_groups=128,
        existed_before_medium_outcomes=True)
    aa=rows(source(STAGE1/f'actions/{ds}_dev.jsonl','saved native R/C2C outputs for post-replay identity only'))
    a={(r['id'],r['action']):r for r in aa if r['action'] in ['R','C']}
    pr={r['id']:r for r in rows(source(STAGE1/f'probes/{ds}_dev.jsonl','saved ProbeMax for post-replay identity only'))}
    gg={r['id']:r for r in rows(source(NATIVE/'data'/('obqa_dev.jsonl' if ds=='obqa' else 'arc_validation.jsonl'),'existing dev gold; analysis only'))}
    for i in ids:
        oldp=pr[i]
        expected.append(dict(task=ds,id=i,ProbeMax=oldp['ProbeMax'],probe_ids_sha256=oldp['probe_ids_sha256'],
            frozen_stage1_route='R' if oldp['ProbeMax']<=d['threshold'] else 'C',
            R=dict(raw_answer=a[i,'R']['output']['raw_answer'],answer=a[i,'R']['answer'],invalid=a[i,'R']['invalid'],
                generated_token_ids=a[i,'R']['output']['generated_token_ids'],native_first_input_ids=a[i,'R']['native_first_input_ids']),
            C=dict(raw_answer=a[i,'C']['output']['raw_answer'],answer=a[i,'C']['answer'],invalid=a[i,'C']['invalid'],
                generated_token_ids=a[i,'C']['output']['generated_token_ids'])))
        gold.append(dict(task=ds,id=i,gold=gg[i]['gold_answer'],legal_labels=gg[i]['choice_labels']))
write_rows(P/'inputs/expected_Stage1_identity_ANALYSIS_ONLY.jsonl',expected)
write_rows(P/'inputs/existing_gold_ANALYSIS_ONLY.jsonl',gold)
proxy_path=source(AUDIT/'summary/medium_stage2_timing_basis.csv','pre-existing full-development arithmetic proxy; compare only after replay')
pr=list(csv.DictReader(proxy_path.open()))
proxy={r['task']:dict(full_dev_N=int(r['N']),proxy_ms=float(r['net_margin_proxy_ms']),displayed_proxy_ms=68.32 if r['task']=='obqa' else 105.38) for r in pr}
save(P/'inputs/prior_proxy.json',proxy)
large_path=source(E2E/'summary/e2e_summary.csv','existing large E2E C2C summary for descriptive comparison only')
large=[r for r in csv.DictReader(large_path.open()) if r['reference']=='C']
csvout(P/'inputs/large_C2C_E2E_summary.csv',large)
idx=read(P/'MODEL_SOURCE_INDEX.json');models={}
for role,m in idx['models'].items():
    ff=[]
    for w in idx['local_verification']['models'][role]['weight_files']:
        path=source(w['path'],'unchanged official pinned '+role+' weight')
        assert sha(path)==w['sha256']==w['official_LFS_sha256']
        ff.append(dict(path=str(path),sha256=w['sha256'],bytes=w['bytes'],kind='official_LFS_weight'))
    for cf in m['verified_local_config_tokenizer_files']:
        path=source(P/'assets'/role/cf['official_file'],'unchanged pinned config/tokenizer/projector configuration')
        assert sha(path)==cf['sha256']
        ff.append(dict(path=str(path),sha256=cf['sha256'],bytes=path.stat().st_size,kind='config_tokenizer'))
    models[role]=dict(repo=m['repo_id'],revision=m['revision'],subfolder=m['subfolder'],local_files=ff,
        chat_template_sha256=m.get('chat_template_sha256'),hash_verification='PASS')
runtime={}
for path,h in old_ex['unchanged_scientific_runtime_source_hashes'].items():
    if '/src/' in path and not path.endswith('/native_runtime.py'):continue
    path=source(path,'unchanged Stage 1 native runtime dependency')
    assert sha(path)==h
    runtime[str(path)]=h
assert sha(P/'src/native_runtime.py')==sha(STAGE1/'src/native_runtime.py')
for name in ['receiver_prompt.py','scoring_v2.py','generation_configs.json','prefix_ids.json','label_token_sets.json']:
    path=source(PARENT/'protocol'/name,'exact inherited medium prompt/probe/parser/generation config')
    runtime[str(path)]=sha(path)
for file in (P/'src').glob('*.py'):ast.parse(file.read_text());runtime[str(file)]=sha(file)
source(P/'MODEL_SOURCE_INDEX.json','local unchanged copy used by Runtime')
freeze=dict(task='P2_MEDIUM_PAIR_E2E_STAGE2',status='PASS',utc=utc(),MEDIUM_STAGE2_RESULTS_OBSERVED=False,
    parent_Stage1_scientific_freeze_sha256=PARENT_HASH,parent_Stage1_execution_freeze_sha256=sha(STAGE1/'MEDIUM_PAIR_EXECUTION_FREEZE_RETRY1.json'),
    deployments=deps,panels=panels,models=models,runtime_source_hashes=runtime,
    stage1_native_runtime_file_unchanged=True,probe='exact original fixed-format prompt, thinking off, FP32 normalized labels; u=1-max p; no KV/prefill reuse',
    invalid='original V2 invalid retained as incorrect; runtime failure separate',
    topology=dict(GPUs=2,helper='cuda:0',receiver_fuser='cuda:1',batch=1,one_residency=True,same_allocation=True),
    timing_boundary='outer perf_counter with final two-device synchronization: input preparation, full unchanged online ProbeMax including tokenization/transfer/prefill/last-position projection/FP32 scores and diagnostics, selector, full unchanged native R or C2C including decode/parser/hook cleanup, final cleanup/sync; disk logging and later gold/identity checks excluded; startup separate',
    execution_order=dict(tasks=['obqa','arc'],question_order='unchanged historical panel order',paths=['fixed_C','policy_C'],rotation='left rotation by panel ordinal modulo 2; even fixed->policy, odd policy->fixed; 64 each per task'),
    expected_counts=dict(questions=256,complete_requests=512,fixed_C2C=256,policy=256,online_probes=256,warmup=0,synthetic_forwards=0,retries=0),
    bootstrap=dict(seed=0,resamples=2000,unit='paired question',N_per_task=128,interval='percentile descriptive 95% of mean paired saving',indices_generator='numpy.random.default_rng(0).integers(0,128,size=(2000,128)) independently per task'),
    primary_metrics=['N','q','threshold','R_count','coverage','fixed_correct','policy_correct','accuracy_difference','fixed_mean_median_ms','policy_mean_median_ms','paired_saving_mean_median_ms','paired_bootstrap_CI95','online_probe_selector_mean_ms','startup'],
    gate='E2E_POSITIVE iff mean saving > 0 and descriptive paired bootstrap lower 95% bound > 0; otherwise E2E_UNCERTAIN_OR_NEGATIVE',
    reporting='both tasks regardless of result; retain first/cold/invalid/identity mismatches; no filtering or repeat to match; no causality',
    output_identity='route C: compare same-round fixed C2C; route R: compare saved Stage1 native R; raw/parsed/token diagnostics all retained; mismatch never triggers retry or deletion',
    prior_proxy=proxy,proxy_comparison='E2E panel minus prior full-dev proxy; direction descriptive, populations and batches differ; no hardware causal attribution',
    budget=dict(HPC='ClusterB',account='project',queue='gpu-queue',walltime='00:15:00',walltime_seconds=900,GPU_count=2,max_GPU_allocation_hours=.5,max_submissions=1),
    throughput_estimate=dict(prior_model_loading_seconds=sum(old_ex['synthetic_smoke_PASS']['load_seconds'].values()),
        two_tasks_two_arm_serial_proxy_seconds=192.79492141947183,conservative_loading_hash_IO_headroom_seconds=400,total_conservative_seconds=600,requested_seconds=900,
        estimate_identity='existing Stage1 loading and full-dev action/probe arithmetic; scheduling budget estimate, not new E2E outcome'),
    PBS_script_sha256=sha(P/'run_medium_stage2.pbs'),prohibited=['ARC test','Text replay','new calibration','new threshold','new router','utility','manuscript/supplement changes','second submission'],
    positioning='development-panel E2E evidence; not sealed confirmation, independent test, or policy selection; medium extension remains post-hoc motivated but protocol-frozen before medium outcomes',
    frozen_files={str(f):sha(f) for f in [P/'MODEL_SOURCE_INDEX.json',P/'run_medium_stage2.pbs']+list((P/'inputs').glob('*'))+list((P/'protocol').glob('*'))},
    preparation_wall_seconds=time.perf_counter()-start)
save(P/'SOURCE_INDEX.json',list(sources.values()))
freeze['source_index_sha256']=sha(P/'SOURCE_INDEX.json')
save(FREEZE,freeze)
save(P/'evidence/PRE_SUBMISSION_VALIDATION.json',dict(status='PASS',utc=utc(),freeze_sha256=sha(FREEZE),
    historical_panel_identity=True,exact_threshold_identity=True,unchanged_native_runtime=True,local_model_hashes_match=True,
    formal_requests=0,formal_probes=0,MEDIUM_STAGE2_RESULTS_OBSERVED=False))
print('FREEZE_PASS',sha(FREEZE),flush=True)
