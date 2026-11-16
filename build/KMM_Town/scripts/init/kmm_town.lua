-- KMM_Town (2026-11-12) — «Город за работой»: видимая цепочка мастер → ящик → носильщик → лавка / караван.
--
-- Только в загруженном городе рядом с игроком; вне его — ничего (числа склада ведёт KMM_Stock внутри дирижёра).
-- Схема старта как у KMM_Ore v2:
--   * при загрузке модуль только объявляет функции и один обработчик общего тика GameWorld::charsUpdate; ни I/O, ни API игры;
--   * данные (kmm_town_data.lua, генерирует tools/streams/town.py) и конфиг читаются лениво в первом тике;
--   * работа начинается, только когда у игрока есть персонажи, после задержки (секунды + число опросов + игровое время);
--   * редкий тик: опрос раз в poll_seconds, цикл цепочки раз в cycle_seconds; лимиты NPC и предметов на цикл.
-- Цепочка за цикл (всё — по загруженным NPC в радиусе near_radius от персонажа игрока, в том же городе):
--   1) мастер = NPC, чьё текущее действие — работа у машины (AUTO_LABOURING_MINES[_PRETEND] / OPERATE_*), машина известна
--      данным (BUILDING → категория склада + продукт); если склад города даёт единицу (KMM_Stock.take) — продукт создаётся
--      в инвентаре машины («ящик мастерской»), иначе в инвентаре мастера; нет запаса → событие town_shortage, ничего не создаётся;
--      (weapons/armor куются из ЕДИНИЦЫ МЕТАЛЛА склада; изделие засчитывается складу, только когда носильщик довёз его до лавки/каравана — KMM_Stock.made,
--      модель мастерских в этот день не повторяет сделанное; пропавшее по дороге складу не засчитывается);
--   2) носильщик = свободный NPC города рядом: предмет из ящика переходит к нему (виден у него в инвентаре);
--   3) через carry_seconds предмет переходит торговцу: лавочнику города или каравану (торговец, не житель города) → события.
--   Ходьбу NPC не приказываем (надёжные приказы — задача плагина): видимость — предмет реально лежит в ящике / у носильщика / в лавке.
-- Склад: только через _G.KMM_Stock (level/take/add); нет склада — тихо ждём. События — _G.KMM_Conductor.emit, type "town_*".
-- Своего сейва нет: счётчики видимой работы — в слоте дирижёра S.town[town_sid].vis (KMM_Conductor.town_state()).
-- Безотказность: каждая функция под guard (pcall); первая ошибка отключает только её до конца сессии, причина → logs/debug.log.
-- U3 (2026-11-15): голод города виден в его загруженных производствах/фермах — ванильный PRODUCTION_STARVED по полке KMM_Stock
--   (плавно, с откатом при изобилии и уходе игрока); маркеры «U3 …» в logs/stock.log. Подробности — раздел «U3» ниже.

local TAG = "[KMM_Town] "
local VERSION = "v1"

local DEFAULTS = {
  enabled = true, debug_log = "C:/KenshiModMap/logs/debug.log",
  start_delay_seconds = 10, start_delay_polls = 10, start_delay_hours = 0.05,
  poll_seconds = 2.0, cycle_seconds = 30,
  use_snapshot = true, snap_ttl = 4,   -- PERF2: скан через KMM_Gov.snapshot (нет Gov / ошибка — свой обход)
  max_scan_chars = 80,           -- сколько персонажей ГОРОДА РЯДОМ (прошедших фильтр) разбираем за цикл (TRADE: раньше считались все записи снимка)
  scan_chunk = 12,               -- TRADE: разбор персонажей порциями по scan_chunk за кадр
  trade_log = true, trade_log_path = "C:/KenshiModMap/logs/stock.log", trade_log_max = 600,   -- TRADE: строки о видимой цепочке
  max_workers_per_cycle = 3,      -- мастеров, которые за цикл могут создать продукт
  max_active_carriers = 2,        -- одновременно несущих носильщиков
  max_items_per_cycle = 3,        -- предметов, созданных за цикл
  max_crate_queue = 6,            -- предметов, ждущих носильщика (дальше мастер «простаивает»)
  near_radius = 2500,             -- NPC дальше от персонажа игрока не трогаем
  carry_seconds = 40,             -- через сколько реальных секунд носильщик «донёс»
  units_per_item = 1,             -- единиц склада на предмет
  min_level = 0.25,               -- ниже этой доли нормы склада мастер не получает сырья → town_shortage
  caravan_share = 0.35,           -- доля доставок каравану, если караван рядом
  shortage_cooldown_hours = 12,   -- игровые часы между town_shortage одного города/категории
  -- LINKS2: население и беспорядки города берутся у дирижёра (KMM_Conductor.town_mood): лимиты работы x clamp(pop/pop0, pop_min, pop_max)
  mood_enabled = true, pop_min = 0.3, pop_max = 1.2,
  unrest_hi = 0.35,               -- беспорядки выше: работа x unrest_work, событие town_alarm (патрули - дело Traces/плагина)
  unrest_work = 0.5,
  famine_food = 0.3,              -- полка еды ниже доли нормы: меньше людей на улице и меньше закупок сырья (x famine_buy)
  famine_buy = 0.5,
  alarm_cooldown_hours = 12,
  -- U3: голод города в его постройках (рычаг №5 docs/core/world.md). Загруженные производства и фермы города рядом с игроком:
  -- полка их категории (KMM_Stock.level) ниже famine_hi — часть построек (до всех при famine_lo) теряет вход (ConsumptionItem.amount; только при слоте
  -- дирижёра, запомненное возвращается) и встаёт в ванильное PRODUCTION_STARVED; полка поднялась — откат. Постройки игрока и шахты (KMM_Ore) не трогаем.
  famine_enabled = true, famine_lo = 0.1, famine_hi = 0.3,
  famine_radius = 1800, famine_max_objects = 60, famine_max_buildings = 24,
  famine_changes_per_cycle = 2,   -- плавность: построек, меняющих состояние за цикл
  famine_hold_hours = 6,          -- игровые часы, раньше которых остановленная постройка не запускается снова (без мигания)
  u3_log_max = 200,               -- строк U3 в stock.log за сессию
  -- ORE4: шахтёры города у рудных узлов (шаблоны KMM_Ore.ore_kind) черпают жилу своего города в модели дирижёра
  -- (KMM_Conductor.town_mined: R падает, вынутое идёт фракции в счёт нужды); единиц руды мира на работо-час, как у игрока (player_to_world)
  mine_enabled = true, mine_rate = 0.25, mine_max_hours = 2, mine_tasks = { 87, 152, 189 },
}

