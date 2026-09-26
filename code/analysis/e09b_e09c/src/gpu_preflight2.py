"""Startup guard for a 2-GPU E9B slot. Exit 0 = both usable, 3 = give up."""
import os, sys, json, time, datetime, socket
from pathlib import Path
S = Path(__file__).resolve().parents[1]
ATTEMPTS = int(os.environ.get('E9B_GPU_ATTEMPTS', '10')); SLEEP = float(os.environ.get('E9B_GPU_SLEEP', '15'))
import torch
errs = []
for k in range(ATTEMPTS):
    try:
        assert torch.cuda.is_available() and torch.cuda.device_count() == 2, f'device_count={torch.cuda.device_count()}'
        names = []
        for i in [0, 1]:
            torch.cuda.set_device(i)
            t = torch.zeros(8, device=f'cuda:{i}'); t.add_(1.0); torch.cuda.synchronize(i)
            names.append(torch.cuda.get_device_properties(i).name); del t
        torch.cuda.empty_cache()
        print(f'GPU_PREFLIGHT2_OK attempt={k+1} host={socket.gethostname()} '
              f'devices={os.environ.get("CUDA_VISIBLE_DEVICES")} {names}', flush=True)
        sys.exit(0)
    except Exception as exc:
        errs.append(f'attempt {k+1}: {exc!r}')
        print(f'GPU_PREFLIGHT2_RETRY {k+1}/{ATTEMPTS} {exc!r}', flush=True)
        if k + 1 < ATTEMPTS: time.sleep(SLEEP)
rec = dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), host=socket.gethostname(),
           job_id=os.environ.get('PBS_JOBID'), CUDA_VISIBLE_DEVICES=os.environ.get('CUDA_VISIBLE_DEVICES'),
           attempts=ATTEMPTS, errors=errs, action='E9B slot skipped; siblings continue')
p = S / 'logs' / f'GPU_UNAVAILABLE_E9B_{os.environ.get("PBS_JOBID","x").split(".")[0]}_r{os.environ.get("PALS_RANKID","x")}.json'
p.parent.mkdir(parents=True, exist_ok=True); p.write_text(json.dumps(rec, indent=2) + '\n')
print('GPU_PREFLIGHT2_GIVE_UP', p, flush=True); sys.exit(3)
