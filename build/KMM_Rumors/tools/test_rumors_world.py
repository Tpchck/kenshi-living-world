"""Офлайн-тест KMM_Rumors.lua (LuaJIT из KenshiLua): список рассказанного живёт в сейве, сброс при новой игре, источник — журнал дирижёра."""
import ctypes, tempfile
DLL = r"C:\Program Files (x86)\Steam\steamapps\workshop\content\233860\3817000612\lua51.dll"
SCRIPT = r"C:\KenshiModMap\build\KMM_Rumors\scripts\init\KMM_Rumors.lua"
TMP = tempfile.mkdtemp(prefix="kmm_rum_").replace("\\", "/")
L = ctypes.CDLL(DLL)
L.luaL_newstate.restype = ctypes.c_void_p
for fn, at in [("luaL_openlibs", [ctypes.c_void_p]), ("luaL_loadstring", [ctypes.c_void_p, ctypes.c_char_p]),
               ("lua_pcall", [ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int]), ("lua_settop", [ctypes.c_void_p, ctypes.c_int])]:
    getattr(L, fn).argtypes = at
L.lua_tolstring.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p]; L.lua_tolstring.restype = ctypes.c_char_p
st = L.luaL_newstate(); L.luaL_openlibs(st)
def run(code, name):
    rc = L.luaL_loadstring(st, code.encode("utf-8")) or L.lua_pcall(st, 0, 0, 0)
    if rc:
        raise RuntimeError(name + ": " + L.lua_tolstring(st, -1, None).decode("utf-8", "replace"))
run(f'''
local real_open = io.open
io.open = function(p, m) p = tostring(p):gsub("^C:/KenshiModMap/logs/", "{TMP}/"):gsub("^C:/KenshiModMap/state/", "{TMP}/"); return real_open(p, m) end; local __rr = os.remove; os.remove = function(p) p = tostring(p):gsub("^C:/KenshiModMap/state/", "{TMP}/"); return __rr(p) end
Events = {{ h = {{}} }}
function Events.on(n, f) Events.h[n] = f; return n end
function Events.off() end
HOURS = 100
function getGameWorld() return {{ getTimeStamp_inGameHours = function() return {{ getTotalHours = function() return HOURS end }} end }} end
function getPlayerInterface() return {{ getAllPlayerCharacters = function() return {{}} end }} end
JOURNAL = {{ events = {{ {{ id = 1, day = 2, type = "leader_killed", town_name = "Bark", attacker = "X", defender = "Y", leader_name = "L", status = "pending" }} }} }}
KMM_Conductor = {{ state = function() return JOURNAL end }}
''', "stubs")
run(open(SCRIPT, encoding="utf-8").read(), "KMM_Rumors.lua")
run(r'''
local R = KMM_Rumors
local tick = Events.h["GameWorld::charsUpdate"]
local fake = 0; os.clock = function() fake = fake + 100; return fake end
tick()
assert(R.order[1] == "1" and R.events["1"].town == "Bark", "conductor journal not used")
R.told["1|Bark"] = true
local gd = { sdata = {} }
Events.h["PlayerInterface::serialise"](nil, gd)
assert(gd.sdata["kmm_rumors_told"] == "1|Bark", "told not saved: " .. tostring(gd.sdata["kmm_rumors_told"]))
R.told = {}
Events.h["PlayerInterface::loadFromSerialise"](nil, gd)
assert(R.told["1|Bark"], "told not restored")
Events.h["PlayerInterface::loadFromSerialise"](nil, { sdata = {} })
assert(next(R.told) == nil, "told not reset for save without key")
R.told["1|Bark"] = true; HOURS = 500; tick(); HOURS = 10; tick()
assert(next(R.told) == nil, "told not reset when time went back")
io.stdout:write("rumors world test OK" .. string.char(10)); io.stdout:flush()
''', "test")
