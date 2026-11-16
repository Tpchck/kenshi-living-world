"""Офлайн-прогон наших Lua-модулей KMM на мире из НАСТОЯЩЕГО сейва владельца (без игры). Lua 5.1 через lua51.dll (как test_runtime).
python -I -X utf8 tools/test/save_replay.py [сейв=quicksave,KMM_Test2 ...] [--days N] [--radius R]
Мир берётся из %LOCALAPPDATA%\\kenshi\\save\\<имя>\\platoon (kmod): персонажи, фракции, расы, позиции, голод, инвентарь, отряды; города/фракции - из
build/KMM_Conductor/conductor.json. Выдуманное (деньги, торговцы, здания, рабочие, ход игрока...) перечислено в шапке tools/test/save_world.lua.
Ловит: ошибки Lua (traceback из обработчиков), самоотключения (debug.log 'disabled until restart', реестр KMM_Gov 'OFF (' и паузы 'failed, retry in'/'-> pause'/'PAUSED', .disabled()), обращения к неизвестным полям заглушки
(UNKNOWN: ключ -> модуль:строка; помечено, есть ли метод в BindingsReference), рост таблиц и очередей. Код возврата 0 при отсутствии ошибок Lua, самоотключений и пауз реестра."""
import collections
import ctypes
import glob
import json
import os
import re
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
import kmod  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

DLL = r"C:\Program Files (x86)\Steam\steamapps\workshop\content\233860\3817000612\lua51.dll"
REFDOC = r"C:\Program Files (x86)\Steam\steamapps\workshop\content\233860\3817000612\docs\BindingsReference.md"
B = r"C:\KenshiModMap\build"
SAVES = os.path.expandvars(r"%LOCALAPPDATA%\kenshi\save")
PLAYER_FID = "204-gamedata.base"
CACHE = os.environ.get("KMM_REPLAY_CACHE") or tempfile.gettempdir()


# ---------------------------------------------------------------- мир из сейва
def extract(save):
    cp = os.path.join(CACHE, f"kmm_save_world_{save}.json")
    d = os.path.join(SAVES, save, "platoon")
    mt = max(os.path.getmtime(p) for p in glob.glob(d + r"\*.platoon"))
    if os.path.exists(cp):
        try:
            c = json.load(open(cp, encoding="utf-8"))
            if c.get("mtime") == mt and c.get("v") == 2:
                return c
        except Exception:
            pass
    chars, fnames = [], collections.defaultdict(collections.Counter)
    Gd = r"C:\Program Files (x86)\Steam\steamapps\common\Kenshi\data"
    try:   # имена рас из ванили (моды-расы остаются sid)
        V = kmod.load_chain([Gd + r"\gamedata.base", Gd + r"\rebirth.mod", Gd + r"\Newwworld.mod", Gd + r"\Dialogue.mod"])
    except Exception:
        V = {}
    for p in sorted(glob.glob(d + r"\*.platoon")):
        base = os.path.basename(p)[:-len(".platoon")]
        try:
            m = kmod.read(p)
        except Exception as e:  # noqa: BLE001
            print("  не прочитан", base, e)
            continue
        by = {it.sid: it for it in m.items}
        for it in m.items:
            if it.type != 30:
                continue
            for ins in it.instances:
                st = [by.get(s) for s in ins.states]
                ch = next((s for s in st if s and s.type == 36), None)
                if not ch:
                    continue
                med = next((s for s in st if s and s.type == 57), None)
                app = next((s for s in st if s and s.type == 66), None)
                inv = next((s for s in st if s and s.type == 41 and s.instances), None)
                items, stack = [], [inv] if inv else []
                depth = 0
                while stack and depth < 40:
                    depth += 1
                    iv = stack.pop()
                    for sl in iv.instances:
                        iit = by.get(sl.target)
                        if not iit:
                            continue
                        if iit.type == 42:
                            items.append([iit.values.get("base data sid", ""), iit.values.get("section", ""), int(iit.values.get("quantity", 1) or 1)])
                            for sl2 in iit.instances:
                                sub = by.get(sl2.target)
                                if sub and sub.type == 41:
                                    stack.append(sub)
                        elif iit.type == 41:
                            stack.append(iit)
                v = ch.values
                fid = v.get("owner faction ID", "")
                fnames[base.rsplit("_", 1)[0]][fid] += 1
                mv = med.values if med else {}
                race = ""
                if app and app.refs.get("race"):
                    race = app.refs["race"][0].target
                chars.append({"n": v.get("name", ins.id), "f": fid, "x": ins.pos[0], "y": ins.pos[1], "z": ins.pos[2], "race": race,
                              "fem": bool(app.values.get("sex female")) if app else False, "hung": mv.get("hung", 3.0), "blood": mv.get("blood", 100.0),
                              "dead": bool(mv.get("dead")), "ko": float(mv.get("KO", 0.0)), "plat": base, "lead": bool(v.get("is leader")),
                              "player": fid == PLAYER_FID, "items": items, "tpl": ins.target,
                              "racen": (V.get(race) or V.get(race.replace(".quack", ".base")) or type("x", (), {"name": race})).name})
    out = {"v": 2, "mtime": mt, "chars": chars, "fnames": {k: c.most_common(1)[0][0] for k, c in fnames.items()}}
    try:
        json.dump(out, open(cp, "w", encoding="utf-8"))
    except Exception:
        pass
    return out


