"""构建提交前预算阻塞交付；不导入/加载任何语言模型，不运行题目。"""
import csv
import hashlib
import importlib.util
import json
import math
import shutil
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from transformers import AutoTokenizer, GenerationConfig

P = Path(__file__).resolve().parents[1]
ROOT = P.parent
B = ROOT / 'P2_CONFIDENCE_REFERENCE_BOUNDARIES_20260914T165012Z'
E = ROOT / 'P2_FROZEN_POLICY_E2E_VALIDATION_20260914T174120Z'
N = ROOT / 'P2_10_20260911T122423Z'
STATE = ROOT / 'P2_1_20260910T041720Z/P2_STATE.md'

def utc(): return datetime.now(timezone.utc).isoformat()
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p): return json.loads(Path(p).read_text())
def save(p, v):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(v, indent=2, ensure_ascii=False, allow_nan=False) + '\n')
def csvread(p): return list(csv.DictReader(p.open()))
def csvout(p, rows):
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open('w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
def module(path, name):
    s = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m

assert not (P / 'MEDIUM_PAIR_PROTOCOL_FREEZE.json').exists(), '冻结不可覆盖'
sources = []
def copy(src, rel):
    dest = P / rel; dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, dest)
    assert sha(dest) == sha(src)
    sources.append({'source_path': str(src), 'local_path': rel, 'sha256': sha(src)})

for stage in [B, E, ROOT / 'P2_FINAL_SEALED_ARC_CONFIRMATION_20260914T211958Z']:
    copy(stage / 'HANDOFF_ZH.md', f'evidence/handoffs/{stage.name}.md')
for f in sorted((B / 'splits').iterdir()):
    copy(f, 'splits/' + f.name)
for ds in ['obqa', 'arc']:
    for s in ['train', 'dev']:
        name = f'{ds}_{s}_queries.jsonl'
        copy(B / 'inputs' / name, 'inputs/' + name)
for name in ['panel_cost.csv', 'probe_timing.csv']:
    copy(B / 'summary' / name, 'evidence/historical_throughput/' + name)
copy(B / 'SPLIT_FREEZE.json', 'evidence/parent_SPLIT_FREEZE.json')
copy(B / 'frozen_config.json', 'evidence/parent_boundary_config.json')
copy(E / 'frozen_config.json', 'evidence/parent_native_config.json')
for name in ['runtime.py', 'legacy_methods.py', 'protocol_min.py', 'arc_runtime_adapter.py', 'arc_protocol.py']:
    copy(N / name, 'protocol/native_source/' + name)
copy(B / 'src/receiver_prompt.py', 'protocol/receiver_prompt.py')
copy(B / 'src/run_boundaries.py', 'protocol/parent_run_boundaries.py')
copy(ROOT / 'P2_SCORING_V2_20260912T191445Z/scoring_v2.py', 'protocol/scoring_v2.py')
copy(P.parents[2] / 'c2c_reproduction_assets/official_C2C/README.md', 'evidence/official_C2C_README.md')
save(P / 'SOURCE_INDEX.json', {'sources': sources, 'state_read_only': {'path': str(STATE), 'sha256': sha(STATE)},
    'official_runtime_repo': 'https://github.com/thu-nics/C2C', 'official_runtime_revision': '113c3a9b2538cbf096a0477e1ec99ae2a2e0d12a',
    'ARC_test_content_read': False, 'prior_artifacts_modified': False})

populations = read(P / 'splits/populations.json')
expected = {'obqa': [(2100, 2100), (1366, 1366), (742, 742)], 'arc': [(671, 670), (448, 448), (299, 299)]}
queries = {}
for ds in ['obqa', 'arc']:
    queries[ds] = {}
    for s in ['train', 'dev']:
        for line in (P / f'inputs/{ds}_{s}_queries.jsonl').read_text().splitlines():
            r = json.loads(line)
            assert set(r) == {'id', 'question_stem', 'choice_text', 'choice_labels'}
            assert r['id'] not in queries[ds]
            queries[ds][r['id']] = r
    used = set()
    for s, (n, g) in zip(['fit', 'cal', 'dev'], expected[ds]):
        ids = read(P / f'splits/{ds}_{s}_ids.json')
        reps = read(P / f'splits/{ds}_{s}_representatives.json')
        assert len(ids) == len(set(ids)) == n and len(reps) == len(set(reps)) == g
        assert set(reps) <= set(ids) and not used.intersection(ids)
        used.update(ids)
    assert used == set(queries[ds])
    groups = csvread(P / f'splits/{ds}_group_members.csv')
    assert all(r['representative'] in used for r in groups)
    for r in groups:
        assert r['id'] in read(P / f"splits/{ds}_{r['split']}_ids.json")

