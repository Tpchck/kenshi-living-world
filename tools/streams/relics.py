"""Поток D RELICS: WH-фракции и отряды в мире — остатки Империума (фракция + патрули в опасных зонах), варбанда орков.
Тиры снаряжения, клоны-тиры и T0-предметы перенесены в WARDROBE (DECISIONS 2026-11-11): снаряжение персонажам выдаёт он.
Владение: BIOME_GROUP, военные/WH SQUAD_TEMPLATE, WEAPON/ARMOUR/CROSSBOW/WEAPON_MANUFACTURER (поля самих предметов)."""
from kmod import F32, Ref


def build(ctx, s, rules):
    # --- остатки Империума ------------------------------------------------------------
    ir = rules["imperial_remnants"]
    tmpl = ctx.find(*ir["faction_template"])
    fac = s.new("FACTION", ir["faction_name"], template=tmpl.sid, values={
        "fundamental type": 2, "trustworthy": F32(30.0), "run away ratio of squad size": F32(0.2),
        "run away ratio relative to enemy": F32(0.4), "heals strangers": True, "anti slavery": True})
    fac.refs = {k: v for k, v in fac.refs.items() if k in ("races", "personality", "color", "dialog default")}
    fac.refs["relations"] = [Ref(ctx.find(t, n).sid, val, 0, 0) for t, n, val in ir["hostile"] + ir["friendly"]]
    s.report["relations_own"] = len(fac.refs["relations"])
    patrol_ai = [Ref(ctx.find(*a).sid) for a in ir["patrol_ai"]]
    squad_tmpl = ctx.find("SQUAD_TEMPLATE", "TC Shek Warrior Patrol")
    for sq in ir["squads"]:
        leader = ctx.find(*sq["leader"])
        q = s.new("SQUAD_TEMPLATE", sq["name"], template=squad_tmpl.sid)
        q.refs = {"AI packages": list(patrol_ai), "faction": [Ref(fac.sid)], "leader": [Ref(leader.sid, 1, 0, 0)]}
        for t, n, sid, lo, hi in sq["members"]:
            q.refs["squad"] = [Ref(ctx.find(t, n, sid).sid, lo, hi, 0)]
        for biome, w in ir["spawns"]:
            s.add_refs(ctx.find("BIOME_GROUP", biome).sid, "homeless spawns", [Ref(q.sid, w, 0, 0)])
            s.report["spawn_entries"] += 1
        fac.refs.setdefault("squads", []).append(Ref(q.sid))
        s.report["squads_new"] += 1

    # --- варбанда орков ---------------------------------------------------------------
    gw = rules["greenskin_warband"]
    gfac = ctx.find(*gw["faction"])
    ai_src = ctx.find(*gw["ai_from_squad"])
    q = s.new("SQUAD_TEMPLATE", gw["name"], template=ai_src.sid)
    q.refs = {k: v for k, v in q.refs.items() if k in ("AI packages", "dialog leader", "dialog squad")}
    q.refs["faction"] = [Ref(gfac.sid)]
    q.refs["leader"] = [Ref(ctx.find(*gw["leader"]).sid, 1, 0, 0)]
    (t1, n1, _, a1, b1), (t2, n2, _, a2, b2) = gw["members"]
    q.refs["squad"] = [Ref(ctx.find(t1, n1).sid, a1, b1, 0)]
    q.refs["squad2"] = [Ref(ctx.find(t2, n2).sid, a2, b2, 0)]
    for biome, w in gw["spawns"]:
        s.add_refs(ctx.find("BIOME_GROUP", biome).sid, "homeless spawns", [Ref(q.sid, w, 0, 0)])
        s.report["spawn_entries"] += 1
    s.add_refs(gfac.sid, "squads", [Ref(q.sid)])
    s.report["squads_new"] += 1

    # --- ARMS (2026-11-13): математика снаряжения. Нормализация значений существующих ARMOUR/WEAPON каталога (tools/arms_audit.py:plan) ---------
    AR = rules.get("arms") or {}
    if AR.get("enabled"):
        import sys as _sys2
        _sys2.path.insert(0, "C:/KenshiModMap/tools")
        import arms_audit as _aa
        P = _aa.plan(ctx, AR)
        # item_scale (владелец 2026-11-13: «Корону Императора в 2 раза ослабить»): поверх ARMS эффект вещи × scale —
        # множители 1+(m-1)·k, сопротивления пропускают урон в 1/k раз больше, целые бонусы ×k
        SC = {k: v for k, v in (AR.get("item_scale") or {}).items() if not k.startswith("_")}

        def _scaled(sid, ch):
            sp = SC.get(sid)
            if not sp or sid not in ctx.M:
                return ch, {}
            it, k_, out, typ = ctx.M[sid], float(sp["scale"]), dict(ch), {}
            for key, x in it.values.items():
                cur = out.get(key, x)
                if isinstance(cur, bool) or not isinstance(cur, (int, float)):
                    continue
                if key in sp["mult_fields"] and cur > 1:
                    out[key] = round(1 + (cur - 1) * k_, 3)
                elif key in sp["resist_fields"] and 0 < cur < 1:
                    out[key] = round(max(0.0, 1 - (1 - cur) / k_), 3)
                elif key in sp["int_fields"] and cur > 0:
                    out[key] = int(round(cur * k_))
                else:
                    continue
                typ[key] = isinstance(x, int)
            s.report["arms_item_scaled"] += 1
            return out, typ

        for sid_ in [k for k in SC if k not in P["plan"]]:
            P["plan"][sid_] = {"ch": {}, "info": {"relic": True}}
        for sid_, v_ in P["plan"].items():
            ch_, typ_ = _scaled(sid_, v_["ch"])
            if not ch_:
                continue
            fl = {k: (int(x) if typ_.get(k) or (k not in typ_ and k in AR["int_fields"]) else F32(x)) for k, x in ch_.items()}
            s.change(sid_, values=fl)
            s.report["arms_items_changed"] += 1
            s.report["arms_relic_uplift" if v_["info"]["relic"] else "arms_outlier_clamped"] += 1
        # носители силовой брони и реликтов: бродячие отряды только в опасных краевых биомах (lore_hard power_armor + реликтовые фракции дирижёра)
        import json as _j2
        _w = _j2.load(open("C:/KenshiModMap/rules/streams/wardrobe.json", encoding="utf-8"))
        _c = _j2.load(open("C:/KenshiModMap/rules/conductor.json", encoding="utf-8"))
        rnames = set(_w["context"]["lore_hard"]["power_armor"]["factions"]) | {f_["name"] for f_ in _c["factions"].values() if f_.get("relic")} | set(AR["relic_faction_extra"])
        rf = {f_.sid for f_ in ctx.all("FACTION") if f_.name in rnames} | {fac.sid}
        allow_b = set(AR["relic_biomes"])
        moved = {}
        for bg in ctx.all("BIOME_GROUP"):
            if bg.name in allow_b:
                continue
            dele = []
            for r in bg.refs.get("homeless spawns", []):
                sq = ctx.M.get(r.target)
                if sq is None or sq.type_name != "SQUAD_TEMPLATE" or not (0 < r.v0 < 2147483647) or not sq.refs.get("faction"):
                    continue
                if sq.refs["faction"][0].target in rf:
                    dele.append(r.target)
                    moved[r.target] = moved.get(r.target, 0) + r.v0
            if dele:
                s.change(bg.sid, del_refs={"homeless spawns": dele})
                s.report["arms_relic_spawns_removed"] += len(dele)
        edge = [bg for bg in ctx.all("BIOME_GROUP") if bg.name in allow_b]
        for sq_sid, w_ in moved.items():
            nw_ = max(1, int(round(w_ * AR["relic_spawn_move_frac"] / max(1, len(edge)))))
            for bg in edge:
                if any(r.target == sq_sid for r in bg.refs.get("homeless spawns", [])):
                    continue
                s.add_refs(bg.sid, "homeless spawns", [Ref(sq_sid, nw_, 0, 0)])
                s.report["arms_relic_spawns_added"] += 1

    # --- бюджет происхождения: доля NPC WH-фракций в спавнах биомов ≤ target (rules/budget.json) ---------------------
    import json
    # --- кристальные жуки: редкие и только в подходящих местах (rules crystal_spawns) ---
    import re as _re
    CS = rules.get("crystal_spawns") or {}
    if CS:
        crx = _re.compile(CS["name_rx"], _re.I)
        crys = {i.sid for t in ("SQUAD_TEMPLATE", "TOWN") for i in ctx.all(t) if crx.search(i.name or "")}
        allow = set(CS["allow_biomes"])
        for bg in ctx.all("BIOME_GROUP"):
            dele, upd = {}, {}
            for cat, key in (("nests", "nests"), ("homeless spawns", "homeless")):
                for r in bg.refs.get(cat, []):
                    if r.target not in crys:
                        continue
                    if bg.name not in allow:
                        dele.setdefault(cat, []).append(r.target)
                    else:
                        w = max(1, min(CS[key]["cap"], round(r.v0 * CS[key]["factor"])))
                        if w != r.v0:
                            upd.setdefault(cat, []).append(Ref(r.target, w, r.v1, r.v2))
            if dele or upd:
                s.change(bg.sid, set_refs=upd, del_refs=dele)
                s.report["crystal_spawn_removed"] += sum(map(len, dele.values()))
                s.report["crystal_spawn_reduced"] += sum(map(len, upd.values()))
    # --- перекосы спавна модов (audit_classes D, 2026-11-13): HTDEnforcers 2000 при медиане 2 в Deadlands и т.п.
    SK = rules.get("spawn_skew") or {}
    if SK:
        import statistics as _st
        van = set(SK.get("vanilla_mods", []))
        skip_rx = _re.compile(SK.get("skip_name_rx", "^$"), _re.I)
        done = {(sid, r.target) for sid, it in s.mb.items.items() if getattr(it, "type_name", "") == "BIOME_GROUP"
                for rs in it.refs.values() for r in rs}
        for bg in ctx.all("BIOME_GROUP"):
            upd = {}
            for cat in ("nests", "homeless spawns"):
                ws = [r for r in bg.refs.get(cat, []) if 0 < r.v0 < 2147483647]
                if len(ws) < 4:
                    continue
                med = _st.median(r.v0 for r in ws)
                for r in ws:
                    t = ctx.M.get(r.target)
                    if t is None or ctx.origin.get(r.target) in van or skip_rx.search(t.name or "") or (bg.sid, r.target) in done:
                        continue
                    if r.v0 >= SK["min_weight"] and r.v0 > SK["ratio"] * med:
                        nv = max(SK["floor"], int(round(SK["cap_x_median"] * med)))
                        upd.setdefault(cat, []).append(Ref(r.target, nv, r.v1, r.v2))
                        s.report["spawn_skew_capped"] += 1
            if upd:
                s.change(bg.sid, set_refs=upd)
    # --- пропорции фракций по биомам (BALANCE, rules faction_balance): структура архетипов — к ванильной ± tol ---------------
    FB = rules.get("faction_balance") or {}
    fb_ref = {}   # (biome sid, cat) -> ориентир долей архетипов (для страховки rival_danger ниже)
    if FB.get("enabled"):
        import collections as _co
        import statistics as _st
        import json as _js
        import sys as _sys
        _sys.path.insert(0, r"C:\KenshiModMap\tools")
        import balance_lib as _bl
        import kmod as _km
        wr = _js.load(open(r"C:\KenshiModMap\rules\streams\behavior.json", encoding="utf-8"))["world_relations"]
        vmods = set(FB["vanilla_mods"])
        Mv = {}
        for _n, _m, _ in ctx.layers:
            if _n in vmods:
                _km.apply(Mv, _m)
        fc_f, uc_f, fc_v, uc_v = {}, {}, {}, {}
        skip_rx = _re.compile(FB["skip_name_rx"], _re.I)
        skip_arch = set(FB["skip_archetypes"])
        tol, floor = FB["tol"], FB["floor"]

        def live(src, own, cat):
            rm = {r.target: r for r in src.refs.get(cat, [])} if src is not None else {}
            for r in (own.refs.get(cat, []) if own else []):
                rm[r.target] = r
            return [r for r in rm.values() if 0 < r.v0 < 2147483647 and (r.v1, r.v2) != (2147483647, 2147483647)]

        def shares(rs, M_, fc, uc, wmap=None):
            acc = _co.Counter()
            for r in rs:
                for a, sz in _bl.entry_units(M_, r.target, wr, fc, uc):
                    acc[a] += (wmap[r.target] if wmap else r.v0) * sz
            tot = sum(acc.values()) or 1
            return {a: v / tot for a, v in acc.items()}

        world_ref = {}
        for cat in ("nests", "homeless spawns"):
            acc = _co.Counter()
            for b in Mv.values():
                if b.type_name == "BIOME_GROUP":
                    for a, sh in shares(live(b, None, cat), Mv, fc_v, uc_v).items():
                        acc[a] += sh
            tt = sum(acc.values()) or 1
            world_ref[cat] = {a: v / tt for a, v in acc.items()}
        for bg in ctx.all("BIOME_GROUP"):
            for cat in ("nests", "homeless spawns"):
                own = s.mb.items.get(bg.sid)
                rs = live(bg, own, cat)
                if len(rs) < 2:
                    continue
                vb = Mv.get(bg.sid)
                n_van = len(live(vb, None, cat))
                sparse = n_van < FB["sparse_min"]
                if sparse and cat == "nests":
                    continue
                ref = world_ref[cat] if sparse else shares(live(vb, None, cat), Mv, fc_v, uc_v)
                fb_ref[bg.sid, cat] = ref
                ent = []   # архетип масштабируемой записи (добавлена модами в этот биом, не событие, не KMM) или None
                van_t = {x.target: x.v0 for x in live(vb, None, cat)}   # ванильные веса записи в этом биоме
                for r in rs:
                    t_ = ctx.M.get(r.target)
                    org = ctx.origin.get(r.target, "KMM")
                    if t_ is None or (r.target in van_t and r.v0 <= van_t[r.target]) or str(org).startswith("KMM") or skip_rx.search(t_.name or ""):
                        ent.append(None)
                        continue
                    dom = _co.Counter()
                    for a, sz in _bl.entry_units(ctx.M, r.target, wr, fc_f, uc_f):
                        dom[a] += sz
                    ent.append(dom.most_common(1)[0][0] if dom else None)
                def nw(r, k):   # новый вес; ванильная запись, раздутая модом, — не ниже ванильного веса и не выше текущего
                    v = max(1, int(round(r.v0 * k)))
                    if r.target in van_t:
                        v = min(r.v0, max(van_t[r.target], v))
                    return v
                K = _co.defaultdict(lambda: 1.0)
                kmax = FB.get("max_factor", 2.5)
                for _ in range(80):
                    wmap = {r.target: (nw(r, K[ent[i]]) if ent[i] and ent[i] not in skip_arch else r.v0) for i, r in enumerate(rs)}
                    sh = shares(rs, ctx.M, fc_f, uc_f, wmap)
                    moved = False
                    for a in set(e for e in ent if e and e not in skip_arch):
                        cap = max(ref.get(a, 0.0) * (1 + tol), floor)
                        low = ref.get(a, 0.0) * (1 - tol)
                        cur = sh.get(a, 0.0)
                        if cur > cap and K[a] > FB["min_factor"] + 1e-9:
                            K[a] = max(FB["min_factor"], K[a] * max(0.6, (cap * FB["aim"] / cur) ** 0.7))
                            moved = True
                        elif low > 0.05 and cur < low and K[a] < kmax - 1e-9:
                            K[a] = min(kmax, K[a] * min(1.5, (ref[a] / max(cur, 1e-6)) ** 0.5))
                            moved = True
                    if not moved:
                        break
                fresh, n_upd = [], 0
                mine = {x.target: x for x in (own.refs.get(cat, []) if own else [])}
                med = _st.median(r.v0 for r in rs)
                for i, r in enumerate(rs):
                    if ent[i] and ent[i] not in skip_arch and K[ent[i]] != 1.0:
                        nv = nw(r, K[ent[i]])
                        if nv > r.v0:
                            nv = min(nv, max(r.v0, int(3 * med)))
                        if nv != r.v0:
                            n_upd += 1
                            if r.target in mine:
                                mine[r.target].v0 = nv
                            else:
                                fresh.append(Ref(r.target, nv, r.v1, r.v2))
                if fresh:
                    s.change(bg.sid, set_refs={cat: fresh})
                if n_upd:
                    s.report["balance_entries_scaled"] += n_upd
                    s.report["balance_slots_changed"] += 1
                    for a in K:
                        if K[a] < 1.0:
                            s.report["balance_scaled_arch:" + a] += 1
                        elif K[a] > 1.0:
                            s.report["balance_raised_arch:" + a] += 1
    # --- RIVALS по опасности (R5): веса искателей удачи (fix.json rivals) по тиру × опасность биома; до бюджета WH (он режет после) ---
    RD = rules.get("rival_danger") or {}
    if RD.get("enabled"):
        _rival_danger(ctx, s, RD, set((rules.get("arms") or {}).get("relic_biomes", [])), fb_ref,
                      dict(shares=shares, fc=fc_f, uc=uc_f, Mv=Mv, tol=tol, floor=floor) if FB.get("enabled") else None,
                      FB.get("vanilla_mods", []))
    import sys
    sys.path.insert(0, r"C:\KenshiModMap\tools\build")
    import budget
    target = budget.RULES["share_max"] * 0.92
    whf = budget.wh_factions(ctx) | {fac.sid}
    new_sq = {it.sid: it for it in s.mb.items.values() if it.type_name == "SQUAD_TEMPLATE"}
    entries = []   # (biome_sid, ref, weight*size, wh?)
    for b in ctx.all("BIOME_GROUP"):
        own = s.mb.items.get(b.sid)
        rm = {r.target: r for r in b.refs.get("homeless spawns", [])}   # итоговые веса: правки этого потока поверх исходных
        for r in (own.refs.get("homeless spawns", []) if own else []):
            rm[r.target] = r
        refs = list(rm.values())
        for r in refs:
            sq = ctx.M.get(r.target) or new_sq.get(r.target)
            if sq is None or (r.v0, r.v1, r.v2) == (2147483647,) * 3:
                continue
            is_wh = bool(sq.refs.get("faction")) and sq.refs["faction"][0].target in whf
            entries.append((b.sid, r, max(0, r.v0) * budget.squad_size(sq), is_wh))
    wh = sum(e[2] for e in entries if e[3])
    non = sum(e[2] for e in entries if not e[3])
    s.report["spawn_share_before"] = round(wh / max(1, wh + non), 4)
    if wh and wh / (wh + non) > target:
        f = target * non / ((1 - target) * wh)
        for bsid, r, _, is_wh in entries:
            if not is_wh or r.v0 <= 1:
                continue
            nv = max(1, int(round(r.v0 * f)))
            if nv == r.v0:
                continue
            own = s.mb.items.get(bsid)
            mine = own is not None and any(x is r for x in own.refs.get("homeless spawns", []))
            if mine:
                r.v0 = nv
            else:
                s.change(bsid, set_refs={"homeless spawns": [Ref(r.target, nv, r.v1, r.v2)]})
            s.report["spawn_weights_trimmed"] += 1
    # --- S1 ЭХО ПАВШИХ (2026-11-15): светящиеся тела душ (Soul World, фракция Soulbodies) — не случайный спавн биома, а эхо боя:
    # веса их записей в biome spawns x weight_mult (последним проходом, поверх баланса и бюджета); ночные эхо у места бойни — KMM_Predators.
    _soul_echo(ctx, s, rules.get("soul_echo") or {})
    # --- A1 ОРДЕНА КОСМОДЕСАНТА (2026-11-15): лагеря Mark-X сняты, ордена — фракции с иерархией и бродячими отрядами в своём опасном регионе.
    # Последним проходом: веса орденов не трогают ни баланс, ни бюджет WH (их масса мала, отчёт astartes_*).
    _astartes_chapters(ctx, s, rules.get("astartes_chapters") or {})


