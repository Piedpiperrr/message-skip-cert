"""E1 OFFICIAL path orchestrator: official C2C unified_evaluator.py, configuration-only changes.

Primary: clean clone (commit 113c3a9, no local changes) with the official recipe
recipe/eval_recipe/unified_eval.yaml; only model/fuser paths, dataset, output dir and gpu_ids change.
The clean evaluator pops CUDA_VISIBLE_DEVICES and loads OBQA with load_dataset("openbookqa")
(hub, via the the-cluster proxy; cache inside this experiment folder).
Fallback (only if the clean run does not yield a valid 500-row CSV): ~/c2c_reproduction_runtime_patch
(same commit + uncommitted patch: optional local OBQA parquet, optional CUDA_VISIBLE_DEVICES preservation),
exactly as task7 ran it. Neither clone is modified.

Modes:  --prefetch            one load_dataset("openbookqa") into the experiment cache (CPU), verified vs local parquet
        --chain A|B --gpu N   run that chain's evaluator runs sequentially on physical GPU N
"""
import sys
sys.dont_write_bytecode = True
import argparse, copy, csv, json, os, subprocess, time, pathlib
import yaml
from common_r1 import *

CLEAN = DATA_ROOT / 'c2c_reproduction_assets/official_C2C'
PATCH = pathlib.Path('$HOME_DIR/c2c_reproduction_runtime_patch')
CLEAN_EVAL_SHA = 'ea198b74544a1008de876ea6f163e8466dc242f2ddb7af59d64a76524ea49c27'
PATCH_EVAL_SHA = '1d4ec4aec511229c2254b9c82c6661a3b96f6b2f542430a86b84df05645f88f2'
RECIPE = CLEAN / 'recipe/eval_recipe/unified_eval.yaml'
RECIPE_SHA = 'a1e0497962f4458abfc5d6a9a662d09bfca28f6a9a33b9f0b7f43d8f4a8c72aa'
PARQUET = DATA_ROOT / 'c2c_reproduction_assets/datasets/allenai--openbookqa/main/test-00000-of-00001.parquet'
OFFCACHE = NEW / 'cache/hf_official'
PY = DATA_ROOT / 'software/envs/c2c_official/bin/python'
MODELS = {
    'small': {'receiver': DATA_ROOT / 'c2c_reproduction_assets/models/Qwen--Qwen3-0.6B',
              'helper': DATA_ROOT / 'c2c_reproduction_assets/models/Qwen--Qwen2.5-0.5B-Instruct',
              'fuser': DATA_ROOT / 'c2c_reproduction_assets/fusers/nics-efc--C2C_Fuser/qwen3_0.6b+qwen2.5_0.5b_Fuser/final'},
    'medium': {'receiver': MED / 'execution_20260915T152640Z/assets/receiver',
               'helper': MED / 'execution_20260915T152640Z/assets/helper',
               'fuser': MED / 'execution_20260915T152640Z/assets/fuser/qwen3_1.7b+qwen2.5_1.5b_Fuser/final'},
    'large': {'receiver': DATA_ROOT / 'hf_cache/hub/models--Qwen--Qwen3-8B/snapshots/b968826d9c46dd6066d109eabc6255188de91218',
              'helper': ROOT / 'P2_6_20260910T164138Z/assets/Qwen2.5-7B-Instruct',
              'fuser': ROOT / 'P2_6_20260910T164138Z/assets/C2C_Fuser/qwen3_8b+qwen2.5_7b_Fuser/final'},
}
CHAINS = {'A': ['large_C', 'small_R'], 'B': ['large_R', 'medium_R', 'medium_C']}
RUNS_DIR = NEW / 'results/e1/official'
CFG_DIR = NEW / 'records/e1_official_configs'
FLAG = NEW / 'results/e1/official/PREFETCH_STATUS.json'


def official_env(kind, gpu):
    env = dict(os.environ)
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    env['PYTHONUNBUFFERED'] = '1'
    env['HF_HOME'] = str(OFFCACHE)
    env['HF_HUB_CACHE'] = str(OFFCACHE / 'hub')
    env['HF_DATASETS_CACHE'] = str(OFFCACHE / 'datasets')
    env['CUDA_VISIBLE_DEVICES'] = str(gpu)
    if kind == 'clean':
        for k in ['HF_HUB_OFFLINE', 'HF_DATASETS_OFFLINE', 'TRANSFORMERS_OFFLINE']:
            env.pop(k, None)
        env['PYTHONPATH'] = str(CLEAN)
        env.pop('C2C_PRESERVE_CUDA_VISIBLE_DEVICES', None)
    else:  # task7 settings
        env.update(HF_HUB_OFFLINE='1', HF_DATASETS_OFFLINE='1', TRANSFORMERS_OFFLINE='1', HF_HUB_DISABLE_XET='1',
                   C2C_PRESERVE_CUDA_VISIBLE_DEVICES='1', PYTHONPATH=str(PATCH))
    return env


def make_config(run, kind, gpu):
    pair, action = run.split('_')
    assert sha(RECIPE) == RECIPE_SHA
    cfg = yaml.safe_load(RECIPE.read_text())
    m = MODELS[pair]
    cfg['model']['rosetta_config']['base_model'] = str(m['receiver'])
    cfg['model']['rosetta_config']['teacher_model'] = str(m['helper'])
    cfg['model']['rosetta_config']['checkpoints_dir'] = str(m['fuser'])
    cfg['model']['model_name'] = 'Rosetta' if action == 'C' else str(m['receiver'])
    cfg['output']['output_dir'] = str(RUNS_DIR / f'{run}__{kind}')
    cfg['eval']['dataset'] = 'openbookqa'
    cfg['eval']['gpu_ids'] = [gpu] if kind == 'clean' else [0]
    if kind == 'patch':
        cfg['eval']['local_openbookqa_parquet'] = str(PARQUET)
    p = CFG_DIR / f'{run}__{kind}.yaml'
    p.parent.mkdir(parents=True, exist_ok=True)
    assert not p.exists()
    p.write_text(yaml.safe_dump(cfg, sort_keys=False))
    return p, pathlib.Path(cfg['output']['output_dir'])


