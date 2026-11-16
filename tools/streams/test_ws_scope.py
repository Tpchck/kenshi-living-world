"""Офлайн-тест (2026-11-16): KMM_Native.ws_set подменяет ТОЛЬКО свои world state.

Собирает все потоки данных в памяти (как kmm_build, без features/mods_cfg; записи файлов под C:\\KenshiModMap и Steam
уходят во временную папку, удаление/переименование/копирование вне неё запрещено) и проверяет:
  1. каждый sid в LUT ws_set (kmm_ws_lut.lua) и в замках Elite (kmm_elite_data.lua wes) — наш: <n>-KMM_Elite.mod,
     WORLD_EVENT_STATE из KMM_Elite, заведомо ложный без ws_set («X жив» И «X НЕ жив»), белый список адаптера его пропускает;
  2. ни одна запись не из KMM (ваниль, основа, Kaizo, WH) не ссылается на наши подменяемые WS;
  3. наши TOWN-варианты ссылаются только на свой WS (один WS = один вариант), без вложенных override town, владелец = LUT,
     базовый город ссылается на вариант; в LUT нет ни одного из 45 прежних общих WS;
  4. шаблоны KMM_Traces не несут «world state»; новые записи без ошибок схемы (сверх ошибок образца);
  5. LUT в build/ совпадает со сгенерированным (данные и таблица дирижёра согласованы); Lua не зовёт ws_set с чужим литералом.
python -I -X utf8 tools/streams/test_ws_scope.py  -> OK, код 1 при провале."""
import builtins
import collections
import glob
import importlib
import io
import json
import os
import re
import shutil
import sys
import tempfile

ROOT = r"C:\KenshiModMap"
TMP = tempfile.mkdtemp(prefix="kmm_ws_scope_")
_open, _mk = builtins.open, os.makedirs


def _redir(p):
    ap = os.path.abspath(str(p))
    low = ap.lower()
    if low.startswith(ROOT.lower()) or "steamapps" in low:
        return os.path.join(TMP, ap.replace(":", "").lstrip("\\/"))
    return ap


def _open_(file, mode="r", *a, **k):
    if isinstance(file, (str, bytes, os.PathLike)) and any(c in mode for c in "wax+"):
        file = _redir(file)
        _mk(os.path.dirname(file), exist_ok=True)
    return _open(file, mode, *a, **k)


_in_tmp = lambda p: os.path.abspath(str(p)).lower().startswith(TMP.lower())  # noqa: E731


def _blocked(name):
    def f(*a, **k):
        raise RuntimeError(name + " blocked in test")
    return f


builtins.open = _open_
io.open = _open_
os.makedirs = lambda p, *a, **k: _mk(_redir(p), *a, **{**k, "exist_ok": True})
_rm, _ren, _rep, _rmt = os.remove, os.rename, os.replace, shutil.rmtree
os.remove = os.unlink = lambda p, *a, **k: _rm(p) if _in_tmp(p) else _blocked("remove")()
os.rename = lambda a, b, *x, **k: _ren(a, b) if _in_tmp(a) and _in_tmp(b) else _blocked("rename")()
os.replace = lambda a, b, *x, **k: _rep(a, b) if _in_tmp(a) and _in_tmp(b) else _blocked("replace")()
shutil.rmtree = lambda p, *a, **k: _rmt(_redir(p), ignore_errors=True) if _in_tmp(_redir(p)) else _blocked("rmtree")()
for _n in ("copy", "copy2", "copyfile", "copytree", "move"):
    setattr(shutil, _n, _blocked("shutil." + _n))

for _p in ("build", "fast", "streams", ""):
    sys.path.insert(0, os.path.join(ROOT, "tools", _p))
import kmm_build  # noqa: E402
import kmod  # noqa: E402
import fcsdef  # noqa: E402
import ws_own  # noqa: E402

FAILS, N = [], [0]


def check(c, what):
    N[0] += 1
    if not c:
        FAILS.append(what)
        print("FAIL", what)


