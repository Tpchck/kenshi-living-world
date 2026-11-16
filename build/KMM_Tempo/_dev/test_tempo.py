"""Офлайн-тест KMM_Tempo v1 на LuaJIT из KenshiLua (lua51.dll) с заглушками API игры. Без игры, без сети, < 5 с.
python -I -X utf8 build/KMM_Tempo/_dev/test_tempo.py
Пути C:/KenshiModMap/logs/ перенаправляются во временную папку — реальные логи не трогаются."""
import ctypes
import os
import sys
import tempfile

DLL = r"C:\Program Files (x86)\Steam\steamapps\workshop\content\233860\3817000612\lua51.dll"
SCRIPT = "C:/KenshiModMap/build/KMM_Tempo/scripts/init/kmm_tempo.lua"
GOV = "C:/KenshiModMap/build/KMM_Conductor/scripts/init/KMM_Gov.lua"

L = ctypes.CDLL(DLL)
L.luaL_newstate.restype = ctypes.c_void_p
L.luaL_openlibs.argtypes = [ctypes.c_void_p]
L.luaL_loadstring.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
L.luaL_loadfile.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
L.lua_pcall.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int]
L.lua_tolstring.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p]
L.lua_tolstring.restype = ctypes.c_char_p
L.lua_settop.argtypes = [ctypes.c_void_p, ctypes.c_int]
L.lua_close.argtypes = [ctypes.c_void_p]

STUBS = r"""
TMP = "%(tmp)s"
OPEN_LOG, LOGS, REG = {}, {}, {}
API_CALLS = 0
local real_open = io.open
io.open = function(p, m)
  OPEN_LOG[#OPEN_LOG + 1] = tostring(p) .. "|" .. tostring(m)
  p = tostring(p):gsub("^C:/KenshiModMap/logs/", TMP .. "/")
  return real_open(p, m)
end
function read_tmp(name) local f = real_open(TMP .. "/" .. name, "r"); if not f then return nil end; local s = f:read("*a"); f:close(); return s end
REAL_CLOCK = os.clock
CLOCK, HOURS = 100, 240.0          -- HOURS: игровые часы (getTotalDays()*24)
os.clock = function() return CLOCK end
KenshiLua = { log = function(s) LOGS[#LOGS + 1] = s end }
Events = { h = {}, n = 0 }
function Events.on(name, f) Events.n = Events.n + 1; Events.h[name] = f; REG[#REG + 1] = name; return Events.n end
local ts = { getTotalDays = function() return HOURS / 24 end }
local gw = { getTimeStamp_inGameHours = function() return ts end,
  gamedata = { getData = function(self, sid, ty) return { sid = sid } end },
  theFactory = { createItem = function(self, gd) return { gd = gd, isFood = function() return true end } end } }
package.path = "C:/KenshiModMap/build/KMM_Stock/scripts/?.lua;" .. package.path
function getGameWorld() API_CALLS = API_CALLS + 1; return gw end
PCS = {}
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
local pi = { getAllPlayerCharacters = function() return ENGINE_LIST(PCS) end }
function getPlayerInterface() API_CALLS = API_CALLS + 1; return pi end

-- игрок: speed (getMovementSpeed), orders (0/1/2), вес, множитель ран
function mkplayer(name)
  local c = { name = name, speed = 0, orders = 0, weight = 0, inj = 1.0, stats = { moveSpeed = 10.0 }, med = { hunger = 100 } }
  function c:getHandle() return setmetatable({}, { __tostring = function() return self.name end }) end
  function c:isDead() return false end
  function c:getMovementSpeed() return self.speed end
  function c:getMovementSpeedOrders() return self.orders end
  function c:getInventory() local w = self.weight; return { getTotalWeight = function() return w end } end
  function c:getMedical() local i = self.inj; local m = self.med; m.getMovementSpeedInjuryMultiplier = function() return i end; return m end
  function c:getStats() return self.stats end
  return c
end
function mkplatoon(orig) return { speedOverride = orig == nil and 2 or orig } end
-- снимок Gov-формата: by_pkey[ключ] = { rec... }
SNAP = nil
function snap_add(key, pl, n, flags)
  SNAP = SNAP or { n = 0, list = {}, by_pkey = {}, players = 0 }
  local ap = { me = pl, isPlayer = (flags and flags.player) and true or false }
  local recs = {}
  for i = 1, n do
    recs[i] = { ch = {}, ap = ap, pl = pl, pkey = key, dead = false, down = false,
                combat = (flags and flags.combat and i == 1) or false, town = (flags and flags.town) and {} or false }
  end
  SNAP.by_pkey[key] = recs
end
-- HUNGER: человек из заглушек. o: hunger, slave(0/1), owner(true=жив), money, food(шт.)
function mkhuman(name, o)
  o = o or {}
  local med = { hunger = o.hunger or 300, blood = 100 }
  function med:pointOfNoReturn() return 40 end
  local inv = { items = {} }
  function inv:getAllItems() return self.items end
  function inv:hasRoomForItem() return true end
  function inv:addItem(it) self.items[#self.items + 1] = it; return true end
  for _ = 1, (o.food or 0) do inv:addItem({ isFood = function() return true end }) end
  local c = { name = name, med = med, inv = inv, money = o.money or 0 }
  function c:getHandle() return name end
  function c:getMedical() return med end
  function c:getInventory() return inv end
  function c:amSomeoneWhoNeedsToEatToLive() return true end
  function c:isAnimal() return false end
  function c:isPlayerCharacter() return false end
  function c:isSlave() return o.slave or 0 end
  function c:getMySlaveOwner() if o.owner then return { isDead = function() return false end } end end
  function c:getNumFoodItems() return #inv.items end
  function c:eatItem(it, from) table.remove(inv.items, 1); med.hunger = math.min(300, med.hunger + 135); return true end
  function c:getStats() return { calculateHungerMult = function() return 1 end } end
  function c:getOwnerships() local me = self; return { getMoney = function() return me.money end, addMoney = function(_, v) me.money = me.money + v end,
    setMoney = function(_, v) if not me.money_ro then me.money = v end end } end
  function c:getFaction() return { getName = function() return "Slavers" end, getProsperityMultiplier = o.prosp and function() return o.prosp end or nil } end
  function c:declareDead() self.dead = true end
  function c:isDead() return self.dead or med.blood < 100 end
  return c
end
STOCK = { towns = { T1 = { q = { food = 50 }, tn = { food = 100 } }, T2 = { q = { food = 50 }, tn = { food = 100 } } } }
SPENT, EVENTS = 0, {}
KMM_Conductor = {
  stock_state = function() return STOCK end,
  stock_spend = function(sid, cat, share) local s = STOCK.towns[sid]; local x = math.min(s.q[cat], s.tn[cat] * share); s.q[cat] = s.q[cat] - x; SPENT = SPENT + x; return x end,
  emit = function(ev) EVENTS[#EVENTS + 1] = ev end,
  cfg = function() return { town_info = { T1 = { name = "Town One" }, T2 = { name = "Town Two" } } } end }
-- запись снимка с персонажем; f: town ("T1"), unique, trader, player
function snap_char(ch, f)
  f = f or {}
  SNAP = SNAP or { n = 0, list = {}, by_pkey = {}, players = 0 }
  local rec = { ch = ch, h = ch.name, ap = { isPlayer = f.player or false }, dead = false, down = false, combat = false,
                unique = f.unique or false, trader = f.trader or false, town = f.town and { data = { stringID = f.town } } or false }
  SNAP.list[#SNAP.list + 1] = rec; SNAP.n = SNAP.n + 1
  return rec
end
function load_gov() dofile("%(gov)s"); KMM_Gov.snapshot = function() return SNAP end end
function TICK(n, dclock, dhours)
  for _ = 1, n do
    CLOCK = CLOCK + (dclock or 1); HOURS = HOURS + (dhours or 0)
    Events.h["GameWorld::charsUpdate"]({})
  end
end
function warm() PCS = PCS; TICK(12, 1, 0.01) end
function count(t) local k = 0; for _ in pairs(t) do k = k + 1 end; return k end
"""


