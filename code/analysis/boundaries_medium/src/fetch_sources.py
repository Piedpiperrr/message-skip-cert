"""仅获取固定版本的官方元数据和小型配置；绝不下载权重或数据集。"""
import hashlib
import json
from pathlib import Path
from datetime import datetime, timezone
from urllib.parse import quote
import requests

P = Path(__file__).resolve().parents[1]
SPECS = {
    'helper': ('Qwen/Qwen2.5-1.5B-Instruct', '989aa7980e4cf806f80c7fef2b1adb7bc71aa306'),
    'receiver': ('Qwen/Qwen3-1.7B', '70d244cc86ccca08cf5af4e1e306ecf908b1ad5e'),
    'fuser': ('nics-efc/C2C_Fuser', 'f01fc3258b305e280e04c7238f4f2cf31b7dc70d'),
}
SUB = 'qwen3_1.7b+qwen2.5_1.5b_Fuser'

def save(p, data):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')

index = {'utc': datetime.now(timezone.utc).isoformat(), 'weights_downloaded': False,
         'local_checkpoint_hash_verification': '未执行：提交前预算门槛未通过；仅核验官方 LFS SHA256 元数据',
         'medium_model_loaded': False, 'model_forward_count': 0, 'models': {}}
session = requests.Session()
for role, (repo, revision) in SPECS.items():
    url = f'https://huggingface.co/api/models/{repo}/revision/{revision}?blobs=true'
    response = session.get(url, timeout=45)
    response.raise_for_status()
    info = response.json()
    assert info['sha'] == revision and info['id'] == repo
    manifest = P / 'evidence' / f'{role}_official_manifest.json'
    manifest.write_bytes(response.content)
    siblings = [f for f in info['siblings'] if role != 'fuser' or f['rfilename'].startswith(SUB + '/')]
    weights = [f for f in siblings if f['rfilename'].endswith(('.safetensors', '.pt'))]
    assert weights and all('lfs' in f for f in weights)
    files = []
    for f in siblings:
        name = f['rfilename']
        allowed = name.endswith('.json') if role == 'fuser' else name in {
            'config.json', 'generation_config.json', 'tokenizer_config.json',
            'tokenizer.json', 'vocab.json', 'merges.txt', 'special_tokens_map.json',
            'added_tokens.json', 'chat_template.jinja', 'model.safetensors.index.json'}
        if not allowed:
            continue
        assert f['size'] < 25 * 1024**2
        local = P / 'protocol/models' / role / name
        if local.exists():
            body = local.read_bytes()
        else:
            download = f'https://huggingface.co/{repo}/resolve/{revision}/{quote(name, safe="/")}'
            content = session.get(download, timeout=60)
            content.raise_for_status()
            body = content.content
            local.parent.mkdir(parents=True, exist_ok=True)
            local.write_bytes(body)
        assert len(body) == f['size'], name
        git_hash = hashlib.sha1(b'blob ' + str(len(body)).encode() + b'\0' + body).hexdigest()
        body_sha = hashlib.sha256(body).hexdigest()
        if 'lfs' in f:
            assert body_sha == f['lfs']['sha256'], name
        else:
            assert git_hash == f['blobId'], (name, git_hash, f['blobId'])
        files.append({'path': str(local.relative_to(P)), 'size': len(body),
                      'sha256': body_sha, 'git_blob_verified': 'lfs' not in f,
                      'LFS_sha256_verified': 'lfs' in f,
                      'official_file': name, 'official_blob_id': f['blobId']})
    weight_digest = hashlib.sha256(json.dumps(
        [(f['rfilename'], f['lfs']['sha256'], f['size']) for f in sorted(weights, key=lambda f: f['rfilename'])],
        separators=(',', ':')).encode()).hexdigest()
    index['models'][role] = {'repo_id': repo, 'revision': revision, 'metadata_url': url,
        'official_manifest': str(manifest.relative_to(P)),
        'official_manifest_sha256': hashlib.sha256(response.content).hexdigest(),
        'subfolder': SUB + '/final' if role == 'fuser' else None,
        'weight_bytes': sum(f['size'] for f in weights),
        'checkpoint_files': weights, 'checkpoint_manifest_sha256': weight_digest,
        'checkpoint_hash_kind': '官方 LFS 哈希清单；不是本地权重实测哈希',
        'verified_local_config_tokenizer_files': files,
        'prospective_weight_destination': str(P / 'assets' / role),
        'checkpoint_local_verified': False}
    print(role, revision, 'small_files_verified', len(files), 'weight_files_not_downloaded', len(weights), flush=True)
save(P / 'MODEL_SOURCE_INDEX.json', index)
