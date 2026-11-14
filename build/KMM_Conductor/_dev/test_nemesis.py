"""Offline test KMM_Nemesis: память мира об игроке — избитый и оставленный жить/сбежавший становится соперником с прозвищем встречи, мститель за убитого, преследование по регионам, встреча с репликой и родной памятью ядра, повторная пощада, гибель. python -I -X utf8 build/KMM_Conductor/_dev/test_nemesis.py -> OK."""
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
C.cfg().params.nemesis = { rival_p_spared = 1, rival_p_fled = 0, avenger_p = 1, cooldown_days = 0, follow_p = 1, say_delay_s = 1, linger_s = 30, ambient = false, company = false }
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
CharacterPerceptionTags_LongTerm = { LT_DEFEATED_MY_SQUAD_ONCE = 7, LT_KILLED_MY_FRIEND = 9 }
KMM_Native = { has_memory = function() return true end,   -- P4: долгая память ядра через плагин (remember_lt)
  remember_lt = function(npc, who, tag) npc.mem[#npc.mem + 1] = tag; return true end }
local function tick(day) DAYV = day; CLOCK = CLOCK + 100; FIRE("GameWorld::charsUpdate", {}) end
local function evs(ty) local n, last = 0, nil; for _, e in ipairs(C.state().events) do if e.type == ty then n = n + 1; last = e end end; return n, last end
local D = O._M.data(C)
-- город и банда региона
local rg, town, gang
for nm, r in pairs(D.regions) do if #r.towns > 0 and #r.gangs > 0 then rg, town, gang = nm, r.towns[1], r.gangs[1]; break end end
check(rg and town and gang, "region with town and gang")
PCS = {}; CHARS = {}
local pc = MKCH("Beep", pf or "player", town.x + 500, town.z + 500, { player = true, platoon = "player_squad" })
PCS[1] = pc; CHARS[1] = pc
tick(500)
local nw0 = 0; for _ in pairs(O.state().L) do nw0 = nw0 + 1 end
check(nw0 >= 5, "outlaws seeded: " .. nw0)
-- 1) избит и оставлен жить -> соперник
local v = MKCH("Hungry Bandit", gang, town.x + 800, town.z + 800, { down = true })
for i = 1, 3 do NM.on_player_hit(v, pc) end
check(next(NM._N.cand) ~= nil, "candidate recorded")
CLOCK = CLOCK + 50; tick(500.2)
check((evs("nemesis_born")) == 0, "still lying next to the player: undecided")
function v:isDown() return false end   -- встал и ушёл
CLOCK = CLOCK + 50; tick(500.3)
local nb, eb = evs("nemesis_born")
check(nb == 1 and eb and eb.deed == "spared", "rival born after being spared: " .. nb)
local r1 = NM.rivals()[1]
check(r1 and r1.pg and r1.pg.gen and not r1.n:find("Hungry Bandit") and r1.ek == "grudge", "generic name replaced, grudge epithet: " .. tostring(r1 and r1.n))
local wt1 = NM._N.where(D, town.x + 800, town.z + 800)
check(r1 and wt1 and r1.pg.place == wt1.name, "place of the deed remembered (nearest town): " .. tostring(r1 and r1.pg.place))
-- 2) убит вожак -> мститель
local v2 = MKCH("Grand Tusk", gang, town.x + 900, town.z + 900, {})
NM.on_player_hit(v2, pc); NM.on_player_hit(v2, pc); v2.dead = true
CLOCK = CLOCK + 5; tick(501)
local na, ea = evs("nemesis_born")
local av; for _, r in ipairs(NM.rivals()) do if r.pg.deed == "avenger" then av = r end end
check(av and av.pg.dead == "Grand Tusk" and av.n:find("Oathsworn"), "avenger sworn for the dead: " .. tostring(av and av.n))
-- 3) лимит соперников
C.cfg().params.nemesis.max_rivals = 2
local v3 = MKCH("Other Thug", gang, town.x, town.z, { down = true })
NM.on_player_hit(v3, pc); NM.on_player_hit(v3, pc)
CLOCK = CLOCK + 5; tick(501.4); function v3:isDown() return false end
CLOCK = CLOCK + 50; tick(501.5)
check(#NM.rivals() == 2, "max_rivals respected: " .. #NM.rivals())
-- 4) преследование: игрок ушёл в другой регион
local rg2, town2
for nm, r in pairs(D.regions) do if nm ~= rg and #r.towns > 0 then rg2, town2 = nm, r.towns[1]; break end end
PCS[1] = MKCH("Beep", pf or "player", town2.x + 300, town2.z + 300, { player = true, platoon = "player_squad" }); CHARS = { PCS[1] }
for d = 502, 504 do tick(d) end
check(r1.r == rg2 and r1.hr == rg2, "rival follows the player to " .. tostring(rg2) .. ": " .. tostring(r1.r))
check((evs("nemesis_trail")) >= 1, "trail rumor emitted")
-- 5) встреча: спавн у игрока, имя, реплика, родная память
for _, o in ipairs(O.wanted()) do if o ~= r1 then o.x = (o.x or 0) + 9e6 end end
r1.x, r1.z, r1.sp = town2.x + 600, town2.z + 600, -1000
O._M.live = {}; O._M.pend = nil
local m0 = #MADE
local function mine() for i = #MADE, m0 + 1, -1 do if MADE[i].leader.name == r1.n then return MADE[i] end end end
for i = 1, 40 do
  for _, o in ipairs(O.wanted()) do if o ~= r1 and (o.x or 0) < 5e6 then o.x = (o.x or 0) + 9e6 end end   -- новые местные тоже подальше
  CLOCK = CLOCK + 80; tick(504.5); if mine() then break end
