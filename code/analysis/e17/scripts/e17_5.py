"""E17-5: (a) population feasibility; (b) binormal model of the certification boundary; (c) grid for a figure.

Binormal: agreeing score ~ N(0,1), disagreeing ~ N(mu,1), mu = sqrt(2) Phi^-1(AUROC); omit iff score <= tau (higher score =
more likely to disagree, as u). One simulation of the frozen procedure: N_fit fit scores (disagreement ~ Bernoulli(prevalence)),
tau_j = order statistic ceil(j N_fit / 20), j = 1..19, q = 1 omits all; N_cal calibration questions; 20 exact binomial tests
P[Bin(n, .05) <= k] <= .001 (n = 0 -> p = 1); deploy the largest accepted q. Coverage = population share below the selected tau
= prev * Phi(tau - mu) + (1 - prev) * Phi(tau) (1 for q = 1). RNG: numpy default_rng(0), fresh per setting and run (main,
sensitivity), per bisection step (common random numbers) and per grid cell; draws in chunks of 250 simulations.
"""
import sys, time, math
import numpy as np
from scipy.stats import norm as N01, binom
from e17_common import *

A_ = .05; DELTA = .001
IDX = lambda Nf: np.array([(j * Nf + 19) // 20 - 1 for j in range(1, 20)])
CH = 250


def draws(rng, B, Nf, Nc, p):
    out = []
    for s in range(0, B, CH):
        b = min(CH, B - s)
        Df = rng.random((b, Nf)) < p; Zf = rng.standard_normal((b, Nf))
        Dc = rng.random((b, Nc)) < p; Zc = rng.standard_normal((b, Nc))
        out.append((Df, Zf, Dc, Zc))
    return out


def run(dr, p, auc, Nf, Nc):
    mu = math.sqrt(2) * N01.ppf(auc)
    cert, qs, cov = [], [], []
    ix = IDX(Nf)
    for Df, Zf, Dc, Zc in dr:
        sf = np.sort(Zf + mu * Df, axis=1); tau = sf[:, ix]                      # (b, 19)
        sc = Zc + mu * Dc
        n = np.empty((len(sf), 20), int); k = np.empty((len(sf), 20), int)
        for j in range(19):
            m = sc <= tau[:, j:j + 1]; n[:, j] = m.sum(1); k[:, j] = (m & Dc).sum(1)
        n[:, 19] = Nc; k[:, 19] = Dc.sum(1)
        pv = np.where(n > 0, binom.cdf(k, n, A_), 1.0)
        acc = pv <= DELTA
        c = acc.any(1)
        last = np.where(c, 19 - np.argmax(acc[:, ::-1], axis=1), -1)            # index of the largest accepted q
        tsel = np.where(last == 19, np.inf, tau[np.arange(len(sf)), np.clip(last, 0, 18)])
        cv = np.where(last == 19, 1.0, p * N01.cdf(tsel - mu) + (1 - p) * N01.cdf(tsel))
        cert.append(c); qs.append((last + 1) / 20); cov.append(cv)
    cert, qs, cov = np.concatenate(cert), np.concatenate(qs), np.concatenate(cov)
    return cert, qs, cov


def summarize(cert, qs, cov):
    P = float(cert.mean())
    if cert.any():
        vals, cnt = np.unique(qs[cert], return_counts=True)
        mode = float(vals[np.argmax(cnt)]); medcov = float(np.median(cov[cert]))
    else:
        mode, medcov = None, None
    return P, mode, medcov


def bisect(p, Nf, Nc, B=1000, lo=.5, hi=.9999, tol=.001):
    dr = draws(np.random.default_rng(0), B, Nf, Nc, p)
    P = lambda a: float(run(dr, p, a, Nf, Nc)[0].mean())
    plo, phi = P(lo), P(hi)
    steps = [(lo, plo), (hi, phi)]
    if plo >= .5: return f'<= {lo}', lo, steps
    if phi < .5: return f'> {hi} (P(certify) at {hi} = {phi:.3f})', None, steps
    while hi - lo > tol:
        mid = (lo + hi) / 2; pm = P(mid); steps.append((mid, pm))
        if pm >= .5: hi = mid
        else: lo = mid
    return f'{(lo + hi) / 2:.4f}', (lo + hi) / 2, steps


if __name__ == '__main__':
    part = sys.argv[1] if len(sys.argv) > 1 else 'ab'
    X = loadcache(); D = X['D']
    if 'a' in part or 'b' in part:
        IN, FA = [], []
        for s in ALL28:
            L = D[s]
            cu, cd = L['cal']['u'], L['cal']['d']
            led = ledger(cu, cd, L['cuts'])
            Nc = led[-1]['n'] if s[1] == 'MMLU-Pro' else len(cu)
            prev = float(cd.mean())
            IN.append(dict(setting=sname(s), observed='certify' if L['q0'] > 0 else 'fallback', q0=L['q0'], N_fit=len(L['fit']['u']), N_cal=Nc,
                           prevalence_cal=prev, AUROC_dev=auroc(L['dev']['d'], L['dev']['u']), AUROC_cal=auroc(cd, cu),
                           share_u0_cal=float((cu == 0).mean()), share_u0_dev=float((L['dev']['u'] == 0).mean())))
            # (a) population feasibility
            A, Dn = int((~cd).sum()), int(cd.sum())
            pi = 1 - prev; Cc = (1 - pi) * (1 - A_) / (pi * A_)
            best, anyle = -1.0, False
            for r in led:
                if r['n'] == 0: continue
                tpr, fpr = (r['n'] - r['k']) / A, r['k'] / Dn
                ratio = float('inf') if fpr == 0 else tpr / fpr
                best = max(best, ratio); anyle |= r['k'] / r['n'] <= A_
            FA.append(dict(setting=sname(s), observed=IN[-1]['observed'], pi=pi, C=Cc, max_TPR_over_FPR=best,
                           max_ge_C=best >= Cc, some_candidate_k_over_n_le_05=anyle, equivalence_holds=(best >= Cc) == anyle, label=LABEL))
            print(FA[-1])
        csvout('E17_5a_feasibility.csv', FA)
        csvout('E17_5_inputs.csv', IN)
    if 'b' in part:
        out, dis = [], []
        for r in IN:
            t0 = time.time()
            row = dict(r)
            for tag, a in [('dev', r['AUROC_dev']), ('cal', r['AUROC_cal'])]:
                dr = draws(np.random.default_rng(0), 2000, r['N_fit'], r['N_cal'], r['prevalence_cal'])
                P, mode, mc = summarize(*run(dr, r['prevalence_cal'], a, r['N_fit'], r['N_cal']))
                row.update({f'P_certify_{tag}AUROC': P, f'modal_q_{tag}AUROC': mode, f'median_coverage_when_certified_{tag}AUROC': mc,
                            f'predicted_{tag}AUROC': 'certify' if P >= .5 else 'fallback'})
                row[f'agree_{tag}AUROC'] = row[f'predicted_{tag}AUROC'] == r['observed']
            txt, val, steps = bisect(r['prevalence_cal'], r['N_fit'], r['N_cal'])
            row.update(AUROC_at_P50=txt, AUROC_at_P50_value=val, bisection_steps=';'.join(f'{a:.4f}:{p:.3f}' for a, p in steps), label=LABEL)
            out.append(row)
            print({k: (round(v, 4) if isinstance(v, float) else v) for k, v in row.items() if k not in ('label', 'bisection_steps')},
                  f'{time.time() - t0:.1f}s', flush=True)
        csvout('E17_5b_binormal.csv', out)
        for tag in ['dev', 'cal']:
            print(tag, 'agreement', sum(r[f'agree_{tag}AUROC'] for r in out), '/', len(out))
        v = [r['AUROC_at_P50_value'] for r in out if r['AUROC_at_P50_value'] is not None]
        print('AUROC at P=.5 range', min(v), max(v), 'n with value', len(v), 'contains .80:', min(v) <= .80 <= max(v))
    if 'c' in part:
        PREV = [.02, .03, .05, .075, .10, .15, .20, .30, .40, .50, .60]
        AUC = [.60, .65, .70, .75, .80, .85, .90, .95, .98]
        grid, cont = [], []
        for Nf, Nc in [(670, 448), (2100, 1366), (3000, 6000)]:
            t0 = time.time()
            for p in PREV:
                Ps = []
                for a in AUC:
                    dr = draws(np.random.default_rng(0), 1000, Nf, Nc, p)
                    P, mode, mc = summarize(*run(dr, p, a, Nf, Nc))
                    Ps.append(P)
                    grid.append(dict(N_fit=Nf, N_cal=Nc, prevalence=p, AUROC=a, P_certify=P, modal_q=mode, median_coverage_when_certified=mc, label=LABEL))
                # P = .5 contour along AUROC (linear interpolation between grid AUROCs, first upward crossing)
                if Ps[0] >= .5: c = f'<= {AUC[0]}'; cv = None
                else:
                    cv = None; c = f'> {AUC[-1]}'
                    for i in range(1, len(AUC)):
                        if Ps[i] >= .5:
                            cv = AUC[i - 1] + (.5 - Ps[i - 1]) * (AUC[i] - AUC[i - 1]) / (Ps[i] - Ps[i - 1]); c = f'{cv:.4f}'; break
                cont.append(dict(N_fit=Nf, N_cal=Nc, prevalence=p, AUROC_at_P50=c, AUROC_at_P50_value=cv, label=LABEL))
            print('grid', Nf, Nc, f'{time.time() - t0:.1f}s', flush=True)
        csvout('E17_5c_grid.csv', grid)
        csvout('E17_5c_contour.csv', cont)
