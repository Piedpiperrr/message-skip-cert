"""Stage 0. No opening, downloading or hashing any test file here."""
from common import *
import ast,resource,shutil,sys,platform,importlib.metadata
assert not (P/'PRE_TEST_FREEZE.json').exists()
resource.setrlimit(resource.RLIMIT_CPU,(600,601))
old=read(P/'protocol/parent_e2e_frozen_config.json')
src=read(P/'protocol/arc_source_manifest.json'); fit=read(P/'protocol/fit_thresholds_large_arc.json')
deps={b:read(P/f'protocol/large_arc_{b}.json') for b in ['T','C']}
for b,q in [('T',.95),('C',.90)]:
 assert deps[b]['mode']=='selective' and deps[b]['q']==q
 assert deps[b]['threshold']==fit['thresholds'][fit['q'].index(q)]
active=ROOT/'dev_e2e_replay'
prior=csvread(active/'summary/e2e_summary.csv')
estimate=1172*sum(float(r[k]) for r in prior if r['dataset']=='arc' for k in ['policy_mean_ms','reference_mean_ms'])/1000
cfg={
 'task':'sealed_arc_confirmation','stage':P.name,'native_root':old['native_root'],'native':old['native'],
 'parser_path':old['parser_path'],'parser_sha256':old['parser_sha256'],'prefix':old['prefix'],
 'thresholds':{b:{'q':d['q'],'threshold':d['threshold'],'source':str(BOUND/f'deployments/large_arc_{b}.json'),'source_sha256':sha(BOUND/f'deployments/large_arc_{b}.json')} for b,d in deps.items()},
 'score':{'name':'ProbeMax','definition':'u = float((1 - exp(log_softmax(stack(logsumexp(last_position_logits.float()[label_token_set]))))).max()).item()) interpreted exactly by native_adapter.Runtime.probe: u=float((1-p.max()).item())','arithmetic':'FP32 label logsumexp, log_softmax, exp, 1-p.max; BF16 backbone and LM-head; all logits projected only at last valid position','comparison':'u <= frozen threshold; all ties retained; no test quantile','probability_meaning':'conditional distribution on union of label token sets, not calibrated correctness','code_sha256':sha(P/'src/native_adapter.py')},
 'population':{'dataset':src['dataset'],'config':src['config'],'revision':src['revision'],'file':src['test_metadata_only']['file'],'expected_sha256':src['test_metadata_only']['lfs_sha256'],'expected_bytes':src['test_metadata_only']['bytes'],'N':1172,'local_file':str(P/'source/test-00000-of-00001.parquet'),'order':'original physical parquet row order, ordinal 0..1171; never sorted for execution','expected_schema':{'id':'string','question':'string','choices':{'label':'list[string]','text':'list[string]'},'answerKey':'string (not projected until prediction freeze)'},'loader':'src/access_test.py: pyarrow.parquet.read_table(columns=[id, question, choices], use_threads=False); no answerKey projection','schema_validation':'after FIRST_TEST_ACCESS.json; mechanical repairs only; semantic change BLOCKED; no row exclusions'},
 'group_rule':{'source':str(BOUND/'src/common.py'),'function':'signature','normalization':'case-sensitive whitespace collapse of Question: stem + Choices: + ordered displayed-label: choice-text; no lowercase, fuzzy, gold or output inputs','representative':'lexicographic minimum original string ID in each signature group','primary_order':'representatives retained in original physical row order','all_raw_rows_retained':True,'raw_row_statistics':'all accuracy/latency/utility also reported on all 1172 rows; primary uses representatives consistently'},
 'gold_isolation':{'pre_prediction_columns':['id','question','choices'],'post_prediction_columns':['id','answerKey'],'freeze_required':'PREDICTION_TIMING_FREEZE.json, including every raw/parsed action, probe, route and timing','opaque_bytes':'download and SHA256 verification do not decode or associate the gold column; content access timestamp precedes first projected read','gold_mapping':'original choice labels mapped in original order to A..Z, exactly stage; unmapped or ambiguous key is BLOCKED; no population edits'},
 'invalid':{'machine_answer':'single sentinel INVALID; both invalid = unchanged; exactly one invalid = changed; distinct valid labels = changed','accuracy':'INVALID always incorrect; runtime failure is not INVALID and stops execution'},
 'risk_target':.05,'primary_metrics':['test_N','independent_group_N','omission_coverage','changed_among_routed/routed','conditional_answer_change','marginal_omission_answer_change','total_policy_reference_answer_change','reference_correct_accuracy','policy_correct_accuracy','paired_accuracy_difference','benefit_harm_neutral','policy_mean_median_E2E_ms','reference_mean_median_E2E_ms','paired_mean_saving_ms','paired_saving_95_interval','online_probe_selector_overhead_ms','same_population_utility'],
 'metric_definitions':{'marginal_omission_answer_change':'count(route_R and policy_answer != reference_answer)/N','total_policy_reference_answer_change':'count(policy_answer != reference_answer)/N, reports reference-route identity failures separately','benefit':'policy correct, reference incorrect','harm':'policy incorrect, reference correct','neutral':'equal correctness, subdivided both correct, both incorrect','saving':'fixed_reference_E2E_ms - policy_E2E_ms','utility':'correct - lambda * latency_ms / frozen_c_ref'},
 'bootstrap':{'seed':0,'replicates':2000,'unit':'independent representative question group, paired paths','generator':'numpy.random.default_rng(0).integers(0,G,size=(2000,G))','shared_indices':'Text and C2C','interval':'percentile [.025,.975], numpy default linear quantile; descriptive','metrics':['net_saving_ms','accuracy_diff','delta_U','coverage','marginal_answer_change','conditional_answer_change'],'zero_routed_resample':'conditional risk undefined/null; count disclosed'},
 'binomial_interval':{'method':'two-sided Clopper-Pearson 95% descriptive, scipy.stats.beta.ppf','lower':'0 if k=0 else beta.ppf(.025,k,n-k+1)','upper':'1 if k=n else beta.ppf(.975,k+1,n-k)','zero_routed':'undefined, cannot conclude preservation'},
 'interpretation':{'preservation':'report exact changed/routed and whether empirical rate <=.05; if >.05 report excess, never retune or use interval as calibration','economic':'report whether paired mean saving >0 and whether descriptive interval is above/across/below zero independently','no_joint_gate':True,'accuracy_not_selection':True,'scope':'two frozen large/ARC policies, one sealed project population and one timing environment; no causal scale or algorithm novelty; public benchmark training contamination unknown'},
 'order':{'tasks':['arc'],'paths':old['order']['paths'],'rotation':'left rotation by original question ordinal modulo 4, reset ordinal=0 for test'},
 'timing':old['timing'],'topology':old['topology'],'lambda':.01,'c_ref':{'arc':old['c_ref']['arc']},
 'runtime_constraints':{'native_adapter':'byte-identical to completed E2E replay','batch_size':1,'warmup':0,'retries':0,'probe_KV_reuse':False,'probe_argmax_as_answer':False,'model_residencies':1,'first_cold_retained':True,'diagnostics_and_audit_IO':'outside authoritative timer as before'},
 'counts':{'complete_action_attempt_cap':4688,'online_policy_probe_cap':2344,'fixed_T':1172,'policy_T':1172,'fixed_C':1172,'policy_C':1172,'extra_fixed_R':0},
 'resources':{'account':'<allocation>','queue':'gpu-queue','select':2,'GPU_count':2,'wall_seconds':7200,'walltime':'02:00:00','requested_GPU_allocation_hours':4,'user_GPU_allocation_hour_cap':5,'CPU_cap_seconds':9000,'preparation_reporting_reserve':1200,'threads':1,'max_submissions':1,'python':old['resources']['python'],'throughput_estimate_seconds':estimate,'throughput_evidence':str(active/'summary/e2e_summary.csv'),'estimate_note':'1172 times sum of four prior ARC path means, excluding startup; under 2h so no extension','stop_margin_seconds':90,'output_destination':str(P),'run_destination':os.environ['STORAGE_ROOT']+'/runs/project/<PBS_JOBID>_sealed_arc','temporary_destination':os.environ['STORAGE_ROOT']+'/tmp/<PBS_JOBID>'},
 'failure_rule':'single submission, no retries/resume/replay successful IDs; runtime failure PARTIAL, semantic protocol change BLOCKED, preserve hashes and completed keys; return Work',
 'method_search':'CLOSED permanently for this task; no method/reference/q/threshold/risk/prompt/parser selection; small and OBQA not executed','D':'learned control','ProbeMax':'ordinary fixed-format confidence baseline',
 'manuscript':{'active_directory':str(active/'paper'),'snapshot':'evidence/manuscript_snapshot','editing':'edit current active English source in place after results; task paper symlink points to same source, no parallel manuscript'},
 'ARC_TEST_ACCESSED':False}
