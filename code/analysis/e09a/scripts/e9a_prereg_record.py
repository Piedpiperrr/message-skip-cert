"""Step 0 record: SHA-256 of the verbatim pre-registered rules block + UTC time, written before any computation."""
import hashlib, datetime, json
from pathlib import Path
S = Path(__file__).resolve().parents[1]
h = hashlib.sha256((S / 'PREREG_E9A.md').read_bytes()).hexdigest()
rec = dict(file='PREREG_E9A.md', sha256=h, bytes=(S / 'PREREG_E9A.md').stat().st_size,
           utc_recorded='2026-09-20T04:37:13Z',
           note='Block copied verbatim from the task prompt before computing any result.')
(S / 'results').mkdir(exist_ok=True)
(S / 'results' / 'e9a_prereg_record.json').write_text(json.dumps(rec, indent=2) + '\n')
print(json.dumps(rec, indent=2))
