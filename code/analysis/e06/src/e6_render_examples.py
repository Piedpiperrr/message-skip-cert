"""Render the frozen large-pair Text helper prompt and the Text+fact variant for the first 2 fit questions."""
import json,sys,hashlib
from pathlib import Path
import pyarrow.parquet as pq
R=Path('$DATA_DIR')
BOUND=R/'P2_CONFIDENCE_REFERENCE_BOUNDARIES_20260914T165012Z'
DS=Path('$DATA_DIR/c2c_reproduction_assets/datasets/allenai--openbookqa')
sys.path.insert(0,str(R/'P2_5_20260910T072811Z'))
from protocol_min import build_prompt   # the frozen P2-5 builder used by arc_protocol.helper_body
BACKGROUND_PROMPT=("In one clear sentence, describe the most essential background knowledge "
                   "needed to answer the question:\n\n{question}\n\n"
                   "Do NOT directly solve or give answer to the question.")
def choices_block(texts):return ''.join(f'{chr(65+i)}. {t}\n' for i,t in enumerate(texts))
def helper_body(rec,fact=None):
    """arc_protocol.helper_body, with the single E6 addition: one 'Useful fact: <fact1>' line
    inserted immediately before the question text (the first line of the body)."""
    q=str(rec['question_stem'])
    if fact is not None:q='Useful fact: '+fact+'\n'+q
    return build_prompt(dataset='mmlu-redux',locale='',question=q,
                        choices=choices_block(rec['choice_text']),use_cot=False,use_template=False)
def helper_prompt(rec,fact=None):return BACKGROUND_PROMPT.format(question=helper_body(rec,fact))
facts={r['id']:r['fact1'] for r in pq.read_table(DS/'additional/train-00000-of-00001.parquet').to_pylist()}
q={r['id']:r for r in (json.loads(s) for s in (BOUND/'inputs/obqa_train_queries.jsonl').open())}
fit=json.load((BOUND/'splits/obqa_fit_ids.json').open())
ex=[]
for i in fit[:2]:
    base=helper_prompt(q[i]);fac=helper_prompt(q[i],facts[i])
    ex.append({'id':i,'fact1':facts[i],'helper_user_message_Text':base,'helper_user_message_Text_plus_fact':fac,
               'Text_sha256':hashlib.sha256(base.encode()).hexdigest(),'Text_plus_fact_sha256':hashlib.sha256(fac.encode()).hexdigest()})
# byte-identity of the flag when off, on the first 5 fit rows
off_ok=all(helper_prompt(q[i])==helper_prompt(q[i],None) for i in fit[:5])
Path(sys.argv[1]).write_text(json.dumps({'examples':ex,'flag_off_is_byte_identical_on_5_fit_rows':off_ok},indent=2,ensure_ascii=False)+'\n')
for e in ex:
    print('='*20,e['id'],'FACT:',e['fact1']);print('--- Text');print(e['helper_user_message_Text']);print('--- Text+fact');print(e['helper_user_message_Text_plus_fact'])
print('flag-off byte-identical on 5 fit rows:',off_ok)
