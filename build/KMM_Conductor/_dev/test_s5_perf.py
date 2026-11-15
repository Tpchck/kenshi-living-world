"""S5: игровой бенч стоимости тика KMM_Traces / KMM_Self / KMM_Stock (кадры как в игре).
В игре снимок KMM_Gov живёт ОДИН кадр (метка getTimeStamp, краш 2026-11-13), поэтому каждый вызов снимка в новом кадре = полная
перестройка (обход всех NPC ~5 вызовов API на персонажа), и её стоимость Gov.run записывает модулю, который позвал первым.
Офлайн-бенчи test_perf/test_perf2 этого не видят (без метки снимок живёт ttl секунд). Здесь: 10 кадров в секунду игрового времени,
getTimeStamp растёт на кадр, обработчики charsUpdate идут через KMM_Gov.run, у каждого модуля свой счёт:
  API/10с   — вызовы методов NPC самим модулем (без перестроек снимка),
  снимков/10с — кадры, в которых модуль запросил снимок (в одиночку = столько перестроек),
  пик API   — максимум вызовов API за один вызов обработчика ВМЕСТЕ с перестройкой, которую он оплатил (то, что Gov видит как пик),
  мс/10с    — стенное время обработчиков (мкс-таймер), вместе с оплаченными перестройками.
«Сводно» — объединение кадров со снимком у всех трёх модулей (в игре они делят снимок, если зовут его в одном кадре).
Варианты: BEFORE (*_pre_s5.lua.txt — код до S5), AFTER (текущий). Поведение сверяется (runAway, события, покупки).
T2 (2026-11-15): набор getCharacterUpdateList с has() как ogre_unordered_set в игре — снимок Gov живёт до ttl_rt с проверкой has() в новом
кадре; «снимок» модуля = кадры, где он оплатил сборку ИЛИ проверку (их вызовы API — в колонке снимка). Стоимость Gov — test_t2_gov.py.
python -I -X utf8 build/KMM_Conductor/_dev/test_s5_perf.py -> OK / FAIL, код 1 при провале."""
import ctypes
import importlib.util
import os
import re
import sys
import tempfile

ROOT = r"C:\KenshiModMap\build"
INIT = ROOT + r"\KMM_Conductor\scripts\init"
DEV = ROOT + r"\KMM_Conductor\_dev"
GOV = INIT + r"\KMM_Gov.lua"
ST = ROOT + r"\KMM_Stock"
DLL = r"C:\Program Files (x86)\Steam\steamapps\workshop\content\233860\3817000612\lua51.dll"
rt = open(r"C:\KenshiModMap\tools\test\test_runtime.py", encoding="utf-8").read()
STUBS_SRC = re.search(r"STUBS = r'''(.*?)'''", rt, re.S).group(1)
N_NPC = 200
FPS = 10
T0 = 1000          # общий старт окна измерения (секунды игрового os.clock) — у обоих стендов одинаковый
WIN = 120          # длина окна, с
FAILS = []


def check(c, m):
    print(("OK   " if c else "FAIL ") + m)
    if not c:
        FAILS.append(m)


HRT_LUA = r'''
local ffi = require("ffi")
ffi.cdef[[int QueryPerformanceCounter(int64_t*); int QueryPerformanceFrequency(int64_t*);]]
local fq, tmp = ffi.new("int64_t[1]"), ffi.new("int64_t[1]")
ffi.C.QueryPerformanceFrequency(fq)
local FQ = tonumber(fq[0])
function HRT() ffi.C.QueryPerformanceCounter(tmp); return tonumber(tmp[0]) / FQ end
'''

