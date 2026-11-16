"""Поток BUILD: порядок в меню построек игрока и единое дерево исследований (docs/BUILD_TREE.md, rules/streams/build.json).

Меню игрока (данные ✓, механика движка по коду BuildModeWindow/Research::isBuildingResearched): постройка видна, если её
открывает достижимое исследование (RESEARCH.enable buildings); пункт меню = (building category, building group).
Записи не удаляются. Рычаги только ванильные:
  - дубль скрывается снятием ссылки из enable buildings (города, лагеря, сейвы ссылаются на sid постройки — он цел);
  - почти-дубли сводятся в один пункт родной группой building group (варианты листаются стрелками);
  - исследование-пустышка прячется флагом blueprint only;
  - уровни исследований только поднимаются (ступени), реликтовые модовые технологии встают за Relic Studies (KMM_Tech).
Анализ (World) общий для генератора и теста tools/streams/test_build_menu.py."""
import collections
import re

from kmod import Ref

UI_FIELDS = ("building category", "building group")


# --------------------------------------------------------------------------------------------- анализ поверх M
def is_vanilla(origin, rules):
    return origin in set(rules["vanilla_files"])


def family(sid, origin, rules):
    o = origin.get(sid, "")
    return "vanilla" if is_vanilla(o, rules) else o


def layout_writers(layers, rx):
    """sid постройки -> {поле: True}, если последний писатель поля building category/group — мод раскладки (BCT)."""
    rxc = re.compile(rx)
    last = {}
    for n, m, _ in layers:
        if m is None:
            continue
        for it in m.items:
            if it.type_name == "BUILDING":
                for k in UI_FIELDS:
                    if k in it.values:
                        last.setdefault(it.sid, {})[k] = n
    return {sid: {k: bool(rxc.search(n)) for k, n in d.items()} for sid, d in last.items()}


def research_state(M, rules, in_game):
    """(R, start, bp, reach): исследования в игре без REMOVED, стартовые, с источником чертежа, достижимые."""
    R = {sid: it for sid, it in M.items() if it.type_name == "RESEARCH" and in_game(sid) and it.values.get("REMOVED") is not True}
    start = {x for x in rules["start_research"] if x in R}
    src = {tuple(x) for x in rules["blueprint_sources"]}
    bp = set()
    for it in M.values():
        for (t, cat) in src:
            if it.type_name == t:
                bp.update(r.target for r in it.refs.get(cat, []) if r.target in R)
    return R, start, bp


def reachable(R, start, bp, bp_only, reqs):
    """bp_only(sid)->bool, reqs(sid)->[sid]. Достижимо: доступно само (не blueprint only / есть чертёж / старт) и все предпосылки достижимы."""
    memo = {}

    def go(k, stack):
        if k in memo:
            return memo[k]
        if k not in R or k in stack:
            return False
        ok = (k in start or k in bp or not bp_only(k)) and all(go(q, stack | {k}) for q in reqs(k))
        memo[k] = ok
        return ok
    return {k for k in R if go(k, frozenset())}


def fsig(M, fsid, ignore=()):
    f = M.get(fsid)
    if f is None:
        return ("?", fsid)
    vals = tuple(sorted((k, str(v)) for k, v in f.values.items() if k not in ignore))
    refs = tuple(sorted((k, tuple(sorted((r.target, r.v0, r.v1, r.v2) for r in v))) for k, v in f.refs.items() if v))
    return (vals, refs)


def _t(it, cat):
    return tuple(sorted(r.target for r in it.refs.get(cat, [])))


def clone_sig(M, it, rules):
    """Точный клон: совпадает всё, кроме имени, описания, раскладки меню и цены постройки (clone.ignore_*);
    функция сравнивается по содержимому BUILDING_FUNCTIONALITY."""
    c = rules["clone"]
    iv, ir = set(c["ignore_values"]), set(c["ignore_refs"])
    vals = tuple(sorted((k, str(v)) for k, v in it.values.items() if k not in iv))
    refs = tuple(sorted((k, tuple(sorted((r.target, r.v0, r.v1, r.v2) for r in v))) for k, v in it.refs.items()
                        if v and k not in ir and k != "functionality"))
    inst = tuple(sorted((i.target, tuple(round(x, 2) for x in i.pos), tuple(round(x, 3) for x in i.rot)) for i in it.instances))
    return (tuple(sorted(fsig(M, r.target) for r in it.refs.get("functionality", []))), vals, refs, inst)


