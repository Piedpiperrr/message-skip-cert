"""E7 step 2: is the native R prompt an exact token prefix of the ProbeMax probe input?
Tokenises exactly as the frozen code does (receiver_prompt -> chat template -> tok(rendered); probe = same + prefix_ids)."""
import json,sys,statistics
from pathlib import Path
from transformers import AutoTokenizer
ROOT=Path('$DATA_DIR')
E3=ROOT/'P2_R1_E3POL_REPEAT1_20260919T075315Z'
sys.path.insert(0,str(E3/'large/src'))
from receiver_prompt import receiver_prompt,display_labels   # frozen extraction, identical to arc_protocol.receiver_prompt
def jl(p):return [json.loads(s) for s in Path(p).open() if s.strip()]
REC={'Qwen3-8B':'$DATA_DIR/hf_cache/hub/models--Qwen--Qwen3-8B/snapshots/b968826d9c46dd6066d109eabc6255188de91218',
     'Qwen3-1.7B':str(E3/'medium/assets/receiver')}
PANELS=[('large_obqa','Qwen3-8B',E3/'large/inputs/obqa_queries.jsonl'),
        ('large_arc','Qwen3-8B',E3/'large/inputs/arc_queries.jsonl'),
        ('large_mmlu_pro','Qwen3-8B',E3/'mmlu/inputs/panel_queries.jsonl'),
        ('medium_obqa','Qwen3-1.7B',E3/'medium/inputs/obqa_queries.jsonl'),
        ('medium_arc','Qwen3-1.7B',E3/'medium/inputs/arc_queries.jsonl')]
out={};toks={}
for name,rec,path in PANELS:
    if rec not in toks:
        toks[rec]=AutoTokenizer.from_pretrained(REC[rec],local_files_only=True)
    tok=toks[rec]
    prefix_ids=tok.encode('The correct answer is',add_special_tokens=False)
    rows=jl(path);res=[];lcp=[]
    for r in rows:
        q={'question_stem':r['question_stem'],'choice_labels':list(r['choice_labels']),'choice_text':list(r['choice_text'])}
        body=receiver_prompt(q)
        rendered=tok.apply_chat_template([{'role':'user','content':body}],tokenize=False,add_generation_prompt=True,enable_thinking=False)
        R=tok(rendered)['input_ids']                    # native receiver-only prompt (protocol_min.receiver_prompt_tensors)
        PR=R+prefix_ids                                 # ProbeMax probe input
        n=0
        while n<len(R) and n<len(PR) and R[n]==PR[n]: n+=1
        res.append(n==len(R));lcp.append(n)
        assert display_labels(len(q['choice_text']))==q['choice_labels']
    out[name]={'receiver':rec,'n_questions':len(rows),'exact_prefix_all':all(res),
               'n_exact_prefix':sum(res),'prefix_ids':prefix_ids,'extra_tokens_in_probe':len(prefix_ids),
               'R_tokens_mean':round(statistics.mean([len(tok(tok.apply_chat_template([{'role':'user','content':receiver_prompt({'question_stem':r['question_stem'],'choice_labels':list(r['choice_labels']),'choice_text':list(r['choice_text'])})}],tokenize=False,add_generation_prompt=True,enable_thinking=False))['input_ids']) for r in rows[:16]]),1),
               'lcp_min':min(lcp),'lcp_max':max(lcp)}
    print(name,out[name]['receiver'],'exact_prefix %d/%d'%(out[name]['n_exact_prefix'],len(rows)),'probe adds',len(prefix_ids),'tokens',flush=True)
Path(sys.argv[1]).write_text(json.dumps(out,indent=2)+'\n')