class Lua:
    def __init__(self, tmp):
        self.st = L.luaL_newstate()
        L.luaL_openlibs(self.st)
        self.run(STUBS % {"tmp": tmp, "gov": GOV}, "stubs")

    def run(self, code, name="chunk"):
        rc = L.luaL_loadstring(self.st, code.encode("utf-8")) or L.lua_pcall(self.st, 0, 0, 0)
        if rc:
            msg = L.lua_tolstring(self.st, -1, None)
            L.lua_settop(self.st, 0)
            raise AssertionError(f"{name}: {msg.decode('utf-8', 'replace') if msg else rc}")

    def load_module(self):
        self.run(f'dofile("{SCRIPT}")', "load kmm_tempo.lua")
        self.run('KMM_Tempo.cfg.road_pace = true', "road_pace on for NPC cases (по умолчанию дорога = ваниль)")

    def close(self):
        L.lua_close(self.st)


def compile_only(path):
    st = L.luaL_newstate()
    rc = L.luaL_loadfile(st, path.encode("utf-8"))
    msg = L.lua_tolstring(st, -1, None) if rc else None
    L.lua_close(st)
    if rc:
        raise AssertionError(f"syntax {path}: {msg.decode('utf-8', 'replace')}")


RESULTS = []
CASES = []


def case(name):
    def deco(fn):
        def wrapped():
            tmp = tempfile.mkdtemp(prefix="kmm_tempo_").replace("\\", "/")
            lua = Lua(tmp)
            try:
                fn(lua, tmp)
                RESULTS.append((name, True, ""))
            except AssertionError as e:
                RESULTS.append((name, False, str(e)))
            finally:
                lua.close()
        wrapped.__name__ = fn.__name__
        CASES.append(wrapped)
        return wrapped
    return deco


@case("syntax: kmm_tempo.lua компилируется (LuaJIT KenshiLua)")
def t_syntax(lua, tmp):
    compile_only(SCRIPT)


@case("загрузка: только charsUpdate, ни I/O, ни API игры; до появления персонажей тишина")
def t_load(lua, tmp):
    lua.load_module()
    lua.run("""
      assert(#REG == 1 and REG[1] == "GameWorld::charsUpdate", "registered: " .. table.concat(REG, ","))
      assert(#OPEN_LOG == 0 and API_CALLS == 0, "work at load")
      PCS = {}
      TICK(100, 1, 0.05)
      assert(KMM_Tempo.status().ready == false and #OPEN_LOG == 0, "idle without chars")
    """)


