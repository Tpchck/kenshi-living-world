"""Самопроверка session_report (B3 И8): маркеры не врут.
1) каждый маркер MARKERS встречается в исходниках Lua (вне строк-комментариев) модулей, которые пишут в указанный лог;
   если строка маркера уходит только в KenshiLua.log (KC.log / local log без записи в файл), а маркер ищется в другом логе — FAIL;
2) KenshiLua.log читается по абсолютному пути папки KenshiLua;
3) лог без меток времени, изменённый в сессии, не «молчит»: явный отказ (smell api unavailable) -> [!] СЛОМАНО;
   с записью размеров прошлого отчёта берутся только новые строки; не менявшийся лог -> молчит;
4) всплеск одинаковых строк в одну секунду (офлайн-тест) в счёт не идёт; asks=0 во всех строках -> [0].
python -I -X utf8 tools/test/test_session_report.py -> ALL OK / FAIL (код 1)."""
import datetime
import glob
import json
import os
import re
import sys
import tempfile

sys.path.insert(0, r"C:\KenshiModMap\tools")
import session_report as S  # noqa: E402

BUILD = r"C:\KenshiModMap\build"
FAILS = []


def check(c, m):
    print(("OK   " if c else "FAIL ") + m)
    if not c:
        FAILS.append(m)


# --- 1. маркеры против исходников
SRC = {}
for p in glob.glob(BUILD + r"\KMM_*\scripts\**\*.lua", recursive=True):
    txt = open(p, encoding="utf-8", errors="replace").read()
    SRC[p] = (txt, "\n".join(l for l in txt.splitlines() if not l.lstrip().startswith("--")))


def writers(logname):
    if logname == "KenshiLua.log":   # все модули: KC.log и local log() каждого пишут туда
        return list(SRC)
    if logname == "debug.log":
        return [p for p, (t, _) in SRC.items() if "debug.log" in t or "debug_log" in t]
    if logname == "chronicle.log":
        return [p for p, (t, _) in SRC.items() if "chronicle" in t]
    return [p for p, (t, _) in SRC.items() if logname in t]


def kenshilua_only(fn, txt):
    """Логгер пишет только в KenshiLua.log: тело содержит KenshiLua.log и не пишет файл."""
    if fn == "KC.log":
        m = re.search(r"function KC\.log\(.*?\n\s*end\b|function KC\.log\(.*?\bend\n", "\n".join(t for t, _ in SRC.values()), re.S)
    else:
        m = re.search(r"local function " + re.escape(fn) + r"\(.*?(\n\s*end\b|\bend\n)", txt, re.S)
    if not m:
        return False
    body = m.group(0)
    return "KenshiLua.log" in body and not re.search(r"io\.open|append_file|dlog\(|:write\(", body)


def caller(line, pos):
    """Имя логгера, в аргументах которого стоит строка маркера: последний вызов перед ней, кроме string.format/tostring."""
    pre = re.sub(r'"(?:[^"\\]|\\.)*"' + "|" + r"'(?:[^'\\]|\\.)*'", '""', line[:pos])   # «player (» внутри строки — не вызов
    pre = re.split(r"[\"']", pre.replace('""', "\x01"))[0].replace("\x01", '""')   # открытая строка с маркером — отрезать
    names = [m.group(1) for m in re.finditer(r"([\w.:]+)\s*\(", pre)]
    names = [n for n in names if n not in ("string.format", "tostring", "format", "S", "string.rep")]
    return names[-1] if names else None


WILD = chr(0)
LIT = re.compile(r'"((?:[^"\\]|\\.)*)"' + "|" + r"'((?:[^'\\]|\\.)*)'")
SPEC = re.compile(r"%[-+ #0]*\d*(?:\.\d+)?[sdfiqgxXc]")


def templates(code):
    """Строки кода -> шаблоны: текст строковых литералов как есть, %-спецификаторы и код между литералами — подстановка (WILD)."""
    out = []
    for l in code.splitlines():
        lits = list(LIT.finditer(l))
        if lits:
            t = WILD.join(SPEC.sub(WILD, (m.group(1) if m.group(1) is not None else m.group(2)).replace("\\t", "\t")) for m in lits)
            out.append(WILD + t + WILD)
    return out


