"""P2-10 双口径分析；仅CPU读取冻结答案、选择与本轮独立计时。"""
import csv,itertools,json
from pathlib import Path
import numpy as np
import joblib
from common_p2_10 import ROOT,ACTIONS,LAMBDAS,readrows,save,sha,utc
from router_p2_10 import best_mixture,predict
from progress_p2_10 import progress

LABELS=['R','T','C','A']
def csvout(path,rows):
    rows=list(rows)
    if not rows:return
    fields=list(dict.fromkeys(k for r in rows for k in r))
    with Path(path).open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
        for r in rows:w.writerow({k:json.dumps(v,ensure_ascii=False) if isinstance(v,(list,dict)) else v for k,v in r.items()})

def summarize(name,y,valid,choice=None,ms=None,overhead=None,**extra):
    r={'policy':name,'n':len(y),'correct':float(np.sum(y)),'accuracy':float(np.mean(y)),'invalid':None if valid is None else int((~np.asarray(valid,dtype=bool)).sum()),**extra}
    if choice is not None:
        r['selection_counts']=np.bincount(choice,minlength=4).tolist();r['selection_proportions']=(np.bincount(choice,minlength=4)/len(y)).tolist()
    if ms is not None:r.update(mean_ms=float(np.mean(ms)),median_ms=float(np.median(ms)),p95_ms=float(np.percentile(ms,95)),mean_overhead_ms=0. if overhead is None else float(np.mean(overhead)))
    return r

def paired(out,population,ids,primary,refs,primary_ms=None,ref_ms=None):
    names=list(refs);diff=np.column_stack([primary-refs[n] for n in names]).astype(float)
    arrays=[diff];fields=['accuracy']
    if primary_ms is not None:
        ld=np.column_stack([primary_ms-ref_ms[n] for n in names]);arrays.append(ld);fields.append('latency_ms')
    both=np.concatenate(arrays,axis=1);rng=np.random.default_rng(0);samples=[]
    # Share every resample across all references and accuracy/latency statistics.
    for start in range(0,20000,200):
        draw=rng.integers(0,len(ids),size=(min(200,20000-start),len(ids)))
        samples.append(both[draw].mean(1))
    boot=np.concatenate(samples);ci=np.percentile(boot,[2.5,97.5],axis=0)
    result=[]
    for k,name in enumerate(names):
        r={'population':population,'n':len(ids),'primary':'word_lambda0.01_actions4','reference':name,'accuracy_difference_pp':float(diff[:,k].mean()*100),'accuracy_ci_low_pp':float(ci[0,k]*100),'accuracy_ci_high_pp':float(ci[1,k]*100),'primary_accuracy':float(primary.mean()),'reference_accuracy':float(refs[name].mean())}
        if primary_ms is not None:
            j=k+len(names);r.update(latency_difference_ms=float(ld[:,k].mean()),latency_ci_low_ms=float(ci[0,j]),latency_ci_high_ms=float(ci[1,j]),primary_mean_ms=float(primary_ms.mean()),reference_mean_ms=float(ref_ms[name].mean()))
        result.append(r)
    np.savez(out/f'{population}_primary_paired_per_question.npz',ids=ids,reference_names=names,accuracy_differences=diff,**({'latency_differences_ms':ld} if primary_ms is not None else {}))
    save(out/f'{population}_primary_paired.json',{'seed':0,'replicates':20000,'sampling':'paired question resampling; shared draws for all references and both measures','interval':'95% percentile','conditional':'fitted models and one timing run; excludes training randomness, deployment jitter, multiplicity correction','comparisons':result})
    csvout(out/f'{population}_primary_paired.csv',result)
    return result

