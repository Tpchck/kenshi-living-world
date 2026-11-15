"""Поток E BEHAVIOR: пороги бегства бандитских фракций по ярусам лора (rules/streams/behavior.json).
Только повышение значений; coexistence не трогаем. Имя из правил, которого нет среди слабых фракций, — ошибка.
Семя пересборки (rules/world_seed.json): стартовые отношения фракций дрожат в рамках лора — сильная вражда/дружба
(|v| ≥ lock_abs) не трогается, остальные ±jitter у доли share пар; знак не меняется."""
import collections
import json
import os
import random
import re

from kmod import F32, Ref


_CULTURE = None
CULTURE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "rules", "culture.json")


def culture():
    """rules/culture.json (B4 И12): явные архетипы/амбиции/отношения фракций и выравнивание двойников. Нет файла — пусто."""
    global _CULTURE
    if _CULTURE is None:
        try:
            _CULTURE = json.load(open(CULTURE_PATH, encoding="utf-8"))
        except FileNotFoundError:
            _CULTURE = {}
    return _CULTURE


def archetype_of(f, origin, wr):
    """Архетип фракции для world_relations (None — не участвует). origin — имя мода-источника.
    Порядок: rules/culture.json factions[имя].archetype > override_by_name > archetype_by_name > regex > ftype."""
    n = f.name
    ca = (culture().get("factions", {}).get(n) or {}).get("archetype")
    if ca:
        return ca
    if n in wr["override_by_name"]:
        return wr["override_by_name"][n]
    for a, names in wr["archetype_by_name"].items():
        if n in names:
            return a
    for a, rx in wr["archetype_regex"]:
        if re.search(rx, n):
            return a
    if f.values.get("not real"):
        return None
    return wr["type_fallback"].get(str(f.values.get("fundamental type", 4)), "settler")


def cohab_pairs(ctx):
    """2026-11-14 баг Mongrel: пары фракций, живущих в одном городе по данным (хозяин TOWN + фракции отрядов residents /
    bar squads / default resident). Матрица не дописывает им вражду: иначе стража, лавки и бары воюют между собой."""
    M = ctx.M
    out = set()
    for t in ctx.all("TOWN"):
        if not ctx.in_game(t.sid):
            continue
        own = {x.target for x in t.refs.get("faction", [])}
        facs = set(own)
        for cat in ("residents", "bar squads", "default resident"):
            for x in t.refs.get(cat, []):
                sq = M.get(x.target)
                if sq is not None and sq.values.get("is trader"):   # лавки и бармены; пленники в клетках и захватчики — не соседи
                    fs = {y.target for y in sq.refs.get("faction", [])}
                    facs.update(fs or own)
        for a in facs:
            for b in facs:
                if a != b:
                    out.add((a, b))
    return out


def plan_world_relations(factions, origin, used, wr, cohab=frozenset(), cult=None):
    """factions: список записей FACTION (в игре); origin: sid->мод; used: множество sid используемых фракций.
    cult — rules/culture.json (None — читается файл): vs_archetype/vs_name как исключения, only_vs — без матрицы.
    Возвращает ({sid: {target_sid: значение}}, статистика). Только добавления и исправления противоречий."""
    arch = {}
    for f in factions:
        if f.sid in used:
            a = archetype_of(f, origin, wr)
            if a and a not in wr["skip_archetypes"] and f.values.get("fundamental type", 4) != 0:
                arch[f.sid] = a
    core = set(wr["core_origins"])
    mat = {}
    for k, v in wr["matrix"].items():
        a, b = k.split("|")
        mat[(a, b)] = mat[(b, a)] = v
    byname = collections.defaultdict(list)
    for f in factions:
        byname[f.name].append(f.sid)
    exc = {}
    force = set()  # исключения с 4-м элементом "force": выставляются точно, даже при совпадении знака
    for a, b, v, *fl in wr["exceptions"]:
        for x in byname.get(a, []):
            for y in byname.get(b, []):
                if x != y:
                    exc[(x, y)] = exc[(y, x)] = v
                    if fl and fl[0] == "force":
                        force.add((x, y))
                        force.add((y, x))
    fac = {f.sid: f for f in factions}
    # паспорт культуры: исключения по архетипу/имени для конкретной фракции (явные exceptions behavior.json важнее)
    cf = (culture() if cult is None else cult).get("factions", {})
    only_vs = set()
    for x in sorted(arch):
        spec = cf.get(fac[x].name)
        if not spec:
            continue
        if spec.get("only_vs"):
            only_vs.add(x)
        for y in sorted(arch):
            if y == x or (x, y) in exc:
                continue
            v = (spec.get("vs_name") or {}).get(fac[y].name)
            if v is None:
                v = (spec.get("vs_archetype") or {}).get(arch[y])
            if v is not None:
                exc[(x, y)] = exc[(y, x)] = v
    plan = collections.defaultdict(dict)
    st = collections.Counter()
    delta = wr["min_delta"]

    def apply(x, y, m, is_exc):
        fx = fac[x]
        if (x, y) in cohab and m < 0 and not is_exc:   # соседи по городу: вражду матрицей не дописываем
            st["cohab_skip"] += 1
            st[f"cohab_skip:{fx.name} -> {fac[y].name} ({m})"] += 1
            return None
        if (x, y) in cohab and m <= -40 and is_exc:
            st["cohab_hostile_exception"] += 1
        explicit = {r.target: r.v0 for r in fx.refs.get("relations", []) if isinstance(r.v0, int)}
        dflt = fx.values.get("default relation", 0)
        dflt = dflt if isinstance(dflt, (int, float)) else 0
        if y not in explicit:
            if is_exc or abs(m - dflt) >= delta:
                plan[x][y] = m
                return "added"
            return None
        v = explicit[y]
        both_core = origin.get(x, "") in core and origin.get(y, "") in core
        if is_exc:
            if (x, y) in force and v != m:
                plan[x][y] = m
                return "fixed"
            if (v > 0) != (m > 0) and v != m and (v != 0 or m != 0):
                plan[x][y] = m
                return "fixed"
        elif not both_core and ((m <= -40 and v > -10) or (m >= 40 and v <= -40)):
            plan[x][y] = m
            return "fixed"
        return None

    sids = sorted(arch)
    for i, x in enumerate(sids):
        for y in sids[i + 1:]:
            e = exc.get((x, y))
            if e is None and (x in only_vs or y in only_vs):
                continue
            m = e if e is not None else mat.get((arch[x], arch[y]))
            if m is None:
                continue
            for p, q in ((x, y), (y, x)):
                r = apply(p, q, m, e is not None)
                if r:
                    st[f"{r}:{min(arch[p], arch[q])}|{max(arch[p], arch[q])}"] += 1
                    st[r] += 1
    st["participants"] = len(arch)
    return plan, st, arch


