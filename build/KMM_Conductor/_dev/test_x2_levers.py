"""Offline test KMM_RecruitRace X2 (пакет 6): рычаг merc (конкурент нанял отряд Mercenary Guild: setContractJob / _setContractJob,
проверка hasContractJob, конец контракта -> recruit_merc_left, лимит недели, отказы) и рычаг slave (работорговец забирает самого сильного раба
лавки: по умолчанию только слух recruit_slave_eyed; при Q.slave_owner changeSlaveOwner, проверка getMySlaveOwner, откат клеткой,
recruit_slave_bought, освобождение взломом игрока -> recruit_slave_freed без LT_FREED_ME). M1: занятые нашими модулями наёмники, M6: хендлы :toString().
Стабы свои (без дирижёра). python -I -X utf8 build/KMM_Conductor/_dev/test_x2_levers.py -> OK."""
import ctypes, tempfile

DLL = r"C:\Program Files (x86)\Steam\steamapps\workshop\content\233860\3817000612\lua51.dll"
MOD = r"C:\KenshiModMap\build\KMM_Conductor\scripts\init\KMM_RecruitRace.lua"
TMP = tempfile.mkdtemp(prefix="kmm_x2_").replace("\\", "/") + "/"
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
    code = code.replace("TMPDIR", TMP)
    if L.luaL_loadstring(st, code.encode("utf-8")) or L.lua_pcall(st, 0, 0, 0):
        msg = L.lua_tolstring(st, -1, None)
        raise RuntimeError(f"{name}: {msg.decode('utf-8', 'replace') if msg else '?'}")


