"""Офлайн-тест KMM_Elite на LuaJIT из KenshiLua (lua51.dll) с заглушками API игры и дирижёра. Без игры, < 5 с.
python -I -X utf8 build/KMM_Elite/_dev/test_elite.py   (сначала: python -I -X utf8 tools/streams/elite.py --check --write)"""
import ctypes
import sys
import tempfile

DLL = r"C:\Program Files (x86)\Steam\steamapps\workshop\content\233860\3817000612\lua51.dll"
SCRIPT = "C:/KenshiModMap/build/KMM_Elite/scripts/init/kmm_elite.lua"
SCRIPTS_DIR = "C:/KenshiModMap/build/KMM_Elite/scripts"

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
EVENTS, API = {}, { pi = 0, scan = 0, spawn = 0 }
BREAK_SPAWN = false
local real_open = io.open
io.open = function(p, m) p = tostring(p):gsub("^C:/KenshiModMap/logs/", TMP .. "/"):gsub("^C:/KenshiModMap/state/", TMP .. "/"); return real_open(p, m) end; local __rr = os.remove; os.remove = function(p) p = tostring(p):gsub("^C:/KenshiModMap/state/", TMP .. "/"); return __rr(p) end
function read_tmp(name) local f = real_open(TMP .. "/" .. name, "r"); if not f then return "" end; local s = f:read("*a"); f:close(); return s end
CLOCK, DAY = 100, 800
os.clock = function() return CLOCK end
math.random = function() return 0 end
package.path = "%(scripts)s/?.lua;" .. package.path
KenshiLua = { log = function(s) end }
Events = { h = {} }
function Events.on(name, f) Events.h[name] = f; return 1 end
DATA = dofile("%(scripts)s/kmm_elite_data.lua")
FID, U = next(DATA.units)
FID2, U2 = nil, nil
for f, u in pairs(DATA.units) do if f ~= FID then FID2, U2 = f, u end end
SPAWNS, CHARS = {}, {}
local gd = {}
local gw = { theFactory = {}, gamedata = {}, factionMgr = {} }
function gw.gamedata:getData(sid, ty) gd[sid] = gd[sid] or { stringID = sid }; return gd[sid] end
function gw.factionMgr:getFactionByStringID(f) return { id = f, warMgr = { getNearestTown = function() return { town = true } end } } end
function gw.theFactory:createRandomSquad(fobj, pos, a, n, b, tmpl, c, d, e, f, tgt, town, g, h, i)
  API.spawn = API.spawn + 1
  if BREAK_SPAWN then error("createRandomSquad: binding changed") end
  SPAWNS[#SPAWNS + 1] = { fid = fobj.id, pos = pos, tmpl = tmpl.stringID, n = n, town = town }
  return {}
end
function gw:getCharacterUpdateList() API.scan = API.scan + 1; local s = {}; for _, c in ipairs(CHARS) do s[c] = true end; return s end
function getGameWorld() return gw end
PCS = {}
local function _hand_stub() local h = { null = false }; function h:setNull() self.null = true end; function h:isNull() return self.null end; return h end
local function _with_hands(list) for _, c in pairs(list or {}) do if type(c) == "table" and not c.getCarryingObject then c.getCarryingObject = function() return _hand_stub() end end end; return list end
local pi = { getAllPlayerCharacters = function() return _with_hands(PCS) end }
function getPlayerInterface() API.pi = API.pi + 1; return pi end
function mkchar(x, z, sid, dead)
  local c = {}
  function c:getPosition() return { x = x, y = 0, z = z } end
  function c:isDead() return dead or false end
  function c:getPlatoon() return { me = { squadTemplate = { stringID = sid } } } end
  return c
end
TOWNX, TOWNZ = 4500, 0
STATE = { F = {} }
STATE.F[FID] = { alive = true, wealth = 300, wealth0 = 100, know = 2 }
if FID2 then STATE.F[FID2] = { alive = true, wealth = 100, wealth0 = 100, know = 2 } end
KMM_Conductor = {
  emit = function(ev) EVENTS[#EVENTS + 1] = ev end,
  state = function() return STATE end,
  day = function() return DAY end,
  towns = function() return { { sid = "t1", name = "Testville", owner = FID, x = TOWNX, z = TOWNZ } } end,
}
function TICK(n, dclock)
  for _ = 1, n do CLOCK = CLOCK + (dclock or 6); Events.h["GameWorld::charsUpdate"]({}) end
end
function assert_eq(a, b, msg) if a ~= b then error(msg .. ": expected " .. tostring(b) .. ", got " .. tostring(a), 2) end end
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

    def close(self):
        L.lua_close(self.st)


def compile_only(path):
    st = L.luaL_newstate()
    rc = L.luaL_loadfile(st, path.encode("utf-8"))
    msg = L.lua_tolstring(st, -1, None) if rc else None
    L.lua_close(st)
    if rc:
        raise AssertionError(f"syntax {path}: {msg.decode('utf-8', 'replace')}")


SETUP = "dofile(SCRIPT_PATH)\nP = mkchar(0, 0, 'player'); PCS = { P }\n"

TESTS = {
    "load_has_no_side_effects": """
dofile(SCRIPT_PATH)
assert_eq(API.pi, 0, "getPlayerInterface на загрузке"); assert_eq(API.scan, 0, "скан на загрузке"); assert_eq(#EVENTS, 0, "события на загрузке")
assert(Events.h["GameWorld::charsUpdate"], "нет обработчика тика")
""",
    "no_player_chars_nothing": """
dofile(SCRIPT_PATH)
TICK(50)
assert_eq(API.spawn, 0, "спавн без персонажей"); assert_eq(API.scan, 0, "скан без персонажей"); assert_eq(#EVENTS, 0, "события без персонажей")
""",
    "too_early_nothing": SETUP + """
DAY = 719
TICK(50)
assert_eq(API.spawn, 0, "спавн раньше 2 лет"); assert_eq(#EVENTS, 0, "события раньше срока")
""",
    "rich_knowing_faction_spawns_once": SETUP + """
TICK(30)
assert_eq(API.spawn, 1, "ровно один спавн"); assert_eq(#EVENTS, 1, "одно событие")
local s = SPAWNS[1]
assert_eq(s.fid, FID, "фракция"); assert_eq(s.tmpl, U.squad, "шаблон отряда")
assert(math.sqrt((s.pos.x - TOWNX) ^ 2 + (s.pos.z - TOWNZ) ^ 2) <= 700, "точка далеко от города")
assert(math.sqrt(s.pos.x ^ 2 + s.pos.z ^ 2) <= 6000 + 700, "точка далеко от игрока")
assert_eq(EVENTS[1].type, "elite_seen", "тип события"); assert_eq(EVENTS[1].a, FID, "a"); assert_eq(EVENTS[1].town_name, "Testville", "город")
""",
    "poor_faction_nothing": SETUP + """
STATE.F[FID].wealth = 140
TICK(30); assert_eq(API.spawn, 0, "бедная фракция")
STATE.F[FID].wealth = 300; STATE.F[FID].know = 1.0
TICK(30); assert_eq(API.spawn, 0, "неучёная фракция")
STATE.F[FID].know = nil
TICK(30); assert_eq(API.spawn, 1, "без know - только по богатству")
""",
    "dead_or_far_nothing": SETUP + """
STATE.F[FID].alive = false; TICK(30); assert_eq(API.spawn, 0, "мёртвая фракция")
STATE.F[FID].alive = true; TOWNX = 9000; TICK(30); assert_eq(API.spawn, 0, "город дальше 6000")
""",
    "cooldown_and_alive_limit": SETUP + """
TICK(30); assert_eq(API.spawn, 1, "первый")
CLOCK = CLOCK + 1000
CHARS = { mkchar(100, 0, U.squad, false) }
DAY = DAY + 30; TICK(30); assert_eq(API.spawn, 1, "живой отряд блокирует")
CHARS = { mkchar(100, 0, U.squad, true) }
DAY = DAY - 25 + 0; TICK(30); assert_eq(API.spawn, 1, "кулдаун 20 дней (прошло 5)")
DAY = DAY + 20; TICK(30); assert_eq(API.spawn, 2, "после кулдауна и гибели отряда")
""",
    "spawn_error_disables_only_itself": SETUP + """
BREAK_SPAWN = true
TICK(30)
assert_eq(API.spawn, 1, "попытка одна, дальше отключено")
assert(KMM_Elite.disabled().spawn, "функция spawn не отключена")
assert(not KMM_Elite.disabled().tick, "тик не должен отключаться")
TICK(30); assert_eq(API.spawn, 1, "после отключения нет вызовов")
assert(read_tmp("debug.log"):find("spawn disabled"), "причина не записана в debug.log")
assert_eq(#EVENTS, 0, "события при ошибке")
""",
    "unseen_all_spawns_far_from_every_pc": SETUP + """
-- два персонажа игрока: у одного рядом с городом с другой стороны; все спавны >= 3500 от КАЖДОГО и <= 6000 от ближайшего
local total = 0
for _, tx in ipairs({ 4200, 5000, 5900 }) do
  for k = 1, 30 do
    TOWNX = tx; PCS = { mkchar(0, 0, 'player'), mkchar(-2500, 300, 'player') }
    SPAWNS = {}; API.spawn = 0; CLOCK = CLOCK + 5000; DAY = DAY + 30; CHARS = {}
    TICK(40)
    for _, s in ipairs(SPAWNS) do
      total = total + 1
      local nearest = 1e9
      for _, p in ipairs(PCS) do
        local d = math.sqrt((s.pos.x - p:getPosition().x) ^ 2 + (s.pos.z - p:getPosition().z) ^ 2)
        assert(d >= 3500, "спавн ближе 3500 к персонажу игрока: " .. d)
        if d < nearest then nearest = d end
      end
      assert(nearest <= 6000, "спавн дальше 6000: " .. nearest)
    end
  end
end
assert(total >= 20, "слишком мало спавнов в проверке: " .. total)
""",
    "city_closer_than_min_spawns_opposite_or_defers": SETUP + """
TOWNX = 3300; local n = 0
for k = 1, 60 do
  SPAWNS = {}; API.spawn = 0; CLOCK = CLOCK + 5000; DAY = DAY + 30; CHARS = {}
  TICK(40)
  for _, s in ipairs(SPAWNS) do
    n = n + 1
    assert(s.pos.x > TOWNX, "со стороны игрока")
    assert(math.sqrt(s.pos.x ^ 2 + s.pos.z ^ 2) >= 3500, "ближе 3500")
  end
end
TOWNX = 1000; SPAWNS = {}; API.spawn = 0; CLOCK = CLOCK + 5000; DAY = DAY + 60; CHARS = {}
TICK(60); assert_eq(API.spawn, 0, "город в 1000 от игрока: нет допустимой точки - нет спавна")
assert((KMM_Elite.stats().deferred or 0) > 0, "отложено не засчитано")
TOWNX = 4500; DAY = DAY + 60; TICK(60); assert_eq(API.spawn, 1, "позже, когда допустимо, спавн происходит")
""",
}


def main():
    res = []
    for p in (SCRIPT, SCRIPTS_DIR + "/kmm_elite_data.lua"):
        compile_only(p)
    res.append(("syntax", True, ""))
    for name, code in TESTS.items():
        tmp = tempfile.mkdtemp(prefix="kmm_elite_")
        lua = Lua(tmp.replace("\\", "/"))
        try:
            lua.run(f'SCRIPT_PATH = "{SCRIPT}"\n' + code, name)
            res.append((name, True, ""))
        except AssertionError as e:
            res.append((name, False, str(e)))
        finally:
            lua.close()
    ok = sum(1 for r in res if r[1])
    for n, good, msg in res:
        print(("OK   " if good else "FAIL ") + n + ("" if good else "  - " + msg))
    print(f"{ok}/{len(res)}")
    sys.exit(0 if ok == len(res) else 1)


if __name__ == "__main__":
    main()
