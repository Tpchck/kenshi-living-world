import sys, struct; sys.path.insert(0, r"C:\KenshiModMap\tools")
import kmod
raw = open("C:/Program Files (x86)/Steam/steamapps/common/Kenshi/data/leveldata/zone.16.17.zone", "rb").read()
r = kmod._R(raw); print("type", r.i32(), "last", r.i32()); n = r.i32(); print("n", n)
for i in range(n):
    p = r.p
    try: it = kmod._read_item(r)
    except Exception as e:
        print("fail item", i, "at", p, e.__class__.__name__); print(raw[p:p+200]); break
    last = (it.type_name, it.name, len(it.instances), it.instances[-1] if it.instances else None)
print("prev:", last)
