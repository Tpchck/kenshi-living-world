"""Генерация KMM_Glue.mod по rules/glue_rules.json поверх слитого контекста (ваниль → основа → WH).

python -I -X utf8 tools/fast/gen_glue.py [--install]
  → build/KMM_Glue/KMM_Glue.mod (+ отчёт out/glue_report.json); --install копирует в Kenshi/mods/KMM_Glue/.
"""
import collections
import json
import os
import re
import shutil
import struct
import sys

sys.path.insert(0, r"C:\KenshiModMap\tools")
sys.path.insert(0, r"C:\KenshiModMap\tools\fast")
import ctx  # noqa: E402
import fcsdef  # noqa: E402
import kmod  # noqa: E402
from kmod import F32, Ref  # noqa: E402

KENSHI = r"C:\Program Files (x86)\Steam\steamapps\common\Kenshi"
NAME = "KMM_Glue"
BUILD = rf"C:\KenshiModMap\build\{NAME}"
RULES = json.load(open(r"C:\KenshiModMap\rules\glue_rules.json", encoding="utf-8"))

lo, van, base, wh = ctx.load()
layers = van + base + wh
M = {}
for _, m, _ in layers:
    kmod.apply(M, m)
origin = {}  # sid -> файл, где запись появилась
for n, m, _ in layers:
    for it in m.items:
        origin.setdefault(it.sid, n)

# Записи, которые игра отбрасывает (TEST_V0: «Item X modified by KMM_Glue does not exist»), не трогаем.
# Источник — лог реального запуска: rules/game_rejected_sids.json (правило «sid чужого незагруженного мода»
# оказалось слишком широким: 663 против 275 реально отвергнутых).
REJECTED = set(json.load(open(r"C:/KenshiModMap/rules/game_rejected_sids.json", encoding="utf-8"))["sids"])


def in_game(sid):
    return sid not in REJECTED


report_skip = collections.Counter()
idx = collections.defaultdict(list)
for it in M.values():
    idx[(it.type_name, it.name)].append(it)


def find(tname, name, sid=None):
    if sid:
        it = M.get(sid)
        if it is None or it.type_name != tname:
            raise KeyError(f"{tname} {sid} не найден")
        return it
    hits = idx.get((tname, name), [])
    if len(hits) != 1:
        raise KeyError(f"{tname} {name!r}: найдено {len(hits)} (нужно ровно 1)")
    return hits[0]


mb = kmod.ModBuilder(f"{NAME}.mod", M, author="KMM",
                     description="KMM glue: cats by role, weak avoid strong, WH squads in world, T0 gear. Load last.")
report = collections.Counter()
f32 = lambda v: struct.unpack("<f", struct.pack("<f", v))[0]  # noqa: E731


def add_refs(sid, cat, refs):
    """Добавить ссылки, которых ещё нет у записи (или у уже созданной новой записи)."""
    cur = mb.items.get(sid)
    have = {r.target for r in M[sid].refs.get(cat, [])} if sid in M else set()
    if cur is not None and cur.change == kmod.CHANGE_NEW:
        cur.refs.setdefault(cat, []).extend(r for r in refs if r.target not in {x.target for x in cur.refs.get(cat, [])})
        return
    new = [r for r in refs if r.target not in have]
    if new:
        mb.change(sid, set_refs={cat: new})


# 1) каты по ролям ---------------------------------------------------------------
mr = RULES["money_by_role"]
skip = [s.lower() for s in mr["skip_name_contains"]]
for it in [i for i in M.values() if i.type_name == "CHARACTER"]:
    if not in_game(it.sid):
        report_skip["character"] += 1
        continue
    rule = mr.get(str(it.values.get("NPC class")))
    if not rule or any(s in it.name.lower() for s in skip) or it.values.get("slave", 0):
        continue
    cmin, cmax = int(it.values.get("money min", 0)), int(it.values.get("money max", 200))
    nmin, nmax = max(cmin, rule["min"]), max(cmax, rule["max"], rule["min"])
    if (nmin, nmax) != (cmin, cmax):
        mb.change(it.sid, values={"money min": nmin, "money max": nmax})
        report[f"money:{rule['role']}"] += 1

# 2) фракция остатков Империума -----------------------------------------------------
ir = RULES["imperial_remnants"]
tmpl = find(*ir["faction_template"])
fac = mb.new("FACTION", ir["faction_name"], template=tmpl.sid, values={
    "fundamental type": 2, "trustworthy": F32(30.0), "run away ratio of squad size": F32(0.2),
    "run away ratio relative to enemy": F32(0.4), "heals strangers": True, "anti slavery": True})
