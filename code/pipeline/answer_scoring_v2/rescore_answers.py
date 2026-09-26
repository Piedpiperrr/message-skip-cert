"""Source-keyed V2 rescoring; reuse the completed old/D1 replay evidence."""
import json,csv,hashlib,collections,itertools,datetime
from pathlib import Path
from scoring_v2 import parse_answer, VERSION
O=Path(__file__).resolve().parent
P=Path('<private_path>/project')
S=P/'score_sensitivity_stage'; P10=P/'native_action_panel'
ACTIONS=['receiver_only','text','c2c','acw']; LETTERS=['R','T','C','A']; SCHEMES=['old','D1','V2']
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''):h.update(b)
    return h.hexdigest()
def save(name,x): (O/name).write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def table(name,rows):
    rows=list(rows)
    if not rows:(O/name).write_text('no_records\n');return
    fields=list(dict.fromkeys(k for r in rows for k in r))
    with (O/name).open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
def jl(p):
    with Path(p).open() as f:
        for line,s in enumerate(f,1):
            if s.strip():yield line,json.loads(s)
def truth(s):return s is True or s=='True'
def label(o):return o if o is not None else 'INVALID'
def outtuple(r,v):return r[v+'_o'],r[v+'_valid'],r[v+'_y']
def flip(q,a,v):
    r=q['receiver_only'];s=q[a];f=s[v+'_o']!=r[v+'_o'];g=s[v+'_y'] and not r[v+'_y'];h=r[v+'_y'] and not s[v+'_y']
    inv=not s[v+'_valid'] or not r[v+'_valid']
    return dict(f=int(f),gain=int(g),harm=int(h),zero_gain=int(f and not(g or h)),invalid_pair=int(inv),invalid_flip=int(f and inv))
