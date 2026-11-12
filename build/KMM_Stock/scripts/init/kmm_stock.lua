-- KMM_Stock v1 (2026-11-12) — рантайм складов городов (DESIGN «Материальный мир»). Модель — scripts/kmm_stock_model.lua.
--
-- Безопасный путь (как KMM_Ore v2):
--   * при загрузке — только функции, таблица _G.KMM_Stock и один обработчик общего тика GameWorld::charsUpdate; ни I/O, ни API игры;
--   * старт лениво: дирижёр опубликован (_G.KMM_Conductor), у игрока есть персонажи, задержка (секунды + опросы + игровое время);
--   * склад живёт в состоянии дирижёра (S.stock) и сохраняется вместе с ним в gameData.sdata — своего сейва нет;
--   * раз в игровой день — M.day (с догоном пропущенных дней порциями), события stock_* → шина дирижёра (KMM_Conductor.emit);
--   * материализация только рядом с игроком: ближайшие лавки/склады и торговцы раз в revisit_days, лимит зданий и операций за проход,
--     вещи добавляются только при наличии места (hasRoomForItem, destroyOnFail), товар списывается со склада города;
--   * каждая функция под guard: первая ошибка отключает только её до конца сессии, причина → logs/debug.log; наружу не выходит.
-- Реликты, «божественное», Crafting Redux и дерево Relics в лавки не кладутся (списки kmm_stock_items.lua, tools/streams/stock.py).

local TAG = "[KMM_Stock] "
local VERSION = "v1"

local DEFAULTS = {
  enabled = true,
  debug_log = "C:/KenshiModMap/logs/debug.log", log_path = "C:/KenshiModMap/logs/stock.log",
  start_delay_seconds = 10, start_delay_polls = 10, start_delay_hours = 0.05, poll_seconds = 1.0,
  max_days_per_tick = 2, max_gap_days = 60,
  materialize = true, scan_seconds = 6, scan_radius = 1800, max_objects = 60, max_buildings_per_pass = 3,
  max_ops_per_pass = 12, revisit_days = 1,
  traders = true, max_traders_per_pass = 2,
  native_refresh = true,        -- NATIVE: перед нашей раздачей торговцу - родной ActivePlatoon:refreshInventory(false) (по vendors refresh time), под крэш-сторожем
  storage = true, storage_cats = { "food", "metal", "scrap", "med" },
  weapons_add = false,          -- createItem для WEAPON без материала/производителя не проверен в игре: по умолчанию только снятие
  remove_when_short = true,
  npc_buys = true, npc_buy_seconds = 12, npc_buy_chance = 0.25, npc_inventory_max = 14, npc_buy_radius = 1500,
  units_per_item = { food = 1, med = 1, drugs = 1, lux = 1, metal = 1, scrap = 1, weapons = 1, armor = 1 },   -- 1 вещь = 1 единица (как у TOWN)
  slots = { shop = 10, storage = 6, trader = 8 },
  deficit = 0.2,
  player_sales = true, sale_seconds = 8, sale_radius = 300, sale_max_items = 60, sale_emit_min = 5, sale_max_objects = 20,
  use_snapshot = true, snap_ttl = 4,   -- PERF2: обход NPC через KMM_Gov.snapshot (нет Gov / ошибка — свой обход)
  day_chunk = 40, trade_log = true, trade_log_max = 1500,   -- TRADE: день склада порциями по day_chunk городов за кадр; строки TRADE в stock.log (не более trade_log_max за сессию)
  rot_apply = true, rot_away_radius = 4500, rot_apply_ops = 8,   -- TOWNLIFE: ротация лавок (модель - M.rot_try); игрок дальше rot_away_radius от города; вещей за проход
  relic_forge = true, relic_seconds = 30, relic_names = { ["Relic AI Core"] = true }, relic_sids = {},
  -- R1: цена категории для родных цен города (Town.tradeGoodsMults через KMM_Traces): пусто x(1+def), норма x1, переполнение (уровень 3) x(1-2*glut);
  -- осада дорожит снаряжение и еду, контрабанда - M.price; пределы min..max; cat_max - вещей категории на город
  tgm = { def = 0.6, glut = 0.15, glut_lv = 2.5, min = 0.6, max = 1.8, cat_max = 40, siege = { weapons = 1.3, armor = 1.25, med = 1.25, food = 1.15 } },
}

local cfg, M, ITEMS
local DISABLED = {}
local RT = { jobs = {}, nlog = 0, dctx = nil, t_poll = 0, ready = false, polls = 0, seen_clock = nil, seen_day = nil, S = nil, t_scan = 0, t_buy = 0,
             visited = {}, nvisited = 0, snap = {}, nsnap = 0, rebase_town = {}, t_sale = 0, t_relic = 0,
             stats = { days = 0, added = 0, removed = 0, buildings = 0, traders = 0, buys = 0, events = 0, sales = 0, sold_items = 0, relic = 0 } }

---------------------------------------------------------------------------------------------- лог и guard
local function append(path, line)
  local ok, f = pcall(io.open, path, "a")
  if ok and f then f:write(line, "\n"); f:close(); return true end
  return false
end
local function klog(msg)
  msg = TAG .. tostring(msg)
  if not (KenshiLua and pcall(function() KenshiLua.log(msg) end)) then print(msg) end
end
local function slog(msg) append((cfg and cfg.log_path) or DEFAULTS.log_path, os.date("%Y-%m-%d %H:%M:%S") .. "\t" .. tostring(msg)) end
local function tlog(msg)   -- TRADE: редкая строка о реальном видимом событии торговли (<= 1 на событие, потолок за сессию)
  if not (cfg and cfg.trade_log) or RT.nlog >= (cfg.trade_log_max or 1500) then return end
  RT.nlog = RT.nlog + 1
  slog("TRADE " .. tostring(msg))
end
local function dlog(msg)
  append((cfg and cfg.debug_log) or DEFAULTS.debug_log, os.date("%Y-%m-%d %H:%M:%S") .. " [KMM_Stock] " .. tostring(msg))
  klog(msg)
end
local function guarded(nm, fn)
  return function(...)
    if DISABLED[nm] then return end
    local ok, a, b = pcall(fn, ...)
    if not ok then DISABLED[nm] = true; dlog(nm .. " disabled until restart: " .. tostring(a)); return nil end
    return a, b
  end
end
local function game_day()
  local ok, d = pcall(function() return getGameWorld():getTimeStamp_inGameHours():getTotalDays() end)
  if ok and type(d) == "number" then return d end
  return nil
