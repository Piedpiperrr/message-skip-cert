"""E20P G2 (login node, no model): pool construction and pilot sampling. Answer columns are never read (pyarrow column projection).

Per dataset: item id = dataset id field (SQuAD 'id', MRQA 'qid', TriviaQA 'question_id'); NQ-Open (no id field) = SHA-256 hex of the raw
question string. Passage datasets: MRQA markup tokens (whitespace-separated tokens matching </?[A-Za-z][A-Za-z0-9]*>) are removed and the
remaining tokens joined with single spaces (NQ-passage); SQuAD passage = context.strip(); keep items whose passage has <= 300
whitespace-separated words. Order by SHA-256 of "<dataset>|<item id>" (dataset = SQuAD, NQ-passage, TriviaQA, NQ-Open; ties by file row);
remove duplicates by normalized question text (passage datasets: by (passage, normalized question)), keeping the first copy in this order;
normalized = e20_extract.normalize_text. Prompt question = raw question .strip(). Pilot = first 400 of the pool.
Writes inputs/POOL_ORDER_<tag>.txt (ids in order), inputs/PILOT_<tag>.jsonl (id, question, passage only), notes/POOL_E20P.json.
"""
import sys, json, re, hashlib, datetime, pathlib
sys.dont_write_bytecode = True
import pyarrow as pa
pa.set_cpu_count(1); pa.set_io_thread_count(1)
import pyarrow.parquet as pq
HERE = pathlib.Path(__file__).resolve().parent; STAGE = HERE.parent
sys.path.insert(0, str(HERE))
from e20_extract import normalize_text

MAN = json.loads((STAGE / 'notes/DOWNLOAD_MANIFEST.json').read_text())
NAME = {'squad': 'SQuAD', 'nqp': 'NQ-passage', 'triviaqa': 'TriviaQA', 'nqopen': 'NQ-Open'}
COLS = {'squad': ['id', 'question', 'context'], 'nqp': ['subset', 'qid', 'question', 'context'],
        'triviaqa': ['question_id', 'question'], 'nqopen': ['question']}
MARKUP = re.compile(r'</?[A-Za-z][A-Za-z0-9]*>')
MAXW, NPILOT = 300, 400


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 22), b''): h.update(b)
    return h.hexdigest()


def sh(s): return hashlib.sha256(s.encode('utf-8')).hexdigest()


def load(tag):
    rows, fr = [], 0
    for fn in sorted(MAN[tag]['files']):
        v = MAN[tag]['files'][fn]; assert sha(v['path']) == v['sha256'], fn
        t = pq.read_table(v['path'], columns=COLS[tag], use_threads=False).to_pylist()
        for x in t:
            x['_row'] = fr; fr += 1
            if tag != 'nqp' or x['subset'] == 'NaturalQuestionsShort': rows.append(x)
        del t
    return rows, fr


out = {'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'columns_read': COLS, 'gold_read': False, 'datasets': {}}
for tag in ['squad', 'nqp', 'triviaqa', 'nqopen']:
    rows, nraw = load(tag)
    st = dict(dataset=NAME[tag], repo=MAN[tag]['repo'], revision=MAN[tag]['revision'], split='train', raw_rows=nraw)
    items = []
    if tag == 'nqp':
        st['rows_subset_NaturalQuestionsShort'] = len(rows)
    for x in rows:
        if tag == 'squad': iid, psg = x['id'], x['context'].strip()
        elif tag == 'nqp': iid, psg = x['qid'], ' '.join(t for t in x['context'].split() if not MARKUP.fullmatch(t))
        elif tag == 'triviaqa': iid, psg = x['question_id'], None
        else: iid, psg = sh(x['question']), None
        items.append(dict(id=iid, question=x['question'].strip(), passage=psg, _row=x['_row'], _key=sh(f'{NAME[tag]}|{iid}')))
    st['distinct_ids_before_filter'] = len({i['id'] for i in items})
    if tag in ('squad', 'nqp'):
        items = [i for i in items if len(i['passage'].split()) <= MAXW]; st['after_length_filter'] = len(items)
    items.sort(key=lambda i: (i['_key'], i['_row']))
    seen, pool = set(), []
    for i in items:
        k = (i['passage'], normalize_text(i['question'])) if i['passage'] is not None else normalize_text(i['question'])
        if k in seen: continue
        seen.add(k); pool.append(i)
    assert len({i['id'] for i in pool}) == len(pool), 'duplicate ids survive dedup'
    st['pool_after_dedup'] = len(pool); st['removed_as_duplicates'] = len(items) - len(pool)
    po = STAGE / f'inputs/POOL_ORDER_{tag}.txt'; po.write_text(''.join(i['id'] + '\n' for i in pool))
    pl = STAGE / f'inputs/PILOT_{tag}.jsonl'
    with open(pl, 'w') as f:
        for i in pool[:NPILOT]:
            f.write(json.dumps(dict(id=i['id'], question=i['question'], passage=i['passage']), ensure_ascii=False) + '\n')
    st.update(pilot_n=min(NPILOT, len(pool)), POOL_ORDER=dict(path=str(po.relative_to(STAGE)), sha256=sha(po)),
              PILOT=dict(path=str(pl.relative_to(STAGE)), sha256=sha(pl)),
              pilot_passage_words=None if tag in ('triviaqa', 'nqopen') else dict(
                  max=max(len(i['passage'].split()) for i in pool[:NPILOT]), min=min(len(i['passage'].split()) for i in pool[:NPILOT])),
              full_run_reserve_after_pilot=len(pool) - NPILOT)
    out['datasets'][tag] = st
    print(json.dumps(st), flush=True)
(STAGE / 'notes/POOL_E20P.json').write_text(json.dumps(out, indent=2) + '\n')
