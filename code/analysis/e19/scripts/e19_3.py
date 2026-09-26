"""E19-3: panel representativeness (panel vs full development population) and the Eq. 4 saving with panel vs full coverage.
Bindings as PREREG_E19.md (E19-3). Tokenizers only (local files, no weights)."""
from e19_common import *
import importlib.util, hashlib
from transformers import AutoTokenizer

T0 = utc()
print('E19-3 start', T0)
EAG = Path('$DATA_DIR')
TOK = {'Qwen3-8B': str(EAG / 'hf_cache/hub/models--Qwen--Qwen3-8B/snapshots/b968826d9c46dd6066d109eabc6255188de91218'),
       'Qwen3-1.7B': str(ROOT / 'P2_MEDIUM_PAIR_E2E_STAGE2_20260915T205303Z/assets/receiver'),
       'Llama-3.1-8B': str(EAG / 'hf_cache/hub/models--meta-llama--Llama-3.1-8B-Instruct/snapshots/0e9e39f249a16976918f6564b8830bc894c89659'),
       'Qwen2.5-7B': str(ROOT / 'P2_6_20260910T164138Z/assets/Qwen2.5-7B-Instruct')}
TK = {k: AutoTokenizer.from_pretrained(v, local_files_only=True) for k, v in TOK.items()}
spec = importlib.util.spec_from_file_location('rp19', ROOT / 'P2_R1_EXP_20260919T050555Z/src/receiver_prompt.py')
RP = importlib.util.module_from_spec(spec); spec.loader.exec_module(RP)
RAWIO = sys.modules['rawio']
BND = ROOT / 'P2_CONFIDENCE_REFERENCE_BOUNDARIES_20260914T165012Z'
E6 = ROOT / 'P2_R2_GPU_20260919T220941Z/e6'


def ntok(tk, s): return len(TK[tk](s or '', add_special_tokens=False)['input_ids'])


# question texts (no gold)
Q = {}
for ds in ['obqa', 'arc']:
    for sp in ['train', 'dev']:
        for r in jl(BND / f'inputs/{ds}_{sp}_queries.jsonl'):
            Q[ds, r['id']] = r
for (i, a), r in RAWIO._mmlu('dev').items():
    if a == 'R': Q['mmlu_pro', i] = r['query']


def qblock(ds, i):
    q = Q[ds, i]
    return q['question_stem'] + '\n\nChoices:\n' + RP.choices_block(q['choice_text'])


E6H = {}
for f in sorted((E6 / 'main').glob('e6_shard*.jsonl')):
    for r in jl(f):
        E6H[r['id'], r['split']] = r['helper_message']


def helper_msgs(key, ds, ids):
    s, q = POLD[key]
    if key == 'large/OBQA/Text+fact':
        return [E6H[i, 'dev'] for i in ids]
    if s[1] == 'MMLU-Pro':
        M = RAWIO._mmlu('dev')
        return [M[i, 'T']['output']['helper_message'] for i in ids]
    lab = RAWIO._v2labels('large', ds)
    out = []
    for i in ids:
        src = lab[i]['source_T']
        x = RAWIO._rawfile(src['source_path'])[src['source_line']]
        assert str(x['id']) == str(i) and x['action'] == 'text'
        out.append(x['helper_message'])
    return out