def _astartes_chapters(ctx, s, AC):
    """A1 (docs/core/ASTARTES.md). Только ванильные рычаги данных: TOWN.REMOVED, BIOME_GROUP.homeless spawns, FACTION (клон шаблона
    с отношениями), CHARACTER (клоны носителей брони ордена), SQUAD_TEMPLATE (бродячие отряды с ванильным AI-пакетом патруля).
    Существующие записи: только REMOVED у лагерей и снятие записей спавна; всё остальное — новые записи."""
    import kmod as _km
    if not AC.get("enabled"):
        return
    M = ctx.M
    DEL = _km.DELETED_REF
    live = lambda r: (r.v0, r.v1, r.v2) != DEL  # noqa: E731

    # 1. лагеря космодесанта: ванильный флаг REMOVED (обратимо)
    for sid, why in AC["remove_camps"]:
        t = M.get(sid)
        if t is None or t.type_name != "TOWN":
            raise KeyError(f"astartes: TOWN {sid} ({why}) не найден")
        if t.values.get("REMOVED") is not True:
            s.change(sid, values={"REMOVED": True})
            s.report["astartes_camps_removed"] += 1
    # 2. случайные спавны: записи отрядов remove_spawn_factions во всех биомах (исходные + уже правленные этим потоком)
    rmf = {f.sid for f in ctx.all("FACTION") if f.name in set(AC["remove_spawn_factions"])}
    rms = {q.sid for q in ctx.all("SQUAD_TEMPLATE") if q.refs.get("faction") and q.refs["faction"][0].target in rmf}
    for b in ctx.all("BIOME_GROUP"):
        own = s.mb.items.get(b.sid)
        for cat in ("homeless spawns", "nests"):
            mine = [x for x in (own.refs.get(cat, []) if own else []) if x.target in rms]
            for x in mine:
                if live(x):
                    x.v0, x.v1, x.v2 = DEL
                    s.report["astartes_spawns_removed"] += 1
            have = {x.target for x in mine}
            orig = sorted({r.target for r in b.refs.get(cat, []) if r.target in rms and live(r) and r.target not in have})
            if orig:
                s.change(b.sid, del_refs={cat: orig})
                s.report["astartes_spawns_removed"] += len(orig)

    # 3. фракции орденов
    tmpl = ctx.find("FACTION", AC["faction_template"])
    by_name = {}
    for f in ctx.all("FACTION") + [it for it in s.mb.items.values() if it.type_name == "FACTION" and it.change == _km.CHANGE_NEW]:   # + остатки Империума этого потока
        by_name.setdefault(f.name, []).append(f.sid)

    def fsids(n):
        if n not in by_name:
            raise KeyError(f"astartes: FACTION {n!r} не найдена")
        return by_name[n]

    race = {k: ctx.find("RACE", AC[k]).sid for k in ("faction_race", "default_race", "elite_race")}
    base_rel = {r.target: r.v0 for r in tmpl.refs.get("relations", []) if r.target in M and live(r)}
    facs = {}
    for ch in AC["chapters"]:
        f = s.new("FACTION", ch["faction"], template=tmpl.sid, values=dict(AC["faction_values"]))
        f.refs = {k: v for k, v in f.refs.items() if k in ("personality", "color", "dialog default")}   # без лагеря, кампаний, жителей, соседства
        f.refs["races"] = [Ref(race["faction_race"], 100, 0, 0)]
        facs[ch["key"]] = f
    for ch in AC["chapters"]:
        f = facs[ch["key"]]
        rel = dict(base_rel)
        for n, v in AC["relations_override"]:
            for x in fsids(n):
                rel[x] = v
        for n in AC["allies"]:
            for x in fsids(n):
                rel[x] = AC["ally_value"]
        for k2, f2 in facs.items():
            if k2 != ch["key"]:
                rel[f2.sid] = AC["chapter_value"]
        rel.pop(f.sid, None)
        f.refs["relations"] = [Ref(t, v, 0, 0) for t, v in sorted(rel.items())]
        s.report["astartes_relations"] += len(rel)

    # 4. ранги: клоны носителей брони ордена; 5. отряды и спавны только в регионе ордена
    squad_tmpl = ctx.find(*AC["squad_template"])
    patrol = [Ref(ctx.find(*AC["patrol_ai"]).sid, 0, 0, 0)]

    def src_char(spec):
        t, n, sid = spec
        c = M.get(sid)
        if c is None or c.type_name != t or c.name != n or not ctx.in_game(sid):
            raise KeyError(f"astartes: {t} {n!r} ({sid}) не найден")
        return c

    for ch in AC["chapters"]:
        fac = facs[ch["key"]]
        rank = {}
        for rk, sp in ch["ranks"].items():
            src = src_char(sp["src"])
            c = s.new("CHARACTER", sp["name"], template=src.sid, values={"unique": bool(sp.get("unique")), "named": False})
            if not c.refs.get("race"):
                c.refs["race"] = [Ref(race["elite_race" if sp.get("elite") else "default_race"], 100, 0, 0)]
            c.refs.pop("dialogue package player", None)
            if sp.get("pkg_from"):
                c.refs["dialogue package"] = [Ref(r.target, r.v0, r.v1, r.v2) for r in M[sp["pkg_from"]].refs.get("dialogue package", [])]
            c.refs["faction"] = [Ref(fac.sid, 0, 0, 0)]
            if sp.get("unique"):
                c.values["faction importance"] = F32(100.0)
                s.report["astartes_masters"] += 1
            rank[rk] = c.sid
            s.report["astartes_characters"] += 1

        def who(x):
            return rank[x] if isinstance(x, str) else src_char(x).sid

        role_sq = {}
        for sq in ch["squads"]:
            q = s.new("SQUAD_TEMPLATE", sq["name"], template=squad_tmpl.sid, values=dict(AC["squad_values"]))
            q.refs = {"AI packages": list(patrol), "faction": [Ref(fac.sid, 0, 0, 0)], "leader": [Ref(who(sq["leader"]), 1, 0, 0)],
                      "squad": [Ref(who(m), lo, hi, 0) for m, lo, hi in sq["members"]]}
            fac.refs.setdefault("squads", []).append(Ref(q.sid, 0, 0, 0))
            role_sq[sq["role"]] = q.sid
            s.report["astartes_squads"] += 1
        for biome, ws in ch["spawns"]:
            bsid = ctx.find("BIOME_GROUP", biome).sid
            for role, w in sorted(ws.items()):
                s.add_refs(bsid, "homeless spawns", [Ref(role_sq[role], int(w), 0, 0)])
                s.report["astartes_spawn_entries"] += 1
                s.report["astartes_spawn_weight"] += int(w)
        s.report[f"astartes:{ch['faction']} -> {', '.join(b for b, _ in ch['spawns'])}"] = len(ch["squads"])


