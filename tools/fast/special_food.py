import sys, collections, json
sys.path.insert(0, r"C:\KenshiModMap\tools"); sys.path.insert(0, r"C:\KenshiModMap\tools\fast")
import kmod, ctx
lo, van, base, wh = ctx.load()
layers = van + base + wh
M = {}
for _, m, _ in layers: kmod.apply(M, m)
food = {i.sid: i for i in M.values() if i.type_name == "ITEM" and i.values.get("item function") is not None}
fn = collections.Counter((i.values.get("item function")) for i in food.values())
by_item = collections.defaultdict(set)
for r in M.values():
    if r.type_name == "RACE":
        for x in r.refs.get("special food", []): by_item[x.target].add(r.sid)
top = sorted(by_item.items(), key=lambda kv: -len(kv[1]))[:8]
races = [r for r in M.values() if r.type_name == "RACE"]
print("races total", len(races), "| races with special food", sum(1 for r in races if r.refs.get("special food")))
for sid, rs in top:
    it = M.get(sid); print(f"  {it.name if it else sid:<22} fn={it.values.get('item function') if it else '?'}  eaten-by {len(rs)} races")
raw = next(i for i in M.values() if i.type_name == "ITEM" and i.name == "Raw Meat")
who = collections.Counter()
for n, m, _ in layers:
    for it in m.items:
        if it.type_name == "RACE" and any(x.target == raw.sid and (x.v0, x.v1, x.v2) != kmod.DELETED_REF for x in it.refs.get("special food", [])):
            who[n] += 1
print("mods adding Raw Meat to RACE.special food:", who.most_common(15), "total mods", len(who))
eaters = by_item[raw.sid]
non = [r for r in races if r.sid not in eaters]
pl = [r for r in races if r.sid in eaters and r.values.get("playable")]
print("Raw Meat eaters", len(eaters), "non-eaters", len(non), "playable eaters", len(pl))
print("ITEM fn for Raw Meat:", raw.values.get("item function"), "| fn distribution among items:", fn.most_common(8))
