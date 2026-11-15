-- KMM_Elite - элитная гвардия богатой фракции рядом с игроком (шаг 1 офлайн-билда, 2026-11-12)
-- Раз в несколько секунд (тик GameWorld::charsUpdate, guarded) проверяем: прошло >= min_years игровых лет, у игрока есть персонажи,
-- рядом (<= radius_max) город фракции, фракция жива, богата (wealth >= wealth_mult * wealth0) и знающая (know >= know_min, если поле есть),
-- кулдаун фракции и лимит живых отрядов. Тогда у её города появляется элитный отряд (шаблон из потока ELITE) и уходит в событие elite_seen.
-- Данные: kmm_elite_data.lua (tools/streams/elite.py). Ничего не делает при загрузке; ленивый старт после появления персонажей игрока.
-- Безотказность: первая ошибка функции отключает только её до конца сессии, причина -> logs/debug.log.

local TAG = "[KMM_Elite] "
local SQUAD_TYPE = 52   -- itemType.SQUAD_TEMPLATE
local DEBUG_LOG = "C:/KenshiModMap/logs/debug.log"

local DATA, C, P, SIDS
local DISABLED = {}
local last_spawn = {}        -- fid -> игровой день последнего спавна
local t_poll, spawn_clock = -1000, -1000
local stats = { spawned = 0 }

local function log(msg) msg = TAG .. tostring(msg); if not (KenshiLua and pcall(function() KenshiLua.log(msg) end)) then print(msg) end end
local function dlog(msg)
  local ok, f = pcall(io.open, DEBUG_LOG, "a")
  if ok and f then f:write(os.date("%Y-%m-%d %H:%M:%S"), " [KMM_Elite] ", tostring(msg), "\n"); f:close() end
  log(msg)
end
-- HEALTH (2026-11-15): отказ шага -> реестр ядра KMM_Gov (ключ KMM_Elite.<шаг>): пауза 1/5/30 мин и повтор, не «до перезапуска».
-- DISABLED — только навсегда (нет Gov: прежнее поведение). off(nm) — шаг сейчас не работает (выключен или на паузе).
local function HG() local g = rawget(_G, "KMM_Gov"); if type(g) == "table" and type(g.h_fail) == "function" then return g end end
local function off(nm)
  if DISABLED[nm] then return true end
  local g = HG(); if not g then return false end
  local ok, up = pcall(g.h_up, "KMM_Elite." .. nm)
  return ok and up == false
end
local function h_ok(nm) local g = HG(); if g then pcall(g.h_ok, "KMM_Elite." .. nm) end end
local function h_off(nm, why, kind) DISABLED[nm] = true; local g = HG(); if g and type(g.h_off) == "function" then pcall(g.h_off, "KMM_Elite." .. nm, why, kind) end end
local function fail(nm, err)   -- отказ шага: пауза в реестре (вернёт секунды), без Gov — до перезапуска (nil)
  local g, p = HG(), nil
  if g then local ok, r = pcall(g.h_fail, "KMM_Elite." .. nm, err); if ok then p = r end end
  if type(p) == "number" then dlog(nm .. " failed, retry in " .. p .. " s: " .. tostring(err)); return p end
  if not DISABLED[nm] then DISABLED[nm] = true; dlog(nm .. " disabled until restart: " .. tostring(err)) end
  return nil
end
local function guarded(nm, fn)
  return function(...)
    if off(nm) then return end
    local ok, err, r2, r3 = pcall(fn, ...)
    if not ok then fail(nm, err); return end
    h_ok(nm)
    return err, r2, r3
  end
end

