import sys, glob, collections, os; sys.path.insert(0, r"C:\KenshiModMap\tools")
import kmod
K = "C:/Program Files (x86)/Steam/steamapps/common/Kenshi/data/"
ok = bad = same = 0; errs = collections.Counter(); types = collections.Counter()
files = glob.glob(K + "newland/leveldata/**/*.zone", recursive=True) + glob.glob(K + "leveldata/*.zone")
for f in files:
    raw = open(f, "rb").read()
    try:
        m = kmod.read(raw); ok += 1
        same += kmod.write(m) == raw
        for it in m.items: types[it.type_name] += 1
    except Exception as e:
        bad += 1; errs[str(e)[:60]] += 1
print("zones", len(files), "ok", ok, "bad", bad, "byte-identical", same); print(errs.most_common(3)); print(types.most_common(20))
for f in glob.glob(K + "**/*.level", recursive=True):
    raw = open(f, "rb").read()
    try: m = kmod.read(raw); print("LEVEL", os.path.relpath(f, K), m.ftype, len(m.items), collections.Counter(i.type_name for i in m.items).most_common(5), kmod.write(m) == raw)
    except Exception as e: print("LEVEL FAIL", f, e)
