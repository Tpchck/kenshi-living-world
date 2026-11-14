"""Offline test KMM_Nemesis traits: черта своего из имени (стабильно); на событие первым отзывается тот, чья черта о нём (deed-ключ debt_made_freed), без черты — общая реплика. Ниже — шапка из test_banter: свой из отряда игрока коротко отзывается о деле (соперник, должник, охотник, лидер), с паузой, только живой; память мира об игроке — избитый и оставленный жить/сбежавший становится соперником с прозвищем встречи, мститель за убитого, преследование по регионам, встреча с репликой и родной памятью ядра, повторная пощада, гибель. python -I -X utf8 build/KMM_Conductor/_dev/test_nemesis.py -> OK."""
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

local P_ = C.cfg().params.nemesis
P_.banter_p = 1; P_.trait_p = 1; P_.greet = false; P_.chronicle = false; P_.ambient = false
local NAMES = { "Beep", "Ruka", "Mol", "Tash", "Kira", "Oda", "Jun", "Vex", "Hobb", "Sela", "Garn", "Ilsa", "Brin", "Toma", "Rhee", "Dusk", "Pell", "Nim", "Yorr", "Cass" }
local by = {}
for _, nm in ipairs(NAMES) do local t = NM.trait_of(nm) or "none"; by[t] = by[t] or nm end
check(by.coward and by.freeborn and by.none, "name pool covers coward, freeborn and no-trait")
check(NM.trait_of(by.coward) == "coward" and NM.trait_of(by.coward) == NM.trait_of(by.coward), "trait stable for a name")
local function mk(nm) local c = mate(nm); return c end
local cw, fb, pl = mk(by.coward), mk(by.freeborn), mk(by.none)
PCS = { pl, cw, fb }; CHARS = { pl, cw, fb }
tick(500)
local function flush() for i = 1, 3 do CLOCK = CLOCK + 5; FIRE("GameWorld::charsUpdate", {}) end end
local function inset(l, set) for _, x in ipairs(set or {}) do if x == l then return true end end return false end
NM.banter("nemesis_hunter"); flush()
check(#cw.said == 1 and inset(cw.said[1], NM._N.TRAITS.coward.nemesis_hunter) and #pl.said + #fb.said == 0, "coward answers the hunter with his own line")
CLOCK = CLOCK + 300
NM.banter("debt_made", "freed"); flush()
check(#fb.said == 1 and inset(fb.said[1], NM._N.TRAITS.freeborn.debt_made_freed), "freeborn speaks on freeing (deed key)")
CLOCK = CLOCK + 300
local n0 = #pl.said + #cw.said + #fb.said
NM.banter("debt_made", "healed"); flush()
local all = {}; for _, c in ipairs({ pl, cw, fb }) do for _, l in ipairs(c.said) do all[#all + 1] = l end end
local chains = 0; for _, l in ipairs(all) do if inset(l, NM._N.TRAITS.freeborn.debt_made_freed) then chains = chains + 1 end end
check(#all == n0 + 1 and chains == 1, "healing: a line, but no chains line from freeborn")
PCS = { pl }; CHARS = { pl }
CLOCK = CLOCK + 300
NM.banter("nemesis_hunter"); flush()
check(#pl.said >= 1 and inset(pl.said[#pl.said], NM._N.BANTER.nemesis_hunter), "no trait in squad: generic banter line")
CLOCK = CLOCK + 300
local m0 = #pl.said
NM.banter("no_such_event"); flush()
check(#pl.said == m0, "unknown event: silent")
check(next(NM.disabled()) == nil, "nemesis still enabled")
RESULT = #FAILS == 0 and ("OK " .. N) or ("FAIL: " .. table.concat(FAILS, "; "))
'''.replace("TMPDIR", TMP), "test")
run("")
L.lua_getfield.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_char_p]
L.lua_getfield(st, -10002, b"RESULT")
r = L.lua_tolstring(st, -1, None).decode()
print(r)
sys.exit(0 if r.startswith("OK") else 1)
