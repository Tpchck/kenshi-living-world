import sys, glob, collections, struct; sys.path.insert(0, r"C:\KenshiModMap\tools")
import kmod
K = "C:/Program Files (x86)/Steam/steamapps/common/Kenshi/data/"
files = glob.glob(K + "newland/leveldata/**/*.zone", recursive=True)
def parse_items(raw):
    r = kmod._R(raw); ft = r.i32(); last = r.i32(); n = r.i32(); items = []; lens = []
    for _ in range(n):
        p = r.p; items.append(kmod._read_item(r)); lens.append(struct.unpack_from("<i", raw, p)[0])
    return ft, last, n, items, raw[r.p:], lens
c = collections.Counter(); shown = 0
for f in files:
    raw = open(f, "rb").read()
    ft, last, n, items, tail, lens = parse_items(raw)
    c[len(tail)] += 1
    if tail and shown < 6:
        shown += 1; print(f.split("leveldata")[-1], "last", last, "n", n, "tail", tail.hex(" "), "lens", lens[:4], [i.type_name for i in items[:3]])
print(c)
