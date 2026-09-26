"""E6 end-to-end replay (PROTOCOL_FREEZE_E6.md section 6), frozen 128-question OBQA panel.

Two arms, same protocol as E3: arm rotation by question ordinal, no warm-up, cold requests kept,
one outer synchronised wall timer per request, batch size 1, zero retries.

  fixed_TF  - Text+fact always.
  policy_TF - the frozen ProbeMax probe; ProbeMax <= threshold -> receiver-only R, else Text+fact.

Text+fact is the frozen large-pair Text action with one extra line "Useful fact: <fact1>" in the
HELPER's question block only; the receiver's first user turn keeps the original fact-free block, so
the receiver prompt is byte-identical to the frozen Text receiver prompt (E6 freeze section 1.0).
The frozen Runtime.probe and Runtime.action are imported and called unchanged.
"""
import os, sys, json, time, hashlib, traceback
from pathlib import Path
sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common as C
import pyarrow.parquet as pq
import torch

P = C.P
CFG = C.CFG
OUTD = P / os.environ.get('E6R_RECORDS', 'records_e6')
OUTD.mkdir(parents=True, exist_ok=True)
REQ = OUTD / 'e6_replay_requests.jsonl'
ATT = OUTD / 'attempts.jsonl'
ARMS = ['fixed_TF', 'policy_TF']
NPANEL = int(os.environ.get('E6R_NPANEL', '128'))
DS = Path('$DATA_DIR/c2c_reproduction_assets/datasets/allenai--openbookqa')
PARQUET = DS / 'additional/train-00000-of-00001.parquet'
PARQUET_SHA = 'd16d719e87efb86ed0a2ac4c8cdf380f7bfb94b602088393674c0a64ce9ed3d3'

import importlib.util as _iu
_s = _iu.spec_from_file_location('frozen_parser', CFG['parser_path'])
parser = _iu.module_from_spec(_s); _s.loader.exec_module(parser)
assert C.sha(CFG['parser_path']) == CFG['parser_sha256']
from native_adapter import Runtime, sync, native
lm = native.lm                       # legacy_methods, already imported by the frozen native runtime
import protocol_min                  # already in sys.modules for the same reason

# ---- the one E6 change: a flag on the helper prompt builder, default off ---------------------------
_frozen_format_openbook = lm.format_openbook
E6 = {'enabled': False, 'fact': None}


def format_openbook_e6(example, use_template=True):
    out = _frozen_format_openbook(example, use_template=use_template)
    if use_template or not E6['enabled']:
        return out                                   # receiver prompt path: untouched
    assert E6['fact'], 'fact line requested but no fact set'
    return 'Useful fact: ' + E6['fact'] + '\n' + out  # immediately before the question text


lm.format_openbook = format_openbook_e6
protocol_min.format_openbook = format_openbook_e6
# ---------------------------------------------------------------------------------------------------


def jl(p):
    with Path(p).open() as f: return [json.loads(s) for s in f if s.strip()]


def order_for(ordinal):
    k = ordinal % 2
    return ARMS[k:] + ARMS[:k]


@torch.inference_mode()
def action_text_plus_fact(rt, q, fact):
    """New method: runtime.Runner.request(q,'text') with the fact line added for the helper only."""
    E6['enabled'] = False
    frozen_body = _frozen_format_openbook(q, use_template=False)
    E6['enabled'] = True; E6['fact'] = fact
    try:
        message = rt.runner.th.run(q)
    finally:
        E6['enabled'] = False; E6['fact'] = None
    result = rt.runner.tr.consume(q, frozen_body, message['helper_message'])
    return {'raw_answer': result['generated_text'], 'generated_token_ids': result['generated_token_ids'],
            'receiver_input_tokens': result['receiver_input_token_count'],
            'helper_message': message['helper_message'], 'helper_body_with_fact': message['helper_body'],
            'helper_generated_token_ids': message['helper_generated_token_ids'],
            'helper_input_tokens': message['helper_input_token_count'],
            'frozen_receiver_body_sha256': hashlib.sha256(frozen_body.encode()).hexdigest()}


