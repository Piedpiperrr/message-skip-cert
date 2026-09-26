"""X1 full-run plan (harness): Text chains (Llama helper then receiver reading, same shard) and C2C chains (option-B evaluator,
one benchmark per chain), balanced by per-row seconds measured in the smoke test. One chain per GPU; 4 GPUs per node.
usage: make_x1_shards.py <nodes> <n_text> <n_c2c_obqa> <n_c2c_arc> <sec_text_row> <sec_c2c_obqa_row> <sec_c2c_arc_row> <queue> <walltime> <name>"""
import sys
sys.dont_write_bytecode = True
from x1_common import *
nodes, nt, nco, nca = map(int, sys.argv[1:5]); st, sco, sca = map(float, sys.argv[5:8]); queue, wall, name = sys.argv[8:11]
assert nt + nco + nca <= 4 * nodes
rows = {ds: [r for sp in ['fit', 'cal', 'dev'] for r in jl(X1POP / f'{ds}_{sp}.jsonl')] for ds in DS1}
allrows = rows['obqa'] + rows['arc']; assert len(allrows) == 5626


def split(rs, k):
    n = len(rs); cut = [round(i * n / k) for i in range(k + 1)]
    return [rs[cut[i]:cut[i + 1]] for i in range(k)]


R = X1 / 'records/work/run'; R.mkdir(parents=True, exist_ok=True)
J = X1 / 'jobs' / name; J.mkdir(parents=True, exist_ok=True)
chains, c = [], 0
for kind, ds, parts, sec in [('text', None, split(allrows, nt), st), ('c2c', 'obqa', split(rows['obqa'], nco), sco), ('c2c', 'arc', split(rows['arc'], nca), sca)]:
    for part in parts:
        f = R / f'{name}_chain_{c:02d}.jsonl'; assert not f.exists()
        with open(f, 'w') as fh:
            for r in part: fh.write(json.dumps(r, ensure_ascii=False) + '\n')
        chains.append(dict(chain=c, kind=kind, dataset=ds, rows=str(f), n=len(part), est_minutes=round(len(part) * sec / 60, 1), sha256=sha(f))); c += 1
for ch in chains:
    k = f"{ch['chain']:02d}"
    if ch['kind'] == 'text':
        cmd = (f'CUDA_VISIBLE_DEVICES=$G "$PY" run_x1_helper.py --mode run --rows {ch["rows"]} --out "$OUT/helper_chain_{k}.jsonl" && '
               f'CUDA_VISIBLE_DEVICES=$G "$PY" run_x1_receiver.py --mode run --rows {ch["rows"]} --messages "$OUT/helper_chain_{k}.jsonl" --out "$OUT/text_chain_{k}.jsonl"')
    else:
        cmd = (f'"$PY" run_x1_c2c.py --mode run --dataset {ch["dataset"]} --rows {ch["rows"]} --gpu $G --workdir "$OUT/c2c_chain_{k}_work" --out "$OUT/c2c_chain_{k}.jsonl"')
    (J / f'chain_{k}.sh').write_text(f'#!/bin/bash\n# X1 {ch["kind"]} chain {k} ({ch["n"]} rows, est {ch["est_minutes"]} min)\n{cmd}\necho "EXIT chain_{k} $?"\n')
h, m, s = map(int, wall.split(':')); wall_s = h * 3600 + m * 60 + s
(J / 'node.sh').write_text(f'''#!/bin/bash
set -uo pipefail
X1={X1}
source "$HOME/.config/ClusterB-storage.sh"
export PY="$DATA_ROOT/software/envs/c2c_official/bin/python" XFAM_DEADLINE_EPOCH="$1" PBS_JOBID="$2" OUT="$X1/results/runs"
RANK="${{PALS_RANKID:-${{PMI_RANK:-x}}}}"
export PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 TOKENIZERS_PARALLELISM=false CUDA_DEVICE_ORDER=PCI_BUS_ID
export HF_HUB_OFFLINE=1 HF_DATASETS_OFFLINE=1 TRANSFORMERS_OFFLINE=1 OMP_NUM_THREADS=4 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
export TMPDIR="$X1/../cache/tmp" TMP="$X1/../cache/tmp" TEMP="$X1/../cache/tmp"
L="$X1/logs/jobs/{name}"; mkdir -p "$L" "$OUT"
{{ echo "NODE_START_UTC=$(date -u +%Y-%m-%dT%H:%M:%SZ) rank=$RANK host=$(hostname)"; nvidia-smi -L; }} > "$L/node${{RANK}}.txt" 2>&1
cd "$X1/src" || exit 3
PIDS=()
for g in 0 1 2 3; do
  k=$(printf '%02d' $((RANK * 4 + g)))
  [ -f "{J}/chain_$k.sh" ] || continue
  ( export G=$g; bash "{J}/chain_$k.sh" ) > "$L/chain_$k.log" 2>&1 &
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
# X1 full run: {len(chains)} single-GPU chains on {nodes} node(s); plan {R}/{name}_PLAN.json
# Submit: submit-job  -q {queue} -l select={nodes} -l walltime={wall} -l fsreq=<fs> -N {name} {name}.pbs
set -uo pipefail
START=$(date +%s); DEADLINE=$((START + {wall_s} - 240))
mpiexec -n {nodes} --ppn 1 --hostfile "$PBS_NODEFILE" --cpu-bind none bash {J}/node.sh "$DEADLINE" "${{PBS_JOBID:-none}}"
echo "MPIEXEC_EXIT=$? $(date -u +%Y-%m-%dT%H:%M:%SZ)" >> {X1}/logs/jobs/{name}_pbs_stdout.log
''')
save(R / f'{name}_PLAN.json', dict(utc=utc(), nodes=nodes, queue=queue, walltime=wall, sec_per_row=dict(text=st, c2c_obqa=sco, c2c_arc=sca), chains=chains))
for ch in chains: print(ch['chain'], ch['kind'], ch['dataset'], ch['n'], ch['est_minutes'])
