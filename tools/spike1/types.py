import sys, collections
sys.path.insert(0, r"C:\KenshiModMap\tools")
import kmod
K = r"C:\Program Files (x86)\Steam\steamapps\common\Kenshi\data"
seen = collections.defaultdict(list)
for fn in ["gamedata.base", "Newwworld.mod", "rebirth.mod"]:
    for it in kmod.read(K + "\\" + fn).items:
        if len(seen[it.type]) < 4: seen[it.type].append(it.name)
for t in sorted(seen): print(t, kmod.type_name(t), seen[t])
