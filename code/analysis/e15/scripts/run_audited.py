"""Run an E15 script under a sys.addaudithook('open') recorder and list every project file it opened (read or write)."""
import sys, os, runpy
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
STAGE = Path(__file__).resolve().parents[1]
seen = {}


def hook(ev, args):
    if ev == 'open' and args and isinstance(args[0], (str, bytes, os.PathLike)):
        p = os.path.abspath(os.fsdecode(args[0]))
        if p.startswith(str(ROOT)) and not p.endswith('.py'):
            mode = args[1] if len(args) > 1 and isinstance(args[1], str) else 'r'
            seen.setdefault(p, set()).add('w' if any(c in mode for c in 'wax+') else 'r')


script = sys.argv[1]
sys.argv = sys.argv[1:]
sys.addaudithook(hook)
try:
    runpy.run_path(script, run_name='__main__')
finally:
    out = STAGE / 'logs' / f'files_opened_{Path(script).stem}.txt'
    with open(out, 'w') as f:
        for p in sorted(seen):
            f.write(f"{''.join(sorted(seen[p]))}\t{p}\n")
