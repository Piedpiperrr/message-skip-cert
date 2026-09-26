"""E21B checks and statistics (PREREG.md). No gold label is read anywhere in this file.

  select    choose preflight rows (P1: 16 per population; P2 extra: sealed-ARC K!=4 / non-letter labels)
  gate      evaluate preflight P1/P2/P3 on the job's preflight outputs; exit 0 = PASS, 3 = STOP
  manifest  every question x arm exactly once; last output timestamp (recorded before any statistic)
  stats     PREREG primary + secondary statistics, CSVs, writing-rule branch
"""
import sys, os, json, csv, hashlib, ast, datetime, collections
from pathlib import Path
sys.dont_write_bytecode = True
E21 = Path(__file__).resolve().parents[1]
ROOT = E21.parent
SEALED = ROOT / 'P2_FINAL_SEALED_ARC_CONFIRMATION_20260914T211958Z'
E9B = ROOT / 'P2_R3_E9BC_20260920T061042Z'
E4 = ROOT / 'P2_R1_EXP_20260919T050555Z/src/prepare_populations.py'
E4_SHA = 'f4941cf4f4efd5d7face281c63586b587037d5102b953538269c890c68b1213f'
STAGE = E21 / 'large_s0'
ACTS = {'arc': ['probe', 'R', 'T', 'C'], 'obqa': ['probe', 'R', 'T', 'C', 'TF']}
N_EXP = {'arc': 1172, 'obqa': 744}
# policy, population, reference arm, q, tau (stored), stored original-format k/n quoted in the PREREG
POLICIES = [
    ('large/ARC/Text', 'arc', 'T', 0.95, 0.01800704002380371, 20, 1100),
    ('large/ARC/C2C', 'arc', 'C', 0.90, 0.0007095932960510254, 11, 1047),
    ('large/OBQA/Text', 'obqa', 'T', 0.80, 0.001170039176940918, 12, 595),
    ('large/OBQA/C2C', 'obqa', 'C', 0.80, 0.001170039176940918, 13, 595),
    ('large/OBQA/Text+fact', 'obqa', 'TF', 0.75, 0.0002611875534057617, 16, 558),
]
DEADLINE_UTC = '2026-09-22T23:00:00+00:00'  # 2026-09-22 18:00 CDT
INV = 'INVALID'


def utc():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def jl(p):
    with open(p) as f:
        return [json.loads(s) for s in f if s.strip()]


def save(p, v):
    p = Path(p); p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(v, indent=2, ensure_ascii=False) + '\n')


def csvout(p, rows):
    rows = list(rows)
    with open(p, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(dict.fromkeys(k for r in rows for k in r)))
        w.writeheader(); w.writerows(rows)


def v1_rotate():
    assert sha(E4) == E4_SHA
    ns = {}
    tree = ast.parse(E4.read_text())
    exec(compile(ast.Module([n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in ('labels', 'rotate')], []),
                 str(E4), 'exec'), ns)
    return ns['rotate']


def identity(q):
    return dict(q), {l: l for l in q['choice_labels']}


def Q(row):
    return {k: row[k] for k in ['question_stem', 'choice_labels', 'choice_text']}


def population(pop):
    if pop == 'arc':
        rows = jl(SEALED / 'inputs/test_queries_no_gold.jsonl')
    else:
        rows = jl(E9B / 'inputs/holdout_744_queries.jsonl')
    assert len(rows) == N_EXP[pop] and len({r['id'] for r in rows}) == N_EXP[pop]
    return rows


def ans_of(parsed):
    return parsed['answer'] if parsed['valid'] else INV


