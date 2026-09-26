"""Build E3 timing-repeat job folders (login node, CPU only, no model loads).

usage: build_e3.py repeat P2R1_REPEAT1      -> P2_R1_E3_P2R1_REPEAT1_<UTC>/{large,medium,mmlu}
Copies replay code and configs (never outputs) from the original P2_* stages, applies only the approved edits
(exact-string replacements asserted to match once), recomputes the copied freeze-hash manifests, writes diffs.
Nothing is written into existing P2_* folders.
"""
import sys
sys.dont_write_bytecode = True
import datetime, hashlib, json, os, shutil, subprocess
from pathlib import Path

ROOT = Path('$DATA_DIR')
ORIG = {'large': ROOT / 'P2_FROZEN_POLICY_E2E_VALIDATION_20260914T174120Z',
        'medium': ROOT / 'P2_MEDIUM_PAIR_E2E_STAGE2_20260915T205303Z',
        'mmlu': ROOT / 'P2_MMLU_PRO_E2E_STAGE2_20260916T212147Z'}
SCRIPT = {'large': 'run_e2e.pbs', 'medium': 'run_medium_stage2.pbs', 'mmlu': 'run_mmlu_stage2.pbs'}
COPY = {
    'large': dict(dirs=['src', 'inputs', 'protocol'],
                  files=['frozen_config.json', 'SOURCE_INDEX.json', 'PROTOCOL_FREEZE.json', 'IMPLEMENTATION_FREEZE.json',
                         'PANEL_VALIDATION_FREEZE.json', 'run_e2e.pbs', 'evidence/panel_source_checks.json']),
    'medium': dict(dirs=['src', 'inputs', 'protocol'], symlinks=['assets/helper', 'assets/receiver', 'assets/fuser'],
                   files=['MEDIUM_PAIR_E2E_STAGE2_FREEZE.json', 'MODEL_SOURCE_INDEX.json', 'SOURCE_INDEX.json', 'run_medium_stage2.pbs']),
    'mmlu': dict(dirs=['src', 'inputs', 'protocol'],
                 files=['MMLU_PRO_E2E_STAGE2_FREEZE.json', 'DATASET_SOURCE_INDEX.json', 'MODEL_SOURCE_INDEX.json',
                        'RUNTIME_SOURCE_INDEX.json', 'SOURCE_INDEX.json', 'run_mmlu_stage2.pbs', 'evidence/CPU_PREFLIGHT.json',
                        'monitor_resources.py', 'supervise_stage2.py', 'validate_results_cpu.py', 'finalize_reports.py']),
}
REPEAT_WALLTIME = '01:30:00'


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 22), b''):
            h.update(b)
    return h.hexdigest()


def utc():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def edit(path, old, new):
    s = path.read_text()
    assert s.count(old) == 1, (str(path), old, s.count(old))
    path.write_text(s.replace(old, new))


def copy_stage(stage, dest):
    src, spec = ORIG[stage], COPY[stage]
    dest.mkdir(parents=True)
    for d in spec['dirs']:
        shutil.copytree(src / d, dest / d, ignore=shutil.ignore_patterns('__pycache__'), symlinks=False)
    for f in spec['files']:
        (dest / f).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src / f, dest / f)
    for l in spec.get('symlinks', []):
        (dest / l).parent.mkdir(parents=True, exist_ok=True)
        target = os.readlink(src / l)
        assert os.path.isabs(target)
        os.symlink(target, dest / l)
    (dest / 'evidence/pbs').mkdir(parents=True, exist_ok=True)
    (dest / 'records').mkdir(exist_ok=True)


def run_script_paths(stage, dest):
    s = dest / SCRIPT[stage]
    stagevar = {'large': 'P2_STAGE', 'medium': 'P2_MEDIUM_EXEC', 'mmlu': 'P2_STAGE'}[stage]
    edit(s, f'export {stagevar}="$DATA_ROOT/projects/iclr2027_p2/{ORIG[stage].name}"', f'export {stagevar}="{dest}"')
    run = {'large': '${PBS_JOBID}_frozen_policy_e2e', 'medium': '${PBS_JOBID}_medium_stage2', 'mmlu': '${PBS_JOBID}_mmlu_stage2'}[stage]
    edit(s, f'export P2_RUN="$DATA_ROOT/runs/iclr2027_p2/{run}"', f'export P2_RUN="${stagevar}/run_logs"')
    edit(s, 'export TMPDIR="$DATA_ROOT/tmp/$PBS_JOBID"', f'export TMPDIR="${stagevar}/tmp"')


