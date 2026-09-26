"""One independent receiver backbone prefill per uncached train item; never load labels."""
import sys;sys.dont_write_bytecode=True
from extract_harness_r1 import *  # R1: harness replaces P2_E1_DIRECTION common.py
import sys,resource
require_compute()
import numpy as np
import torch,transformers
from transformers import AutoModelForCausalLM,AutoTokenizer
from receiver_prompt import receiver_prompt
pair=sys.argv[1];spec=CFG['models'][pair];SETTINGS=sys.argv[2].split(',')  # R1: explicit populations
torch.set_num_threads(1);torch.set_num_interop_threads(1)
torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False
assert torch.cuda.is_available() and torch.cuda.device_count()==1
if all(feature_path(pair,ds,i).exists() for ds in SETTINGS for i in range(len(queries(ds)))):
 print('ALL_FEATURES_CACHED',pair,flush=True);sys.exit(0)
print('MODEL_LOADING',pair,spec['path'],flush=True)
load_start=time.perf_counter();tok=AutoTokenizer.from_pretrained(spec['path'],local_files_only=True)
if tok.pad_token is None:tok.pad_token=tok.eos_token
assert hashlib.sha256(tok.chat_template.encode()).hexdigest()==spec['chat_template_sha256']
tok_seconds=time.perf_counter()-load_start
# Same checkpoint, BF16 and SDPA; low-memory loading changes storage, not arithmetic.
tm=time.perf_counter()
lm=AutoModelForCausalLM.from_pretrained(spec['path'],local_files_only=True,torch_dtype=torch.bfloat16,attn_implementation='sdpa',low_cpu_mem_usage=True).to('cuda:0').eval().requires_grad_(False)
torch.cuda.synchronize();model_seconds=time.perf_counter()-tm
model=lm.model
assert model.config.hidden_size==spec['hidden_size'] and model.config.num_hidden_layers==spec['num_hidden_layers']
assert all(not p.requires_grad for p in lm.parameters()) and not lm.training
load={'pair':pair,'job_id':os.environ['PBS_JOBID'],'utc':utc(),'tokenizer_seconds':tok_seconds,'model_load_transfer_seconds':model_seconds,'total_load_seconds':time.perf_counter()-load_start,'torch':torch.__version__,'transformers':transformers.__version__,'GPU':str(torch.cuda.get_device_properties(0)),'CUDA_VISIBLE_DEVICES':os.environ.get('CUDA_VISIBLE_DEVICES'),'peak_RSS_KiB':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'cold_start_policy':'no separate warmup; first actual formal item included and flagged','no_helper':True,'no_LM_head_forward':True}
append(O/'evidence/model_loads.jsonl',load);print('MODEL_LOADED',pair,load,flush=True)
state={};k=spec['ac_block_index'];checks=[]
def ac_hook(module,args,output):
 h=output[0];state['ac']=h[:,state['pos'],:].detach().clone();state['ac_shape']=list(h.shape);state['ac_calls']+=1
 # Read-only hook, returning None preserves original output.
def final_hook(module,args,output):
 state['final']=output[:,state['pos'],:].detach().clone();state['norm_shape']=list(output.shape);state['norm_calls']+=1
