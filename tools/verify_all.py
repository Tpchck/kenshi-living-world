r"""Единый вход перед установкой (RELY): python -I -X utf8 tools\verify_all.py   (<= 2-3 мин, обычно секунды)

1. окружение: kenshi_x64.exe == откатанный 1.0.65 (rules/env_baseline.json), RE_Kenshi.dll / KenshiLib.dll на месте и совпадают с эталоном,
   KenshiLua (3817000612) на диске, md5 модов из mods.cfg против rules/installed_manifest.json (изменённые Steam-моды - предупреждение);
2. все test_*.py (build/**/_dev, KMM_Rumors/tools, tools/cpp/kmm_native, tools/conductor, tools/test) параллельно, каждый из своей папки,
   через tools/test/log_sandbox.py (logs/ теста -> своя временная папка); живые logs/ до и после прогона сверяются (рост = FAIL);
3. lua_lint; mods_cfg check; test_conflict (ДОЛЖЕН остановить сборку: «СБОРКА ОСТАНОВЛЕНА»/EXIT 1 = успех); kmm_build холостой (errors == []).
Итог последней строкой: OK / OK, предупреждений: N / FAIL (N). Код выхода 0 только при OK.
  --init-env        записать текущие хэши exe/dll как эталон rules/env_baseline.json
  --init-manifest   записать rules/installed_manifest.json по живому mods.cfg (kmm_build --install делает это сам)
Игровые папки только читаются.
"""
import concurrent.futures as cf
import glob
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = r"C:\KenshiModMap"
GAME = r"C:\Program Files (x86)\Steam\steamapps\common\Kenshi"
WORK = r"C:\Program Files (x86)\Steam\steamapps\workshop\content\233860"
LUA_ID = "3817000612"
BASELINE = os.path.join(ROOT, "rules", "env_baseline.json")
MANIFEST = os.path.join(ROOT, "rules", "installed_manifest.json")
EXE_BACKUP = os.path.join(ROOT, "backup", "pre_rekenshi", "kenshi_x64.exe")
ENV = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
TEST_GLOBS = ["build/*/_dev/test_*.py", "build/KMM_Rumors/tools/test_rumors_world.py", "tools/cpp/kmm_native/test_adapter.py",
              "tools/conductor/test_*.py", "tools/test/test_*.py"]


def _h(path, algo):
    h = hashlib.new(algo)
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def env_files():
    return {"kenshi_x64.exe": (os.path.join(GAME, "kenshi_x64.exe"), "sha256"),
            "RE_Kenshi.dll": (os.path.join(GAME, "RE_Kenshi.dll"), "md5"),
            "KenshiLib.dll": (os.path.join(GAME, "KenshiLib.dll"), "md5")}


