"""E10 frozen numeric answer extractor (PREREG_E10.md, section "Change indicator and answer
extraction").  Written and hashed before any model output exists.  NOT modified afterwards.

Rule, verbatim from the preregistration:
  The extracted answer is the number following the last occurrence of "answer is" in the
  generation; if that string does not occur, the last number in the generation; if there is no
  number, INVALID.
  Normalization: strip surrounding whitespace, commas, currency symbols, percent signs and a
  trailing period; parse as a Decimal; strip trailing zeros.
  Two answers are equal iff both parse and their normalized Decimals are equal, or both are
  INVALID.

The extracted answer string `a` is the matched numeric token exactly as it appears in the
generation (optional sign, digits, embedded commas, optional fractional part).  Currency symbols
and percent signs are outside the token and are therefore removed by normalization, not by the
match.  `start`/`end` are the character offsets of `a` in the generation; the score in the
preregistration re-scores the prompt plus the generation up to `start`, followed by `a`.
"""
import re
from decimal import Decimal, InvalidOperation

INVALID = 'INVALID'
_MARKER = 'answer is'
# optional sign, then digits with optional embedded commas, then an optional fractional part.
_NUM = re.compile(r'[-+]?\d[\d,]*(?:\.\d+)?')
_STRIP = ' \t\r\n$£€¥%,'


def normalize(raw):
    """raw numeric token -> Decimal with trailing zeros stripped, or None if it does not parse."""
    s = raw.strip()
    while s and s[-1] == '.':
        s = s[:-1]
    s = s.strip(_STRIP)
    s = s.replace(',', '')
    if not s:
        return None
    try:
        d = Decimal(s)
    except InvalidOperation:
        return None
    if not d.is_finite():
        return None
    return d.normalize()


def extract(text):
    """-> dict(answer=<str 'INVALID' or canonical decimal string>, value=<Decimal|None>,
              raw=<matched token or None>, start=<int|None>, end=<int|None>, route=<str>)"""
    t = text if isinstance(text, str) else ''
    i = t.lower().rfind(_MARKER)
    m, route = None, None
    if i >= 0:
        m = _NUM.search(t, i + len(_MARKER))
        route = 'after_last_answer_is'
    if m is None:
        last = None
        for mm in _NUM.finditer(t):
            last = mm
        m, route = last, 'last_number_in_generation'
    if m is None:
        return {'answer': INVALID, 'value': None, 'raw': None, 'start': None, 'end': None,
                'route': 'no_number'}
    d = normalize(m.group(0))
    if d is None:
        return {'answer': INVALID, 'value': None, 'raw': m.group(0), 'start': m.start(),
                'end': m.end(), 'route': route + '_unparseable'}
    return {'answer': fmt(d), 'value': d, 'raw': m.group(0), 'start': m.start(), 'end': m.end(),
            'route': route}


def fmt(d):
    """Canonical plain-decimal string for a normalized Decimal (no exponent form)."""
    return format(d, 'f')


def equal(a, b):
    """Two extraction results are equal iff both parse to the same normalized Decimal, or both
    are INVALID."""
    va, vb = a['value'], b['value']
    if va is None and vb is None:
        return True
    if va is None or vb is None:
        return False
    return va == vb