# учёт по модулю: обёртка обработчика; перестройка снимка Gov выделяется по счётчику builds
METER = r'''
FRAME = 0; MEAS = false
M = {}
SNAPF = {}   -- имя модуля -> { [кадр] = true }
local function bstat() local g = rawget(_G, "KMM_Gov"); if g and g.snapshot_stats then local s = g.snapshot_stats(); return s.builds + (s.vals or 0) end; return 0 end
function METER_WRAP(name, f)
  M[name] = M[name] or { api = 0, build_api = 0, req = 0, peak = 0, t = 0, calls = 0 }
  SNAPF[name] = SNAPF[name] or {}
  local m = M[name]
  return function(...)
    local c0, b0, w0, ba0, t0 = CAPI, bstat(), WALKS, BUILD_API or 0, HRT()
    local a, b = f(...)
    local dt = HRT() - t0
    if MEAS then
      local dc = CAPI - c0
      local built = bstat() - b0
      local walked = WALKS - w0
      if built > 0 or walked > 0 then SNAPF[name][FRAME] = true; m.req = m.req + 1 end
      m.calls = m.calls + 1; m.t = m.t + dt
      if dc > m.peak then m.peak = dc end
      m.api = m.api + dc
      m.build_api = m.build_api + ((BUILD_API or 0) - ba0)
    end
    return a, b
  end
end
-- перестройка снимка: её вызовы API отдельно (для колонки «API модуля без снимка»)
function METER_GOV()
  local g = rawget(_G, "KMM_Gov")
  if not (g and g.snapshot) then return end
  local s0 = g.snapshot
  g.snapshot = function(...)
    local s = g.snapshot_stats()
    local b0, v0, c0 = s.builds, s.vals or 0, CAPI
    local r = s0(...)
    local s2 = g.snapshot_stats()
    if s2.builds > b0 or (s2.vals or 0) > v0 then BUILD_API = (BUILD_API or 0) + (CAPI - c0); BUILD_LAST = CAPI - c0 end   -- T2: и проверка has() в новом кадре
    return r
  end
end
function SNAPLIST(name) local o = {}; for f in pairs(SNAPF[name] or {}) do o[#o + 1] = f end; table.sort(o); return table.concat(o, ",") end
'''


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


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
            L.lua_settop(st, 0)
            raise RuntimeError(f"{name}: {msg.decode('utf-8', 'replace') if msg else '?'}")

    def get(var):
        run("__V = tostring(%s)" % var, "get")
        L.lua_getfield(st, -10002, b"__V")
        v = L.lua_tolstring(st, -1, None)
        L.lua_settop(st, -2)
        return v.decode("utf-8", "replace") if v else None
    return run, get


# ------------------------------------------------------------------------------------------------ Traces + Self (мир test_perf)
WORLD = r'''
CAPI = 0; WALKS = 0; FRAME_C0 = 0; FPEAK = 0
APIM = {}
SET_MT = { __index = { has = function(self, c) CAPI = CAPI + 1; APIM.has = (APIM.has or 0) + 1; return rawget(self, c) == true end } }
local function cnt(nm, f) return function(...) CAPI = CAPI + 1; APIM[nm] = (APIM[nm] or 0) + 1; return f(...) end end
function MK(nm, fid, x, z, opt)
  opt = opt or {}
  local c = { dead = false, x = x, z = z }
  local pl = PLATOON(opt.platoon, opt.tsid)
  c.medical = { knockoutTimer = 0, unconcious = false }
  c.getName = cnt("getName", function() return nm end)
  c.getFaction = cnt("getFaction", function() return FAC(fid) end)
  c.getPosition = cnt("getPosition", function() return { x = c.x, y = 0, z = c.z } end)
  c.isPlayerCharacter = cnt("isPlayerCharacter", function() return false end)
  c.isUnique = cnt("isUnique", function() return opt.unique or false end)
  c.isDead = cnt("isDead", function() return c.dead end)
  c.isDown = cnt("isDown", function() return opt.down or false end)
  c.isUnconcious = cnt("isUnconcious", function() return false end)
  c.isInCombatMode = cnt("isInCombatMode", function() return opt.combat or false end)
  c.isAnimal = cnt("isAnimal", function() return nil end)
  c.getRace = cnt("getRace", function() return { data = { name = "Greenlander" } } end)
  c.getHandle = cnt("getHandle", function() return "h_" .. nm end)
  c.declareDead = function() c.dead = true end
  c.getPlatoon = cnt("getPlatoon", function() return { me = pl, getIsTrader = function() CAPI = CAPI + 1; APIM.getIsTrader = (APIM.getIsTrader or 0) + 1; return opt.trader or false end } end)
  c.getGameData = cnt("getGameData", function() return { stringID = "char_" .. nm } end)
  c.getInventory = cnt("getInventory", function() return { getAllItems = function() return {} end, addItem = function() end, equipItem = function() end } end)
  c.getCurrentTownLocation = cnt("getCurrentTownLocation", function() return nil end)
  c.is_trader = opt.trader
  if opt.leader then pl.leader = c end
  return c
end
local gw0 = getGameWorld
function getGameWorld()
  local g = gw0()
  local f = g.getCharacterUpdateList
  g.getCharacterUpdateList = function(...)
    WALKS = WALKS + 1
    local s = f(...)
    if HAS ~= false then setmetatable(s, SET_MT) end   -- как ogre_unordered_set в игре: set:has(ch) (ContainersReference)
    return s
  end
  g.getTimeStamp = function() return FRAME end   -- как в игре: метка кадра
  return g
end
'''

