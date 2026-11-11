"""Каталог предметов сборки (поток G WARDROBE): ваниль + основа + WH (без KMM_*) → data/catalog.json.

Для каждого ARMOUR / WEAPON / CROSSBOW: слот, тир (перцентиль силы по статам внутри слота/категории, 80 %; цена — поправка 20 %), происхождение
(WH-имперское / ксенос / хаос / культура ванильной фракции по тем, кто это носит и продаёт / самоделка / общее),
стиль (ключевые слова), мод-источник, носители (фракции) и торговые списки.
Кандидаты из Workshop, которых нет на диске, сюда не попадают — их считаем после подписки.
python -I -X utf8 tools/catalog.py
"""
import collections
import json
import os
import re
import sys

sys.path.insert(0, r"C:\KenshiModMap\tools")
sys.path.insert(0, r"C:\KenshiModMap\tools\fast")
import ctx  # noqa: E402
import kmod  # noqa: E402

ROOT = r"C:\KenshiModMap"
ATTACH = ["weapon", "back", "hair", "hat", "eyes", "body", "legs", "none", "shirt", "boots", "gloves", "neck", "backpack", "beard", "belt"]
WEAPON_CAT = {0: "katana", 1: "sabre", 2: "hacker", 3: "blunt", 4: "heavy", 5: "polearm", 6: "unarmed", 7: "bow", 8: "turret", 9: "ninja"}
WH_IMPERIAL = {"wh40k_imperial_forces.mod", "Death Korps of Krieg.mod", "Steel Legion Armor Mod.mod", "KMM_Relics.mod"}
WH_XENOS = {"OrcRaceReview.mod", "40K Necrons.mod"}
WH_MIXED = {"TEXT TEXTURE.mod"}  # Mark-X: Astartes + Chaos — по ключевым словам
EXCLUDE_MODS = {"ChaosDaemonsStandalone.mod"}  # «оружие» демонов — природные когти расы, не снаряжение (в гардероб не идёт)
CHAOS_RX = re.compile(r"chaos|khorn|nurg|slaan|tzeen|world eater|night lord|midnight|daemon|demon", re.I)
SELF_RX = re.compile(r"rag|scrap|makeshift|home ?made|crude|trash|junk|improvis|stitch|patch|tatter|salvag|rust|torn|scavenged|worn|failing|jammed|\[T0", re.I)
STYLE = {"rags": r"rag|tatter|torn|cloth|robe|shirt|wrap|poncho|cape|cloak",
         "scrap": r"scrap|junk|trash|salvag|makeshift|rust|crude|improvis",
         "leather": r"leather|hide|fur|pelt|skin",
         "chain": r"chain|mail",
         "plate": r"plate|armou?r|cuirass|breastplate|samurai|heavy",
         "power": r"power|terminator|astartes|mark|mk\s?[ivx\d]|exo|servo",
         "carapace": r"carapace|flak|guard(?:sman)?|cadian|krieg|steel legion",
         "masked": r"mask|gas|respirator|helmet|helm|visor",
         "holy": r"holy|paladin|inquisit|okran",
         "tribal": r"bone|tribal|skull|tusk|horn|totem",
         "cyber": r"cyber|robot|mech|tech|laser|las|plasma|gauss|bolt",
         "xenos": r"necron|orc|ork|choppa|greenskin|xenos"}
STYLE = {k: re.compile(v, re.I) for k, v in STYLE.items()}


NONLATIN = re.compile(r"[Ѐ-ӿ　-鿿가-힯]")   # кириллица / CJK / хангыль в названии
RW = json.load(open(os.path.join(ROOT, "rules", "streams", "wardrobe.json"), encoding="utf-8")).get("ranged", {})
R_ALLOW, R_DENY = re.compile(RW.get("allow_rx", "$^"), re.I), re.compile(RW.get("deny_rx", "$^"), re.I)
R_ALLOW_FIRST = re.compile(RW.get("allow_first_rx", "$^"), re.I)   # однозарядные кремнёвки и т.п.: проверяются ДО общего запрета («rifle», «revolver»)
R_HARD = re.compile(RW.get("hard_deny_rx", "$^"), re.I)           # многоствольные/скорострельные/осадные: запрет даже для allow_first
R_FIREARM = re.compile(RW.get("firearm_rx", "$^"), re.I)          # порох (а не лук/арбалет): для правил техуровня фракций