if __name__=='__main__':
    if (O/'SCORING_COMPLETE.json').exists():raise SystemExit('ALREADY_COMPLETE; reuse stage results')
    freeze=json.loads((O/'RULE_FREEZE_V2.json').read_text())
    assert sha(O/'scoring_v2.py')==freeze['code_sha256'] and sha(O/'SCORING_V2_RULES_ZH.md')==freeze['rules_sha256']
    save('PROGRESS.json',{'status':'SCORING_RUNNING','started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'freeze_sha256':sha(O/'RULE_FREEZE_V2.json')})
    cfg=json.loads((P10/'frozen_config.json').read_text())
    manifest=json.loads((S/'evidence/input_manifest.json').read_text()); sources={r['path']:r for r in manifest}
    save('evidence/input_manifest.json',manifest)
    inherited=['RULE_FREEZE_V1.json','FINAL_RECEIPT.json','ANALYSIS_COMPLETE.json','action_accuracy_sensitivity.csv','population_complementarity.csv','pairwise_answer_agreement.csv','ffr_label_sensitivity.csv','changed_records.csv','record_branch_flags.csv','evidence/input_manifest.json']
    save('evidence/inherited_evidence.json',[{'path':str(S/n),'sha256':sha(S/n),'role':'Reuse completed D1/old scoring verification; no old-parser rerun'} for n in inherited])
    d1changes={(r['source_id'],int(r['source_line'])):r for r in csv.DictReader((S/'changed_records.csv').open())}
    flags={(r['source_id'],int(r['source_line'])):r for r in csv.DictReader((S/'record_branch_flags.csv').open())}
    norm={}
    for ds,sps in cfg['data'].items():
        for sp,spec in sps.items():
            assert sp in ['train','dev','validation']
            norm[ds,sp]={r['id']:(r['choice_labels'],r['gold_answer']) for _,r in jl(spec['path'])}
    records=[];pop={};coverage=[];failures=[];changed=[];reasoncounts=collections.Counter()
    for pair,ds in itertools.product(['large','small'],['obqa','arc']):
        for sp in cfg['data'][ds]:
            paths=[(cfg['history_and_features'][pair+'/'+ds+'/'+sp]['path'],False),(str(P10/'results'/pair/ds/(sp+'_cases.jsonl')),True)]
            for path,new in paths:
                src=sources[path];sid=src['source_id'];count=0
                assert sha(path)==src['sha256']
                for ln,r in jl(path):
                    if r.get('runtime_error') not in [None,'None','']:
                        failures.append(dict(source_id=sid,source_line=ln,pair=pair,dataset=ds,split=sp,id=r.get('id'),action=r.get('action'),runtime_error=str(r['runtime_error']),counted_as_population=False));continue
                    uid=(sid,ln); qid=str(r['id']);a=r['action'];legal,gold=norm[ds,sp][qid]
                    old=r['scoring'];assert isinstance(old,dict)
                    d=d1changes.get(uid);fl=flags[uid]
                    parsed=parse_answer(r.get('raw_answer'),legal)
                    rec=dict(source_id=sid,source_line=ln,source_path=path,pair=pair,dataset=ds,split=sp,id=qid,action=a,
                        job_id=r['job_id'],block_id=r.get('block_id'),in_full=(a=='acw' if new else True),in_panel=bool(new and r['panel']),
                        raw_sha256=hashlib.sha256((r.get('raw_answer') or '').encode()).hexdigest(),legal_labels='|'.join(legal),gold=gold,
                        old_o=label(old['answer'] if old['valid'] else None),old_valid=int(old['valid']),old_y=int(old['correct']),old_reason=old.get('reason') or ('saved_valid' if old['valid'] else 'saved_invalid'),
                        D1_o=label(d['diagnostic_answer'] or None) if d else label(old['answer'] if old['valid'] else None),
                        D1_valid=int(truth(d['diagnostic_valid'])) if d else int(old['valid']),D1_y=int(truth(d['diagnostic_correct'])) if d else int(old['correct']),D1_reason=fl['diagnostic_reason'],
                        V2_o=label(parsed['answer']),V2_valid=int(parsed['valid']),V2_y=int(parsed['valid'] and parsed['answer']==gold),V2_reason=parsed['reason'],
                        runtime_error=False,score_version=VERSION,parser_sha256=freeze['code_sha256'],latency_ms=r.get('latency_ms'))
                    assert bool(rec['in_full'])==truth(fl['in_full']) and bool(rec['in_panel'])==truth(fl['in_panel'])
                    for v in SCHEMES:assert rec[v+'_y']==int(rec[v+'_valid'] and rec[v+'_o']==gold)
                    for population,take in [('full',rec['in_full']),('panel',rec['in_panel'])]:
                        if take:
                            q=pop.setdefault((population,pair,ds,sp),{}).setdefault(qid,{})
                            assert a not in q;q[a]=rec
                    for before in ['old','D1']:
                        if outtuple(rec,before)!=outtuple(rec,'V2'):
                            changed.append({**{k:rec[k] for k in ['source_id','source_line','source_path','pair','dataset','split','id','action','in_full','in_panel','raw_sha256']},
                                'comparison':before+'_to_V2',**{k:rec[k] for v in SCHEMES for k in [v+'_o',v+'_valid',v+'_y',v+'_reason']},
                                'answer_changed':rec[before+'_o']!=rec['V2_o'],'validity_changed':rec[before+'_valid']!=rec['V2_valid'],
                                'correctness_delta':rec['V2_y']-rec[before+'_y'],'old_branch':fl['legacy_branch'],
                                'V2_events':json.dumps(parsed['events'],ensure_ascii=False),'V2_ignored':json.dumps(parsed['ignored'],ensure_ascii=False)})
                    records.append(rec);count+=1
                coverage.append(dict(source_id=sid,path=path,successful_records=count,sha256_match=True))
    assert len(records)==49616
    del flags
    acc=[];comp=[];agreements=[];ffr=[];fchanges=[];popchanges=[];label_manifest=[]
    streams={}
    for population in ['full','panel']:
        for splitrole in ['train','development']:
            name=f'labels/{population}_{splitrole}_SCORING_V2.jsonl';streams[population,splitrole]=(name,(O/name).open('w'))
    for (population,pair,ds,sp),qs in pop.items():
        n=len(qs);base=dict(population=population,pair=pair,dataset=ds,split=sp,n=n)
        expected=len(norm[ds,sp]) if population=='full' else len(cfg['cost_panel'][ds][sp]['ids']);assert n==expected
        for qid,q in qs.items():
            assert set(q)==set(ACTIONS)
            if population=='panel':assert len({(r['job_id'],r['block_id']) for r in q.values()})==1
            row={**base,'id':qid,'scoring_version':VERSION,'parser_sha256':freeze['code_sha256'],'freeze_sha256':sha(O/'RULE_FREEZE_V2.json'),
                 'gold':q['receiver_only']['gold'],'legal_labels':q['receiver_only']['legal_labels'].split('|'),
                 'split_role':'train' if sp=='train' else 'exposed_development','runtime_failure':False}
            row.pop('n')
            for a,letter in zip(ACTIONS,LETTERS):
                r=q[a];f=flip(q,a,'V2')
                for name,val in [('o',r['V2_o']),('valid',r['V2_valid']),('y',r['V2_y']),('invalid',1-r['V2_valid']),('reason',r['V2_reason']),*f.items()]:row[name+'_'+letter]=val
                row['source_'+letter]={k:r[k] for k in ['source_id','source_line','source_path','raw_sha256','job_id','block_id']}
            name,file=streams[population,'train' if sp=='train' else 'development'];file.write(json.dumps(row,ensure_ascii=False,separators=(',',':'))+'\n')
        for before in ['old','D1']:
            rr=[r for q in qs.values() for r in q.values()]
            popchanges.append({**base,'comparison':before+'_to_V2','action_records':len(rr),'answer_changed':sum(r[before+'_o']!=r['V2_o'] for r in rr),
                'validity_changed':sum(r[before+'_valid']!=r['V2_valid'] for r in rr),'correctness_improved':sum(r['V2_y']>r[before+'_y'] for r in rr),
                'correctness_harmed':sum(r['V2_y']<r[before+'_y'] for r in rr)})
        for a in ACTIONS:
            rr=[q[a] for q in qs.values()];ar={**base,'action':a};fr={**base,'action':a}
            for v in SCHEMES:
                valid=sum(r[v+'_valid'] for r in rr);correct=sum(r[v+'_y'] for r in rr)
                ar.update({v+'_valid':valid,v+'_invalid':n-valid,v+'_correct':correct,v+'_accuracy':correct/n,
                    v+'_exclusive_correct':sum(q[a][v+'_y'] and not any(q[b][v+'_y'] for b in ACTIONS if b!=a) for q in qs.values())})
                fs=[flip(q,a,v) for q in qs.values()]
                for k in fs[0]:fr[v+'_'+k]=sum(r[k] for r in fs)
                ar[v+'_gain_over_R']=fr[v+'_gain'];ar[v+'_harm_vs_R']=fr[v+'_harm']
                fr[v+'_historical_direction_diagnostic']=(fr[v+'_gain']-fr[v+'_harm'])/(fr[v+'_f']+2)
                for r in rr:reasoncounts[(population,pair,ds,sp,a,v,r[v+'_reason'])]+=1
            for before in ['old','D1']:
                tag=before+'_to_V2'
                ar[tag+'_answer_changed']=sum(r[before+'_o']!=r['V2_o'] for r in rr)
                ar[tag+'_correct_improved']=sum(r['V2_y']>r[before+'_y'] for r in rr);ar[tag+'_correct_harmed']=sum(r['V2_y']<r[before+'_y'] for r in rr)
                ar[tag+'_accuracy_delta_pp']=100*(ar['V2_correct']-ar[before+'_correct'])/n
                fr[tag+'_f_changed']=sum(flip(q,a,before)['f']!=flip(q,a,'V2')['f'] for q in qs.values())
                fr[tag+'_invalid_flip_changed']=sum(flip(q,a,before)['invalid_flip']!=flip(q,a,'V2')['invalid_flip'] for q in qs.values())
                for qid,q in qs.items():
                    oldf,newf=flip(q,a,before),flip(q,a,'V2')
                    if oldf!=newf:fchanges.append({**base,'id':qid,'action':a,'comparison':tag,**{before+'_'+k:v for k,v in oldf.items()},**{'V2_'+k:v for k,v in newf.items()},
                        'R_source_id':q['receiver_only']['source_id'],'R_source_line':q['receiver_only']['source_line'],'action_source_id':q[a]['source_id'],'action_source_line':q[a]['source_line']})
            acc.append(ar);ffr.append(fr)
        cr={**base}
        for v in SCHEMES:
            yc={a:sum(q[a][v+'_y'] for q in qs.values()) for a in ACTIONS};best=max(yc.values())
            u3=sum(any(q[a][v+'_y'] for a in ACTIONS[:3]) for q in qs.values());u4=sum(any(q[a][v+'_y'] for a in ACTIONS) for q in qs.values())
            cr.update({v+'_best_fixed':'|'.join(a for a in ACTIONS if yc[a]==best),v+'_best_fixed_correct':best,v+'_union3':u3,v+'_union4':u4,v+'_gap':u4-best,v+'_gap_pp':100*(u4-best)/n,v+'_AC_exclusive':u4-u3})
            cr.update({v+'_'+a+'_correct':yc[a] for a in ACTIONS})
        comp.append(cr)
        for a,b in itertools.combinations(ACTIONS,2):
            ar={**base,'a':a,'b':b}
            for v in SCHEMES:
                eq=sum(q[a][v+'_o']==q[b][v+'_o'] for q in qs.values());bv=sum(q[a][v+'_valid'] and q[b][v+'_valid'] for q in qs.values())
                veq=sum(q[a][v+'_valid'] and q[b][v+'_valid'] and q[a][v+'_o']==q[b][v+'_o'] for q in qs.values())
                ar.update({v+'_equal_including_INVALID':eq,v+'_agreement':eq/n,v+'_both_valid':bv,v+'_equal_both_valid':veq,v+'_agreement_both_valid':veq/bv if bv else '',v+'_both_invalid':sum(not q[a][v+'_valid'] and not q[b][v+'_valid'] for q in qs.values())})
            agreements.append(ar)
    for (population,role),(name,f) in streams.items():
        f.close();label_manifest.append({'path':str(P/O.name/name),'relative_path':name,'sha256':sha(O/name),'size_bytes':(O/name).stat().st_size,'population':population,'role':role,
            'question_rows':sum(r['n'] for r in comp if r['population']==population and (r['split']=='train')==(role=='train'))})
    # D1 reconstructed from its saved changes must exactly reproduce completed summaries.
    inherited_acc={(r['population'],r['pair'],r['dataset'],r['split'],r['action']):r for r in csv.DictReader((S/'action_accuracy_sensitivity.csv').open())}
    for r in acc:
        prior=inherited_acc[tuple(r[k] for k in ['population','pair','dataset','split','action'])]
        for v,pref in [('old','saved'),('D1','diagnostic')]:
            for met in ['correct','valid','invalid']:assert r[v+'_'+met]==int(prior[pref+'_'+met])
    table('scoring_records.csv',records);table('changed_records.csv',changed);table('action_summary.csv',acc)
    table('complementarity.csv',comp);table('pairwise_agreement.csv',agreements);table('flip_summary.csv',ffr);table('changed_flip_labels.csv',fchanges)
    table('population_changes.csv',popchanges);table('runtime_failures.csv',failures)
    table('reason_counts.csv',[dict(zip(['population','pair','dataset','split','action','scheme','reason'],k),count=n) for k,n in sorted(reasoncounts.items())])
    save('labels/LABEL_MANIFEST.json',label_manifest)
    save('evidence/source_coverage.json',coverage)
    save('SCORING_COMPLETE.json',{'status':'SCORING_COMPLETE','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'records':len(records),
         'full_records':45008,'panel_records':6144,'overlap_AC_records':1536,'inherited_old_replay_mismatch':0,'old_parser_rerun':False,
         'D1_saved_summary_exact_match':True,'runtime_failure_attempts':len(failures),'scoring_code_sha256':sha(__file__),
         'parser_sha256':sha(O/'scoring_v2.py'),'rule_freeze_sha256':sha(O/'RULE_FREEZE_V2.json')})
    print(json.dumps({'population_changes':popchanges,'labels':label_manifest},ensure_ascii=False,indent=2))
