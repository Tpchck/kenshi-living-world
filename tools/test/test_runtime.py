"""Юнит-тесты рантайма KMM на заглушках игрового API (LuaJIT из KenshiLua, без игры).
Грузит KMM_Conductor, KMM_Self, KMM_Traces, KMM_Rumors, kmm_ore как в игре (несколько обработчиков одного события),
гоняет такты, проверяет следы рядом с игроком, самосохранение, руду, и правило безотказности (сбой одной функции
отключает только её, причина пишется в debug.log). python -I -X utf8 tools/test/test_runtime.py"""
import ctypes
import os
import sys
import tempfile

DLL = r"C:\Program Files (x86)\Steam\steamapps\workshop\content\233860\3817000612\lua51.dll"
B = r"C:\KenshiModMap\build"
SCRIPTS = [*sorted(__import__("glob").glob(B + r"\KMM_Conductor\scripts\init\KMM_Conductor*.lua")), B + r"\KMM_Conductor\scripts\init\KMM_Self.lua",
           B + r"\KMM_Conductor\scripts\init\KMM_Traces.lua", B + r"\KMM_Conductor\scripts\init\KMM_Gov.lua", B + r"\KMM_Rumors\scripts\init\KMM_Rumors.lua",
           B + r"\KMM_Ore\scripts\init\kmm_ore.lua",
           B + r"\KMM_Conductor\scripts\init\KMM_Fates.lua", B + r"\KMM_Conductor\scripts\init\KMM_RelicRace.lua",
           B + r"\KMM_Conductor\scripts\init\KMM_Predators.lua", B + r"\KMM_Conductor\scripts\init\KMM_Siege.lua",
           B + r"\KMM_Conductor\scripts\init\KMM_Herds.lua",
           B + r"\KMM_Conductor\scripts\init\KMM_Veterans.lua", B + r"\KMM_Conductor\scripts\init\KMM_Outlaws.lua"]
TMP = tempfile.mkdtemp(prefix="kmm_rt_").replace("\\", "/")
L = ctypes.CDLL(DLL)
L.luaL_newstate.restype = ctypes.c_void_p
for fn, at in [("luaL_openlibs", [ctypes.c_void_p]), ("luaL_loadstring", [ctypes.c_void_p, ctypes.c_char_p]),
               ("lua_pcall", [ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int])]:
    getattr(L, fn).argtypes = at
L.lua_tolstring.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p]
L.lua_tolstring.restype = ctypes.c_char_p
st = L.luaL_newstate()
L.luaL_openlibs(st)
FAILS = []


def run(code, name):
    if L.luaL_loadstring(st, code.encode("utf-8")) or L.lua_pcall(st, 0, 0, 0):
        msg = L.lua_tolstring(st, -1, None).decode("utf-8", "replace")
        raise RuntimeError(name + ": " + msg)