@case("усталость: бег копит, шаг/стоянка снимают, трусца почти нейтральна; эффект <= 15%")
def t_fatigue(lua, tmp):
    lua.load_module()
    lua.run("""
      local p = mkplayer("A"); PCS = { p }
      warm(); assert(KMM_Tempo.status().ready, "ready")
      local function fat() return KMM_Tempo.fatigue()["A"] end
      p.speed, p.orders = 5, 2
      TICK(10, 1, 0.1)                      -- 1 игровой час бега
      local f1 = fat(); assert(f1 > 0.2 and f1 < 0.4, "1h run f=" .. f1)
      TICK(40, 1, 0.1)                      -- ещё 4 часа
      assert(fat() > 0.95, "saturates: " .. fat())
      local mult = p.stats.moveSpeed / 10.0
      assert(mult >= 0.85 - 1e-9 and mult < 0.9, "slow within cap: " .. mult)
      p.orders = 1; local before = fat(); TICK(10, 1, 0.1)
      assert(math.abs(fat() - before) < 0.1, "jog neutral: " .. before .. " -> " .. fat())
      p.orders = 0; TICK(30, 1, 0.1)         -- 3 ч ходьбы
      assert(fat() < 0.5, "walk recovers: " .. fat())
      assert(math.abs(p.stats.moveSpeed - 10.0) < 1e-6, "speed restored: " .. p.stats.moveSpeed)
      for _, f in ipairs({0, 0.3, 0.5, 0.75, 1}) do assert(KMM_Tempo.slow_mult(f) >= 0.85 - 1e-9, "cap at " .. f) end
      KMM_Tempo.cfg.slow_max = 0.9; assert(KMM_Tempo.slow_mult(1) >= 0.85 - 1e-9, "hard cap ignores cfg")
    """)


@case("вес и раны ускоряют накопление; пауза (dt=0) и x1/x5 согласованы по игровому времени")
def t_weight_time(lua, tmp):
    lua.load_module()
    lua.run("""
      local a, b = mkplayer("A"), mkplayer("B")
      b.weight, b.inj = 80, 0.5
      for _, p in ipairs({a, b}) do p.speed, p.orders = 5, 2 end
      PCS = { a, b }; warm()
      TICK(10, 1, 0.05)
      local fa, fb = KMM_Tempo.fatigue()["A"], KMM_Tempo.fatigue()["B"]
      assert(fb > fa * 1.8, "loaded+wounded faster: " .. fa .. " vs " .. fb)
      TICK(20, 1, 0)                         -- пауза: игровое время стоит
      assert(math.abs(KMM_Tempo.fatigue()["A"] - fa) < 1e-9, "pause no change")
      -- тот же игровой час: 10 тиков по 0.1 ч (медленно) и 2 тика по 0.5 ч (x5, реже) -> одинаково
      local lua_a = KMM_Tempo.fatigue()["A"]
      TICK(10, 1, 0.1); local f_slow = KMM_Tempo.fatigue()["A"] - lua_a
      lua_a = KMM_Tempo.fatigue()["A"]
      TICK(2, 1, 0.5); local f_fast = KMM_Tempo.fatigue()["A"] - lua_a
      assert(math.abs(f_slow - f_fast) < 0.02, "x1 vs x5: " .. f_slow .. " " .. f_fast)
    """)


@case("самоотключение: нет CharStats.moveSpeed -> player_slow выкл., fatigue жива; лог")
def t_no_field(lua, tmp):
    lua.load_module()
    lua.run("""
      local p = mkplayer("A"); p.stats = {}; PCS = { p }; warm()
      p.speed, p.orders = 5, 2
      TICK(10, 1, 0.1)
      local d = KMM_Tempo.status().disabled
      assert(d.player_slow and d.player_slow:find("moveSpeed"), "slow disabled")
      assert(not d.player_fatigue and KMM_Tempo.fatigue()["A"] > 0.2, "fatigue alive")
      local lg = read_tmp("tempo.log"); assert(lg and lg:find("DISABLED player_slow"), "logged")
    """)


@case("самоотключение: запись moveSpeed не применилась (движок игнорирует) -> выкл., база возвращена")
def t_write_ignored(lua, tmp):
    lua.load_module()
    lua.run("""
      local p = mkplayer("A")
      p.stats = setmetatable({}, { __index = function(_, k) if k == "moveSpeed" then return 10.0 end end, __newindex = function() end })
      PCS = { p }; warm(); p.speed, p.orders = 5, 2
      TICK(60, 1, 0.1)
      assert(KMM_Tempo.status().disabled.player_slow, "disabled on ignored write")
    """)


@case("голод: по умолчанию выключен; включённый, при отсутствии поля выключается сам")
def t_hunger(lua, tmp):
    lua.load_module()
    lua.run("""
      local p = mkplayer("A"); PCS = { p }; warm(); p.speed, p.orders = 5, 2
      TICK(60, 1, 0.1)
      assert(p.med.hunger == 100, "hunger untouched by default")
      KMM_Tempo.cfg.hunger_extra = 10
      TICK(5, 1, 0.1)
      assert(p.med.hunger < 100, "hunger drained: " .. p.med.hunger)
      p.med.hunger = nil; TICK(3, 1, 0.1)
      assert(KMM_Tempo.status().disabled.player_hunger, "hunger disabled without field")
    """)


