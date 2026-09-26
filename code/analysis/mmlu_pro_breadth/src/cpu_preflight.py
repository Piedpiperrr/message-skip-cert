from common import *
import ast,collections,math,types
from transformers import AutoTokenizer,GenerationConfig
from risk import thresholds,calibrate
assert not os.environ.get('CUDA_VISIBLE_DEVICES','')
assert not (P/'MMLU_PRO_STAGE1_PROTOCOL_FREEZE.json').exists()
print('RESOLVED_PATHS',json.dumps(resolved_paths()),flush=True)
for f in (P/'src').glob('*.py'):ast.parse(f.read_text(),filename=str(f))
for f in (REVIEW/'candidates/PLAN_C').glob('*.json'):assert sha(f)==sha(P/'splits'/f.name),f
for f,h in read(P/'splits/MANIFEST.json')['hashes'].items():assert sha(P/'splits'/f)==h
for f,h in read(P/'RUNTIME_SOURCE_INDEX.json').items():assert sha(f)==h
parquet=REVIEW/'dataset/test-00000-of-00001.parquet'
assert sha(parquet)=='0e24a191921c2f453518a537a8b2117bd137e7714d4ef1565e9ba06c1ecb9ad8'
meta={r['id']:r for r in rows(P/'inputs/queries_only.jsonl') if r['source_split']=='test'}
assert len(meta)==12032
allids=[];allgroups=[];split_summary={}
for split,n,ng in [('fit',3093,3000),('cal',6196,6000),('dev',2743,2641)]:
    ii=ids(split);gg=read(P/f'splits/{split}_groups.json');assert len(ii)==n and len(gg)==ng
    members=[]
    for g in gg:
        assert g['representative_id']==min(g['members'],key=lambda x:int(x.split(':')[1]))
        normalized={' '.join(meta[x]['question_stem'].split()) for x in g['members']};assert len(normalized)==1
        assert hashlib.sha256(next(iter(normalized)).encode()).hexdigest()==g['group_hash']
        members+=g['members'];allgroups.append(g['group_hash'])
    assert sorted(members)==sorted(ii);allids+=ii
    split_summary[split]=dict(rows=n,groups=ng,category_rows=dict(sorted(collections.Counter(meta[x]['category'] for x in ii).items())),
        category_reps=dict(sorted(collections.Counter(meta[x]['category'] for x in ids(split,True)).items())),
        K_rows=dict(sorted(collections.Counter(meta[x]['K'] for x in ii).items())),K_reps=dict(sorted(collections.Counter(meta[x]['K'] for x in ids(split,True)).items())))
assert len(set(allgroups))==11641 and len(set(allids))==12032 and set(allids)==set(meta)
shards=read(P/'splits/STAGE1_CANDIDATE_SHARDS.json');combined=[]
for job in shards['jobs']:
    jj=sum((job[k] for k in ['fit','cal','dev']),[]);assert len(jj)==6016;combined+=jj
    save(P/f'splits/SHARD_{job["job"]}_FROZEN_IDS.json',dict(source_sha256=sha(P/'splits/STAGE1_CANDIDATE_SHARDS.json'),
        job=job['job'],fit=job['fit'],cal=job['cal'],dev=job['dev'],rows=6016,execution_order='fit/cal/dev; each row R,T,C,P; collection only'))
assert len(set(combined))==12032 and set(combined)==set(allids)
for split in ['fit','cal','dev']:assert sorted(sum((j[split] for j in shards['jobs']),[]))==sorted(ids(split))
prompt=load_module(P/'protocol/receiver_prompt.py','cpu_prompt');parser=load_module(P/'protocol/scoring_v2.py','cpu_parser')
old=load_module(NATIVE/'protocol_min.py','cpu_protocol');configs={};index=read(P/'MODEL_SOURCE_INDEX.json')
for role in ['helper','receiver']:
    cfg=GenerationConfig.from_pretrained(index['models'][role]['path'],local_files_only=True)
    dummy=types.SimpleNamespace(generation_config=cfg);old.apply_generation_config(dummy,dict(do_sample=False,max_new_tokens=64))
    configs[role]=cfg.to_dict()
assert configs['receiver']==read(P/'protocol/large_native_config.json')['receiver_generation_config']
save(P/'protocol/generation_configs.json',dict(model_generation_config_after_native_cleanup=configs,
    native_receiver_max_new_tokens=64,native_text_helper_max_new_tokens=256,do_sample=False,thinking=False,seed=0,
    helper_objective='one background sentence, do NOT solve',C2C='official prefix L-1 KV; 36 projectors; no helper decode'))
tok=AutoTokenizer.from_pretrained(index['models']['receiver']['path'],local_files_only=True)
sets={k:[] for k in 'ABCDEFGHIJ'}
for i in range(len(tok)):
    if i in tok.all_special_ids:continue
    d=tok.decode([i],skip_special_tokens=False,clean_up_tokenization_spaces=False).strip()
    if d in sets:sets[d].append(i)
assert sets==read(P/'protocol/label_token_sets.json')
cases=0
for K in range(3,11):
    labels=list('ABCDEFGHIJ')[:K];q=dict(id='SYNTHETIC',question_stem='Synthetic placeholder.',choice_text=['placeholder '+str(i) for i in range(K)],choice_labels=labels)
    body=prompt.receiver_prompt(q)
    assert '/'.join(labels) in body
    for label in labels:
        assert len(tok.encode(label,add_special_tokens=False))==1
        assert parser.parse_answer('The correct answer is '+label,labels)['answer']==label;cases+=1
    assert not parser.parse_answer('The correct answer is '+chr(65+K),labels)['valid']
    assert not parser.parse_answer('The correct answer is A or B',labels)['valid']
    if K==4:
        oq=dict(question_stem=q['question_stem'],choices={'text':q['choice_text']})
        assert body==old.format_openbook(oq)
    chat=tok.apply_chat_template([dict(role='user',content=body)],tokenize=False,add_generation_prompt=True,enable_thinking=False)
    assert tok(chat,add_special_tokens=True)['input_ids']==tok.apply_chat_template([dict(role='user',content=body)],tokenize=True,add_generation_prompt=True,enable_thinking=False)
assert tok.encode('The correct answer is',add_special_tokens=False)==[785,4396,4226,374]
assert thresholds(list(range(3000)))[:2]==[149,299]
assert calibrate([0]*135,[0]*135,[0]*19+['Infinity'])[1]['q']==1
assert calibrate([0]*134,[0]*134,[0]*19+['Infinity'])[1]['q']==0
save(P/'protocol/POPULATION_IDENTITY.json',dict(dataset_revision='b189ec765aa7ed75c8acfea42df31fdae71f97be',raw_rows=12032,groups=11641,
    split_summary=split_summary,category_counts=dict(sorted(collections.Counter(r['category'] for r in meta.values()).items())),K_distribution=dict(sorted(collections.Counter(r['K'] for r in meta.values()).items()))))
save(P/'protocol/QUERY_IDENTITIES.json',{x:queryhash(q) for x,q in project_queries().items()})
save(P/'evidence/CPU_PREFLIGHT.json',dict(status='PASS',utc=utc(),parser_legal_cases=cases,model_loads=0,model_forwards=0,GPU=0,
    all_candidate_manifests_unchanged=True,all_group_normalizations_verified=True,raw_parquet_sha256=sha(parquet),
    token_variants_reenumerated=True,receiver_generation_config_matches_frozen_large=True,risk_edge_checks='n=134 zero changes fail; n=135 pass',
    paths=resolved_paths()))
print('CPU_PREFLIGHT_PASS',flush=True)