def lua_lit(v):
    if isinstance(v, bool):
        return "true" if v else "false"
    if v is None:
        return "nil"
    if isinstance(v, (int, float)):
        return repr(float(v)) if isinstance(v, float) else str(v)
    if isinstance(v, str):
        return '"' + v.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\r", "") + '"'
    if isinstance(v, (list, tuple)):
        return "{" + ",".join(lua_lit(x) for x in v) + "}"
    if isinstance(v, dict):
        return "{" + ",".join(f"[{lua_lit(k)}]={lua_lit(x)}" for k, x in v.items()) + "}"
    raise TypeError(type(v))


def build_world(save):
    w = extract(save)
    cj = json.load(open(B + r"\KMM_Conductor\conductor.json", encoding="utf-8"))
    towns = [{"sid": s, "name": i.get("name", s), "x": float(i["x"]), "z": float(i["z"])} for s, i in cj["town_info"].items() if i.get("x") is not None]
    town_fid = {}
    for fid, f in cj["factions"].items():
        for t in f.get("towns") or []:
            town_fid[t] = fid
    trader_words = ("trader", "caravan", "merchant", "guild")
    ownerless = 0
    for i, c in enumerate(w["chars"]):
        # INV: торговцы = отряды фракций-торговцев; unique = лидер отряда "No Faction"/без деления нет данных -> не помечаем
        c["trader"] = any(t in c["plat"].lower() for t in trader_words) and c["lead"]
        c["resident"] = c["trader"] and (i % 2 == 0)
        c["animal"] = any(a in c.get("racen", "").lower() for a in ("garru", "bonedog", "beak thing", "leviathan", "gorillo", "raptor", "crab", "spider", "goat", "bull", "swampy", "boneyard", "hound"))   # INV: эвристика по имени расы
    town_items = []
    try:
        td = open(B + r"\KMM_Town\scripts\kmm_town_data.lua", encoding="utf-8").read()
        town_items = re.findall(r'"(\d+-[^"]+\.(?:mod|base))"', td.split('["cat_items"]', 1)[1].split('["machines"]', 1)[0])
    except Exception:
        pass
    fn = dict(w["fnames"])
    names = {}
    for fid in {c["f"] for c in w["chars"]}:
        names[fid] = fid
    for pk, fid in fn.items():
        names[fid] = pk
    for fid, f in cj["factions"].items():
        names.setdefault(fid, f.get("name", fid))
    return {"chars": w["chars"], "towns": towns, "town_fid": town_fid, "fnames": names, "shop_items": town_items[:40]}


