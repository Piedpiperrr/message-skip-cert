"""P2-8：ARC-Challenge train/validation 标准记录、映射、重复与异常统计（CPU）。

只读取本目录 source/ 下按固定 revision 下载的 train/validation parquet；test 不下载、不读取，只记录元数据。
异常只标记，不删题、不改gold、不重排选项。
"""
import collections
import csv
import hashlib
import json
from pathlib import Path

import pyarrow.parquet as pq

import arc_protocol as ap

OUT = Path(__file__).resolve().parent
REPO, CONFIG = 'allenai/ai2_arc', 'ARC-Challenge'
REV = '210d026faf9955653af8916fad021475a3f00453'
# HfApi.dataset_info(files_metadata=True) 于 revision REV 返回的 LFS sha256 与大小
LFS = {'train': ('e488c1587ffdcfc8443f916c53488a95cd471c5790e0746c6bfe4cecf20962cb', 189909),
       'validation': ('395a5c88d1580d69855fbaee9450270578df1ad5af6259771cd0a42c20e99f05', 55743),
       'test': ('62f03257e737aed263f55c6abf87c7bb0028a44a6bdd2a26eb1279eb42c1d1e9', 203808)}
README_SPLITS = {'train': 1119, 'validation': 299, 'test': 1172}  # source/README.md dataset_info
OBQA = Path('$DATA_DIR/c2c_reproduction_assets/datasets/allenai--openbookqa/main')
P5 = ap.P5


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def norm(s):
    return ' '.join(str(s).lower().split())


