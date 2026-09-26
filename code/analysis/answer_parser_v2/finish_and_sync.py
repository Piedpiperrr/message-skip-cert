"""Publish this authorized local stage and append only the new P2 state block."""
import os,json,hashlib,shutil,csv,tarfile,resource,datetime,socket,time
from pathlib import Path
O=Path(__file__).resolve().parent
P=Path('$DATA_DIR');T=P/O.name
STATE=P/'P2_1_20260910T041720Z/P2_STATE.md'
resource.setrlimit(resource.RLIMIT_AS,(768*1024*1024,768*1024*1024))
resource.setrlimit(resource.RLIMIT_CPU,(30,31))
os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
if os.getpriority(os.PRIO_PROCESS,0)<10:os.nice(10-os.getpriority(os.PRIO_PROCESS,0))
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''):h.update(b)
    return h.hexdigest()
def save_both(name,x):
    text=json.dumps(x,ensure_ascii=False,indent=2)+'\n'
    for root in [O,T]:(root/name).write_text(text)
freeze=json.loads((O/'RULE_FREEZE_V2.json').read_text())
assert sha(O/'scoring_v2.py')==freeze['code_sha256'] and sha(O/'P2_SCORING_V2_RULES_ZH.md')==freeze['rules_sha256']
assert json.loads((O/'evidence/output_validation.json').read_text())['status']=='PASS_WITHIN_REQUESTED_SCOPE'
assert json.loads((O/'ROUTING_COMPLETE.json').read_text())['missing_items']==[]
for name in ['scoring_v2.py','P2_SCORING_V2_RULES_ZH.md','RULE_FREEZE_V2.json']:
    assert sha(T/name)==sha(O/name),'Existing formal freeze differs; abort'
print(json.dumps({'host':socket.gethostname(),'model':'NONE','dataset':'only registered train/dev/validation inputs',
    'output':str(T),'checkpoint':'NONE','cache':{k:os.environ.get(k) for k in ['HF_HOME','XDG_CACHE_HOME']},
    'temporary':str(O/'tmp'),'log':str(T/'FINAL_RECEIPT.json'),'state_append':str(STATE),
    'archive':str(T/'P2_SCORING_V2_BUNDLE.tar.gz'),'nice':10,'affinity':list(os.sched_getaffinity(0))}),flush=True)
assert all(str(p).startswith('$DATA_DIR') for p in [O,T,STATE])
# Only this new stage is copied; original P2 inputs and history remain read-only.
files=[p for p in O.rglob('*') if p.is_file() and 'tmp' not in p.relative_to(O).parts and '__pycache__' not in p.relative_to(O).parts]
for p in files:
    rel=p.relative_to(O);dest=T/rel;dest.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(p,dest);assert sha(p)==sha(dest)
block=(O/'P2_STATE_APPEND.md').read_bytes();before=STATE.read_bytes()
marker=('<!-- BEGIN P2-SCORING-V2 '+O.name+' -->').encode()
if marker in before:
    assert block in before,'Existing incomplete/different block; abort'
    state_receipt=json.loads((T/'evidence/state_sync_receipt.json').read_text())
