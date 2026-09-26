"""P2_R6_X4 shared definitions: byte copy of P2_R6_X3 src/xfam_common.py (X = this X4 folder). Writes only under this folder."""
import sys
sys.dont_write_bytecode = True
import json, hashlib, pathlib, os, datetime

X = pathlib.Path(__file__).resolve().parents[1]
ROOT = X.parent
DATA_ROOT = ROOT.parent.parent
P210 = ROOT / 'P2_10_20260911T122423Z'
BND = ROOT / 'P2_CONFIDENCE_REFERENCE_BOUNDARIES_20260914T165012Z'
ZG = ROOT / 'P2_ZERO_GOLD_CONTROLS_20260914T065145Z'
MMLU = ROOT / 'P2_MMLU_PRO_BREADTH_STAGE1_20260916T002337Z'
V2L = ROOT / 'P2_SCORING_V2_20260912T191445Z/labels'
PARSER = ROOT / 'P2_SCORING_V2_20260912T191445Z/scoring_v2.py'
PARSER_SHA = 'd05978f400cf69aa6bddc56168a260ac3ea9158abaa640e9331602dc9bfcc2f9'
POP = X / 'records/populations'
RECEIVERS = {
    'qwen3_8b': dict(path=str(DATA_ROOT / 'hf_cache/hub/models--Qwen--Qwen3-8B/snapshots/b968826d9c46dd6066d109eabc6255188de91218'),
                     repo='Qwen/Qwen3-8B', revision='b968826d9c46dd6066d109eabc6255188de91218'),
    'olmo2_7b': dict(path=str(DATA_ROOT / 'hf_cache/hub/models--allenai--OLMo-2-1124-7B-Instruct/snapshots/470b1fba1ae01581f270116362ee4aa1b97f4c84'),
                     repo='allenai/OLMo-2-1124-7B-Instruct', revision='470b1fba1ae01581f270116362ee4aa1b97f4c84'),
    'llama31_8b': dict(path=str(DATA_ROOT / 'hf_cache/hub/models--meta-llama--Llama-3.1-8B-Instruct/snapshots/0e9e39f249a16976918f6564b8830bc894c89659'),
                       repo='meta-llama/Llama-3.1-8B-Instruct', revision='0e9e39f249a16976918f6564b8830bc894c89659'),
    'mistral7b_v03': dict(path=str(DATA_ROOT / 'hf_cache/hub/models--mistralai--Mistral-7B-Instruct-v0.3/snapshots/c170c708c41dac9275d15a8fff4eca08d52bab71'),
                          repo='mistralai/Mistral-7B-Instruct-v0.3', revision='c170c708c41dac9275d15a8fff4eca08d52bab71'),
}
PREFIX = 'The correct answer is'
LABELS_ALL = list('ABCDEFGHIJ')
DATASETS = ['obqa', 'arc']


def utc(): return datetime.datetime.now(datetime.timezone.utc).isoformat()


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 22), b''):
            h.update(b)
    return h.hexdigest()


def jl(p):
    with open(p) as f:
        return [json.loads(s) for s in f if s.strip()]


def read(p): return json.loads(pathlib.Path(p).read_text())


def save(p, v):
    p = pathlib.Path(p); p.parent.mkdir(parents=True, exist_ok=True)
    t = p.with_suffix(p.suffix + '.tmp'); t.write_text(json.dumps(v, ensure_ascii=False, indent=2) + '\n'); t.replace(p)


def append(p, v):
    p = pathlib.Path(p); p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, 'a') as f:
        f.write(json.dumps(v, ensure_ascii=False) + '\n'); f.flush(); os.fsync(f.fileno())


def rawline(path, line, _cache={}):
    if path not in _cache:
        with open(path) as f:
            _cache[path] = f.read().split('\n')
    return json.loads(_cache[path][line - 1])


def runtime_query(row):
    """Runtime query dict as in run_p2_10.query_only / the E4 populations: fields + 'choices'."""
    return {'question_stem': row['question_stem'], 'choice_labels': list(row['choice_labels']), 'choice_text': list(row['choice_text']),
            'choices': {'label': list(row['choice_labels']), 'text': list(row['choice_text'])}}


def parser():
    import importlib.util
    assert sha(PARSER) == PARSER_SHA
    spec = importlib.util.spec_from_file_location('xfam_scoring_v2', PARSER); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m.parse_answer
