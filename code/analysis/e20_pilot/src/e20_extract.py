"""E20-pilot frozen answer extractor, normalizer and score functions (PREREG_E20P.md). Written and hashed before any model output.

Extraction (verbatim rule): strip whitespace; strip leading markdown/quote characters (* _ " ' ` #); remove a leading "Answer:",
"Final answer:" or "The answer is" (case-insensitive); keep the first line that is non-empty after this; remove a trailing period;
Unicode NFKD with accents removed; then the official SQuAD normalization (lowercase, remove punctuation, remove articles a/an/the,
collapse whitespace). INVALID = empty after this. Change = 1[normalized o_R != normalized o_b]; two INVALIDs agree.

Scores (larger = more uncertain) from per-position float64 arrays computed from the raw logits (see e20_exec.py):
  s1 = 1 - max_v p(v) (total non-argmax probability) at the first generated token whose text contains an alphanumeric character;
  s2 = -expm1(sum of chosen-token log-probabilities over the answer tokens): from the first generated token containing a non-whitespace
       character up to, but excluding, the first later token whose text contains a newline; EOS/end-of-turn tokens excluded (the span
       also ends at the first such token);
  s3 = -expm1(mean of the same log-probabilities).
Operationalization fixed here: a token's text = tokenizer.decode([id], skip_special_tokens=False); special / EOS / end-of-turn ids are
never a start or answer token. If no qualifying token exists, the score is 1.0 (maximal uncertainty) and a *_missing flag is set.
"""
import re, math, string, unicodedata

INVALID = 'INVALID'
_LEAD = '*_"\'`#'
_PREFIX = re.compile(r'^\s*(?:final answer:|answer:|the answer is)', re.I)   # alternatives are mutually exclusive at position 0


def squad_normalize(s):
    """Official SQuAD v1.1 evaluate-v1.1.py normalize_answer."""
    def remove_articles(text): return re.sub(r'\b(a|an|the)\b', ' ', text)
    def white_space_fix(text): return ' '.join(text.split())
    def remove_punc(text):
        exclude = set(string.punctuation)
        return ''.join(ch for ch in text if ch not in exclude)
    def lower(text): return text.lower()
    return white_space_fix(remove_articles(remove_punc(lower(s))))


def strip_accents(s):
    s = unicodedata.normalize('NFKD', s)
    return ''.join(c for c in s if not unicodedata.combining(c))


def normalize_text(s):
    """NFKD with accents removed, then the official SQuAD normalization (also used for question dedup and for gold aliases)."""
    return squad_normalize(strip_accents(s))


def extract(raw):
    """raw generation -> dict(extracted=<string before normalization>, answer=<normalized string or INVALID>, words=<int>)."""
    s = (raw if isinstance(raw, str) else '').strip()
    s = s.lstrip(_LEAD)
    s = _PREFIX.sub('', s, count=1)
    line = next((l for l in s.split('\n') if l.strip()), '')
    line = line.strip()
    if line.endswith('.'):
        line = line[:-1]
    n = normalize_text(line)
    ans = n if n else INVALID
    return dict(extracted=line, answer=ans, words=0 if ans == INVALID else len(ans.split()))


def changed(a, b):
    return a != b    # INVALID == INVALID -> agree


def scores(token_texts, is_special, logp, nonmax):
    """token_texts[i], is_special[i], logp[i] (chosen-token log-prob, float64), nonmax[i] (1 - max p, float64) per generated position."""
    n = len(token_texts)
    i1 = next((i for i in range(n) if not is_special[i] and any(c.isalnum() for c in token_texts[i])), None)
    s1 = float(nonmax[i1]) if i1 is not None else 1.0
    st = next((i for i in range(n) if not is_special[i] and token_texts[i].strip() != ''), None)
    if st is None:
        return dict(s1=s1, s1_pos=i1, s1_missing=i1 is None, s2=1.0, s3=1.0, span=None, span_missing=True)
    en = st + 1
    while en < n and not is_special[en] and '\n' not in token_texts[en]:
        en += 1
    lp = [float(x) for x in logp[st:en]]
    tot = math.fsum(lp)
    return dict(s1=s1, s1_pos=i1, s1_missing=i1 is None, s2=float(-math.expm1(tot)), s3=float(-math.expm1(tot / len(lp))),
                span=[st, en], span_missing=False)
