"""The only test of the frozen extractor: the twelve hand-written synthetic strings listed in
PREREG_E10.md.  No model output is involved."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from decimal import Decimal
from e10_extract import extract, equal, INVALID

CASES = [
    ('The answer is 42.', Decimal('42')),
    ('the answer is $1,250', Decimal('1250')),
    ('The answer is 3.50', Decimal('3.5')),
    ('The answer is -7', Decimal('-7')),
    ('so the answer is 18 apples', Decimal('18')),
    ('The answer is 12. The answer is 15.', Decimal('15')),
    ('Step 1: 3+4=7. Step 2: 7*2=14.', Decimal('14')),
    ('The answer is 100%', Decimal('100')),
    ('The answer is one hundred', None),
    ('No numbers here.', None),
    ('The answer is 0.0', Decimal('0')),
    ('The answer is 007', Decimal('7')),
]

fails = 0
for s, want in CASES:
    got = extract(s)
    ok = (got['value'] is None) if want is None else (got['value'] is not None and got['value'] == want)
    fails += (not ok)
    print('%-5s %-38r -> %-10s (want %s)  route=%s' %
          ('ok' if ok else 'FAIL', s, got['answer'], INVALID if want is None else want, got['route']))
# equality semantics stated in the preregistration
assert equal(extract('The answer is 3.50'), extract('The answer is 3.5'))
assert equal(extract('No numbers here.'), extract('The answer is one hundred'))
assert not equal(extract('The answer is 3.5'), extract('No numbers here.'))
assert not equal(extract('The answer is 3.5'), extract('The answer is 3.6'))
print('EXTRACTOR_TEST fails=%d' % fails)
sys.exit(1 if fails else 0)