fac.refs = {k: v for k, v in fac.refs.items() if k in ("races", "personality", "color", "dialog default")}
fac.refs["relations"] = []
for t, n, val in ir["hostile"] + ir["friendly"]:
    other = find(t, n)
    fac.refs["relations"].append(Ref(other.sid, val, 0, 0))
    add_refs(other.sid, "relations", [Ref(fac.sid, val, 0, 0)])  # взаимно
    report["relations"] += 2

# 3) T0-предметы ------------------------------------------------------------------
t0 = {}
for spec in RULES["t0"]["items"]:
    src = find(*spec["src"])
    vals = {}
    for k, mult in spec["mult"].items():
        v = src.values[k]
        vals[k] = int(round(v * mult)) if isinstance(v, int) and not isinstance(v, bool) else F32(v * mult)
    vals["description"] = (src.values.get("description", "") + " Worn trophy from a fallen expedition.").strip()
    t0[spec["src"][1]] = mb.new(src.type_name, src.name + spec["suffix"], template=src.sid, values=vals)
    report["t0_items"] += 1


def t0_character(base_sid, suffix=" (worn kit)"):
    """Клон персонажа, у которого WH-снаряжение заменено на T0-варианты (если есть)."""
    src = M[base_sid]
    c = mb.new("CHARACTER", src.name + suffix, template=base_sid)
    for cat in ("clothing", "crossbows", "weapons"):
        c.refs[cat] = [Ref(t0[M[r.target].name].sid, r.v0, r.v1, r.v2) if r.target in M and M[r.target].name in t0 else r
                       for r in c.refs.get(cat, [])]
    report["t0_characters"] += 1
    return c


# 4) патрули остатков Империума ------------------------------------------------------
patrol_ai = [Ref(find(*a).sid) for a in ir["patrol_ai"]]
squad_tmpl = find("SQUAD_TEMPLATE", "TC Shek Warrior Patrol")
for sq in ir["squads"]:
    leader = find(*sq["leader"])
    s = mb.new("SQUAD_TEMPLATE", sq["name"], template=squad_tmpl.sid)
    s.refs = {"AI packages": list(patrol_ai), "faction": [Ref(fac.sid)], "leader": [Ref(leader.sid, 1, 0, 0)]}
    for t, n, sid, lo_, hi in sq["members"]:
        mem = find(t, n, sid)
        s.refs["squad"] = [Ref(mem.sid, lo_, hi, 0)]
        if sq.get("t0_share"):
            s.refs["squad2"] = [Ref(t0_character(mem.sid).sid, 1, 3, 0)]
    for biome, w in ir["spawns"]:
        add_refs(find("BIOME_GROUP", biome).sid, "homeless spawns", [Ref(s.sid, w, 0, 0)])
        report["spawn_entries"] += 1
    fac.refs.setdefault("squads", []).append(Ref(s.sid))
    report["squads"] += 1

# 5) варбанда орков -------------------------------------------------------------------
gw = RULES["greenskin_warband"]
gfac = find(*gw["faction"])
ai_src = find(*gw["ai_from_squad"])
s = mb.new("SQUAD_TEMPLATE", gw["name"], template=ai_src.sid)
s.refs = {k: v for k, v in s.refs.items() if k in ("AI packages", "dialog leader", "dialog squad")}
s.refs["faction"] = [Ref(gfac.sid)]
s.refs["leader"] = [Ref(find(*gw["leader"]).sid, 1, 0, 0)]
s.refs["squad"] = [Ref(find(gw["members"][0][0], gw["members"][0][1]).sid, gw["members"][0][3], gw["members"][0][4], 0)]
s.refs["squad2"] = [Ref(find(gw["members"][1][0], gw["members"][1][1]).sid, gw["members"][1][3], gw["members"][1][4], 0)]
for biome, w in gw["spawns"]:
    add_refs(find("BIOME_GROUP", biome).sid, "homeless spawns", [Ref(s.sid, w, 0, 0)])
    report["spawn_entries"] += 1
add_refs(gfac.sid, "squads", [Ref(s.sid)])
report["squads"] += 1

# 6) слабые избегают сильных -------------------------------------------------------------
ws = RULES["weak_vs_strong"]
strong = [fac if t == "KMM" else find(t, n) for t, n in ws["strong"]]
weak = [f for f in M.values() if f.type_name == "FACTION" and in_game(f.sid) and f.values.get("fundamental type") == ws["weak_fundamental_type"]
        and not f.values.get("not real", False)]
