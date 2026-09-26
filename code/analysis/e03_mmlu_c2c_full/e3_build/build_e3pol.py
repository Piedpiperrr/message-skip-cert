"""Build the E3 ClusterA folders (login node, CPU only, no model loads).

usage: build_e3pol.py
  -> P2_R1_E3POL_{REPEAT1,REPEAT2,REPEAT3}_<UTC>/{large,medium,mmlu}   copies of the ORIGINAL stage folders
  -> P2_R1_E3POL_MMLU_C2C_FULL_<UTC>/                                 copy of the approved ClusterB rebuild (freeze f73e9b90...)
Copies replay code and configs (never outputs), applies only harness edits (exact-string replacements asserted to
match once), recomputes the copied freeze-hash manifests, writes diffs, node scripts and the two 2-node job scripts.
Nothing is written into existing P2_* folders. Adapted from P2_R1_E3_P2R1_REPEAT1_*/e3_build/build_e3.py (ClusterB).
"""
import sys
sys.dont_write_bytecode = True
import datetime, hashlib, json, os, shutil, subprocess
from pathlib import Path

ROOT = Path('$DATA_DIR')
ORIG = {'large': ROOT / 'P2_FROZEN_POLICY_E2E_VALIDATION_20260914T174120Z',
        'medium': ROOT / 'P2_MEDIUM_PAIR_E2E_STAGE2_20260915T205303Z',
        'mmlu': ROOT / 'P2_MMLU_PRO_E2E_STAGE2_20260916T212147Z'}
FULL_SRC = ROOT / 'P2_R1_E3_P2R1_MMLU_C2C_FULL_20260919T065245Z'
FULL_FREEZE_SHA = 'f73e9b90e5a1937c890cfbe1cb0848d5e2aced318d9114d55c7083024047871e'
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
    'full': dict(dirs=['src', 'inputs', 'protocol'],
                 files=['MMLU_PRO_E2E_STAGE2_FREEZE.json', 'DATASET_SOURCE_INDEX.json', 'MODEL_SOURCE_INDEX.json',
                        'RUNTIME_SOURCE_INDEX.json', 'SOURCE_INDEX.json', 'run_mmlu_stage2.pbs', 'evidence/CPU_PREFLIGHT.json',
                        'evidence/FREEZE_RECEIPT.json', 'monitor_resources.py', 'supervise_stage2.py', 'validate_results_cpu.py',
                        'finalize_reports.py']),
}
FULL_PROVENANCE = {'DEVIATIONS.md': 'provenance/ClusterB_REBUILD_DEVIATIONS.md', 'README_E3.md': 'provenance/ClusterB_REBUILD_README_E3.md',
                   'diffs/mmlu_full_code.diff': 'provenance/ClusterB_rebuild_diffs/mmlu_full_code.diff',
                   'diffs/mmlu_full_regenerated_artifacts.diff': 'provenance/ClusterB_rebuild_diffs/mmlu_full_regenerated_artifacts.diff',
                   'e3_build/build_e3.py': 'provenance/ClusterB_build_e3.py', 'logs/prepare_freeze_login.log': 'provenance/prepare_freeze_login.log'}
WALLTIME = '00:55:00'
WALLTIME_S = 3300
POL = '  # E3 ClusterA: '


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


def copy_items(src, spec, dest):
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
    """Stage path -> this copy; P2_RUN and TMPDIR inside the copy (as in the ClusterB E3 build); rg -> grep (no rg on ClusterA)."""
    s = dest / SCRIPT[stage]
    stagevar = {'large': 'P2_STAGE', 'medium': 'P2_MEDIUM_EXEC', 'mmlu': 'P2_STAGE'}[stage]
    edit(s, f'export {stagevar}="$DATA_ROOT/projects/iclr2027_p2/{ORIG[stage].name}"', f'export {stagevar}="{dest}"')
    run = {'large': '${PBS_JOBID}_frozen_policy_e2e', 'medium': '${PBS_JOBID}_medium_stage2', 'mmlu': '${PBS_JOBID}_mmlu_stage2'}[stage]
    edit(s, f'export P2_RUN="$DATA_ROOT/runs/iclr2027_p2/{run}"', f'export P2_RUN="${stagevar}/run_logs"')
    edit(s, 'export TMPDIR="$DATA_ROOT/tmp/$PBS_JOBID"', f'export TMPDIR="${stagevar}/tmp"')
    if stage != 'large':
        edit(s, "if ! rg -q 'Home space check: PASSED'", "if ! grep -q 'Home space check: PASSED'")


