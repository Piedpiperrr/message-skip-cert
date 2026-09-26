"""E22 step 0: the REPRO checks (0a-0d) and INPUTS.md.  Nothing here is an E22 statistic.

  0a  re-execute E9-a's own scripts verbatim with their output directory redirected into this stage
      (numpy.random.default_rng(0), the seed stored in e9a_main.py / e9a_boot.py) and compare every
      per-reference ratio, the two medians and their 95% intervals with the stored E9-a outputs.
  0b  the stratified-joint medians (E13 Item 2): from the stored item2 outputs, and by re-executing item2.point().
  0c  the real gains per reference-population cell, and the E5 large/OBQA direction counts.
  0d  Table 1 accuracies, tab:null, tab:overlap (n(Text) = a + c, n(C2C) = b + c) and the medium/ARC eligible count.

Usage: step0_repro.py point | boot | report
"""
import sys, json, time, hashlib, builtins, pathlib
import numpy as np
from e22_common import *
import e22_common as C

OUT = RES / 'step0'
OUT.mkdir(parents=True, exist_ok=True)
READS = []


def trace_on():
    if getattr(builtins, '_e22_traced', False):
        return
    bo, po = builtins.open, pathlib.Path.open
    def o(f, *a, **k):
        try: READS.append(str(pathlib.Path(f).resolve()))
        except Exception: pass
        return bo(f, *a, **k)
    def p(self, *a, **k):
        try: READS.append(str(self.resolve()))
        except Exception: pass
        return po(self, *a, **k)
    builtins.open, pathlib.Path.open = o, p
    builtins._e22_traced = True


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''): h.update(b)
    return h.hexdigest()


def run_e9a(name):
    """Re-execute an E9-a script unchanged; only e9a_common.RES (where it writes) is redirected."""
    E.RES = OUT / 'e9a_rerun'
    E.RES.mkdir(parents=True, exist_ok=True)
    f = E9A / 'scripts' / name
    exec(compile(f.read_text(), str(f), 'exec'), {'__name__': 'e22_rerun_' + name[:-3]})


def chk(rows, name, expected, obtained, ok=None):
    if ok is None:
        ok = (str(expected) == str(obtained))
    rows.append(dict(check=name, expected=str(expected), obtained=str(obtained), pass_=str(bool(ok)), label=LABEL))
    return bool(ok)


# ----------------------------------------------------------------------------- 0a (point) / 0a (bootstrap)
def a_point(rows):
    run_e9a('e9a_main.py')
    new = {r['population']: r for r in csvread(OUT / 'e9a_rerun' / 'e9a_ratios.csv')}
    old = {r['population']: r for r in csvread(E9A / 'results' / 'e9a_ratios.csv')}
    allok = True
    for p in POPNAME:
        for k, nm in [('perref_Text_ratio', 'Text'), ('perref_C2C_ratio', 'C2C')]:
            allok &= chk(rows, f'0a ratio {p} per-reference {nm}', old[p][k], new[p][k])
    for k, nm, exp in [('perref_Text_ratio', 'Text', '0.742'), ('perref_C2C_ratio', 'C2C', '1.125')]:
        med = fmt(np.median([float(new[p][k]) for p in POPNAME]))
        allok &= chk(rows, f'0a median of 7, per-reference {nm} (point)', exp, med)
    return allok


def a_boot(rows):
    run_e9a('e9a_boot.py')
    new = {(r['design'], r['population']): r for r in csvread(OUT / 'e9a_rerun' / 'e9a_bootstrap_intervals.csv')}
    old = {(r['design'], r['population']): r for r in csvread(E9A / 'results' / 'e9a_bootstrap_intervals.csv')}
    allok = True
    for d in ['per-reference Text', 'per-reference C2C']:
        for p in POPNAME + ['MEDIAN of 7']:
            o, n = old[d, p], new[d, p]
            allok &= chk(rows, f'0a interval {p} {d}', f"[{o['ci_lo_2_5']}, {o['ci_hi_97_5']}]",
                         f"[{n['ci_lo_2_5']}, {n['ci_hi_97_5']}]")
    allok &= chk(rows, '0a stored median interval, per-reference Text', '[0.644, 0.840]',
                 f"[{new['per-reference Text', 'MEDIAN of 7']['ci_lo_2_5']}, {new['per-reference Text', 'MEDIAN of 7']['ci_hi_97_5']}]")
    allok &= chk(rows, '0a stored median interval, per-reference C2C', '[0.895, 1.349]',
                 f"[{new['per-reference C2C', 'MEDIAN of 7']['ci_lo_2_5']}, {new['per-reference C2C', 'MEDIAN of 7']['ci_hi_97_5']}]")
    return allok