def edits_large(dest, walltime):
    edit(dest / 'src/common.py', 'P=Path(__file__).resolve().parents[1]; ROOT=P.parent\n',
         'P=Path(__file__).resolve().parents[1]; ROOT=P.parent.parent  # E3: stage copy nested one level below the project root\n')
    e = dest / 'src/pbs_entry.py'
    edit(e, "j['queue']=='gpu-queue'", "j['queue']=='node-queue'")
    edit(e, "int(r['ngpus'])==2", "int(r['ngpus'])==8")
    edit(e, f"r['walltime']=='00:30:00'", f"r['walltime']=='{walltime}'")
    s = dest / 'src/supervise.py'
    edit(s, "stime=datetime.datetime.strptime(job['stime'],'%a %b %d %H:%M:%S %Y').replace(tzinfo=datetime.timezone.utc).timestamp();deadline=stime+1800-60;os.environ['P2_DEADLINE_EPOCH']=str(deadline)\n",
         "stime=float(os.environ['R1E3_REPLAY_START_EPOCH']);deadline=stime+1800-60;os.environ['P2_DEADLINE_EPOCH']=str(deadline)  # E3: this replay's own start (original: PBS stime)\n")
    edit(s, "phases=[['validate_sources.py'],['execute.py'],['analyze.py'],['render.py']]",
         "phases=[['validate_sources.py'],['execute.py']]  # E3: records only; original analyze.py/render.py run later on the login node")
    run_script_paths('large', dest)
    f = dest / 'IMPLEMENTATION_FREEZE.json'
    j = json.loads(f.read_text())
    j['files'] = {k: sha(dest / k) for k in j['files']}
    j['E3_manifest_recomputed'] = 'hashes recomputed over this copy after the approved E3 edits; original hashes are in diffs/large.diff'
    f.write_text(json.dumps(j, ensure_ascii=False, indent=2) + '\n')
    p = json.loads((dest / 'PROTOCOL_FREEZE.json').read_text())
    assert all(sha(dest / k) == v for k, v in p['files'].items()), 'PROTOCOL_FREEZE must still match unchanged copies'


def edits_medium(dest, walltime_seconds):
    edit(dest / 'src/common.py', 'ROOT=P.parent\n', 'ROOT=P.parent.parent  # E3: stage copy nested one level below the project root\n')
    g = dest / 'src/guard_checks.py'
    edit(g, "queue=job.get('queue')=='gpu-queue'", "queue=job.get('queue')=='node-queue'")
    edit(g, "requested_GPUs=int(r.get('ngpus',0))==2", "requested_GPUs=int(r.get('ngpus',0))==8")
    edit(g, "allocated_GPUs=sum(x['ngpus'] for x in assigned)==2", "allocated_GPUs=sum(x['ngpus'] for x in assigned)==8")
    edit(g, "budget=0<walltime_seconds(r['walltime'])<=900", f"budget=0<walltime_seconds(r['walltime'])<={walltime_seconds}")
    e = dest / 'src/pbs_entry.py'
    edit(e, "    deadline=stime+allocation['walltime_seconds']-45\n",
         "    replay_start=float(os.environ['R1E3_REPLAY_START_EPOCH']);deadline=replay_start+900-45  # E3: own start + original 900 s budget, original 45 s margin\n")
    edit(e, "save(P/'evidence/DEADLINE.json',dict(PBS_stime=job['stime'],", "save(P/'evidence/DEADLINE.json',dict(PBS_stime=job['stime'],E3_replay_start_epoch=replay_start,E3_replay_budget_seconds=900,")
    run_script_paths('medium', dest)
    f = dest / 'MEDIUM_PAIR_E2E_STAGE2_FREEZE.json'
    j = json.loads(f.read_text())
    o = str(ORIG['medium'])

    def remap(d):
        out = {}
        for k, v in d.items():
            if k.startswith(o + '/'):
                nk = str(dest) + k[len(o):]
                out[nk] = sha(nk)
            else:
                out[k] = v
        return out
    j['frozen_files'] = remap(j['frozen_files'])
    j['runtime_source_hashes'] = remap(j['runtime_source_hashes'])
    j['PBS_script_sha256'] = sha(dest / 'run_medium_stage2.pbs')
    j['E3_manifest_recomputed'] = 'frozen_files/runtime_source_hashes entries of the original stage folder remapped to this copy and re-hashed after the approved E3 edits; original paths and hashes are in diffs/medium.diff'
    f.write_text(json.dumps(j, ensure_ascii=False, indent=2) + '\n')


