"""E16 Step 0 G2 + G4 (login node, read-only; no gold). -> notes/STEP0_G2_G4.json"""
import sys
sys.dont_write_bytecode = True
import json, glob, hashlib, pathlib, collections
ROOT = pathlib.Path('$DATA_DIR'); X = pathlib.Path(__file__).resolve().parents[1]
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
jl = lambda p: [json.loads(l) for l in open(p) if l.strip()]
from transformers import AutoTokenizer
t7 = AutoTokenizer.from_pretrained(ROOT / 'P2_6_20260910T164138Z/assets/Qwen2.5-7B-Instruct', local_files_only=True)
out = {}
# ---- G2 (a) 744 held-out: E9b large T records
E9 = ROOT / 'P2_R3_E9BC_20260920T061042Z'
ho = json.load(open(E9 / 'inputs/holdout_744_ids.json'))
T = {r['id']: r for f in sorted(glob.glob(str(E9 / 'large/records/e9b_large_shard*.jsonl'))) for r in jl(f) if r['action'] == 'T'}
so = {(r['id'], r['action']): r for r in jl(E9 / 'analysis/SEALED_OUTPUTS.jsonl') if r['pair'] == 'large'}
dec = sum(t7.decode(T[i]['helper_generated_token_ids'], skip_special_tokens=True, clean_up_tokenization_spaces=False) == T[i]['helper_message'] for i in ho if 'helper_generated_token_ids' in T[i])
out['G2_holdout744'] = dict(source='E9BC large/records/e9b_large_shard*.jsonl action T', n_ids=len(ho), with_message=sum(i in T and isinstance(T[i].get('helper_message'), str) and len(T[i]['helper_message']) > 0 for i in ho),
                            has_helper_generated_ids=sum('helper_generated_token_ids' in T[i] for i in ho), decodes_from_saved_ids=dec,
                            T_raw_equals_sealed_output=sum(so[(i, 'T')]['raw_answer'] == T[i]['raw_answer'] for i in ho),
                            sealed_outputs_sha256_matches_seal_receipt=sha(E9 / 'analysis/SEALED_OUTPUTS.jsonl') == json.load(open(E9 / 'analysis/SEAL_RECEIPT.json'))['files']['SEALED_OUTPUTS.jsonl'],
                            shard_sha256={pathlib.Path(f).name: sha(f) for f in sorted(glob.glob(str(E9 / 'large/records/e9b_large_shard*.jsonl')))})
# ---- G2 (b) 1,172 ARC test: sealed run, fixed-Text reference requests
SE = ROOT / 'P2_FINAL_SEALED_ARC_CONFIRMATION_20260914T211958Z'
at = [json.loads(l)['id'] for l in open(SE / 'inputs/test_queries_no_gold.jsonl')]
R = {}
for r in jl(SE / 'records/e2e_requests.jsonl'):
    if r['reference'] == 'T' and r['mode'] == 'reference': assert r['id'] not in R; R[r['id']] = r
sums = dict(l.split()[::-1] for l in open(SE / 'SHA256SUMS') if l.strip())
out['G2_arc_test1172'] = dict(source='SEALED_ARC records/e2e_requests.jsonl reference=T mode=reference', n_ids=len(at), with_message=sum(i in R and isinstance(R[i]['output'].get('helper_message'), str) for i in at),
                              decodes_from_saved_ids=sum(t7.decode(R[i]['output']['helper_generated_token_ids'], skip_special_tokens=True, clean_up_tokenization_spaces=False) == R[i]['output']['helper_message'] for i in at),
                              runtime_failures=sum(bool(R[i].get('runtime_failure')) for i in at),
                              e2e_requests_sha256_matches_SHA256SUMS=sha(SE / 'records/e2e_requests.jsonl') == sums.get('records/e2e_requests.jsonl'))
# ---- G2 (c) fit/cal/dev: X3 hash-check record
out['G2_fit_cal_dev'] = json.load(open(ROOT / 'P2_R6_X3_20260921T052602Z/notes/HELPER_AND_SPLIT_CHECK.json'))['populations']
# ---- G4: fields of stored probe records per receiver x benchmark
files = {'Qwen3-0.6B/obqa+arc (BND small)': glob.glob(str(ROOT / 'P2_CONFIDENCE_REFERENCE_BOUNDARIES_20260914T165012Z/records/small_*_probes.jsonl')),
         'Qwen3-8B/arc (BND large)': glob.glob(str(ROOT / 'P2_CONFIDENCE_REFERENCE_BOUNDARIES_20260914T165012Z/records/large_arc_*_probes.jsonl')),
         'Qwen3-8B/obqa (ZG)': [str(ROOT / 'P2_ZERO_GOLD_CONTROLS_20260914T065145Z/records/probe_records.jsonl')],
         'Qwen3-1.7B/obqa+arc (MED)': glob.glob(str(ROOT / 'P2_MEDIUM_PAIR_BOUNDARY_EXTENSION_STAGE1_20260915T144407Z/execution_retry1_20260915T164957Z/probes/*.jsonl')),
         'Qwen3-8B/mmlu_pro (stage1)': glob.glob(str(ROOT / 'P2_MMLU_PRO_BREADTH_STAGE1_20260916T002337Z/shards/*/probes/*.jsonl'))[:3],
         'Qwen3-0.6B+1.7B/mmlu_pro (E8 merged)': glob.glob(str(ROOT / 'P2_R2_E8_20260920T012544Z/analysis/merged/*_rows.jsonl'))}
g4 = {}
for k, fs in files.items():
    keys = collections.Counter()
    for f in fs:
        with open(f) as fh:
            for n, l in enumerate(fh):
                if n >= 50: break
                keys.update(json.loads(l).keys())
    g4[k] = dict(n_files=len(fs), fields=sorted(keys), logit_like_fields=sorted(x for x in keys if 'logit' in x.lower()))
out['G4_probe_record_fields'] = g4
json.dump(out, open(X / 'notes/STEP0_G2_G4.json', 'w'), indent=1)
print(json.dumps({k: {a: b for a, b in v.items() if a not in ('shard_sha256',)} if isinstance(v, dict) and k != 'G2_fit_cal_dev' and k != 'G4_probe_record_fields' else '...' for k, v in out.items()}, indent=1))
for k, v in g4.items(): print('G4', k, 'n_files', v['n_files'], 'logit fields:', v['logit_like_fields'], '| has p_labels:', 'p_labels' in v['fields'])
