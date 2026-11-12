r"""Разбор логов после сессии игрока (RELY): python -I -X utf8 tools\health.py   (<= 10 с, только чтение, в папку игры ничего не пишет)

Читает: Kenshi\RE_Kenshi_log.txt, Kenshi\kenshi.log, ...\workshop\content\233860\3817000612\logs\KenshiLua.log.
Выводит краткий отчёт по-русски: время сессии, плагины RE_Kenshi, строки KMM_Native, ошибки Lua, отключённые модули KMM_*
(«disabled until restart»), троттлинг KMM_Gov, исключения/краш в kenshi.log. Пользователю логи присылать не нужно.
"""
import collections
import glob
import os
import re
import sys
import time

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

GAME = r"C:\Program Files (x86)\Steam\steamapps\common\Kenshi"
LUA_LOG = r"C:\Program Files (x86)\Steam\steamapps\workshop\content\233860\3817000612\logs\KenshiLua.log"
RE_LOG = os.path.join(GAME, "RE_Kenshi_log.txt")
K_LOG = os.path.join(GAME, "kenshi.log")
MODS = os.path.join(GAME, "mods")


def rd(p):
    try:
        return open(p, "rb").read().decode("utf-8", "replace").splitlines()
    except OSError:
        return None


def ts(p):
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(os.path.getmtime(p)))


def short(s, n=170):
    s = s.strip()
    return s if len(s) <= n else s[:n] + "..."


