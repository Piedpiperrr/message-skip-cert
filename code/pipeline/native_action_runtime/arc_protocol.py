"""stage ARC-Challenge 最小适配（CPU，不加载模型）。

- 保留原始选项顺序；展示标签按顺序统一为 A、B、C……；原标签→展示标签可逆映射转换 gold。
- 提示词、Text helper 正文与路由 query 复用 stage 的 build_prompt / serialize_question（只读导入），
  去掉 stage format_openbook 中"必须恰好四个选项"的限制；receiver 指令按每题实际合法标签渲染（v2，2026-09-11）。
  四选项题输出与 stage 逐字节一致（见核验脚本）。
- 解析器是 stage 修正 parser 的参数化版本：只承认该题合法展示标签；
  另加一条统一规则：显式答案标记后紧跟非法单字母标签（如三选项题回答 D）判为无效。
"""
import re
import sys
from pathlib import Path

P5 = Path('<private_path>/obqa_small_action_matrix')
if str(P5) not in sys.path:
    sys.path.insert(0, str(P5))
from protocol_min import build_prompt  # noqa: E402
from query_features import serialize_question  # noqa: E402

# 逐字复制自 stage legacy_methods.py（该模块导入 torch，故不直接导入；核验脚本用 ast 比对一致）
BACKGROUND_PROMPT = ("In one clear sentence, describe the most essential background knowledge "
                     "needed to answer the question:\n\n{question}\n\n"
                     "Do NOT directly solve or give answer to the question.")


def display_labels(n):
    assert 1 <= n <= 26
    return [chr(65 + i) for i in range(n)]


def choices_block(texts):
    return ''.join(f'{chr(65 + i)}. {t}\n' for i, t in enumerate(texts))


_INSTRUCTION_ABCD = '"The correct answer is A/B/C/D"'


def receiver_prompt(rec):
    """Receiver-only 与 C2C 的 receiver 用户消息；Text 的最后一轮用户消息也用它。

    指令中的标签按该题实际展示标签渲染（3选项 A/B/C，4选项保持 A/B/C/D，5选项 A/B/C/D/E）；
    四选项题与P2-5模板逐字节一致。
    """
    prompt = build_prompt(dataset='mmlu-redux', locale='', question=str(rec['question_stem']),
                          choices=choices_block(rec['choice_text']), use_cot=False, use_template=True)
    assert prompt.count(_INSTRUCTION_ABCD) == 1
    labels = '/'.join(display_labels(len(rec['choice_text'])))
    return prompt.replace(_INSTRUCTION_ABCD, f'"The correct answer is {labels}"')


def helper_body(rec):
    """Text(t2t_full) helper 看到的题目正文（stage 中为 format_openbook(use_template=False)）。"""
    return build_prompt(dataset='mmlu-redux', locale='', question=str(rec['question_stem']),
                        choices=choices_block(rec['choice_text']), use_cot=False, use_template=False)


def helper_prompt(rec):
    return BACKGROUND_PROMPT.format(question=helper_body(rec))


def router_query(rec):
    return serialize_question(rec['question_stem'], tuple(rec['choice_labels']), tuple(rec['choice_text']))


# ---------------- 解析器 ----------------
_ANSWER_PATTERNS = [
    r'Answer:\s*(.*)', r'answer:\s*(.*)', r'ANSWER:\s*(.*)',
    r'Your answer:\s*(.*)', r'your answer:\s*(.*)', r'YOUR ANSWER:\s*(.*)',
    r'The answer is\s*(.*)', r'the answer is\s*(.*)', r'THE ANSWER IS\s*(.*)',
    r'Correct answer is\s*(.*)', r'correct answer is\s*(.*)',
    r'Correct answer is:\s*(.*)', r'correct answer is:\s*(.*)',
    r'Correct answer:\s*(.*)', r'correct answer:\s*(.*)', r'CORRECT ANSWER:\s*(.*)',
    r'Jibu lako:\s*(.*)', r'jibu lako:\s*(.*)', r'JIBU LAKO:\s*(.*)',
    r'Jibu:\s*(.*)', r'jibu:\s*(.*)', r'JIBU:\s*(.*)',
    r'Jibu sahihi:\s*(.*)', r'jibu sahihi:\s*(.*)', r'JIBU SAHIHI:\s*(.*)',
    r'Response:\s*(.*)', r'response:\s*(.*)', r'RESPONSE:\s*(.*)',
    r'Choice:\s*(.*)', r'choice:\s*(.*)', r'CHOICE:\s*(.*)',
    r'Option:\s*(.*)', r'option:\s*(.*)', r'OPTION:\s*(.*)',
]
_MATH = ['+', '-', '*', '/', '=', '^', 'x^', 'y^', 'z^', 'mod', 'sqrt', 'sin', 'cos', 'tan']
_ANS_WORDS = ['jibu', 'answer', 'choice', 'option', 'response', 'correct', 'sahihi']
MARKER = re.compile(
    r'\b(?:(?:the|my|your)\s+)?(?:(?:correct|final)\s+)?'
    r'(?:answer|choice|option|response)\s*(?:is\s*:?[ \t]*|:[ \t]*)', re.I)