def lut_parse(txt):
    def lst(key):
        m = re.search(r"^%s=\{(.*)\},$" % key, txt, re.M)
        return re.findall(r'"((?:[^"\\]|\\.)*)"', m.group(1)) if m else []
    rows = {}
    for bt, body in re.findall(r'^\["((?:[^"\\]|\\.)*)"\]=\{(.*)\},$', txt, re.M):
        rows[bt] = [(int(o), [int(x) for x in c.split(",")]) for o, c in re.findall(r"\{o=(\d+),c=\{([\d,]+)\}\}", body)]
    return lst("F"), lst("W"), rows


ctx = kmm_build.Ctx()
mods = {}
for name, mod in kmm_build.DATA_STREAMS:
    rp = os.path.join(ROOT, "rules", "streams", f"{name}.json")
    if not os.path.exists(rp):
        continue
    rules = json.load(_open(rp, encoding="utf-8"))
    s = kmm_build.Stream(name, mod, ctx)
    importlib.import_module(name).build(ctx, s, rules)
    m = s.mb.build()
    mods[name] = m
    kmod.apply(ctx.M, m)
    for it in m.items:
        ctx.origin.setdefault(it.sid, f"{mod}.mod")
    ctx._reindex()
M, origin = ctx.M, ctx.origin
elite = {it.sid: it for it in mods["elite"].items}
rules_e = json.load(_open(os.path.join(ROOT, "rules", "streams", "elite.json"), encoding="utf-8"))
npc = rules_e["own_ws"]["false_npc"]
check(npc in M and M[npc].type_name == "CHARACTER", "false_npc — CHARACTER")

# --- 1. sid в LUT и замках Elite
gen_lut = _open(_redir(ws_own.LUT_OUT), "rb").read()
F, W, rows = lut_parse(gen_lut.decode("utf-8"))
check(len(W) > 0 and len(rows) > 0, "LUT не пуст")
OWN_RX = re.compile(r"^\d+-(KMM_[A-Za-z0-9_]+)\.mod$")   # то же правило, что own_ws() в KMM_Native.lua


def is_false(ws):
    is_ = {(r.target, r.v0) for r in ws.refs.get("NPC is", [])}
    not_ = {(r.target, r.v0) for r in ws.refs.get("NPC is NOT", [])}
    return bool(is_ & not_)


ed = _open(_redir(os.path.join(ROOT, "build", "KMM_Elite", "scripts", "kmm_elite_data.lua")), encoding="utf-8").read()
wes = re.findall(r'\["wes"\] = "([^"]+)"', ed)
check(len(wes) >= 1, "у Elite есть замки wes")
for sid in W + wes:
    mm = OWN_RX.match(sid)
    check(bool(mm) and mm.group(1) != "KMM_Merged", f"sid {sid}: формат своего WS (белый список адаптера)")
    it = elite.get(sid)
    check(it is not None and it.type_name == "WORLD_EVENT_STATE" and it.change == kmod.CHANGE_NEW, f"{sid}: новая запись WORLD_EVENT_STATE в KMM_Elite")
    if it is not None:
        check(is_false(it), f"{sid}: запрос ложен без ws_set (X жив И X НЕ жив)")
        check(not it.values.get("player involvement") and not it.refs.get("player ally") and not it.refs.get("player enemy"),
              f"{sid}: без условий игрока")
own = set(W) | set(wes)

# --- 2. кто ссылается на наши WS
refs_to = collections.defaultdict(list)
for it in M.values():
    for cat, rs in it.refs.items():
        for r in rs:
            if r.target in own and (r.v0, r.v1, r.v2) != kmod.DELETED_REF:
                refs_to[r.target].append((it.sid, it.type_name, cat, r.v0))
foreign = [(w, x) for w, lst in refs_to.items() for x in lst if not origin.get(x[0], "").startswith("KMM_")]
check(not foreign, f"чужие записи ссылаются на наши WS: {foreign[:5]}")
for w in wes:
    lst = refs_to.get(w, [])
    check(len(lst) == 1 and lst[0][1] == "UNIQUE_SQUAD_TEMPLATE" and lst[0][0] in elite, f"замок Elite {w}: ровно один свой уникальный отряд")

# --- 3. наши TOWN-варианты
reg = json.load(_open(ws_own.REG, encoding="utf-8"))["pairs"]
by_ws = {ws_own.own_sid(e["ws"]): (k, ws_own.own_sid(e["town"])) for k, e in reg.items()}
old_shared = set()
old = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_ws_scope_old_shared.json")
if os.path.isfile(old):
    old_shared = set(json.load(_open(old, encoding="utf-8")))