local function xz(v) if v then return v.x or v[1], v.z or v[3], v.y or v[2] or 0 end end
local function pc_xz()   -- позиции всех персонажей игрока
  local out = {}
  pcall(function()
    for _, c in pairs(getPlayerInterface():getAllPlayerCharacters()) do
      local x, z = xz(c:getPosition()); if x then out[#out + 1] = { x, z } end
    end
  end)
  return out
end
local function player_pos()
  local ok, x, z, y = pcall(function()
    for _, c in pairs(getPlayerInterface():getAllPlayerCharacters()) do return xz(c:getPosition()) end
  end)
  if ok and x then return x, z, y end
end
local function dist(ax, az, bx, bz) return math.sqrt((ax - bx) ^ 2 + (az - bz) ^ 2) end

-- Точка спавна вне видимости: до КАЖДОГО персонажа игрока >= unseen_min (3500), до ближайшего <= unseen_max (6000). До 8 кандидатов у города
-- (250..600 от него); если город ближе unseen_min - кандидаты со стороны города, противоположной игроку; допустимой нет -> nil (отложить).
-- Проверки загруженности точки в KenshiLua нет (isLoaded/getHeight - методы объектов), только расстояние.
local function unseen_ok(x, z, pcs)
  if #pcs == 0 then return false end
  local mn, mx = (P and P.unseen_min) or 3500, (P and P.unseen_max) or 6000
  local near
  for _, p in ipairs(pcs) do
    local d = dist(x, z, p[1], p[2])
    if d < mn then return false end
    if not near or d < near then near = d end
  end
  return near <= mx
end
local function pick_point(town, pcs)
  local away
  if pcs[1] then
    local best
    for _, p in ipairs(pcs) do local d = dist(town.x, town.z, p[1], p[2]); if not best or d < best then best = d; away = math.atan2(town.z - p[2], town.x - p[1]) end end
  end
  for i = 1, 8 do
    local off = 250 + math.random() * 350
    local ang = math.random() * 2 * math.pi
    if i % 2 == 0 and away then ang = away + (math.random() - 0.5) * 1.6 end   -- чётные: от ближайшего персонажа игрока
    local x, z = town.x + off * math.cos(ang), town.z + off * math.sin(ang)
    if unseen_ok(x, z, pcs) then return x, z end
  end
end

local function load_data()
  local ok, d = pcall(require, "kmm_elite_data")
  if ok and type(d) == "table" then return d end
  for _, p in ipairs({ "C:/Program Files (x86)/Steam/steamapps/common/Kenshi/mods/KMM_Elite/scripts/kmm_elite_data.lua",
                       "C:/KenshiModMap/build/KMM_Elite/scripts/kmm_elite_data.lua" }) do
    local f = loadfile(p)
    if f then local ok2, d2 = pcall(f); if ok2 and type(d2) == "table" then return d2 end end
  end
end

local function init()
  if DATA then return true end
  C = KMM_Conductor
  if not (C and C.state and C.day and C.towns) then return false end
  local d = load_data()
  if not d then error("kmm_elite_data.lua not found") end
  DATA, P = d, d.params or {}
  SIDS = {}
  for _, u in pairs(d.units or {}) do SIDS[u.squad] = true end
  return true
end

-- живой элитный отряд: любой не мёртвый персонаж с нашим шаблоном отряда (или недавний спавн - персонажи ещё не в списке)
local function elite_alive()
  if os.clock() - spawn_clock < (P.alive_grace or 40) then return true end
  -- PERF2: общий снимок KMM_Gov (шаблон отряда кэшируется в записи); isDead у совпавшего проверяем вживую. Нет Gov / ошибка - прежний обход.
  local g = rawget(_G, "KMM_Gov")
  if g and g.snapshot and P.use_snapshot ~= false then
    local oks, snap = pcall(g.snapshot, P.snap_ttl or 4)
    if oks and type(snap) == "table" and snap.list then
      for _, r in ipairs(snap.list) do
        local sid = r.tsid
        if sid and SIDS[sid] then
          local okd, dead = pcall(r.ch.isDead, r.ch)
          if okd and not dead then return true end
        end
      end
      return false
    end
  end
  local set = getGameWorld():getCharacterUpdateList()
  for ch in pairs(set) do
    local ok, sid = pcall(function() local ap = ch:getPlatoon(); local pl = ap and ap.me; local t = pl and pl.squadTemplate; return t and t.stringID end)
    if ok and sid and SIDS[sid] then
      local okd, dead = pcall(function() return ch:isDead() end)
      if okd and not dead then return true end
    end
  end
  return false
end

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
local function spawn(fid, squad_sid, x, y, z, maxnum, target_town)
  local gw = getGameWorld()
  local fobj = gw.factionMgr:getFactionByStringID(fid)
  if not fobj then error("no faction object " .. tostring(fid)) end
  local gd = gw.gamedata:getData(squad_sid, SQUAD_TYPE)
  if not gd then error("no squad template " .. tostring(squad_sid)) end
  local nh = null_hand(); if nh == nil then error("no null hand") end
  return gw.theFactory:createRandomSquad(fobj, { x = x, y = y, z = z }, nil, maxnum or 5, nil, gd, nil, nil, nil, false,
                                         nh, target_town, 1.0, 2, false)
end

local function nearest_town_obj(fid, x, z)
  local ok, t = pcall(function()
    local f = getGameWorld().factionMgr:getFactionByStringID(fid)
    return f and f.warMgr and f.warMgr:getNearestTown({ x = x, y = 0, z = z })
  end)
  return ok and t or nil
end

-- LINKS2: элита берётся из склада города: полки брони и металла >= shelf_min нормы (нет данных склада - не мешаем, как раньше)
local function shelf_ok(t)
  local lv = t.lv
  if type(lv) ~= "table" or lv.armor == nil or lv.metal == nil then return true end
  local mn = P.shelf_min or 0.8
  return lv.armor >= mn and lv.metal >= mn
end
local function nearest_own_town(fid, px, pz, towns)
  local best, bd
  for _, t in ipairs(towns) do
    if t.owner == fid and t.x and shelf_ok(t) then
      local d = dist(px, pz, t.x, t.z)
      if not bd or d < bd then best, bd = t, d end
    end
  end
  return best, bd
end

local function eligible(fid, S, day)
  local f = S.F and S.F[fid]
  if not (f and f.alive) then return nil end
  local w0 = f.wealth0 or 0
  if w0 <= 0 or (f.wealth or 0) < (P.wealth_mult or 1.5) * w0 then return nil end
  if f.know ~= nil and f.know < (P.know_min or 1.5) then return nil end
  if last_spawn[fid] and day - last_spawn[fid] < (P.faction_cooldown_days or 20) then return nil end
  return (f.wealth or 0) / w0
end

local function try_spawn(px, pz, py)
  local day = C.day()
  if day < (P.min_years or 2) * (P.year_days or 360) then return false end
  local S = C.state()
  if not S then return false end
  local towns = C.towns()
  local cand
  for fid, u in pairs(DATA.units) do
    local r = eligible(fid, S, day)
    if r then
      local t, d = nearest_own_town(fid, px, pz, towns)
      if t and d <= (P.radius_max or 6000) and (not cand or r > cand.r) then cand = { fid = fid, u = u, t = t, r = r } end
    end
  end
  if not cand then return false end
  if elite_alive() then return false end
  local sx, sz = pick_point(cand.t, pc_xz())
  if not sx then stats.deferred = (stats.deferred or 0) + 1; return false end   -- нет допустимой точки вне видимости: позже, не ближе
  if math.random() > (P.chance or 0.1) then return false end
  spawn(cand.fid, cand.u.squad, sx, py, sz, P.squad_size or 5, nearest_town_obj(cand.fid, sx, sz))
  last_spawn[cand.fid] = day
  if type(C.stock_spend) == "function" and type(cand.t.lv) == "table" then   -- LINKS2: снаряжение отряда списывается с полок города
    local lo, hi = (P.shelf_spend or { 0.05, 0.08 })[1], (P.shelf_spend or { 0.05, 0.08 })[2]
    local okx, e1 = pcall(function() C.stock_spend(cand.t.sid, "armor", lo + (hi - lo) * math.random()); C.stock_spend(cand.t.sid, "metal", lo + (hi - lo) * math.random()) end)
    if not okx then dlog("stock_spend failed: " .. tostring(e1)) end
    stats.spent = (stats.spent or 0) + 1
  end
  spawn_clock = os.clock()
  stats.spawned = stats.spawned + 1
  C.emit({ type = "elite_seen", a = cand.fid, town_name = cand.t.name, town_sid = cand.t.sid, unit = cand.u.name })
  dlog(string.format("elite %s spawned near %s (wealth x%.2f, day %.0f)", tostring(cand.u.name), tostring(cand.t.name), cand.r, day))
  return true
end

local g_spawn = guarded("spawn", try_spawn)

-- NATIVE (2026-11-13): отряд - родной UNIQUE_SQUAD_TEMPLATE в FACTION."special squads" (движок сам спавнит и респавнит по replacement time).
-- Наш мозг - только богатство: открываем замок WORLD_EVENT_STATE (KMM_Native.ws_set) на gate_open_days дней; закрываем после. Нет плагина - старый спавн.
local open_day = {}   -- fid -> день открытия замка
local function native_on()
  if not (P and P.native_special ~= false) then return false end
  local N = rawget(_G, "KMM_Native")
  if not (N and N.ws_set and N.is_available) then return false end
  local ok, a = pcall(N.is_available)
  return ok and a == true
end
local function native_step(px, pz)
  local N = KMM_Native
  local day = C.day()
  local S = C.state()
  if not S then return false end
  local towns = C.towns()
  for fid, u in pairs(DATA.units) do
    if u.wes then
      local od = open_day[fid]
      if od then
        if day - od >= (P.gate_open_days or 2) then
          if N.ws_set(u.wes, false) then open_day[fid] = nil end
        end
      elseif day >= (P.min_years or 2) * (P.year_days or 360) then
        local r = eligible(fid, S, day)
        if r and math.random() <= (P.chance or 0.1) then
          local t = nearest_own_town(fid, px, pz, towns)
          if t and N.ws_set(u.wes, true) then
            open_day[fid] = day; last_spawn[fid] = day
            if type(C.stock_spend) == "function" and type(t.lv) == "table" then
              local lo, hi = (P.shelf_spend or { 0.05, 0.08 })[1], (P.shelf_spend or { 0.05, 0.08 })[2]
              local okx, e1 = pcall(function() C.stock_spend(t.sid, "armor", lo + (hi - lo) * math.random()); C.stock_spend(t.sid, "metal", lo + (hi - lo) * math.random()) end)
              if not okx then dlog("stock_spend failed: " .. tostring(e1)) end
              stats.spent = (stats.spent or 0) + 1
            end
            stats.opened = (stats.opened or 0) + 1
            C.emit({ type = "elite_seen", a = fid, town_name = t.name, town_sid = t.sid, unit = u.name })
            dlog(string.format("elite %s native gate open (%s, wealth x%.2f, day %.0f)", tostring(u.name), tostring(t.name), r, day))
          end
        end
      end
    end
  end
  return true
end
local g_native = guarded("native", native_step)

local function tick()
  local now = os.clock()
  if now - t_poll < (P and P.poll_seconds or 5) then return end
  t_poll = now
  local px, pz, py = player_pos()
  if not px then return end   -- нет персонажей игрока (меню, загрузка) - ничего
  if not init() then return end
  if native_on() then g_native(px, pz); return end
  if P.legacy_if_no_native ~= false then g_spawn(px, pz, py) end
end

if Events and Events.on then Events.on("GameWorld::charsUpdate", guarded("tick", function(...) if _G.KMM_Gov then return KMM_Gov.run("elite", tick, ...) else return tick(...) end end)) end

KMM_Elite = {
  stats = function() return stats end,
  disabled = function() return DISABLED end,
  last_spawn = function() return last_spawn end,
}
