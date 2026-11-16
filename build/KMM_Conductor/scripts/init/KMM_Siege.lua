-- KMM_Siege - осады городов (2026-11-13, "живой мир"). Часть атак дирижёра на город превращается в осаду на 3..7 игровых дней.
-- Дальний мир: S.ext.siege в состоянии дирижёра (сохраняется в сейв; только числа/строки/таблицы; старые сейвы создают слот лениво).
-- Склад города: native-поля модели KMM_Stock s.siege/s.cut (производство x0.4, рынок и караваны закрыты) + доп. убыль еды/лекарств.
-- Торговые караваны: дирижёр выбирает в плане самый голодный склад - осаждённый город был бы целью №1, поэтому идущие туда
--   записи ROADS (road_state().tr) разворачиваются обратно к источнику (груз зачтётся там).
-- Исход: штурм (город переходит осаждающему - состояние дирижёра правится так же, как act("capture"), + событие town_captured) или отход.
-- Видимое: игрок рядом с городом -> KMM_Traces.request: отряды осаждающих (приход со стороны их фракции) и патруль защитников.
-- Лимиты: <= 2 осады в мире, кулдаун города 30 дн, один осаждающий - одна осада, города игрока не трогаем, столицу не берём штурмом.
-- Безотказность: всё под pcall, первая ошибка отключает модуль до перезапуска (строка в logs/siege.log). Работы на старте нет.
-- Q4 (2026-11-15): осада = родная кампания движка. Запуск путём дирижёра (C.camp(): CA.pick/CA.fire/CA.note -> FactionWarMgr:triggerCampaign [2],
--   только рядом с игроком), привязка к новому CampaignInstance в warMgr.activeCampaigns осаждающего (uniqueID, enemy = защитник),
--   исход из currentPhase (Phase: VICTORY 3 -> город пал, RETREATING 2 -> осада снята, ASSAULT_2_HAPPY 4 -> откуп; исчезла -> по последней фазе).
--   Пока кампания жива, своих отрядов Traces не ставим (на поле силы движка). Кампания недоступна -> прежний бросок силы (маркер "fallback roll").
local M = rawget(_G, "KMM_Siege") or {}
_G.KMM_Siege = M
M.cfg = M.cfg or {
  enabled = true,
  max_active = 2, cooldown = 30, min_days = 3, max_days = 7,
  start_chance = 0.35,       -- доля подходящих атак (raid / attack_repelled), ставшая осадой
  food_drain = 0.05, med_drain = 0.03, weapons_drain = 0.02,   -- доля нормы склада в сутки
  defender_mult = 1.2, hunger_bonus = 0.5, storm_ratio = 1.0,  -- штурм удаётся, если сила осады >= storm_ratio * сила защиты
  vis_radius = 70000, atk_squads = 2, def_squads = 1, squad_size = 5, storm_squads = 3,
  progress_every = 2, native_alarm = false, alarm_pulse = 30, sdir = "C:/KenshiModMap/state/",
  log = "C:/KenshiModMap/logs/siege.log",
  native = true,     -- осада через родную кампанию; false = только своя модель (бросок)
  camp_tries = 3,    -- попыток запуска на осаду (по дням, когда игрок рядом с городом)
  camp_radius = nil, -- «игрок рядом» для запуска; nil = load_radius дирижёра (params.campaign)
  bind_days = 2,     -- дней ждать появления CampaignInstance после запуска (перегрузка [2] ставит в очередь), иначе фолбэк
  camp_max = 20,     -- предел осады с живой кампанией (дней от начала), потом осаждающий отходит
}
local CF = M.cfg
local OFF, SUB, LASTCLK, LOGGED = false, nil, 0, 0

local function log(msg)
  pcall(function()
    local f = io.open(CF.log, "a")
    if f then f:write(os.date("%Y-%m-%d %H:%M:%S"), " [KMM_Siege] ", tostring(msg), "\n"); f:close() end
  end)
