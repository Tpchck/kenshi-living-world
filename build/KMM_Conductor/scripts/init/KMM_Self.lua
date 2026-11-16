-- KMM_Self — самосохранение NPC рядом с игроком (шаг 1 офлайн-билда, 2026-11-12)
-- 1) отряд, потерявший в бою долю бойцов (лежат/без сознания/мертвы), бежит (Blackboard:runAway);
-- 2) слабые избегают сильных: бандиты в бою с игроком бегут, если тир снаряжения игрока выше их тира на weak_tier_gap
--    (тир читается по надетым вещам через Inventory:getAllItems → тиры каталога data/catalog.json);
-- 3) сдача: разбитая банда (лидер лежит, потери ≥ surrender_loss_share) бросает бой и разбегается; режим surrender_mode="knockout"
--    (оставшиеся ложатся, «сдались») — экспериментальный, по умолчанию выключен: настоящая сдача — задача C++-плагина.
-- Пороги бегства по численности в данных — поток BEHAVIOR (FACTION run away ratio). Оценка силы до боя — задача C++-плагина.
-- Безотказность: всё в pcall; при первой ошибке функция отключается до конца сессии, причина → logs/debug.log.

local TAG = "[KMM_Self] "
local DISABLED = {}
local P, TIER, CFG
local function log(msg) msg = TAG .. tostring(msg); if not (KenshiLua and pcall(function() KenshiLua.log(msg) end)) then print(msg) end end
local function dlog(msg)
  local path = (CFG and CFG.params and CFG.params.guard and CFG.params.guard.debug_log) or "C:/KenshiModMap/logs/debug.log"
  local ok, f = pcall(io.open, path, "a")
  if ok and f then f:write(os.date("%Y-%m-%d %H:%M:%S"), " [KMM_Self] ", tostring(msg), "\n"); f:close() end
  log(msg)
end
-- on_err (Y3, override): при ошибке зовётся on_err(err), обработчик возвращает результат fn (nil = ванильное значение ядра).
-- Без on_err (уведомления) ничего не возвращаем: false из уведомления глушит соседние обработчики.
-- HEALTH (2026-11-15): отказ шага -> реестр ядра KMM_Gov (ключ KMM_Self.<шаг>): пауза 1/5/30 мин и повтор, не «до перезапуска».
-- DISABLED — только навсегда (нет Gov: прежнее поведение). off(nm) — шаг сейчас не работает (выключен или на паузе).
local function HG() local g = rawget(_G, "KMM_Gov"); if type(g) == "table" and type(g.h_fail) == "function" then return g end end
local function off(nm)
  if DISABLED[nm] then return true end
  local g = HG(); if not g then return false end
  local ok, up = pcall(g.h_up, "KMM_Self." .. nm)
  return ok and up == false
end
local function h_ok(nm) local g = HG(); if g then pcall(g.h_ok, "KMM_Self." .. nm) end end
local function h_off(nm, why, kind) DISABLED[nm] = true; local g = HG(); if g and type(g.h_off) == "function" then pcall(g.h_off, "KMM_Self." .. nm, why, kind) end end
local function fail(nm, err)   -- отказ шага: пауза в реестре (вернёт секунды), без Gov — до перезапуска (nil)
  local g, p = HG(), nil
  if g then local ok, r = pcall(g.h_fail, "KMM_Self." .. nm, err); if ok then p = r end end
  if type(p) == "number" then dlog(nm .. " failed, retry in " .. p .. " s: " .. tostring(err)); return p end
  if not DISABLED[nm] then DISABLED[nm] = true; dlog(nm .. " disabled until restart: " .. tostring(err)) end
  return nil
end
-- on_err (окно нокаута, override ядра): выключение навсегда — повторная регистрация override из тика не доказана (B3 И2/п.2)
local function guarded(nm, fn, on_err)
  return function(...)
    if off(nm) then return end
    local ok, res = pcall(fn, ...)
    if not ok then
      if on_err then
        h_off(nm, res, "override"); dlog(nm .. " disabled until restart: " .. tostring(res))
        pcall(on_err, res)
      else fail(nm, res) end
      return nil
    end
    if not on_err then h_ok(nm) end
    if on_err then return res end
  end
end
local function xz(v) if v then return v.x or v[1], v.z or v[3] end end
-- ключ персонажа между кадрами: hand:toString() (BindingsReference «hand», ✓игра: hand-ключи Stock/Town). tostring(hand) у sol2 даёт адрес
-- userdata, а getHandle() каждый раз возвращает новую копию — такой ключ не совпадает (ревью batch7 M1). Строка — офлайн-заглушки.
local function hkey(ch)
  local h = ch:getHandle()
  if type(h) == "string" then return h end
  return h:toString()
end
local function rkey(r)   -- ключ записи снимка, кэш в записи (поле "hk" — только этот смысл); ошибка API -> false
  local v = rawget(r, "hk")
  if v == nil then
    local ok, k = pcall(hkey, r.ch)
    v = (ok and type(k) == "string" and k ~= "") and k or false
    rawset(r, "hk", v)
  end
  return v
end

