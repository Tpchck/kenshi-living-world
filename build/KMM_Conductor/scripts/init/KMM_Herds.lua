-- KMM_Herds: экология дальнего мира. Стада кочуют по 4 точкам за цикл ~30 игровых дней, за ними с задержкой идут хищники, ещё позже охотники.
-- Дальний мир живёт в KMM_Conductor.state().ext.herds (≈1-2 КБ, старые сейвы создают лениво). Видимое игроку:
--   * рядом с маршрутом: стадо / отстающие хищники / охотники материализуются через KMM_Traces.request (лимит <= 3 живых групп, кулдауны);
--   * где прошло стадо (и особенно охотники) полки food/lux города растут -> мясо и шкуры дешевле (S.stock.towns[..].q, как делают модели Conductor);
--   * события herd_move / herd_pred / herd_hunt (cat = вид) уходят в хронику и слухи (KMM_Rumors показывает их, если в его пуле есть эти типы).
-- Данные: herds.json (tools/conductor/gen_herds.py). Всё под pcall; ошибка -> модуль выключается до перезапуска, одна строка в logs/herds.log.
-- Ограничение: Traces.request целится в ГОРОД (to_fid = фракция-владелец ближайшего города), не в произвольную точку; к точкам-руинам/нейтральным
-- владениям цели нет, стадо просто появляется с нужной стороны (from_x/from_z) и идёт по своему ИИ патруля.
-- R4 (2026-11-15): хищники по следу стада — сначала ЗАПАХ ЯДРА. Игрок у точки следа -> KMM_Predators.smell(SMELLMSG_CORPSE, туша за стадом)
-- в зоне точки: ванильные хищники биома (HUNTING_BLOODSMELL) приходят сами. Через smell_check_s сравниваем getGeneralSmellLevel зоны:
-- вырос -> «smell took», свой спавн не нужен; не вырос / API запаха нет -> свой спавн через Traces как фолбэк (маркер в herds.log).
-- Стада и охотники остаются своим спавном: маршрута миграции у ванильных биомных спавнов нет.
local LOG = "C:/KenshiModMap/logs/herds.log"
local DATA = "C:/KenshiModMap/build/KMM_Conductor/herds.json"

local H = { disabled = false, D = nil, last = -1e9, stats = { days = 0, ev = 0, glut = 0, req = 0, smell = 0, smell_took = 0, smell_fb = 0 },
            towns = nil, towns_day = nil, pend = {} }   -- pend: рантайм {[id стада] = {t, l0, x, z}} — запах поставлен, ждём проверки

local function log(msg)
  pcall(function() local f = io.open(LOG, "a"); if f then f:write(os.date("%Y-%m-%d %H:%M:%S"), " [KMM_Herds] ", tostring(msg), "\n"); f:close() end end)
end
-- HEALTH (2026-11-15): отказы идут в реестр ядра KMM_Gov (ключи KMM_Herds.<механика>): пауза 1/5/30 мин и повтор вместо «до перезапуска».
-- Навсегда — только нет API в движке (noapi) или крэш-сторож (crash). Без Gov — прежнее поведение (до перезапуска).
local function HG() local g = rawget(_G, "KMM_Gov"); if type(g) == "table" and type(g.h_fail) == "function" then return g end end
local function h_up(k) local g = HG(); if not g then return true end; local ok, r = pcall(g.h_up, k); return (not ok) or r ~= false end
local function h_ok(k) local g = HG(); if g then pcall(g.h_ok, k) end end
local function h_off(k, why, kind) local g = HG(); if g and type(g.h_off) == "function" then pcall(g.h_off, k, why, kind) end end
-- отказ: t[f] = true; пауза реестра -> t[f .. "_p"] = ключ, вернёт секунды; без Gov -> nil (до перезапуска)
local function down(t, f, key, err)
  t[f] = true
  local g, p = HG(), nil
  if g then local ok, r = pcall(g.h_fail, key, err); if ok then p = r end end
  if type(p) == "number" then t[f .. "_p"] = key; return p end
  t[f .. "_p"] = nil
  return nil
end
-- true = выключено сейчас; пауза истекла -> флаг снят (одна попытка)
local function live(t, f)
  if not t[f] then return false end
  local key = t[f .. "_p"]
  if key and h_up(key) then t[f], t[f .. "_p"] = false, nil; return false end
  return true
