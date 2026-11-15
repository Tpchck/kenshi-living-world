"""Сверка вызовов API в наших Lua (KMM_*) со справочником KenshiLua (BindingsReference.md).
Ловит класс ошибок «метода нет в игре» (getGameData у Faction и т.п.) офлайн. Только чтение. До 5 с."""
import glob, os, re, sys, collections
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
DOC = r"C:\Program Files (x86)\Steam\steamapps\workshop\content\233860\3817000612\docs\BindingsReference.md"
ROOT = os.environ.get("KMM_AUDIT_ROOT") or r"C:\KenshiModMap\build"   # KMM_AUDIT_ROOT: самопроверка на фикстурах (tools/test/test_api_contract.py)
cls, methods, fields = None, collections.defaultdict(set), collections.defaultdict(set)
sect = None
for line in open(DOC, encoding="utf-8"):
    m = re.match(r"^## (\S+)", line)
    if m: cls = m.group(1); continue
    if line.startswith("### "): sect = line[4:].strip().lower(); continue
    m = re.match(r"^\| (\w+)", line)
    if m and cls and m.group(1) not in ("Lua", "Method", "Name"):
        (fields if sect and sect.startswith("field") else methods)[m.group(1)].add(cls)
allm = set(methods) | set(fields)
used = collections.defaultdict(list)
OWN = set()
for p in glob.glob(ROOT + r"\KMM_*\scripts\**\*.lua", recursive=True):
    src = open(p, encoding="utf-8").read()
    OWN |= set(re.findall(r"function\s+[\w.]*[:.](\w+)\s*\(", src)) | set(re.findall(r"(\w+)\s*=\s*function", src)) | set(re.findall(r"function\s+(\w+)", src))
    for i, l in enumerate(src.splitlines(), 1):
        if l.lstrip().startswith("--"): continue
        for m in re.finditer(r"(\w+):(\w+)\s*\(", l):
            used[m.group(2)].append((os.path.relpath(p, ROOT), i, m.group(1)))
LUA_STD = {"format", "gsub", "match", "gmatch", "find", "sub", "lower", "upper", "rep", "byte", "len", "write", "read", "close", "lines", "seek", "flush", "reverse"}
# методы контейнеров KenshiLua (docs/ContainersReference.md: ogre/boost/std map/set/lektor) — не входят в BindingsReference
CONTAINER = {"toTable", "has", "remove", "clear", "size", "insert", "push_back", "contains"}
unknown = {k: v for k, v in used.items() if k not in allm and k not in LUA_STD and k not in OWN and k not in CONTAINER}
print(f"методов в справочнике {len(allm)}, вызовов в KMM {sum(map(len, used.values()))}, разных {len(used)}")
print(f"неизвестных справочнику: {len(unknown)}")
for k, v in sorted(unknown.items(), key=lambda kv: -len(kv[1])):
    print(f"  {k:28s} x{len(v):3d}  напр. {v[0][0]}:{v[0][1]} ({v[0][2]}:)")
# getGameData на объектах, похожих на фракцию
for k in ("getGameData",):
    for f, i, obj in used.get(k, []):
        if re.match(r"(f|fac|faction|f0|fo|fobj)\w*$", obj, re.I): print(f"  ВНИМАНИЕ {k} на '{obj}' {f}:{i} (у Faction нет getGameData)")

# --- сверка с учётом класса: тип по имени переменной, наследование из заголовков KenshiLib
HDR = r"C:\KenshiModMap\tools\ref\KenshiLib\Include"
parents = collections.defaultdict(list)
for h in glob.glob(HDR + r"\**\*.h", recursive=True):
    for m in re.finditer(r"^class\s+(?:KENSHILIB_API\s+)?(\w+)\s*:\s*([^{\n]+)", open(h, encoding="utf-8", errors="replace").read(), re.M):
        parents[m.group(1)] = re.findall(r"public\s+([\w:]+)", m.group(2))
def closure(c):
    out, st = set(), [c]
    while st:
        x = st.pop()
        if x in out: continue
        out.add(x); st += [p.split("::")[-1] for p in parents.get(x, [])]
    return out
GUESS = [(r"^(f|f0|fa|fb|fo|fac|faction|fobj|fx)$", "Faction"), (r"^(ch|c|char|chr|pc|leader|npc|m)$", "Character"),
         (r"^(t|town|tw|tb)$", "TownBase"), (r"^(b|bb|bld|building|shop)$", "Building"), (r"^(it|item|itm)$", "Item"),
         (r"^(plat|platoon|pl|sq)$", "Platoon|ActivePlatoon"), (r"^(gw|ou)$", "GameWorld"), (r"^(inv|inventory)$", "Inventory")]
bad = []
for meth, calls in used.items():
    owners = methods.get(meth, set()) | fields.get(meth, set())
    if not owners: continue
    for f, i, obj in calls:
        for rx, c in GUESS:
            if re.match(rx, obj, re.I):
                if not (set().union(*[closure(x) for x in c.split('|')]) & owners): bad.append((f, i, obj, c, meth, sorted(owners)[:4]))
                break
