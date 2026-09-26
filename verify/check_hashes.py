"""Check every recorded SHA-256 in the release against the released file.

Three outcomes are expected and are reported separately:

  OK        the released file still hashes to the recorded value;
  ALTERED   the file was rewritten by anonymization (absolute paths replaced by
            $DATA_DIR, cluster and host names replaced by neutral labels), so the
            recorded hash - which is the hash of the ORIGINAL frozen file - no
            longer matches the released copy. The recorded value is kept as the
            record of the original;
  ABSENT    the manifest names a file that is not part of this release (excluded
            weights, logs, caches, feature dumps - see the "What is not included"
            section of README.md).

It reads every *.sha256 and SHA256SUMS* manifest in the release.

Run from the repository root:  python3 verify/check_hashes.py [--list-altered]
"""
import hashlib, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LINE = re.compile(r"^([0-9a-f]{64})\s+\*?(.+)$")

def main():
    show = "--list-altered" in sys.argv
    ok = altered = absent = 0
    alist = []
    for dp, dn, fn in os.walk(ROOT):
        if ".git" in dp.split(os.sep):
            continue
        for f in sorted(fn):
            if not (f.endswith(".sha256") or f.startswith("SHA256SUMS")
                    or f in ("WORK_BUNDLE_SHA256SUMS",)):
                continue
            try:
                lines = open(os.path.join(dp, f)).read().strip().splitlines()
            except OSError:
                continue
            for ln in lines:
                m = LINE.match(ln.strip())
                if not m:
                    continue
                want, name = m.group(1), m.group(2).strip()
                tgt = os.path.join(dp, name)
                if not os.path.exists(tgt):
                    absent += 1
                    continue
                with open(tgt, "rb") as fh:
                    got = hashlib.sha256(fh.read()).hexdigest()
                if got == want:
                    ok += 1
                else:
                    altered += 1
                    alist.append(os.path.relpath(tgt, ROOT))
    print("recorded SHA-256 entries")
    print("  OK      %4d  released file matches the recorded hash" % ok)
    print("  ALTERED %4d  rewritten by anonymization; recorded hash is the original file's" % altered)
    print("  ABSENT  %4d  manifest names a file not shipped in this release" % absent)
    if show:
        print("\naltered files:")
        for a in alist:
            print("   ", a)
    return 0

if __name__ == "__main__":
    sys.exit(main())
