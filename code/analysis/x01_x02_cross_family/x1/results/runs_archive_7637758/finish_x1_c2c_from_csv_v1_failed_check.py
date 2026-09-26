"""X1 C2C post-processing from an existing official-evaluator CSV (CPU, receiver tokenizer only; no model, no gold). DEVIATIONS C15.
Same record construction as run_x1_c2c.py lines 58-68; only the CSV->row mapping check differs: the official ai2-arc CSV writer
logs choices A-D only, so for K=5 rows columns E.. are empty. Check used here, per row: question equal; choices 1..min(K,4) equal;
CSV choice columns beyond them empty; and CSV cot_input_length (= Rosetta receiver input_ids length) equal to the token count of our
rendered receiver prompt (ids byte-identical per PROMPT_IDENTITY_v2), which for K=5 rows shows the fifth choice was in the prompt.
usage: finish_x1_c2c_from_csv.py --dataset {obqa,arc} --rows <jsonl> --env <c2c_chain_XX.env.json> --out <jsonl> [--partial <jsonl>]"""
import sys
sys.dont_write_bytecode = True
import argparse, csv
from x1_common import *
from transformers import AutoTokenizer
sys.path.insert(0, str(P210)); import protocol_min
FMT = {'obqa': protocol_min.format_openbook}
import arc_runtime_adapter; FMT['arc'] = protocol_min.format_openbook

ap = argparse.ArgumentParser()
ap.add_argument('--dataset', required=True, choices=DS1); ap.add_argument('--rows', required=True)
ap.add_argument('--env', required=True); ap.add_argument('--out', required=True); ap.add_argument('--partial')
a = ap.parse_args()
OUT = pathlib.Path(a.out); assert not OUT.exists(), f'refusing to overwrite {OUT}'
rows = jl(a.rows); assert all(r['dataset'] == a.dataset for r in rows)
meta = read(a.env)
assert meta['exit_code'] == 0 and len(meta['csv']) == 1 and meta['mode'] == 'run' and meta['dataset'] == a.dataset, meta
assert meta['rows_sha256'] == sha(a.rows) and meta['evaluator_sha256'] == sha(EVALUATOR), 'rows or evaluator changed since the run'
parse = parser()
tq = AutoTokenizer.from_pretrained(QWEN06['path'], local_files_only=True)
with open(meta['csv'][0], newline='') as f:
    got = {int(x['question_id']): x for x in csv.DictReader(f)}
assert sorted(got) == list(range(len(rows))), ('question_id coverage', len(got), len(rows))
chk = dict(n=0, question_equal=0, logged_choices_equal=0, unlogged_columns_empty=0, input_length_equal=0, K_gt_4=[])
for i, r in enumerate(rows):
    x = got[i]; q = r['query']; K = len(q['choice_text']); L = 'ABCDEFGHIJ'
    rendered = tq.apply_chat_template([{'role': 'user', 'content': FMT[a.dataset](q, use_template=True)}], tokenize=False, add_generation_prompt=True, enable_thinking=False)
    c = [x['question'] == q['question_stem'], [x[k] for k in L[:min(K, 4)]] == q['choice_text'][:4], all(x[k] == '' for k in L[min(K, 4):]),
         int(x['cot_input_length']) == len(tq(rendered)['input_ids'])]
    chk['n'] += 1
    for name, ok in zip(['question_equal', 'logged_choices_equal', 'unlogged_columns_empty', 'input_length_equal'], c): chk[name] += ok
    if K > 4: chk['K_gt_4'].append(dict(id=r['id'], K=K, csv_input_length=int(x['cot_input_length']), ours=len(tq(rendered)['input_ids']), all_checks=all(c)))
    assert all(c), (r['id'], c)
for i, r in enumerate(rows):
    x = got[i]; p = parse(x['cot_output'], r['legal_labels'])
    append(OUT, dict(dataset=r['dataset'], split=r['split'], id=r['id'], representative=r['representative'], pair='x1', runtime_error=None,
                     C=dict(raw=x['cot_output'], parsed=p['answer'] if p['valid'] else 'INVALID', parse_reason=p['reason'], question_id=i,
                            official_pred=x['pred'], official_input_length=x.get('cot_input_length'), official_gen_length=x.get('cot_gen_length'),
                            answer_latency_ms=float(x['answer_latency_ms']) if x.get('answer_latency_ms') else None)))
if a.partial:
    old, new = jl(a.partial), jl(OUT)
    chk['partial_rows'] = len(old); chk['partial_prefix_identical'] = old == new[:len(old)]
    assert chk['partial_prefix_identical']
save(OUT.with_suffix('.finish.json'), dict(utc=utc(), script=__file__, script_sha256=sha(__file__), csv=meta['csv'][0], csv_sha256=sha(meta['csv'][0]),
                                           env=a.env, rows=a.rows, out=str(OUT), out_sha256=sha(OUT), checks=chk))
print('FINISH', a.dataset, len(rows), json.dumps(chk), flush=True)
