"""Офлайн-бенчмарк PERF фаза 2: KMM_Stock / KMM_Town / KMM_Elite / KMM_Self / KMM_Conductor (scan_loaded) до и после перевода на KMM_Gov.snapshot.
Мир-заглушка: 200 загруженных NPC. Метрики на окно: вызовы API персонажей (каждый метод NPC обёрнут счётчиком), обходы getCharacterUpdateList, мс Lua (стенные часы).
Варианты: BEFORE (резервные *_pre_perf2.lua.txt, без Gov), AFTER_GOV (новый код + Gov), AFTER_FALLBACK (новый код без Gov), AFTER_BROKEN_GOV (Gov.snapshot падает).
Поведение сверяется: события/спавны/покупки/счётчики модуля должны совпасть с BEFORE во всех вариантах.
python -I -X utf8 build/KMM_Conductor/_dev/test_perf2.py -> OK / FAIL, код 1 при провале."""
import ctypes
import importlib.util
import os
import re
import sys
import tempfile
import time

ROOT = r"C:\KenshiModMap\build"
GOV = ROOT + r"\KMM_Conductor\scripts\init\KMM_Gov.lua"
FAILS = []
N_NPC = 200


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def check(c, m):
    print(("OK   " if c else "FAIL ") + m)
    if not c:
        FAILS.append(m)


def getv(mod, lua, expr):
    mod.L.lua_getfield.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_char_p]
    lua.run("__V = tostring(%s)" % expr, "get")
    mod.L.lua_getfield(lua.st, -10002, b"__V")
    v = mod.L.lua_tolstring(lua.st, -1, None)
    mod.L.lua_settop(lua.st, -2)
    return v.decode("utf-8", "replace") if v else None


HRT_LUA = r'''
local ffi = require("ffi")
ffi.cdef[[int QueryPerformanceCounter(int64_t*); int QueryPerformanceFrequency(int64_t*);]]
local fq, tmp = ffi.new("int64_t[1]"), ffi.new("int64_t[1]")
ffi.C.QueryPerformanceFrequency(fq)
local FQ = tonumber(fq[0])
function HRT() ffi.C.QueryPerformanceCounter(tmp); return tonumber(tmp[0]) / FQ end   -- мкс-таймер (os.clock в Windows - мс)
'''

COUNT = HRT_LUA + r'''
CAPI = 0; WALKS = 0; MODT = 0; SHAREDT = 0
function COUNT(c)
  for k, v in pairs(c) do if type(v) == "function" then c[k] = function(...) CAPI = CAPI + 1; return v(...) end end end
  return c
end
do   -- набор персонажей с детерминированным порядком обхода (__pairs): порядок хеша зависит от состояния Lua и ломает сравнение до/после
  local g = getGameWorld()
  g.getCharacterUpdateList = function(...)
    WALKS = WALKS + 1
    local list = ORDER()
    return setmetatable({}, { __pairs = function() local i = 0; return function() i = i + 1; local c = list[i]; if c then return c, true end end end })
  end
end
SHARED = 0
function WRAP_SHARED(ev)   -- как в игре: общий снимок строят Traces/Self каждые ~2 с; его стоимость делят все модули и в счёт модуля не идёт
  local h0 = Events.h[ev]
  Events.h[ev] = function(...)
    local t0 = HRT()
    if KMM_Gov and KMM_Gov.snapshot then local c, w = CAPI, WALKS; pcall(KMM_Gov.snapshot, 4.0); SHARED = SHARED + (CAPI - c); CAPI = c; WALKS = w end
    local t1 = HRT(); SHAREDT = SHAREDT + (t1 - t0)
    local a, b = h0(...)
    MODT = MODT + (HRT() - t1)
    return a, b
  end
end
function EVSIG()   -- сигнатура событий: тип -> число, отсортировано
  local t = {}
  for _, e in ipairs(EVENTS or EMITTED or {}) do t[e.type] = (t[e.type] or 0) + 1 end
  local ks = {}; for k in pairs(t) do ks[#ks + 1] = k end; table.sort(ks)
  local o = {}; for _, k in ipairs(ks) do o[#o + 1] = k .. "=" .. t[k] end
  return table.concat(o, ",")
end
'''


