from common import *
import sys,subprocess,pwd
jid=os.environ['PBS_JOBID'];host=socket.gethostname();user=pwd.getpwuid(os.getuid()).pw_name
assert host.startswith('x3') and user=='user'  # E3 ClusterA: compute node (original: ClusterB-gpu)
rec=json.loads(subprocess.check_output(['job-status','-f','-F','json',jid],text=True));assert list(rec['Jobs'])==[jid]
j=rec['Jobs'][jid];r=j['Resource_List'];assert j['Job_Owner'].split('@')[0]==user and j['job_state']=='R' and j['Account_Name']=='project' and j['queue']=='debug-2'
assert int(r['nodect'])==2 and int(r.get('ngpus',0))==0 and r['fsreq']=='home:sharedfs' and r['walltime']=='00:55:00'  # E3 ClusterA: debug, 2 exclusive nodes of 4 A100 (GPUs are not a PBS resource); original: gpu-queue, 1 node, ngpus=2, 00:30:00
short=lambda x:x.split('.')[0];nodes=Path(os.environ['PBS_NODEFILE']).read_text().split();assert short(host) in {short(x) for x in nodes} and len({short(x) for x in nodes})==2  # E3 ClusterA: this node is one of the job's 2 nodes (original: the only node)
cgroup=Path('/proc/self/cgroup').read_text();match=any('jobs' in x and jid.split('.')[0] in x for x in [l.split(':',2)[2].split('/') for l in cgroup.splitlines()]);ClusterA_match=any(jid in x or jid.split('.')[0] in x or any(c.startswith(jid.split('.')[0]+'.') for c in x) for x in [l.split(':',2)[2].split('/') for l in cgroup.splitlines()])  # E3 ClusterA: cgroup layout unverified on ClusterA; both matches recorded, not fatal (as in the medium and MMLU-Pro guards)
CFG=read(P/'frozen_config.json');paths={'helper':CFG['native']['models']['helper']['path'],'receiver':CFG['native']['models']['receiver']['path'],'fuser':CFG['native']['fuser']['path'],'dataset':str(P/'inputs'),'output':str(P),'checkpoint':str(P/'protocol'),'log':os.environ['P2_RUN'],'PBS_logs':os.environ['DATA_ROOT']+'/logs/pbs','temporary':os.environ['TMPDIR'],'python':sys.executable}
for k,v in os.environ.items():
 if 'CACHE' in k or k in ['HF_HOME','TORCH_HOME','MPLCONFIGDIR']:paths[k]=v
for k,v in paths.items():assert str(Path(v).resolve()).startswith(os.environ['DATA_ROOT']+'/'),(k,v)
print('RESOLVED_PATHS',json.dumps(paths),flush=True)
for frozen in ['PROTOCOL_FREEZE.json','IMPLEMENTATION_FREEZE.json']:
 for f,h in read(P/frozen)['files'].items():assert sha(P/f)==h,(f,h)
for src in read(P/'SOURCE_INDEX.json'):
 assert Path(src['path']).stat().st_size==src['bytes'],src['path']
 if src['sha256']:assert sha(src['path'])==src['sha256'],src['path']
j.pop('Variable_List',None);save(P/'evidence/pbs/allocation.json',{'job_id':jid,'host':host,'strict_cgroup_match':match,'ClusterA_cgroup_match':ClusterA_match,'cgroup':cgroup,'scheduler':rec,'paths':paths,'CUDA_VISIBLE_DEVICES':os.environ.get('CUDA_VISIBLE_DEVICES'),'utc':utc()})
save(P/'execution_clearance.json',{'job_id':jid,'host':host,'strict_cgroup_match':match,'ClusterA_cgroup_match':ClusterA_match,'cgroup_match_fatal':False,'GPU_count':2})
os.execv(sys.executable,[sys.executable,'-u',str(P/'src/supervise.py')])
