-- KMM_Conductor_World: part of KMM_Conductor (world conductor), run by KC._BOOT in KMM_Conductor.lua
-- Часть дирижёра мира (KMM_Conductor.lua собирает части и регистрирует события). 1-я строка ASCII: имя чанка в тестах.
-- Здесь: шаг мира и мир v2 (беспорядки, семя, руда, потоки, наследование, осколки, хаос), GOALS (цели фракций, оплоты),
-- WS (world_step фазами под бюджет KMM_Gov), LINKN (смена владельца города -> вариант города через KMM_Native).
-- Код части выполняется не при загрузке файла, а в KC._BOOT() в порядке KC._PARTS (как шёл бы единый файл),
-- когда загружены все части — порядок загрузки файлов KenshiLua не важен.
local KC = rawget(_G, "KMM_C_INT")   -- общее пространство имён частей дирижёра (бывшие локали главного чанка: KC.<имя>)
if type(KC) ~= "table" then KC = { _SEG = {} }; _G.KMM_C_INT = KC end
if KC._booted then KC._SEG, KC._booted = {}, false end   -- повторная загрузка скриптов: собрать части заново
KC._SEG.World = function()
---------------------------------------------------------------------------------------------- шаг мира
function KC.next_interval()
  local iv = KC.P.interval
  return iv.base_days - iv.jitter_days + 2 * iv.jitter_days * math.random()
end

-- волнения: захваченный город бунтует (шанс растёт с волнением, расстоянием от столицы и числом городов, гарнизон гасит);
-- мятеж возвращает город прежнему владельцу (если жив) или город отделяется (свободный, его можно захватить снова)
function KC.unrest_step()
  local U = KC.P.unrest or {}
  for fid, f in pairs(KC.S.F) do
    if f.alive and f.unrest then
      for t, u in pairs(f.unrest) do
        if not f.towns[t] then f.unrest[t] = nil
        else
          u.level = u.level - (U.decay or 0.02)
          if u.level <= 0 then f.unrest[t] = nil
          else
            local cap_t = KC.capital(fid)
            local d = cap_t and KC.town_dist(t, cap_t) or 0
            local garrison = math.min(0.7, f.strength / (f.strength + (U.garrison_ref or 150)))
            local p = (U.base or 0.04) * u.level * (1 + d / 100000) * (1 + KC.ncities(f) * 0.05) * (1 - garrison)
            if math.random() < p then
              f.towns[t] = nil; f.unrest[t] = nil
              KC.S.stats.revolts = (KC.S.stats.revolts or 0) + 1
              local prev = u.prev
              if prev and KC.S.F[prev] and KC.S.F[prev].alive then
                KC.S.F[prev].towns[t] = true
                KC.emit({ type = "revolt", a = prev, b = fid, town_sid = t, town_name = KC.TOWN_NAME[t] or t,
                       text = string.format("%s rose against %s and returned to %s.", KC.TOWN_NAME[t] or t, KC.name(fid), KC.name(prev)) })
              else
                KC.S.free[t] = true
                KC.S.stats.secessions = (KC.S.stats.secessions or 0) + 1
                KC.emit({ type = "revolt", b = fid, town_sid = t, town_name = KC.TOWN_NAME[t] or t,
                       text = string.format("%s threw off %s and declared itself free.", KC.TOWN_NAME[t] or t, KC.name(fid)) })
              end
            end
          end
        end
      end
    end
  end
end

---------------------------------------------------------------------------------------------- мир v2 (шаг 1 офлайн-билда)
-- семя мира, Пик руды, потоки (наркотики, рабы, краденое, еда), кризис преемственности, осколки и варлорды, Хаос на кризисе
function KC.rnd(a, b) return a + (b - a) * math.random() end

