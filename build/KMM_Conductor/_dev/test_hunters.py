"""Offline test KMM_Nemesis hunters: охота за головой игрока ведёт постоянный именной охотник — побит и пощажён: сильнее и помнит место; убит: ордер у преемника; память мира об игроке — избитый и оставленный жить/сбежавший становится соперником с прозвищем встречи, мститель за убитого, преследование по регионам, встреча с репликой и родной памятью ядра, повторная пощада, гибель. python -I -X utf8 build/KMM_Conductor/_dev/test_nemesis.py -> OK."""
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
C.cfg().params.nemesis = { rival_p_spared = 1, rival_p_fled = 1, avenger_p = 1, cooldown_days = 0, follow_p = 1, say_delay_s = 1, linger_s = 30 }
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
CharacterPerceptionTags_LongTerm = { LT_MY_LIFESAVER = 2, LT_FREED_ME = 3, LT_DEFEATED_MY_SQUAD_ONCE = 7, LT_KILLED_MY_FRIEND = 9 }
KMM_Native = { has_memory = function() return true end,   -- P4: долгая память ядра через плагин (remember_lt)
  remember_lt = function(npc, who, tag) npc.mem[#npc.mem + 1] = tag; return true end }
local function tick(day) DAYV = day; CLOCK = CLOCK + 100; FIRE("GameWorld::charsUpdate", {}) end
local function evs(ty) local n, last = 0, nil; for _, e in ipairs(C.state().events) do if e.type == ty then n = n + 1; last = e end end; return n, last end
local D = O._M.data(C)
local S = C.state()
local tr = C.read_json("traces.json", "C:/KenshiModMap/build/KMM_Conductor/traces.json")
local F
for fid, f in pairs(S.F) do if f.alive and not f.player and fid ~= pf and tr.factions[fid] and tr.factions[fid].tiers and next(tr.factions[fid].tiers) then F = fid; break end end
check(F, "law faction found")
local rg, town
for nm, r in pairs(D.regions) do if #r.towns > 0 then rg, town = nm, r.towns[1]; break end end
PCS = {}; CHARS = {}
local pc = MKCH("Beep", pf or "player", town.x + 500, town.z + 500, { player = true, platoon = "player_squad" })
local REW = { [F] = 12000 }
pc.crimes = {
  _getHighestBountyFaction = function(self) return FAC(F) end,
  getActualBounty = function(self, fo) return REW[F] end,
}
PCS[1] = pc; CHARS[1] = pc
TP.bounty = { enabled = false, chance = 1.0, check_hours = 1, cooldown_hours = 100000, threshold = 5000, max_active = 9 }
tick(500)
local function hunt()
  local B = T.bounty(); B.last_chk = nil; B.last_hunt = nil; B.act = {}
  local m0 = #MADE
  TP.bounty.enabled = true; B.step(); TP.bounty.enabled = false
  for i = 1, 60 do CLOCK = CLOCK + 80; DAYV = DAYV + 0.0001; FIRE("GameWorld::charsUpdate", {})
    for j = m0 + 1, #MADE do if MADE[j].fid == F and NM.hunters()[F] and MADE[j].leader.name == NM.hunters()[F].n then
      for k = 1, 3 do CLOCK = CLOCK + 5; FIRE("GameWorld::charsUpdate", {}) end
      return MADE[j] end end
  end
end
local function fight(lead, how)
  local pp = pc:getPosition(); function lead:getPosition() return { x = pp.x + 3, y = 0, z = pp.z + 3 } end   -- удар игрока = вплотную
  for i = 1, 3 do NM.on_player_hit(lead, pc) end
  if how == "dead" then lead.dead = true else lead.down = true end
  CLOCK = CLOCK + 5; tick(DAYV + 0.01)
  lead.down = false
  CLOCK = CLOCK + 80; tick(DAYV + 0.01)
end
-- 1) первая охота: именной охотник, реплика с суммой
local h1 = hunt()
local H = NM.hunters()[F]
check(h1 and H and H.met == 1, "named hunter leads the hunt: " .. tostring(H and H.n))
check(h1 and h1.leader.said[1] and h1.leader.said[1]:find("12000", 1, true), "hunter names the bounty: " .. tostring(h1 and h1.leader.said[1]))
check((evs("nemesis_hunter")) == 1, "nemesis_hunter event")
check(NM.hunt_bonus(F) == 0, "no bonus before defeat")
-- 2) уложен и оставлен жить
local name1 = H.n
local nr0 = #NM.rivals()
fight(h1.leader, "down")
local wt = NM._N.where(D, pc:getPosition().x + 3, pc:getPosition().z + 3)
check(H.wins == 1 and wt and H.place == wt.name, "hunter remembers the defeat: wins " .. tostring(H.wins) .. " at " .. tostring(H.place))
check((evs("nemesis_hunter_beaten")) == 1, "beaten event")
check(#NM.rivals() == nr0, "beaten hunter is not turned into an outlaw rival")
check(NM.hunt_bonus(F) == 1, "bonus after defeat")
-- 3) вторая охота: тот же, сильнее, помнит место
local h2 = hunt()
check(h2 and h2.leader.name == name1 and H.met == 2, "same hunter returns")
check(h2 and h2.leader.said[1] and h2.leader.said[1]:find(H.place, 1, true), "hunter recalls the place: " .. tostring(h2 and h2.leader.said[1]))
check(h2 and h2.leader.mem[1] == 7 and not h2.leader.lua_mem, "native memory of the defeat via plugin")
local ehs = 0; for _, e in ipairs(S.events) do if e.type == "bounty_hunters" then ehs = e.tier end end
check(ehs == "T2" or ehs == "T3", "stronger hunt tier: " .. tostring(ehs))
-- 4) убит: преемник
fight(h2.leader, "dead")
local H2 = NM.hunters()[F]
check(H2 and H2.n ~= name1 and H2.heir_of == name1 and H2.met == 0, "heir takes the warrant: " .. tostring(H2 and H2.n))
check((evs("nemesis_hunter_dead")) == 1, "hunter_dead event")
local av = 0; for _, r in ipairs(NM.rivals()) do if r.pg.dead == name1 then av = av + 1 end end
check(av == 0, "no outlaw avenger for a hunter")
local h3 = hunt()
check(h3 and h3.leader.name == H2.n and h3.leader.said[1] and h3.leader.said[1]:find(name1, 1, true), "heir names the dead hunter: " .. tostring(h3 and h3.leader.said[1]))
check(NM.hunt_bonus(F) == 0, "heir starts without bonus")
check(next(NM.disabled()) == nil and next(T.disabled()) == nil, "modules still enabled")
RESULT = #FAILS == 0 and ("OK " .. N) or ("FAIL: " .. table.concat(FAILS, "; "))
'''.replace("TMPDIR", TMP), "test")
run("")
L.lua_getfield.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_char_p]
L.lua_getfield(st, -10002, b"RESULT")
r = L.lua_tolstring(st, -1, None).decode()
print(r)
sys.exit(0 if r.startswith("OK") else 1)
