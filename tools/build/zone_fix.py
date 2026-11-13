"""Патч зон мира (leveldata/*.zone) для KMM_Fix: возвращает намеренные правки зданий, откатанные «снимками» поздних модов.

Факт (2026-11-13, сейвы владельца): редактор FCS пишет в zone-файл мода копии ВСЕХ инстансов зоны, включая чужие
неизменённые. Поздний мод такой копией воскрешает здание, удалённое ранним модом, или откатывает его перенос.
Пример: CATO V4 удаляет 119 ванильных зданий Heng и ставит свои; Towns Expansion грузится позже и несёт неизменённые
копии этих 119 — в сейве все 119 стоят под зданиями CATO (наложение). Модель предсказывает сейв точно (119/119).
Решение: KMM_Fix грузится последним; для инстанса, чьё итоговое состояние — неизменённая копия оригинала, а раньше
был намеренный правщик (удаление или иная позиция/модель), повторяем намеренное состояние. Новых зданий не ставим.
python -I -X utf8 tools/build/zone_fix.py [--write]  — отчёт / запись в build/KMM_Fix/leveldata."""
import collections
import glob
import json
import os
import shutil
import sys

ROOT = r"C:\KenshiModMap"
GAME = r"C:\Program Files (x86)\Steam\steamapps\common\Kenshi"
for _p in ("", "build", "fast"):
    _d = os.path.join(ROOT, "tools", _p)
    if _d not in sys.path:
        sys.path.insert(0, _d)
import kmod  # noqa: E402
import mods_cfg  # noqa: E402


def layers():
    """[(имя слоя, {зона: путь})] в порядке загрузки: ваниль (data/__mods.list), затем mods.cfg."""
    out = []
    base = os.path.join(GAME, "data", "newland", "leveldata")
    out.append(("vanilla:base", {os.path.basename(f): f for f in glob.glob(os.path.join(base, "*.zone"))}))
    try:
        vlist = [l.strip() for l in open(os.path.join(GAME, "data", "__mods.list"), encoding="utf-8", errors="replace") if l.strip()]
    except OSError:
        vlist = []
    vdirs = [d for d in os.listdir(base) if os.path.isdir(os.path.join(base, d))]
    vorder = [os.path.splitext(v)[0] for v in vlist if os.path.splitext(v)[0] in vdirs] + sorted(d for d in vdirs if d + ".mod" not in vlist and d not in [os.path.splitext(v)[0] for v in vlist])
    for d in vorder:
        out.append(("vanilla:" + d, {os.path.basename(f): f for f in glob.glob(os.path.join(base, d, "*.zone"))}))
    paths = mods_cfg.mod_paths()
    for name in mods_cfg.generate():
        if name == "KMM_Fix.mod":
            continue
        p = paths.get(name)
        if not p:
            continue
        zs = {os.path.basename(f): f for f in glob.glob(os.path.join(os.path.dirname(p), "leveldata", "*.zone"))}
        if zs:
            out.append((name, zs))
    return out


def _same(a, b):
    return (a.target == b.target and all(abs(x - y) < 0.05 for x, y in zip(a.pos, b.pos))
            and all(abs(x - y) < 1e-3 for x, y in zip(a.rot, b.rot)))


def plan():
    """{зона: [(Instance намеренного состояния, путь файла-источника)]}, отчёт."""
    L = layers()
    by_zone = collections.defaultdict(list)
    for name, zs in L:
        for z, f in zs.items():
            by_zone[z].append((name, f))
    res, rep = {}, {"layers_with_zones": len(L), "zones_multi": 0, "zones": 0, "deletions": 0, "restored_edits": 0,
                    "by_pair": collections.Counter(), "bad": []}
    for z, chain in sorted(by_zone.items()):
        if len(chain) < 2:
            continue
        rep["zones_multi"] += 1
        orig, intended, actual = {}, {}, {}
        for name, f in chain:
            try:
                m = kmod.read(f)
            except Exception as e:
                rep["bad"].append(f"{name}:{z}:{type(e).__name__}")
                continue
            for it in m.items:
                if it.type_name != "INSTANCE_COLLECTION":
                    continue
                for ins in it.instances:
                    if ins.id not in orig:
                        if ins.target:
                            orig[ins.id] = ins
                        actual[ins.id] = (name, ins, f)
                        continue
                    if not ins.target or not _same(ins, orig[ins.id]):
                        intended[ins.id] = (name, ins, f)
                    actual[ins.id] = (name, ins, f)
        fix = []
        for k, (iname, ins, f) in intended.items():
            aname, ains, _ = actual[k]
            if aname != iname and ains.target and _same(ains, orig[k]):
                fix.append((ins, f))
                rep["by_pair"][f"{'del' if not ins.target else 'edit'}: {iname} <- {aname}"] += 1
                rep["deletions" if not ins.target else "restored_edits"] += 1
        if fix:
            res[z] = fix
            rep["zones"] += 1
    rep["by_pair"] = dict(rep["by_pair"].most_common())
    return res, rep


def write(out_dir=os.path.join(ROOT, "build", "KMM_Fix", "leveldata")):
    res, rep = plan()
    if os.path.isdir(out_dir):
        shutil.rmtree(out_dir)
    if not res:
        return rep
    os.makedirs(out_dir)
    for z, fix in res.items():
        tf = next((f for ins, f in fix if not ins.target), fix[0][1])
        m = kmod.read(tf)
        ic = next(it for it in m.items if it.type_name == "INSTANCE_COLLECTION")
        ic.instances, states, cache = [], [], {}
        for ins, f in fix:
            if not ins.target:
                ic.instances.append(kmod.Instance(ins.id, "", (0.0, 0.0, 0.0), (1.0, 0.0, 0.0, 0.0), []))
                continue
            ic.instances.append(kmod.Instance(ins.id, ins.target, tuple(ins.pos), tuple(ins.rot), list(ins.states)))
            src = cache.get(f) or cache.setdefault(f, {it.sid: it for it in kmod.read(f).items})
            states += [src[sid] for sid in ins.states if sid in src]
        m.items = [ic] + states
        kmod.write(m, os.path.join(out_dir, z))
    rep["written"] = sorted(res)
    return rep


if __name__ == "__main__":
    if "--write" in sys.argv:
        r = write()
    else:
        _, r = plan()
    print(json.dumps(r, ensure_ascii=False, indent=1)[:4000])
