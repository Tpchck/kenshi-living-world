"""Поток FIX (интегратор): точечные исправления совместимости (rules/streams/fix.json)."""
import collections
import json
import os

from kmod import Ref, F32
from _shared import rival_tier


def build(ctx, s, rules):
    race_link(ctx, s, rules)
    faction_merge(ctx, s, rules)
    junk_unlink(ctx, s, rules)
    homeless_faction(ctx, s, rules)
    xp_curve(ctx, s, rules)
    rivals(ctx, s, rules)
    for spec in rules["race_own_animations"]["items"]:
        race = ctx.find(*spec["race"])
        af = ctx.find(*spec["animation_file"])
        if spec.get("attach_own", True) and not any(x.target == af.sid for x in race.refs.get("animation files", [])):
            s.add_refs(race.sid, "animation files", [Ref(af.sid, 0, 0, 0)])
            s.report["race_animation_files"] += 1
        if spec.get("inherit_from"):   # краш 2026-11-13 (разговор с шаманом орков): у расы был только свой файл -> idle «-25» не найден
            donor = ctx.find(*spec["inherit_from"])
            have = {x.target for x in race.refs.get("animation files", [])} | {af.sid}
            add = [Ref(r.target, r.v0, r.v1, r.v2) for r in donor.refs.get("animation files", []) if r.target not in have]
            if add:
                s.add_refs(race.sid, "animation files", add)
                s.report["race_animation_files_inherited"] += len(add)

    # --- атмосфера: чуть мрачнее, пустынный гримдарк (по итогам плейтеста 2026-11-13: +2..13 %, без ReShade, пыль не убираем) ---
    AT = rules.get("atmosphere") or {}
    if AT.get("enabled"):
        def grade(c, g):
            r, gg, b = (c >> 16) & 255, (c >> 8) & 255, c & 255
            l = 0.299 * r + 0.587 * gg + 0.114 * b
            out = []
            for ch, t in zip((r, gg, b), g.get("tint", [1, 1, 1])):
                v = ch + (l - ch) * g.get("desat", 0)          # обесцвечивание к яркости
                v = v * (1 - g.get("tint_mix", 0) + g.get("tint_mix", 0) * t)   # лёгкий охристый сдвиг
                out.append(max(0, min(255, int(round(v * g.get("bright", 1))))))
            return (out[0] << 16) | (out[1] << 8) | out[2]
        for se in ctx.all("SEASON"):
            c = se.values.get("sunlight color")
            if isinstance(c, int):
                nc = grade(c, AT["sunlight"])
                if nc != c:
                    s.change(se.sid, values={"sunlight color": nc}); s.report["atmos_seasons"] += 1
        for w in ctx.all("WEATHER"):
            v = {}
            for k, g in (("sky color mult", AT["sky"]), ("fog color", AT["fog"])):
                c = w.values.get(k)
                if isinstance(c, int) and grade(c, g) != c:
                    v[k] = grade(c, g)
            for k, mul, cap in (("fog distance min", AT["fog_distance_mult"], None), ("fog distance max", AT["fog_distance_mult"], None),
                                ("clouds density", AT["clouds_mult"], 1.0), ("dust", AT["dust_mult"], 1.0)):
                x = w.values.get(k)
                if x is not None and float(x) > 0:
                    nx = float(x) * mul
                    v[k] = F32(min(cap, nx) if cap else nx)
            if v:
                s.change(w.sid, values=v); s.report["atmos_weathers"] += 1

    # --- расы с человеческим мешем без файлов анимаций (audit_classes C, род краша у шамана орков) ---
    RA = rules.get("race_anim_auto") or {}
    if RA.get("enabled"):
        donor = ctx.find(*RA["donor"])
        dafs = donor.refs.get("animation files", [])
        used = {r.target for c in ctx.all("CHARACTER") for r in c.refs.get("race", [])}
        for rc in ctx.all("RACE"):
            if rc.sid not in used or rc.sid == donor.sid or rc.refs.get("animation files"):
                continue
            if RA["mesh_rx"] not in str(rc.values.get("male mesh", "")).lower():
                continue
            s.add_refs(rc.sid, "animation files", [Ref(r.target, r.v0, r.v1, r.v2) for r in dafs])
            s.report["race_anim_auto"] += 1

    # --- тестовый старт владельца (rules/streams/fix.json test_start) ---
    def get(spec):
        tname, name, sid = spec
        if sid and sid in ctx.M:
            return ctx.M[sid]
        return ctx.find(tname, name, sid if sid and not name else None)

    def make_start(T):   # один персонаж, свой отряд, город или точка force_pos; возвращает sid NEW_GAME_STARTOFF
        st_t = get(T["stats_template"])
        stats = s.new("STATS", T["char_name"] + " stats", values={k: F32(T["stat_value"]) for k, v in st_t.values.items() if isinstance(v, float)})
        tpl = get(T["char_template"])
        refs = {"stats": [Ref(stats.sid, 0, 0, 0)], "clothing": [Ref(get(x).sid, 1, 100, 0) for x in T.get("clothing", [])]}
        refs["weapons"] = [Ref(get(x).sid, 1, 0, 0) for x in T.get("weapons", [])]
        if T.get("weapon_level"):
            refs["weapon level"] = [Ref(get(T["weapon_level"]).sid, 0, 0, 0)]
        if T.get("backpack"):
            refs["backpack"] = [Ref(get(T["backpack"]).sid, 1, 100, 0)]
        vals = dict(tpl.values)
        vals.update({"armour grade": int(T.get("armour_grade", 0)), "armour upgrade chance": 0, "stats randomise": 0, "unique": False, "named": True})
        ch = s.new("CHARACTER", T["char_name"], values=vals, refs=refs)
        sq_t = ctx.M["46039-rebirth.mod"]   # отряд старта Rock Bottom — значения отряда игрока
        sq = s.new("SQUAD_TEMPLATE", "start- " + T["char_name"], values=dict(sq_t.values, **{"malnourished": bool(T.get("malnourished", False))}),
                   refs={"leader": [Ref(ch.sid, 1, 0, 0)]})
        so_t = next(i for i in ctx.M.values() if i.type_name == "NEW_GAME_STARTOFF" and i.name == "Rock Bottom")
        sv = dict(so_t.values, **{"force start pos": False, "money": int(T["money"]), "description": T["description"],
                                  "difficulty": T.get("difficulty", "Test"), "style": T.get("style", "Test"), "REMOVED": False})
        srefs = {"squad": [Ref(sq.sid, 0, 0, 0)]}
        if T.get("force_pos"):   # родной механизм Rock Bottom: точка в мире вместо города
            sv.update({"force start pos": True, "start pos X": int(T["force_pos"][0]), "start pos Z": int(T["force_pos"][1])})
        else:
            srefs["town"] = [Ref(get(T["town"]).sid, 0, 0, 0)]
        return s.new("NEW_GAME_STARTOFF", T["name"], values=sv, refs=srefs).sid

    # --- старты владельца (rules/streams/fix.json test_start, survival_start); прочие NEW_GAME_STARTOFF скрыты флагом REMOVED ---
    mine = [make_start(T) for T in (rules.get("test_start") or {}, rules.get("survival_start") or {}) if T.get("enabled")]
    if mine:
        for it in list(ctx.M.values()):
            if it.type_name == "NEW_GAME_STARTOFF" and it.sid not in mine and it.values.get("REMOVED") is not True:
                s.change(it.sid, values={"REMOVED": True})
                s.report["starts_hidden"] += 1
        s.report["own_starts"] = len(mine)

    # --- кристальные жуки: редкость и численность (rules crystal) ---
    import re, random
    C = rules.get("crystal") or {}
    if C:
        rx = re.compile(C["name_rx"], re.I)
        cfacs = {f.sid for f in ctx.all("FACTION") if f.name in C["squad_factions"]}
        for sq in ctx.all("SQUAD_TEMPLATE"):
            if not any(r.target in cfacs for r in sq.refs.get("faction", [])):
                continue
            new = {}
            for cat in ("squad", "squad2"):
                for r in sq.refs.get(cat, []):
                    lo, hi = max(1, round(r.v0 * C["squad_factor"])), max(1, round(r.v1 * C["squad_factor"]))
                    if (lo, hi) != (r.v0, r.v1):
                        new.setdefault(cat, []).append(Ref(r.target, lo, max(lo, hi), r.v2))
            if new:
                s.change(sq.sid, set_refs=new)
                s.report["crystal_squads_halved"] += 1

    # --- сокровища в логовах главарей с наградой (rules treasure) ---
    TR = rules.get("treasure") or {}
    if TR:
        ex = re.compile(TR["exclude_rx"], re.I)
        book = re.compile(TR["book_rx"], re.I)
        pool = []
        for it in ctx.all("ITEM"):
            v, fn, nm = it.values.get("value", 0), it.values.get("item function", 0), it.name or ""
            if not isinstance(v, int) or v <= 0 or it.values.get("REMOVED") or fn not in TR["functions"] or ex.search(nm):
                continue
            if fn == 13 and (not book.search(nm) or v > TR.get("book_vmax", 10**9)):
                continue   # книги: после подъёма цен economy (до 2500) не должны попадать в дорогие тиры
            pool.append((v, it.sid, nm))
        rng = random.Random(TR["seed"])
        lists = []
        for t in TR["tiers"]:
            cand = sorted({p for p in pool if t["vmin"] <= p[0] <= t["vmax"]})
            if not cand:
                continue
            pick = rng.sample(cand, min(t["size"], len(cand)))
            vals = {"items count": 40, "money item prob": F32(0.0), "money item min": 0, "money item max": 0}
            if t.get("money"):
                vals.update({"money item prob": F32(t["money"][0]), "money item min": t["money"][1], "money item max": t["money"][2]})
            vl = s.new("VENDOR_LIST", "KMM Treasure " + t["id"], values=vals, refs={"items": [Ref(p[1], 100, 0, 0) for p in pick]})
            lists.append((vl.sid, t["spawn"]))
            s.report["treasure_items:" + t["id"]] = len(pick)
        lrx = re.compile(TR["leader_rx"], re.I)
        def lair_leader(sq):
            for r in sq.refs.get("leader", []):
                ch = ctx.M.get(r.target)
                if ch is not None and ch.type_name == "CHARACTER" and ch.values.get("unique") and (ch.refs.get("bounty factions") or lrx.search(ch.name or "")):
                    return True
            return False
        lair_sids = set()
        for town in ctx.all("TOWN"):
            sqs = [ctx.M[r.target] for c in ("residents", "roaming squads", "bar squads") for r in town.refs.get(c, []) if r.target in ctx.M]
            if not any(sq.type_name in ("SQUAD_TEMPLATE", "UNIQUE_SQUAD_TEMPLATE") and lair_leader(sq) for sq in sqs):
                continue
            if town.refs.get("bar squads") or any(sq.values.get("is trader") for sq in sqs):
                s.report["treasure_skip_city"] += 1   # города с барами/торговцами: у бочек есть хозяева
                continue
            s.add_refs(town.sid, "loot spawn", [Ref(sid, sp[0], sp[1], 0) for sid, sp in lists])
            s.report["treasure_lairs"] += 1
            lair_sids.add(town.sid)
        ruins_fill(ctx, s, TR.get("ruins") or {}, lair_sids)
        # реликтовое оружие в опасных/древних точках (rules treasure.edge_lairs): по одной вещи на точку, шанс малый
        EL = TR.get("edge_lairs") or {}
        if EL:
            erng = random.Random(TR["seed"] + 7)
            for g in EL["groups"]:
                grx = re.compile(g["name_rx"], re.I)
                items = [i for i in g["items"] if i in ctx.M]
                s.report["edge_missing_items:" + g["id"]] = len(g["items"]) - len(items)
                erng.shuffle(items)
                k = 0
                for town in sorted(ctx.all("TOWN"), key=lambda x: x.sid):
                    if not items or not grx.search(town.name or "") or "override" in (town.name or "").lower():
                        continue
                    fres = (ctx.M[town.refs["faction"][0].target].refs.get("residents", []) if town.refs.get("faction") and town.refs["faction"][0].target in ctx.M and not town.values.get("residents override") else [])   # лавки фракции по умолчанию тоже (The Eternal Laboratory)
                    if town.refs.get("bar squads") or any(ctx.M[r.target].values.get("is trader") for c in ("residents", "roaming squads") for r in town.refs.get(c, []) if r.target in ctx.M) or any(r.target in ctx.M and ctx.M[r.target].values.get("is trader") for r in fres):
                        continue
                    it = items[k % len(items)]
                    k += 1
                    vl = s.new("VENDOR_LIST", "KMM Relic " + g["id"] + " " + town.sid[:24], values={"items count": 1, "money item prob": F32(0.0), "money item min": 0, "money item max": 0}, refs={{"WEAPON": "weapons", "CROSSBOW": "crossbows", "ARMOUR": "clothing", "CONTAINER": "containers"}.get(ctx.M[it].type_name, "items"): [Ref(it, EL["chance"], 0, 0)]})
                    s.add_refs(town.sid, "loot spawn", [Ref(vl.sid, EL["spawn"][0], EL["spawn"][1], 0)])
                    s.report["edge_lairs:" + g["id"]] += 1

    # ZONE_FIX (2026-11-13, наложение зданий в Heng): поздние моды «снимками» зон воскрешают удалённые/откатывают
    # перенесённые здания раннего мода (CATO <- Towns Expansion и др.) — KMM_Fix грузится последним и повторяет
    # намеренное состояние (tools/build/zone_fix.py). Выключатель: fix.json zone_fix.enabled.
    # ICON_FIX (2026-11-16): huge mod icons (1600-2500 px) render blank -> downscaled copies in KMM_Fix (tools/build/icon_fix.py)
    if rules.get("icon_fix", {}).get("enabled", True):
        import sys as _sys2
        if r"C:\KenshiModMap\tools\build" not in _sys2.path:
            _sys2.path.insert(0, r"C:\KenshiModMap\tools\build")
        import icon_fix
        IF = rules.get("icon_fix", {})
        pairs = [(it.sid, it.values.get("icon")) for it in ctx.M.values()
                 if it.type_name == "ITEM" or isinstance(it.values.get("icon"), str)]
        pairs = [(sid, ic) for sid, ic in pairs if isinstance(ic, str) and ic and ctx.in_game(sid)]
        newv, ist = icon_fix.run(pairs, r"C:\KenshiModMap\build\KMM_Fix\icons", IF.get("limit", 1024), IF.get("target", 512))
        for sid, v in newv.items():
            s.change(sid, values={"icon": v})
        # icon file exists nowhere: empty icon -> the game renders it from the item's 3D model (as for vanilla items)
        for sid in ist.pop("lost_sids", []):
            vv = ctx.M[sid].values
            if any(isinstance(vv.get(k), str) and vv.get(k).strip() for k in ("ground mesh", "mesh")):
                s.change(sid, values={"icon": ""})
                s.report["icon_fix_auto"] += 1
        for k, v in ist.items():
            s.report["icon_fix_" + k] = v
        if ist["failed"]:
            raise RuntimeError("icon_fix: failed to write %d icons" % ist["failed"])
    if rules.get("zone_fix", {}).get("enabled", True):
        import os as _os
        import sys as _sys
        _d = r"C:\KenshiModMap\tools\build"
        if _d not in _sys.path:
            _sys.path.insert(0, _d)
        import zone_fix
        zr = zone_fix.write(_os.path.join(r"C:\KenshiModMap", "build", "KMM_Fix", "leveldata"))
        if zr.get("bad"):
            raise RuntimeError("zone_fix: нечитаемые zone-файлы: " + "; ".join(zr["bad"][:5]))
        s.report["zone_fix_zones"] = zr["zones"]
        s.report["zone_fix_deletions"] = zr["deletions"]
        s.report["zone_fix_restored_edits"] = zr["restored_edits"]


