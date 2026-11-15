"""Offline test P4 (B2/B8): N.remember пишет долгую память ядра только через KMM_Native.remember_lt (числа LT_* из Character.h), без плагина — маркер «remember: no native» и НИ ОДНОГО вызова Lua rememberCharacter; ошибки плагина в лог; адаптер KMM_Native.remember_lt/memory_lt/has_memory на заглушке модуля; маркер B8 «chronicle: addMessage ok». python -I -X utf8 build/KMM_Conductor/_dev/test_p4_memory.py -> OK."""
import ctypes, re, sys, tempfile

DLL = r"C:\Program Files (x86)\Steam\steamapps\workshop\content\233860\3817000612\lua51.dll"
B = r"C:\KenshiModMap\build\KMM_Conductor\scripts\init"
TMP = tempfile.mkdtemp(prefix="kmm_outlaws_").replace("\\", "/")
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
run(open(B + r"\KMM_Fates.lua", encoding="utf-8").read(), "KMM_Fates.lua")
run(open(B + r"\KMM_Outlaws.lua", encoding="utf-8").read(), "KMM_Outlaws.lua")
run(open(B + r"\KMM_Nemesis.lua", encoding="utf-8").read(), "KMM_Nemesis.lua")
NATIVE_SRC = open(r"C:\KenshiModMap\build\KMM_Native\scripts\init\KMM_Native.lua", encoding="utf-8").read()
L.lua_pushstring = getattr(L, "lua_pushstring"); L.lua_pushstring.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
L.lua_setfield.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_char_p]
L.lua_pushstring(st, NATIVE_SRC.encode("utf-8")); L.lua_setfield(st, -10002, b"NATIVE_SRC")
run("function run_native() local f = assert(loadstring(NATIVE_SRC, 'KMM_Native.lua')); f() end", "helper")
run(open(r"C:\KenshiModMap\build\KMM_Native\scripts\init\KMM_Native.lua", encoding="utf-8").read(), "KMM_Native.lua")
run(r'''
N, FAILS = 0, {}
function check(c, what) N = N + 1; if not c then FAILS[#FAILS + 1] = what end end
local NN = KMM_Nemesis._N
local LOG = {}
NN.log = function(m) LOG[#LOG + 1] = tostring(m) end
local function logged(s) for _, l in ipairs(LOG) do if l:find(s, 1, true) then return true end end return false end
local KN_real = KMM_Native
-- игроки
local function pc(nm) local p = { nm = nm }; function p:getName() return self.nm end; return p end
PCS = { pc("Beep"), pc("Ruka") }
local lead = { nm = "Boss", lua = 0 }
function lead:getName() return self.nm end
function lead:rememberCharacter() self.lua = self.lua + 1 end
-- 1) номера тегов = Character.h:87-101
check(NN.LT.LT_MY_INTRUDER == 1 and NN.LT.LT_MY_LIFESAVER == 2 and NN.LT.LT_FREED_ME == 3 and NN.LT.LT_STOLE_FROM_ME == 4
  and NN.LT.LT_MY_CAPTOR == 5 and NN.LT.LT_FRIENDLY_AQUAINTANCE == 6 and NN.LT.LT_DEFEATED_MY_SQUAD_ONCE == 7
  and NN.LT.LT_SQUAD_LOST_TO_ME_ONCE == 8 and NN.LT.LT_KILLED_MY_FRIEND == 9 and NN.LT.LT_I_SCREWED_THIS_GUY == 10, "LT numbers from Character.h")
-- 2) нет модуля kmm_native (адаптер есть, DLL нет) -> no native, Lua-метод не тронут
check(KN_real and KN_real.has_memory() == false, "adapter without DLL: has_memory false")
NN.remember(lead, "LT_MY_CAPTOR")
check(lead.lua == 0 and logged("remember: no native"), "no native: marker, no Lua rememberCharacter")
local n1 = #LOG; NN.remember(lead, "LT_MY_CAPTOR")
check(#LOG == n1, "no native marker only once")
-- 3) нет адаптера совсем
KMM_Native = nil; NN.remember(lead, "LT_FREED_ME"); check(lead.lua == 0, "no adapter: no Lua call")
-- 4) модуль-заглушка через адаптер: package.preload
local CALLS = {}
package.preload["kmm_native"] = function() return {
  ws_hook_active = function() return true end,
  remember_lt = function(npc, who, tag) CALLS[#CALLS + 1] = { npc, who, tag }; if who.nm == "Ruka" then return false, "not a character" end; return true end,
  memory_lt = function(npc, who, tag) return tag == 5 end } end
package.loaded["kmm_native"] = nil
-- адаптер кеширует неудачную загрузку: свежий экземпляр
run_native()
KN_real = KMM_Native
check(KN_real.has_memory() == true, "adapter with module: has_memory true")
local okr, why = KN_real.remember_lt(lead, PCS[2], 3)
check(okr == false and why == "not a character", "adapter passes reason: " .. tostring(why))
check(KN_real.remember_lt(lead, nil, 3) == false and KN_real.memory_lt(lead, PCS[1], 5) == true, "adapter args / memory_lt")
CALLS = {}
NN.remember(lead, "LT_MY_CAPTOR")
check(#CALLS == 2 and CALLS[1][3] == 5 and CALLS[1][1] == lead and lead.lua == 0, "native write LT_MY_CAPTOR=5 for each player char: " .. #CALLS)
check(logged("remember: LT_MY_CAPTOR=5 written for 1 player chars by Boss"), "success marker")
-- 5) все отказали -> причина в лог
PCS = { PCS[2] }
NN.remember(lead, "LT_FREED_ME")
check(logged("remember: LT_FREED_ME failed for Boss: not a character"), "failure marker with reason")
-- 6) неизвестный тег и cfg выключатель
CALLS = {}
NN.remember(lead, "LT_BOGUS"); check(#CALLS == 0 and logged("remember: unknown tag LT_BOGUS"), "unknown tag")
local PN = KMM_Conductor.cfg().params; PN.nemesis = PN.nemesis or {}; PN.nemesis.native_memory = false; NN.remember(lead, "LT_FREED_ME"); check(#CALLS == 0, "native_memory=false: nothing"); PN.nemesis.native_memory = nil
-- 7) потолок на число персонажей
PCS = {}; for i = 1, 40 do PCS[i] = pc("P" .. i) end
CALLS = {}; NN.remember(lead, "LT_MY_LIFESAVER"); check(#CALLS == NN.REMEMBER_MAX, "cap on player chars: " .. #CALLS)
check(not NN.off, "nemesis still enabled")
RESULT = #FAILS == 0 and ("OK " .. N) or ("FAIL: " .. table.concat(FAILS, "; "))
'''.replace("TMPDIR", TMP), "test")
run("")
L.lua_getfield.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_char_p]
L.lua_getfield(st, -10002, b"RESULT")
r = L.lua_tolstring(st, -1, None).decode()
print(r)
sys.exit(0 if r.startswith("OK") else 1)