def edits_mmlu(dest, walltime, nested=True):
    if nested:
        edit(dest / 'src/common.py', 'ROOT=P.parent\n', 'ROOT=P.parent.parent  # E3: stage copy nested one level below the project root\n')
    g = dest / 'src/guard_checks.py'
    edit(g, "'queue_gpu_queue':job.get('queue')=='gpu-queue'", "'queue_node_queue':job.get('queue')=='node-queue'")
    edit(g, "'requested_ngpus_2':int(r.get('ngpus',0))==2", "'requested_ngpus_8':int(r.get('ngpus',0))==8")
    edit(g, "'allocated_ngpus_2':sum(item['ngpus'] for item in assigned)==2", "'allocated_ngpus_8':sum(item['ngpus'] for item in assigned)==8")
    if walltime != '01:00:00':
        edit(g, "<=walltime_seconds('01:00:00')}", f"<=walltime_seconds('{walltime}')}}")
    e = dest / 'src/pbs_entry.py'
    edit(e, "research_stop=datetime.datetime(2026,9,20,tzinfo=datetime.timezone.utc).timestamp()",
         "research_stop=datetime.datetime(2026,9,23,tzinfo=datetime.timezone.utc).timestamp()  # E3: moved from 2026-09-20")
    edit(e, "    deadline=start+check['walltime_seconds']-45;os.environ['MMLU_DEADLINE_EPOCH']=str(deadline)\n",
         "    replay_start=float(os.environ['R1E3_REPLAY_START_EPOCH']);deadline=replay_start+3600-45;os.environ['MMLU_DEADLINE_EPOCH']=str(deadline)  # E3: own start + original 3600 s budget, original 45 s margin\n")
    edit(e, "save(P/'evidence/DEADLINE.json',dict(utc=utc(),PBS_stime=j['stime'],", "save(P/'evidence/DEADLINE.json',dict(utc=utc(),PBS_stime=j['stime'],E3_replay_start_epoch=replay_start,E3_replay_budget_seconds=3600,")
    run_script_paths('mmlu', dest)


def recompute_mmlu_freeze(dest):
    f = dest / 'MMLU_PRO_E2E_STAGE2_FREEZE.json'
    j = json.loads(f.read_text())
    j['frozen_files'] = {k: sha(dest / k) for k in j['frozen_files']}
    j['PBS_script_sha256'] = sha(dest / 'run_mmlu_stage2.pbs')
    j['E3_manifest_recomputed'] = 'frozen_files re-hashed over this copy after the approved E3 edits; original hashes are in diffs/mmlu.diff'
    f.write_text(json.dumps(j, ensure_ascii=False, indent=2) + '\n')


def home_receipt(dest):
    p = subprocess.run([str(Path.home() / 'bin/check-home-space'), '15'], capture_output=True, text=True)
    assert p.returncode == 0 and 'Home space check: PASSED' in p.stdout, p.stdout + p.stderr
    (dest / 'evidence/pbs/home_check.txt').write_text(p.stdout)


def stage_diff(stage, dest, out):
    spec = COPY[stage]
    items = spec['dirs'] + spec['files']
    with open(out, 'w') as fh:
        for it in items:
            r = subprocess.run(['diff', '-ruN', '--exclude=__pycache__', str(ORIG[stage] / it), str(dest / it)], capture_output=True, text=True)
            assert r.returncode in (0, 1), r.stderr
            fh.write(r.stdout)


JOB_SCRIPT = r'''#!/bin/bash
# [scheduler directive removed for anonymity]
# [scheduler directive removed for anonymity]
# [scheduler directive removed for anonymity]
# [scheduler directive removed for anonymity]
# [scheduler directive removed for anonymity]
# E3 {JOB}: {PURPOSE}
# Submit: submit-job  -q node-queue -l select=1 -l walltime={WALLTIME} -l fsreq=<fs> -N {JOB} [-W depend=afterany:<previous>] {SELF}
# Exclusive 8-GPU node (node-queue, place=scatter:excl). Replays use GPUs 0-1 only (helper cuda:0, receiver+fuser cuda:1); GPUs 2-7 stay idle.
set -uo pipefail
NEW={NEW}
source "$HOME/.config/ClusterB-storage.sh"
export http_proxy=http://proxy.cluster.invalid:3128 https_proxy=http://proxy.cluster.invalid:3128
export HTTP_PROXY=http://proxy.cluster.invalid:3128 HTTPS_PROXY=http://proxy.cluster.invalid:3128
export CUDA_VISIBLE_DEVICES=0,1 CUDA_DEVICE_ORDER=PCI_BUS_ID
LOG="$NEW/logs"; mkdir -p "$LOG"
{{
  echo "JOB_START_UTC=$(date -u +%Y-%m-%dT%H:%M:%SZ) host=$(hostname) PBS_JOBID=${{PBS_JOBID:-none}}"
  nvidia-smi -L
  nvidia-smi --query-gpu=index,uuid,memory.used,utilization.gpu --format=csv
  job-status -f "$PBS_JOBID" | grep -E 'queue =|Resource_List|exec_vnode|exec_host'
}} > "$LOG/job_env.txt" 2>&1
for item in {ITEMS}; do
  stage=${{item%%:*}}; script=${{item#*:}}
  export R1E3_REPLAY_START_EPOCH=$(date +%s.%N)
  echo "REPLAY_START $stage utc=$(date -u +%Y-%m-%dT%H:%M:%SZ) epoch=$R1E3_REPLAY_START_EPOCH" >> "$LOG/replays.log"
  bash "$NEW/$stage/$script"; rc=$?
  echo "REPLAY_END $stage exit=$rc utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "$LOG/replays.log"
  nvidia-smi --query-gpu=index,memory.used,utilization.gpu --format=csv >> "$LOG/replays.log" 2>&1
done
echo "JOB_END_UTC=$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "$LOG/job_env.txt"
'''


