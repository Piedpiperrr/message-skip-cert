"""汇总已有计时证据；未单独测量的管理耗时保留空值，不补造分项。"""
import json
from common_p2_10 import ROOT,readrows,save,utc

def main():
    entries=[]
    for pair in ['large','small']:
        for dataset in ['obqa','arc']:
            out=ROOT/'results'/pair/dataset
            for split in ['train','dev' if dataset=='obqa' else 'validation']:
                rows=[r for r in readrows(out/f'{split}_cases.jsonl') if r['runtime_error'] is None]
                entries.append({'pair':pair,'dataset':dataset,'split':split,'requests':len(rows),'action_seconds':sum(r['latency_ms'] for r in rows)/1000,'extra_diagnostics_seconds':sum(r['diagnostics_ms'] for r in rows)/1000})
    overhead=[];fits=[]
    for pair in ['large','small']:
        for dataset in ['obqa','arc']:
            rows=readrows(ROOT/'results'/pair/dataset/'router_overhead.jsonl')
            fit=json.loads((ROOT/'results'/pair/dataset/'fit_info.json').read_text())
            fits.extend({'pair':pair,'dataset':dataset,'family':f,'head_fit_seconds':v['seconds']} for f,v in fit.items())
            overhead.append({'pair':pair,'dataset':dataset,'measurements':len(rows),'seconds':sum(r['overhead_ms'] for r in rows)/1000})
    ledger=json.loads((ROOT/'evidence/submissions.json').read_text());loads=[];segments=[]
    run_root=ROOT.parents[2]/'runs/iclr2027_p2'/ROOT.name
    for job in ledger:
        run=run_root/job['job_id']
        for pair in ['large','small']:
            path=run/f'{pair}_load.json'
            if path.exists():
                data=json.loads(path.read_text());loads.append({'job_id':job['job_id'],'pair':pair,**data['load_times']})
        path=run/'segment_complete.json'
        if path.exists():segments.append({'job_id':job['job_id'],**json.loads(path.read_text())})
    wm=json.loads((ROOT/'results/large/W/final_receipt.json').read_text())['metrics']
    save(ROOT/'evidence/timing_accounting.json',{'utc':utc(),'formal_actions':entries,'online_router_overhead':overhead,'backbone_and_fuser_loads':loads,'C4_extraction_seconds':wm['extraction_this_job_seconds'],'W_training_seconds_including_recovery_writes':wm['training_this_job_seconds'],'python_segments':segments,'scoring_seconds':None,'result_log_write_seconds':None,'smoke_seconds':None,'router_head_fits':fits,'router_feature_preparation_seconds':None,'unmeasured_detail_note':'评分、结果日志、smoke与离线特征准备在热请求完整计时外，并计入PBS实际耗时；没有各自独立的毫秒计数，不以时间戳差补造，也不为非核心分项重跑动作。W训练计时包含其自身恢复状态写入，不与日志重复求和。'})
    print('P2_10_TIMING_ACCOUNTING_SAVED')

if __name__=='__main__':main()
