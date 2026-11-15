"""Офлайн-тест KMM_Ore v3 на LuaJIT из KenshiLua (lua51.dll) с заглушками API игры. Без игры, без сети, < 5 с.
cd build/KMM_Ore/_dev && python -I -X utf8 ../../../tools/test/log_sandbox.py test_ore.py
Пути C:/KenshiModMap/logs/ перенаправляются во временную папку — реальные логи не трогаются.
Тесты не зависят от порядка обхода таблиц (проверяются множества и суммы)."""
import ctypes
import os
import sys
import tempfile

DLL = r"C:\Program Files (x86)\Steam\steamapps\workshop\content\233860\3817000612\lua51.dll"
SCRIPT = "C:/KenshiModMap/build/KMM_Ore/scripts/init/kmm_ore.lua"
CONFIG = "C:/KenshiModMap/build/KMM_Ore/scripts/ore_config.lua"
TEMPLATES = "C:/KenshiModMap/build/KMM_Ore/scripts/ore_templates.lua"
SCRIPTS_DIR = "C:/KenshiModMap/build/KMM_Ore/scripts"

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
OPEN_LOG, LOGS, REG, PM = {}, {}, {}, {}
API_CALLS, BODY_CALLS, BREAK, SEED, REGION_BREAK, REGION = 0, 0, false, 777, false, 0.5
local real_open = io.open
io.open = function(p, m)
  OPEN_LOG[#OPEN_LOG + 1] = tostring(p) .. "|" .. tostring(m)
  p = tostring(p):gsub("^C:/KenshiModMap/logs/", TMP .. "/")
  return real_open(p, m)
end
function read_tmp(name) local f = real_open(TMP .. "/" .. name, "r"); if not f then return nil end; local s = f:read("*a"); f:close(); return s end
CLOCK, DAY = 100, 10.0
os.clock = function() return CLOCK end
package.path = "%(scripts)s/?.lua;" .. package.path
KenshiLua = { log = function(s) LOGS[#LOGS + 1] = s end }
Events = { h = {}, n = 0 }
function Events.on(name, f) Events.n = Events.n + 1; Events.h[name] = f; REG[#REG + 1] = name; return Events.n end
function Events.off(id) end
-- мир: здания для getObjectsWithinSphere
BUILDINGS = {}
local ts = { getTotalDays = function() return DAY end }
local gw = { getTimeStamp_inGameHours = function() return ts end }
function gw:getObjectsWithinSphere(buf, pos, r, typ, maxn, skip)
  for _, b in ipairs(BUILDINGS) do
    if (b.x - pos.x) ^ 2 + (b.z - pos.z) ^ 2 <= r * r then buf[#buf + 1] = { getHandle = function() return { getBuilding = function() return b end } end } end
  end
end
function getGameWorld() API_CALLS = API_CALLS + 1; return gw end
lektor = { new = function(t) local o = {}; function o:clear() for i = #self, 1, -1 do self[i] = nil end end; return o end }
PCS = {}
local pi = { getAllPlayerCharacters = function() return PCS end }
function getPlayerInterface() API_CALLS = API_CALLS + 1; return pi end
WORLDS = {}
function world_state() local S = WORLDS[SEED]; if not S then S = { seed = { r = SEED } }; WORLDS[SEED] = S end; return S end
KMM_Conductor = {
  state = function() return world_state() end,
  cfg = function() return { player_faction = "204-gamedata.base" } end,
  region_ore = function(x, z) if REGION_BREAK then error("region_ore boom") end; return REGION end,
  player_mined = function(a, x, z) PM[#PM + 1] = a end,
}
function pm_sum() local s = 0; for _, a in ipairs(PM) do s = s + a end; return s end
-- узел: Building (b) с ProductionBuilding (pb). Методы RootObjectBase — у Building; у pb только поле уровня и состояние.
function mknode(sid, x, z, lvl, opt)
  opt = opt or {}
  local pb = { _resourceMiningLevel = lvl, productionState = opt.state or 2 }
  local b = { pb = pb, sid = sid, x = x, z = z, name = opt.name or "Iron", player = opt.player or false, power = opt.power ~= false, funcs = opt.funcs }
  function b:getProductionBuilding() return self.pb end
  function b:getGameData()
    local me = self
    local gd = { stringID = self.sid, name = self.name }
    function gd:getListSize(n) return me.funcs and #me.funcs or 0 end
    function gd:getFromList(n, i) return me.funcs and me.funcs[i + 1] end
    return gd
  end
  function b:getPosition() return { x = self.x, y = 0, z = self.z } end
  function b:getName() return self.name end
  function b:setName(n) self.name = n end
  function b:isThePlayer() return self.player end
  function b:getFaction() return nil end
  function b:isPowerOn() return self.power end
  function b:isBroken() return false end
  local h = { b = b }
  function h:isValid() return true end
  function h:getBuilding() return self.b end
  BUILDINGS[#BUILDINGS + 1] = b
  return pb, h, b
end
function mkchar(name, x, z, hand, task, field)
  local c = { name = name, x = x, z = z, hand = hand, task = task or 87, field = field or "subject" }
  function c:getHandle() local s = self.name; return { toString = function() return s end } end
  function c:getPosition() return { x = self.x, y = 0, z = self.z } end
  function c:getBody()
    BODY_CALLS = BODY_CALLS + 1
    if BREAK then error("getBody: binding changed") end
    local ch = self
    return { getCurrentAction = function()
      if not ch.hand then return nil end
      local a = { key = function() return ch.task end }
      a[ch.field] = ch.hand
      return a
    end }
  end
  return c
end
function TICK(n, dclock, dday)
  for _ = 1, n do
    CLOCK = CLOCK + (dclock or 1); DAY = DAY + (dday or 0.01)
    Events.h["GameWorld::charsUpdate"]({})
  end
end
function count(t) local k = 0; for _ in pairs(t) do k = k + 1 end; return k end
function first(t) for k, v in pairs(t) do return v, k end end
function hasnode(prefix) for k, v in pairs(KMM_Ore.nodes()) do if k:sub(1, #prefix) == prefix then return v end end end
"""


class Lua:
    def __init__(self, tmp):
        self.st = L.luaL_newstate()
        L.luaL_openlibs(self.st)
        self.run(STUBS % {"tmp": tmp, "scripts": SCRIPTS_DIR}, "stubs")

    def run(self, code, name="chunk"):
        rc = L.luaL_loadstring(self.st, code.encode("utf-8")) or L.lua_pcall(self.st, 0, 0, 0)
        if rc:
            msg = L.lua_tolstring(self.st, -1, None)
            L.lua_settop(self.st, 0)
            raise AssertionError(f"{name}: {msg.decode('utf-8', 'replace') if msg else rc}")

    def load_module(self):
        self.run(f'dofile("{SCRIPT}")', "load kmm_ore.lua")

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
            tmp = tempfile.mkdtemp(prefix="kmm_ore_").replace("\\", "/")
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


@case("syntax: kmm_ore.lua, ore_config.lua, ore_templates.lua компилируются (LuaJIT KenshiLua)")
def t_syntax(lua, tmp):
    compile_only(SCRIPT)
    compile_only(CONFIG)
    compile_only(TEMPLATES)


@case("загрузка модуля: только charsUpdate, ни I/O, ни API игры")
def t_load(lua, tmp):
    lua.load_module()
    lua.run("""
      assert(#REG == 1 and REG[1] == "GameWorld::charsUpdate", "registered: " .. table.concat(REG, ","))
      assert(#OPEN_LOG == 0, "io.open at load: " .. table.concat(OPEN_LOG, ";"))
      assert(API_CALLS == 0, "game API called at load: " .. API_CALLS)
      assert(KMM_Ore and KMM_Ore.tick and KMM_Ore.status, "KMM_Ore table")
      assert(package.loaded.ore_config == nil and package.loaded.ore_templates == nil, "config read at load")
    """)


@case("загрузка сейва, персонажей ещё нет: ничего не происходит")
def t_no_chars(lua, tmp):
    lua.load_module()
    lua.run("""
      PCS = {}
      TICK(300, 1, 0.01)
      assert(BODY_CALLS == 0, "body calls")
      assert(#OPEN_LOG == 0, "io: " .. table.concat(OPEN_LOG, ";"))
      assert(KMM_Ore._rt.ready == false and KMM_Ore._rt.world == nil, "not ready")
      assert(count(KMM_Ore.disabled()) == 0, "nothing disabled")
    """)


@case("истощение: R0 класса, уровень = base*(R/R0)^k*жила региона, подпись, файл, узлы в состоянии мира, порции в мир")
def t_happy(lua, tmp):
    lua.load_module()
    lua.run("""
      PB, H, B = mknode("14521-rebirth.mod", 1000, 2000, 1.0)
      PCS = { mkchar("A", 1010, 2010, H), mkchar("B", 5000, 5000, nil) }
      TICK(5, 1, 0.01)
      assert(BODY_CALLS == 0, "worked before delay: " .. BODY_CALLS)
      TICK(10, 1, 0.01)
      assert(KMM_Ore._rt.ready, "ready after delay")
      TICK(200, 1, 0.05)    -- ~10 игровых суток, шахтёр всё время на узле
      local s = first(KMM_Ore.nodes())
      assert(s, "node created")
      assert(math.abs(s.R0 - 400) < 1e-6, "R0 = class R0 (region is live, not baked in): " .. s.R0)
      assert(s.R < s.R0 and s.hours > 100, "depleted: R=" .. s.R .. " hours=" .. s.hours)
      local want = math.max(0.02, (math.max(0, s.R) / s.R0) ^ 1.5) * 0.5
      assert(math.abs(PB._resourceMiningLevel - want) < 1e-3, "level " .. PB._resourceMiningLevel .. " want " .. want)
      assert(string.find(B.name, "^Iron %[ore left %d+%% vein 50%%%]$"), "label: " .. tostring(B.name))
      assert(WORLDS[777].ore_nodes == KMM_Ore.nodes(), "nodes live in conductor state (saved with the game)")
      assert(#PM > 0 and #PM <= 10 * 24 / 2 + 2, "fed in portions (2 game hours), not per poll: " .. #PM)
      assert(math.abs(pm_sum() - 0.25 * s.hours) < 0.25 * 2 * 1.0 + 1e-6, "fed = 0.25 * hours (minus last portion): " .. pm_sum() .. " vs " .. s.hours)
      local st = read_tmp("ore_nodes_w777.tsv"); assert(st and st:find("14521%-rebirth%.mod@1000,2000"), "fallback state file")
      local ol = read_tmp("ore.log") or ""
      assert(ol:find("NEW node") and ol:find("MINE ") and ol:find("source=save%(new%)"), "ore.log: " .. ol)
      assert(count(KMM_Ore.disabled()) == 0, "nothing disabled")
    """)


@case("цель по currentSubTarget и мод-бур из ore_templates (Soulbody) считаются")
def t_subtarget(lua, tmp):
    lua.load_module()
    lua.run("""
      local _, h1 = mknode("14521-rebirth.mod", 0, 0, 1.0)
      local _, h2 = mknode("5008195-Soulbody.mod", 9000, 9000, 0.8, { name = "SC Iron Ore Drill red" })
      PCS = { mkchar("A", 0, 0, h1, 87, "currentSubTarget"), mkchar("B", 9000, 9000, h2, 87) }
      TICK(100, 1, 0.05)
      assert(hasnode("14521-rebirth.mod@") and hasnode("14521-rebirth.mod@").hours > 0, "subtarget node worked")
      local d = hasnode("5008195-Soulbody.mod@"); assert(d and d.cls == "mine" and d.res == "iron", "mod drill as mine")
    """)


@case("далеко от узла / haul / камень: труд не считается; CHAIN пишет стадии обрыва")
def t_filters(lua, tmp):
    lua.load_module()
    lua.run("""
      local _, h1 = mknode("14521-rebirth.mod", 0, 0, 1.0)
      local _, h2 = mknode("42250-gamedata.base", 0, 0, 1.0, { name = "Stone Resource" })
      PCS = { mkchar("far", 5000, 5000, h1), mkchar("haul", 0, 0, h1, 113), mkchar("stone", 0, 0, h2) }
      TICK(100, 1, 0.05)
      assert(KMM_Ore._rt.ready and BODY_CALLS > 0, "polled")
      assert(count(KMM_Ore.nodes()) == 0, "no nodes")
      local ol = read_tmp("ore.log") or ""
      assert(ol:find("CHAIN [^\\n]*far=%d+[^\\n]*not_ore=%d+[^\\n]*task_other=%d+"), "chain line: " .. ol)
      assert(ol:find("SKIP template 42250%-gamedata%.base"), "stone skipped once")
    """)


@case("B7: 189 считается; 221/190 pretend — нет, но SKIP task один раз")
def t_b7_tasks(lua, tmp):
    lua.load_module()
    lua.run("""
      local pb1, h1 = mknode("14521-rebirth.mod", 0, 0, 1.0)
      local pb2, h2 = mknode("42248-gamedata.base", 9000, 9000, 1.0)
      PCS = { mkchar("slave", 0, 0, h1, 189), mkchar("pretend", 9000, 9000, h2, 221) }
      TICK(100, 1, 0.05)
      assert(count(KMM_Ore.nodes()) == 1, "only the 189 node: " .. count(KMM_Ore.nodes()))
      local s = first(KMM_Ore.nodes()); assert(s.tpl == "14521-rebirth.mod" and s.R < s.R0, "189 depletes")
      assert(pb2._resourceMiningLevel == 1.0, "pretend node untouched")
      local ol = read_tmp("ore.log") or ""
      local _, n = ol:gsub("SKIP task=221 at ore node 42248%-gamedata%.base", ""); assert(n == 1, "skip logged once: " .. n)
    """)


@case("приказ игрока на рудный узел: подписка после старта, TaskType учится (LEARN), затем считается")
def t_learn(lua, tmp):
    lua.load_module()
    lua.run("""
      local _, h = mknode("42249-gamedata.base", 0, 0, 1.0, { name = "Copper" })
      PCS = { mkchar("A", 0, 0, h, 77) }
      TICK(40, 1, 0.05)
      assert(count(KMM_Ore.nodes()) == 0, "unknown task not counted")
      local f = Events.h["PlayerInterface::newPlayerTaskSelectedCharacters"]
      assert(f, "order hook registered lazily: " .. table.concat(REG, ","))
      f({}, 77, h, nil, { x = 0, y = 0, z = 0 }, false)
      assert(KMM_Ore.learned()[77], "learned 77")
      TICK(60, 1, 0.05)
      local s = first(KMM_Ore.nodes()); assert(s and s.res == "copper" and s.hours > 0, "now counted")
      local ol = read_tmp("ore.log") or ""
      assert(ol:find("LEARN task=77") and ol:find("ORDER task=77 node=42249%-gamedata%.base"), "markers: " .. ol)
    """)


@case("запасная классификация по функциональности шаблона (LEARN template)")
def t_funcs(lua, tmp):
    lua.load_module()
    lua.run("""
      local _, h = mknode("31337-newmod.mod", 0, 0, 1.0, { name = "Big Iron Drill", funcs = { "x", "1869-gamedata.base" } })
      PCS = { mkchar("A", 0, 0, h, 87) }
      TICK(100, 1, 0.05)
      local s = hasnode("31337-newmod.mod@"); assert(s and s.cls == "mine" and s.res == "iron", "learned template")
      assert((read_tmp("ore.log") or ""):find("LEARN template 31337%-newmod%.mod"), "marker")
    """)


@case("автобур игрока под питанием: AUTO-часы без шахтёра; без питания, чужой или с шахтёром — нет двойного счёта")
def t_auto(lua, tmp):
    lua.load_module()
    lua.run("""
      local _, _, b1 = mknode("2098-gamedata.base", 100, 0, 1.0, { name = "Ore Drill III", player = true })
      local _, _, b2 = mknode("5008199-Soulbody.mod", 200, 0, 1.0, { name = "SC Auto", player = true, power = false })
      local _, _, b3 = mknode("5008200-Soulbody.mod", 300, 0, 1.0, { name = "SC Auto", player = false })
      PCS = { mkchar("idle", 0, 0, nil) }
      for _ = 1, 40 do TICK(30, 1, 0.01) end   -- 40 сканов по 30 с, ~12 игровых суток
      local s1 = hasnode("2098-gamedata.base@"); assert(s1 and s1.hours > 100, "auto hours: " .. tostring(s1 and s1.hours))
      local s2 = hasnode("5008199-Soulbody.mod@"); assert(s2 and s2.hours == 0, "unpowered: no hours")
      assert(not hasnode("5008200-Soulbody.mod@"), "npc drill not ours")
      assert(KMM_Ore.stats().auto_hours > 100 and KMM_Ore.stats().work_hours == 0, "auto only")
      assert((read_tmp("ore.log") or ""):find("AUTO 2098"), "AUTO marker")
    """)


@case("жила региона живая: падение region_ore снижает уровень узла после обновления")
def t_region(lua, tmp):
    lua.load_module()
    lua.run("""
      local pb, h = mknode("14521-rebirth.mod", 0, 0, 1.0)
      PCS = { mkchar("A", 0, 0, h) }
      TICK(40, 1, 0.01)
      local l1 = pb._resourceMiningLevel
      REGION = 0.1
      TICK(60, 1, 0.01)   -- > 6 игровых часов
      local l2 = pb._resourceMiningLevel
      assert(l2 < l1 * 0.5, "region drop lowers level: " .. l1 .. " -> " .. l2)
      local s = first(KMM_Ore.nodes())
      assert(math.abs(l2 - math.max(0.02, (s.R / s.R0) ^ 1.5) * 0.2) < 1e-3, "floor 0.2 of vein: " .. l2)
    """)


@case("порции: не больше chars_per_poll персонажей за опрос")
def t_portions(lua, tmp):
    lua.load_module()
    lua.run("""
      local _, h = mknode("14521-rebirth.mod", 0, 0, 1.0)
      PCS = {}; for i = 1, 10 do PCS[i] = mkchar("c" .. i, 0, 0, h) end
      TICK(20, 1, 0.01)
      assert(KMM_Ore._rt.ready, "ready")
      local b0 = BODY_CALLS; TICK(1, 1, 0.01); assert(BODY_CALLS - b0 == 4, "per poll " .. (BODY_CALLS - b0))
      b0 = BODY_CALLS; TICK(5, 0.2, 0.001); assert(BODY_CALLS - b0 <= 4, "rate limit " .. (BODY_CALLS - b0))
    """)


@case("ошибка API: поток отключается, причина в debug.log, исключение наружу не выходит")
def t_api_error(lua, tmp):
    lua.load_module()
    lua.run("""
      local _, h = mknode("14521-rebirth.mod", 0, 0, 1.0)
      PCS = { mkchar("A", 0, 0, h) }
      TICK(20, 1, 0.01)
      BREAK = true
      TICK(5, 1, 0.01)
      assert(KMM_Ore.disabled().tick, "tick disabled")
      local d = read_tmp("debug.log"); assert(d and d:find("%[KMM_Ore%] tick disabled until restart: .*getBody"), "debug.log: " .. tostring(d))
      local b0 = BODY_CALLS; BREAK = false; TICK(50, 1, 0.01)
      assert(BODY_CALLS == b0, "stays off for the session")
      KMM_Ore.tick()
    """)


@case("ошибка скана: отключается только скан, труд персонажей считается")
def t_scan_error(lua, tmp):
    lua.load_module()
    lua.run("""
      local _, h = mknode("14521-rebirth.mod", 0, 0, 1.0)
      PCS = { mkchar("A", 0, 0, h) }
      getGameWorld = function() local gw = { getTimeStamp_inGameHours = function() return { getTotalDays = function() return DAY end } end }
        function gw:getObjectsWithinSphere() error("sphere boom") end; return gw end
      TICK(100, 1, 0.05)
      local d = KMM_Ore.disabled(); assert(d.scan and not d.tick, "only scan disabled")
      assert(first(KMM_Ore.nodes()).hours > 0, "char work counted")
    """)


@case("ошибка getGameWorld/getPlayerInterface: ждём, без исключения")
def t_world_missing(lua, tmp):
    lua.load_module()
    lua.run("""
      getPlayerInterface = function() error("no interface in main menu") end
      TICK(50, 1, 0.01)
      getPlayerInterface = function() return nil end
      TICK(50, 1, 0.01)
      assert(not KMM_Ore._rt.ready and count(KMM_Ore.disabled()) == 0, "waiting, nothing disabled")
    """)


@case("ошибка дирижёра: отключается только связь, истощение работает (жила = 1)")
def t_conductor_error(lua, tmp):
    lua.load_module()
    lua.run("""
      REGION_BREAK = true
      local pb, h = mknode("14521-rebirth.mod", 0, 0, 1.0)
      PCS = { mkchar("A", 0, 0, h) }
      TICK(100, 1, 0.05)
      local d = KMM_Ore.disabled()
      assert(d.conductor_link and not d.tick, "only link disabled")
      local s = first(KMM_Ore.nodes()); assert(s and math.abs(s.R0 - 400) < 1e-6 and s.R < 400, "full R0 and depletion")
      assert(pb._resourceMiningLevel < 1.0, "level written")
    """)


@case("ore_enabled = false: тик сразу выходит")
def t_disabled(lua, tmp):
    lua.run("""
      local c = dofile("%s"); c.ore_enabled = false; package.loaded.ore_config = c
    """ % CONFIG)
    lua.load_module()
    lua.run("""
      local _, h = mknode("14521-rebirth.mod", 0, 0, 1.0)
      PCS = { mkchar("A", 0, 0, h) }
      local a0 = API_CALLS
      TICK(100, 1, 0.05)
      assert(API_CALLS == a0 and BODY_CALLS == 0 and #OPEN_LOG == 0, "no API/IO")
    """)


@case("tick_source = conductor: свой обработчик молчит, KMM_Ore.tick() работает")
def t_conductor_source(lua, tmp):
    lua.run("""
      local c = dofile("%s"); c.tick_source = "conductor"; package.loaded.ore_config = c
    """ % CONFIG)
    lua.load_module()
    lua.run("""
      local _, h = mknode("14521-rebirth.mod", 0, 0, 1.0)
      PCS = { mkchar("A", 0, 0, h) }
      TICK(100, 1, 0.05)
      assert(BODY_CALLS == 0, "own handler idle")
      for _ = 1, 100 do CLOCK = CLOCK + 1; DAY = DAY + 0.05; KMM_Ore.tick(); Events.h["GameWorld::charsUpdate"]({}) end
      assert(BODY_CALLS > 0 and count(KMM_Ore.nodes()) == 1, "worked via conductor call")
    """)


@case("загрузка сейва того же мира: узлы берутся из нового состояния дирижёра (откат вместе с сейвом)")
def t_reload_same_world(lua, tmp):
    lua.load_module()
    lua.run("""
      local _, h = mknode("14521-rebirth.mod", 0, 0, 1.0)
      PCS = { mkchar("A", 0, 0, h) }
      TICK(100, 1, 0.05)
      local R1 = first(KMM_Ore.nodes()).R
      -- игрок загрузил более ранний сейв того же мира: дирижёр отдал новую таблицу состояния со старыми узлами
      WORLDS[777] = { seed = { r = 777 }, ore_nodes = { ["14521-rebirth.mod@0,0"] = { cls = "surface", tpl = "14521-rebirth.mod", R = 390, R0 = 400, base = 1, last_day = DAY, hours = 10, recent = 0 } } }
      TICK(3, 1, 0.01)
      local s = KMM_Ore.nodes()["14521-rebirth.mod@0,0"]
      assert(KMM_Ore.nodes() == WORLDS[777].ore_nodes and s.R > R1 and s.R <= 390, "rolled back with the save: " .. s.R .. " vs " .. R1)
    """)


@case("старый сейв без S.ore_nodes: импорт из файла мира; смена мира — своё состояние")
def t_worlds(lua, tmp):
    lua.load_module()
    lua.run("""
      local _, h = mknode("14521-rebirth.mod", 0, 0, 1.0)
      PCS = { mkchar("A", 0, 0, h) }
      TICK(100, 1, 0.05)
      SEED = 888
      PCS = {}; TICK(5, 1, 0.01)
      PCS = { mkchar("A", 0, 0, h) }; TICK(30, 1, 0.01)
      assert(KMM_Ore._rt.world == "w888", "new world")
      assert(read_tmp("ore_nodes_w777.tsv"), "old world saved to file")
    """)
    lua.close()
    lua2 = Lua(tmp)                 # новая сессия игры: тот же мир 777, состояние дирижёра без ore_nodes (сейв до v3)
    lua.st = lua2.st
    lua2.load_module()
    lua2.run("""
      local _, h = mknode("14521-rebirth.mod", 0, 0, 1.0)
      PCS = { mkchar("A", 0, 0, h) }
      TICK(12, 1, 0.01)
      local s = first(KMM_Ore.nodes())
      assert(s and s.R < s.R0, "imported depleted node")
      assert(WORLDS[777].ore_nodes == KMM_Ore.nodes(), "now in conductor state")
      assert((read_tmp("ore.log") or ""):find("source=file%->save"), "import marker")
    """)


@case("сводка S.base.ore пишется, только если база игрока уже известна")
def t_summary(lua, tmp):
    lua.load_module()
    lua.run("""
      local _, h = mknode("14521-rebirth.mod", 50, 60, 1.0)
      PCS = { mkchar("A", 50, 60, h) }
      TICK(100, 1, 0.05)
      assert(world_state().base == nil, "no base created")
      world_state().base = { known = true, x = 0, z = 0, value = 40 }
      for _ = 1, 3 do TICK(61, 1, 0.01) end
      local o = world_state().base.ore
      assert(o and o.active == 1 and o.recent > 0 and o.x == 50 and o.z == 60, "summary: " .. tostring(o and o.active))
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
