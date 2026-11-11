"""Бюджет происхождения (DESIGN.md «Доля божественного»): доля WH/реликтового в мире ≤ rules/budget.json.

spawn_share(ctx)   — доля NPC WH-фракций в спавнах биомов (homeless spawns: вес × размер отряда)
item_share(...)    — доля вещей «Империум / Хаос / ксенос / реликт T3» в выдачах гардероба и у торговцев
Генератор (kmm_build.py) вызывает check() после сборки: превышение → ошибка, факт — в отчёт.
"""
import json
import os
import re

ROOT = r"C:\KenshiModMap"
RULES = json.load(open(os.path.join(ROOT, "rules", "budget.json"), encoding="utf-8"))
WH_MODS = set(RULES["wh_mods"])


def wh_factions(ctx):
    """Фракции, созданные WH-модами или нашими KMM_* (остатки Империума)."""
    out = set()
    for n, m, _ in ctx.layers:
        if n in WH_MODS:
            out |= {it.sid for it in m.items if it.type_name == "FACTION" and it.change == 0}
    out |= {sid for sid, it in ctx.M.items() if it.type_name == "FACTION" and re.search(r"-KMM_\w+\.mod$", sid)}
    return out


def squad_size(sq):
    return max(1, sum(max(r.v0, r.v1) for c in ("leader", "squad", "squad2") for r in sq.refs.get(c, [])))


def spawn_share(ctx):
    whf = wh_factions(ctx)
    total = wh = 0.0
    for b in ctx.M.values():
        if b.type_name != "BIOME_GROUP":
            continue
        for r in b.refs.get("homeless spawns", []):
            sq = ctx.M.get(r.target)
            if sq is None or (r.v0, r.v1, r.v2) == (2147483647,) * 3:
                continue
            w = max(0, r.v0) * squad_size(sq)
            total += w
            if sq.refs.get("faction") and sq.refs["faction"][0].target in whf:
                wh += w
    return wh / total if total else 0.0, whf


def is_exotic(x):
    """WH-происхождение или реликт (T3 без ванильной культуры). Должно совпадать с wardrobe.is_exotic."""
    return x["origin"] in ("imperial", "chaos", "xenos") or (x["tier"] == "T3" and not x["origin"].startswith("culture:"))


def check(ctx, wardrobe_report):
    sh, _ = spawn_share(ctx)
    res = {"spawn_share_wh": round(sh, 4), "spawn_max": RULES["share_max"],
           "item_share_exotic": wardrobe_report.get("exotic_share"), "item_max": RULES["share_max"],
           "exotic_at_own_factions": wardrobe_report.get("exotic_own_share")}
    errs = []
    if sh > RULES["share_max"] * (1 + RULES["tolerance"]):
        errs.append(f"БЮДЖЕТ: доля NPC WH-фракций в спавнах {sh:.2%} > {RULES['share_max']:.0%}")
    ish = wardrobe_report.get("exotic_share")
    if ish is not None and ish > RULES["share_max"] * (1 + RULES["tolerance"]):
        errs.append(f"БЮДЖЕТ: доля экзотики в выдачах гардероба/торговцев {ish:.2%} > {RULES['share_max']:.0%}")
    return res, errs
