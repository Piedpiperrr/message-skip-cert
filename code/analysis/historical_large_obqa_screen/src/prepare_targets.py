from numerics import *
fit=read(P/'splits/fit_ids.json');cal=read(P/'splits/cal_ids.json');dev=read(P/'splits/dev_ids.json')
assert (P/'SPLIT_FREEZE.json').exists()
# Dedicated independent RNG. Freeze stream BEFORE reading any source label.
rng=np.random.Generator(np.random.PCG64(0))
for split,ids in [('cal',cal),('dev',dev)]:
 rows=[]
 for i in ids:
  t=time.perf_counter_ns();u=float(rng.random());ms=(time.perf_counter_ns()-t)/1e6
  rows.append({'id':i,'u':u,'rng_generation_ms':ms})
 writejl(P/f'splits/random_{split}.jsonl',rows)
freeze('RANDOM_FREEZE.json',[P/'splits/random_cal.jsonl',P/'splits/random_dev.jsonl'],rng='separate PCG64(seed=0), cal then dev, one coin/request',label_statistics_read=False)
labels={r['id']:r for r in jl(CFG['train_labels_source'])}
assert set(labels)==set(fit+cal)
for split,ids in [('fit',fit),('cal',cal)]:
 # Candidate and all calibrators are given only IDs, features and d.
 writejl(P/f'inputs/candidate_{split}.jsonl',({'id':i,'d':int(labels[i]['o_R']!=labels[i]['o_T'])} for i in ids))
writejl(P/'inputs/baseline_fit.jsonl',({'id':i,'y_R':labels[i]['y_R'],'y_T':labels[i]['y_T'],'harm':int(labels[i]['y_R']==0 and labels[i]['y_T']==1)} for i in fit))
freeze('TARGET_INTERFACE_FREEZE.json',[P/'inputs/candidate_fit.jsonl',P/'inputs/candidate_cal.jsonl',P/'inputs/baseline_fit.jsonl'],candidate_columns=['id','d'],baseline_calibration_columns=['id','d'],cal_gold_used=False)
