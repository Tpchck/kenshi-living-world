"""Побайтовый round-trip всех ванильных .zone и .level через kmod."""
import sys, glob, collections, os; sys.path.insert(0, r"C:\KenshiModMap\tools")
import kmod
K = "C:/Program Files (x86)/Steam/steamapps/common/Kenshi/data/"
files = glob.glob(K + "**/*.zone", recursive=True) + glob.glob(K + "**/*.level", recursive=True)
res = collections.Counter(); bad = []
for f in files:
    raw = open(f, "rb").read()
    try:
        m = kmod.read(raw)
    except Exception as e:
        res["read-fail"] += 1; bad.append((os.path.relpath(f, K), str(e)[:70])); continue
    if kmod.write(m) == raw: res["identical"] += 1
    else:
        out = kmod.write(m); i = next((i for i, (a, b) in enumerate(zip(raw, out)) if a != b), min(len(raw), len(out)))
        res["differs"] += 1; bad.append((os.path.relpath(f, K), f"diff@{i} len {len(raw)}/{len(out)}"))
print(len(files), "files:", dict(res))
for b in bad[:12]: print("  ", b)
