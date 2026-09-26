"""Metadata only. No scoring, label inspection, model or tokenizer loading."""
from common import *
import shutil,random,collections,ast
assert not (P/'PROTOCOL_FREEZE.json').exists()
c0=read(OLD/'frozen_config.json'); c10=read(P10/'frozen_config.json'); e1=read(E1/'frozen_config.json')
sources=[]
def index(p,role):
 p=Path(p);sources.append(dict(path=str(p),sha256=sha(p),bytes=p.stat().st_size,role=role))
for src in [OLD/'HANDOFF_ZH.md',OLD/'frozen_config.json',OLD/'PROBE_PROTOCOL_FREEZE.json',OLD/'src/run_controls.py',OLD/'src/receiver_prompt.py',OLD/'records/probe_records.jsonl',OLD/'records/dev_scored_routes.jsonl',OLD/'records/dev_per_question_new.jsonl',OLD/'summary/main_dev.csv',OLD/'summary/calibration_new_60.csv',OLD/'models/deployment.json',OLD/'thresholds/new_thresholds.json',BINARY/'src/prepare.py',E0/'prepare_protocol.py',E0/'folds/groups.csv',E1/'frozen_config.json',E1/'SOURCE_INDEX.json',P10/'frozen_config.json',P10/'run_p2_10.py',P10/'runtime.py',P10/'arc_protocol.py',P10/'protocol_min.py',P10/'analyze_p2_10.py',V2/'RULE_FREEZE_V2.json',V2/'action_summary.csv',V2/'labels/LABEL_MANIFEST.json']:
 index(src,'frozen source identity')
for name in ['full_train','full_development','panel_train','panel_development']:index(V2/f'labels/{name}_P2_SCORING_V2.jsonl','V2: only d projection after thresholds; gold/correctness only after all routes')
for pair in PAIRS:
 for ds in DATASETS:
  dv='dev' if ds=='obqa' else 'validation'
  for s in ['train',dv]:
   for suff in ['cost_panel_matrix.npz','cost_panel_originals.jsonl']:index(P10/f'results/{pair}/{ds}/{s}_{suff}','original complete requests; panel ids/action costs')
# Source-index validation for each receiver, using E1, no weights read or copied.
model_index=[]
for pair,spec in e1['models'].items():
 assert spec['revision']=={'large':'b968826d9c46dd6066d109eabc6255188de91218','small':'c1899de289a04d12100db370d81485cdf75e47ca'}[pair]
 matched=[r for r in read(E1/'SOURCE_INDEX.json') if str(Path(r['path']).parent)==spec['path']]
 assert matched
 for r in matched:
  f=Path(r['path']);assert f.exists() and f.stat().st_size==r['size_bytes']
  if r['sha256']:assert sha(f)==r['sha256'];index(f,'E1 verified receiver/tokenizer identity')
  model_index.append({**r,'pair':pair,'revision':spec['revision']})
save(P/'protocol/MODEL_SOURCE_INDEX.json',model_index)
pop=[]
for ds in DATASETS:
 dv='dev' if ds=='obqa' else 'validation'
 rows={}
 for s,orig in [('train','train'),('dev',dv)]:
  src=Path(c10['data'][ds][orig]['path']);assert sha(src)==c10['data'][ds][orig]['sha256'];index(src,'query source; whitelist projection only')
  rows[s]=[{k:r[k] for k in ['id','question_stem','choice_labels','choice_text']} for r in jl(src)]
  assert len(rows[s])==c10['data'][ds][orig]['n'];writejl(P/f'inputs/{ds}_{s}_queries.jsonl',rows[s])
 groups={s:collections.defaultdict(list) for s in rows}
 for s in rows:
  for r in rows[s]:groups[s][signature(r)].append(r['id'])
 if ds=='obqa':
  ids={s:read(BINARY/f'splits/{s}_ids.json') for s in ['fit','cal','dev']}
  for s in ids:index(BINARY/f'splits/{s}_ids.json','verbatim original OBQA order');shutil.copyfile(BINARY/f'splits/{s}_ids.json',P/f'splits/obqa_{s}_ids.json')
  assert len(groups['train'])==3466 and len(ids['fit'])==2100 and len(ids['cal'])==1366
 else:
  reps=sorted(min(x) for x in groups['train'].values());random.Random(0).shuffle(reps);n=3*len(reps)//5
  byrep={min(x):sorted(x) for x in groups['train'].values()}
  ids={s:[i for r in rr for i in byrep[r]] for s,rr in [('fit',reps[:n]),('cal',reps[n:])]};ids['dev']=[r['id'] for r in rows['dev']]
  assert len(reps)==1118 and n==670
  dup=next(v for v in groups['train'].values() if 'MEA_2011_8_8' in v);assert set(dup)=={'MEA_2011_8_8','MEA_2012_5_8'}
  assert any(set(dup)<=set(ids[s]) for s in ['fit','cal'])
  for s,v in ids.items():save(P/f'splits/{ds}_{s}_ids.json',v)
 members=[]
 for s in ['fit','cal','dev']:
  gg=groups['dev' if s=='dev' else 'train'];lookup={i:(sig,min(v)) for sig,v in gg.items() for i in v}
  representatives=[i for i in ids[s] if i==lookup[i][1]];save(P/f'splits/{ds}_{s}_representatives.json',representatives)
  for i in ids[s]:sig,rep=lookup[i];members.append(dict(dataset=ds,split=s,id=i,representative=rep,primary=i==rep,group_sha256=hashlib.sha256(sig.encode()).hexdigest()))
  pop.append(dict(dataset=ds,split=s,rows=len(ids[s]),groups=len(representatives),omitted_from_primary=[i for i in ids[s] if i!=lookup[i][1]]))
 csvout(P/f'splits/{ds}_group_members.csv',members)
 save(P/f'splits/{ds}_train_dev_overlap.json',[{'train_ids':groups['train'][s],'dev_ids':v} for s,v in groups['dev'].items() if s in groups['train']])
 save(P/f'inputs/{ds}_panel_ids.json',{'train':c10['cost_panel'][ds]['train']['ids'],'dev':c10['cost_panel'][ds][dv]['ids']})
 assert len(c10['cost_panel'][ds]['train']['ids'])==256 and len(c10['cost_panel'][ds][dv]['ids'])==128