def stored(pop):
    """Stored original-format outputs per id: u, probe sha, and per arm raw/ids/answer/input counts."""
    out = {}
    if pop == 'arc':
        rr = {}
        for r in jl(SEALED / 'records/e2e_requests.jsonl'):
            k = (r['id'], r['mode'], r['reference']); assert k not in rr; rr[k] = r
        ids = {r['id'] for r in population('arc')}
        for i in ids:
            pT, pC, rT, rC = rr[i, 'policy', 'T'], rr[i, 'policy', 'C'], rr[i, 'reference', 'T'], rr[i, 'reference', 'C']
            assert pT['probe']['ProbeMax'] == pC['probe']['ProbeMax']
            d = {'u': pT['probe']['ProbeMax'], 'sha': pT['probe']['probe_ids_sha256']}
            for arm, rec in [('T', rT), ('C', rC)] + [('R', x) for x in (pT, pC) if x['selected'] == 'R'][:1]:
                o = rec['output']
                d[arm] = {'raw': o['raw_answer'], 'ids': o['generated_token_ids'], 'ans': ans_of(rec['parsed']),
                          'rin': o.get('receiver_input_tokens'), 'hin': o.get('helper_input_tokens'),
                          'hmsg': o.get('helper_message'), 'hids': o.get('helper_generated_token_ids')}
            out[i] = d
    else:
        by = {}
        for s in range(3):
            for r in jl(E9B / f'large/records/e9b_large_shard{s}.jsonl'):
                k = (r['id'], r['action']); assert k not in by; by[k] = r
        for r in population('obqa'):
            i = r['id']; p = by[i, 'probe']
            d = {'u': p['ProbeMax'], 'sha': p['probe_ids_sha256']}
            for arm in ['R', 'T', 'C', 'TF']:
                o = by[i, arm]
                d[arm] = {'raw': o['raw_answer'], 'ids': o['generated_token_ids'], 'ans': o['answer'],
                          'rin': o.get('receiver_input_tokens'), 'hin': o.get('helper_input_tokens'),
                          'hmsg': o.get('helper_message'), 'hids': None}
            out[i] = d
    return out


def new_records(paths, transform):
    by = {}
    dup = []
    for p in paths:
        if not Path(p).exists():
            continue
        for r in jl(p):
            if r.get('transform') != transform:
                continue
            k = (r['id'], r['action'])
            if k in by:
                dup.append(k)
            by[k] = r
    return by, dup


def first_diff(a, b):
    a, b = list(a or []), list(b or [])
    for j, (x, y) in enumerate(zip(a, b)):
        if x != y:
            return j
    return None if len(a) == len(b) else min(len(a), len(b))


# ------------------------------------------------------------------ select
def cmd_select():
    s = stored('arc')
    arc = population('arc')
    p1_arc = [r['id'] for r in arc if 'R' in s[r['id']]][:16]
    p1_obqa = [r['id'] for r in population('obqa')][:16]
    extra = [r['id'] for r in arc if len(r['choice_text']) != 4
             or list(r['original_choice_labels']) != [chr(65 + j) for j in range(len(r['choice_text']))]]
    sel = {'utc': utc(), 'P1_P3_rows': {'arc': p1_arc, 'obqa': p1_obqa}, 'P2_extra_arc': extra,
           'rule': {'arc': 'first 16 sealed ARC questions in ordinal order that have a stored R output',
                    'obqa': 'first 16 held-out OBQA questions in population order',
                    'P2_extra_arc': 'every sealed ARC question with K != 4 or original labels other than A..'},
           'counts': {'extra_K_not_4': sum(len(r['choice_text']) != 4 for r in arc),
                      'extra_nonletter': sum(list(r['original_choice_labels']) != [chr(65 + j) for j in range(len(r['choice_text']))] for r in arc),
                      'extra_total': len(extra)}}
    save(E21 / 'preflight/ROWS.json', sel)
    for pop in ['arc', 'obqa']:
        (E21 / f'preflight/ids_{pop}.json').write_text(json.dumps(sel['P1_P3_rows'][pop]) + '\n')
    print(json.dumps(sel['counts']), len(p1_arc), len(p1_obqa))


