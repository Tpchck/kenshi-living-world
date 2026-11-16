-- KMM_Traces — видимые следы событий дирижёра рядом с игроком (шаг 1 офлайн-билда, 2026-11-12)
-- Каждое событие дирижёра в радиусе игрока оставляет материальный след: беженцы из павшего/голодного/захваченного города,
-- военные колонны, разорённые караваны (тела на дороге), усиленные гарнизоны, пачки отрядов в тире богатства фракции,
-- цены у ближайших торговцев. Первый час новой игры — несколько следов из стартового (семенного) состояния мира.
-- Шаблоны отрядов — поток данных KMM_Traces (tools/streams/traces.py) → traces.json.
-- Безотказность: каждая функция в pcall; при первой ошибке отключается до конца сессии, причина → logs/debug.log.

local TAG = "[KMM_Traces] "
local SQUAD_TYPE = 52   -- itemType.SQUAD_TEMPLATE
local TIERS = { "T0", "T1", "T2", "T3" }
local TIDX = { T0 = 1, T1 = 2, T2 = 3, T3 = 4 }

local C, CFG, P, TR      -- KMM_Conductor API, его конфиг, params.traces, traces.json
local DISABLED = {}
local function log(msg) msg = TAG .. tostring(msg); if not (KenshiLua and pcall(function() KenshiLua.log(msg) end)) then print(msg) end end
local function dlog(msg)
  local path = (CFG and CFG.params and CFG.params.guard and CFG.params.guard.debug_log) or "C:/KenshiModMap/logs/debug.log"
  local ok, f = pcall(io.open, path, "a")
  if ok and f then f:write(os.date("%Y-%m-%d %H:%M:%S"), " [KMM_Traces] ", tostring(msg), "\n"); f:close() end
  log(msg)
end
-- HEALTH: отказы идут в реестр KMM_Gov (ключи KMM_Traces.<механика>): пауза 60/300/1800 с и повтор; без Gov - до перезапуска.
local function HG() local g = rawget(_G, "KMM_Gov"); if type(g) == "table" and type(g.h_fail) == "function" then return g end end
local DISABLED_P, RETRY = {}, {}
local function h_off(k, why, kind) local g = HG(); if g and type(g.h_off) == "function" then pcall(g.h_off, k, why, kind) end end
local function is_down(nm)
  if not DISABLED[nm] then return false end
  local key = DISABLED_P[nm]
  local g = HG()
  if key and g then
    local ok, up = pcall(g.h_up, key)
    if (not ok) or up ~= false then DISABLED[nm], DISABLED_P[nm], RETRY[nm] = nil, nil, true; return false end
  end
  return true
end
local function go_down(nm, err)
  DISABLED[nm], DISABLED_P[nm], RETRY[nm] = true, nil, nil
  local g, p = HG(), nil
  if g then local ok, r = pcall(g.h_fail, "KMM_Traces." .. nm, err); if ok and type(r) == "number" then p = r end end
  if p then DISABLED_P[nm] = "KMM_Traces." .. nm end
  dlog(nm .. (p and (" failed, retry in " .. p .. " s: ") or " disabled until restart: ") .. tostring(err))
end
local function go_ok(nm) if RETRY[nm] then RETRY[nm] = nil; local g = HG(); if g then pcall(g.h_ok, "KMM_Traces." .. nm) end end end
local function guarded(nm, fn)
  return function(...)
    if is_down(nm) then return end
    local ok, err, r2, r3 = pcall(fn, ...)
    if not ok then go_down(nm, err); return end
    go_ok(nm)
    return err, r2, r3
  end
end

local function xz(v) if v then return v.x or v[1], v.z or v[3], v.y or v[2] or 0 end end
local function player_char()
  local ok, pc = pcall(function()
    for _, c in pairs(getPlayerInterface():getAllPlayerCharacters()) do return c end
  end)
  return ok and pc or nil
end
local function player_pos()
  local pc = player_char()
  if not pc then return nil end
  local ok, x, z, y = pcall(function() return xz(pc:getPosition()) end)
  if ok and x then return x, z, y, pc end
end
local function dist(ax, az, bx, bz) return math.sqrt((ax - bx) ^ 2 + (az - bz) ^ 2) end

---------------------------------------------------------------------------------------------- снимок загруженных NPC (PERF фаза 1)
-- Источник — KMM_Gov.snapshot(ttl) (один обход на окно на все модули). Нет Gov / ошибка снимка → собственный обход own_snapshot (тот же формат записей,
-- кэш на ttl секунд): сканы lost/amb/br/loot/prices/dead делят один обход, а не ходят каждый по всему списку.
-- rec: ch, x, z, fid, dead, ap, pl, pkey ("" = нет платуна); лениво: trader, tsid, down, unique, h. Игроки в снимок не входят.
local function o_core(ch, r)
  local pos = ch:getPosition()
  r.x, r.z = pos.x or pos[1], pos.z or pos[3]
  if not (r.x and r.z) then error("no pos") end
  r.dead = ch:isDead() and true or false
end
local function o_fac(ch, r)   -- фракция необязательна: без неё запись остаётся (fid = nil)
  local f = ch:getFaction(); local gd = f and (f:getData() or f.data)
  r.fid = gd and gd.stringID
end
local function o_plat(ch, r)
  local ap = ch:getPlatoon()
  r.ap = ap; r.pl = ap and ap.me
  local me = ap and (ap.me or ap)
  local k = me and me:getPlatoonStringID()
  r.pkey = (k and k ~= "") and k or ""
