"""E8 task 2(b), as its own process. Reproduces 16 saved large-pair MMLU-Pro fit rows with the
unchanged large configuration. Added after job 7638148 showed that a second Runtime() in the same
process cannot re-call torch.set_num_interop_threads; no frozen file is modified."""
import os,sys,traceback
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from common_e8 import *
import validate_smoke as vs

def main():
    V=P/'validation'/os.environ.get('E8_JOBTAG','local');V.mkdir(parents=True,exist_ok=True)
    from native_runtime_e8 import Runtime
    out={'slot':SLOT,'pair':'large','utc_start':utc(),'host':os.uname().nodename,
         'CUDA_VISIBLE_DEVICES':os.environ.get('CUDA_VISIBLE_DEVICES'),
         'note':'unchanged large-pair configuration; control for the pair substitution'}
    t=time.perf_counter();rt=Runtime('large');out['load_seconds']=round(time.perf_counter()-t,1)
    out['load_breakdown']=rt.load_times
    out['mechanical_smoke']=rt.mechanical_smoke()['status']
    acts,probes,src=vs.saved_large_mmlu()
    out['b_large_mmlu_bit_for_bit']=vs.reproduce(rt,'large_mmlu_pro_fit_bit_for_bit',
        project_queries(),acts,probes,ids('fit'),src)
    out['utc_end']=utc()
    save(V/'VALIDATION_large_control.json',out)
    print('LARGE_CONTROL b_match=',out['b_large_mmlu_bit_for_bit']['all_bit_for_bit'],flush=True)

if __name__=='__main__':
    try:main()
    except BaseException as exc:
        V=P/'validation'/os.environ.get('E8_JOBTAG','local');V.mkdir(parents=True,exist_ok=True)
        save(V/'VALIDATION_FAILURE_large_control.json',dict(utc=utc(),error=repr(exc),traceback=traceback.format_exc()))
        raise
