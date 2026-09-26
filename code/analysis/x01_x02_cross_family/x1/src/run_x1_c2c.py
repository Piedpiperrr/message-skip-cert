"""X1 C2C reference via option B: the official evaluator (clean clone 113c3a9 + XFAM local-rows loader + ARC K!=4 label patch,
x1_optionB/unified_evaluator_xfam.py) on our rows. Configuration-only changes to the official recipe unified_eval.yaml:
model_name Rosetta; rosetta_config base_model / teacher_model / checkpoints_dir / is_do_alignment (+ alignment_strategy
'longest', as in the recipe and the X1 fuser config); eval.dataset openbookqa|ai2-arc; eval.gpu_ids; eval.local_rows_jsonl;
output.output_dir. All other recipe keys unchanged (generate, greedy, max_new_tokens 64, use_cot false, use_template true).
The evaluator's per-question CSV (question_id = row index) is mapped back to our ids and parsed with the frozen V2 parser.
Modes: validate (pair small: helper Qwen2.5-0.5B, small fuser 8704f555, no alignment; raw outputs must equal the saved small-pair
       C2C raw outputs; exit 3 on diff), smoke/run (pair x1: helper Llama-3.2-1B, X1 fuser f01fc325, is_do_alignment true).
usage: run_x1_c2c.py --mode {validate,smoke,run} --dataset {obqa,arc} --rows <jsonl> --gpu <physical id> --workdir <dir> --out <jsonl>"""
import sys
sys.dont_write_bytecode = True
import argparse, csv, glob, os, subprocess, time, yaml
from x1_common import *

ap = argparse.ArgumentParser()
ap.add_argument('--mode', required=True, choices=['validate', 'smoke', 'run'])
ap.add_argument('--dataset', required=True, choices=DS1)
ap.add_argument('--rows', required=True); ap.add_argument('--gpu', type=int, required=True)
ap.add_argument('--workdir', required=True); ap.add_argument('--out', required=True)
a = ap.parse_args()
OUT = pathlib.Path(a.out); assert not OUT.exists(), f'refusing to overwrite {OUT}'
W = pathlib.Path(a.workdir); W.mkdir(parents=True, exist_ok=False)
rows = jl(a.rows); assert all(r['dataset'] == a.dataset for r in rows)
parse = parser()
small = a.mode == 'validate'
cfg = yaml.safe_load(open(CLEAN / 'recipe/eval_recipe/unified_eval.yaml'))
rc = cfg['model']['rosetta_config']
cfg['model']['model_name'] = 'Rosetta'
rc['base_model'] = QWEN06['path']
rc['teacher_model'] = SMALL_HELPER['path'] if small else LLAMA['path']
rc['checkpoints_dir'] = SMALL_FUSER if small else X1_FUSER
rc['is_do_alignment'] = (not small)
assert rc['alignment_strategy'] == 'longest'
cfg['output']['output_dir'] = str(W / 'eval_out')
cfg['eval']['dataset'] = {'obqa': 'openbookqa', 'arc': 'ai2-arc'}[a.dataset]
cfg['eval']['gpu_ids'] = [a.gpu]
cfg['eval']['local_rows_jsonl'] = str(pathlib.Path(a.rows).resolve())
cfgp = W / 'eval_config.yaml'; cfgp.write_text(yaml.safe_dump(cfg, sort_keys=False))
jid = (os.environ.get('PBS_JOBID') or 'nojob').split('.')[0]
tmp = f'/tmp/xfam_{jid}_{a.gpu}_{os.getpid()}'; os.makedirs(tmp, exist_ok=True)
env = dict(os.environ, PYTHONPATH=str(CLEAN), TMPDIR=tmp, TMP=tmp, TEMP=tmp, PYTHONDONTWRITEBYTECODE='1', PYTHONUNBUFFERED='1',
           HF_HUB_OFFLINE='1', HF_DATASETS_OFFLINE='1', TRANSFORMERS_OFFLINE='1')
deadline = float(os.environ.get('XFAM_DEADLINE_EPOCH', time.time() + 3 * 3600))
t = time.time()
with open(W / 'evaluator.log', 'w') as f:
    try:
        proc = subprocess.run([str(DATA_ROOT / 'software/envs/c2c_official/bin/python'), str(EVALUATOR), '--config', str(cfgp)], cwd=W, env=env,
                              stdout=f, stderr=subprocess.STDOUT, timeout=max(60, deadline - time.time() - 60))
        rcode = proc.returncode
    except subprocess.TimeoutExpired:
        rcode = 'TIMEOUT'
meta = dict(utc=utc(), mode=a.mode, dataset=a.dataset, rows_file=a.rows, rows_sha256=sha(a.rows), evaluator=str(EVALUATOR), evaluator_sha256=sha(EVALUATOR),
            config=str(cfgp), config_sha256=sha(cfgp), exit_code=rcode, seconds=time.time() - t, gpu=a.gpu, job_id=os.environ.get('PBS_JOBID'), host=os.uname().nodename)
csvs = sorted(glob.glob(str(W / 'eval_out/**/*_cot.csv'), recursive=True))
meta['csv'] = csvs
save(OUT.with_suffix('.env.json'), meta)
assert rcode == 0 and len(csvs) == 1, meta
with open(csvs[0], newline='') as f:
    got = {int(x['question_id']): x for x in csv.DictReader(f)}
assert sorted(got) == list(range(len(rows))), ('question_id coverage', len(got), len(rows))
for i, r in enumerate(rows):
    x = got[i]; q = r['query']
    assert x['question'] == q['question_stem'] and [x[k] for k in 'ABCDEFGHIJ'[:len(q['choice_text'])]] == q['choice_text'], r['id']
    p = parse(x['cot_output'], r['legal_labels'])
    append(OUT, dict(dataset=r['dataset'], split=r['split'], id=r['id'], representative=r['representative'], pair='small' if small else 'x1', runtime_error=None,
                     C=dict(raw=x['cot_output'], parsed=p['answer'] if p['valid'] else 'INVALID', parse_reason=p['reason'], question_id=i,
                            official_pred=x['pred'], official_input_length=x.get('cot_input_length'), official_gen_length=x.get('cot_gen_length'),
                            answer_latency_ms=float(x['answer_latency_ms']) if x.get('answer_latency_ms') else None)))
print('DONE', a.mode, a.dataset, len(rows), 'seconds', round(meta['seconds'], 1), flush=True)
if small:
    lab = {}
    for name in ['full_train', 'full_development']:
        for x in jl(V2L / f'{name}_P2_SCORING_V2.jsonl'):
            if x['pair'] == 'small': lab[(x['dataset'], x['id'])] = x
    res = []
    for o in jl(OUT):
        s = lab[(o['dataset'], o['id'])]['source_C']; saved = rawline(s['source_path'], s['source_line'])
        res.append(dict(dataset=o['dataset'], id=o['id'], C_raw_equal=o['C']['raw'] == saved['raw_answer'], saved_record=f"{s['source_path']}:{s['source_line']}"))
    v = all(c['C_raw_equal'] for c in res) and len(res) == len(rows)
    save(OUT.parent / f'C2C_VALIDATION_{a.dataset}.json', dict(utc=utc(), verdict='PASS' if v else 'FAIL', rows=res))
    print('C2C_VALIDATION', a.dataset, 'PASS' if v else 'FAIL', sum(c['C_raw_equal'] for c in res), '/', len(res), flush=True); sys.exit(0 if v else 3)
