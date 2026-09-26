"""E8 login-node CPU feasibility: resolve both pairs, verify tokenizers/label sets,
derive expected generation configs, strict-load both fusers. No GPU, no project queries, no gold."""
import os,sys,json,time,hashlib,datetime,re
from pathlib import Path
sys.dont_write_bytecode=True
os.environ.setdefault('OPENBLAS_NUM_THREADS','1')
E8=Path(__file__).resolve().parents[1]
ROOT=E8.parent
NATIVE=ROOT/'P2_10_20260911T122423Z'
MEDA=ROOT/'P2_MEDIUM_PAIR_BOUNDARY_EXTENSION_STAGE1_20260915T144407Z/execution_20260915T152640Z/assets'
SMALLA=Path('$DATA_DIR/c2c_reproduction_assets')

def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
    return h.hexdigest()
def save(p,v):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(v,ensure_ascii=False,indent=2,allow_nan=False)+'\n')

PAIRS={
 'small':dict(
   helper=dict(repo_id='Qwen/Qwen2.5-0.5B-Instruct',revision='7ae557604adf67be50417f59c2c2f167def9a775',
               path=str(SMALLA/'models/Qwen--Qwen2.5-0.5B-Instruct')),
   receiver=dict(repo_id='Qwen/Qwen3-0.6B',revision='c1899de289a04d12100db370d81485cdf75e47ca',
               path=str(SMALLA/'models/Qwen--Qwen3-0.6B')),
   fuser=dict(repo_id='nics-efc/C2C_Fuser',revision='8704f555c6b4a60b764de7d755e6f1daf21a57ef',
               subfolder='qwen3_0.6b+qwen2.5_0.5b_Fuser/final',
               path=str(SMALLA/'fusers/nics-efc--C2C_Fuser/qwen3_0.6b+qwen2.5_0.5b_Fuser/final'))),
 'medium':dict(
   helper=dict(repo_id='Qwen/Qwen2.5-1.5B-Instruct',revision='989aa7980e4cf806f80c7fef2b1adb7bc71aa306',
               path=str(MEDA/'helper')),
   receiver=dict(repo_id='Qwen/Qwen3-1.7B',revision='70d244cc86ccca08cf5af4e1e306ecf908b1ad5e',
               path=str(MEDA/'receiver')),
   fuser=dict(repo_id='nics-efc/C2C_Fuser',revision='f01fc3258b305e280e04c7238f4f2cf31b7dc70d',
               subfolder='qwen3_1.7b+qwen2.5_1.5b_Fuser/final',
               path=str(MEDA/'fuser/qwen3_1.7b+qwen2.5_1.5b_Fuser/final'))),
}

import torch
from transformers import AutoModelForCausalLM,AutoTokenizer
sys.path.insert(0,str(NATIVE))
import legacy_methods as lm
sys.path.remove(str(NATIVE))

prefix_ids=json.loads((E8/'protocol/prefix_ids.json').read_text())['ids']
label_sets=json.loads((E8/'protocol/label_token_sets.json').read_text())
report={'utc_start':utc(),'pairs':{},'shared_protocol':{
    'prefix_ids':prefix_ids,'labels':sorted(label_sets),
    'receiver_prompt_sha256':sha(E8/'protocol/receiver_prompt.py'),
    'scoring_v2_sha256':sha(E8/'protocol/scoring_v2.py'),
    'label_token_sets_sha256':sha(E8/'protocol/label_token_sets.json'),
    'prefix_ids_sha256':sha(E8/'protocol/prefix_ids.json')}}

