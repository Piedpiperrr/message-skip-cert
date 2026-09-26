# Metadata-only preparation. No numpy, labels, fitting or calibration statistics.
from common import *
import random,collections,shutil
assert not (P/'PROTOCOL_FREEZE.json').exists()
assert not list(ROOT.glob('P2_RISK_CALIBRATION_BINARY_*/evidence/pbs/submission_attempt.json'))
old=read(E/'frozen_config.json')
def query(r):return {k:r[k] for k in ['id','question_stem','choice_labels','choice_text']}
train=[query(r) for r in jl(E/'inputs/train_queries.jsonl')];dev=[query(r) for r in jl(E/'inputs/dev_queries.jsonl')]
assert len(train)==3466 and len(dev)==742
for rows in [train,dev]:assert len({r['id'] for r in rows})==len(rows)
def signature(r):
 s='\n'.join(['Question: '+r['question_stem'],'Choices:']+[a+': '+b for a,b in zip(r['choice_labels'],r['choice_text'])])
 return ' '.join(s.split())
groups=collections.defaultdict(list)
for r in train:groups[signature(r)].append(r['id'])
# Deterministic representative = lexicographically smallest complete ID, no prefix grouping.
reps=sorted(min(v) for v in groups.values());random.Random(0).shuffle(reps)
assert len(reps)>2100
fit=reps[:2100];cal=reps[2100:];dev_ids=[r['id'] for r in dev]
for name,ids in [('fit',fit),('cal',cal),('dev',dev_ids)]:save(P/f'splits/{name}_ids.json',ids)
csvout(P/'splits/group_members.csv',({'group_sha256':hashlib.sha256(s.encode()).hexdigest(),'representative':min(ids),'id':i,'selected_unique':i==min(ids)} for s,ids in sorted(groups.items()) for i in sorted(ids)))
freeze('SPLIT_FREEZE.json',list((P/'splits').glob('*')),seed=0,rng='Python random.Random(0), shuffle lexicographically sorted representatives',fit_n=len(fit),cal_n=len(cal),dev_n=len(dev_ids),labels_read=False)
# Population metadata only after split freeze.
dgroups=collections.defaultdict(list)
for r in dev:dgroups[signature(r)].append(r['id'])
save(P/'splits/population_metadata.json',{'train_rows':len(train),'train_unique':len(reps),'train_duplicate_groups':sum(len(v)>1 for v in groups.values()),'dev_rows':len(dev),'dev_unique':len(dgroups),'dev_duplicate_groups':sum(len(v)>1 for v in dgroups.values()),'cross_train_dev_groups':[{'train_ids':groups[s],'dev_ids':ids} for s,ids in dgroups.items() if s in groups],'duplicate_definition':'exact whitespace-normalized question + ordered label/text, inherited E0 prepare_protocol.py lines 52-57; no id prefixes','representative_rule':'lexicographically smallest complete ID'})
for name,rows in [('train',train),('dev',dev)]:writejl(P/f'inputs/{name}_queries.jsonl',rows)
shutil.copyfile(E/'TRAIN_FEATURE_INDEX.csv',P/'inputs/TRAIN_FEATURE_INDEX.csv');shutil.copyfile(E/'receiver_prompt.py',P/'src/receiver_prompt.py')
# Inspect only feature index and one previously recorded route field, never statistics.
record=E/'records/dev/0259_FFR_E1.json';route=read(record)['route']
idx=list(csv.DictReader((D/'FEATURE_INDEX.csv').open()))
save(P/'evidence/dev_cache_audit.json',{'E1_index':str(D/'FEATURE_INDEX.csv'),'E1_index_sha256':sha(D/'FEATURE_INDEX.csv'),'E1_index_columns':list(idx[0]),'E2E_index_files':[x.name for x in E.glob('*INDEX*')],'record':str(record),'inspected_field':'route','route':route,'compliant_dev_z_found':False,'reason':'E1 index indexes training features only; E2E route metadata contains g/scores but no z or z cache path; no development feature index','max_new_prefill_attempts':742})
config={'task':'P2_RISK_CALIBRATION_BINARY_PILOT','stage':P.name,'scope':'large/OBQA binary R/Text; exploratory frozen-rule pilot','reference':'T','alpha':0.05,'delta':0.10,'M':100,'p_cutoff':0.001,'CP_quantile':0.999,'q_grid':[i/20 for i in range(1,21)],'quantile':'inverse empirical CDF; order statistic ceil(q*n_fit), ties included; q=1 is +infinity / fixed R','selection':'largest accepted q per family; no acceptance -> fixed Text','split_rng':'Python random.Random(0), unstratified, label independent','random_family':'separate numpy PCG64(0) stream; cal list then dev list, one independent Uniform(0,1) per request; no redraw; deployment independent fresh coin','LR':{'penalty':'l2','C':1,'solver':'lbfgs','max_iter':1000,'random_state':0,'class_weight':None},'standardization':'none; inherit normalized E1 z','heads':['disagreement','correctness_R','correctness_T','harm'],'families':['D','R','Diff','H','Random'],'model':old['native']['models']['receiver'],'E1_features':old['E1_features'],'parser_path':old['parser_path'],'parser_sha256':old['parser_sha256'],'train_labels_source':old['data']['train_labels'],'dev_gold_source':old['data']['dev_gold'],'historical_dev_records':str(E/'records/dev'),'lambda':0.01,'c_ref_ms':262.462515,'bootstrap':{'seed':0,'replicates':2000,'unit':'joint question, models and thresholds fixed','comparisons':['each of five frozen policies minus Text','D minus R','D minus Diff','D minus H','D minus Random'],'interval':'percentile 2.5/97.5 exploratory descriptive'},'resources':{'account':'project','queue':'gpu-queue','select':1,'GPUs':1,'max_jobs':1,'walltime_seconds':1800,'GPU_allocation_hours_cap':0.5,'CPU_seconds_cap':1200,'preparation_reporting_CPU_reserve':60,'threads':1,'prefill_attempt_cap':742,'python':old['resources']['python']},'exposure':'Historical train/dev influenced earlier research decisions and reference choice. New split isolates this computation only; no restoration of untouched independent confirmatory status.','historical_requests_reused':6932,'no_new_protocol_requests':True,'timing':'per-query measured feature wall + own head(s)/selector + selected historical full request; constant frozen R/T removes feature/head; diagnostic extraction remains experiment cost','ranking_diagnostics':'all fixed q, AUROC/AP wrt d; descriptive exact coverage tie-broken by frozen dev order; no new deployable threshold','random_reference':'hypergeometric 2.5/97.5 range at matched n; no tail-probability gate','B_gate':'A completes normally and resource permits, regardless of statistical acceptance'}
save(P/'frozen_config.json',config)
sources=[(E/'frozen_config.json','inherited config'),(E/'COST_FREEZE.json','historical costs'),(E/'inputs/train_labels_V2.jsonl','frozen labels, read only after split'),(E/'inputs/dev_gold.jsonl','post-route evaluation only'),(E/'REQUEST_INDEX.csv','historical complete request index'),(E/'summary/main_results.csv','old end-to-end reference'),(D/'extract_features.py','feature implementation'),(D/'SOURCE_INDEX.json','feature provenance'),(D/'frozen_config.json','E1 identity'),(ROOT/'P2_SCORING_V2_20260912T191445Z/RULE_FREEZE_V2.json','V2 identity'),(Path(old['parser_path']),'parser identity, do not rescore'),(ROOT/'P2_V2_BASELINES_FFR_E0_20260913T000052Z/prepare_protocol.py','directly inherited grouping definition')]
csvout(P/'SOURCE_INDEX.csv',({'path':str(p),'role':role,'sha256':sha(p),'bytes':p.stat().st_size} for p,role in sources))
assert sha(old['parser_path'])==old['parser_sha256']
freeze('PROTOCOL_FREEZE.json',[P/'frozen_config.json',P/'SPLIT_FREEZE.json',P/'SOURCE_INDEX.csv',*list((P/'inputs').glob('*')),P/'src/receiver_prompt.py'],new_fits=0,new_prefills=0,new_jobs=0,cal_disagreement_statistics_read=False)
print(json.dumps(read(P/'splits/population_metadata.json'),ensure_ascii=False));print('PROTOCOL_FROZEN',sha(P/'frozen_config.json'))