@case("NPC: город -> шаг, дорога -> трусца, бой/игрок -> ваниль, возврат исходного; ваниль-шаг не трогаем")
def t_npc(lua, tmp):
    lua.load_module()
    lua.run("""
      load_gov()
      PCS = { mkplayer("A") }; warm()
      local pt, pr, pc, pp, pw = mkplatoon(2), mkplatoon(2), mkplatoon(2), mkplatoon(2), mkplatoon(0)
      snap_add("t", pt, 3, { town = true }); snap_add("r", pr, 3); snap_add("c", pc, 3, { combat = true })
      snap_add("p", pp, 2, { player = true }); snap_add("w", pw, 2)
      TICK(4, 3, 0.01)
      assert(pt.speedOverride == 0, "town WALK: " .. pt.speedOverride)
      assert(pr.speedOverride == 1, "road JOG: " .. pr.speedOverride)
      assert(pc.speedOverride == 2 and pp.speedOverride == 2, "combat/player untouched")
      assert(pw.speedOverride == 0, "vanilla walk stays")
      SNAP.by_pkey.r[1].combat = true; TICK(4, 3, 0.01)
      assert(pr.speedOverride == 2, "combat restores original: " .. pr.speedOverride)
      SNAP.by_pkey.r[1].combat = false; SNAP.by_pkey.t[2].town = false; TICK(4, 3, 0.01)
      assert(pr.speedOverride == 1 and pt.speedOverride == 0, "back to pace")
      SNAP.by_pkey.t = nil; TICK(4, 3, 0.01)       -- платун выгружен: его не трогаем и забываем
      assert(KMM_Tempo._rt.npc.t == nil, "forgotten")
      local s = KMM_Tempo.status(); assert(not next(s.disabled), "nothing disabled")
    """)


@case("NPC: нет снимка Gov -> тихо пропуск; нет поля speedOverride -> npc_pace выкл.")
def t_npc_off(lua, tmp):
    lua.load_module()
    lua.run("""
      load_gov(); PCS = { mkplayer("A") }; warm()
      SNAP = nil; TICK(10, 3, 0.01)
      assert(not KMM_Tempo.status().disabled.npc_pace, "no snapshot is not an error")
      snap_add("x", {}, 2); TICK(4, 3, 0.01)
      assert(KMM_Tempo.status().disabled.npc_pace or KMM_Tempo.status().paused.npc_pace, "disabled (or paused by KMM_Gov health) without speedOverride")
    """)


@case("бюджет: 300 отрядов, 300 тиков -> среднее на вызов < 0.6 мс (разрешение таймера ~15 мс, поэтому среднее по 300), троттлинга нет")
def t_budget(lua, tmp):
    lua.load_module()
    lua.run("""
      load_gov()
      local ps = {}
      for i = 1, 300 do ps[i] = mkplatoon(2); snap_add("k" .. i, ps[i], 4, { town = (i % 3 == 0) }) end
      local p = mkplayer("A"); p.speed, p.orders = 5, 2; PCS = { p }; warm()
      local t0 = REAL_CLOCK(); local worst = 0
      for _ = 1, 300 do
        CLOCK = CLOCK + 3; HOURS = HOURS + 0.01
        local a = REAL_CLOCK(); Events.h["GameWorld::charsUpdate"]({}); local d = REAL_CLOCK() - a
        if d > worst then worst = d end
      end
      local avg = (REAL_CLOCK() - t0) / 300
      assert(avg < 0.0006, string.format("avg %.3f ms", avg * 1000))
      -- пик не проверяем: разрешение os.clock в Windows ~15 мс, одиночный замер ничего не значит
      assert(KMM_Gov.stats().tempo.n == 1, "not throttled")
      assert(KMM_Tempo._rt.stats.npc_set >= 280, "all paced after sweeps: " .. KMM_Tempo._rt.stats.npc_set)
    """)


@case("по умолчанию дорога = ваниль (road_pace=false): бегущие/погоня не замедляются, город -> шаг")
def t_road_default(lua, tmp):
    lua.load_module()
    lua.run("""
      KMM_Tempo.cfg.road_pace = false
      load_gov()
      PCS = { mkplayer("A") }; warm()
      local pt, pr = mkplatoon(2), mkplatoon(2)
      snap_add("t", pt, 3, { town = true }); snap_add("r", pr, 3)
      TICK(4, 3, 0.01)
      assert(pt.speedOverride == 0, "town WALK: " .. pt.speedOverride)
      assert(pr.speedOverride == 2, "road untouched: " .. pr.speedOverride)
    """)


@case("сводка раз в игровые сутки в tempo.log")
def t_summary(lua, tmp):
    lua.load_module()
    lua.run("""
      local p = mkplayer("A"); p.speed, p.orders = 5, 2; PCS = { p }; warm()
      TICK(300, 1, 0.1)    -- 30 игровых часов
      local lg = read_tmp("tempo.log")
      assert(lg and lg:find("start v1") and lg:find("day %d+: max_fatigue"), "summary: " .. tostring(lg))
    """)


HUNGER_PRE = """
  load_gov(); PCS = { mkplayer("A") }; warm()
  KMM_Tempo._hg.cal = KMM_Tempo.cfg.hunger_dir      -- калибровка пройдена (отдельные тесты ниже)
"""


