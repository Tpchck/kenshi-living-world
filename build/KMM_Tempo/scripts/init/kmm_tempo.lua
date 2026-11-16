-- KMM_Tempo v1.1 (2026-11-13) — ходьба/бег имеют смысл: усталость от бега (игрок), шаг/трусца отрядов NPC, живой голод NPC через ваниль (блок HUNGER).
-- Игрок: накопитель усталости 0..1 на персонажа. Бег копит (быстрее с весом и ранами), трусца почти нейтральна, шаг/стоянка снимают.
--   Эффект мягкий: moveSpeed (CharStats) умножается на 1 - slow_max*плавная_ступень(усталость выше порога), slow_max <= 0.15 (жёсткий потолок в коде).
--   Расход голода (MedicalSystem.hunger) выключен по умолчанию: направление шкалы в справке не указано (hunger_extra = 0).
--   Время — ИГРОВОЕ (GameWorld:getTimeStamp_inGameHours():getTotalDays()), x1-x5 и пауза согласованы; в паузе dt = 0.
-- NPC: Platoon.speedOverride (RW, MoveSpeed): город -> WALK, дорога -> JOG; бой/раненые/игроковые отряды не трогаем, исходное значение возвращается.
--   Данные берёт из общего снимка KMM_Gov.snapshot (не сканирует сам; нет снимка — NPC-часть пропускает такт).
-- КАССА (R3): касса торговца (ванильные деньги отряда) идёт к цели «богатство города» (население, беспорядки, еда, осада, товар, процветание фракции) — блок till.
-- ПОЛКИ (U4): торговцы-жители города пополняют лавку реже в бедном/осаждённом/голодном городе и чаще в богатом — сдвиг ванильной метки traderInventoryRefreshTime (блок restock).
-- Безотказность: ленивый старт, pcall везде, каждая функция отключается сама (причина -> logs/tempo.log), наружу ошибок нет.
local TAG = "[KMM_Tempo] "
local CFG = {
  enabled = true,
  player_fatigue = true, player_slow = true, player_hunger = true, npc_pace = true,
  log_path = "C:/KenshiModMap/logs/tempo.log", debug_log = "C:/KenshiModMap/logs/debug.log",
  start_delay_seconds = 8, start_delay_polls = 8,
  poll_seconds = 1.0, npc_seconds = 2.0, npc_per_tick = 16,
  max_dt_hours = 2.0,
  -- усталость, единиц/игровой час
  run_rate = 0.30, jog_rate = 0.02, walk_rate = -0.20, rest_rate = -0.30,
  weight_ref = 80, weight_gain = 0.5, wound_gain = 1.0,    -- множитель накопления: 1 + weight_gain*min(1,вес/ref) + wound_gain*(1-injMult)
  move_threshold = 0.3,                                    -- getMovementSpeed() ниже -> стоит
  -- эффект
  slow_threshold = 0.5, slow_max = 0.12,                    -- <= 0.15 жёстко
  hunger_extra = 0, hunger_sign = -1,                      -- единиц hunger/игровой час при полной усталости (0 = выключено)
  -- NPC
  town_speed = 0, road_speed = 1, road_pace = false,   -- road_pace=true вернёт трусцу на дороге                          -- MoveSpeed.WALK / JOG
  log_day_summary = true,
  -- HUNGER (NPC): живой голод через ваниль. Поле MedicalSystem.hunger/fed читается и пишется; шкала: hunger_dir=-1 значит «hunger падает, когда голоден», 0..hunger_full.
  -- Направление шкалы справка не указывает: первые hunger_probe_log замеров пишутся в tempo.log (HUNGER probe), при выходе за 0..1.5*full модуль выключается сам.
  npc_hunger = true, npc_feed = true, slave_hunger = true, protect_unique = true, npc_starve = true,
  hunger_dir = -1, cal_hours = 1, soft_floor = 0.5, hunger_full = 300, starve_hours = 72, vanilla_drain_ok = 0.25,   -- starve_hours = 3 x CONSTANTS.starvation time (FCS: 24 ч на 100 очков; «x3 — время до смерти»), т.е. родная скорость 100/24 в ч; сама константа недоступна из Lua. vanilla_drain_ok: ваниль тратит >= этой доли ожидаемого -> своего расхода нет
  hunger_seconds = 3.0, hunger_per_tick = 24, hunger_min_dt = 0.25, hunger_max_dt = 6.0, hunger_probe_log = 5,
  eat_below = 0.35, meal_restore = 0.45, meal_units = 1,   -- ест, если fed < eat_below*full; порция возвращает meal_restore*full, на складе города -meal_units
  wild_floor = 0.12,                                       -- вне города и не раб: падает до «голоден», не ниже (смерти нет)
  slave_floor = 0.18, slave_ration_units = 0.5,             -- хозяин кормит минимально: «голоден, но жив»
  slave_caravan = true, slave_loss_days = 3, slave_loss_min = 3, slave_caravan_cd_days = 5, slave_demand_days = 4,   -- убыль рабов фракции-хозяина >= min за days суток -> событие slave_caravan + метка спроса (T.slave_demand), кулдаун cd суток
  starve_grace_h = 6, kill_method = "blood",                -- «blood»: кровь ниже pointOfNoReturn (ваниль-смерть от кровопотери); «declare»: Character:declareDead()
  death_cap_town = 2, death_cap_day = 6,                    -- смертей от голода на город / всего в игровые сутки
  prot_min = 0.25, prot_meal = 0.8, prot_trigger = 0.5,     -- уникальные/торговцы: не ниже prot_min; раз в сутки паёк до prot_meal
  supply_min = 2, supply_max = 4,                           -- порций еды в инвентаре уникального (раз в сутки)
  -- КАССА (R3): касса торговца = богатство города (ванильные деньги отряда, Ownerships:getMoney/setMoney). Заменяет прежнюю подкачку money_min.
  till = true, till_seconds = 4.0, till_per_tick = 12,
  till_base = { city = 8000, town = 4000 }, till_base_cap = 2.5,   -- база кассы: по виду города, но не ниже/выше этого от кассы торговца при первой встрече (? ваниль-касса обычно 2-10 тыс.)
  till_rate = 0.35, till_down_rate = 0.2,                   -- доля разрыва до цели за игровые сутки: вверх (подвоз денег) / вниз (налоги, расходы города)
  till_visit_days = 1, till_max_gap = 5,                    -- первая встреча в сессии = визит игрока: шаг за till_visit_days суток; догон за пропуск не больше till_max_gap суток
  till_max = 40000, till_min_delta = 25,                    -- цель не выше till_max; мелкие изменения не пишем
  till_w_min = 0.08, till_w_max = 1.6, till_siege = 0.35,   -- пределы множителя богатства; осада режет кассу
  till_poor = 0.35, till_probe_log = 3,                     -- касса ниже till_poor*базы -> маркер TILL poor; первые N значений процветания фракции -> TILL probe
  till_goods = { "lux", "metal", "weapons", "armor", "med", "drugs" },   -- товарные полки KMM_Stock: избыток = торговый город богаче
  -- ПОЛКИ (U4): темп пополнения лавки торговца-жителя = богатство города w (как у кассы); двигаем только ванильную метку Platoon.traderInventoryRefreshTime.
  restock = true, restock_seconds = 5.0, restock_per_tick = 12,
  restock_period_h = 16,                                    -- vendors refresh time торговцев (economy.json vendor_turnover: 24 -> 16 ч); из Lua шаблон не читаем
  restock_m_min = 0.25, restock_m_max = 1.5, restock_dead = 0.1,   -- темп: 0.25 = вчетверо реже (~64 ч), 1.5 = в полтора раза чаще (~11 ч); |m-1| < dead -> ваниль
  restock_smooth = 0.5, restock_min_shift_h = 1.0,          -- доля шага темпа города к цели за сутки; сдвиг мельче часа не пишем
  restock_plaus_h = 72, restock_arm_reads = 3, restock_jump_h = 36,   -- окно правдоподобия метки (ч от «сейчас»); чтений до первой записи; скачок времени -> заново наблюдать
  restock_forget_days = 10, restock_probe_log = 4,          -- забыть платун без встречи N суток; первые N платунов -> RESTOCK probe (метка, дом, житель)
  exertion_gain = 0.6,                                      -- мост усталости: вклад ванильного calculateHungerMult (бег+вес) вместо своего веса
}
local SLOW_CAP = 0.15
local DISABLED = {}
local RT = { ready = false, polls = 0, t_start = nil, t_poll = nil, t_npc = nil, last_h = nil, day = nil,
  chars = {}, npc = {}, cursor = 0,
  stats = { polls = 0, npc_ticks = 0, npc_set = 0, npc_restore = 0, max_fat = 0, min_mult = 1, run_h = 0, rest_h = 0 } }
