-- KMM_Stock model — абстрактные склады городов дирижёра (DESIGN «Материальный мир»). Чистая модель: без API игры.
--
-- Контракт с дирижёром (INTEG):
--   local M = dofile(".../kmm_stock_model.lua")   -- или loadfile; модуль возвращает таблицу M
--   M.init(stock, cstate, cfg)                    -- stock = cstate.stock (живёт внутри состояния дирижёра S, сохраняется в sdata)
--   M.day(stock, cstate, day, emit)               -- раз в игровой день; emit(ev) — шина дирижёра, ev.type = "stock_*"
-- Читает из S: F[fid].{towns, alive, wealth, wealth0, strength, last_war, mode, hunger, stress, player, relic},
--   ore[t].{R, R0, mine, flow}, metal_price, ore_crisis, treaties (type "trade"), events (id, type, a, b, town_sid), free.
-- Пишет только в stock (и события через emit). Состояние дирижёра (богатство, сила) НЕ меняет.
-- Склад — абстрактные единицы по категориям; T = нормальный уровень города (100 × размер). Реликты, «божественное»,
-- Crafting Redux и дерево Relics (KMM_Tech) в категории не входят никогда — склад их не производит и не хранит.

local M = { VERSION = 1 }

M.CATS = { "food", "metal", "weapons", "armor", "med", "drugs", "lux", "scrap" }
local CATS = M.CATS

-- параметры по умолчанию (cfg.stock может переопределить любой ключ)
M.DEFAULTS = {
  unit_T = 100,                 -- нормальный уровень категории для города размера 1
  size_city = { [2] = 1.0, [5] = 1.4, [6] = 0.8, [7] = 1.6 },
  size_holding = 0.35, size_village = 0.45,
  -- нормы владений (фермы, лагеря, аванпосты) по категориям, доля нормы города того же размера: роскоши и лекарств там мало
  holding_norm = { food = 1, metal = 0.6, weapons = 0.6, armor = 0.6, med = 0.5, drugs = 0.5, lux = 0.25, scrap = 0.6 },
  holding_market = 0.8, holding_workshop = 0.5, med_holding = 0.008, lux_holding = 0.004,
  deficit = 0.2, overflow = 2.5, hard_cap = 3.0,    -- доли T
  spoil = { food = 0.02, med = 0.004, drugs = 0.006, metal = 0, weapons = 0.002, armor = 0.002, lux = 0.001, scrap = 0 },
  -- потребление (доля T в день) населением/гарнизоном
  eat = { food = 0.05, weapons = 0.012, armor = 0.010, med = 0.012, drugs = 0.012, lux = 0.02, metal = 0, scrap = 0 },
  -- производство (доля T в день, до множителей)
  food_city = 0.038, food_village = 0.11, food_holding = 0.05,
  ore_to_metal = 0.0012,        -- металл из рудного выхода узла (единицы руды дирижёра → единицы склада)
  smelt = 0.02,                 -- доля скрапа в металл в день (только пока металла меньше нормы; в рудный кризис ×crisis_smelt)
  -- рудный кризис дирижёра: металл фракции режет её «голод по металлу» (S.F.stress), в первый год кризиса — паника
  -- (запасы прячут, закупки металла падают), потом частичное восстановление (рудники дирижёра, переплавка)
  stress_metal = 0.6, crisis_panic = 0.6, crisis_panic_days = 300, crisis_after = 0.85, crisis_import = 0.5, crisis_smelt = 2.0,
  ws_metal_boost = 0.9,         -- темп мастерских × clamp(0.7 + boost·(металл/норма), 0.7, 1.7): приток металла (в т.ч. от игрока) ускоряет ковку
  workshop = 0.035,             -- мощность мастерских (доля T) × знание фракции
  med_city = 0.016, lux_city = 0.012, drugs_role = 0.05, scrap_city = 0.005, scrap_from_wear = 0.3,
  market_out = 0.04, market_in = 0.035,             -- продажи излишка / закупки на рынке (к T)
  caravan_rate = 0.06, trade_rate = 0.04, caravan_loss_war = 0.08, war_days = 20, siege_days = 6,
  plunder_share = { 0.45, 0.7 }, plunder_carry = 0.4, raid_take = { 0.08, 0.18 }, owner_change_loss = 0.15,
  event_cooldown = 45, caravan_lost_take = 0.06, caravan_cut_days = 12,
  -- TOWNLIFE: ротация лавок (смена специализации неуникальной лавки раз в rot_min_days..+rot_jitter дней, когда игрока нет в городе)
  rot_enabled = true, rot_min_days = 2, rot_jitter = 1, rot_tries = 12, rot_pending_days = 6,
  rot_cap_guild = 0.25, rot_cap_spec = 0.30,   -- потолки доли гильдии/специализации среди неуникальных лавок (критерий дизайна 0.25/0.35, запас на проверке)
  rot_weapons = false,                         -- оружие как новая специализация: только если рантайм умеет класть оружие (weapons_add)
}

local function P(stock, k) local c = stock.cfg; if c and c[k] ~= nil then return c[k] end; return M.DEFAULTS[k] end
local function clamp(x, a, b) if x < a then return a elseif x > b then return b end return x end

