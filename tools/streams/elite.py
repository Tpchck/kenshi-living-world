"""Поток ELITE (rules/streams/elite.json): элитные мини-подразделения богатых фракций.
Данные (KMM_Elite.mod, только новые записи): на подразделение 3 CHARACTER (боец, ветеран, командир; клон базового бойца фракции
с полным комплектом брони и оружием из каталога) + SQUAD_TEMPLATE (клон боевого отряда фракции: 1 командир + 2–3 бойца + 1–2 ветерана).
Для Lua пишет build/KMM_Elite/scripts/kmm_elite_data.lua (фракция -> шаблон отряда, имя, параметры).
Самостоятельный запуск:  python -I -X utf8 tools/streams/elite.py --check [--write]"""
import json
import os
import sys

ROOT = r"C:\KenshiModMap"
OUT_DIR = os.path.join(ROOT, "build", "KMM_Elite", "scripts")
for _p in ("build", "fast", ""):
    sys.path.insert(0, os.path.join(ROOT, "tools", _p))
from kmod import Ref  # noqa: E402

SLOT_ORDER = ("hat", "body", "legs", "boots", "belt")


def _lua(v, ind=""):
    if isinstance(v, dict):
        inner = ",\n".join(f"{ind}  [{_lua(k)}] = {_lua(x, ind + '  ')}" for k, x in sorted(v.items(), key=lambda kv: str(kv[0])))
        return "{\n" + inner + "\n" + ind + "}" if v else "{}"
    if isinstance(v, (list, tuple)):
        return "{ " + ", ".join(_lua(x, ind) for x in v) + " }"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return repr(v)
    return '"' + str(v).replace("\\", "\\\\").replace('"', '\\"') + '"'