def _soul_echo(ctx, s, SE):
    """S1: отряды фракции SE["faction"] реже в биомах + ванильный пакет движения.
    Веса: итоговые веса записей шаблона (правки этого потока поверх исходных) по всем биомам x weight_mult; веса целые, поэтому масса
    шаблона T = round(W*mult) раздаётся методом наибольшего остатка (floor(w*mult) + единицы записям с большей дробной частью, при равенстве —
    по имени биома); запись с 0 снимается из биома. Так x0.3 честный и при весах 1–3. Пакет: шаблоны фракции с пакетом из pkg_from и
    членами CHARACTER получают pkg_to с теми же числами ссылки (у pkg_from signal func 0 / unloaded func 0: «Patrol» без маршрута ?)."""
    import kmod as _km
    if not SE.get("enabled"):
        return
    M, MAXI = ctx.M, 2147483647
    fid = SE["faction"]
    if fid not in M or not ctx.in_game(fid):
        s.report["soul_echo_skip_no_faction"] = 1
        return
    sq = {i.sid for i in ctx.all("SQUAD_TEMPLATE") if i.refs.get("faction") and i.refs["faction"][0].target == fid}
    s.report["soul_echo_squads"] = len(sq)
    k = float(SE["weight_mult"])
    ent = {}   # шаблон -> [(биом, cat, ref)]
    for b in ctx.all("BIOME_GROUP"):
        own = s.mb.items.get(b.sid)
        for cat in SE.get("cats", ["homeless spawns"]):
            rm = {r.target: r for r in b.refs.get(cat, []) if r.target in sq}
            for r in (own.refs.get(cat, []) if own else []):
                if r.target in sq:
                    rm[r.target] = r
            for r in rm.values():
                if 0 < r.v0 < MAXI and (r.v0, r.v1, r.v2) != _km.DELETED_REF:
                    ent.setdefault(r.target, []).append((b, cat, r))
    for tsid in sorted(ent):
        rows = ent[tsid]
        W = sum(r.v0 for _, _, r in rows)
        T = int(round(W * k))
        base = [int(r.v0 * k) for _, _, r in rows]
        order = sorted(range(len(rows)), key=lambda i: (-(rows[i][2].v0 * k - base[i]), rows[i][0].name or rows[i][0].sid))
        for i in order[:max(0, T - sum(base))]:
            base[i] += 1
        s.report["soul_echo_weight_before"] += W
        s.report["soul_echo_weight_after"] += sum(base)
        s.report[f"soul_echo:{M[tsid].name} {W}->{sum(base)} in {sum(1 for x in base if x)}/{len(rows)} biomes"] = 1
        for (b, cat, r), nv in zip(rows, base):
            if nv == r.v0:
                continue
            own = s.mb.items.get(b.sid)
            mine = [x for x in (own.refs.get(cat, []) if own else []) if x.target == r.target and 0 < x.v0 < MAXI]
            if nv <= 0:
                if mine:
                    for x in mine:
                        x.v0, x.v1, x.v2 = _km.DELETED_REF
                else:
                    s.change(b.sid, del_refs={cat: [r.target]})
                s.report["soul_echo_spawns_dropped"] += 1
                continue
            if mine:
                for x in mine:
                    x.v0 = nv
            else:
                s.change(b.sid, set_refs={cat: [Ref(r.target, nv, r.v1, r.v2)]})
            s.report["soul_echo_spawns_scaled"] += 1
    src, dst = set(SE.get("pkg_from", [])), SE.get("pkg_to")
    if not dst:
        return
    if dst not in M or M[dst].type_name != "AI_PACKAGE":
        raise KeyError(f"soul_echo: AI_PACKAGE {dst} не найден")
    for sid in sorted(sq):
        q = M[sid]
        old = [r for r in q.refs.get("AI packages", []) if r.target in src]
        if not old or any(r.target == dst for r in q.refs.get("AI packages", [])):
            continue
        mem = [M.get(x.target) for c in ("leader", "squad", "squad2") for x in q.refs.get(c, [])]
        if not any(m_ is not None and m_.type_name == "CHARACTER" for m_ in mem):
            s.report["soul_echo_pkg_skip_animals:" + (q.name or sid)] = 1
            continue
        s.change(sid, set_refs={"AI packages": [Ref(dst, old[0].v0, old[0].v1, old[0].v2)]}, del_refs={"AI packages": [r.target for r in old]})
        s.report["soul_echo_pkg_swapped"] += 1
        s.report["soul_echo_pkg:" + (q.name or sid)] = 1


