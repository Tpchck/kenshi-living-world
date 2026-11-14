"""Offline test KMM_Nemesis captives: закованный рядом с игроком и вырвавшийся не через его взлом — соперник «escaped» с родной памятью LT_MY_CAPTOR; освобождённый игроком — должник; память мира об игроке — избитый и оставленный жить/сбежавший становится соперником с прозвищем встречи, мститель за убитого, преследование по регионам, встреча с репликой и родной памятью ядра, повторная пощада, гибель. python -I -X utf8 build/KMM_Conductor/_dev/test_nemesis.py -> OK."""
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
C.cfg().params.nemesis = { rival_p_spared = 0, rival_p_fled = 0, avenger_p = 0, escape_p = 1, cooldown_days = 0, follow_p = 1, say_delay_s = 1, linger_s = 30 }
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
    function leader:rememberCharacter(who, tag) self.lua_mem = true end   -- P4: неоднозначный Lua-метод вызываться не должен
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
CharacterPerceptionTags_LongTerm = { LT_MY_LIFESAVER = 2, LT_FREED_ME = 3, LT_DEFEATED_MY_SQUAD_ONCE = 7, LT_KILLED_MY_FRIEND = 9, LT_MY_CAPTOR = 11 }
KMM_Native = { has_memory = function() return true end,   -- P4: долгая память ядра через плагин (remember_lt)
  remember_lt = function(npc, who, tag) npc.mem[#npc.mem + 1] = tag; return true end }
local function tick(day) DAYV = day; CLOCK = CLOCK + 100; FIRE("GameWorld::charsUpdate", {}) end
local function evs(ty) local n, last = 0, nil; for _, e in ipairs(C.state().events) do if e.type == ty then n = n + 1; last = e end end; return n, last end
local D = O._M.data(C)
local rg, town, gang
for nm, r in pairs(D.regions) do if #r.towns > 0 and #r.gangs > 0 then rg, town, gang = nm, r.towns[1], r.gangs[1]; break end end
check(gang, "gang found")
PCS = {}; CHARS = {}
local pc = MKCH("Beep", pf or "player", town.x + 500, town.z + 500, { player = true, platoon = "player_squad" })
PCS[1] = pc; CHARS[1] = pc
tick(500)
local function evs2(ty, deed) local n = 0; for _, e in ipairs(C.state().events) do if e.type == ty and (not deed or e.deed == deed) then n = n + 1 end end; return n end
-- 1) закован рядом — пленник; далеко — нет
local pr = MKCH("Dust Bandit", gang, town.x + 520, town.z + 510, {})
FIRE("Character::setChainedMode", pr, true)
check(NM.captives()[gang .. "|Dust Bandit"], "captive recorded near the player")
local far = MKCH("Far Bandit", gang, town.x + 9000, town.z, {})
FIRE("Character::setChainedMode", far, true)
check(not NM.captives()[gang .. "|Far Bandit"], "chained far away: not our captive")
local own = MKCH("Own Guy", pf, town.x + 510, town.z + 500, {})
FIRE("Character::setChainedMode", own, true)
check(not NM.captives()[pf .. "|Own Guy"], "own faction member is not a captive")
local sc0 = C.self_chaining
check(sc0 and sc0() == false, "conductor exports self_chaining = false at rest")
C.self_chaining = function() return true end
local mat = MKCH("Rumoured Boss", gang, town.x + 515, town.z + 505, {})
FIRE("Character::setChainedMode", mat, true)
C.self_chaining = sc0
check(not NM.captives()[gang .. "|Rumoured Boss"], "chained by the conductor itself (materialize): not a player captive")
-- 2) вырвался сам — соперник escaped
FIRE("Character::setChainedMode", pr, false)
check(not NM.captives()[gang .. "|Dust Bandit"], "captive removed after escape")
check(evs2("nemesis_born", "escaped") == 1, "escaped captive becomes a rival: " .. evs2("nemesis_born", "escaped"))
local r
for _, o in ipairs(NM.rivals()) do if o.pg.deed == "escaped" then r = o end end
local epi = false
for _, e in ipairs(NM._N.EPI.escaped) do if r and r.n:find(e, 1, true) then epi = true end end
check(r and epi and r.pg.place, "escaped epithet and place: " .. tostring(r and r.n))
-- 3) встреча: реплика и родная память «мой тюремщик»
local lead = { name = r.n, said = {}, mem = {} }
function lead:say(s) self.said[#self.said + 1] = s end
function lead:rememberCharacter(who, tag) self.lua_mem = true end
NM.on_spawn(r, lead)
for i = 1, 3 do CLOCK = CLOCK + 5; FIRE("GameWorld::charsUpdate", {}) end
check(lead.said[1] and lead.said[1]:find(r.pg.place, 1, true), "escaped rival names the place: " .. tostring(lead.said[1]))
check(lead.mem[1] == 5 and not lead.lua_mem, "native memory LT_MY_CAPTOR=5 via plugin: " .. tostring(lead.mem[1]))
do   -- P4: нет плагина -> Lua rememberCharacter не вызывается, маркер в лог
  local NN, KN0, log0, LG = KMM_Nemesis._N, KMM_Native, KMM_Nemesis._N.log, {}
  NN.log = function(m) LG[#LG + 1] = tostring(m) end; NN.mem_nonative = nil; KMM_Native = nil
  local n0 = #lead.mem; NN.remember(lead, "LT_MY_CAPTOR")
  check(#lead.mem == n0 and not lead.lua_mem and LG[1] and LG[1]:find("remember: no native", 1, true), "no plugin: no Lua rememberCharacter, marker: " .. tostring(LG[1]))
  NN.log = log0; KMM_Native = KN0
end
-- 4) освобождён взломом игрока — должник, не соперник
local pr2 = MKCH("Sad Slave", gang, town.x + 530, town.z + 500, {})
FIRE("Character::setChainedMode", pr2, true)
FIRE("CharStats::xpLockpicking", { me = pc }, 20, true)
FIRE("Character::setChainedMode", pr2, false)
check(evs2("nemesis_born", "escaped") == 1 and evs2("debt_made", "freed") == 1, "freed by the player: debt, not a rival")
-- 5) лимит пленников
CLOCK = CLOCK + 100
for i = 1, 14 do FIRE("Character::setChainedMode", MKCH("Cap " .. i, gang, town.x + 500 + i, town.z + 500, {}), true) end
local nc = 0; for _ in pairs(NM.captives()) do nc = nc + 1 end
check(nc <= 10, "max_captives respected: " .. nc)
check(next(NM.disabled()) == nil and next(NM.hook_off()) == nil, "nemesis and hooks still enabled")
RESULT = #FAILS == 0 and ("OK " .. N) or ("FAIL: " .. table.concat(FAILS, "; "))
'''.replace("TMPDIR", TMP), "test")
run("")
L.lua_getfield.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_char_p]
L.lua_getfield(st, -10002, b"RESULT")
r = L.lua_tolstring(st, -1, None).decode()
print(r)
sys.exit(0 if r.startswith("OK") else 1)
