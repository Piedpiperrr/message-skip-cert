"""Three answer extractors used by the E5-a independent-parser check (all read-only, pure text -> label).

V2       : frozen project parser (P2_SCORING_V2/scoring_v2.py), the labels used everywhere in the paper.
OFFICIAL : the official C2C evaluator's extraction, rosetta/utils/evaluate.py::extract_answer_from_content.
           Loaded by extracting that function's source with ast (the module itself imports torch/rosetta).
           NOTE: it hard-codes the option set A-D, so it is only applicable to 4-option benchmarks.
D1       : the pre-V2 parser version in the repo history (P2_SCORE_SENSITIVITY/diagnostic_parser_v1.py::parse_explicit,
           frozen 2026-09-12T06:02:33Z, i.e. before V2's 19:19:38Z freeze).
LEGACY   : the run-time parser actually used when the outputs were produced; its verdicts are stored in each raw
           record's `scoring` field (not re-executed here).
"""
import ast, hashlib, importlib.util, re, sys
from pathlib import Path
from typing import Optional  # noqa: F401  (used by the exec'd official function)

ROOT = Path('$DATA_DIR')
OFFICIAL_SRC = Path('$DATA_DIR/c2c_reproduction_assets/official_C2C/rosetta/utils/evaluate.py')
V2_SRC = ROOT / 'P2_SCORING_V2_20260912T191445Z/scoring_v2.py'
D1_SRC = ROOT / 'P2_SCORE_SENSITIVITY_20260912T055929Z/diagnostic_parser_v1.py'


def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m


_v2 = _load(V2_SRC, 'scoring_v2_r2')
_d1 = _load(D1_SRC, 'diagnostic_parser_v1_r2')

# official: exec only the extraction function, not the torch-importing module
_tree = ast.parse(OFFICIAL_SRC.read_text())
_fn = next(n for n in _tree.body if isinstance(n, ast.FunctionDef) and n.name == 'extract_answer_from_content')
_ns = {'re': re, 'Optional': Optional}
exec(compile(ast.Module(body=[_fn], type_ignores=[]), str(OFFICIAL_SRC), 'exec'), _ns)
extract_answer_from_content = _ns['extract_answer_from_content']

INV = 'INVALID'
SOURCES = dict(V2=str(V2_SRC), OFFICIAL=str(OFFICIAL_SRC), D1=str(D1_SRC))
HASHES = {k: sha(v) for k, v in SOURCES.items()}


def label_v2(raw, legal):
    r = _v2.parse_answer(raw, legal)
    return r['answer'] if r['valid'] else INV


def label_d1(raw, legal):
    r = _d1.parse_explicit(raw, legal)
    return r['answer'] if r['valid'] else INV


def label_official(raw, legal):
    """Official evaluator extraction; INVALID when it returns None or a label outside this question's option set."""
    a = extract_answer_from_content(raw or '')
    return a if (a is not None and a in legal) else INV


def official_applicable(legal): return set(legal) <= {'A', 'B', 'C', 'D'}
