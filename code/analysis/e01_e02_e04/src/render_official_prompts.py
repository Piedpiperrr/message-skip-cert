"""Render the first 3 receiver prompts of every OFFICIAL E1 run through the official evaluator's own code
(UnifiedEvaluator._format_openbookqa_example + prepare_model_inputs, CPU, tokenizer only; no model weights).
Uses the exact config each run used (task7 config for the reused small-pair C2C run, output_dir redirected
into this experiment folder so nothing is written elsewhere). Neither clone is modified.
"""
import sys
sys.dont_write_bytecode = True
import json, os, pathlib, copy
import yaml
from common_r1 import *

CLEAN = DATA_ROOT / 'c2c_reproduction_assets/official_C2C'
PATCH = pathlib.Path('$HOME_DIR/c2c_reproduction_runtime_patch')
TASK7_CFG = pathlib.Path('$HOME_DIR/c2c_reproduction_control/task5_recovery/configs/openbookqa_c2c_full500.yaml')
OUT = pathlib.Path(os.environ.get('R1_RENDER_OUT', NEW / 'results/e1/prompts/official.json'))
SCRATCH = pathlib.Path(os.environ.get('R1_RENDER_SCRATCH', NEW / 'logs/render_scratch'))
RUNS = NEW / 'results/e1/official'

todo = []
for chain in ['A', 'B']:
    p = RUNS / f'RUNS_chain{chain}.jsonl'
    if p.exists():
        for r in jl(p):
            if r.get('valid'):
                todo.append((r['run'], r['kind'], pathlib.Path(r['config'])))
todo.append(('small_C', 'task7_patch', TASK7_CFG))

results = []
for run, kind, cfgp in todo:
    repo = CLEAN if kind == 'clean' else PATCH
    code = f'''
import sys, json, os
sys.dont_write_bytecode = True
sys.path.insert(0, {str(repo)!r})
import importlib.util, yaml, torch
spec = importlib.util.spec_from_file_location('ue', {str(repo / 'script/evaluation/unified_evaluator.py')!r})
ue = importlib.util.module_from_spec(spec); spec.loader.exec_module(ue)
from transformers import AutoTokenizer
cfg = yaml.safe_load(open({str(cfgp)!r}))
cfg['output']['output_dir'] = {str(SCRATCH)!r}
ev = ue.UnifiedEvaluator(cfg)
mc = cfg['model']
if 'rosetta' in mc['model_name'].lower():
    path = mc['rosetta_config']['base_model']; model_type = 'rosetta'
    tok = AutoTokenizer.from_pretrained(str(path)); ue.set_default_chat_template(tok, path)
else:
    path = mc['model_name']; model_type = 'qwen' if 'Qwen' in path else 'hf'
    tok = AutoTokenizer.from_pretrained(str(path), trust_remote_code=True, padding_side='left')
    if tok.pad_token is None: tok.pad_token = tok.eos_token
    ue.set_default_chat_template(tok, path)
if getattr(ev, 'local_openbookqa_parquet', None):
    ds = ue._load_openbookqa_dataset(ev.dataset_config, ev.local_openbookqa_parquet)
else:
    ds = ue.load_dataset(ev.dataset_config['dataset_name'])
test = ds[ev.dataset_config['test_split']]
out = []
for i in range(3):
    ex = test[i]
    prompt = ev._format_openbookqa_example(ex, use_cot=cfg['eval']['use_cot'], use_template=cfg['eval']['use_template'])
    prep = ev.prepare_model_inputs(prompt=prompt, tokenizer=tok, device=torch.device('cpu'), model_type=model_type,
                                   llm_tokenizer=None, answer_method=cfg['eval']['answer_method'])
    kv = prep['inputs'].get('kv_cache_index')
    out.append(dict(question_id=i, id=ex['id'], user_message=prompt, rendered=prep['printable_text'],
                    rendered_input_ids=prep['inputs']['input_ids'][0].tolist(), model_type=model_type,
                    kv_cache_index_segments=[list(t.shape) + [t[0,0].tolist()] for t in kv] if kv is not None else None))
print('RENDER_JSON=' + json.dumps(out))
'''
    env = dict(os.environ, CUDA_VISIBLE_DEVICES='', PYTHONDONTWRITEBYTECODE='1', HF_HOME=str(NEW / 'cache/hf_official'),
               HF_HUB_CACHE=str(NEW / 'cache/hf_official/hub'), HF_DATASETS_CACHE=str(NEW / 'cache/hf_official/datasets'),
               HF_DATASETS_OFFLINE='1', HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1')
    import subprocess
    proc = subprocess.run([str(DATA_ROOT / 'software/envs/c2c_official/bin/python'), '-c', code], env=env, cwd=SCRATCH.parent,
                          capture_output=True, text=True, timeout=1200)
    rec = {'run': run, 'kind': kind, 'config': str(cfgp), 'config_sha256': sha(cfgp), 'returncode': proc.returncode}
    line = [l for l in proc.stdout.splitlines() if l.startswith('RENDER_JSON=')]
    if line:
        rec['prompts'] = json.loads(line[-1][len('RENDER_JSON='):])
    else:
        rec['stderr_tail'] = proc.stderr[-3000:]
    results.append(rec)
    print(run, kind, proc.returncode, flush=True)
save(OUT, results)
