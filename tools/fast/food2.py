import sys, collections
sys.path.insert(0, r"C:\KenshiModMap\tools"); sys.path.insert(0, r"C:\KenshiModMap\tools\fast")
import kmod, ctx
lo, van, base, wh = ctx.load()
layers = van + base + wh
M = {}
for _, m, _ in layers: kmod.apply(M, m)
for it in [i for i in M.values() if i.name in ("Raw Meat", "Dried Meat", "Foodcube")]:
    print("==", it.type_name, it.sid, it.name, {k: len(v) for k, v in it.refs.items()})
    for n, m, _ in layers:
        for x in m.items:
            if x.sid == it.sid and x.refs: print("    ", n[:40], {k: len(v) for k, v in x.refs.items()})
# which ref categories on ITEM records are long race lists?
c = collections.Counter()
for i in M.values():
    if i.type_name in ("ITEM",):
        for k, v in i.refs.items():
            if v and all(M.get(r.target) is not None and M[r.target].type_name == "RACE" for r in v[:5]): c[(k, len(v) // 50 * 50)] += 1
print(c.most_common(10))
