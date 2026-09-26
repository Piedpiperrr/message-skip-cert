"""E8 task 2: (a) bit-for-bit reproduction of saved OBQA fit rows for the target pair,
(b) bit-for-bit reproduction of saved large-pair MMLU-Pro fit rows with the unchanged large
configuration, (c) 16-row MMLU-Pro smoke for the target pair. No gold is read anywhere."""
from common_e8 import *
import traceback,collections
N=16
V=P/'validation'/os.environ.get('E8_JOBTAG','local')
def slot_out(name):return V/f'{name}.json'

def obqa_queries():
    return {r['id']:{k:r[k] for k in ['id','question_stem','choice_labels','choice_text']}
            for r in rows(BND/'inputs/obqa_train_queries.jsonl')}

AKEYS=['raw_answer','generated_token_ids','receiver_input_tokens','helper_input_tokens','helper_generated_token_ids','helper_message']
PKEYS=['ProbeMax','p_labels','argmax_probe_label','probe_ids','input_tokens','last_valid_position','probe_ids_sha256','rendered_sha256']

def _norm_action(rec):
    """Saved action record -> the model-output fields, wherever the stage stored them.
    Gold-bearing fields (e.g. gold_answer, scoring) are never read."""
    src=rec.get('output',rec)
    out={k:src[k] for k in AKEYS if k in src}
    for k in AKEYS:
        if k not in out and k in rec:out[k]=rec[k]
    return out

def _norm_probe(rec):return {k:rec[k] for k in PKEYS if k in rec}

def saved_medium_obqa():
    acts=collections.defaultdict(dict);probes={}
    for r in rows(MEDIUM/'actions/obqa_fit.jsonl'):acts[r['id']][r['action']]=_norm_action(r)
    for r in rows(MEDIUM/'probes/obqa_fit.jsonl'):probes[r['id']]=_norm_probe(r)
    return acts,probes,[str(MEDIUM/'actions/obqa_fit.jsonl'),str(MEDIUM/'probes/obqa_fit.jsonl')]

def saved_small_obqa():
    code={'receiver_only':'R','text':'T','c2c':'C'}
    acts=collections.defaultdict(dict);probes={}
    f=ROOT/'P2_10_20260911T122423Z/results/small/obqa/train_cases.jsonl'
    for r in rows(f):
        if r['action'] in code:acts[r['id']][code[r['action']]]=_norm_action(r)
    g=BND/'records/small_obqa_fit_probes.jsonl'
    for r in rows(g):probes[r['id']]=_norm_probe(r)
    return acts,probes,[str(f),str(g)]

def saved_large_mmlu():
    acts=collections.defaultdict(dict);probes={}
    src=[]
    for sh in ['1','2']:
        fa=MMLU/f'shards/{sh}/actions/fit.jsonl';fp=MMLU/f'shards/{sh}/probes/fit.jsonl'
        if fa.exists():
            src.append(str(fa))
            for r in rows(fa):acts[r['id']][r['action']]=_norm_action(r)
        if fp.exists():
            src.append(str(fp))
            for r in rows(fp):probes[r['id']]=_norm_probe(r)
    return acts,probes,src

def cmp_action(new,old):
    """Bit-for-bit on the model output; latency and bookkeeping are excluded by construction."""
    o=new['output'];d={}
    d['raw_answer']=(o['raw_answer']==old['raw_answer'])
    d['generated_token_ids']=(list(o['generated_token_ids'])==list(old['generated_token_ids']))
    d['receiver_input_tokens']=(o['receiver_input_tokens']==old['receiver_input_tokens'])
    for k in ['helper_input_tokens','helper_generated_token_ids','helper_message']:
        if k in o and k in old:d[k]=(o[k]==old[k])
    return d,all(d.values())

def cmp_probe(new,old):
    d={'ProbeMax_exact':new['ProbeMax']==old['ProbeMax'],
       'p_labels_exact':new['p_labels']==old['p_labels'],
       'argmax_probe_label':new['argmax_probe_label']==old['argmax_probe_label'],
       'input_tokens':new['input_tokens']==old['input_tokens']}
    if 'probe_ids' in old:d['probe_ids']=(list(new['probe_ids'])==list(old['probe_ids']))
    if 'last_valid_position' in old:d['last_valid_position']=(new['last_valid_position']==old['last_valid_position'])
    for k in ['probe_ids_sha256','rendered_sha256']:
        if k in old:d[k]=(new[k]==old[k])
    return d,all(d.values())

