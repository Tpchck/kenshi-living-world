"""Проверка потока TOWN вне общего генератора (kmm_build.py его пока не знает): сборка в памяти поверх ctx после всех
текущих потоков данных (как это сделает генератор, если TOWN стоит после DIPLO), затем:
fcs.def-валидация записей TOWN (новые ошибки), float-поля только kmod.F32, битые ссылки, round-trip,
изменения существующих записей — только категория «AI packages» SQUAD_TEMPLATE, пересечения полей с другими потоками.
Пишет build/KMM_Town/KMM_Town.mod и scripts/kmm_town_data.lua.     python -I -X utf8 tools/streams/_town_check.py"""
import collections
import importlib
import json
import os
import sys
import time

sys.path.insert(0, r"C:\KenshiModMap\tools\build")
import kmm_build as kb  # noqa: E402  (импорт без запуска run())
import fcsdef  # noqa: E402
import kmod  # noqa: E402


def touched_of(m, name, touched):
    for it in m.items:
        if it.change != kmod.CHANGE_NEW:
            for k in it.values:
                touched[(it.sid, "v:" + k)].append(name)
            for cat in it.refs:
                touched[(it.sid, "r:" + cat)].append(name)


def main():
    t0 = time.time()
    ctx = kb.Ctx()
    sch = fcsdef.load(kb.KENSHI)
    touched = collections.defaultdict(list)
    for name, mod in kb.DATA_STREAMS:   # чужие потоки — только чтобы увидеть их поля и новые записи (ничего не пишем)
        if name == "fix":
            continue
        rp = os.path.join(kb.ROOT, "rules", "streams", f"{name}.json")
        if not os.path.exists(rp):
            continue
        s = kb.Stream(name, mod, ctx)
        importlib.import_module(name).build(ctx, s, json.load(open(rp, encoding="utf-8")))
        m = s.mb.build()
        touched_of(m, name, touched)
        kmod.apply(ctx.M, m)
        for it in m.items:
            ctx.origin.setdefault(it.sid, f"{mod}.mod")
        ctx._reindex()
    rules = json.load(open(os.path.join(kb.ROOT, "rules", "streams", "town.json"), encoding="utf-8"))
    town = importlib.import_module("town")
    s = kb.Stream("town", "KMM_Town", ctx)
    town.build(ctx, s, rules)
    m = s.mb.build()
    touched_of(m, "town", touched)
    need = set()
    for it in m.items:
        if it.change != kmod.CHANGE_NEW and it.sid in ctx.origin:
            need.add(ctx.origin[it.sid])
        for refs in it.refs.values():
            for r in refs:
                if r.target in ctx.origin:
                    need.add(ctx.origin[r.target])
    order = [n for n, _, _ in ctx.layers] + [f"{mod}.mod" for _, mod in kb.DATA_STREAMS]
    m.header.dependencies = [n for n in order if n in need]
    pre = set()
    for it in m.items:
        if it.sid in ctx.M:
            pre |= set(fcsdef.validate(ctx.M[it.sid], sch, resolve=ctx.M.get)[0])
    data = kmod.write(m)
    back = kmod.read(data)
    assert kmod.write(back) == data, "round-trip"
    M = dict(ctx.M)
    kmod.apply(M, back)
    errs, warns = [], 0
    for it in back.items:
        e, w = fcsdef.validate(M[it.sid], sch, resolve=M.get)
        errs += [f"{it.type_name} {it.name}: {x}" for x in e if x not in pre]
        warns += len(w)
    # float-поля только F32 (в новых и изменённых значениях)
    floats = sch.fields
    badf = []
    for it in m.items:
        fd = floats.get(it.type_name, {})
        for k, v in it.values.items():
            if k in fd and fd[k].kind == "float" and not isinstance(v, kmod.F32):
                badf.append(f"{it.type_name} {it.name}: {k}={v!r}")
    broken = [(it.name, c, r.target) for it in back.items for c, rs in it.refs.items() for r in rs
              if (r.v0, r.v1, r.v2) != kmod.DELETED_REF and r.target not in M]
    changed = [it for it in back.items if it.change != kmod.CHANGE_NEW]
    bad_change = [f"{it.type_name} {it.name}: {sorted(it.values)} {sorted(it.refs)}" for it in changed
                  if it.type_name != "SQUAD_TEMPLATE" or it.values or set(it.refs) != {"AI packages"}]
    conflicts = [f"{sid} {f}: {sorted(set(st))}" for (sid, f), st in touched.items() if len(set(st)) > 1 and "town" in st]
    rej = [it.sid for it in back.items if it.sid in ctx.rejected]
    res = {"records": len(back.items), "by_type": dict(collections.Counter(i.type_name for i in back.items)),
           "changed_existing": len(changed), "fcs_errors": len(errs), "warnings": warns, "float_not_f32": len(badf),
           "broken_refs": len(broken), "bad_changes": len(bad_change), "field_conflicts": len(conflicts), "rejected": len(rej),
           "deps": m.header.dependencies, "report": dict(s.report), "seconds": round(time.time() - t0, 1)}
    print(json.dumps(res, ensure_ascii=False, indent=1))
    for x in (errs + badf + [str(b) for b in broken] + bad_change + conflicts)[:30]:
        print("   ERR", x)
    if errs or badf or broken or bad_change or conflicts or rej:
        print("ОШИБКИ — файл не записан")
        sys.exit(1)
    out = os.path.join(kb.ROOT, "build", "KMM_Town")
    os.makedirs(out, exist_ok=True)
    open(os.path.join(out, "KMM_Town.mod"), "wb").write(data)
    print("OK → build/KMM_Town/KMM_Town.mod", len(data), "байт")


if __name__ == "__main__":
    main()