end
local function C() return rawget(_G, "KMM_Conductor") end
-- HEALTH (2026-11-15): отказы идут в реестр ядра KMM_Gov (ключи KMM_Siege.<механика>): пауза 1/5/30 мин и повтор вместо «до перезапуска».
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
local ST = { off = false }   -- HEALTH: OFF = ST.off (пауза реестра или навсегда без Gov)
local function is_off() OFF = live(ST, "off"); return OFF end
local function mod_fail(nm, e) local p = down(ST, "off", "KMM_Siege.module", e); OFF = true; log(nm .. " " .. why_p(p) .. ": " .. tostring(e)) end
local function guard(nm, fn, ...)
  if is_off() then return nil end
  local ok, a, b = pcall(fn, ...)
  if not ok then mod_fail(nm, a); return nil end
  h_ok("KMM_Siege.module")
  return a, b
end

-- слот состояния (ленивый)
function M.slot()
  local c = C(); local S = c and c.state()
  if not S then return nil end
  S.ext = S.ext or {}
  local x = S.ext.siege
  if type(x) ~= "table" then x = { v = 1, active = {}, cd = {}, last = -1, n = 0, storms = 0, lifted = 0 }; S.ext.siege = x end
  x.active = x.active or {}; x.cd = x.cd or {}
  return x
end
function M.state() return M.slot() end
function M.disabled() return is_off() end