KMM_Tempo = rawget(_G, "KMM_Tempo") or {}
local T = KMM_Tempo
T.cfg, T._rt, T._disabled = CFG, RT, DISABLED

local function klog(m) m = TAG .. tostring(m); if not (KenshiLua and pcall(function() KenshiLua.log(m) end)) then print(m) end end
local function append(path, line)
  local ok, f = pcall(io.open, path, "a")
  if ok and f then f:write(line, "\n"); f:close(); return true end
  return false
end
local function tlog(msg) append(CFG.log_path, os.date("%Y-%m-%d %H:%M:%S") .. " " .. tostring(msg)) end
-- HEALTH (2026-11-15): отказ механики -> реестр ядра KMM_Gov (ключ KMM_Tempo.<имя>): пауза 1/5/30 мин и повтор.
-- DISABLED — только навсегда: forever (запись не применилась — поле/API не то) или нет Gov (прежнее поведение).
local function GOV() local g = rawget(_G, "KMM_Gov"); if type(g) == "table" and type(g.h_fail) == "function" then return g end end
local function paused(name)
  local g = GOV(); if not g then return false end
  local ok, up = pcall(g.h_up, "KMM_Tempo." .. name)
  return ok and up == false
end
local PAUSED = {}   -- имена на паузе реестра (для T.status().paused)
local function disable(name, why, forever)
  if DISABLED[name] or paused(name) then return end
  local g, p = GOV(), nil
  if g and not forever then local ok, r = pcall(g.h_fail, "KMM_Tempo." .. name, why); if ok then p = r end end
  if type(p) == "number" then
    PAUSED[name] = true
    tlog("PAUSED " .. name .. " " .. p .. " s: " .. tostring(why)); klog("paused " .. name .. " " .. p .. " s: " .. tostring(why))
    pcall(append, CFG.debug_log, os.date("%Y-%m-%d %H:%M:%S") .. " " .. TAG .. name .. " failed, retry in " .. p .. " s: " .. tostring(why))
    return
  end
  if forever and g and type(g.h_off) == "function" then pcall(g.h_off, "KMM_Tempo." .. name, why, "noeffect") end
  DISABLED[name] = tostring(why)
  tlog("DISABLED " .. name .. ": " .. tostring(why)); klog("disabled " .. name .. ": " .. tostring(why))
  pcall(append, CFG.debug_log, os.date("%Y-%m-%d %H:%M:%S") .. " " .. TAG .. "disabled " .. name .. ": " .. tostring(why))
end
local function on(name) return CFG[name] and not DISABLED[name] and not paused(name) end
local function game_hours()
  local ok, d = pcall(function() return getGameWorld():getTimeStamp_inGameHours():getTotalDays() end)
  if ok and type(d) == "number" then return d * 24 end
  return nil
end
local function clamp(v, a, b) if v < a then return a elseif v > b then return b end return v end

---------------------------------------------------------------------------------------------- игрок
function T.slow_mult(f)   -- плавная ступень; всегда в [1-SLOW_CAP, 1]
  local smax = math.min(CFG.slow_max, SLOW_CAP)
  local x = clamp((f - CFG.slow_threshold) / math.max(1e-6, 1 - CFG.slow_threshold), 0, 1)
  return 1 - smax * x * x * (3 - 2 * x)
end

function T.hkey(ch)   -- ключ персонажа между опросами: hand:toString(); tostring(hand) у sol2 — адрес новой userdata на каждый вызов (ревью 2026-11-15)
  local h = ch:getHandle()
  local ok, s = pcall(function() return h:toString() end)
  if ok and type(s) == "string" then return s end
  return tostring(h)   -- офлайн-заглушки без toString
end
local function char_state(ch)
  local ok, key = pcall(T.hkey, ch)
  if not ok or not key then return nil end
  local s = RT.chars[key]
  if not s then s = { f = 0 }; RT.chars[key] = s end
  s.seen = RT.polls
  return s
end

local function player_one(ch, dt)
  local s = char_state(ch); if not s then return end
  local okd, dead = pcall(ch.isDead, ch); if okd and dead then return end
  if on("player_fatigue") then
    local ok, err = pcall(function()
      local spd = ch:getMovementSpeed() or 0
      local ord = ch:getMovementSpeedOrders()
      local rate
      if spd < CFG.move_threshold then rate = CFG.rest_rate
      elseif ord == 2 then
        local mult = 1
        -- мост: ваниль уже связывает нагрузку и бег с голодом (CharStats:calculateHungerMult, ENCUMBRANCE_HUNGER_RATE); берём её, свой вес — запасной путь
        local okh, hm = pcall(function() return ch:getStats():calculateHungerMult() end)
        if okh and type(hm) == "number" then mult = mult + CFG.exertion_gain * clamp(hm - 1, 0, 2)
        else
          local okw, w = pcall(function() return ch:getInventory():getTotalWeight() end)
          if okw and type(w) == "number" then mult = mult + CFG.weight_gain * clamp(w / CFG.weight_ref, 0, 1) end
        end
        local oki, im = pcall(function() return ch:getMedical():getMovementSpeedInjuryMultiplier() end)
        if oki and type(im) == "number" then mult = mult + CFG.wound_gain * clamp(1 - im, 0, 1) end
        rate = CFG.run_rate * mult
      elseif ord == 1 then rate = CFG.jog_rate
      else rate = CFG.walk_rate end
      s.f = clamp(s.f + rate * dt, 0, 1)
      if rate > 0 then RT.stats.run_h = RT.stats.run_h + dt else RT.stats.rest_h = RT.stats.rest_h + dt end
      if s.f > RT.stats.max_fat then RT.stats.max_fat = s.f end
    end)
    if not ok then disable("player_fatigue", err); return end
  end
  if on("player_slow") then
    local ok, err = pcall(function()
      local st = ch:getStats()
      local cur = st.moveSpeed
      if type(cur) ~= "number" then error("CharStats.moveSpeed is " .. type(cur)) end
      if s.written and math.abs(cur - s.written) < 1e-6 then cur = s.base or cur end   -- наше значение: база прежняя, иначе движок пересчитал
      s.base = cur
      local m = on("player_fatigue") and T.slow_mult(s.f) or 1
      if m < 1 or s.written then
        local nv = cur * m
        st.moveSpeed = nv
        local back = st.moveSpeed
        if type(back) ~= "number" or math.abs(back - nv) > 1e-3 * math.max(1, nv) then error("moveSpeed write not applied: " .. tostring(back) .. " vs " .. tostring(nv)) end
        s.written = (m < 1) and nv or nil
      end
      if m < RT.stats.min_mult then RT.stats.min_mult = m end
    end)
    if not ok then
      disable("player_slow", err)
      pcall(function() if s.written and s.base then ch:getStats().moveSpeed = s.base end end)
    end
  end
  if on("player_hunger") and CFG.hunger_extra ~= 0 and s.f > CFG.slow_threshold then
    local ok, err = pcall(function()
      local med = ch:getMedical()
      local h = med.hunger
      if type(h) ~= "number" then error("MedicalSystem.hunger is " .. type(h)) end
      local x = (s.f - CFG.slow_threshold) / (1 - CFG.slow_threshold)
      med.hunger = h + CFG.hunger_sign * CFG.hunger_extra * x * dt
    end)
    if not ok then disable("player_hunger", err) end
  end
end

