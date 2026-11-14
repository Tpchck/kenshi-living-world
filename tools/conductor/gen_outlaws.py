"""Генератор outlaws.json для KMM_Outlaws.lua: «живые» разыскиваемые (2026-11-14).
Запуск: python -I -X utf8 tools/conductor/gen_outlaws.py [--print]   (грузит Ctx ~минуты; игру не трогает)

Родная основа (не свои переменные):
- регионы = BIOME_GROUP; карта регионов = data/newland/land/areasmap.tga (256x256, цвет пикселя = BIOME_GROUP.index 0xRRGGBB);
  мир 64 зоны x 4608 ед., начало -147456 -> 1152 ед. на пиксель (сверено: Admag=Stenn Desert, Heng=Heng, Mud Town/Shark=The Swamp,
  Squin/The Hub=Border Zone, Mongrel=Fog Islands).
- соседство регионов = общие границы пикселей карты (кочуют по своему региону и соседним — климат меняется плавно).
- банды региона = фракции отрядов BIOME_GROUP.homeless spawns (родные бродячие банды региона), только те, что есть в traces.json
  (есть тир-шаблоны для спавна) и враждебны игроку по умолчанию (бандиты, а не караваны/звери).
- города для рэкета = публичные города региона с фракцией-владельцем (data/atlas_cleanup.json), без лагерей KMM_Cleanup.
Выход: build/KMM_Conductor/outlaws.json = { regions: {name: {adj, gangs, towns:[{sid,name,fid,x,z}], spots:[[x,z]...]}}, gangs: {fid: name} }"""
import collections
import json
import math
import os
import random
import sys

ROOT = r"C:\KenshiModMap"
for _p in ("", "build", "fast"):
    sys.path.insert(0, os.path.join(ROOT, "tools", _p))
OUT = os.path.join(ROOT, "build", "KMM_Conductor", "outlaws.json")
AREAS = r"C:\Program Files (x86)\Steam\steamapps\common\Kenshi\data\newland\land\areasmap.tga"
ORIGIN, PX = 147456, 1152
SEED = 20261114
GANG = ("bandit", "raider", "thie", "outlaw", "gang", "skin", "hungry", "rust", "cannibal", "pirate", "reaver", "band of", "berserk",
        "peddler", "ninja", "smuggl", "brigand", "marauder", "cutthroat", "rogue", "deserter")
NOT_GANG = ("wildlife", "herbivore", "goats", "wild bulls", "wolves", "spiders", "beak", "animal", "gutters", "jackal", "hounds", "fogmen",
            "crab", "slaver", "trader", "caravan", "nomad", "pilgrim", "drifter", "mercenar", "hunter", "farmer", "refugee", "beggar")


def pix(x, z):
    return max(0, min(255, int((x + ORIGIN) / PX))), max(0, min(255, int((z + ORIGIN) / PX)))


