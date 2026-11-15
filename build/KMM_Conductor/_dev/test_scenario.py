"""Offline test KMM_Scenario (Z1): без state/scenario.txt — ноль вызовов движка и модулей; с файлом — каждый сценарий (probe, bar, rival,
hunter, famine, raid) выполняет свои шаги один раз за мир (метка S.ext.scenario), повторная загрузка не повторяет; ошибки шагов
пишутся FAIL и не роняют модуль. Заглушки свои (считают каждый вызов). python -I -X utf8 build/KMM_Conductor/_dev/test_scenario.py -> OK."""
import ctypes, os, shutil, sys, tempfile

DLL = r"C:\Program Files (x86)\Steam\steamapps\workshop\content\233860\3817000612\lua51.dll"
MOD = r"C:\KenshiModMap\build\KMM_Conductor\scripts\init\KMM_Scenario.lua"
FAILS = []

STUBS = r'''
math.randomseed(20261115)
CALLS = 0
function F(fn) return function(...) CALLS = CALLS + 1; return fn(...) end end
NOW = 0
os.clock = function() return NOW end
EV = {}
Events = { on = function(name, fn) EV[name] = fn; return 1 end }
HOURS = 100
POS = { x = 1000, y = 50, z = 2000 }
MONEY = 500
TW = {}
TW.getName = F(function() return "Squin" end)
TW.getPositionOutsideTownGates = F(function(_, d) return { x = 50000 + d, y = 10, z = 60000 } end)
TW.getPosition = F(function() return { x = 50000, y = 10, z = 60000 } end)
TOWN_HERE = nil
AP = { teleport = F(function(_, p) TELE = p; POS = { x = p.x, y = p.y, z = p.z }; TOWN_HERE = TW end) }
OWN = { getMoney = F(function() return MONEY end), addMoney = F(function(_, n) MONEY = MONEY + n end) }
PC = { getPosition = F(function() return POS end), getCurrentTownLocation = F(function() return TOWN_HERE end),
       getPlatoon = F(function() return AP end), getOwnerships = F(function() return OWN end) }
function getPlayerInterface() CALLS = CALLS + 1; return { getAllPlayerCharacters = function() return { PC } end } end
FAC = { warMgr = { getNearestTown = F(function() return TW end) } }
function getGameWorld() CALLS = CALLS + 1
  return { factionMgr = { getFactionByStringID = F(function() return FAC end) },
           getTimeStamp_inGameHours = function() return { getTotalHours = function() return HOURS end, getTotalDays = function() return HOURS / 24 end } end }
end
-- дирижёр
S = { F = { A = { alive = true }, B = { alive = true }, PF = { alive = true, player = true }, R = { alive = true, relic = true } }, ext = {} }
CS = { steps = 3, off = false, ys = { probed = false, calls = 0, mcalls = 0, eff = 0 } }
CA = { OFF = false, PROBE = {}, CPv = { p_raid = 0.15, max_forces = 30 } }
CA.CP = F(function() return CA.CPv end)
CA.data = F(function() return { factions = { A = { raid = { "c1" } } } } end)
CA.pick = F(function(f) return (f == "A") and "c1" or nil end)
CA.limits_ok = F(function() return true end)
CA.try = F(function(fid, o, a, t)
  if CA_ERR then error("try boom") end
  TRY = { fid, o, a, t, CA.CPv.p_raid }; CA.PROBE["triggerCampaign"] = true; CA.PROBE["triggerCampaign#done"] = true; return CA.CPv.p_raid == 1 end)
KMM_Conductor = {
  state = F(function() return S end),
  cfg = F(function() return { player_faction = "PF" } end),
  towns = F(function() return {
    { sid = "T1", name = "Squin", kind = "city", x = 50000, z = 60000, owner = "B" },
    { sid = "T2", name = "Farm", kind = "holding", x = 1500, z = 2000, owner = "B" },
    { sid = "T3", name = "Near Camp", kind = "city", x = 3000, z = 2500, owner = "B" } } end),
  rel = F(function(a, b) return a == "A" and -50 or 0 end),
  fpos = F(function() return 5000, 5000 end),
  coresync = F(function() return CS end),
  coresync_test = F(function() CS.steps = CS.steps + 1 end),
  camp = F(function() return CA end),
  disabled = F(function() return {} end),
  _act = F(function(fid, a, o) ACT = { fid, a, o }; if a == "raid_base" then S.bcamp = { fid = fid } end end),
}
TGMP = 0
TGM = { done = false, ok = false, tries = 0 }
TGM.probe = F(function(pl, ch)
  if TGM_ERR then error("tgm boom") end
  TGMP = TGMP + 1; TGM.done, TGM.ok = true, true; return true, "src=char_here town Squin: entries=3" end)
KMM_Traces = { tgm = TGM, stats = F(function() return { spawned = 2 } end), disabled = F(function() return {} end) }
KMM_Tempo = { _restock = { reads = 1, armed = false, errs = 0, pl = { a = {} } }, _disabled = {} }
KMM_RelicRace = { off = false, rt = { loot = { n = 0, probe = { ["take#ok"] = true } } }, stats = { launched = 1 } }
RRR = {}
REC = { name = "Bob" }
KMM_RecruitRace = { off = false, X = { off = {} }, stats = { races = 0 } }
KMM_RecruitRace.st = F(function(c) return RRR, S end)
KMM_RecruitRace.pick = F(function(snap, px, pz, pf) if TOWN_HERE then return REC, 40 end end)
KMM_RecruitRace.start = F(function(c, R, rec, sk, h) R.race = { name = rec.name, town = "Squin", fid = "D", t1 = h + 40 } end)
KMM_Gov = { snapshot = F(function() return { list = {} } end) }
-- разыскиваемые и соперники
OO = { L = { o1 = { i = 1, n = "Grim", st = "a", t = 1, b = 4000, g = "G1", x = 90000, z = 90000 },
             o2 = { i = 2, n = "Ska", st = "a", t = 2, b = 9000, g = "G2", x = 80000, z = 80000 } }, hunt = {} }
OD = { regions = { R1 = { towns = { { sid = "T9", name = "Stack", fid = "B", x = 60000, z = 60000 } } } } }
OX = { pend = nil, stats = { patrol = 0 } }
OX.list = function(O) local out = {}; for _, o in pairs(O.L) do out[#out + 1] = o end; table.sort(out, function(a, b) return a.i < b.i end); return out end
OX.cfg = function() return { vis_r = 22000 } end
OX.today = function() return 4 end
OX.data = function() return OD end
OX.O = function() return OO end
OX.manhunt = F(function(C, O, D, cfg, t, o, day) O.hunt[t.sid] = { u = day + 5, lf = "LAW", x = t.x, z = t.z, tn = t.name, oi = o.i } end)
LIVE = {}
TICKS = 0
KMM_Outlaws = { _M = OX, live = F(function() return LIVE end), disabled = F(function() return {} end) }
KMM_Outlaws._tick = F(function()
  TICKS = TICKS + 1
  for id, o in pairs(OO.L) do
    if o.st == "a" and o.x and math.sqrt((o.x - POS.x) ^ 2 + (o.z - POS.z) ^ 2) < 5000 and not LIVE[id] then LIVE[id] = { pl = {} } end
  end
  for _, h in pairs(OO.hunt) do if not h.sp then h.sp = true; OX.stats.patrol = OX.stats.patrol + 1; HUNT_SPAWN = h end end
end)
NM = { outlaws = F(function() return OX, OO, OD end) }
NM.make = F(function(X, O, D, C, S_, c, deed) local o = { i = 3, n = c.n .. " the Runner", st = "a", t = 1, b = 100, g = "G1", pg = { deed = deed } }; O.L.o3 = o; MADE = c; return o end)
KMM_Nemesis = { _N = NM, disabled = F(function() return {} end) }
-- склад
SHELF = { T3 = { food = 40 } }
KMM_Stock = { ready = F(function() return true end), town_of = F(function() return nil end), disabled = F(function() return {} end),
  stats = F(function() return { days = 2 } end) }
KMM_Stock.stock = F(function(sid) local q = SHELF[sid]; return q and { q = { food = q.food }, T = 50 } end)
KMM_Stock.take = F(function(sid, cat, n) local q = SHELF[sid]; local x = math.min(q[cat], n); q[cat] = q[cat] - x; TAKEN = (TAKEN or 0) + x; return x end)
KMM_Stock.level = F(function(sid, cat) return SHELF[sid] and SHELF[sid][cat] / 50 end)

function ticks(n) for _ = 1, n do NOW = NOW + 1; HOURS = HOURS + 0.02; EV["GameWorld::charsUpdate"]() end end
function readlog() local f = io.open(LOGP, "r"); if not f then return nil end; local s = f:read("*a"); f:close(); return s end
function has(s, p) return s ~= nil and s:find(p, 1, true) ~= nil end
function count(s, p) local n, i = 0, 1; while s do local a, b = s:find(p, i, true); if not a then break end; n = n + 1; i = b + 1 end; return n end
CHECKS, BAD = 0, {}
function check(c, what) CHECKS = CHECKS + 1; if not c then BAD[#BAD + 1] = what end end
'''


