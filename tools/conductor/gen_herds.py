"""Генератор herds.json для KMM_Herds.lua: экология дальнего мира (стада, хищники, охотники).
Запуск: python -I -X utf8 tools/conductor/gen_herds.py   (грузит Ctx ~минуты; игру не трогает)
Данные: отряды животных = SQUAD_TEMPLATE с refs 'animals' (главное животное — по v1); фракции — дикие (Herbivore, Goats, Wild Bulls, Wildlife,
Wolves, Spiders, Blood Spiders, Gutters, Bone Jackals, Savannah Hounds...). Отряды с 'world state' и 'forbidden' отбрасываются.
Биом: прямых координат спавна в данных нет (зоны .zone не разбираем). Заменитель — «якоря обитания»: города/владения из conductor.json town_info,
в чьих residents/bar squads/roaming squads есть отряд с этим животным. Нет >=4 якорей — маршрут по всем точкам (города+руины), anchored=false.
Маршрут: цикл из 4 точек, смещение по циклу и старт — от seed, детерминированно.
2026-11-14: среда обитания = настоящие регионы карты. areasmap.tga (256x256, цвет = BIOME_GROUP.index 0xRRGGBB; x/z -> пиксель
int((x+147456)/1152), без переворота — как tools/conductor/gen_outlaws.py). Регионы вида = BIOME_GROUP, в чьих homeless spawns есть отряд с его
животным, плюс соседние (общая граница пикселей). Точки маршрута = города/руины внутри этих регионов; меньше 4 — добор клетками региона
(sid "biome:<регион>:<n>"). Регионов нет — старые якоря по городам, затем все точки."""
import collections
import json
import math
import os
import random
import re
import sys

sys.path.insert(0, r"C:\KenshiModMap\tools")
sys.path.insert(0, r"C:\KenshiModMap\tools\build")
ROOT = r"C:\KenshiModMap"
OUT = os.path.join(ROOT, "build", "KMM_Conductor", "herds.json")
SEED = 20261113
AREAS = os.path.join(r"C:/Program Files (x86)/Steam/steamapps/common/Kenshi", "data", "newland", "land", "areasmap.tga")
ORIGIN, PX = 147456, 1152


def biome_map(M):
    """-> (cell(x,z)->имя региона|None, adj{имя:set}, cells{имя:[(px,py)]}) по areasmap.tga и BIOME_GROUP.index."""
    from PIL import Image
    im = Image.open(AREAS).convert("RGB")
    W, H = im.size
    bg = {}
    for t in M.values():
        if t.type_name == "BIOME_GROUP" and not t.values.get("REMOVED"):
            bg.setdefault(int(t.values.get("index", 0)) & 0xFFFFFF, t.name)
    grid = [[None] * H for _ in range(W)]
    cells = collections.defaultdict(list)
    for x in range(W):
        for y in range(H):
            r, g, b = im.getpixel((x, y))
            n = bg.get((r << 16) | (g << 8) | b)
            if n and n != "NONE":
                grid[x][y] = n
                cells[n].append((x, y))
    adj = collections.defaultdict(set)
    for x in range(W):
        for y in range(H):
            a = grid[x][y]
            if not a:
                continue
            for dx, dy in ((1, 0), (0, 1)):
                if x + dx < W and y + dy < H:
                    b2 = grid[x + dx][y + dy]
                    if b2 and b2 != a:
                        adj[a].add(b2); adj[b2].add(a)

    def at(x, z):
        return grid[max(0, min(W - 1, int((x + ORIGIN) / PX)))][max(0, min(H - 1, int((z + ORIGIN) / PX)))]
    return at, adj, cells

