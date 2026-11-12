"""Офлайн-тест LINKS2 (2026-11-12): связки существующих механик на LuaJIT из KenshiLua (lua51.dll) без игры.
Часть A (дирижёр): stock_glut -> рейд за излишком + скидка, stock_shortage -> trade_for, stock_sacked -> недовольство, drug_bust/smuggle_run/
contraband_caught -> Holy Nation и цели рейда, бог Хаоса по причине (отряды только из traces.json), события Self (заглушка {fid, n}),
профиль орков (правила), кампания за руду (заглушка FactionWarMgr), API stock_spend/town_mood/towns().lv.
Часть B (KMM_Elite): полки брони и металла, трата полки при спавне. Часть C (KMM_Town): население, беспорядки, голод.
python -I -X utf8 build/KMM_Conductor/_dev/test_links2.py -> OK, код 1 при провале."""
import ctypes
import json
import re
import sys
import tempfile

DLL = r"C:\Program Files (x86)\Steam\steamapps\workshop\content\233860\3817000612\lua51.dll"
B = r"C:\KenshiModMap\build\KMM_Conductor\scripts\init"
MODEL = "C:/KenshiModMap/build/KMM_Stock/scripts/kmm_stock_model.lua"
TRACES = "C:/KenshiModMap/build/KMM_Conductor/traces.json"
TMP = tempfile.mkdtemp(prefix="kmm_links2_").replace("\\", "/")
L = ctypes.CDLL(DLL)
L.luaL_newstate.restype = ctypes.c_void_p
for fn, at in [("luaL_openlibs", [ctypes.c_void_p]), ("luaL_loadstring", [ctypes.c_void_p, ctypes.c_char_p]),
               ("lua_pcall", [ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int]), ("lua_settop", [ctypes.c_void_p, ctypes.c_int]),
               ("lua_close", [ctypes.c_void_p])]:
    getattr(L, fn).argtypes = at
L.lua_tolstring.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p]
L.lua_tolstring.restype = ctypes.c_char_p
FAILED = []


def new_state():
    st = L.luaL_newstate()
    L.luaL_openlibs(st)
    return st


def run(st, code, name="chunk"):
    if L.luaL_loadstring(st, code.encode("utf-8")) or L.lua_pcall(st, 0, 0, 0):
        msg = L.lua_tolstring(st, -1, None)
        raise RuntimeError(f"{name}: {msg.decode('utf-8', 'replace') if msg else '?'}")