local function player_tick(h)
  local pcs = getPlayerInterface():getAllPlayerCharacters()
  local dt = 0
  if h and RT.last_h then dt = clamp(h - RT.last_h, 0, CFG.max_dt_hours) end
  RT.last_h = h or RT.last_h
  RT.polls = RT.polls + 1; RT.stats.polls = RT.stats.polls + 1
  local n = 0
  for _, ch in pairs(pcs) do n = n + 1; if n > 32 then break end; player_one(ch, dt) end
  if RT.polls % 60 == 0 then for k, s in pairs(RT.chars) do if RT.polls - (s.seen or 0) > 120 then RT.chars[k] = nil end end end
  return n
end

---------------------------------------------------------------------------------------------- NPC
-- режим отряда: "vanilla" (не трогаем), "town", "road"
local function platoon_mode(members, ap)
  local okp, isp = pcall(function() return ap and ap.isPlayer end)
  if okp and isp then return "vanilla" end
  local town = false
  for i = 1, #members do
    local r = members[i]
    if r.dead or r.down or r.combat then return "vanilla" end
    if not town and r.town then town = true end
  end
  -- дорога: ванильная скорость (интегратор 2026-11-13): трусца на дороге замедлила бы бегущих (KMM_Self), погоню и караван под угрозой
  if town then return "town" end
  return CFG.road_pace and "road" or "vanilla"
end

local function npc_tick()
  local G = rawget(_G, "KMM_Gov")
  local snap = G and G.snapshot and G.snapshot()
  if not snap then return end
  RT.stats.npc_ticks = RT.stats.npc_ticks + 1
  local keys, nk = {}, 0
  for k in pairs(snap.by_pkey) do nk = nk + 1; keys[nk] = k end
  for k in pairs(RT.npc) do if not snap.by_pkey[k] then RT.npc[k] = nil end end   -- платун выгружен: указатель не трогаем
  if nk == 0 then return end
  table.sort(keys)
  local per = math.min(CFG.npc_per_tick, nk)
  for i = 1, per do
    if not on("npc_pace") then return end
    RT.cursor = RT.cursor % nk + 1
    local key = keys[RT.cursor]
    local members = snap.by_pkey[key]
    local pl = members[1] and members[1].pl
    if pl then
      local ok, err = pcall(function()
        local mode = platoon_mode(members, members[1].ap)
        local st = RT.npc[key]
        if mode == "vanilla" then
          if st and st.changed then pl.speedOverride = st.orig; RT.stats.npc_restore = RT.stats.npc_restore + 1 end
          RT.npc[key] = nil
          return
        end
        local target = (mode == "town") and CFG.town_speed or CFG.road_speed
        if not st then
          local cur = pl.speedOverride
          if type(cur) ~= "number" then error("Platoon.speedOverride is " .. type(cur)) end
          st = { orig = cur }; RT.npc[key] = st
        end
        if st.orig == 0 or (st.cur == target) then return end      -- ваниль уже шаг / уже выставлено
        pl.speedOverride = target
        if pl.speedOverride ~= target then error("speedOverride write not applied") end
        st.cur, st.changed = target, true
        RT.stats.npc_set = RT.stats.npc_set + 1
      end)
      if not ok then disable("npc_pace", err); return end
    end
  end
end

---------------------------------------------------------------------------------------------- голод NPC
-- Ваниль-рычаги (BindingsReference): MedicalSystem.hunger/fed (RW), CharStats:calculateHungerMult (нагрузка+бег), Character:amSomeoneWhoNeedsToEatToLive,
-- getNumFoodItems, eatItem(food, inv), isSlave/getMySlaveOwner, isUnique. Магический голод (getMagicHungerSetting) записать нельзя
-- (нет сеттера), поэтому голод эмулируется полем MedicalSystem.hunger: добавляем только НЕДОСТАЮЩИЙ до ванильной скорости расход (если ваниль уже тратит — не удваиваем).
-- Еда: ваниль-путь (eatItem из инвентаря); город: склад KMM_Stock через дирижёра (stock_state — чтение, stock_spend — списание его же API). Склад событий сам не слушает.
local HG = { cal = nil, pobs = {}, visits_total = 0, killed = {}, cursor = 0, st = {}, tick = 0, deaths = {}, deaths_day = 0, day = nil, deficit_day = {}, fed_by = {}, probe = 0,
  stats = { visited = 0, drained = 0, ate = 0, town_meals = 0, slave_rations = 0, supplies = 0, starved = 0, vanilla_ate = 0 } }
T._hg = HG

local function conductor() local C = rawget(_G, "KMM_Conductor"); if type(C) == "table" then return C end end
local function fed_get(med)
  local h = med.hunger
  if type(h) ~= "number" then error("MedicalSystem.hunger is " .. type(h)) end
  return CFG.hunger_dir < 0 and h or (CFG.hunger_full - h)
end
local function fed_set(med, v)
  v = clamp(v, 0, CFG.hunger_full)
  local want = CFG.hunger_dir < 0 and v or (CFG.hunger_full - v)
  med.hunger = want
  local back = med.hunger
  if type(back) ~= "number" or math.abs(back - want) > 1e-3 * math.max(1, CFG.hunger_full) then error("hunger write not applied: " .. tostring(back) .. " vs " .. tostring(want)) end
end
local function town_of(r)
  local t = r.town
  if not t then return nil end
  local ok, sid = pcall(function() local gd = (t.getGameData and t:getGameData()) or t.data; return gd and gd.stringID end)
  if not (ok and sid) then return nil end
  local name = sid
  local C = conductor()
  if C and C.cfg then
    local okc, cf = pcall(C.cfg)
    local i = okc and cf and cf.town_info and cf.town_info[sid]
    if i and i.name then name = i.name end
  end
  return sid, name
end
local function stock_food(sid)   -- (единиц, норма) или nil, если склад города недоступен (тогда о дефиците судить нельзя)
  local C = conductor()
  if not (C and C.stock_state) then return nil end
  local ok, st = pcall(C.stock_state)
  local s = ok and st and st.towns and st.towns[sid]
  if not (s and type(s.q) == "table" and type(s.tn) == "table" and type(s.q.food) == "number" and type(s.tn.food) == "number" and s.tn.food > 0) then return nil end
  return s.q.food, s.tn.food
end
local function stock_take(sid, units)   -- списание общим API дирижёра (stock_spend); возвращает фактически списанное
  local q, tn = stock_food(sid)
  if not q or q < units then return 0 end
  local C = conductor()
  if not (C and C.stock_spend) then return 0 end
  local ok, x = pcall(C.stock_spend, sid, "food", units / tn)
  if ok and type(x) == "number" then return x end
  return 0
end
local function try_eat(ch)   -- ваниль-путь: Character:eatItem из своего инвентаря
  local okn, n = pcall(ch.getNumFoodItems, ch)
  if not (okn and type(n) == "number" and n > 0) then return false end
  local inv = ch:getInventory()
  local k = 0
  for _, it in pairs(inv:getAllItems()) do
    k = k + 1; if k > 80 then break end
    local okf, isf = pcall(it.isFood, it)
    if okf and isf then
      local oke, res = pcall(ch.eatItem, ch, it, inv)
      return oke and res and true or false
    end
  end
  return false
