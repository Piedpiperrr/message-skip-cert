from common import *
import resource,signal,traceback
from native_runtime import Runtime
from risk import thresholds,calibrate,mask
from retry_audit import freeze_after_gpu_smoke

def interrupted(signum,frame):raise RuntimeError(f'FACILITY_SIGNAL_{signum}_NO_RETRY')
signal.signal(signal.SIGTERM,interrupted);signal.signal(signal.SIGINT,interrupted)
assert os.environ.get('PBS_JOBID')
freeze=read(P/'MEDIUM_PAIR_EXECUTION_PRECHECK_RETRY1.json');assert freeze['status']=='PASS'
EXEC_HASH=None  # Set after synthetic smoke; before any project inference.
assert read(P/'evidence/pbs/allocation.json')['job_id']==os.environ['PBS_JOBID']
assert not (P/'records/attempts.jsonl').exists(),'Only one execution; no retry/resume'
started=time.perf_counter();success=[];action_count=0;probe_count=0;attempts=0
data={};deployments={};qmap={};phase='GPU_LOADING'

def progress(status='RUNNING'):
    save(P/'PROGRESS.json',{'status':status,'phase':phase,'utc':utc(),'job_id':os.environ['PBS_JOBID'],
        'action_success_count':action_count,'probe_success_count':probe_count,'attempt_count':attempts,
        'successful_IDs_path':'records/successful_keys.json','wall_seconds':time.perf_counter()-started,
        'wall_remaining_seconds':max(0,float(os.environ['P2_MEDIUM_DEADLINE'])-time.time()),
        'MEDIUM_PAIR_OUTCOMES_OBSERVED':action_count+probe_count>0,'retry_count':0})
    save(P/'records/successful_keys.json',success)