class Lua:
    def __init__(self):
        self.L = ctypes.CDLL(DLL)
        L = self.L
        L.luaL_newstate.restype = ctypes.c_void_p
        for fn, at in [("luaL_openlibs", [ctypes.c_void_p]), ("luaL_loadstring", [ctypes.c_void_p, ctypes.c_char_p]),
                       ("lua_pcall", [ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int]),
                       ("lua_getfield", [ctypes.c_void_p, ctypes.c_int, ctypes.c_char_p]),
                       ("lua_settop", [ctypes.c_void_p, ctypes.c_int]), ("lua_close", [ctypes.c_void_p])]:
            getattr(L, fn).argtypes = at
        L.lua_tolstring.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p]
        L.lua_tolstring.restype = ctypes.c_char_p
        self.st = L.luaL_newstate()
        L.luaL_openlibs(self.st)

    def run(self, code, name="chunk"):
        if self.L.luaL_loadstring(self.st, code.encode("utf-8")) or self.L.lua_pcall(self.st, 0, 0, 0):
            msg = self.L.lua_tolstring(self.st, -1, None)
            raise RuntimeError(f"{name}: {msg.decode('utf-8', 'replace') if msg else '?'}")

    def get(self, name):
        self.L.lua_getfield(self.st, -10002, name.encode())
        v = self.L.lua_tolstring(self.st, -1, None)
        self.L.lua_settop(self.st, -2)
        return v.decode("utf-8", "replace") if v else None

    def close(self):
        self.L.lua_close(self.st)


