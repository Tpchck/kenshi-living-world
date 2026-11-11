import sys, glob, os; sys.path.insert(0, r"C:\KenshiModMap\tools")
import kmod
K = "C:/Program Files (x86)/Steam/steamapps/common/Kenshi/data/"
BARK = "1076-gamedata.base"
for f in [K+"newland/leveldata.level"] + glob.glob(K+"newland/leveldata/*/leveldata.level"):
    m = kmod.read(f)
    print(os.path.relpath(f, K), "type", m.ftype, "items", len(m.items), [(i.type_name, len(i.instances), len(i.values), list(i.refs)[:3]) for i in m.items[:3]])
    for it in m.items:
        for ins in it.instances:
            if ins.target == BARK or BARK in ins.states: print("   BARK instance:", it.type_name, it.sid, ins)
