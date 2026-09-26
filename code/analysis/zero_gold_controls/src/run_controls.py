"""Only PBS. No correctness/gold/reference score reads before deployment freeze.
The sole LR fit is isolated to id/text/d. Receiver outputs are features only.
"""
from common import *
compute()
import numpy as np,joblib,warnings,math,resource
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from scipy.special import expit
from scipy.stats import binom,beta
import torch,transformers
from transformers import AutoTokenizer,AutoModelForCausalLM
from receiver_prompt import receiver_prompt
CFG=read(P/'frozen_config.json');Q=CFG['q_grid']
torch.set_num_threads(1);torch.set_num_interop_threads(1)
torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False
assert torch.cuda.is_available() and torch.cuda.device_count()==1
IDS={s:read(P/f'splits/{s}_ids.json') for s in ['fit','cal','dev']}
query_rows=jl(P/'inputs/train_queries.jsonl')+jl(P/'inputs/dev_queries.jsonl')
assert all(set(r)=={'id','question_stem','choice_labels','choice_text'} for r in query_rows)
queries={r['id']:r for r in query_rows};assert len(queries)==4208
assert all(queries[i]['choice_labels']==list('ABCD') and len(queries[i]['choice_text'])==4 for ids in IDS.values() for i in ids)
def word_text(r):return '\n'.join(['Question: '+r['question_stem'],'Choices:']+[a+': '+b for a,b in zip(r['choice_labels'],r['choice_text'])])
def fit_word(interface):
 assert all(set(r)=={'id','text','d'} for r in interface)
 assert [r['id'] for r in interface]==IDS['fit'] and len(interface)==2100
 assert not (P/'records/fit_attempts.jsonl').exists(),'No second fit attempt'
 vec=TfidfVectorizer(**{**CFG['word_tfidf'],'ngram_range':tuple(CFG['word_tfidf']['ngram_range'])})
 t=time.perf_counter();c=time.process_time();X=vec.fit_transform([r['text'] for r in interface]);vectorize_wall=time.perf_counter()-t;vectorize_cpu=time.process_time()-c
 y=np.array([r['d'] for r in interface]);assert set(y)=={0,1}
 append(P/'records/fit_attempts.jsonl',{'event':'START_LR','attempt':1,'utc':utc()})
 t=time.perf_counter();c=time.process_time()
 with warnings.catch_warnings(record=True) as captured:
  warnings.simplefilter('always');model=LogisticRegression(**CFG['word_LR']).fit(X,y)
 fit_wall=time.perf_counter()-t;fit_cpu=time.process_time()-c
 assert np.array_equal(model.classes_,[0,1]) and np.isfinite(model.coef_).all()
 assert np.allclose(model.predict_proba(X[:1])[:,1],expit(np.asarray(X[:1]@model.coef_.T).ravel()+model.intercept_[0]))
 joblib.dump(vec,P/'models/word_tfidf.joblib');joblib.dump(model,P/'models/WordD.joblib')
 save(P/'models/WordD_receipt.json',{'id_text_d_only':True,'N':2100,'d_positive':int(y.sum()),'fit_attempts':1,'iterations':int(model.n_iter_.max()),'warnings':[str(w.message) for w in captured],'vocabulary_size':len(vec.vocabulary_),'vectorizer_settings':{k:str(v) for k,v in vec.get_params().items()},'vectorizer_wall_seconds':vectorize_wall,'vectorizer_CPU_seconds':vectorize_cpu,'LR_wall_seconds':fit_wall,'LR_CPU_seconds':fit_cpu,'converged':not any('converge' in str(w.message).lower() for w in captured),'CPU_threads':1})
 freeze('WORD_MODEL_FREEZE.json',[P/'models/word_tfidf.joblib',P/'models/WordD.joblib',P/'models/WordD_receipt.json',P/'inputs/word_fit_id_text_d.jsonl'],cal_d_read=False,gold_read=False)
 return vec,model