# Exact math is expressed separately to remove any ambiguity in the prose nesting.
cfg['score']['definition']='For each displayed label l: a_l=logsumexp(FP32 last-position logits at frozen token set S_l); p=exp(log_softmax(stack(a_l))); u=float((1-p.max()).item()).'
save(P/'frozen_config.json',cfg)
sources={}
def index(path,role,expected=None):
 path=Path(path);h=sha(path)
 if expected:assert h==expected,('SOURCE_CHANGED',str(path))
 sources[str(path)]={'path':str(path),'resolved_path':str(path.resolve()),'bytes':path.stat().st_size,'sha256':h,'role':role}
# Revalidate frozen native provenance; hash every checkpoint shard, without copies.
for s in read(P/'protocol/parent_e2e_SOURCE_INDEX.json'):
 path=Path(s['path'])
 if (str(path).startswith(cfg['native_root']+'/') and path.suffix=='.py') or any(str(path).startswith(v['path']+'/') for v in cfg['native']['models'].values()) or str(path).startswith(cfg['native']['fuser']['path']+'/'):
  assert path.stat().st_size==s['bytes']
  print('HASH_NATIVE',path.name,flush=True);index(path,s['role'],s['sha256'])
for path in Path(cfg['native_root']).glob('*.py'):index(path,'native runtime import closure')
for path in (Path(cfg['native_root'])/'runtime_source').rglob('*.py'):index(path,'official transplanted runtime import closure')
for name in ['query_features.py','protocol_min.py']:
 index(ROOT/'obqa_small_action_matrix'/name,'read-only ARC formatter dependency')
