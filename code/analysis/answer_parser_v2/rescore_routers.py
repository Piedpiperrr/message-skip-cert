"""Re-evaluate saved choices/probabilities; no model import, prediction or fitting."""
import json,csv,itertools,datetime
from pathlib import Path
import numpy as np
from rescore_answers import O,P,P10,ACTIONS,LETTERS,SCHEMES,sha,save,table,jl
PRIMARY='word_lambda0.01_actions4';ABL='word_lambda0.01_actions3'
LAMBDAS=[0,.01,.03,.1,.3,1,3]
def arr(x):return np.asarray(x)
def quant(x,p):return float(np.percentile(x,p))
def main():
    if (O/'ROUTING_COMPLETE.json').exists():raise SystemExit('ALREADY_COMPLETE; reuse')
    assert (O/'SCORING_COMPLETE.json').exists()
    manifest=[]
    def register(p,role):
        manifest.append({'path':str(p),'sha256':sha(p),'size_bytes':p.stat().st_size,'role':role})
    # Small per-question versioned matrices from already-scored records.
    pop={}
    for r in csv.DictReader((O/'scoring_records.csv').open()):
        for v in SCHEMES:
            r[v+'_y']=int(r[v+'_y']);r[v+'_valid']=int(r[v+'_valid'])
        r['latency_ms']=float(r['latency_ms'])
        for population in ['full','panel']:
            if r['in_'+population]=='True':pop.setdefault((population,r['pair'],r['dataset'],r['split']),{}).setdefault(r['id'],{})[r['action']]=r
    results=[];comparisons=[];selections=[];replacements=[];mixrows=[];aucrows=[];missing=[];primary_sources=[]
    for pair,ds in itertools.product(['large','small'],['obqa','arc']):
        d=P10/'results'/pair/ds;dv='dev' if ds=='obqa' else 'validation'
        receipt=json.loads((d/'train_mixture_receipt.json').read_text());mix=np.array(receipt['mixture']['probabilities'])
        assert np.isclose(mix.sum(),1) and (mix>=0).all();register(d/'train_mixture_receipt.json','unchanged train-frozen mixture probabilities')
        overhead={}
        for ln,r in jl(d/'router_overhead.jsonl'):overhead[r['split'],r['id'],r['family'],r['n_actions']]=r
        register(d/'router_overhead.jsonl','saved per-question choices and original online overhead; read-only')
        replay={(r['id'],r['policy']):r for r in csv.DictReader((d/'router_replay.csv').open())};register(d/'router_replay.csv','saved original dev panel action/overhead/total latency')
        historical={population:{r['policy']:r for r in csv.DictReader((d/name).open())} for population,name in [('full','full_dev_all_policy_results.csv'),('panel','cost_panel_all_policy_results.csv')]}
        for name in ['full_dev_all_policy_results.csv','cost_panel_all_policy_results.csv']:register(d/name,'old fixed-policy summary for exact arithmetic consistency')
        for sp in ['train',dv]:
            policies={a:None for a in LETTERS};predictions={};choice_maps={};prob_maps={}
            for family in ['word','semantic']:
                path=d/(('train' if sp=='train' else 'dev')+'_predictions_'+family+'.npz')
                if not path.exists():
                    # Registered CPU fallback: original online choices (panel only).
                    missing.append(dict(pair=pair,dataset=ds,split=sp,family=family,missing_path=str(path),status='missing full choices; panel online choices remain available'))
                    continue
                register(path,'saved choices/probabilities; no estimator loaded')
                z=np.load(path,allow_pickle=False);ids=z['ids'].tolist();assert len(set(ids))==len(ids)
                if 'lambdas' in z:assert np.allclose(z['lambdas'],LAMBDAS)
                predictions[family]={k:z[k] for k in z.files};z.close()
                for na,li in itertools.product([3,4],range(7)):
                    name=f'{family}_lambda{LAMBDAS[li]:g}_actions{na}'
                    choice_maps[name]=dict(zip(ids,predictions[family][f'choices{na}'][:,li].astype(int).tolist()))
                    policies[name]=(family,na,li)
            policies['train_frozen_mixture']=None
            for population in ['full','panel']:
                qs=pop[population,pair,ds,sp];ids=list(qs);n=len(ids);idx=np.arange(n)
                y={v:np.array([[qs[i][a][v+'_y'] for a in ACTIONS] for i in ids],float) for v in SCHEMES}
                valid={v:np.array([[qs[i][a][v+'_valid'] for a in ACTIONS] for i in ids],float) for v in SCHEMES}
                options={v:np.array([[qs[i][a][v+'_o'] for a in ACTIONS] for i in ids]) for v in SCHEMES}
                costs=np.array([[qs[i][a]['latency_ms'] for a in ACTIONS] for i in ids]) if population=='panel' else None
                vectors={};cost_vectors={};choice_vectors={};group=[]
                base=dict(population=population,pair=pair,dataset=ds,split=sp,n=n,training_labels='old_scoring',refitted_V2=False,
                    evaluation_role='train_in_sample_diagnostic' if sp=='train' else 'previously_exposed_development',timing_source='original_P2_10_same_job' if population=='panel' else 'accuracy_only')
                for name,spec in policies.items():
                    if name in LETTERS:
                        choices=np.full(n,LETTERS.index(name));weights=np.eye(4)[choices];oh=np.zeros(n);source='fixed_action'
                    elif name=='train_frozen_mixture':
                        choices=None;weights=np.broadcast_to(mix,(n,4));oh=np.zeros(n);source=str(d/'train_mixture_receipt.json')
                    else:
                        family,na,li=spec;choices=np.array([choice_maps[name][i] for i in ids]);weights=np.eye(4)[choices]
                        source=str(d/(('train' if sp=='train' else 'dev')+'_predictions_'+family+'.npz'))
                        if population=='panel':
                            online=np.array([overhead[sp,i,family,na]['choices'][li] for i in ids]);assert np.array_equal(online,choices)
                            oh=np.array([overhead[sp,i,family,na]['overhead_ms'] for i in ids])
                            for i in ids:
                                if sp!='train':assert overhead[sp,i,family,na]['block_id']==qs[i]['receiver_only']['block_id']
                        else:oh=None
                    row={**base,'policy':name,'is_original_primary':name==PRIMARY,'selection_source':source,
                        'probabilities':json.dumps(mix.tolist()) if choices is None else '',
                        'selection_counts_RTCA':json.dumps(np.bincount(choices,minlength=4).tolist()) if choices is not None else '',
                        'old_to_V2_selected_correctness_up':float(np.sum(weights*(y['V2']>y['old']))),
                        'old_to_V2_selected_correctness_down':float(np.sum(weights*(y['V2']<y['old']))),
                        'D1_to_V2_selected_correctness_up':float(np.sum(weights*(y['V2']>y['D1']))),
                        'D1_to_V2_selected_correctness_down':float(np.sum(weights*(y['V2']<y['D1'])))}
                    vectors[name]={v:(y[v]*weights).sum(1) for v in SCHEMES};choice_vectors[name]=choices
                    for v in SCHEMES:
                        flip=(options[v]!=options[v][:,[0]]);inv=(1-valid[v]).astype(bool)|((1-valid[v][:,[0]]).astype(bool))
                        gain=(y[v]>y[v][:,[0]]);harm=(y[v]<y[v][:,[0]])
                        row.update({v+'_correct':float(vectors[name][v].sum()),v+'_accuracy':float(vectors[name][v].mean()),
                            v+'_valid':float((weights*valid[v]).sum()),v+'_invalid':float((weights*(1-valid[v])).sum()),
                            v+'_gain_over_R':float((weights*gain).sum()),v+'_harm_vs_R':float((weights*harm).sum()),
                            v+'_flips':float((weights*flip).sum()),v+'_zero_gain_flips':float((weights*flip*~(gain|harm)).sum()),
                            v+'_INVALID_flips':float((weights*flip*inv).sum())})
                    if population=='panel':
                        ms=(costs*weights).sum(1)+oh;cost_vectors[name]=ms
                        row.update(mean_ms=float(ms.mean()),median_ms=quant(ms,50),p95_ms=quant(ms,95),mean_original_router_overhead_ms=float(oh.mean()))
                        if spec and sp!='train':
                            for k,i in enumerate(ids):
                                r=replay[i,name];assert ACTIONS[choices[k]]==r['selected_action']
                                assert np.isclose(ms[k],float(r['total_ms']),rtol=0,atol=1e-9)
                                assert np.isclose(costs[k,choices[k]],float(r['action_ms']),rtol=0,atol=1e-9)
                    if sp!='train':
                        hist=historical[population][name]
                        assert np.isclose(row['old_correct'],float(hist['correct']),atol=1e-8,rtol=0)
                        if population=='panel':assert np.isclose(row['mean_ms'],float(hist['mean_ms']),atol=1e-8,rtol=0)
                    group.append(row);results.append(row)
                    if name in [PRIMARY,ABL,'train_frozen_mixture']:
                        for k,i in enumerate(ids):
                            selections.append({**base,'id':i,'policy':name,'selected_action':ACTIONS[choices[k]] if choices is not None else 'expected_mixture',
                                'probabilities':row['probabilities'],**{v+'_correct':float(vectors[name][v][k]) for v in SCHEMES},
                                'original_total_ms':float(cost_vectors[name][k]) if population=='panel' else '',
                                'source_ids_RTCA':'|'.join(qs[i][a]['source_id']+':'+str(qs[i][a]['source_line']) for a in ACTIONS)})
                # Same saved 3/4 choices; decomposition does not use newly selected dev points.
                c3,c4=choice_vectors[ABL],choice_vectors[PRIMARY];changed=c3!=c4
                rep={**base,'changed_actions_3_to_4':int(changed.sum()),'selected_A':int((c4==3).sum()),
                    'AC_exclusive_captured_V2':int(((y['V2'][:,3]==1)&(y['V2'][:,:3].sum(1)==0)&(c4==3)).sum())}
                for v in SCHEMES:
                    delta=vectors[PRIMARY][v]-vectors[ABL][v]
                    rep.update({v+'_four_minus_three_correct':float(delta.sum()),v+'_improved':int((delta>0).sum()),v+'_harmed':int((delta<0).sum()),v+'_same_on_changed':int((changed&(delta==0)).sum())})
                replacements.append(rep)
                if sp!='train':
                    refs=[ABL,*LETTERS,'train_frozen_mixture']
                    # Recompute conditional intervals, with the same original 20k/seed0 design.
                    cols=[];meta=[]
                    for v,ref in itertools.product(SCHEMES,refs):cols.append(vectors[PRIMARY][v]-vectors[ref][v]);meta.append((v,ref))
                    if population=='panel':
                        for ref in refs:cols.append(cost_vectors[PRIMARY]-cost_vectors[ref]);meta.append(('latency',ref))
                    matrix=np.column_stack(cols);rng=np.random.default_rng(0);boot=[]
                    for start in range(0,20000,200):
                        ix=rng.integers(0,n,size=(200,n));boot.append(matrix[ix].mean(1))
                    ci=np.percentile(np.concatenate(boot),[2.5,97.5],axis=0);metaidx={x:i for i,x in enumerate(meta)}
                    for ref in refs:
                        row={**base,'primary':PRIMARY,'reference':ref,'bootstrap_n':20000,'bootstrap_seed':0,'conditional_on':'saved old-trained policies and original measurement; exposed development'}
                        for v in SCHEMES:
                            j=metaidx[v,ref];row.update({v+'_accuracy_delta_pp':100*float(matrix[:,j].mean()),v+'_ci_low_pp':100*float(ci[0,j]),v+'_ci_high_pp':100*float(ci[1,j])})
                        if population=='panel':
                            j=metaidx['latency',ref];row.update(original_latency_delta_ms=float(matrix[:,j].mean()),latency_ci_low_ms=float(ci[0,j]),latency_ci_high_ms=float(ci[1,j]))
                        comparisons.append(row)
                    # Saved 286 mixtures and old descriptive-envelope probabilities remain fixed.
                    if population=='panel':
                        for name in ['query_independent_mixtures_286.csv','continuous_mixture_comparisons.csv']:
                            register(d/name,'saved mixture probabilities; rescored without reoptimizing envelope')
                            for k,r in enumerate(csv.DictReader((d/name).open()),1):
                                if not r.get('probabilities'):continue
                                w=np.array(json.loads(r['probabilities']));assert np.isclose(w.sum(),1)
                                row={**base,'saved_reference_file':name,'saved_row':k,'policy':r['policy'],'probabilities':r['probabilities'],'mean_ms':float((costs@w).mean()),'V2_reoptimized':False}
                                for v in SCHEMES:row.update({v+'_correct':float((y[v]@w).sum()),v+'_accuracy':float((y[v]@w).mean())})
                                mixrows.append(row)
                # Discrimination of saved probability differences, never fitted V2 AUC.
                if population=='full' and sp!='train':
                    for family,z in predictions.items():
                        order={i:k for k,i in enumerate(z['ids'].tolist())};prob=z['probabilities'][[order[i] for i in ids]]
                        for a,b in itertools.combinations(range(4),2):
                            row={**base,'family':family,'action_pair':LETTERS[a]+'-'+LETTERS[b],'prediction_source':'unchanged_saved_probabilities'}
                            score=prob[:,a]-prob[:,b]
                            for v in SCHEMES:
                                pos=(y[v][:,a]>y[v][:,b]);neg=(y[v][:,a]<y[v][:,b]);x=score[pos];zneg=score[neg]
                                auc=float(((x[:,None]>zneg).sum()+.5*(x[:,None]==zneg).sum())/(len(x)*len(zneg))) if len(x)*len(zneg) else None
                                row.update({v+'_positive_n':int(pos.sum()),v+'_negative_n':int(neg.sum()),v+'_auc':auc})
                            aucrows.append(row)
        print('RESCORED_SAVED_ROUTING',pair,ds,flush=True)
    table('frozen_policy_rescoring.csv',results);table('primary_paired_comparisons.csv',comparisons)
    table('primary_per_question.csv',selections);table('primary_three_four_replacements.csv',replacements)
    table('saved_mixture_rescoring.csv',mixrows);table('saved_head_pairwise_discrimination.csv',aucrows);table('unrecoverable_policy_items.csv',missing)
    save('evidence/router_source_manifest.json',manifest)
    save('ROUTING_COMPLETE.json',{'status':'ROUTING_COMPLETE','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'policy_rows':len(results),'saved_mixture_rows':len(mixrows),'primary_paired_comparisons':len(comparisons),'primary_per_question_rows':len(selections),
        'missing_items':missing,'all_old_dev_correctness_matched':True,'all_original_panel_latency_matched':True,
        'choices_changed':False,'parameters_changed':False,'mixture_probabilities_changed':False,'router_refits':0,'new_feature_extractions':0,
        'script_sha256':sha(__file__),'bootstrap_note':'20000 paired question resamples, seed0, 95% percentile, identical population and original timing, mixture expectations'})
    print('ROUTING_COMPLETE',len(results),len(comparisons),len(mixrows),flush=True)
if __name__=='__main__':main()