def run_one(rt, row, arm, fact, threshold):
    rt.begin(); sync(); t0 = time.perf_counter()
    q = {k: row[k] for k in ['question_stem', 'choice_labels', 'choice_text']}
    t1 = time.perf_counter()
    u = None; meta = None
    if arm == 'policy_TF':
        u, meta = rt.probe(q)
    t2 = time.perf_counter()
    omitted = (arm == 'policy_TF') and (u <= threshold)
    selected = 'R' if omitted else 'TF'
    t3 = time.perf_counter()
    if selected == 'R':
        result = rt.action(q, 'R')
    else:
        result = action_text_plus_fact(rt, q, fact)
    sync(); t4 = time.perf_counter()
    parsed = parser.parse_answer(result['raw_answer'], q['choice_labels'])
    t5 = time.perf_counter()
    rt.end(); sync(); t6 = time.perf_counter()
    parts = dict(input_preparation_ms=(t1 - t0) * 1000, probe_ms=(t2 - t1) * 1000,
                 selector_ms=(t3 - t2) * 1000, action_ms=(t4 - t3) * 1000,
                 parse_ms=(t5 - t4) * 1000, cleanup_ms=(t6 - t5) * 1000)
    result['selected'] = selected
    if selected == 'R':
        rt.validate_and_release(result)
    else:
        rt.check_hooks()
    _, gpu = rt.trace_result()
    return dict(selected=selected, omitted=bool(omitted), latency_ms=(t6 - t0) * 1000, parts_ms=parts,
                probe=meta, ProbeMax=u, raw_answer=result['raw_answer'], parsed=parsed,
                answer=parsed['answer'] if parsed['valid'] else 'INVALID', invalid=not parsed['valid'],
                output=result, GPU_forward_event_sum_ms=gpu, runtime_failure=False)


def main():
    assert os.environ.get('PBS_JOBID')
    assert not REQ.exists(), 'ONE FORMAL E6 REPLAY ONLY; no resume, no retry'
    assert C.sha(PARQUET) == PARQUET_SHA
    dep = C.read(P / 'protocol/e6_deployment.json')
    threshold = dep['threshold']
    assert dep['q'] > 0, 'E6 replay only exists when the certified q > 0'
    panel = jl(P / 'inputs/obqa_queries.jsonl')
    assert [r['id'] for r in panel] == C.read(P / 'inputs/obqa_panel_ids.json') and len(panel) == 128
    panel = panel[:NPANEL]
    facts = {r['id']: r['fact1'] for r in pq.read_table(PARQUET).to_pylist()}
    assert all(r['id'] in facts and facts[r['id']] for r in panel), 'fact1 missing on a panel question'

    # flag-off byte identity, before any model is loaded
    E6['enabled'] = False
    off = [_frozen_format_openbook(r, use_template=False) == format_openbook_e6(r, use_template=False)
           for r in panel[:5]]
    assert all(off), 'flag-off is not byte-identical'

    t = time.perf_counter(); rt = Runtime(); sync()
    C.save(P / 'evidence/E6R_STARTUP.json', dict(utc=C.utc(), job_id=os.environ['PBS_JOBID'],
           startup_wall_seconds=time.perf_counter() - t, load_seconds=rt.load_times,
           flag_off_byte_identical_5_panel_rows=all(off), warmup_requests=0, one_residency=True))
    print('E6R_LOAD_PASS', json.dumps(rt.load_times), flush=True)

    attempt = 0; success = []; first = True; started = time.perf_counter()
    expect = NPANEL * 2
    for ordinal, row in enumerate(panel):
        for position, arm in enumerate(order_for(ordinal)):
            C.stop_check(); attempt += 1; assert attempt <= expect
            key = f'obqa|{row["id"]}|{arm}'
            C.append(ATT, dict(event='START', utc=C.utc(), key=key, attempt=attempt, arm=arm,
                               panel_ordinal=ordinal, order_position=position, job_id=os.environ['PBS_JOBID']))
            try:
                out = run_one(rt, row, arm, facts[row['id']], threshold)
                C.append(REQ, dict(key=key, setting='large/OBQA/Text+fact', task='obqa', id=row['id'],
                                   panel_ordinal=ordinal, order_position=position, arm=arm,
                                   q=dep['q'], threshold=threshold, fact1=facts[row['id']],
                                   cold_first_request=first, attempt=attempt, utc=C.utc(),
                                   job_id=os.environ['PBS_JOBID'], **out))
                first = False
                C.append(ATT, dict(event='SUCCESS', utc=C.utc(), key=key, attempt=attempt))
                success.append(key)
                if attempt % 32 == 0:
                    print('E6R_PROGRESS', len(success), '/', expect, flush=True)
            except BaseException as error:
                C.append(ATT, dict(event='FAILURE', utc=C.utc(), key=key, attempt=attempt, error=repr(error)))
                C.save(P / 'E6R_FAILURE.json', dict(utc=C.utc(), key=key, attempt=attempt, error=repr(error),
                       traceback=traceback.format_exc(), complete=len(success), resubmit_allowed=False))
                raise
    assert attempt == expect and len(set(success)) == expect
    C.save(P / 'E6R_REPLAY_COMPLETE.json', dict(utc=C.utc(), status='COMPLETE', job_id=os.environ['PBS_JOBID'],
           complete_requests=expect, questions=NPANEL, arms=ARMS, q=dep['q'], threshold=threshold,
           requests_sha256=C.sha(REQ), attempts_sha256=C.sha(ATT), gold_read=False, retries=0, warmup=0,
           analysis_performed=False, elapsed_seconds=time.perf_counter() - started))
    print('E6R_REPLAY_COMPLETE', expect, flush=True)


if __name__ == '__main__':
    main()
