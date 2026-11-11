"""Поток C ECONOMY (rules/streams/economy.json):
- money_by_role — деньги NPC по ролям (поля money min/max существующих CHARACTER); трофеи — в WARDROBE;
- thieves — воры ходят между городами (второй AI-пакет), контрабандисты скупают краденое;
- caravans — караваны гильдии/ульев выходят из торговых городов (TOWN roaming squads);
- vendor_turnover — торговцы обновляют ассортимент чаще.
- items — ITEMS-блок: цены предметов (кроме брони/оружия/патронов), цены записок/книг, мёртвые предметы в списки торговцев по тематике, дубли в пулах (tools/streams/_items.py, rules items).
Владение: CHARACTER, торговые/воровские/караванные SQUAD_TEMPLATE, TOWN, VENDOR_LIST, ITEMS_CULTURE (DECISIONS.md)."""
import re
import struct

from kmod import F32, Ref
from _shared import money_norm, role_of
import _items

f32 = lambda v: struct.unpack("<f", struct.pack("<f", v))[0]  # noqa: E731


def _money(ctx, s, rules):
    """Деньги по ролям (поля money min/max). Трофеи бандитов (поле clothing) — в WARDROBE (DECISIONS 2026-11-11)."""
    for it in ctx.all("CHARACTER"):
        if re.search(r"-KMM_\w+\.mod$", it.sid):  # новые записи других потоков — не наши
            continue
        vals = money_norm(it)  # нормы — tools/streams/_shared.py
        if vals:
            s.change(it.sid, values=vals)
            s.report[f"money:{role_of(it)}"] += 1


