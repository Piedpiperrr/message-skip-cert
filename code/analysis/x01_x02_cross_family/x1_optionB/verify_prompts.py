"""X1 option B (prepared, not run): verify the patched official evaluator renders byte-identical receiver prompts to ours for all
4,208 OBQA and 1,418 ARC rows (receiver Qwen3-0.6B; CPU, tokenizers only; no Llama files, no gold).
Official side = unified_evaluator_xfam.py (clean clone 113c3a9 + local-rows loader + ARC K!=4 label patch): _format_* then
prepare_model_inputs(model_type='rosetta', llm_tokenizer=None) as in P2_R1_EXP render_official_prompts.py.
Ours = paper formatters (P2_10 OBQA / arc_runtime_adapter ARC) + apply_chat_template(enable_thinking=False) + tokenizer(rendered)."""
import sys
sys.dont_write_bytecode = True
import json, importlib.util, pathlib, yaml
X = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(X / 'src'))
from xfam_common import *
CLEAN = DATA_ROOT / 'c2c_reproduction_assets/official_C2C'
sys.path.insert(0, str(CLEAN))
import torch
from transformers import AutoTokenizer
spec = importlib.util.spec_from_file_location('ue_xfam', X / 'x1_optionB/unified_evaluator_xfam.py'); ue = importlib.util.module_from_spec(spec); spec.loader.exec_module(ue)
sys.path.insert(0, str(P210)); import protocol_min
FMT = {'obqa': protocol_min.format_openbook}
import arc_runtime_adapter; FMT['arc'] = protocol_min.format_openbook
QWEN06 = DATA_ROOT / 'c2c_reproduction_assets/models/Qwen--Qwen3-0.6B'
res = {}
for ds, dname, fmt in [('obqa', 'openbookqa', '_format_openbookqa_example'), ('arc', 'ai2-arc', '_format_ai2_arc_example')]:
    rows = [r for sp in ['fit', 'cal', 'dev'] for r in jl(POP / f'{ds}_{sp}.jsonl')]
    rf = X / f'x1_optionB/rows_{ds}.jsonl'
    with open(rf, 'w') as f:
        for r in rows: f.write(json.dumps(r, ensure_ascii=False) + '\n')
    cfg = yaml.safe_load(open(CLEAN / 'recipe/eval_recipe/unified_eval.yaml'))
    cfg['model']['model_name'] = 'Rosetta'; cfg['model']['rosetta_config']['base_model'] = str(QWEN06)
    cfg['output']['output_dir'] = str(X / 'cache/x1_optionB_scratch'); cfg['eval']['dataset'] = dname; cfg['eval']['local_rows_jsonl'] = str(rf)
    ev = ue.UnifiedEvaluator(cfg)
    tok = AutoTokenizer.from_pretrained(str(QWEN06)); ue.set_default_chat_template(tok, str(QWEN06))
    data = ue._xfam_local_dataset(str(rf), dname)['test']
    c = dict(n=0, user_message_equal=0, rendered_equal=0, ids_equal=0, K_not_4=0, K_not_4_all_equal=0, first_mismatch=None)
    for ex, r in zip(data, rows):
        assert ex['id'] == r['id']
        prompt = getattr(ev, fmt)(ex, use_cot=cfg['eval']['use_cot'], use_template=cfg['eval']['use_template'])
        prep = ev.prepare_model_inputs(prompt=prompt, tokenizer=tok, device=torch.device('cpu'), model_type='rosetta', llm_tokenizer=None, answer_method=cfg['eval']['answer_method'])
        mine = FMT[ds](r['query'], use_template=True)
        rendered = tok.apply_chat_template([{'role': 'user', 'content': mine}], tokenize=False, add_generation_prompt=True, enable_thinking=False)
        ids = tok(rendered)['input_ids']
        e1, e2, e3 = prompt == mine, prep['printable_text'] == rendered, prep['inputs']['input_ids'][0].tolist() == ids
        c['n'] += 1; c['user_message_equal'] += e1; c['rendered_equal'] += e2; c['ids_equal'] += e3
        if len(r['query']['choice_text']) != 4:
            c['K_not_4'] += 1; c['K_not_4_all_equal'] += (e1 and e2 and e3)
        if not (e1 and e2 and e3) and c['first_mismatch'] is None:
            c['first_mismatch'] = dict(id=r['id'], official=prep['printable_text'][-400:], ours=rendered[-400:])
    res[ds] = c; print(ds, {k: v for k, v in c.items() if k != 'first_mismatch'}, flush=True)
save(X / 'x1_optionB/PROMPT_IDENTITY.json', dict(utc=utc(), evaluator=str(X / 'x1_optionB/unified_evaluator_xfam.py'), evaluator_sha256=sha(X / 'x1_optionB/unified_evaluator_xfam.py'),
                                                  clean_clone_commit='113c3a9b2538cbf096a0477e1ec99ae2a2e0d12a', receiver_tokenizer=str(QWEN06), results=res,
                                                  scope='receiver-side prompt only; the Llama-side aligned input needs the (gated) Llama tokenizer'))