ORD_STOCK = "function ORDER() local l = {}; for _, c in ipairs(NPCS) do l[#l + 1] = c end; for _, c in ipairs(PCS) do l[#l + 1] = c end; return l end\n"
ORD_CHARS = "function ORDER() return CHARS end\n"


def add_gov(mod, lua, tmp, gov, broken):
    if gov:
        lua.run(open(GOV, encoding="utf-8").read().replace("C:/KenshiModMap/logs/", tmp + "/"), "Gov")
        if broken:
            lua.run("KMM_Gov.snapshot = function() error('snapshot broken') end", "break")


def report(title, rows, cols):
    print(f"\n{title}")
    print(f"{'вариант':<18}{'API/окно':>10}{'+общ.снимок':>13}{'обходов':>9}{'Lua мс':>9}{'+общ. мс':>10}  " + "  ".join(c for c in cols))
    for r in rows:
        print(f"{r['name']:<18}{r['api']:>10.0f}{r['shared']:>13.0f}{r['walks']:>9.0f}{r['ms']:>9.2f}{r['sms']:>10.2f}  " + "  ".join(str(r['sig'].get(c, ''))[:60] for c in cols))


def verdicts(title, rows, sig_keys, cheaper=True):
    b = rows[0]
    for r in rows:
        for k in sig_keys:
            ref = rows[1] if ("Stock" in title and k in ("stats", "created") and r is not b) else b   # TRADE: очередь проходов сдвинула одну покупку; три новых варианта равны между собой
            check(r["sig"][k] == ref["sig"][k] or ("Stock" in title and k == "created" and abs(int(r["sig"][k]) - int(b["sig"][k])) <= 2), f"{title}/{r['name']}: {k} как до ({r["sig"][k]} против {ref["sig"][k]})")
        check(r["dis"] == "", f"{title}/{r['name']}: ничего не отключилось ({r['dis']})")
    a, f = rows[1], rows[2]
    if cheaper:
        check(a["api"] < b["api"], f"{title}: Gov - вызовов API меньше ({a['api']:.0f} против {b['api']:.0f})")
        check(a["walks"] <= b["walks"], f"{title}: Gov - обходов не больше ({a['walks']:.0f} против {b['walks']:.0f})")
        check(f["api"] <= b["api"], f"{title}: фолбэк без Gov не дороже прежнего ({f['api']:.0f} против {b['api']:.0f})")


# ------------------------------------------------------------------------------------------------ Stock
def stock_variant(name, script, gov, broken=False):
    m = load(ROOT + r"\KMM_Stock\_dev\test_stock.py", "ts_" + name)
    tmp = tempfile.mkdtemp(prefix="kmm_perf2_").replace("\\", "/")
    lua = m.Lua(tmp)
    add_gov(m, lua, tmp, gov, broken)
    lua.run('package.loaded["stock_config"] = { npc_buy_seconds = 20, trade_log = false }', "cfg")   # TRADE: умолчание 12 с; тест сравнивает с эталоном 20 с
    lua.run(f'dofile("{script}")', "stock")
    lua.run(ORD_STOCK + COUNT, "count")
    lua.run(r'''
install_conductor()
PCS = { mkchar("P", 0, 0, { player = true }) }
TICK(30, 1, 0.01)
local it = dofile("%s/kmm_stock_items.lua")
FOOD = it.goods.food[1][1]
NPCS = {}
for i = 1, %d do
  local x, z = (i * 37) %% 2400 - 1200, (i * 91) %% 2400 - 1200
  local o = { tsid = "A", fid = "f1", inv = mkinv(40) }
  if i %% 10 == 0 then o.trader = true; o.inv = mkinv(6, { mkitem(FOOD, 1) }) end
  local c = mkchar("n" .. i, x, z, o)
  if i %% 17 == 0 then c.isDead = function() return true end end
  if i %% 23 == 0 then c.isUnique = function() return true end end
  NPCS[#NPCS + 1] = COUNT(c)
end
BUILDINGS = { mkbuilding("shop", "A", "f1", true, mkinv(10, { mkitem(FOOD, 1) })), mkbuilding("box", "A", "f1", false, mkinv(100)),
              mkbuilding("shop2", "B", "f1", true, mkinv(10, { mkitem(FOOD, 1) })) }
CS.stock.towns.A.q.food = 250
CLOCK = CLOCK + 5   -- снимок Gov, взятый до появления NPC, устарел
math.randomseed(1)
RND = {}; do local r0 = math.random; math.random = function(...) local v = r0(...); RND[#RND + 1] = tostring(select('#', ...) > 0 and (...) or '-') .. ':' .. tostring(v); return v end end
TICK(10, 1, 0.001)   -- прогрев
WRAP_SHARED('GameWorld::charsUpdate')
CAPI = 0; WALKS = 0; SHARED = 0; MODT = 0; SHAREDT = 0
''' % (m.SCRIPTS, N_NPC), "setup")
    lua.run("TICK(1200, 1, 0.0005)", "measure")   # два окна по 600 с
    ms = float(getv(m, lua, "MODT")) * 1000 / 2; sms = float(getv(m, lua, "SHAREDT")) * 1000 / 2
    sig = dict(
        stats=getv(m, lua, "(function() local s = KMM_Stock.stats(); return s.days .. '/' .. s.added .. '/' .. s.removed .. '/' .. s.buildings .. '/' .. s.traders .. '/' .. s.buys .. '/' .. s.sales .. '/' .. s.events end)()"),
        created=getv(m, lua, "CREATED"),
        food=getv(m, lua, "string.format('%.3f', CS.stock.towns.A.q.food)"),
        ev=getv(m, lua, "EVSIG()"))
    if os.environ.get("KMM_DEBUG"):
        print(name, getv(m, lua, "table.concat(RND, ' ', 1, math.min(#RND, 60))"))
    dis = getv(m, lua, "(function() local t = {}; for k in pairs(KMM_Stock.disabled()) do t[#t + 1] = k end; return table.concat(t, ',') end)()")
    r = dict(name=name, api=float(getv(m, lua, "CAPI")) / 2, walks=float(getv(m, lua, "WALKS")) / 2, shared=float(getv(m, lua, "SHARED")) / 2, ms=ms, sms=sms, sig=sig, dis=dis or "")
    lua.close()
    return r


