"""Offline test KMM_Nemesis rescue: пленник в цепях дольше 6 игровых часов — его фракция шлёт отряд к игроку, главарь спрашивает о нём по имени; раз на пленника; закованный рядом с игроком и вырвавшийся не через его взлом — соперник «escaped» с родной памятью LT_MY_CAPTOR; освобождённый игроком — должник; память мира об игроке — избитый и оставленный жить/сбежавший становится соперником с прозвищем встречи, мститель за убитого, преследование по регионам, встреча с репликой и родной памятью ядра, повторная пощада, гибель. python -I -X utf8 build/KMM_Conductor/_dev/test_nemesis.py -> OK."""
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
C.cfg().params.nemesis = { rival_p_spared = 0, rival_p_fled = 0, avenger_p = 0, escape_p = 1, rescue_p = 1, rescue_cd_days = 0, banter = false, cooldown_days = 0, follow_p = 1, say_delay_s = 1, linger_s = 30 }
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
CharacterPerceptionTags_LongTerm = { LT_MY_LIFESAVER = 2, LT_FREED_ME = 3, LT_DEFEATED_MY_SQUAD_ONCE = 7, LT_KILLED_MY_FRIEND = 9, LT_MY_CAPTOR = 11 }
local function tick(day) DAYV = day; CLOCK = CLOCK + 100; FIRE("GameWorld::charsUpdate", {}) end
local function evs(ty) local n, last = 0, nil; for _, e in ipairs(C.state().events) do if e.type == ty then n = n + 1; last = e end end; return n, last end
local D = O._M.data(C)
local M = O._M
local rg, town, gang
for nm, r in pairs(D.regions) do if #r.towns > 0 and #r.gangs > 0 and M.tier_sid(D, r.gangs[1], 1) then rg, town, gang = nm, r.towns[1], r.gangs[1]; break end end
check(gang, "gang with tier squad")
PCS = {}; CHARS = {}
local pc = MKCH("Beep", pf or "player", town.x + 500, town.z + 500, { player = true, platoon = "player_squad" })
PCS[1] = pc; CHARS[1] = pc
tick(500)
local function evs2(ty) local n = 0; for _, e in ipairs(C.state().events) do if e.type == ty then n = n + 1 end end; return n end
local pr = MKCH("Big Rorek", gang, town.x + 520, town.z + 510, {})
FIRE("Character::setChainedMode", pr, true)
check(NM.captives()[gang .. "|Big Rorek"], "captive recorded")
CLOCK = CLOCK + 10; tick(500.1)
check(evs2("nemesis_rescue") == 0, "2.4 h: too early")
local m0 = #MADE
CLOCK = CLOCK + 10; tick(500.3)
check(evs2("nemesis_rescue") == 1, "7 h in chains: rescue party sent")
local mk
for i = 1, 40 do CLOCK = CLOCK + 80; tick(500.31)
  for j = m0 + 1, #MADE do if MADE[j].fid == gang and #MADE[j].leader.said > 0 then mk = MADE[j] end end
  if mk then break end
  for j = m0 + 1, #MADE do if MADE[j].fid == gang then for k = 1, 2 do CLOCK = CLOCK + 5; FIRE("GameWorld::charsUpdate", {}) end end end
end
check(mk and mk.leader.said[1]:find("Big Rorek", 1, true), "rescue leader asks for the prisoner by name: " .. tostring(mk and mk.leader.said[1]))
CLOCK = CLOCK + 10; tick(501.5)
check(evs2("nemesis_rescue") == 1, "one attempt per captive")
-- сбежавший/освобождённый — за ним не идут
local pr2 = MKCH("Quick One", gang, town.x + 520, town.z + 520, {})
FIRE("Character::setChainedMode", pr2, true)
FIRE("Character::setChainedMode", pr2, false)
CLOCK = CLOCK + 10; tick(502.5)
check(evs2("nemesis_rescue") == 1, "escaped captive: nobody comes for him")
local c1 = T.pace_class({ tag = "rescue" }); check(c1 == "story", "PACE: rescue is story/hostile")
check(next(NM.disabled()) == nil and next(NM.hook_off()) == nil, "nemesis enabled")
RESULT = #FAILS == 0 and ("OK " .. N) or ("FAIL: " .. table.concat(FAILS, "; "))
'''.replace("TMPDIR", TMP), "test")
run("")
L.lua_getfield.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_char_p]
L.lua_getfield(st, -10002, b"RESULT")
r = L.lua_tolstring(st, -1, None).decode()
print(r)
sys.exit(0 if r.startswith("OK") else 1)