def ranged_class(name, mod, i):
    """Правило владельца: NPC — только однозарядное/двуствольное/арбалет/лук/гарпун/джезайл, вписывающееся в мир.
    allow: подходит; wh: WH-оружие (только у WH-фракций, 2 %); reject:<причина>."""
    if mod in RW.get("deny_mods", []):
        return "reject:mod"
    if NONLATIN.search(name):
        return "reject:nonlatin"
    if R_HARD.search(name):
        return "reject:modern/energy/auto"
    if R_ALLOW_FIRST.search(name):
        return "allow"
    if R_DENY.search(name):
        return "reject:modern/energy/auto"
    if R_ALLOW.search(name):
        return "allow"
    return "reject:unclassified"


REJ = set(json.load(open(os.path.join(ROOT, "rules", "game_rejected_sids.json"), encoding="utf-8"))["sids"])


def ctx_in_game(sid):
    return sid not in REJ


def main():
    lo, van, base, wh = ctx.load()
    layers = van + base + wh   # без KMM_*: свои вещи потоки создают сами (sid KMM-модов меняются между сборками)
    # источник: мод из суффикса sid (если загружен), иначе первый определивший мод, кроме патчей совместимости
    # (MEGA Animation - Collection Pack заранее объявляет заглушки предметов чужих модов и грузится первым)
    COMPAT = {"Animation - Collection Pack.mod", "MEGA - Item Integration Patch.mod"}
    loaded = {n for n, _, _ in layers}
    M, first = {}, {}
    for n, m, _ in layers:
        for it in m.items:
            if (it.change == kmod.CHANGE_NEW or n in ctx.VANILLA) and n not in COMPAT:
                first.setdefault(it.sid, n)
        kmod.apply(M, m)
    origin = {}
    for sid in M:
        mm = re.match(r"^\d+-(.+\.(?:mod|base))$", sid)
        origin[sid] = mm.group(1) if mm and mm.group(1) in loaded else first.get(sid, "?")
    # кто носит: персонаж → отряды → фракция
    char_fac = collections.defaultdict(collections.Counter)
    for sq in M.values():
        if sq.type_name not in ("SQUAD_TEMPLATE", "UNIQUE_SQUAD_TEMPLATE") or not sq.refs.get("faction"):
            continue
        f = M.get(sq.refs["faction"][0].target)
        for cat in ("leader", "squad", "squad2"):
            for r in sq.refs.get(cat, []):
                if f:
                    char_fac[r.target][f.name] += 1
    worn = collections.defaultdict(collections.Counter)
    for ch in M.values():
        if ch.type_name != "CHARACTER":
            continue
        for cat in ("clothing", "weapons", "crossbows", "backpack"):
            for r in ch.refs.get(cat, []):
                for fn, k in char_fac.get(ch.sid, {}).items():
                    worn[r.target][fn] += k
    sold = collections.defaultdict(list)
    for vl in M.values():
        if vl.type_name == "VENDOR_LIST":
            for cat, rs in vl.refs.items():
                for r in rs:
                    sold[r.target].append(vl.name)

    MESH = ("mesh", "mesh female", "ground mesh", "bare sword", "sheath", "vest texture", "vest texture female")   # рубашки = текстура на теле (2026-11-13)
    ANIMAL_BP = re.compile(r"animal|bull|garru|crab|canine|dog\b|gorillo|spider|skimmer|raptor|goat|leviathan|behemoth|beak|bat\b|turtle|crimper|bovidae|cage beast|fiend|tyrant|"
                           r"crocuta|horned|grigori|direwolf|runty|soul|stack|cyberimplant|queen|john's|compression|spectral|undertaker|sentry|plates|pack_beast|bull_bags|"
                           r"[\/]animal[\/]", re.I)
    def is_human_backpack(i):
        """Рюкзак гуманоида: CONTAINER, slot 12 (backpack), своя модель, не вьюк животного, не уникальный/квестовый."""
        m = i.values.get("mesh")
        return (i.type_name == "CONTAINER" and i.values.get("slot") == 12 and isinstance(m, str) and m.strip()
                and re.search(r"backpack|knapsack|satchel|rucksack|\bbag\b|pack\b", i.name or "", re.I) and not re.search(r"quiver|crystal|barrel|luggage|mount|hat\b|basket|food", i.name or "", re.I)
                and not ANIMAL_BP.search(i.name or "") and not ANIMAL_BP.search(m))
    items = [i for i in M.values() if (i.type_name in ("ARMOUR", "WEAPON", "CROSSBOW") or is_human_backpack(i)) and i.name and ctx_in_game(i.sid)
             and any(isinstance(i.values.get(k), str) and i.values.get(k).strip() for k in MESH)
             and not (i.type_name == "ARMOUR" and i.values.get("slot") == 12)]   # только вещи с моделью; ARMOUR slot 12 = вьючная броня зверей
    phantom = [i for i in items if origin.get(i.sid, "?") == "?"]   # заглушки патча совместимости для модов вне сборки
    items = [i for i in items if origin.get(i.sid, "?") != "?"]
    def group(i):
        if i.type_name == "CONTAINER":
            return "armour:backpack"
        if i.type_name == "ARMOUR":
            s = i.values.get("slot")
            return "armour:" + (ATTACH[s] if isinstance(s, int) and 0 <= s < len(ATTACH) else str(s))
        if i.type_name == "WEAPON":
            return "weapon:" + WEAPON_CAT.get(i.values.get("skill category"), str(i.values.get("skill category")))
        return "crossbow"
    groups = collections.defaultdict(list)
    for i in items:
        groups[group(i)].append(i)
    def num(i, k, d=0.0):
        v = i.values.get(k, d)
        return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else d

    def stat_score(i):
        """Сила вещи по статам (без цены). Броня: материал × покрытие × (1+бонусы) + вес + боевые бонусы − штрафы подвижности.
        Оружие: урон × (1+бронебойность) + атака + вес. Арбалет: урон × точность × скорострельность + дальность."""
        if i.type_name == "ARMOUR":
            mat = {0: 1.0, 1: 2.0, 2: 3.0, 3: 4.0}.get(int(num(i, "material type", 0)), 1.0)
            cov = sum(r.v0 for r in i.refs.get("part coverage", [])) / 100.0
            bonus = num(i, "cut def bonus") + num(i, "blunt def bonus") + 0.5 * max(0.0, num(i, "pierce def mult", 1.0) - 1.0)
            mob = (1 - num(i, "combat speed mult", 1.0)) + 0.5 * (1 - num(i, "dodge mult", 1.0))
            return mat * max(cov, 0.2) * (1 + bonus) + 0.05 * min(num(i, "weight kg"), 25.0) + num(i, "combat def bonus") / 10 + num(i, "level bonus") / 20 - mob
        if i.type_name == "CONTAINER":
            return num(i, "value") / 1000.0
        if i.type_name == "WEAPON":
            dmg = num(i, "cut damage multiplier") + 0.8 * num(i, "blunt damage multiplier") + num(i, "pierce damage multiplier")
            return dmg * (1 + max(-0.5, num(i, "armour penetration"))) + num(i, "attack mod") / 20 + 0.05 * min(num(i, "weight kg"), 25.0)
        dmg = num(i, "pierce damage max 0", num(i, "pierce damage"))
        reload = max(0.5, (num(i, "reload time min", 3) + num(i, "reload time max", 4)) / 2)
        return dmg * (1 + num(i, "accuracy perfect skill") / 100) * max(1.0, num(i, "num shots", 1)) ** 0.3 / reload + num(i, "range") / 1000

    def pct(vals, v):
        n = len(vals)
        return (sum(1 for x in vals if x < v) + 0.5 * sum(1 for x in vals if x == v)) / max(1, n)

    tier, score_of = {}, {}
    for g, lst in groups.items():
        st = {i.sid: stat_score(i) for i in lst}
        pr = {i.sid: float(i.values.get("value", 0) or 0) for i in lst}
        sv, pv = sorted(st.values()), sorted(pr.values())
        for i in lst:
            p = 0.8 * pct(sv, st[i.sid]) + 0.2 * pct(pv, pr[i.sid])   # статы, цена — поправка
            score_of[i.sid] = round(st[i.sid], 3)
            tier[i.sid] = "T3" if p >= 0.97 else "T2" if p >= 0.70 else "T1" if p >= 0.30 else "T0"
            m = re.search(r"\[T(\d)", i.name)
            if m and i.sid.endswith("-KMM_Relics.mod"):
                tier[i.sid] = "T" + m.group(1)

    # --- исключения (rules/excluded_mods.json): моды по аудиту, вещи-части тела расы, меши, несовместимые со скелетом основы
    exr = json.load(open(os.path.join(ROOT, "rules", "excluded_mods.json"), encoding="utf-8"))
    skip_mods = EXCLUDE_MODS | set(exr["mods"])
    race_lock = {sid: [r.sid for r in M.values() if r.type_name == "RACE" and re.search(rx, r.name or "", re.I)]
                 for sid, rx in exr["item_race_lock"].items() if not sid.startswith("_")}
    import mesh_skel
    base_files = {b["file"] for b in lo["base"]}
    check_mods = set(exr.get("mesh_check_mods", {}).get("list") or []) or {x["file"] for x in lo["wh"] + lo.get("extra", [])}
    folders = {x["file"]: os.path.dirname(x["path"]) for x in lo["base"] + lo["wh"] + lo.get("extra", [])}
    files_by_name = {}
    for f, d in folders.items():
        if f in check_mods:
            for dp, _, fs in os.walk(d):
                for fn in fs:
                    if fn.lower().endswith(".mesh"):
                        files_by_name.setdefault(fn.lower(), os.path.join(dp, fn))
    van_names = set()
    for dp, _, fs in os.walk(os.path.join(ctx.DATA, "items")):
        van_names |= {fn.lower() for fn in fs}
    other_names = set()
    for f, d in folders.items():
        if f not in check_mods:
            for dp, _, fs in os.walk(d):
                other_names |= {fn.lower() for fn in fs if fn.lower().endswith(".mesh")}
    excluded_items = []

    def mesh_problem(i, src):
        if src not in check_mods or i.type_name not in ("ARMOUR", "WEAPON", "CONTAINER"):
            return None
        for k in (("mesh", "mesh female") if i.type_name in ("ARMOUR", "CONTAINER") else ("mesh", "bare sword", "sheath")):
            v = i.values.get(k)
            if not (isinstance(v, str) and v.strip()):
                continue
            n = v.replace("/", "\\").split("\\")[-1].strip().lower()
            p = files_by_name.get(n)
            if p is None:
                if n in van_names or n in other_names:
                    continue
                return f"{k}: нет файла {n}"
            r = mesh_skel.check_mesh(p, [os.path.dirname(p), folders.get(src, "")])
            if r:
                return f"{k} {n}: {r}"
        return None

    out = []
    for i in items:
        src = origin.get(i.sid, "?")
        if src in skip_mods:
            continue
        if i.sid in exr.get("items", {}):
            excluded_items.append({"sid": i.sid, "name": i.name, "mod": src, "reason": exr["items"][i.sid]})
            continue
        mp = mesh_problem(i, src)
        if mp:
            excluded_items.append({"sid": i.sid, "name": i.name, "mod": src, "reason": mp})
            continue
        fac = worn.get(i.sid, collections.Counter())
        name = i.name
        if src in WH_IMPERIAL:
            org = "imperial"
        elif src in WH_XENOS:
            org = "xenos"
        elif src in WH_MIXED:
            org = "chaos" if CHAOS_RX.search(name) else "imperial"
        elif SELF_RX.search(name):
            org = "selfmade"
        elif fac:
            org = "culture:" + fac.most_common(1)[0][0]
        else:
            org = "generic"
        styles = [k for k, rx in STYLE.items() if rx.search(name)]
        extra = {}
        if NONLATIN.search(name):
            extra["nonlatin"] = True   # нет английского имени — в пулы не берём
        if i.type_name == "CROSSBOW":
            extra["ranged"] = ranged_class(name, src, i)
            extra["firearm"] = bool(R_FIREARM.search(name))
        out.append({**extra, "sid": i.sid, "name": name, "type": i.type_name, "group": group(i), "tier": tier[i.sid], "stat_score": score_of[i.sid],
                    "value": int(i.values.get("value", 0) or 0), "origin": org, "styles": styles, "mod": src,
                    "worn_by": dict(fac.most_common(5)), "sold_in": sorted(set(sold.get(i.sid, [])))[:6]})
        if i.sid in race_lock:
            out[-1]["race_lock"] = race_lock[i.sid]
    json.dump({"_doc": "вещи, не попавшие в каталог/пулы: меш без файла или скелет не как у основы (растяжка на анимациях)",
               "items": excluded_items}, open(os.path.join(ROOT, "data", "catalog_excluded.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    os.makedirs(os.path.join(ROOT, "data"), exist_ok=True)
    json.dump({"_doc": __doc__, "count": len(out), "items": out}, open(os.path.join(ROOT, "data", "catalog.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=0)
    # --- хлам и лут для стартового инвентаря (CHARACTER inventory): мелкие нефункциональные ITEM из белого списка модов
    RL = json.load(open(os.path.join(ROOT, "rules", "streams", "wardrobe.json"), encoding="utf-8")).get("loot", {})
    bad = re.compile(RL.get("bad_rx", "$^"), re.I)
    loot = []
    for i in M.values():
        if i.type_name != "ITEM" or not i.name or not ctx_in_game(i.sid) or not i.name.isascii() or bad.search(i.name):
            continue
        src = origin.get(i.sid, "?")
        if src not in RL.get("mods", []) or i.values.get("artifact") or i.values.get("persistent") or i.values.get("food crop"):
            continue
        fn, val, wt = i.values.get("item function") or 0, int(i.values.get("value", 0) or 0), num(i, "weight kg")
        if wt > RL.get("max_weight", 6) or not (RL.get("min_value", 15) <= val <= RL.get("max_value", 6000)):
            continue
        if fn == 3:
            kind = "food"
        elif fn == 8:
            kind = "drug"
        elif fn == 13 and i.values.get("trade item"):
            kind = "book"
        elif fn == 0 and i.values.get("trade item"):
            kind = "luxury" if val >= 1000 else "junk"
        else:
            continue
        loot.append({"sid": i.sid, "name": i.name, "mod": src, "value": val, "kind": kind})
    json.dump({"_doc": "лут-пул CHARACTER inventory (tools/catalog.py, правила rules/streams/wardrobe.json loot)", "count": len(loot), "items": loot},
              open(os.path.join(ROOT, "data", "catalog_loot.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    # сводка
    def C(key):
        return collections.Counter(key(x) for x in out)
    summ = {"total": len(out), "loot": len(loot), "crossbow_ranged": dict(collections.Counter(x["ranged"] for x in out if x["type"] == "CROSSBOW")), "nonlatin": sum(1 for x in out if x.get("nonlatin")), "excluded_mesh": len(excluded_items), "race_locked": sum(1 for x in out if "race_lock" in x), "phantom_compat_stubs_excluded": len(phantom), "by_group": C(lambda x: x["group"]).most_common(),
            "by_tier": C(lambda x: x["tier"]).most_common(), "by_origin_class": C(lambda x: x["origin"].split(":")[0]).most_common(),
            "top_cultures": C(lambda x: x["origin"]).most_common(25),
            "by_style": collections.Counter(s for x in out for s in x["styles"]).most_common(),
            "unworn_unsold": sum(1 for x in out if not x["worn_by"] and not x["sold_in"]),
            "by_mod_top": C(lambda x: x["mod"]).most_common(20),
            "group_x_tier": {g: dict(collections.Counter(x["tier"] for x in out if x["group"] == g)) for g, _ in C(lambda x: x["group"]).most_common(12)}}
    json.dump(summ, open(os.path.join(ROOT, "data", "catalog_summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({k: v for k, v in summ.items() if k != "group_x_tier"}, ensure_ascii=False)[:3500])


if __name__ == "__main__":
    main()