end
local FOODITEMS
local function supply_food(ch, sid, n)   -- пополнить запас уникального (раз в сутки): ваниль-предметы тира 1 из списков KMM_Stock
  if FOODITEMS == nil then
    local ok, it = pcall(require, "kmm_stock_items")
    FOODITEMS = (ok and type(it) == "table" and it.goods and it.goods.food and it.goods.food[1]) and it or false
  end
  if not FOODITEMS then return 0 end
  local list, ty = FOODITEMS.goods.food[1], FOODITEMS.type.ITEM
  local inv, gw, made = ch:getInventory(), getGameWorld(), 0
  if sid and stock_food(sid) then   -- склад знает город: порции из него; пустой склад -> запас не создаём
    local got = 0
    for _ = 1, n do if stock_take(sid, 1) >= 1 then got = got + 1 else break end end
    n = got
  end
  for _ = 1, n do
    local gd = gw.gamedata:getData(list[math.random(#list)], ty)
    if not gd or not inv:hasRoomForItem(gd) then break end
    local item = gw.theFactory:createItem(gd, nil, nil, nil, -1, nil)
    if not item or not inv:addItem(item, 1, false, true) then break end
    made = made + 1
  end
  return made
end
local function kill(ch, med)
  if CFG.kill_method == "declare" then ch:declareDead(); return true end
  local ponr = med:pointOfNoReturn()
  if type(ponr) ~= "number" then error("pointOfNoReturn is " .. type(ponr)) end
  med.blood = math.max(0, ponr - 1)
  return true
end
local function fname(ch)
  local ok, n = pcall(function() local f = ch:getFaction(); return f and f:getName() end)
  return (ok and n) or "owner"
end
-- РАБСТВО: убыль рабов (смерть от голода) по фракции-хозяину; состояние только в сессии (в сейв не пишется). Раз в сутки проверка порога -> заявка на караван работорговцев.
-- Публичного вызова «поставить колонну работорговцев» у дирижёра нет (road_plan 'caravan' строит маршрут только по излишку/дефициту склада), поэтому:
--   1) C.emit({type="slave_caravan", fid, town_sid, n, text}) - в хронику/шину; 2) метка спроса T.slave_demand() = { [фракция] = { n, day, town_sid, until_day } } - точка подключения для дирижёра/Traces.
HG.slv = { loss = {}, cd = {}, demand = {}, last_check = nil, emitted = 0 }
function T.slave_demand()   -- копия актуальных меток; читать pcall(KMM_Tempo.slave_demand)
  local out, day = {}, HG.day
  for k, d in pairs(HG.slv.demand) do if day == nil or d.until_day >= day then out[k] = { n = d.n, day = d.day, town_sid = d.town_sid, town_name = d.town_name, until_day = d.until_day } end end
  return out
end
local function slave_lost(key, day, tsid, tname)
  if not (CFG.slave_caravan and on("slave_caravan")) then return end
  local L = HG.slv.loss[key]; if not L then L = { days = {} }; HG.slv.loss[key] = L end
  L.days[day] = (L.days[day] or 0) + 1
  if tsid then L.town_sid, L.town_name = tsid, tname end
end
local function slave_daily(day)
  local V = HG.slv
  if V.last_check == day or not (CFG.slave_caravan and on("slave_caravan")) then return end
  V.last_check = day
  for key, L in pairs(V.loss) do
    local sum, any = 0, false
    for d, n in pairs(L.days) do
      if d <= day - CFG.slave_loss_days then L.days[d] = nil else sum = sum + n; any = true end
    end
    if not any then V.loss[key] = nil
    elseif sum >= CFG.slave_loss_min and (V.cd[key] or -1e9) <= day then
      V.cd[key] = day + CFG.slave_caravan_cd_days
      V.demand[key] = { n = sum, day = day, town_sid = L.town_sid, town_name = L.town_name, until_day = day + CFG.slave_demand_days }
      V.emitted = V.emitted + 1
      local txt = string.format("%s lost %d slaves in %d days; slavers' caravans are expected to bring fresh stock.", tostring(key), sum, CFG.slave_loss_days)
      tlog("SLAVES: demand " .. txt)
      local C = conductor()
      if C and C.emit then pcall(C.emit, { type = "slave_caravan", fid = key, town_sid = L.town_sid, town_name = L.town_name, n = sum, text = txt }) end
    end
  end
  for key, d in pairs(V.demand) do if d.until_day < day then V.demand[key] = nil end end
end

-- Калибровка знака шкалы по персонажам игрока (у них ванильный голод работает): только ЧТЕНИЕ hunger у 1-3 персонажей.
-- За >= cal_hours игровых часов монотонное изменение без скачков (еда даёт скачок -> наблюдение сначала) = направление «голодания».
local function calibrate(h)
  if HG.cal or not h then return end
  local pcs = getPlayerInterface():getAllPlayerCharacters()
  local n = 0
  for _, ch in pairs(pcs) do
    n = n + 1; if n > 3 then break end
    local ok, err = pcall(function()
      local v = ch:getMedical().hunger
      if type(v) ~= "number" then return end
      local key = T.hkey(ch)
      local o = HG.pobs[key]
      if not o then HG.pobs[key] = { h0 = h, v0 = v, last = v, sign = 0, max = v }; return end
      if v > o.max then o.max = v end
      local d = v - o.last; o.last = v
      if math.abs(d) < 1e-6 then return end
      local sg = d > 0 and 1 or -1
      if (o.sign ~= 0 and sg ~= o.sign) or math.abs(d) > CFG.hunger_full * 0.3 then HG.pobs[key] = { h0 = h, v0 = v, last = v, sign = 0, max = v }; return end
      o.sign = sg
      if h - o.h0 >= CFG.cal_hours and (v - o.v0) * sg > 0 then
        HG.cal = (sg < 0) and -1 or 1
        CFG.hunger_dir = HG.cal
        if o.max > CFG.hunger_full then CFG.hunger_full = math.ceil(o.max) end
        tlog(string.format("HUNGER calibrated dir=%d from player (hunger %s over %.1f h, max seen %.0f, full=%d)", HG.cal, sg < 0 and "falls" or "rises", h - o.h0, o.max, CFG.hunger_full))
      end
    end)
    if not ok and not HG.cal_err then HG.cal_err = true; tlog("HUNGER calibration read failed: " .. tostring(err)) end
    if HG.cal then return end
  end
end

local function hunger_one(r, h, day)
  local ch = r.ch
  if type(ch) ~= "table" and type(ch) ~= "userdata" then return end
  if type(ch.getMedical) ~= "function" or r.dead or r.down then return end
  if r.ap and r.ap.isPlayer then return end
  local okp, isp = pcall(ch.isPlayerCharacter, ch)
  if okp and isp then return end                                    -- игрок: ваниль сама
  local key = r.h
  if not key or key == "" or HG.killed[key] then return end
  local okdd, isdead = pcall(ch.isDead, ch)
  if okdd and isdead then return end
  local okn, need = pcall(ch.amSomeoneWhoNeedsToEatToLive, ch)
  if okn and need == false then return end                          -- роботы/скелеты
  local oka, animal = pcall(ch.isAnimal, ch)
  if oka and animal then return end
  local med = ch:getMedical()
  local fed = fed_get(med)
  local S = HG.st[key]
  if not S then
    if fed < -1 or fed > CFG.hunger_full * 1.5 then error("hunger value out of scale: " .. tostring(med.hunger)) end
    HG.st[key] = { t = h, fed = fed, seen = HG.tick }
    if HG.probe < CFG.hunger_probe_log then
      HG.probe = HG.probe + 1
      local okm, mg = pcall(ch.getMagicHungerSetting, ch)
      tlog(string.format("HUNGER probe: hunger=%s fed=%.1f magic=%s dir=%d", tostring(med.hunger), fed, okm and tostring(mg) or "n/a", CFG.hunger_dir))
    end
    return
  end
  S.seen = HG.tick
  local dt = h - S.t
  if dt < CFG.hunger_min_dt then return end
  dt = math.min(dt, CFG.hunger_max_dt)
  HG.stats.visited = HG.stats.visited + 1; HG.visits_total = HG.visits_total + 1
  local full = CFG.hunger_full
  -- роль
  local slave = false
  local oks, sl = pcall(ch.isSlave, ch)
  if oks and type(sl) == "number" and sl ~= 0 then slave = true end
  local prot = (CFG.protect_unique and not DISABLED.protect_unique and ((r.unique and true) or (r.trader and true))) or false
  local tsid, tname = town_of(r)
  -- 1) расход: недостающее до ванильной скорости
  if on("npc_hunger") then
    local observed = S.fed - fed                                    -- >0: ваниль уже тратит; <0: поел
    if observed >= -1 then
      local mult = 1
      local okm, m = pcall(function() return ch:getStats():calculateHungerMult() end)
      if okm and type(m) == "number" and m > 0 then mult = m end
      local expected = (full / CFG.starve_hours) * mult * dt
      -- ваниль уже тратит (в т.ч. с родным bed hunger rate во сне) -> её скорость не переписываем; эмуляция только если родного расхода нет вовсе
      if observed < expected * CFG.vanilla_drain_ok then
        local extra = expected - math.max(observed, 0)
        if extra > 0 then fed = fed - extra; HG.stats.drained = HG.stats.drained + extra end
      end
    else HG.stats.vanilla_ate = HG.stats.vanilla_ate + 1 end
  end
  if not HG.cal then   -- мягкий режим до калибровки знака: только лёгкий расход не ниже середины шкалы, без еды/рабов/смертей/защиты
    if not HG.pending_logged then HG.pending_logged = true; tlog("HUNGER calibration pending (soft mode: drain not below " .. CFG.soft_floor .. " of scale, no deaths)") end
    local mid = CFG.soft_floor * full
    if fed < mid then fed = math.min(S.fed, mid) end
    fed_set(med, math.min(fed, full))
    S.fed, S.t = fed_get(med), h
    return
  end
  local source_empty = false      -- источника еды нет, и это известно
  -- 2) еда
  if on("npc_feed") and fed < CFG.eat_below * full then
    local ate = false
    local okx, res = pcall(try_eat, ch)
    if okx and res then
      local nf = fed_get(med)
      if nf > fed then fed = nf else fed = fed + CFG.meal_restore * full end
      ate = true; HG.stats.ate = HG.stats.ate + 1
    end
    if not ate and tsid and not slave then
      if stock_food(tsid) then
        if stock_take(tsid, CFG.meal_units) >= CFG.meal_units then fed = fed + CFG.meal_restore * full; HG.stats.town_meals = HG.stats.town_meals + 1
        else
          source_empty = true
          if HG.deficit_day[tsid] ~= day then HG.deficit_day[tsid] = day; tlog("HUNGER: town food deficit " .. tostring(tname)) end
        end
      end
    end
  end
  -- 3) рабы: хозяин кормит минимально, пока он в загруженной зоне
  if slave and on("slave_hunger") then
    local owner_ok = false
    local okh, own = pcall(ch.getMySlaveOwner, ch)
    if okh and own then owner_ok = pcall(function() if own:isDead() then error("dead") end end) end
    local fl = CFG.slave_floor * full
    if not S.skey then
      S.skey = r.fid
      if not S.skey then local okf, n = pcall(function() local f = own and own:getFaction(); return f and f:getName() end); S.skey = okf and n or nil end
      S.skey = S.skey or fname(ch)
    end
    if owner_ok or (tsid and stock_food(tsid) and stock_food(tsid) >= CFG.slave_ration_units) then
      if fed < fl then
        if S.ration_day ~= day then
          S.ration_day = day
          if tsid then stock_take(tsid, CFG.slave_ration_units) end
          HG.stats.slave_rations = HG.stats.slave_rations + 1
          local fn = fname(ch); HG.fed_by[fn] = (HG.fed_by[fn] or 0) + 1
        end
        fed = fl
      end
    else source_empty = true end
  elseif not slave and not prot and (not tsid or not stock_food(tsid)) then
    fed = math.max(fed, CFG.wild_floor * full)                      -- вне города / склад города неизвестен: голодает, но не мрёт
  end
  -- 4) уникальные/торговцы: реалистичная защита (смерти от голода нет)
  if prot then
    local floor = CFG.prot_min * full
    if fed < CFG.prot_trigger * full and S.sup_day ~= day then
      S.sup_day = day
      local have = 0
      local okq, nn = pcall(ch.getNumFoodItems, ch); if okq and type(nn) == "number" then have = nn end
      if have < CFG.supply_min then
        local want = math.random(CFG.supply_min, CFG.supply_max) - have
        local okm, made = pcall(supply_food, ch, tsid, want)
        if okm and made and made > 0 then HG.stats.supplies = HG.stats.supplies + 1 end
        if not okm and not HG.sup_err then HG.sup_err = true; tlog("HUNGER: supply failed: " .. tostring(made)) end
      end
      local okx, res = pcall(try_eat, ch)
      local target = CFG.prot_meal * full
      if okx and res then fed = math.max(fed, fed_get(med), target) else fed = math.max(fed, target) end
      HG.stats.ate = HG.stats.ate + 1
    end
    if fed < floor then fed = floor end   -- деньги торговца ведёт блок КАССА (till), здесь не трогаем
    source_empty = false
  end
  if fed < 0 then fed = 0 end
  if fed > full then fed = full end
  -- 5) голодная смерть: источник известен и пуст, нет защиты, лимиты на город и сутки
  if on("npc_starve") and source_empty and not prot and fed <= 0 then
    S.zero = S.zero or h
    if h - S.zero >= CFG.starve_grace_h then
      local zone = tsid or "zone"
      local dz = HG.deaths[zone]
      if not dz or dz.day ~= day then dz = { day = day, n = 0 }; HG.deaths[zone] = dz end
      if dz.n < CFG.death_cap_town and HG.deaths_day < CFG.death_cap_day then
        local okk, err = pcall(kill, ch, med)
        if not okk then disable("npc_starve", err)
        else
          dz.n = dz.n + 1; HG.deaths_day = HG.deaths_day + 1; HG.stats.starved = HG.stats.starved + 1
          tlog("HUNGER: npc starved in " .. tostring(tname or (slave and "slave zone" or "the wilds")))
          if slave then pcall(slave_lost, S.skey or r.fid or fname(ch), day, tsid, tname) end
          local C = conductor()
          if C and C.emit then pcall(C.emit, { type = "hunger_starved", town_sid = tsid, town_name = tname, slave = slave or nil, text = "Hunger claimed a life in " .. tostring(tname or "the wastes") .. "." }) end
          HG.st[key] = nil; HG.killed[key] = h
          return
        end
      end
    end
  else S.zero = nil end
  fed_set(med, fed)
  S.fed, S.t = fed, h
