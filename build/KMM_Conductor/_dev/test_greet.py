"""Offline test KMM_Nemesis greet: игрок вошёл в город — житель фракции-хозяина говорит по положению дел (прозвище, смена хозяина, беспорядки, убыль, отношение); раз в greet_cd_days на город, без говорящего — повтор. Ниже — шапка из test_banter: свой из отряда игрока коротко отзывается о деле (соперник, должник, охотник, лидер), с паузой, только живой; память мира об игроке — избитый и оставленный жить/сбежавший становится соперником с прозвищем встречи, мститель за убитого, преследование по регионам, встреча с репликой и родной памятью ядра, повторная пощада, гибель. python -I -X utf8 build/KMM_Conductor/_dev/test_nemesis.py -> OK."""
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
local rg, town
for nm, r in pairs(D.regions) do if #r.towns > 0 then rg, town = nm, r.towns[1]; break end end
local function mate(nm, opt)
  local c = MKCH(nm, pf or "player", town.x + 500, town.z + 500, opt or { player = true, platoon = "player_squad" })
  c.said = {}; function c:say(s) self.said[#self.said + 1] = s end
  return c
end

C.cfg().params.nemesis.ambient = false
local S = C.state()
local tsid, owner, I
for _, t in ipairs(C.towns()) do if t.owner and t.owner ~= pf and t.x then tsid, owner, I = t.sid, t.owner, t; break end end
check(tsid ~= nil, "a town with a non-player owner")
local other; for fid in pairs(S.F) do if fid ~= owner and fid ~= pf then other = fid; break end end
local TOWNOBJ = { getGameData = function() return { stringID = tsid } end }
local INTOWN = false
local pc = MKCH("Beep", pf or "player", I.x + 100, I.z + 100, { player = true, platoon = "player_squad" })
pc.said = {}; function pc:say(s) self.said[#self.said + 1] = s end
function pc:getCurrentTownLocation() return INTOWN and TOWNOBJ or nil end
PCS = { pc }; CHARS = { pc }
local function npc(nm, fid, dx)
  local c = MKCH(nm, fid, I.x + 100 + dx, I.z + 100, {})
  c.said = {}; function c:say(s) self.said[#self.said + 1] = s end
  return { ch = c, x = I.x + 100 + dx, z = I.z + 100, dead = false, town = true }
end
local guard, stranger = npc("Gate Guard", owner, 300), npc("Passer", other, 50)
local LIST = { guard, stranger }
KMM_Gov = { snapshot = function() return { list = LIST } end }
local REL, MOOD = 0, {}
local rel0, mood0 = C.rel, C.town_mood
C.rel = function(a, b) return REL end
C.town_mood = function(sid) local m = { owner = owner, unrest = 0, pop = 100, pop0 = 100 }; for k, v in pairs(MOOD) do m[k] = v end; return m end
local function fire(dt) CLOCK = CLOCK + dt; FIRE("GameWorld::charsUpdate", {}) end
local DAY = 500
local function visit()
  INTOWN = false; fire(5); DAY = DAY + 2; tick(DAY); INTOWN = true; fire(5); fire(30); fire(5); fire(5)
end
local function last() return guard.ch.said[#guard.ch.said] end
local function from(set, arg) local l = last(); for _, f in ipairs(set) do if l == (arg and string.format(f, arg) or f) then return true end end return false end
tick(DAY)
visit()
check(#guard.ch.said == 0 and #stranger.ch.said == 0, "neutral town, nothing new: silent")
REL = -30; visit()
check(#guard.ch.said == 1 and from(NM._N.GREET.cold) and #stranger.ch.said == 0, "cold relation: owner's resident (not the closer stranger) warns: " .. tostring(last()))
check(NM.greet_said(tsid) == true and NM.greet_said("other_town") == false, "greet_said: true for this visit (for KMM_Rumors)")
INTOWN = false; fire(5)
local s1, p1 = NM.greet_said(tsid)
check(s1 == false and p1 == false, "greet_said: visit over after leaving town")
INTOWN = true; fire(5)
local s2, p2 = NM.greet_said(tsid)
check(s2 == false and p2 == true, "greet_said: new visit, greet pending")
REL = 60; visit()
check(#guard.ch.said == 2 and from(NM._N.GREET.warm), "warm relation: welcome")
REL = 0; MOOD = { unrest = 0.8 }; visit()
check(#guard.ch.said == 3 and from(NM._N.GREET.unrest), "unrest: angry town line")
MOOD = { pop = 30 }; visit()
check(#guard.ch.said == 4 and from(NM._N.GREET.pop), "depopulated: empty houses line")
MOOD = {}
S.events[#S.events + 1] = { type = "town_captured", id = 990001, day = DAY + 1, town_sid = tsid, a = owner }
visit()
check(#guard.ch.said == 5 and from(NM._N.GREET.owner, C.name(owner)), "new owner (chronicle): flags line with owner name: " .. table.concat(guard.ch.said, " / "))
for i = #S.events, 1, -1 do if S.events[i].id == 990001 then table.remove(S.events, i) end end
NM._N.state(S).title = "the Butcher"; visit()
check(#guard.ch.said == 6 and from(NM._N.GREET.title, "the Butcher"), "title: town knows the player's name")
REL = -30; INTOWN = false; fire(5); INTOWN = true; fire(5); fire(30); fire(5)
check(#guard.ch.said == 6, "same day re-entry: cooldown")
REL = 0; NM._N.state(S).cnt = { spared = 4, freed = 3, healed = 1 }; visit()
check(#guard.ch.said == 7 and last():find("spared 4", 1, true) and last():find("chains of 3", 1, true) and last():find("The Butcher", 1, true),
      "legend: title and deeds told as a tale: " .. tostring(last()))
visit()
check(#guard.ch.said == 8 and from(NM._N.GREET.title, "the Butcher"), "legend once per town, then the plain title line")
NM._N.state(S).cnt = nil; REL = -30
NM._N.state(S).title = nil
LIST = {}; INTOWN = false; fire(5); DAY = DAY + 2; tick(DAY); INTOWN = true; fire(5); fire(30); fire(5)
check(#guard.ch.said == 8, "nobody near: no line yet")
LIST = { guard, stranger }; fire(25); fire(5)
check(#guard.ch.said == 9 and from(NM._N.GREET.cold), "speaker appears: retry says it")
local own = owner; owner = pf; visit(); owner = own
check(#guard.ch.said == 9, "player's own town: silent")
REL = 0
S.events[#S.events + 1] = { type = "leader_killed", id = 990002, day = DAY + 1, town_sid = tsid, leader_name = "Boss Kog" }
visit()
check(#guard.ch.said == 10 and from(NM._N.MOURN.leader_killed, "Boss Kog"), "mourning: fallen leader named first: " .. tostring(last()))
for i = #S.events, 1, -1 do if S.events[i].id == 990002 then table.remove(S.events, i) end end
C.rel, C.town_mood = rel0, mood0
check(NM.greet_off() ~= true, "greet enabled")
check(next(NM.disabled()) == nil, "nemesis still enabled")
RESULT = #FAILS == 0 and ("OK " .. N) or ("FAIL: " .. table.concat(FAILS, "; "))
'''.replace("TMPDIR", TMP), "test")
run("")
L.lua_getfield.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_char_p]
L.lua_getfield(st, -10002, b"RESULT")
r = L.lua_tolstring(st, -1, None).decode()
print(r)
sys.exit(0 if r.startswith("OK") else 1)
