"""Model-free login-node dry check of the E3 ClusterA folders. Writes nothing into the stage folders.

Uses the real ClusterA 2-node debug job record of job 7634910 (job-status -f -F json, captured 2026-09-19) as the accept fixture.
Each stage check runs in its own subprocess (the stages share module names such as common/guard_checks).
"""
import sys, json, os, subprocess, copy, tempfile, pathlib, re
sys.dont_write_bytecode = True
ROOT = pathlib.Path('$DATA_DIR')
TS = sys.argv[1]
FOLDERS = {k: ROOT / f'P2_R1_E3POL_{k}_{TS}' for k in os.environ.get('ONLY', 'REPEAT1,REPEAT2,REPEAT3,MMLU_C2C_FULL').split(',')}
FIX = pathlib.Path(sys.argv[2])  # ClusterA_2node_job_7634910.json
PY = sys.executable
results = []


def ok(name, cond, detail=''):
    results.append((bool(cond), name, str(detail)[:300]))


def sh(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


# fixture: real record, walltime set to the E3 request (the record itself is the E1 job's 00:55:00 2-node debug job)
rec = json.loads(FIX.read_text())
jid = list(rec['Jobs'])[0]
job = rec['Jobs'][jid]
job['Resource_List']['walltime'] = '00:55:00'
job['queue'] = os.environ.get('FIX_QUEUE', job['queue'])
hosts = [h.split('/')[0] for h in job['exec_host'].split('+')]
nodefile = [h + '.cluster.invalid' for h in hosts]
one_node = copy.deepcopy(job); one_node['Resource_List']['nodect'] = 1; one_node['exec_host'] = job['exec_host'].split('+')[0]; one_node['exec_vnode'] = job['exec_vnode'].split('+')[0]
ClusterB_like = copy.deepcopy(job); ClusterB_like['queue'] = 'gpu-queue'; ClusterB_like['Resource_List']['ngpus'] = 2
long_wall = copy.deepcopy(job); long_wall['Resource_List']['walltime'] = '01:30:00'
fixtures = {'accept_ClusterA_2node': (job, hosts[0], nodefile, 'PASS'), 'accept_node2': (job, hosts[1], nodefile, 'PASS'),
            'reject_foreign_host': (job, 'compute-node', nodefile, 'BLOCKED'),
            'reject_one_node': (one_node, hosts[0], nodefile[:1], 'BLOCKED'),
            'reject_ClusterB_queue_ngpus': (ClusterB_like, hosts[0], nodefile, 'BLOCKED'),
            'reject_walltime_1h30': (long_wall, hosts[0], nodefile, 'BLOCKED')}

GUARD_TEST = r'''
import sys, json
sys.dont_write_bytecode = True
sys.path.insert(0, sys.argv[1])
from guard_checks import allocation_identity
fx = json.loads(sys.argv[2])
print(json.dumps({k: allocation_identity(j, h, n)['status'] for k, (j, h, n, _) in fx.items()}))
'''
FREEZE_TEST = r'''
import sys, os, json
sys.dont_write_bytecode = True
os.chdir(sys.argv[1]); sys.path.insert(0, sys.argv[1] + '/src')
import common
f = common.verify_freeze(include_weights=False)
print(json.dumps({'status': f.get('status'), 'ROOT': str(common.ROOT), 'P': str(common.P)}))
'''
LARGE_TEST = r'''
import sys, os, json, subprocess, socket, tempfile, pathlib
sys.dont_write_bytecode = True
stage, fx = sys.argv[1], json.loads(sys.argv[2])
os.chdir(stage); sys.path.insert(0, stage + '/src')
src = pathlib.Path(stage, 'src/pbs_entry.py').read_text().splitlines()
guard = '\n'.join(src[:9])   # lines 1-9: identity, scheduler, nodefile and cgroup guards (line 10+ touch files)
out = {}
for name, (job, host, nodes, want) in fx.items():
    jid = next(iter([k for k in [job.get('_jid')] if k]), None) or os.environ['FIXJID']
    os.environ['PBS_JOBID'] = jid
    nf = tempfile.NamedTemporaryFile('w', delete=False); nf.write('\n'.join(nodes) + '\n'); nf.close(); os.environ['PBS_NODEFILE'] = nf.name
    subprocess.check_output = lambda *a, **k: json.dumps({'Jobs': {jid: job}})
    socket.gethostname = lambda: host
    ns = {}
    try:
        exec(compile(guard, 'pbs_entry.py[1:9]', 'exec'), ns)
        out[name] = ['PASS', ns['match'], ns['ClusterA_match']]
    except AssertionError as e:
        out[name] = ['BLOCKED', repr(e)[:80]]
    os.unlink(nf.name)
print(json.dumps(out))
'''


def guard_status(stage_src):
    fx = {k: (j, h, n, w) for k, (j, h, n, w) in fixtures.items()}
    r = sh([PY, '-c', GUARD_TEST, str(stage_src), json.dumps(fx)])
    return json.loads(r.stdout) if r.returncode == 0 else {'ERROR': r.stderr[-500:]}


for name, F in FOLDERS.items():
    stages = {'large': F / 'large', 'medium': F / 'medium', 'mmlu': F / 'mmlu'} if name != 'MMLU_C2C_FULL' else {'full': F}
    # shell syntax
    for s in [F / 'run_e3pol_node.sh', *F.glob('*.pbs'), *[p / x for p in stages.values() for x in ['run_e2e.pbs', 'run_medium_stage2.pbs', 'run_mmlu_stage2.pbs'] if (p / x).exists()]]:
        r = sh(['bash', '-n', str(s)]); ok(f'{name} bash -n {s.relative_to(F)}', r.returncode == 0, r.stderr)
    for st, p in stages.items():
        tag = f'{name}/{st}'
        # python syntax (compile only, no bytecode written)
        bad = []
        for f in (p / 'src').glob('*.py'):
            try:
                compile(f.read_text(), str(f), 'exec')
            except SyntaxError as e:
                bad.append(f'{f.name}: {e}')
        ok(f'{tag} python compile src/*.py', not bad, bad)
        ok(f'{tag} records/ empty, no run_logs/', not any((p / 'records').iterdir()) and not (p / 'run_logs').exists())
        ok(f'{tag} home_check receipt PASSED (grep -q)', sh(['grep', '-q', 'Home space check: PASSED', str(p / 'evidence/pbs/home_check.txt')]).returncode == 0)
        script = p / {'large': 'run_e2e.pbs', 'medium': 'run_medium_stage2.pbs'}.get(st, 'run_mmlu_stage2.pbs')
        txt = script.read_text()
        ok(f'{tag} stage path points to this copy', f'="{p}"' in txt, [l for l in txt.splitlines() if 'export P2_STAGE=' in l or 'export P2_MEDIUM_EXEC=' in l])
        ok(f'{tag} no rg in stage script', not re.search(r'\brg\b', txt))
        if st == 'large':
            proto = json.loads((p / 'PROTOCOL_FREEZE.json').read_text()); impl = json.loads((p / 'IMPLEMENTATION_FREEZE.json').read_text())
            sys.path.insert(0, str(p / 'src'))
            import hashlib
            h = lambda x: hashlib.sha256(pathlib.Path(x).read_bytes()).hexdigest()
            ok(f'{tag} PROTOCOL_FREEZE files match', all(h(p / k) == v for k, v in proto['files'].items()), len(proto['files']))
            ok(f'{tag} IMPLEMENTATION_FREEZE files match', all(h(p / k) == v for k, v in impl['files'].items()), len(impl['files']))
            src_idx = json.loads((p / 'SOURCE_INDEX.json').read_text())
            size_ok = all(pathlib.Path(s['path']).stat().st_size == s['bytes'] for s in src_idx)
            small = [s for s in src_idx if s['sha256'] and s['bytes'] < 50_000_000]
            ok(f'{tag} SOURCE_INDEX sizes (all {len(src_idx)}) + sha (files <50 MB: {len(small)})', size_ok and all(h(s['path']) == s['sha256'] for s in small))
            os.environ['FIXJID'] = jid
            r = sh([PY, '-c', LARGE_TEST, str(p), json.dumps(fixtures)], env=dict(os.environ))
            res = json.loads(r.stdout) if r.returncode == 0 else {'ERROR': r.stderr[-800:]}
            ok(f'{tag} guard accept/reject (pbs_entry lines 1-9)', all(res.get(k, ['?'])[0] == w for k, (_, _, _, w) in fixtures.items()), res)
            sup = (p / 'src/supervise.py').read_text()
            ok(f'{tag} deadline = own start + 1800-60; phases validate+execute only', "stime=float(os.environ['R1E3_REPLAY_START_EPOCH']);deadline=stime+1800-60" in sup and "phases=[['validate_sources.py'],['execute.py']]" in sup)
            ok(f'{tag} ROOT fix', 'ROOT=P.parent.parent' in (p / 'src/common.py').read_text())
        else:
            r = sh([PY, '-c', FREEZE_TEST, str(p)])
            ok(f'{tag} verify_freeze(include_weights=False)', r.returncode == 0 and '"PASS"' in r.stdout, (r.stdout + r.stderr)[-300:])
            res = guard_status(p / 'src')
            ok(f'{tag} guard accept/reject (allocation_identity)', all(res.get(k) == w for k, (_, _, _, w) in fixtures.items()), res)
            pe = (p / 'src/pbs_entry.py').read_text()
            if st == 'medium':
                ok(f'{tag} deadline = own start + 900-45', "deadline=replay_start+900-45" in pe)
            else:
                ok(f'{tag} deadline = own start + 3600-45; date stop 2026-09-23', "deadline=replay_start+3600-45" in pe and 'datetime.datetime(2026,9,23' in pe)
            idx = json.loads(((p / 'MODEL_SOURCE_INDEX.json')).read_text())
            paths = [m.get('path') for m in idx['models'].values() if isinstance(m, dict) and m.get('path')]
            if st == 'medium':
                paths = [os.path.realpath(p / 'assets' / r_) for r_ in ['helper', 'receiver', 'fuser']]
            ok(f'{tag} model paths resolve ({len(paths)})', paths and all(pathlib.Path(x).exists() for x in paths), paths)
            if st in ('mmlu', 'full'):
                ok(f'{tag} ROOT', ("ROOT=P.parent.parent" in (p / 'src/common.py').read_text()) == (st == 'mmlu'))
    # dispatcher (job scripts): substitute exec with echo and run the case block for ranks 0/1
    for js in F.glob('P2R1_E3POL_*.pbs'):
        body = js.read_text()
        m = re.search(r"bash -c '\n(.*?)'\n", body, re.S)
        case = m.group(1).replace('exec bash', 'echo')
        got = [sh(['bash', '-c', case], env={**os.environ, 'PALS_RANKID': str(i)}).stdout.strip() for i in (0, 1)]
        ok(f'{name} {js.name} dispatch rank0/rank1', all(g.endswith('/run_e3pol_node.sh') for g in got), got)
        ok(f'{js.name} requests {os.environ.get("FIX_QUEUE","debug")} select=2 walltime 00:55:00', f"-q {os.environ.get('FIX_QUEUE','debug')} -l select=2 -l walltime=00:55:00" in body)
    ns = (F / 'run_e3pol_node.sh').read_text()
    ok(f'{name} node script: CUDA_VISIBLE_DEVICES=0,1, hardware record incl. topo -m and lscpu', 'CUDA_VISIBLE_DEVICES=0,1' in ns and 'nvidia-smi topo -m' in ns and 'lscpu' in ns and 'R1E3_REPLAY_START_EPOCH' in ns)

n_ok = sum(r[0] for r in results)
for r in results:
    print(('PASS ' if r[0] else 'FAIL ') + r[1] + ('' if r[0] else '  :: ' + r[2]))
print(f'DRY_CHECK {n_ok}/{len(results)} passed')
