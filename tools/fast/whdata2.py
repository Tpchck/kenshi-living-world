import sys, collections, pickle
sys.path.insert(0, r"C:\KenshiModMap\tools"); sys.path.insert(0, r"C:\KenshiModMap\tools\fast")
import kmod, ctx
M = pickle.load(open(ctx.OUT + "/merged.pkl", "rb"))
nm = lambda s: M[s].name if s in M else "?"
by_name = lambda t, n: [i for i in M.values() if i.type_name == t and i.name == n]
for sqn in ["imperial_guard_squad", "startoff- DKOK", "start- steellegion", "Wasteland Wanderers", "Greenskin Mercenaries", "Space Necromancer Slave Wandering Squad"]:
    for s in by_name("SQUAD_TEMPLATE", sqn):
        print("SQUAD", s.sid, s.name, {c: [(nm(r.target)[:24], r.v0, r.v1) for r in rs][:5] for c, rs in s.refs.items()})
        for c in ("leader", "squad"):
            for r in s.refs.get(c, [])[:2]:
                ch = M.get(r.target)
                if ch: print("    CHAR", ch.sid, ch.name, "class", ch.values.get("NPC class"), "money", ch.values.get("money min"), ch.values.get("money max"),
                              {k: [(nm(x.target)[:22], x.v0, x.v1, x.v2) for x in v][:4] for k, v in ch.refs.items() if k in ("clothing", "weapons", "race", "weapon level", "crossbows")})
# who uses homeless spawns: weight distribution
bg = [i for i in M.values() if i.type_name == "BIOME_GROUP"]
w = collections.Counter((r.v0, r.v1) for b in bg for r in b.refs.get("homeless spawns", []))
print("homeless weights", w.most_common(8), "biomes", len(bg))
print([ (b.sid, b.name, len(b.refs.get('homeless spawns', []))) for b in bg if b.name in ("Border Zone","Okran's Pride","Vain","Skinner's Roam","Bonefields","The Grey Desert","Ashlands","Spider Plains","The Hidden Forest","Shem","Stenn Desert","Venge","Heng")])
