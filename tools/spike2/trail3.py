import sys; sys.path.insert(0, r"C:\KenshiModMap\tools")
import kmod
K = "C:/Program Files (x86)/Steam/steamapps/common/Kenshi/data/newland/leveldata/"
for fn in ["rebirth/zone.18.23.zone"]:
    raw = open(K+fn, "rb").read(); r = kmod._R(raw); r.i32(); r.i32(); n = r.i32()
    for _ in range(n): it = kmod._read_item(r)
    print(fn, "n", n, "last item", it.type_name, it.name, len(it.instances)); print(raw[r.p:r.p+160].hex(" ")); print(raw[r.p:r.p+160])
