"""Поток E BEHAVIOR: пороги бегства бандитских фракций по ярусам лора (rules/streams/behavior.json).
Только повышение значений; coexistence не трогаем. Имя из правил, которого нет среди слабых фракций, — ошибка.
Семя пересборки (rules/world_seed.json): стартовые отношения фракций дрожат в рамках лора — сильная вражда/дружба
(|v| ≥ lock_abs) не трогается, остальные ±jitter у доли share пар; знак не меняется."""
import collections
import random
import re

from kmod import F32, Ref


def archetype_of(f, origin, wr):
    """Архетип фракции для world_relations (None — не участвует). origin — имя мода-источника."""
    n = f.name
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


def plan_world_relations(factions, origin, used, wr, cohab=frozenset()):
    """factions: список записей FACTION (в игре); origin: sid->мод; used: множество sid используемых фракций.
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
