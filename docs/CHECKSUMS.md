# Recorded SHA-256 values in this release

Each stage recorded SHA-256 values for its protocol and its outputs when they were frozen.
Anonymization replaced paths, user names and cluster-specific names (scheduler queue and resource
names, a CPU model) inside some of those files, so their stored values no longer match the released
copies. `verify/check_hashes.py` classifies every recorded entry; it reads every `*.sha256` and `SHA256SUMS*` manifest in the release.

Counts for this release (`python3 verify/check_hashes.py`):

| outcome | count | meaning |
|---|---:|---|
| OK | 169 | the released file still hashes to the recorded value; 55 of these are `PREREG` or `FREEZE` protocols |
| ALTERED | 83 | the file was rewritten by anonymization, so the recorded hash — the hash of the original frozen file — does not match the released copy |
| ABSENT | 213 | the manifest names a file that is not shipped here (model weights, logs, caches, feature dumps; see "What is not included" in the README) |

`python3 verify/check_hashes.py --list-altered` prints the 83 paths.
`results/e13/PREREG_E13.md` is one of them; `results/e15/PREREG_E15.md` is not, and verifies as shown
in the README.

The unanonymized originals will be released with the camera-ready version.