end
local function clamp(x, a, b) if x < a then return a elseif x > b then return b end return x end

---------------------------------------------------------------------------------------------- конфиг и модули (лениво)
local function load_cfg()
  local c = {}
  for k, v in pairs(DEFAULTS) do c[k] = v end
  local ok, user = pcall(require, "stock_config")
  if ok and type(user) == "table" then for k, v in pairs(user) do c[k] = v end end
  cfg = c
  local okM, m = pcall(require, "kmm_stock_model")
  if not (okM and type(m) == "table" and m.day) then error("kmm_stock_model not loaded: " .. tostring(m)) end
  M = m
  M.rot_log = function(msg) tlog(msg) end   -- «shop rotated in <город>: <было> -> <стало>», <= 1 на событие
  local okI, it = pcall(require, "kmm_stock_items")
  ITEMS = (okI and type(it) == "table") and it or nil
  if not ITEMS then klog("kmm_stock_items not loaded — materialization off: " .. tostring(it)) end
end

---------------------------------------------------------------------------------------------- дирижёр
local function conductor() local C = rawget(_G, "KMM_Conductor"); if type(C) == "table" and C.state then return C end end
local function ccfg() local C = conductor(); local ok, v = pcall(function() return C and C.cfg and C.cfg() end); return ok and v or nil end

local function tname(tsid) local I = (ccfg() or {}).town_info; return (I and I[tsid] and I[tsid].name) or tostring(tsid) end

local function ensure_stock(S)
  local CF = ccfg() or {}
  local had = type(S.stock) == "table" and S.stock.v == M.VERSION and S.stock.towns ~= nil   -- склад приехал из сейва (или уже жил в этой сессии)
  if type(S.stock) ~= "table" or S.stock.v ~= M.VERSION then S.stock = {} end
  if RT.S ~= S or not S.stock.towns then
    M.init(S.stock, S, CF)
    RT.S = S
    RT.dctx = nil   -- смена состояния (загрузка сейва): недосчитанный день бросаем
    RT.visited, RT.nvisited = {}, 0
    slog(string.format("KMM_Stock %s active: towns=%d last_day=%.0f source=%s", VERSION,
      (function() local n = 0; for _ in pairs(S.stock.towns) do n = n + 1 end; return n end)(), S.stock.last_day or -1,
      had and "save/session" or "new (not in save)"))
  end
  return S.stock
end

local function emit(ev)
  RT.stats.events = RT.stats.events + 1
  local C = conductor()
  if C and C.emit then return C.emit(ev) end
end

-- TRADE: дневной расчёт порциями (M.day_begin / day_step по day_chunk городов за кадр / day_end_part по частям), чтобы один вызов
-- не превышал бюджет Gov. Начало дня - в опросе, продолжение - в следующих кадрах (pump). Дни догоняются по одному.
local function model_step(S, day)
  local st = ensure_stock(S)
  if RT.dctx then return end
  local d = math.floor(day)
  local last = st.last_day or -1
  local nxt
  if last < 0 then nxt = d
  else
    if d - last > cfg.max_gap_days then st.last_day = d - cfg.max_gap_days; last = st.last_day end
    if last < d then nxt = last + 1 end
  end
  if not nxt then return end
  local ev0 = RT.stats.events
  local ctx = M.day_begin(st, S, nxt, emit)
  if ctx then ctx.ev0, ctx.frames, ctx.t0 = ev0, 1, os.clock(); RT.dctx, RT.dph, RT.dend = ctx, "towns", 0 end
end
local g_model = guarded("model", model_step)
local function day_advance()   -- один квант дня; вызывается из pump по кадрам
  local c = RT.dctx
  c.frames = c.frames + 1
  if RT.dph == "towns" then
    if M.day_step(c, cfg.day_chunk) then RT.dph, RT.dend = "end", 0 end
  else
    RT.dend = RT.dend + 1
    if M.day_end_part(c, RT.dend) then
      RT.dctx = nil
      RT.stats.days = RT.stats.days + 1
      local st = RT.S and RT.S.stock
      tlog(string.format("stock day %d computed: towns=%d frames=%d bus_events=%d added=%d removed=%d buys=%d sales=%d last_day=%d", c.day, c.n, c.frames,
        RT.stats.events - (c.ev0 or 0), RT.stats.added, RT.stats.removed, RT.stats.buys, RT.stats.sales, st and st.last_day or -1))
    end
  end
end
local g_dayadv = guarded("model", function() return day_advance() end)

---------------------------------------------------------------------------------------------- игрок и окружение
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
  return nil   -- главное меню / загрузка — «не готов», не ошибка