---------------------------------------------------------------------------------------------- справочники
-- ЗАКОННОСТЬ (CONTRA): таблица cfg.params.contra.legal (дирижёр кладёт её в P): список { pat = <Lua-паттерн по "fid имя">, <cat> = false | множитель спроса }.
-- false — категория незаконна для владельца: открытого производства/торговли нет, спрос (contra.demand) покрывается контрабандой.
M.CONTRA = {
  inflow = 0.3, demand = 0.5, confiscate = 0.012, trig = 0.25, delivery = 0.5, cooldown = 45, gap = 8, price = 1.5,
  legal = { { pat = "Holy Nation", drugs = false }, { pat = "Shek", lux = 0.5 } },
}
local function CT(stock)
  local cfg = M._cfg
  local c = cfg and cfg.params and cfg.params.contra
  return c or M.CONTRA
end
local function cfg_name(fid)
  local f = M._cfg and M._cfg.factions and M._cfg.factions[fid]
  return f and f.name or ""
end
-- legality(stock, fid, cat) -> illegal(bool), demand_mult(number)
local function legality(stock, fid, c)
  if not fid then return false, 1 end
  local C = CT(stock)
  local ill, mult = false, 1
  if c == "drugs" and stock.R and stock.R.ban[fid] then ill = true end
  local key
  for _, e in ipairs(C.legal or {}) do
    local v = e[c]
    if v ~= nil then
      key = key or (fid .. " " .. cfg_name(fid))
      if key:find(e.pat) then if v == false then ill = true elseif type(v) == "number" then mult = mult * v end end
    end
  end
  if ill then return true, (C.demand or 0.5) end
  return false, mult
end
M.legality = function(stock, fid, c) return legality(stock, fid, c) end
function M.illegal(stock, fid, c) local i = legality(stock, fid, c); return i end
function M.price(stock, t, c)   -- множитель цены для рантайма: контрабанда дороже
  local s = stock.towns and stock.towns[t]
  if s and s.owner and legality(stock, s.owner, c) then return CT(stock).price or 1.5 end
  return 1
end

local function town_info(cfg) return (cfg and cfg.town_info) or {} end
local function town_size(stock, I)
  if I.kind == "city" then return (P(stock, "size_city"))[I.type] or 1.0 end
  if I.type == 3 then return P(stock, "size_village") end
  return P(stock, "size_holding")
end
local function role_set(cfg, k)
  local out = {}
  for _, fid in ipairs((cfg and cfg.roles and cfg.roles[k]) or {}) do out[fid] = true end
  return out
end

local function new_store(stock, t, I, owner)
  local s = { owner = owner, size = town_size(stock, I), city = (I.kind == "city"), q = {}, def = {}, over = {}, told = {}, siege = -1, ws = "idle" }
  local T = P(stock, "unit_T") * s.size
  local hn = P(stock, "holding_norm")
  for _, c in ipairs(CATS) do s.q[c] = T * (s.city and 1 or (hn[c] or 1)) * ((c == "drugs" or c == "scrap") and 0.5 or 0.9) end
  return s
end

local function owners(cs)
  local o = {}
  for fid, f in pairs(cs.F or {}) do
    if f.alive then for t in pairs(f.towns or {}) do o[t] = fid end end
  end
  return o
end

function M.init(stock, cs, cfg)
  stock.v = M.VERSION
  stock.cfg = stock.cfg or (cfg and cfg.params and cfg.params.stock) or nil
  stock.towns = stock.towns or {}
  stock.ev_seen = stock.ev_seen or ((cs.next_id or 1) - 1)
  stock.last_day = stock.last_day or -1
  stock.metrics = stock.metrics or { days = 0, def = {}, over = {}, by_town = {} }
  stock.R = { drugs = role_set(cfg, "drugs"), ban = role_set(cfg, "drug_ban"), tech = role_set(cfg, "technopriests"),
              thieves = role_set(cfg, "thieves"), fences = role_set(cfg, "fences"), slavers = role_set(cfg, "slavers") }
  local own = owners(cs)
  for t, I in pairs(town_info(cfg)) do
    if not stock.towns[t] then stock.towns[t] = new_store(stock, t, I, own[t]) end
  end
  M._cfg = cfg
  return stock
end

---------------------------------------------------------------------------------------------- вспомогательное
local function Tof(stock, s) return P(stock, "unit_T") * s.size end
local function Tc(stock, s, c)   -- норма категории склада: город — T, владение — T × holding_norm[c]
  local T = P(stock, "unit_T") * s.size
  if s.city then return T end
  return T * ((P(stock, "holding_norm"))[c] or 1)
end
local function add(stock, s, c, v)
  if v ~= v or v == math.huge or v == -math.huge then return 0 end   -- NaN/inf из входа не портит склад
  local x = (s.q[c] or 0) + v
  local cap = P(stock, "hard_cap") * Tc(stock, s, c)
  s.q[c] = clamp(x, 0, cap)
  return s.q[c] - (x - v)   -- фактическое изменение
end
local function take(s, c, v)
  local have = s.q[c] or 0
  if v ~= v then return 0 end
  local d = math.min(have, math.max(0, v)); s.q[c] = have - d; return d
end

local function wealth_factor(f)
  if not f then return 0.35 end
  local r = (tonumber(f.wealth) or 0) / math.max(1, tonumber(f.wealth0) or 1)
  if r ~= r or r <= 0 then return 0.3 end   -- казна дирижёра может уйти в минус
  return clamp(r ^ 0.5, 0.3, 1.6)
end
local function at_war(stock, f, day) return f and (day - (f.last_war or -1000) < P(stock, "war_days")) end

local function hub_of(stock, cfg, fid, cs)   -- главный склад фракции: столица, иначе крупнейший город, иначе любой
  local F = cfg.factions and cfg.factions[fid]
  local f = cs.F[fid]
  if F and F.capital and f.towns[F.capital] and stock.towns[F.capital] then return F.capital end
  local best, bs
  for t in pairs(f.towns) do
    local s = stock.towns[t]
    if s and (not bs or s.size > bs or (s.size == bs and t < best)) then best, bs = t, s.size end
  end
  return best
