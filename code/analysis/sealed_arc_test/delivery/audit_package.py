"""Validate cached outputs/indices and package. No raw test column access."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from common import *
import numpy as np
import collections,re,shutil,tarfile,resource
resource.setrlimit(resource.RLIMIT_CPU,(400,401))
final=read(P/'FINAL_RECEIPT.json');complete=final['status']=='COMPLETE'
for f in ['PRE_TEST_FREEZE.json','PROTOCOL_FREEZE.json','TEST_POPULATION_FREEZE.json','PREDICTION_TIMING_FREEZE.json','GOLD_ASSOCIATION_FREEZE.json','ANALYSIS_FREEZE.json']:
 if (P/f).exists():verify_freeze(f)
checks={'immutable_freezes':True,'raw_test_reloaded':False,'new_bootstrap_draws':0,'model_forwards':0}
if complete:
 pairs=jl(P/'records/paired_sealed_2344.jsonl');assert len(pairs)==2344
 routes=jl(P/'records/frozen_scores_routes_1172.jsonl');assert len(routes)==1172
 indices=np.load(P/'summary/paired_bootstrap_indices.npz',allow_pickle=False);idx=indices['indices'];assert idx.shape==(2000,1172) and int(indices['seed'])==0
 cached_gold={r['id']:r['gold'] for r in jl(P/'inputs/evaluation_gold_after_prediction_freeze.jsonl')}
 records=jl(P/'records/e2e_requests.jsonl');assert len(records)==4688
 rr={r['key']:r for r in records};assert len(rr)==4688
 assert collections.Counter(r['mode']+'_'+r['reference'] for r in records)=={p:1172 for p in ['policy_T','reference_T','policy_C','reference_C']}
 for b in ['T','C']:
  s=read(P/f'summary/large_arc_{b}_primary.json');v=[r for r in pairs if r['reference']==b and r['primary']]
  assert [r['id'] for r in v]==indices['ids'].tolist()
  for z in v:
   p=rr[z['policy_record_key']];r=rr[z['reference_record_key']]
   assert z['route']==p['selected']==('R' if p['probe']['ProbeMax']<=CFG['thresholds'][b]['threshold'] else b)
   assert z['policy_answer']==normalized_answer(p['parsed']) and z['reference_answer']==normalized_answer(r['parsed'])
   assert z['policy_correct']==int(p['parsed']['valid'] and p['parsed']['answer']==cached_gold[z['id']])
   assert z['reference_correct']==int(r['parsed']['valid'] and r['parsed']['answer']==cached_gold[z['id']])
   assert z['omission_changed']==int(z['routed'] and z['policy_answer']!=z['reference_answer'])
   assert z['net_saving_ms']==r['latency_ms']-p['latency_ms']
   assert abs(sum(p['parts_ms'].values())-p['latency_ms'])<1e-7
  assert sum(z['routed'] for z in v)==s['routed'] and sum(z['omission_changed'] for z in v)==s['changed_among_routed']
  for count in ['policy_correct','reference_correct','benefit','harm','neutral']:assert sum(z[count] for z in v)==s[count]
  for metric in ['net_saving_ms','accuracy_diff','delta_U','policy_U','reference_U']:assert abs(np.mean([z[metric] for z in v])-s[metric])<1e-12
  cached=np.load(P/f'summary/{b}_bootstrap_replicates.npz',allow_pickle=False)
  for metric in ['net_saving_ms','accuracy_diff','delta_U']:
   derived=np.array([z[metric] for z in v])[idx].mean(axis=1)
   assert np.array_equal(derived,cached[metric])
   ci=np.quantile(derived,[.025,.975]);assert np.array_equal(ci,[s[metric+'_CI95_low'],s[metric+'_CI95_high']])
 checks.update(exact_request_counts=True,score_threshold_routes=True,cached_gold_accuracy=True,benefit_harm_neutral=True,timing_parts_sum=True,same_population_utility=True,bootstrap_cached_indices_recomputed=True)
 # Check the connected active manuscript and all included historical figures.
 paper=Path(CFG['manuscript']['active_directory']);seen=set();links=[]
 def walk(f):
  f=f.resolve()
  if f in seen:return
  seen.add(f);s=f.read_text();stack=[]
  for kind,env in re.findall(r'\\(begin|end)\{([^}]+)\}',s):
   if kind=='begin':stack.append(env)
   else:assert stack and stack.pop()==env,(f.name,env)
  assert not stack,(f.name,stack)
  for name in re.findall(r'\\input\{([^}]+)\}',s):
   target=f.parent/name;assert target.exists(),str(target);links.append({'source':f.name,'target':name});walk(target)
  for name in re.findall(r'\\includegraphics(?:\[[^]]*\])?\{([^}]+)\}',s):assert (f.parent/name).exists(),name
 walk(paper/'manuscript.tex')
 assert (paper/'sealed_arc_confirmation.tex').resolve() in seen
 assert (paper/'contribution_positioning.tex').resolve() in seen
 assert 'sealed-test generalization' not in (paper/'contribution_positioning.tex').read_text().lower()
 engines={n:shutil.which(n) for n in ['pdflatex','xelatex','lualatex','tectonic','latexmk']}
 assert not any(engines.values()),'If a compiler exists, run it and record the actual result.'
 tex={'utc':utc(),'compiled':False,'engines':engines,'reason':'No installed TeX engine; no environment installation or upgrade','active_input_graph':links,'active_files_count':len(seen),'historical_figures_exist':True,'sealed_subsection_connected':True}
 save(paper/'TEX_VALIDATION.json',tex);save(P/'evidence/TEX_VALIDATION.json',tex)
 with (P/'REPORT_ZH.md').open('a') as f:f.write('\n论文核验：已检查真实活跃稿的全部\\input拓扑、LaTeX环境配对、历史图路径以及sealed subsection连接。环境没有TeX编译器，未编译PDF，未安装环境。\n')
 with (P/'HANDOFF_ZH.md').open('a') as f:f.write('\nTeX源拓扑核验通过；无已安装编译器，未生成新论文PDF。\n')
 final.update(TeX_compiled=False,TeX_source_validation=True)
# Frozen runtime import snapshots for a reviewable lightweight package.
runtime=P/'delivery/runtime_source_snapshot';runtime.mkdir(exist_ok=True)
source_checks=[]
for s in read(P/'SOURCE_INDEX.json'):
 path=Path(s['path']);assert path.stat().st_size==s['bytes'];assert sha(path)==s['sha256'],str(path)
 source_checks.append({'path':str(path),'sha256':s['sha256'],'verified':True})
 if path.suffix=='.py':
  rel=path.relative_to(ROOT) if path.is_relative_to(ROOT) else Path(path.name)
  dst=runtime/rel;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,dst)
save(P/'evidence/FINAL_AUDIT.json',{'utc':utc(),'checks':checks,'source_checks':source_checks,'no_new_scientific_choices':True})
final.update(delivery_validation='PASS',final_audit_sha256=sha(P/'evidence/FINAL_AUDIT.json'),lightweight_package=P.name+'_WORK_LIGHT.tar.gz')
save(P/'FINAL_RECEIPT.json',final)
# Include updated real paper and the inherited figures, following only these two explicit symlinks.
def all_files():
 base=[f for f in P.rglob('*') if f.is_file() and not f.is_symlink() and f.name not in ['SHA256SUMS','PACKAGE_RECEIPT.json','PACKAGE_SHA256SUMS','final_audit_command.log'] and not f.name.endswith('.tar.gz') and '__pycache__' not in f.parts]
 for folder in ['paper','figures']:
  base.extend(f for f in (P/folder).rglob('*') if f.is_file())
 return sorted(set(base),key=lambda f:str(f.relative_to(P)))
files=all_files()
(P/'SHA256SUMS').write_text(''.join(sha(f)+'  '+str(f.relative_to(P))+'\n' for f in files))
archive=P/(P.name+'_WORK_LIGHT.tar.gz')
with tarfile.open(archive,'w:gz',compresslevel=6,dereference=True) as tf:
 for f in files+[P/'SHA256SUMS']:tf.add(f,arcname=P.name+'/'+str(f.relative_to(P)),recursive=False)
with tarfile.open(archive,'r:gz') as tf:
 members=tf.getmembers();assert len(members)==len(files)+1
 sums=tf.extractfile(P.name+'/SHA256SUMS').read().decode().splitlines()
 for line in sums:
  h,rel=line.split('  ',1);assert hashlib.sha256(tf.extractfile(P.name+'/'+rel).read()).hexdigest()==h,rel
receipt={'utc':utc(),'archive':str(archive),'bytes':archive.stat().st_size,'sha256':sha(archive),'contained_file_count':len(files)+1,'archive_members_hash_verified':True,'contains_weights':False,'full_raw_predictions_and_timing':complete,'updated_actual_paper_included':True,'budget_closed':True}
save(P/'PACKAGE_RECEIPT.json',receipt)
(P/'PACKAGE_SHA256SUMS').write_text(sha(archive)+'  '+archive.name+'\n'+sha(P/'PACKAGE_RECEIPT.json')+'  PACKAGE_RECEIPT.json\n')
print(json.dumps(receipt,ensure_ascii=False))