# ---------------------------------------------------------------- справочник API
def reference_classes():
    """класс -> множество имён (методы+поля) из BindingsReference"""
    out = collections.defaultdict(set)
    cls = None
    try:
        for line in open(REFDOC, encoding="utf-8"):
            m = re.match(r"^## (\S+)", line)
            if m:
                cls = m.group(1)
                continue
            m = re.match(r"^\| (\w+)", line)
            if m and cls and m.group(1) not in ("Lua", "Method", "Name"):
                out[cls].add(m.group(1))
    except OSError:
        pass
    return out


def reference_methods():
    ms, fs = set(), set()
    cls, sect = None, None
    try:
        for line in open(REFDOC, encoding="utf-8"):
            m = re.match(r"^## (\S+)", line)
            if m:
                cls = m.group(1)
                continue
            if line.startswith("### "):
                sect = line[4:].strip().lower()
                continue
            m = re.match(r"^\| (\w+)", line)
            if m and cls and m.group(1) not in ("Lua", "Method", "Name"):
                (fs if sect and sect.startswith("field") else ms).add(m.group(1))
    except OSError:
        pass
    return ms, fs


# ---------------------------------------------------------------- Lua
L = ctypes.CDLL(DLL)
L.luaL_newstate.restype = ctypes.c_void_p
for fn, at in [("luaL_openlibs", [ctypes.c_void_p]), ("luaL_loadstring", [ctypes.c_void_p, ctypes.c_char_p]),
               ("luaL_loadbuffer", [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_size_t, ctypes.c_char_p]),
               ("lua_pcall", [ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int]), ("lua_settop", [ctypes.c_void_p, ctypes.c_int]),
               ("lua_getfield", [ctypes.c_void_p, ctypes.c_int, ctypes.c_char_p]), ("lua_close", [ctypes.c_void_p])]:
    getattr(L, fn).argtypes = at
L.lua_tolstring.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p]
L.lua_tolstring.restype = ctypes.c_char_p


class Lua:
    def __init__(self):
        self.st = L.luaL_newstate()
        L.luaL_openlibs(self.st)

    def run(self, code, name="chunk", chunk=None):
        """chunk - путь файла для сообщений об ошибках/неизвестных полях (файл:строка), иначе [string ...]"""
        b = code.encode("utf-8")
        cn = ("@" + chunk).encode("utf-8") if chunk else ("=" + name).encode("utf-8")
        if L.luaL_loadbuffer(self.st, b, len(b), cn) or L.lua_pcall(self.st, 0, 0, 0):
            msg = L.lua_tolstring(self.st, -1, None).decode("utf-8", "replace")
            L.lua_settop(self.st, 0)
            raise RuntimeError(name + ": " + msg)

    def val(self, expr):
        """строковое значение Lua-выражения (tostring); при ошибке выражения - None"""
        try:
            self.run("_V = tostring(" + expr + ")", "val")
        except RuntimeError:
            return None
        L.lua_getfield(self.st, -10002, b"_V")
        v = L.lua_tolstring(self.st, -1, None)
        L.lua_settop(self.st, -2)
        return v.decode("utf-8", "replace") if v else None

    def num(self, expr):
        try:
            return float(self.val(expr))
        except (TypeError, ValueError):
            return None


