import os,sys,json,csv,time,datetime,hashlib,importlib.util
from pathlib import Path
sys.dont_write_bytecode=True
P=Path(__file__).resolve().parents[1]
ROOT=P.parent
DATA_ROOT=ROOT.parent.parent
STAGE1=ROOT/'P2_MMLU_PRO_BREADTH_STAGE1_20260916T002337Z'
REVIEW=ROOT/'P2_MMLU_PRO_BREADTH_PROTOCOL_AND_COST_REVIEW_20260915T224801Z'
NATIVE=ROOT/'P2_10_20260911T122423Z'
PYTHON=DATA_ROOT/'software/envs/c2c_official/bin/python'
FREEZE=P/'MMLU_PRO_E2E_STAGE2_FREEZE.json'
PARENT_HASH='c6300cff73ef096c81fb07cdab3eef68050265fec97ec2fcecfbf94e25a38624'
ARMS=['fixed_T','policy_T','fixed_C','policy_C']
THRESHOLD=3.838539123535156e-05
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
    p=Path(p);assert p.is_relative_to(P) or p.is_relative_to(DATA_ROOT/'runs/iclr2027_p2')
    p.parent.mkdir(parents=True,exist_ok=True);tmp=p.with_suffix(p.suffix+'.tmp')
    tmp.write_text(json.dumps(v,ensure_ascii=False,indent=2,allow_nan=False)+'\n');tmp.replace(p)
def append(p,v):
    p=Path(p);assert p.is_relative_to(P)
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('a') as f:f.write(json.dumps(v,ensure_ascii=False,allow_nan=False)+'\n');f.flush();os.fsync(f.fileno())
def write_rows(p,rr):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('w') as f:
        for r in rr:f.write(json.dumps(r,ensure_ascii=False,allow_nan=False)+'\n')
def csvout(p,rr):
    rr=list(rr);p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(dict.fromkeys(k for r in rr for k in r)) if rr else ['empty']);w.writeheader();w.writerows(rr)
def load_module(path,name):
    s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def queryhash(q):return hashlib.sha256(json.dumps(q,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
def order_for(i):
    offset=i%4;return ARMS[offset:]+ARMS[:offset]
def stop_check():
    if time.time()>float(os.environ.get('MMLU_DEADLINE_EPOCH','inf')):raise RuntimeError('WALLTIME_STOP_NO_RESUBMISSION')
    if (P/'STOP').exists():raise RuntimeError('EXPLICIT_STOP_NO_RESUBMISSION')
def verify_freeze(include_weights=False):
    f=read(FREEZE);assert f['status']=='PASS' and f['MMLU_PRO_STAGE2_RESULTS_OBSERVED'] is False
    assert sha(STAGE1/'MMLU_PRO_STAGE1_PROTOCOL_FREEZE.json')==f['parent_Stage1_protocol_freeze_sha256']==PARENT_HASH
    for path,h in f['frozen_files'].items():assert sha(P/path)==h,path
    for path,h in f['source_hashes'].items():assert sha(path)==h,path
    if include_weights:
        for m in read(P/'MODEL_SOURCE_INDEX.json')['models'].values():
            for z in m['files']:assert sha(z['path'])==z['sha256'],z['path']
    return f
def resolved_paths():
    models=read(P/'MODEL_SOURCE_INDEX.json')['models'];out={r:z['path'] for r,z in models.items()}
    out.update(dataset=P/'inputs',output=P/'records',artifacts=P,checkpoint='none',log=os.environ.get('P2_RUN',str(P/'evidence')),
        temporary=os.environ.get('TMPDIR',str(DATA_ROOT/'tmp/p2_mmlu_stage2_cpu')),PBS_logs=DATA_ROOT/'logs/pbs',python=PYTHON)
    for k,z in os.environ.items():
        if 'CACHE' in k or k in ['HF_HOME','TORCH_HOME','MPLCONFIGDIR']:out[k]=z
    for k,z in out.items():
        if z!='none':out[k]=str(Path(z).resolve());assert out[k].startswith(str(DATA_ROOT)+'/'),(k,out[k])
    return out