def functions(M, it):
    return {M[r.target].values.get("function") for r in it.refs.get("functionality", []) if r.target in M}


def fold_key(M, it, rules):
    """Ключ почти-дубля. Рабочая постройка (функция из fold.functions, ферма, турель, генератор/батарея):
    функция без меша; склад с лимитом — только «что хранит» (размер и вместимость — варианты); остальное (декор,
    свет, сиденья, столы, общие сундуки) — набор мешей."""
    f = rules["fold"]
    v = it.values
    fn = functions(M, it)
    lim = _t(it, "limit inventory")
    if lim and fn <= {2}:
        return ("S", lim, str(v.get("itemtype limit")))
    if (fn & set(f["functions"])) or it.refs.get("farm data") or it.refs.get("gun turret")             or (v.get("power output") or 0) > 0 or (v.get("power capacity") or 0) > 0:
        ign = set(f["function_ignore_values"])
        return ("F", tuple(sorted(fsig(M, r.target, ign) for r in it.refs.get("functionality", []))),
                tuple(_t(it, k) for k in f["functional_refs"]), tuple(str(v.get(k)) for k in f["functional_values"]))
    parts = _t(it, "parts")
    return ("M", parts) if parts else None


def common_name(names):
    """Общее начало имён вариантов: «Staff (Mk I)», «Staff (Edge Type 2)» -> «Staff»."""
    p = names[0]
    for n in names[1:]:
        while not n.startswith(p):
            p = p[:-1]
    p = p.rstrip(" ([:-_").strip()
    return p if len(p) >= 3 else ""


def entry(it):
    g = it.values.get("building group") or ""
    return (it.values.get("building category", "misc"), g if g else "#" + it.sid)


def canon_key(it, origin, rules, locked, lo_index):
    o = origin.get(it.sid, "")
    lk = locked.get(it.sid, {})
    return (0 if is_vanilla(o, rules) else 1, 0 if any(lk.values()) else 1, lo_index.get(o, 10 ** 6), it.sid)


def has_content(it, enables):
    if enables:
        return True
    return any(v for k, v in it.refs.items() if (k.startswith("enable") and k != "enable buildings") or k == "improve buildings")