MODULES = [  # (метка, файл, лежит в KMM_*\scripts\init); порядок как у игры: Conductor раньше потребителей
    ("Conductor", "KMM_Conductor/scripts/init/KMM_Conductor.lua"),
    *[(f[4:-4], "KMM_Conductor/scripts/init/" + f) for f in sorted(p.split("\\")[-1] for p in __import__("glob").glob(B + r"\KMM_Conductor\scripts\init\KMM_Conductor_*.lua"))],   # части дирижёра (T1)
    ("Gov", "KMM_Conductor/scripts/init/KMM_Gov.lua"),
    ("Self", "KMM_Conductor/scripts/init/KMM_Self.lua"), ("Traces", "KMM_Conductor/scripts/init/KMM_Traces.lua"),
    ("Fates", "KMM_Conductor/scripts/init/KMM_Fates.lua"), ("RelicRace", "KMM_Conductor/scripts/init/KMM_RelicRace.lua"),
    ("Predators", "KMM_Conductor/scripts/init/KMM_Predators.lua"), ("Siege", "KMM_Conductor/scripts/init/KMM_Siege.lua"),
    ("Herds", "KMM_Conductor/scripts/init/KMM_Herds.lua"), ("Veterans", "KMM_Conductor/scripts/init/KMM_Veterans.lua"), ("Outlaws", "KMM_Conductor/scripts/init/KMM_Outlaws.lua"),
    ("Diplo", "KMM_Diplo/scripts/init/kmm_diplo.lua"), ("Elite", "KMM_Elite/scripts/init/kmm_elite.lua"),
    ("Native", "KMM_Native/scripts/init/KMM_Native.lua"), ("Ore", "KMM_Ore/scripts/init/kmm_ore.lua"),
    ("Rumors", "KMM_Rumors/scripts/init/KMM_Rumors.lua"), ("Stock", "KMM_Stock/scripts/init/kmm_stock.lua"),
    ("Tempo", "KMM_Tempo/scripts/init/kmm_tempo.lua"), ("Town", "KMM_Town/scripts/init/kmm_town.lua")]
GLOBAL_OF = {"Conductor": "KMM_Conductor", "Gov": "KMM_Gov", "Self": "KMM_Self", "Traces": "KMM_Traces", "Diplo": "KMM_Diplo", "Elite": "KMM_Elite",
             "Native": "KMM_Native", "Ore": "KMM_Ore", "Rumors": "KMM_Rumors", "Stock": "KMM_Stock", "Tempo": "KMM_Tempo", "Town": "KMM_Town",
             "Fates": "KMM_Fates", "RelicRace": "KMM_RelicRace", "Predators": "KMM_Predators", "Siege": "KMM_Siege", "Herds": "KMM_Herds", "Veterans": "KMM_Veterans", "Outlaws": "KMM_Outlaws"}





PROBES = {  # метка -> выражение, чей размер (DEEPSIZE) наблюдаем по суткам; рост = подозрение на утечку/бесконечную очередь
    "Conductor.state": "KMM_Conductor.state()", "Conductor.all": "KMM_Conductor", "Traces": "KMM_Traces", "Traces.stats": "KMM_Traces.stats()",
    "Self": "KMM_Self", "Self.stats": "KMM_Self.stats()", "Gov.snap": "KMM_Gov.snapshot_stats()", "Stock": "KMM_Stock", "Tempo": "KMM_Tempo",
    "Town": "KMM_Town", "Ore": "KMM_Ore", "Rumors": "KMM_Rumors", "Elite": "KMM_Elite", "Diplo": "KMM_Diplo",
    "Ext": "KMM_Conductor.state().ext"}

WORKERS_LUA = r'''
local DATA = dofile("@B@/KMM_Town/scripts/kmm_town_data.lua")
local OC = dofile("@B@/KMM_Ore/scripts/ore_config.lua")
local ore_tpl; for k, v in pairs(OC.templates) do if v == "surface" then ore_tpl = k; break end end
local mach; for k, m in pairs(DATA.machines) do if m.item then mach = k; break end end
local wt = 87; for _, v in pairs(DATA.work_tasks or {}) do wt = v; break end
function ORE_REASSIGN(p) ASSIGN_WORK(p, ore_tpl, 87, nil) end
for _, p in ipairs(PCS_PUB) do ORE_REASSIGN(p) end
WORKERS = 0
for i, ch in ipairs(CHARS_PUB) do
  local c = ch._c
  if not c.player and not c.dead and i % 3 == 0 then
    local t = nearest_town_pub(c.x, c.z)
    if t then ASSIGN_WORK(ch, mach, wt, t.sid); WORKERS = WORKERS + 1 end
  end
end
PLAN_ROUTE()
'''