KC.seed_world = function(s)
  local Z = KC.P.seed or {}
  s.seed = { r = math.random(1, 999999) }
  local A = { "expansion", "enrichment", "survival", "revenge", "faith" }
  for _, f in pairs(s.F) do
    if not f.player then
      local j, w = Z.strength_jitter or 0.25, Z.wealth_jitter or 0.3
      f.strength = f.strength * KC.rnd(1 - j, 1 + j); f.strength0 = f.strength
      f.wealth = f.wealth * KC.rnd(1 - w, 1 + w); f.wealth0 = math.max(1, f.wealth)
      if not f.relic and math.random() < (Z.ambition_shuffle or 0.15) then f.ambition = A[math.random(#A)] end
      f.metal, f.scrap, f.stress, f.hunger = 0, 0, 0.6, 0
      if f.relic then f.components = KC.rnd(70, 100) end
    end
  end
  local keys = {}
  for a, row in pairs(s.rel) do for b in pairs(row) do if a < b then keys[#keys + 1] = { a, b } end end end
  table.sort(keys, function(x, y) return x[1] .. x[2] < y[1] .. y[2] end)
  for _, k in ipairs(keys) do   -- отношения: дрожание в рамках лора; сильная вражда/дружба почти не двигается и не меняет знак
    local a, b = k[1], k[2]
    local v = s.rel[a][b]
    local lock = math.abs(v) >= (Z.rel_lock or 50)
    local nv = math.floor(v + (lock and KC.rnd(-3, 3) or KC.rnd(-(Z.rel_jitter or 12), Z.rel_jitter or 12)) + 0.5)
    nv = math.max(-100, math.min(100, nv))
    if lock and (nv > 0) ~= (v > 0) then nv = v end
    if nv ~= v then
      s.rel[a][b] = nv; s.rel[b] = s.rel[b] or {}; s.rel[b][a] = nv
      s.dirty_rel[a .. "|" .. b] = true
    end
  end
  s.ore = {}
  local mf = Z.mine_flow or { 25, 60 }
  for t, I in pairs(KC.CFG.town_info or {}) do
    local r = (I.kind == "city") and (Z.ore_city or { 2500, 6000 }) or (I.mine and (Z.ore_mine or { 3000, 8000 })) or (Z.ore_holding or { 1200, 4000 })
    local mine = I.mine or (I.kind ~= "city" and math.random() < 0.08)
    local R0 = KC.rnd(r[1], r[2])
    s.ore[t] = { R = R0, R0 = R0, mine = mine, flow = mine and KC.rnd(mf[1], mf[2]) or 0 }
  end
  s.ruins = {}
  local rs = Z.ruin_scrap or { 2000, 6000 }
  for _, st in ipairs(KC.CFG.sites or {}) do
    if st.kind == "ruins" then s.ruins[st.sid] = { scrap = KC.rnd(rs[1], rs[2]), comp = KC.rnd(10, 60) } end
  end
end

-- Пик руды ------------------------------------------------------------------------------------------------
function KC.ore_step()
  local O = KC.P.ore or {}
  local k = O.k or 1.5
  local tR, tR0, ssum, sn = 0, 0, 0, 0
  for _, n in pairs(KC.S.ore) do tR = tR + n.R; tR0 = tR0 + n.R0 end
  for fid, f in pairs(KC.S.F) do
    if f.alive and not f.player then
      local dmult = (O.demand_per_strength or 0.55) * (f.relic and 0.6 or 1) * (KC.ROLE.technopriests[fid] and 0.8 or 1)
      local demand = f.strength * dmult
      local supply = 0
      for t in pairs(f.towns) do   -- рудники: поток с содержанием; без оплаты деградируют
        local n = KC.S.ore[t]
        if n and n.mine and n.flow > 0.5 then
          if f.wealth >= (O.mine_upkeep or 3) then f.wealth = f.wealth - (O.mine_upkeep or 3); supply = supply + n.flow
          else n.flow = n.flow * (1 - (O.mine_decay_unpaid or 0.15)) end
        end
      end
      local sm = (f.scrap or 0) * (O.smelt_share or 0.5)   -- переплавка
      f.scrap = (f.scrap or 0) - sm; supply = supply + sm
      local need = demand - supply
      if need > 0 then   -- поверхностные жилы: добыча по нужде, выход ∝ (R/R0)^k
        local cap, csum = {}, 0
        for t in pairs(f.towns) do
          local n = KC.S.ore[t]
          if n and n.R > 0 then local y = (O.base_yield or 0.035) * n.R0 * (n.R / n.R0) ^ k; cap[t] = y; csum = csum + y end
        end
        if csum > 0 then
          local take = math.min(need, csum)
          for t, y in pairs(cap) do
            local n = KC.S.ore[t]
            local d = take * y / csum
            n.R = math.max(0, n.R - d)
            supply = supply + d
            if not n.told and n.R < 0.05 * n.R0 then
              n.told = true
              KC.S.stats.exhausted = (KC.S.stats.exhausted or 0) + 1
              KC.emit({ type = "mine_exhausted", a = fid, town_sid = t, town_name = KC.TOWN_NAME[t] or t,
                     text = string.format("The ore seams at %s have run dry; the miners' camp stands empty.", KC.TOWN_NAME[t] or t) })
            end
          end
        end
      end
      f.metal = math.min(math.max(0, (f.metal or 0) + supply - demand), demand * 6)
      f.metal_cap = (supply + 0.1 * f.metal) / math.max(0.01, dmult) * (O.metal_cap_mult or 1.6)
      local st = demand / math.max(0.1, supply + 0.15 * f.metal) + ((KC.P.loop or {}).metal_mix or 0.25) * (f.metal_def or 0)   -- CORE: склады подмешиваются
      f.stress = (f.stress or st) * 0.6 + st * 0.4
      if f.stress > 1 then
        local x = math.min(2, f.stress - 1)
        f.wealth = f.wealth - (O.stress_wealth_cost or 6) * x
        f.strength = f.strength * (1 - (O.stress_strength_cost or 0.02) * x)
      end
      if KC.ntowns(f) > 0 then ssum = ssum + f.stress; sn = sn + 1 end
      if f.stress > 1.2 and f.wealth > 200 then   -- дорогой металл окупает глубокий рудник
        local list = {}
        for t in pairs(f.towns) do local n = KC.S.ore[t]; if n and not n.mine and not KC.is_city(t) then list[#list + 1] = t end end
        table.sort(list)
        if #list > 0 and math.random() < 0.15 then
          local t = list[math.random(#list)]
          KC.S.ore[t].mine, KC.S.ore[t].flow = true, KC.rnd(15, 35)
          f.wealth = f.wealth - 150
          KC.S.stats.mines_built = (KC.S.stats.mines_built or 0) + 1
          KC.emit({ type = "mine_opened", a = fid, town_sid = t, town_name = KC.TOWN_NAME[t] or t,
                 text = string.format("%s sank a deep mine at %s; metal is worth the risk now.", KC.name(fid), KC.TOWN_NAME[t] or t) })
        end
      end
      if f.relic then f.components = math.max(0, (f.components or 100) - ((f.mode == "mobilized") and (O.comp_wear_mobilized or 0.3) or (O.comp_wear_focused or 0.04))) end   -- Сумерки реликтов
    end
  end
  KC.S.ore_share = tR / math.max(1, tR0)
  KC.S.ore_stress = ssum / math.max(1, sn)
  KC.S.metal_price = (O.metal_price_base or 1) * KC.clamp(0.7 + 0.5 * KC.S.ore_stress + 0.8 * (1 - KC.S.ore_share), 0.6, 3)
  if not KC.S.ore_crisis and KC.S.ore_share < (O.crisis_reserve_share or 0.45) and KC.S.ore_stress > (O.crisis_stress or 1.15) then
    KC.S.ore_crisis = { since = KC.DAY, phase = "deficit" }
    KC.S.stats.ore_crisis_day = KC.DAY
    KC.emit({ type = "ore_crisis", text = "Iron grows scarce across the land: smiths reforge old blades and every caravan with metal draws raiders." })
  elseif KC.S.ore_crisis then   -- излом: элита не может чинить реликты, голодная элита начинает грабить
    for fid, f in pairs(KC.S.F) do
      if f.alive and f.relic and (f.components or 100) < 30 and not f.broken_rule then
        f.broken_rule = true
        KC.S.ore_crisis.phase = "fracture"
        f.trigger_day, f.trigger_why = KC.DAY, "crisis"
        KC.emit({ type = "elite_hunger", a = fid, text = string.format("%s can no longer mend their relics; their patrols thin and grow desperate.", KC.name(fid)) })
      end
    end
  end
end

-- добыча игрока истощает ближайшую жилу мира (вызывает KMM_Ore)
function KC.PLAYER_MINED(amount, x, z)
  local best, bd
  for t, I in pairs(KC.CFG.town_info or {}) do
    if I.x and KC.S.ore[t] then local d = (I.x - x) ^ 2 + (I.z - z) ^ 2; if not bd or d < bd then best, bd = t, d end end
  end
  if best then local n = KC.S.ore[best]; n.R = math.max(0, n.R - amount * ((KC.P.ore or {}).player_drain_mult or 1)) end
  KC.S.stats.player_mined = (KC.S.stats.player_mined or 0) + amount
end
function KC.REGION_ORE(x, z)   -- доля остатка жил вокруг точки (0..1), для стартового запаса новых узлов игрока
  local r, r0 = 0, 0
  for t, I in pairs(KC.CFG.town_info or {}) do
    if I.x and KC.S.ore[t] and (I.x - x) ^ 2 + (I.z - z) ^ 2 <= 60000 ^ 2 then r, r0 = r + KC.S.ore[t].R, r0 + KC.S.ore[t].R0 end
  end
  if r0 <= 0 then return KC.S.ore_share or 1 end
  return r / r0
end
function KC.TIER_SHIFT(fid)   -- сдвиг тира снаряжения: богатство ± ржавчина от голода по металлу
  local f = KC.S and KC.S.F[fid]
  if not f then return 0 end
  local sh = KC.wealth_shift(fid)
  if (f.stress or 0) > 1.4 then sh = sh - 1 end
  if f.relic and (f.components or 100) < 30 then sh = sh - 1 end
  sh = sh + math.min(0, f.gear_shift or 0)   -- склады без брони/оружия: патрули в ржавом
  return KC.clamp(sh, -2, 1)
end

-- потоки ---------------------------------------------------------------------------------------------------
function KC.flows_step()
  local FL = KC.P.flows or {}
  for fid in pairs(KC.ROLE.drugs) do
    local f = KC.S.F[fid]
    if f and f.alive then
      f.wealth = f.wealth + (FL.drugs_income or 5)
      for b in pairs(KC.ROLE.drug_ban) do
        if KC.S.F[b] and KC.S.F[b].alive and KC.rel(b, fid) < 0 and math.random() < (FL.bust_chance or 0.08) then
          local loss = f.wealth * 0.1
          f.wealth = f.wealth - loss; KC.S.F[b].wealth = KC.S.F[b].wealth + loss * 0.5
          KC.S.stats.busts = (KC.S.stats.busts or 0) + 1
          KC.emit({ type = "drug_bust", a = b, b = fid, text = string.format("%s seized a smugglers' hashish cargo belonging to %s.", KC.name(b), KC.name(fid)) })
        end
      end
    end
  end
  local smult = KC.CFG.throes and 1.3 or 1   -- Throes of Obedience: рабство глубже, поток ценнее
  for fid in pairs(KC.ROLE.slavers) do
    local f = KC.S.F[fid]
    if f and f.alive then
      local market = false
      for m in pairs(KC.ROLE.slave_markets) do if KC.S.F[m] and KC.S.F[m].alive and KC.rel(m, fid) >= 0 then market = true end end
      f.wealth = f.wealth + (FL.slaves_income or 6) * smult * (market and 1 or 0.4)
      if math.random() < (FL.slave_raid_chance or 0.1) then
        local c = {}
        for _, o in ipairs(KC.near(fid, KC.P.bus.radius)) do if not KC.S.F[o].relic and not KC.S.F[o].player and KC.power(o) < KC.power(fid) and KC.rel(fid, o) < 20 then c[#c + 1] = o end end
        table.sort(c)
        if #c > 0 then
          local o = c[math.random(#c)]
          KC.S.F[o].strength = KC.S.F[o].strength * 0.97; f.wealth = f.wealth + 15 * smult; KC.add_rel(fid, o, -4)
          KC.S.stats.slave_raids = (KC.S.stats.slave_raids or 0) + 1
          KC.emit({ type = "slave_raid", a = fid, b = o, text = string.format("%s hunters dragged off people of %s in chains.", KC.name(fid), KC.name(o)) })
        end
      end
      for a in pairs(KC.ROLE.anti_slavers) do
        if KC.S.F[a] and KC.S.F[a].alive and math.random() < 0.05 then
          f.wealth = f.wealth * 0.95; KC.S.F[a].strength = KC.S.F[a].strength + 2
          KC.S.stats.freed = (KC.S.stats.freed or 0) + 1
          KC.emit({ type = "slaves_freed", a = a, b = fid, text = string.format("%s struck a slave column of %s and set the captives free.", KC.name(a), KC.name(fid)) })
        end
      end
    end
  end
  local V = KC.CFG.vassals   -- VASSALS: чёрные рынки — бандиты сбывают через нейтральный хаб, крупные фракции скупают без договора
  for _ = 1, (V and V.markets and #V.markets > 0) and (FL.market_tries or 3) or 0 do if math.random() < (FL.market_chance or 0.5) then
    local m = V.markets[math.random(#V.markets)]
    local own = KC.owner_of(m.town) or m.owner
    local g = m.goods[math.random(#m.goods)]
    local forb = {}
    for _, x in ipairs((V.market.buyer_forbidden or {})[g] or {}) do forb[x] = true end
    local function ok(x) return KC.S.F[x] and KC.S.F[x].alive and not KC.S.F[x].player and (x == own or KC.rel(x, own) >= -20) end
    local sl, bu = {}, {}
    for _, x in ipairs((V.market.sellers or {})[g] or {}) do if ok(x) then sl[#sl + 1] = x end end
    for _, x in ipairs((V.market.buyers or {})[g] or {}) do if ok(x) and not forb[x] then bu[#bu + 1] = x end end
    if #sl > 0 and #bu > 0 then
      local a = sl[math.random(#sl)]
      local c = {}
      for _, x in ipairs(bu) do if x ~= a and not KC.GL.banned(a, x) then c[#c + 1] = x end end
      if #c > 0 then
        local b = c[math.random(#c)]
        local price = (g == "slaves" and 40 or 25) * smult
        KC.S.F[a].wealth = KC.S.F[a].wealth + price
        KC.S.F[b].wealth = math.max(0, KC.S.F[b].wealth - price * 1.1)
        if KC.S.F[own] then KC.S.F[own].wealth = KC.S.F[own].wealth + price * 0.2 end
        if g == "slaves" then KC.S.F[b].strength = KC.S.F[b].strength * 1.005 end   -- руки на шахтах и полях
        KC.S.stats.market_deals = (KC.S.stats.market_deals or 0) + 1
        local tn = KC.TOWN_NAME[m.town] or m.name
        local txt = ({ slaves = "%s brought captives in chains to %s; buyers of %s took the lot.",
                       drugs = "%s moved a load of hashish through %s; %s merchants bought it quietly.",
                       stolen = "%s fenced stolen goods at %s; agents of %s paid without questions." })[g] or "%s traded at %s with %s."
        KC.emit({ type = "black_market", a = a, b = b, town_sid = m.town, town_name = tn, goods = g, owner = own,
               text = string.format(txt, KC.name(a), tn, KC.name(b)) })
      end
    end
  end end
  for fid in pairs(KC.ROLE.thieves) do   -- краденое: воры → скупщики
    local f = KC.S.F[fid]
    if f and f.alive and math.random() < (FL.theft_chance or 0.25) then
      local best, bw = nil, 150
      for _, o in ipairs(KC.near(fid, KC.P.bus.radius * 1.5)) do
        if not KC.S.F[o].player and not KC.S.F[o].relic and KC.S.F[o].wealth > bw then best, bw = o, KC.S.F[o].wealth end
      end
      if best then
        local take = KC.S.F[best].wealth * (FL.stolen_take or 0.03)
        KC.S.F[best].wealth = KC.S.F[best].wealth - take
        local fence
        for x in pairs(KC.ROLE.fences) do if x ~= fid and KC.S.F[x] and KC.S.F[x].alive then fence = x end end
        local cut = fence and take * (FL.fence_cut or 0.3) or 0
        f.wealth = f.wealth + take - cut
        if fence then KC.S.F[fence].wealth = KC.S.F[fence].wealth + cut end
        KC.S.stats.thefts = (KC.S.stats.thefts or 0) + 1
        if take > 25 then
          KC.emit({ type = "theft", a = fid, b = best, text = string.format("Thieves of %s emptied storehouses of %s%s.", KC.name(fid), KC.name(best),
            fence and (" and sold the goods through " .. KC.name(fence)) or "") })
        end
      end
    end
  end
  for fid, f in pairs(KC.S.F) do   -- еда: деревни кормят, города едят; торговые договоры подвозят
    if f.alive and not f.player and KC.ntowns(f) > 0 then
      local prod, cons = 0, 0
      for t in pairs(f.towns) do
        if KC.is_city(t) then cons = cons + (FL.food_per_city or 2); prod = prod + (FL.city_self_food or 1)
        else local I = KC.CFG.town_info[t]; prod = prod + ((I and I.type == 3) and (FL.food_per_village or 3) or (FL.food_per_holding or 1.2)) end
      end
      prod = prod + 0.6 * #KC.allies_of(fid, { trade = true }) + (f.wealth > 400 and 2 or 0)
      local h = KC.clamp((cons - prod) / math.max(1, cons) + ((KC.P.loop or {}).food_mix or 0.35) * (f.food_def or 0), 0, 1)   -- CORE: склады подмешиваются
      f.hunger = (f.hunger or 0) * 0.5 + h * 0.5
      if f.hunger > (FL.famine_level or 0.45) then
        local onset = not f.famine
        if not f.famine then
          f.famine = true
          KC.S.stats.famines = (KC.S.stats.famines or 0) + 1
          local c = KC.capital(fid)
          KC.emit({ type = "famine", a = fid, town_sid = c, town_name = c and (KC.TOWN_NAME[c] or c) or nil,
                 text = string.format("Hunger stalks %s: bread lines at %s, families leaving on the roads.", KC.name(fid), c and (KC.TOWN_NAME[c] or c) or "their towns") })
        end
        f.unrest = f.unrest or {}
        for t in pairs(f.towns) do
          if KC.is_city(t) and (onset or math.random() < 0.1) then
            local u = f.unrest[t] or { level = 0 }
            u.level = math.min(1.0, u.level + (onset and (FL.famine_unrest or 0.25) or 0.05) * f.hunger)
            f.unrest[t] = u
          end
        end
      elseif f.hunger < 0.15 then f.famine = false end
    end
  end
end

-- преемственность, осколки, варлорды ----------------------------------------------------------------------------
KC.start_succession = function(fid, why)
  local f = KC.S.F[fid]
  if not (f and f.alive) or f.player then return end
  local SC = KC.P.succession or {}
  if f.succession then f.succession.severity = math.min(3, f.succession.severity + 1); return end
  local d = SC.days or { 45, 120 }
  f.succession = { until_day = KC.DAY + KC.rnd(d[1], d[2]), severity = 1, why = why }
  f.strength = f.strength * (1 - (SC.strength_cost or 0.15))
  KC.S.stats.successions = (KC.S.stats.successions or 0) + 1
  KC.emit({ type = "succession_crisis", a = fid, text = string.format("%s is torn by a struggle for succession (%s).", KC.name(fid), why) })
end

function KC.active_shards() local n = 0; for _, F in pairs(KC.S.F) do if F.shard_active and F.alive then n = n + 1 end end; return n end
function KC.activate(sid, parent, share)
  local f, Pf = KC.S.F[sid], KC.S.F[parent]
  if not (f and Pf) then return false end
  if not f.alive and KC.active_shards() >= ((KC.P.shards or {}).sleepers_max_active or 6) then return false end
  f.alive, f.shard_active, f.sleeper = true, true, nil
  f.proxy = f.proxy or parent
  local ds = Pf.strength * share
  f.strength = f.strength + ds; Pf.strength = Pf.strength - ds
  local w = Pf.wealth * share * 0.7
  Pf.wealth = Pf.wealth - w; f.wealth = f.wealth + w
  f.strength0 = math.max(f.strength0, f.strength); f.wealth0 = math.max(f.wealth0, f.wealth)
  f.metal, f.scrap, f.stress, f.hunger = f.metal or 0, f.scrap or 0, f.stress or 0.8, f.hunger or 0
  local cap, list = KC.capital(parent), {}
  for t in pairs(Pf.towns) do if not KC.is_city(t) and t ~= cap then list[#list + 1] = t end end
  table.sort(list, function(a, b) return (cap and KC.town_dist(a, cap) or 0) > (cap and KC.town_dist(b, cap) or 0) end)
  local n = math.floor(#list * share + 0.5)
  for i = 1, n do Pf.towns[list[i]] = nil; f.towns[list[i]] = true end
  KC.set_rel(sid, parent, (KC.P.shards or {}).start_rel or -50)
  for o, v in pairs(KC.S.rel[parent] or {}) do
    if o ~= sid and KC.S.F[o] and (KC.S.rel[sid] or {})[o] == nil then KC.set_rel(sid, o, v - 10) end
  end
  return true, n
end

function KC.succession_step()
  local SC = KC.P.succession or {}
  for fid, f in pairs(KC.S.F) do
    if f.alive and f.succession then
      if KC.DAY >= f.succession.until_day then
        f.succession = nil
        KC.emit({ type = "succession_resolved", a = fid, text = string.format("%s has a new master; the infighting is over.", KC.name(fid)) })
      elseif math.random() < (SC.split_chance or 0.05) * f.succession.severity then
        local cands, pick = (KC.CFG.shards or {})[fid] or {}, nil
        for _, c in ipairs(cands) do if KC.S.F[c] and not KC.S.F[c].alive then pick = c; break end end
        if not pick then for _, c in ipairs(cands) do if KC.S.F[c] and KC.S.F[c].alive then pick = c; break end end end
        if pick then
          local ok, n = KC.activate(pick, fid, SC.split_share or 0.3)
          if ok then
            KC.S.stats.splits = (KC.S.stats.splits or 0) + 1
            KC.emit({ type = "faction_split", a = pick, b = fid, text = string.format("%s broke away from %s in the succession struggle%s.", KC.name(pick), KC.name(fid),
              (n or 0) > 0 and string.format(", taking %d holdings", n) or "") })
          end
        end
      end
    end
  end
end

function KC.shards_step()
  local SH = KC.P.shards or {}
  for fid, f in pairs(KC.S.F) do
    if f.alive and not f.player and not f.relic and not f.shard_active and f.strength >= (SH.warlord_min_strength or 120) then
      local troubled = f.succession or (f.stress or 0) > 1.3 or (f.hunger or 0) > 0.35 or f.decline_told
      if troubled and math.random() < (SH.warlord_chance or 0.03) then
        local pick
        for _, c in ipairs(KC.CFG.warlords or {}) do if KC.S.F[c] and not KC.S.F[c].alive then pick = c; break end end
        if pick then
          local ok = KC.activate(pick, fid, 0.15)
          if ok then
            KC.S.stats.warlords = (KC.S.stats.warlords or 0) + 1
            KC.emit({ type = "warlord_rose", a = pick, b = fid, text = string.format("A warlord rose among the discontented of %s; %s gather under new banners.", KC.name(fid), KC.name(pick)) })
          end
        end
      end
    end
  end
end

KC.REMNANTS = function(dead)   -- остатки разбитой армии: варлорд из спящих подбирает уцелевших
  local cf = KC.CFG.factions[dead]
  if not cf or (cf.strength or 0) < 60 or math.random() > 0.5 then return end
  for _, c in ipairs(KC.CFG.warlords or {}) do
    if KC.S.F[c] and not KC.S.F[c].alive then
      KC.S.F[dead].alive = true   -- activate берёт долю у «родителя»; мёртвому — вернуть статус
      local ok = KC.activate(c, dead, 1.0)
      KC.S.F[dead].alive = false
      if ok then
        KC.S.stats.warlords = (KC.S.stats.warlords or 0) + 1
        KC.emit({ type = "warlord_rose", a = c, b = dead, text = string.format("Survivors of %s rallied under %s.", KC.name(dead), KC.name(c)) })
      end
      return
    end
  end
end

-- Хаос растёт на нестабильности --------------------------------------------------------------------------------
function KC.overextended(fid, t)   -- держава у потолка доли городов не берёт новый город ни силой, ни миром
  return KC.is_city(t) and KC.ncities(KC.S.F[fid]) / math.max(1, KC.TOTAL_CITIES) >= ((KC.P.unrest or {}).max_city_share or 0.22)
end
function KC.free_step()
  for t in pairs(KC.S.free or {}) do
    local o = KC.ORIG_OWNER[t]
    if o and KC.S.F[o] and KC.S.F[o].alive and not KC.overextended(o, t) and math.random() < 0.05 then
      KC.S.free[t] = nil; KC.S.F[o].towns[t] = true
      KC.S.F[o].unrest = KC.S.F[o].unrest or {}; KC.S.F[o].unrest[t] = { level = 0.4 }
      KC.S.stats.rejoined = (KC.S.stats.rejoined or 0) + 1
      KC.emit({ type = "town_rejoined", a = o, town_sid = t, town_name = KC.TOWN_NAME[t] or t, text = string.format("%s opened its gates to %s again.", KC.TOWN_NAME[t] or t, KC.name(o)) })
    elseif math.random() < 0.02 then
      local I = KC.CFG.town_info[t]
      local best, bd
      if I and I.x then
        for fid, F in pairs(KC.S.F) do
          if F.alive and not F.player and not F.relic and not KC.overextended(fid, t) then
            local x, z = KC.FPOS(fid)
            if x then local d = (x - I.x) ^ 2 + (z - I.z) ^ 2; if not bd or d < bd then best, bd = fid, d end end
          end
        end
      end
      if best then
        KC.S.free[t] = nil; KC.S.F[best].towns[t] = true
        KC.S.F[best].unrest = KC.S.F[best].unrest or {}; KC.S.F[best].unrest[t] = { level = 0.5 }
        KC.S.stats.rejoined = (KC.S.stats.rejoined or 0) + 1
        KC.emit({ type = "town_captured", a = best, town_sid = t, town_name = KC.TOWN_NAME[t] or t, text = string.format("%s brought the free town of %s under its banner.", KC.name(best), KC.TOWN_NAME[t] or t) })
      end
    end
  end
end

function KC.chaos_step()
  local C = KC.P.chaos or {}
  KC.S.chaos = KC.S.chaos or {}
  local cf = {}
  for fid, f in pairs(KC.S.F) do if f.alive and f.relic == "spread_chaos" then cf[#cf + 1] = fid end end
  table.sort(cf)
  for fid, f in pairs(KC.S.F) do
    if f.alive and not f.player and not f.relic and KC.ntowns(f) > 0 then
      local nun = 0
      for _ in pairs(f.unrest or {}) do nun = nun + 1 end
      local ci = (f.succession and 1 or 0) + KC.clamp((f.stress or 0) - 1, 0, 1.5) + 2 * (f.hunger or 0) + 0.3 * nun + (f.decline_told and 0.5 or 0) + (KC.S.ore_crisis and 0.5 or 0)
      f.crisis = ci
      if ci > (C.crisis_threshold or 2) and KC.DAY - (f.last_cult or -1000) > (C.cooldown_days or 120) and math.random() < (C.incursion_chance or 0.25) then
        f.last_cult = KC.DAY
        local list = {}
        for t in pairs(f.towns) do list[#list + 1] = t end
        table.sort(list)
        local c = KC.capital(fid) or list[1]
        f.unrest = f.unrest or {}
        local u = f.unrest[c] or { level = 0 }
        u.level = math.min(1.2, u.level + 0.5)
        f.unrest[c] = u
        f.wealth = f.wealth - (C.cult_wealth_drain or 8)
        KC.S.chaos[c] = KC.DAY
        KC.S.stats.chaos = (KC.S.stats.chaos or 0) + 1
        local who = (#cf > 0) and cf[math.random(#cf)] or nil
        local ok_g, god, gsq, gcause = pcall(KC.L2.pick, fid)   -- LINKS2: бог по причине кризиса
        if not ok_g then KC.sub_log("chaos_pick failed: " .. tostring(god)); god, gsq, gcause = nil, nil, nil end
        if not god then KC.S.stats.chaos_nogod = (KC.S.stats.chaos_nogod or 0) + 1 end
        if god then KC.S.stats["chaos_god_" .. god] = (KC.S.stats["chaos_god_" .. god] or 0) + 1 end
        if who then
          KC.S.F[who].strength = KC.S.F[who].strength + (C.foothold_strength or 30) * 0.3
          KC.S.F[who].trigger_day, KC.S.F[who].trigger_why = KC.DAY, "crisis"
        end
        KC.emit({ type = "chaos_cult", a = who, b = fid, town_sid = c, town_name = KC.TOWN_NAME[c] or c, cause = gcause, god = god,
               text = string.format("Whispers of the Dark Gods spread in %s; a cult gathers in the hungry streets%s.", KC.TOWN_NAME[c] or c,
                 who and (" and " .. KC.name(who) .. " stir") or "") })
        if ci > (C.crisis_threshold or 2.5) + (C.incursion_extra or 1.0) and math.random() < (C.rift_chance or 0.5) then   -- прорыв: демоны в мир
          KC.S.stats.incursions = (KC.S.stats.incursions or 0) + 1
          f.strength = f.strength * 0.95
          KC.emit({ type = "chaos_incursion", b = fid, town_sid = c, town_name = KC.TOWN_NAME[c] or c, cause = gcause, god = god, squad = gsq,
                 text = string.format("A rift tore open near %s; daemons walk the land.", KC.TOWN_NAME[c] or c) })
        end
      end
    end
  end
end

---------------------------------------------------------------------------------------------- GOALS: цели фракций и роль оплотов (2026-11-13)
-- Каждая сознательная фракция (архетип: bandit/savage/trader/religion/settler/state/robot/imperium/chaos/xeno) держит ЦЕЛЬ f.goal = { k, n, need, t0 }.
-- Цель выбирается по архетипу и состоянию мира (голод/нужда, слабость, месть, акт сюжета) и смещает utility действий (GL.mult в choose_action);
-- progress растёт от реальных действий (GL.note после act) и собственных шагов (GL.own_step: паломничество, маршрут торговца, основание, патруль...).
-- Оплот (town_info.sh) = безопасность + рынок + убежище: опасность вокруг (S.danger, события шины) -> беженцы и караваны тянутся к оплоту,
-- владелец нанимает охрану (strength за wealth, Traces: гарнизон), бандиты/дикари обходят сильные оплоты (S.shield) и бьют слабых.
-- Работа порциями (по образцу day_chunk склада): GL.begin() в world_step строит очередь, GL.pump(n) в advance обрабатывает n записей за вызов.
-- Всё под xsafe/pcall: первая ошибка отключает блок до перезапуска (цели -> нейтральные множители 1.0).
KC.GL.GOALSET = {
  bandit   = { { "loot_roads", 1.2 }, { "racket", 1.0 }, { "seize_camp", 0.8 }, { "survive", 0.4 } },
  savage   = { { "hunt_travelers", 1.3 }, { "defend_lands", 0.9 }, { "seize_camp", 0.4 }, { "survive", 0.4 } },
  trader   = { { "trade_route", 1.6 }, { "grow", 0.6 }, { "survive", 0.5 } },
  religion = { { "pilgrimage", 1.2 }, { "crusade", 0.8 }, { "convert", 1.0 }, { "survive", 0.3 } },
  settler  = { { "found", 1.2 }, { "grow", 1.2 }, { "survive", 0.6 } },
  state    = { { "patrol", 1.2 }, { "grow", 0.8 }, { "trade_route", 0.5 }, { "survive", 0.5 } },
  robot    = { { "scavenge", 1.4 }, { "defend_lands", 0.8 }, { "survive", 0.4 } },
  imperium = { { "hunt", 1.4 }, { "scavenge", 0.7 }, { "survive", 0.3 } },
  chaos    = { { "spread", 1.4 }, { "scavenge", 0.5 }, { "survive", 0.3 } },
  xeno     = { { "spread", 1.2 }, { "hunt", 0.6 }, { "survive", 0.3 } },
}
KC.GL.NEED = { loot_roads = 3, racket = 2, seize_camp = 1, hunt_travelers = 3, defend_lands = 2, trade_route = 3, pilgrimage = 2, crusade = 2, convert = 3,
            found = 1, grow = 3, patrol = 3, scavenge = 2, hunt = 2, spread = 2, survive = 2, revenge = 1 }
KC.GL.ACTS = {   -- какие act() засчитываются целью
  loot_roads = { waylay = 1, raid_surplus = 1, raid = 1 }, racket = { raid = 1, waylay = 1 }, seize_camp = { capture_free = 1, expedition = 1, capture = 1 },
  hunt_travelers = { waylay = 1 }, defend_lands = { hide = 1, recruit = 1, raid = 1 }, trade_route = { trade = 1, trade_for = 1 },
  pilgrimage = { alliance = 1 }, crusade = { raid = 1, capture = 1 }, convert = { alliance = 1, trade = 1 }, found = { capture_free = 1 }, grow = { recruit = 1, trade = 1 },
  patrol = { recruit = 1, raid = 1, alliance = 1 }, scavenge = { expedition = 1, raid_surplus = 1 }, hunt = { raid = 1, capture = 1 }, spread = { raid = 1, capture = 1, waylay = 1 },
  survive = { hide = 1, recruit = 1, alliance = 1 }, revenge = { raid = 1, waylay = 1, capture = 1 },
}
function KC.GP() return (KC.P and KC.P.goals) or {} end
function KC.GD() return KC.GP().danger or {} end
function KC.garch(fid) local c = KC.CFG.factions[fid]; return c and c.arch end
function KC.gstat(k, n) KC.S.stats[k] = (KC.S.stats[k] or 0) + (n or 1) end
KC.GL.arch = KC.garch

function KC.GL.slots()
  KC.S.danger = KC.S.danger or {}; KC.S.founded = KC.S.founded or {}; KC.S.hire = KC.S.hire or {}; KC.S.shield = KC.S.shield or {}
end

function KC.GL.on() return KC.GL.off ~= true and KC.GP().enabled ~= false end

-- множитель utility действия a (цель + щит оплотов); вызывается из consider() в choose_action
function KC.GL.mult_impl(fid, f, a, o)
  local m = 1
  local G = f.goal
  if G then
    local b = (KC.GP().bias or {})[G.k]
    local v = b and b[a]
    if v then
      if f.townless or KC.ncities(f) == 0 then m = v else m = 1 + (v - 1) * (KC.GP().city_bias_mult or 0.5) end
    end
  end
  if o and KC.S.shield and (a == "raid" or a == "capture" or a == "waylay" or a == "raid_surplus") then
    local ar = KC.garch(fid)
    if ar == "bandit" or ar == "savage" then
      local O = KC.S.F[o]
      local sd = KC.S.shield[o]
      local SH = KC.GP().shield or {}
      if sd and sd > 0 then m = m / (1 + (SH.per_stronghold or 0.35) * sd)
      elseif O and O.strength < (SH.weak_ratio or 0.6) * f.strength then m = m * (SH.weak_boost or 1.3) end
    end
  end
  return m
end
function KC.GL.mult(fid, f, a, o)
  if KC.GL.off or KC.GP().enabled == false then return 1 end
  local ok, m = pcall(KC.GL.mult_impl, fid, f, a, o)
  if ok and type(m) == "number" then return m end
  KC.GL.off = true
  pcall(function() _G.KMM_Conductor.guard_log("goals disabled until restart: " .. tostring(m)) end)
  return 1
end

-- шина -> опасность вокруг оплотов
function KC.GL.hook_impl(ev)
  if not KC.S.danger then return end
  local D = KC.GD()
  local w = D[ev.type]
  if type(w) ~= "number" then return end
  local R = D.radius or 60000
  local sid = ev.town_sid
  local I = sid and KC.CFG.town_info[sid]
  if I and I.sh then KC.S.danger[sid] = (KC.S.danger[sid] or 0) + w; return end
  if I and I.x then
    local best, bd
    for _, t in ipairs(KC.GL.shl or {}) do
      local T = KC.CFG.town_info[t]
      local d = math.sqrt((T.x - I.x) ^ 2 + (T.z - I.z) ^ 2)
      if d <= R and (not bd or d < bd) then best, bd = t, d end
    end
    if best then KC.S.danger[best] = (KC.S.danger[best] or 0) + w * (1 - bd / R) end
    return
  end
  local b = ev.b and KC.S.F[ev.b]
  if b then for t in pairs(b.towns) do local T = KC.CFG.town_info[t]; if T and T.sh then KC.S.danger[t] = (KC.S.danger[t] or 0) + w * 0.5 end end end
end
function KC.GL.hook(ev) if not KC.GL.off and KC.GL.on() then KC.xsafe("goals_hook", KC.GL.hook_impl, ev) end end

function KC.GL.danger(sid)
  local d = KC.S.danger[sid] or 0
  local ab = (KC.GD().act_base or {})[(KC.S.story and KC.S.story.act) or ""]
  return d + (ab or 0)
end

-- выбор цели --------------------------------------------------------------------------------------------------
function KC.GL.pick(fid, f)
  local ar = KC.garch(fid)
  local set = KC.GL.GOALSET[ar]
  if not set then return nil end
  local act = KC.S.story and KC.S.story.act
  local need = (f.hunger or 0) > 0.3 or f.wealth < 0.5 * f.wealth0 or (f.food_def or 0) > 0.15
  local weak = f.strength < 0.6 * f.strength0 or (f.low_until and KC.DAY < f.low_until)
  local tot, opts = 0, {}
  local function add(k, w)
    if w > 0 then opts[#opts + 1] = { k, w }; tot = tot + w end
  end
  for _, e in ipairs(set) do
    local k, w = e[1], e[2]
    if k == "loot_roads" or k == "racket" or k == "hunt_travelers" or k == "seize_camp" then
      if need then w = w * 1.6 end
      if weak then w = w * 0.5 end
      if act == "famine" then w = w * 1.3 end
    elseif k == "survive" then
      if weak then w = w * 3 end
      if need then w = w * 1.5 end
      if act == "night" then w = w * 1.4 end
    elseif k == "pilgrimage" or k == "crusade" then
      if act == "night" then w = w * 1.6 end
    elseif k == "convert" then
      if act == "twilight" then w = w * 1.3 end
    elseif k == "trade_route" then
      if act == "famine" then w = w * 1.3 elseif act == "quiet" then w = w * 1.2 end
    elseif k == "found" or k == "grow" then
      if act == "quiet" or act == "forge" then w = w * 1.4 end
      if weak and k == "found" then w = w * 0.6 end
      if need and k == "grow" then w = w * 1.3 end
    elseif k == "scavenge" then
      if act == "scramble" then w = w * 1.5 end
      if need then w = w * 1.3 end
    elseif k == "hunt" or k == "spread" then
      if act == "night" or act == "twilight" then w = w * 1.4 end
    end
    if k == "found" and (f.founded or 0) >= (KC.GP().found_max or 3) then w = 0 end
    add(k, w)
  end
  local rv = 0
  for _, d0 in pairs(f.wronged or {}) do if KC.DAY - d0 < 90 then rv = rv + 1 end end
  if rv > 0 and not weak then add("revenge", 1.5 * math.min(2, rv)) end
  if tot <= 0 then return nil end
  local r, acc = math.random() * tot, 0
  for _, o in ipairs(opts) do acc = acc + o[2]; if r <= acc then return o[1] end end
  return opts[#opts][1]
end

function KC.GL.set_goal(fid, f, k)
  f.goal = { k = k, n = 0, need = KC.GL.NEED[k] or 2, t0 = KC.DAY }
  KC.gstat("goal_set")
end

-- результат
function KC.GL.finish(fid, f, ok)
  local G = f.goal
  if not G then return end
  local Gp = KC.GP()
  f.goal, f.goal_next = nil, KC.DAY + (Gp.goal_gap or 6)
  if ok then
    f.goals_done = (f.goals_done or 0) + 1
    f.wealth = f.wealth + (Gp.reward_wealth or 14)
    f.strength = f.strength + (Gp.reward_strength or 4)
    KC.gstat("goals_done"); KC.gstat("goals_done_" .. (KC.garch(fid) or "?"))
    local c = KC.CFG.factions[fid]
    if c and c.townless then KC.gstat("goals_done_townless") end
    if f.goals_done == 1 or f.goals_done % 10 == 0 then
      KC.emit({ type = "goal_milestone", a = fid, goal = G.k, n = f.goals_done, text = string.format("%s have seen their aim through (%s); more follow.", KC.name(fid), G.k) })
    else
      KC.emit({ type = "goal_done", a = fid, goal = G.k, n = f.goals_done })
    end
  else
    f.goals_failed = (f.goals_failed or 0) + 1
    KC.gstat("goals_failed")
  end
end

function KC.GL.note(fid, a, o)
  if KC.GL.off or not KC.GL.on() then return end
  local f = KC.S.F[fid]
  local G = f and f.goal
  if not G then return end
  local acts = KC.GL.ACTS[G.k]
  if not (acts and acts[a]) then return end
  if G.k == "revenge" and not (o and f.wronged and f.wronged[o] and KC.DAY - f.wronged[o] < 90) then return end
  G.n = G.n + 1
  if G.n >= G.need then KC.GL.finish(fid, f, true) end
end

-- собственные шаги (цели без естественного действия) ------------------------------------------------------------
function KC.nearest_stronghold_of(fid, x, z, maxd, relmin)   -- ближайший оплот чужого владельца (rel >= relmin); -> sid, owner, d
  local best, bo, bd
  for _, t in ipairs(KC.GL.shl or {}) do
    local T = KC.CFG.town_info[t]
    local ow = KC.GL.own[t]
    if ow and ow ~= fid and KC.S.F[ow] and KC.S.F[ow].alive and KC.rel(fid, ow) >= relmin then
      local d = math.sqrt((T.x - x) ^ 2 + (T.z - z) ^ 2)
      if d <= maxd and (not bd or d < bd) then best, bo, bd = t, ow, d end
    end
  end
  return best, bo, bd
end

function KC.GL.own_step(fid, f)
  local G = f.goal
  if not G then return end
  local Gp = KC.GP()
  local x, z = KC.FPOS(fid)
  local k = G.k
  if k == "pilgrimage" then
    if not x or f.wealth < (Gp.pilgrim_cost or 3) then return end
    local t, ow = KC.nearest_stronghold_of(fid, x, z, 120000, 15)
    if not t then return end
    f.wealth = f.wealth - (Gp.pilgrim_cost or 3)
    KC.add_rel(fid, ow, 2)
    G.n = G.n + 1
    KC.gstat("pilgrimages")
    KC.emit({ type = "pilgrimage", a = fid, b = ow, town_sid = t, town_name = KC.TOWN_NAME[t] or t })
  elseif k == "trade_route" then
    local best, bd = nil, 0
    for _, t in ipairs(KC.GL.shl or {}) do   -- пункт назначения: оплот с наибольшей опасностью/нуждой (убежище нуждается в припасах)
      local ow = KC.GL.own[t]
      if ow and ow ~= fid and KC.S.F[ow] and KC.S.F[ow].alive and KC.rel(fid, ow) >= -20 then
        local lf = KC.tlv(t, "food") or 1
        local need = KC.GL.danger(t) + math.max(0, 1 - lf) * 2 + math.random() * 0.4
        if need > bd then best, bd = t, need end
      end
    end
    if not best then return end
    local B = KC.GL.own[best]
    local owners, seen = {}, {}
    for _, t in ipairs(KC.GL.shl or {}) do   -- откуда везти: владельцы других оплотов, не враждебные ни торговцу, ни получателю
      local ow = KC.GL.own[t]
      if ow and not seen[ow] and ow ~= B and ow ~= fid and KC.S.F[ow].alive and KC.rel(fid, ow) >= -20 and KC.rel(ow, B) > -60 then seen[ow] = true; owners[#owners + 1] = ow end
    end
    local cats, moved, from, cat = { "food", "metal", "med" }, 0, nil, nil
    if #owners > 0 then
      local o0 = math.random(#owners)
      for tr = 0, math.min(#owners, 6) - 1 do
        local ow = owners[(o0 + tr - 1) % #owners + 1]
        local c = cats[(tr % #cats) + 1]
        moved = KC.ship(ow, B, c, Gp.route_share or 0.35)
        if moved > 0 then from, cat = ow, c; break end
      end
    end
    if not from then
      G.n = G.n + 0.2   -- пустой рейс: хоть что-то везли (цель идёт медленнее)
    else
      f.wealth = f.wealth + math.min(12, moved * 0.06) + 1
      G.n = G.n + 1
      KC.gstat("routes"); KC.gstat("routes_moved", moved)
      KC.emit({ type = "trade_route", a = fid, b = B, town_sid = best, town_name = KC.TOWN_NAME[best] or best, cat = cat, n = math.floor(moved) })
    end
  elseif k == "found" then
    if not x or f.wealth < (Gp.found_cost or 40) or (f.founded or 0) >= (Gp.found_max or 3) then return end
    local bs, bd
    for _, st in ipairs(KC.CFG.sites or {}) do
      if not KC.S.founded[st.sid] then
        local d = math.sqrt((st.x - x) ^ 2 + (st.z - z) ^ 2)
        if d <= 60000 and (not bd or d < bd) then bs, bd = st, d end
      end
    end
    if not bs then return end
    KC.S.founded[bs.sid] = fid
    f.founded = (f.founded or 0) + 1
    f.wealth = f.wealth - (Gp.found_cost or 40)
    f.strength = f.strength + 6
    G.n = G.n + 1
    KC.gstat("founded")
    KC.emit({ type = "settlement_founded", a = fid, town_sid = bs.sid, town_name = bs.name,
           text = string.format("%s raised a new settlement among the ruins of %s.", KC.name(fid), bs.name or "the old world") })
  elseif k == "grow" then
    if f.wealth >= 20 then f.wealth = f.wealth - 6; f.strength = f.strength + 2; G.n = G.n + 1 end
  elseif k == "patrol" then
    if f.wealth < 5 then return end
    f.wealth = f.wealth - 3; f.strength = f.strength + 1
    G.n = G.n + 1
    if x then   -- патруль гасит опасность у ближайшего дружественного оплота
      local t = KC.nearest_stronghold_of(fid, x, z, 80000, 0)
      if t then KC.S.danger[t] = (KC.S.danger[t] or 0) * 0.85; KC.gstat("patrols") end
    end
  elseif k == "convert" then
    local best, bp
    for _, o in ipairs(KC.near(fid, KC.P.bus.radius or 120000)) do
      local r = KC.rel(fid, o)
      if r > -30 and r < 40 and not KC.S.F[o].player and (not bp or KC.power(o) < bp) then best, bp = o, KC.power(o) end
    end
    if best then KC.add_rel(fid, best, 4); KC.add_trust(fid, best, 2); G.n = G.n + 1; KC.gstat("converts") end
  elseif k == "scavenge" or (k == "seize_camp" and next(KC.S.free or {}) == nil) then
    if not x then return end
    local bs, bd
    for sid, r in pairs(KC.S.ruins or {}) do
      local I = KC.SITE[sid]
      if r.scrap > 150 and I then
        local d = math.sqrt((I.x - x) ^ 2 + (I.z - z) ^ 2)
        if d <= KC.P.bus.radius and (not bd or d < bd) then bs, bd = sid, d end
      end
    end
    if bs and f.strength > 12 then KC.act(fid, "expedition", bs); G.n = G.n + 1 end
  end
  if f.goal and G.n >= G.need then KC.GL.finish(fid, f, true) end
end

-- шаг одной фракции
function KC.GL.step_faction(fid)
  local f = KC.S.F[fid]
  if not (f and f.alive and not f.player) then return end
  if f.goal and KC.DAY - f.goal.t0 > (KC.GP().goal_ttl or 100) then KC.GL.finish(fid, f, false) end
  if not f.goal then
    if f.goal_next and KC.DAY < f.goal_next then return end
    local k = KC.GL.pick(fid, f)
    if k then KC.GL.set_goal(fid, f, k) end
    return
  end
  if math.random() < (KC.GP().own_step_chance or 0.5) then KC.GL.own_step(fid, f) end
  if f.goal and f.goal.k ~= "survive" and f.goal.k ~= "revenge" and f.strength < 0.4 * f.strength0 and math.random() < 0.3 then   -- слабость сменяет цель на выживание
    KC.GL.finish(fid, f, false); KC.GL.set_goal(fid, f, "survive")
  end
end

-- оплоты ------------------------------------------------------------------------------------------------------
function KC.GL.step_stronghold(sid)
  local D = KC.GD()
  local I = KC.CFG.town_info[sid]
  local ow = KC.GL.own[sid]
  local d = KC.GL.danger(sid)
  local tw = KC.S.town[sid]
  if d >= (D.refuge_at or 1.2) and type(tw) == "table" and tw.pop and KC.DAY - (tw.refuge_day or -1000) >= (D.refuge_cooldown or 40) then
    local PP = KC.P.pop or {}
    local ms = PP.min_share or 0.25
    local got = 0
    for _, t in ipairs(KC.GL.tl) do
      local T, fw = KC.CFG.town_info[t], KC.S.town[t]
      if not T.sh and T.x and type(fw) == "table" and fw.pop and fw.pop0 then
        local dd = math.sqrt((T.x - I.x) ^ 2 + (T.z - I.z) ^ 2)
        if dd <= (D.feeder_radius or 40000) and fw.pop > fw.pop0 * (ms + 0.15) then
          local n = math.min(fw.pop - fw.pop0 * (ms + 0.1), fw.pop * (D.refuge_share or 0.05) * math.min(2, d))
          if n >= 1 and tw.pop + got + n <= tw.pop0 * (PP.cap or 1.3) * 1.3 then
            fw.pop = fw.pop - n
            local fo = KC.GL.own[t]
            local moved = false
            if KC.RDS.rd_on("refugees") and not KC.RDS.ROADS_OFF.relocate then
              moved = KC.RDS.rsafe("refuge", KC.RDS.rd_add, { k = "refugees", f = fo, from = t, to = sid, n = n, days = KC.RDS.rd_travel(t, sid, 0.5) }) and true or false
            end
            if not moved then got = got + n end
            if n >= 5 then
              KC.S.stats.refugees = (KC.S.stats.refugees or 0) + 1
              KC.emit({ type = "refugees", a = fo, town_sid = t, town_name = KC.TOWN_NAME[t] or t, n = math.floor(n), why = "danger", to = sid,
                     text = string.format("Families leave %s for the walls of %s.", KC.TOWN_NAME[t] or t, KC.TOWN_NAME[sid] or sid) })
            end
          end
        end
      end
    end
    tw.refuge_day = KC.DAY
    if got > 0 then tw.pop = tw.pop + got end
    KC.gstat("refuge_pulls")
  end
  if ow and d >= (D.hire_at or 1.8) then
    local O = KC.S.F[ow]
    if O and O.alive and O.wealth >= (D.hire_cost or 12) * 2 and KC.DAY - (KC.S.hire[sid] or -1000) >= (D.hire_cooldown or 40) then
      O.wealth = O.wealth - (D.hire_cost or 12)
      O.strength = O.strength + (D.hire_gain or 8)
      KC.S.hire[sid] = KC.DAY
      KC.S.danger[sid] = (KC.S.danger[sid] or 0) * 0.6
      KC.gstat("hires")
      KC.emit({ type = "stronghold_hire", a = ow, town_sid = sid, town_name = KC.TOWN_NAME[sid] or sid })
    end
  end
end

function KC.GL.refresh_shield()
  local sh = {}
  for _, t in ipairs(KC.GL.shl or {}) do
    local ow = KC.GL.own[t]
    if ow then
      local I = KC.CFG.town_info[t]
      sh[ow] = (sh[ow] or 0) + (I.sh or 1) * 0.67 + ((KC.S.hire[t] and KC.DAY - KC.S.hire[t] < 90) and 0.3 or 0)
    end
  end
  KC.S.shield = sh
end

-- очередь ------------------------------------------------------------------------------------------------------
function KC.GL.init()
  if KC.GL.shl then return end
  local l = {}
  for t, I in pairs(KC.CFG.town_info or {}) do if I.sh and I.x then l[#l + 1] = t end end
  table.sort(l)
  KC.GL.shl = l
  local all = {}
  for t in pairs(KC.CFG.town_info or {}) do all[#all + 1] = t end
  table.sort(all)
  KC.GL.tl = all   -- порядок обхода городов фиксирован (детерминизм)
  KC.GL.own = {}
end

function KC.GL.pump_one()
  local e = KC.GL.q[KC.GL.qi]
  KC.GL.qi = KC.GL.qi + 1
  if e[1] == "f" then KC.GL.step_faction(e[2]) else KC.GL.step_stronghold(e[2]) end
end

function KC.GL.pump_impl(n)
  if KC.GL.for_s ~= KC.S then return end   -- очередь чужого мира
  if not KC.GL.q or KC.GL.qi > #KC.GL.q then return end
  for _ = 1, n or KC.GP().chunk or 14 do
    if KC.GL.qi > #KC.GL.q then break end
    KC.GL.pump_one()
  end
end

function KC.GL.begin_impl()   -- из world_step: новая очередь (прежняя доделывается целиком, чтобы не терять записи)
  KC.GL.init()
  if KC.GL.for_s ~= KC.S then KC.GL.for_s, KC.GL.q, KC.GL.qi, KC.GL.own = KC.S, nil, 1, {} end   -- другой мир (reset/загрузка): очередь прежнего не переносим
  KC.GL.slots()
  while KC.GL.q and KC.GL.qi <= #KC.GL.q do KC.GL.pump_one() end
  KC.GL.own = {}
  for fid, f in pairs(KC.S.F) do if f.alive then for t in pairs(f.towns) do KC.GL.own[t] = fid end end end
  local D = KC.GD().decay or 0.8
  for t, v in pairs(KC.S.danger) do v = v * D; if v < 0.05 then KC.S.danger[t] = nil else KC.S.danger[t] = v end end
  KC.GL.refresh_shield()
  local q = {}
  for fid, f in pairs(KC.S.F) do if f.alive and not f.player and KC.garch(fid) then q[#q + 1] = { "f", fid } end end
  table.sort(q, function(a, b) return a[2] < b[2] end)
  for _, t in ipairs(KC.GL.shl) do q[#q + 1] = { "s", t } end
  KC.GL.q, KC.GL.qi = q, 1
end

function KC.GL.begin() if KC.GL.on() then KC.xsafe("goals_begin", KC.GL.begin_impl) end end
function KC.GL.pump(n) if KC.GL.on() and KC.GL.q then KC.xsafe("goals_pump", KC.GL.pump_impl, n) end end
function KC.GL.pending() return KC.GL.q and (#KC.GL.q - KC.GL.qi + 1) or 0 end

---------------------------------------------------------------------------------------------- WS: world_step фазами (бюджет KMM_Gov)
-- Тик мира (раз в tick_days) = список именованных фаз; из игры (on_tick -> advance(day, true)) фазы идут в очередь WSQ и исполняются по времени
-- (os.clock, WS.slice секунд за вызов, минимум одна фаза), как day_chunk склада; офлайн-тесты и симуляция зовут advance(day) без staged -
-- те же фазы выполняются сразу и целиком (поведение прежнее). Ход фаз: порядок world_step v1 сохранён. Очередь не пишется в сейв (потеря тика при загрузке допустима).
KC.WS = { q = {}, i = 1, slice = 0.0004, tmax = {}, timer = nil, calls = 0 }
function KC.ws_front(name, fn) table.insert(KC.WS.q, KC.WS.i, { name, fn }) end
function KC.acts_phase(order, from)   -- действия фракций порциями по ACT_CHUNK
  return function()
    local U = KC.P.utility
    local last = math.min(#order, from + ((KC.P.goals or {}).act_chunk or 24) - 1)
    for k = from, last do
      local fid = order[k]
      if KC.S.F[fid].alive and math.random() < U.act_chance * (KC.S.F[fid].succession and ((KC.P.succession or {}).act_mult or 0.4) or 1) then
        local a, o = KC.choose_action(fid)
        if a then KC.act(fid, a, o); KC.GL.note(fid, a, o) end
        KC.maybe_betrayal(fid)
      end
    end
    if last < #order then KC.ws_front("acts", KC.acts_phase(order, last + 1)) end
  end
end
function KC.ws_phases(day)
  local ph = {}
  local function add(name, fn) ph[#ph + 1] = { name, fn } end
  add("begin", function() KC.DAY = day; if not KC.S.free then KC.S.free = {} end; KC.GL.begin() end)   -- GOALS: очередь целей/оплотов на этот тик (порции в advance)
  add("stock_loop", KC.stock_loop)
  add("links2", function() KC.L2.step() end)
  add("town_pop", function() KC.town_step(KC.P.tick_days) end)
  add("famine", function() KC.RDS.famine_step() end)
  add("roads", function() KC.RDS.roads_step() end)
  add("economy", KC.economy)
  add("loot", KC.loot_step)
  add("ambush", function() KC.xsafe("ambush_expire", KC.ambush_expire) end)
  add("ore", KC.ore_step)
  add("know", function() KC.know_step(KC.P.tick_days) end)
  add("flows", KC.flows_step)
  add("unrest", KC.unrest_step)
  add("succession", KC.succession_step)
  add("shards", KC.shards_step)
  add("chaos", KC.chaos_step)
  add("free", KC.free_step)
  add("relic_modes", KC.relic_modes)
  add("treaties", KC.treaties_review)
  add("acts", function()
    local order = {}
    for fid, f in pairs(KC.S.F) do if f.alive and not f.player then order[#order + 1] = fid end end
    table.sort(order)
    for i = #order, 2, -1 do local j = math.random(i); order[i], order[j] = order[j], order[i] end
    KC.ws_front("acts", KC.acts_phase(order, 1))
  end)
  return ph
end
function KC.ws_run_one()
  local e = KC.WS.q[KC.WS.i]
  KC.WS.i = KC.WS.i + 1
  local t0 = KC.WS.timer and KC.WS.timer()
  e[2]()
  if t0 then local dt = KC.WS.timer() - t0; if dt > (KC.WS.tmax[e[1]] or 0) then KC.WS.tmax[e[1]] = dt end end
  if KC.WS.i > #KC.WS.q then KC.WS.q, KC.WS.i = {}, 1 end
end
function KC.ws_enqueue(day)
  if KC.WS.for_s ~= KC.S then KC.WS.for_s, KC.WS.q, KC.WS.i = KC.S, {}, 1 end   -- другой мир: очередь фаз прежнего не переносим
  for _, e in ipairs(KC.ws_phases(day)) do KC.WS.q[#KC.WS.q + 1] = e end
end
function KC.ws_pump(all)   -- all: выполнить всё сразу; иначе по времени, минимум одна фаза
  if KC.WS.for_s ~= KC.S then KC.WS.for_s, KC.WS.q, KC.WS.i = KC.S, {}, 1 end
  if #KC.WS.q == 0 then return end
  KC.WS.calls = KC.WS.calls + 1
  local c0 = os.clock()
  repeat
    KC.ws_run_one()
  local sl = (KC.P and tonumber(KC.P.ws_slice)) or (rawget(_G, "KMM_TEST") and 1e9) or KC.WS.slice   -- params.ws_slice (сек): офлайн-тесты ставят большое значение — детерминизм без зависимости от скорости CPU
  until #KC.WS.q == 0 or (not all and os.clock() - c0 >= sl)
end
function KC.world_step(day, staged)
  KC.ws_enqueue(day)
  if not staged then KC.ws_pump(true) end
end

function KC.major_event(day)   -- крупное событие раз в 30±10 дней: удар по паре «город — лидер» с весом по силе атакующего
  KC.DAY = day
  local pool, total = {}, 0
  for _, c in ipairs(KC.CFG.towns or {}) do
    if c.enabled and not KC.S.resolved[c.leader_sid] and not KC.S.pending[c.leader_sid] and KC.S.F[c.attacker_sid] and KC.S.F[c.attacker_sid].alive
       and KC.S.F[c.defender_sid] and KC.S.F[c.defender_sid].alive then
      local w = math.max(1, KC.power(c.attacker_sid)) ^ (KC.P.attacker_weight.exponent or 1)
      pool[#pool + 1] = { c = c, w = w }; total = total + w
    end
  end
  if #pool == 0 then return end
  local r, c = math.random() * total, pool[#pool].c
  for _, e in ipairs(pool) do r = r - e.w; if r <= 0 then c = e.c; break end end
  local sa, sd = KC.power(c.attacker_sid), KC.power(c.defender_sid)
  local p = KC.clamp(KC.P.outcome.base_success * (2 * sa / math.max(1, sa + sd)) ^ KC.P.outcome.strength_exponent, KC.P.outcome.min_success, KC.P.outcome.max_success)
  if math.random() < p then KC.leader_outcome(c.town_sid, c.attacker_sid, c.defender_sid)
  else
    KC.S.F[c.attacker_sid].strength = KC.S.F[c.attacker_sid].strength * 0.9
    KC.emit({ type = "attack_repelled", a = c.attacker_sid, b = c.defender_sid, town_sid = c.town_sid, town_name = c.town_name,
           text = string.format("%s attacked %s, but %s's people drove them off.", KC.name(c.attacker_sid), c.town_name, c.leader_name) })
  end
end

---------------------------------------------------------------------------------------------- LINKN: города -> настоящие варианты через KMM_Native
-- Когда владелец города в модели сменился (town_captured, revolt, town_rejoined, распад державы и т.п. - ловим сравнением владельцев раз в сутки и по событиям),
-- включаем в игре настоящий вариант города (override world state) через _G.KMM_Native.ws_set. Таблица вариантов - modules/kmm_ws_lut.lua
-- (tools/cpp/ws_town_lut.py), читается лениво при первой нужде. Вариант применяем, только если (1) он не рискованный, (2) все задетые им города модели
-- принадлежат ровно тем владельцам, которых даёт переключение, (3) условия «NPC мёртв/в плену» относятся к лидеру, которого дирижёр сам убил/пленил,
-- (4) нет конфликта с уже применёнными вариантами. Иначе событие ws_skip (раз на город/владельца/причину). Переопределения не пишутся в сейв:
-- после загрузки (смена S) - ws_clear_all и пересчёт по текущим владельцам. Возврат города исходному владельцу снимает переопределения по счётчику ссылок.
-- Нет плагина или available=false - ничего не делаем. Любая ошибка отключает только эту подсистему.
do
  local W = KC.WSL
  local ST = { changes = 0, applied = 0, applied_retry = 0, cleared = 0, skip = {}, no_variant = 0, native_fail = 0, syncs = 0, passes = 0 }
  local LUT, lut_tried
  local APPLIED, WSV, SEEN, SKIPPED, SKEY, STATUS = {}, {}, {}, {}, {}, {}
  local FOR_S, ACTIVE, OFF, RUNNING, KICK, LAST_DAY, TOWN_KEYS = nil, false, false, false, false, nil, nil

  local function native() return rawget(_G, "KMM_Native") end
  local function nat_ok()
    local n = native()
    if type(n) ~= "table" then return false end
    local ok, a = pcall(function() return n.available end)
    return ok and a == true
  end
  local function wlog(msg) pcall(function() _G.KMM_Conductor.guard_log(msg) end) end
  local function get_lut()
    if LUT then return LUT end
    if lut_tried then return nil end
    lut_tried = true
    local cands = {}
    if KC.P.ws and KC.P.ws.lut_path then cands[#cands + 1] = KC.P.ws.lut_path end
    if KC.ROOT then cands[#cands + 1] = KC.ROOT .. "/scripts/modules/kmm_ws_lut.lua" end
    cands[#cands + 1] = "C:/KenshiModMap/build/KMM_Conductor/scripts/modules/kmm_ws_lut.lua"
    for _, p in ipairs(cands) do
      local txt = KC.read_file(p)
      local LS = rawget(_G, "loadstring") or rawget(_G, "load")
      if txt and LS then
        local okc, f = pcall(LS, txt, "@kmm_ws_lut")
        if okc and f then
          setfenv(f, {})
          local ok, v = pcall(f)
          if ok and type(v) == "table" and v.v == 1 and type(v.T) == "table" and type(v.F) == "table" and type(v.W) == "table" then LUT = v; return v end
        end
      end
    end
    for _, mn in ipairs({ "kmm_ws_lut", "modules.kmm_ws_lut" }) do   -- 2026-11-13: loadstring в игре ограничен -> require
      local okr, v = pcall(require, mn)
      if okr and type(v) == "table" and v.v == 1 and type(v.T) == "table" and type(v.F) == "table" and type(v.W) == "table" then LUT = v; return v end
    end
    return nil
  end

  local function leader_fate(npc)   -- "k" убит, "c" пленён (по модели дирижёра), nil - жив
    local r = KC.S.resolved and KC.S.resolved[npc]
    if r == "leader_killed" then return "k" elseif r == "leader_captured" then return "c" end
    local id = KC.S.pending and KC.S.pending[npc]
    if id then
      for i = #KC.S.events, 1, -1 do
        local ev = KC.S.events[i]
        if ev.id == id then return ev.type == "leader_killed" and "k" or "c" end
      end
    end
    return nil
  end

  local function owner_map()
    local m = {}
    for fid, f in pairs(KC.S.F) do if f.alive then for t in pairs(f.towns) do m[t] = fid end end end
    return m
  end

  local function check(t, v, own)   -- true | false, причина
    if v.r then return false, "risky" end
    local mine = APPLIED[t] and APPLIED[t].ws
    local c = v.c
    for i = 1, #c, 2 do
      local sid, want = LUT.W[c[i]], (c[i + 1] == 1)
      local cur = WSV[sid]
      if cur and cur.want ~= want and (cur.n - ((mine and mine[sid] ~= nil) and 1 or 0)) > 0 then return false, "ws_conflict" end
    end
    local x = v.x
    if x then
      for i = 1, #x, 2 do
        if own[x[i]] ~= LUT.F[x[i + 1]] then return false, "other_town" end
      end
    end
    local d = v.d
    if d then
      for i = 1, #d, 2 do
        local fa = leader_fate(LUT.N[d[i]])
        if not fa or (d[i + 1] ~= "x" and fa ~= d[i + 1]) then return false, "risky_npc" end
      end
    end
    if v.a then
      for _, ni in ipairs(v.a) do if leader_fate(LUT.N[ni]) then return false, "dead_leader" end end
    end
    return true
  end

  local function eval(t, fid, own)   -- variant | nil, причина
    local list = LUT.T[t]
    if not list then return nil, "no_variant" end
    local why, any
    for _, v in ipairs(list) do
      if LUT.F[v.o] == fid then
        any = true
        local ok, w2 = check(t, v, own)
        if ok then return v end
        why = why or w2
      end
    end
    if not any then return nil, "no_variant" end
    return nil, why
  end

  local function release(t, why)
    local a = APPLIED[t]
    if not a then return end
    APPLIED[t] = nil
    local N = native()
    for sid in pairs(a.ws) do
      local e = WSV[sid]
      if e then
        e.n = e.n - 1
        if e.n <= 0 then WSV[sid] = nil; if N then pcall(N.ws_clear, sid) end end
      end
    end
    ST.cleared = ST.cleared + 1
    KC.emit({ type = "ws_cleared", town_sid = t, town_name = KC.TOWN_NAME[t] or t, owner = a.fid, reason = why })
  end

  local function apply(t, fid, v)   -- true | false
    local N = native()
    local set, fresh, n = {}, {}, 0
    local c = v.c
    for i = 1, #c, 2 do
      local sid, want = LUT.W[c[i]], (c[i + 1] == 1)
      local okset = N.ws_set(sid, want)
      if okset ~= true then
        for _, f in ipairs(fresh) do pcall(N.ws_clear, f) end
        ST.native_fail = ST.native_fail + 1
        if ST.native_fail >= 3 then OFF = true; wlog("ws link disabled until restart: ws_set failed 3 times") end
        return false
      end
      if not WSV[sid] then fresh[#fresh + 1] = sid end
      set[sid] = want; n = n + 1
    end
    for sid, want in pairs(set) do
      local e = WSV[sid]
      if not e then e = { want = want, n = 0 }; WSV[sid] = e end
      e.n = e.n + 1
    end
    APPLIED[t] = { fid = fid, ws = set, v = v }
    ST.applied = ST.applied + 1
    KC.emit({ type = "ws_applied", town_sid = t, town_name = KC.TOWN_NAME[t] or t, owner = fid, states = n })
    return true
  end

  local function skip(t, fid, why)
    STATUS[t] = why
    SKIPPED[t] = fid
    local key = t .. "|" .. tostring(fid) .. "|" .. why
    if SKEY[key] then return end
    SKEY[key] = true
    ST.skip[why] = (ST.skip[why] or 0) + 1
    KC.emit({ type = "ws_skip", town_sid = t, town_name = KC.TOWN_NAME[t] or t, owner = fid, reason = why })
  end

  local function pass()
    ST.passes = ST.passes + 1
    local own = owner_map()
    if not TOWN_KEYS then TOWN_KEYS = KC.sorted_keys(KC.CFG.town_info or {}) end
    local changed, todo = {}, {}
    for _, t in ipairs(TOWN_KEYS) do
      local k = own[t] or ((KC.S.free and KC.S.free[t]) and "~free" or "~none")
      if SEEN[t] ~= k then SEEN[t] = k; changed[t] = true; todo[t] = true end
    end
    for t in pairs(SKIPPED) do todo[t] = true end
    for t in pairs(APPLIED) do todo[t] = true end
    local list = KC.sorted_keys(todo)
    -- 1) снимаем то, что вернулось исходному владельцу / стало вольным / перестало быть безопасным
    local want_var = {}
    for _, t in ipairs(list) do
      local fid = own[t]
      local target = fid and fid ~= KC.ORIG_OWNER[t]
      local a = APPLIED[t]
      if not target then
        if a then release(t, fid and "returned" or "free") end
        SKIPPED[t] = nil; STATUS[t] = nil
      else
        if a and (a.fid ~= fid or not check(t, a.v, own)) then release(t, "revalidate") end
        want_var[#want_var + 1] = t
      end
    end
    -- 2) применяем
    for _, t in ipairs(want_var) do
      local fid = own[t]
      if changed[t] then ST.changes = ST.changes + 1 end
      if APPLIED[t] and APPLIED[t].fid == fid then
        STATUS[t] = "applied"
      else
        if not get_lut() then OFF = true; wlog("ws link disabled until restart: kmm_ws_lut.lua not readable"); return end
        local was_skipped = SKIPPED[t] ~= nil
        local v, why = eval(t, fid, own)
        if v then
          SKIPPED[t] = nil
          if apply(t, fid, v) then
            STATUS[t] = "applied"
            if was_skipped and not changed[t] then ST.applied_retry = ST.applied_retry + 1 end
          else skip(t, fid, "native_fail") end
        elseif why == "no_variant" then
          SKIPPED[t] = nil
          STATUS[t] = "no_variant"
          if changed[t] then ST.no_variant = ST.no_variant + 1 end
        else skip(t, fid, why) end
      end
    end
  end

  local function sync()   -- новая загрузка / новый мир: переопределения плагина не в сейве - сбрасываем и пересчитываем
    FOR_S = KC.S
    ST.syncs = ST.syncs + 1
    APPLIED, WSV, SEEN, SKIPPED, SKEY, STATUS = {}, {}, {}, {}, {}, {}
    ACTIVE = nat_ok()
    if not ACTIVE then return end
    pcall(native().ws_clear_all)
    for t in pairs(KC.CFG.town_info or {}) do SEEN[t] = KC.ORIG_OWNER[t] or "~none" end
    pass()
  end

  local function body()
    if not KC.S then return end
    if FOR_S ~= KC.S then KICK = false; LAST_DAY = math.floor(KC.S.last_day or 0); sync(); return end
    if not ACTIVE then KICK = false; return end
    local day = math.floor(KC.S.last_day or 0)
    if KICK or day ~= LAST_DAY then KICK = false; LAST_DAY = day; pass() end
  end

  local function run()
    if OFF or RUNNING or not (KC.S and KC.CFG and KC.CFG.town_info) then return end
    if KC.P.ws and KC.P.ws.enabled == false then return end
    RUNNING = true
    local ok, err = pcall(function()
      if rawget(_G, "KMM_Gov") then KMM_Gov.run("conductor_ws", body) else body() end
    end)
    RUNNING = false
    if not ok then
      OFF = true
      wlog("ws link disabled until restart: " .. tostring(err))
      pcall(function() local n = native(); if n then n.ws_clear_all() end end)
    end
  end

  W.on_event = function() KICK = true end   -- сама сверка - в конце advance (к этому времени leader_outcome уже записал S.pending)
  W.tick = function() run() end
  W.reset = function() FOR_S, LUT, lut_tried, OFF, KICK = nil, nil, nil, false, false end   -- офлайн-тест
  W.inject = function(t) LUT = t; lut_tried = true end
  W.stats = function()
    local out = {}
    for k, v in pairs(ST) do if k ~= "skip" then out[k] = v end end
    out.skip = {}
    for k, v in pairs(ST.skip) do out.skip[k] = v end
    out.active, out.off = ACTIVE and true or false, OFF and true or false
    local fin = {}
    for _, st in pairs(STATUS) do fin[st] = (fin[st] or 0) + 1 end
    out.final = fin
    local na, nw = 0, 0
    for _ in pairs(APPLIED) do na = na + 1 end
    for _ in pairs(WSV) do nw = nw + 1 end
    out.applied_now, out.ws_now = na, nw
    return out
  end
  W.applied = function() local o = {}; for t, a in pairs(APPLIED) do o[t] = a.fid end; return o end
end

function KC.ensure_slots(s)   -- старое состояние (до складов/города) получает пустые слоты при загрузке
  if type(s.stock) ~= "table" then s.stock = {} end
  if type(s.town) ~= "table" then s.town = {} end
  if type(s.loot) ~= "table" then s.loot = {} end
  if type(s.ambush) ~= "table" then s.ambush = {} end
  if type(s.l2) ~= "table" then s.l2 = {} end
  if type(s.roads) ~= "table" then s.roads = {} end
  for _, k in ipairs({ "danger", "founded", "hire", "shield" }) do if type(s[k]) ~= "table" then s[k] = {} end end   -- GOALS
end
end
if KC._BOOT then KC._BOOT() end
