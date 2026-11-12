"""Проверка потока TECH вне общего генератора (kmm_build.py его пока не знает): сборка в памяти поверх ctx
(1) как сейчас (без Crafting Redux в ctx → ванильные опоры) и (2) с Crafting Redux, подмешанным в ctx так,
как это сделает lo.py EXTRA. Валидация fcs.def, битые ссылки, round-trip, изменения существующих записей.
Пишет build/KMM_Tech/KMM_Tech.mod из варианта (2).   python -I -X utf8 tools/streams/_tech_check.py"""
import collections
import glob
import json
import os
import sys

sys.path.insert(0, r"C:\KenshiModMap\tools\build")
import kmm_build as kb  # noqa: E402  (импорт без запуска run())
import fcsdef  # noqa: E402
import kmod  # noqa: E402

W = r"C:\Program Files (x86)\Steam\steamapps\workshop\content\233860"
CR = [("3585383286", "2PN8CraftingReduxVanilla.mod"), ("3585385588", "2PN8CraftingResearchPatch.mod"),
      ("3585385029", "2PN8CraftingReduxOMO.mod"), ("3585385287", "2PN8CraftingReduxEVA.mod"),
      ("3585386517", "2PN8WeaponSmithingCore.mod"), ("3585386805", "2PN8WeaponSmithing.mod"),
      ("3589917614", "2PN8RoboticsRedux.mod"), ("2760310007", "2PN8RoboticsStorageAndLimbs.mod")]


def one(ctx, sch, rules, label):
    import importlib
    tech = importlib.reload(importlib.import_module("tech"))
    s = kb.Stream("tech", "KMM_Tech", ctx)
    tech.build(ctx, s, rules)
    m = s.mb.build()
    need = set()
    for it in m.items:
        for refs in it.refs.values():
            for r in refs:
                if r.target in ctx.origin:
                    need.add(ctx.origin[r.target])
    m.header.dependencies = [n for n, _, _ in ctx.layers if n in need]
    data = kmod.write(m)
    back = kmod.read(data)
    assert kmod.write(back) == data, "round-trip"
    M = dict(ctx.M)
    kmod.apply(M, back)
    errs, warns = [], 0
    for it in back.items:
        e, w = fcsdef.validate(M[it.sid], sch, resolve=M.get)
        errs += [f"{it.type_name} {it.name}: {x}" for x in e]
        warns += len(w)
    broken = [(it.name, c, r.target) for it in back.items for c, rs in it.refs.items() for r in rs if r.target not in M]
    changed = [it.sid for it in back.items if it.change != kmod.CHANGE_NEW]
    rej = [it.sid for it in back.items if it.sid in ctx.rejected]
    res = {"variant": label, "records": len(back.items), "by_type": dict(collections.Counter(i.type_name for i in back.items)),
           "changed_existing": len(changed), "fcs_errors": len(errs), "warnings": warns, "broken_refs": len(broken),
           "rejected": len(rej), "deps": m.header.dependencies, "report": dict(s.report)}
    print(json.dumps(res, ensure_ascii=False))
    for e in errs[:20]:
        print("   ERR", e)
    for b in broken[:10]:
        print("   BROKEN", b)
    ok = not errs and not broken and not changed and not rej
    return ok, data


def main():
    rules = json.load(open(r"C:\KenshiModMap\rules\streams\tech.json", encoding="utf-8"))
    ctx = kb.Ctx()
    sch = fcsdef.load(kb.KENSHI)
    ok1, _ = one(ctx, sch, rules, "ctx как сейчас (без CR)")
    have = {n for n, _, _ in ctx.layers}
    for wid, f in CR:   # как lo.py EXTRA: после WH/доп. модов, перед KMM_*
        if f in have:
            continue
        m = kmod.read(os.path.join(W, wid, f))
        ctx.wh.append((f, m, None))
        ctx.layers.append((f, m, None))
        kmod.apply(ctx.M, m)
        for it in m.items:
            ctx.origin.setdefault(it.sid, f)
    ctx._reindex()
    ok2, data = one(ctx, sch, rules, "ctx + Crafting Redux (после lo.py EXTRA)")
    if ok1 and ok2:
        out = os.path.join(kb.ROOT, "build", "KMM_Tech")
        os.makedirs(out, exist_ok=True)
        open(os.path.join(out, "KMM_Tech.mod"), "wb").write(data)
        print("OK → build/KMM_Tech/KMM_Tech.mod", len(data), "байт")
    else:
        print("ОШИБКИ — файл не записан")
        sys.exit(1)


if __name__ == "__main__":
    main()
