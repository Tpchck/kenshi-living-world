"""Офлайн-проверка test_mode дирижёра на заглушках игрового API (LuaJIT из KenshiLua). debug.log пишется во временную папку и печатается.
python -I -X utf8 tools/conductor/test_testmode.py"""
import ctypes
import os
import tempfile

DLL = r"C:\Program Files (x86)\Steam\steamapps\workshop\content\233860\3817000612\lua51.dll"
SCRIPT = r"C:\KenshiModMap\build\KMM_Conductor\scripts\init\KMM_Conductor.lua"
TMP = tempfile.mkdtemp(prefix="kmm_tm_").replace("\\", "/")
L = ctypes.CDLL(DLL)
L.luaL_newstate.restype = ctypes.c_void_p
for fn, at in [("luaL_openlibs", [ctypes.c_void_p]), ("luaL_loadstring", [ctypes.c_void_p, ctypes.c_char_p]),
               ("lua_pcall", [ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int])]:
    getattr(L, fn).argtypes = at
L.lua_tolstring.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p]
L.lua_tolstring.restype = ctypes.c_char_p
st = L.luaL_newstate()
L.luaL_openlibs(st)


def run(code, name):
    if L.luaL_loadstring(st, code.encode("utf-8")) or L.lua_pcall(st, 0, 0, 0):
        raise RuntimeError(name + ": " + L.lua_tolstring(st, -1, None).decode("utf-8", "replace"))


STUBS = '''
local real_open = io.open
io.open = function(p, m) p = tostring(p):gsub("^C:/KenshiModMap/logs/", "TMPDIR/"); return real_open(p, m) end
KenshiLua = { log = function(s) end }
Events = { h = {} }
function Events.on(n, f) Events.h[n] = f; return n end
CLOCK = 0
os.clock = function() return CLOCK end
FACS = {}
function FAC(id)
  if not FACS[id] then
    local f = { id = id, rel = {} }
    f.relations = { getFactionRelation = function(self, o) return f.rel[o.id] or 0 end, setRelation = function(self, o, v) f.rel[o.id] = v end }
    f.data = { stringID = id }; f.getData = function() return f.data end   -- как в игре: у Faction нет getGameData (лог 2026-11-12)
    FACS[id] = f
  end
  return FACS[id]
end
function MKCH(nm, fid, x, z, player, unique)
  local c = { chained = false, dead = false }
  function c:getName() return nm end
  function c:getFaction() return FAC(fid) end
  function c:getPosition() return { x = x, y = 0, z = z } end
  function c:isPlayerCharacter() return player or false end
  function c:isUnique() return unique or false end
  function c:isDead() return c.dead end
  function c:isChained() return c.chained end
  function c:getHandle() return "h_" .. nm end
  function c:setChainedMode(b) c.chained = b end
  function c:declareDead() c.dead = true end
  function c:getInventory() return { addItem = function() end, equipItem = function() end } end
  return c
end
PCS, CHARS = {}, {}
function getPlayerInterface() return { getAllPlayerCharacters = function() return PCS end } end
function getGameWorld()
  return {
    factionMgr = { getFactionByStringID = function(self, id) return FAC(id) end },
    getCharacterUpdateList = function() local s = {}; for _, c in ipairs(CHARS) do s[c] = true end; return s end,
    gamedata = { getData = function(self, sid, t) return { sid = sid } end },
    theFactory = { createItem = function() return {} end,
                   createRandomSquad = function(self, f, pos) if type(pos) ~= "table" or not pos.x then error("bad pos") end; return "platoon" end },
  }
end
'''.replace("TMPDIR", TMP)
run(STUBS, "stubs")
for _f in sorted(__import__("glob").glob(SCRIPT.replace("KMM_Conductor.lua", "KMM_Conductor*.lua"))): run(open(_f, encoding="utf-8").read(), _f.split("\\")[-1])
run('''
KMM_Conductor.reset()
local S = KMM_Conductor.state()
local ids, pf = {}, nil
for fid, f in pairs(S.F) do if f.player then pf = fid else ids[#ids + 1] = fid end end
table.sort(ids)
PCS = { MKCH("Nameless", pf or "player", 0, 0, true) }
CHARS = { PCS[1], MKCH("Guard", ids[1], 500, 0), MKCH("Drifter", ids[2], 900, 300), MKCH("Bandit", ids[3], 1200, -100),
          MKCH("Lord", ids[4], 300, 0, false, true), MKCH("FarAway", ids[5], 9000, 0) }
KMM_Conductor._set("test_mode", true)
for t = 0, 400, 5 do CLOCK = t; KMM_Conductor._test_tick() end
assert(S.test_done, "test not finished")
assert(CHARS[2].chained or CHARS[3].chained or CHARS[4].chained, "nobody chained")
assert(not CHARS[5].chained and not CHARS[5].dead, "unique touched")
assert(not CHARS[6].chained and not CHARS[6].dead, "far NPC touched")
''', "test")
print(open(os.path.join(TMP, "debug.log"), encoding="utf-8").read())
print("chronicle lines:", len(open(os.path.join(TMP, "chronicle.log"), encoding="utf-8").read().splitlines()) if os.path.exists(os.path.join(TMP, "chronicle.log")) else 0)
