"""S4: офлайн-проверка условий мира KMM_Diplo (перехват Dialogue::_checkCondition) на lua51.dll из KenshiLua, без игры, ~1 с.
Заглушки движка/дирижёра — те же, что в test_diplo.py (берутся из него). Проверяется:
1) данные: коды мира, близнецы ответов без жетона, разговор-угроза соперника;
2) горячий путь: чужие условия → nil (ваниль), зарезервированные → bool из таблицы; скорость 200k вызовов;
3) такт мира: город игрока (голод, осада, беспорядки, опустение, хозяин враждебен/сменился), прозвище, соперник в городе;
4) посланник без жетонов при живом перехвате; «изложите письменно» → назад к жетонам; ошибка перехвата → жетоны;
5) соперник: addConversation один раз на живой отряд; маркеры в логе.
python -I -X utf8 build/KMM_Diplo/_dev/test_s4_world.py"""
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = open(os.path.join(HERE, "test_diplo.py"), encoding="utf-8").read()
ns = {"__name__": "s4_harness"}
head = SRC.split("# ---- 1. синтаксис", 1)[0]   # ctypes-обвязка lua51 без запуска старых сценариев
exec(compile(head, "test_diplo_head", "exec"), ns)
stubs_src = SRC.split("STUBS = r'''", 1)[1].split("'''.replace", 1)[0].replace("TMPDIR", ns["TMP"])
new_state, run, read, MAIN = ns["new_state"], ns["run"], ns["read"], ns["MAIN"]