# ------------------------------------------------------------------ frozen builders on CPU
class Builders:
    def __init__(self):
        cfg = json.loads((STAGE / 'frozen_config.json').read_text())
        sys.path.insert(0, cfg['native_root'])
        import runtime as native  # noqa: F401  (same import order as native_adapter)
        import arc_runtime_adapter  # noqa: F401
        import protocol_min
        sys.path.remove(cfg['native_root'])
        sys.path.insert(0, str(STAGE / 'src'))
        import receiver_prompt as RP
        from transformers import AutoTokenizer
        self.lm, self.pm, self.RP = native.lm, protocol_min, RP
        m = cfg['native']['models']
        self.rtok = AutoTokenizer.from_pretrained(m['receiver']['path'], local_files_only=True)
        self.htok = AutoTokenizer.from_pretrained(m['helper']['path'], local_files_only=True)
        self.prefix = json.loads((STAGE / 'protocol/prefix_ids.json').read_text())['ids']
        assert self.rtok.encode(cfg['prefix'], add_special_tokens=False) == self.prefix

    def probe_ids(self, q):
        body = self.RP.receiver_prompt(q)
        rendered = self.rtok.apply_chat_template([{'role': 'user', 'content': body}], tokenize=False,
                                                 add_generation_prompt=True, enable_thinking=False)
        return self.rtok(rendered)['input_ids'] + self.prefix

    def probe_sha(self, q):
        import numpy as np
        return hashlib.sha256(np.array([self.probe_ids(q)], dtype=np.int64).tobytes()).hexdigest()

    def receiver_only_ids(self, q):
        _, _, t = self.pm.receiver_prompt_tensors(self.rtok, q, 'cpu')
        return t['input_ids'][0].tolist()

    def helper_body(self, q):
        return self.lm.format_openbook(q, use_template=False)

    def helper_ids(self, q, fact=None):
        body = self.helper_body(q)
        if fact is not None:
            body = 'Useful fact: ' + fact + '\n' + body
        prompt = self.lm.BACKGROUND_PROMPT.format(question=body)
        return self.htok.apply_chat_template([{'role': 'user', 'content': prompt}], tokenize=True,
                                             add_generation_prompt=True, enable_thinking=False), prompt

    def receiver_body(self, q):
        return self.lm.format_openbook(q, use_template=True)


def block(labels, texts):
    return ''.join(f'{l}. {t}\n' for l, t in zip(labels, texts))