SRC = open(MOD, encoding="utf-8").read()


def case(title, scen, setup, body, ticks=420):
    tmp = tempfile.mkdtemp(prefix="kmm_scen_").replace("\\", "/") + "/"
    os.makedirs(tmp + "state"), os.makedirs(tmp + "logs")
    if scen is not None:
        with open(tmp + "state/scenario.txt", "w", encoding="utf-8") as f:
            f.write(scen + "\r\n")
    lua = Lua()
    try:
        lua.run(STUBS, "stubs")
        lua.run(f'LOGP = "{tmp}logs/scenario.log"', "logp")
        lua.run(setup, title + ":setup")
        lua.run("CALLS0 = CALLS", "c0")
        lua.run(SRC.replace("C:/KenshiModMap/", tmp), "KMM_Scenario.lua")
        lua.run(f"ticks({ticks})", title + ":ticks")
        lua.run(body, title + ":checks")
        n, bad = lua.get("CHECKS_S"), lua.get("BAD_S")
        if bad:
            FAILS.append(f"{title}: {bad}")
        print(f"{title}: {n} checks{' FAIL ' + bad if bad else ' ok'}")
    except Exception as e:
        FAILS.append(f"{title}: {e}")
        print(f"{title}: ERROR {e}")
    finally:
        lua.close()
        shutil.rmtree(tmp, ignore_errors=True)


