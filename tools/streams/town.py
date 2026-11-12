"""Поток TOWN (DESIGN «Город за работой»; rules/streams/town.json).

Данные (KMM_Town.mod):
- новый AI_TASK «KMM go to the bar and drink» (GO_TO_THE_BAR_AND_DRINK — в ванили задачи-записи нет);
- новые AI_PACKAGE-варианты: клон исходного пакета жителя (все цели и addon-наследования сохраняются) + цели расписания
  из ванильных AI_TASK (работа у машин / подмастерье у верстака, склад, патруль, покупки, бар, сон, «проснуться при тревоге»);
- существующие SQUAD_TEMPLATE-жители (TOWN/FACTION residents и bar squads, их housemates): ТОЛЬКО категория ссылок
  «AI packages» — исходный пакет заменяется вариантом с тем же приоритетом. Вариант — по crc32(sid) среди [ваниль, A, B];
  торговые/караванные отряды (is trader, roaming squads — ECONOMY) и записи KMM_* не трогаются;
- PCR (CitizensRedux.mod): 4 отряда, явные варианты (rules.pcr).
Ванильные здания, мебель, BUILDING_FUNCTIONALITY, TOWN и чужие town override не меняются.
Для Lua пишет build/KMM_Town/scripts/kmm_town_data.lua: номера taskType работы, машина → категория склада/продукт, города."""
import collections
import os
import re
import zlib

import kmod
from kmod import Ref

ROOT = r"C:\KenshiModMap"
OUT_DIR = os.path.join(ROOT, "build", "KMM_Town", "scripts")
ENUMS = r"C:\Program Files (x86)\Steam\steamapps\common\Kenshi\fcs_enums.def"
GOAL_CATS = ("Leader AI Goals", "Squad AI Goals", "Squad2 AI Goals")
WORK_TASKS = ("AUTO_LABOURING_MINES", "AUTO_LABOURING_MINES_PRETEND", "OPERATE_MACHINERY", "PRETEND_TO_OPERATE_MACHINERY",
              "OPERATE_AUTOMATIC_MACHINERY")


