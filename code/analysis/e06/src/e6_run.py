"""E6 Text+fact: helper message + receiver answer for one shard of the OBQA calibration/development rows.

Only change to the frozen large-pair Text action: a new flag on the helper prompt builder that inserts
one line "Useful fact: <fact1>" immediately before the question text.  Default off; with the flag off
the rendered helper prompt is byte-identical to the frozen Text prompt (checked on 5 fit rows at start).
The receiver's conversation is the frozen one: its first user turn carries the ORIGINAL (fact-free)
helper body, so the fact reaches the receiver only through the helper's message.
No gold is read.
"""
import json,sys,os,time,argparse,hashlib,traceback
from pathlib import Path
import torch
import pyarrow.parquet as pq
from transformers import AutoModelForCausalLM,AutoTokenizer
R=Path('$DATA_DIR')
BOUND=R/'P2_CONFIDENCE_REFERENCE_BOUNDARIES_20260914T165012Z'
NATIVE=R/'P2_10_20260911T122423Z'
DS=Path('$DATA_DIR/c2c_reproduction_assets/datasets/allenai--openbookqa')
HELPER=R/'P2_6_20260910T164138Z/assets/Qwen2.5-7B-Instruct'
RECEIVER='$DATA_DIR/hf_cache/hub/models--Qwen--Qwen3-8B/snapshots/b968826d9c46dd6066d109eabc6255188de91218'
def rd(p):return json.loads(Path(p).read_text())
def jl(p):
    with Path(p).open() as f:return [json.loads(s) for s in f if s.strip()]

ap=argparse.ArgumentParser()
ap.add_argument('--shard',type=int,default=0);ap.add_argument('--nshards',type=int,default=1)
ap.add_argument('--mode',choices=['smoke','main'],required=True)
ap.add_argument('--helper-gpu',type=int,default=0);ap.add_argument('--receiver-gpu',type=int,default=1)
ap.add_argument('--out',required=True)
a=ap.parse_args()

sys.path.insert(0,str(NATIVE))
import legacy_methods as lm
import arc_runtime_adapter            # patches format_openbook to the frozen ARC/OBQA builder
import protocol_min
from protocol_min import apply_generation_config
import importlib.util as _iu
_spec=_iu.spec_from_file_location('parserv2',str(R/'P2_SCORING_V2_20260912T191445Z/scoring_v2.py'))
parser=_iu.module_from_spec(_spec);_spec.loader.exec_module(parser)

# ---- the one E6 change: a flag on the helper prompt builder -------------------------------------
_frozen_format_openbook=lm.format_openbook
E6={'enabled':False,'fact':None}
def format_openbook_e6(example,use_template=True):
    out=_frozen_format_openbook(example,use_template=use_template)
    if use_template or not E6['enabled']:return out          # receiver prompt path: untouched
    assert E6['fact'],'fact line requested but no fact set'
    return 'Useful fact: '+E6['fact']+'\n'+out               # immediately before the question text
lm.format_openbook=format_openbook_e6
protocol_min.format_openbook=format_openbook_e6
# -------------------------------------------------------------------------------------------------

facts={r['id']:r['fact1'] for r in pq.read_table(DS/'additional/train-00000-of-00001.parquet').to_pylist()}
qtrain={r['id']:r for r in jl(BOUND/'inputs/obqa_train_queries.jsonl')}
qdev={r['id']:r for r in jl(BOUND/'inputs/obqa_dev_queries.jsonl')}
cal=rd(BOUND/'splits/obqa_cal_representatives.json');dev=rd(BOUND/'splits/obqa_dev_representatives.json')
fit=rd(BOUND/'splits/obqa_fit_ids.json')
if a.mode=='smoke':
    work=[('fit',i,qtrain[i]) for i in fit[:16]]
else:
    allrows=[('cal',i,qtrain[i]) for i in cal]+[('dev',i,qdev[i]) for i in dev]
    work=[x for j,x in enumerate(allrows) if j%a.nshards==a.shard]

# flag-off byte identity on 5 fit rows, before anything is loaded
E6['enabled']=False
off=[_frozen_format_openbook(qtrain[i],use_template=False)==format_openbook_e6(qtrain[i],use_template=False) for i in fit[:5]]
assert all(off),'flag-off is not byte-identical'

