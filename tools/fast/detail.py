import json, sys, collections, pickle
sys.path.insert(0, r"C:\KenshiModMap\tools"); sys.path.insert(0, r"C:\KenshiModMap\tools\fast")
import kmod, ctx
a = json.load(open(ctx.OUT + "/wh_analysis.json", encoding="utf-8"))
lo, van, base, wh = ctx.load()
merged = {}
for _, m, _ in van + base + wh: kmod.apply(merged, m)
nm = lambda s: merged[s].name if s in merged else "?"
by = collections.defaultdict(lambda: collections.defaultdict(list))
for o in a["overlaps"]:
    by[o["wh"]][(o["sid"], o["type"], nm(o["sid"]))].append((o["other"], len(o["same_fields"]), o["same_ref_cats"]))
for w, recs in by.items():
    print("==", w)
    for (sid, t, n), others in recs.items():
        print(f"   {t:<16} {n[:34]:<34} {sid:<26} ← {len(others)} модов основы; пример: {[(x[0][:30], x[1], x[2]) for x in others[:3]]}")
# '?' changed + collisions
for name, m, _ in wh:
    for it in m.items:
        if it.change != 0 and not any(t for t in [x for x in (van+base+wh)] if False): pass
origin = {}
for _, m, _ in van + base + wh:
    for it in m.items:
        if it.change == 0: origin.setdefault(it.sid, None)
for name, m, _ in wh:
    q = [(it.type_name, it.name, it.sid) for it in m.items if it.change != 0 and it.sid not in origin]
    if q: print("CHANGE-TO-MISSING", name, q)
for p in a["passports"]:
    if p["sid_collisions"]: print("COLLIDE", p["file"], [(s, nm(s), merged[s].type_name if s in merged else '') for s in p["sid_collisions"]])
pickle.dump({s: (merged[s].type_name, merged[s].name) for s in merged}, open(ctx.OUT + "/names.pkl", "wb"))
