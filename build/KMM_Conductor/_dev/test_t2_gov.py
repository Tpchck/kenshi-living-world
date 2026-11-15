r"""T2 (2026-11-15): KMM_Gov — снимок NPC с TTL по реальному времени + проверка has() в новом кадре, стоимость снимка отдельно от модулей,
сводка нагрузки в debug.log. Две части:
  1) бенч: мир test_s5_perf (200 NPC, 10 кадров/с, метка кадра, set:has), Traces+Self (текущие) + «прочий» потребитель снимка
     (как скан дирижёра/Town/Tempo: свой кадр, раз в 0.7 с) под Gov ДО (_dev/KMM_Gov_pre_t2.lua.txt) и ПОСЛЕ (scripts/init/KMM_Gov.lua).
     Время Gov моделируется счётом API: os.clock = CLOCK + (вызовов API с начала кадра) * US.
       US = 1 мкс — троттлинга нет ни у кого: честное сравнение работы (пик кадра, вызовов на окно, сборок, поведение);
       US = 4 мкс — ДО воспроизводит игровой троттлинг из logs\debug.log («avg > 0.60 ms» у первого модуля кадра): сравнение учёта Gov.
  2) юнит-проверки снимка на мини-заглушках: удалённый персонаж не отдаётся и не трогается, ap/pl/town в позднем кадре заново, без has —
     правило одного кадра, без метки — правило ttl, кэши потребителя на снимке живут кадр, учёт gov:snapshot, маркеры сводки.
python -I -X utf8 build/KMM_Conductor/_dev/test_t2_gov.py -> OK / FAIL, код 1 при провале."""
import importlib.util
import os
import sys
import tempfile

DEV = r"C:\KenshiModMap\build\KMM_Conductor\_dev"
spec = importlib.util.spec_from_file_location("s5bench", DEV + r"\test_s5_perf.py")
B = importlib.util.module_from_spec(spec)
spec.loader.exec_module(B)
GOV_NEW = B.GOV
GOV_OLD = DEV + r"\KMM_Gov_pre_t2.lua.txt"
FAILS = []


def check(c, m):
    print(("OK   " if c else "FAIL ") + m)
    if not c:
        FAILS.append(m)


if not os.path.exists(B.DLL):
    print("SKIP: lua51.dll KenshiLua не найден")
    sys.exit(1)

# ------------------------------------------------------------------------------------------------ 1) бенч
PRE = r'''
US = %(us)s
os.clock = function() return CLOCK + (CAPI - FRAME_C0) * US end   -- модель: время Gov = вызовы API в кадре
'''
# прочий потребитель: свой кадр (раз в 7 кадров), читает x/z/fid у всех, pl у ближних (как скан дирижёра / Town / Tempo)
POST = r'''
local OT = { n = 0, pl = 0 }
OTHER = OT
local function other()
  OT.n = OT.n + 1
  if OT.n % 7 ~= 3 then return end
  local snap = KMM_Gov.snapshot(4)
  if not snap then return end
  for _, r in ipairs(snap.list) do
    if r.fid and not r.dead and (r.x - 1000) ^ 2 + r.z ^ 2 < 1500 ^ 2 and r.pl then OT.pl = OT.pl + 1 end
  end
end
local hs = Events.h['GameWorld::charsUpdate']
hs[#hs + 1] = METER_WRAP("other", function(...) return KMM_Gov.run("other", other, ...) end)
if KMM_Gov.cfg then KMM_Gov.cfg.report_s = 30 end
'''
MODS = ("traces", "self", "other")
EXTRA = ["FPEAK", "CAPI", "OTHER.pl", "M.other.peak"]
for m in MODS:
    for f in ("avg_ms", "peak_ms", "skipped", "runs", "n"):
        EXTRA.append(f'(KMM_Gov.stats()["{m}"] or {{}}).{f}')
for f in ("builds", "vals", "dropped", "hits"):
    EXTRA.append(f"(KMM_Gov.snapshot_stats().{f} or 0)")