def build_repeat(job):
    ts = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    new = ROOT / f'P2_R1_E3_{job}_{ts}'
    new.mkdir()
    (new / 'diffs').mkdir(); (new / 'logs').mkdir(); (new / 'e3_build').mkdir()
    for stage in ['large', 'medium', 'mmlu']:
        copy_stage(stage, new / stage)
    edits_large(new / 'large', REPEAT_WALLTIME)
    edits_medium(new / 'medium', 5400)
    edits_mmlu(new / 'mmlu', REPEAT_WALLTIME)
    recompute_mmlu_freeze(new / 'mmlu')
    for stage in ['large', 'medium', 'mmlu']:
        home_receipt(new / stage)
        stage_diff(stage, new / stage, new / 'diffs' / f'{stage}.diff')
    js = new / 'run_e3_repeat.pbs'
    js.write_text(JOB_SCRIPT.format(NEW=new, JOB=job, WALLTIME=REPEAT_WALLTIME, SELF=js.name,
                                    PURPOSE='three original E2E replays (large, medium, MMLU-Pro) one after another, records only',
                                    ITEMS='large:run_e2e.pbs medium:run_medium_stage2.pbs mmlu:run_mmlu_stage2.pbs'))
    shutil.copy2(__file__, new / 'e3_build/build_e3.py')
    print(new)
    return new


if __name__ == '__main__' and sys.argv[1] == 'repeat':
    build_repeat(sys.argv[2])


# ============================================================================ MMLU_C2C_FULL (approved scoped rebuild)
FULL_WALLTIME = '01:00:00'
FULL_PROTOCOL_KEEP = ['Stage1_deployment_configs.json', 'generation_configs.json', 'label_token_sets.json', 'large_native_config.json',
                      'prefix_ids.json', 'receiver_prompt.py', 'scoring_v2.py']
FULL_FILES = ['DATASET_SOURCE_INDEX.json', 'MODEL_SOURCE_INDEX.json', 'RUNTIME_SOURCE_INDEX.json', 'run_mmlu_stage2.pbs',
              'monitor_resources.py', 'supervise_stage2.py', 'validate_results_cpu.py', 'finalize_reports.py']


