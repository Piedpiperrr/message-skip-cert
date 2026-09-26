"""Load the 28 settings and the sealed ARC rows once (same loaders as step2.py) and pickle them under this stage."""
import pickle
from e17_common import *

D = {s: load(s) for s in ALL28}
S = {b: load_sealed(b) for b in 'TC'}
(STAGE / 'cache').mkdir(exist_ok=True)
with open(STAGE / 'cache/data28.pkl', 'wb') as f:
    pickle.dump(dict(D=D, S=S), f)
print('cached', len(D), 'settings')
