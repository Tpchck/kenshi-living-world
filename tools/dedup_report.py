"""Быстрый офлайн-отчёт по дублям в сборке (docs/DEDUP.md). Ничего не пишет, сеть не нужна.
python -I -X utf8 tools/dedup_report.py
Читает моды по списку генератора (tools/build/mods_cfg.py generate) + 4 файла ядра через tools/kmod.py:
  1) точные клоны предметов (ARMOUR/WEAPON/CROSSBOW/ITEM: те же строки, числа, ссылки; имя/описание/цена не важны);
  2) моды-кандидаты на отключение: 0 новых записей, нет ресурсов кроме .mod/.img/.info, никто не ссылается,
     каждая правка (запись, поле) перекрыта более поздним модом;
  3) пустые моды-разделители, всё ещё стоящие в списке.
Код выхода 0 всегда: отчёт информационный."""
import collections
import os
import sys
import time

ROOT = r"C:\KenshiModMap"
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, os.path.join(ROOT, "tools", "build"))
sys.path.insert(0, os.path.join(ROOT, "tools", "fast"))
import kmod  # noqa: E402
import mods_cfg as M  # noqa: E402

T4 = ("ARMOUR", "WEAPON", "CROSSBOW", "ITEM")


def main():
    t0 = time.time()
    lines = M.generate()
    paths = M.mod_paths()
    order = [(c, os.path.join(M.GAME, "data", c)) for c in ("gamedata.base", "rebirth.mod", "Newwworld.mod", "Dialogue.mod")]
    order += [(l, paths[l]) for l in lines if l in paths and not l.startswith("KMM_")]
    seen, groups, writers = set(), collections.defaultdict(list), collections.defaultdict(list)
    info, refd = {}, collections.defaultdict(set)
    for mi, (name, path) in enumerate(order):
        try:
            m = kmod.read(path)
        except Exception:  # noqa: BLE001
            continue
        h = m.header
        for x in list(h.dependencies or []) + list(h.references or []) if h else []:
            refd[x].add(name)
        new = 0
        for it in m.items:
            for k, v in it.values.items():
                writers[(it.sid, k)].append(mi) if (it.change != 0 or it.sid in seen) else None
            if it.change == 0 and it.sid not in seen:
                seen.add(it.sid)
                new += 1
                if mi >= 4 and it.type_name in T4 and it.values.get("mesh"):
                    v = it.values
                    sig = (it.type_name,
                           tuple(sorted((k, str(x).lower().replace("\\", "/")) for k, x in v.items()
                                        if isinstance(x, str) and k not in ("description", "name", "class name") and x)),
                           tuple(sorted((k, round(x, 3) if isinstance(x, float) else x) for k, x in v.items()
                                        if isinstance(x, (int, float)) and not isinstance(x, bool) and k != "value" and "icon" not in k)),
                           tuple(sorted((c, tuple(sorted(r.target for r in rs))) for c, rs in it.refs.items())))
                    groups[sig].append(name)
        files = [f for dp, _, fs in os.walk(os.path.dirname(path)) for f in fs] if mi >= 4 else []
        ext = {os.path.splitext(f)[1].lower() for f in files}
        info[mi] = dict(name=name, n=len(m.items), new=new, res=bool(ext - {".mod", ".img", ".info"}), keys=[
            (it.sid, k) for it in m.items if it.change != 0 for k in it.values])
    cl = {s: v for s, v in groups.items() if len(v) > 1}
    by = collections.Counter(n for v in cl.values() for n in v[1:])
    print(f"клоны предметов: групп {len(cl)}, лишних записей {sum(len(v) - 1 for v in cl.values())}; по модам: {by.most_common(4)}")
    cand = []
    for mi, d in info.items():
        if mi < 4 or d["new"] or d["res"] or d["n"] == 0 or refd.get(d["name"]) or not d["keys"]:
            continue
        if all(any(w > mi for w in writers[k]) for k in d["keys"]):
            cand.append(d["name"])
    print(f"полностью перекрытые моды без новых записей и ресурсов (кандидаты на excluded_mods.json): {len(cand)} {cand[:10]}")
    seps = [d["name"] for mi, d in info.items() if mi >= 4 and d["n"] == 0 and d["name"].startswith("[") and not d["res"]]
    print(f"пустые разделители в списке: {len(seps)}")
    print(f"готово за {time.time() - t0:.0f} с; модов прочитано {len(info)}")


if __name__ == "__main__":
    main()