end

local function ore_out(n, k)   -- выход узла дирижёра (как в ore_step): рудник — поток, жила — base_yield·R0·(R/R0)^k
  if not n then return 0 end
  local y = 0
  if n.mine and (n.flow or 0) > 0.5 then y = y + n.flow end
  if (n.R0 or 0) > 0 then y = y + 0.035 * n.R0 * ((n.R or 0) / n.R0) ^ k * 0.35 end
  return y
end

local function emit_ev(stock, emit, ev, day)
  if not emit then return end
  ev.day = day
  stock.metrics.events = (stock.metrics.events or 0) + 1
  emit(ev)
end

local function tname(cfg, t) local I = town_info(cfg)[t]; return (I and I.name) or tostring(t) end

---------------------------------------------------------------------------------------------- события дирижёра
local function plunder(stock, s, share, to)
  local carried = {}
  for _, c in ipairs(CATS) do
    local d = take(s, c, (s.q[c] or 0) * share)
    if to and c ~= "food" then carried[c] = d * P(stock, "plunder_carry") end
  end
  if to then for c, v in pairs(carried) do add(stock, to, c, v) end end
end

local function on_event(stock, cs, cfg, ev, day, emit)
  local ty = ev.type
  local T = stock.towns
  if ty == "town_captured" and ev.town_sid and T[ev.town_sid] then
    local s = T[ev.town_sid]
    local ps = P(stock, "plunder_share")
    local share = ps[1] + (ps[2] - ps[1]) * math.random()
    local hub = ev.a and cs.F[ev.a] and hub_of(stock, cfg, ev.a, cs)
    plunder(stock, s, share, hub and hub ~= ev.town_sid and T[hub] or nil)
    s.owner = ev.a; s.siege = day + P(stock, "siege_days"); s.sacked = day
    stock.metrics.sacks = (stock.metrics.sacks or 0) + 1
    if s.city then emit_ev(stock, emit, { type = "stock_sacked", a = ev.a, b = ev.b, town_sid = ev.town_sid, town_name = tname(cfg, ev.town_sid),
      text = string.format("The storehouses of %s were looted after it fell; the stalls stand half empty.", tname(cfg, ev.town_sid)) }, day) end
  elseif ty == "attack_repelled" and ev.town_sid and T[ev.town_sid] then
    local s = T[ev.town_sid]
    s.siege = day + P(stock, "siege_days")
    for _, c in ipairs({ "food", "weapons", "armor", "med" }) do take(s, c, Tc(stock, s, c) * 0.08) end
  elseif (ty == "raid" or ty == "slave_raid" or ty == "base_raid") and ev.b and cs.F[ev.b] and ty ~= "base_raid" then
    local hv = hub_of(stock, cfg, ev.b, cs)
    if hv then
      local rt = P(stock, "raid_take")
      local share = rt[1] + (rt[2] - rt[1]) * math.random()
      local ha = ev.a and cs.F[ev.a] and hub_of(stock, cfg, ev.a, cs)
      local s = T[hv]
      for _, c in ipairs({ "food", "lux", "weapons", "drugs", "med" }) do
        local d = take(s, c, (s.q[c] or 0) * share)
        if ha and T[ha] then add(stock, T[ha], c, d * 0.5) end
      end
    end
  elseif ty == "theft" and ev.b and cs.F[ev.b] then
    local hv = hub_of(stock, cfg, ev.b, cs)
    local ha = ev.a and cs.F[ev.a] and hub_of(stock, cfg, ev.a, cs)
    if hv then local d = take(T[hv], "lux", T[hv].q.lux * 0.1); if ha and T[ha] then add(stock, T[ha], "lux", d * 0.6) end end
  elseif ty == "drug_bust" and ev.b and cs.F[ev.b] then
    for t in pairs(cs.F[ev.b].towns) do local s = T[t]; if s then take(s, "drugs", s.q.drugs * 0.3) end end
  elseif ty == "ruin_expedition" and ev.a and cs.F[ev.a] then
    local h = hub_of(stock, cfg, ev.a, cs)
    if h then add(stock, T[h], "scrap", Tc(stock, T[h], "scrap") * 0.4) end
  elseif ty == "famine" and ev.a and cs.F[ev.a] then
    for t in pairs(cs.F[ev.a].towns) do local s = T[t]; if s then take(s, "food", s.q.food * 0.2) end end
  elseif ty == "player_sold" and ev.town_sid and T[ev.town_sid] and ev.cat and not ev.added then   -- поставка игрока; если PLAYER сам вызвал add - шлёт added=true
    local s = T[ev.town_sid]
    if s.q[ev.cat] then add(stock, s, ev.cat, tonumber(ev.n) or 0) end
  elseif ty == "caravan_lost" and ev.town_sid and T[ev.town_sid] then   -- груз потерян: склад-источник теряет часть, маршрут закрыт на N дней
    local s = T[ev.town_sid]
    if not ev.ambush then   -- видимая засада: груз списывает waylay_finish дирижёра (один раз)
      for _, c in ipairs({ "food", "metal", "weapons", "armor", "med" }) do take(s, c, (s.q[c] or 0) * P(stock, "caravan_lost_take")) end
    end
    s.cut = day + P(stock, "caravan_cut_days")
    if ev.to_sid and T[ev.to_sid] then T[ev.to_sid].cut = day + math.floor(P(stock, "caravan_cut_days") / 2) end
    stock.metrics.caravans_lost_ev = (stock.metrics.caravans_lost_ev or 0) + 1
  elseif ty == "chaos_incursion" and ev.town_sid and T[ev.town_sid] then
    plunder(stock, T[ev.town_sid], 0.2, nil)
  end
