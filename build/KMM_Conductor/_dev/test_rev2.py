"""Офлайн-тест REV2 (ревизия видения 2026-11-12): города (гарнизон при мятеже/возврате), реакции (репутация предателя, оппортунизм при распаде),
слабые избегают сильных (модель + KMM_Self между фракциями + Traces не шлют колонны затаившихся и павших), совместные рейды союзников,
рейд на базу игрока (ожидание возвращения, исход «отбит»/«пусто»), эволюция (павшая фракция не выставляет отрядов).
python -I -X utf8 build/KMM_Conductor/_dev/test_rev2.py -> OK, код 1 при провале."""
import ctypes
import os
import re
import tempfile

DLL = r"C:\Program Files (x86)\Steam\steamapps\workshop\content\233860\3817000612\lua51.dll"
B = r"C:\KenshiModMap\build\KMM_Conductor\scripts\init"
TMP = tempfile.mkdtemp(prefix="kmm_rev2_").replace("\\", "/")
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
run(open(B + r"\KMM_Self.lua", encoding="utf-8").read(), "KMM_Self.lua")
run(r'''
N, FAILS = 0, {}
function check(c, what) N = N + 1; if not c then FAILS[#FAILS + 1] = what end end
function ticks(n) for i = 1, n do CLOCK = CLOCK + 1; DAYV = DAYV + 0.001; FIRE("GameWorld::charsUpdate", {}) end end
local C = KMM_Conductor
local P = C.cfg().params
C._set("tick_days", 1e9); C._set("first_event_after_days", 1e9)   -- без случайных шагов мира: события только наши
P.traces.first_hour_traces = 0; P.traces.arrive_enabled = false; P.traces.max_per_day = 1000
C.reset()
C.cfg().params.roads.scouts = false   -- ROADS: предвестники проверяются в test_roads.py
local S = C.state()
local tr = C.read_json("traces.json", "C:/KenshiModMap/build/KMM_Conductor/traces.json")
local pf = C.cfg().player_faction
DAYV = 10
local function drain(k) for _ = 1, k or 4 do CLOCK = CLOCK + 100; ticks(2) end end   -- по одному спавну на min_gap
local function evs(ty) local n = 0; for _, e in ipairs(C.state().events) do if e.type == ty then n = n + 1 end end; return n end
local function lastev(ty) local r; for _, e in ipairs(C.state().events) do if e.type == ty then r = e end end; return r end
local function setrel(a, b, v) S.rel[a] = S.rel[a] or {}; S.rel[b] = S.rel[b] or {}; S.rel[a][b] = v; S.rel[b][a] = v; end
local function trust(a, b) return S.F[a].trust[b] or 0 end
-- платуны с лидером и целью (как в test_link15) + учёт целей
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
local function mkchar(nm, fid, x, z, key, opt)
  opt = opt or {}
  local c = MKCH(nm, fid, x, z, { platoon = key, combat = opt.combat })
  local pl = PLATOON(key)
  function c:getPlatoon() return setmetatable({ me = pl }, { __index = { getIsTrader = function() return false end } }) end
  return c
end
local function setp(x, z) PCS[1] = MKCH("Nameless", pf or "player", x, z, { player = true, platoon = "player_squad" }); CHARS = { PCS[1] } end
-- фракции: у кого есть шаблоны Traces, города, соседи
local cand = {}
for fid, f in pairs(S.F) do
  local e = tr.factions[fid]
  local nt = 0; for _ in pairs(f.towns) do nt = nt + 1 end
  if f.alive and not f.player and not f.relic and e and e.tiers and nt > 0 then cand[#cand + 1] = fid end
end
table.sort(cand)
check(#cand >= 5, "есть фракции с шаблонами Traces (" .. #cand .. ")")
local function town_of(fid) for t in pairs(S.F[fid].towns) do local I = C.cfg().town_info[t]; if I and I.x then return t, I.x, I.z end end end
local A, O, L, V = cand[1], cand[2], cand[3], cand[4]
local TA, AX, AZ = town_of(A)
setp(AX + 2500, AZ)
ticks(6)

-- 1) города: мятеж возвращает город прежнему хозяину → у него гарнизон; town_rejoined тоже
CLOCK = CLOCK + 5000
local g0 = (KMM_Traces.stats().by_kind.garrison or 0)
C.emit({ type = "revolt", a = A, b = O, town_sid = TA, town_name = "T" })
drain()
check((KMM_Traces.stats().by_kind.garrison or 0) == g0 + 1, "revolt: гарнизон нового хозяина (a) материализован")
local gfound = false; for _, sp in ipairs(SPAWNS) do if sp.fid == A then gfound = true end end
check(gfound, "гарнизон — отряд фракции-хозяина")
CLOCK = CLOCK + 5000
C.emit({ type = "town_rejoined", a = A, town_sid = TA, town_name = "T" })
drain()
check((KMM_Traces.stats().by_kind.garrison or 0) == g0 + 2, "town_rejoined: гарнизон")
CLOCK = CLOCK + 5000
C.emit({ type = "revolt", b = O, town_sid = TA, town_name = "T" })   -- вольный город (без a): гарнизона нет
drain()
check((KMM_Traces.stats().by_kind.garrison or 0) == g0 + 2, "revolt без хозяина (вольный город): гарнизона нет")

-- 2) эволюция: павшая фракция и затаившаяся не выставляют колонн/отрядов; затаившаяся на базу идёт
CLOCK = CLOCK + 5000
local n0 = #SPAWNS
S.F[A].alive = false
KMM_Traces._enqueue({ kind = "column", fid = A, enemy = O, tx = AX, tz = AZ, why = "t" })
drain(2)
check(#SPAWNS == n0 and (KMM_Traces.stats().skipped_dead or 0) == 1, "павшая фракция: колонна не выставлена")
S.F[A].alive = true
CLOCK = CLOCK + 5000
S.F[A].low_until = S.last_day + 10
KMM_Traces._enqueue({ kind = "column", fid = A, enemy = O, tx = AX, tz = AZ, why = "t" })
drain(2)
check(#SPAWNS == n0 and (KMM_Traces.stats().skipped_low or 0) == 1, "затаившаяся фракция: колонна не выставлена")
check(C.low(A) == true and C.alive(A) == true, "API low/alive")
S.F[A].low_until = nil
CLOCK = CLOCK + 5000
KMM_Traces._enqueue({ kind = "column", fid = A, enemy = O, tx = AX, tz = AZ, why = "t" })
drain(2)
check(#SPAWNS > n0, "после затишья колонна снова выходит")

-- 3) реакции: репутация предателя
local nb
for _, e in ipairs(C.cfg().factions[A].near or {}) do if S.F[e[1]] and S.F[e[1]].alive and not S.F[e[1]].player and e[1] ~= O and e[2] <= P.bus.radius then nb = e[1]; break end end
check(nb ~= nil, "у фракции есть сосед в радиусе шины")
S.F[nb].trust[A] = 0; setrel(nb, A, 0); setrel(nb, O, 30)
S.treaties[900] = { id = 900, type = "defense", a = nb, b = O, active = true, since = 0, term = 1e9 }
local t0, r0 = trust(nb, A), C.rel(nb, A)
C.emit({ type = "betrayal", a = A, b = O, treaty = "trade", text = "t" })
check(trust(nb, A) < t0, "предательство: сосед теряет доверие к предателю (" .. t0 .. " -> " .. trust(nb, A) .. ")")
check(C.rel(nb, A) < r0, "предательство: союзник жертвы холоднее к предателю (" .. r0 .. " -> " .. C.rel(nb, A) .. ")")
check((S.stats.rep_hits or 0) == 1, "rep_hits=1")
S.treaties[900] = nil

-- 4) реакции: распад державы → оппортунизм недругов
local V2 = O
local nb2
for _, e in ipairs(C.cfg().factions[V2].near or {}) do if S.F[e[1]] and S.F[e[1]].alive and not S.F[e[1]].player and e[1] ~= V and e[1] ~= V2 and e[2] <= P.bus.radius then nb2 = e[1]; break end end
check(nb2 ~= nil, "у ослабшей державы есть сосед")
nb = nb2
S.F[V2].strength = 10; S.F[nb].strength = 200; setrel(nb, V2, -40); S.F[nb].opp = {}
C.emit({ type = "faction_split", a = V, b = V2, text = "t" })
check(S.F[nb].opp[V2] ~= nil and S.F[nb].opp[V2] > S.last_day, "faction_split: недруг ослабшей державы получает окно оппортунизма")
S.F[nb].opp = {}
C.emit({ type = "warlord_rose", a = V, b = V2, text = "t" })
check(S.F[nb].opp[V2] ~= nil, "warlord_rose: оппортунизм")
S.F[nb].opp = {}
setrel(nb, V2, 30)
C.emit({ type = "revolt", a = V, b = V2, text = "t" })
check(S.F[nb].opp[V2] == nil, "друг ослабшей державы оппортунизма не получает")

-- 5) слабые избегают сильных: модель
do
  local W, Sg = cand[1], cand[2]
  for fid, f in pairs(S.F) do f.opp = {} ; f.wronged = nil end
  S.base = nil   -- рейд на базу игрока здесь не мешает выбору
  S.F[W].strength = 100; S.F[W].wealth = 10; S.F[Sg].strength = 400; S.F[W].ambition = "expansion"
  for _, e in ipairs(C.cfg().factions[W].near or {}) do setrel(W, e[1], 0); if e[1] ~= Sg and S.F[e[1]] then S.F[e[1]].wealth = 0 end end
  setrel(W, Sg, -25)
  -- соседство
  local near = C.cfg().factions[W].near
  local have = false; for _, e in ipairs(near or {}) do if e[1] == Sg then have = true end end
  if not have then table.insert(near, { Sg, 1000 }) end
  local real = math.random
  math.randomseed(77)
  local function trial(n)
    local bad = 0
    for _ = 1, n do
      local a, arg = C.choose(W)
      if (a == "raid" or a == "capture" or a == "waylay") and arg == Sg then bad = bad + 1 end
    end
    return bad
  end
  local avoided = trial(400)
  check(avoided == 0, "слабая фракция не идёт рейдом/захватом/засадой на явно сильную (" .. avoided .. ")")
  P.rev2.avoid_ratio = 0
  local control = trial(400)
  check(control > 0, "контроль (избегание выключено): те же рейды случаются (" .. control .. ")")
  P.rev2.avoid_ratio = 0.4
  S.F[W].wronged = { [Sg] = S.last_day }
  local rev = trial(400)
  check(rev > 0, "обидчик, которому слабый мстит, не избегается (" .. rev .. ")")
  S.F[W].wronged = nil
  -- затаиться
  S.F[W].low_until = nil
  local e0 = evs("lie_low")
  C._act(W, "hide", Sg)
  check(evs("lie_low") == e0 + 1 and C.low(W), "hide: событие lie_low, фракция затаилась")
  C._act(W, "hide", Sg)
  check(evs("lie_low") == e0 + 1, "повторное hide не дублирует событие")
  S.last_day = S.last_day + 50
  check(not C.low(W), "через low_days затишье кончается")
  S.last_day = S.last_day - 50
  S.F[W].low_until = nil
end

-- 6) слабые избегают сильных: KMM_Self между фракциями в загруженной зоне
do
  local W, Sg = cand[1], cand[2]
  S.F[W].strength = 10; S.F[Sg].strength = 400
  S.F[W].mode, S.F[Sg].mode = nil, nil
  setrel(W, Sg, -60)
  setp(AX, AZ)
  local function arena(wfid, sfid)
    local w, s = {}, {}
    for i = 1, 3 do w[i] = mkchar("w" .. i, wfid, AX + 100 + i, AZ, "wsq", { combat = true }); s[i] = mkchar("s" .. i, sfid, AX + 600 + i, AZ, "ssq", { combat = true }) end
    CHARS = { PCS[1], w[1], w[2], w[3], s[1], s[2], s[3] }
  end
  arena(W, Sg)
  local r0, st0 = RUNAWAY, KMM_Self.stats().faction_avoid
  CLOCK = CLOCK + 100; ticks(4)
  check(KMM_Self.stats().faction_avoid == st0 + 1 and RUNAWAY >= r0 + 1, "Self: слабый отряд в бою с сильной фракцией отходит (runAway)")
  local r1 = RUNAWAY
  ticks(4)
  check(RUNAWAY == r1, "Self: кулдаун на отряд — повторно не гоним")
  -- равные силы: не бегут
  S.F[W].strength = 400
  PLATOONS["wsq"], PLATOONS["ssq"] = nil, nil
  arena(W, Sg); CLOCK = CLOCK + 100
  local r2 = RUNAWAY
  ticks(4)
  check(RUNAWAY == r2, "Self: при равной силе фракций никто не отходит")
  -- слабый, но враг не враждебен: не бегут
  S.F[W].strength = 10; setrel(W, Sg, 10)
  PLATOONS["wsq"], PLATOONS["ssq"] = nil, nil
  arena(W, Sg); CLOCK = CLOCK + 100
  local r3 = RUNAWAY
  ticks(4)
  check(RUNAWAY == r3, "Self: нейтральный/дружеский сильный — не повод бежать")
  CHARS = { PCS[1] }
  setrel(W, Sg, -60)
end

-- 7) совместные рейды союзников
do
  local A2, Lally, Tgt = cand[1], cand[3], cand[4]
  for fid, f in pairs(S.F) do f.opp = {}; f.wronged = nil; f.last_war = nil end
  for k in pairs(S.treaties) do S.treaties[k] = nil end
  S.treaties[1] = { id = 1, type = "military", a = A2, b = Lally, active = true, since = 0, term = 1e9 }
  S.F[A2].strength, S.F[Lally].strength, S.F[Tgt].strength = 100, 100, 100
  setrel(Lally, Tgt, -30); setrel(A2, Tgt, -40)
  local real = math.random
  math.random = function(n) if n then return 1 end; return 0.01 end
  local j0, w0, str0, tr0 = evs("joint_raid"), S.F[Lally].wealth, S.F[Lally].strength, trust(A2, Lally)
  C._act(A2, "raid", Tgt)
  local je = lastev("joint_raid")
  check(evs("joint_raid") == j0 + 1 and je and je.a == Lally and je.b == Tgt and je.lead == A2, "raid: союзник по военному договору присоединился (joint_raid)")
  check(S.F[Lally].strength < str0, "союзник платит силой за участие")
  check(S.F[Lally].wealth > w0, "союзник получает долю добычи при удачном рейде")
  check(trust(A2, Lally) > tr0, "доверие между союзниками растёт")
  check((S.treaties[1].last_joint or -1e9) >= S.last_day, "кулдаун договора выставлен")
  C._act(A2, "raid", Tgt)
  check(evs("joint_raid") == j0 + 1, "кулдаун: второй рейд подряд без союзника")
  -- нет присоединения: договор с целью, нет военного, слабый союзник
  S.treaties[1].last_joint = nil
  S.treaties[2] = { id = 2, type = "nonaggression", a = Lally, b = Tgt, active = true, since = 0, term = 1e9 }
  C._act(A2, "raid", Tgt)
  check(evs("joint_raid") == j0 + 1, "союзник с договором с целью не присоединяется")
  S.treaties[2] = nil
  S.treaties[1].type = "defense"
  C._act(A2, "raid", Tgt)
  check(evs("joint_raid") == j0 + 1, "оборонительный пакт — не наступательный: без присоединения")
  S.treaties[1].type = "military"
  S.F[Lally].strength = 5
  C._act(A2, "raid", Tgt)
  check(evs("joint_raid") == j0 + 1, "слишком слабый союзник не присоединяется")
  S.F[Lally].strength = 100
  -- захват: joint_raid с городом, шанс растёт
  local T2; for t in pairs(S.F[Tgt].towns) do T2 = t; break end
  S.F[A2].strength = 300; S.F[Tgt].strength = 100
  local c0 = evs("town_captured")
  C._act(A2, "capture", Tgt)
  local je2 = lastev("joint_raid")
  check(evs("joint_raid") == j0 + 2 and je2.town_sid ~= nil and je2.success == true, "capture: союзник идёт на захват, исход в событии")
  check(evs("town_captured") == c0 + 1, "захват состоялся")
  -- шина: joint_raid как нападение (союзники жертвы получают обязательства)
  math.random = real
  -- Traces: колонна союзника к цели
  CLOCK = CLOCK + 5000
  setp(AX + 2500, AZ)
  S.F[Lally].alive = true
  local x1, z1 = C.fpos(Tgt)   -- событие привязано к месту цели рейда
  setp((x1 or AX) + 2500, z1 or AZ)
  drain(10)   -- события предыдущих шагов уже разобраны
  local n1 = #SPAWNS
  C.emit({ type = "joint_raid", a = Lally, b = Tgt, lead = A2, text = "t" })
  drain(6)
  local got = false; for i = n1 + 1, #SPAWNS do if SPAWNS[i].fid == Lally then got = true end end
  check(got, "joint_raid: колонна союзника материализуется отдельно от ведущего")
end

-- 8) рейд на базу игрока: ждёт возвращения, исход «отбит» / «пусто»
do
  for k in pairs(S.treaties) do S.treaties[k] = nil end
  local R = cand[2]
  local bx, bz = 500, 500   -- заглушка PLATOON ставит дом отряда игрока в (500,500): base_track сам пишет базу
  setp(bx + 30000, bz); ticks(2); CLOCK = CLOCK + 100; ticks(40)   -- база известна, очередь следов пуста
  drain(8)
  C.set_base(bx, bz, 100, 10)
  S.base.last_raid = nil
  S.F[R].strength = 120
  local f0 = S.F[R].wealth
  setp(bx + 30000, bz)   -- игрок далеко от базы
  CLOCK = CLOCK + 5000; ticks(2)
  local n0 = #SPAWNS
  C.emit({ type = "base_raid", a = R, b = pf, why = "greed", day = S.last_day, text = "t" })
  drain(2)
  check(#SPAWNS == n0, "игрока нет на базе: рейдеры не спавнятся (ждут)")
  local function nbr() local n = 0; for _, j in ipairs(KMM_Traces.queue()) do if j.kind == "base_raid" then n = n + 1 end end; return n end
  check(nbr() == 1, "рейд ждёт в очереди")
  CLOCK = CLOCK + 5000
  ticks(3)
  check(#SPAWNS == n0, "ожидание продолжается")
  -- игрок вернулся к базе
  setp(bx + 1000, bz)
  CLOCK = CLOCK + 5000
  drain(2)
  check(#SPAWNS == n0 + 2 and SPAWNS[#SPAWNS].fid == R, "игрок у базы: два отряда рейдеров")
  check(TARGETS[#SPAWNS] == "h_Nameless", "рейдеры идут на персонажа игрока")
  local ux, uz = SPAWNS[#SPAWNS].x, SPAWNS[#SPAWNS].z
  check(math.sqrt((ux - (bx + 1000)) ^ 2 + (uz - bz) ^ 2) >= 3500 - 1, "рейдеры вне видимости игрока (>= 3500)")
  -- рейдеров разбили
  local k1, k2 = "sq" .. (#SPAWNS - 2), "sq" .. (#SPAWNS - 1)
  local r1 = mkchar("rd1", R, ux, uz, k1); local r2 = mkchar("rd2", R, ux + 50, uz, k2)
  CHARS = { PCS[1], r1, r2 }
  CLOCK = CLOCK + 10; ticks(6)
  check(evs("base_raid_repelled") == 0, "пока рейдеры живы, исхода нет")
  local str0 = S.F[R].strength
  r1.dead = true; r2.dead = true
  ticks(7)
  check(evs("base_raid_repelled") == 1, "рейдеры мертвы при живой базе: base_raid_repelled")
  check(S.F[R].strength < str0, "рейдер теряет силу")
  check((S.base.def_bonus or 0) > 0, "оборона базы получает бонус за отбитый рейд")
  -- бонус влияет на мотив жадности: защита выше
  -- «пусто»: игрок так и не вернулся за hold_days
  CHARS = { PCS[1] }
  S.base.last_raid = nil
  setp(bx + 30000, bz)
  CLOCK = CLOCK + 5000; ticks(2)
  local n1 = #SPAWNS
  local w1 = S.F[R].wealth
  C.emit({ type = "base_raid", a = R, b = pf, why = "need", day = S.last_day, text = "t" })
  ticks(3)
  check(nbr() == 1 and #SPAWNS == n1, "второй рейд ждёт")
  DAYV = DAYV + 12
  CLOCK = CLOCK + 5000; ticks(3)
  check(evs("base_raid_unattended") == 1 and #SPAWNS == n1 and nbr() == 0, "не дождались: base_raid_unattended, спавна нет")
  check(S.F[R].wealth > w1, "рейдеры уносят добычу в абстракции")
  check((S.stats.base_unattended or 0) == 1 and (S.stats.base_repelled or 0) == 1, "статистика базы")
  -- рейдер неизвестен базе: API не падает
  check(C.base_result("repelled", "no_such_fid") == false, "base_result с неизвестной фракцией не падает")
end

print(N .. " checks, fails: " .. #FAILS)
for _, f in ipairs(FAILS) do print("FAIL " .. f) end
if #FAILS > 0 then error("FAILS " .. #FAILS) end
''', "tests")
print("OK")
