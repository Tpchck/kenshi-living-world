import sys, collections
sys.path.insert(0, r"C:\KenshiModMap\tools"); sys.path.insert(0, r"C:\KenshiModMap\tools\fast")
import kmod, ctx
lo, van, base, wh = ctx.load()
kmm = []
for m in ["KMM_Core", "KMM_Relics", "KMM_Economy", "KMM_Behavior"]:
    kmm.append((m + ".mod", kmod.read(rf"C:\KenshiModMap\build\{m}\{m}.mod"), None))
layers = van + base + wh + kmm
orc_mod = next(m for n, m, _ in wh if n == "OrcRaceReview.mod")
orc_races = [it for it in orc_mod.items if it.type_name == "RACE"]
print("orc races:", [(r.sid, r.name, r.change) for r in orc_races])
sids = {r.sid for r in orc_races}
M = {}
for n, m, _ in layers:
    for it in m.items:
        if it.sid in sids:
            print(f"  {n[:36]:<36} {it.sid:<24} ch={it.change} vals={len(it.values)} refs={ {k: len(v) for k, v in it.refs.items()} }")
    kmod.apply(M, m)
for s in sids:
    r = M[s]
    print("FINAL", r.name, {k: [(M[x.target].name if x.target in M else x.target, x.v0) for x in v] for k, v in r.refs.items() if "anim" in k.lower() or "skeleton" in k.lower()})
    print("   values anim-ish:", {k: v for k, v in r.values.items() if any(t in k.lower() for t in ("anim", "skeleton", "walk", "mesh", "speed", "female", "male"))})
print("=== refs to orc race")
touch = collections.Counter(); ex = {}
for n, m, _ in layers:
    for it in m.items:
        for cat, rs in it.refs.items():
            for x in rs:
                if x.target in sids:
                    touch[(n, it.type_name, cat)] += 1; ex.setdefault((n, it.type_name, cat), (it.name, x.v0, x.v1, x.v2))
for k, v in touch.most_common(25): print(f"  {v:4} {k[0][:34]:<34} {k[1]:<16} {k[2]:<18} e.g. {ex[k]}")
# анимации ходьбы: ANIMATION с ключом walk и их race-фильтры в финале
walk = [i for i in M.values() if i.type_name == "ANIMATION" and "walk" in i.name.lower()]
print("walk anims", len(walk), "with orc in any race ref:", sum(1 for w in walk if any(x.target in sids for rs in w.refs.values() for x in rs)))
cats = collections.Counter(c for w in walk for c in w.refs); print("walk anim ref cats", cats.most_common(8))