def ruins_fill(ctx, s, RU, lair_sids):
    """RUINS (L1 2026-11-15, rules fix.json treasure.ruins): руины/лагеря/заброшенные TOWN получают ванильный
    'loot spawn' из списков «KMM Ruin <тип>» + стройматериалы; уже залутанные — скромную добавку. См. docs/core/world.md «Руины»."""
    import math
    import re
    if not RU.get("enabled", True) or not RU.get("kinds"):
        return
    M = ctx.M

    def pick(tname, name):   # ванильная запись предпочтительнее одноимённой модовой
        hits = [i for i in ctx.idx.get((tname, name), []) if ctx.in_game(i.sid) and not i.values.get("REMOVED")]
        hits.sort(key=lambda i: (ctx.origin.get(i.sid) != "gamedata.base", i.sid))
        return hits[0] if hits else None

    lists = {}
    for lid, spec in RU["lists"].items():
        refs = []
        for name, w in spec["items"]:
            it = pick("ITEM", name)
            v = it.values.get("value", 0) if it is not None else 0
            if it is None or not isinstance(v, int) or v <= 0:
                s.report["ruin_missing_item:" + name] = 1
                continue
            if v > RU["item_vmax"]:
                s.report["ruin_too_pricey:" + name] = v
                continue
            refs.append(Ref(it.sid, int(w), 0, 0))
        if not refs:
            continue
        m = spec.get("money") or [0, 0, 0]
        vl = s.new("VENDOR_LIST", "KMM Ruin " + lid, values={"items count": 40, "money item prob": F32(m[0]), "money item min": int(m[1]),
                   "money item max": int(m[2])}, refs={"items": refs})
        lists[lid] = vl.sid
        s.report["ruin_list_items:" + lid] = len(refs)
    kinds = [(k, re.compile(k["rx"], re.I) if k.get("rx") else None) for k in RU["kinds"]]
    fallback = next(k for k, rx in kinds if rx is None)
    extra = {}
    for k, _ in kinds:
        for name, lo, hi in k.get("extra", []):
            vl = pick("VENDOR_LIST", name)
            if vl is None:
                s.report["ruin_missing_list:" + name] = 1
                continue
            extra.setdefault(k["id"], []).append((vl.sid, lo, hi))
    ruin_rx, exc = re.compile(RU["ruin_rx"], re.I), re.compile(RU["exclude_rx"], re.I)
    an_rx, an_frx = re.compile(RU["animal_rx"], re.I), re.compile(RU["animal_faction_rx"], re.I)
    law = set(RU["lawful_factions"])
    skip_t, living_t, ruin_t, nest_t = (set(RU[k]) for k in ("skip_types", "living_types", "ruin_types", "nest_types"))
    mult = RU["addon_mult"]

    def scaled(a, f):
        return [int(a[0] * f), max(1 if a[1] else 0, int(math.ceil(a[1] * f)))]

    for town in sorted(ctx.all("TOWN"), key=lambda x: x.sid):
        nm, ty = town.name or "", town.values.get("type")
        f = M.get(town.refs["faction"][0].target) if town.refs.get("faction") else None
        fn = (f.name or "") if f is not None else ""
        sqs = [M[r.target] for c in ("residents", "roaming squads", "bar squads") for r in town.refs.get(c, []) if r.target in M]
        fres = [M[r.target] for r in (f.refs.get("residents", []) if f is not None and not town.values.get("residents override") else []) if r.target in M]
        ruin = bool(ruin_rx.search(nm))
        rich = sum(r.v1 for r in town.refs.get("loot spawn", []))
        if town.values.get("REMOVED"):
            why = "removed"
        elif town.sid in lair_sids:
            why = "lair_treasure"
        elif exc.search(nm):
            why = "name_excluded"
        elif ty in skip_t:
            why = "city_prison_marker"
        elif town.refs.get("bar squads") or any(q.values.get("is trader") for q in sqs + fres):
            why = "bar_or_traders"
        elif ty in nest_t and (an_rx.search(nm) or an_frx.search(fn)):
            why = "animal_nest"
        elif ty in living_t and not ruin:
            why = "living_settlement"
        elif fn in law and (town.refs.get("residents") or town.refs.get("roaming squads")) and not ruin:
            why = "lawful_inhabited"
        elif rich >= RU["rich_skip"]:
            why = "already_rich_loot"
        elif not (ty in ruin_t or ruin or any(rx and rx.search(nm) for _, rx in kinds)):
            why = "not_ruin_like"
        else:
            why = None
        if why:
            s.report["ruin_skip:" + why] += 1
            continue
        key = nm + " | " + fn
        k = next((k for k, rx in kinds if rx is not None and rx.search(key)), fallback)
        fx = mult if rich else 1.0
        refs = []
        for lid, sp in ((k["list"], k["spawn"]), ("Materials", k.get("materials", [0, 0]))):
            lo, hi = scaled(sp, fx)
            if lid in lists and hi > 0:
                refs.append(Ref(lists[lid], lo, hi, 0))
        if not rich:   # снаряжение — только там, где лута не было
            refs += [Ref(sid, lo, hi, 0) for sid, lo, hi in extra.get(k["id"], [])]
        if refs:
            s.add_refs(town.sid, "loot spawn", refs)
            s.report["ruin_kind:" + k["id"] + (":addon" if rich else "")] += 1


