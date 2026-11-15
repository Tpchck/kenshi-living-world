"""Offline test S2: сила, богатство и владение городами сверяются с ядром (getFactionSize, getProsperityMultiplier,
FactionWarMgr.myTowns, колбэк Faction::destroyPlatoon). Первое чтение - семя, дальше дельта вливается в модель с потолком,
скачок не вливается, офлайн без методов модель живёт сама, ошибка выключает только сверку.
python -I -X utf8 build/KMM_Conductor/_dev/test_s2_coresync.py -> OK."""
import ctypes, re, sys, tempfile

DLL = r"C:\Program Files (x86)\Steam\steamapps\workshop\content\233860\3817000612\lua51.dll"
B = r"C:\KenshiModMap\build\KMM_Conductor\scripts\init"
TMP = tempfile.mkdtemp(prefix="kmm_s2_").replace("\\", "/")
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
local function near(a, b) return type(a) == "number" and math.abs(a - b) < 1e-6 end
local C = KMM_Conductor
C.reset()
local S = C.state()
local CF = C.cfg()
local P = CF.params
P.guard = P.guard or {}; P.guard.debug_log = "TMPDIR/debug.log"
P.chronicle_path = "TMPDIR/chronicle.log"
P.materialize.coresync = { every_s = 1, batch = 1000, mark_every = 1 }
local function logtxt() local f = io.open("TMPDIR/debug.log", "r"); if not f then return "" end; local s = f:read("*a"); f:close(); return s end
local function step() CLOCK = CLOCK + 2; C.coresync_test() end
local ids = {}; for fid, f in pairs(S.F) do if f.alive and not f.player then ids[#ids + 1] = fid end end; table.sort(ids)
local A, Bf, Cf = ids[1], ids[2], ids[3]
-- 1. офлайн: методов ядра нет - модель не трогается, маркер есть, read=0
local s0, w0 = S.F[A].strength, S.F[A].wealth
step()
check(S.F[A].strength == s0 and S.F[A].wealth == w0, "offline: model untouched")
check(logtxt():find("CORESYNC steps=1 str read=0", 1, true) ~= nil, "offline marker read=0")
check(not C.coresync().off, "offline is not an error")
-- 2. первое чтение - семя
local fa = FAC(A); fa.size = 100; fa.getFactionSize = function(self) return self.size end
step()
check(S.F[A].strength == s0, "first read seeds only: " .. tostring(S.F[A].strength))
local function kill(fo) FIRE("Faction::destroyPlatoon", fo, {}) end
-- 3. падение без destroyPlatoon (выгрузка зоны/уход) не вливается; с подсказкой - вливается (вес 0.5)
fa.size = 90; step()
check(S.F[A].strength == s0, "drop without hint not merged: " .. tostring(S.F[A].strength))
check(logtxt():find("guard credit=0 nohint=1", 1, true) ~= nil, "nohint counted in marker")
fa.size = 80; kill(fa); step()
check(near(S.F[A].strength, s0 * (1 - 0.5 * 10 / 90)), "hinted loss merged: " .. tostring(S.F[A].strength))
check(logtxt():find("CORESYNC first strength merge", 1, true) ~= nil, "first strength merge marker")
-- 4. стабильная численность - без изменений
local s4 = S.F[A].strength; step(); step()
check(S.F[A].strength == s4, "no change without delta")
-- 5. скачок 80 -> 20 (загрузка/выгрузка): не вливается, новое семя
fa.size = 20; kill(fa); step()
check(S.F[A].strength == s4, "jump not merged")
check(logtxt():find("CORESYNC strength jump reseed", 1, true) ~= nil, "jump marker")
-- 6. рост (респаун или наш спавн) не вливается, а копится кредитом; падение сначала гасит кредит
fa.size = 28; step()
check(S.F[A].strength == s4, "growth not merged (w_up=0): " .. tostring(S.F[A].strength))
fa.size = 22; kill(fa); step()
check(S.F[A].strength == s4, "drop absorbed by growth credit")
fa.size = 18; kill(fa); step()
check(near(S.F[A].strength, s4 * (1 - 0.5 * 2 / 22)), "drop beyond credit merged: " .. tostring(S.F[A].strength))
-- 6b. наши спавны: 20 циклов «пришёл +5 / ушёл -5 с destroyPlatoon» - сила не дрейфует ни вверх, ни вниз
local s6 = S.F[A].strength
for _ = 1, 20 do fa.size = 23; step(); fa.size = 18; kill(fa); step() end
check(S.F[A].strength == s6, "own spawn cycles: no drift: " .. tostring(S.F[A].strength) .. " vs " .. tostring(s6))
-- 7. окно событий: модель уже уронила силу на 10% (засада/KMM_Self) - падение ядра в пределах этого не вливается повторно
S.F[A].strength = S.F[A].strength * 0.9
local s7 = S.F[A].strength
fa.size = 17; kill(fa); step()
check(S.F[A].strength == s7, "loss explained by model events not double-counted: " .. tostring(S.F[A].strength))
check(logtxt():find("explained=1", 1, true) ~= nil, "explained counted")
-- 7b. сверх объяснённого вливается только остаток
S.F[A].strength = S.F[A].strength * 0.95
local s7b = S.F[A].strength
local ex7 = C.coresync().ex[A] * 0.5 + 0.05
fa.size = 14; kill(fa); step()
check(near(S.F[A].strength, s7b * (1 - 0.5 * (3 / 17 - ex7))), "only unexplained remainder merged: " .. tostring(S.F[A].strength))
-- 8. destroyPlatoon: подсказка читает фракцию даже без обхода по кругу
check(Events.h["Faction::destroyPlatoon"] ~= nil, "destroyPlatoon hook registered")
P.materialize.coresync.batch = 0
local s8 = S.F[A].strength
fa.size = 13; step()
check(S.F[A].strength == s8, "batch=0: no round read")
fa.size = 12; kill(fa)
check(C.coresync().hot[A] == true, "hint queued")
step()
check(near(S.F[A].strength, s8 * (1 - 0.5 * 2 / 14)), "hinted faction read and merged: " .. tostring(S.F[A].strength))
check(C.coresync().hot[A] == nil, "hint consumed")
P.materialize.coresync.batch = 1000
-- 8b. запасной счёт отрядами (src=platoons), lektor через ENGINE_LIST
local fb = FAC(Bf)
fb.act, fb.unl = { 1, 2 }, { 3, 4, 5, 6, 7, 8, 9, 10 }
fb.getActivePlatoons = function(self) return ENGINE_LIST(self.act) end
fb.getUnloadedPlatoons = function(self) return ENGINE_LIST(self.unl) end
local sb = S.F[Bf].strength
step()
fb.unl[#fb.unl] = nil; kill(fb); step()
check(near(S.F[Bf].strength, sb * (1 - 0.5 * 1 / 10)), "platoon count fallback: " .. tostring(S.F[Bf].strength))
-- 9. процветание: 1.0 -> 0.8 (r=-0.2, x0.5=-0.1) срезается до -8% богатства
fb.pm = 1.0; fb.getProsperityMultiplier = function(self) return self.pm end
local wb = S.F[Bf].wealth
step()
check(S.F[Bf].wealth == wb, "prosperity seed only")
fb.pm = 0.8; step()
check(near(S.F[Bf].wealth, wb * 0.92), "prosperity merged with cap: " .. tostring(S.F[Bf].wealth))
check(logtxt():find("CORESYNC first prosperity merge", 1, true) ~= nil, "first prosperity marker")
local wb2 = S.F[Bf].wealth; fb.pm = 0.802; step()
check(S.F[Bf].wealth == wb2, "tiny prosperity change ignored")
-- 10. города: ядро числит город A за Cf - расхождение в лог; свой город A - согласие
local tA, OW; for _, fid in ipairs(ids) do for t in pairs(S.F[fid].towns) do if CF.town_info and CF.town_info[t] then tA, OW = t, fid; break end end; if tA then break end end
check(tA ~= nil, "model town found")
if tA then
  local OT = OW == Cf and A or Cf
  local town = { data = { stringID = tA } }
  local fc = FAC(OT); fc.warMgr.myTowns = ENGINE_LIST({ town })
  fc.countPopulation = function(self, t) return 12 end
  FAC(OW).warMgr.myTowns = ENGINE_LIST({ town })
  P.materialize.coresync.tbatch = 1000
  step()
  P.materialize.coresync.tbatch = nil
  check(logtxt():find("CORESYNC town owner differs: " .. tA .. " core=" .. OT .. " model=" .. OW, 1, true) ~= nil, "town owner divergence logged")
  check((S.stats.town_owner_div or 0) == 1, "divergence counted once: " .. tostring(S.stats.town_owner_div))
  check(logtxt():find("agree=%d+ diverged=%d+ pop=12") ~= nil, "towns mark with pop")
  check(logtxt():find("agree=1 diverged=") ~= nil, "own town agrees")
  check(not S.F[OT].towns[tA] and S.F[OW].towns[tA], "model not rewritten by town check")
end
-- 11. игрок не сверяется
local pf = CF.player_faction
if pf and S.F[pf] then
  local fp = FAC(pf); fp.size = 10; fp.getFactionSize = function(self) return self.size end
  local sp = S.F[pf].strength; step(); fp.size = 5; step()
  check(S.F[pf].strength == sp, "player faction skipped")
end
-- 12. новый мир (reset): старые числа ядра не сравниваются
C.reset(); S = C.state()
local s12 = S.F[A].strength
fa.size = 60; step()
check(S.F[A].strength == s12, "new world: seed, no spurious merge: " .. tostring(S.F[A].strength))
-- 13. ошибка в логике выключает только сверку
P.materialize.coresync = { every_s = 1, batch = "x" }
step()
check(C.coresync().off == true, "error disables coresync")
check(logtxt():find("CORESYNC disabled until restart", 1, true) ~= nil, "disable logged")
P.materialize.coresync = { every_s = 1, batch = 1000 }
local s13 = S.F[A].strength; fa.size = 50; step()
check(S.F[A].strength == s13, "off: no more merges")
DBGL = logtxt():sub(-900)
RESULT = #FAILS == 0 and ("OK " .. N) or ("FAIL: " .. table.concat(FAILS, "; "))
'''
run(TEST.replace("TMPDIR", TMP), "test")
L.lua_getfield(st, -10002, b"RESULT")
r = L.lua_tolstring(st, -1, None).decode()
print(r)
if not r.startswith("OK"):
    L.lua_getfield(st, -10002, b"DBGL"); print(L.lua_tolstring(st, -1, None).decode())
sys.exit(0 if r.startswith("OK") else 1)
