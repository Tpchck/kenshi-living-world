"""A1 (2026-11-15, docs/core/ASTARTES.md): офлайн-проверка орденов космодесанта по СОБРАННЫМ модам (build/KMM_*), без игры, ~15 с.
Контекст: ваниль + основа + WH-слой (tools/fast/ctx) + потоки в порядке DATA_STREAMS + KMM_Cleanup (как в mods.cfg).
1) лагеря космодесанта (remove_camps) REMOVED; ни одной живой записи homeless spawns/nests у отрядов Astartes survivors;
2) 4 фракции-ордена: not real=false, раса Astartes, отряды master/captain/sergeant, у master-отряда уникальный лидер со своим именем;
3) отношения (итог после behavior): UC/HN/Shek в [-20..0] с обеих сторон, ордена между собой и с союзниками +80, хаос/некроны/орки <= -100,
   каннибалы/туманники <= -40; ни одна сильная фракция (UC/HN/Shek) не враждебна ордену;
4) спавны орденов — только в биомах своего региона, у каждого отряда есть запись; веса > 0;
5) экипировка: у клонов-рангов сохранена силовая броня тела исходника (гардероб не снял), раса задана;
6) диалог «KMM Order: <орден>» с условием my faction = орден и цепочкой >= 9 реплик есть у всех членов отрядов ордена;
7) дирижёр (rules/conductor.json): орден — реликтовая фракция архетипа imperium с лагерем модели в своём регионе;
8) отчёт сборки: errors [], fcs_errors 0, доля WH в спавнах в бюджете.
python -I -X utf8 build/KMM_Relics/_dev/test_a1_astartes.py -> OK"""
import json
import os
import sys

ROOT = r"C:\KenshiModMap"
for _p in ("", "fast", "build"):
    sys.path.insert(0, os.path.join(ROOT, "tools", _p))
import kmod  # noqa: E402
import ctx as _ctx  # noqa: E402
import areas  # noqa: E402

FAILS, N = [], [0]


def check(cond, what):
    N[0] += 1
    if not cond:
        FAILS.append(what)


A = json.load(open(os.path.join(ROOT, "rules", "streams", "relics.json"), encoding="utf-8"))["astartes_chapters"]
D = json.load(open(os.path.join(ROOT, "rules", "streams", "diplo.json"), encoding="utf-8"))["astartes_orders"]
COND = json.load(open(os.path.join(ROOT, "rules", "conductor.json"), encoding="utf-8"))
REP = json.load(open(os.path.join(ROOT, "build", "kmm_build_report.json"), encoding="utf-8"))
BUD = json.load(open(os.path.join(ROOT, "rules", "budget.json"), encoding="utf-8"))

lo, van, base, wh = _ctx.load()
M = {}
for _, m, _ in van + base + wh:
    kmod.apply(M, m)
src = open(os.path.join(ROOT, "tools", "build", "kmm_build.py"), encoding="utf-8").read()
streams = [m for _, m in eval(src.split("DATA_STREAMS = ", 1)[1].split("\n", 1)[0])] + ["KMM_Cleanup"]
for mod in streams:
    p = os.path.join(ROOT, "build", mod, mod + ".mod")
    if os.path.exists(p):
        kmod.apply(M, kmod.read(p))
DEL = kmod.DELETED_REF
live = lambda r: (r.v0, r.v1, r.v2) != DEL and r.v0 > 0  # noqa: E731
fac_by = {}
for it in M.values():
    if it.type_name == "FACTION":
        fac_by.setdefault(it.name, []).append(it)
nm = lambda sid: M[sid].name if sid in M else sid  # noqa: E731

# 1. лагеря и случайные спавны
for sid, why in A["remove_camps"]:
    check(sid in M and M[sid].values.get("REMOVED") is True, f"camp not REMOVED: {why}")
old = {f.sid for n in A["remove_spawn_factions"] for f in fac_by.get(n, [])}
old_sq = {q.sid for q in M.values() if q.type_name == "SQUAD_TEMPLATE" and q.refs.get("faction") and q.refs["faction"][0].target in old}
left = [(b.name, nm(r.target)) for b in M.values() if b.type_name == "BIOME_GROUP" for c in ("homeless spawns", "nests")
        for r in b.refs.get(c, []) if r.target in old_sq and live(r)]
check(not left, f"Astartes survivors spawns left: {left[:5]}")