-- События шины дирижёра (PERF фаза 1, только эмит; подписчики — позже). Тип в EPHEMERAL дирижёра (без журнала) должен быть записан там же:
--   self_retreat           { a = fid отряда, b = fid врага (faction_avoid) | nil, squad = ключ платуна, why = "flee"|"avoid"|"faction_avoid",
--                            n = бойцов, down = лежат, loss = доля лежащих, pa/pb = сила фракций (faction_avoid), player_tier = средний тир игрока (avoid), x, z }
--   self_surrender_attempt { a = fid, squad, mode = "runaway"|"knockout", n, down, loss, leader_down = true, x, z }
-- Эмит под pcall, cfg.params.self.emit_events = false выключает.
local function emit_ev(ev)
  if P and P.emit_events == false then return end
  local Cn = KMM_Conductor
  if not (Cn and Cn.emit) then return end
  local ok, err = pcall(Cn.emit, ev)
  if not ok and not off("emit") then fail("emit", err) end
end

-- снимок загруженных NPC: KMM_Gov.snapshot(ttl); нет Gov / ошибка → собственный обход (тот же формат записей, кэш на ttl)
local function s_core(ch, r)
  local pos = ch:getPosition()
  r.x, r.z = xz(pos)
  if not (r.x and r.z) then error("no pos") end
  r.dead = ch:isDead() and true or false
end
local function s_fac(ch, r)   -- фракция необязательна: без неё запись остаётся (fid = nil)
  local f = ch:getFaction(); local gd = f and (f:getData() or f.data)
  r.fid = gd and gd.stringID
end
local function s_plat(ch, r)
  local ap = ch:getPlatoon()
  r.ap = ap; r.pl = ap and ap.me
  local me = ap and (ap.me or ap)
  local k = me and me:getPlatoonStringID()
  r.pkey = (k and k ~= "") and k or ""
end
local S_LAZY = {
  down = function(r) return (r.dead or r.ch:isDown() or r.ch:isUnconcious()) and true or false end,
  unique = function(r) return r.ch:isUnique() and true or false end,
  h = function(r) return hkey(r.ch) end,
  combat = function(r) return r.ch:isInCombatMode(true, true) and true or false end,
}
local S_MT = { __index = function(r, k)
  local fn = S_LAZY[k]
  if not fn then return nil end
  local ok, v = pcall(fn, r)
  if not ok or v == nil then v = false end
  rawset(r, k, v)
  return v
end }
local OWN
local function own_snapshot(ttl)
  local now = os.clock()
  -- краш 2026-11-13: между кадрами персонаж может быть удалён движком — повторно только в том же кадре (игровая метка времени)
  local okst, stamp = pcall(function() return getGameWorld():getTimeStamp() end)
  if okst and type(stamp) == "number" then
    if OWN and OWN.stamp == stamp and now - OWN.t >= 0 and now - OWN.t <= 0.25 then return OWN end
  elseif OWN and now - OWN.t >= 0 and now - OWN.t <= ttl then return OWN end
  local list, n = {}, 0
  for ch in pairs(getGameWorld():getCharacterUpdateList()) do
    local okp, isp = pcall(ch.isPlayerCharacter, ch)
    if okp and not isp then
      local r = { ch = ch }
      if pcall(s_core, ch, r) then
        pcall(s_fac, ch, r)
        if not pcall(s_plat, ch, r) then r.pkey = "" end
        setmetatable(r, S_MT)
        n = n + 1; list[n] = r
      end
    end
  end
  OWN = { t = now, n = n, list = list, own = true }
  do local ok2, st2 = pcall(function() return getGameWorld():getTimeStamp() end); if ok2 then OWN.stamp = st2 end end
  return OWN
end
local function get_snap(ttl)
  local g = rawget(_G, "KMM_Gov")
  if g and g.snapshot then
    local ok, snap = pcall(g.snapshot, ttl)
    if ok and snap then return snap end
  end
  return own_snapshot(ttl)
end

local function init()
  if P then return true end
  local C = KMM_Conductor
  if not (C and C.cfg) then return false end
  CFG = C.cfg()
  if not (CFG and CFG.params) then return false end
  P = CFG.params.self or { enabled = false }
  log(string.format("loaded: enabled=%s (item tiers on first use)", tostring(P.enabled)))
  return true
end
-- S5: тиры вещей (traces.json, ~110 КБ) — лениво при первой оценке тира, а не в первом тике (пик старта под Gov);
-- если Traces уже разобрал тот же файл — берём его таблицу без второго разбора
local function tiers()
  if TIER then return TIER end
  local T = rawget(_G, "KMM_Traces")
  local ok, t = pcall(function() return T and T.item_tiers and T.item_tiers() end)
  if ok and type(t) == "table" then TIER = t
  else
    local C = KMM_Conductor
    local tr = C.read_json("traces.json", "C:/KenshiModMap/build/KMM_Conductor/traces.json") or {}
    TIER = tr.item_tiers or {}
  end
  local n = 0; for _ in pairs(TIER) do n = n + 1 end
  log(string.format("item tiers: %d", n))
  return TIER
end

