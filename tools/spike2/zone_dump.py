import sys, collections; sys.path.insert(0, r"C:\KenshiModMap\tools")
import kmod
K = "C:/Program Files (x86)/Steam/steamapps/common/Kenshi/data/newland/leveldata/"
m = kmod.read(K + "Newwworld/zone.51.8.zone")
print("type", m.ftype, "last", m.last_id, "items", len(m.items), "tail", len(m.tail_ids or []))
print(collections.Counter(i.type_name for i in m.items))
ic = [i for i in m.items if i.type_name == "INSTANCE_COLLECTION"]
for c in ic: print("IC", c.sid, c.name, c.values, len(c.instances), c.instances[:2])
gb = [i for i in m.items if i.type_name == "GAMESTATE_BUILDING"][:3]
for g in gb: print("GB", g.sid, g.name, g.values, g.refs, g.instances[:2])
xs = [ins.pos for c in ic for ins in c.instances]
print("x range", min(p[0] for p in xs), max(p[0] for p in xs), "z range", min(p[2] for p in xs), max(p[2] for p in xs))