# ----------------------------------------------------------------------------- 0b
def b_stratified_joint(rows):
    stored = {r['population']: r for r in csvread(E13 / 'results' / 'item2_stratified_ratios.csv')}
    allok = True
    for k, exp in [('ratio_gain_over_R', '0.849'), ('ratio_best_fixed', '0.967')]:
        med = fmt(np.median([float(stored[p][k]) for p in POPNAME]))
        allok &= chk(rows, f'0b stored stratified-joint median, {k}', exp, med)
        allok &= chk(rows, f'0b stored stratified-joint MEDIAN row, {k}', exp, stored['MEDIAN of 7'][k])
    sys.path.insert(0, str(E13 / 'scripts'))
    import e13_common as E13C
    E13C.RES = OUT / 'e13_rerun'
    E13C.RES.mkdir(parents=True, exist_ok=True)
    f = E13 / 'scripts' / 'item2.py'
    g = {'__name__': 'e22_rerun_item2'}
    exec(compile(f.read_text(), str(f), 'exec'), g)
    g['point']()
    new = {r['population']: r for r in csvread(OUT / 'e13_rerun' / 'item2_stratified_ratios.csv')}
    for k, exp in [('ratio_gain_over_R', '0.849'), ('ratio_best_fixed', '0.967')]:
        allok &= chk(rows, f'0b re-run stratified-joint median, {k}', exp, new['MEDIAN of 7'][k])
    for p in POPNAME:
        for k in ['ratio_gain_over_R', 'ratio_best_fixed']:
            allok &= chk(rows, f'0b re-run {p} {k}', stored[p][k], new[p][k])
    return allok


# ----------------------------------------------------------------------------- 0c / 0d
def cd_checks(rows, raw):
    old = {r['population']: r for r in csvread(E9A / 'results' / 'e9a_ratios.csv')}
    ovl = {r['population']: r for r in csvread(E9A / 'results' / 'e9a_overlap.csv')}
    nc = {r['population']: r for r in csvread(E5 / 'results' / 'e5c_null_control.csv')}
    dec = {(r['population'], r['action']): r for r in csvread(E5 / 'results' / 'e5c_change_decomposition.csv')}
    # Table 1 as printed in P2_FINAL_ABSTRACT_REVISION_20260918T193147Z/paper/tab_main_complementarity.tex
    TAB1 = {'small/OBQA': (742, 285, 346, 366, 498, '17.79'), 'small/ARC': (299, 110, 126, 155, 204, '16.39'),
            'medium/OBQA': (742, 490, 523, 486, 593, '9.43'), 'medium/ARC': (299, 217, 221, 202, 248, '9.03'),
            'large/OBQA': (742, 617, 645, 598, 670, '3.37'), 'large/ARC': (299, 268, 274, 266, 280, '2.01'),
            'large/MMLU-Pro': (2641, 1282, 1319, 1233, 1558, '9.05')}
    allok = True
    gains = []
    for (P, R, _), nm in zip(raw, POPNAME):
        v = P.view()
        g = np.array(R['gold'], object)
        y = {a: np.array([x == b for x, b in zip(R[a], R['gold'])], bool) for a in ['R', 'Text', 'C2C', 'V1', 'V2']}
        ch = {a: np.array([x != b for x, b in zip(R[a], R['R'])], bool) for a in ['Text', 'C2C', 'V1', 'V2']}
        # --- 0c real gains
        for a, key in [('Text', 'real_gain_R_Text'), ('C2C', 'real_gain_R_C2C')]:
            got = int((~y['R'] & y[a]).sum())
            allok &= chk(rows, f'0c real gain over R, {nm} {a}', old[nm][key], got)
            gains.append(dict(population=nm, reference=a, real_gain_over_R=got, stored_E9a=old[nm][key], label=LABEL))
        allok &= chk(rows, f'0c real gain over R, {nm} Text+C2C (oracle)', old[nm]['real_gain_R_Text_C2C'],
                     int((~y['R'] & (y['Text'] | y['C2C'])).sum()))
        # --- 0c / E22-2 precondition: E5 direction counts
        for a in ['Text', 'C2C', 'V1', 'V2']:
            corr = int((ch[a] & ~y['R'] & y[a]).sum()); harm = int((ch[a] & y['R']).sum())
            neut = int((ch[a] & ~y['R'] & ~y[a]).sum())
            allok &= chk(rows, f'0c E5 decomposition {nm} {a} corrective', dec[nm, a]['corrective'], corr)
            allok &= chk(rows, f'0c E5 decomposition {nm} {a} harmful', dec[nm, a]['harmful'], harm)
            allok &= chk(rows, f'0c E5 decomposition {nm} {a} neutral(wrong->wrong)', dec[nm, a]['neutral_both_wrong'], neut)
            allok &= chk(rows, f'0c E5 decomposition {nm} {a} changed', dec[nm, a]['changed'], int(ch[a].sum()))
        # --- 0d Table 1
        N, cR, cT, cC, orc, gpp = TAB1[nm]
        allok &= chk(rows, f'0d Table 1 {nm} N', N, P.N)
        allok &= chk(rows, f'0d Table 1 {nm} correct R/Text/C2C', f'{cR} / {cT} / {cC}',
                     f"{int(y['R'].sum())} / {int(y['Text'].sum())} / {int(y['C2C'].sum())}")
        o = int((y['R'] | y['Text'] | y['C2C']).sum())
        allok &= chk(rows, f'0d Table 1 {nm} oracle', orc, o)
        allok &= chk(rows, f'0d Table 1 {nm} gain (pp)', gpp,
                     f'{100 * (o - max(int(y["R"].sum()), int(y["Text"].sum()), int(y["C2C"].sum()))) / P.N:.2f}')
        # --- 0d tab:null  (correct R / V1 / V2 and % changed)
        for a in ['R', 'V1', 'V2']:
            allok &= chk(rows, f'0d tab:null {nm} correct {a}', nc[nm][f'{a}_correct'], int(y[a].sum()))
        for a in ['V1', 'V2']:
            allok &= chk(rows, f'0d tab:null {nm} % changed {a}', f'{100 * int(dec[nm, a]["changed"]) / P.N:.2f}',
                         f'{100 * int(ch[a].sum()) / P.N:.2f}')
        # --- 0d tab:overlap
        a_, b_, c_, cs_ = v.a, v.b, v.c, v.c_same
        for key, got in [('a_Text_only', a_), ('b_C2C_only', b_), ('c_both', c_), ('c_same_answer', cs_)]:
            allok &= chk(rows, f'0d tab:overlap {nm} {key}', ovl[nm][key], got)
        allok &= chk(rows, f'0d tab:overlap {nm} n(Text) = a + c', old[nm]['m_Text'], a_ + c_)
        allok &= chk(rows, f'0d tab:overlap {nm} n(C2C) = b + c', old[nm]['m_C2C'], b_ + c_)
        allok &= chk(rows, f'0d eligible (P(x) nonempty) {nm}', old[nm]['n_eligible_P_nonempty'], v.E)
    allok &= chk(rows, '0d large/OBQA n(Text) = 72 and n(C2C) = 60', '72 / 60',
                 f"{old['large/OBQA']['m_Text']} / {old['large/OBQA']['m_C2C']}")
    allok &= chk(rows, '0d medium/ARC eligible = 73', '73', old['medium/ARC']['n_eligible_P_nonempty'])
    csvout(OUT / 'step0_real_gains.csv', gains)
    return allok


