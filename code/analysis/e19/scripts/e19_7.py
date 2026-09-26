"""E19-7: other receivers. Search every project directory (excluding this stage) for Mistral / Granite model identifiers and for any
receiver / model field value other than the known models; classify every hit. grep is used for speed (read-only)."""
from e19_common import *
import subprocess, collections, re

T0 = utc()
print('E19-7 start', T0)
INC = ['--include=*.jsonl', '--include=*.json', '--include=*.csv', '--include=*.md', '--include=*.txt', '--include=*.log',
       '--include=*.tsv', '--include=*.yaml', '--include=*.yml']
EXC = [f'--exclude-dir={STAGE.name}']


def grep(args):
    r = subprocess.run(['grep', '-rI'] + EXC + INC + args + ['.'], cwd=ROOT, capture_output=True, text=True)
    return [l for l in r.stdout.splitlines() if l]


# (1) broad word search (counts only; the words also occur in question text: granite = a rock, mistral = a wind)
broad = sorted(set(grep(['-li', '-e', 'mistral', '-e', 'granite'])))
# (2) model-identifier patterns
MID = r'mistralai|mistral[-_ ]?7b|mistral[-_]instruct|ibm-granite|granite[-_ ]?[0-9]|granite[-_]instruct|granite[-_]code'
files = sorted(set(grep(['-liE', MID])))
HITS = []
for f in files:
    p = ROOT / f
    lines = subprocess.run(['grep', '-inE', MID, str(p)], capture_output=True, text=True).stdout.splitlines()
    ex = lines[0][:300] if lines else ''
    fl = f.lower()
    if 'download' in fl or 'manifest' in fl:
        kind = 'download manifest / access log'
    elif 'step0' in fl or 'template_check' in fl or 'receiver_check' in fl:
        kind = 'tokenizer/template check (X3 Step 0; not a model output)'
    elif f.endswith(('.md', '.txt')) or 'notes' in fl or 'prereg' in fl or 'readme' in fl:
        kind = 'text mention (plan / notes / report)'
    elif 'logs' in fl or f.endswith('.log'):
        kind = 'log'
    else:
        kind = 'OTHER - inspect'
    HITS.append(dict(file=f, n_matching_lines=len(lines), kind=kind, first_match=ex))
# (3) every receiver / model identifier field value in jsonl/json/csv records
FIELD = r'"(receiver|receiver_model|receiver_id|model|model_id|model_name|repo_id|repo|helper|helper_model)" *: *"[^"]{1,120}"'
vals = collections.Counter()
where = collections.defaultdict(set)
r = subprocess.run(['grep', '-rIohE'] + EXC + ['--include=*.jsonl', '--include=*.json', FIELD, '.'], cwd=ROOT, capture_output=True, text=True)
for m in r.stdout.splitlines():
    vals[m] += 1
r2 = subprocess.run(['grep', '-rIlE'] + EXC + ['--include=*.jsonl', '--include=*.json', FIELD, '.'], cwd=ROOT, capture_output=True, text=True)
VALS = [dict(field_value=k, count=v) for k, v in sorted(vals.items(), key=lambda x: -x[1])]
KNOWN = re.compile(r'qwen|llama|olmo|fuser|c2c|gpt2|t5|bert|none|null|true|false|^"(model|repo|helper)" *: *"(R|T|C|TF|text|c2c|receiver_only|large|medium|small)"', re.I)
unknown = [v for v in VALS if not KNOWN.search(v['field_value'])]
# receiver field values specifically
recv = collections.Counter()
for k, v in vals.items():
    if k.startswith('"receiver"'):
        recv[k] += v
# (4) model directories in the HF cache and project assets
EAG = Path('$DATA_DIR')
hub = sorted(p.name for p in (EAG / 'hf_cache/hub').glob('models--*'))
# (5) any Mistral receiver output: X3 records with receiver != llama31_8b, and any chain/run records with a mistral receiver
x3recv = collections.Counter()
for f in sorted((X3 / 'results').rglob('*.jsonl')):
    for line in open(f):
        m = re.search(r'"receiver": *"([^"]+)"', line)
        if m: x3recv[(str(f.relative_to(ROOT)), m.group(1))] += 1
mistral_outputs = [dict(file=k[0], receiver=k[1], rows=v) for k, v in x3recv.items() if 'llama' not in k[1] and 'qwen' not in k[1]]
SUM = dict(broad_word_hits_files=len(broad), model_identifier_hit_files=len(files),
           model_identifier_hits_by_kind=json.dumps(collections.Counter(h['kind'] for h in HITS)),
           receiver_field_values=json.dumps(dict(recv)), unknown_model_field_values=json.dumps([v['field_value'] for v in unknown][:50]),
           hf_cache_models=';'.join(hub), x3_nonllama_receiver_rows=json.dumps(mistral_outputs),
           other_receiver_outputs='none' if (not mistral_outputs and not any(h['kind'] == 'OTHER - inspect' for h in HITS)) else 'see rows',
           label=LABEL)
for h in HITS: print(h['kind'], '|', h['file'], '|', h['first_match'][:160])
print('receiver values', dict(recv))
print('unknown field values', [v['field_value'] for v in unknown][:40])
print('hf cache', hub)
print('x3 receivers', dict(x3recv))
csvout('E19_7_model_identifier_hits.csv', HITS or [dict(file='none')])
csvout('E19_7_field_values.csv', VALS)
csvout('E19_7_broad_word_hit_files.csv', [dict(file=f) for f in broad])
csvout('E19_7_summary.csv', [SUM])
json.dump(dict(start_utc=T0, end_utc=utc()), open(STAGE / 'logs/e19_7_run.json', 'w'), indent=1)
print(SUM)
print('E19-7 done', utc())