TS_SETUP = r'''
local C = KMM_Conductor
local P = C.cfg().params
C._set("tick_days", 1e9); C._set("first_event_after_days", 1e9)
P.traces.first_hour_traces = 0
C.reset()
local S = C.state()
local fids = {}
for fid, f in pairs(S.F) do if f.alive and not f.player and not f.townless then fids[#fids + 1] = fid end end
table.sort(fids)
PF = C.cfg().player_faction or "player"
PCS = { MKCH("Nameless", PF, 0, 0, { player = true, platoon = "player_squad" }) }
CHARS = { PCS[1] }
NPC = {}
-- 200 NPC: 40 отрядов по 5; каждый 4-й торговый; отряды 1-2 в бою (в 1-м четверо лежат с вожаком); у мирных каждый 7-й лежит
for i = 1, %(N)d do
  local sq = math.floor((i - 1) / 5) + 1
  local fid = fids[(sq %% #fids) + 1]
  local opt = { platoon = "sq" .. sq, trader = (sq %% 4 == 0), combat = (sq <= 2), leader = ((i - 1) %% 5 == 0) }
  if sq == 1 then opt.down = ((i - 1) %% 5) < 4 end
  if sq > 2 and (i %% 7 == 0) then opt.down = true end
  local c = MK("n" .. i, fid, 400 + (i * 37) %% 3000, (i * 91) %% 3000 - 1500, opt)
  NPC[i] = c; CHARS[#CHARS + 1] = c
end
local AMB = KMM_Traces.ambush()
AMB.perf = { a = fids[1], b = fids[2], x = 1000, z = 0, t0 = 0, mode = "wait" }
EVS = {}
C.subscribe("self_*", function(ev) EVS[#EVS + 1] = ev end)
C.subscribe("caravan_lost", function(ev) EVS[#EVS + 1] = ev end)
'''