def main():
    t0 = time.time()
    out, bad = [], 0
    install_m = max([os.path.getmtime(p) for p in glob.glob(os.path.join(MODS, "KMM_*", "KMM_*.mod"))] or [0])
    out.append("health: разбор логов (только чтение)")

    # --- KenshiLua.log: берём последнюю сессию ---
    lua = rd(LUA_LOG)
    if lua is None:
        out.append("KenshiLua.log: нет файла")
        bad += 1
        lua = []
    starts = [i for i, l in enumerate(lua) if "KenshiLua logger initialized" in l]
    lua = lua[starts[-1]:] if starts else lua
    t_first = lua[0][:19] if lua else "?"
    t_last = lua[-1][:19] if lua else "?"
    if lua:
        age = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(os.path.getmtime(LUA_LOG)))
        out.append(f"последняя сессия: {t_first} .. {t_last} (лог обновлён {age})")
        if os.path.getmtime(LUA_LOG) < install_m:
            out.append("  сессия была ДО последней установки KMM_* (" + time.strftime("%Y-%m-%d %H:%M", time.localtime(install_m)) + "): новые модули/плагин в ней не участвовали")
    # загрузка скриптов
    loaded = {m.group(1) for l in lua for m in [re.search(r"ScriptLoader: loaded @(\S+)", l)] if m}
    m = next((re.search(r"discovered (\d+) script\(s\) across (\d+) active", l) for l in lua if "discovered" in l), None)
    if m:
        out.append(f"KenshiLua: найдено скриптов {m.group(1)} в {m.group(2)} активных модах, загружено {len(loaded)}")
    expect = set()
    for p in glob.glob(os.path.join(MODS, "KMM_*", "scripts", "init", "*.lua")):
        parts = p.split(os.sep)
        expect.add(f"{parts[-4]}/scripts/init/{parts[-1]}")
    miss = sorted(e for e in expect if e not in loaded)
    if lua and miss:
        out.append("  KMM-скрипты установлены, но в логе не загружены: " + ", ".join(miss))
        if os.path.getmtime(LUA_LOG) >= install_m:
            bad += 1
    # отключения и ошибки
    dis = [l for l in lua if "disabled until restart" in l]
    if dis:
        bad += 1
        out.append(f"отключились до перезапуска ({len(dis)}):")
        for l in dis:
            m = re.search(r"\[(KMM_\w+)\] (\S+) disabled until restart: (.*)", l)
            out.append("  " + (f"{m.group(1)}.{m.group(2)}: {short(m.group(3), 150)}" if m else short(l[24:])))
    else:
        out.append("отключений модулей KMM_*: нет")
    errs = [l for l in lua if "[ERROR]" in l or "[ERR]" in l]
    warns = [l for l in lua if "[WARN]" in l]
    other = [l for l in lua if re.search(r"KMM_\w+\].*(unavailable|error|failed|exception)", l, re.I) and "disabled until restart" not in l]
    if errs:
        bad += 1
        out.append(f"ошибки Lua ({len(errs)}):")
        out += ["  " + short(l[24:]) for l in errs[:8]]
    else:
        out.append("ошибок Lua [ERROR]: нет")
    if other:
        out.append(f"прочие проблемы KMM ({len(other)}):")
        out += ["  " + short(l[24:]) for l in other[:6]]
    out.append(f"предупреждений [WARN]: {len(warns)}")
    gov = [l for l in lua if "KMM_Gov" in l and ("throttle" in l or "recover" in l or "disabled" in l)]
    if gov:
        cnt = collections.Counter(re.sub(r"^\S+ \S+ ", "", re.sub(r"\d+(\.\d+)?", "N", l[24:]))[:90] for l in gov)
        out.append(f"KMM_Gov троттлинг ({len(gov)} строк):")
        out += [f"  {n}x {k}" for k, n in cnt.most_common(5)]
    else:
        out.append("KMM_Gov: троттлинга в логе нет")

    # --- RE_Kenshi_log.txt ---
    re_l = rd(RE_LOG)
    if re_l is None:
        out.append("RE_Kenshi_log.txt: нет файла")
        bad += 1
        re_l = []
    plugins = [l for l in re_l if re.match(r"[\d.]+ RE_Kenshi: .+ -> ", l) and "Override" not in l]
    overrides_from = {m.group(1) for l in re_l for m in [re.search(r'Loading mod overrides from "(.+?)"', l)] if m}
    plug_names = {re.match(r"[\d.]+ RE_Kenshi: (.+?) -> ", l).group(1) for l in plugins}
    ver = next((l.split("RE_Kenshi: ", 1)[1] for l in re_l if "RE_Kenshi: RE_Kenshi " in l), "?")
    last_t = re_l[-1].split(" ", 1)[0] if re_l else "?"
    out.append(f"RE_Kenshi: {ver}, плагинов загружено {len(plug_names)}, лог до {last_t} с от старта, обновлён {ts(RE_LOG) if re_l else '?'}")
    noload = sorted(overrides_from - plug_names - {"Terrain Fog Overhaul", "Heightmap Fix"})
    if noload:
        out.append("  в списке RE_Kenshi без строки загрузки dll (возможно, только оверрайды): " + ", ".join(noload[:10]))
    hookerr = [l for l in re_l if (l.startswith("Error") or re.search(r"\b(failed|could not|cannot|exception)\b", l, re.I))
               and "failed='-'" not in l and "Override" not in l and "NGX init failed" not in l and "crash reporting" not in l]
    if hookerr:
        out.append(f"RE_Kenshi ошибки/сбои хуков ({len(hookerr)}):")
        out += ["  " + short(l) for l in hookerr[:8]]
    else:
        out.append("RE_Kenshi: ошибок хуков нет")
    nat = [l for l in re_l + (rd(K_LOG) or []) + lua if "KMM_Native" in l and "KMM_Native/scripts" not in l]
    if nat:
        out.append(f"KMM_Native ({len(nat)} строк):")
        seen = set()
        for l in nat:
            k = re.sub(r"^[\d.:\s-]+", "", l)
            if k not in seen:
                seen.add(k)
                out.append("  " + short(l))
        if any(re.search(r"nothing hooked|skipped|failed|not found|disabled|not supported", l, re.I) for l in nat):
            bad += 1
            out.append("  есть отказы/пропуски хуков - см. выше")
        if not any("hook installed" in l for l in nat):
            out.append("  строки 'hook installed' нет (ws_hook выключен или отказ)")
    else:
        out.append("KMM_Native: строк в логах нет" + (" (сессия была до установки плагина)" if os.path.exists(LUA_LOG) and os.path.getmtime(LUA_LOG) < install_m else " - плагин не загрузился или не писал"))

    # --- kenshi.log ---
    k = rd(K_LOG)
    if k is None:
        out.append("kenshi.log: нет файла")
        k = []
    exc = collections.Counter()
    for l in k:
        m = re.search(r"OGRE EXCEPTION\((\d+):(\w+)\)", l)
        if m:
            exc[m.group(2)] += 1
    crash = [l for l in k if re.search(r"access violation|unhandled|assertion|fatal|crash dump|stack trace|0xC0000", l, re.I)]
    out.append(f"kenshi.log: {len(k)} строк, до {k[-1][:8] if k else '?'}, обновлён {ts(K_LOG) if k else '?'}; OGRE-исключения: " +
               (", ".join(f"{a} {b}" for a, b in exc.most_common(4)) if exc else "нет") + " (текстуры/скелеты чужих модов - шум)")
    if crash:
        bad += 1
        out.append(f"  признаки краша ({len(crash)}):")
        out += ["  " + short(l) for l in crash[:5]]
    else:
        out.append("  признаков краша в kenshi.log нет")
    for d in glob.glob(os.path.join(GAME, "crashDump*")):
        if os.path.getmtime(d) > install_m - 10 * 86400 and os.path.getmtime(d) > os.path.getmtime(K_LOG) - 3600:
            out.append("  свежий crashDump: " + os.path.basename(d) + " " + ts(d) + "  -> КРАШ; разбор: python tools/mdmp.py <распакованный .dmp>")
            bad += 1   # 2026-11-13: краш с дампом не должен давать «критичного нет»
    out.append(("ИТОГ: есть что разобрать (" + str(bad) + " групп)") if bad else "ИТОГ: критичного в логах нет")
    out.append(f"({time.time() - t0:.1f} с)")
    print("\n".join(out))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