ACTIVITY_LUA = r'''
local function compact(v, d)
  if type(v) ~= "table" then return tostring(v) end
  if d > 1 then return "{..}" end
  local keys = {}
  for k, x in pairs(v) do keys[#keys + 1] = tostring(k) end
  table.sort(keys)
  local out = {}
  for _, k in ipairs(keys) do
    local x = v[k]; if x == nil then x = v[tonumber(k)] end
    if type(x) == "table" and d == 1 then local n = 0; for _ in pairs(x) do n = n + 1 end; out[#out + 1] = k .. "=#" .. n
    else out[#out + 1] = k .. "=" .. compact(x, d + 1) end
    if #out >= 24 then out[#out + 1] = "..."; break end
  end
  return "{" .. table.concat(out, " ") .. "}"
end
local probes = { Traces = "KMM_Traces.stats()", Self = "KMM_Self.stats()", Gov = "KMM_Gov.snapshot_stats()", Stock = "KMM_Stock.stats()", Tempo = "KMM_Tempo.status()",
  Town = "KMM_Town.stats()", Ore = "KMM_Ore.stats()", Elite = "KMM_Elite.stats()", Diplo = "KMM_Diplo.stats()", Rumors = "KMM_Rumors.status()" }
local names = {}; for k in pairs(probes) do names[#names + 1] = k end; table.sort(names)
local out = {}
for _, k in ipairs(names) do
  local f = loadstring("return " .. probes[k])
  local ok, v = pcall(f)
  out[#out + 1] = k .. ": " .. (ok and compact(v, 0) or ("ERR " .. tostring(v)))
end
return table.concat(out, "\n")
'''

LIST_UNKNOWN_LUA = r'''(function() local t = {}; for k, w in pairs(UNKNOWN) do for loc, n in pairs(w) do t[#t+1] = k .. "\t" .. loc .. "\t" .. n end end; table.sort(t); return table.concat(t, "\n") end)()'''


