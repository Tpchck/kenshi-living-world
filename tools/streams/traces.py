"""Поток TRACES (шаг 1 офлайн-билда): шаблоны отрядов для видимых следов событий дирижёра рядом с игроком.

Только НОВЫЕ записи (существующие не меняются → пересечений по полям нет):
- отряды фракции по тирам снаряжения T0..T3 (клон основного бойца, одежда из пула тира data/wardrobe_tiers.json);
  KMM_Traces.lua спавнит их пачкой в тире текущего богатства фракции (обеднение/обогащение видно сразу, а не заменой вещей);
- беженцы фракции (бойцы T0 без оружия, ИИ бродяг Drifter squad) — из павшего, голодного или захваченного города;
- «разорённый караван» (клон торгового отряда без лавки) — Lua убивает его сразу после спавна: тела и вьючные на дороге.
Экзотика (WH/реликт) — только у своих WH-фракций (бюджет 2 %). Карта шаблонов для Lua → build/KMM_Conductor/traces.json."""
import collections
import json
import os
import random
import re
import zlib

from kmod import Ref

ROOT = r"C:\KenshiModMap"
TIERS = ["T0", "T1", "T2", "T3"]


def build(ctx, s, rules):
    M = ctx.M
    cond = json.load(open(os.path.join(ROOT, "rules", "conductor.json"), encoding="utf-8"))
    tiers_data = json.load(open(os.path.join(ROOT, "data", "wardrobe_tiers.json"), encoding="utf-8"))["factions"]
    wr = json.load(open(os.path.join(ROOT, "rules", "streams", "wardrobe.json"), encoding="utf-8"))
    cat = {x["sid"]: x for x in json.load(open(os.path.join(ROOT, wr["catalog"]) if not os.path.isabs(wr["catalog"]) else wr["catalog"], encoding="utf-8"))["items"]}
    wh_names = {n for v in wr["wh_origin_factions"].values() for n in v}
    base_tier = {r["faction"][1]: (r["base"], r["leader"]) for r in wr["factions"]}
    SVG = wr["context"]["lore_hard"].get("savage") or {}
    def sav_ban(sid):   # дикие без шлемов и металла (как в гардеробе, rules wardrobe.json savage.ban_rx)
        nm = (M[sid].name if sid in M else "") or ""
        return bool(SVG.get("ban_rx")) and bool(re.search(SVG["ban_rx"], nm, re.I)) and not re.search(SVG.get("ban_keep_rx", "^$"), nm, re.I)

    def exotic(sid):
        x = cat.get(sid)
        return bool(x) and (x["origin"] in ("imperial", "chaos", "xenos") or (x["tier"] == "T3" and not x["origin"].startswith("culture:")))

    fac_of = lambda it: it.refs["faction"][0].target if it.refs.get("faction") and it.refs["faction"][0].target in M else None  # noqa: E731
    squads = collections.defaultdict(list)
    for sq in ctx.all("SQUAD_TEMPLATE"):
        f = fac_of(sq)
        if f:
            squads[f].append(sq)
    drifter = ctx.find(*rules["refugee_ai_from"])
    out = {"factions": {}, "caravans": {}, "dead_caravan_sids": [], "live_caravans": {}}
    rng_for = lambda key: random.Random(rules["seed"] + zlib.crc32(key.encode()))  # noqa: E731

    for fid, fd in sorted(cond["factions"].items()):
        if fd.get("player") or fid not in M:
            continue
        mil = [q for q in squads.get(fid, []) if not q.values.get("is trader") and q.refs.get("squad") and ctx.in_game(q.sid)]
        if not mil:
            s.report["no_military_squad"] += 1
            continue
        members = collections.Counter()
        for q in mil:
            for cat_name in ("squad", "squad2"):
                for r in q.refs.get(cat_name, []):
                    t = M.get(r.target)
                    if t is not None and t.type_name == "CHARACTER" and ctx.in_game(t.sid) and not t.values.get("unique"):
                        members[t.sid] += max(1, r.v1 or r.v0 or 1)
        if not members:
            s.report["no_soldier"] += 1
            continue
        soldier = M[sorted(members.items(), key=lambda x: (-x[1], x[0]))[0][0]]
        main_sq = sorted(mil, key=lambda q: (-sum(r.v1 or r.v0 or 1 for r in q.refs.get("squad", [])), q.sid))[0]
        pools = tiers_data.get(fd["name"], {})
        allow_exotic = fd["name"] in wh_names
        rng = rng_for(fid)
        entry = {"name": fd["name"], "tiers": {}, "base_tier": base_tier.get(fd["name"], ("T0", "T1"))[0]}
        for t in TIERS:
            slots = pools.get(t) or {}
            clothing = []
            loot_n = 0 if t in ("T2", "T3") else 1   # дикие: шлем/металл — только мародёрка старших тиров (рост фракции), не больше одной вещи
            for g, lst in sorted(slots.items()):
                lst = [x for x in lst if x in M and ctx.in_game(x) and (allow_exotic or not exotic(x))]
                if fd["name"] in SVG.get("factions", []):
                    ok_ = [x for x in lst if not sav_ban(x)]
                    if loot_n < 1 and len(ok_) < len(lst) and rng.random() < 0.5:
                        lst = [x for x in lst if sav_ban(x)][:1] or ok_; loot_n += 1 if lst and sav_ban(lst[0]) else 0
                    else:
                        lst = ok_
                if lst:
                    for x in rng.sample(lst, min(2, len(lst))):
                        clothing.append(Ref(x, 1, 50, 0))
            if len(clothing) < 4:   # пул тира пуст — тир не делаем (Lua возьмёт ближайший)
                continue
            ch = s.new("CHARACTER", soldier.name, template=soldier.sid)   # имя видно игроку: без служебных меток (тир — в sid/отчёте)
            ch.refs["clothing"] = clothing
            q = s.new("SQUAD_TEMPLATE", f"KMM {fd['name']} {t} band", template=main_sq.sid)
            for k in ("leader", "squad", "squad2", "squad3", "vendors", "special"):
                q.refs.pop(k, None)
            q.refs["leader"] = [Ref(ch.sid, 1, 0, 0)]
            q.refs["squad"] = [Ref(ch.sid, rules["tier_squad"][0], rules["tier_squad"][1], 0)]
            entry["tiers"][t] = q.sid
            s.report["tier_squads"] += 1
        if not entry["tiers"]:   # пулы одежды пусты: берём реальные военные отряды фракции (без клонов), квантили по размеру -> T0..T3
            ranked = sorted(mil, key=lambda q: (sum(r.v1 or r.v0 or 1 for r in q.refs.get("squad", [])), q.sid))
            if len(ranked) == 1:
                entry["tiers"][entry["base_tier"]] = ranked[0].sid
            else:
                for i, t in enumerate(TIERS):
                    entry["tiers"][t] = ranked[round(i * (len(ranked) - 1) / (len(TIERS) - 1))].sid
            s.report["tier_real_squads"] += len(entry["tiers"])
            s.report["tier_fallback_factions"] += 1
        # беженцы: бойцы T0 без оружия, ИИ бродяг
        t0 = pools.get("T0") or {}
        cl = []
        for g, lst in sorted(t0.items()):
            lst = [x for x in lst if x in M and ctx.in_game(x) and not exotic(x)]
            if lst:
                cl.append(Ref(rng.choice(lst), 1, 70, 0))
        rch = s.new("CHARACTER", soldier.name, template=soldier.sid)
        rch.refs["weapons"] = []
        rch.refs.pop("crossbows", None)
        if cl:
            rch.refs["clothing"] = cl
        rq = s.new("SQUAD_TEMPLATE", f"KMM {fd['name']} refugees", template=drifter.sid)
        rq.refs = {k: v for k, v in rq.refs.items() if k in ("AI packages",)}
        rq.refs["faction"] = [Ref(fid)]
        rq.refs["leader"] = [Ref(rch.sid, 1, 0, 0)]
        rq.refs["squad"] = [Ref(rch.sid, rules["refugees"][0], rules["refugees"][1], 0)]
        entry["refugees"] = rq.sid
        s.report["refugee_squads"] += 1
        # ветераны-калеки (ваниль: CHARACTER.«starting health» = LOCATIONAL_DAMAGE, val0 в процентах -100..100, < -100 = ампутация)
        vcfg = rules.get("veteran")
        if vcfg:
            vrng = rng_for(fid + "|vet")
            vcl = []
            for tn in ("T1", "T0"):
                for g, lst in sorted((pools.get(tn) or {}).items()):
                    lst = [x for x in lst if x in M and ctx.in_game(x) and (allow_exotic or not exotic(x)) and not (fd["name"] in SVG.get("factions", []) and sav_ban(x))]
                    if lst:
                        vcl.append(Ref(vrng.choice(lst), 1, 50, 0))
                if len(vcl) >= 4:
                    break
            vch = []
            for label, limbs in vcfg["variants"]:
                c = s.new("CHARACTER", soldier.name, template=soldier.sid)
                if vcl:
                    c.refs["clothing"] = list(vcl)
                sh = [r for r in c.refs.get("starting health", []) if r.target not in {vcfg["limbs"][k] for k, _ in limbs}]
                for k, val in limbs:
                    sh.append(Ref(vcfg["limbs"][k], val, 100, 0))
                c.refs["starting health"] = sh
                vch.append(c)
            vq = s.new("SQUAD_TEMPLATE", f"KMM {fd['name']} Veterans", template=main_sq.sid)
            for k in ("leader", "squad", "squad2", "squad3", "vendors", "special"):
                vq.refs.pop(k, None)
            vq.refs["leader"] = [Ref(vch[0].sid, 1, 0, 0)]
            vq.refs["squad"] = [Ref(c.sid, 1, 1, 0) for c in vch]
            entry["veteran"] = vq.sid
            s.report["veteran_squads"] += 1
        if entry["tiers"] or entry.get("refugees"):
            out["factions"][fid] = entry
        # разорённый караван: торговый отряд фракции без лавки
        tr = sorted([q for q in squads.get(fid, []) if q.values.get("is trader") and q.refs.get("squad") and ctx.in_game(q.sid)], key=lambda q: q.sid)
        if tr:   # живой торговый отряд фракции (существующий шаблон, не клон) — торговый путь на дороге (KMM_Traces: trade_for)
            out["live_caravans"][fid] = tr[0].sid
        if tr and len(out["caravans"]) < rules["max_caravans"]:
            dq = s.new("SQUAD_TEMPLATE", f"KMM {fd['name']} ruined caravan", template=tr[0].sid, values={"is trader": False})
            dq.refs.pop("vendors", None)
            out["caravans"][fid] = dq.sid
            out["dead_caravan_sids"].append(dq.sid)
            s.report["caravans"] += 1
    s.report["factions"] = len(out["factions"])
    # демоны Хаоса (Chaos Demons): только прорывы в кризисных державах (KMM_Traces, событие chaos_incursion)
    dm = [q for q in ctx.all("SQUAD_TEMPLATE") if ctx.origin.get(q.sid) == rules.get("daemon_mod", "ChaosDaemonsStandalone.mod")]
    if dm:
        dfac = next((fac_of(q) for q in dm if fac_of(q)), None)
        out["daemons"] = {"faction": dfac, "squads": sorted(q.sid for q in dm if fac_of(q) == dfac)}
        s.report["daemon_squads"] = len(out["daemons"]["squads"])
    out["item_tiers"] = {sid: TIERS.index(x["tier"]) for sid, x in cat.items() if x.get("tier") in TIERS}   # для KMM_Self: тир снаряжения противника
    dst = os.path.join(ROOT, "build", "KMM_Conductor", "traces.json")
    json.dump(out, open(dst, "w", encoding="utf-8"), ensure_ascii=False)
