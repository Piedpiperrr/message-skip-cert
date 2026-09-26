from common import *
compute()
import numpy as np
import torch,transformers,resource
from transformers import AutoModelForCausalLM,AutoTokenizer
from receiver_prompt import receiver_prompt
CFG=read(P/'frozen_config.json');spec=CFG['model'];assert (P/'DEPLOYMENT_FREEZE.json').exists()
torch.set_num_threads(1);torch.set_num_interop_threads(1);torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False
assert torch.cuda.is_available() and torch.cuda.device_count()==1
rows=jl(P/'inputs/dev_queries.jsonl');assert [r['id'] for r in rows]==read(P/'splits/dev_ids.json')
assert len(rows)==742
attempts=jl(P/'records/prefill_attempts.jsonl') if (P/'records/prefill_attempts.jsonl').exists() else []
count=sum(r['event']=='START_PREFILL' for r in attempts);cached=0
if all((P/f'features/dev/{i:04d}.npz').exists() for i in range(742)):raise RuntimeError('Already complete: do not execute duplicate extraction')
stop();t=time.perf_counter();tok=AutoTokenizer.from_pretrained(spec['path'],local_files_only=True)
if tok.pad_token is None:tok.pad_token=tok.eos_token
assert hashlib.sha256(tok.chat_template.encode()).hexdigest()==spec['chat_template_sha256']
lm=AutoModelForCausalLM.from_pretrained(spec['path'],local_files_only=True,torch_dtype=torch.bfloat16,attn_implementation='sdpa',low_cpu_mem_usage=True).to('cuda:0').eval().requires_grad_(False)
torch.cuda.synchronize();load_seconds=time.perf_counter()-t;model=lm.model
save(P/'evidence/model_load.json',{'load_wall_seconds':load_seconds,'torch':torch.__version__,'transformers':transformers.__version__,'GPU':str(torch.cuda.get_device_properties(0)),'CUDA_VISIBLE_DEVICES':os.environ.get('CUDA_VISIBLE_DEVICES'),'job_id':os.environ['PBS_JOBID'],'host':socket.gethostname(),'helper_loaded':False,'LM_head_forward':False})
print('MODEL_LOADED',load_seconds,flush=True)
assert model.config.hidden_size==4096 and model.config.num_hidden_layers==36
state={}
def block_hook(module,args,out):state['block']=out[0][:,state['pos'],:].detach().clone();state['bc']+=1
def norm_hook(module,args,out):state['final']=out[:,state['pos'],:].detach().clone();state['nc']+=1
hooks=[model.layers[25].register_forward_hook(block_hook),model.norm.register_forward_hook(norm_hook)]
index=[];new=0
try:
 for i,row in enumerate(rows):
  stop();dest=P/f'features/dev/{i:04d}.npz'
  if dest.exists():
   with np.load(dest,allow_pickle=False) as a:m=json.loads(str(a['meta']));z=a['z']
   assert m['id']==row['id'] and m['config_sha256']==sha(P/'frozen_config.json') and z.shape==(8192,)
   cached+=1
  else:
   assert count<742;count+=1
   append(P/'records/prefill_attempts.jsonl',{'event':'START_PREFILL','attempt':count,'id':row['id'],'row':i,'utc':utc(),'job_id':os.environ['PBS_JOBID']})
   assert set(row)=={'id','question_stem','choice_labels','choice_text'}
   state.clear();state.update(bc=0,nc=0)
   validation=None
   if new==0:
    def next_hook(module,args):state['next']=args[0][:,state['pos'],:].detach().clone()
    validation=model.layers[26].register_forward_pre_hook(next_hook)
   torch.cuda.synchronize();t0=time.perf_counter()
   body=receiver_prompt(row);rendered=tok.apply_chat_template([{'role':'user','content':body}],tokenize=False,add_generation_prompt=True,enable_thinking=False)
   t1=time.perf_counter();inputs=tok(rendered,return_tensors='pt');t2=time.perf_counter()
   mask=inputs['attention_mask'][0];pos=int(torch.nonzero(mask,as_tuple=False)[-1,0]);state['pos']=pos;n=int(inputs['input_ids'].shape[1])
   token_hash=hashlib.sha256(inputs['input_ids'].numpy().tobytes()).hexdigest()
   tensors={a:b.to('cuda:0') for a,b in inputs.items()};torch.cuda.synchronize();t3=time.perf_counter()
   ev0=torch.cuda.Event(enable_timing=True);ev1=torch.cuda.Event(enable_timing=True)
   with torch.inference_mode():
    ev0.record();out=model(**tensors,use_cache=False,return_dict=True,output_hidden_states=False,output_attentions=False);ev1.record();torch.cuda.synchronize();t4=time.perf_counter()
    h1=state['block'].float();h2=state['final'].float()
    z=torch.cat([h1/torch.linalg.vector_norm(h1,dim=-1,keepdim=True).clamp_min(1e-12),h2/torch.linalg.vector_norm(h2,dim=-1,keepdim=True).clamp_min(1e-12)],dim=-1)/(2**.5)
    torch.cuda.synchronize();t5=time.perf_counter();z_cpu=z[0].cpu().numpy();torch.cuda.synchronize();t6=time.perf_counter()
   assert pos==n-1 and int(mask.sum())==n and n<=40960
   assert state['bc']==state['nc']==1 and out.past_key_values is None
   assert z_cpu.shape==(8192,) and z_cpu.dtype==np.float32 and np.isfinite(z_cpu).all() and np.isclose(np.linalg.norm(z_cpu),1,atol=2e-6)
   if validation:
    assert torch.equal(state['block'],state['next']) and torch.equal(state['final'],out.last_hidden_state[:,pos,:]);validation.remove()
    save(P/'evidence/feature_location_check.json',{'id':row['id'],'block25_equals_block26_input':True,'norm_equals_last_hidden_state':True,'dimension':8192,'no_extra_prefill':True})
   m={'id':row['id'],'row':i,'attempt':count,'job_id':os.environ['PBS_JOBID'],'config_sha256':sha(P/'frozen_config.json'),'input_tokens':n,'last_valid_position':pos,'rendered_sha256':hashlib.sha256(rendered.encode()).hexdigest(),'input_token_ids_sha256':token_hash,'cold_first_after_load':new==0,'feature_ms':(t6-t0)*1000,'prompt_ms':(t1-t0)*1000,'tokenization_ms':(t2-t1)*1000,'input_prepare_transfer_ms':(t3-t2)*1000,'prefill_state_read_ms':(t4-t3)*1000,'normalize_ms':(t5-t4)*1000,'D2H_ms':(t6-t5)*1000,'GPU_prefill_event_ms':ev0.elapsed_time(ev1)}
   tw=time.perf_counter();temp=dest.with_suffix('.tmp')
   with temp.open('wb') as f:np.savez(f,z=z_cpu,meta=json.dumps(m));f.flush();os.fsync(f.fileno())
   temp.replace(dest);append(P/'records/feature_writes.jsonl',{'id':row['id'],'file_write_ms_excluded':(time.perf_counter()-tw)*1000})
   new+=1
   append(P/'records/prefill_attempts.jsonl',{'event':'SUCCESS','attempt':count,'id':row['id'],'path':str(dest),'utc':utc()})
   del out,tensors,z,h1,h2;state.clear()
  index.append({'id':row['id'],'row':i,'path':str(dest),'sha256':sha(dest),'dimension':8192,'dtype':'float32',**m})
  if (i+1)%100==0 or i+1==742:
   csvout(P/'features/DEV_FEATURE_INDEX.csv',index);save(P/'FEATURE_PROGRESS.json',{'completed':len(index),'attempts':count,'new_success':new,'cached':cached,'utc':utc()});print('DEV_PREFILL',len(index),flush=True)
finally:
 for h in hooks:h.remove()
 csvout(P/'features/DEV_FEATURE_INDEX.csv',index)
freeze('DEV_FEATURES_COMPLETE.json',[P/'features/DEV_FEATURE_INDEX.csv'],success=len(index),attempts=count,new_success=new,cached=cached,model_load_wall_seconds=load_seconds)