def race_link(ctx, s, rules):
    """RACE_LINK (2026-11-14): модовые подрасы в ванильных списках рядом со своей основой (см. rules fix.json race_link)."""
    import re
    RL = rules.get("race_link") or {}
    if not RL.get("enabled"):
        return
    M = ctx.M
    van = {n for n, _, _ in ctx.van}
    creator = lambda sid: sid.split("-", 1)[1] if "-" in sid else sid  # noqa: E731
    races = ctx.all("RACE")
    is_van = {r.sid: creator(r.sid) in van for r in races}
    van_by_name = {(r.name or "").strip().lower(): r for r in races if is_van[r.sid]}
    # живые: раса у персонажа / отряда / фракции / старта
    live = set()
    for it in M.values():
        if not ctx.in_game(it.sid):
            continue
        for c in {"CHARACTER": ("race",), "SQUAD_TEMPLATE": ("race override",), "UNIQUE_SQUAD_TEMPLATE": ("race override",),
                  "NEW_GAME_STARTOFF": ("force race",), "FACTION": ("races",)}.get(it.type_name, ()):
            live.update(x.target for x in it.refs.get(c, []))
    norm = lambda v: str(v or "").strip().lower().replace("/", "\\")  # noqa: E731
    keyf = {"m": lambda r: norm(r.values.get("male mesh")), "e": lambda r: norm(r.values.get("editor limits")),
            "a": lambda r: tuple(sorted(x.target for x in r.refs.get("animation files", [])))}
    idx = {k: {} for k in keyf}
    for r in races:
        if is_van[r.sid]:
            for k, f in keyf.items():
                v = f(r)
                if v:
                    idx[k].setdefault(v, []).append(r)
    ex = re.compile(RL["exclude_rx"], re.I)
    base = {}
    for r in races:
        if is_van[r.sid] or r.sid not in live or ex.search(r.name or ""):
            continue
        b = None
        for rx, bn in RL.get("base_by_name", []):
            if re.search(rx, r.name or "", re.I) and bn.lower() in van_by_name:
                b = van_by_name[bn.lower()]
                break
        if b is None:
            for k, f in keyf.items():
                v = f(r)
                if v and idx[k].get(v):
                    tok = (r.name or "").split(" ")[0].lower()
                    cands = idx[k][v]
                    b = next((c for c in cands if (c.name or "").split(" ")[0].lower() == tok), cands[0])
                    break
        if b is not None:
            base[r.sid] = b.sid
    s.report["race_link_mod_races"] = len(base)
    for it in list(M.values()):
        cats = RL["cats"].get(it.type_name)
        if not cats or not ctx.in_game(it.sid) or creator(it.sid) not in van:
            continue
        for c in cats:
            xs = it.refs.get(c)
            if not xs:
                continue
            have = {x.target: x for x in xs}
            add = [Ref(rs, have[bs].v0, have[bs].v1, have[bs].v2) for rs, bs in sorted(base.items()) if bs in have and rs not in have]
            if add:
                s.add_refs(it.sid, c, add)
                s.report["race_link_refs:" + it.type_name + "." + c] += len(add)


