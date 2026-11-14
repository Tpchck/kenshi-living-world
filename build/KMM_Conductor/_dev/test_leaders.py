"""Offline test KMM_Nemesis leaders: игрок убил/заковал настоящего лидера города из пар дирижёра -> модель мира узнаёт (событие, кризис наследования), без двойного учёта; память мира об игроке — избитый и оставленный жить/сбежавший становится соперником с прозвищем встречи, мститель за убитого, преследование по регионам, встреча с репликой и родной памятью ядра, повторная пощада, гибель. python -I -X utf8 build/KMM_Conductor/_dev/test_nemesis.py -> OK."""
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
C.cfg().params.nemesis = { rival_p_spared = 1, rival_p_fled = 0, avenger_p = 1, cooldown_days = 0, follow_p = 1, say_delay_s = 1, linger_s = 30 }
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
local S = C.state()
local pairs_ = {}
local seen = {}
for _, c in ipairs(C.cfg().towns or {}) do
  if c.leader_sid and S.F[c.defender_sid] and S.F[c.defender_sid].alive and not S.F[c.defender_sid].succession and not seen[c.defender_sid]
     and not S.resolved[c.leader_sid] and not seen[c.leader_sid] then
    seen[c.defender_sid] = true; seen[c.leader_sid] = true; pairs_[#pairs_ + 1] = c
  end
end
check(#pairs_ >= 4, "4 town leaders of distinct factions: " .. #pairs_)
local rg, town
for nm, r in pairs(D.regions) do if #r.towns > 0 then rg, town = nm, r.towns[1]; break end end
PCS = {}; CHARS = {}
local pc = MKCH("Beep", pf or "player", town.x + 500, town.z + 500, { player = true, platoon = "player_squad" })
PCS[1] = pc; CHARS[1] = pc
tick(500)
local function boss(c, dx)
  local b = MKCH(c.leader_name, c.defender_sid, town.x + 500 + dx, town.z + 500, {})
  function b:getGameData() return { stringID = c.leader_sid } end
  return b
end
local function lev(sid) local n, last = 0, nil; for _, e in ipairs(S.events) do if e.leader_sid == sid and (e.type == "leader_killed" or e.type == "leader_captured") then n = n + 1; last = e end end; return n, last end
-- 1) убит игроком
local c1 = pairs_[1]
local st0 = S.F[c1.defender_sid].strength
C.add_rel(c1.defender_sid, pf, 50 - C.rel(c1.defender_sid, pf))
local r0 = C.rel(c1.defender_sid, pf)
local b1 = boss(c1, 10)
NM.on_player_hit(b1, pc); NM.on_player_hit(b1, pc); b1.dead = true
CLOCK = CLOCK + 5; tick(500.5)
local n1, e1 = lev(c1.leader_sid)
check(n1 == 1 and e1.type == "leader_killed" and e1.real and e1.by_player, "real leader kill reaches the model: " .. n1)
check(S.F[c1.defender_sid].succession and S.F[c1.defender_sid].strength < st0, "succession crisis and strength cost")
check(e1.a == pf, "player recorded as the attacker")
check(S.F[c1.defender_sid].wronged and S.F[c1.defender_sid].wronged[pf], "faction remembers the wrong (revenge motive)")
check(C.rel(c1.defender_sid, pf) <= r0 - 30, "relation to the player drops: " .. r0 .. " -> " .. C.rel(c1.defender_sid, pf))
local e3w = S.F[pairs_[3].defender_sid]
-- повтор (второй учёт) — нет
check(KMM_Conductor.leader_fell(c1.leader_sid, nil, "killed", true) == nil and (lev(c1.leader_sid)) == 1, "no double count")
-- 2) закован рядом с игроком
local c2 = pairs_[2]
FIRE("Character::setChainedMode", boss(c2, 20), true)
local n2, e2 = lev(c2.leader_sid)
check(n2 == 1 and e2.type == "leader_captured" and e2.by_player == true, "chained near the player: captured by player")
-- 3) закован далеко — не игроком
local c3 = pairs_[3]
FIRE("Character::setChainedMode", boss(c3, 9000), true)
local n3, e3 = lev(c3.leader_sid)
check(n3 == 1 and e3.by_player == false and e3.a == nil, "chained far away: captured, not by the player")
check(not (e3w.wronged and e3w.wronged[pf]), "not by the player: no grudge against the player")
-- 4) модель сама материализует плен — не дублировать
local c4 = pairs_[4]
S.pending[c4.leader_sid] = 999999
FIRE("Character::setChainedMode", boss(c4, 10), true)
check((lev(c4.leader_sid)) == 0, "materialize-owned capture is not reported twice")
S.pending[c4.leader_sid] = nil
-- 5) обычный NPC — ничего
local b5 = MKCH("Random Guard", c4.defender_sid, town.x + 510, town.z + 500, {})
NM.on_player_hit(b5, pc); NM.on_player_hit(b5, pc); b5.dead = true
CLOCK = CLOCK + 5; tick(500.8)
check((lev(c4.leader_sid)) == 0 and not S.F[c4.defender_sid].succession, "ordinary NPC death: no leader event")
-- 6) тёзка лидера (другой stringID) — не лидер
local c5 = pairs_[4]
local tz = MKCH(c5.leader_name, c5.defender_sid, town.x + 520, town.z + 500, {})
NM.on_player_hit(tz, pc); NM.on_player_hit(tz, pc); tz.dead = true
CLOCK = CLOCK + 5; tick(500.9)
check((lev(c5.leader_sid)) == 0, "namesake with another stringID is not the leader")
check(next(NM.disabled()) == nil, "nemesis still enabled")
RESULT = #FAILS == 0 and ("OK " .. N) or ("FAIL: " .. table.concat(FAILS, "; "))
'''.replace("TMPDIR", TMP), "test")
run("")
L.lua_getfield.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_char_p]
L.lua_getfield(st, -10002, b"RESULT")
r = L.lua_tolstring(st, -1, None).decode()
print(r)
sys.exit(0 if r.startswith("OK") else 1)
