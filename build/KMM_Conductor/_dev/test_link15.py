"""Офлайн-тест LINK15: видимая засада (пара, исходы, таймаут, лимиты) и тир отряда по знанию. python -I -X utf8 build/KMM_Conductor/_dev/test_link15.py -> OK, код 1 при провале."""
import ctypes
import os
import re
import sys
import tempfile

DLL = r"C:\Program Files (x86)\Steam\steamapps\workshop\content\233860\3817000612\lua51.dll"
B = r"C:\KenshiModMap\build\KMM_Conductor\scripts\init"
TMP = tempfile.mkdtemp(prefix="kmm_l15_").replace("\\", "/")
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
for _f in sorted(__import__("glob").glob(B + r"\KMM_Conductor*.lua")): run(open(_f, encoding="utf-8").read(), _f.split("\\")[-1])
run(open(B + r"\KMM_Traces.lua", encoding="utf-8").read(), "KMM_Traces.lua")
run(r'''
N, FAILS = 0, {}
function check(c, what) N = N + 1; if not c then FAILS[#FAILS + 1] = what end end
function ticks(n) for i = 1, n do CLOCK = CLOCK + 1; DAYV = DAYV + 0.001; FIRE("GameWorld::charsUpdate", {}) end end
local C = KMM_Conductor
C.reset()
C.cfg().params.traces.first_hour_traces = 0; C.cfg().params.traces.arrive_enabled = false; C.cfg().params.ws_slice = 1e9; C.cfg().params.rng_fixed = true
local tr = C.read_json("traces.json", "C:/KenshiModMap/build/KMM_Conductor/traces.json")
local pf = C.cfg().player_faction
TARGETS = {}
local gw0 = getGameWorld
function getGameWorld()   -- createRandomSquad возвращает платун с лидером; помним цель (AItarget)
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
local function skeys(t) local k = {}; for x in pairs(t) do k[#k + 1] = x end; table.sort(k); return k end   -- детерминированный порядок (pairs зависит от адресов)
for _, sid in ipairs(skeys(C.cfg().town_info)) do local I = C.cfg().town_info[sid]
  for _, fid in ipairs(skeys(C.state().F)) do local f = C.state().F[fid]
    if f.alive and f.towns[sid] and tr.live_caravans[fid] and I.x and not f.player and C.cfg().factions[fid] then T, TX, TZ, B = sid, I.x, I.z, fid end
  end
  if T then break end
end
for _, fid in ipairs(skeys(C.state().F)) do local f = C.state().F[fid]; if f.alive and not f.player and fid ~= B and C.cfg().factions[fid] and tr.factions[fid] and tr.factions[fid].tiers and next(tr.factions[fid].tiers) then A = fid; break end end
check(T and A and B, "найдены город, жертва и грабитель")
local function mkstock()
  local st = C.stock_state(); st.towns = {}
  local s = { q = {}, tn = {}, lv = {} }
  for _, c in ipairs({ "food", "metal", "weapons", "armor", "med", "drugs", "lux", "scrap" }) do s.q[c] = 200; s.tn[c] = 100; s.lv[c] = 2 end
  st.towns[T] = s
  return s
end
local function setp(x, z) PCS[1] = MKCH("Nameless", pf or "player", x, z, { player = true, platoon = "player_squad" }); CHARS = { PCS[1], }; ticks(1) end
local function evs(ty) local n = 0; for _, e in ipairs(C.state().events) do if e.type == ty then n = n + 1 end end; return n end
local function lastev(ty) local r; for _, e in ipairs(C.state().events) do if e.type == ty then r = e end end; return r end
local function world()   -- свежий мир + чистое состояние Traces + свежий склад
  C.reset(); C.state().treaties = {}; DAYV = 10; C.state().last_day = 10; C.state().F[B].towns = { [T] = true }   -- у жертвы один город: засада всегда у него
  local am, aq = KMM_Traces.ambush(); for k in pairs(am) do am[k] = nil end; for i = #aq, 1, -1 do aq[i] = nil end
  CLOCK = CLOCK + 5000; SPAWNS_N = #SPAWNS
  return mkstock()
end
local function force_waylay()   -- случайность конвоя: подбираем зерно, пока засада не состоится
  local p0, w0 = C.ambush_pending(), evs("waylay")
  for seed = 1, 300 do
    math.randomseed(seed); C.state().F[A].last_waylay = nil
    C._waylay(A, B)
    if C.ambush_pending() > p0 or evs("waylay") > w0 then return seed end
  end
end
local function mkchar(nm, fid, x, z, key, trader, dead)
  local c = MKCH(nm, fid, x, z, { platoon = key })
  local pl = PLATOON(key)
  c.dead = dead or false
  function c:getPlatoon() return setmetatable({ me = pl }, { __index = { getIsTrader = function() return trader end } }) end
  function c:attackTarget(w) c.attacked = w end
  return c
end
PCS = { MKCH("Nameless", pf or "player", TX + 2500, TZ, { player = true, platoon = "player_squad" }) }; CHARS = { PCS[1] }
ticks(5)

-- 1) пара спавнится один раз, в лимитах, грабителям задана цель
local st = world()
local s0 = #SPAWNS
setp(TX + 2500, TZ)
check(force_waylay() ~= nil and C.ambush_pending() == 1, "игрок рядом: абстрактный исход отложен")
check(evs("waylay") == 0 and st.q.food == 200 and st.q.metal == 200, "груз цел, пока бой не решён")
ticks(3)
check(#SPAWNS == s0 + 2, "пара: 2 спавна (" .. (#SPAWNS - s0) .. ")")
check(SPAWNS[s0 + 1].fid == B and SPAWNS[s0 + 1].sid == tr.live_caravans[B], "первым спавнится живой караван жертвы")
check(SPAWNS[s0 + 2].fid == A, "вторым — отряд грабителя")
check(TARGETS[s0 + 2] == "lead" .. (s0 + 1), "грабителям задана цель — лидер каравана")
check(KMM_Traces.stats().by_kind.vambush == 1, "vambush=1")
ticks(20)
check(#SPAWNS == s0 + 2, "пара не спавнится повторно")
C.state().stats.waylay = 0
force_waylay()
check(C.ambush_pending() == 1 and (C.state().stats.waylay or 0) >= 1, "пауза 60 с: второй waylay абстрактный")
CLOCK = CLOCK + 700   -- PACE: враждебная пауза hostile_gap_seconds (600 с)
check(force_waylay() ~= nil and C.ambush_pending() == 2, "после паузы: вторая засада отложена")
ticks(3)
check(KMM_Traces.stats().by_kind.vambush == 2 and #SPAWNS == s0 + 4, "вторая пара спавнится")
CLOCK = CLOCK + 100
C.state().stats.waylay = 0
force_waylay()
check(C.ambush_pending() == 2 and (C.state().stats.waylay or 0) >= 1, "4 живых: третья пара не спавнится, исход абстрактный")
-- далеко от города жертвы → абстрактно
st = world(); setp(TX + 60000, TZ)
force_waylay()
check(C.ambush_pending() == 0 and evs("waylay") == 1, "игрок далеко: абстрактно, как раньше")

-- 2) отбитая засада при игроке рядом: груз цел, rel/trust +
local function ambush_setup(px_off)
  st = world(); setp(TX + 2500, TZ)
  force_waylay(); ticks(3)
  local am = KMM_Traces.ambush(); local id, e = next(am)
  setp(e.x + px_off, e.z)
  return id, e
end
local id, e = ambush_setup(500)
local r0, t0 = C.rel(B, pf), C.state().F[B].trust[pf] or 0
local car = mkchar("car", B, e.x, e.z, e.ckey, true)
local rob = mkchar("rob", A, e.x + 300, e.z, e.rkey, false)
CHARS = { PCS[1], car, rob }
ticks(6)
check(rob.attacked == car, "грабителям отдан приказ атаковать караван")
rob.dead = true
ticks(12)
check(evs("waylay_repelled") == 1 and C.ambush_pending() == 0, "waylay_repelled, засада закрыта")
check(evs("waylay") == 0 and st.q.food == 200 and st.q.metal == 200 and st.q.weapons == 200, "груз цел, добычи нет")
check(C.rel(B, pf) > r0 and (C.state().F[B].trust[pf] or 0) > t0, "рядом был игрок: rel и trust жертвы к игроку растут")
-- отбита без игрока рядом
id, e = ambush_setup(3300)
r0 = C.rel(B, pf)
car = mkchar("car", B, e.x, e.z, e.ckey, true); rob = mkchar("rob", A, e.x + 300, e.z, e.rkey, false)
CHARS = { PCS[1], car, rob }; ticks(6); rob.dead = true; ticks(12)
check(evs("waylay_repelled") == 1 and C.rel(B, pf) == r0, "отбита без игрока: rel к игроку не меняется")

-- 3) погибший караван → caravan_lost(killer = грабитель) + добыча
id, e = ambush_setup(3300)
car = mkchar("car", B, e.x, e.z, e.ckey, true); rob = mkchar("rob", A, e.x + 300, e.z, e.rkey, false)
CHARS = { PCS[1], car, rob }; ticks(6); car.dead = true; ticks(12)
local cl = lastev("caravan_lost")
check(cl and cl.killer == A and cl.a == B and cl.by == "other", "caravan_lost(killer=грабитель, by=other)")
check(evs("waylay") == 1 and C.ambush_pending() == 0 and evs("waylay_repelled") == 0, "абстрактная добыча грабителя выдана, засада закрыта")
id, e = ambush_setup(500)
car = mkchar("car", B, e.x, e.z, e.ckey, true); rob = mkchar("rob", A, e.x + 300, e.z, e.rkey, false)
CHARS = { PCS[1], car, rob }; ticks(6); car.dead = true; ticks(12)
cl = lastev("caravan_lost")
check(cl and cl.by == "player" and cl.killer == A, "караван погиб при игроке, грабители живы: by=player (пособник)")

-- 4) таймаут 2 игровых дня → абстрактный исход как раньше
st = world(); setp(TX + 2500, TZ); force_waylay()
check(C.ambush_pending() == 1, "таймаут: засада отложена")
C.state().last_day = 11; C._ambush_expire()
check(C.ambush_pending() == 1 and evs("waylay") == 0, "через 1 день ещё ждём")
C.state().last_day = 13; C._ambush_expire()
check(C.ambush_pending() == 0 and evs("waylay") == 1 and C.state().stats.ambush_timeout == 1, "через 2 дня: абстрактный исход")
check(st.q.food < 200 or st.q.metal < 200 or st.q.weapons < 200 or st.q.armor < 200 or st.q.med < 200 or st.q.drugs < 200 or st.q.lux < 200 or st.q.scrap < 200, "груз списан при таймауте")

-- 5) тир отряда по знанию: высокий know → ступень выше (если есть); gear_shift -1 → ниже
local ups, tot, hi_n = 0, 0, 0
local gdown = 0
for fid, e2 in pairs(tr.factions) do
  local f = C.state().F[fid]
  if f and f.alive and e2.tiers then
    local base = KMM_Traces.tier_pick(fid)
    local k0 = f.know; f.know = 0; local _, t_lo = KMM_Traces.tier_pick(fid); f.know = 3; local _, t_hi = KMM_Traces.tier_pick(fid); f.know = k0
    tot = tot + 1
    if t_hi ~= t_lo then ups = ups + 1; check(t_hi > t_lo, "высокий know не понижает тир") end
    local g0 = f.gear_shift; f.know = 0; f.gear_shift = 0; local _, tn = KMM_Traces.tier_pick(fid, 0, true); f.gear_shift = -1; local _, tg = KMM_Traces.tier_pick(fid, 0, true); f.gear_shift = g0; f.know = k0
    if tg ~= tn then gdown = gdown + 1; check(tg < tn, "gear_shift -1 не повышает тир") end
  end
end
check(ups > 0, "знание поднимает тир хотя бы у части фракций (" .. ups .. "/" .. tot .. ")")
check(gdown > 0, "gear_shift -1 опускает тир у части фракций (" .. gdown .. "/" .. tot .. ")")
print(string.format("tier_know: up %d/%d factions at know=3; gear_down %d/%d", ups, tot, gdown, tot))
-- частота в живом мире: 15 лет симуляции, выборка раз в 90 дней
C.reset()
math.randomseed(2026)
local samp, chg = 0, 0
for d = 1, 5475 do
  C.advance(d)
  if d % 90 == 0 then
    for fid, e2 in pairs(tr.factions) do
      local f = C.state().F[fid]
      if f and f.alive and not f.player and e2.tiers then
        local _, ta = KMM_Traces.tier_pick(fid)
        local k0 = f.know; f.know = 0; local _, tb = KMM_Traces.tier_pick(fid); f.know = k0
        samp = samp + 1; if ta ~= tb then chg = chg + 1 end
      end
    end
  end
end
print(string.format("tier_know live sim 15y: know changes pick in %d/%d samples (%.1f%%)", chg, samp, 100 * chg / math.max(1, samp)))
-- 6) caravan_lost с ambush=id: модель склада не списывает груз второй раз (только waylay_finish)
do
  local M = dofile("C:/KenshiModMap/build/KMM_Stock/scripts/kmm_stock_model.lua")
  local function run1(amb)
    math.randomseed(5); C.reset(); local S = C.state(); M.init(S.stock, S, C.cfg())
    local sid; for t, s in pairs(S.stock.towns) do if S.F[B] and S.F[B].towns[t] then sid = t; break end end
    S.last_day = 20
    local food0 = S.stock.towns[sid].q.food
    S.events[#S.events + 1] = { id = 999999, type = "caravan_lost", a = B, town_sid = sid, day = 20, ambush = amb }
    M.day(S.stock, S, 21, function(ev) return C.emit(ev) end)
    return S.stock.towns[sid].q.food, S.stock.towns[sid].cut
  end
  local fa, ca = run1(7); local fn, cn = run1(nil)
  check(fa > fn and ca ~= nil, "ambush-caravan_lost: склад не режется моделью (" .. string.format("%.1f vs %.1f", fa, fn) .. "), маршрут закрыт")
end
print(N .. " checks, fails: " .. #FAILS)
for _, f in ipairs(FAILS) do print("FAIL " .. f) end
if #FAILS > 0 then error("FAILS " .. #FAILS) end
''', "tests")
print("OK")
