import sys, collections, pickle
sys.path.insert(0, r"C:\KenshiModMap\tools"); sys.path.insert(0, r"C:\KenshiModMap\tools\fast")
import kmod, ctx
M = pickle.load(open(ctx.OUT + "/merged.pkl", "rb"))
nm = lambda s: M[s].name if s in M else "?"
def one(t, n):
    r = [i for i in M.values() if i.type_name == t and i.name == n]; return r[0] if r else None
for t, n in [("ARMOUR", "Guardsman Armor"), ("ARMOUR", "Death Korps Jacket - 5"), ("CROSSBOW", "Lasgun"), ("WEAPON", "(AM WH40k) Chainsword")]:
    i = one(t, n)
    if not i: print("NOT FOUND", t, n); continue
    print("==", t, i.sid, i.name); print("   ", {k: v for k, v in i.values.items() if not isinstance(v, str)}); print("    refs", {k: [nm(r.target) for r in v][:3] for k, v in i.refs.items()})
# фракции: fundamental type
fac = [i for i in M.values() if i.type_name == "FACTION"]
print("faction types", collections.Counter(f.values.get("fundamental type") for f in fac))
print("bandit-type:", [f.name for f in fac if f.values.get("fundamental type") == 8][:60])
for n in ["Holy Nation", "United Cities", "Shek Kingdom", "Tech Hunters", "Greenskins", "Mercenaries", "Manhunters"]:
    f = one("FACTION", n); print(n, f.sid if f else None, f and {k: len(v) for k, v in f.refs.items()})
# шаблоны патрулей
hs = set(r.target for b in M.values() if b.type_name == "BIOME_GROUP" for r in b.refs.get("homeless spawns", []))
pat = [M[s] for s in hs if s in M and "patrol" in M[s].name.lower()]
for p in pat[:15]: print("PATROL", p.sid, p.name, [nm(r.target) for r in p.refs.get("faction", [])], [nm(r.target) for r in p.refs.get("AI packages", [])])
