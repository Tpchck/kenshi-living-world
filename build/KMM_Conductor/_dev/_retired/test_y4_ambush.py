"""Offline test Y4: наряд засады через ядро (KMM_Predators.ambush_hold): Blackboard:addSquadJob (весь отряд, TEE_REMOVE_WHOLE_SQUADS) +
AI:setCenterOfMovement/setManuveringFreedomLevel у лидера; через hold_h+hold_pp*power игровых часов снятие: clearAllTheJobs + replaceAIPackage
(пакет отряда) + ROAM_FAR; отряд пропал -> без вызовов; отказ ядра -> addOrder и самоотключение; крэш-сторож; смена мира/откат часов;
связка с visible() через KMM_Traces.request. python -I -X utf8 build/KMM_Conductor/_dev/test_y4_ambush.py -> OK."""
import ctypes, re, sys, tempfile

DLL = r"C:\Program Files (x86)\Steam\steamapps\workshop\content\233860\3817000612\lua51.dll"
B = r"C:\KenshiModMap\build\KMM_Conductor\scripts\init"
TMP = tempfile.mkdtemp(prefix="kmm_y4_").replace("\\", "/")
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
# стаб отряда ядра: доска с нарядами, лидер с AI, список платунов фракции; фабрика может отдавать такой отряд
run(r'''
JOBS, ORDERS, AICALLS, BCALLS, LOCKS = {}, {}, {}, {}, {}
JOB_MODE = "ok"   -- ok | noreg (наряд не регистрируется) | err (вызов падает)
FPL = {}          -- [fid] = { платуны } для getActivePlatoons
function MKPL(key, fid, opt)
  opt = opt or {}
  local ai = {}   -- opt.prev: прежнее движение лидера читается (AI.centerOfMovement / AI.ordersMovement)
  if opt.prev then ai.centerOfMovement = { x = 11, y = 5, z = 22 }; ai.ordersMovement = 0 end
  function ai:setCenterOfMovement(v) AICALLS[#AICALLS + 1] = { k = key, m = "center", x = v.x, y = v.y, z = v.z } end
  function ai:setManuveringFreedomLevel(a) AICALLS[#AICALLS + 1] = { k = key, m = "free", a = a } end
  local leader = { h = "H_" .. key }
  function leader:getHandle() return self.h end
  function leader:getAI() return ai end
  function leader:getPosition() if opt.far then return { x = 90000, y = 77, z = 0 } end return { x = 0, y = 77, z = 0 } end
  function leader:addOrder(d, tt, sub, sh, cl, loc) ORDERS[#ORDERS + 1] = { k = key, tt = tt, x = loc.x, z = loc.z } end
  local board = { squadJobs = {}, squadJobs2 = {}, leaderJobs = {} }
  function board:addSquadJob(ty, tk, subj, pri, w, tg, tee, t0, t1)
    local f = io.open("TMPDIR/probe_squadJob.lock", "r"); if f then LOCKS.sq = true; f:close() end
    if JOB_MODE == "err" then error("bad argument #3 to 'addSquadJob' (KenshiLua.hand expected)") end
    JOBS[#JOBS + 1] = { k = key, ty = ty, tk = tk, subj = subj, pri = pri, w = w, tg = tg, tee = tee, t0 = t0, t1 = t1 }
    if JOB_MODE == "ok" then local l = (ty == 2) and self.leaderJobs or self.squadJobs; l[#l + 1] = true end
  end
  function board:getCurrentPackage() return { packageData = { stringID = opt.pkg or "pkgA" } } end
  function board:clearAllTheJobs() BCALLS[#BCALLS + 1] = { k = key, m = "clear" } end
  function board:replaceAIPackage(gd) BCALLS[#BCALLS + 1] = { k = key, m = "pkg", sid = gd.stringID, t = gd.t } end
  local p = { key = key }
  function p:getPlatoonStringID() return key end
  function p:getSquadLeader() if opt.noleader then return nil end return leader end
  function p:getBlackboard() if opt.noboard then error("no board") end return board end
  FPL[fid] = FPL[fid] or {}
  table.insert(FPL[fid], p)
  return p
end
FACTORY_PL = nil   -- если задан: createRandomSquad отдаёт отряд ядра
local gw0 = getGameWorld
getGameWorld = function()
  local g = gw0()
  local mk = g.theFactory.createRandomSquad
  g.theFactory.createRandomSquad = function(self, f, ...) local r = mk(self, f, ...); if FACTORY_PL then return FACTORY_PL(f.id) end return r end
  local fm = g.factionMgr.getFactionByStringID
  g.factionMgr.getFactionByStringID = function(self, id) local fo = fm(self, id); fo.getActivePlatoons = function() return FPL[id] or {} end; return fo end
  return g
end
'''.replace("TMPDIR", TMP), "squad stub")
run("math.randomseed(20261117)", "seed")
for f in [p.split("\\")[-1] for p in sorted(__import__("glob").glob(B + r"\KMM_Conductor*.lua"))] + ["KMM_Traces.lua", "KMM_Predators.lua"]:
    run(open(B + "\\" + f, encoding="utf-8").read(), f)
