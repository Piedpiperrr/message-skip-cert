"""Establish clearance from this job's real PBS allocation; no numerical imports."""
import os, sys, json, socket, pwd, subprocess, time, hashlib
from pathlib import Path
O = Path(__file__).resolve().parent
def save(p,x): p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
jobid=os.environ['PBS_JOBID'];host=socket.gethostname();user=pwd.getpwuid(os.getuid()).pw_name
assert host.startswith('ClusterB-gpu') and 'login' not in host
record=json.loads(subprocess.check_output(['job-status','-f','-F','json',jobid],text=True))
assert list(record['Jobs'])==[jobid]
job=record['Jobs'][jobid]
assert job['Job_Owner'].split('@')[0]==user=='user'
assert job['job_state']=='R' and job['Account_Name']=='project' and job['queue']=='gpu-queue'
r=job['Resource_List'];assert int(r['nodect'])==1 and int(r['ngpus'])==1 and r['fsreq']=='home:sharedfs'
nodefile=Path(os.environ['PBS_NODEFILE']);nodes=nodefile.read_text().split();short=lambda h:h.split('.')[0]
assert short(host) in {short(h) for h in nodes}
assert any(short(h.split('/')[0])==short(host) for h in job['exec_host'].split('+'))
cgroup=Path('/proc/self/cgroup').read_text();sid=os.getsid(0)
session_match=int(job.get('session_id',-1))==sid
cgroup_paths=[line.split(':',2)[2].split('/') for line in cgroup.splitlines()]
cgroup_match=any('jobs' in parts and jobid.split('.')[0] in parts for parts in cgroup_paths)
assert session_match or cgroup_match, ('process membership unverified',sid,job.get('session_id'),cgroup)
a=json.loads((O/'RESOURCE_ADDENDUM.json').read_text());assert a['stage']==O.name and a['compute']['CPU_only']
paths={'output':str(O),'models':str(O/'baseline'),'checkpoint':str(O/'oof'),'datasets':str(O.parent/'P2_10_20260911T122423Z/data'),'labels':str(O.parent/'P2_SCORING_V2_20260912T191445Z/labels'),'python':sys.executable,'run':os.environ['P2_RUN'],'temporary':os.environ['TMPDIR'],'pbs_logs':os.environ['DATA_ROOT']+'/logs/pbs'}
for k,v in os.environ.items():
 if k.endswith('_CACHE') or k.endswith('_CACHE_HOME') or k in ['HF_HOME','HF_HUB_CACHE','HF_DATASETS_CACHE','HF_ASSETS_CACHE','TORCH_HOME','TORCH_EXTENSIONS_DIR','TRITON_CACHE_DIR','NUMBA_CACHE_DIR','CUDA_CACHE_PATH','APPTAINER_CACHEDIR','PIP_CACHE_DIR','UV_CACHE_DIR']:paths[k]=v
for k,v in paths.items():assert str(Path(v).resolve()).startswith(os.environ['DATA_ROOT']+'/'),(k,v)
assert os.access(sys.executable,os.R_OK|os.X_OK) and os.access(Path(sys.executable).parent,os.R_OK|os.W_OK)
probe=O/'evidence/pbs'/('write_probe_'+jobid);probe.write_text('allocation write check\n');assert probe.read_text()=='allocation write check\n';probe.unlink()
ep=O/'evidence/pbs'/('allocation_'+jobid+'.json')
save(ep,{'job_id':jobid,'observed_epoch':time.time(),'user':user,'uid':os.getuid(),'hostname':host,'pid':os.getpid(),'ppid':os.getppid(),'process_session_id':sid,'scheduler_session_match':session_match,'cgroup_job_match':cgroup_match,'cgroup':cgroup,'nodefile':str(nodefile),'nodefile_contents':nodes,'scheduler':record,'resolved_paths':paths,'sharedfs_read_write_verified':True,'python_existing_environment_verified':True,'GPU_computation':0,'GPU_quota_allocated':1,'resource_addendum_sha256':sha(O/'RESOURCE_ADDENDUM.json')})
save(O/'execution_clearance.json',{'allowed':True,'host':host,'stage':O.name,'job_id':jobid,'evidence':[str(ep),str(O/'RESOURCE_ADDENDUM.json')],'allocation_evidence_sha256':sha(ep),'basis':'Verified real PBS owner, scheduler host, nodefile, process membership and sharedfs/environment access'})
print(json.dumps({'EXECUTION_CLEARANCE':True,'jobid':jobid,'host':host,'paths':paths},ensure_ascii=False),flush=True)
os.execv(sys.executable,[sys.executable,'-u',str(O/'run_bounded.py')])
