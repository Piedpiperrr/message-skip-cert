import json
from pathlib import Path
from common_p2_10 import ROOT,readrows,save,utc

def progress():
    ac=rtc=panel=devpanel=invalid=errors=0;parts={};cross=[]
    for pair in ['large','small']:
        for dataset in ['obqa','arc']:
            out=ROOT/'results'/pair/dataset
            for split in ['train','dev' if dataset=='obqa' else 'validation']:
                rr=readrows(out/f'{split}_cases.jsonl');ok=[r for r in rr if r['runtime_error'] is None]
                a=sum(r['action']=='acw' for r in ok);t=len(ok)-a;ac+=a;rtc+=t;errors+=len(rr)-len(ok);inv=sum(not r['scoring']['valid'] for r in ok);invalid+=inv
                blocks={}
                for r in ok:
                    if r['panel']:blocks.setdefault(r['id'],[]).append(r)
                good=0
                for i,b in blocks.items():
                    if len(b)==4:
                        if len({r['job_id'] for r in b})==len({r['block_id'] for r in b})==1:good+=1
                        else:cross.append([pair,dataset,split,i])
                panel+=good;devpanel+=good if split!='train' else 0
                parts[f'{pair}/{dataset}/{split}']={'AC':a,'RTC':t,'panel_complete':good,'runtime_errors':len(rr)-len(ok),'invalid_outputs':inv}
    records=json.loads((ROOT/'evidence/submissions.json').read_text());requested=sum(r['requested_node_seconds'] for r in records)
    state={'utc':utc(),'AC_complete':ac,'AC_target':11252,'RTC_complete':rtc,'RTC_target':4608,'panel_complete':panel,'panel_target':1536,'dev_panel_complete':devpanel,'dev_panel_target':512,'runtime_failures':errors,'retries':len(readrows(ROOT/'evidence/retry_attempts.jsonl')),'invalid_outputs':invalid,'smoke_attempts':len(readrows(ROOT/'evidence/smoke_attempts.jsonl')),'requested_node_seconds':requested,'remaining_request_node_seconds':21600-requested,'submissions':len(records),'large_W_final':(ROOT/'results/large/W/final_receipt.json').exists(),'routers_frozen':[f'{p}/{d}' for p in ['large','small'] for d in ['obqa','arc'] if (ROOT/'results'/p/d/'router_fit_receipt.json').exists()],'parts':parts,'cross_job_panel':cross}
    save(ROOT/'evidence/progress.json',state);return state
if __name__=='__main__':print(json.dumps(progress(),ensure_ascii=False))
