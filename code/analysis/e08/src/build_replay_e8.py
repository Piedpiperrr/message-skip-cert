"""Builds the E8 replay from the frozen MMLU-Pro replay driver, for whichever E8 policies deployed.
Run on the login node after analyze_e8.py. Writes REPLAY_E8/ and its freeze; no GPU, no gold."""
from common_e8 import *
import shutil
S2=ROOT/'P2_MMLU_PRO_E2E_STAGE2_20260916T212147Z'
R=P/'REPLAY_E8'
dep=read(P/'analysis/deployments/deployment_configs.json')['deployments']
deployed={k:v for k,v in dep.items() if v['q']>0}
if not deployed:
    save(P/'REPLAY_NOT_REQUIRED.json',dict(utc=utc(),reason='no E8 setting deployed; every setting fell back',
        deployments={k:v['q'] for k,v in dep.items()},replay_jobs=0))
    print('NO_DEPLOYMENT: no replay',flush=True);raise SystemExit(0)
R.mkdir(exist_ok=True);(R/'inputs').mkdir(exist_ok=True);(R/'protocol').mkdir(exist_ok=True)
for f in ['panel_queries.jsonl','candidate_e2e128_ids.json']:
    shutil.copy2(S2/'inputs'/f,R/'inputs'/f)
panel=rows(R/'inputs/panel_queries.jsonl');pids=read(R/'inputs/candidate_e2e128_ids.json')
assert [r['id'] for r in panel]==pids==read(P/'splits/candidate_e2e128_ids.json') and len(pids)==128
byp={}
for k,v in deployed.items():
    pair,ref=k.split('/');byp.setdefault(pair,[]).append('T' if ref=='Text' else 'C')
arms={};sched={}
for pair,refs in byp.items():
    refs=[r for r in ['T','C'] if r in refs]
    A=[a for r in refs for a in (f'fixed_{r}',f'policy_{r}')]
    arms[pair]=A
    sched[pair]=[dict(ordinal=i,id=ident,arms=A[i%len(A):]+A[:i%len(A)]) for i,ident in enumerate(pids)]
    save(R/f'protocol/SCHEDULE_{pair}.json',sched[pair])
    for pos in range(len(A)):
        c=[s['arms'][pos] for s in sched[pair]]
        assert all(c.count(a)==128//len(A) for a in A),(pair,pos)
freeze=dict(utc=utc(),stage=str(R),protocol='E3 replay protocol on the frozen 128-question MMLU-Pro panel: '
    'fixed reference vs policy, rotated left by question ordinal, no warm-up, cold requests kept, batch 1, '
    'versions (a) all 128 questions and (b) dropping the questions on which either compared arm made its '
    'first formal request; class + / - / ? from the 95% paired bootstrap interval. Only the class is reported; '
    'it is not compared with the original hardware.',
    source_driver=str(S2/'src/execute.py'),source_driver_sha256=sha(S2/'src/execute.py'),
    panel_sha256=sha(R/'inputs/panel_queries.jsonl'),panel_equals_E8_candidate_ids=True,
    policies={k:dict(pair=k.split('/')[0],reference=k.split('/')[1],q=v['q'],threshold=v['threshold'],mode=v['mode'])
              for k,v in deployed.items()},
    arms=arms,requests_per_pair={p:128*len(a) for p,a in arms.items()},
    probes_per_pair={p:128*(len(a)//2) for p,a in arms.items()},
    bootstrap=dict(seed=0,resamples=2000,unit='question-level paired fixed-minus-policy latency',
        interval='numpy.quantile([.025,.975]) percentile 95%'),
    protocol_freeze_E8_sha256=freeze_hash(),
    deployment_configs_sha256=sha(P/'analysis/deployments/deployment_configs.json'),
    gold_read=False)
save(R/'REPLAY_FREEZE_E8.json',freeze)
# one MPI rank per deploying pair; rank 0 -> GPUs 0,1 and rank 1 -> GPUs 2,3 on the same node
for rank,pair in enumerate(sorted(arms)):
    refs=','.join(r for r in ['T','C'] if f'fixed_{r}' in arms[pair])
    (R/f'protocol/RANK_{rank}.env').write_text(f'E8_FORCE_PAIR={pair}\nE8_REPLAY_REFS={refs}\n')
(R/'protocol/NRANKS').write_text(f'{len(arms)}\n')
print('REPLAY_BUILT pairs=',list(arms),'arms=',arms,'requests=',freeze['requests_per_pair'],flush=True)
