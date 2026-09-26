from common import *
compute()
import numpy as np
c10=read(P10/'frozen_config.json')
labels={(r['dataset'],r['id']):r for r in jl(V2/'labels/panel_development_P2_SCORING_V2.jsonl') if r['pair']=='large'}
components=[r for r in jl(BOUND/'records/panel_per_question.jsonl') if r['pair']=='large' and r['policy'] in ['ProbeMax','Fixed_reference']]
checks=[];evaluation=[];comp=[]
for ds in ['obqa','arc']:
 ids=read(P/f'inputs/{ds}_panel_ids.json');orig='dev' if ds=='obqa' else 'validation'
 assert ids==c10['cost_panel'][ds][orig]['ids']==read(BOUND/f'inputs/{ds}_panel_ids.json')['dev']
 queries=jl(P/f'inputs/{ds}_queries.jsonl');assert [r['id'] for r in queries]==ids
 signatures=[' '.join(('\n'.join(['Question: '+r['question_stem'],'Choices:']+[a+': '+b for a,b in zip(r['choice_labels'],r['choice_text'])])).split()) for r in queries];assert len(set(signatures))==128
 source=next(r for r in read(BOUND/'summary/panel_source_checks.json') if r['pair']=='large' and r['dataset']==ds)
 assert sha(source['source_cost'])==source['cost_sha256']
 z=np.load(source['source_cost'],allow_pickle=False);assert z['ids'].tolist()==ids
 assert z['actions'].tolist()==['receiver_only','text','c2c','acw']
 tr=np.load(P10/f'results/large/{ds}/train_cost_panel_matrix.npz',allow_pickle=False)
 assert tr['ids'].tolist()==c10['cost_panel'][ds]['train']['ids'] and float(tr['latency_ms'][:,0].mean())==CFG['c_ref'][ds]
 raw={(r['id'],r['action']):r for r in jl(P10/f'results/large/{ds}/{orig}_cost_panel_originals.jsonl')}
 for j,i in enumerate(ids):
  r=labels[ds,i];assert r['legal_labels']==queries[j]['choice_labels']
  block=[raw[i,a] for a in z['actions'].tolist()];assert len({v['block_id'] for v in block})==len({v['job_id'] for v in block})==1
  for ai,a in enumerate('RTCA'):
   rr=block[ai];assert rr['runtime_error'] is None and rr['latency_ms']==float(z['latency_ms'][j,ai]);assert hashlib.sha256(rr['raw_answer'].encode()).hexdigest()==r['source_'+a]['raw_sha256']
  evaluation.append({'dataset':ds,'id':i,'group':i,'gold':r['gold'],'legal_labels':r['legal_labels'],**{k:r[k] for k in r if k.startswith(('o_','y_','valid_','source_'))}})
 for b in ['T','C']:
  expected=jl(P/f'inputs/large_{ds}_{b}_expected_routes.jsonl');assert [r['id'] for r in expected]==ids
  d=read(P/f'protocol/large_{ds}_{b}_deployment.json')
  for r in expected:assert r['route']==('R' if r['ProbeMax']<=d['threshold'] else b)
  cp={r['id']:r for r in components if r['dataset']==ds and r['reference']==b and r['policy']=='ProbeMax'}
  cr={r['id']:r for r in components if r['dataset']==ds and r['reference']==b and r['policy']=='Fixed_reference'}
  for i in ids:comp.append({'dataset':ds,'reference':b,'id':i,'old_policy_ms':cp[i]['total_ms'],'old_action_ms':cp[i]['historical_action_ms'],'old_probe_selector_ms':cp[i]['probe_selector_ms'],'old_reference_ms':cr[i]['total_ms'],'old_net_saving_ms':cr[i]['total_ms']-cp[i]['total_ms']})
 checks.append({**source,'ordered_ids_sha256':sha(P/f'inputs/{ds}_panel_ids.json'),'query_sha256':sha(P/f'inputs/{ds}_queries.jsonl'),'current_recheck':True,'unique_groups':128})
writejl(P/'inputs/evaluation_existing_gold.jsonl',evaluation);writejl(P/'inputs/component_estimates.jsonl',comp)
save(P/'evidence/panel_source_checks.json',checks)
freeze('PANEL_VALIDATION_FREEZE.json',[P/'inputs/evaluation_existing_gold.jsonl',P/'inputs/component_estimates.jsonl',P/'evidence/panel_source_checks.json'],new_requests=0,scope='identity validation only; existing gold isolated from runtime')
print('PANEL_SOURCE_VALIDATION_PASSED',flush=True)