def edits_large(dest):
    edit(dest / 'src/common.py', 'P=Path(__file__).resolve().parents[1]; ROOT=P.parent\n',
         'P=Path(__file__).resolve().parents[1]; ROOT=P.parent.parent  # E3: stage copy nested one level below the project root\n')
    edit(dest / 'src/common.py', " assert os.environ.get('PBS_JOBID') and socket.gethostname().startswith('ClusterB-gpu')\n",
         " assert os.environ.get('PBS_JOBID') and socket.gethostname().startswith('x3')" + POL + "compute node (original: ClusterB-gpu)\n")
    edit(dest / 'src/common.py', " c=read(P/'execution_clearance.json');assert c['job_id']==os.environ['PBS_JOBID'] and c['strict_cgroup_match']\n",
         " c=read(P/'execution_clearance.json');assert c['job_id']==os.environ['PBS_JOBID']" + POL + "cgroup match recorded, not required (see pbs_entry.py)\n")
    e = dest / 'src/pbs_entry.py'
    edit(e, "assert host.startswith('ClusterB-gpu') and user=='user'",
         "assert host.startswith('x3') and user=='user'" + POL + "compute node (original: ClusterB-gpu)")
    edit(e, "j['queue']=='gpu-queue'", "j['queue']=='debug'")
    edit(e, "assert int(r['nodect'])==1 and int(r['ngpus'])==2 and r['fsreq']=='home:sharedfs' and r['walltime']=='00:30:00'",
         f"assert int(r['nodect'])==2 and int(r.get('ngpus',0))==0 and r['fsreq']=='home:sharedfs' and r['walltime']=='{WALLTIME}'"
         + POL + "debug, 2 exclusive nodes of 4 A100 (GPUs are not a PBS resource); original: gpu-queue, 1 node, ngpus=2, 00:30:00")
    edit(e, "nodes=Path(os.environ['PBS_NODEFILE']).read_text().split();assert {short(x) for x in nodes}=={short(host)}",
         "nodes=Path(os.environ['PBS_NODEFILE']).read_text().split();assert short(host) in {short(x) for x in nodes} and len({short(x) for x in nodes})==2"
         + POL + "this node is one of the job's 2 nodes (original: the only node)")
    edit(e, ";assert match,'STRICT_JOB_CGROUP_MISMATCH'",
         ";ClusterA_match=any(jid in x or jid.split('.')[0] in x or any(c.startswith(jid.split('.')[0]+'.') for c in x) for x in [l.split(':',2)[2].split('/') for l in cgroup.splitlines()])"
         + POL + "cgroup layout unverified on ClusterA; both matches recorded, not fatal (as in the medium and MMLU-Pro guards)")
    edit(e, "'strict_cgroup_match':match,'cgroup':cgroup,", "'strict_cgroup_match':match,'ClusterA_cgroup_match':ClusterA_match,'cgroup':cgroup,")
    edit(e, "save(P/'execution_clearance.json',{'job_id':jid,'host':host,'strict_cgroup_match':True,'GPU_count':2})",
         "save(P/'execution_clearance.json',{'job_id':jid,'host':host,'strict_cgroup_match':match,'ClusterA_cgroup_match':ClusterA_match,'cgroup_match_fatal':False,'GPU_count':2})")
    s = dest / 'src/supervise.py'
    edit(s, "stime=datetime.datetime.strptime(job['stime'],'%a %b %d %H:%M:%S %Y').replace(tzinfo=datetime.timezone.utc).timestamp();deadline=stime+1800-60;os.environ['P2_DEADLINE_EPOCH']=str(deadline)\n",
         "stime=float(os.environ['R1E3_REPLAY_START_EPOCH']);deadline=stime+1800-60;os.environ['P2_DEADLINE_EPOCH']=str(deadline)  # E3: this replay's own start (original: PBS stime)\n")
    edit(s, "phases=[['validate_sources.py'],['execute.py'],['analyze.py'],['render.py']]",
         "phases=[['validate_sources.py'],['execute.py']]  # E3: records only; original analyze.py/render.py run later on the login node")
    run_script_paths('large', dest)
    f = dest / 'IMPLEMENTATION_FREEZE.json'
    j = json.loads(f.read_text())
    j['files'] = {k: sha(dest / k) for k in j['files']}
    j['E3_manifest_recomputed'] = 'hashes recomputed over this copy after the E3 ClusterA harness edits; original hashes are in diffs/large.diff'
    f.write_text(json.dumps(j, ensure_ascii=False, indent=2) + '\n')
    p = json.loads((dest / 'PROTOCOL_FREEZE.json').read_text())
    assert all(sha(dest / k) == v for k, v in p['files'].items()), 'PROTOCOL_FREEZE must still match unchanged copies'


