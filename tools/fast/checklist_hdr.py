"""CHECKLIST п.2 (офлайн): dependencies/references из заголовков .mod в mods.cfg — отсутствует или стоит ниже зависимого."""
import os, glob, sys
sys.path.insert(0, r"C:\KenshiModMap\tools")
import kmod
GAME = r"C:\Program Files (x86)\Steam\steamapps\common\Kenshi"
W = r"C:\Program Files (x86)\Steam\steamapps\workshop\content\233860"
VAN = ["gamedata.base", "Newwworld.mod", "Dialogue.mod", "rebirth.mod"]
cfg = [l for l in open(os.path.join(GAME, "data", "mods.cfg"), "rb").read().decode("utf-8").split("\r\n") if l]
path = {os.path.basename(f): f for f in glob.glob(os.path.join(W, "*", "*.mod")) + glob.glob(os.path.join(GAME, "mods", "*", "*.mod"))}
pos = {m: i for i, m in enumerate(cfg)}
probs = []
for i, m in enumerate(cfg):
    h = kmod.read(path[m]).header
    for kind, lst in (("dependency", h.dependencies), ("reference", h.references)):
        for d in lst:
            if d in VAN: continue
            if d not in pos: probs.append((kind, m, d, "нет в mods.cfg"))
            elif pos[d] > i: probs.append((kind, m, d, f"стоит ниже (#{pos[d]+1} > #{i+1})"))
deps = [p for p in probs if p[0] == "dependency"]; refs = [p for p in probs if p[0] == "reference"]
print(f"проблем: dependencies {len(deps)} (нет: {sum('нет' in p[3] for p in deps)}, ниже: {sum('ниже' in p[3] for p in deps)}); references {len(refs)}")
for p in (deps + refs)[:20]: print(f"  {p[0][:3]} #{pos[p[1]]+1} {p[1]} → {p[2]}: {p[3]}")
