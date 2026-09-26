"""E21-3a (PREREG.md): option-rotation stability of the receiver (stored E4 V1 outputs).
Gate (programmatic part; the code/protocol reading is quoted in SUMMARY.md): for every E4 population row, v1_query = query with only the option
contents rotated by one (labels, stem and every other field unchanged) and v1_display_to_original consistent with that rotation; for every V1
record, parsed_original = v1_display_to_original[parsed_displayed] (INVALID stays INVALID); for the rendered prompts of questions 0-2, the V1
prompt equals the V0 (unchanged receiver-only) prompt once option contents are masked, and lists the options in rotated order; the V0/V1 run
records one generation config (greedy, max_new_tokens 64). If any check fails, the statistics are not computed.
Statistics: c = 1[V1 mapped back != R] with R = the saved receiver-only answer (frozen V2 labels, INVALID-normalized; two INVALIDs agree,
exactly one INVALID = change); n, changes, rate, two-sided 95% CP, split by the receiver's stored u == 0 vs u > 0; parseable-only (neither
R nor V1 INVALID); the same on each deployed policy's omitted dev questions; V0 (same-job unchanged replay) vs R, supplementary drift line."""
from e21_common import *

T0 = utc()
print('E21-3a start', T0, flush=True)
POP = E4DIR / 'records/populations'
E4R = E4DIR / 'results/e4'
POPS = [('small', 'obqa'), ('small', 'arc'), ('medium', 'obqa'), ('medium', 'arc'), ('large', 'obqa'), ('large', 'arc'), ('large', 'mmlu_pro')]
TN = {'obqa': 'OBQA', 'arc': 'ARC', 'mmlu_pro': 'MMLU-Pro'}
FIVE = ['medium/OBQA', 'medium/ARC', 'large/OBQA', 'large/ARC', 'large/MMLU-Pro']
GATE = []


def gate(name, ok, detail):
    GATE.append(dict(check=name, status='PASS' if ok else 'FAIL', detail=detail))
    print(f"[{'PASS' if ok else 'FAIL'}] gate: {name}: {detail}", flush=True)


# ---- gate 1: population rows
for pair, ds in POPS:
    rows = jl(POP / f'e4_{pair}_{ds}.jsonl')
    bad = 0
    for r in rows:
        q, v, back = r['query'], r['v1_query'], r['v1_display_to_original']
        t, rot, lab = q['choice_text'], v['choice_text'], q['choice_labels']
        K = len(t)
        ok = (v['choice_labels'] == lab and v['question_stem'] == q['question_stem'] and set(v) == set(q)
              and all(rot[(i + 1) % K] == t[i] for i in range(K))
              and all(back[lab[p]] == lab[(p - 1) % K] and rot[p] == t[lab.index(back[lab[p]])] for p in range(K))
              and all(v[k] == q[k] for k in q if k not in ('choice_text', 'choices')))
        if 'choices' in q:
            ok = ok and v['choices']['label'] == lab and list(v['choices']['text']) == rot
        bad += not ok
    gate(f'{pair}/{TN[ds]} population: v1_query = option contents rotated by one, labels/stem/other fields unchanged, back-map consistent',
         bad == 0, f'{len(rows)} rows, {bad} violations')
# ---- gate 2: V1 records mapped back with the row's own map; decoding config
NREC = {}
for f in sorted(E4R.glob('*V1*.jsonl')):
    recs = [r for r in jl(f) if r['variant'] == 'V1']
    pair, ds = recs[0]['pair'], recs[0]['dataset']
    back = {r['id']: r['v1_display_to_original'] for r in jl(POP / f'e4_{pair}_{ds}.jsonl')}
    bad = sum(1 for r in recs if r.get('runtime_error') is None and
              r['parsed_original'] != (back[r['id']][r['parsed_displayed']] if r['parsed_displayed'] != INV else INV))
    nerr = sum(1 for r in recs if r.get('runtime_error') is not None)
    probe_fields = sorted({k for r in recs for k in r if 'probe' in k.lower() or k in ('ProbeMax', 'p_labels', 'u')})
    NREC[pair, ds] = dict(n=len(recs), runtime_errors=nerr, probe_fields=probe_fields)
    gate(f'{pair}/{TN[ds]} V1 records: parsed_original = back-map(parsed_displayed)', bad == 0,
         f'{len(recs)} V1 records, {bad} mismatches, {nerr} runtime errors; probe-score fields stored: {probe_fields or "none"}')