def replay(save, days, tick_s, radius):
    t0 = time.time()
    tmp = tempfile.mkdtemp(prefix="kmm_replay_").replace("\\", "/")
    W = build_world(save)
    refm, _ = reference_methods()
    R = {"save": save, "errors": [], "disabled": [], "load_errors": [], "unknown": {}, "growth": [], "days": 0}
    lua = Lua()
    bj = B.replace("\\", "/")
    paths = ";".join(f"{bj}/{d}/scripts/?.lua" for d in ("KMM_Ore", "KMM_Stock", "KMM_Town", "KMM_Diplo", "KMM_Elite", "KMM_Rumors", "KMM_Native"))
    lua.run(f'TMP = "{tmp}"; package.path = "{paths};" .. package.path\nREFM = {lua_lit({m: True for m in refm})}\nWORLD = {lua_lit(W)}', "world")
    lua.run("REAL_CLOCK = os.clock", "rc")
    lua.run(open(os.path.join(HERE, "save_world.lua"), encoding="utf-8").read(), "save_world.lua", chunk=os.path.join(HERE, "save_world.lua"))
    for lab, rel in MODULES:
        try:
            fp = os.path.join(B, rel.replace("/", os.sep))
            lua.run(open(fp, encoding="utf-8").read(), lab, chunk=fp)
        except RuntimeError as e:
            R["load_errors"].append(f"{lab}: {e}")
    R["world"] = {"chars": len(W["chars"]), "players": sum(1 for c in W["chars"] if c["player"]), "dead": sum(1 for c in W["chars"] if c["dead"]),
                  "factions": len({c["f"] for c in W["chars"]}), "platoons": len({c["plat"] for c in W["chars"]}), "towns": len(W["towns"]),
                  "items": sum(len(c["items"]) for c in W["chars"]), "with_items": sum(1 for c in W["chars"] if c["items"])}
    lua.run(f"LOAD_RADIUS = {radius}", "radius")
    lua.run(WORKERS_LUA.replace("@B@", bj), "workers")
    R["world"]["workers"] = int(lua.num("WORKERS") or 0)
    per_day = int(1440 / tick_s)
    sizes, day_t = [], []
    for d in range(days):
        t1 = time.time()
        try:
            lua.run(f"SIM({per_day}, {tick_s}, {tick_s / 1440.0})", f"day{d}")
        except RuntimeError as e:
            R["errors"].append(str(e))
            break
        day_t.append(time.time() - t1)
        row = {"day": d + 1}
        for k, ex in PROBES.items():
            row[k] = int(lua.num(f"DEEPSIZE({ex}, 400000)") or 0)
        row["mem_kb"] = int(lua.num('(function() collectgarbage("collect"); return collectgarbage("count") end)()') or 0)
        row["loaded"] = int(lua.num("#LOADED") or 0)
        sizes.append(row)
        R["days"] = d + 1
    R["day_seconds"] = day_t
    n_ev = int(lua.num("#EVENT_ERRORS") or 0)
    for i in range(1, n_ev + 1):
        R["errors"].append(lua.val(f"EVENT_ERRORS[{i}]"))
    dbg = ""
    p = os.path.join(tmp, "debug.log")
    if os.path.exists(p):
        dbg = open(p, encoding="utf-8", errors="replace").read()
    nlogs = int(lua.num("#LOGS") or 0)
    logs = [lua.val(f"LOGS[{i}]") or "" for i in range(1, nlogs + 1)]
    lines = dbg.splitlines() + logs
    # реестр здоровья KMM_Gov (2026-11-16): навсегда — «disabled until restart» (модуль без Gov) и «health <ключ>: OFF (»;
    # отказ с повтором — «failed, retry in N s», «health <ключ>: fail #n -> pause», «PAUSED <имя> N s»; восстановление — «recovered after».
    # В стенде пауза = механика упала на заглушке: считается в итог так же, как раньше «disabled until restart».
    off_rx = re.compile(r"disabled until restart|disabled for|\bhealth \S+: OFF \(")
    pause_rx = re.compile(r"failed, retry in \d+|\bhealth \S+: fail #\d+ -> pause|\bPAUSED \S+ \d+ s")
    R["disabled"] = sorted({l.strip()[:400] for l in lines if off_rx.search(l)})
    R["paused"] = sorted({l.strip()[:400] for l in lines if pause_rx.search(l) and not off_rx.search(l)})
    R["recovered"] = sorted({l.strip()[:300] for l in lines if re.search(r"\bhealth \S+: recovered after \d+ fails", l)})
    R["bad_lines"] = sorted({l.strip()[:300] for l in lines if re.search(r"(?i)\berror\b|traceback|attempt to|bad argument", l)
                             and not off_rx.search(l) and not pause_rx.search(l)})[:40]
    R["flags"] = {}
    for lab, g in GLOBAL_OF.items():
        v = lua.val("(function() local m = rawget(_G, '%s'); if not m then return 'MISSING' end; if type(m.disabled) == 'function' then local t = {}; for k, x in pairs(m.disabled()) do if x then t[#t+1] = k end end; table.sort(t); return table.concat(t, ',') end; return m.disabled and 'DISABLED' or '' end)()" % g)
        if v:
            R["flags"][lab] = v
    lua.run("ACTFN = function() " + ACTIVITY_LUA + " end", "act")
    R["activity"] = lua.val("ACTFN()") or ""
    nu = lua.val(LIST_UNKNOWN_LUA) or ""
    unk = collections.defaultdict(list)
    for row in nu.splitlines():
        k, loc, n = row.split("\t")
        unk[k].append((loc, int(n)))
    R["unknown"] = dict(unk)
    if len(sizes) >= 2:
        a, z = sizes[0], sizes[-1]
        for k in list(PROBES) + ["mem_kb"]:
            lim = 20000 if k == "mem_kb" else 2000
            if (z[k] > 3 * max(a[k], 1) and z[k] - a[k] > lim) or (k != "mem_kb" and z[k] > 150000):
                R["growth"].append(f"{k}: {a[k]} -> {z[k]} (сутки 1 -> {z['day']})")
    R["sizes"] = sizes
    R["stats"] = {k: lua.num(f"WSTATS.{k}") for k in ("declared_dead", "added", "removed", "msgs", "spawn_calls")}
    for k, ex in (("spawns", "#SPAWNS"), ("setrel", "SETREL"), ("runaway", "RUNAWAY"), ("player_steps", "PLAYER_STEPS or 0"), ("combats", "COMBATS or 0"), ("created_items", "CREATED")):
        R["stats"][k] = int(lua.num(ex) or 0)
    R["secs"] = time.time() - t0
    return R


