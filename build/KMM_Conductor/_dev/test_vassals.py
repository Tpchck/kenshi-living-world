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
N, FAILS = 0, {}
function check(c, what) N = N + 1; if not c then FAILS[#FAILS + 1] = what end end
local C = KMM_Conductor
local tick = Events.h["GameWorld::charsUpdate"]
local fake = 0
os.clock = function() return fake end
math.randomseed(20261114)
tick()
local S = C.state()
local V = C.cfg().vassals
check(V and #V.seed > 30, "vassals config present: " .. tostring(V and #V.seed))
local seeded, vas = 0, 0
for _, t in pairs(S.treaties) do if t.seed then seeded = seeded + 1; if t.type == "vassal" then vas = vas + 1 end end end
check(seeded >= 30 and vas >= 10, "seed treaties at start: " .. seeded .. " vassal " .. vas)
local NA = {}
for _, p in ipairs(V.never_ally) do NA[p[1] .. "|" .. p[2]] = true; NA[p[2] .. "|" .. p[1]] = true end
local bad0 = 0
for _, t in pairs(S.treaties) do if t.active and NA[t.a .. "|" .. t.b] then bad0 = bad0 + 1 end end
check(bad0 == 0, "no banned pair seeded: " .. bad0)
-- нарочно сблизить мятежников и государство: договор всё равно не должен родиться
for _, p in ipairs(V.never_ally) do S.rel[p[1]] = S.rel[p[1]] or {}; S.rel[p[2]] = S.rel[p[2]] or {}; S.rel[p[1]][p[2]] = 60; S.rel[p[2]][p[1]] = 60 end
for i = 1, 360 * 2 * 4 do DAY = i * 0.25; fake = fake + 3; tick() end   -- 2 года
local bad, cl = 0, 0
for _, t in pairs(S.treaties) do if t.active and NA[t.a .. "|" .. t.b] then bad = bad + 1 end end
check(bad == 0, "no treaty between banned pairs after 2 years (rel forced 60): " .. bad)
for _, c in ipairs(V.closure) do
  local ag = {}; for _, x in ipairs(c.against) do ag[x] = true end
  for _, t in pairs(S.treaties) do
    if t.active and (t.a == c.rebel or t.b == c.rebel) and t.type ~= "trade" and t.type ~= "nonaggression" and t.since > 0 then
      local o = (t.a == c.rebel) and t.b or t.a
      for _, u in pairs(S.treaties) do
        if u.active and u.since <= t.since and u.type ~= "trade" and u.type ~= "nonaggression" and (u.a == o or u.b == o) and ag[(u.a == o) and u.b or u.a] then cl = cl + 1 end
      end
    end
  end
end
check(cl == 0, "rebel never signed with an ally/vassal of its enemy: " .. cl)
local bm, towns, goods = 0, {}, {}
for _, e in ipairs(S.events) do if e.type == "black_market" then bm = bm + 1; towns[e.town_name] = true; goods[e.goods] = true; check(not NA[e.a .. "|" .. e.b], "market deal between banned " .. e.text) end end
local nt = 0; for _ in pairs(towns) do nt = nt + 1 end
check(bm >= 12 and nt >= 4 and goods.slaves, "black market deals: " .. bm .. " in " .. nt .. " hubs")
local vleft = 0; for _, t in pairs(S.treaties) do if t.active and t.seed and t.type == "vassal" then vleft = vleft + 1 end end
local br = {}; for k, v in pairs(S.stats.broken) do br[#br + 1] = k .. "=" .. v end
local dead = 0; for _, t in pairs(S.treaties) do if t.seed and t.type == "vassal" and not (S.F[t.a].alive and S.F[t.b].alive) then dead = dead + 1 end end
R = "broken: " .. table.concat(br, ", ") .. " | seed vassal pairs with a dead side: " .. dead .. string.char(10) .. string.format("seeded=%d vassal=%d blocked=%s deals=%d hubs=%d vassals_after_2y=%d signed=%d", seeded, vas, tostring(S.stats.pact_blocked), bm, nt, vleft, S.stats.signed)
""", "scenario")
run('io.stdout:write(R, string.char(10)); for _, f in ipairs(FAILS) do io.stdout:write("FAIL: ", f, string.char(10)) end; '
    'if #FAILS == 0 then io.stdout:write("OK ", N, string.char(10)) end; io.stdout:flush(); RESULT_FAIL = #FAILS', "print")
run('if RESULT_FAIL > 0 then error("fails") end', "rc")