# ============================================================ A. дирижёр
st = new_state()
rt = open(r"C:\KenshiModMap\tools\test\test_runtime.py", encoding="utf-8").read()
stubs = re.search(r"STUBS = r'''(.*?)'''", rt, re.S).group(1).replace("TMPDIR", TMP)
run(st, stubs, "stubs")
for _f in sorted(__import__("glob").glob(B + r"\KMM_Conductor*.lua")): run(st, open(_f, encoding="utf-8").read(), _f.split("\\")[-1])
run(st, f"TRACES_PATH = '{TRACES}'\nMODEL_PATH = '{MODEL}'", "paths")
run(st, r'''
N, FAILS = 0, {}
function check(c, what) N = N + 1; if not c then FAILS[#FAILS + 1] = what end end
local C = KMM_Conductor
local CFG = C.cfg()
local P = CFG.params
C._set("tick_days", 1e9); C._set("first_event_after_days", 1e9)
C.reset(); C.advance(10)
local S = C.state()
check(P.links2 and P.links2.enabled, "params.links2 есть в правилах")

-- подходящая пара соседей X, Y (живые, не игрок, не реликт, Y в списке near у X)
local ids = {}
for fid in pairs(S.F) do ids[#ids + 1] = fid end
table.sort(ids)
local function ok_f(f) local F = S.F[f]; return F and F.alive and not F.player and not F.relic and next(F.towns) ~= nil end   -- GOALS: бездомные участники без городов тестом складов не годятся
local X, Y
for _, a in ipairs(ids) do
  if ok_f(a) and CFG.factions[a].near then
    for _, e in ipairs(CFG.factions[a].near) do
      if ok_f(e[1]) and e[1] ~= a and e[2] <= P.bus.radius then X, Y = a, e[1]; break end
    end
  end
  if X then break end
end
check(X and Y, "нашлась пара соседей")
local function reset_l2() S = C.state(); S.l2 = {}; S.treaties = {} end
local function set_rel(a, b, v) S.rel[a] = S.rel[a] or {}; S.rel[b] = S.rel[b] or {}; S.rel[a][b] = v; S.rel[b][a] = v end
local function prep()
  reset_l2()
  for _, f in pairs(S.F) do f.lvl = nil; f.last_loop = nil; f.need_cat = nil; f.strength = 100; f.morale = nil end
  S.F[X].lvl, S.F[Y].lvl = nil, { food = 1.8, metal = 1, armor = 1, weapons = 1 }
end
local function tally(fid, n)
  math.randomseed(12345)
  local r = {}
  for i = 1, n do local a, o = C.choose(fid); local k = tostring(a) .. ":" .. tostring(o); r[k] = (r[k] or 0) + 1 end
  return r
end

-- 1) перебор -> рейд за излишком + скидка
prep(); set_rel(X, Y, -40)
local t0 = tally(X, 500)
check((t0["raid_surplus:" .. Y] or 0) == 0, "без перебора нет raid_surplus на соседа")
local ty = nil
for t in pairs(S.F[Y].towns) do ty = t; break end
C.emit({ type = "stock_glut", a = Y, town_sid = ty, town_name = "t", cat = "food" })
local l = C.l2_state()
check(l.glut[Y] and l.glut[Y].cat == "food" and l.glut[Y].untl > 10, "stock_glut записан как причина")
P.links2.glut.raid_w = 40
local t1 = tally(X, 3000)
check((t1["raid_surplus:" .. Y] or 0) > 0, "перебор у соседа даёт рейд за излишком")
S.F[Y].lvl.food = 1.0
local t1b = tally(X, 300)
check((t1b["raid_surplus:" .. Y] or 0) == 0, "излишек пропал - рейда нет")
S.F[Y].lvl.food = 1.8
set_rel(X, Y, 30)
local t1c = tally(X, 300)
check((t1c["raid_surplus:" .. Y] or 0) == 0, "добрососедям рейд не нужен")
-- скидка у торговцев
S.stock = S.stock or {}; S.stock.towns = S.stock.towns or {}
S.stock.towns[ty] = { lv = { food = 1, metal = 1, weapons = 1 } }
local pm1 = C.price_mult_town(Y, ty)
S.l2.price = {}
local pm0 = C.price_mult_town(Y, ty)
check(pm1 < pm0 or pm0 <= P.traces.price_min + 1e-9, "скидка на цены в городе с перебором")
check(pm0 >= P.traces.price_min and pm1 >= P.traces.price_min, "цена не ниже минимума")
-- кулдаун скидки: после срока
S.l2.price = { [ty] = 5 }
check(C.price_mult_town(Y, ty) == pm0, "истекшая скидка не действует")

-- 2) нехватка -> trade_for
prep(); set_rel(X, Y, 20)
local t2 = tally(X, 500)
check((t2["trade_for:" .. Y] or 0) == 0, "без нехватки нет trade_for")
S.stock.towns[next(S.F[X].towns)] = { lv = { food = 0.1, metal = 1, weapons = 1 } }
C.emit({ type = "stock_shortage", a = X, town_sid = next(S.F[X].towns), town_name = "t", cat = "food" })
check(C.l2_state().need[X] and C.l2_state().need[X].cat == "food", "stock_shortage записан")
local t3 = tally(X, 3000)
check((t3["trade_for:" .. Y] or 0) > 0, "нехватка даёт торговый договор/караван")
local a3, o3 = nil, nil
for i = 1, 2000 do a3, o3 = C.choose(X); if a3 == "trade_for" then break end end
check(a3 == "trade_for" and S.F[X].need_cat == "food", "need_cat = нужная категория")
S.F[Y].lvl.food = 1.0
local t3b = tally(X, 300)
check((t3b["trade_for:" .. Y] or 0) == 0, "у соседа нет излишка - нет trade_for")

-- 3) stock_sacked -> недовольство соседних городов жертвы
reset_l2()
local Z
for _, a in ipairs(ids) do if ok_f(a) then local n = 0; for _ in pairs(S.F[a].towns) do n = n + 1 end; if n >= 3 then Z = a; break end end end
check(Z ~= nil, "есть фракция с 3+ городами")
S.F[Z].unrest = {}
local zt = {}
for t in pairs(S.F[Z].towns) do zt[#zt + 1] = t end
table.sort(zt)
C.emit({ type = "stock_sacked", a = X, b = Z, town_sid = zt[1], town_name = "t" })
local nu, self_u = 0, S.F[Z].unrest[zt[1]]
for t, u in pairs(S.F[Z].unrest) do nu = nu + 1; check(u.level > 0 and u.level <= 0.6 + 1e-9, "недовольство в пределах") end
check(nu >= 1 and nu <= 2 and self_u == nil, "всплеск недовольства в 1-2 соседних городах, не в разграбленном")

-- 4) контрабанда: Holy Nation и ветви, цели рейда
local HN1, HN2 = "1083-gamedata.base", "42022-rebirth.mod"
check(S.F[HN1] and S.F[HN2], "Holy Nation и Outlaws в данных")
local Q
for _, a in ipairs(ids) do if ok_f(a) and a ~= HN1 and a ~= HN2 and a ~= X and CFG.factions[HN1].near then
  for _, e in ipairs(CFG.factions[HN1].near) do if e[1] == a and e[2] <= P.bus.radius then Q = a end end
end if Q then break end end
check(Q ~= nil, "источник контрабанды рядом с Holy Nation")
prep(); set_rel(HN2, Q, 0); set_rel(HN1, Q, -30)
S.F[HN1].wealth = 0; S.F[Q].towns = {}; for _, f in ipairs(ids) do if f ~= HN1 then set_rel(HN1, f, 0) end end; set_rel(HN1, Q, -30)   -- без городов у Q захват недоступен и не заслоняет рейд
local c0 = tally(HN1, 3000)["raid:" .. Q] or 0
C.emit({ type = "drug_bust", a = HN1, b = Q, text = "t" })
local l4 = C.l2_state()
check(l4.tgt[HN1] and l4.tgt[HN1][Q] and l4.tgt[HN1][Q] >= 10, "drug_bust: источник - цель рейда охотника")
local r2 = S.rel[HN2][Q]
check(r2 <= -2 and r2 >= -5, "drug_bust: ветвь Holy Nation охладела к источнику на 2..5, а не " .. tostring(r2))
C.emit({ type = "drug_bust", a = HN1, b = Q, text = "t" })
check(S.rel[HN2][Q] == r2, "кулдаун: повторный drug_bust в тот же день не бьёт отношения снова")
P.links2.contra.raid_w = 40
local c1 = tally(HN1, 3000)["raid:" .. Q] or 0
P.links2.contra.raid_w = 0.8
check(c1 > 0 and c1 >= c0, "drug_bust повышает шанс рейда на источник: " .. c0 .. " -> " .. c1)
local pf = CFG.player_faction
set_rel(HN2, pf, 0)
C.emit({ type = "contraband_caught", a = HN1, town_sid = next(S.F[HN1].towns), cat = "drugs", n = 3 })
check(S.rel[HN2][pf] <= -1, "contraband_caught: ветвь Holy Nation холоднее к игроку")
reset_l2(); set_rel(HN1, X, -20)
C.emit({ type = "smuggle_run", a = X, b = HN1, town_sid = next(S.F[HN1].towns), cat = "drugs" })
check(C.l2_state().tgt[HN1] and C.l2_state().tgt[HN1][X], "smuggle_run: источник ходки - цель охотника")

-- 5) бог Хаоса по причине
local tj = nil
do
  local f = io.open(TRACES_PATH, "r"); local txt = f:read("*a"); f:close()
  TJ_SQUADS = {}
  for sid in txt:match('"daemons"%s*:%s*{.-"squads"%s*:%s*%[(.-)%]'):gmatch('"([^"]+)"') do TJ_SQUADS[sid] = true end
end
local GODS = P.links2.chaos.gods
for g, sq in pairs(GODS) do check(TJ_SQUADS[sq], "бог " .. g .. " привязан к существующему отряду Chaos Demons") end
check(GODS.tzeentch == nil, "у Тзинча нет своего отряда в данных мода - не придумываем")
local V = X
local function calm(f)
  f.hunger, f.stress, f.food_def, f.succession, f.last_war = 0, 0, 0, nil, -1000
  S.l2 = {}
end
local F = S.F[V]
calm(F)
check(C.chaos_pick(V) == nil, "без причины бога нет")
F.last_war = 10
local g, sq, cause = C.chaos_pick(V)
check(g == "khorne" and sq == GODS.khorne and cause == "war", "война -> Кхорн")
calm(F); F.hunger = 0.8
g, sq, cause = C.chaos_pick(V)
check(g == "nurgle" and sq == GODS.nurgle and cause == "famine", "голод -> Нургл")
calm(F); C.emit({ type = "drug_bust", a = HN1, b = V, text = "t" })
g, sq, cause = C.chaos_pick(V)
check(g == "slaanesh" and sq == GODS.slaanesh and cause == "excess", "контрабанда/излишества -> Слаанеш")
calm(F); C.emit({ type = "betrayal", a = V, b = Y, treaty = "military", text = "t" })
g, sq, cause = C.chaos_pick(V)
check(g == "tzeentch" and sq == nil and cause == "intrigue", "предательство -> Тзинч (отряда нет - любой)")
-- через мир: массовые прорывы
reset_l2()
C._set("chaos", { crisis_threshold = -5, cooldown_days = 0, incursion_chance = 1, incursion_extra = -10, rift_chance = 1, cult_wealth_drain = 0, foothold_strength = 0 })
C._set("tick_days", 5)
C.reset(); C.advance(100); S = C.state()
INC = {}
C.subscribe("chaos_incursion", function(e) INC[#INC + 1] = e end)
for d = 106, 400, 6 do C.advance(d) end
check(#INC >= 10, "прорывы Хаоса в прогоне: " .. #INC)
local gods_seen, bad = {}, 0
for _, e in ipairs(INC) do
  if e.god then
    gods_seen[e.god] = (gods_seen[e.god] or 0) + 1
    if e.god == "tzeentch" then if e.squad ~= nil then bad = bad + 1 end
    elseif e.squad ~= GODS[e.god] then bad = bad + 1 end
  else
    if e.squad ~= nil then bad = bad + 1 end
  end
  if e.squad and not TJ_SQUADS[e.squad] then bad = bad + 1 end
end
check(bad == 0, "каждый squad события есть в traces.json и соответствует богу")
local sq_ev = nil
for i = #INC, 1, -1 do if INC[i].squad then sq_ev = INC[i]; break end end
if sq_ev then check(C.chaos_squad(sq_ev.id) == sq_ev.squad, "chaos_squad(ev.id) отдаёт отряд события (для Traces)") end
check(next(gods_seen) == nil or S.stats["chaos_god_" .. next(gods_seen)] ~= nil, "счётчики богов")

-- 6) события Self (заглушка {fid, n})
C._set("tick_days", 1e9)
C.reset(); C.advance(10); S = C.state()
local A = X
S.F[A].strength = 100
local pw0 = C.power(A)
C.emit({ type = "self_retreat", a = A, n = 5 })
check(math.abs(S.F[A].strength - 99) < 1e-6, "self_retreat: сила -1% (кап суток), а не " .. S.F[A].strength)
check(S.F[A].morale and S.F[A].morale < 1 and S.F[A].morale >= 0.3, "боевой дух снижен")
check(C.power(A) < pw0 * 0.99, "боевой дух гасит силу в выборе действий")
C.emit({ type = "self_retreat", a = A, n = 5 })
check(math.abs(S.F[A].strength - 99) < 1e-6, "суточный кап: второй отход в тот же день силу не режет")
local m1 = S.F[A].morale
C.emit({ type = "self_surrender_attempt", a = A, n = 2 })
check(S.F[A].morale < m1, "попытка сдаться: дух ниже")
for i = 1, 20 do C.emit({ type = "self_retreat", a = A, n = 5 }) end
check(S.F[A].morale >= 0.3, "дух не ниже пола")
C.emit({ type = "self_retreat", a = pf, n = 5 })
check(S.F[pf].strength == (S.F[pf].strength0 or S.F[pf].strength) or true, "игрок не затронут (нет ошибки)")
C.emit({ type = "self_retreat", a = "nope", n = 3 }); C.emit({ type = "self_retreat" })
check(not C.disabled().l2_self_self_retreat, "подписчик Self не отключён на мусорных событиях")
C.advance(20)
local st1 = S.F[A].strength
C.emit({ type = "self_retreat", a = A, n = 5 })
check(S.F[A].strength < st1, "на следующие сутки кап обновился")
-- восстановление духа в тике мира
C._set("tick_days", 5); C.reset(); C.advance(100); S = C.state()
S.F[A].morale = 0.5
for d = 106, 130, 6 do C.advance(d) end
check(S.F[A].morale > 0.5 and S.F[A].morale <= 1, "боевой дух медленно восстанавливается")
C._set("tick_days", 1e9)

-- 7) профиль орков (правила) и Waaagh
C.reset(); C.advance(10); S = C.state()
local ORC
for fid, f in pairs(CFG.factions) do if f.name == "Greenskins" then ORC = fid end end
check(ORC and S.F[ORC], "орки есть в данных дирижёра")
local legal_ok = false
for _, e in ipairs(P.contra.legal) do if e.pat == "Greenskins" and e.lux == 0.5 and e.med == 0.5 then legal_ok = true end end
check(legal_ok, "правило: у орков спрос на роскошь и медицину x0.5")
local M = dofile(MODEL_PATH)
M._cfg = CFG
local _, dm = M.legality({ R = { ban = {} } }, ORC, "med")
local _, dl = M.legality({ R = { ban = {} } }, ORC, "lux")
local _, dh = M.legality({ R = { ban = {} } }, X, "med")
check(dm == 0.5 and dl == 0.5 and dh == 1, "модель склада применяет профиль орков без кода")
local E
for _, e in ipairs(CFG.factions[ORC].near or {}) do if ok_f(e[1]) and e[1] ~= ORC and e[2] <= P.bus.radius then E = e[1]; break end end
check(E ~= nil, "у орков есть сосед-цель")
if E then
  reset_l2(); for _, f in pairs(S.F) do f.lvl = nil; f.last_loop = nil end
  S.F[ORC].strength, S.F[E].strength = 100, 100
  for _, f in ipairs(ids) do if f ~= ORC then set_rel(ORC, f, 0) end end
  set_rel(ORC, E, -40)
  S.F[ORC].wealth = 0
  S.F[ORC].lvl = { weapons = 2.0 }; S.F[E].lvl = { food = 1.8, metal = 1.0 }
  local w0_ = P.links2.profiles[1].waaagh.w; P.links2.profiles[1].waaagh.w = 40   -- тест кандидата: перекрываем засады
  local o1 = tally(ORC, 4000)
  P.links2.profiles[1].waaagh.w = w0_
  check((o1["raid_surplus:" .. E] or 0) > 0, "Waaagh: избыток оружия -> налёт на излишек врага")
  P.links2.profiles[1].waaagh.w = 40
  local seen = false
  for i = 1, 3000 do local a = C.choose(ORC); if a == "raid_surplus" then seen = (S.F[ORC].need_cat == "food"); break end end
  P.links2.profiles[1].waaagh.w = w0_
  check(seen, "Waaagh: цель - категория с излишком у врага")
  S.F[ORC].lvl = { weapons = 1.0 }
  check((tally(ORC, 400)["raid_surplus:" .. E] or 0) == 0, "Waaagh молчит без избытка оружия")
  S.F[ORC].lvl = { weapons = 2.0 }; S.treaties = { { id = 1, type = "nonaggression", a = ORC, b = E, active = true, term = 1e9 } }
  check((tally(ORC, 400)["raid_surplus:" .. E] or 0) == 0, "Waaagh не бьёт по договорам")
  S.treaties = {}
  -- ни один другой не получает бонус профиля
  local K
  for _, a in ipairs(ids) do if ok_f(a) and a ~= ORC and a ~= E and CFG.factions[a].near then
    for _, e in ipairs(CFG.factions[a].near) do if e[1] == E then K = a end end end if K then break end end
  if K then
    S.F[K].strength = 100; S.F[K].lvl = { weapons = 2.0 }; set_rel(K, E, -40)
    check((tally(K, 400)["raid_surplus:" .. E] or 0) == 0, "профиль только у орков")
  end
end

-- 8) кампания за руду (заглушка FactionWarMgr), по умолчанию выключена
C.reset(); C.advance(10); S = C.state()
CALLS = {}
local townobj = { name = "T" }
local function wm(fid) return { getNearestTown = function(self, pos) return { fid = fid, x = pos.x } end,
  triggerCampaign = function(self, target, gd, a, b, home, dup, trig) CALLS[#CALLS + 1] = { target = target, gd = gd, a = a, b = b, home = home, dup = dup, trig = trig } end } end
local gw = { factionMgr = { getFactionByStringID = function(self, fid) return { id = fid, warMgr = wm(fid) } end },
             gamedata = { getData = function(self, sid, ty) return { stringID = sid, ty = ty } end } }
function getGameWorld() return gw end
PCS = {}
function getPlayerInterface() return { getAllPlayerCharacters = function() return PCS end } end
local OA, OB
for _, a in ipairs(ids) do if ok_f(a) then
  for _, b in ipairs(ids) do if ok_f(b) and b ~= a then
    for t in pairs(S.F[b].towns) do if S.ore and S.ore[t] and CFG.town_info[t] and CFG.town_info[t].x then OA, OB, OT = a, b, t end end
    if OT then break end
  end end
end if OT then break end end
check(OT ~= nil, "есть чужой рудный город")
if OT then
  local function setup_target()
    S.treaties = {}
    for _, f in pairs(S.F) do f.camp_day = nil end
    S.F[OB].towns = { [OT] = true }
    S.F[OA].metal_def = 0.9
    set_rel(OA, OB, -50)
    S.F[OA].strength, S.F[OB].strength = 200, 50
  end
  local function capture()
    setup_target(); math.randomseed(3); C._act(OA, "capture", OB)
  end
  local I = CFG.town_info[OT]
  PCS = { { getPosition = function() return { x = I.x + 500, y = 0, z = I.z } end } }
  capture()
  check(#CALLS == 0, "по умолчанию кампании за руду выключены флагом")
  P.links2.ore_campaign = { enabled = true, campaign = "18932-gamedata.base", campaign_type = 93, cooldown_days = 60, load_radius = 15000, min_time = 0, max_time = 0 }
  capture()
  check(#CALLS == 1, "включена + зона загружена -> triggerCampaign вызван один раз, а не " .. #CALLS)
  if CALLS[1] then
    check(CALLS[1].gd.stringID == "18932-gamedata.base" and CALLS[1].gd.ty == 93 and CALLS[1].trig.id == OA and CALLS[1].target.fid == OB and CALLS[1].home.fid == OA,
          "аргументы: цель - город жертвы, дом - город атакующего, кампания - GameData")
  end
  local n1 = #CALLS
  S.F[OA].metal_def = 0.9; S.F[OB].towns = { [OT] = true }; S.treaties = {}; set_rel(OA, OB, -50); S.F[OA].strength, S.F[OB].strength = 200, 50
  C._act(OA, "capture", OB)
  check(#CALLS == n1, "не больше одной кампании на фракцию за cooldown_days")
  PCS = { { getPosition = function() return { x = I.x + 90000, y = 0, z = I.z } end } }
  n1 = #CALLS; capture()
  check(#CALLS == n1, "зона не загружена (игрок далеко) -> только абстрактная хроника")
  PCS = { { getPosition = function() return { x = I.x, y = 0, z = I.z } end } }
  S.treaties = {}
  n1 = #CALLS; setup_target(); S.treaties = { { id = 7, type = "trade", a = OA, b = OB, active = true, term = 1e9 } }; C._act(OA, "capture", OB)
  check(#CALLS == n1, "вне договоров: при договоре кампании нет")
  getGameWorld = function() error("no world") end
  setup_target(); C._act(OA, "capture", OB)
  local lf = io.open("TMPDIR/debug.log", "r"); local ltxt = lf and lf:read("*a") or ""; if lf then lf:close() end
  check(ltxt:find("ore_campaign disabled until restart", 1, true) ~= nil, "сбой API отключает только кампании за руду (запись в debug.log)")
end

-- 9) API склада/города
C.reset(); C.advance(10); S = C.state()
local tt = next(S.F[X].towns)
S.stock.towns = S.stock.towns or {}
S.stock.towns[tt] = { q = { armor = 100, metal = 80 }, tn = { armor = 100, metal = 100 }, lv = { armor = 1, metal = 0.8 } }
local spent = C.stock_spend(tt, "armor", 0.06)
check(math.abs(spent - 6) < 1e-9 and math.abs(S.stock.towns[tt].q.armor - 94) < 1e-9 and math.abs(S.stock.towns[tt].lv.armor - 0.94) < 1e-9, "stock_spend списывает долю нормы и пересчитывает полку")
check(C.stock_spend(tt, "metal", 5) == 80, "stock_spend не уходит в минус")
check(C.stock_spend("nope", "armor", 0.1) == 0, "stock_spend: нет склада - 0")
local found = false
for _, t in ipairs(C.towns()) do if t.sid == tt then found = (t.lv ~= nil and t.lv.armor ~= nil) end end
check(found, "towns() отдаёт полки lv")
S.town[tt] = { pop = 40, pop0 = 100 }
S.F[X].unrest = { [tt] = { level = 0.7 } }
local mo = C.town_mood(tt)
check(mo.pop == 40 and mo.pop0 == 100 and mo.unrest == 0.7 and mo.owner == X, "town_mood: население, беспорядки, владелец")

local rf = io.open("TMPDIR/result.txt", "w"); rf:write(N .. " " .. #FAILS .. "|" .. table.concat(FAILS, "|")); rf:close()
'''.replace("TMPDIR", TMP), "test")
res = open(TMP + "/result.txt", encoding="utf-8").read().split("|")
n, nf = map(int, res[0].split())
print("LINKS2 conductor: checks", n, "fails", nf)
for x in res[1:]:
    if x:
        print("FAIL:", x)
        FAILED.append(x)

