"""Офлайн-тест KMM_Ore v2 на LuaJIT из KenshiLua (lua51.dll) с заглушками API игры. Без игры, без сети, < 5 с.
python -I -X utf8 build/KMM_Ore/_dev/test_ore.py
Пути C:/KenshiModMap/logs/ перенаправляются во временную папку — реальные логи не трогаются."""
import ctypes
import os
import sys
import tempfile

DLL = r"C:\Program Files (x86)\Steam\steamapps\workshop\content\233860\3817000612\lua51.dll"
SCRIPT = "C:/KenshiModMap/build/KMM_Ore/scripts/init/kmm_ore.lua"
CONFIG = "C:/KenshiModMap/build/KMM_Ore/scripts/ore_config.lua"
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
API_CALLS, BODY_CALLS, BREAK, SEED, REGION_BREAK = 0, 0, false, 777, false
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
local ts = { getTotalDays = function() return DAY end }
local gw = { getTimeStamp_inGameHours = function() return ts end }
function getGameWorld() API_CALLS = API_CALLS + 1; return gw end
PCS = {}
local pi = { getAllPlayerCharacters = function() return PCS end }
function getPlayerInterface() API_CALLS = API_CALLS + 1; return pi end
KMM_Conductor = {
  state = function() return { seed = { r = SEED } } end,
  region_ore = function(x, z) if REGION_BREAK then error("region_ore boom") end; return 0.5 end,
  player_mined = function(a, x, z) PM[#PM + 1] = a end,
}
function mknode(sid, x, z, lvl)
  local pb = { _resourceMiningLevel = lvl, sid = sid, x = x, z = z }
  function pb:getGameData() return { stringID = self.sid } end
  function pb:getPosition() return { x = self.x, y = 0, z = self.z } end
  pb.name = "Iron"
  function pb:getName() return self.name end   -- RootObjectBase (BindingsReference)
  function pb:setName(n) self.name = n end
  local b = { pb = pb }
  function b:getProductionBuilding() return self.pb end
  local h = { b = b }
  function h:isValid() return true end
  function h:getBuilding() return self.b end
  return pb, h
end
function mkchar(name, x, z, hand, task)
  local c = { name = name, x = x, z = z, hand = hand, task = task or 87 }
  function c:getHandle() local s = self.name; return { toString = function() return s end } end
  function c:getPosition() return { x = self.x, y = 0, z = self.z } end
  function c:getBody()
    BODY_CALLS = BODY_CALLS + 1
    if BREAK then error("getBody: binding changed") end
    local ch = self
    return { getCurrentAction = function()
      if not ch.hand then return nil end
      return { subject = ch.hand, key = function() return ch.task end }
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


CASES = []


@case("syntax: kmm_ore.lua и ore_config.lua компилируются (LuaJIT KenshiLua)")
def t_syntax(lua, tmp):
    compile_only(SCRIPT)
    compile_only(CONFIG)


@case("загрузка модуля: только charsUpdate, ни I/O, ни API игры")
def t_load(lua, tmp):
    lua.load_module()
    lua.run("""
      assert(#REG == 1 and REG[1] == "GameWorld::charsUpdate", "registered: " .. table.concat(REG, ","))
      assert(#OPEN_LOG == 0, "io.open at load: " .. table.concat(OPEN_LOG, ";"))
      assert(API_CALLS == 0, "game API called at load: " .. API_CALLS)
      assert(KMM_Ore and KMM_Ore.tick and KMM_Ore.status, "KMM_Ore table")
      assert(package.loaded.ore_config == nil, "config read at load")
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


@case("персонажи появились: до задержки узлы не трогаются, после — истощение, запись уровня, файл")
def t_happy(lua, tmp):
    lua.load_module()
    lua.run("""
      PB, H = mknode("14521-rebirth.mod", 1000, 2000, 1.0)
      PCS = { mkchar("A", 1010, 2010, H), mkchar("B", 5000, 5000, nil) }
      TICK(5, 1, 0.01)
      assert(BODY_CALLS == 0, "worked before delay: " .. BODY_CALLS)
      assert(PB._resourceMiningLevel == 1.0, "level touched before delay")
      TICK(10, 1, 0.01)
      assert(KMM_Ore._rt.ready, "ready after delay")
      TICK(200, 1, 0.05)    -- ~10 игровых суток, шахтёр всё время на узле
      local s = first(KMM_Ore.nodes())
      assert(s, "node created")
      assert(math.abs(s.R0 - 200) < 1e-6, "R0 = 400 * region 0.5, got " .. s.R0)
      assert(s.R < s.R0 and s.hours > 100, "depleted: R=" .. s.R .. " hours=" .. s.hours)
      assert(PB._resourceMiningLevel < 1.0 and PB._resourceMiningLevel >= 0.02 - 1e-9, "level " .. PB._resourceMiningLevel)
      assert(string.find(PB.name, "^Iron %[ore left %d+%%%]$"), "left shown: " .. tostring(PB.name))
      assert(#PM > 0, "conductor fed")
      local st = read_tmp("ore_nodes_w777.tsv"); assert(st and st:find("14521%-rebirth%.mod@1000,2000"), "state file")
      local ol = read_tmp("ore.log"); assert(ol and ol:find("NEW node") and ol:find("MINE"), "ore.log")
      assert(count(KMM_Ore.disabled()) == 0, "nothing disabled")
    """)


@case("далеко от узла / чужая задача / не руда: труд не считается")
def t_filters(lua, tmp):
    lua.load_module()
    lua.run("""
      local _, h1 = mknode("14521-rebirth.mod", 0, 0, 1.0)
      local _, h2 = mknode("9999-stone.mod", 0, 0, 1.0)
      PCS = { mkchar("far", 5000, 5000, h1), mkchar("haul", 0, 0, h1, 113), mkchar("stone", 0, 0, h2) }
      TICK(100, 1, 0.05)
      assert(KMM_Ore._rt.ready and BODY_CALLS > 0, "polled")
      assert(count(KMM_Ore.nodes()) == 0, "no nodes")
    """)


@case("B7: 189 AUTO_LABOURING_MINES считается (даже при ore_config {87,152}); 221/190 pretend — нет, но SKIP в ore.log")
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
      assert(ol:find("SKIP task=221 at ore node 42248%-gamedata%.base"), "skip marker: " .. ol)
      local _, n = ol:gsub("SKIP task=221", ""); assert(n == 1, "skip logged once: " .. n)
    """)


@case("B7: рабочая задача у неизвестного производственного узла — SKIP template один раз")
def t_b7_template(lua, tmp):
    lua.load_module()
    lua.run("""
      local _, h = mknode("777-somemod.mod", 0, 0, 1.0)
      PCS = { mkchar("A", 0, 0, h, 87) }
      TICK(100, 1, 0.05)
      assert(count(KMM_Ore.nodes()) == 0, "not an ore template")
      local ol = read_tmp("ore.log") or ""
      local _, n = ol:gsub("SKIP template 777%-somemod%.mod", ""); assert(n == 1, "template skip once: " .. n .. " " .. ol)
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
      TICK(5, 1, 0.01)            -- handler не бросает (иначе этот чанк упал бы)
      assert(KMM_Ore.disabled().tick, "tick disabled")
      local d = read_tmp("debug.log"); assert(d and d:find("%[KMM_Ore%] tick disabled until restart: .*getBody"), "debug.log: " .. tostring(d))
      local b0 = BODY_CALLS; BREAK = false; TICK(50, 1, 0.01)
      assert(BODY_CALLS == b0, "stays off for the session")
      KMM_Ore.tick()              -- и вызов из дирижёра тоже молчит
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


@case("ошибка дирижёра: отключается только связь, истощение работает")
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


@case("смена мира и перезагрузка: состояние на мир сохраняется и подхватывается")
def t_worlds(lua, tmp):
    lua.load_module()
    lua.run("""
      local _, h = mknode("14521-rebirth.mod", 0, 0, 1.0)
      PCS = { mkchar("A", 0, 0, h) }
      TICK(100, 1, 0.05)
      R1 = first(KMM_Ore.nodes()).R
      SEED = 888                    -- другой мир: старое состояние записано, новое пустое
      PCS = {}; TICK(5, 1, 0.01)    -- экран загрузки: персонажей нет
      PCS = { mkchar("A", 0, 0, h) }; TICK(30, 1, 0.01)
      assert(KMM_Ore._rt.world == "w888" and count(KMM_Ore.nodes()) <= 1, "new world")
      assert(read_tmp("ore_nodes_w777.tsv"), "old world saved")
    """)
    lua.close()
    lua2 = Lua(tmp)                 # новая сессия игры: тот же мир 777
    lua.st = lua2.st
    lua2.load_module()
    lua2.run("""
      local _, h = mknode("14521-rebirth.mod", 0, 0, 1.0)
      PCS = { mkchar("A", 0, 0, h) }
      TICK(12, 1, 0.01)
      local s = first(KMM_Ore.nodes())
      assert(s and s.R < s.R0, "restored depleted node")
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
