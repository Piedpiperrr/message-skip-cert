import csv,datetime,hashlib,json,os,sys,time
from pathlib import Path
P=Path(__file__).resolve().parents[1]
ROOT=P.parent
DATA_ROOT=ROOT.parent.parent
PARENT=ROOT/'P2_MEDIUM_PAIR_BOUNDARY_EXTENSION_STAGE1_20260915T144407Z'
STAGE1=PARENT/'execution_retry1_20260915T164957Z'
NATIVE=ROOT/'P2_10_20260911T122423Z'
PYTHON=DATA_ROOT/'software/envs/c2c_official/bin/python'
FREEZE=P/'MEDIUM_PAIR_E2E_STAGE2_FREEZE.json'
PARENT_HASH='c4b85ca697030ca115020fdb959143c8c4901135a5b876cf716bf4b6a4c94bf8'
def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
    return h.hexdigest()
def read(path):return json.loads(Path(path).read_text())
def rows(path):
    with Path(path).open() as f:return [json.loads(s) for s in f if s.strip()]
def save(path,value):
    path=Path(path);assert path.is_relative_to(P) or path.is_relative_to(DATA_ROOT/'runs/iclr2027_p2')
    path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_suffix(path.suffix+'.tmp')
    tmp.write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n');tmp.replace(path)
def append(path,value):
    path=Path(path);assert path.is_relative_to(P)
    with path.open('a') as f:f.write(json.dumps(value,ensure_ascii=False,allow_nan=False)+'\n');f.flush();os.fsync(f.fileno())
def write_rows(path,rr):
    path=Path(path);assert path.is_relative_to(P)
    with path.open('w') as f:
        for r in rr:f.write(json.dumps(r,ensure_ascii=False,allow_nan=False)+'\n')
def csvout(path,rr):
    rr=list(rr)
    with Path(path).open('w',newline='') as f:
        keys=list(dict.fromkeys(k for r in rr for k in r)) if rr else ['empty']
        w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows(rr)
def load_module(path,name):
    import importlib.util
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def stop_check():
    if time.time()>float(os.environ.get('P2_MEDIUM_DEADLINE','inf')):raise RuntimeError('WALLTIME_BUDGET_STOP_NO_RESUBMISSION')
    if (P/'STOP').exists():raise RuntimeError('EXPLICIT_STOP_NO_RESUBMISSION')
def verify_freeze(include_weights=True):
    f=read(FREEZE);assert f['status']=='PASS' and f['MEDIUM_STAGE2_RESULTS_OBSERVED'] is False
    assert sha(P/'SOURCE_INDEX.json')==f['source_index_sha256']
    assert sha(PARENT/'MEDIUM_PAIR_PROTOCOL_FREEZE.json')==f['parent_Stage1_scientific_freeze_sha256']==PARENT_HASH
    for path,h in f['frozen_files'].items():assert sha(path)==h,path
    for path,h in f['runtime_source_hashes'].items():assert sha(path)==h,path
    if include_weights:
        for role,m in f['models'].items():
            for ff in m['local_files']:assert sha(ff['path'])==ff['sha256'],ff['path']
    return f
def paths():
    values={'helper':P/'assets/helper','receiver':P/'assets/receiver','fuser':P/'assets/fuser',
        'dataset':P/'inputs','output':P,'checkpoint':P/'assets','log':os.environ.get('P2_RUN',str(P/'evidence')),
        'PBS_logs':DATA_ROOT/'logs/pbs','temporary':os.environ.get('TMPDIR',str(DATA_ROOT/'tmp/p2_medium_stage2')),'python':PYTHON}
    for k,v in os.environ.items():
        if 'CACHE' in k or k in ['HF_HOME','TORCH_HOME','MPLCONFIGDIR']:values[k]=v
    resolved={k:str(Path(v).resolve()) for k,v in values.items()}
    assert all(v.startswith(str(DATA_ROOT)+'/') for v in resolved.values()),resolved
    return resolved