for f in weak:
    vals = {}
    for k, v in ws["weak_flee"].items():
        cur = f32(f.values.get(k, 0.0))
        if cur < v:
            vals[k] = F32(v)
    if vals:
        mb.change(f.sid, values=vals)
        report["weak_flee"] += 1
    add_refs(f.sid, "coexistence", [Ref(x.sid) for x in strong])
for x in strong:
    add_refs(x.sid, "coexistence", [Ref(f.sid) for f in weak])
report["weak_factions"] = len(weak)
report["strong_factions"] = len(strong)

# 7) бандиты подбирают T0-броню -------------------------------------------------------------
bs = RULES["t0"]["bandit_scavenge"]
armour_t0 = [x for x in t0.values() if x.type_name == "ARMOUR"]
n = 0
for it in M.values():
    if n >= bs["max_characters"]:
        break
    if it.type_name == "CHARACTER" and in_game(it.sid) and it.values.get("NPC class") == 8 and it.refs.get("clothing"):
        add_refs(it.sid, "clothing", [Ref(a.sid, 1, bs["chance"], 0) for a in armour_t0])
        n += 1
report["bandits_scavenge"] = n

# 8) вернуть значения Pathfinding - Collection Pack, перетёртые WH ---------------------------
ra = RULES["reassert_base_values"]
pf = next(m for nme, m, _ in base if nme == ra["from_mod"])
for it in pf.items:
    if it.sid not in M:
        continue
    vals = {k: v for k, v in it.values.items() if k in ra["keys"] and f32(M[it.sid].values.get(k, v)) != f32(v)}
    if vals:
        mb.change(it.sid, values=vals)
        report["reasserted_values"] += len(vals)

# --- зависимости заголовка: моды, чьи записи мы меняем или на которые ссылаемся ----------------
need = set()
for it in mb.items.values():
    if it.change != kmod.CHANGE_NEW:
        need.add(origin[it.sid])
    for refs in it.refs.values():
        for r in refs:
            if r.target in origin:
                need.add(origin[r.target])
order = [n for n, _, _ in layers]
mb.header.dependencies = [n for n in order if n in need]

mod = mb.build()
os.makedirs(BUILD, exist_ok=True)
path = os.path.join(BUILD, f"{NAME}.mod")
data = kmod.write(mod, path)

# --- проверки -------------------------------------------------------------------------
back = kmod.read(path)
assert kmod.write(back) == data
final = {s: kmod._copy(i) for s, i in M.items()}
kmod.apply(final, back)
sch = fcsdef.load(KENSHI)
errors, warns = [], []
for it in back.items:
    e, w = fcsdef.validate(final[it.sid], sch, resolve=final.get) if it.change != kmod.CHANGE_NEW else \
        fcsdef.validate(final[it.sid], sch, resolve=final.get)
    errors += e; warns += w
# ошибки, которые уже были в исходной записи до нас, — не наши
pre = set()
for it in back.items:
    if it.sid in M:
        pre |= set(fcsdef.validate(M[it.sid], sch, resolve=M.get)[0])
ours = [e for e in errors if e not in pre]
missing = [(it.sid, c, r.target) for it in back.items for c, rs in it.refs.items() for r in rs if r.target not in final]
assert not missing, missing[:5]
assert not ours, ours[:10]

rep = {"file": path, "bytes": len(data), "records": len(back.items),
       "new": sum(1 for i in back.items if i.change == kmod.CHANGE_NEW),
       "changed": sum(1 for i in back.items if i.change != kmod.CHANGE_NEW),
       "dependencies": mb.header.dependencies, "counts": dict(report), "skipped_not_in_game": dict(report_skip),
       "validation": {"our_errors": len(ours), "preexisting_errors_in_touched_records": len(errors) - len(ours),
                      "warnings": len(warns)},
       "new_records": [(i.type_name, i.name, i.sid) for i in back.items if i.change == kmod.CHANGE_NEW]}
json.dump(rep, open(os.path.join(ctx.OUT, "glue_report.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(json.dumps({k: rep[k] for k in ("bytes", "records", "new", "changed", "counts", "validation")}, ensure_ascii=False, indent=1))
print("deps:", len(rep["dependencies"]), rep["dependencies"][:6], "...")
for r in rep["new_records"]:
    print("  NEW", *r)

if "--install" in sys.argv:
    dst = os.path.join(KENSHI, "mods", NAME)
    os.makedirs(dst, exist_ok=True)
    shutil.copy2(path, os.path.join(dst, f"{NAME}.mod"))
    print("installed →", dst)