local cfg, DATA          -- nil до первого тика
local WORK = {}          -- множество taskType работы
local MINE = {}          -- ORE4: taskType настоящей добычи (без «изображать работу»)
local DISABLED = {}
local RT = {
  t_poll = 0, t_cycle = -1e9, ready = false, polls = 0, seen_clock = nil, seen_day = nil,
  town = nil, crate = {}, jobs = {}, rr = 0, short = {}, stages = nil, nlog = 0,
  stats = { cycles = 0, crafted = 0, hauled = 0, delivered = 0, to_caravan = 0, shortages = 0, waits_stock = 0 },
  -- U3: fh[key] = { h = hand, tsid } — загруженные остановленные постройки; u3 — счётчики; nu3 — строк лога
  fh = {}, fstore_local = {}, nu3 = 0,
  u3 = { passes = 0, seen = 0, starved = 0, restored = 0, reassert = 0, kept = 0, flipped = 0, lost = 0, adopted = 0, inputs_ok = nil },
}

---------------------------------------------------------------------------------------------- лог и guard
local function append(path, line)
  local ok, f = pcall(io.open, path, "a")
  if ok and f then f:write(line, "\n"); f:close(); return true end
  return false
end
local function tlog(msg)   -- TRADE: одна строка на событие видимой цепочки (потолок за сессию)
  if not (cfg and cfg.trade_log) or RT.nlog >= (cfg.trade_log_max or 600) then return end
  RT.nlog = RT.nlog + 1
  append(cfg.trade_log_path or DEFAULTS.trade_log_path, os.date("%Y-%m-%d %H:%M:%S") .. "	TRADE " .. tostring(msg))
end
local function klog(msg)
  msg = TAG .. tostring(msg)
  if not (KenshiLua and pcall(function() KenshiLua.log(msg) end)) then print(msg) end
end
local function dlog(msg)
  append((cfg and cfg.debug_log) or DEFAULTS.debug_log, os.date("%Y-%m-%d %H:%M:%S") .. " [KMM_Town] " .. tostring(msg))
  klog(msg)
end
-- HEALTH (2026-11-15): отказ шага -> реестр ядра KMM_Gov (ключ KMM_Town.<шаг>): пауза 1/5/30 мин и повтор, не «до перезапуска».
-- DISABLED — только навсегда (нет Gov: прежнее поведение). off(nm) — шаг сейчас не работает (выключен или на паузе).
local function HG() local g = rawget(_G, "KMM_Gov"); if type(g) == "table" and type(g.h_fail) == "function" then return g end end
local function off(nm)
  if DISABLED[nm] then return true end
  local g = HG(); if not g then return false end
  local ok, up = pcall(g.h_up, "KMM_Town." .. nm)
  return ok and up == false
end
local function h_ok(nm) local g = HG(); if g then pcall(g.h_ok, "KMM_Town." .. nm) end end
local function fail(nm, err)   -- отказ шага: пауза в реестре, без Gov — до перезапуска
  local g, p = HG(), nil
  if g then local ok, r = pcall(g.h_fail, "KMM_Town." .. nm, err); if ok then p = r end end
  if type(p) == "number" then dlog(nm .. " failed, retry in " .. p .. " s: " .. tostring(err))
  elseif not DISABLED[nm] then DISABLED[nm] = true; dlog(nm .. " disabled until restart: " .. tostring(err)) end
end
local function guarded(nm, fn)
  return function(...)
    if off(nm) then return nil end
    local ok, r = pcall(fn, ...)
    if not ok then fail(nm, r); return nil end
    h_ok(nm)
    return r
  end
end
local function link_fail(nm, err) if not off(nm) then fail(nm, err) end end

---------------------------------------------------------------------------------------------- конфиг и данные (лениво)
local function load_data()
  local ok, d = pcall(require, "kmm_town_data")
  if ok and type(d) == "table" then return d end
  for _, p in ipairs({ "C:/Program Files (x86)/Steam/steamapps/common/Kenshi/mods/KMM_Town/scripts/kmm_town_data.lua",
                       "C:/KenshiModMap/build/KMM_Town/scripts/kmm_town_data.lua" }) do
    local f = loadfile(p)
    if f then local ok2, d2 = pcall(f); if ok2 and type(d2) == "table" then return d2 end end
  end
  return nil
end
local function load_cfg()
  local c = {}
  for k, v in pairs(DEFAULTS) do c[k] = v end
  local ok, user = pcall(require, "town_config")
  if ok and type(user) == "table" then for k, v in pairs(user) do c[k] = v end end
  cfg = c
  DATA = load_data()
  if not DATA then error("kmm_town_data.lua not found") end
  WORK = {}
  for _, n in pairs(DATA.work_tasks or {}) do WORK[n] = true end
  MINE = {}
  for _, n in ipairs(cfg.mine_tasks or {}) do MINE[n] = true end
end

---------------------------------------------------------------------------------------------- внешние API (необязательны)
local function conductor()
  local c = rawget(_G, "KMM_Conductor")
  if type(c) == "table" and type(c.emit) == "function" then return c end
  return nil
end
local function stock()
  if off("stock_link") then return nil end
  local k = rawget(_G, "KMM_Stock")
  if type(k) == "table" and type(k.take) == "function" and type(k.level) == "function" then return k end
  return nil
end
local function emit(ev)
  if off("conductor_link") then return end
  local c = conductor()
  if not c then return end
  local ok, err = pcall(c.emit, ev)
  if not ok then link_fail("conductor_link", err) else h_ok("conductor_link") end
end
local function stock_level(K, t, cat)
  local ok, v = pcall(K.level, t, cat)
  if not ok then link_fail("stock_link", v); return nil end
  h_ok("stock_link")
  return tonumber(v)
end
local function stock_take(K, t, cat, n)
  local ok, v = pcall(K.take, t, cat, n)
  if not ok then link_fail("stock_link", v); return 0 end
  return tonumber(v) or 0
end
local function stock_made(K, t, cat, n)   -- изделие доставлено: на склад (made — с дневным зачётом модели; нет made — просто add)
  local f = (type(K.made) == "function") and K.made or K.add
  if type(f) ~= "function" then return 0 end
  local ok, v = pcall(f, t, cat, n)
  if not ok then link_fail("stock_link", v); return 0 end
  return tonumber(v) or 0