def analyze_combo(cfg,pair,dataset):
    out=ROOT/'results'/pair/dataset;assert (out/'completion.json').exists()
    matrices={};panels={};diffrows=[];validation={'coverage':True,'same_job_panels':True,'dev_overhead_same_job':True,'frozen_selection_replay':True,'online_choice_differences':{},'probability_max_abs_diff':{}}
    overhead=readrows(out/'router_overhead.jsonl');oh={(r['split'],r['id'],r['family'],r['n_actions']):r for r in overhead}
    assert len(oh)==len(overhead)==384*4
    fit=json.loads((out/'router_fit_receipt.json').read_text());mixrec=json.loads((out/'train_mixture_receipt.json').read_text())
    for name,h in fit['hashes'].items():assert sha(out/name)==h
    mix=mixrec['mixture'];mixp=np.array(mix['probabilities']) if mix['status']=='feasible' else None
    all_ac=[];new_originals=[]
    for split,spec in cfg['data'][dataset].items():
        rows=readrows(spec['path']);ids=[r['id'] for r in rows];n=len(rows)
        old=readrows(out/f'{split}_historical_rtc.jsonl');hm={(r['id'],r['action']):r for r in old};assert len(hm)==len(old)==n*3
        new=[r for r in readrows(out/f'{split}_cases.jsonl') if r['runtime_error'] is None];nm={(r['id'],r['action']):r for r in new};assert len(nm)==len(new)
        expected={(i,'acw') for i in ids}|{(i,a) for i in cfg['cost_panel'][dataset][split]['ids'] for a in ACTIONS[:3]};assert set(nm)==expected
        raw=[[ (nm if a=='acw' else hm)[i,a] for a in ACTIONS] for i in ids]
        y=np.array([[r['scoring']['correct'] for r in x] for x in raw],dtype=np.int8)
        valid=np.array([[r['scoring']['valid'] for r in x] for x in raw],dtype=bool)
        current_ms=np.full((n,4),np.nan);current_ms[:,3]=[nm[i,'acw']['latency_ms'] for i in ids]
        historical_ms=np.full((n,4),np.nan);historical_ms[:,:3]=[[hm[i,a]['latency_ms'] for a in ACTIONS[:3]] for i in ids]
        np.savez(out/f'{split}_full_matrix.npz',ids=ids,actions=ACTIONS,correctness=y,valid=valid,current_independent_ms=current_ms,historical_ms=historical_ms)
        csvout(out/f'{split}_full_matrix.csv',[{'id':i,'split':split,'gold_answer':rows[k]['gold_answer'],**{f'{LABELS[a]}_correct':int(y[k,a]) for a in range(4)},**{f'{LABELS[a]}_valid':bool(valid[k,a]) for a in range(4)},'A_current_ms':current_ms[k,3],'R_current_ms':None,'T_current_ms':None,'C_current_ms':None,'RTC_label_source':'historical successful originals','RTC_current_cost_source':'not measured for full population; see separate panel matrix','A_source':'P2-10 independent action'} for k,i in enumerate(ids)])
        pi=cfg['cost_panel'][dataset][split]['ids'];pr=[[nm[i,a] for a in ACTIONS] for i in pi]
        pc=np.array([[r['latency_ms'] for r in x] for x in pr]);py=np.array([[r['scoring']['correct'] for r in x] for x in pr],dtype=np.int8);pv=np.array([[r['scoring']['valid'] for r in x] for x in pr],dtype=bool)
        for i,b in zip(pi,pr):
            assert len({r['job_id'] for r in b})==len({r['block_id'] for r in b})==1
            if split!='train':
                for f in ['word','semantic']:
                    for na in [3,4]:assert oh[split,i,f,na]['job_id']==b[0]['job_id'] and oh[split,i,f,na]['block_id']==b[0]['block_id']
            for a in ACTIONS[:3]:
                nr=nm[i,a];hr=hm[i,a]
                diffrows.append({'split':split,'id':i,'action':a,'old_job_id':hr['job_id'],'new_job_id':nr['job_id'],'token_ids_changed':hr['generated_token_ids']!=nr['generated_token_ids'],'raw_text_changed':hr['raw_answer']!=nr['raw_answer'],'parsed_answer_changed':hr['scoring']['answer']!=nr['scoring']['answer'],'correctness_changed':hr['scoring']['correct']!=nr['scoring']['correct'],'old_answer':hr['scoring']['answer'],'new_answer':nr['scoring']['answer'],'old_correct':hr['scoring']['correct'],'new_correct':nr['scoring']['correct'],'old_valid':hr['scoring']['valid'],'new_valid':nr['scoring']['valid'],'old_raw_text':hr['raw_answer'],'new_raw_text':nr['raw_answer']})
        assert np.isfinite(pc).all() and (pc>0).all()
        np.savez(out/f'{split}_cost_panel_matrix.npz',ids=pi,actions=ACTIONS,correctness=py,valid=pv,latency_ms=pc,job_ids=[[r['job_id'] for r in x] for x in pr],block_ids=[[r['block_id'] for r in x] for x in pr])
        csvout(out/f'{split}_cost_panel_matrix.csv',[{'id':i,'split':split,'same_job':pr[k][0]['job_id'],**{f'{LABELS[a]}_correct':int(py[k,a]) for a in range(4)},**{f'{LABELS[a]}_ms':float(pc[k,a]) for a in range(4)}} for k,i in enumerate(pi)])
        (out/f'{split}_AC_originals.jsonl').write_text(''.join(json.dumps(nm[i,'acw'],ensure_ascii=False)+'\n' for i in ids))
        (out/f'{split}_cost_panel_originals.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for x in pr for r in x))
        matrices[split]=(ids,y,valid,current_ms);panels[split]=(pi,py,pv,pc)
        all_ac.extend([{'split':split,'id':i,'latency_ms':nm[i,'acw']['latency_ms'],'invalid':not nm[i,'acw']['scoring']['valid']} for i in ids])
        if split!='train':
            assert all(fit['utc']<r['utc'] and mixrec['utc']<r['utc'] for r in new),'dev action before freeze'
    csvout(out/'new_old_RTC_differences.csv',diffrows)
    changes=[]
    for split in cfg['data'][dataset]:
        for a in ACTIONS[:3]:
            rr=[r for r in diffrows if r['split']==split and r['action']==a]
            changes.append({'split':split,'action':a,'n':len(rr),**{k:sum(r[k] for r in rr) for k in ['token_ids_changed','raw_text_changed','parsed_answer_changed','correctness_changed']},'improved':sum(not r['old_correct'] and r['new_correct'] for r in rr),'harmed':sum(r['old_correct'] and not r['new_correct'] for r in rr)})
    csvout(out/'new_old_RTC_difference_summary.csv',changes)
    save(out/'AC_full_cost_summary.json',{split:{'n':len(v:= [r for r in all_ac if r['split']==split]),'mean_ms':float(np.mean([r['latency_ms'] for r in v])),'median_ms':float(np.median([r['latency_ms'] for r in v])),'p95_ms':float(np.percentile([r['latency_ms'] for r in v],95)),'invalid':sum(r['invalid'] for r in v)} for split in cfg['data'][dataset]})
    devsplit=next(s for s in cfg['data'][dataset] if s!='train');ids,y,valid,_=matrices[devsplit];pi,py,pv,pc=panels[devsplit];ix=np.array([ids.index(i) for i in pi]);n=len(ids)
    full_rows=[];panel_rows=[];full_vectors={};panel_vectors={};cost_vectors={};replays=[]
    for a,name in enumerate(LABELS):
        full_vectors[name]=y[:,a];panel_vectors[name]=py[:,a];cost_vectors[name]=pc[:,a]
        full_rows.append(summarize(name,y[:,a],valid[:,a],np.full(n,a),population='full_dev'))
        panel_rows.append(summarize(name,py[:,a],pv[:,a],np.full(128,a),pc[:,a],population='new_dev_cost_panel'))
    for family in ['word','semantic']:
        pred=np.load(out/f'dev_predictions_{family}.npz');assert pred['ids'].tolist()==ids
        b=joblib.load(out/'models'/f'{family}.joblib')
        from scipy import sparse
        x=sparse.load_npz(out/'features'/f'word_{devsplit}.npz') if family=='word' else np.load(ROOT/'data'/f'{dataset}_{devsplit}_semantic.npy')
        for na in [3,4]:
            p,c,ch=predict(b,x,na);assert np.array_equal(ch,pred[f'choices{na}']);assert np.allclose(p,pred['probabilities'][:,:na],rtol=0,atol=1e-12)
            online=np.array([oh[devsplit,i,family,na]['choices'] for i in pi]);diff=int((online!=ch[ix]).sum());validation['online_choice_differences'][f'{family}{na}']=diff
            validation['probability_max_abs_diff'][f'{family}{na}']=float(np.max(np.abs(np.array([oh[devsplit,i,family,na]['probabilities'] for i in pi])-p[ix])))
            assert diff==0,'online versus frozen choices differ; must report affected scope before deployment-equivalence claim'
            ov=np.array([oh[devsplit,i,family,na]['overhead_ms'] for i in pi])
            for k,lam in enumerate(LAMBDAS):
                name=f'{family}_lambda{lam:g}_actions{na}';choice=ch[:,k];pchoice=choice[ix]
                fy=y[np.arange(n),choice];fv=valid[np.arange(n),choice]
                cy=py[np.arange(128),pchoice];cv=pv[np.arange(128),pchoice];tm=ov+pc[np.arange(128),pchoice]
                full_vectors[name]=fy;panel_vectors[name]=cy;cost_vectors[name]=tm
                full_rows.append(summarize(name,fy,fv,choice,population='full_dev',family=family,n_actions=na,lambda_value=lam))
                panel_rows.append(summarize(name,cy,cv,pchoice,tm,ov,population='new_dev_cost_panel',family=family,n_actions=na,lambda_value=lam))
                for j,i in enumerate(pi):replays.append({'id':i,'policy':name,'selected_action':ACTIONS[pchoice[j]],'correct':int(cy[j]),'action_ms':float(pc[j,pchoice[j]]),'router_overhead_ms':float(ov[j]),'total_ms':float(tm[j]),'job_id':oh[devsplit,i,family,na]['job_id']})
    primary='word_lambda0.01_actions4';abl='word_lambda0.01_actions3'
    if mixp is not None:
        full_vectors['train_frozen_mixture']=y@mixp;panel_vectors['train_frozen_mixture']=py@mixp;cost_vectors['train_frozen_mixture']=pc@mixp
        full_rows.append(summarize('train_frozen_mixture',y@mixp,None,population='full_dev',probabilities=mixp.tolist()))
        panel_rows.append(summarize('train_frozen_mixture',py@mixp,None,ms=pc@mixp,population='new_dev_cost_panel',probabilities=mixp.tolist()))
    # All router points retained, with paired improvements/harm against every fixed action and corresponding ablation.
    for table,vectors in [(full_rows,full_vectors),(panel_rows,panel_vectors)]:
        for r in table:
            if 'actions' not in r['policy']:continue
            refs=LABELS+[r['policy'].replace('actions4','actions3')]
            v=vectors[r['policy']]
            for ref in refs:
                rv=vectors[ref];r[f'improved_vs_{ref}']=int(((v==1)&(rv==0)).sum());r[f'harmed_vs_{ref}']=int(((v==0)&(rv==1)).sum())
    csvout(out/'full_dev_all_policy_results.csv',full_rows);csvout(out/'cost_panel_all_policy_results.csv',panel_rows);csvout(out/'router_replay.csv',replays)
    refs=[abl]+LABELS+(['train_frozen_mixture'] if mixp is not None else [])
    fp=paired(out,'full_dev',ids,full_vectors[primary],{k:full_vectors[k] for k in refs})
    cp=paired(out,'cost_panel',pi,panel_vectors[primary],{k:panel_vectors[k] for k in refs},cost_vectors[primary],{k:cost_vectors[k] for k in refs})
    mixtures=[]
    for p in cfg['mixtures']['grid']:
        p=np.array(p);yy=py@p;tt=pc@p
        mixtures.append(summarize('query_independent_mixture',yy,None,ms=tt,probabilities=p.tolist()))
    csvout(out/'query_independent_mixtures_286.csv',mixtures)
    envelope=[]
    for r in panel_rows:
        mixdesc=best_mixture(py.mean(0),pc.mean(0),r['mean_ms'])
        envelope.append({'policy':r['policy'],'budget_ms':r['mean_ms'],'policy_accuracy':r['accuracy'],**mixdesc,'accuracy_above_envelope_pp':None if mixdesc['status']=='infeasible' else 100*(r['accuracy']-mixdesc['expected_accuracy']),'descriptive_dev_reference':True})
    csvout(out/'continuous_mixture_comparisons.csv',envelope)
    grid=np.unique(np.r_[np.linspace(pc.mean(0).min(),pc.mean(0).max(),301),pc.mean(0)])
    envcurve=[best_mixture(py.mean(0),pc.mean(0),t) for t in grid];csvout(out/'continuous_mixture_envelope.csv',envcurve)
    complement={}
    for pop,yy,vv,iids in [('full_dev',y,valid,ids),('cost_panel',py,pv,pi)]:
        ac_only=yy[:,3].astype(bool)&(~yy[:,:3].any(1));complement[pop]={'n':len(iids),'fixed_correct':yy.sum(0).tolist(),'fixed_accuracy':yy.mean(0).tolist(),'fixed_invalid':(~vv).sum(0).tolist(),'oracle3':int(yy[:,:3].any(1).sum()),'oracle4':int(yy.any(1).sum()),'AC_exclusive':int(ac_only.sum()),'AC_exclusive_ids':[i for i,flag in zip(iids,ac_only) if flag]}
    trainy=matrices['train'][1];complement['train']={'n':len(trainy),'fixed_correct':trainy.sum(0).tolist(),'all_wrong':int((~trainy.any(1)).sum()),'multiple_correct':int((trainy.sum(1)>1).sum()),'oracle3':int(trainy[:,:3].any(1).sum()),'oracle4':int(trainy.any(1).sum()),'AC_exclusive':int((trainy[:,3].astype(bool)&(~trainy[:,:3].any(1))).sum())}
    ohsummary=[]
    for split in cfg['data'][dataset]:
        for f,na in itertools.product(['word','semantic'],[3,4]):
            v=np.array([r['overhead_ms'] for r in overhead if r['split']==split and r['family']==f and r['n_actions']==na])
            ohsummary.append({'split':split,'family':f,'n_actions':na,'n':len(v),'mean_ms':float(v.mean()),'median_ms':float(np.median(v)),'p95_ms':float(np.percentile(v,95))})
    csvout(out/'router_overhead_summary.csv',ohsummary)
    save(out/'complementarity.json',complement);save(out/'validation_checks.json',validation)
    summary={'pair':pair,'dataset':dataset,'dev_split':devsplit,'complementarity':complement,'full_primary':next(r for r in full_rows if r['policy']==primary),'full_ablation':next(r for r in full_rows if r['policy']==abl),'panel_primary':next(r for r in panel_rows if r['policy']==primary),'panel_ablation':next(r for r in panel_rows if r['policy']==abl),'full_primary_comparisons':fp,'panel_primary_comparisons':cp,'primary_vs_dev_envelope':next(r for r in envelope if r['policy']==primary),'train_mixture':mixrec,'new_old_changes':changes,'overhead':ohsummary,'fit_info':json.loads((out/'fit_info.json').read_text()),'validation':validation}
    save(out/'summary.json',summary)
    return summary

def ac_regression():
    src=ROOT.parent/'P2_4_20260910T062023Z/reused_free_results.jsonl'
    old={r['id']:r for r in readrows(src) if r['condition']=='free' and r['config']=='acw'}
    new={r['id']:r for r in readrows(ROOT/'results/small/obqa/dev_cases.jsonl') if r['action']=='acw' and r['runtime_error'] is None}
    assert set(old)==set(new) and len(old)==742
    d=[]
    for i,n in new.items():
        o=old[i]['result'];d.append({'id':i,'old_source':old[i]['source'],'new_job_id':n['job_id'],'token_ids_changed':o['generated_token_ids']!=n['generated_token_ids'],'text_changed':o['raw_answer']!=n['raw_answer'],'answer_changed':o['scoring']['answer']!=n['scoring']['answer'],'correctness_changed':o['scoring']['correct']!=n['scoring']['correct'],'old_correct':o['scoring']['correct'],'new_correct':n['scoring']['correct'],'old_raw_text':o['raw_answer'],'new_raw_text':n['raw_answer']})
    dest=ROOT/'results/small/obqa';csvout(dest/'AC_old_P2_4_regression.csv',d)
    save(dest/'AC_old_P2_4_regression_summary.json',{'n':742,'old_source':str(src),'old_source_sha256':sha(src),**{k:sum(r[k] for r in d) for k in ['token_ids_changed','text_changed','answer_changed','correctness_changed','old_correct','new_correct']},'old_shared_times_never_used':True})

def plot(summaries):
    import matplotlib;matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False,'pdf.fonttype':42})
    fig,axes=plt.subplots(2,2,figsize=(13,10),sharex=True,sharey=True)
    colors={'word':'#2368A2','semantic':'#B16B13'}
    for ax,s in zip(axes.flat,summaries):
        out=ROOT/'results'/s['pair']/s['dataset'];rows=list(csv.DictReader((out/'cost_panel_all_policy_results.csv').open()));mix=list(csv.DictReader((out/'query_independent_mixtures_286.csv').open()));env=list(csv.DictReader((out/'continuous_mixture_envelope.csv').open()))
        ax.scatter([float(r['mean_ms']) for r in mix],[100*float(r['accuracy']) for r in mix],s=8,color='#B7B7B7',alpha=.35,label='286 fixed mixtures',zorder=1)
        ax.plot([float(r['budget_ms']) for r in env],[100*float(r['expected_accuracy']) for r in env],color='#383838',lw=1.5,label='Dev mixture envelope',zorder=2)
        for f,na in itertools.product(['word','semantic'],[3,4]):
            rr=[r for r in rows if r['family']==f and r['n_actions']==str(na)]
            ax.scatter([float(r['mean_ms']) for r in rr],[100*float(r['accuracy']) for r in rr],marker='o' if na==4 else '^',s=42,facecolors=colors[f] if na==4 else 'none',edgecolors=colors[f],linewidths=1.25,label=f'{f}, {na} actions',zorder=4)
        for r in rows:
            if r['policy'] in LABELS:
                x=float(r['mean_ms']);y=100*float(r['accuracy']);ax.scatter(x,y,marker='s',s=42,color='#222222',zorder=5);ax.annotate(r['policy'],(x,y),xytext=(5,-12 if r['policy']=='A' else 6),textcoords='offset points',weight='bold')
        p=s['panel_primary'];ax.scatter(p['mean_ms'],100*p['accuracy'],s=145,marker='*',color=colors['word'],edgecolors='white',linewidths=.7,zorder=7,label='Primary: word, lambda=0.01, 4 actions')
        tr=next((r for r in rows if r['policy']=='train_frozen_mixture'),None)
        if tr:ax.scatter(float(tr['mean_ms']),100*float(tr['accuracy']),s=65,marker='D',facecolors='white',edgecolors='#706187',linewidths=1.5,zorder=6,label='Train-frozen mixture')
        ax.set_title(f"{s['pair'].capitalize()} / {s['dataset'].upper()} | development n=128",loc='left',fontweight='bold');ax.grid(alpha=.16);ax.set_xlabel('Mean total latency (ms)');ax.set_ylabel('Accuracy (%)')
    handles,labels=axes.flat[0].get_legend_handles_labels();fig.legend(handles,labels,loc='lower center',bbox_to_anchor=(.5,.032),ncol=3,frameon=False,fontsize=9)
    fig.suptitle('P2-10: four vs three actions on fixed, newly timed development panels',fontsize=14,y=.985)
    fig.text(.5,.012,'Both axes use the same 128 questions. Router totals include measured overhead; all seven lambda points are retained.',ha='center',fontsize=9)
    fig.tight_layout(rect=[0,.15,1,.95]);fig.savefig(ROOT/'cost_panel_accuracy_latency.png',dpi=180);fig.savefig(ROOT/'cost_panel_accuracy_latency.pdf');plt.close(fig)

