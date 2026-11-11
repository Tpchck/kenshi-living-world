"""Генерирует scripts/kmm_rumors_towns.lua: позиции городов (ванильный townlist) для задержки/направления слухов.
python -I -X utf8 build/KMM_Rumors/tools/gen_towns.py"""
import sys, os
sys.path.insert(0, r"C:\KenshiModMap\tools")
import kmod
L = r"C:\Program Files (x86)\Steam\steamapps\common\Kenshi\data\newland\leveldata"
D = r"C:\Program Files (x86)\Steam\steamapps\common\Kenshi\data"
names = kmod.load_chain([os.path.join(D, f) for f in ["gamedata.base", "Newwworld.mod", "Dialogue.mod", "rebirth.mod"]])
pos = {}
for sub in ["Newwworld", "Dialogue", "rebirth"]:
    p = os.path.join(L, sub, "leveldata.level")
    if not os.path.exists(p):
        continue
    for it in kmod.read(p).items:
        if it.type_name == "GAMESTATE_TOWN_INSTANCE_LIST":
            for ins in it.instances:
                pos[ins.target] = ins.pos
q = lambda s: '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'
out = ["-- сгенерировано tools/gen_towns.py из ванильного townlist (rebirth/Newwworld/Dialogue leveldata.level)", "return {"]
for sid, (x, y, z) in sorted(pos.items()):
    n = names[sid].name if sid in names else sid
    out.append(f"  [{q(sid)}] = {{ x = {x:.0f}, z = {z:.0f}, name = {q(n)} }},")
out.append("}")
dst = r"C:\KenshiModMap\build\KMM_Rumors\scripts\kmm_rumors_towns.lua"
open(dst, "w", encoding="utf-8", newline="\n").write("\n".join(out) + "\n")
print("towns", len(pos), "->", dst)