def twin_groups(ctx):
    """Двойники: фракции в игре (не KMM_*) с одним именем. [(канон, [двойники])], канон как в fix.faction_merge:
    ваниль > больше ссылок из не-FACTION записей > реальная."""
    van = {n for n, _, _ in ctx.van}
    creator = lambda sid: sid.split("-", 1)[1] if "-" in sid else sid  # noqa: E731
    groups = collections.defaultdict(list)
    for f in ctx.all("FACTION"):
        if not creator(f.sid).startswith("KMM_") and (f.name or "").strip():
            groups[f.name.strip()].append(f)
    groups = {n: fs for n, fs in groups.items() if len(fs) > 1}
    if not groups:
        return []
    want = {f.sid for fs in groups.values() for f in fs}
    cnt = collections.Counter()
    for it in ctx.M.values():
        if it.type_name == "FACTION" or not ctx.in_game(it.sid):
            continue
        for xs in it.refs.values():
            for x in xs:
                if x.target in want:
                    cnt[x.target] += 1
    out = []
    for n, fs in sorted(groups.items()):
        canon = max(fs, key=lambda f: (creator(f.sid) in van, cnt[f.sid], not f.values.get("not real", False), f.sid))
        out.append((canon, sorted((f for f in fs if f.sid != canon.sid), key=lambda f: f.sid)))
    return out


def align_twins(ctx, s, plan, TW, min_delta):
    """TWINS (B4 Н4, rules/culture.json twins): политика двойника = политика канона. Пишет в plan (дальше общий путь с дрожанием
    семени) и default relation двойника (значение FACTION, других писателей нет)."""
    if not TW.get("enabled"):
        return
    M = ctx.M
    skip = set(TW.get("skip_names", []))
    facs = ctx.all("FACTION")
    expl = {f.sid: {r.target: r.v0 for r in f.refs.get("relations", []) if isinstance(r.v0, int)} for f in facs}

    def dflt(f):
        v = f.values.get("default relation", 0)
        return v if isinstance(v, (int, float)) else 0

    def rel(a, b):
        if b in plan.get(a, {}):
            return plan[a][b]
        return expl.get(a, {}).get(b)

    def put(a, b, v):
        cur = rel(a, b)
        if cur is None:
            cur = dflt(M[a])
        if cur != v and (abs(cur - v) >= min_delta or (cur > 0) != (v > 0)):
            plan.setdefault(a, {})[b] = v
            return 1
        return 0

    for canon, twins in twin_groups(ctx):
        if canon.name.strip() in skip:
            continue
        c = canon.sid
        for tw in twins:
            t = tw.sid
            n = 0
            for y in sorted(set(expl.get(c, {})) | set(plan.get(c, {}))):
                if y in (t, c) or y not in M or M[y].type_name != "FACTION" or not ctx.in_game(y):
                    continue
                n += put(t, y, rel(c, y))
            for y in sorted(set(expl.get(t, {})) - set(expl.get(c, {})) - set(plan.get(c, {}))):   # своя дружба/вражда двойника, которой нет у канона
                if y not in (t, c) and y in M and M[y].type_name == "FACTION" and ctx.in_game(y):
                    n += put(t, y, dflt(canon))
            for f in facs:
                y = f.sid
                if y in (t, c):
                    continue
                v = rel(y, c)
                if v is None and rel(y, t) is not None:   # к канону отношения нет, к двойнику есть — как к канону: по умолчанию
                    v = dflt(f)
                if v is not None:
                    n += put(y, t, v)
            cv = TW.get("twin_canon_value", 100)
            n += put(t, c, cv) + put(c, t, cv)
            if dflt(tw) != dflt(canon):
                s.change(t, values={"default relation": canon.values.get("default relation", 0)})
                s.report["twins_default_relation"] += 1
            s.report["twins_pairs"] += n
            s.report["twins:" + canon.name.strip() + " <- " + t.split("-", 1)[-1]] = n