hooks=[model.layers[k].register_forward_hook(ac_hook),model.norm.register_forward_hook(final_hook)]
attempts=sum(r['event']=='START_PREFILL' for r in jl(O/'prefill_attempts.jsonl'));loaded_index=0
folds=FOLDS  # R1: no fold map for these populations
try:
 for ds in SETTINGS:
  first_check=not (O/'evidence'/f'first_feature_{pair}_{ds}.json').exists()
  rows=queries(ds)
  for i,row in enumerate(rows):
   stop_check();dest=feature_path(pair,ds,i);dest.parent.mkdir(parents=True,exist_ok=True)
   if dest.exists():
    with np.load(dest,allow_pickle=False) as v:
     rec=json.loads(str(v['meta']));assert rec['id']==row['id'] and rec['config_sha256']==FREEZE['config_sha256']
    continue
   assert set(row)=={'id','question_stem','choice_labels','choice_text'}
   assert attempts<LIMIT,'PREFILL_ATTEMPT_LIMIT';attempts+=1
   append(O/'prefill_attempts.jsonl',{'event':'START_PREFILL','attempt':attempts,'pair':pair,'dataset':ds,'id':row['id'],'row':i,'job_id':os.environ['PBS_JOBID'],'utc':utc()})
   state.clear();state.update(ac_calls=0,norm_calls=0)
   validation_hook=None
   if first_check:
    def next_input(module,args):state['next_input']=args[0][:,state['pos'],:].detach().clone()
    validation_hook=model.layers[k+1].register_forward_pre_hook(next_input)
   torch.cuda.synchronize();t0=time.perf_counter()
   body=receiver_prompt(row)
   rendered=tok.apply_chat_template([{'role':'user','content':body}],tokenize=False,add_generation_prompt=True,enable_thinking=False)
   t1=time.perf_counter();inputs=tok(rendered,return_tensors='pt');t2=time.perf_counter()
   mask=inputs['attention_mask'][0];pos=int(torch.nonzero(mask,as_tuple=False)[-1,0]);state['pos']=pos
   n=int(inputs['input_ids'].shape[1]);last_id=int(inputs['input_ids'][0,pos]);token_hash=hashlib.sha256(inputs['input_ids'].numpy().tobytes()).hexdigest()
   tensors={a:b.to('cuda:0') for a,b in inputs.items()};torch.cuda.synchronize();t3=time.perf_counter()
   ev0=torch.cuda.Event(enable_timing=True);ev1=torch.cuda.Event(enable_timing=True)
   with torch.inference_mode():
    ev0.record()
    output=model(**tensors,use_cache=False,return_dict=True,output_hidden_states=False,output_attentions=False)
    ev1.record();torch.cuda.synchronize();t4=time.perf_counter()
    h1=state['ac'].float();h2=state['final'].float()
    z=torch.cat([h1/torch.linalg.vector_norm(h1,dim=-1,keepdim=True).clamp_min(1e-12),h2/torch.linalg.vector_norm(h2,dim=-1,keepdim=True).clamp_min(1e-12)],dim=-1)/(2**.5)
    torch.cuda.synchronize();t5=time.perf_counter();z_cpu=z[0].cpu().numpy();torch.cuda.synchronize();t6=time.perf_counter()
   # These checks reuse the actual formal request and are timed separately.
   tv=time.perf_counter()
   assert pos==n-1 and int(mask.sum())==n and n<=spec['max_position_embeddings']
   assert state['ac_calls']==state['norm_calls']==1 and output.past_key_values is None
   assert z_cpu.shape==(2*spec['hidden_size'],) and np.isfinite(z_cpu).all()
   assert np.isclose(np.linalg.norm(z_cpu),1,atol=2e-6)
   if first_check:
    assert torch.equal(state['ac'],state['next_input'])
    assert torch.equal(state['final'],output.last_hidden_state[:,pos,:])
    check={'pair':pair,'dataset':ds,'id':row['id'],'row':i,'actual_AC_module':f'model.layers[{k}]','side':'output[0], before next block input RMSNorm','zero_based_index':k,'equivalent_hidden_states_index':k+1,'actual_final_module':'model.norm','side_final':'output after final RMSNorm','final_hidden_states_index':-1,'AC_equals_next_block_input_exact':True,'final_equals_backbone_last_hidden_state_exact':True,'shape_AC':state['ac_shape'],'shape_norm':state['norm_shape'],'last_valid_token_position':pos,'token_count':n,'last_token_id':last_id,'finite':True,'normalized_dimension':len(z_cpu),'no_extra_prefill':True,'job_id':os.environ['PBS_JOBID']}
    save(O/'evidence'/f'first_feature_{pair}_{ds}.json',check);first_check=False
   if validation_hook:validation_hook.remove()
   validation_ms=(time.perf_counter()-tv)*1000
   rec={'pair':pair,'dataset':ds,'id':row['id'],'row':i,'fold':folds[ds,row['id']],'attempt':attempts,'job_id':os.environ['PBS_JOBID'],'config_sha256':FREEZE['config_sha256'],'input_tokens':n,'last_valid_position':pos,'last_token_id':last_id,'rendered_sha256':hashlib.sha256(rendered.encode()).hexdigest(),'input_token_ids_sha256':token_hash,'cold_first_after_load':loaded_index==0,'layer_validation_in_prefill':validation_hook is not None,'feature_ms':(t6-t0)*1000,'prompt_ms':(t1-t0)*1000,'tokenization_ms':(t2-t1)*1000,'input_prepare_transfer_ms':(t3-t2)*1000,'prefill_state_read_ms':(t4-t3)*1000,'normalize_ms':(t5-t4)*1000,'D2H_ms':(t6-t5)*1000,'GPU_prefill_event_ms':ev0.elapsed_time(ev1),'validation_ms_excluded':validation_ms,'peak_RSS_KiB':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}
   tw=time.perf_counter();temp=dest.with_suffix('.tmp')
   with temp.open('wb') as f:np.savez(f,z=z_cpu,meta=json.dumps(rec));f.flush();os.fsync(f.fileno())
   temp.replace(dest);write_ms=(time.perf_counter()-tw)*1000
   append(O/'feature_writes.jsonl',{'pair':pair,'dataset':ds,'id':row['id'],'row':i,'cache_write_ms_excluded':write_ms,'path':str(dest)})
   loaded_index+=1
   del output,tensors,z,h1,h2;state.clear()
   if (i+1)%100==0 or i+1==len(rows):
    print('FEATURE_PROGRESS',pair,ds,i+1,'attempts',attempts,'RSS_KiB',resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,flush=True)
    save(O/'FEATURE_PROGRESS.json',{'pair':pair,'dataset':ds,'row_completed':i+1,'prefill_attempts':attempts,'updated_utc':utc()})
finally:
 for hook in hooks:hook.remove()
save(O/'features'/pair/'COMPLETE.json',{'pair':pair,'n':LIMIT,'settings':SETTINGS,'job_id':os.environ['PBS_JOBID'],'prefill_attempts_cumulative':attempts,'config_sha256':FREEZE['config_sha256'],'completed_utc':utc()})