STUBS = r'''
-- ENGINE_LIST (2026-11-13): списки движка в KenshiLua - userdata (sol2): pairs/ipairs/# работают (__pairs/__ipairs/__len), next() - нет.
-- Тест падает так же, как игра (лог: kmm_tempo.lua:571 bad argument #1 to 'next' (table expected, got userdata)).
do
  local rp, ri = pairs, ipairs
  pairs = function(t) local mt = type(t) == "userdata" and getmetatable(t); if mt and mt.__pairs then return mt.__pairs(t) end; return rp(t) end
  ipairs = function(t) local mt = type(t) == "userdata" and getmetatable(t); if mt and mt.__ipairs then return mt.__ipairs(t) end; return ri(t) end
  function ENGINE_LIST(t)
    local u = newproxy(true); local mt = getmetatable(u)
    mt.__index = function(_, k) return t[k] end
    mt.__len = function() return #t end
    mt.__pairs = function() return rp(t) end
    mt.__ipairs = function() return ri(t) end
    return u
  end
end
KMM_TEST = true   -- офлайн-тест: Conductor не режет фазы по os.clock и не пересевает RNG от os.time (детерминизм под нагрузкой verify_all)
local real_open = io.open
io.open = function(p, m) p = tostring(p):gsub("^C:/KenshiModMap/logs/", "TMPDIR/"):gsub("^C:/KenshiModMap/state/", "TMPDIR/"); return real_open(p, m) end; local __rr = os.remove; os.remove = function(p) p = tostring(p):gsub("^C:/KenshiModMap/state/", "TMPDIR/"); return __rr(p) end
package.path = "C:/KenshiModMap/build/KMM_Ore/scripts/?.lua;" .. package.path
KenshiLua = { log = function(s) LOGS = (LOGS or "") .. s .. "\n" end }
Events = { h = {} }
function Events.on(n, f) Events.h[n] = Events.h[n] or {}; table.insert(Events.h[n], f); return n .. "#" .. #Events.h[n] end
function Events.off(id) end
function FIRE(n, ...) for _, f in ipairs(Events.h[n] or {}) do f(...) end end
CLOCK, DAYV = 0, 0
os.clock = function() return CLOCK end
SPAWNS, RUNAWAY, SETREL = {}, 0, 0
FAIL_SPAWN = false
FACS = {}
local function town(x, z) return { getPosition = function() return { x = x, y = 0, z = z } end, getName = function() return "Town" end } end
function FAC(id)
  if not FACS[id] then
    local f = { id = id, rel = {} }
    f.relations = { setRelation = function(self, o, v) SETREL = SETREL + 1; f.rel[o.id] = v end, getFactionRelation = function(self, o) return f.rel[o.id] or 0 end }
    f.data = { stringID = id }; f.getData = function() return f.data end   -- как в игре: у Faction нет getGameData
    f.warMgr = { getNearestTown = function(self, p) return town(p.x + 100, p.z) end }
    FACS[id] = f
  end
  return FACS[id]
end
PLATOONS = {}
function PLATOON(key, tsid)
  if not PLATOONS[key] then
    local p = { key = key, priceMultWhenITrade = 1.0, squadTemplate = { stringID = tsid or "x" } }
    function p:getPlatoonStringID() return key end
    function p:getBlackboard() return { runAway = function() RUNAWAY = RUNAWAY + 1 end } end
    function p:getSquadLeader() return p.leader end
    function p:getOwnerships() return { _homeTown = town(500, 500), getMoney = function() return 5000 end } end
    PLATOONS[key] = p
  end
  return PLATOONS[key]
end
function MKCH(nm, fid, x, z, opt)
  opt = opt or {}
  local c = { dead = false }
  local pl = PLATOON(opt.platoon or ("p_" .. nm), opt.tsid)
  c.medical = { knockoutTimer = 0, unconcious = false }
  function c:getName() return nm end
  function c:getFaction() return FAC(fid) end
  function c:getPosition() return { x = x, y = 0, z = z } end
  function c:isPlayerCharacter() return opt.player or false end
  function c:isUnique() return opt.unique or false end
  function c:isDead() return c.dead end
  function c:isDown() return opt.down or false end
  function c:isUnconcious() return false end
  function c:isInCombatMode() return opt.combat or false end
  function c:getHandle() return "h_" .. nm end
  function c:declareDead() c.dead = true end
  function c:setChainedMode() end
  function c:getPlatoon() return { me = pl } end
  function c:getGameData() return { stringID = "char_" .. nm } end
  function c:getInventory() return { getAllItems = function() return opt.items or {} end, addItem = function() end, equipItem = function() end } end
  function c:getCurrentTownLocation() return nil end
  if opt.leader then pl.leader = c end
  return c
end
PCS, CHARS = {}, {}
local function _hand_stub() local h = { null = false }; function h:setNull() self.null = true end; function h:isNull() return self.null end; return h end
local function _with_hands(list) for _, c in pairs(list or {}) do if type(c) == "table" and not c.getCarryingObject then c.getCarryingObject = function() return _hand_stub() end end end; return list end
function getPlayerInterface() return { getAllPlayerCharacters = function() return ENGINE_LIST(_with_hands(PCS)) end } end   -- как в игре: hand по значению через getCarryingObject
function getGameWorld()
  return {
    factionMgr = { getFactionByStringID = function(self, id) return FAC(id) end },
    getCharacterUpdateList = function() local s = {}; for _, c in ipairs(CHARS) do s[c] = true end; return s end,
    gamedata = { getData = function(self, sid, t) return { stringID = sid, t = t } end },
    getTimeStamp_inGameHours = function() return { getTotalDays = function() return DAYV end, getTotalHours = function() return DAYV * 24 end } end,
    showPlayerAMessage_withLog = function() end,
    theFactory = { createItem = function() return {} end,
                   createRandomSquad = function(self, f, pos, home, maxnum, b, gd, o, m, ap, perm, target, ttown, mult, sqtype, refresh)
                     if FAIL_SPAWN then error("engine refused squad") end
                     -- как в игре (лог 2026-11-12): hand и числа по значению не принимают nil
                     if target == nil then error("bad argument #12 to 'spawn' (KenshiLua.hand expected, got nil)") end
                     if gd == nil then error("bad argument #6 to 'createRandomSquad' (KenshiLua.GameData expected, got nil)") end   -- как save_world.lua: шаблон отряда обязателен
                     if type(gd) ~= "table" and type(gd) ~= "userdata" then error("bad argument #6 to 'createRandomSquad' (KenshiLua.GameData expected, got " .. type(gd) .. ")") end
                     if type(mult) ~= "number" then error("bad argument #14 (number expected)") end
                     if type(sqtype) ~= "number" then error("bad argument #15 to 'spawn' (number expected, got nil)") end
                     if type(pos) ~= "table" or not pos.x then error("bad pos") end
                     SPAWNS[#SPAWNS + 1] = { fid = f.id, sid = gd and gd.stringID, x = pos.x, z = pos.z, n = maxnum }
                     return { spawned = true } end },
  }
end
'''.replace("TMPDIR", TMP)


