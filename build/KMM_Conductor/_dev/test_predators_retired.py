"""KMM_Predators retired 2026-11-16 (crash in ZoneSmell::periodicUpdate; owner: vanilla patrols and nests are enough).
Checks: module reports disabled, tick and bus never call addSmell, Herds does not use smell. Old tests: _dev/_retired/."""
import ctypes, re, sys, tempfile

DLL = r"C:\Program Files (x86)\Steam\steamapps\workshop\content\233860\3817000612\lua51.dll"
B = r"C:\KenshiModMap\build\KMM_Conductor\scripts\init"
TMP = tempfile.mkdtemp(prefix="kmm_r4_").replace("\\", "/")
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
# свой стаб зоны: ZoneManager:getZoneMap(v).zoneSmell с addSmell/getGeneralSmellLevel
run(r'''
ZS_CALLS, ZS_LVL, ZS_RISE, ZS_FAIL, ZS_LOCK = {}, 0, 0.5, false, false
local zs = {}
function zs:addSmell(t, key, pos)
  if ZS_FAIL then error("bad argument #2 to 'addSmell' (userdata expected)") end
  local f = io.open("TMPDIR/probe_addSmell.lock", "r"); if f then ZS_LOCK = true; f:close() end
  ZS_CALLS[#ZS_CALLS + 1] = { t = t, key = key, x = pos.x, z = pos.z }
  if t ~= 0 then ZS_LVL = ZS_LVL + ZS_RISE end
end
function zs:getGeneralSmellLevel(t) return ZS_LVL end
local zm = { zoneSmell = zs }
local gw0 = getGameWorld
getGameWorld = function() local g = gw0(); g.zoneMgr = { getZoneMap = function(self, v) return zm end }; return g end
'''.replace("TMPDIR", TMP), "zone stub")
run("math.randomseed(20261115)", "seed")
for f in [p.split("\\")[-1] for p in sorted(__import__("glob").glob(B + r"\KMM_Conductor*.lua"))] + ["KMM_Traces.lua", "KMM_Predators.lua", "KMM_Herds.lua"]:
    run(open(B + "\\" + f, encoding="utf-8").read(), f)
run('KMM_Predators.P.sdir = "%s/"' % TMP, "sdir")
run(r'''
N, FAILS = 0, {}
function check(c, what) N = N + 1; if not c then FAILS[#FAILS + 1] = what end end
local C, Pr, H = KMM_Conductor, KMM_Predators, KMM_Herds
C.reset(); C.advance(10); DAYV = 10
check(Pr.retired == true, "retired flag")
check(Pr.disabled() == true, "disabled() true")
Pr.tick(); Pr.tick()
pcall(Pr.on_bus, { type = "deed", kind = "killed", x = 1, z = 1 })
local ok, r1, r2, r3 = pcall(Pr.smell, 1, 1, "blood", nil, "test")
check(ok and r1 == false, "smell refused")
check(#ZS_CALLS == 0, "addSmell never called")
check(Pr.smell_retract("x") == false, "retract no-op")
for d = 11, 40 do C.advance(d); DAYV = d; pcall(H._daily, d); pcall(H._materialize, d) end
local hs = H.stats()
check((hs.smell or 0) == 0 and (hs.smell_took or 0) == 0, "herds never used smell")
local D = H.data(); check(D == nil or D.P.smell_first == false, "herds smell_first off")
check(#ZS_CALLS == 0, "addSmell never called (end)")
local f = io.open("TMPDIR/res.txt", "w"); f:write(#FAILS == 0 and ("OK " .. N) or ("FAIL: " .. table.concat(FAILS, "; "))); f:close()
'''.replace("TMPDIR", TMP), "test")
res = open(TMP + "/res.txt", encoding="utf-8").read()
print(res)
sys.exit(0 if res.startswith("OK") else 1)