end
local mk = mine()
check(#MADE > m0 and mk.leader.name == r1.n, "rival squad spawned, leader named " .. r1.n)
check((evs("nemesis_return")) >= 1, "nemesis_return event: " .. evs("nemesis_return"))
for i = 1, 3 do CLOCK = CLOCK + 5; FIRE("GameWorld::charsUpdate", {}) end
check(mk and #mk.leader.said == 1 and mk.leader.said[1]:find(r1.pg.place, 1, true), "leader taunts with the place: " .. tostring(mk and mk.leader.said[1]))
check(mk and mk.leader.mem[1] == 7 and not mk.leader.lua_mem, "native memory LT_DEFEATED_MY_SQUAD_ONCE via plugin, no Lua rememberCharacter")
-- 6) снова уложен и оставлен жить -> растёт
local t0, n0 = r1.t, r1.n
mk.leader.down = true
NM.on_player_hit(mk.leader, PCS[1]); NM.on_player_hit(mk.leader, PCS[1])
CLOCK = CLOCK + 5; tick(504.9); mk.leader.down = false
CLOCK = CLOCK + 50; tick(505)
check(r1.pg.met == 2 and r1.t >= math.min(3, t0 + 1) and r1.n ~= n0, "spared again: met 2, tier up, new epithet " .. r1.n)
-- 7) убит окончательно
NM.on_player_hit(mk.leader, PCS[1]); NM.on_player_hit(mk.leader, PCS[1])
check(mk.leader.name == r1.n, "live leader renamed in place: " .. tostring(mk.leader.name))
mk.leader.dead = true
CLOCK = CLOCK + 5; tick(505.5)
local nd_, ed_ = evs("nemesis_dead")
check(nd_ == 1 and ed_.by_player == true and not O.state().L["o" .. r1.i], "nemesis_dead by player, removed: " .. evs("nemesis_dead") .. " rivals " .. #NM.rivals() .. " outlaw_dead " .. evs("outlaw_dead"))
local navg = 0; for _, r in ipairs(NM.rivals()) do if r.pg.dead == r1.n then navg = navg + 1 end end
check(navg == 0, "no avenger sworn for the rival himself")
check(next(NM.disabled()) == nil and next(O.disabled()) == nil, "modules still enabled")
RESULT = #FAILS == 0 and ("OK " .. N) or ("FAIL: " .. table.concat(FAILS, "; "))
'''.replace("TMPDIR", TMP), "test")
run("")
L.lua_getfield.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_char_p]
L.lua_getfield(st, -10002, b"RESULT")
r = L.lua_tolstring(st, -1, None).decode()
print(r)
sys.exit(0 if r.startswith("OK") else 1)