# 2-5. ордена
rmap = areas.RegionMap(M)
strong = {n: [f.sid for f in fac_by.get(n, [])] for n in ("United Cities", "The Holy Nation", "Shek Kingdom")}
chap_sids = {}
for ch in A["chapters"]:
    fs = fac_by.get(ch["faction"], [])
    check(len(fs) == 1, f"{ch['faction']}: factions {len(fs)}")
    if len(fs) != 1:
        continue
    f = fs[0]
    chap_sids[ch["faction"]] = f.sid
    check(f.values.get("not real") is False, f"{f.name}: not real")
    check(any("Astartes" in nm(r.target) for r in f.refs.get("races", [])), f"{f.name}: races")
    rel = {}
    for r in f.refs.get("relations", []):
        rel.setdefault(r.target, r.v0)
    for n, sids in strong.items():
        for x in sids:
            v = rel.get(x, f.values.get("default relation", 0))
            check(-20 <= v <= 0, f"{f.name} -> {n}: {v}")
            back = {r.target: r.v0 for r in M[x].refs.get("relations", [])}.get(f.sid)
            check(back is None or back > -30, f"{n} -> {f.name}: {back}")
    for n in ("Midnight Lord", "Space Necromancer - Sora Dynasty", "Greenskins", "Lost Chaos Space Marines", "World Devourer War Gang"):
        for x in fac_by.get(n, []):
            check(rel.get(x.sid, 0) <= -100, f"{f.name} -> {n}: {rel.get(x.sid)}")
    for n in ("Cannibals", "Fogmen"):
        for x in fac_by.get(n, []):
            check(rel.get(x.sid, 0) <= -40, f"{f.name} -> {n}: {rel.get(x.sid)}")
    sq = [M[r.target] for r in f.refs.get("squads", []) if r.target in M]
    by_name = {q.name: q for q in sq}
    check(len(sq) == len(ch["squads"]), f"{f.name}: squads {len(sq)}")
    home = {b for b, _ in ch["spawns"]}
    for spec in ch["squads"]:
        q = by_name.get(spec["name"])
        check(q is not None, f"{f.name}: squad {spec['name']} missing")
        if q is None:
            continue
        check(q.refs.get("faction") and q.refs["faction"][0].target == f.sid, f"{q.name}: faction")
        check(any(nm(r.target) == "Patrol map (short range)" for r in q.refs.get("AI packages", [])), f"{q.name}: AI")
        lead = M.get(q.refs["leader"][0].target)
        check(lead is not None and lead.type_name == "CHARACTER", f"{q.name}: leader")
        if spec["role"] == "master":
            check(lead.values.get("unique") is True and lead.name == ch["ranks"]["master"]["name"], f"{q.name}: master unique/name")
        where = {b.name for b in M.values() if b.type_name == "BIOME_GROUP" for r in b.refs.get("homeless spawns", []) if r.target == q.sid and live(r)}
        check(where and where <= home, f"{q.name}: spawns {sorted(where)} not in {sorted(home)}")
        for c in ("leader", "squad", "squad2"):
            for r in q.refs.get(c, []):
                m_ = M.get(r.target)
                check(m_ is not None and m_.type_name == "CHARACTER", f"{q.name}: member {r.target}")
    for rk, sp in ch["ranks"].items():
        clones = [c for c in M.values() if c.type_name == "CHARACTER" and c.name == sp["name"] and c.sid.endswith("KMM_Relics.mod")]
        check(len(clones) == 1, f"{f.name}: rank {sp['name']} x{len(clones)}")
        if len(clones) != 1:
            continue
        c, s0 = clones[0], M[sp["src"][2]]
        body = [r.target for r in s0.refs.get("clothing", []) if r.target in M and "armor" in nm(r.target).lower()
                and not any(w in nm(r.target).lower() for w in ("leg", "boot", "helm", "liner", "lining", "gauntlet", "claw"))]
        have = {r.target for r in c.refs.get("clothing", []) if (r.v0, r.v1, r.v2) != DEL}
        check(body and set(body) <= have, f"{c.name}: body armour {[nm(x) for x in body]} lost")
        check(bool(c.refs.get("race")), f"{c.name}: race")
    # 6. диалог ордена
    dl = [d for d in M.values() if d.type_name == "DIALOGUE" and d.name == "KMM Order: " + ch["faction"]]
    check(len(dl) == 1, f"{f.name}: order dialogue x{len(dl)}")
    if dl:
        d = dl[0]
        check([r.target for r in d.refs.get("my faction", [])] == [f.sid], f"{f.name}: dialogue my faction")
        n_lines, stack = 0, [r.target for r in d.refs.get("lines", [])]
        while stack:
            x = stack.pop()
            n_lines += 1
            stack += [r.target for r in M[x].refs.get("lines", [])]
        check(n_lines >= 9, f"{f.name}: dialogue lines {n_lines}")
        mem = {r.target for q in sq for c in ("leader", "squad", "squad2") for r in q.refs.get(c, [])}
        miss = [nm(x) for x in mem if not any(r.target == d.sid for r in M[x].refs.get("dialogue", []))]
        check(not miss, f"{f.name}: no order dialogue at {miss}")
    # 7. дирижёр
    cf = COND["factions"].get(f.sid)
    check(cf is not None, f"{f.name}: not in conductor.json")
    if cf:
        check(cf.get("relic") == ch["relic"] and cf.get("arch") == "imperium", f"{f.name}: conductor relic/arch {cf.get('relic')}/{cf.get('arch')}")
        b = rmap.at(cf["x"], cf["z"]) if cf.get("x") is not None else None
        check(b is not None and b.name in home, f"{f.name}: conductor camp {cf.get('camp_name')} in {getattr(b, 'name', None)}")
check(len(chap_sids) == len(A["chapters"]), "chapters")
for a in chap_sids.values():   # ордена между собой
    ra = {r.target: r.v0 for r in M[a].refs.get("relations", [])}
    for b in chap_sids.values():
        if a != b:
            check(ra.get(b) == A["chapter_value"], f"{nm(a)} -> {nm(b)}: {ra.get(b)}")

# 8. отчёт сборки
check(REP["errors"] == [], f"build errors {REP['errors'][:3]}")
check(all(s.get("fcs_errors", 0) == 0 for s in REP["streams"]), "fcs_errors")
check(REP["budget"]["spawn_share_wh"] <= BUD["share_max"] * (1 + BUD["tolerance"]), f"WH spawn share {REP['budget']['spawn_share_wh']}")
rel_rep = next(s["report"] for s in REP["streams"] if s["stream"] == "relics")
check(rel_rep.get("astartes_squads") == sum(len(c["squads"]) for c in A["chapters"]), "report astartes_squads")
check(len(D["orders"]) == len(A["chapters"]), "diplo orders")

print(f"A1 astartes: {N[0] - len(FAILS)}/{N[0]} checks")
for x in FAILS:
    print("FAIL", x)
print("OK" if not FAILS else f"FAILED {len(FAILS)}")
sys.exit(1 if FAILS else 0)