def _rival_danger(ctx, s, RD, relic_biomes, fb_ref, fb, vanilla_mods):
    """R5 (2026-11-15, продолжение Q1): прокачка через встречи. Соперники = бродячие отряды искателей из rules/streams/fix.json
    rivals (prospectors + wanderers), тир по _shared.rival_tier (те же пороги, что в fix.rivals). Новых спавнов нет: только веса
    уже существующих записей BIOME_GROUP.homeless spawns.
    Опасность биома d = средние combat stats членов бродячих отрядов биома (вес записи x число членов) по ванильным слоям
    (vanilla_mods; не зависит от модов и этого прохода); если ванильной массы < min_vanilla_mass, то по текущему состоянию.
    t = (d - safe_at)/(danger_at - safe_at) в [0,1]; биомы arms.relic_biomes («опасные краевые», носители реликтов) не ниже
    relic_biome_floor. Множитель тира: ломаная по t (0 / 0.5 / 1). keep_rival_mass: масса соперников в биоме (вес x размер)
    сохраняется, меняется не частота встреч, а кто встречается. Страховка faction_balance: если доля архетипа уходит за его
    коридор (cap/low), сила сдвига ослабляется (fb_guard_steps). Веса целые и часто = 1: чтобы выразить x0.4, все записи
    биома умножаются на общее целое Q <= max_upscale (относительные шансы прочих записей не меняются)."""
    import json as _j
    import sys as _sys
    _sys.path.insert(0, r"C:\KenshiModMap\tools\build")
    import budget
    import _shared
    import kmod as _km
    MAXI, cat = 2147483647, "homeless spawns"
    M = ctx.M
    RV = _j.load(open(r"C:\KenshiModMap\rules\streams\fix.json", encoding="utf-8"))["rivals"]
    tier = {}
    for sid in list(RV["prospectors"]) + list(RV["wanderers"]):
        sq = M.get(sid)
        if sq is None or sq.type_name != "SQUAD_TEMPLATE" or not ctx.in_game(sid):
            continue
        tr, pw = _shared.rival_tier(M, sq, RV["tiers"])
        if pw <= 0:   # статы не заданы: тир неизвестен, вес не трогаем
            s.report["rival_danger_skip_nostats:" + (sq.name or sid)] = 1
            continue
        tier[sid] = tr
    if fb:
        Mv = fb["Mv"]
    else:
        Mv, vm = {}, set(vanilla_mods)
        for _n, _m, _ in ctx.layers:
            if _n in vm:
                _km.apply(Mv, _m)
    D, TM, QR = RD["danger"], RD["tier_mult"], RD["quant"]

    def live(b):
        own = s.mb.items.get(b.sid)
        rm = {r.target: r for r in b.refs.get(cat, [])}
        for r in (own.refs.get(cat, []) if own else []):
            rm[r.target] = r
        return [r for r in rm.values() if 0 < r.v0 < MAXI]

    def mean_pw(Mx, refs):
        acc = w = 0.0
        for r in refs:
            sq = Mx.get(r.target)
            if sq is None or sq.type_name != "SQUAD_TEMPLATE":
                continue
            tot = n = 0
            for c in ("leader", "squad", "squad2"):
                for x in sq.refs.get(c, []):
                    ch = Mx.get(x.target)
                    if ch is None or ch.type_name != "CHARACTER" or (x.v0, x.v1, x.v2) == _km.DELETED_REF:
                        continue
                    k = 1 if c == "leader" else max(1, x.v0, x.v1)
                    tot += (ch.values.get("combat stats", 0) or 0) * k
                    n += k
            if n:
                acc += tot * r.v0
                w += r.v0 * n
        return (acc / w if w else None), w

    def mult(tr, t, a):
        p = TM[tr]
        m = p[0] + (p[1] - p[0]) * 2 * t if t < 0.5 else p[1] + (p[2] - p[1]) * (2 * t - 1)
        return 1 + a * (m - 1)

    def setw(b, r, nv):
        own = s.mb.items.get(b.sid)
        mine = [x for x in (own.refs.get(cat, []) if own else []) if x.target == r.target and 0 < x.v0 < MAXI]
        for x in mine:
            x.v0 = nv
        if not mine:
            s.change(b.sid, set_refs={cat: [Ref(r.target, nv, r.v1, r.v2)]})

    def band(t):
        return "safe" if t < 1 / 3 else ("danger" if t > 2 / 3 else "mid")

    for b in ctx.all("BIOME_GROUP"):
        rs = live(b)
        riv = [r for r in rs if r.target in tier]
        if not riv:
            continue
        vb = Mv.get(b.sid)
        d, wv = mean_pw(Mv, [r for r in (vb.refs.get(cat, []) if vb else []) if 0 < r.v0 < MAXI])
        if d is None or wv < D["min_vanilla_mass"]:
            d, _ = mean_pw(M, rs)
        t = 0.5 if d is None else min(1.0, max(0.0, (d - D["safe_at"]) / (D["danger_at"] - D["safe_at"])))
        if b.name in relic_biomes:
            t = max(t, D["relic_biome_floor"])
        s.report[f"rival_danger_t:{b.name}"] = round(t, 2)
        size = {r.target: budget.squad_size(M[r.target]) for r in riv}
        mass0 = sum(r.v0 * size[r.target] for r in riv)
        ref = fb_ref.get((b.sid, cat)) if fb else None
        f, why, sl = None, "", RD["fb_slack"]   # sl: допуск сдвига доли архетипа (абс.), когда она уже вне коридора faction_balance
        for a in RD["fb_guard_steps"]:
            if a <= 0:
                break
            fr = {r.target: r.v0 * mult(tier[r.target], t, a) for r in riv}
            if RD["keep_rival_mass"]:
                k = mass0 / max(1e-9, sum(fr[x] * size[x] for x in fr))
                fr = {x: v * k for x, v in fr.items()}
            if ref is not None:
                sh0 = fb["shares"](rs, M, fb["fc"], fb["uc"])
                sh1 = fb["shares"](rs, M, fb["fc"], fb["uc"], {r.target: fr.get(r.target, r.v0) for r in rs})
                bad = False
                for arch in set(sh0) | set(sh1):
                    x0, x1, rf = sh0.get(arch, 0.0), sh1.get(arch, 0.0), ref.get(arch, 0.0)
                    hi, lo = max(rf * (1 + fb["tol"]), fb["floor"]), rf * (1 - fb["tol"])
                    if x1 > max(hi, x0) + sl or (lo > 0.05 and x1 < min(lo, x0) - sl):
                        bad, why = True, f"{arch} {x0:.3f}->{x1:.3f} ref{rf:.3f}"
                        break
                if bad:
                    s.report["rival_danger_fb_softened"] += 1
                    continue
            f = fr
            break
        if f is None:
            s.report[f"rival_danger_fb_blocked:{b.name} t{t:.2f} ({why})"] = 1
            continue
        Q = 1
        for Q in range(1, int(QR["max_upscale"]) + 1):
            if all(abs(max(1, round(Q * v)) - Q * v) <= QR["tol"] * Q * v for v in f.values()):
                break
        new = {r.target: (max(1, int(round(Q * f[r.target]))) if r.target in f else r.v0 * Q) for r in rs}
        if all(new[r.target] == r.v0 for r in rs):
            continue
        sz = {r.target: (budget.squad_size(M[r.target]) if r.target in M and M[r.target].type_name == "SQUAD_TEMPLATE" else 1) for r in rs}
        bd = band(t)
        tw0, tw1 = sum(x.v0 * sz[x.target] for x in rs), sum(new[x.target] * sz[x.target] for x in rs)
        s.report[f"rival_danger_n_{bd}"] += 1
        for r in riv:
            tr = tier[r.target]
            s.report[f"rival_danger_share_{bd}_{tr}_before"] += r.v0 * size[r.target] / tw0
            s.report[f"rival_danger_share_{bd}_{tr}_after"] += new[r.target] * size[r.target] / tw1
        line = ", ".join(f"{(M[r.target].name or '').strip()}[{tier[r.target][0]}] {r.v0}->{new[r.target]}" for r in riv)
        s.report[f"rival_danger:{b.name} d{round(d) if d is not None else '?'} t{t:.2f} Q{Q}: {line}"] = 1
        for r in rs:
            if new[r.target] != r.v0:
                setw(b, r, new[r.target])
                s.report["rival_danger_entries_set"] += 1
        s.report["rival_danger_biomes"] += 1
        s.report["rival_danger_upscaled_biomes"] += Q > 1