for pair,spec in PAIRS.items():
    out={'pair':pair,'models':{},'checks':{}}
    index={'utc':utc(),'pair':pair,'models':{}}
    gen={}
    for role in ['helper','receiver']:
        loc=Path(spec[role]['path']);assert loc.is_dir(),loc
        files=sorted(p for p in loc.iterdir() if p.is_file() and p.suffix in
                     {'.json','.txt','.safetensors','.model'} or p.name=='tokenizer.json')
        fh=[dict(path=str(p),size=p.stat().st_size,sha256=sha(p)) for p in files]
        tok=AutoTokenizer.from_pretrained(loc,local_files_only=True)
        ct=hashlib.sha256(tok.chat_template.encode()).hexdigest()
        if tok.pad_token is None:tok.pad_token=tok.eos_token
        t=time.perf_counter()
        model,info=AutoModelForCausalLM.from_pretrained(loc,local_files_only=True,torch_dtype=torch.bfloat16,
            attn_implementation='sdpa',output_loading_info=True)
        assert all(not info.get(k) for k in ['missing_keys','unexpected_keys','mismatched_keys','error_msgs']),(pair,role,info)
        lm_mod=sys.modules['legacy_methods']
        sys.path.insert(0,str(NATIVE));from protocol_min import apply_generation_config;sys.path.remove(str(NATIVE))
        apply_generation_config(model,{'do_sample':False,'max_new_tokens':64})
        gen[role]=model.generation_config.to_dict()
        cfg=model.config
        out['models'][role]=dict(repo_id=spec[role]['repo_id'],revision=spec[role]['revision'],path=str(loc),
            num_hidden_layers=cfg.num_hidden_layers,num_key_value_heads=cfg.num_key_value_heads,
            hidden_size=cfg.hidden_size,head_dim=lm.head_dim(cfg),model_type=cfg.model_type,
            chat_template_sha256=ct,strict_cpu_load_seconds=round(time.perf_counter()-t,2),
            loading_info_clean=True,n_files_hashed=len(fh))
        index['models'][role]=dict(repo_id=spec[role]['repo_id'],revision=spec[role]['revision'],path=str(loc),
            files=fh,chat_template_sha256=ct,
            aggregate_sha256=hashlib.sha256(''.join(x['sha256'] for x in fh).encode()).hexdigest())
        if role=='receiver':
            enc=tok.encode('The correct answer is',add_special_tokens=False)
            ok_labels=all(all(v not in tok.all_special_ids and
                tok.decode([v],skip_special_tokens=False,clean_up_tokenization_spaces=False).strip()==label
                for v in values) for label,values in label_sets.items())
            out['checks']['prefix_ids_match']=(enc==prefix_ids)
            out['checks']['prefix_ids_actual']=enc
            out['checks']['label_token_sets_valid_A_to_J']=bool(ok_labels)
            rcfg=cfg
        else:
            hcfg=cfg
        del model
    # fuser strict load on CPU, exactly as legacy_methods.load_c2c_fusers
    lm.C2C_FUSERS=Path(spec['fuser']['path']);lm.HELPER_CONFIG=hcfg;lm.RECEIVER_CONFIG=rcfg
    lm.FUSER_LOAD_AUDIT.clear()
    t=time.perf_counter();projectors,mapping=lm.load_c2c_fusers('cpu')
    secs=time.perf_counter()-t
    pfiles=sorted(p for p in Path(spec['fuser']['path']).iterdir() if p.is_file())
    index['models']['fuser']=dict(repo_id=spec['fuser']['repo_id'],revision=spec['fuser']['revision'],
        subfolder=spec['fuser']['subfolder'],path=spec['fuser']['path'],
        files=[dict(path=str(p),size=p.stat().st_size,sha256=sha(p)) for p in pfiles],
        projector_config_sha256=sha(Path(spec['fuser']['path'])/'projector_config.json'))
    out['models']['fuser']=dict(repo_id=spec['fuser']['repo_id'],revision=spec['fuser']['revision'],
        subfolder=spec['fuser']['subfolder'],path=spec['fuser']['path'],
        projector_count=len(projectors),strict_cpu_load_seconds=round(secs,2),
        parameters_total=sum(a['parameters'] for a in lm.FUSER_LOAD_AUDIT),
        all_strict=all(a['strict'] and not a['missing_keys'] and not a['unexpected_keys'] for a in lm.FUSER_LOAD_AUDIT))
    out['checks']['fuser_loads_for_pair']=True
    out['checks']['projector_count_equals_receiver_layers']=(len(projectors)==rcfg.num_hidden_layers)
    out['checks']['mapping']= {str(k):list(v) for k,v in sorted(mapping.items())}
    out['checks']['mapping_is_identity']=all(v==(k,k) for k,v in mapping.items())
    index['models']['fuser']['projector_count']=len(projectors)
    index['models']['fuser']['mapping']={str(k):list(v) for k,v in sorted(mapping.items())}
    del projectors
    save(E8/f'protocol/generation_configs_{pair}.json',dict(
        model_generation_config_after_native_cleanup=gen,
        native_receiver_max_new_tokens=64,native_text_helper_max_new_tokens=256,
        do_sample=False,thinking='disabled (enable_thinking=False)',seed=0,
        helper_objective='one background sentence, do NOT solve',
        C2C='official C2CSharerHelperBundle + C2CReceiverSideFuserBundle; BF16 weights, FP32 projection'))
    save(E8/f'MODEL_SOURCE_INDEX_{pair}.json',index)
    report['pairs'][pair]=out
    print(pair,'OK projectors=',len(projectors) if False else out['models']['fuser']['projector_count'],
          'layers=',rcfg.num_hidden_layers,'prefix_ok=',out['checks']['prefix_ids_match'],
          'labels_ok=',out['checks']['label_token_sets_valid_A_to_J'],flush=True)

report['utc_end']=utc()
report['generation_configs']={p:sha(E8/f'protocol/generation_configs_{p}.json') for p in PAIRS}
report['model_source_index']={p:sha(E8/f'MODEL_SOURCE_INDEX_{p}.json') for p in PAIRS}
report['GPU_used']=False;report['project_queries_read']=0;report['gold_read']=False
save(E8/'feasibility/CPU_FEASIBILITY.json',report)
print('FEASIBILITY_WRITTEN',E8/'feasibility/CPU_FEASIBILITY.json',flush=True)
