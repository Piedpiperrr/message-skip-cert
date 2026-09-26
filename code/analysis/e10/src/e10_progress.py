"""Row counts per split/action after a job, so completeness is visible without reading outputs."""
import json, glob
from collections import Counter
from pathlib import Path
STAGE = Path(__file__).resolve().parents[1]
c = Counter(); ntok = Counter(); inv = Counter()
for f in sorted(glob.glob(str(STAGE / 'records/main_rank*.jsonl'))):
    for line in open(f):
        line = line.strip()
        if not line: continue
        try: r = json.loads(line)
        except Exception: continue
        c[(r['split'], r['action'])] += 1
        ntok[(r['split'], r['action'])] += r['n_gen_tokens']
        inv[(r['split'], r['action'])] += bool(r['invalid'])
want = {('fit', 'R'): 400, ('cal', 'R'): 1000, ('cal', 'T'): 1000, ('dev', 'R'): 400, ('dev', 'T'): 400}
print('E10 PROGRESS')
for k, w in want.items():
    n = c[k]
    print('  %-10s %5d / %5d  invalid=%-4d mean_gen_tok=%.0f' %
          ('%s %s' % k, n, w, inv[k], (ntok[k] / n) if n else 0))
print('  COMPLETE =', all(c[k] == w for k, w in want.items()))