save(P/'splits/populations.json',pop)
shutil.copyfile(OLD/'src/receiver_prompt.py',P/'src/receiver_prompt.py')
# Copy only the small existing paper sources, leaving all old assets read-only.
for f in (OLD/'paper').iterdir():
 if f.suffix in ['.tex','.bib']:shutil.copyfile(f,P/'paper'/f.name);index(f,'inherited paper source')
cfg={'task':'P2_CONFIDENCE_REFERENCE_BOUNDARIES','stage':P.name,'primary_stratum':'small_obqa_C','pairs':PAIRS,'datasets':DATASETS,'references':REFS,'actions':'independent R/b only; never choose Text versus C2C','models':e1['models'],'score':'ProbeMax','prefix':c0['prefix'],'probability':c0['probability'],'runtime':c0['runtime'],'label_token_rule':'own tokenizer non-special single tokens decoding.strip()==actual displayed label; dynamic K','alpha':.05,'delta_per_stratum':.10,'q_grid':[j/20 for j in range(1,21)],'p_cutoff':.001,'CP_quantile':.999,'tests_per_stratum':20,'ideal_Bonferroni_per_stratum':.02,'joint_eight_FWER_claim':False,'threshold':'integer rank ceil(j*N_fit/20); FP32 zeros and all ties retained; q1 fixed R','selection':'largest accepted q else fixed reference; constants pay zero online probe','lambda':.01,'c_ref':'each pair/dataset original train256 R latency mean','cost':'new per-id probe/selector plus original complete action request on exact dev128 panel; no KV discount or E2E claim','bootstrap':{'seed':0,'replicates':2000,'unit':'independent question group; Text/C share indices; full and panel separate'},'resources':{**c0['resources'],'prefill_attempt_cap':7044,'fit_attempt_cap':0,'new_calibration_cap':140,'new_deployment_question_evaluations_cap':3422,'preparation_reporting_CPU_reserve':150},'reuse':{'large_obqa_probes':4208,'calibration_items':20,'large_obqa_Text_evaluations':742},'new_protocol_requests':0,'helper_forwards':0,'answer_generation':0,'ARC_test_read':False,'D':'learned control only; no rescue variants','exposure':c0['historical_exposure'],'ordering':['prepare label-free groups and freeze scientific rules','receiver train fit/cal probes','fit representative thresholds freeze','read only cal machine d','freeze deployments','dev probes then routes','after ALL routes associate V2 correctness/gold and report all strata'],'ARC_split':'new risk table independent of old five-fold: whitespace normalization, min-id group representative, sort then random.Random(0), first floor(.6G) complete groups fit; representatives only for calibration'}
save(P/'frozen_config.json',cfg);csvout(P/'SOURCE_INDEX.csv',sources)
freeze('SPLIT_FREEZE.json',list((P/'splits').glob('*'))+list((P/'inputs').glob('*')),outcomes_used=False)
freeze('PROTOCOL_FREEZE.json',[P/'frozen_config.json',P/'SOURCE_INDEX.csv',P/'protocol/MODEL_SOURCE_INDEX.json'],probes=0)
save(P/'SESSION_RESUME_ZH.json',{'stage':'PREPARED','job_id':None,'successful_ids_file':'records/probe_records.jsonl','prefill_attempts':0,'remaining_probe_attempts':7044,'new_cal':0,'new_evaluations':0,'submission_count':0,'config_sha256':sha(P/'frozen_config.json'),'note':'仅本轮预算；禁止第二提交；D仅对照；压缩时更新此记录并提示Work'})
print(json.dumps({'stage':str(P),'populations':pop,'config_sha256':sha(P/'frozen_config.json')},ensure_ascii=False))
