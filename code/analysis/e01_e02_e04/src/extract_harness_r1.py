"""Harness replacing P2_E1_DIRECTION common.py for the copied extractor (extract_features_r1.py).

Only bookkeeping changes: where rows come from, where features are written, the per-model spec table
(small/large copied verbatim from P2_E1_DIRECTION frozen_config.json; medium added by the frozen depth rule),
and a walltime stop. The feature computation in extract_features_r1.py is unchanged (see extract_features_r1.diff).
"""
import sys
sys.dont_write_bytecode = True
import os, json, csv, hashlib, time, datetime, socket, collections, pathlib
from common_r1 import NEW, ROOT, MEDX, POP, sha, utc, save, append

E1DIR = ROOT / 'P2_E1_DIRECTION_20260913T053456Z'
_e1 = json.loads((E1DIR / 'frozen_config.json').read_text())
MEDIUM_LAYERS, SMALL_LAYERS, SMALL_K = 28, 28, 19
# Frozen rule (same formula P2-10 used for small->large AC layers): j = floor((k_small+1)*L/L_small + 0.5); k = j-1
MEDIUM_K = int(((SMALL_K + 1) * MEDIUM_LAYERS / SMALL_LAYERS) + 0.5) - 1
assert MEDIUM_K == 19
CFG = {'models': {
    'small': dict(_e1['models']['small']),
    'large': dict(_e1['models']['large']),
    'medium': {'repo_id': 'Qwen/Qwen3-1.7B', 'revision': '70d244cc86ccca08cf5af4e1e306ecf908b1ad5e',
               'path': str(MEDX / 'assets/receiver'),
               'chat_template_sha256': 'a55ee1b1660128b7098723e0abcd92caa0788061051c62d51cbe87d9cf1974d8',
               'hidden_size': 2048, 'num_hidden_layers': 28, 'max_position_embeddings': 40960,
               'ac_block_index': MEDIUM_K}}}
assert CFG['models']['small']['ac_block_index'] == 19 and CFG['models']['large']['ac_block_index'] == 25
FREEZE = {'config_sha256': sha(NEW / 'PROTOCOL_FREEZE.md')}
PAIR = sys.argv[1]
O = NEW / 'results/e2b' / PAIR
FOLDS = collections.defaultdict(lambda: None)  # no fold map for these populations
_rows = {}


def queries(ds):
    if ds not in _rows:
        assert ds.startswith(PAIR + '_'), (PAIR, ds)
        with open(POP / f'e2b_{ds}.jsonl') as f:
            _rows[ds] = [json.loads(l) for l in f if l.strip()]
    return _rows[ds]


LIMIT = sum(len(queries(ds)) for ds in sys.argv[2].split(','))


def jl(p):
    return [json.loads(s) for s in pathlib.Path(p).read_text().splitlines()] if pathlib.Path(p).exists() else []


def feature_path(pair, ds, i):
    return O / 'features' / ds / f'{i:05d}.npz'


def require_compute():
    # R1 ClusterA (DEVIATIONS.md D3): also accept ClusterA compute nodes (x3...); login nodes are still refused
    assert os.environ.get('PBS_JOBID') and socket.gethostname().startswith(('ClusterB-gpu', 'x3'))


def stop_check():
    if time.time() > float(os.environ.get('R1_DEADLINE_EPOCH', 'inf')) - 60:
        raise RuntimeError('R1_WALLTIME_STOP: preserve written features')
