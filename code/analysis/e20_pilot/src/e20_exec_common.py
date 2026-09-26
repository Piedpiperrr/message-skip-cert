"""E20P shared definitions (models, datasets, paths, IO). No torch at import. Writes only under this stage."""
import sys, json, hashlib, pathlib, os, datetime
sys.dont_write_bytecode = True
HERE = pathlib.Path(__file__).resolve().parent
STAGE = HERE.parent
ROOT = STAGE.parent
P10 = ROOT / 'P2_10_20260911T122423Z'
BOUND = ROOT / 'P2_CONFIDENCE_REFERENCE_BOUNDARIES_20260914T165012Z'
X3 = ROOT / 'P2_R6_X3_20260921T052602Z'
CFG = json.loads((ROOT / 'P2_R3_E9BC_20260920T061042Z/large/frozen_config.json').read_text())['native']
MODELS = {
    'helper': dict(repo=CFG['models']['helper']['repo_id'], revision=CFG['models']['helper']['revision'], path=CFG['models']['helper']['path'],
                   chat_template_sha256=CFG['models']['helper']['chat_template_sha256']),
    'qwen3': dict(repo=CFG['models']['receiver']['repo_id'], revision=CFG['models']['receiver']['revision'], path=CFG['models']['receiver']['path'],
                  chat_template_sha256=CFG['models']['receiver']['chat_template_sha256']),
    'llama': dict(repo='meta-llama/Llama-3.1-8B-Instruct', revision='0e9e39f249a16976918f6564b8830bc894c89659',
                  path='$DATA_DIR/hf_cache/hub/models--meta-llama--Llama-3.1-8B-Instruct/snapshots/'
                       '0e9e39f249a16976918f6564b8830bc894c89659',
                  chat_template_sha256='e10ca381b1ccc5cf9db52e371f3b6651576caee0a630b452e2816b2d404d4b65'),   # = X3 chain env.json
}
DATASETS = ['squad', 'nqp', 'triviaqa', 'nqopen']
JOBS = {'A': ['squad', 'nqp'], 'B': ['triviaqa', 'nqopen']}
NAME = {'squad': 'SQuAD', 'nqp': 'NQ-passage', 'triviaqa': 'TriviaQA', 'nqopen': 'NQ-Open'}
RECEIVERS = ['qwen3', 'llama']
HELPER_MAX_NEW, RECEIVER_MAX_NEW = 256, 32


def PILOT(ds): return STAGE / f'inputs/PILOT_{ds}.jsonl'


def utc(): return datetime.datetime.now(datetime.timezone.utc).isoformat()


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 22), b''): h.update(b)
    return h.hexdigest()


def jl(p):
    with open(p) as f:
        return [json.loads(s) for s in f if s.strip()]


def save(p, v):
    p = pathlib.Path(p); p.parent.mkdir(parents=True, exist_ok=True)
    t = p.with_suffix(p.suffix + '.tmp'); t.write_text(json.dumps(v, ensure_ascii=False, indent=2, allow_nan=False) + '\n'); t.replace(p)


def append(fh, v):
    fh.write(json.dumps(v, ensure_ascii=False, allow_nan=False) + '\n'); fh.flush(); os.fsync(fh.fileno())


def load_tokenizer(role):
    from transformers import AutoTokenizer
    tok = AutoTokenizer.from_pretrained(MODELS[role]['path'], local_files_only=True)
    assert hashlib.sha256(tok.chat_template.encode()).hexdigest() == MODELS[role]['chat_template_sha256'], role
    if tok.pad_token is None: tok.pad_token = tok.eos_token
    return tok
