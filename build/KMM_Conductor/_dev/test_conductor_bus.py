"""Офлайн-тест шины подписчиков и слотов stock/town дирижёра (LuaJIT из KenshiLua, без игры).
python -I -X utf8 build/KMM_Conductor/_dev/test_conductor_bus.py   → «OK n checks», код 1 при провале.
Пути C:/KenshiModMap/logs/ перенаправлены во временную папку."""
import ctypes
import os
import sys
import tempfile

DLL = r"C:\Program Files (x86)\Steam\steamapps\workshop\content\233860\3817000612\lua51.dll"
SCRIPT = r"C:\KenshiModMap\build\KMM_Conductor\scripts\init\KMM_Conductor.lua"
TMP = tempfile.mkdtemp(prefix="kmm_bus_").replace("\\", "/")

L = ctypes.CDLL(DLL)
L.luaL_newstate.restype = ctypes.c_void_p
L.luaL_openlibs.argtypes = [ctypes.c_void_p]
L.luaL_loadstring.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
L.lua_pcall.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int]
L.lua_tolstring.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p]
L.lua_tolstring.restype = ctypes.c_char_p
L.lua_settop.argtypes = [ctypes.c_void_p, ctypes.c_int]
st = L.luaL_newstate()
L.luaL_openlibs(st)


def run(code, name="chunk"):
    if L.luaL_loadstring(st, code.encode("utf-8")) or L.lua_pcall(st, 0, 0, 0):
        msg = L.lua_tolstring(st, -1, None)
        L.lua_settop(st, 0)
        raise RuntimeError(f"{name}: {msg.decode('utf-8', 'replace') if msg else '?'}")


