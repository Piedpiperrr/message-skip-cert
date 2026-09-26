"""E20F G1 (login node): verify the pilot's PREREG_E20P.md, SELECTION_E20P.json, PROMPTS_E20.md and every file in its CODE_FREEZE.json
against the hashes stored in the pilot directory. Writes notes/G1_VERIFY.json; exit 1 on any difference."""
import sys, json, hashlib, pathlib, datetime
S = pathlib.Path(__file__).resolve().parents[1]; P = S.parent / 'P2_R8_E20P_20260921T224653Z'
sha = lambda p: hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
out = dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), pilot_dir=str(P), checks=[])
def chk(name, stored, now): out['checks'].append(dict(item=name, stored=stored, now=now, ok=stored == now))
for f in ['PREREG_E20P', 'SELECTION_E20P']:
    h, n = (P / f'{f}.sha256').read_text().split('\n')[0].split('  '); assert n == f'{f}.md' or n == f'{f}.json'
    chk(n, h, sha(P / n))
chk('PREREG_E20P.md (task-stated)', 'c02cf958a7c972c6c976da4100d02293fcd81ba91b5f614d02b3cf0a1ab7adb5', sha(P / 'PREREG_E20P.md'))
pre = (P / 'PREREG_E20P.md').read_text()
ph = pre.split('PROMPTS_E20.md sha256 `')[1].split('`')[0]; chk('PROMPTS_E20.md (hash in PREREG_E20P.md)', ph, sha(P / 'PROMPTS_E20.md'))
fh = pre.split('notes/CODE_FREEZE.json sha256 `')[1].split('`')[0]; chk('notes/CODE_FREEZE.json (hash in PREREG_E20P.md)', fh, sha(P / 'notes/CODE_FREEZE.json'))
fz = json.loads((P / 'notes/CODE_FREEZE.json').read_text())['files']
for f, h in fz.items(): chk(f'CODE_FREEZE: {f}', h, sha(P / f))
out['n_code_freeze_files'] = len(fz); out['all_ok'] = all(c['ok'] for c in out['checks'])
(S / 'notes/G1_VERIFY.json').write_text(json.dumps(out, indent=1) + '\n')
print('G1', 'PASS' if out['all_ok'] else 'FAIL', f"{sum(c['ok'] for c in out['checks'])}/{len(out['checks'])} checks; CODE_FREEZE files {len(fz)}")
sys.exit(0 if out['all_ok'] else 1)
