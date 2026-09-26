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


if __name__ == '__main__':
    mode, job = sys.argv[1], sys.argv[2]
    assert mode == 'repeat'
    build_repeat(job)
