"""X3 Step 0: receiver availability + label-token rule, in the preregistered order. Tokenizer/config files only; no model output; no gold.
(a) cached on the shared filesystem or downloadable with the project's HF token via the proxy; (b) X2 label-token rule (run_x2.py) holds for the probe labels.
Writes notes/STEP0_RECEIVER_CHECK.json."""
import sys
sys.dont_write_bytecode = True
import json, pathlib, datetime, os, glob, hashlib
from huggingface_hub import HfApi, hf_hub_download
from transformers import AutoTokenizer

X = pathlib.Path(__file__).resolve().parents[1]
CACHE = '$DATA_DIR/hf_cache/hub'   # X2 download location
ORDER = ['meta-llama/Llama-3.1-8B-Instruct', 'mistralai/Mistral-7B-Instruct-v0.3', 'ibm-granite/granite-3.1-8b-instruct']
PREFIX = 'The correct answer is'
PROBE_LABELS = list('ABCDE')      # OBQA A-D, ARC A-E (display labels)
api = HfApi(); out = dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), whoami=api.whoami()['name'], models={})


def label_rule(tok):
    sets = {l: [] for l in 'ABCDEFGHIJ'}; special = set(tok.all_special_ids)
    for v in sorted(set(tok.get_vocab().values())):
        if v in special: continue
        d = tok.decode([v], skip_special_tokens=False, clean_up_tokenization_spaces=False)
        if d.strip() in sets: sets[d.strip()].append(v)
    used = {l: sets[l] for l in PROBE_LABELS}; allv = [v for s in used.values() for v in s]
    single = {l: tok.encode(l, add_special_tokens=False) for l in PROBE_LABELS}
    pid = tok.encode(PREFIX, add_special_tokens=False)
    return dict(label_token_sets_A_E=used, counts_A_E={l: len(v) for l, v in used.items()}, nonempty=all(used.values()), disjoint=len(set(allv)) == len(allv),
                encode_label_alone=single, each_label_single_token=all(len(v) == 1 for v in single.values()),
                decoded_set_members={l: [tok.decode([v], skip_special_tokens=False, clean_up_tokenization_spaces=False) for v in s] for l, s in used.items()},
                prefix_ids=pid, prefix_roundtrip=tok.decode(pid, skip_special_tokens=False, clean_up_tokenization_spaces=False) == PREFIX,
                chat_template_sha256=hashlib.sha256(tok.chat_template.encode()).hexdigest() if isinstance(tok.chat_template, str) else None,
                passes=all(used.values()) and len(set(allv)) == len(allv))


for repo in ORDER:
    m = dict(); out['models'][repo] = m
    try:
        mi = api.model_info(repo, files_metadata=True); m.update(sha=mi.sha, gated=mi.gated)
        m['hub_files'] = {s.rfilename: dict(blob_id=s.blob_id, lfs_sha256=(s.lfs.sha256 if s.lfs else None), size=s.size) for s in mi.siblings}
    except Exception as e:
        m['model_info_error'] = f'{type(e).__name__}: {str(e)[:300]}'; continue
    try:
        p = hf_hub_download(repo, 'config.json', revision=m['sha'], cache_dir=CACHE); m['download'] = 'ok'
    except Exception as e:
        m['download'] = f'DENIED/FAILED {type(e).__name__}: {str(e)[:300]}'
    # shared-filesystem copies (this user's caches, then any readable copy in the project area)
    name = 'models--' + repo.replace('/', '--')
    cands = sorted(set(glob.glob(f'$DATA_DIR/*/hf_cache/hub/{name}/snapshots/*') + glob.glob(f'$DATA_DIR/*/*/.hf-cache/hub/{name}/snapshots/*')
                       + glob.glob(f'$DATA_DIR/cache/huggingface/hub/{name}/snapshots/*')
                       + glob.glob(f'$DATA_DIR/*/{repo.split("/")[1]}')))
    m['sharedfs_copies'] = []
    for c in cands:
        e = dict(path=c, owner_area=c.split('/')[5], this_user=c.split('/')[5] == 'user', files={})
        for f, meta in m['hub_files'].items():
            fp = pathlib.Path(c) / f
            if not fp.exists(): continue
            tgt = os.path.basename(os.path.realpath(fp)) if fp.is_symlink() else None
            e['files'][f] = dict(size_ok=fp.stat().st_size == meta['size'], blob_name_matches_hub=(tgt in (meta['blob_id'], meta['lfs_sha256'])) if tgt else None)
        need = [f for f in m['hub_files'] if f.endswith('.safetensors') or f in ('config.json', 'tokenizer.json', 'tokenizer_config.json', 'generation_config.json')]
        e['required_files_present_size_ok'] = all(f in e['files'] and e['files'][f]['size_ok'] for f in need)
        m['sharedfs_copies'].append(e)
    # tokenizer: downloaded (if allowed) else first readable shared-filesystem copy (read-only)
    src = None
    if m['download'] == 'ok':
        for f in ['tokenizer.json', 'tokenizer_config.json', 'special_tokens_map.json', 'tokenizer.model', 'generation_config.json']:
            if f in m['hub_files']: hf_hub_download(repo, f, revision=m['sha'], cache_dir=CACHE)
        src = str(pathlib.Path(CACHE) / name / 'snapshots' / m['sha'])
    elif m['sharedfs_copies']:
        src = m['sharedfs_copies'][0]['path']
    m["tokenizer_source"] = src; print("TOKENIZER_SOURCE", repo, src, flush=True)
    if src:
        try:
            tok = AutoTokenizer.from_pretrained(src, local_files_only=True)
        except Exception as e:
            m['tokenizer_load_error'] = f'{type(e).__name__}: {str(e)[:300]}'; print('TOKENIZER_LOAD_ERROR', repo, m['tokenizer_load_error'], flush=True); continue
        m['label_rule'] = label_rule(tok)
        m['tokenizer_class'] = type(tok).__name__; m['vocab_size'] = len(tok.get_vocab())
json.dump(out, open(X / 'notes/STEP0_RECEIVER_CHECK.json', 'w'), indent=1)
for r, m in out['models'].items():
    print(r, m.get('sha'), 'gated', m.get('gated'), 'download:', str(m.get('download'))[:80])
    for e in m.get('sharedfs_copies', []): print('   sharedfs', e['path'], 'this_user', e['this_user'], 'complete', e['required_files_present_size_ok'],
                                               'blobs_match', all(v['blob_name_matches_hub'] in (True, None) for v in e['files'].values()))
    lr = m.get('label_rule')
    if lr: print('   label rule passes', lr['passes'], 'single', lr['each_label_single_token'], lr['encode_label_alone'], lr['label_token_sets_A_E'], 'prefix ok', lr['prefix_roundtrip'])