# ClusterA allocation guard for the medium stage (function allocation_identity in src/guard_checks.py)
MEDIUM_GUARD = [
    ("queue=job.get('queue')=='gpu-queue',nodect=int(r.get('nodect',0))==1,", "queue=job.get('queue')=='debug',nodect=int(r.get('nodect',0))==2,"),
    ("requested_GPUs=int(r.get('ngpus',0))==2,allocated_GPUs=sum(x['ngpus'] for x in assigned)==2,",
     "requested_GPUs=int(r.get('ngpus',0))==0,allocated_GPUs=sum(x['ngpus'] for x in assigned)==0," + POL + "GPUs are not a PBS resource (2 exclusive nodes of 4 A100); the CUDA guard still asserts 2 visible devices"),
    ("assigned_host=bool(assigned) and {x['node'].split('.')[0] for x in assigned}=={short},",
     "assigned_host=len(assigned)==2 and short in {x['node'].split('.')[0] for x in assigned},"),
    ("exec_host={x.split('/')[0].split('.')[0] for x in job.get('exec_host','').split('+')}=={short},",
     "exec_host=len(job.get('exec_host','').split('+'))==2 and short in {x.split('/')[0].split('.')[0] for x in job.get('exec_host','').split('+')},"),
    ("nodefile={x.split('.')[0] for x in nodefile}=={short},", "nodefile=len({x.split('.')[0] for x in nodefile})==2 and short in {x.split('.')[0] for x in nodefile},"),
    ("budget=0<walltime_seconds(r['walltime'])<=900)", f"budget=0<walltime_seconds(r['walltime'])<={WALLTIME_S})" + POL + "debug walltime 00:55:00 (original cap 900 s; the replay's own 900 s budget is kept in pbs_entry.py)"),
]


def edits_medium(dest):
    edit(dest / 'src/common.py', 'ROOT=P.parent\n', 'ROOT=P.parent.parent  # E3: stage copy nested one level below the project root\n')
    for old, new in MEDIUM_GUARD:
        edit(dest / 'src/guard_checks.py', old, new)
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
    j['E3_manifest_recomputed'] = 'frozen_files/runtime_source_hashes entries of the original stage folder remapped to this copy and re-hashed after the E3 ClusterA harness edits; original paths and hashes are in diffs/medium.diff'
    f.write_text(json.dumps(j, ensure_ascii=False, indent=2) + '\n')


def mmlu_guard(src_queue, src_ngpus):
    """ClusterA allocation guard edits for the MMLU-Pro guard_checks.py (original: gpu-queue/2; ClusterB rebuild: node-queue/8)."""
    qk = {'gpu-queue': 'queue_gpu_queue', 'node-queue': 'queue_node_queue'}[src_queue]
    return [
        (f"'{qk}':job.get('queue')=='{src_queue}','nodect_1':int(r.get('nodect',0))==1,",
         "'queue_debug':job.get('queue')=='debug','nodect_2':int(r.get('nodect',0))==2,"),
        (f"'requested_ngpus_{src_ngpus}':int(r.get('ngpus',0))=={src_ngpus},",
         "'requested_ngpus_0_ClusterA':int(r.get('ngpus',0))==0," + POL + "GPUs are not a PBS resource (2 exclusive nodes of 4 A100); the CUDA guard still asserts 2 visible devices"),
        (f"'allocated_ngpus_{src_ngpus}':sum(item['ngpus'] for item in assigned)=={src_ngpus},",
         "'allocated_ngpus_0_ClusterA':sum(item['ngpus'] for item in assigned)==0,"),
        ("'assigned_host_matches_process':bool(assigned) and {item['node'].split('.')[0] for item in assigned}=={short},",
         "'assigned_host_matches_process':len(assigned)==2 and short in {item['node'].split('.')[0] for item in assigned},"),
        ("'exec_host_matches_process':{part.split('/')[0].split('.')[0] for part in job.get('exec_host','').split('+')}=={short},",
         "'exec_host_matches_process':len(job.get('exec_host','').split('+'))==2 and short in {part.split('/')[0].split('.')[0] for part in job.get('exec_host','').split('+')},"),
        ("'PBS_nodefile_matches_process':{node.split('.')[0] for node in nodefile_nodes}=={short},",
         "'PBS_nodefile_matches_process':len({node.split('.')[0] for node in nodefile_nodes})==2 and short in {node.split('.')[0] for node in nodefile_nodes},"),
    ]


