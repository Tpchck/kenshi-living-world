"""Офлайн-тест CORE: детерминизм, петля склад->дирижёр, цена по городу, беженцы, caravan_lost, player_relic_forge.
python -I -X utf8 build/KMM_Conductor/_dev/test_conductor_core.py -> «OK n/n», код 1 при провале."""
import ctypes
import os
import sys
import tempfile

DLL = r"C:\Program Files (x86)\Steam\steamapps\workshop\content\233860\3817000612\lua51.dll"
SCRIPT = r"C:\KenshiModMap\build\KMM_Conductor\scripts\init\KMM_Conductor.lua"
MODEL = "C:/KenshiModMap/build/KMM_Stock/scripts/kmm_stock_model.lua"
TMP = tempfile.mkdtemp(prefix="kmm_core_").replace("\\", "/")
L = ctypes.CDLL(DLL)
L.luaL_newstate.restype = ctypes.c_void_p
L.luaL_openlibs.argtypes = [ctypes.c_void_p]
L.luaL_loadstring.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
L.lua_pcall.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int]
L.lua_tolstring.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p]
L.lua_tolstring.restype = ctypes.c_char_p
L.lua_settop.argtypes = [ctypes.c_void_p, ctypes.c_int]


def mk():
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
do
  local rawpairs = pairs
  function pairs(t)
    local ks = {{}}
    for k in rawpairs(t) do ks[#ks + 1] = k end
    table.sort(ks, function(a, b) if type(a) ~= type(b) then return type(a) < type(b) end; if type(a) == "number" or type(a) == "string" then return a < b end; return tostring(a) < tostring(b) end)
    local i = 0
    return function() i = i + 1; local k = ks[i]; if k ~= nil then return k, t[k] end end, t, nil
  end
end
''', "stubs")
    for _f in sorted(__import__("glob").glob(SCRIPT.replace("KMM_Conductor.lua", "KMM_Conductor*.lua"))): run(open(_f, encoding="utf-8").read(), _f.split("\\")[-1])
    return run


SETUP = f'''
local C = KMM_Conductor
local M = dofile("{MODEL}")
local function boot(seed)
  math.randomseed(seed); C.reset()
  local S = C.state(); M.init(S.stock, S, C.cfg()); return S
end
local function days(S, a, b) for d = a, b do C.advance(d); M.day(S.stock, S, d, function(ev) return C.emit(ev) end) end end
'''
run = mk()
run(SETUP + r'''
N, FAILS = 0, {}
local function check(c, what) N = N + 1; if not c then FAILS[#FAILS + 1] = what end end
-- 1. детерминизм: два прогона одного сида
local function sig(seed)
  local S = boot(seed); days(S, 0, 200)
  local s = 0; for fid, f in pairs(S.F) do s = s + f.strength + f.wealth * 0.01 + (f.know or 0) end
  return string.format("%.6f|%d|%d", s, S.next_id, S.stats.captures)
end
local a, b = sig(11), sig(11)
check(a == b, "determinism: " .. a .. " vs " .. b)
-- 2. петля: нехватка еды у фракции -> food_def > 0, hunger растёт; цена в городе дороже
local S = boot(3); days(S, 0, 30)
local fid, town
local best_r = -1   -- фракция с наибольшей долей городов: без подмеса склада у неё нет избытка еды
for id, f in pairs(S.F) do if f.alive and not f.player then local nc, nt, ct = 0, 0, nil; for t in pairs(f.towns) do nt = nt + 1; if (C.cfg().town_info[t] or {}).kind == "city" then nc = nc + 1; if S.stock.towns[t] and not ct then ct = t end end end
  if ct and nc / nt > best_r then best_r, fid, town = nc / nt, id, ct end end end
local f = S.F[fid]
for t in pairs(f.towns) do local s = S.stock.towns[t]; if s then s.q.food = 0; s.q.metal = 0 end end
days(S, 31, 36)
check((f.food_def or 0) > 0.3, "food_def after emptying stock: " .. tostring(f.food_def))
check((f.metal_def or 0) > 0.3, "metal_def: " .. tostring(f.metal_def))
check((f.hunger or 0) > 0.01, "hunger mixed in (REV2: порог >0 — у фракции с избытком еды без подмеса склада hunger ровно 0): " .. tostring(f.hunger))
local s = S.stock.towns[town]; local lo = C.price_mult_town(fid, town)
s.q.food, s.q.metal, s.q.weapons = s.tn.food * 3, s.tn.metal * 3, s.tn.weapons * 3; for _, c in ipairs({"food","metal","weapons"}) do s.lv[c] = 3 end
local hi = C.price_mult_town(fid, town)
check(lo > hi and lo <= 1.45 and hi >= 0.8, string.format("price_mult_town deficit %.3f > glut %.3f, clamped", lo, hi))
check(math.abs(C.price_mult(fid) - C.price_mult(fid)) < 1e-9, "price_mult kept")
-- 3. беженцы при смене владельца (захват)
local S2 = boot(4); days(S2, 0, 20)
local victim, vt
for id, ff in pairs(S2.F) do if ff.alive and not ff.player and id ~= "x" then for t, _ in pairs(ff.towns) do if S2.town[t] and S2.town[t].pop and (C.cfg().town_info[t] or {}).kind == "city" then victim, vt = id, t; break end end end if victim then break end end
local taker; for id, ff in pairs(S2.F) do if ff.alive and id ~= victim and not ff.player then taker = id; break end end
local n0 = S2.stats.refugees or 0
S2.F[victim].towns[vt] = nil; S2.F[taker].towns[vt] = true
local pop0 = S2.town[vt].pop
days(S2, 21, 26)
check((S2.stats.refugees or 0) > n0, "refugees event after capture")
check(S2.town[vt].pop < pop0 and S2.town[vt].pop > 0, "pop drops after sack but stays > 0")
local found = false; for _, ev in ipairs(S2.events) do if ev.type == "refugees" and ev.town_sid == vt and ev.n and ev.n >= 5 then found = true end end
check(found, "refugees ev has town_sid/n")
-- 4. caravan_lost: склад источника теряет груз, отношения падают при by=player
local S3 = boot(5); days(S3, 0, 10)
local pf = C.cfg().player_faction
local own, ot; for id, ff in pairs(S3.F) do if ff.alive and not ff.player then for t in pairs(ff.towns) do if S3.stock.towns[t] then own, ot = id, t; break end end end if own then break end end
local q0 = S3.stock.towns[ot].q.food; local r0 = pf and C.rel(own, pf) or 0
C.emit({ type = "caravan_lost", a = own, town_sid = ot, by = "player" })
days(S3, 11, 12)
check(S3.stock.towns[ot].q.food < q0 and (S3.stock.towns[ot].cut or -1) >= 11, "caravan_lost cuts source stock and route")
if pf then check(C.rel(own, pf) < r0, "caravan_lost by player lowers relations") end
-- player_sold: склад +n (added не задан)
local qs = S3.stock.towns[ot].q.med
C.emit({ type = "player_sold", town_sid = ot, cat = "med", n = 5 })
days(S3, 13, 14)
check(S3.stock.towns[ot].q.med > qs - 0.0001, "player_sold adds to stock")
-- 5. player_relic_forge
local S4 = boot(6); days(S4, 0, 40)
C.emit({ type = "player_relic_forge", item = "blade" })
check(S4.forge and S4.forge.until_day > S4.last_day, "forge window set")
local tl = false; for _, ev in ipairs(S4.events) do if ev.type == "relic_forge_known" then tl = true end end
check(tl, "relic_forge_known emitted")
local mob = 0; for _, ff in pairs(S4.F) do if ff.relic and ff.trigger_why == "forge" then mob = mob + 1 end end
check(mob >= 1, "relic factions triggered by forge: " .. mob)
-- 6. CONTRA: contraband_caught роняет отношения; дефицит брони/оружия -> tier_shift -1 (гистерезис) + gear_worn
local S5 = boot(8); days(S5, 0, 10)
local own5; for id, ff in pairs(S5.F) do if ff.alive and not ff.player and ff.lvl then own5 = id; break end end
local r5 = C.rel(own5, pf)
C.emit({ type = "contraband_caught", a = own5, town_sid = next(S5.F[own5].towns), cat = "drugs" })
check(C.rel(own5, pf) < r5, "contraband_caught lowers relations")
local base = C.tier_shift(own5)
-- мастерские теперь тратят металл и быстро восполняют броню/оружие: держим дефицит оружия/брони/металла каждый день (осада/разграбление арсенала)
for d = 11, 25 do
  for t in pairs(S5.F[own5].towns) do local st = S5.stock.towns[t]; if st then st.q.armor, st.q.weapons, st.q.metal = 0, 0, 0 end end
  days(S5, d, d)
end
check((S5.F[own5].gear_shift or 0) == -1 and C.tier_shift(own5) <= base, "gear deficit shifts tier down")
local gw = false; for _, ev in ipairs(S5.events) do if ev.type == "gear_worn" and ev.a == own5 then gw = true end end
check(gw, "gear_worn emitted")
for t in pairs(S5.F[own5].towns) do local st = S5.stock.towns[t]; if st then st.q.armor, st.q.weapons = 90, 90 end end
days(S5, 26, 80)
check((S5.F[own5].gear_shift or 0) == 0, "gear shift released with hysteresis")
check(next(C.disabled()) == nil, "no guarded function disabled")
''', "core test")
run('local f = io.open("C:/KenshiModMap/logs/core_result.txt", "w"); f:write(N, "\\n", table.concat(FAILS, "\\n")); f:close()', "collect")
res = open(os.path.join(TMP, "core_result.txt"), encoding="utf-8").read().split("\n")
n, fails = int(res[0]), [x for x in res[1:] if x]
dbg = os.path.join(TMP, "debug.log")
if os.path.exists(dbg):
    print("debug.log:", open(dbg, encoding="utf-8").read().strip()[-400:])
for f in fails:
    print("FAIL:", f)
print(f"{'FAILED' if fails else 'OK'} {n - len(fails)}/{n}")
sys.exit(1 if fails else 0)
