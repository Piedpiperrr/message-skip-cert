import ast,hashlib,itertools,json,datetime,sys,re
from pathlib import Path
from scoring_v2 import parse_answer, VERSION, IMPLEMENTATION
O=Path(__file__).resolve().parent
S=Path('$DATA_DIR/P2_SCORE_SENSITIVITY_20260912T055929Z')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
checks=[]
def check(text,legal,expected,kind):
    r=parse_answer(text,list(legal)); ok=r['answer']==expected and r['valid']==(expected is not None)
    checks.append(dict(kind=kind,text=text,legal_labels=list(legal),expected=expected,actual=r['answer'],reason=r['reason'],pass_=ok))
    if not ok:print('FAIL',checks[-1],r,flush=True)
cases=[
 ('C. 70 km/h','C'),('C. v=d/t','C'),('A. 0°C','A'),('D. 120°C','D'),
 ('C=d/t',None),('sin x + cos y',None),('A cat can run.',None),('Carbon dioxide',None),
 ('The correct order of a sequence is A.','A'),('The correct scientific notation for this value is D.','D'),
 ('The best explanation for this phenomenon is B.','B'),('I choose C.','C'),('Option D is correct.','D'),
 ('The correct answer is A. The reason why this is the correct answer is because it follows.','A'),
 ('Answer: A. The answer is since the condition holds.','A'),
 ('The correct answer is A/B/C/D. The correct answer is A.','A'),
 ('D/B/A/C. The answer is C.','C'),('Answer: A/B. The answer is A.',None),
 ('A/B/C/D',None),('The answer is A/B/C/D.',None),('Answer: A and B.',None),
 ('Answer: A. Answer: B.',None),('Answer: A. Final answer: B.','B'),
 ('Answer: A. Actually, the answer is B.','B'),('Answer: A. Final answer: B. Answer: A.',None),
 ('Answer: A. Final answer: B. Answer: B.','B'),('Answer: A. Final answer: B or C.',None),
 ('Answer: A. The answer is A/B/C/D.',None),('A. Option B is also correct.',None),
 ('Answer: A/B/C/D/E. Answer: A.',None),('Answer: E.',None),('Answer: A. Answer: E.',None),
 ('He said "The answer is A."',None),('He said “The answer is A.”',None),
 ('> The answer is A.',None),('If the answer is A, proceed.',None),
 ('Suppose the correct order is A.',None),('The correct order is A if the condition holds.',None),
 ('The answer is not A.',None),('Answer: C. C is incorrect.',None),
 ('The answer is A. The answer is not A.',None),('The answer is A. Option B is wrong.','A'),
 ('C. Options A and B are wrong.','C'),('C. He said "The answer is A."','C'),
 ('The answer is a chemical compound.',None),('The answer is c.','C'),
 ('The correct formula is C=d/t.',None),('A. The correct formula is C=d/t.','A'),
 ('The answer is 1. one hydrogen.',None),('I cannot provide an answer to this question.',None),
 ('',None),('A. apple\nB. banana',None),('A. apple\nB. banana\nFinal answer: B.','B'),
 ('**C.** 70 km/h','C'),('```text\nAnswer: B.\n```','B')]
for text,expected in cases:check(text,'ABCD',expected,'syntax')
for perm in itertools.permutations('ABCD'):
    trans=str.maketrans(dict(zip('ABCD',perm)))
    for text,expected in [
        ('Answer: A/B/C/D. Answer: A.','A'),('Answer: A. Answer: B.',None),
        ('Answer: C.','C'),('The correct arrangement is D.','D'),
        ('Answer: A. Final answer: B.','B'),('A/B/C/D',None),('Answer: E.',None)]:
        permuted=re.sub(r'\b[A-D]\b',lambda m:m.group().translate(trans),text)
        check(permuted,perm,expected.translate(trans) if expected else None,'letter_permutation')
for legal in ['WXYZ','ABCDE']:
    a,b=legal[:2];check('Answer: '+ '/'.join(legal)+'. Answer: '+b+'.',legal,b,'legal_set')
    check('Answer: '+a+'. Answer: '+b+'.',legal,None,'legal_set')
for a in 'ABCD':
    for expr in ['70 km/h','70 kilometers per hour','0°C','120°C','v=d/t','sin(x)','tan(x)','cos(x)','x mod 3','using substances in an ecosystem model']:
        check(a+'. '+expr,'ABCD',a,'unit_formula_invariance')
    r=parse_answer('The answer is '+a+'.',list('ABCD'))
    for gold in 'ABCD':
        checks.append(dict(kind='synthetic_correct_wrong_symmetry',selected=a,synthetic_gold=gold,
                           pass_=r['valid'] and int(r['answer']==gold)==int(a==gold)))
# Only designated exposed boundary raw strings, never real gold or option semantics.
expected_by_source={('S007',3308):None,('S011',247):None,('S011',1062):None,
    ('S014',2689):None,('S014',7063):'A',('S014',8225):None,('S014',8226):'A',
    ('S018',1157):'A',('S018',1489):'D',('S018',2909):None,('S019',341):'A',
    ('S019',343):None,('S020',486):None,('S021',47):None}
seen=set()
for line in (S/'case_review.jsonl').open():
    r=json.loads(line);key=(r['source_id'],r['source_line'])
    if key in expected_by_source:
        check(r['raw_answer'],r['legal_labels'],expected_by_source[key],'exposed_boundary_raw');seen.add(key)
assert seen==set(expected_by_source)
tree=ast.parse((O/'scoring_v2.py').read_text())
fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='parse_answer')
assert [a.arg for a in fn.args.args]==['raw_answer','legal_labels']
assert not any(isinstance(n,ast.Name) and n.id in ['gold','id','pair','dataset','split','action','choice_text'] for n in ast.walk(fn))
report={'checks':len(checks),'passed':sum(c['pass_'] for c in checks),'failed':[c for c in checks if not c['pass_']],
        'parser_signature':['raw_answer','legal_labels'],'real_population_accuracy_computed':False,'cases':checks}
(O/'evidence/targeted_validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
if report['failed']:raise SystemExit('Targeted syntax check failed; no freeze/no population scoring')
receipt={'version':VERSION,'implementation':IMPLEMENTATION,'frozen_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'code_sha256':sha(O/'scoring_v2.py'),'rules_sha256':sha(O/'P2_SCORING_V2_RULES_ZH.md'),
    'validation_code_sha256':sha(__file__),'validation_result_sha256':sha(O/'evidence/targeted_validation.json'),
    'targeted_checks_passed':len(checks),'v2_population_statistics_started':False,
    'exposure_disclosure':'Revision followed review of exposed cases, gold and old/D1 outcomes; NOT globally blinded.',
    'rule_authority':'User-approved general V2 principles; no question-ID or method-specific scoring exceptions.',
    'revision_chain':[],'revision_policy':'At most one directed implementation correction for deviation from predetermined rules; never select by accuracy.',
    'parent_D1_freeze_path':str(S/'RULE_FREEZE_V1.json'),'parent_D1_freeze_sha256':sha(S/'RULE_FREEZE_V1.json')}
with (O/'RULE_FREEZE_V2.json').open('x') as f:json.dump(receipt,f,ensure_ascii=False,indent=2);f.write('\n')
print(json.dumps({k:v for k,v in receipt.items() if k!='exposure_disclosure'},ensure_ascii=False))
