"""Finalize only the light archive and checksums; never repeat state append or computation."""
from common import *
import tarfile,ast
assert read(P/'FINAL_RECEIPT.json')['status']=='COMPLETE'
for code in (P/'src').glob('*.py'):ast.parse(code.read_text(),filename=str(code))
excluded={'SHA256SUMS','DELIVERY_RECEIPT.json','finalize_stdout.json'}
files=sorted(f for f in P.rglob('*') if f.is_file() and not any(x in f.parts for x in ['__pycache__','matplotlib-cache']) and f.suffix!='.gz' and f.name not in excluded)
hashes={str(f.relative_to(P)):sha(f) for f in files}
(P/'SHA256SUMS').write_text(''.join(hashes[str(f.relative_to(P))]+'  '+str(f.relative_to(P))+'\n' for f in files))
archive=P/(P.name+'_WORK_LIGHT.tar.gz')
with tarfile.open(archive,'w:gz',compresslevel=4) as tar:
 for f in files+[P/'SHA256SUMS']:tar.add(f,arcname=P.name+'/'+str(f.relative_to(P)),recursive=False)
with tarfile.open(archive,'r:gz') as tar:
 for name,h in hashes.items():
  item=tar.extractfile(P.name+'/'+name);assert item is not None
  assert hashlib.sha256(item.read()).hexdigest()==h,name
 assert tar.extractfile(P.name+'/SHA256SUMS').read()==(P/'SHA256SUMS').read_bytes()
for name,h in hashes.items():assert sha(P/name)==h,name
r={'utc':utc(),'archive':str(archive),'bytes':archive.stat().st_size,'sha256':sha(archive),'file_count':len(files)+1,'status':'COMPLETE','all_disk_and_archive_members_match_SHA256SUMS':True,'excluded_runtime_stdout':'evidence/finalize_stdout.json','no_weights_or_full_vocab_logits':True}
save(P/'DELIVERY_RECEIPT.json',r);print(json.dumps(r))
