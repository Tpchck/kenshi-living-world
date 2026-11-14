"""Offline test KMM_Nemesis scars: свой лежал без сознания — встав, роняет слово (с паузой); через scar_days вспоминает место (ближайший город), раз на шрам. Ниже — шапка из test_banter: свой из отряда игрока коротко отзывается о деле (соперник, должник, охотник, лидер), с паузой, только живой; память мира об игроке — избитый и оставленный жить/сбежавший становится соперником с прозвищем встречи, мститель за убитого, преследование по регионам, встреча с репликой и родной памятью ядра, повторная пощада, гибель. python -I -X utf8 build/KMM_Conductor/_dev/test_nemesis.py -> OK."""
import ctypes, re, sys, tempfile

DLL = r"C:\Program Files (x86)\Steam\steamapps\workshop\content\233860\3817000612\lua51.dll"
B = r"C:\KenshiModMap\build\KMM_Conductor\scripts\init"
TMP = tempfile.mkdtemp(prefix="kmm_outlaws_").replace("\\", "/")
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
run(open(B + r"\KMM_Outlaws.lua", encoding="utf-8").read(), "KMM_Outlaws.lua")
run(open(B + r"\KMM_Nemesis.lua", encoding="utf-8").read(), "KMM_Nemesis.lua")
run(r'''
N, FAILS = 0, {}
function check(c, what) N = N + 1; if not c then FAILS[#FAILS + 1] = what end end
local C = KMM_Conductor
C.reset()
local TP = C.cfg().params.traces
TP.first_hour_traces = 0; TP.max_per_day = 1000; TP.max_queue = 1000; TP.arrive_enabled = false
TP.bounty = { enabled = false }
local pf = C.cfg().player_faction
C.cfg().params.outlaws = { watch_s = 1e9, sdir = "TMPDIR/", spawn_p = 1, cd_h = 0, native_bounty = false }
C.cfg().params.nemesis = { night = false, rival_p_spared = 1, rival_p_fled = 0, avenger_p = 1, cooldown_days = 0, follow_p = 1, say_delay_s = 1, linger_s = 30 }
local O, T, NM = KMM_Outlaws, KMM_Traces, KMM_Nemesis
MADE = {}
local old = getGameWorld
getGameWorld = function()
  local w = old()
  w.theFactory.createRandomSquad = function(self, f, pos, ...)
    local leader = { name = "Some Raider", dead = false, said = {}, mem = {} }
    leader.crimes = { unfairAddToBounty = function() end, getTotalBounty = function() return 0 end }
    function leader:setName(n) self.name = n end
    function leader:getName() return self.name end
    function leader:isDead() return self.dead end
    function leader:isDown() return self.down or false end
    function leader:say(s) self.said[#self.said + 1] = s end
    function leader:rememberCharacter(who, tag) self.mem[#self.mem + 1] = tag end
    function leader:getFaction() return FAC(f.id) end
    function leader:getPosition() return { x = pos.x, y = 0, z = pos.z } end
    local pl = { isDead = false }
    function pl:getSquadLeader() return leader end
    function pl:getActivePlatoon() return { setName = function() end } end
    MADE[#MADE + 1] = { pl = pl, leader = leader, x = pos.x, z = pos.z, fid = f.id }
    return pl
  end
  if not w.factionMgr then w.factionMgr = {} end
  if not w.factionMgr.getFactionByStringID then w.factionMgr.getFactionByStringID = function(self, sid) return { id = sid } end end
  return w
end
CharacterPerceptionTags_LongTerm = { LT_DEFEATED_MY_SQUAD_ONCE = 7, LT_KILLED_MY_FRIEND = 9 }
local function tick(day) DAYV = day; CLOCK = CLOCK + 100; FIRE("GameWorld::charsUpdate", {}) end
local function evs(ty) local n, last = 0, nil; for _, e in ipairs(C.state().events) do if e.type == ty then n = n + 1; last = e end end; return n, last end
local D = O._M.data(C)
local rg, town
for nm, r in pairs(D.regions) do if #r.towns > 0 then rg, town = nm, r.towns[1]; break end end
local function mate_unused(nm, opt)
  local c = MKCH(nm, pf or "player", town.x + 500, town.z + 500, opt or { player = true, platoon = "player_squad" })
  c.said = {}; function c:say(s) self.said[#self.said + 1] = s end
  return c
end

local P_ = C.cfg().params.nemesis
P_.scar_up_p = 1; P_.greet = false; P_.chronicle = false
ORDER = {}
local function mate2(nm)
  local c = MKCH(nm, pf or "player", town.x + 100, town.z + 100, { player = true, platoon = "player_squad" })
  c.said = {}; c.dn = false
  function c:say(s) self.said[#self.said + 1] = s; ORDER[#ORDER + 1] = { nm, s } end
  function c:isDown() return self.dn end
  return c
end
local a, b = mate2("Beep"), mate2("Ruka")
PCS = { a, b }; CHARS = { a, b }
local function fire(dt) CLOCK = CLOCK + dt; FIRE("GameWorld::charsUpdate", {}) end
local S = C.state()
for i = #S.events, 1, -1 do table.remove(S.events, i) end
tick(500); fire(5)
local placeT = NM._N.where(D, town.x + 100, town.z + 100)
a.dn = true; fire(5)
check(#a.said == 0, "lying down: silent")
a.dn = false; fire(5); fire(5)
local okU = false; for _, l in ipairs(NM._N.AMB.up) do if a.said[#a.said] == l then okU = true end end
check(#a.said == 1 and okU, "got up: recovery line from the same character")
local sc = NM._N.state(S).scars and NM._N.state(S).scars["Beep"]
check(sc and sc.place == placeT.name, "scar remembers nearest town: " .. tostring(sc and sc.place))
b.dn = true; fire(5); b.dn = false; fire(5); fire(5)
check(#b.said == 0, "second recovery within 60 s: no extra line (gap)")
fire(700); fire(5)
local function scar_lines(c) local n = 0; for _, l in ipairs(c.said) do if l:find(placeT.name, 1, true) then n = n + 1 end end; return n end
check(scar_lines(a) == 0, "same day: scar not recalled yet")
for i = #S.events, 1, -1 do table.remove(S.events, i) end
tick(501.5); for i = #S.events, 1, -1 do table.remove(S.events, i) end
fire(700); fire(5)
check(scar_lines(a) >= 1 and scar_lines(a) + scar_lines(b) >= 1, "a day later: scar recalled by its owner")
for i = 1, 3 do for j = #S.events, 1, -1 do table.remove(S.events, j) end; fire(700); fire(5) end
check(scar_lines(a) == 1 and scar_lines(b) == 1, "each scar recalled once, by its own owner")
for i = 1, 3 do fire(700); fire(5) end
check(scar_lines(a) + scar_lines(b) == 2, "no repeats")
check(next(NM.disabled()) == nil, "nemesis still enabled")
RESULT = #FAILS == 0 and ("OK " .. N) or ("FAIL: " .. table.concat(FAILS, "; "))
'''.replace("TMPDIR", TMP), "test")
run("")
L.lua_getfield.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_char_p]
L.lua_getfield(st, -10002, b"RESULT")
r = L.lua_tolstring(st, -1, None).decode()
print(r)
sys.exit(0 if r.startswith("OK") else 1)
