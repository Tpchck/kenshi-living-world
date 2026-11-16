"""Общий генератор KMM (владелец — интегратор). Собирает моды потоков поверх слитого контекста
ваниль → основа (официальный LO) → WH и проверяет, что каждое поле существующей записи меняет не больше одного потока.

Потоки данных: tools/streams/<имя>.py (функция build(ctx, s, rules)) + rules/streams/<имя>.json → build/KMM_<Имя>/KMM_<Имя>.mod
Lua-потоки: только папка build/KMM_<Имя>/ (scripts/…); генератор кладёт туда пустой KMM_<Имя>.mod для лаунчера.

python -I -X utf8 tools/build/kmm_build.py                  # собрать всё в памяти, проверки, ничего не писать
python -I -X utf8 tools/build/kmm_build.py --write merged   # пересобрать только build/KMM_Merged (слияние малых модов)
python -I -X utf8 tools/build/kmm_build.py --write economy  # записать только свой мод (для потоков)
python -I -X utf8 tools/build/kmm_build.py --write all --install   # ТОЛЬКО интегратор: сначала tools/verify_all.py (при FAIL не ставит; --no-verify только для отладки), запись + копия в Kenshi/mods + mods.cfg (tools/build/mods_cfg.py) + rules/installed_manifest.json
Рубильники (rules/features.json) раскладываются features.py при каждом запуске.
"""
import collections
import importlib
import json
import os
import re
import shutil
import struct
import sys

ROOT = r"C:\KenshiModMap"
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, os.path.join(ROOT, "tools", "fast"))
sys.path.insert(0, os.path.join(ROOT, "tools", "streams"))
sys.path.insert(0, os.path.join(ROOT, "tools", "build"))
import ctx as _ctx  # noqa: E402
import fcsdef  # noqa: E402
import kmod  # noqa: E402

KENSHI = r"C:\Program Files (x86)\Steam\steamapps\common\Kenshi"
# порядок важен: поздние потоки видят новые записи ранних (могут ссылаться, но не менять их)
DATA_STREAMS = [("core", "KMM_Core"), ("relics", "KMM_Relics"), ("wardrobe", "KMM_Wardrobe"), ("economy", "KMM_Economy"), ("behavior", "KMM_Behavior"), ("traces", "KMM_Traces"), ("tech", "KMM_Tech"), ("build", "KMM_Build"), ("diplo", "KMM_Diplo"), ("town", "KMM_Town"), ("elite", "KMM_Elite"), ("atlas", "KMM_Atlas"), ("fix", "KMM_Fix")]
LUA_STREAMS = [("conductor", "KMM_Conductor"), ("rumors", "KMM_Rumors"), ("ore", "KMM_Ore"), ("stock", "KMM_Stock"), ("tempo", "KMM_Tempo"), ("native", "KMM_Native")]   # native: Lua-адаптер + DLL (tools/cpp/kmm_native/build.bat кладёт DLL в build/KMM_Native)
f32 = lambda v: struct.unpack("<f", struct.pack("<f", v))[0]  # noqa: E731


class Ctx:
    def __init__(self):
        self.lo, self.van, self.base, self.wh = _ctx.load()
        self.layers = self.van + self.base + self.wh
        self.M = {}
        for _, m, _ in self.layers:
            kmod.apply(self.M, m)
        self.origin = {}
        for n, m, _ in self.layers:
            for it in m.items:
                self.origin.setdefault(it.sid, n)
        self.rejected = set(json.load(open(os.path.join(ROOT, "rules", "game_rejected_sids.json"), encoding="utf-8"))["sids"])
        ws = json.load(open(os.path.join(ROOT, "rules", "world_seed.json"), encoding="utf-8"))
        import time
        self.world_seed_rules = ws
        self.world_seed = int(time.time()) % 1000000007 if ws.get("mode") == "per_build" else int(ws.get("seed", 2026))
        self._reindex()

    def _reindex(self):
        self.idx = collections.defaultdict(list)
        for it in self.M.values():
            self.idx[(it.type_name, it.name)].append(it)

    def in_game(self, sid):
        """False для записей, которые игра отбрасывает (лог теста → rules/game_rejected_sids.json)."""
        return sid not in self.rejected

    def find(self, tname, name, sid=None):
        if sid:
            it = self.M.get(sid)
            if it is None or it.type_name != tname:
                raise KeyError(f"{tname} {sid} не найден")
            return it
        hits = self.idx.get((tname, name), [])
        if len(hits) != 1:
            raise KeyError(f"{tname} {name!r}: найдено {len(hits)} (нужно ровно 1)")
        return hits[0]

    def all(self, tname):
        return [i for i in self.M.values() if i.type_name == tname and self.in_game(i.sid)]


