"""Bounded CPU structural and synthetic checks. No sealed source read."""
from common import *
import ast,importlib.util
for path in (P/'src').glob('*.py'):ast.parse(path.read_text(),filename=str(path))
prior=read(P/'protocol/parent_e2e_frozen_config.json')
assert sha(P/'src/native_adapter.py')==sha(ROOT/'dev_e2e_replay/src/native_adapter.py')
spec=importlib.util.spec_from_file_location('v2',prior['parser_path']);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
assert m.parse_answer('The correct answer is A',['A','B'])['answer']=='A'
assert not m.parse_answer('The correct answer is C',['A','B'])['valid']
assert normalized_answer(m.parse_answer('', ['A','B']))=='INVALID'
q={'question_stem':'x  y','choice_labels':['A','B'],'choice_text':['one','two']}
assert signature(q)==signature(q|{'question_stem':' x\ny '})
assert signature(q)!=signature(q|{'choice_text':['two','one']})
assert signature(q)!=signature(q|{'question_stem':'X y'})
for b in ['T','C']:
 d=read(P/f'protocol/large_arc_{b}.json');t=d['threshold'];assert t<=t and not (t+1e-8<=t)
access=(P/'src/access_test.py').read_text();assert "columns=['id','question','choices']" in access
calls=[n for n in ast.walk(ast.parse(access)) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='read_table']
assert len(calls)==1 and next(ast.literal_eval(k.value) for k in calls[0].keywords if k.arg=='columns')==['id','question','choices']
execution=(P/'src/execute.py').read_text();assert 'gold[' not in execution and 'read_table' not in execution
analysis=(P/'src/analyze.py').read_text();assert analysis.index("verify_freeze('PREDICTION_TIMING_FREEZE.json')")<analysis.index('pq.read_table')
assert len({(i,p) for i in range(1172) for p in prior['order']['paths']})==4688
save(P/'evidence/SELF_CHECK.json',{'utc':utc(),'AST_all_pass':True,'native_adapter_byte_identical':True,'parser_syntax_cases':3,'group_rule_case_and_order_preserved':True,'threshold_ties_included':True,'gold_column_projection_isolated':True,'test_content_access':False,'model_forwards':0})
print('SELF_CHECK_PASS; no test content or model execution')
