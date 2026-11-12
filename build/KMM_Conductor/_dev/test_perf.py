"""Офлайн-бенчмарк PERF фаза 1: общий снимок загруженных NPC (KMM_Gov.snapshot) против прежних обходов в Traces/Self.
N=200 загруженных NPC в заглушке, счёт вызовов API персонажа и время Lua на окно (10 с игрового времени).
Варианты: BEFORE (резервные копии *_pre_perf.lua.txt, без Gov), AFTER_GOV (новый код + Gov), AFTER_FALLBACK (новый код без Gov),
AFTER_BROKEN_GOV (Gov.snapshot бросает исключение -> модули идут своим обходом).
Проверяет и поведение: runAway, caravan_lost, события self_* на шине, отсутствие отключённых функций.
python -I -X utf8 build/KMM_Conductor/_dev/test_perf.py -> OK / FAIL, код 1 при провале."""
import ctypes
import re
import sys
import tempfile

DLL = r"C:\Program Files (x86)\Steam\steamapps\workshop\content\233860\3817000612\lua51.dll"
B = r"C:\KenshiModMap\build\KMM_Conductor"
INIT = B + r"\scripts\init"
DEV = B + r"\_dev"
rt = open(r"C:\KenshiModMap\tools\test\test_runtime.py", encoding="utf-8").read()
STUBS_SRC = re.search(r"STUBS = r'''(.*?)'''", rt, re.S).group(1)
N_NPC = 200
FAILS = []


def make_state():
    L = ctypes.CDLL(DLL)
    L.luaL_newstate.restype = ctypes.c_void_p
    for fn, at in [("luaL_openlibs", [ctypes.c_void_p]), ("luaL_loadstring", [ctypes.c_void_p, ctypes.c_char_p]),
                   ("lua_pcall", [ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int]),
                   ("lua_settop", [ctypes.c_void_p, ctypes.c_int]),
                   ("lua_getfield", [ctypes.c_void_p, ctypes.c_int, ctypes.c_char_p])]:
        getattr(L, fn).argtypes = at
    L.lua_tolstring.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p]
    L.lua_tolstring.restype = ctypes.c_char_p
    st = L.luaL_newstate()
    L.luaL_openlibs(st)

    def run(code, name="chunk"):
        if L.luaL_loadstring(st, code.encode("utf-8")) or L.lua_pcall(st, 0, 0, 0):
            msg = L.lua_tolstring(st, -1, None)
            raise RuntimeError(f"{name}: {msg.decode('utf-8', 'replace') if msg else '?'}")

    def get(var):
        run("__V = tostring(%s)" % var, "get")
        L.lua_getfield(st, -10002, b"__V")
        v = L.lua_tolstring(st, -1, None)
        L.lua_settop(st, -2)
        return v.decode("utf-8", "replace") if v else None
    return run, get


WORLD = r'''
API = 0; WALKS = 0
local function cnt(f) return function(...) API = API + 1; return f(...) end end
function MK(nm, fid, x, z, opt)
  opt = opt or {}
  local c = { dead = false, x = x, z = z }
  local pl = PLATOON(opt.platoon, opt.tsid)
  c.medical = { knockoutTimer = 0, unconcious = false }
  c.getName = cnt(function() return nm end)
  c.getFaction = cnt(function() return FAC(fid) end)
  c.getPosition = cnt(function() return { x = c.x, y = 0, z = c.z } end)
  c.isPlayerCharacter = cnt(function() return false end)
  c.isUnique = cnt(function() return opt.unique or false end)
  c.isDead = cnt(function() return c.dead end)
  c.isDown = cnt(function() return opt.down or false end)
  c.isUnconcious = cnt(function() return false end)
  c.isInCombatMode = cnt(function() return opt.combat or false end)
  c.getHandle = cnt(function() return "h_" .. nm end)
  c.declareDead = function() c.dead = true end
  c.getPlatoon = cnt(function() return { me = pl, getIsTrader = function() API = API + 1; return opt.trader or false end } end)
  c.getInventory = cnt(function() return { getAllItems = function() return {} end } end)
  c.getCurrentTownLocation = cnt(function() return nil end)
  c.is_trader = opt.trader
  if opt.leader then pl.leader = c end
  return c
end
'''

