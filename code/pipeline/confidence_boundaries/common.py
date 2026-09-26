import os,json,csv,hashlib,time,datetime,socket
from pathlib import Path
P=Path(__file__).resolve().parents[1]; ROOT=P.parent
OLD=ROOT/'zero_gold_controls'
BINARY=ROOT/'risk_calibration_binary'
P10=ROOT/'native_action_panel'; V2=ROOT/'answer_scoring_v2'
E1=ROOT/'receiver_state_features'; E0=ROOT/'historical_baselines'
PAIRS=['large','small']; DATASETS=['obqa','arc']; REFS=['T','C']
def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def read(p):return json.loads(Path(p).read_text())
def jl(p):
 with Path(p).open() as f:return [json.loads(s) for s in f if s.strip()]
def save(p,v):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);t=p.with_suffix(p.suffix+'.tmp');t.write_text(json.dumps(v,ensure_ascii=False,indent=2,allow_nan=False)+'\n');t.replace(p)
def writejl(p,rows):
 Path(p).parent.mkdir(parents=True,exist_ok=True)
 with Path(p).open('w') as f:
  for r in rows:f.write(json.dumps(r,ensure_ascii=False,allow_nan=False)+'\n')
def append(p,r):
 with Path(p).open('a') as f:f.write(json.dumps(r,ensure_ascii=False,allow_nan=False)+'\n');f.flush();os.fsync(f.fileno())
def csvread(p):return list(csv.DictReader(Path(p).open()))
def csvout(p,rows):
 rows=list(rows);Path(p).parent.mkdir(parents=True,exist_ok=True)
 with Path(p).open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(dict.fromkeys(k for r in rows for k in r)) if rows else ['empty']);w.writeheader();w.writerows(rows)
def freeze(name,paths,**kw):save(P/name,dict(utc=utc(),files={str(Path(p).relative_to(P)):sha(p) for p in paths},**kw))
def compute():
 assert os.environ.get('PBS_JOBID') and socket.gethostname().startswith('<cluster>-gpu')
 c=read(P/'execution_clearance.json');assert c['job_id']==os.environ['PBS_JOBID'] and c['strict_cgroup_match']
def stop():
 if (P/'STOP_BUDGET').exists() or time.time()>float(os.environ.get('RUN_DEADLINE_EPOCH','inf')):raise RuntimeError('BUDGET_STOP; no second submission')
def tv(t):return float('inf') if t=='Infinity' else float(t)
def route(u,p):return u<=tv(p['threshold']) if p['mode']=='selective' else p['mode']=='fixed_R'
def signature(r):return ' '.join(('\n'.join(['Question: '+r['question_stem'],'Choices:']+[a+': '+b for a,b in zip(r['choice_labels'],r['choice_text'])])).split())
def key(pair,ds,b):return f'{pair}_{ds}_{b}'