GS_AVG = '(KMM_Gov.stats()["gov:snapshot"] or {}).avg_ms'
GS_PK = '(KMM_Gov.stats()["gov:snapshot"] or {}).peak_ms'
EXTRA += [GS_AVG, GS_PK]
BUILDS, VALS = "(KMM_Gov.snapshot_stats().builds or 0)", "(KMM_Gov.snapshot_stats().vals or 0)"


def bench(name, gov, us):
    return B.ts_variant(name, B.INIT + r"\KMM_Traces.lua", B.INIT + r"\KMM_Self.lua", gov=gov, pre=PRE % {"us": us}, extra=EXTRA, post=POST)


def num(v, k, d=0.0):
    x = v["x"].get(k)
    try:
        return float(x)
    except (TypeError, ValueError):
        return d


def mstat(v, m, f):
    return num(v, f'(KMM_Gov.stats()["{m}"] or {{}}).{f}')


PER = B.WIN / 10.0
RES = {}
for us in ("1e-6", "4e-6"):
    Bv, Av = bench("BEFORE", GOV_OLD, us), bench("AFTER", GOV_NEW, us)
    RES[us] = (Bv, Av)
    print(f"\nN={B.N_NPC} NPC, {B.FPS} кадров/с, окно {B.WIN} с, модель времени {float(us) * 1e6:.0f} мкс на вызов API")
    print(f"{'':<8}{'пик кадра API':>14}{'API/10с':>9}{'сборок':>8}{'проверок':>9}{'gov:snapshot avg/пик мс':>25}")
    for nm, v in (("BEFORE", Bv), ("AFTER", Av)):
        print(f"{nm:<8}{num(v, 'FPEAK'):>14.0f}{num(v, 'CAPI') / PER:>9.0f}{num(v, BUILDS):>8.0f}{num(v, VALS):>9.0f}{num(v, GS_AVG):>15.3f}/{num(v, GS_PK):.3f}")
    print(f"{'модуль':<8}{'вариант':<8}{'Gov avg мс':>11}{'Gov пик мс':>11}{'пропуск %':>10}{'1/N':>5}{'пик API(бенч)':>14}")
    for m in MODS:
        for nm, v in (("BEFORE", Bv), ("AFTER", Av)):
            runs, sk = mstat(v, m, "runs"), mstat(v, m, "skipped")
            pk = v[m]["peak"] if m in v else num(v, "M.other.peak")
            print(f"{m:<8}{nm:<8}{mstat(v, m, 'avg_ms'):>11.3f}{mstat(v, m, 'peak_ms'):>11.3f}{(sk * 100 / max(1, runs + sk)):>10.1f}{mstat(v, m, 'n'):>5.0f}{pk:>14.0f}")

# работа (без троттлинга ни у кого)
Bv, Av = RES["1e-6"]
check(sum(mstat(Bv, m, "skipped") for m in MODS) == 0, "1 мкс: ДО без троттлинга — сравнение работы честное")
check(num(Av, "FPEAK") <= num(Bv, "FPEAK") * 1.02, f"пик кадра (вызовов API) не выше, допуск 2% ({num(Av, 'FPEAK'):.0f} против {num(Bv, 'FPEAK'):.0f})")
check(num(Av, "CAPI") < num(Bv, "CAPI"), f"вызовов API на окно меньше ({num(Av, 'CAPI'):.0f} против {num(Bv, 'CAPI'):.0f})")
check(num(Av, BUILDS) < num(Bv, BUILDS), f"сборок снимка меньше ({num(Av, BUILDS):.0f} против {num(Bv, BUILDS):.0f})")
check(num(Av, VALS) > 0, "в новом кадре снимок проверяется has(), а не собирается заново")
for k in ("runaway", "lost", "selfev", "evsig"):
    check(Av["sig"][k] == Bv["sig"][k], f"Traces+Self: {k} как до ({Av['sig'][k]} против {Bv['sig'][k]})")
