"""Офлайн-тест реестра здоровья KMM_Gov (HEALTH, 2026-11-15) на lua51.dll из KenshiLua.
Запуск из папки теста: python -I -X utf8 ../../../tools/test/log_sandbox.py test_health.py"""
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
local R, N = {}, 0
local function check(c, m) N = N + 1; if not c then R[#R+1] = "FAIL " .. m end end
local function lg() local f = real_open("%(tmp)s/debug.log", "r"); local s = f and f:read("*a") or ""; if f then f:close() end; return s end
dofile("%(gov)s")
local G = KMM_Gov
check(type(G.health) == "table" and type(G.health.mech) == "table", "health table published")
for _, f in ipairs({ "h_reg", "h_up", "h_ok", "h_fail", "h_off", "h_get", "health_list", "h_guard", "health_line" }) do
  check(type(G[f]) == "function", "api " .. f)
end
-- неизвестная механика можно запускать
check(G.h_up("X.none") == true, "unknown key is up")
-- отказ -> пауза 60, повтор, второй отказ -> 300, третий -> 1800, дальше 1800
check(G.h_fail("A.m", "boom1") == 60, "fail #1 -> 60")
local r = G.health.mech["A.m"]
check(r.state == "pause" and r.reason == "error" and r.err == "boom1" and r.fails == 1 and r.mod == "A", "record after fail #1")
check(G.h_up("A.m") == false, "paused -> not up")
CLOCK = 59; check(G.h_up("A.m") == false, "still paused at 59 s")
CLOCK = 60; check(G.h_up("A.m") == true and G.health.mech["A.m"].state == "retry", "retry at 60 s")
check(G.h_up("A.m") == true, "retry stays up until verdict")
check(G.h_fail("A.m", "boom2") == 300, "fail #2 -> 300")
CLOCK = 360; G.h_up("A.m"); check(G.h_fail("A.m", "boom3") == 1800, "fail #3 -> 1800")
CLOCK = 2160; G.h_up("A.m"); check(G.h_fail("A.m", "boom4") == 1800, "fail #4 stays 1800")
check(G.health.mech["A.m"].total == 4, "total counts fails")
-- восстановление
CLOCK = 3960; check(G.h_up("A.m") == true, "retry after 1800")
G.h_ok("A.m")
r = G.health.mech["A.m"]
check(r.state == "ok" and r.recovered == 1, "recovered after ok")
check(lg():find("[KMM_Gov] health A.m: recovered after 4 fails", 1, true) ~= nil, "recovered log line")
-- скоро снова отказ -> шаг продолжает расти; долго работал -> шаг с начала
CLOCK = 4000; check(G.h_fail("A.m", "again") == 1800, "fail soon after recovery keeps the step")
CLOCK = 5800; G.h_up("A.m"); G.h_ok("A.m")
CLOCK = 5800 + 1801; check(G.h_fail("A.m", "much later") == 60, "fail long after recovery restarts at 60")
-- навсегда: только h_off; h_fail после off -> false, up -> false
G.h_off("B.api", "no ZoneSmell:addSmell", "noapi")
check(G.h_up("B.api") == false and G.health.mech["B.api"].state == "off" and G.health.mech["B.api"].reason == "noapi", "off noapi")
check(G.h_fail("B.api", "x") == false, "fail after off -> false")
CLOCK = 1e9; check(G.h_up("B.api") == false, "off never comes back")
G.h_off("C.crash", "lock", "crash"); check(G.health.mech["C.crash"].reason == "crash", "off crash reason")
check(lg():find("[KMM_Gov] health B.api: OFF (noapi): no ZoneSmell:addSmell", 1, true) ~= nil, "off log line")
-- h_guard
local calls = 0
local ok, v = G.h_guard("D.g", function(a) calls = calls + 1; return a * 2 end, 21)
check(ok == true and v == 42 and calls == 1, "guard ok passes results")
ok, v = G.h_guard("D.g", function() error("bad") end)
check(ok == false and tostring(v):find("bad", 1, true) and G.health.mech["D.g"].state == "pause", "guard fail -> pause")
ok, v = G.h_guard("D.g", function() calls = calls + 1 end)
check(ok == nil and v == "paused" and calls == 1, "guard skips while paused")
-- список отсортирован по ключу и даёт копии
local list = G.health_list()
local keys = {}
for i, e in ipairs(list) do keys[i] = e.key end
local sorted = true
for i = 2, #keys do if keys[i - 1] > keys[i] then sorted = false end end
check(#list >= 4 and sorted, "health_list sorted by key")
list[1].state = "changed"; check(G.health.mech[keys[1]].state ~= "changed", "health_list returns copies")
local cp = G.h_get("B.api"); cp.state = "x"; check(G.health.mech["B.api"].state == "off", "h_get returns a copy")
-- строка сводки
local hl = G.health_line()
check(type(hl) == "string" and hl:find("B.api(noapi)", 1, true) and hl:find("D.g(#1 60s)", 1, true), "health_line: " .. tostring(hl))
-- длинная ошибка: не больше 300 байт, без разорванного UTF-8
G.h_fail("E.long", string.rep("ж", 400))
local e = G.health.mech["E.long"].err
check(#e <= 300 and #e % 2 == 0 and e:sub(-2) == "ж", "long error cut at a UTF-8 boundary (" .. #e .. ")")
-- сводка report_s пишет строку health
G.cfg.report_s = 10
CLOCK = 2e9; G.run("m", function() end)
CLOCK = 2e9 + 11; G.run("m", function() end)
check(lg():find("[KMM_Gov] health: ok ", 1, true) ~= nil, "summary health line")
-- сломанный реестр/cfg не роняет вызывающих
G.cfg = nil
check(G.h_fail("F.nocfg", "e") == 60, "no cfg -> default steps")
G.health.mech = nil
check(G.h_up("Z") == true and G.h_fail("Z", "e") == nil, "broken registry: up true, fail nil (caller falls back)")
check(type(G.health_list()) == "table" and G.health_line() == nil, "broken registry: list/line safe")
-- реестр не сериализуется в сейв: Gov ничего не пишет в состояние дирижёра (поля только в _G.KMM_Gov)
check(rawget(_G, "KMM_Conductor") == nil, "registry lives outside conductor state")
R_OUT = #R == 0 and ("OK " .. N) or table.concat(R, "; ")
"""
code = CODE.replace("%(tmp)s", tmp).replace("%(gov)s", GOV)
bad = L.luaL_loadstring(st, code.encode()) or L.lua_pcall(st, 0, 0, 0)
if bad:
    print("LUA ERROR:", L.lua_tolstring(st, -1, None).decode("utf-8", "replace")); sys.exit(1)
L.luaL_loadstring(st, b"return R_OUT"); L.lua_pcall(st, 0, 1, 0)
out = L.lua_tolstring(st, -1, None).decode()
print("test_health:", out); sys.exit(0 if out.startswith("OK") else 1)
