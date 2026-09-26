"""E7 validation on 16 fit questions per receiver.  No gold is read.

For each question: run the frozen probe (use_cache=False) and the REUSE probe (use_cache=True),
check the scores agree exactly, continue the cropped cache to a receiver-only answer, and compare the
raw output string with the saved R output.  Also check the probe argmax equals the saved argmax.
"""
import json,sys,os,time
from pathlib import Path
import torch
from transformers import AutoModelForCausalLM,AutoTokenizer
R=Path('$DATA_DIR')
W=Path(os.environ['P2R2_W'])
E3=R/'P2_R1_E3POL_REPEAT1_20260919T075315Z'
BOUND=R/'P2_CONFIDENCE_REFERENCE_BOUNDARIES_20260914T165012Z'
ZERO=R/'P2_ZERO_GOLD_CONTROLS_20260914T065145Z'
MED=R/'P2_MEDIUM_PAIR_BOUNDARY_EXTENSION_STAGE1_20260915T144407Z/execution_retry1_20260915T164957Z'
sys.path.insert(0,str(E3/'large/src'));sys.path.insert(0,str(W/'src'))
from receiver_prompt import receiver_prompt,display_labels
from e7_reuse import probe_core,crop_to_R_prefix,generate_R_from_cache
def jl(p):
    with Path(p).open() as f:return [json.loads(s) for s in f if s.strip()]
def rd(p):return json.loads(Path(p).read_text())

which=sys.argv[1]                      # 'large' (Qwen3-8B) or 'medium' (Qwen3-1.7B)
out_path=Path(sys.argv[2])
PATHS={'large':'$DATA_DIR/hf_cache/hub/models--Qwen--Qwen3-8B/snapshots/b968826d9c46dd6066d109eabc6255188de91218',
       'medium':str(E3/'medium/assets/receiver')}
fit=rd(BOUND/'splits/obqa_fit_ids.json')[:16]
queries={r['id']:r for r in jl(BOUND/'inputs/obqa_train_queries.jsonl')}
if which=='large':
    saved_R={r['id']:r['raw_answer'] for r in jl(R/'P2_6_20260910T164138Z/results/train_cases.jsonl')
             if r['action']=='receiver_only' and r['id'] in set(fit)}
    saved_probe={r['id']:r['argmax_probe_label'] for r in jl(ZERO/'records/probe_records.jsonl') if r['id'] in set(fit)}
else:
    saved_R={r['id']:r['output']['raw_answer'] for r in jl(MED/'actions/obqa_fit.jsonl')
             if r['action']=='R' and r['id'] in set(fit)}
    saved_probe={r['id']:r['argmax_probe_label'] for r in jl(MED/'probes/obqa_fit.jsonl') if r['id'] in set(fit)}
assert all(i in saved_R and i in saved_probe for i in fit),'missing saved reference rows'

torch.set_num_threads(1);torch.set_num_interop_threads(1)
torch.manual_seed(0);torch.cuda.manual_seed_all(0)
torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False
tok=AutoTokenizer.from_pretrained(PATHS[which],local_files_only=True)
if tok.pad_token is None:tok.pad_token=tok.eos_token
model=AutoModelForCausalLM.from_pretrained(PATHS[which],local_files_only=True,torch_dtype=torch.bfloat16,
        attn_implementation='sdpa').to('cuda:0').eval().requires_grad_(False)
model.generation_config.do_sample=False;model.generation_config.max_new_tokens=64
for k in ['temperature','top_p','top_k','min_p','repetition_penalty']:
    try:setattr(model.generation_config,k,None)
    except Exception:pass
prefix_ids=tok.encode('The correct answer is',add_special_tokens=False)
MEDP=R/'P2_MEDIUM_PAIR_BOUNDARY_EXTENSION_STAGE1_20260915T144407Z'
label_sets=rd(E3/'large/protocol/label_token_sets.json') if which=='large' else rd(MEDP/'protocol/label_token_sets.json')
for l,v in label_sets.items():
    assert all(t not in tok.all_special_ids and tok.decode([t],skip_special_tokens=False,clean_up_tokenization_spaces=False).strip()==l for t in v),l
ix={l:torch.tensor(v,device=model.device) for l,v in label_sets.items()}

rows=[];mism=0;argmax_bad=0
with torch.inference_mode():
    for i in fit:
        src=queries[i];q={'question_stem':src['question_stem'],'choice_labels':list(src['choice_labels']),'choice_text':list(src['choice_text'])}
        u0,m0,R0,_=probe_core(model,tok,q,receiver_prompt,display_labels,prefix_ids,ix,keep_cache=False)
        u1,m1,R1,cache=probe_core(model,tok,q,receiver_prompt,display_labels,prefix_ids,ix,keep_cache=True)
        n_R=R1.shape[1]
        crop_to_R_prefix(cache,n_R)
        text,gen=generate_R_from_cache(model,tok,R1,cache)
        ok_raw=(text==saved_R[i]);ok_arg=(m1['argmax_probe_label']==saved_probe[i])
        mism+= (not ok_raw);argmax_bad+= (not ok_arg)
        rows.append({'id':i,'reuse_raw':text,'saved_R_raw':saved_R[i],'raw_match':ok_raw,
                     'probe_argmax':m1['argmax_probe_label'],'saved_probe_argmax':saved_probe[i],'argmax_match':ok_arg,
                     'ProbeMax_nocache':u0,'ProbeMax_cache':u1,'probe_scores_identical':u0==u1 and m0['p_labels']==m1['p_labels'],
                     'probe_ids_sha256_identical':m0['probe_ids_sha256']==m1['probe_ids_sha256'],'n_R_tokens':n_R})
        del cache
res={'receiver':which,'model_path':PATHS[which],'n':len(fit),'reuse_raw_mismatches':mism,
     'argmax_mismatches':argmax_bad,'probe_scores_identical_all':all(r['probe_scores_identical'] for r in rows),
     'PASS':(mism<=1 and argmax_bad==0),'gold_read':False,'rows':rows}
out_path.parent.mkdir(parents=True,exist_ok=True);out_path.write_text(json.dumps(res,indent=2,ensure_ascii=False)+'\n')
print('E7_VALIDATION',which,'reuse_mismatches',mism,'argmax_mismatches',argmax_bad,'PASS',res['PASS'],flush=True)