def ts_variant(name, traces, selff, gov=GOV, pre="", extra=(), post=""):
    tmp = tempfile.mkdtemp(prefix="kmm_s5_").replace("\\", "/")
    run, get = make_state()
    run(HRT_LUA, "hrt")
    run(STUBS_SRC.replace("TMPDIR", tmp), "stubs")
    run(WORLD, "world")
    if pre: run(pre, "pre")
    run(METER, "meter")
    run(open(gov, encoding="utf-8").read().replace("C:/KenshiModMap/logs/", tmp + "/"), "Gov")
    run("METER_GOV()", "metergov")
    for _f in sorted(__import__("glob").glob(INIT + r"\KMM_Conductor*.lua")): run(open(_f, encoding="utf-8").read(), _f.split("\\")[-1])
    run("H0 = #(Events.h['GameWorld::charsUpdate'] or {})", "h0")
    run(open(traces, encoding="utf-8").read(), "Traces")
    run("H1 = #(Events.h['GameWorld::charsUpdate'] or {})", "h1")
    run(open(selff, encoding="utf-8").read(), "Self")
    run(r'''
local hs = Events.h['GameWorld::charsUpdate']
local nh = {}
for i = H0 + 1, H1 do nh[#nh + 1] = METER_WRAP("traces", hs[i]) end
for i = H1 + 1, #hs do nh[#nh + 1] = METER_WRAP("self", hs[i]) end
Events.h['GameWorld::charsUpdate'] = nh   -- только Traces и Self (дирижёр и прочие не мешают счёту)
''', "wrap")
    if post: run(post, "post")
    run(TS_SETUP % {"N": N_NPC}, "setup")
    run(r'''
function FRAMES(secs)
  for i = 1, secs * %(FPS)d do
    FRAME = FRAME + 1; CLOCK = CLOCK + 1 / %(FPS)d; DAYV = DAYV + 0.00005
    FRAME_C0 = CAPI
    FIRE("GameWorld::charsUpdate")
    if MEAS and CAPI - FRAME_C0 > FPEAK then FPEAK = CAPI - FRAME_C0 end
  end
end
CLOCK = %(T0)d - 30
FRAMES(30)   -- прогрев: init, первые сканы
CLOCK = %(T0)d; FRAME = %(T0)d * %(FPS)d
CAPI = 0; WALKS = 0; BUILD_API = 0; APIM = {}; MEAS = true
FRAMES(%(WIN)d)
MEAS = false
''' % {"FPS": FPS, "T0": T0, "WIN": WIN}, "measure")
    run(r'''
for i = 1, %(N)d do local c = NPC[i]; if c.is_trader then c.dead = true end end
FRAMES(12)
LOST = 0; SELFEV = 0
local sig = {}
for _, e in ipairs(EVS) do
  if e.type == "caravan_lost" then LOST = LOST + 1 else SELFEV = SELFEV + 1; sig[#sig + 1] = e.type .. ":" .. tostring(e.why or e.mode) .. ":" .. tostring(e.squad) end
end
table.sort(sig); EVSIG = table.concat(sig, "|")
local d = {}; for k in pairs(KMM_Traces.disabled()) do d[#d + 1] = "T:" .. k end; for k in pairs(KMM_Self.disabled()) do d[#d + 1] = "S:" .. k end
DIS = table.concat(d, ",")
local ks = {}; for k, v in pairs(APIM) do ks[#ks + 1] = k end; table.sort(ks)
local o = {}; for _, k in ipairs(ks) do o[#o + 1] = k .. "=" .. APIM[k] end; APIMS = table.concat(o, " ")
''' % {"N": N_NPC}, "sig")
    out = {}
    for mod in ("traces", "self"):
        out[mod] = dict(api=float(get(f"M.{mod}.api")), build_api=float(get(f"M.{mod}.build_api")), req=float(get(f"M.{mod}.req")), peak=float(get(f"M.{mod}.peak")),
                        ms=float(get(f"M.{mod}.t")) * 1000, frames=set(int(x) for x in (get(f'SNAPLIST("{mod}")') or "").split(",") if x))
    out["sig"] = dict(runaway=get("RUNAWAY"), lost=get("LOST"), selfev=get("SELFEV"), evsig=get("EVSIG"))
    out["dis"] = get("DIS") or ""
    out["apim"] = get("APIMS")
    out["x"] = {e: get(e) for e in extra}
    out["tmp"] = tmp
    return out


# ------------------------------------------------------------------------------------------------ Stock (мир test_perf2)
COUNT = r'''
CAPI = 0; WALKS = 0; FRAME_C0 = 0; FPEAK = 0
function COUNT(c)
  for k, v in pairs(c) do if type(v) == "function" then c[k] = function(...) CAPI = CAPI + 1; return v(...) end end end
  return c
end
do
  local g = getGameWorld()
  g.getCharacterUpdateList = function(...)
    WALKS = WALKS + 1
    local list, mem = {}, {}; for _, c in ipairs(NPCS) do list[#list + 1] = c; mem[c] = true end; for _, c in ipairs(PCS) do list[#list + 1] = c; mem[c] = true end
    local idx = (HAS ~= false) and { has = function(self, c) CAPI = CAPI + 1; return mem[c] == true end } or {}   -- T2: как ogre_unordered_set:has в игре
    return setmetatable({}, { __index = idx, __pairs = function() local i = 0; return function() i = i + 1; local c = list[i]; if c then return c, true end end end })
  end
  function g:getTimeStamp() return FRAME end
end
'''


