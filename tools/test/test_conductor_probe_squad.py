"""Проба test_mode №2 дирижёра (KMM_Conductor_Runtime, createRandomSquad союзного отряда), B3 §2.3:
шаблон отряда squad: GameData (6-й аргумент, BindingsReference RootObjectFactory) никогда не nil — берётся KMM_Traces.tier_pick + getData(sid, 52);
нет шаблона / нет Traces -> SKIP без вызова движка; отказ движка «bad argument» -> одна попытка, ошибка не выходит из пробы.
Заглушка фабрики строгая, как движок: nil в squad / AItarget, не число в maxnum / sizeMultiplier / squadType -> ошибка.
python -I -X utf8 tools/test/test_conductor_probe_squad.py -> ALL OK / FAIL (код 1)."""
import ctypes
import glob
import os
import re
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import log_sandbox  # noqa: E402

log_sandbox.install()
DLL = r"C:\Program Files (x86)\Steam\steamapps\workshop\content\233860\3817000612\lua51.dll"
B = r"C:\KenshiModMap\build\KMM_Conductor\scripts\init"
TMP = tempfile.mkdtemp(prefix="kmm_probe2_").replace("\\", "/")
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


rt = open(os.path.join(HERE, "test_runtime.py"), encoding="utf-8").read()
run(re.search(r"STUBS = r'''(.*?)'''", rt, re.S).group(1).replace("TMPDIR", TMP), "stubs")
for f in sorted(glob.glob(os.path.join(B, "KMM_Conductor*.lua"))):
    run(open(f, encoding="utf-8").read(), os.path.basename(f))
run(r'''
N, FAILS = 0, {}
function check(c, what) N = N + 1; if not c then FAILS[#FAILS + 1] = what end end
local C, KC = KMM_Conductor, KMM_C_INT
C.reset()
CALLS = {}
local REFUSE = nil
local GW0 = getGameWorld()   -- заглушка test_runtime строит мир заново на каждый вызов: фиксируем один
function getGameWorld() return GW0 end
local fac = GW0.theFactory
fac.createRandomSquad = function(self, f, pos, home, maxnum, b, gd, o, m, ap, perm, target, ttown, mult, sqtype, refresh)
  CALLS[#CALLS + 1] = { gd = gd, target = target, pos = pos, maxnum = maxnum }
  if gd == nil then error("bad argument #6 to 'createRandomSquad' (KenshiLua.GameData expected, got nil)") end
  if target == nil then error("bad argument #11 to 'createRandomSquad' (KenshiLua.hand expected, got nil)") end
  if type(maxnum) ~= "number" or type(mult) ~= "number" or type(sqtype) ~= "number" then error("bad argument (number expected)") end
  if REFUSE then error(REFUSE) end
  return { spawned = true }
end
local pc = { getPosition = function() return { x = 100, y = 5, z = 200 } end, getHandle = function() return { toString = function() return "h_pc" end } end }
KC.player_chars = function() return { pc } end
KC.faction_obj = function(fid) return { id = fid } end
KC.CFG.player_faction = "PF"
KC.S.F = { ALLY = { alive = true }, PF = { player = true, alive = true } }
KC.S.rel.ALLY = { PF = 50 }
local step = KC.test_steps[2]
local function logs() return LOGS or "" end
-- 1. шаблон есть
KMM_Traces = { tier_pick = function(fid, sh) return fid == "ALLY" and "sq_ally_t1" or nil end }
local d0 = KC.S.stats.dispatch
local ok, err = pcall(step)
check(ok, "step 2 runs: " .. tostring(err))
check(#CALLS == 1, "one createRandomSquad call: " .. #CALLS .. " | " .. logs():gsub("\n", " / "):sub(-300))
check(CALLS[1] and CALLS[1].gd ~= nil and CALLS[1].gd.stringID == "sq_ally_t1" and CALLS[1].gd.t == 52, "squad GameData from tier_pick, type 52")
check(CALLS[1] and CALLS[1].target ~= nil, "AItarget hand not nil")
check(KC.S.stats.dispatch == d0 + 1, "stats.dispatch +1")
-- 2. нет шаблона у фракции
CALLS = {}; LOGS = ""
KMM_Traces = { tier_pick = function() return nil end }
ok, err = pcall(step)
check(ok and #CALLS == 0, "no template -> no engine call (" .. #CALLS .. ")")
check(logs():find("SKIP no squad template", 1, true), "no template -> SKIP in log")
-- 3. нет Traces
CALLS = {}; LOGS = ""; KMM_Traces = nil
ok, err = pcall(step)
check(ok and #CALLS == 0 and logs():find("SKIP no squad template", 1, true), "no KMM_Traces -> SKIP")
-- 4. отказ движка «bad argument»: одна попытка, без падения пробы
CALLS = {}; LOGS = ""
KMM_Traces = { tier_pick = function() return "sq_ally_t1" end }
REFUSE = "bad argument #9 to 'createRandomSquad' (KenshiLua.Platoon expected, got nil)"
local d1 = KC.S.stats.dispatch
ok, err = pcall(step)
check(ok, "engine refusal stays inside probe: " .. tostring(err))
check(#CALLS == 1, "bad argument -> no second try: " .. #CALLS)
check(KC.S.stats.dispatch == d1, "refusal -> dispatch not counted")
check(logs():find("ok=false", 1, true), "refusal logged ok=false")
-- 5. прочий отказ (не аргумент): вторая точка пробуется
CALLS = {}; REFUSE = "engine refused squad"
ok, err = pcall(step)
check(ok and #CALLS == 2, "other refusal -> both positions tried: " .. #CALLS)
REFUSE = nil
''', "probe2")
run('io.stdout:write(N, " checks, fails: ", #FAILS, "\\n"); for _, f in ipairs(FAILS) do io.stdout:write("FAIL ", f, "\\n") end; io.stdout:flush(); if #FAILS > 0 then error("FAILS " .. #FAILS) end', "result")
print("ALL OK")