FIN = "\nCHECKS_S = tostring(CHECKS); BAD_S = (#BAD > 0) and table.concat(BAD, '; ') or nil\n"

# 1. нет файла: ноль вызовов движка/модулей, лога нет, модуль выключен
case("nofile", None, "", r'''
check(CALLS == CALLS0, "calls without scenario file: " .. (CALLS - CALLS0))
check(readlog() == nil, "log written without scenario file")
check(KMM_Scenario.off == true, "module not idle")
''' + FIN, ticks=600)

# 2. неизвестное имя: тоже инертен
case("unknown", "foo", "", r'''
check(CALLS == CALLS0, "calls with unknown scenario")
check(has(readlog(), "unknown scenario 'foo'"), "no unknown line")
check(KMM_Scenario.off == true, "module not idle")
''' + FIN, ticks=200)

# 3. probe: все шаги, один раз; повторная загрузка мира не повторяет
case("probe", "probe", "TOWN_HERE = TW", r'''
local s = readlog()
check(has(s, "scenario probe start: 10 steps"), "no start")
for _, k in ipairs({ "modules", "coresync", "restock", "prosperity", "ruinloot", "tgm", "recruit", "campaign", "restock_later", "modules_later" }) do
  check(count(s, "ok probe." .. k .. ":") == 1, "step " .. k .. " not ok once")
end
check(has(s, "scenario probe done: ok=10 fail=0 skip=0"), "no done line")
check(has(s, "module KMM_Conductor: alive"), "no module line")
check(has(s, "module KMM_Native: absent"), "absent module not reported")
check(TGMP == 1, "tgm probe calls " .. TGMP)
check(TRY and TRY[1] == "A" and TRY[2] == "B" and TRY[3] == "raid" and TRY[4] == "T2" and TRY[5] == 1, "campaign try args")
check(CA.CPv.p_raid == 0.15, "p_raid not restored")
check(RRR.race and math.abs(RRR.race.t1 - (HOURS - 0)) < 10 and RRR.race.t1 < 101, "recruit race not made immediate")
check(S.ext.scenario and S.ext.scenario.done.probe, "no world mark")
check(MONEY == 500, "probe touched money")
-- новая сессия, тот же мир: шаги не повторяются
local c0, t0 = CALLS, TGMP
KMM_Scenario._reset(); NOW = NOW + 1000
ticks(300)
local s2 = readlog()
check(has(s2, "scenario probe already ran in this world"), "no already line")
check(count(s2, "scenario probe start") == 1, "probe started twice")
check(TGMP == t0, "tgm probed again")
''' + FIN)

# 4. probe с ошибками: шаг FAIL/skip, модуль жив, остальные шаги идут
case("probe_errors", "probe", "TOWN_HERE = TW; TGM_ERR = true; CA_ERR = true; KMM_Tempo = nil; KMM_RecruitRace.pick = function() error('pick boom') end", r'''
local s = readlog()
check(has(s, "FAIL probe.tgm: TGM probe error"), "tgm error not logged")
check(has(s, "FAIL probe.campaign: CA.try error"), "campaign error not logged")
check(has(s, "FAIL probe.recruit: error"), "recruit error not logged")
check(has(s, "skip probe.restock:"), "restock not skipped")
check(has(s, "ok probe.coresync:"), "coresync not run after errors")
check(has(s, "scenario probe done:"), "not done")
check(KMM_Scenario.off == false, "module died on step errors")
check(CA.CPv.p_raid == 0.15, "p_raid not restored after error")
''' + FIN)

