"""预执行边界条件检查：不读任何模型或项目分数。"""
from common import *
import math
from risk import thresholds,calibrate,mask
assert thresholds(list(range(21)))==[math.ceil(j*21/20)-1 for j in range(1,20)]+['Infinity']
cuts=thresholds([0.]*2100)
assert cuts==[0.]*19+['Infinity']
for n,expected in [(134,False),(135,True)]:
    led,dep=calibrate([0.]*n,[0]*n,cuts)
    assert all(x['routed']==n and x['changed']==0 and x['accepted']==expected for x in led)
    assert abs(led[0]['p_value']-.95**n)<1e-14
    assert abs(led[0]['CP_upper_0_999']-(1-.001**(1/n)))<1e-12
    assert dep['q']==(1. if expected else 0.)
led,dep=calibrate([1.]*448,[0]*448,cuts)
assert all(x['routed']==0 and x['p_value']==1 and x['CP_upper_0_999']==1 and not x['accepted'] for x in led[:-1])
assert dep['q']==1 and mask([float('nan')],1,'Infinity')==[True]
led,dep=calibrate([0.]*448,[1]*448,cuts)
assert dep['q']==0 and all(x['CP_upper_0_999']==1 for x in led)
assert mask([0.,0.,.1],.05,0.)==[True,True,False]
assert mask([0.],0,None)==[False]
save(P/'RISK_UNIT_CHECKS.json',{'status':'PASS','utc':utc(),'cases':['integer_rank_nondivisible_N','all_ties_retained','n134_reject_n135_accept_zero_changes','n0_p1_CP1','all_changes_reject','q1_fixed_R','q0_fixed_reference'],'project_questions_or_scores_used':False})
print('RISK_UNIT_CHECKS_PASS')
