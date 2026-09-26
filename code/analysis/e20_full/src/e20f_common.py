"""E20F shared paths, split lists and hash checks (no torch). Pilot modules are imported from the pilot directory, unmodified."""
import sys, json, hashlib, pathlib
sys.dont_write_bytecode = True
E20F = pathlib.Path(__file__).resolve().parents[1]
ROOT = E20F.parent
PILOT_DIR = ROOT / 'P2_R8_E20P_20260921T224653Z'
if str(PILOT_DIR / 'src') not in sys.path: sys.path.insert(0, str(PILOT_DIR / 'src'))
PHASES = {'fitcal': ['fit', 'cal'], 'devtest': ['dev', 'test']}
N_SPLIT = {'fit': 500, 'cal': 2000, 'dev': 1000, 'test': 1000}


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 22), b''): h.update(b)
    return h.hexdigest()


def jl(p):
    with open(p) as f:
        return [json.loads(s) for s in f if s.strip()]


def base(dry): return E20F / 'notes/dryrun' if dry else E20F


def check_hashfile(hf, name):
    """'<sha>  <name>' first line; returns the sha after verifying the file."""
    h, n = pathlib.Path(hf).read_text().split('\n')[0].split('  ')
    assert n == name and sha(pathlib.Path(hf).parent / n) == h, f'{name} missing or changed since it was hashed'
    return h


def load_cert(dry):
    b = base(dry)
    h = check_hashfile(b / 'CERT_E20F.sha256', 'CERT_E20F.json')
    return json.loads((b / 'CERT_E20F.json').read_text()), h


def phase_splits(phase, dry):
    """fitcal -> fit, cal; devtest -> dev, plus test only if CERT_E20F.json (hash verified) deployed a threshold."""
    if phase == 'fitcal': return ['fit', 'cal']
    cert, _ = load_cert(dry)
    return ['dev'] + (['test'] if cert['deployed_q'] > 0 else [])


def split_items(sp): return jl(E20F / f'inputs/FULL_{sp}.jsonl')


def check_freezes():
    """Pilot CODE_FREEZE.json (27 files) and this stage's notes/CODE_FREEZE_E20F.json, file by file."""
    bad = []
    for base_dir, fz in [(PILOT_DIR, PILOT_DIR / 'notes/CODE_FREEZE.json'), (E20F, E20F / 'notes/CODE_FREEZE_E20F.json')]:
        for f, h in json.loads(fz.read_text())['files'].items():
            if sha(base_dir / f) != h: bad.append(str(base_dir / f))
    assert not bad, f'CODE_FREEZE mismatch: {bad}'
