"""E20P Step 1: CODE_FREEZE.json (hashes of code, inputs, prompts) and PREREG_E20P.md (verbatim block + resolved revisions/hashes/choices),
then PREREG_E20P.sha256 (SHA-256 + UTC). Run once, before the first job."""
import json, hashlib, datetime, pathlib
S = pathlib.Path(__file__).resolve().parents[1]
assert not (S / 'PREREG_E20P.md').exists(), 'PREREG already written'
sha = lambda p: hashlib.sha256((S / p).read_bytes()).hexdigest()
utc = lambda: datetime.datetime.now(datetime.timezone.utc).isoformat()
files = sorted([str(p.relative_to(S)) for p in (S / 'src').glob('*.py')] + [str(p.relative_to(S)) for p in (S / 'jobs').glob('*')] +
               [str(p.relative_to(S)) for p in (S / 'inputs').glob('*')] +
               ['PROMPTS_E20.md', 'GATE.md', 'notes/DOWNLOAD_MANIFEST.json', 'notes/POOL_E20P.json', 'notes/PROMPT_CHECKS.json', 'notes/PREREG_BLOCK.txt'])
files = [f for f in files if f != 'src/write_prereg.py']
fz = dict(utc=utc(), files={f: sha(f) for f in files})
(S / 'notes/CODE_FREEZE.json').write_text(json.dumps(fz, indent=1) + '\n')
P = json.loads((S / 'notes/POOL_E20P.json').read_text())['datasets']
E17 = S.parent / 'P2_R7_E17_20260921T183100Z/scripts/e17_5.py'
L = ['# PREREG_E20P.md — E20-pilot (label-free), Paper A', '', f'Stage P2_R8_E20P_20260921T224653Z. Written {utc()}, before any E20 model output and '
     'before the first job. The block between the markers is verbatim from the task; everything after it is resolved detail.', '',
     '----- BEGIN PREREG BLOCK -----', (S / 'notes/PREREG_BLOCK.txt').read_text().rstrip('\n'), '----- END PREREG BLOCK -----', '',
     '## Resolved dataset revisions and pool / pilot hashes', '',
     '| dataset | repo @ revision | pool after filters + dedup | POOL_ORDER sha256 | PILOT sha256 |', '|---|---|---|---|---|']
for t, d in P.items():
    L.append(f"| {d['dataset']} | {d['repo']} @ `{d['revision']}` | {d['pool_after_dedup']:,} | `{d['POOL_ORDER']['sha256']}` | `{d['PILOT']['sha256']}` |")
L += ['', f"PROMPTS_E20.md sha256 `{sha('PROMPTS_E20.md')}`. GATE.md sha256 `{sha('GATE.md')}`. notes/CODE_FREEZE.json sha256 "
      f"`{sha('notes/CODE_FREEZE.json')}` (checked by every GPU rank at start-up; lists {len(files)} files).", '',
      f"Frozen E17-5 binormal code: P2_R7_E17_20260921T183100Z/scripts/e17_5.py sha256 `{hashlib.sha256(E17.read_bytes()).hexdigest()}` "
      '(= the value recorded in P2_R7_E16 E17_5_on_E16_5.json; asserted in src/e20_analyze.py).', '',
      'Models: helper Qwen/Qwen2.5-7B-Instruct @ a09a35458c702b33eeacc393d103063234e8bc28; receivers Qwen/Qwen3-8B @ b968826d9c46dd6066d109eabc6255188de91218',
      'and meta-llama/Llama-3.1-8B-Instruct @ 0e9e39f249a16976918f6564b8830bc894c89659 (X3 copy; chat template sha256 e10ca381...4d4b65).', '',
      '## Code hashes', '', '| file | sha256 |', '|---|---|'] + [f'| {f} | `{h}` |' for f, h in fz['files'].items() if f.startswith(('src/', 'jobs/'))]
