"""E16 Job B plan (E16-3 prefills): tier-ordered row lists per (receiver, dtype) process and the job scripts. Tier (1) = cal+dev of the certified
policies' receivers x benchmarks (Qwen3-8B: OBQA, ARC, MMLU-Pro; Qwen3-1.7B: OBQA, ARC); tier (2) = their fit splits; tier (3) = fallback-only
receivers x benchmarks (Qwen3-0.6B: all; Qwen3-1.7B: MMLU-Pro). Within a process rows run in tier order, so a deadline stop drops tiers from (3)
upward. Qwen3-8B fp32 rows are dealt round-robin (tier order kept) over 5 GPUs. -> records/work/jobB/*.jsonl, jobs/e16_jobB{.pbs,_node.sh}, notes/JOBB_PLAN.json"""
import sys
sys.dont_write_bytecode = True
from xfam_common import *
W = X / 'records/work'; B = W / 'jobB'; B.mkdir(parents=True, exist_ok=True)
R = lambda ds, sp: jl(W / f'e163_{ds}_{sp}.jsonl')
tiers = {'qwen3_8b': [('obqa', 'cal', 1), ('obqa', 'dev', 1), ('arc', 'cal', 1), ('arc', 'dev', 1), ('mmlu_pro', 'cal', 1), ('mmlu_pro', 'dev', 1),
                      ('obqa', 'fit', 2), ('arc', 'fit', 2), ('mmlu_pro', 'fit', 2)],
         'qwen3_1_7b': [('obqa', 'cal', 1), ('obqa', 'dev', 1), ('arc', 'cal', 1), ('arc', 'dev', 1), ('obqa', 'fit', 2), ('arc', 'fit', 2),
                        ('mmlu_pro', 'cal', 3), ('mmlu_pro', 'dev', 3), ('mmlu_pro', 'fit', 3)],
         'qwen3_0_6b': [(ds, sp, 3) for ds in ['obqa', 'arc', 'mmlu_pro'] for sp in ['cal', 'dev', 'fit']]}
ordered = {rec: [dict(r, tier=t) for ds, sp, t in tl for r in R(ds, sp)] for rec, tl in tiers.items()}
procs = []   # (node, gpu, [(receiver, dtype, rowsfile)])
def dump(name, rows):
    p = B / name
    with open(p, 'w') as f:
        for r in rows: f.write(json.dumps(r, ensure_ascii=False) + '\n')
    return str(p)
f8 = ordered['qwen3_8b']
shards = [dump(f'q8b_fp32_s{k}.jsonl', f8[k::5]) for k in range(5)]
for k in range(4): procs.append((0, k, [('qwen3_8b', 'fp32', shards[k])]))
procs.append((1, 0, [('qwen3_8b', 'fp32', shards[4])]))
procs.append((1, 1, [('qwen3_8b', 'bf16', dump('q8b_bf16.jsonl', f8)), ('qwen3_1_7b', 'bf16', dump('q17b_bf16.jsonl', ordered['qwen3_1_7b']))]))
procs.append((1, 2, [('qwen3_1_7b', 'fp32', dump('q17b_fp32.jsonl', ordered['qwen3_1_7b']))]))
procs.append((1, 3, [('qwen3_0_6b', 'bf16', dump('q06b_bf16.jsonl', ordered['qwen3_0_6b'])), ('qwen3_0_6b', 'fp32', dump('q06b_fp32.jsonl', ordered['qwen3_0_6b']))]))
plan = dict(utc=utc(), tiers={k: [list(x) for x in v] for k, v in tiers.items()}, processes=[dict(node=n, gpu=g, runs=[dict(receiver=a, dtype=b, rows=c, n=len(jl(c)), sha256=sha(c)) for a, b, c in runs]) for n, g, runs in procs])
save(X / 'notes/JOBB_PLAN.json', plan)
lines = []
for n, g, runs in procs:
    cmds = '; '.join(f'"$PY" e16_probe.py --receiver {a} --dtype {b} --mode run --rows {c} --out "$X/results/e163/{a}_{b}_{pathlib.Path(c).stem}.jsonl"; echo "EXIT {a} {b} $?"' for a, b, c in runs)
    lines.append(f'  [ "$RANK" = "{n}" ] && ( export CUDA_VISIBLE_DEVICES={g}; {cmds} ) > "$L/node{n}_gpu{g}.log" 2>&1 &\n  [ "$RANK" = "{n}" ] && PIDS+=($!)')
