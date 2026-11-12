"""Офлайн-тест KMM_Gov на lua51.dll из KenshiLua. python -I -X utf8 build/KMM_Conductor/_dev/test_gov.py"""
import ctypes, sys, tempfile
DLL = r"C:\Program Files (x86)\Steam\steamapps\workshop\content\233860\3817000612\lua51.dll"
GOV = "C:/KenshiModMap/build/KMM_Conductor/scripts/init/KMM_Gov.lua"
L = ctypes.CDLL(DLL)
L.luaL_newstate.restype = ctypes.c_void_p
for n, a in (("luaL_openlibs", [ctypes.c_void_p]), ("luaL_loadstring", [ctypes.c_void_p, ctypes.c_char_p]),
             ("lua_pcall", [ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int]),
             ("lua_tolstring", [ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p]), ("lua_close", [ctypes.c_void_p])):
    getattr(L, n).argtypes = a
L.lua_tolstring.restype = ctypes.c_char_p
tmp = tempfile.mkdtemp().replace("\\", "/")
st = L.luaL_newstate(); L.luaL_openlibs(st)
CODE = r"""
local real_open = io.open
io.open = function(p, m) p = tostring(p):gsub("^C:/KenshiModMap/logs/", "%(tmp)s/"); return real_open(p, m) end
CLOCK = 0; os.clock = function() return CLOCK end
local R = {}
local function check(c, m) if not c then R[#R+1] = "FAIL " .. m end end
-- модуль без Gov
local calls = 0
local function mod() calls = calls + 1; return "x" end
check(_G.KMM_Gov == nil, "gov absent")
check(mod() == "x" and calls == 1, "no gov works")
dofile("%(gov)s")
check(type(KMM_Gov.run) == "function" and type(KMM_Gov.stats) == "function", "api")
-- быстрый не трогается
local fast = 0
for i = 1, 100 do KMM_Gov.run("fast", function() fast = fast + 1; CLOCK = CLOCK + 0.0001 end) end
check(fast == 100 and KMM_Gov.stats().fast.n == 1, "fast untouched")
-- медленный троттлится (3 мс на вызов > 0.6 мс)
local slow = 0
local function sl() slow = slow + 1; CLOCK = CLOCK + 0.003 end
for i = 1, 200 do KMM_Gov.run("slow", sl) end
local s = KMM_Gov.stats().slow
check(s.n == 8, "slow throttled to 8, n=" .. tostring(s.n))
check(slow < 100 and s.skipped > 0, "slow skipped, ran=" .. slow)
-- восстановление: теперь быстрый
local function sf() CLOCK = CLOCK + 0.00005 end
for i = 1, 3000 do KMM_Gov.run("slow", sf) end
check(KMM_Gov.stats().slow.n == 1, "slow recovered n=" .. tostring(KMM_Gov.stats().slow.n))
-- пики: 3 подряд >8 мс при низком среднем
for i = 1, 20 do KMM_Gov.run("pk", function() CLOCK = CLOCK + 0.00001 end) end
for i = 1, 3 do KMM_Gov.run("pk", function() CLOCK = CLOCK + 0.01 end) end
check(KMM_Gov.stats().pk.n == 2, "peak throttle n=" .. tostring(KMM_Gov.stats().pk.n))
-- возвращаемые значения и ошибки fn пробрасываются
local a, b = KMM_Gov.run("ret", function(x, y) return x + y, "k" end, 2, 3)
check(a == 5 and b == "k", "returns")
check(not pcall(KMM_Gov.run, "err", function() error("boom") end), "error propagates")
-- сломанный Gov не ломает модули
KMM_Gov._s = nil; KMM_Gov.cfg = nil
local n0 = calls
check(KMM_Gov.run("m", mod) == "x" and calls == n0 + 1, "broken gov: fn still called")
os.clock = function() error("clock broken") end
check(KMM_Gov.run("m", mod) == "x", "broken clock: fn still called")
-- лог
local f = real_open("%(tmp)s/debug.log", "r"); local log = f and f:read("*a") or ""; if f then f:close() end
check(log:find("%[KMM_Gov%] slow: throttle") ~= nil, "log line")
R_OUT = #R == 0 and "OK" or table.concat(R, "; ")
"""
code = CODE.replace("%(tmp)s", tmp).replace("%(gov)s", GOV)
bad = L.luaL_loadstring(st, code.encode()) or L.lua_pcall(st, 0, 0, 0)
if bad:
    print("LUA ERROR:", L.lua_tolstring(st, -1, None).decode("utf-8", "replace")); sys.exit(1)
L.luaL_loadstring(st, b"return R_OUT"); L.lua_pcall(st, 0, 1, 0)
out = L.lua_tolstring(st, -1, None).decode()
print("test_gov:", out); sys.exit(0 if out == "OK" else 1)
