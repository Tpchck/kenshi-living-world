"""Разбор тестового запуска → docs/TEST_V0.md.

python -I -X utf8 tools/test/analyze_test.py [run_dir]
Источники: logs/test_done.json (наблюдатель), run_dir/{kenshi_info.log,kenshi.log,RE_Kenshi_log.txt,*.dmp,app_events.json,mem.csv},
logs/ref_vanilla_spike1_1946 (эталонный «шум» ванили), Kenshi/data/mods.cfg, папки Workshop (привязка файлов к модам).
"""
import collections
import csv
import datetime as dt
import glob
import json
import os
import re
import struct
import sys

ROOT = r"C:\KenshiModMap"
LOGS = os.path.join(ROOT, "logs")
GAME = r"C:\Program Files (x86)\Steam\steamapps\common\Kenshi"
WS = r"C:\Program Files (x86)\Steam\steamapps\workshop\content\233860"
OUT_MD = os.path.join(ROOT, "docs", "TEST_V0.md")

DONE = sys.argv[2] if len(sys.argv) > 2 else os.path.join(LOGS, "test_done.json")
if len(sys.argv) > 3:
    OUT_MD = sys.argv[3]
done = json.load(open(DONE, encoding="utf-8-sig"))
RUN = sys.argv[1] if len(sys.argv) > 1 else done["run_dir"]
T0 = dt.datetime.strptime(done["test_start"], "%Y-%m-%d %H:%M:%S")


def rd(path):
    return open(path, encoding="utf-8", errors="replace").read() if os.path.exists(path) else ""


# --- mods.cfg и индекс файлов → мод ----------------------------------------------
cfg = [l for l in open(os.path.join(GAME, "data", "mods.cfg"), "rb").read().decode("utf-8", "replace").splitlines() if l.strip()]
mod_dir = {}  # имя .mod -> папка
for d in os.listdir(WS):
    for f in glob.glob(os.path.join(WS, d, "*.mod")):
        mod_dir[os.path.basename(f)] = os.path.join(WS, d)
for d in os.listdir(os.path.join(GAME, "mods")):
    for f in glob.glob(os.path.join(GAME, "mods", d, "*.mod")):
        mod_dir[os.path.basename(f)] = os.path.join(GAME, "mods", d)
file_owner = collections.defaultdict(list)  # basename(lower) -> [mod]
for m in cfg:
    d = mod_dir.get(m)
    if not d:
        continue
    for dp, _, fs in os.walk(d):
        for f in fs:
            file_owner[f.lower()].append(m)
mod_stem = {m[:-4].lower(): m for m in cfg}


def owner_of(text):
    """Привязка строки лога к модам: sid вида N-Имя.mod, имена файлов (mesh/dds/dll/…), имена модов."""
    hits = []
    for sid_mod in re.findall(r"\d+-([^\s'\"(),]+?\.mod)", text):
        hits.append(sid_mod if sid_mod in cfg or sid_mod in ("gamedata.base",) else sid_mod + " (нет в mods.cfg)")
    for fn in re.findall(r"([\w\-. \[\]()']+\.(?:mesh|dds|png|tga|skeleton|xml|phs|bod2|dll|lua|material|bnk|hkx))", text, re.I):
        fn = fn.strip().split("/")[-1].split("\\")[-1].lower()
        if fn in file_owner:
            hits += file_owner[fn][:3]
    for stem, m in mod_stem.items():
        if len(stem) > 5 and stem in text.lower():
            hits.append(m)
    return sorted(set(hits))


# --- kenshi_info.log ------------------------------------------------------------------
LINE = re.compile(r"^\{0x[0-9a-f]+\} (\d{4}-\d\d-\d\d \d\d:\d\d:\d\d) \[(\w+)\]: (.*)$")


def parse_info(text):
    out = []
    for l in text.splitlines():
        m = LINE.match(l)
        if m:
            out.append((dt.datetime.strptime(m.group(1), "%Y-%m-%d %H:%M:%S"), m.group(2), m.group(3)))
    return out


def norm(msg):  # для сравнения с эталоном: убрать числа
    return re.sub(r"\d+", "#", msg)


info = parse_info(rd(os.path.join(RUN, "kenshi_info.log")))
ref = parse_info(rd(os.path.join(LOGS, "ref_vanilla_spike1_1946", "kenshi_info.log")))
ref_noise = {norm(m) for _, lv, m in ref if lv in ("error", "warning")}


