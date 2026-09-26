"""Non-frozen startup guard. Confirms this slot's two visible GPUs are actually usable before the
frozen runtime is constructed, retrying while a stuck device clears. Exit 0 = usable, 3 = give up.
Touches nothing scientific: it allocates an 8-element tensor per device and frees it."""
import os,sys,json,time,datetime,socket
from pathlib import Path
E8=Path(__file__).resolve().parents[1]
ATTEMPTS=int(os.environ.get('E8_GPU_ATTEMPTS','10'))
SLEEP=float(os.environ.get('E8_GPU_SLEEP','15'))
def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()
import torch
errs=[];ok=False
for k in range(ATTEMPTS):
    try:
        assert torch.cuda.is_available() and torch.cuda.device_count()==2,f'device_count={torch.cuda.device_count()}'
        names=[]
        for i in [0,1]:
            torch.cuda.set_device(i)
            t=torch.zeros(8,device=f'cuda:{i}');t.add_(1.0);torch.cuda.synchronize(i)
            names.append(torch.cuda.get_device_properties(i).name);del t
        torch.cuda.empty_cache()
        ok=True
    except Exception as exc:          # SystemExit/KeyboardInterrupt must not be swallowed
        errs.append(f'attempt {k+1}: {exc!r}')
        print(f'GPU_PREFLIGHT_RETRY {k+1}/{ATTEMPTS} {exc!r}',flush=True)
        if k+1<ATTEMPTS:time.sleep(SLEEP)
    if ok:
        print(f'GPU_PREFLIGHT_OK attempt={k+1} host={socket.gethostname()} '
              f'devices={os.environ.get("CUDA_VISIBLE_DEVICES")} {names}',flush=True)
        sys.exit(0)
rec=dict(utc=utc(),host=socket.gethostname(),job_id=os.environ.get('PBS_JOBID'),
    slot=os.environ.get('E8_SLOT'),pair=os.environ.get('E8_PAIR'),
    CUDA_VISIBLE_DEVICES=os.environ.get('CUDA_VISIBLE_DEVICES'),
    attempts=ATTEMPTS,sleep_seconds=SLEEP,errors=errs,
    action='slot skipped; its lanes stay unclaimed for a later job; sibling ranks continue')
p=E8/'evidence'/f'GPU_UNAVAILABLE_{os.environ.get("PBS_JOBID","x").split(".")[0]}_{os.environ.get("E8_SLOT","x")}.json'
p.parent.mkdir(parents=True,exist_ok=True)
p.write_text(json.dumps(rec,indent=2)+'\n')
print('GPU_PREFLIGHT_GIVE_UP',p,flush=True)
sys.exit(3)