run('KMM_Predators.P.sdir = "%s/"' % TMP, "sdir")
run(r'''
N, FAILS = 0, {}
function check(c, what) N = N + 1; if not c then FAILS[#FAILS + 1] = what end end
local C, Pr, T = KMM_Conductor, KMM_Predators, KMM_Traces
C.reset()
C.advance(10); C.advance(16); DAYV = 16.25   -- 06:00
local P = Pr.P
P.tick_gap = 0; P.daily_chance = 0; P.smell = false
local TP = C.cfg().params.traces
TP.first_hour_traces = 0; TP.max_per_day = 1000; TP.max_queue = 1000; TP.arrive_enabled = false; TP.bounty = { enabled = false }
TaskType = TaskType or { HOLD_POSITION = 30, PATROL_TOWN = 36 }
local pf = C.cfg().player_faction
PCS = {}; CHARS = {}
local ch = MKCH("PC1", pf or "player", 9e6, 9e6, { player = true, platoon = "player_squad" })
PCS[1] = ch; CHARS[1] = ch
local SQ = Pr.sq
local function pump(n) for i = 1, n do CLOCK = CLOCK + 10; FIRE("GameWorld::charsUpdate", {}) end end
local function rd(p) local f = io.open(p, "r"); if not f then return "" end local s = f:read("*a"); f:close(); return s end
local function cnt(t, k, m) local n = 0; for _, c in ipairs(t) do if (not k or c.k == k) and (not m or c.m == m) then n = n + 1 end end; return n end
pump(1)
-- 1. наряд двум отрядам: весь отряд, хендл лидера, конец наряда, центр движения у гнезда; реестр — в сейве (C.state().ext.pred_sq)
local p1, p2 = MKPL("K1", "fB", { prev = true }), MKPL("K2", "fB")
Pr.ambush_hold({ p1, p2 }, 1000, 2000, 8, "fB")
check(#JOBS == 4 and #ORDERS == 0, "4 наряда, без addOrder: " .. #JOBS .. "/" .. #ORDERS)
local j1, j2 = JOBS[1] or {}, JOBS[2] or {}
check(j1.ty == 2 and j2.ty == 0 and j1.tk == 30 and j2.tk == 30, "SQUAD_LEADER + SQUAD_1, HOLD_POSITION")
check(j1.subj == "H_K1" and j1.pri == 3 and j1.tg == 1 and j2.tg == 2 and j1.tee == 2, "хендл лидера, TP_URGENT, TARGET_SELF/LEADER, TEE_REMOVE_WHOLE_SQUADS")
check(j1.t0 == 6 and j1.t1 == 14, "часы суток наряда 6-14: " .. tostring(j1.t0) .. "-" .. tostring(j1.t1))
local c1 = AICALLS[1] or {}
check(c1.m == "center" and c1.x == 1000 and c1.z == 2000 and c1.y == 77 and AICALLS[2].m == "free" and AICALLS[2].a == 1, "центр движения в точке + STAY_CLOSE")
check(LOCKS.sq and io.open("TMPDIR/probe_squadJob.lock", "r") == nil, "крэш-сторож: lock во время вызова, снят после")
check(#SQ.live == 2 and type(SQ.live[1].k) == "string" and SQ.live[1].pl == nil, "записи — ключи платунов, без указателей")
check(C.state().ext.pred_sq == SQ.live and SQ.live[1].cx == 11 and SQ.live[1].mv == 0 and SQ.live[2].cx == nil, "реестр в C.state().ext.pred_sq, прежнее движение лидера записано")
local lg = rd("TMPDIR/predators.log")
check(lg:find("squadjob registered key=K1 fid=fB hold=8.0h hours 6-14 jobs=0->2 center=ok prev=11,22/0 pkg=pkgA", 1, true), "маркер squadjob registered")
check(not lg:find("squadjob ok", 1, true), "регистрация не выдаётся за работу")
-- 2. через sq_verify_h лидер у точки -> «squadjob ok»; до срока не снимается; после срока — пакет, прежний центр и уровень свободы
DAYV = DAYV + 7 / 24; pump(1)
check(#BCALLS == 0 and #SQ.live == 2, "до срока держат")
check(rd("TMPDIR/predators.log"):find("squadjob ok key=K1 fid=fB: leader 2236 from the point", 1, true) and SQ.st.work == 2, "проба работы: лидер у точки -> squadjob ok")
DAYV = DAYV + 1.5 / 24; pump(1)
check(cnt(BCALLS, "K1", "clear") == 1 and cnt(BCALLS, "K1", "pkg") == 1 and cnt(BCALLS, "K2", "pkg") == 1, "снятие: clearAllTheJobs + replaceAIPackage")
local bp = BCALLS[2] or {}
check(bp.sid == "pkgA" and bp.t == 72, "пакет отряда AI_PACKAGE=72: " .. tostring(bp.sid))
local function last_ai(k, m) for i = #AICALLS, 1, -1 do local c = AICALLS[i]; if c.k == k and c.m == m then return c end end return {} end
check(last_ai("K1", "center").x == 11 and last_ai("K1", "center").z == 22 and last_ai("K1", "free").a == 0, "K1: прежний центр движения и уровень свободы возвращены")
check(last_ai("K2", "center").x == 0 and last_ai("K2", "center").y == 77 and last_ai("K2", "free").a == 2, "K2 (прежнее не читалось): центр у лидера + ROAM_FAR")
check(#SQ.live == 0 and #C.state().ext.pred_sq == 0, "записи сняты (и в сейве)")
check(rd("TMPDIR/predators.log"):find("squadjob release key=K1 (time): jobs cleared; pkg pkgA ok; center saved move 0 ok", 1, true), "маркер squadjob release")
-- 3. отряд не загружен -> запись ждёт; появился -> снят; не появился за sq_grace_d дней после срока -> забыт
local p3 = MKPL("K3", "fC")
Pr.ambush_hold({ p3 }, 0, 0, 6, "fC")
FPL.fC = {}
local b0 = #BCALLS
DAYV = DAYV + 0.3; pump(1)
check(#BCALLS == b0 and #SQ.live == 1 and rd("TMPDIR/predators.log"):find("K3 (time): squad not loaded - retry", 1, true), "невыгруженный отряд: запись ждёт, без вызовов")
FPL.fC = { p3 }; pump(1)
check(#SQ.live == 1, "повтор не чаще sq_retry_s")
pump(3)
check(#SQ.live == 0 and cnt(BCALLS, "K3", "clear") == 1, "отряд снова загружен -> наряд снят")
Pr.ambush_hold({ MKPL("K3b", "fC2") }, 0, 0, 6, "fC2")
FPL.fC2 = {}
DAYV = DAYV + 0.3; pump(4)
check(#SQ.live == 1, "до конца отсрочки запись жива")
DAYV = DAYV + 3.1; pump(4)
check(#SQ.live == 0 and rd("TMPDIR/predators.log"):find("K3b (time): squad gone (unloaded/dead) 3 days past the end", 1, true), "после отсрочки забыт")
b0 = #BCALLS
-- 4. откат часов -> снятие сейчас; загрузка сейва / смена мира -> записи из сейва снимаются при первом нахождении
Pr.ambush_hold({ MKPL("K4", "fD") }, 0, 0, 6, "fD")
SQ.live[1].t0 = C.day() + 1; pump(1)   -- C.day() монотонен; откат = запись из «будущего»
check(#SQ.live == 0 and cnt(BCALLS, "K4", "clear") == 1 and rd("TMPDIR/predators.log"):find("squadjob release key=K4 (clock)", 1, true), "откат часов: наряд снят")
Pr.ambush_hold({ MKPL("K5", "fD") }, 0, 0, 6, "fD")
local saved = {}
for _, r in ipairs(C.state().ext.pred_sq) do local c = {}; for k, v in pairs(r) do c[k] = v end; saved[#saved + 1] = c end
C.state().ext.pred_sq = saved; SQ.S = {}   -- как после загрузки: новые таблицы записей, новый мир
pump(1)
check(#SQ.live == 0 and cnt(BCALLS, "K5", "clear") == 1 and cnt(BCALLS, "K5", "pkg") == 1, "запись из сейва: отряд найден -> наряд снят")
lg = rd("TMPDIR/predators.log")
check(lg:find("world loaded with 1 holds from the save", 1, true) and lg:find("squadjob release key=K5 (load)", 1, true), "маркеры загрузки и снятия (load)")
-- 4b. снятие без пакета при спавне: задачи чистятся всегда, пакет — текущий
local pn = MKPL("KN", "fD")
Pr.ambush_hold({ pn }, 0, 0, 6, "fD")
SQ.live[#SQ.live].p = nil; DAYV = DAYV + 0.3; pump(1)
check(cnt(BCALLS, "KN", "clear") == 1 and cnt(BCALLS, "KN", "pkg") == 1 and rd("TMPDIR/predators.log"):find("key=KN (time): jobs cleared; pkg current ok", 1, true), "без пакета: clearAllTheJobs + текущий пакет")
-- 4c. потолок sq_max: старейший снимается, а не забывается
P.sq_max = 2
Pr.ambush_hold({ MKPL("KC1", "fG"), MKPL("KC2", "fG"), MKPL("KC3", "fG") }, 0, 0, 6, "fG")
check(#SQ.live == 2 and cnt(BCALLS, "KC1", "clear") == 1 and rd("TMPDIR/predators.log"):find("squadjob release key=KC1 (cap)", 1, true), "потолок: старейший наряд снят (cap)")
P.sq_max = 9; DAYV = DAYV + 0.3; pump(1)
check(#SQ.live == 0, "остальные сняты по сроку")
-- 4d. лидер ушёл от точки -> «squadjob drift» + addOrder этому отряду
local od = #ORDERS
Pr.ambush_hold({ MKPL("KD", "fG", { far = true }) }, 0, 0, 6, "fG")
DAYV = DAYV + 1.2 / 24; pump(1)
check(#ORDERS == od + 1 and ORDERS[#ORDERS].k == "KD" and rd("TMPDIR/predators.log"):find("squadjob drift key=KD", 1, true), "проба работы: ушёл -> drift + addOrder")
DAYV = DAYV + 0.3; pump(1)
check(#SQ.live == 0, "drift-наряд снят по сроку")
-- 5. отряд не готов (нет доски) -> addOrder, наряд жив
local o0 = #ORDERS
Pr.ambush_hold({ MKPL("K6", "fE", { noboard = true }) }, 5, 6, 6, "fE")
check(#ORDERS == o0 + 1 and ORDERS[#ORDERS].tt == 30 and not SQ.off and SQ.st.skip >= 1, "skip -> addOrder, наряд не выключен")
-- 6. наряд не зарегистрирован -> FAIL, самоотключение, addOrder; дальше сразу addOrder
JOB_MODE = "noreg"
local jn = #JOBS
Pr.ambush_hold({ MKPL("K7", "fE") }, 5, 6, 6, "fE")
check(SQ.off and #ORDERS == o0 + 2 and #SQ.live == 0, "noreg -> FAIL + addOrder")
check(rd("TMPDIR/predators.log"):find("squadjob FAIL key=K7 fid=fE: jobs on board 0 -> 0 (not registered)", 1, true), "маркер squadjob FAIL")
check(rd("TMPDIR/predators.log"):find("squadjob fallback addOrder 1/1", 1, true), "маркер fallback")
jn = #JOBS
Pr.ambush_hold({ MKPL("K8", "fE") }, 5, 6, 6, "fE")
check(#JOBS == jn and #ORDERS == o0 + 3, "после FAIL наряд не пробуется")
check(not Pr.disabled(), "модуль Predators жив")
-- 7. вызов падает -> FAIL
SQ.off = false; JOB_MODE = "err"
Pr.ambush_hold({ MKPL("K9", "fE") }, 5, 6, 6, "fE")
check(SQ.off and #ORDERS == o0 + 4 and rd("TMPDIR/predators.log"):find("squadjob FAIL key=K9", 1, true), "ошибка вызова -> FAIL + addOrder")
-- 7b. наряды регистрируются, но не держат (2 ухода, 0 подтверждений) -> наряд выключен
SQ.off = false; JOB_MODE = "ok"; SQ.st.work = 0; SQ.st.drift = 0
Pr.ambush_hold({ MKPL("KF1", "fH", { far = true }), MKPL("KF2", "fH", { far = true }) }, 0, 0, 6, "fH")
DAYV = DAYV + 1.2 / 24; pump(1)
check(SQ.off and rd("TMPDIR/predators.log"):find("jobs register but do not hold", 1, true), "2 drift без ok -> наряд выключен")
SQ.off = false; DAYV = DAYV + 0.3; pump(1)
check(#SQ.live == 0, "и сняты по сроку")
-- 8. связка: гнездо у игрока -> visible() -> Traces.request -> on_spawn -> наряд на hold_h + hold_pp*power часов
SQ.off = false; JOB_MODE = "ok"; SQ.st.reg = 0
local e = Pr.slot()
e.nests["ya|yb"] = { a = "ya", b = "yb", x = 50000, z = 50000, fid = "fN", owner = "fO", power = 2, born = math.floor(DAYV), loot = 0, raids = 0, pw = 99 }
ch.getPosition = function() return { x = 50300, y = 0, z = 50000 } end
local np = 0
FACTORY_PL = function(fid) np = np + 1; return MKPL("V" .. np, fid) end
local T0 = T.request
local RQ = 0
T.request = function(job) RQ = RQ + 1; if job.tag == "predator_ambush" then job.on_spawn({ FACTORY_PL(job.fid), FACTORY_PL(job.fid) }) end; return true end
pump(1)
T.request = T0
check(RQ >= 1 and SQ.st.reg == 2 and #SQ.live == 2, "засада из visible(): наряд обоим отрядам: " .. SQ.st.reg)
check((SQ.live[1] or {}).f == "fN" and math.abs(((SQ.live[1] or {}).till or 0) - (SQ.live[1] or {}).t0 - 8 / 24) < 1e-6, "срок = 6 + 1*2 часа")
e.nests["ya|yb"] = nil; FACTORY_PL = nil
-- 9. крэш-сторож: lock при старте -> addSquadJob не вызывается, .off, addOrder
local fh = io.open("TMPDIR/probe_squadJob.lock", "w"); fh:write("x"); fh:close()
assert(loadfile("PREDPATH"))()
Pr = KMM_Predators; Pr.P.sdir = "TMPDIR/"
jn = #JOBS; o0 = #ORDERS
Pr.ambush_hold({ MKPL("KA", "fE") }, 5, 6, 6, "fE")
check(#JOBS == jn and #ORDERS == o0 + 1 and Pr.sq.off, "после упавшей сессии наряд не вызывается, addOrder")
check(io.open("TMPDIR/probe_squadJob.off", "r") ~= nil and io.open("TMPDIR/probe_squadJob.lock", "r") == nil, ".off создан, lock убран")
-- 10. выключатель конфига
assert(loadfile("PREDPATH"))()
Pr = KMM_Predators; Pr.P.sdir = "TMPDIR/"; Pr.P.squadjob = false
o0 = #ORDERS
Pr.ambush_hold({ MKPL("KB", "fE") }, 5, 6, 6, "fE")
check(#ORDERS == o0 + 1 and not Pr.sq.off, "squadjob=false -> addOrder")
RESULT = #FAILS == 0 and ("OK " .. N) or ("FAIL: " .. table.concat(FAILS, "; "))
'''.replace("TMPDIR", TMP).replace("PREDPATH", (B + "/KMM_Predators.lua").replace("\\", "/")), "test")
L.lua_getfield.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_char_p]
L.lua_getfield(st, -10002, b"RESULT")
r = L.lua_tolstring(st, -1, None).decode()
print(r)
sys.exit(0 if r.startswith("OK") else 1)