check(int(Bv["sig"]["selfev"]) >= 1 and int(Bv["sig"]["lost"]) >= 1, f"сценарий порождает события (self={Bv['sig']['selfev']}, lost={Bv['sig']['lost']})")
check(Av["dis"] == "" and Bv["dis"] == "", f"Traces/Self: ничего не отключилось ({Av['dis']}|{Bv['dis']})")
check(num(Av, "OTHER.pl") > 0 and abs(num(Av, "OTHER.pl") - num(Bv, "OTHER.pl")) <= 0.1 * num(Bv, "OTHER.pl") + 5,
      f"прочий потребитель видит платуны как до ({num(Av, 'OTHER.pl'):.0f} против {num(Bv, 'OTHER.pl'):.0f})")
# учёт Gov (ДО троттлит первого модуля кадра)
Bv, Av = RES["4e-6"]
check(sum(mstat(Bv, m, "skipped") for m in MODS) > 0, "4 мкс: ДО воспроизводит троттлинг из-за чужой перестройки")
for m in MODS:
    bp, ap_ = mstat(Bv, m, "peak_ms"), mstat(Av, m, "peak_ms")
    check(ap_ < bp, f"{m}: пик по Gov ниже — стоимость снимка не на модуле ({ap_:.3f} против {bp:.3f} мс)")
    bs, as_ = mstat(Bv, m, "skipped"), mstat(Av, m, "skipped")
    check(as_ <= bs, f"{m}: пропусков троттлинга не больше ({as_:.0f} против {bs:.0f})")
check(sum(mstat(Av, m, "skipped") for m in MODS) == 0, "ПОСЛЕ: ни один модуль не троттлится из-за чужого снимка")
check(num(Av, GS_AVG) > 0 and num(Av, GS_PK) > 0, "стоимость снимка учтена отдельно (stats()['gov:snapshot'])")
for k in ("runaway", "lost", "selfev", "evsig"):
    check(Av["sig"][k] == RES["1e-6"][1]["sig"][k], f"ПОСЛЕ при 4 мкс: {k} как при 1 мкс (поведение не зависит от цены вызова)")
log = ""
try:
    with open(os.path.join(Av["tmp"], "debug.log"), encoding="utf-8", errors="replace") as f:
        log = f.read()
except OSError:
    pass
sl = [ln for ln in log.splitlines() if "[KMM_Gov] summary:" in ln]
ml = [ln for ln in log.splitlines() if "[KMM_Gov] modules:" in ln]
check(len(sl) >= 2 and len(ml) == len(sl), f"маркеры сводки в debug.log (summary {len(sl)}, modules {len(ml)})")
if sl:
    print("  " + sl[-1].split("] ", 1)[-1])
    print("  " + ml[-1].split("] ", 1)[-1][:260])
check(bool(sl) and "snap builds" in sl[-1] and "validated" in sl[-1], "summary: перестройки/проверки в секунду и их стоимость")
check(bool(ml) and all(m in ml[-1] for m in ("traces avg", "self avg", "other avg", "thr ")), "modules: среднее/пик/доля троттлинга по модулям")