PANEL_SETS = {}
CHK, ROWS, LAT, EQ4 = [], [], [], []
DS = {'OBQA': 'obqa', 'ARC': 'arc', 'MMLU-Pro': 'mmlu_pro'}
for key in QWEN9 + ['Llama-3.1-8B/OBQA/Text', 'Llama-3.1-8B/ARC/Text']:
    s, q = POLD[key]
    ds = DS[s[1]]
    D = dev(key)
    ids = D['ids']
    R = replay(key)
    pids = R['ids']
    pos = {i: j for j, i in enumerate(ids)}
    miss = [i for i in pids if i not in pos]
    CHK.append(dict(check=f'{key}: panel ids subset of dev population', expected=0, observed=len(miss)))
    inP = np.zeros(len(ids), bool); inP[[pos[i] for i in pids if i in pos]] = True
    rtk = 'Llama-3.1-8B' if key.startswith('Llama') else ('Qwen3-1.7B' if s[0] == 'medium' else 'Qwen3-8B')
    var = {}
    var['question_len_tokens'] = np.array([ntok(rtk, qblock(ds, i)) for i in ids], float)
    if key.startswith('Llama'):
        X = E17._x3load(ds)['dev']
        assert list(X['ids']) == ids
        rawR, rawB = X['rawR'], X['rawb']
        hm = helper_msgs('large/OBQA/Text' if ds == 'obqa' else 'large/ARC/Text', ds, ids)
        # the Llama Text path read the large helper's stored messages: check the X3 record hash
        x3rec = {}
        import glob
        for f in sorted(glob.glob(str(X3 / 'results/runs/chain_*.jsonl'))):
            for r in jl(f):
                if r['dataset'] == ds: x3rec[r['id']] = r
        bad = sum(hashlib.sha256(m.encode('utf-8')).hexdigest() != x3rec[i]['T']['helper_message_sha256'] for i, m in zip(ids, hm))
        CHK.append(dict(check=f'{key}: large-pair helper message sha256 == X3 T.helper_message_sha256 (dev)', expected=0, observed=int(bad)))
        var['helper_msg_len_tokens'] = np.array([ntok('Qwen2.5-7B', m) for m in hm], float)
    else:
        raw, _ = C.raw(s, 'dev', ids)
        rawR, rawB = raw['R'], raw[s[2]]
        if s[2] in ('Text', 'Text+fact'):
            var['helper_msg_len_tokens'] = np.array([ntok('Qwen2.5-7B', m) for m in helper_msgs(key, ds, ids)], float)
    var['R_output_len_tokens'] = np.array([ntok(rtk, t) for t in rawR], float)
    var['ref_output_len_tokens'] = np.array([ntok(rtk, t) for t in rawB], float)
    var['u_eq_0'] = (D['u'] == 0.0).astype(float)
    var['coverage_omitted'] = D['m'].astype(float)
    for vn, x in var.items():
        full, pan = x, x[inP]
        sd = full.std(ddof=0)
        ROWS.append(dict(policy=key, variable=vn, tokenizer=(rtk if vn in ('question_len_tokens', 'R_output_len_tokens', 'ref_output_len_tokens')
                                                             else 'Qwen2.5-7B' if vn == 'helper_msg_len_tokens' else ''),
                         N_full=len(full), N_panel=len(pan), mean_full=full.mean(), mean_panel=pan.mean(),
                         median_full=float(np.median(full)), median_panel=float(np.median(pan)), SD_full=sd,
                         diff_panel_minus_full=pan.mean() - full.mean(),
                         SMD=((pan.mean() - full.mean()) / sd if sd > 0 else float('nan')),
                         diff_points=(100 * (pan.mean() - full.mean()) if vn in ('u_eq_0', 'coverage_omitted') else ''),
                         length_variable=vn.endswith('_tokens'), label=LABEL))
    # Eq. 4 with the panel replay's components
    fx, po = R['fx'], R['po']
    om = np.array([route_R(po[i]) for i in pids])
    cb = np.array([fx[i]['latency_ms'] for i in pids]); pl = np.array([po[i]['latency_ms'] for i in pids])
    pr = np.array([probe_ms(po[i]) for i in pids])
    gap = float((cb - (pl - pr))[om].mean())
    cs = float(pr.mean())
    k_i, k_ii = float(om.mean()), float(D['m'].mean())
    EQ4.append(dict(policy=key, configuration=R['config'], replay_panel_coverage=k_i, dev_panel_coverage_stored_u=float(D['m'][inP].mean()),
                    full_dev_coverage=k_ii, mean_gap_cb_minus_cR_on_omitted_ms=gap, mean_probe_cs_ms=cs,
                    eq4_saving_panel_coverage_ms=k_i * gap - cs, eq4_saving_full_coverage_ms=k_ii * gap - cs,
                    eq4_diff_full_minus_panel_ms=(k_ii - k_i) * gap, measured_net_saving_ms=float((cb - pl).mean()),
                    source=R['source'], label=LABEL))
    PANEL_SETS[key] = pids