SETUP = r'''
local C = KMM_Conductor
local P = C.cfg().params
C._set("tick_days", 1e9); C._set("first_event_after_days", 1e9)
P.traces.first_hour_traces = 0
C.reset()
local S = C.state()
local fids = {}
for fid, f in pairs(S.F) do if f.alive and not f.player then fids[#fids + 1] = fid end end
table.sort(fids)
PF = C.cfg().player_faction or "player"
PCS = { MKCH("Nameless", PF, 0, 0, { player = true, platoon = "player_squad" }) }
CHARS = { PCS[1] }
NPC = {}
-- 200 NPC: 40 отрядов по 5; каждый 4-й отряд торговцы; отряды 1 и 2 в бою, в отряде 1 четверо лежат (с вожаком)
for i = 1, %(N)d do
  local sq = math.floor((i - 1) / 5) + 1
  local fid = fids[(sq %% #fids) + 1]
  local opt = { platoon = "sq" .. sq, trader = (sq %% 4 == 0), combat = (sq <= 2), leader = ((i - 1) %% 5 == 0) }
  if sq == 1 then opt.down = ((i - 1) %% 5) < 4 end
  local c = MK("n" .. i, fid, 400 + (i * 37) %% 3000, (i * 91) %% 3000 - 1500, opt)
  NPC[i] = c; CHARS[#CHARS + 1] = c
end
local AMB = KMM_Traces.ambush()   -- видимая засада: amb_scan не пустует
AMB.perf = { a = fids[1], b = fids[2], x = 1000, z = 0, t0 = 0, mode = "wait" }
EVS = {}
C.subscribe("self_*", function(ev) EVS[#EVS + 1] = ev end)
C.subscribe("caravan_lost", function(ev) EVS[#EVS + 1] = ev end)
'''

LOOP = r'''
function WINDOW(secs)
  local cpu = 0
  for i = 1, secs do
    CLOCK = CLOCK + 1; DAYV = DAYV + 0.0005
    local t = REAL_CLOCK()
    KMM_Traces._tick()
    KMM_Self._tick()
    cpu = cpu + (REAL_CLOCK() - t)
  end
  return cpu
end
'''


def legacy_api(src):
    """Копии *_pre_perf писались до сверки с живым API (лог игры 2026-11-12): у Faction нет getGameData,
    createRandomSquad требует hand и число squadType. Приводим базовую линию к тем же правилам, иначе BEFORE ломается
    на заглушке, а не меряет обходы. На новый код не влияет (там этих мест уже нет)."""
    import re as _re
    src = _re.sub(r"(\w+) and \1:getGameData\(\)", r"\1 and (\1:getData() or \1.data)", src)
    src = src.replace("target_handle, target_town, 1.0, nil, false)", "target_handle or {}, target_town, 1.0, 2, false)")
    return src


def variant(name, traces, selff, gov, break_gov=False):
    tmp = tempfile.mkdtemp(prefix="kmm_perf_").replace("\\", "/")
    run, get = make_state()
    run("REAL_CLOCK = os.clock", "realclock")
    run(STUBS_SRC.replace("TMPDIR", tmp), "stubs")
    run(WORLD, "world")
    if gov:
        run(open(INIT + r"\KMM_Gov.lua", encoding="utf-8").read().replace("C:/KenshiModMap/logs/", tmp + "/"), "Gov")
    for _f in sorted(__import__("glob").glob(INIT + r"\KMM_Conductor*.lua")): run(open(_f, encoding="utf-8").read(), _f.split("\\")[-1])
    run(legacy_api(open(traces, encoding="utf-8").read()), "Traces")
    run(legacy_api(open(selff, encoding="utf-8").read()), "Self")
    run(r'''
local gw0 = getGameWorld
function getGameWorld() local g = gw0(); local f = g.getCharacterUpdateList; g.getCharacterUpdateList = function(...) WALKS = WALKS + 1; return f(...) end; return g end
''', "walkcount")
    run(SETUP % {"N": N_NPC}, "setup")
    run(LOOP, "loop")
    if break_gov:
        run("KMM_Gov.snapshot = function() error('snapshot broken') end", "break")
    run("WINDOW(30)", "warm")
    run("API = 0; WALKS = 0", "reset")
    run("WCPU = 0; for w = 1, 20 do WCPU = WCPU + WINDOW(10) end; CPUMS = WCPU / 20 * 1000; API20 = API / 20; WALK20 = WALKS / 20", "measure")
    run(r'''
for i = 1, %(N)d do local c = NPC[i]; if c.is_trader then c.dead = true end end
WINDOW(12)
LOST = 0; for _, e in ipairs(EVS) do if e.type == "caravan_lost" then LOST = LOST + 1 end end
SELFEV = 0; for _, e in ipairs(EVS) do if e.type:sub(1, 5) == "self_" then SELFEV = SELFEV + 1 end end
DIS = {}; for k in pairs(KMM_Traces.disabled()) do DIS[#DIS+1] = "T:" .. k end; for k in pairs(KMM_Self.disabled()) do DIS[#DIS+1] = "S:" .. k end
DISS = table.concat(DIS, ",")
local e1; for _, e in ipairs(EVS) do if e.type:sub(1, 5) == "self_" then e1 = e; break end end
EVD = e1 and (e1.type .. "/" .. tostring(e1.why or e1.mode) .. " a=" .. tostring(e1.a) .. " squad=" .. tostring(e1.squad) .. " n=" .. tostring(e1.n) .. " down=" .. tostring(e1.down)) or "-"
''' % {"N": N_NPC}, "kill")
    r = dict(name=name, api=float(get("API20")), walks=float(get("WALK20")), cpu_ms=float(get("CPUMS")),
             runaway=get("RUNAWAY"), selfev=float(get("SELFEV")), lost=float(get("LOST")), disabled=get("DISS") or "", ev=get("EVD"))
    if gov:
        run("local s = KMM_Gov.snapshot_stats(); GS = string.format('builds=%d hits=%d fails=%d', s.builds, s.hits, s.fails)", "gs")
        r["gov"] = get("GS")
    return r


