import os,json,csv,hashlib,time,datetime,socket
from pathlib import Path
P=Path(__file__).resolve().parents[1]
ROOT=P.parent
E=ROOT/'P2_E1_E2E_OBQA_20260913T174210Z'
D=ROOT/'P2_E1_DIRECTION_20260913T053456Z'
def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def read(p):return json.loads(Path(p).read_text())
def jl(p):
 with Path(p).open() as f:return [json.loads(s) for s in f if s.strip()]
def save(p,v):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);t=p.with_suffix(p.suffix+'.tmp')
 t.write_text(json.dumps(v,ensure_ascii=False,indent=2,allow_nan=False)+'\n');t.replace(p)
def writejl(p,rows):
 with Path(p).open('w') as f:
  for r in rows:f.write(json.dumps(r,ensure_ascii=False,allow_nan=False)+'\n')
def append(p,r):
 with Path(p).open('a') as f:f.write(json.dumps(r,ensure_ascii=False)+'\n');f.flush();os.fsync(f.fileno())
def csvout(p,rows):
 rows=list(rows)
 with Path(p).open('w') as f:
  w=csv.DictWriter(f,fieldnames=list(dict.fromkeys(k for r in rows for k in r)) if rows else ['empty']);w.writeheader();w.writerows(rows)
def freeze(name,paths,**kw):
 save(P/name,dict(utc=utc(),files={str(Path(p).relative_to(P)):sha(p) for p in paths},**kw))
def compute():
 assert os.environ.get('PBS_JOBID') and socket.gethostname().startswith('ClusterB-gpu')
 c=read(P/'execution_clearance.json');assert c['job_id']==os.environ['PBS_JOBID'] and c['strict_cgroup_match']
def stop():
 if (P/'STOP_BUDGET').exists() or time.time()>float(os.environ.get('P2_DEADLINE_EPOCH','inf')):raise RuntimeError('BUDGET_STOP')
OLD=ROOT/'P2_RISK_CALIBRATION_BINARY_20260914T043954Z'