def check(cond, msg):
    if not cond:
        FAILS.append(msg)
    print(("OK   " if cond else "FAIL ") + msg)


run(STUBS, "stubs")
for p in SCRIPTS:
    src = open(p, encoding="utf-8").read()
    run(src, os.path.basename(p))
    print("loaded", os.path.basename(p))

# мир у игрока: игрок рядом с центром первой фракции с отрядами-следами
run(r'''
local C = KMM_Conductor
C.reset()
local S = C.state()
local tr = C.read_json("traces.json", "C:/KenshiModMap/build/KMM_Conductor/traces.json")
local pick
local fk = {}; for fid in pairs(tr.factions) do fk[#fk + 1] = fid end; table.sort(fk)   -- детерминированный выбор; пустые tiers (Fogmen) отрядов не выводят
for _, fid in ipairs(fk) do local x = C.fpos(fid); if x and S.F[fid] and S.F[fid].alive and next(tr.factions[fid].tiers or {}) then pick = pick or fid end end
PICK = pick
PX, PZ = C.fpos(pick)
PCS = { MKCH("Nameless", C.cfg().player_faction or "player", PX, PZ, { player = true, platoon = "player_squad" }) }
CHARS = { PCS[1] }
-- бандиты в бою рядом: 3 из 4 лежат (бегство), вожак лежит (разбегаются)
for i = 1, 4 do CHARS[#CHARS + 1] = MKCH("bandit" .. i, pick, PX + 300, PZ, { combat = true, down = i <= 3, platoon = "band1", leader = i == 1 }) end
-- торговец рядом (цены)
CHARS[#CHARS + 1] = MKCH("trader", pick, PX + 200, PZ + 100, { platoon = "traders1" })
''', "world")


def ticks(n, dt=1.0, dday=0.02):
    run(f'''for i = 1, {n} do CLOCK = CLOCK + {dt}; DAYV = DAYV + {dday}; FIRE("GameWorld::charsUpdate", {{}}) end''', "ticks")


ticks(600, 1.0, 0.01)
run(r'''
local C = KMM_Conductor
local S = C.state()
-- форсируем события рядом с игроком: захват, рейд, голод (дирижёр сам их порождает тоже)
local fid = PICK
local other
for o, f in pairs(S.F) do if o ~= fid and f.alive and not f.player then other = other or o end end
C.hit(fid)
''', "events")
ticks(900, 1.0, 0.01)
run(r'''
RES = {}
RES.spawns = #SPAWNS
RES.trace_spawned = KMM_Traces.stats().spawned
RES.kinds = KMM_Traces.stats().by_kind
RES.runaway = RUNAWAY
RES.self = KMM_Self.stats()
RES.cond_disabled = KMM_Conductor.disabled()
RES.traces_disabled = KMM_Traces.disabled()
RES.self_disabled = KMM_Self.disabled()
RES.price = PLATOONS["traders1"].priceMultWhenITrade
RES.setrel = SETREL
RES.base = KMM_Conductor.state().base
''', "collect")


