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

------------------------------------------------------------------ ОБОРОТЫ: синтетический мир (метрики подменены, дирижёр не шагает)
local KC = rawget(_G, "KMM_C_INT")
local Y = P.story.cycle
local REAL_METRICS = KC.story_metrics
local SYN = {}
local function syn_flat() SYN = { ore_stress = 1, ore_crisis = false, ore_fracture = false, forged = false, know = 0.5, comp = 80, heat = 1, hs = 0.1, ci = 1 } end
KC.story_metrics = function(c) local m = {}; for k, v in pairs(SYN) do m[k] = v end; m.year = (KC.DAY or 0) / 365; return m end
local function fresh() C.story_reset(); C.reset(); KC.S.story = nil end
local function run_days(d0, d1, f) for dd = d0, d1 do KC.DAY = dd; if f then f(dd) end; KC.STORY.tick(dd) end end
local function is_crisis(a) for _, x in ipairs(Y.crises) do if x == a then return true end end; return false end
local function cycles_ok(stx, tag)   -- каждый законченный оборот: start -> rise -> кризис ... -> recover, длина в min..max лет
  local ok, why = true, ""
  for i, r in ipairs(stx.cycles) do
    local p = r.path
    if p[1] ~= P.story.start or p[2] ~= Y.rise or not is_crisis(p[3]) or p[#p] ~= Y.recover then ok = false; why = why .. " path" .. i .. "=" .. table.concat(p, ">") end
    if r.len < 365 * Y.min_years - 1 or r.len > 365 * Y.max_years + 1 then ok = false; why = why .. " len" .. i .. "=" .. r.len end
  end
  check(ok, tag .. ": cycle structure and length 4..6 y" .. why)
end
local function first_crises(stx) local out = {}; for i, r in ipairs(stx.cycles) do out[i] = r.cr[1] end; return out end

-- 1) ровный мир, 26 лет: обороты идут, возвращаются к началу, повтор того же кризиса подряд гасится
fresh(); syn_flat(); math.randomseed(5)
run_days(0, 365 * 26)
local s1 = C.story_state()
check(not KC.STORY.off, "flat: story alive")
check(#s1.cycles >= 4, "flat: >= 4 full cycles in 26 years (got " .. #s1.cycles .. ")")
cycles_ok(s1, "flat")
local fc = first_crises(s1)
local rep, kinds = 0, {}
for i = 1, #fc do kinds[fc[i]] = true; if i > 1 and fc[i] == fc[i - 1] then rep = rep + 1 end end
local nk = 0; for _ in pairs(kinds) do nk = nk + 1 end
print("flat cycles: " .. table.concat(fc, ",") .. " | len " .. (function() local t = {}; for i, r in ipairs(s1.cycles) do t[i] = string.format("%.2f", r.len / 365) end; return table.concat(t, ",") end)())
check(rep == 0, "flat: no same opening crisis twice in a row (" .. table.concat(fc, ",") .. ")")
check(nk >= 2, "flat: >= 2 different crises over cycles")
local nq = 0
for _, e in ipairs(C.state().events) do if e.type == "story_" .. P.story.start and e.cycle then nq = nq + 1 end end
check(nq >= #s1.cycles, "flat: story_" .. P.story.start .. " event on each return to the start (" .. nq .. ")")
check(s1.cur.n == #s1.cycles + 1, "flat: cycle counter = finished + 1")
-- идемпотентность внутри нового оборота: параметр = база x множитель фазы (сила k x kx оборота)
if s1.act == P.story.start then
  local kk = math.max(0.4, math.min(1.6, s1.k[s1.act] * (s1.cur.kx[s1.act] or 1)))
  check(math.abs(P.chaos.incursion_chance - base_inc * (1 + (0.5 - 1) * kk)) < 1e-9, "flat: start multiplier from base in a later cycle")
else
  local inc = P.chaos.incursion_chance; run_days(365 * 26 + 1, 365 * 26 + 3)
  check(P.chaos.incursion_chance == inc, "flat: daily re-apply does not compound")
end

-- 2) изношенный мир с дрейфом (компоненты 90 -> 5, знание и жар растут, руда дорожает) + всплеск в Охоте каждого оборота:
--    ветвь следует за всплеском (адаптация), и на 3-м..5-м обороте ветки всё ещё разные
local PLAN = { "famine", "night", "twilight", "night", "famine", "twilight" }
local SPIKE = { famine = 0, night = 0, twilight = 0 }
fresh(); syn_flat(); math.randomseed(9)
local wear = 0
run_days(0, 365 * 28, function(dd)
  local y = dd / 365
  local st = KC.S.story
  local n = st and st.cur and st.cur.n or 1
  local want = (st and st.act == Y.rise) and PLAN[n] or nil
  for k in pairs(SPIKE) do SPIKE[k] = (k == want) and math.min(1, SPIKE[k] + 1 / 90) or math.max(0, SPIKE[k] - 1 / 200) end
  if SPIKE.twilight > 0 then wear = wear + 0.12 * SPIKE.twilight end
  SYN.comp = math.max(5, 90 - 3.2 * y) - wear + 0.002 * dd % 3
  SYN.know = 0.4 + 0.08 * y
  SYN.ore_stress = (0.8 + 0.25 * y) * (1 + 0.9 * SPIKE.famine)
  SYN.heat = math.floor(0.2 * y + 4 * SPIKE.night)
  SYN.ci = 0.8 + 0.06 * y + 0.9 * SPIKE.night
  SYN.hs = math.min(1, SYN.heat / 12)
  if wear > 0 and SPIKE.twilight == 0 then wear = math.max(0, wear - 0.03) end
end)
local s2 = C.story_state()
check(not KC.STORY.off, "drift: story alive")
check(#s2.cycles >= 5, "drift: >= 5 full cycles in 28 years (got " .. #s2.cycles .. ")")
cycles_ok(s2, "drift")
local f2 = first_crises(s2)
print("drift cycles: " .. table.concat(f2, ",") .. " | paths " .. (function() local t = {}; for i, r in ipairs(s2.cycles) do t[i] = table.concat(r.path, ">") .. string.format(" %.2fy", r.len / 365) end; return table.concat(t, " ; ") end)())
local follow = 0
for i = 1, math.min(5, #f2) do if f2[i] == PLAN[i] then follow = follow + 1 end end
check(follow == math.min(5, #f2), "drift: crisis follows the world (" .. table.concat(f2, ",") .. " vs " .. table.concat(PLAN, ",", 1, 5) .. ")")
check(f2[3] ~= f2[4] and f2[3] ~= nil and f2[4] ~= nil, "drift: cycles 3 and 4 open with different crises")
local late = {}; for i = 3, #f2 do late[f2[i]] = true end
local nl = 0; for _ in pairs(late) do nl = nl + 1 end
check(nl == 3, "drift: all three branches still reachable from cycle 3 on")
local night_after = false
for _, r in ipairs(s2.cycles) do
  for i, a in ipairs(r.path) do if a == "night" and r.path[i + 1] == Y.after_act then night_after = true end end
end
check(night_after, "drift: night is followed by the after phase (heavy crisis)")
local post_night = false
for i = 2, #s2.cycles do
  for _, a in ipairs(s2.cycles[i - 1].cr) do if a == "night" then post_night = true end end
end
check(post_night, "drift: some cycle came after a night (recovery mods exercised)")

-- 3) сейвы: старое состояние (до оборотов), финал «ashes», мусор в полях, сериализация, нет params.story.cycle
fresh(); syn_flat(); math.randomseed(3)
KC.S.story = { act = "twilight", since = 1700, shift = 0.3, hk = 1.1, k = { quiet = 1, scramble = 1, famine = 1, twilight = 1, night = 1, forge = 1, ashes = 1 },
               hist = { { "quiet", 0 }, { "scramble", 700 }, { "famine", 1300 }, { "twilight", 1700 } }, last = 1800, m = { y = 4.9 } }
run_days(1801, 1801 + 365 * 7)
local s3 = C.story_state()
check(not KC.STORY.off, "old save: story alive")
check(#s3.cycles >= 1 and s3.cycles[1].path[1] == "quiet" and s3.cycles[1].cr[1] == "famine", "old save: cycle 1 rebuilt from hist and closed")
check(s3.cur.n >= 2, "old save: returned to start, new cycle")
fresh(); syn_flat()
KC.S.story = { act = "ashes", since = 4600, shift = 0, hk = 1, k = {}, hist = { { "quiet", 0 }, { "forge", 3600 }, { "ashes", 4600 } }, last = 4700 }
run_days(4701, 4701 + 365 * 2)
check(not KC.STORY.off and C.story_state().cur.n >= 2, "old final ashes: goes on to a new cycle")
fresh(); syn_flat()
KC.S.story = { act = "gone_act", k = "x", hist = 5, cycles = "y", cur = 7, e = "z", pt = "w", since = "?" }
run_days(10, 400)
check(not KC.STORY.off and C.story_state().act == P.story.start, "garbage state: restarts at start, no error")
local ser = KC.serialize(KC.S.story)
local back = KC.deserialize(ser)
check(type(back) == "table" and back.act == C.story_state().act and back.cur.n == C.story_state().cur.n, "state survives serialize/deserialize")
KC.S.story = back; back.cur.future_field = { a = 1 }; back.future_top = 5
run_days(401, 800)
check(not KC.STORY.off, "unknown extra fields are ignored")
local saved_cycle = P.story.cycle
P.story.cycle = nil
fresh(); syn_flat()
run_days(0, 365 * 7)
check(not KC.STORY.off and #C.story_state().cycles >= 1 and #C.story_state().cycles[1].cr >= 1, "no params.story.cycle (old config): defaults still cycle through a crisis")
P.story.cycle = saved_cycle
KC.story_metrics = REAL_METRICS
C.story_reset(); C.reset()
print(N .. " checks")
if #FAILS > 0 then print("FAILS: " .. table.concat(FAILS, "; ")); error("story test failed") end
''', "test")
print("OK")