# latency comparison: panel rows inside the full MMLU-Pro C2C run vs all rows of that run
FR = replay_full_mmlu_c2c()
pids = PANEL_SETS['large/MMLU-Pro/C2C']
CHK.append(dict(check='MMLU-Pro panel ids inside the full 2,641 run', expected=128, observed=sum(i in FR['fx'] for i in pids)))
for grp, gids in [('panel (128) inside full run', pids), ('full run (2,641)', FR['ids'])]:
    f = np.array([FR['fx'][i]['latency_ms'] for i in gids]); p = np.array([FR['po'][i]['latency_ms'] for i in gids])
    om = np.array([route_R(FR['po'][i]) for i in gids])
    LAT.append(dict(policy='large/MMLU-Pro/C2C', run=FR['source'], group=grp, N=len(gids), mean_fixed_ms=f.mean(), mean_policy_ms=p.mean(),
                    mean_saving_ms=(f - p).mean(), median_saving_ms=float(np.median(f - p)), median_fixed_ms=float(np.median(f)),
                    median_policy_ms=float(np.median(p)), coverage_in_run=om.mean(), label=LABEL))
fullsd = np.array([FR['fx'][i]['latency_ms'] - FR['po'][i]['latency_ms'] for i in FR['ids']]).std(ddof=0)
LAT.append(dict(policy='large/MMLU-Pro/C2C', group='SMD of saving (panel - full) / SD_full', N='',
                mean_saving_ms=(LAT[0]['mean_saving_ms'] - LAT[1]['mean_saving_ms']) / fullsd, label=LABEL))
for c in CHK:
    c['status'] = 'PASS' if c['expected'] == c['observed'] else 'FAIL'; print(c)
assert all(c['status'] == 'PASS' for c in CHK)

# writing rule
trig = []
for r in ROWS:
    if r['variable'] == 'coverage_omitted' and abs(r['diff_points']) > 10: trig.append(f"{r['policy']} coverage {r['diff_points']:+.1f} pts")
    if r['length_variable'] and abs(r['SMD']) > .2: trig.append(f"{r['policy']} {r['variable']} SMD {r['SMD']:+.3f}")
rule = dict(triggered=bool(trig), triggers=';'.join(trig) or 'none',
            max_abs_SMD_length=max(abs(r['SMD']) for r in ROWS if r['length_variable']),
            max_abs_coverage_diff_points=max(abs(r['diff_points']) for r in ROWS if r['variable'] == 'coverage_omitted'), label=LABEL)
print(rule)
for r in ROWS:
    print(f"{r['policy']:24s} {r['variable']:24s} full {r['mean_full']:.3f} (med {r['median_full']:.1f}) panel {r['mean_panel']:.3f} (med {r['median_panel']:.1f}) SMD {r['SMD']:+.3f}")
for r in EQ4: print(r)
for r in LAT: print(r)
csvout('E19_3_panel_vs_full.csv', ROWS)
csvout('E19_3_eq4.csv', EQ4)
csvout('E19_3_latency_full_mmlu_c2c.csv', LAT)
csvout('E19_3_checks.csv', CHK)
csvout('E19_3_writing_rule.csv', [rule])
json.dump(dict(start_utc=T0, end_utc=utc(), tokenizers=TOK, files_read=READ), open(STAGE / 'logs/e19_3_run.json', 'w'), indent=1)
print('E19-3 done', utc())