@case("голод: без ванильного расхода (магический голод) hunger падает со скоростью fed/starve_hours; еда горожанина со склада города")
def t_hunger_drain(lua, tmp):
    lua.load_module()
    lua.run(HUNGER_PRE + """
      local w = mkhuman("W", { hunger = 300 }); snap_char(w)
      local t = mkhuman("R", { hunger = 100 }); snap_char(t, { town = "T1" })
      TICK(2, 3, 1)
      TICK(20, 3, 1)
      local rate = 300 / KMM_Tempo.cfg.starve_hours
      assert(w.med.hunger < 300 - rate * 15 and w.med.hunger > 300 - rate * 25, "drain ~" .. rate * 20 .. ": " .. w.med.hunger)
      assert(t.med.hunger > 100 - rate * 25 and SPENT > 0 and STOCK.towns.T1.q.food < 50, "town meal from stock: h=" .. t.med.hunger .. " spent=" .. SPENT)
      assert(not next(KMM_Tempo.status().disabled), "nothing disabled")
    """)


@case("голод: ваниль уже тратит -> не удваиваем; поел сам (рост) -> не штрафуем")
def t_hunger_no_double(lua, tmp):
    lua.load_module()
    lua.run(HUNGER_PRE + """
      local w = mkhuman("W", { hunger = 300 }); snap_char(w)
      TICK(1, 3, 1)
      local rate = 300 / KMM_Tempo.cfg.starve_hours
      for _ = 1, 10 do w.med.hunger = w.med.hunger - rate; TICK(1, 3, 1) end
      assert(math.abs(w.med.hunger - (300 - rate * 10)) < rate * 1.5, "no double drain: " .. w.med.hunger)
      local before = w.med.hunger; w.med.hunger = before + 30; TICK(1, 3, 1)
      assert(w.med.hunger >= before + 30 - 1, "ate: not penalized " .. w.med.hunger)
    """)


@case("рабы: хозяин в зоне держит голод около «голоден, но жив» (slave_floor), не мрут; строка slaves fed by")
def t_hunger_slaves(lua, tmp):
    lua.load_module()
    lua.run(HUNGER_PRE + """
      local s = mkhuman("S", { hunger = 300, slave = 1, owner = true }); snap_char(s)
      TICK(2, 3, 1); TICK(130, 3, 1)
      local fl = KMM_Tempo.cfg.slave_floor * 300
      assert(s.med.hunger >= fl - 1 and s.med.hunger < fl + 30, "slave near floor " .. fl .. ": " .. s.med.hunger)
      assert(s.med.blood == 100 and not s.dead, "alive")
      TICK(30, 3, 1); assert(read_tmp("tempo.log"):find("slaves fed by Slavers"), "log line")
    """)


@case("смерть от голода: пустой склад города / раб без хозяина; лимит смертей на город и сутки; события; строки лога; вне города не мрут")
def t_hunger_starve(lua, tmp):
    lua.load_module()
    lua.run(HUNGER_PRE + """
      STOCK.towns.T1.q.food = 0
      local rs = {}
      for i = 1, 5 do rs[i] = mkhuman("R" .. i, { hunger = 10 }); snap_char(rs[i], { town = "T1" }) end
      local sl = mkhuman("SL", { hunger = 5, slave = 1, owner = false }); snap_char(sl)
      local w = mkhuman("WILD", { hunger = 5 }); snap_char(w)
      TICK(2, 3, 1); TICK(18, 3, 1)
      local dead = 0; for i = 1, 5 do if rs[i].med.blood < 100 then dead = dead + 1 end end
      assert(dead == 2, "town cap 2/day: " .. dead)
      assert(sl.med.blood < 100, "slave without owner starves")
      assert(w.med.blood == 100 and w.med.hunger >= KMM_Tempo.cfg.wild_floor * 300 - 1, "wild never dies")
      assert(#EVENTS == 3 and EVENTS[1].type == "hunger_starved", "events: " .. #EVENTS)
      local lg = read_tmp("tempo.log")
      assert(lg:find("HUNGER: npc starved in Town One") and lg:find("HUNGER: town food deficit Town One"), "log lines")
      assert(KMM_Tempo._hg.stats.starved == 3, "stats")
    """)