for f in sorted(E4R.glob('env_*V0-V1*.json')):
    g = read(f)['generation_config']
    gate(f'{f.name}: one generation config for V0 and V1 (greedy, max_new_tokens 64)', g['do_sample'] is False and g['max_new_tokens'] == 64
         and g.get('num_beams', 1) == 1, f"do_sample={g['do_sample']} max_new_tokens={g['max_new_tokens']} num_beams={g.get('num_beams')}")
# ---- gate 3: rendered prompts (questions 0-2): V1 == V0 once option contents are masked, options in rotated order
for f in sorted(E4R.glob('prompts_*V0-V1*.json')):
    P = read(f)
    pair_ds = f.name[len('prompts_'):].split('__')[0]
    pair, ds = pair_ds.split('_', 1)
    rows = {r['pos']: r for r in jl(POP / f'e4_{pair}_{ds}.jsonl')}
    ok, n = True, 0
    for pos in sorted({x['pos'] for x in P}):
        v0 = next(x['rendered'] for x in P if x['pos'] == pos and x['variant'] == 'V0')
        v1 = next(x['rendered'] for x in P if x['pos'] == pos and x['variant'] == 'V1')
        t, rot = rows[pos]['query']['choice_text'], rows[pos]['v1_query']['choice_text']
        m0, m1 = v0, v1
        for s in sorted(set(t), key=len, reverse=True):
            m0, m1 = m0.replace(s, '<OPT>'), m1.replace(s, '<OPT>')
        lab = rows[pos]['query']['choice_labels']
        lines0 = all(f'\n{lab[p]}. {t[p]}\n' in v0 for p in range(len(t)))
        lines1 = all(f'\n{lab[p]}. {rot[p]}\n' in v1 for p in range(len(t)))
        ok = ok and m0 == m1 and v0 != v1 and lines0 and lines1
        n += 1
    gate(f'{f.name}: rendered V1 prompt = V0 prompt with option contents rotated (questions 0-2)', ok, f'{n} questions compared')
GATE_OK = all(g['status'] == 'PASS' for g in GATE)
csvout('E21_3a_gate_checks.csv', GATE)
if not GATE_OK:
    run_log('e21_3a.py', T0, dict(gate='FAIL'))
    print('GATE FAILED: E21-3a statistics not computed')
    sys.exit(0)

# ---- statistics
NULL = E9A.null_answers()


def line(c, n_mask, what, **kw):
    n, k = int(n_mask.sum()), int(c[n_mask].sum())
    lo, hi = cp95(k, n)
    return dict(line=what, n=n, changes=k, rate=(k / n if n else float('nan')), CP95_lo=lo, CP95_hi=hi, **kw)


