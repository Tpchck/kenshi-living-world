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
  c.isOnScreen = false
  c.pos = {{ x = 0, y = 0, z = 0 }}
  function c:getPosition() return self.pos end
  function c:lineOfSightCheck(pc) return self.los or 0 end
  return c
end
MKCHAR = mkchar
LOADED = {{}}
local world = {{ factionMgr = {{}} }}
function world:getTimeStamp_inGameHours() return {{ getTotalDays = function() return DAY end }} end
function world.factionMgr:getFactionByStringID(sid) return {{ getFactionSize = function() return 40 end }} end
function world:getCharacterUpdateList() local s = {{}}; for _, c in ipairs(LOADED) do s[c] = true end; return s end
function getGameWorld() return world end
PLAYER = {{ getPosition = function() return {{ x = 100000, y = 0, z = 0 }} end }}
function getPlayerInterface() return {{ getAllPlayerCharacters = function() return {{ PLAYER }} end }} end
"""
run(STUBS, "stubs")
for _f in sorted(__import__("glob").glob(SCRIPT.replace("KMM_Conductor.lua", "KMM_Conductor*.lua"))): run(open(_f, encoding="utf-8").read(), _f.split("\\")[-1])
run("""
local tick = Events.h["GameWorld::charsUpdate"]
local fake = 0
os.clock = function() return fake end
math.randomseed(778)
for i = 0, 360 * 4 do DAY = i * 0.25; fake = fake + 3; tick() end   -- 360 игровых дней
local S = KMM_Conductor.state()
R_EVENTS = #S.events
local pend = {}
for sid in pairs(S.pending) do pend[#pend+1] = sid end
R_PENDING = #pend
assert(#pend >= 2, "need >=2 pending for scenario test, got " .. #pend)
-- 1) лидер на экране при загрузке: не применять
local a = MKCHAR(pend[1]); a.isOnScreen = true
LOADED = { a }; fake = fake + 3; tick(); fake = fake + 3; tick()
R_VISIBLE_KEPT = S.pending[pend[1]] ~= nil and 1 or 0
-- он всё ещё загружен, ушёл с экрана, но окно (15 с) прошло: не применять
a.isOnScreen = false; fake = fake + 30; tick()
R_LATE_KEPT = S.pending[pend[1]] ~= nil and 1 or 0
-- выгружен и загружен снова, скрыт: применить
LOADED = {}; fake = fake + 3; tick()
LOADED = { a }; fake = fake + 3; tick()
R_RELOAD_APPLIED = S.pending[pend[1]] == nil and 1 or 0
-- 2) второй лидер рядом с игроком (дистанция < min_distance): не применять; далеко и без видимости: применить
local b = MKCHAR(pend[2]); b.pos = { x = 99500, y = 0, z = 0 }
LOADED = { b }; fake = fake + 3; tick()
R_NEAR_KEPT = S.pending[pend[2]] ~= nil and 1 or 0
LOADED = {}; fake = fake + 3; tick()
b.pos = { x = 0, y = 0, z = 0 }; LOADED = { b }; fake = fake + 3; tick()
R_FAR_APPLIED = S.pending[pend[2]] == nil and 1 or 0
""", "scenario")
run('io.stdout:write(string.format("events_360d=%d pending=%d visible_kept=%d late_kept=%d reload_applied=%d near_kept=%d far_applied=%d" .. string.char(10), '
    'R_EVENTS, R_PENDING, R_VISIBLE_KEPT, R_LATE_KEPT, R_RELOAD_APPLIED, R_NEAR_KEPT, R_FAR_APPLIED)); io.stdout:flush()', "print")
run('for _, s in ipairs(LOGS) do if s:find("config") or s:find("loaded") or s:find("failed") then io.stdout:write(s, string.char(10)) end end; io.stdout:flush()', "logs")