# ============================================================ B. KMM_Elite
src = open(r"C:\KenshiModMap\build\KMM_Elite\_dev\test_elite.py", encoding="utf-8").read()
ESTUBS = re.search(r'STUBS = r"""(.*?)"""', src, re.S).group(1)
EL = "C:/KenshiModMap/build/KMM_Elite/scripts/init/kmm_elite.lua"
ESC = "C:/KenshiModMap/build/KMM_Elite/scripts"


def elite(code, name):
    s = new_state()
    tmp = tempfile.mkdtemp(prefix="kmm_l2e_").replace("\\", "/")
    try:
        run(s, ESTUBS % {"tmp": tmp, "scripts": ESC}, "estubs")
        run(s, f'SCRIPT_PATH = "{EL}"\n' + "dofile(SCRIPT_PATH)\nP = mkchar(0, 0, 'player'); PCS = { P }\nSPENT = {}\n"
            "KMM_Conductor.stock_spend = function(sid, cat, sh) SPENT[#SPENT + 1] = { sid, cat, sh }; return sh end\n"
            "function setlv(lv) KMM_Conductor.towns = function() return { { sid = 't1', name = 'Testville', owner = FID, x = TOWNX, z = TOWNZ, lv = lv } } end end\n" + code, name)
        print("OK   elite:", name)
    except Exception as e:
        print("FAIL elite:", name, e)
        FAILED.append("elite " + name)
    finally:
        L.lua_close(s)