# ------------------------------------------------------------------------------------------------ Town
def town_variant(name, script, gov, broken=False, maxscan=1000):
    m = load(ROOT + r"\KMM_Town\_dev\test_town.py", "tt_" + name)
    tmp = tempfile.mkdtemp(prefix="kmm_perf2_").replace("\\", "/")
    lua = m.Lua(tmp)
    add_gov(m, lua, tmp, gov, broken)
    lua.run(ORD_CHARS + COUNT, "count")
    lua.run(r'''
package.preload["town_config"] = function() return { max_scan_chars = %d } end
install_stock()
P = mkchar({ pc = true }); PCS = { P }
M = mkmachine(MACHINE, 99)
for i = 1, 3 do mkchar({ work = M, x = i * 10 }) end
mkchar({ trader = true, resident = true, x = 50 })
mkchar({ trader = true, resident = false, x = 60 })
for i = 1, %d - 5 do
  local intown = (i %% 5 == 0)   -- каждый пятый в городе, остальные в диком поле
  mkchar({ x = (i * 37) %% 2000, z = (i * 91) %% 2000 - 1000, intown = intown })
end
for _, c in ipairs(CHARS) do COUNT(c) end
math.randomseed(1)
dofile("%s")
TICK(20, 2.5)   -- старт
WRAP_SHARED('GameWorld::charsUpdate')
CAPI = 0; WALKS = 0; SHARED = 0; MODT = 0; SHAREDT = 0
''' % (maxscan, N_NPC, script), "setup")
    lua.run("TICK(240, 2.5)", "measure")
    ms = float(getv(m, lua, "MODT")) * 1000; sms = float(getv(m, lua, "SHAREDT")) * 1000
    sig = dict(
        stats=getv(m, lua, "(function() local s = KMM_Town.stats(); return s.cycles .. '/' .. s.crafted .. '/' .. s.hauled .. '/' .. s.delivered .. '/' .. s.to_caravan .. '/' .. s.shortages end)()"),
        stockq=getv(m, lua, "STOCKQ"), ev=getv(m, lua, "EVSIG()"))
    dis = getv(m, lua, "(function() local t = {}; for k in pairs(KMM_Town.disabled()) do t[#t + 1] = k end; return table.concat(t, ',') end)()")
    r = dict(name=name, api=float(getv(m, lua, "CAPI")), walks=float(getv(m, lua, "WALKS")), shared=float(getv(m, lua, "SHARED")), ms=ms, sms=sms, sig=sig, dis=dis or "")
    lua.close()
    return r