def check(c, m):
    print(("OK   " if c else "FAIL ") + m)
    if not c:
        FAILS.append(m)


b = variant("BEFORE", DEV + r"\KMM_Traces_pre_perf.lua.txt", DEV + r"\KMM_Self_pre_perf.lua.txt", False)
a = variant("AFTER_GOV", INIT + r"\KMM_Traces.lua", INIT + r"\KMM_Self.lua", True)
f = variant("AFTER_FALLBACK", INIT + r"\KMM_Traces.lua", INIT + r"\KMM_Self.lua", False)
x = variant("AFTER_BROKEN_GOV", INIT + r"\KMM_Traces.lua", INIT + r"\KMM_Self.lua", True, break_gov=True)

print(f"\nN={N_NPC} NPC, окно = 10 с игрового времени (Traces + Self, прямой вызов _tick, Gov.run-тротлинг не включён)")
print(f"{'вариант':<18}{'вызовов API/окно':>18}{'обходов списка/окно':>21}{'Lua мс/окно':>14}  gov")
for r in (b, a, f, x):
    print(f"{r['name']:<18}{r['api']:>18.0f}{r['walks']:>21.1f}{r['cpu_ms']:>14.2f}  {r.get('gov', '')}")
if b["api"]:
    print(f"API после/до: {a['api'] / b['api']:.2f} (Gov), {f['api'] / b['api']:.2f} (без Gov); время после/до: {a['cpu_ms'] / max(b['cpu_ms'], 1e-9):.2f} (Gov)")
print("первое событие Self:", a["ev"])

check(a["api"] < b["api"] * 0.5, f"Gov: вызовов API минимум вдвое меньше ({a['api']:.0f} против {b['api']:.0f})")
check(a["walks"] < b["walks"], f"Gov: обходов списка меньше ({a['walks']:.1f} против {b['walks']:.1f})")
check(f["api"] < b["api"], f"фолбэк без Gov тоже дешевле прежнего ({f['api']:.0f} против {b['api']:.0f})")
check(a["cpu_ms"] <= b["cpu_ms"] * 1.10, f"Gov: время Lua на окно не больше эталона +10% — шум таймера ({a['cpu_ms']:.2f} против {b['cpu_ms']:.2f} мс)")
for r in (b, a, f, x):
    check(r["disabled"] == "", f"{r['name']}: ни одна функция не отключилась ({r['disabled']})")
    check(r["lost"] == b["lost"] and r["lost"] >= 1, f"{r['name']}: caravan_lost сработал, как до ({r['lost']:.0f} против {b['lost']:.0f})")
    check(r["runaway"] == b["runaway"], f"{r['name']}: runAway тот же ({r['runaway']} против {b['runaway']})")
check(a["selfev"] >= 1 and a["ev"].startswith("self_"), "Self эмитит события шины: " + a["ev"])
check(b["selfev"] == 0, "до PERF Self не эмитил")
check(x["selfev"] >= 1 and x["lost"] == b["lost"], "сломанный Gov.snapshot: свой обход, поведение и события сохранены")
print("test_perf:", "OK" if not FAILS else "FAIL " + "; ".join(FAILS))
sys.exit(0 if not FAILS else 1)