def reproduce(rt,tag,queries,acts,probes,order,sources):
    picked=[i for i in order if i in acts and i in probes and set(acts[i])>={'R','T','C'}][:N]
    assert len(picked)==N,(tag,'insufficient saved rows',len(picked))
    per=[];ok=True
    for i in picked:
        q=queries[i];row={'id':i,'actions':{},'probe':None}
        for a in ['R','T','C']:
            res=rt.action(q,a);d,good=cmp_action(res,acts[i][a])
            row['actions'][a]={'match':good,'fields':d,'new_answer_label':res['answer'],
                'saved_raw_len':len(acts[i][a].get('raw_answer',''))}
            ok&=good
        pr=rt.probe(q);d,good=cmp_probe(pr,probes[i])
        row['probe']={'match':good,'fields':d,'new_ProbeMax':pr['ProbeMax'],'saved_ProbeMax':probes[i]['ProbeMax']}
        ok&=good;per.append(row)
    return dict(check=tag,utc=utc(),pair=rt.pair,n_rows=N,ids=picked,sources=sources,
        all_bit_for_bit=bool(ok),
        action_mismatches=[(r['id'],a) for r in per for a,v in r['actions'].items() if not v['match']],
        probe_mismatches=[r['id'] for r in per if not r['probe']['match']],
        per_row=per,gold_read=False)

def smoke(rt,queries,order):
    picked=order[:N];per=[];inv=collections.Counter();lat=collections.defaultdict(list)
    for i in picked:
        q=queries[i];row={'id':i,'K':len(q['choice_labels']),'answers':{},'invalid':{}}
        for a in ['R','T','C']:
            res=rt.action(q,a);row['answers'][a]=res['answer'];row['invalid'][a]=bool(res['invalid'])
            inv[a]+=int(res['invalid']);lat[a].append(res['latency_ms'])
        pr=rt.probe(q);row['ProbeMax']=pr['ProbeMax'];lat['P'].append(pr['latency_ms'])
        assert abs(sum(pr['p_labels'].values())-1)<2e-6 and set(pr['p_labels'])==set(q['choice_labels'])
        per.append(row)
    mean=lambda v:sum(v)/len(v)
    return dict(check='smoke_mmlu_pro',utc=utc(),pair=rt.pair,n_rows=N,ids=picked,
        invalid_counts={a:int(inv[a]) for a in ['R','T','C']},invalid_threshold_per_action=4,
        exceeded=[a for a in ['R','T','C'] if inv[a]>4],
        mean_latency_ms={a:round(mean(lat[a]),1) for a in ['R','T','C','P']},
        measured_seconds_per_row=round(sum(mean(lat[a]) for a in ['R','T','C','P'])/1000,4),
        per_row=per,gold_read=False)

def main():
    V.mkdir(parents=True,exist_ok=True)
    pair=PAIR;assert pair in ('small','medium'),pair
    t0=time.perf_counter()
    from native_runtime_e8 import Runtime
    import_seconds=time.perf_counter()-t0
    res={'slot':SLOT,'pair':pair,'utc_start':utc(),'import_seconds':round(import_seconds,1),
         'host':os.uname().nodename,'CUDA_VISIBLE_DEVICES':os.environ.get('CUDA_VISIBLE_DEVICES')}
    t=time.perf_counter();rt=Runtime(pair);res['load_seconds']=round(time.perf_counter()-t,1)
    res['load_breakdown']=rt.load_times
    res['mechanical_smoke']=rt.mechanical_smoke()['status']
    oq=obqa_queries()
    acts,probes,src=(saved_medium_obqa() if pair=='medium' else saved_small_obqa())
    order=read(BND/'splits/obqa_fit_ids.json')
    res['a_obqa_bit_for_bit']=reproduce(rt,f'{pair}_obqa_fit_bit_for_bit',oq,acts,probes,order,src)
    mq=project_queries()
    res['c_smoke']=smoke(rt,mq,ids('fit'))
    save(slot_out(f'VALIDATION_{pair}'),res)
    print('SLOT_DONE',pair,'a_match=',res['a_obqa_bit_for_bit']['all_bit_for_bit'],
          'invalid=',res['c_smoke']['invalid_counts'],'s/row=',res['c_smoke']['measured_seconds_per_row'],flush=True)
    if os.environ.get('E8_RUN_LARGE')=='1':
        import torch,gc
        del rt;gc.collect();torch.cuda.empty_cache()
        big={'slot':SLOT,'pair':'large','utc_start':utc()}
        t=time.perf_counter();rtl=Runtime('large');big['load_seconds']=round(time.perf_counter()-t,1)
        big['mechanical_smoke']=rtl.mechanical_smoke()['status']
        la,lp,lsrc=saved_large_mmlu()
        big['b_large_mmlu_bit_for_bit']=reproduce(rtl,'large_mmlu_pro_fit_bit_for_bit',mq,la,lp,ids('fit'),lsrc)
        big['utc_end']=utc()
        save(slot_out('VALIDATION_large_control'),big)
        print('SLOT_DONE large b_match=',big['b_large_mmlu_bit_for_bit']['all_bit_for_bit'],flush=True)

if __name__=='__main__':
    try:
        main()
    except BaseException as exc:
        V.mkdir(parents=True,exist_ok=True)
        save(V/f'VALIDATION_FAILURE_{PAIR or "unknown"}_{SLOT}.json',
             dict(utc=utc(),pair=PAIR,slot=SLOT,error=repr(exc),traceback=traceback.format_exc()))
        raise
