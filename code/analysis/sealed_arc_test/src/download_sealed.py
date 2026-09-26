"""One opaque pinned-file acquisition after Stage 0, without decoding columns."""
from common import *
import urllib.request
verify_freeze('PRE_TEST_FREEZE.json');assert read(P/'PRE_TEST_FREEZE.json')['ARC_TEST_ACCESSED'] is False
assert not (P/'evidence/DOWNLOAD_ATTEMPT.json').exists()
s=CFG['population'];dst=Path(s['local_file']);assert not dst.exists()
url=f"https://huggingface.co/datasets/{s['dataset']}/resolve/{s['revision']}/{s['file']}"
save(P/'evidence/DOWNLOAD_ATTEMPT.json',{'utc':utc(),'url':url,'destination':str(dst),'decode_columns':[],'pre_test_freeze_sha256':sha(P/'PRE_TEST_FREEZE.json')})
with urllib.request.urlopen(url,timeout=50) as r, dst.open('xb') as f:
 while True:
  b=r.read(65536)
  if not b:break
  f.write(b)
assert dst.stat().st_size==s['expected_bytes'] and sha(dst)==s['expected_sha256']
save(P/'evidence/SEALED_DOWNLOAD_RECEIPT.json',{'utc':utc(),'bytes':dst.stat().st_size,'sha256':sha(dst),'ARC_TEST_CONTENT_DECODED':False,'gold_decoded_or_associated':False,'opaque_download_only':True,'pre_test_freeze_sha256':sha(P/'PRE_TEST_FREEZE.json')})
print('OPAQUE_PINNED_DOWNLOAD_COMPLETE; no projected content read')