fit_d=jl(P/'inputs/candidate_fit.jsonl');assert all(set(r)=={'id','d'} for r in fit_d) and [r['id'] for r in fit_d]==IDS['fit']
interface=[{'id':r['id'],'text':word_text(queries[r['id']]),'d':r['d']} for r in fit_d]
writejl(P/'inputs/word_fit_id_text_d.jsonl',interface)
vec,word=fit_word(interface);del interface,fit_d
def score_word(ids,policy=None):
 rows=[]
 for i in ids:
  stop();t=time.perf_counter_ns();txt=word_text(queries[i]);a=time.perf_counter_ns();x=vec.transform([txt]);b=time.perf_counter_ns();u=float(word.predict_proba(x)[0,1]);c=time.perf_counter_ns()
  selected=route(u,policy) if policy else None;e=time.perf_counter_ns()
  rows.append({'id':i,'WordD':u,'text_ms':(a-t)/1e6,'vectorize_ms':(b-a)/1e6,'LR_ms':(c-b)/1e6,'feature_head_ms':(c-t)/1e6,'selector_ms':(e-c)/1e6 if policy else None,'route_R':selected})
 return rows
word_scores={s:score_word(IDS[s]) for s in ['fit','cal']}
for s,rows in word_scores.items():writejl(P/f'records/word_{s}_scores.jsonl',rows)
stop();start=time.perf_counter();tokenizer=AutoTokenizer.from_pretrained(CFG['model']['path'],local_files_only=True)
if tokenizer.pad_token is None:tokenizer.pad_token=tokenizer.eos_token
assert hashlib.sha256(tokenizer.chat_template.encode()).hexdigest()==CFG['model']['chat_template_sha256']
prefix_ids=tokenizer.encode(CFG['prefix'],add_special_tokens=False)
assert tokenizer.decode(prefix_ids,skip_special_tokens=False,clean_up_tokenization_spaces=False)==CFG['prefix']
sets={l:[] for l in 'ABCD'};mapping=[];special=set(tokenizer.all_special_ids)
for v in sorted(set(tokenizer.get_vocab().values())):
 if v in special:continue
 decoded=tokenizer.decode([v],skip_special_tokens=False,clean_up_tokenization_spaces=False)
 if decoded.strip() in sets:
  l=decoded.strip();sets[l].append(v);mapping.append({'label':l,'token_id':v,'token_string':tokenizer.convert_ids_to_tokens(v),'decoded':decoded})
assert all(sets.values()) and len(set(v for s in sets.values() for v in s))==sum(map(len,sets.values()))
save(P/'protocol/label_token_sets.json',sets);writejl(P/'protocol/token_decode_mapping.jsonl',mapping)
save(P/'protocol/prefix_ids.json',{'literal':CFG['prefix'],'ids':prefix_ids,'encoding':'add_special_tokens=False','chat_template_sha256':CFG['model']['chat_template_sha256']})
(P/'protocol/chat_template.jinja').write_text(tokenizer.chat_template)
def construct(row):
 body=receiver_prompt(row)
 rendered=tokenizer.apply_chat_template([{'role':'user','content':body}],tokenize=False,add_generation_prompt=True,enable_thinking=False)
 base=tokenizer(rendered,return_tensors='pt')
 suffix=tokenizer.encode(CFG['prefix'],add_special_tokens=False);assert suffix==prefix_ids
 ids=torch.cat([base['input_ids'],torch.tensor([suffix],dtype=base['input_ids'].dtype)],dim=1)
 mask=torch.cat([base['attention_mask'],torch.ones((1,len(suffix)),dtype=base['attention_mask'].dtype)],dim=1)
 return rendered,base,{'input_ids':ids,'attention_mask':mask}