def faction_merge(ctx, s, rules):
    """FACTION_MERGE (2026-11-14, аудит мусора): фракции-двойники с одним именем из разных модов. Двойник (1-5 членов, свои пустые
    отношения) сливается в основную: все ссылки на двойника в игре перенаправляются на основную с теми же значениями."""
    FM = rules.get("faction_merge") or {}
    if not FM.get("enabled"):
        return
    M = ctx.M
    van = {n for n, _, _ in ctx.van}
    creator = lambda sid: sid.split("-", 1)[1] if "-" in sid else sid  # noqa: E731
    skip = set(FM.get("skip_names", []))
    groups = {}
    for f in ctx.all("FACTION"):
        if ctx.in_game(f.sid) and not creator(f.sid).startswith("KMM_") and (f.name or "").strip() and f.name not in skip:
            groups.setdefault(f.name.strip(), []).append(f)
    # сколько ссылок на фракцию в игре
    cnt = collections.Counter()
    for it in M.values():
        if not ctx.in_game(it.sid) or it.type_name == "FACTION":   # отношения есть у всех ко всем — считаем членов, города, диалоги
            continue
        for xs in it.refs.values():
            for x in xs:
                cnt[x.target] += 1
    remap = {}
    for name, fs in groups.items():
        if len(fs) < 2:
            continue
        canon = max(fs, key=lambda f: (creator(f.sid) in van, cnt[f.sid], not f.values.get("not real", False)))
        for f in fs:
            if f.sid != canon.sid:
                crel = {r.target: r.v0 for r in canon.refs.get("relations", []) if isinstance(r.v0, int)}
                cdef = canon.values.get("default relation", 0) or 0
                clash = [r.target for r in f.refs.get("relations", []) if isinstance(r.v0, int) and r.target not in (f.sid, canon.sid)
                         and abs(r.v0 - crel.get(r.target, cdef)) >= 40 and (r.v0 > 0) != (crel.get(r.target, cdef) > 0)]
                if clash or f.values.get("fundamental type") != canon.values.get("fundamental type"):
                    # 2026-11-14 баг Mongrel: Gunsmiths BlackPowder (торговцы, свои отношения) ушли в копию Cannibal Hunters из Shoddy Firearm —
                    # сливаем только пустого двойника того же типа, иначе это другая фракция с тем же именем
                    # (2026-11-15: отношение двойника к канону/себе не в счёт — behavior.align_twins ставит им +100)
                    s.report["faction_merge_skip:" + name + " <- " + creator(f.sid)] = cnt[f.sid]
                    continue
                remap[f.sid] = canon.sid
                s.report["faction_merge:" + name + " <- " + creator(f.sid)] = cnt[f.sid]
    if not remap:
        return
    # отряды лагерей, которые переносит KMM_Cleanup (refaction в фракцию хоста): их фракцию не трогаем — иначе у отряда две фракции
    # (баг Mongrel 14.11: cleanup ставил Mongrel, слияние — копию Gunsmiths, игра брала вторую)
    import json as _json, os as _os
    cl_squads = set()
    try:
        cl = _json.load(open(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "..", "rules", "cleanup.json"), encoding="utf-8"))
        for c in cl.get("camps", []):
            camp = M.get(c.get("camp"))
            if camp is not None:
                for xs in camp.refs.values():
                    cl_squads.update(x.target for x in xs if x.target in M and M[x.target].type_name == "SQUAD_TEMPLATE")
    except (OSError, ValueError) as e:
        raise RuntimeError(f"faction_merge: rules/cleanup.json не читается: {e}")
    for it in list(M.values()):
        if not ctx.in_game(it.sid) or it.sid in remap:
            continue
        if it.sid in cl_squads and any(x.target in remap for x in it.refs.get("faction", [])):
            s.report["faction_merge_cleanup_skip"] += 1
            continue
        for cat, xs in it.refs.items():
            if it.type_name == "FACTION" and cat == "relations":   # отношения пишет поток behavior; к пустому двойнику они ни на что не влияют
                continue
            hit = [x for x in xs if x.target in remap]
            if not hit:
                continue
            have = {x.target for x in xs}
            add = [Ref(remap[x.target], x.v0, x.v1, x.v2) for x in hit if remap[x.target] not in have and remap[x.target] != it.sid]
            s.change(it.sid, del_refs={cat: [x.target for x in hit]}, set_refs={cat: add} if add else None)
            s.report["faction_merge_refs"] += len(hit)