print(f"подозрительных вызовов с учётом класса: {len(bad)}")
for b in bad: print(f"  {b[0]}:{b[1]}  {b[2]}:{b[4]}()  — {b[3]} не имеет; есть у {b[5]}")

# --- заглушки тестов: методы, которых нет в игре (корень ошибок 2026-11-12: тесты зелёные, игра нет)
stub_bad = collections.defaultdict(list)
OURMOD = re.compile(r"^(KMM_|kmm_|_)")
GLOBALS = {"getGameWorld", "getPlayerInterface"}   # глобальные функции KenshiLua (работают в игре, лог 2026-11-12)
for p in glob.glob(ROOT + r"\*\_dev\test_*.py") + glob.glob(r"C:\KenshiModMap\tools\test\test_*.py") + glob.glob(r"C:\KenshiModMap\tools\conductor\test_*.py"):
    src = open(p, encoding="utf-8", errors="replace").read()
    for m in re.finditer(r"\b(get\w+|is\w+|set\w+|has\w+)\s*=\s*function", src):
        nm = m.group(1)
        if nm not in allm and nm not in OWN and nm not in GLOBALS and not OURMOD.match(nm):
            stub_bad[nm].append(os.path.basename(p))
print(f"методов в заглушках, которых нет в игре: {len(stub_bad)}")
for k, v in sorted(stub_bad.items()): print(f"  {k:28s} {sorted(set(v))[:4]}")

KNOWN_FP = {"close", "lines", "sub"}   # файлы/строки Lua под именами f/t
real = [b for b in bad if b[4] not in KNOWN_FP]
EARLY_FAIL = bool(real or stub_bad or unknown)

# --- сигнатуры: число аргументов и явный nil там, где игра ждёт значение (баг squadType 2026-11-12)
sigs = collections.defaultdict(list)   # method -> [ [ type, ... ], ... ]
signames = collections.defaultdict(list)   # method -> [ [ имя, ... ], ... ]
for line in open(DOC, encoding="utf-8"):
    m = re.match(r"^\| (\w+)(?: \[\d+\])? \| `([^`]*)` \| `[^`]*` \| `obj:", line)
    if m:
        args = [a.strip() for a in m.group(2).split(",") if a.strip()]
        sigs[m.group(1)].append([tuple(x.split(":", 1)[1].strip() for _ in [0]) [0] if ":" in x else x for x in args])
        signames[m.group(1)].append([x.split(":", 1)[0].strip() for x in args])
# проверено в игре (лог 2026-11-12): createItem принимает nil вместо hand (печать посланника выдана), createRandomSquad — нет
NIL_OK = {("createItem", 2)}
# Контракт движка (B3 И1): параметр-объект, который НЕ принимает nil, хотя большинство указателей sol2 nil пропускает
# (createRandomSquad: homeTown/home/ownr/maparea/_activePlatoon = nil работают в Traces; createItem: weaponMesh/matData = nil работают).
# (метод, позиция без self) -> источник. ✓игра — из лога; ? — аналог по той же сигнатуре BindingsReference, в игре не видели.
NIL_BAD = {("createRandomSquad", 6): "✓игра 2026-11-15: bad argument #6 to 'createRandomSquad' (KenshiLua.GameData expected, got nil)",
           ("createRandomUnloadedSquad", 6): "? аналог createRandomSquad: тот же squad: GameData",
           ("createRandomUnloadedCharacter", 4): "? аналог: characterTemplate: GameData (шаблон, как squad)"}
VEC_T = {"Vector3", "Quaternion"}   # таблица {x=,y=,z=} вместо Vector3 работает в игре (Traces, 2026-11-12)
VALUE_T = re.compile(r"^(integer|number|boolean|string|hand|bool|float|int|[A-Z]\w*Type|itemType|AttachSlot|\w+Enum)$")


def split_args(src, i):
    """src[i] == '(' -> список аргументов верхнего уровня (строки), конец"""
    depth, cur, out, j, q = 0, "", [], i, None
    while j < len(src):
        ch = src[j]
        if q:
            cur += ch
            if ch == q and src[j - 1] != "\\": q = None
        elif ch in "\"'":
            q = ch; cur += ch
        elif ch in "({[":
            depth += 1
            if depth > 1: cur += ch
        elif ch in ")}]":
            depth -= 1
            if depth == 0:
                if cur.strip(): out.append(cur.strip())
                return out
            cur += ch
        elif ch == "," and depth == 1:
            out.append(cur.strip()); cur = ""
        else:
            cur += ch
        j += 1
    return out