def build(ctx, s, rules):
    cat = {x["sid"]: x for x in json.load(open(rules["catalog"], encoding="utf-8"))["items"]}
    ex = json.load(open(rules["excluded"], encoding="utf-8"))
    excluded = {x["sid"] if isinstance(x, dict) else x for x in (ex["items"] if isinstance(ex, dict) and "items" in ex else ex)}
    bad = tuple(rules["bad_origins"])
    M = ctx.M

    def check_item(sid, typ, unit):
        it = M.get(sid)
        if it is None or it.type_name != typ or not ctx.in_game(sid):
            raise KeyError(f"elite {unit}: {typ} {sid} не найден")
        if sid in excluded:
            raise ValueError(f"elite {unit}: {sid} в catalog_excluded")
        c = cat.get(sid)
        if c is None or c["origin"] in bad:
            raise ValueError(f"elite {unit}: {sid} вне каталога или WH/экзотика")

    out = {"units": {}, "params": rules["lua"]}
    for u in rules["units"]:
        fid = u["faction"]
        if fid not in M or M[fid].type_name != "FACTION" or not ctx.in_game(fid):
            s.report["faction_missing"] += 1   # фракции нет в сборке - тихо пропускаем
            continue
        base = M.get(u["char_template"])
        tsq = M.get(u["squad_template"])
        if base is None or base.type_name != "CHARACTER" or tsq is None or tsq.type_name != "SQUAD_TEMPLATE":
            raise KeyError(f"elite {u['key']}: шаблон бойца/отряда не найден")
        clothing = []
        for slot in SLOT_ORDER:
            lst = u["slots"][slot]
            for i, sid in enumerate(lst):
                check_item(sid, "ARMOUR", u["key"])
                clothing.append(Ref(sid, 1, 100 if i == len(lst) - 1 else 60, 0))
        weapons = []
        for i, sid in enumerate(u["weapons"]):
            check_item(sid, "WEAPON", u["key"])
            weapons.append(Ref(sid, 1, 1, 100 if i == len(u["weapons"]) - 1 else 45))
        chars = {}
        for role, rr in rules["roles"].items():
            ch = s.new("CHARACTER", f"{u['name']} {rr['suffix']}", template=base.sid, values={
                "combat stats": rr["combat"], "wages": rr["wages"], "money min": rr["money"][0], "money max": rr["money"][1],
                "stats randomise": 3})
            ch.refs["clothing"] = list(clothing)
            ch.refs["weapons"] = list(weapons)
            chars[role] = ch.sid
            s.report["characters"] += 1
        q = s.new("SQUAD_TEMPLATE", f"KMM Elite {u['name']}", template=tsq.sid)
        for k in ("leader", "squad", "squad2", "squad3", "vendors", "special items", "world state", "housemates"):
            q.refs.pop(k, None)
        q.refs["leader"] = [Ref(chars["commander"], 1, 0, 0)]
        q.refs["squad"] = [Ref(chars["guard"], *rules["squad_size"]["guard"], 0), Ref(chars["veteran"], *rules["squad_size"]["veteran"], 0)]
        q.refs["faction"] = [Ref(fid)]
        s.report["squads"] += 1
        out["units"][fid] = {"squad": q.sid, "name": u["name"], "key": u["key"]}
        ns = rules.get("native_special")
        if ns and ns.get("enabled"):
            native_special(ctx, s, ns, fid, u, q, chars, base, out["units"][fid], rules.get("own_ws"))
    s.report["units"] = len(out["units"])
    if rules.get("personal_guard", {}).get("enabled"):
        personal_guard(ctx, s, rules["personal_guard"])
    if rules.get("own_ws", {}).get("enabled"):   # LINKN: свои WS + TOWN-варианты (явные sid из реестра) — последним, после всех последовательных sid
        import ws_own
        ws_own.build(ctx, s, rules["own_ws"])
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(os.path.join(OUT_DIR, "kmm_elite_data.lua"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write("-- KMM_Elite data (сгенерировано tools/streams/elite.py - не править руками)\nreturn " + _lua(out) + "\n")


def _check():
    import collections
    import kmm_build as kb
    import fcsdef
    import kmod
    rules = json.load(open(os.path.join(ROOT, "rules", "streams", "elite.json"), encoding="utf-8"))
    ctx = kb.Ctx()
    sch = fcsdef.load(kb.KENSHI)
    s = kb.Stream("elite", "KMM_Elite", ctx)
    build(ctx, s, rules)
    m = s.mb.build()
    need = {ctx.origin[r.target] for it in m.items for rs in it.refs.values() for r in rs if r.target in ctx.origin}
    m.header.dependencies = [n for n, _, _ in ctx.layers if n in need]
    data = kmod.write(m)
    back = kmod.read(data)
    assert kmod.write(back) == data, "round-trip"
    M = dict(ctx.M)
    kmod.apply(M, back)
    errs = []
    for it in back.items:
        e, _ = fcsdef.validate(M[it.sid], sch, resolve=M.get)
        errs += [f"{it.name}: {x}" for x in e]
    broken = [(it.name, c, r.target) for it in back.items for c, rs in it.refs.items() for r in rs if r.target not in M]
    changed = [it.sid for it in back.items if it.change != kmod.CHANGE_NEW]
    print(json.dumps({"records": len(back.items), "by_type": dict(collections.Counter(i.type_name for i in back.items)),
                      "fcs_errors": len(errs), "broken_refs": len(broken), "changed_existing": len(changed),
                      "report": dict(s.report)}, ensure_ascii=False))
    for e in errs[:20]:
        print("  ERR", e)
    for b in broken[:10]:
        print("  BROKEN", b)
    if "--write" in sys.argv and not errs and not broken and not changed:
        os.makedirs(os.path.join(ROOT, "build", "KMM_Elite"), exist_ok=True)
        open(os.path.join(ROOT, "build", "KMM_Elite", "KMM_Elite.mod"), "wb").write(data)
        print("written KMM_Elite.mod", len(data))
    sys.exit(1 if (errs or broken or changed) else 0)


if __name__ == "__main__":
    if "--check" in sys.argv:
        _check()
    print(__doc__)


def personal_guard(ctx, s, R):
    """Личная охрана важных персонажей (владелец 2026-11-13: «усилить личную охрану важных персов»).
    VIP — уникальный CHARACTER (combat >= vip_min_cs или faction importance >= vip_min_imp) в SQUAD_TEMPLATE вместе с
    неуникальными бойцами. Каждый такой боец заменяется в ЭТИХ отрядах клоном-гвардейцем (то же имя/вид/снаряжение/AI,
    combat stats выше), а число гвардейцев растёт умеренно. Исходные шаблоны бойцов (общие для всей фракции) не меняются."""
    import math
    import re
    M = ctx.M
    skip_sq = re.compile(R["skip_squad_rx"], re.I)
    not_guard = re.compile(R["not_guard_rx"], re.I)
    skip_fac = set(R.get("skip_factions", []))
    clones = {}

    def fac_name(ch):
        f = ch.refs.get("faction")
        return M[f[0].target].name if f and f[0].target in M else ""

    def is_vip(ch):
        v = ch.values
        return bool(v.get("unique")) and not v.get("slave") and fac_name(ch) not in skip_fac and (
            (v.get("combat stats") or 0) >= R["vip_min_cs"] or (v.get("faction importance") or 0) >= R["vip_min_imp"])

    def guard_clone(g):
        if g.sid in clones:
            return clones[g.sid]
        cs = int(g.values.get("combat stats") or 0)
        new_cs = min(R["cs_cap"], max(cs + R["cs_add"], int(round(cs * R["cs_mult"]))))
        c = s.new("CHARACTER", g.name, template=g.sid, values={"combat stats": new_cs})
        clones[g.sid] = c.sid
        s.report["guard_clones"] += 1
        return c.sid

    for sq in sorted(M.values(), key=lambda x: x.sid):
        if sq.type_name != "SQUAD_TEMPLATE" or not ctx.in_game(sq.sid) or skip_sq.search(sq.name or ""):
            continue
        mem = [(c, r) for c in ("leader", "squad", "squad2") for r in sq.refs.get(c, []) if r.target in M and M[r.target].type_name == "CHARACTER"]
        if not any(is_vip(M[r.target]) for _, r in mem):
            continue
        guards = [(c, r) for c, r in mem if c != "leader" and not M[r.target].values.get("unique") and not M[r.target].values.get("slave")
                  and not not_guard.search(M[r.target].name or "") and (M[r.target].values.get("combat stats") or 0) >= R["guard_min_cs"]
                  and fac_name(M[r.target]) not in skip_fac]
        if not guards:
            continue
        total = sum(max(r.v0, 0) for _, r in mem)
        if total > R["max_squad_total"]:   # армия, а не личная охрана (Nail's Army 55)
            s.report["guard_skip_army"] += 1
            continue
        sets, dels = {}, {}
        for c, r in guards:
            n0 = max(r.v0, 1)
            add = 0 if total >= R["max_squad_for_growth"] else min(R["add_max"], max(1, math.ceil(n0 * R["add_frac"])))
            v1 = r.v1 + add if r.v1 > 0 else r.v1
            sets.setdefault(c, []).append(kmod_ref(guard_clone(M[r.target]), r.v0 + add if r.v0 > 0 else r.v0, v1, r.v2))
            dels.setdefault(c, []).append(r.target)
            s.report["guard_slots"] += 1
            s.report["guard_added_min"] += add if r.v0 > 0 else 0
        s.change(sq.sid, set_refs=sets, del_refs=dels)
        s.report["vip_squads"] += 1


def native_special(ctx, s, R, fid, u, q, chars, base, rec, rules_own_ws=None):
    """Родной механизм: UNIQUE_SQUAD_TEMPLATE в FACTION."special squads" (движок сам держит и респавнит отряд, replacement time).
    Открывается WORLD_EVENT_STATE-замком (по умолчанию ложен: «жив уник», которого нет); Lua kmm_elite включает его через
    KMM_Native.ws_set, когда фракция богата. Только новые записи + добавленная ссылка в FACTION (сейв-безопасно)."""
    M = ctx.M
    tpl = R["template"]
    if tpl not in M or M[tpl].type_name != "UNIQUE_SQUAD_TEMPLATE":
        raise KeyError(f"elite native: шаблон {tpl} не UNIQUE_SQUAD_TEMPLATE")
    gate = s.new("CHARACTER", f"KMM Elite Gate {u['name']}", template=base.sid)   # никогда не спавнится: «NPC is alive» ложно
    ws = s.new("WORLD_EVENT_STATE", f"KMM Elite open {u['name']}", values={"notes": "KMM_Elite gate: Lua ws_set"})
    ws.refs["NPC is"] = [Ref(gate.sid, 1, 0, 0)]
    fn = (rules_own_ws or {}).get("false_npc")
    if fn and fn in M and M[fn].type_name == "CHARACTER":   # ложь при любом ответе движка о неизвестном NPC: «X жив» И «X НЕ жив» (ванильный уникал)
        import ws_own
        ws.refs.update(ws_own.false_refs(fn, extra_is=[gate.sid]))
    uq = s.new("UNIQUE_SQUAD_TEMPLATE", f"KMM Elite {u['name']}", template=tpl, values={
        "replacement time": R["replacement_hours"], "persistent": R.get("persistent", True)})
    for k in ("leader", "squad", "squad2", "missions", "world state", "faction"):
        uq.refs.pop(k, None)
    uq.refs["leader"] = [Ref(chars["commander"], 1, 0, 0)]
    uq.refs["squad"] = [Ref(chars["guard"], *R["squad_size"]["guard"], 0), Ref(chars["veteran"], *R["squad_size"]["veteran"], 0)]
    uq.refs["faction"] = [Ref(fid)]
    uq.refs["world state"] = [Ref(ws.sid, 1, 0, 0)]
    s.add_refs(fid, "special squads", [Ref(uq.sid, 1, 100, 0)])
    s.report["native_special"] += 1
    rec["uniq"] = uq.sid
    rec["wes"] = ws.sid


def kmod_ref(t, a, b, c):
    return Ref(t, a, b, c)
