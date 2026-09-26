"""正式执行完成后核验所有已记录的实际模型输入；只做CPU tokenization，无forward。"""
from common import *
assert (P/'INFERENCE_COMPLETE.json').exists()
from transformers import AutoTokenizer
import native_runtime as rt
tok={role:AutoTokenizer.from_pretrained(P/'assets'/role,local_files_only=True) for role in ['helper','receiver']}
plans={(r['task'],r['id']):r for r in rows(P/'protocol/formal_input_identities.jsonl')}
prefix=read(PARENT/'protocol/prefix_ids.json')['ids']
actions=probes=0
for ds in ['obqa','arc']:
    for split in ['fit','cal','dev']:
        for r in rows(P/f'actions/{ds}_{split}.jsonl'):
            plan=plans[ds,r['id']];expected=plan['native_receiver_input_ids'];q=r['query'];a=r['action'];cap=r['native_first_input_ids']
            assert r['query_sha256']==plan['query_sha256']
            if a=='R':assert set(cap)=={'receiver'} and cap['receiver']==[expected]
            elif a=='C':
                assert set(cap)=={'helper','receiver'} and cap['helper']==cap['receiver']==[expected[:-1]]
                assert r['runtime_diagnostics']['projected_shape']==[28,2,8,len(expected)-1,128]
                assert r['output']['transferred_kv_bytes']==28*2*2*(len(expected)-1)*128*2
            else:
                assert a=='T' and set(cap)=={'helper','receiver'}
                body=rt.arc_runtime_adapter.arc_protocol.helper_body(q)
                msg=[{'role':'user','content':rt.native.lm.BACKGROUND_PROMPT.format(question=body)}]
                hi=tok['helper'].apply_chat_template(msg,tokenize=True,add_generation_prompt=True,enable_thinking=False)
                msg+=[{'role':'assistant','content':r['output']['helper_message']},{'role':'user','content':rt.prompt.receiver_prompt(q)}]
                ri=tok['receiver'].apply_chat_template(msg,tokenize=True,add_generation_prompt=True,enable_thinking=False)
                assert cap['helper']==[hi] and cap['receiver']==[ri]
            actions+=1
        for r in rows(P/f'probes/{ds}_{split}.jsonl'):
            plan=plans[ds,r['id']]
            assert r['query_sha256']==plan['query_sha256'] and r['probe_ids']==plan['native_receiver_input_ids']+prefix
            probes+=1
assert actions==16878 and probes==5626
save(P/'INPUT_IDENTITY_VALIDATION.json',{'status':'PASS','utc':utc(),'actual_action_inputs_checked':actions,
    'actual_probe_inputs_checked':probes,'Text_full_native_message_protocol':True,'C2C_receiver_tokenizer_and_KV_shapes':True,
    'no_KV_reuse_probe_input_identity':True,'new_model_forwards':0,'project_answers_generated':0})
print('INPUT_IDENTITY_VALIDATION_PASS')
