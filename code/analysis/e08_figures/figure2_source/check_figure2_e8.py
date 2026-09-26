"""Verify the redrawn Figure 2 against the 18-cell truth table supplied with the E8 request.
Reads the rendering script's own ROWS/legend and the rendered PDF's text layer. No GPU, no queue."""
import ast,json,re,subprocess,sys,hashlib
from pathlib import Path
HERE=Path(__file__).resolve().parent;STAGE=HERE.parent
SCRIPT=HERE/'make_figure2_boundary.py';PDF=STAGE/'paper_active/figures/figure2_boundary.pdf'
src=SCRIPT.read_text()
tree=ast.parse(src)
WANT={'F','NE','POS','UNC','ROWS','TASKS'}
def names(t):
    if isinstance(t,ast.Name):return {t.id}
    if isinstance(t,(ast.Tuple,ast.List)):return set().union(*[names(e) for e in t.elts]) if t.elts else set()
    return set()
keep=[n for n in tree.body if isinstance(n,ast.Assign) and names(n.targets[0]) & WANT]
g={}
exec(compile(ast.Module(body=keep,type_ignores=[]),str(SCRIPT),'exec'),g)
ROWS=g['ROWS'];F,NE,POS,UNC=g['F'],g['NE'],g['POS'],g['UNC']

TRUTH={  # (pair, task, reference) -> (state, extra marks)
 ('small','OBQA','Text'):('fallback',[]),      ('small','OBQA','C2C'):('fallback',[]),
 ('small','ARC','Text'):('fallback',[]),       ('small','ARC','C2C'):('fallback',[]),
 ('small','MMLU-Pro','Text'):('fallback',[]),  ('small','MMLU-Pro','C2C'):('fallback',[]),
 ('medium','OBQA','Text'):('fallback',[]),     ('medium','OBQA','C2C'):('deploy+',['*']),
 ('medium','ARC','Text'):('fallback',[]),      ('medium','ARC','C2C'):('deploy+',[]),
 ('medium','MMLU-Pro','Text'):('fallback',[]), ('medium','MMLU-Pro','C2C'):('fallback',[]),
 ('large','OBQA','Text'):('deploy+',['‡']),    ('large','OBQA','C2C'):('deploy+',[]),
 ('large','ARC','Text'):('deploy+',[]),        ('large','ARC','C2C'):('deploy+',[]),
 ('large','MMLU-Pro','Text'):('deploy+',[]),   ('large','MMLU-Pro','C2C'):('deploy?',[]),
}
EXPECTED_COUNT={'small':'0/4 + 0/2','medium':'2/4 + 0/2','large':'4/4 + 2/2'}
TASKS=g['TASKS'];REFS=['Text','C2C']
# marks actually present in the script, by (pair, cell index)
marks={}
for m in re.finditer(r'if \(name, j\) == \("(\w+)", (\d+)\):.*?\n\s*ax\.annotate\("(.)"',src,re.S):
    marks.setdefault((m.group(1),int(m.group(2))),[]).append(m.group(3))

rows=[];fails=[]
for name,sizes,cells,count in ROWS:
    if count!=EXPECTED_COUNT[name]:fails.append(f'{name}: deployed label {count!r} != {EXPECTED_COUNT[name]!r}')
    for j,c in enumerate(cells):
        task=TASKS[j//2];ref=REFS[j%2]
        want,wmark=TRUTH[(name,task,ref)]
        got_mark=marks.get((name,j),[])
        ok = (c==want) and (sorted(got_mark)==sorted(wmark))
        rows.append(dict(pair=name,task=task,reference=ref,rendered=c,expected=want,
                         marks=''.join(got_mark),expected_marks=''.join(wmark),ok=ok))
        if not ok:fails.append(f'{name}/{task}/{ref}: rendered {c!r}{got_mark} != expected {want!r}{wmark}')
if any(c==NE for _,_,cells,_ in ROWS for c in cells):fails.append('a cell is still "not evaluated"')
# legend
leg=re.search(r'entries = \[(.*?)\]\n',src,re.S).group(1)
if 'not evaluated' in leg:fails.append('legend still lists "not evaluated"')
# PDF text layer
txt=subprocess.run(['pdftotext',str(PDF),'-'],capture_output=True,text=True).stdout
for needle in ['0/4 + 0/2','2/4 + 0/2','4/4 + 2/2','sealed test','fallback','deploy']:
    if needle not in txt:fails.append(f'PDF text layer missing {needle!r}')
if 'not evaluated' in txt or 'not\nevaluated' in txt:fails.append('PDF text layer still contains "not evaluated"')
size=subprocess.run(['pdfinfo',str(PDF)],capture_output=True,text=True).stdout
psize=re.search(r'Page size:\s+(\S+ x \S+) pts',size).group(1)
if psize!='396 x 108':fails.append(f'page size {psize} != 396 x 108')
out=dict(utc=__import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat(),
    script_sha256=hashlib.sha256(SCRIPT.read_bytes()).hexdigest(),
    pdf_sha256=hashlib.sha256(PDF.read_bytes()).hexdigest(),page_size_pts=psize,
    cells=rows,fallback_cells=sum(r['rendered']=='fallback' for r in rows),
    deploy_cells=sum(r['rendered'].startswith('deploy') for r in rows),
    not_evaluated_cells=sum(r['rendered']=='n/e' for r in rows),
    legend_entries=[e for e in re.findall(r'\("(\w+)", "([^"]+)"\)',leg)],
    deployed_labels={n:c for n,_,_,c in ROWS},failures=fails,status='PASS' if not fails else 'FAIL')
(STAGE/'CHECK_figure2_e8.json').write_text(json.dumps(out,indent=2,ensure_ascii=False)+'\n')
for r in rows:print(f"{r['pair']:7s} {r['task']:9s} {r['reference']:5s} -> {r['rendered']:8s}{r['marks']:2s} {'ok' if r['ok'] else 'MISMATCH'}")
print('deployed labels:',out['deployed_labels'])
print('legend:',[l for _,l in out['legend_entries']])
print('fallback/deploy/not-evaluated cells:',out['fallback_cells'],out['deploy_cells'],out['not_evaluated_cells'])
print('STATUS',out['status'],out['failures'])
sys.exit(0 if not fails else 1)