class Stream:
    """Обёртка ModBuilder для потока: учёт затронутых записей и отчёт."""

    def __init__(self, name, mod, ctx):
        self.name, self.mod, self.ctx = name, mod, ctx
        self.mb = kmod.ModBuilder(f"{mod}.mod", ctx.M, author="KMM", description=f"KMM stream: {name}")
        self.report = collections.Counter()

    def new(self, *a, **k):
        return self.mb.new(*a, **k)

    def change(self, sid, **k):
        if not self.ctx.in_game(sid):
            self.report["skipped_rejected_sid"] += 1
            return None
        return self.mb.change(sid, **k)

    def add_refs(self, sid, cat, refs):
        """Добавить ссылки, которых ещё нет (в существующую запись — дельтой, в свою новую — напрямую)."""
        cur = self.mb.items.get(sid)
        if cur is not None and cur.change == kmod.CHANGE_NEW:
            have = {x.target for x in cur.refs.get(cat, [])}
            cur.refs.setdefault(cat, []).extend(r for r in refs if r.target not in have)
            return
        have = {r.target for r in self.ctx.M[sid].refs.get(cat, [])} if sid in self.ctx.M else set()
        new = [r for r in refs if r.target not in have]
        if new:
            self.change(sid, set_refs={cat: new})

    def raise_values(self, sid, values):
        """Поднять числовые значения (только вверх)."""
        it = self.ctx.M[sid]
        out = {}
        for k, v in values.items():
            cur = it.values.get(k, 0)
            if f32(float(cur)) < f32(float(v)):
                out[k] = v
        if out:
            self.change(sid, values=out)
        return out