def first(pred):
    return next((t for t, _, m in info if pred(m)), None)


marks = {
    "kenshi_start": first(lambda m: "Kenshi start" in m),
    "launch_game": first(lambda m: "[Launcher] Launching game" in m),
    "gamedata_init": first(lambda m: m.startswith("Initialising GameData")),
    "title_screen": first(lambda m: m.startswith("Starting Title Screen")),
    "new_game": first(lambda m: "[Game] New game start" in m),
    "load_game": first(lambda m: "[Game] Load" in m or "Loading game" in m),
    "last_line": info[-1][0] if info else None,
}
loaded_mods = [m.split(": ", 1)[1] for _, _, m in info if m.startswith("[Mods] Loaded mod: ")]
cfg_stems = [m[:-4] for m in cfg]
not_loaded = [m for m in cfg_stems if m not in loaded_mods]
start_name = next((m.split("'")[1] for _, _, m in info if "[Game] New game start" in m and "'" in m), None)

lv_count = collections.Counter(lv for _, lv, _ in info)
issues = collections.OrderedDict()
for t, lv, m in info:
    if lv not in ("error", "warning"):
        continue
    k = (lv, norm(m))
    if k not in issues:
        issues[k] = {"level": lv, "example": m, "count": 0, "first": t, "vanilla_noise": norm(m) in ref_noise, "mods": owner_of(m)}
    issues[k]["count"] += 1

# --- kenshi.log (Ogre) -----------------------------------------------------------------
ogre = rd(os.path.join(RUN, "kenshi.log")).splitlines()
OGRE_RX = r"exception|error|cannot|can't|failed|not found|missing"
ogre_ref = {norm(re.sub(r"^\d\d:\d\d:\d\d: ", "", l)) for l in rd(os.path.join(LOGS, "ref_vanilla_spike1_1946", "kenshi.log")).splitlines()
            if re.search(OGRE_RX, l, re.I)}
ogre_bad = collections.Counter()
ogre_ex = {}
ogre_noise = 0
for l in ogre:
    if re.search(OGRE_RX, l, re.I):
        k = norm(re.sub(r"^\d\d:\d\d:\d\d: ", "", l))
        if k in ogre_ref:
            ogre_noise += 1
            continue
        ogre_bad[k] += 1
        ogre_ex.setdefault(k, l)
ogre_tail = ogre[-15:]

# --- RE_Kenshi_log.txt -------------------------------------------------------------------
rek_text = rd(os.path.join(RUN, "RE_Kenshi_log.txt"))
rek_lines = rek_text.splitlines()
rek_bad = [l for l in rek_lines if re.search(r"error|fail|exception|could not|unable|crash|missing", l, re.I)]
rek_plugins = [l for l in rek_lines if re.search(r"plugin", l, re.I)]

# --- память ----------------------------------------------------------------------------------
mem = []
mp = os.path.join(RUN, "mem.csv") if os.path.exists(os.path.join(RUN, "mem.csv")) else os.path.join(LOGS, "mem.csv")
with open(mp, encoding="utf-8-sig") as f:
    for r in csv.DictReader(f):
        try:
            t = dt.datetime.strptime(r["time"], "%Y-%m-%d %H:%M:%S")
        except ValueError:
            continue
        if t >= T0:
            mem.append((t, float(r["working_set_mb"]), float(r["private_mb"]), float(r["peak_working_set_mb"])))
peak_ws = max((x[3] for x in mem), default=0)
peak_priv = max((x[2] for x in mem), default=0)


def plateau_after(t_from):
    """Момент, после которого Private растёт <1% за 30 с (≈ конец загрузки мира)."""
    if not t_from:
        return None
    pts = [x for x in mem if x[0] >= t_from]
    for i, (t, _, p, _) in enumerate(pts):
        later = [x for x in pts[i:] if (x[0] - t).total_seconds() <= 30]
        if len(later) >= 6 and max(x[2] for x in later) <= p * 1.01:
            return t
    return None


world_ready = plateau_after(marks["new_game"] or marks["load_game"])

