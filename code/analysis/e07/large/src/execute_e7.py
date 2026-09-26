"""E7 four-arm replay driver (new file; the frozen execute.py of each stage is not used and not edited).

Arms per deployed policy, on the frozen 128-question panel, rotated by question ordinal:
  1 FIXED    - the fixed reference, frozen Runtime.action, no probe.
  2 ORIGINAL - the deployed policy: frozen Runtime.probe (use_cache=False) then a fresh complete request.
  3 REUSE    - probe with the prefill cache kept and cropped to the native R prompt; on omitted
               questions the receiver-only answer continues from that cache; kept questions run arm 2.
  4 ARGMAX   - on omitted questions (q_A of E7_ARGMAX_RECERT.json) the probe argmax label is the
               answer and no R request is made; kept questions run arm 2.

Arms 1 and 2 call the frozen probe()/action() exactly as the frozen driver of this stage does.
"""
import os, sys, json, time, hashlib, traceback
from pathlib import Path
sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common as C

P = C.P
KIND = os.environ['E7_KIND']
RECERT = Path(os.environ['E7_RECERT'])
OUTD = P / os.environ.get('E7_RECORDS', 'records_e7')
OUTD.mkdir(parents=True, exist_ok=True)
REQ = OUTD / 'e7_requests.jsonl'
ATT = OUTD / 'attempts.jsonl'
ARMS = ['fixed', 'original', 'reuse', 'argmax']
NPANEL = int(os.environ.get('E7_NPANEL', '128'))
SMOKE = os.environ.get('E7_SMOKE') == '1'


def utc(): return C.utc()
def read(p): return C.read(p)
def jl(p):
    with Path(p).open() as f: return [json.loads(s) for s in f if s.strip()]
def save(p, v): return C.save(p, v)
def append(p, v): return C.append(p, v)


POLICIES = {'large': [('obqa', 'T'), ('obqa', 'C'), ('arc', 'T'), ('arc', 'C')],
            'medium': [('obqa', 'C'), ('arc', 'C')],
            'mmlu': [('mmlu_pro', 'T'), ('mmlu_pro', 'C')]}[KIND]
SETTING = {'large': 'large/%s/%s', 'medium': 'medium/%s/%s', 'mmlu': 'large/%s/%s'}[KIND]

recert = {s['setting']: s for s in read(RECERT)['settings']}


def panel_rows(ds):
    if KIND == 'mmlu':
        rows = jl(P / 'inputs/panel_queries.jsonl')
        ids = read(P / 'inputs/candidate_e2e128_ids.json')
    else:
        rows = jl(P / f'inputs/{ds}_queries.jsonl')
        ids = read(P / f'inputs/{ds}_panel_ids.json')
    assert [r['id'] for r in rows] == ids and len(ids) == 128
    return rows[:NPANEL]


def threshold_for(ds, b):
    if KIND == 'large':
        return read(P / f'protocol/large_{ds}_{b}_deployment.json')['threshold']
    if KIND == 'medium':
        return read(C.FREEZE)['deployments'][ds]['threshold']
    return C.THRESHOLD


def deployed_q(ds, b):
    if KIND == 'large':
        return read(P / f'protocol/large_{ds}_{b}_deployment.json')['q']
    if KIND == 'medium':
        return read(C.FREEZE)['deployments'][ds]['q']
    return .4


# ---- runtime -------------------------------------------------------------------------------------
if KIND == 'large':
    import importlib.util as _iu
    CFG = C.CFG
    _s = _iu.spec_from_file_location('frozen_parser', CFG['parser_path'])
    parser = _iu.module_from_spec(_s); _s.loader.exec_module(parser)
    assert C.sha(CFG['parser_path']) == CFG['parser_sha256']
    from native_adapter import Runtime, sync
    from receiver_prompt import receiver_prompt, display_labels
    expected = {(ds, b): {r['id']: r for r in jl(P / f'inputs/large_{ds}_{b}_expected_routes.jsonl')}
                for ds, b in POLICIES}
else:
    import native_runtime as NR
    from native_runtime import Runtime, sync
    receiver_prompt, display_labels = NR.prompt.receiver_prompt, NR.prompt.display_labels
    expected = {}

import e7_arms


def frozen_probe(rt, q):
    """The frozen probe, called exactly as the frozen driver of this stage calls it."""
    if KIND == 'large':
        u, meta = rt.probe(q)
        return u, meta
    meta = rt.probe(q)
    return meta['ProbeMax'], meta


