"""Офлайн-тест KMM_Conductor.lua на LuaJIT из KenshiLua (lua51.dll) с заглушками API игры.
python -I -X utf8 build/KMM_Conductor/_dev/test_conductor.py
Пути C:/KenshiModMap/logs/ внутри скрипта перенаправляются во временную папку — реальные логи не трогаются."""
import ctypes
import os
import tempfile

DLL = r"C:\Program Files (x86)\Steam\steamapps\workshop\content\233860\3817000612\lua51.dll"
SCRIPT = r"C:\KenshiModMap\build\KMM_Conductor\scripts\init\KMM_Conductor.lua"
TMP = tempfile.mkdtemp(prefix="kmm_cond_").replace("\\", "/")

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
assert(Events.h["GameWorld::charsUpdate"], "tick not registered")
assert(Events.h["PlayerInterface::serialise"] and Events.h["PlayerInterface::loadFromSerialise"], "save hooks not registered")
local tick = Events.h["GameWorld::charsUpdate"]
local real_clock = os.clock
local fake = 0
os.clock = function() fake = fake + 10; return fake end   -- каждый тик «прошло 10 с»
math.randomseed(12345)
for i = 0, 240 do DAY = i * 0.25; tick() end              -- 60 игровых дней
local S = KMM_Conductor.state()
local pend = {}
for sid, id in pairs(S.pending) do pend[#pend+1] = sid end
RESULT_EVENTS = #S.events
RESULT_PENDING = #pend
-- материализация: подгружаем всех ожидающих лидеров
for _, sid in ipairs(pend) do LOADED[#LOADED+1] = MKCHAR(sid) end
DAY = DAY + 0.1; tick()
local after = 0; for _ in pairs(S.pending) do after = after + 1 end
RESULT_PENDING_AFTER = after
RESULT_CALLS = #CALLS
-- сейв/загрузка
local gd = { sdata = {} }
Events.h["PlayerInterface::serialise"](nil, gd)
assert(type(gd.sdata["kmm_conductor_state"]) == "string", "state not written to save")
local n_before = #S.events
Events.h["PlayerInterface::loadFromSerialise"](nil, gd)
assert(#KMM_Conductor.state().events == n_before, "journal not restored")
-- откат времени → новый журнал
DAY = 1; tick()
RESULT_AFTER_RESET = #KMM_Conductor.state().events
os.clock = real_clock
""", "simulation")
run('io.stdout:write(string.format("events=%d pending=%d pending_after_materialize=%d calls=%d reset_events=%d\\n", '
    'RESULT_EVENTS, RESULT_PENDING, RESULT_PENDING_AFTER, RESULT_CALLS, RESULT_AFTER_RESET)); io.stdout:flush()', "print")
print("chronicle:")
print(open(os.path.join(TMP, "chronicle.log"), encoding="utf-8").read())
run('for _, s in ipairs(LOGS) do if s:find("config") or s:find("loaded") or s:find("failed") then io.stdout:write(s, "\\n") end end; io.stdout:flush()', "logs")