end
local function forever(t, f, key, why, kind) t[f], t[f .. "_p"] = true, nil; h_off(key, why, kind) end
local function why_p(p) return p and ("failed, retry in " .. p .. " s") or "disabled until restart" end
local function fail(where, err)
  local p = down(H, "disabled", "KMM_Herds.module", err)
  log((p and ("failed, retry in " .. p .. " s") or "disabled until restart") .. " (" .. where .. "): " .. tostring(err))
end

H.P_DEF = { cycle_days = 30, stay = 0.4, pred_delay = 4, hunt_delay = 9, near_r = 45000, max_live = 3, live_days = 1.0, cooldown_days = 3.0,
            global_cd_days = 0.5, tick_sec = 25, aim_town = true, smell_first = false, smell_check_s = 60, smell_eps = 0.0001, herd_size = { 8, 14 }, pred_size = { 4, 8 }, hunter_size = 4, max_events_day = 3,
            glut = { herd = { food = 0.08, lux = 0.03 }, hunt = { food = 0.2, lux = 0.1 }, cap = 1.6, range = 35000 } }

H.load = function()
  if H.D then return H.D end
  local C = rawget(_G, "KMM_Conductor")
  if not (C and C.read_json and C.state) then return nil end
  local d = C.read_json("herds.json", DATA)
  if type(d) ~= "table" or type(d.herds) ~= "table" or type(d.species) ~= "table" then error("herds.json missing/invalid") end
  local P = {}
  for k, v in pairs(H.P_DEF) do P[k] = v end
  for k, v in pairs(d.params or {}) do if type(v) ~= "string" then P[k] = v end end
  if type(P.glut) ~= "table" or not P.glut.herd then P.glut = H.P_DEF.glut end
  d.P = P
  H.D = d
  return d
end

H.slot = function()
  local C = rawget(_G, "KMM_Conductor")
  local S = C and C.state and C.state()
  if not S then return nil end
  S.ext = S.ext or {}
  local e = S.ext.herds
  if type(e) ~= "table" then e = { v = 1, h = {}, live = {}, gcd = -1e9, evd = -1, evn = 0 }; S.ext.herds = e end
  e.h = e.h or {}; e.live = e.live or {}
  return e
end

---------------------------------------------------------------------------------------------- геометрия маршрута
-- абсолютный номер сегмента a и доля f: стоит на точке a%N до доли stay, затем идёт к следующей
H.seg = function(h, day)
  local P, N = H.D.P, #h.route
  local t = (day + (h.off or 0)) / P.cycle_days * N
  local a = math.floor(t)
  return a, t - a
end
H.pos = function(h, day)
  local P, N = H.D.P, #h.route
  local a, f = H.seg(h, day)
  local w0 = h.route[(a % N) + 1]
  if f < P.stay then return w0.x, w0.z, w0, w0 end
  local w1 = h.route[((a + 1) % N) + 1]
  local g = (f - P.stay) / (1 - P.stay)
  return w0.x + (w1.x - w0.x) * g, w0.z + (w1.z - w0.z) * g, w0, w1
end
local function dist(ax, az, bx, bz) return math.sqrt((ax - bx) ^ 2 + (az - bz) ^ 2) end

H.town_list = function(day)
  local C = rawget(_G, "KMM_Conductor")
  local dk = math.floor(day)
  if H.towns_day ~= dk or not H.towns then H.towns = C.towns() or {}; H.towns_day = dk end
  return H.towns
end
H.nearest_town = function(x, z, day, only_stock)
  local best, bd
  for _, t in ipairs(H.town_list(day)) do
    if t.x and t.z and (not only_stock or t.lv) then
      local d = dist(x, z, t.x, t.z)
      if not bd or d < bd then best, bd = t, d end
    end
  end
  return best, bd
end

---------------------------------------------------------------------------------------------- события и последствия
H.emit = function(e, typ, cat, x, z, day, text)
  local C = rawget(_G, "KMM_Conductor")
  local dk = math.floor(day)
  if e.evd ~= dk then e.evd, e.evn = dk, 0 end
  if e.evn >= H.D.P.max_events_day then return end
  e.evn = e.evn + 1
  local t = H.nearest_town(x, z, day)
  C.emit({ type = typ, cat = cat, town_sid = t and t.sid, town_name = t and t.name, text = text })
  H.stats.ev = H.stats.ev + 1