check(not (set(W) & old_shared), "в LUT нет прежних общих WS")
seen_ws = set()
for bt, lst in rows.items():
    owners = [F[o - 1] for o, _ in lst]
    check(len(owners) == len(set(owners)), f"{bt}: один вариант на владельца")
    for o, c in lst:
        check(len(c) == 2 and c[1] == 1, f"{bt}: в LUT ровно одно своё состояние =1")
        w = W[c[0] - 1]
        check(w not in seen_ws, f"{w}: WS используется одним городом/владельцем")
        seen_ws.add(w)
        key, tsid = by_ws.get(w, (None, None))
        check(key == f"{bt}|{F[o - 1]}", f"{w}: пара реестра совпадает с LUT ({key} / {bt}|{F[o - 1]})")
        t = M.get(tsid)
        check(t is not None and t.type_name == "TOWN" and tsid in elite, f"{tsid}: свой TOWN-вариант")
        if t is None:
            continue
        check([(r.target, r.v0) for r in t.refs.get("world state", [])] == [(w, 1)], f"{tsid}: world state только свой WS=1")
        check(not t.refs.get("override town"), f"{tsid}: без вложенных override town")
        check(bool(t.refs.get("faction")) and t.refs["faction"][0].target == F[o - 1], f"{tsid}: владелец = LUT")
        check(tsid in {r.target for r in M[bt].refs.get("override town", [])}, f"{bt}: базовый город ссылается на свой вариант")
        rl = refs_to.get(w, [])
        check([x[0] for x in rl] == [tsid], f"{w}: на WS ссылается только его вариант ({[x[0] for x in rl][:3]})")
our_towns = [it for it in elite.values() if it.type_name == "TOWN" and it.change == kmod.CHANGE_NEW]
for t in our_towns:
    check(all(r.target in own for r in t.refs.get("world state", [])), f"{t.sid}: наш вариант ссылается только на свои WS")

# --- 4. Traces без world state; схема новых записей
tr_ws = [it.name for it in mods["traces"].items if it.refs.get("world state")]
check(not tr_ws, f"KMM_Traces: шаблоны с world state: {tr_ws[:5]}")
sch = fcsdef.load(kmm_build.KENSHI)
src_of = {ws_own.own_sid(e["town"]): e.get("src") for e in reg.values()}
bad = []
for it in elite.values():
    if it.type_name not in ("WORLD_EVENT_STATE", "TOWN"):
        continue
    e, _w = fcsdef.validate(M[it.sid], sch, resolve=M.get)
    base = set()
    if it.type_name == "TOWN" and src_of.get(it.sid) in M:
        base = set(fcsdef.validate(M[src_of[it.sid]], sch, resolve=M.get)[0])
    bad += [(it.sid, x) for x in e if x not in base]
check(not bad, f"ошибки схемы в своих WS/TOWN: {bad[:5]}")

# --- 5. LUT в build/ = сгенерированному; литералы ws_set в Lua
cur = _open(ws_own.LUT_OUT, "rb").read() if os.path.isfile(ws_own.LUT_OUT) else b""
check(cur == gen_lut, "build/.../kmm_ws_lut.lua совпадает со сгенерированным (переложить из прогона)")
lit = []
for p in glob.glob(os.path.join(ROOT, "build", "KMM_*", "scripts", "**", "*.lua"), recursive=True):
    for sid in re.findall(r'ws_set\(\s*"([^"]+)"', _open(p, encoding="utf-8").read()):
        if not OWN_RX.match(sid):
            lit.append((os.path.basename(p), sid))
check(not lit, f"Lua зовёт ws_set с чужим sid: {lit[:5]}")

print(json.dumps({"lut_ws": len(W), "lut_towns": len(rows), "elite_wes": len(wes), "own_town_variants": len(our_towns),
                  "checks": N[0], "fails": len(FAILS), "tmp": TMP}, ensure_ascii=False))
if "--emit-lut" in sys.argv:   # для переноса в build/: путь сгенерированной таблицы
    print("GEN_LUT", _redir(ws_own.LUT_OUT))
print("OK" if not FAILS else "FAILED")
sys.exit(1 if FAILS else 0)
