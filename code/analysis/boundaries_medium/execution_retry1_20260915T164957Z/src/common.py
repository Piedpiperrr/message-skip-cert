import csv, datetime, hashlib, json, os, sys, time
from pathlib import Path
P = Path(__file__).resolve().parents[1]
PARENT = P.parent
ROOT = PARENT.parent
DATA_ROOT = ROOT.parent.parent
PYTHON = DATA_ROOT / 'software/envs/c2c_official/bin/python'
NATIVE = ROOT / 'P2_10_20260911T122423Z'
PARENT_HASH = 'c4b85ca697030ca115020fdb959143c8c4901135a5b876cf716bf4b6a4c94bf8'
def utc(): return datetime.datetime.now(datetime.timezone.utc).isoformat()
def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
    return h.hexdigest()
def read(path): return json.loads(Path(path).read_text())
def rows(path):
    with Path(path).open() as f: return [json.loads(s) for s in f if s.strip()]
def save(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_suffix(path.suffix+'.tmp')
    temp.write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n');temp.replace(path)
def append(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('a') as f:
        f.write(json.dumps(value,ensure_ascii=False,allow_nan=False)+'\n');f.flush();os.fsync(f.fileno())
def write_rows(path,values):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('w') as f:
        for v in values:f.write(json.dumps(v,ensure_ascii=False,allow_nan=False)+'\n')
def csvout(path,values):
    values=list(values);path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(dict.fromkeys(k for r in values for k in r)));w.writeheader();w.writerows(values)
def load_module(path,name):
    import importlib.util
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def validate_parent():
    assert sha(PARENT/'MEDIUM_PAIR_PROTOCOL_FREEZE.json')==PARENT_HASH
    f=read(PARENT/'MEDIUM_PAIR_PROTOCOL_FREEZE.json')
    for name,h in f['frozen_files'].items(): assert sha(PARENT/name)==h,name
    assert sha(PARENT/'MODEL_SOURCE_INDEX.json')==f['model_source_index_sha256']
    return f
def ids(ds,split,representatives=False):
    return read(PARENT/f'splits/{ds}_{split}_{"representatives" if representatives else "ids"}.json')
def query_map(ds):
    return {r['id']:r for s in ['train','dev'] for r in rows(PARENT/f'inputs/{ds}_{s}_queries.jsonl')}
def stop_check():
    if time.time()>float(os.environ.get('P2_MEDIUM_DEADLINE','inf')):raise RuntimeError('WALLTIME_BUDGET_STOP_NO_RESUBMISSION')
    if (P/'STOP').exists():raise RuntimeError('EXPLICIT_STOP')
def paths():
    values={'helper':P/'assets/helper','receiver':P/'assets/receiver','fuser':P/'assets/fuser',
      'dataset':PARENT/'inputs','output':P,'checkpoint':P/'assets','log':os.environ.get('P2_RUN',str(P/'evidence')),
      'PBS_logs':DATA_ROOT/'logs/pbs','temporary':os.environ.get('TMPDIR',str(DATA_ROOT/'tmp/p2_medium_resume')),'python':PYTHON}
    for k,v in os.environ.items():
        if 'CACHE' in k or k in ['HF_HOME','TORCH_HOME','MPLCONFIGDIR']:values[k]=v
    values={k:str(Path(v).resolve()) for k,v in values.items()}
    assert all(v.startswith(str(DATA_ROOT)+'/') for v in values.values()),values
    return values