def frozen_action(rt, q, a):
    """The frozen action; for `large` the parser runs in the driver, as in the frozen execute.py."""
    if KIND == 'large':
        result = rt.action(q, a)
        parsed = parser.parse_answer(result['raw_answer'], q['choice_labels'])
        return result, parsed
    result = rt.action(q, a)
    return result['output'], result['parsed']


def parse_raw(raw, labels):
    return parser.parse_answer(raw, labels) if KIND == 'large' else NR.parser.parse_answer(raw, labels)


def build_q(row):
    """The query dict each stage's frozen driver builds, unchanged."""
    if KIND == 'large':
        return {k: row[k] for k in ['question_stem', 'choice_labels', 'choice_text']}
    if KIND == 'medium':
        return {'question_stem': row['question_stem'], 'choice_labels': list(row['choice_labels']),
                'choice_text': list(row['choice_text'])}
    return {k: (list(row[k]) if k in ['choice_labels', 'choice_text'] else row[k])
            for k in ['id', 'question_stem', 'choice_labels', 'choice_text']}


def run_one(rt, row, ds, b, arm, threshold, thr_A):
    """One timed request.  The outer synchronised wall timer covers input preparation, probe,
    selector, the complete native action including decode and parser V2, and cleanup."""
    if KIND == 'large':
        rt.begin()
    sync(); t0 = time.perf_counter()
    q = build_q(row)
    if KIND != 'large':
        rt.check_hooks()
    t1 = time.perf_counter()
    meta = None; cache = None; R_ids = None; n_R = None
    if arm == 'fixed':
        u = None
    elif arm == 'reuse':
        rt.in_probe = True
        meta, cache, R_ids, n_R = e7_arms.probe_keep_cache(rt, q, receiver_prompt, display_labels)
        rt.in_probe = False
        u = meta['ProbeMax']
    else:
        u, meta = frozen_probe(rt, q)
    t2 = time.perf_counter()
    cut = thr_A if arm == 'argmax' else threshold
    omitted = (arm != 'fixed') and (u <= cut)
    selected = b if arm == 'fixed' else ('R' if omitted else b)
    t3 = time.perf_counter()
    reuse_used = False; argmax_used = False
    if arm == 'argmax' and omitted:
        raw = meta['argmax_probe_label']
        parsed = parse_raw(raw, q['choice_labels'])
        result = {'raw_answer': raw, 'generated_token_ids': [], 'receiver_input_tokens': meta['input_tokens'],
                  'probe_argmax_answer': True}
        argmax_used = True
    elif arm == 'reuse' and omitted:
        raw, gen = e7_arms.generate_R_from_cache(rt, R_ids, cache)
        parsed = parse_raw(raw, q['choice_labels'])
        result = {'raw_answer': raw, 'generated_token_ids': gen, 'receiver_input_tokens': int(R_ids.shape[1]),
                  'continued_from_probe_cache': True, 'cache_cropped_to': n_R - 1}
        reuse_used = True
    else:
        result, parsed = frozen_action(rt, q, selected)
    t4 = time.perf_counter()
    if cache is not None:
        del cache
    if KIND == 'large':
        rt.end()
    else:
        rt.check_hooks()
    sync(); t5 = time.perf_counter()
    parts = dict(input_preparation_ms=(t1 - t0) * 1000, probe_ms=(t2 - t1) * 1000,
                 selector_ms=(t3 - t2) * 1000, action_decode_parse_ms=(t4 - t3) * 1000,
                 cleanup_ms=(t5 - t4) * 1000)
    gpu = None
    if KIND == 'large':
        # Outside the timer, exactly as the frozen driver: release the native diagnostics tensor
        # (validate_and_release pops `_projected`) and read the trace.
        result['selected'] = selected
        if not (reuse_used or argmax_used):
            rt.validate_and_release(result)
        else:
            rt.check_hooks()
        _, gpu = rt.trace_result()
    ident = None
    if meta is not None and (ds, b) in expected and row['id'] in expected[ds, b]:
        e = expected[ds, b][row['id']]
        ident = {'probe_ids_sha256_match': meta['probe_ids_sha256'] == e['probe_ids_sha256'],
                 'FP32_score_equal': meta['ProbeMax'] == e['ProbeMax'],
                 'route_match': (selected == e['route']) if arm in ('original', 'reuse') else None}
    return dict(selected=selected, omitted=bool(omitted), latency_ms=(t5 - t0) * 1000, parts_ms=parts,
                probe=meta, ProbeMax=u, raw_answer=result['raw_answer'], parsed=parsed,
                answer=parsed['answer'] if parsed['valid'] else 'INVALID', invalid=not parsed['valid'],
                output=result, frozen_identity=ident, probe_KV_reuse=reuse_used,
                probe_argmax_answer=argmax_used, GPU_forward_event_sum_ms=gpu, runtime_failure=False)


