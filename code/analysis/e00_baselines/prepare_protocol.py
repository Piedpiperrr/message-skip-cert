"""Lightweight preparation only: no LR, features, original-answer parsing, or dev evaluation."""
import os,json,csv,hashlib,random,collections,datetime,resource,socket
from pathlib import Path
O=Path(__file__).resolve().parent
P=Path('$DATA_DIR')
P10=P/'P2_10_20260911T122423Z';V2=P/'P2_SCORING_V2_20260912T191445Z'
START=resource.getrusage(resource.RUSAGE_SELF)
resource.setrlimit(resource.RLIMIT_AS,(512*1024*1024,512*1024*1024));resource.setrlimit(resource.RLIMIT_CPU,(60,61))
os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''):h.update(b)
    return h.hexdigest()
def save(n,x):
    p=O/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def table(n,rows):
    rows=list(rows)
    with (O/n).open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def jl(p):
    with Path(p).open() as f:
        for line in f:
            if line.strip():yield json.loads(line)
def main():
    if (O/'PROTOCOL_FREEZE.json').exists():raise SystemExit('ALREADY_FROZEN; reuse existing folds and configuration')
    cfg=json.loads((P10/'frozen_config.json').read_text());lm=json.loads((V2/'labels/LABEL_MANIFEST.json').read_text())
    source=[]
    def register(path,role,expected=None):
        path=Path(path);s=sha(path)
        if expected:assert s==expected
        r=dict(path=str(path),role=role,sha256=s,size_bytes=path.stat().st_size);source.append(r);return r
    register(P10/'frozen_config.json','P2-10 frozen feature/LR/cost provenance')
    register(V2/'RULE_FREEZE_V2.json','formal V2 scoring; do not rerun parser/tests')
    register(V2/'refit_inventory.csv','8 C heads targeted, 24 R/T/A heads reusable only outside OOF')
    for row in lm:register(row['path'],'V2 '+row['population']+' '+row['role']+' labels',row['sha256'])
    train={}
    for r in jl(V2/'labels/full_train_P2_SCORING_V2.jsonl'):train[r['pair'],r['dataset'],r['id']]=r
    foldrows=[];groups=[];counts=[];panelcounts=[];dataset_inputs={};assets=[]
    dupfile=P/'P2_8_20260911T032044Z/duplicates.csv';register(dupfile,'registered duplicate groups; no test data read')
    duplicate_rows=list(csv.DictReader(dupfile.open()))
    for ds in ['obqa','arc']:
        rows=list(jl(cfg['data'][ds]['train']['path']));ids=[r['id'] for r in rows];assert len(ids)==len(set(ids))
        register(cfg['data'][ds]['train']['path'],'train query source (only question/choices used)',cfg['data'][ds]['train']['sha256'])
        parent={i:i for i in ids}
        def root(i):
            while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
            return i
        def union(members):
            roots=sorted({root(i) for i in members});base=roots[0]
            for i in roots:parent[i]=base
        # Exact whitespace-normalized query duplicates are grouped without labels/outcomes.
        querygroups=collections.defaultdict(list)
        for r in rows:
            query='\n'.join(['Question: '+r['question_stem'],'Choices:']+[a+': '+b for a,b in zip(r['choice_labels'],r['choice_text'])])
            signature=' '.join(query.split());querygroups[signature].append(r['id'])
        for members in querygroups.values():union(members)
        for r in duplicate_rows:
            if r['scope']==ds+'_within_train':union([x.split(':',1)[1] for x in r['members'].split(';')])
        members=collections.defaultdict(list)
        for i in ids:members[root(i)].append(i)
        entries=[]
        for m in members.values():
            m=sorted(m);gid=ds+'_'+hashlib.sha256((ds+'|'+'|'.join(m)).encode()).hexdigest()[:20]
            entries.append((gid,m))
        entries.sort();rng=random.Random(0);rng.shuffle(entries);entries.sort(key=lambda x:-len(x[1]))
        sizes=[0]*5;assignment={}
        for gid,m in entries:
            k=min(range(5),key=lambda k:(sizes[k],k));sizes[k]+=len(m)
            for i in m:assignment[i]=(gid,k)
            groups.append(dict(dataset=ds,group_id=gid,fold=k,n=len(m),members='|'.join(m)))
        assert max(sizes)-min(sizes)<=2
        if ds=='arc':assert assignment['MEA_2011_8_8']==assignment['MEA_2012_5_8']
        for row_index,i in enumerate(ids):
            gid,k=assignment[i];foldrows.append(dict(dataset=ds,id=i,source_row=row_index,group_id=gid,fold=k))
        dataset_inputs[ds]={'query_train':cfg['data'][ds]['train']['path'],'n':len(ids),'group_n':len(entries),'fold_sizes':sizes,
            'semantic_train':str(P10/'data'/(ds+'_train_semantic.npy')),'semantic_row_ids_reference':str(P10/'results/large'/ds/'features/row_ids.json')}
        register(P10/'data'/(ds+'_train_semantic.npy'),'fixed per-query semantic train cache, no new forward')
        dv='dev' if ds=='obqa' else 'validation'
        register(P10/'data'/(ds+'_'+dv+'_semantic.npy'),'baseline-only exposed dev semantic cache; forbidden to FFR OOF')
        for pair in ['large','small']:
            for k in range(5):
                for role,take in [('fit',lambda f:f!=k),('heldout',lambda f:f==k)]:
                    use=[train[pair,ds,i] for i in ids if take(assignment[i][1])]
                    for target in ['y_R','y_T','y_C','y_A','f_T','f_C','f_A']:
                        pos=sum(r[target] for r in use);counts.append(dict(pair=pair,dataset=ds,fold=k,role=role,target=target,n=len(use),positive=pos,negative=len(use)-pos,
                            single_class=len({r[target] for r in use})<2))
                panel_ids=cfg['cost_panel'][ds]['train']['ids'];fitpanel=[i for i in panel_ids if assignment[i][1]!=k]
                assert fitpanel;panelcounts.append(dict(pair=pair,dataset=ds,fold=k,fit_panel_n=len(fitpanel),heldout_panel_n=len(panel_ids)-len(fitpanel),
                    fit_panel_ids='|'.join(fitpanel),heldout_excluded=True))
            d=P10/'results'/pair/ds
            for name,role in [('features/row_ids.json','feature row-ID provenance'),('features/word_train.npz','full-train frozen TF-IDF for C refit only'),
                ('features/word_'+dv+'.npz','old baseline dev TF-IDF; no OOF use'),('train_cost_panel_matrix.npz','original train panel action costs'),
                (dv+'_cost_panel_matrix.npz','baseline-only old dev panel action costs'),('train_mixture_receipt.json','historical probability/B_train reference'),
                ('dev_predictions_word.npz','old baseline dev choices/probabilities'),('dev_predictions_semantic.npz','old baseline dev choices/probabilities')]:register(d/name,role)
            for family in ['word','semantic']:
                r=register(d/'models'/(family+'.joblib'),'old bundle; only C replaced, R/T/A and costs unchanged')
                assets.append(dict(pair=pair,dataset=ds,family=family,source_bundle=r,output_bundle=f'baseline/{pair}/{ds}/{family}_V2.joblib',
                    output_C_head=f'baseline/{pair}/{ds}/{family}_C_V2.joblib',old_component_order=['R','T','C','A']))
    table('folds/group_folds.csv',foldrows);table('folds/groups.csv',groups);table('folds/target_counts.csv',counts);table('folds/cost_panel_fit_members.csv',panelcounts)
    plan={
      'stage':O.name,'scoring_version':'P2_SCORING_V2','primary_input_authority':'current user prompt, overrides P2-11 draft',
      'combinations':[['large','obqa'],['large','arc'],['small','obqa'],['small','arc']],
      'features':['word','semantic'],'feature_input_fields':['question_stem','choice_labels','choice_text'],
      'LR':cfg['router']['logistic'],'tfidf':cfg['router']['tfidf'],'new_standardization':None,
      'single_class':'constant exact training class probability; logged; counts as a completed head but no LR fit',
      'probability_clipping':'log loss only, epsilon=1e-15; no clipping for choices or AUC/AP',
      'lambdas':[0,.01,.03,.1,.3,1,3],'tie_order':['R','T','C','A'],'n_actions':[3,4],
      'folds':{'n':5,'seed':0,'assignment':'group IDs sorted, Python random.Random(0) shuffle, stable largest-group-first, assign smallest fold, tie lowest fold index',
        'group_definition':'registered groups plus exact whitespace-normalized question + ordered label/text duplicates; no gold/answer/score used',
        'shared_between':['model_pairs','feature_families','methods'],'label_stratification':False,'posthoc_movement':False,
        'fold_file':'folds/group_folds.csv','fold_file_sha256':sha(O/'folds/group_folds.csv')},
      'baseline':{'fit':'8 full-train C correctness heads only','reuse':'24 R/T/A correctness heads, all original cost Ridge, c_ref, frozen full-train features',
        'dev':'one fixed post-refit evaluation; original word lambda .01 remains focus; all lambdas appended',
        'panel':'original panel action-cost replay only, no new total router latency',
        'old_mixture':'historical probabilities/B_train retained; new budget/overhead matched mixture pending separate freeze'},
      'OOF':{'methods':['FFR_E0','IndepLR','FFR_constant_flip_rate','FFR_true_flip_DIAGNOSTIC'],
        'FFR_heads':['f_T','f_C','f_A'],'IndepLR_heads':['y_R','y_T','y_C','y_A'],
        'FFR_delta':'(fit_gain-fit_harm)/(fit_flips+2); zero gain flips included; zero flips -> zero; shrinkage to zero, not standard binary Beta posterior',
        'FFR_gain':'[0,m_T*delta_T,m_C*delta_C,m_A*delta_A]',
        'IndepLR_gain':'[0,p_T-p_R,p_C-p_R,p_A-p_R]',
        'cost_proxy':'mean original per-action train panel cost only among training-fold questions; c_ref is same rows R mean',
        'score':'gain - lambda*mean_action_cost/c_ref',
        'query_independent':'choose max training-fold mean correctness minus same lambda cost proxy; same tie order; also report all fixed actions',
        'TFIDF':'fit vocabulary/IDF only on training fold; same transformed matrices for both pairs and methods',
        'semantic':'existing frozen query-independent per-item cache reused by IDs, no new scaling',
        'dev_usage':'NONE; train OOF only','old_full_train_heads_in_OOF':False,'C_or_lambda_search':False,'G1_G2_gates':False},
      'statistics':{'flip':['positive_rate','ROC_AUC','AP','log_loss'],'single_class_evaluation':'ROC_AUC/AP NA; log loss defined with labels [0,1]',
        'flip_scopes':['all','both_R_and_action_valid_diagnostic_only'],
        'aggregation':['each fold','pooled one-prediction-per-question OOF'],'uncertainty':'exploratory point estimates; no best-point bootstrap or cross-combination pooled significance',
        'decision':['accuracy','proxy_utility','action_proportions','gain_harm_vs_R','FFR_minus_IndepLR_paired','true_flip_minus_learned'],
        'overhead':'unmeasured; for lambda>0 per-fold admissible added ms=utility_advantage*c_ref/lambda; pooled common-ms threshold=pooled_utility_advantage/(lambda*mean(1/c_ref_i)); negative means no nonnegative headroom',
        'lambda_zero':'accuracy only; overhead headroom NA'},
      'budget':{'CPU_seconds_total':3600,'RSS_GiB':4,'threads':1,'nice':10,'planned_LR':288,'max_LR_with_targeted_retries':320,
        'GPU':0,'PBS':0,'LLM_forward':0,'new_semantic_features':0,'ARC_test':0,'installation':0},
      'resume':'save each successful head and each OOF fold, skip by frozen-config/input hash; no successful fit repeated',
      'execution_gate':'must resolve current login-node eligibility before any LR fit; no automatic PBS or other node',
      'dataset_inputs':dataset_inputs,'baseline_assets':assets,
      'output_plan':['baseline/*/*/*_C_V2.joblib','baseline/*/*/*_V2.joblib','baseline_dev_predictions.npz per combination/family',
        'baseline_update_summary.csv','baseline_changed_selections.csv','oof/<dataset>/<family>/fold<k>/<pair>/*head.joblib',
        'oof_predictions.csv','flip_metrics.csv','decision_metrics.csv','paired_method_differences.csv','overhead_headroom.csv',
        'fit_receipts.jsonl','source_manifest.json','MODEL_INDEX.tsv','P2_V2_BASELINES_FFR_E0_REPORT_ZH.md','paper/*.tex','HANDOFF_ZH.md','light bundle']}
    save('frozen_config.json',plan);save('evidence/source_manifest.json',source)
    freeze={'stage':O.name,'frozen_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'config_sha256':sha(O/'frozen_config.json'),'folds_sha256':sha(O/'folds/group_folds.csv'),'groups_sha256':sha(O/'folds/groups.csv'),
        'target_counts_sha256':sha(O/'folds/target_counts.csv'),'source_manifest_sha256':sha(O/'evidence/source_manifest.json'),
        'preparation_code_sha256':sha(__file__),'new_training_or_refitting_started':False,'new_development_evaluation_started':False,
        'prior_exposure':'V2 and old baseline development results already exposed; OOF outcomes not computed',
        'node_training_eligible':False,'not_a_scientific_result':True}
    save('PROTOCOL_FREEZE.json',freeze)
    save('PROGRESS.json',{'status':'PROTOCOL_FROZEN_EXECUTION_PENDING_NODE_CLEARANCE','planned_heads':288,'completed_heads':0,'LR_fit_attempts':0,
        'folds_completed':0,'baseline_C_heads_completed':0,'node':socket.gethostname(),'PBS_submissions':0,'GPU':0,
        'next':'Resolve node eligibility, then resume this frozen stage; do not regenerate folds or scoring.'})
    ru=resource.getrusage(resource.RUSAGE_SELF)
    save('evidence/preparation_resources.json',{'cpu_seconds':ru.ru_utime+ru.ru_stime,'max_RSS_KiB':ru.ru_maxrss,'threads':1,'nice':os.getpriority(os.PRIO_PROCESS,0),'LR_fit_attempts':0})
    print(json.dumps({'status':'PROTOCOL_FROZEN','fold_sizes':{ds:d['fold_sizes'] for ds,d in dataset_inputs.items()},'duplicate_groups':[r for r in groups if r['n']>1],
        'target_single_class_training_folds':[r for r in counts if r['single_class'] and r['role']=='fit'],'sources':len(source),'freeze':freeze},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