end

local function hunger_tick(h)
  local G = rawget(_G, "KMM_Gov")
  local snap = G and G.snapshot and G.snapshot()
  if not snap or not snap.list then return end
  HG.tick = HG.tick + 1
  local day = math.floor(h / 24)
  if HG.day ~= day then HG.day = day; HG.deaths_day = 0 end
  pcall(slave_daily, day)
  local n = #snap.list
  if n == 0 then return end
  local per = math.min(CFG.hunger_per_tick, n)
  for _ = 1, per do
    HG.cursor = HG.cursor % n + 1
    local r = snap.list[HG.cursor]
    if r then
      local ok, err = pcall(hunger_one, r, h, day)
      if not ok then
        -- ошибка одного персонажа модуль не гасит; повторяющаяся ошибка при ни одном успехе (нет поля) - гасит
        HG.errs = (HG.errs or 0) + 1
        HG.last_err = tostring(err)
        if HG.errs >= 5 and not HG.okc then disable("npc_hunger", err); disable("npc_feed", err); disable("slave_hunger", err); return end
      else HG.okc = true end
    end
  end
  if HG.tick % 40 == 0 then for k, t0 in pairs(HG.killed) do if h - t0 > 48 then HG.killed[k] = nil end end end
  if HG.tick % 40 == 0 then for k, S in pairs(HG.st) do if HG.tick - S.seen > 200 then HG.st[k] = nil end end end
end

---------------------------------------------------------------------------------------------- КАССА (R3): касса торговца = богатство города
-- Ваниль: деньги торговца — деньги его отряда, Ownerships (BindingsReference: Character:getOwnerships, Ownerships:getMoney/setMoney/addMoney ✓код).
-- Окно торговли само не даёт продать дороже, чем есть в кассе («у торговца нет денег») — игроку приходится искать другой рынок.
-- Цель кассы = база x w. База — по виду города (till_base) и кассе торговца при первой встрече (в пределах [база, база*till_base_cap], без накопления между сессиями).
-- w = население (pop/pop0) x беспорядки x полка еды x осада x товарные полки x процветание фракции (Faction:getProsperityMultiplier, шкала ? -> TILL probe).
-- Входы только читаются: KMM_Conductor.town_mood(sid), KMM_Stock.stock(sid).siege / KMM_Stock.level(sid, cat).
-- Ход: раз в игровые сутки на торговца, пока он загружен (т.е. рядом игрок), и при первой встрече в сессии (визит); доля разрыва till_rate/till_down_rate, догон за пропуск.
local TL = { tr = {}, w = {}, prosp = {}, poor = {}, cursor = 0, tick = 0, probe = 0, errs = 0, okc = false,
  stats = { traders = 0, raised = 0, lowered = 0, up = 0, down = 0, poor = 0 } }
T._till = TL

