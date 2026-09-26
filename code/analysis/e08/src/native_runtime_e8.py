"""E8 MMLU-Pro runtime. Verbatim from the frozen large-pair MMLU-Pro
P2_MMLU_PRO_BREADTH_STAGE1_20260916T002337Z/src/native_runtime.py, with exactly three
pair-dependent substitutions: (i) model/fuser source index, (ii) expected generation
configs, (iii) projector count and projector_config mapping. Prompts, generation limits,
decoding, dtype/attention, parser, ProbeMax and all assertions are unchanged."""
from common_e8 import *
import torch
from transformers import AutoModelForCausalLM,AutoTokenizer
sys.path.insert(0,str(NATIVE))
import runtime as native
import protocol_min

def format_mmlu(example,use_template=True):
    if use_template:return prompt.receiver_prompt(example)
    return prompt.build_prompt(dataset="mmlu-redux",locale="",question=example["question_stem"],choices=prompt.choices_block(example["choice_text"]),use_cot=False,use_template=False)
protocol_min.format_openbook=format_mmlu
native.lm.format_openbook=format_mmlu
from protocol_min import apply_generation_config,receiver_prompt_tensors
sys.path.remove(str(NATIVE))
prompt=load_module(P/'protocol/receiver_prompt.py','mmlu_receiver_prompt')
parser=load_module(P/'protocol/scoring_v2.py','mmlu_parser')

def sync():
    for i in [0,1]:torch.cuda.synchronize(i)