def edits_mmlu(dest):
    edit(dest / 'src/common.py', 'ROOT=P.parent\n', 'ROOT=P.parent.parent  # E3: stage copy nested one level below the project root\n')
    for old, new in mmlu_guard('gpu-queue', 2):
        edit(dest / 'src/guard_checks.py', old, new)
    e = dest / 'src/pbs_entry.py'
    edit(e, "research_stop=datetime.datetime(2026,9,20,tzinfo=datetime.timezone.utc).timestamp()",
         "research_stop=datetime.datetime(2026,9,23,tzinfo=datetime.timezone.utc).timestamp()  # E3: moved from 2026-09-20")
    edit(e, "    deadline=start+check['walltime_seconds']-45;os.environ['MMLU_DEADLINE_EPOCH']=str(deadline)\n",
         "    replay_start=float(os.environ['R1E3_REPLAY_START_EPOCH']);deadline=replay_start+3600-45;os.environ['MMLU_DEADLINE_EPOCH']=str(deadline)  # E3: own start + original 3600 s budget, original 45 s margin\n")
    edit(e, "save(P/'evidence/DEADLINE.json',dict(utc=utc(),PBS_stime=j['stime'],", "save(P/'evidence/DEADLINE.json',dict(utc=utc(),PBS_stime=j['stime'],E3_replay_start_epoch=replay_start,E3_replay_budget_seconds=3600,")
    run_script_paths('mmlu', dest)
    recompute_mmlu_freeze(dest, 'diffs/mmlu.diff')


def edits_full(dest):
    """ClusterB rebuild already has: own-start deadline, 2026-09-23 date stop, stage-local P2_RUN/TMPDIR, flat folder (ROOT unchanged)."""
    for old, new in mmlu_guard('node-queue', 8):
        edit(dest / 'src/guard_checks.py', old, new)
    s = dest / 'run_mmlu_stage2.pbs'
    edit(s, f'export P2_STAGE="{FULL_SRC}"', f'export P2_STAGE="{dest}"')
    edit(s, "if ! rg -q 'Home space check: PASSED'", "if ! grep -q 'Home space check: PASSED'")
    assert "research_stop=datetime.datetime(2026,9,23" in (dest / 'src/pbs_entry.py').read_text()
    assert "replay_start=float(os.environ['R1E3_REPLAY_START_EPOCH']);deadline=replay_start+3600-45" in (dest / 'src/pbs_entry.py').read_text()
    assert sha(dest / 'MMLU_PRO_E2E_STAGE2_FREEZE.json') == FULL_FREEZE_SHA
    recompute_mmlu_freeze(dest, 'diffs/mmlu_full_ClusterA.diff')


def recompute_mmlu_freeze(dest, diffname):
    f = dest / 'MMLU_PRO_E2E_STAGE2_FREEZE.json'
    j = json.loads(f.read_text())
    j['frozen_files'] = {k: sha(dest / k) for k in j['frozen_files']}
    j['PBS_script_sha256'] = sha(dest / 'run_mmlu_stage2.pbs')
    j['E3_manifest_recomputed'] = f'frozen_files re-hashed over this copy after the E3 ClusterA harness edits; original hashes are in {diffname}'
    f.write_text(json.dumps(j, ensure_ascii=False, indent=2) + '\n')