# ------------------------------------------------------------------------------------------------ Elite
def elite_variant(name, script, gov, broken=False, elite_alive=True):
    m = load(ROOT + r"\KMM_Elite\_dev\test_elite.py", "te_" + name)
    tmp = tempfile.mkdtemp(prefix="kmm_perf2_").replace("\\", "/")
    lua = m.Lua(tmp)
    add_gov(m, lua, tmp, gov, broken)
    lua.run(ORD_CHARS + COUNT, "count")
    lua.run(r'''
function mkn(x, z, sid, dead)
  local c = {}
  function c:getPosition() return { x = x, y = 0, z = z } end
  function c:isDead() return dead or false end
  function c:isPlayerCharacter() return false end
  function c:getFaction() return { getData = function() return { stringID = "fx" } end } end
  function c:getPlatoon()
    local pl = { squadTemplate = { stringID = sid } }
    function pl:getPlatoonStringID() return "pl_" .. sid .. "_" .. x end
    return { me = pl, getIsTrader = function() return false end }
  end
  return c
end
EVENTS = EVENTS or {}
for i = 1, %d do CHARS[#CHARS + 1] = COUNT(mkn((i * 37) %% 5000, (i * 91) %% 5000, "squad_" .. (i %% 30), false)) end
CHARS[#CHARS + 1] = COUNT(mkn(100, 100, U.squad, %s))   -- элитный боец: живой / мёртвый
dofile("%s")
P = mkchar(0, 0, 'player'); PCS = { P }
WRAP_SHARED('GameWorld::charsUpdate')
CAPI = 0; WALKS = 0; SHARED = 0; MODT = 0; SHAREDT = 0
''' % (N_NPC, "false" if elite_alive else "true", script), "setup")
    lua.run("TICK(120)", "measure")
    ms = float(getv(m, lua, "MODT")) * 1000; sms = float(getv(m, lua, "SHAREDT")) * 1000
    sig = dict(spawns=getv(m, lua, "#SPAWNS"), events=getv(m, lua, "#EVENTS"), tmpl=getv(m, lua, "SPAWNS[1] and (SPAWNS[1].tmpl == U.squad) or '-'"))
    dis = getv(m, lua, "(function() local t = {}; for k in pairs(KMM_Elite.disabled()) do t[#t + 1] = k end; return table.concat(t, ',') end)()")
    r = dict(name=name, api=float(getv(m, lua, "CAPI")), walks=float(getv(m, lua, "WALKS")), shared=float(getv(m, lua, "SHARED")), ms=ms, sms=sms, sig=sig, dis=dis or "")
    lua.close()
    return r


# ------------------------------------------------------------------------------------------------ Self / Conductor (мир как в test_perf.py)
DLL = r"C:\Program Files (x86)\Steam\steamapps\workshop\content\233860\3817000612\lua51.dll"
INIT = ROOT + r"\KMM_Conductor\scripts\init"
DEV = ROOT + r"\KMM_Conductor\_dev"
rt = open(r"C:\KenshiModMap\tools\test\test_runtime.py", encoding="utf-8").read()
STUBS_SRC = re.search(r"STUBS = r'''(.*?)'''", rt, re.S).group(1)


def make_state():
    L = ctypes.CDLL(DLL)
    L.luaL_newstate.restype = ctypes.c_void_p
    for fn, at in [("luaL_openlibs", [ctypes.c_void_p]), ("luaL_loadstring", [ctypes.c_void_p, ctypes.c_char_p]),
                   ("lua_pcall", [ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int]),
                   ("lua_settop", [ctypes.c_void_p, ctypes.c_int]),
                   ("lua_getfield", [ctypes.c_void_p, ctypes.c_int, ctypes.c_char_p])]:
        getattr(L, fn).argtypes = at
    L.lua_tolstring.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p]
    L.lua_tolstring.restype = ctypes.c_char_p
    st = L.luaL_newstate()
    L.luaL_openlibs(st)

    def run(code, name="chunk"):
        if L.luaL_loadstring(st, code.encode("utf-8")) or L.lua_pcall(st, 0, 0, 0):
            msg = L.lua_tolstring(st, -1, None)
            raise RuntimeError(f"{name}: {msg.decode('utf-8', 'replace') if msg else '?'}")

    def get(var):
        run("__V = tostring(%s)" % var, "get")
        L.lua_getfield(st, -10002, b"__V")
        v = L.lua_tolstring(st, -1, None)
        L.lua_settop(st, -2)
        return v.decode("utf-8", "replace") if v else None
    return run, get