STUBS = r'''
math.randomseed(6)
EV = {}
Events = { on = function(name, fn) EV[name] = fn; return #name end }
itemType = { SQUAD_TEMPLATE = 52, AI_PACKAGE = 72, DIALOGUE_LINE = 19 }
HOURS = 1000
EVENTS = {}
CONTRACT_MODE = "line"     -- line: setContractJob работает; pkg: только _setContractJob; none: ничего; throw / throw2
SLAVE_MODE = "ok"          -- ok / noop / throw
CALLS = {}
FACS = {}
function MKFAC(id) local f = { id = id }; f.getData = function(self) return { stringID = self.id } end; FACS[id] = f; return f end
for _, id in ipairs({ "51707-rebirth.mod", "1214-gamedata.base", "1084-gamedata.base", "PF", "TOWNF" }) do MKFAC(id) end
GD = { ["5079-gamedata.base"] = { stringID = "5079-gamedata.base" }, ["5090-gamedata.base"] = { stringID = "5090-gamedata.base" } }
WORLD = {
  getTimeStamp_inGameHours = function() return { getTotalHours = function() return HOURS end } end,
  factionMgr = { getFactionByStringID = function(_, id) return FACS[id] end },
  gamedata = { getData = function(_, sid, t) CALLS.gd = (CALLS.gd or "") .. sid .. "/" .. tostring(t) .. ";"; return GD[sid] end },
}
function getGameWorld() return WORLD end
TOWN = { getName = function() return "Stack" end }
-- M6: хендл по значению — новый userdata-объект на каждый вызов; ключ только через :toString(), tostring() — адрес (как в игре)
HMT = { __index = { toString = function(self) return self.s end } }
function HND(s) if s == nil then return nil end; return setmetatable({ s = s }, HMT) end
CHARS = {}
function MKBOARD()
  local bd = { contract = nil }
  bd.hasContractJob = function(self) return self.contract ~= nil end
  bd.setContractJob = function(self, line, hand)
    CALLS.set = (CALLS.set or 0) + 1; CALLS.set_args = { line, hand }
    if CONTRACT_MODE == "throw" or CONTRACT_MODE == "throw2" then error("setContractJob boom") end
    if CONTRACT_MODE == "line" then self.contract = { giver = hand, h = 48 } end
  end
  bd._setContractJob = function(self, pkg, hours, hand)
    CALLS.set2 = (CALLS.set2 or 0) + 1; CALLS.set2_args = { pkg, hours, hand }
    if CONTRACT_MODE == "throw2" then error("_setContractJob boom") end
    if CONTRACT_MODE == "pkg" or CONTRACT_MODE == "throw" then self.contract = { giver = hand, h = hours } end
  end
  bd.getContractExpiryTime = function(self) return { getTotalHours = function() return HOURS + (self.contract and self.contract.h or 0) end } end
  return bd
end
function MKPL(key) local pl = { key = key, members = {}, board = MKBOARD() }
  pl.getBlackboard = function(self) return self.board end
  pl.getSquadLeader = function(self) return self.members[1] end
  pl.getPlatoonStringID = function(self) return self.key end
  pl.isPersistentSquad = function(self) return self.persistent == true end
  return pl
end
PLS = {}
function MKCH(o)
  local ch = { name = o.name, h = o.h, fid = o.fid, x = o.x or 0, z = o.z or 0, dead = false, skill = o.skill or 30, unique = false, player = false,
               slave = o.slave or 0, owner = o.owner, said = {}, town = (o.town ~= false) and TOWN or false, trader = o.trader or false, combat = false, down = false }
  local pl = PLS[o.pkey] or MKPL(o.pkey); PLS[o.pkey] = pl; pl.members[#pl.members + 1] = ch; ch.pl = pl
  ch.getName = function(self) return self.name end
  ch.getHandle = function(self) return HND(self.h) end
  ch.isDead = function(self) return self.dead end
  ch.isPlayerCharacter = function(self) return self.player end
  ch.isUnique = function(self) return self.unique end
  ch.isSlave = function(self) return self.slave end
  ch.getMySlaveOwner = function(self) return HND(self.owner) end
  ch.changeSlaveOwner = function(self, hand)
    CALLS.cso = (CALLS.cso or 0) + 1; CALLS.cso_args = { self.name, hand }
    if SLAVE_MODE == "throw" then error("changeSlaveOwner boom") end
    if SLAVE_MODE == "ok" then self.owner = hand:toString() end
  end
  ch.getStats = function(self) return { getOverallSkillLevel_0_100 = function() return self.skill end } end
  ch.say = function(self, s) self.said[#self.said + 1] = s end
  ch.getPosition = function(self) return { x = self.x, y = 0, z = self.z } end
  CHARS[#CHARS + 1] = ch
  return ch
end
PC = { player = true, h = "PC1", intown = true, x = 100, z = 100 }
PC.getPosition = function(self) return { x = self.x, y = 0, z = self.z } end
PC.getCurrentTownLocation = function(self) if self.intown then return TOWN end return nil end
PC.getHandle = function(self) return HND(self.h) end
PCS = { PC }
function getPlayerInterface() return { getAllPlayerCharacters = function() return PCS end } end
KMM_Gov = { run = function(name, fn, ...) return fn(...) end, snapshot = function()
  local list, by = {}, {}
  for _, ch in ipairs(CHARS) do
    local r = { ch = ch, x = ch.x, z = ch.z, fid = ch.fid, dead = ch.dead, pkey = ch.pl.key, pl = ch.pl, town = ch.town, down = ch.down,
                unique = ch.unique, h = tostring(HND(ch.h)), combat = ch.combat, trader = ch.trader }
    list[#list + 1] = r
    by[r.pkey] = by[r.pkey] or {}; table.insert(by[r.pkey], r)
  end
  return { list = list, by_pkey = by, n = #list }
end }
REMEMBERED = {}
KMM_Nemesis = { remember = function(ch, tag) REMEMBERED[#REMEMBERED + 1] = { ch = ch, tag = tag } end, _N = {} }
S = { ext = {} }
KMM_Conductor = { state = function() return S end, emit = function(ev) EVENTS[#EVENTS + 1] = ev end, day = function() return HOURS / 24 end,
  name = function(fid) if fid == "51707-rebirth.mod" then return "Drifters" elseif fid == "1084-gamedata.base" then return "Slave Traders" end return fid end,
  cfg = function() return { player_faction = "PF" } end }
N, FAILS = 0, {}
function check(c, what) N = N + 1; if not c then FAILS[#FAILS + 1] = what end end
function readlog() local f = io.open("TMPDIR" .. "recruitrace.log", "r"); if not f then return "" end; local s = f:read("*a"); f:close(); return s end
function has(s, pat) return s:find(pat, 1, true) ~= nil end
function evn(t) local n = 0; for _, e in ipairs(EVENTS) do if e.type == t then n = n + 1 end end; return n end
function lastev(t) for i = #EVENTS, 1, -1 do if EVENTS[i].type == t then return EVENTS[i] end end end
function fexists(p) local f = io.open("TMPDIR" .. p, "r"); if f then f:close(); return true end; return false end
'''
run(STUBS, "stubs")
run(open(MOD, encoding="utf-8").read(), "KMM_RecruitRace.lua")
run(r'''
local M = KMM_RecruitRace
local P, Q = M.P, M.Q
P.log = "TMPDIR" .. "recruitrace.log"; P.sdir = "TMPDIR"
P.start_s, P.tick_s, P.pick_s, P.house_s, Q.pick_s = 0, 0, 0, 0, 0
local tick = function() M.last = nil; M.rt.pick = nil; M.rt.house = nil; M.rt.x2 = nil; EV["GameWorld::charsUpdate"]() end
local function reset() M._reset(); S = { ext = {} }; CALLS = {}; EVENTS = {} end

-- ===== merc =====
local rl = MKCH({ name = "Rakor", h = "HL", fid = "51707-rebirth.mod", pkey = "RIV", x = 900, z = 100 })
MKCH({ name = "Rakor2", h = "HL2", fid = "51707-rebirth.mod", pkey = "RIV", x = 910, z = 100 })
local mg = MKCH({ name = "Merc1", h = "HM", fid = "1214-gamedata.base", pkey = "MERC", x = 1500, z = 300 })
local far = MKCH({ name = "FarMerc", h = "HF", fid = "1214-gamedata.base", pkey = "MERCFAR", x = 60000, z = 300 })
tick()
local R = S.ext.recruitrace
local log = readlog()
check(CALLS.set == 1 and CALLS.set_args[1].stringID == "5079-gamedata.base" and CALLS.set_args[2]:toString() == "HL", "setContractJob(line 5079, leader hand)")
check(has(CALLS.gd or "", "5079-gamedata.base/19"), "line read as DIALOGUE_LINE")
check(PLS.MERC.board.contract and not PLS.MERCFAR.board.contract, "nearby guild squad got the contract, far one not")
check(has(log, "merc hired Rakor (51707-rebirth.mod) <- guild squad MERC via setContractJob, contract 48 h"), "marker merc hired")
local e = lastev("recruit_merc_hired")
check(e and e.a == "51707-rebirth.mod" and e.b == "1214-gamedata.base" and e.leader_name == "Rakor" and e.town_name == "Stack" and has(e.text, "Drifters"), "recruit_merc_hired event")
check(#rl.said == 1 and rl.said[1] == M.SAY_MERC, "rival leader says line")
check(R.merc.act and R.merc.act.mk == "MERC" and R.merc.next_h == HOURS + Q.week_h, "watch record + weekly limit")
for k, v in pairs(R.merc.act) do check(type(v) ~= "userdata" and type(v) ~= "table", "act holds only strings/numbers: " .. k) end
-- ещё такт: контракт идёт, нового найма нет
local mg2 = MKCH({ name = "Merc2", h = "HM2", fid = "1214-gamedata.base", pkey = "MERC2", x = 1200, z = 200 })
tick(); check(CALLS.set == 1 and evn("recruit_merc_left") == 0, "no second hire while contract active")
-- контракт кончился -> recruit_merc_left
PLS.MERC.board.contract = nil; HOURS = HOURS + 50; tick()
check(evn("recruit_merc_left") == 1 and has(readlog(), "merc contract ended Rakor") and R.merc.act == nil, "contract ended -> merc_left")
check(lastev("recruit_merc_left").leader_name == "Rakor", "merc_left names the leader")
tick(); check(CALLS.set == 1, "weekly limit holds after contract end")
HOURS = R.merc.next_h + 1; PLS.MERC.board.contract = { h = 10 }; tick()   -- игрок нанял MERC сам: занят
check(CALLS.set == 2 and PLS.MERC2.board.contract ~= nil, "busy guild squad skipped, free one hired after a week")
-- watch: отряд выгружен -> снят после t_end + grace
for i, ch in ipairs(CHARS) do if ch == mg2 then table.remove(CHARS, i) end end
HOURS = R.merc.act.t_end + Q.grace_h + 1; tick()
check(R.merc.act == nil and has(readlog(), "merc watch dropped Rakor"), "watch dropped when guild squad unloaded")
for i, ch in ipairs(CHARS) do if ch == far then table.remove(CHARS, i) end end
-- фолбэк _setContractJob
reset(); PLS.MERC.board.contract = nil; CONTRACT_MODE = "pkg"; tick(); R = S.ext.recruitrace
check(CALLS.set == 1 and CALLS.set2 == 1 and CALLS.set2_args[1].stringID == "5090-gamedata.base" and CALLS.set2_args[2] == 48 and CALLS.set2_args[3]:toString() == "HL", "fallback _setContractJob(Bodyguard, 48, hand)")
check(has(readlog(), "via _setContractJob") and R.merc.act, "hired via fallback")
-- ни одна ветка не дала контракта -> рычаг до перезапуска, модуль жив
reset(); PLS.MERC.board.contract = nil; CONTRACT_MODE = "none"; tick(); R = S.ext.recruitrace
check(has(readlog(), "contract FAIL Rakor") and M.X.off.merc and not M.off and not fexists("recruitrace_merc.off"), "unconfirmed contract: lever off until restart, module alive")
tick(); check(CALLS.set == 1, "disabled lever does not retry")
-- вызов setContractJob упал -> ветка выключена навсегда, фолбэк работает
reset(); CONTRACT_MODE = "throw"; tick()
check(fexists("probe_rr_contract.off") and PLS.MERC.board.contract and not M.X.off.merc, "setContractJob error: branch off, fallback hired")
reset(); PLS.MERC.board.contract = nil; tick()
check(CALLS.set == nil and CALLS.set2 == 1, "dead branch skipped next session")
-- обе ветки упали -> рычаг навсегда
os.remove("TMPDIR" .. "probe_rr_contract.off")
reset(); PLS.MERC.board.contract = nil; CONTRACT_MODE = "throw2"; tick()
check(fexists("recruitrace_merc.off") and M.X.off.merc, "both calls failed: lever off forever")
reset(); tick(); check(M.X.off.merc and CALLS.set == nil, "off file keeps lever off")
os.remove("TMPDIR" .. "recruitrace_merc.off"); os.remove("TMPDIR" .. "probe_rr_contract.off"); os.remove("TMPDIR" .. "probe_rr_contract2.off")
CONTRACT_MODE = "line"
-- конкурент далеко -> ничего
reset(); PLS.MERC.board.contract = nil; rl.x = 90000; PLS.RIV.members[2].x = 90000; tick()
check(CALLS.set == nil and evn("recruit_merc_hired") == 0, "rival far from player: no hire")
-- M1: наёмники, которых ведут наши модули, и наёмники вне города не нанимаются
rl.x = 900; PLS.RIV.members[2].x = 910
local function m1(setup, undo, what)
  reset(); PLS.MERC.board.contract = nil; setup(); tick()
  check(CALLS.set == nil and evn("recruit_merc_hired") == 0, what)
  undo()
end
m1(function() PLS.MERC.persistent = true end, function() PLS.MERC.persistent = nil end, "persistent guild squad (V1/S3/NAT) skipped")
m1(function() KMM_Traces = { native = function() return {}, { { k = "MERC" } }, {}, 0, {} end } end, function() KMM_Traces = nil end, "Traces NAT registry squad skipped")
m1(function() KMM_Traces = { native = function() return {}, {}, {}, 0, { { k = "MERC" } } end } end, function() KMM_Traces = nil end, "Traces temporary native squad skipped")
m1(function() KMM_Outlaws = { state = function() return { L = { o1 = { pk = "MERC", n = "x" } }, orph = {} } end } end, function() KMM_Outlaws = nil end, "Outlaws persistent key skipped")
m1(function() KMM_Outlaws = { state = function() return { L = { o1 = { n = "Merc1" } } } end } end, function() KMM_Outlaws = nil end, "Outlaws named leader skipped")
m1(function() KMM_Nemesis.hunters = function() return { f = { n = "Merc1" } } end end, function() KMM_Nemesis.hunters = nil end, "Nemesis hunter leader skipped")
m1(function() S.ext.recruitrace = { taken = { { pk = "MERC" } }, orph = {} } end, function() end, "own V1 recruit squad skipped")
m1(function() mg.town = false end, function() mg.town = TOWN end, "guild squad outside a town skipped")
reset(); PLS.MERC.board.contract = nil; KMM_Traces = { native = function() return {}, { { k = "OTHER" } }, {}, 0, {} end }; tick(); KMM_Traces = nil
check(CALLS.set == 1 and PLS.MERC.board.contract, "free guild squad still hired with registries present")
-- merc выключаем для слейв-части
CHARS = {}; PLS = {}

-- ===== slave =====
reset()
local keeper = MKCH({ name = "Keeper", h = "HK", fid = "1084-gamedata.base", pkey = "SHOP", x = 150, z = 150, trader = true })
local sa = MKCH({ name = "Ayo", h = "HSA", fid = "TOWNF", pkey = "CAGE", x = 160, z = 160, slave = 1, owner = "HK", skill = 30 })
local sb = MKCH({ name = "Beep", h = "HSB", fid = "TOWNF", pkey = "CAGE", x = 170, z = 160, slave = 1, owner = "HK", skill = 60 })
MKCH({ name = "Mine", h = "HSC", fid = "TOWNF", pkey = "CAGE", x = 170, z = 170, slave = 1, owner = "PC1", skill = 90 })
MKCH({ name = "Lost", h = "HSD", fid = "TOWNF", pkey = "CAGE", x = 175, z = 170, slave = 1, owner = "NOBODY", skill = 99 })
MKCH({ name = "Free", h = "HSE", fid = "TOWNF", pkey = "CAGE", x = 175, z = 175, slave = 0, owner = "HK", skill = 98 })
local bl = MKCH({ name = "Grat", h = "HB", fid = "1084-gamedata.base", pkey = "BUY", x = 2000, z = 300 })
-- H5: по умолчанию только слух, хозяин не меняется
check(Q.slave_owner == false, "slave_owner off by default")
tick(); R = S.ext.recruitrace
check(CALLS.cso == nil and sb.owner == "HK" and M.rt.spend == nil, "default: no changeSlaveOwner, slave stays with the shop")
e = lastev("recruit_slave_eyed")
check(e and e.a == "1084-gamedata.base" and e.leader_name == "Beep" and e.town_name == "Stack" and has(e.text, "Slave Traders"), "recruit_slave_eyed rumor")
check(has(readlog(), "slave rumor Beep (skill 60): Grat of 1084-gamedata.base eyes the cages of Stack") and evn("recruit_slave_bought") == 0, "rumor marker, no bought event")
check(#R.slave.bought == 0 and R.slave.next_h == HOURS + Q.week_h, "rumor: weekly limit, nothing recorded")
tick(); check(evn("recruit_slave_eyed") == 1, "one rumor per week")
Q.slave_owner = true
reset()
tick(); R = S.ext.recruitrace
check(CALLS.cso == 1 and CALLS.cso_args[1] == "Beep" and CALLS.cso_args[2]:toString() == "HB", "changeSlaveOwner(strongest shop slave, buyer leader hand)")
check(M.rt.spend and has(readlog(), "changeSlaveOwner called Beep (skill 60) -> Grat"), "pending confirmation")
for k, v in pairs(M.rt.spend) do check(type(v) ~= "userdata" and type(v) ~= "table", "pending holds only strings/numbers: " .. k) end
check(evn("recruit_slave_bought") == 0, "no rumor before confirmation")
for i = 1, Q.confirm_n do tick() end
log = readlog()
check(has(log, "changeSlaveOwner ok Beep -> Grat") and has(log, "slave bought Beep (skill 60) by 1084-gamedata.base at Stack"), "markers ok + bought")
e = lastev("recruit_slave_bought")
check(e and e.a == "1084-gamedata.base" and e.b == "1084-gamedata.base" and e.leader_name == "Beep" and has(e.text, "Slave Traders"), "recruit_slave_bought event")
check(sb.said[#sb.said] == M.SAY_SOLD, "slave says sold line")
check(#R.slave.bought == 1 and R.slave.bought[1].h == "HSB" and R.slave.next_h == HOURS + Q.week_h and M.rt.spend == nil, "bought record + weekly limit")
tick(); check(CALLS.cso == 1, "no second purchase within a week")
-- освобождение: без взлома игрока не считается даже рядом (M3: фолбэк по дистанции убран)
sb.x = 120; EV["Character::setChainedMode"](sb, false)
check(#R.slave.bought == 1 and evn("recruit_slave_freed") == 0, "unchained near player without lockpick: not freed by player")
EV["Character::setChainedMode"](sb, true); check(#R.slave.bought == 1, "chaining ignored")
-- взлом игрока (Nemesis lock_t) засчитывается и издалека; память LT_FREED_ME пишет только Nemesis (здесь не дублируется)
sb.x = 9000
KMM_Nemesis._N.lock_t = os.clock(); EV["Character::setChainedMode"](sb, false); KMM_Nemesis._N.lock_t = nil
check(#REMEMBERED == 0, "M3: no LT_FREED_ME from RecruitRace (Nemesis debt owns it)")
check(evn("recruit_slave_freed") == 1 and lastev("recruit_slave_freed").leader_name == "Beep" and #R.slave.bought == 0, "recruit_slave_freed + record removed")
check(has(readlog(), "slave freed by player Beep"), "marker freed")
sb.x = 170
-- клетка вернула хозяина -> рычаг до перезапуска
reset(); sb.owner = "HK"; R = nil; tick(); R = S.ext.recruitrace
check(CALLS.cso == 1 and M.rt.spend, "second world: purchase pending")
sb.owner = "HK"; tick()
check(has(readlog(), "changeSlaveOwner FAIL Beep: owner reverted to HK") and M.X.off.slave and not fexists("recruitrace_slave.off") and evn("recruit_slave_bought") == 0, "owner reverted: lever off until restart")
-- вызов прошёл, хозяин не сменился
reset(); SLAVE_MODE = "noop"; tick()
check(has(readlog(), "changeSlaveOwner FAIL Beep -> 1084-gamedata.base: owner is HK") and M.X.off.slave and M.rt.spend == nil, "owner not changed: FAIL")
-- вызов упал -> навсегда
reset(); SLAVE_MODE = "throw"; tick()
check(has(readlog(), "call failed") and fexists("recruitrace_slave.off") and not M.off, "changeSlaveOwner error: lever off forever, module alive")
reset(); tick(); check(CALLS.cso == nil and M.X.off.slave, "off file keeps slave lever off")
os.remove("TMPDIR" .. "recruitrace_slave.off"); SLAVE_MODE = "ok"
-- игрок не в городе -> ничего; нет покупателя -> ничего
reset(); sb.owner = "HK"; PC.intown = false; tick(); check(CALLS.cso == nil, "player outside town: no purchase")
PC.intown = true; bl.fid = "TOWNF"; tick(); check(CALLS.cso == nil, "no slaver buyer: no purchase")
bl.fid = "1084-gamedata.base"
-- хозяин не загружен/не торговец -> диагностика один раз
reset(); keeper.trader = false; keeper.fid = "TOWNF"; tick()
check(CALLS.cso == nil and has(readlog(), "slave scan: 4 slaves near"), "slave scan diagnostic when no shop owner matched")
keeper.trader = true; keeper.fid = "1084-gamedata.base"
-- смена мира посреди подтверждения -> ожидание сброшено
reset(); sb.owner = "HK"; tick(); check(M.rt.spend ~= nil, "pending before world change")
S = { ext = {} }; tick(); check(M.rt.spend == nil or M.rt.spend.h == "HSB" and M.rt.spend.tries == 0, "world change drops pending runtime")
''', "test")
run(r'''
if #FAILS > 0 then error("FAIL " .. #FAILS .. "/" .. N .. ":\n  " .. table.concat(FAILS, "\n  ")) end
print("checks " .. N)
''', "result")
print("OK test_x2_levers")
