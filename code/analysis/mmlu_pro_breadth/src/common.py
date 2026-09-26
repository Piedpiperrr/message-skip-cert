import os,sys,json,csv,time,datetime,hashlib,importlib.util
from pathlib import Path
sys.dont_write_bytecode=True
P=Path(__file__).resolve().parents[1]
ROOT=P.parent
DATA_ROOT=ROOT.parent.parent
REVIEW=ROOT/'P2_MMLU_PRO_BREADTH_PROTOCOL_AND_COST_REVIEW_20260915T224801Z'
NATIVE=ROOT/'P2_10_20260911T122423Z'
PYTHON=DATA_ROOT/'software/envs/c2c_official/bin/python'
SHARD=os.environ.get('MMLU_SHARD','')
S=P/'shards'/SHARD if SHARD else None
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
def project_queries():
    return {r['id']:{k:r[k] for k in ['id','question_stem','choice_labels','choice_text']} for r in rows(P/'inputs/queries_only.jsonl') if r['source_split']=='test'}
def ids(split,reps=False):
    return [g['representative_id'] for g in read(P/f'splits/{split}_groups.json')] if reps else read(P/f'splits/{split}_ids.json')
def stop_check():
    if time.time()>float(os.environ.get('MMLU_DEADLINE_EPOCH','inf')):raise RuntimeError('WALLTIME_BUDGET_STOP_NO_REPLACEMENT')
    if (P/'STOP').exists():raise RuntimeError('EXPLICIT_STOP')
def validate_freeze():
    f=read(P/'MMLU_PRO_STAGE1_PROTOCOL_FREEZE.json')
    assert f['MMLU_PRO_OUTCOMES_OBSERVED'] is False
    for path,h in f['frozen_files'].items():assert sha(P/path)==h,path
    for path,h in f['native_source_hashes'].items():assert sha(path)==h,path
    return f
def resolved_paths():
    m=read(P/'MODEL_SOURCE_INDEX.json')['models']
    v={r:spec['path'] for r,spec in m.items()}
    v.update(dataset=P/'inputs',output=P/'shards',checkpoint='none',log=os.environ.get('P2_RUN',str(P/'evidence')),temporary=os.environ.get('TMPDIR',str(DATA_ROOT/'tmp/p2_mmlu_stage1_cpu')),PBS_logs=DATA_ROOT/'logs/pbs')
    for k,z in os.environ.items():
        if 'CACHE' in k or k in ['HF_HOME','TORCH_HOME','MPLCONFIGDIR']:v[k]=z
    for k,z in v.items():
        if z!='none':
            v[k]=str(Path(z).resolve());assert v[k].startswith(str(DATA_ROOT)+'/'),(k,v[k])
    return v