for path in [Path(cfg['parser_path']),active/'frozen_config.json',active/'PROTOCOL_FREEZE.json',active/'IMPLEMENTATION_FREEZE.json',active/'summary/e2e_summary.csv',BOUND/'src/common.py',BOUND/'frozen_config.json',BOUND/'PROTOCOL_FREEZE.json',BOUND/'thresholds/large_arc.json',BOUND/'thresholds/large_arc_FREEZE.json',ROOT/'arc_data_protocol/prepare_arc_p2_8.py',ROOT/'arc_data_protocol/data_use_contract.json']:
 index(path,'direct frozen protocol / population metadata / timing provenance')
for b in ['T','C']:
 for suffix in ['.json','_FREEZE.json']:index(BOUND/f'deployments/large_arc_{b}{suffix}','original frozen deployment')
assert sha(P/'src/native_adapter.py')==sha(active/'src/native_adapter.py')
assert sha(P/'src/receiver_prompt.py')==sha(active/'src/receiver_prompt.py')
save(P/'SOURCE_INDEX.json',list(sources.values()))
save(P/'protocol/ENVIRONMENT.json',{'python':sys.executable,'python_version':sys.version,'platform':platform.platform(),'installed_versions':{n:importlib.metadata.version(n) for n in ['torch','transformers','tokenizers','numpy','scipy','pyarrow','safetensors','huggingface-hub']},'install_or_upgrade':False})
for path in (P/'src').glob('*.py'):ast.parse(path.read_text(),filename=str(path))
save(P/'evidence/STAGE0_VALIDATION.json',{'utc':utc(),'source_files':len(sources),'all_weights_sha256':True,'native_adapter_byte_identical':True,'receiver_prompt_byte_identical':True,'actual_thresholds_copied':cfg['thresholds'],'test_content_opened':False,'schema_not_inspected':True,'throughput_estimate_seconds':estimate,'AST_valid':True})
paths=[P/'frozen_config.json',P/'SOURCE_INDEX.json',P/'USER_PROMPT_ZH.md',P/'run_sealed.pbs']+list((P/'protocol').glob('*'))+list((P/'src').glob('*.py'))+list((P/'evidence/manuscript_snapshot').glob('*'))+[P/'evidence/STAGE0_VALIDATION.json',P/'evidence/SELF_CHECK.json',P/'evidence/resolved_stage0_paths.json']
freeze('PROTOCOL_FREEZE.json',paths,ARC_TEST_ACCESSED=False,thresholds=cfg['thresholds'],risk_target=.05)
freeze('PRE_TEST_FREEZE.json',[P/'PROTOCOL_FREEZE.json']+paths,ARC_TEST_ACCESSED=False,method_search='CLOSED',test_source_known_metadata=cfg['population'],resources=cfg['resources'])
print('PRE_TEST_FREEZE_COMPLETE',sha(P/'PRE_TEST_FREEZE.json'),flush=True)