local function till_prosperity(ch, day)   -- множитель процветания фракции торговца (ванильный ProsperityManager) или nil; кэш на сутки
  local okf, f = pcall(ch.getFaction, ch)
  if not (okf and f) then return nil end
  local okn, key = pcall(function() local gd = f:getData() or f.data; return gd and gd.stringID end)
  if not (okn and key) then key = tostring(f) end
  local c = TL.prosp[key]
  if c and c.day == day then return c.v end
  local okp, v = pcall(function() return f:getProsperityMultiplier() end)
  if not (okp and type(v) == "number" and v == v and v >= 0) then v = nil end
  TL.prosp[key] = { day = day, v = v }
  if TL.probe < CFG.till_probe_log then TL.probe = TL.probe + 1; tlog("TILL probe: faction " .. tostring(key) .. " prosperity_mult=" .. tostring(v)) end
  return v
end

function T.town_wealth(sid, pm)   -- w в [till_w_min, till_w_max] и разбор входов; нет данных о входе -> множитель 1
  local p = { pop = 1, unrest = 1, food = 1, siege = 1, goods = 1, prosp = 1 }
  local food, city = nil, nil
  local C = conductor()
  if C and C.town_mood then
    local ok, m = pcall(C.town_mood, sid)
    if ok and type(m) == "table" then
      if type(m.pop) == "number" and type(m.pop0) == "number" and m.pop0 > 0 then
        local r = clamp(m.pop / m.pop0, 0, 1.5)
        p.pop = (r < 1) and (0.3 + 0.7 * r) or (1 + 0.4 * (r - 1))     -- разграблен/вымер -> беднее; разросся -> чуть богаче
      end
      if type(m.unrest) == "number" then p.unrest = 1 - 0.5 * clamp(m.unrest, 0, 1) end
      if type(m.food) == "number" then food = m.food end
    end
  end
  local K = rawget(_G, "KMM_Stock")
  if type(K) == "table" then
    if K.stock then
      local ok, s = pcall(K.stock, sid)
      if ok and type(s) == "table" then
        if s.siege then p.siege = CFG.till_siege end
        city = s.city and true or false
      end
    end
    if K.level then
      if food == nil then local ok, v = pcall(K.level, sid, "food"); if ok and type(v) == "number" then food = v end end
      local sum, n = 0, 0
      for _, c in ipairs(CFG.till_goods) do
        local ok, v = pcall(K.level, sid, c)
        if ok and type(v) == "number" and v == v then sum = sum + v; n = n + 1 end
      end
      if n > 0 then p.goods = clamp(1 + 0.3 * (sum / n - 1), 0.75, 1.3) end
    end
  end
  if food and food == food then p.food = (food < 0.5) and (0.4 + 1.2 * clamp(food, 0, 0.5)) or 1 end   -- голод: пустая полка еды -> 0.4
  if pm then p.prosp = 0.6 + 0.4 * clamp(pm, 0, 1.5) end
  if city == nil and C and C.cfg then
    local okc, cf = pcall(C.cfg)
    local i = okc and type(cf) == "table" and cf.town_info and cf.town_info[sid]
    city = (i and i.kind == "city") and true or false
  end
  local w = clamp(p.pop * p.unrest * p.food * p.siege * p.goods * p.prosp, CFG.till_w_min, CFG.till_w_max)
  return w, p, city
end

local function till_town(sid, tname, ch, day)   -- богатство города на сутки (кэш); маркер TILL town при первом расчёте или сдвиге w >= 0.1
  local c = TL.w[sid]
  if c and c.day == day then return c end
  local w, p, city = T.town_wealth(sid, till_prosperity(ch, day))
  local last = c and c.lw
  c = { day = day, w = w, city = city, lw = last }
  TL.w[sid] = c
  if not last or math.abs(w - last) >= 0.1 then
    c.lw = w
    tlog(string.format("TILL town %s: w=%.2f (pop=%.2f unrest=%.2f food=%.2f siege=%.2f goods=%.2f prosp=%.2f)",
      tostring(tname or sid), w, p.pop, p.unrest, p.food, p.siege, p.goods, p.prosp))
  end
  return c
end

local function till_one(r, day)
  if not r.trader or r.dead then return end
  if r.ap and r.ap.isPlayer then return end
  local ch = r.ch
  if type(ch) ~= "table" and type(ch) ~= "userdata" then return end
  local okp, isp = pcall(ch.isPlayerCharacter, ch)
  if okp and isp then return end
  local key = r.h
  if not key or key == "" then return end
  local R = TL.tr[key]
  if R and R.day == day then return end                                  -- раз в игровые сутки
  local tsid, tname = town_of(r)
  if not tsid then return end                                           -- бродячий торговец: касса ванильная
  local own = ch:getOwnerships()
  local cur = own:getMoney()
  if type(cur) ~= "number" then error("Ownerships:getMoney is " .. type(cur)) end
  local W = till_town(tsid, tname, ch, day)
  if not R then                                                          -- первая встреча в сессии = визит игрока
    local kb = W.city and CFG.till_base.city or CFG.till_base.town
    R = { base = clamp(cur, kb, kb * CFG.till_base_cap), day = day - CFG.till_visit_days }
    TL.tr[key] = R
  end
  local gap = clamp(day - R.day, 1, CFG.till_max_gap)
  R.day, R.seen = day, TL.tick
  TL.stats.traders = TL.stats.traders + 1
  local target = math.floor(clamp(R.base * W.w, 0, CFG.till_max))
  local rate = (cur < target) and CFG.till_rate or CFG.till_down_rate
  local k = 1 - (1 - rate) ^ gap
  local new = math.floor(clamp(cur + (target - cur) * k, 0, math.max(cur, CFG.till_max)) + 0.5)
  if math.abs(new - cur) < CFG.till_min_delta then return end
  if own.setMoney then own:setMoney(new) else own:addMoney(new - cur) end
  local back = own:getMoney()
  if back ~= new then   -- HEALTH: вердикт noeffect только после till_noeff_n промахов подряд у разных торговцев и ни одной удачной записи
    TL.nap = (TL.nap or 0) + 1
    local msg = "money write not applied: " .. tostring(back) .. " vs " .. tostring(new)
    if not TL.wok and TL.nap >= (CFG.till_noeff_n or 3) then TL.fatal = msg .. " (" .. TL.nap .. " traders, none applied)" end
    error(msg)
  end
  TL.wok, TL.nap = true, 0
  local S = TL.stats
  if new > cur then S.raised = S.raised + 1; S.up = S.up + (new - cur) else S.lowered = S.lowered + 1; S.down = S.down + (cur - new) end
  if new < CFG.till_poor * R.base and TL.poor[tsid] ~= day then
    TL.poor[tsid] = day; S.poor = S.poor + 1
    tlog(string.format("TILL poor %s: trader cash %d -> %d (target %d, w=%.2f)", tostring(tname or tsid), cur, new, target, W.w))
  end
end

local function till_tick(h)
  local G = rawget(_G, "KMM_Gov")
  local snap = G and G.snapshot and G.snapshot()
  if not snap or not snap.list then return end
  local n = #snap.list
  if n == 0 then return end
  TL.tick = TL.tick + 1
  local day = math.floor(h / 24)
  for _ = 1, math.min(CFG.till_per_tick, n) do
    TL.cursor = TL.cursor % n + 1
    local r = snap.list[TL.cursor]
    if r then
      local ok, err = pcall(till_one, r, day)
      if TL.fatal then disable("till", TL.fatal, true); return end            -- запись денег не применилась: API не тот — выключаемся сразу
      if not ok then
        TL.errs = TL.errs + 1
        if TL.errs >= 5 and not TL.okc then disable("till", err); return end
      else TL.okc = true end
    end
  end
  if TL.tick % 50 == 0 then for k, R in pairs(TL.tr) do if day - R.day > 10 then TL.tr[k] = nil end end end
end