def inputs_md(main):
    files = set()
    for k, D in main.items():
        files.update(D['sources'].values())
    files.update(str(p) for p in READS)
    files.add(str(E.MMLU_PARQUET))
    for f in ['P2_R3_E9A_20260920T043713Z/scripts/e9a_common.py', 'P2_R3_E9A_20260920T043713Z/scripts/e9a_main.py',
              'P2_R3_E9A_20260920T043713Z/scripts/e9a_boot.py', 'P2_R2_CPU_20260919T220412Z/scripts/r2_common.py',
              'P2_R2_CPU_20260919T220412Z/scripts/e5c.py', 'P2_R1_CPU_20260919T045556Z/src/common_r1.py',
              'P2_R1_CPU_20260919T045556Z/src/data_r1.py', 'P2_R5_E13_20260921T031606Z/scripts/e13_common.py',
              'P2_R5_E13_20260921T031606Z/scripts/item2.py']:
        files.add(str(ROOT / f))
    keep = sorted({f for f in files if pathlib.Path(f).is_file()
                   and '/P2_R10_E22_' not in f and not f.endswith(('.pyc', '.so'))
                   and str(ROOT) in f})
    lines = ['# E22 INPUTS (SHA-256)', '',
             'Every file read by the loaders and every stored output used as an expected value.', '',
             '| file | bytes | sha256 |', '|---|---|---|']
    for f in keep:
        lines.append(f'| `{pathlib.Path(f).relative_to(ROOT)}` | {pathlib.Path(f).stat().st_size} | `{sha(f)}` |')
    (STAGE / 'INPUTS.md').write_text('\n'.join(lines) + f'\n\n{len(keep)} files.\n')
    return len(keep)


def main_point():
    trace_on()
    rows = []
    raw = load_raw()
    for f in sorted((E9A / 'results').glob('*.csv')) + sorted((E13 / 'results').glob('item2_*.csv')) + \
             sorted((E5 / 'results').glob('e5c_*.csv')):
        READS.append(str(f.resolve()))
    ok_c = cd_checks(rows, raw)
    ok_a = a_point(rows)
    ok_b = b_stratified_joint(rows)
    csvout(OUT / 'step0_checks_point.csv', rows)
    n = inputs_md({nm: D for (_, _, D), nm in zip(raw, POPNAME)})
    print(f'0a point {ok_a} | 0b {ok_b} | 0c/0d {ok_c} | {sum(r["pass_"] == "True" for r in rows)}/{len(rows)} checks pass'
          f' | INPUTS.md {n} files')


def main_boot():
    t0 = time.time()
    rows = []
    ok = a_boot(rows)
    csvout(OUT / 'step0_checks_boot.csv', rows)
    print(f'0a bootstrap {ok} | {sum(r["pass_"] == "True" for r in rows)}/{len(rows)} checks pass | {time.time() - t0:.0f}s')


if __name__ == '__main__':
    {'point': main_point, 'boot': main_boot}[sys.argv[1]]()
