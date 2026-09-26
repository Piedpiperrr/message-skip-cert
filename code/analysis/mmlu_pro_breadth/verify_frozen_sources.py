import sys
from pathlib import Path
sys.dont_write_bytecode=True
sys.path.insert(0,str(Path(__file__).resolve().parent/'src'))
from common import *
v4=ROOT/'P2_SUBMISSION_MANUSCRIPT_V4_MEDIUM_INTEGRATION_20260915T213129Z'
checks=[]
for old in read(REVIEW/'evidence/V4_FROZEN_CHECKSUM_VERIFICATION.json'):
    path=v4/old['file'];actual=sha(path)
    checks.append(dict(path=str(path),expected=old['expected'],actual=actual,match=actual==old['expected']))
for old in read(REVIEW/'evidence/SELECTED_FROZEN_SCIENCE_CHECKSUMS.json'):
    actual=sha(old['path']);checks.append(dict(path=old['path'],expected=old['expected'],actual=actual,match=actual==old['expected']))
for name in ['MANIFEST.json','fit_ids.json','cal_ids.json','dev_ids.json','fit_groups.json','cal_groups.json','dev_groups.json','candidate_e2e128_ids.json','STAGE1_CANDIDATE_SHARDS.json']:
    path=REVIEW/'candidates/PLAN_C'/name;actual=sha(path);expected=sha(P/'splits'/name)
    checks.append(dict(path=str(path),expected=expected,actual=actual,match=actual==expected))
validate_freeze()
save(P/'evidence/FROZEN_SOURCE_VERIFICATION.json',dict(utc=utc(),status='PASS' if all(r['match'] for r in checks) else 'FAIL',checks=checks,
    formal_freeze_sha256=sha(P/'MMLU_PRO_STAGE1_PROTOCOL_FREEZE.json')))
assert all(r['match'] for r in checks)
print('FROZEN_SOURCES_PASS',len(checks))