end

---------------------------------------------------------------------------------------------- шаг дня
local function metal_mult(stock, cs, f, day)   -- голод фракции по металлу и рудный кризис дирижёра
  local m = 1
  if f and f.stress then m = clamp(1 + P(stock, "stress_metal") * (1 - f.stress), 0.35, 1.15) end
  local cr = cs.ore_crisis
  if cr and cr.since then
    local age = day - cr.since
    if age < P(stock, "crisis_panic_days") then m = m * P(stock, "crisis_panic") else m = m * P(stock, "crisis_after") end
  end
  return m
end

local function produce(stock, cs, cfg, t, s, f, fid, day, oreK, ore_norm, mm)
  local T = Tof(stock, s)
  local I = town_info(cfg)[t] or {}
  local wf = wealth_factor(f)
  local free = not f
  local war = at_war(stock, f, day)
  local sieged = (s.siege or -1) >= day
  local eff = (free and 0.6 or 1) * (sieged and 0.4 or 1) * (f and f.succession and 0.8 or 1)
  -- еда
  local food = (s.city and P(stock, "food_city") or ((I.type == 3) and P(stock, "food_village") or P(stock, "food_holding"))) * Tc(stock, s, "food")
  add(stock, s, "food", food * eff * (0.8 + 0.2 * wf))
  -- металл: руда узла (истощение жил дирижёра/KMM_Ore) × голод по металлу/кризис + переплавка скрапа (в кризис — больше)
  local ore = ore_out(cs.ore and cs.ore[t], oreK)
  local metal = ore * P(stock, "ore_to_metal") * ore_norm * T * eff * mm
  local smelt = P(stock, "smelt") * (s.city and 1 or 0.3) * (cs.ore_crisis and P(stock, "crisis_smelt") or 1)
  local sm = (s.q.metal < Tc(stock, s, "metal")) and take(s, "scrap", s.q.scrap * smelt) or 0
  add(stock, s, "metal", metal + sm * 0.7)
  s.ore_in = metal
  -- мастерские: металл → оружие/броня по спросу; знание = богатство фракции (+ техножрецы); во владениях — кузня лагеря
  s.ws = "idle"
  local know = (f and stock.R.tech[fid]) and 1.25 or 1
  local Tw, Ta = Tc(stock, s, "weapons"), Tc(stock, s, "armor")
  local mlv = (s.q.metal or 0) / math.max(1e-6, Tc(stock, s, "metal"))
  local cap = P(stock, "workshop") * Tw * clamp(wf, 0.4, 1.4) * know * eff * (s.city and 1 or P(stock, "holding_workshop"))
            * clamp(0.7 + P(stock, "ws_metal_boost") * mlv, 0.7, 1.7)
  local needW = math.max(0, 1.4 * Tw - s.q.weapons)
  local needA = math.max(0, 1.4 * Ta - s.q.armor)
  local want = math.min(cap, needW + needA)
  local reserve = P(stock, "deficit") * Tc(stock, s, "metal")
  local use = math.min(want, math.max(0, s.q.metal - reserve))
  -- видимая цепочка KMM_Town уже сковала и доставила вещи за день (металл списан, изделия на складе) — модель их не дублирует
  local vm = s.vis_made or {}
  local vw, va = vm.weapons or 0, vm.armor or 0
  if want > 0 and use <= 0.05 * want then s.ws = "no_metal"
  elseif use > 0 then
    local wshare = (needW + needA > 0) and (needW / (needW + needA)) or 0.5
    local uw, ua = math.max(0, use * wshare - vw), math.max(0, use * (1 - wshare) - va)
    use = uw + ua
    take(s, "metal", use)
    add(stock, s, "weapons", uw)
    add(stock, s, "armor", ua)
    s.ws = (wshare >= 0.5) and "weapons" or "armor"
  end
  s.vis_made = nil
  s.ws_rate = use
  if s.city then
    if not legality(stock, fid, "med") then add(stock, s, "med", P(stock, "med_city") * T * eff * (0.7 + 0.3 * wf)) end
    if not legality(stock, fid, "lux") then add(stock, s, "lux", P(stock, "lux_city") * T * eff * wf * wf) end
    add(stock, s, "scrap", P(stock, "scrap_city") * T)
  else
    add(stock, s, "med", P(stock, "med_holding") * T * eff)
    add(stock, s, "lux", P(stock, "lux_holding") * T * eff * wf)
  end
  if f and stock.R.drugs[fid] and not legality(stock, fid, "drugs") then add(stock, s, "drugs", P(stock, "drugs_role") * Tc(stock, s, "drugs") * eff) end
  if war then add(stock, s, "scrap", 0.01 * T) end   -- обломки войны
end

