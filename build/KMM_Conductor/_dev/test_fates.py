"""Offline test KMM_Fates: far simulation, state size, materialization near player, rename, death. python -I -X utf8 build/KMM_Conductor/_dev/test_fates.py -> OK."""
import ctypes, re, sys, tempfile

DLL = r"C:\Program Files (x86)\Steam\steamapps\workshop\content\233860\3817000612\lua51.dll"
B = r"C:\KenshiModMap\build\KMM_Conductor\scripts\init"
TMP = tempfile.mkdtemp(prefix="kmm_fates_").replace("\\", "/")
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
run("math.randomseed(20261113)", "seed")
for _f in sorted(__import__("glob").glob(B + r"\KMM_Conductor*.lua")): run(open(_f, encoding="utf-8").read(), _f.split("\\")[-1])
run(open(B + r"\KMM_Traces.lua", encoding="utf-8").read(), "KMM_Traces.lua")
run(open(B + r"\KMM_Fates.lua", encoding="utf-8").read(), "KMM_Fates.lua")
run(r'''
N, FAILS = 0, {}
function check(c, what) N = N + 1; if not c then FAILS[#FAILS + 1] = what end end
local C = KMM_Conductor
C.reset()
local TP = C.cfg().params.traces
TP.first_hour_traces = 0; TP.max_per_day = 1000; TP.max_queue = 1000; TP.arrive_enabled = false
TP.bounty = { enabled = false }
local pf = C.cfg().player_faction
C.cfg().params.fates = { watch_s = 1e9 }
local F, T = KMM_Fates, KMM_Traces
-- платуны с лидером для createRandomSquad
MADE = {}
local old = getGameWorld
getGameWorld = function()
  local w = old()
  local orig = w.theFactory.createRandomSquad
  w.theFactory.createRandomSquad = function(self, f, pos, ...)
    local r = orig(self, f, pos, ...)
    local leader = { name = "Nameless Raider", dead = false }
    function leader:setName(n) self.name = n end
    function leader:getName() return self.name end
    function leader:isDead() return self.dead end
    local pl = { isDead = false }
    function pl:getSquadLeader() return leader end
    function pl:getActivePlatoon() return { setName = function() end } end
    MADE[#MADE + 1] = { pl = pl, leader = leader, x = pos.x, z = pos.z, fid = f.id }
    return pl
  end
  return w
end
PCS = {}; CHARS = {}
local pc = MKCH("PC1", pf or "player", 0, 0, { player = true, platoon = "player_squad" })
PCS[1] = pc; CHARS[1] = pc
local function tick(day) DAYV = day; CLOCK = CLOCK + 100; FIRE("GameWorld::charsUpdate", {}) end
local function evcount(prefix) local n = 0; for _, e in ipairs(C.state().events) do if tostring(e.type):sub(1, #prefix) == prefix then n = n + 1 end end; return n end
local function nh() local n = 0; for _ in pairs(F.state().H) do n = n + 1 end; return n end
local function ser(t, d)
  d = d or 0; if type(t) ~= "table" then return tostring(t) end
  local o = {}; for k, v in pairs(t) do o[#o + 1] = tostring(k) .. "=" .. ser(v, d + 1) end; return "{" .. table.concat(o, ",") .. "}"
end
-- 1) посев
tick(500)
check(F.state() and nh() >= 20 and nh() <= 40, "seeded 20..40 heroes: " .. tostring(F.state() and nh()))
local ok_fields = true
for _, h in ipairs(F.heroes()) do if not (h.n and h.f and h.r and h.t and h.t >= 0 and h.t <= 3 and h.x and h.rep) then ok_fields = false end end
check(ok_fields, "hero fields complete")
check(next(F.disabled()) == nil, "module enabled")
-- 2) дальняя симуляция 200 игровых дней (ядро гонит дни само; модуль берёт до 3 дней за тик)
for d = 501, 700 do tick(d) end
check(next(F.disabled()) == nil, "still enabled after 200 days")
check(nh() >= 20 and nh() <= 40, "hero count kept 20..40: " .. nh())
local st = F.stats()
check(st.deaths > 0 and st.rise > 0, "deaths and rises happened: d=" .. st.deaths .. " r=" .. st.rise)
check(st.wound > 0 and st.slave > 0 and (st.defect + st.camp) > 0, "wound/slave/defect-or-camp: " .. st.wound .. "/" .. st.slave .. "/" .. st.defect .. "/" .. st.camp)
check(evcount("fate_") >= 5, "fate_* events in chronicle: " .. evcount("fate_"))
local maxt = 0; for _, h in ipairs(F.heroes()) do if h.t > maxt then maxt = h.t end end
check(maxt >= 1, "someone reached T1+")
local sz = #ser(C.state().ext.fates)
check(sz < 20000, "state size < 20KB: " .. sz)
local le = C.state().events[#C.state().events]
local txt; for i = #C.state().events, 1, -1 do local e = C.state().events[i]; if tostring(e.type):sub(1, 5) == "fate_" then txt = e; break end end
check(txt and txt.text and #txt.text > 10 and txt.leader_name, "event has text + leader_name: " .. tostring(txt and txt.text))
-- 3) материализация: игрок у героя, остальные герои далеко
local hs = F.heroes()
local hero
for _, h in ipairs(hs) do if h.st == "a" then hero = h; break end end
for _, h in ipairs(hs) do if h ~= hero then h.x = (h.x or 0) + 9e6 end end
hero.sp = -1000
F._M.live = {}; F._M.pend = nil
PCS = {}; CHARS = {}
pc = MKCH("PC1", pf or "player", hero.x + 300, hero.z + 300, { player = true, platoon = "player_squad" })
PCS[1] = pc; CHARS[1] = pc
local base = (T.stats().by_tag or {}).fate or 0
local function fate_n() return ((T.stats().by_tag or {}).fate or 0) - base end
local function mine() for i = #MADE, 1, -1 do local m = MADE[i]; if m.leader.name == hero.n then return m end end end
for i = 1, 40 do tick(700); if fate_n() > 0 then break end; CLOCK = CLOCK + 80 end
for i = 1, 40 do CLOCK = CLOCK + 80; FIRE("GameWorld::charsUpdate", {}) end
check(fate_n() == 1, "hero squad requested once: " .. fate_n())
local made = mine()
check(made ~= nil, "leader renamed to hero name " .. hero.n)
for i = 1, 60 do CLOCK = CLOCK + 80; FIRE("GameWorld::charsUpdate", {}) end
check(fate_n() == 1, "cooldown holds: " .. fate_n())
-- 4) гибель лидера рядом с игроком
local nd = F.stats().slain
if not made then made = { leader = {} } end
local ev0 = evcount("fate_death")
made.leader.dead = true
for i = 1, 5 do CLOCK = CLOCK + 80; FIRE("GameWorld::charsUpdate", {}) end
check(F.stats().slain == nd + 1, "slain recorded")
check(evcount("fate_death") >= ev0 and not F.state().H["h" .. hero.i], "hero removed from fates after leader death")
check(nh() >= 20, "hero replaced: " .. nh())
RESULT = #FAILS == 0 and ("OK " .. N) or ("FAIL: " .. table.concat(FAILS, "; "))
''', "test")
run("")
L.lua_getfield.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_char_p]
L.lua_getfield(st, -10002, b"RESULT")
r = L.lua_tolstring(st, -1, None).decode()
print(r)
sys.exit(0 if r.startswith("OK") else 1)