end
local O_LAZY = {
  trader = function(r) return (r.ap and r.ap:getIsTrader()) and true or false end,
  tsid = function(r) local t = r.pl and r.pl.squadTemplate; return t and t.stringID end,
  down = function(r) return (r.dead or r.ch:isDown() or r.ch:isUnconcious()) and true or false end,
  unique = function(r) return r.ch:isUnique() and true or false end,
  h = function(r) local h = r.ch:getHandle(); local ok, s = pcall(function() return h:toString() end); if ok and type(s) == "string" then return s end; return tostring(h) end,   -- hand:toString(): tostring(hand) — новый адрес на каждый вызов
}
local O_MT = { __index = function(r, k)
  local fn = O_LAZY[k]
  if not fn then return nil end
  local ok, v = pcall(fn, r)
  if not ok or v == nil then v = false end
  rawset(r, k, v)
  return v
end }
local OWN
local function own_snapshot(ttl)
  local now = os.clock()
  -- краш 2026-11-13: между кадрами персонаж может быть удалён движком — повторно только в том же кадре (игровая метка времени)
  local okst, stamp = pcall(function() return getGameWorld():getTimeStamp() end)
  if okst and type(stamp) == "number" then
    if OWN and OWN.stamp == stamp and now - OWN.t >= 0 and now - OWN.t <= 0.25 then return OWN end
  elseif OWN and now - OWN.t >= 0 and now - OWN.t <= ttl then return OWN end
  local list, by_pkey, n = {}, {}, 0
  for ch in pairs(getGameWorld():getCharacterUpdateList()) do
    local okp, isp = pcall(ch.isPlayerCharacter, ch)
    if okp and not isp then
      local r = { ch = ch }
      if pcall(o_core, ch, r) then
        pcall(o_fac, ch, r)
        if not pcall(o_plat, ch, r) then r.pkey = "" end
        setmetatable(r, O_MT)
        n = n + 1; list[n] = r
        if r.pkey ~= "" then local b = by_pkey[r.pkey]; if b then b[#b + 1] = r else by_pkey[r.pkey] = { r } end end
      end
    end
  end
  OWN = { t = now, n = n, list = list, by_pkey = by_pkey, own = true }
  do local ok2, st2 = pcall(function() return getGameWorld():getTimeStamp() end); if ok2 then OWN.stamp = st2 end end
  return OWN
end
local function get_snap(ttl)
  local g = rawget(_G, "KMM_Gov")
  if g and g.snapshot then
    local ok, snap = pcall(g.snapshot, ttl)
    if ok and snap then return snap end
  end
  return own_snapshot(ttl)
end
local function snap_ttl() return (P and P.snap_ttl) or 4 end   -- устаревание снимка для сканов следов, сек
-- S5 (2026-11-15): в игре снимок Gov живёт один кадр (метка getTimeStamp), и каждый вызов в новом кадре — полная перестройка (~5 вызовов API
-- на NPC), которую Gov.run записывает позвавшему модулю. Сканы по снимку Traces/Self/Stock идут только в первом кадре общего «такта»
-- floor(os.clock() / SNAP_BEAT): все три модуля зовут снимок в одном кадре и делят одну перестройку (было: каждый скан в своём кадре).
-- Период скана округляется до целого числа тактов n (вверх), скан идёт в тактах с номером, кратным n: у Traces/Self/Stock кратные такты
-- совпадают, а не расходятся по фазе (lost 5 с -> 6 с, dead 4 -> 6, loot 6, prices 20 -> 21; Self 3 -> каждый такт).
local SNAP_BEAT = 3
-- Такт нужен только в игре: там снимок живёт кадр. Офлайн-заглушка без getTimeStamp — снимок живёт ttl, делить нечего, расписание прежнее.
local STAMP, stamp_t = nil, -1e9
local function stamp_mode()   -- true: есть метка кадра (игра); нет — повторная проверка не чаще раза в 10 с
  if STAMP then return true end
  local now = os.clock()
  if now - stamp_t < 10 and now >= stamp_t then return false end
  stamp_t = now
  local ok, v = pcall(function() return getGameWorld():getTimeStamp() end)
  STAMP = (ok and type(v) == "number") or nil
  return STAMP == true
end
local function beat_due(beat, period)
  local n = math.max(1, math.ceil(((period or SNAP_BEAT) - 0.5) / SNAP_BEAT))
  return beat % n == 0
end
-- Торговый ли отряд и его шаблон — свойства платуна, не персонажа: кэш по ключу платуна на сессию вместо getIsTrader/squadTemplate
-- у каждого NPC в каждом скане. Значение кладётся и в запись снимка (rawset): другие модули в том же кадре не зовут API повторно.
local PKC, npkc = {}, 0
local function pkf(r, f)
  local v = rawget(r, f)
  if v ~= nil then return v end
  local k = r.pkey
  local e = (k and k ~= "") and PKC[k] or nil
  if e and e[f] ~= nil then rawset(r, f, e[f]); return e[f] end
  v = r[f]   -- ленивое поле записи: один вызов API, ошибка -> false
  if k and k ~= "" then
    if not e then
      if npkc >= 2000 then PKC, npkc = {}, 0 end
      e = {}; PKC[k] = e; npkc = npkc + 1
    end
    e[f] = v
  end
  return v
end

---------------------------------------------------------------------------------------------- спавн только вне видимости игрока
-- Точка допустима, если до КАЖДОГО персонажа игрока >= unseen_min (за пределами обзора) и до ближайшего <= unseen_max (область загружена).
-- До unseen_tries кандидатов; допустимой нет -> nil (вызывающий откладывает, а не спавнит ближе). Проверки загруженности точки в KenshiLua нет
-- (isLoaded/getHeight - методы объектов, не точек), поэтому только расстояние.
local function pc_xz()
  local out = {}
  pcall(function()
    for _, c in pairs(getPlayerInterface():getAllPlayerCharacters()) do
      local x, z = xz(c:getPosition()); if x then out[#out + 1] = { x, z } end
    end
  end)
  return out
end
local function unseen_ok(x, z, pcs)
  if not (x and z) or #pcs == 0 then return false end
  local mn, mx = (P and P.unseen_min) or 3500, (P and P.unseen_max) or 6000
  local near
  for _, p in ipairs(pcs) do
    local d = dist(x, z, p[1], p[2])
    if d < mn then return false end
    if not near or d < near then near = d end
  end
  return near <= mx
end
local function pick_unseen(pcs, gen)   -- gen(i) -> x, z кандидата
  for i = 1, (P and P.unseen_tries) or 8 do
    local x, z = gen(i)
    if x and unseen_ok(x, z, pcs) then return x, z end
  end
end
local function ring_gen(pcs)   -- кольцо вокруг персонажей игрока (по кругу)
  local mn, mx = (P and P.unseen_min) or 3500, (P and P.unseen_max) or 6000
  return function(i)
    local p = pcs[((i - 1) % #pcs) + 1]
    local a, r = math.random() * 2 * math.pi, mn + 150 + math.random() * math.max(1, mx - mn - 300)
    return p[1] + r * math.cos(a), p[2] + r * math.sin(a)
  end
end
local function line_gen(pcs, tx, tz)   -- вдоль направления от игрока к цели (tx,tz), веер +-50 градусов
  local mn, mx = (P and P.unseen_min) or 3500, (P and P.unseen_max) or 6000
  return function(i)
    local p = pcs[((i - 1) % #pcs) + 1]
    local base = math.atan2(tz - p[2], tx - p[1]) + (math.random() - 0.5) * 1.7
    local r = mn + 150 + math.random() * math.max(1, mx - mn - 300)
    return p[1] + r * math.cos(base), p[2] + r * math.sin(base)
  end
end
local function pick_any(pcs) return pick_unseen(pcs, ring_gen(pcs)) end
local function jit(x, z, j, pcs)   -- сдвиг +-j, если точка остаётся допустимой, иначе без сдвига
  local nx, nz = x + math.random(-j, j), z + math.random(-j, j)
  if unseen_ok(nx, nz, pcs) then return nx, nz end
  return x, z
end

---------------------------------------------------------------------------------------------- инициализация
local function init()
  if TR then return true end
  C = KMM_Conductor
  if not (C and C.cfg) then return false end
  CFG = C.cfg()
  if not (CFG and CFG.params) then return false end
  P = CFG.params.traces or {}
  TR = C.read_json("traces.json", "C:/KenshiModMap/build/KMM_Conductor/traces.json") or { factions = {}, caravans = {}, dead_caravan_sids = {} }
  TR.dead = {}
  for _, sid in ipairs(TR.dead_caravan_sids or {}) do TR.dead[sid] = true end
  local n = 0; for _ in pairs(TR.factions or {}) do n = n + 1 end
  log(string.format("loaded: %d factions with trace squads, %d caravan templates, enabled=%s", n, #(TR.dead_caravan_sids or {}), tostring(P.enabled)))
  return true
end

---------------------------------------------------------------------------------------------- тиры и выбор отряда
local tier_stats = { picks = 0, know_up = 0, gear_down = 0 }
local function know_bonus(fid)   -- высокое знание фракции: ступень выше (если такой шаблон есть)
  local ok, k = pcall(function() return C.know and C.know(fid) end)
  return (ok and (k or 0) >= (P.know_tier_hi or 1.5)) and 1 or 0
end
-- shift == nil: сдвиг дирижёра (богатство, ржавчина, дефицит брони/оружия gear_shift -1) + знание.
-- shift задан и adj: заданный сдвиг + знание + дефицит снаряжения (gear_shift < 0); без adj — как есть (-9 = самый бедный тир).
local function tier_sid(fid, shift, adj)
  local e = TR.factions[fid]
  if not e then return nil end
  local sh, gear = shift, 0
  if sh == nil then sh = C.tier_shift(fid) or 0
  elseif adj then
    local okg, g = pcall(function() return (C.state().F[fid].gear_shift or 0) end)
    gear = (okg and g < 0) and -1 or 0; sh = sh + gear
  end
  local kb = (shift == nil or adj) and know_bonus(fid) or 0
  local base = TIDX[e.base_tier or "T0"]
  local want0 = math.max(1, math.min(4, base + sh))
  local want = want0
  if kb > 0 then
    local w1 = math.max(1, math.min(4, base + sh + kb))
    if w1 ~= want0 and e.tiers[TIERS[w1]] then want = w1 end
  end
  tier_stats.picks = tier_stats.picks + 1
  if want ~= want0 then tier_stats.know_up = tier_stats.know_up + 1 end
  if gear < 0 then tier_stats.gear_down = tier_stats.gear_down + 1 end
  for d = 0, 3 do   -- ближайший существующий тир, вниз в первую очередь
    for _, k in ipairs({ want - d, want + d }) do
      if TIERS[k] and e.tiers[TIERS[k]] then return e.tiers[TIERS[k]], TIERS[k] end
    end
  end
  return nil
end

local stats = { spawned = 0, by_kind = {} }
local function null_hand()   -- в игре createRandomSquad требует hand (nil -> "KenshiLua.hand expected", лог 2026-11-12); конструктора нет.
  -- getCarryingObject/getMySlaveOwner возвращают hand ПО ЗНАЧЕНИЮ (копия) — её можно обнулить. getHandle() отдаёт const& — его не трогать.
  for _, c in pairs(getPlayerInterface():getAllPlayerCharacters()) do
    for _, m in ipairs({ "getCarryingObject", "getMySlaveOwner" }) do
      local ok, h = pcall(function() return c[m](c) end)
      if ok and h then pcall(function() h:setNull() end); return h end
    end
  end
  return nil
end
-- нет шаблона отряда (sid пуст или не найден в gamedata) -> nil без вызова движка: createRandomSquad с nil 6-м аргументом в игре даёт
-- «bad argument #6» и выключает весь спавн до перезапуска. Вызывающий видит nil (do_job: «notemplate», задание снято без счёта спавна).
local function spawn(fid, squad_sid, x, y, z, maxnum, target_handle, target_town)
  local gw = getGameWorld()
  local gd = squad_sid and gw.gamedata:getData(squad_sid, SQUAD_TYPE) or nil
  if gd == nil then
    stats.no_template = (stats.no_template or 0) + 1
    if stats.no_template <= 20 then dlog(string.format("spawn skipped: no squad template for %s (sid %s)", tostring(fid), tostring(squad_sid))) end
    return nil
  end
  if target_handle == nil then target_handle = null_hand(); if target_handle == nil then error("no null hand") end end
  local fobj = gw.factionMgr:getFactionByStringID(fid)
  if not fobj then error("no faction object " .. tostring(fid)) end
  stats.spawn_calls = (stats.spawn_calls or 0) + 1
  return gw.theFactory:createRandomSquad(fobj, { x = x, y = y, z = z }, nil, maxnum or 5, nil, gd, nil, nil, nil, false,
                                         target_handle, target_town, 1.0, 2, false)
end


-- NATIVE2 (2026-11-13): крэш-сторож нативного вызова (pcall не ловит краш): lock до первого вызова, снимается после успеха; lock при старте = прошлая сессия упала -> .off навсегда.
local PROBE = {}
local function probe_call(x, fn)
  local sd = "C:/KenshiModMap/state/"
  local lock, offp = sd .. "probe_" .. x .. ".lock", sd .. "probe_" .. x .. ".off"
  if PROBE[x] == nil then
    PROBE[x] = true
    pcall(function()
      local f = io.open(offp, "r")
      if f then f:close(); PROBE[x] = false; return end
      f = io.open(lock, "r")
      if f then
        f:close(); PROBE[x] = false
        local o = io.open(offp, "w"); if o then o:write("disabled: previous session crashed in ", x); o:close() end
        os.remove(lock)
        dlog("native method " .. x .. " DISABLED forever: previous session crashed during the call (state/probe_" .. x .. ".off)")
        h_off("KMM_Traces.native_" .. x, "previous session crashed in " .. x, "crash")
      end
    end)
  end
  if not PROBE[x] then return false end
  local first = not PROBE[x .. "#done"]
  if first then pcall(function() local f = io.open(lock, "w"); if f then f:write(tostring(os.time())); f:close() end end) end
  local ok = pcall(fn)
  if first then pcall(os.remove, lock); PROBE[x .. "#done"] = true end
  return ok
end
-- родной дом беженцам: Ownerships:setHomeTown(город назначения, SQ_RESIDENT) - движок сам ведёт и поселяет отряд
local function settle(pl, tt)
  if not (pl and tt) then return false end
  local R = (P and P.refugee_home)
  if R == false then return false end
  local sq = rawget(_G, "SquadType"); sq = sq and sq.SQ_RESIDENT
  if sq == nil then return false end
  return probe_call("setHomeTown", function() pl:getOwnerships():setHomeTown(tt, sq) end)
end

local function town_of(fid, x, z)   -- ближайший город фракции к точке (цель марша); nil — без цели
  local ok, t = pcall(function()
    local f = getGameWorld().factionMgr:getFactionByStringID(fid)
    return f and f.warMgr and f.warMgr:getNearestTown({ x = x, y = 0, z = z })
  end)
  return ok and t or nil
end

---------------------------------------------------------------------------------------------- очередь следов
local Q, recent = {}, {}
local last_spawn, day_key, day_count = -1000, -1, 0
local EXTB = { day = -1, n = 0, tag = {} }   -- EXT-бюджет внешних модулей
local function day_roll()   -- дневной лимит общий для следов, видимых событий и засад: сброс при любой смене дня
  local dk = math.floor(C.state().last_day or 0)
  if dk ~= day_key then day_key, day_count = dk, 0 end
end
local function enqueue(job)
  if #Q >= (P.max_queue or 12) then table.remove(Q, 1) end
  job.qt = job.qt or os.clock()
  Q[#Q + 1] = job
end

-- PACE (2026-11-14, по итогам плейтеста о пропорциях): единый ритм видимого у игрока. Очередь выбирает не «кто первый», а лучший по
-- счёту = приоритет класса + «давно не виденное» (дни с прошлого спавна этого тега) + ожидание в очереди. Враждебные встречи разведены
-- паузой hostile_gap_seconds (критические — рейд на базу, штурм — без паузы). Засуха (нет спавнов drought_seconds) ослабляет EXT-лимит.
local PACE = { seen = {}, last_host = -1e9, n = { critical = 0, story = 0, hostile = 0, ambient = 0 }, waited_host = 0, drought = 0 }
PACE.CLASS = { base_raid = "critical", siege_storm = "critical", siege_defenders = "critical", siege_besiegers = "story",
  outlaw = "story", fate = "story", relic_champ = "story", relic_exp = "story", manhunt = "story", veteran = "story", bounty_hunters = "story",
  slave_caravan = "story", elite = "story", predator_ambush = "hostile", herd_pred = "hostile", ambush = "hostile", waylay = "hostile",
  nemesis = "story", bounty = "story", bounty_hunt = "story", rescue = "story",   -- PACE2: соперник игрока и охота за головой — сюжет, враждебные (пауза между встречами)
  debt = "critical" }   -- PACE2: должник бежит на помощь в идущем бою — без очереди и паузы
PACE.PRIO = { critical = 100, story = 30, hostile = 15, ambient = 10 }
function PACE.tag(job) return job.tag or job.why or job.kind or "?" end
function PACE.class(job) return PACE.CLASS[PACE.tag(job)] or PACE.CLASS[job.kind or ""] or "ambient" end
PACE.HOSTILE_TAG = { outlaw = true, nemesis = true, bounty = true, bounty_hunt = true, rescue = true }
function PACE.hostile(job) if PACE.tag(job) == "ally_dispatch" then return false end; local c = PACE.class(job); return c == "hostile" or job.target == "player" or PACE.HOSTILE_TAG[PACE.tag(job)] == true end
function PACE.stale(tag)   -- игровых дней с прошлого спавна тега (не было — 3)
  local d = (C.state() and C.state().last_day) or 0
  local t = PACE.seen[tag]
  return t and math.max(0, d - t) or 3
end
function PACE.score(job, now)
  local c = PACE.class(job)
  return PACE.PRIO[c] + math.min(40, PACE.stale(PACE.tag(job)) * 10) + math.min(10, (now - (job.qt or now)) / 30)
end
-- Ворота силы и богатства (общее правило, не тип старта): задание с poor_gate ждёт, пока отряд игрока нищ и слаб
-- (KMM_Nemesis.poor: деньги, цена вещей, награда ядра, прозвище, численность, навык — ванильные числа). Нет Nemesis -> не ждёт.
function PACE.poor()
  local NM = rawget(_G, "KMM_Nemesis")
  if not (NM and NM.poor) then return false end
  local ok, v = pcall(NM.poor)
  return ok and v == true
end
-- свой игрока лежит (ванильные isDown/isUnconcious): метка ko_t; враждебная встреча не раньше hostile_after_ko_seconds после того,
-- как последний раз видели лежащего (нокаут длиннее hostile_gap — без цепочки нокаутов)
function PACE.ko_step(now)
  local down = false
  pcall(function()
    for _, c in pairs(getPlayerInterface():getAllPlayerCharacters()) do
      local ok, d = pcall(function() return c:isDown() or c:isUnconcious() end)
      if ok and d == true then down = true; break end
    end
  end)
  if down then
    if not PACE.ko_t or now - PACE.ko_t > (P.hostile_after_ko_seconds or 300) then dlog("PACE: player squad down - hostile encounters wait") end
    PACE.ko_t = now
  end
  return down
end
function PACE.blocked(job, now)   -- враждебная встреча слишком скоро после прошлой (или пока отряд игрока нищ и слаб — для poor_gate)
  if job.poor_gate and PACE.poor() then PACE.waited_poor = (PACE.waited_poor or 0) + 1; return true end
  if PACE.class(job) == "critical" or not PACE.hostile(job) then return false end
  if PACE.ko_t and now >= PACE.ko_t and now - PACE.ko_t < (P.hostile_after_ko_seconds or 300) then PACE.waited_ko = (PACE.waited_ko or 0) + 1; return true end
  return now - PACE.last_host < (P.hostile_gap_seconds or 600)
end
-- ПОДПИСЬ И ВЕСТНИК (B1 V1): отряд следа подписан по сути (ActivePlatoon:setName — подпись на карте и над головами), вожак беженцев,
-- колонны, гонца, каравана, патруля, освобождённых один раз говорит строку о своём деле (Character:say), когда игрок подойдёт на herald_r.
-- Вожак хранится как указатель не дольше herald_ttl_seconds и трогается только пока он в живом наборе движка
-- (getCharacterUpdateList():has — без разыменования); проверить нечем -> вестники выключены, подписи остаются.
PACE.HER = {}
function PACE.clean(n) if type(n) == "string" and n ~= "" and not n:find("[\128-\255%(%)%d]") then return n end end
function PACE.fname(fid) local ok, n = pcall(C.name, fid); return (ok and PACE.clean(n)) or nil end
function PACE.tname(sid, fallback)
  local I = sid and CFG.town_info and CFG.town_info[sid]
  return (I and PACE.clean(I.name)) or PACE.clean(fallback)
end
PACE.LINES = {
  refugees = { "We left with what we could carry.", "%s is lost to us. We carry what we could.", "Do not go towards %s. There is nothing left there.", "We had homes near %s. Now we have this road." },
  column = { "We march on %s. Stay off the road.", "War with %s. Keep clear, stranger." },
  courier = { "Word for the garrisons. Out of my way.", "Urgent news for %s. Move." },
  caravan = { "Goods for the market. Keep your hands to yourself.", "Long road, thin margins. Don't make it longer." },
  garrison = { "Trouble in town. Move along.", "Orders from %s. Nobody loiters here." },
  freed = { "We were in chains until yesterday.", "Free. Thanks to %s. Never again." },
}
function PACE.label(pl, kind, fid, ex)   -- подпись отряда + вестник; ex: { town = имя, enemy = fid, ev = id }
  if not pl or P.trace_names == false then return end
  ex = ex or {}
  local fn = PACE.fname(fid) or "Travelling"
  local nm, lk, arg
  if kind == "refugees" then nm = ex.town and ("Refugees from " .. ex.town) or (fn .. " refugees"); lk, arg = "refugees", ex.town
  elseif kind == "column" then local en = ex.enemy and PACE.fname(ex.enemy); nm = en and (fn .. " column against " .. en) or (fn .. " war column"); lk, arg = en and "column", en
  elseif kind == "garrison" then nm = fn .. " patrol"; lk, arg = "garrison", fn
  elseif kind == "band" then nm = fn .. " band"
  elseif kind == "slave_caravan" then nm = fn .. " slave caravan"
  elseif kind == "bounty_hunt" then nm = fn .. " bounty hunters"
  elseif kind == "courier" then nm = fn .. " courier"; lk, arg = "courier", ex.town or fn
  elseif kind == "caravan" then nm = fn .. " caravan"; lk = "caravan"
  elseif kind == "wanderer" then nm = fn .. " wanderers"
  elseif kind == "freed" then nm = fn .. " and the freed"; lk, arg = "freed", fn
  elseif kind == "expedition" then nm = fn .. " expedition"
  elseif kind == "smugglers" then nm = fn .. " smugglers"
  end
  if not nm then return end
  local okn = pcall(function() pl:getActivePlatoon():setName(nm) end)
  stats.named = (stats.named or 0) + (okn and 1 or 0)
  if not okn then stats.name_fail = (stats.name_fail or 0) + 1 end
  if lk and PACE.LINES[lk] and P.heralds ~= false and not PACE.her_off and #PACE.HER < (P.herald_max or 6) then
    local okl, leader = pcall(function() return pl:getSquadLeader() end)
    if okl and leader then
      local fmt = PACE.LINES[lk][math.random(#PACE.LINES[lk])]
      if fmt:find("%s", 1, true) and not arg then fmt = PACE.LINES[lk][1]; if fmt:find("%s", 1, true) then fmt = nil end end
      if fmt then
        PACE.HER[#PACE.HER + 1] = { ch = leader, line = fmt:find("%s", 1, true) and string.format(fmt, arg) or fmt, kind = kind, ev = ex.ev,
                                    t1 = os.clock() + (P.herald_ttl_seconds or 900), nm = nm }
      end
    end
  end
end
function PACE.herald_step(px, pz, now)
  if #PACE.HER == 0 or PACE.her_off then return end
  local okS, set = pcall(function() return getGameWorld():getCharacterUpdateList() end)
  local keep = {}
  for _, h in ipairs(PACE.HER) do
    if now < h.t1 and now >= h.t1 - (P.herald_ttl_seconds or 900) - 1 then
      local okh, live = false, nil
      if okS and set then okh, live = pcall(function() return set:has(h.ch) end) end
      if not okh or type(live) ~= "boolean" then
        PACE.her_off = true; PACE.HER = {}
        dlog("herald off until restart: no liveness check (getCharacterUpdateList has unavailable) - names stay, lines off")
        return
      end
      if live then
        local okp, x, z = pcall(function() local p = h.ch:getPosition(); return p.x, p.z end)
        local okd, gone = pcall(function() return h.ch:isDead() or h.ch:isDown() end)
        if okp and x and okd and not gone then
          if dist(px, pz, x, z) <= (P.herald_r or 700) then
            local oks = pcall(function() h.ch:say(h.line) end)
            if not oks then oks = pcall(function() h.ch:sayALine(h.line, true) end) end
            stats.herald = (stats.herald or 0) + (oks and 1 or 0)
            dlog(string.format("herald said: kind=%s event=%s squad=%s ok=%s line=%s", h.kind, tostring(h.ev), h.nm, tostring(oks), h.line))
          else keep[#keep + 1] = h end
        end
      end
    end
  end
  PACE.HER = keep
end
function PACE.took(job, now)
  local tag = PACE.tag(job)
  PACE.seen[tag] = (C.state() and C.state().last_day) or 0
  local c = PACE.class(job)
  PACE.n[c] = (PACE.n[c] or 0) + 1
  if PACE.hostile(job) then PACE.last_host = now end
end

local function event_xz(ev)
  local I = ev.town_sid and CFG.town_info and CFG.town_info[ev.town_sid]
  if I and I.x then return I.x, I.z end
  if ev.town_sid then for _, st in ipairs(CFG.sites or {}) do if st.sid == ev.town_sid then return st.x, st.z end end end   -- 2026-11-13: без town_sid nil==nil ловил первый сайт без sid
  for _, k in ipairs({ "b", "a", "fid" }) do   -- 2026-11-13: ipairs по {ev.b, ev.a} обрывался на первом nil (событие без b терял a)
    local fid = ev[k]
    if fid then local x, z = C.fpos(fid); if x then return x, z end end
  end
end

local function plat_key(pl) local ok, k = pcall(function() return pl:getPlatoonStringID() end); return ok and k or nil end

---------------------------------------------------------------------------------------------- U1: родные отряды движка
-- После createRandomSquad отряд получает ванильный AI_PACKAGE под свой вид (Blackboard:replaceAIPackage): к цели (targetTown/AItarget
-- фабрики) его ведёт ядро, вне экрана — по UnloadedPlatoonJob пакета. Временный отряд после прибытия по-прежнему тихо убирается вне
-- видимости, а живые временные у игрока считаются по снимку (nat_live_max); attackTarget засады остаётся (пакет враждебности не создаёт).
-- Постоянными (Platoon:setPersistentSquad) делаются только путники, которые должны дожить вне видимости: караван с грузом по плану
-- дорог и беженцы в новый город, не больше nat_persist_max записей; через nat_persist_days игровых дней отряд отпускается (снова временный,
-- ядро уберёт его при выгрузке). Реестр — ключи платунов (getPlatoonStringID) в C.state().ext.traces_nat, указателей между тактами нет.
-- Ключ не прочитан -> отряд не делается постоянным; «потерян» — только после nat_lost_miss промахов и срока nat_orph_days (сирота
-- остаётся в лимите, пока не забыта). Любой сбой шага -> прежнее поведение (временный отряд, пакет шаблона, свой деспавн/приказ).
local NAT = { n = { pkg = 0, pkg_fail = 0, persist = 0, persist_fail = 0, released = 0, dropped = 0, arrive = 0 }, t = -1e9 }
NAT.PKG = {
  travel = "14545-gamedata.base",    -- «base- travel to target town (slow)»: цель travel to target town, вне экрана UPJOB_TRAVEL_TARGET_FAST
  refugee = "16849-gamedata.base",   -- «disband / refugee»: SIG_REFUGEE_DISBAND, travel to mission target, вне экрана TRAVEL_TARGET_FAST
  wander = "2675-gamedata.base",     -- «Wandering from town to town»: wandering trader, SIG_WANDERING_TOWN_TO_TOWN, UPJOB_TRAVEL_TARGET
  assault = "2957-gamedata.base",    -- «Assault target squad»: SIG_DEFEAT_SQUAD, цель = AItarget фабрики
}
NAT.EXT = { siege_besiegers = "travel", siege_storm = "travel", siege_defenders = "travel" }   -- заявки T.request: пакет по тегу (иначе job.pkg)
function NAT.cfg(k, d) local v = P and P["nat_" .. k]; if v == nil then return d end; return v end
function NAT.reg()
  local S = C.state()
  S.ext = S.ext or {}
  local R = S.ext.traces_nat
  if type(R) ~= "table" then R = { L = {} }; S.ext.traces_nat = R end
  R.L = R.L or {}
  return R
end
function NAT.day() local ok, d = pcall(function() return C.state().last_day or 0 end); return ok and tonumber(d) or 0 end
function NAT.pkg(pl, sid)   -- true, имя текущего пакета | false, причина
  local gd, board
  pcall(function() gd = getGameWorld().gamedata:getData(sid, (rawget(_G, "itemType") and itemType.AI_PACKAGE) or 72) end)
  if not gd then return false, "no AI_PACKAGE data" end
  local okb, b = pcall(function() return pl:getBlackboard() end)
  if okb then board = b end
  if not board then return false, "no blackboard" end
  if not probe_call("ai_package", function() board:replaceAIPackage(gd) end) then return false, "replaceAIPackage failed" end
  local okn, nm = pcall(function() return board:getCurrentAIPackageName() end)
  return true, tostring(okn and nm or "?")
end
function NAT.persist(pl, fid, kind)   -- ключ платуна | nil, причина
  local R = NAT.reg()
  if #R.L >= NAT.cfg("persist_max", 4) then return nil, "cap " .. #R.L end
  local k = plat_key(pl)
  if not (type(k) == "string" and k ~= "") then return nil, "no platoon key (could not find it again)" end
  if not probe_call("persist", function() pl:setPersistentSquad(true) end) then return nil, "setPersistentSquad failed" end
  local okv, v = pcall(function() return pl:isPersistentSquad() end)
  if not (okv and v == true) then
    pcall(function() pl:setPersistentSquad(false) end)   -- полупостоянный не оставлять
    return nil, "isPersistentSquad " .. tostring(v)
  end
  R.L[#R.L + 1] = { k = k, f = fid, kind = kind, d = NAT.day() }
  return k
end
-- pl: платун от spawn; pk: ключ NAT.PKG или sid пакета (nil — пакет шаблона); persist: просить постоянный отряд.
-- -> true, если отряд ведёт ядро (пакет поставлен или отряд постоянный); второе значение — ключ постоянного отряда.
function NAT.apply0(pl, kind, fid, pk, persist)
  if not pl or NAT.cfg("enabled", true) == false then return false end
  local parts, led, key = {}, false, nil
  local sid = pk and (NAT.PKG[pk] or pk)
  if sid and NAT.cfg("pkg", true) ~= false then
    local ok, why = NAT.pkg(pl, sid)
    if ok then led = true; NAT.n.pkg = NAT.n.pkg + 1; parts[#parts + 1] = "pkg ok " .. sid .. " (current " .. why .. ")"
    else NAT.n.pkg_fail = NAT.n.pkg_fail + 1; parts[#parts + 1] = "pkg FAIL " .. sid .. ": " .. why .. " - template package as before" end
  end
  if persist and NAT.cfg("persist", true) ~= false then
    local k, why = NAT.persist(pl, fid, kind)
    if k then
      led, key = true, k; NAT.n.persist = NAT.n.persist + 1
      parts[#parts + 1] = string.format("persistent ok key %s (%d/%d): engine keeps the squad off-screen", k, #NAT.reg().L, NAT.cfg("persist_max", 4))
    else NAT.n.persist_fail = NAT.n.persist_fail + 1; parts[#parts + 1] = "persistent FAIL " .. tostring(why) .. " - temporary squad as before" end
  end
  if led and not key then NAT.track(pl) end   -- временный под пакетом ядра: в счёт живых у игрока
  if #parts > 0 then dlog(string.format("native %s %s: %s", kind, tostring(fid), table.concat(parts, "; "))) end
  return led, key
end
function NAT.apply(...)   -- ошибка шага не ломает спавн: отряд остаётся временным с пакетом шаблона
  local ok, led, key = pcall(NAT.apply0, ...)
  if ok then return led, key end
  NAT.n.pkg_fail = NAT.n.pkg_fail + 1; dlog("native error: " .. tostring(led) .. " - temporary squad as before")
  return false
end
function NAT.find(x)   -- платун, загружен?, фракция найдена? (nil, nil, true — фракция есть, ключа нет ни в одном списке)
  local fo
  pcall(function() fo = getGameWorld().factionMgr:getFactionByStringID(x.f) end)
  if not fo then return nil, nil, false end
  local cap = NAT.cfg("scan", 1500)
  local listed = false
  for _, m in ipairs({ "getActivePlatoons", "getUnloadedPlatoons" }) do
    local ok, lst = pcall(function() return fo[m](fo) end)
    local n = 0
    if ok and lst then listed = true; pcall(function() n = #lst end) end
    for i = 1, math.min(n, cap) do
      local p = lst[i]
      if p and plat_key(p) == x.k then return p, m == "getActivePlatoons", true end
    end
  end
  return nil, nil, listed
end
function NAT.has(k)   -- ключ — постоянный отряд из реестра U1
  if not k then return false end
  local ok, R = pcall(NAT.reg)
  if not ok then return false end
  for _, x in ipairs(R.L) do if x.k == k then return true end end
  return false
end
-- раз в nat_step_seconds одна запись реестра (по кругу): погиб/исчез -> место в лимите свободно сразу; срок вышел -> отпустить,
-- но только загруженный платун (ядро проверяет постоянство при выгрузке); выгруженный ждёт подгрузки с пометкой due
function NAT.step()
  local now = os.clock()
  if now - NAT.t < NAT.cfg("step_seconds", 60) then return end
  NAT.t = now
  local R = NAT.reg()
  local x = table.remove(R.L, 1)
  if not x then return end
  local d = NAT.day()
  local age = d - (x.d or d)
  local p, loaded, fac = NAT.find(x)
  if p then
    x.miss = nil
    local okd, dead = pcall(function() return p.isDead end)   -- у выгруженного платуна персонажей нет: верим только флагу isDead
    if okd and dead == true then NAT.n.dropped = NAT.n.dropped + 1; dlog(string.format("native release %s key %s: squad is dead - slot freed", tostring(x.kind), x.k)); return end
    if age >= NAT.cfg("persist_days", 3) then
      if loaded then
        local ok = probe_call("persist", function() p:setPersistentSquad(false) end)
        NAT.n.released = NAT.n.released + 1
        dlog(string.format("native release %s key %s after %.1f days: %s", tostring(x.kind), x.k, age, ok and "ok (temporary again)" or "FAIL"))
        return
      end
      if not x.due then x.due = true; dlog(string.format("native release %s key %s deferred: squad unloaded, released when it loads", tostring(x.kind), x.k)) end
    end
    R.L[#R.L + 1] = x
    return
  end
  x.miss = (x.miss or 0) + 1   -- один промах — не потеря (переход active<->unloaded)
  if fac and x.miss >= NAT.cfg("lost_miss", 3) then   -- фракция отдала списки, ключа нет lost_miss раз подряд: отряд уничтожен
    NAT.n.dropped = NAT.n.dropped + 1
    dlog(string.format("native lost %s key %s: not in faction lists %d times - slot freed", tostring(x.kind), x.k, x.miss))
  elseif not fac and x.miss >= NAT.cfg("lost_miss", 3) and age >= NAT.cfg("persist_days", 3) + NAT.cfg("orph_days", 30) then
    NAT.n.dropped = NAT.n.dropped + 1
    dlog(string.format("native orphan dropped %s key %s: faction not found %d times in %.0f days", tostring(x.kind), x.k, x.miss, age))
  else R.L[#R.L + 1] = x end   -- в конец: следующие записи тоже проверяются
end
-- временные отряды под пакетом ядра у игрока: живые считаются по снимку (ключ платуна), лимит nat_live_max — до него новых спавнов нет
NAT.tmp, NAT.alive = {}, 0
function NAT.track(pl)
  local k = plat_key(pl)
  if not (type(k) == "string" and k ~= "") then return end
  if #NAT.tmp >= 40 then table.remove(NAT.tmp, 1) end
  NAT.tmp[#NAT.tmp + 1] = { k = k, t = os.clock() }
end
function NAT.count(info)   -- info: kinfo(snap); не виден в снимке nat_gone_seconds — ядро выгрузило/убрали
  local now, n = os.clock(), 0
  for i = #NAT.tmp, 1, -1 do
    local e = NAT.tmp[i]
    local x = info[e.k]
    if x and x.alive > 0 then e.seen = now; n = n + 1
    elseif now - (e.seen or e.t) > NAT.cfg("gone_seconds", 120) then table.remove(NAT.tmp, i) end
  end
  NAT.alive = n
  return n
end
function NAT.full() return NAT.alive >= NAT.cfg("live_max", 8) end

---------------------------------------------------------------------------------------------- ROADS: путники с целью (откуда-куда-зачем)
-- План пути даёт дирижёр (C.road_plan): беженцы - в ближайший сытый город, караван - в город с дефицитом груза, бродяги - в бар богатого города,
-- гонцы - между городами фракции. Спавн только через общую очередь (лимиты Traces) и pick_unseen. Прибытие/выход из загруженной зоны: тихий деспавн
-- вне видимости и зачёт чисел в дирижёре (C.road_arrive); гибель в пути - груз потерян (C.road_lost).
local function RP() return (CFG and CFG.params and CFG.params.roads) or {} end
local function roads_on(k) local R = RP(); return R.enabled ~= false and (k == nil or R[k] ~= false) and C ~= nil and C.road_plan ~= nil end
local TRV = {}   -- живые путники: { kind, fid, key, sx, sz, tx, tz, from, to, id, t0, d0, seen, lx, lz, ls }
local function dest_xz(to) local I = to and CFG.town_info and CFG.town_info[to]; if I and I.x then return I.x, I.z end end
local function dest_town(plan, fid)   -- объект города назначения для createRandomSquad (nil - без цели)
  if not plan then return nil end
  local x, z = dest_xz(plan.to)
  if not x then return nil end
  return town_of(plan.owner or fid, x, z) or town_of(fid, x, z)
end
local function trv_register(kind, fid, pl, sx, sz, plan, id, tx, tz, nat)   -- nat: отряд ведёт ядро (U1) — без своего деспавна
  if pl == nil then return end   -- спавна не было (нет шаблона): путника без отряда не заводим
  if #TRV >= (RP().max_live or 6) then table.remove(TRV, 1) end
  if not tx then tx, tz = dest_xz(plan and plan.to) end
  TRV[#TRV + 1] = { kind = kind, fid = fid, key = pl and plat_key(pl) or nil, sx = sx, sz = sz, tx = tx, tz = tz, from = plan and plan.from, to = plan and plan.to,
                    id = id, t0 = os.clock(), d0 = tx and dist(sx, sz, tx, tz) or nil, nat = nat or nil }
end
local GARRISON_OF = { town_captured = "a", revolt = "a", town_rejoined = "a", stronghold_hire = "a" }   -- GOALS: оплот нанял охрану при угрозе   -- REV2: новый хозяин города (захват, мятеж к прежнему, вольный город вернулся) ставит гарнизон
local REFUGEE_FROM = { town_captured = "b", revolt = "b", famine = "a", famine_refugees = "a", faction_fell = "a", mine_exhausted = "a", succession_crisis = "a",
                       slave_raid = "b", chaos_cult = "b" }
local COLUMN_OF = { raid = "a", attack_repelled = "a", town_captured = "a", mobilized = "a", warlord_rose = "a", faction_split = "a",
                    betrayal = "a", ally_help = "a", base_raid = "a", joint_raid = "a", ruin_expedition = "a", chaos_cult = "a", elite_hunger = "a" }
local CARAVAN_OF = { raid = "b", theft = "b", slave_raid = "b", black_market = "b" }   -- VASSALS: караван покупателя у чёрного рынка

local function on_event(ev, px, pz)
  if ev.native == true and ev.type ~= "base_raid" then stats.native_skip = (stats.native_skip or 0) + 1; return end   -- CAMPAIGN: атаку ведёт родная кампания движка — своя колонна/беженцы для этой пары не нужны
  local ex, ez = event_xz(ev)
  if not ex and ev.type == "mobilized" and ev.a then   -- ROADS: у фракции нет центра - берём любой её город
    for _, t in ipairs(C.towns()) do if t.owner == ev.a and t.x then ex, ez = t.x, t.z; break end end
  end
  if not ex then return end
  local d = dist(px, pz, ex, ez)
  local R = P.radius or 70000
  if ev.type == "base_raid" then d = 0 end   -- рейд на базу игрока материализуется у него всегда
  if d > R then return end
  local rf = REFUGEE_FROM[ev.type] and ev[REFUGEE_FROM[ev.type]]
  if rf and TR.factions[rf] and TR.factions[rf].refugees then
    enqueue({ kind = "refugees", fid = rf, ev = ev.id, tx = ex, tz = ez, why = ev.type, sid = ev.town_sid })
  end
  local cf = COLUMN_OF[ev.type] and ev[COLUMN_OF[ev.type]]
  if cf and TR.factions[cf] then
    local target = (ev.type == "base_raid") and "player" or ev.b
    enqueue({ kind = (ev.type == "base_raid") and "base_raid" or "column", fid = cf, enemy = target, ev = ev.id, tx = ex, tz = ez, why = ev.type, day = ev.day })
  end
  if ev.type == "mobilized" and ev.a and TR.factions[ev.a] and roads_on("couriers") then   -- ROADS: перед большой войной - гонцы между городами фракции
    local dup = false
    for _, j in ipairs(Q) do if j.kind == "courier" and j.fid == ev.a then dup = true end end
    if not dup then enqueue({ kind = "courier", fid = ev.a, ev = ev.id, why = "mobilized" }) end
  end
  if ev.type == "slave_caravan" then   -- SLAVES (Tempo): рабы вымерли от голода -> работорговцы везут новых к хозяину
    local sf = (ev.fid and TR.factions[ev.fid] and TR.caravans[ev.fid]) and ev.fid or (P.slaver_fid or "1084-gamedata.base")
    if TR.caravans[sf] then enqueue({ kind = "slave_caravan", fid = sf, owner = ev.fid, ev = ev.id, tx = ex, tz = ez, why = ev.type }) end
  end
  local vf = CARAVAN_OF[ev.type] and ev[CARAVAN_OF[ev.type]]
  if vf and TR.caravans[vf] then enqueue({ kind = "caravan", fid = vf, ev = ev.id, why = ev.type }) end
  if ev.type == "chaos_incursion" and TR.daemons and TR.daemons.faction and #(TR.daemons.squads or {}) > 0 then
    enqueue({ kind = "daemons", ev = ev.id, fid = TR.daemons.faction, why = ev.type, squad = ev.squad })   -- LINKS2: бог по причине
  end
  if ev.type == "town_alarm" and ev.town_sid and C.town_mood then   -- LINKS2: беспорядки в городе -> патруль хозяина рядом с игроком
    local okm, m = pcall(C.town_mood, ev.town_sid)
    local of = okm and m and m.owner
    if of and TR.factions[of] and d < R * 0.5 then enqueue({ kind = "garrison", fid = of, ev = ev.id, tx = ex, tz = ez, why = ev.type }) end
  end
  local gf = GARRISON_OF[ev.type] and ev[GARRISON_OF[ev.type]]
  if gf and TR.factions[gf] and d < R * 0.5 then
    enqueue({ kind = "garrison", fid = gf, ev = ev.id, tx = ex, tz = ez, why = ev.type })
  end
end

-- пачка в тире богатства: тир фракции ближайшего к игроку города сменился → её отряды рядом сразу в новом тире
local last_tier = {}
local function tier_watch(px, pz)
  local best, bd
  for t, I in pairs(CFG.town_info or {}) do
    if I.x then local d = dist(px, pz, I.x, I.z); if not bd or d < bd then best, bd = t, d end end
  end
  if not best or bd > (P.radius or 70000) then return end
  local S = C.state()
  local owner
  for fid, f in pairs(S.F) do if f.alive and f.towns[best] then owner = fid; break end end
  if not owner or not TR.factions[owner] then return end
  local sid, tier = tier_sid(owner)
  if not sid then return end
  if last_tier[owner] and last_tier[owner] ~= tier then
    enqueue({ kind = "band", fid = owner, why = "tier " .. last_tier[owner] .. "->" .. tier, n = 2 })
  end
  last_tier[owner] = tier
end

---------------------------------------------------------------------------------------------- исполнение следа
local dead_watch = {}   -- {until, x, z} — убить разорённый караван после спавна
local BR = {}   -- REV2: живые рейдовые отряды на базу игрока { fid, keys, t0, x, z, seen }
-- BOUNTY (2026-11-13): ванильная награда за голову игрока -> охотники фракции-заказчика. Читаем Character.crimes (BountyManager):
-- _getHighestBountyFaction() -> Faction, getActualBounty(Faction) -> integer. Раз в check_hours игровых часов, без обхода мира.
local BNT = { on = true, last_chk = nil, last_hunt = nil, act = {}, n = 0 }
local function BP() local b = P and P.bounty; if type(b) ~= "table" then b = {}; if P then P.bounty = b end end; return b end
function BNT.read()   -- { [fid] = сумма наград по членам отряда игрока }
  local out = {}
  for _, c in pairs(getPlayerInterface():getAllPlayerCharacters()) do
    local ok = pcall(function()
      local bm = c.crimes
      if not bm then return end
      local hf = bm:_getHighestBountyFaction()
      if not hf then return end
      local gd = hf:getData() or hf.data
      local fid = gd and gd.stringID
      if not fid then return end
      local amt = tonumber(bm:getActualBounty(hf)) or 0
      if amt > 0 then out[fid] = (out[fid] or 0) + amt end
    end)
    if not ok then BNT.errs = (BNT.errs or 0) + 1 end
  end
  return out
end
function BNT.law_of(fid)   -- фракция-полиция заказчика: f.myLawEnforcementFaction -> stringID; nil/сам/не в traces.json -> fid
  if BP().law_enforcement == false then return fid end
  local ok, r = pcall(function()
    local f = getGameWorld().factionMgr:getFactionByStringID(fid)
    local lf = f and f.myLawEnforcementFaction
    if not lf then return nil end
    local gd = lf:getData() or lf.data
    return gd and gd.stringID
  end)
  if ok and type(r) == "string" and r ~= fid and TR.factions[r] and not (C.alive and C.alive(r) == false) then return r end
  return fid
end
function BNT.tier(amt)   -- 1..4 (T0..T3) по сумме награды
  local B = BP()
  if amt >= (B.t3 or 60000) then return 4 elseif amt >= (B.t2 or 20000) then return 3 elseif amt >= (B.t1 or 8000) then return 2 end
  return 1
end
function BNT.step()
  local B = BP()
  if B.enabled == false or not BNT.on then return end
  local d = C.state().last_day or 0
  if BNT.last_chk and d - BNT.last_chk < (B.check_hours or 4) / 24 then return end
  BNT.last_chk = d
  if BNT.last_hunt and d - BNT.last_hunt < (B.cooldown_hours or 36) / 24 then return end
  local now = os.clock()
  local n = 0
  for i = #BNT.act, 1, -1 do if now - BNT.act[i] > (B.active_seconds or 900) then table.remove(BNT.act, i) else n = n + 1 end end
  for _, j in ipairs(Q) do if j.kind == "bounty_hunt" then n = n + 1 end end
  if n >= (B.max_active or 2) then return end
  local rew = BNT.read()
  local pf = C.cfg().player_faction
  local bf, ba
  for fid, amt in pairs(rew) do
    if fid ~= pf and TR.factions[fid] and amt >= (B.threshold or 5000) and (not ba or amt > ba) then bf, ba = fid, amt end
  end
  if not bf then return end
  local okl, low = pcall(function() return C.alive and C.alive(bf) == false end)
  if okl and low then return end
  if math.random() >= (B.chance or 0.5) then return end
  BNT.last_hunt = d
  enqueue({ kind = "bounty_hunt", fid = bf, amount = ba, why = "bounty", ev = 0 })
end

local function do_job(job, px, pz, py, pc)
  -- 2026-11-15 плейтест: патруль Mongrel (Туманные о-ва) возник у Stoat — след «первого часа» планируется у места старта, а срабатывает
  -- через ~20 мин там, куда игрок ушёл. Задание с точкой планирования (ox/oz): игрок ушёл дальше first_hour_drift -> след отменён.
  if job.ox and px and dist(px, pz, job.ox, job.oz) > (P.first_hour_drift or 20000) then
    stats.skipped_drift = (stats.skipped_drift or 0) + 1
    dlog(string.format("trace %s dropped: %s - player moved %.0f from where it was planned", job.kind, tostring(job.why), dist(px, pz, job.ox, job.oz)))
    return false, "drift"
  end
  if job.kind == "column" or job.kind == "band" or job.kind == "garrison" or job.kind == "base_raid" or job.kind == "courier" or job.kind == "bounty_hunt" then   -- REV2: павшие не выходят, затаившиеся не шлют колонн
    local oka, alive = pcall(function() return C.alive and C.alive(job.fid) end)
    if oka and alive == false then stats.skipped_dead = (stats.skipped_dead or 0) + 1; return false, "dead" end
    if job.kind == "column" or job.kind == "band" then
      local okl, low = pcall(function() return C.low and C.low(job.fid) end)
      if okl and low then stats.skipped_low = (stats.skipped_low or 0) + 1; return false, "low" end
    end
  end
  local pcs = pc_xz()
  local sx, sz = pick_any(pcs)
  if not sx then return false, "nopoint" end
  local nt0, sc0 = stats.no_template or 0, stats.spawn_calls or 0
  local r = dist(px, pz, sx, sz)
  local name = (job.kind == "daemons") and "Chaos daemons" or C.name(job.fid)
  if job.kind == "refugees" then
    -- уходят к ближайшему своему городу подальше от беды (или просто прочь по дороге)
    local plan
    if roads_on("refugees") then   -- ROADS: числа уже списаны в источнике (дирижёр) - группа несёт их в ближайший сытый город
      plan = job.sid and C.road_claim("refugees", job.fid, job.sid) or nil
      if not plan then plan = C.road_plan("refugees", job.fid, { from = job.sid, x = job.tx, z = job.tz }) end
    end
    local tt = dest_town(plan, job.fid) or town_of(job.fid, px + (px - (job.tx or px)), pz + (pz - (job.tz or pz)))
    local pl = spawn(job.fid, TR.factions[job.fid] and TR.factions[job.fid].refugees, sx, py, sz, P.refugee_size or 4, nil, tt)
    settle(pl, tt)
    PACE.label(pl, "refugees", job.fid, { town = PACE.tname(job.sid), ev = job.ev })
    local led = tt and NAT.apply(pl, "refugees", job.fid, "refugee", plan ~= nil)   -- U1: ванильные беженцы идут в новый город сами
    if plan then trv_register("refugees", job.fid, pl, sx, sz, plan, plan.id, nil, nil, led) end
  elseif job.kind == "column" or job.kind == "band" or job.kind == "garrison" then
    local sid = tier_sid(job.fid)
    if not sid then return false end
    local tt
    if job.kind == "column" and job.enemy then tt = town_of(job.enemy, job.tx or px, job.tz or pz)
    elseif job.kind == "garrison" then tt = town_of(job.fid, job.tx or px, job.tz or pz) end
    local n = (job.kind == "band") and (job.n or 2) or ((job.kind == "column") and 2 or 1)
    local wplan = (job.kind == "band") and roads_on("wanderers") and C.road_wanderer(job.fid) and C.road_plan("wanderer", job.fid) or nil   -- наёмники/бродяги идут в бар богатого города
    if wplan then tt = dest_town(wplan, job.fid) or tt end
    for i = 1, n do
      local jx, jz = jit(sx, sz, 200, pcs)
      local pl = spawn(job.fid, sid, jx, py, jz, P.tier_squad_size or 5, nil, tt)
      if i == 1 then PACE.label(pl, job.kind, job.fid, { enemy = job.enemy, ev = job.ev }) end
      local led = tt and NAT.apply(pl, job.kind, job.fid, wplan and "wander" or (job.kind ~= "band" and "travel" or nil), false)   -- U1: колонна/гарнизон — к городу-цели, бродяги — по городам
      if wplan and i == 1 then trv_register("wanderer", job.fid, pl, jx, jz, wplan, C.road_depart(wplan), nil, nil, led) end
    end
  elseif job.kind == "base_raid" then
    local sid = tier_sid(job.fid)
    if not sid or not pc then return false end
    local h = pc:getHandle()
    local bx, bz = sx, sz   -- REV2: рейдеры приходят со стороны своей фракции (та же функция выбора точки вне видимости)
    local fx, fz = C.fpos(job.fid)
    if fx then local lx, lz = pick_unseen(pcs, line_gen(pcs, fx, fz)); if lx then bx, bz = lx, lz end end
    local keys = {}
    for _ = 1, 2 do
      local pl = spawn(job.fid, sid, bx, py, bz, P.tier_squad_size or 5, h, nil); local k = pl and plat_key(pl); if k then keys[#keys + 1] = k end
      NAT.apply(pl, "base_raid", job.fid, "assault", false)   -- U1: штурм цели (AItarget = персонаж игрока) ведёт ядро
    end
    if #keys == 0 and (stats.spawn_calls or 0) == sc0 then return false, "notemplate" end
    BR[#BR + 1] = { fid = job.fid, keys = keys, t0 = os.clock(), x = bx, z = bz }
    while #BR > 4 do table.remove(BR, 1) end
  elseif job.kind == "ext" then   -- EXT API (2026-11-13): заявка внешнего модуля (KMM_Fates/Relic race/Predators/Siege/Herds) через общую очередь и лимиты
    local sid = job.sid or (job.fid and tier_sid(job.fid, job.shift))
    if not sid or not job.fid then return false end
    local bx, bz = sx, sz
    if job.from_x then local lx, lz = pick_unseen(pcs, line_gen(pcs, job.from_x, job.from_z)); if lx then bx, bz = lx, lz end end
    local tt = job.to_fid and town_of(job.to_fid, job.to_x or px, job.to_z or pz) or nil
    local h = (job.target == "player" and pc) and pc:getHandle() or nil
    local pls = {}
    for _ = 1, math.max(1, math.min(job.n or 1, 3)) do
      local jx, jz = jit(bx, bz, 150, pcs)
      pls[#pls + 1] = spawn(job.fid, sid, jx, py, jz, job.size or P.tier_squad_size or 5, h, tt)
    end
    if #pls == 0 then return false, "notemplate" end   -- заказчику не отдаём пустой список
    local xpk = job.pkg or NAT.EXT[job.tag or ""]   -- U1: пакет по тегу/заявке до on_spawn (модуль-заказчик может поставить свой поверх)
    if xpk and ((xpk == "assault" and h) or (xpk ~= "assault" and tt)) then for _, pl in ipairs(pls) do NAT.apply(pl, "ext:" .. tostring(job.tag), job.fid, xpk, false) end end
    if job.on_spawn then local okc, e = pcall(job.on_spawn, pls, bx, bz); if not okc then dlog("ext on_spawn error (" .. tostring(job.tag) .. "): " .. tostring(e)) end end
    stats.by_tag = stats.by_tag or {}; stats.by_tag[job.tag or "?"] = (stats.by_tag[job.tag or "?"] or 0) + 1
  elseif job.kind == "slave_caravan" then   -- SLAVES: караван (живой шаблон) + охрана тира фракции, цель — город хозяина рабов
    if not TR.caravans[job.fid] then stats.no_template = (stats.no_template or 0) + 1; return false, "notemplate" end
    local tt = (job.owner and getGameWorld().factionMgr:getFactionByStringID(job.owner) and town_of(job.owner, job.tx or px, job.tz or pz)) or town_of(job.fid, job.tx or px, job.tz or pz)
    PACE.label(spawn(job.fid, TR.caravans[job.fid], sx, py, sz, P.caravan_size or 4, nil, tt), "slave_caravan", job.fid, { ev = job.ev })
    local gs = tier_sid(job.fid)
    if gs then local jx, jz = jit(sx, sz, 150, pcs); spawn(job.fid, gs, jx, py, jz, P.tier_squad_size or 5, nil, tt) end
  elseif job.kind == "bounty_hunt" then   -- BOUNTY: охотники за головой идут на отряд игрока; сила растёт с наградой
    local hfid = BNT.law_of(job.fid)   -- NATIVE2: охотники от правоохранительной фракции заказчика (Faction.myLawEnforcementFaction), иначе от самого заказчика
    local e = TR.factions[hfid]
    if not (e and pc) then hfid = job.fid; e = TR.factions[hfid] end
    if not (e and pc) then return false end
    local NM = rawget(_G, "KMM_Nemesis")   -- именной охотник: побитый игроком приходит на тир сильнее
    local hb = 0
    if NM and NM.hunt_bonus then local okb, bv = pcall(NM.hunt_bonus, hfid); if okb and tonumber(bv) then hb = bv end end
    local ti = math.min(4, BNT.tier(job.amount or 0) + hb)
    local sid = tier_sid(hfid, ti - TIDX[e.base_tier or "T0"])
    if not sid and hb > 0 then ti = ti - hb; sid = tier_sid(hfid, ti - TIDX[e.base_tier or "T0"]) end
    if not sid then return false end
    local h = pc:getHandle()
    local k = (ti >= 3) and 2 or 1
    local got = 0
    for i = 1, k do
      local jx, jz = jit(sx, sz, 150, pcs)
      local hpl = spawn(hfid, sid, jx, py, jz, P.tier_squad_size or 5, h, nil)
      if hpl then
        got = got + 1
        PACE.label(hpl, "bounty_hunt", hfid)
        NAT.apply(hpl, "bounty_hunt", hfid, "assault", false)   -- U1: охоту на отряд игрока (AItarget) ведёт ядро
        if got == 1 and NM and NM.on_hunt then pcall(NM.on_hunt, hpl, hfid, job.fid, job.amount) end
      end
    end
    if got == 0 then return false, "notemplate" end   -- без отряда нет ни счёта охоты, ни вести
    BNT.act[#BNT.act + 1] = os.clock(); BNT.n = BNT.n + 1
    if hfid ~= job.fid then name = C.name(hfid) .. " (for " .. C.name(job.fid) .. ")" end
    C.emit({ type = "bounty_hunters", a = job.fid, fid = job.fid, amount = job.amount, tier = TIERS[ti],
             text = string.format("%s hunters are after the Nameless for a bounty of %d.", name, job.amount or 0) })
  elseif job.kind == "trader" then   -- ROADS: караван из города с избытком в город с дефицитом груза
    local plan = C.road_plan("caravan", nil, { x = px, z = pz, fids = TR.live_caravans })
    local csid = plan and TR.live_caravans and TR.live_caravans[plan.fid]
    if not csid then return false, "noplan" end
    local ctt = dest_town(plan, plan.fid)
    local pl = spawn(plan.fid, csid, sx, py, sz, 3, nil, ctt)
    PACE.label(pl, "caravan", plan.fid)
    local led = ctt and NAT.apply(pl, "caravan", plan.fid, nil, true)   -- U1: живой шаблон каравана (свой ванильный пакет торговца) + постоянный отряд
    trv_register("caravan", plan.fid, pl, sx, sz, plan, C.road_depart(plan), nil, nil, led)
    name = C.name(plan.fid)
  elseif job.kind == "wanderer" then
    local plan = C.road_plan("wanderer", job.fid, {})
    local wsid = plan and tier_sid(plan.fid, -9)
    if not wsid then return false, "noplan" end
    local wtt = dest_town(plan, plan.fid)
    local pl = spawn(plan.fid, wsid, sx, py, sz, 2, nil, wtt)
    PACE.label(pl, "wanderer", plan.fid)
    local led = wtt and NAT.apply(pl, "wanderer", plan.fid, "wander", false)
    trv_register("wanderer", plan.fid, pl, sx, sz, plan, C.road_depart(plan), nil, nil, led)
    name = C.name(plan.fid)
  elseif job.kind == "courier" then
    local plan = C.road_plan("courier", job.fid, { b = job.b, x = px, z = pz, why = job.why })
    local csid = plan and tier_sid(job.fid, -9)
    if not csid then return false, "noplan" end
    local ctt = dest_town(plan, job.fid)
    local pl = spawn(job.fid, csid, sx, py, sz, 2, nil, ctt)
    if not pl then return false, "notemplate" end   -- гонца нет — и вести о нём нет
    PACE.label(pl, "courier", job.fid, { town = PACE.tname(plan.to, plan.to), ev = job.ev })
    local led = ctt and NAT.apply(pl, "courier", job.fid, "travel", false)
    trv_register("courier", job.fid, pl, sx, sz, plan, nil, nil, nil, led)
    C.emit({ type = "courier", a = job.fid, from = plan.from, to = plan.to, why = job.why })
  elseif job.kind == "daemons" then
    local list = TR.daemons.squads
    local sq = list[math.random(#list)]
    if job.squad then for _, x in ipairs(list) do if tostring(x) == tostring(job.squad) then sq = x; break end end end
    spawn(TR.daemons.faction, sq, sx, py, sz, 4, nil, nil)
  elseif job.kind == "caravan" then
    local cs = TR.caravans[job.fid]   -- шаблон «мёртвого» каравана (его персонажей kill_dead_caravans кладёт телами); живой вместо него не годится
    if not cs then
      stats.no_template = (stats.no_template or 0) + 1
      dlog(string.format("trace caravan skipped: %s has no dead-caravan template", tostring(job.fid)))
      return false, "notemplate"
    end
    if spawn(job.fid, cs, sx, py, sz, P.caravan_dead or 3, nil, nil) then dead_watch[#dead_watch + 1] = { until_t = os.clock() + 20, x = sx, z = sz } end
  else
    return false
  end
  if (stats.spawn_calls or 0) == sc0 and (stats.no_template or 0) > nt0 then   -- ни одного отряда: шаблона не нашлось
    dlog(string.format("trace %s skipped: %s (%s) - no squad template", job.kind, tostring(name), tostring(job.why)))
    return false, "notemplate"
  end
  stats.spawned = stats.spawned + 1
  stats.by_kind[job.kind] = (stats.by_kind[job.kind] or 0) + 1
  dlog(string.format("trace %s: %s (%s) at %.0f from player", job.kind, name, tostring(job.why), r))
  return true
end

-- разорённый караван: персонажи нашего «мёртвого» шаблона рядом с точкой спавна — убиты (тела и груз на дороге)
local function kill_dead_caravans()
  if #dead_watch == 0 then return end
  local now = os.clock()
  for _, r in ipairs(get_snap(snap_ttl()).list) do
    local sid = pkf(r, "tsid")
    if sid and TR.dead[sid] and not r.dead and not r.unique then
      local ch = r.ch
      local okd, dead = pcall(ch.isDead, ch)   -- снимок мог устареть: жив ли на самом деле — в момент действия
      if okd and not dead then ch:declareDead() end
    end
  end
  for i = #dead_watch, 1, -1 do if dead_watch[i].until_t < now then table.remove(dead_watch, i) end end
end

---------------------------------------------------------------------------------------------- потерянные караваны (рядом с игроком)
-- Торговые отряды (платун getIsTrader) в радиусе lost_radius: помним живых и мёртвых участников. Все виденные участники мертвы
-- и живых в отряде не осталось → caravan_lost (один раз на отряд). by="player", если игрок был рядом в момент гибели.
local CAR, ncar, LOST = {}, 0, {}
local AMB, AQ = {}, {}   -- видимые засады: активные пары и очередь на материализацию
local PXZ, probe_set = {}, false
local function nearest_town_of(fid, x, z)
  local best, bd
  local ok, list = pcall(function() return C.towns() end)
  if not (ok and type(list) == "table") then return nil end
  for _, t in ipairs(list) do
    if t.owner == fid and t.x then local d = dist(x, z, t.x, t.z); if not bd or d < bd then best, bd = t.sid, d end end
  end
  return best
end
local function pick_killer(others, victim, pf, x, z, R)   -- ближайший живой NPC чужой (не жертвы и не игрока) фракции в радиусе R
  local best, bd
  for _, o in ipairs(others or {}) do
    if o[1] ~= victim and o[1] ~= pf then
      local d = dist(x, z, o[2], o[3])
      if d <= R and (not bd or d < bd) then best, bd = o[1], d end
    end
  end
  return best, bd
end
local function lost_scan(px, pz, snap)
  if not P.lost_enabled and P.lost_enabled ~= nil then return end
  snap = snap or get_snap(snap_ttl())
  local R = P.lost_radius or 6500   -- >= unseen_max: караваны вне видимости тоже учитываются
  local pf = CFG.player_faction
  local now = os.clock()
  local alive, dead, others = {}, {}, {}   -- others: живые не-караванщики (кандидаты в убийцы)
  local lim = R + (P.lost_killer_radius or 1500)   -- дальше не жертва и не убийца жертвы
  for _, r in ipairs(snap.list) do
    local x, z = r.x, r.z
    local d0 = dist(px, pz, x, z)
    if d0 <= lim then
      if pkf(r, "trader") then
        local key, fid = r.pkey, r.fid
        local tsid = pkf(r, "tsid")
        if key ~= "" and fid and fid ~= pf and d0 <= R and not (tsid and TR.dead[tsid]) then   -- наши разорённые караваны — не потеря
          local e = CAR[key]
          if not e then
            if ncar > 300 then CAR, ncar = {}, 0 end
            e = { fid = fid, seen = 0, dead = 0 }; CAR[key] = e; ncar = ncar + 1
          end
          e.x, e.z, e.t = x, z, now
          if r.dead then dead[key] = (dead[key] or 0) + 1 else alive[key] = (alive[key] or 0) + 1; e.seen = math.max(e.seen, alive[key]) end
          e.pdist = e.pdist and math.min(e.pdist, d0) or d0
        end
      elseif #others < 400 and not r.dead and r.fid then
        others[#others + 1] = { r.fid, x, z }
      end
    end
  end
  for key, nd in pairs(dead) do
    local e = CAR[key]
    if e and not alive[key] and not LOST[key] and (e.seen > 0 or nd > 0) then
      LOST[key] = true
      local by = (dist(px, pz, e.x, e.z) <= (P.lost_by_radius or 1500)) and "player" or "other"
      local ts = nearest_town_of(e.fid, e.x, e.z)
      local killer, kd = pick_killer(others, e.fid, pf, e.x, e.z, P.lost_killer_radius or 1500)
      local amid
      for id, am in pairs(AMB) do   -- караван видимой засады погиб: убийца — отряд грабителя
        if not am.done and am.b == e.fid and (key == am.ckey or dist(e.x, e.z, am.x, am.z) <= (P.ambush_match_radius or 3000)) then
          am.done = true; killer = am.a; amid = id; break
        end
      end
      C.emit({ type = "caravan_lost", a = e.fid, town_sid = ts, to_sid = nil, by = by, killer = killer, ambush = amid, x = e.x, z = e.z })   -- x,z: место остова (реплика отряда Nemesis)
      dlog(string.format("caravan lost: %s by=%s near %s killer=%s", tostring(e.fid), by, tostring(ts), tostring(killer)))
    end
  end
end

---------------------------------------------------------------------------------------------- цены у торговцев
local price_orig = {}   -- исходный множитель по строковому ID отряда (userdata из множеств каждый раз новые — ключом быть не могут)
-- TGM (2026-11-14): проба ТОЛЬКО ЧТЕНИЯ родной таблицы цен города (Town.tradeGoodsMults, ogre_unordered_map<GameData*, float>) — раз за сессию,
-- у первого торговца рядом: доступна ли из Lua и что в ней. Цель — перенести наши цены с priceMultWhenITrade на родной мап (виден в окне торговли).
-- B5 (2026-11-15): Ownerships._homeTown — TownBase, поле tradeGoodsMults есть только у Town (BindingsReference: Town / TownBase).
-- Приведение — родной виртуальный TownBase:isTown() -> Town (nil у гнезда). Источники города по очереди: дом отряда, город, где стоит
-- отряд (Platoon:getCurrentTownLocation), где стоит торговец (Character:getCurrentTownLocation). Проба — до P.tgm_tries торговцев.
local TGM = { done = false, tries = 0, ok = false, tried = {} }
function TGM.town_of(pl, ch)
  local why = {}
  for _, s in ipairs({ { "home", function() return pl:getOwnerships()._homeTown end },
                       { "platoon_here", function() return pl:getCurrentTownLocation() end },
                       { "char_here", function() return ch and ch:getCurrentTownLocation() end } }) do
    local ok, tb = pcall(s[2])
    if ok and tb then
      local ok2, t = pcall(function() return tb:isTown() end)
      if ok2 and t then return t, s[1] end
      why[#why + 1] = s[1] .. ":" .. (ok2 and "not a Town" or ("isTown err " .. tostring(t)))
    else
      why[#why + 1] = s[1] .. ":" .. (ok and "nil" or ("err " .. tostring(tb)))
    end
  end
  return nil, table.concat(why, "; ")
end
function TGM.name(t)
  local ok, nm = pcall(function() local gd = t:getGameData(); return gd and (gd.name or gd.stringID) end)
  return tostring(ok and nm or "?")
end
-- чтение родного мапа: n записей, до 3 примеров, тип контейнера (userdata/table — от него зависит способ записи)
function TGM.read(t)
  local m = t.tradeGoodsMults
  if m == nil then return nil, "tradeGoodsMults = nil" end
  local n, ex = 0, {}
  local okp, perr = pcall(function()
    for k, v in pairs(m) do
      n = n + 1
      if n <= 3 then local okk, kn = pcall(function() return k.name or k.stringID end); ex[#ex + 1] = tostring(okk and kn or k) .. "=" .. tostring(v) end
    end
  end)
  local mt = (type(m) == "userdata" or type(m) == "table") and getmetatable(m)
  local caps = type(mt) == "table" and string.format("idx=%s newidx=%s", tostring(mt.__index ~= nil), tostring(mt.__newindex ~= nil)) or "mt=none"
  if not okp then return nil, string.format("tradeGoodsMults %s (%s), pairs failed: %s", type(m), caps, tostring(perr)) end
  return n, string.format("tradeGoodsMults %s (%s) entries=%d %s", type(m), caps, n, table.concat(ex, ", "))
end
-- R1: запись разрешена после «TGM probe OK» в этой сессии, пока проверка первой записи не провалилась; P.tgm_write = false — выключено
function TGM.can_write() return P.tgm_write ~= false and TGM.ok and TGM.wok ~= false end
-- запись множителя товара (gd = GameData вещи); m — уже прочитанный мап (копию-таблицу вызывающий возвращает полю сам)
function TGM.set(t, gd, v, m)
  if not (TGM.can_write() and t and gd and type(v) == "number") then return false end
  return (pcall(function()
    local mm = m or t.tradeGoodsMults
    mm[gd] = v
    if not m and type(mm) == "table" then t.tradeGoodsMults = mm end   -- биндинг отдал копию: вернуть целиком
  end))
end
function TGM.probe(pl, ch)
  TGM.tries = TGM.tries + 1
  local res, okr = "error before read", false
  probe_call("tgm_read", function()
    local t, src = TGM.town_of(pl, ch)
    if not t then res = "no Town (" .. tostring(src) .. ")"; return end
    local okq, n, info = pcall(TGM.read, t)
    if not okq then n, info = nil, "read error " .. tostring(n) end
    res = string.format("src=%s town %s: %s", src, TGM.name(t), tostring(info))
    okr = n ~= nil
  end)
  if okr then
    TGM.done, TGM.ok = true, true
    dlog("TGM probe OK: " .. res)
  elseif TGM.tries >= (P.tgm_tries or 6) then
    TGM.done = true
    dlog(string.format("TGM probe FAIL after %d traders: %s", TGM.tries, res))
  end
  return okr, res
end
-- R1 (2026-11-15): склад города -> родные цены товара. После «TGM probe OK» в этой сессии и проверки первой записи (обратное чтение,
-- крэш-сторож tgm_write) город у торговцев рядом с игроком получает Town.tradeGoodsMults[вещь] = родной множитель x цена категории:
-- KMM_Stock.price_x (уровень к норме, осада, контрабанда) x C.price_mult(владелец: война, голод, богатство), пределы tgm_min..tgm_max.
-- Пересчёт раз в tgm_hours игровых часов шагом tgm_smooth к цели; новая корзина склада (дефицит/избыток/осада) и первый заход — сразу.
-- Город с TGM: priceMultWhenITrade его торговцев — исходный (без двойного счёта); иначе прежний общий множитель (фолбэк).
-- Родные значения (не 1) — в S.tgm.o[tsid][sid] при первом заходе, дальше берутся оттуда: если движок сохранит наши цены, они не накопятся.
-- Ограничение: вещи нового владельца города (смена культуры) считаются с родным множителем 1.
TGM.T, TGM.GD, TGM.st = {}, {}, { towns = 0, writes = 0, updates = 0, events = 0 }
function TGM.hours()
  local ok, h = pcall(function() return getGameWorld():getTimeStamp_inGameHours():getTotalHours() end)
  if ok and type(h) == "number" then return h end
  local ok2, d = pcall(function() return C.state().last_day or 0 end)
  return (ok2 and tonumber(d) or 0) * 24
end
function TGM.town_for(pl, ch, tsid)   -- Town именно этого города (как KMM_Stock.town_of): здесь торговец / отряд / дом
  for _, f in ipairs({ function() return ch and ch:getCurrentTownLocation() end, function() return pl:getCurrentTownLocation() end,
                       function() return pl:getOwnerships()._homeTown end }) do
    local ok, t = pcall(function()
      local tb = f(); local tt = tb and tb:isTown(); local gd = tt and tt:getGameData()
      return gd and gd.stringID == tsid and tt
    end)
    if ok and t then return t end
  end
end
function TGM.gd(sid, ty)
  local k = sid .. "#" .. tostring(ty)
  local g = TGM.GD[k]
  if g == nil then
    local ok, v = pcall(function() return getGameWorld().gamedata:getData(sid, ty) end)
    g = (ok and v) or false; TGM.GD[k] = g
  end
  return g or nil
end
function TGM.verify(twn, gd, sid, v)   -- первая запись сессии под крэш-сторожем: обратное чтение и родной getLocalTradePriceMult
  local okw, rb, lm = false, nil, nil
  local ran = probe_call("tgm_write", function()
    okw = TGM.set(twn, gd, v)
    local okr, r = pcall(function() return twn.tradeGoodsMults[gd] end); rb = okr and r or nil
    local okl, l = pcall(function() return twn:getLocalTradePriceMult(gd) end); lm = okl and l or nil
  end)
  TGM.wok = (ran and okw and tonumber(rb) ~= nil and math.abs(rb - v) < 1e-3) and true or false
  dlog(string.format("TGM write %s: town %s item %s set %.3f read %s local_mult %s%s", TGM.wok and "OK" or "FAIL", TGM.name(twn), tostring(sid), v,
    tostring(rb), tostring(lm), ran and "" or " (crash guard: tgm_write off)"))
  return TGM.wok
end
-- родной множитель вещи в городе: из S.tgm.o (город уже обследован) или с живого мапа при первом заходе (не 1 — запомнить)
function TGM.orig(rec, PS, tsid, sid, gd, m, t)
  local o = rec.o[sid]
  if o then return o end
  if PS.w[tsid] then
    o = (PS.o[tsid] or {})[sid] or 1
    local smp = PS.s[tsid]
    if not TGM.persist_told and smp and smp[1] == sid then   -- однократно за сессию: сохраняет ли движок наши цены в сейве
      TGM.persist_told = true
      local okv, v = pcall(function() return m[gd] end)
      local kept = okv and tonumber(v) and math.abs(v - smp[2]) < 1e-3 and math.abs(smp[2] - o) > 1e-3
      dlog(string.format("TGM persist: town %s engine %s our prices (live %s, ours %.3f)", TGM.name(t), kept and "kept" or "reset", tostring(okv and v), smp[2]))
    end
  else
    local okv, v = pcall(function() return m[gd] end)
    o = (okv and tonumber(v)) or 1
    if math.abs(o - 1) > 1e-4 then PS.o[tsid] = PS.o[tsid] or {}; PS.o[tsid][sid] = o end
  end
  rec.o[sid] = o
  return o
end
function TGM.apply(tsid, pl, ch, fid)   -- true: цены этого города ведёт родной мап (общий множитель торговцу не нужен)
  if not TGM.can_write() then return false end
  local K = rawget(_G, "KMM_Stock")
  local S = C.state()
  if not (K and K.price_x and K.cat_items and S) then return false end
  if TGM.S ~= S then TGM.S, TGM.T = S, {} end   -- загрузка другого сейва: записи сессии не переносим
  local rec = TGM.T[tsid]
  local h = TGM.hours()
  local px = K.price_x(tsid)
  if not (px and px.x) then return rec and rec.live or false end
  if rec and rec.sig == px.sig and h >= rec.h and h - rec.h < (P.tgm_hours or 1) then return rec.live end
  local t = TGM.town_for(pl, ch, tsid)
  local okm, m = pcall(function() return t and t.tradeGoodsMults end)
  if not (okm and m) then return rec and rec.live or false end
  if not rec then rec = { f = {}, o = {}, live = false }; TGM.T[tsid] = rec; TGM.st.towns = TGM.st.towns + 1 end
  local snap = rec.sig == nil or rec.sig ~= px.sig   -- первый заход или событие склада: сразу к цели
  if rec.sig ~= nil and rec.sig ~= px.sig then TGM.st.events = TGM.st.events + 1 end
  S.tgm = type(S.tgm) == "table" and S.tgm or {}
  local PS = S.tgm
  PS.o, PS.w, PS.s = PS.o or {}, PS.w or {}, PS.s or {}
  local owner = (K.stock(tsid) or {}).owner or fid
  local fac = 1
  do local okf, v = pcall(C.price_mult, owner); if okf and tonumber(v) then fac = v end end
  local lo, hi, ops, nw, done = P.tgm_min or 0.6, P.tgm_max or 1.8, P.tgm_ops or 240, 0, true
  local parts = {}
  for _, c in ipairs(K.CATS or {}) do
    local x = px.x[c]
    if x then
      local want = math.max(lo, math.min(hi, x * fac))
      local cur = rec.f[c]
      local nf = (snap or not cur) and want or (cur + (want - cur) * (P.tgm_smooth or 0.5))
      if math.abs(want - nf) < 0.02 then nf = want end
      if not cur or math.abs(nf - cur) >= 0.01 then
        local items = K.cat_items(tsid, c) or {}
        if nw > 0 and nw + #items > ops then done = false; break end   -- бюджет прохода: остаток категорий — в следующий
        for _, it in ipairs(items) do
          local sid = it[1]
          local gd = TGM.gd(sid, it[2])
          if gd then
            local val = TGM.orig(rec, PS, tsid, sid, gd, m, t) * nf
            if TGM.wok == nil and not TGM.verify(t, gd, sid, val) then return false end
            if not TGM.set(t, gd, val, m) then
              TGM.wok = false
              dlog(string.format("TGM write FAIL: town %s item %s (fallback priceMultWhenITrade)", TGM.name(t), tostring(sid)))
              return false
            end
            nw = nw + 1
            local smp = PS.s[tsid]   -- образец для «TGM persist»: вещь с самым заметным сдвигом
            if not smp or smp[1] == sid or math.abs(nf - 1) > math.abs((smp[3] or 1) - 1) then PS.s[tsid] = { sid, val, nf } end
          end
        end
        rec.f[c] = nf
      end
      parts[#parts + 1] = string.format("%s=%.2f", c, rec.f[c] or nf)
    end
  end
  if type(m) == "table" then pcall(function() t.tradeGoodsMults = m end) end   -- биндинг отдал копию: вернуть целиком
  TGM.st.writes = TGM.st.writes + nw
  rec.live = true
  if done then
    PS.w[tsid] = true
    if snap then
      dlog(string.format("TGM town %s (%s) %s: %s fac=%.2f writes=%d", TGM.name(t), tsid, rec.sig and "stock changed" or "first",
        table.concat(parts, " "), fac, nw))
    end
    rec.sig, rec.h = px.sig, h
    TGM.st.updates = TGM.st.updates + 1
  end
  return true
end
local function prices(px, pz, snap)
  if not P.price_enabled then return end
  snap = snap or get_snap(snap_ttl())
  local seen = {}   -- множитель — свойство платуна: один раз на платун за проход
  local rad = P.price_radius or 9000
  for _, r in ipairs(snap.list) do
    local key, pl, fid = r.pkey, r.pl, r.fid
    if key ~= "" and pl and fid and not seen[key] and dist(px, pz, r.x, r.z) <= rad then
      seen[key] = true
      if price_orig[key] == nil then price_orig[key] = pl.priceMultWhenITrade or 1 end
      if not TGM.done and not TGM.tried[key] then TGM.tried[key] = true; TGM.probe(pl, r.ch) end   -- разные торговцы, не один и тот же
      local mult = C.price_mult(fid)   -- полка своего города (склад): дефицит дороже, избыток дешевле
      if C.price_mult_town and _G.KMM_Stock and KMM_Stock.town_of then
        local tsid = KMM_Stock.town_of(r.ch)
        local oka, act = false, false
        if tsid and TGM.can_write() then
          oka, act = pcall(TGM.apply, tsid, pl, r.ch, fid)
          if not oka then TGM.wok = false; dlog("TGM write FAIL: apply error " .. tostring(act) .. " (fallback priceMultWhenITrade)"); act = false end
        end
        if act then mult = 1   -- R1: цены города на родном мапе — без общего множителя
        elseif tsid then mult = C.price_mult_town(fid, tsid) or mult end
      end
      local want = price_orig[key] * mult
      if math.abs((pl.priceMultWhenITrade or 1) - want) > 0.01 then pl.priceMultWhenITrade = want end
    end
  end
end

---------------------------------------------------------------------------------------------- база игрока (для мотивированных рейдов)
local function base_track()
  local pc = player_char()
  if not pc then return end
  local ap = pc:getPlatoon()
  local pl = ap and ap.me
  local own = pl and pl:getOwnerships()
  local town = own and own._homeTown
  if not town then return end
  local x, z = xz(town:getPosition())
  if not x then return end
  local money = own:getMoney() or 0
  local nchars = 0
  pcall(function() for _ in pairs(getPlayerInterface():getAllPlayerCharacters()) do nchars = nchars + 1 end end)
  C.set_base(x, z, 40 + money / 200 + nchars * 4, 10 + nchars * 6)
end

---------------------------------------------------------------------------------------------- первый час новой игры
local first_hour_done = false
local function first_hour(px, pz)
  if first_hour_done then return end
  first_hour_done = true
  local S = C.state()
  if (S.last_day or 0) > 3 then return end   -- загруженный старый мир: только обычные следы
  local near = {}
  for fid, e in pairs(TR.factions) do
    local x, z = C.fpos(fid)
    local f = S.F[fid]
    if x and f and f.alive and dist(px, pz, x, z) <= (P.radius or 70000) * 1.5 then near[#near + 1] = { fid = fid, d = dist(px, pz, x, z), x = x, z = z } end
  end
  table.sort(near, function(a, b) return a.d < b.d end)
  local jobs = {}
  -- порядок: сперва то, что даёт шанс (разорённый караван — лут; беженцы — весть), потом война, отряд фракции — последним и за воротами
  -- силы и богатства (poor_gate: ждёт, пока отряд игрока нищ и слаб, не дольше first_hour_poor_seconds, потом отменён)
  for _, a in ipairs(near) do if TR.caravans[a.fid] then jobs[#jobs + 1] = { kind = "caravan", fid = a.fid, why = "first hour: road ambush" }; break end end   -- 1)
  local poor, pw   -- 2) беженцы из самого бедного соседа
  for _, a in ipairs(near) do local w = S.F[a.fid].wealth / math.max(1, S.F[a.fid].wealth0); if TR.factions[a.fid].refugees and (not pw or w < pw) then poor, pw = a, w end end
  if poor then jobs[#jobs + 1] = { kind = "refugees", fid = poor.fid, tx = poor.x, tz = poor.z, why = "first hour: hardship" } end
  local col
  for _, a in ipairs(near) do   -- 3) колонна на войну: ближайшая пара в смертельной вражде
    for _, b in ipairs(near) do
      if not col and a.fid ~= b.fid and C.rel(a.fid, b.fid) <= -50 then col = { kind = "column", fid = a.fid, enemy = b.fid, tx = b.x, tz = b.z, why = "first hour: war" } end
    end
    if col then break end
  end
  if col then jobs[#jobs + 1] = col end
  if near[1] then jobs[#jobs + 1] = { kind = "band", fid = near[1].fid, n = 1, why = "first hour: patrol in wealth tier", poor_gate = true,
                                      pg_until = os.clock() + (P.first_hour_poor_seconds or 5400) } end           -- 4)
  local gap = P.first_hour_gap_seconds or 420
  for i = 1, math.min(#jobs, P.first_hour_traces or 4) do jobs[i].at = os.clock() + 60 + (i - 1) * gap; jobs[i].ox, jobs[i].oz = px, pz; enqueue(jobs[i]) end
  dlog(string.format("first hour: %d traces scheduled near player (order:%s; player poor now=%s)", math.min(#jobs, P.first_hour_traces or 4),
       (function() local t = {}; for i = 1, math.min(#jobs, P.first_hour_traces or 4) do t[#t + 1] = " " .. jobs[i].kind end; return table.concat(t) end)(),
       tostring(PACE.poor())))
end

---------------------------------------------------------------------------------------------- видимые события (шина → отряд рядом с игроком)
-- trade_for/treaty trade → живой торговый отряд фракции между игроком и городом; refugees → беженцы; relic_salvage → отряд у руин/города;
-- smuggle_run → малый отряд T0 фракции у города. Подписка на шину, очередь ≤16, события старше 10 игровых дней выбрасываются.
-- Лимиты: ≤1 спавн на 60 с, ≤4 живых наших (TTL), общие min_gap/max_per_day Traces. Нет живого каравана-шаблона/персонажей → тип пропущен.
local VQ, VSEEN, VLIVE, vsub = {}, {}, {}, nil
local vlast = -1000
local VKIND = { trade_route = "vcaravan", trade_for = "vcaravan", refugees = "vrefugees", relic_salvage = "vexpedition", smuggle_run = "vsmuggle", slaves_freed = "vfreed" }
local function vday() local ok, d = pcall(function() return C.state().last_day or 0 end); return ok and d or 0 end
local ALQ = {}   -- town_alarm эфемерен (не в S.events): копим из подписки, разбираем в такте событий
local function visible_push(ev)
  if ev.type == "town_alarm" then if #ALQ < 4 then ALQ[#ALQ + 1] = ev end; return end
  local kind = VKIND[ev.type]
  if kind == nil and ev.type == "treaty_signed" and (ev.kind == "trade" or ev.treaty == "trade" or ev.treaty_type == "trade") then kind = "vcaravan" end
  if not kind or not ev.a then return end
  local key = kind .. "|" .. tostring(ev.a) .. "|" .. tostring(ev.town_sid or ev.town_name or "")
  if ev.id and VSEEN["id" .. tostring(ev.id)] then return end
  if ev.id then VSEEN["id" .. tostring(ev.id)] = true end
  for _, q in ipairs(VQ) do if q.key == key then return end end   -- дубль
  local d = vday()
  if VSEEN[key] and d - VSEEN[key] < 10 then return end
  for i = #VQ, 1, -1 do if d - VQ[i].day > 10 then table.remove(VQ, i) end end
  VQ[#VQ + 1] = { kind = kind, key = key, ev = ev, day = ev.day or d }
  while #VQ > 16 do table.remove(VQ, 1) end
end
local g_vpush = guarded("visible_subscribe", visible_push)
local function visible_sub()
  if vsub or is_down("visible_subscribe_init") then return end
  if not C.subscribe then return end
  local ok, id = pcall(C.subscribe, "*", function(ev) g_vpush(ev) end)
  if ok then vsub = id; go_ok("visible_subscribe_init") else go_down("visible_subscribe_init", id) end
end

local function ruin_near(px, pz)
  local best, bd
  for _, st in ipairs(CFG.sites or {}) do
    if st.kind == "ruins" and st.x then local d = dist(px, pz, st.x, st.z); if not bd or d < bd then best, bd = st, d end end
  end
  if best and bd <= (P.visible_radius or 6000) then return best.x, best.z end
end

local function visible_materialize(px, pz, py)
  if #VQ == 0 or NAT.full() then return end
  local now = os.clock()
  if now - vlast < (P.visible_gap_seconds or 60) or now - last_spawn < (P.min_gap_seconds or 75) then return end
  day_roll()
  if day_count >= (P.max_per_day or 8) then return end
  local live = 0
  for i = #VLIVE, 1, -1 do if now > VLIVE[i] then table.remove(VLIVE, i) else live = live + 1 end end
  if live >= (P.visible_max_live or 4) then return end
  local d0, R = vday(), (P.visible_radius or 6000)
  for i = #VQ, 1, -1 do if d0 - VQ[i].day > 10 then table.remove(VQ, i) end end
  for i, q in ipairs(VQ) do
    local ev = q.ev
    local ex, ez = event_xz(ev)
    if q.kind == "vexpedition" then
      local rx, rz = ruin_near(px, pz)
      if rx then ex, ez = rx, rz end
    end
    if ex and dist(px, pz, ex, ez) <= R then
      local fid, ok = ev.a, false
      local pcs = pc_xz()
      local function at_event(j)   -- у места события, если оно вне видимости; иначе любая допустимая точка (отряд придёт сам)
        local x, z = pick_unseen(pcs, function() return ex + math.random(-j, j), ez + math.random(-j, j) end)
        if x then return x, z end
        return pick_any(pcs)
      end
      local nopoint = false
      if q.kind == "vcaravan" then
        local sid = TR.live_caravans and TR.live_caravans[fid]
        if sid then   -- на дороге к городу-источнику: направление от игрока к городу
          local sx, sz = pick_unseen(pcs, line_gen(pcs, ex, ez))
          if not sx then sx, sz = pick_any(pcs) end
          if sx then
            local plan = roads_on("caravans") and C.road_plan("caravan", fid, { x = ex, z = ez, fids = TR.live_caravans }) or nil   -- ROADS: груз из избытка в дефицит
            local ctt = dest_town(plan, fid) or town_of(fid, ex, ez)
            local pl = spawn(fid, sid, sx, py, sz, 3, nil, ctt)
            PACE.label(pl, "caravan", fid, { ev = ev.id })
            local led = plan and ctt and NAT.apply(pl, "caravan", fid, nil, true)   -- U1: караван с грузом — постоянный отряд ядра
            if plan then trv_register("caravan", fid, pl, sx, sz, plan, C.road_depart(plan), nil, nil, led) end
            ok = pl ~= nil
          else nopoint = true end
        end
      elseif q.kind == "vrefugees" then
        local rs = TR.factions[fid] and TR.factions[fid].refugees
        if rs then
          local sx, sz = at_event(300)
          if sx then
            local plan
            if roads_on("refugees") then plan = (ev.town_sid and C.road_claim("refugees", fid, ev.town_sid)) or C.road_plan("refugees", fid, { from = ev.town_sid, x = ex, z = ez }) end
            local rtt = dest_town(plan, fid) or town_of(fid, px + (px - ex), pz + (pz - ez))
            local pl = spawn(fid, rs, sx, py, sz, P.refugee_size or 4, nil, rtt)
            settle(pl, rtt)
            PACE.label(pl, "refugees", fid, { town = PACE.tname(ev.town_sid, ev.town_name), ev = ev.id })
            local led = rtt and NAT.apply(pl, "refugees", fid, "refugee", plan ~= nil)
            if plan then trv_register("refugees", fid, pl, sx, sz, plan, plan.id, nil, nil, led) end
            ok = pl ~= nil
          else nopoint = true end
        end
      elseif q.kind == "vfreed" then   -- освободители ведут отбитых пленников к своему городу: колонна + малый конвой
        local rs = TR.factions[fid] and TR.factions[fid].refugees
        local es = tier_sid(fid, 0, true)
        if rs then
          local sx, sz = at_event(300)
          if sx then
            local rtt = town_of(fid, ex, ez)
            local pl = spawn(fid, rs, sx, py, sz, P.refugee_size or 4, nil, rtt)
            settle(pl, rtt)
            PACE.label(pl, "freed", fid, { ev = ev.id })
            if rtt then NAT.apply(pl, "freed", fid, "refugee", false) end
            if es and pl then local epl = spawn(fid, es, sx + 60, py, sz + 60, 2, nil, rtt); if rtt then NAT.apply(epl, "escort", fid, "travel", false) end end
            ok = pl ~= nil
          else nopoint = true end
        end
      elseif q.kind == "vexpedition" then
        local sid = tier_sid(fid, 0, true)
        if sid then
          local sx, sz = at_event(300)
          if sx then local epl = spawn(fid, sid, sx, py, sz, 3, nil, nil); PACE.label(epl, "expedition", fid, { ev = ev.id }); ok = epl ~= nil else nopoint = true end
        end
      elseif q.kind == "vsmuggle" then
        local sid = tier_sid(fid, -9)   -- самый бедный тир фракции: малый отряд без блеска
        if sid then
          local sx, sz = at_event(400)
          if sx then local spl = spawn(fid, sid, sx, py, sz, 2, nil, nil); PACE.label(spl, "smugglers", fid, { ev = ev.id }); ok = spl ~= nil else nopoint = true end
        end
      end
      if nopoint then return end   -- нет допустимой точки: остаётся в очереди, повтор в следующем тике (не ближе)
      table.remove(VQ, i)
      if ok then
        VSEEN[q.key] = vday(); vlast = now; last_spawn = now; day_count = day_count + 1; PACE.took({ tag = q.kind }, now)
        VLIVE[#VLIVE + 1] = now + (P.visible_ttl_seconds or 900)
        stats.spawned = stats.spawned + 1; stats.by_kind[q.kind] = (stats.by_kind[q.kind] or 0) + 1
        dlog(string.format("visible %s: %s (%s) near %s", q.kind, C.name(fid), tostring(ev.type), tostring(ev.town_name)))
      end
      return
    end
  end
end

---------------------------------------------------------------------------------------------- ВИДИМАЯ ЗАСАДА
-- Дирижёр (waylay) спрашивает probe: игрок рядом с городом жертвы → пара (караван жертвы + бедный отряд грабителя) на дороге к городу.
-- Грабителям задана цель — лидер каравана (AItarget / Character:attackTarget), бой решает Kenshi. Итог: гибель каравана → caravan_lost
-- (killer = грабитель, в lost_scan); грабители погибли/бежали при живом караване → waylay_repelled. Нет итога — дирижёр по таймауту.
local function amb_probe(a, b, tsid, id)
  if not (TR and P.enabled) or P.ambush_enabled == false then return false end
  local px, pz = PXZ[1], PXZ[2]
  local I = CFG.town_info and CFG.town_info[tsid]
  if not (px and I and I.x) or dist(px, pz, I.x, I.z) > (P.ambush_radius or P.visible_radius or 6000) then return false end
  if not (TR.live_caravans and TR.live_caravans[b]) or not tier_sid(a, -1, true) then return false end
  local now = os.clock()
  if #AQ >= 1 or now - vlast < (P.visible_gap_seconds or 60) or now - last_spawn < (P.min_gap_seconds or 75) then return false end
  day_roll()
  if day_count >= (P.max_per_day or 8) then return false end
  local live = 0
  for i = #VLIVE, 1, -1 do if now > VLIVE[i] then table.remove(VLIVE, i) else live = live + 1 end end
  if live + 2 > (P.visible_max_live or 4) then return false end
  AQ[1] = { id = id, a = a, b = b, tsid = tsid, ex = I.x, ez = I.z, t = now }
  return true
end
-- Планирование засады. Маршрут каравана: город жертвы (ex,ez) -> другой город её фракции (dest). Режимы:
--  "wait"  - засада заранее: грабители стоят в допустимой точке на маршруте (30-70%), караван стартует тоже вне видимости на том же маршруте
--            ближе к городу и идёт через эту точку к пункту назначения (встреча сама);
--  "track" - выслеживание: нет допустимой точки на маршруте -> караван в допустимой точке (на пути к городу или вокруг игрока),
--            грабители в другой допустимой точке и целью получают лидера каравана.
local function amb_plan(job, pcs)
  local dx, dz, dtown
  local okt, list = pcall(function() return C.towns() end)
  local cands = {}
  if okt and type(list) == "table" then
    for _, t in ipairs(list) do
      if t.owner == job.b and t.x and t.sid ~= job.tsid then
        local d = dist(job.ex, job.ez, t.x, t.z)
        if d > 1500 then cands[#cands + 1] = { t.x, t.z, d } end
      end
    end
    table.sort(cands, function(p, q) return p[3] < q[3] end)
  end
  local nearest = cands[1]
  dx, dz = nearest and nearest[1], nearest and nearest[2]
  -- ROADS: память дорог игрока - засада выбирает маршрут, проходящий через частые клетки игрока; сменил путь - засады отстают
  local R = RP()
  local heat_on = roads_on("grid") and C.road_route_heat and #(C.road_grid() or {}) > 0
  if heat_on and nearest then
    local bh, bi = -1, 1
    for i = 1, math.min(4, #cands) do
      local h = C.road_route_heat(job.ex, job.ez, cands[i][1], cands[i][2])
      if h > bh + 1e-9 then bh, bi = h, i end
    end
    if bh > 0 then dx, dz = cands[bi][1], cands[bi][2] end
    local total = 0
    for _, g in ipairs(C.road_grid()) do total = total + g.w end
    if total >= (R.grid_mature or 4) and math.max(0, bh) < (R.cold or 0.3) and math.random() > (R.cold_accept or 0.4) then dx = nil end   -- холодный маршрут: выслеживание вместо засады заранее
  end
  if dx then
    dtown = town_of(job.b, dx, dz)
    local L = dist(job.ex, job.ez, dx, dz)
    local ux, uz = (dx - job.ex) / L, (dz - job.ez) / L
    local back = P.ambush_lead or 700
    local best
    for _ = 1, (P.unseen_tries or 8) do
      local f = 0.3 + math.random() * 0.4
      local mx, mz = job.ex + (dx - job.ex) * f, job.ez + (dz - job.ez) * f
      local cx, cz = mx - ux * back, mz - uz * back   -- караван стартует позади точки засады
      if unseen_ok(mx, mz, pcs) and unseen_ok(cx, cz, pcs) then
        local h = heat_on and C.road_heat(mx, mz) or 0
        if not best or h > best[5] then best = { cx, cz, mx, mz, h } end
        if not heat_on then break end
      end
    end
    if best then return "wait", best[1], best[2], best[3], best[4], dtown end
  end
  local cx, cz = pick_unseen(pcs, line_gen(pcs, job.ex, job.ez))
  if not cx then cx, cz = pick_any(pcs) end
  if not cx then return nil end
  local off = P.ambush_offset or 300
  local rx, rz = pick_unseen(pcs, function() local a = math.random() * 2 * math.pi; return cx + off * math.cos(a), cz + off * math.sin(a) end)
  if not rx then rx, rz = cx, cz end
  return "track", cx, cz, rx, rz, nil
end
local function amb_materialize(px, pz, py)
  local job = AQ[1]
  if not job or NAT.full() then return end
  local now = os.clock()
  if now - job.t > (P.ambush_queue_seconds or 120) or dist(px, pz, job.ex, job.ez) > (P.ambush_radius or P.visible_radius or 6000) then table.remove(AQ, 1); return end
  if now - vlast < (P.visible_gap_seconds or 60) or now - last_spawn < (P.min_gap_seconds or 75) then return end
  if PACE.blocked({ tag = "ambush" }, now) then return end   -- PACE: засада не сразу после другой враждебной встречи (ждёт в AQ до ambush_queue_seconds)
  local live = 0
  for i = #VLIVE, 1, -1 do if now > VLIVE[i] then table.remove(VLIVE, i) else live = live + 1 end end
  if live + 2 > (P.visible_max_live or 4) then return end
  local csid, rsid = TR.live_caravans[job.b], tier_sid(job.a, -1, true)
  if not (csid and rsid) then table.remove(AQ, 1); return end
  local pcs = pc_xz()
  local mode, cx, cz, rx, rz, dtown = amb_plan(job, pcs)
  if not mode then return end   -- нет допустимой точки вне видимости: не спавним ближе, ждём (очередь живёт ambush_queue_seconds)
  table.remove(AQ, 1)
  local cp = spawn(job.b, csid, cx, py, cz, 3, nil, dtown or town_of(job.b, job.ex, job.ez))
  local h = nil
  if mode == "track" then pcall(function() h = cp:getSquadLeader():getHandle() end) end   -- выслеживание: цель - лидер каравана
  local rp = spawn(job.a, rsid, rx, py, rz, P.ambush_size or 3, h, nil)                   -- засада заранее: стоят на месте
  if not (cp and rp) then dlog(string.format("visible ambush skipped: %s / %s - no squad template", C.name(job.a), C.name(job.b))); return end
  local led = h and NAT.apply(rp, "ambush", job.a, "assault", false)   -- U1: выслеживание — к отряду каравана ведёт ядро
  AMB[job.id] = { id = job.id, a = job.a, b = job.b, x = rx, z = rz, t0 = now, mode = mode, ckey = cp and plat_key(cp), rkey = rp and plat_key(rp),
                  nat = led or nil }   -- attackTarget остаётся поверх пакета: пакет враждебности не создаёт
  vlast = now; last_spawn = now; day_count = day_count + 1; PACE.took({ tag = "ambush" }, now)
  VLIVE[#VLIVE + 1] = now + (P.visible_ttl_seconds or 900); VLIVE[#VLIVE + 1] = now + (P.visible_ttl_seconds or 900)
  stats.spawned = stats.spawned + 2; stats.by_kind.vambush = (stats.by_kind.vambush or 0) + 1
  dlog(string.format("visible ambush: %s waylay %s near %s", C.name(job.a), C.name(job.b), tostring(job.tsid)))
end
---------------------------------------------------------------------------------------------- TOWNLIFE: приход в город
-- Первые arrive_days игровых дней после старта/входа в новый район (ближайший город игрока сменился): к ближайшему городу игрока
-- по очереди приходят бродяги (T0 фракции, продают хлам), торговцы и караван (живой шаблон каравана). Охрану/владельцев не спавним.
-- Лимиты общие: min_gap, max_per_day, <= visible_max_live (4) живых; сверх этого - arrive_max отрядов на район, пауза arrive_gap_seconds.
---------------------------------------------------------------------------------------------- ПОГОДА (2026-11-13)
-- API: Character:getCurrentWeatherAffectStatus() -> WeatherAffecting (1 пыльная буря, 2 кислотный дождь, 3 огонь, 4 газ, 5 дождь; 0 нет),
-- :getCurrentWeatherAffectStrength() -> число. Читаем у персонажа игрока (раз в wx_check_seconds). Плохая = тип из wx_bad и сила >= wx_min_strength.
-- Плохая погода: путники приходят в ближайший город чаще (arrive_gap x wx_gap_mult, +wx_arrive_bonus отрядов, окно arrive_days снимается),
-- ambient/ext на дороге режутся (wx_road_skip / wx_ext_reject). После бури - волна выхода wx_wave_seconds с теми же ускорениями.
local WX = { bad = false, str = 0, t = -1000, wave = -1000, was = false, n_bad = 0, n_wave = 0 }
local function weather_check()
  if P.wx_enabled == false then WX.bad = false; return WX end
  local now = os.clock()
  if now - WX.t < (P.wx_check_seconds or 5) then return WX end
  WX.t = now
  local pc = player_char()
  if not pc then return WX end
  local ok, w, s = pcall(function() return pc:getCurrentWeatherAffectStatus(), pc:getCurrentWeatherAffectStrength() end)
  if not ok or type(w) ~= "number" then return WX end   -- нет API/ошибка: погоду не учитываем
  s = tonumber(s) or 0
  local bad = false
  for _, b in ipairs(P.wx_bad or { 1, 2, 3, 4 }) do if b == w then bad = true end end
  bad = bad and s >= (P.wx_min_strength or 0.3)
  if bad and not WX.was then WX.n_bad = WX.n_bad + 1 end
  if WX.was and not bad then WX.wave = now; WX.n_wave = WX.n_wave + 1 end   -- буря кончилась: волна
  WX.was, WX.bad, WX.str = bad, bad, s
  return WX
end
local function weather_rush()   -- true: буря или волна после неё
  local w = weather_check()
  return w.bad or (os.clock() - w.wave) < (P.wx_wave_seconds or 240)
end
local ARR = { town = nil, day0 = nil, n = 0, last = -1000, chk = -1000 }
local ARR_SEQ = { "vagrant", "trader", "vagrant", "caravan", "trader", "vagrant" }
local function arrive_materialize(px, pz, py)
  if P.arrive_enabled == false or NAT.full() then return end
  local now = os.clock()
  if now - ARR.chk >= (P.arrive_check_seconds or 30) then   -- смена района: ближайший к игроку город (kind=city, не далее arrive_radius)
    ARR.chk = now
    local best, bd
    for _, t in ipairs(C.towns() or {}) do
      if t.kind == "city" and t.x then local d = dist(px, pz, t.x, t.z); if not bd or d < bd then best, bd = t, d end end
    end
    if best and bd <= (P.arrive_radius or 9000) then
      if best.sid ~= ARR.town then ARR.town, ARR.day0, ARR.n = best.sid, vday(), 0 end
    else ARR.town = nil end
  end
  if not ARR.town then return end
  local rush = weather_rush()
  if not rush and (vday() - (ARR.day0 or 0) > (P.arrive_days or 3)) then return end
  if ARR.n >= (P.arrive_max or 6) + (rush and (P.wx_arrive_bonus or 3) or 0) then return end
  if now - ARR.last < (P.arrive_gap_seconds or 240) * (rush and (P.wx_gap_mult or 0.4) or 1) or now - last_spawn < (P.min_gap_seconds or 75) then return end
  day_roll()
  if day_count >= (P.max_per_day or 8) or #Q > 0 then return end
  local live = 0
  for i = #VLIVE, 1, -1 do if now > VLIVE[i] then table.remove(VLIVE, i) else live = live + 1 end end
  if live >= (P.visible_max_live or 4) then return end
  local town
  for _, t in ipairs(C.towns() or {}) do if t.sid == ARR.town then town = t; break end end
  local fid = town and town.owner
  if not (fid and TR.factions[fid] and C.alive(fid)) then ARR.last = now; return end   -- свободный/павший город: следующий опрос позже
  local kind = ARR_SEQ[(ARR.n % #ARR_SEQ) + 1]
  local sid, size = nil, 2
  if kind == "vagrant" then sid = tier_sid(fid, -9)
  else sid = TR.live_caravans and TR.live_caravans[fid]; size = (kind == "caravan") and 3 or 2 end
  if not sid then kind = "vagrant"; sid, size = tier_sid(fid, -9), 2 end
  if not sid then ARR.last = now; return end
  local sx, sz = pick_any(pc_xz())
  if not sx then return end   -- нет допустимой точки вне видимости: повтор через опрос
  local att = town_of(fid, town.x, town.z)
  local apl = spawn(fid, sid, sx, py, sz, size, nil, att)
  if not apl then ARR.last = now; return end   -- нет шаблона: без счёта прихода, повтор через обычную паузу
  if kind == "vagrant" and att then NAT.apply(apl, "arrive_vagrant", fid, "travel", false) end   -- U1: бедный отряд идёт в город сам (торговцы — пакет шаблона)
  ARR.n, ARR.last, last_spawn, day_count = ARR.n + 1, now, now, day_count + 1
  VLIVE[#VLIVE + 1] = now + (P.visible_ttl_seconds or 900)
  stats.spawned = stats.spawned + 1
  stats.by_kind["arrive_" .. kind] = (stats.by_kind["arrive_" .. kind] or 0) + 1
  dlog(string.format("arrival %s: %s -> %s (%d of %d)", kind, C.name(fid), tostring(town.name or town.sid), ARR.n, P.arrive_max or 6))
end
-- сведения по платунам (общие для amb_scan и br_scan): живые/мёртвые, фракция, торговый ли, первая позиция, позиция последнего живого, живые персонажи
local function kinfo(snap)
  local I = snap.traces_info
  if I then return I end
  I = {}
  for _, r in ipairs(snap.list) do
    local k = r.pkey
    if k ~= "" then
      local e = I[k]
      if not e then e = { alive = 0, dead = 0, fid = r.fid, trader = pkf(r, "trader"), x = r.x, z = r.z, chars = {} }; I[k] = e end
      if r.dead then e.dead = e.dead + 1 else e.alive = e.alive + 1; e.ax, e.az = r.x, r.z; e.chars[#e.chars + 1] = r.ch end
    end
  end
  snap.traces_info = I
  return I
end
local function amb_scan(px, pz, snap)
  if next(AMB) == nil then return end
  local now = os.clock()
  local info = kinfo(snap or get_snap(snap_ttl()))   -- ключ платуна → { alive, dead, ax, az, fid, trader, chars }
  for id, am in pairs(AMB) do
    if am.done or now - am.t0 > (P.ambush_ttl_seconds or 1200) then AMB[id] = nil
    else
      for _, w in ipairs({ { "ckey", am.b, true }, { "rkey", am.a, false } }) do   -- ключ платуна не вернулся от spawn — ищем рядом с точкой засады
        if not am[w[1]] then
          for k, e in pairs(info) do
            if e.fid == w[2] and e.ax and dist(e.ax, e.az, am.x, am.z) <= 1500 and e.trader == w[3] then am[w[1]] = k; break end
          end
        end
      end
      local c, rr = am.ckey and info[am.ckey], am.rkey and info[am.rkey]
      if c and c.alive > 0 then am.cseen = true end
      if rr and rr.alive > 0 then am.rseen = true end
      local engage = am.mode ~= "wait" or (c and rr and c.ax and rr.ax and dist(c.ax, c.az, rr.ax, rr.az) <= (P.ambush_engage or 1500))
      if c and c.alive > 0 and rr and rr.alive > 0 and not am.ordered and c.chars[1] and engage then   -- цель грабителям: враждебность задаём явно
        am.ordered = true
        for _, ch in ipairs(rr.chars) do pcall(function() ch:attackTarget(c.chars[1]) end) end
      end
      local repelled = false
      if am.cseen and c and c.alive > 0 then
        if am.rseen and rr and rr.alive == 0 and rr.dead > 0 then repelled = true
        elseif rr and rr.alive > 0 and c.ax and rr.ax and dist(c.ax, c.az, rr.ax, rr.az) > (P.ambush_flee or 3500) then repelled = true end
      end
      if repelled then
        am.done = true
        local near = c.ax and dist(px, pz, c.ax, c.az) <= (P.repel_player_radius or 1500)
        C.emit({ type = "waylay_repelled", a = am.a, b = am.b, id = id, near_player = near or nil })
        dlog(string.format("ambush repelled: %s vs %s near_player=%s", tostring(am.a), tostring(am.b), tostring(near)))
      end
    end
  end
end

---------------------------------------------------------------------------------------------- ROBBERY: добыча NPC-отрядов рядом с игроком
-- До 12 отрядов, участвовавших в драке (рядом упали/мертвы чужие, драка не у игрока): снимок инвентаря → прирост = добыча.
-- Когда отряд покидает радиус игрока или исчезает — KMM_Conductor.loot_add(fid, cat, n, victim) + событие loot_carried (один раз на отряд).
-- Лучшая броня/оружие (по таблице gear_scores.json: sid → [score, group, flags]) надевается грабителем, а не уходит на продажу.
local LT, nlt, LREP, nrep = {}, 0, {}, 0
local GS, GS_TRIED
local gear_cd = {}        -- хендл → os.clock() последнего переодевания
local gstat = { equipped = 0, carried = 0, tracked = 0 }
local cat_memo, ncm = {}, 0

local function gear_scores()
  if GS or GS_TRIED then return GS end
  GS_TRIED = true
  local t = C.read_json("gear_scores.json", "C:/KenshiModMap/build/KMM_Conductor/gear_scores.json")
  GS = (type(t) == "table" and t.s) or nil
  return GS
end
local function item_cat(it)   -- категория вещи: списки KMM_Stock; неизвестное → lux (дорогое) или scrap
  local gd = it:getGameData()
  local sid = gd and gd.stringID
  if not sid then return "scrap" end
  local c = cat_memo[sid]
  if c then return c end
  local ty = gd.type
  local ok, r = false, nil
  if KMM_Stock and KMM_Stock.item_cat then ok, r = pcall(KMM_Stock.item_cat, sid, ty) end
  c = ok and r or nil
  if not c and ty == 2 then c = "weapons" elseif not c and ty == 3 then c = "armor" end
  if not c then
    local okv, v = pcall(function() return it:getValueSingle(false) end)   -- у Item нет getValue (BindingsReference: InventoryItemBase.getValueSingle)
    c = (okv and tonumber(v) or 0) >= (P.loot_lux_value or 500) and "lux" or "scrap"
  end
  if ncm > 2000 then cat_memo, ncm = {}, 0 end
  cat_memo[sid] = c; ncm = ncm + 1
  return c
end
local function inv_snapshot(inv)   -- { категория = единиц } по всему инвентарю (надетое тоже)
  local snap = {}
  for _, it in ipairs(inv:getAllItems()) do
    local c = item_cat(it)
    snap[c] = (snap[c] or 0) + (tonumber(it.quantity) or 1)
  end
  return snap
end
local function race_name(ch)
  local ok, r = pcall(function() local x = ch:getRace(); return tostring((x.data and x.data.name) or x.name or "") end)   -- RaceData: имя в .data.name (save_replay 2026-11-13); x.name - заглушки тестов
  return ok and r:lower() or ""
end

-- переодевание: лучше надетого в той же группе на заметный порог → equipItem. Возвращает true, категорию нового и старого.
local function try_equip(ch, inv, now, handle)
  local gs = gear_scores()
  if not gs then return false end
  if now - (gear_cd[handle] or -1000) < (P.loot_equip_gap or 60) then return false end
  local worn, best_new = {}, {}
  local raceN
  for _, it in ipairs(inv:getAllItems()) do
    local gd = it:getGameData()
    local rec = gd and gs[gd.stringID]
    if rec then
      local sc, grp, fl = rec[1], rec[2], rec[3] or 0
      if it.isEquipped then
        if fl % 2 == 1 then return false end   -- WH-персонаж: не трогаем
        if not worn[grp] or sc > worn[grp].sc then worn[grp] = { sc = sc, it = it } end
      elseif fl % 2 == 0 then
        local locked = fl >= 2
        if locked then raceN = raceN or race_name(ch) end
        if not locked or raceN:find("whistler", 1, true) then
          if not best_new[grp] or sc > best_new[grp].sc then best_new[grp] = { sc = sc, it = it } end
        end
      end
    end
  end
  local pick, gain
  local ratio, diff = P.loot_equip_ratio or 1.3, P.loot_equip_diff or 0.5
  for grp, n in pairs(best_new) do
    local w = worn[grp]
    local g
    if w then
      if n.sc >= w.sc * ratio and n.sc - w.sc >= diff then g = n.sc - w.sc end
    elseif grp:sub(1, 6) == "armour" then g = n.sc end   -- пустой слот брони занимаем; оружие без аналога не меняем
    if g and (not gain or g > gain) then pick, gain = grp, g end
  end
  if not pick then return false end
  local n, w = best_new[pick], worn[pick]
  gear_cd[handle] = now
  local ok = inv:equipItem(n.it)
  if ok == false then return false end
  return true, item_cat(n.it), w and item_cat(w.it) or nil
end
local g_equip = guarded("loot_equip", try_equip)

local function loot_finish(key, e)
  LT[key] = nil; nlt = nlt - 1
  if LREP[key] then return end
  local total = 0
  for _, n in pairs(e.gain) do total = total + math.max(0, n) end
  if total <= 0 or not e.victim then return end
  if nrep > 400 then LREP, nrep = {}, 0 end
  LREP[key] = true; nrep = nrep + 1
  local upi = (CFG.params.stock and CFG.params.stock.units_per_item) or {}
  for c, n in pairs(e.gain) do
    if n > 0 then pcall(C.loot_add, e.fid, c, n * (upi[c] or 1), e.victim) end
  end
  gstat.carried = gstat.carried + 1
  C.emit({ type = "loot_carried", a = e.fid, b = e.victim, n = total,
           text = string.format("A band of %s hauls plunder from a fight and heads for a market.", C.name(e.fid)) })
  -- TRADE: куда понесут добычу - ближайший НЕвраждебный город с лавкой (только лог/диагностика: приказов отряду API не даёт)
  local dest = "?"
  pcall(function()
    local g1 = e.lx and e or nil
    if not g1 then return end
    local best, bd
    for _, t in ipairs(C.towns()) do
      if t.x and t.owner and (t.kind == "city" or t.kind == "town") and (t.owner == e.fid or C.rel(e.fid, t.owner) > -30) and not (t.mine == true) then
        local d = dist(e.lx, e.lz, t.x, t.z)
        if not bd or d < bd then best, bd = t, d end
      end
    end
    if best then dest = string.format("%s (%.0f away)", tostring(best.name), bd) end
  end)
  dlog(string.format("loot carried: %s from %s n=%d, nearest friendly market: %s", tostring(e.fid), tostring(e.victim), total, dest))
end

local function loot_scan(px, pz)
  if P.loot_enabled == false then return end
  local R = P.loot_radius or 5000
  local FR = P.loot_fight_radius or 1500
  local PR = P.loot_player_radius or 2000
  local now = os.clock()
  local pf = CFG.player_faction
  local pcs = {}
  local okp, all = pcall(function() return getPlayerInterface():getAllPlayerCharacters() end)
  if okp then for _, pc in pairs(all) do local x, z = xz(pc:getPosition()); if x then pcs[#pcs + 1] = { x, z } end end end
  local downed, groups, dead_keys = {}, {}, {}
  for _, r in ipairs(get_snap(snap_ttl()).list) do
    local fid, cx, cz = r.fid, r.x, r.z
    if fid and dist(px, pz, cx, cz) <= R then
      local key = r.pl and r.pkey or ""
      if r.down then
        downed[#downed + 1] = { x = cx, z = cz, fid = fid }
        if key ~= "" then dead_keys[key] = true end
      elseif key ~= "" and fid ~= pf then
        local g = groups[key]
        if not g then g = { fid = fid, chars = {} }; groups[key] = g end
        g.chars[#g.chars + 1] = { ch = r.ch, x = cx, z = cz, r = r }   -- S5: хендл лениво (r.h) — только у тех, чей инвентарь смотрим
      end
    end
  end
  if nlt == 0 and #downed == 0 then return end   -- S5: ни жертв, ни отслеживаемых отрядов — дальше работы нет
  local function victim_near(g)   -- чужая фракция лежит рядом с отрядом, и не у игрока
    for _, d in ipairs(downed) do
      if d.fid ~= g.fid and d.fid ~= pf then
        local near_p = false
        for _, p in ipairs(pcs) do if dist(p[1], p[2], d.x, d.z) <= PR then near_p = true; break end end
        if not near_p then
          for _, c in ipairs(g.chars) do if dist(c.x, c.z, d.x, d.z) <= FR then return d.fid end end
        end
      end
    end
  end
  local budget = P.loot_equip_per_pass or 2
  local maxn = P.loot_max_squads or 12
  for key, g in pairs(groups) do
    local e = LT[key]
    local v = victim_near(g)
    if not e and v and nlt < maxn and not LREP[key] then
      e = { fid = g.fid, victim = v, t0 = now, gain = {}, base = {}, seen = now }
      LT[key] = e; nlt = nlt + 1; gstat.tracked = gstat.tracked + 1
    end
    if e then
      e.seen = now
      if v then e.victim = e.victim or v end
      if g.chars[1] then e.lx, e.lz = g.chars[1].x, g.chars[1].z end
      local window = (now - e.t0) <= (P.loot_window_seconds or 400)
      for i = 1, math.min(#g.chars, P.loot_chars_per_squad or 8) do
        local c = g.chars[i]
        c.h = c.h or c.r.h
        local okS, snap = pcall(function() return inv_snapshot(c.ch:getInventory()) end)
        if okS and snap then
          local prev = e.base[c.h]
          e.base[c.h] = snap
          if prev and window then
            local armsgain = false
            for cat, n in pairs(snap) do
              local d = n - (prev[cat] or 0)
              if d > 0 then
                e.gain[cat] = (e.gain[cat] or 0) + math.min(d, 60)
                if cat == "armor" or cat == "weapons" then armsgain = true end
              end
            end
            if armsgain and budget > 0 then
              local inv = c.ch:getInventory()
              local done, ncat, ocat = g_equip(c.ch, inv, now, c.h)
              if done then
                budget = budget - 1; gstat.equipped = gstat.equipped + 1
                if ncat then e.gain[ncat] = (e.gain[ncat] or 0) - 1 end     -- надетое не продаётся
                if ocat then e.gain[ocat] = (e.gain[ocat] or 0) + 1 end     -- снятое старое — обычная добыча
                e.base[c.h] = nil
              end
            end
          end
        end
      end
    end
  end
  for key, e in pairs(LT) do
    if not groups[key] then
      if dead_keys[key] then LT[key] = nil; nlt = nlt - 1            -- отряд полёг: добыча не уходит
      elseif now - e.seen >= (P.loot_leave_seconds or 10) then loot_finish(key, e)
      end
    elseif now - e.t0 > (P.loot_max_track_seconds or 900) then loot_finish(key, e)
    end
  end
end

---------------------------------------------------------------------------------------------- такт
local last_ev, t_tick, t_prices, t_base, t_tier, t_dead, t_lost, t_loot = 0, 0, 0, 0, 0, 0, 0, 0
local t_beat   -- S5: номер такта снимка
-- REV2: рейд на базу игрока ждёт, пока кто-то из персонажей игрока рядом с базой (иначе база не загружена и рейдерам некого штурмовать);
-- не дождались за base_hold_days → абстрактный исход «пусто» (добыча рейдеров), реальная кража из контейнеров базы — плагин (NEEDS_REKENSHI REV2).
local function base_gate(job, pcs_xz)
  local B = C.state().base
  if not (B and B.known and B.x) then return "go" end
  for _, p in ipairs(pcs_xz) do if dist(p[1], p[2], B.x, B.z) <= (P.base_near or 7000) then return "go" end end
  if vday() - (job.day or vday()) > (P.base_hold_days or 10) then return "expired" end
  return "wait"
end
-- ROADS: за 1-2 игровых дня до рейда на базу у базы вне видимости появляются разведчики рейдера и уходят обратно; сам рейд ждёт rel_day
local function scout_step(job, now)   -- "go" | "hold" | "spawned"
  if not roads_on("scouts") then return "go" end
  if job.rel_day then return (vday() >= job.rel_day) and "go" or "hold" end
  local B = C.state().base
  local sid = (B and B.x) and tier_sid(job.fid, -9)
  if not sid then job.rel_day = vday(); return "go" end
  local pcs = pc_xz()
  local bx, bz = B.x, B.z
  local rmin = P.scout_r_min or 2500
  local sx, sz = pick_unseen(pcs, function() local a = math.random() * 2 * math.pi; local r = rmin + math.random() * 2000; return bx + r * math.cos(a), bz + r * math.sin(a) end)
  if not sx then
    job.stries = (job.stries or 0) + 1
    if job.stries > (P.unseen_retry_max or 20) then job.rel_day = vday(); return "go" end
    job.at = now + (P.unseen_retry_seconds or 20)
    return "hold"
  end
  local fx, fz = C.fpos(job.fid)
  if not fx then for _, t in ipairs(C.towns()) do if t.owner == job.fid and t.x then fx, fz = t.x, t.z; break end end end   -- нет центра фракции: любой её город
  local home = fx and town_of(job.fid, fx, fz) or nil
  local pl = spawn(job.fid, sid, sx, 0, sz, math.random(1, 2), nil, home)   -- 1-2 разведчика, цель - свой город (уходят обратно)
  if not pl then job.rel_day = vday(); return "go" end   -- разведчиков нет (шаблон): рейд идёт без предвестника, как при отказе точки
  local led = home and NAT.apply(pl, "scout", job.fid, "travel", false)
  trv_register("scout", job.fid, pl, sx, sz, nil, nil, fx, fz, led)
  local lead = (RP().scout_lead_min or 1) + math.random() * ((RP().scout_lead_max or 2) - (RP().scout_lead_min or 1))
  job.rel_day = vday() + lead
  C.emit({ type = "raid_scout", a = job.fid, base = { x = bx, z = bz }, lead_days = lead })
  stats.spawned = stats.spawned + 1; stats.by_kind.scout = (stats.by_kind.scout or 0) + 1
  dlog(string.format("raid scout: %s near base, raid in %.1f days", tostring(job.fid), lead))
  return "spawned"
end
local function br_scan(px, pz, snap)
  if #BR == 0 then return end
  local now = os.clock()
  local info = kinfo(snap or get_snap(snap_ttl()))
  for i = #BR, 1, -1 do
    local r = BR[i]
    if now - r.t0 > (P.base_raid_ttl_seconds or 1500) then table.remove(BR, i)
    else
      if #r.keys == 0 then   -- spawn не вернул платун: берём чужие отряды этой фракции у точки спавна
        for k, e in pairs(info) do if e.fid == r.fid and not e.trader and e.x and dist(e.x, e.z, r.x, r.z) <= 3000 then r.keys[#r.keys + 1] = k end end
      end
      local alive, dead = 0, 0
      for _, k in ipairs(r.keys) do local e = info[k]; if e then alive = alive + e.alive; dead = dead + e.dead end end
      if alive > 0 then r.seen = true end
      if r.seen and alive == 0 and dead > 0 then
        table.remove(BR, i)
        stats.base_repelled = (stats.base_repelled or 0) + 1
        pcall(C.base_result, "repelled", r.fid)
        dlog("base raid repelled: " .. tostring(r.fid))
      end
    end
  end
end

-- прибытие путников: у цели или вышли из загруженной зоны в её сторону -> тихий деспавн вне видимости + зачёт чисел; погибли - груз потерян
local function trv_finish(t)
  if t.id then C.road_arrive(t.id, "visible")
  else C.emit({ type = "traveler_arrived", a = t.fid, fid = t.fid, kind = t.kind, from = t.from, to = t.to, how = "visible" }) end
  stats.arrived = (stats.arrived or 0) + 1
end
local function trv_scan(px, pz, snap)
  if #TRV == 0 then return end
  local now = os.clock()
  local info = kinfo(snap or get_snap(snap_ttl()))
  local pcs = pc_xz()
  local R = RP()
  local umin = P.unseen_min or 3500
  for i = #TRV, 1, -1 do
    local t = TRV[i]
    if not t.key then
      for k, e in pairs(info) do
        if e.fid == t.fid and e.ax and dist(e.ax, e.az, t.sx, t.sz) <= 2500 and (e.trader and true or false) == (t.kind == "caravan") then t.key = k; break end
      end
    end
    local e = t.key and info[t.key]
    local expired = now - t.t0 > (R.trv_ttl_seconds or 1500)
    local near = 1e9
    if e and e.alive > 0 then
      t.seen, t.lx, t.lz, t.ls = true, e.ax, e.az, now
      for _, p in ipairs(pcs) do near = math.min(near, dist(e.ax, e.az, p[1], p[2])) end
      local d = t.tx and dist(e.ax, e.az, t.tx, t.tz)
      local arrived = expired or (d and (d <= (R.arrive_radius or 2200) or (near >= (R.leave_dist or 7500) and t.d0 and d <= t.d0 - 2000)))
      if arrived and NAT.has(t.key) then   -- U1: постоянный отряд ядра — зачёт без своего деспавна, дальше его ведёт движок
        NAT.n.arrive = NAT.n.arrive + 1
        trv_finish(t); table.remove(TRV, i)
      elseif arrived and near >= umin then   -- тихий деспавн только вне видимости (временный — и под пакетом ядра, иначе копятся у игрока)
        for _, ch in ipairs(e.chars) do pcall(function() if not ch:isDead() then ch:declareDead() end end) end
        trv_finish(t); table.remove(TRV, i)
      elseif now - t.t0 > 2 * (R.trv_ttl_seconds or 1500) then table.remove(TRV, i) end
    elseif e and e.alive == 0 and e.dead > 0 and t.seen then
      if t.id then C.road_lost(t.id) end
      stats.traveler_lost = (stats.traveler_lost or 0) + 1
      table.remove(TRV, i)
    elseif t.seen and t.ls and now - t.ls > 10 then   -- пропал из загруженной зоны живым: ушёл дальше сам
      trv_finish(t); table.remove(TRV, i)
    elseif expired or (not t.seen and now - t.t0 > 180) then table.remove(TRV, i) end   -- не нашли: журнал дирижёра зачтёт по сроку сам
  end
end
local g_trvscan = guarded("traveler_scan", trv_scan)
local t_grid, t_trib, t_bnt = 0, 0, 0
local trib_next = {}
local g_roadgrid = guarded("road_grid", function() for _, p in ipairs(pc_xz()) do C.road_visit(p[1], p[2]) end end)
local g_tribute = guarded("road_tribute", function(px, pz)   -- сборщики дани сюзерена идут к вассалу (DIPLO), кулдаун в дирижёре
  if not (roads_on("tribute") and roads_on("couriers") and C.tribute_pairs) or #Q >= 3 then return end
  local pf, now = CFG.player_faction, os.clock()
  for _, pr in ipairs(C.tribute_pairs()) do
    local a, b = pr[1], pr[2]
    local key = a .. "|" .. b
    if a ~= pf and b ~= pf and TR.factions[a] and (trib_next[key] or 0) <= now then
      for _, t in ipairs(C.towns()) do
        if t.owner == b and t.x and dist(px, pz, t.x, t.z) <= (RP().tribute_radius or 30000) then
          trib_next[key] = now + 300
          enqueue({ kind = "courier", fid = a, b = b, why = "tribute", ev = 0 })
          return
        end
      end
    end
  end
end)

local g_events = guarded("events", function(px, pz)
  local evs = C.state().events
  for _, ev in ipairs(evs) do
    if ev.id > last_ev then last_ev = ev.id; on_event(ev, px, pz) end
  end
  while #ALQ > 0 do on_event(table.remove(ALQ, 1), px, pz) end
end)
local g_spawn = guarded("spawn", function(px, pz, py, pc)
  day_roll()
  if #Q == 0 then return end
  local now = os.clock()
  if now - last_spawn < (P.min_gap_seconds or 75) then return end
  if day_count >= (P.max_per_day or 8) then return end
  for i = #Q, 1, -1 do   -- ворота богатства: отряд так и остался нищ и слаб до срока — след отменён (мир не ждёт вечно)
    local j = Q[i]
    if j.poor_gate and j.pg_until and now > j.pg_until and PACE.poor() then
      table.remove(Q, i); stats.skipped_poor = (stats.skipped_poor or 0) + 1
      dlog(string.format("trace %s dropped: %s - player squad stayed poor and weak", tostring(j.kind), tostring(j.why)))
    end
  end
  local best, bs = nil, -1   -- PACE: лучший готовый не-base_raid по счёту; base_raid обрабатывается по-старому (шлюз/разведка) и важнее всех
  local full = NAT.full()   -- U1: у игрока уже nat_live_max живых временных отрядов ядра — ждут только некритичные
  for i, job in ipairs(Q) do
    if job.kind ~= "base_raid" and (not job.at or now >= job.at) and not (full and PACE.class(job) ~= "critical") then
      if PACE.blocked(job, now) then PACE.waited_host = PACE.waited_host + 1
      else local sc = PACE.score(job, now); if sc > bs then best, bs = i, sc end end
    end
  end
  for i, job in ipairs(Q) do
    if job.kind == "base_raid" or i == best then
    local gate = (job.kind == "base_raid") and base_gate(job, pc_xz()) or "go"
    if gate == "expired" then
      table.remove(Q, i)
      stats.base_unattended = (stats.base_unattended or 0) + 1
      pcall(C.base_result, "unattended", job.fid)
      return
    end
    local sg = "go"
    if gate == "go" and job.kind == "base_raid" and (not job.at or now >= job.at) then
      sg = scout_step(job, now)
      if sg == "spawned" then last_spawn = now; day_count = day_count + 1; return end
    end
    if gate == "go" and sg == "go" and (not job.at or now >= job.at) then
      table.remove(Q, i)
      local okj, why = do_job(job, px, pz, py, pc)
      if okj then last_spawn = now; day_count = day_count + 1; PACE.took(job, now)
      elseif why == "nopoint" then   -- нет допустимой точки вне видимости: не спавним ближе, повторим позже
        job.tries = (job.tries or 0) + 1
        if job.tries <= (P.unseen_retry_max or 20) then job.at = now + (P.unseen_retry_seconds or 20); table.insert(Q, i, job) end
      end
      return
    end
    end
  end
end)
local g_bounty = guarded("bounty", function() return BNT.step() end)
local g_brscan = guarded("base_raid_scan", br_scan)
local g_dead = guarded("dead_caravans", kill_dead_caravans)
local g_prices = guarded("prices", prices)
local g_lost = guarded("caravan_lost", lost_scan)
local g_loot = guarded("loot_scan", loot_scan)
local g_base = guarded("base_track", base_track)
local g_tier = guarded("tier_watch", tier_watch)
local g_first = guarded("first_hour", first_hour)
local g_pko = guarded("pace_ko", PACE.ko_step)
local g_her = guarded("herald", PACE.herald_step)
local g_visible = guarded("visible", visible_materialize)
local g_vsub = guarded("visible_sub", visible_sub)
local g_amb = guarded("ambush", amb_materialize)
local g_ambscan = guarded("ambush_scan", amb_scan)
local g_arrive = guarded("arrive", arrive_materialize)
NAT.g = guarded("native_release", NAT.step)   -- U1: отпуск постоянных отрядов Traces по сроку
NAT.gc = guarded("native_live", function(snap) return NAT.count(kinfo(snap or get_snap(snap_ttl()))) end)
local function scan_window(px, pz)   -- lost + amb + br делят один снимок (один обход вместо трёх)
  local ok, snap = pcall(get_snap, snap_ttl())
  if not ok then snap = nil end   -- ошибка API: каждая функция сама обратится к снимку и отключится под своим именем
  g_lost(px, pz, snap); g_ambscan(px, pz, snap); g_brscan(px, pz, snap); g_trvscan(px, pz, snap)
  if #NAT.tmp > 0 then NAT.gc(snap) end   -- U1: живые временные отряды под пакетом ядра у игрока
end

local function tick_a(px, pz, py, pc)   -- секундный такт, часть до сканов по снимку
  if last_ev == 0 then   -- старые события до входа в мир — не следы
    local evs = C.state().events
    last_ev = (#evs > 0) and evs[#evs].id or 0
    if last_ev == 0 then last_ev = -1 end
    g_first(px, pz)
  end
  g_pko(os.clock())
  g_her(px, pz, os.clock())
  g_events(px, pz)
  g_spawn(px, pz, py, pc)
  g_vsub()
  g_visible(px, pz, py)
  g_amb(px, pz, py)
  g_arrive(px, pz, py)
end
local function tick_b(now, px, pz)   -- секундный такт, часть после сканов
  if now - t_base >= 30 then t_base = now; g_base() end
  if now - t_tier >= 20 then t_tier = now; g_tier(px, pz) end
  if now - t_grid >= (RP().grid_seconds or 8) then t_grid = now; g_roadgrid() end
  if now - t_trib >= 60 then t_trib = now; g_tribute(px, pz) end
  if now - t_bnt >= 20 then t_bnt = now; g_bounty() end
  NAT.g()
end
local function scans(now, sm, beat, px, pz)   -- сканы по снимку: в игре (sm) по тактам, офлайн без метки кадра — по своим периодам, как раньше
  if sm then
    if #dead_watch > 0 and beat_due(beat, P.dead_scan_seconds or 4) then t_dead = now; g_dead() end
    if beat_due(beat, P.lost_scan_seconds or 5) then t_lost = now; scan_window(px, pz) end
    if beat_due(beat, P.loot_scan_seconds or 6) then t_loot = now; g_loot(px, pz) end
    if beat_due(beat, P.price_seconds or 20) then t_prices = now; g_prices(px, pz) end
  else
    if now - t_dead >= (P.dead_scan_seconds or 4) then t_dead = now; g_dead() end
    if now - t_lost >= (P.lost_scan_seconds or 5) then t_lost = now; scan_window(px, pz) end
    if now - t_loot >= (P.loot_scan_seconds or 6) then t_loot = now; g_loot(px, pz) end
    if now - t_prices >= (P.price_seconds or 20) then t_prices = now; g_prices(px, pz) end
  end
end
local function tick()
  if not init() or not P.enabled then return end
  if not probe_set and C.set_ambush_probe then probe_set = true; C.set_ambush_probe(function(a, b, t, id) return amb_probe(a, b, t, id) end) end
  local now = os.clock()
  local full = now - t_tick >= 1      -- секундный такт, как раньше
  local sm = stamp_mode()
  local beat = math.floor(now / SNAP_BEAT)
  local bf = sm and beat ~= t_beat    -- S5: первый кадр такта снимка (сканы по снимку — только здесь, вместе с Self/Stock)
  if not (full or bf) then return end
  if bf then t_beat = beat end
  if full then t_tick = now end
  if not C.state() then return end
  local px, pz, py, pc = player_pos()
  if not px then return end
  PXZ[1], PXZ[2] = px, pz
  if full then tick_a(px, pz, py, pc) end
  if bf or (full and not sm) then scans(now, sm, beat, px, pz) end
  if full then tick_b(now, px, pz) end
end

if Events and Events.on then Events.on("GameWorld::charsUpdate", guarded("tick", function(...) if _G.KMM_Gov then return KMM_Gov.run("traces", tick, ...) else return tick(...) end end)) end

KMM_Traces = {
  queue = function() return Q end,
  stats = function() return stats end,
  weather = function() return weather_check() end,
  disabled = function() return DISABLED end,
  _tick = function() tick() end,
  item_tiers = function() return TR and TR.item_tiers or nil end,   -- S5: Self берёт разобранный traces.json, а не читает его второй раз
  tier_pick = function(fid, shift, adj) if not init() then return nil end; return tier_sid(fid, shift, adj) end,
  tier_stats = function() return tier_stats end,
  ambush = function() return AMB, AQ end,
  travelers = function() return TRV end,
  native = function() if not init() then return nil end; return NAT.n, NAT.reg().L, NAT.PKG, NAT.alive, NAT.tmp end,   -- U1: счётчики, реестр постоянных, пакеты
  _native_step = function() NAT.t = -1e9; return NAT.g() end,
  _enqueue = function(job) enqueue(job) end,
  -- EXT API: request{tag, fid, sid|shift, n<=3, size, from_x/from_z (сторона прихода), to_fid/to_x/to_z (цель-город), target="player", on_spawn(pls,x,z)}
  -- спавн вне видимости рядом с игроком через общую очередь (лимиты Traces); дальний мир внешний модуль ведёт сам в C.state()
  request = function(job) if type(job) ~= "table" or not job.fid or not init() then return false end
    -- EXT-бюджет (2026-11-13, replay: 28 из 45 спавнов за 8 дн были ext): ≤ ext_per_day в игровой день на все модули, ≤ ext_per_tag на тег
    local dk = math.floor((C.state() and C.state().last_day) or 0)
    if EXTB.day ~= dk then EXTB.day, EXTB.n, EXTB.tag = dk, 0, {} end
    local tg = job.tag or "?"
    if weather_check().bad and math.random() < (P.wx_ext_reject or 0.7) then stats.wx_skipped = (stats.wx_skipped or 0) + 1; return false end   -- буря: путники пережидают
    -- PACE: дневной EXT-лимит; сверх него (до +ext_bonus) пускаем «давно не виденный» тег (stale_days) или в засуху (нет спавнов drought_seconds)
    local cap = P.ext_per_day or 4
    if EXTB.n >= cap then
      local drought = os.clock() - last_spawn > (P.drought_seconds or 900)
      if EXTB.n >= cap + (P.ext_bonus or 2) or not (drought or PACE.stale(tg) >= (P.stale_days or 3)) then stats.ext_rejected = (stats.ext_rejected or 0) + 1; return false end
      if drought then PACE.drought = PACE.drought + 1 end
    end
    if (EXTB.tag[tg] or 0) >= (P.ext_per_tag or 1) then stats.ext_rejected = (stats.ext_rejected or 0) + 1; return false end
    for _, q in ipairs(Q) do if q.kind == "ext" and q.tag == tg then return false end end
    EXTB.n = EXTB.n + 1; EXTB.tag[tg] = (EXTB.tag[tg] or 0) + 1; job.kind = "ext"; job.why = job.why or job.tag; job.ev = job.ev or 0; enqueue(job); return true end,
  near = function(x, z, r) if not init() then return false end; local px, pz = player_pos(); if not px or not x then return false end; return dist(px, pz, x, z) <= (r or P.radius or 70000) end,
  bounty = function() return BNT end,
  tgm = TGM,   -- B5: town_of/read/set/probe родного Town.tradeGoodsMults
  pace = function() return { n = PACE.n, seen = PACE.seen, waited_host = PACE.waited_host, drought = PACE.drought, last_host = PACE.last_host,
                              waited_ko = PACE.waited_ko or 0, waited_poor = PACE.waited_poor or 0, ko_t = PACE.ko_t } end,
  heralds = function() return PACE.HER end,
  _pace = PACE,
  pace_class = function(job) return PACE.class(job), PACE.hostile(job) end,
  loot_state = function() return LT, gstat end,
  _equip = function(ch, inv, now, h) return try_equip(ch, inv, now or os.clock(), h or "h") end,
}

-- PUBLISH (2026-11-16): KenshiLua runs each init script in its own sandbox; a plain global stays inside it.
if KMM_Traces ~= nil then rawset(_G, "KMM_Traces", KMM_Traces) end
