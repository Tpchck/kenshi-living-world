"""S6 offline test KMM_Fates: deeds bus -> hero bounty (KMM_Outlaws add_bounty/lawful), native unfairAddToBounty on live leader
(spawn + live deed), fate_deed on the bus (rumor), dedup/caps/lawless/by_player, decay, justice, core hostility/alive with fallback,
repeat meeting -> KMM_Nemesis remember. python -I -X utf8 build/KMM_Conductor/_dev/test_s6_fates_links.py -> OK."""
import ctypes, re, sys, tempfile

DLL = r"C:\Program Files (x86)\Steam\steamapps\workshop\content\233860\3817000612\lua51.dll"
B = r"C:\KenshiModMap\build\KMM_Conductor\scripts\init"
TMP = tempfile.mkdtemp(prefix="kmm_s6_").replace("\\", "/")
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
run("math.randomseed(20261116)", "seed")
for _f in sorted(__import__("glob").glob(B + r"\KMM_Conductor*.lua")): run(open(_f, encoding="utf-8").read(), _f.split("\\")[-1])
run(open(B + r"\KMM_Traces.lua", encoding="utf-8").read(), "KMM_Traces.lua")
run(open(B + r"\KMM_Fates.lua", encoding="utf-8").read(), "KMM_Fates.lua")
run(open(B + r"\KMM_Outlaws.lua", encoding="utf-8").read(), "KMM_Outlaws.lua")
run(r'''
N, FAILS = 0, {}
function check(c, what) N = N + 1; if not c then FAILS[#FAILS + 1] = what end end
local C = KMM_Conductor
C.reset()
local TP = C.cfg().params.traces
TP.first_hour_traces = 0; TP.max_per_day = 1000; TP.max_queue = 1000; TP.arrive_enabled = false
TP.bounty = { enabled = false }
local pf = C.cfg().player_faction or "player"
C.cfg().params.outlaws = { enabled = false, sdir = "TMPDIR/" }
C.cfg().params.fates = { watch_s = 1e9 }
local F, T, OM = KMM_Fates, KMM_Traces, KMM_Outlaws._M
local M = F._M
LOGS = {}
M.log = function(m) LOGS[#LOGS + 1] = tostring(m) end
local function logged(s) for _, l in ipairs(LOGS) do if l:find(s, 1, true) then return true end end; return false end
REM = {}
KMM_Nemesis = { remember = function(leader, tag) REM[#REM + 1] = { leader, tag } end }   -- публичный экспорт (фолбэк на _N убран, W1)
REL = nil
MADE = {}
local old = getGameWorld
getGameWorld = function()
  local w = old()
  local orig = w.theFactory.createRandomSquad
  w.theFactory.createRandomSquad = function(self, f, pos, ...)
    local r = orig(self, f, pos, ...)
    local leader = { name = "Nameless Raider", dead = false, bty = {} }
    leader.crimes = { unfairAddToBounty = function(self2, fo, amt) leader.bty[#leader.bty + 1] = { fo, amt } end,
                      getTotalBounty = function(self2) local s = 0; for _, b in ipairs(leader.bty) do s = s + b[2] end; return s end,
                      getBountyRecognitionThreshold = function() return 500 end }
    function leader:setName(n) self.name = n end
    function leader:getName() return self.name end
    function leader:isDead() return self.dead end
    local pl = { isDead = false }
    function pl:getSquadLeader() return leader end
    function pl:getActivePlatoon() return { setName = function() end } end
    MADE[#MADE + 1] = { pl = pl, leader = leader, fid = f.id }
    return pl
  end
  w.factionMgr = w.factionMgr or {}
  w.factionMgr.getFactionByStringID = function(self, sid)
    return { id = sid, relations = { getFactionRelation = function(s2, other) if REL == nil then error("no core") end; return REL end } }
  end
  return w
end
PCS = {}; CHARS = {}
local pc = MKCH("PC1", pf, 0, 0, { player = true, platoon = "player_squad" })
PCS[1] = pc; CHARS[1] = pc
local function tick(day) DAYV = day; CLOCK = CLOCK + 100; FIRE("GameWorld::charsUpdate", {}) end
FEV = {}
C.subscribe("fate_*", function(ev) FEV[#FEV + 1] = ev end)
tick(500)
check(F.state() ~= nil, "fates seeded")
local W = M.world(C, C.state(), F.state().day)
-- герой с городом; жертва — фракция с законом, беззаконная — без
local hero; for _, h in ipairs(F.heroes()) do if h.st == "a" and h.s and h.r ~= "bandit_chief" then hero = h; break end end
check(hero ~= nil, "hero with a town")
local victim, lawless
local fids = {}; for fid in pairs(C.state().F) do fids[#fids + 1] = fid end; table.sort(fids)
for _, fid in ipairs(fids) do
  if fid ~= hero.f and fid ~= pf then
    if not victim and M.lawful(C, OM, W, fid) then victim = fid end
    if not lawless and not M.lawful(C, OM, W, fid) then lawless = fid end
  end
end
check(victim ~= nil, "lawful victim found")
for _, h in ipairs(F.heroes()) do if h ~= hero then h.x = (h.x or 0) + 9e6 end end
local function deed(kind, extra)
  local ev = { type = "deed", kind = kind, tone = "harm", a = hero.f, b = victim, n = 1, x = hero.x + 100, z = hero.z + 100, town_name = "Testtown" }
  if extra then for k, v in pairs(extra) do ev[k] = v end end
  C.emit(ev)
end
-- 0) H4: дело, которое Outlaws приписывает своему разыскиваемому (рядом, без живой банды), Fates не берёт
local OS = OM.O(C.state())
OS.L["o999"] = { i = 999, n = "Test Outlaw", g = hero.f, st = "a", x = hero.x + 50, z = hero.z + 50, t = 0, b = 0, bb = {} }
check(OM.data(C) ~= nil, "outlaws.json loaded")
deed("killed")
check((hero.b or 0) == 0 and (F.stats().deed_outlaw or 0) == 1, "deed owned by outlaw -> no fates bounty (one deed, one bounty)")
OS.L["o999"] = nil
-- 1) не живой, рядом: награда растёт в h.bb, ядро — позже
local ev0 = #FEV
deed("killed")
check((hero.b or 0) > 0 and hero.bb and next(hero.bb), "deed raises hero bounty: " .. tostring(hero.b))
check(logged("deed bounty +") and logged("native later"), "marker: deed bounty + native later")
local de; for i = ev0 + 1, #FEV do if FEV[i].type == "fate_deed" then de = FEV[i] end end
check(de and de.deed == "killed" and de.b == victim and tostring(de.text):find(hero.n, 1, true) and de.bounty == hero.b, "fate_deed on bus with text")
local found = false
for _, e in ipairs(C.state().events) do if e.type == "fate_deed" then found = true end end
check(found, "fate_deed in chronicle (rumor source)")
local b1 = hero.b
deed("killed")
check(hero.b == b1 and (F.stats().deed_dup or 0) == 1, "same deed same day deduped")
deed("killed", { by_player = true }); deed("killed", { to_player = true }); deed("aided")
check(hero.b == b1, "player/help deeds ignored")
if lawless then
  local sv = victim; victim = lawless; deed("executed"); victim = sv
  check(hero.b == b1 and (F.stats().deed_lawless or 0) >= 1, "lawless victim gives no bounty")
end
C.emit({ type = "deed", kind = "killed", a = hero.f, b = victim, n = 1, x = hero.x + 9e6, z = hero.z + 9e6 })
check(hero.b == b1, "far deed not blamed")
deed("executed"); local b2 = hero.b
check(b2 > b1, "executed raises bounty")
deed("captured")
check(hero.b == b2 and (F.stats().deed_capped or 0) >= 1, "per-hero day cap")
-- 2) отряд героя у игрока: родная награда ядра при выходе
REL = 50
hero.sp = -1000; M.live = {}; M.pend = nil
PCS = {}; CHARS = {}
pc = MKCH("PC1", pf, hero.x + 300, hero.z + 300, { player = true, platoon = "player_squad" })
PCS[1] = pc; CHARS[1] = pc
for i = 1, 40 do tick(500); if M.live["h" .. hero.i] then break end; CLOCK = CLOCK + 80 end
local lv = M.live["h" .. hero.i]
check(lv and lv.named, "hero squad live and named")
local made; for i = #MADE, 1, -1 do if MADE[i].leader.name == hero.n then made = MADE[i]; break end end
check(made ~= nil, "leader found")
local tot = 0; if made then for _, b in ipairs(made.leader.bty) do tot = tot + b[2] end end
check(tot == hero.b, "native bounty on spawn equals hero bounty: " .. tot .. " vs " .. tostring(hero.b))
check(logged("native bounty ok on " .. hero.n), "marker: native bounty ok on spawn")
check(hero.met == 1 and #REM == 0, "first meeting: no memory write")
-- 3) живое дело: прибавка сразу в ядро
DAYV = 501
local nb, b3 = made and #made.leader.bty or 0, hero.b
deed("killed")
check(made and #made.leader.bty == nb + 1 and made.leader.bty[#made.leader.bty][2] == hero.b - b3, "live deed -> unfairAddToBounty increment")
check(made and made.leader.bty[#made.leader.bty][1].id == OM.law(victim), "bounty from victim's law faction")
check(logged("native ok"), "marker: deed native ok")
-- 4) повторная встреча: родная память через KMM_Nemesis
-- шаг судьбы дня 501 (гибель/плен/рана/правосудие по случайному броску, death_p T0 = 5 %) мог снять героя до встречи: 1 падение
-- на ~12 прогонов (fate_death в логе). Здесь проверяется память при встрече, а не судьба — шаги судьбы на время встречи выключены.
C.cfg().params.fates.step_p = 0
M.live = {}; M.pend = nil; hero.sp = -1000
for i = 1, 40 do tick(501); if M.live["h" .. hero.i] then break end; CLOCK = CLOCK + 80 end
C.cfg().params.fates.step_p = nil
check(hero.met == 2 and #REM == 1 and REM[1][2] == "LT_FRIENDLY_AQUAINTANCE", "repeat meeting -> remember: " .. tostring(REM[1] and REM[1][2]))
check(logged("memory LT_FRIENDLY_AQUAINTANCE for " .. hero.n), "marker: memory")
-- 5) враждебность из ядра с фолбэком
local bc = { r = "bandit_chief", f = hero.f, rep = 90 }
REL = -80; check(M.hostile(C, M.cfg(), bc) == true, "core hostile relation -> chief targets player")
REL = 40; check(M.hostile(C, M.cfg(), bc) == false, "core friendly -> no target")
REL = nil
local r, src = M.prel(C, hero.f)
check(src == "model", "no core -> conductor model fallback: " .. tostring(src))
check(M.hostile(C, M.cfg(), { r = "trader", f = hero.f, rep = -50 }) == false, "non-chief never targets")
check(M.alive(C, C.state(), hero.f) == C.alive(hero.f), "alive via C.alive")
-- 6) награда тает; охотники закрывают её
local b4 = hero.b
M.bounty_day(M.cfg(), hero)
check(hero.b < b4, "bounty decays")
local cfg = M.cfg(); cfg.justice_max = 1; cfg.justice_per = 1
local got = M.justice(C, F.state(), W, cfg, hero, 501)
check(got and (not F.state().H["h" .. hero.i] or (hero.st == "e" and hero.b == nil)), "justice: dead or jailed, bounty closed")
check((F.stats().justice or 0) == 1, "justice counted")
check(next(F.disabled()) == nil and not M.deed_off, "module and deed link enabled")
-- 7) без KMM_Outlaws связка спит, модуль жив
local sv = KMM_Outlaws; KMM_Outlaws = nil
DAYV = 502; local hh; for _, h in ipairs(F.heroes()) do if h.st == "a" then hh = h; break end end
if hh then C.emit({ type = "deed", kind = "killed", a = hh.f, b = victim, n = 1, x = hh.x, z = hh.z }) end
KMM_Outlaws = sv
check(logged("bounty link idle") and next(F.disabled()) == nil and not M.deed_off, "no Outlaws: link idle, module alive")
-- 8) H3: другой сейв — указатели Platoon прошлого мира сброшены
local oldpl, oldpend = {}, { t = os.clock(), id = "h1" }
M.live = { h1 = { pl = oldpl, t = os.clock(), named = true } }; M.pend = oldpend
C.reset()
tick(600)
-- после сброса модуль вправе сразу заказать новый отряд (случайный spawn_p): проверяем, что старые указатели ушли
local stale = false; for _, lv in pairs(M.live) do if lv.pl == oldpl then stale = true end end
check(not stale and M.pend ~= oldpend and M.live_S == C.state(), "world change drops live squads")
check(logged("world changed: live squads dropped"), "marker: world changed")
check(next(F.disabled()) == nil, "module enabled after world change")
-- 9) Y1: дело игрока без свидетелей - награды героя нет
local f0 = M.stats.deed_unwitnessed or 0
M.on_deed_g({ type = "deed", kind = "killed", by_player = true, witnessed = false, a = "x", b = "y" })
check((M.stats.deed_unwitnessed or 0) == f0 + 1 and not M.deed_off, "Fates: unwitnessed player deed skipped")
RESULT = #FAILS == 0 and ("OK " .. N) or ("FAIL: " .. table.concat(FAILS, "; "))
'''.replace("TMPDIR", TMP), "test")
L.lua_getfield.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_char_p]
L.lua_getfield(st, -10002, b"RESULT")
r = L.lua_tolstring(st, -1, None).decode()
print(r)
sys.exit(0 if r.startswith("OK") else 1)