ROWS = []
POPDATA = {}
for pair, ds in POPS:
    D = C.load_main()[pair, TN[ds]]['dev']
    ids = list(D['ids'])
    assert set(ids) == {r['id'] for r in jl(POP / f'e4_{pair}_{ds}.jsonl')}
    R = np.array([E17.norm(x) for x in D['ans']['R']], object)
    u = np.asarray(D['scores']['ProbeMax'], float)
    miss = sum(1 for i in ids if i not in NULL[pair, ds, 'V1'])
    V1 = np.array([NULL[pair, ds, 'V1'].get(i, INV) for i in ids], object)
    V0 = np.array([NULL[pair, ds, 'V0'].get(i, INV) for i in ids], object)
    c = V1 != R
    c0 = V0 != R
    z = u == 0.0
    par = (R != INV) & (V1 != INV)
    name = f'{pair}/{TN[ds]}'
    POPDATA[name] = dict(ids=ids, c=c, z=z, par=par)
    base = dict(population=name, N=len(ids), V1_missing=miss, V1_INVALID=int((V1 == INV).sum()), R_INVALID=int((R == INV).sum()),
                V1_probe_score='not stored (E4 V1 records carry no probe score)', label=LABEL)
    for lab, msk in [('all', np.ones(len(ids), bool)), ('u = 0', z), ('u > 0', ~z)]:
        ROWS.append(line(c, msk, f'V1 vs R, {lab}', **base))
        ROWS.append(line(c, msk & par, f'V1 vs R, {lab}, parseable-only (R and V1 both parse)', **base))
        ROWS.append(line(c0, msk, f'supplementary: V0 (same-job unchanged replay) vs R, {lab}', **base))
# per deployed policy: the receiver's own answer change under rotation on the policy's omitted dev questions
for key in POL9:
    s = setting_of(key)
    Dk = dev(key)
    name = f'{s[0]}/{s[1]}'
    P = POPDATA[name]
    assert Dk['ids'] == P['ids']
    m = Dk['m']
    for lab, msk in [('omitted', m), ('omitted, u = 0', m & P['z']), ('omitted, u > 0', m & ~P['z'])]:
        ROWS.append(line(P['c'], msk, f"{key} [{lab}]: the receiver's own answer change under rotation, not the policy's change rate",
                         population=name, policy=key, q=Dk['q'], label=LABEL))
    ROWS.append(line(P['c'], m & P['par'], f"{key} [omitted, parseable-only]: the receiver's own answer change under rotation, not the policy's change rate",
                     population=name, policy=key, q=Dk['q'], label=LABEL))
for r in ROWS:
    print(f"{r['population']:15s} {r['line'][:110]:110s} n={r['n']} k={r['changes']} rate={r['rate']:.4f} CP=[{r['CP95_lo']:.4f},{r['CP95_hi']:.4f}]", flush=True)

# ---- writing rule
U0 = {r['population']: r for r in ROWS if r['line'] == 'V1 vs R, u = 0'}
fails = [p for p in FIVE if not U0[p]['CP95_hi'] < .05]
rates = [100 * U0[p]['rate'] for p in FIVE]
RULE = dict(u0_lines={p: dict(n=U0[p]['n'], changes=U0[p]['changes'], rate=U0[p]['rate'], CP95_hi=U0[p]['CP95_hi']) for p in FIVE},
            failing_populations=fails, label=LABEL)
if not fails:
    RULE['branch'] = 'all five u = 0 CP upper < 5%'
    RULE['sentence'] = (f'at u = 0 the receiver keeps its answer under option rotation (changes {min(rates):.1f}-{max(rates):.1f}%), so these confident '
                        f'answers follow option content, not position')
else:
    RULE['branch'] = 'otherwise (>= 1 of the five u = 0 CP upper ends >= 5%)'
    RULE['sentence'] = ('Sec. 6 gives the numbers (' + '; '.join(f"{p}: {U0[p]['changes']}/{U0[p]['n']} = {100 * U0[p]['rate']:.1f}% "
                                                               f"[CP upper {100 * U0[p]['CP95_hi']:.1f}%]" for p in FIVE) + '), names ' + ', '.join(fails) +
                        '; Limitations adds "part of the receiver\'s confident answers follow option position; the certificate covers the deployed prompt format".')
print(json.dumps(RULE, indent=1))
csvout('E21_3a_rotation.csv', ROWS)
jdump(RES / 'E21_3a_writing_rule.json', RULE)
run_log('e21_3a.py', T0, dict(gate='PASS'))
print('E21-3a done', utc())