def report(R, refm):
    print(f"=== {R['save']}: {R['days']} сут., {R['secs']:.0f} с (по суткам: {', '.join('%.1f' % t for t in R['day_seconds'])}) ===")
    print("мир:", R["world"])
    print("итоги движка-заглушки:", R["stats"])
    print("активность модулей (их же счётчики):")
    for ln in R["activity"].splitlines():
        print("  " + ln[:420])
    print(f"ошибки Lua из обработчиков: {len(R['errors'])}")
    seen = set()
    for e in R["errors"]:
        k = e.split("\n")[0][:200]
        if k not in seen:
            seen.add(k)
            print("  ERR", e[:900].replace("\n", "\n      "))
    print("ошибки загрузки модулей:", R["load_errors"] or "нет")
    print(f"самоотключения навсегда — СЛОМАНО ({len(R['disabled'])}):")
    for l in R["disabled"]:
        print("  OFF", l[:300])
    print(f"паузы реестра — отказ с повтором ({len(R['paused'])}):")
    for l in R["paused"]:
        print("  PAUSE", l[:300])
    print(f"восстановления после паузы ({len(R['recovered'])}):")
    for l in R["recovered"]:
        print("  RECOVERED", l[:300])
    print("флаги .disabled():", R["flags"] or "пусто")
    if R["bad_lines"]:
        print("строки логов с ошибками:")
        for l in R["bad_lines"][:15]:
            print("  LOG", l)
    print(f"неизвестные поля/методы заглушки ({len(R['unknown'])}): [в классе]=справочник знает, заглушка неполна; [у других: ...]=метод есть у других классов, у этого нет (кандидат на несоответствие); [НЕТ в справочнике]=нигде")
    RC = reference_classes()
    for k, locs in sorted(R["unknown"].items()):
        cls, meth = k.split(".", 1)
        if meth in RC.get(cls, ()):
            tag = "[в классе]"
        elif meth in refm:
            tag = "[у других: " + ",".join(sorted(c for c, v in RC.items() if meth in v and "::" not in c)[:4]) + "]"
        else:
            tag = "[НЕТ в справочнике]"
        print(f"  {tag} {k:34s} " + ", ".join(f"{l}x{n}" for l, n in sorted(locs)[:4]))
    print("рост таблиц:", R["growth"] or "нет")
    if R["sizes"]:
        a, z = R["sizes"][0], R["sizes"][-1]
        print("  размеры сутки 1 -> %d: " % z["day"] + ", ".join(f"{k} {a[k]}->{z[k]}" for k in list(PROBES) + ["mem_kb", "loaded"]))


def main():
    args = sys.argv[1:]
    days, radius, tick_s = 8, 7000, 2.0
    saves = []
    i = 0
    while i < len(args):
        if args[i] == "--days":
            days = int(args[i + 1]); i += 2
        elif args[i] == "--radius":
            radius = float(args[i + 1]); i += 2
        elif args[i] == "--tick":
            tick_s = float(args[i + 1]); i += 2
        else:
            saves.append(args[i]); i += 1
    saves = saves or ["quicksave", "KMM_Test2"]
    refm, _ = reference_methods()
    bad = 0
    for s in saves:
        R = replay(s, days, tick_s, radius)
        report(R, refm)
        bad += len(R["errors"]) + len(R["load_errors"]) + len(R["disabled"]) + len(R["paused"])
    print("ИТОГ: ошибок Lua/самоотключений/пауз реестра:", bad)
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