def stock_variant(name, script, gov=GOV, pre="", extra=()):
    m = load(ST + r"\_dev\test_stock.py", "ts5_" + name)
    tmp = tempfile.mkdtemp(prefix="kmm_s5_").replace("\\", "/")
    lua = m.Lua(tmp)
    run = lua.run

    def get(expr):
        m.L.lua_getfield.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_char_p]
        run("__V = tostring(%s)" % expr, "get")
        m.L.lua_getfield(lua.st, -10002, b"__V")
        v = m.L.lua_tolstring(lua.st, -1, None)
        m.L.lua_settop(lua.st, -2)
        return v.decode("utf-8", "replace") if v else None
    run(HRT_LUA, "hrt")
    if pre: run(pre, "pre")
    run(METER, "meter")
    run(open(gov, encoding="utf-8").read().replace("C:/KenshiModMap/logs/", tmp + "/"), "Gov")
    run("METER_GOV()", "metergov")
    run('package.loaded["stock_config"] = { npc_buy_seconds = 20, trade_log = false }', "cfg")
    run(f'dofile("{script}")', "stock")
    run(COUNT, "count")
    run(r'''
Events.h["GameWorld::charsUpdate"] = METER_WRAP("stock", Events.h["GameWorld::charsUpdate"])
install_conductor()
PCS = { mkchar("P", 0, 0, { player = true }) }
CLOCK = %(T0)d - 60
for _ = 1, 30 do FRAME = FRAME + 1; CLOCK = CLOCK + 1; DAY = DAY + 0.01; Events.h["GameWorld::charsUpdate"]({}) end
local it = dofile("%(scripts)s/kmm_stock_items.lua")
FOOD = it.goods.food[1][1]
NPCS = {}
for i = 1, %(N)d do
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
math.randomseed(1)
function FRAMES(secs)
  for i = 1, secs * %(FPS)d do
    FRAME = FRAME + 1; CLOCK = CLOCK + 1 / %(FPS)d; DAY = DAY + 0.0005 / %(FPS)d
    FRAME_C0 = CAPI
    Events.h["GameWorld::charsUpdate"]({})
    if MEAS and CAPI - FRAME_C0 > FPEAK then FPEAK = CAPI - FRAME_C0 end
  end
end
FRAMES(30)
CLOCK = %(T0)d; FRAME = %(T0)d * %(FPS)d
CAPI = 0; WALKS = 0; BUILD_API = 0; MEAS = true
FRAMES(%(WIN)d)
MEAS = false
''' % {"T0": T0, "N": N_NPC, "FPS": FPS, "WIN": WIN, "scripts": m.SCRIPTS}, "setup")
    sig = dict(stats=get("(function() local s = KMM_Stock.stats(); return s.added .. '/' .. s.removed .. '/' .. s.buildings .. '/' .. s.traders .. '/' .. s.buys .. '/' .. s.sales end)()"),
               created=get("CREATED"), food=get("string.format('%.3f', CS.stock.towns.A.q.food)"))
    dis = get("(function() local t = {}; for k in pairs(KMM_Stock.disabled()) do t[#t + 1] = k end; return table.concat(t, ',') end)()") or ""
    r = dict(api=float(get("M.stock.api")), build_api=float(get("M.stock.build_api")), req=float(get("M.stock.req")), peak=float(get("M.stock.peak")), ms=float(get("M.stock.t")) * 1000,
             frames=set(int(x) for x in (get('SNAPLIST("stock")') or "").split(",") if x))
    x = {e: get(e) for e in extra}
    lua.close()
    return dict(stock=r, sig=sig, dis=dis, x=x, tmp=tmp)