def junk_unlink(ctx, s, rules):
    """JUNK (2026-11-14, аудит мусора): отладочные записи модов, до которых доходит игрок (тест-куб на ванильном верстаке, заметки
    модостроителя в инвентаре, недоделанные диалоги). Ссылки на них снимаются у всех родителей (или только в указанных категориях);
    названия-заглушки у нужных записей заменяются нормальными."""
    JU = rules.get("junk_unlink") or {}
    if not JU.get("enabled"):
        return
    M = ctx.M
    spec = {x["sid"]: set(x.get("cats") or []) for x in JU.get("unlink", [])}
    for it in list(M.values()):
        if not ctx.in_game(it.sid):
            continue
        for cat, xs in it.refs.items():
            hit = [x.target for x in xs if x.target in spec and (not spec[x.target] or cat in spec[x.target])]
            if hit:
                s.change(it.sid, del_refs={cat: hit})
                s.report["junk_unlinked_refs"] += len(hit)
    done = set()
    for x in JU.get("rename", []):
        if x["sid"] in M and s.change(x["sid"], rename=x["name"]) is not None:
            s.report["junk_renamed"] += 1
            done.add(x["sid"])
    rename_auto(ctx, s, JU.get("rename_auto") or {}, done)


_LATIN_OK = lambda ch: ch < "\x7f" or "À" <= ch <= "ÿ"  # noqa: E731  ASCII + буквы Latin-1: то, что точно есть в шрифте игры