def _items_block(ctx, s, rules):
    import collections
    import json
    import os
    R = rules["items"]
    rows = [r for r in _items.build_rows(ctx) if not r["sid"].endswith(".mod") or "-KMM_" not in r["sid"]]
    byid = {r["sid"]: r for r in rows}
    bad_assets = {}
    ap = r"C:\KenshiModMap\data\items_audit.json"
    if os.path.exists(ap):
        for x in json.load(open(ap, encoding="utf-8"))["items"]:
            bad_assets[x["sid"]] = bool(x.get("missing_assets"))
    wh = set(json.load(open(r"C:\KenshiModMap\rules\budget.json", encoding="utf-8"))["wh_mods"])
    skip_g, skip_n = set(R["skip_groups"]), re.compile(R["skip_name_rx"], re.I)
    O, B = R["outlier"], R["books"]
    rare = re.compile(O["rare_rx"], re.I)
    lo_skip = re.compile(O["lo_skip_rx"], re.I)
    sc = _items.vanilla_scales(rows)
    newval = {}

    def txt(r):
        return r["text"]

    # 1) пустые цены книг/записок
    tiers = [(t["id"], re.compile(t["rx"], re.I), t["value"]) for t in B["tiers"]]
    keep0 = re.compile(B["keep_zero_rx"], re.I)
    for r in rows:
        if r["group"] != "book" or r["value"] > 0 or r["quest"] or keep0.search(r["name"]) or skip_n.search(r["name"]):
            continue
        if r["vanilla"] and not any(x in B["vanilla_value0_refs"] for x in (k.split("=")[0] for k in r["refs"])):
            continue
        for tid, rx, val in tiers:
            if rx.search(r["name"] + " " + r["text"][len(r["name"]):160]):
                newval[r["sid"]] = val
                s.report["price_book_new:" + ("vanilla_" if r["vanilla"] else "") + tid] += 1
                break
    # 2) выбросы модов относительно ванильной шкалы группы
    for r in rows:
        g, sv = r["group"], sc.get(r["group"])
        if r["vanilla"] or r["quest"] or g in skip_g or r["value"] <= 0 or not sv or sv["n"] < O["min_vanilla_n"] or skip_n.search(r["name"]):
            continue
        ratio = r["vw"] / sv["med_vw"] if sv["med_vw"] else None
        if ratio is None:
            continue
        if r["value"] > sv["p90"] * O["hi_trigger_p90"] and ratio > O["hi_trigger_ratio"]:
            k = O["hi_factor_rare"] if (r["mod"] in wh or rare.search(r["name"])) else O["hi_factor"]
            nv = int(round(sv["p90"] * k, -1))
            if nv < r["value"]:
                newval[r["sid"]] = nv
                s.report["price_outlier_hi:" + g] += 1
        elif g in O["lo_groups"] and not lo_skip.search(r["name"]) and r["value"] < sv["p10"] * O["lo_trigger_p10"] and ratio < O["lo_trigger_ratio"]:
            newval[r["sid"]] = int(sv["p10"])
            s.report["price_outlier_lo:" + g] += 1
    examples = []
    for sid, nv in newval.items():
        s.change(sid, values={"value": nv})
        if len(examples) < 14:
            examples.append(f"{byid[sid]['name'][:28]} [{byid[sid]['mod'][:16]}]: {byid[sid]['value']} -> {nv}")
    s.report["price_changed_total"] = len(newval)
    s.report["price_examples"] = examples

    # 3) мёртвые предметы -> списки торговцев по тематике
    I = R["intro"]
    dref = tuple(I["default_ref"])
    themes = [(t, re.compile(t["rx"], re.I)) for t in I["themes"]]
    cat_of = {"container": "containers", "map": "maps"}
    fill = collections.Counter()
    vlcache = {}

    def vl_by_name(n):
        if n not in vlcache:
            hits = [v for v in ctx.all("VENDOR_LIST") if v.name == n]
            vlcache[n] = sorted(hits, key=lambda v: v.sid)[0] if hits else None
            if not hits:
                s.report["intro_missing_list:" + n] += 1
        return vlcache[n]

    placed = {}
    cands = sorted((r for r in rows if r["dead"] and not r["quest"]), key=lambda r: r["sid"])
    seen = set()
    for r in cands:
        if r["sid"] in seen:
            continue
        seen.add(r["sid"])
        val = newval.get(r["sid"], r["value"])
        if r["vanilla"] or val <= 0 or not r["icon"] or bad_assets.get(r["sid"]) or skip_n.search(r["name"]) or keep0.search(r["name"]):
            continue
        for t, rx in themes:
            if r["group"] in t["groups"] and rx.search(r["text"]):
                lists = t["lists"]
                vl = vl_by_name(lists[sum(map(ord, r["sid"])) % len(lists)])
                if vl is None or fill[vl.sid] >= t["cap"]:
                    break
                cat = cat_of.get(r["group"], "items")
                s.add_refs(vl.sid, cat, [Ref(r["sid"], *dref)])
                fill[vl.sid] += 1
                s.report["intro:" + t["id"]] += 1
                placed[r["sid"]] = vl.name
                break
    s.report["intro_total"] = len(placed)
    s.report["intro_examples"] = [f"{byid[k]['name'][:30]} [{byid[k]['mod'][:14]}] -> {v}" for k, v in list(placed.items())[:14]]

    # 4) дубли: худший заменяется лучшим в пулах торговцев/лута
    D = R["dups"]
    by = collections.defaultdict(list)
    for r in rows:
        n = _items.norm_name(r["name"])
        if r["group"] in D["groups"] and len(n) >= D["min_name_len"]:
            by[(r["group"], n)].append(r)
    nref = lambda r: len(r["refs"])  # noqa: E731
    swap = {}
    for k, v in by.items():
        if len(v) < 2 or any(x["quest"] for x in v):
            continue
        best = min(v, key=lambda x: (not x["vanilla"], bool(bad_assets.get(x["sid"])), not x["icon"], -nref(x), x["sid"]))
        for x in v:
            if x["sid"] != best["sid"] and not x["vanilla"] and (bad_assets.get(x["sid"]) or not x["icon"] or best["vanilla"]):
                swap[x["sid"]] = best["sid"]
    done = collections.Counter()
    for vl in ctx.all("VENDOR_LIST"):
        for cat in ("items", "containers"):
            have = {x.target for x in vl.refs.get(cat, [])}
            for x in vl.refs.get(cat, []):
                b = swap.get(x.target)
                if b is None or "-KMM_" in vl.sid:
                    continue
                s.change(vl.sid, del_refs={cat: [x.target]})
                if b not in have:
                    s.add_refs(vl.sid, cat, [Ref(b, x.v0, x.v1, x.v2)])
                    have.add(b)
                done[cat] += 1
    s.report["dup_pool_swaps"] = sum(done.values())
    s.report["dup_pairs"] = len(swap)


