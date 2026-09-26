"""Lightweight source/ID projection only; no scoring or model loading."""
from common import *
import shutil
assert not (P/'PROTOCOL_FREEZE.json').exists()
old=read(E2E/'frozen_config.json');bc=read(BOUND/'frozen_config.json');c10=read(P10/'frozen_config.json');deps=read(BOUND/'deployments/all.json')
native={k:old['native'][k] for k in ['models','fuser','receiver_generation_config','dtype','attention','tf32','thinking','generation_seed','helper_text_max_new_tokens','receiver_max_new_tokens','R_T_C_calls','C_helper_tokenizer']}
assert native['models']['receiver']['revision']==bc['models']['large']['revision']
sources={}
def index(p,role):
 p=Path(p);sources[str(p)]={'path':str(p),'bytes':p.stat().st_size,'sha256':sha(p),'role':role}
for p in [BOUND/'HANDOFF_ZH.md',BOUND/'frozen_config.json',BOUND/'summary/panel_source_checks.json',BOUND/'summary/panel_cost.csv',BOUND/'records/panel_per_question.jsonl',BOUND/'deployments/all.json',BOUND/'src/run_boundaries.py',BOUND/'ALL_ROUTES_FREEZE.json',E2E/'native_adapter.py',E2E/'execute_e2e.py',E2E/'frozen_config.json',E2E/'SOURCE_INDEX.json',P10/'frozen_config.json',V2/'scoring_v2.py',V2/'labels/panel_development_P2_SCORING_V2.jsonl']:index(p,'direct frozen provenance')
# Preserve prior model/fuser manifests; weights are stat-checked, no copies/downloads.
for r in read(E2E/'SOURCE_INDEX.json'):
 p=Path(r['path'])
 if (str(p).startswith(str(P10)) and p.suffix=='.py') or any(str(p).startswith(s['path']+'/') for s in native['models'].values()) or str(p).startswith(native['fuser']['path']+'/'):
  assert p.exists() and p.stat().st_size==r['bytes'];sources[str(p)]=r
# Directly referenced runtime projector implementation only.
for p in (P10/'runtime_source/rosetta/model').glob('*.py'):index(p,'official transplanted projector source')
for name in ['receiver_prompt.py']:shutil.copyfile(BOUND/'src'/name,P/'src'/name);index(BOUND/'src'/name,'exact frozen query formatter')
for f in (BOUND/'protocol/large').iterdir():
 if f.is_file():shutil.copyfile(f,P/'protocol'/f.name);index(f,'frozen tokenizer/probe protocol')
panel=[]
for ds in ['obqa','arc']:
 orig='dev' if ds=='obqa' else 'validation';ids=read(BOUND/f'inputs/{ds}_panel_ids.json')['dev'];assert ids==c10['cost_panel'][ds][orig]['ids'] and len(set(ids))==128
 save(P/f'inputs/{ds}_panel_ids.json',ids);index(BOUND/f'inputs/{ds}_panel_ids.json','original panel identity')
 qmap={r['id']:r for r in jl(BOUND/f'inputs/{ds}_dev_queries.jsonl')};writejl(P/f'inputs/{ds}_queries.jsonl',[qmap[i] for i in ids]);index(BOUND/f'inputs/{ds}_dev_queries.jsonl','label-free queries')
 for suf in ['cost_panel_matrix.npz','cost_panel_originals.jsonl']:index(P10/f'results/large/{ds}/{orig}_{suf}','same-block historical full action requests')
 index(P10/f'results/large/{ds}/train_cost_panel_matrix.npz','frozen train c_ref source')
 for b in ['T','C']:
  tag=f'large_{ds}_{b}';dep=deps[tag];assert dep['mode']=='selective' and dep['q']=={('obqa','T'):.8,('obqa','C'):.8,('arc','T'):.95,('arc','C'):.9}[ds,b]
  save(P/f'protocol/{tag}_deployment.json',dep)
  for suf in ['.json','_FREEZE.json','_ROUTES_FREEZE.json']:index(BOUND/f'deployments/{tag}{suf}','unchanged frozen deployment')
  src=BOUND/f'records/{tag}_routes.jsonl';rmap={r['id']:r for r in jl(src)};writejl(P/f'inputs/{tag}_expected_routes.jsonl',[rmap[i] for i in ids]);index(src,'frozen per-id score/input hash/route identity')
  panel.append({'dataset':ds,'reference':b,'q':dep['q'],'threshold':dep['threshold'],'N':128})