# ------------------------------------------------------------------ gate
def cmd_gate():
    sel = json.loads((E21 / 'preflight/ROWS.json').read_text())
    rotate = v1_rotate()
    B = Builders()
    facts = json.loads((E9B / 'inputs/obqa_fact1.json').read_text())
    rep = {'utc': utc(), 'P1': {}, 'P2': {}, 'P3': {}, 'stop_reasons': []}
    stop = rep['stop_reasons']
    for pop in ['arc', 'obqa']:
        ids = sel['P1_P3_rows'][pop]
        rows = {r['id']: r for r in population(pop)}
        st = stored(pop)
        # ---------------- P1 identity rotation vs stored outputs and frozen builders
        new, dup = new_records([E21 / f'preflight/p1_{pop}.jsonl'], 'identity')
        p1 = {'rows': len(ids), 'duplicates': len(dup), 'missing': [], 'hard': collections.Counter(),
              'identical': collections.Counter(), 'mismatches': [], 'u_absdiff_max': 0.0, 'u_bitwise': 0}
        arms_soft = ['T_helper', 'T', 'C'] + (['TF_helper', 'TF'] if pop == 'obqa' else [])
        for i in ids:
            q = Q(rows[i]); qi, back = identity(q); s = st[i]
            fact = facts[i] if pop == 'obqa' else None
            miss = [a for a in ACTS[pop] if (i, a) not in new]
            if miss:
                p1['missing'].append({'id': i, 'arms': miss}); continue
            # prompt token IDs from the frozen builders: original q vs the wrapper's q, and vs stored/new probe input
            cpu_sha = B.probe_sha(q)
            checks = {
                'probe_ids_builder_orig_eq_wrapper': B.probe_ids(q) == B.probe_ids(qi),
                'receiver_only_ids_orig_eq_wrapper': B.receiver_only_ids(q) == B.receiver_only_ids(qi),
                'helper_ids_orig_eq_wrapper': B.helper_ids(q)[0] == B.helper_ids(qi)[0],
                'probe_sha_new_eq_stored': new[i, 'probe']['probe_ids_sha256'] == s['sha'],
                'probe_sha_builder_eq_stored': cpu_sha == s['sha'],
                'R_rin_eq_stored_and_builder': new[i, 'R']['receiver_input_tokens'] == s['R']['rin'] == len(B.receiver_only_ids(q)),
                'C_rin_eq_stored': new[i, 'C']['receiver_input_tokens'] == s['C']['rin'],
                'C_hin_eq_stored': new[i, 'C']['helper_input_tokens'] == s['C']['hin'],
                'T_hin_eq_stored_and_builder': new[i, 'T']['helper_input_tokens'] == s['T']['hin'] == len(B.helper_ids(q)[0]),
            }
            if pop == 'obqa':
                checks['TF_helper_ids_orig_eq_wrapper'] = B.helper_ids(q, fact)[0] == B.helper_ids(qi, fact)[0]
                checks['TF_hin_eq_stored_and_builder'] = new[i, 'TF']['helper_input_tokens'] == s['TF']['hin'] == len(B.helper_ids(q, fact)[0])
            du = abs(new[i, 'probe']['ProbeMax'] - s['u'])
            p1['u_absdiff_max'] = max(p1['u_absdiff_max'], du)
            p1['u_bitwise'] += new[i, 'probe']['ProbeMax'] == s['u']
            checks['u_within_1e-6'] = du <= 1e-6
            checks['R_byte_identical'] = (new[i, 'R']['raw_answer'] == s['R']['raw'] and list(new[i, 'R']['generated_token_ids']) == list(s['R']['ids']))
            for k, ok in checks.items():
                if not ok:
                    p1['hard'][k] += 1
                    p1['mismatches'].append({'id': i, 'check': k})
            if not checks['R_byte_identical']:
                p1['mismatches'][-1]['first_differing_token'] = first_diff(new[i, 'R']['generated_token_ids'], s['R']['ids'])
            for arm in arms_soft:
                base = arm.split('_')[0]
                n, o = new[i, base], s[base]
                if arm.endswith('_helper'):
                    ok = n['helper_message'] == o['hmsg']
                    if not ok:
                        a_ids = n.get('helper_generated_token_ids') if o['hids'] is not None else B.htok.encode(n['helper_message'] or '', add_special_tokens=False)
                        b_ids = o['hids'] if o['hids'] is not None else B.htok.encode(o['hmsg'] or '', add_special_tokens=False)
                        p1['mismatches'].append({'id': i, 'arm': arm, 'first_differing_token': first_diff(a_ids, b_ids),
                                                 'token_basis': 'generated ids' if o['hids'] is not None else 'helper-tokenized messages'})
                else:
                    ok = n['raw_answer'] == o['raw'] and list(n['generated_token_ids']) == list(o['ids'])
                    if not ok:
                        p1['mismatches'].append({'id': i, 'arm': arm, 'first_differing_token': first_diff(n['generated_token_ids'], o['ids']),
                                                 'new_raw': n['raw_answer'], 'stored_raw': o['raw']})
                p1['identical'][arm] += ok
        p1['hard'] = dict(p1['hard']); p1['identical'] = dict(p1['identical'])
        if p1['missing'] or p1['duplicates']:
            stop.append(f'P1 {pop}: missing {len(p1["missing"])} rows / duplicates {p1["duplicates"]}')
        for k, v in p1['hard'].items():
            stop.append(f'P1 {pop}: {k} failed on {v}/16 rows')
        for arm in arms_soft:
            if p1['identical'].get(arm, 0) < 15:
                stop.append(f'P1 {pop}: {arm} identical on {p1["identical"].get(arm, 0)}/16 (< 15)')
        rep['P1'][pop] = p1
        # ---------------- P2 rotation check (P1 rows + sealed-ARC K!=4 / non-letter labels); P3 rows' real prompts
        new3, dup3 = new_records([E21 / f'preflight/p3_{pop}.jsonl'], 'v1')
        p2rows = ids + ([x for x in sel['P2_extra_arc'] if x not in ids] if pop == 'arc' else [])
        p2 = {'rows': len(p2rows), 'failures': []}
        for i in p2rows:
            q = Q(rows[i]); K = len(q['choice_text'])
            qr, back = rotate(q)
            L = [chr(65 + j) for j in range(K)]
            perm = [q['choice_text'][(p - 1) % K] for p in range(K)]
            f = []
            if qr['choice_labels'] != q['choice_labels'] or q['choice_labels'] != L:
                f.append('labels moved')
            if qr['choice_text'] != perm or sorted(qr['choice_text']) != sorted(q['choice_text']):
                f.append('texts not the V1 permutation')
            rb, hb = B.receiver_body(qr), B.helper_body(qr)
            for name, text in [('receiver_prompt', rb), ('helper_body', hb), ('probe_prompt', B.RP.receiver_prompt(qr))]:
                if text.count(block(L, perm)) != 1:
                    f.append(f'{name}: permuted option block not found exactly once')
                if K > 1 and len(set(q['choice_text'])) == K and block(L, q['choice_text']) in text:
                    f.append(f'{name}: original-order option block present')
            if pop == 'obqa':
                _, tfp = B.helper_ids(qr, facts[i])
                if ('Useful fact: ' + facts[i] + '\n' + hb) not in tfp:
                    f.append('TF helper: fact line / rotated body mismatch')
            for p in range(K):
                j = ord(back[L[p]]) - 65
                if j != (p - 1) % K or qr['choice_text'][p] != q['choice_text'][j]:
                    f.append(f'map-back wrong at position {p}')
            if i in ids:  # P3 rows actually run: the model saw exactly this rotated prompt
                if (i, 'probe') not in new3:
                    f.append('P3 record missing')
                else:
                    pr = new3[i, 'probe']
                    if pr['probe_ids_sha256'] != B.probe_sha(qr):
                        f.append('P3 probe input ids != frozen builder on rotated question')
                    if pr['choice_text_used'] != qr['choice_text'] or pr['back'] != back:
                        f.append('P3 record rotation/back mismatch')
                    if (i, 'R') in new3 and new3[i, 'R']['receiver_input_tokens'] != len(B.receiver_only_ids(qr)):
                        f.append('P3 R input length != frozen builder on rotated question')
                    for a in ACTS[pop][1:]:
                        if (i, a) in new3:
                            r = new3[i, a]
                            if r['answer_original'] != (back[r['answer']] if r['answer'] != INV else INV):
                                f.append(f'P3 {a} answer_original mapping wrong')
            if f:
                p2['failures'].append({'id': i, 'K': K, 'fail': f})
        if p2['failures']:
            stop.append(f'P2 {pop}: {len(p2["failures"])} rows fail')
        rep['P2'][pop] = p2
        # ---------------- P3 smoke: INVALID per arm on 16 rotated rows
        p3 = {'rows': len(ids), 'duplicates': len(dup3), 'missing': 0, 'invalid': {}}
        for a in ACTS[pop]:
            got = [new3[i, a] for i in ids if (i, a) in new3]
            p3['missing'] += len(ids) - len(got)
            if a != 'probe':
                p3['invalid'][a] = sum(r['answer'] == INV for r in got)
                if p3['invalid'][a] > 2:
                    stop.append(f'P3 {pop}: {a} INVALID {p3["invalid"][a]}/16 (> 2)')
        if p3['missing'] or p3['duplicates']:
            stop.append(f'P3 {pop}: missing {p3["missing"]} / duplicates {p3["duplicates"]}')
        rep['P3'][pop] = p3
    rep['verdict'] = 'PASS' if not stop else 'STOP'
    rep['gold_read'] = False
    save(E21 / 'preflight/PREFLIGHT_GATE.json', rep)
    print('PREFLIGHT', rep['verdict'], json.dumps(stop), flush=True)
    for pop in ['arc', 'obqa']:
        print(pop, 'P1 identical', rep['P1'][pop]['identical'], 'hard', rep['P1'][pop]['hard'],
              'u max|d|', rep['P1'][pop]['u_absdiff_max'], 'P2 fail', len(rep['P2'][pop]['failures']),
              'P3 invalid', rep['P3'][pop]['invalid'], flush=True)
    sys.exit(0 if not stop else 3)