@case("безопасность: отряд игрока не тронут; уникальные/торговцы: запас раз в сутки, не мрут при пустом складе; касса торговца ведётся блоком till")
def t_hunger_protect(lua, tmp):
    lua.load_module()
    lua.run(HUNGER_PRE + """
      KMM_Tempo.cfg.eat_below = 0.1                      -- сначала срабатывает суточный паёк уникального, а не городская трапеза
      STOCK.towns.T1.q.food = 0
      local pl = mkhuman("PLAYERSQ", { hunger = 100 }); snap_char(pl, { player = true, town = "T1" })
      local un = mkhuman("UN", { hunger = 60, money = 10 }); snap_char(un, { unique = true, town = "T1" })
      local tr = mkhuman("TR", { hunger = 60, money = 0 }); snap_char(tr, { trader = true, town = "T2" })
      TICK(2, 3, 1)
      TICK(10, 3, 1)
      assert(pl.med.hunger == 100, "player squad untouched")
      assert(un.med.blood == 100 and un.med.hunger >= KMM_Tempo.cfg.prot_min * 300 - 1, "unique alive, floor: " .. un.med.hunger)
      assert(un.money == 10 and tr.money > 0, "R3: unique money untouched, trader till moves toward town wealth " .. un.money .. "/" .. tr.money)
      assert(#un.inv.items == 0, "empty city stock -> no free ration for unique")
      assert(#tr.inv.items >= 1 and #tr.inv.items <= 4, "trader got a modest supply: " .. #tr.inv.items)
      local sup = KMM_Tempo._hg.stats.supplies; local spent = SPENT
      TICK(5, 3, 1)
      assert(KMM_Tempo._hg.stats.supplies == sup and SPENT == spent, "supply once per day, not every tick")
      TICK(150, 3, 1)
      assert(KMM_Tempo._hg.stats.ate >= 2 and tr.med.hunger >= KMM_Tempo.cfg.prot_min * 300 - 1, "next day ration: " .. tr.med.hunger)
      for _ = 1, 200 do TICK(1, 3, 1) end
      assert(un.med.blood == 100 and tr.med.blood == 100 and pl.med.hunger == 100, "never starve")
      assert(not next(KMM_Tempo.status().disabled), "nothing disabled")
    """)


@case("голод: нет поля hunger -> функция выключается сама; остальное живо")
def t_hunger_off(lua, tmp):
    lua.load_module()
    lua.run(HUNGER_PRE + """
      for i = 1, 10 do local c = mkhuman("X" .. i); snap_char(c); c.med.hunger = nil end
      TICK(10, 3, 1)
      assert(KMM_Tempo.status().disabled.npc_hunger or KMM_Tempo.status().paused.npc_hunger, "disabled (or paused by KMM_Gov health) without field")
      assert(not KMM_Tempo.status().disabled.npc_pace and not KMM_Tempo.status().disabled.all, "others alive")
    """)


@case("бюджет голода: 1200 персонажей в снимке, 300 тиков -> среднее на вызов < 0.6 мс")
def t_hunger_budget(lua, tmp):
    lua.load_module()
    lua.run(HUNGER_PRE + """
      for i = 1, 1200 do snap_char(mkhuman("B" .. i, { hunger = 200 }), { town = (i % 2 == 0) and "T2" or nil }) end
      TICK(60, 3, 0.5)
      local t0 = REAL_CLOCK()
      for _ = 1, 300 do CLOCK = CLOCK + 3; HOURS = HOURS + 0.5; Events.h["GameWorld::charsUpdate"]({}) end
      local avg = (REAL_CLOCK() - t0) / 300
      assert(avg < 0.0006, string.format("avg %.3f ms", avg * 1000))
      assert(KMM_Tempo._hg.visits_total > 1000, "visited " .. KMM_Tempo._hg.visits_total)
    """)


@case("калибровка знака по игроку: убывающий hunger -> dir=-1, нарастающий -> dir=+1; еда (скачок) не сбивает в неверный вывод; игрок не тронут")
def t_cal(lua, tmp):
    lua.load_module()
    lua.run("""
      load_gov(); local p = mkplayer("A"); p.med.hunger = 250; PCS = { p }; warm()
      KMM_Tempo.cfg.hunger_dir = 1                                  -- заведомо неверный знак
      assert(KMM_Tempo._hg.cal == nil, "pending")
      for i = 1, 5 do p.med.hunger = p.med.hunger - 2; TICK(1, 1, 0.1) end
      p.med.hunger = p.med.hunger + 100; TICK(1, 1, 0.1)             -- поел: сброс наблюдения
      assert(KMM_Tempo._hg.cal == nil, "eating resets")
      for i = 1, 15 do p.med.hunger = p.med.hunger - 2; TICK(1, 1, 0.1) end   -- ~1.5 ч убывания
      assert(KMM_Tempo._hg.cal == -1 and KMM_Tempo.cfg.hunger_dir == -1, "calibrated falling: " .. tostring(KMM_Tempo._hg.cal))
      assert(read_tmp("tempo.log"):find("HUNGER calibrated dir=%-1 from player"), "log")
    """)
    lua2 = Lua(tempfile.mkdtemp(prefix="kmm_tempo_").replace("\\", "/"))
    try:
        lua2.load_module()
        lua2.run("""
          load_gov(); local p = mkplayer("A"); p.med.hunger = 20; PCS = { p }; warm()
          for i = 1, 15 do p.med.hunger = p.med.hunger + 3; TICK(1, 1, 0.1) end
          assert(KMM_Tempo._hg.cal == 1 and KMM_Tempo.cfg.hunger_dir == 1, "calibrated rising: " .. tostring(KMM_Tempo._hg.cal))
          assert(p.med.hunger == 20 + 45, "player read only")
        """)
    finally:
        lua2.close()


