"""Offline test FAMINE (голод города -> беженцы); основа test_roads: цели и перенос чисел, деспавн, предвестники до рейда, гонцы/дань, сетка игрока с затуханием и выбор засады, всё вне видимости,
нет точки -> отложить. python -I -X utf8 build/KMM_Conductor/_dev/test_roads.py -> OK."""
import ctypes
import os
import re
import tempfile

DLL = r"C:\Program Files (x86)\Steam\steamapps\workshop\content\233860\3817000612\lua51.dll"
B = r"C:\KenshiModMap\build\KMM_Conductor\scripts\init"
TMP = tempfile.mkdtemp(prefix="kmm_famine_").replace("\\", "/")
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
run("math.randomseed(20261113)", "seed")
for _f in sorted(__import__("glob").glob(B + r"\KMM_Conductor*.lua")): run(open(_f, encoding="utf-8").read(), _f.split("\\")[-1])
run(open(B + r"\KMM_Traces.lua", encoding="utf-8").read(), "KMM_Traces.lua")
run(r'''
N, FAILS = 0, {}
local function MAIN()
function check(c, what) N = N + 1; if not c then FAILS[#FAILS + 1] = what; print("FAIL " .. what) end end
local C = KMM_Conductor
local function skeys(t) local k = {}; for x in pairs(t) do k[#k + 1] = x end; table.sort(k); return k end
C.reset()
local CFGP = C.cfg().params
CFGP.traces.first_hour_traces = 0; CFGP.traces.arrive_enabled = false; CFGP.ws_slice = 1e9; CFGP.rng_fixed = true
local FP = CFGP.famine
check(FP and FP.enabled and FP.below and FP.days and FP.cooldown and FP.max_groups, "params.famine с дефолтами в коде")
FP.chance = 1
C.advance(10); C.advance(16)
local S = C.state()
local function stock_all(food_lv)
  S.stock.towns = {}
  for sid in pairs(C.cfg().town_info) do
    local s = { q = {}, tn = {}, lv = {} }
    for _, c in ipairs({ "food", "metal", "weapons", "armor", "med", "drugs", "lux", "scrap" }) do s.q[c] = 100 * food_lv; s.tn[c] = 100; s.lv[c] = food_lv end
    S.stock.towns[sid] = s
  end
end
local function famine_events() local r = {}; for _, e in ipairs(S.events) do if e.type == "famine_refugees" then r[#r + 1] = e end end; return r end
-- хозяин X с городом и сытый свой город Y
local X, A, Y
for _, fid in ipairs(skeys(S.F)) do
  local f = S.F[fid]
  if f.alive and not f.player and not f.relic and not X then
    local ts = {}
    for _, t in ipairs(skeys(f.towns)) do local I = C.cfg().town_info[t]; if I and I.x then ts[#ts + 1] = t end end
    if #ts >= 2 then A, X, Y = fid, ts[1], ts[2] end
  end
end
check(X and Y, "найдены два города одной фракции")
-- 1) сытый мир: беженцев нет
stock_all(1.5)
local base = #famine_events()
for i = 1, 6 do C.advance(S.last_day + 5) end
check(#famine_events() == base, "сытый мир: беженцев от голода нет")
-- 2) X голодает, Y сыт: через несколько дней беженцы из X в Y (или другой сытый свой/дружественный город)
S.stock.towns[X].lv.food = 0.1
S.town[X].pop = math.max(S.town[X].pop, S.town[X].pop0)
local pop0 = S.town[X].pop
C.advance(S.last_day + 5)
check(#famine_events() == base, "первый тик дефицита: ещё рано (нужно несколько дней подряд)")
for i = 1, 3 do S.stock.towns[X].lv.food = 0.1; C.advance(S.last_day + 5) end
local evs = famine_events()
check(#evs == base + 1, "голодный город: поставлена одна группа беженцев (" .. (#evs - base) .. ")")
local e = evs[#evs]
check(e and e.a == A and e.town_sid == X, "фракция-владелец и источник верны")
local dest = e and e.to
check(dest and dest ~= X and S.F[A].towns[dest] or (dest and (S.rel[A] and (S.rel[A][S.F[A] and dest] or 0) >= 0)), "цель - свой/дружественный город")
check(dest and (S.stock.towns[dest].lv.food or 0) >= 0.8, "цель - сытый город")
check(S.town[X].pop < pop0, "население источника списано сразу")
local rs = C.road_state(); local found
for id, r in pairs(rs.tr) do if r.k == "refugees" and r.from == X and r.to == dest then found = r end end
check(found ~= nil, "ROADS-запись беженцев есть (Traces заберёт через road_claim)")
check(e and e.text and e.text:find("Hunger"), "текст хроники понятен")
-- 3) кулдаун: дефицит продолжается, новых групп из X нет
local n1 = #famine_events()
local d_ev = e.day
while S.last_day - d_ev < 20 do S.stock.towns[X].lv.food = 0.1; C.advance(S.last_day + 5) end
local fromX = 0; for _, ev in ipairs(famine_events()) do if ev.town_sid == X then fromX = fromX + 1 end end
check(fromX == 1, "кулдаун: из X только одна группа за 20 дней после первой (" .. fromX .. ")")
-- 4) после кулдауна группа возможна снова
while S.last_day - d_ev < 45 do S.stock.towns[X].lv.food = 0.1; S.town[X].pop = S.town[X].pop0; C.advance(S.last_day + 5) end
fromX = 0; for _, ev in ipairs(famine_events()) do if ev.town_sid == X then fromX = fromX + 1 end end
check(fromX == 2, "после кулдауна возможна вторая группа (" .. fromX .. ")")
-- 5) отключение флагом и старый сейв без S.famine
S.famine = nil; FP.enabled = false
for i = 1, 6 do S.stock.towns[X].lv.food = 0.1; C.advance(S.last_day + 5) end
check(S.famine == nil, "enabled=false: подсистема молчит, состояния не создаёт")
FP.enabled = true
C.advance(S.last_day + 5)
check(type(S.famine) == "table", "старый сейв без S.famine: состояние создаётся лениво")
print("FAMINE_RESULT " .. N .. " checks, " .. #FAILS .. " fails")
end
local ok, err = xpcall(MAIN, debug.traceback)
if not ok then print("TESTERROR " .. tostring(err)); FAILS[#FAILS + 1] = "error" end
if #FAILS > 0 then error("FAILS " .. #FAILS) end
''', "test")
print("OK")
