"""Startup guard: confirm this slot's single visible GPU is usable before the runtime is built.
Exit 0 = usable, 3 = give up. Allocates and frees an 8-element tensor; nothing scientific."""
import os, sys, json, time, datetime, socket
from pathlib import Path
S = Path(__file__).resolve().parents[1]
ATTEMPTS = int(os.environ.get('E9_GPU_ATTEMPTS', '10')); SLEEP = float(os.environ.get('E9_GPU_SLEEP', '15'))
import torch
errs = []
for k in range(ATTEMPTS):
    try:
        assert torch.cuda.is_available() and torch.cuda.device_count() == 1, f'device_count={torch.cuda.device_count()}'
        torch.cuda.set_device(0)
        t = torch.zeros(8, device='cuda:0'); t.add_(1.0); torch.cuda.synchronize(0)
        name = torch.cuda.get_device_properties(0).name; del t; torch.cuda.empty_cache()
        print(f'GPU_PREFLIGHT_OK attempt={k+1} host={socket.gethostname()} '
              f'devices={os.environ.get("CUDA_VISIBLE_DEVICES")} {name}', flush=True)
        sys.exit(0)
    except Exception as exc:
        errs.append(f'attempt {k+1}: {exc!r}')
        print(f'GPU_PREFLIGHT_RETRY {k+1}/{ATTEMPTS} {exc!r}', flush=True)
        if k + 1 < ATTEMPTS: time.sleep(SLEEP)
rec = dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), host=socket.gethostname(),
           job_id=os.environ.get('PBS_JOBID'), rank=os.environ.get('E9_RANK'),
           CUDA_VISIBLE_DEVICES=os.environ.get('CUDA_VISIBLE_DEVICES'), attempts=ATTEMPTS, errors=errs,
           action='lane skipped; its rows stay unwritten for a later job; sibling ranks continue')
p = S / 'logs' / f'GPU_UNAVAILABLE_{os.environ.get("PBS_JOBID","x").split(".")[0]}_r{os.environ.get("E9_RANK","x")}.json'
p.parent.mkdir(parents=True, exist_ok=True); p.write_text(json.dumps(rec, indent=2) + '\n')
print('GPU_PREFLIGHT_GIVE_UP', p, flush=True); sys.exit(3)