def population(ds,split):
    global phase,attempts,action_count,probe_count
    phase=f'{ds}/{split}'
    for ordinal,ident in enumerate(ids(ds,split)):
        q=qmap[ds][ident]
        query_sha=hashlib.sha256(json.dumps(q,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
        d=data.setdefault((ds,ident),{})
        for action in ['R','T','C','P']:
            stop_check();key=f'{ds}|{split}|{ident}|{action}';assert action not in d
            attempts+=1
            append(P/'records/attempts.jsonl',{'event':'START','key':key,'attempt':attempts,'utc':utc(),'query_sha256':query_sha})
            result=rt.probe(q) if action=='P' else rt.action(q,action)
            record={'key':key,'pair':'medium','task':ds,'split':split,'id':ident,'ordinal':ordinal,
                'action':action,'query':q,'query_sha256':query_sha,'attempt':attempts,'utc':utc(),
                'job_id':os.environ['PBS_JOBID'],'scientific_protocol_sha256':PARENT_HASH,
                'execution_freeze_sha256':EXEC_HASH,**result}
            target=P/f'{"probes" if action=="P" else "actions"}/{ds}_{split}.jsonl'
            append(target,record)
            append(P/'records/attempts.jsonl',{'event':'SUCCESS','key':key,'attempt':attempts,'utc':utc()})
            success.append(key);d[action]=record
            if action=='P':probe_count+=1
            else:action_count+=1
            if action_count+probe_count==1:
                save(P/'OUTCOMES_OBSERVED.json',{'utc':utc(),'MEDIUM_PAIR_OUTCOMES_OBSERVED':True,'first_success_key':key,
                    'parent_freeze_unchanged':sha(PARENT/'MEDIUM_PAIR_PROTOCOL_FREEZE.json')==PARENT_HASH})
        if (ordinal+1)%20==0 or ordinal+1==len(ids(ds,split)):
            progress();print('PROGRESS',ds,split,ordinal+1,'actions',action_count,'probes',probe_count,flush=True)

try:
    progress();rt=Runtime();phase='SYNTHETIC_MECHANICAL_SMOKE'
    smoke=rt.mechanical_smoke();save(P/'GPU_MECHANICAL_PASS.json',smoke)
    assert smoke['status']=='PASS' and not smoke['MEDIUM_PAIR_OUTCOMES_OBSERVED']
    freeze_after_gpu_smoke(smoke)
    EXEC_HASH=sha(P/'MEDIUM_PAIR_EXECUTION_FREEZE_RETRY1.json')
    # First access to project queries occurs only after mechanical PASS.
    qmap={ds:query_map(ds) for ds in ['obqa','arc']}
    for ds in ['obqa','arc']:
        population(ds,'fit')
        reps=ids(ds,'fit',True)
        scores=[data[ds,i]['P']['ProbeMax'] for i in reps]
        cuts=thresholds(scores)
        fitfile=P/f'thresholds/{ds}.json'
        save(fitfile,{'task':ds,'fit_N_groups':len(reps),'fit_N_rows':len(ids(ds,'fit')),
            'fit_representative_IDs':reps,'thresholds':cuts,'q_grid':[j/20 for j in range(1,21)],
            'fit_scores':scores,'calibration_outcomes_read':False,'utc':utc()})
        save(P/f'thresholds/{ds}_FREEZE.json',{'utc':utc(),'sha256':sha(fitfile),'calibration_project_inference_started':False})
        population(ds,'cal')
        reps=ids(ds,'cal',True);scores=[data[ds,i]['P']['ProbeMax'] for i in reps]
        for ref in ['T','C']:
            d=[int(data[ds,i]['R']['answer']!=data[ds,i][ref]['answer']) for i in reps]
            ledger,dep=calibrate(scores,d,cuts)
            for r in ledger:r.update(task=ds,reference=ref,pair='medium')
            csvout(P/f'calibration/{ds}_{ref}.csv',ledger)
            write_rows(P/f'calibration/{ds}_{ref}_observations.jsonl',[{'id':i,'score':u,'disagreement':x} for i,u,x in zip(reps,scores,d)])
            dep.update(task=ds,reference=ref,utc=utc(),fit_threshold_sha256=sha(fitfile),dev_project_inference_started=False)
            depfile=P/f'deployments/{ds}_{ref}.json';save(depfile,dep)
            save(P/f'deployments/{ds}_{ref}_FREEZE.json',{'utc':utc(),'deployment_sha256':sha(depfile),
                'calibration_ledger_sha256':sha(P/f'calibration/{ds}_{ref}.csv'),'development_outcomes_observed':False})
            deployments[ds+'_'+ref]=dep
        progress()
    save(P/'ALL_DEPLOYMENTS_FREEZE.json',{'utc':utc(),'deployments':deployments,
        'hashes':{str(f.relative_to(P)):sha(f) for f in sorted((P/'deployments').glob('*'))},
        'development_project_inference_started':False,'gold_read':False})
    for ds in ['obqa','arc']:population(ds,'dev')
    routefiles=[]
    for ds in ['obqa','arc']:
        dev_ids=ids(ds,'dev');scores=[data[ds,i]['P']['ProbeMax'] for i in dev_ids]
        for ref in ['T','C']:
            dep=deployments[ds+'_'+ref];routed=mask(scores,dep['q'],dep['threshold'])
            dest=P/f'development/{ds}_{ref}_routes.jsonl'
            write_rows(dest,[{'id':i,'task':ds,'reference':ref,'score':u,'selected':'R' if m else ref,
                'q':dep['q'],'threshold':dep['threshold']} for i,u,m in zip(dev_ids,scores,routed)])
            routefiles.append(dest)
    save(P/'ALL_ROUTES_FREEZE.json',{'utc':utc(),'hashes':{str(f.relative_to(P)):sha(f) for f in routefiles},'gold_read':False})
    assert action_count==16878 and probe_count==5626 and attempts==22504
    assert len(success)==len(set(success))==22504
    phase='FORMAL_INFERENCE_COMPLETE';progress('INFERENCE_COMPLETE')
    save(P/'INFERENCE_COMPLETE.json',{'utc':utc(),'job_id':os.environ['PBS_JOBID'],'actions':action_count,
        'probes':probe_count,'attempts':attempts,'retries':0,'gold_read':False,
        'wall_seconds':time.perf_counter()-started,'CPU_seconds':resource.getrusage(resource.RUSAGE_SELF).ru_utime+resource.getrusage(resource.RUSAGE_SELF).ru_stime,
        'files':{str(f.relative_to(P)):sha(f) for d in ['actions','probes'] for f in sorted((P/d).glob('*.jsonl'))}})
except BaseException as e:
    status='BLOCKED_MEDIUM_STAGE1' if attempts==0 else 'PARTIAL_MEDIUM_STAGE1'
    progress(status)
    save(P/'EXECUTION_FAILURE.json',{'status':status,'utc':utc(),'phase':phase,'error':repr(e),
        'traceback':traceback.format_exc(),'successful_actions':action_count,'successful_probes':probe_count,
        'attempts':attempts,'successful_IDs_file':'records/successful_keys.json','retry_count':0,'resubmit_allowed':False})
    raise
