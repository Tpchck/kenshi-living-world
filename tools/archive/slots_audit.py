"""Аудит слотов экипировки (READ-ONLY): покрытие слот x культура x тир, наборы (сеты), кандидаты в мелкие слоты.
Вывод: data/slots_audit.json. План: docs/SLOTS_PLAN.md (пишется вручную по этим данным).
Запуск: python -I -X utf8 tools/slots_audit.py   (~1 мин). Ничего, кроме data/slots_audit.json, не пишет."""
import collections as C
import json
import os
import re
import sys

ROOT = r"C:\KenshiModMap"
sys.path.insert(0, ROOT + r"\tools")
sys.path.insert(0, ROOT + r"\tools\build")
import kmm_build  # noqa: E402
import kmod  # noqa: E402

SLOT = {3: "hat", 4: "eyes", 5: "body", 6: "legs", 8: "shirt", 9: "boots", 10: "gloves", 11: "neck", 12: "backpack", 14: "belt"}
MAIN = ["hat", "body", "shirt", "legs", "boots", "belt", "backpack", "eyes", "neck", "gloves"]
TIERS = ["T0", "T1", "T2", "T3"]
GENERIC_TOK = {"leather", "plate", "light", "heavy", "old", "rag", "rags", "simple", "iron", "steel", "black", "red", "white", "green", "blue",
               "dark", "long", "short", "small", "large", "big", "the", "a", "armor", "armour", "advanced", "basic", "cheap", "fine", "great"}
SMALL_RX = {
    "gloves": r"glove|gauntlet|mitt|vambrace|bracer|wrist|arm ?guard|hand ?guard|handwrap|knuckle",
    "neck": r"scarf|bandan|neckerchief|neck|cowl|collar|mantle|shawl|keffiyeh|shemagh|gorget|choker|necklace|amulet|stole|ruff",
    "eyes": r"goggle|glasses|eye ?patch|blindfold|monocle|visor|shades|eyewear",
}
CULT_FAMILY = {  # крупные семьи для матрицы
    "desert": ["Shek", "Scorchlander", "Dust Bandits", "Nomad", "Desert", "Hashish", "Sand", "Ashland", "Flotsam"],
    "holy": ["Holy Nation", "Paladin", "Preacher", "Church", "Reavers"],
    "city": ["United Cities", "Traders", "Tech Hunters", "Mercenar", "Anti-Slavers", "Slave Traders", "Black Dragon", "Machinist", "Guild"],
    "ninja": ["Ninja", "Samurai", "Shinobi", "Shogun", "Ronin"],
    "wild": ["Fogmen", "Cannibal", "Band of Bones", "Swamp", "Bandit", "Scaveng", "Hive", "Vagrants", "Drifters", "Skin"],
}


def family(origin):
    if not origin.startswith("culture:"):
        return origin
    c = origin[8:]
    for fam, keys in CULT_FAMILY.items():
        if any(k.lower() in c.lower() for k in keys):
            return fam + ":" + c
    return "other:" + c


def modname(sid):
    return sid.split("-", 1)[1] if "-" in sid else sid


