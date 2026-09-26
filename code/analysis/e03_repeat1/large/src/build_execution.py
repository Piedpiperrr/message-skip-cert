from common import *
s=(BOUND/'src/pbs_entry.py').read_text().replace("int(r['ngpus'])==1","int(r['ngpus'])==2")
a=s.index("CFG=read(P/'frozen_config.json');paths=");b=s.index('for k,v in os.environ.items():',a)
s=s[:a]+"CFG=read(P/'frozen_config.json');paths={'helper':CFG['native']['models']['helper']['path'],'receiver':CFG['native']['models']['receiver']['path'],'fuser':CFG['native']['fuser']['path'],'dataset':str(P/'inputs'),'output':str(P),'checkpoint':str(P/'protocol'),'log':os.environ['P2_RUN'],'PBS_logs':os.environ['DATA_ROOT']+'/logs/pbs','temporary':os.environ['TMPDIR'],'python':sys.executable}\n"+s[b:]
s=s.replace("['PROTOCOL_FREEZE.json','SPLIT_FREEZE.json','IMPLEMENTATION_FREEZE.json']","['PROTOCOL_FREEZE.json','IMPLEMENTATION_FREEZE.json']")
s=s.replace("for src in csv.DictReader((P/'SOURCE_INDEX.csv').open()):assert sha(src['path'])==src['sha256'],src['path']", "for src in read(P/'SOURCE_INDEX.json'):\n assert Path(src['path']).stat().st_size==src['bytes'],src['path']\n if src['sha256']:assert sha(src['path'])==src['sha256'],src['path']")
s=s.replace("'GPU_count':1","'GPU_count':2")
(P/'src/pbs_entry.py').write_text(s)
s=(BOUND/'src/supervise.py').read_text().replace('reserve=150','reserve=180').replace('900','1500').replace('885','1485').replace("read(P/'PROBE_PROGRESS.json') if (P/'PROBE_PROGRESS.json').exists() else None","read(P/'REPLAY_PROGRESS.json') if (P/'REPLAY_PROGRESS.json').exists() else None").replace("'prefill_progress'","'replay_progress'")
s=s.replace("phases=[['run_boundaries.py'],['analyze.py'],['render.py']]","phases=[['validate_sources.py'],['execute.py'],['analyze.py'],['render.py']]").replace("args[0]!='run_boundaries.py'","args[0]!='execute.py'")
s=s.replace("**read(P/'CONTROLS_COMPLETE.json'),'evaluations':3422","'complete_action_requests':1024,'online_policy_probes':512,'paired_evaluations':512")
(P/'src/supervise.py').write_text(s)
s=(BOUND/'run_boundaries.pbs').read_text().replace('p2_ref_bounds','p2_policy_e2e').replace('select=1','select=2').replace(BOUND.name,P.name).replace('_ref_bounds','_frozen_policy_e2e')
(P/'run_e2e.pbs').write_text(s)
s=(BOUND/'src/submit.py').read_text().replace("'run_boundaries.pbs'","'run_e2e.pbs'").replace("'GPUs':1","'GPUs':2").replace("'GPU_count':1","'GPU_count':2")
a=s.index('with (ROOT/');s=s[:a]+'''with (ROOT/'P2_1_20260910T041720Z/P2_STATE.md').open('a') as f:f.write(f'\\n\\n## {utc()} — {P.name} 已提交\\n唯一 P2_FROZEN_POLICY_E2E_VALIDATION 作业 {jid}，gpu-queue/select2/00:30:00，申请上限1 GPU allocation hour；累计CPU上限1500秒含180秒准备报告预留。仅原两large模型任务128题panel的四个冻结ProbeMax policy及fixed Text/C2C真实完整重放：1024完整动作、512独立在线probe，0新拟合/校准/gold/warmup/retry。small四层fallback不执行；上一轮冻结资产只读、不重采。D仍learned control，ProbeMax普通基线，ARC test继续封存。配置SHA256 `{sha(P/"frozen_config.json")}`。尚无E2E结论；禁止第二提交。\\n')
'''
(P/'src/submit.py').write_text(s)
(P/'evidence/pbs').mkdir(exist_ok=True)
