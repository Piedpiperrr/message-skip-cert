import json,sys
from common_p2_10 import ROOT,sha,utc,freeze
assert json.loads((ROOT/'evidence/implementation_checks.json').read_text())['passed']
cfg=json.loads((ROOT/'prepared_config.json').read_text())
cfg['frozen_utc']=utc()
cfg['user_prompt']={'path':str(ROOT/'USER_EXECUTION_PROMPT.md'),'sha256':sha(ROOT/'USER_EXECUTION_PROMPT.md'),'format':'user request archived with normalized Markdown layout'}
cfg['timing']={'start':'synchronize GPU0/1, then timer before raw query copy/templates/tokenization','end':'after full receiver generation and both GPU synchronizations','exclude':'loading, offline W training, authoritative scoring, logging, extra tensor diagnostics','threading':{'torch':4,'OMP_NUM_THREADS':4,'MKL_NUM_THREADS':1,'OPENBLAS_NUM_THREADS':1},'residency':'helper BF16 + standalone semantic FP32 on cuda:0; receiver/fuser BF16 + W FP32 cuda:1; same residency across R/T/C/A','legacy_wrapper_unused_parser':'disabled; frozen dataset scoring outside timer','AC_diagnostics':'production captures block output and injects full hidden once; finite reductions and hook-cleanup checks outside request timer'}
cfg['large_W']['recovery']={'activation_cache':'32-sentence atomic chunks, no re-extraction of successful chunks','training_checkpoint':'atomic W/Adam/RNG/step/epoch/cursor/order after every update; final committed step 960 only','checkpoint_path':str(ROOT/'results/large/W/training_state.pt'),'final_path':str(ROOT/'results/large/W/W_final.pt')}
names=['common_p2_10.py','run_p2_10.py','ac_p2_10.py','router_p2_10.py','runtime.py','legacy_methods.py','protocol_min.py','scoring.py','query_features.py','arc_protocol.py','arc_runtime_adapter.py']
names += [str(p.relative_to(ROOT)) for p in sorted((ROOT/'runtime_source').rglob('*.py'))]
cfg['execution_source_sha256']={n:sha(ROOT/n) for n in names}
cfg['pre_submission_source_sha256']={p.name:sha(p) for p in ROOT.glob('*.py')}
freeze(ROOT/'frozen_config.json',cfg)
freeze(ROOT/'evidence/freeze_receipt.json',{'utc':utc(),'config_sha256':sha(ROOT/'frozen_config.json'),'user_prompt_sha256':sha(ROOT/'USER_EXECUTION_PROMPT.md'),'cpu_preparation_sha256':sha(ROOT/'evidence/cpu_preparation.json'),'implementation_checks_sha256':sha(ROOT/'evidence/implementation_checks.json'),'immutable':True})
print(json.dumps({'FROZEN':cfg['frozen_utc'],'config_sha256':sha(ROOT/'frozen_config.json'),'requests':15860}))
