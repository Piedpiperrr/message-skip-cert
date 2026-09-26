"""Archive-only correction: exclude the command's own still-growing stdout log.
No statistical checks, model execution, or raw dataset reads.
"""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from common import *
import tarfile,resource
resource.setrlimit(resource.RLIMIT_CPU,(120,121))
assert read(P/'FINAL_RECEIPT.json')['delivery_validation']=='PASS'
excluded={'SHA256SUMS','PACKAGE_RECEIPT.json','PACKAGE_SHA256SUMS','final_audit_command.log'}
files=[f for f in P.rglob('*') if f.is_file() and not f.is_symlink() and f.name not in excluded and not f.name.endswith('.tar.gz') and '__pycache__' not in f.parts]
for folder in ['paper','figures']:files.extend(f for f in (P/folder).rglob('*') if f.is_file())
files=sorted(set(files),key=lambda f:str(f.relative_to(P)))
(P/'SHA256SUMS').write_text(''.join(sha(f)+'  '+str(f.relative_to(P))+'\n' for f in files))
archive=P/(P.name+'_WORK_LIGHT.tar.gz')
with tarfile.open(archive,'w:gz',compresslevel=6,dereference=True) as tf:
 for f in files+[P/'SHA256SUMS']:tf.add(f,arcname=P.name+'/'+str(f.relative_to(P)),recursive=False)
with tarfile.open(archive,'r:gz') as tf:
 assert len(tf.getmembers())==len(files)+1
 for line in tf.extractfile(P.name+'/SHA256SUMS').read().decode().splitlines():
  h,rel=line.split('  ',1);assert hashlib.sha256(tf.extractfile(P.name+'/'+rel).read()).hexdigest()==h,rel
  assert sha(P/rel)==h,('LIVE_FILE_CHANGED',rel)
receipt={'utc':utc(),'archive':str(archive),'bytes':archive.stat().st_size,'sha256':sha(archive),'contained_file_count':len(files)+1,'archive_members_hash_verified':True,'live_SHA256SUMS_verified':True,'contains_weights':False,'full_raw_predictions_and_timing':True,'updated_actual_paper_included':True,'excluded_mutable_command_stdout':'evidence/final_audit_command.log; preserved locally, not a scientific record','scientific_records_or_rules_changed':False,'budget_closed':True}
save(P/'PACKAGE_RECEIPT.json',receipt)
(P/'PACKAGE_SHA256SUMS').write_text(sha(archive)+'  '+archive.name+'\n'+sha(P/'PACKAGE_RECEIPT.json')+'  PACKAGE_RECEIPT.json\n')
print(json.dumps(receipt,ensure_ascii=False))