def write_csv(name, rows, fields=None):
    with (OUT / name).open('w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields or list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


# ---------- 来源校验与标准记录 ----------
source = {}
records = {}
for split in ['train', 'validation']:
    path = OUT / 'source' / f'{split}-00000-of-00001.parquet'
    assert sha(path) == LFS[split][0] and path.stat().st_size == LFS[split][1], f'{split} 源文件哈希不符'
    source[split] = {'file': f'{CONFIG}/{split}-00000-of-00001.parquet', 'local': str(path), 'sha256': LFS[split][0], 'bytes': LFS[split][1]}
    raw = pq.read_table(path).to_pylist()
    recs = []
    for i, r in enumerate(raw):
        labels, texts = list(r['choices']['label']), list(r['choices']['text'])
        disp = ap.display_labels(len(labels))
        flags = []
        if len(labels) != len(texts):
            flags.append('label_text_length_mismatch')
        if len(set(labels)) != len(labels):
            flags.append('duplicate_original_labels')
        lmap = dict(zip(labels, disp))
        gold = lmap.get(r['answerKey'])
        if gold is None:
            flags.append('answer_key_not_in_labels')
        if len(labels) != 4:
            flags.append(f'n_choices_{len(labels)}')
            flags.append('instruction_labels_rendered_per_question')  # v2：指令按该题合法标签渲染
        if labels != disp:
            flags.append('numeric_original_labels' if all(l.isdigit() for l in labels) else 'relabelled_non_sequential')
        if len(set(texts)) != len(texts):
            flags.append('exact_duplicate_choice_text_within_question')
        elif len({norm(t) for t in texts}) != len(texts):
            flags.append('choice_texts_differ_only_by_case_or_whitespace')  # 如基因型 WW/Ww，原文不同，仅提示
        if any(not str(t).strip() for t in texts) or not str(r['question']).strip():
            flags.append('empty_text')
        if any(str(t) != str(t).strip() for t in texts + [r['question']]):
            flags.append('leading_trailing_whitespace')
        rec = {'dataset': REPO, 'config': CONFIG, 'revision': REV, 'source_split': split, 'source_row_index': i, 'id': r['id'],
               'question_stem': r['question'], 'original_choice_labels': labels, 'choice_text': texts, 'n_choices': len(labels),
               'choice_labels': disp, 'display_label_map': lmap, 'choices': {'label': disp, 'text': texts}}
        rec['query'] = ap.router_query(rec)
        rec['receiver_prompt'] = ap.receiver_prompt(rec)
        rec['helper_prompt'] = ap.helper_prompt(rec)
        # gold 仅供监督与评价，不进入 query/prompt
        rec['original_answer_key'] = r['answerKey']
        rec['gold_answer'] = gold
        rec['flags'] = flags
        recs.append(rec)
    records[split] = recs
    (OUT / f'arc_challenge_{split}.jsonl').write_text(''.join(json.dumps(x, ensure_ascii=False) + '\n' for x in recs))

# ---------- 映射与计数 ----------
checks = {}
map_rows = []
for split, recs in records.items():
    ids = [r['id'] for r in recs]
    inv_ok = all({v: k for k, v in r['display_label_map'].items()}[r['gold_answer']] == r['original_answer_key'] for r in recs if r['gold_answer'])
    checks[split] = {'n': len(recs), 'expected_readme': README_SPLITS[split], 'n_matches_readme': len(recs) == README_SPLITS[split],
                     'ids_unique': len(set(ids)) == len(ids), 'gold_mapped': sum(r['gold_answer'] is not None for r in recs),
                     'gold_inverse_mapping_ok': inv_ok,
                     'gold_display_distribution': dict(sorted(collections.Counter(r['gold_answer'] for r in recs).items())),
                     'flag_counts': dict(collections.Counter(f for r in recs for f in r['flags']))}
    for (ls, n), c in sorted(collections.Counter((''.join(r['original_choice_labels']), r['n_choices']) for r in recs).items()):
        map_rows.append({'split': split, 'original_label_set': ls, 'n_choices': n, 'display_label_set': ''.join(ap.display_labels(n)), 'count': c})
write_csv('mapping_summary.csv', map_rows)
anom = [{'split': r['source_split'], 'id': r['id'], 'n_choices': r['n_choices'], 'original_labels': ''.join(r['original_choice_labels']),
         'flags': ';'.join(r['flags'])} for s in records for r in records[s] if r['flags']]
write_csv('anomalies.csv', anom, ['split', 'id', 'n_choices', 'original_labels', 'flags'])

# ---------- 重复：划分内、划分间、与OBQA ----------
def keys(stem, texts):
    return {'stem': norm(stem), 'stem_choices_ordered': norm(stem) + '||' + '||'.join(norm(t) for t in texts),
            'stem_choices_unordered': norm(stem) + '||' + '||'.join(sorted(norm(t) for t in texts))}


dup_rows = []
index = collections.defaultdict(list)
for split, recs in records.items():
    for r in recs:
        for kt, kv in keys(r['question_stem'], r['choice_text']).items():
            index[(kt, kv)].append((split, r['id']))
for (kt, kv), members in index.items():
    if len(members) > 1:
        splits = sorted({s for s, _ in members})
        dup_rows.append({'scope': 'arc_within_' + splits[0] if len(splits) == 1 else 'arc_cross_split', 'key_type': kt,
                         'key_sha1': hashlib.sha1(kv.encode()).hexdigest()[:12], 'members': ';'.join(f'{s}:{i}' for s, i in members)})
id_overlap = sorted({r['id'] for r in records['train']} & {r['id'] for r in records['validation']})

p5_ids = {}
for name, split in [('train_questions.jsonl', 'p2_5_train3466'), ('dev_questions.jsonl', 'p2_5_dev742')]:
    for s in (P5 / name).read_text().splitlines():
        p5_ids[json.loads(s)['id']] = split
obqa_index = collections.defaultdict(list)
obqa_n = {}
for split in ['train', 'validation', 'test']:
    rows = pq.read_table(OBQA / f'{split}-00000-of-00001.parquet', columns=['id', 'question_stem', 'choices']).to_pylist()
    obqa_n[split] = len(rows)
    for r in rows:
        tag = f"obqa_{split}" + (f"({p5_ids[r['id']]})" if r['id'] in p5_ids else '')
        for kt, kv in keys(r['question_stem'], r['choices']['text']).items():
            obqa_index[(kt, kv)].append(f"{tag}:{r['id']}")
obqa_hits = collections.Counter()
for split, recs in records.items():
    for r in recs:
        for kt, kv in keys(r['question_stem'], r['choice_text']).items():
            if (kt, kv) in obqa_index:
                obqa_hits[(split, kt)] += 1
                dup_rows.append({'scope': 'arc_vs_obqa', 'key_type': kt, 'key_sha1': hashlib.sha1(kv.encode()).hexdigest()[:12],
                                 'members': f"{split}:{r['id']};" + ';'.join(obqa_index[(kt, kv)])})
write_csv('duplicates.csv', dup_rows, ['scope', 'key_type', 'key_sha1', 'members'])
dup_summary = {'id_overlap_train_validation': id_overlap,
               'groups_by_scope_and_key': dict(collections.Counter(f"{d['scope']}|{d['key_type']}" for d in dup_rows)),
               'obqa_reference_rows': obqa_n, 'obqa_hits': {f'{s}|{k}': v for (s, k), v in obqa_hits.items()},
               'normalization': 'lowercase + whitespace collapse; exact match only (no fuzzy dedup)'}

# ---------- 来源清单、用途约定、汇总 ----------
manifest = {'dataset': REPO, 'config': CONFIG, 'revision': REV, 'revision_last_modified': '2023-12-21T15:09:48+00:00',
            'url': 'https://huggingface.co/datasets/allenai/ai2_arc', 'license': 'cc-by-sa-4.0 (README)',
            'paper': 'arXiv:1803.05457', 'readme_sha256': sha(OUT / 'source' / 'README.md'),
            'downloaded': source,
            'test_metadata_only': {'file': f'{CONFIG}/test-00000-of-00001.parquet', 'lfs_sha256': LFS['test'][0], 'bytes': LFS['test'][1],
                                   'num_examples_readme': README_SPLITS['test'], 'downloaded': False, 'answers_viewed': False},
            'not_downloaded': ['ARC-Challenge/test', 'ARC-Easy', 'any additional science corpus']}
(OUT / 'source_manifest.json').write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
contract = {'dataset': f'{REPO}:{CONFIG}@{REV}',
            'train': {'n': len(records['train']), 'use': 'future router training and within-train cross-validation'},
            'validation': {'n': len(records['validation']), 'use': 'future development selection under pre-specified rules only'},
            'test': {'n_metadata': README_SPLITS['test'], 'use': 'final-evaluation candidate after methods and selection rules are frozen',
                     'current_status': 'not downloaded; no model run; answers not viewed',
                     'eligibility_caveats': ['publicly released benchmark; official C2C evaluator config includes the ARC-Challenge test split '
                                             '(direct evidence is the config only; actual evaluation runs or use for model selection unverified/unknown)',
                                             'base-model pretraining and public fuser training data cannot be proven uncontaminated',
                                             'project-record check is bounded; "no record found" is not proof of non-use']},
            'undecided': ['future training-data mixture', 'method selection rule', 'GPU budget']}
(OUT / 'data_use_contract.json').write_text(json.dumps(contract, indent=2, ensure_ascii=False))
summary = {'checks': checks, 'duplicates': dup_summary,
           'outputs_sha256': {n: sha(OUT / n) for n in ['arc_challenge_train.jsonl', 'arc_challenge_validation.jsonl']}}
(OUT / 'prep_summary.json').write_text(json.dumps(summary, indent=2, ensure_ascii=False))
print(json.dumps(summary, indent=2, ensure_ascii=False))