run(f'''
local real_open = io.open
io.open = function(p, m) p = tostring(p):gsub("^C:/KenshiModMap/logs/", "{TMP}/"):gsub("^C:/KenshiModMap/state/", "{TMP}/"); return real_open(p, m) end; local __rr = os.remove; os.remove = function(p) p = tostring(p):gsub("^C:/KenshiModMap/state/", "{TMP}/"); return __rr(p) end
KenshiLua = {{ log = function(s) end }}
Events = {{ h = {{}} }}
function Events.on(n, f) Events.h[n] = f end
function getGameWorld() error("no game") end
function getPlayerInterface() error("no game") end
''', "stubs")
for _f in sorted(__import__("glob").glob(SCRIPT.replace("KMM_Conductor.lua", "KMM_Conductor*.lua"))): run(open(_f, encoding="utf-8").read(), _f.split("\\")[-1])
run(r'''
N, FAILS = 0, {}
local function check(c, what) N = N + 1; if not c then FAILS[#FAILS + 1] = what end end
local C = KMM_Conductor
math.randomseed(5)
C.reset()
local S = C.state()
check(type(S.stock) == "table" and type(S.town) == "table", "fresh_state has stock/town slots")
check(C.stock_state() == S.stock and C.town_state() == S.town, "stock_state/town_state return slots")

local got = { stock = 0, star = 0, exact = 0, town = 0, bad = 0 }
local id_stock = C.subscribe("stock_*", function(ev) got.stock = got.stock + 1; check(ev.type:sub(1, 6) == "stock_", "stock_* gets only stock_ " .. ev.type) end)
local id_bad = C.subscribe("*", function(ev) got.bad = got.bad + 1; error("boom from bad subscriber") end)
local id_star = C.subscribe("*", function(ev) got.star = got.star + 1 end)
local id_exact = C.subscribe("town_captured", function(ev) got.exact = got.exact + 1 end)
local id_town = C.subscribe("town_*", function(ev) got.town = got.town + 1 end)
check(type(id_stock) == "number" and id_stock ~= id_star, "subscribe returns distinct ids")
check(not pcall(C.subscribe, "x", 5) and not pcall(C.subscribe, "", function() end), "subscribe validates arguments")

C.advance(0)
local ev = C.emit({ type = "stock_shortage", town_sid = "t1", town_name = "Testtown", text = "metal ran out" })
check(ev and ev.id and ev.day, "emit returns event with id/day")
C.emit({ type = "stock_glut", town_sid = "t1" })
C.emit({ type = "town_work", town_sid = "t1" })
C.emit({ type = "town_captured", town_sid = "t1" })
check(got.bad == 1, "bad subscriber called once then disabled (" .. got.bad .. ")")
check(got.stock == 2, "stock_* got 2 (" .. got.stock .. ")")
check(got.star == 4, "* got 4 (" .. got.star .. ")")
check(got.exact == 1, "exact town_captured got 1 (" .. got.exact .. ")")
check(got.town == 2, "town_* got town_work + town_captured (" .. got.town .. ")")
local found = 0
for _, e in ipairs(S.events) do if e.type == "stock_shortage" or e.type == "town_work" then found = found + 1 end end
check(found == 2, "stock_/town_ events land in the journal")
check(not pcall(C.emit, { text = "no type" }), "emit without type errors")

-- внутренние события мира тоже идут подписчикам
local before = got.star
for d = 1, 120 do C.advance(d) end
check(got.star > before + 5, "world events reach '*' subscriber (" .. (got.star - before) .. ")")
check(got.stock == 2, "world events do not reach stock_* (" .. got.stock .. ")")

-- отписка
check(C.unsubscribe(id_star) == true and C.unsubscribe(id_star) == false, "unsubscribe true then false")
local s0 = got.star
C.emit({ type = "stock_x" })
check(got.star == s0 and got.stock == 3, "unsubscribed gets nothing, others still do")

-- подписчик, эмитящий из себя: петля обрезается, emit не падает
local loops = 0
local id_loop = C.subscribe("loop_*", function(ev) loops = loops + 1; C.emit({ type = "loop_again" }) end)
local okl = pcall(C.emit, { type = "loop_start" })
check(okl and loops >= 1 and loops <= 5, "re-entrant emit bounded (" .. loops .. ")")
C.unsubscribe(id_loop)

-- сейв/загрузка: слоты сохраняются; старое состояние без слотов получает их
S.stock["t1"] = { food = 12, metal = 3 }
S.town["t1"] = { pop = 40 }
local gd = { sdata = {} }
Events.h["PlayerInterface::serialise"](nil, gd)
Events.h["PlayerInterface::loadFromSerialise"](nil, gd)
local S2 = C.state()
check(S2 ~= S and S2.stock.t1 and S2.stock.t1.food == 12 and S2.town.t1.pop == 40, "stock/town survive save/load")
S2.stock, S2.town = nil, nil
local old = C.serialize()
Events.h["PlayerInterface::loadFromSerialise"](nil, { sdata = { kmm_conductor_state = old } })
local S3 = C.state()
check(type(S3.stock) == "table" and type(S3.town) == "table", "old state without slots gets them on load")

-- PERSIST: sdata при загрузке пуст (как в игре 2026-11-13) -> запасной файл по имени сейва (SaveManager)
SaveManager = { getSingleton = function() return { name = "kmm_selftest_slot", currentGame = "kmm_selftest_slot" } end }
S3.stock["t9"] = { food = 77 }
Events.h["PlayerInterface::serialise"](nil, { sdata = {} })
Events.h["PlayerInterface::loadFromSerialise"](nil, { sdata = {} })
local S4 = C.state()
check(S4 ~= S3 and S4.stock.t9 and S4.stock.t9.food == 77, "state restored from file fallback when sdata empty")
os.remove("C:/KenshiModMap/state/kmm_selftest_slot.kmmstate")
SaveManager = nil

-- PARSER: в игре loadstring ограничен -> разбор без него (loadstring = nil), включая настоящий 600-КБ стейт из сейва (если выгружен)
local _ls, _ld = loadstring, load
loadstring, load = nil, nil
S4.stock["t9"].note = "q" .. string.char(34) .. "b" .. string.char(92) .. "c" .. string.char(10) .. "d"
local str = C.serialize()
Events.h["PlayerInterface::loadFromSerialise"](nil, { sdata = { kmm_conductor_state = str } })
local S5 = C.state()
check(S5 ~= S4 and S5.stock.t9 and S5.stock.t9.note == "q" .. string.char(34) .. "b" .. string.char(92) .. "c" .. string.char(10) .. "d" and S5.stock.t9.food == 77, "parser without loadstring restores state (escapes)")
local fh = io.open("C:/KenshiModMap/build/KMM_Conductor/_dev/fixtures/state_real.txt", "rb")
if fh then
  local real = fh:read("*a"); fh:close()
  Events.h["PlayerInterface::loadFromSerialise"](nil, { sdata = { kmm_conductor_state = real } })
  local S6 = C.state()
  check(S6 ~= S5 and type(S6.events) == "table" and #S6.events > 0, "real save state parsed without loadstring: events " .. tostring(S6.events and #S6.events))
end
loadstring, load = _ls, _ld

-- towns() и day()
local tw = C.towns()
local owned, cities = 0, 0
for _, t in ipairs(tw) do if t.owner then owned = owned + 1 end; if t.kind == "city" then cities = cities + 1 end end
check(#tw > 100 and owned > 50 and cities > 50, string.format("towns(): %d, owned %d, cities %d", #tw, owned, cities))
check(math.abs(C.day() - 120) < 1, "day() = " .. tostring(C.day()))
local dis = C.disabled()
check(next(dis) == nil, "no guarded function disabled")
''', "bus test")

run('local f = io.open("C:/KenshiModMap/logs/bus_result.txt", "w"); f:write(N, "\\n", table.concat(FAILS, "\\n")); f:close()', "collect")
res = open(os.path.join(TMP, "bus_result.txt"), encoding="utf-8").read().split("\n")
n, fails = int(res[0]), [x for x in res[1:] if x]
dbg = os.path.join(TMP, "debug.log")
log = open(dbg, encoding="utf-8").read() if os.path.exists(dbg) else ""
ok_log = "boom from bad subscriber" in log and "disabled until restart" in log
print("debug.log:", log.strip().splitlines()[-1] if log else "(empty)")
if not ok_log:
    fails.append("subscriber error not written to debug.log")
for f in fails:
    print("FAIL:", f)
print(f"{'FAILED' if fails else 'OK'} {n + 1 - len(fails)}/{n + 1} checks")
sys.exit(1 if fails else 0)