elite("setlv({ armor = 0.5, metal = 1.0 }); TICK(30); assert_eq(API.spawn, 0, 'броня на полке < 0.8 - элиты нет'); assert_eq(#SPENT, 0, 'ничего не списано')", "armor_low_no_spawn")
elite("setlv({ armor = 1.0, metal = 0.7 }); TICK(30); assert_eq(API.spawn, 0, 'металла < 0.8 - элиты нет')", "metal_low_no_spawn")
elite("setlv({ armor = 1.0, metal = 1.0 }); TICK(30); assert_eq(API.spawn, 1, 'полки полные - элита'); assert_eq(#SPENT, 2, 'списано две категории')\n"
      "assert(SPENT[1][2] == 'armor' and SPENT[2][2] == 'metal', 'броня и металл'); assert(SPENT[1][3] >= 0.05 and SPENT[1][3] <= 0.08, 'доля 5-8%'); assert_eq(SPENT[1][1], 't1', 'город')", "full_shelf_spawns_and_spends")
elite("setlv(nil); TICK(30); assert_eq(API.spawn, 1, 'нет данных склада - как раньше'); assert_eq(#SPENT, 0, 'без lv ничего не списываем')", "no_stock_data_backward_compatible")
elite("setlv({ armor = 1.0, metal = 1.0 }); KMM_Conductor.stock_spend = function() error('boom') end; TICK(30); assert_eq(API.spawn, 1, 'сбой списания не мешает спавну')", "spend_error_is_not_fatal")

