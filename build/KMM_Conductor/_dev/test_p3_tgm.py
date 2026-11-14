"""Offline test B5 (P3): KMM_Traces TGM — родной Town.tradeGoodsMults. _homeTown — TownBase, приведение TownBase:isTown() -> Town;
запасные источники города (Platoon/Character:getCurrentTownLocation); маркеры «TGM probe OK» / «TGM probe FAIL» в debug.log;
запись TGM.set только после успешной пробы (P.tgm_write=false выключает). python -I -X utf8 build/KMM_Conductor/_dev/test_p3_tgm.py -> OK."""
import ctypes, re, sys, tempfile

DLL = r"C:\Program Files (x86)\Steam\steamapps\workshop\content\233860\3817000612\lua51.dll"
B = r"C:\KenshiModMap\build\KMM_Conductor\scripts\init"
TMP = tempfile.mkdtemp(prefix="kmm_p3_tgm_").replace("\\", "/")
L = ctypes.CDLL(DLL)
L.luaL_newstate.restype = ctypes.c_void_p
for fn, at in [("luaL_openlibs", [ctypes.c_void_p]), ("luaL_loadstring", [ctypes.c_void_p, ctypes.c_char_p]),
               ("lua_pcall", [ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int])]:
    getattr(L, fn).argtypes = at
L.lua_tolstring.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p]
L.lua_tolstring.restype = ctypes.c_char_p
st = L.luaL_newstate()
L.luaL_openlibs(st)


def run(code, name="chunk"):
    if L.luaL_loadstring(st, code.encode("utf-8")) or L.lua_pcall(st, 0, 0, 0):
        msg = L.lua_tolstring(st, -1, None)
        raise RuntimeError(f"{name}: {msg.decode('utf-8', 'replace') if msg else '?'}")


rt = open(r"C:\KenshiModMap\tools\test\test_runtime.py", encoding="utf-8").read()
run(re.search(r"STUBS = r'''(.*?)'''", rt, re.S).group(1).replace("TMPDIR", TMP), "stubs")
run("math.randomseed(20261115)", "seed")
for _f in sorted(__import__("glob").glob(B + r"\KMM_Conductor*.lua")): run(open(_f, encoding="utf-8").read(), _f.split("\\")[-1])
run(open(B + r"\KMM_Traces.lua", encoding="utf-8").read(), "KMM_Traces.lua")
run(r'''
N, FAILS = 0, {}
function check(c, what) N = N + 1; if not c then FAILS[#FAILS + 1] = what end end
local C = KMM_Conductor
C.reset()
local TP = C.cfg().params.traces
TP.first_hour_traces = 0; TP.arrive_enabled = false; TP.bounty = { enabled = false }
DAYV = 500; CLOCK = CLOCK + 100; FIRE("GameWorld::charsUpdate", {})   -- init() Traces: P = params.traces
local TGM = KMM_Traces.tgm
check(TGM and TGM.town_of and TGM.read and TGM.probe and TGM.set, "TGM exported")
local function dbg() local f = io.open("TMPDIR/debug.log", "r"); if not f then return "" end; local s = f:read("*a"); f:close(); return s end

-- Town: поле tradeGoodsMults (копия-таблица, ключи GameData), isTown() возвращает себя
local IRON, BREAD = { name = "Iron Plates", stringID = "iron" }, { name = "Bread", stringID = "bread" }
local TOWN = { tradeGoodsMults = { [IRON] = 1.4, [BREAD] = 0.8 } }
function TOWN:isTown() return self end
function TOWN:getGameData() return { name = "Stack" } end
-- TownBase без поля: isTown() приводит к Town; гнездо: isTown() = nil
local BASE = {}; function BASE:isTown() return TOWN end
local NEST = {}; function NEST:isTown() return nil end
local function plat(home, here) return {
  getOwnerships = function() return { _homeTown = home } end,
  getCurrentTownLocation = function() return here end } end
local function char(here) return { getCurrentTownLocation = function() return here end } end

local t, src = TGM.town_of(plat(BASE, nil), nil)
check(t == TOWN and src == "home", "home TownBase -> isTown() -> Town")
t, src = TGM.town_of(plat(nil, NEST), char(BASE))
check(t == TOWN and src == "char_here", "no home, platoon in nest -> char town: " .. tostring(src))
t, src = TGM.town_of(plat(nil, nil), char(nil))
check(t == nil and src:find("home:nil") and src:find("char_here:nil"), "nothing: reasons listed: " .. tostring(src))
local bad = { getOwnerships = function() error("no ownerships") end, getCurrentTownLocation = function() return nil end }
t, src = TGM.town_of(bad, nil)
check(t == nil and src:find("home:err"), "error swallowed with reason: " .. tostring(src))

local n, info = TGM.read(TOWN)
check(n == 2 and info:find("entries=2") and info:find("table"), "read entries: " .. tostring(info))
n, info = TGM.read({})
check(n == nil and info:find("nil"), "missing field reported")

-- проба: 2 торговца без города, третий — дом-TownBase -> OK, маркер в debug.log; дальше проб нет
TGM.done, TGM.tries, TGM.ok = false, 0, false
check(TGM.set(TOWN, IRON, 9.0) == false and TOWN.tradeGoodsMults[IRON] == 1.4, "no write before probe OK")
check(not TGM.probe(plat(nil, nil), char(nil)), "probe 1: no town")
check(not TGM.probe(plat(NEST, nil), nil), "probe 2: nest only")
check(not TGM.done, "still probing after 2 failures")
local ok, res = TGM.probe(plat(BASE, nil), nil)
check(ok and TGM.done and TGM.ok, "probe 3 OK: " .. tostring(res))
local d = dbg()
check(d:find("TGM probe OK: src=home town Stack: tradeGoodsMults table") ~= nil, "OK marker in debug.log: " .. d)

-- запись (R1): после пробы OK — разрешена по умолчанию (пишет в копию и возвращает её полю); P.tgm_write = false — нет
TP.tgm_write = false
check(TGM.set(TOWN, IRON, 2.0) == false and TOWN.tradeGoodsMults[IRON] == 1.4, "write off with tgm_write=false")
TP.tgm_write = nil
check(TGM.set(TOWN, IRON, 2.0) == true and TOWN.tradeGoodsMults[IRON] == 2.0, "write on after probe OK: value set")

-- провал: после P.tgm_tries торговцев — маркер FAIL с причиной
TGM.done, TGM.tries, TGM.ok = false, 0, false
TP.tgm_tries = 2
TGM.probe(plat(nil, nil), nil); TGM.probe(plat(nil, nil), nil)
check(TGM.done and not TGM.ok, "gave up after tgm_tries")
check(dbg():find("TGM probe FAIL after 2 traders: no Town %(home:nil") ~= nil, "FAIL marker with reason")
check(next(KMM_Traces.disabled()) == nil, "traces still enabled")
RESULT = #FAILS == 0 and ("OK " .. N) or ("FAIL: " .. table.concat(FAILS, "; "))
'''.replace("TMPDIR", TMP), "test")
L.lua_getfield.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_char_p]
L.lua_getfield(st, -10002, b"RESULT")
r = L.lua_tolstring(st, -1, None).decode()
print(r)
sys.exit(0 if r.startswith("OK") else 1)
