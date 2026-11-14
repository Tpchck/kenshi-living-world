"""Offline test KMM_Nemesis shop_talk: окно торговли (ForgottenGUI::showTradeWindow) — торговец говорит о рынке города по KMM_Stock (осада, дефицит еды/металла/оружия, избыток) и price_mult_town; раз в день на торговца, молчит, когда всё обычно. Ниже — шапка из test_banter: свой из отряда игрока коротко отзывается о деле (соперник, должник, охотник, лидер), с паузой, только живой; память мира об игроке — избитый и оставленный жить/сбежавший становится соперником с прозвищем встречи, мститель за убитого, преследование по регионам, встреча с репликой и родной памятью ядра, повторная пощада, гибель. python -I -X utf8 build/KMM_Conductor/_dev/test_nemesis.py -> OK."""
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

C.cfg().params.nemesis.ambient = false; C.cfg().params.nemesis.greet = false
local S = C.state()
local tsid = "town_x"
local TOWNOBJ = { getGameData = function() return { stringID = tsid } end }
local INTOWN = true
local pc = MKCH("Beep", pf or "player", 0, 0, { player = true, platoon = "player_squad" })
PCS = { pc }; CHARS = { pc }
local other; for fid in pairs(S.F) do if fid ~= pf then other = fid; break end end
local tr = MKCH("Shopkeeper", other, 10, 10, {})
tr.said = {}; function tr:say(s) self.said[#self.said + 1] = s end
function tr:getCurrentTownLocation() return INTOWN and TOWNOBJ or nil end
local function hand(ch) return { getCharacter = function() return ch end } end
STK, LV = { siege = false }, { food = 1, metal = 1, weapons = 1 }
KMM_Stock = { stock = function(t) return STK end, level = function(t, c) return LV[c] end }
local PM = 1.0
local pm0 = C.price_mult_town; C.price_mult_town = function() return PM end
local function fire(dt) CLOCK = CLOCK + dt; FIRE("GameWorld::charsUpdate", {}) end
local DAY = 500
tick(DAY)
local function trade(newday) if newday then DAY = DAY + 1; tick(DAY) end; CLOCK = CLOCK + 50; FIRE("ForgottenGUI::showTradeWindow", {}, hand(pc), hand(tr), 0); fire(5) end
local function from(set) local l = tr.said[#tr.said]; for _, f in ipairs(set) do if l == f then return true end end return false end
local SH = NM._N.SHOP
trade(false)
check(#tr.said == 0, "normal market: trader silent")
STK.siege = true; trade(true)
check(#tr.said == 1 and from(SH.siege), "siege: siege prices line")
STK.siege = false; LV.food = 0.1; trade(false)
check(#tr.said == 1, "same day: once per trader")
trade(true)
check(#tr.said == 2 and from(SH.food), "food shortage: bread line: " .. tostring(tr.said[#tr.said]))
LV.food = 1; LV.metal = 0.05; trade(true)
check(#tr.said == 3 and from(SH.metal), "metal shortage")
LV.metal = 1; LV.weapons = 0.1; trade(true)
check(#tr.said == 4 and from(SH.weapons), "weapons shortage")
LV.weapons = 1; PM = 1.3; trade(true)
check(#tr.said == 5 and from(SH.dear), "dear prices line")
PM = 1.0; LV.food = 2; local n0 = #tr.said
for i = 1, 6 do trade(true) end
check(#tr.said > n0 and from(SH.glut), "glut: sometimes a full-shelves line")
LV.food = 0.1; INTOWN = false; local n1 = #tr.said; trade(true)
check(#tr.said == n1, "trader outside a town: silent")
INTOWN = true; local n2 = #tr.said
CLOCK = CLOCK + 50; FIRE("ForgottenGUI::showTradeWindow", {}, hand(pc), hand(pc), 0); fire(5)
check(#tr.said == n2, "player-player transfer: silent")
FIRE("ForgottenGUI::showTradeWindow", {}, { getCharacter = function() error("bad hand") end }, nil, 0)
check(not NM.hook_off().trade, "bad hand swallowed, hook alive")
C.price_mult_town = pm0
check(next(NM.disabled()) == nil, "nemesis still enabled")
RESULT = #FAILS == 0 and ("OK " .. N) or ("FAIL: " .. table.concat(FAILS, "; "))
'''.replace("TMPDIR", TMP), "test")
run("")
L.lua_getfield.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_char_p]
L.lua_getfield(st, -10002, b"RESULT")
r = L.lua_tolstring(st, -1, None).decode()
print(r)
sys.exit(0 if r.startswith("OK") else 1)