# key -> (метка en, роль, фракция-имя, имена главных животных, имена для якорей обитания)
SPECIES = {
    "garru": ("Garru", "herd", "Herbivore", {"Garru", "Greater Garru"}, {"Garru", "Greater Garru"}),
    "goat": ("goats", "herd", "Goats", {"Goat"}, {"Goat"}),
    "bull": ("wild bulls", "herd", "Wild Bulls", {"Wild Bull"}, {"Wild Bull", "Domesticated Bull", "Pack Bull"}),
    "turtle": ("swamp turtles", "herd", "Wildlife", {"Swamp Turtle"}, {"Swamp Turtle"}),
    "leviathan": ("leviathans", "herd", "Wildlife", {"Leviathan"}, {"Leviathan", "Runty Leviathan"}),
    "horse": ("wild horses", "herd", "Herbivore", {"Wild Horse"}, {"Wild Horse"}),
    "bonedog": ("bonedogs", "pred", "Wolves", {"Bonedog", "Bloodhound"}, {"Bonedog", "Crested Bonedog", "Bone Mutt"}),
    "jackal": ("bone jackals", "pred", "Bone Jackals", {"Bone Jackal"}, {"Bone Jackal"}),
    "savhound": ("savannah hounds", "pred", "Savannah Hounds", {"Savannah Hound"}, {"Savannah Hound", "Dust Hound"}),
    "beak": ("beak things", "pred", "Gutters", {"Beak Thing"}, {"Beak Thing"}),
    "skinspider": ("skin spiders", "pred", "Spiders", {"Skin Spider"}, {"Skin Spider"}),
    "bloodspider": ("blood spiders", "pred", "Blood Spiders", {"Blood Spider"}, {"Blood Spider"}),
}
# кто идёт за кем (первый, у кого есть отряды)
FOLLOW = {"garru": ["bonedog", "savhound"], "goat": ["bonedog", "jackal"], "bull": ["savhound", "bonedog"], "turtle": ["beak", "skinspider"],
          "leviathan": ["bloodspider", "beak"], "horse": ["savhound", "bonedog"]}
HERDS = ["garru", "garru", "garru", "goat", "goat", "goat", "bull", "bull", "turtle", "leviathan", "horse"]   # 11 стад
HUNTER_NAMES = ["Nomads", "Drifters", "Cannibal Hunters"]
PARAMS = {"_doc": "KMM_Herds: params правятся руками; species/herds/hunters генерируются gen_herds.py", "cycle_days": 30, "stay": 0.4, "pred_delay": 4,
          "hunt_delay": 9, "near_r": 45000, "max_live": 3, "live_days": 1.0, "cooldown_days": 3.0, "global_cd_days": 0.5, "tick_sec": 25,
          "aim_town": True, "herd_size": [8, 14], "pred_size": [4, 8], "hunter_size": 4,
          "glut": {"herd": {"food": 0.08, "lux": 0.03}, "hunt": {"food": 0.2, "lux": 0.1}, "cap": 1.6, "range": 35000}, "max_events_day": 3, "seed": SEED}


