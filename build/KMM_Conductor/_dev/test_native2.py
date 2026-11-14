"""Offline test native2: BNT.law_of (Faction.myLawEnforcementFaction -> полиция заказчика), KMM_Outlaws.law, крэш-сторож probe_bounty_add (lock на старте -> .off навсегда). python -I -X utf8 build/KMM_Conductor/_dev/test_native2.py -> OK."""
import ctypes, re, sys, tempfile

DLL = r"C:\Program Files (x86)\Steam\steamapps\workshop\content\233860\3817000612\lua51.dll"
B = r"C:\KenshiModMap\build\KMM_Conductor\scripts\init"
TMP = tempfile.mkdtemp(prefix="kmm_native2_").replace("\\", "/")
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
run(open(B + r"\KMM_Outlaws.lua", encoding="utf-8").read(), "KMM_Outlaws.lua")
run(r'''
N, FAILS = 0, {}
function check(c, what) N = N + 1; if not c then FAILS[#FAILS + 1] = what end end
local C = KMM_Conductor
C.reset()
C.cfg().params.outlaws = { sdir = "TMPDIR/" }
local T = KMM_Traces
local tr = C.read_json("traces.json", "C:/KenshiModMap/build/KMM_Conductor/traces.json").factions
local A, LAW
local keys = {}; for fid in pairs(tr) do keys[#keys + 1] = fid end; table.sort(keys)   -- стабильный порядок; полиция — живая фракция
for _, fid in ipairs(keys) do if not A then A = fid elseif not LAW and fid ~= A and not (C.alive and C.alive(fid) == false) then LAW = fid end end
local function F(sid, law) local f = { id = sid, data = { stringID = sid } }; function f:getData() return self.data end; f.myLawEnforcementFaction = law; return f end
local old = getGameWorld
getGameWorld = function()
  local w = old()
  w.factionMgr = { getFactionByStringID = function(self, sid)
    if sid == A then return F(A, F(LAW)) end
    if sid == "nolaw" then return F("nolaw", nil) end
    if sid == "foreign" then return F("foreign", F("not_in_traces")) end
    return F(sid) end }
  return w
end
FIRE("GameWorld::charsUpdate", {})
local B = T.bounty()
check(B and B.law_of, "Traces exposes bounty().law_of")
check(B.law_of(A) == LAW, "law_of -> law enforcement faction: " .. tostring(B.law_of(A)))
check(B.law_of("nolaw") == "nolaw", "no law faction -> self")
check(B.law_of("foreign") == "foreign", "law faction unknown to traces.json -> self")
local M = KMM_Outlaws._M
check(M.law(A) == LAW, "Outlaws.law uses Traces law_of")
-- крэш-сторож: прошлая сессия упала (lock остался) -> вызов отключён навсегда, функция не вызывается
local f = io.open("TMPDIR/probe_bounty_add.lock", "w"); f:write("1"); f:close()
local called = false
check(M.probe_call("bounty_add", function() called = true end) == false and not called, "stale lock -> method disabled, not called")
local off = io.open("TMPDIR/probe_bounty_add.off", "r")
check(off ~= nil, ".off written"); if off then off:close() end
M.PROBE = {}
check(M.probe_call("bounty_add", function() called = true end) == false and not called, ".off persists after restart")
-- чистый вызов: lock снят после успеха
local n = 0
check(M.probe_call("other_x", function() n = n + 1 end) == true and n == 1, "clean probe call runs")
local lk = io.open("TMPDIR/probe_other_x.lock", "r")
check(lk == nil, "lock removed after success"); if lk then lk:close() end
RESULT = #FAILS == 0 and ("OK " .. N) or ("FAIL: " .. table.concat(FAILS, "; "))
'''.replace("TMPDIR", TMP), "test")
run("")
L.lua_getfield.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_char_p]
L.lua_getfield(st, -10002, b"RESULT")
r = L.lua_tolstring(st, -1, None).decode()
print(r)
sys.exit(0 if r.startswith("OK") else 1)
