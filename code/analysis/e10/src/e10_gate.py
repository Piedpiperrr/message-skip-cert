"""Aggregate the per-rank preflight and smoke results and decide whether main may run.
Refuse if any stored OBQA row failed to reproduce, or if INVALID > 2/16 on either receiver path."""
import json, sys, glob
from pathlib import Path
STAGE = Path(__file__).resolve().parents[1]
REC = STAGE / 'records'
pre = [json.loads(Path(p).read_text()) for p in sorted(glob.glob(str(REC / 'preflight_rank*.json')))]
sm = [json.loads(Path(p).read_text()) for p in sorted(glob.glob(str(REC / 'smokecheck_rank*.json')))]
mis = {a: sum(r['per_action'][a]['mismatches'] for r in pre) for a in ['R', 'T']}
n = {a: sum(r['per_action'][a]['n'] for r in pre) for a in ['R', 'T']}
iR = sum(r['invalid_R'] for r in sm); iT = sum(r['invalid_T'] for r in sm)
nsm = sum(len(r['ids']) for r in sm)
ok = all(r['PASS'] for r in pre) and mis['R'] == 0 and mis['T'] == 0 and iR <= 2 and iT <= 2
rep = {'ranks_preflight': len(pre), 'ranks_smoke': len(sm),
       'obqa_rows_checked': n, 'obqa_mismatches': mis,
       'smoke_questions': nsm, 'smoke_invalid_R': iR, 'smoke_invalid_T': iT,
       'empty_helper_messages': sum(r['empty_helper_message'] for r in sm),
       'gen_tokens_R': [x for r in sm for x in r['n_gen_tokens_R']],
       'gen_tokens_T': [x for r in sm for x in r['n_gen_tokens_T']],
       'rescore_check': [c for r in sm for c in r['rescore_vs_generation']],
       'criterion': 'all 16 stored OBQA rows reproduce bit for bit on both paths; INVALID <= 2/16 '
                    'on receiver-only and on Text',
       'GATE_PASS': bool(ok), 'gold_read': False}
(REC / 'GATE.json').write_text(json.dumps(rep, indent=2) + '\n')
g = rep['gen_tokens_R'] + rep['gen_tokens_T']
print('GATE pass=%s obqa_mismatch=%s invalid R=%d T=%d n=%d  gen_tokens mean=%.0f max=%d' %
      (ok, mis, iR, iT, nsm, (sum(g) / len(g)) if g else -1, max(g) if g else -1))
sys.exit(0 if ok else 5)