def edits_full_code(dest):
    c = dest / 'src/common.py'
    edit(c, "ARMS=['fixed_T','policy_T','fixed_C','policy_C']", "ARMS=['fixed_C','policy_C']  # E3 FULL: fixed C2C and C2C policy only")
    edit(c, "offset=i%4;return ARMS[offset:]+ARMS[:offset]", "offset=i%len(ARMS);return ARMS[offset:]+ARMS[:offset]  # E3 FULL: alternates which arm runs first")
    e = dest / 'src/pbs_entry.py'
    edit(e, "complete_requests=512,online_ProbeMax=256,", "complete_requests=read(P/'REPLAY_COMPLETE.json')['complete_requests'],online_ProbeMax=read(P/'REPLAY_COMPLETE.json')['online_ProbeMax'],")
    x = dest / 'src/execute.py'
    edit(x, "ids=read(P/'inputs/candidate_e2e128_ids.json')\n    assert [r['id'] for r in panel]==ids and len(ids)==128\n    schedule=read(P/'protocol/FOUR_ARM_SCHEDULE.json')",
         "ids=read(P/'inputs/panel_ids.json')\n    N=len(ids);NREQ=N*len(ARMS);NPOL=N*sum(a.startswith('policy') for a in ARMS)  # E3 FULL: counts derived from the list length\n"
         "    assert [r['id'] for r in panel]==ids and N==len(set(ids))==cfg['expected_counts']['questions'] and NREQ==cfg['expected_counts']['complete_action_requests']\n"
         "    schedule=read(P/'protocol/ARM_SCHEDULE.json')")
    edit(x, "complete_questions=len(success)//4,online_probe_attempts=probes,attempts=attempt,expected_requests=512,expected_probes=256,",
         "complete_questions=len(success)//len(ARMS),online_probe_attempts=probes,attempts=attempt,expected_requests=NREQ,expected_probes=NPOL,")
    edit(x, "ETA_remaining_seconds=elapsed*(512-len(success))/len(success)", "ETA_remaining_seconds=elapsed*(NREQ-len(success))/len(success)")
    edit(x, "stop_check();attempt+=1;assert attempt<=512", "stop_check();attempt+=1;assert attempt<=NREQ")
    edit(x, "if is_policy:probes+=1;assert probes<=256", "if is_policy:probes+=1;assert probes<=NPOL")
    edit(x, "print('PROGRESS',len(success),'/512','ONLINE_PROBES',probes,'/256',flush=True)", "print('PROGRESS',len(success),f'/{NREQ}','ONLINE_PROBES',probes,f'/{NPOL}',flush=True)")
    edit(x, "assert attempt==len(success)==len(set(success))==512 and probes==256", "assert attempt==len(success)==len(set(success))==NREQ and probes==NPOL")
    edit(x, "complete_requests=512,\n        fixed_Text=128,policy_Text=128,fixed_C2C=128,policy_C2C=128,online_ProbeMax=256,retries=0,",
         "complete_requests=NREQ,\n        per_arm_requests={a:N for a in ARMS},online_ProbeMax=NPOL,retries=0,")
    a = dest / 'src/analyze.py'
    edit(a, "ids=read(P/'inputs/candidate_e2e128_ids.json');panel=read(P/'protocol/PANEL_MANIFEST.json');meta={r['id']:r for r in panel['rows']}\n",
         "ids=read(P/'inputs/panel_ids.json');panel=read(P/'protocol/PANEL_MANIFEST.json');meta={r['id']:r for r in panel['rows']}\n"
         "N=len(ids);NREQ=N*len(ARMS);NPOL=N*sum(a.startswith('policy') for a in ARMS);REFS=[(x,{'T':'Text','C':'C2C'}[x]) for x in dict.fromkeys(a[-1] for a in ARMS)]  # E3 FULL: derived counts\n")
    edit(a, "assert len(rr)==512 and len(pp)==256 and len({r['key'] for r in rr})==512 and len({r['key'] for r in pp})==256",
         "assert len(rr)==NREQ and len(pp)==NPOL and len({r['key'] for r in rr})==NREQ and len({r['key'] for r in pp})==NPOL")
    edit(a, "assert len(ids)==len(set(ids))==128", "assert len(ids)==len(set(ids))==cfg['expected_counts']['questions']")
    edit(a, "assert len(attempts)==1024 and", "assert len(attempts)==2*NREQ and")
    edit(a, "idx.shape==(2000,128)", "idx.shape==(2000,N)")
    edit(a, "np.random.default_rng(0).integers(0,128,size=(2000,128))", "np.random.default_rng(0).integers(0,N,size=(2000,N))")
    edit(a, "for ref,label in [('T','Text'),('C','C2C')]:", "for ref,label in REFS:")
    edit(a, "mean_saving_ms=float(x),seed=0,N=128))", "mean_saving_ms=float(x),seed=0,N=N))")
    edit(a, "summary.append(dict(reference=label,N=128,q=.4,threshold=THRESHOLD,route_to_R_count=nR,coverage=nR/128,",
         "summary.append(dict(reference=label,N=N,q=.4,threshold=THRESHOLD,route_to_R_count=nR,coverage=nR/N,")
    edit(a, "for pos in range(4):diagnostic", "for pos in range(len(ARMS)):diagnostic")
    edit(a, "[dict(reference=r['reference'],N=128,paired_mean_saving_ms", "[dict(reference=r['reference'],N=N,paired_mean_saving_ms")
    edit(a, "requests=512,online_probes=256,\n    N=128,duplicate_request_keys=0,missing_requests=0,input_hash_mismatches=0,reparsed_outputs=512,",
         "requests=NREQ,online_probes=NPOL,\n    N=N,duplicate_request_keys=0,missing_requests=0,input_hash_mismatches=0,reparsed_outputs=NREQ,")
    edit(a, "each_arm_each_position_32=True,\n    independent_online_probes_per_policy=128,", "each_arm_each_position_balanced=True,\n    independent_online_probes_per_policy=N,")
    edit(a, "MMLU_TEXT_E2E=summary[0]['classification'],MMLU_C2C_E2E=summary[1]['classification'])",
         "**{'MMLU_'+r['reference'].upper()+'_E2E':r['classification'] for r in summary})")