def main():
    ctx = kmm_build.Ctx()
    M = ctx.M
    cat = {x["sid"]: x for x in json.load(open(ROOT + r"\data\catalog.json", encoding="utf-8"))["items"]}
    for p in sorted(os.listdir(ROOT + r"\build")):   # после KMM (только чтение .mod)
        f = ROOT + "\\build\\" + p + "\\" + p + ".mod"
        if p.startswith("KMM_") and os.path.exists(f):
            try:
                kmod.apply(M, kmod.read(f))
            except Exception as e:
                print("apply fail", p, e)
    # --- использование: надето (CHARACTER.clothing) / продаётся (VENDOR_LIST.clothing)
    worn, sold = C.Counter(), C.Counter()
    char_items = {}
    for c in M.values():
        if c.type_name == "CHARACTER":
            ss = [r.target for r in c.refs.get("clothing", [])]
            char_items[c.sid] = ss
            for t in set(ss):
                worn[t] += 1
        elif c.type_name == "VENDOR_LIST":
            for t in {r.target for r in c.refs.get("clothing", [])}:
                sold[t] += 1
    # --- предметы
    items = {}
    for sid, it in M.items():
        if it.type_name not in ("ARMOUR", "CONTAINER"):
            continue
        sl = SLOT.get(it.values.get("slot"))
        if not sl:
            continue
        if it.type_name == "CONTAINER" and sl != "backpack":
            continue
        cx = cat.get(sid)
        if not cx and not sid.endswith("KMM_Wardrobe.mod"):
            continue
        if cx is None:   # клон: берём данные исходника по имени
            src = next((v for v in cat.values() if v["name"] == it.name), None)
            cx = src or {"origin": "generic", "tier": "T1", "styles": []}
        items[sid] = dict(sid=sid, name=it.name, slot=sl, group=cx.get("group"), tier=cx.get("tier", "T1"), origin=cx.get("origin", "generic"),
                          mod=modname(sid), styles=cx.get("styles", []), worn_cat=sum((cx.get("worn_by") or {}).values()),
                          worn=worn[sid], sold=sold[sid], clone=sid.endswith("KMM_Wardrobe.mod"),
                          mesh=bool(str(it.values.get("mesh", "")).strip()), skel=None)
    # --- 1. матрица
    matrix = {}
    for i in items.values():
        k = i["slot"] + "|" + family(i["origin"])
        c = matrix.setdefault(k, {t: dict(n=0, used=0) for t in TIERS})
        t = c[i["tier"]]
        t["n"] += 1
        if i["worn"] or i["sold"]:
            t["used"] += 1
    by_slot_origin = C.defaultdict(lambda: C.Counter())
    for i in items.values():
        by_slot_origin[i["slot"]][i["origin"].split(":")[0]] += 1
    slot_tot = {s: dict(n=sum(1 for i in items.values() if i["slot"] == s),
                        used=sum(1 for i in items.values() if i["slot"] == s and (i["worn"] or i["sold"])),
                        tiers=dict(C.Counter(i["tier"] for i in items.values() if i["slot"] == s))) for s in MAIN}
    # культуры: тонкие клетки — культура, у которой в слоте < 2 используемых вещей, хотя в других слотах >= 6
    cults = C.Counter(i["origin"] for i in items.values() if i["origin"].startswith("culture:"))
    thin = []
    for cu, n in cults.items():
        if n < 8:
            continue
        for s in ["hat", "body", "legs", "boots", "belt", "shirt", "neck", "eyes", "gloves", "backpack"]:
            its = [i for i in items.values() if i["origin"] == cu and i["slot"] == s]
            used = [i for i in its if i["worn"] or i["sold"]]
            if len(used) < 2:
                thin.append(dict(culture=cu, slot=s, items=len(its), used=len(used), culture_total=n))
    # --- 2. сеты
    sets = {}
    for i in items.values():
        nm = i["name"]
        pre = nm.split(" - ")[0].strip() if " - " in nm else nm.split()[0]
        if pre.lower() in GENERIC_TOK or len(pre) < 3:
            continue
        sets.setdefault((pre, i["mod"]), []).append(i)
    set_rep = []
    for (pre, mod), L in sets.items():
        slots = {i["slot"] for i in L}
        main = slots & {"hat", "body", "legs", "boots", "belt", "shirt"}
        if len(main) < 3 or len(L) < 4:
            continue
        sids = {i["sid"] for i in L}
        wearers = [c for c, ss in char_items.items() if sids & set(ss)]
        coherent = 0
        for c in wearers:
            have = {items[t]["slot"] for t in char_items[c] if t in sids}
            if len(have) >= 2:
                coherent += 1
        set_rep.append(dict(prefix=pre, mod=mod, pieces=len(L), slots=sorted(slots), missing=sorted({"hat", "body", "legs", "boots"} - slots),
                            wearers=len(wearers), coherent=coherent, tiers=dict(C.Counter(i["tier"] for i in L)),
                            origin=C.Counter(i["origin"] for i in L).most_common(1)[0][0], sold=sum(1 for i in L if i["sold"]),
                            names=[i["name"] for i in L][:10]))
    set_rep.sort(key=lambda r: -r["pieces"])
    # --- 3. кандидаты в мелкие слоты: ВСЕ ARMOUR (каталог) по имени
    cand = {k: [] for k in SMALL_RX}
    existing_clone_src = {i["name"] for i in items.values() if i["clone"]}
    for sid, it in M.items():
        if it.type_name != "ARMOUR":
            continue
        cx = cat.get(sid)
        if not cx or SLOT.get(it.values.get("slot")) in (None, "backpack"):
            continue
        for k, rx in SMALL_RX.items():
            if re.search(rx, cx["name"], re.I) and SLOT.get(it.values.get("slot")) != k:
                cand[k].append(dict(sid=sid, name=cx["name"], slot=SLOT.get(it.values.get("slot")), tier=cx["tier"], origin=cx["origin"],
                                    worn=worn[sid], sold=sold[sid], mod=modname(sid), has_mesh=bool(str(it.values.get("mesh", "")).strip()),
                                    cloned=cx["name"] in existing_clone_src))
    # --- сводка по нужным дырам: культуры без neck/eyes среди носящих
    out = dict(items_total=len(items), slot_totals=slot_tot, origin_by_slot={k: dict(v) for k, v in by_slot_origin.items()},
               matrix=matrix, thin_cells=thin, sets=set_rep, small_candidates={k: v for k, v in cand.items()},
               small_existing={s: [dict(name=i["name"], tier=i["tier"], origin=i["origin"], worn=i["worn"], sold=i["sold"]) for i in items.values() if i["slot"] == s]
                               for s in ("eyes", "neck", "gloves")})
    json.dump(out, open(ROOT + r"\data\slots_audit.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("items", len(items), "sets", len(set_rep), "thin", len(thin), {k: len(v) for k, v in cand.items()})


if __name__ == "__main__":
    main()
