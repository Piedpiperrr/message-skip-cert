"""E8 shared helpers. Same conventions as the frozen MMLU-Pro Stage1 src/common.py;
only the pair indirection and the multi-slot/resumable bookkeeping are new."""
import os,sys,json,csv,time,datetime,hashlib,importlib.util
from pathlib import Path
sys.dont_write_bytecode=True
P=Path(__file__).resolve().parents[1]
ROOT=P.parent
DATA_ROOT=ROOT.parent.parent
NATIVE=ROOT/'P2_10_20260911T122423Z'
MMLU=ROOT/'P2_MMLU_PRO_BREADTH_STAGE1_20260916T002337Z'
MEDIUM=ROOT/'P2_MEDIUM_PAIR_BOUNDARY_EXTENSION_STAGE1_20260915T144407Z/execution_retry1_20260915T164957Z'
MEDIUMP=ROOT/'P2_MEDIUM_PAIR_BOUNDARY_EXTENSION_STAGE1_20260915T144407Z'
BND=ROOT/'P2_CONFIDENCE_REFERENCE_BOUNDARIES_20260914T165012Z'
PYTHON=DATA_ROOT/'software/envs/c2c_official/bin/python'
PAIR=os.environ.get('E8_PAIR','')
SLOT=os.environ.get('E8_SLOT','')

def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
    return h.hexdigest()
def read(p):return json.loads(Path(p).read_text())
def rows(p):
    with Path(p).open() as f:return [json.loads(x) for x in f if x.strip()]
def save(p,v):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);t=p.with_suffix(p.suffix+'.tmp')
    t.write_text(json.dumps(v,ensure_ascii=False,indent=2,allow_nan=False)+'\n');t.replace(p)
def append(p,v):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('a') as f:f.write(json.dumps(v,ensure_ascii=False,allow_nan=False)+'\n');f.flush();os.fsync(f.fileno())
def write_rows(p,v):
    Path(p).parent.mkdir(parents=True,exist_ok=True)
    with Path(p).open('w') as f:
        for r in v:f.write(json.dumps(r,ensure_ascii=False,allow_nan=False)+'\n')
def csvout(p,v):
    v=list(v);Path(p).parent.mkdir(parents=True,exist_ok=True)
    with Path(p).open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(dict.fromkeys(k for r in v for k in r)) if v else ['empty']);w.writeheader();w.writerows(v)
def load_module(path,name):
    s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def queryhash(q):return hashlib.sha256(json.dumps(q,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()

# --- pair indirection: the ONLY thing that differs between the four E8 settings and the frozen large run ---
def pair_config(pair):
    """Model/fuser index and expected generation configs for one pair.
    'large' points at the frozen Stage1 files and is never rewritten (validation (b) control)."""
    if pair=='large':
        index=read(MMLU/'MODEL_SOURCE_INDEX.json')
        native=read(MMLU/'protocol/large_native_config.json')
        mapping={int(k):tuple(v[0]) for k,v in native['fuser']['projector_config']['0']['1'].items()}
        return dict(pair='large',index=index,index_path=str(MMLU/'MODEL_SOURCE_INDEX.json'),
            expected=read(MMLU/'protocol/generation_configs.json')['model_generation_config_after_native_cleanup'],
            expected_path=str(MMLU/'protocol/generation_configs.json'),
            fuser_path=Path(index['models']['fuser']['path']),projector_count=36,mapping=mapping)
    index=read(P/f'MODEL_SOURCE_INDEX_{pair}.json')
    f=index['models']['fuser']
    return dict(pair=pair,index=index,index_path=str(P/f'MODEL_SOURCE_INDEX_{pair}.json'),
        expected=read(P/f'protocol/generation_configs_{pair}.json')['model_generation_config_after_native_cleanup'],
        expected_path=str(P/f'protocol/generation_configs_{pair}.json'),
        fuser_path=Path(f['path']),projector_count=f['projector_count'],
        mapping={int(k):tuple(v) for k,v in f['mapping'].items()})

def project_queries():
    return {r['id']:{k:r[k] for k in ['id','question_stem','choice_labels','choice_text']}
            for r in rows(P/'inputs/queries_only.jsonl') if r['source_split']=='test'}
def query_meta():
    return {r['id']:r for r in rows(P/'inputs/queries_only.jsonl') if r['source_split']=='test'}
def ids(split,reps=False):
    return [g['representative_id'] for g in read(P/f'splits/{split}_groups.json')] if reps else read(P/f'splits/{split}_ids.json')
def stop_check():
    if time.time()>float(os.environ.get('E8_DEADLINE_EPOCH','inf')):raise RuntimeError('WALLTIME_BUDGET_STOP')
    if (P/'STOP').exists():raise RuntimeError('EXPLICIT_STOP')
def freeze_hash():return sha(P/'PROTOCOL_FREEZE_E8.md')
def validate_freeze():
    f=read(P/'FREEZE_INDEX_E8.json')
    assert f['PROTOCOL_FREEZE_E8_sha256']==freeze_hash(),'PROTOCOL_FREEZE_E8.md changed after freeze'
    for path,h in f['frozen_files'].items():assert sha(P/path)==h,path
    for path,h in f['external_source_hashes'].items():assert sha(path)==h,path
    return f