FULL_PREPARE = r'''"""E3 FULL: new pre-request freeze + model-free CPU preflight for the 2,641-question two-arm C2C replay.
Adapted from the original Stage2 prepare_freeze.py: panel = all development group representatives in frozen Stage1
order; arms fixed_C/policy_C alternating first per question; bootstrap default_rng(0).integers(0,N,(2000,N));
counts derived from the list length; q=.40 threshold unchanged. No model load, forward, gold or outcome read."""
from common import *
import ast,collections,subprocess
import numpy as np
from transformers import AutoTokenizer
assert not os.environ.get('CUDA_VISIBLE_DEVICES','') and not FREEZE.exists()
assert ARMS==['fixed_C','policy_C']
print('RESOLVED_PATHS',json.dumps(resolved_paths()),flush=True)
assert sha(STAGE1/'MMLU_PRO_STAGE1_PROTOCOL_FREEZE.json')==PARENT_HASH
parent=read(STAGE1/'MMLU_PRO_STAGE1_PROTOCOL_FREEZE.json');assert read(STAGE1/'NUMERICAL_VALIDATION.json')['status']=='PASS'
assert read(STAGE1/'FINAL_STATE.json')['status']=='COMPLETE_MMLU_PRO_STAGE1'
groups_path=STAGE1/'splits/dev_groups.json';gh=sha(groups_path)
assert gh==parent['frozen_files']['splits/dev_groups.json'],'dev_groups.json must be the Stage1-frozen split'
dev_groups=read(groups_path);ii=[g['representative_id'] for g in dev_groups];N=len(ii)
assert N==len(set(ii))==2641
groups={g['representative_id']:g for g in dev_groups}
meta={r['id']:r for r in rows(STAGE1/'inputs/queries_only.jsonl') if r['source_split']=='test'}
qh=read(STAGE1/'protocol/QUERY_IDENTITIES.json');manifest=[];queries=[]
for ordinal,ident in enumerate(ii):
    r=meta[ident];q={k:r[k] for k in ['id','question_stem','choice_labels','choice_text']}
    assert queryhash(q)==qh[ident]
    g=groups[ident];assert ident==min(g['members'],key=lambda x:int(x.split(':')[1]))
    manifest.append(dict(ordinal=ordinal,id=ident,question_id=r['question_id'],representative_id=ident,group_hash=g['group_hash'],
        category=r['category'],K=r['K'],query_sha256=qh[ident]));queries.append(q)
assert len({r['group_hash'] for r in manifest})==N
(P/'inputs').mkdir(exist_ok=True);save(P/'inputs/panel_ids.json',ii);write_rows(P/'inputs/panel_queries.jsonl',queries)
save(P/'protocol/PANEL_MANIFEST.json',dict(status='E3_FULL_ALL_DEVELOPMENT_GROUP_REPRESENTATIVES',N=N,IDs=ii,rows=manifest,
    category_counts=dict(sorted(collections.Counter(r['category'] for r in manifest).items())),K_distribution=dict(sorted(collections.Counter(r['K'] for r in manifest).items())),
    source=str(groups_path),source_sha256=gh,order='frozen Stage1 dev_groups.json representative order',
    selection='all development group representatives; no subset selection',selection_changed=False,Stage1_score_route_correctness_used_for_selection=False))
schedule=[dict(ordinal=i,id=ident,arms=order_for(i)) for i,ident in enumerate(ii)]
save(P/'protocol/ARM_SCHEDULE.json',schedule)
assert [r['arms'] for r in schedule[:2]]==[['fixed_C','policy_C'],['policy_C','fixed_C']]
first_counts={arm:sum(r['arms'][0]==arm for r in schedule) for arm in ARMS};assert max(first_counts.values())-min(first_counts.values())<=1
idx=np.random.default_rng(0).integers(0,N,size=(2000,N));np.savez_compressed(P/'protocol/bootstrap_indices.npz',ids=np.array(ii),indices=idx,seed=0)
deps=read(P/'protocol/Stage1_deployment_configs.json')['deployments']
assert sha(P/'protocol/Stage1_deployment_configs.json')==sha(STAGE1/'deployments/deployment_configs.json')
assert deps['C']['q']==.4 and deps['C']['threshold']==THRESHOLD and deps['C']['mode']=='selective'
assert sha(P/'src/native_runtime.py')==sha(STAGE1/'src/native_runtime.py')
for file in (P/'protocol').glob('*'):
    if (STAGE1/'protocol'/file.name).is_file():assert sha(file)==sha(STAGE1/'protocol'/file.name)
for f in (P/'src').glob('*.py'):ast.parse(f.read_text())
subprocess.run(['bash','-n',str(P/'run_mmlu_stage2.pbs')],check=True)
parser=load_module(P/'protocol/scoring_v2.py','preflight_parser');tok=AutoTokenizer.from_pretrained(read(P/'MODEL_SOURCE_INDEX.json')['models']['receiver']['path'],local_files_only=True)
sets=read(P/'protocol/label_token_sets.json')
for K in range(3,11):
    labels=list('ABCDEFGHIJ')[:K]
    for label in labels:
        assert len(tok.encode(label,add_special_tokens=False))==1
        assert parser.parse_answer('The correct answer is '+label,labels)['answer']==label
        assert all(tok.decode([i],skip_special_tokens=False,clean_up_tokenization_spaces=False).strip()==label for i in sets[label])
    assert not parser.parse_answer('The correct answer is '+chr(65+K),labels)['valid']
    assert not parser.parse_answer('The correct answer is A or B',labels)['valid']
from execute import timed_arm
class Dummy:
    def __init__(self,u):self.u=u;self.calls=[]
    def check_hooks(self):pass
    def probe(self,q):self.calls.append('probe');return {'ProbeMax':self.u}
    def action(self,q,a):self.calls.append(a);return {'synthetic':True}
dummyq=dict(id='SYNTHETIC',question_stem='Placeholder.',choice_labels=list('ABCDEFGHIJ'),choice_text=['placeholder']*10)
cases=0
for u in [0.,THRESHOLD,THRESHOLD+1e-8,1.]:
    for arm in ARMS:
        rt=Dummy(u);chosen,probe,res,parts,elapsed=timed_arm(rt,dummyq,arm,THRESHOLD,lambda:None)
        expected=('R' if u<=THRESHOLD else arm[-1]) if arm.startswith('policy') else arm[-1]
        assert chosen==expected and rt.calls==(['probe',expected] if arm.startswith('policy') else [expected])
        assert abs(sum(parts.values())-elapsed)<1e-8;cases+=1
source=read(P/'RUNTIME_SOURCE_INDEX.json')
for rel in ['MMLU_PRO_STAGE1_PROTOCOL_FREEZE.json','MODEL_SOURCE_INDEX.json','deployments/deployment_configs.json','src/native_runtime.py',
    'splits/dev_groups.json','protocol/QUERY_IDENTITIES.json','inputs/queries_only.jsonl','FINAL_STATE.json','ARTIFACT_SHA256SUMS']:
    source[str(STAGE1/rel)]=sha(STAGE1/rel)
for directory in ['actions','probes']:
    path=STAGE1/f'shards/2/{directory}/dev.jsonl';expected=read(STAGE1/'shards/2/INFERENCE_COMPLETE.json')['files'][directory+'/dev.jsonl']
    assert sha(path)==expected;source[str(path)]=expected
for path,h in source.items():assert sha(path)==h,path
save(P/'SOURCE_INDEX.json',dict(parent_Stage1=str(STAGE1),source_hashes=source))
save(P/'evidence/CPU_PREFLIGHT.json',dict(utc=utc(),status='PASS',model_loads=0,model_forwards=0,GPU_calls=0,
    panel_group_reps=N,panel_order='frozen Stage1 dev_groups representative order',first_arm_counts=first_counts,
    synthetic_wrapper_cases=cases,native_runtime_byte_identical=True,parser_token_checks='K=3..10 PASS',paths=resolved_paths()))
paths=[*P.glob('src/*.py'),*P.glob('protocol/*'),*P.glob('inputs/*'),P/'run_mmlu_stage2.pbs',P/'MODEL_SOURCE_INDEX.json',P/'DATASET_SOURCE_INDEX.json',P/'RUNTIME_SOURCE_INDEX.json',P/'SOURCE_INDEX.json',P/'evidence/CPU_PREFLIGHT.json']
cfg=dict(task='P2_R1_E3_MMLU_C2C_FULL',status='PASS',utc=utc(),MMLU_PRO_STAGE2_RESULTS_OBSERVED=False,
    parent_Stage1_protocol_freeze_sha256=PARENT_HASH,Stage1_deployment_sha256=sha(STAGE1/'deployments/deployment_configs.json'),
    deployments={'C':dict(reference=deps['C']['reference'],q=.4,threshold=THRESHOLD,comparison='u<=threshold; no panel quantile')},
    panel_source_sha256=gh,panel_manifest_sha256=sha(P/'protocol/PANEL_MANIFEST.json'),
    models={role:{k:v for k,v in m.items() if k!='files'} for role,m in read(P/'MODEL_SOURCE_INDEX.json')['models'].items()},model_file_hash_index_sha256=sha(P/'MODEL_SOURCE_INDEX.json'),
    source_hashes=source,Stage1_native_runtime_file_unchanged=True,model_and_generation_semantics='exact Stage1 dynamic-K R/C2C and FP32 ProbeMax, V2 parser, thinking off, receiver64 greedy',
    topology=dict(GPUs=2,helper='cuda:0',receiver_fuser='cuda:1',batch=1,one_residency=True,same_allocation=True,node='exclusive node-queue 8-GPU node; GPUs 2-7 idle'),
    execution_order=dict(question_order='frozen Stage1 dev_groups representative order (all development group representatives)',arms=ARMS,rotation='alternating per question ordinal: even fixed_C first, odd policy_C first',schedule_sha256=sha(P/'protocol/ARM_SCHEDULE.json')),
    expected_counts=dict(questions=N,complete_action_requests=N*len(ARMS),each_arm=N,online_ProbeMax=N,online_ProbeMax_each_policy=N,warmup=0,synthetic_forwards=0,retries=0),
    timing_boundary='authoritative outer perf_counter: input preparation and entry hooks; independent unchanged online ProbeMax with tokenization/transfer/full prefill/last-position lm_head/FP32 label aggregation and diagnostics; selector; complete selected native R/Text/C2C generation/decode/V2 parser/hook removal; final cleanup and two-GPU sync. Pre-request drain sync precedes timer. Disk logging/JSON serialization, gold/identity analysis and startup are excluded; startup reported separately. No KV/prefill reuse, no shared policy probe.',
    bootstrap=dict(seed=0,resamples=2000,N=N,unit='question-level paired fixed-policy saving',indices='protocol/bootstrap_indices.npz',indices_sha256=sha(P/'protocol/bootstrap_indices.npz'),generator=f'numpy.random.default_rng(0).integers(0,{N},size=(2000,{N}))',interval='numpy.quantile(mean_savings,[.025,.975],method=linear); descriptive percentile 95%',numpy_version=np.__version__),
    positive_gate='E2E_POSITIVE iff paired mean(fixed-policy)>0 and descriptive bootstrap 95% lower>0; otherwise E2E_UNCERTAIN_OR_NEGATIVE; not population guarantee',
    identity='route C compares same-round fixed C2C; route R compares saved Stage1 native R; raw/parsed/tokens retained; differences reported without reruns; gold only linked after complete replay',
    reporting='records only inside the job; retain first formal request and all invalid/long/mismatched items; analysis later on the login node',
    positioning='E3 reviewer request: full development-population E2E for the C2C reference; exposed development data; not sealed/test confirmation',
    budget=dict(max_formal_PBS_jobs=1,queue='node-queue',select=1,replay_GPUs=2,walltime='01:00:00',resubmission_allowed=False),
    PBS_script_sha256=sha(P/'run_mmlu_stage2.pbs'),manuscript_or_supplement_changes=False,
    frozen_files={str(path.relative_to(P)):sha(path) for path in sorted(paths) if path.is_file()})
save(FREEZE,cfg);save(P/'evidence/FREEZE_RECEIPT.json',dict(utc=utc(),freeze_sha256=sha(FREEZE),MMLU_PRO_STAGE2_RESULTS_OBSERVED=False))
save(P/'RESOURCE_LEDGER.json',dict(status='PREPARED',utc=utc(),max_formal_PBS_jobs=1,formal_PBS_submissions=0,queue='node-queue',select=1,walltime='01:00:00'))
print('CPU_PREFLIGHT_AND_E3_FULL_FREEZE_PASS',N,sha(FREEZE),flush=True)
'''


