"""独立从原答/冻结选择重算核心计数、成本与bootstrap，不调用分析器。"""
import csv,json,hashlib,itertools
from pathlib import Path
import numpy as np
from common_p2_10 import ROOT,readrows,sha,save,utc,ACTIONS
from scoring import score as obqa_score
import arc_protocol as arc

def main():
    cfg=json.loads((ROOT/'frozen_config.json').read_text());assert sha(ROOT/'frozen_config.json')==json.loads((ROOT/'evidence/freeze_receipt.json').read_text())['config_sha256']
    assert sha(cfg['small_W']['path'])==cfg['small_W']['sha256']
    req=readrows(ROOT/'data/request_manifest.jsonl');expected={r['key'] for r in req};all_success=[];checks=[]
    known={('large','obqa'):[617,645,587],('large','arc'):[268,274,255],('small','obqa'):[285,346,365],('small','arc'):[110,126,155]}
    for pair,dataset in itertools.product(['large','small'],['obqa','arc']):
        out=ROOT/'results'/pair/dataset;dev='dev' if dataset=='obqa' else 'validation';scores={};latencies={}
        for split in ['train',dev]:
            originals=[r for r in readrows(out/f'{split}_cases.jsonl') if r['runtime_error'] is None];all_success+=originals
            frozen_order=[r['key'] for r in req if (r['pair'],r['dataset'],r['split'])==(pair,dataset,split)]
            assert [r['key'] for r in originals]==frozen_order,'actual successful request order differs from frozen manifest'
            for r in originals:
                scored=obqa_score(r['raw_answer'],r['gold_answer']) if dataset=='obqa' else arc.score(r['raw_answer'],r['gold_answer'],r['legal_labels'])
                assert all(scored[k]==r['scoring'][k] for k in ['answer','valid','correct']),r['key']
                assert r['receiver_generated_tokens']==len(r['generated_token_ids'])<=64
                assert r['helper_generated_tokens']<=256
                if r['action']=='acw':
                    assert r['audit']['injections']==1 and r['audit']['calls']==len(r['generated_token_ids'])
                    assert r['audit']['block_index']==cfg['ac_layers']['receiver'][pair]['block_index']
                    assert r['audit']['prompt_position']==r['receiver_input_tokens']-1
            scores[split]={(r['id'],r['action']):int(r['scoring']['correct']) for r in originals};latencies[split]={(r['id'],r['action']):r['latency_ms'] for r in originals}
        old={(r['id'],r['action']):r for r in readrows(out/f'{dev}_historical_rtc.jsonl')}
        rr=readrows(cfg['data'][dataset][dev]['path']);ids=[r['id'] for r in rr]
        expected_y=[[scores[dev][i,'acw'] if a=='acw' else int(old[i,a]['scoring']['correct']) for a in ACTIONS] for i in ids]
        assert [sum(row[a] for row in expected_y) for a in range(3)]==known[pair,dataset]
        matrix=np.load(out/f'{dev}_full_matrix.npz');assert matrix['ids'].tolist()==ids and matrix['correctness'].tolist()==expected_y
        assert np.isnan(matrix['current_independent_ms'][:,:3]).all()
        panelids=cfg['cost_panel'][dataset][dev]['ids'];panel_y=[[scores[dev][i,a] for a in ACTIONS] for i in panelids];panel_t=[[latencies[dev][i,a] for a in ACTIONS] for i in panelids]
        panel=np.load(out/f'{dev}_cost_panel_matrix.npz');assert panel['ids'].tolist()==panelids and panel['correctness'].tolist()==panel_y and np.allclose(panel['latency_ms'],panel_t,rtol=0,atol=0)
        oh={(r['split'],r['id'],r['family'],r['n_actions']):r for r in readrows(out/'router_overhead.jsonl')}
        for r in csv.DictReader((out/'router_replay.csv').open()):
            f=r['policy'].split('_lambda')[0];na=int(r['policy'][-1]);lam=float(r['policy'].split('_lambda')[1].split('_')[0]);li=cfg['lambdas'].index(lam)
            pred=np.load(out/f'dev_predictions_{f}.npz');di=ids.index(r['id']);ci=int(pred[f'choices{na}'][di,li]);a=ACTIONS[ci]
            expected_ms=oh[dev,r['id'],f,na]['overhead_ms']+latencies[dev][r['id'],a]
            assert int(r['correct'])==scores[dev][r['id'],a] and abs(float(r['total_ms'])-expected_ms)<1e-9
            assert r['selected_action']==a
        pred=np.load(out/'dev_predictions_word.npz');y=np.asarray(expected_y,dtype=float);py=np.asarray(panel_y,dtype=float);pt=np.asarray(panel_t)
        choices=pred['choices4'][:,1];abl=pred['choices3'][:,1];pi=[ids.index(i) for i in panelids]
        mix=json.loads((out/'train_mixture_receipt.json').read_text())['mixture'];mp=np.array(mix['probabilities']) if mix['status']=='feasible' else None
        comparisons_checked=0
        for pop,iids,yy,c4,c3,tm in [('full_dev',ids,y,choices,abl,None),('cost_panel',panelids,py,choices[pi],abl[pi],pt)]:
            n=len(iids);primary=np.array([yy[j,c4[j]] for j in range(n)]);refs={'word_lambda0.01_actions3':np.array([yy[j,c3[j]] for j in range(n)]),**{a:yy[:,k] for k,a in enumerate(['R','T','C','A'])}}
            if mp is not None:refs['train_frozen_mixture']=np.array([sum(row[k]*mp[k] for k in range(4)) for row in yy])
            ds=[primary-r for r in refs.values()]
            if tm is not None:
                pms=np.array([oh[dev,i,'word',4]['overhead_ms']+tm[j,c4[j]] for j,i in enumerate(iids)])
                rms={'word_lambda0.01_actions3':np.array([oh[dev,i,'word',3]['overhead_ms']+tm[j,c3[j]] for j,i in enumerate(iids)]),**{a:tm[:,k] for k,a in enumerate(['R','T','C','A'])}}
                if mp is not None:rms['train_frozen_mixture']=np.array([sum(row[k]*mp[k] for k in range(4)) for row in tm])
                ds += [pms-r for r in rms.values()]
            delta=np.column_stack(ds);rng=np.random.default_rng(0);samples=[]
            # Alternate arithmetic: multinomial counts from the SAME integer draws.
            for st in range(0,20000,200):
                draw=rng.integers(n,size=(200,n));offset=np.arange(200)[:,None]*n
                counts=np.bincount((draw+offset).ravel(),minlength=200*n).reshape(200,n)
                samples.append(counts@delta/n)
            ci=np.quantile(np.concatenate(samples),[.025,.975],axis=0)
            saved=list(csv.DictReader((out/f'{pop}_primary_paired.csv').open()))
            for k,r in enumerate(saved):
                assert r['reference']==list(refs)[k]
                assert abs(float(r['accuracy_difference_pp'])-delta[:,k].mean()*100)<1e-10
                assert abs(float(r['accuracy_ci_low_pp'])-ci[0,k]*100)<1e-9 and abs(float(r['accuracy_ci_high_pp'])-ci[1,k]*100)<1e-9
                if tm is not None:
                    j=k+len(refs);assert abs(float(r['latency_difference_ms'])-delta[:,j].mean())<1e-9
                    assert abs(float(r['latency_ci_low_ms'])-ci[0,j])<1e-8 and abs(float(r['latency_ci_high_ms'])-ci[1,j])<1e-8
                comparisons_checked+=1
        # Reconstruct B_train from the actual online decisions and measurements.
        train_ids=cfg['cost_panel'][dataset]['train']['ids'];bs=[]
        for i in train_ids:
            h=oh['train',i,'word',4];bs.append(h['overhead_ms']+latencies['train'][i,ACTIONS[h['choices'][1]]])
        mr=json.loads((out/'train_mixture_receipt.json').read_text());assert abs(sum(bs)/256-mr['B_train'])<1e-9
        checks.append({'pair':pair,'dataset':dataset,'historical_fixed_correct':known[pair,dataset],'new_raw_scoring_verified':True,'full_and_panel_matrices':True,'router_replay_rows':128*28,'paired_comparisons_recomputed':comparisons_checked,'B_train_recomputed':True})
    assert len(all_success)==len({r['key'] for r in all_success})==15860 and {r['key'] for r in all_success}==expected
    assert sum(r['action']=='acw' for r in all_success)==11252
    ledger=json.loads((ROOT/'evidence/submissions.json').read_text());assert len(ledger)<=3
    assert all(r['requested_node_seconds']<=cap for r,cap in zip(ledger,[10800,7200,3600])) and sum(r['requested_node_seconds'] for r in ledger)<=21600
    w=json.loads((ROOT/'results/large/W/final_receipt.json').read_text());assert w['steps']==960 and sha(ROOT/'results/large/W/W_final.pt')==w['sha256']
    for n,h in cfg['execution_source_sha256'].items():assert sha(ROOT/n)==h
    save(ROOT/'evidence/independent_result_check.json',{'utc':utc(),'passed':True,'unique_successes':15860,'AC':11252,'new_RTC':4608,'combinations':checks,'small_W_hash_unchanged':True,'large_W_step_and_hash':True,'frozen_sources_unchanged':True,'budget_within_limits':True,'method':'raw-answer scoring; direct key lookup; independently reconstructed paired vectors; count-weighted bootstrap arithmetic'})
    print('P2_10_INDEPENDENT_CHECK_PASS')
if __name__=='__main__':main()