def run(write=(), install=False):
    # автопроверка перед сборкой (tools/build/mods_cfg.py): моды на диске, зависимости, исключённые, файлы тела, Dust
    import mods_cfg
    import features
    for ch in features.apply():   # рубильники rules/features.json -> kmm_native.json, conductor.json, wardrobe.json, merge.json
        print("рубильник:", ch)
    import merge_mods   # поток merged → build/KMM_Merged (rules/merge.json, tools/build/merge_mods.py)
    mrep = merge_mods.step(write=("all" in write or "merged" in write))
    if mrep.get("enabled") and not mrep.get("ok"):
        sys.exit("ПРОВЕРКА ПЕРЕД СБОРКОЙ НЕ ПРОЙДЕНА: слияние KMM_Merged (эквивалентность/чтение)")
    cfg_lines = mods_cfg.generate()   # заодно обновляет tools/fast/out/final_lo.json для контекста
    cerr, cwarn, unknown = mods_cfg.check(cfg_lines)
    merged_src = set(mods_cfg.merge_state(cfg_lines)["ok"])   # слитые моды: зависимость на них = зависимость на KMM_Merged
    for w_ in cwarn:
        print("ВНИМАНИЕ:", w_)
    if cerr:
        for e in cerr:
            print("ОШИБКА mods.cfg:", e)
        sys.exit(f"ПРОВЕРКА ПЕРЕД СБОРКОЙ НЕ ПРОЙДЕНА: {len(cerr)} ошибок")
    import subprocess as _sp   # статическая проверка Lua (tools/build/lua_lint.py): хуки на загрузке, guarded, sdata
    lint = _sp.run([sys.executable, "-I", "-X", "utf8", os.path.join(ROOT, "tools", "build", "lua_lint.py")], capture_output=True, text=True, encoding="utf-8")
    if lint.returncode != 0:
        print(lint.stdout[-3000:])
        sys.exit("ПРОВЕРКА ПЕРЕД СБОРКОЙ НЕ ПРОЙДЕНА: lua_lint")
    if "all" in write or "fix" in write:
        print("маски тела Community Part Map → build/KMM_Fix:", mods_cfg.reassert(cfg_lines))
    ctx = Ctx()
    sch = fcsdef.load(KENSHI)
    touched = collections.defaultdict(list)  # (sid, поле) -> [поток]; поле = «v:<значение>» или «r:<категория ссылок>»; только изменения существующих записей
    built = []
    for name, mod in DATA_STREAMS:
        rp = os.path.join(ROOT, "rules", "streams", f"{name}.json")
        if not os.path.exists(rp):
            continue
        rules = json.load(open(rp, encoding="utf-8"))
        s = Stream(name, mod, ctx)
        importlib.import_module(name).build(ctx, s, rules)
        m = s.mb.build()
        if not m.items:
            continue
        for it in m.items:
            if it.change != kmod.CHANGE_NEW:
                for k in it.values:
                    touched[(it.sid, "v:" + k)].append(name)
                for cat in it.refs:
                    touched[(it.sid, "r:" + cat)].append(name)
                if it.change & kmod.CHANGE_RENAMED:
                    touched[(it.sid, "name")].append(name)
        # зависимости заголовка: моды, чьи записи меняем или на которые ссылаемся
        need = set()
        for it in m.items:
            if it.change != kmod.CHANGE_NEW and it.sid in ctx.origin:
                need.add(ctx.origin[it.sid])
            for refs in it.refs.values():
                for r in refs:
                    if r.target in ctx.origin:
                        need.add(ctx.origin[r.target])
        need = {"KMM_Merged.mod" if n in merged_src else n for n in need}
        order = [n for n, _, _ in ctx.layers] + ["KMM_Merged.mod"] + [b[1] + ".mod" for b in built]
        m.header.dependencies = [n for n in order if n in need]
        pre = set()  # ошибки схемы, которые были в записи до потока (огрехи чужих модов) — не наши
        for it in m.items:
            if it.sid in ctx.M:
                pre |= set(fcsdef.validate(ctx.M[it.sid], sch, resolve=ctx.M.get)[0])
        kmod.apply(ctx.M, m)
        for it in m.items:  # новые записи потока видны следующим потокам
            ctx.origin.setdefault(it.sid, f"{mod}.mod")
        ctx._reindex()
        built.append((name, mod, m, s.report, pre))

    # --- проверки -------------------------------------------------------------------
    errors = []
    # правило (DECISIONS 2026-11-11): конфликт = два потока меняют ОДНО ПОЛЕ одной записи (разные поля — можно)
    conflicts = {key: st for key, st in touched.items() if len(set(st)) > 1}
    for (sid, field), st in sorted(conflicts.items()):
        errors.append(f"КОНФЛИКТ: {sid} «{ctx.M[sid].name if sid in ctx.M else '?'}» поле {field[2:] if field[1] == ':' else field} меняют потоки {sorted(set(st))}")
    # бюджет происхождения (rules/budget.json): доля WH в спавнах и экзотики в выдачах гардероба
    import budget
    wrep = next((dict(rep) for name, mod, m, rep, pre in built if name == "wardrobe"), {})
    bres, berr = budget.check(ctx, wrep)
    errors += berr
    print("БЮДЖЕТ ПРОИСХОЖДЕНИЯ:", json.dumps(bres, ensure_ascii=False))
    summary = []
    for name, mod, m, rep, pre in built:
        data = kmod.write(m)
        back = kmod.read(data)
        assert kmod.write(back) == data, f"{mod}: round-trip"
        ours = []
        warns = 0
        for it in back.items:
            e, w = fcsdef.validate(ctx.M[it.sid], sch, resolve=ctx.M.get)
            ours += [x for x in e if x not in pre]
            warns += len(w)
        missing = [(it.sid, c, r.target) for it in back.items for c, rs in it.refs.items() for r in rs
                   if (r.v0, r.v1, r.v2) != kmod.DELETED_REF and r.target not in ctx.M]
        rej = [it.sid for it in back.items if it.sid in ctx.rejected]
        errors += [f"{mod}: {e}" for e in ours] + [f"{mod}: битая ссылка {x}" for x in missing[:20]] + [f"{mod}: отвергнутый игрой sid {x}" for x in rej]
        summary.append({"stream": name, "mod": mod, "records": len(back.items),
                        "new": sum(1 for i in back.items if i.change == kmod.CHANGE_NEW),
                        "changed": sum(1 for i in back.items if i.change != kmod.CHANGE_NEW),
                        "deps": len(m.header.dependencies), "fcs_errors": len(ours), "warnings": warns, "report": dict(rep)})
        if ("all" in write or name in write) and not errors:
            out = os.path.join(ROOT, "build", mod)
            os.makedirs(out, exist_ok=True)
            open(os.path.join(out, f"{mod}.mod"), "wb").write(data)
    # Lua-потоки: пустой .mod рядом со scripts/
    for name, mod in LUA_STREAMS:
        d = os.path.join(ROOT, "build", mod)
        if os.path.isdir(os.path.join(d, "scripts")) and ("all" in write or name in write):
            e = kmod.ModFile(kmod.FILE_MOD17, kmod.Header(author="KMM", description=f"KMM Lua stream: {name}"), 0, [])
            kmod.write(e, os.path.join(d, f"{mod}.mod"))
            summary.append({"stream": name, "mod": mod, "lua_files": sum(len(f) for _, _, f in os.walk(os.path.join(d, "scripts")))})
    rep = {"errors": errors, "budget": bres, "world_seed": ctx.world_seed, "streams": summary}
    json.dump(rep, open(os.path.join(ROOT, "build", "kmm_build_report.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(rep, ensure_ascii=False, indent=1)[:6000])
    if errors:
        print(f"\nСБОРКА ОСТАНОВЛЕНА: {len(errors)} ошибок")
        sys.exit(1)
    if install:
        sys.path.insert(0, os.path.join(ROOT, "tools"))
        import release                      # снимок установленного перед заменой: откат одной командой
        release.snapshot("pre_install")
        if merged_src:
            summary.append({"stream": "merged", "mod": "KMM_Merged"})   # слитые малые моды (merge_mods.py)
        for s in summary:
            src = os.path.join(ROOT, "build", s["mod"])
            dst = os.path.join(KENSHI, "mods", s["mod"])
            if os.path.isdir(dst):
                shutil.rmtree(dst)
            shutil.copytree(src, dst, ignore=shutil.ignore_patterns("_dev", "tools", "__pycache__", "*.txt"))
            print("installed →", dst)
        _lo = json.load(open(os.path.join(ROOT, "rules", "load_order.json"), encoding="utf-8"))
        for m, on in _lo.get("new_game", {}).items():   # моды новой игры (KMM_Cleanup): ставим только включённые
            src, dst = os.path.join(ROOT, "build", m), os.path.join(KENSHI, "mods", m)
            if on is True and os.path.isdir(src):
                if os.path.isdir(dst):
                    shutil.rmtree(dst)
                shutil.copytree(src, dst, ignore=shutil.ignore_patterns("_dev", "tools", "__pycache__", "*.txt"))
                print("installed (new game) →", dst)
        cfg_lines = mods_cfg.generate()   # с учётом только что собранных модов
        cerr, _, unknown = mods_cfg.check(cfg_lines)
        if cerr:
            sys.exit("mods.cfg не записан: " + "; ".join(cerr))
        stamp = mods_cfg.write(cfg_lines, unknown)
        import verify_all   # манифест установленного (md5 .mod) для следующих проверок
        print("rules/installed_manifest.json:", verify_all.write_manifest(cfg_lines), "модов")
        print(f"mods.cfg записан: {len(cfg_lines)} модов (бэкап backup/cfg/mods.cfg.{stamp}), реестр лаунчера +{len(unknown)}")
    return rep


if __name__ == "__main__":
    args = sys.argv[1:]
    if "--install" in args and "--no-verify" not in args:   # единый вход перед установкой (tools/verify_all.py); --no-verify только для отладки
        sys.path.insert(0, os.path.join(ROOT, "tools"))
        import verify_all
        if not verify_all.run()[0]:
            sys.exit("УСТАНОВКА ОТМЕНЕНА: verify_all FAIL")
    w = args[args.index("--write") + 1].split(",") if "--write" in args else []
    run(write=w, install="--install" in args)