first=queries[IDS['fit'][0]];rendered,base,inp=construct(first)
native_ids=tokenizer.apply_chat_template([{'role':'user','content':receiver_prompt(first)}],tokenize=True,add_generation_prompt=True,enable_thinking=False)
assert native_ids==base['input_ids'][0].tolist()
assert tokenizer(rendered,add_special_tokens=False)['input_ids']==native_ids
decoded=tokenizer.decode(inp['input_ids'][0],skip_special_tokens=False,clean_up_tokenization_spaces=False)
assert decoded.count('<|im_start|>assistant\n')==1 and decoded.count('<|im_start|>user\n')==1
assistant=decoded.split('<|im_start|>assistant\n')[1]
assert assistant.endswith(CFG['prefix']) and '<|im_end|>' not in assistant and '<|im_start|>' not in assistant
save(P/'protocol/FIRST_INPUT_CHECK.json',{'id':first['id'],'decoded_full_input':decoded,'decoded_assistant_content':assistant,'original_generation_prefix_ids':native_ids,'probe_ids':inp['input_ids'][0].tolist(),'prefix_ids':prefix_ids,'role_boundary_pass':True,'prefix_position_pass':True,'no_duplicate_BOS_EOS':True,'gold_or_correctness_read':False,'model_scores_generated':0,'official_interface_reference':'https://huggingface.co/docs/transformers/v4.52.3/chat_templating'})
freeze('PROBE_PROTOCOL_FREEZE.json',list((P/'protocol').glob('*'))+[P/'src/receiver_prompt.py',P/'src/run_controls.py',P/'frozen_config.json'],prefill_attempts=0,gold_read=False)
tokenizer_mapping_seconds=time.perf_counter()-start
print('PROBE_PROTOCOL_FROZEN',sha(P/'PROBE_PROTOCOL_FREEZE.json'),sets,repr(assistant),flush=True)
stop();start=time.perf_counter();lm=AutoModelForCausalLM.from_pretrained(CFG['model']['path'],local_files_only=True,torch_dtype=torch.bfloat16,attn_implementation='sdpa',low_cpu_mem_usage=True).to('cuda:0').eval().requires_grad_(False)
torch.cuda.synchronize();load_seconds=time.perf_counter()-start
assert lm.config.hidden_size==4096 and lm.config.num_hidden_layers==36 and lm.config._attn_implementation=='sdpa'
assert all(0<=v<lm.config.vocab_size for s in sets.values() for v in s)
save(P/'evidence/model_startup.json',{'tokenizer_mapping_check_wall_seconds':tokenizer_mapping_seconds,'model_load_wall_seconds':load_seconds,'torch':torch.__version__,'transformers':transformers.__version__,'GPU':str(torch.cuda.get_device_properties(0)),'CUDA_VISIBLE_DEVICES':os.environ.get('CUDA_VISIBLE_DEVICES'),'model_path':CFG['model']['path'],'dtype':'bfloat16','attention':'sdpa','receiver_only':True,'helper_loaded':False,'generation':False})
ix={l:torch.tensor(v,device='cuda:0') for l,v in sets.items()};union=torch.cat(list(ix.values()))
probes={};attempts=0
if (P/'records/probe_attempts.jsonl').exists():attempts=len(jl(P/'records/probe_attempts.jsonl'))
if (P/'records/probe_records.jsonl').exists():probes={r['id']:r for r in jl(P/'records/probe_records.jsonl')}
def probe_split(split):
 global attempts
 outrows=[]
 for j,i in enumerate(IDS[split]):
  stop()
  if i in probes:
   r=probes[i];assert r['split']==split and r['protocol_sha256']==sha(P/'PROBE_PROTOCOL_FREEZE.json');outrows.append(r);continue
  assert attempts<4208
  torch.cuda.synchronize();t0=time.perf_counter();rendered,base,inputs=construct(queries[i]);t1=time.perf_counter()
  pos=int(torch.nonzero(inputs['attention_mask'][0],as_tuple=False)[-1,0]);n=inputs['input_ids'].shape[1]
  tensors={k:v.to('cuda:0') for k,v in inputs.items()};torch.cuda.synchronize();t2=time.perf_counter()
  # Audit I/O occurs before forward and is excluded from online component timing.
  audit0=time.perf_counter();attempts+=1
  append(P/'records/probe_attempts.jsonl',{'attempt':attempts,'id':i,'split':split,'utc':utc(),'event':'START_PREFILL','job_id':os.environ['PBS_JOBID']})
  audit_s=time.perf_counter()-audit0
  cold=not probes;calls=[]
  hook=lm.lm_head.register_forward_pre_hook(lambda mod,args:calls.append(list(args[0].shape))) if cold else None
  ev0=torch.cuda.Event(enable_timing=True);ev1=torch.cuda.Event(enable_timing=True)
  with torch.inference_mode():
   ev0.record();out=lm.model(**tensors,use_cache=False,return_dict=True,output_hidden_states=False,output_attentions=False)
   assert out.past_key_values is None and pos==n-1 and int(inputs['attention_mask'].sum())==n
   last=out.last_hidden_state[:,pos:pos+1,:]
   logits=lm.lm_head(last)[0,0,:].float();ev1.record();torch.cuda.synchronize();t3=time.perf_counter()
   label_logits=torch.stack([torch.logsumexp(logits[ix[l]],dim=0) for l in 'ABCD'])
   logp=torch.log_softmax(label_logits,dim=0);p=logp.exp();ps=p.cpu().tolist();torch.cuda.synchronize();t4=time.perf_counter()
   a=time.perf_counter();umax=float((1-p.max()).item());torch.cuda.synchronize();max_ms=(time.perf_counter()-a)*1000
   a=time.perf_counter();uent=float((-(p*logp).sum()/math.log(4)).item());torch.cuda.synchronize();ent_ms=(time.perf_counter()-a)*1000
   a=time.perf_counter();mass=float(torch.exp(torch.logsumexp(logits[union],0)-torch.logsumexp(logits,0)).item());torch.cuda.synchronize();diag_ms=(time.perf_counter()-a)*1000
  if hook:
   hook.remove();assert calls==[[1,1,4096]]
   save(P/'evidence/FIRST_FORMAL_FORWARD_CHECK.json',{'id':i,'attempt':attempts,'LM_head_input_shapes':calls,'output_vocab_shape':list(logits.shape),'dtype_projection_input':str(last.dtype),'stable_probability_dtype':str(p.dtype),'backbone_calls':1,'extra_warmup_or_check_forward':0,'kept_as_formal_sample':True,'past_key_values':None})
  assert np.isfinite(ps).all() and abs(sum(ps)-1)<2e-6 and 0<=mass<=1.00001 and 0<=umax<=1 and 0<=uent<=1.00001
  r={'id':i,'split':split,'row':j,'attempt':attempts,'protocol_sha256':sha(P/'PROBE_PROTOCOL_FREEZE.json'),'probe_ids':inputs['input_ids'][0].tolist(),'probe_ids_sha256':hashlib.sha256(inputs['input_ids'].numpy().tobytes()).hexdigest(),'hash_encoding':'contiguous int64 little endian input_ids bytes','original_generation_prefix_ids_sha256':hashlib.sha256(base['input_ids'].numpy().tobytes()).hexdigest(),'rendered_sha256':hashlib.sha256(rendered.encode()).hexdigest(),'input_tokens':int(n),'last_valid_position':pos,'p_labels':dict(zip('ABCD',ps)),'ProbeMax':umax,'ProbeEntropy':uent,'label_union_mass':mass,'argmax_probe_label':'ABCD'[int(np.argmax(ps))],'cold_first_after_load':cold,'tokenization_prefix_ms':(t1-t0)*1000,'prepare_transfer_ms':(t2-t1)*1000,'prefill_projection_ms':(t3-t2-audit_s)*1000,'label_distribution_ms':(t4-t3)*1000,'probe_core_ms':(t4-t0-audit_s)*1000,'ProbeMax_score_ms':max_ms,'ProbeEntropy_score_ms':ent_ms,'diagnostic_mass_ms':diag_ms,'GPU_prefill_projection_event_ms':ev0.elapsed_time(ev1),'attempt_audit_io_ms_excluded':audit_s*1000}
  append(P/'records/probe_records.jsonl',r);probes[i]=r;outrows.append(r)
  del out,last,logits,tensors,p,logp,label_logits
  if (j+1)%100==0 or j+1==len(IDS[split]):
   save(P/'PROBE_PROGRESS.json',{'split':split,'split_success':j+1,'total_success':len(probes),'attempts':attempts,'remaining_attempt_budget':4208-attempts,'success_ids_file':'records/probe_records.jsonl','last_id':i,'utc':utc()});print('PROBE',split,j+1,'TOTAL',len(probes),flush=True)
 return outrows