def init_env():
    base = {"_doc": "Эталон окружения (verify_all.py). kenshi_x64.exe = откатанный RE_Kenshi 0.3.5 exe 1.0.65; эталон совпадает с backup/pre_rekenshi/kenshi_x64.exe. Менять только после осознанного обновления RE_Kenshi/игры: python tools/verify_all.py --init-env",
            "game_version": "1.0.65", "files": {}}
    for k, (p, a) in env_files().items():
        base["files"][k] = {"algo": a, "hash": _h(p, a), "size": os.path.getsize(p)}
    if os.path.exists(EXE_BACKUP):
        base["backup_exe_sha256"] = _h(EXE_BACKUP, "sha256")
    json.dump(base, open(BASELINE, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return base


def live_mods():
    sys.path.insert(0, os.path.join(ROOT, "tools", "build"))
    import mods_cfg
    return mods_cfg.read_live(), mods_cfg.mod_paths()


def _kind(path):
    p = os.path.normcase(path)
    if p.startswith(os.path.normcase(WORK)):
        return "workshop:" + os.path.relpath(path, WORK).split(os.sep)[0]
    return "build" if p.startswith(os.path.normcase(os.path.join(ROOT, "build"))) else "game"


def write_manifest(lines=None, paths=None, stamp=None):
    """Манифест установленного: md5 .mod каждого мода из mods.cfg. Зовётся после успешной установки."""
    if lines is None or paths is None:
        l2, p2 = live_mods()
        lines = l2 if lines is None else lines
        paths = p2 if paths is None else paths
    mods = {}
    for n in lines:
        p = paths.get(n)
        if p and os.path.exists(p):
            mods[n] = {"md5": _h(p, "md5"), "src": _kind(p)}
    json.dump({"stamp": stamp or time.strftime("%Y%m%d_%H%M%S"), "count": len(mods), "mods": mods},
              open(MANIFEST, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    return len(mods)


def check_env(fails, warns, info):
    if not os.path.exists(BASELINE):
        init_env()
        warns.append("rules/env_baseline.json не было - записан текущий хэш как эталон (проверь вручную)")
    base = json.load(open(BASELINE, encoding="utf-8"))
    for k, (p, a) in env_files().items():
        if not os.path.exists(p):
            fails.append(f"нет файла {k}")
            continue
        want = base["files"].get(k)
        if not want:
            warns.append(f"{k}: в эталоне нет записи")
        elif _h(p, a) != want["hash"]:
            fails.append(f"{k}: хэш не совпал с эталоном" + (" (exe не откатан на 1.0.65 или обновился Steam-ом - запусти RE_Kenshi-установщик)" if k == "kenshi_x64.exe" else ""))
    if os.path.exists(EXE_BACKUP) and base.get("backup_exe_sha256") and _h(EXE_BACKUP, "sha256") != base["backup_exe_sha256"]:
        warns.append("backup/pre_rekenshi/kenshi_x64.exe изменился относительно эталона")
    if not os.path.exists(os.path.join(WORK, LUA_ID, "KenshiLua.mod")):
        fails.append(f"KenshiLua ({LUA_ID}) не найден на диске")
    if not os.path.exists(os.path.join(WORK, LUA_ID, "plugin", "KenshiLua.dll")):
        fails.append("KenshiLua plugin/KenshiLua.dll отсутствует")
    if not os.path.exists(MANIFEST):
        warns.append("rules/installed_manifest.json нет (появится после установки или --init-manifest)")
        return
    man = json.load(open(MANIFEST, encoding="utf-8"))["mods"]
    lines, paths = live_mods()
    changed, missing = [], []
    for n in lines:
        if n.startswith("KMM_"):
            continue   # свои собирает генератор; их ставит --install
        p = paths.get(n)
        if not p:
            missing.append(n)
            continue
        m = man.get(n)
        if m is None:
            changed.append(f"{n} (нет в манифесте)")
        elif _h(p, "md5") != m["md5"]:
            changed.append(f"{n} [{_kind(p)}]")
    info.append(f"манифест: {len(man)} модов, сверено {len(lines)}")
    if changed:
        warns.append(f"моды изменились с момента установки ({len(changed)}): " + "; ".join(changed[:15]) + (" ..." if len(changed) > 15 else ""))
    if missing:
        fails.append(f"моды из mods.cfg не найдены на диске: {missing[:10]}")


SANDBOX = os.path.join(ROOT, "tools", "test", "log_sandbox.py")   # B3 И9: тесты пишут logs/ в свою временную папку
LOGS = os.path.join(ROOT, "logs")


def sandbox_env():
    return dict(ENV, KMM_TEST_LOG_DIR=tempfile.mkdtemp(prefix="kmm_testlogs_"))


def logs_snapshot():
    """Размер и mtime живых logs/* (кроме verify_fail_*, их пишет сам verify_all)."""
    snap = {}
    for p in glob.glob(os.path.join(LOGS, "*")):
        n = os.path.basename(p)
        if os.path.isfile(p) and not n.startswith("verify_fail_"):
            st = os.stat(p)
            snap[n] = (st.st_size, st.st_mtime_ns)
    return snap


def logs_changed(before, after):
    return sorted(n for n in set(before) | set(after) if before.get(n) != after.get(n))


def run_test(f):
    t = time.time()
    with tempfile.TemporaryDirectory(prefix="kmm_testlogs_", ignore_cleanup_errors=True) as d:
        try:
            p = subprocess.run([sys.executable, "-I", "-X", "utf8", SANDBOX, f], cwd=os.path.dirname(f), capture_output=True, text=True,
                               encoding="utf-8", errors="replace", env=dict(ENV, KMM_TEST_LOG_DIR=d), timeout=300)
            return f, p.returncode, time.time() - t, p.stdout + p.stderr
        except subprocess.TimeoutExpired:
            return f, -1, time.time() - t, "таймаут 300 с"


def py(args, **kw):
    kw.setdefault("env", ENV)
    return subprocess.run([sys.executable, "-I", "-X", "utf8"] + args, capture_output=True, text=True, encoding="utf-8",
                          errors="replace", **kw)


def _last(r):
    t = (r.stdout + r.stderr).strip().splitlines()
    return t[-1][:200] if t else "код %d" % r.returncode


def build_checks(fails, info):
    """Последовательно (общий build/kmm_build_report.json): lua_lint, mods_cfg check, test_conflict, затем холостой kmm_build."""
    b = os.path.join(ROOT, "tools", "build")
    r = py([os.path.join(b, "lua_lint.py")])
    if r.returncode != 0:
        fails.append("lua_lint: " + _last(r))
    r = py([os.path.join(ROOT, "tools", "api_audit.py")])   # вызовы API и заглушки тестов против BindingsReference
    if r.returncode != 0:
        fails.append("api_audit: " + _last(r))
    # 2026-11-13: офлайн-прогон Lua на мире из реального сейва и аудит зон мира (снимковые откаты после KMM_Fix должны быть 0)
    r = py([SANDBOX, os.path.join(ROOT, "tools", "test", "save_replay.py"), "--days", "4"], timeout=600, env=sandbox_env())
    if r.returncode != 0:
        fails.append("save_replay: " + _last(r))
    r = py([os.path.join(ROOT, "tools", "zone_audit.py")], timeout=600)
    try:
        za = json.load(open(os.path.join(ROOT, "data", "zone_audit.json"), encoding="utf-8"))
        rl = za["rollbacks_left"]; nleft = rl.get("count", 0) if isinstance(rl, dict) else (rl if isinstance(rl, int) else len(rl))
        if r.returncode not in (0, 1) or nleft:
            fails.append("zone_audit: снимковых откатов после KMM_Fix %s (код %d)" % (nleft, r.returncode))
    except Exception as e:
        fails.append("zone_audit: отчёт не прочитан: %s" % e)
    r = py([os.path.join(b, "mods_cfg.py"), "check"])
    if r.returncode != 0:
        fails.append("mods_cfg check: " + _last(r))
    r = py([os.path.join(b, "test_conflict.py")], cwd=b)
    out = r.stdout + r.stderr
    if "СБОРКА ОСТАНОВЛЕНА" not in out or "EXIT 1" not in out:
        fails.append("test_conflict: искусственный конфликт потоков НЕ остановил сборку (защита сломана)")
    r = py([os.path.join(b, "kmm_build.py")], cwd=b)     # холостой: без --write
    rep = os.path.join(ROOT, "build", "kmm_build_report.json")
    try:
        errs = json.load(open(rep, encoding="utf-8"))["errors"]
    except Exception as e:
        errs = [f"нет отчёта сборки: {e}"]
    if r.returncode != 0 or errs:
        fails.append(f"kmm_build холостой: код {r.returncode}, errors={len(errs)} {errs[:3]} {_last(r)[:150]}")


def run(quiet=False):
    t0 = time.time()
    fails, warns, info = [], [], []
    check_env(fails, warns, info)
    files = sorted({f for g in TEST_GLOBS for f in glob.glob(os.path.join(ROOT, g))})
    logs0 = logs_snapshot()
    with cf.ThreadPoolExecutor(1) as bex, cf.ThreadPoolExecutor(8) as tex:
        bfut = bex.submit(build_checks, fails, info)       # сборочные проверки идут последовательно в своём потоке
        results = list(tex.map(run_test, files))
        bfut.result()
    changed = logs_changed(logs0, logs_snapshot())
    if changed:   # B3 И9: рост живого лога от тестов даёт ложные [+] в session_report
        fails.append("прогон изменил живые logs/ (тест пишет мимо песочницы или игра/другой процесс писал во время проверки): " + ", ".join(changed[:10]))
    for f, rc, dt, out in results:
        if rc != 0:
            name = os.path.splitext(os.path.basename(f))[0]
            try:   # полный вывод упавшего прогона — для разбора нестабильности
                os.makedirs(os.path.join(ROOT, "logs"), exist_ok=True)
                open(os.path.join(ROOT, "logs", f"verify_fail_{name}.log"), "w", encoding="utf-8").write(out)
            except OSError:
                pass
            _, rc2, _, out2 = run_test(f)   # повтор в одиночку: прошёл — нестабилен под нагрузкой (предупреждение), нет — настоящий провал
            if rc2 == 0:
                warns.append(f"нестабилен под параллельной нагрузкой: {os.path.relpath(f, ROOT)} (повтор прошёл; вывод logs/verify_fail_{name}.log)")
            else:
                fails.append(f"тест {os.path.relpath(f, ROOT)}: код {rc2} (и в повторе); " + " | ".join(out2.strip().splitlines()[-2:])[:200])
    dt = time.time() - t0
    if not quiet:
        for i in info:
            print("инфо:", i)
        for w in warns:
            print("ВНИМАНИЕ:", w)
        print(f"тестов: {len(files)}, время: {dt:.0f} с")
        for x in fails:
            print("ПРИЧИНА:", x)
        print("verify_all: " + ("FAIL (%d)" % len(fails) if fails else ("OK, предупреждений: %d" % len(warns) if warns else "OK")))
    return not fails, fails, warns


if __name__ == "__main__":
    if "--init-env" in sys.argv:
        print(json.dumps(init_env()["files"], indent=1))
    elif "--init-manifest" in sys.argv:
        print("манифест:", write_manifest(), "модов")
    else:
        sys.exit(0 if run()[0] else 1)
