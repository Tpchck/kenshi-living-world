"""S3 offline test KMM_Outlaws/KMM_Nemesis: materialized gang/rival becomes an engine persistent squad (setPersistentSquad + check,
fallback field, FAIL -> temporary as before), vanilla AI_PACKAGE mission (replaceAIPackage: racket/roam/hunt), no duplicates on repeat
materialization (lookup by platoon key / leader name in faction lists: unloaded -> wait + sync position, loaded -> adopt), lost -> spawn
again after N misses (orphan released when it resurfaces), release on death, cap with orphans,
double-bounty / world-change / repeat-meeting / unloaded-death guards; markers persistent ok/FAIL/adopt/lost/released, package ok/FAIL; public exports for KMM_Fates.
python -I -X utf8 build/KMM_Conductor/_dev/test_s3_persist.py -> OK."""
import ctypes, re, sys, tempfile

DLL = r"C:\Program Files (x86)\Steam\steamapps\workshop\content\233860\3817000612\lua51.dll"
B = r"C:\KenshiModMap\build\KMM_Conductor\scripts\init"
TMP = tempfile.mkdtemp(prefix="kmm_s3_").replace("\\", "/")
L = ctypes.CDLL(DLL)
L.luaL_newstate.restype = ctypes.c_void_p
for fn, at in [("luaL_openlibs", [ctypes.c_void_p]), ("luaL_loadstring", [ctypes.c_void_p, ctypes.c_char_p]),
               ("lua_pcall", [ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int])]:
    getattr(L, fn).argtypes = at
L.lua_tolstring.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p]
L.lua_tolstring.restype = ctypes.c_char_p
L.lua_getfield.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_char_p]
st = L.luaL_newstate()
L.luaL_openlibs(st)


def run(code, name="chunk"):
    if L.luaL_loadstring(st, code.encode("utf-8")) or L.lua_pcall(st, 0, 0, 0):
        msg = L.lua_tolstring(st, -1, None)
        raise RuntimeError(f"{name}: {msg.decode('utf-8', 'replace') if msg else '?'}")


rt = open(r"C:\KenshiModMap\tools\test\test_runtime.py", encoding="utf-8").read()
run(re.search(r"STUBS = r'''(.*?)'''", rt, re.S).group(1).replace("TMPDIR", TMP), "stubs")
run("math.randomseed(20261115)", "seed")
for f in [p.split(chr(92))[-1][:-4] for p in sorted(__import__("glob").glob(B + r"\KMM_Conductor*.lua"))] + ["KMM_Traces", "KMM_Fates", "KMM_Outlaws", "KMM_Nemesis"]:
    run(open(B + "\\" + f + ".lua", encoding="utf-8").read(), f + ".lua")
