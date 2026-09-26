"""X3 Step 1: fill the three bracketed fields of the verbatim preregistration block (notes/PREREG_BLOCK_TEMPLATE.txt), write PREREG_X3.md,
then PREREG_X3.sha256 (line 1: sha256sum format; line 2: UTC) and jobs/receiver.env. Refuses if any X3 model output exists.
usage: write_prereg.py <receiver tag: llama31_8b | mistral7b_v03> <reason text>"""
import sys
sys.dont_write_bytecode = True
from xfam_common import *
tag, reason = sys.argv[1], sys.argv[2]
assert tag in ('llama31_8b', 'mistral7b_v03') and not (X / 'PREREG_X3.md').exists()
outs = [p for d in ['results/validation', 'results/smoke', 'results/runs'] for p in (X / d).glob('*') if (X / d).exists()]
assert not outs, outs
man = read(X / f'manifests/DOWNLOAD_{tag}.json'); assert man['all_ok'] and man['revision'] == RECEIVERS[tag]['revision']
t = (X / 'notes/PREREG_BLOCK_TEMPLATE.txt').read_text()
for old, new in [('[model id]', RECEIVERS[tag]['repo']), ('[commit hash]', RECEIVERS[tag]['revision']), ('[reason any earlier option was skipped, or "first choice"]', reason)]:
    assert t.count(old) == 1; t = t.replace(old, new)
(X / 'PREREG_X3.md').write_text(t)
h = sha(X / 'PREREG_X3.md'); now = utc()
(X / 'PREREG_X3.sha256').write_text(f'{h}  PREREG_X3.md\n# utc={now}\n')
(X / 'jobs/receiver.env').write_text(f'X3_RECEIVER={tag}\nX3_PYTHONPATH={str(X / "pydeps") if tag == "mistral7b_v03" else ""}\n')
print('PREREG', h, now, 'receiver', tag, 'no X3 outputs existed:', not outs)
