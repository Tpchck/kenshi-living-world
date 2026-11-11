import sys, glob, collections, struct; sys.path.insert(0, r"C:\KenshiModMap\tools")
import kmod
K = "C:/Program Files (x86)/Steam/steamapps/common/Kenshi/data/"
files = glob.glob(K + "newland/leveldata/**/*.zone", recursive=True) + glob.glob(K + "leveldata/*.zone")
res = collections.Counter(); ex = []
for f in files:
    raw = open(f, "rb").read()
    r = kmod._R(raw); ft = r.i32(); last = r.i32(); n = r.i32()
    try:
        for _ in range(n): kmod._read_item(r)
    except Exception as e:
        res["items-fail"] += 1; ex.append((f, "items", str(e)[:80], n)); continue
    if r.p == len(raw): res["no-tail"] += 1; continue
    k = r.i32(); end = r.p + 4*k
    if end == len(raw): res["idlist-exact"] += 1
    else: res["idlist-mismatch"] += 1; ex.append((f, "tail", len(raw)-r.p+4, k))
print(res)
for e in ex[:6]: print(e)