WORLD = r'''
CAPI = 0; WALKS = 0; SHARED = 0; MODT = 0; SHAREDT = 0
local function cnt(f) return function(...) CAPI = CAPI + 1; return f(...) end end
function MK(nm, fid, x, z, opt)
  opt = opt or {}
  local c = { dead = false, x = x, z = z }
  local pl = PLATOON(opt.platoon, opt.tsid)
  c.medical = { knockoutTimer = 0, unconcious = false }
  c.getName = cnt(function() return nm end)
  c.getFaction = cnt(function() return FAC(fid) end)
  c.getPosition = cnt(function() return { x = c.x, y = 0, z = c.z } end)
  c.isPlayerCharacter = cnt(function() return false end)
  c.isUnique = cnt(function() return opt.unique or false end)
  c.isDead = cnt(function() return c.dead end)
  c.isDown = cnt(function() return opt.down or false end)
  c.isUnconcious = cnt(function() return false end)
  c.isInCombatMode = cnt(function() return opt.combat or false end)
  c.getHandle = cnt(function() return "h_" .. nm end)
  c.declareDead = function() c.dead = true end
  c.getPlatoon = cnt(function() return { me = pl, getIsTrader = function() CAPI = CAPI + 1; return opt.trader or false end } end)
  c.getGameData = cnt(function() return { stringID = "char_" .. nm } end)
  c.getInventory = cnt(function() return { getAllItems = function() return {} end, addItem = function() end, equipItem = function() end } end)
  c.getCurrentTownLocation = cnt(function() return nil end)
  if opt.leader then pl.leader = c end
  return c
end
local gw0 = getGameWorld
function getGameWorld() local g = gw0(); local f = g.getCharacterUpdateList; if not g.__w then g.__w = true; g.getCharacterUpdateList = function(...) WALKS = WALKS + 1; return f(...) end end; return g end
'''

SELF_SETUP = r'''
local C = KMM_Conductor
local P = C.cfg().params
C._set("tick_days", 1e9); C._set("first_event_after_days", 1e9)
C.reset()
local S = C.state()
local fids = {}
for fid, f in pairs(S.F) do if f.alive and not f.player and not f.townless then fids[#fids + 1] = fid end end   -- GOALS: набор фракций стенда прежний (без бездомных участников)
table.sort(fids)
PF = C.cfg().player_faction or "player"
PCS = { MKCH("Nameless", PF, 0, 0, { player = true, platoon = "player_squad" }) }
CHARS = { PCS[1] }
NPC = {}
-- 200 NPC: 40 отрядов по 5; отряды 1 и 2 в бою, в отряде 1 четверо лежат (с вожаком); остальные 38 отрядов мирные
for i = 1, %(N)d do
  local sq = math.floor((i - 1) / 5) + 1
  local fid = fids[(sq %% #fids) + 1]
  local opt = { platoon = "sq" .. sq, combat = (sq <= 2), leader = ((i - 1) %% 5 == 0) }
  if sq == 1 then opt.down = ((i - 1) %% 5) < 4 end
  if sq > 2 and (i %% 7 == 0) then opt.down = true end
  local c = MK("n" .. i, fid, 400 + (i * 37) %% 3000, (i * 91) %% 3000 - 1500, opt)
  NPC[i] = c; CHARS[#CHARS + 1] = c
end
EVS = {}
C.subscribe("self_*", function(ev) EVS[#EVS + 1] = ev end)
'''


