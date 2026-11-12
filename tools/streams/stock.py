"""Поток STOCK — генератор списков вещей для материализации складов (build/KMM_Stock/scripts/kmm_stock_items.lua).
Lua-поток: записей FCS не создаёт и чужих полей не меняет. Запуск (офлайн, < 5 с):
    python -I -X utf8 tools/streams/stock.py
Источники: data/catalog.json (оружие/броня: тир, происхождение), data/wardrobe_tiers.json (пулы брони фракций),
ванильные ITEM (еда, медицина, наркотики, роскошь, металл, скрап) — список ниже (SID проверены по gamedata.base,
Newwworld.mod, Dialogue.mod, rebirth.mod).
Исключено всегда: «божественное» (origin imperial/chaos/xenos, моды budget.json wh_mods), Crafting Redux (2PN8*),
дерево Relics (KMM_Tech), вещи вне каталога и из data/catalog_excluded.json — склад их не производит и в лавки не кладёт,
бюджет 2 % не трогается."""
import json
import os

ROOT = r"C:\KenshiModMap"
OUT = os.path.join(ROOT, "build", "KMM_Stock", "scripts", "kmm_stock_items.lua")
ITEM, WEAPON, ARMOUR = 4, 2, 3  # itemType для gamedata:getData(sid, type)

# категория → ярус богатства (0 бедный, 1 средний, 2 богатый) → [(sid, имя)]
GOODS = {
    "food": [
        [("50568-rebirth.mod", "Dried Gristle Flaps"), ("1016-gamedata.base", "Rice Bowl"), ("43957-rebirth.mod", "Gohan"),
         ("42334-changes_otto.mod", "Dried Meat"), ("43955-rebirth.mod", "Cooked Vegetables")],
        [("1946-gamedata.base", "Bread"), ("43956-rebirth.mod", "Chewsticks"), ("43961-rebirth.mod", "Dustwich"),
         ("43959-rebirth.mod", "Foodcube"), ("43960-rebirth.mod", "Meatwrap")],
        [("50518-Newwworld.mod", "Dried Fish"), ("50517-Newwworld.mod", "Thinfish"), ("42337-changes_otto.mod", "Ration Pack")],
    ],
    "med": [
        [("209-gamedata.base", "Basic First Aid Kit"), ("582-gamedata.base", "Medical Supplies")],
        [("515-gamedata.base", "Standard first aid kit"), ("1435-gamedata.base", "Splint Kit")],
        [("1359-gamedata.base", "Advanced First Aid Kit"), ("1436-gamedata.base", "Advanced Splint Kit")],
    ],
    "drugs": [
        [("42311-changes_otto.mod", "Grog"), ("43316-rebirth.mod", "Bloodrum")],
        [("42310-changes_otto.mod", "Sake"), ("1015-gamedata.base", "Cactus Rum")],
        [("1230-gamedata.base", "Hashish")],
    ],
    "lux": [
        [("2292-gamedata.base", "Leather"), ("42316-changes_otto.mod", "Ceramic Bowl")],
        [("584-gamedata.base", "Fabrics"), ("1534063-Newwworld.mod", "Simple Rug")],
        [("585-gamedata.base", "Luxury Goods"), ("42330-changes_otto.mod", "Pearl Cup")],
    ],
    "metal": [
        [("1866-gamedata.base", "Raw Iron")],
        [("42159-gamedata.base", "Iron Plates"), ("42160-gamedata.base", "Copper Alloy Plates")],
        [("579-gamedata.base", "Steel bars")],
    ],
    "scrap": [
        [("42318-changes_otto.mod", "Gears"), ("43396-changes_otto.mod", "Hinge")],
        [("97090-rebirth.mod", "Spring Steel"), ("580-gamedata.base", "Building Material")],
        [("42164-gamedata.base", "Electrical Components")],
    ],
}
DIVINE_ORIGINS = ("imperial", "chaos", "xenos", "relic")
PER_TIER_ARMOUR, PER_TIER_WEAPON, GLOBAL_WEAPON = 10, 6, 24


def banned_mod(mod, wh):
    m = mod or ""
    return m in wh or m.startswith("2PN8") or "KMM_Tech" in m or "Crafting" in m


