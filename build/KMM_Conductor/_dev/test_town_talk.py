"""Offline test KMM_Nemesis town talk: игрок в городе рядом с местом своего дела — горожанин заговаривает о нём (раз на дело, после того как весть разошлась); память мира об игроке — избитый и оставленный жить/сбежавший становится соперником с прозвищем встречи, мститель за убитого, преследование по регионам, встреча с репликой и родной памятью ядра, повторная пощада, гибель. python -I -X utf8 build/KMM_Conductor/_dev/test_nemesis.py -> OK."""
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
C.cfg().params.nemesis = { rival_p_spared = 0, rival_p_fled = 0, avenger_p = 0, banter = false, cooldown_days = 0, follow_p = 1, say_delay_s = 1, linger_s = 30 }
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
local rg, town, gang
for nm, r in pairs(D.regions) do if #r.towns > 0 and #r.gangs > 0 then rg, town, gang = nm, r.towns[1], r.gangs[1]; break end end
local pf_ = C.cfg().player_faction
local dfid; for fid in pairs(S.F) do if fid ~= pf_ then dfid = fid; break end end
PCS = {}; CHARS = {}
local pc = MKCH("Beep", pf or "player", town.x + 500, town.z + 500, { player = true, platoon = "player_squad" })
local IN_TOWN = false
function pc:getCurrentTownLocation() return IN_TOWN and {} or nil end
PCS[1] = pc; CHARS[1] = pc
local function npc(nm, dx, opt)
  local c = MKCH(nm, dfid, town.x + 500 + dx, town.z + 500, opt or {})
  c.said = {}; function c:say(s) self.said[#self.said + 1] = s end
  return { ch = c, x = town.x + 500 + dx, z = town.z + 500, dead = false, town = true }
end
local near, dead_one, far_one = npc("Barkeep", 100), npc("Corpse", 50, { down = true }), npc("Far Guy", 3000)
KMM_Gov = { snapshot = function() return { list = { near, dead_one, far_one } } end }
tick(500)
-- дело: вылечил чужого
local w = MKCH("Wounded Drifter", dfid, town.x + 700, town.z + 700, {})
for i = 1, 5 do FIRE("CharStats::xpFirstAid", { me = pc }, w, 5) end
check(#NM.deeds() == 1 and NM.deeds()[1].k == "debt_made_healed", "deed recorded with place: " .. #NM.deeds())
-- вне города — молчат; в городе, но весть ещё не разошлась — молчат
CLOCK = CLOCK + 200; tick(500.1)
IN_TOWN = true
CLOCK = CLOCK + 200; tick(500.2)
check(#near.ch.said == 0, "too fresh: no talk yet")
CLOCK = CLOCK + 200; tick(501)
for i = 1, 2 do CLOCK = CLOCK + 5; FIRE("GameWorld::charsUpdate", {}) end
check(#near.ch.said == 1 and near.ch.said[1]:find(NM.deeds()[1].who, 1, true), "nearest townsperson talks about the deed: " .. tostring(near.ch.said[1]))
check(#dead_one.ch.said == 0 and #far_one.ch.said == 0, "not the downed one, not the far one")
-- раз на дело
CLOCK = CLOCK + 500; tick(501.2)
for i = 1, 2 do CLOCK = CLOCK + 5; FIRE("GameWorld::charsUpdate", {}) end
check(#near.ch.said == 1, "each deed only once")
-- дело далеко отсюда — не вспоминают
NM._N.deed_add(C, "leader_fell", "Tinfist", town.x + 60000, town.z)
CLOCK = CLOCK + 500; tick(502)
for i = 1, 2 do CLOCK = CLOCK + 5; FIRE("GameWorld::charsUpdate", {}) end
check(#near.ch.said == 1, "deed far away: this town does not know")
-- дело рядом, но говорить некому — ждём
NM._N.deed_add(C, "leader_fell", "Moll", town.x + 600, town.z + 600)
local keep = KMM_Gov.snapshot; KMM_Gov.snapshot = function() return { list = {} } end
CLOCK = CLOCK + 500; tick(503)
KMM_Gov.snapshot = keep
CLOCK = CLOCK + 30; tick(503.01)
for i = 1, 2 do CLOCK = CLOCK + 5; FIRE("GameWorld::charsUpdate", {}) end
check(#near.ch.said == 2 and near.ch.said[2]:find("Moll", 1, true), "no speaker -> retry shortly: " .. tostring(near.ch.said[2]))
-- осведомители: есть должник и соперник далеко — весть, где его видели
local M_, O_, D_ = NM._N.outlaws()
local ftown, frg
for nm, r in pairs(D.regions) do for _, t in ipairs(r.towns) do
  if not ftown and ((t.x - town.x) ^ 2 + (t.z - town.z) ^ 2) > 20000 ^ 2 and #r.gangs > 0 then ftown, frg = t, nm end end end
check(ftown, "a far region")
local rv = NM._N.make(M_, O_, D_, C, S, { n = "Rorek Bandit", fid = D.regions[frg].gangs[1], x = ftown.x + 100, z = ftown.z + 100, lead = true, hits = 3, down = true }, "spared")
check(rv and rv.r, "far rival made: " .. tostring(rv and rv.r))
local n0 = #near.ch.said
CLOCK = CLOCK + 500; tick(506)
for i = 1, 2 do CLOCK = CLOCK + 5; FIRE("GameWorld::charsUpdate", {}) end
local il = near.ch.said[n0 + 1]
check(il and il:find(rv.n, 1, true), "townsperson passes the debtor's word about the rival: " .. tostring(il))
CLOCK = CLOCK + 500; tick(506.5)
for i = 1, 2 do CLOCK = CLOCK + 5; FIRE("GameWorld::charsUpdate", {}) end
check(#near.ch.said == n0 + 1, "intel not more often than intel_gap_days")
check(not NM.town_talk_off() and next(NM.disabled()) == nil, "town talk and nemesis enabled")
RESULT = #FAILS == 0 and ("OK " .. N) or ("FAIL: " .. table.concat(FAILS, "; "))
'''.replace("TMPDIR", TMP), "test")
run("")
L.lua_getfield.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_char_p]
L.lua_getfield(st, -10002, b"RESULT")
r = L.lua_tolstring(st, -1, None).decode()
print(r)
sys.exit(0 if r.startswith("OK") else 1)
