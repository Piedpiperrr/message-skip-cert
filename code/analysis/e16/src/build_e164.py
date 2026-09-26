"""E16-4: build the Llama-3.1-8B Text-only copy of the E3 ClusterA large-stage replay (login node, CPU, no model loads, no gold).
Source: P2_R1_E3POL_REPEAT1_20260919T075315Z/large (the E3 second-configuration replay). Copies code and configs only (as build_e3pol.py), then:
  data/config (not code): receiver = Llama-3.1-8B-Instruct @ 0e9e39f2 (path, chat-template SHA, config, post-cleanup generation config from the
    X3 env record); order.paths = policy_T, reference_T; protocol/label_token_sets.json and prefix_ids.json = the X3 receiver's (X3 env);
    protocol/large_{obqa,arc}_T_deployment.json = X3 frozen q/tau; inputs/large_{obqa,arc}_T_expected_routes.jsonl = X3 dev u, probe ids and
    route (u <= tau -> R) for the 128 panel ids; protocol/chat_template.jinja = Llama's (record). C deployments/expected routes stay as copied
    (read by execute.py/validate_sources.py loops, never used by a Text-only order).
  code (exact-string edits asserted once; diff in diffs/e164_replay_code.diff):
    native_adapter.py: R path and probe tokenize the rendered chat template with add_special_tokens=False (no second BOS); C2C bundles and
      fuser traces are not built (Text-only policy);
    execute.py: arm rotation ordinal%4 -> ordinal%len(paths) (approved as D7); final count assert for 2 arms;
    supervise.py: EXECUTION_COMPLETE counts for 2 arms (record only);
    run_e2e.pbs: stage path, model line.
  Freeze manifests (IMPLEMENTATION_FREEZE, PROTOCOL_FREEZE) recomputed over the copy. -> replay_llama/, notes/E164_BUILD.json"""
import sys
sys.dont_write_bytecode = True
import shutil, glob, subprocess
from xfam_common import *
SRC = ROOT / 'P2_R1_E3POL_REPEAT1_20260919T075315Z/large'; D = X / 'replay_llama'; assert not D.exists()
D.mkdir()
for d in ['src', 'inputs', 'protocol']: shutil.copytree(SRC / d, D / d, ignore=shutil.ignore_patterns('__pycache__'))
for f in ['frozen_config.json', 'SOURCE_INDEX.json', 'PROTOCOL_FREEZE.json', 'IMPLEMENTATION_FREEZE.json', 'PANEL_VALIDATION_FREEZE.json', 'run_e2e.pbs', 'evidence/panel_source_checks.json']:
    (D / f).parent.mkdir(parents=True, exist_ok=True); shutil.copy2(SRC / f, D / f)
(D / 'evidence/pbs').mkdir(parents=True, exist_ok=True); (D / 'records').mkdir()


def edit(path, old, new):
    s = path.read_text(); assert s.count(old) == 1, (str(path), old[:80], s.count(old)); path.write_text(s.replace(old, new))


# ---- data / config from X3 (receiver Llama-3.1-8B)
env = read(X3 / 'results/runs/chain_00.env.json'); spec = RECEIVERS['llama31_8b']
st = {(r['dataset'], r['id']): r for f in sorted(glob.glob(str(X3 / 'results/runs/chain_*.jsonl'))) for r in jl(f)}
xt = {r['setting']: r for r in __import__('csv').DictReader(open(X3 / 'results/analysis/dev_table_pre_gold.csv'))}
assert sha(X3 / 'results/analysis/dev_table_pre_gold.csv') == read(X3 / 'results/analysis/CERT_HASHES.json')['files']['dev_table_pre_gold.csv']
c = read(D / 'frozen_config.json')
tok_cfg = read(pathlib.Path(spec['path']) / 'config.json')
c['native']['models']['receiver'] = dict(repo_id=spec['repo'], revision=spec['revision'], path=spec['path'], chat_template_sha256=env['chat_template_sha256'], config=tok_cfg)
c['native']['receiver_generation_config'] = env['generation_config']
c['order']['paths'] = ['policy_T', 'reference_T']
c['order']['rotation'] = 'left by canonical panel ordinal modulo len(paths) (= 2); original panel order (E16-4, D7)'
c['E16_4'] = 'Llama-3.1-8B receiver, Text-only policy; see P2_R7_E16 DEVIATIONS D7/D8'
save(D / 'frozen_config.json', c)
save(D / 'protocol/label_token_sets.json', env['label_token_sets'])
save(D / 'protocol/prefix_ids.json', dict(literal=PREFIX, ids=env['prefix_ids'], encoding='add_special_tokens=False', chat_template_sha256=env['chat_template_sha256']))
from transformers import AutoTokenizer
(D / 'protocol/chat_template.jinja').write_text(AutoTokenizer.from_pretrained(spec['path'], local_files_only=True).chat_template)
routes = {}
for ds, name in [('obqa', 'X3 obqa/Text'), ('arc', 'X3 arc/Text')]:
    q, tau = float(xt[name]['deployed_q']), float(xt[name]['threshold'])
    dep = read(D / f'protocol/large_{ds}_T_deployment.json'); dep.update(q=q, threshold=tau, accepted_q=[float(x) for x in xt[name]['accepted_q'].split(';')],
                                                                        source='P2_R6_X3 dev_table_pre_gold.csv (Llama-3.1-8B receiver)')
    for k in list(dep):
        if k not in ('q', 'threshold', 'mode', 'accepted_q', 'source'): dep.pop(k)
    save(D / f'protocol/large_{ds}_T_deployment.json', dep)
    ids = read(D / f'inputs/{ds}_panel_ids.json'); rows = []
    for i in ids:
        s = st[(ds, i)]; assert s['split'] == 'dev' and s['runtime_error'] is None
        rows.append(dict(pair='llama31_8b', dataset=ds, reference='T', id=i, route='R' if s['P']['ProbeMax'] <= tau else 'T', ProbeMax=s['P']['ProbeMax'],
                         probe_ids_sha256=s['P']['probe_ids_sha256'], identity='X3 stored dev record'))
    with open(D / f'inputs/large_{ds}_T_expected_routes.jsonl', 'w') as f:
        for r in rows: f.write(json.dumps(r) + '\n')
    routes[ds] = dict(q=q, tau=tau, n_panel=len(rows), routed_R=sum(r['route'] == 'R' for r in rows))