def main():
    import kmm_build
    ctx = kmm_build.Ctx()
    M = ctx.M
    cond = json.load(open(os.path.join(ROOT, "build", "KMM_Conductor", "conductor.json"), encoding="utf-8"))
    ti = {k: v for k, v in cond["town_info"].items() if v.get("x") is not None}
    sites = [s for s in cond["sites"] if s.get("x") is not None]
    traces = json.load(open(os.path.join(ROOT, "build", "KMM_Conductor", "traces.json"), encoding="utf-8"))["factions"]
    fid_by_name = collections.defaultdict(list)
    for f in M.values():
        if f.type_name == "FACTION" and ctx.in_game(f.sid):
            fid_by_name[f.name].append(f.sid)
    sq_main = {}
    for q in ctx.all("SQUAD_TEMPLATE"):
        an = q.refs.get("animals", [])
        if not an:
            continue
        main = max(an, key=lambda r: (r.v1 or 0, r.v2 or 0))
        m = M.get(main.target)
        if m is None:
            continue
        sq_main[q.sid] = (q, m.name, main.v0 or 0, main.v1 or 0)
    home = collections.defaultdict(set)
    for t in M.values():
        if t.type_name != "TOWN" or t.sid not in ti:
            continue
        for k in ("residents", "bar squads", "roaming squads", "default resident"):
            for r in t.refs.get(k, []):
                if r.target in sq_main:
                    home[sq_main[r.target][1]].add(t.sid)
    at, adj, cells = biome_map(M)
    regions_of = collections.defaultdict(set)   # имя животного -> регионы, где его отряды в BIOME_GROUP.homeless spawns
    for b in M.values():
        if b.type_name == "BIOME_GROUP" and not b.values.get("REMOVED") and b.name in cells:
            for r in b.refs.get("homeless spawns", []):
                if r.target in sq_main:
                    regions_of[sq_main[r.target][1]].add(b.name)
    rng = random.Random(SEED)
    species = {}
    for key, (label, role, facname, names, anames) in SPECIES.items():
        fids = fid_by_name.get(facname, [])
        if not fids:
            continue
        sqs = []
        for sid, (q, mname, mn, mx) in sq_main.items():
            if mname not in names or q.refs.get("world state") or re.search(r"forbidden|loner|lone\b", q.name, re.I):
                continue
            if not any(r.target in fids for r in q.refs.get("faction", [])):
                continue
            sqs.append({"sid": sid, "name": q.name, "min": mn, "max": mx})
        if not sqs:
            continue
        anch = sorted({t for n in anames for t in home.get(n, ())})
        core = sorted({rg for n in anames for rg in regions_of.get(n, ())})
        hab = sorted(set(core) | {a for rg in core for a in adj.get(rg, ())})
        species[key] = {"label": label, "role": role, "fid": fids[0], "squads": sorted(sqs, key=lambda x: (-x["max"], x["sid"])), "anchors": anch,
                        "regions": core, "habitat": hab}
    pts_all = [{"sid": k, "name": v["name"], "x": v["x"], "z": v["z"]} for k, v in sorted(ti.items())] + \
              [{"sid": s["sid"], "name": s["name"], "x": s["x"], "z": s["z"]} for s in sites]

    def d(a, b):
        return math.hypot(a["x"] - b["x"], a["z"] - b["z"])
    used_start = set()
    used_pts = set()
    herds = []
    for i, key in enumerate(HERDS):
        sp = species.get(key)
        if not sp:
            continue
        anch = set(sp["anchors"])
        hab = set(sp.get("habitat") or [])
        mode = "all"
        if hab:
            mode = "biome"
            core = set(sp.get("regions") or [])   # сначала регионы, где вид реально водится; соседние — если там точек мало
            pool = [p for p in pts_all if at(p["x"], p["z"]) in core]
            if len(pool) < 4:
                pool = [p for p in pts_all if at(p["x"], p["z"]) in hab]
            if len(pool) < 4:   # добор клетками регионов обитания (детерминированно от SEED)
                cl = sorted(c for rg in sorted(hab) for c in cells.get(rg, ()))
                for n, (cx, cy) in enumerate(rng.sample(cl, min(len(cl), 12))):
                    rg = at(cx * PX - ORIGIN + PX / 2, cy * PX - ORIGIN + PX / 2)
                    pool.append({"sid": f"biome:{rg}:{n}", "name": rg, "x": int(cx * PX - ORIGIN + PX / 2), "z": int(cy * PX - ORIGIN + PX / 2)})
        elif len(anch) >= 4:
            mode = "towns"
            pool = [p for p in pts_all if p["sid"] in anch]
        else:
            pool = pts_all
        starts = [p for p in pool if p["sid"] not in used_start and p["sid"] not in used_pts] or [p for p in pool if p["sid"] not in used_start] or pool
        cur = rng.choice(starts)
        used_start.add(cur["sid"])
        route = [cur]
        for _ in range(3):
            cand = [p for p in pool if p not in route and 15000 <= d(p, route[-1]) <= 75000]
            fresh = [p for p in cand if p["sid"] not in used_pts]   # стада не делят точки маршрута, если есть выбор
            cand = fresh or cand
            if not cand and mode == "biome":
                cand = [p for p in pool if p not in route]
            if not cand:
                cand = [p for p in pts_all if p not in route and 15000 <= d(p, route[-1]) <= 90000]
            cand.sort(key=lambda p: d(p, route[-1]))
            route.append(rng.choice(cand[:3]) if cand else rng.choice(pts_all))
        used_pts.update(p["sid"] for p in route)
        pred = next((k for k in FOLLOW.get(key, []) if k in species), None)
        herds.append({"id": f"h{i + 1}", "species": key, "pred": pred, "off": round(rng.uniform(0, 30), 1), "anchored": mode != "all", "habitat": mode,
                      "route": [{"sid": p["sid"], "name": p["name"], "x": p["x"], "z": p["z"]} for p in route]})
    hunters = [fid for n in HUNTER_NAMES for fid, e in sorted(traces.items()) if e["name"] == n and e.get("tiers")]
    out = {"_doc": "KMM_Herds data (tools/conductor/gen_herds.py). Не править руками, кроме params.", "params": PARAMS, "species": species, "herds": herds,
           "hunters": hunters}
    json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("species (squads, anchors):", {k: (len(v["squads"]), len(v["anchors"])) for k, v in species.items()})
    print("regions:", {k: (len(v["regions"]), len(v["habitat"])) for k, v in species.items()})
    print("herds", len(herds), [(h["id"], h["species"], h["pred"], h["habitat"], [p["name"] for p in h["route"]]) for h in herds], "hunters", hunters)


if __name__ == "__main__":
    main()