local function count(t) local n = 0; for _ in pairs(t) do n = n + 1 end; return n end
local function sorted_keys(t) local k = {}; for key in pairs(t) do k[#k + 1] = key end; table.sort(k, function(a, b) return tostring(a) < tostring(b) end); return k end
local function tinfo(sid)
  for _, t in ipairs(C().towns()) do if t.sid == sid then return t end end
end
local function stock_of(sid)
  local st = C().stock_state()
  return st and st.towns and st.towns[sid]
end
local function nm(fid) return C().name(fid) or tostring(fid) end

-- крэш-сторож нативного вызова (pcall не ловит нативный краш): lock до первого вызова; lock при старте = прошлый вызов упал -> .off навсегда
local PROBE = {}
local function probe_ok(k)
  if PROBE[k] == nil then
    local st = true
    pcall(function()
      local lock, offp = CF.sdir .. "probe_" .. k .. ".lock", CF.sdir .. "probe_" .. k .. ".off"
      local f = io.open(offp, "r")
      if f then f:close(); st = false; return end
      f = io.open(lock, "r")
      if f then
        f:close(); st = false
        local o = io.open(offp, "w"); if o then o:write("disabled: previous session crashed in ", k); o:close() end
        os.remove(lock); log("native " .. k .. " DISABLED forever: previous session crashed in the call")
      end
    end)
    PROBE[k] = st
  end
  return PROBE[k]
end
local function probe_call(k, fn)
  if not probe_ok(k) then return false end
  local lock = CF.sdir .. "probe_" .. k .. ".lock"
  local first = not PROBE[k .. "#done"]
  if first then pcall(function() local f = io.open(lock, "w"); if f then f:write(tostring(os.time())); f:close() end end) end
  local ok, r = pcall(fn)
  if first then pcall(os.remove, lock); PROBE[k .. "#done"] = true end
  return ok, r
end

-- родная тревога города (TownBase.setAlarmState [L:13666], enum TownAlarmState ALARM_NONE=0/ALARM_ATTACK=3): жители прячутся, стража по местам, лавки закрываются как в ванили.
-- Город достаём через FactionWarMgr.myTowns владельца (только загруженные отдают живой объект); sid сверяем по data.stringID.
local function find_town(sid, fid)
  local gw = getGameWorld()
  local fo = gw.factionMgr:getFactionByStringID(fid)
  local list = fo and fo.warMgr and fo.warMgr.myTowns
  if not list then return nil end
  for _, t in pairs(list) do
    local ok, gd = pcall(function() return t.data or t:getGameData() end)   -- RootObjectBase.data [L:11860] / getGameData [L:11870]; у TownBase нет getData
    if ok and gd and gd.stringID == sid then return t end
  end
end
local function set_alarm(s, on)
  if not CF.native_alarm then return false end
  local T = rawget(_G, "KMM_Traces")
  local t0 = tinfo(s.town)
  if not (T and T.near and t0 and t0.x and T.near(t0.x, t0.z, CF.vis_radius)) then return false end
  local ok, done = probe_call("setAlarmState", function()
    local t = find_town(s.town, s.b)
    if not t then return false end
    local E = rawget(_G, "TownAlarmState")
    local v = on and ((E and E.ALARM_ATTACK) or 3) or ((E and E.ALARM_NONE) or 0)
    t:setAlarmState(v)
    return true
  end)
  if ok and done then s.alarm = on and true or nil; return true end
  return false
end
function M.alarm_pulse(now)   -- родная тревога сбрасывается ванилью сама; поддерживаем, пока осада идёт и город загружен
  local x = M.slot()
  if not x then return end
  for _, key in ipairs(sorted_keys(x.active)) do
    local s = x.active[key]
    if s and (s.apulse or 0) + CF.alarm_pulse <= now then s.apulse = now; set_alarm(s, true) end
  end
end

-- выбор города b для осады со стороны a
local function pick_town(a, b, hint)
  local c = C()
  local ax, az = c.fpos(a)
  local best, bd
  for _, t in ipairs(c.towns()) do
    if t.owner == b and t.kind == "city" and t.x then
      local d = (t.sid == hint) and -1 or (ax and math.sqrt((t.x - ax) ^ 2 + (t.z - az) ^ 2) or 0)
      if not bd or d < bd then best, bd = t, d end
    end
  end
  return best
end

-- ===== Q4: родная кампания осады (FactionWarMgr / CampaignInstance) =====
-- s.nat: nil (не запускали) | "fired" (запущена, ждём экземпляр) | "bound" (s.cid = uniqueID) | "lost" (недоступна -> фолбэк)
local PH = { GATHERING = 0, ASSAULTING = 1, RETREATING = 2, VICTORY = 3, ASSAULT_2_HAPPY = 4, ASSAULT_2_ANGRY = 5 }
local PHN = {}; for k, v in pairs(PH) do PHN[v] = k end
M.PH = PH
local function camp_api()   -- путь дирижёра (L2.camp); nil, если ядро кампаний выключено
  local c = C()
  local ok, CA = pcall(function() return c.camp and c.camp() end)
  if not (ok and type(CA) == "table" and CA.fire and CA.pick and CA.data and CA.near_player and CA.home_pos) then return nil, "no conductor campaign api" end
  local off = CA.OFF
  if type(CA.off_now) == "function" then local okn, v = pcall(CA.off_now); if okn then off = v end end   -- HEALTH: пауза реестра, а не навсегда
  if off or (CA.PROBE and CA.PROBE["triggerCampaign"] == false) then return nil, "triggerCampaign disabled" end
  local G = CA.CP and CA.CP() or {}
  if G.enabled == false then return nil, "params.campaign.enabled=false" end
  return CA, G
end
local function warmgr(fid)
  local fo = getGameWorld().factionMgr:getFactionByStringID(fid)
  return fo and fo.warMgr, fo
end
local function phase_num(v)
  if type(v) == "number" then return v end
  local n = tonumber(v)
  if n then return n end
  local E = rawget(_G, "Phase")
  if type(E) == "table" then for k, ev in pairs(E) do if ev == v and PH[k] then return PH[k] end end end
  return nil
end
-- активные кампании фракции: { {id, ph, enemy, mp}... } (lektor: # и индекс; в тестах - Lua-таблица)
local function camps_of(fid)
  local wm = warmgr(fid)
  local l = wm and wm.activeCampaigns
  local out = {}
  if not l then return out end
  for i = 1, #l do
    local inst = l[i]
    if inst then
      local en = inst.enemy
      local esid = en and ((en.data and en.data.stringID) or en.id)
      out[#out + 1] = { id = inst.uniqueID, ph = phase_num(inst.currentPhase), enemy = esid, mp = inst.manPowerLastCount }
    end
  end
  return out
end
M.camps_of = camps_of
local function claimed(x, id, me)
  for _, o in pairs(x.active) do if o ~= me and o.cid == id then return true end end
end
-- запуск: тот же путь, что CA.try дирижёра (pick/fire/note, лимиты мира), но без его броска: осада уже решена
local function camp_launch(s, day, x)
  local CA, G = camp_api()
  if not CA then s.nwhy = G; return false end
  local t = tinfo(s.town)
  if not (t and t.x) then s.nwhy = "town has no coords"; return false end
  local R = CF.camp_radius or G.load_radius or 15000
  if not CA.near_player(t.x, t.z, R) then s.nwhy = "player far"; return false end   -- незагруженная зона: поведение очереди не проверено
  s.ctries = (s.ctries or 0) + 1
  if not (CA.data() and CA.data().factions[s.a]) then s.nwhy = "no FACTION_CAMPAIGN for attacker"; s.ctries = 99; return false end
  if CA.limits_ok and not CA.limits_ok(s.a) then s.nwhy = "campaign limits"; return false end
  local sid = CA.pick(s.a, { "assault", "raid" }, G.max_forces or 30)
  if not sid then s.nwhy = "no usable campaign"; s.ctries = 99; return false end
  local wa, wb = warmgr(s.a), warmgr(s.b)
  if not (wa and wb) then s.nwhy = "no warMgr"; return false end
  local target = wb:getNearestTown({ x = t.x, y = 0, z = t.z })
  local home = wa:getNearestTown(CA.home_pos(s.a, t.x, t.z))
  if not (target and home) then s.nwhy = "no target/home town"; return false end
  local pre = {}
  for _, e in ipairs(camps_of(s.a)) do if e.id then pre[#pre + 1] = e.id end end
  if not CA.fire(s.a, sid, target, home) then s.nwhy = "triggerCampaign failed"; return false end
  if CA.note then CA.note(s.a) end
  s.nat, s.fday, s.csid, s.cpre = "fired", day, sid, pre
  x.fired = (x.fired or 0) + 1
  log(string.format("campaign fired %s -> %s (%s) %s day %s", s.a, s.b, s.town, sid, day))
  return true
end
-- опрос: привязка к экземпляру и чтение фазы; возвращает исход ("storm" | "withdraw" | "tribute" | "ended") или nil
local function camp_poll(s, day, x)
  local list = camps_of(s.a)
  if s.nat == "fired" then
    local pre = {}; for _, id in ipairs(s.cpre or {}) do pre[id] = true end
    for _, e in ipairs(list) do
      if e.id and not pre[e.id] and (e.enemy == nil or e.enemy == s.b) and not claimed(x, e.id, s) then
        s.nat, s.cid, s.ph, s.mp = "bound", e.id, e.ph, e.mp
        x.native = (x.native or 0) + 1
        log(string.format("campaign bound %s id=%s phase=%s men=%s", s.town, tostring(e.id), tostring(PHN[e.ph or -1] or e.ph), tostring(e.mp)))
        break
      end
    end
    if s.nat == "fired" then
      if day - (s.fday or day) > (CF.bind_days or 2) then
        s.nat, s.nwhy = "lost", "campaign never started (queue/world state)"
        log("campaign not started " .. s.town .. " -> fallback roll later")
      end
      return nil
    end
  end
  if s.nat ~= "bound" then return nil end
  local cur
  for _, e in ipairs(list) do if e.id == s.cid then cur = e; break end end
  if not cur then   -- кампания закончилась (endCampaign): исход по последней виденной фазе
    log(string.format("campaign gone %s last phase=%s", s.town, tostring(PHN[s.ph or -1] or s.ph)))
    if s.ph == PH.VICTORY then return "storm" elseif s.ph == PH.ASSAULT_2_HAPPY then return "tribute" elseif s.ph == PH.RETREATING then return "withdraw" end
    return "ended"
  end
  if cur.ph ~= s.ph then log(string.format("phase %s %s -> %s men=%s", s.town, tostring(PHN[s.ph or -1] or s.ph), tostring(PHN[cur.ph or -1] or cur.ph), tostring(cur.mp))) end
  s.ph, s.mp = cur.ph, cur.mp
  if s.ph == PH.VICTORY then return "storm" end
  if s.ph == PH.RETREATING then return "withdraw" end
  if s.ph == PH.ASSAULT_2_HAPPY then return "tribute" end
  return nil
end
local finish
-- шаг кампании для осады: запуск (если ещё нет) / опрос; true = осада завершена исходом кампании. Сбой движка -> фолбэк, модуль живёт.
local function camp_step(s, day, x)
  if CF.native == false or s.nat == "lost" then return false end
  local ok, how = pcall(function()
    if s.nat == nil then
      if (s.ctries or 0) >= (CF.camp_tries or 3) then return nil end
      if not camp_launch(s, day, x) then return nil end
    end
    return camp_poll(s, day, x)
  end)
  if not ok then
    s.nat, s.nwhy = "lost", "engine error: " .. tostring(how)
    log("campaign error " .. s.town .. " -> fallback roll: " .. tostring(how))
    return false
  end
  if not how then return false end
  log(string.format("outcome from campaign %s: %s (phase %s)", s.town, how, tostring(PHN[s.ph or -1] or s.ph)))
  finish(s, day, how, x)
  return true
end
M.camp_step = camp_step

function M.begin(a, b, hint, day, native)
  local c, x = C(), M.slot()
  local S = c.state()
  local pf = c.cfg().player_faction
  if not (x and S and a and b and a ~= b) or a == pf or b == pf then return false end
  local fa, fb = S.F[a], S.F[b]
  if not (fa and fb and fa.alive and fb.alive) or fa.player or fb.player then return false end
  if count(x.active) >= CF.max_active then return false end
  for _, s in pairs(x.active) do if s.a == a then return false end end
  local t = pick_town(a, b, hint)
  if not t or x.active[t.sid] or (x.cd[t.sid] or -1) > day then return false end
  local days = math.random(CF.min_days, CF.max_days)
  local s = { a = a, b = b, town = t.sid, tname = t.name, day0 = day, day_end = day + days,
              pa = c.power(a), pd = c.power(b) * CF.defender_mult, prog = -1, vis = -1 }
  if native and CF.native ~= false then s.nat, s.fday, s.cpre = "fired", day, {} end   -- дирижёр уже запустил родную кампанию этой пары сегодня: привязываемся к ней
  x.active[t.sid] = s; x.n = (x.n or 0) + 1
  c.emit({ type = "siege_started", a = a, b = b, town_sid = t.sid, town_name = t.name, days = days,
           text = string.format("%s laid siege to %s (%s). Expected to last about %d days.", nm(a), t.name, nm(b), days) })
  log(string.format("start %s -> %s (%s) day %s..%s pa=%.0f pd=%.0f", a, b, t.sid, day, s.day_end, s.pa, s.pd))
  return true
end

-- итог: штурм или отход. how: storm | withdraw (родная RETREATING или бросок) | tribute | ended | stalled | dead | peace
local LIFT_TXT = {
  withdraw = "%s lifted the siege of %s and pulled back.",
  tribute = "%s took tribute from %s and lifted the siege.",
  ended = "The host of %s broke up before %s; the siege is over.",
  stalled = "%s gave up the long siege of %s.",
  sacked = "%s broke into %s, sacked it and marched off.",
}
local function cap_guard(s)   -- столицу и последний город штурмом не берём (и при VICTORY кампании: тогда разграбление)
  local c = C(); local fb = c.state().F[s.b]
  local cap = c.cfg().factions[s.b] and c.cfg().factions[s.b].capital
  return fb and s.town ~= cap and count(fb.towns) > 1
end
finish = function(s, day, how, x)
  local c = C(); local S = c.state()
  local F = S.F
  local nat = s.nat == "bound" or nil
  if how == "storm" and nat and not cap_guard(s) then how = "sacked" end
  x.active[s.town] = nil
  x.cd[s.town] = day + CF.cooldown
  local fa, fb = F[s.a], F[s.b]
  if s.alarm then set_alarm(s, false) end
  if how == "storm" and fa and fb and fb.towns[s.town] then
    x.storms = (x.storms or 0) + 1
    local txt = string.format("After %d days of siege %s stormed %s and took it from %s.", day - s.day0, nm(s.a), s.tname, nm(s.b))
    if c.capture_town then
      c.capture_town(s.a, s.b, s.town, { siege = true, str_a = 0.9, str_b = 0.85, rel = -15, text = txt })
    else   -- запасной путь: ядро без capture_town
      fb.towns[s.town] = nil; fa.towns[s.town] = true
      fa.unrest = fa.unrest or {}; fa.unrest[s.town] = { level = 1.0, prev = s.b }
      S.stats.captures = (S.stats.captures or 0) + 1
      fa.strength = fa.strength * 0.9; fb.strength = fb.strength * 0.85
      c.add_rel(s.a, s.b, -15)
      c.emit({ type = "town_captured", a = s.a, b = s.b, town_sid = s.town, town_name = s.tname, siege = true, native = nat, text = txt })
    end
    log("storm " .. s.town)
  else
    if fa then fa.strength = fa.strength * 0.93 end
    x.lifted = (x.lifted or 0) + 1
    c.emit({ type = "siege_lifted", a = s.a, b = s.b, town_sid = s.town, town_name = s.tname, why = how, native = nat,
             text = string.format(LIFT_TXT[how] or LIFT_TXT.withdraw, nm(s.a), s.tname) })
    log("lifted " .. s.town .. " " .. tostring(how))
  end
end

local function visible(s, day)
  local T = rawget(_G, "KMM_Traces")
  if not (T and T.request and T.near) or s.vis >= day then return end
  local c = C()
  local t = tinfo(s.town)
  if not (t and t.x and T.near(t.x, t.z, CF.vis_radius)) then return end
  s.vis = day
  s.apulse = os.clock(); set_alarm(s, true)
  if s.nat == "fired" or s.nat == "bound" then return end   -- на поле силы родной кампании: своих отрядов не ставим
  local ax, az = c.fpos(s.a)
  local storm = day >= s.day_end
  T.request({ tag = storm and "siege_storm" or "siege_besiegers", fid = s.a, shift = 0, n = storm and CF.storm_squads or CF.atk_squads, size = CF.squad_size,
              from_x = ax, from_z = az, to_fid = s.b, to_x = t.x, to_z = t.z })
  T.request({ tag = "siege_defenders", fid = s.b, shift = 0, n = CF.def_squads, size = CF.squad_size,
              from_x = t.x, from_z = t.z, to_fid = s.b, to_x = t.x, to_z = t.z })
end

local function day_step(s, day, x)
  local c = C(); local S = c.state()
  local fa, fb = S.F[s.a], S.F[s.b]
  if not (fa and fb and fa.alive and fb.alive) then return finish(s, day, "dead", x) end
  if not fb.towns[s.town] then if s.alarm then set_alarm(s, false) end; x.active[s.town] = nil; x.cd[s.town] = day + CF.cooldown; return log("owner changed " .. s.town) end
  if c.rel(s.a, s.b) > 10 then return finish(s, day, "peace", x) end
  -- склад: закрыт рынок/караваны (native siege/cut), убыль припасов
  local st = stock_of(s.town)
  if st then
    st.siege = math.max(st.siege or -1, day + 1); st.cut = math.max(st.cut or -1, day + 1)
    c.stock_spend(s.town, "food", CF.food_drain); c.stock_spend(s.town, "med", CF.med_drain); c.stock_spend(s.town, "weapons", CF.weapons_drain)
  end
  -- караваны, идущие в осаждённый город, разворачиваются
  local r = c.road_state and c.road_state()
  if r and r.tr then
    for _, e in pairs(r.tr) do
      if e.k == "caravan" and e.to == s.town and e.from and e.from ~= s.town then e.to = e.from; x.turned = (x.turned or 0) + 1 end
    end
  end
  if camp_step(s, day, x) then return end   -- исход из фазы родной кампании
  visible(s, day)
  local n = day - s.day0
  if n >= 2 and n - s.prog >= CF.progress_every and day < s.day_end then
    s.prog = n
    local lv = st and st.lv and st.lv.food
    local hungry = lv and lv < 0.5
    local nat = s.nat == "bound"
    c.emit({ type = "siege_progress", a = s.a, b = s.b, town_sid = s.town, town_name = s.tname, n = n, hungry = hungry and true or false,
             native = nat or nil, phase = nat and PHN[s.ph or -1] or nil, men = nat and s.mp or nil,
             text = hungry and string.format("Hunger in %s. The siege by %s enters day %d.", s.tname, nm(s.a), n)
                           or (nat and s.ph == PH.GATHERING) and string.format("%s gathers its host before %s, day %d.", nm(s.a), s.tname, n)
                           or (nat and (s.ph == PH.ASSAULTING or s.ph == PH.ASSAULT_2_ANGRY)) and string.format("%s assaults %s, day %d of the siege.", nm(s.a), s.tname, n)
                           or string.format("The siege of %s by %s goes on, day %d.", s.tname, nm(s.a), n) })
  end
  if s.nat == "bound" then   -- живая кампания: исход ждём от её фазы, бросок не нужен; предел против вечной осады
    if n >= (CF.camp_max or 20) then log("campaign stalled " .. s.town .. " day " .. n); finish(s, day, "stalled", x) end
    return
  end
  if s.nat == "fired" then return end   -- ждём экземпляр (bind_days), потом "lost" -> бросок
  if day >= s.day_end then
    log(string.format("fallback roll %s (campaign: %s)", s.town, tostring(CF.native == false and "native=false" or s.nwhy or "not launched")))
    local lv = (st and st.lv and st.lv.food) or 1
    local hunger = math.max(0, math.min(1, 1 - lv))
    local pa = c.power(s.a) * (1 + CF.hunger_bonus * hunger) * (0.85 + 0.3 * math.random())
    local pd = c.power(s.b) * CF.defender_mult
    local cap = c.cfg().factions[s.b] and c.cfg().factions[s.b].capital
    local ntowns = count(fb.towns)
    if pa >= CF.storm_ratio * pd and s.town ~= cap and ntowns > 1 then finish(s, day, "storm", x) else finish(s, day, "withdraw", x) end
  end
end

function M.daily(day)
  local x = M.slot()
  if not x then return end
  local from = math.max(x.last + 1, day - 8)
  if x.last < 0 then from = day end
  for d = from, day do
    for _, key in ipairs(sorted_keys(x.active)) do
      local s = x.active[key]
      if s then local ok, e = pcall(day_step, s, d, x); if not ok then x.active[key] = nil; error(e, 0) end end
    end
  end
  x.last = day
end

function M.camp_pulse(day)   -- фаза кампании меняется внутри суток (VICTORY живёт недолго до endCampaign): опрос каждый тик (<= 2 осады)
  local x = M.slot()
  if not x then return end
  for _, key in ipairs(sorted_keys(x.active)) do
    local s = x.active[key]
    if s and (s.nat == "fired" or s.nat == "bound") then camp_step(s, day, x) end
  end
end

local function on_attack(ev)
  local c = C()
  if is_off() or not CF.enabled or not (ev and ev.a and ev.b) then return end
  local x = M.slot()
  if not x or ev.siege then return end
  if math.random() > CF.start_chance then return end
  guard("begin", M.begin, ev.a, ev.b, ev.town_sid, math.floor(c.day()), ev.native == true)
end

local function tick()
  if is_off() or not CF.enabled then return end
  local c = C()
  if not (c and c.state and c.state()) then return end
  if not SUB then
    SUB = {}
    SUB[1] = c.subscribe("attack_repelled", on_attack)
    SUB[2] = c.subscribe("raid", on_attack)
  end
  local day = math.floor(c.day() or 0)
  local x = M.slot()
  if x and next(x.active) then M.alarm_pulse(os.clock()); M.camp_pulse(day) end
  if x and day > x.last then M.daily(day) end
end

M._tick = function() guard("tick", tick) end
M.begin_manual = function(a, b, hint) return guard("begin", function() return M.begin(a, b, hint, math.floor(C().day())) end) end   -- тест/консоль

if rawget(_G, "Events") and Events.on and not M._hooked then
  M._hooked = true
  local function guarded(fn) return function(...) local ok, e = pcall(fn, ...); if not ok then mod_fail("handler", e) end end end
  Events.on("GameWorld::charsUpdate", guarded(function()
    local now = os.clock()
    if now - LASTCLK < 5 then return end
    LASTCLK = now
    M._tick()
  end))
end
