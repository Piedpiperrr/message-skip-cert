"""Run the frozen src/analyze_r1.py on the ClusterA outputs (DEVIATIONS.md D6). The frozen file is not modified.

Two exact-string substitutions are applied in memory, then the frozen code is executed as-is:
 1. E4 variant files: the ClusterA run named them by variant list (<pair>_<ds>__V0-V1.jsonl, __V2.jsonl, __V0-V1-V2.jsonl;
    D3) instead of __V1-V2.jsonl + __V0.jsonl. Every record carries its 'variant' and 'pos', so all __V*.jsonl files of a
    population are loaded into the same V[variant][pos] structure (duplicates asserted absent).
 2. The frozen summary is written to results/SUMMARY_analyze_r1.md (results/SUMMARY.md is the combined R1 summary).
Everything else (hash-before-gold order, parser, metrics, CSV names) is the frozen code.
"""
import sys, hashlib, pathlib
sys.dont_write_bytecode = True
SRC = pathlib.Path(__file__).resolve().parents[1]
FROZEN = SRC / 'analyze_r1.py'
assert hashlib.sha256(FROZEN.read_bytes()).hexdigest() == '29028eab586b53277a1e7b76be93a7a7083235be9494c514ac4aa067909416b6'
code = FROZEN.read_text()
SUBS = [
    ("""        vpath = RES / f'e4/{pair}_{ds}__V1-V2.jsonl'
        V = collections.defaultdict(dict)
        for x in (jl(vpath) if vpath.exists() else []):
            V[x['variant']][x['pos']] = x
        v0path = RES / f'e4/{pair}_{ds}__V0.jsonl'
        for x in (jl(v0path) if v0path.exists() else []):
            V['V0'][x['pos']] = x
""",
     """        V = collections.defaultdict(dict)  # ClusterA adapter (D6): variant files are named by variant list (D3)
        for vpath in sorted(RES.glob(f'e4/{pair}_{ds}__V*.jsonl')):
            for x in jl(vpath):
                assert x['pos'] not in V[x['variant']], (str(vpath), x['variant'], x['pos'])
                V[x['variant']][x['pos']] = x
"""),
    ("(RES / 'SUMMARY.md').write_text(''.join(S))", "(RES / 'SUMMARY_analyze_r1.md').write_text(''.join(S))"),
]
for old, new in SUBS:
    assert code.count(old) == 1, old[:60]
    code = code.replace(old, new)
if __name__ == '__main__':
    sys.path.insert(0, str(SRC))
    exec(compile(code, str(FROZEN) + ' [ClusterA adapter D6]', 'exec'), {'__name__': '__main__', '__file__': str(FROZEN)})