def build_full(job):
    ts = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    new = ROOT / f'P2_R1_E3_{job}_{ts}'
    src = ORIG['mmlu']
    new.mkdir()
    shutil.copytree(src / 'src', new / 'src', ignore=shutil.ignore_patterns('__pycache__'))
    (new / 'protocol').mkdir()
    for f in FULL_PROTOCOL_KEEP:
        shutil.copy2(src / 'protocol' / f, new / 'protocol' / f)
    for f in FULL_FILES:
        shutil.copy2(src / f, new / f)
    for d in ['records', 'evidence/pbs', 'diffs', 'logs', 'e3_build']:
        (new / d).mkdir(parents=True, exist_ok=True)
    edits_mmlu(new, FULL_WALLTIME, nested=False)
    edits_full_code(new)
    (new / 'src/prepare_freeze.py').write_text(FULL_PREPARE)
    home_receipt(new)
    shutil.copy2(__file__, new / 'e3_build/build_e3.py')
    js = new / 'run_e3_full.pbs'
    js.write_text(JOB_SCRIPT.format(NEW=new, JOB=job, WALLTIME=FULL_WALLTIME, SELF=js.name,
                                    PURPOSE='MMLU-Pro C2C replay on all 2,641 development group representatives (fixed C2C vs C2C policy q=.40), records only',
                                    ITEMS='.:run_mmlu_stage2.pbs'))
    print(new)
    return new


