import json,hashlib,sys
from pathlib import Path
import pyarrow.parquet as pq
ROOT=Path('$DATA_DIR')
BOUND=ROOT/'P2_CONFIDENCE_REFERENCE_BOUNDARIES_20260914T165012Z'
DS=Path('$DATA_DIR/c2c_reproduction_assets/datasets/allenai--openbookqa')
def read(p):return json.loads(Path(p).read_text())
def jl(p):return [json.loads(s) for s in Path(p).open() if s.strip()]
rows={}
for split in ['train','validation','test']:
    t=pq.read_table(DS/'additional'/f'{split}-00000-of-00001.parquet').to_pylist()
    for r in t: rows.setdefault(r['id'],[]).append((split,r))
print('additional columns:',list(pq.read_schema(DS/'additional'/'train-00000-of-00001.parquet').names))
print('additional rows per split:',{s:sum(1 for v in rows.values() for sp,_ in v if sp==s) for s in ['train','validation','test']})
print('unique ids:',len(rows),'dup ids:',sum(1 for v in rows.values() if len(v)>1))
cal=read(BOUND/'splits/obqa_cal_ids.json');dev=read(BOUND/'splits/obqa_dev_ids.json');fit=read(BOUND/'splits/obqa_fit_ids.json')
q={r['id']:r for s in ['train','dev'] for r in jl(BOUND/f'inputs/obqa_{s}_queries.jsonl')}
out={}
for name,ids in [('cal',cal),('dev',dev),('fit16',fit[:16])]:
    miss=[i for i in ids if i not in rows]
    nofact=[i for i in ids if i in rows and not (rows[i][0][1].get('fact1') or '').strip()]
    stems=[i for i in ids if i in rows and str(rows[i][0][1].get('question_stem','')).strip()!=str(q[i]['question_stem']).strip()]
    out[name]={'n':len(ids),'missing_id':len(miss),'missing_fact1':len(nofact),'question_stem_mismatch':len(stems),
               'examples_missing':miss[:5],'examples_nofact':nofact[:5],'stem_mismatch_examples':stems[:3]}
    print(name,out[name])
# fact1 length stats
import statistics
fl=[len((rows[i][0][1]['fact1'] or '')) for i in cal+dev if i in rows]
print('fact1 chars: mean %.1f max %d min %d'%(statistics.mean(fl),max(fl),min(fl)))
print('split of cal/dev ids in additional:',{n:sorted({rows[i][0][0] for i in ids if i in rows}) for n,ids in [('cal',cal),('dev',dev),('fit16',fit[:16])]})
Path(sys.argv[1]).write_text(json.dumps({'dataset_revision':'388097ea7776314e93a529163e0fea805b8a6454','local_path':str(DS),'config':'additional','coverage':out,'fact1_chars_mean':statistics.mean(fl),'fact1_chars_max':max(fl)},indent=2)+'\n')
