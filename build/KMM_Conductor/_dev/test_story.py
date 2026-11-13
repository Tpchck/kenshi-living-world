"""Офлайн-тест STORY (акты мира) дирижёра (LuaJIT из KenshiLua, без игры).
python -I -X utf8 build/KMM_Conductor/_dev/test_story.py   → «OK n checks», код 1 при провале.
Пути C:/KenshiModMap/logs/ перенаправлены во временную папку."""
import ctypes
import os
import sys
import tempfile

DLL = r"C:\Program Files (x86)\Steam\steamapps\workshop\content\233860\3817000612\lua51.dll"
SCRIPT = r"C:\KenshiModMap\build\KMM_Conductor\scripts\init\KMM_Conductor.lua"
TMP = tempfile.mkdtemp(prefix="kmm_story_").replace("\\", "/")

L = ctypes.CDLL(DLL)
L.luaL_newstate.restype = ctypes.c_void_p
L.luaL_openlibs.argtypes = [ctypes.c_void_p]
L.luaL_loadstring.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
L.lua_pcall.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int]
L.lua_tolstring.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p]
L.lua_tolstring.restype = ctypes.c_char_p
L.lua_settop.argtypes = [ctypes.c_void_p, ctypes.c_int]
st = L.luaL_newstate()
L.luaL_openlibs(st)


def run(code, name="chunk"):
    if L.luaL_loadstring(st, code.encode("utf-8")) or L.lua_pcall(st, 0, 0, 0):
        msg = L.lua_tolstring(st, -1, None)
        L.lua_settop(st, 0)
        raise RuntimeError(f"{name}: {msg.decode('utf-8', 'replace') if msg else '?'}")


run(f'''
local real_open = io.open
io.open = function(p, m) p = tostring(p):gsub("^C:/KenshiModMap/logs/", "{TMP}/"):gsub("^C:/KenshiModMap/state/", "{TMP}/"); return real_open(p, m) end; local __rr = os.remove; os.remove = function(p) p = tostring(p):gsub("^C:/KenshiModMap/state/", "{TMP}/"); return __rr(p) end
KenshiLua = {{ log = function(s) end }}
Events = {{ h = {{}} }}
function Events.on(n, f) Events.h[n] = f end
function getGameWorld() error("no game") end
function getPlayerInterface() error("no game") end
''', "stubs")
for _f in sorted(__import__("glob").glob(SCRIPT.replace("KMM_Conductor.lua", "KMM_Conductor*.lua"))): run(open(_f, encoding="utf-8").read(), _f.split("\\")[-1])
run(r'''
N, FAILS = 0, {}
local function check(c, what) N = N + 1; if not c then FAILS[#FAILS + 1] = what end end
local C = KMM_Conductor
local CFG = C.cfg()
local P = CFG.params
local base_raid = P.utility.weights.raid.expansion
local base_inc = P.chaos.incursion_chance
math.randomseed(11)
C.reset(); C.story_reset()
local d = 0
local function adv(n) for _ = 1, n do C.advance(d); d = d + 1 end end
adv(3)
local st = C.story_state()
check(type(st) == "table" and st.act == CFG.params.story.start, "story starts in start act")
check(#st.hist == 1, "hist has first act")
-- квiет: множитель chaos.incursion_chance = 0.5 с силой k
local k = st.k.quiet
check(math.abs(P.chaos.incursion_chance - base_inc * (1 + (0.5 - 1) * k)) < 1e-9, "quiet act scales chaos.incursion_chance")
adv(2)
check(math.abs(P.chaos.incursion_chance - base_inc * (1 + (0.5 - 1) * k)) < 1e-9, "apply is idempotent (no compounding)")
-- принудительный переход по году: прыжок на 3 года
d = 365 * 3; adv(2)
check(st.act ~= "quiet", "act changed after year 3 (state: " .. tostring(st.act) .. ")")
check(#st.hist >= 2, "transition recorded")
local ev = false
for _, e in ipairs(C.state().events) do if tostring(e.type):find("^story_") then ev = true end end
check(ev, "story_<act> event in journal")
-- сейв: состояние переживает сериализацию (она у дирижёра общая) и не ломает базу
local snapshot_act = st.act
-- самоотключение: ломаем S.F, тик падает -> база восстановлена, дальше тишина
local sF = C.state().F
C.state().F = nil
adv(2)
C.state().F = sF
check(P.utility.weights.raid.expansion == base_raid and P.chaos.incursion_chance == base_inc, "base restored after story failure")
local act_after = C.story_state().act
adv(40)
check(C.story_state().act == act_after and P.chaos.incursion_chance == base_inc, "story stays off after failure")
-- выключатель
C.story_reset(); P.story.enabled = false; C.reset(); adv(3)
check(C.story_state() == nil and P.chaos.incursion_chance == base_inc, "enabled=false: no story state, params untouched")
P.story.enabled = true
print(N .. " checks")
if #FAILS > 0 then print("FAILS: " .. table.concat(FAILS, "; ")); error("story test failed") end
''', "test")
print("OK")