_DECLARED_LETTER = re.compile(r'^\s*[\"\x27(\[]?([A-Z])(?=\s*(?:[.,;:)\]\"\x27]|$))')


def legacy_extract(text, legal):
    """stage protocol_min.extract_answer_from_content，把 A-D 换成该题合法标签集合。"""
    L = set(legal)
    cls = '[' + ''.join(legal) + ']'
    text = text.strip()
    if not text:
        return None
    for pattern in _ANSWER_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            for char in match.group(1).strip():
                if char in L:
                    return char
    for pattern in [rf'\b({cls})(?:\s*[.,!?:)]?\s*$)', rf'\b({cls})(?:\s*[.,!?:)]\s)', rf'(?:^|\s)({cls})(?:\s*$)']:
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            has_math = any(i in text for i in _MATH)
            has_ans = any(p in text.lower() for p in _ANS_WORDS)
            if has_math and not has_ans:
                continue
            return matches[-1].upper()
    letters = re.findall(rf'\b({cls})\b', text, re.IGNORECASE)
    if letters:
        has_math = any(i in text for i in _MATH)
        has_ans = any(p in text.lower() for p in _ANS_WORDS)
        if has_math and not has_ans:
            return None
        return letters[-1].upper()
    for char in reversed(text):
        if char in L:
            return char
    return None


def parse_answer(text, legal):
    """stage scoring.parse_answer 的参数化版本，返回唯一明确的合法展示标签或无效。"""
    legal = list(legal)
    cls = '[' + ''.join(legal) + ']'
    option_list = re.compile(rf'\b{cls}\b(?:\s*(?:/|\||,\s*(?:(?:or|and)\s+)?|\bor\b|\band\b)\s*{cls}\b)+', re.I)
    single = re.compile(rf'^\s*[\"\x27(\[]?({cls})\b', re.I)
    # 统一规则：最后一个显式答案标记后紧跟单个非法字母标签 → 无效（不回退到正文中其他字母）
    declared = [m for m in (_DECLARED_LETTER.match(text[mk.end():]) for mk in MARKER.finditer(text)) if m]
    if declared and declared[-1].group(1) not in legal:
        return {'answer': None, 'valid': False, 'reason': 'illegal_label', 'historical_answer': legacy_extract(text, legal)}
    legacy = legacy_extract(text, legal)
    lists = [m for m in option_list.finditer(text)
             if len(set(re.findall(rf'\b{cls}\b', m.group().upper()))) > 1]
    if not lists:
        return {'answer': legacy, 'valid': legacy is not None,
                'reason': None if legacy is not None else 'legacy_parse_failure', 'historical_answer': legacy}
    declarations = []
    for marker in MARKER.finditer(text):
        s = single.match(text[marker.end():])
        if s:
            start = marker.end() + s.start(1)
            ambiguous = any(m.start() == start for m in lists)
            declarations.append((marker.start(), None if ambiguous else s.group(1).upper()))
    leading = single.match(text)
    if leading and not any(m.start() == leading.start(1) for m in lists):
        declarations.insert(0, (-1, leading.group(1).upper()))
    if declarations and declarations[-1][1] is not None:
        return {'answer': declarations[-1][1], 'valid': True, 'reason': None, 'historical_answer': legacy}
    return {'answer': None, 'valid': False, 'reason': 'unresolved_multiple_options', 'historical_answer': legacy}


def score(text, gold, legal, runtime_error=None):
    parsed = parse_answer(text or '', legal)
    return {**parsed, 'correct': runtime_error is None and parsed['valid'] and parsed['answer'] == gold}
