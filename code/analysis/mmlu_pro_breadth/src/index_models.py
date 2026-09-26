"""CPU只读计算冻结模型及fuser文件hash；不加载tensor或运行模型。"""
from common import *
config=read(P/'protocol/large_native_config.json')
specs={r:config['models'][r] for r in ['helper','receiver']};specs['fuser']=config['fuser']
index={}
for role,spec in specs.items():
    path=Path(spec['path']);print('HASH_BEGIN',role,str(path),flush=True)
    files=[]
    names=[p for p in sorted(path.iterdir()) if p.is_file() and p.suffix in ['.json','.safetensors','.pt','.txt','.model']]
    for f in names:
        files.append(dict(name=f.name,path=str(f),resolved_path=str(f.resolve()),bytes=f.stat().st_size,sha256=sha(f)))
    assert any(x['name'].endswith(('.safetensors','.pt')) for x in files)
    index[role]=dict(repo_id=spec['repo_id'],revision=spec['revision'],path=str(path),files=files,
        aggregate_sha256=hashlib.sha256(json.dumps(files,sort_keys=True).encode()).hexdigest(),chat_template_sha256=spec.get('chat_template_sha256'))
    print('HASH_COMPLETE',role,len(files),sum(x['bytes'] for x in files),flush=True)
save(P/'MODEL_SOURCE_INDEX.json',dict(utc=utc(),models=index,model_loads=0,model_forwards=0,
    identity_source=str(NATIVE/'frozen_config.json'),identity_source_sha256=sha(NATIVE/'frozen_config.json'),
    policy='本地历史冻结revision；所有实际加载的weights/config/tokenizer/映射逐文件SHA256；正式job加载前再次核对'))
