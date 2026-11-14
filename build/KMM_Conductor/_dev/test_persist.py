"""PERSIST-2: запасное состояние мира state/last.kmmstate с отпечатком партии. Офлайн-тест KMM_Conductor.lua на LuaJIT из KenshiLua (lua51.dll) с заглушками API игры.
python -I -X utf8 build/KMM_Conductor/_dev/test_conductor.py
Пути C:/KenshiModMap/logs/ внутри скрипта перенаправляются во временную папку — реальные логи не трогаются."""
import ctypes
import os
import tempfile

DLL = r"C:\Program Files (x86)\Steam\steamapps\workshop\content\233860\3817000612\lua51.dll"
SCRIPT = r"C:\KenshiModMap\build\KMM_Conductor\scripts\init\KMM_Conductor.lua"
TMP = tempfile.mkdtemp(prefix="kmm_persist_").replace("\\", "/")

L = ctypes.CDLL(DLL)
L.luaL_newstate.restype = ctypes.c_void_p
L.luaL_openlibs.argtypes = [ctypes.c_void_p]
L.luaL_loadstring.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
L.luaL_loadfile.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
L.lua_pcall.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int]
L.lua_tolstring.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p]
L.lua_tolstring.restype = ctypes.c_char_p
L.lua_settop.argtypes = [ctypes.c_void_p, ctypes.c_int]
st = L.luaL_newstate()
L.luaL_openlibs(st)


def run(code, name="chunk"):
    rc = L.luaL_loadstring(st, code.encode("utf-8")) or L.lua_pcall(st, 0, 0, 0)
    if rc:
        msg = L.lua_tolstring(st, -1, None)
        L.lua_settop(st, 0)
        raise RuntimeError(f"{name}: {msg.decode('utf-8', 'replace') if msg else rc}")


STUBS = f"""
TMP = "{TMP}"
local real_open = io.open
io.open = function(p, m) p = tostring(p):gsub("^C:/KenshiModMap/logs/", TMP .. "/"):gsub("^C:/KenshiModMap/state/", TMP .. "/"); return real_open(p, m) end; local __rr = os.remove; os.remove = function(p) p = tostring(p):gsub("^C:/KenshiModMap/state/", TMP .. "/"); return __rr(p) end
KenshiLua = {{ log = function(s) LOGS[#LOGS+1] = s end }}
LOGS = {{}}
Events = {{ h = {{}} }}
function Events.on(n, f) Events.h[n] = f end
DAY = 0
CALLS = {{}}
local function mkchar(sid, name)
  local c = {{ sid = sid, dead = false }}
  function c:getGameData() return {{ stringID = self.sid }} end
  function c:isPlayerCharacter() return false end
  function c:isDead() return self.dead end
  function c:declareDead() self.dead = true; CALLS[#CALLS+1] = "declareDead " .. self.sid end
  function c:getHandle() return "hand:" .. self.sid end
  function c:setChainedMode(on, owner) CALLS[#CALLS+1] = "setChainedMode " .. tostring(on) .. " " .. self.sid end
  function c:uniqueStateUpdate() end
  return c
end
MKCHAR = mkchar
LOADED = {{}}
local world = {{ factionMgr = {{}} }}
function world:getTimeStamp_inGameHours() return {{ getTotalDays = function() return DAY end }} end
function world.factionMgr:getFactionByStringID(sid) return {{ getFactionSize = function() return 40 end }} end
function world:getCharacterUpdateList() local s = {{}}; for _, c in ipairs(LOADED) do s[c] = true end; return s end
function getGameWorld() return world end
"""
run(STUBS, "stubs")
for _f in sorted(__import__("glob").glob(SCRIPT.replace("KMM_Conductor.lua", "KMM_Conductor*.lua"))): run(open(_f, encoding="utf-8").read(), _f.split("\\")[-1])  # компиляция + регистрация
run("""
local tick = Events.h["GameWorld::charsUpdate"]
local save, load = Events.h["PlayerInterface::serialise"], Events.h["PlayerInterface::loadFromSerialise"]
local N, FAILS = 0, {}
local function check(c, w) N = N + 1; if not c then FAILS[#FAILS + 1] = w end end
local real_clock = os.clock; local fake = 0
os.clock = function() fake = fake + 10; return fake end
math.randomseed(7)
PARTY = {}
local function mkpc(n) return { getName = function() return n end, getPosition = function() return { x = 0, y = 0, z = 0 } end } end
function getPlayerInterface() return { getAllPlayerCharacters = function() local t = {}; for i, n in ipairs(PARTY) do t[i] = mkpc(n) end; return t end } end
PARTY = { "Beep", "Ruka", "Hamut" }
for i = 0, 80 do DAY = i * 0.25; tick() end
local S1 = KMM_Conductor.state()
local ev1 = #S1.events
check(ev1 > 0, "world produced events: " .. ev1)
save(nil, { sdata = {} })   -- сейв: запись в sdata + last.kmmstate
local f = io.open(TMP .. "/last.kmmstate", "r"); check(f ~= nil, "last.kmmstate written"); if f then f:close() end
-- 1) загрузка, где sdata пуст (как в игре 13.11): новый мир, затем на первом тике с партией — состояние из last-файла
local broken = { sdata = setmetatable({}, { __index = function() return nil end }) }
load(nil, broken)
check(#KMM_Conductor.state().events == 0, "fresh world right after failed load")
PARTY = {}
DAY = 20.1; tick()
check(#KMM_Conductor.state().events <= 1, "waits while party not loaded")
PARTY = { "Hamut", "Beep", "Ruka", "NewGuy" }
DAY = 20.2; tick()
check(#KMM_Conductor.state().events >= ev1, "adopted last-file state for same party: " .. #KMM_Conductor.state().events .. "/" .. ev1)
-- 2) чужая партия: не берём
load(nil, broken)
PARTY = { "Alice", "Bob" }
DAY = 20.3; tick()
check(#KMM_Conductor.state().events < ev1, "other playthrough not adopted")
-- 3) состояние «из будущего» (загружен более ранний сейв той же партии): не берём
load(nil, broken)
PARTY = { "Beep", "Ruka", "Hamut" }
DAY = 3; tick()
check(#KMM_Conductor.state().events < ev1, "future state not adopted for an earlier save")
-- 4) нормальная загрузка из sdata не трогает last-файл
local gd = { sdata = {} }; save(nil, gd)
load(nil, gd); DAY = 20.4; tick()
local okl = false; for _, s in ipairs(LOGS) do if s:find("world state loaded via index", 1, true) then okl = true end end
check(okl, "regular sdata load still works")
os.clock = real_clock
RESULT = #FAILS == 0 and ("OK " .. N) or ("FAIL: " .. table.concat(FAILS, "; "))
""", "test")
L.lua_getfield.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_char_p]
L.lua_getfield(st, -10002, b"RESULT")
r = L.lua_tolstring(st, -1, None).decode()
print(r)
raise SystemExit(0 if r.startswith("OK") else 1)