# --------------------------------------------------------------------------------------------- генератор
def build(ctx, s, rules):
    M, origin = ctx.M, ctx.origin
    van = set(rules["vanilla_files"])
    lo_index = {n: i for i, (n, _, _) in enumerate(ctx.layers)}
    locked = layout_writers(ctx.layers, rules["layout_mods_rx"])
    R, start, bp = research_state(M, rules, ctx.in_game)
    B = {sid: it for sid, it in M.items() if it.type_name == "BUILDING" and ctx.in_game(sid)}
    rep = s.report

    # рабочее состояние
    en = {r: {x.target for x in it.refs.get("enable buildings", []) if x.target in B} for r, it in R.items()}
    lvl = {r: int(it.values.get("level", 1)) for r, it in R.items()}
    req = {r: [x.target for x in it.refs.get("requirements", []) if x.target in R] for r, it in R.items()}
    bp_only = {r: it.values.get("blueprint only") is True for r, it in R.items()}
    vals = collections.defaultdict(dict)     # r -> новые значения
    add_req = collections.defaultdict(list)

    # --- R3: is level upgrade только у ванильных Tech Level
    for r, it in sorted(R.items()):
        if it.values.get("is level upgrade") is True and origin.get(r) not in van:
            vals[r]["is level upgrade"] = False
            rep["levelup_flag_removed"] += 1

    # --- R4: реликтовые модовые технологии
    RL = rules["relic"]
    anchor = None
    for sid, it in R.items():
        if it.name == RL["anchor"][1] and origin.get(sid) == RL["anchor"][2]:
            anchor = sid
    if anchor is None:
        raise KeyError("BUILD: опора реликтов Relic Studies (KMM_Tech) не найдена — поток tech должен идти раньше")
    rx = re.compile(RL["category_rx"])
    relic = {r for r, it in R.items() if origin.get(r) != RL["anchor"][2]
             and (origin.get(r) in set(RL["mods"]) or rx.search(str(it.values.get("category", ""))))}
    for r in sorted(relic):
        it = R[r]
        if lvl[r] < RL["level"]:
            lvl[r] = RL["level"]
        if it.values.get("category") != RL["category"]:
            vals[r]["category"] = RL["category"]
        if not any(q in relic or q == anchor for q in req[r]):
            add_req[r].append(anchor)
            req[r].append(anchor)
            rep["relic_rooted"] += 1
        if not it.refs.get("cost") and not it.values.get("money"):
            vals[r]["money"] = RL["free_money"]
            s.add_refs(r, "cost", [Ref(sid, n, 0, 0) for sid, n in RL["free_cost"]])
            rep["relic_priced"] += 1
        rep["relic_research"] += 1

    # --- R5: чужие технологии
    AL = rules["alien"]
    for r in sorted(R):
        if origin.get(r) in set(AL["mods"]) and lvl[r] < AL["min_level"]:
            lvl[r] = AL["min_level"]
            rep["alien_raised"] += 1

    reach = reachable(R, start, bp, lambda k: bp_only[k], lambda k: req[k])

    def menu():
        m = collections.defaultdict(set)
        for r in reach:
            for b in en[r]:
                m[b].add(r)
        return m

    # --- D1: точные клоны
    vis = menu()
    up_targets = {u.target for b in vis for u in B[b].refs.get("upgrades to", [])}
    groups = collections.defaultdict(list)
    for b in vis:
        groups[clone_sig(M, B[b], rules)].append(b)
    hidden = set()
    for sig_, bs in sorted(groups.items(), key=lambda kv: min(kv[1])):
        if len(bs) < 2:
            continue
        bs.sort(key=lambda b: canon_key(B[b], origin, rules, locked, lo_index))
        c = bs[0]
        for h in bs[1:]:
            if h in up_targets:
                rep["clone_kept_upgrade_target"] += 1
                continue
            for r in vis[h]:
                en[r].discard(h)
                en[r].add(c)
            hidden.add(h)
            rep["clone_hidden"] += 1

    # --- R1: одна постройка — одно исследование (между семействами)
    def avail_key(r, b):
        return (0 if r in start else 1, 0 if r in start else lvl[r],
                0 if family(r, origin, rules) == family(b, origin, rules) else 1,
                0 if family(r, origin, rules) == "vanilla" else 1, r)
    vis = menu()
    for b in sorted(vis):
        rs = vis[b]
        if len({family(r, origin, rules) for r in rs}) < 2:
            continue
        keep = min(rs, key=lambda r: avail_key(r, b))
        fk = family(keep, origin, rules)
        for r in rs:
            if family(r, origin, rules) != fk:
                en[r].discard(b)
                rep["dedupe_research_ref"] += 1

    # --- R6: предпосылки (уровни только вверх)
    PR = rules["prereq"]
    for _ in range(20):
        changed = 0
        vis = menu()

        def avail(b):
            return min((0 if r in start else lvl[r]) for r in vis[b])
        if PR.get("power"):
            gens = [avail(b) for b in vis if (B[b].values.get("power output") or 0) > 0]
            gl = min(gens) if gens else 99
            for b in sorted(vis):
                if (B[b].values.get("power output") or 0) < 0:
                    for r in sorted(vis[b]):
                        if r not in start and lvl[r] < gl:
                            lvl[r] = gl
                            changed += 1
                            rep["power_raised"] += 1
        if PR.get("upgrades"):
            for a in sorted(vis):
                for u in B[a].refs.get("upgrades to", []):
                    if u.target in vis and avail(u.target) < avail(a):
                        need = avail(a)
                        for r in sorted(vis[u.target]):
                            if r not in start and lvl[r] < need:
                                lvl[r] = need
                                changed += 1
                                rep["upgrade_raised"] += 1
        for r in sorted(R):
            m = max([lvl[q] for q in req[r]] or [0])
            if lvl[r] < m:
                lvl[r] = m
                changed += 1
                rep["mono_raised"] += 1
        if not changed:
            break

    # --- R2: тупики
    required = {q for r in reach for q in req[r]}
    for r in sorted(reach):
        it = R[r]
        if r in start or vals[r].get("is level upgrade", it.values.get("is level upgrade")) is True or r in required:
            continue
        if has_content(it, en[r]):
            continue
        if r in bp:
            rep["dead_research_blueprint_sold"] += 1
            continue
        vals[r]["blueprint only"] = True
        rep["dead_research_hidden"] += 1

    # --- категории и группы (только незакреплённые раскладкой поля)
    bcat = {b: it.values.get("building category", "misc") for b, it in B.items()}
    bgrp = {b: it.values.get("building group") or "" for b, it in B.items()}
    cmap = rules["categories"]["map"]
    vis = menu()
    for b in sorted(vis):
        if not locked.get(b, {}).get("building category") and bcat[b] in cmap:
            bcat[b] = cmap[bcat[b]]
            rep["category_mapped"] += 1

    skip = set(rules["fold"]["skip_categories"])
    classes = collections.defaultdict(list)
    for b in vis:
        if bcat[b] in skip:
            continue
        k = fold_key(M, B[b], rules)
        if k is not None:
            classes[k].append(b)
    lc = lambda b: locked.get(b, {}).get("building category", False)   # noqa: E731
    lg = lambda b: locked.get(b, {}).get("building group", False)      # noqa: E731
    for k, bs in sorted(classes.items(), key=lambda kv: min(kv[1])):
        if len({(bcat[b], bgrp[b] or "#" + b) for b in bs}) < 2:
            continue
        rep["fold_classes"] += 1
        bs.sort(key=lambda b: canon_key(B[b], origin, rules, locked, lo_index))
        # категория пункта: закреплённая раскладкой (канон среди закреплённых), иначе категория канона
        cl = [b for b in bs if lc(b)]
        tc = bcat[cl[0]] if cl else bcat[bs[0]]
        # 2026-11-16 (playtest: plain raw-meat Campfire vanished from CAMPING): a vanilla canon keeps its own category;
        # a furniture layout mod (Cattrina's "Cozy Campfire") must not drag the vanilla building away
        if is_vanilla(origin.get(bs[0], ""), rules):
            tc = bcat[bs[0]]
        if len({bcat[b] for b in cl}) > 1:
            rep["fold_layout_exception"] += 1        # раскладка BCT держит дубль в двух категориях
        for b in bs:
            if not lc(b) and bcat[b] != tc:
                bcat[b] = tc
                rep["fold_moved_category"] += 1
        # группа внутри каждой категории: закреплённая непустая группа, иначе группа/имя канона категории
        for c in sorted({bcat[b] for b in bs}):
            mem = [b for b in bs if bcat[b] == c]
            gl = [b for b in mem if lg(b) and bgrp[b]]
            if gl:
                tg = bgrp[gl[0]]
            else:
                head = next((b for b in mem if not lg(b)), None)
                if head is None:
                    continue
                tg = bgrp[head]
                ms = set(mem)
                taken = lambda g: any(x not in ms and bcat[x] == c and bgrp[x] == g for x in vis)   # noqa: E731
                cn = common_name(sorted(B[x].name for x in mem))
                if not tg or taken(tg) or (cn and cn.lower() not in tg.lower()):   # группа канона чужая — пункт по общему имени
                    tg = cn or B[head].name
                    if taken(tg):
                        tg = B[head].name
            for b in mem:
                if not lg(b) and bgrp[b] != tg:
                    bgrp[b] = tg
                    rep["fold_moved_group"] += 1

    # --- запись дельт -----------------------------------------------------------------------------------------
    for r, it in sorted(R.items()):
        old = {x.target for x in it.refs.get("enable buildings", []) if x.target in B}
        added, removed = sorted(en[r] - old), sorted(old - en[r])
        v = dict(vals.get(r, {}))
        if lvl[r] != int(it.values.get("level", 1)):
            v["level"] = lvl[r]
            rep["research_level_changed"] += 1
        sr = {}
        if added:
            sr["enable buildings"] = [Ref(b, 0, 0, 0) for b in added]
        if add_req.get(r):
            sr["requirements"] = [Ref(q, 0, 0, 0) for q in add_req[r]]
        if v or sr or removed:
            s.change(r, values=v or None, set_refs=sr or None, del_refs={"enable buildings": removed} if removed else None)
    for b, it in sorted(B.items()):
        v = {}
        if bcat[b] != it.values.get("building category", "misc"):
            v["building category"] = bcat[b]
        if bgrp[b] != (it.values.get("building group") or ""):
            v["building group"] = bgrp[b]
        if v:
            s.change(b, values=v)
            rep["building_ui_changed"] += 1
    rep["menu_buildings_before"] = len({b for r in reach for x in R[r].refs.get("enable buildings", []) for b in [x.target] if b in B})
    rep["menu_buildings_after"] = len(menu())