def main(show=False):
    import kmm_build as kb
    from PIL import Image
    ctx = kb.Ctx()
    M = ctx.M
    im = Image.open(AREAS).convert("RGB")
    W, H = im.size
    bg = {}
    for t in M.values():
        if t.type_name == "BIOME_GROUP" and not t.values.get("REMOVED"):
            bg.setdefault(int(t.values.get("index", 0)) & 0xFFFFFF, t)
    cell = [[None] * H for _ in range(W)]
    for x in range(W):
        for y in range(H):
            r, g, b = im.getpixel((x, y))
            t = bg.get((r << 16) | (g << 8) | b)
            cell[x][y] = t.name if t else None
    adj = collections.defaultdict(set)
    area = collections.Counter()
    for x in range(W):
        for y in range(H):
            a = cell[x][y]
            if not a or a == "NONE":
                continue
            area[a] += 1
            for dx, dy in ((1, 0), (0, 1)):
                if x + dx < W and y + dy < H:
                    b2 = cell[x + dx][y + dy]
                    if b2 and b2 != a and b2 != "NONE":
                        adj[a].add(b2); adj[b2].add(a)
    tr = json.load(open(os.path.join(ROOT, "build", "KMM_Conductor", "traces.json"), encoding="utf-8"))["factions"]
    cond = json.load(open(os.path.join(ROOT, "build", "KMM_Conductor", "conductor.json"), encoding="utf-8"))
    pf = cond.get("player_faction")

    def is_gang(fid):   # родная вражда к игроку в данных не хранится (Nameless без relations) -> признак по имени фракции
        f = M.get(fid)
        if not f or fid not in tr or not (tr[fid].get("tiers")):
            return False
        nm = f.name.lower()
        if any(k in nm for k in NOT_GANG):
            return False
        return any(k in nm for k in GANG)

    gangs_of = collections.defaultdict(collections.Counter)
    for name, t in ((t.name, t) for t in bg.values()):
        for r in t.refs.get("homeless spawns", []):
            q = M.get(r.target)
            if not q:
                continue
            for fr in q.refs.get("faction", []):
                if is_gang(fr.target):
                    gangs_of[name][fr.target] += max(1, int(r.v1 or 1))
    for f in M.values():   # FACTION.biomes — территория фракции (родное поле): банда живёт и в своих регионах
        if f.type_name == "FACTION" and is_gang(f.sid):
            for r in f.refs.get("biomes", []):
                if r.target in M:
                    gangs_of[M[r.target].name][f.sid] += 2
    atlas = json.load(open(os.path.join(ROOT, "data", "atlas_cleanup.json"), encoding="utf-8"))
    clean = {c["camp"] for c in json.load(open(os.path.join(ROOT, "rules", "cleanup.json"), encoding="utf-8"))["camps"]}
    towns_of = collections.defaultdict(list)
    for t in atlas["towns"]:
        if t.get("x") is None or not t.get("public") or t["sid"] in clean or not t.get("owner_sid"):
            continue
        if t.get("members_est", 0) < 8 or t["owner_sid"] == pf:
            continue
        px, pz = pix(t["x"], t["z"])
        rg = cell[px][pz]
        if rg and rg != "NONE":
            towns_of[rg].append({"sid": t["sid"], "name": t["name"], "fid": t["owner_sid"], "x": round(t["x"]), "z": round(t["z"])})
    rnd = random.Random(SEED)
    regions = {}
    for rg, n in area.items():
        g = gangs_of.get(rg)
        tw = sorted(towns_of.get(rg, []), key=lambda d: d["sid"])
        if not g and not tw:
            continue
        pts = [(x, y) for x in range(W) for y in range(H) if cell[x][y] == rg]
        rnd.shuffle(pts)
        spots = [[int(x * PX - ORIGIN + PX / 2), int(y * PX - ORIGIN + PX / 2)] for x, y in pts[:12]]
        regions[rg] = {"adj": sorted(adj[rg]), "gangs": [f for f, _ in g.most_common(6)] if g else [], "towns": tw, "spots": spots, "area": n}
    for rg in regions:
        regions[rg]["adj"] = [a for a in regions[rg]["adj"] if a in regions]
    gangs = sorted({f for r in regions.values() for f in r["gangs"]})
    out = {"_doc": __doc__.split("\n")[0], "version": 1, "seed": SEED,
           "regions": dict(sorted(regions.items())), "gangs": {f: M[f].name for f in gangs}}
    json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    home = [r for r, v in regions.items() if v["gangs"] and v["towns"]]
    print(f"outlaws.json: регионов {len(regions)}, с бандами и городами {len(home)}, банд {len(gangs)}, городов {sum(len(v['towns']) for v in regions.values())}")
    if show:
        for r, v in sorted(regions.items()):
            print(f"  {r}: банды {[M[f].name for f in v['gangs']]} города {[t['name'] for t in v['towns']][:6]} сосед {v['adj'][:5]}")


if __name__ == "__main__":
    main("--print" in sys.argv)