def home_receipt(dest):
    p = subprocess.run([str(Path.home() / 'bin/check-home-space'), '15'], capture_output=True, text=True)
    assert p.returncode == 0 and 'Home space check: PASSED' in p.stdout, p.stdout + p.stderr
    (dest / 'evidence/pbs/home_check.txt').write_text(p.stdout)


def write_diff(src, items, dest, out):
    with open(out, 'w') as fh:
        for it in items:
            r = subprocess.run(['diff', '-ruN', '--exclude=__pycache__', str(src / it), str(dest / it)], capture_output=True, text=True)
            assert r.returncode in (0, 1), r.stderr
            fh.write(r.stdout)


NODE_SCRIPT = r'''#!/bin/bash
# E3 ClusterA node run for {NAME}: {PURPOSE}
# Started by the 2-node job script through mpiexec (one shell per node). Replays run one after another on THIS node,
# GPUs 0-1 only (helper cuda:0, receiver+fuser cuda:1); GPUs 2-3 stay idle and nothing else runs on the node. Records only.
set -uo pipefail
NEW={NEW}
source "$HOME/.config/ClusterB-storage.sh"
export PATH="$PATH:/opt/pbs/bin"
export http_proxy=http://proxy.cluster.invalid:3128 https_proxy=http://proxy.cluster.invalid:3128
export HTTP_PROXY=http://proxy.cluster.invalid:3128 HTTPS_PROXY=http://proxy.cluster.invalid:3128
export CUDA_VISIBLE_DEVICES=0,1 CUDA_DEVICE_ORDER=PCI_BUS_ID
LOG="$NEW/logs"; mkdir -p "$LOG"
{{
  echo "NODE_START_UTC=$(date -u +%Y-%m-%dT%H:%M:%SZ) host=$(hostname) PBS_JOBID=${{PBS_JOBID:-none}} rank=${{PALS_RANKID:-${{PMI_RANK:-?}}}}"
  echo "## GPU model, driver, CUDA"
  nvidia-smi -L
  nvidia-smi --query-gpu=index,name,uuid,pci.bus_id,driver_version,vbios_version,memory.total,memory.used,utilization.gpu,clocks.max.sm,power.limit,persistence_mode,mig.mode.current --format=csv
  nvidia-smi | head -4
  grep -E "^(__version__|cuda|git_version)" "$DATA_ROOT/software/envs/c2c_official/lib/python3.10/site-packages/torch/version.py"
  echo "## GPU topology (nvidia-smi topo -m)"
  nvidia-smi topo -m
  echo "## CPU"
  lscpu
  echo "nproc=$(nproc) affinity=$(taskset -pc $$ 2>&1)"
  echo "## memory"; free -g
  echo "## scheduler"; job-status -f "$PBS_JOBID" | grep -E 'queue =|Resource_List|exec_vnode|exec_host'
  echo "## cgroup of this shell"; cat /proc/self/cgroup
  echo "## tools"; for t in job-status myquota rg grep; do echo "$t=$(command -v $t || echo MISSING)"; done
}} > "$LOG/node_hardware.txt" 2>&1
for item in {ITEMS}; do
  stage=${{item%%:*}}; script=${{item#*:}}
  export R1E3_REPLAY_START_EPOCH=$(date +%s.%N)
  echo "REPLAY_START $stage utc=$(date -u +%Y-%m-%dT%H:%M:%SZ) epoch=$R1E3_REPLAY_START_EPOCH host=$(hostname)" >> "$LOG/replays.log"
  bash "$NEW/$stage/$script"; rc=$?
  echo "REPLAY_END $stage exit=$rc utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "$LOG/replays.log"
  nvidia-smi --query-gpu=index,memory.used,utilization.gpu --format=csv >> "$LOG/replays.log" 2>&1
done
echo "NODE_END_UTC=$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "$LOG/node_hardware.txt"
'''