-- «Без страха» (плейтест 2026-11-13: монстры при отступлении кричат как люди, Mist Creatures не должны бежать):
-- runAway — человеческий приказ с криками. Не отдаём его животным, роботам (скелеты, машины) и монстрам/ужасам
-- по имени расы или фракции. Решение кэшируется на отряд (ключ платуна) на сессию; любая ошибка API -> «боится» (как раньше).
-- B6 (2026-11-15): решают люди отряда, а не первый попавшийся. Вьючный зверь (Character:isAnimal() -> CharacterAnimal | nil,
-- BindingsReference «Character») из решения исключён: в логе «The Holy Nation (animal)» бык запрещал отход паладинам.
-- Отряд «без страха», если в нём нет гуманоидов (стая) или бесстрашных (робот/раса) больше половины гуманоидов, либо фракция из списка.
local FEAR = {}
local FEAR_RACE = "mist|crystal|fog|spider|beast|demon|daemon|undead|zombie|ghoul|wraith|horror|abomination|golem|construct|necron|tyranid|beak|leviathan|deadhive|sundemon|wendigo|monster|creature|drone"
local FEAR_FAC = "mist|crystal|fog|demon|daemon|necron|tyranid|undead|horror|creature|monster"
-- животное ли запись снимка: кэш в самой записи (снимок Gov общий, поле "animal" — только этот смысл); ошибка API -> человек
local function is_animal(r)
  local v = rawget(r, "animal")
  if v == nil then
    local ok, a = pcall(function() return r.ch:isAnimal() end)
    v = (ok and a) and true or false
    rawset(r, "animal", v)
  end
  return v
end
local function fear_one(ch)   -- причина бесстрашия гуманоида (робот / раса) или false; ошибка API -> false
  local v = false
  local ok = pcall(function()
    local race = ch:getRace()
    if race and race.robot and not P.robots_flee then v = "robot"; return end
    local rn = race and race.data and race.data.name
    if type(rn) == "string" then
      local lrn = string.lower(rn)
      for w in string.gmatch(P.fearless_race_rx or FEAR_RACE, "[^|]+") do
        if string.find(lrn, w, 1, true) then v = "race:" .. rn; return end
      end
    end
  end)
  return ok and v or false
end
local function fear_fac(ch)
  local v = false
  local ok = pcall(function()
    local f = ch:getFaction()
    local gd = f and (f:getData() or f.data)
    local fn = gd and gd.name
    if type(fn) == "string" then
      for w in string.gmatch(P.fearless_faction_rx or FEAR_FAC, "[^|]+") do
        if string.find(string.lower(fn), w, 1, true) then v = "faction:" .. fn; return end
      end
    end
  end)
  return ok and v or false
