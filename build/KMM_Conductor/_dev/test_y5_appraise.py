"""Offline test Y5: KMM_Nemesis — соперник при встрече оценивает ВИДИМУЮ силу отряда игрока (StateBroadcastData.apparentStrength тех,
кого главарь видит и кто на ногах; Blackboard.moraleIsBroken) против своей (actualStrength x размер отряда): слабый -> нападает,
сильный -> уходит (пакет roam S3 + ванильная реплика EV_GIVE_UP_CHASE + событие), середина -> угроза и пересмотр; раненые/спрятанные/
сломленный дух меняют исход; не прочиталось или не подошёл -> фолбэк (пакет не трогаем); ушедший постоянный соперник снова на следе.
M6: повторный отход того же соперника в окне appr_withdraw_days - без нового события; KMM_Nemesis.withdrew_recent для Outlaws.
M7: оценка выключилась - соперник с пакетом «бродить» сразу получает охоту; регрупп идёт и при выключенной оценке.
python -I -X utf8 build/KMM_Conductor/_dev/test_y5_appraise.py -> OK."""
import ctypes, re, sys, tempfile

DLL = r"C:\Program Files (x86)\Steam\steamapps\workshop\content\233860\3817000612\lua51.dll"
B = r"C:\KenshiModMap\build\KMM_Conductor\scripts\init"
TMP = tempfile.mkdtemp(prefix="kmm_y5_").replace("\\", "/")
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
run("math.randomseed(20261115)", "seed")
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
local pf = C.cfg().player_faction or "player"
C.cfg().params.outlaws = { watch_s = 1e9, sdir = "TMPDIR/", native_bounty = false }
C.cfg().params.nemesis = { say_delay_s = 1, ambient = false, banter = false }
local NM, NN = KMM_Nemesis, KMM_Nemesis._N
local LOG = {}
local log0 = NN.log
NN.log = function(m) LOG[#LOG + 1] = tostring(m); log0(m) end
local function logged(s) for _, l in ipairs(LOG) do if l:find(s, 1, true) then return true end end return false end
local function clear() LOG = {}; NN.said = {} end
local S = C.state()
local cfg = NN.cfg()
local OM = KMM_Outlaws._M
local roam_sid, hunt_sid = OM.cfg().pkg_roam, OM.cfg().pkg_hunt
-- главарь соперника
local PKG = {}
local RB = { moraleIsBroken = false }
function RB:replaceAIPackage(gd) PKG[#PKG + 1] = gd.stringID end
local LX, LZ = 0, 0
local lead = { dead = false, down = false, act = 10, size = 3 }
function lead:getName() return "Kadan Sandscar" end
function lead:getPosition() return { x = LX, y = 0, z = LZ } end
function lead:isDead() return self.dead end
function lead:isDown() return self.down end
function lead:getBlackboard() return RB end
function lead:getStateBroadcast() return { actualStrength = self.act, apparentStrength = 4 } end
local AP = {}; function AP:getSquadSize() return lead.size end
function lead:getPlatoon() return AP end
local SENS = {}; function SENS:canISeeThisGuy(pc) return not pc.hidden end
function lead:getSensoryData() return SENS end
-- отряд игрока: n персонажей с видимой силой a
local PB = { moraleIsBroken = false }
local function squad(n, a)
  PCS = {}
  for i = 1, n do
    local c = MKCH("pc" .. i, pf, 300 + i * 10, 0, { player = true, platoon = "player_squad" })
    c.app, c.isdown = a, false
    function c:isDown() return self.isdown end
    function c:getStateBroadcast() if self.badsb then error("no broadcast") end; return { apparentStrength = self.app, actualStrength = self.app } end
    function c:getBlackboard() return PB end
    PCS[i] = c
  end
  CHARS = PCS
  return PCS
end
local nexti = 900
local function rival()
  nexti = nexti + 1
  return { i = nexti, n = "Kadan Sandscar", st = "a", g = "bandits", t = 1, b = 1000, pg = { deed = "spared", place = "Squin", met = 1, day = 0 } }
end
-- живой набор движка: has по указателю (ContainersReference); на обход pairs не влияет
LEAD_LIVE, HAS_OK = true, true
local gw0 = getGameWorld
getGameWorld = function()
  local w = gw0()
  local base = w.getCharacterUpdateList
  w.getCharacterUpdateList = function(self)
    local set = base(self)
    if HAS_OK then setmetatable(set, { __index = { has = function(_, c) if c == lead then return LEAD_LIVE end; return rawget(set, c) == true end } }) end
    return set
  end
  return w
end
local function meet(o) PKG = {}; clear(); NN.on_spawn(o, lead); NN.said = {}; return NN.appr["o" .. o.i] end
local function step() NN.appraise_step(C, S) end
local function said_ev(ev) for _, s in ipairs(NN.said) do if s.ev == ev then return s end end end

-- (0) on_spawn ставит оценку в очередь
squad(1, 10)
local o = rival()
local e = meet(o)
check(e and e.leader == lead and e.o == o, "on_spawn queues an appraisal for the rival")

-- (1) одиночка: 10 против 10x3 -> нападает, пакет не трогаем, без лишней реплики
step()
check(NN.appr["o" .. o.i] == nil and logged("appraise: app=10.0 own=30.0 (x3) ratio=0.33") and logged("-> attack"), "lone player provokes an attack")
check(#PKG == 0 and #NN.said == 0, "attack on first look: assault package kept, no extra line")

-- (2) сильный отряд: 5x12=60 против 30 -> уходит: пакет roam, ванильная реплика отказа, событие, метка на сегодня
squad(5, 12); o = rival(); meet(o)
local ne = #S.events
step()
local wev; for i = ne + 1, #S.events do if S.events[i].type == "nemesis_withdrew" then wev = S.events[i] end end
check(logged("ratio=2.00") and logged("-> withdraw") and PKG[1] == roam_sid, "strong squad: rival withdraws with the roam package")
check(said_ev("EV_GIVE_UP_CHASE") and wev and o.pg.wd_day ~= nil and o.pg.wd == 1, "withdraw: vanilla give-up line, chronicle event, wd_day")

-- (3) тот же отряд, но трое лежат и один спрятан -> видна одна шпага -> нападает
squad(5, 12); PCS[1].isdown, PCS[2].isdown, PCS[3].isdown = true, true, true; PCS[4].hidden = true
o = rival(); meet(o); step()
check(logged("app=12.0") and logged("hidden=1 down=3") and logged("-> attack") and #PKG == 0, "wounded and hidden members do not count: attack")

-- (4) середина: 3x12=36/30=1.2 -> угроза (roam + своя строка), через appr_parley_s двое легли -> штурм (hunt + EV_LAUNCH_ATTACK)
squad(3, 12); o = rival(); e = meet(o); step()
check(e.phase == "parley" and PKG[1] == roam_sid and NN.said[1] and NN.said[1].ev == nil and logged("-> parley"), "middle: parley with roam package and threat line")
NN.said = {}; LOG = {}
step()
check(#PKG == 1 and NN.appr["o" .. o.i] ~= nil, "parley waits appr_parley_s before re-appraising")
PCS[1].isdown, PCS[2].isdown = true, true
CLOCK = CLOCK + cfg.appr_parley_s + 1
step()
check(logged("after parley") and logged("-> attack") and PKG[2] == hunt_sid and said_ev("EV_LAUNCH_ATTACK") and NN.appr["o" .. o.i] == nil,
      "squad weakened during parley: assault package back and attack shout")

-- (5) сломленный дух игрока: та же середина, но moraleIsBroken -> нападает сразу, с криком
squad(3, 12); PB.moraleIsBroken = true; o = rival(); meet(o); step()
check(logged("broken=true") and logged("ratio=0.60") and logged("-> attack") and said_ev("EV_LAUNCH_ATTACK") and #PKG == 0, "broken morale halves visible strength: attack")
PB.moraleIsBroken = false

-- (6) дух банды сломлен -> уходит, даже когда игрок слаб
squad(1, 5); RB.moraleIsBroken = true; o = rival(); meet(o); step()
check(logged("rbroken=true") and logged("-> withdraw") and PKG[1] == roam_sid, "rival's own broken morale: withdraw")
RB.moraleIsBroken = false

-- (7) фолбэк: apparentStrength не читается -> пакет не трогаем
squad(2, 10); PCS[1].badsb, PCS[2].badsb = true, true; o = rival(); meet(o); step()
check(logged("appraise: fallback") and logged("apparentStrength unreadable") and #PKG == 0 and NN.appr["o" .. o.i] == nil, "unreadable strength: fallback, no package change")
-- не подошёл за appr_max_s
squad(2, 10); LX = 50000; o = rival(); meet(o); step()
check(NN.appr["o" .. o.i] ~= nil and #PKG == 0, "far away: still waiting")
CLOCK = CLOCK + cfg.appr_max_s + 1; step()
check(logged("never came close") and NN.appr["o" .. o.i] == nil and #PKG == 0, "timeout: fallback as before")
LX = 0
-- угроза, потом главарь не читается -> охота как раньше
squad(3, 12); o = rival(); e = meet(o); step()
local gp = lead.getPosition; lead.getPosition = function() error("gone") end
CLOCK = CLOCK + cfg.appr_parley_s + 1; step()
lead.getPosition = gp
check(logged("fallback Kadan Sandscar after parley") and PKG[#PKG] == hunt_sid, "parley then unreadable: assault package restored")
-- главарь лёг -> запись снимается
squad(3, 12); o = rival(); meet(o); lead.down = true; step(); lead.down = false
check(NN.appr["o" .. o.i] == nil and logged("dropped (leader down or dead)"), "leader down: appraisal dropped")
-- угроза, потом отряд выгружен (указатель не в живом наборе): не трогаем, метка регруппа
squad(3, 12); o = rival(); e = meet(o); step()
LEAD_LIVE = false; local nd0 = lead.isDown; lead.isDown = function() error("dangling pointer touched") end
CLOCK = CLOCK + cfg.appr_parley_s + 1; step()
lead.isDown = nd0; LEAD_LIVE = true
check(NN.appr["o" .. o.i] == nil and logged("dropped (leader unloaded)") and o.pg.wd_day ~= nil, "unloaded leader: not touched, regroup mark set")

-- (8) регрупп: постоянный соперник ушёл wd_day, через appr_regroup_days снова пакет охоты через доску платуна
local PB2 = { }; local PK2 = {}
function PB2:replaceAIPackage(gd) PK2[#PK2 + 1] = gd.stringID end
local PLT = {}; function PLT:getBlackboard() return PB2 end
local fp0 = OM.find_pl; OM.find_pl = function(x) return PLT, true end
local O = OM.O(S)
local ro = rival(); ro.pk = "key1"; ro.pg.wd_day = 10
O.L["o" .. ro.i] = ro
LOG = {}
NN.regroup_day(OM, O, 11)
check(#PK2 == 0 and ro.pg.wd_day == 10, "regroup waits appr_regroup_days")
NN.regroup_day(OM, O, 10 + cfg.appr_regroup_days)
check(PK2[1] == hunt_sid and ro.pg.wd_day == nil and logged("appraise: regroup"), "regroup: hunt package on the persistent squad")
local rt = rival(); rt.pg.wd_day = 1; O.L["o" .. rt.i] = rt
NN.regroup_day(OM, O, 30)
check(rt.pg.wd_day == nil and #PK2 == 1, "temporary rival: mark cleared, no package call")
OM.find_pl = fp0
O.L["o" .. ro.i], O.L["o" .. rt.i] = nil, nil

-- (9) другой сейв: очередь сбрасывается
squad(1, 10); o = rival(); meet(o)
NN.appr_S = {}
step()
check(next(NN.appr) == nil, "world change clears queued appraisals")

-- (9b) нет has у набора -> оценка выключается без касания указателя, поведение как раньше
squad(1, 10); o = rival(); meet(o); HAS_OK = false; PKG = {}
step()
check(NN.appr_off == true and logged("no liveness check") and #PKG == 0, "no set:has: appraise off, behaviour as before")
HAS_OK = true; NN.appr_off = nil; NN.regroup_now = nil
-- (9c) M6: тот же соперник отходит второй раз (новый спавн) - одно событие на отход, withdrew_recent
squad(5, 12); o = rival(); O.L["o" .. o.i] = o; meet(o); step()
local function nwd() local k = 0; for _, ev in ipairs(S.events) do if ev.type == "nemesis_withdrew" then k = k + 1 end end; return k end
local w1 = nwd()
check(o.pg.wd == 1 and o.pg.wdd ~= nil, "first withdraw counted")
meet(o); step()
check(o.pg.wd == 1 and nwd() == w1 and logged("withdraw repeat of") and said_ev("EV_GIVE_UP_CHASE"), "repeat withdraw: line kept, no new event/count")
check(NM.withdrew_recent(o) == true and NM.withdrew_recent(o.i) == true and NM.withdrew_recent("o" .. o.i) == true, "withdrew_recent by record, i, key")
check(NM.withdrew_recent(rival()) == false and NM.withdrew_recent("nobody") == false, "no withdraw -> false")
o.pg.wdd = o.pg.wdd - cfg.appr_withdraw_days - 1
check(NM.withdrew_recent(o) == false, "old withdraw -> false")
meet(o); step()
check(o.pg.wd == 2 and nwd() == w1 + 1, "after the window: a new withdraw is a new event")
O.L["o" .. o.i] = nil
-- (9d) M7: угроза (пакет «бродить») у постоянного соперника, потом оценка выключилась -> охота сразу, без ожидания дней
local PB3, PK3 = {}, {}
function PB3:replaceAIPackage(gd) PK3[#PK3 + 1] = gd.stringID end
local PLT3 = {}; function PLT3:getBlackboard() return PB3 end
local fp1 = OM.find_pl; OM.find_pl = function(x) return PLT3, true end
squad(3, 12); local po = rival(); po.pk = "keyP"; O.L["o" .. po.i] = po; e = meet(po); step()
check(e.phase == "parley" and e.roam and PKG[#PKG] == roam_sid, "persistent rival on roam after parley")
NN.appr_stop(C, "appraise disabled until restart: test")
check(NN.appr_off == true and NN.regroup_now == true and po.pg.wd_day ~= nil, "stop: regroup mark set for roam rival")
NN.regroup_now = nil; NN.regroup_safe(OM, O, math.floor(NN.day(C)))
check(PK3[1] == hunt_sid and po.pg.wd_day == nil, "appraise off: hunt package restored immediately")
-- регрупп и при appraise=false (в т.ч. после перезапуска: метка в сейве)
NN.appr_off = nil; po.pg.wd_day = NN.day(C); C.cfg().params.nemesis.appraise = false
NN.regroup_safe(OM, O, math.floor(NN.day(C)))
check(PK3[2] == hunt_sid and po.pg.wd_day == nil, "appraise=false: regroup still returns the hunt")
C.cfg().params.nemesis.appraise = nil
-- ошибка регруппа выключает только его
local rd = NN.regroup_day; NN.regroup_day = function() error("rg") end
NN.regroup_safe(OM, O, 1); NN.regroup_day = rd
check(NN.regroup_off == true and logged("regroup disabled until restart") and not NN.appr_off, "regroup error disables only regroup")
NN.regroup_off = nil
OM.find_pl = fp1; O.L["o" .. po.i] = nil
-- (10) ошибка в оценке выключает только её
squad(1, 10); o = rival(); meet(o)
local ar = NN.appr_read; NN.appr_read = function() error("x") end
NM._tick()
NN.appr_read = ar
check(NM.appraise_off() == true and logged("appraise disabled until restart") and next(NM.disabled()) == nil, "appraise error disables only appraise")
local AN = NM.appraisals()
check((AN.attack or 0) >= 4 and (AN.withdraw or 0) >= 2 and (AN.fallback or 0) >= 3, "counters exported")
-- выключено в конфиге -> on_spawn не ставит
C.cfg().params.nemesis.appraise = false; NN.appr = {}
NN.on_spawn(rival(), lead)
check(next(NN.appr) == nil, "appraise=false: nothing queued (behaviour as before)")
RESULT = #FAILS == 0 and ("OK " .. N) or ("FAIL: " .. table.concat(FAILS, "; "))
'''.replace("TMPDIR", TMP), "test")
L.lua_getfield.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_char_p]
L.lua_getfield(st, -10002, b"RESULT")
r = L.lua_tolstring(st, -1, None).decode()
print(r)
sys.exit(0 if r.startswith("OK") else 1)
