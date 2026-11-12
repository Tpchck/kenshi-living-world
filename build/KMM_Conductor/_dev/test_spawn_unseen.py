"""Offline test: spawn only out of sight (Traces all kinds, ambush wait/track, no point -> no spawn). python -I -X utf8 build/KMM_Conductor/_dev/test_spawn_unseen.py -> OK."""
import ctypes
import os
import re
import sys
import tempfile

DLL = r"C:\Program Files (x86)\Steam\steamapps\workshop\content\233860\3817000612\lua51.dll"
B = r"C:\KenshiModMap\build\KMM_Conductor\scripts\init"
TMP = tempfile.mkdtemp(prefix="kmm_unseen_").replace("\\", "/")
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
stubs = re.search(r"STUBS = r'''(.*?)'''", rt, re.S).group(1).replace("TMPDIR", TMP)
run(stubs, "stubs")
run("math.randomseed(20261112)", "seed")   # детерминизм: без сида тест изредка падал
for _f in sorted(__import__("glob").glob(B + r"\KMM_Conductor*.lua")): run(open(_f, encoding="utf-8").read(), _f.split("\\")[-1])
run(open(B + r"\KMM_Traces.lua", encoding="utf-8").read(), "KMM_Traces.lua")
run(r'''
N, FAILS = 0, {}
function check(c, what) N = N + 1; if not c then FAILS[#FAILS + 1] = what end end
function ticks(n) for i = 1, n do CLOCK = CLOCK + 1; DAYV = DAYV + 0.001; FIRE("GameWorld::charsUpdate", {}) end end
local C = KMM_Conductor
C.reset()
local TP = C.cfg().params.traces
C.cfg().params.roads.scouts = false   -- ROADS: предвестники проверяются в test_roads.py
TP.first_hour_traces = 0; TP.max_per_day = 1000; TP.max_queue = 1000; TP.arrive_enabled = false   -- очередь не вытесняет виды (GOALS-события), arrive вне теста
local tr = C.read_json("traces.json", "C:/KenshiModMap/build/KMM_Conductor/traces.json")
local pf = C.cfg().player_faction
TARGETS = {}
local gw0 = getGameWorld
function getGameWorld()
  local g = gw0(); local orig = g.theFactory.createRandomSquad
  g.theFactory.createRandomSquad = function(self, f, pos, home, maxnum, b, gd, o, m, ap, perm, target, ttown, mult, sqt, rf)
    orig(self, f, pos, home, maxnum, b, gd, o, m, ap, perm, target, ttown, mult, sqt, rf)
    local n = #SPAWNS; TARGETS[n] = target
    local pl = PLATOON("sq" .. n, gd and gd.stringID)
    pl.leader = { getHandle = function() return "lead" .. n end }
    return pl
  end
  return g
end
local T, TX, TZ, B, A
for sid, I in pairs(C.cfg().town_info) do
  for fid, f in pairs(C.state().F) do
    if f.alive and f.towns[sid] and tr.live_caravans[fid] and tr.factions[fid] and tr.factions[fid].refugees and tr.factions[fid].tiers and next(tr.factions[fid].tiers) and I.x and not f.player then T, TX, TZ, B = sid, I.x, I.z, fid end
  end
  if T then break end
end
for fid, f in pairs(C.state().F) do if f.alive and not f.player and fid ~= B and tr.factions[fid] and tr.factions[fid].tiers and next(tr.factions[fid].tiers) then A = fid; break end end   -- пустые tiers (Fogmen) = {} истинно в Lua: такой грабитель не выводит отрядов
check(T and A and B, "найдены город, жертва и грабитель")
local function setpcs(list)
  PCS = {}; CHARS = {}
  for i, p in ipairs(list) do PCS[i] = MKCH("PC" .. i, pf or "player", p[1], p[2], { player = true, platoon = "player_squad" }); CHARS[i] = PCS[i] end
end
local function far_ok(from)   -- все спавны с индекса from: >= 3500 от каждого персонажа игрока, <= 6000 от ближайшего
  local worst, wmax = 1e9, 0
  for i = from, #SPAWNS do
    local s = SPAWNS[i]; local near = 1e9
    for _, p in ipairs(PCS) do
      local pos = p:getPosition(); local d = math.sqrt((s.x - pos.x) ^ 2 + (s.z - pos.z) ^ 2)
      if d < worst then worst = d end
      if d < near then near = d end
    end
    if near > wmax then wmax = near end
  end
  return worst >= 3500 and wmax <= 6000, worst, wmax
end
setpcs({ { TX + 2500, TZ }, { TX - 1000, TZ + 3000 } })
ticks(5)

-- 1) все виды следов (очередь) и видимые события: не ближе 3500 ни к одному персонажу
C.cfg().params.traces.base_near = 1e9   -- REV2: рейд на базу ждёт игрока у базы (см. test_rev2); здесь проверяется только точка спавна
local s0 = #SPAWNS
local kinds = { { kind = "refugees", fid = A }, { kind = "column", fid = A, enemy = B, tx = TX, tz = TZ }, { kind = "band", fid = A, n = 2 },
                { kind = "garrison", fid = A, tx = TX, tz = TZ }, { kind = "base_raid", fid = A, enemy = "player" }, { kind = "caravan", fid = B } }
if tr.daemons and tr.daemons.faction and #(tr.daemons.squads or {}) > 0 then kinds[#kinds + 1] = { kind = "daemons", fid = tr.daemons.faction } end
for round = 1, 3 do
  for _, j in ipairs(kinds) do
    local jj = {}; for k, v in pairs(j) do jj[k] = v end; jj.ev = round
    KMM_Traces._enqueue(jj)
    DAYV = DAYV + 1; CLOCK = CLOCK + 100; ticks(2)
  end
end
for _ = 1, 12 do if #KMM_Traces.queue() == 0 then break end; DAYV = DAYV + 1; CLOCK = CLOCK + 100; ticks(2) end   -- дослить очередь: порядок задач зависит от адресов таблиц (pairs), виды не должны теряться
check(#SPAWNS - s0 >= #kinds, "следы всех видов спавнятся (" .. (#SPAWNS - s0) .. ")")
local ok1, w1, m1 = far_ok(s0 + 1)
check(ok1, string.format("следы: все >= 3500 и <= 6000 (min %.0f, max %.0f)", w1, m1))
local bk = KMM_Traces.stats().by_kind
check(bk.base_raid and bk.band and bk.refugees and bk.column and bk.garrison and bk.caravan, "все виды учтены: " .. (function() local o = "" for k, v in pairs(bk) do o = o .. k .. "=" .. v .. " " end local st = KMM_Traces.stats(); return o .. "dis=" .. tostring(next(KMM_Traces.disabled())) .. " sdead=" .. tostring(st.skipped_dead) .. " slow=" .. tostring(st.skipped_low) .. " Q=" .. (function() local o = "" for _, j in ipairs(KMM_Traces.queue()) do o = o .. j.kind .. ":" .. tostring(j.fid == A) .. ":" .. tostring(j.tries) .. "," end return o end)() .. " A=" .. tostring(A) end)())
local br; for i = s0 + 1, #SPAWNS do if TARGETS[i] ~= nil then br = i end end
check(br ~= nil, "base_raid идёт целью на игрока")

local VK = { { "trade_for", { cat = "food" } }, { "refugees", { n = 4, why = "x" } }, { "relic_salvage", {} }, { "smuggle_run", { cat = "x" } } }
for k = 1, 3 do
  for n, v in ipairs(VK) do
    local s1 = #SPAWNS
    local ev = { type = v[1], a = B, town_sid = T, town_name = "T" .. k .. n }
    for kk, vv in pairs(v[2]) do ev[kk] = vv end
    if v[1] == "trade_for" then ev.b = B end
    CLOCK = CLOCK + 2000; C.emit(ev); for _ = 1, 60 do CLOCK = CLOCK + 100; ticks(1) end
    if #SPAWNS > s1 then local ok, w = far_ok(s1 + 1); check(ok, string.format("видимое %s: >= 3500 (min %.0f)", v[1], w)) end
  end
end
local dd = ""; for k, v in pairs(KMM_Traces.disabled()) do dd = dd .. k .. "," end
local vb = "dis=" .. dd .. " "; for k, v in pairs(bk) do vb = vb .. k .. "=" .. v .. " " end
check((bk.vcaravan or 0) >= 1 and (bk.vrefugees or 0) >= 1, "видимые события спавнятся вне видимости: " .. vb)

-- 2) нет допустимой точки -> нет спавна (и не ближе), задача остаётся
TP.unseen_max = 3400
local s2 = #SPAWNS
KMM_Traces._enqueue({ kind = "band", fid = A, n = 2, ev = 777 })
for i = 1, 5 do CLOCK = CLOCK + 100; DAYV = DAYV + 1; ticks(3) end
check(#SPAWNS == s2, "нет допустимой точки: спавна нет (" .. (#SPAWNS - s2) .. ")")
check(#KMM_Traces.queue() >= 1, "задача осталась в очереди (повтор позже)")
TP.unseen_max = 6000
CLOCK = CLOCK + 5000; DAYV = DAYV + 5; ticks(3)
check(#SPAWNS > s2, "точка появилась: спавн состоялся после повтора")
local ok2, w2 = far_ok(s2 + 1); check(ok2, "после повтора тоже >= 3500")

-- 3) засада. Мир: у жертвы город T и дальний пункт D; режим wait, если на маршруте есть допустимая точка
local function world(towns)
  C.reset(); DAYV = 10; C.state().last_day = 10; C.state().F[B].towns = towns
  local am, aq = KMM_Traces.ambush(); for k in pairs(am) do am[k] = nil end; for i = #aq, 1, -1 do aq[i] = nil end
  for _ = 1, 40 do CLOCK = CLOCK + 100; ticks(1) end   -- очередь следов дренируется, пауза спавна проходит
  CLOCK = CLOCK + 5000
  local st = C.stock_state(); st.towns = {}
  local s = { q = {}, tn = {}, lv = {} }
  for _, c in ipairs({ "food", "metal", "weapons", "armor", "med", "drugs", "lux", "scrap" }) do s.q[c] = 200; s.tn[c] = 100; s.lv[c] = 2 end
  st.towns[T] = s
end
local function force_waylay()
  local p0 = C.ambush_pending()
  for seed = 1, 300 do
    math.randomseed(seed); C.state().F[A].last_waylay = nil
    C._waylay(A, B)
    if C.ambush_pending() > p0 then return seed end
  end
end
C.cfg().town_info.fakeD = { x = TX + 9000, z = TZ, name = "Dest" }
world({ [T] = true, fakeD = true })
setpcs({ { TX + 4000, TZ + 4200 } }); ticks(1)
local s3 = #SPAWNS
check(force_waylay() ~= nil, "засада решена (wait)")
ticks(3)
local _, aq0 = KMM_Traces.ambush()
check(#SPAWNS == s3 + 2, "wait: пара спавнится (" .. (#SPAWNS - s3) .. ") AQ=" .. #aq0 .. " pend=" .. C.ambush_pending() .. " dis=" .. tostring(next(KMM_Traces.disabled())))
if #SPAWNS ~= s3 + 2 then print(table.concat(FAILS, " | ")); error("stop") end
local am = KMM_Traces.ambush(); local id, e = next(am)
check(e and e.mode == "wait", "режим wait: засада заранее на маршруте")
check(TARGETS[s3 + 2] == nil or not tostring(TARGETS[s3 + 2]):find("^lead"), "wait: грабители стоят (без цели; null hand допустим)")
check(SPAWNS[s3 + 1].fid == B and SPAWNS[s3 + 2].fid == A, "караван первым, потом грабители")
local okw, ww = far_ok(s3 + 1); check(okw, string.format("wait: оба >= 3500 (min %.0f)", ww))
check(math.abs(SPAWNS[s3 + 2].z - TZ) < 1 and SPAWNS[s3 + 2].x > TX + 2000 and SPAWNS[s3 + 2].x < TX + 7000, "грабители на маршруте T-D")
check(SPAWNS[s3 + 1].x < SPAWNS[s3 + 2].x and math.abs(SPAWNS[s3 + 1].z - TZ) < 1, "караван стартует позади точки засады, на том же маршруте")
world({ [T] = true })   -- нет второго пункта: выслеживание
setpcs({ { TX + 4000, TZ + 4200 } }); ticks(1)
local s4 = #SPAWNS
check(force_waylay() ~= nil, "засада решена (track)")
ticks(3)
check(#SPAWNS == s4 + 2, "track: пара спавнится")
am = KMM_Traces.ambush(); id, e = next(am)
check(e and e.mode == "track", "режим track: выслеживание")
check(TARGETS[s4 + 2] == "lead" .. (s4 + 1), "track: цель грабителей - лидер каравана")
local okt, wt = far_ok(s4 + 1); check(okt, string.format("track: оба >= 3500 (min %.0f)", wt))

-- нет допустимой точки -> засада не спавнится
world({ [T] = true, fakeD = true })
setpcs({ { TX + 4000, TZ + 4200 } }); ticks(1)
TP.unseen_max = 3400
local s5 = #SPAWNS
force_waylay(); ticks(5)
check(#SPAWNS == s5, "засада: нет допустимой точки - нет спавна")
TP.unseen_max = 6000

print(N .. " checks, fails: " .. #FAILS)
for _, f in ipairs(FAILS) do print("FAIL " .. f) end
if #FAILS > 0 then error("FAILS " .. #FAILS) end
''', "tests")
print("OK")