def task_enum():
    """taskType из fcs_enums.def с вырезанными комментариями (fcsdef._parse_enums комментарии не режет)."""
    t = re.sub(r"//[^\n]*", "", open(ENUMS, encoding="utf-8", errors="replace").read())
    m = re.search(r"enum\s+taskType\s*\{([^}]*)\}", t)
    vals, n = {}, 0
    for tok in re.split(r"[,\s]+", m.group(1)):
        if not tok:
            continue
        if "=" in tok:
            a, b = tok.split("=", 1)
            n, tok = int(b), a
        vals[tok] = n
        n += 1
    return vals


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
    TE = task_enum()
    if TE.get("OPERATE_MACHINERY") != 87:
        raise ValueError("town: taskType сдвинут — проверь разбор fcs_enums.def")
    # --- задачи ---------------------------------------------------------------------------------------------------
    bt = rules["bar_task"]
    if TE.get("GO_TO_THE_BAR_AND_DRINK") != bt["enum"]:
        raise ValueError("town: номер GO_TO_THE_BAR_AND_DRINK не совпадает с правилами")
    bar = s.new("AI_TASK", bt["name"], values={"classification": bt["classification"], "ending": bt["ending"],
                                                "enum": bt["enum"], "targeting": bt["targeting"]})
    tasks = {}
    for k, sid in rules["tasks"].items():
        if k.startswith("_"):
            continue
        if sid == "@bar":
            tasks[k] = bar.sid
            continue
        it = ctx.M.get(sid)
        if it is None or it.type_name != "AI_TASK" or it.values.get("REMOVED"):
            raise KeyError(f"town: AI_TASK {k}={sid} не найден")
        tasks[k] = sid

    # --- жители ---------------------------------------------------------------------------------------------------
    residents, roaming = set(), set()
    for it in ctx.all("TOWN") + ctx.all("FACTION"):
        for c in ("residents", "bar squads"):
            residents.update(r.target for r in it.refs.get(c, []))
        roaming.update(r.target for r in it.refs.get("roaming squads", []))
    for sid in list(residents):
        q = ctx.M.get(sid)
        if q is not None:
            residents.update(r.target for r in q.refs.get("housemates", []))

    made = {}  # (src_pkg, variant) -> sid нового пакета

    def variant_pkg(src_sid, vname, spec):
        key = (src_sid, vname)
        if key in made:
            return made[key]
        src = ctx.M.get(src_sid)
        if src is None or src.type_name != "AI_PACKAGE":
            raise KeyError(f"town: AI_PACKAGE {src_sid} не найден")
        p = s.new("AI_PACKAGE", f"KMM {src.name} [{vname}]", template=src_sid)
        for cat, task, a, b in spec.get("drop", []):
            before = len(p.refs.get(cat, []))
            p.refs[cat] = [r for r in p.refs.get(cat, []) if not (r.target == tasks[task] and r.v0 == a and r.v1 == b)]
            if len(p.refs[cat]) == before:
                raise KeyError(f"town: drop {cat}/{task}({a},{b}) не найден в {src.name}")
        for cat, task, a, b, w in spec["add"]:
            if cat not in GOAL_CATS:
                raise KeyError(f"town: категория {cat}")
            p.refs.setdefault(cat, []).append(Ref(tasks[task], a, b, w))
        made[key] = p.sid
        s.report["packages_new"] += 1
        return p.sid

    def swap(q, src_sid, new_sid, role):
        old = [r for r in q.refs.get("AI packages", []) if r.target == src_sid]
        s.change(q.sid, set_refs={"AI packages": [Ref(new_sid, old[0].v0, old[0].v1, old[0].v2)]}, del_refs={"AI packages": [src_sid]})
        s.report[f"squads:{role}"] += 1
        s.report["squads_changed"] += 1

    skip_kmm = re.compile(r"-KMM_\w+\.mod$")
    pkg_role = {}
    for role, spec in rules["roles"].items():
        for p in spec["packages"]:
            pkg_role[p] = role
    pcr = rules["pcr"]["squads"]
    for sid in sorted(residents):
        q = ctx.M.get(sid)
        if q is None or q.type_name != "SQUAD_TEMPLATE" or not ctx.in_game(sid) or sid in pcr:
            continue
        if skip_kmm.search(sid) or q.values.get("is trader") or sid in roaming:
            s.report["skip_trade_or_kmm"] += 1 if any(r.target in pkg_role for r in q.refs.get("AI packages", [])) else 0
            continue
        hit = [r.target for r in q.refs.get("AI packages", []) if r.target in pkg_role]
        if not hit:
            continue
        src = hit[0]
        role = pkg_role[src]
        names = sorted(rules["roles"][role]["variants"])
        opts = ([None] if rules.get("vanilla_share", True) else []) + names
        pick = opts[zlib.crc32(sid.encode("utf-8")) % len(opts)]
        if pick is None:
            s.report[f"vanilla:{role}"] += 1
            continue
        swap(q, src, variant_pkg(src, f"{role}:{pick}", rules["roles"][role]["variants"][pick]), role)
    for sid, (src, vname) in sorted(pcr.items()):
        q = ctx.M.get(sid)
        if q is None:
            s.report["pcr_missing"] += 1   # PCR не в сборке — тихо пропускаем
            continue
        if all(r.target != src for r in q.refs.get("AI packages", [])):
            raise KeyError(f"town: у отряда PCR {sid} нет пакета {src}")
        swap(q, src, variant_pkg(src, f"pcr:{vname}", rules["pcr"]["variants"][vname]), "pcr")

    # --- данные для Lua -------------------------------------------------------------------------------------------
    ch = rules["chain"]
    item_by_name = collections.defaultdict(list)
    for it in ctx.all("ITEM"):
        item_by_name[it.name].append(it)
    prio, cat_items = {}, {}
    for cat, names in ch["items"].items():
        cat_items[cat] = []
        for i, nm in enumerate(names):
            vs = sorted(item_by_name.get(nm, []), key=lambda x: (ctx.origin.get(x.sid) not in ("gamedata.base", "rebirth.mod"), x.sid))
            if vs:
                prio[vs[0].sid] = (cat, i)
                cat_items[cat].append(vs[0].sid)
    machines = {}
    for b in ctx.all("BUILDING"):
        for fr in b.refs.get("functionality", []):
            f = ctx.M.get(fr.target)
            if f is None:
                continue
            best = None
            for c in ("produces", "item crafts"):
                for r in f.refs.get(c, []):
                    if r.target in prio and (best is None or prio[r.target][1] < prio[best][1]):
                        best = r.target
            if best:
                machines[b.sid] = {"cat": prio[best][0], "item": best}
            else:
                for c, cat in ch["bench_categories"].items():
                    if f.refs.get(c):
                        machines[b.sid] = {"cat": cat}
                        break
    towns = {t.sid: t.name for t in ctx.all("TOWN") if t.refs.get("residents") or t.refs.get("bar squads")}
    data = {"version": 1, "work_tasks": {k: TE[k] for k in WORK_TASKS}, "machines": machines, "cat_items": cat_items, "towns": towns}
    s.report["lua_machines"] = len(machines)
    s.report["lua_towns"] = len(towns)
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(os.path.join(OUT_DIR, "kmm_town_data.lua"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write("-- KMM_Town data (сгенерировано tools/streams/town.py — не править руками)\nreturn " + _lua(data) + "\n")