---------------------------------------------------------------------------------------------- ПОЛКИ (U4): темп пополнения лавки = жизнь города
-- Ваниль: торговый отряд перегенерирует товар раз в vendors refresh time (SQUAD_TEMPLATE; у нас 16 ч, economy.json vendor_turnover) по метке
-- Platoon.traderInventoryRefreshTime (TimeOfDay, RW ✓код). Что в метке — момент прошлого обновления или срок следующего — ? (-> RESTOCK probe).
-- Двигаем только время: ваниль переставила метку (= обновила лавку) -> один сдвиг на P*(1/m - 1) ч, цикл становится ~P/m.
-- Знак сдвига одинаков при обеих трактовках метки (+ч позже, -ч раньше). m = богатство города w (тот же T.town_wealth через till_town), сглажено по суткам.
-- Товар лавки ведёт KMM_Stock (родной refreshInventory(false) по этой же метке + раздача со склада города): Tempo — время, Stock — содержимое.
-- Только торговцы-жители города (Platoon.myBaseHomeTownData / isResidentSquad); бродячие и караваны — ваниль.
-- Выключили блок или весь модуль — несработавший сдвиг снимается (метка возвращается к ванильной) у платунов в снимке; прочие — ваниль со следующего цикла.
-- Единицы: читаем TimeOfDay:getTotalHours(), сдвигаем TimeOfDay:addHours(d) (BindingsReference: TimeOfDay). Пока restock_arm_reads чтений на разных тактах
-- не попали в окно |метка - сейчас| <= restock_plaus_h — только проба без записи (RESTOCK armed); неправдоподобное чтение до этого — блок выключается.
-- Повтор: первая встреча платуна в сессии и после скачка времени (загрузка сейва) — только запоминаем метку; сдвиг только когда ваниль
-- переставила метку на наших глазах. Сдвинутая метка из сейва повторно не сдвигается, загрузка не ускоряет лавку.
local RS = { pl = {}, m = {}, logd = {}, cursor = 0, tick = 0, probe = 0, errs = 0, okc = false, dirty = false,
  armed = false, reads = 0, read_tick = -1,
  stats = { platoons = 0, delayed = 0, hastened = 0, restamped = 0, rolled = 0, implausible = 0 } }
T._restock = RS

function T.restock_mult(w)   -- темп пополнения по богатству города: 1 = ваниль, <1 реже, >1 чаще
  local m = clamp(w or 1, CFG.restock_m_min, CFG.restock_m_max)
  if math.abs(m - 1) < CFG.restock_dead then m = 1 end
  return m
end

local function rs_town_m(tsid, tname, ch, day)   -- сглаженный темп города (раз в сутки шаг restock_smooth к цели)
  local c = RS.m[tsid]
  if c and c.day == day then return c.v end
  local tgt = T.restock_mult(till_town(tsid, tname, ch, day).w)
  local v = c and c.v or 1
  v = v + (tgt - v) * CFG.restock_smooth
  if math.abs(v - tgt) < 0.02 then v = tgt end
  RS.m[tsid] = { day = day, v = v }
  return v
end

local function rs_resident(pl, tsid)   -- житель этого города? дом другой -> караван/бродячий; данных нет -> как till (торговец в городе)
  local okh, hsid = pcall(function() local gd = pl.myBaseHomeTownData; return gd and gd.stringID end)
  if okh and type(hsid) == "string" and hsid ~= "" then return hsid == tsid, hsid end
  local okr, res = pcall(function() return pl.isResidentSquad end)
  if okr and type(res) == "boolean" then return res, nil end
  return true, nil
end

local function tod_get(pl)   -- часы метки или nil (метка не выставлена)
  local tod = pl.traderInventoryRefreshTime
  if tod == nil then return nil end
  local oku, un = pcall(function() return tod:isUnset() end)
  if oku and un == true then return nil end
  local t = tod:getTotalHours()
  if type(t) ~= "number" or t ~= t then error("traderInventoryRefreshTime:getTotalHours is " .. type(t)) end
  if t <= 0 then return nil end                                         -- нулевая метка: ещё не выставлена, о единицах не судим
  return t
end

local function tod_shift(pl, t, d)   -- сдвиг на d часов через addHours с проверкой; поле отдано копией -> пишем значение целиком
  local tod = pl.traderInventoryRefreshTime
  tod:addHours(d)
  local back = tod_get(pl)
  if back and math.abs(back - (t + d)) < 1e-3 then return true end
  if back and math.abs(back - t) < 1e-3 then
    pl.traderInventoryRefreshTime = tod
    back = tod_get(pl)
    if back and math.abs(back - (t + d)) < 1e-3 then return true end
  end
  return false, back
end

local function rs_plausible(t, now)   -- метка в часах того же отсчёта, что и мир? до restock_plaus_h*1.2 ч игры дни и часы не различить
  return now >= 1.2 * CFG.restock_plaus_h and math.abs(t - now) <= CFG.restock_plaus_h
end

local function restock_one(r, day, now)
  if not r.trader or r.dead then return end
  if r.ap and r.ap.isPlayer then return end
  local pl, key = r.pl, r.pkey
  if not pl or not key or key == "" then return end
  local R = RS.pl[key]
  if R and R.chk == RS.tick then return end                              -- платун уже смотрели в этом такте (другой член отряда)
  local tsid, tname = town_of(r)
  if not tsid then return end                                           -- вне города: ваниль
  if not R then
    local res, home = rs_resident(pl, tsid)
    R = { res = res }
    RS.pl[key] = R
    if RS.probe < CFG.restock_probe_log then
      RS.probe = RS.probe + 1
      local okt, t0 = pcall(tod_get, pl)
      tlog(string.format("RESTOCK probe %s: resident=%s home=%s refresh_time=%s now=%.1f", tostring(tname), tostring(res), tostring(home), tostring(okt and t0), now))
    end
  end
  R.chk, R.seen = RS.tick, day
  if not R.res then return end                                          -- караван/бродячий торговец: ваниль
  local t = tod_get(pl)
  if not t then return end
  if not RS.armed then                                                  -- проба единиц: только чтение
    if now < 1.2 * CFG.restock_plaus_h then return end
    if not rs_plausible(t, now) then
      RS.fatal = string.format("refresh time units implausible: %.2f vs now %.1f h", t, now); error(RS.fatal)
    end
    if RS.read_tick ~= RS.tick then RS.read_tick = RS.tick; RS.reads = RS.reads + 1 end
    if RS.reads >= CFG.restock_arm_reads then RS.armed = true; tlog(string.format("RESTOCK armed: %d plausible reads (last %.1f vs now %.1f h)", RS.reads, t, now)) end
  end
  local fresh = not R.obs
  if R.obs and math.abs(t - R.obs) < 1e-3 then return end               -- метка та же, что мы видели/записали
  R.obs, R.d = t, nil
  if fresh or not RS.armed then return end                               -- первая встреча/после загрузки: запомнить, не сдвигать
  RS.stats.restamped = RS.stats.restamped + 1                            -- ваниль обновила лавку и переставила метку на наших глазах
  if not rs_plausible(t, now) then RS.stats.implausible = RS.stats.implausible + 1; return end
  RS.stats.platoons = RS.stats.platoons + 1
  local m = rs_town_m(tsid, tname, r.ch, day)
  if math.abs(m - 1) < CFG.restock_dead then return end
  local P = CFG.restock_period_h
  local lo, hi = math.min(t, now - P), math.max(t, now + P / CFG.restock_m_min)   -- метку не уводим дальше этого окна
  local new = clamp(t + P * (1 / m - 1), lo, hi)
  local d = new - t
  if math.abs(d) < CFG.restock_min_shift_h then return end
  local ok, back = tod_shift(pl, t, d)
  if not ok then RS.fatal = "refresh time write not applied: " .. tostring(back) .. " vs " .. tostring(new); error(RS.fatal) end
  R.obs, R.d, RS.dirty = new, d, true
  local S = RS.stats
  if d > 0 then S.delayed = S.delayed + 1 else S.hastened = S.hastened + 1 end
  if RS.logd[tsid] ~= day then
    RS.logd[tsid] = day
    tlog(string.format("RESTOCK shift %s: m=%.2f %+.1fh (cycle ~%.0fh)", tostring(tname or tsid), m, d, P / m))
  end
end

