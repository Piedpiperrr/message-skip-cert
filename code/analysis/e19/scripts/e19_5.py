"""E19-5: pass criteria quoted verbatim from the hashed protocols, and the ten out-of-sample tests (frozen parser V2, original populations).
n, k are recomputed from the stored per-row files (same sources as E19-2) and must equal the stored counts."""
from e19_common import *
import collections, re

T0 = utc()
print('E19-5 start', T0)
P9F = E9B / 'PROTOCOL_FREEZE_E9B.md'
P9A = E9B / 'PROTOCOL_AMENDMENT_E9B.md'
PSA = SA / 'USER_PROMPT_ZH.md'
P16 = E16 / 'PREREG.md'
# stored hashes of the protocols
H = {P9F: (E9B / 'PROTOCOL_FREEZE_E9B.md.sha256').read_text().split()[0],
     P9A: (E9B / 'PROTOCOL_AMENDMENT_E9B.md.sha256').read_text().split()[0],
     PSA: read(SA / 'PROTOCOL_FREEZE.json')['files']['USER_PROMPT_ZH.md'],
     P16: (E16 / 'PREREG.sha256').read_text().split()[0]}
HT = {P9F: (E9B / 'PROTOCOL_FREEZE_E9B.utc').read_text().strip(), P9A: (E9B / 'PROTOCOL_AMENDMENT_E9B.utc').read_text().strip(),
      PSA: read(SA / 'PROTOCOL_FREEZE.json')['utc'], P16: [l for l in (E16 / 'PREREG.sha256').read_text().splitlines() if 'utc' in l][0]}
CHK = []
for p, h in H.items():
    got = sha(p)
    CHK.append(dict(check=f'SHA-256 of {p.relative_to(ROOT)} == stored hash', expected=h, observed=got, status='PASS' if got == h else 'FAIL'))


def lines(p, a, b):
    L = open(p, encoding='utf-8').read().split('\n')
    return '\n'.join(L[a - 1:b])


# every line in each protocol that contains a candidate criterion word (for the record of what was searched)
PAT = re.compile(r'pass|fail|p\s*<=|p<=|\.001|0\.001|upper|Clopper|CP|reject|通过|拒绝|成功|失败|风险目标|5%', re.I)
SCAN = []
for p in H:
    for n, l in enumerate(open(p, encoding='utf-8').read().split('\n'), 1):
        if PAT.search(l):
            SCAN.append(dict(file=str(p.relative_to(ROOT)), line=n, text=l.strip()))

QUOTES = [
    dict(test_family='held-out 744 OBQA (E9b), 5 tests', file=str(P9F.relative_to(ROOT)), lines='16-20', sha256=H[P9F], hashed_utc=HT[P9F],
         quote=lines(P9F, 16, 20),
         reading='Defines the statistics (CP 95% interval; exact binomial p of the single prespecified test H0: rho >= .05). '
                 'No sentence defines "pass"; no significance level or CP-upper criterion is stated.'),
    dict(test_family='held-out 744 OBQA (E9b), amendment', file=str(P9A.relative_to(ROOT)), lines='18-22', sha256=H[P9A], hashed_utc=HT[P9A],
         quote=lines(P9A, 18, 22),
         reading='Keeps the statistics unchanged; adds no pass criterion.'),
    dict(test_family='held-out 744 OBQA (E9b), amendment (the only "p<=.001" in either E9b file)', file=str(P9A.relative_to(ROOT)), lines='83',
         sha256=H[P9A], hashed_utc=HT[P9A], quote=lines(P9A, 83, 83),
         reading='Lists the calibration design artifact (per-candidate acceptance p<=.001 in BOUNDARIES frozen_config.json) searched by check C2; '
                 'not a pass criterion for the held-out test. No separate p <= .001 sentence for large OBQA Text exists in either file.'),
    dict(test_family='sealed ARC (2 tests)', file=str(PSA.relative_to(ROOT)), lines='267-287', sha256=H[PSA], hashed_utc=HT[PSA],
         quote=lines(PSA, 267, 287),
         reading='States that the sealed test does not "pass/reject" a threshold; the question is whether the empirical conditional answer-change '
                 'rate stays near/within the prespecified 5% risk target, with a prespecified descriptive binomial interval allowed. '
                 'No p-value or CP-upper pass criterion. (Translation: "This round does not redo calibration, nor pass/reject a new threshold on '
                 'test. The target risk is still conditional answer-change <= 5%. The sealed test only reports the frozen policy\'s actual empirical '
                 'result on an independent population. ... Is the frozen policy\'s empirical conditional answer-change still near/within the '
                 'prespecified 5% risk target? Report numerator/denominator in full ... A prespecified descriptive binomial interval may be given, '
                 'but the test must not be used as a calibration set again, and q must not be changed based on the interval.")'),
    dict(test_family='E16 out-of-sample (E16-1 Llama OBQA/ARC; E16-2 medium ARC C2C)', file=str(P16.relative_to(ROOT)), lines='21-27; 29-34',
         sha256=H[P16], hashed_utc=HT[P16], quote=lines(P16, 21, 27) + '\n...\n' + lines(P16, 29, 34),
         reading='Pass = two-sided 95% CP upper < 5%; fail = CP lower > 5%; otherwise inconclusive. p <= .001 and p <= .025 are to be stated, not criteria.'),
]
for q in QUOTES: q['label'] = LABEL