def fits(stem, t):
    """stem — подстрока какой-то подстановки шаблона t, и литералом шаблона покрыто не меньше половины stem (минимум 3 знака)."""
    n, m, best = len(stem), len(t), -1
    for j0 in range(m):
        if t[j0] != WILD and t[j0] != stem[0]:
            continue
        cur, j = {0: 0}, j0
        while j < m and cur:
            nxt = {}
            for i, c in cur.items():
                if t[j] == WILD:
                    for k in range(i, n + 1):   # подстановка съедает stem[i:k]
                        nxt[k] = max(nxt.get(k, -1), c)
                elif stem[i] == t[j]:
                    nxt[i + 1] = max(nxt.get(i + 1, -1), c + 1)
            if n in nxt:
                best = max(best, nxt[n])
            cur = {i: c for i, c in nxt.items() if i < n}
            j += 1
    return best >= max(3, (n + 1) // 2)


def in_source(stem, p):
    """Маркер в исходнике: дословно; по шаблону строки (format / ..); или по частям — строка собирается в помощнике
    (CA.log добавляет «campaign: », y2_fail(what) — «PROSPERITY » .. what): каждое слово маркера есть в литералах файла."""
    code = SRC[p][1]
    if stem in code or any(fits(stem, t) for t in templates(code) if stem[:3] in t):
        return True
    lits = " ".join(t.replace(WILD, " ") for t in templates(code))
    words = [w for w in re.findall(r"[A-Za-z_]{3,}", stem)]
    return bool(words) and all(re.search(r"(?<![A-Za-z_])" + re.escape(w) + r"(?![A-Za-z_])", lits) for w in words)


for f, sub, what, *rest in S.MARKERS:
    stem = sub.strip("\t ")
    ws = writers(f)
    found = [p for p in ws if in_source(stem, p)]
    check(bool(found), f"маркер [{f}] «{stem}» есть в исходниках модулей, пишущих этот лог ({len(ws)} файлов)")
    if found and f != "KenshiLua.log":
        calls = []
        for p in found:
            for l in SRC[p][1].splitlines():
                i = l.find(stem)
                if i >= 0:
                    calls.append((p, caller(l, i)))
        calls = [(p, c) for p, c in calls if c]   # строка не в вызове (return/таблица сценария) — не запись лога
        only_lua = bool(calls) and all(kenshilua_only(c, SRC[p][0]) for p, c in calls)
        check(not only_lua, f"маркер [{f}] «{stem}» пишется не только в KenshiLua.log ({sorted({c for _, c in calls if c})[:3]})")
    if rest:
        check(re.compile(rest[0]).groups == 1, f"маркер «{stem}»: регекс значения с одной группой")

# --- 2. путь KenshiLua.log
check(os.path.isabs(S.LUALOG) and S.LUALOG.lower().endswith(r"3817000612\logs\kenshilua.log"), "KenshiLua.log: абсолютный путь в папке KenshiLua")
check(S.log_path("KenshiLua.log") == S.LUALOG and S.log_path("debug.log") == os.path.join(S.LOGS, "debug.log"), "log_path: KenshiLua.log и logs/*")

# --- 3-4. разбор на временной папке
tmp = tempfile.mkdtemp(prefix="kmm_srtest_")
S.LOGS, S.OFFSETS = tmp, os.path.join(tmp, "session_offsets.json")
now = datetime.datetime.now().replace(microsecond=0)
t0 = now - datetime.timedelta(hours=1)
old = now - datetime.timedelta(hours=3)
ts = lambda d: d.strftime("%Y-%m-%d %H:%M:%S")  # noqa: E731
open(os.path.join(tmp, "predators.log"), "w", encoding="utf-8").write(
    "smell bus subscribed: 3/3\nsmell api unavailable (zoneMgr/zoneSmell): nil -> smell off, fallbacks only\n")
open(os.path.join(tmp, "chronicle.log"), "w", encoding="utf-8").write("1.0\t1\tblack_market\ta\tb\n")
os.utime(os.path.join(tmp, "chronicle.log"), (old.timestamp(), old.timestamp()))
dbg = [f"{ts(old)} [KMM_Self] KO release: x asks=3 (override calls=3)"]
dbg += [f"{ts(now - datetime.timedelta(minutes=5))} [KMM_Self] KO hold: override registered at load"] * 26
dbg += [f"{ts(now - datetime.timedelta(minutes=4))} [KMM_Self] KO hold: override registered at load",
        f"{ts(now - datetime.timedelta(minutes=3))} [KMM_Self] KO release: b2 why=timeout held=30s asks=0 (override calls=0 miss_me=0)"]
open(os.path.join(tmp, "debug.log"), "w", encoding="utf-8").write("\n".join(dbg) + "\n")
S._CACHE.clear()
M = {(m[0], m[1]): m for m in S.MARKERS}
st, n, note = S.marker_status(M[("predators.log", "smell api unavailable")], t0)
check(st == "!" and "СЛОМАНО" in note and n.startswith("≈"), f"лог без меток, изменён в сессии: smell api unavailable -> [!] СЛОМАНО ({st} {n})")
ls, mode = S.session_lines("chronicle.log", t0)
check(mode == "old" and not ls, f"лог без меток, не менялся с начала сессии -> молчит ({mode})")
st, n, _ = S.marker_status(M[("debug.log", "override registered at load")], t0)
check(st == "+" and n == "1", f"всплеск 26 строк в секунду отброшен, реальная строка осталась ({st} {n})")
st, n, note = S.marker_status(M[("debug.log", "KO release:")], t0)
check(st == "0" and n == "1", f"KO release asks=0 в сессии -> [0], строка до сессии не в счёт ({st} {n}{note})")
out = S.modules(t0)
check(any("predators.log" in l and "без меток" in l for l in out) and not any(l.startswith("молчали") and "predators.log" in l for l in out),
      "predators.log в разделе модулей, а не в «молчали»")
check(out[0].startswith("СЛОМАНО") and any("smell api unavailable" in l for l in out[:4]), "СЛОМАНО — первым в разделе")
# с размерами прошлого отчёта берутся только новые строки
size = os.path.getsize(os.path.join(tmp, "predators.log"))
json.dump({"predators.log": [[ts(t0 - datetime.timedelta(minutes=10)), size]]}, open(S.OFFSETS, "w", encoding="utf-8"))
open(os.path.join(tmp, "predators.log"), "a", encoding="utf-8").write("smell: blood deed:defeated at 1,2\n")
S._CACHE.clear()
ls, mode = S.session_lines("predators.log", t0)
check(mode == "offset" and ls == ["smell: blood deed:defeated at 1,2"], f"лог без меток + размер прошлого отчёта -> только новые строки ({mode} {ls})")
st, _, _ = S.marker_status(M[("predators.log", "smell api unavailable")], t0)
check(st == " ", "старый отказ до сессии не считается")

# --- 5. самопроверка KMM_Probe: формат строк совпадает с исходником, раздел печатает fail/absent, итог, сломалось/починилось
PSRC = open(os.path.join(BUILD, r"KMM_Conductor\scripts\init\KMM_Probe.lua"), encoding="utf-8").read()
check('" PROBE " .. name .. " " .. st .. " "' in PSRC and "PROBE summary ok=%d fail=%d absent=%d pass=%d" in PSRC and "logs/probe.log" in PSRC,
      "KMM_Probe пишет «PROBE <имя> <статус> <значение>» и summary в logs/probe.log — тот формат, что разбирает session_report")
S.STATE = tmp
prev_t, cur_t = t0 - datetime.timedelta(days=1), t0 + datetime.timedelta(minutes=2)
pl = [f"{ts(prev_t)} PROBE money ok money=0 via=Character:getMoney",
      f"{ts(prev_t)} PROBE smell fail ZoneMap.zoneSmell = nil at the player",
      f"{ts(prev_t)} PROBE update_list ok n=40 has(player)=true",
      f"{ts(prev_t)} PROBE summary ok=2 fail=1 absent=0 pass=1 ms=1.0 slow=smell:0.4",
      f"{ts(cur_t)} PROBE money ok money=10 via=Character:getMoney",
      f"{ts(cur_t)} PROBE smell ok zoneSmell ok addSmell=yes level=0.00",
      f"{ts(cur_t)} PROBE update_list fail n=40 has(player)=false (expected true)",
      f"{ts(cur_t)} PROBE item_value absent no items on player characters",
      f"{ts(cur_t)} PROBE summary ok=2 fail=1 absent=1 pass=1 ms=1.0 slow=smell:0.4",
      f"{ts(cur_t + datetime.timedelta(minutes=5))} PROBE update_list ok n=41 has(player)=true",
      f"{ts(cur_t + datetime.timedelta(minutes=5))} PROBE summary ok=1 fail=0 absent=0 pass=2 ms=0.5 slow=update_list:0.5"]
open(os.path.join(tmp, "probe.log"), "w", encoding="utf-8").write("\n".join(pl) + "\n")
sec = S.probe_section(t0)
txt = "\n".join(sec)
check(sec[0].startswith("итог: ok=3 fail=0 absent=1"), f"итог по последнему статусу каждой пробы (проход 2 уточняет 1): {sec[0][:60]}")
check("[?] absent item_value" in txt and "FAIL update_list" not in txt, "absent с причиной; fail, починенный проходом 2, не висит")
check("ПОЧИНИЛОСЬ smell" in txt and "сломалось 0, починилось 1" in txt, "сравнение с прошлой сессией: smell починился")
open(os.path.join(tmp, "probe.log"), "w", encoding="utf-8").write("\n".join(pl[:9]) + "\n")
sec = S.probe_section(t0)
txt = "\n".join(sec)
check("[!] FAIL update_list: n=40 has(player)=false" in txt and "СЛОМАЛОСЬ update_list" in txt, "fail печатается и попадает в «сломалось»")
open(os.path.join(tmp, "probe.log"), "w", encoding="utf-8").write("\n".join(pl[:4]) + "\n")
check("за сессию строк самопроверки нет" in S.probe_section(t0)[0], "проходов в сессии нет -> сказано прямо")
os.remove(os.path.join(tmp, "probe.log"))
check("probe.log нет" in S.probe_section(t0)[0], "нет probe.log -> сказано прямо")

print("ALL OK" if not FAILS else "FAIL %d" % len(FAILS))
sys.exit(1 if FAILS else 0)
