"""Split all X2 rows into single-GPU chains balanced by expected time (harness). Per-row seconds come from the smoke latencies.
usage: make_run_shards.py <n_nodes> <sec_per_row_obqa_arc> <sec_per_row_mmlu> <queue> <walltime HH:MM:SS> <job_name>
Writes records/work/run/chain_XX.jsonl, records/work/run/PLAN.json and jobs/<job_name>.pbs + jobs/<job_name>_node.sh."""
import sys
sys.dont_write_bytecode = True
from xfam_common import *
nodes, s_oa, s_mm, queue, wall, name = int(sys.argv[1]), float(sys.argv[2]), float(sys.argv[3]), sys.argv[4], sys.argv[5], sys.argv[6]
C = 4 * nodes
rows = [(r, s_mm if ds == 'mmlu_pro' else s_oa) for ds in DATASETS for sp in ['fit', 'cal', 'dev'] for r in jl(POP / f'{ds}_{sp}.jsonl')]
chains = [[] for _ in range(C)]; load = [0.0] * C
# contiguous greedy fill in paper order keeps each chain's rows in split order
total = sum(s for _, s in rows); target = total / C
i = 0
for r, s in rows:
    if load[i] + s > target * 1.0001 and i < C - 1 and chains[i]:
        i += 1
    chains[i].append(r); load[i] += s
W = X / 'records/work/run'; W.mkdir(parents=True, exist_ok=True)
plan = dict(utc=utc(), nodes=nodes, chains=C, sec_per_row=dict(obqa_arc=s_oa, mmlu_pro=s_mm), queue=queue, walltime=wall, job=name, chain_files={})
for c, rs in enumerate(chains):
    p = W / f'chain_{c:02d}.jsonl'; assert not p.exists()
    with open(p, 'w') as f:
        for r in rs: f.write(json.dumps(r, ensure_ascii=False) + '\n')
    plan['chain_files'][p.name] = dict(n=len(rs), est_minutes=round(load[c] / 60, 1), sha256=sha(p),
                                       first=f"{rs[0]['dataset']}/{rs[0]['split']}/{rs[0]['id']}", last=f"{rs[-1]['dataset']}/{rs[-1]['split']}/{rs[-1]['id']}")
assert sum(v['n'] for v in plan['chain_files'].values()) == len(rows) == 17267
save(W / 'PLAN.json', plan)
J = X / 'jobs'
h, m, s = map(int, wall.split(':')); wall_s = h * 3600 + m * 60 + s
(J / f'{name}_node.sh').write_text(f'''#!/bin/bash
# X2 full run: node shell (one per node via mpiexec); 4 single-GPU chains (receiver OLMo-2-7B); records only, gold never read.
set -uo pipefail
X={X}
source "$HOME/.config/ClusterB-storage.sh"
PY="$DATA_ROOT/software/envs/c2c_official/bin/python"
export XFAM_DEADLINE_EPOCH="$1" PBS_JOBID="$2"
RANK="${{PALS_RANKID:-${{PMI_RANK:-x}}}}"
export PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 TOKENIZERS_PARALLELISM=false CUDA_DEVICE_ORDER=PCI_BUS_ID
export HF_HUB_OFFLINE=1 HF_DATASETS_OFFLINE=1 TRANSFORMERS_OFFLINE=1 OMP_NUM_THREADS=4 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
export TMPDIR="$X/cache/tmp" TMP="$X/cache/tmp" TEMP="$X/cache/tmp"
L="$X/logs/jobs/{name}"; mkdir -p "$L" "$X/results/runs"
{{ echo "NODE_START_UTC=$(date -u +%Y-%m-%dT%H:%M:%SZ) rank=$RANK host=$(hostname)"; nvidia-smi -L; }} > "$L/node${{RANK}}.txt" 2>&1
cd "$X/src" || exit 3
PIDS=()
for g in 0 1 2 3; do
  c=$(printf '%02d' $((RANK * 4 + g)))
  [ -f "$X/records/work/run/chain_$c.jsonl" ] || continue
  ( export CUDA_VISIBLE_DEVICES=$g
    "$PY" run_x2.py --mode run --receiver olmo2_7b --rows "$X/records/work/run/chain_$c.jsonl" --out "$X/results/runs/chain_$c.jsonl"; echo "EXIT chain_$c $?" ) > "$L/chain_$c.log" 2>&1 &
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
# X2 full run ({C} single-GPU chains on {nodes} node(s)); plan: records/work/run/PLAN.json
# Submit: submit-job  -q {queue} -l select={nodes} -l walltime={wall} -l fsreq=<fs> -N {name} {name}.pbs
set -uo pipefail
START=$(date +%s); DEADLINE=$((START + {wall_s} - 240))
mpiexec -n {nodes} --ppn 1 --hostfile "$PBS_NODEFILE" --cpu-bind none bash {J}/{name}_node.sh "$DEADLINE" "${{PBS_JOBID:-none}}"
echo "MPIEXEC_EXIT=$? $(date -u +%Y-%m-%dT%H:%M:%SZ)" >> {X}/logs/jobs/{name}_pbs_stdout.log
''')
print(json.dumps({k: v for k, v in plan.items() if k != 'chain_files'}, indent=1))
for k, v in plan['chain_files'].items(): print(k, v['n'], v['est_minutes'], v['first'], '->', v['last'])
