from common import *
import ast,subprocess
assert not (P/'MMLU_PRO_STAGE1_PROTOCOL_FREEZE.json').exists()
assert read(P/'evidence/CPU_PREFLIGHT.json')['status']=='PASS'
assert not any((P/'shards').glob('*/OUTCOMES_OBSERVED.json'))
for f in (P/'src').glob('*.py'):ast.parse(f.read_text(),filename=str(f))
for i in [1,2]:subprocess.run(['bash','-n',str(P/f'run_shard{i}.pbs')],check=True)
for f in (REVIEW/'candidates/PLAN_C').glob('*.json'):assert sha(f)==sha(P/'splits'/f.name)
native=read(P/'RUNTIME_SOURCE_INDEX.json')
for f,h in native.items():assert sha(f)==h
models=read(P/'MODEL_SOURCE_INDEX.json');pop=read(P/'protocol/POPULATION_IDENTITY.json')
paths=[*P.glob('src/*.py'),*P.glob('protocol/*'),*P.glob('splits/*.json'),*P.glob('inputs/*'),*P.glob('run_shard*.pbs')]
paths += [P/f for f in ['MODEL_SOURCE_INDEX.json','DATASET_SOURCE_INDEX.json','DATASET_STRUCTURE_AUDIT.json','CHOICE_TOKEN_COMPATIBILITY.json','RUNTIME_SOURCE_INDEX.json','evidence/CPU_PREFLIGHT.json']]
frozen={str(f.relative_to(P)):sha(f) for f in sorted(paths) if f.is_file()}
freeze=dict(task='P2_MMLU_PRO_BREADTH_STAGE1',status='SCIENTIFIC_PROTOCOL_FROZEN_FOR_AUTHORIZED_STAGE1',utc=utc(),
    authorization='Work user instruction: GO MMLU-Pro Plan C, exactly two Stage1 PBS jobs, no E2E',
    scientific_positioning='post-hoc benchmark breadth extension, protocol-frozen before observing MMLU-Pro model outcomes; entire benchmark is development evidence',
    MMLU_PRO_OUTCOMES_OBSERVED=False,dataset_repo='TIGER-Lab/MMLU-Pro',dataset_revision='b189ec765aa7ed75c8acfea42df31fdae71f97be',
    raw_parquet_path=str(REVIEW/'dataset/test-00000-of-00001.parquet'),raw_parquet_sha256='0e24a191921c2f453518a537a8b2117bd137e7714d4ef1565e9ba06c1ecb9ad8',
    population=pop,Plan_C_manifest_hashes={str(f.relative_to(P)):sha(f) for f in sorted((P/'splits').glob('*.json'))},
    duplicate_group_rule='exact Python whitespace collapse: " ".join(question.split()); SHA256 UTF-8; choices excluded; frozen minimum numeric question_id representative; all group members kept in same existing split',
    primary_risk_unit='one frozen representative per normalized-question group; 3000 fit / 6000 cal / 2641 dev',
    raw_duplicate_rows='all retained and inferred; descriptive only; no inflation of independent n',
    helper_receiver_fuser={role:{k:v for k,v in spec.items() if k!='files'} for role,spec in models['models'].items()},
    model_file_hashes_index='MODEL_SOURCE_INDEX.json',model_file_hashes_index_sha256=sha(P/'MODEL_SOURCE_INDEX.json'),
    native_source_hashes=native,
    Text_protocol='P2_10 native T2THelperBundle + T2TReceiverBundle; one background sentence, do NOT solve; same three-message consume; helper 256 / receiver 64 greedy; no semantic changes',
    C2C_protocol='P2_10 official C2CSharerHelperBundle + C2CReceiverSideFuserBundle; helper KV prefix L-1 using receiver tokenizer; native transfer; 36 official projectors; BF16 weights, FP32 projection; receiver native generation',
    adapters='schema projection; dynamic choice formatting and legal labels A..chr(64+K); unchanged P2_SCORING_V2 2.0.0 supports A-J',
    ProbeMax=dict(definition='u(x)=1-max_a p(a|x)',label_logits='FP32 logsumexp across every nonspecial token whose decode(token).strip()==label',
        probabilities='FP32 log_softmax then exp only across this question actual K legal labels',legal_labels='A through chr(64+K), K=len(ordered options)',
        label_token_sets=read(P/'protocol/label_token_sets.json'),prefix_ids=[785,4396,4226,374],prefix='The correct answer is',
        independent_full_prefill=True,thinking=False,use_cache=False,projection='lm_head only last valid position hidden state',probe_KV_reuse=False,
        once_per_raw_query=True,argmax_diagnostic_only=True),
    risk=dict(q_grid=[j/20 for j in range(1,21)],alpha=.05,p_threshold=.001,CP_level=.999,
        thresholds='ceil(j*Nfit/20) integer order statistic, all ties retained; q=1 threshold=Infinity fixed R',
        outcome='canonical parsed R/reference answer disagreement conditional on route-to-R',invalid='P2_SCORING_V2 invalid canonical INVALID; both invalid equal; runtime failure is missing, never fallback',
        accept='BinomialCDF(k;n,.05)<=.001; report one-sided CP .999 upper',selection='independently largest accepted q per reference; none -> q=0 fixed-reference fallback; accuracy never used',
        tests_per_stratum=20,new_strata=2,total_tests=40,ideal_Bonferroni_per_stratum=.02,ideal_Bonferroni_extension=.04,historical_families_combined=False),
    parser=dict(identity='P2_SCORING_V2',implementation='2.0.0',sha256=sha(P/'protocol/scoring_v2.py')),
    generation_config=read(P/'protocol/generation_configs.json'),
    reporting_metrics=['q','threshold','routed count','coverage','changed/routed','conditional disagreement','marginal disagreement','fit/cal/dev R/reference disagreement prevalence','AUROC higher-u predicts disagreement','AP','reference/policy correct and accuracy difference','benefit/harm/neutral-change','invalid counts','14-category descriptive summaries','K=3..10 descriptive summaries','raw-row descriptive counterparts'],
    primary_reporting_split='dev group representatives; fit/cal prevalence and ranking diagnostics; no category/K threshold adaptation',
    uncertainty='calibration one-sided CP .999; descriptive dev routed risk one-sided CP .95 on representatives; AUROC/AP point estimates; no independent raw-row confidence intervals',
    analysis_order='both shards PBS terminal -> full completeness/key/input identity validation -> fit thresholds -> 40 cal tests -> deployment configs saved -> gold read and dev/descriptive reporting',
    candidate_ordering_override='The old candidate shard JSON ordering metadata is retained byte-for-byte but superseded by this Work authorization: jobs collect only; no scientific analysis until both jobs terminate. No ID/group/split/order changes.',
    intermediate_access='PBS state, completion counts, runtime failures, walltime/ETA, disk/resources only; no scientific results used for execution decisions',
    submission_barrier='both fixed scripts submitted held via submit-job -h; write BOTH_SUBMISSIONS_CONFIRMED.json only after two held receipts; then qrls both; no scientific outcome before both submissions',
    shard_manifests={str(i):dict(path=f'splits/SHARD_{i}_FROZEN_IDS.json',sha256=sha(P/f'splits/SHARD_{i}_FROZEN_IDS.json'),rows=6016) for i in [1,2]},
    PBS_scripts={str(i):dict(path=f'run_shard{i}.pbs',sha256=sha(P/f'run_shard{i}.pbs'),GPUs=2,walltime='14:00:00') for i in [1,2]},
    total_Stage1_GPU_budget=56,max_formal_PBS_jobs=2,replacement_jobs_allowed=False,E2E_authorized=False,
    E2E_candidate_ids='splits/candidate_e2e128_ids.json; candidate identity only, forbidden to execute',
    mechanical_validation='each job scheduler + visible CUDA count=2 + strict exact model/fuser load + synthetic non-benchmark R/T/C and ProbeMax structures + dynamic parser labels before project queries',
    research_hard_stop='2026-09-20T00:00:00Z conservative boundary; no job whose requested end crosses this',
    complete_results_must_be_reported=True,manuscript_or_supplement_changes_authorized=False,frozen_files=frozen)
save(P/'MMLU_PRO_STAGE1_PROTOCOL_FREEZE.json',freeze)
save(P/'evidence/FREEZE_RECEIPT.json',dict(utc=utc(),sha256=sha(P/'MMLU_PRO_STAGE1_PROTOCOL_FREEZE.json'),MMLU_PRO_OUTCOMES_OBSERVED=False))
print('SCIENTIFIC_FREEZE',sha(P/'MMLU_PRO_STAGE1_PROTOCOL_FREEZE.json'),flush=True)
