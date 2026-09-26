"""Minimal adaptation of existing E2E runtime: unchanged native R/T/C; frozen ProbeMax replaces probe, no W/head."""
from common import *
import sys,time,hashlib,math,torch,numpy as np
from types import SimpleNamespace
from transformers import AutoModelForCausalLM,AutoTokenizer
# Import the original native modules read-only, without the stage driver.
sys.path.insert(0,CFG['native_root'])
import runtime as native
import arc_runtime_adapter
from runtime_checks import validate_result
from protocol_min import apply_generation_config,receiver_prompt_tensors
sys.path.remove(CFG['native_root'])
# Native runtime already disables old internal timing and unused old parsing.

def sync():
 for i in [0,1]:torch.cuda.synchronize(i)

class Runtime:
 def __init__(self):
  assert torch.cuda.device_count()==2
  torch.set_num_threads(1);torch.set_num_interop_threads(1)
  torch.manual_seed(0);torch.cuda.manual_seed_all(0)
  torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False
  self.load_times={};self.runner=native.Runner.__new__(native.Runner)
  cfg=CFG['native']
  for role,device in [('helper','cuda:0'),('receiver','cuda:1')]:
   stop_check();t=time.perf_counter();spec=cfg['models'][role]
   tok=AutoTokenizer.from_pretrained(spec['path'],local_files_only=True)
   assert hashlib.sha256(tok.chat_template.encode()).hexdigest()==spec['chat_template_sha256']
   if tok.pad_token is None:tok.pad_token=tok.eos_token
   model=AutoModelForCausalLM.from_pretrained(spec['path'],local_files_only=True,torch_dtype=torch.bfloat16,attn_implementation='sdpa').to(device).eval().requires_grad_(False)
   apply_generation_config(model,{'do_sample':False,'max_new_tokens':64})
   setattr(self.runner,role,model);setattr(self.runner,role+'_tok',tok);sync();self.load_times[role]=time.perf_counter()-t
  assert self.runner.receiver.generation_config.to_dict()==cfg['receiver_generation_config']
  lm=native.lm;lm.C2C_FUSERS=Path(cfg['fuser']['path']);lm.HELPER_CONFIG=self.runner.helper.config;lm.RECEIVER_CONFIG=self.runner.receiver.config
  self.runner.th=lm.T2THelperBundle(self.runner.helper,self.runner.helper_tok)
  self.runner.tr=lm.T2TReceiverBundle(self.runner.receiver,self.runner.receiver_tok)
  self.runner.ch=lm.C2CSharerHelperBundle(self.runner.helper,self.runner.receiver_tok)
  assert self.runner.ch.tokenizer is self.runner.receiver_tok
  t=time.perf_counter();self.runner.cr=lm.C2CReceiverSideFuserBundle(self.runner.receiver,self.runner.receiver_tok)
  for f in self.runner.cr.projectors:f.eval().requires_grad_(False)
  sync();self.load_times['fusers']=time.perf_counter()-t
  self.trace=[];self.active=False;self.trace_handles=[]
  for role in ['helper','receiver']:
   model=getattr(self.runner,role)
   self._install_trace(model,role,model.device)
  self._install_trace(self.runner.receiver.model,'receiver_backbone',self.runner.receiver.device)
  for j,f in enumerate(self.runner.cr.projectors):self._install_trace(f,'fuser_'+str(j),self.runner.receiver.device)
  self.baseline=self.hook_signature();self.first_request=True;self.action_first={a:True for a in A};self.validated_probe=False
  self.prefix_ids=read(P/'protocol/prefix_ids.json')['ids'];self.ix={l:torch.tensor(v,device='cuda:1') for l,v in read(P/'protocol/label_token_sets.json').items()}
  assert self.runner.receiver_tok.encode(CFG['prefix'],add_special_tokens=False)==self.prefix_ids
  for l,ix in read(P/'protocol/label_token_sets.json').items():
   assert all(v not in self.runner.receiver_tok.all_special_ids and self.runner.receiver_tok.decode([v],skip_special_tokens=False,clean_up_tokenization_spaces=False).strip()==l for v in ix)
  save(P/'evidence'/('model_load_'+os.environ['PBS_JOBID']+'.json'),{'utc':utc(),'job_id':os.environ['PBS_JOBID'],'load_seconds':self.load_times,'GPUs':[str(torch.cuda.get_device_properties(i)) for i in [0,1]],'cuda_device_count':2,'peer_access':torch.cuda.can_device_access_peer(0,1),'semantic_encoder_loaded':False,'generation_config':self.runner.receiver.generation_config.to_dict(),'C_helper_uses_receiver_tokenizer':True,'hook_baseline':self.baseline})
 def _install_trace(self,module,role,device):
  stack=[]
  def pre(m,args,kwargs):
   if not self.active:return
   # Receiver backbone nested inside LM is excluded from compute-event sums.
   inp=kwargs.get('input_ids',args[0] if args else None)
   tokens=int(inp.shape[-1]) if hasattr(inp,'shape') and inp.ndim>=2 else None
   with torch.cuda.device(device):ev=torch.cuda.Event(enable_timing=True);ev.record()
   record={'role':role,'input_tokens':tokens,'device':str(device),'start':ev,'end':None,'probe':bool(getattr(self,'in_probe',False))};stack.append(record);self.trace.append(record)
  def post(m,args,kwargs,out):
   if not self.active or not stack:return
   r=stack.pop()
   with torch.cuda.device(device):r['end']=torch.cuda.Event(enable_timing=True);r['end'].record()
  self.trace_handles.extend([module.register_forward_pre_hook(pre,with_kwargs=True),module.register_forward_hook(post,with_kwargs=True,always_call=True)])
 def hook_signature(self):
  return {r:[(len(m._forward_hooks),len(m._forward_pre_hooks)) for m in getattr(self.runner,r).model.layers] for r in ['helper','receiver']}
 def check_hooks(self):
  if self.hook_signature()!=self.baseline:raise SemanticFailure('NATIVE_BLOCK_HOOKS_NOT_RESTORED')
 def begin(self):
  self.check_hooks();self.trace=[];self.active=True;self.in_probe=False
 def end(self):self.active=False;self.check_hooks()
 def trace_result(self):
  rr=[]
  for r in self.trace:
   assert r['end'] is not None
   rr.append({k:v for k,v in r.items() if k not in ['start','end']}|{'CUDA_event_ms':float(r['start'].elapsed_time(r['end']))})
  # Backbone is counted only during probe; native LM includes its backbone already.
  compute=[r for r in rr if r['role']!='receiver_backbone' or r['probe']]
  return rr,sum(r['CUDA_event_ms'] for r in compute)
 @torch.inference_mode()
 def probe(self,q):
  from receiver_prompt import receiver_prompt,display_labels
  self.in_probe=True;tok=self.runner.receiver_tok;model=self.runner.receiver;device=model.device
  t0=time.perf_counter();body=receiver_prompt(q)
  rendered=tok.apply_chat_template([{'role':'user','content':body}],tokenize=False,add_generation_prompt=True,enable_thinking=False)
  base=tok(rendered,return_tensors='pt');suffix=tok.encode(CFG['prefix'],add_special_tokens=False)
  assert suffix==self.prefix_ids
  ids=torch.cat([base['input_ids'],torch.tensor([suffix],dtype=base['input_ids'].dtype)],dim=1)
  mask=torch.cat([base['attention_mask'],torch.ones((1,len(suffix)),dtype=base['attention_mask'].dtype)],dim=1)
  inputs={'input_ids':ids,'attention_mask':mask};t1=time.perf_counter()
  pos=int(torch.nonzero(mask[0],as_tuple=False)[-1,0]);n=ids.shape[1]
  tensors={k:v.to(device) for k,v in inputs.items()};sync();t2=time.perf_counter()
  calls=[];hook=model.lm_head.register_forward_pre_hook(lambda mod,args:calls.append(list(args[0].shape))) if not self.validated_probe else None
  with torch.cuda.device(device):
   ev0=torch.cuda.Event(enable_timing=True);ev1=torch.cuda.Event(enable_timing=True);ev0.record()
   out=model.model(**tensors,use_cache=False,return_dict=True,output_hidden_states=False,output_attentions=False)
   assert out.past_key_values is None and pos==n-1 and int(mask.sum())==n
   last=out.last_hidden_state[:,pos:pos+1,:];logits=model.lm_head(last)[0,0,:].float();ev1.record();sync();t3=time.perf_counter()
   labels=display_labels(len(q['choice_text']));assert labels==q['choice_labels']
   label_logits=torch.stack([torch.logsumexp(logits[self.ix[l]],dim=0) for l in labels])
   logp=torch.log_softmax(label_logits,dim=0);p=logp.exp();ps=p.cpu().tolist();sync();t4=time.perf_counter()
   u=float((1-p.max()).item());sync();t5=time.perf_counter()
  if hook:
   hook.remove();assert calls==[[1,1,4096]]
   assert base['input_ids'][0].tolist()==tok.apply_chat_template([{'role':'user','content':body}],tokenize=True,add_generation_prompt=True,enable_thinking=False)
   self.validated_probe=True
  meta={'ProbeMax':u,'p_labels':dict(zip(labels,ps)),'argmax_probe_label':labels[max(range(len(ps)),key=ps.__getitem__)],'probe_ids_sha256':hashlib.sha256(ids.numpy().tobytes()).hexdigest(),'input_tokens':n,'last_valid_position':pos,'tokenization_prefix_ms':(t1-t0)*1000,'prepare_transfer_ms':(t2-t1)*1000,'prefill_projection_ms':(t3-t2)*1000,'label_distribution_ms':(t4-t3)*1000,'score_ms':(t5-t4)*1000,'GPU_prefill_projection_event_ms':float(ev0.elapsed_time(ev1)),'first_formal_check':bool(hook),'LM_head_input_shapes':calls if hook else None,'cache_reused':False}
  del out,last,logits,tensors,p,logp,label_logits,inputs,base,ids,mask
  self.in_probe=False
  return u,meta
 @torch.inference_mode()
 def action(self,q,a):
  first=self.action_first[a];self.action_first[a]=False
  assert a in ['R','T','C']
  result=self.runner.request(q,{'R':'receiver_only','T':'text','C':'c2c'}[a])
  # Native diagnostics are not model inputs. They are checked after timing.
  result['cold_first_native_action_after_load']=first
  return result
 def validate_and_release(self,result):
  validate_result(result,result.get('selected'))
  self.check_hooks()