JOB_SCRIPT = r'''#!/bin/bash
# [scheduler directive removed for anonymity]
# [scheduler directive removed for anonymity]
# [scheduler directive removed for anonymity]
# [scheduler directive removed for anonymity]
# [scheduler directive removed for anonymity]
# E3 {JOB} (ClusterA debug, 2 nodes, one replay run per node, records only):
#   node 1 (rank 0): {N1}
#   node 2 (rank 1): {N2}
# Submit (from {HOME_FOLDER}):
#   submit-job  -q debug -l select=2 -l walltime={WALLTIME} -l fsreq=<fs> -N {JOB} {JOB}.pbs
set -uo pipefail
LOG={HOME_FOLDER}/logs; mkdir -p "$LOG"
{{
  echo "JOB_START_UTC=$(date -u +%Y-%m-%dT%H:%M:%SZ) head=$(hostname) PBS_JOBID=${{PBS_JOBID:-none}}"
  echo "PBS_NODEFILE:"; cat "$PBS_NODEFILE"
}} > "$LOG/{JOB}_job_env.txt" 2>&1
mpiexec -n 2 --ppn 1 --hostfile "$PBS_NODEFILE" --cpu-bind none bash -c '
  case "${{PALS_RANKID:-${{PMI_RANK:-x}}}}" in
    0) exec bash {N1}/run_e3pol_node.sh ;;
    1) exec bash {N2}/run_e3pol_node.sh ;;
    *) echo "UNKNOWN_RANK host=$(hostname)"; exit 9 ;;
  esac'
echo "MPIEXEC_EXIT=$? JOB_END_UTC=$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "$LOG/{JOB}_job_env.txt"
'''

REPEAT_ITEMS = 'large:run_e2e.pbs medium:run_medium_stage2.pbs mmlu:run_mmlu_stage2.pbs'


def build_repeat(name, ts):
    new = ROOT / f'P2_R1_E3POL_{name}_{ts}'
    new.mkdir()
    for d in ['diffs', 'logs', 'e3_build']:
        (new / d).mkdir()
    for stage in ['large', 'medium', 'mmlu']:
        copy_items(ORIG[stage], COPY[stage], new / stage)
    edits_large(new / 'large')
    edits_medium(new / 'medium')
    edits_mmlu(new / 'mmlu')
    for stage in ['large', 'medium', 'mmlu']:
        home_receipt(new / stage)
        write_diff(ORIG[stage], COPY[stage]['dirs'] + COPY[stage]['files'], new / stage, new / 'diffs' / f'{stage}.diff')
    (new / 'run_e3pol_node.sh').write_text(NODE_SCRIPT.format(
        NAME=new.name, NEW=new, ITEMS=REPEAT_ITEMS,
        PURPOSE='three original E2E replays (large, medium, MMLU-Pro panels) one after another'))
    shutil.copy2(__file__, new / 'e3_build/build_e3pol.py')
    return new


def build_full(ts):
    new = ROOT / f'P2_R1_E3POL_MMLU_C2C_FULL_{ts}'
    copy_items(FULL_SRC, COPY['full'], new)
    for d in ['diffs', 'logs', 'e3_build']:
        (new / d).mkdir()
    for a, b in FULL_PROVENANCE.items():
        (new / b).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(FULL_SRC / a, new / b)
    edits_full(new)
    home_receipt(new)
    write_diff(FULL_SRC, COPY['full']['dirs'] + COPY['full']['files'], new, new / 'diffs/mmlu_full_ClusterA.diff')
    (new / 'run_e3pol_node.sh').write_text(NODE_SCRIPT.format(
        NAME=new.name, NEW=new, ITEMS='.:run_mmlu_stage2.pbs',
        PURPOSE='MMLU-Pro C2C replay on all 2,641 development group representatives (fixed C2C vs C2C policy q=.40)'))
    shutil.copy2(__file__, new / 'e3_build/build_e3pol.py')
    return new


def job(name, home, n1, n2):
    p = home / f'{name}.pbs'
    p.write_text(JOB_SCRIPT.format(JOB=name, HOME_FOLDER=home, N1=n1, N2=n2, WALLTIME=WALLTIME))
    return p


if __name__ == '__main__':
    ts = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    r = {k: build_repeat(k, ts) for k in ['REPEAT1', 'REPEAT2', 'REPEAT3']}
    full = build_full(ts)
    a = job('P2R1_E3POL_A', r['REPEAT1'], r['REPEAT1'], r['REPEAT2'])
    b = job('P2R1_E3POL_B', r['REPEAT3'], r['REPEAT3'], full)
    print(json.dumps({'utc': utc(), 'folders': [str(x) for x in [*r.values(), full]], 'jobs': [str(a), str(b)]}, indent=1))