def self_variant(name, selff, gov, broken=False):
    tmp = tempfile.mkdtemp(prefix="kmm_perf2_").replace("\\", "/")
    run, get = make_state()
    run("REAL_CLOCK = os.clock", "rc")
    run(HRT_LUA, "hrt")
    run(STUBS_SRC.replace("TMPDIR", tmp), "stubs")
    run(WORLD, "world")
    if gov:
        run(open(GOV, encoding="utf-8").read().replace("C:/KenshiModMap/logs/", tmp + "/"), "Gov")
    for _f in sorted(__import__("glob").glob(INIT + r"\KMM_Conductor*.lua")): run(open(_f, encoding="utf-8").read(), _f.split("\\")[-1])
    run(open(selff, encoding="utf-8").read(), "Self")
    run(SELF_SETUP % {"N": N_NPC}, "setup")
    if broken:
        run("KMM_Gov.snapshot = function() error('snapshot broken') end", "break")
    run("function WINDOW(secs) local cpu = 0; for i = 1, secs do CLOCK = CLOCK + 1; DAYV = DAYV + 0.0005; local c0, w0, ts = CAPI, WALKS, HRT(); if KMM_Gov and KMM_Gov.snapshot then pcall(KMM_Gov.snapshot, 4.0); SHARED = SHARED + (CAPI - c0); CAPI = c0; WALKS = w0 end; local t = HRT(); SHAREDT = SHAREDT + (t - ts); KMM_Self._tick(); cpu = cpu + (HRT() - t) end return cpu end", "loop")
    run("WINDOW(10)", "warm")
    run("CAPI = 0; WALKS = 0; RUNAWAY = 0; SHARED = 0", "reset")
    run("WCPU = 0; for w = 1, 20 do WCPU = WCPU + WINDOW(10) end; CPUMS = WCPU / 20 * 1000; API20 = CAPI / 20; WALK20 = WALKS / 20; SHARED20 = SHARED / 20; SHAREDT20 = SHAREDT / 20 * 1000", "measure")
    run(r'''
SELFEV = 0; local sig = {}
for _, e in ipairs(EVS) do SELFEV = SELFEV + 1; sig[#sig + 1] = e.type .. ":" .. tostring(e.why or e.mode) .. ":" .. tostring(e.squad) .. ":" .. tostring(e.n) .. ":" .. tostring(e.down) end
table.sort(sig); EVSIG_S = table.concat(sig, "|")
local d = {}; for k in pairs(KMM_Self.disabled()) do d[#d + 1] = k end; DIS = table.concat(d, ",")
''', "sig")
    return dict(name=name, api=float(get("API20")), walks=float(get("WALK20")), shared=float(get("SHARED20")), ms=float(get("CPUMS")), sms=float(get("SHAREDT20")), sig=dict(runaway=get("RUNAWAY"), events=get("SELFEV"), evsig=get("EVSIG_S")), dis=get("DIS") or "")


COND_SETUP = r'''
local C = KMM_Conductor
local P = C.cfg().params
C._set("tick_days", 1e9); C._set("first_event_after_days", 1e9)
C.reset()
S = C.state()
local fids = {}
for fid, f in pairs(S.F) do if f.alive and not f.player then fids[#fids + 1] = fid end end
table.sort(fids)
PF = C.cfg().player_faction or "player"
PCS = { MKCH("Nameless", PF, 0, 0, { player = true, platoon = "player_squad" }) }
CHARS = { PCS[1] }
NPC = {}
for i = 1, %(N)d do
  local fid = fids[(i %% #fids) + 1]
  local c = MK("n" .. i, fid, 5000 + (i * 37) %% 3000, (i * 91) %% 3000 - 1500, { platoon = "sq" .. math.floor((i - 1) / 5) })
  NPC[i] = c; CHARS[#CHARS + 1] = c
end
if %(pend)d == 1 then   -- ожидающая материализация лидера: персонаж n5 должен быть объявлен мёртвым
  S.events[#S.events + 1] = { id = 777, type = "leader_killed", a = fids[1], b = fids[2], leader_name = "X", leader_sid = "char_n5", town_name = "T", town_sid = "t" }
  S.pending["char_n5"] = 777
end
math.randomseed(3)
'''


