"""Поток TECH: путь к реликтам через технологии (LATE_GAME.md §9, DESIGN.md «Доля божественного»).
Дерево исследований «Relics» поверх Crafting Redux: исследование реликтов → комплект экспедиции (T0–T1) →
кузнечная броня (T2) и оружие/стрелковое (T0–T2) → реконструкция когитатора (новый компонент Relic AI Core) →
реликты T3. Воспроизводится только имперская (человеческая) техника из каталога гардероба (data/catalog.json).
Только НОВЫЕ записи (RESEARCH, BUILDING, BUILDING_FUNCTIONALITY, ITEM); существующие записи не меняются.
Опоры дерева — исследования Crafting Redux, если они в ctx (lo.py EXTRA), иначе ванильные (rules anchors)."""
import json

from kmod import F32, Ref


def build(ctx, s, rules):
    r_items = rules["items_ref"]
    for k, sid in r_items.items():
        if sid not in ctx.M:
            raise KeyError(f"TECH: предмет {k} {sid} не найден")

    # --- опоры дерева: первая существующая запись из списка ---------------------------------------------
    anchors = {}
    for key, cands in rules["anchors"].items():
        if key.startswith("_"):
            continue
        for t, name, sid in cands:
            it = ctx.M.get(sid)
            if it is not None and it.type_name == t and ctx.in_game(sid):
                anchors[key] = sid
                s.report["anchor_" + key + ("_cr" if "2PN8" in sid else "_vanilla")] += 1
                break
        else:
            raise KeyError(f"TECH: опора {key} не найдена ни в одном варианте")

    # --- реликтовые вещи из каталога: происхождение × тир × тип ----------------------------------------------
    vanilla_races = {it.sid for _, m, _ in ctx.van for it in m.items if it.type_name == "RACE"}
    pool = {}  # (type, tier) -> [sid]
    for x in json.load(open(rules["catalog"], encoding="utf-8"))["items"]:
        if x["origin"] not in rules["origins"] or x.get("group") in rules["exclude_groups"]:
            continue
        it = ctx.M.get(x["sid"])
        if it is None or it.type_name != x["type"] or not ctx.in_game(it.sid):
            s.report["relic_skipped_missing"] += 1
            continue
        races = [r.target for r in it.refs.get("races", [])]
        if races and not any(r in vanilla_races for r in races):
            s.report["relic_skipped_race"] += 1   # носить может только не-игровая раса — производство бессмысленно
            continue
        pool.setdefault((x["type"], x["tier"]), []).append(it.sid)
    for k in pool:
        pool[k].sort()

    def tier_sids(tname, tiers):
        return [sid for t in tiers for sid in pool.get((tname, t), [])]

    # --- компонент вершины: Relic AI Core ------------------------------------------------------------------
    rc = rules["relic_core"]
    core = s.new("ITEM", rc["name"], template=rc["template"], values={
        "value": rc["value"], "weight kg": F32(rc["weight kg"]), "production time": rc["production time"],
        "description": rc["description"]})
    core.refs["ingredients"] = [Ref(r_items[k], n, 0, 0) for k, n in rc["ingredients"]]
    own = dict(r_items, relic_core=core.sid)
    s.report["items_new"] += 1

    # --- курируемый набор реликтов (редкие материалы, рецепты на предметах) --------------------------------
    rcf = rules.get("relic_craft") or {}
    cur = {"ARMOUR": [], "CROSSBOW": [], "WEAPON": []}
    for tname, sid, rkey in rcf.get("items", []):
        it = ctx.M.get(sid)
        if it is None or it.type_name != tname or not ctx.in_game(sid):
            raise KeyError(f"TECH: курируемый предмет {sid} ({tname}) не найден")
        rec = rcf["recipes"][rkey]
        s.add_refs(sid, "ingredients", [Ref(own[k], n * 100, 0, 0) for k, n in rec["ing"]])
        if it.values.get("production time") in (None, 0):
            s.change(sid, values={"production time": rec["time"]})
        cur[tname].append(sid)
        s.report["relic_craft_" + tname.lower()] += 1

    # --- станки -------------------------------------------------------------------------------------------
    ftmpl = rules["functionality_templates"]
    bld = {}
    for key, b in rules["buildings"].items():
        tmpl = ctx.find(*b["template"])
        f = s.new("BUILDING_FUNCTIONALITY", b["name"] + " Function", template=ftmpl[b["functionality"]])
        for cat in ("armour crafts", "crossbow crafts", "weapon crafts", "item crafts", "robotics crafts", "backpack crafts", "produces"):
            f.refs.pop(cat, None)
        cr = b["crafts"]
        if cr.get("curated"):
            f.refs[{"ARMOUR": "armour crafts", "CROSSBOW": "crossbow crafts"}[cr["curated"]]] = [Ref(x) for x in cur[cr["curated"]]]
        elif b["functionality"] == "armour":
            f.refs["armour crafts"] = [Ref(x) for x in tier_sids("ARMOUR", cr["tiers"])]
        elif b["functionality"] == "crossbow":
            f.refs["crossbow crafts"] = [Ref(x) for x in tier_sids("CROSSBOW", cr["tiers"])]
        else:
            f.refs["item crafts"] = [Ref(own[k], 2, 0, 0) for k in cr["items"]]
        q = s.new("BUILDING", b["name"], template=tmpl.sid, values={"Description": b["description"], "building category": "CRAFTING - Relics"})
        q.refs.pop("upgrades to", None)
        q.refs["functionality"] = [Ref(f.sid)]
        q.refs["construction"] = [Ref(own[k], n, 0, 0) for k, n in b["construction"]]
        bld[key] = q.sid
        s.report["buildings_new"] += 1
        s.report["crafts_" + key] = sum(len(f.refs.get(c, [])) for c in ("armour crafts", "crossbow crafts", "item crafts"))

    # --- дерево исследований ------------------------------------------------------------------------------
    res = {}
    for node in rules["research"]:
        rq = []
        for x in node["requires"]:
            sid = anchors[x[1:]] if x.startswith("@") else res[x]
            if sid not in [r.target for r in rq]:
                rq.append(Ref(sid, 0, 0, 0))
        it = s.new("RESEARCH", node["name"], values={
            "level": node["level"], "time": node["time"], "money": node["money"], "category": rules["category"],
            "description": node["description"], "blueprint only": False, "is level upgrade": False,
            "repeats": 0, "repeat mult": F32(1.0), "production mult": F32(1.0)})
        it.refs["requirements"] = rq
        it.refs["cost"] = [Ref(own[k], n, 0, 0) for k, n in node["cost"]]
        en = node.get("enable", {})
        if en.get("armour_tiers"):
            it.refs["enable armour"] = [Ref(x) for x in tier_sids("ARMOUR", en["armour_tiers"])]
        if en.get("weapon_tiers"):
            it.refs["enable weapon type"] = [Ref(x) for x in tier_sids("WEAPON", en["weapon_tiers"])]
        if en.get("crossbow_tiers"):
            it.refs["enable crossbow"] = [Ref(x) for x in tier_sids("CROSSBOW", en["crossbow_tiers"])]
        if en.get("curated"):
            it.refs["enable armour"] = [Ref(x) for x in cur["ARMOUR"]]
            it.refs["enable weapon type"] = [Ref(x) for x in cur["WEAPON"]]
            it.refs["enable crossbow"] = [Ref(x) for x in cur["CROSSBOW"]]
        if en.get("buildings"):
            it.refs["enable buildings"] = [Ref(bld[k]) for k in en["buildings"]]
        if en.get("items"):
            it.refs["enable item"] = [Ref(own[k]) for k in en["items"]]
        it.refs = {k: v for k, v in it.refs.items() if v}
        res[node["key"]] = it.sid
        s.report["research_new"] += 1
        for c in ("enable armour", "enable weapon type", "enable crossbow"):
            s.report["unlocks_" + c.split()[-1]] += len(it.refs.get(c, []))