def maybe_nil(src, pos, name):
    """Эвристика: в теле функции до вызова есть `local name = nil` или `local name` без значения; name получает значение только
    глубже по отступу (внутри if); проверки `if not name` / `if name == nil` / `assert(name` / безусловного присваивания на уровне
    объявления нет -> вернуть строку объявления."""
    fs = max(src.rfind("function", 0, pos), 0)
    body = src[fs:pos].split(chr(10))
    decl = None
    for idx, l in enumerate(body):
        if re.match(r"^\s*local\s+" + name + r"\s*(=\s*nil\s*)?(--.*)?$", l):
            decl = idx
    if decl is None:
        return None
    ind = len(body[decl]) - len(body[decl].lstrip())
    guard = re.compile(r"^\s*(if\s+not\s+\(?\s*" + name + r"\b|if\s+" + name + r"\s*==\s*nil|assert\(\s*" + name + r"\b|" + name + r"\s*=[^=])")
    for l in body[decl + 1:]:
        li = len(l) - len(l.lstrip())
        if l.strip() and li <= ind and guard.match(l):
            return None
    return body[decl].strip()


sig_bad, sig_warn = [], []
for p in glob.glob(ROOT + r"\KMM_*\scripts\**\*.lua", recursive=True):
    src = open(p, encoding="utf-8").read()
    for m in re.finditer(r"(\w+):(\w+)\s*\(", src):
        meth = m.group(2)
        if meth not in sigs or meth in OWN: continue
        ls = src.rfind(chr(10), 0, m.start()) + 1
        if "--" in src[ls:m.start()]: continue   # в комментарии
        args = split_args(src, m.end() - 1)
        if any(a == "..." for a in args): continue
        counts = {len(s) for s in sigs[meth]}
        line = src.count("\n", 0, m.start()) + 1
        rel = os.path.relpath(p, ROOT)
        if len(args) not in counts:
            sig_bad.append(f"{rel}:{line}  {m.group(1)}:{meth}() аргументов {len(args)}, в игре {sorted(counts)}")
            continue
        for k, a in enumerate(args):
            types = {s[k] for s in sigs[meth] if len(s) == len(args)}
            if a == "nil" and (meth, k + 1) not in NIL_OK:
                if (meth, k + 1) in NIL_BAD:
                    sig_bad.append(f"{rel}:{line}  {m.group(1)}:{meth}() аргумент #{k + 1} = nil, а игра ждёт {sorted(types)} ({NIL_BAD[(meth, k + 1)]})")
                elif types and all(VALUE_T.match(t) for t in types):
                    sig_bad.append(f"{rel}:{line}  {m.group(1)}:{meth}() аргумент #{k + 1} = nil, а игра ждёт {sorted(types)}")
                continue
            # литерал не того типа на месте объекта движка (строка sid вместо GameData, число/true вместо Faction и т.п.)
            lit = ("string" if a[:1] in "\"'" or a.startswith("[[") else "number" if re.fullmatch(r"-?\d+(\.\d+)?", a)
                   else "boolean" if a in ("true", "false") else "table" if a.startswith("{") else None)
            obj_t = types and all(not VALUE_T.match(t) and t not in ("userdata", "any", "object", "table", "function", "sol::object")
                                  and t[:1].isupper() for t in types)
            if lit and obj_t and not (lit == "table" and types <= VEC_T):
                sig_bad.append(f"{rel}:{line}  {m.group(1)}:{meth}() аргумент #{k + 1} = {lit}-литерал, а игра ждёт {sorted(types)}")
            # возможный nil (предупреждение): local X = nil / local X, присвоен только внутри if, проверки на уровне объявления нет
            if (meth, k + 1) in NIL_BAD and re.fullmatch(r"[A-Za-z_]\w*", a):
                w = maybe_nil(src, m.start(), a)
                if w:
                    sig_warn.append(f"{rel}:{line}  {m.group(1)}:{meth}() аргумент #{k + 1} '{a}' может быть nil ({w}); {NIL_BAD[(meth, k + 1)]}")
print(f"нарушений сигнатур: {len(sig_bad)}")
for s in sig_bad: print("  " + s)
print(f"возможный nil в аргументах контракта движка (предупреждение, код выхода не меняет): {len(sig_warn)}")
for s in sig_warn: print("  " + s)
# --- события: каждое Events.on("X") должно быть в CallbacksReference.md
CB = os.path.join(os.path.dirname(DOC), "CallbacksReference.md")
cbtxt = open(CB, encoding="utf-8").read()
ev_bad = []
for p in glob.glob(ROOT + r"\KMM_*\scripts\**\*.lua", recursive=True):
    for ev in set(re.findall(r'Events\.on\("([^"]+)"', open(p, encoding="utf-8").read())):
        if "| `" + ev + "` |" not in cbtxt:
            ev_bad.append(f"{os.path.relpath(p, ROOT)}: событие {ev} не найдено в CallbacksReference")
print(f"неизвестных событий: {len(ev_bad)}")
for e in ev_bad: print("  " + e)
sys.exit(1 if (EARLY_FAIL or sig_bad or ev_bad) else 0)