# ---- code edits
na = D / 'src/native_adapter.py'
edit(na, "sys.path.remove(CFG['native_root'])\n",
     "sys.path.remove(CFG['native_root'])\n"
     "import protocol_min as _pm  # E16-4: R path tokenizes the rendered chat template with add_special_tokens=False (no second BOS)\n"
     "def _rpt(tokenizer,example,device):\n"
     " prompt=_pm.format_openbook(example,use_template=True);rendered=tokenizer.apply_chat_template([{'role':'user','content':prompt}],tokenize=False,add_generation_prompt=True,enable_thinking=False)\n"
     " t=tokenizer(rendered,return_tensors='pt',add_special_tokens=False);return prompt,rendered,{k:v.to(device) for k,v in t.items()}\n"
     "native.receiver_prompt_tensors=_rpt\n")
edit(na, "  self.runner.ch=lm.C2CSharerHelperBundle(self.runner.helper,self.runner.receiver_tok)\n"
         "  assert self.runner.ch.tokenizer is self.runner.receiver_tok\n"
         "  t=time.perf_counter();self.runner.cr=lm.C2CReceiverSideFuserBundle(self.runner.receiver,self.runner.receiver_tok)\n"
         "  for f in self.runner.cr.projectors:f.eval().requires_grad_(False)\n"
         "  sync();self.load_times['fusers']=time.perf_counter()-t\n",
     "  # E16-4: Text-only policy; C2C bundles and fuser are not built\n")
edit(na, "  for j,f in enumerate(self.runner.cr.projectors):self._install_trace(f,'fuser_'+str(j),self.runner.receiver.device)\n", "")
edit(na, "  base=tok(rendered,return_tensors='pt');suffix=", "  base=tok(rendered,return_tensors='pt',add_special_tokens=False);suffix=")
ex = D / 'src/execute.py'
edit(ex, "paths=CFG['order']['paths'];k=ordinal%4;order=paths[k:]+paths[:k]", "paths=CFG['order']['paths'];k=ordinal%len(paths);order=paths[k:]+paths[:k]  # E16-4 D7: balanced rotation for 2 arms")
edit(ex, "assert attempt==1024 and probes==512 and len(set(success))==1024", "assert attempt==512 and probes==256 and len(set(success))==512  # E16-4: 2 arms")
edit(ex, "freeze('REPLAY_COMPLETE.json',[P/'records/e2e_requests.jsonl',P/'records/attempts.jsonl'],job_id=os.environ['PBS_JOBID'],action_attempts=attempt,online_probe_attempts=probes,successful=1024,",
     "freeze('REPLAY_COMPLETE.json',[P/'records/e2e_requests.jsonl',P/'records/attempts.jsonl'],job_id=os.environ['PBS_JOBID'],action_attempts=attempt,online_probe_attempts=probes,successful=len(set(success)),")
sv = D / 'src/supervise.py'
edit(sv, "'complete_action_requests':1024,'online_policy_probes':512,'paired_evaluations':512,", "'complete_action_requests':512,'online_policy_probes':256,'paired_evaluations':256,")
rp = D / 'run_e2e.pbs'
edit(rp, f'export P2_STAGE="{SRC}"', f'export P2_STAGE="{D}"')
edit(rp, '"$DATA_ROOT/hf_cache/hub/models--Qwen--Qwen3-8B/snapshots/b968826d9c46dd6066d109eabc6255188de91218"', f'"{spec["path"]}"')
# ---- freeze manifests
for fn in ['IMPLEMENTATION_FREEZE.json', 'PROTOCOL_FREEZE.json']:
    j = read(D / fn); j['files'] = {k: sha(D / k) for k in j['files']}; j['E16_4_manifest_recomputed'] = 'hashes recomputed over this Llama copy (P2_R7_E16 build_e164.py)'; save(D / fn, j)
diff = subprocess.run(['diff', '-ru', str(SRC / 'src'), str(D / 'src')], capture_output=True, text=True).stdout
(X / 'diffs/e164_replay_code.diff').write_text(diff)
changed = [l for l in diff.splitlines() if (l.startswith('+') or l.startswith('-')) and not l.startswith('+++') and not l.startswith('---')]
save(X / 'notes/E164_BUILD.json', dict(utc=utc(), source=str(SRC), dest=str(D), routes=routes, code_diff_changed_lines=len(changed), code_diff_added=sum(l.startswith('+') for l in changed),
                                       code_diff_removed=sum(l.startswith('-') for l in changed), files={k: sha(D / k) for k in ['frozen_config.json', 'protocol/label_token_sets.json', 'protocol/prefix_ids.json',
                                       'protocol/large_obqa_T_deployment.json', 'protocol/large_arc_T_deployment.json', 'inputs/large_obqa_T_expected_routes.jsonl', 'inputs/large_arc_T_expected_routes.jsonl']}))
print('BUILT', D, 'routes', routes, 'changed code lines', len(changed))