# 5. bar: деньги до bar_money, перенос к воротам, гонка с коротким сроком
case("bar", "bar", "", r'''
local s = readlog()
check(MONEY == 6000, "money " .. MONEY)
check(TELE and TELE.x == 50300, "no teleport to gates")
for _, k in ipairs({ "money", "teleport", "arrive", "race" }) do check(count(s, "ok bar." .. k .. ":") == 1, "bar step " .. k) end
check(RRR.race and RRR.race.t1 <= RRR.race.t1 and has(s, "taken in 6.0 game h"), "race not shortened")
check(has(s, "scenario bar done: ok=4 fail=0"), "bar not done")
''' + FIN)

# 6. rival: соперник через KMM_Nemesis + банда разыскиваемого у игрока
case("rival", "rival", "", r'''
local s = readlog()
check(MADE and MADE.n == "Varn" and MADE.lead, "nemesis make not called")
check(LIVE.o3 ~= nil, "rival not spawned")
check(LIVE.o2 ~= nil, "outlaw gang (highest bounty) not spawned")
check(LIVE.o1 == nil, "wrong outlaw moved")
for _, k in ipairs({ "rival", "rival_spawn", "outlaw", "outlaw_spawn" }) do check(count(s, "ok rival." .. k .. ":") == 1, "rival step " .. k) end
local d = math.sqrt((OO.L.o3.x - 1000) ^ 2 + (OO.L.o3.z - 2000) ^ 2)
check(d >= 1800 and d <= 2600, "rival distance " .. d)
''' + FIN)

# 7. hunter: разыскиваемый у игрока + облава с выходом рядом
case("hunter", "hunter", "", r'''
local s = readlog()
check(LIVE.o2 ~= nil, "hunted gang not spawned")
local h = OO.hunt.T9
check(h and h.oi == 2, "manhunt not against hunted")
check(h and math.sqrt((h.x - 1000) ^ 2 + (h.z - 2000) ^ 2) <= 2600, "patrol start not near player")
check(OX.stats.patrol == 1, "patrol count " .. OX.stats.patrol)
for _, k in ipairs({ "wanted", "wanted_spawn", "manhunt", "patrol" }) do check(count(s, "ok hunter." .. k .. ":") == 1, "hunter step " .. k) end
''' + FIN)

# 8. famine: полка еды ближайшего города - в ноль, второй проход
case("famine", "famine", "", r'''
local s = readlog()
check(SHELF.T3.food == 0, "shelf not emptied")
check(TAKEN == 40, "taken " .. tostring(TAKEN))
check(count(s, "ok famine.shelf:") == 1 and count(s, "ok famine.shelf_again:") == 1, "famine steps")
check(has(s, "nearest town Near Camp"), "town choice")
''' + FIN)

# 9. raid: база есть -> raid_base дирижёра (враждебная фракция с кампанией)
case("raid", "raid", "S.base = { known = true, x = 1000, z = 2000 }", r'''
local s = readlog()
check(ACT and ACT[1] == "A" and ACT[2] == "raid_base", "raid_base not acted")
check(has(s, "ok raid.raid:") and has(s, "native campaign fired"), "raid line")
''' + FIN)

# 10. raid без базы: ожидание, затем FAIL по таймауту «нет базы», без действия
case("raid_nobase", "raid", "", r'''
local s = readlog()
check(ACT == nil, "acted without base")
check(has(s, "FAIL raid.raid: timeout") and has(s, "нет базы"), "no timeout line")
check(KMM_Scenario.off == false, "module died")
''' + FIN, ticks=1900)

if FAILS:
    print("FAIL")
    for f in FAILS:
        print("  " + f)
    sys.exit(1)
print("OK")