local function consume(stock, cs, s, f, fid, day, t)
  local E = P(stock, "eat")
  local war = at_war(stock, f, day)
  local mob = f and f.mode == "mobilized"
  local garrison = f and clamp((f.strength or 0) / math.max(1, (f.strength0 or f.strength or 1)), 0.5, 1.6) or 0.7
  local pop = s.city and 1 or 0.6
  local tw = cs.town and t and cs.town[t]   -- население города (дирижёр): меньше людей - меньше спроса
  local pf = (type(tw) == 'table' and tw.pop and tw.pop0 and tw.pop0 > 0) and clamp(tw.pop / tw.pop0, 0.3, 1.6) or 1
  pop = pop * pf
  local function T(c) return Tc(stock, s, c) end
  take(s, "food", E.food * T("food") * pop * (1 + 0.15 * (garrison - 1)))
  local wear = (war and 2.2 or 1) * (mob and 1.5 or 1) * garrison
  -- нехватка: старые клинки чинят и держат в строю дольше (износ падает до 35 %), сломанное — в скрап
  local ww = wear * clamp(s.q.weapons / (0.8 * T("weapons")), 0.35, 1)
  local wa = wear * clamp(s.q.armor / (0.8 * T("armor")), 0.35, 1)
  local broken = take(s, "weapons", E.weapons * T("weapons") * ww) + take(s, "armor", E.armor * T("armor") * wa)
  add(stock, s, "scrap", broken * P(stock, "scrap_from_wear"))
  local _, dmed = legality(stock, fid, "med")
  local _, ddrg = legality(stock, fid, "drugs")
  local _, dlux = legality(stock, fid, "lux")
  take(s, "med", E.med * T("med") * (war and 2 or 1) * dmed)
  take(s, "drugs", E.drugs * T("drugs") * pop * ddrg)
  take(s, "lux", E.lux * T("lux") * pop * wealth_factor(f) * dlux)
  local conf = CT(stock).confiscate or 0.03   -- на незаконное налетает стража
  for _, c in ipairs(CATS) do if legality(stock, fid, c) then take(s, c, s.q[c] * conf) end end
  local sp = P(stock, "spoil")
  for _, c in ipairs(CATS) do if (sp[c] or 0) > 0 then take(s, c, s.q[c] * sp[c]) end end
end

local function market(stock, cs, s, f, fid, day, metal_price)
  -- продажи излишка наружу и закупки при нехватке; закупки режут осада, война, бедность, дорогой металл и паника кризиса
  local wf = wealth_factor(f)
  local sieged = (s.siege or -1) >= day
  local war = at_war(stock, f, day)
  local mo, mi = P(stock, "market_out"), P(stock, "market_in")
  local cr = cs.ore_crisis
  local panic = cr and cr.since and (day - cr.since < P(stock, "crisis_panic_days"))
  for _, c in ipairs(CATS) do
    local T = Tc(stock, s, c)
    local x = s.q[c]
    if x > T then take(s, c, (x - T) * mo)
    elseif not sieged and c ~= "scrap" then
      local r = mi * clamp(wf, 0.3, 1.4) * (war and 0.6 or 1) * (s.city and 1 or P(stock, "holding_market"))
      if c == "metal" or c == "weapons" or c == "armor" then
        r = r / (metal_price * metal_price)
        if panic then r = r * P(stock, "crisis_import") end
      end
      if fid and legality(stock, fid, c) then r = r * (CT(stock).inflow or 0.3) end   -- контрабанда: медленно
      add(stock, s, c, (T - x) * r)
    end
  end
end