def is_nonlatin(name):
    """Флаг nonlatin (как в data/catalog.json): в имени есть символ вне ASCII/Latin-1 (иероглифы, кана, хангыль, кириллица, типографика)."""
    return any(not _LATIN_OK(ch) for ch in (name or ""))


def foreign_script(text):
    """В тексте есть буквы нелатинского письма (иероглифы, кана, хангыль, кириллица); типографика не в счёт."""
    return any(ch.isalpha() and not _LATIN_OK(ch) for ch in (text or ""))


def latin_name(name, punct):
    """Имя без нелатиницы: типографика по словарю punct, остальное снимается. None, если латинского смысла не осталось
    (меньше 4 латинских букв) — такое имя нужно в словарь."""
    import re
    t = "".join(punct.get(ch, ch) for ch in name)
    t = "".join(ch if _LATIN_OK(ch) else " " for ch in t)
    t = re.sub(r"\(\s*\)|\[\s*\]", " ", t)
    t = re.sub(r"\s+", " ", t).strip(" -_|")
    return t if sum(ch.isalpha() for ch in t) >= 4 else None


def rename_auto(ctx, s, RA, done=frozenset()):
    """RENAME_AUTO (B4 Н1/Н2, 2026-11-15): видимые игроку имена без нелатиницы и без чужих франшиз. Автосбор по всем записям
    видимых типов (types) в игре, включая копии из своих потоков (Traces копирует уников с именем): 1) имя в dict (точное имя -> новое; франшизные латинские имена тоже) или
    sid в dict_sid; 2) нелатинское имя, которое поверх ванили/основы переписал другой мод (Metro переименовал Tinfist HQ, медящик) —
    возвращается последнее латинское имя из нижних слоёв; 3) смешанное имя («机械师外骨骼MK1 Machinists exoskeleton MK1») —
    латинская часть; 4) иначе — в отчёт nonlatin_left:<тип>|<имя> (тест падает). Ключ словаря — имя, а не sid: после обновления
    мода в Workshop переименование не слетает."""
    if not RA.get("enabled"):
        return
    M = ctx.M
    types = set(RA.get("types", []))
    punct = RA.get("punct", {})
    by_name = RA.get("dict", {})
    by_sid = {k: v for k, v in RA.get("dict_sid", {}).items() if not k.startswith("_")}
    todo = {}
    for it in M.values():
        if it.type_name not in types or it.sid in done or not ctx.in_game(it.sid) or it.values.get("REMOVED"):
            continue
        n = it.name or ""
        d = it.values.get("description")
        if it.sid in by_sid or n in by_name or n.strip() in by_name or is_nonlatin(n) or (isinstance(d, str) and foreign_script(d)):
            todo[it.sid] = n
    hist = {}   # sid -> последнее латинское имя в слоях до того, кто поставил нелатиницу
    for _, m, _ in ctx.layers:
        for it in m.items:
            if it.sid in todo and it.name:
                if is_nonlatin(it.name):
                    hist.setdefault(it.sid + "\0bad", True)
                elif it.sid + "\0bad" not in hist:
                    hist[it.sid] = it.name
    for sid, n in sorted(todo.items()):
        it = M[sid]
        spec = by_sid.get(sid)
        if isinstance(spec, dict):
            new, desc = spec.get("name"), spec.get("description")
        else:
            new, desc = (spec if isinstance(spec, str) else None), None
        how = "sid"
        if new is None and (n in by_name or n.strip() in by_name):
            new, how = by_name.get(n, by_name.get(n.strip())), "dict"
        if new is None and is_nonlatin(n) and sid in hist:
            new, how = hist[sid], "restore"
        if new is None and is_nonlatin(n):
            new, how = latin_name(n, punct), "strip"
        if new is None and not is_nonlatin(n):
            new, how = n, "keep"
        if new is None:
            s.report["nonlatin_left:" + it.type_name + "|" + n] += 1
            continue
        od = it.values.get("description")
        if desc is None and isinstance(od, str) and foreign_script(od):   # описание иероглифами/кириллицей: английский текст или пусто
            ld = latin_name(od, punct) or ""
            letters = sum(ch.isalpha() for ch in od) or 1
            desc = ld if sum(ch.isalpha() for ch in ld) >= 0.6 * letters else ""
            s.report["rename_auto:description"] += 1
        vals = {"description": desc} if desc is not None else None
        if (new != n or vals) and s.change(sid, rename=new if new != n else None, values=vals) is not None:
            s.report["rename_auto:" + how] += 1


