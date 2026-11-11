import sys, glob, collections; sys.path.insert(0, r"C:\KenshiModMap\tools")
import kmod
K = "C:/Program Files (x86)/Steam/steamapps/common/Kenshi/data/"
c = collections.Counter()
for f in glob.glob(K + "newland/leveldata/Newwworld/*.zone")[:80]:
    try: m = kmod.read(f)
    except Exception: continue
    for it in m.items:
        c[(it.type_name, "raw==ninst" if it._len_raw == len(it.instances) else ("raw0" if it._len_raw == 0 else "other"))] += 1
print(c.most_common(12))
m = kmod.read(K + "leveldata/zone.13.20.zone"); it = m.items[0]; print(it.type_name, it._len_raw, len(it.instances), m.ftype)
