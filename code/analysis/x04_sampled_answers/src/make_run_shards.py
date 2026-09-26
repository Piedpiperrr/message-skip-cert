"""X4 (copy of X3 make_run_shards.py; node script runs run_x4.py --sampling on; receiver qwen3_8b via jobs/receiver.env). X3 docstring: X3 (copy of X2 make_run_shards.py; OBQA + ARC only, receiver from jobs/receiver.env): split all X3 rows into single-GPU chains balanced
by expected time (harness). Per-row seconds come from the smoke latencies.
usage: make_run_shards.py <n_nodes> <sec_per_row_obqa_arc> <queue> <walltime HH:MM:SS> <job_name>
Writes records/work/run/chain_XX.jsonl, records/work/run/PLAN.json and jobs/<job_name>.pbs + jobs/<job_name>_node.sh."""
import sys
sys.dont_write_bytecode = True
from xfam_common import *
nodes, s_oa, queue, wall, name = int(sys.argv[1]), float(sys.argv[2]), sys.argv[3], sys.argv[4], sys.argv[5]
C = 4 * nodes
rows = [(r, s_oa) for ds in DATASETS for sp in ['fit', 'cal', 'dev'] for r in jl(POP / f'{ds}_{sp}.jsonl')]
chains = [[] for _ in range(C)]; load = [0.0] * C
# contiguous greedy fill in paper order keeps each chain's rows in split order
total = sum(s for _, s in rows); target = total / C
i = 0
for r, s in rows:
    if load[i] + s > target * 1.0001 and i < C - 1 and chains[i]:
        i += 1
    chains[i].append(r); load[i] += s
W = X / 'records/work/run'; W.mkdir(parents=True, exist_ok=True)
plan = dict(utc=utc(), nodes=nodes, chains=C, sec_per_row=dict(obqa_arc=s_oa), receiver_env=(X / 'jobs/receiver.env').read_text(), queue=queue, walltime=wall, job=name, chain_files={})
for c, rs in enumerate(chains):
    p = W / f'chain_{c:02d}.jsonl'; assert not p.exists()
    with open(p, 'w') as f:
        for r in rs: f.write(json.dumps(r, ensure_ascii=False) + '\n')
    plan['chain_files'][p.name] = dict(n=len(rs), est_minutes=round(load[c] / 60, 1), sha256=sha(p),
                                       first=f"{rs[0]['dataset']}/{rs[0]['split']}/{rs[0]['id']}", last=f"{rs[-1]['dataset']}/{rs[-1]['split']}/{rs[-1]['id']}")
assert sum(v['n'] for v in plan['chain_files'].values()) == len(rows) == 5626
save(W / 'PLAN.json', plan)
J = X / 'jobs'
h, m, s = map(int, wall.split(':')); wall_s = h * 3600 + m * 60 + s
(J / f'{name}_node.sh').write_text(f'''#!/bin/bash
# X4 full run (sampled receiver answers): node shell (one per node via mpiexec); 4 single-GPU chains; records only, gold never read.
set -uo pipefail
X={X}
source "$HOME/.config/ClusterB-storage.sh"
source "$X/jobs/receiver.env"
PY="$DATA_ROOT/software/envs/c2c_official/bin/python"
export XFAM_DEADLINE_EPOCH="$1" PBS_JOBID="$2"
RANK="${{PALS_RANKID:-${{PMI_RANK:-x}}}}"
export PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 TOKENIZERS_PARALLELISM=false CUDA_DEVICE_ORDER=PCI_BUS_ID
export HF_HUB_OFFLINE=1 HF_DATASETS_OFFLINE=1 TRANSFORMERS_OFFLINE=1 OMP_NUM_THREADS=4 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
export http_proxy=http://proxy.cluster.invalid:3128 https_proxy=http://proxy.cluster.invalid:3128 HTTP_PROXY=http://proxy.cluster.invalid:3128 HTTPS_PROXY=http://proxy.cluster.invalid:3128
if [ -n "${{X3_PYTHONPATH:-}}" ]; then export PYTHONPATH="$X3_PYTHONPATH"; else unset PYTHONPATH; fi
export TMPDIR="$X/cache/tmp" TMP="$X/cache/tmp" TEMP="$X/cache/tmp"
L="$X/logs/jobs/{name}"; mkdir -p "$L" "$X/results/runs"
{{ echo "NODE_START_UTC=$(date -u +%Y-%m-%dT%H:%M:%SZ) rank=$RANK host=$(hostname) X3_RECEIVER=$X3_RECEIVER PYTHONPATH=${{PYTHONPATH:-}}"; nvidia-smi -L; }} > "$L/node${{RANK}}.txt" 2>&1
cd "$X/src" || exit 3
PIDS=()
for g in 0 1 2 3; do
  c=$(printf '%02d' $((RANK * 4 + g)))
  [ -f "$X/records/work/run/chain_$c.jsonl" ] || continue
  ( export CUDA_VISIBLE_DEVICES=$g
    "$PY" run_x4.py --mode run --receiver "$X3_RECEIVER" --sampling on --rows "$X/records/work/run/chain_$c.jsonl" --out "$X/results/runs/chain_$c.jsonl"; echo "EXIT chain_$c $?" ) > "$L/chain_$c.log" 2>&1 &
  PIDS+=($!)
done
wait "${{PIDS[@]}}"
echo "NODE_END_UTC=$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "$L/node${{RANK}}.txt"
''')
(J / f'{name}.pbs').write_text(f'''#!/bin/bash
# [scheduler directive removed for anonymity]
# [scheduler directive removed for anonymity]
# [scheduler directive removed for anonymity]
# [scheduler directive removed for anonymity]
# [scheduler directive removed for anonymity]
# X4 full run, sampled ({C} single-GPU chains on {nodes} node(s)); plan: records/work/run/PLAN.json
# Submit: submit-job  -q {queue} -l select={nodes} -l walltime={wall} -l fsreq=<fs> -N {name} {name}.pbs
set -uo pipefail
START=$(date +%s); DEADLINE=$((START + {wall_s} - 240))
mpiexec -n {nodes} --ppn 1 --hostfile "$PBS_NODEFILE" --cpu-bind none bash {J}/{name}_node.sh "$DEADLINE" "${{PBS_JOBID:-none}}"
echo "MPIEXEC_EXIT=$? $(date -u +%Y-%m-%dT%H:%M:%SZ)" >> {X}/logs/jobs/{name}_pbs_stdout.log
cd {X}/results/runs && {{ sha256sum chain_*.jsonl chain_*.env.json; echo "# utc=$(date -u +%Y-%m-%dT%H:%M:%SZ) job=${{PBS_JOBID:-none}}"; }} > MANIFEST.sha256
''')
print(json.dumps({k: v for k, v in plan.items() if k != 'chain_files'}, indent=1))
for k, v in plan['chain_files'].items(): print(k, v['n'], v['est_minutes'], v['first'], '->', v['last'])