# --- minidump ---------------------------------------------------------------------------------
EXC = {0xC0000005: "ACCESS_VIOLATION", 0xC00000FD: "STACK_OVERFLOW", 0xC0000409: "STACK_BUFFER_OVERRUN",
       0xC0000374: "HEAP_CORRUPTION", 0xE06D7363: "C++ exception", 0x80000003: "BREAKPOINT", 0xC0000017: "NO_MEMORY",
       0xC000001D: "ILLEGAL_INSTRUCTION", 0xC0000094: "INT_DIVIDE_BY_ZERO"}


def minidump(path):
    b = open(path, "rb").read()
    if b[:4] != b"MDMP":
        return {"file": path, "error": "не minidump"}
    nstreams, rva = struct.unpack_from("<II", b, 8)
    streams = {}
    for i in range(nstreams):
        st, size, srva = struct.unpack_from("<III", b, rva + 12 * i)
        streams[st] = (size, srva)

    def mstr(r):
        n = struct.unpack_from("<I", b, r)[0]
        return b[r + 4:r + 4 + n].decode("utf-16-le", "replace")
    mods = []
    if 4 in streams:
        _, r = streams[4]
        n = struct.unpack_from("<I", b, r)[0]
        for i in range(n):
            o = r + 4 + 108 * i
            base, size = struct.unpack_from("<QI", b, o)
            name_rva = struct.unpack_from("<I", b, o + 20)[0]
            mods.append((base, size, mstr(name_rva)))
    res = {"file": os.path.basename(path)}
    if 6 in streams:
        _, r = streams[6]
        tid = struct.unpack_from("<I", b, r)[0]
        code, flags, rec, addr = struct.unpack_from("<IIQQ", b, r + 8)
        mod = next((m for m in mods if m[0] <= addr < m[0] + m[1]), None)
        res.update({"thread": tid, "code": f"0x{code:08X}", "code_name": EXC.get(code, "?"), "address": f"0x{addr:X}",
                    "module": os.path.basename(mod[2]) if mod else "?", "offset": f"0x{addr - mod[0]:X}" if mod else "?"})
    res["modules_loaded"] = len(mods)
    res["plugin_modules"] = sorted({os.path.basename(m[2]) for m in mods if "workshop" in m[2].lower() or "\\mods\\" in m[2].lower()})
    return res


dumps = [minidump(p) for p in glob.glob(os.path.join(RUN, "*.dmp"))]
for d in dumps:
    d["owner_mods"] = file_owner.get(d.get("module", "").lower(), [])
other_crash = [os.path.relpath(p, RUN) for p in glob.glob(os.path.join(RUN, "**", "*.zip"), recursive=True)]

# --- события Windows ------------------------------------------------------------------------
ev_raw = rd(os.path.join(RUN, "app_events.json")).lstrip("\ufeff").strip()
events = json.loads(ev_raw) if ev_raw else []
events = events if isinstance(events, list) else [events]
ev_parsed = []
for e in events:
    msg = e.get("message", "")
    fm = re.search(r"Faulting module name: ([^,\r\n]+)", msg)
    ec = re.search(r"Exception code: (0x[0-9a-fA-F]+)", msg)
    off = re.search(r"Fault offset: (0x[0-9a-fA-F]+)", msg)
    ev_parsed.append({"time": e.get("time"), "id": e.get("id"), "provider": e.get("provider"),
                      "module": fm.group(1).strip() if fm else None, "code": ec.group(1) if ec else None,
                      "offset": off.group(1) if off else None,
                      "owner_mods": file_owner.get(fm.group(1).strip().lower(), []) if fm else []})

# --- вывод ----------------------------------------------------------------------------------
sess = done.get("sessions") or []
sess = sess if isinstance(sess, list) else [sess]
crashed = any(str(s.get("exit_code")) not in ("0", "None") for s in sess) or dumps or any(e["id"] == 1000 for e in ev_parsed)


def dur(a, b):
    return f"{int((b - a).total_seconds())} с" if a and b else "—"


L = [f"# TEST_V0 — тестовый запуск сборки ({done['test_start']})", ""]
L.append(f"Артефакты: `{RUN}`. Анализатор: `tools\\test\\analyze_test.py`.")
L.append("")
L.append("## Итог")
for s in sess:
    L.append(f"- Процесс pid {s.get('pid')}: старт {s.get('start')}, выход {s.get('exit')}, код {s.get('exit_code')} ({s.get('exit_code_hex')}).")