def exclusive_capture(summaries):
    rows=[]
    for s in summaries:
        out=ROOT/'results'/s['pair']/s['dataset'];m=np.load(out/f"{s['dev_split']}_full_matrix.npz")
        y=m['correctness'].astype(bool);exclusive=y[:,3]&~y[:,:3].any(1);ids=m['ids'].tolist()
        for family in ['word','semantic']:
            pred=np.load(out/f'dev_predictions_{family}.npz')
            for na,li in itertools.product([3,4],range(len(LAMBDAS))):
                choice=pred[f'choices{na}'][:,li];selected=choice==3;found=selected&exclusive
                rows.append({'pair':s['pair'],'dataset':s['dataset'],'population':'full_dev','n':len(ids),'policy':f'{family}_lambda{LAMBDAS[li]:g}_actions{na}','AC_selected':int(selected.sum()),'AC_selected_correct':int((selected&y[:,3]).sum()),'AC_exclusive_available':int(exclusive.sum()),'AC_exclusive_selected':int(found.sum()),'AC_exclusive_selected_ids':[i for i,flag in zip(ids,found) if flag]})
    csvout(ROOT/'AC_exclusive_router_capture.csv',rows)

def main():
    cfg=json.loads((ROOT/'frozen_config.json').read_text());prog=progress()
    assert prog['AC_complete']==11252 and prog['RTC_complete']==4608 and prog['panel_complete']==1536 and prog['dev_panel_complete']==512
    summaries=[]
    for p in ['large','small']:
        for d in ['obqa','arc']:
            cached=ROOT/'results'/p/d/'summary.json'
            # A combination can finish its CPU analysis while the GPU executes
            # the next combination; successful immutable inputs need no rerun.
            s=json.loads(cached.read_text()) if cached.exists() else analyze_combo(cfg,p,d)
            assert s['validation']['coverage'] and s['validation']['frozen_selection_replay']
            summaries.append(s)
    if not (ROOT/'results/small/obqa/AC_old_P2_4_regression_summary.json').exists():ac_regression()
    exclusive_capture(summaries)
    plot(summaries)
    csvout(ROOT/'full_dev_accuracy_table.csv',[{'pair':s['pair'],'dataset':s['dataset'],**r} for s in summaries for r in csv.DictReader((ROOT/'results'/s['pair']/s['dataset']/'full_dev_all_policy_results.csv').open())])
    csvout(ROOT/'cost_panel_accuracy_latency_table.csv',[{'pair':s['pair'],'dataset':s['dataset'],**r} for s in summaries for r in csv.DictReader((ROOT/'results'/s['pair']/s['dataset']/'cost_panel_all_policy_results.csv').open())])
    save(ROOT/'analysis_summary.json',{'utc':utc(),'progress':prog,'combinations':summaries})
    print('P2_10_ANALYSIS_COMPLETE')
if __name__=='__main__':main()