def main():
    if not os.path.exists(DLL):
        print("SKIP: lua51.dll KenshiLua не найден")
        sys.exit(1)

    PER = WIN / 10.0
    B_ts = ts_variant("BEFORE", DEV + r"\KMM_Traces_pre_s5.lua.txt", DEV + r"\KMM_Self_pre_s5.lua.txt")
    A_ts = ts_variant("AFTER", INIT + r"\KMM_Traces.lua", INIT + r"\KMM_Self.lua")
    B_st = stock_variant("BEFORE", (ST + r"\_dev\kmm_stock_pre_s5.lua.txt").replace("\\", "/"))
    A_st = stock_variant("AFTER", (ST + r"\scripts\init\kmm_stock.lua").replace("\\", "/"))

    bn = sum(v[m]["req"] for v, m in ((B_ts, "traces"), (B_ts, "self"), (B_st, "stock")))
    bcost = sum(v[m]["build_api"] for v, m in ((B_ts, "traces"), (B_ts, "self"), (B_st, "stock"))) / max(1, bn)
    print(f"\nN={N_NPC} NPC, {FPS} кадров/с, окно {WIN} с, метка кадра getTimeStamp, has() у набора (снимок Gov до ttl_rt); перестройка ~{bcost:.0f} API")
    print(f"{'модуль':<8}{'вариант':<8}{'API/10с':>9}{'снимков/10с':>13}{'полн. API/10с':>15}{'пик API':>9}{'мс/10с':>9}")
    rows = []
    for mod, bv, av in (("traces", B_ts, A_ts), ("self", B_ts, A_ts), ("stock", B_st, A_st)):
        for nm, v in (("BEFORE", bv), ("AFTER", av)):
            r = v[mod]
            own = r["api"] - r["build_api"]   # вызовы самого модуля, без перестроек снимка
            full = r["api"]                   # с перестройками, которые модуль оплатил бы в игре в одиночку
            rows.append((mod, nm, own / PER, r["req"] / PER, full / PER, r["peak"], r["ms"] / PER))
            print(f"{mod:<8}{nm:<8}{own / PER:>9.0f}{r['req'] / PER:>13.2f}{full / PER:>15.0f}{r['peak']:>9.0f}{r['ms'] / PER:>9.2f}")
    ub = len(B_ts["traces"]["frames"] | B_ts["self"]["frames"] | B_st["stock"]["frames"]) / PER
    ua = len(A_ts["traces"]["frames"] | A_ts["self"]["frames"] | A_st["stock"]["frames"]) / PER
    sb = (B_ts["traces"]["req"] + B_ts["self"]["req"] + B_st["stock"]["req"]) / PER
    sa = (A_ts["traces"]["req"] + A_ts["self"]["req"] + A_st["stock"]["req"]) / PER
    print(f"сводно: кадров со снимком/10с (= перестроек в игре) {ub:.2f} -> {ua:.2f}; запросов {sb:.2f} -> {sa:.2f}")
    print("API по методам до:   ", B_ts["apim"])
    print("API по методам после:", A_ts["apim"])

    R = {(r[0], r[1]): r for r in rows}
    for mod in ("traces", "self", "stock"):
        b, a = R[(mod, "BEFORE")], R[(mod, "AFTER")]
        check(a[4] < b[4], f"{mod}: полных вызовов API на окно меньше ({a[4]:.0f} против {b[4]:.0f})")
        check(a[3] <= b[3], f"{mod}: перестроек снимка на окно не больше ({a[3]:.2f} против {b[3]:.2f})")
    check(ua < ub, f"сводно: перестроек снимка меньше ({ua:.2f} против {ub:.2f})")
    # поведение
    for k in ("runaway", "lost", "selfev", "evsig"):
        check(A_ts["sig"][k] == B_ts["sig"][k], f"Traces+Self: {k} как до ({A_ts['sig'][k]} против {B_ts['sig'][k]})")
    check(int(B_ts["sig"]["selfev"]) >= 1 and int(B_ts["sig"]["lost"]) >= 1, f"сценарий порождает события (self={B_ts['sig']['selfev']}, lost={B_ts['sig']['lost']})")
    check(A_ts["dis"] == "" and B_ts["dis"] == "", f"Traces/Self: ничего не отключилось ({A_ts['dis']}|{B_ts['dis']})")
    check(A_st["dis"] == "" and B_st["dis"] == "", f"Stock: ничего не отключилось ({A_st['dis']}|{B_st['dis']})")
    sb_, sa_ = B_st["sig"]["stats"].split("/"), A_st["sig"]["stats"].split("/")
    check(sa_[2:4] == sb_[2:4], f"Stock: здания/торговцы как до ({A_st['sig']['stats']} против {B_st['sig']['stats']})")
    check(int(sa_[4]) >= 1 and abs(int(sa_[4]) - int(sb_[4])) <= max(2, int(sb_[4]) // 3), f"Stock: покупки жителей идут ({sa_[4]} против {sb_[4]})")
    print("test_s5_perf:", "OK" if not FAILS else "FAIL " + "; ".join(FAILS))
    sys.exit(0 if not FAILS else 1)


if __name__ == "__main__":
    main()