def validate(outdir):
    csvs = sorted(outdir.glob('*_cot.csv'))
    if len(csvs) != 1:
        return False, f'{len(csvs)} cot csv files'
    with open(csvs[0], newline='') as f:
        rows = list(csv.DictReader(f))
    ids = sorted(int(r['question_id']) for r in rows)
    if ids != list(range(500)):
        return False, f'{len(rows)} rows; ids not 0..499'
    if (outdir / 'bad_samples').exists():
        return False, 'bad_samples present'
    return True, str(csvs[0])


def run_one(run, kind, gpu, log):
    ev = (CLEAN if kind == 'clean' else PATCH) / 'script/evaluation/unified_evaluator.py'
    assert sha(ev) == (CLEAN_EVAL_SHA if kind == 'clean' else PATCH_EVAL_SHA)
    cfgp, outdir = make_config(run, kind, gpu)
    remaining = float(os.environ.get('R1_DEADLINE_EPOCH', time.time() + 3 * 3600)) - time.time() - 60
    rec = {'run': run, 'kind': kind, 'evaluator': str(ev), 'evaluator_sha256': sha(ev), 'config': str(cfgp),
           'config_sha256': sha(cfgp), 'gpu': gpu, 'start_utc': utc()}
    if remaining < 300:
        rec.update(status='SKIPPED_DEADLINE')
        return rec
    cwd = NEW / 'logs/official_cwd'
    cwd.mkdir(parents=True, exist_ok=True)
    t = time.time()
    with open(log, 'a') as f:
        f.write(f'\n===== {run} {kind} {utc()} =====\n'); f.flush()
        try:
            proc = subprocess.run([str(PY), str(ev), '--config', str(cfgp)], cwd=cwd, env=official_env(kind, gpu),
                                  stdout=f, stderr=subprocess.STDOUT, timeout=remaining)
            rec['exit_code'] = proc.returncode
        except subprocess.TimeoutExpired:
            rec['exit_code'] = 'TIMEOUT'
    ok, detail = validate(outdir)
    rec.update(end_utc=utc(), seconds=time.time() - t, valid=ok, detail=detail)
    if ok:
        rec['csv_sha256'] = sha(detail)
    return rec


def prefetch():
    code = ('from datasets import load_dataset\nimport json,pyarrow.parquet as pq\n'
            'd=load_dataset("openbookqa")\nt=d["test"]\n'
            f'loc=pq.read_table("{PARQUET}").to_pylist()\n'
            'same=sum(1 for a,b in zip(t,loc) if a["id"]==b["id"] and a["question_stem"]==b["question_stem"] and '
            'list(a["choices"]["text"])==list(b["choices"]["text"]) and list(a["choices"]["label"])==list(b["choices"]["label"]) and a["answerKey"]==b["answerKey"])\n'
            'print(json.dumps({"config":t.config_name,"n":len(t),"rows_identical_in_order_to_local_parquet":same,"fingerprint":t._fingerprint,'
            '"cache_files":[c["filename"] for c in t.cache_files]}))\n')
    env = official_env('clean', '')
    env['CUDA_VISIBLE_DEVICES'] = ''
    t = time.time()
    proc = subprocess.run([str(PY), '-c', code], env=env, capture_output=True, text=True, timeout=900, cwd=NEW / 'logs')
    info = {'utc': utc(), 'seconds': time.time() - t, 'returncode': proc.returncode, 'stderr_tail': proc.stderr[-3000:]}
    try:
        info.update(json.loads(proc.stdout.strip().splitlines()[-1]))
    except Exception:
        info['stdout_tail'] = proc.stdout[-2000:]
    info['clean_usable'] = proc.returncode == 0 and info.get('n') == 500 and info.get('rows_identical_in_order_to_local_parquet') == 500
    save(FLAG, info)
    print(json.dumps(info, indent=1), flush=True)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--prefetch', action='store_true')
    ap.add_argument('--chain', choices=list(CHAINS))
    ap.add_argument('--gpu', type=int)
    a = ap.parse_args()
    if a.prefetch:
        prefetch(); sys.exit(0)
    status = json.loads(FLAG.read_text()) if FLAG.exists() else {'clean_usable': False}
    log = NEW / f'logs/e1_official_eval_gpu{a.gpu}.log'
    manifest = NEW / f'results/e1/official/RUNS_chain{a.chain}.jsonl'
    for run in CHAINS[a.chain]:
        recs = []
        if status.get('clean_usable'):
            recs.append(run_one(run, 'clean', a.gpu, log))
            print(json.dumps(recs[-1]), flush=True)
        else:
            recs.append({'run': run, 'kind': 'clean', 'status': 'NOT_ATTEMPTED_PREFETCH_FAILED', 'prefetch': status})
        if not recs[-1].get('valid'):
            recs.append(run_one(run, 'patch', a.gpu, log))
            print(json.dumps(recs[-1]), flush=True)
        for r in recs:
            append(manifest, r)
    print('E1_OFFICIAL_CHAIN_DONE', a.chain, utc(), flush=True)
