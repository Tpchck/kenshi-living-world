-- KMM_Gov — общий контроль нагрузки Lua наших модулей (2026-11-12). Публикует _G.KMM_Gov.
-- API: KMM_Gov.run(name, fn, ...) — вызывает fn(...) с замером os.clock; KMM_Gov.stats() — таблица для отладки.
-- Модуль считает скользящее среднее и пик; при превышении бюджета включает троттлинг: модуль выполняется 1 тик из N
-- (N: 2 -> 4 -> 8), пропущенные тики fn не вызываются. Восстановление: среднее упало ниже половины бюджета -> N делится на 2.
-- Безотказность: вся бухгалтерия под pcall; если Gov сломан, run просто вызывает fn (модули от Gov не зависят).
-- KMM_Gov.snapshot(ttl) — общий снимок загруженных NPC (PERF фаза 1): один обход getCharacterUpdateList на окно, кэш полей, ленивое заполнение.
--   snap = { t, n, list = { rec... }, by_pkey = { [ключ платуна] = { rec... } } }, rec: ch, x, z, fid, dead, ap, pl, pkey (всегда),
--   лениво по первому обращению: trader, tsid, down, unique, h (строка-хендл), combat, town. Игроки в снимок не попадают.
--   Возвращает nil при любой ошибке (модули откатываются на свой обход). Снимок устаревает до ttl секунд: действия над rec.ch — с проверкой isDead в момент действия.
--   Конфиг: KMM_Gov.cfg.snap = { enabled, ttl, ttl_rt, same_frame, max_chars, fail_pause }.
-- T2 (2026-11-15): снимок живёт до ttl_rt секунд реального времени (не один кадр). В новом кадре запись отдаётся, только если её персонаж
--   всё ещё в живом наборе движка: ogre_unordered_set:has(ch) (ContainersReference: хеш-поиск по указателю, объект не разыменовывается) —
--   выгруженные/удалённые (лут, выгрузка зоны) выпадают из list/by_pkey этого кадра. Указатели платуна и города (ap, pl, town) в кадре сборки
--   берутся из сборки, в поздних кадрах — заново от проверенного персонажа (адрес удалённого персонажа мог занять новый: старый ap/pl висел бы).
--   Скалярные поля (x, z, fid, dead, pkey, down, combat...) устаревают до ttl_rt. Нет has у набора (офлайн-заглушки) — прежнее правило «один кадр».
--   Порционной/инкрементальной сборки нет: без вызова API (getHandle) нечем сопоставить персонажа нового обхода с записью прошлого.
-- Стоимость snapshot() (сборка/проверка) копится отдельно (stats()["gov:snapshot"]) и вычитается из замера Gov.run позвавшего модуля.
-- Своих Events.on нет, на старте ничего не делает; пишет в debug.log при смене режима (<= 1 раза в 60 с на модуль)
-- и сводку раз в report_s секунд: маркеры «[KMM_Gov] summary:» и «[KMM_Gov] modules:».
-- HEALTH (2026-11-15): реестр здоровья механик KMM_Gov.health + h_up/h_ok/h_fail/h_off/h_guard/health_list (блок внизу файла).
local G = rawget(_G, "KMM_Gov") or {}
G.cfg = G.cfg or {
  frame_budget = 0.002,   -- сумма средних по всем модулям, сек
  module_budget = 0.0006, -- скользящее среднее одного модуля, сек
  peak = 0.008,           -- пик одного вызова, сек
  peak_hits = 3,          -- столько пиков подряд -> эскалация
  alpha = 0.2,            -- вес нового замера в скользящем среднем
  min_runs = 5,           -- минимум замеров между сменами режима
  calm_runs = 10,         -- замеров с низким средним для отката на ступень
  max_n = 8,
  log_gap = 60,           -- сек между строками лога на модуль
  report_s = 300,         -- сек между сводками нагрузки в debug.log (0 = выкл)
  debug_log = "C:/KenshiModMap/logs/debug.log",
  snap = { enabled = true, ttl = 2.0, ttl_rt = 0.75, same_frame = 0.25, max_chars = 3000, fail_pause = 20 },
}
G.cfg.snap = G.cfg.snap or {}
do
  local d = { enabled = true, ttl = 2.0, ttl_rt = 0.75, same_frame = 0.25, max_chars = 3000, fail_pause = 20 }
  for k, v in pairs(d) do if G.cfg.snap[k] == nil then G.cfg.snap[k] = v end end
  if G.cfg.report_s == nil then G.cfg.report_s = 300 end