# ------------------------------------------------------------------------------------------------ 2) юнит-проверки снимка
UNIT = r'''
local R = {}
local function check(c, m) if not c then R[#R + 1] = m end end
CLOCK, FRAME = 0, 1
os.clock = function() return CLOCK end
DEL_CALLS, CALLS, HAS = 0, 0, true
CHARS = {}
local function PL(id) return { getPlatoonStringID = function() return id end, squadTemplate = { stringID = "t_" .. id } } end
local function AP(pl) return { me = pl, getIsTrader = function() return false end } end
function MK(nm, x)
  local c = { nm = nm, x = x, del = false }
  c.ap = AP(PL("sq_" .. nm))
  local function m(f) return function(...) CALLS = CALLS + 1; if c.del then DEL_CALLS = DEL_CALLS + 1; error("dangling " .. nm) end; return f(...) end end
  c.isPlayerCharacter = m(function() return false end)
  c.getPosition = m(function() return { x = c.x, z = 0 } end)
  c.isDead = m(function() return false end)
  c.getFaction = m(function() return { getData = function() return { stringID = "f1" } end } end)
  c.getPlatoon = m(function() return c.ap end)
  c.isDown = m(function() return false end); c.isUnconcious = m(function() return false end)
  c.getCurrentTownLocation = m(function() return { town = nm } end)
  CHARS[#CHARS + 1] = c
  return c
end
local SMT = { __index = { has = function(self, c) CALLS = CALLS + 1; return rawget(self, c) == true end } }
function getGameWorld()
  return {
    getCharacterUpdateList = function() local s = {}; for _, c in ipairs(CHARS) do if not c.del then s[c] = true end end; if HAS then setmetatable(s, SMT) end; return s end,
    getTimeStamp = function() return FRAME end,
  }
end
dofile(GOVF)
local G = KMM_Gov
G.cfg.report_s = 10
for i = 1, 10 do MK("c" .. i, i * 10) end
-- кадр 1: сборка
local s1 = G.snapshot(4)
check(s1 and s1.n == 10, "build n=" .. tostring(s1 and s1.n))
local r5
for _, r in ipairs(s1.list) do if r.ch == CHARS[5] then r5 = r end end   -- порядок обхода набора не задан
check(r5.pl and r5.pl:getPlatoonStringID() == "sq_c5", "pl из сборки")
s1.traces_info = "cache"
check(G.snapshot(4) == s1, "тот же кадр: тот же вид")
-- кадр 2: персонаж 3 удалён движком (лут), у 5 другой платун (адрес занят новым персонажем)
FRAME = 2; CLOCK = 0.1
CHARS[3].del = true
local old5 = CHARS[5].ap
CHARS[5].ap = AP(PL("sq_new"))
local d0 = DEL_CALLS
local s2 = G.snapshot(4)
check(s2 and s2 ~= s1, "новый кадр: новый вид")
check(s2.traces_info == nil, "кэш потребителя на виде живёт кадр")
check(s2.n == 9 and #s2.list == 9, "удалённый выпал из list: n=" .. tostring(s2.n))
local found = false
for _, r in ipairs(s2.list) do if r.ch == CHARS[3] then found = true end end
check(not found and s2.by_pkey["sq_c3"] == nil, "удалённый выпал из list/by_pkey")
check(G.snapshot_stats().builds == 1 and G.snapshot_stats().vals == 1, "кадр 2: проверка без пересборки")
check(r5.pl and r5.pl:getPlatoonStringID() == "sq_new", "pl в позднем кадре — заново от живого персонажа")
check(r5.ap ~= old5, "ap в позднем кадре заново")
check(r5.town and r5.town.town == "c5", "town (указатель) в позднем кадре заново")
for _, r in ipairs(s2.list) do local _ = r.pl; local _ = r.town; local _ = r.down end
check(DEL_CALLS == d0, "методы удалённого персонажа не вызывались: " .. (DEL_CALLS - d0))
-- кадр 3..: дальше ttl_rt — пересборка
FRAME = 3; CLOCK = 0.2; G.snapshot(4)
check(G.snapshot_stats().builds == 1 and G.snapshot_stats().vals == 2, "кадр 3 в пределах ttl_rt: проверка")
FRAME = 4; CLOCK = 0.2 + G.cfg.snap.ttl_rt + 0.01; G.snapshot(4)
check(G.snapshot_stats().builds == 2, "старше ttl_rt: пересборка")
-- ttl потребителя меньше ttl_rt
FRAME = 5; CLOCK = CLOCK + 0.3; G.snapshot(0.2)
check(G.snapshot_stats().builds == 3, "ttl потребителя < возраста: пересборка")
-- пауза: та же метка дольше same_frame — проверка, а не слепой повтор
local v0 = G.snapshot_stats().vals
CLOCK = CLOCK + G.cfg.snap.same_frame + 0.05; G.snapshot(4)
check(G.snapshot_stats().vals == v0 + 1, "пауза дольше same_frame: проверка has()")
-- учёт: стоимость снимка не на модуле
G.snapshot_reset()
FRAME = 10; CLOCK = 100
local oldb = getGameWorld
local function heavy() CLOCK = CLOCK + 0.004 end   -- «дорогой» обход: +4 мс на каждом getCharacterUpdateList
getGameWorld = function() local g = oldb(); local f = g.getCharacterUpdateList; g.getCharacterUpdateList = function() heavy(); return f() end; return g end
for i = 1, 12 do
  FRAME = FRAME + 1; CLOCK = CLOCK + 1
  G.run("modx", function() G.snapshot(4); CLOCK = CLOCK + 0.0001 end)
end
local st = G.stats()
check(st.modx and st.modx.peak_ms < 0.2 and st.modx.n == 1, "модуль: пик без снимка " .. tostring(st.modx and st.modx.peak_ms) .. " мс, 1/" .. tostring(st.modx and st.modx.n))
check(st["gov:snapshot"] and st["gov:snapshot"].peak_ms >= 4, "gov:snapshot: пик снимка учтён " .. tostring(st["gov:snapshot"] and st["gov:snapshot"].peak_ms))
getGameWorld = oldb
-- сводка
local f = io.open(G.cfg.debug_log, "r"); local log = f and f:read("*a") or ""; if f then f:close() end
check(log:find("%[KMM_Gov%] summary: ") and log:find("%[KMM_Gov%] modules: .*modx avg"), "маркеры summary/modules в debug.log")
-- без has: правило одного кадра
HAS = false; G.snapshot_reset()
local b0 = G.snapshot_stats().builds
for i = 1, 3 do FRAME = FRAME + 1; CLOCK = CLOCK + 0.1; G.snapshot(4) end
check(G.snapshot_stats().builds == b0 + 3, "без has: пересборка в каждом новом кадре")
R_OUT = #R == 0 and "OK" or table.concat(R, "; ")
'''
UNIT_NOSTAMP = r'''
local R = {}
local function check(c, m) if not c then R[#R + 1] = m end end
CLOCK = 0; os.clock = function() return CLOCK end
CHARS = {}
for i = 1, 5 do
  local c = {}
  c.isPlayerCharacter = function() return false end; c.getPosition = function() return { x = i, z = 0 } end; c.isDead = function() return false end
  c.getFaction = function() return nil end; c.getPlatoon = function() return nil end
  CHARS[i] = c
end
function getGameWorld() return { getCharacterUpdateList = function() local s = {}; for _, c in ipairs(CHARS) do s[c] = true end; return s end } end
dofile(GOVF)
local a = KMM_Gov.snapshot(2); CLOCK = 1.5; local b = KMM_Gov.snapshot(2); CLOCK = 3; local c = KMM_Gov.snapshot(2)
check(a and a == b and c ~= a and KMM_Gov.snapshot_stats().builds == 2, "без метки: прежнее правило ttl")
check(a.list[1].pkey == "" and a.list[1].pl == nil, "без платуна: pkey '' и pl nil")
R_OUT = #R == 0 and "OK" or table.concat(R, "; ")
'''


def unit(code, tag):
    tmp = tempfile.mkdtemp(prefix="kmm_t2_").replace("\\", "/")
    run, get = B.make_state()
    gov_src = open(GOV_NEW, encoding="utf-8").read().replace("C:/KenshiModMap/logs/", tmp + "/")
    gf = tmp + "/gov.lua"
    with open(gf, "w", encoding="utf-8") as f:
        f.write(gov_src)
    run(f'GOVF = "{gf}"', "govf")
    try:
        run(code, tag)
        out = get("R_OUT")
    except RuntimeError as e:
        out = str(e)
    check(out == "OK", f"юнит {tag}: {out}")


unit(UNIT, "снимок")
unit(UNIT_NOSTAMP, "без метки")
print("test_t2_gov:", "OK" if not FAILS else "FAIL " + "; ".join(FAILS))
sys.exit(0 if not FAILS else 1)
