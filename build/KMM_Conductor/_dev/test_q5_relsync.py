"""Offline test Q5: отношения живут в ядре. Ванильная дельта (дело) вливается в модель, своё изменение уходит ядру дельтой,
дело из шины deed не считается дважды, офлайн без getFactionRelation - абсолютная запись как раньше, ошибка выключает только сверку.
python -I -X utf8 build/KMM_Conductor/_dev/test_q5_relsync.py -> OK."""
import ctypes, re, sys, tempfile

DLL = r"C:\Program Files (x86)\Steam\steamapps\workshop\content\233860\3817000612\lua51.dll"
B = r"C:\KenshiModMap\build\KMM_Conductor\scripts\init"
TMP = tempfile.mkdtemp(prefix="kmm_q5_").replace("\\", "/")
L = ctypes.CDLL(DLL)
L.luaL_newstate.restype = ctypes.c_void_p
for fn, at in [("luaL_openlibs", [ctypes.c_void_p]), ("luaL_loadstring", [ctypes.c_void_p, ctypes.c_char_p]),
               ("lua_pcall", [ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int])]:
    getattr(L, fn).argtypes = at
L.lua_tolstring.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p]
L.lua_tolstring.restype = ctypes.c_char_p
L.lua_getfield.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_char_p]
st = L.luaL_newstate()
L.luaL_openlibs(st)


def run(code, name="chunk"):
    if L.luaL_loadstring(st, code.encode("utf-8")) or L.lua_pcall(st, 0, 0, 0):
        msg = L.lua_tolstring(st, -1, None)
        raise RuntimeError(f"{name}: {msg.decode('utf-8', 'replace') if msg else '?'}")