run(r'''
N, FAILS = 0, {}
function check(c, what) N = N + 1; if not c then FAILS[#FAILS + 1] = what end end
local C = KMM_Conductor
C.reset()
local TP = C.cfg().params.traces
TP.first_hour_traces = 0; TP.arrive_enabled = false; TP.bounty = { enabled = false }
local pf = C.cfg().player_faction or "player"
C.cfg().params.outlaws = { watch_s = 1e9, sdir = "TMPDIR/", spawn_p = 1, cd_h = 0, native_bounty = false, persist_max = 2 }
local O_, M, NN = KMM_Outlaws, KMM_Outlaws._M, KMM_Nemesis._N
LOGS, NLOGS = {}, {}
M.log = function(m) LOGS[#LOGS + 1] = tostring(m) end
NN.log = function(m) NLOGS[#NLOGS + 1] = tostring(m) end
local function logged(s, t) for _, l in ipairs(t or LOGS) do if l:find(s, 1, true) then return true end end; return false end
local function nlogs(s) local n = 0; for _, l in ipairs(LOGS) do if l:find(s, 1, true) then n = n + 1 end end; return n end
PCS = {}; CHARS = {}
local pc = MKCH("PC1", pf, 0, 0, { player = true, platoon = "player_squad" })
PCS[1] = pc; CHARS[1] = pc
DAYV = 500; CLOCK = CLOCK + 100; FIRE("GameWorld::charsUpdate", {})
local S = C.state()
local D = M.data(C)
local O = M.O(S)
check(D and next(O.L) ~= nil, "outlaws state ready")
-- мир ядра: списки отрядов фракций, пакеты ИИ по sid
LISTS = {}   -- fid -> { act = {}, unl = {} }
local function lists(fid) LISTS[fid] = LISTS[fid] or { act = {}, unl = {} }; return LISTS[fid] end
PKG_OK = { ["5504-gamedata.base"] = true, ["2675-gamedata.base"] = true, ["2957-gamedata.base"] = true }
local NK = 0
function MKPL(opt)
  opt = opt or {}
  NK = NK + 1
  local leader = { name = "Nameless Raider", dead = false }
  function leader:setName(n) self.name = n end
  function leader:getName() return self.name end
  function leader:isDead() return self.dead end
  leader.bty = {}
  leader.crimes = { unfairAddToBounty = function(_, fo, amt) leader.bty[#leader.bty + 1] = { fo, amt } end,
                    getTotalBounty = function() local t = 0; for _, b in ipairs(leader.bty) do t = t + b[2] end; return t end,
                    getBountyRecognitionThreshold = function() return 500 end }
  local pl = { isDead = false, key = opt.key or ("plat_" .. NK), pers = false, pos = { x = 100, y = 0, z = 200 }, n = 4, pkgs = {}, cur = "Raiders default" }
  function pl:getSquadLeader() return leader end
  function pl:getActivePlatoon() if self.loaded == false then return nil end; return { setName = function() end } end
  function pl:getPlatoonStringID() return self.key end
  function pl:setPersistentSquad(on) if opt.nopersist then error("not bound") end; self.pers = on end
  function pl:isPersistentSquad() return self.pers end
  function pl:getPosition() return self.pos end
  function pl:getCharacterCount() return self.n end
  local board = {}
  function board.replaceAIPackage(_, gd) pl.pkgs[#pl.pkgs + 1] = gd.stringID; pl.cur = gd.stringID end
  function board.getCurrentAIPackageName() return pl.cur end
  function pl:getBlackboard() return board end
  pl.leader = leader
  return pl
end
local old = getGameWorld
getGameWorld = function()
  local w = old()
  w.factionMgr = { getFactionByStringID = function(self, sid)
    local f = FAC(sid)
    f.getActivePlatoons = function() return lists(sid).act end
    f.getUnloadedPlatoons = function() return lists(sid).unl end
    return f end }
  w.gamedata = { getData = function(self, sid, t) if t == 72 and not PKG_OK[sid] then return nil end; return { stringID = sid, t = t } end }
  return w
end
-- KMM_Traces подменён: заявка записывается, спавн делает тест (on_spawn с нашим платуном)
REQ = {}
local T = { request = function(job) REQ[#REQ + 1] = job; return true end, near = function() return true end }
local hero; for _, o in ipairs(O_.wanted()) do if o.st == "a" and o.s and M.tier_sid(D, o.g, o.t) then hero = o; break end end
if not hero then for _, o in ipairs(O_.wanted()) do if o.st == "a" and M.tier_sid(D, o.g, o.t) then hero = o; break end end end
for k, o in pairs(O.L) do if o ~= hero then O.L[k] = nil end end
local cfg = M.cfg()
local function vis() M.pend = nil; M.vis(C, O, D, cfg, T) end
-- (1) первая материализация: постоянный + пакет
vis()
check(#REQ == 1 and REQ[1].tag == "outlaw" and REQ[1].target == nil, "outlaw request issued")
local p1 = MKPL()
REQ[1].on_spawn({ p1 })
check(p1.pers == true and hero.pk == p1.key and hero.pf == hero.g, "squad persistent, key stored: " .. tostring(hero.pk))
check(logged("persistent ok " .. hero.n), "marker persistent ok")
local kind = REQ[1].to_fid and "racket" or "roam"
local want = kind == "racket" and "5504-gamedata.base" or "2675-gamedata.base"
check(p1.pkgs[1] == want and logged("package ok " .. kind .. " " .. want), "vanilla package " .. kind .. " applied")
check(M.live["o" .. hero.i] and M.live["o" .. hero.i].pk, "live entry marked persistent")
local function again() M.live = {}; M.adopt_t = {}; CLOCK = CLOCK + 120 end
-- (2) повторная встреча, отряд выгружен (в сейве): новой заявки нет, позиция — от ядра; 0 персонажей у выгруженного — не гибель (M4)
again(); hero.sp = -1000
p1.loaded = false; p1.pos = { x = 7777, y = 0, z = 8888 }; p1.n = 0
lists(hero.g).unl[1] = p1
vis()
check(#REQ == 1, "unloaded persistent squad: no duplicate spawn")
check(hero.x == 7777 and hero.z == 8888, "record position synced from engine squad")
check(not M.live["o" .. hero.i], "unloaded: not adopted as live")
check(O.L["o" .. hero.i] ~= nil and hero.pk == p1.key, "M4: unloaded squad with 0 characters is not declared dead")
p1.n = 4
-- (3) отряд загружен рядом: подхват без спавна; H1: награда ядра уже лежит — докладывается только разница
C.cfg().params.outlaws.native_bounty = true
p1.loaded = nil; p1.leader.name = "renamed by save"
p1.leader.bty = { { { id = hero.lf }, hero.b - 50 } }
lists(hero.g).unl[1] = nil; lists(hero.g).act[1] = p1
again(); vis()
check(#REQ == 1 and M.live["o" .. hero.i] and M.live["o" .. hero.i].pl == p1, "loaded persistent squad adopted, no new spawn")
check(p1.leader.name == hero.n and logged("persistent adopt " .. hero.n), "adopt marker + leader renamed")
check(#p1.leader.bty == 1, "H1: bounty already in engine (diff < 100) -> nothing added")
p1.leader.bty = { { { id = hero.lf }, 100 } }
again(); vis()
check(#p1.leader.bty == 2 and p1.leader.bty[2][2] == math.floor(hero.b - 100), "H1: adopt adds only the difference")
-- H1: главарь не загрузился в кадре подхвата -> watch одевает позже, тоже только разницей
local lead = p1.leader
again(); p1.leader = nil
p1.getSquadLeader = function(self) return self.leader end
lead.bty = { { { id = hero.lf }, hero.b } }
vis()
check(M.live["o" .. hero.i] and not M.live["o" .. hero.i].named, "leader not yet loaded at adopt")
p1.leader = lead
M.watch(C, O, D)
check(M.live["o" .. hero.i].named and #lead.bty == 1, "H1: watch dress of adopted squad does not double the bounty")
C.cfg().params.outlaws.native_bounty = false
-- (3b) ключ сменился (сейв): находим по имени главаря у загруженных
again()
p1.key = "new_key_after_load"
vis()
check(#REQ == 1 and M.live["o" .. hero.i] and hero.pk == "new_key_after_load", "found by leader name, key refreshed")
-- (4) H2: один промах — не потеря; lost после 3 промахов подряд, ключ уходит в сироты
lists(hero.g).act[1] = nil
again(); vis()
check(hero.pk == "new_key_after_load" and hero.pk_miss == 1 and #REQ == 1, "H2: single miss keeps the key, no spawn")
again(); vis()
check(hero.pk ~= nil and #REQ == 1, "H2: second miss keeps the key")
again(); vis()
check(hero.pk == nil and logged("persistent lost " .. hero.n) and #M.orph(O) == 1, "H2: lost after 3 misses, orphan kept")
check(#REQ == 2, "after lost: normal materialization again (same pass)")
-- (5) M5: метод не связан -> FAIL, временный (поле в обход ядра не пишется); пакета нет в данных -> package FAIL
PKG_OK = {}
local p2 = MKPL({ nopersist = true })
REQ[2].on_spawn({ p2 })
check(hero.pk == nil and p2._persistentSquad == nil and logged("persistent FAIL " .. hero.n), "M5: persistent FAIL -> temporary, no field bypass")
check(logged("package FAIL") and #p2.pkgs == 0, "package FAIL when AI_PACKAGE data missing")
check(M.live["o" .. hero.i] and not M.live["o" .. hero.i].pk, "temporary squad still tracked as before")
PKG_OK = { ["5504-gamedata.base"] = true, ["2675-gamedata.base"] = true, ["2957-gamedata.base"] = true }
-- H2: ключ не читается -> не делать постоянным
M.live = {}; hero.sp = -1000
vis()
local p3 = MKPL({ key = "" })
REQ[#REQ].on_spawn({ p3 })
check(hero.pk == nil and p3.pers == false and logged("no platoon key"), "H2: no key -> not persistent")
-- сирота всплыла в мире -> отпускается
p1.key = "new_key_after_load"; p1.loaded = false
lists(hero.g).unl[1] = p1
M.live = {}; M.adopt_t = {}; CLOCK = CLOCK + 120
M.vis_persist(C, O, D, cfg, T)
check(#M.orph(O) == 0 and p1.pers == false and logged("persistent orphan released"), "H2: orphan found by key and released")
lists(hero.g).unl[1] = nil
-- (6) гибель главаря: отряд отпускается (снова временный)
M.live = {}; hero.sp = -1000
vis()
local p4 = MKPL()
REQ[#REQ].on_spawn({ p4 })
check(hero.pk == p4.key, "persistent again")
lists(hero.g).act[1] = p4
local nm = hero.n
p4.leader.dead = true
M.watch(C, O, D)
check(O.L["o" .. hero.i] == nil and p4.pers == false and logged("persistent released " .. nm), "release on death")
lists(hero.g).act[1] = nil
-- (7) соперник Nemesis: цель — игрок, пакет охоты, маркер и в nemesis.log; M2: подхват не повторяет встречу в тот же день
local r = M.born(C, O, D, DAYV, hero.hr, hero.g)
r.pg = { deed = "spared", place = "Squin", day = DAYV, met = 1 }
for k, o in pairs(O.L) do if o ~= r then O.L[k] = nil end end
M.live = {}
local MEET = 0
local on0 = KMM_Nemesis.on_spawn
KMM_Nemesis.on_spawn = function(o, l) MEET = MEET + 1; return on0(o, l) end
vis()
local jr = REQ[#REQ]
check(jr.tag == "nemesis" and jr.target == "player", "rival request targets player")
local p5 = MKPL()
jr.on_spawn({ p5 })
check(r.pk == p5.key and p5.pkgs[1] == "2957-gamedata.base", "rival persistent + hunt package")
check(logged("persistent ok " .. r.n, NLOGS) and logged("package ok hunt", NLOGS), "markers mirrored to nemesis.log")
check(MEET == 1, "spawn = one meeting")
lists(r.g).act[1] = p5
again(); vis(); again(); vis()
check(MEET == 1 and nlogs("persistent adopt " .. r.n) == 2, "M2: adopts on the same day are not new meetings")
DAYV = DAYV + 1
again(); vis()
check(MEET == 2, "M2: next day the returning rival meets again")
lists(r.g).act[1] = nil
-- лимит: записи с ключом + сироты
for k, o in pairs(O.L) do if o ~= r then O.L[k] = nil end end
M.orph(O)[1] = { k = "lost1", f = r.g, n = "Old", d = DAYV }
local r3 = M.born(C, O, D, DAYV, hero.hr, hero.g)
local p6 = MKPL()
M.mat(C, O, r3, p6, "roam")
check(r3.pk == nil and logged("persistent FAIL " .. r3.n .. ": cap 2"), "persist_max counts orphans")
-- (8) Nemesis: постоянный соперник не телепортируется по следу игрока
r.x, r.z = 1e7, 1e7
NN.day_step(M, O, D, C, S, DAYV + 1)
check(r.x == 1e7 and r.z == 1e7, "persistent rival is not relocated by our follow model")
-- (9) экспорты для KMM_Fates
check(type(O_.add_bounty) == "function" and type(O_.native_bounty) == "function" and type(O_.lawful) == "function", "Outlaws exports")
check(type(KMM_Nemesis.remember) == "function", "Nemesis export remember")
local b0 = r3.b; O_.add_bounty(r3, r3.g, 100); check(r3.b > b0, "add_bounty export works")
check(type(O_.lawful(r3.g)) == "boolean", "lawful export returns boolean")
-- (10) H3: другой сейв (новая таблица состояния) -> указатели прошлого мира сброшены
M.live["o" .. r.i] = { pl = p5, t = CLOCK, pk = true }
M.live_S = {}
O_._tick()
check(not (M.live["o" .. r.i] and M.live["o" .. r.i].pl == p5), "H3: live squads reset on world change")
check(M.live_S == C.state() and logged("world changed"), "H3: marker world changed")
check(not M.off and not NN.off, "modules still on")
RESULT = #FAILS == 0 and ("OK " .. N) or ("FAIL: " .. table.concat(FAILS, "; "))
'''.replace("TMPDIR", TMP), "test")
L.lua_getfield(st, -10002, b"RESULT")
res = L.lua_tolstring(st, -1, None).decode("utf-8", "replace")
print(res)
sys.exit(0 if res.startswith("OK") else 1)
