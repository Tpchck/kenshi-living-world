import sys, collections, pickle
sys.path.insert(0, r"C:\KenshiModMap\tools"); sys.path.insert(0, r"C:\KenshiModMap\tools\fast")
import kmod, ctx
lo, van, base, wh = ctx.load()
M = {}
for _, m, _ in van + base + wh: kmod.apply(M, m)
pickle.dump(M, open(ctx.OUT + "/merged.pkl", "wb"))
ch = [i for i in M.values() if i.type_name == "CHARACTER"]
print("characters", len(ch))
by = collections.defaultdict(list)
for c in ch: by[c.values.get("NPC class", "unset")].append(c)
for k, v in sorted(by.items(), key=lambda x: str(x[0])):
    mm = collections.Counter((c.values.get("money min", "-"), c.values.get("money max", "-")) for c in v).most_common(4)
    print(f"class {k}: {len(v)}  traders={sum(1 for c in v if c.values.get('is trader'))}  slaves={sum(1 for c in v if c.values.get('slave',0))}  money={mm}")
    print("     ", [c.name for c in v[:14]])