def build():
    cat = {i["sid"]: i for i in json.load(open(os.path.join(ROOT, "data", "catalog.json"), encoding="utf-8"))["items"]}
    exc = json.load(open(os.path.join(ROOT, "data", "catalog_excluded.json"), encoding="utf-8")).get("items", [])
    excl = set(x["sid"] if isinstance(x, dict) else x for x in exc)
    wh = set(json.load(open(os.path.join(ROOT, "rules", "budget.json"), encoding="utf-8"))["wh_mods"])
    tiers = json.load(open(os.path.join(ROOT, "data", "wardrobe_tiers.json"), encoding="utf-8"))["factions"]

    def ok(sid):
        i = cat.get(sid)
        return bool(i) and sid not in excl and not str(i.get("origin", "")).startswith(DIVINE_ORIGINS) and not banned_mod(i.get("mod"), wh) \
            and not i.get("race_lock")

    armour = {}
    for fname, ft in sorted(tiers.items()):
        row = []
        for t in ("T0", "T1", "T2", "T3"):
            pool = []
            groups = sorted((ft.get(t) or {}).items())
            k = 0
            while len(pool) < PER_TIER_ARMOUR and any(k < len(l) for _, l in groups):  # по кругу по слотам — разнообразие
                for _, l in groups:
                    if k < len(l) and ok(l[k]) and l[k] not in pool and len(pool) < PER_TIER_ARMOUR:
                        pool.append(l[k])
                k += 1
            row.append(pool)
        armour[fname] = row
    weapons_g = []
    for t in ("T0", "T1", "T2", "T3"):
        lst = sorted((i for i in cat.values() if i["type"] == "WEAPON" and i["tier"] == t and ok(i["sid"])
                      and not str(i.get("origin", "")).startswith("culture:")), key=lambda i: (-i.get("stat_score", 0), i["sid"]))
        weapons_g.append([i["sid"] for i in lst[:GLOBAL_WEAPON]])
    weapons_c = {}
    for i in sorted(cat.values(), key=lambda i: (-i.get("stat_score", 0), i["sid"])):
        o = str(i.get("origin", ""))
        if i["type"] == "WEAPON" and o.startswith("culture:") and ok(i["sid"]):
            row = weapons_c.setdefault(o[8:], [[], [], [], []])
            ti = int(i["tier"][1])
            if len(row[ti]) < PER_TIER_WEAPON:
                row[ti].append(i["sid"])
    return armour, weapons_g, weapons_c


def lua_str(s):
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def lua_list(lst):
    return "{" + ",".join(lua_str(x) for x in lst) + "}"


def main():
    armour, wg, wc = build()
    out = ["-- KMM_Stock: списки вещей для лавок/ящиков. СГЕНЕРИРОВАНО tools/streams/stock.py — не править руками.",
           "-- Без «божественного» (imperial/chaos/xenos, WH-моды), Crafting Redux и дерева Relics (KMM_Tech).",
           f"return {{ type = {{ ITEM = {ITEM}, WEAPON = {WEAPON}, ARMOUR = {ARMOUR} }},", " goods = {"]
    for c, tiers in GOODS.items():
        out.append(f"  {c} = {{" + ",".join(lua_list([s for s, _ in t]) for t in tiers) + "},")
    out.append(" },")
    out.append(" weapons = {" + ",".join(lua_list(t) for t in wg) + "},")
    out.append(" weapons_culture = {")
    for f, row in sorted(wc.items()):
        out.append(f"  [{lua_str(f)}] = {{" + ",".join(lua_list(t) for t in row) + "},")
    out.append(" },")
    out.append(" armour = {")
    for f, row in sorted(armour.items()):
        out.append(f"  [{lua_str(f)}] = {{" + ",".join(lua_list(t) for t in row) + "},")
    out.append(" },")
    out.append("}")
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, "w", encoding="utf-8", newline="\n").write("\n".join(out) + "\n")
    na = sum(len(t) for r in armour.values() for t in r)
    print(f"{OUT}: goods {sum(len(t) for v in GOODS.values() for t in v)}, weapons {sum(len(t) for t in wg)} + culture "
          f"{sum(len(t) for r in wc.values() for t in r)} ({len(wc)} cultures), armour {na} ({len(armour)} factions)")


def check():
    """Офлайн-проверка списков: ванильные SID товаров существуют как ITEM; в оружии/броне нет «божественного» и CR."""
    import sys
    sys.path.insert(0, os.path.join(ROOT, "tools"))
    import kmod
    data = r"C:\Program Files (x86)\Steam\steamapps\common\Kenshi\data"
    merged = {}
    for f in ("gamedata.base", "Newwworld.mod", "Dialogue.mod", "rebirth.mod"):
        kmod.apply(merged, kmod.read(os.path.join(data, f)))
    errs = []
    for c, tiers in GOODS.items():
        for t in tiers:
            for sid, nm in t:
                it = merged.get(sid)
                if not it or kmod.type_name(it.type) != "ITEM":
                    errs.append(f"{c}: {sid} ({nm}) нет ITEM в ванили")
    cat = {i["sid"]: i for i in json.load(open(os.path.join(ROOT, "data", "catalog.json"), encoding="utf-8"))["items"]}
    armour, wg, wc = build()
    for sid in [x for r in armour.values() for t in r for x in t] + [x for t in wg for x in t] + [x for r in wc.values() for t in r for x in t]:
        i = cat.get(sid)
        if not i or str(i.get("origin", "")).startswith(DIVINE_ORIGINS) or str(i.get("mod", "")).startswith("2PN8"):
            errs.append(f"gear: {sid} вне каталога или «божественное»/CR")
    for e in errs:
        print("ERROR", e)
    print(f"stock check: {len(errs)} errors")
    return 1 if errs else 0


if __name__ == "__main__":
    import sys
    if "--check" in sys.argv:
        sys.exit(check())
    main()