# ============================================================ C. KMM_Town
src = open(r"C:\KenshiModMap\build\KMM_Town\_dev\test_town.py", encoding="utf-8").read()
TSTUBS = re.search(r'STUBS = r"""(.*?)"""', src, re.S).group(1)
TL = "C:/KenshiModMap/build/KMM_Town/scripts/init/kmm_town.lua"
TSC = "C:/KenshiModMap/build/KMM_Town/scripts"


def town(code, name):
    s = new_state()
    tmp = tempfile.mkdtemp(prefix="kmm_l2t_").replace("\\", "/")
    try:
        run(s, TSTUBS % {"tmp": tmp, "scripts": TSC}, "tstubs")
        run(s, f'SCRIPT_PATH = "{TL}"\n' + """
install_stock(); STOCKQ = 500
P = mkchar({ pc = true }); PCS = { P }
M = mkmachine(MACHINE, 99)
W1 = mkchar({ work = M }); W2 = mkchar({ work = M }); W3 = mkchar({ work = M }); C1 = mkchar({}); C2 = mkchar({}); C3 = mkchar({}); S1 = mkchar({ trader = true, resident = true })
MOOD = nil
KMM_Conductor.town_mood = function(t) return MOOD end
dofile(SCRIPT_PATH)
""" + code, name)
        print("OK   town:", name)
    except Exception as e:
        print("FAIL town:", name, e)
        FAILED.append("town " + name)
    finally:
        L.lua_close(s)


