"""E20F Step 1: notes/CODE_FREEZE_E20F.json and PREREG_E20F.md (verbatim block + resolved hashes), then PREREG_E20F.sha256. Run once, before job 1."""
import json, hashlib, pathlib, datetime
S = pathlib.Path(__file__).resolve().parents[1]
assert not (S / 'PREREG_E20F.md').exists(), 'PREREG_E20F.md already written'
assert not (S / 'records').exists() or not any((S / 'records').rglob('*.jsonl')), 'E20-full outputs already exist'
sha = lambda p: hashlib.sha256((S / p).read_bytes()).hexdigest()
utc = lambda: datetime.datetime.now(datetime.timezone.utc).isoformat()
rel = lambda g: sorted(str(p.relative_to(S)) for p in S.glob(g))
files = [f for f in rel('src/*.py') if f != 'src/write_prereg_e20f.py'] + rel('jobs/*') + rel('inputs/FULL_*.jsonl') + rel('pool/src/*.py') + \
    ['pool/notes/DOWNLOAD_MANIFEST.json', 'pool/inputs/POOL_ORDER_squad.txt', 'notes/SPLITS_E20F.json', 'notes/G1_VERIFY.json', 'notes/G4_CERT_REPRO.json',
     'notes/G3_GREP_run3_status.txt', 'notes/G3_GREP_HITS_run3.txt', 'notes/PREREG_BLOCK_E20F.txt', 'GATE.md', 'CODE_DIFF.patch']
fz = dict(utc=utc(), files={f: sha(f) for f in files})
(S / 'notes/CODE_FREEZE_E20F.json').write_text(json.dumps(fz, indent=1) + '\n')
P = S.parent / 'P2_R8_E20P_20260921T224653Z'
psha = lambda p: hashlib.sha256((P / p).read_bytes()).hexdigest()
sp = json.loads((S / 'notes/SPLITS_E20F.json').read_text())['splits']
L = ['# PREREG_E20F.md — E20-full (Paper A)', '', f'Stage P2_R8_E20F_20260922T003652Z. Written {utc()}, before any E20-full output and before job 1. The block between',
     'the markers is verbatim from the task; everything after it is resolved detail.', '', '----- BEGIN PREREG BLOCK -----',
     (S / 'notes/PREREG_BLOCK_E20F.txt').read_text().rstrip('\n'), '----- END PREREG BLOCK -----', '', '## Resolved hashes', '',
     f"- Pilot: PREREG_E20P.md `{psha('PREREG_E20P.md')}`; SELECTION_E20P.json `{psha('SELECTION_E20P.json')}`; PROMPTS_E20.md `{psha('PROMPTS_E20.md')}`;",
     f"  notes/CODE_FREEZE.json `{psha('notes/CODE_FREEZE.json')}` (27 files, all verified: notes/G1_VERIFY.json; re-checked by every GPU rank).",
     '- Helper Qwen/Qwen2.5-7B-Instruct @ a09a35458c702b33eeacc393d103063234e8bc28; receiver meta-llama/Llama-3.1-8B-Instruct @ 0e9e39f249a16976918f6564b8830bc894c89659.',
     f"- SQuAD rajpurkar/squad @ 7b6d24c440a36b6815f21b70d25016731768db1f; pool 86,830; POOL_ORDER_squad.txt `{sha('pool/inputs/POOL_ORDER_squad.txt')}` (= pilot).",
     '- Splits (id, question, passage only): ' + '; '.join(f"{k} {v['n']} `{v['sha256']}`" for k, v in sp.items()) + '.',
     f"- Certification functions: common_r1.py / data_r1.py / analyze_x3.py ledger_rows (hashes in notes/G4_CERT_REPRO.json), wrapper src/e20f_cert.py `{sha('src/e20f_cert.py')}`;",
     '  X3 OBQA reproduction q = .60, 21/800, p = 5.735e-4 (PASS). Frozen E17-5 binormal code e17_5.py `ef1537c7289b30d7a0adfe5b9180fc9a53a35bf6cb6aba1021ebf6759dde2b6b`.',
     f"- DEVIATIONS.md at PREREG time `{sha('DEVIATIONS.md')}`. GATE.md `{sha('GATE.md')}`; CODE_DIFF.patch `{sha('CODE_DIFF.patch')}`; notes/CODE_FREEZE_E20F.json `{sha('notes/CODE_FREEZE_E20F.json')}` ({len(files)} files,",
     '  checked by every GPU rank at start-up).', '', '## Full-run scripts and job scripts', '', '| file | sha256 |', '|---|---|'] + \
    [f'| {f} | `{h}` |' for f, h in fz['files'].items() if f.startswith(('src/', 'jobs/', 'pool/src/'))]
L += ['', '## Implementation choices where the block leaves a detail open (fixed in the hashed code before any output)', '',
      '1. Preflight (every job, rank 0): the first 16 pilot SQuAD questions (PILOT_squad.jsonl) through src/e20f_exec.py; PASS iff for all 16 the helper',
      '   token IDs, receiver-only and receiver-with-message token IDs, and s1/s2/s3 of both paths equal the pilot rows (results/E20P_jobA_rows.jsonl).',
      '2. Continuation: rank 0 writes PLAN_j<PBS job number>.json; every question of the phase without an error-free receiver row is assigned',
      '   round-robin; a question counts once (first error-free row). Certification and statistics require every question of their splits.',
      '3. CERT: src/e20f_cert_run.py; always-omit change rate = the q = 1 row; TPR/FPR vs C as in E17-5(a) over the 20 candidates; needed N_cal',
      '   (fallback only) = the E5-b needed_m rule (verbatim from analyze_e16_5.py).',
      '4. Stats: src/e20f_stats.py docstring (AUROC = explicit Mann-Whitney ties 1/2; bootstrap default_rng(0), 2,000, percentile; binormal with',
      '   the pilot settings N_fit 500, 1,000 simulations, seed 0; surface / length / test / re-split / value definitions). A test that is not',
      '   complete is reported as incomplete (rule 7).',
      '5. Gold: src/e20f_gold.py (SQuAD answers.text; paired bootstrap default_rng(0), 2,000; corrections / breakages among all changes and among',
      '   omitted changes); RESULTS_E20F.md and the writing-rule branch: src/e20f_results.py.']
(S / 'PREREG_E20F.md').write_text('\n'.join(L) + '\n')
h = hashlib.sha256((S / 'PREREG_E20F.md').read_bytes()).hexdigest()
(S / 'PREREG_E20F.sha256').write_text(f'{h}  PREREG_E20F.md\nhashed_utc: {utc()}\n')
print((S / 'PREREG_E20F.sha256').read_text()); print(len(files), 'files frozen')