end
local function install_away()
  if M.away then return end
  M.away = function(tsid)   -- ротируем лавку, только когда ни один персонаж игрока не рядом с городом (игрок не видит смену)
    local ok, res = pcall(function()
      local I = (ccfg() or {}).town_info
      I = I and I[tsid]
      local pcs = player_chars()
      if not (I and I.x and pcs and #pcs > 0) then return false end
      local r2 = cfg.rot_away_radius ^ 2
      for i = 1, math.min(#pcs, 12) do
        local p = pcs[i]:getPosition()
        if (p.x - I.x) ^ 2 + (p.z - I.z) ^ 2 < r2 then return false end
      end
      return true
    end)
    return ok and res or false
  end
end

local function gd_of(o)   -- в игре: у Faction нет getGameData (лог 2026-11-12), данные в поле data; у RootObjectBase/Town есть getGameData
  if not o then return nil end
  local ok, gd = pcall(function() return o.data end)
  if ok and gd then return gd end
  ok, gd = pcall(function() return o:getGameData() end)
  if ok and gd then return gd end
  ok, gd = pcall(function() return o:getData() end)
  return ok and gd or nil
end
local function fid_of(obj) local f = obj:getFaction(); local gd = gd_of(f); return gd and gd.stringID end
local function raw_building(o) return o:getHandle():getBuilding() end   -- без замыканий в тике (PERF2)
local function raw_key(obj) return obj:getHandle():toString() end
local function as_building(o)   -- getObjectsWithinSphere отдаёт RootObject: isAShop/getInventory есть только у Building -> приведение через handle (только чтение)
  local ok, b = pcall(raw_building, o)
  return ok and b or nil
end
local function key_of(obj)
  local ok, k = pcall(raw_key, obj)
  if ok and type(k) == "string" and k ~= "" then return k end
  return tostring(obj)
end
local function tsid_of(t) local gd = gd_of(t); return gd and gd.stringID end
local function town_of_building(b) return tsid_of(b:getTown()) end
local function town_of_char(ch) return tsid_of(ch:getCurrentTownLocation()) end
local function town_sid(obj)   -- API: здание (getTown) или любой объект мира (getCurrentTownLocation)
  local okb, isb = pcall(function() return obj.getTown ~= nil end)   -- у Character getTown нет (save_replay: ~60 тыс. лишних ошибок за 8 суток)
  local ok, t = false, nil
  if okb and isb then ok, t = pcall(function() return obj:getTown() end) end
  if ok and t then return tsid_of(t) end
  return tsid_of(obj:getCurrentTownLocation())
end

---------------------------------------------------------------------------------------------- вещи
local REV   -- sid → категория (по спискам kmm_stock_items)
local function reverse()
  if REV then return REV end
  REV = {}
  for c, tiers in pairs(ITEMS.goods or {}) do for _, l in ipairs(tiers) do for _, s in ipairs(l) do REV[s] = c end end end
  for _, l in ipairs(ITEMS.weapons or {}) do for _, s in ipairs(l) do REV[s] = "weapons" end end
  for _, row in pairs(ITEMS.weapons_culture or {}) do for _, l in ipairs(row) do for _, s in ipairs(l) do REV[s] = "weapons" end end end
  for _, row in pairs(ITEMS.armour or {}) do for _, l in ipairs(row) do for _, s in ipairs(l) do REV[s] = "armor" end end end
  return REV
end

local function tier_of(S, fid)   -- 1..4 (T0..T3) по сдвигу тира дирижёра (богатство, голод по металлу)
  local C = conductor()
  local sh = 0
  if C and C.tier_shift and fid then local ok, v = pcall(C.tier_shift, fid); if ok and tonumber(v) then sh = v end end
  return clamp(2 + sh, 1, 4)
end

local function pick_sid(S, fid, cat)
  local tier = tier_of(S, fid)
  local list, ty
  if cat == "armor" then
    local CF = ccfg()
    local fname = CF and CF.factions and CF.factions[fid] and CF.factions[fid].name
    local row = fname and ITEMS.armour[fname]
    list = row and (row[tier] ~= nil and #row[tier] > 0 and row[tier] or row[math.max(1, tier - 1)])
    ty = ITEMS.type.ARMOUR
  elseif cat == "weapons" then
    local CF = ccfg()
    local fname = CF and CF.factions and CF.factions[fid] and CF.factions[fid].name
    local row = fname and ITEMS.weapons_culture[fname]
    list = (row and row[tier] and #row[tier] > 0) and row[tier] or ITEMS.weapons[tier]
    ty = ITEMS.type.WEAPON
  else
    local g = ITEMS.goods[cat]
    list = g and g[clamp(tier - 1, 1, #g)]
    ty = ITEMS.type.ITEM
  end
  if not list or #list == 0 then return nil end
  return list[math.random(#list)], ty
end

local function create_into(inv, sid, ty)
  local gw = getGameWorld()
  local gd = gw.gamedata:getData(sid, ty)
  if not gd then return false end
  if not inv:hasRoomForItem(gd) then return false, "full" end
  local item = gw.theFactory:createItem(gd, nil, nil, nil, -1, nil)
  if not item then return false end
  return inv:addItem(item, 1, false, true) and true or false   -- destroyOnFail: никаких вещей на земле
end

-- наполнение/опустошение одного инвентаря по складу города. kind: shop | storage | trader. Возвращает число операций.
local function work_inventory(S, inv, tsid, kind, budget)
  local st = S.stock
  local s = st.towns[tsid]
  if not s or budget <= 0 then return 0 end
  local rev = reverse()
  local have, items = {}, {}
  for _, it in ipairs(inv:getAllItems()) do
    if not it.isEquipped then
      local gd = it:getGameData()
      local c = gd and rev[gd.stringID]
      if c then have[c] = (have[c] or 0) + (it.quantity or 1); items[c] = items[c] or {}; table.insert(items[c], it) end
    end
  end
  local cats = {}
  if kind == "storage" then for _, c in ipairs(cfg.storage_cats) do cats[#cats + 1] = c end
  else for c in pairs(have) do cats[#cats + 1] = c end end   -- лавка торгует тем, чем торговала: специализация сохраняется
  table.sort(cats)
  local ops = 0
  local slots = cfg.slots[kind] or 6
  for _, c in ipairs(cats) do
    if ops >= budget then break end
    local r = M.level(st, tsid, c) or 0
    local target = math.floor(slots * clamp(r, 0, 2) + 0.5)
    local h = have[c] or 0
    if h < target and r > cfg.deficit and (c ~= "weapons" or cfg.weapons_add) then
      local units = cfg.units_per_item[c] or 1
      for _ = 1, math.min(target - h, budget - ops) do
        if (s.q[c] or 0) < units then break end
        local sid, ty = pick_sid(S, s.owner, c)
        if not sid then break end
        local ok, why = create_into(inv, sid, ty)
        ops = ops + 1
        if not ok then break end
        M.take(st, tsid, c, units)
        RT.rebase_town[tsid] = true
        RT.stats.added = RT.stats.added + 1
      end
    elseif h > target and r < cfg.deficit * 1.5 and cfg.remove_when_short and items[c] then
      for _, it in ipairs(items[c]) do   -- нехватка в городе: полки пустеют (только вещи из наших списков, не надетые)
        if ops >= budget or h <= target then break end
        local n = math.min(it.quantity or 1, h - target)
        inv:removeItemAutoDestroy(it, n)
        RT.rebase_town[tsid] = true
        h = h - n; ops = ops + 1
        RT.stats.removed = RT.stats.removed + n
      end
    end
  end
  return ops
end

-- TOWNLIFE: отложенная смена специализации лавки (решение принято моделью, пока игрока не было рядом). Реальная лавка города при первом
-- заходе игрока в радиус: наши вещи старой категории возвращаются на склад города, новая категория добавляется по уровню склада.
-- Ванильный ассортимент лавки и её владелец не меняются (Lua это не умеет); оружие кладётся только при weapons_add.
local function apply_rot(S, inv, tsid, budget)
  if not cfg.rot_apply then return 0 end
  local st = S.stock
  local p = M.rot_pending(st, tsid)
  if not p then return 0 end
  local day = game_day() or 0
  if day - p.day > (M.DEFAULTS.rot_pending_days or 6) then M.rot_done(st, tsid); return 0 end
  budget = math.min(budget, cfg.rot_apply_ops or 8)
  local rev, ops, a0, r0 = reverse(), 0, RT.stats.added, RT.stats.removed
  for _, it in ipairs(inv:getAllItems()) do
    if ops >= budget then break end
    if not it.isEquipped then
      local gd = it:getGameData()
      if gd and rev[gd.stringID] == p.from then
        local n = it.quantity or 1
        inv:removeItemAutoDestroy(it, n)
        M.add(st, tsid, p.from, n * (cfg.units_per_item[p.from] or 1))
        ops = ops + 1; RT.stats.removed = RT.stats.removed + n
      end
    end
  end
  local s = st.towns[tsid]
  if s and (p.to ~= "weapons" or cfg.weapons_add) then
    local r = M.level(st, tsid, p.to) or 0
    local target = math.floor((cfg.slots.shop or 10) * clamp(r, 0, 2) + 0.5)
    local units = cfg.units_per_item[p.to] or 1
    for _ = 1, target do
      if ops >= budget or (s.q[p.to] or 0) < units then break end
      local sid, ty = pick_sid(S, s.owner, p.to)
      if not sid then break end
      ops = ops + 1
      if not create_into(inv, sid, ty) then break end
      M.take(st, tsid, p.to, units)
      RT.stats.added = RT.stats.added + 1
    end
  end
  RT.rebase_town[tsid] = true
  M.rot_done(st, tsid)
  tlog(string.format("shop restocked after rotation in %s: %s -> %s (+%d -%d)", tname(tsid), p.from, p.to, RT.stats.added - a0, RT.stats.removed - r0))
  return ops
end

---------------------------------------------------------------------------------------------- проходы рядом с игроком
local BUF
local function nearby_buildings(pc)
  if not BUF then BUF = lektor.new("RootObject*") end   -- один буфер на сессию (ContainersReference: не аллоцировать в тике)
  BUF:clear()
  getGameWorld():getObjectsWithinSphere(BUF, pc:getPosition(), cfg.scan_radius, 0, cfg.max_objects, nil)   -- 0 = itemType.BUILDING
  local out = {}
  for _, o in ipairs(BUF) do local b = as_building(o); if b then out[#out + 1] = b end end
  return out
end

local function scan(S, pcs, day)
  if not (cfg.materialize and ITEMS) then return end
  local pc = pcs[1]
  local pf = (ccfg() or {}).player_faction
  local budget, nb = cfg.max_ops_per_pass, 0
  for _, b in ipairs(nearby_buildings(pc)) do
    if nb >= cfg.max_buildings_per_pass or budget <= 0 then break end
    local k = key_of(b)
    if RT.nvisited > 3000 then RT.visited, RT.nvisited = {}, 0 end
    if day - (RT.visited[k] or -1e9) >= cfg.revisit_days then
      if not RT.visited[k] then RT.nvisited = RT.nvisited + 1 end
      RT.visited[k] = day
      local fid = b:hasFaction() and fid_of(b) or nil
      if fid ~= pf then
        local tsid = town_of_building(b)
        local inv = tsid and S.stock.towns[tsid] and b:getInventory()
        if inv then
          local kind = b:isAShop() and "shop" or (cfg.storage and inv:isAContainer() and "storage") or nil
          if kind then
            local a0, r0 = RT.stats.added, RT.stats.removed
            if kind == "shop" and not DISABLED.rot_apply then   -- TOWNLIFE: своя защита - ошибка отключает только ротацию, не склад
              local okr, o = pcall(apply_rot, S, inv, tsid, budget)
              if okr then budget = budget - (o or 0) else DISABLED.rot_apply = true; dlog("rot_apply disabled until restart: " .. tostring(o)) end
            end
            budget = budget - work_inventory(S, inv, tsid, kind, budget)
            if RT.stats.added > a0 or RT.stats.removed > r0 then
              tlog(string.format("restock %s in %s: +%d -%d (stock food=%.2f metal=%.2f)", kind, tname(tsid), RT.stats.added - a0, RT.stats.removed - r0,
                M.level(S.stock, tsid, "food") or -1, M.level(S.stock, tsid, "metal") or -1))
            end
            nb = nb + 1
            RT.stats.buildings = RT.stats.buildings + 1
          end
        end
      end
    end
  end
end
local g_scan = guarded("materialize", scan)

-- общий снимок загруженных NPC (PERF2): KMM_Gov.snapshot(ttl); нет Gov / ошибка → nil, и nearby_npcs идёт прежним обходом
local function gov_snap()
  local g = rawget(_G, "KMM_Gov")
  if not (g and g.snapshot) or cfg.use_snapshot == false then return nil end
  local ok, snap = pcall(g.snapshot, cfg.snap_ttl or 4)
  if ok and type(snap) == "table" and snap.list then return snap end
  return nil
end
-- возвращает список персонажей и (если был снимок) таблицу ch -> запись снимка (кэш trader/town/fid без повторных вызовов API)
local function nearby_npcs(pc, r)
  local px, pz
  local p = pc:getPosition(); px, pz = p.x, p.z
  local out = {}
  local snap = gov_snap()
  if snap then
    local R, r2 = {}, r * r
    for _, rec in ipairs(snap.list) do
      if not rec.dead and (rec.x - px) ^ 2 + (rec.z - pz) ^ 2 <= r2 and not rec.unique then out[#out + 1] = rec.ch; R[rec.ch] = rec end
    end
    return out, R
  end
  for ch in pairs(getGameWorld():getCharacterUpdateList()) do
    if not ch:isPlayerCharacter() and not ch:isDead() and not ch:isUnique() then
      local q = ch:getPosition()
      if (q.x - px) ^ 2 + (q.z - pz) ^ 2 <= r * r then out[#out + 1] = ch end
    end
  end
  return out
end
-- снимок мог устареть до ttl: перед действием над персонажем — живая проверка isDead
local function npc_alive(ch, R)
  if not (R and R[ch]) then return true end
  local ok, d = pcall(ch.isDead, ch)
  return ok and not d
end
-- S5: торговый ли отряд — свойство платуна: кэш по ключу платуна на сессию (вместо getIsTrader у каждого NPC в каждом проходе);
-- значение кладётся и в запись снимка (rawset) — Traces в том же кадре его не перезапрашивает
local PKT, npkt = {}, 0
local function rec_trader(rec)
  local v = rawget(rec, "trader")
  if v ~= nil then return v end
  local k = rec.pkey
  if k and k ~= "" and PKT[k] ~= nil then v = PKT[k]; rawset(rec, "trader", v); return v end
  v = rec.trader
  if k and k ~= "" then
    if npkt >= 2000 then PKT, npkt = {}, 0 end
    if PKT[k] == nil then npkt = npkt + 1 end
    PKT[k] = v
  end
  return v
end
local function npc_trader(ch, R)
  local rec = R and R[ch]
  if rec then return rec_trader(rec) and true or false end
  local pl = ch:getPlatoon()
  return (pl and pl:getIsTrader()) and true or false
end
local function npc_town_sid(ch, R)
  local rec = R and R[ch]
  if rec then return tsid_of(rec.town or nil) end
  return town_of_char(ch)
end
local function npc_fid(ch, R)
  local rec = R and R[ch]
  if rec then return rec.fid end
  return fid_of(ch)
end

-- NATIVE: крэш-сторож нативного вызова (pcall не ловит краш движка): lock до первого вызова; lock при старте = прошлая сессия упала -> .off навсегда
local PROBE = {}
local PDIR = "C:/KenshiModMap/state/"
local function probe_ok(x)
  if PROBE[x] == nil then
    local st = true
    pcall(function()
      local f = io.open(PDIR .. "probe_" .. x .. ".off", "r")
      if f then f:close(); st = false; return end
      f = io.open(PDIR .. "probe_" .. x .. ".lock", "r")
      if f then
        f:close(); st = false
        local o = io.open(PDIR .. "probe_" .. x .. ".off", "w"); if o then o:write("disabled: previous session crashed in ", x); o:close() end
        os.remove(PDIR .. "probe_" .. x .. ".lock")
      end
    end)
    PROBE[x] = st
  end
  return PROBE[x]
end
local function probe_call(x, fn)
  if not probe_ok(x) then return false end
  local lock = PDIR .. "probe_" .. x .. ".lock"
  local first = not PROBE[x .. "#done"]
  if first then pcall(function() local f = io.open(lock, "w"); if f then f:write(tostring(os.time())); f:close() end end) end
  local ok = pcall(fn)
  if first then pcall(os.remove, lock); PROBE[x .. "#done"] = true end
  return ok
end
-- ваниль сама освежает лавку торговца раз в vendors refresh time (SQUAD_TEMPLATE); мы просим её сделать это ДО нашей раздачи (метод сам проверяет срок),
-- чтобы базу заполнила ваниль, а склад только довёл «что и сколько» и последующий ванильный цикл не затирал свежую раздачу.
local function native_refresh(ch)
  if not cfg.native_refresh or DISABLED.native_refresh then return false end
  local ok, done = pcall(function()
    local ap = ch:getPlatoon()
    if not (ap and ap.refreshInventory) then return false end
    return probe_call("refreshInventory", function() ap:refreshInventory(false) end)
  end)
  if not ok then DISABLED.native_refresh = true; dlog("native_refresh disabled until restart: " .. tostring(done)); return false end
  if done then RT.stats.native = (RT.stats.native or 0) + 1 end
  return done
end

local function traders(S, pcs, day)
  if not (cfg.traders and cfg.materialize and ITEMS) then return end
  local budget, n = cfg.max_ops_per_pass, 0
  local list, R = nearby_npcs(pcs[1], cfg.scan_radius)
  for _, ch in ipairs(list) do
    if n >= cfg.max_traders_per_pass or budget <= 0 then break end
    if npc_trader(ch, R) and npc_alive(ch, R) then
      -- тест 2026-11-13: getIsTrader истинно у всех членов торгового отряда (охрана каравана) -> ~30 пополнений за 1.5 мин в Mongrel.
      -- Ключ - отряд: пополняется один персонаж отряда в revisit_days (первый встреченный), охрана товар не таскает.
      local rec = R and R[ch]
      local okp, pid = true, rec and rec.pkey   -- S5: ключ платуна уже в записи снимка
      if not (pid and pid ~= "") then
        okp, pid = pcall(function() local ap = ch:getPlatoon(); local me = ap and (ap.me or ap); return me and me:getPlatoonStringID() end)   -- ActivePlatoon -> .me (Platoon), как в Gov (save_replay 2026-11-13)
      end
      local k = (okp and type(pid) == "string" and pid ~= "") and ("pl:" .. pid) or key_of(ch)
      if day - (RT.visited[k] or -1e9) >= cfg.revisit_days then
        RT.visited[k] = day
        local tsid = npc_town_sid(ch, R)
        if tsid and S.stock.towns[tsid] then
          local a0, r0 = RT.stats.added, RT.stats.removed
          native_refresh(ch)
          budget = budget - work_inventory(S, ch:getInventory(), tsid, "trader", budget)
          if RT.stats.added > a0 or RT.stats.removed > r0 then
            tlog(string.format("restock trader in %s: +%d -%d", tname(tsid), RT.stats.added - a0, RT.stats.removed - r0))
          end
          n = n + 1
          RT.stats.traders = RT.stats.traders + 1
        end
      end
    end
  end
end
local g_traders = guarded("traders", traders)

-- покупки жителей (идея Fun merchant life): редкая вероятностная покупка еды/выпивки/роскоши со склада города;
-- шанс по богатству фракции и уровню склада; вещь в инвентарь — только если там мало вещей и есть место
local function npc_buy(S, pcs, day)
  if not (cfg.npc_buys and ITEMS) then return end
  local list, R = nearby_npcs(pcs[1], cfg.npc_buy_radius)
  if #list == 0 then return end
  local ch = list[math.random(#list)]
  if npc_trader(ch, R) or not npc_alive(ch, R) then return end
  local tsid = npc_town_sid(ch, R)
  local s = tsid and S.stock.towns[tsid]
  if not s or not s.owner or npc_fid(ch, R) ~= s.owner then return end   -- покупают свои жители города
  local F = S.F and S.F[s.owner]
  local w = F and clamp((F.wealth or 0) / math.max(1, F.wealth0 or 1), 0.2, 2) or 0.5
  if math.random() > cfg.npc_buy_chance * w then return end
  local cats = { "food", "food", "drugs", "lux", "med" }
  local c = cats[math.random(#cats)]
  local units = cfg.units_per_item[c] or 1
  if (M.level(S.stock, tsid, c) or 0) < cfg.deficit * 2 then return end
  local inv = ch:getInventory()
  if inv:getNumItems() >= cfg.npc_inventory_max then M.take(S.stock, tsid, c, units); RT.stats.buys = RT.stats.buys + 1; return end
  local sid, ty = pick_sid(S, s.owner, c)
  if sid and create_into(inv, sid, ty) then
    M.take(S.stock, tsid, c, units); RT.stats.buys = RT.stats.buys + 1
    tlog(string.format("npc bought %s (%s) in %s, shelf %.2f", c, tostring(sid), tname(tsid), M.level(S.stock, tsid, c) or -1))
  end
end
local g_buy = guarded("npc_buys", npc_buy)

---------------------------------------------------------------------------------------------- продажи игрока и реликтовая кузня
local function counts_of(inv)
  local rev, have = reverse(), {}
  for _, it in ipairs(inv:getAllItems()) do
    if not it.isEquipped then
      local gd = it:getGameData()
      local c = gd and rev[gd.stringID]
      if c then have[c] = (have[c] or 0) + (it.quantity or 1) end
    end
  end
  return have
end
local function near_player(pcs, obj, r)
  local q = obj:getPosition()
  for i = 1, math.min(#pcs, 6) do
    local p = pcs[i]:getPosition()
    if (p.x - q.x) ^ 2 + (p.z - q.z) ^ 2 <= r * r then return true end
  end
  return false
end
-- снимок инвентаря торговца/лавки: прирост наших вещей без нашего пополнения и при игроке в радиусе торговли = продажа игрока.
-- Консервативно: наше пополнение и ванильный restock (скачок > sale_max_items или без игрока рядом) сбрасывают снимок, а не считаются.
local function sale_check(S, pcs, obj, key, tsid, fid, pf)
  local st = S.stock
  local s = st.towns[tsid]
  if not s or fid == pf then return end
  local have = counts_of(obj:getInventory())
  local prev = RT.snap[key]
  local now = os.clock()
  RT.snap[key] = have
  RT.snap_t = RT.snap_t or {}
  local pt = RT.snap_t[key]; RT.snap_t[key] = now
  if prev and (not pt or now - pt > cfg.sale_seconds * 3) then prev = nil end   -- старый снимок (игрок уходил) — не сравнивать
  if not prev then RT.nsnap = RT.nsnap + 1; return end
  if RT.rebase_town[tsid] then return end
  if not near_player(pcs, obj, cfg.sale_radius) then return end
  local total, add = 0, {}
  for c, n in pairs(have) do local d = n - (prev[c] or 0); if d > 0 then add[c] = d; total = total + d end end
  if total == 0 or total > cfg.sale_max_items then return end
  for c, d in pairs(add) do
    local lvl = M.level(st, tsid, c) or 1
    M.add(st, tsid, c, d * (cfg.units_per_item[c] or 1))
    RT.stats.sales = RT.stats.sales + 1; RT.stats.sold_items = RT.stats.sold_items + d
    tlog(string.format("player sold %d x %s in %s (shelf was %.2f)", d, c, tname(tsid), lvl))
    local okc, ill = pcall(M.illegal, st, s.owner, c)   -- CONTRA: сбыт незаконного для владельца — поставка контрабандой, но стража может поймать
    if okc and ill then
      local CC = (ccfg() or {}).params
      CC = CC and CC.contra or {}
      local dday = math.floor(game_day() or 0)
      RT.caught = RT.caught or {}
      if (RT.caught[tsid] or -1) < dday and math.random() < (CC.caught or 0.25) then
        RT.caught[tsid] = dday
        local I = (ccfg() or {}).town_info
        emit({ type = "contraband_caught", town_sid = tsid, town_name = I and I[tsid] and I[tsid].name or tsid, cat = c, n = d, a = s.owner })
      end
    end
    if d >= cfg.sale_emit_min or lvl < cfg.deficit * 1.5 then
      local I = (ccfg() or {}).town_info
      emit({ type = "player_sold", town_sid = tsid, town_name = I and I[tsid] and I[tsid].name or tsid, cat = c, n = d, a = s.owner, added = true })
    end
  end
end
local function sales(S, pcs, day)
  if not (cfg.player_sales and ITEMS) then return end
  local pf = (ccfg() or {}).player_faction
  if RT.nsnap > 400 then RT.snap, RT.snap_t, RT.nsnap = {}, {}, 0 end
  local seen = {}
  for i = 1, math.min(#pcs, 3) do
    if not BUF then BUF = lektor.new("RootObject*") end
    BUF:clear()
    getGameWorld():getObjectsWithinSphere(BUF, pcs[i]:getPosition(), cfg.sale_radius, 0, cfg.sale_max_objects, nil)
    local list = {}
    for _, o in ipairs(BUF) do local bb = as_building(o); if bb then list[#list + 1] = bb end end
    for _, b in ipairs(list) do
      local k = "b:" .. key_of(b)
      if not seen[k] and b:isAShop() then
        seen[k] = true
        local fid = b:hasFaction() and fid_of(b) or nil
        local tsid = town_of_building(b)
        if tsid and b:getInventory() then sale_check(S, pcs, b, k, tsid, fid, pf) end
      end
    end
  end
  local list, R = nearby_npcs(pcs[1], cfg.sale_radius + 10)
  for _, ch in ipairs(list) do
    if npc_trader(ch, R) and npc_alive(ch, R) then
      local k = "c:" .. key_of(ch)
      local tsid = npc_town_sid(ch, R)
      if not seen[k] and tsid then seen[k] = true; sale_check(S, pcs, ch, k, tsid, npc_fid(ch, R), pf) end
    end
  end
  RT.rebase_town = {}
end
local g_sales = guarded("player_sales", sales)

local function is_relic(it)
  local gd = it:getGameData()
  if not gd then return false end
  return (cfg.relic_names[gd.name] or cfg.relic_sids[gd.stringID]) and true or false
end
local function relic(S, pcs, day)
  if not cfg.relic_forge then return end
  S.stock.flags = S.stock.flags or {}
  if S.stock.flags.player_relic_forge then return end
  for i = 1, math.min(#pcs, 40) do
    local inv = pcs[i]:getInventory()
    if inv then
      for _, it in ipairs(inv:getAllItems()) do
        if is_relic(it) then
          S.stock.flags.player_relic_forge = day
          RT.stats.relic = RT.stats.relic + 1
          local gd = it:getGameData()
          emit({ type = "player_relic_forge", item = gd.stringID, a = (ccfg() or {}).player_faction })
          return
        end
      end
    end
  end
end
local g_relic = guarded("relic_forge", relic)

---------------------------------------------------------------------------------------------- тик
local function reset_ready() RT.ready, RT.polls, RT.seen_clock, RT.seen_day = false, 0, nil, nil end

-- TRADE: тяжёлые проходы ставятся в очередь и исполняются по одному за вызов (кванты по кадрам), чтобы один вызов тика не складывал
-- model + scan + traders + sales + buy и не выбивал бюджет Gov. Порядок: недосчитанный день склада, затем очередь.
local JOBS = { scan = function(S, pcs, day) g_scan(S, pcs, day) end, traders = function(S, pcs, day) g_traders(S, pcs, day) end,
               sales = function(S, pcs, day) g_sales(S, pcs, day) end, relic = function(S, pcs, day) g_relic(S, pcs, day) end,
               buy = function(S, pcs, day) g_buy(S, pcs, day) end }
local function push_job(nm) for _, x in ipairs(RT.jobs) do if x == nm then return end end; RT.jobs[#RT.jobs + 1] = nm end
-- S5: проходы по NPC (traders/sales/buy) берут общий снимок Gov; в игре он живёт один кадр, и проход в своём кадре = своя перестройка.
-- Поэтому они ждут первого кадра общего такта floor(os.clock() / SNAP_BEAT) (тот же такт у Traces/Self) и идут в нём все вместе:
-- одна перестройка на три модуля вместо трёх-пяти. Проходы без NPC (scan/relic) по-прежнему по одному за кадр.
local SNAP_BEAT = 3
local STAMP, stamp_t = nil, -1e9
local function stamp_mode()   -- true: есть метка кадра getTimeStamp (игра); офлайн-заглушка без неё — прежнее расписание (проверка раз в 10 с)
  if STAMP then return true end
  local now = os.clock()
  if now - stamp_t < 10 and now >= stamp_t then return false end
  stamp_t = now
  local ok, v = pcall(function() return getGameWorld():getTimeStamp() end)
  STAMP = (ok and type(v) == "number") or nil
  return STAMP == true
end
local NPC_JOB = { traders = true, sales = true, buy = true }
local function pump(bf)   -- true, если квант выполнен; bf — первый кадр такта снимка
  if RT.dctx then
    if DISABLED.model or RT.S ~= (conductor() and conductor().state()) then RT.dctx = nil
    else g_dayadv(); return true end
  end
  local pick
  if not stamp_mode() then local nm = table.remove(RT.jobs, 1); pick = nm and { nm }   -- офлайн без метки кадра: по одному, как раньше
  elseif bf then
    pick = {}
    for i = #RT.jobs, 1, -1 do if NPC_JOB[RT.jobs[i]] then table.insert(pick, 1, table.remove(RT.jobs, i)) end end
    if #pick == 0 then pick = nil end
  end
  if not pick and stamp_mode() then
    for i, nm in ipairs(RT.jobs) do if not NPC_JOB[nm] then pick = { table.remove(RT.jobs, i) }; break end end
  end
  if not pick then return false end
  local S = RT.S
  local pcs = player_chars()
  local day = game_day()
  if not (S and S.stock and S.stock.towns and pcs and #pcs > 0 and day) then return false end
  for _, nm in ipairs(pick) do JOBS[nm](S, pcs, day) end
  return true
end

local function tick()
  local t = os.clock()
  local beat = math.floor(t / SNAP_BEAT)
  local bf = beat ~= RT.beat
  RT.beat = beat
  if RT.ready and (RT.dctx or RT.jobs[1]) and pump(bf) then return end
  if t - RT.t_poll < ((cfg and cfg.poll_seconds) or 1) then return end
  RT.t_poll = t
  if not cfg then load_cfg(); install_away() end
  if not cfg.enabled then return end
  local C = conductor()
  if not C then return end
  local pcs = player_chars()
  if not pcs or #pcs == 0 then if RT.ready or RT.seen_clock then reset_ready() end; RT.jobs, RT.dctx = {}, nil; return end
  local day = game_day()
  if not day then return end
  if not RT.ready then   -- ленивый старт: персонажи есть N опросов, M секунд, и игровое время пошло
    RT.polls = RT.polls + 1
    if not RT.seen_clock then RT.seen_clock, RT.seen_day = t, day; return end
    if RT.polls < cfg.start_delay_polls or t - RT.seen_clock < cfg.start_delay_seconds
       or (day - RT.seen_day) * 24 < cfg.start_delay_hours then return end
    RT.ready = true
  end
  local S = C.state()
  if type(S) ~= "table" or type(S.F) ~= "table" then return end
  g_model(S, day)
  if DISABLED.model or not (S.stock and S.stock.towns) then return end
  if t - RT.t_scan >= cfg.scan_seconds then RT.t_scan = t; push_job("scan"); push_job("traders") end
  if t - RT.t_sale >= cfg.sale_seconds then RT.t_sale = t; push_job("sales") end
  if t - RT.t_relic >= cfg.relic_seconds then RT.t_relic = t; push_job("relic") end
  if t - RT.t_buy >= cfg.npc_buy_seconds then RT.t_buy = t; push_job("buy") end
end
local g_tick = guarded("tick", tick)

---------------------------------------------------------------------------------------------- публичное API (_G.KMM_Stock, для TOWN)
local function stock_ready()
  local C = conductor()
  local S = C and C.state()
  if type(S) == "table" and type(S.stock) == "table" and S.stock.towns and M then return S.stock, S end
end
local function safe(nm, fn) local g = guarded("api_" .. nm, fn); return function(...) return g(...) end end

-- R1: цена категорий по складу города: { x = {cat = множитель}, siege = bool, sig = "корзины уровней" } (sig меняется на дефиците/избытке/осаде)
local function price_x(st, tsid)
  local s = st.towns[tsid]
  if not s then return nil end
  local G = cfg.tgm or DEFAULTS.tgm
  local sieged = (s.siege or -1) >= (st.last_day or 0)
  local x, sig = {}, {}
  for _, c in ipairs(KMM_Stock.CATS) do
    local lv = M.level(st, tsid, c)
    if lv then
      local v = (lv < 1) and (1 + (G.def or 0.6) * (1 - math.max(lv, 0))) or (1 - (G.glut or 0.15) * (math.min(lv, 3) - 1))
      if sieged then v = v * ((G.siege or {})[c] or 1) end
      local okp, pm = pcall(M.price, st, tsid, c)   -- контрабанда у владельца города дороже
      if okp and tonumber(pm) then v = v * pm end
      x[c] = clamp(v, G.min or 0.6, G.max or 1.8)
      sig[#sig + 1] = c .. ((lv < (cfg.deficit or 0.2)) and "d" or (lv > (G.glut_lv or 2.5)) and "g" or "n")
    end
  end
  return { x = x, siege = sieged, sig = table.concat(sig, ",") .. (sieged and "|S" or "") }
end
-- R1: вещи категории для цен города: { {sid, itemType}, ... } (культура владельца первой, без повторов, <= tgm.cat_max); кэш по владельцу; только чтение
local CATI = {}
local function cat_items(fid, cat)
  local key = cat .. "|" .. tostring(fid)
  if CATI[key] then return CATI[key] end
  local G = cfg.tgm or DEFAULTS.tgm
  local cap, out, seen = G.cat_max or 40, {}, {}
  local function add(tiers, ty) for _, l in ipairs(tiers or {}) do for _, sid in ipairs(l) do
    if #out < cap and not seen[sid] then seen[sid] = true; out[#out + 1] = { sid, ty } end
  end end end
  local CF = ccfg()
  local fname = CF and CF.factions and CF.factions[fid] and CF.factions[fid].name
  if cat == "weapons" then add(fname and ITEMS.weapons_culture[fname], ITEMS.type.WEAPON); add(ITEMS.weapons, ITEMS.type.WEAPON)
  elseif cat == "armor" then add(fname and ITEMS.armour[fname], ITEMS.type.ARMOUR)
  else add(ITEMS.goods[cat], ITEMS.type.ITEM) end
  CATI[key] = out
  return out
end

KMM_Stock = KMM_Stock or {}
KMM_Stock.version = VERSION
KMM_Stock.CATS = { "food", "metal", "weapons", "armor", "med", "drugs", "lux", "scrap" }
-- уровень категории города: доля нормы (0..3; < 0.2 дефицит, > 2.5 переполнение) или nil
KMM_Stock.level = safe("level", function(tsid, cat) local st = stock_ready(); return st and M.level(st, tsid, cat) end)
-- запас города: { q = {cat = единиц}, T = норма, owner = fid, city = bool, siege = bool } или nil (копия)
KMM_Stock.stock = safe("stock", function(tsid)
  local st, S = stock_ready(); local s = st and st.towns[tsid]
  if not s then return nil end
  local q = {}; for k, v in pairs(s.q) do q[k] = v end
  return { q = q, T = M.T(st, s), owner = s.owner, city = s.city, siege = (s.siege or -1) >= (st.last_day or 0) }
end)
-- списать / добавить единицы (TOWN: грузчик унёс в лавку, караван увёз, мастер положил продукт). Возвращает фактическое количество.
KMM_Stock.take = safe("take", function(tsid, cat, units) local st = stock_ready(); return st and M.take(st, tsid, cat, units) or 0 end)
KMM_Stock.add = safe("add", function(tsid, cat, units) local st = stock_ready(); return st and M.add(st, tsid, cat, units) or 0 end)
-- изделие видимой цепочки доставлено (TOWN): +на склад и в дневной зачёт мастерских модели (без двойного счёта)
KMM_Stock.made = safe("made", function(tsid, cat, units) local st = stock_ready(); return st and M.made(st, tsid, cat, units) or 0 end)
-- какую вещь категории (броня; оружие только при weapons_add) выковать городу по ярусу владельца: sid, itemType или nil (без побочных эффектов)
KMM_Stock.pick_item = safe("pick_item", function(tsid, cat)
  local st, S = stock_ready(); local s = st and st.towns[tsid]
  if not (s and ITEMS) or (cat ~= "armor" and cat ~= "weapons") or (cat == "weapons" and not cfg.weapons_add) then return nil end
  return pick_sid(S, s.owner, cat)
end)
-- что сейчас производит мастерская города: { making = "weapons"|"armor"|"idle"|"no_metal", rate = единиц/день }
KMM_Stock.workshop = safe("workshop", function(tsid)
  local st = stock_ready(); local s = st and st.towns[tsid]
  if not s then return nil end
  return { making = s.ws or "idle", rate = s.ws_rate or 0 }
end)
-- одна реальная вещь категории в инвентарь (ящик мастерской, лавка, ноша грузчика) со списанием со склада;
-- true при успехе; false если нет места/запаса. Оружие — только при weapons_add.
KMM_Stock.put_item = safe("put_item", function(inv, tsid, cat)
  local st, S = stock_ready(); local s = st and st.towns[tsid]
  if not (s and ITEMS and inv) or (cat == "weapons" and not cfg.weapons_add) then return false end
  local units = cfg.units_per_item[cat] or 1
  if (s.q[cat] or 0) < units then return false end
  local sid, ty = pick_sid(S, s.owner, cat)
  if not sid or not create_into(inv, sid, ty) then return false end
  M.take(st, tsid, cat, units); RT.stats.added = RT.stats.added + 1
  RT.rebase_town[tsid] = true   -- наша вещь в лавке города: следующий снимок продаж берётся заново
  return true
end)
-- ROBBERY: категория вещи по её sid (списки kmm_stock_items) или по itemType (2 оружие, 3 броня); nil — неизвестное (рантайм решит: scrap/lux по цене)
KMM_Stock.item_cat = safe("item_cat", function(sid, ty)
  if not ITEMS then local okI, it = pcall(require, "kmm_stock_items"); if okI and type(it) == "table" then ITEMS = it end end
  local c = ITEMS and sid and reverse()[sid]
  if c then return c end
  if ty == 2 then return "weapons" elseif ty == 3 then return "armor" end
  return nil
end)
KMM_Stock.town_of = safe("town_of", function(obj) return obj and town_sid(obj) end)
-- R1 (родные цены города, KMM_Traces): цена категорий по складу и вещи категории для Town.tradeGoodsMults
KMM_Stock.price_x = safe("price_x", function(tsid) local st = stock_ready(); return st and price_x(st, tsid) end)
KMM_Stock.cat_items = safe("cat_items", function(tsid, cat)
  local st = stock_ready(); local s = st and st.towns[tsid]
  if not (s and ITEMS) then return nil end
  return cat_items(s.owner, cat)
end)
KMM_Stock.ready = function() return RT.ready and stock_ready() ~= nil end
KMM_Stock.disabled = function() return DISABLED end
KMM_Stock.stats = function() return RT.stats end
KMM_Stock.status = function()
  local t = {}; for k in pairs(DISABLED) do t[#t + 1] = k end
  local s = RT.stats
  return string.format("%s ready=%s days=%d added=%d removed=%d buildings=%d traders=%d buys=%d events=%d disabled=%s", VERSION,
    tostring(RT.ready), s.days, s.added, s.removed, s.buildings, s.traders, s.buys, s.events, table.concat(t, ","))
end
KMM_Stock._rt = RT

if KMM_Stock._handler and Events and Events.off then pcall(Events.off, KMM_Stock._handler) end   -- перезагрузка не дублирует
if Events and Events.on then KMM_Stock._handler = Events.on("GameWorld::charsUpdate", guarded("handler", function(...) if _G.KMM_Gov then return KMM_Gov.run("stock", g_tick, ...) else return g_tick(...) end end)) end
_G.KMM_Stock = KMM_Stock