def build(ctx, s, rules):
    weak = {f.name: f for f in ctx.all("FACTION")
            if f.values.get("fundamental type") == rules["weak_fundamental_type"] and not f.values.get("not real", False)}
    tier_of = {}
    for tier, spec in rules["tiers"].items():
        for n in spec["factions"]:
            if n not in weak:
                raise KeyError(f"behavior: фракция {n!r} из яруса {tier} не найдена среди слабых (OT_BANDIT)")
            if n in tier_of:
                raise KeyError(f"behavior: фракция {n!r} в двух ярусах ({tier_of[n]}, {tier})")
            tier_of[n] = tier
    for n, f in weak.items():
        tier = tier_of.get(n, rules["default_tier"])
        vals = rules["tiers"][tier]["values"]
        s.report[f"tier:{tier}"] += 1
        if vals and s.raise_values(f.sid, {k: F32(v) for k, v in vals.items()}):
            s.report[f"changed:{tier}"] += 1

    # --- единый мир: архетипная матрица (до дрожания семени) -------------------------------------------------------
    wr = rules.get("world_relations")
    plan = {}
    if wr:
        used = set()
        for t in ctx.M.values():
            if t.type_name in ("SQUAD_TEMPLATE", "TOWN") and ctx.in_game(t.sid):
                used.update(r.target for r in t.refs.get("faction", []))
        cohab = cohab_pairs(ctx)
        s.report["world:cohab_pairs"] += len(cohab) // 2
        plan, st, _ = plan_world_relations(ctx.all("FACTION"), ctx.origin, used, wr, cohab)
        for k, v in sorted(st.items()):
            s.report[f"world:{k}"] += v
        align_twins(ctx, s, plan, culture().get("twins") or {}, wr["min_delta"])

    # --- семя пересборки: стартовые отношения в рамках лора ------------------------------------------------------
    ws = ctx.world_seed_rules["relations"]
    rng = random.Random(ctx.world_seed)
    for f in sorted(ctx.all("FACTION"), key=lambda x: x.sid):
        if f.values.get("not real") and f.sid not in plan:
            continue
        orig = {r.target: r for r in f.refs.get("relations", [])}
        mine = plan.get(f.sid, {})
        if not orig and not mine:
            continue
        new = []
        seen = set()
        for r in list(f.refs.get("relations", [])) + [Ref(t, v, 0, 0) for t, v in mine.items() if t not in orig]:
            seen.add(r.target)
            v = r.v0
            if r.target in mine:
                nv = mine[r.target]
                if r.target in orig:
                    s.report["world_fixed_pairs"] += 1
                else:
                    s.report["world_added_pairs"] += 1
                if v == nv and r.target in orig:
                    continue
                v = nv
                if abs(v) < ws["lock_abs"] and rng.random() <= ws["share"] and r.target in ctx.M:
                    v2 = v + rng.randint(-ws["jitter"], ws["jitter"])
                    if (v2 > 0) == (v > 0) or v2 == 0 and v == 0:
                        v = max(-100, min(100, v2))
                new.append(Ref(r.target, v, r.v1, r.v2))
                continue
            if f.values.get("not real") or not isinstance(v, int) or abs(v) >= ws["lock_abs"] or r.target not in ctx.M or rng.random() > ws["share"]:
                continue
            nv = v + rng.randint(-ws["jitter"], ws["jitter"])
            if v != 0 and (nv > 0) != (v > 0):
                nv = v // abs(v)
            if nv != v:
                new.append(Ref(r.target, nv, r.v1, r.v2))
                s.report["seed_relations_changed"] += 1
        if new:
            s.change(f.sid, set_refs={"relations": new})
    s.report["world_seed"] = ctx.world_seed