# ------------------------------------------------------------------ manifest
def prod_paths(pop):
    return sorted((E21 / 'out').glob(f'{pop}_rot_shard*.jsonl'))


def cmd_manifest():
    man = {'utc': utc(), 'deadline_utc': DEADLINE_UTC, 'populations': {}, 'files': {}}
    last, first = None, None
    for pop in ['arc', 'obqa']:
        ids = [r['id'] for r in population(pop)]
        cnt = collections.Counter()
        for p in prod_paths(pop):
            man['files'][str(p.relative_to(E21))] = sha(p)
            for r in jl(p):
                assert r['transform'] == 'v1' and r['dataset'] == pop
                cnt[r['id'], r['action']] += 1
                last = max(last or r['utc'], r['utc']); first = min(first or r['utc'], r['utc'])
        missing = [(i, a) for i in ids for a in ACTS[pop] if cnt[i, a] == 0]
        multi = [(i, a, c) for (i, a), c in cnt.items() if c > 1]
        extra = [k for k in cnt if k[0] not in set(ids) or k[1] not in ACTS[pop]]
        man['populations'][pop] = {'N': len(ids), 'arms': ACTS[pop], 'records': sum(cnt.values()),
                                   'missing': len(missing), 'duplicates': len(multi), 'unexpected': len(extra),
                                   'missing_examples': missing[:20], 'complete': not missing and not multi and not extra}
    man['first_output_utc'], man['last_output_utc'] = first, last
    man['all_complete'] = all(v['complete'] for v in man['populations'].values())
    man['written_by_deadline'] = bool(man['all_complete'] and last and
                                      datetime.datetime.fromisoformat(last) <= datetime.datetime.fromisoformat(DEADLINE_UTC))
    save(E21 / 'results/MANIFEST.json', man)
    print(json.dumps({k: v for k, v in man.items() if k != 'files'}, indent=1))