end
local S = G._s or {}
G._s = S
local SN = G._snap or {}
G._snap = SN
do
  local d = { pause_until = -1, builds = 0, hits = 0, fails = 0, chars = 0, skipped = 0, vals = 0, dropped = 0, acc = 0,
              t_build = 0, t_val = 0, pk_build = 0, pk_val = 0, calls = 0 }
  for k, v in pairs(d) do if SN[k] == nil then SN[k] = v end end
end

local function dlog(st, name, msg)
  local ok = pcall(function()
    local now = os.time()
    if st.logged and now - st.logged < G.cfg.log_gap then return end
    st.logged = now
    local fh = io.open(G.cfg.debug_log, "a")
    if fh then fh:write(os.date("%Y-%m-%d %H:%M:%S"), " [KMM_Gov] ", name, ": ", msg, "\n"); fh:close() end
  end)
  return ok
end

local function pre(name)   -- true, если этот тик пропустить
  local st = S[name]
  if not st then st = { avg = 0, peak = 0, runs = 0, skipped = 0, hits = 0, since = 0, calm = 0, n = 1, ctr = 0 }; S[name] = st end
  if st.n > 1 then
    st.ctr = st.ctr + 1
    if st.ctr % st.n ~= 0 then st.skipped = st.skipped + 1; return true end
  end
  return false
end

local function total_avg()
  local t = 0
  for _, s in pairs(S) do t = t + s.avg / (s.n > 1 and s.n or 1) end
  return t
end

local function post(name, dt)
  local c, st = G.cfg, S[name]
  st.runs = st.runs + 1; st.since = st.since + 1
  st.avg = (st.runs == 1) and dt or (st.avg + c.alpha * (dt - st.avg))
  if dt > st.peak then st.peak = dt end
  if dt > (st.wpeak or 0) then st.wpeak = dt end
  if dt > c.peak then st.hits = st.hits + 1 else st.hits = 0 end
  local why
  if st.hits >= c.peak_hits then why = string.format("peak %.1f ms x%d", dt * 1000, st.hits)
  elseif st.since >= c.min_runs and st.avg > c.module_budget then why = string.format("avg %.2f ms > %.2f ms", st.avg * 1000, c.module_budget * 1000)
  elseif st.since >= c.min_runs and st.avg > c.module_budget * 0.5 and total_avg() > c.frame_budget then
    local worst = true
    for k, s in pairs(S) do if k ~= name and s.avg > st.avg then worst = false end end
    if worst then why = string.format("frame sum %.2f ms > %.2f ms", total_avg() * 1000, c.frame_budget * 1000) end
  end
  if why and st.n < c.max_n and st.since >= c.min_runs then
    st.n = st.n * 2; st.since = 0; st.hits = 0; st.calm = 0; st.ctr = 0
    st.reason = why
    st.thr = (st.thr or 0) + 1
    dlog(st, name, "throttle 1/" .. st.n .. " (" .. why .. ")")
  elseif st.n > 1 then
    if st.avg < c.module_budget * 0.5 then st.calm = st.calm + 1 else st.calm = 0 end
    if st.calm >= c.calm_runs then
      st.n = math.max(1, math.floor(st.n / 2)); st.calm = 0; st.since = 0; st.ctr = 0
      dlog(st, name, "recover -> " .. (st.n > 1 and ("1/" .. st.n) or "full") .. string.format(" (avg %.2f ms)", st.avg * 1000))
    end
  end
end

