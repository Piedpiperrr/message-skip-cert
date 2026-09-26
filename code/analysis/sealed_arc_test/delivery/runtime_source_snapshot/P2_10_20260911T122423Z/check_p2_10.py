"""提交前必要 CPU 检查：数据、计数、AC hook、消融、混合边界。无GPU运算。"""
import ast,itertools,json,types
from pathlib import Path
import numpy as np
import torch
from common_p2_10 import ROOT,readrows,save,sha,utc,ACTIONS
import ac_p2_10 as ac
from router_p2_10 import best_mixture,ConstantProbability,predict

def main():
    for p in ROOT.glob('*.py'):ast.parse(p.read_text())
    cfg=json.loads((ROOT/'prepared_config.json').read_text());req=readrows(ROOT/'data/request_manifest.jsonl')
    assert len(req)==len({r['key'] for r in req})==15860
    assert sum(r['action']=='acw' for r in req)==11252
    assert sum(r['action']!='acw' for r in req)==4608
    assert len({(r['pair'],r['dataset'],r['split'],r['id']) for r in req if r['panel']})==1536
    assert len({(r['pair'],r['dataset'],r['split'],r['id']) for r in req if r['panel'] and r['split']!='train'})==512
    assert set(tuple(x) for x in cfg['orders'])==set(itertools.permutations(ACTIONS))
    for d,ss in cfg['data'].items():
        for split,s in ss.items():
            rr=readrows(s['path']);ids=cfg['cost_panel'][d][split]['ids']
            from hashlib import sha256
            check=sorted([r['id'] for r in rr],key=lambda i:(sha256(f'P2_10_COST_PANEL_V1|{d}|{split}|{i}'.encode()).hexdigest(),i))[:len(ids)]
            assert ids==check
    # Drive the actual AC hook with CPU stand-ins; check full replacement once.
    class Block(torch.nn.Module):
        def forward(self,x,cache_position=None):return (x+1,)
    class Model(torch.nn.Module):
        def __init__(self,width):
            super().__init__();self.model=types.SimpleNamespace(layers=torch.nn.ModuleList([Block(),Block(),Block()]));self.device=torch.device('cpu');self.config=types.SimpleNamespace(hidden_size=width)
        def forward(self,input_ids,attention_mask,**kw):
            x=torch.zeros((1,input_ids.shape[1],self.config.hidden_size),dtype=torch.bfloat16)
            for b in self.model.layers:x=b(x)[0]
            raise AssertionError('helper must stop before subsequent blocks/head')
    runner=types.SimpleNamespace(helper=Model(2),receiver=Model(3),helper_tok=None,receiver_tok=None)
    original_prompt=ac.receiver_prompt_tensors;original_generate=ac.generate_receiver
    ac.receiver_prompt_tensors=lambda *args:('q','q',{'input_ids':torch.ones((1,4),dtype=torch.long),'attention_mask':torch.ones((1,4),dtype=torch.long)})
    W=torch.nn.Linear(2,3,bias=False,dtype=torch.float32);W.weight.data.fill_(2)
    def generated(model,tok,inputs):
        h=torch.zeros((1,4,3),dtype=torch.bfloat16);b=model.model.layers[1]
        pre=b(h,cache_position=torch.arange(4))[0]
        assert torch.equal(pre[:,:-1],torch.ones_like(pre[:,:-1]))
        assert torch.equal(pre[:,-1],torch.full_like(pre[:,-1],8))
        dec=b(torch.zeros((1,1,3),dtype=torch.bfloat16),cache_position=torch.tensor([4]))[0]
        assert torch.equal(dec,torch.ones_like(dec))
        return 'The correct answer is E',torch.tensor([1,2])
    ac.generate_receiver=generated
    try:
        result=ac.ac_request(runner,{},W,{'helper':{'block_index':1},'receiver':{'block_index':1}})
        ac.validate_result(result,'acw');assert result['audit']['injections']==1
        assert all(not m._forward_hooks for model in [runner.helper,runner.receiver] for m in model.model.layers)
    finally:ac.receiver_prompt_tensors=original_prompt;ac.generate_receiver=original_generate
    assert best_mixture([.1,.2,.3,.4],[1,2,3,4],.5)['status']=='infeasible'
    assert best_mixture([.5,.5,.5,.5],[1,1,1,1],1)['probabilities']==[1,0,0,0]
    m=best_mixture([0,1,.1,.2],[1,3,5,6],2);assert np.allclose(m['probabilities'],[.5,.5,0,0])
    class Cost:
        def predict(self,x):return np.zeros(x.shape[0])
    class Forbidden:
        def predict(self,x):raise AssertionError('A cost evaluated in 3-action ablation')
        def predict_proba(self,x):raise AssertionError('A correctness evaluated in 3-action ablation')
    b={'correctness':[ConstantProbability(1)]*3+[Forbidden()],'log_latency':[Cost()]*3+[Forbidden()],'c_ref_ms':1}
    p,c,ch=predict(b,np.zeros((2,1)),3);assert np.array_equal(ch,np.zeros((2,7),dtype=int))
    save(ROOT/'evidence/implementation_checks.json',{'utc':utc(),'passed':True,'requests':15860,'AC':11252,'new_RTC':4608,'panel_question_pairs':1536,'dev_panel_question_pairs':512,'hook_initial_prefill_once_full_vector':True,'hook_cleanup':True,'three_action_does_not_compute_A':True,'mixture_infeasible_and_ties':True,'parser_regression_not_repeated':True})
    print('CPU_IMPLEMENTATION_CHECKS_PASS')
if __name__=='__main__':main()
