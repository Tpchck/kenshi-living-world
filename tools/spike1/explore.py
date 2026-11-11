import sys, collections; sys.path.insert(0, r"C:\KenshiModMap\tools")
import kmod
K = r"C:\Program Files (x86)\Steam\steamapps\common\Kenshi\data\\"
base = kmod.read(K+"gamedata.base"); nw = kmod.read(K+"Newwworld.mod"); rb = kmod.read(K+"rebirth.mod")
B = base.by_sid()
print("sid samples base:", [it.sid for it in base.items[:5]], "new in rebirth:", [it.sid for it in rb.items if it.change==0][:5])
print("save_data samples:", collections.Counter(it.save_data for it in rb.items).most_common(8))
# changed items: how many values vs base
for it in [x for x in rb.items if x.change==1][:3]:
    b = B.get(it.sid)
    print("\nCHANGED", it.type_name, it.name, it.sid, "nvals", len(it.values), "base nvals", len(b.values) if b else None)
    print("  vals:", dict(list(it.values.items())[:6])); print("  refs:", {k:v[:3] for k,v in it.refs.items()})
# removed refs: look for magic values
mag = collections.Counter()
for m in (nw, rb):
    for it in m.items:
        for c, rs in it.refs.items():
            for r in rs:
                if r.v0 == 2147483647 or r.v0 < -1000: mag[(r.v0, r.v1, r.v2)] += 1
print("\nmagic refs:", mag.most_common(5))
c3 = [x for x in rb.items if x.change==3][:3]
for it in c3: print("CHANGE3", it.type_name, it.name, it.sid, len(it.values), list(it.values)[:5])