end

H.glut = function(x, z, day, kind)   -- мясо и шкуры у ближайшего города со складом; через полку lv цену считает Conductor.price_mult_town
  local C = rawget(_G, "KMM_Conductor")
  local G = H.D.P.glut
  local t, d = H.nearest_town(x, z, day, true)
  if not t or d > G.range then return nil end
  local stock = C.stock_state and C.stock_state()
  local s = stock and stock.towns and stock.towns[t.sid]
  if not (s and s.q and s.tn) then return nil end
  local sh = G[kind] or G.herd
  s.lv = s.lv or {}
  for cat, share in pairs(sh) do
    local tn = s.tn[cat]
    if tn and tn > 0 and s.q[cat] then
      local top = G.cap * tn
      if s.q[cat] < top then s.q[cat] = math.min(top, s.q[cat] + share * tn); s.lv[cat] = s.q[cat] / tn end
    end
  end
  H.stats.glut = H.stats.glut + 1
  return t
end

H.daily = function(day)
  local e = H.slot()
  if not e then return end
  local D = H.D
  local P = D.P
  local first = (e.day == nil)
  e.day = math.floor(day)
  H.stats.days = H.stats.days + 1
  for _, h in ipairs(D.herds) do
    local sp = D.species[h.species]
    if sp then
      local st = e.h[h.id]
      local fresh = (st == nil)
      if fresh then st = {}; e.h[h.id] = st end
      local a, f = H.seg(h, day)
      local N = #h.route
      local w0, w1 = h.route[(a % N) + 1], h.route[((a + 1) % N) + 1]
      -- стадо: отправление (событие) и прибытие (последствия)
      if f >= P.stay then
        if st.dep ~= a then
          if not fresh then H.emit(e, "herd_move", h.species, w0.x, w0.z, day, string.format("%s herds are leaving %s for %s.", sp.label, w0.name, w1.name)) end
          st.dep = a
        end
      elseif st.arr ~= a then
        if not fresh then
          local t = H.glut(w0.x, w0.z, day, "herd")
          if t then H.emit(e, "herd_glut", h.species, w0.x, w0.z, day, string.format("%s herds passed near %s: game meat and hides are cheaper.", sp.label, t.name)) end
        end
        st.arr = a
      end
      -- хищники: та же геометрия со сдвигом назад
      local ps = h.pred and D.species[h.pred]
      if ps then
        local pa, pf = H.seg(h, day - P.pred_delay)
        local pw0, pw1 = h.route[(pa % N) + 1], h.route[((pa + 1) % N) + 1]
        if pf >= P.stay and st.pdep ~= pa then
          if not fresh and st.pdep ~= nil then H.emit(e, "herd_pred", h.pred, pw0.x, pw0.z, day, string.format("%s trail the %s herds toward %s.", ps.label, sp.label, pw1.name)) end
          st.pdep = pa
        end
      end
      -- охотники: ещё позже; приход охотников в точку — большая добыча
      if D.hunters and #D.hunters > 0 then
        local ha, hf = H.seg(h, day - P.hunt_delay)
        local hw0, hw1 = h.route[(ha % N) + 1], h.route[((ha + 1) % N) + 1]
        if hf >= P.stay and st.hdep ~= ha then
          if not fresh and st.hdep ~= nil then H.emit(e, "herd_hunt", h.species, hw0.x, hw0.z, day, string.format("Hunters follow the %s herds toward %s.", sp.label, hw1.name)) end
          st.hdep = ha
        elseif hf < P.stay and st.harr ~= ha then
          if not fresh and st.harr ~= nil then
            local t = H.glut(hw0.x, hw0.z, day, "hunt")
            if t then H.emit(e, "herd_glut", h.species, hw0.x, hw0.z, day, string.format("Hunters brought %s meat and hides to %s: prices fell.", sp.label, t.name)) end
          end
          st.harr = ha
        end
      end
    end
  end
  -- чистим живые группы по сроку
  local keep = {}
  for _, l in ipairs(e.live) do if l.d > day then keep[#keep + 1] = l end end
  e.live = keep
end

---------------------------------------------------------------------------------------------- материализация рядом с игроком
H.pick_sq = function(sp, lo, hi)
  local lst = sp.squads
  if not lst or #lst == 0 then return nil end
  local q = lst[math.random(math.min(#lst, 6))]
  local n = math.random(lo, hi)
  if q.max and q.max > 0 then n = math.max(q.min or 1, math.min(n, q.max)) end
  return q.sid, n
end

H.request = function(e, day, tag, h, fid, sid, size, x, z, role)
  local T = rawget(_G, "KMM_Traces")
  local P = H.D.P
  local N = #h.route
  local fx, fz = H.pos(h, day - 1.5 - (role == "pred" and P.pred_delay or (role == "hunt" and P.hunt_delay or 0)))
  local a, f = H.seg(h, day - (role == "pred" and P.pred_delay or (role == "hunt" and P.hunt_delay or 0)))
  local nx = h.route[((a + (f >= P.stay and 1 or 0)) % N) + 1]
  local to_fid
  if P.aim_town and role ~= "hunt" then
    local t = H.nearest_town(nx.x, nx.z, day)
    if t and t.owner and dist(t.x, t.z, nx.x, nx.z) < 20000 then to_fid = t.owner end
  end
  local job = { tag = tag, fid = fid, sid = sid, shift = role == "hunt" and 0 or nil, n = 1, size = size, from_x = fx, from_z = fz,
                to_fid = to_fid, to_x = nx.x, to_z = nx.z, target = "player" }
  if role == "hunt" then job.target = nil end
  local ok = T.request(job)
  if ok then
    e.live[#e.live + 1] = { d = day + H.D.P.live_days, id = h.id, r = role }
    local cdk = "cd_" .. role
    e.h[h.id] = e.h[h.id] or {}
    e.h[h.id][cdk] = day
    e.gcd = day
    H.stats.req = H.stats.req + 1
  end
  return ok
end

-- R4: запах ядра вместо своего спавна хищников. -> "wait" (ждём/не время), "took" (ядро сработало), строка-причина фолбэка, nil (выкл)
H.pred_smell = function(e, day, h, st, ps, x, z)
  local P = H.D.P
  if not P.smell_first then return nil end
  local Pr = rawget(_G, "KMM_Predators")
  if not (Pr and Pr.smell and Pr.smell_level) or (Pr.disabled and Pr.disabled()) then return "no smell api" end
  local now = os.clock()
  local pd = H.pend[h.id]
  if pd and now - pd.t > P.smell_check_s * 10 then H.pend[h.id] = nil; pd = nil end   -- игрок уходил: проверка устарела
  if pd then
    if now - pd.t < P.smell_check_s then return "wait" end
    H.pend[h.id] = nil
    local l1 = Pr.smell_level(pd.x, pd.z)
    local lv = string.format("lvl %s->%s", pd.l0 and string.format("%.3f", pd.l0) or "?", l1 and string.format("%.3f", l1) or "?")
    if l1 and l1 > (pd.l0 or 0) + P.smell_eps then
      st.cd_pred = day; e.gcd = day
      H.stats.smell_took = H.stats.smell_took + 1
      log(string.format("smell took: %s pred trail (%s), no spawn", tostring(h.id), lv))
      return "took"
    end
    return "no effect " .. lv
  end
  local ok, l0, why = Pr.smell(x, z, "corpse", ps.fid, "herd trail " .. tostring(h.id))
  if ok then
    H.pend[h.id] = { t = now, l0 = l0, x = x, z = z }
    H.stats.smell = H.stats.smell + 1
    log(string.format("smell: %s pred trail at %d,%d lvl0=%s, check in %ds", tostring(h.id), math.floor(x), math.floor(z),
        l0 and string.format("%.3f", l0) or "?", P.smell_check_s))
    return "wait"
  end
  if why == "off" or why == "api" or why == "no zone" then return "smell " .. tostring(why) end
  return "wait"   -- далеко от зоны точки / кулдаун / потолок дня: ждём, пока игрок подойдёт
end

H.materialize = function(day)
  local T = rawget(_G, "KMM_Traces")
  if not (T and T.request and T.near) then return end
  local e = H.slot()
  if not e then return end
  local D = H.D
  local P = D.P
  if #e.live >= P.max_live or day - (e.gcd or -1e9) < P.global_cd_days then return end
  for _, h in ipairs(D.herds) do
    local sp = D.species[h.species]
    local st = e.h[h.id]
    if sp and st then
      -- стадо
      local x, z = H.pos(h, day)
      if day - (st.cd_herd or -1e9) >= P.cooldown_days and T.near(x, z, P.near_r) then
        local sid, n = H.pick_sq(sp, P.herd_size[1], P.herd_size[2])
        if sid and H.request(e, day, "herd", h, sp.fid, sid, n, x, z, "herd") then return end
      end
      -- отставшие хищники: 2026-11-16 off with KMM_Predators (playtest: predators are vanilla nests and patrols only;
      -- a Symbiosis pack spawned 5471 from the player knocked the squad out 40 s later). P.pred_spawn = true brings it back.
      local ps = P.pred_spawn == true and h.pred and D.species[h.pred]
      if ps then
        local px, pz = H.pos(h, day - P.pred_delay)
        if day - (st.cd_pred or -1e9) >= P.cooldown_days and T.near(px, pz, P.near_r) then
          local r = H.pred_smell(e, day, h, st, ps, px, pz)
          if r == "wait" or r == "took" then return end
          local sid, n = H.pick_sq(ps, P.pred_size[1], P.pred_size[2])
          if sid and H.request(e, day, "herd_pred", h, ps.fid, sid, n, px, pz, "pred") then
            if r then H.stats.smell_fb = H.stats.smell_fb + 1; log(string.format("smell fallback spawn: %s pred trail (%s)", tostring(h.id), r)) end
            return
          end
        end
      end
      -- охотники
      if D.hunters and #D.hunters > 0 then
        local hx, hz = H.pos(h, day - P.hunt_delay)
        if day - (st.cd_hunt or -1e9) >= P.cooldown_days and T.near(hx, hz, P.near_r) then
          local fid = D.hunters[math.random(#D.hunters)]
          if H.request(e, day, "herd_hunt", h, fid, nil, P.hunter_size, hx, hz, "hunt") then return end
        end
      end
    end
  end
end

---------------------------------------------------------------------------------------------- тик
H.tick = function()
  if live(H, "disabled") then return end
  local now = os.clock()
  local P = (H.D and H.D.P) or H.P_DEF
  if now - H.last < P.tick_sec then return end
  H.last = now
  local ok, err = pcall(function()
    local C = rawget(_G, "KMM_Conductor")
    if not (C and C.day and C.state and C.state()) then return end   -- дирижёр ещё не поднялся: ленивый старт
    if not H.load() then return end
    local day = C.day()
    if type(day) ~= "number" or day < 0 then return end
    local e = H.slot()
    if not e then return end
    if e.day ~= math.floor(day) then H.daily(day) end
    H.materialize(day)
  end)
  if not ok then fail("tick", err) else h_ok("KMM_Herds.module") end
end

local function guarded(nm, fn)
  return function(...)
    if live(H, "disabled") then return end
    local ok, err = pcall(fn, ...)
    if not ok then fail(nm, err) end
  end
end
if Events and Events.on then Events.on("GameWorld::charsUpdate", guarded("tick", function() H.tick() end)) end

KMM_Herds = {
  tick = function() H.tick() end,
  _daily = function(day) local ok, err = pcall(function() H.load(); H.daily(day) end); if not ok then fail("daily", err) end end,
  _materialize = function(day) local ok, err = pcall(function() H.load(); H.materialize(day) end); if not ok then fail("mat", err) end end,
  pos = function(id, day) if not H.D then return nil end for _, h in ipairs(H.D.herds) do if h.id == id then return H.pos(h, day) end end end,
  data = function() return H.D end,
  stats = function() return H.stats end,
  disabled = function() return H.disabled end,
  reset = function() H.D, H.towns, H.disabled, H.last, H.pend = nil, nil, false, -1e9, {} end,
  pend = function() return H.pend end,
}

-- PUBLISH (2026-11-16): KenshiLua runs each init script in its own sandbox; a plain global stays inside it.
if KMM_Herds ~= nil then rawset(_G, "KMM_Herds", KMM_Herds) end
