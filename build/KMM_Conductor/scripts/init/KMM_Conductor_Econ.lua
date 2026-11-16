-- KMM_Conductor_Econ: part of KMM_Conductor (world conductor), run by KC._BOOT in KMM_Conductor.lua
-- Часть дирижёра мира (KMM_Conductor.lua собирает части и регистрирует события). 1-я строка ASCII: имя чанка в тестах.
-- Здесь: CORE-петля склад -> дирижёр, население и знание, ROADS (путники, перенос чисел), ROBBERY (засады, сбыт добычи),
-- реакции на события, LINKS2 (связки механик), выбор и исполнение действий фракций (choose_action/act).
-- Код части выполняется не при загрузке файла, а в KC._BOOT() в порядке KC._PARTS (как шёл бы единый файл),
-- когда загружены все части — порядок загрузки файлов KenshiLua не важен.
local KC = rawget(_G, "KMM_C_INT")   -- общее пространство имён частей дирижёра (бывшие локали главного чанка: KC.<имя>)
if type(KC) ~= "table" then KC = { _SEG = {} }; _G.KMM_C_INT = KC end
if KC._booted then KC._SEG, KC._booted = {}, false end   -- повторная загрузка скриптов: собрать части заново
KC._SEG.Econ = function()
---------------------------------------------------------------------------------------------- CORE: петля склад->дирижёр, население, знание, события игрока
-- Каждая функция в xsafe: первая ошибка отключает только её (причина -> debug.log). Состояние - в S (F[fid].know/lvl/..., S.town[sid].pop, S.forge).
KC.XDIS = {}
function KC.sorted_keys(t) local k = {}; for x in pairs(t) do k[#k + 1] = x end; table.sort(k); return k end
function KC.xsafe(nm, fn, ...)   -- HEALTH: отказ -> пауза реестра (KMM_Conductor.<nm>), повтор
  if KC.GL.h_live(KC.XDIS, nm) then return end
  local ok, err = pcall(fn, ...)
  if not ok then KC.GL.h_bad(KC.XDIS, nm, "KMM_Conductor." .. nm, err, nm)
  else KC.GL.h_done(KC.XDIS, nm) end
end
function KC.tlv(sid, c)   -- уровень склада города: доля нормы (пишет модель STOCK в s.lv раз в день)
  local st = KC.S.stock and KC.S.stock.towns and KC.S.stock.towns[sid]
  local lv = st and st.lv
  return lv and lv[c] or nil
end
function KC.owner_of(sid)
  for fid, f in pairs(KC.S.F) do if f.alive and f.towns[sid] then return fid end end
  return nil
end

function KC.stock_loop_impl()   -- раз в тик: дефицит еды/металла по городам фракции (вес: город 1, владение 0.35)
  local L = KC.P.loop or {}
  if not (KC.S.stock and KC.S.stock.towns) then return end
  local th = L.def_below or 0.6
  for fid, f in pairs(KC.S.F) do
    if f.alive and not f.player then
      local sw, sf, sm, lf, lm, la, lw = 0, 0, 0, 0, 0, 0, 0
      for t in pairs(f.towns) do
        local lv = KC.tlv(t, "food")
        if lv then
          local w = KC.is_city(t) and 1 or 0.35
          local lvm = KC.tlv(t, "metal") or 1
          sw = sw + w; lf = lf + w * lv; lm = lm + w * lvm
          la = la + w * (KC.tlv(t, "armor") or 1); lw = lw + w * (KC.tlv(t, "weapons") or 1)
          sf = sf + w * KC.clamp((th - lv) / th, 0, 1); sm = sm + w * KC.clamp((th - lvm) / th, 0, 1)
        end
      end
      if sw > 0 then f.lvl = { food = lf / sw, metal = lm / sw, armor = la / sw, weapons = lw / sw }; f.food_def, f.metal_def = sf / sw, sm / sw
      else f.lvl = nil; f.food_def, f.metal_def = 0, 0 end
      -- снаряжение патрулей: дефицит брони/оружия на складах → ярус вниз на 1 (гистерезис), избыток выше обычного не поднимает
      local G = KC.P.contra or {}
      local gl = f.lvl and (0.5 * f.lvl.armor + 0.5 * f.lvl.weapons) or nil
      if gl then
        if (f.gear_shift or 0) == 0 and gl < (G.gear_lo or 0.4) and KC.DAY >= (f.gear_grace or 0) then
          f.gear_shift = -1
          if KC.DAY - (f.gear_told or -1000) >= (G.gear_cooldown or 90) then
            f.gear_told = KC.DAY
            local cap = KC.capital(fid)
            KC.emit({ type = "gear_worn", a = fid, town_sid = cap, town_name = cap and KC.TOWN_NAME[cap] or nil,
                   text = string.format("The patrols of %s go about in rusted gear; the armouries run dry.", KC.name(fid)) })
          end
        elseif (f.gear_shift or 0) < 0 and gl > (G.gear_hi or 0.65) then f.gear_shift = 0 end
      end
    end
  end
end
function KC.stock_loop() KC.xsafe("stock_loop", KC.stock_loop_impl) end

---------------------------------------------------------------------------------------------- ROADS: путники, перенос чисел, память дорог игрока
-- Каждый встречный идёт откуда-то куда-то по причине из мира. Журнал дорог S.roads.tr (<= max_transit записей): то, что списано в источнике и ещё не зачтено
-- в пункте назначения (беженцы - население, караван - груз склада, бродяга - монеты). Зачёт - когда Traces видит прибытие (road_arrive) или абстрактно по сроку
-- (roads_step в world_step): ничего не создаётся из воздуха, сумма сохраняется (кроме погибших в пути). Сетка присутствия игрока S.roads.grid - клетки cell x cell,
-- вес затухает с полураспадом half_days, хранится <= grid_max клеток. Всё под rsafe: ошибка отключает только свою функцию (причина -> debug.log).
KC.RDS = {}
do
local ROADS_OFF = {}
local function RD() return (KC.P and KC.P.roads) or {} end
local function rd_on(k) local R = RD(); return R.enabled ~= false and (k == nil or R[k] ~= false) end
local function rsafe(nm, fn, ...)
  if KC.GL.h_live(ROADS_OFF, nm) then return nil end
  local ok, a, b = pcall(fn, ...)
  if not ok then KC.GL.h_bad(ROADS_OFF, nm, "KMM_Conductor.roads_" .. nm, a, "roads " .. nm); return nil end
  KC.GL.h_done(ROADS_OFF, nm)
  return a, b
end
local function rd_slot()
  if type(KC.S.roads) ~= "table" then KC.S.roads = {} end
  local r = KC.S.roads
  if type(r.tr) ~= "table" then r.tr = {} end
  if type(r.grid) ~= "table" then r.grid = {} end
  if type(r.cd) ~= "table" then r.cd = {} end
  if type(r.st) ~= "table" then r.st = {} end
  r.nid = r.nid or 1
  return r
end
local function rd_stat(k, n) local r = rd_slot(); r.st[k] = (r.st[k] or 0) + (n or 1) end
local function rdist(ax, az, bx, bz) return math.sqrt((ax - bx) ^ 2 + (az - bz) ^ 2) end
local function tpos(sid) local i = KC.CFG.town_info and KC.CFG.town_info[sid]; if i and i.x then return i.x, i.z end end
local ROAD_CATS = { "food", "metal", "weapons", "armor", "med" }   -- законные грузы караванов (наркотики/роскошь/скрап - контрабанда, не здесь)
local function rd_travel(a, b, mult)   -- игровые дни пути между городами
  local d = (a and b) and KC.town_dist(a, b) or 8000
  return KC.clamp(d / ((RD().speed or 8000) * (mult or 1)), 0.5, 12)
end
local function rd_owner_map()
  local own = {}
  for fid, f in pairs(KC.S.F) do if f.alive then for t in pairs(f.towns) do own[t] = fid end end end
  return own
end
local function rd_stock(sid) local st = KC.S.stock and KC.S.stock.towns and KC.S.stock.towns[sid]; if st and st.q and st.tn then return st end end
local function rd_credit(e)   -- зачесть груз в пункте назначения; возвращает принятое количество
  if (e.n or 0) <= 0 then return 0 end
  if e.k == "refugees" then
    local tw = KC.S.town and KC.S.town[e.to]
    if type(tw) ~= "table" or not tw.pop then return 0 end
    local room = math.max(0, tw.pop0 * (RD().pop_room or 1.4) - tw.pop)
    local x = math.min(e.n, room)
    tw.pop = tw.pop + x
    return x
  elseif e.k == "caravan" then
    local s = rd_stock(e.to)
    if not (s and s.tn[e.c]) then return 0 end
    s.q[e.c] = (s.q[e.c] or 0) + e.n; s.lv = s.lv or {}; s.lv[e.c] = s.q[e.c] / s.tn[e.c]
    return e.n
  elseif e.k == "wanderer" then
    local o = KC.owner_of(e.to)
    local f = (o and KC.S.F[o]) or KC.S.F[e.f]   -- нет хозяина у города: деньги возвращаются в кошелёк странника
    if f then f.wealth = f.wealth + e.n; return e.n end
  end
  return 0
end
local function rd_arrive(id, how)
  local r = rd_slot()
  local e = r.tr[id]
  if not e then return false end
  r.tr[id] = nil
  local got = rd_credit(e)
  rd_stat("arrived_" .. e.k); rd_stat("arrived_n", got)
  if how == "visible" then rd_stat("arrived_visible") end
  if e.vis or how == "visible" then
    KC.emit({ type = "traveler_arrived", a = e.f, fid = e.f, kind = e.k, from = e.from, to = e.to, n = got, how = how or "abstract" })
  end
  return true
end
local function rd_add(e)
  local r = rd_slot()
  e.id = r.nid; r.nid = r.nid + 1
  e.d0 = KC.DAY
  e.eta = KC.DAY + (e.days or rd_travel(e.from, e.to))
  e.days = nil
  r.tr[e.id] = e
  local n, old = 0, nil
  for id, x in pairs(r.tr) do n = n + 1; if id ~= e.id and (not old or x.d0 < old.d0) then old = x end end
  if n > (RD().max_transit or 40) and old then rd_arrive(old.id, "cap") end
  return e
end
local function roads_step_impl()
  local r = rd_slot()
  local grace = RD().vis_grace_days or 2
  for id, e in pairs(r.tr) do
    if KC.DAY >= e.eta + (e.vis and grace or 0) then rd_arrive(id, "abstract") end
  end
  for k, d in pairs(r.cd) do if d < KC.DAY - 60 then r.cd[k] = nil end end
end
local function roads_step() rsafe("step", roads_step_impl) end
-- беженцам города sid: ближайший сытый город (еда >= 0.8 нормы, население < 1.3 нормы)
local function rd_fed_town(sid, x, z)
  local best, bd
  for t, I in pairs(KC.CFG.town_info or {}) do
    local tw = KC.S.town and KC.S.town[t]
    if t ~= sid and I.x and type(tw) == "table" and tw.pop and tw.pop0 and (KC.tlv(t, "food") or 0) >= 0.8 and tw.pop < tw.pop0 * 1.3 then
      local d = (sid and KC.town_dist(sid, t)) or ((x and rdist(x, z, I.x, I.z)) or 0)
      if not bd or d < bd then best, bd = t, d end
    end
  end
  return best
end
local function rd_wanderer_ok(fid)
  local f, c = KC.S.F[fid], KC.CFG.factions[fid]
  if not (f and c and f.alive and not f.player and not f.relic) then return false end
  if KC.ntowns(f) == 0 then return true end
  for _, x in ipairs((KC.CFG.roles or {}).thieves or {}) do if x == fid then return true end end
  return false
end
local function rd_courier_cd(key, days)
  local r = rd_slot()
  if (r.cd[key] or -1) > KC.DAY then return false end
  r.cd[key] = KC.DAY + days
  return true
end
-- план пути: { kind, fid, from, to, owner (хозяин города назначения), c, n, why }; nil - причины идти нет
local function road_plan_impl(kind, fid, o)
  o = o or {}
  if kind == "refugees" then
    local to = rd_fed_town(o.from, o.x, o.z)
    if not to then return nil end
    return { kind = "refugees", fid = fid, from = o.from, to = to, owner = KC.owner_of(to), n = 0, why = "refuge" }
  elseif kind == "caravan" then
    local st = KC.S.stock and KC.S.stock.towns
    if not st then return nil end
    local own = rd_owner_map()
    local hi, lo, share = RD().surplus or 1.15, RD().deficit or 0.6, RD().cargo_share or 0.05
    local best, bs
    for src, s in pairs(st) do
      local ow = own[src]
      if type(s) == "table" and s.q and s.tn and s.lv and ow and not KC.S.F[ow].player and (not fid or ow == fid) and (not o.fids or o.fids[ow]) and tpos(src) then
        local sx, sz = tpos(src)
        local dp = o.x and rdist(sx, sz, o.x, o.z) or 0
        if dp <= (RD().near or 90000) then
          for _, c in ipairs(ROAD_CATS) do
            local lv = s.lv[c]
            local room = lv and s.q[c] and s.tn[c] and (s.q[c] - s.tn[c] * 1.0)
            if lv and lv >= hi and room and room >= 1 then
              for dst, d2 in pairs(st) do
                local dw = own[dst]
                if dst ~= src and type(d2) == "table" and d2.lv and d2.lv[c] and d2.lv[c] <= lo and dw and tpos(dst) and (dw == ow or (not KC.S.F[dw].player and KC.rel(ow, dw) > -20)) then
                  local dd = KC.town_dist(src, dst)
                  if dd >= (RD().min_dist or 2500) and dd <= (RD().max_dist or 70000) then
                    local sc = dp + dd * 0.3 + d2.lv[c] * 20000
                    if not bs or sc < bs then bs = sc; best = { kind = "caravan", fid = ow, from = src, to = dst, owner = dw, c = c, n = math.min(share * s.tn[c], room), why = "deficit_" .. c } end
                  end
                end
              end
            end
          end
        end
      end
    end
    return best
  elseif kind == "wanderer" then
    if not fid then
      local list = {}
      for f2 in pairs(KC.S.F) do if rd_wanderer_ok(f2) then list[#list + 1] = f2 end end
      table.sort(list)
      if #list == 0 then return nil end
      fid = list[math.random(#list)]
    elseif not rd_wanderer_ok(fid) then return nil end
    local f = KC.S.F[fid]
    local own = rd_owner_map()
    local cand = {}
    for t, ow in pairs(own) do
      if KC.is_city(t) and ow ~= fid and tpos(t) and KC.rel(fid, ow) > -30 and not KC.S.F[ow].player then
        cand[#cand + 1] = { t, ow, KC.S.F[ow].wealth / math.max(1, KC.S.F[ow].wealth0) }
      end
    end
    if #cand == 0 then return nil end
    table.sort(cand, function(p, q) if p[3] ~= q[3] then return p[3] > q[3] end return p[1] < q[1] end)
    local pick = cand[math.random(math.min(3, #cand))]   -- бар богатого города: один из трёх самых богатых хозяев
    local fx, fz = KC.FPOS(fid)
    local from, fd
    if fx then for t in pairs(KC.CFG.town_info or {}) do local x, z = tpos(t); if x then local d = rdist(fx, fz, x, z); if not fd or d < fd then from, fd = t, d end end end end
    return { kind = "wanderer", fid = fid, from = from, to = pick[1], owner = pick[2], n = (f.wealth >= 5) and math.min(RD().merc_pay or 3, math.floor(f.wealth * 0.02)) or 0, why = "bar" }
  elseif kind == "courier" then
    local a, b = fid, o.b
    if not (a and KC.S.F[a] and KC.S.F[a].alive) then return nil end
    local mine = {}
    for t in pairs(KC.S.F[a].towns) do if tpos(t) then mine[#mine + 1] = t end end
    table.sort(mine)
    local from, to
    if b and KC.S.F[b] then
      local cap = KC.capital(a)
      if not (cap and tpos(cap)) then cap = mine[1] end
      if not cap then return nil end
      local cx, cz = tpos(cap)
      local bd
      if cx then for t in pairs(KC.S.F[b].towns) do local x, z = tpos(t); if x then local d = rdist(cx, cz, x, z); if not bd or d < bd then to, bd = t, d end end end end
      from = cap
    else
      if #mine < 2 then return nil end
      local bd
      for _, t in ipairs(mine) do local x, z = tpos(t); local d = o.x and rdist(o.x, o.z, x, z) or 0; if not bd or d < bd then from, bd = t, d end end
      local nd
      for _, t in ipairs(mine) do if t ~= from then local d = KC.town_dist(from, t); if d > 3000 and (not nd or d < nd) then to, nd = t, d end end end
    end
    if not (from and to) or from == to then return nil end
    if not rd_courier_cd("c|" .. a .. "|" .. tostring(b or ""), RD().courier_cd_days or 20) then return nil end
    return { kind = "courier", fid = a, from = from, to = to, owner = b or a, n = 0, why = o.why or "courier" }
  end
end
local function road_depart_impl(plan)   -- списать источник, записать путь в журнал; возвращает id записи (nil - числа не двигаются)
  if not plan then return nil end
  if plan.kind == "caravan" then
    local s = rd_stock(plan.from)
    if not s then return nil end
    local take = math.min(plan.n or 0, math.max(0, s.q[plan.c] or 0))
    if take <= 0 then return nil end
    s.q[plan.c] = s.q[plan.c] - take; s.lv = s.lv or {}; s.lv[plan.c] = s.q[plan.c] / s.tn[plan.c]
    return rd_add({ k = "caravan", f = plan.fid, from = plan.from, to = plan.to, c = plan.c, n = take, vis = KC.DAY }).id
  elseif plan.kind == "wanderer" then
    local f = KC.S.F[plan.fid]
    local take = f and math.min(plan.n or 0, f.wealth) or 0
    if take <= 0 then return nil end
    f.wealth = f.wealth - take
    return rd_add({ k = "wanderer", f = plan.fid, from = plan.from, to = plan.to, n = take, vis = KC.DAY }).id
  elseif plan.kind == "refugees" and plan.id then
    return plan.id
  end
  return nil
end
local function road_claim_impl(kind, fid, from)   -- видимая группа берёт на себя ожидающий путь (число уже списано в источнике)
  local r = rd_slot()
  local best
  for _, e in pairs(r.tr) do
    if e.k == kind and not e.vis and (not from or e.from == from) and (not best or e.d0 < best.d0 or (e.d0 == best.d0 and e.id < best.id)) then best = e end
  end
  if not best then return nil end
  best.vis = KC.DAY
  return { kind = kind, fid = fid or best.f, from = best.from, to = best.to, owner = KC.owner_of(best.to), n = best.n, id = best.id, why = "relocate" }
end
-- память дорог игрока
local function rd_eff(g)
  return g.w * 0.5 ^ (math.max(0, KC.DAY - g.d) / (RD().half_days or 20))
end
local function rd_cell(x, z)
  local c = RD().cell or 8000
  return math.floor(x / c) .. ":" .. math.floor(z / c)
end
local function road_visit_impl(x, z)
  if not (x and z) or not rd_on("grid") then return end
  local r = rd_slot()
  local k = rd_cell(x, z)
  local g = r.grid[k]
  if g and KC.DAY - (g.t or -1000) < (RD().grid_step_days or 0.1) then return end
  if g then g.w = math.min(RD().grid_cap or 60, rd_eff(g) + 1) else g = { w = 1 }; r.grid[k] = g end
  g.d, g.t = KC.DAY, KC.DAY
  local n = 0; for _ in pairs(r.grid) do n = n + 1 end
  local mx = RD().grid_max or 48
  if n > mx + 8 then
    local arr = {}
    for kk, gg in pairs(r.grid) do arr[#arr + 1] = { kk, rd_eff(gg) } end
    table.sort(arr, function(p, q) if p[2] ~= q[2] then return p[2] > q[2] end return p[1] < q[1] end)
    for i = mx + 1, #arr do r.grid[arr[i][1]] = nil end
    for i = 1, math.min(mx, #arr) do if arr[i][2] < 0.05 then r.grid[arr[i][1]] = nil end end
  end
end
local function road_heat_impl(x, z)
  local g = x and KC.S.roads and KC.S.roads.grid and KC.S.roads.grid[rd_cell(x, z)]
  return g and rd_eff(g) or 0
end
local function road_route_heat_impl(x1, z1, x2, z2)   -- сумма веса уникальных клеток вдоль отрезка
  local c = RD().cell or 8000
  local L = rdist(x1, z1, x2, z2)
  local steps = math.min(60, math.max(1, math.floor(L / (c / 4))))
  local seen, sum = {}, 0
  for i = 0, steps do
    local f = i / steps
    local x, z = x1 + (x2 - x1) * f, z1 + (z2 - z1) * f
    local k = rd_cell(x, z)
    if not seen[k] then seen[k] = true; sum = sum + road_heat_impl(x, z) end
  end
  return sum
end
local function road_grid_list()
  local out = {}
  if KC.S.roads and KC.S.roads.grid then for k, g in pairs(KC.S.roads.grid) do out[#out + 1] = { key = k, w = rd_eff(g) } end end
  table.sort(out, function(p, q) if p.w ~= q.w then return p.w > q.w end return p.key < q.key end)
  return out
end
for k, v in pairs({ROADS_OFF = ROADS_OFF, rd_on = rd_on, rsafe = rsafe, rd_add = rd_add, rd_travel = rd_travel, roads_step = roads_step, road_plan_impl = road_plan_impl, road_depart_impl = road_depart_impl, road_claim_impl = road_claim_impl, rd_arrive = rd_arrive, rd_slot = rd_slot, rd_stat = rd_stat, rd_wanderer_ok = rd_wanderer_ok, road_visit_impl = road_visit_impl, road_heat_impl = road_heat_impl, road_route_heat_impl = road_route_heat_impl, road_grid_list = road_grid_list}) do KC.RDS[k] = v end
end

function KC.pop_start(I)
  if I.kind == "city" then return ({ [2] = 100, [5] = 140, [6] = 80, [7] = 160 })[I.type] or 100 end
  if I.type == 3 then return 45 end
  return 35
end
function KC.relocate(sid, n, from_fid, okf)   -- беженцы идут в ближайший сытый город (ROADS: зачёт по прибытии, а не мгновенно); okf(t) - необязательный фильтр целей; возвращает цель
  local best, bd
  for t, I in pairs(KC.CFG.town_info) do
    local tw = KC.S.town[t]
    if t ~= sid and I.x and type(tw) == "table" and (not okf or okf(t)) and tw.pop and (KC.tlv(t, "food") or 0) >= 0.8 and tw.pop < tw.pop0 * 1.3 then   -- ROADS: без координат расстояние 0 - цель была бы "ближайшей" всегда
      local d = KC.town_dist(sid, t) * (I.sh and 0.7 or 1)   -- GOALS: оплот = убежище (стены, рынок, охрана): тянет беженцев сильнее
      if not bd or d < bd then best, bd = t, d end
    end
  end
  if not best then return end
  if KC.RDS.rd_on("refugees") and not KC.GL.h_live(KC.RDS.ROADS_OFF, "relocate") then
    local e = KC.RDS.rsafe("relocate", KC.RDS.rd_add, { k = "refugees", f = from_fid, from = sid, to = best, n = n, days = KC.RDS.rd_travel(sid, best, 0.5) })
    if e then return best end
  end
  KC.S.town[best].pop = KC.S.town[best].pop + n
  return best
end
function KC.refugees_ev(sid, n, a, why)
  if n < 5 then return end
  KC.S.stats.refugees = (KC.S.stats.refugees or 0) + 1
  KC.S.stats.refugees_n = (KC.S.stats.refugees_n or 0) + n
  local nm_ = KC.TOWN_NAME[sid] or sid
  KC.emit({ type = "refugees", a = a, town_sid = sid, town_name = nm_, n = math.floor(n), why = why,
         text = string.format("Families flee %s (%s): columns of refugees fill the roads.", nm_, why) })
end
function KC.town_step_impl(dt)
  local PP = KC.P.pop or {}
  if type(KC.S.town) ~= "table" then KC.S.town = {} end
  local own = {}
  for fid, f in pairs(KC.S.F) do if f.alive then for t in pairs(f.towns) do own[t] = fid end end end
  for sid, I in pairs(KC.CFG.town_info) do
    local tw = KC.S.town[sid]
    if type(tw) ~= "table" then tw = {}; KC.S.town[sid] = tw end
    local o = own[sid] or false
    if not tw.pop then tw.pop0 = KC.pop_start(I); tw.pop = tw.pop0; tw.own = o end
    tw.pop0 = tw.pop0 or KC.pop_start(I)
    if tw.own ~= o then   -- смена владельца: захват = разграбление и бегство, мятеж/распад - меньше
      local forced = o and tw.own
      local loss = tw.pop * (forced and (PP.sack_loss or 0.12) or (PP.unrest_loss or 0.04))
      loss = math.min(loss, tw.pop - tw.pop0 * (PP.min_share or 0.25))
      if loss > 0 then
        tw.pop = tw.pop - loss
        KC.refugees_ev(sid, loss, tw.own or o or nil, forced and "sacked" or "unrest")
        KC.relocate(sid, loss * 0.5, tw.own or o or nil)
      end
      tw.own = o
    end
    local lf = KC.tlv(sid, "food")
    if lf then
      local cap = tw.pop0 * (PP.cap or 1.3)
      if lf >= (PP.grow_above or 0.9) then
        tw.pop = tw.pop + tw.pop * (PP.grow or 0.0004) * dt * math.max(0, 1 - tw.pop / cap)
      elseif lf < (PP.starve_below or 0.3) then
        local floor_ = tw.pop0 * (PP.min_share or 0.25)
        local loss = math.max(0, math.min(tw.pop - floor_, tw.pop * (PP.starve or 0.002) * dt * (1 - lf / (PP.starve_below or 0.3))))
        tw.pop = tw.pop - loss
        tw.lost = (tw.lost or 0) + loss
        if tw.lost >= math.max(3, tw.pop0 * 0.08) and KC.DAY - (tw.ref_day or -1000) >= (PP.refugee_cooldown or 60) then
          tw.ref_day = KC.DAY
          KC.refugees_ev(sid, tw.lost, o or nil, "famine")
          KC.relocate(sid, tw.lost * 0.5, o or nil)
          tw.lost = 0
        end
      end
    end
  end
end
function KC.town_step(dt) KC.xsafe("town_pop", KC.town_step_impl, dt) end

-- FAMINE: хронический дефицит еды на складе города (lv.food < below несколько дней подряд) -> группа беженцев от хозяина в ближайший сытый дружественный город.
-- Раз в игровой день (тик может быть реже - тогда считаем прошедшие дни), лимит групп за прогон и кулдаун на город; состояние S.famine ленивое (старые сейвы без него).
-- Числа списываются в источнике сразу (relocate -> ROADS-запись), группу на дороге рисует KMM_Traces по событию famine_refugees.
function KC.RDS.famine_impl()
  local F = KC.P.famine or {}
  if F.enabled == false then return end
  if type(KC.S.famine) ~= "table" then KC.S.famine = { last = KC.DAY, t = {} } end
  local fs = KC.S.famine
  if type(fs.t) ~= "table" then fs.t = {} end
  local el = KC.DAY - (tonumber(fs.last) or KC.DAY)
  if el < 1 then return end
  if el > 30 then el = 30 end
  fs.last = KC.DAY
  local PP = KC.P.pop or {}
  local own = {}
  for fid, f in pairs(KC.S.F) do if f.alive then for t in pairs(f.towns) do own[t] = fid end end end
  local made = 0
  local below, need, cd = F.below or 0.35, F.days or 6, F.cooldown or 30
  for _, sid in ipairs(KC.sorted_keys(KC.CFG.town_info)) do
    local a = own[sid]
    local lv = KC.tlv(sid, "food")
    local rec = fs.t[sid]
    if type(rec) ~= "table" then rec = { n = 0, cd = -1000 }; fs.t[sid] = rec end
    if lv and lv < below and a and not KC.S.F[a].player then rec.n = (rec.n or 0) + el else rec.n = 0 end
    local tw = KC.S.town and KC.S.town[sid]
    if made < (F.max_groups or 2) and rec.n >= need and KC.DAY - (rec.cd or -1000) >= cd and type(tw) == "table" and tw.pop and tw.pop0
       and math.random() < (F.chance or 0.5) then
      local floor_ = tw.pop0 * (PP.min_share or 0.25)
      local n = math.min(tw.pop - floor_, math.max(F.min_n or 4, tw.pop * (F.share or 0.06)))
      if n >= (F.min_n or 4) then
        local dest = KC.relocate(sid, n, a, function(t)
          local o = own[t]
          return o and (o == a or (KC.S.F[o] and not KC.S.F[o].player and KC.rel(a, o) >= (F.friend_rel or 1))) and (KC.tlv(t, "food") or 0) >= (F.dest_food or 0.8)
        end)
        if dest then
          tw.pop = tw.pop - n
          rec.cd, rec.n = KC.DAY, 0
          made = made + 1
          KC.S.stats.famine_groups = (KC.S.stats.famine_groups or 0) + 1
          local nm_, dn = KC.TOWN_NAME[sid] or sid, KC.TOWN_NAME[dest] or dest
          KC.emit({ type = "famine_refugees", a = a, town_sid = sid, town_name = nm_, to = dest, to_name = dn, n = math.floor(n),
                 text = string.format("Hunger empties the granaries of %s: %d people of %s set out for %s.", nm_, math.floor(n), KC.name(a), dn) })
        end
      end
    end
  end
end
function KC.RDS.famine_step() KC.xsafe("famine", KC.RDS.famine_impl) end

function KC.init_know(fid, f)
  local c = KC.CFG.factions[fid] or {}
  if c.know then return c.know end
  for _, x in ipairs((KC.CFG.roles or {}).technopriests or {}) do if x == fid then return 2.4 end end
  if f.relic then return 2.0 end
  if tostring(fid):find("Empire") then return 1.8 end
  local nc = 0
  for t in pairs(f.towns) do if KC.is_city(t) then nc = nc + 1 end end
  if nc == 0 then return 0 end
  return math.min(1.6, 0.5 + 0.15 * nc)
end
function KC.know_step_impl(dt)
  local K = KC.P.know or {}
  for fid, f in pairs(KC.S.F) do
    if f.alive and not f.player then
      if f.know == nil then f.know = KC.init_know(fid, f) end
      local nt = KC.ntowns(f)
      f.nt_prev = f.nt_prev or nt
      if nt < f.nt_prev then f.know = math.max(0, f.know - (K.loss_per_town or 0.12) * (f.nt_prev - nt)) end   -- лаборатории потеряны
      f.nt_prev = nt
      if nt > 0 and f.wealth > f.wealth0 then
        f.know = math.min(K.cap or 3, f.know + (K.grow or 0.0003) * dt * math.min(1, f.wealth / f.wealth0 - 1))
      end
      if f.relic then   -- износ и пополнение реликтовых частей (f.components = relic_parts)
        if f.components == nil then f.components = 100 end
        if nt > 0 then f.components = math.min(100, f.components + (K.parts_regen or 0.02) * f.know * dt / 5) end
        if f.mode == "mobilized" then f.components = math.max(0, f.components - (K.mobilized_extra_wear or 0.05) * dt / 5) end
        if nt == 0 then f.components = math.max(0, f.components - (K.homeless_wear or 0.06) * dt / 5) end
        if f.mode == "mobilized" and math.random() < (K.salvage_chance or 0.006) * dt / 5 then
          f.components = math.min(100, f.components + (K.salvage_gain or 10))
          KC.emit({ type = "relic_salvage", a = fid, text = string.format("%s recovered ancient parts from a forgotten vault.", KC.name(fid)) })
        end
        if f.components < (K.weak_below or 12) then f.strength = f.strength * (1 - (K.weak_decay or 0.004) * dt / 5) end   -- реликты не чинят: сила тает
        f.relic_parts = f.components
      end
    end
  end
end
function KC.know_step(dt) KC.xsafe("know", KC.know_step_impl, dt) end

function KC.ship(from, to, c, share)   -- перевозка излишка категории c из городов фракции from в нуждающиеся города фракции to
  local T = KC.S.stock and KC.S.stock.towns
  if not T then return 0 end
  local donors, rec = {}, {}
  for t in pairs(KC.S.F[from].towns) do local s = T[t]; if s and s.lv and s.tn and (s.lv[c] or 0) > 1.1 then donors[#donors + 1] = s end end
  for t in pairs(KC.S.F[to].towns) do local s = T[t]; if s and s.lv and s.tn and (s.lv[c] or 1) < 0.9 then rec[#rec + 1] = s end end
  if #donors == 0 or #rec == 0 then return 0 end
  table.sort(donors, function(p, q) return p.lv[c] > q.lv[c] end)
  table.sort(rec, function(p, q) return p.lv[c] < q.lv[c] end)
  local pool = 0
  for _, s in ipairs(donors) do local x = (s.q[c] - s.tn[c]) * share; if x > 0 then pool = pool + x; s.q[c] = s.q[c] - x; s.lv[c] = s.q[c] / s.tn[c] end end
  local moved = 0
  for _, s in ipairs(rec) do
    local need = math.min(pool - moved, s.tn[c] - s.q[c])
    if need > 0 then s.q[c] = s.q[c] + need; s.lv[c] = s.q[c] / s.tn[c]; moved = moved + need end
  end
  if pool > moved then donors[1].q[c] = donors[1].q[c] + (pool - moved); donors[1].lv[c] = donors[1].q[c] / donors[1].tn[c] end   -- остаток возвращается
  return moved
end
function KC.raid_surplus_do(fid, o, c)
  local T = KC.S.stock and KC.S.stock.towns
  local f, O = KC.S.F[fid], KC.S.F[o]
  if not T then return end
  local best, bl
  local lst = {}
  for t in pairs(O.towns) do lst[#lst + 1] = t end
  table.sort(lst)
  for _, t in ipairs(lst) do local s = T[t]; if s and s.lv and s.tn and (s.lv[c] or 0) > (bl or 1.1) then best, bl = t, s.lv[c] end end
  if not best then return end
  local U, L = KC.P.utility, KC.P.loop or {}
  local p = KC.power(fid) / math.max(1, KC.power(fid) + KC.power(o))
  KC.S.stats.raid_surplus = (KC.S.stats.raid_surplus or 0) + 1
  f.last_loop = KC.DAY
  local tn = KC.TOWN_NAME[best] or best
  if math.random() < p then
    local s = T[best]
    local take = math.max(0, (s.q[c] - s.tn[c]) * (L.raid_take or 0.4))
    s.q[c] = s.q[c] - take; s.lv[c] = s.q[c] / s.tn[c]
    local hub, hl
    for t in pairs(f.towns) do local r = T[t]; if r and r.lv and r.tn and (not hl or r.lv[c] < hl) then hub, hl = t, r.lv[c] end end
    if hub then local r = T[hub]; r.q[c] = math.min(r.q[c] + take, 2.5 * r.tn[c]); r.lv[c] = r.q[c] / r.tn[c] end
    O.strength = O.strength * (1 - U.raid_loss * 0.6); f.strength = f.strength * (1 - U.raid_loss * 0.4)
    KC.add_rel(fid, o, -10)
    KC.emit({ type = "raid_surplus", a = fid, b = o, town_sid = best, town_name = tn, cat = c, n = math.floor(take),
           text = string.format("%s hit the %s caravans of %s near %s.", KC.name(fid), c, KC.name(o), tn) })
  else
    f.strength = f.strength * (1 - U.raid_loss); KC.add_rel(fid, o, -5)
    KC.emit({ type = "attack_repelled", a = fid, b = o, town_sid = best, town_name = tn,
           text = string.format("%s tried to seize stores at %s, but guards held.", KC.name(fid), tn) })
  end
end
function KC.trade_for_do(fid, o, c)
  local f, O = KC.S.F[fid], KC.S.F[o]
  local L = KC.P.loop or {}
  f.last_loop = KC.DAY
  if not KC.treaty_between(fid, o, "trade") and KC.trust(fid, o) >= KC.P.treaties.min_trust then KC.sign("trade", fid, o, "needs " .. c) end
  local n = KC.ship(o, fid, c, L.ship or 0.5)
  if n > 0 then
    local pay = n * 0.05 * (c == "metal" and (KC.S.metal_price or 1) or 1)
    f.wealth = f.wealth - pay; O.wealth = O.wealth + pay
    KC.add_rel(fid, o, 3); KC.add_trust(fid, o, 2)
    KC.S.stats.trade_for = (KC.S.stats.trade_for or 0) + 1
    KC.emit({ type = "trade_for", a = fid, b = o, cat = c, n = math.floor(n),
           text = string.format("%s bought %s from %s to ease their shortage.", KC.name(fid), c, KC.name(o)) })
  end
end

---------------------------------------------------------------------------------------------- ROBBERY: засады на путников и сбыт добычи
-- waylay: A (даже нейтральная к B, но с просевшими отношениями, без договора) грабит караваны B по мотиву: нужда / жадность / месть.
-- Груз = часть склада города-источника B (как caravan_lost by="other"), уходит в S.loot[A]; через sell_days добыча «продаётся» в ближайшем
-- городе союзного/нейтрального владельца (rel >= 0; незаконное — только у скупщиков ROLE.fences): склад города + добыча, богатство A + цена.
-- Нет города — добыча тает. Параметры: P.robbery (дефолты ниже). Каждая функция в xsafe.
KC.RB_DEF = {
  rel_max = -15, cooldown = 14, pair_cooldown = 50, weight = 0.5, take = 0.06, keep = 0.6, min_take = 1,
  need_def = 0.15, poor = 0.5, revenge_days = 240, greed = 0.5, rel_hit = 4, rel_victim = 4, trust_hit = 3,
  sell_days = 10, max_age = 90, sell_range = 180000, full = 1.8, sale_k = 0.7, contra_k = 1.3, fence_rel = 2, max_entries = 12,
  keep_gear = 0.5, gear_need = 0.5, gear_metal = 0.5, gear_other = 0.5, gear_pull = 1.5, gear_motive = 1.5, gear_rel = 15, gear_weight = 1.5, thief_pull = 2.5, contra_range = 3, drug_pull = 0.85, gear_grace = 45, ambush_days = 2, repel_rel = 8, repel_trust = 6,
  price = { food = 0.3, metal = 0.6, weapons = 1.0, armor = 1.0, med = 0.8, drugs = 1.2, lux = 1.5, scrap = 0.2 },
}
KC.RB_CATS = { "food", "metal", "weapons", "armor", "med", "lux", "drugs" }
function KC.RB()
  local R = KC.P.robbery
  if type(R) ~= "table" then R = {}; KC.P.robbery = R end
  for k, v in pairs(KC.RB_DEF) do if R[k] == nil then R[k] = v end end
  return R
end
function KC.illegal_for(fid, c)   -- копия правила модели STOCK (legality): drug_ban и P.contra.legal
  if c == "drugs" and KC.ROLE.drug_ban and KC.ROLE.drug_ban[fid] then return true end
  local key
  for _, e in ipairs((KC.P.contra or {}).legal or {}) do
    if e[c] == false then key = key or (fid .. " " .. KC.name(fid)); if key:find(e.pat) then return true end end
  end
  return false
end
function KC.loot_add_impl(fid, c, n, victim)
  local R = KC.RB()
  if not (KC.S and KC.S.F[fid]) or type(c) ~= "string" or not R.price[c] then return false end
  n = tonumber(n) or 0
  if n <= 0 then return false end
  if type(KC.S.loot) ~= "table" then KC.S.loot = {} end
  local L = KC.S.loot[fid]
  if not L then L = {}; KC.S.loot[fid] = L end
  for _, e in ipairs(L) do   -- та же категория и жертва в тот же день — одна запись
    if e.c == c and e.b == victim and e.day == math.floor(KC.DAY) then e.n = e.n + n; return true end
  end
  L[#L + 1] = { c = c, n = n, day = math.floor(KC.DAY), b = victim }
  while #L > R.max_entries do   -- переполнение: старейшая запись сливается в следующую
    local x = table.remove(L, 1); if L[1] and L[1].c == x.c then L[1].n = L[1].n + x.n end
  end
  return true
end
function KC.waylay_motive(fid, o)
  local f, R = KC.S.F[fid], KC.RB()
  local m, why = 0, nil
  if (f.food_def or 0) > R.need_def or (f.metal_def or 0) > R.need_def or f.wealth < R.poor * f.wealth0 or (f.hunger or 0) > 0.3 or (f.gear_shift or 0) < 0 then m = m + 1; why = "need" end
  if (f.gear_shift or 0) < 0 then m = m + R.gear_motive; why = why or "need" end   -- рваная экипировка толкает на грабёж
  local w = f.wronged and f.wronged[o]
  if w and KC.DAY - w < R.revenge_days then m = m + 1.2; why = "revenge" end
  if f.ambition == "enrichment" or KC.ntowns(f) == 0 then m = m + R.greed; why = why or "greed" end
  return m, why
end
function KC.waylay_ok(fid, o)   -- условия засады (выбор действия и тесты)
  local f, O, R = KC.S.F[fid], KC.S.F[o], KC.RB()
  if not (f and O and f.alive and O.alive and fid ~= o) or f.player or O.player or f.relic then return false end
  if KC.rel(fid, o) > R.rel_max + (((f.gear_shift or 0) < 0) and R.gear_rel or 0) or KC.treaty_between(fid, o) then return false end
  if KC.DAY - (f.last_waylay or -1000) < R.cooldown or KC.DAY - ((f.way_pair or {})[o] or -1000) < R.pair_cooldown then return false end
  return (KC.waylay_motive(fid, o)) > 0
end
KC.AMB_PROBE = nil   -- Traces: fn(a, b, town_sid, id) → true, если засаду разыграют живым боем рядом с игроком
function KC.waylay_finish(fid, o, tsid, why)   -- абстрактный исход засады (грабёж груза города жертвы)
  local f, O, R, U = KC.S.F[fid], KC.S.F[o], KC.RB(), KC.P.utility
  local T = KC.S.stock and KC.S.stock.towns
  local cat, n = nil, 0
  if T and tsid then
    local s = T[tsid]
    if s and s.q and s.tn then
      local want = (why == "need") and (((f.metal_def or 0) > (f.food_def or 0)) and "metal" or "food") or nil
      local gpoor = (f.gear_shift or 0) < 0   -- рваная экипировка: тянет к броне/оружию
      local thief = KC.ROLE.thieves and KC.ROLE.thieves[fid]   -- воровские фракции охотнее берут запретное (дурь, роскошь)
      local bs
      for _, c in ipairs(KC.RB_CATS) do
        if s.q[c] and (s.tn[c] or 0) > 0 then
          local sc = (s.q[c] / s.tn[c]) * (0.7 + 0.6 * math.random()) + ((c == want) and 0.5 or 0) + ((gpoor and (c == "armor" or c == "weapons")) and R.gear_pull or 0) + ((thief and (c == "drugs" or c == "lux")) and R.thief_pull or 0) + ((c == "drugs") and R.drug_pull or 0)
          if not bs or sc > bs then bs, cat = sc, c end
        end
      end
      if cat then
        local take = math.min(s.q[cat] * R.take, s.q[cat] - R.keep * s.tn[cat])
        if take >= R.min_take then
          n = math.floor(take)
          s.q[cat] = s.q[cat] - n; s.lv[cat] = s.q[cat] / s.tn[cat]
        else cat = nil end
      end
    else tsid = nil end
  end
  local tn = tsid and (KC.TOWN_NAME[tsid] or tsid) or nil
  O.strength = O.strength * (1 - U.raid_loss * 0.15); f.strength = f.strength * (1 - U.raid_loss * 0.1)
  KC.add_rel(fid, o, -R.rel_hit)   -- отношения симметричны: жертва тоже холоднее
  KC.add_trust(fid, o, -R.trust_hit)
  KC.S.stats.waylay = (KC.S.stats.waylay or 0) + 1
  KC.S.stats["waylay_" .. why] = (KC.S.stats["waylay_" .. why] or 0) + 1
  if (f.gear_shift or 0) < 0 then KC.S.stats.waylay_gearpoor = (KC.S.stats.waylay_gearpoor or 0) + 1 end
  if cat then KC.S.stats['waylay_cat_' .. cat] = (KC.S.stats['waylay_cat_' .. cat] or 0) + 1; if (cat == 'armor' or cat == 'weapons') and (f.gear_shift or 0) < 0 then KC.S.stats.waylay_gear_poor = (KC.S.stats.waylay_gear_poor or 0) + 1 end end
  if cat and n > 0 then
    local keepn = 0   -- бедный грабитель (дефицит брони/оружия) оставляет часть себе: смягчает gear_shift, а не продаёт
    if cat ~= "drugs" and (f.gear_shift or 0) < 0 then   -- металл и прочее идут в починку экипировки вполсилы/вчетверть
      local gw = (cat == "armor" or cat == "weapons") and 1 or ((cat == "metal") and R.gear_metal or R.gear_other)
      keepn = math.min(n, math.ceil(n * R.keep_gear * gw)); n = n - keepn
      f.gear_loot = (f.gear_loot or 0) + keepn * gw
      if f.gear_loot >= R.gear_need then f.gear_loot = 0; f.gear_shift = 0; f.gear_grace = KC.DAY + R.gear_grace; KC.S.stats.gear_loot = (KC.S.stats.gear_loot or 0) + 1 end
    end
    if n > 0 then KC.loot_add_impl(fid, cat, n, o) end
    n = n + keepn
  end
  KC.emit({ type = "waylay", a = fid, b = o, town_sid = tsid, town_name = tn, cat = cat, n = n, why = why,
         text = string.format("%s waylay travellers of %s on the roads%s.", KC.name(fid), KC.name(o), tn and (" near " .. tn) or "") })
end
function KC.waylay_do(fid, o)
  local f, O, R, U = KC.S.F[fid], KC.S.F[o], KC.RB(), KC.P.utility
  local T = KC.S.stock and KC.S.stock.towns
  f.last_waylay = KC.DAY; f.way_pair = f.way_pair or {}; f.way_pair[o] = KC.DAY
  KC.S.stats.waylay_try = (KC.S.stats.waylay_try or 0) + 1
  local _, why = KC.waylay_motive(fid, o)
  why = why or "greed"
  local pa, po = KC.power(fid), KC.power(o)
  if math.random() >= KC.clamp(0.2 + 0.6 * pa / math.max(1, pa + po), 0.2, 0.85) then   -- конвой отбился
    f.strength = f.strength * (1 - U.raid_loss * 0.2); KC.add_rel(fid, o, -2)
    return
  end
  local lst = {}
  for t in pairs(O.towns) do lst[#lst + 1] = t end
  table.sort(lst)
  local tsid = nil
  if T and #lst > 0 then tsid = lst[math.random(#lst)] end
  -- ВИДИМАЯ ЗАСАДА: если игрок рядом с городом жертвы, Traces разыгрывают засаду живым боем (караван B против отряда A);
  -- абстрактный исход откладывается до результата (caravan_lost / waylay_repelled) или таймаута R.ambush_days
  if KC.AMB_PROBE and tsid then
    local id = (KC.S.amb_seq or 0) + 1
    local okp, yes = pcall(KC.AMB_PROBE, fid, o, tsid, id)
    if okp and yes then
      KC.S.amb_seq = id; KC.S.ambush = KC.S.ambush or {}
      KC.S.ambush[id] = { a = fid, b = o, tsid = tsid, why = why, day = KC.DAY, exp = KC.DAY + (R.ambush_days or 2) }
      KC.S.stats.waylay_ambush = (KC.S.stats.waylay_ambush or 0) + 1
      return
    end
  end
  KC.waylay_finish(fid, o, tsid, why)
end
function KC.ambush_find(id, a, b)   -- отложенная засада: по id или по паре (грабитель, жертва)
  local A = KC.S.ambush
  if type(A) ~= "table" then return nil end
  if id and A[id] then return id, A[id] end
  for _, k in ipairs(KC.sorted_keys(A)) do if A[k].a == a and A[k].b == b then return k, A[k] end end
end
function KC.ambush_finish(id, am)   -- абстрактный исход отложенной засады (добыча как обычно)
  KC.S.ambush[id] = nil
  if KC.S.F[am.a] and KC.S.F[am.a].alive and KC.S.F[am.b] then KC.waylay_finish(am.a, am.b, am.tsid, am.why) end
end
function KC.ambush_expire()   -- таймаут: видимая засада не дала результата → абстрактный исход, как раньше
  if type(KC.S.ambush) ~= "table" then return end
  for _, k in ipairs(KC.sorted_keys(KC.S.ambush)) do
    local am = KC.S.ambush[k]
    if KC.DAY >= am.exp then KC.S.stats.ambush_timeout = (KC.S.stats.ambush_timeout or 0) + 1; KC.ambush_finish(k, am) end
  end
end
function KC.loot_buyer(fid, c, owners, day, victim)   -- ближайший город союзного/нейтрального владельца, куда A сбудет категорию c
  local R = KC.RB()
  local T = KC.S.stock and KC.S.stock.towns
  local x, z = KC.FPOS(fid)
  if not (T and x) then return nil end
  local best, bd, bo, contra
  for _, sid in ipairs(KC.sorted_keys(T)) do
    local o = owners[sid]
    local s, I = T[sid], KC.CFG.town_info and KC.CFG.town_info[sid]
    if o and I and I.x and s.q and s.q[c] and s.tn and (s.tn[c] or 0) > 0 and KC.S.F[o] and not KC.S.F[o].player and (s.siege or -1) < day then
      local d = math.sqrt((I.x - x) ^ 2 + (I.z - z) ^ 2)
      local fence = KC.ROLE.fences and KC.ROLE.fences[o]
      local ok = (o == fid) or KC.rel(fid, o) >= 0 or (fence and KC.rel(fid, o) > -60)
      local ill = KC.illegal_for(o, c)
      local vill_any = c == "drugs" and next(KC.ROLE.drug_ban or {}) ~= nil   -- контрабанда: где-то запрещено, сбывают только скупщики
      local vill = fence and vill_any   -- запрещённое хоть где (drug_ban) краденое: скупщик берёт как контрабанду
      if ok and (ill or (vill_any and o ~= fid)) and not fence then ok = false end   -- незаконное берут только скупщики
      if ok and d <= R.sell_range * (vill_any and R.contra_range or 1) and s.q[c] < R.full * s.tn[c] and (not bd or d < bd) then best, bd, bo, contra = sid, d, o, (ill or vill) and true or false end
    end
  end
  return best, bo, contra
end
function KC.loot_step_impl()
  local R = KC.RB()
  if type(KC.S.loot) ~= "table" then return end
  local owners
  local T = KC.S.stock and KC.S.stock.towns
  for _, fid in ipairs(KC.sorted_keys(KC.S.loot)) do
    local L, f = KC.S.loot[fid], KC.S.F[fid]
    if not (f and f.alive) then KC.S.loot[fid] = nil
    else
      local keep = {}
      for _, e in ipairs(L) do
        if KC.DAY - e.day < R.sell_days then keep[#keep + 1] = e
        else
          if not owners then owners = {}; for g, F in pairs(KC.S.F) do if F.alive then for t in pairs(F.towns) do owners[t] = g end end end end
          local sid, bo, contra = KC.loot_buyer(fid, e.c, owners, KC.DAY, e.b)
          if sid then
            local s = T[sid]
            local nn = math.min(e.n, R.full * s.tn[e.c] - s.q[e.c])
            if nn >= 0.5 then
              s.q[e.c] = s.q[e.c] + nn; s.lv[e.c] = s.q[e.c] / s.tn[e.c]
              local pr = (R.price[e.c] or 0.2) * (e.c == "metal" and (KC.S.metal_price or 1) or 1)
              f.wealth = f.wealth + nn * pr * R.sale_k * (contra and R.contra_k or 1)
              local kind = (bo == fid) and "loot_sold_own" or ((KC.rel(fid, bo) >= 20) and "loot_sold_ally" or "loot_sold_neutral")
              KC.S.stats.loot_sold = (KC.S.stats.loot_sold or 0) + 1
              KC.S.stats[kind] = (KC.S.stats[kind] or 0) + 1
              if contra then KC.S.stats.loot_sold_contra = (KC.S.stats.loot_sold_contra or 0) + 1 end
              if e.b and KC.S.F[e.b] and bo ~= e.b and bo ~= fid and KC.rel(e.b, bo) >= 0 then KC.add_rel(e.b, bo, -R.fence_rel) end   -- покупка краденого сердит жертву
              KC.emit({ type = "loot_sold", a = fid, b = e.b, owner = bo, town_sid = sid, town_name = KC.TOWN_NAME[sid] or sid, cat = e.c, n = math.floor(nn), contra = contra or nil,
                     text = string.format("%s sold plundered %s in %s.", KC.name(fid), e.c, KC.TOWN_NAME[sid] or sid) })
            else keep[#keep + 1] = e end
          elseif KC.DAY - e.day < R.max_age then keep[#keep + 1] = e
          else KC.S.stats.loot_melted = (KC.S.stats.loot_melted or 0) + 1 end   -- покупателя нет: добыча «растаяла»
        end
      end
      KC.S.loot[fid] = (#keep > 0) and keep or nil
    end
  end
end
function KC.loot_step() KC.xsafe("loot", KC.loot_step_impl) end

KC.react_impl = function(ev)   -- реакции на события игрока и чужие события (из emit, под pcall)
  local ty = ev.type
  local pf = KC.CFG.player_faction
  local L, K = KC.P.loop or {}, KC.P.know or {}
  if (ty == "raid" or ty == "raid_surplus" or ty == "waylay") and ev.a and ev.b and ev.a ~= ev.b and KC.S.F[ev.a] and KC.S.F[ev.b] then   -- жертва помнит обидчика (мотив мести)
    local V = KC.S.F[ev.b]; V.wronged = V.wronged or {}; V.wronged[ev.a] = KC.DAY
  end
  if ty == "town_captured" then   -- «кража» знания у более знающей жертвы
    local A, B = KC.S.F[ev.a], KC.S.F[ev.b]
    if A and B and (B.know or 0) > (A.know or 0) then
      A.know = math.min(K.cap or 3, (A.know or 0) + (K.steal or 0.5) * (B.know - (A.know or 0)))
      B.know = math.max(0, B.know - (K.steal_loss or 0.1))
    end
  elseif ty == "player_sold" and pf then   -- поставка игрока в дефицитную категорию: владелец города теплее
    local o = ev.town_sid and KC.owner_of(ev.town_sid)
    local lv = ev.town_sid and ev.cat and KC.tlv(ev.town_sid, ev.cat)
    if o and lv and lv < (L.def_below or 0.6) and KC.S.sold_rel_day ~= KC.DAY then
      KC.S.sold_rel_day = KC.DAY
      KC.add_rel(o, pf, L.sold_rel or 1)
    end
  elseif ty == "contraband_caught" and pf then   -- игрок попался на сбыте незаконного: владелец города холоднее
    if ev.a and KC.S.F[ev.a] and KC.S.contra_rel_day ~= KC.DAY then
      KC.S.contra_rel_day = KC.DAY
      KC.add_rel(ev.a, pf, -((KC.P.contra or {}).caught_rel or 4)); KC.S.stats.contraband_caught = (KC.S.stats.contraband_caught or 0) + 1
    end
  elseif ty == "caravan_lost" then
    if ev.by == "player" and ev.a and KC.S.F[ev.a] and pf then
      KC.add_rel(ev.a, pf, -(L.caravan_rel or 6)); KC.S.stats.caravan_lost_player = (KC.S.stats.caravan_lost_player or 0) + 1
    end
    local k = ev.killer   -- Traces увидели чужих NPC рядом с погибшим караваном: жертва запомнит обидчика (мотив мести, как raid/waylay)
    if k and ev.a and k ~= ev.a and k ~= pf and KC.S.F[k] and KC.S.F[ev.a] and KC.S.F[ev.a].alive then
      local V = KC.S.F[ev.a]; V.wronged = V.wronged or {}; V.wronged[k] = KC.DAY
      KC.S.stats.caravan_wronged = (KC.S.stats.caravan_wronged or 0) + 1
    end
    if k and ev.a then   -- погиб караван видимой засады: добыча грабителя как обычно
      local id, am = KC.ambush_find(ev.ambush, k, ev.a)
      if am then KC.S.stats.ambush_lost = (KC.S.stats.ambush_lost or 0) + 1; KC.ambush_finish(id, am) end
    end
  elseif ty == "waylay_repelled" then   -- грабителей отбили/разбили, караван жив: груз цел, добычи нет
    local id, am = KC.ambush_find(ev.id, ev.a, ev.b)
    if am then
      KC.S.ambush[id] = nil
      local f, U, R = KC.S.F[am.a], KC.P.utility, KC.RB()
      if f then f.strength = f.strength * (1 - U.raid_loss * 0.2); KC.add_rel(am.a, am.b, -2) end
      KC.S.stats.ambush_repelled = (KC.S.stats.ambush_repelled or 0) + 1
      if ev.near_player and pf and KC.S.F[am.b] and am.b ~= pf then   -- игрок рядом помог отбиться: жертва благодарна (договор станет легче через rel/trust)
        KC.add_rel(am.b, pf, R.repel_rel or 8); KC.add_trust(am.b, pf, R.repel_trust or 6)
        KC.S.stats.ambush_repelled_player = (KC.S.stats.ambush_repelled_player or 0) + 1
      end
    end
  elseif ty == "player_relic_forge" and pf then
    KC.S.forge = KC.S.forge or { n = 0 }
    KC.S.forge.n = KC.S.forge.n + 1; KC.S.forge.day = KC.DAY; KC.S.forge.until_day = KC.DAY + (K.forge_days or 150); KC.S.forge.item = ev.item
    KC.S.stats.forge = (KC.S.stats.forge or 0) + 1
    for _, fid in ipairs(KC.sorted_keys(KC.S.F)) do
      local f = KC.S.F[fid]
      if f.alive and f.relic and math.random() < (K.forge_mobilize or 0.7) then KC.relic_trigger(fid, "forge") end
    end
    if KC.DAY - (KC.S.forge.told or -1000) >= (K.forge_tell_cooldown or 30) then
      KC.S.forge.told = KC.DAY
      KC.emit({ type = "relic_forge_known", b = pf, item = ev.item, text = "Whispers run along the roads: the Nameless one is forging relics of the old kind." })
    end
  end
end

function KC.base_def()   -- защита базы игрока: измеренная + бонус за отбитые рейды (затухает за 120 дней)
  local B = KC.S.base
  if not B then return nil end
  local bonus = B.def_bonus or 0
  if bonus > 0 then bonus = bonus * math.max(0, 1 - (KC.DAY - (B.def_bonus_day or KC.DAY)) / 120) end
  return (B.defense or 30) + bonus
end
function KC.base_result(kind, fid, nat)   -- REV2: исход рейда на базу: repelled — рейдеры разбиты; unattended — игрока не было на базе;
  -- sacked — база разграблена при игроке (только из фазы родной кампании, U2). nat = исход из фазы CampaignInstance (KC.L2.camp.base_step), иначе Traces
  if not (KC.S and KC.S.base and fid and KC.S.F[fid]) then return false end
  KC.DAY = math.max(KC.DAY, KC.S.last_day or KC.DAY)
  local R, U, pf, f, B = KC.R2(), KC.P.utility, KC.CFG.player_faction, KC.S.F[fid], KC.S.base
  if kind == "repelled" then
    f.strength = f.strength * (1 - U.raid_loss)
    B.def_bonus, B.def_bonus_day = math.min(R.base_def_cap or 40, (KC.base_def() or 30) - (B.defense or 30) + (R.base_def_gain or 6)), KC.DAY
    if pf and KC.S.F[pf] then KC.add_rel(fid, pf, -(R.base_repel_rel or 3)) end
    KC.S.stats.base_repelled = (KC.S.stats.base_repelled or 0) + 1
    KC.emit({ type = "base_raid_repelled", a = fid, b = pf, native = nat, text = string.format("The raiders of %s were broken at the Nameless settlement.", KC.name(fid)) })
  elseif kind == "unattended" then
    local g = math.min(R.base_plunder_cap or 20, (B.value or 0) * (R.base_plunder or 0.1))
    f.wealth = f.wealth + g
    if pf and KC.S.F[pf] then KC.add_rel(fid, pf, -(R.base_unattended_rel or 2)) end
    KC.S.stats.base_unattended = (KC.S.stats.base_unattended or 0) + 1
    KC.emit({ type = "base_raid_unattended", a = fid, b = pf, native = nat, text = string.format("%s raiders found the Nameless settlement empty and left with what they could carry.", KC.name(fid)) })
  elseif kind == "sacked" and nat then   -- U2: VICTORY кампании при игроке у базы: добыча как у пустой базы x base_sack_mult, бонус обороны сгорает
    local g = math.min((R.base_plunder_cap or 20) * (R.base_sack_mult or 1.5), (B.value or 0) * (R.base_plunder or 0.1) * (R.base_sack_mult or 1.5))
    f.wealth = f.wealth + g
    f.strength = f.strength * (1 - U.raid_loss * 0.5)
    B.def_bonus, B.def_bonus_day = 0, KC.DAY
    if pf and KC.S.F[pf] then KC.add_rel(fid, pf, -(R.base_unattended_rel or 2)) end
    KC.S.stats.base_sacked = (KC.S.stats.base_sacked or 0) + 1
    KC.emit({ type = "base_raid_sacked", a = fid, b = pf, native = true, text = string.format("%s broke into the Nameless settlement and carried off its goods.", KC.name(fid)) })
  else return false end
  return true
end

---------------------------------------------------------------------------------------------- LINKS2: связки существующих механик (склад, шина, хаос, Self)
-- Подписчики шины (под pcall, при первой ошибке отключается только свой), состояние S.l2 (в сейве), параметры P.links2 (rules\conductor.json).
--   stock_glut      -> цель рейда за излишком (raid_surplus) для соседей без договора + скидка у торговцев города (price_mult_town)
--   stock_shortage  -> повод для торгового договора/каравана (trade_for) за нужной категорией
--   stock_sacked    -> всплеск недовольства в соседних городах пострадавшей фракции
--   drug_bust / smuggle_run / contraband_caught -> отношения источника с Holy Nation и ветвями, источник - цель рейда
--   self_retreat / self_surrender_attempt {fid, n} -> лёгкий удар по силе и боевому духу фракции (KMM_Self)
--   chaos_incursion/chaos_cult несут cause/god/squad: бог по причине кризиса (squad - только из отрядов Chaos Demons в traces.json)
KC.L2 = (function()   -- замыкание: у основного чанка Lua лимит 200 локальных
local function L2P() return KC.P.links2 or {} end
local function l2()
  if type(KC.S.l2) ~= "table" then KC.S.l2 = {} end
  local l = KC.S.l2
  for _, k in ipairs({ "glut", "need", "price", "tgt", "hot", "selfd", "intr", "famine" }) do if type(l[k]) ~= "table" then l[k] = {} end end
  return l
end
local function l2_match(fid, pat) return pat ~= nil and fid ~= nil and (tostring(fid) .. " " .. KC.name(fid)):find(pat) ~= nil end
local function l2_profile(fid)
  for _, pr in ipairs(L2P().profiles or {}) do if l2_match(fid, pr.pat) then return pr end end
  return nil
end
local function l2_alive(fid) local f = fid and KC.S.F[fid]; if f and f.alive then return f end; return nil end
local function l2_hn(fid) return l2_match(fid, (L2P().contra or {}).hn_pat) end
local function l2_count(k) KC.S.stats[k] = (KC.S.stats[k] or 0) + 1 end

local function l2_contra(src, hunter, d)   -- src - источник контрабанды (или игрок), hunter - кто поймал/пострадал
  local G, l = L2P().contra or {}, l2()
  if not l2_alive(src) then return end
  l.hot[src] = d
  if hunter and hunter ~= src and l2_alive(hunter) and src ~= KC.CFG.player_faction then   -- источник становится целью рейда охотника (не игрок: у базы свои рейды)
    l.tgt[hunter] = l.tgt[hunter] or {}
    l.tgt[hunter][src] = d + (G.days or 60)
    l2_count("l2_contra_tgt")
  end
  local hn_hunter = hunter and l2_hn(hunter)
  if hn_hunter and d - (l.hot["rel|" .. tostring(src)] or -1000) >= (G.cooldown or 20) then
    l.hot["rel|" .. tostring(src)] = d
    local lo, hi = G.rel_min or 2, G.rel_max or 5
    for _, x in ipairs(KC.sorted_keys(KC.S.F)) do
      if x ~= src and l2_hn(x) and KC.S.F[x].alive then KC.add_rel(x, src, -(lo + (hi - lo) * math.random())) end
    end
    l2_count("l2_contra_rel")
  end
end

local function l2_selfhit(ev, w)
  local G, l = L2P().self or {}, l2()
  local fid = ev.a or ev.fid   -- KMM_Self (PERF.md): a = фракция отряда; fid - запасное имя поля
  local f = l2_alive(fid)
  if not f or f.player or fid == KC.CFG.player_faction then return end
  local n = math.max(1, tonumber(ev.n) or 1)
  if ev.why == "avoid" or ev.why == "faction_avoid" then w = w * (G.avoid_w or 0.3) end   -- осторожность, не поражение
  if ev.mode == "knockout" then w = w * (G.knockout_w or 1.5) end
  local d = math.floor(ev.day or KC.DAY)
  local sd = l.selfd[fid]
  if not sd or sd.day ~= d then sd = { day = d, sum = 0 }; l.selfd[fid] = sd end
  local k = math.min((G.cap or 0.01) - sd.sum, (G.strength or 0.003) * n * w)
  if k > 0 then f.strength = f.strength * (1 - k); sd.sum = sd.sum + k end
  f.morale = math.max(G.morale_floor or 0.3, (f.morale or 1) - math.min(G.morale_max or 0.15, (G.morale or 0.02) * n * w))
  l2_count("l2_self_hits")
end

local function l2_install()
  local function sub(nm, pat, fn)
    KC.subscribe(pat, function(ev)
      local key = "l2_" .. nm
      if KC.GL.h_live(KC.XDIS, key) or not KC.S or not L2P().enabled then return end
      local ok, err = pcall(fn, ev)
      if not ok then KC.GL.h_bad(KC.XDIS, key, "KMM_Conductor." .. key, err, key) else KC.GL.h_done(KC.XDIS, key) end
    end)
  end
  sub("glut", "stock_glut", function(ev)
    local G, l = L2P().glut or {}, l2()
    local d = ev.day or KC.DAY
    if not l2_alive(ev.a) or not ev.cat then return end
    l.glut[ev.a] = { cat = ev.cat, town = ev.town_sid, untl = d + (G.days or 40) }
    if ev.town_sid then l.price[ev.town_sid] = d + (G.price_days or 30) end
    l2_count("l2_glut")
  end)
  sub("shortage", "stock_shortage", function(ev)
    local G, l = L2P().shortage or {}, l2()
    local d = ev.day or KC.DAY
    if not l2_alive(ev.a) or not ev.cat then return end
    l.need[ev.a] = { cat = ev.cat, town = ev.town_sid, untl = d + (G.days or 40) }
    l2_count("l2_shortage")
  end)
  sub("sacked", "stock_sacked", function(ev)
    local G = L2P().sacked or {}
    local f = l2_alive(ev.b)
    if not f or not ev.town_sid then return end
    local lst = {}
    for t in pairs(f.towns) do if t ~= ev.town_sid then lst[#lst + 1] = t end end
    table.sort(lst, function(p, q) local dp, dq = KC.town_dist(ev.town_sid, p), KC.town_dist(ev.town_sid, q); if dp ~= dq then return dp < dq end; return p < q end)
    f.unrest = f.unrest or {}
    for i = 1, math.min(G.towns or 2, #lst) do
      local u = f.unrest[lst[i]] or { level = 0 }
      if u.level < (G.max_level or 0.6) then u.level = math.min(G.max_level or 0.6, u.level + (G.unrest or 0.1)); f.unrest[lst[i]] = u end
    end
    l2_count("l2_sacked")
  end)
  sub("bust", "drug_bust", function(ev) l2_contra(ev.b, ev.a, ev.day or KC.DAY) end)
  sub("run", "smuggle_run", function(ev) l2_contra(ev.a, ev.b, ev.day or KC.DAY) end)
  sub("caught", "contraband_caught", function(ev)
    local G, l = L2P().contra or {}, l2()
    local pf, d = KC.CFG.player_faction, ev.day or KC.DAY
    l.hot[ev.a or "?"] = d
    if pf and KC.S.F[pf] and ev.a and l2_hn(ev.a) and d - (l.hot["rel|" .. pf] or -1000) >= (G.cooldown or 20) then   -- ветви Holy Nation: холодок к игроку (сам владелец города уже обработан реакцией)
      l.hot["rel|" .. pf] = d
      for _, x in ipairs(KC.sorted_keys(KC.S.F)) do
        if x ~= ev.a and x ~= pf and l2_hn(x) and KC.S.F[x].alive then KC.add_rel(x, pf, -(G.branch_rel or 1.5)) end
      end
      l2_count("l2_caught_branches")
    end
  end)
  sub("betrayal", "betrayal", function(ev) local d = ev.day or KC.DAY; local l = l2(); if ev.a then l.intr[ev.a] = d end; if ev.b then l.intr[ev.b] = d end end)
  sub("broken", "treaty_broken", function(ev) local d = ev.day or KC.DAY; local l = l2(); if ev.a then l.intr[ev.a] = math.max(l.intr[ev.a] or -1000, d - 60) end; if ev.b then l.intr[ev.b] = math.max(l.intr[ev.b] or -1000, d - 60) end end)
  sub("famine", "famine", function(ev) if ev.a then l2().famine[ev.a] = ev.day or KC.DAY end end)
  for _, nm in ipairs((L2P().self or {}).events or { "self_retreat", "self_surrender_attempt" }) do
    local w = (nm == "self_surrender_attempt") and ((L2P().self or {}).surrender_w or 1.5) or 1
    sub("self_" .. nm, nm, function(ev) l2_selfhit(ev, w) end)
  end
end

-- причина кризиса -> бог. Сумма взвешенных признаков фракции-жертвы, побеждает наибольший (>= min); иначе без бога (тройка/любой отряд)
local TR_SQUADS   -- множество отрядов Chaos Demons из traces.json (ленивая загрузка)
local function chaos_squads()
  if TR_SQUADS == nil then
    TR_SQUADS = false
    local tj = KC.load_json("traces.json", "C:/KenshiModMap/build/KMM_Conductor/traces.json")
    if tj and tj.daemons and type(tj.daemons.squads) == "table" then
      TR_SQUADS = {}
      for _, sq in ipairs(tj.daemons.squads) do TR_SQUADS[sq] = true end
    end
  end
  return TR_SQUADS or nil
end
local function chaos_pick(fid)
  local G = (L2P().chaos) or {}
  local f = KC.S.F[fid]
  if not (f and G.gods) then return nil end
  local l = l2()
  local sc = { khorne = 0, nurgle = 0, slaanesh = 0, tzeentch = 0 }
  if KC.DAY - (f.last_war or -1000) < (G.war_days or 60) then sc.khorne = sc.khorne + 1 end
  sc.khorne = sc.khorne + (f.stress and KC.clamp((f.stress - 1) * 0.5, 0, 0.8) or 0)
  sc.nurgle = 2 * (f.hunger or 0) + ((KC.DAY - (l.famine[fid] or -1000) < (G.famine_days or 120)) and 1 or 0)
              + ((l.need[fid] and l.need[fid].cat == "food" and l.need[fid].untl >= KC.DAY) and 0.5 or 0) + (f.food_def or 0)
  local cap = KC.capital(fid)
  local lux = cap and KC.tlv(cap, "lux") or 1
  local drg = cap and KC.tlv(cap, "drugs") or 1
  sc.slaanesh = ((KC.DAY - (l.hot[fid] or -1000) < (G.contra_days or 120)) and 1 or 0) + ((lux or 1) > 1.5 and 0.7 or 0) + ((drg or 1) > 1.5 and 0.5 or 0)
  sc.tzeentch = ((KC.DAY - (l.intr[fid] or -1000) < (G.intrigue_days or 120)) and 1 or 0) + (f.succession and 0.4 or 0)
  local best, bs = nil, G.min_score or 0.5
  for _, g in ipairs({ "khorne", "nurgle", "slaanesh", "tzeentch" }) do if sc[g] > bs then best, bs = g, sc[g] end end
  if not best then return nil end
  local sq = G.gods[best]
  local set = chaos_squads()
  if not (sq and set and set[sq]) then sq = nil end   -- у бога нет своего отряда в данных мода -> любой отряд, как раньше
  return best, sq, ({ khorne = "war", nurgle = "famine", slaanesh = "excess", tzeentch = "intrigue" })[best]
end

local function links2_step_impl()
  local G, l = L2P(), l2()
  if not G.enabled then return end
  local rec = (G.self or {}).morale_rec or 0.02
  for _, f in pairs(KC.S.F) do if f.morale and f.morale < 1 then f.morale = math.min(1, f.morale + rec) end end
  for _, k in ipairs({ "glut", "need" }) do for fid, e in pairs(l[k]) do if e.untl < KC.DAY then l[k][fid] = nil end end end
  for t, u in pairs(l.price) do if u < KC.DAY then l.price[t] = nil end end
  for h, tt in pairs(l.tgt) do
    for s, u in pairs(tt) do if u < KC.DAY then tt[s] = nil end end
    if next(tt) == nil then l.tgt[h] = nil end
  end
end
local function links2_step() KC.xsafe("l2_step", links2_step_impl) end

-- кандидаты utility-выбора из причин; возвращает категорию, если победил raid_surplus/trade_for из этого блока
local function links2_consider_impl(fid, f, cands, consider, peek, avoids, amb)
  local G = L2P()
  if not G.enabled then return nil end
  local U, L, W = KC.P.utility, KC.P.loop or {}, KC.P.utility.weights
  local l = l2()
  local win
  local myp = KC.power(fid)
  local ready = KC.DAY - (f.last_loop or -1000) >= (L.cooldown_days or 25)
  local can_war = (not f.relic) or f.mode == "mobilized"
  local function try(a, u, arg, cat)
    local _, b0 = peek()
    consider(a, u, arg)
    local nb, b1, ba = peek()
    if b1 ~= b0 and nb == a and ba == arg then win = cat end
  end
  local function hostile(o) local O = KC.S.F[o]; return O and O.alive and not O.player and o ~= fid and KC.rel(fid, o) < 0 and not KC.treaty_between(fid, o) end
  -- 1) перебор у соседа: повод для рейда за излишком
  local GG = G.glut or {}
  if ready and can_war then
    for _, o in ipairs(cands) do
      local g = l.glut[o]
      if g and g.untl >= KC.DAY and hostile(o) then
        local O = KC.S.F[o]
        local ratio = myp / math.max(1, KC.power(o))
        if (O.lvl and (O.lvl[g.cat] or 0) > 1.1) and not avoids(o, ratio) then
          try("raid_surplus", (GG.raid_w or 0.7) * (W.raid[amb] or 1) * math.min(2, ratio), o, g.cat)
        end
      end
    end
  end
  -- 2) нехватка у себя: торговый договор/караван с соседом, у которого есть излишек этой категории
  local GS = G.shortage or {}
  local nd = l.need[fid]
  if ready and nd and nd.untl >= KC.DAY then
    local lv0 = nd.town and KC.tlv(nd.town, nd.cat) or 0.3
    local needv = KC.clamp(1 - lv0 / 0.6, 0.2, 1)
    for _, o in ipairs(cands) do
      local O = KC.S.F[o]
      local ol = O and O.alive and not O.player and O.lvl and O.lvl[nd.cat]
      if ol and o ~= fid and ol > (L.surplus_lv or 1.25) and KC.rel(fid, o) >= 0 then
        try("trade_for", (GS.trade_w or 1.0) * (W.trade[amb] or 1) * needv * 3 * math.min(1, ol - 1), o, nd.cat)
      end
    end
  end
  -- 3) контрабанда: источник - цель рейда
  local GC = G.contra or {}
  local tg = l.tgt[fid]
  if tg and can_war then
    for _, o in ipairs(cands) do
      if tg[o] and tg[o] >= KC.DAY and hostile(o) then
        local ratio = myp / math.max(1, KC.power(o))
        if not avoids(o, ratio) then try("raid", (GC.raid_w or 0.8) * (U.raid_weight_mult or 1) * (W.raid[amb] or 1) * math.min(2, ratio) * (1 + math.max(0, -KC.rel(fid, o)) / 100), o, nil) end
      end
    end
  end
  -- 4) профиль экономики фракции (правила): избыток оружия/брони у себя -> налёт на излишек соседа вне договоров (орки: «Waaagh»)
  local pr = l2_profile(fid)
  local wg = pr and pr.waaagh
  if wg and ready and can_war and f.lvl then
    local hot = false
    for _, c in ipairs(KC.sorted_keys(wg.cats or {})) do if (f.lvl[c] or 0) >= wg.cats[c] then hot = true end end
    if hot then
      for _, o in ipairs(cands) do
        if hostile(o) then
          local O = KC.S.F[o]
          local cat, cl
          for _, c in ipairs(wg.loot or { "food", "metal" }) do local v = O.lvl and O.lvl[c]; if v and v > 1.1 and (not cl or v > cl) then cat, cl = c, v end end
          local ratio = myp / math.max(1, KC.power(o))
          if cat and not avoids(o, ratio) then try("raid_surplus", (wg.w or 0.8) * (W.raid[amb] or 1) * math.min(2, ratio), o, cat) end
        end
      end
    end
  end
  return win
end
local function links2_consider(...)
  if KC.GL.h_live(KC.XDIS, "l2_choose") then return nil end
  local ok, r = pcall(links2_consider_impl, ...)
  if not ok then KC.GL.h_bad(KC.XDIS, "l2_choose", "KMM_Conductor.l2_choose", r, "l2_choose"); return nil end
  KC.GL.h_done(KC.XDIS, "l2_choose")
  return r
end
return { consider = links2_consider, step = links2_step, pick = chaos_pick, install = l2_install, P = L2P, state = l2 }
end)()

function KC.choose_action(fid)
  local f = KC.S.F[fid]
  local U = KC.P.utility
  local W = U.weights
  local amb = f.ambition
  if f.relic then
    if f.mode == "focused" and math.random() > KC.P.relic.focused_act_chance then return nil end
    amb = (f.relic == "spread_chaos") and "expansion" or "faith"
  end
  local best, bu, barg = nil, 0, nil
  local myp = KC.power(fid)
  local function consider(a, u, arg) u = u * (0.8 + 0.4 * math.random()) * KC.GL.mult(fid, f, a, arg); if u > bu then best, bu, barg = a, u, arg end end
  local function peek() return best, bu, barg end
  local l2cat   -- LINKS2: категория победившего кандидата из причин шины
  local cands = KC.near(fid, KC.P.bus.radius * 1.5)
  if f.relic then
    local seen = {}
    for _, o in ipairs(cands) do seen[o] = true end
    for o, F in pairs(KC.S.F) do if F.alive and o ~= fid and KC.rel(fid, o) <= -50 and not seen[o] then cands[#cands + 1] = o end end
  end
  local pf = KC.CFG.player_faction   -- игрок без координат: кандидат в союз для всех, кто к нему хорошо относится
  if pf and pf ~= fid and KC.S.F[pf] and KC.rel(fid, pf) >= 40 then cands[#cands + 1] = pf end
  local threat, tid, tmax = 0, nil, 0
  for _, o in ipairs(cands) do
    if KC.rel(fid, o) <= -30 and KC.power(o) > myp then
      threat = threat + KC.power(o) / math.max(1, myp)
      if KC.power(o) > tmax then tid, tmax = o, KC.power(o) end
    end
  end
  local AVR = KC.R2().avoid_ratio or 0.4   -- REV2: слабый не лезет на явно сильного (кроме мести)
  local function avoids(o, ratio)
    if KC.GL.h_live(KC.REV2_OFF, "avoid") or ratio >= AVR then return false end
    local w = f.wronged and f.wronged[o]
    return not (w and KC.DAY - w < (KC.R2().avoid_revenge_days or 90)) and amb ~= "revenge"
  end
  for _, o in ipairs(cands) do
    local O = KC.S.F[o]
    if O and O.alive and o ~= fid then
      local op = KC.power(o)
      local r = KC.rel(fid, o)
      local ratio = myp / math.max(1, op)
      if r >= 0 and (f.gear_shift or 0) < 0 and KC.waylay_ok(fid, o) then   -- бедный снаряжением грабит и прохладных соседей
        consider("waylay", KC.RB().weight * KC.RB().gear_weight * (KC.waylay_motive(fid, o)) * math.min(2, ratio), o)
      end
      if r < 0 and not KC.treaty_between(fid, o) and not O.player then
        local weary = math.min(1, (KC.DAY - (f.last_war or -1000)) / (U.war_cooldown_days or 20))   -- усталость от войны
        local bonus = ((f.opp[o] and f.opp[o] >= KC.DAY) and 1.5 or 1) * weary
        local shy = avoids(o, ratio)
        if not shy then consider("raid", (U.raid_weight_mult or 1) * W.raid[amb] * math.min(2, ratio) * bonus * (1 + math.max(0, -r) / 100), o) end
        if not shy and KC.waylay_ok(fid, o) then consider("waylay", KC.RB().weight * (((f.gear_shift or 0) < 0) and KC.RB().gear_weight or 1) * (KC.waylay_motive(fid, o)) * math.min(2, ratio) * (1 + math.max(0, -r) / 100), o) end
        if ratio >= U.capture_min_ratio and KC.ntowns(O) > 0 and (not f.relic or f.mode == "mobilized") then consider("capture", (U.capture_weight_mult or 1) * W.capture[amb] * math.min(3, ratio) / 2 * bonus, o) end
      end
      if r >= 0 and not KC.treaty_between(fid, o, "trade") and not O.player then consider("trade", W.trade[amb] * 0.6 * math.min(1, O.wealth / 300), o) end
      if r >= 10 and not KC.treaty_between(fid, o) and not KC.GL.banned(fid, o) then
        local common = 0
        if O.player then   -- враги игрока могут быть далеко: общих врагов с игроком ищем по всем фракциям
          for x, X in pairs(KC.S.F) do if X.alive and x ~= fid and x ~= o and KC.rel(fid, x) <= -50 and KC.rel(o, x) <= -50 then common = common + 1 end end
        else
          for _, x in ipairs(cands) do if KC.rel(fid, x) <= -50 and KC.rel(o, x) <= -50 then common = common + 1 end end
        end
        local fear = (threat > 1) and threat or 0
        if O.player and KC.S.forge and KC.S.forge.until_day and KC.DAY < KC.S.forge.until_day and (amb == "faith" or (f.know or 0) >= 1.5) then common = common + 1 end   -- ищут союза с кузнецом реликтов
        if common > 0 or fear > 0 or O.player then consider("alliance", W.alliance[amb] * (0.4 * common + 0.3 * fear + 0.1) * (1 + math.max(0, r) / 50), o) end
      end
    end
  end
  do   -- CORE: нужда в еде/металле -> договор/рейд за излишком соседа (петля склад -> дирижёр)
    local L = KC.P.loop or {}
    f.need_cat = nil
    if f.lvl and KC.DAY - (f.last_loop or -1000) >= (L.cooldown_days or 25) then
      local fd, md, nm0 = f.food_def or 0, f.metal_def or 0, L.need_min or 0.12
      local needc, needv
      if fd >= nm0 and fd >= md then needc, needv = "food", fd elseif md >= nm0 then needc, needv = "metal", md end
      if needc then
        f.need_cat = needc
        for _, o in ipairs(cands) do
          local O = KC.S.F[o]
          local ol = O and O.lvl and O.lvl[needc]
          if O and O.alive and not O.player and o ~= fid and ol and ol > (L.surplus_lv or 1.25) then
            local sur = math.min(1, ol - 1)
            local r = KC.rel(fid, o)
            if r >= 0 then
              consider("trade_for", (L.trade_for_w or 1.2) * (W.trade[amb] or 1) * needv * 3 * sur, o)
            elseif not KC.treaty_between(fid, o) and myp >= 0.8 * KC.power(o) and (not f.relic or f.mode == "mobilized") then
              consider("raid_surplus", (L.raid_surplus_w or 0.6) * (W.raid[amb] or 1) * needv * 3 * sur * math.min(2, myp / math.max(1, KC.power(o))), o)
            end
          end
        end
      end
    end
  end
  l2cat = KC.L2.consider(fid, f, cands, consider, peek, avoids, amb)   -- LINKS2: перебор/нехватка/контрабанда/профиль экономики
  if KC.S.free and next(KC.S.free) then   -- свободные (отделившиеся) города рядом — лёгкая добыча
    local cf = KC.CFG.factions[fid]
    if cf and cf.x then
      for t in pairs(KC.S.free) do
        local I = KC.CFG.town_info[t]
        if I and I.x and math.sqrt((I.x - cf.x) ^ 2 + (I.z - cf.z) ^ 2) <= KC.P.bus.radius and (not f.relic or f.mode == "mobilized") then
          consider("capture_free", W.capture[amb] * 0.9, t)
        end
      end
    end
  end
  local B, PB = KC.S.base, KC.P.player_base or {}
  if B and B.known and pf and pf ~= fid and (B.value or 0) >= (PB.min_value or 30) and not f.relic and KC.DAY - (B.last_raid or -1000) > (PB.raid_cooldown_days or 15)
     and not KC.treaty_between(fid, pf) then
    local fx, fz = KC.FPOS(fid)
    local home = fx and math.sqrt((fx - B.x) ^ 2 + (fz - B.z) ^ 2) <= KC.P.bus.radius * 1.5
    local okm, OM = pcall(KC.ore_motive, fid, f, fx, fz)   -- ORE4: голод по металлу + работающий рудник игрока рядом
    if not okm then OM = nil end
    if home or OM then
      local m, why = 0, nil
      if home then
        if (f.stress or 0) > (PB.need_stress or 1.2) or (f.hunger or 0) > 0.35 or f.wealth < 40 then m = m + 1; why = "need" end
        if KC.rel(fid, pf) <= (PB.revenge_rel or -40) then m = m + 1.2; why = why or "revenge" end
        if (amb == "enrichment" or amb == "expansion") and myp > (PB.greed_ratio or 1.4) * (KC.base_def() or 30) then m = m + 0.6 * math.min(2, B.value / 100); why = why or "greed" end
        if KC.S.forge and KC.S.forge.until_day and KC.DAY < KC.S.forge.until_day and (amb == "enrichment" or amb == "expansion" or (f.know or 0) >= 1) then m = m + ((KC.P.know or {}).forge_raid or 0.8); why = why or "relic" end   -- игрок ковёт реликты: приманка
      end
      if OM then m = m + OM.w; if why == nil or why == "need" then why = "ore" end end   -- цель - рудник (Sync base_try, Traces base_gate)
      if m > 0 then consider("raid_base", (PB.raid_weight or 1.3) * m, why) end
    end
  end
  if (f.relic and f.mode == "mobilized") or ((((f.stress or 0) > 1.1) or amb == "enrichment") and myp > 60) then
    local fx, fz = KC.FPOS(fid)
    if fx then
      local bs, bd
      for sid, r in pairs(KC.S.ruins or {}) do
        local I = KC.SITE[sid]
        if r.scrap > 200 and I then
          local d = math.sqrt((I.x - fx) ^ 2 + (I.z - fz) ^ 2)
          if d <= KC.P.bus.radius and (not bd or d < bd) then bs, bd = sid, d end
        end
      end
      if bs then consider("expedition", 0.5 * (f.relic and 1.5 or 1) * math.max(0.5, f.stress or 1), bs) end
    end
  end
  if f.wealth > U.recruit_cost * 3 then consider("recruit", W.recruit[amb] * math.min(2, f.wealth / (f.strength * 4 + 1)), nil) end
  if threat > 1.5 then consider("hide", W.hide[amb] * math.min(2, threat / 2), tid) end
  if l2cat and (best == "raid_surplus" or best == "trade_for") then f.need_cat = l2cat end
  return best, barg
end

-- REV2: совместный рейд — союзники по военному договору присоединяются к рейду/захвату, если им выгодно (общая цель, есть силы, не друзья цели)
function KC.joint_allies(fid, o)
  local R, out = KC.R2(), {}
  if KC.GL.h_live(KC.REV2_OFF, "joint") or R.joint_enabled == false or not (o and KC.S.F[o]) then return out end
  for _, e in ipairs(KC.allies_of(fid, { military = true })) do
    local t, al = e.t, e.other
    local A = KC.S.F[al]
    if A and A.alive and not A.player and al ~= o and not KC.treaty_between(al, o) and KC.rel(al, o) < (R.joint_max_rel or 20)
       and not (A.relic and A.mode ~= "mobilized") and KC.DAY - (t.last_joint or -1000) >= (R.joint_cooldown or 40)
       and KC.power(al) >= (R.joint_min_power or 0.2) * KC.power(fid) and math.random() < (R.joint_chance or 0.6) then
      out[#out + 1] = { al = al, t = t }
    end
  end
  return out
end
function KC.joint_bonus(J) local b = 0; for _, j in ipairs(J) do b = b + (KC.R2().joint_weight or 0.6) * KC.power(j.al) end; return b end
function KC.joint_finish(J, fid, o, success, town_sid, loot)
  if #J == 0 then return end
  KC.r2safe("joint_finish", function()
    local U = KC.P.utility
    for _, j in ipairs(J) do
      local A = KC.S.F[j.al]
      j.t.last_joint = KC.DAY
      A.strength = A.strength * (1 - U.raid_loss * (KC.R2().joint_cost or 0.4))
      KC.add_trust(fid, j.al, KC.R2().joint_trust or 4)
      KC.add_rel(j.al, o, -6)
      A.last_war = KC.DAY
      if success and loot and loot > 0 then local share = loot * (KC.R2().joint_loot or 0.25); KC.S.F[fid].wealth = KC.S.F[fid].wealth - share; A.wealth = A.wealth + share end
      KC.S.stats.joint = (KC.S.stats.joint or 0) + 1
      KC.emit({ type = "joint_raid", a = j.al, b = o, lead = fid, town_sid = town_sid, town_name = town_sid and (KC.TOWN_NAME[town_sid] or town_sid) or nil,
             success = success and true or false,
             text = string.format("%s rode with %s against %s.", KC.name(j.al), KC.name(fid), KC.name(o)) })
    end
  end)
end

function KC.act(fid, a, o)
  local f, U = KC.S.F[fid], KC.P.utility
  local J = {}
  KC.P._ncur = nil
  if a == "raid" and o and KC.L2.camp and KC.L2.camp.try then KC.xsafe("native_campaign", KC.L2.camp.try, fid, o, a) end
  if a == "raid" or a == "capture" then local okj, jr = pcall(KC.joint_allies, fid, o); if okj then J = jr; KC.GL.h_done(KC.REV2_OFF, "joint") else KC.GL.h_bad(KC.REV2_OFF, "joint", "KMM_Conductor.rev2_joint", jr, "rev2 joint", KC.sub_log) end end
  local jb = KC.joint_bonus(J)
  if a == "raid" or a == "capture" or a == "capture_free" or a == "raid_surplus" then f.last_war = KC.DAY end
  local sa0, so0 = f.strength, (o and KC.S.F[o] and KC.S.F[o].strength) or 0
  local function war_scrap()   -- война пожирает металл и производит его: потери → скрап обеим сторонам
    local O = o and KC.S.F[o]
    if not O then return end
    local loss = math.max(0, sa0 - f.strength) + math.max(0, so0 - O.strength)
    local k = (KC.P.ore and KC.P.ore.scrap_per_loss or 0.6) * loss * 0.5
    f.scrap = (f.scrap or 0) + k; O.scrap = (O.scrap or 0) + k
  end
  if a == "raid" then
    local O = KC.S.F[o]
    local p = (KC.power(fid) + jb) / math.max(1, KC.power(fid) + jb + KC.power(o))
    KC.S.stats.raids = KC.S.stats.raids + 1
    local won = math.random() < p
    local loot0 = O.wealth * U.raid_gain
    if won then
      local loot = loot0
      O.wealth, f.wealth = O.wealth - loot, f.wealth + loot
      O.strength = O.strength * (1 - U.raid_loss); f.strength = f.strength * (1 - U.raid_loss * 0.5)
      KC.add_rel(fid, o, -8)
      war_scrap()
      KC.emit({ type = "raid", a = fid, b = o, text = string.format("%s raided %s and carried off goods.", KC.name(fid), KC.name(o)) })
    else
      f.strength = f.strength * (1 - U.raid_loss); O.strength = O.strength * (1 - U.raid_loss * 0.3)
      KC.add_rel(fid, o, -5)
      war_scrap()
      KC.emit({ type = "attack_repelled", a = fid, b = o, text = string.format("%s attacked %s, but were driven off.", KC.name(fid), KC.name(o)) })
    end
    KC.joint_finish(J, fid, o, won, nil, loot0)
  elseif a == "capture" then
    local O = KC.S.F[o]
    local list = {}
    for t in pairs(O.towns) do list[#list + 1] = t end
    if #list == 0 then return end
    table.sort(list)
    if (f.stress or 0) > 1.1 or (f.metal_def or 0) > ((KC.P.loop or {}).mine_def or 0.3) then   -- голод по металлу: целью становятся рудники, а не города (LATE_GAME §3)
      local mines = {}
      for _, t in ipairs(list) do if KC.S.ore and KC.S.ore[t] and (KC.S.ore[t].mine or KC.S.ore[t].R > 0.3 * KC.S.ore[t].R0) then mines[#mines + 1] = t end end
      if #mines > 0 then list = mines end
    end
    local town = list[math.random(#list)]
    local tname = KC.TOWN_NAME[town] or town
    if KC.ore_campaign_try and (f.metal_def or 0) > ((KC.P.loop or {}).mine_def or 0.3) then KC.xsafe("ore_campaign", KC.ore_campaign_try, fid, o, town) end   -- LINKS2
    if KC.L2.camp and KC.L2.camp.try then KC.xsafe("native_campaign", KC.L2.camp.try, fid, o, a, town) end   -- NATIVE_MAP п.2
    local p = KC.clamp(KC.P.outcome.base_success * (2 * (KC.power(fid) + jb) / math.max(1, KC.power(fid) + jb + KC.power(o))) ^ KC.P.outcome.strength_exponent,
                    KC.P.outcome.min_success, KC.P.outcome.max_success)
    if KC.is_city(town) then p = p * ((KC.P.unrest or {}).city_capture_mult or 0.7) end   -- город брать труднее, чем ферму или аванпост
    local share = KC.ncities(f) / math.max(1, KC.TOTAL_CITIES)   -- перерастяжение: у крупной державы каждый новый город даётся тяжелее
    if share > 0.17 then p = p * KC.clamp(1 - (share - 0.17) * 14, 0.02, 1) end
    f.strength = f.strength * 0.85; O.strength = O.strength * 0.8
    war_scrap()
    KC.add_rel(fid, o, -15)
    local took = math.random() < p
    if took then
      KMM_Conductor.capture_town(fid, o, town, {})
    else
      KC.emit({ type = "attack_repelled", a = fid, b = o, town_sid = town, town_name = tname, text = string.format("%s assaulted %s and were thrown back by %s.", KC.name(fid), tname, KC.name(o)) })
    end
    KC.joint_finish(J, fid, o, took, town, 0)
  elseif a == "capture_free" then
    if KC.S.free[o] and math.random() < 0.6 and not (KC.is_city(o) and KC.ncities(f) / math.max(1, KC.TOTAL_CITIES) >= ((KC.P.unrest or {}).max_city_share or 0.22)) then
      KC.S.free[o] = nil; f.towns[o] = true
      f.unrest = f.unrest or {}; f.unrest[o] = { level = 0.6 }
      KC.S.stats.captures = KC.S.stats.captures + 1
      KC.emit({ type = "town_captured", a = fid, town_sid = o, town_name = KC.TOWN_NAME[o] or o, text = string.format("%s took the free town of %s.", KC.name(fid), KC.TOWN_NAME[o] or o) })
    end
  elseif a == "trade" then
    if math.random() < KC.P.treaties.propose_chance and KC.trust(fid, o) >= KC.P.treaties.min_trust then KC.sign("trade", fid, o, "mutual gain")
    else f.wealth = f.wealth + U.trade_gain; KC.S.F[o].wealth = KC.S.F[o].wealth + U.trade_gain * 0.8 end
  elseif a == "alliance" then
    local O = KC.S.F[o]
    if KC.trust(fid, o) < KC.P.treaties.min_trust or math.random() > KC.P.treaties.propose_chance then return end
    local ratio = KC.power(fid) / math.max(1, KC.power(o))
    local ttype, why = "nonaggression", "a common enemy"
    if ratio >= KC.P.treaties.vassal_power_ratio and KC.ntowns(O) <= 2 and not O.player then ttype, why = "vassal", "fear"
    elseif KC.rel(fid, o) >= 40 then ttype = "military"
    elseif KC.rel(fid, o) >= 20 then ttype = "defense" end
    local accept = (O.player and KC.rel(fid, o) >= 50) or (not O.player and (KC.rel(o, fid) >= 0 or ttype == "vassal"))
    if accept then KC.sign(ttype, fid, o, why) end   -- для вассалитета a = сюзерен, b = вассал
  elseif a == "raid_base" then
    local pf = KC.CFG.player_faction
    KC.S.base.last_raid = KC.DAY
    f.last_war = KC.DAY
    KC.S.stats.base_raids = (KC.S.stats.base_raids or 0) + 1
    KC.S.base_raids = KC.S.base_raids or {}
    table.insert(KC.S.base_raids, { fid = fid, why = o, day = KC.DAY })
    while #KC.S.base_raids > 5 do table.remove(KC.S.base_raids, 1) end
    KC.add_rel(fid, pf, -10)
    -- U2: рейд ведёт родная кампания движка (KC.L2.camp.base_try; событие base_campaign даёт привязка к CampaignInstance, исход - фаза в base_step);
    -- кампания невозможна (игрок далеко, нет FACTION_CAMPAIGN, лимиты, сбой) -> base_raid старым путём Traces. Одно событие на рейд.
    local nat = KC.L2.camp and KC.L2.camp.base_try and KC.L2.camp.base_try(fid, o)
    local OB = (o == "ore") and KC.BASE_ORE() or nil   -- ORE4: рейд за железом идёт на рудник (точка для Traces base_gate)
    if not nat then KC.emit({ type = "base_raid", a = fid, b = pf, why = o, ox = OB and OB.x, oz = OB and OB.z, text = KC.L2.camp and KC.L2.camp.base_text(fid, o) or (KC.name(fid) .. " are marching on the Nameless settlement.") }) end
  elseif a == "expedition" then
    local r, I = KC.S.ruins[o], KC.SITE[o]
    f.strength = f.strength * (1 - (0.03 + 0.07 * math.random()))
    local g = math.min(r.scrap, ((KC.P.ore or {}).ruin_raid_gain or 120) * (0.5 + math.random()))
    r.scrap = r.scrap - g; f.scrap = (f.scrap or 0) + g
    if f.relic then local c = math.min(r.comp, 5 * math.random()); r.comp = r.comp - c; f.components = math.min(100, (f.components or 0) + c * 4) end
    KC.S.stats.expeditions = (KC.S.stats.expeditions or 0) + 1
    KC.emit({ type = "ruin_expedition", a = fid, town_sid = o, town_name = I and I.name, text = string.format("%s sent an expedition into %s and hauled out scrap%s.",
      KC.name(fid), I and I.name or "the ruins", f.relic and " and ancient parts" or "") })
  elseif a == "trade_for" then
    KC.trade_for_do(fid, o, f.need_cat or "food")
  elseif a == "raid_surplus" then
    KC.raid_surplus_do(fid, o, f.need_cat or "food")
  elseif a == "waylay" then
    KC.waylay_do(fid, o)
  elseif a == "recruit" then
    f.wealth = f.wealth - U.recruit_cost; f.strength = f.strength + U.recruit_gain
  elseif a == "hide" then
    f.strength = f.strength * 1.02; f.wealth = f.wealth * 0.99
    KC.r2safe("lie_low", function()   -- REV2: затаились — патрули не выходят (Traces), отряды в бою с сильным отходят (Self)
      local was = f.low_until and KC.DAY < f.low_until
      f.low_until = KC.DAY + (KC.R2().low_days or 40)
      if not was and o and KC.S.F[o] and KC.DAY - (f.low_told or -1000) >= (KC.R2().low_tell_days or 120) then   -- в журнал не чаще раза в 120 дней на фракцию
        f.low_told = KC.DAY
        KC.S.stats.lie_low = (KC.S.stats.lie_low or 0) + 1
        KC.emit({ type = "lie_low", a = fid, b = o, text = string.format("%s keep their heads down and avoid %s.", KC.name(fid), KC.name(o)) })
      end
    end)
  end
end

-- измена: союзник бьёт ослабшего союзника, если выгода велика (редко, по амбиции)
function KC.maybe_betrayal(fid)
  local f = KC.S.F[fid]
  if f.ambition ~= "expansion" and f.ambition ~= "enrichment" then return end
  for _, e in ipairs(KC.allies_of(fid, { nonaggression = true, trade = true, defense = true })) do
    local o = e.other
    if KC.S.F[o].alive and not KC.S.F[o].player and KC.power(o) < 0.35 * KC.power(fid) and math.random() < (KC.P.utility.betrayal_chance or 0.03) then
      KC.break_treaty(e.t, "seized an opportunity", fid)
      KC.act(fid, "raid", o)
      return
    end
  end
end
end
if KC._BOOT then KC._BOOT() end