torch.set_num_threads(1);torch.set_num_interop_threads(1)
torch.manual_seed(0);torch.cuda.manual_seed_all(0)
torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False
hdev='cuda:%d'%a.helper_gpu;rdev='cuda:%d'%a.receiver_gpu
t0=time.perf_counter();load={}
htok=AutoTokenizer.from_pretrained(str(HELPER),local_files_only=True)
if htok.pad_token is None:htok.pad_token=htok.eos_token
helper=AutoModelForCausalLM.from_pretrained(str(HELPER),local_files_only=True,torch_dtype=torch.bfloat16,attn_implementation='sdpa').to(hdev).eval().requires_grad_(False)
apply_generation_config(helper,{'do_sample':False,'max_new_tokens':64});load['helper']=time.perf_counter()-t0
t0=time.perf_counter()
rtok=AutoTokenizer.from_pretrained(RECEIVER,local_files_only=True)
if rtok.pad_token is None:rtok.pad_token=rtok.eos_token
receiver=AutoModelForCausalLM.from_pretrained(RECEIVER,local_files_only=True,torch_dtype=torch.bfloat16,attn_implementation='sdpa').to(rdev).eval().requires_grad_(False)
apply_generation_config(receiver,{'do_sample':False,'max_new_tokens':64});load['receiver']=time.perf_counter()-t0
th=lm.T2THelperBundle(helper,htok);tr=lm.T2TReceiverBundle(receiver,rtok)

out=Path(a.out);out.parent.mkdir(parents=True,exist_ok=True)
n_invalid=0;n=0;errors=[]
with out.open('w') as f:
    for split,i,src in work:
        q={'question_stem':src['question_stem'],'choice_labels':list(src['choice_labels']),'choice_text':list(src['choice_text'])}
        try:
            E6['enabled']=False;frozen_body=_frozen_format_openbook(q,use_template=False)
            E6['enabled']=True;E6['fact']=facts[i]
            t=time.perf_counter()
            msg=th.run(q)                                     # helper sees the fact line
            E6['enabled']=False;E6['fact']=None
            # receiver conversation is the frozen one: original body + the helper's message
            res=tr.consume(q,frozen_body,msg['helper_message'])
            dt=(time.perf_counter()-t)*1000
            p=parser.parse_answer(res['generated_text'],q['choice_labels'])
            n_invalid+= (not p['valid']);n+=1
            f.write(json.dumps({'id':i,'split':split,'action':'text_plus_fact','fact1':facts[i],
                'helper_body_with_fact':msg['helper_body'],'helper_message':msg['helper_message'],
                'helper_generated_tokens':msg['helper_output_token_count'],'helper_input_tokens':msg['helper_input_token_count'],
                'raw_answer':res['generated_text'],'generated_token_ids':res['generated_token_ids'],
                'receiver_input_tokens':res['receiver_input_token_count'],'parsed':p,
                'answer':p['answer'] if p['valid'] else 'INVALID','invalid':not p['valid'],
                'latency_ms':dt,'frozen_body_sha256':hashlib.sha256(frozen_body.encode()).hexdigest(),
                'runtime_failure':False,'gold_read':False},ensure_ascii=False)+'\n')
            f.flush()
        except BaseException as e:
            errors.append({'id':i,'error':repr(e),'traceback':traceback.format_exc()});E6['enabled']=False;E6['fact']=None
            if a.mode=='smoke':break
Path(str(out)+'.status.json').write_text(json.dumps({'mode':a.mode,'shard':a.shard,'nshards':a.nshards,
    'n_done':n,'n_requested':len(work),'invalid':n_invalid,'errors':errors,'load_seconds':load,
    'flag_off_byte_identical_5_fit_rows':all(off),
    'PASS':(a.mode!='smoke') or (n==len(work) and not errors and n_invalid<=2),'gold_read':False},indent=2)+'\n')
print('E6',a.mode,'shard',a.shard,'done',n,'/',len(work),'INVALID',n_invalid,'errors',len(errors),flush=True)