@case("до калибровки: мягкий режим — расход не ниже середины шкалы, ни смертей, ни кормления рабов, ни защиты; лог calibration pending")
def t_cal_soft(lua, tmp):
    lua.load_module()
    lua.run("""
      load_gov(); PCS = { mkplayer("A") }; warm()
      STOCK.towns.T1.q.food = 0
      local rs = {}
      for i = 1, 4 do rs[i] = mkhuman("R" .. i, { hunger = 200 }); snap_char(rs[i], { town = "T1" }) end
      local sl = mkhuman("SL", { hunger = 200, slave = 1, owner = false }); snap_char(sl)
      local un = mkhuman("UN", { hunger = 200 }); snap_char(un, { unique = true, town = "T1" })
      TICK(2, 3, 1); TICK(80, 3, 1)
      for i = 1, 4 do assert(rs[i].med.blood == 100 and rs[i].med.hunger >= 0.5 * 300 - 1 - 5 and rs[i].med.hunger <= 200, "soft " .. rs[i].med.hunger) end
      assert(sl.med.blood == 100 and sl.med.hunger >= 0.5 * 300 - 6, "slave soft")
      assert(#EVENTS == 0 and KMM_Tempo._hg.stats.starved == 0, "no deaths before calibration")
      assert(un.money == 0 and SPENT == 0, "no protection/feeding writes before calibration")
      assert(read_tmp("tempo.log"):find("HUNGER calibration pending"), "pending logged")
    """)


@case("рабство: убыль рабов фракции >= порога за K суток -> событие slave_caravan + метка спроса; кулдаун; без убыли - нет")
def t_slave_caravan(lua, tmp):
    lua.load_module()
    lua.run(HUNGER_PRE + """
      local V = KMM_Tempo._hg.slv; KMM_Tempo.cfg.death_cap_town = 10
      -- нет убыли: сутки идут, ничего нет
      HOURS = HOURS + 24; TICK(3, 3, 0.1)
      for _ = 1, 3 do HOURS = HOURS + 24; TICK(2, 3, 0.1) end
      assert(V.emitted == 0 and next(KMM_Tempo.slave_demand()) == nil, "no loss no demand")
      -- убыль: 3 раба без хозяина мрут от голода
      local sl = {}
      for i = 1, 3 do sl[i] = mkhuman("SL" .. i, { hunger = 5, slave = 1, owner = false }); snap_char(sl[i]) end
      TICK(2, 3, 1); TICK(18, 3, 1)
      local dead = 0; for i = 1, 3 do if sl[i].med.blood < 100 then dead = dead + 1 end end
      assert(dead == 3, "slaves starved " .. dead)
      HOURS = HOURS + 24; TICK(3, 3, 0.1)
      assert(V.emitted == 1, "one caravan request: " .. V.emitted)
      local ev; for _, e in ipairs(EVENTS) do if e.type == "slave_caravan" then ev = e end end
      assert(ev and ev.n == 3 and ev.fid and ev.text:find("lost 3 slaves"), "event")
      local d = KMM_Tempo.slave_demand(); local k = next(d)
      assert(k and d[k].n == 3, "demand mark")
      assert(read_tmp("tempo.log"):find("SLAVES: demand"), "log")
      -- кулдаун: ещё убыль в пределах cd не даёт второй заявки
      for i = 1, 3 do local x = mkhuman("SM" .. i, { hunger = 5, slave = 1, owner = false }); snap_char(x) end
      TICK(2, 3, 1); TICK(18, 3, 1)
      HOURS = HOURS + 24; TICK(3, 3, 0.1)
      assert(V.emitted == 1, "cooldown: " .. V.emitted)
      -- метка спроса истекает
      for _ = 1, 5 do HOURS = HOURS + 24; TICK(2, 3, 0.1) end
      assert(next(KMM_Tempo.slave_demand()) == nil, "demand expires")
    """)

# ---------------------------------------------------------------- R3: касса торговца = богатство города
TILL_PRE = """
  load_gov(); PCS = { mkplayer("A") }; warm()
  local function flat(v) return { lux = v, metal = v, weapons = v, armor = v, med = v, drugs = v } end
  FLAT = flat
  MOOD = { T1 = { pop = 100, pop0 = 100, unrest = 0, food = 1.0 }, T2 = { pop = 100, pop0 = 100, unrest = 0, food = 1.0 } }
  KMM_Conductor.town_mood = function(sid) return MOOD[sid] end
  STK = { T1 = { city = true, siege = false }, T2 = { city = false, siege = false } }
  LVL = { T1 = flat(1), T2 = flat(1) }
  KMM_Stock = { stock = function(sid) return STK[sid] end, level = function(sid, c) return LVL[sid] and LVL[sid][c] end }
  function DAY(n) for _ = 1, n do HOURS = HOURS + 24; TICK(3, 3, 0.01) end end
"""


@case("R3 касса: разграбленный/голодный/осаждённый город беднеет плавно до «нет денег», процветающий торговый — богатеет; раз в сутки")
def t_till_rich_poor(lua, tmp):
    lua.load_module()
    lua.run(TILL_PRE + """
      MOOD.T2 = { pop = 40, pop0 = 100, unrest = 0.8, food = 0.05 }; STK.T2.siege = true
      LVL.T1 = FLAT(2.0)
      local rich = mkhuman("RICH", { money = 8000 }); snap_char(rich, { trader = true, town = "T1" })
      local poor = mkhuman("POOR", { money = 4000 }); snap_char(poor, { trader = true, town = "T2" })
      TICK(3, 3, 0.01)
      local r1, p1 = rich.money, poor.money
      assert(p1 < 4000 and p1 > 3000, "visit: smooth step down, not a jump: " .. p1)
      assert(r1 > 8000 and r1 < 9500, "visit: smooth step up: " .. r1)
      TICK(8, 3, 0.01)
      assert(rich.money == r1 and poor.money == p1, "once per game day")
      DAY(10)
      assert(poor.money < 0.35 * 4000, "poor town till: " .. poor.money)
      assert(rich.money > 9500 and rich.money <= 10400, "rich trade town till: " .. rich.money)
      local lg = read_tmp("tempo.log")
      assert(lg:find("TILL poor Town Two"), "poor marker")
      assert(lg:find("TILL town Town Two: w=0.08"), "town marker (w clamped to min)")
      assert(lg:find("TILL town Town One: w=1.30"), "rich town marker")
      assert(lg:find("TILL day %d+: traders=%d+ raised=%d+ lowered=%d+"), "day marker")
      assert(not next(KMM_Tempo.status().disabled), "nothing disabled")
    """)


