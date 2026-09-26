"""First question/options access. Never project answerKey before predictions."""
from common import *
import collections
compute();verify_freeze('PRE_TEST_FREEZE.json')
assert not (P/'FIRST_TEST_ACCESS.json').exists()
s=CFG['population'];path=Path(s['local_file'])
assert path.stat().st_size==s['expected_bytes'] and sha(path)==s['expected_sha256']
import pyarrow.parquet as pq
save(P/'FIRST_TEST_ACCESS.json',{'utc':utc(),'ARC_TEST_ACCESSED':True,'event':'immediately before first projected parquet read','columns':['id','question','choices'],'gold_column_read':False,'pre_test_freeze_sha256':sha(P/'PRE_TEST_FREEZE.json'),'source_sha256':s['expected_sha256'],'job_id':os.environ['PBS_JOBID']})
raw=pq.read_table(path,columns=['id','question','choices'],use_threads=False).to_pylist()
assert len(raw)==1172,'SEMANTIC_BLOCKED: unexpected population N'
queries=[];groups=collections.defaultdict(list)
for ordinal,r in enumerate(raw):
 assert set(r)=={'id','question','choices'} and isinstance(r['id'],str) and isinstance(r['question'],str)
 labels,texts=r['choices']['label'],r['choices']['text']
 assert len(labels)==len(texts) and 1<=len(labels)<=26 and len(set(labels))==len(labels)
 assert all(isinstance(x,str) for x in labels+texts)
 disp=[chr(65+j) for j in range(len(labels))]
 q={'id':r['id'],'ordinal':ordinal,'question_stem':r['question'],'choice_labels':disp,'choice_text':texts,'original_choice_labels':labels,'display_label_map':dict(zip(labels,disp))}
 queries.append(q);groups[signature(q)].append(q['id'])
assert len({r['id'] for r in queries})==1172,'SEMANTIC_BLOCKED: nonunique original ID'
lookup={i:(min(ids),hashlib.sha256(sig.encode()).hexdigest()) for sig,ids in groups.items() for i in ids}
for q in queries:q.update(group_representative=lookup[q['id']][0],group_sha256=lookup[q['id']][1],primary=q['id']==lookup[q['id']][0])
writejl(P/'inputs/test_queries_no_gold.jsonl',queries)
save(P/'inputs/ordered_test_ids.json',[r['id'] for r in queries]);save(P/'inputs/representative_ids.json',[r['id'] for r in queries if r['primary']])
csvout(P/'inputs/group_members.csv',[{k:r[k] for k in ['id','ordinal','group_representative','group_sha256','primary']} for r in queries])
save(P/'evidence/SEALED_EXPOSURE_RECEIPT.json',{'utc':utc(),'N':len(queries),'independent_groups':len(groups),'duplicate_groups':[{'representative':min(v),'ids':v} for v in groups.values() if len(v)>1],'gold_read':False,'columns_projected':['id','question','choices'],'first_test_access_sha256':sha(P/'FIRST_TEST_ACCESS.json'),'schema_validation':'PASSED expected schema','rows_deleted':0,'source_order_preserved':True,'choice_count_distribution':dict(collections.Counter(len(r['choice_text']) for r in queries))})
freeze('TEST_POPULATION_FREEZE.json',list((P/'inputs').glob('*'))+[P/'FIRST_TEST_ACCESS.json',P/'evidence/SEALED_EXPOSURE_RECEIPT.json'],gold_read=False,N=1172,groups=len(groups))
print('TEST_POPULATION_FROZEN',1172,len(groups),'gold column not read',flush=True)
