"""ЗАПУСК ИГРЫ ОТОЗВАН владельцем 2026-11-12 23:40 — функции запуска удалены (W1, 2026-11-15); остался только разбор логов.

python tools\\smoke.py [--report]   — разбор логов последней игровой сессии (RE_Kenshi, KenshiLua) → logs\\smoke_last.txt
"""
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = r"C:\KenshiModMap"
GAME = r"C:\Program Files (x86)\Steam\steamapps\common\Kenshi"
RELOG = os.path.join(GAME, "RE_Kenshi_log.txt")
LUALOG = r"C:\Program Files (x86)\Steam\steamapps\workshop\content\233860\3817000612\logs\KenshiLua.log"
KMM_SCRIPTS = ("KMM_Conductor", "KMM_Traces", "KMM_Stock", "KMM_Town", "KMM_Native", "KMM_Diplo", "KMM_Ore", "KMM_Rumors", "kmm_elite")


def read(p):
    try:
        return open(p, "rb").read().decode("utf-8", "replace")
    except OSError:
        return ""


def report(extra=None, state=None):
    re_log, lua = read(RELOG), read(LUALOG)
    lines = []
    ok = state in (None, "menu")   # закрылась сама / не дошла до меню = провал
    if "Crash detected" in re_log or "Assertion failed" in re_log:
        ok = False
    if extra:
        lines += extra
    # плагины RE_Kenshi
    native = [l for l in re_log.splitlines() if "KMM_Native" in l]
    lines.append("KMM_Native: " + (" | ".join(x.split(":", 1)[-1].strip() for x in native[-4:]) if native else "нет строк в логе RE_Kenshi"))
    fails = [l for l in re_log.splitlines() if re.search(r"(?i)fail|error|exception", l) and "crash reporting ready" not in l]
    lines.append(f"RE_Kenshi: строк с fail/error {len(fails)}")
    lines += ["  " + l[:200] for l in fails[:12]]
    # Lua
    loaded = [s for s in KMM_SCRIPTS if re.search(r"ScriptLoader: loaded @[^\n]*" + re.escape(s), lua, re.I)]
    lines.append("KenshiLua: загружены " + ", ".join(loaded) if loaded else "KenshiLua: скрипты KMM не загружены")
    errs = [l for l in lua.splitlines() if re.search(r"(?i)disabled until restart|error|attempt to|bad argument|stack traceback", l)]
    if errs:
        ok = False
    lines.append(f"KenshiLua: ошибок/отключений {len(errs)}")
    lines += ["  " + l[:220] for l in errs[:25]]
    if not loaded:
        ok = False
    txt = ("SMOKE OK" if ok else "SMOKE FAIL") + "\n" + "\n".join(lines)
    os.makedirs(os.path.join(ROOT, "logs"), exist_ok=True)
    open(os.path.join(ROOT, "logs", "smoke_last.txt"), "w", encoding="utf-8").write(txt)
    print(txt)
    return ok


FLAG = os.path.join(ROOT, "logs", "smoke_load.txt")   # флаг смоук-хука KMM_Native.lua (бывший --world): хвост удаляем


if __name__ == "__main__":
    if os.path.exists(FLAG):
        os.remove(FLAG)   # хвост прерванного смоука: игра владельца не должна сама грузить сейв
    sys.exit(0 if report() else 1)