def main():
    assert os.environ.get('PBS_JOBID')
    assert not REQ.exists(), 'ONE FORMAL E7 REPLAY ONLY; no resume, no retry'
    t = time.perf_counter()
    rt = Runtime(); sync()
    save(P / 'evidence/E7_STARTUP.json', dict(utc=utc(), kind=KIND, job_id=os.environ['PBS_JOBID'],
         startup_wall_seconds=time.perf_counter() - t, load_seconds=rt.load_times,
         warmup_requests=0, synthetic_forward_requests=0, one_residency=True, smoke=SMOKE))
    print('E7_LOAD_PASS', KIND, json.dumps(rt.load_times), flush=True)
    attempt = 0; probes = 0; success = []; first = True
    started = time.perf_counter()
    expect = len(POLICIES) * NPANEL * 4
    for ds, b in POLICIES:
        rows = panel_rows(ds)
        threshold = threshold_for(ds, b)
        qdep = deployed_q(ds, b)
        s = SETTING % (ds, {'T': 'T', 'C': 'C'}[b])
        rec = recert[s]
        thr_A = rec['threshold_A']
        assert rec['q_A'] > 0 and thr_A is not None, ('no ARGMAX arm for', s)
        for ordinal, row in enumerate(rows):
            k = ordinal % 4
            order = ARMS[k:] + ARMS[:k]
            for position, arm in enumerate(order):
                C.stop_check(); attempt += 1; assert attempt <= expect
                if arm != 'fixed':
                    probes += 1
                key = f'{ds}|{b}|{row["id"]}|{arm}'
                append(ATT, dict(event='START', utc=utc(), key=key, attempt=attempt, arm=arm,
                                 panel_ordinal=ordinal, order_position=position,
                                 job_id=os.environ['PBS_JOBID']))
                try:
                    out = run_one(rt, row, ds, b, arm, threshold, thr_A)
                    append(REQ, dict(key=key, stage=KIND, setting=s, task=ds, reference=b, id=row['id'],
                                     panel_ordinal=ordinal, order_position=position, arm=arm,
                                     deployed_q=qdep, threshold=threshold, q_A=rec['q_A'], threshold_A=thr_A,
                                     cold_first_request=first, attempt=attempt, utc=utc(),
                                     job_id=os.environ['PBS_JOBID'], **out))
                    first = False
                    append(ATT, dict(event='SUCCESS', utc=utc(), key=key, attempt=attempt))
                    success.append(key)
                    if out['frozen_identity'] and not all(v for v in out['frozen_identity'].values() if v is not None):
                        raise RuntimeError('ONLINE_FROZEN_PROBE_IDENTITY_MISMATCH; record saved, no retry')
                    if attempt % 32 == 0:
                        el = time.perf_counter() - started
                        save(P / 'E7_PROGRESS.json', dict(utc=utc(), status='RUNNING', kind=KIND,
                             job_id=os.environ['PBS_JOBID'], complete=len(success), expected=expect,
                             attempts=attempt, probes=probes, elapsed_seconds=el,
                             ETA_remaining_seconds=el * (expect - len(success)) / max(1, len(success))))
                        print('E7_PROGRESS', KIND, len(success), '/', expect, flush=True)
                except BaseException as error:
                    append(ATT, dict(event='FAILURE', utc=utc(), key=key, attempt=attempt, error=repr(error)))
                    save(P / 'E7_FAILURE.json', dict(utc=utc(), kind=KIND, key=key, attempt=attempt,
                         error=repr(error), traceback=traceback.format_exc(), complete=len(success),
                         resubmit_allowed=False))
                    raise
    assert attempt == expect and len(set(success)) == expect
    save(P / 'E7_REPLAY_COMPLETE.json', dict(utc=utc(), status='COMPLETE', kind=KIND, smoke=SMOKE,
         job_id=os.environ['PBS_JOBID'], complete_requests=expect, policies=len(POLICIES),
         questions_per_panel=NPANEL, arms=ARMS, probe_requests=probes,
         requests_sha256=C.sha(REQ), attempts_sha256=C.sha(ATT),
         gold_read=False, retries=0, warmup=0, analysis_performed=False,
         elapsed_seconds=time.perf_counter() - started))
    print('E7_REPLAY_COMPLETE', KIND, expect, flush=True)


if __name__ == '__main__':
    main()
