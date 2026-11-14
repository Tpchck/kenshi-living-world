"""Offline test KMM_Nemesis titles: мир зовёт игрока по делам (the Kind, the Liberator…), слух при смене, прозвище в текстах событий; вылеченный/освобождённый игроком становится должником — приходит на помощь в бою (имя, реплика, родная память LT_MY_LIFESAVER/LT_FREED_ME) или разносит добрую молву; память мира об игроке — избитый и оставленный жить/сбежавший становится соперником с прозвищем встречи, мститель за убитого, преследование по регионам, встреча с репликой и родной памятью ядра, повторная пощада, гибель. python -I -X utf8 build/KMM_Conductor/_dev/test_nemesis.py -> OK."""
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
C.cfg().params.nemesis = { rival_p_spared = 0, rival_p_fled = 0, avenger_p = 0, cooldown_days = 0, follow_p = 1, say_delay_s = 1, linger_s = 30 }
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
CharacterPerceptionTags_LongTerm = { LT_MY_LIFESAVER = 2, LT_FREED_ME = 3, LT_DEFEATED_MY_SQUAD_ONCE = 7, LT_KILLED_MY_FRIEND = 9 }
local function tick(day) DAYV = day; CLOCK = CLOCK + 100; FIRE("GameWorld::charsUpdate", {}) end
local function evs(ty) local n, last = 0, nil; for _, e in ipairs(C.state().events) do if e.type == ty then n = n + 1; last = e end end; return n, last end
local D = O._M.data(C)
local S = C.state()
local rg, town
for nm, r in pairs(D.regions) do if #r.towns > 0 then rg, town = nm, r.towns[1]; break end end
local dfid; for fid in pairs(S.F) do if fid ~= pf then dfid = fid; break end end
C.cfg().params.nemesis.max_debts = 50; C.cfg().params.nemesis.banter = false
PCS = {}; CHARS = {}
local pc = MKCH("Beep", pf or "player", town.x + 500, town.z + 500, { player = true, platoon = "player_squad" })
PCS[1] = pc; CHARS[1] = pc
tick(500)
local function evs2(ty) local n, last = 0, nil; for _, e in ipairs(S.events) do if e.type == ty then n = n + 1; last = e end end; return n, last end
local function heal(nm) local w = MKCH(nm, dfid, town.x + 600, town.z + 600, {}); for i = 1, 5 do FIRE("CharStats::xpFirstAid", { me = pc }, w, 5) end end
local function free(nm) local w = MKCH(nm, dfid, town.x + 600, town.z + 600, {}); CLOCK = CLOCK + 1; FIRE("CharStats::xpLockpicking", { me = pc }, 10, true); FIRE("Character::setChainedMode", w, false) end
heal("Anna Kor"); heal("Bel Mar")
check(NM.player_title() == nil and (evs2("nemesis_title")) == 0, "two good deeds: no title yet")
heal("Cyra Lun")
local nt, et = evs2("nemesis_title")
check(NM.player_title() == "the Kind" and nt == 1 and et.text:find("the Kind", 1, true), "three healed: the Kind: " .. tostring(NM.player_title()))
heal("Dov Ash")
local _, ed = evs2("debt_made")
check(ed.text:find("they call the Kind", 1, true), "title used in event text: " .. ed.text)
local AS; for fid in pairs(S.F) do if C.name(fid) == "Anti-Slavers" then AS = fid end end
if AS then C.add_rel(AS, pf, 20 - C.rel(AS, pf)) end
local as0 = AS and C.rel(AS, pf)
for i = 1, 5 do free("Freed " .. i) end
check(not AS or C.rel(AS, pf) == as0 + 15, "Liberator: Anti-Slavers warm to the player: " .. tostring(as0) .. " -> " .. tostring(AS and C.rel(AS, pf)))
local nt2, et2 = evs2("nemesis_title")
check(NM.player_title() == "the Liberator" and nt2 == 2 and et2.text:find("used to call", 1, true), "more freed than healed: the Liberator: " .. tostring(et2 and et2.text))
check((NM.counts().healed or 0) == 4 and (NM.counts().freed or 0) == 5, "counters")
C.cfg().params.nemesis.titles = false
check(NM.player_title() == nil, "titles = false: none")
check(next(NM.disabled()) == nil, "nemesis enabled")
RESULT = #FAILS == 0 and ("OK " .. N) or ("FAIL: " .. table.concat(FAILS, "; "))
'''.replace("TMPDIR", TMP), "test")
run("")
L.lua_getfield.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_char_p]
L.lua_getfield(st, -10002, b"RESULT")
r = L.lua_tolstring(st, -1, None).decode()
print(r)
sys.exit(0 if r.startswith("OK") else 1)
