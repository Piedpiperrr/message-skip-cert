"""E20F Step 7 (login node), ONLY after STATS_E20F.json and ROUTES_E20F.json are hashed: gold answers (SQuAD answers.text of the pinned train
parquet, read only for dev / test ids) for accuracy. Exact match after the pilot normalization (e20_extract.normalize_text) against any gold
answer; INVALID is incorrect. Policy output = receiver-only answer if routed 'omit', else the receiver-with-message answer (ROUTES_E20F.json).
Per split (dev; test if routed): R, Text, policy as x/n with paired bootstrap 95% intervals (numpy default_rng(0), 2,000, the same resample
indices for all), G = acc(Text) - acc(R) with interval; kappa*alpha = dev coverage x .05 against G; among changes (and among omitted changes):
reference corrects (R wrong, Text right) / breaks (R right, Text wrong) / both wrong. Writes results/ACCURACY_E20F.json and
logs/GOLD_FIRST_OPENED.utc. usage: e20f_gold.py [--dry-run --manifest <synthetic manifest>]"""
import sys, json, argparse, pathlib, datetime
sys.dont_write_bytecode = True
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import e20f_common as FC
from e20_extract import INVALID, normalize_text, changed                     # pilot module
import numpy as np
import pyarrow as pa
pa.set_cpu_count(1); pa.set_io_thread_count(1)
import pyarrow.parquet as pq

ap = argparse.ArgumentParser(); ap.add_argument('--dry-run', action='store_true'); ap.add_argument('--manifest', default=None); a = ap.parse_args()
REAL = FC.E20F / 'pool/notes/DOWNLOAD_MANIFEST.json'
MANP = pathlib.Path(a.manifest) if a.manifest else REAL
assert not a.dry_run or MANP.resolve() != REAL.resolve(), 'dry run must not open the real gold files'
B = FC.base(a.dry_run); RES = B / 'results'
utc = lambda: datetime.datetime.now(datetime.timezone.utc).isoformat()
hs = FC.check_hashfile(B / 'STATS_E20F.sha256', 'STATS_E20F.json'); hr = FC.check_hashfile(B / 'ROUTES_E20F.sha256', 'ROUTES_E20F.json')
gl = (RES if a.dry_run else B / 'logs') / 'GOLD_FIRST_OPENED.utc'
if not gl.exists(): gl.write_text(utc() + f'  (after STATS_E20F.json {hs} and ROUTES_E20F.json {hr})\n')
stats = json.loads((B / 'STATS_E20F.json').read_text()); routes = json.loads((B / 'ROUTES_E20F.json').read_text())['routes']
R = {(r['split'], r['id']): r['route'] for r in routes}
rows = {r['id']: r for r in FC.jl(RES / 'E20F_devtest_rows.jsonl')}
SPL = [sp for sp in ['dev', 'test'] if any(k[0] == sp for k in R)]
want = {i for (sp, i) in R if sp in SPL}
man = json.loads(MANP.read_text())['squad']; (fn, v), = man['files'].items(); assert FC.sha(v['path']) == v['sha256']
gold = {}
for x in pq.read_table(v['path'], columns=['id', 'answers'], use_threads=False).to_pylist():
    if x['id'] in want and x['id'] not in gold: gold[x['id']] = {normalize_text(t) for t in x['answers']['text']} - {''}
assert want <= set(gold), 'gold missing for some ids'


def ci(v): return [float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))]


out = dict(utc=utc(), stats_sha256=hs, routes_sha256=hr, splits={})
for sp in SPL:
    ids = [i for (s, i) in R if s == sp]
    oR = [rows[i]['llama']['R']['answer'] for i in ids]; oT = [rows[i]['llama']['T']['answer'] for i in ids]
    om = np.array([R[(sp, i)] == 'omit' for i in ids], bool)
    cR = np.array([a_ != INVALID and a_ in gold[i] for a_, i in zip(oR, ids)], bool)
    cT = np.array([b != INVALID and b in gold[i] for b, i in zip(oT, ids)], bool)
    cP = np.where(om, cR, cT); d = np.array([changed(x, y) for x, y in zip(oR, oT)], bool); n = len(ids)
    rng = np.random.default_rng(0); bs = {k: [] for k in ['R', 'Text', 'policy', 'G']}
    for _ in range(2000):
        ix = rng.integers(0, n, n)
        bs['R'].append(cR[ix].mean()); bs['Text'].append(cT[ix].mean()); bs['policy'].append(cP[ix].mean()); bs['G'].append(cT[ix].mean() - cR[ix].mean())
    G = float(cT.mean() - cR.mean())

    def cb(m): return dict(n=int(m.sum()), reference_corrects=int((m & ~cR & cT).sum()), reference_breaks=int((m & cR & ~cT).sum()),
                           both_wrong=int((m & ~cR & ~cT).sum()), both_right=int((m & cR & cT).sum()))
    out['splits'][sp] = dict(n=n, R_correct=int(cR.sum()), Text_correct=int(cT.sum()), policy_correct=int(cP.sum()),
                             acc_R=float(cR.mean()), acc_Text=float(cT.mean()), acc_policy=float(cP.mean()),
                             CI95={k: ci(v_) for k, v_ in bs.items()}, G=G, omitted=int(om.sum()), coverage=float(om.mean()),
                             changes=cb(d), omitted_changes=cb(d & om))
dv = out['splits']['dev']
ka = stats['dev']['coverage'] * .05
out['kappa_alpha'] = dict(value=ka, definition='dev coverage x 5 points', G_dev=dv['G'], G_dev_CI95=dv['CI95']['G'], G_le_kappa_alpha=dv['G'] <= ka,
                          G_CI_includes_0=dv['CI95']['G'][0] <= 0 <= dv['CI95']['G'][1])
out['rule5_redundancy_triggered'] = bool(out['kappa_alpha']['G_le_kappa_alpha'] or out['kappa_alpha']['G_CI_includes_0'])
(RES / 'ACCURACY_E20F.json').write_text(json.dumps(out, indent=1) + '\n')
print(json.dumps(out, indent=1))
