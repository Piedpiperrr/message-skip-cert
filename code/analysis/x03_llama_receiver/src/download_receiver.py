"""X3: access check + download of one receiver with user's own HF token (login node, the-cluster proxy), then verify every downloaded file:
LFS files against the HF LFS SHA-256, other files against the git blob SHA-1. HF-format files only (original/, consolidated.*, params.json skipped).
The first network action is the access check (config.json at the pinned revision); on failure it records the error and exits 2.
usage: download_receiver.py <repo> <revision> <tag>   ->  manifests/DOWNLOAD_<tag>.json"""
import sys
sys.dont_write_bytecode = True
import json, hashlib, pathlib, datetime, time
from huggingface_hub import HfApi, hf_hub_download, snapshot_download

X = pathlib.Path(__file__).resolve().parents[1]
CACHE = '$DATA_DIR/hf_cache/hub'
repo, rev, tag = sys.argv[1:4]
utc = lambda: datetime.datetime.now(datetime.timezone.utc).isoformat()
out = dict(repo=repo, revision=rev, cache_dir=CACHE, access_check_utc=utc())
api = HfApi(); out['whoami'] = api.whoami()['name']
M = X / 'manifests'; M.mkdir(exist_ok=True)
try:
    hf_hub_download(repo, 'config.json', revision=rev, cache_dir=CACHE); out['access'] = 'granted'
except Exception as e:
    out['access'] = f'DENIED/FAILED {type(e).__name__}: {str(e)[:400]}'
    json.dump(out, open(M / f'DOWNLOAD_{tag}.json', 'w'), indent=1); print('ACCESS', out['access'][:200]); sys.exit(2)
print('ACCESS granted', utc(), flush=True)
mi = api.model_info(repo, revision=rev, files_metadata=True); assert mi.sha == rev, (mi.sha, rev)
keep = [s for s in mi.siblings if not (s.rfilename.startswith('original/') or s.rfilename.startswith('consolidated') or s.rfilename in ('params.json', 'tokenizer.model.v3'))]
t0 = time.time()
snap = snapshot_download(repo, revision=rev, cache_dir=CACHE, allow_patterns=[s.rfilename for s in keep])
out.update(snapshot=snap, download_seconds=time.time() - t0, files={})
for s in keep:
    p = pathlib.Path(snap) / s.rfilename; b = p.read_bytes() if not s.lfs else None
    if s.lfs:
        h = hashlib.sha256()
        with open(p, 'rb') as f:
            for c in iter(lambda: f.read(1 << 24), b''): h.update(c)
        got, want, kind = h.hexdigest(), s.lfs.sha256, 'lfs_sha256'
    else:
        got, want, kind = hashlib.sha1(b'blob %d\0' % len(b) + b).hexdigest(), s.blob_id, 'git_blob_sha1'
    out['files'][s.rfilename] = dict(size=p.stat().st_size, size_hub=s.size, kind=kind, hash=got, hub=want, ok=(got == want and p.stat().st_size == s.size))
out['all_ok'] = all(v['ok'] for v in out['files'].values()); out['verified_utc'] = utc()
json.dump(out, open(M / f'DOWNLOAD_{tag}.json', 'w'), indent=1)
print('VERIFY', 'all_ok' if out['all_ok'] else 'MISMATCH', len(out['files']), 'files', round(out['download_seconds']), 's', snap, flush=True)
sys.exit(0 if out['all_ok'] else 3)