index = read(P / 'MODEL_SOURCE_INDEX.json')
prompt = module(P / 'protocol/receiver_prompt.py', 'medium_prompt')
native_config = module(P / 'protocol/native_source/protocol_min.py', 'medium_native_config')
tokens = {}
generation = {}
for role in ['helper', 'receiver']:
    loc = P / 'protocol/models' / role
    tok = AutoTokenizer.from_pretrained(loc, local_files_only=True)
    if tok.pad_token is None: tok.pad_token = tok.eos_token
    tokens[role] = tok
    g = GenerationConfig.from_pretrained(loc, local_files_only=True)
    native_config.apply_generation_config(SimpleNamespace(generation_config=g), {'do_sample': False, 'max_new_tokens': 64})
    generation[role] = g.to_dict()
    (P / f'protocol/{role}_chat_template.jinja').write_text(tok.chat_template)
    index['models'][role]['chat_template_sha256'] = hashlib.sha256(tok.chat_template.encode()).hexdigest()
    index['models'][role]['config'] = read(loc / 'config.json')
save(P / 'MODEL_SOURCE_INDEX.json', index)
tok = tokens['receiver']
label_sets = {l: [] for l in 'ABCDE'}
special = set(tok.all_special_ids)
for v in sorted(set(tok.get_vocab().values())):
    if v not in special:
        label = tok.decode([v], skip_special_tokens=False, clean_up_tokenization_spaces=False).strip()
        if label in label_sets: label_sets[label].append(v)
assert all(label_sets.values())
prefix = 'The correct answer is'
prefix_ids = tok.encode(prefix, add_special_tokens=False)
assert tok.decode(prefix_ids, clean_up_tokenization_spaces=False) == prefix
save(P / 'protocol/label_token_sets.json', label_sets)
save(P / 'protocol/prefix_ids.json', {'literal': prefix, 'ids': prefix_ids})
save(P / 'protocol/generation_configs.json', {'model_generation_config_after_native_cleanup': generation,
      'helper_Text_call_override': {'do_sample': False, 'max_new_tokens': 256}, 'receiver_max_new_tokens': 64})