-- сводка в debug.log раз в report_s секунд: перестройки/проверки снимка в секунду, их средняя/пиковая стоимость, доля пропусков по модулям
local RP = G._rep or {}
G._rep = RP
local function report(now)
  local every = G.cfg.report_s
  if not every or every <= 0 then return end
  if not RP.t then RP.t = now; RP.b, RP.v, RP.h, RP.tb, RP.tv, RP.dr, RP.f = SN.builds, SN.vals, SN.hits, SN.t_build, SN.t_val, SN.dropped, SN.fails; return end
  local w = now - RP.t
  if w < 0 then RP.t = now; return end
  if w < every then return end
  local nb, nv, nh = SN.builds - RP.b, SN.vals - RP.v, SN.hits - RP.h
  local s1 = string.format("summary: %.0fs, snap builds %.2f/s avg %.2f ms peak %.2f ms, validated %.2f/s avg %.2f ms peak %.2f ms, reuse %.2f/s, dropped %d, fails %d, chars %d",
    w, nb / w, nb > 0 and (SN.t_build - RP.tb) / nb * 1000 or 0, SN.pk_build * 1000, nv / w, nv > 0 and (SN.t_val - RP.tv) / nv * 1000 or 0, SN.pk_val * 1000,
    nh / w, SN.dropped - RP.dr, SN.fails - RP.f, SN.cur and SN.cur.n or 0)
  local names = {}
  for k in pairs(S) do names[#names + 1] = k end
  table.sort(names)
  local parts = {}
  for _, k in ipairs(names) do
    local s = S[k]
    local dr, dk = s.runs - (s.r0 or 0), s.skipped - (s.k0 or 0)
    parts[#parts + 1] = string.format("%s avg %.2f peak %.2f ms thr %d%% 1/%d", k, s.avg * 1000, (s.wpeak or 0) * 1000, (dr + dk) > 0 and math.floor(dk * 100 / (dr + dk) + 0.5) or 0, s.n)
    s.r0, s.k0, s.wpeak = s.runs, s.skipped, 0
  end
  local fh = io.open(G.cfg.debug_log, "a")
  if fh then
    local ts = os.date("%Y-%m-%d %H:%M:%S")
    fh:write(ts, " [KMM_Gov] ", s1, "\n", ts, " [KMM_Gov] modules: ", (#parts > 0 and table.concat(parts, "; ") or "-"), "\n")
    local hl = G.health_line and G.health_line()
    if hl then fh:write(ts, " [KMM_Gov] health: ", hl, "\n") end
    fh:close()
  end
  RP.t = now; RP.b, RP.v, RP.h, RP.tb, RP.tv, RP.dr, RP.f = SN.builds, SN.vals, SN.hits, SN.t_build, SN.t_val, SN.dropped, SN.fails
  SN.pk_build, SN.pk_val = 0, 0
end

function G.run(name, fn, ...)
  local ok, skip, t0, a0 = pcall(function() return pre(name), os.clock(), SN.acc end)
  if not ok then return fn(...) end
  if skip then return end
  local a, b = fn(...)
  pcall(function()
    local now = os.clock()
    local dt = now - t0 - (SN.acc - a0)   -- снимок, собранный/проверенный внутри fn, — на счёт gov:snapshot, не модуля
    post(name, dt > 0 and dt or 0)
    report(now)
  end)
  return a, b
end

function G.stats()
  local out = {}
  pcall(function()
    for k, s in pairs(S) do out[k] = { avg_ms = s.avg * 1000, peak_ms = s.peak * 1000, runs = s.runs, skipped = s.skipped, n = s.n, reason = s.reason } end
    local nr = SN.builds + SN.vals
    out["gov:snapshot"] = { avg_ms = nr > 0 and (SN.t_build + SN.t_val) / nr * 1000 or 0, peak_ms = math.max(SN.pk_build, SN.pk_val) * 1000, runs = nr, skipped = 0, n = 1,
                            builds = SN.builds, vals = SN.vals, total_ms = SN.acc * 1000 }
  end)
  return out
end

---------------------------------------------------------------------------------------------- общий снимок загруженных NPC
local function f_core(ch, r)
  local pos = ch:getPosition()
  r.x, r.z = pos.x or pos[1], pos.z or pos[3]
  if not (r.x and r.z) then error("no pos") end
  r.dead = ch:isDead() and true or false
end
local function f_fac(ch, r)   -- фракция необязательна: без неё запись остаётся (fid = nil)
  local f = ch:getFaction(); local gd = f and (f:getData() or f.data)
  r.fid = gd and gd.stringID
end
local function f_plat(ch, r)
  local ap = ch:getPlatoon()
  r._ap = ap
  r._pl = ap and ap.me
  local me = ap and (ap.me or ap)
  local k = me and me:getPlatoonStringID()
  r.pkey = (k and k ~= "") and k or ""
end
local LAZY = {   -- скаляры: кэш в записи до пересборки (устаревают до ttl_rt)
  trader = function(r) return (r.ap and r.ap:getIsTrader()) and true or false end,
  tsid = function(r) local t = r.pl and r.pl.squadTemplate; return t and t.stringID end,
  down = function(r) return (r.dead or r.ch:isDown() or r.ch:isUnconcious()) and true or false end,
  unique = function(r) return r.ch:isUnique() and true or false end,
  h = function(r) return tostring(r.ch:getHandle()) end,
  combat = function(r) return r.ch:isInCombatMode(true, true) and true or false end,
}
local PLAZY = {   -- указатели: на кадр (в кадре сборки — из сборки)
  ap = function(r) return r.ch:getPlatoon() end,
  pl = function(r, c) local ap = c.ap; if ap == nil then ap = r.ap end; return ap and ap.me end,
  town = function(r) return r.ch:getCurrentTownLocation() end,
}
local function pget(r, k)
  local vs = SN.vstamp
  local c = rawget(r, "_pc")
  if not c or c.s ~= vs then
    c = { s = vs }; rawset(r, "_pc", c)
    if rawget(r, "_bs") == vs then c.ap = rawget(r, "_ap") or false; c.pl = rawget(r, "_pl") or false end
  end
  local v = c[k]
  if v == nil then
    local ok, val = pcall(PLAZY[k], r, c)
    v = (ok and val) or false
    c[k] = v
  end
  if v == false and k ~= "town" then return nil end
  return v
end
local RMT = { __index = function(r, k)
  if PLAZY[k] then return pget(r, k) end
  local fn = LAZY[k]
  if not fn then return nil end
  local ok, v = pcall(fn, r)
  if not ok or v == nil then v = false end
  rawset(r, k, v)
  return v
end }

local function index_pkey(list)
  local by_pkey = {}
  for _, r in ipairs(list) do
    local k = r.pkey
    if k ~= "" then local b = by_pkey[k]; if b then b[#b + 1] = r else by_pkey[k] = { r } end end
  end
  return by_pkey
end

local function build(stamp)
  local C = G.cfg.snap
  local set = getGameWorld():getCharacterUpdateList()
  local list, by_pkey, n, bad, seen, players = {}, {}, 0, 0, 0, 0
  local maxc = C.max_chars or 3000
  for ch in pairs(set) do
    seen = seen + 1
    if seen > maxc then break end
    local okp, isp = pcall(ch.isPlayerCharacter, ch)
    if okp and isp then players = players + 1
    else
      local r = { ch = ch, _bs = stamp }
      if okp and pcall(f_core, ch, r) then
        pcall(f_fac, ch, r)
        if not pcall(f_plat, ch, r) then r.pkey = "" end
        setmetatable(r, RMT)
        n = n + 1; list[n] = r
        if r.pkey ~= "" then local b = by_pkey[r.pkey]; if b then b[#b + 1] = r else by_pkey[r.pkey] = { r } end end
      else bad = bad + 1 end
    end
  end
  if seen >= 8 and bad * 2 > seen then error("snapshot: " .. bad .. "/" .. seen .. " characters unreadable") end
  return { t = os.clock(), n = n, all = list, by_pkey = by_pkey, players = players, bad = bad, stamp = stamp }
end

-- вид кадра: новая таблица на кадр (кэши потребителей вроде snap.traces_info живут один кадр), записи общие
local function view(base, stamp, now)
  return { t = base.t, n = base.n, list = base.all, by_pkey = base.by_pkey, players = base.players, bad = base.bad, stamp = stamp, built = base.stamp, vt = now }
end

-- проверка в новом кадре: запись остаётся, только если её персонаж в живом наборе (has — хеш по указателю, без разыменования)
local function validate(base)
  local set = getGameWorld():getCharacterUpdateList()
  local okh, has = pcall(function() return set.has end)
  if not okh or type(has) ~= "function" then
    SN.no_has = true
    dlog(SN, "snapshot", "set:has unavailable (" .. type(has) .. "), one-frame rule")
    return false
  end
  local all, keep, n = base.all, nil, 0
  for i, r in ipairs(all) do
    local ok, live = pcall(has, set, rawget(r, "ch"))
    if ok and live then
      n = n + 1
      if keep then keep[n] = r end
    elseif not keep then
      keep = {}
      for j = 1, i - 1 do keep[j] = all[j] end
    end
  end
  if keep then
    SN.dropped = SN.dropped + (#all - n)
    base.all, base.n, base.by_pkey = keep, n, index_pkey(keep)
  end
  return true
end

function G.snapshot(ttl)
  local t0
  local ok, res = pcall(function()
    local C = G.cfg.snap
    if not C or C.enabled == false then return nil end
    local now = os.clock()
    t0 = now
    SN.calls = SN.calls + 1
    if now < SN.pause_until then SN.skipped = SN.skipped + 1; return nil end
    local cur = SN.cur
    if cur and not cur.all then cur, SN.cur, SN.view = nil, nil, nil end   -- снимок прежней версии Gov (перезагрузка скрипта)
    local age = cur and (now - cur.t)
    local okst, stamp = pcall(function() local gw = getGameWorld(); return gw:getTimeStamp() end)
    if okst and type(stamp) == "number" then
      -- КРАШ 2026-11-13 (обыск побеждённых кристаллов): движок удаляет персонажа (смерть/превращение в лут) — вызов метода у устаревшего
      -- указателя роняет игру, pcall не спасает. Поэтому без проверки снимок отдаётся только в ТОМ ЖЕ кадре (метка времени), в паузе — не
      -- дольше same_frame; в новом кадре — только проверенные has() записи, пока снимку не больше ttl_rt; иначе пересборка.
      local v = SN.view
      if cur and v and v.stamp == stamp and now - v.vt >= 0 and now - v.vt <= (C.same_frame or 0.25) then SN.hits = SN.hits + 1; return v end
      local lim = math.min(ttl or C.ttl or 2.0, C.ttl_rt or 0.75)
      if cur and age >= 0 and age <= lim and not SN.no_has then
        local tv = os.clock()
        local okv, valid = pcall(validate, cur)
        if okv and valid then
          local dt = os.clock() - tv
          SN.vals = SN.vals + 1; SN.t_val = SN.t_val + dt; if dt > SN.pk_val then SN.pk_val = dt end
          v = view(cur, stamp, now); SN.view = v; SN.vstamp = stamp
          return v
        end
      end
    else
      if cur and SN.view and age >= 0 and age <= (ttl or C.ttl or 2.0) then SN.hits = SN.hits + 1; return SN.view end   -- без метки (офлайн-заглушки) — прежнее правило ttl
      stamp = nil
    end
    local tb = os.clock()
    local okb, snap = pcall(build, stamp)
    if not okb then
      SN.fails = SN.fails + 1; SN.cur = nil; SN.view = nil; SN.pause_until = now + (C.fail_pause or 20); SN.last_err = tostring(snap)
      dlog(SN, "snapshot", "disabled for " .. (C.fail_pause or 20) .. " s, modules use their own walk: " .. SN.last_err)
      return nil
    end
    local dt = os.clock() - tb
    SN.t_build = SN.t_build + dt; if dt > SN.pk_build then SN.pk_build = dt end
    SN.cur = snap; SN.builds = SN.builds + 1; SN.chars = SN.chars + snap.n
    local v = view(snap, stamp, now); SN.view = v; SN.vstamp = stamp
    return v
  end)
  pcall(function() if t0 then local d = os.clock() - t0; if d > 0 then SN.acc = SN.acc + d end end end)
  if ok then return res end
  return nil
end

function G.snapshot_reset() SN.cur = nil; SN.view = nil; SN.pause_until = -1; SN.no_has = nil end

---------------------------------------------------------------------------------------------- HEALTH: реестр здоровья механик (2026-11-15)
-- Вместо «выкл до перезапуска»: отказ механики -> пауза, растущая по шагам cfg.health.steps (60, 300, 1800 с; дальше последний шаг),
-- по её истечении одна новая попытка (state "retry"); успех -> "ok" (строка recovered). Навсегда ("off") — только h_off: доказанное
-- отсутствие API (reason "noapi") или крэш-сторож нативного вызова (reason "crash"). Только рантайм: в сейв не пишется.
-- Читать (самопроверка): rawget(_G, "KMM_Gov").health.mech[ключ] или KMM_Gov.health_list() — массив копий записей по ключу.
-- Запись: key "Модуль.механика", mod, state ("ok"|"pause"|"retry"|"off"), reason ("error"|"noapi"|"crash"|nil), err (последняя ошибка),
--   fails (отказов подряд, шаг паузы), total (отказов за сессию), oks, recovered, pause (с), retry_at / t_fail / t_ok (os.clock),
--   at_fail / at_off (os.date), desc. Время — os.clock (как у троттлинга); G.hclock можно подменить в тестах.
-- Лог debug.log: «[KMM_Gov] health <ключ>: fail #n -> pause Ns: <err>», «retry», «recovered after n fails», «OFF (<reason>): <why>»,
--   и в сводке report_s: «[KMM_Gov] health: ok N, pause K [..], off M [..]» (только если есть не-ok записи).
G.health = G.health or { v = 1, mech = {} }
G.health.mech = G.health.mech or {}
local function HC()
  local c = G.cfg and G.cfg.health
  return type(c) == "table" and c or { steps = { 60, 300, 1800 } }
end
if G.cfg and G.cfg.health == nil then G.cfg.health = { steps = { 60, 300, 1800 } } end
local function hnow()
  local f = G.hclock
  if type(f) == "function" then local ok, v = pcall(f); if ok and type(v) == "number" then return v end end
  return os.clock()
end
local function hlog(msg)
  pcall(function()
    local fh = io.open((G.cfg and G.cfg.debug_log) or "C:/KenshiModMap/logs/debug.log", "a")
    if fh then fh:write(os.date("%Y-%m-%d %H:%M:%S"), " [KMM_Gov] health ", msg, "\n"); fh:close() end
  end)
end
local function hrec(key)
  local M = G.health.mech
  local r = M[key]
  if not r then
    r = { key = key, mod = (tostring(key):match("^([^%.]+)")) or tostring(key), state = "ok", fails = 0, total = 0, oks = 0, recovered = 0 }
    M[key] = r
  end
  return r
end
local function hstr(e)   -- до 300 байт, не разрывая символ UTF-8 (лог читают как utf-8)
  local s = tostring(e)
  if #s > 300 then s = s:sub(1, 300):gsub("[\192-\255][\128-\191]*$", "") end
  return s
end
function G.h_reg(key, desc)   -- необязательно: механика видна в реестре до первого отчёта
  local ok, r = pcall(function() local r = hrec(key); if desc then r.desc = tostring(desc) end; return r end)
  return ok and r ~= nil
end
function G.h_up(key)   -- можно ли запускать сейчас; пауза истекла -> одна попытка (retry)
  local ok, res = pcall(function()
    local r = G.health.mech[key]
    if not r or r.state == "ok" or r.state == "retry" then return true end
    if r.state == "off" then return false end
    if hnow() >= (r.retry_at or 0) then
      r.state = "retry"
      hlog(key .. ": retry after " .. tostring(r.pause) .. " s pause (fail #" .. r.fails .. ")")
      return true
    end
    return false
  end)
  return (not ok) or res
end
function G.h_ok(key)
  pcall(function()
    local r = G.health.mech[key]
    if r and r.state == "ok" then r.oks = r.oks + 1; return end
    r = r or hrec(key)
    r.oks = r.oks + 1
    if r.state == "off" then return end
    if r.state == "pause" or r.state == "retry" then
      r.state = "ok"; r.recovered = r.recovered + 1; r.t_ok = hnow()
      hlog(key .. ": recovered after " .. r.fails .. " fails")
    end
  end)
end
-- отказ: возвращает паузу в секундах; false — механика выключена навсегда (h_off); nil — сбой самого реестра (вызывающий решает сам)
function G.h_fail(key, err, desc)
  local ok, res = pcall(function()
    local r = hrec(key)
    if desc then r.desc = tostring(desc) end
    r.total = r.total + 1; r.err = hstr(err); r.t_fail = hnow(); r.at_fail = os.date("%Y-%m-%d %H:%M:%S")
    if r.state == "off" then return false end
    local steps = HC().steps or { 60, 300, 1800 }
    local last = steps[#steps] or 1800
    -- долго работал после восстановления -> шаг паузы заново с первого
    if r.state == "ok" and r.t_ok and r.t_fail - r.t_ok > last then r.fails = 0 end
    r.fails = r.fails + 1
    r.pause = steps[math.min(r.fails, #steps)] or last
    r.state, r.reason = "pause", "error"
    r.retry_at = r.t_fail + r.pause
    hlog(key .. ": fail #" .. r.fails .. " -> pause " .. r.pause .. " s: " .. r.err)
    return r.pause
  end)
  if ok then return res end
  return nil
end
-- навсегда: kind "noapi" (функции нет в движке) или "crash" (крэш-сторож); иначе используйте h_fail
function G.h_off(key, why, kind)
  local ok = pcall(function()
    local r = hrec(key)
    if r.state == "off" then return end
    r.state, r.reason, r.err = "off", (kind == "crash" and "crash" or "noapi"), hstr(why)
    r.at_off = os.date("%Y-%m-%d %H:%M:%S"); r.t_fail = hnow()
    hlog(key .. ": OFF (" .. r.reason .. "): " .. r.err)
  end)
  return ok
end
function G.h_get(key)
  local ok, c = pcall(function()
    local r = G.health.mech[key]; if not r then return nil end
    local c = {}; for k, v in pairs(r) do c[k] = v end; return c
  end)
  return ok and c or nil
end
function G.health_list()
  local out = {}
  pcall(function()
    local keys = {}
    for k in pairs(G.health.mech) do keys[#keys + 1] = k end
    table.sort(keys)
    for _, k in ipairs(keys) do local c = {}; for a, b in pairs(G.health.mech[k]) do c[a] = b end; out[#out + 1] = c end
  end)
  return out
end
-- обёртка: пауза -> nil, "paused"; иначе pcall(fn, ...) и отчёт ok/fail. Возвращает ok, результат (как pcall) или nil, "paused"
function G.h_guard(key, fn, ...)
  if not G.h_up(key) then return nil, "paused" end
  local res = { pcall(fn, ...) }
  if res[1] then G.h_ok(key) else G.h_fail(key, res[2]) end
  return unpack(res)
end
function G.health_line()
  local ok, s = pcall(function()
    local n, p, o = 0, {}, {}
    for _, r in ipairs(G.health_list()) do
      if r.state == "off" then o[#o + 1] = r.key .. "(" .. tostring(r.reason) .. ")"
      elseif r.state == "pause" or r.state == "retry" then p[#p + 1] = r.key .. "(#" .. r.fails .. " " .. tostring(r.pause) .. "s)"
      else n = n + 1 end
    end
    if #p == 0 and #o == 0 then return nil end
    return string.format("ok %d, pause %d [%s], off %d [%s]", n, #p, table.concat(p, ", "), #o, table.concat(o, ", "))
  end)
  return ok and s or nil
end

function G.snapshot_stats()
  return { builds = SN.builds, hits = SN.hits, fails = SN.fails, skipped = SN.skipped, chars = SN.chars, last_err = SN.last_err, n = SN.cur and SN.cur.n or 0,
           vals = SN.vals, dropped = SN.dropped, calls = SN.calls, build_ms = SN.t_build * 1000, val_ms = SN.t_val * 1000, total_ms = SN.acc * 1000 }
end

rawset(_G, "KMM_Gov", G)