L += ['', '## Implementation choices where the block leaves a detail open (fixed in the hashed code before any output)', '',
      '1. Prompts (PROMPTS_E20.md, src/e20_prompts.py): from the frozen MC receiver prompt, R1 options block removed; R2 "and all options" removed;',
      '   R3 the answer-format bullet replaced by the task instruction; R4 the trailing MC cue "The correct answer is" removed; R5 passage datasets:',
      '   "Passage:\\n<passage>\\n\\n" before the question. Helper: BACKGROUND_PROMPT unchanged, body = question (+ the same passage block).',
      '   Receiver-with-message = frozen 3-turn Text structure. Receiver ids = tokenizer(rendered, add_special_tokens=False) (identical to',
      '   apply_chat_template(tokenize=True) on all 1,600 pilot prompts; Llama 1 BOS). Generations decoded with skip_special_tokens=True,',
      '   clean_up_tokenization_spaces=False on both paths and both receivers; helper decoding as the frozen T2THelperBundle.',
      '2. Pool: markup tokens = whitespace-separated tokens matching </?[A-Za-z][A-Za-z0-9]*> (MRQA only); normalized question for dedup =',
      '   e20_extract.normalize_text (NFKD accents removed + SQuAD normalization); prompt question = raw question .strip();',
      '   SHA string "<dataset>|<id>" with dataset in {SQuAD, NQ-passage, TriviaQA, NQ-Open}; ties by file row.',
      '3. Extraction = e20_extract.extract (literal implementation; the official SQuAD normalization removes ASCII punctuation only, so e.g. curly',
      '   quotes survive). Words = whitespace tokens of the normalized answer; INVALID = 0 words.',
      '4. Scores: raw logits = generate(output_logits=True) (float32 copy of the bf16 model logits before any logits processor) -> float64;',
      '   1 - max p = sum of softmax over all non-argmax ids. Token text = decode([id], skip_special_tokens=False). Special ids (tokenizer special',
      '   ids, special added tokens, generation EOS ids) never start s1/s2 and end the s2 span. If no qualifying token exists the score is 1.0',
      '   (flagged). argmax != chosen token is counted per row (expected 0).',
      '5. Smoke (first 8 pilot questions per dataset, receiver-only): a dataset is dropped if, for either receiver, INVALID > 2/8 or the median',
      '   answer words > 10. Projection = elapsed + measured load times + worst case (256 helper + 4 x 32 receiver tokens per question) at the',
      '   measured decode rates, for the largest shard; > 45 min -> first 300 pilot questions per dataset in that job (deviation).',
      '6. Statistics (src/e20_analyze.py docstring): AUROC with average ranks; paired bootstrap, percentile interval; lowest 10/25/50% = the',
      "   paper's order-statistic threshold on the pilot scores with ties kept; Clopper-Pearson upper bound = two-sided 95%; E17-5(a) over the 20",
      '   pilot-quantile candidates; missing / runtime-error rows excluded and counted; if d = 0 or 1 there is no AUROC, no prediction, and the',
      '   setting cannot be ranked; expected coverage = N/A (the frozen code returns median coverage when certified, reported separately).',
      '7. Step 6 aliases: SQuAD answers.text; MRQA answers; TriviaQA answer.value + aliases + normalized_aliases; NQ-Open answer.',
      '', '## Job plan', '',
      'ClusterA debug, 2 jobs x (select=2, 4 A100 40GB per node, walltime 00:55:00): job A = SQuAD + NQ-passage (rank 0: preflight 16 OBQA',
      'large-pair rows + 16 X3 Llama rows bitwise, smoke, GATE), job B = TriviaQA + NQ-Open (preflight skipped if job A PASSED; smoke, GATE).',
      'All ranks: helper -> Qwen3-8B (R, T) -> Llama-3.1-8B (R, T), 100 questions per GPU. Gold is not read before SELECTION_E20P.json is hashed.']
(S / 'PREREG_E20P.md').write_text('\n'.join(L) + '\n')
h = hashlib.sha256((S / 'PREREG_E20P.md').read_bytes()).hexdigest()
(S / 'PREREG_E20P.sha256').write_text(f'{h}  PREREG_E20P.md\nhashed_utc: {utc()}\n')
print((S / 'PREREG_E20P.sha256').read_text())