def build(ctx, s, rules):
    _money(ctx, s, rules)
    _items_block(ctx, s, rules)
    changed_squads = {}  # sid -> (values, refs): одна дельта на отряд

    def squad_delta(sid):
        return changed_squads.setdefault(sid, ({}, {}))

    # воры: второй AI-пакет «между городами»
    th = rules["thieves"]
    pkg = ctx.find(*th["travel_package"])
    for spec in th["travel_squads"]:
        q = ctx.find(*spec)
        if all(r.target != pkg.sid for r in q.refs.get("AI packages", [])):
            squad_delta(q.sid)[1].setdefault("AI packages", []).append(Ref(pkg.sid, th["travel_priority"], 0, 0))
            s.report["thieves_travel"] += 1
    for spec in th["fences"]["squads"]:
        q = ctx.find(*spec)
        vals = {k: v for k, v in th["fences"]["values"].items() if q.values.get(k) != v}
        if vals:
            squad_delta(q.sid)[0].update(vals)
            s.report["fences"] += 1

    # оборот торговцев
    vt = rules["vendor_turnover"]
    for q in ctx.all("SQUAD_TEMPLATE"):
        if q.values.get("is trader") and f32(float(q.values.get("vendors refresh time", 24.0))) >= f32(vt["from_hours"]):
            squad_delta(q.sid)[0]["vendors refresh time"] = F32(vt["to_hours"])
            s.report["vendor_refresh_faster"] += 1

    for sid, (vals, refs) in changed_squads.items():
        s.change(sid, values=vals, set_refs=refs)

    # караваны из торговых городов
    for spec in rules["caravans"]["roaming"]:
        q = ctx.find(*spec["squad"])
        for town in spec["towns"]:
            t = ctx.find("TOWN", town)
            if all(r.target != q.sid for r in t.refs.get("roaming squads", [])):
                s.add_refs(t.sid, "roaming squads", [Ref(q.sid, spec["weight"], 0, 0)])
                s.report["caravan_town_entries"] += 1


def seed_towns(ctx, s):
    """Семя пересборки (rules/world_seed.json): варианты гарнизонов — число жителей-отрядов городов ±jitter у доли share."""
    import random
    from kmod import Ref
    ws = ctx.world_seed_rules["towns"]
    rng = random.Random(ctx.world_seed * 7 + 1)
    variant = {r.target for t in ctx.all("TOWN") for r in t.refs.get("override town", [])}
    for t in sorted(ctx.all("TOWN"), key=lambda x: x.sid):
        if t.sid in variant or not t.refs.get("residents"):
            continue
        new = []
        for r in t.refs["residents"]:
            if isinstance(r.v0, int) and r.v0 >= ws["min_residents"] and r.target in ctx.M and rng.random() < ws["share"]:
                nv = max(1, r.v0 + rng.randint(-ws["residents_jitter"], ws["residents_jitter"]))
                if nv != r.v0:
                    new.append(Ref(r.target, nv, r.v1, r.v2))
        if new:
            s.change(t.sid, set_refs={"residents": new})
            s.report["seed_town_residents_changed"] += len(new)


_build_core = build


def build(ctx, s, rules):   # noqa: F811 — основная сборка потока + семя пересборки для гарнизонов
    _build_core(ctx, s, rules)
    seed_towns(ctx, s)
