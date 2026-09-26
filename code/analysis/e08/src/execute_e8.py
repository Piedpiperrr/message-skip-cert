"""E8 formal collection for one pair. Same request protocol and record schema as the frozen
large-pair MMLU-Pro Stage1 src/execute.py. Difference forced by the ClusterA debug queue
(<=00:50:00): work is split into frozen lanes that a slot claims with an exclusive lock and
may resume across jobs. Every (pair, split, id, action) key is written at most once; a key is
never recomputed after it has a record; runtime errors are fatal and are not retried."""
from common_e8 import *
import signal,traceback,resource,fcntl,collections

ACTIONS=['R','T','C','P']
LANES=read(P/'splits/E8_LANES.json')
assert PAIR in ('small','medium'),PAIR
JOB=os.environ.get('PBS_JOBID','');assert JOB
ROOTDIR=P/'shards'/PAIR
MARGIN=float(os.environ.get('E8_STOP_MARGIN','60'))

def lane_dir(k):return ROOTDIR/f'lane_{k:02d}'

def lane_state(k):
    """Keys already recorded in this lane (tolerating a trailing truncated line from a hard kill)."""
    d=lane_dir(k);keys=set();truncated=[]
    for sub in ['actions','probes']:
        for f in sorted((d/sub).glob('*.jsonl')) if (d/sub).is_dir() else []:
            good=[]
            with f.open() as fh:lines=fh.readlines()
            for i,line in enumerate(lines):
                if not line.strip():continue
                try:good.append(json.loads(line))
                except json.JSONDecodeError:
                    assert i==len(lines)-1,('mid-file corruption',str(f),i)
                    truncated.append(str(f));break
            if truncated and truncated[-1]==str(f):
                with f.open('w') as fh:
                    for r in good:fh.write(json.dumps(r,ensure_ascii=False,allow_nan=False)+'\n')
            keys.update(r['key'] for r in good)
    return keys,truncated