end
local function fearless(key, recs)
  local v = FEAR[key]
  if v ~= nil then return v end
  local hum, nf, why, first = 0, 0, nil, nil
  for _, r in ipairs(recs) do
    if not is_animal(r) then
      hum = hum + 1
      first = first or r.ch
      local w = fear_one(r.ch)
      if w then nf = nf + 1; why = why or w end
    end
  end
  if hum == 0 then v = (#recs > 0) and "animal" or false
  elseif nf * 2 > hum then v = string.format("%s, %d/%d", why, nf, hum)
  else v = fear_fac(first) end
  FEAR[key] = v
  if v then dlog("fearless: squad " .. tostring(key) .. " (" .. tostring(v) .. ") - no retreat orders") end
  return v
end

-- средний тир надетого: вещи инвентаря, известные каталогу (без каталога — nil)
local tier_cache = {}
local function char_tier(ch, key)
  local c = tier_cache[key]
  local now = os.clock()
  if c and now - c.t < 30 then return c.v end
  local sum, n = 0, 0
  local TIER = tiers()
  local items = ch:getInventory():getAllItems()
  for _, it in ipairs(items) do
    local okg, sid = pcall(function() return it:getGameData().stringID end)
    local t = okg and sid and TIER[sid]
    if t then sum, n = sum + t, n + 1 end
  end
  local v = (n > 0) and (sum / n) or nil
  tier_cache[key] = { t = now, v = v }
  return v
end

local acted = {}   -- ключ отряда → время последнего решения
local logged = {}  -- одна строка в debug.log на отряд и вид решения за сессию
local stats = { flee = 0, avoid = 0, surrender = 0, faction_avoid = 0, ko_hold = 0, ko_release = 0 }
-- REV2: слабые избегают сильных между фракциями. Отряд в бою, чья фракция по оценке дирижёра (KMM_Conductor.power) слабее ratio от силы
-- враждебной фракции из отряда рядом (<= avoid_dist), отходит (runAway), если не превосходит врага числом вдвое. Оценка силы по месту боя — плагин.
local function faction_avoid(groups, now)
  local C = KMM_Conductor
  if P.faction_avoid == false or not (C and C.power and C.rel and C.cfg) then return end
  local pf = C.cfg().player_faction
  local ratio, dmax = P.avoid_ratio or 0.4, P.avoid_dist or 1500
  for key, g in pairs(groups) do
    if g.combat and g.fid and g.fid ~= pf and not g.uniq and #g.standing > 0 and g.x and (not acted[key] or now - acted[key] > (P.cooldown_seconds or 60)) then
      local pg = C.power(g.fid)
      for k2, h in pairs(groups) do
        if k2 ~= key and h.combat and h.fid and h.fid ~= g.fid and h.x and g.n <= 2 * h.n
           and math.sqrt((g.x - h.x) ^ 2 + (g.z - h.z) ^ 2) <= dmax then
          local ph = C.power(h.fid)
          if ph > 0 and pg < ratio * ph and C.rel(g.fid, h.fid) <= -30 then
            acted[key] = now
            g.pl:getBlackboard():runAway()
            stats.faction_avoid = stats.faction_avoid + 1
            emit_ev({ type = "self_retreat", a = g.fid, b = h.fid, squad = key, why = "faction_avoid", n = g.n, down = g.down, loss = g.n > 0 and g.down / g.n or 0, pa = pg, pb = ph, x = g.x, z = g.z })
            logged[key] = logged[key] or {}
            if not logged[key].faction_avoid then logged[key].faction_avoid = true; dlog(string.format("faction_avoid: %s squad %s backs off from %s (power %.0f vs %.0f)", tostring(g.fid), key, tostring(h.fid), pg, ph)) end
            break
          end
        end
      end
    end
  end
end
local g_favoid = guarded("faction_avoid", faction_avoid)

-- Y3 (пакет 7): ОКНО ПОБЕЖДЁННОГО. Побеждённый рядом с игроком не вскакивает сразу: у игрока есть короткое окно — связать, обыскать,
-- добить или уйти (отпустить). Кто победил — ядро: поле Character.lastGuyWhoDefeatedMe (hand, BindingsReference «Character»).
-- Держим только: (а) побеждённых персонажем игрока (isPlayerCharacter у победителя); (б) бой конкурентов при игроке — побеждённый
-- или победитель из отряда соперника Nemesis (ключ платуна o.pk из KMM_Nemesis.rivals()). Кандидаты — только из отрядов, бывших в бою
-- в последние ko_fight_window_s (метка в скане), в радиусе ko_hold_r от игрока; посторонние без вызовов движка.
-- Свежесть (ревью batch7 M2): поле хранит ПОСЛЕДНЕГО победителя, поэтому победитель должен быть жив и не дальше ko_win_r от побеждённого,
-- а побеждённого должны были видеть стоящим в этом бою (метка KO.up за ko_fight_window_s): кто лёг от голода или зверя возле старого
-- победителя — не наш случай.
-- Рычаг — override MedicalSystem::canGetUpWakeUp(self, defaultVal) (CallbacksReference, Override): false = «ещё не встаёт»,
-- nil = ванильный ответ. Горячий путь: обработчик зарегистрирован ТОЛЬКО пока есть удерживаемые (Events.on при первом, Events.off
-- в такте после последнего); внутри — defaultVal=false или пустая таблица -> nil без вызовов движка; иначе me -> getHandle -> toString ->
-- таблица по ключу (O(1), 3 обращения к движку) и сравнение с запасным пределом реального времени.
-- Предел (ревью batch7 H1): не дольше ko_hold_s (≤60) секунд реального времени при скорости 1× с момента взятия = игровые часы
-- (getTimeStamp_inGameHours) × getLengthOfHourInRealSeconds. Игровая секунда во много раз короче реальной: прежний предел в игровых секундах
-- отпускал на первом же скане. Пауза окно не тратит, ускорение сокращает его в реальных секундах (игровой ход тот же). Длины часа нет —
-- реальные часы os.clock; игрового времени нет — окна нет. Шаг скана берётся в запас не больше четверти окна. Запасной предел реального
-- времени ko_hard_real_s проверяет сам override (если скан встал). Не больше ko_hold_max разом; персонаж — не чаще раза в 10 мин.
-- Отпуск: связан (isChained), мёртв, игрок дальше ko_release_r, встал сам, пропал, таймаут, смена мира.
-- Ключи персонажей — hand:toString() (hkey/rkey), не tostring(hand) (M1).
-- B3 согласован: сдавшиеся через knockoutForceTimer (своё окно surrender_ko_seconds) сюда не берутся — одно окно на персонажа.
-- Ошибка в override или в скане окна -> все отпущены, обработчик снят в следующем такте, окно выключено до перезапуска.
-- Маркеры debug.log: «KO hold:» / «KO release:» (asks = сколько раз ядро спросило за удержание — замер частоты override в игре).
-- S1 (2026-11-15): одно удержание на персонажа за бой — KO.once[hand:toString()] = момент взятия, повтор не раньше ko_once_s (120) реальных
-- секунд, что бы ни случилось с записью seen (смена мира, сбой). В строке «KO hold:» — key=<хвост ключа>: одноимённые (орда «Fogman») различимы.
local KO = { hold = {}, n = 0, seen = {}, forced = {}, fight = {}, up = {}, once = {}, hook = nil, perm = false, off = false, S = nil,
             rpk = nil, rpk_t = -1e9, g_last = nil, g_step = 0, logs = 0, prune_t = -1e9, notime = false, lh = nil }
local function ko_p(k, d) local v = P and P[k]; if v == nil then return d end; return v end
local function ko_log(msg)
  if KO.logs >= ko_p("ko_log_max", 300) then return end
  KO.logs = KO.logs + 1
  dlog(msg)
end
local function ko_override(med, dv)
  KO.calls = (KO.calls or 0) + 1   -- 2026-11-15 игра: asks=0 во всех удержаниях — счётчик вызовов отличает «ядро не зовёт» от «не узнали персонажа»
  if not dv or KO.n == 0 then return nil end
  local me = med.me
  if not me then KO.miss_me = (KO.miss_me or 0) + 1; return nil end
  local e = KO.hold[hkey(me)]
  if not e then KO.miss_key = (KO.miss_key or 0) + 1; return nil end
  if os.clock() > e.hard then return nil end
  e.asks = e.asks + 1
  return false
end
-- время окна: секунды реального времени при скорости 1× (игровые часы × длина часа в реальных секундах); nil — игрового времени нет
local function ko_now()
  local ok, h = pcall(function() return getGameWorld():getTimeStamp_inGameHours():getTotalHours() end)
  if not (ok and type(h) == "number") then return nil end
  if KO.lh == nil then
    local okl, lh = pcall(function() return getGameWorld():getLengthOfHourInRealSeconds() end)
    if okl and type(lh) == "number" and lh >= 1 and lh <= 36000 then
      KO.lh = lh; dlog(string.format("KO hold: game hour = %.1f real s at 1x - window on game clock", lh))
    else
      KO.lh = false; dlog("KO hold: getLengthOfHourInRealSeconds unavailable (" .. tostring(lh) .. ") - window on real clock")
    end
  end
  if KO.lh then return h * KO.lh end
  return os.clock()
end
local function ko_release(k, e, why, gnow)
  KO.hold[k] = nil; KO.n = KO.n - 1
  KO.seen[k] = { t = os.clock(), n = 0, done = true }
  stats.ko_release = stats.ko_release + 1
  ko_log(string.format("KO release: %s why=%s held=%.0fs asks=%d (override calls=%d miss_me=%d miss_key=%d)", tostring(e.nm), why, (gnow and gnow >= e.g0) and (gnow - e.g0) or -1, e.asks,
    KO.calls or 0, KO.miss_me or 0, KO.miss_key or 0))
end
local function ko_reset(why, gnow)
  for k, e in pairs(KO.hold) do ko_release(k, e, why, gnow) end
  KO.hold = {}; KO.n = 0
end
local function ko_shutdown(reason)
  if KO.off then return end
  KO.off = true
  pcall(ko_reset, "off")
  KO.hold = {}; KO.n = 0
  dlog("KO hold disabled until restart: " .. tostring(reason))
end
local function ko_fail(err) ko_shutdown("override: " .. tostring(err)) end
local function ko_hook_on()
  if KO.hook or KO.perm then return true end
  if not (Events and Events.on) then ko_shutdown("no Events.on"); return false end
  local ok, id = pcall(function() return Events.on("MedicalSystem::canGetUpWakeUp", guarded("ko_override", ko_override, ko_fail)) end)
  if not ok then ko_shutdown("Events.on: " .. tostring(id)); return false end
  if id == nil then KO.perm = true; dlog("KO hold: override handler id missing - stays registered (idle cost: one table check)")
  else KO.hook = id end
  return true
end
-- такт: снять обработчик, когда держать некого или окно выключено (не из самого override: там ядро обходит список обработчиков)
local function ko_maint()
  if KO.n > 0 then
    if ko_p("ko_hold", true) == false then pcall(ko_reset, "off")
    elseif DISABLED.scan or DISABLED.ko_hold then ko_shutdown("scan stopped")
    elseif off("scan") then pcall(ko_reset, "scan paused") end   -- HEALTH: скан на паузе — отпустить удержанных, окно живо
  end
  if KO.hook and (KO.off or (KO.n == 0 and not KO.boot)) and Events and Events.off then   -- регистрация при загрузке (KO.boot) снимается только при выключении окна
    local id = KO.hook; KO.hook = nil
    pcall(Events.off, id)
  end
end
local function ko_rivals(now)
  if now - KO.rpk_t < 30 and now >= KO.rpk_t then return KO.rpk end
  KO.rpk_t = now; KO.rpk = nil
  local NM = rawget(_G, "KMM_Nemesis")
  local ok, list = pcall(function() return NM and NM.rivals and NM.rivals() end)
  if ok and type(list) == "table" then
    local s, n = {}, 0
    for _, o in ipairs(list) do
      if type(o) == "table" and type(o.pk) == "string" and o.pk ~= "" and o.pk ~= "?" then s[o.pk] = true; n = n + 1 end
    end
    if n > 0 then KO.rpk = s end
  end
  return KO.rpk
end
-- кто победил: только ядро; победитель жив и рядом с побеждённым (поле хранит последнего победителя); nil — не наш случай
local function ko_judge(r, rpk)
  local hd = r.ch.lastGuyWhoDefeatedMe
  local w = hd and hd:getCharacter()
  if not w or w:isDead() then return nil end
  local wx, wz = xz(w:getPosition())
  local wr = ko_p("ko_win_r", ko_p("ko_hold_r", 2500))
  if not (wx and wz) or (wx - r.x) ^ 2 + (wz - r.z) ^ 2 > wr * wr then return nil end
  if w:isPlayerCharacter() then return "player", w end
  if rpk then
    if r.pkey ~= "" and rpk[r.pkey] then return "rival_down", w end
    local ap = w:getPlatoon()
    local me = ap and (ap.me or ap)
    local k = me and me:getPlatoonStringID()
    if k and rpk[k] then return "rival_win", w end
  end
  return nil
end
local function ko_prune(now)
  if now - KO.prune_t < 60 and now >= KO.prune_t then return end
  KO.prune_t = now
  for k, v in pairs(KO.seen) do if now - v.t > 600 or now < v.t then KO.seen[k] = nil end end
  for k, t in pairs(KO.forced) do if now - t > 120 or now < t then KO.forced[k] = nil end end
  for k, t in pairs(KO.fight) do if now - t > 120 or now < t then KO.fight[k] = nil end end
  for k, t in pairs(KO.up) do if now - t > 120 or now < t then KO.up[k] = nil end end
  local og = math.max(120, ko_p("ko_once_s", 120))
  for k, t in pairs(KO.once) do if now - t > og or now < t then KO.once[k] = nil end end
end
-- kc: записи снимка из отрядов, бывших в бою недавно, в радиусе ko_hold_r от игрока (собирает scan)
local function ko_step(kc, px, pz, now)
  if KO.off then return end
  if ko_p("ko_hold", true) == false then if KO.n > 0 then ko_reset("off") end; return end
  ko_prune(now)
  -- смена мира (другой сейв без перезапуска): хендлы прошлого мира не держим
  local C = KMM_Conductor
  local okS, S = pcall(function() return C and C.state and C.state() end)
  S = okS and S or nil
  if S ~= nil then
    if KO.S ~= nil and S ~= KO.S then
      if KO.n > 0 then ko_reset("world") end
      KO.seen, KO.forced, KO.fight, KO.up, KO.once, KO.g_last, KO.g_step, KO.lh = {}, {}, {}, {}, {}, nil, 0, nil
    end
    KO.S = S
  end
  local lim = math.min(ko_p("ko_hold_s", 30), 60)
  local gnow
  if KO.n > 0 then
    gnow = ko_now()
    if gnow and KO.g_last then local d = gnow - KO.g_last; if d >= 0 and d < 120 then KO.g_step = d end end
    KO.g_last = gnow
    local pad = math.min(KO.g_step, lim * 0.25)   -- шаг скана в запас: удержание не перешагнёт предел и не обрежется больше чем на четверть
    local rr2 = ko_p("ko_release_r", 4000) ^ 2
    for k, e in pairs(KO.hold) do
      local why
      if not gnow then why = "no_time"
      elseif gnow < e.g0 or gnow - e.g0 + pad >= lim then why = "timeout"
      else
        local okc, ch = pcall(function() return e.hd:getCharacter() end)
        if not okc or not ch then why = "gone"
        else
          local okv, w2 = pcall(function()
            if ch:isDead() then return "dead" end
            if ch.isChained then return "tied" end
            local x, z = xz(ch:getPosition())
            if not x or (x - px) ^ 2 + (z - pz) ^ 2 > rr2 then return "left" end
            if not (ch:isDown() or ch:isUnconcious()) then return "up" end
            return nil
          end)
          if okv then why = w2 else why = "err" end
        end
      end
      if why then ko_release(k, e, why, gnow) end
    end
  end
  if #kc == 0 then return end
  local pf = CFG and CFG.player_faction
  local kwin = ko_p("ko_fight_window_s", 30)
  -- M2: кто стоял в этом бою — метка KO.up (ключ hand:toString, не больше ko_up_max вызовов за скан)
  local ub = ko_p("ko_up_max", 24)
  for _, r in ipairs(kc) do
    if ub <= 0 then break end
    if not r.dead and (pf == nil or r.fid ~= pf) and not r.down then
      ub = ub - 1
      local k = rkey(r)
      if k then KO.up[k] = now end
    end
  end
  local maxn = ko_p("ko_hold_max", 6)
  if KO.n >= maxn then return end
  local budget = ko_p("ko_judge_max", 12)
  local rpk
  for _, r in ipairs(kc) do
    if KO.n >= maxn or budget <= 0 then break end
    if not r.dead and (pf == nil or r.fid ~= pf) and r.down then
      local k = rkey(r)
      local up = k and KO.up[k]
      if k and not KO.hold[k] and up and now - up <= kwin and now >= up then
        local sn, fz, o1 = KO.seen[k], KO.forced[k], KO.once[k]
        local skip = (fz and now - fz < 120 and now >= fz)
          or (o1 and now - o1 < math.max(120, ko_p("ko_once_s", 120)) and now >= o1)
          or (sn and now >= sn.t and ((sn.done and now - sn.t < 600) or (not sn.done and sn.n >= 3 and now - sn.t < 120)))
        if not skip and not is_animal(r) then
          budget = budget - 1
          if not gnow then
            gnow = ko_now()
            if not gnow then
              if not KO.notime then KO.notime = true; dlog("KO hold: no game time (getTimeStamp_inGameHours) - no window") end
              return
            end
          end
          if rpk == nil then rpk = ko_rivals(now) or false end
          local okj, why, w = pcall(ko_judge, r, rpk or nil)
          local okh, hd = pcall(function() return r.ch:getHandle() end)
          local okp, isp = pcall(function() return r.ch:isPlayerCharacter() end)
          if okj and why and okh and hd and okp and not isp then
            if not ko_hook_on() then return end
            local _, nm = pcall(function() return r.ch:getName() end)
            local _, wn = pcall(function() return w:getName() end)
            KO.hold[k] = { hd = hd, g0 = gnow, hard = now + math.max(ko_p("ko_hard_real_s", 90), lim + 15), asks = 0, why = why, nm = nm or k }
            KO.n = KO.n + 1; KO.once[k] = now
            if KO.g_last == nil or KO.n == 1 then KO.g_last = gnow end   -- шаг скана меряется от взятия, а не от прошлого окна
            stats.ko_hold = stats.ko_hold + 1
            ko_log(string.format("KO hold: %s (%s) by %s why=%s limit=%ds key=%s", tostring(nm or k), tostring(r.fid), tostring(wn or "?"), why, lim,
                                 tostring(k):sub(-24)))
          else
            KO.seen[k] = { t = now, n = (sn and not sn.done and sn.n or 0) + 1 }
          end
        end
      end
    end
  end
end
local g_ko = guarded("ko_hold", ko_step, function(err) ko_shutdown("ko_hold: " .. tostring(err)) end)

local function scan()
  local pcs = getPlayerInterface():getAllPlayerCharacters()
  local px, pz = nil, nil
  for _, pc in pairs(pcs) do
    local x, z = xz(pc:getPosition())
    if x then px, pz = x, z; break end
  end
  if not px then return end
  -- S5: средний тир игрока — лениво (инвентари всех персонажей игрока нужны только решению «avoid» и строке лога), раз за скан
  local ptier, pn, pt_done = nil, 0, false
  local function player_tier()
    if pt_done then return ptier, pn end
    pt_done = true
    local sum = 0
    for _, pc in pairs(pcs) do
      local okh, h = pcall(hkey, pc)
      local t = char_tier(pc, (okh and type(h) == "string") and h or tostring(pn))
      if t then sum, pn = sum + t, pn + 1 end
    end
    ptier = (pn > 0) and (sum / pn) or nil
    return ptier, pn
  end
  local groups = {}
  local snap = get_snap(P.snap_ttl or 3.5)
  local rad = P.radius or 6000
  -- PERF2: проход 1 - только группировка и признак боя (дёшево, r.combat кэшируется и отсекается после первого боевого бойца отряда);
  -- проход 2 - только для боевых отрядов: лежат/уникальные/вожак (решения принимаются лишь у g.combat, остальное было впустую).
  local rad2 = rad * rad
  for _, r in ipairs(snap.list) do
    local key = r.pkey
    if key ~= "" and r.pl and (r.x - px) ^ 2 + (r.z - pz) ^ 2 <= rad2 then
      local g = groups[key]
      if not g then
        local fdata = r.fid and CFG.factions[r.fid]
        g = { pl = r.pl, fid = r.fid, ftype = fdata and fdata.ftype, n = 0, down = 0, combat = false, standing = {}, leader_down = false, uniq = false, recs = {} }
        groups[key] = g
      end
      g.n = g.n + 1
      g.x, g.z = r.x, r.z
      g.recs[g.n] = r
      if not g.combat and r.combat then g.combat = true end
    end
  end
  local now = os.clock()
  -- Y3: метка боя отряда (до «без страха») и кандидаты окна побеждённого — записи недавно воевавших отрядов у игрока (без вызовов движка)
  local kc, kon = {}, not KO.off and ko_p("ko_hold", true) ~= false
  local kwin, khr2 = ko_p("ko_fight_window_s", 30), ko_p("ko_hold_r", 2500) ^ 2
  for key, g in pairs(groups) do
    if g.combat then KO.fight[key] = now end
    if g.combat and g.recs[1] and fearless(key, g.recs) then g.combat = false end   -- без страха: решений не принимаем
    if g.combat then
      local lead_h   -- хендл вожака: один вызов на боевой платун, и только если кто-то лежит
      g.n = 0        -- B6: бой оценивают люди отряда — вьючные звери не считаются ни бойцами, ни потерями, ни «стоящими»
      for _, r in ipairs(g.recs) do
        if is_animal(r) then -- пропуск
        elseif r.down then
          g.n = g.n + 1; g.down = g.down + 1
          if lead_h == nil then
            local okl, lh = pcall(function() local lead = r.pl:getSquadLeader(); return lead ~= nil and hkey(lead) or false end)
            lead_h = okl and lh or false
          end
          if lead_h and rkey(r) == lead_h then g.leader_down = true end
        else g.n = g.n + 1; g.standing[#g.standing + 1] = r.ch end
        if not g.uniq and not r.animal and r.unique then g.uniq = true end
      end
    end
    local ft = kon and KO.fight[key]
    if ft and now - ft <= kwin and now >= ft then
      for _, r in ipairs(g.recs) do if (r.x - px) ^ 2 + (r.z - pz) ^ 2 <= khr2 then kc[#kc + 1] = r end end
    end
    g.recs = nil
  end
  g_favoid(groups, now)
  local weak = {}
  for _, t in ipairs(P.surrender_factions_ftype or { 8 }) do weak[t] = true end
  for key, g in pairs(groups) do
    if g.combat and g.n >= 2 and #g.standing > 0 and (not acted[key] or now - acted[key] > (P.cooldown_seconds or 60)) then
      local loss = g.down / g.n
      local action
      if weak[g.ftype] and not g.uniq and g.leader_down and loss >= (P.surrender_loss_share or 0.75) then action = "surrender"
      elseif loss >= (P.flee_loss_share or 0.5) then action = "flee"
      elseif weak[g.ftype] and #g.standing > 0 and player_tier() then
        local okt, mt = pcall(char_tier, g.standing[1], key .. "#1")
        if okt and mt and ptier - mt >= (P.weak_tier_gap or 1.5) and g.n <= 2 * math.max(1, pn) then action = "avoid" end
      end
      if action then
        acted[key] = now
        local ev = { a = g.fid, squad = key, n = g.n, down = g.down, loss = loss, x = g.x, z = g.z }
        local ko_ok = false
        if action == "surrender" and P.surrender_mode == "knockout" and not off("knockout") then   -- экспериментально: «сдались» = легли (нокаут)
          -- B3: ванильный MedicalSystem:knockoutForceTimer(sec) (BindingsReference «MedicalSystem», MedicalSystem.h:211) вместо записи
          -- полей knockoutTimer/unconcious: ядро само проходит коллапс и рэгдолл. B6: getMedical() вместо поля ch.medical (копия по значению).
          local okk, err = pcall(function()
            for _, ch in ipairs(g.standing) do ch:getMedical():knockoutForceTimer(P.surrender_ko_seconds or 25) end
          end)
          if okk then
            ko_ok = true
            for _, ch in ipairs(g.standing) do   -- Y3: у сдавшихся своё окно (B3), окно побеждённого их не продлевает
              local okh, h = pcall(hkey, ch)
              if okh and type(h) == "string" then KO.forced[h] = now end
            end
          else fail("knockout", "(surrender -> runaway) " .. tostring(err)) end
        end
        if ko_ok then
          stats.surrender = stats.surrender + 1
          ev.type, ev.mode, ev.leader_down = "self_surrender_attempt", "knockout", true
        elseif action == "surrender" then   -- по умолчанию: разбитая банда без вожака бросает бой и разбегается
          g.pl:getBlackboard():runAway()
          stats.surrender = stats.surrender + 1
          ev.type, ev.mode, ev.leader_down = "self_surrender_attempt", "runaway", true
        else
          g.pl:getBlackboard():runAway()
          stats[action] = stats[action] + 1
          ev.type, ev.why = "self_retreat", action
          if action == "avoid" then ev.player_tier = ptier end
        end
        emit_ev(ev)
        logged[key] = logged[key] or {}
        if not logged[key][action] then logged[key][action] = true; player_tier(); dlog(string.format("%s: %s squad %s (%d/%d down%s)", action, tostring(g.fid), key, g.down, g.n, ptier and string.format(", player tier %.1f", ptier) or "")) end
      end
    end
  end
  if kon or KO.n > 0 then g_ko(kc, px, pz, now) end
end

local t_scan, t_beat = 0, nil
local g_scan = guarded("scan", scan)
-- S5: скан по снимку — только в первом кадре общего такта floor(os.clock() / SNAP_BEAT) (как Traces/Stock): в игре снимок Gov живёт один кадр,
-- и три модуля в одном кадре делят одну перестройку. scan_seconds 3 = каждый такт (период прежний).
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
local function tick()
  if not init() or not P.enabled then return end
  if KO.hook or KO.n > 0 then ko_maint() end
  local now = os.clock()
  if not stamp_mode() then   -- офлайн без метки кадра: прежнее расписание
    if now - t_scan < (P.scan_seconds or 3) then return end
    t_scan = now
    return g_scan()
  end
  local beat = math.floor(now / SNAP_BEAT)
  if beat == t_beat then return end
  t_beat = beat
  local n = math.max(1, math.ceil(((P.scan_seconds or 3) - 0.5) / SNAP_BEAT))   -- период в тактах (вверх), такты кратные n — как у Traces
  if beat % n ~= 0 then return end
  t_scan = now
  g_scan()
end
-- 2026-11-15 игра: override, зарегистрированный посреди игры, ядро не вызывало (asks=0); перехват диалогов, зарегистрированный при
-- загрузке, работает (DIPLO_COND hook live). Регистрируем override один раз здесь и не снимаем: без удержаний он стоит одно сравнение.
pcall(function() if ko_hook_on() then KO.boot = true; dlog("KO hold: override registered at load") end end)
if Events and Events.on then Events.on("GameWorld::charsUpdate", guarded("tick", function(...) if _G.KMM_Gov then return KMM_Gov.run("self", tick, ...) else return tick(...) end end)) end

KMM_Self = { stats = function() return stats end, disabled = function() return DISABLED end, _tick = function() tick() end,
             ko = function() return KO end }

-- PUBLISH (2026-11-16): KenshiLua runs each init script in its own sandbox; a plain global stays inside it.
if KMM_Self ~= nil then rawset(_G, "KMM_Self", KMM_Self) end