probe_scores={s:probe_split(s) for s in ['fit','cal']}
for s in ['fit','cal']:writejl(P/f'records/probe_{s}.jsonl',probe_scores[s])
freeze('FIT_CAL_PROBES_FREEZE.json',[P/'records/probe_fit.jsonl',P/'records/probe_cal.jsonl'],success=3466,attempts=attempts)
thresholds={};score_rows={}
for s in ['fit','cal']:
 score_rows[s]=[{'id':i,'ProbeMax':p['ProbeMax'],'ProbeEntropy':p['ProbeEntropy'],'WordD':w['WordD']} for i,p,w in zip(IDS[s],probe_scores[s],word_scores[s])]
 writejl(P/f'records/{s}_scores.jsonl',score_rows[s])
for f in NEW:
 vals=sorted(r[f] for r in score_rows['fit']);thresholds[f]=[vals[(step*2100+19)//20-1] if step<20 else 'Infinity' for step in range(1,21)]
save(P/'thresholds/new_thresholds.json',thresholds)
freeze('THRESHOLDS_FREEZE.json',[P/'thresholds/new_thresholds.json',P/'records/fit_scores.jsonl',P/'records/cal_scores.jsonl',P/'records/probe_fit.jsonl',P/'records/probe_cal.jsonl',P/'WORD_MODEL_FREEZE.json',P/'PROBE_PROTOCOL_FREEZE.json'],new_families=3,cal_d_read=False,gold_read=False)
# Sole calibration label opening occurs after all new thresholds are frozen.
cal_rows=jl(P/'inputs/candidate_cal.jsonl');assert [r['id'] for r in cal_rows]==IDS['cal'] and all(set(r)=={'id','d'} for r in cal_rows)
d=np.array([r['d'] for r in cal_rows],bool)
def test(n,k):
 return {'n_R':int(n),'changed':int(k),'conditional_risk':float(k/n) if n else None,'p_value':float(binom.cdf(k,n,.05)) if n else 1.,'CP_upper_0_999':float(beta.ppf(.999,k+1,n-k)) if n and k<n else 1.,'accepted':bool(n and binom.cdf(k,n,.05)<=.001)}
tests=[];deployment={}
for f in NEW:
 vals=np.array([r[f] for r in score_rows['cal']]);accepted=[]
 for q,t in zip(Q,thresholds[f]):
  mask=vals<=threshold_value(t);r={'family':f,'q':q,'threshold':t,'N':1366,**test(int(mask.sum()),int(d[mask].sum())),'coverage':float(mask.mean()),'marginal_change':float((mask&d).mean())};tests.append(r)
  append(P/'records/calibration_new.jsonl',r)
  if r['accepted']:accepted.append(r)
 chosen=accepted[-1] if accepted else None
 deployment[f]={'q':chosen['q'] if chosen else 0.,'threshold':chosen['threshold'] if chosen else None,'mode':('fixed_R' if chosen['q']==1 else 'selective') if chosen else 'fixed_T','accepted_q':[r['q'] for r in accepted],'calibration':chosen}
assert len(tests)==60;csvout(P/'summary/calibration_new_60.csv',tests)
old_tests=[r for r in csv.DictReader((OLD/'summary/calibration_100.csv').open()) if r['family'] in ['D','R']]
assert len(old_tests)==40
csvout(P/'summary/calibration_reused_40_original.csv',old_tests)
old_dep=read(OLD/'models/deployment.json')
for new,old in [('D','D'),('R2100','R')]:deployment[new]={**old_dep[old],'provenance':'directly reused original deployment; unchanged'}
assert deployment['D']['q']==.3 and deployment['R2100']['q']==.4
csvout(P/'summary/calibration_comparison_100.csv',[{**r,'family':'R2100' if r['family']=='R' else r['family'],'calculation_identity':'reused'} for r in old_tests]+[{**r,'calculation_identity':'new'} for r in tests])
save(P/'models/deployment.json',deployment)
freeze('DEPLOYMENT_FREEZE.json',[P/'models/deployment.json',P/'summary/calibration_new_60.csv',P/'summary/calibration_reused_40_original.csv',P/'summary/calibration_comparison_100.csv',P/'THRESHOLDS_FREEZE.json'],new_tests=60,reused_tests=40,total_family_items=100,dev_probe_success=0,dev_gold_or_answers_read=False)
print('DEPLOYMENT_FROZEN',{f:deployment[f]['q'] for f in FAMILIES},flush=True)
probe_scores['dev']=probe_split('dev');writejl(P/'records/probe_dev.jsonl',probe_scores['dev'])
word_scores['dev']=score_word(IDS['dev'],deployment['WordD']);writejl(P/'records/word_dev_scores.jsonl',word_scores['dev'])
dev=[];grids=[]
for i,p,w in zip(IDS['dev'],probe_scores['dev'],word_scores['dev']):
 scores={f:p[f] for f in NEW[:2]};scores['WordD']=w['WordD'];routes={};overhead={};measured={};selector={}
 for f in NEW:
  a=time.perf_counter_ns();selected=route(scores[f],deployment[f]);b=time.perf_counter_ns();routes[f]='R' if selected else 'T'
  selector[f]=(b-a)/1e6 if f!='WordD' else w['selector_ms']
  measured[f]=p['probe_core_ms']+p[f+'_score_ms']+selector[f] if f!='WordD' else w['feature_head_ms']+selector[f]
  overhead[f]=measured[f] if deployment[f]['mode']=='selective' else 0.
 dev.append({'id':i,'scores':scores,'route':routes,'required_overhead_ms':overhead,'measured_selective_overhead_ms':measured,'selector_ms':selector,'probe_ids_sha256':p['probe_ids_sha256']})
 grids.append({'id':i,'routes':{f:[int(scores[f]<=threshold_value(t)) for t in thresholds[f]] for f in NEW}})
writejl(P/'records/dev_scored_routes.jsonl',dev);writejl(P/'records/dev_grid_routes.jsonl',grids)
assert len(probes)==attempts==4208
freeze('PROBES_COMPLETE.json',[P/f'records/probe_{s}.jsonl' for s in IDS]+[P/'records/probe_records.jsonl',P/'records/probe_attempts.jsonl'],attempts=attempts,success=len(probes),extra_forward=0)
freeze('DEV_ROUTES_FREEZE.json',[P/'records/dev_scored_routes.jsonl',P/'records/dev_grid_routes.jsonl',P/'records/word_dev_scores.jsonl',P/'DEPLOYMENT_FREEZE.json',P/'PROBES_COMPLETE.json'],N=742,new_families=3,dev_gold_or_answers_read=False)
save(P/'CONTROLS_COMPLETE.json',{'utc':utc(),'heads':1,'fit_attempts':1,'probes':4208,'prefill_attempts':4208,'new_calibration':60,'reused_calibration':40,'dev_routes':2226,'helper_forward':0,'answer_generation':0,'new_protocol_requests':0})
print('CONTROLS_COMPLETE',flush=True)