# ---------------------------------------------------------------- the ten tests
HK = [('large/OBQA/Text', 'large_obqa_T_q80'), ('large/OBQA/C2C', 'large_obqa_C_q80'), ('medium/OBQA/C2C q=.55', 'medium_obqa_C_q55'),
      ('medium/OBQA/C2C q=.50', 'medium_obqa_C_q50'), ('large/OBQA/Text+fact', 'large_obqa_TF_q75')]
HO = collections.defaultdict(list)
for r in jl(E9B / 'analysis/SEALED_ROUTES.jsonl'): HO[r['policy']].append(r)
e9b = {r['policy']: r for r in read(E9B / 'analysis/E9B_RESULTS.json')['policies']}
TESTS = []


def nz(x): return INV if x in (None, INV) else x


for key, pk in HK:
    rr = [r for r in HO[pk] if r['omitted']]
    n, k = len(rr), sum(nz(r['R_answer']) != nz(r['reference_answer']) for r in rr)
    TESTS.append(dict(test=f'held-out OBQA (E9b) {key}', population='744 held-out OBQA (not sealed)', n=n, k=k, stored=[e9b[pk]['omitted'], e9b[pk]['changed']],
                      protocol=str(P9F.relative_to(ROOT)) + ' + amendment', protocol_criterion='none stated (statistics only: CP 95% + exact binomial p of H0 rho >= .05)'))
paired = collections.defaultdict(list)
for r in jl(SA / 'records/paired_sealed_2344.jsonl'): paired[r['reference']].append(r)
prim = {r['reference']: r for r in csvread(SA / 'summary/primary_sealed.csv')}
for key, b in [('large/ARC/Text', 'T'), ('large/ARC/C2C', 'C')]:
    rr = [r for r in paired[b] if r['routed']]
    n, k = len(rr), sum(nz(r['policy_answer']) != nz(r['reference_answer']) for r in rr)
    TESTS.append(dict(test=f'sealed ARC {key}', population='1,172 sealed ARC-Challenge test', n=n, k=k,
                      stored=[int(prim[b]['routed']), int(prim[b]['changed_among_routed'])], protocol=str(PSA.relative_to(ROOT)),
                      protocol_criterion='no pass/reject; descriptive: empirical conditional change near/within the 5% target'))
