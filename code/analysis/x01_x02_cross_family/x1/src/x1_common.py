"""X1 shared definitions (Llama-3.2-1B helper -> Qwen3-0.6B receiver; OBQA and ARC). Reuses the X2 module read-only."""
import sys
sys.dont_write_bytecode = True
import pathlib
X1 = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(X1.parent / 'src'))
from xfam_common import *   # noqa: F401,F403  (X, ROOT, DATA_ROOT, P210, BND, MMLU, V2L, jl, read, save, append, sha, utc, rawline, parser, PREFIX)

H = DATA_ROOT / 'hf_cache/hub'
LLAMA = dict(path=str(H / 'models--meta-llama--Llama-3.2-1B-Instruct/snapshots/9213176726f574b556790deb65791e0c5aa438b6'),
             repo='meta-llama/Llama-3.2-1B-Instruct', revision='9213176726f574b556790deb65791e0c5aa438b6')
QWEN06 = dict(path=str(DATA_ROOT / 'c2c_reproduction_assets/models/Qwen--Qwen3-0.6B'), repo='Qwen/Qwen3-0.6B', revision='c1899de289a04d12100db370d81485cdf75e47ca')
SMALL_HELPER = dict(path=str(DATA_ROOT / 'c2c_reproduction_assets/models/Qwen--Qwen2.5-0.5B-Instruct'), repo='Qwen/Qwen2.5-0.5B-Instruct',
                    revision='7ae557604adf67be50417f59c2c2f167def9a775')
SMALL_FUSER = str(DATA_ROOT / 'c2c_reproduction_assets/fusers/nics-efc--C2C_Fuser/qwen3_0.6b+qwen2.5_0.5b_Fuser/final')     # rev 8704f555
X1_FUSER = str(H / 'models--nics-efc--C2C_Fuser/snapshots/f01fc3258b305e280e04c7238f4f2cf31b7dc70d/qwen3_0.6b+llam3.2_1b_Fuser/final')
CLEAN = DATA_ROOT / 'c2c_reproduction_assets/official_C2C'
EVALUATOR = X / 'x1_optionB/unified_evaluator_xfam.py'
LLAMA_DATE = '26 Jul 2024'    # fixed date_string for the Llama-3.2 chat template (its own fallback constant; recorded in the freeze)
X1POP = X1 / 'records/populations'
DS1 = ['obqa', 'arc']
