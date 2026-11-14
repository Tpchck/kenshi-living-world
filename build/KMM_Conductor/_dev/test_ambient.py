"""Offline test KMM_Nemesis ambient: отряд игрока говорит о месте недавнего боя (хроника дирижёра), о голоде (MedicalSystem.hunger), о пустых прилавках и осаде (KMM_Stock); раз на событие/день/город, пауза amb_gap_s, после banter тише. Ниже — шапка из test_banter: свой из отряда игрока коротко отзывается о деле (соперник, должник, охотник, лидер), с паузой, только живой; память мира об игроке — избитый и оставленный жить/сбежавший становится соперником с прозвищем встречи, мститель за убитого, преследование по регионам, встреча с репликой и родной памятью ядра, повторная пощада, гибель. python -I -X utf8 build/KMM_Conductor/_dev/test_nemesis.py -> OK."""
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
C.cfg().params.nemesis = { night = false, rival_p_spared = 1, rival_p_fled = 0, avenger_p = 1, cooldown_days = 0, follow_p = 1, say_delay_s = 1, linger_s = 30 }
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

local TI = C.cfg().town_info or {}
local tsid, I
for k, v in pairs(TI) do if v.x and v.name then tsid, I = k, v; break end end
check(tsid ~= nil, "town_info has a town with coords")
local TOWNOBJ = { getGameData = function() return { stringID = tsid } end }
local INTOWN = false
local function mate(nm)
  local c = MKCH(nm, pf or "player", I.x + 300, I.z + 300, { player = true, platoon = "player_squad" })
  c.said = {}; function c:say(s) self.said[#self.said + 1] = s; ORDER[#ORDER + 1] = s end
  c.medical.hunger = 250
  function c:getMedical() return self.medical end
  function c:getCurrentTownLocation() return INTOWN and TOWNOBJ or nil end
  return c
end
ORDER = {}
local a, b = mate("Beep"), mate("Ruka")
PCS = { a, b }; CHARS = { a, b }
STK, LV = {}, {}
KMM_Stock = { stock = function(t) return STK[t] end, level = function(t, c) return LV[t] end }
local function lines() return ORDER end
local function step() CLOCK = CLOCK + 700; FIRE("GameWorld::charsUpdate", {}); CLOCK = CLOCK + 5; FIRE("GameWorld::charsUpdate", {}) end
local function has(sub) for _, s in ipairs(lines()) do if s:find(sub, 1, true) then return true end end return false end
tick(500)
step()
check(#lines() == 0, "nothing to say: silent")
local S = C.state()
for i = #S.events, 1, -1 do if NM._N.AMB_EV[S.events[i].type] then table.remove(S.events, i) end end; 
S.events[#S.events + 1] = { type = "raid", id = 900001, day = 495, town_sid = tsid, town_name = I.name }
step()
check(#lines() == 0, "old battle (5 days ago): silent")
S.events[#S.events + 1] = { type = "raid", id = 900002, day = 499.5, town_sid = tsid, town_name = I.name }
step()
check(#lines() == 1 and has(I.name), "recent battle nearby: one line with town name: " .. tostring(lines()[1]))
step()
check(#lines() == 1, "same battle: said once")
S.events[#S.events + 1] = { type = "town_craft", id = 900003, day = 500, town_sid = tsid, town_name = I.name }
step()
check(#lines() == 1, "non-battle event: silent")
a.medical.hunger = 40; b.medical.hunger = 60
step()
local n = #lines(); local okh = false
for _, l in ipairs(NM._N.AMB.hungry) do if lines()[n] == l then okh = true end end
check(n == 2 and okh, "squad hungry: hunger line")
step()
check(#lines() == 2, "hungry: once per game day")
a.medical.hunger = 250; b.medical.hunger = 250
for i = #S.events, 1, -1 do if NM._N.AMB_EV[S.events[i].type] then table.remove(S.events, i) end end; INTOWN = true; STK[tsid] = { siege = true }; LV[tsid] = 0.9
step()
local okS = false; for _, l in ipairs(NM._N.AMB.siege) do if lines()[#lines()] == string.format(l, I.name) then okS = true end end
check(#lines() == 3 and okS, "town under siege: siege line: " .. tostring(lines()[#lines()]))
step()
check(#lines() == 3, "town line: once per 3 days")
STK[tsid] = { siege = false }; LV[tsid] = 0.05; tick(504); for i = #S.events, 1, -1 do if NM._N.AMB_EV[S.events[i].type] then table.remove(S.events, i) end end
step()
local okE = false; for _, l in ipairs(NM._N.AMB.empty) do if lines()[#lines()] == string.format(l, I.name) then okE = true end end
check(#lines() == 4 and okE, "empty food stalls: empty line: " .. #lines() .. " " .. tostring(lines()[#lines()]))
tick(508); NM.banter("debt_repaid"); C.cfg().params.nemesis.banter_p = 1
S.events[#S.events + 1] = { type = "revolt", id = 900004, day = 508, town_sid = tsid, town_name = I.name }
C.cfg().params.nemesis.ambient = false
step()
local n0 = #lines()
step()
check(#lines() == n0, "ambient = false: off")
C.cfg().params.nemesis.ambient = true
for i = #S.events, 1, -1 do if NM._N.AMB_EV[S.events[i].type] or S.events[i].type == "caravan_lost" then table.remove(S.events, i) end end
KMM_Stock = nil; INTOWN = false
S.events[#S.events + 1] = { type = "caravan_lost", id = 900010, day = 508, by = "player", x = I.x + 200, z = I.z + 200, attacker = "Traders Guild" }
step()
check(not has("Traders Guild"), "caravan killed by the player: no wreck line")
S.events[#S.events + 1] = { type = "caravan_lost", id = 900011, day = 508, by = "other", x = I.x + 200, z = I.z + 200, attacker = "Traders Guild" }
step()
check(has("Traders Guild"), "caravan wreck nearby (killed by others): squad names the colours")
local nw = #lines(); step()
check(#lines() == nw, "wreck: once per event")
C.cfg().params.nemesis.night = true; INTOWN = false
for i = #S.events, 1, -1 do table.remove(S.events, i) end
local nn0 = #lines()
DAYV = 520 + 12 / 24; step()
check(#lines() == nn0, "noon on the road: no night line")
DAYV = 520 + 23 / 24; step()
local okN = false; for _, l in ipairs(NM._N.AMB.night) do if lines()[#lines()] == l then okN = true end end
check(#lines() == nn0 + 1 and okN, "night on the road: one night line")
DAYV = 521 + 2 / 24; step()
check(#lines() == nn0 + 1, "same night after midnight: no repeat")
DAYV = 521 + 23 / 24; INTOWN = true; step()
check(#lines() == nn0 + 1, "night inside a town: silent")
INTOWN = false; step()
check(#lines() == nn0 + 2, "next night on the road: new line")
C.cfg().params.nemesis.night = false
KMM_Stock = { stock = function() error("boom") end, level = function() error("boom") end }
step()
check(NM.ambient_off() ~= true, "Stock errors swallowed, ambient alive")
check(next(NM.disabled()) == nil, "nemesis still enabled")
check(NM.ambient_off() ~= true, "ambient enabled")
RESULT = #FAILS == 0 and ("OK " .. N) or ("FAIL: " .. table.concat(FAILS, "; "))
'''.replace("TMPDIR", TMP), "test")
run("")
L.lua_getfield.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_char_p]
L.lua_getfield(st, -10002, b"RESULT")
r = L.lua_tolstring(st, -1, None).decode()
print(r)
sys.exit(0 if r.startswith("OK") else 1)
