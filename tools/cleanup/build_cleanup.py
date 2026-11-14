"""Чистка карты: build/KMM_Cleanup/KMM_Cleanup.mod (+ leveldata/*.zone) и docs/CLEANUP_PLAN.md. Мод ТОЛЬКО для новой игры.
Читает: rules/cleanup.json, Ctx (kmm_build.Ctx — только чтение), зоны слоёв (zone_fix.layers). Пишет только build/KMM_Cleanup,
build/cleanup_report.json и docs/CLEANUP_PLAN.md.
python -I -X utf8 tools/cleanup/build_cleanup.py [--write]   # без --write — только проверки и отчёт (мод не пишется)"""
import collections
import glob
import json
import math
import os
import shutil
import sys

ROOT = r"C:\KenshiModMap"
for _p in ("", "build", "fast", "streams"):
    sys.path.insert(0, os.path.join(ROOT, "tools", _p))
import kmod  # noqa: E402
import fcsdef  # noqa: E402
import zone_fix  # noqa: E402
import mods_cfg  # noqa: E402
import kmm_build as kb  # noqa: E402
import areas  # noqa: E402

OUT = os.path.join(ROOT, "build", "KMM_Cleanup")
SQ_CATS = ("residents", "bar squads", "roaming squads")


def main(write):
    R = json.load(open(os.path.join(ROOT, "rules", "cleanup.json"), encoding="utf-8"))
    ctx = kb.Ctx()
    M = ctx.M
    sch = fcsdef.load(kb.KENSHI)
    mb = kmod.ModBuilder("KMM_Cleanup.mod", M, author="KMM", description="KMM Cleanup: лагеря -> города (только для новой игры; после KMM_Fix)")
    errors, rows = [], []

    # --- слои зон: итоговое состояние инстансов и «кто ввёл» ---
    first, final, src_file = {}, {}, {}
    for lname, zs in zone_fix.layers():
        for z, f in zs.items():
            try:
                mm = kmod.read(f)
            except Exception:
                continue
            for it in mm.items:
                if it.type_name != "INSTANCE_COLLECTION":
                    continue
                for ins in it.instances:
                    k = (z, ins.id)
                    if ins.target and k not in first:
                        first[k] = lname
                        src_file[k] = f
                    final[k] = (lname, ins.target, ins.pos[0], ins.pos[2])
    live = {k: v for k, v in final.items() if v[1]}

    # --- позиции TOWN из leveldata.level (последний слой побеждает) ---
    game = os.path.join(kb.KENSHI, "data", "newland")
    levels = [os.path.join(game, "leveldata.level")] + sorted(glob.glob(os.path.join(game, "leveldata", "*", "leveldata.level")))
    levels += [os.path.join(os.path.dirname(p), "leveldata", "leveldata.level") for p in mods_cfg.mod_paths().values()]
    pos = {}
    for lf in levels:
        if os.path.isfile(lf):
            try:
                for it in kmod.read(lf).items:
                    if it.type_name == "GAMESTATE_TOWN_INSTANCE_LIST":
                        for ins in it.instances:
                            if ins.target:
                                pos[ins.target] = (ins.pos[0], ins.pos[2])
            except Exception:
                pass

    def fac(t):
        r = t.refs.get("faction")
        return r[0].target if r else None

    rmap = areas.RegionMap(M)
    AI_ROAM = [("hang out in a bar", 0), ("Wandering from town to town", 1)]   # как у Poacher Ring (Sailback) / Draul (LFW): родной кочевник
    ai_sid = {}
    for t in M.values():
        if t.type_name == "AI_PACKAGE" and t.name in dict(AI_ROAM) and t.name not in ai_sid and not t.values.get("REMOVED"):
            ai_sid[t.name] = t.sid
    roam_added = collections.defaultdict(list)    # BIOME_GROUP sid -> [squad sid]
    merch_ai = next((t.sid for t in M.values() if t.type_name == "AI_PACKAGE" and t.name == "Merchant (Mod)" and not t.values.get("REMOVED")), None)
    hosts_added = collections.defaultdict(list)   # host sid -> [(squad sid, kind)]
    del_by_zone = collections.defaultdict(list)   # zone -> [instance ids]
    radius = R.get("radius", 2000)
    for c in R["camps"]:
        camp, host = M[c["camp"]], M[c["host"]]
        if camp.type_name != "TOWN" or host.type_name != "TOWN":
            errors.append(f"{c['camp']}/{c['host']}: не TOWN")
            continue
        if host.values.get("REMOVED") or c["host"] in ctx.rejected:
            errors.append(f"хост {host.name} REMOVED/отвергнут")
        src = ctx.origin.get(camp.sid)
        want = set(c.get("squads") or [])
        sqs = [(cat, r) for cat in SQ_CATS for r in camp.refs.get(cat, [])
               if r.target in M and M[r.target].type_name == "SQUAD_TEMPLATE" and (not want or r.target in want)]
        hf = fac(host)
        has_bar = bool(host.refs.get("bar squads"))
        moved = []
        roam = c.get("mode") == "roam"
        region = None
        if roam:   # разыскиваемый уник: не в бар хоста, а родным кочевником своего региона (BIOME_GROUP.homeless spawns + AI «от города к городу»)
            cx0, cz0 = pos.get(camp.sid, (None, None))
            region = rmap.at(cx0, cz0) if cx0 is not None else None
            if region is None or len(ai_sid) < 2:   # точка вне регионов карты -> запасной путь: хост-город
                print(f"ВНИМАНИЕ {camp.name}: roam невозможен (регион {region}, AI {len(ai_sid)}) — отряд идёт в хост {host.name}")
                roam = False
        if roam:
            lead = [(cat, r) for cat, r in sqs if cat != "roaming squads" and M[r.target].refs.get("leader")]
            pets = [(cat, r) for cat, r in sqs if cat != "roaming squads" and not M[r.target].refs.get("leader")]
            if not lead:
                errors.append(f"{camp.name}: roam — нет отряда с лидером")
                continue
            q0 = M[lead[0][1].target]
            for _, r in pets:   # питомцы (отдельный отряд без лидера) идут в отряд хозяина, иначе бродили бы отдельно
                pq = M[r.target]
                for cat2 in ("squad", "squad2", "animals"):
                    if pq.refs.get(cat2):
                        mb.change(q0.sid, set_refs={cat2: [kmod.Ref(x.target, x.v0, x.v1, x.v2) for x in pq.refs[cat2]]})
                moved.append((pq.name, "в отряд " + q0.name, False))
            for _, r in lead:
                q = M[r.target]
                old_ai = [x.target for x in q.refs.get("AI packages", []) if x.target not in ai_sid.values()]
                mb.change(q.sid, set_refs={"AI packages": [kmod.Ref(ai_sid[n], v, 0, 0) for n, v in AI_ROAM]},
                          del_refs={"AI packages": old_ai} if old_ai else None)
                mb.change(region.sid, set_refs={"homeless spawns": [kmod.Ref(q.sid, 1, 0, 0)]})
                roam_added[region.sid].append(q.sid)
                moved.append((q.name, "кочует: " + region.name, False))
            sqs = []
        shop = c.get("mode") == "shop"
        if shop:   # одинокая лавка -> уличный торговец в баре хоста (образец Live Street: is trader, без здания, AI «Merchant (Mod)»)
            if not merch_ai:
                errors.append(f"{camp.name}: shop — нет AI_PACKAGE «Merchant (Mod)»")
                continue
            keep = []
            for cat, r in sqs:
                q = M[r.target]
                if cat == "roaming squads" or not q.values.get("is trader"):
                    moved.append((q.name, "не переезжает (охрана/прочее)", False))
                    continue
                old_ai = [x.target for x in q.refs.get("AI packages", []) if x.target != merch_ai]
                mb.change(q.sid, values={"building designation": 0, "layout interior": "", "building name": ""},
                          set_refs={"AI packages": [kmod.Ref(merch_ai, 0, 0, 0)]}, del_refs={"AI packages": old_ai} if old_ai else None)
                keep.append((cat, r))
            sqs = keep
        for cat, r in sqs:
            if cat == "roaming squads":
                continue
            q = M[r.target]
            if has_bar:
                kind, ref = "bar squads", kmod.Ref(q.sid, 1, 100, 0)
            else:
                kind, ref = "residents", kmod.Ref(q.sid, 1, 2, 0)
            mb.change(host.sid, set_refs={kind: [ref]})
            hosts_added[host.sid].append((q.sid, kind))
            qf = fac(q)
            refac = bool(R.get("refaction") and qf and hf and qf != hf)
            if refac:
                mb.change(q.sid, set_refs={"faction": [kmod.Ref(hf, 0, 0, 0)]}, del_refs={"faction": [qf]})
            moved.append((q.name, kind, refac))
        rem = [camp.sid] + [r.target for r in camp.refs.get("override town", []) if r.target in M]
        for sid in rem:
            mb.change(sid, values={"REMOVED": True})
        cx, cz = pos.get(camp.sid, (None, None))
        if cx is None:
            errors.append(f"{camp.name}: нет позиции в leveldata")
            continue
        mine, other = [], []
        for k, (l, t, x, zz) in live.items():
            d = math.hypot(x - cx, zz - cz)
            if d > 12000:
                continue
            (mine if (first.get(k) == src and d <= radius) else other).append((d, k))
        other.sort()
        for d, k in mine:
            del_by_zone[k[0]].append(k[1])
        rows.append({"camp": camp.name, "camp_sid": camp.sid, "host": ("кочует: " + region.name) if roam else host.name, "roam": roam, "host_sid": host.sid, "host_faction": M[hf].name if hf else None,
                     "who": c["who"], "why": c["why"], "moved": moved, "has_bar": has_bar, "removed_towns": len(rem),
                     "pos": [round(cx), round(cz)], "src": src, "bld": len(mine), "bld_far": round(max([d for d, _ in mine], default=0)),
                     "nearest_other": round(other[0][0]) if other else None, "nearest_other_src": first.get(other[0][1]) if other else None,
                     "alt": c.get("alt")})

    # --- зоны: удаления (шаблон файла — зона мода-источника) ---
    if write:
        if os.path.isdir(OUT):
            shutil.rmtree(OUT)
        os.makedirs(os.path.join(OUT, "leveldata"))
    zones = {}
    for z, ids in sorted(del_by_zone.items()):
        tf = src_file[(z, ids[0])]
        zm = kmod.read(tf)
        ic = next(it for it in zm.items if it.type_name == "INSTANCE_COLLECTION")
        ic.instances = [kmod.Instance(i, "", (0.0, 0.0, 0.0), (1.0, 0.0, 0.0, 0.0), []) for i in sorted(set(ids))]
        zm.items = [ic]
        data = kmod.write(zm)
        if kmod.write(kmod.read(data)) != data:
            errors.append(f"round-trip зоны {z}")
        zones[z] = len(ic.instances)
        if write:
            open(os.path.join(OUT, "leveldata", z), "wb").write(data)

    # --- заголовок: зависимости в порядке слоёв, KMM_Fix последним ---
    m = mb.build()
    need = set()
    for it in m.items:
        if it.sid in ctx.origin:
            need.add(ctx.origin[it.sid])
        for rs in it.refs.values():
            for r in rs:
                if r.target in ctx.origin:
                    need.add(ctx.origin[r.target])
    m.header.dependencies = [n for n, _, _ in ctx.layers if n in need] + ["KMM_Fix.mod"]
    data = kmod.write(m)
    back = kmod.read(data)
    if kmod.write(back) != data:
        errors.append("round-trip KMM_Cleanup.mod")

    # --- проверки ---
    missing = [(it.sid, c, r.target) for it in back.items for c, rs in it.refs.items() for r in rs
               if (r.v0, r.v1, r.v2) != kmod.DELETED_REF and r.target not in M]
    errors += [f"битая ссылка {x}" for x in missing]
    errors += [f"отвергнутый sid {it.sid}" for it in back.items if it.sid in ctx.rejected]
    M2 = dict(M)
    kmod.apply(M2, back)
    for hs, lst in hosts_added.items():
        have = {r.target for cat in ("bar squads", "residents") for r in M2[hs].refs.get(cat, [])}
        errors += [f"хост {M[hs].name}: отряд {sq} не добавлен" for sq, _ in lst if sq not in have]
    errors += [f"{c['camp']}: REMOVED не применился" for c in R["camps"] if not M2[c["camp"]].values.get("REMOVED")]
    for bs, lst in roam_added.items():
        have = {r.target for r in M2[bs].refs.get("homeless spawns", [])}
        errors += [f"регион {M[bs].name}: кочевник {sq} не добавлен" for sq in lst if sq not in have]
        for sq in lst:
            ai = {M2[r.target].name for r in M2[sq].refs.get("AI packages", []) if r.target in M2}
            if ai != {"hang out in a bar", "Wandering from town to town"}:
                errors.append(f"{M[sq].name}: AI-пакеты {sorted(ai)}")
    fe = 0
    for it in back.items:
        e, _ = fcsdef.validate(M2[it.sid], sch, resolve=M2.get)
        pre, _ = fcsdef.validate(M[it.sid], sch, resolve=M.get)
        fe += len([x for x in e if x not in pre])
    if fe:
        errors.append(f"fcsdef: {fe} новых ошибок схемы")
    for r_ in rows:
        if r_["nearest_other"] is not None and r_["nearest_other"] <= radius:
            errors.append(f"{r_['camp']}: чужое здание в радиусе удаления ({r_['nearest_other']})")
    hosts_n = len(hosts_added)
    if write and not errors:
        open(os.path.join(OUT, "KMM_Cleanup.mod"), "wb").write(data)
    rep = {"errors": errors, "records": len(back.items), "deps": back.header.dependencies, "zones": zones, "hosts": hosts_n,
           "camps": [{k: v for k, v in r.items() if k != "why"} for r in rows], "fcs_new_errors": fe, "written": bool(write and not errors)}
    json.dump(rep, open(os.path.join(ROOT, "build", "cleanup_report.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    plan(R, rows, zones)
    print(json.dumps(rep, ensure_ascii=False, indent=1)[:7000])
    if errors:
        sys.exit(1)


def plan(R, rows, zones):
    L = ["# CLEANUP_PLAN — чистка карты (мод KMM_Cleanup, только для новой игры)", "",
         "Генерируется tools\\cleanup\\build_cleanup.py из rules\\cleanup.json (одобрено: удалять локацию вместе с постройками; хост выбирается по лору).",
         "Что делает: отряды лагеря (уник, питомцы внутри отряда) переезжают в хост-город (bar squads v0=1, v1=100; если у хоста нет баров — residents (1, 2, 0) как у жителей лагерей); "
         "TOWN лагеря и его override-варианты получают REMOVED=true; здания лагеря удаляются из zone-файлов. Если фракция переезжающего отряда отличается от фракции хоста, "
         "она заменяется на фракцию хоста (иначе отряд воюет с жителями).",
         "", "## MERGE: лагерь -> хост", "",
         "| Лагерь (позиция; мод) | Хост (фракция) | Кто переезжает | Почему по лору | Как | Построек удаляется | Ближайшее чужое здание |", "|---|---|---|---|---|---|---|"]
    for r in rows:
        how = ", ".join(sorted({k for _, k, _ in r["moved"]})) + (" (баров нет)" if not r["has_bar"] else "")
        if any(f for _, _, f in r["moved"]):
            how += "; фракция заменена на хостовую"
        near = f"{r['nearest_other']} ед." if r["nearest_other"] is not None else "нет в 12000 ед."
        L.append(f"| {r['camp']} ({r['pos'][0]}, {r['pos'][1]}; {r['src']}) | {r['host']} ({r['host_faction']}) | {r['who']} | {r['why']} | {how} | {r['bld']} (до {r['bld_far']} ед.) | {near} |")
    L += ["", f"Итого: {len(rows)} лагерей, {sum(r['bld'] for r in rows)} построек в {len(zones)} зонах. Выбор построек: instance'ы зон, впервые введённые модом-источником лагеря, "
          f"в радиусе {R.get('radius')} ед. от позиции лагеря; чужих зданий в этом радиусе нет (проверяется сборкой).", "",
          "## REVIEW: рекомендации (в сборку НЕ входят)", "", "| Локация | Рекомендация | Причина |", "|---|---|---|"]
    for v in R["review"]:
        L.append(f"| {v['name']} | {v['rec']} | {v['why']} |")
    L += ["", "## Как включить", "",
          "1. rules\\load_order.json: добавить \"KMM_Cleanup\" в список kmm после \"KMM_Fix\" (последним). Генератор mods_cfg берёт мод из build\\KMM_Cleanup\\KMM_Cleanup.mod.",
          "2. Установка: kmm_build копирует только моды потоков из своего summary; папку build\\KMM_Cleanup (с leveldata) нужно скопировать в Kenshi\\mods\\KMM_Cleanup тем же способом (добавить в список копирования установщика) — до этого мод в игру не попадает.",
          "3. Включать только на новой игре: старый сейв хранит лагеря, их жителей и здания; REMOVED и удаление зданий поверх старого сейва дадут рассинхрон.", ""]
    open(os.path.join(ROOT, "docs", "CLEANUP_PLAN.md"), "w", encoding="utf-8").write("\n".join(L))


if __name__ == "__main__":
    main("--write" in sys.argv)
