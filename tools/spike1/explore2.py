import sys, collections; sys.path.insert(0, r"C:\KenshiModMap\tools")
import kmod
K = r"C:\Program Files (x86)\Steam\steamapps\common\Kenshi\data\\"
# слить base + Newwworld + rebirth (как делает игра): последующие перезаписывают значения/ссылки
merged = {}
for fn in ["gamedata.base","Newwworld.mod","Dialogue.mod","rebirth.mod"]:
    for it in kmod.read(K+fn).items:
        if it.sid not in merged: merged[it.sid] = kmod.Item(it.type, it.id, it.name, it.sid, it.save_data, dict(it.values), {k:list(v) for k,v in it.refs.items()}, list(it.instances))
        else:
            m = merged[it.sid]; m.values.update(it.values); m.name = it.name
            for c, rs in it.refs.items():
                cur = {r.target: r for r in m.refs.get(c, [])}
                for r in rs:
                    if (r.v0,r.v1,r.v2)==(2147483647,)*3: cur.pop(r.target, None)
                    else: cur[r.target] = r
                m.refs[c] = list(cur.values())
            m.instances += it.instances
T = lambda n: [x for x in merged.values() if x.type_name==n]
towns = T("TOWN"); print("towns", len(towns), "squads", len(T("SQUAD_TEMPLATE")), "world states", len(T("WORLD_EVENT_STATE")))
ov = [t for t in towns if t.refs.get("override town")]
print("towns with overrides:", len(ov))
def show(it, depth=0):
    p = "  "*depth
    print(f"{p}[{it.type_name}] {it.name!r} sid={it.sid}")
    for k,v in it.values.items(): print(f"{p}   {k} = {v!r}")
    for c, rs in it.refs.items():
        for r in rs: print(f"{p}   -> {c}: {merged[r.target].name if r.target in merged else '??'} ({r.target}) {r.v0},{r.v1},{r.v2}")
    if it.instances: print(f"{p}   instances: {len(it.instances)}", it.instances[:2])
t = ov[0]; show(t)
o = merged[t.refs["override town"][0].target]; show(o, 1)
ws = o.refs.get("world state")
if ws: show(merged[ws[0].target], 2)
print("\n--- items with instances by type:", collections.Counter(x.type_name for x in merged.values() if x.instances))