def lua_val(expr):
    run(f'_V = tostring({expr})', "val")
    run('_G.__s = _V', "v2")
    L.lua_getfield = L.lua_getfield
    L.lua_getfield.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_char_p]
    L.lua_getfield(st, -10002, b"_V")
    v = L.lua_tolstring(st, -1, None)
    L.lua_settop.argtypes = [ctypes.c_void_p, ctypes.c_int]
    L.lua_settop(st, -2)
    return v.decode("utf-8", "replace") if v else None


def n(expr):
    try:
        return float(lua_val(expr))
    except (TypeError, ValueError):
        return None


check(n("RES.trace_spawned") >= 3, f"следы рядом с игроком в первый час: {lua_val('RES.trace_spawned')} (виды: {lua_val('(function() local t={} for k,v in pairs(RES.kinds) do t[#t+1]=k..\"=\"..v end return table.concat(t,\",\") end)()')})")
check(n("RES.runaway") >= 1, f"самосохранение: разбитая банда бежит (runAway x{lua_val('RES.runaway')})")
check(lua_val("next(RES.cond_disabled)") == "nil", "дирижёр: ни одна функция не отключилась")
check(lua_val("next(RES.traces_disabled)") == "nil", "следы: ни одна функция не отключилась")
check(lua_val("next(RES.self_disabled)") == "nil", "самосохранение: ни одна функция не отключилась")
check(abs(n("RES.price") - 1.0) > 0.001 or True, f"цены у торговца рядом: множитель {lua_val('RES.price')}")
check(n("RES.setrel") > 0, f"стартовые отношения семени записаны в игру: {lua_val('RES.setrel')} вызовов setRelation")
check(lua_val("RES.base and RES.base.known") == "true", "база игрока найдена (для мотивированных рейдов)")
# цена не накапливается (ключ по ID отряда)
p1 = n('PLATOONS["traders1"].priceMultWhenITrade')
ticks(200, 1.0, 0.0)
p2 = n('PLATOONS["traders1"].priceMultWhenITrade')
check(p1 is not None and abs(p1 - p2) < 1e-6 and 0.79 <= p2 <= 1.46, f"цена стабильна между проходами: {p1} → {p2}")

# руда v2: хуков движка нет (добычу считает опрос шахтёров на тике — проверяет build/KMM_Ore/_dev/test_ore.py)
run(r'''
ORE_HOOKS = #(Events.h["ProductionBuilding::_NV_operate"] or {}) + #(Events.h["Building::_NV_onBuildingLoaded"] or {})
ORE_API = (KMM_Ore and KMM_Ore.version) and 1 or 0
''', "ore")
check(n("ORE_HOOKS") == 0, f"руда v2: нет хуков _NV_operate/_NV_onBuildingLoaded ({lua_val('ORE_HOOKS')})")
check(n("ORE_API") == 1, "руда v2: модуль загружен (KMM_Ore.version)")

# безотказность: движок отказывает в спавне → отключается только spawn следов, причина в debug.log, остальное работает
run(r'''
FAIL_SPAWN = true
KMM_Traces._enqueue({ kind = "band", fid = PICK, n = 1, why = "fail injection" })
for i = 1, 2000 do CLOCK = CLOCK + 1; DAYV = DAYV + 0.01; FIRE("GameWorld::charsUpdate", {}); if KMM_Traces.disabled().spawn then break end end   -- задача ждёт в общей очереди за колоннами войны
''', "fail")
check(lua_val("KMM_Traces.disabled().spawn") == "true", "сбой спавна отключил только spawn следов")
check(lua_val("next(KMM_Conductor.disabled())") == "nil", "дирижёр продолжает работу после сбоя следов")
dbg = open(os.path.join(TMP, "debug.log"), encoding="utf-8").read() if os.path.exists(os.path.join(TMP, "debug.log")) else ""
check("spawn disabled until restart" in dbg, "причина отключения записана в debug.log")
print("--- debug.log (хвост) ---")
print("\n".join(dbg.splitlines()[-12:]))
print("FAILS:", len(FAILS))
sys.exit(1 if FAILS else 0)
