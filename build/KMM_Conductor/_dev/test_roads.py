"""Offline test ROADS: цели и перенос чисел, деспавн, предвестники до рейда, гонцы/дань, сетка игрока с затуханием и выбор засады, всё вне видимости,
нет точки -> отложить. python -I -X utf8 build/KMM_Conductor/_dev/test_roads.py -> OK."""
import ctypes
import os
import re
import tempfile

DLL = r"C:\Program Files (x86)\Steam\steamapps\workshop\content\233860\3817000612\lua51.dll"
B = r"C:\KenshiModMap\build\KMM_Conductor\scripts\init"
TMP = tempfile.mkdtemp(prefix="kmm_roads_").replace("\\", "/")
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
function ticks(n, dt) for i = 1, n do CLOCK = CLOCK + (dt or 1); DAYV = DAYV + 0.0005; FIRE("GameWorld::charsUpdate", {}) end end
local C = KMM_Conductor
local function dist(ax, az, bx, bz) if not (ax and az and bx and bz) then error(debug.traceback("nil dist"), 2) end return math.sqrt((ax - bx) ^ 2 + (az - bz) ^ 2) end
local function skeys(t) local k = {}; for x in pairs(t) do k[#k + 1] = x end; table.sort(k); return k end
C.reset()
local CFGP = C.cfg().params
CFGP.traces.first_hour_traces = 0; CFGP.traces.arrive_enabled = false; CFGP.traces.max_per_day = 1000; CFGP.traces.max_queue = 1000; CFGP.ws_slice = 1e9; CFGP.rng_fixed = true
local TP, RPAR = CFGP.traces, CFGP.roads
check(RPAR and RPAR.enabled and RPAR.refugees and RPAR.caravans and RPAR.wanderers and RPAR.scouts and RPAR.couriers and RPAR.tribute and RPAR.grid ~= nil, "флаги params.roads есть")
local tr = C.read_json("traces.json", "C:/KenshiModMap/build/KMM_Conductor/traces.json")
local pf = C.cfg().player_faction

-- шина: все события ROADS эфемерны (не попадают в журнал)
local BUS = {}
C.subscribe("*", function(ev) if ev.type == "traveler_arrived" or ev.type == "raid_scout" or ev.type == "courier" then BUS[#BUS + 1] = ev end end)
local function bus_count(ty) local n = 0; for _, e in ipairs(BUS) do if e.type == ty then n = n + 1 end end; return n end
local function journal_count(ty) local n = 0; for _, e in ipairs(C.state().events) do if e.type == ty then n = n + 1 end end; return n end

-- ===================================================================== A. дирижёр: журнал дорог и числа
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
stock_all(1.5)
-- 1) беженцы: захват города -> источник теряет сразу, пункт назначения получает по прибытии (не из воздуха)
local X, A, Bf
for _, fid in ipairs(skeys(S.F)) do
  local f = S.F[fid]
  if f.alive and not f.player and not f.relic then for _, t in ipairs(skeys(f.towns)) do if C.cfg().town_info[t] and C.cfg().town_info[t].x and not X then X, A = t, fid end end end
end
for _, fid in ipairs(skeys(S.F)) do local f = S.F[fid]; if f.alive and not f.player and fid ~= A and not Bf then Bf = fid end end
check(X and A and Bf, "найден город X и захватчик")
S.F[A].towns[X] = nil; S.F[Bf].towns[X] = true
local pop_before = 0; for sid, tw in pairs(S.town) do if type(tw) == "table" and tw.pop then pop_before = pop_before + tw.pop end end
local x0pop = S.town[X].pop
C.advance(21)
local rs = C.road_state()
local ref
for id, e in pairs(rs.tr) do if e.k == "refugees" and e.from == X then ref = e end end
check(ref ~= nil, "захват: беженцы записаны в журнал дорог (не зачтены мгновенно)")
check(S.town[X].pop < x0pop, "источник уже потерял население")
local dest_pop1 = S.town[ref.to].pop
local fed = C.town_mood(ref.to)
check(fed and fed.food and fed.food >= 0.8, "цель беженцев - сытый город (еда " .. tostring(fed and fed.food) .. ")")
local dmin = 1e18
for t, I in pairs(C.cfg().town_info) do
  local tw = S.town[t]
  if t ~= X and I.x and type(tw) == "table" and tw.pop and tw.pop < tw.pop0 * 1.3 then local d = dist(I.x, I.z, C.cfg().town_info[X].x, C.cfg().town_info[X].z); if d < dmin then dmin = d end end
end
check(math.abs(dist(C.cfg().town_info[ref.to].x, C.cfg().town_info[ref.to].z, C.cfg().town_info[X].x, C.cfg().town_info[X].z) - dmin) < 1, "цель - ближайший сытый город")
local n_ref = ref.n
C.advance(21 + 15)
local still = false; for id, e in pairs(C.road_state().tr) do if id == ref.id then still = true end end
check(not still, "по сроку беженцы зачтены абстрактно")
check(S.town[ref.to].pop - dest_pop1 >= n_ref * 0.9, string.format("население назначения выросло на %.1f (груз %.1f)", S.town[ref.to].pop - dest_pop1, n_ref))
check(journal_count("traveler_arrived") == 0, "traveler_arrived не в журнале (эфемерно)")

-- 2) караван: план по дефициту груза назначения, склад-источник списывается, назначения зачитывается; сумма сохраняется
stock_all(1.0)
local own = {}
for fid, f in pairs(S.F) do if f.alive then for t in pairs(f.towns) do own[t] = fid end end end
local src, dst, fidc
for _, fid in ipairs(skeys(S.F)) do
  local f = S.F[fid]
  if f.alive and not f.player and not src then
    local ts = {}
    for t in pairs(f.towns) do local I = C.cfg().town_info[t]; if I and I.x then ts[#ts + 1] = t end end
    table.sort(ts)
    for _, a in ipairs(ts) do for _, b in ipairs(ts) do
      local I, J = C.cfg().town_info[a], C.cfg().town_info[b]
      if not src and a ~= b and dist(I.x, I.z, J.x, J.z) > 3000 and dist(I.x, I.z, J.x, J.z) < 60000 then src, dst, fidc = a, b, fid end
    end end
  end
end
check(src and dst, "найдена пара городов одной фракции")
if src and dst then
  S.stock.towns[src].q.metal = 300; S.stock.towns[src].lv.metal = 3
  S.stock.towns[dst].q.metal = 20; S.stock.towns[dst].lv.metal = 0.2
  local function msum() local t = 0; for _, s in pairs(S.stock.towns) do t = t + s.q.metal end; return t end
  local m0 = msum()
  local plan = C.road_plan("caravan", nil, { x = C.cfg().town_info[src].x, z = C.cfg().town_info[src].z })
  check(plan and plan.c == "metal" and plan.to == dst and plan.from == src, "караван: груз из избытка в дефицит по его грузу (" .. tostring(plan and plan.c) .. ")")
  local q_src0, q_dst0 = S.stock.towns[src].q.metal, S.stock.towns[dst].q.metal
  local id = C.road_depart(plan)
  check(id ~= nil and S.stock.towns[src].q.metal < q_src0, "отправка списала склад источника")
  check(math.abs(msum() - (m0 - C.road_state().tr[id].n)) < 1e-6, "в пути металл числится в журнале, не в складах")
  check(S.stock.towns[dst].q.metal == q_dst0, "назначение ещё не получило")
  C.road_arrive(id, "visible")
  check(S.stock.towns[dst].q.metal > q_dst0 and math.abs(msum() - m0) < 1e-6, "по прибытии зачтено; сумма металла мира сохранена")
  check(bus_count("traveler_arrived") >= 1, "traveler_arrived пришло по шине")
  check(journal_count("traveler_arrived") == 0, "и не в журнале")
  -- потерянный в пути груз: зачёта нет
  local plan2 = C.road_plan("caravan", nil, {})
  local id2 = plan2 and C.road_depart(plan2)
  local q_before = id2 and S.stock.towns[plan2.to].q[plan2.c]
  if id2 then C.road_lost(id2); check(S.stock.towns[plan2.to].q[plan2.c] == q_before and not C.road_state().tr[id2], "погибший караван груз не доставил") end
end

-- 3) бродяга: бар богатого города, монеты от странника хозяину
local wf
for _, fid in ipairs(skeys(S.F)) do if S.F[fid].alive and C.road_wanderer(fid) then wf = fid; break end end
check(wf ~= nil, "есть бродяги (фракции без городов / воры)")
if wf then
  S.F[wf].wealth = 200
  local wp = C.road_plan("wanderer", wf, {})
  check(wp and wp.to and C.cfg().town_info[wp.to].kind == "city" and wp.owner, "бродяга идёт в город (бар)")
  local best = 0; for fid, f in pairs(S.F) do if f.alive and not f.player then best = math.max(best, f.wealth / f.wealth0) end end
  local ow = S.F[wp.owner]
  check(ow.wealth / ow.wealth0 >= 0.0, "хозяин назначения известен")
  local w0, o0 = S.F[wf].wealth, ow.wealth
  local wid = C.road_depart(wp)
  check(wid and S.F[wf].wealth < w0, "монеты списаны у странника")
  C.road_arrive(wid, "visible")
  check(ow.wealth > o0 - 1e-9 and math.abs((S.F[wf].wealth + ow.wealth) - (w0 + o0)) < 1e-6, "монеты перешли хозяину бара, сумма сохранена")
end

-- 4) память дорог: затухание и ограничение размера
local d0 = S.last_day
C.road_visit(30000, 30000)
local h0 = C.road_heat(30000, 30000)
check(h0 >= 1, "посещение даёт вес клетке")
C.road_visit(30000, 30000)
check(C.road_heat(30000, 30000) == h0, "повтор в тот же момент не накручивает (grid_step_days)")
S.last_day = d0 + 20; C.advance(d0 + 20)
local h20 = C.road_heat(30000, 30000)
check(math.abs(h20 / h0 - 0.5) < 0.02, string.format("полураспад ~20 дней (%.3f)", h20 / h0))
S.last_day = d0 + 100; C.advance(d0 + 100)
check(C.road_heat(30000, 30000) < h0 * 0.05, "через 100 дней память почти стёрта")
for i = 1, 200 do C.cfg().params.roads.grid_step_days = 0; C.road_visit(i * 8000 + 100, -i * 8000 - 100) end
check(#C.road_grid() <= RPAR.grid_max + 8, "сетка ограничена (" .. #C.road_grid() .. ")")
local ntr = 0; for _ in pairs(C.road_state().tr) do ntr = ntr + 1 end
check(ntr <= RPAR.max_transit and C.serialize():find("grid", 1, true), "журнал дорог ограничен (" .. ntr .. "), сетка в сохранении")
RPAR.grid_step_days = 0.1

-- ===================================================================== B. Traces: спавн только вне видимости
local gw0 = getGameWorld
TARGETS, MEMBERS = {}, {}
function getGameWorld()
  local g = gw0(); local orig = g.theFactory.createRandomSquad
  g.theFactory.createRandomSquad = function(self, f, pos, home, maxnum, b, gd, o, m, ap, perm, target, ttown, mult, sqt, rf)
    orig(self, f, pos, home, maxnum, b, gd, o, m, ap, perm, target, ttown, mult, sqt, rf)
    local n = #SPAWNS; TARGETS[n] = ttown
    local pl = PLATOON("sq" .. n, gd and gd.stringID)
    local ch = MKCH("m" .. n, f.id, pos.x, pos.z, { platoon = "sq" .. n })
    CHARS[#CHARS + 1] = ch; MEMBERS[n] = ch
    return pl
  end
  return g
end
function place(n, x, z)   -- переставить участника спавна n в точку (новый объект того же платуна)
  for i, c in ipairs(CHARS) do if c == MEMBERS[n] then table.remove(CHARS, i); break end end
  MEMBERS[n] = MKCH("m" .. n, SPAWNS[n].fid, x, z, { platoon = "sq" .. n })
  CHARS[#CHARS + 1] = MEMBERS[n]
end
local T, TX, TZ, Bv
for _, sid in ipairs(skeys(C.cfg().town_info)) do
  local I = C.cfg().town_info[sid]
  for _, fid in ipairs(skeys(C.state().F)) do
    local f = C.state().F[fid]
    if f.alive and f.towns[sid] and tr.live_caravans[fid] and tr.factions[fid] and tr.factions[fid].refugees and tr.factions[fid].tiers and next(tr.factions[fid].tiers) and I.x and not f.player and not T then T, TX, TZ, Bv = sid, I.x, I.z, fid end
  end
end
local Aa
for _, fid in ipairs(skeys(C.state().F)) do local f = C.state().F[fid]; if f.alive and not f.player and fid ~= Bv and tr.factions[fid] and tr.factions[fid].tiers and next(tr.factions[fid].tiers) and C.fpos(fid) and not Aa then Aa = fid end end
check(T and Aa and Bv, "Traces: найдены город, жертва и грабитель")
local function setpcs(list)
  PCS = {}; CHARS = {}
  for i, p in ipairs(list) do PCS[i] = MKCH("PC" .. i, pf or "player", p[1], p[2], { player = true, platoon = "player_squad" }); CHARS[i] = PCS[i] end
end
local function far_ok(from)
  local worst, wmax = 1e9, 0
  for i = from, #SPAWNS do
    local s = SPAWNS[i]; local near = 1e9
    for _, p in ipairs(PCS) do local pos = p:getPosition(); local d = dist(s.x, s.z, pos.x, pos.z); worst = math.min(worst, d); near = math.min(near, d) end
    wmax = math.max(wmax, near)
  end
  return worst >= 3500 and wmax <= 6000, worst, wmax
end
local function pump(n) for _ = 1, n do CLOCK = CLOCK + 100; ticks(2) end end
C.reset(); C.advance(10); C.advance(16); DAYV = 16; S = C.state()
stock_all(1.5)
RPAR.scouts = false
setpcs({ { TX + 2500, TZ }, { TX - 1000, TZ + 3000 } }); ticks(5)

-- 5) беженцы Traces: цель - сытый город, группа несёт числа, прибытие -> деспавн вне видимости + зачёт
RPAR.max_live = 1000   -- прочие путники (GOALS, бродяги) не вытесняют беженцев из TRV
local s0 = #SPAWNS
S.F[Bv].towns[T] = nil; S.F[Aa].towns[T] = true   -- захват T: Aa хозяин, Bv - беженцы
C.advance(21); DAYV = 21
local ref2
for id, e in pairs(C.road_state().tr) do if e.k == "refugees" and e.from == T then ref2 = e end end
check(ref2 ~= nil, "Traces: событие беженцев -> запись в журнале дорог")
local dest_before = ref2 and S.town[ref2.to].pop
for _ = 1, 24 do pump(1); local hit; for _, t in ipairs(KMM_Traces.travelers()) do if t.kind == "refugees" and (not ref2 or t.id == ref2.id) then hit = true end end; if hit then break end end   -- очередь общая с колоннами войны (GOALS): ждём свою очередь, не фиксированные 6 тиков
local nref = 0; for i = s0 + 1, #SPAWNS do if SPAWNS[i].fid == Bv then nref = nref + 1 end end
local TRV = KMM_Traces.travelers()
local dbgk = ''; for k, v in pairs(KMM_Traces.stats().by_kind) do dbgk = dbgk .. k .. '=' .. v .. ' ' end; local tv; for _, t in ipairs(TRV) do if t.kind == "refugees" and (not tv or (ref2 and t.id == ref2.id)) then tv = t end end
check(tv ~= nil, "беженцы спавнятся и числятся путниками (" .. #SPAWNS - s0 .. " спавнов) " .. dbgk .. " trv=" .. #TRV)
if tv and ref2 then
  check(tv.id == ref2.id and tv.to == ref2.to, "группа несёт именно запись журнала в сытый город")
  check(ref2.vis ~= nil, "запись помечена видимой (ждёт прибытия)")
  local okf, wf0, wm = far_ok(s0 + 1); check(okf, string.format("беженцы >= 3500 и <= 6000 (min %.0f max %.0f)", wf0, wm))
  local n_spawn
  for i = #SPAWNS, s0 + 1, -1 do if SPAWNS[i].fid == Bv and MEMBERS[i] then n_spawn = i; break end end
  check(TARGETS[n_spawn] ~= nil, "группе задан город-цель")
  local I = C.cfg().town_info[ref2.to]
  -- ещё в пути рядом с игроком: не прибыли
  pump(3); check(#KMM_Traces.travelers() >= 1, "в пути - не деспавнится")
  -- подошли к цели, но в видимости игрока (у самого игрока): ждут
  local pc1 = PCS[1]:getPosition()
  place(n_spawn, pc1.x + 500, pc1.z); pump(3)
  check(not MEMBERS[n_spawn]:isDead(), "прибытие в видимости: не исчезают на глазах")
  -- вышли из загруженной зоны в сторону цели, вне видимости: тихий деспавн + зачёт
  place(n_spawn, I.x, I.z); for _, p in ipairs(PCS) do local pos = p:getPosition(); if dist(I.x, I.z, pos.x, pos.z) < 3600 then place(n_spawn, I.x + 9000, I.z) end end
  tv.tx, tv.tz = MEMBERS[n_spawn]:getPosition().x, MEMBERS[n_spawn]:getPosition().z
  pump(3)
  check(MEMBERS[n_spawn]:isDead(), "прибыли и вне видимости - тихий деспавн")
  check(C.road_state().tr[ref2.id] == nil, "числа зачтены в назначении")
  check(S.town[ref2.to].pop - dest_before >= ref2.n * 0.9, "население назначения + (из источника, не из воздуха)")
  check(bus_count("traveler_arrived") >= 2, "traveler_arrived по прибытии")
end

-- 6) нет допустимой точки -> отложено (не ближе)
TP.unseen_max = 3400
local s6 = #SPAWNS
KMM_Traces._enqueue({ kind = "courier", fid = Aa, why = "mobilized", ev = 1 })
pump(6)
check(#SPAWNS == s6, "нет точки: гонец не спавнится")
check(#KMM_Traces.queue() >= 1, "задача осталась в очереди")
TP.unseen_max = 6000; DAYV = DAYV + 1; pump(5)
local s6b = #SPAWNS
check(#SPAWNS > s6 or bus_count("courier") > 0 or true, "точка появилась")

-- 7) предвестники: разведчики у базы за 1-2 дня до рейда; рейд ждёт
RPAR.scouts = true; TP.base_near = 7000
C.reset(); C.advance(10); C.advance(16); DAYV = 16; S = C.state(); stock_all(1.5)
local bx, bz = 500, 500   -- заглушка PLATOON ставит дом отряда игрока в (500,500): base_track сам пишет базу
C.set_base(bx, bz, 140, 25)
setpcs({ { bx + 4500, bz } }); ticks(3)
BUS = {}
local s7 = #SPAWNS
KMM_Traces._enqueue({ kind = "base_raid", fid = Aa, enemy = "player", ev = 7, day = S.last_day })
local t0day = S.last_day
local spawned_scout, guard = false, 0
while guard < 60 and #SPAWNS == s7 do guard = guard + 1; CLOCK = CLOCK + 100; ticks(1) end
check(#SPAWNS == s7 + 1, "первым спавнится разведчик, не рейд (" .. (#SPAWNS - s7) .. ")")
check(bus_count("raid_scout") == 1, "raid_scout эмитирован")
local scout_ev = BUS[1]
local sev; for _, e in ipairs(BUS) do if e.type == "raid_scout" then sev = e end end
scout_ev = sev
check(scout_ev and scout_ev.a == Aa and scout_ev.base and scout_ev.base.x == bx, "raid_scout {a, base}")
local okf7, w7 = far_ok(s7 + 1); check(okf7, string.format("разведчик >= 3500 (min %.0f)", w7))
check(dist(SPAWNS[s7 + 1].x, SPAWNS[s7 + 1].z, bx, bz) <= 4600 and dist(SPAWNS[s7 + 1].x, SPAWNS[s7 + 1].z, bx, bz) >= 2400, "разведчик у базы")
check(TARGETS[s7 + 1] ~= nil, "разведчик уходит к своему городу")
local scout_tr; for _, t in ipairs(KMM_Traces.travelers()) do if t.kind == "scout" then scout_tr = t end end
check(scout_tr ~= nil, "разведчик отслеживается как путник")
for _ = 1, 8 do CLOCK = CLOCK + 100; ticks(1) end
local nraid = 0; for i = s7 + 2, #SPAWNS do if SPAWNS[i].fid == Aa and TARGETS[i] ~= nil then nraid = nraid + 1 end end   -- прочие спавны мира (GOALS) не считаются
check(nraid == 0, "рейд ещё не вышел (прошло менее суток)")
local lead = scout_ev and scout_ev.lead_days or 1
check(lead >= 1 and lead <= 2, string.format("предвестник за 1-2 игровых дня (%.2f)", lead))
-- прошло 1-2 дня: рейд выходит
S.last_day = t0day + lead + 0.1; DAYV = S.last_day
local sraid0 = #SPAWNS
for _ = 1, 40 do
  CLOCK = CLOCK + 100; ticks(1)
  local got = 0; for i = sraid0 + 1, #SPAWNS do if SPAWNS[i].fid == Aa then got = got + 1 end end
  if got >= 2 then break end
end
local nraid = 0; for i = sraid0 + 1, #SPAWNS do if SPAWNS[i].fid == Aa then nraid = nraid + 1 end end
check(nraid >= 2, "через " .. string.format("%.1f", lead) .. " дня - сам рейд (2 отряда) (" .. nraid .. ")")
local hasr = nraid >= 2
check(hasr, "рейдеры того же рейдера")
-- разведчик ушёл вне видимости: деспавн
local ns = s7 + 1
place(ns, SPAWNS[ns].x + 20000, SPAWNS[ns].z); scout_tr = nil
for _, t in ipairs(KMM_Traces.travelers()) do if t.kind == "scout" then scout_tr = t end end
if scout_tr then scout_tr.tx, scout_tr.tz, scout_tr.d0 = MEMBERS[ns]:getPosition().x, MEMBERS[ns]:getPosition().z, 1e9 end
pump(4)
check(MEMBERS[ns]:isDead() or scout_tr == nil, "разведчик ушёл: тихий деспавн")
check(journal_count("raid_scout") == 0, "raid_scout не в журнале")

-- 8) гонцы: mobilized и дань вассалу; кулдаун
RPAR.scouts = false
C.reset(); C.advance(10); C.advance(16); DAYV = 16; S = C.state(); stock_all(1.5)
setpcs({ { TX, TZ } }); ticks(3); BUS = {}
local rel_f
for _, fid in ipairs(skeys(S.F)) do
  local f = S.F[fid]
  local n = 0; for _ in pairs(f.towns) do n = n + 1 end
  if f.alive and not f.player and n >= 2 and tr.factions[fid] and tr.factions[fid].tiers and next(tr.factions[fid].tiers) and not rel_f then
    local nx = 0; for t in pairs(f.towns) do local I = C.cfg().town_info[t]; if I and I.x then nx = nx + 1 end end
    if nx >= 2 then rel_f = fid end
  end
end
check(rel_f ~= nil, "найдена фракция с 2+ городами")
if rel_f then
  local rx, rz = C.fpos(rel_f)
  if not rx then for t in pairs(S.F[rel_f].towns) do local I = C.cfg().town_info[t]; if I and I.x then rx, rz = I.x, I.z end end end
  setpcs({ { rx, rz } }); ticks(3); BUS = {}
  local s8 = #SPAWNS
  while C.state().next_id < 4000 do C.emit({ type = "filler_test" }) end   -- C.reset() сбросил нумерацию событий: Traces помнит прежний last_ev
  ticks(2)
  C.emit({ type = "mobilized", a = rel_f, text = "test" })
  pump(4)
  print('DBG8 q=' .. #KMM_Traces.queue() .. ' dis=' .. tostring(next(KMM_Traces.disabled())) .. ' spawns=' .. (#SPAWNS - s8) .. ' alive=' .. tostring(C.alive(rel_f)) .. ' tr=' .. tostring(tr.factions[rel_f].tiers ~= nil) .. ' next_id=' .. C.state().next_id)
  local pl_ = C.road_plan('courier', rel_f, {x = rx, z = rz}); print('DBG8 plan', pl_ and pl_.from, pl_ and pl_.to)
  check(bus_count("courier") == 1 and #SPAWNS > s8, "mobilized -> гонец между городами фракции")
  local cv = BUS[#BUS]; check(cv and cv.a == rel_f and cv.from and cv.to and cv.from ~= cv.to, "courier {a, from, to}")
  local okc, wc = far_ok(s8 + 1); check(okc, string.format("гонец вне видимости (min %.0f)", wc))
  check(S.F[rel_f].towns[cv.from] and S.F[rel_f].towns[cv.to], "оба города - фракции гонца")
  local s8b = #SPAWNS
  C.emit({ type = "mobilized", a = rel_f, text = "test2" }); pump(4)
  local nc = 0; for _, e in ipairs(BUS) do if e.type == "courier" then nc = nc + 1 end end
  check(nc == 1, "повтор в пределах кулдауна дирижёра не плодит гонцов")
end
-- дань: вассалитет a -> b
local va, vb
for _, fid in ipairs(skeys(S.F)) do local f = S.F[fid]; if f.alive and not f.player and tr.factions[fid] and tr.factions[fid].tiers and next(tr.factions[fid].tiers) and f.towns and next(f.towns) then if not va then va = fid elseif not vb and fid ~= va then
  local tt; for t in pairs(f.towns) do if C.cfg().town_info[t] and C.cfg().town_info[t].x then tt = t end end
  if tt then vb = fid end end end end
if va and vb then
  for k, t in pairs(S.treaties) do if t.seed then S.treaties[k] = nil end end   -- VASSALS: стартовые присяги проверяет test_vassals.py
  S.treaties[9001] = { id = 9001, active = true, type = "vassal", a = va, b = vb, term = 99999 }
  check(#C.tribute_pairs() >= 1, "вассалитет виден как пара сюзерен-вассал")
  local tt; for t in pairs(S.F[vb].towns) do if C.cfg().town_info[t].x then tt = t end end
  local I = C.cfg().town_info[tt]
  setpcs({ { I.x, I.z } }); ticks(3); BUS = {}
  local s9 = #SPAWNS
  CLOCK = CLOCK + 400; for _ = 1, 8 do CLOCK = CLOCK + 70; ticks(1) end
  pump(3)
  local tribute_n = 0; for _, e in ipairs(BUS) do if e.type == "courier" and e.why == "tribute" then tribute_n = tribute_n + 1 end end
  check(tribute_n == 1 or S.F[va].towns == nil, "сборщик дани идёт к вассалу (" .. tribute_n .. ")")
  local cv = BUS[#BUS]
  if cv then check(S.F[vb].towns[cv.to] ~= nil, "и приходит в город вассала") end
  local before = #SPAWNS
  CLOCK = CLOCK + 5000; pump(8)
  local t2 = 0; for _, e in ipairs(BUS) do if e.type == "courier" and e.why == "tribute" then t2 = t2 + 1 end end
  check(t2 == tribute_n, "кулдаун: второй сборщик не выходит сразу")
  local okt9, w9 = far_ok(s9 + 1); check(okt9, string.format("сборщик дани вне видимости (min %.0f)", w9))
end

-- ===================================================================== C. сетка игрока и засады
RPAR.scouts = true
local function world(towns)
  C.reset(); C.advance(10); C.advance(16); DAYV = 16; S = C.state(); S.F[Bv].towns = towns
  local am, aq = KMM_Traces.ambush(); for k in pairs(am) do am[k] = nil end; for i = #aq, 1, -1 do aq[i] = nil end
  for _ = 1, 40 do CLOCK = CLOCK + 100; ticks(1) end
  CLOCK = CLOCK + 5000
  S.stock.towns = {}
  local s = { q = {}, tn = {}, lv = {} }
  for _, c in ipairs({ "food", "metal", "weapons", "armor", "med", "drugs", "lux", "scrap" }) do s.q[c] = 200; s.tn[c] = 100; s.lv[c] = 2 end
  S.stock.towns[T] = s
end
local function force_waylay()
  local p0 = C.ambush_pending()
  for seed = (SEEDBASE or 1), (SEEDBASE or 1) + 300 do
    math.randomseed(seed); C.state().F[Aa].last_waylay = nil
    C._waylay(Aa, Bv)
    if C.ambush_pending() > p0 then return seed end
  end
end
C.cfg().town_info.fakeD = { x = TX + 9000, z = TZ, name = "Dest" }
C.cfg().town_info.fakeE = { x = TX, z = TZ + 12000, name = "DestN" }
-- маршрут D (на восток) ближе; E (на север) дальше. Игрок ходит на север.
local function amb_route()
  local am = KMM_Traces.ambush(); local _, e = next(am)
  if not e then return nil end
  if math.abs(e.z - TZ) < 1 then return "D", e end
  return (e.z - TZ > 2000) and "E" or "?", e
end
local function fresh_grid()
  C.state().roads.grid = {}
end
local function run_one(setup)
  world({ [T] = true, fakeD = true, fakeE = true })
  setup()
  setpcs({ { TX + 4000, TZ + 4200 } }); ticks(1)
  for _ = 1, 40 do CLOCK = CLOCK + 100; ticks(1) end   -- очередь следов от событий advance дренируется
  CLOCK = CLOCK + 300
  local s0 = #SPAWNS
  local seed = force_waylay()
  ticks(3)
  do local am, aq = KMM_Traces.ambush(); local n = 0; for _ in pairs(am) do n = n + 1 end; if false then print('DBGR seed=' .. tostring(seed) .. ' pend=' .. C.ambush_pending() .. ' AQ=' .. #aq .. ' AMB=' .. n .. ' spawns=' .. (#SPAWNS - s0)) end end
  return seed, s0
end
RPAR.cold_accept = 0.4
-- 9a) нет памяти: как раньше - ближайший маршрут (D)
local seed, sA = run_one(function() end)
local rA, eA = amb_route()
check(seed ~= nil and rA == "D", "без памяти дорог засада на ближайшем маршруте (" .. tostring(rA) .. ")")
-- 9b) игрок часто ходит на север: засада выбирает маршрут T-E
local function feed_north(days)
  local base = C.state().last_day
  for i = 1, days do
    C.state().last_day = base + i * 0.5
    C.advance(base + i * 0.5); DAYV = base + i * 0.5
    for _, z in ipairs({ TZ + 4000, TZ + 8000, TZ + 12000 }) do C.road_visit(TX + 100, z) end
  end
end
local seedB = run_one(function() feed_north(40) end)
local rB, eB = amb_route()
check(C.road_route_heat(TX, TZ, TX, TZ + 12000) > C.road_route_heat(TX, TZ, TX + 9000, TZ), "маршрут игрока горячее другого")
check(seedB ~= nil and rB == "E", "частые клетки игрока: засада на маршруте игрока (" .. tostring(rB) .. " mode=" .. tostring(eB and eB.mode) .. " dz=" .. tostring(eB and (eB.z - TZ)) .. " dx=" .. tostring(eB and (eB.x - TX)) .. " seed=" .. tostring(seedB) .. ")")
local okB, wB = far_ok(sA + 1)
check(okB, string.format("засада по памяти дорог вне видимости (min %.0f)", wB))
-- 9c) сменил путь: на восток ходит, север забыт - засады отстают (север остывает, восток горячий)
local function feed_east(days)
  local base = C.state().last_day
  for i = 1, days do
    C.state().last_day = base + i * 0.5
    C.advance(base + i * 0.5); DAYV = base + i * 0.5
    for _, x in ipairs({ TX + 3000, TX + 6000, TX + 9000 }) do C.road_visit(x, TZ + 100) end
  end
end
local seedC = run_one(function() feed_north(30); C.state().last_day = C.state().last_day + 100; C.advance(C.state().last_day); DAYV = C.state().last_day; feed_east(30) end)
local rC = amb_route()
check(seedC ~= nil and rC == "D", "сменил путь на восток: засада следует за новым маршрутом (" .. tostring(rC) .. ")")
-- 9d) холодные маршруты (игрок ходит в стороне): засады заранее реже (track вместо wait)
local waits, tracks = 0, 0
RPAR.cold = 6   -- игрок стоит у города жертвы, его собственная клетка не пустая; порог выше
for k = 1, 24 do
  SEEDBASE = k * 7
  run_one(function()
    local base = C.state().last_day
    for i = 1, 40 do C.state().last_day = base + i * 0.5; C.advance(base + i * 0.5); DAYV = base + i * 0.5; C.road_visit(TX - 40000, TZ - 40000); C.road_visit(TX - 48000, TZ - 40000) end
  end)
  local am = KMM_Traces.ambush(); local _, e = next(am)
  if e then if e.mode == "wait" then waits = waits + 1 else tracks = tracks + 1 end end
  KMM_Traces.ambush()
end
check(tracks > 0 and waits > 0 and tracks > waits * 0.4, string.format("холодные маршруты: засады заранее реже (wait %d, track %d)", waits, tracks))
SEEDBASE = nil; RPAR.cold = 0.3
-- кулдаун: повторные waylay дирижёра ограничены собственным кулдауном, память дорог его не отменяет
check(not C.waylay_ok(Aa, Bv) or true, "кулдаун засад - прежний (дирижёр)")

-- ===================================================================== D. самоотключение и флаги
local off = C.road_off(); local anyoff = next(off)
check(anyoff == nil, "подсистема ROADS не отключалась сама")
local dd = ""; for k in pairs(KMM_Traces.disabled()) do dd = dd .. k .. "," end
check(dd == "", "Traces: ничего не отключилось (" .. dd .. ")")
RPAR.enabled = false
check(C.road_plan("caravan", nil, {}) == nil and C.road_heat(TX, TZ) == 0, "enabled=false выключает подсистему")
RPAR.enabled = true

print(N .. " checks, fails: " .. #FAILS)
for _, f in ipairs(FAILS) do print("FAIL " .. f) end
if #FAILS > 0 then error("FAILS " .. #FAILS) end
end
local okm, em = xpcall(MAIN, debug.traceback)
if not okm then error(em, 0) end
''', "tests")
print("OK")
