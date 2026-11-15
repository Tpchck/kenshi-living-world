"""X3 (пакет 6): офлайн-проверка вызова на поединок в KMM_Diplo на lua51.dll из KenshiLua, без игры, ~1 с.
Заглушки движка/дирижёра — из test_diplo.py (как test_s4_world.py). Проверяется:
1) данные: разговор вызова, коды duel_open/duel_accept/duel_refuse, роли реплик, эффекты DA_FLAG_TEMP_ENEMY + DA_ATTACK_CHASE_FOREVER;
2) разговор вызова добавляется один раз главарю KMM_Outlaws, сопернику Nemesis, герою KMM_Fates и rival-отряду Q1 рядом (снимок KMM_Gov);
3) ответ лидера: трус (намного слабее) и кулдаун -> отказ, сильный -> принятие; поединок закрывает duel_open;
4) исходы: победа над сильным (слух outlaw_duel_won, вражда снята), поражение соперника Nemesis (nemesis_duel_lost, вражда снята после окна
   ограбления), таймаут героя (без слуха), указатель не читается (снят), помощь своих (слух «не один на один»);
5) player_raid против фракции лидера во время поединка не рвёт договор; смена мира сбрасывает поединок; маркеры DUEL в логе;
6) ревью batch6: амнистия конечна и снимается при смене мира / загрузке сейва / ошибке такта; вражда снимается со всего отряда
   (+ reThinkCurrentAIAction); в городе отказ; Q1 только по шаблонам rivals.json, без торговцев и отрядов в городе; разговор один на лидера
   (повторный скан и загрузка сейва не дублируют addConversation); персонажи поединка — через handle.
python -I -X utf8 build/KMM_Diplo/_dev/test_x3_duel.py"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = open(os.path.join(HERE, "test_diplo.py"), encoding="utf-8").read()
ns = {"__name__": "x3_harness"}
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
local roles = {}
for _, m in pairs(data.lines) do roles[m.role] = (roles[m.role] or 0) + 1 end
OK("data: duel dialogue + codes", W.duel_dialogue ~= nil and W.codes.duel_open == 31 and W.codes.duel_accept == 32 and W.codes.duel_refuse == 33
   and W.duel_events[1] == 1 and #data.duel.rival_factions >= 1)
OK("data: duel roles (ask, start, refused x2)", roles.duel_ask == 1 and roles.duel_start == 1 and roles.duel_refused == 2)
OK("data: duel params", data.params.duel == true and data.params.duel_loot_s > 0 and data.params.duel_coward_gap > 0)
-- персонажи с полями поединка
local HN = 0
local function FIGHTER(id, fid, x, z, player, skill)
  local c = CH(id, fid, x, z, player)
  HN = HN + 1; local h = "H" .. HN
  c.skill, c.dead, c.down, c.cleared, c.conv = skill or 30, false, false, {}, {}
  c.hd = { toString = function() return h end, isValid = function() return not c.gone end, getCharacter = function() return c end }
  c.getHandle = function() if c.gone then error("dangling character") end; return c.hd end
  c.rethink = 0
  c.reThinkCurrentAIAction = function() c.rethink = c.rethink + 1 end
  c.getCurrentTownLocation = function() return nil end
  c.isDead = function() if c.gone then error("dangling character") end; return c.dead end
  c.isDown = function() return c.down end
  c.isUnconcious = function() return false end
  c.getStats = function() return { getOverallSkillLevel_0_100 = function() return c.skill end } end
  c.getName = function() return id end
  c.clearTempEnemyStatus = function(_, other) c.cleared[#c.cleared + 1] = other.id end
  c.lists = {}
  c.dialogue = { addConversation = function(_, gd, ev) c.conv[#c.conv + 1] = tostring(gd.sid) .. "@" .. tostring(ev)
                   c.lists[ev] = c.lists[ev] or { conversationChoices = {} }; table.insert(c.lists[ev].conversationChoices, { data = gd }) end,
                 getConversationList = function(_, ev) return c.lists[ev] end }
  return c
end
local pc = FIGHTER("pc1", "P", 0, 0, true, 40)
local pc2 = FIGHTER("pc2", "P", 5000, 0, true, 20)
PCS = { pc, pc2 }; LOADED = { pc }
CFG.town_info = { T1 = { name = "Testtown" } }
local TOWN_T1 = { getGameData = function() return { stringID = "T1" } end }
TOWN = nil
pc.getCurrentTownLocation = function() return TOWN end
for i = 1, 10 do CLOCK = CLOCK + 1; FIRE("GameWorld::charsUpdate") end
OK("lazy start + hook", Dm.ready() and Dm.hook().on and Events.h["Dialogue::_checkCondition"] ~= nil)
local HOOK = Events.h["Dialogue::_checkCondition"][1]
local function Q(code) return HOOK(nil, 6, 0, 9000 + W.codes[code], nil, nil, false) end
local function T(n) for _ = 1, n do CLOCK = CLOCK + 1; FIRE("GameWorld::charsUpdate") end end
-- 2. кому добавить вызов
local boss = FIGHTER("Grit", "WEAK", 300, 0, false, 55)      -- главарь банды, сильнее игрока на 15
local rival = FIGHTER("Ash", "BIG", 400, 0, false, 45)       -- соперник Nemesis (pg)
local hero = FIGHTER("Vera", "FRIEND", 500, 0, false, 35)    -- герой Fates
local coward = FIGHTER("Mole", "ENEMY", 200, 0, false, 10)   -- слабый главарь
local drifter = FIGHTER("Drifter Joe", data.duel.rival_factions[1], 900, 0, false, 30)
local far = FIGHTER("Far Away", data.duel.rival_factions[1], 90000, 0, false, 30)
local function PL(ch) return { getSquadLeader = function() return ch end } end
local mate = FIGHTER("Grit's mate", "WEAK", 320, 0, false, 30)   -- товарищ главаря по отряду (ключ платуна pk3)
boss.getPlatoon = function() return { me = { getPlatoonStringID = function() return "pk3" end } } end
local trader = FIGHTER("Trader Bob", data.duel.rival_factions[1], 700, 0, false, 30)
local barmerc = FIGHTER("Bar Merc", data.duel.rival_factions[1], 800, 0, false, 30)
local guild = FIGHTER("Guild Merc", "1214-gamedata.base", 750, 0, false, 30)
KMM_Conductor.read_json = function(name) if name == "rivals.json" then return { prospectors = { TPL1 = { name = "Treasure hunters" } } } end end
KMM_Outlaws = { live = function() return { o1 = { pl = PL(boss) }, o2 = { pl = PL(rival) }, o3 = { pl = PL(coward) } } end,
                state = function() return { L = { o1 = { n = "Grit", st = "a" }, o2 = { n = "Ash", st = "a", pg = {} }, o3 = { n = "Mole", st = "a" } } } end }
KMM_Fates = { live = function() return { h1 = { pl = PL(hero) } } end, state = function() return { H = { h1 = { n = "Vera", st = "a" } } } end }
SNAP = {
  { fid = data.duel.rival_factions[1], pkey = "pk1", tsid = "TPL1", x = 900, z = 0, dead = false, pl = PL(drifter), ch = drifter },
  { fid = data.duel.rival_factions[1], pkey = "pk2", tsid = "TPL1", x = 90000, z = 0, dead = false, pl = PL(far), ch = far },
  { fid = "WEAK", pkey = "pk3", x = 100, z = 0, dead = false, pl = PL(boss), ch = boss },
  { fid = "WEAK", pkey = "pk3", x = 320, z = 0, dead = false, pl = PL(boss), ch = mate },
  { fid = data.duel.rival_factions[1], pkey = "pk4", tsid = "TPL1", trader = true, x = 700, z = 0, dead = false, pl = PL(trader), ch = trader },
  { fid = data.duel.rival_factions[1], pkey = "pk5", tsid = "TPL1", town = TOWN_T1, x = 800, z = 0, dead = false, pl = PL(barmerc), ch = barmerc },
  { fid = "1214-gamedata.base", pkey = "pk6", tsid = "BAR_MERCS", x = 750, z = 0, dead = false, pl = PL(guild), ch = guild },
  { fid = "FRIEND", pkey = "pk7", tsid = "TPL1", x = 500, z = 0, dead = false, pl = PL(hero), ch = hero } }   -- герой Fates и Q1: один разговор
KMM_Gov = { run = function(_, fn, ...) return fn(...) end, snapshot = function()
  local bp = {}; for _, r in ipairs(SNAP) do bp[r.pkey] = bp[r.pkey] or {}; table.insert(bp[r.pkey], r) end
  return { list = SNAP, by_pkey = bp } end }
T(5); T(5)
local ev1 = tostring(W.duel_dialogue) .. "@1"
local function nd(c) local n = 0; for _, x in ipairs(c.conv) do if x == ev1 then n = n + 1 end end; return n end   -- соперник ещё получает разговор-угрозу S4
OK("offer: outlaw boss, nemesis rival, fate hero, near drifter (once each, EV_PLAYER_TALK_TO_ME)",
   nd(boss) == 1 and #boss.conv == 1 and nd(rival) == 1 and nd(hero) == 1 and nd(drifter) == 1 and #far.conv == 0,
   table.concat({ nd(boss), nd(rival), nd(hero), nd(drifter), #far.conv }, ","))
OK("Q1: no traders, no squads in town, no Mercenary Guild, only rivals.json templates", #trader.conv == 0 and #barmerc.conv == 0 and #guild.conv == 0)
OK("Q1 + Fates hero: one conversation per leader", nd(hero) == 1 and #hero.conv == 1, #hero.conv)
OK("duel_open on, answers off", Q("duel_open") == true and Q("duel_accept") == false and Q("duel_refuse") == false)
-- загрузка сейва: ключи сессии сброшены, повторный скан находит разговор в списке лидера и не дублирует его
FIRE("PlayerInterface::loadFromSerialise"); T(5)
OK("save load: no duplicate addConversation, leader still known", nd(boss) == 1 and nd(hero) == 1 and nd(drifter) == 1
   and (LOGS or ""):find("DUEL offer kept: Grit (outlaw) already has it", 1, true), table.concat({ nd(boss), nd(hero), nd(drifter) }, ","))
local function LINE(role) for sid, m in pairs(data.lines) do if m.role == role then return { getStringID = function() return sid end } end end end
local function TALK(npc, role) Dm.on_line({ me = npc, getSpeaker = function() return pc end }, LINE(role)) end
-- 3. трус отказывает
TALK(coward, "duel_ask")
OK("coward (much weaker) refuses", Q("duel_refuse") == true and Q("duel_accept") == false)
TALK(coward, "duel_refused")
OK("refusal clears answer codes", Q("duel_refuse") == false and Dm.duel() == nil)
-- в городе лидер отказывается (стража и город вмешаются)
TOWN = TOWN_T1
TALK(hero, "duel_ask")
OK("in town: leader refuses", Q("duel_refuse") == true and (LOGS or ""):find("refuse, in town", 1, true)); TALK(hero, "duel_refused")
TOWN = nil
-- сильный главарь принимает
S.treaties[5] = { id = 5, type = "trade", a = "WEAK", b = "P", active = true, since = 90, term = 400 }
TALK(boss, "duel_ask")
OK("strong boss accepts", Q("duel_accept") == true and Q("duel_refuse") == false)
TALK(boss, "duel_start")
local d = Dm.duel()
OK("duel started (faction, diff, cooldown in conductor save)", d and d.fid == "WEAK" and d.diff == 15 and S.diplo.duel.cd[d.rec.key] == S.last_day)
OK("duel: handles + squad key, amnesty finite", d and d.hn == boss.hd and d.hp == pc.hd and d.pk == "pk3"
   and Dm.duel_until() - CLOCK <= data.params.duel_timeout_s + data.params.duel_loot_s + data.params.duel_spare_s)
T(5)
OK("duel_open off while fighting", Q("duel_open") == false)
TALK(hero, "duel_ask")
OK("second challenge during a duel refused", Q("duel_refuse") == true); TALK(hero, "duel_refused")
-- 5. удар игрока по фракции лидера (событие дирижёра player_raid) — не измена
S.events[#S.events + 1] = { id = S.next_id, type = "player_raid", a = "P", b = "WEAK" }; S.next_id = S.next_id + 1
T(6)
OK("player_raid during duel keeps the pact", S.treaties[5].active == true and Dm.duel_stats().spared == 1)
OK("duel_active(fid) for conductor", Dm.duel_active("WEAK") == true and Dm.duel_active("BIG") == false)
-- 4. победа над сильным
local nev = #S.events
TOWN = TOWN_T1   -- поединок у города (игрок зашёл в черту) — слух «near Testtown»
boss.down = true; T(1)
TOWN = nil
local e = S.events[#S.events]
OK("win: rumor outlaw_duel_won, strong, by player", #S.events == nev + 1 and e.type == "outlaw_duel_won" and e.by_player and e.strong
   and e.text:find("better fighter", 1, true) and e.text:find("near Testtown", 1, true), e and e.text)
OK("win: temp enemy cleared both ways, duel closed", #boss.cleared == 2 and pc.cleared[1] == "Grit" and Dm.duel() == nil)
OK("win: whole squad cleared + AI rethink", #mate.cleared == 2 and pc.cleared[2] == "Grit's mate" and #pc2.cleared == 2 and boss.rethink == 1 and mate.rethink == 1,
   table.concat({ #mate.cleared, tostring(pc.cleared[2]), #pc2.cleared, boss.rethink, mate.rethink }, ","))
OK("win: player message", MSGS[#MSGS] == e.text)
T(5)
OK("duel_open again after the duel", Q("duel_open") == true)
boss.down = false
TALK(boss, "duel_ask")
OK("cooldown: same leader refuses next time", Q("duel_refuse") == true); TALK(boss, "duel_refused")
-- поражение от соперника Nemesis: вражда снимается только после окна ограбления
TALK(rival, "duel_ask"); TALK(rival, "duel_start")
pc.down = true; T(1)
e = S.events[#S.events]
OK("loss: rumor nemesis_duel_lost", e.type == "nemesis_duel_lost" and e.text:find("purse emptied", 1, true), e.type)
OK("loss: hostility kept during loot window", #rival.cleared == 0 and Dm.duel() ~= nil)
T(data.params.duel_loot_s + 2)
OK("loss: hostility cleared after loot window", #rival.cleared == 2 and Dm.duel() == nil)
pc.down = false
-- таймаут героя: без слуха
nev = #S.events
TALK(hero, "duel_ask"); TALK(hero, "duel_start")
T(data.params.duel_timeout_s + 2)
OK("timeout: duel dropped, no rumor, cleared", Dm.duel() == nil and #S.events == nev and #hero.cleared == 2 and Dm.duel_stats().void == 1)
-- указатель лидера не читается -> снят, модуль жив
TALK(drifter, "duel_ask"); TALK(drifter, "duel_start")
drifter.gone = true; T(1)
OK("dangling leader: duel void, step not disabled", Dm.duel() == nil and not Dm.disabled().duel_step and Dm.duel_stats().void == 2)
-- помощь своих: слух «не один на один»
local brute = FIGHTER("Brute", "POOR", 300, 0, false, 40)
KMM_Outlaws.live = function() return { o9 = { pl = PL(brute) } } end
KMM_Outlaws.state = function() return { L = { o9 = { n = "Brute", st = "a" } } } end
T(5)
pc2.x = 350
TALK(brute, "duel_ask"); TALK(brute, "duel_start")
brute.down = true; T(1)
e = S.events[#S.events]
OK("helped win: rumor says not alone, not strong", e.type == "outlaw_duel_won" and e.text:find("not alone", 1, true) and not e.strong, e.text)
-- после окна duel_spare_s player_raid снова рвёт договор
T(data.params.duel_spare_s + 2)
S.events[#S.events + 1] = { id = S.next_id, type = "player_raid", a = "P", b = "WEAK" }; S.next_id = S.next_id + 1
T(6)
OK("after spare window player_raid breaks pact as before", S.treaties[5].active == false)
-- смена мира: поединок сброшен, указатели прошлого не трогаются
local brute2 = FIGHTER("Brute2", "POOR", 300, 0, false, 40)
KMM_Outlaws.live = function() return { o10 = { pl = PL(brute2) } } end
KMM_Outlaws.state = function() return { L = { o10 = { n = "Brute2", st = "a" } } } end
T(5)
TALK(brute2, "duel_ask"); TALK(brute2, "duel_start")
OK("duel on before world change", Dm.duel() ~= nil)
local S_old = S; S = {}; for k, v in pairs(S_old) do S[k] = v end
T(5)
OK("world change drops duel and offers", Dm.duel() == nil)
OK("world change drops amnesty (H1)", Dm.duel_active("POOR") == false and Dm.duel_until() < 0)
-- загрузка сейва посреди поединка: поединок и амнистия сброшены, указатели прошлого мира не трогаются
local brute3 = FIGHTER("Brute3", "POOR", 300, 0, false, 40)
KMM_Outlaws.live = function() return { o11 = { pl = PL(brute3) } } end
KMM_Outlaws.state = function() return { L = { o11 = { n = "Brute3", st = "a" } } } end
T(5)
TALK(brute3, "duel_ask"); TALK(brute3, "duel_start")
OK("duel on before save load", Dm.duel() ~= nil and Dm.duel_active("POOR") == true)
brute3.gone = true; pc.gone = true
FIRE("PlayerInterface::loadFromSerialise"); T(2)
pc.gone = false
OK("save load drops duel and amnesty, no dangling access", Dm.duel() == nil and Dm.duel_active("POOR") == false and not Dm.disabled().duel_step)
-- маркеры
local L = LOGS or ""
OK("markers: DUEL offer / ask / start / end / clear / spared",
   L:find("DUEL offer added: Grit (outlaw)", 1, true) and L:find("DUEL ask Mole (outlaw): diff -30 -> refuse, coward", 1, true)
   and L:find("DUEL start: Grit (outlaw, faction WEAK)", 1, true) and L:find("DUEL end: Grit (outlaw) -> won", 1, true)
   and L:find("DUEL clear: temp enemy status cleared", 1, true) and L:find("DUEL spared", 1, true))
OK("nothing disabled", next(Dm.disabled()) == nil, (function() local t = {}; for k in pairs(Dm.disabled()) do t[#t + 1] = k end; return table.concat(t, ",") end)())
-- ошибка такта посреди поединка: поединок и амнистия сброшены, вызов закрыт до перезапуска
local brute4 = FIGHTER("Brute4", "POOR", 300, 0, false, 40)
KMM_Outlaws.live = function() return { o12 = { pl = PL(brute4) } } end
KMM_Outlaws.state = function() return { L = { o12 = { n = "Brute4", st = "a" } } } end
T(5)
TALK(brute4, "duel_ask"); TALK(brute4, "duel_start")
local emit0 = KMM_Conductor.emit
KMM_Conductor.emit = function() error("emit exploded") end
brute4.down = true; T(1)
KMM_Conductor.emit = emit0
OK("step error: duel and amnesty dropped, step off", Dm.duel() == nil and Dm.duel_active("POOR") == false and Dm.disabled().duel_step == true)
T(5)
OK("step off: duel_open closed", Q("duel_open") == false)
return table.concat(R, "\n")
'''

FAILS, PASSES = [], []
st = new_state()
try:
    run(st, stubs_src, "stubs")
    run(st, read(MAIN), "kmm_diplo.lua")
    out = run(st, TESTS, "tests", ret=True)
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
