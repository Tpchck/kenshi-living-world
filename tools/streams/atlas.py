"""Поток ATLAS: фракции у обитаемых локаций TOWN без фракции + отчёт по локациям (rules/streams/atlas.json).
Расстановка и координаты не трогаются. Пишет data/atlas_report.json."""
import collections
import json
import os
import re
import types
import zlib

import kmod
from kmod import Ref

ROOT = r"C:\KenshiModMap"
POP = ("residents", "roaming squads", "bar squads")


def build(ctx, s, rules):
    M = ctx.M
    fn = lambda sid: M[sid].name if sid in M else sid  # noqa: E731
    report = {"assigned": [], "skipped": [], "coverage_gaps": [], "notes": rules.get("notes", {})}

    def set_faction(t, fid, how):
        s.add_refs(t.sid, "faction", [Ref(fid, 0, 0, 0)])
        s.report["town_faction_set"] += 1
        report["assigned"].append({"sid": t.sid, "name": t.name, "faction": fn(fid), "how": how})

    for sid in rules["faction_from_squads"]["sids"]:
        t = M.get(sid)
        if t is None or t.type_name != "TOWN" or t.refs.get("faction"):
            s.report["town_skipped_missing_or_has_faction"] += 1
            continue
        votes = collections.Counter()
        for k in POP:
            for r in t.refs.get(k, []):
                q = M.get(r.target)
                if q is None:
                    continue
                for f in q.refs.get("faction", [])[:1]:
                    votes[f.target] += max(1, r.v0 if isinstance(r.v0, int) else 1)
        top = votes.most_common(2)
        if not top or (len(top) > 1 and top[0][1] == top[1][1]):
            report["skipped"].append({"sid": sid, "name": t.name, "why": "ничья/нет фракций у отрядов", "votes": [(fn(f), n) for f, n in top]})
            s.report["town_faction_ambiguous"] += 1
            continue
        set_faction(t, top[0][0], "squads %s" % [(fn(f), n) for f, n in top])

    base_of = collections.defaultdict(list)
    for t in ctx.all("TOWN"):
        for r in t.refs.get("override town", []):
            base_of[r.target].append(t)
    for sid in rules["faction_from_base"]["sids"]:
        t = M.get(sid)
        if t is None or t.type_name != "TOWN" or t.refs.get("faction"):
            s.report["town_skipped_missing_or_has_faction"] += 1
            continue
        fs = {b.refs["faction"][0].target for b in base_of.get(sid, []) if b.refs.get("faction")}
        if len(fs) != 1:
            report["skipped"].append({"sid": sid, "name": t.name, "why": "базовые города расходятся/нет базы", "bases": sorted(fn(f) for f in fs)})
            s.report["town_faction_ambiguous"] += 1
            continue
        set_faction(t, next(iter(fs)), "base town faction (ванильная практика руинных override)")

    # связь с дирижёром/складами: обитаемые не-override города с реальной фракцией, которых нет в conductor.json town_info
    try:
        ci = json.load(open(os.path.join(ROOT, "rules", "conductor.json"), encoding="utf-8")).get("town_info", {})
        variant = {r.target for t in ctx.all("TOWN") for r in t.refs.get("override town", [])}
        for t in ctx.all("TOWN"):
            if t.sid in variant or t.sid in ci or "(override)" in (t.name or "").lower():
                continue
            fr = t.refs.get("faction")
            if not fr or not sum(len(t.refs.get(k, [])) for k in POP):
                continue
            F = M.get(fr[0].target)
            if F is None or F.values.get("not real"):
                s.report["gap_unreal_faction"] += 1
                continue
            report["coverage_gaps"].append({"sid": t.sid, "name": t.name, "mod": ctx.origin.get(t.sid), "faction": F.name})
        s.report["coverage_gaps_real_faction"] = len(report["coverage_gaps"])
    except Exception as e:  # отчётная часть не должна ронять сборку
        report["coverage_error"] = repr(e)
    sh = rules.get("stronghold")
    if sh and sh.get("enabled"):
        try:
            report["stronghold"] = stronghold(ctx, s, sh)
        except Exception as e:  # оплоты не должны ронять остальные части потока
            report["stronghold"] = {"error": repr(e)}
            s.report["stronghold_error"] += 1
    tl = rules.get("townlife")
    if tl and tl.get("enabled"):
        try:
            report["townlife"] = townlife(ctx, s, tl)
        except Exception as e:  # жизнь города не должна ронять остальные части потока
            import traceback
            report["townlife"] = {"error": repr(e), "tb": traceback.format_exc()[-1500:]}
            s.report["townlife_error"] += 1
    json.dump(report, open(os.path.join(ROOT, "data", "atlas_report.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def _persons(ctx, sid):
    """Оценка числа персонажей в отряде-шаблоне: лидер + члены (v0 как число, если задано)."""
    q = ctx.M.get(sid)
    if q is None:
        return 1
    n = 0
    for cat in ("leader", "squad"):
        for r in q.refs.get(cat, []):
            n += max(1, r.v0) if isinstance(r.v0, int) and 0 < r.v0 < 50 else 1
    return max(1, n)


def _ai_names(ctx, q):
    return [ctx.M[r.target].name or "" for r in q.refs.get("AI packages", []) if r.target in ctx.M]


def stronghold(ctx, s, sh):
    """Оплоты: охрана и путники для крупных городов сильных фракций (см. _doc в rules/streams/atlas.json)."""
    M = ctx.M
    CITY = {2, 5, 6, 7}
    g_rx, g_ex = re.compile(sh["guard_ai_regex"], re.I), re.compile(sh["guard_ai_exclude"], re.I)
    fb_rx = re.compile(sh["fallback_bar_regex"], re.I)
    n_ex = re.compile(sh.get("guard_name_exclude") or "$^", re.I)
    is_guard = lambda q: not n_ex.search(q.name or "") and any(g_rx.search(a) and not g_ex.search(a) for a in _ai_names(ctx, q))  # noqa: E731
    variant = {r.target for t in ctx.all("TOWN") for r in t.refs.get("override town", [])}
    # исходное состояние TOWN (до потоков KMM): не конфликтовать с полями, уже изменёнными раньше (ECONOMY: семя residents, караваны)
    pri = {}
    for _, m, _ in ctx.layers:
        if m is not None:
            kmod.apply(pri, types.SimpleNamespace(items=[i for i in m.items if i.type_name == "TOWN"]))
    sig = lambda t, k: sorted((r.target, r.v0, r.v1, r.v2) for r in t.refs.get(k, []))  # noqa: E731
    touched = lambda t, k: (t.sid in pri) and sig(t, k) != sig(pri[t.sid], k)  # noqa: E731

    def rel(a, b):
        fa = M.get(a)
        if fa is None:
            return None
        for r in fa.refs.get("relations", []):
            if r.target == b and isinstance(r.v0, int):
                return r.v0
        return None

    def fac_defaults(fid):
        F = M.get(fid)
        return [(r.target, r.v0 if isinstance(r.v0, int) else 1, r.v1) for r in F.refs.get("residents", [])] if F else []

    def town_pop(t):
        """Оценка населения города: жители (+ умолчания фракции) + бары*шанс + roaming."""
        n = 0
        res = [(r.target, r.v0 if isinstance(r.v0, int) else 1) for r in t.refs.get("residents", [])]
        if not t.values.get("residents override") and t.refs.get("faction"):
            res += [(x[0], x[1]) for x in fac_defaults(t.refs["faction"][0].target)]
        for sid, c in res:
            n += max(1, c) * _persons(ctx, sid)
        for r in t.refs.get("bar squads", []):
            pct = r.v1 if isinstance(r.v1, int) else 100
            n += (r.v0 if isinstance(r.v0, int) and r.v0 > 0 else 1) * _persons(ctx, r.target) * min(100, max(0, pct)) / 100.0
        for r in t.refs.get("roaming squads", []):
            n += _persons(ctx, r.target)
        return n

    base_pop = sum(town_pop(t) for t in ctx.all("TOWN") if t.refs.get("faction") and t.sid not in variant and "(override)" not in (t.name or "").lower())
    rep = {"towns": [], "totals": {}}
    tot = collections.Counter()
    for t in sorted(ctx.all("TOWN"), key=lambda x: x.sid):
        if t.values.get("type") not in CITY or t.sid in variant or "(override)" in (t.name or "").lower() or not t.refs.get("faction"):
            continue
        fid = t.refs["faction"][0].target
        spec = sh["factions"].get(fid)
        if spec is None:
            continue
        typ = t.values.get("type")
        row = {"sid": t.sid, "name": t.name, "faction": spec["name"], "type": typ}
        own = [(r, M[r.target]) for r in t.refs.get("residents", []) if r.target in M and not ctx.origin.get(r.target, "").startswith("KMM") and is_guard(M[r.target])]
        dflt = [] if t.values.get("residents override") else [(x, M[x[0]]) for x in fac_defaults(fid) if x[0] in M and is_guard(M[x[0]])]
        base = sum(r.v0 if isinstance(r.v0, int) else 1 for r, _ in own) + sum(x[1] for x, _ in dflt)
        row["guards_before"] = base
        sets = {}
        add = 0
        gkey = None
        if base > 0:
            f = sh["factor"][str(typ)]
            add = min(sh["max_add_per_town"], max(1, round(base * (f - 1))))
            if not touched(t, "residents"):
                gkey = "residents"
                if own:
                    r, q = max(own, key=lambda x: (x[0].v0 if isinstance(x[0].v0, int) else 1))
                    sets["residents"] = [Ref(r.target, (r.v0 if isinstance(r.v0, int) else 1) + add, r.v1, r.v2)]
                    row["guard_how"] = "residents: %s %s->%s" % (q.name, r.v0, r.v0 + add)
                else:
                    x, q = max(dflt, key=lambda y: y[0][1])
                    sets["residents"] = [Ref(x[0], add, x[2] if isinstance(x[2], int) else 2, 0)]
                    row["guard_how"] = "residents: +%s %s (умолчание фракции)" % (add, q.name)
            else:
                cand = [q for _, q in own] + [q for _, q in dflt]
                cand = [q for q in cand if any(fb_rx.search(a) and not g_ex.search(a) for a in _ai_names(ctx, q)) and all(r.target != q.sid for r in t.refs.get("bar squads", []))]
                if cand and not touched(t, "bar squads"):
                    q = cand[0]
                    gkey = "bar squads"
                    sets["bar squads"] = [Ref(q.sid, add, 100, 0)]
                    row["guard_how"] = "bar squads (residents уже менял ECONOMY): +%s %s" % (add, q.name)
                else:
                    add = 0
                    row["guard_how"] = "пропуск: residents менял ECONOMY, запасного шаблона нет"
                    tot["guard_skipped_economy"] += 1
        else:
            row["guard_how"] = "нет охранных шаблонов у города/фракции"
            tot["guard_none"] += 1
        row["guards_added"] = add
        if gkey:
            tot["guards_added_squads"] += add
            tot["guard_persons"] += add * _persons(ctx, sets[gkey][0].target)
            tot["guard_towns"] += 1
            tot["guards_before"] += base
        # путники
        pool = sh["pools"].get(spec["pool"]) if spec.get("pool") else None
        row["travellers"] = []
        if sh.get("travellers_enabled", True) and pool and not touched(t, "roaming squads"):   # DIET: путники приходят через Traces arrive
            pop = sum(r.v0 if isinstance(r.v0, int) else 1 for r in t.refs.get("residents", []))
            n = 1
            for lo, k in sh["traveller_tiers"]:
                if pop >= lo:
                    n = k
            n = max(n, sh["traveller_min_for_type"].get(str(typ), 1))
            have = {r.target for r in t.refs.get("roaming squads", [])}
            h = zlib.crc32(t.sid.encode("utf-8"))
            got = []
            for i in range(len(pool)):
                if len(got) >= n:
                    break
                q = M.get(pool[(h + i) % len(pool)][2])
                if q is None or q.type_name != "SQUAD_TEMPLATE" or not ctx.in_game(q.sid) or q.sid in have or q.sid in got:
                    continue
                qf = q.refs.get("faction", [])
                if qf:
                    a, b = rel(qf[0].target, fid), rel(fid, qf[0].target)
                    if (a is not None and a < 0) or (b is not None and b < 0):
                        tot["traveller_hostile_skipped"] += 1
                        continue
                got.append(q.sid)
            if got:
                sets["roaming squads"] = [Ref(g, sh["traveller_roaming_v0"], 0, 0) for g in got]
                row["travellers"] = [M[g].name for g in got]
                tot["travellers_added"] += len(got)
                tot["traveller_persons"] += sum(_persons(ctx, g) for g in got)
                tot["traveller_towns"] += 1
        elif pool:
            row["travellers_skip"] = "roaming squads менял ECONOMY"
        if sets:
            s.change(t.sid, set_refs=sets)
        rep["towns"].append(row)
    add_persons = tot["guard_persons"] + tot["traveller_persons"]
    cap = base_pop * sh["world_growth_cap_pct"] / 100.0
    rep["totals"] = dict(tot)
    rep["totals"].update({"baseline_town_persons_est": round(base_pop), "added_persons_est": round(add_persons),
                          "growth_pct_of_town_population": round(100.0 * add_persons / base_pop, 2) if base_pop else None,
                          "cap_pct": sh["world_growth_cap_pct"], "within_cap": add_persons <= cap})
    s.report["stronghold_towns"] = len(rep["towns"])
    s.report["stronghold_guard_squads_added"] = tot["guards_added_squads"]
    s.report["stronghold_travellers_added"] = tot["travellers_added"]
    return rep


def townlife(ctx, s, tl):
    """TOWNLIFE: бары (калеки, дубли, разнообразие), постепенное заселение, имена, ротация лавок (см. rules/streams/atlas.json townlife)."""
    M = ctx.M
    rx = lambda k: re.compile(tl[k], re.I)  # noqa: E731
    r_amp, r_vis, r_rec, r_prot, r_roam = rx("amputee_regex"), rx("visitor_regex"), rx("recruit_regex"), rx("protect_regex"), rx("roaming_ai_regex")
    street = {n.lower() for n in tl["street_names"]}
    civ_rx = re.compile(tl["civ_regex"], re.I) if tl.get("civ_regex") else None   # DIET 2026-11-13: гражданский наполнитель
    seed = ctx.world_seed
    h = lambda *a: zlib.crc32(("|".join(str(x) for x in a) + "|%s" % seed).encode("utf-8"))  # noqa: E731
    hs = lambda *a: zlib.crc32("|".join(str(x) for x in a).encode("utf-8"))  # noqa: E731  # без семени: стабильный выбор
    variant = {r.target for t in ctx.all("TOWN") for r in t.refs.get("override town", [])}
    pri = {}
    for _, m, _ in ctx.layers:
        if m is not None:
            kmod.apply(pri, types.SimpleNamespace(items=[i for i in m.items if i.type_name == "TOWN"]))
    sig = lambda t, k: sorted((r.target, r.v0, r.v1, r.v2) for r in t.refs.get(k, []))  # noqa: E731
    touched = lambda t, k: (t.sid in pri) and sig(t, k) != sig(pri[t.sid], k)  # noqa: E731
    allt = [t for t in sorted(ctx.all("TOWN"), key=lambda x: x.sid) if not ctx.origin.get(t.sid, "").startswith("KMM")]
    isvar = lambda t: t.sid in variant or "(override)" in (t.name or "").lower()  # noqa: E731
    towns = [t for t in allt if not isvar(t)]   # базовые города: уникальные, фракционные пулы, roaming, лавки
    fid_of = lambda t: t.refs["faction"][0].target if t.refs.get("faction") else None  # noqa: E731

    def chars(q):
        return [M[r.target] for k in ("leader", "squad", "squad2", "choosefrom list") for r in q.refs.get(k, []) if r.target in M]

    def is_unique(q):
        return any(c.values.get("unique") for k in ("leader", "squad", "squad2") for r in q.refs.get(k, []) for c in [M.get(r.target)] if c is not None)

    def klass(q):
        nm = (q.name or "").strip()
        if q.values.get("is trader") or r_prot.search(nm) or q.type_name != "SQUAD_TEMPLATE":
            return "core"
        if r_amp.search(nm):
            return "amputee"
        if nm.lower() in street:
            return "street"
        if is_unique(q):
            return "unique"
        if q.refs.get("choosefrom list") and r_rec.search(nm):
            return "recruit"
        if r_vis.search(nm):
            return "visitor"
        return "other"

    cls = {}

    def K(sid):
        if sid not in cls:
            q = M.get(sid)
            cls[sid] = klass(q) if q is not None else "core"
        return cls[sid]

    rep = {}
    c0 = collections.Counter(); p0 = collections.Counter(); amp0 = collections.Counter()
    for t in allt:
        for r in t.refs.get("bar squads", []):
            k = K(r.target)
            n = (r.v0 if isinstance(r.v0, int) and r.v0 > 0 else 1) * (r.v1 if isinstance(r.v1, int) else 100) / 100.0
            c0[k] += n
            p0[k] += n * _persons(ctx, r.target)
            if k == "amputee":
                amp0[M[r.target].name] += n
    rep["bar_before_expected_squads"] = {k: round(v, 1) for k, v in c0.items()}
    rep["bar_before_expected_persons"] = {k: round(v) for k, v in p0.items()}
    rep["amputee_before_by_template"] = {k: round(v, 1) for k, v in amp0.items()}

    # ---------- уникальные рекруты: максимум unique_keep баров мира
    listing = collections.defaultdict(list)
    for t in towns:
        for r in t.refs.get("bar squads", []):
            if K(r.target) == "unique":
                listing[r.target].append(t)
    drop = collections.defaultdict(set)
    for sid, ts in listing.items():
        if len(ts) <= tl["unique_keep"]:
            continue
        qf = M[sid].refs.get("faction", [])
        qf = qf[0].target if qf else None
        ts2 = sorted(ts, key=lambda t: (0 if (qf and fid_of(t) == qf) else 1, hs(sid, t.sid)))
        for t in ts2[tl["unique_keep"]:]:
            if not touched(t, "bar squads"):
                drop[t.sid].add(sid)
    rep["unique_recruit_templates"] = len(listing)
    rep["unique_listings_before"] = sum(len(v) for v in listing.values())
    rep["unique_listings_dropped"] = sum(len(v) for v in drop.values())

    # ---------- частоты приходящих в мире (для балансировки)
    world_cnt = collections.Counter()
    fac_pool = collections.defaultdict(collections.Counter)
    for t in towns:
        for r in t.refs.get("bar squads", []):
            if K(r.target) in ("visitor", "recruit"):
                world_cnt[r.target] += 1
                fac_pool[fid_of(t)][r.target] += 1
    all_vis = sorted(world_cnt, key=lambda x: (world_cnt[x], hs(x)))

    tot_removed = 0.0
    roam_add = roam_persons = filled = trimmed = 0
    c1 = collections.Counter(); p1 = collections.Counter(); amp1 = collections.Counter()
    kept_types = collections.Counter()
    for t in allt:
        bars = {r.target: r for r in t.refs.get("bar squads", [])}
        if not bars:
            continue
        if touched(t, "bar squads"):
            for k, r in bars.items():
                n = (r.v0 if isinstance(r.v0, int) and r.v0 > 0 else 1) * (r.v1 if isinstance(r.v1, int) else 100) / 100.0
                c1[K(k)] += n; p1[K(k)] += n * _persons(ctx, k)
            continue
        sets, dels = [], set(drop.get(t.sid, ()))
        iv = isvar(t)
        big = t.values.get("type") in tl["big_town_types"] and not iv
        removed_persons = 0.0
        removed_vis = []
        cur = {k: (r.v0 if isinstance(r.v0, int) and r.v0 > 0 else 1, r.v1 if isinstance(r.v1, int) else 100) for k, r in bars.items()}
        amps = sorted([k for k in bars if K(k) == "amputee"], key=lambda k: (hs(t.sid, k), k))
        for k in amps[1:]:
            dels.add(k)
        if amps and cur[amps[0]][1] > tl["amputee_chance"]:
            sets.append(Ref(amps[0], 1, tl["amputee_chance"], bars[amps[0]].v2))
            cur[amps[0]] = (1, tl["amputee_chance"])
        for k in bars:
            c = K(k)
            n, pct = cur[k]
            if c == "other" and civ_rx and civ_rx.search(M[k].name or "") and tl.get("civ_bar_mult", 1) < 1:
                p2 = max(tl.get("civ_min_chance", 10), int(round(pct * tl["civ_bar_mult"])))
                if p2 < pct:
                    removed_persons += n * (pct - p2) / 100.0 * _persons(ctx, k)
                    sets.append(Ref(k, n, p2, bars[k].v2)); cur[k] = (n, p2)
            elif c == "street" and pct > tl["street_chance"]:
                sets.append(Ref(k, n, tl["street_chance"], bars[k].v2))
                cur[k] = (n, tl["street_chance"])
            elif c in ("visitor", "recruit"):
                n2, p2 = min(n, tl["visitor_cap"]), min(pct, tl["visitor_chance"])
                if (n2, p2) != (n, pct):
                    removed_persons += (n * pct - n2 * p2) / 100.0 * _persons(ctx, k)
                    removed_vis.append(k)
                    sets.append(Ref(k, n2, p2, bars[k].v2))
                    cur[k] = (n2, p2)
        vis = [k for k in bars if K(k) in ("visitor", "recruit") and k not in dels]
        if len(vis) > tl["visitor_types_max"]:
            vis_sorted = sorted(vis, key=lambda k: (-world_cnt[k], hs(t.sid, k)))
            for k in vis_sorted[:len(vis) - tl["visitor_types_max"]]:
                dels.add(k)
                removed_persons += cur[k][0] * cur[k][1] / 100.0 * _persons(ctx, k)
                removed_vis.append(k)
                trimmed += 1
            vis = [k for k in vis if k not in dels]
        added = []
        if len(vis) < tl["visitor_types_min"] and not iv and (big or len(bars) >= tl["min_bar_entries_for_fill"]):
            fp = fac_pool.get(fid_of(t)) or collections.Counter()
            cand = sorted([k for k in fp if k not in bars and ctx.in_game(k)], key=lambda k: (world_cnt[k], hs(t.sid, k)))
            if len(cand) < tl["visitor_types_min"] - len(vis):
                cand += [k for k in all_vis if k not in bars and k not in cand and ctx.in_game(k)]
            for k in cand[:tl["visitor_types_min"] - len(vis)]:
                sets.append(Ref(k, 1, tl["added_chance"], 0))
                cur[k] = (1, tl["added_chance"])
                vis.append(k); added.append(k)
                world_cnt[k] += 1
                filled += 1
        if big and removed_persons >= tl["roaming_min_removed_persons"] and not touched(t, "roaming squads"):
            have = {r.target for r in t.refs.get("roaming squads", [])}
            moved = 0
            for k in sorted(removed_vis, key=lambda k: (-world_cnt[k], hs(t.sid, k))):
                if moved >= tl["roaming_max"]:
                    break
                if k in have or k in dels or not any(r_roam.search(a) for a in _ai_names(ctx, M[k])):
                    continue
                s.add_refs(t.sid, "roaming squads", [Ref(k, tl["roaming_v0"], 0, 0)])
                moved += 1; roam_add += 1; roam_persons += _persons(ctx, k)
        tot_removed += removed_persons
        if sets:
            s.change(t.sid, set_refs={"bar squads": sets})
        if dels:
            s.change(t.sid, del_refs={"bar squads": sorted(dels)})
        if sets or dels:
            s.report["townlife_bar_towns"] += 1
        for k, (n, pct) in cur.items():
            if k in dels:
                continue
            c1[K(k)] += n * pct / 100.0; p1[K(k)] += n * pct / 100.0 * _persons(ctx, k)
            if K(k) == "amputee":
                amp1[M[k].name] += n * pct / 100.0
        kept_types[len([k for k in cur if k not in dels and K(k) in ("visitor", "recruit")])] += 1
    rep["bar_after_expected_squads"] = {k: round(v, 1) for k, v in c1.items()}
    rep["bar_after_expected_persons"] = {k: round(v) for k, v in p1.items()}
    rep["amputee_after_by_template"] = {k: round(v, 1) for k, v in amp1.items()}
    rep["visitor_types_per_bar_town_after"] = dict(sorted(kept_types.items()))
    rep["bar_trimmed_types"] = trimmed
    rep["bar_filled_types"] = filled
    rep["bar_removed_persons_est"] = round(tot_removed)
    rep["moved_to_roaming_squads"] = roam_add
    rep["moved_to_roaming_persons"] = roam_persons

    # ---------- имена: CHARACTER.named
    named_chars = set()
    for t in allt:
        for r in t.refs.get("bar squads", []):
            if K(r.target) in tl["named_for_classes"] and r.target in M:
                for c in chars(M[r.target]):
                    if c.type_name == "CHARACTER" and not c.values.get("unique") and not c.values.get("named") and not c.values.get("is trader") \
                            and not ctx.origin.get(c.sid, "").startswith("KMM") and ctx.in_game(c.sid):
                        named_chars.add(c.sid)
    for sid in sorted(named_chars):
        s.change(sid, values={"named": True})
    rep["named_set"] = len(named_chars)
    s.report["townlife_named"] = len(named_chars)

    # ---------- DIET (владелец 2026-11-13): города при загрузке полупустые, люди приходят (Traces arrive). Гражданские отряды-жители
    # фракций (FACTION.residents: «Civilian mongrel» x5 и т.п.) - val0 x civ_res_mult; охрана, лавки, уникальные, HQ не трогаются.
    diet = collections.Counter()
    if civ_rx and tl.get("civ_res_mult", 1) < 1:
        fids = sorted({fid_of(t) for t in towns if fid_of(t)})
        for fid in fids:
            F = M.get(fid)
            if F is None or ctx.origin.get(fid, "").startswith("KMM"):
                continue
            sets = []
            for r in F.refs.get("residents", []):
                q = M.get(r.target)
                if q is None or not isinstance(r.v0, int) or r.v0 <= 1 or r.v0 >= 1000 or K(r.target) != "other" or not civ_rx.search(q.name or ""):
                    continue
                n2 = max(1, int(round(r.v0 * tl["civ_res_mult"])))
                if n2 < r.v0:
                    sets.append(Ref(r.target, n2, r.v1, r.v2)); diet["faction_civ_squads_removed"] += r.v0 - n2
            if sets:
                s.change(fid, set_refs={"residents": sets}); diet["factions"] += 1
        for t in towns:
            if touched(t, "residents"):
                continue
            sets = []
            for r in t.refs.get("residents", []):
                q = M.get(r.target)
                if q is None or not isinstance(r.v0, int) or r.v0 <= 1 or r.v0 >= 1000 or K(r.target) != "other" or not civ_rx.search(q.name or ""):
                    continue
                n2 = max(1, int(round(r.v0 * tl["civ_res_mult"])))
                if n2 < r.v0:
                    sets.append(Ref(r.target, n2, r.v1, r.v2)); diet["town_civ_squads_removed"] += r.v0 - n2
            if sets:
                s.change(t.sid, set_refs={"residents": sets}); diet["towns"] += 1
    rep["diet"] = dict(diet)
    s.report["townlife_diet_civ_removed"] = diet["faction_civ_squads_removed"]

    rep["shops"] = shops_rotation(ctx, s, tl, towns, touched, h, fid_of, is_unique)
    return rep


def shops_rotation(ctx, s, tl, towns, touched, h, fid_of, is_unique):
    """Ротация лавок: замена торгового отряда на отряд той же фракции/здания/AI другой специализации + метрика долей по гильдиям."""
    M = ctx.M
    SPEC = (("weapons", r"weapon|crossbow|sword|gun|ammo"), ("armor", r"armo|clothing|hat|boot|footwear|cloth"),
            ("food", r"food|fish|bakery|bread|farm|hydro|narcot|brew"), ("tools/mats", r"tool|mats|construction|material|mechanic|machin|robot|trade goods"),
            ("medical", r"medic|surgeon"), ("books/loot", r"book|library|loot|junk"), ("bar", r"\bbar\b"))
    spec_rx = [(k, re.compile(v, re.I)) for k, v in SPEC]

    def spec(q):
        n = " ".join(M[r.target].name or "" for r in q.refs.get("vendors", []) if r.target in M) + " " + (q.name or "")
        for k, rx in spec_rx:
            if rx.search(n):
                return k
        return "misc"

    def shop_ok(q):
        return (q is not None and q.type_name == "SQUAD_TEMPLATE" and q.values.get("is trader") and not is_unique(q)
                and not q.refs.get("world state") and not ctx.origin.get(q.sid, "").startswith("KMM") and ctx.in_game(q.sid))

    def key(q):
        f = q.refs.get("faction")
        return (f[0].target if f else None, tuple(sorted(r.target for r in q.refs.get("building", []))),
                tuple(sorted((M[r.target].name or "") for r in q.refs.get("AI packages", []) if r.target in M)))

    def eff_shops(t):
        res = [(r.target, r.v0 if isinstance(r.v0, int) else 1) for r in t.refs.get("residents", [])]
        fid = fid_of(t)
        if not t.values.get("residents override") and fid and fid in M:
            res += [(r.target, r.v0 if isinstance(r.v0, int) else 1) for r in M[fid].refs.get("residents", [])]
        return [(sid, max(1, n)) for sid, n in res if shop_ok(M.get(sid))]

    def snapshot(over):
        g = collections.Counter(); sp = collections.Counter(); tot = 0
        for t in towns:
            for sid, n in eff_shops(t):
                sid = over.get((t.sid, sid), sid)
                q = M[sid]
                f = q.refs.get("faction", []) or t.refs.get("faction", [])
                fn = (M[f[0].target].name if f and f[0].target in M else "?")
                g[fn] += n; sp[spec(q)] += n; tot += n
        return g, sp, tot

    g0, sp0, tot0 = snapshot({})
    pool = collections.defaultdict(list)
    seen = set()
    for t in towns:
        for r in t.refs.get("residents", []):
            q = M.get(r.target)
            if shop_ok(q) and q.sid not in seen:
                seen.add(q.sid); pool[key(q)].append(q)
    gcount = collections.Counter()
    for t in towns:
        for sid, n in eff_shops(t):
            gcount[(key(M[sid])[0], spec(M[sid]))] += n
    over = {}
    swaps = skipped_touched = 0
    for t in sorted(towns, key=lambda x: h(x.sid)):
        mine = [r for r in t.refs.get("residents", []) if shop_ok(M.get(r.target))]
        if not mine:
            continue
        if touched(t, "residents"):
            skipped_touched += 1
            continue
        have = {r.target for r in t.refs.get("residents", [])}
        for r in mine:
            q = M[r.target]
            if (h(t.sid, q.sid) % 1000) / 1000.0 >= tl["swap_p"]:
                continue
            alts = [a for a in pool.get(key(q), []) if a.sid not in have and spec(a) != spec(q)]
            if not alts:
                continue
            alts.sort(key=lambda a: (gcount[(key(a)[0], spec(a))], h(t.sid, a.sid)))
            a = alts[0]
            gcount[(key(q)[0], spec(q))] -= 1
            gcount[(key(a)[0], spec(a))] += 1
            s.change(t.sid, set_refs={"residents": [Ref(a.sid, r.v0, r.v1, r.v2)]}, del_refs={"residents": [q.sid]})
            have.add(a.sid); have.discard(q.sid)
            over[(t.sid, q.sid)] = a.sid
            swaps += 1
    g1, sp1, tot1 = snapshot(over)
    pct = lambda c, tot: {k: round(100.0 * v / tot, 1) for k, v in c.most_common(12)}  # noqa: E731
    mx0, mx1 = max(pct(g0, tot0).values() or [0]), max(pct(g1, tot1).values() or [0])
    s.report["townlife_shop_swaps"] = swaps
    return {"nonunique_shops_est": tot0, "swaps": swaps, "towns_skipped_economy_residents": skipped_touched,
            "guild_share_pct_before": pct(g0, tot0), "guild_share_pct_after": pct(g1, tot1),
            "spec_share_pct_before": pct(sp0, tot0), "spec_share_pct_after": pct(sp1, tot1),
            "max_guild_pct_before": mx0, "max_guild_pct_after": mx1, "cap_pct": tl["monopoly_cap_pct"], "within_cap": mx1 <= tl["monopoly_cap_pct"],
            "pools_with_alternatives": sum(1 for v in pool.values() if len({spec(x) for x in v}) > 1)}
