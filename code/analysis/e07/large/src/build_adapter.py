from common import *
s=(E2E/'native_adapter.py').read_text()
s=s.replace('"""Use P2-10 native calls; only add request instrumentation and online E1."""','"""Minimal adaptation of existing E2E runtime: unchanged native R/T/C; frozen ProbeMax replaces E1, no W/head."""')
s=s.replace('from ac_p2_10 import ac_request,validate_result','from ac_p2_10 import validate_result')
a=s.index("  t=time.perf_counter();assert sha(cfg['W_path'])")
b=s.index("  for role in ['helper','receiver']:",a)
s=s[:a]+"  self.trace=[];self.active=False;self.trace_handles=[]\n"+s[b:]
s=s.replace(";self.validated_E1=False",";self.validated_probe=False")
s=s.replace(",'AC_W_sha256':cfg['W_sha256']", "")
s=s.replace('E1','probe')
a=s.index(' @torch.inference_mode()\n def e1(');b=s.index(' @torch.inference_mode()\n def action(',a)
probe=''' @torch.inference_mode()
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
'''
s=s[:a]+probe+s[b:]
s=s.replace("  if a=='A':result=ac_request(self.runner,q,self.W,self.layers)\n  else:result=self.runner.request(q,{'R':'receiver_only','T':'text','C':'c2c'}[a])", "  assert a in ['R','T','C']\n  result=self.runner.request(q,{'R':'receiver_only','T':'text','C':'c2c'}[a])")
needle="  self.baseline=self.hook_signature();self.first_request=True;self.action_first={a:True for a in A};self.validated_probe=False"
assert needle in s
s=s.replace(needle,needle+"\n  self.prefix_ids=read(P/'protocol/prefix_ids.json')['ids'];self.ix={l:torch.tensor(v,device='cuda:1') for l,v in read(P/'protocol/label_token_sets.json').items()}\n  assert self.runner.receiver_tok.encode(CFG['prefix'],add_special_tokens=False)==self.prefix_ids\n  for l,ix in read(P/'protocol/label_token_sets.json').items():\n   assert all(v not in self.runner.receiver_tok.all_special_ids and self.runner.receiver_tok.decode([v],skip_special_tokens=False,clean_up_tokenization_spaces=False).strip()==l for v in ix)")
(P/'src/native_adapter.py').write_text(s)