def claim(k):
    d=lane_dir(k);d.mkdir(parents=True,exist_ok=True)
    fh=(d/'lane.lock').open('a')
    try:fcntl.flock(fh,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except OSError:fh.close();return None
    return fh

def run_lane(rt,k,work,deadline,counters,per_row_estimate):
    d=lane_dir(k);keys,truncated=lane_state(k)
    done_rows=sum(1 for i,(split,ident) in enumerate(work) if all(f'{PAIR}|mmlu_pro|{split}|{ident}|{a}' in keys for a in ACTIONS))
    qmap=rt.qmap;started=time.perf_counter();rows_here=0;stopped=None
    append(d/'records/attempts.jsonl',dict(event='LANE_OPEN',utc=utc(),job_id=JOB,slot=SLOT,
        lane=k,recorded_keys=len(keys),truncated_tail_repaired=truncated))
    for ordinal,(split,ident) in enumerate(work):
        rowkeys=[f'{PAIR}|mmlu_pro|{split}|{ident}|{a}' for a in ACTIONS]
        if all(x in keys for x in rowkeys):continue
        need=per_row_estimate[0]*1.5+MARGIN
        if time.time()+need>deadline:stopped='DEADLINE';break
        if (P/'STOP').exists():stopped='EXPLICIT_STOP';break
        q=qmap[ident];qh=queryhash(q);t0=time.perf_counter()
        for a,key in zip(ACTIONS,rowkeys):
            if key in keys:continue
            append(d/'records/attempts.jsonl',dict(event='START',utc=utc(),key=key,job_id=JOB))
            result=rt.probe(q) if a=='P' else rt.action(q,a)
            record=dict(key=key,pair=PAIR,task='mmlu_pro',split=split,id=ident,ordinal=ordinal,lane=k,action=a,
                query=q,query_sha256=qh,utc=utc(),job_id=JOB,slot=SLOT,
                protocol_freeze_sha256=os.environ['E8_FREEZE_SHA256'],**result)
            append(d/f'{"probes" if a=="P" else "actions"}/{split}.jsonl',record)
            append(d/'records/attempts.jsonl',dict(event='SUCCESS',utc=utc(),key=key))
            keys.add(key);counters[a]+=1
        dt=time.perf_counter()-t0;rows_here+=1;done_rows+=1
        per_row_estimate[0]=0.8*per_row_estimate[0]+0.2*dt if rows_here>2 else max(per_row_estimate[0],dt)
        if rows_here%25==0:
            save(d/'PROGRESS.json',dict(utc=utc(),pair=PAIR,lane=k,job_id=JOB,slot=SLOT,rows_total=len(work),
                rows_complete=done_rows,rows_this_job=rows_here,recorded_keys=len(keys),
                seconds_per_row_recent=round(per_row_estimate[0],3),status='RUNNING'))
            print('PROGRESS',PAIR,'lane',k,done_rows,'/',len(work),f'{per_row_estimate[0]:.2f}s/row',flush=True)
    complete=done_rows==len(work)
    save(d/'PROGRESS.json',dict(utc=utc(),pair=PAIR,lane=k,job_id=JOB,slot=SLOT,rows_total=len(work),
        rows_complete=done_rows,rows_this_job=rows_here,recorded_keys=len(keys),
        seconds_per_row_recent=round(per_row_estimate[0],3),
        status='LANE_COMPLETE' if complete else 'PARTIAL',stopped_because=stopped))
    if complete:
        save(d/'LANE_COMPLETE.json',dict(utc=utc(),pair=PAIR,lane=k,rows=len(work),keys=len(keys),job_id=JOB,
            files={str(p.relative_to(d)):sha(p) for sub in ['actions','probes'] for p in sorted((d/sub).glob('*.jsonl'))}))
    append(d/'records/attempts.jsonl',dict(event='LANE_CLOSE',utc=utc(),job_id=JOB,slot=SLOT,lane=k,
        rows_complete=done_rows,complete=complete,stopped_because=stopped))
    return complete,stopped,rows_here

def main():
    def interrupted(signum,frame):raise RuntimeError(f'FACILITY_SIGNAL_{signum}')
    signal.signal(signal.SIGTERM,interrupted);signal.signal(signal.SIGINT,interrupted)
    validate_freeze()
    deadline=float(os.environ['E8_DEADLINE_EPOCH'])
    from native_runtime_e8 import Runtime
    rt=Runtime(PAIR)
    smokepath=P/'evidence'/f'GPU_MECHANICAL_{PAIR}_{JOB.split(".")[0]}_{SLOT}.json'
    sm=rt.mechanical_smoke();save(smokepath,sm);assert sm['status']=='PASS'
    rt.qmap=project_queries()
    counters=collections.Counter();per_row=[3.0];worked=[]
    lanes=[l for l in LANES['lanes'] if l['pair']==PAIR]
    for l in lanes:
        if (lane_dir(l['lane'])/'LANE_COMPLETE.json').exists():continue
        if time.time()+per_row[0]*1.5+MARGIN>deadline:break
        fh=claim(l['lane'])
        if fh is None:continue
        try:
            work=[(s,i) for s,i in (tuple(x) for x in l['work'])]
            complete,stopped,n=run_lane(rt,l['lane'],work,deadline,counters,per_row)
            worked.append(dict(lane=l['lane'],rows_this_job=n,complete=complete,stopped=stopped))
        finally:
            fcntl.flock(fh,fcntl.LOCK_UN);fh.close()
        if stopped:break
    save(P/'evidence'/f'SLOT_{JOB.split(".")[0]}_{SLOT}_{PAIR}.json',dict(utc=utc(),pair=PAIR,job_id=JOB,slot=SLOT,
        host=os.uname().nodename,CUDA_VISIBLE_DEVICES=os.environ.get('CUDA_VISIBLE_DEVICES'),
        lanes_worked=worked,counts=dict(counters),seconds_per_row_final=round(per_row[0],3),
        mechanical_smoke=str(smokepath),load_seconds=rt.load_times,
        CPU_seconds=resource.getrusage(resource.RUSAGE_SELF).ru_utime+resource.getrusage(resource.RUSAGE_SELF).ru_stime,
        gold_read=False,scientific_analysis_performed=False))
    print('SLOT_END',PAIR,SLOT,dict(counters),flush=True)

if __name__=='__main__':
    try:main()
    except BaseException as exc:
        save(P/'evidence'/f'SLOT_FAILURE_{os.environ.get("PBS_JOBID","x").split(".")[0]}_{SLOT}_{PAIR}.json',
             dict(utc=utc(),pair=PAIR,slot=SLOT,error=repr(exc),traceback=traceback.format_exc()))
        raise
