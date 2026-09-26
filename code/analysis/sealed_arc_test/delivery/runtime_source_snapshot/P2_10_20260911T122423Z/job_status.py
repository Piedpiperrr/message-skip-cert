import json
import subprocess
import socket
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
server = next((line.split('=', 1)[1].strip() for line in Path('/etc/pbs.conf').read_text().splitlines()
               if line.startswith('PBS_SERVER=')), socket.gethostname())
local_cluster = server.split('-')[0]
fields = ['Job_Name','job_state','queue','ctime','qtime','stime','mtime','etime','obittime',
          'Exit_status','comment','estimated','exec_host','exec_vnode','Resource_List','resources_used',
          'Output_Path','Error_Path','Submit_arguments','run_count']
records = json.loads((ROOT/'evidence/submissions.json').read_text())
jobs = []
for r in records:
    path = ROOT/f"evidence/job_{r['job_id'].split('.')[0]}.json"
    cluster = r['job_id'].split('.')[1].split('-')[0]
    if local_cluster != cluster:
        v = json.loads(path.read_text())
        assert v['job_state'] == 'F', '外部集群作业尚无最终退出证据，不能使用旧排队快照。'
        v['status_source'] = 'preserved final PBS evidence from originating cluster'
    else:
        proc = subprocess.run(['job-status','-xf','-F','json',r['job_id']],stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True,check=True,timeout=15)
        v = json.loads(proc.stdout)['Jobs'][r['job_id']]
        v = {k:v[k] for k in fields if k in v}
        v['job_id'] = r['job_id']
        v['queried_utc'] = datetime.now(timezone.utc).isoformat()
        path.write_text(json.dumps(v,indent=2)+'\n')
    jobs.append(v)
    print(json.dumps({k:v.get(k) for k in ['job_id','job_state','queue','stime','comment','estimated','exec_host','resources_used','Exit_status']},ensure_ascii=False),flush=True)
(ROOT/'evidence/jobs.json').write_text(json.dumps(jobs,indent=2)+'\n')