local function restock_rollback()   -- снять несработавшие сдвиги: метка не менялась с нашей записи -> вернуть ванильную; только платуны снимка
  local G = rawget(_G, "KMM_Gov")
  local snap = G and G.snapshot and G.snapshot()
  local by = snap and snap.by_pkey
  local left = false
  for key, R in pairs(RS.pl) do
    if R.d then
      local recs = by and by[key]
      local pl = recs and recs[1] and recs[1].pl
      if pl then
        local okt, t = pcall(tod_get, pl)
        if okt and t and R.obs and math.abs(t - R.obs) < 1e-3 then
          local okw, done = pcall(tod_shift, pl, t, -R.d)
          if okw and done then RS.stats.rolled = RS.stats.rolled + 1 end
        end
        R.d, R.obs = nil, nil
      else left = true end
    end
  end
  if not left then RS.dirty = false; tlog("RESTOCK off: shifts rolled back (" .. RS.stats.rolled .. ")") end
end

local function restock_tick(h)
  local G = rawget(_G, "KMM_Gov")
  local snap = G and G.snapshot and G.snapshot()
  if not snap or not snap.list then return end
  local n = #snap.list
  if n == 0 then return end
  if RS.last_h and (h < RS.last_h - 0.5 or h - RS.last_h > CFG.restock_jump_h) then   -- скачок времени (загрузка сейва): метки чужие, запоминаем заново
    RS.pl = {}
    tlog(string.format("RESTOCK time jump %.1f -> %.1f h: re-observe", RS.last_h, h))
  end
  RS.last_h = h
  RS.tick = RS.tick + 1
  local day = math.floor(h / 24)
  for _ = 1, math.min(CFG.restock_per_tick, n) do
    RS.cursor = RS.cursor % n + 1
    local r = snap.list[RS.cursor]
    if r then
      local ok, err = pcall(restock_one, r, day, h)
      if RS.fatal then disable("restock", RS.fatal, true); return end         -- запись метки не применилась: поле не то — выключаемся сразу
      if not ok then
        RS.errs = RS.errs + 1; RS.last_err = tostring(err)
        if RS.errs >= 5 and not RS.okc then disable("restock", err); return end
      else RS.okc = true end
    end
  end
  if RS.tick % 50 == 0 then for k, R in pairs(RS.pl) do if day - (R.seen or day) > CFG.restock_forget_days then RS.pl[k] = nil end end end
end

local function restock_off(now)   -- блок/модуль выключен: откат сдвигов, раз в restock_seconds, пока есть что снимать
  if not RS.dirty or (RS.t_off and now - RS.t_off < CFG.restock_seconds) then return end
  RS.t_off = now
  if not pcall(restock_rollback) then RS.dirty = false end
end

---------------------------------------------------------------------------------------------- тик
local function summary(h)
  local day = math.floor(h / 24)
  if RT.day == nil then RT.day = day; return end
  if day == RT.day then return end
  RT.day = day
  if CFG.log_day_summary then
    local s, n = RT.stats, 0
    for _ in pairs(RT.npc) do n = n + 1 end
    tlog(string.format("day %d: max_fatigue=%.2f min_speed_mult=%.3f run_h=%.1f rest_h=%.1f npc_set=%d npc_restore=%d npc_tracked=%d disabled=%s",
      day, s.max_fat, s.min_mult, s.run_h, s.rest_h, s.npc_set, s.npc_restore, n, next(DISABLED) and "yes" or "none"))
    s.max_fat, s.min_mult, s.run_h, s.rest_h = 0, 1, 0, 0
    local g = HG.stats
    tlog(string.format("HUNGER day %d: visited=%d drained=%.0f ate=%d town_meals=%d slave_rations=%d supplies=%d starved=%d vanilla_ate=%d",
      day, g.visited, g.drained, g.ate, g.town_meals, g.slave_rations, g.supplies, g.starved, g.vanilla_ate))
    for fn, c in pairs(HG.fed_by) do tlog("HUNGER: slaves fed by " .. tostring(fn) .. " (" .. c .. ")") end
    HG.fed_by = {}
    for k in pairs(g) do g[k] = 0 end
    local ts = TL.stats
    if on("till") then
      tlog(string.format("TILL day %d: traders=%d raised=%d lowered=%d up=%d down=%d poor=%d", day, ts.traders, ts.raised, ts.lowered, ts.up, ts.down, ts.poor))
    end
    for k in pairs(ts) do ts[k] = 0 end
    local rs = RS.stats
    if on("restock") then
      tlog(string.format("RESTOCK day %d: platoons=%d delayed=%d hastened=%d restamped=%d implausible=%d armed=%s", day, rs.platoons, rs.delayed, rs.hastened, rs.restamped, rs.implausible, tostring(RS.armed)))
    end
    for k in pairs(rs) do if k ~= "rolled" then rs[k] = 0 end end
  end
end

local function g_tick()
  if not CFG.enabled or DISABLED.all or paused("all") then pcall(restock_off, os.clock()); return end
  local now = os.clock()
  if not RT.t_start then RT.t_start = now end
  if RT.t_poll and now - RT.t_poll < CFG.poll_seconds then return end
  RT.t_poll = now
  if not RT.ready then
    local okp, pcs = pcall(function() return getPlayerInterface():getAllPlayerCharacters() end)
    local any = false; if okp and pcs then pcall(function() for _ in pairs(pcs) do any = true; break end end) end   -- список движка - userdata: next() на нём падает (лог 2026-11-13), pairs работает
    if not any then return end
    RT.pre = (RT.pre or 0) + 1
    if now - RT.t_start < CFG.start_delay_seconds or RT.pre < CFG.start_delay_polls then return end
    RT.ready = true; RT.last_h = game_hours()
    tlog("start v1 (fatigue=" .. tostring(CFG.player_fatigue) .. " slow_max=" .. CFG.slow_max .. " hunger_extra=" .. CFG.hunger_extra .. " npc=" .. tostring(CFG.npc_pace) .. " till=" .. tostring(CFG.till) .. " restock=" .. tostring(CFG.restock) .. ")")
    return
  end
  local h = game_hours()
  if h then pcall(summary, h) end
  if on("player_fatigue") or on("player_slow") or on("player_hunger") then
    local ok, err = pcall(player_tick, h)
    if not ok then disable("player_fatigue", err); disable("player_slow", err); disable("player_hunger", err) end
  end
  if on("npc_pace") and (not RT.t_npc or now - RT.t_npc >= CFG.npc_seconds) then
    RT.t_npc = now
    local ok, err = pcall(npc_tick)
    if not ok then disable("npc_pace", err) end
  end
  if h and on("npc_hunger") and not HG.cal then
    local okc, errc = pcall(calibrate, h)
    if not okc then HG.cal_err = true; tlog("HUNGER calibration failed: " .. tostring(errc)) end
  end
  if h and on("npc_hunger") and (not RT.t_hunger or now - RT.t_hunger >= CFG.hunger_seconds) then
    RT.t_hunger = now
    local ok, err = pcall(hunger_tick, h)
    if not ok then disable("npc_hunger", err); disable("npc_feed", err); disable("slave_hunger", err) end
  end
  if h and on("till") and (not RT.t_till or now - RT.t_till >= CFG.till_seconds) then
    RT.t_till = now
    local ok, err = pcall(till_tick, h)
    if not ok then disable("till", err) end
  end
  if h and (not RT.t_rs or now - RT.t_rs >= CFG.restock_seconds) then
    RT.t_rs = now
    if on("restock") then
      local ok, err = pcall(restock_tick, h)
      if not ok then disable("restock", err) end
    else pcall(restock_off, now) end
  end
end

function T.tick() local ok, err = pcall(g_tick); if not ok then disable("all", err) end end
function T.status()
  local pz = {}
  for k in pairs(PAUSED) do if paused(k) then pz[k] = true else PAUSED[k] = nil end end
  return { ready = RT.ready, disabled = DISABLED, paused = pz, stats = RT.stats }
end
function T.fatigue() local out = {}; for k, s in pairs(RT.chars) do out[k] = s.f end; return out end

local function guarded(fn) return function(...) local ok, err = pcall(fn, ...); if not ok then disable("all", err) end end end
if Events and Events.on then
  T._handler = Events.on("GameWorld::charsUpdate", guarded(function()
    local G = rawget(_G, "KMM_Gov")
    if G and G.run then return G.run("tempo", T.tick) end
    return T.tick()
  end))
end