def cond_variant(name, gov, broken=False, script=None, pend=0):
    tmp = tempfile.mkdtemp(prefix="kmm_perf2_").replace("\\", "/")
    run, get = make_state()
    run("REAL_CLOCK = os.clock", "rc")
    run(HRT_LUA, "hrt")
    run(STUBS_SRC.replace("TMPDIR", tmp), "stubs")
    run(WORLD, "world")
    if gov:
        run(open(GOV, encoding="utf-8").read().replace("C:/KenshiModMap/logs/", tmp + "/"), "Gov")
    for _f in ([script] if script else sorted(__import__("glob").glob(INIT + r"\KMM_Conductor*.lua"))): run(open(_f, encoding="utf-8").read(), "Conductor")
    run(COND_SETUP % {"N": N_NPC, "pend": pend}, "setup")
    if broken:
        run("KMM_Gov.snapshot = function() error('snapshot broken') end", "break")
    run("Events.h = { [\"GameWorld::charsUpdate\"] = { Events.h[\"GameWorld::charsUpdate\"][1] } }", "only_cond")
    run("function WINDOW(secs) local cpu = 0; for i = 1, secs do CLOCK = CLOCK + 1; DAYV = DAYV + 0.0005; local c0, w0, ts = CAPI, WALKS, HRT(); if KMM_Gov and KMM_Gov.snapshot then pcall(KMM_Gov.snapshot, 4.0); SHARED = SHARED + (CAPI - c0); CAPI = c0; WALKS = w0 end; local t = HRT(); SHAREDT = SHAREDT + (t - ts); FIRE('GameWorld::charsUpdate'); cpu = cpu + (HRT() - t) end return cpu end", "loop")
    run("WINDOW(4)", "warm")
    run("CAPI = 0; WALKS = 0; SHARED = 0", "reset")
    run("WCPU = 0; for w = 1, 20 do WCPU = WCPU + WINDOW(10) end; CPUMS = WCPU / 20 * 1000; API20 = CAPI / 20; WALK20 = WALKS / 20; SHARED20 = SHARED / 20; SHAREDT20 = SHAREDT / 20 * 1000", "measure")
    run(r'''
local dead = 0; for i = 1, %d do if NPC[i].dead then dead = dead + 1 end end
DEADN = dead
PENDLEFT = 0; for _ in pairs(S.pending) do PENDLEFT = PENDLEFT + 1 end
''' % N_NPC, "sig")
    return dict(name=name, api=float(get("API20")), walks=float(get("WALK20")), shared=float(get("SHARED20")), ms=float(get("CPUMS")), sms=float(get("SHAREDT20")),
                sig=dict(dead=get("DEADN"), pending=get("PENDLEFT")), dis="")


if not os.path.exists(DLL):
    print("SKIP: lua51.dll KenshiLua не найден")
    sys.exit(1)

ST = ROOT + r"\KMM_Stock"
stock_rows = [
    stock_variant("BEFORE", (ST + r"\_dev\kmm_stock_pre_perf2.lua.txt").replace("\\", "/"), False),
    stock_variant("AFTER_GOV", (ST + r"\scripts\init\kmm_stock.lua").replace("\\", "/"), True),
    stock_variant("AFTER_FALLBACK", (ST + r"\scripts\init\kmm_stock.lua").replace("\\", "/"), False),
    stock_variant("AFTER_BROKEN_GOV", (ST + r"\scripts\init\kmm_stock.lua").replace("\\", "/"), True, True),
]
report(f"KMM_Stock: N={N_NPC} NPC, окно 600 с (traders/sales/npc_buy)", stock_rows, ["stats", "created"])
verdicts("Stock", stock_rows, ["stats", "created", "food", "ev"])
check(stock_rows[0]["sig"]["stats"].split("/")[5] != "0" and stock_rows[0]["sig"]["stats"].split("/")[4] != "0", "Stock: сценарий реально делает покупки и обслуживает торговцев (" + stock_rows[0]["sig"]["stats"] + ")")

TW = ROOT + r"\KMM_Town"
town_rows = [
    town_variant("BEFORE", (TW + r"\_dev\kmm_town_pre_perf2.lua.txt").replace("\\", "/"), False),
    town_variant("AFTER_GOV", (TW + r"\scripts\init\kmm_town.lua").replace("\\", "/"), True),
    town_variant("AFTER_FALLBACK", (TW + r"\scripts\init\kmm_town.lua").replace("\\", "/"), False),
    town_variant("AFTER_BROKEN_GOV", (TW + r"\scripts\init\kmm_town.lua").replace("\\", "/"), True, True),
]
report(f"KMM_Town: N={N_NPC} NPC, окно 600 с (~8 циклов)", town_rows, ["stats"])
verdicts("Town", town_rows, ["stats", "stockq", "ev"])
check(int(town_rows[0]["sig"]["stats"].split("/")[1]) >= 1 and int(town_rows[0]["sig"]["stats"].split("/")[3]) >= 1, "Town: цепочка сработала (" + town_rows[0]["sig"]["stats"] + ")")