OOSP = read(E16 / 'results/analysis_oos/OOS_PRE_GOLD.json')['results']
for key, f, pk in [('Llama-3.1-8B/OBQA/Text', 'routes_llama_obqa.jsonl', 'Llama-3.1-8B OBQA/Text (q=.60) on 744 held-out OBQA'),
                   ('Llama-3.1-8B/ARC/Text', 'routes_llama_arc.jsonl', 'Llama-3.1-8B ARC/Text (q=.70) on 1,172 ARC test'),
                   ('medium/ARC/C2C', 'routes_medium_arc_C.jsonl', 'medium ARC/C2C (q=.60) on 1,172 ARC test')]:
    rr = [r for r in jl(E16 / 'results/analysis_oos' / f) if r['omitted']]
    n, k = len(rr), sum(nz(r['o_R']) != nz(r['o_ref']) for r in rr)
    TESTS.append(dict(test=f'E16 {key}', population=pk.split(' on ')[1], n=n, k=k, stored=[OOSP[pk]['omitted_n'], OOSP[pk]['changed_k']],
                      protocol=str(P16.relative_to(ROOT)), protocol_criterion='CP upper < 5% (pass); CP lower > 5% (fail); else inconclusive'))
for t in TESTS:
    CHK.append(dict(check=f"{t['test']}: n/k == stored", expected=json.dumps(t.pop('stored')), observed=json.dumps([t['n'], t['k']])))
    CHK[-1]['status'] = 'PASS' if CHK[-1]['expected'] == CHK[-1]['observed'] else 'FAIL'
    t['rate'] = t['k'] / t['n']
    t['p_exact_H0_rate_ge_05'] = pval(t['k'], t['n'])
    lo, hi = cp95(t['k'], t['n'])
    t['CP95_lo'], t['CP95_hi'] = lo, hi
    t['pass_p_le_001'] = t['p_exact_H0_rate_ge_05'] <= .001
    t['pass_CP_upper_lt_5pct'] = hi < .05
    if t['protocol'].endswith('PREREG.md'):
        t['passes_own_protocol'] = 'yes' if hi < .05 else ('fails' if lo > .05 else 'inconclusive')
    elif 'sealed' in t['test']:
        t['passes_own_protocol'] = f"n/a (no pass/reject; rate {100 * t['rate']:.2f}% within the 5% target)" if t['rate'] <= .05 else 'n/a (rate above 5%)'
    else:
        t['passes_own_protocol'] = 'n/a (protocol states no pass criterion)'
    t['label'] = LABEL
for c in CHK: print(c)
assert all(c['status'] == 'PASS' for c in CHK)
for t in TESTS:
    print(f"{t['test']:34s} n={t['n']} k={t['k']} p={t['p_exact_H0_rate_ge_05']:.3g} CPup={t['CP95_hi']:.4f} p<=.001:{t['pass_p_le_001']} CP<5%:{t['pass_CP_upper_lt_5pct']} own:{t['passes_own_protocol']}")
rule = dict(protocols_with_criterion_other_than_CP_upper=('E9b (none stated); sealed ARC (no pass/reject, descriptive 5% target)'),
            protocols_specifying_p_le_001='none',
            tests_failing_own_protocol_criterion='none',
            tests_failing_p_le_001=';'.join(t['test'] for t in TESTS if not t['pass_p_le_001']) or 'none',
            tests_failing_CP_upper_lt_5=';'.join(t['test'] for t in TESTS if not t['pass_CP_upper_lt_5pct']) or 'none',
            n_pass_CP_upper=sum(t['pass_CP_upper_lt_5pct'] for t in TESTS), n_pass_p001=sum(t['pass_p_le_001'] for t in TESTS), n_tests=len(TESTS),
            label=LABEL)
print(rule)
csvout('E19_5_quotes.csv', QUOTES)
csvout('E19_5_protocol_line_scan.csv', SCAN)
csvout('E19_5_ten_tests.csv', TESTS)
csvout('E19_5_checks.csv', CHK)
csvout('E19_5_writing_rule.csv', [rule])
json.dump(dict(start_utc=T0, end_utc=utc(), files_read=READ), open(STAGE / 'logs/e19_5_run.json', 'w'), indent=1)
print('E19-5 done', utc())