(X / 'jobs/e16_jobB_node.sh').write_text(f'''#!/bin/bash
# E16 Job B node shell (E16-3 prefills; plan notes/JOBB_PLAN.json). Records only; gold never read.
set -uo pipefail
X={X}
source "$HOME/.config/ClusterB-storage.sh"
PY="$DATA_ROOT/software/envs/c2c_official/bin/python"
export XFAM_DEADLINE_EPOCH="$1" PBS_JOBID="$2"
RANK="${{PALS_RANKID:-${{PMI_RANK:-x}}}}"
export PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 TOKENIZERS_PARALLELISM=false CUDA_DEVICE_ORDER=PCI_BUS_ID
export HF_HUB_OFFLINE=1 HF_DATASETS_OFFLINE=1 TRANSFORMERS_OFFLINE=1 OMP_NUM_THREADS=4 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
export http_proxy=http://proxy.cluster.invalid:3128 https_proxy=http://proxy.cluster.invalid:3128 HTTP_PROXY=http://proxy.cluster.invalid:3128 HTTPS_PROXY=http://proxy.cluster.invalid:3128
unset PYTHONPATH
export TMPDIR="$X/cache/tmp" TMP="$X/cache/tmp" TEMP="$X/cache/tmp"
L="$X/logs/jobs/jobB"; mkdir -p "$L" "$X/results/e163"
{{ echo "NODE_START_UTC=$(date -u +%Y-%m-%dT%H:%M:%SZ) rank=$RANK host=$(hostname)"; nvidia-smi -L; }} > "$L/node${{RANK}}.txt" 2>&1
cd "$X/src" || exit 3
PIDS=()
''' + '\n'.join(lines) + '''
wait "${PIDS[@]}"
echo "NODE_END_UTC=$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "$L/node${RANK}.txt"
''')
(X / 'jobs/e16_jobB.pbs').write_text(f'''#!/bin/bash
# [scheduler directive removed for anonymity]
# [scheduler directive removed for anonymity]
# [scheduler directive removed for anonymity]
# [scheduler directive removed for anonymity]
# [scheduler directive removed for anonymity]
# E16 Job B (ClusterA debug, 2 nodes): E16-3 prefills, bf16 (deployed) and fp32 (TF32 off), all Qwen3 receivers x OBQA/ARC/MMLU-Pro x fit/cal/dev, tier order.
# Submit: submit-job  -q debug -l select=2 -l walltime=00:50:00 -l fsreq=<fs> -N P2R7_E16_B e16_jobB.pbs
set -uo pipefail
X={X}
START=$(date +%s); DEADLINE=$((START + 3000 - 240))
if [ "$(sha256sum "$X/PREREG.md" | cut -d' ' -f1)" != "$(head -1 "$X/PREREG.sha256" | cut -d' ' -f1)" ]; then echo "PREREG_HASH_MISMATCH" >> "$X/logs/jobs/jobB_pbs_stdout.log"; exit 4; fi
mpiexec -n 2 --ppn 1 --hostfile "$PBS_NODEFILE" --cpu-bind none bash "$X/jobs/e16_jobB_node.sh" "$DEADLINE" "${{PBS_JOBID:-none}}"
echo "MPIEXEC_EXIT=$? $(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "$X/logs/jobs/jobB_pbs_stdout.log"
cd "$X/results" && {{ find e163 -type f | sort | xargs sha256sum; echo "# utc=$(date -u +%Y-%m-%dT%H:%M:%SZ) job=${{PBS_JOBID:-none}}"; }} > MANIFEST_jobB.sha256
''')
for p in plan['processes']: print(p['node'], p['gpu'], [(r['receiver'], r['dtype'], r['n']) for r in p['runs']])