def full_diff(new):
    src = ORIG['mmlu']
    with open(new / 'diffs/mmlu_full_code.diff', 'w') as fh:
        for it in ['src'] + [f'protocol/{f}' for f in FULL_PROTOCOL_KEEP] + FULL_FILES:
            r = subprocess.run(['diff', '-ruN', '--exclude=__pycache__', str(src / it), str(new / it)], capture_output=True, text=True)
            assert r.returncode in (0, 1), r.stderr
            fh.write(r.stdout)
    with open(new / 'diffs/mmlu_full_regenerated_artifacts.diff', 'w') as fh:
        for a, b in [('inputs/candidate_e2e128_ids.json', 'inputs/panel_ids.json'), ('inputs/panel_queries.jsonl', 'inputs/panel_queries.jsonl'),
                     ('protocol/FOUR_ARM_SCHEDULE.json', 'protocol/ARM_SCHEDULE.json'), ('protocol/PANEL_MANIFEST.json', 'protocol/PANEL_MANIFEST.json'),
                     ('SOURCE_INDEX.json', 'SOURCE_INDEX.json'), ('evidence/CPU_PREFLIGHT.json', 'evidence/CPU_PREFLIGHT.json'),
                     ('MMLU_PRO_E2E_STAGE2_FREEZE.json', 'MMLU_PRO_E2E_STAGE2_FREEZE.json')]:
            fh.write(f'### regenerated: original {a} (sha256 {sha(src / a)}) -> new {b} (sha256 {sha(new / b)})\n')
        fh.write(f'### regenerated: original protocol/bootstrap_indices.npz (sha256 {sha(src / "protocol/bootstrap_indices.npz")}) -> new (sha256 {sha(new / "protocol/bootstrap_indices.npz")})\n')
        r = subprocess.run(['diff', '-u', str(src / 'MMLU_PRO_E2E_STAGE2_FREEZE.json'), str(new / 'MMLU_PRO_E2E_STAGE2_FREEZE.json')], capture_output=True, text=True)
        fh.write(r.stdout[:200000])


if __name__ == '__main__' and sys.argv[1] in ('full', 'full_diff'):
    if sys.argv[1] == 'full':
        build_full(sys.argv[2])
    else:
        full_diff(Path(sys.argv[2]))