end
local function raw_cat(cat) return (cat == "weapons" or cat == "armor") and "metal" or cat end   -- кует из металла; прочее берёт свою категорию
local function vis(tsid)   -- счётчики видимой работы в состоянии дирижёра (едут в его сейве); нет дирижёра — nil
  local c = conductor()
  if not (c and type(c.town_state) == "function") or off("conductor_link") then return nil end
  local ok, T = pcall(c.town_state)
  if not ok then link_fail("conductor_link", T); return nil end
  if type(T) ~= "table" then return nil end
  T[tsid] = T[tsid] or {}
  T[tsid].vis = T[tsid].vis or { crafted = 0, hauled = 0, delivered = 0, to_caravan = 0, stocked = 0 }
  return T[tsid].vis
end
local function mood_of(tsid)   -- множители работы по населению/беспорядкам/голоду города; нет дирижёра или данных - 1
  local m = { work = 1, carry = 1, buy = 1, alarm = false, pop = nil, unrest = 0, hungry = false }
  if not cfg.mood_enabled or off("conductor_link") then return m end
  local c = conductor()
  if not (c and type(c.town_mood) == "function") then return m end
  local ok, d = pcall(c.town_mood, tsid)
  if not ok then link_fail("conductor_link", d); return m end
  if type(d) ~= "table" then return m end
  if d.pop and d.pop0 and d.pop0 > 0 then
    local k = math.max(cfg.pop_min, math.min(cfg.pop_max, d.pop / d.pop0))
    m.work, m.carry, m.pop = k, k, d.pop / d.pop0
  end
  m.unrest = tonumber(d.unrest) or 0
  if m.unrest > cfg.unrest_hi then m.work = m.work * cfg.unrest_work; m.carry = m.carry * cfg.unrest_work; m.alarm = true end
  if d.food and d.food < cfg.famine_food then m.hungry = true; m.carry = m.carry * cfg.famine_buy; m.buy = cfg.famine_buy end
  return m
end
local function lim(n, k) return math.floor(n * k + 0.5) end
local function bump(tsid, k) local v = vis(tsid); if v then v[k] = (v[k] or 0) + 1 end end

---------------------------------------------------------------------------------------------- мир
local function game_day()
  local ok, d = pcall(function() return getGameWorld():getTimeStamp_inGameHours():getTotalDays() end)
  if ok and type(d) == "number" then return d end
  return nil