for f in (BOUND/'paper').iterdir():
 if f.suffix in ['.tex','.bib']:shutil.copyfile(f,P/'paper'/f.name);index(f,'continuation of accepted manuscript')
for name in ['reference_boundaries.pdf','reference_boundaries.png']:
 shutil.copyfile(BOUND/'figures'/name,P/'figures'/name);index(BOUND/'figures'/name,'unchanged boundary figure')
cfg={'task':'P2_FROZEN_POLICY_E2E_VALIDATION','stage':P.name,'parent':str(BOUND),'native_root':str(P10),'native':native,'parser_path':str(V2/'scoring_v2.py'),'parser_sha256':sha(V2/'scoring_v2.py'),'strata':panel,'prefix':bc['prefix'],'probe_protocol':str(BOUND/'protocol/large/PROBE_PROTOCOL_FREEZE.json'),'score':'exact frozen FP32 ProbeMax; u<=threshold; all ties; no KV/prefill reuse','label_sets':'protocol/label_token_sets.json','topology':{'GPU_count':2,'helper':'cuda:0','receiver_fuser':'cuda:1','single_node':True,'one_residency':True},'order':{'tasks':['obqa','arc'],'paths':['policy_T','reference_T','policy_C','reference_C'],'rotation':'left by canonical panel ordinal modulo 4; original panel order'},'counts':{'complete_action_attempt_cap':1024,'online_policy_probe_cap':512,'fixed_reference_requests':512,'warmup':0,'retry':0,'new_fits':0,'new_calibration':0,'new_gold':0,'old_probe_reacquisition':0},'timing':'outer synchronized wall: query fields, tokenization/prefix/transfer/backbone/last projection/FP32 score, selector, complete native action, decode, V2 parse, hook cleanup; I/O/diagnostics/gold excluded; startup separate','accuracy':'reuse existing V2 gold after all replay outputs; same parser, INVALID distinct from execution failure','bootstrap':{'seed':0,'replicates':2000,'unit':'independent panel question group','shared_indices':'Text/C2C within each task','CI':'paired percentile 95%; descriptive exposed panel only'},'savings_confirmation':'positive paired mean AND positive lower descriptive 95% interval; no population/FWER/equivalence claim','lambda':.01,'c_ref':{r['dataset']:r['c_ref_train256_R_ms'] for r in read(BOUND/'summary/panel_source_checks.json') if r['pair']=='large'},'resources':{'account':'project','queue':'gpu-queue','select':2,'GPU_count':2,'wall_seconds':1800,'max_GPU_allocation_hours':1.,'CPU_cap_seconds':1500,'preparation_reporting_reserve':180,'threads':1,'max_submissions':1,'python':old['resources']['python']},'failures':'zero retries; stop on identity/runtime failure, preserve completed keys and budgets, PARTIAL/BLOCKED; no second job','small':'all four fixed-reference fallbacks retained; no replay','ARC_test_read':False,'D':'learned control only','ProbeMax':'ordinary confidence baseline'}
save(P/'frozen_config.json',cfg);save(P/'SOURCE_INDEX.json',list(sources.values()))
freeze('PROTOCOL_FREEZE.json',[P/'frozen_config.json',P/'SOURCE_INDEX.json']+list((P/'inputs').glob('*'))+list((P/'protocol').glob('*')),new_action_requests=0,new_online_probes=0)
print(P,sha(P/'frozen_config.json'))