fdir = P / 'protocol/models/fuser/qwen3_1.7b+qwen2.5_1.5b_Fuser'
fconf = read(fdir / 'config.json')
projector = read(fdir / 'final/projector_0.json')
mapping = read(fdir / 'final/projector_config.json')
assert fconf['model']['base_model'] == index['models']['receiver']['repo_id']
assert fconf['model']['teacher_model'] == index['models']['helper']['repo_id']
pc = projector['init_args']
for role, prefix_name in [('helper', 'source'), ('receiver', 'target')]:
    mc = index['models'][role]['config']
    assert pc[prefix_name + '_dim'] == mc.get('head_dim', mc['hidden_size'] // mc['num_attention_heads'])
    assert pc[prefix_name + '_num_heads'] == mc['num_key_value_heads']
assert set(mapping['0']['1']) == set(map(str, range(28)))
assert all(mapping['0']['1'][str(i)] == [[i, i]] for i in range(28))
save(P / 'evidence/fuser_static_identity.json', {'config': fconf, 'projector': projector,
    'mapping': mapping, 'weight_file_count': len(index['models']['fuser']['checkpoint_files']),
    'model_identity_and_dimensions_static_check': True,
    'strict_runtime_loading_test': '未执行', 'checkpoint_tensors_local_verified': False})

panel = csvread(P / 'evidence/historical_throughput/panel_cost.csv')
probe = csvread(P / 'evidence/historical_throughput/probe_timing.csv')
timings = []
for pair in ['small', 'large']:
    for ds, count in [('obqa', 4208), ('arc', 1418)]:
        def point(policy, ref): return next(r for r in panel if r['pair'] == pair and r['dataset'] == ds and r['policy'] == policy and r['reference'] == ref)
        r_ms = float(point('Fixed_R', 'T')['action_ms'])
        t_ms = float(point('Fixed_reference', 'T')['reference_ms'])
        c_ms = float(point('Fixed_reference', 'C')['reference_ms'])
        p_ms = sum(float(r['sum']) for r in probe if r['pair'] == pair and r['dataset'] == ds and r['component'] in ['probe_core_ms', 'ProbeMax_score_ms']) / count
        timings.append({'historical_pair': pair, 'task': ds, 'medium_question_count': count,
            'R_mean_ms': r_ms, 'Text_mean_ms': t_ms, 'C2C_mean_ms': c_ms, 'ProbeMax_mean_ms': p_ms,
            'projected_wall_seconds': count * (r_ms + t_ms + c_ms + p_ms) / 1000})
csvout(P / 'summary/budget_projection.csv', timings)
scenarios = []
for pair in ['small', 'large']:
    t = sum(r['projected_wall_seconds'] for r in timings if r['historical_pair'] == pair)
    scenarios.append({'historical_pair': pair, 'projected_inference_wall_seconds': t,
        'two_GPU_allocation_hours_without_margin': 2 * t / 3600,
        'margin_fraction': 0.15, 'startup_and_io_reserve_seconds': 300,
        'conservative_wall_seconds': t * 1.15 + 300,
        'conservative_two_GPU_allocation_hours': 2 * (t * 1.15 + 300) / 3600})
assert all(s['two_GPU_allocation_hours_without_margin'] > 4 for s in scenarios)
ledger = {'status': 'BLOCKED_MEDIUM_STAGE1', 'utc': utc(), 'budget_cap_GPU_allocation_hours': 4,
    'planned_GPU_count': 2, 'topology': 'helper cuda:0; receiver/fuser cuda:1; reuse validated residency',
    'maximum_permitted_wall_seconds_at_two_GPUs': 7200, 'one_formal_job_maximum': 1,
    'formal_jobs_submitted': 0, 'submitted_job_ids': [], 'allocated_GPU_hours': 0,
    'requested_GPU_hours': 0, 'formal_action_attempts': 0, 'formal_probe_attempts': 0,
    'mechanical_smoke_forwards': 0, 'retry_count': 0, 'official_weights_downloaded_bytes': 0,
    'planned_questions': 5626, 'planned_actions': 16878, 'planned_probes': 5626,
    'projection_scenarios': scenarios, 'decision': '预算门槛不通过；不提交；停止交回 Work',
    'projection_scope': '既有已曝光 dev128 原生完整动作计时外推到全部 population；ProbeMax 为历史全量逐划分计时；不是 medium 实测或保证',
    'one_GPU_assessment': '未验证：沿用当前双 GPU runtime 驻留；未更改硬编码设备、传输路径或引入新的调度方式以通过预算。此结论不证明单 GPU 实现必然超预算。',
    'new_E2E_or_component_measurements': 0, 'installations': 0,
    'preparation_CPU_seconds': None, 'preparation_CPU_note': '未对交互式准备命令累计计量；不得当成 0',
    'storage_root': str(P.parents[2]), 'checkpoint_local_verification_pending': True,
    'historical_panel_numbers_used_for_submission_estimate_only': True}
save(P / 'RESOURCE_LEDGER.json', ledger)

freeze = {'task': 'P2_MEDIUM_PAIR_BOUNDARY_EXTENSION_STAGE1', 'utc': utc(),
    'freeze_kind': 'SCIENTIFIC_PROTOCOL_AND_OFFICIAL_SOURCE_FREEZE_NOT_EXECUTION_CLEARANCE',
    'execution_ready': False, 'blocking_reason': '既有双 GPU runtime 吞吐估计超过 4 GPU allocation hours；权重尚未下载/本地实测校验，GPU mechanical loading 未进行',
    'MEDIUM_PAIR_OUTCOMES_OBSERVED': False,
    'positioning': 'post-hoc motivated, but protocol-frozen before observing medium-pair outcomes',
    'forbidden_claims': ['preregistered scaling study', 'independent validation', 'sealed confirmation', 'causal model-scale law'],
    'model_source_index': 'MODEL_SOURCE_INDEX.json', 'model_source_index_sha256': sha(P / 'MODEL_SOURCE_INDEX.json'),
    'models': index['models'], 'populations': populations,
    'population_ID_and_query_hashes': {str(f.relative_to(P)): sha(f) for d in ['splits', 'inputs'] for f in sorted((P / d).iterdir())},
    'OBQA_exposure': 'pre-existing exposed project partition；精确 ID/顺序/题目原样复制，无重新抽样或重建',
    'ARC_exposure': '只读既有 train/validation 的 query-only 文件。ARC test 已用于此前 large pair project-sealed confirmation；medium 永远不能产生新 sealed claim。',
    'ARC_test_content_read': False,
    'grouping': '直接继承现有 grouping 文件；空白归一问题/选项签名，最小 id 为组代表。ARC fit671行/670组，只用670代表定阈值；cal448/448；dev299/299。全部原始行仍应生成 R/Text/C2C 与 probe。',
    'actions': ['R', 'Text', 'C2C'],
    'Text_protocol': '原 native t2t_full：helper 用完整题目与选项生成完整 communication message；receiver 接收 user背景请求、assistant完整message、user原题三轮消息；不得截断/改提示词。',
    'C2C_protocol': '官方 pretrained final；helper prefill 使用 receiver tokenizer 与相同指令 token ids；官方28层 fuser及原映射；FP32 projected KV 按原实现插入 BF16 receiver cache；严格加载，不训练或改 projector。',
    'generation': read(P / 'protocol/generation_configs.json'),
    'runtime': {'dtype': 'bfloat16', 'attention': 'sdpa', 'thinking': False, 'TF32': False,
        'batch_size': 1, 'seed': 0, 'mode': 'eval/inference', 'offline': True, 'CPU_threads': 1,
        'residency': ledger['topology'], 'official_code_revision': '113c3a9b2538cbf096a0477e1ec99ae2a2e0d12a'},
    'parser': {'path': 'protocol/scoring_v2.py', 'sha256': sha(P / 'protocol/scoring_v2.py'),
        'version': 'P2_SCORING_V2/2.0.0', 'invalid_answer_symbol': 'INVALID',
        'disagreement': 'parsed symbols differ; INVALID vs INVALID agrees; invalid is incorrect for accuracy; no denominator deletion'},
    'ProbeMax': {'prompt_source': 'protocol/receiver_prompt.py', 'prefix': prefix,
        'prefix_construction': 'native thinking-off generation prefix IDs + separately encoded literal; no trailing space',
        'label_rule': 'all own-tokenizer non-special single tokens whose standalone decode.strip() exactly equals an actual displayed legal label; dynamic K=3/4/5',
        'label_token_sets': label_sets, 'prefix_ids': prefix_ids,
        'probabilities': 'BF16 full backbone, only last valid position lm_head; FP32 label logsumexp then log_softmax.exp; normalize over union of legal labels',
        'score': 'u = float((1 - p.max()).item())', 'no_KV_reuse': True, 'prefill_use_cache': False,
        'invalid_handling': '继承 finite/probability-sum/mass/range assertions；失败保存证据并停止，不能过滤、改分或重采；argmax诊断不替代原生R答案',
        'finiteness_checks': 'all p finite; abs(sum(p)-1)<2e-6; 0<=label_union_mass<=1.00001; 0<=u<=1'},
    'q_grid': [j / 20 for j in range(1, 21)], 'alpha': 0.05, 'p_threshold': 0.001, 'CP_level': 0.999,
    'fit_threshold_rule': 'j=1..19: sorted fit representative u at 1-based ceil(j*N_fit/20); j=20 q=1 fixed R threshold=Infinity',
    'tie_handling': 'route if u<=threshold; keep all exact ties including FP32 zeros; no jitter/ranking tie-break',
    'calibration': 'each reference independent; n routed calibration representatives, k parsed R/reference disagreements; BinomialCDF(k;n,.05); accept p<=.001',
    'CP_upper': 'BetaQuantile(.999;k+1,n-k), n=0 or k=n -> 1; n=0 p=1',
    'selection': 'largest accepted q; none -> q=0 fixed-reference fallback; q=1 fixed R; accuracy never selects thresholds',
    'multiple_testing': {'family': '4 strata x 20 q = 80 tests', 'per_stratum_ideal_Bonferroni_upper_bound': 0.02,
        'extension_ideal_Bonferroni_upper_bound': 0.08, 'selection_unchanged': True, 'historical_100_test_family_combined': False},
    'execution_order': ['fit/cal R/Text/C2C and probe (query-only)', 'fit representative thresholds freeze',
        'calibration 80 tests and four deployments freeze', 'dev outputs and probes', 'dev routes freeze',
        'then associate pre-existing dev gold for accuracy, report every stratum'],
    'analysis_metrics': ['fit/cal/dev representative disagreement prevalence, with all-row diagnostic',
        'dev chosen q/actual threshold/R count/coverage/changed/routed/conditional and marginal disagreement',
        'ProbeMax AUROC and AP of R/reference disagreement; high u predicts disagreement; all rows primary; both-valid diagnostic',
        'score distribution min/p05/median/p95/max/mean/exact-zero count; argmax vs native R; invalid probe count',
        'policy/reference correct counts and accuracies/difference; changed benefit/harm/neutral (sum equals changed)',
        'invalid R/reference/policy/probe counts; per-request raw output, parsed answer, raw helper message, generation token IDs, exact query/input identity, latency/runtime diagnostics'],
    'degenerate_statistics': 'n_R=0 conditional disagreement=null; one-class d AUROC/AP=null; no fabricated zero',
    'reporting_rule': '四层完整执行后，无论0/4到4/4或杂乱模式都必须进入交付；Work只决定main/appendix位置，不决定是否报告。未执行不能记fallback或0/4。',
    'PBS_budget': ledger, 'retry': 'no automatic retry or second submission; facilities failure preserves success IDs and returns PARTIAL to Work',
    'prohibited': ['ARC test', 'E2E replay', 'component cost measurement', 'utility', 'training', 'AC', 'entropy', 'D', 'AgentGate', 'paper/supplement/abstract/figure/table/bibliography modifications'],
    'stop_after_stage1': True}
freeze['frozen_files'] = {str(f.relative_to(P)): sha(f) for directory in ['protocol', 'splits', 'inputs'] for f in sorted((P / directory).rglob('*')) if f.is_file()}
save(P / 'MEDIUM_PAIR_PROTOCOL_FREEZE.json', freeze)
save(P / 'EXECUTION_STATUS.json', {'status': 'BLOCKED_MEDIUM_STAGE1', 'MEDIUM_PAIR_OUTCOMES_OBSERVED': False,
    'MEDIUM_DEPLOY_COUNT': None, 'strata_completed': 0, 'strata_planned': 4,
    'GPU_jobs_submitted': 0, 'Stage2_started': False, 'stop_and_return_to': 'Work'})
for directory in ['actions', 'probes', 'thresholds', 'calibration', 'deployments', 'development']:
    save(P / directory / 'STATUS.json', {'status': 'NOT_EXECUTED', 'reason': '提交前预算门槛未通过',
        'successful_IDs': [], 'outcome_files_generated': 0})
print(json.dumps({'population_rows': sum(x['rows'] for x in populations), 'label_sets': label_sets,
      'protocol_freeze_sha256': sha(P / 'MEDIUM_PAIR_PROTOCOL_FREEZE.json'), 'budget_scenarios': scenarios}, ensure_ascii=False), flush=True)