end
local function player_chars()
  local ok, list = pcall(function()
    local pi = getPlayerInterface()
    if not pi then return nil end
    local all = pi:getAllPlayerCharacters()
    if not all then return nil end
    local out = {}
    for _, c in pairs(all) do if c then out[#out + 1] = c end end
    return out
  end)
  if ok then return list end
  return nil   -- меню / загрузка — «не готов», не ошибка
end
local function xz(v) if v then return v.x or v[1], v.z or v[3] end end
local function d2(a, b) local ax, az = xz(a:getPosition()); local bx, bz = xz(b:getPosition()); return (ax - bx) ^ 2 + (az - bz) ^ 2 end
local function town_sid_of(obj, t0)   -- t0 — уже известное getCurrentTownLocation (из снимка Gov), иначе спрашиваем у объекта
  local t = t0
  if t == nil then t = obj:getCurrentTownLocation() end
  if not t then return nil end
  -- town override (захват/разорение) → исходная запись города: склад и дирижёр знают города по исходному sid
  local okg, og = pcall(function() local tt = t:isTown(); local g = tt and tt:getOriginalGameData(); return g and g.stringID end)
  if okg and og then return og end
  local gd = t:getGameData()
  return gd and gd.stringID
end
local function hkey(h) return h and h:toString() or nil end
-- SC (2026-11-15, ревью M6 того же класса): стадии цикла идут по тику, а сейв может смениться между ними. Персонажей из скана держим
-- как handle и берём свежими перед каждым шагом (hand:isValid / getCharacter); указатель прошлого мира не разыменовываем.
local function fresh(hd) if hd and hd:isValid() then return hd:getCharacter() end return nil end
local GD = {}
local function gd_item(sid, ty)
  if not GD[sid] then
    GD[sid] = getGameWorld().gamedata:getData(sid, ty or 4)   -- itemType.ITEM (оружие 2, броня 3 — от склада)
    if not GD[sid] then error("getData(ITEM) nil for " .. tostring(sid)) end
  end
  return GD[sid]
end

-- текущий город игрока (известный данным) и опорный персонаж игрока в нём
local function find_town(pcs)
  for _, pc in ipairs(pcs) do
    local t = town_sid_of(pc)
    if t and DATA.towns[t] then return { t, pc } end
  end
  return false
end

-- общий снимок загруженных NPC (PERF2): KMM_Gov.snapshot(ttl); нет Gov / ошибка → nil, и scan идёт прежним обходом
local function gov_snap()
  local g = rawget(_G, "KMM_Gov")
  if not (g and g.snapshot) or cfg.use_snapshot == false then return nil end
  local ok, snap = pcall(g.snapshot, cfg.snap_ttl or 4)
  if ok and type(snap) == "table" and snap.list then return snap end
  return nil
end
-- разбор одного персонажа города: мастер / носильщик-кандидат / торговец
local function classify(ch, out)
  local hd = ch:getHandle()
  local k = hkey(hd)
  out.by_key[k] = hd
  if ch:isATrader() then
    if ch:isResident() then out.shop[#out.shop + 1] = hd else out.caravan[#out.caravan + 1] = hd end
  else
    local act = ch:getBody() and ch:getBody():getCurrentAction()
    local key = act and act:key()
    local m, h
    if key and WORK[key] then
      h = act.subject
      local b = h and h:isValid() and h:getBuilding()
      local gd = b and b:getGameData()
      m = gd and DATA.machines[gd.stringID]
      if not m and gd and MINE[key] and cfg.mine_enabled then   -- ORE4: шахтёр города у рудного узла (носильщиком не берём)
        local O = rawget(_G, "KMM_Ore")
        local okk, res = pcall(function() return O and O.ore_kind and O.ore_kind(gd.stringID) end)
        if okk and res then out.miners[k] = true end
      end
    end
    if m then out.workers[#out.workers + 1] = { hd = hd, h = h, m = m, k = k }
    elseif out.miners[k] then
    elseif not (ch:isInCombatMode(true, true)) then out.idle[#out.idle + 1] = { hd = hd, k = k } end
  end
end

-- скан загруженных NPC рядом: мастера, свободные, торговцы (ошибки API ловит guard → «scan» отключается)
-- TRADE: по снимку скан идёт порциями (scan_begin/scan_step); без снимка - прежний целый проход (scan_full)
local function scan_full(tsid, anchor)
  local R2 = cfg.near_radius ^ 2
  local out = { workers = {}, idle = {}, shop = {}, caravan = {}, by_key = {}, miners = {} }
  local n = 0
  local set = getGameWorld():getCharacterUpdateList()
  for ch in pairs(set) do
    if not ch:isPlayerCharacter() and not ch:isDead() and not ch:isAnimal() and d2(ch, anchor) <= R2 and town_sid_of(ch) == tsid then
      n = n + 1
      if n > cfg.max_scan_chars then break end
      classify(ch, out)
    end
  end
  return out
end
local function scan_begin(tsid, anchor)
  local snap = gov_snap()
  if not snap then return { done = true, out = scan_full(tsid, anchor) } end
  local ax, az = xz(anchor:getPosition())
  return { snap = snap, i = 0, n = 0, tsid = tsid, ax = ax, az = az, R2 = cfg.near_radius ^ 2,
           out = { workers = {}, idle = {}, shop = {}, caravan = {}, by_key = {}, miners = {} } }
end
local function scan_step(c)   -- обработать до scan_chunk подходящих персонажей; true - список кончился или набрано max_scan_chars
  if c.done then return true end
  local list, got = c.snap.list, 0
  while c.i < #list do
    c.i = c.i + 1
    local r = list[c.i]
    if not r.dead and (r.x - c.ax) ^ 2 + (r.z - c.az) ^ 2 <= c.R2 then
      local ch = r.ch
      if town_sid_of(ch, r.town) == c.tsid and not ch:isAnimal() and not ch:isDead() then
        classify(ch, c.out)
        c.n = c.n + 1; got = got + 1
        if c.n >= cfg.max_scan_chars then c.done = true; return true end
        if got >= cfg.scan_chunk then return false end
      end
    end
  end
  c.done = true
  return true
end

---------------------------------------------------------------------------------------------- шаги цепочки
local function crate_count() return #RT.crate end
local function busy_carriers() local n = 0; for _ in pairs(RT.jobs) do n = n + 1 end; return n end

-- 1) мастер → ящик
local function craft(tsid, sc, day)
  local K = stock()
  if not K then RT.stats.waits_stock = RT.stats.waits_stock + 1; return 0 end
  local made, tried = 0, 0
  local nw = #sc.workers
  local md = RT.mood or { work = 1, buy = 1 }
  local max_w, max_i = lim(cfg.max_workers_per_cycle, md.work), lim(cfg.max_items_per_cycle, md.work * md.buy)
  while tried < math.min(nw, max_w) and made < max_i and crate_count() < cfg.max_crate_queue do
    tried = tried + 1
    RT.rr = RT.rr % nw + 1
    local w = sc.workers[RT.rr]
    if not (w.hd:isValid() and w.h:isValid()) then break end   -- мир сменился между стадиями: этот цикл без крафта
    local m = w.m
    local isid, ity = m.item, 4
    if not isid and (m.cat == "weapons" or m.cat == "armor") and type(K.pick_item) == "function" then   -- изделие по ярусу владельца: подбирает склад
      local okp, a, b = pcall(K.pick_item, tsid, m.cat)
      if okp then isid, ity = a, b elseif not off("stock_link") then link_fail("stock_link", a) end
      if off("stock_link") then return made end
    end
    if isid then
      local lv = stock_level(K, tsid, raw_cat(m.cat))
      if off("stock_link") then return made end
      if lv and lv >= cfg.min_level and stock_take(K, tsid, raw_cat(m.cat), cfg.units_per_item) >= cfg.units_per_item then
        local item = getGameWorld().theFactory:createItem(gd_item(isid, ity), nil, nil, nil, -1, nil)
        if not item then error("createItem nil for " .. isid) end
        local b = w.h:isValid() and w.h:getBuilding()
        local inv = b and b:getInventory()
        local where, owner = "crate", w.h
        if not (inv and inv:tryAddItem(item, 1)) then
          local wch = fresh(w.hd)
          if not wch then error("worker gone after stock take") end
          inv = wch:getInventory(); where, owner = "worker", w.hd
          if not inv:addItem(item, 1, false, true) then   -- 2026-11-15 игра: ящик и мастер полны — не ошибка, цикл ремесла на этом заканчивается
            RT.stats.craft_full = (RT.stats.craft_full or 0) + 1
            return made
          end
        end
        RT.crate[#RT.crate + 1] = { inv = inv, oh = owner, gd = gd_item(isid, ity), sid = isid, cat = m.cat, from = w.k }
        made = made + 1
        RT.stats.crafted = RT.stats.crafted + 1
        bump(tsid, "crafted")
        emit({ type = "town_craft", town_sid = tsid, town_name = DATA.towns[tsid], cat = m.cat, item = isid, n = 1, where = where,
               text = string.format("A craftsman in %s finished a batch of %s goods.", DATA.towns[tsid], m.cat) })
      elseif lv ~= nil and not off("stock_link") then   -- lv == nil: склад этот город не ведёт — молча пропускаем
        local key = tsid .. "|" .. m.cat
        if (day - (RT.short[key] or -1e9)) * 24 >= cfg.shortage_cooldown_hours then
          RT.short[key] = day
          tlog(string.format("workshops in %s idle: no %s (shelf %.2f)", DATA.towns[tsid], m.cat, lv))
          RT.stats.shortages = RT.stats.shortages + 1
          emit({ type = "town_shortage", town_sid = tsid, town_name = DATA.towns[tsid], cat = m.cat, level = lv,
                 text = string.format("Workshops in %s stand idle: no %s to work with.", DATA.towns[tsid], m.cat) })
        end
      end
    end
  end
  return made
end

-- ORE4) шахтёры у рудных узлов → жила города (KMM_Conductor.town_mined); часы - игровые с прошлого цикла, потолок mine_max_hours
local function mine(tsid, sc, day)
  if not cfg.mine_enabled then return 0 end
  local n = 0
  for _ in pairs(sc.miners or {}) do n = n + 1 end
  RT.mine_day = RT.mine_day or {}
  local last = RT.mine_day[tsid]
  RT.mine_day[tsid] = day
  RT.stats.miners = n
  if n == 0 or not last or day <= last then return 0 end
  local c = conductor()
  if not (c and type(c.town_mined) == "function") or off("conductor_link") then return 0 end
  local ok, got = pcall(c.town_mined, tsid, n * math.min(cfg.mine_max_hours, (day - last) * 24) * cfg.mine_rate)
  if not ok then link_fail("conductor_link", got); return 0 end
  h_ok("conductor_link")
  got = tonumber(got) or 0
  RT.stats.mined = (RT.stats.mined or 0) + got
  return got
end

-- 2) ящик → носильщик
local function haul(tsid, sc)
  local moved = 0
  if #sc.shop + #sc.caravan == 0 then return 0 end
  local used = {}
  for _, j in pairs(RT.jobs) do used[j.carrier] = true end
  for _, w in ipairs(sc.workers) do used[w.k] = true end
  local i = 1
  local max_c = lim(cfg.max_active_carriers, (RT.mood or { carry = 1 }).carry)
  while i <= #RT.crate and busy_carriers() < max_c do
    local c = RT.crate[i]
    local carrier
    for _, x in ipairs(sc.idle) do if not used[x.k] then carrier = x; break end end
    if not carrier then break end
    local cch = fresh(carrier.hd)
    local it = (cch and not (c.oh and not c.oh:isValid())) and c.inv:getItem(c.gd) or nil
    if not cch then used[carrier.k] = true                                        -- носильщик ушёл/мир сменился: следующий
    elseif not it then table.remove(RT.crate, i)                                 -- предмет уже забрали (игрок/торговец) или ящика нет
    else
      local got = c.inv:removeItemDontDestroy_returnsItem(it, 1, true)
      if not got then error("removeItemDontDestroy_returnsItem nil") end
      if not cch:getInventory():addItem(got, 1, false, true) then   -- 2026-11-15 игра: носильщик полон — вернуть в ящик, взять следующего
        c.inv:addItem(got, 1, false, true)
        used[carrier.k] = true
        RT.stats.haul_full = (RT.stats.haul_full or 0) + 1
      else
      local to_caravan = #sc.caravan > 0 and (#sc.shop == 0 or math.random() < cfg.caravan_share)
      RT.jobs[carrier.k] = { carrier = carrier.k, h = carrier.hd, gd = c.gd, sid = c.sid, cat = c.cat,
                             to = to_caravan and "caravan" or "shop", t_due = os.clock() + cfg.carry_seconds }
      used[carrier.k] = true
      table.remove(RT.crate, i)
      moved = moved + 1
      RT.stats.hauled = RT.stats.hauled + 1
      bump(tsid, "hauled")
      emit({ type = "town_haul", town_sid = tsid, town_name = DATA.towns[tsid], cat = c.cat, item = c.sid, n = 1, to = to_caravan and "caravan" or "shop" })
      end
    end
  end
  return moved
end

-- 3) носильщик → лавка / караван
local function deliver(tsid, sc)
  local now, done = os.clock(), 0
  for k, j in pairs(RT.jobs) do
    if now >= j.t_due then
      RT.jobs[k] = nil
      local ch = sc.by_key[k] and fresh(sc.by_key[k])
      local list = (j.to == "caravan" and #sc.caravan > 0) and sc.caravan or sc.shop
      if j.to == "caravan" and #sc.caravan == 0 then j.to = "shop" end
      local dst = list[1] and fresh(list[1])
      if ch and dst then
        local inv = ch:getInventory()
        local it = inv:getItem(j.gd)
        if it then
          local got = inv:removeItemDontDestroy_returnsItem(it, 1, true)
          if not got then error("removeItemDontDestroy_returnsItem nil (deliver)") end
          if not dst:getInventory():addItem(got, 1, false, true) then error("trader addItem failed") end
          done = done + 1
          RT.stats.delivered = RT.stats.delivered + 1
          bump(tsid, "delivered")
          if j.cat == "weapons" or j.cat == "armor" then   -- тот же предмет дошёл до лавки/каравана: изделие засчитано складу
            local K = stock()
            if K and not off("stock_link") and stock_made(K, tsid, j.cat, cfg.units_per_item) > 0 then bump(tsid, "stocked") end
          end
          if j.to == "caravan" then
            RT.stats.to_caravan = RT.stats.to_caravan + 1
            bump(tsid, "to_caravan")
            tlog(string.format("caravan loaded in %s: %s (%s) onto a passing trader", DATA.towns[tsid], j.cat, tostring(j.sid)))
            emit({ type = "town_caravan_loaded", town_sid = tsid, town_name = DATA.towns[tsid], cat = j.cat, item = j.sid, n = 1,
                   text = string.format("Porters in %s loaded %s goods onto a passing caravan.", DATA.towns[tsid], j.cat) })
          else
            emit({ type = "town_delivered", town_sid = tsid, town_name = DATA.towns[tsid], cat = j.cat, item = j.sid, n = 1 })
          end
        end
      end   -- носильщик ушёл/выгружен: предмет остаётся у него (его собственность), без ошибки
    end
  end
  return done
end

---------------------------------------------------------------------------------------------- U3: голод города в его постройках
-- Рычаг ядра (✓код, BindingsReference ProductionBuilding / StorageBuilding::ConsumptionItem; ✓игра — ещё нет):
--   вход постройки (consumptionItems[i].amount) обнуляется, изъятое помнится в слоте дирижёра S.town[tsid].u3 (едет в сейве),
--   productionState = PRODUCTION_STARVED. Откат: вход = min(maxCapacity, текущий + изъятый); изымается только то, что влезет обратно.
-- Без слота дирижёра (нечем откатить после сейва) и у построек без входов (фермы) — только productionState: его ваниль пересчитает сама.
-- productionMult не трогаем (ревью batch5 H3: мог бы остаться x0.2 в сейве навсегда).
-- Если запись в элемент lektor не держится (копия) — первая же проверка это видит, дальше только productionState.
-- famine_enabled = false: изъятое по записям слота возвращается при каждом проходе, пока записи есть.
-- Жители: у TownBase::ResidentData в Lua нет полей — рычага числа жителей нет; население действует через town_mood (лимиты работы).
local U3 = { PS_STARVED = 0, PS_NORMAL = 2, BF_MINE = 1, BF_MINE_NATURAL = 27, BCTYPE_FARM = 13, buf = nil, last = {}, pop_noted = false }
function U3.log(msg)
  if not cfg or RT.nu3 >= (cfg.u3_log_max or 200) then return end
  RT.nu3 = RT.nu3 + 1
  append(cfg.trade_log_path or DEFAULTS.trade_log_path, os.date("%Y-%m-%d %H:%M:%S") .. "\tU3 " .. tostring(msg))
end
function U3.store(tsid)   -- -> записи, persist. Слот дирижёра (едет в сейве) — входы можно изымать;
  local c = conductor()      -- без него — память сессии, и записи там только о productionState (входы не трогаем)
  if c and type(c.town_state) == "function" and not off("conductor_link") then
    local ok, T = pcall(c.town_state)
    if ok and type(T) == "table" then
      T[tsid] = T[tsid] or {}
      T[tsid].u3 = T[tsid].u3 or {}
      return T[tsid].u3, true
    end
  end
  RT.fstore_local[tsid] = RT.fstore_local[tsid] or {}
  return RT.fstore_local[tsid], false
end
function U3.pf()
  local c = conductor()
  if not (c and type(c.cfg) == "function") then return nil end
  local ok, v = pcall(c.cfg)
  return ok and type(v) == "table" and v.player_faction or nil
end
function U3.is_player(b, pf)
  if b:isThePlayer() then return true end
  if not pf then return false end
  local ok, sid = pcall(function() local f = b:getFaction(); local g = f and f.data; return g and g.stringID end)
  return ok and sid == pf
end
function U3.cat(b, sid)   -- категория склада, от которой живёт постройка: машина из данных (кузня — металл) или ферма — еда
  local m = DATA.machines[sid]
  if m and m.cat then return raw_cat(m.cat) end
  if b:getBuildingClass() == U3.BCTYPE_FARM then return "food" end
  return nil
end
function U3.key(b, sid)   -- шаблон + позиция: ключ переживает перезагрузку (handle — нет)
  local x, z = xz(b:getPosition())
  return string.format("%s@%d,%d", sid, math.floor((x or 0) / 4 + 0.5), math.floor((z or 0) / 4 + 0.5))
end
function U3.collect(tsid, anchor)   -- загруженные производства города рядом с игроком (не игрока, не шахты KMM_Ore)
  local gw = rawget(_G, "lektor") and getGameWorld()
  local okm, fn = false, nil
  if gw then okm, fn = pcall(function() return gw.getObjectsWithinSphere end) end
  if not (okm and fn) then   -- нет контейнеров/запроса сферы (не та версия KenshiLua, офлайн-заглушки): тихо без U3
    if not U3.unavail then U3.unavail = true; U3.log("unavailable: no lektor/getObjectsWithinSphere, famine in buildings off") end
    return nil
  end
  if not U3.buf then U3.buf = lektor.new("RootObject*") end   -- один буфер на сессию (ContainersReference)
  U3.buf:clear()
  -- буфер первым аргументом — форма из примера ContainersReference и KMM_Stock (BindingsReference выходной lektor не перечисляет)
  getGameWorld():getObjectsWithinSphere(U3.buf, anchor:getPosition(), cfg.famine_radius, 0, cfg.famine_max_objects, nil)   -- 0 = itemType.BUILDING
  local pf, out = U3.pf(), {}
  for _, o in ipairs(U3.buf) do
    if #out >= cfg.famine_max_buildings then break end
    local okb, b = pcall(function() return o:getHandle():getBuilding() end)
    local pb = okb and b and b:getProductionBuilding()
    if pb and not U3.is_player(b, pf) then
      local sf = b:getSpecialFunction()
      if sf ~= U3.BF_MINE and sf ~= U3.BF_MINE_NATURAL then
        local gd = b:getGameData()
        local sid = gd and gd.stringID
        local cat = sid and U3.cat(b, sid)
        if cat and town_sid_of(b, b:getTown()) == tsid then
          out[#out + 1] = { b = b, pb = pb, sid = sid, cat = cat, key = U3.key(b, sid) }
        end
      end
    end
  end
  table.sort(out, function(a, c) return a.key < c.key end)
  return out
end
function U3.starve(e, day, store, tsid, persist)
  local rec = { t = day, cat = e.cat, ps = e.pb.productionState }
  local lek = (persist and RT.u3.inputs_ok ~= false) and e.pb.consumptionItems or nil
  local n = lek and #lek or 0
  if n > 0 then
    rec.a = {}
    local any = false
    for i = 1, n do
      local ci = lek[i]
      local cap = ci and tonumber(ci.maxCapacity) or 0
      if ci and cap > 0 then   -- без известного потолка не изымаем: вернуть изъятое не сможем гарантировать
        local cur = tonumber(ci.amount) or 0
        local a = math.min(cur, cap)
        rec.a[i] = a; if a > 0 then any = true end
        ci.amount = cur - a
      end
    end
    if RT.u3.inputs_ok == nil and any then   -- первая запись сессии: держится ли она в памяти движка
      local c1 = e.pb.consumptionItems[1]
      RT.u3.inputs_ok = (c1 ~= nil and (tonumber(c1.amount) or 0) == 0)
      U3.log(string.format("check inputs_write=%d b=%s", RT.u3.inputs_ok and 1 or 0, e.sid))
    end
    if RT.u3.inputs_ok == false or not next(rec.a) then rec.a = nil end
  end
  e.pb.productionState = U3.PS_STARVED
  store[e.key] = rec
  RT.fh[e.key] = { h = e.b:getHandle(), tsid = tsid, mem = not persist }
end
function U3.reassert(e, rec)   -- остановленная постройка: ванильный подвоз снова изымается, состояние держится
  local st = e.pb.productionState
  if st == U3.PS_STARVED then RT.u3.kept = RT.u3.kept + 1 else RT.u3.flipped = RT.u3.flipped + 1 end
  if rec.a then
    local lek = e.pb.consumptionItems
    for i = 1, #lek do
      local ci = lek[i]
      local a = ci and tonumber(ci.amount) or 0
      local cap = ci and tonumber(ci.maxCapacity) or 0
      local take = math.min(a, cap - (rec.a[i] or 0))   -- только то, что потом влезет обратно (ревью M7: сверх потолка не уничтожать)
      if take > 0 then rec.a[i] = (rec.a[i] or 0) + take; ci.amount = a - take end
    end
  end
  if st ~= U3.PS_STARVED then e.pb.productionState = U3.PS_STARVED; RT.u3.reassert = RT.u3.reassert + 1 end
end
function U3.restore(b, pb, rec)
  if rec.a then
    local lek = pb.consumptionItems
    for i, v in pairs(rec.a) do
      local ci = lek[tonumber(i)]
      if ci then
        local cap, nv = tonumber(ci.maxCapacity) or 0, (tonumber(ci.amount) or 0) + (tonumber(v) or 0)
        ci.amount = cap > 0 and math.min(nv, cap) or nv
      end
    end
  end
  if pb.productionState == U3.PS_STARVED then
    pb.productionState = (rec.ps ~= nil and rec.ps ~= U3.PS_STARVED) and rec.ps or U3.PS_NORMAL
  end
end
function U3.restore_all(reason)   -- выход из города / самоотключение: откат у всех ещё загруженных; выгруженные ждут в store
  local n, lost = 0, 0
  for key, r in pairs(RT.fh) do
    local ok, done = pcall(function()
      if not (r.h and r.h:isValid()) then return false end
      local b = r.h:getBuilding()
      local pb = b and b:getProductionBuilding()
      local store = r.mem and RT.fstore_local[r.tsid] or U3.store(r.tsid)
      local rec = store and store[key]
      if not (pb and rec) then return false end
      U3.restore(b, pb, rec)
      store[key] = nil
      return true
    end)
    if ok and done then n = n + 1 else lost = lost + 1 end
  end
  RT.fh = {}
  RT.u3.restored, RT.u3.lost = RT.u3.restored + n, RT.u3.lost + lost
  if n + lost > 0 then U3.log(string.format("restore_all reason=%s n=%d unloaded=%d", tostring(reason), n, lost)) end
end
function U3.unwind(tsid, anchor, reason)   -- famine_enabled = false: вернуть изъятое (загруженным — сразу, выгруженным — когда загрузятся)
  if next(RT.fh) then U3.restore_all(reason) end
  local store = U3.store(tsid)
  if not next(store) then return end
  local list = U3.collect(tsid, anchor)
  for _, e in ipairs(list or {}) do
    local rec = store[e.key]
    if rec then
      U3.restore(e.b, e.pb, rec); store[e.key] = nil
      RT.u3.restored = RT.u3.restored + 1
      U3.log(string.format("restore town=%s b=%s reason=%s", DATA.towns[tsid] or tostring(tsid), e.sid, reason))
    end
  end
end
function U3.pass(tsid, anchor, day)
  if not anchor then return end
  if not cfg.famine_enabled then U3.unwind(tsid, anchor, "config_off"); return end
  local K = stock()
  if not K then return end
  if not U3.pop_noted then
    U3.pop_noted = true
    U3.log("pop lever: none in Lua (TownBase::ResidentData has no bound fields); population acts via town_mood work limits")
  end
  local list = U3.collect(tsid, anchor)
  if not list then return end
  local store, persist = U3.store(tsid)
  RT.u3.passes, RT.u3.seen = RT.u3.passes + 1, #list
  local groups, order = {}, {}
  for _, e in ipairs(list) do
    local g = groups[e.cat]
    if not g then g = {}; groups[e.cat] = g; order[#order + 1] = e.cat end
    g[#g + 1] = e
  end
  table.sort(order)
  local budget = cfg.famine_changes_per_cycle
  local tn = DATA.towns[tsid] or tostring(tsid)
  for _, cat in ipairs(order) do
    local g = groups[cat]
    local lv = stock_level(K, tsid, cat)
    if off("stock_link") then return end
    if lv then
      local f = math.max(0, math.min(1, (cfg.famine_hi - lv) / (cfg.famine_hi - cfg.famine_lo)))
      local target = math.floor(f * #g + 0.5)
      local ns = 0
      for _, e in ipairs(g) do
        local rec = store[e.key]
        if rec then
          ns = ns + 1
          if not RT.fh[e.key] then   -- остановлена в прошлой сессии/заходе: снова под присмотром
            RT.fh[e.key] = { h = e.b:getHandle(), tsid = tsid, mem = not persist }
            RT.u3.adopted = RT.u3.adopted + 1
            U3.log(string.format("adopt town=%s b=%s cat=%s", tn, e.sid, cat))
          end
          U3.reassert(e, rec)
        end
      end
      for _, e in ipairs(g) do
        if ns >= target or budget <= 0 then break end
        if not store[e.key] then
          U3.starve(e, day, store, tsid, persist)
          ns, budget = ns + 1, budget - 1
          RT.u3.starved = RT.u3.starved + 1
          U3.log(string.format("starve town=%s b=%s cat=%s shelf=%.2f inputs=%d state=%s", tn, e.sid, cat, lv,
            store[e.key].a and #store[e.key].a or 0, tostring(e.pb.productionState)))
        end
      end
      for i = #g, 1, -1 do
        if ns <= target or budget <= 0 then break end
        local e = g[i]
        local rec = store[e.key]
        if rec and (day - (rec.t or -1e9)) * 24 >= cfg.famine_hold_hours then
          U3.restore(e.b, e.pb, rec)
          store[e.key], RT.fh[e.key] = nil, nil
          ns, budget = ns - 1, budget - 1
          RT.u3.restored = RT.u3.restored + 1
          U3.log(string.format("restore town=%s b=%s cat=%s shelf=%.2f reason=stock state=%s", tn, e.sid, cat, lv, tostring(e.pb.productionState)))
        end
      end
      local lk = tsid .. "|" .. cat
      local sig = ns .. "/" .. #g
      if U3.last[lk] ~= sig then
        U3.last[lk] = sig
        U3.log(string.format("town=%s cat=%s shelf=%.2f starved=%s target=%d kept=%d flipped=%d", tn, cat, lv, sig, target, RT.u3.kept, RT.u3.flipped))
      end
    end
  end
end
local g_famine = guarded("famine", U3.pass)
local famine_find   -- = g_find (объявлен ниже)
local function famine_stage(day)   -- опорный персонаж — свежий (ревью M6: Character* через тики не держим — сейв мог смениться)
  if off("famine") or U3.unavail or not rawget(_G, "lektor") then return end   -- без контейнеров U3 недоступен: и опроса нет
  local pcs = player_chars()
  if not pcs or #pcs == 0 then RT.stage = nil; return end
  local ft = famine_find and famine_find(pcs)
  if not (ft and ft[1] == RT.town) then return end
  g_famine(RT.town, ft[2], day)
  if off("famine") then   -- самоотключение: всё изъятое вернуть сразу
    pcall(U3.restore_all, "disabled")
    U3.log("off: famine paused or disabled (reason in debug.log, KMM_Gov health KMM_Town.famine)")
  end
end

local g_find = guarded("find_town", find_town)
famine_find = g_find
local g_sbegin, g_sstep = guarded("scan", scan_begin), guarded("scan", scan_step)
local g_craft, g_haul, g_deliver = guarded("craft", craft), guarded("haul", haul), guarded("deliver", deliver)
local g_mine = guarded("mine", mine)

---------------------------------------------------------------------------------------------- тик
local function reset_ready() RT.ready, RT.polls, RT.seen_clock, RT.seen_day = false, 0, nil, nil end
local function leave_town(walked)   -- walked: игрок ушёл из города (постройки ещё загружены) — U3 откатывает; меню/загрузка — только забыть
  if next(RT.fh) then
    if walked and not off("famine") then pcall(U3.restore_all, "leave") else RT.fh = {} end
  end
  RT.town, RT.crate, RT.jobs, RT.stage, RT.sc = nil, {}, {}, nil, nil
  RT.mine_day = {}
end

-- TRADE: цикл цепочки идёт стадиями по одному вызову тика (find+scan порциями -> mood -> deliver -> craft -> haul -> итог),
-- чтобы не складывать скан и три шага цепочки в один кадр (бюджет Gov 0.6 мс на модуль).
local function stage_scan()
  local c = RT.sc
  if not c then return "done" end
  local r = g_sstep(c)
  if r == nil then return "done" end   -- шаг отключён guard-ом
  if r then return "next" end
  return "again"
end
local function cycle_summary()
  local st, b = RT.stats, RT.base or {}
  local dc, dh, dd, dv = st.crafted - (b.crafted or 0), st.hauled - (b.hauled or 0), st.delivered - (b.delivered or 0), st.to_caravan - (b.to_caravan or 0)
  local dm = (st.mined or 0) - (b.mined or 0)   -- ORE4: руда, вынутая шахтёрами города из его жилы
  RT.base = { crafted = st.crafted, hauled = st.hauled, delivered = st.delivered, to_caravan = st.to_caravan, mined = st.mined or 0 }
  if dc + dh + dd + dv > 0 or dm > 0.05 then
    tlog(string.format("%s cycle: crafted=%d hauled=%d delivered=%d to_caravan=%d (crate=%d)%s", DATA.towns[RT.town] or tostring(RT.town), dc, dh, dd, dv, #RT.crate,
      dm > 0.05 and string.format(" ore=%.1f miners=%d", dm, st.miners or 0) or ""))
  end
end
local STAGES = {
  function(day)   -- 1: mood и тревога
    RT.mood = mood_of(RT.town)
    if RT.mood.alarm then
      RT.alarm = RT.alarm or {}
      if (day - (RT.alarm[RT.town] or -1e9)) * 24 >= cfg.alarm_cooldown_hours then
        RT.alarm[RT.town] = day
        RT.stats.alarms = (RT.stats.alarms or 0) + 1
        emit({ type = "town_alarm", town_sid = RT.town, town_name = DATA.towns[RT.town], unrest = RT.mood.unrest,
               text = string.format("%s is restless: shops shutter early and the guards are doubled.", DATA.towns[RT.town]) })
      end
    end
  end,
  function(day) g_mine(RT.town, RT.sc.out, day) end,   -- ORE4: шахтёры города → жила города
  function(day) g_deliver(RT.town, RT.sc.out) end,
  function(day) g_craft(RT.town, RT.sc.out, day) end,
  function(day) g_haul(RT.town, RT.sc.out) end,
  function(day) famine_stage(day) end,   -- U3: голод в постройках города
  function(day) cycle_summary() end,
}

local function tick()
  local t = os.clock()
  if RT.ready and RT.stage and t - (RT.t_stage or 0) >= 0.05 then   -- следующая стадия цикла: один квант за вызов
    RT.t_stage = t
    local day = game_day()
    local st = RT.stage
    if not day or not RT.town then RT.stage, RT.sc = nil, nil
    elseif st == 0 then   -- скан порциями
      local r = stage_scan()
      if r == "done" then RT.stage, RT.sc = nil, nil elseif r == "next" then RT.stage = 1 end
    else
      local fn = STAGES[st]
      RT.stage = STAGES[st + 1] and (st + 1) or nil
      if fn then
        local ok, err = pcall(fn, day)
        if not ok then fail("stage" .. st, err); RT.stage = nil end
      end
      if not RT.stage then RT.sc = nil end
    end
    return
  end
  if t - RT.t_poll < ((cfg and cfg.poll_seconds) or DEFAULTS.poll_seconds) then return end
  RT.t_poll = t
  local pcs = player_chars()
  if not pcs or #pcs == 0 then if RT.ready or RT.seen_clock then reset_ready(); leave_town() end; return end
  if not cfg then load_cfg() end
  if not cfg.enabled then return end
  local day = game_day()
  if not day then return end
  if not RT.ready then
    RT.polls = RT.polls + 1
    if not RT.seen_clock then RT.seen_clock, RT.seen_day = t, day; return end
    if RT.polls < cfg.start_delay_polls or t - RT.seen_clock < cfg.start_delay_seconds
       or (day - RT.seen_day) * 24 < cfg.start_delay_hours then return end
    RT.ready = true
  end
  if RT.stage then return end
  if t - RT.t_cycle < cfg.cycle_seconds then return end
  RT.t_cycle = t
  local ft = g_find(pcs)
  local tsid, anchor = ft and ft[1], ft and ft[2]
  if tsid ~= RT.town then
    leave_town(RT.town ~= nil); RT.town = tsid
    if tsid then tlog("player entered " .. tostring(DATA.towns[tsid]) .. ": trade chain active") end
  end
  if not tsid then return end
  if not stock() then RT.stats.waits_stock = RT.stats.waits_stock + 1; return end   -- без склада — тихо ждём
  local sc = g_sbegin(tsid, anchor)
  if not sc then return end
  RT.stats.cycles = RT.stats.cycles + 1
  RT.sc = sc
  RT.stage = 0
  RT.t_stage = t
end
local g_tick = guarded("tick", tick)
local function on_load()   -- загружен сейв: всё, что держит объекты прошлого мира (скан, ящик, носильщики, U3), забыть до первого тика
  leave_town(false); reset_ready()
  RT.t_cycle = -1e9
end

---------------------------------------------------------------------------------------------- регистрация: только общий тик
KMM_Town = KMM_Town or {}
KMM_Town.version = VERSION
KMM_Town.tick = function() g_tick() end
KMM_Town.disabled = function() return DISABLED end
KMM_Town.stats = function() return RT.stats end
KMM_Town.status = function()
  local d = {}
  for k in pairs(DISABLED) do d[#d + 1] = k end
  table.sort(d)
  return string.format("%s ready=%s town=%s crate=%d carriers=%d crafted=%d delivered=%d caravan=%d disabled=%s", VERSION, tostring(RT.ready),
    tostring(RT.town), #RT.crate, busy_carriers(), RT.stats.crafted, RT.stats.delivered, RT.stats.to_caravan, table.concat(d, ","))
end
KMM_Town.u3 = function() return RT.u3 end   -- U3: счётчики голода в постройках (passes/starved/restored/kept/flipped/...)
KMM_Town._rt = RT
rawset(_G, "KMM_Town", KMM_Town)

if KMM_Town._handler and Events and Events.off then pcall(Events.off, KMM_Town._handler) end   -- перезагрузка скрипта не дублирует
if KMM_Town._load_handler and Events and Events.off then pcall(Events.off, KMM_Town._load_handler) end
if Events and Events.on then KMM_Town._handler = Events.on("GameWorld::charsUpdate", guarded("tick_hook", function(...) if _G.KMM_Gov then return KMM_Gov.run("town", g_tick, ...) else return g_tick(...) end end)) end
if Events and Events.on then KMM_Town._load_handler = Events.on("PlayerInterface::loadFromSerialise", guarded("load_hook", on_load)) end
