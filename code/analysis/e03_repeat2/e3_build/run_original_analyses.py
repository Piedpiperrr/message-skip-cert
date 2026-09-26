"""Run each E3 replay's ORIGINAL src/analyze.py on the login node through a thin adapter (DEVIATIONS D7 + each E3 folder).

The analyze.py files are executed as-is except for exact-string substitutions (each asserted present) that
 - write every output to <stage>/results/ (REPEAT; linked as <E3 folder>/results/<stage>) or <E3 folder>/results/ (FULL) instead of the stage's
   summary/, records/, evidence/ and top-level files, so no record or stage file is created or modified;
 - large: skip common.compute() (it asserts a ClusterA compute hostname); instead the adapter asserts that every record's
   job_id equals execution_clearance.json's job_id;
 - MMLU-Pro and FULL: read the job ledger (job_state F, job_id) from the scheduler's own record, `job-status -x -f -F json`,
   saved to results/.../RESOURCE_LEDGER_from_qstat.json, instead of the login-node supervisor's RESOURCE_LEDGER.json
   that the original stage wrote.
usage: run_original_analyses.py <E3 folder> [stage ...]
"""
import sys, os, json, subprocess, pathlib, hashlib
sys.dont_write_bytecode = True
F = pathlib.Path(sys.argv[1]).resolve()
FULL = F.name.startswith('P2_R1_E3POL_MMLU_C2C_FULL')
STAGES = sys.argv[2:] or (['full'] if FULL else ['large', 'medium', 'mmlu'])
PY = '$DATA_DIR/software/envs/c2c_official/bin/python'

COMMON_SUMMARY = [("P/f'summary/", "R/f'summary/", 'any'), ("P/'summary/", "R/'summary/", 'any')]
SUBS = {
    'large': [("compute();assert (P/'REPLAY_COMPLETE.json').exists()", "assert (P/'REPLAY_COMPLETE.json').exists()", 1),
              ("writejl(P/'records/paired_e2e_512.jsonl'", "writejl(R/'records/paired_e2e_512.jsonl'", 1),
              ("save(P/'NUMERICAL_VALIDATION.json'", "save(R/'NUMERICAL_VALIDATION.json'", 1),
              ("freeze('ANALYSIS_FREEZE.json',list((P/'summary').glob('*'))+[P/'records/paired_e2e_512.jsonl',P/'NUMERICAL_VALIDATION.json'])",
               "save(R/'ANALYSIS_FREEZE.json',dict(utc=utc(),files={str(p.relative_to(R)):sha(p) for p in list((R/'summary').glob('*'))+[R/'records/paired_e2e_512.jsonl',R/'NUMERICAL_VALIDATION.json']}))", 1)]
             + COMMON_SUMMARY,
    'medium': [("write_rows(P/'records/", "write_rows(R/'records/", 'all'), ("save(P/'ANALYSIS_COMPLETE.json'", "save(R/'ANALYSIS_COMPLETE.json'", 1)]
              + COMMON_SUMMARY,
    'mmlu': [("resource=read(P/'RESOURCE_LEDGER.json')", "resource=read(R/'RESOURCE_LEDGER_from_qstat.json')", 1),
             ("save(P/'evidence/ANALYSIS_START.json'", "save(R/'evidence/ANALYSIS_START.json'", 1),
             ("P/'NUMERICAL_VALIDATION.json'", "R/'NUMERICAL_VALIDATION.json'", 'all'),
             ("write_rows(P/'records/", "write_rows(R/'records/", 'all'), ("save(P/'ANALYSIS_COMPLETE.json'", "save(R/'ANALYSIS_COMPLETE.json'", 1)]
            + COMMON_SUMMARY,
}
SUBS['full'] = SUBS['mmlu']

RUNNER = r'''
import sys, os, pathlib
sys.dont_write_bytecode = True
stage, R, code = sys.argv[1], pathlib.Path(sys.argv[2]), open(sys.argv[3]).read()
os.chdir(stage); sys.path.insert(0, stage + '/src')
g = {'__name__': '__main__', '__file__': stage + '/src/analyze.py', 'R': R}
exec(compile(code, stage + '/src/analyze.py [E3 ClusterA login-node adapter]', 'exec'), g)
'''

for st in STAGES:
    P = F if st == 'full' else F / st
    R = P / 'results'  # inside the stage copy: the medium/MMLU-Pro write helpers assert outputs stay under P; <E3 folder>/results/<stage> links here
    if st != 'full':
        (F / 'results').mkdir(exist_ok=True); link = F / 'results' / st
        if not link.is_symlink(): link.symlink_to(f'../{st}/results')
    for d in ['summary', 'records', 'evidence']:
        (R / d).mkdir(parents=True, exist_ok=True)
    code = (P / 'src/analyze.py').read_text()
    for old, new, n in SUBS[st]:
        c = code.count(old); assert n == 'any' or (c >= 1 and (n == 'all' or c == n)), (st, old, c)
        code = code.replace(old, new)
    assert "P/'summary" not in code and "P/f'summary" not in code and "(P/'summary')" not in code, st
    recs = P / ('records/e2e_requests.jsonl' if st in ('large', 'medium') else 'records/four_arm_requests.jsonl')
    jobs = {json.loads(l)['job_id'] for l in open(recs)}
    assert len(jobs) == 1, jobs
    jid = jobs.pop()
    if st == 'large':
        assert json.loads((P / 'execution_clearance.json').read_text())['job_id'] == jid
    if st in ('mmlu', 'full'):
        q = json.loads(subprocess.run(['job-status', '-x', '-f', '-F', 'json', jid], capture_output=True, text=True, check=True).stdout)
        j = q['Jobs'][jid]; j.pop('Variable_List', None)
        (R / 'RESOURCE_LEDGER_from_qstat.json').write_text(json.dumps(dict(job_id=jid, job_state=j['job_state'], Exit_status=j.get('Exit_status'),
            queue=j['queue'], exec_host=j['exec_host'], stime=j.get('stime'), obittime=j.get('obittime'),
            resources_used=j.get('resources_used'), source='job-status -x -f -F json (login node)'), indent=2) + '\n')
    tmp = R / 'evidence/analyze_adapted.py'; tmp.write_text(code)
    env = dict(os.environ, CUDA_VISIBLE_DEVICES='', PYTHONDONTWRITEBYTECODE='1', OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='1', MKL_NUM_THREADS='1')
    r = subprocess.run([PY, '-c', RUNNER, str(P), str(R), str(tmp)], capture_output=True, text=True, env=env, timeout=600)
    (R / 'evidence/analyze_stdout.txt').write_text(r.stdout + '\n--- stderr ---\n' + r.stderr)
    print(st, 'rc', r.returncode, 'job', jid, (r.stderr.strip().splitlines() or [''])[-1][:300], flush=True)