def homeless_faction(ctx, s, rules):
    """HOMELESS_FACTION (2026-11-15, BACKLOG B1): отряд из BIOME_GROUP «homeless spawns» без фракции движок не спавнит
    (kenshi_info.log «<имя>: no faction for homeless squad»). Фракция берётся: 1) от членов (CHARACTER.faction лидера/squad/squad2),
    2) от других отрядов с теми же животными (animals/animals2), 3) из rules fallback (по sid, с обоснованием),
    иначе отряд снимается из homeless spawns всех биомов."""
    HF = rules.get("homeless_faction") or {}
    if not HF.get("enabled"):
        return
    M = ctx.M
    live = lambda sid: sid in M and ctx.in_game(sid)  # noqa: E731
    has_fac = lambda it: any(live(f.target) and M[f.target].type_name == "FACTION" for f in it.refs.get("faction", []))  # noqa: E731
    users = collections.defaultdict(list)   # отряд -> [биом]
    for bg in ctx.all("BIOME_GROUP"):
        for r in bg.refs.get("homeless spawns", []):
            users[r.target].append(bg.sid)
    by_animal = collections.defaultdict(collections.Counter)   # животное -> Counter(фракция) у отрядов с фракцией
    for sq in ctx.all("SQUAD_TEMPLATE"):
        if not has_fac(sq):
            continue
        fs = [f.target for f in sq.refs.get("faction", []) if live(f.target)]
        for a in {x.target for c in ("animals", "animals2") for x in sq.refs.get(c, [])}:
            by_animal[a][fs[0]] += 1
    fb = HF.get("fallback", {})
    drop = []
    for sid in sorted(users):
        sq = M.get(sid)
        if sq is None or not ctx.in_game(sid) or sq.type_name != "SQUAD_TEMPLATE" or has_fac(sq):
            continue
        fac, how = None, None
        c = collections.Counter()
        for cat in ("leader", "squad", "squad2"):
            for r in sq.refs.get(cat, []):
                ch = M.get(r.target)
                if ch is not None and ch.type_name == "CHARACTER":
                    for f in ch.refs.get("faction", []):
                        if live(f.target) and M[f.target].type_name == "FACTION":
                            c[f.target] += 1
        if c:
            fac, how = c.most_common(1)[0][0], "members"
        if fac is None:
            c = collections.Counter()
            for a in {x.target for k in ("animals", "animals2") for x in sq.refs.get(k, [])}:
                c.update(by_animal.get(a, {}))
            if c:
                fac, how = c.most_common(1)[0][0], "animals"
        if fac is None and sid in fb and live(fb[sid]["faction"]):
            fac, how = fb[sid]["faction"], "fallback"
        if fac is None:
            drop.append(sid)
            continue
        s.change(sid, set_refs={"faction": [Ref(fac, 0, 0, 0)]})
        s.report["homeless_faction_" + how] += 1
        s.report["homeless_faction:" + (sq.name or sid) + " -> " + (M[fac].name or fac) + " (" + how + ")"] = len(users[sid])
    if drop:
        dset = set(drop)
        for bg in ctx.all("BIOME_GROUP"):
            hit = [r.target for r in bg.refs.get("homeless spawns", []) if r.target in dset]
            if hit:
                s.change(bg.sid, del_refs={"homeless spawns": hit})
                s.report["homeless_faction_dropped_refs"] += len(hit)
        for sid in drop:
            s.report["homeless_faction_dropped:" + (M[sid].name or sid)] = len(users[sid])


