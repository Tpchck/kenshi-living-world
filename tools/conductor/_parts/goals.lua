---------------------------------------------------------------------------------------------- GOALS: цели фракций и роль оплотов (2026-11-13)
-- Каждая сознательная фракция (архетип: bandit/savage/trader/religion/settler/state/robot/imperium/chaos/xeno) держит ЦЕЛЬ f.goal = { k, n, need, t0 }.
-- Цель выбирается по архетипу и состоянию мира (голод/нужда, слабость, месть, акт сюжета) и смещает utility действий (GL.mult в choose_action);
-- progress растёт от реальных действий (GL.note после act) и собственных шагов (GL.own_step: паломничество, маршрут торговца, основание, патруль...).
-- Оплот (town_info.sh) = безопасность + рынок + убежище: опасность вокруг (S.danger, события шины) -> беженцы и караваны тянутся к оплоту,
-- владелец нанимает охрану (strength за wealth, Traces: гарнизон), бандиты/дикари обходят сильные оплоты (S.shield) и бьют слабых.
-- Работа порциями (по образцу day_chunk склада): GL.begin() в world_step строит очередь, GL.pump(n) в advance обрабатывает n записей за вызов.
-- Всё под xsafe/pcall: первая ошибка отключает блок до перезапуска (цели -> нейтральные множители 1.0).
GL.GOALSET = {
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
GL.NEED = { loot_roads = 3, racket = 2, seize_camp = 1, hunt_travelers = 3, defend_lands = 2, trade_route = 3, pilgrimage = 2, crusade = 2, convert = 3,
            found = 1, grow = 3, patrol = 3, scavenge = 2, hunt = 2, spread = 2, survive = 2, revenge = 1 }
GL.ACTS = {   -- какие act() засчитываются целью
  loot_roads = { waylay = 1, raid_surplus = 1, raid = 1 }, racket = { raid = 1, waylay = 1 }, seize_camp = { capture_free = 1, expedition = 1, capture = 1 },
  hunt_travelers = { waylay = 1 }, defend_lands = { hide = 1, recruit = 1, raid = 1 }, trade_route = { trade = 1, trade_for = 1 },
  pilgrimage = { alliance = 1 }, crusade = { raid = 1, capture = 1 }, convert = { alliance = 1, trade = 1 }, found = { capture_free = 1 }, grow = { recruit = 1, trade = 1 },
  patrol = { recruit = 1, raid = 1, alliance = 1 }, scavenge = { expedition = 1, raid_surplus = 1 }, hunt = { raid = 1, capture = 1 }, spread = { raid = 1, capture = 1, waylay = 1 },
  survive = { hide = 1, recruit = 1, alliance = 1 }, revenge = { raid = 1, waylay = 1, capture = 1 },
}
local function GP() return (P and P.goals) or {} end
local function GD() return GP().danger or {} end
local function garch(fid) local c = CFG.factions[fid]; return c and c.arch end
local function gstat(k, n) S.stats[k] = (S.stats[k] or 0) + (n or 1) end
GL.arch = garch

function GL.slots()
  S.danger = S.danger or {}; S.founded = S.founded or {}; S.hire = S.hire or {}; S.shield = S.shield or {}
end

function GL.on() return GL.off ~= true and GP().enabled ~= false end

-- множитель utility действия a (цель + щит оплотов); вызывается из consider() в choose_action
function GL.mult_impl(fid, f, a, o)
  local m = 1
  local G = f.goal
  if G then
    local b = (GP().bias or {})[G.k]
    local v = b and b[a]
    if v then
      if f.townless or ncities(f) == 0 then m = v else m = 1 + (v - 1) * (GP().city_bias_mult or 0.5) end
    end
  end
  if o and S.shield and (a == "raid" or a == "capture" or a == "waylay" or a == "raid_surplus") then
    local ar = garch(fid)
    if ar == "bandit" or ar == "savage" then
      local O = S.F[o]
      local sd = S.shield[o]
      local SH = GP().shield or {}
      if sd and sd > 0 then m = m / (1 + (SH.per_stronghold or 0.35) * sd)
      elseif O and O.strength < (SH.weak_ratio or 0.6) * f.strength then m = m * (SH.weak_boost or 1.3) end
    end
  end
  return m
end
function GL.mult(fid, f, a, o)
  if GL.off or GP().enabled == false then return 1 end
  local ok, m = pcall(GL.mult_impl, fid, f, a, o)
  if ok and type(m) == "number" then return m end
  GL.off = true
  pcall(function() _G.KMM_Conductor.guard_log("goals disabled until restart: " .. tostring(m)) end)
  return 1
end

-- шина -> опасность вокруг оплотов
function GL.hook_impl(ev)
  if not S.danger then return end
  local D = GD()
  local w = D[ev.type]
  if type(w) ~= "number" then return end
  local R = D.radius or 60000
  local sid = ev.town_sid
  local I = sid and CFG.town_info[sid]
  if I and I.sh then S.danger[sid] = (S.danger[sid] or 0) + w; return end
  if I and I.x then
    local best, bd
    for _, t in ipairs(GL.shl or {}) do
      local T = CFG.town_info[t]
      local d = math.sqrt((T.x - I.x) ^ 2 + (T.z - I.z) ^ 2)
      if d <= R and (not bd or d < bd) then best, bd = t, d end
    end
    if best then S.danger[best] = (S.danger[best] or 0) + w * (1 - bd / R) end
    return
  end
  local b = ev.b and S.F[ev.b]
  if b then for t in pairs(b.towns) do local T = CFG.town_info[t]; if T and T.sh then S.danger[t] = (S.danger[t] or 0) + w * 0.5 end end end
end
function GL.hook(ev) if not GL.off and GL.on() then xsafe("goals_hook", GL.hook_impl, ev) end end

function GL.danger(sid)
  local d = S.danger[sid] or 0
  local ab = (GD().act_base or {})[(S.story and S.story.act) or ""]
  return d + (ab or 0)
end

-- выбор цели --------------------------------------------------------------------------------------------------
function GL.pick(fid, f)
  local ar = garch(fid)
  local set = GL.GOALSET[ar]
  if not set then return nil end
  local act = S.story and S.story.act
  local need = (f.hunger or 0) > 0.3 or f.wealth < 0.5 * f.wealth0 or (f.food_def or 0) > 0.15
  local weak = f.strength < 0.6 * f.strength0 or (f.low_until and DAY < f.low_until)
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
    if k == "found" and (f.founded or 0) >= (GP().found_max or 3) then w = 0 end
    add(k, w)
  end
  local rv = 0
  for _, d0 in pairs(f.wronged or {}) do if DAY - d0 < 90 then rv = rv + 1 end end
  if rv > 0 and not weak then add("revenge", 1.5 * math.min(2, rv)) end
  if tot <= 0 then return nil end
  local r, acc = math.random() * tot, 0
  for _, o in ipairs(opts) do acc = acc + o[2]; if r <= acc then return o[1] end end
  return opts[#opts][1]
end

function GL.set_goal(fid, f, k)
  f.goal = { k = k, n = 0, need = GL.NEED[k] or 2, t0 = DAY }
  gstat("goal_set")
end

-- результат
function GL.finish(fid, f, ok)
  local G = f.goal
  if not G then return end
  local Gp = GP()
  f.goal, f.goal_next = nil, DAY + (Gp.goal_gap or 6)
  if ok then
    f.goals_done = (f.goals_done or 0) + 1
    f.wealth = f.wealth + (Gp.reward_wealth or 14)
    f.strength = f.strength + (Gp.reward_strength or 4)
    gstat("goals_done"); gstat("goals_done_" .. (garch(fid) or "?"))
    local c = CFG.factions[fid]
    if c and c.townless then gstat("goals_done_townless") end
    if f.goals_done == 1 or f.goals_done % 10 == 0 then
      emit({ type = "goal_milestone", a = fid, goal = G.k, n = f.goals_done, text = string.format("%s have seen their aim through (%s); more follow.", name(fid), G.k) })
    else
      emit({ type = "goal_done", a = fid, goal = G.k, n = f.goals_done })
    end
  else
    f.goals_failed = (f.goals_failed or 0) + 1
    gstat("goals_failed")
  end
end

function GL.note(fid, a, o)
  if GL.off or not GL.on() then return end
  local f = S.F[fid]
  local G = f and f.goal
  if not G then return end
  local acts = GL.ACTS[G.k]
  if not (acts and acts[a]) then return end
  if G.k == "revenge" and not (o and f.wronged and f.wronged[o] and DAY - f.wronged[o] < 90) then return end
  G.n = G.n + 1
  if G.n >= G.need then GL.finish(fid, f, true) end
end

-- собственные шаги (цели без естественного действия) ------------------------------------------------------------
local function nearest_stronghold_of(fid, x, z, maxd, relmin)   -- ближайший оплот чужого владельца (rel >= relmin); -> sid, owner, d
  local best, bo, bd
  for _, t in ipairs(GL.shl or {}) do
    local T = CFG.town_info[t]
    local ow = GL.own[t]
    if ow and ow ~= fid and S.F[ow] and S.F[ow].alive and rel(fid, ow) >= relmin then
      local d = math.sqrt((T.x - x) ^ 2 + (T.z - z) ^ 2)
      if d <= maxd and (not bd or d < bd) then best, bo, bd = t, ow, d end
    end
  end
  return best, bo, bd
end

function GL.own_step(fid, f)
  local G = f.goal
  if not G then return end
  local Gp = GP()
  local x, z = FPOS(fid)
  local k = G.k
  if k == "pilgrimage" then
    if not x or f.wealth < (Gp.pilgrim_cost or 3) then return end
    local t, ow = nearest_stronghold_of(fid, x, z, 120000, 15)
    if not t then return end
    f.wealth = f.wealth - (Gp.pilgrim_cost or 3)
    add_rel(fid, ow, 2)
    G.n = G.n + 1
    gstat("pilgrimages")
    emit({ type = "pilgrimage", a = fid, b = ow, town_sid = t, town_name = TOWN_NAME[t] or t })
  elseif k == "trade_route" then
    local best, bd = nil, 0
    for _, t in ipairs(GL.shl or {}) do   -- пункт назначения: оплот с наибольшей опасностью/нуждой (убежище нуждается в припасах)
      local ow = GL.own[t]
      if ow and ow ~= fid and S.F[ow] and S.F[ow].alive and rel(fid, ow) >= -20 then
        local lf = tlv(t, "food") or 1
        local need = GL.danger(t) + math.max(0, 1 - lf) * 2 + math.random() * 0.4
        if need > bd then best, bd = t, need end
      end
    end
    if not best then return end
    local B = GL.own[best]
    local from, cat
    for _, t in ipairs(GL.shl or {}) do
      local ow = GL.own[t]
      if ow and ow ~= B and ow ~= fid and S.F[ow].alive and rel(fid, ow) >= -20 and rel(ow, B) > -60 then
        for _, c in ipairs({ "food", "metal", "med" }) do
          if (tlv(t, c) or 0) > 1.15 and (tlv(best, c) or 9) < 1.0 then from, cat = ow, c; break end
        end
        if from then break end
      end
    end
    if not from then
      G.n = G.n + 0.34   -- пустой рейс: хоть что-то везли (цель идёт медленнее)
    else
      local moved = ship(from, B, cat, Gp.route_share or 0.35)
      if moved > 0 then
        f.wealth = f.wealth + math.min(12, moved * 0.06) + 1
        G.n = G.n + 1
        gstat("routes"); gstat("routes_moved", moved)
        emit({ type = "trade_route", a = fid, b = B, town_sid = best, town_name = TOWN_NAME[best] or best, cat = cat, n = math.floor(moved) })
      end
    end
  elseif k == "found" then
    if not x or f.wealth < (Gp.found_cost or 40) or (f.founded or 0) >= (Gp.found_max or 3) then return end
    local bs, bd
    for _, st in ipairs(CFG.sites or {}) do
      if not S.founded[st.sid] then
        local d = math.sqrt((st.x - x) ^ 2 + (st.z - z) ^ 2)
        if d <= 60000 and (not bd or d < bd) then bs, bd = st, d end
      end
    end
    if not bs then return end
    S.founded[bs.sid] = fid
    f.founded = (f.founded or 0) + 1
    f.wealth = f.wealth - (Gp.found_cost or 40)
    f.strength = f.strength + 6
    G.n = G.n + 1
    gstat("founded")
    emit({ type = "settlement_founded", a = fid, town_sid = bs.sid, town_name = bs.name,
           text = string.format("%s raised a new settlement among the ruins of %s.", name(fid), bs.name or "the old world") })
  elseif k == "grow" then
    if f.wealth >= 20 then f.wealth = f.wealth - 6; f.strength = f.strength + 2; G.n = G.n + 1 end
  elseif k == "patrol" then
    if f.wealth < 5 then return end
    f.wealth = f.wealth - 3; f.strength = f.strength + 1
    G.n = G.n + 1
    if x then   -- патруль гасит опасность у ближайшего дружественного оплота
      local t = nearest_stronghold_of(fid, x, z, 80000, 0)
      if t then S.danger[t] = (S.danger[t] or 0) * 0.85; gstat("patrols") end
    end
  elseif k == "convert" then
    local best, bp
    for _, o in ipairs(near(fid, P.bus.radius or 120000)) do
      local r = rel(fid, o)
      if r > -30 and r < 40 and not S.F[o].player and (not bp or power(o) < bp) then best, bp = o, power(o) end
    end
    if best then add_rel(fid, best, 4); add_trust(fid, best, 2); G.n = G.n + 1; gstat("converts") end
  elseif k == "scavenge" or (k == "seize_camp" and next(S.free or {}) == nil) then
    if not x then return end
    local bs, bd
    for sid, r in pairs(S.ruins or {}) do
      local I = SITE[sid]
      if r.scrap > 150 and I then
        local d = math.sqrt((I.x - x) ^ 2 + (I.z - z) ^ 2)
        if d <= P.bus.radius and (not bd or d < bd) then bs, bd = sid, d end
      end
    end
    if bs and f.strength > 12 then act(fid, "expedition", bs); G.n = G.n + 1 end
  end
  if f.goal and G.n >= G.need then GL.finish(fid, f, true) end
end

-- шаг одной фракции
function GL.step_faction(fid)
  local f = S.F[fid]
  if not (f and f.alive and not f.player) then return end
  if f.goal and DAY - f.goal.t0 > (GP().goal_ttl or 100) then GL.finish(fid, f, false) end
  if not f.goal then
    if f.goal_next and DAY < f.goal_next then return end
    local k = GL.pick(fid, f)
    if k then GL.set_goal(fid, f, k) end
    return
  end
  if math.random() < (GP().own_step_chance or 0.5) then GL.own_step(fid, f) end
  if f.goal and f.goal.k ~= "survive" and f.goal.k ~= "revenge" and f.strength < 0.4 * f.strength0 and math.random() < 0.3 then   -- слабость сменяет цель на выживание
    GL.finish(fid, f, false); GL.set_goal(fid, f, "survive")
  end
end

-- оплоты ------------------------------------------------------------------------------------------------------
function GL.step_stronghold(sid)
  local D = GD()
  local I = CFG.town_info[sid]
  local ow = GL.own[sid]
  local d = GL.danger(sid)
  local tw = S.town[sid]
  if d >= (D.refuge_at or 1.2) and type(tw) == "table" and tw.pop and DAY - (tw.refuge_day or -1000) >= (D.refuge_cooldown or 40) then
    local PP = P.pop or {}
    local ms = PP.min_share or 0.25
    local got = 0
    for t, T in pairs(CFG.town_info) do
      local fw = S.town[t]
      if not T.sh and T.x and type(fw) == "table" and fw.pop and fw.pop0 then
        local dd = math.sqrt((T.x - I.x) ^ 2 + (T.z - I.z) ^ 2)
        if dd <= (D.feeder_radius or 40000) and fw.pop > fw.pop0 * (ms + 0.15) then
          local n = math.min(fw.pop - fw.pop0 * (ms + 0.1), fw.pop * (D.refuge_share or 0.05) * math.min(2, d))
          if n >= 1 and tw.pop + got + n <= tw.pop0 * (PP.cap or 1.3) * 1.3 then
            fw.pop = fw.pop - n
            local fo = GL.own[t]
            local moved = false
            if RDS.rd_on("refugees") and not RDS.ROADS_OFF.relocate then
              moved = RDS.rsafe("refuge", RDS.rd_add, { k = "refugees", f = fo, from = t, to = sid, n = n, days = RDS.rd_travel(t, sid, 0.5) }) and true or false
            end
            if not moved then got = got + n end
            if n >= 5 then
              S.stats.refugees = (S.stats.refugees or 0) + 1
              emit({ type = "refugees", a = fo, town_sid = t, town_name = TOWN_NAME[t] or t, n = math.floor(n), why = "danger", to = sid,
                     text = string.format("Families leave %s for the walls of %s.", TOWN_NAME[t] or t, TOWN_NAME[sid] or sid) })
            end
          end
        end
      end
    end
    tw.refuge_day = DAY
    if got > 0 then tw.pop = tw.pop + got end
    gstat("refuge_pulls")
  end
  if ow and d >= (D.hire_at or 1.8) then
    local O = S.F[ow]
    if O and O.alive and O.wealth >= (D.hire_cost or 12) * 2 and DAY - (S.hire[sid] or -1000) >= (D.hire_cooldown or 40) then
      O.wealth = O.wealth - (D.hire_cost or 12)
      O.strength = O.strength + (D.hire_gain or 8)
      S.hire[sid] = DAY
      S.danger[sid] = (S.danger[sid] or 0) * 0.6
      gstat("hires")
      emit({ type = "stronghold_hire", a = ow, town_sid = sid, town_name = TOWN_NAME[sid] or sid })
    end
  end
end

function GL.refresh_shield()
  local sh = {}
  for _, t in ipairs(GL.shl or {}) do
    local ow = GL.own[t]
    if ow then
      local I = CFG.town_info[t]
      sh[ow] = (sh[ow] or 0) + (I.sh or 1) * 0.67 + ((S.hire[t] and DAY - S.hire[t] < 90) and 0.3 or 0)
    end
  end
  S.shield = sh
end

-- очередь ------------------------------------------------------------------------------------------------------
function GL.init()
  if GL.shl then return end
  local l = {}
  for t, I in pairs(CFG.town_info or {}) do if I.sh and I.x then l[#l + 1] = t end end
  table.sort(l)
  GL.shl = l
  GL.own = {}
end

function GL.pump_one()
  local e = GL.q[GL.qi]
  GL.qi = GL.qi + 1
  if e[1] == "f" then GL.step_faction(e[2]) else GL.step_stronghold(e[2]) end
end

function GL.pump_impl(n)
  if not GL.q or GL.qi > #GL.q then return end
  for _ = 1, n or GP().chunk or 14 do
    if GL.qi > #GL.q then break end
    GL.pump_one()
  end
end

function GL.begin_impl()   -- из world_step: новая очередь (прежняя доделывается целиком, чтобы не терять записи)
  GL.init()
  GL.slots()
  while GL.q and GL.qi <= #GL.q do GL.pump_one() end
  GL.own = {}
  for fid, f in pairs(S.F) do if f.alive then for t in pairs(f.towns) do GL.own[t] = fid end end end
  local D = GD().decay or 0.8
  for t, v in pairs(S.danger) do v = v * D; if v < 0.05 then S.danger[t] = nil else S.danger[t] = v end end
  GL.refresh_shield()
  local q = {}
  for fid, f in pairs(S.F) do if f.alive and not f.player and garch(fid) then q[#q + 1] = { "f", fid } end end
  table.sort(q, function(a, b) return a[2] < b[2] end)
  for _, t in ipairs(GL.shl) do q[#q + 1] = { "s", t } end
  GL.q, GL.qi = q, 1
end

function GL.begin() if GL.on() then xsafe("goals_begin", GL.begin_impl) end end
function GL.pump(n) if GL.on() and GL.q then xsafe("goals_pump", GL.pump_impl, n) end end
function GL.pending() return GL.q and (#GL.q - GL.qi + 1) or 0 end
