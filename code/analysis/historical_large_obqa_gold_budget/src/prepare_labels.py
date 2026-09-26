from numerics import *
assert (P/'SUBSETS_FREEZE.json').exists()
for f,h in read(P/'SUBSETS_FREEZE.json')['files'].items():assert sha(P/f)==h
subsets={c['name']:read(P/c['subset_file']) for c in CFG['configs']};needed=set(i for ids in subsets.values() for i in ids)
# Select only y_R for the union of prescribed subsets; no y_T/d/cal correctness supplied.
lookup={}
for r in jl(OLD/'inputs/baseline_fit.jsonl'):
 if r['id'] in needed:lookup[r['id']]=int(r['y_R'])
assert set(lookup)==needed
for name,ids in subsets.items():writejl(P/f'inputs/{name}_labels.jsonl',({'id':i,'y_R':lookup[i]} for i in ids))
freeze('LABEL_INTERFACES_FREEZE.json',[P/f'inputs/{n}_labels.jsonl' for n in subsets],columns=['id','y_R'],unique_gold_union=len(needed),labels_after_subsets_freeze=True,preparation_preview_exception='evidence/PREPARATION_DEVIATION.json')