def xp_curve(ctx, s, rules):
    """XP_CURVE (2026-11-15, BACKLOG P5): нелинейная прокачка через ванильную кривую разницы навыков (CONSTANTS, fcs.def «xp»).
    KMM_Fix — единственный поток-владелец xp-полей CONSTANTS; грузится после KMM_Merged (там «Weaklings give XP»: penalty 50)."""
    XC = rules.get("xp_curve") or {}
    if not XC.get("enabled"):
        return
    it = next((c for c in ctx.all("CONSTANTS")), None)
    if it is None:
        raise RuntimeError("xp_curve: нет записи CONSTANTS")
    out = {}
    for k, v in XC["values"].items():
        if k not in it.values:
            raise RuntimeError(f"xp_curve: поля {k!r} нет в CONSTANTS")
        if kb_f32(it.values[k]) != kb_f32(v):
            out[k] = F32(v)
            s.report[f"xp_curve:{k} {it.values[k]:g} -> {float(v):g}"] = 1
    if out:
        s.change(it.sid, values=out)


def rivals(ctx, s, rules):
    """RIVALS (2026-11-15, BACKLOG Q1): соперники-искатели удачи = уже существующие бродячие отряды (homeless spawns ванили и модов:
    Drifters / Tech Hunters / Scavengers / Bounty Hunters / Mercenary Guild). Новых фракций и спавнов нет. Сделано два шага:
    1) у «руинных» искателей ближний патруль (unloaded PATROL_SHORTRANGE) меняется на клон того же пакета, у клона unloaded func
       PATROL_LONGRANGE (3). Вне экрана они ходят по всей карте, а не вокруг точки спавна (как у ванильных «Patrol map rebirth slavers»: 6/3);
    2) всем им добавлен ванильный «hang out in a bar» (v0=0) для встреч в барах (ритм ванильного «Drifter solo»: бродить v0=1 + бар v0=0).
    Тиры силы берутся по combat stats лидера/членов (слабые / средние / сильные) и идут только в отчёт.
    Веса спавна по опасности биома НЕ здесь: BIOME_GROUP.homeless spawns принадлежит потоку relics (правка отсюда = конфликт поля)."""
    RV = rules.get("rivals") or {}
    if not RV.get("enabled"):
        return
    M = ctx.M
    clones = {}
    for src_sid, spec in RV["long_range_clones"].items():
        src = M.get(src_sid)
        if src is None or src.type_name != "AI_PACKAGE":
            raise KeyError(f"rivals: AI_PACKAGE {src_sid} не найден")
        p = s.new("AI_PACKAGE", spec["name"], template=src_sid,
                  values={"unloaded func": int(spec["unloaded func"]), "signal func": int(spec["signal func"])})
        clones[src_sid] = p.sid
        s.report["rivals_packages_new"] += 1
    bar = RV["bar_package"]
    if bar not in M or M[bar].type_name != "AI_PACKAGE":
        raise KeyError(f"rivals: пакет бара {bar} не найден")
    users = collections.Counter()
    looters = {}   # X4: шаблоны искателей с пакетом LOOTING -> build/KMM_Conductor/rivals.json (KMM_RelicRace: кто опустошает руины)
    for bg in ctx.all("BIOME_GROUP"):
        for r in bg.refs.get("homeless spawns", []):
            if 0 < r.v0 < 2147483647:
                users[r.target] += r.v0
    for sid in list(RV["prospectors"]) + list(RV["wanderers"]):
        sq = M.get(sid)
        if sq is None or sq.type_name != "SQUAD_TEMPLATE" or not ctx.in_game(sid):
            raise KeyError(f"rivals: SQUAD_TEMPLATE {sid} не найден")
        if not users[sid]:
            s.report["rivals_skip_not_spawned:" + (sq.name or sid)] = 1
            continue
        pk = sq.refs.get("AI packages", [])
        add, rm = [], []
        if sid in RV["prospectors"]:
            for r in pk:
                if r.target in clones:
                    add.append(Ref(clones[r.target], max(1, r.v0), r.v1, r.v2))
                    rm.append(r.target)
            if not rm:
                raise RuntimeError(f"rivals: у {sq.name} нет пакета из long_range_clones")
        if not any(r.target == bar for r in pk):
            add.append(Ref(bar, 0, 0, 0))
        if add:
            s.change(sid, set_refs={"AI packages": add}, del_refs={"AI packages": rm} if rm else None)
        tier, pw = rival_tier(M, sq, RV["tiers"])
        s.report["rivals_tier_" + tier] += 1
        s.report["rivals_tier_" + tier + "_weight"] += users[sid]
        s.report[f"rivals:{sq.name} [{tier} {pw}] w{users[sid]}" + (" longrange" if rm else "") + (" +bar" if any(a.target == bar for a in add) else "")] = 1
        if sid in RV["prospectors"]:
            looters[sid] = {"name": sq.name or sid, "tier": tier, "pw": pw}
    dst = os.path.join(r"C:\KenshiModMap", "build", "KMM_Conductor", "rivals.json")
    json.dump({"_doc": "RIVALS Q1 (fix.py rivals): шаблоны отрядов-искателей с пакетом LOOTING, по ним KMM_RelicRace узнаёт грабителей руин (X4)",
               "prospectors": looters}, open(dst, "w", encoding="utf-8"), ensure_ascii=False, indent=0, sort_keys=True)
    s.report["rivals_looters_json"] = len(looters)


def kb_f32(v):
    import struct
    return struct.unpack("<f", struct.pack("<f", float(v)))[0]