local function caravans(stock, cs, cfg, day, emit)
  -- свои города: выравнивание долей к среднему по фракции; война режет и грабит, осада закрывает ворота
  local T_ = stock.towns
  local cr, loss = P(stock, "caravan_rate"), P(stock, "caravan_loss_war")
  for fid, f in pairs(cs.F) do
    if f.alive and not f.player then
      local list = {}
      for t in pairs(f.towns) do local s = T_[t]; if s and (s.siege or -1) < day and (s.cut or -1) < day then list[#list + 1] = s end end
      if #list >= 2 then
        local war = at_war(stock, f, day)
        local rate = cr * (war and 0.5 or 1)
        for _, c in ipairs(CATS) do
          local sum, tsum = 0, 0
          for _, s in ipairs(list) do sum = sum + s.q[c]; tsum = tsum + Tc(stock, s, c) end
          local ratio = sum / math.max(1, tsum)
          local lost = 0
          for _, s in ipairs(list) do
            local d = (ratio * Tc(stock, s, c) - s.q[c]) * rate
            if d > 0 then
              local l = war and d * loss or 0
              add(stock, s, c, d - l); lost = lost + l
            else take(s, c, -d) end
          end
          stock.metrics.caravan_lost = (stock.metrics.caravan_lost or 0) + lost
        end
      end
    end
  end
  -- торговые договоры (дирижёр/DIPLO): обмен между главными складами сторон
  local tr = P(stock, "trade_rate")
  for _, t in pairs(cs.treaties or {}) do
    if t.active and t.type == "trade" then
      local fa, fb = cs.F[t.a], cs.F[t.b]
      if fa and fb and fa.alive and fb.alive and not fa.player and not fb.player then
        local ha, hb = hub_of(stock, cfg, t.a, cs), hub_of(stock, cfg, t.b, cs)
        local A, B = ha and T_[ha], hb and T_[hb]
        if A and B and (A.siege or -1) < day and (B.siege or -1) < day and (A.cut or -1) < day and (B.cut or -1) < day then
          local war = at_war(stock, fa, day) or at_war(stock, fb, day)
          local rate = tr * (war and 0.5 or 1)
          for _, c in ipairs(CATS) do
            if not (legality(stock, t.a, c) or legality(stock, t.b, c)) then
              local ra, rb = A.q[c] / Tc(stock, A, c), B.q[c] / Tc(stock, B, c)
              local m = math.min(Tc(stock, A, c), Tc(stock, B, c))
              local d = (ra - rb) * m * rate * 0.5
              if d > 0 then add(stock, B, c, take(A, c, d)) elseif d < 0 then add(stock, A, c, take(B, c, -d)) end
            end
          end
          stock.metrics.trade_days = (stock.metrics.trade_days or 0) + 1
        end
      end
    end
  end
end

local function account(stock, cfg, day, emit)
  local Mx = stock.metrics
  Mx.days = Mx.days + 1
  local def, over = P(stock, "deficit"), P(stock, "overflow")
  local cd = P(stock, "event_cooldown")
  local hc = P(stock, "hard_cap")
  for t, s in pairs(stock.towns) do
    do
      s.lv, s.tn = s.lv or {}, s.tn or {}   -- публикуются для дирижёра: уровень (доля нормы) и норма по категориям
      for _, c in ipairs(CATS) do
        local Tn = Tc(stock, s, c)
        local q = tonumber(s.q[c]) or 0
        if q ~= q or q < 0 then q = 0 end
        if q > hc * Tn then q = hc * Tn end   -- потолок склада: ничего не копится бесконечно (и после внешних add)
        s.q[c] = q
        local r = q / Tn
        s.lv[c], s.tn[c] = r, Tn
        if r < def then
          if s.city then Mx.def[c] = (Mx.def[c] or 0) + 1 end
          if not s.def[c] then
            s.def[c] = day
            if s.city and (c == "food" or c == "metal" or c == "weapons") and day - (s.told[c] or -1000) >= cd and s.owner then
              s.told[c] = day
              emit_ev(stock, emit, { type = "stock_shortage", a = s.owner, town_sid = t, town_name = tname(cfg, t), cat = c,
                text = string.format("%s runs short of %s; prices climb at the stalls.", tname(cfg, t),
                  c == "food" and "food" or c == "metal" and "metal" or "blades") }, day)
            end
          end
        else
          if s.def[c] and r > def * 2 then s.def[c] = nil end
        end
        if r > over then
          if s.city then Mx.over[c] = (Mx.over[c] or 0) + 1 end
          if not s.over[c] and c ~= "scrap" then
            s.over[c] = day
            if s.city and (c == "food" or c == "metal") and day - (s.told["g" .. c] or -1000) >= cd * 2 and s.owner then
              s.told["g" .. c] = day
              emit_ev(stock, emit, { type = "stock_glut", a = s.owner, town_sid = t, town_name = tname(cfg, t), cat = c,
                text = string.format("%s is overflowing with %s; merchants cut their prices.", tname(cfg, t), c) }, day)
            end
          end
        elseif s.over[c] and r < over * 0.8 then s.over[c] = nil end
      end
    end
  end
end

local function smuggler_for(stock, cs, s, c)   -- кто возит: производитель наркотиков/скупщик краденого, иначе сам владелец
  local list = (c == "drugs") and stock.R.drugs or stock.R.fences
  local ids = {}
  for fid in pairs(list or {}) do if cs.F[fid] and cs.F[fid].alive and fid ~= s.owner then ids[#ids + 1] = fid end end
  table.sort(ids)
  if #ids > 0 then return ids[((stock.metrics.smug or 0) % #ids) + 1] end
  return s.owner
end
local function smuggle(stock, cs, cfg, day, emit)   -- спрос + дефицит по незаконной категории в городе: ходка контрабандистов (кулдаун на город и на мир)
  local C = CT(stock)
  if day - (stock.smug_day or -1000) < (C.gap or 8) then return end
  local ids = {}
  for t in pairs(stock.towns) do ids[#ids + 1] = t end
  table.sort(ids)
  for _, t in ipairs(ids) do
    local s = stock.towns[t]
    if s.city and s.owner and (s.siege or -1) < day then
      for _, c in ipairs(CATS) do
        if c ~= "scrap" and day - ((s.smug or {})[c] or -1000) >= (C.cooldown or 30) and legality(stock, s.owner, c)
           and s.q[c] < (C.trig or 0.3) * Tc(stock, s, c) then
          s.smug = s.smug or {}
          s.smug[c] = day; stock.smug_day = day
          add(stock, s, c, (C.delivery or 0.35) * Tc(stock, s, c))
          stock.metrics.smug = (stock.metrics.smug or 0) + 1
          local a = smuggler_for(stock, cs, s, c)
          emit_ev(stock, emit, { type = "smuggle_run", a = a, b = s.owner, town_sid = t, town_name = tname(cfg, t), cat = c,
            text = string.format("Smugglers slip %s into %s past the guards.", c, tname(cfg, t)) }, day)
          return
        end
      end
    end
  end
end

---------------------------------------------------------------------------------------------- TOWNLIFE: ротация лавок
-- Лавка = (гильдия, специализация) из kmm_townlife.lua. Гильдия не меняется (владельца/здание из Lua менять нельзя), специализация - да.
-- Состояние в stock.rot: ov = {[город] = {[лавка] = индекс специализации}}, next, pend = {[город] = {from, to, day}}, n, maxg, maxs.
-- Рантайм (kmm_stock.lua) по pend перекладывает вещи в реальной лавке рядом с игроком; модель и симуляция работают без игры.
local TL
local function townlife()
  if TL == nil then
    local ok, d = pcall(require, "kmm_townlife")
    TL = (ok and type(d) == "table" and type(d.shops) == "table") and d or false
  end
  return TL or nil
end
M.away = nil      -- function(town_sid) -> true, если игрока нет рядом с городом (ставит рантайм; nil = симуляция, всегда true)
M.rot_log = nil   -- function(msg) - строка TRADE (ставит рантайм)

local DER = setmetatable({}, { __mode = "k" })
local function rot_state(stock)
  local TLd = townlife()
  if not TLd then return nil end
  local R = stock.rot
  if type(R) ~= "table" then R = { ov = {}, pend = {}, n = 0 }; stock.rot = R end
  local D = DER[R]
  if not D then   -- производные счётчики не сохраняются в сейв и пересчитываются при каждой загрузке (дёшево: ~600 лавок)
    D = { gc = {}, sc = {}, N = 0, keys = {} }
    DER[R] = D
    for t, row in pairs(TLd.shops) do
      D.keys[#D.keys + 1] = t
      for i = 1, math.floor(#row / 2) do
        local sp = (R.ov[t] and R.ov[t][i]) or row[2 * i]
        local g = row[2 * i - 1]
        D.gc[g] = (D.gc[g] or 0) + 1; D.sc[sp] = (D.sc[sp] or 0) + 1; D.N = D.N + 1
      end
    end
    table.sort(D.keys)
    R.maxg, R.maxs = R.maxg or 0, R.maxs or 0
  end
  return R, TLd, D
end
local function rot_shares(R, D)
  local mg, ms = 0, 0
  for _, n in pairs(D.gc) do if n > mg then mg = n end end
  for _, n in pairs(D.sc) do if n > ms then ms = n end end
  return mg / math.max(1, D.N), ms / math.max(1, D.N)
end

-- одна попытка ротации (раз в rot_min_days..): возвращает запись {town, from, to, ...} или nil
function M.rot_try(stock, cs, cfg, day)
  if stock.rot_off or not P(stock, "rot_enabled") then return nil end
  local R, TLd, D = rot_state(stock)
  if not R or #D.keys == 0 then return nil end
  R.next = R.next or (day + P(stock, "rot_min_days"))
  if day < R.next then return nil end
  R.next = day + P(stock, "rot_min_days") + math.floor(math.random() * (P(stock, "rot_jitter") + 1))
  for t, p in pairs(R.pend) do if day - p.day > P(stock, "rot_pending_days") then R.pend[t] = nil end end
  local pf = cfg and cfg.player_faction
  for _ = 1, P(stock, "rot_tries") do
    local t = D.keys[math.random(#D.keys)]
    local s = stock.towns[t]
    local row = TLd.shops[t]
    if s and row and not R.pend[t] and (s.siege or -1) < day - 1 and not (pf and s.owner == pf)
       and (not M.away or M.away(t)) then
      local i = math.random(math.floor(#row / 2))
      local cur = (R.ov[t] and R.ov[t][i]) or row[2 * i]
      local g = row[2 * i - 1]
      if not TLd.fixed[cur] and TLd.cat[cur] then
        -- новая специализация: чаще редкая в мире, не выше потолка, не бар/книги; оружие - только если разрешено
        local cand, wsum = {}, 0
        for sp, c in pairs(TLd.cat) do
          if sp ~= cur and (c ~= "weapons" or P(stock, "rot_weapons")) and ((D.sc[sp] or 0) + 1) <= P(stock, "rot_cap_spec") * D.N then
            local w = 1 / math.max(1, D.sc[sp] or 1)
            cand[#cand + 1] = { sp, w }; wsum = wsum + w
          end
        end
        if #cand > 0 and (D.gc[g] or 0) <= P(stock, "rot_cap_guild") * D.N then   -- гильдия не меняется; потолок проверяется при каждой смене
          local r, pick = math.random() * wsum, cand[#cand][1]
          for _, c in ipairs(cand) do r = r - c[2]; if r <= 0 then pick = c[1]; break end end
          R.ov[t] = R.ov[t] or {}
          R.ov[t][i] = pick
          D.sc[cur] = D.sc[cur] - 1; D.sc[pick] = (D.sc[pick] or 0) + 1
          R.n = R.n + 1
          local mg, ms = rot_shares(R, D)
          if mg > R.maxg then R.maxg = mg end
          if ms > R.maxs then R.maxs = ms end
          R.pend[t] = { from = TLd.cat[cur], to = TLd.cat[pick], day = day, shop = i }
          local I = town_info(cfg)[t]
          local rec = { town = t, name = (I and I.name) or t, guild = TLd.guilds[g], from = TLd.specs[cur], to = TLd.specs[pick] }
          if M.rot_log then pcall(M.rot_log, string.format("shop rotated in %s: %s/%s -> %s/%s", rec.name, rec.guild, rec.from, rec.guild, rec.to)) end
          return rec
        end
      end
    end
  end
  return nil
end
-- сводка для симуляции/тестов
function M.rot_stats(stock)
  local R, _, D = rot_state(stock)
  if not R then return nil end
  local mg, ms = rot_shares(R, D)
  local np = 0; for _ in pairs(R.pend) do np = np + 1 end
  return { n = R.n, shops = D.N, max_guild_share = mg, max_spec_share = ms, max_guild_ever = R.maxg, max_spec_ever = R.maxs, pending = np, spec = D.sc, guild = D.gc }
end
function M.rot_pending(stock, t) local R = stock.rot; return R and R.pend and R.pend[t] or nil end
function M.rot_done(stock, t) local R = stock.rot; if R and R.pend then R.pend[t] = nil end end

-- TRADE (2026-11-13): день считается порциями. day_begin — события, владельцы, руда (дёшево, без цикла по городам);
-- day_step(ctx, n) — цикл по городам по n штук за вызов; day_end — караваны, контрабанда, учёт. M.day = всё подряд (тесты, офлайн-симуляция).
function M.day_begin(stock, cs, day, emit)
  if not stock.towns then M.init(stock, cs, M._cfg or {}) end
  local cfg = M._cfg or {}
  day = math.floor(day)
  if stock.last_day >= 0 and day <= stock.last_day then return nil end
  stock.last_day = day
  -- 1. события дирижёра с прошлого дня
  local seen = stock.ev_seen or 0
  for _, ev in ipairs(cs.events or {}) do
    if (ev.id or 0) > seen then
      seen = ev.id
      if type(ev.type) == "string" and ev.type:sub(1, 6) ~= "stock_" then on_event(stock, cs, cfg, ev, day, emit) end
    end
  end
  stock.ev_seen = seen
  -- 2. владельцы (революции, свободные города, распад — без события тоже)
  local own = owners(cs)
  for t, s in pairs(stock.towns) do
    local o = own[t]
    if s.owner ~= o then
      if s.owner and o and not (s.sacked == day) then
        for _, c in ipairs(CATS) do take(s, c, s.q[c] * P(stock, "owner_change_loss")) end
      end
      s.owner = o
    end
  end
  -- 3. руда: нормировка к стартовому выходу мира
  local oreK = 1.5
  if not stock.ore0 then
    local sum, n = 0, 0
    for t, nd in pairs(cs.ore or {}) do
      if stock.towns[t] and nd.R0 then sum = sum + ore_out({ R = nd.R0, R0 = nd.R0, mine = nd.mine, flow = nd.flow }, oreK); n = n + 1 end
    end
    stock.ore0 = (n > 0) and sum / n or 1
  end
  local ore_norm = 1 / math.max(1, stock.ore0) * 30
  local mp = clamp(cs.metal_price or 1, 0.6, 3)
  local keys, n = {}, 0
  for t in pairs(stock.towns) do n = n + 1; keys[n] = t end
  return { stock = stock, cs = cs, cfg = cfg, day = day, emit = emit, oreK = oreK, ore_norm = ore_norm, mp = mp, keys = keys, n = n, i = 0 }
end
function M.day_step(ctx, k)   -- true, когда города кончились
  local stock, cs, day = ctx.stock, ctx.cs, ctx.day
  local last = math.min(ctx.n, ctx.i + (k or ctx.n))
  while ctx.i < last do
    ctx.i = ctx.i + 1
    local t = ctx.keys[ctx.i]
    local s = stock.towns[t]
    if s then
      local fid = s.owner
      local f = fid and cs.F[fid] or nil
      produce(stock, cs, ctx.cfg, t, s, f, fid, day, ctx.oreK, ctx.ore_norm, metal_mult(stock, cs, f, day))
      consume(stock, cs, s, f, fid, day, t)
      market(stock, cs, s, f, fid, day, ctx.mp)
    end
  end
  return ctx.i >= ctx.n
end
function M.day_end_part(ctx, i)   -- 1 караваны, 2 контрабанда, 3 учёт и события; true — это была последняя часть
  local stock, cs, cfg, day, emit = ctx.stock, ctx.cs, ctx.cfg, ctx.day, ctx.emit
  if i == 1 then caravans(stock, cs, cfg, day, emit)
  elseif i == 2 then smuggle(stock, cs, cfg, day, emit)
  else
    account(stock, cfg, day, emit)
    local okr, e = pcall(M.rot_try, stock, cs, cfg, day)   -- TOWNLIFE: ошибка ротации не ломает учёт, отключает только её
    if not okr then stock.rot_off = tostring(e) end
  end
  return i >= 3
end
function M.day_end(ctx) for i = 1, 3 do M.day_end_part(ctx, i) end end
function M.day(stock, cs, day, emit)
  local ctx = M.day_begin(stock, cs, day, emit)
  if not ctx then return end
  M.day_step(ctx)
  M.day_end(ctx)
end

---------------------------------------------------------------------------------------------- чтение (для рантайма/TOWN)
function M.T(stock, s, c) if c then return Tc(stock, s, c) end; return Tof(stock, s) end
function M.level(stock, t, c)   -- доля нормы категории 0..3 (< deficit — дефицит, > overflow — переполнение)
  local s = stock.towns and stock.towns[t]
  if not s or not s.q[c] then return nil end
  return s.q[c] / Tc(stock, s, c)
end
-- для офлайн-прогона дирижёра (sim_years.py): запасы и пороги по категориям
function M.view(stock, cs)
  local out = {}
  for t, s in pairs(stock.towns or {}) do local row = {}; for c, v in pairs(s.q) do row[c] = v end; out[t] = row end
  return out
end
function M.bounds(stock, cs, t, c)
  local s = stock.towns and stock.towns[t]
  if not s then return nil end
  local T = Tc(stock, s, c)
  return P(stock, "deficit") * T, P(stock, "overflow") * T
end
function M.take(stock, t, c, v) local s = stock.towns and stock.towns[t]; if not s or not s.q[c] then return 0 end; return take(s, c, v) end
function M.made(stock, t, c, v)   -- изделие, сделанное видимой цепочкой: на склад + в дневной зачёт (модель не дублирует)
  local s = stock.towns and stock.towns[t]; if not s or not s.q[c] then return 0 end
  local r = add(stock, s, c, v)
  if c == "weapons" or c == "armor" then s.vis_made = s.vis_made or {}; s.vis_made[c] = (s.vis_made[c] or 0) + r end
  return r
end
function M.add(stock, t, c, v) local s = stock.towns and stock.towns[t]; if not s or not s.q[c] then return 0 end; return add(stock, s, c, v) end

return M