# ------------------------------------------------------------------ stats
def cp(k, n):
    from scipy.stats import beta
    if n == 0:
        return float('nan'), float('nan')
    lo = 0.0 if k == 0 else float(beta.ppf(0.025, k, n - k + 1))
    hi = 1.0 if k == n else float(beta.ppf(0.975, k + 1, n - k))
    return lo, hi


def pval(k, n):
    from scipy.stats import binom
    return float(binom.cdf(k, n, 0.05)) if n else float('nan')


def cmd_stats():
    man = json.loads((E21 / 'results/MANIFEST.json').read_text())  # manifest must exist before any statistic
    gate = json.loads((E21 / 'preflight/PREFLIGHT_GATE.json').read_text())
    prim, sec_R, sec_u0, sec_b, inv = [], [], [], [], []
    for pop in ['arc', 'obqa']:
        ids = [r['id'] for r in population(pop)]
        new, dup = new_records(prod_paths(pop), 'v1')
        assert not dup
        st = stored(pop)
        have = [i for i in ids if all((i, a) in new for a in ACTS[pop])]
        u = {i: new[i, 'probe']['ProbeMax'] for i in have}
        A = {(i, a): new[i, a]['answer_original'] for i in have for a in ACTS[pop][1:]}
        for (name, p, ref, q, tau, k0, n0) in POLICIES:
            if p != pop:
                continue
            N = len(have)
            om = [i for i in have if u[i] <= tau]
            ch = [i for i in om if A[i, 'R'] != A[i, ref]]
            z = [i for i in om if u[i] == 0.0]
            lo, hi = cp(len(ch), len(om))
            om0 = [i for i in ids if st[i]['u'] <= tau]
            k0c = sum(st[i]['R']['ans'] != st[i][ref]['ans'] for i in om0)
            lo0, hi0 = cp(k0, n0)
            prim.append({'policy': name, 'population': pop, 'q': q, 'tau': tau, 'N': N,
                         'u_rot_zero_share': sum(u[i] == 0.0 for i in have) / N if N else float('nan'),
                         'n_omitted': len(om), 'coverage': len(om) / N if N else float('nan'),
                         'coverage_orig': len(om0) / len(ids), 'n_orig': len(om0),
                         'k': len(ch), 'k_over_n': len(ch) / len(om) if om else float('nan'), 'CP95_lo': lo, 'CP95_hi': hi,
                         'p_one_sided_H0_rho_ge_.05': pval(len(ch), len(om)),
                         'k_at_u_rot_0': sum(u[i] == 0.0 for i in ch), 'n_at_u_rot_0': len(z),
                         'k_at_u_rot_gt_0': sum(u[i] > 0.0 for i in ch), 'n_at_u_rot_gt_0': len(om) - len(z),
                         'orig_k': k0, 'orig_n': n0, 'orig_k_over_n': k0 / n0, 'orig_CP95_hi': hi0,
                         'orig_k_recomputed_from_stored': k0c, 'orig_n_recomputed_from_stored': len(om0)})
        # secondary: R_rot vs stored R_orig (ARC: only where a stored R exists)
        base = [i for i in have if 'R' in st[i]]
        for lab, sub in [('all', base), ('u_orig=0', [i for i in base if st[i]['u'] == 0.0]),
                         ('u_orig>0', [i for i in base if st[i]['u'] > 0.0])]:
            agree = sum(A[i, 'R'] == st[i]['R']['ans'] for i in sub)
            sec_R.append({'population': pop, 'subset': lab, 'n': len(sub), 'agree': agree,
                          'agreement': agree / len(sub) if sub else float('nan')})
        u0 = [i for i in have if st[i]['u'] == 0.0]
        sec_u0.append({'population': pop, 'n_u_orig_0': len(u0), 'n_u_rot_0_among_them': sum(u[i] == 0.0 for i in u0),
                       'share': sum(u[i] == 0.0 for i in u0) / len(u0) if u0 else float('nan'),
                       'n_u_rot_0_all': sum(u[i] == 0.0 for i in have)})
        for ref in ACTS[pop][2:]:
            agree = sum(A[i, ref] == st[i][ref]['ans'] for i in have)
            sec_b.append({'population': pop, 'reference': ref, 'n': len(have), 'agree': agree, 'agreement': agree / len(have) if have else float('nan')})
        for a in ACTS[pop][1:]:
            inv.append({'population': pop, 'arm': a, 'invalid_rot': sum(A[i, a] == INV for i in have), 'N_rot': len(have),
                        'invalid_orig': sum(st[i][a]['ans'] == INV for i in ids if a in st[i]),
                        'N_orig': sum(a in st[i] for i in ids)})
    R = E21 / 'results'
    csvout(R / 'primary_policies.csv', prim); csvout(R / 'secondary_R_agreement.csv', sec_R)
    csvout(R / 'secondary_u0.csv', sec_u0); csvout(R / 'secondary_b_agreement.csv', sec_b); csvout(R / 'invalid_counts.csv', inv)
    # writing rule
    reasons = []
    if gate['verdict'] != 'PASS':
        reasons.append('preflight STOP')
    if not man['all_complete']:
        reasons.append('outputs incomplete')
    elif not man['written_by_deadline']:
        reasons.append(f'last output {man["last_output_utc"]} after {DEADLINE_UTC}')
    if reasons:
        rule = '(4)'
    elif any(r['k_over_n'] > 0.05 for r in prim):
        rule = '(2)'
    elif all(r['CP95_hi'] < 0.05 for r in prim):
        rule = '(1)'
    else:
        rule = '(3)'
    res = {'utc': utc(), 'rule': rule, 'rule4_reasons': reasons, 'primary': prim, 'secondary_R': sec_R, 'secondary_u0': sec_u0,
           'secondary_b': sec_b, 'invalid': inv, 'manifest_last_output_utc': man['last_output_utc'], 'gold_read': False}
    save(R / 'E21B_RESULTS.json', res)
    print('RULE', rule, reasons)
    for r in prim:
        print('%-22s N=%d u0=%.3f n=%d (%.4f; orig %.4f) k=%d k/n=%.4f [%.4f, %.4f] p=%.3g k(u0/u>0)=%d/%d orig %d/%d' % (
            r['policy'], r['N'], r['u_rot_zero_share'], r['n_omitted'], r['coverage'], r['coverage_orig'], r['k'], r['k_over_n'],
            r['CP95_lo'], r['CP95_hi'], r['p_one_sided_H0_rho_ge_.05'], r['k_at_u_rot_0'], r['k_at_u_rot_gt_0'], r['orig_k'], r['orig_n']))


if __name__ == '__main__':
    {'select': cmd_select, 'gate': cmd_gate, 'manifest': cmd_manifest, 'stats': cmd_stats}[sys.argv[1]]()
