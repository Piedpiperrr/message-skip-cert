"""E20P G1: download the pinned train files of the 4 candidate datasets (login node, the-cluster proxy). No model involved."""
import json, hashlib, datetime, pathlib
from huggingface_hub import hf_hub_download
STAGE = pathlib.Path(__file__).resolve().parents[1]
SPEC = {
    'squad': ('rajpurkar/squad', '7b6d24c440a36b6815f21b70d25016731768db1f', ['plain_text/train-00000-of-00001.parquet']),
    'nqp': ('mrqa-workshop/mrqa', 'f3178d9888471dfb2b67c93de14f0ddf499a8d9f', [f'plain_text/train-{i:05d}-of-00009.parquet' for i in range(9)]),
    'triviaqa': ('mandarjoshi/trivia_qa', '0f7faf33a3908546c6fd5b73a660e0f8ff173c2f', ['rc.nocontext/train-00000-of-00001.parquet']),
    'nqopen': ('google-research-datasets/nq_open', '5dd9790a83002ad084ddeb7c420dc716852c6f28', ['nq_open/train-00000-of-00001.parquet']),
}
def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 22), b''): h.update(b)
    return h.hexdigest()
out = {}
for ds, (repo, rev, files) in SPEC.items():
    out[ds] = dict(repo=repo, revision=rev, files={})
    for fn in files:
        p = hf_hub_download(repo, fn, repo_type='dataset', revision=rev)
        out[ds]['files'][fn] = dict(path=p, sha256=sha(p), bytes=pathlib.Path(p).stat().st_size)
        print(ds, fn, out[ds]['files'][fn]['sha256'], flush=True)
out['_utc'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
(STAGE / 'notes/DOWNLOAD_MANIFEST.json').write_text(json.dumps(out, indent=2) + '\n')