TESTS = r'''
local R = {}
local function OK(name, cond, info) R[#R + 1] = (cond and "PASS " or "FAIL ") .. name .. (info and (" | " .. tostring(info)) or "") end
local Dm = KMM_Diplo
local data = require("kmm_diplo_data")
local W = data.world
-- 1. данные
OK("data: world block", W and W.cond == 6 and W.base == 9000 and W.codes.town_hungry and W.rival_dialogue ~= nil)
local twins, roles = 0, {}
for sid, m in pairs(data.lines) do if m.twin then twins = twins + 1; roles[m.role] = true end end
OK("data: token-free twins (>= 20, commit roles kept)", twins >= 20 and roles.commit, twins)
-- 2. до старта: перехвата нет, горячий путь молчит
OK("before init: _check -> nil", Dm._check(nil, 6, 0, 9001) == nil)
-- мир и персонажи
CFG.town_info = { T1 = { name = "Testtown" } }
CFG.factions.WEAK.towns = { "T1" }
MOOD = { pop = 20, pop0 = 50, unrest = 0.7, food = 0.2, owner = "BIG" }
KMM_Conductor.town_mood = function(sid) if sid == "T1" then return MOOD end end
SIEGE = true
KMM_Stock = { stock = function(sid) return { siege = SIEGE } end, level = function() return 1 end }
TITLE = "Kingslayer"
RIVALS = { { n = "Grit", s = "T1", pg = {}, st = "a" } }
KMM_Nemesis = { player_title = function() return TITLE end, rivals = function() return RIVALS end }
local pc = CH("pc1", "P", 0, 0, true)
pc.getCurrentTownLocation = function() return { getGameData = function() return { stringID = "T1" } end } end
PCS = { pc }
local npc = CH("envoy1", "WEAK", 100, 0, false); LOADED = { npc, pc }
for i = 1, 10 do CLOCK = CLOCK + 1; FIRE("GameWorld::charsUpdate") end
OK("lazy start + hook registered", Dm.ready() and Events.h["Dialogue::_checkCondition"] ~= nil and Dm.hook().on)
local HOOK = Events.h["Dialogue::_checkCondition"][1]
local function Q(code) return HOOK(nil, 6, 0, 9000 + W.codes[code], nil, nil, false) end
CLOCK = CLOCK + 5; FIRE("GameWorld::charsUpdate")
-- 3. ответы по миру
OK("vanilla condition untouched", HOOK(nil, 2, 2, 100, nil, nil, true) == nil and HOOK(nil, 6, 0, 5, nil, nil, true) == nil and HOOK(nil, 6, 0, 9500) == nil)
OK("town hungry", Q("town_hungry") == true and Q("town_plenty") == false)
OK("town siege / unrest / emptied", Q("town_siege") and Q("town_unrest") and Q("town_emptied"))
OK("owner hostile + captured (BIG holds WEAK's town)", Q("owner_hostile") and Q("owner_captured"))
OK("player title / rival alive / rival here", Q("player_title") and Q("rival_alive") and Q("rival_here"))
MOOD = { pop = 50, pop0 = 50, unrest = 0, food = 2.0, owner = "WEAK" }; SIEGE = false; TITLE = nil; RIVALS = {}
CLOCK = CLOCK + 5; FIRE("GameWorld::charsUpdate")
OK("world changes follow state", Q("town_plenty") and not Q("town_hungry") and not Q("town_siege") and not Q("owner_captured") and not Q("owner_hostile")
   and not Q("player_title") and not Q("rival_alive") and not Q("town_emptied"))
pc.getCurrentTownLocation = function() return nil end
CLOCK = CLOCK + 5; FIRE("GameWorld::charsUpdate")
OK("outside towns: town codes off", not Q("town_plenty") and not Q("town_unrest"))
-- 4. посланник: перехват жив → без жетонов
OK("cond mode on (hook seen)", Dm.cond_mode())
local DLG = { me = npc, getSpeaker = function() return pc end }
local function LINE(sid) return { getStringID = function() return sid end } end
local function line_of(role, kind, outcome, twin)
  for sid, m in pairs(data.lines) do if m.role == role and (not kind or m.kind == kind) and (not outcome or m.outcome == outcome) and (not twin == not m.twin) then return sid end end
end
S.treaties[7] = { id = 7, type = "trade", a = "WEAK", b = "P", active = true, since = 90, term = 400 }
local t0 = Dm.stats().tokens
Dm.on_line(DLG, LINE(line_of("open")))
OK("open: has_pact by condition, no token", Q("has_pact") and (pc.items[data.items.has_pact] or 0) == 0)
Dm.on_line(DLG, LINE(line_of("propose", "nonaggression")))
local acc = Q("dec_accept") or Q("dec_refuse") or Q("dec_counter_s") or Q("dec_counter_l")
OK("propose: decision by condition, no token", acc and Dm.stats().tokens == t0, Dm.stats().tokens - t0)
Dm.on_line(DLG, LINE(line_of("commit", "nonaggression", "accept", true)))
OK("commit (twin line) queues and clears decision", #Dm.queue() >= 1 and not Q("dec_accept") and not Q("dec_refuse"))
CLOCK = CLOCK + 2; FIRE("GameWorld::charsUpdate")
Dm.on_line(DLG, LINE(line_of("close")))
OK("close clears conversation codes", not Q("has_pact"))
-- «изложите письменно» при ответе по условию → назад к жетонам
Dm.on_line(DLG, LINE(line_of("open"))); Dm.on_line(DLG, LINE(line_of("propose", "trade")))
Dm.on_line(DLG, LINE(line_of("deferred", "trade")))
OK("deferred after cond reply -> tokens again", not Dm.cond_mode() and Dm.hook().fail == 1)
Dm.on_line(DLG, LINE(line_of("open"))); Dm.on_line(DLG, LINE(line_of("propose", "trade")))
OK("token mode gives token again", Dm.stats().tokens > t0)
Dm.hook().fail = 0
-- соперник: разговор-угроза в рантайме
local LV = { pl = { getSquadLeader = function() return LEADER end } }
ADDED = {}
LEADER = { dialogue = { addConversation = function(_, gd, ev) ADDED[#ADDED + 1] = tostring(gd.sid) .. "@" .. tostring(ev) end } }
KMM_Outlaws = { live = function() return { o3 = LV } end, state = function() return { L = { o3 = { n = "Grit", pg = {}, st = "a" } } } end }
CLOCK = CLOCK + 5; FIRE("GameWorld::charsUpdate")
CLOCK = CLOCK + 5; FIRE("GameWorld::charsUpdate")
OK("rival: threat talk added once per live squad (2 events)", #ADDED == 2 and ADDED[1] == tostring(W.rival_dialogue) .. "@66", table.concat(ADDED, ","))
-- M3: подхват того же постоянного главаря — новая таблица lv, та же запись → без дублей
local LV2 = { pl = { getSquadLeader = function() return LEADER end } }
KMM_Outlaws.live = function() return { o3 = LV2 } end
CLOCK = CLOCK + 5; FIRE("GameWorld::charsUpdate")
OK("rival: re-adopted squad (new lv) gets no duplicate talk", #ADDED == 2, #ADDED)
-- H3: getSquadLeader падает → под pcall, модуль жив, отряд больше не трогаем
local CALLS = 0
local LVX = { pl = { getSquadLeader = function() CALLS = CALLS + 1; error("dangling platoon") end } }
KMM_Outlaws.live = function() return { o3 = LV2, o4 = LVX } end
KMM_Outlaws.state = function() return { L = { o3 = { n = "Grit", pg = {}, st = "a" }, o4 = { n = "Ash", pg = {}, st = "a" } } } end
CLOCK = CLOCK + 5; FIRE("GameWorld::charsUpdate"); CLOCK = CLOCK + 5; FIRE("GameWorld::charsUpdate")
OK("rival: leader error caught, squad skipped after first miss", CALLS == 1 and not Dm.disabled().rival_talk, CALLS)
-- H3: загружен другой сейв (новая таблица состояния дирижёра) → отряды прошлого мира не трогаем; новые — получают разговор
local STALE_CALLS = 0
local LVOLD = { pl = { getSquadLeader = function() STALE_CALLS = STALE_CALLS + 1; return LEADER end } }
KMM_Outlaws.live = function() return { o5 = LVOLD } end
KMM_Outlaws.state = function() return { L = { o5 = { n = "Old", pg = {}, st = "a" } } } end
local S_old = S; S = {}; for k, v in pairs(S_old) do S[k] = v end   -- как после loadFromSerialise: другой объект состояния
CLOCK = CLOCK + 5; FIRE("GameWorld::charsUpdate")
local LVNEW = { pl = { getSquadLeader = function() return LEADER end } }
KMM_Outlaws.live = function() return { o5 = LVOLD, o6 = LVNEW } end
KMM_Outlaws.state = function() return { L = { o5 = { n = "Old", pg = {}, st = "a" }, o6 = { n = "Grit", pg = {}, st = "a" } } } end
CLOCK = CLOCK + 5; FIRE("GameWorld::charsUpdate")
OK("rival: after world change old squads untouched, new one gets talk", STALE_CALLS == 0 and #ADDED == 4 and not Dm.disabled().rival_talk,
   STALE_CALLS .. " " .. #ADDED)
-- ревью: деньги игрока — через персонажа (у PlayerInterface нет getOwnerships); мёртвый пропускается; платун — запасной путь
do
  local sp, sm = PCS, MONEY
  local dead = CH("pcd", "P", 0, 0, true); dead.isDead = function() return true end; dead.getOwnerships = function() return { getMoney = function() return 1 end } end
  local alive = CH("pca", "P", 0, 0, true); MONEY = 4321
  PCS = { dead, alive }
  OK("money: Character:getOwnerships of a live player char", Dm._money() == 4321, Dm._money())
  local plat = CH("pcp", "P", 0, 0, true); plat.getOwnerships = function() error("no ownerships") end; plat.getMoney = nil
  plat.getPlatoon = function() return { me = { getOwnerships = function() return { getMoney = function() return 777 end } end } } end
  PCS = { plat }
  OK("money: platoon ownerships fallback", Dm._money() == 777, Dm._money())
  PCS = {}
  OK("money: no player chars -> 0", Dm._money() == 0)
  PCS, MONEY = sp, sm
end
-- B1: имя условия не числом (биндинги обещают целое) — терпим, считаем, пишем тип в debug.log; маркеры мира — в debug.log
local hk = Dm.hook(); local c0 = hk.calls
local r1 = Dm._check(nil, "6", 0, 9001)
OK("hot path: non-number cname tolerated and counted", r1 ~= nil and hk.calls == c0 + 1 and hk.ctype == "string" and hk.cond_n > 0, tostring(r1) .. " " .. tostring(hk.ctype))
CLOCK = CLOCK + 5; FIRE("GameWorld::charsUpdate")
local df = io.open("C:/KenshiModMap/logs/debug.log", "r"); local DL = df and df:read("*a") or ""; if df then df:close() end
OK("debug.log: DIPLO_WORLD / asked / stats (session_report reads debug.log)",
   DL:find("DIPLO_WORLD town=Testtown", 1, true) and DL:find("DIPLO_COND asked town_hungry", 1, true)
   and DL:find("DIPLO_COND stats: calls=", 1, true) and DL:find("cname_type=string", 1, true), #DL)
-- ошибка в перехвате → отключается только он, жетоны
local bad = setmetatable({}, { __index = function() error("hook exploded") end })
local save = Dm.hook().asked; Dm.hook().asked = bad
HOOK(nil, 6, 0, 9002)
Dm.hook().asked = save
OK("hook error disables only 'cond' -> tokens", Dm.disabled().cond == true and not Dm.cond_mode() and not Dm.disabled().tick and HOOK(nil, 6, 0, 9001) == nil)
-- 5. маркеры
local L = LOGS or ""
OK("markers: DIPLO_WORLD / DIPLO_COND hook live / asked / DIPLO_RIVAL / fallback",
   L:find("DIPLO_WORLD town=Testtown flags=", 1, true) and L:find("DIPLO_COND hook live", 1, true) and L:find("DIPLO_COND asked town_hungry", 1, true)
   and L:find("DIPLO_RIVAL threat talk added: Grit", 1, true) and L:find("DIPLO_COND fallback", 1, true))
return table.concat(R, "\n")
'''

PERF = r'''
local Dm = KMM_Diplo
local N = 0
for i = 1, 200000 do if Dm._check(nil, (i % 3 == 0) and 6 or 23, 0, (i % 2 == 0) and 9001 or 1) ~= nil then N = N + 1 end end
return tostring(N)
'''

FAILS, PASSES = [], []
st = new_state()
try:
    run(st, stubs_src, "stubs")
    run(st, read(MAIN), "kmm_diplo.lua")
    out = run(st, TESTS, "tests", ret=True)
    t = time.perf_counter()
    n = run(st, PERF, "perf", ret=True)
    dt = time.perf_counter() - t
    out += "\n" + ("PASS" if dt < 1.0 else "FAIL") + f" hot path: 200k checks in {dt * 1000:.0f} ms (answered {n})"
except RuntimeError as e:
    out = "FAIL runtime: " + str(e)
for ln in out.splitlines():
    (FAILS if ln.startswith("FAIL") else PASSES).append(ln)
for p in PASSES:
    print(p)
for f_ in FAILS:
    print(f_)
print(f"\n{len(PASSES)} passed, {len(FAILS)} failed")
sys.exit(1 if FAILS else 0)
