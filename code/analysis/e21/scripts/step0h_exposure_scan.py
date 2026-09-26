"""E21 Step 0 (h): exposure search. Walk every earlier P2_* folder under the project root (not this stage), read result-type text files
(.csv .json .md .txt .tex, <= 5 MB; raw model-record .jsonl files and model/tokenizer/dataset folders skipped), and list every file whose text
contains a lost-correction / correction-decomposition keyword, with the matching lines that also mention calibration. The hits are then
classified by hand in REPRO.md (h)."""
import os, re, json, sys, datetime
STAGE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(STAGE)
KW = re.compile(r'corrections_lost|lost_correct|lost correction|lost-correction|corrections lost|reference_corrects|reference_breaks|'
                r'corrective|harmful|corrections_kept|lost_gain|gain_lost|corrections_total|lost corrections', re.I)
CAL = re.compile(r'\bcal\b|cal_|calibration', re.I)
SKIP_DIR = {'assets', 'hf_cache', 'models', 'dataset', 'datasets', '__pycache__', 'pydeps', 'eval_out'}
EXT = ('.csv', '.json', '.md', '.txt', '.tex')
t0 = datetime.datetime.now(datetime.timezone.utc).isoformat()
hits, nfiles = [], 0
for d in sorted(os.listdir(ROOT)):
    p = os.path.join(ROOT, d)
    if not os.path.isdir(p) or os.path.abspath(p) == STAGE:
        continue
    for dp, dns, fns in os.walk(p):
        dns[:] = [x for x in dns if x not in SKIP_DIR]
        for fn in fns:
            if not fn.endswith(EXT) or fn in ('vocab.json', 'tokenizer.json', 'merges.txt', 'tokenizer_config.json'):
                continue
            fp = os.path.join(dp, fn)
            try:
                if os.path.getsize(fp) > 5_000_000:
                    continue
                with open(fp, errors='replace') as f:
                    txt = f.read()
            except Exception:
                continue
            nfiles += 1
            if not KW.search(txt):
                continue
            lines = txt.splitlines()
            hl = [ln for ln in lines if KW.search(ln)]
            hits.append(dict(file=os.path.relpath(fp, ROOT), n_hit_lines=len(hl), header=(lines[0] if lines else '')[:400],
                             header_mentions_cal=bool(CAL.search(lines[0])) if lines else False,
                             hit_lines_mentioning_cal=[ln[:400] for ln in hl if CAL.search(ln)][:8], first_hits=[ln[:400] for ln in hl[:4]]))
out = os.path.join(STAGE, 'results', 'step0h_exposure_hits.json')
json.dump(dict(start_utc=t0, end_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), files_scanned=nfiles, keyword_regex=KW.pattern,
               hits=hits), open(out, 'w'), indent=1)
print('files scanned', nfiles, 'files with hits', len(hits))
