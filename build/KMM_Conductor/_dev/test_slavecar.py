"""Offline test: slave_caravan event -> Slave Traders caravan + guard near player. python -I -X utf8 build/KMM_Conductor/_dev/test_slavecar.py -> OK."""
import ctypes, re, sys, tempfile

DLL = r"C:\Program Files (x86)\Steam\steamapps\workshop\content\233860\3817000612\lua51.dll"
B = r"C:\KenshiModMap\build\KMM_Conductor\scripts\init"
TMP = tempfile.mkdtemp(prefix="kmm_slavecar_").replace("\\", "/")
L = ctypes.CDLL(DLL)
L.luaL_newstate.restype = ctypes.c_void_p
for fn, at in [("luaL_openlibs", [ctypes.c_void_p]), ("luaL_loadstring", [ctypes.c_void_p, ctypes.c_char_p]),
               ("lua_pcall", [ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int])]:
    getattr(L, fn).argtypes = at
L.lua_tolstring.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p]
L.lua_tolstring.restype = ctypes.c_char_p
st = L.luaL_newstate()
L.luaL_openlibs(st)


def run(code, name="chunk"):
    if L.luaL_loadstring(st, code.encode("utf-8")) or L.lua_pcall(st, 0, 0, 0):
        msg = L.lua_tolstring(st, -1, None)
        raise RuntimeError(f"{name}: {msg.decode('utf-8', 'replace') if msg else '?'}")


rt = open(r"C:\KenshiModMap\tools\test\test_runtime.py", encoding="utf-8").read()
run(re.search(r"STUBS = r'''(.*?)'''", rt, re.S).group(1).replace("TMPDIR", TMP), "stubs")
run("math.randomseed(20261113)", "seed")
for _f in sorted(__import__("glob").glob(B + r"\KMM_Conductor*.lua")): run(open(_f, encoding="utf-8").read(), _f.split("\\")[-1])
run(open(B + r"\KMM_Traces.lua", encoding="utf-8").read(), "KMM_Traces.lua")
run(r'''
N, FAILS = 0, {}
function check(c, what) N = N + 1; if not c then FAILS[#FAILS + 1] = what end end
local C = KMM_Conductor
C.reset()
local TP = C.cfg().params.traces
TP.first_hour_traces = 0; TP.max_per_day = 1000; TP.max_queue = 1000; TP.arrive_enabled = false
TP.bounty = { enabled = false }
local tr = C.read_json("traces.json", "C:/KenshiModMap/build/KMM_Conductor/traces.json")
local pf = C.cfg().player_faction
local OWN
for fid, f in pairs(C.state().F) do if f.alive and not f.player and fid ~= pf and C.fpos(fid) and not tr.caravans[fid] then OWN = fid; break end end
check(OWN, "owner faction with position")
local ox, oz = C.fpos(OWN)
PCS = {}; CHARS = {}
local ch = MKCH("PC1", pf or "player", ox + 500, oz + 500, { player = true, platoon = "player_squad" })
PCS[1] = ch; CHARS[1] = ch
local T = KMM_Traces
local function pump(n) for i = 1, n do CLOCK = CLOCK + 80; DAYV = DAYV + 0.0001; FIRE("GameWorld::charsUpdate", {}) end end
pump(3)
local n0 = #SPAWNS
C.emit({ type = "slave_caravan", fid = OWN, n = 4, text = "test" })
pump(1)
local qk = {}; for _, j in ipairs(T.queue()) do qk[#qk+1] = j.kind end
DBG = "queue=" .. table.concat(qk, ",") .. " ev=" .. tostring(C.state().events[#C.state().events].type) .. " fpos=" .. tostring(ox) .. " evid=" .. tostring(C.state().events[#C.state().events].id) .. " dis=" .. (function() local o={} for k,v in pairs(T.disabled() or {}) do o[#o+1]=k end return table.concat(o,",") end)() .. " spawned=" .. tostring(T.stats().spawned)
pump(60)
local car, guard = false, false
for i = n0 + 1, #SPAWNS do local s = SPAWNS[i]
  if s.fid == "1084-gamedata.base" and s.sid == tr.caravans["1084-gamedata.base"] then car = true end
  if s.fid == "1084-gamedata.base" and s.sid ~= tr.caravans["1084-gamedata.base"] then guard = true end
end
check(car, "slave caravan spawned (Slave Traders caravan template)")
check(guard, "caravan guard spawned")
check((T.stats().by_kind or {}).slave_caravan == 1, "by_kind slave_caravan = 1: " .. tostring((T.stats().by_kind or {}).slave_caravan))
-- EXT API
local n2, got = #SPAWNS, nil
check(T.request({ tag = "test_ext", fid = "1084-gamedata.base", n = 2, on_spawn = function(pls) got = #pls end }), "request accepted")
check(T.near(ox, oz) == true and T.near(ox + 9e6, oz) == false, "near()")
pump(40)
check(#SPAWNS >= n2 + 2 and got == 2 and (T.stats().by_tag or {}).test_ext == 1, "ext spawned 2 + on_spawn: " .. tostring(got))
RESULT = #FAILS == 0 and ("OK " .. N) or (DBG .. " FAIL: " .. table.concat(FAILS, "; "))
''', "test")
run("")
L.lua_getfield.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_char_p]
L.lua_getfield(st, -10002, b"RESULT")
r = L.lua_tolstring(st, -1, None).decode()
print(r)
sys.exit(0 if r.startswith("OK") else 1)