class Runtime:
    def __init__(self,pair=None):
        assert torch.cuda.device_count()==2
        torch.set_num_threads(1);torch.set_num_interop_threads(1)
        torch.manual_seed(0);torch.cuda.manual_seed_all(0)
        torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False
        self.cfg=pair_config(pair or PAIR);self.pair=self.cfg['pair']
        index=self.cfg['index'];expected=self.cfg['expected']
        self.runner=native.Runner.__new__(native.Runner);self.load_times={};self.load_info={}
        for role,device in [('helper','cuda:0'),('receiver','cuda:1')]:
            stop_check();t=time.perf_counter();loc=Path(index['models'][role]['path'])
            tok=AutoTokenizer.from_pretrained(loc,local_files_only=True)
            assert hashlib.sha256(tok.chat_template.encode()).hexdigest()==index['models'][role]['chat_template_sha256']
            if tok.pad_token is None:tok.pad_token=tok.eos_token
            model,info=AutoModelForCausalLM.from_pretrained(loc,local_files_only=True,torch_dtype=torch.bfloat16,
                attn_implementation='sdpa',output_loading_info=True)
            assert all(not info.get(k) for k in ['missing_keys','unexpected_keys','mismatched_keys','error_msgs']),info
            model=model.to(device).eval().requires_grad_(False)
            apply_generation_config(model,{'do_sample':False,'max_new_tokens':64})
            assert model.generation_config.to_dict()==expected[role]
            setattr(self.runner,role,model);setattr(self.runner,role+'_tok',tok)
            assert all(str(p.device)==device for p in model.parameters())
            sync();self.load_times[role]=time.perf_counter()-t;self.load_info[role]=info
        lm=native.lm
        lm.C2C_FUSERS=self.cfg['fuser_path']
        lm.HELPER_CONFIG=self.runner.helper.config;lm.RECEIVER_CONFIG=self.runner.receiver.config
        self.runner.th=lm.T2THelperBundle(self.runner.helper,self.runner.helper_tok)
        self.runner.tr=lm.T2TReceiverBundle(self.runner.receiver,self.runner.receiver_tok)
        self.runner.ch=lm.C2CSharerHelperBundle(self.runner.helper,self.runner.receiver_tok)
        t=time.perf_counter()
        self.runner.cr=lm.C2CReceiverSideFuserBundle(self.runner.receiver,self.runner.receiver_tok)
        for f in self.runner.cr.projectors:f.eval().requires_grad_(False)
        assert len(self.runner.cr.projectors)==self.cfg['projector_count']
        assert self.runner.cr.mapping==self.cfg['mapping']
        assert all(str(p.device)=='cuda:1' for f in self.runner.cr.projectors for p in f.parameters())
        sync();self.load_times['fuser']=time.perf_counter()-t
        self.hooks=self.hook_signature()
        self.prefix_ids=read(P/'protocol/prefix_ids.json')['ids']
        self.sets=read(P/'protocol/label_token_sets.json')
        self.ix={k:torch.tensor(v,device='cuda:1') for k,v in self.sets.items()}
        tok=self.runner.receiver_tok
        assert tok.encode('The correct answer is',add_special_tokens=False)==self.prefix_ids
        for label,values in self.sets.items():
            assert all(v not in tok.all_special_ids and tok.decode([v],skip_special_tokens=False,clean_up_tokenization_spaces=False).strip()==label for v in values)
        self.first_probe=True

    def hook_signature(self):
        return {r:[(len(m._forward_hooks),len(m._forward_pre_hooks)) for m in getattr(self.runner,r).model.layers] for r in ['helper','receiver']}

    def check_hooks(self):assert self.hook_signature()==self.hooks

    @torch.inference_mode()
    def mechanical_smoke(self):
        # Artificial placeholder text only; no benchmark/gold/risk/accuracy.
        q={'id':'SYNTHETIC_MECHANICAL_ONLY','question_stem':'Synthetic mechanical check: select a placeholder.',
           'choice_labels':list('ABCDEFGHIJ'),'choice_text':['placeholder '+str(i) for i in range(10)]}
        checks=[]
        for action in ['R','T','C']:
            self.check_hooks()
            out=self.runner.request(q,{'R':'receiver_only','T':'text','C':'c2c'}[action])
            projected=out.pop('_projected',None)
            check={'action':action,'runtime_entered':True,'receiver_input_tokens':out['receiver_input_tokens'],
                   'generation_tensor_nonempty':bool(out['generated_token_ids'])}
            assert check['generation_tensor_nonempty']
            if projected is not None:
                assert projected.dtype==torch.float32 and torch.isfinite(projected).all().item()
                check.update(projected_shape=list(projected.shape),projected_dtype=str(projected.dtype))
            self.check_hooks();checks.append(check);del out,projected
        parser_checks=0
        for K in range(3,11):
            labels=list('ABCDEFGHIJ')[:K]
            for label in labels:
                out=parser.parse_answer('The correct answer is '+label,labels)
                assert out['valid'] and out['answer']==label
                assert self.runner.receiver_tok.encode(label,add_special_tokens=False)[0] in self.sets[label]
                parser_checks+=1
            assert not parser.parse_answer('The correct answer is '+chr(65+K),labels)['valid']
            assert not parser.parse_answer('The correct answer is A or B',labels)['valid']
        probe_checks=[]
        for K in [3,10]:
            qq={**q,'choice_labels':q['choice_labels'][:K],'choice_text':q['choice_text'][:K]}
            result=self.probe(qq)
            assert set(result['p_labels'])==set(qq['choice_labels'])
            probe_checks.append({'K':K,'probability_sum_valid':abs(sum(result['p_labels'].values())-1)<2e-6,
                'last_valid_position':result['last_valid_position'],'input_tokens':result['input_tokens'],
                'LM_head_input_shapes':result['LM_head_input_shapes'],'cache_reused':result['cache_reused']})
            del result
        self.first_probe=True
        sync()
        return {'status':'PASS','utc':utc(),'pair':self.pair,'synthetic_input':q,'native_action_checks':checks,
            'parser_legal_synthetic_cases':parser_checks,'probe_structural_checks':probe_checks,
            'model_loading_info':self.load_info,'load_seconds':self.load_times,
            'fuser_load_audit':native.lm.FUSER_LOAD_AUDIT,'helper_device':str(self.runner.helper.device),
            'receiver_device':str(self.runner.receiver.device),'projectors_device':'cuda:1',
            'projector_count':self.cfg['projector_count'],
            'project_question_reads':0,'scientific_metrics_computed':False,'synthetic_generated_text_retained':False,
            'MMLU_PRO_OUTCOMES_OBSERVED':False}

    @torch.inference_mode()
    def action(self,q,a):
        self.check_hooks()
        # Capture actual native model input IDs from the first invocation of
        # each model. No extra forward or component timing is introduced.
        captured={};handles=[]
        for role in ['helper','receiver']:
            def capture(mod,args,kwargs,role=role):
                if role in captured:return
                x=kwargs.get('input_ids',args[0] if args else None)
                if x is not None:captured[role]=x.detach().cpu().tolist()
            handles.append(getattr(self.runner,role).register_forward_pre_hook(capture,with_kwargs=True))
        sync();t=time.perf_counter()
        try:out=self.runner.request(q,{'R':'receiver_only','T':'text','C':'c2c'}[a])
        finally:
            for h in handles:h.remove()
        sync();elapsed=(time.perf_counter()-t)*1000
        parsed=parser.parse_answer(out['raw_answer'],q['choice_labels'])
        projected=out.pop('_projected',None);diag={}
        if projected is not None:
            assert projected.dtype==torch.float32 and torch.isfinite(projected).all().item()
            diag={'projected_shape':list(projected.shape),'projected_dtype':str(projected.dtype),'projected_finite':True}
        self.check_hooks()
        return {'output':out,'parsed':parsed,'answer':parsed['answer'] if parsed['valid'] else 'INVALID',
            'invalid':not parsed['valid'],'latency_ms':elapsed,'native_first_input_ids':captured,
            'runtime_diagnostics':diag,'runtime_failure':False,'cross_request_KV_reuse':False}

    @torch.inference_mode()
    def probe(self,q):
        self.check_hooks();tok=self.runner.receiver_tok;model=self.runner.receiver
        sync();t=time.perf_counter()
        body=prompt.receiver_prompt(q)
        rendered=tok.apply_chat_template([{'role':'user','content':body}],tokenize=False,add_generation_prompt=True,enable_thinking=False)
        base=tok(rendered,return_tensors='pt')
        suffix=tok.encode('The correct answer is',add_special_tokens=False);assert suffix==self.prefix_ids
        probe_ids=torch.cat([base['input_ids'],torch.tensor([suffix],dtype=base['input_ids'].dtype)],dim=1)
        mask=torch.cat([base['attention_mask'],torch.ones((1,len(suffix)),dtype=base['attention_mask'].dtype)],dim=1)
        inp={'input_ids':probe_ids.to(model.device),'attention_mask':mask.to(model.device)}
        pos=int(torch.nonzero(mask[0],as_tuple=False)[-1,0]);n=probe_ids.shape[1]
        calls=[];hook=model.lm_head.register_forward_pre_hook(lambda m,a:calls.append(list(a[0].shape))) if self.first_probe else None
        out=model.model(**inp,use_cache=False,return_dict=True,output_hidden_states=False,output_attentions=False)
        assert out.past_key_values is None and pos==n-1 and int(mask.sum())==n
        last=out.last_hidden_state[:,pos:pos+1,:];logits=model.lm_head(last)[0,0,:].float()
        labels=prompt.display_labels(len(q['choice_text']));assert labels==q['choice_labels']
        label_logits=torch.stack([torch.logsumexp(logits[self.ix[l]],dim=0) for l in labels])
        logp=torch.log_softmax(label_logits,dim=0);p=logp.exp();ps=p.cpu().tolist()
        u=float((1-p.max()).item())
        union=torch.cat([self.ix[l] for l in labels]);mass=float(torch.exp(torch.logsumexp(logits[union],0)-torch.logsumexp(logits,0)).item())
        sync();elapsed=(time.perf_counter()-t)*1000
        if hook:
            hook.remove();assert calls==[[1,1,model.config.hidden_size]]
            assert base['input_ids'][0].tolist()==tok.apply_chat_template([{'role':'user','content':body}],tokenize=True,add_generation_prompt=True,enable_thinking=False)
        import math
        assert all(math.isfinite(x) for x in ps) and abs(sum(ps)-1)<2e-6 and 0<=mass<=1.00001 and 0<=u<=1
        result={'ProbeMax':u,'p_labels':dict(zip(labels,ps)),'label_union_mass':mass,
            'argmax_probe_label':labels[max(range(len(ps)),key=ps.__getitem__)],
            'probe_ids':probe_ids[0].tolist(),'probe_ids_sha256':hashlib.sha256(probe_ids.numpy().tobytes()).hexdigest(),
            'rendered_sha256':hashlib.sha256(rendered.encode()).hexdigest(),'last_valid_position':pos,'input_tokens':n,
            'latency_ms':elapsed,'invalid_probe':False,'runtime_failure':False,'cache_reused':False,
            'first_formal_projection_check':self.first_probe,'LM_head_input_shapes':calls if hook else None}
        self.first_probe=False;self.check_hooks();return result