@case("R3 касса: игрок выкупил кассу — восстанавливается постепенно; город оправился — касса растёт обратно")
def t_till_recovery(lua, tmp):
    lua.load_module()
    lua.run(TILL_PRE + """
      local a = mkhuman("SOLD", { money = 0 }); snap_char(a, { trader = true, town = "T1" })
      TICK(3, 3, 0.01)
      assert(a.money > 2000 and a.money < 3500, "not instant refill: " .. a.money)   -- база города 8000, шаг 0.35
      DAY(8)
      assert(a.money > 7000 and a.money <= 8000, "refilled over days: " .. a.money)
      MOOD.T2 = { pop = 30, pop0 = 100, unrest = 1, food = 0 }; STK.T2.siege = true
      local b = mkhuman("RUIN", { money = 300 }); snap_char(b, { trader = true, town = "T2" })
      DAY(3)
      local low = b.money
      assert(low <= 330, "ruined town stays poor: " .. low)
      MOOD.T2 = { pop = 100, pop0 = 100, unrest = 0, food = 1 }; STK.T2.siege = false
      DAY(1); local d1 = b.money
      DAY(8)
      assert(d1 > low and d1 < 2000 and b.money > 3200, "recovers gradually: " .. d1 .. " -> " .. b.money)
    """)


@case("R3 касса: процветание фракции (ванильный ProsperityManager) снижает цель; probe в лог")
def t_till_prosperity(lua, tmp):
    lua.load_module()
    lua.run(TILL_PRE + """
      STK.T2.city = true
      local a = mkhuman("PA", { money = 8000, prosp = 1.0 }); snap_char(a, { trader = true, town = "T1" })
      local b = mkhuman("PB", { money = 8000, prosp = 0.25 }); snap_char(b, { trader = true, town = "T2" })
      DAY(10)
      assert(math.abs(a.money - 8000) < 50, "normal prosperity keeps till: " .. a.money)
      assert(b.money < 6000 and b.money > 5400, "low prosperity -> poorer: " .. b.money)
      assert(read_tmp("tempo.log"):find("TILL probe: faction"), "probe logged")
    """)


@case("R3 касса: не торговцы, отряд игрока и бродячие торговцы не тронуты; нет входов — цель = база")
def t_till_scope(lua, tmp):
    lua.load_module()
    lua.run(TILL_PRE + """
      KMM_Conductor.town_mood = nil; KMM_Stock = nil
      local u = mkhuman("UNQ", { money = 50 }); snap_char(u, { unique = true, town = "T1" })
      local p = mkhuman("PTR", { money = 0 }); snap_char(p, { trader = true, player = true, town = "T1" })
      local w = mkhuman("WAND", { money = 0 }); snap_char(w, { trader = true })
      local t = mkhuman("TWN", { money = 3000 }); snap_char(t, { trader = true, town = "T2" })
      DAY(12)
      assert(u.money == 50 and p.money == 0 and w.money == 0, "untouched")
      assert(t.money > 3900 and t.money <= 4000, "no inputs: target = town base 4000: " .. t.money)
    """)


@case("R3 касса: запись денег не применилась у 3 торговцев подряд (ни одной удачной) -> till выключается сам (лог), остальное работает")
def t_till_write_ignored(lua, tmp):
    lua.load_module()
    lua.run(TILL_PRE + """
      local a = mkhuman("RO", { money = 100 }); a.money_ro = true; snap_char(a, { trader = true, town = "T1" })
      TICK(3, 3, 0.01)
      assert(not KMM_Tempo.status().disabled.till, "one ignored write is not a verdict")
      for i = 2, 3 do local b = mkhuman("RO" .. i, { money = 100 }); b.money_ro = true; snap_char(b, { trader = true, town = "T1" }) end
      TICK(6, 3, 0.01)
      local d = KMM_Tempo.status().disabled
      assert(d.till and d.till:find("money write not applied"), "till disabled: " .. tostring(d.till))
      assert(not d.npc_hunger and not d.all and not d.player_fatigue, "others alive")
      assert(read_tmp("tempo.log"):find("DISABLED till"), "logged")
      DAY(2)
      assert(a.money == 100, "no further writes")
    """)


def main():
    if not os.path.exists(DLL):
        print("SKIP: lua51.dll KenshiLua не найден")
        return 1
    for c in CASES:
        c()
    bad = [r for r in RESULTS if not r[1]]
    for name, ok, msg in RESULTS:
        print(("OK   " if ok else "FAIL ") + name + ("" if ok else "\n     " + msg))
    print(f"{len(RESULTS) - len(bad)}/{len(RESULTS)} passed")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