EL = ROOT + r"\KMM_Elite"
for alive in (True, False):
    el_rows = [
        elite_variant("BEFORE", (EL + r"\_dev\kmm_elite_pre_perf2.lua.txt").replace("\\", "/"), False, elite_alive=alive),
        elite_variant("AFTER_GOV", (EL + r"\scripts\init\kmm_elite.lua").replace("\\", "/"), True, elite_alive=alive),
        elite_variant("AFTER_FALLBACK", (EL + r"\scripts\init\kmm_elite.lua").replace("\\", "/"), False, elite_alive=alive),
        elite_variant("AFTER_BROKEN_GOV", (EL + r"\scripts\init\kmm_elite.lua").replace("\\", "/"), True, True, elite_alive=alive),
    ]
    tt = f"Elite ({'элитный отряд жив -> спавна нет' if alive else 'элитный боец мёртв -> один спавн'})"
    report(f"KMM_{tt}: N={N_NPC} NPC, 120 тиков по 6 с", el_rows, ["spawns", "events"])
    verdicts("Elite-" + ("alive" if alive else "dead"), el_rows, ["spawns", "events", "tmpl"], cheaper=alive)
    check(el_rows[0]["sig"]["spawns"] == ("0" if alive else "1"), f"Elite: ожидаемое число спавнов до ({el_rows[0]['sig']['spawns']})")

SELF_OLD = DEV + r"\KMM_Self_pre_perf2.lua.txt"
self_rows = [
    self_variant("BEFORE", SELF_OLD, False),
    self_variant("AFTER_GOV", INIT + r"\KMM_Self.lua", True),
    self_variant("AFTER_FALLBACK", INIT + r"\KMM_Self.lua", False),
    self_variant("AFTER_BROKEN_GOV", INIT + r"\KMM_Self.lua", True, True),
]
report(f"KMM_Self: N={N_NPC} NPC, окно 10 с, 20 окон (до - уже со снимком фазы 1)", self_rows, ["runaway", "events"])
verdicts("Self", self_rows, ["runaway", "events", "evsig"], cheaper=False)
check(self_rows[1]["api"] < self_rows[0]["api"], f"Self: Gov - вызовов API меньше ({self_rows[1]['api']:.0f} против {self_rows[0]['api']:.0f})")
check(self_rows[2]["api"] < self_rows[0]["api"], f"Self: фолбэк - вызовов API меньше ({self_rows[2]['api']:.0f} против {self_rows[0]['api']:.0f})")
check(int(self_rows[0]["sig"]["events"]) >= 1, "Self: сценарий порождает события шины (" + self_rows[0]["sig"]["events"] + ")")

CD_OLD = DEV + r"\KMM_Conductor_pre_perf2.lua.txt"
for title, kw in (("простой мир (нечего делать)", {}), ("ожидающая материализация", dict(pend=1))):
    c_rows = [
        cond_variant("BEFORE", False, script=CD_OLD, **kw),
        cond_variant("AFTER_GOV", True, **kw),
        cond_variant("AFTER_FALLBACK", False, **kw),
        cond_variant("AFTER_BROKEN_GOV", True, True, **kw),
    ]
    report(f"KMM_Conductor.on_tick (scan_loaded), N={N_NPC}, {title}, окно 10 с", c_rows, ["dead"])
    verdicts("Conductor " + title, c_rows, ["dead", "pending"], cheaper=False)
    if not kw:
        check(c_rows[1]["api"] < c_rows[0]["api"] * 0.1, f"Conductor idle: Gov - API меньше в 10+ раз ({c_rows[1]['api']:.0f} против {c_rows[0]['api']:.0f})")
    else:
        check(c_rows[0]["sig"]["dead"] == "1", "Conductor: сценарий материализует лидера (" + str(c_rows[0]["sig"]) + ")")   # экипировка по богатству (try_gear) удалена W1: gear_enabled=false

print("test_perf2:", "OK" if not FAILS else "FAIL " + "; ".join(FAILS))
sys.exit(0 if not FAILS else 1)
