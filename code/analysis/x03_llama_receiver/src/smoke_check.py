"""X3 smoke stop rule (Step 3), outputs only (gold never read): STOP_INVALID if INVALID > 2/16 on R or on Text; STOP_BUG on any runtime
error or NaN/inf ProbeMax; else PASS. Also BOS counts per path and warm latencies (for shard sizing). -> results/smoke/SMOKE_CHECK.json
usage: smoke_check.py <smoke outputs jsonl>"""
import sys
sys.dont_write_bytecode = True
import math, collections
from xfam_common import *
f = pathlib.Path(sys.argv[1]); rows = jl(f)
err = [r['id'] for r in rows if r.get('runtime_error')]
ok = [r for r in rows if not r.get('runtime_error')]
invR = sum(r['R']['parsed'] == 'INVALID' for r in ok) + len(err); invT = sum(r['T']['parsed'] == 'INVALID' for r in ok) + len(err)
nan = [r['id'] for r in ok if not math.isfinite(r['P']['ProbeMax'])]
bos = {a: dict(collections.Counter(r[a]['bos_count'] for r in ok)) for a in 'RTP'}
warm = [r for r in ok if not r['cold_first_after_load']]
lat = {a: sum(r[a]['latency_ms'] for r in warm) / max(len(warm), 1) for a in 'RTP'}
verdict = 'STOP_BUG' if err or nan or len(rows) != 16 else ('STOP_INVALID' if invR > 2 or invT > 2 else 'PASS')
out = dict(utc=utc(), file=str(f), sha256=sha(f), n=len(rows), runtime_errors=err, INVALID_R=invR, INVALID_T=invT, nan_ProbeMax=nan, bos_counts=bos,
           warm_mean_latency_ms=lat, warm_sec_per_row=sum(lat.values()) / 1000, n_warm=len(warm),
           R_new_tokens=[len(r['R']['generated_token_ids']) for r in ok], T_new_tokens=[len(r['T']['generated_token_ids']) for r in ok], verdict=verdict)
save(f.parent / 'SMOKE_CHECK.json', out); print('SMOKE', verdict, 'INVALID R', invR, 'T', invT, 'errors', len(err), 'nan', len(nan), 'bos', bos, 'sec/row', round(out['warm_sec_per_row'], 3), flush=True)