rt = open(r"C:\KenshiModMap\tools\test\test_runtime.py", encoding="utf-8").read()
run(re.search(r"STUBS = r'''(.*?)'''", rt, re.S).group(1).replace("TMPDIR", TMP), "stubs")
run("math.randomseed(20261115)", "seed")
for _f in sorted(__import__("glob").glob(B + r"\KMM_Conductor*.lua")): run(open(_f, encoding="utf-8").read(), _f.split("\\")[-1])
TEST = r'''
N, FAILS = 0, {}
function check(c, what) N = N + 1; if not c then FAILS[#FAILS + 1] = what end end
local C = KMM_Conductor
C.reset()
local S = C.state()
local P = C.cfg().params
P.materialize.relations_enabled = true
P.guard = P.guard or {}; P.guard.debug_log = "TMPDIR/debug.log"
P.chronicle_path = "TMPDIR/chronicle.log"
P.materialize.relsync = { every_s = 1, mark_every = 1 }
local function logtxt() local f = io.open("TMPDIR/debug.log", "r"); if not f then return "" end; local s = f:read("*a"); f:close(); return s end
local ids = {}; for fid, f in pairs(S.F) do if f.alive and not f.player then ids[#ids + 1] = fid end end; table.sort(ids)
local A, Bf, Cf = ids[1], ids[2], ids[3]
local function w() CLOCK = CLOCK + 2; C.write_rel_test() end
local function dirty(a, b) S.dirty_rel[a .. "|" .. b] = true end
local function setm(a, b, v) S.rel[a][b], S.rel[b][a] = v, v end
local function hint(a, b) C.emit({ type = "deed", kind = "killed", tone = "harm", a = a, b = b, text = "test deed" }) end
S.dirty_rel = {}
-- 1. первая запись пары - абсолютная (семя/лор), пара согласована
setm(A, Bf, -30); dirty(A, Bf); w()
check(FAC(A).rel[Bf] == -30 and FAC(Bf).rel[A] == -30, "first write absolute: " .. tostring(FAC(A).rel[Bf]))
check(S.relq and S.relq[A < Bf and (A .. "|" .. Bf) or (Bf .. "|" .. A)] == -30, "pair aligned (relq)")
-- 2. ядро само уронило отношение (игрок/NPC убил своего): дельта вливается в модель, ядро не затирается
FAC(A).rel[Bf], FAC(Bf).rel[A] = -42, -40
hint(A, Bf); w()
check(S.rel[A][Bf] == -42 and S.rel[Bf][A] == -42, "vanilla delta merged into model: " .. tostring(S.rel[A][Bf]))
check(FAC(A).rel[Bf] == -42 and FAC(Bf).rel[A] == -40, "core untouched by merge")
-- 3. дело не считается дважды: ещё сверки без изменений ядра - модель стоит
hint(A, Bf); w(); w()
check(S.rel[A][Bf] == -42, "deed not counted twice: " .. tostring(S.rel[A][Bf]))
-- 4. своё изменение дирижёра (+10) уходит ядру дельтой, свежая ванильная дельта (-5) сохраняется
setm(A, Bf, S.rel[A][Bf] + 10)
FAC(A).rel[Bf], FAC(Bf).rel[A] = -47, -45
dirty(A, Bf); w()
check(FAC(A).rel[Bf] == -37 and FAC(Bf).rel[A] == -35, "own change as delta, vanilla kept: " .. tostring(FAC(A).rel[Bf]) .. "/" .. tostring(FAC(Bf).rel[A]))
check(S.rel[A][Bf] == -37, "model = own + vanilla: " .. tostring(S.rel[A][Bf]))
-- 5. дробная дельта копится в ядре до целого
FAC(A).rel[Bf] = -37.4; hint(A, Bf); w()
check(S.rel[A][Bf] == -37, "fraction < 1 not merged yet")
FAC(A).rel[Bf] = -38.2; hint(A, Bf); w()
check(S.rel[A][Bf] == -38, "accumulated fraction merged: " .. tostring(S.rel[A][Bf]))
-- 6. пары игрока сверяются по кругу без подсказки
local pf = C.cfg().player_faction
if pf and S.F[pf] then
  local pids = {}; for fid in pairs(S.F) do pids[#pids + 1] = fid end; table.sort(pids)
  local o = pids[1] == pf and pids[2] or pids[1]
  for _ = 1, 40 do w() end   -- круг пар игрока: seen взят
  local m0 = (S.rel[pf] and S.rel[pf][o]) or 0
  FAC(pf).rel[o] = (FAC(pf).rel[o] or 0) - 15
  for _ = 1, 40 do w() end
  check(((S.rel[pf] and S.rel[pf][o]) or 0) == math.max(-100, m0 - 15), "player pair synced without hint: " .. tostring(S.rel[pf] and S.rel[pf][o]))
end
-- 7. маркер расхождения/сверки в debug.log
check(logtxt():find("RELSYNC steps=", 1, true) ~= nil, "RELSYNC marker in debug.log")
check(logtxt():find("RELSYNC first merge", 1, true) ~= nil, "first merge marker")
-- 8. офлайн без getFactionRelation: запись абсолютная, сверка не падает
local fc = FAC(Cf); local saved = fc.relations.getFactionRelation; fc.relations.getFactionRelation = nil
setm(A, Cf, -20); dirty(A, Cf); w()
setm(A, Cf, -25); dirty(A, Cf); w()
check(FAC(A).rel[Cf] == -25 and fc.rel[A] == -25, "no core read: absolute write as before Q5")
check(logtxt():find("relsync disabled", 1, true) == nil, "no core read is not an error")
fc.relations.getFactionRelation = saved
-- 9. новый мир (reset): старые числа ядра не сравниваются - нет ложной дельты
C.reset(); S = C.state(); S.dirty_rel = {}
local m9 = S.rel[A][Bf] or 0
hint(A, Bf); w()
check((S.rel[A][Bf] or 0) == m9, "new world: no spurious merge: " .. tostring(S.rel[A][Bf]) .. " vs " .. tostring(m9))
-- 10. ошибка в сверке выключает только её; запись идёт абсолютной
P.materialize.relsync = { every_s = 1, batch = "x" }
setm(A, Bf, 15); dirty(A, Bf); w()
check(logtxt():find("relsync disabled until restart", 1, true) ~= nil, "relsync error logged and disabled")
check(FAC(A).rel[Bf] == 15 and FAC(Bf).rel[A] == 15, "writer still works (absolute) after relsync off")
FAC(A).rel[Bf] = 5; setm(A, Bf, 20); dirty(A, Bf); w()
check(FAC(A).rel[Bf] == 20 and S.rel[A][Bf] == 20, "off: model written as is (old path)")
DBGL = logtxt():sub(-600)
RESULT = #FAILS == 0 and ("OK " .. N) or ("FAIL: " .. table.concat(FAILS, "; "))
'''
run(TEST.replace("TMPDIR", TMP), "test")
L.lua_getfield(st, -10002, b"RESULT")
r = L.lua_tolstring(st, -1, None).decode()
print(r)
if not r.startswith("OK"):
    L.lua_getfield(st, -10002, b"DBGL"); print(L.lua_tolstring(st, -1, None).decode())
sys.exit(0 if r.startswith("OK") else 1)