L.append(f"- **{'КРАШ' if crashed else 'Штатный выход'}**. Старт игры: {start_name or '—'}.")
L.append(f"- Загрузка: запуск → лаунчер «Launch» {dur(marks['kenshi_start'], marks['launch_game'])}; "
         f"данные модов → главное меню {dur(marks['gamedata_init'], marks['title_screen'])}; "
         f"новая игра/загрузка → мир готов (плато памяти) {dur(marks['new_game'] or marks['load_game'], world_ready)}.")
L.append(f"- Пиковая память: Working Set {peak_ws:.0f} МБ, Private {peak_priv:.0f} МБ (ОЗУ 16 ГБ).")
L.append(f"- Модов в mods.cfg {len(cfg)}, загружено по логу {len(loaded_mods)}; не загрузились: {len(not_loaded)}"
         + (f" — {', '.join(not_loaded[:15])}" if not_loaded else ""))
L.append(f"- kenshi_info.log: error {lv_count.get('error', 0)}, warning {lv_count.get('warning', 0)}; "
         f"новых типов (нет в эталоне ванили) {sum(1 for i in issues.values() if not i['vanilla_noise'])}.")
L.append("")
if crashed:
    L.append("## Краш")
    for d in dumps:
        L.append(f"- Дамп `{d['file']}`: {d.get('code')} {d.get('code_name')} в `{d.get('module')}`+{d.get('offset')}; "
                 f"мод-владелец модуля: {', '.join(d['owner_mods']) or 'не мод (движок/система)'}; плагинов в процессе: {len(d.get('plugin_modules', []))}.")
    for e in ev_parsed:
        L.append(f"- Событие {e['id']} ({e['provider']}, {e['time']}): модуль `{e['module']}`, код {e['code']}, смещение {e['offset']}; мод: {', '.join(e['owner_mods']) or '—'}.")
    if other_crash:
        L.append(f"- Архивы краша RE_Kenshi: {', '.join(other_crash)}")
    L.append("- Последние строки kenshi_info.log:")
    L += [f"  - `{m[:200]}`" for _, _, m in info[-8:]]
    L.append("- Последние строки kenshi.log:")
    L += [f"  - `{x[:200]}`" for x in ogre_tail[-8:]]
    L.append("")
L.append("## Ошибки и предупреждения kenshi_info.log (без ванильного шума)")
L.append("| Уровень | Кол-во | Первый раз | Пример | Мод(ы) |")
L.append("|---|---|---|---|---|")
for i in sorted(issues.values(), key=lambda x: (x["vanilla_noise"], x["level"] != "error", -x["count"])):
    if i["vanilla_noise"]:
        continue
    L.append(f"| {i['level']} | {i['count']} | {i['first']:%H:%M:%S} | `{i['example'][:150].replace('|', '/')}` | {', '.join(i['mods'][:3]) or '—'} |")
noise = [i for i in issues.values() if i["vanilla_noise"]]
L.append(f"\nВанильный шум (есть и в эталоне 19:46): {len(noise)} типов, {sum(i['count'] for i in noise)} строк.")
L.append("")
L.append("## RE_Kenshi_log.txt")
if rek_text:
    L.append(f"Строк {len(rek_lines)}, про плагины {len(rek_plugins)}, проблемных {len(rek_bad)}.")
    L += [f"- `{l[:200]}` — {', '.join(owner_of(l)[:3]) or '—'}" for l in rek_bad[:40]]
else:
    L.append("Файл не найден в артефактах.")
L.append("")
L.append(f"## kenshi.log (Ogre): частые проблемы (ванильный шум отброшен: {ogre_noise} строк)")
for k, n in ogre_bad.most_common(15):
    L.append(f"- ×{n} `{ogre_ex[k][:180]}` — {', '.join(owner_of(ogre_ex[k])[:3]) or '—'}")
L.append("")
L.append("## Память (каждые 5 с)")
if mem:
    step = max(1, len(mem) // 12)
    L.append("| Время | Working Set, МБ | Private, МБ |")
    L.append("|---|---|---|")
    L += [f"| {t:%H:%M:%S} | {w:.0f} | {p:.0f} |" for t, w, p, _ in mem[::step]]
open(OUT_MD, "w", encoding="utf-8").write("\n".join(L) + "\n")
print("\n".join(L[:14]))
print("→", OUT_MD)