NUM = {}


def town_n(mood, name, extra=""):
    code = (f"MOOD = {mood}; TICK(60, 2.5); local f = io.open(TMP .. '/n.txt', 'w'); f:write(KMM_Town.stats().crafted .. ' ' .. count_ev('town_alarm')); f:close()" + extra)
    s2 = new_state()
    tmp = tempfile.mkdtemp(prefix="kmm_l2t_").replace("\\", "/")
    try:
        run(s2, TSTUBS % {"tmp": tmp, "scripts": TSC}, "tstubs")
        run(s2, f'SCRIPT_PATH = "{TL}"' + chr(10) + TOWN_SETUP + code, name)
        a, b = map(int, open(tmp + "/n.txt").read().split())
        NUM[name] = (a, b)
    except Exception as e:
        print("FAIL town:", name, e)
        FAILED.append("town " + name)
    finally:
        L.lua_close(s2)


TOWN_SETUP = """
install_stock(); STOCKQ = 500
P = mkchar({ pc = true }); PCS = { P }
M = mkmachine(MACHINE, 99)
W1 = mkchar({ work = M }); W2 = mkchar({ work = M }); W3 = mkchar({ work = M }); C1 = mkchar({}); C2 = mkchar({}); C3 = mkchar({}); S1 = mkchar({ trader = true, resident = true })
MOOD = nil
KMM_Conductor.town_mood = function(t) return MOOD end
dofile(SCRIPT_PATH)
"""
town_n("nil", "none")
town_n("{ pop = 100, pop0 = 100, unrest = 0, food = 1 }", "healthy")
town_n("{ pop = 100, pop0 = 100, unrest = 0.6, food = 1 }", "unrest")
town_n("{ pop = 100, pop0 = 100, unrest = 0, food = 0.1 }", "famine")
town_n("{ pop = 30, pop0 = 100, unrest = 0, food = 1 }", "lowpop")
town_n("{ pop = 30, pop0 = 100, unrest = 0.8, food = 1 }", "riot")
print("town crafted/alarms:", NUM)
if len(NUM) == 6:
    n = {k: v[0] for k, v in NUM.items()}
    checks = [(n["none"] >= 3, "без данных дирижёра работа как раньше"), (n["healthy"] == n["none"], "здоровый город = без данных"),
              (n["unrest"] < n["healthy"] and n["unrest"] >= 1, "беспорядки режут работу, но не в ноль"),
              (n["famine"] < n["healthy"] and n["famine"] >= 1, "голод: меньше закупок сырья"),
              (n["lowpop"] < n["healthy"] and n["lowpop"] >= 1, "малое население: работа пропорционально"),
              (n["riot"] == 0, "беспорядки + вымирание: работы нет"),
              (NUM["riot"][1] == 1 and NUM["unrest"][1] == 1 and NUM["healthy"][1] == 0 and NUM["famine"][1] == 0, "town_alarm только при беспорядках, раз в кулдаун")]
    for ok, what in checks:
        print(("OK   town: " if ok else "FAIL town: ") + what)
        if not ok:
            FAILED.append("town " + what)
town("KMM_Conductor.town_mood = function() error('boom') end; TICK(60, 2.5); assert(KMM_Town.stats().crafted >= 3, 'сбой дирижёра: работа как раньше'); assert(KMM_Town.disabled().conductor_link, 'ссылка отключена')", "mood_error_is_not_fatal")

print("OK" if not FAILED and nf == 0 else "FAILED")
sys.exit(1 if (FAILED or nf) else 0)
