"""Offline test Y2: подтверждённый разгром отряда (подсказка destroyPlatoon + падение численности в CORESYNC) зовёт
diplomatMgr.prosperityMgr:notifySquadDefeated(squadTemplate); уход/выгрузка/свой спавн не зовут; лимиты за чтение/фракцию/день;
ваниль уже уронила процветание - пропуск; богатство модели меняется один раз (через чтение процветания CORESYNC);
нет эффекта - вызовы прекращаются; ошибка - проба FAIL, Y2 выкл., сверка живёт.
H2: в очередь только Platoon.isDead (выгрузка временных отрядов при падении численности не зовёт ядро).
H3: вызов под крэш-сторожем probe_call("prosperity"): lock на первом вызове, lock при старте -> .off, Y2 выключен навсегда.
python -I -X utf8 build/KMM_Conductor/_dev/test_y2_prosperity.py -> OK."""
import ctypes, re, sys, tempfile

DLL = r"C:\Program Files (x86)\Steam\steamapps\workshop\content\233860\3817000612\lua51.dll"
B = r"C:\KenshiModMap\build\KMM_Conductor\scripts\init"
TMP = tempfile.mkdtemp(prefix="kmm_y2_").replace("\\", "/")
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
P.materialize.prosperity = {}
P.campaign = P.campaign or {}; P.campaign.sdir = "TMPDIR/"
local function logtxt() local f = io.open("TMPDIR/debug.log", "r"); if not f then return "" end; local s = f:read("*a"); f:close(); return s end
local function count(pat) local n = 0; for _ in logtxt():gmatch(pat) do n = n + 1 end; return n end
local function step() CLOCK = CLOCK + 2; C.coresync_test() end
local DAY = 1000
S.last_day = DAY
local ids = {}; for fid, f in pairs(S.F) do if f.alive and not f.player then ids[#ids + 1] = fid end end; table.sort(ids)
local A, Bf, Cf, Df = ids[1], ids[2], ids[3], ids[4]
local function kill(fo, key, tsid) local p = PLATOON(key, tsid); p.isDead = true; FIRE("Faction::destroyPlatoon", fo, p) end
local function unload(fo, key, tsid) local p = PLATOON(key, tsid); p.isDead = false; FIRE("Faction::destroyPlatoon", fo, p) end
local function exists(path) local f = io.open(path, "r"); if f then f:close(); return true end; return false end
local function mgr(fo, d)
  fo.diplomatMgr = { prosperityMgr = { actualProsperity = 100, maxProsperity = 100, n = 0, sids = {},
    notifySquadDefeated = function(self, t) self.n = self.n + 1; self.sids[#self.sids + 1] = t.stringID; self.actualProsperity = self.actualProsperity - d end } }
  fo.getProsperityMultiplier = function(self) return self.diplomatMgr.prosperityMgr.actualProsperity / 100 end
  fo.size = 100; fo.getFactionSize = function(self) return self.size end
  return fo.diplomatMgr.prosperityMgr
end
-- 1. офлайн (нет численности ядра): destroyPlatoon с шаблоном - вызова нет, маркер сверки с хвостом defeat
local f0 = FAC(Df)
kill(f0, "d1", "bandits_d"); step()
check(logtxt():find("PROSPERITY", 1, true) == nil, "offline: no prosperity call/log")
check(logtxt():find("| defeat calls=0", 1, true) ~= nil, "mark carries defeat tail")
-- 2. подтверждённая потеря: шаблон уходит в ядро, проба ok, богатство -1.5% один раз (через CORESYNC), сила - по S2
local fa = FAC(A); local pa = mgr(fa, 3)
step()   -- семя численности и процветания
local s0, w0 = S.F[A].strength, S.F[A].wealth
fa.size = 96; kill(fa, "a1", "dust_bandits"); step()
check(pa.n == 1 and pa.sids[1] == "dust_bandits", "confirmed loss -> notifySquadDefeated(template): " .. tostring(pa.n))
check(logtxt():find("PROSPERITY probe ok: " .. A .. " tpl=dust_bandits", 1, true) ~= nil, "probe ok marker")
check(not exists("TMPDIR/probe_prosperity.lock") and not exists("TMPDIR/probe_prosperity.off"), "probe lock removed after ok call")
check(logtxt():find("PROSPERITY defeated: " .. A .. " tpl=dust_bandits loaded=false pm 1.0000->0.9700 act 100.0000->97.0000 fac 1/3 day 1/12", 1, true) ~= nil, "defeated marker")
check(near(S.F[A].wealth, w0 * (1 - 0.5 * 0.03)), "wealth merged once via coresync: " .. tostring(S.F[A].wealth))
check(near(S.F[A].strength, s0 * (1 - 0.5 * 4 / 100)), "strength only via S2 merge: " .. tostring(S.F[A].strength))
local w2 = S.F[A].wealth; step(); step()
check(S.F[A].wealth == w2, "no second wealth drop on later reads")
check(C.coresync().ys.eff == 1, "effect counted")
-- 3. destroyPlatoon без падения численности (уход/выгрузка) - вызова нет, очередь сброшена
kill(fa, "a2", "dust_bandits"); step()
check(pa.n == 1, "no drop -> no call")
check(C.coresync().y.q[A] == nil, "queue cleared")
-- 4. падение, погашенное кредитом своего спавна, - вызова нет
fa.size = 100; step(); fa.size = 96; kill(fa, "a3", "own_spawn"); step()
check(pa.n == 1, "credit-absorbed drop -> no call")
-- 5. лимит за чтение (2) и на фракцию в день (3)
fa.size = 92; kill(fa, "a4", "t4"); kill(fa, "a5", "t5"); kill(fa, "a6", "t6"); step()
check(pa.n == 3, "per_read cap 2: " .. tostring(pa.n))
fa.size = 90; kill(fa, "a7", "t7"); step()
check(pa.n == 3, "per_fac_day cap 3: " .. tostring(pa.n))
S.last_day = DAY + 1
fa.size = 88; kill(fa, "a8", "t8"); step()
check(pa.n == 4, "new day resets cap: " .. tostring(pa.n))
check(logtxt():find("tpl=t8 loaded=false pm [%d%.]+%->[%d%.]+ act [%d%.]+%->[%d%.]+ fac 1/3 day 1/12") ~= nil, "day counter restarted")
-- 6. ваниль уже уронила процветание с прошлого чтения - не дублируем
pa.actualProsperity = pa.actualProsperity - 5
fa.size = 86; kill(fa, "a9", "t9"); step()
check(pa.n == 4, "vanilla drop -> skip")
check(logtxt():find("PROSPERITY vanilla already dropped: " .. A, 1, true) ~= nil, "vanilla skip logged")
-- 7. нет шаблона / нет менеджера - без вызова
local fb = FAC(Bf); mgr(fb, 2); step()
local pl = PLATOON("b0"); pl.squadTemplate = nil; pl.isDead = true
fb.size = 96; FIRE("Faction::destroyPlatoon", fb, pl); step()
check(fb.diplomatMgr.prosperityMgr.n == 0, "no template -> no call")
local mb = fb.diplomatMgr; fb.diplomatMgr = nil
fb.size = 92; kill(fb, "b1", "tb"); step()
check(mb.prosperityMgr.n == 0, "no manager -> no call")
check(logtxt():find("notpl=1", 1, true) ~= nil and logtxt():find("nomgr=1", 1, true) ~= nil, "skips counted in mark")
fb.diplomatMgr = mb
-- 8. смена мира: очередь прошлого мира не доходит до ядра
local fc = FAC(Cf); local pc = mgr(fc, 1)
step(); fc.size = 96; kill(fc, "c1", "tc")
C.reset(); S = C.state(); S.last_day = DAY + 2
step()
check(pc.n == 0, "world change drops queue")
-- 9. ошибка вызова после пройденной пробы: Y2 выключается, сверка работает дальше
pc.notifySquadDefeated = function() error("boom") end
step(); fc.size = 92; kill(fc, "c2", "tc"); step()
check(C.coresync().ys.off == true, "error disables Y2")
check(logtxt():find("PROSPERITY disabled until restart", 1, true) ~= nil, "disable logged (probe already passed)")
check(not C.coresync().off, "coresync keeps running")
local G = KMM_C_INT.GL
-- 10. проба FAIL на первом вызове (чистое состояние Y2)
G.cs.ys = { calls = 0, mcalls = 0, eff = 0 }; G.y2_st0()
fc.size = 88; kill(fc, "c3", "tc"); step()
check(logtxt():find("PROSPERITY probe FAIL", 1, true) ~= nil, "probe FAIL logged")
-- 11. вызов без эффекта: после noeff_n измеренных вызовов вызовы прекращаются
G.cs.ys = { calls = 0, mcalls = 0, eff = 0 }; G.y2_st0()
P.materialize.prosperity = { noeff_n = 2, per_fac_day = 10 }
pc.notifySquadDefeated = function(self) self.n = self.n + 1 end
for i = 1, 4 do fc.size = fc.size - 2; kill(fc, "n" .. i, "tn"); step() end
check(pc.n == 2, "calls stop after no effect: " .. tostring(pc.n))
check(G.cs.ys.off == true and logtxt():find("PROSPERITY no effect after 2 measured calls", 1, true) ~= nil, "no-effect logged and off")
-- 12. выключено конфигом - ничего
G.cs.ys = { calls = 0, mcalls = 0, eff = 0 }; G.y2_st0()
P.materialize.prosperity = { enabled = false }
local fd = FAC(Df); local pd = mgr(fd, 2); step()
fd.size = 96; kill(fd, "d2", "td"); step()
check(pd.n == 0, "disabled by config")
check(count("PROSPERITY probe ok") == 2, "one probe ok per fresh Y2 state (scenarios 2 and 11)")
-- 13. H3: lock прошлой сессии (крэш в нативном вызове) -> .off, вызова нет, Y2 выключен
G.cs.ys = { calls = 0, mcalls = 0, eff = 0 }; G.y2_st0()
P.materialize.prosperity = {}
local lf = io.open("TMPDIR/probe_prosperity.lock", "w"); lf:write("1"); lf:close()
KMM_C_INT.L2.camp.PROBE = {}
local fe = FAC(Df); local pe = mgr(fe, 2); pe.n = 0; step(); step()
fe.size = fe.size - 6; kill(fe, "e1", "te"); step()
check(pe.n == 0, "crash lock -> no native call")
check(exists("TMPDIR/probe_prosperity.off") and not exists("TMPDIR/probe_prosperity.lock"), "lock turned into .off")
check(G.cs.ys.off == true and logtxt():find("PROSPERITY disabled forever", 1, true) ~= nil, "Y2 off forever logged")
G.cs.ys = { calls = 0, mcalls = 0, eff = 0 }; G.y2_st0(); KMM_C_INT.L2.camp.PROBE = {}
step(); fe.size = fe.size - 6; kill(fe, "e2", "te"); step()
check(pe.n == 0, ".off persists to next session")
-- 14. H2: падение численности + destroyPlatoon при выгрузке зоны (isDead=false) - вызова нет; в ядро только погибшие
os.remove("TMPDIR/probe_prosperity.off"); KMM_C_INT.L2.camp.PROBE = {}
G.cs.ys = { calls = 0, mcalls = 0, eff = 0 }; G.y2_st0(); S.last_day = DAY + 5
local fh = FAC(Bf); local ph = mgr(fh, 1); ph.n = 0; step(); step()
fh.size = fh.size - 8; unload(fh, "u1", "tu1"); unload(fh, "u2", "tu2"); step()
check(ph.n == 0, "unloaded platoons -> no call: " .. tostring(ph.n))
check(logtxt():find("unload=2", 1, true) ~= nil, "unload counted in mark")
fh.size = fh.size - 8; unload(fh, "u3", "tu3"); kill(fh, "u4", "tu4"); unload(fh, "u5", "tu5"); step()
check(ph.n == 1 and ph.sids[1] == "tu4", "only the dead platoon goes to core: " .. tostring(ph.n))
DBGL = logtxt():sub(-1500)
RESULT = #FAILS == 0 and ("OK " .. N) or ("FAIL: " .. table.concat(FAILS, "; "))
'''
run(TEST.replace("TMPDIR", TMP), "test")
L.lua_getfield(st, -10002, b"RESULT")
r = L.lua_tolstring(st, -1, None).decode()
print(r)
if not r.startswith("OK"):
    L.lua_getfield(st, -10002, b"DBGL"); print(L.lua_tolstring(st, -1, None).decode())
sys.exit(0 if r.startswith("OK") else 1)
