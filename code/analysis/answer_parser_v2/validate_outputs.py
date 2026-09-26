"""Independent arithmetic over delivered labels and saved primary vectors."""
import json,csv,collections,hashlib,math,datetime
from pathlib import Path
O=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def rows(n):return list(csv.DictReader((O/n).open()))
freeze=json.loads((O/'RULE_FREEZE_V2.json').read_text())
assert sha(O/'scoring_v2.py')==freeze['code_sha256']
assert sha(O/'P2_SCORING_V2_RULES_ZH.md')==freeze['rules_sha256']
assert sha(O/'evidence/targeted_validation.json')==freeze['validation_result_sha256']
names={'R':'receiver_only','T':'text','C':'c2c','A':'acw'}
counts=collections.Counter();summaries={};uids={'full':set(),'panel':set()};question_count=0;label_checks=0
manifest=json.loads((O/'labels/LABEL_MANIFEST.json').read_text())
for f in manifest:
    path=O/f['relative_path'];assert sha(path)==f['sha256'];seen=set();n=0
    for line in path.open():
        r=json.loads(line);key=tuple(r[k] for k in ['population','pair','dataset','split']);qkey=(*key,r['id']);assert qkey not in seen;seen.add(qkey)
        assert (r['split']=='train')==(f['role']=='train');n+=1;question_count+=1
        assert r['scoring_version']=='P2_SCORING_V2' and r['parser_sha256']==freeze['code_sha256']
        ays=[]
        for a,name in names.items():
            o=r['o_'+a];v=r['valid_'+a];y=r['y_'+a]
            assert v==int(o in r['legal_labels']);assert y==int(v and o==r['gold'])
            assert r['f_'+a]==int(o!=r['o_R'])
            gain=int(y==1 and r['y_R']==0);harm=int(y==0 and r['y_R']==1)
            assert r['gain_'+a]==gain and r['harm_'+a]==harm
            assert r['zero_gain_'+a]==int(r['f_'+a] and not gain and not harm)
            assert r['invalid_'+a]==1-v
            assert r['invalid_flip_'+a]==int(r['f_'+a] and (not v or not r['valid_R']))
            s=r['source_'+a];uids[r['population']].add((s['source_id'],s['source_line']))
            counts[(*key,name,'correct')]+=y;counts[(*key,name,'valid')]+=v
            counts[(*key,name,'gain')]+=gain;counts[(*key,name,'harm')]+=harm
            ays.append(y);label_checks+=1
        counts[(*key,'union4')]+=int(any(ays));counts[(*key,'union3')]+=int(any(ays[:3]));counts[(*key,'n')]+=1
    assert n==f['question_rows']
assert len(uids['full'])==45008 and len(uids['panel'])==6144 and len(uids['full']&uids['panel'])==1536
for r in rows('action_summary.csv'):
    key=tuple(r[k] for k in ['population','pair','dataset','split']);a=r['action']
    for met in ['correct','valid']:assert counts[(*key,a,met)]==int(r['V2_'+met])
    assert counts[(*key,a,'gain')]==int(r['V2_gain_over_R']);assert counts[(*key,a,'harm')]==int(r['V2_harm_vs_R'])
for r in rows('complementarity.csv'):
    key=tuple(r[k] for k in ['population','pair','dataset','split'])
    for met in ['union3','union4']:assert counts[(*key,met)]==int(r['V2_'+met])
    best=max(counts[(*key,a,'correct')] for a in names.values())
    assert best==int(r['V2_best_fixed_correct'])
    assert counts[(*key,'union4')]-best==int(r['V2_gap'])
primary=collections.defaultdict(list)
for r in rows('primary_per_question.csv'):
    key=tuple(r[k] for k in ['population','pair','dataset','split','policy']);primary[key].append(r)
for r in rows('frozen_policy_rescoring.csv'):
    if r['population']=='full':assert not r['mean_ms'] and r['timing_source']=='accuracy_only'
    key=tuple(r[k] for k in ['population','pair','dataset','split','policy'])
    if key in primary:
        rr=primary[key];assert len(rr)==int(r['n'])
        for v in ['old','D1','V2']:assert math.isclose(sum(float(x[v+'_correct']) for x in rr),float(r[v+'_correct']),abs_tol=1e-8)
        if r['population']=='panel':assert math.isclose(sum(float(x['original_total_ms']) for x in rr)/len(rr),float(r['mean_ms']),abs_tol=1e-8)
    assert r['refitted_V2']=='False'
    if r['split']!='train':assert r['D1_correct']==r['V2_correct']
for r in rows('primary_three_four_replacements.csv'):
    if r['split']!='train':assert r['old_four_minus_three_correct']==r['V2_four_minus_three_correct'] and r['AC_exclusive_captured_V2']=='0'
    if r['population']=='panel' and r['split']!='train':assert float(r['V2_four_minus_three_correct'])==0
report={'status':'PASS_WITHIN_REQUESTED_SCOPE','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'label_question_rows_checked':question_count,'label_action_checks':label_checks,'source_overlap_AC':1536,
    'all_V2_action_counts_and_complementarity_recomputed':True,'primary_vectors_and_population_timing_separation_checked':True,
    'original_old_parser_replay_repeated':False,'frozen_parser_unchanged':True,'parser_post_freeze_corrections':0,
    'limitations':'Syntax tests plus exact delivered-label arithmetic; no semantic judge, new method fit, or independent test.',
    'validation_code_sha256':sha(__file__)}
(O/'evidence/output_validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(report,ensure_ascii=False))