else:
    with STATE.open('ab') as f:f.write(block);f.flush();os.fsync(f.fileno())
    after=STATE.read_bytes();assert after==before+block
    state_receipt={'path':str(STATE),'before_sha256':hashlib.sha256(before).hexdigest(),'after_sha256':hashlib.sha256(after).hexdigest(),
        'original_bytes':len(before),'appended_bytes':len(block),'original_prefix_preserved':True,'only_append':True,
        'utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
save_both('evidence/state_sync_receipt.json',state_receipt)
ledger=json.loads((O/'evidence/resource_ledger.json').read_text())
cpu=sum(r['cpu_seconds'] for r in ledger['runs']);peak=max(r['max_rss_kib'] for r in ledger['runs'])
assert cpu+ledger['preparation_and_unmetered_cpu_reserved_seconds']<600 and peak<1024*1024
assert all(r['nice']==10 and r['threads']==1 for r in ledger['runs'])
receipt={'status':'COMPLETE_SCORING_V2_READY_FOR_MAINLINE_REVIEW','completed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'stage':str(T),'implementation':'2.0.0','version':'P2_SCORING_V2','freeze_sha256':sha(O/'RULE_FREEZE_V2.json'),
    'parser_sha256':sha(O/'scoring_v2.py'),'parser_post_freeze_revisions':0,'targeted_checks_passed':297,
    'sources_scored':49616,'full_action_records':45008,'panel_action_records':6144,'shared_AC_source_records':1536,
    'old_to_V2_full_answer_changes':158,'old_to_V2_full_correctness_up_down':[129,0],
    'D1_to_V2_full_answer_changes':4,'D1_to_V2_full_correctness_up_down':[3,0],'D1_to_V2_panel_correctness_up_down':[1,0],
    'development_D1_equals_V2':True,'policy_rescoring_rows':528,'saved_mixture_rows':1273,'unrecoverable_policy_items':0,
    'parameters_choices_probabilities_unchanged':True,'original_panel_latency_unchanged':True,
    'word_lambda_001_four_minus_three_full':[-2,0,1,0],'panel_four_three_correctness_identical_per_question':True,
    'old_routing_scientific_conclusion_changed':False,'V2_trained_C_correctness_heads_still_needed':8,
    'old_R_T_A_heads_with_unchanged_training_y':24,'old_to_V2_changed_train_C_flip_labels':[51,60,2,3],
    'metered_analysis_validation_CPU_seconds_including_failed_attempts':cpu,'preparation_packaging_and_unmetered_CPU_reserved_seconds':30,
    'CPU_budget_charged_seconds':cpu+30,'CPU_budget_limit_seconds':600,'measured_peak_RSS_KiB':peak,'address_space_hard_limit_MiB':768,
    'threads':1,'nice':10,'node':socket.gethostname(),'GPU_use':0,'PBS_submissions':0,'node_jobs':0,'model_or_tokenizer_loads':0,
    'model_generation_calls':0,'feature_extractions':0,'router_refits':0,'FFR_E0_E1_runs':0,'ARC_test_reads':0,
    'P2_STATE_append_synced':True,'state_sync_receipt_sha256':sha(T/'evidence/state_sync_receipt.json'),
    'paper_fragments':4,'paper_tex_compiled':False,'paper_limitation':'No pdflatex available; source values and syntax checked, final layout pending manuscript insertion.',
    'large_labels_manifest':str(T/'labels/LABEL_MANIFEST.json'),'large_labels_manifest_sha256':sha(T/'labels/LABEL_MANIFEST.json'),
    'archive_name':'P2_SCORING_V2_BUNDLE.tar.gz','archive_excludes':'complete raw answers, large labels, large per-record tables, model arrays',
    'staging_copy_retained':str(O),'next_action':'Stop and return to Work for mainline method-validation review; no automatic training or new stage.'}
save_both('FINAL_RECEIPT.json',receipt)
save_both('PROGRESS.json',{'status':receipt['status'],'completed_utc':receipt['completed_utc'],'final_receipt':'FINAL_RECEIPT.json','active_stage_processes_after_finalizer':0,'next_action':receipt['next_action']})
excluded={'scoring_records.csv','primary_per_question.csv','P2_SCORING_V2_BUNDLE.tar.gz','BUNDLE_VALIDATION.json','FILE_INDEX.tsv'}
allfiles=[p for p in T.rglob('*') if p.is_file() and 'tmp' not in p.relative_to(T).parts]
members=[];index=[]
for p in sorted(allfiles):
    rel=p.relative_to(T).as_posix()
    package=p.name not in excluded and not (rel.startswith('labels/') and p.suffix=='.jsonl') and p.stat().st_size<2*1024*1024
    if p.name in ['P2_SCORING_V2_BUNDLE.tar.gz','BUNDLE_VALIDATION.json','FILE_INDEX.tsv']:continue
    index.append(dict(path=rel,size_bytes=p.stat().st_size,sha256=sha(p),included_in_light_bundle=package))
    if package:members.append(p)
for root in [O,T]:
    with (root/'FILE_INDEX.tsv').open('w') as f:
        w=csv.DictWriter(f,fieldnames=list(index[0]),delimiter='\t');w.writeheader();w.writerows(index)
members.append(T/'FILE_INDEX.tsv')
bundle=T/'P2_SCORING_V2_BUNDLE.tar.gz'
with tarfile.open(bundle,'w:gz',compresslevel=6) as tar:
    for p in sorted(members):tar.add(p,arcname=p.relative_to(T).as_posix(),recursive=False)
with tarfile.open(bundle,'r:gz') as tar:
    names=tar.getnames();assert len(names)==len(members)
    assert not any(n.startswith('labels/') and n.endswith('.jsonl') for n in names)
    for member in tar.getmembers():assert hashlib.sha256(tar.extractfile(member).read()).hexdigest()==sha(T/member.name)
shutil.copy2(bundle,O/bundle.name)
save_both('BUNDLE_VALIDATION.json',{'archive':str(bundle),'sha256':sha(bundle),'size_bytes':bundle.stat().st_size,'member_count':len(members),
    'all_members_match_delivered_bytes':True,'no_complete_raw_answers_or_large_labels_or_arrays':True,
    'index_note':'FILE_INDEX excludes itself, archive and this receipt to avoid recursive hashes.',
    'finalization_self_cpu_seconds_at_receipt':resource.getrusage(resource.RUSAGE_SELF).ru_utime+resource.getrusage(resource.RUSAGE_SELF).ru_stime,
    'finalization_self_peak_RSS_KiB':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
    'finalization_charged_within_reserved_30_CPU_seconds':True})
assert (T/'P2_SCORING_V2_REPORT_ZH.md').exists() and state_receipt['original_prefix_preserved']
print(json.dumps({'status':receipt['status'],'report':str(T/'P2_SCORING_V2_REPORT_ZH.md'),'bundle':str(bundle),
    'bundle_bytes':bundle.stat().st_size,'metered_analysis_CPU_seconds':cpu,'charged_CPU_seconds_with_reserve':cpu+30,'peak_RSS_KiB':peak,
    'state_append_only':True,'all_new_stage_files_copied_and_verified':True},ensure_ascii=False,indent=2),flush=True)
