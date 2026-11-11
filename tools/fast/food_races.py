import sys, collections, json
sys.path.insert(0, r"C:\KenshiModMap\tools"); sys.path.insert(0, r"C:\KenshiModMap\tools\fast")
import kmod, ctx
lo, van, base, wh = ctx.load()
layers = van + base + wh
M = {}
contrib = collections.defaultdict(lambda: collections.Counter())  # sid -> mod -> refs added in 'races'
for n, m, _ in layers:
    for it in m.items:
        rs = it.refs.get("races")
        if rs and it.type_name in ("ITEM", "CONTAINER", "NEST_ITEM"):
            contrib[it.sid][n] += sum(1 for r in rs if (r.v0, r.v1, r.v2) != kmod.DELETED_REF)
    kmod.apply(M, m)
races_all = [i for i in M.values() if i.type_name == "RACE"]
print("RACE records in build:", len(races_all))
items = [i for i in M.values() if i.type_name == "ITEM" and i.refs.get("races")]
fn = collections.Counter(i.values.get("item function") for i in items)
print("ITEM with 'races':", len(items), "item function:", fn.most_common(6))
L = collections.Counter(len(i.refs["races"]) for i in items)
print("list lengths:", sorted(L.items())[-8:])
for i in sorted(items, key=lambda x: -len(x.refs["races"]))[:6]:
    print(f"  {i.name[:30]:<30} {i.sid:<26} races={len(i.refs['races'])} excl={len(i.refs.get('races exclude', []))} fn={i.values.get('item function')}  by={dict(contrib[i.sid].most_common(4))}")
bymod = collections.Counter()
for s, c in contrib.items():
    for n, k in c.items(): bymod[n] += 1
print("mods writing ITEM.races (items touched):", bymod.most_common(12))
raw = next(i for i in M.values() if i.type_name == "ITEM" and i.name == "Raw Meat")
allowed = {r.target for r in raw.refs.get("races", [])}
missing = [r for r in races_all if r.sid not in allowed]
print("Raw Meat allowed", len(allowed), "of", len(races_all), "→ not allowed:", [r.name for r in missing][:40])
