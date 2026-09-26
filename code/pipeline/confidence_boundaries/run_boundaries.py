"""Fixed ProbeMax port. Only machine d is opened after each threshold freeze."""
from common import *
compute()
import numpy as np, math, gc
from scipy.stats import binom,beta
import torch,transformers
from transformers import AutoTokenizer,AutoModelForCausalLM
from receiver_prompt import receiver_prompt,display_labels
CFG=read(P/'frozen_config.json');Q=CFG['q_grid']
torch.set_num_threads(1);torch.set_num_interop_threads(1)
torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False
assert torch.cuda.is_available() and torch.cuda.device_count()==1
IDS={ds:{s:read(P/f'splits/{ds}_{s}_ids.json') for s in ['fit','cal','dev']} for ds in DATASETS}
REPS={ds:{s:read(P/f'splits/{ds}_{s}_representatives.json') for s in ['fit','cal','dev']} for ds in DATASETS}
queries={ds:{r['id']:r for s in ['train','dev'] for r in jl(P/f'inputs/{ds}_{s}_queries.jsonl')} for ds in DATASETS}
assert all(set(r)=={'id','question_stem','choice_labels','choice_text'} for dd in queries.values() for r in dd.values())
assert not (P/'records/probe_attempts.jsonl').exists(),'No restart; successful ids must never be resampled'
attempts=0; allnew={}; data={}; deployments={}; tests=[]; route_files=[]
oldprobes=jl(OLD/'records/probe_records.jsonl'); assert len(oldprobes)==4208
oldby={r['id']:r for r in oldprobes}
assert len(oldby)==4208 and set(oldby)==set(queries['obqa'])
data['large','obqa']=oldby
csvout(P/'records/reused_probe_index_4208.csv',[{'pair':'large','dataset':'obqa','id':r['id'],'split':r['split'],'source_path':str(OLD/'records/probe_records.jsonl'),'source_line':j+1,'probe_ids_sha256':r['probe_ids_sha256'],'protocol_sha256':r['protocol_sha256']} for j,r in enumerate(oldprobes)])
def calibrate(pair,ds):
 dd=data[pair,ds]; ids=REPS[ds]['fit']; vals=sorted(dd[i]['ProbeMax'] for i in ids);nfit=len(ids)
 thresholds=[vals[(j*nfit+19)//20-1] if j<20 else 'Infinity' for j in range(1,21)]
 if (pair,ds)==('large','obqa'):assert thresholds==read(OLD/'thresholds/new_thresholds.json')['ProbeMax']
 path=P/f'thresholds/{pair}_{ds}.json';save(path,{'thresholds':thresholds,'N_fit':nfit,'q':Q,'fit_ids':ids,'fit_scores_sha256':hashlib.sha256(json.dumps([(i,dd[i]['ProbeMax']) for i in ids]).encode()).hexdigest()})
 freeze(f'thresholds/{pair}_{ds}_FREEZE.json',[path],cal_d_read=False,gold_read=False)
 # Whitelist machine disagreement; correctness and gold never leave this projection.
 needed=set(REPS[ds]['cal']);dmap={}
 with (V2/'labels/full_train_SCORING_V2.jsonl').open() as f:
  for line in f:
   r=json.loads(line)
   if r['pair']==pair and r['dataset']==ds and r['id'] in needed:dmap[r['id']]={b:int(r['o_R']!=r['o_'+b]) for b in REFS}
   del r
 assert set(dmap)==needed
 writejl(P/f'inputs/{pair}_{ds}_cal_machine_d.jsonl',[{'id':i,**dmap[i]} for i in REPS[ds]['cal']])
 u=np.array([dd[i]['ProbeMax'] for i in REPS[ds]['cal']])
 for b in REFS:
  tag=key(pair,ds,b);depfile=P/f'deployments/{tag}.json'
  if tag=='large_obqa_T':
   tr=[r for r in csvread(OLD/'summary/calibration_new_60.csv') if r['family']=='ProbeMax'];assert len(tr)==20
   rr=[]
   for r in tr:
    rr.append({'pair':pair,'dataset':ds,'reference':b,'q':float(r['q']),'threshold':r['threshold'] if r['threshold']=='Infinity' else float(r['threshold']),'N':int(r['N']),'n_R':int(r['n_R']),'changed':int(r['changed']),'conditional_risk':float(r['conditional_risk']) if r['conditional_risk'] else None,'p_value':float(r['p_value']),'CP_upper_0_999':float(r['CP_upper_0_999']),'accepted':r['accepted']=='True','coverage':float(r['coverage']),'calculation_identity':'reused'})
   dep=read(OLD/'models/deployment.json')['ProbeMax'];assert dep['q']==.8
  else:
   rr=[];d=np.array([dmap[i][b] for i in REPS[ds]['cal']],bool)
   for q,t in zip(Q,thresholds):
    mask=u<=tv(t);n=int(mask.sum());k=int(d[mask].sum());pv=float(binom.cdf(k,n,.05)) if n else 1.;cp=float(beta.ppf(.999,k+1,n-k)) if n and k<n else 1.
    r={'pair':pair,'dataset':ds,'reference':b,'q':q,'threshold':t,'N':len(u),'n_R':n,'changed':k,'conditional_risk':k/n if n else None,'p_value':pv,'CP_upper_0_999':cp,'accepted':pv<=.001,'coverage':n/len(u),'calculation_identity':'new'};rr.append(r);append(P/'records/calibration_new.jsonl',r)
   accepted=[r for r in rr if r['accepted']];chosen=accepted[-1] if accepted else None
   dep={'q':chosen['q'] if chosen else 0.,'threshold':chosen['threshold'] if chosen else None,'mode':('fixed_R' if chosen['q']==1 else 'selective') if chosen else 'fixed_reference','accepted_q':[r['q'] for r in accepted],'calibration':chosen}
  tests.extend(rr);deployments[tag]=dep;save(depfile,dep)
  csvout(P/f'deployments/{tag}_tests.csv',rr)
  freeze(f'deployments/{tag}_FREEZE.json',[depfile,P/f'deployments/{tag}_tests.csv',P/f'thresholds/{pair}_{ds}_FREEZE.json'],dev_probes_read=tag=='large_obqa_T',dev_gold_read=False,identity='reused historical exposure' if tag=='large_obqa_T' else 'new predetermined stratum')
  print('DEPLOYMENT_FROZEN',tag,dep['q'],dep['mode'],flush=True)
def freeze_routes(pair,ds):
 dd=data[pair,ds];oldroutes={r['id']:r for r in jl(OLD/'records/dev_scored_routes.jsonl')} if (pair,ds)==('large','obqa') else {}
 for b in REFS:
  tag=key(pair,ds,b);dep=deployments[tag];out=[]
  for i in IDS[ds]['dev']:
   p=dd[i];t=time.perf_counter_ns();m=route(p['ProbeMax'],dep);elapsed=(time.perf_counter_ns()-t)/1e6
   if tag=='large_obqa_T':
    old=oldroutes[i];assert m==(old['route']['ProbeMax']=='R');elapsed=old['selector_ms']['ProbeMax']
   measured=p['probe_core_ms']+p['ProbeMax_score_ms']+elapsed
   out.append({'pair':pair,'dataset':ds,'reference':b,'id':i,'route':'R' if m else b,'ProbeMax':p['ProbeMax'],'selector_ms':elapsed,'measured_selective_overhead_ms':measured,'required_overhead_ms':measured if dep['mode']=='selective' else 0.,'probe_ids_sha256':p['probe_ids_sha256'],'identity':'reused' if tag=='large_obqa_T' else 'new'})
  dest=P/f'records/{tag}_routes.jsonl';writejl(dest,out);route_files.append(dest)
  freeze(f'deployments/{tag}_ROUTES_FREEZE.json',[dest,P/f'deployments/{tag}_FREEZE.json'],gold_or_dev_answers_read=False,identity=out[0]['identity'])
# Large/OBQA scores and its Text point remain immutable; no model request.
calibrate('large','obqa');freeze_routes('large','obqa')

def run_receiver(pair,datasets):
 global attempts
 spec=CFG['models'][pair];protocol_dir=P/f'protocol/{pair}';protocol_dir.mkdir()
 labels=sorted({l for ds in datasets for r in queries[ds].values() for l in display_labels(len(r['choice_text']))})
 stop();start=time.perf_counter();tokenizer=AutoTokenizer.from_pretrained(spec['path'],local_files_only=True)
 if tokenizer.pad_token is None:tokenizer.pad_token=tokenizer.eos_token
 assert hashlib.sha256(tokenizer.chat_template.encode()).hexdigest()==spec['chat_template_sha256']
 prefix_ids=tokenizer.encode(CFG['prefix'],add_special_tokens=False)
 assert tokenizer.decode(prefix_ids,skip_special_tokens=False,clean_up_tokenization_spaces=False)==CFG['prefix']
 sets={l:[] for l in labels};mapping=[];special=set(tokenizer.all_special_ids)
 for v in sorted(set(tokenizer.get_vocab().values())):
  if v in special:continue
  decoded=tokenizer.decode([v],skip_special_tokens=False,clean_up_tokenization_spaces=False)
  if decoded.strip() in sets:
   l=decoded.strip();sets[l].append(v);mapping.append({'label':l,'token_id':v,'token_string':tokenizer.convert_ids_to_tokens(v),'decoded':decoded})
 assert all(sets.values()) and len(set(v for s in sets.values() for v in s))==sum(map(len,sets.values()))
 save(protocol_dir/'label_token_sets.json',sets);writejl(protocol_dir/'token_decode_mapping.jsonl',mapping)
 save(protocol_dir/'prefix_ids.json',{'literal':CFG['prefix'],'ids':prefix_ids,'encoding':'add_special_tokens=False','chat_template_sha256':spec['chat_template_sha256']})
 (protocol_dir/'chat_template.jinja').write_text(tokenizer.chat_template)
 def construct(row):
  body=receiver_prompt(row)
  rendered=tokenizer.apply_chat_template([{'role':'user','content':body}],tokenize=False,add_generation_prompt=True,enable_thinking=False)
  base=tokenizer(rendered,return_tensors='pt')
  suffix=tokenizer.encode(CFG['prefix'],add_special_tokens=False);assert suffix==prefix_ids
  ids=torch.cat([base['input_ids'],torch.tensor([suffix],dtype=base['input_ids'].dtype)],dim=1)
  mask=torch.cat([base['attention_mask'],torch.ones((1,len(suffix)),dtype=base['attention_mask'].dtype)],dim=1)
  return rendered,base,{'input_ids':ids,'attention_mask':mask}
 first=queries[datasets[0]][IDS[datasets[0]]['fit'][0]];rendered,base,inp=construct(first)
 native_ids=tokenizer.apply_chat_template([{'role':'user','content':receiver_prompt(first)}],tokenize=True,add_generation_prompt=True,enable_thinking=False)
 assert native_ids==base['input_ids'][0].tolist()
 assert tokenizer(rendered,add_special_tokens=False)['input_ids']==native_ids
 decoded=tokenizer.decode(inp['input_ids'][0],skip_special_tokens=False,clean_up_tokenization_spaces=False)
 assert decoded.count('<|im_start|>assistant\n')==1 and decoded.count('<|im_start|>user\n')==1
 assistant=decoded.split('<|im_start|>assistant\n')[1]
 assert assistant.endswith(CFG['prefix']) and '<|im_end|>' not in assistant and '<|im_start|>' not in assistant
 save(protocol_dir/'FIRST_INPUT_CHECK.json',{'id':first['id'],'decoded_full_input':decoded,'decoded_assistant_content':assistant,'original_generation_prefix_ids':native_ids,'probe_ids':inp['input_ids'][0].tolist(),'prefix_ids':prefix_ids,'role_boundary_pass':True,'prefix_position_pass':True,'no_duplicate_BOS_EOS':True,'gold_or_correctness_read':False,'model_scores_generated':0,'official_interface_reference':'https://huggingface.co/docs/transformers/v4.52.3/chat_templating'})
 freeze(f'protocol/{pair}/PROBE_PROTOCOL_FREEZE.json',list(protocol_dir.glob('*'))+[P/'src/receiver_prompt.py',P/'src/run_boundaries.py',P/'frozen_config.json'],prefill_attempts=attempts,gold_read=False)
 tokenizer_mapping_seconds=time.perf_counter()-start
 print('PROBE_PROTOCOL_FROZEN',sha(protocol_dir/'PROBE_PROTOCOL_FREEZE.json'),sets,repr(assistant),flush=True)
 stop();start=time.perf_counter();lm=AutoModelForCausalLM.from_pretrained(spec['path'],local_files_only=True,torch_dtype=torch.bfloat16,attn_implementation='sdpa',low_cpu_mem_usage=True).to('cuda:0').eval().requires_grad_(False)
 torch.cuda.synchronize();load_seconds=time.perf_counter()-start
 assert lm.config.hidden_size==spec['hidden_size'] and lm.config.num_hidden_layers==spec['num_hidden_layers'] and lm.config._attn_implementation=='sdpa'
 assert all(0<=v<lm.config.vocab_size for s in sets.values() for v in s)
 save(P/f'evidence/{pair}_model_startup.json',{'tokenizer_mapping_check_wall_seconds':tokenizer_mapping_seconds,'model_load_wall_seconds':load_seconds,'torch':torch.__version__,'transformers':transformers.__version__,'GPU':str(torch.cuda.get_device_properties(0)),'CUDA_VISIBLE_DEVICES':os.environ.get('CUDA_VISIBLE_DEVICES'),'model_path':spec['path'],'dtype':'bfloat16','attention':'sdpa','receiver_only':True,'helper_loaded':False,'generation':False})
 ix={l:torch.tensor(v,device='cuda:0') for l,v in sets.items()};union=torch.cat(list(ix.values()))
 probes={}
 def probe_split(ds,split):
  global attempts
  outrows=[]
  for j,i in enumerate(IDS[ds][split]):
   stop()
   if (ds,i) in probes:
    r=probes[ds,i];assert r['split']==split and r['protocol_sha256']==sha(protocol_dir/'PROBE_PROTOCOL_FREEZE.json');outrows.append(r);continue
   assert attempts<7044
   torch.cuda.synchronize();t0=time.perf_counter();rendered,base,inputs=construct(queries[ds][i]);t1=time.perf_counter()
   pos=int(torch.nonzero(inputs['attention_mask'][0],as_tuple=False)[-1,0]);n=inputs['input_ids'].shape[1]
   tensors={k:v.to('cuda:0') for k,v in inputs.items()};torch.cuda.synchronize();t2=time.perf_counter()
   # Audit I/O occurs before forward and is excluded from online component timing.
   audit0=time.perf_counter();attempts+=1
   append(P/'records/probe_attempts.jsonl',{'pair':pair,'dataset':ds,'attempt':attempts,'id':i,'split':split,'utc':utc(),'event':'START_PREFILL','job_id':os.environ['PBS_JOBID']})
   audit_s=time.perf_counter()-audit0
   cold=not probes;calls=[];item_labels=display_labels(len(queries[ds][i]['choice_text']));item_union=torch.cat([ix[l] for l in item_labels])
   hook=lm.lm_head.register_forward_pre_hook(lambda mod,args:calls.append(list(args[0].shape))) if cold else None
   ev0=torch.cuda.Event(enable_timing=True);ev1=torch.cuda.Event(enable_timing=True)
   with torch.inference_mode():
    ev0.record();out=lm.model(**tensors,use_cache=False,return_dict=True,output_hidden_states=False,output_attentions=False)
    assert out.past_key_values is None and pos==n-1 and int(inputs['attention_mask'].sum())==n
    last=out.last_hidden_state[:,pos:pos+1,:]
    logits=lm.lm_head(last)[0,0,:].float();ev1.record();torch.cuda.synchronize();t3=time.perf_counter()
    label_logits=torch.stack([torch.logsumexp(logits[ix[l]],dim=0) for l in item_labels])
    logp=torch.log_softmax(label_logits,dim=0);p=logp.exp();ps=p.cpu().tolist();torch.cuda.synchronize();t4=time.perf_counter()
    a=time.perf_counter();umax=float((1-p.max()).item());torch.cuda.synchronize();max_ms=(time.perf_counter()-a)*1000
    a=time.perf_counter();mass=float(torch.exp(torch.logsumexp(logits[item_union],0)-torch.logsumexp(logits,0)).item());torch.cuda.synchronize();diag_ms=(time.perf_counter()-a)*1000
   if hook:
    hook.remove();assert calls==[[1,1,spec['hidden_size']]]
    save(P/f'evidence/{pair}_FIRST_FORMAL_FORWARD_CHECK.json',{'id':i,'attempt':attempts,'LM_head_input_shapes':calls,'output_vocab_shape':list(logits.shape),'dtype_projection_input':str(last.dtype),'stable_probability_dtype':str(p.dtype),'backbone_calls':1,'extra_warmup_or_check_forward':0,'kept_as_formal_sample':True,'past_key_values':None})
   assert np.isfinite(ps).all() and abs(sum(ps)-1)<2e-6 and 0<=mass<=1.00001 and 0<=umax<=1
   r={'pair':pair,'dataset':ds,'id':i,'split':split,'row':j,'attempt':attempts,'protocol_sha256':sha(protocol_dir/'PROBE_PROTOCOL_FREEZE.json'),'probe_ids':inputs['input_ids'][0].tolist(),'probe_ids_sha256':hashlib.sha256(inputs['input_ids'].numpy().tobytes()).hexdigest(),'hash_encoding':'contiguous int64 little endian input_ids bytes','original_generation_prefix_ids_sha256':hashlib.sha256(base['input_ids'].numpy().tobytes()).hexdigest(),'rendered_sha256':hashlib.sha256(rendered.encode()).hexdigest(),'input_tokens':int(n),'last_valid_position':pos,'p_labels':dict(zip(item_labels,ps)),'ProbeMax':umax,'label_union_mass':mass,'argmax_probe_label':item_labels[int(np.argmax(ps))],'cold_first_after_load':cold,'tokenization_prefix_ms':(t1-t0)*1000,'prepare_transfer_ms':(t2-t1)*1000,'prefill_projection_ms':(t3-t2-audit_s)*1000,'label_distribution_ms':(t4-t3)*1000,'probe_core_ms':(t4-t0-audit_s)*1000,'ProbeMax_score_ms':max_ms,'diagnostic_mass_ms':diag_ms,'GPU_prefill_projection_event_ms':ev0.elapsed_time(ev1),'attempt_audit_io_ms_excluded':audit_s*1000}
   append(P/'records/probe_records.jsonl',r);probes[ds,i]=r;allnew[pair,ds,i]=r;outrows.append(r)
   del out,last,logits,tensors,p,logp,label_logits
   if (j+1)%100==0 or j+1==len(IDS[ds][split]):
    save(P/'PROBE_PROGRESS.json',{'split':split,'split_success':j+1,'pair':pair,'dataset':ds,'total_success':len(allnew),'attempts':attempts,'remaining_attempt_budget':7044-attempts,'success_ids_file':'records/probe_records.jsonl','last_id':i,'utc':utc()});print('PROBE',split,j+1,'TOTAL',len(probes),flush=True)
  return outrows

 for ds in datasets:
  data[pair,ds]={}
  for split in ['fit','cal']:
   rows=probe_split(ds,split);data[pair,ds].update({r['id']:r for r in rows});writejl(P/f'records/{pair}_{ds}_{split}_probes.jsonl',rows)
  freeze(f'thresholds/{pair}_{ds}_PROBES_FREEZE.json',[P/f'records/{pair}_{ds}_{s}_probes.jsonl' for s in ['fit','cal']],cal_d_read=False)
  calibrate(pair,ds)
 # All train scores and policies for this receiver frozen before any new dev prefill.
 for ds in datasets:
  rows=probe_split(ds,'dev');data[pair,ds].update({r['id']:r for r in rows});writejl(P/f'records/{pair}_{ds}_dev_probes.jsonl',rows)
  freeze_routes(pair,ds)
 del lm,ix,union;gc.collect();torch.cuda.empty_cache();torch.cuda.synchronize()
run_receiver('large',['arc'])
run_receiver('small',['obqa','arc'])
assert attempts==len(allnew)==7044
assert len(tests)==160 and sum(r['calculation_identity']=='new' for r in tests)==140
csvout(P/'summary/calibration_all_160.csv',tests)
csvout(P/'summary/calibration_new_140.csv',[r for r in tests if r['calculation_identity']=='new'])
csvout(P/'summary/calibration_reused_20.csv',[r for r in tests if r['calculation_identity']=='reused'])
save(P/'deployments/all.json',deployments)
freeze('ALL_ROUTES_FREEZE.json',route_files+[P/'summary/calibration_all_160.csv',P/'deployments/all.json'],new_deployment_rows=3422,reused_deployment_rows=742,gold_or_correctness_associated=False)
freeze('PROBES_COMPLETE.json',[P/'records/probe_records.jsonl',P/'records/probe_attempts.jsonl',P/'records/reused_probe_index_4208.csv'],new_attempts=attempts,new_success=len(allnew),reused=4208)
save(P/'CONTROLS_COMPLETE.json',{'utc':utc(),'heads':0,'fit_attempts':0,'probes':7044,'prefill_attempts':7044,'new_calibration':140,'reused_calibration':20,'new_dev_routes':3422,'reused_dev_routes':742,'helper_forward':0,'answer_generation':0,'new_protocol_requests':0})
print('ALL_ROUTES_FROZEN',flush=True)
