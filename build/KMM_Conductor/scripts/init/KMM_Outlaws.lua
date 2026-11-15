-- KMM_Outlaws — «живые» разыскиваемые (2026-11-14, «Живой мир»). Вместо ванильной схемы «награда = NPC, стоящий в точке карты»:
-- дирижёр ведёт 8-14 преступников. Каждый живёт в своём регионе (BIOME_GROUP по карте areasmap) и соседних — климат его банды,
-- банда = родная бродячая банда региона (BIOME_GROUP.homeless spawns / FACTION.biomes). Раз в игровой день преступник:
-- кочует по региону/соседям, рэкетирует город (награда от правоохранителей хозяина города — FACTION «legal system»), грабит караваны,
-- переходит в другую банду региона, растёт в тире (тир = шаблон отряда банды T0..T3). Мир охотится сам: шанс гибели от охотников за
-- головами/ареста растёт с наградой; из тюрьмы бегут. Павший заменяется: новое имя на плакатах (иногда его лейтенант в той же банде).
-- Видимое: игрок рядом с преступником -> KMM_Traces.request: банда идёт к городу рэкета; лидер получает имя преступника и РОДНУЮ награду
-- ядра (Character.crimes:unfairAddToBounty(фракция закона, сумма)) — её видно в окне персонажа, на неё реагируют стража и охотники ядра
-- (AI:findBounty), тело/пленника можно сдать по ванильной механике. Смерть лидера -> гибель преступника + хроника + замена.
-- S3: заспавненная банда становится постоянным отрядом ядра (сейв игры, ход вне видимости по пакету) + ванильный AI_PACKAGE миссии;
-- ключ платуна o.pk в записи — повторная встреча подхватывает тот же отряд (без дублей). Маркеры: persistent ok/FAIL/adopt/lost/released/orphan, package ok/FAIL.
-- X1: охотник несёт разыскиваемого живым у игрока -> весть outlaw_captive_carried; игрок отбил -> outlaw_captive_taken (маркеры captive *).
-- Состояние: S.ext.outlaws (сейв дирижёра, ленивое создание, ~4 КБ). Данные: build/KMM_Conductor/outlaws.json (tools/conductor/gen_outlaws.py).
-- Всё под pcall; ошибка -> модуль выключается до перезапуска; нативный вызов награды — под крэш-сторожем state/probe_bounty_add.*.
-- Лог: C:/KenshiModMap/logs/outlaws.log. Kenshi Lua 5.1; всё — поля таблицы M (лимит локалей).
local TAG = "[KMM_Outlaws] "
local M = { off = false, live = {}, last = -1000, pend = nil, nlog = 0, DAY_EMITS = 0, PROBE = {}, adopt_t = {} }

M.DEF = {
  enabled = true,
  count = 10,            -- целевое число разыскиваемых
  tick_s = 9,
  step_p = 0.55,         -- доля преступников, делающих шаг в игровой день
  max_catchup = 3,
  max_emits_day = 4,
  w_roam = 0.25, w_racket = 0.32, w_raid = 0.18, w_join = 0.025,   -- остальное — залечь на дно
  adj_p = 0.3,           -- шанс уйти в соседний регион (не дальше соседей родного)
  tier_b = { 4000, 12000, 30000 },   -- награда для T1/T2/T3
  justice_base = 0.004, justice_per = 1 / 250000, justice_max = 0.07,
  jail_p = 0.35, escape_p = 0.5,
  heir_p = 0.5,          -- замена — лейтенант павшего (та же банда и регион)
  replace_d = { 2, 6 },  -- дней до появления замены
  decay = 0.01,          -- награда тает за день «на дне»
  vis_r = 22000, cd_h = 60, spawn_p = 0.45, max_live = 2, pend_s = 120, watch_s = 1800,
  native_bounty = true,
  manhunt_heat = 2.5,      -- поборов в одном городе (с затуханием 15 %/день) до облавы закона
  manhunt_days = 5, manhunt_mult = 2.5,   -- облава: столько дней правосудие в регионе сильнее
  hire_p = 0.07,
  local_r = 45000, local_min = 2, local_p = 0.7,   -- PACE: держать 2 разыскиваемых в родных регионах рядом с игроком (новые имена — «местные»)         -- T2+ в день: нанялся во фракцию региона (уходит в KMM_Fates героем)
  sdir = "C:/KenshiModMap/state/",
  log_max = 400,
  -- Q2: дела банды (шина KMM_Deeds) против фракций с законом -> ванильная награда главаря растёт сама
  deed_bounty = true, deed_r = 30000, deed_day = 2, deed_cap = 70000,
  hunt_goal = true,      -- патрулю облавы — ванильная цель HUNT_BOUNTIES (охота через findBounty ядра)
  -- S3: банда/соперник — постоянный отряд ядра (Platoon:setPersistentSquad, живёт в сейве игры, вне видимости его ведёт
  -- UnloadedPlatoonJob пакета), миссию задаёт ванильный AI_PACKAGE (Blackboard:replaceAIPackage). Ошибка -> временный отряд, как раньше.
  persist = true, persist_max = 12, adopt_s = 60, persist_scan = 1500, lost_miss = 3, orph_days = 30,
  pkg = true,
  pkg_racket = "5504-gamedata.base",   -- «Patrol map: Raiders» (ванильные рейдеры; вне экрана UPJOB_TRAVEL_TARGET)
  pkg_roam = "2675-gamedata.base",     -- «Wandering from town to town» (SIG_WANDERING_TOWN_TO_TOWN, UPJOB_TRAVEL_TARGET)
  pkg_hunt = "2957-gamedata.base",     -- «Assault target squad» (SIG_DEFEAT_SQUAD, цель = AItarget = отряд игрока)
  -- X1: охотник несёт разыскиваемого живым рядом с игроком -> весть (outlaw_captive_carried); игрок отбил -> outlaw_captive_taken
  cap = true, cap_scan_s = 15, cap_chars = 400, cap_r = 8000, cap_day = 3, cap_track_s = 1500, cap_min_bounty = 1, cap_pcs = 16,
  cap_seen_max = 8, cap_memory = true,
  -- B1: награда за голову глубже (раздел B1 ниже; docs/core/people.md «Награда за голову»). Своей валюты нет: всё — награда ядра.
  b1 = true,                 -- false: B1 выключен целиком (колбэк не ставится, рост не идёт)
  b1_settle_s = 3,           -- дело ждёт столько реальных секунд, пока ядро само выставит награду
  b1_pend_s = 90,            -- ядро так и не выставило награду за это время -> доплаты нет (дело не наказуемо по ванили)
  b1_dedup_s = 300,          -- одно дело (персонаж, вид, жертва) учитывается раз за столько секунд (свидетелей много)
  b1_pend_max = 12, b1_calls_s = 120,   -- очередь дел; колбэков в секунду сверх — мимо
  b1_price = { murder = 8000, terrorism = 5000, kidnapping = 4000, enslaving = 4000, escape_prison = 3500, assault_vip = 3000,
               slave_freeing = 2000, assault = 1500, stealing = 800, lockpicking = 700, looting = 600, uniform_theft = 600,
               trespassing = 300, smuggling = 0, fencing = 0, farm_eating = 0 },   -- цена дела: ядро доплачивает разницу до неё
  b1_add_max = 15000,        -- доплата за одно дело не больше
  b1_recid = 0.15, b1_recid_max = 1.6,   -- каждое следующее дело перед той же фракцией дороже на 15 % (до x1.6)
  b1_w_law = 1.6, b1_w_unique = 1.5, b1_w_trader = 1.3, b1_w_lawless = 0.25,   -- вес жертвы: страж / уникальный / торговец / без закона
  b1_rate = 0.05, b1_rate_recid = 0.01, b1_rate_max = 0.10,   -- скрылся: рост в игровой день (+1 % за дело сверх первого, до 10 %)
  b1_cap_mult = 3,           -- рост не выше x3 от честной награды (без роста)
  b1_window = 12,            -- растёт не дольше стольких дней после последнего дела (дальше след остывает, ваниль сама гасит)
  b1_min_add = 50, b1_tiers = { 5000, 15000, 40000 }, b1_pcs = 30, b1_rec_max = 40, b1_forget_d = 30,
  b1_npc = true,             -- тот же рост у NPC-разыскиваемых (o.b), медленнее: их награда и так растёт от дел
  b1_npc_rate = 0.015, b1_npc_recid = 0.002, b1_npc_max = 0.04, b1_npc_window = 6, b1_npc_cap = 2,   -- кап NPC: x2 от честной
  b1_npc_tiers = { 10000, 25000, 50000 }, b1_hunt_at = 25000,   -- порог: весть; выше b1_hunt_at — облава закона (HUNT_BOUNTIES)
}
M.DEED_B = { killed = 600, executed = 900, captured = 450 }   -- тяжкие дела: база награды за тир
M.DEED_T = { killed = "killed people of %s", executed = "executed a prisoner of %s", captured = "took people of %s prisoner" }
M.SYL_A = { "Ra", "Ko", "Su", "Ve", "Gri", "Ma", "Ze", "Bo", "Sha", "Dra", "Ni", "Kai", "Jo", "Ur", "Ske", "Tor", "Ya", "Lu", "Ta", "Fe", "Hak", "Oz" }
M.SYL_B = { "r", "rr", "n", "k", "l", "d", "m", "x", "sh", "g", "v" }
M.SYL_C = { "a", "o", "u", "ek", "ar", "en", "ak", "ra", "is", "on", "ug" }
M.EPI = { "the Knife", "Two-Fingers", "the Butcher", "Sandrat", "the Smiler", "Coldeye", "the Tax", "Gravel", "the Leech", "Rustjaw",
          "the Snake", "Bonecutter", "the Debt", "Scald", "the Collector", "Mudfoot", "the Grin", "Saltcrow", "the Widow", "Blackhand" }
M.PRIO = { outlaw_dead = true, outlaw_jailed = true, outlaw_escape = true, outlaw_hired = true, outlaw_manhunt = true, outlaw_new = true,
           outlaw_epithet = true }
-- личность по делам: первое дело, ставшее привычкой, даёт заслуженное прозвище (вместо случайного с рождения) и склонность.
-- k — счётчик в o.cr, n — порог; town — в прозвище город поборов. Порядок — приоритет при одновременном пороге.
M.EARN = {
  { k = "escape", n = 1, ep = { "the Unchained", "Lockbreaker", "the Slippery" } },
  { k = "evade",  n = 2, ep = { "the Ghost", "the Unhunted", "Smoke" } },
  { k = "murder", n = 4, ep = { "Red-Hands", "Gravedigger", "the Butcher" } },
  { k = "racket", n = 6, ep = { "the Tax of %s", "Landlord of %s", "the Toll of %s" }, town = true },
  { k = "raid",   n = 6, ep = { "the Roadwolf", "Caravan-Eater", "the Highwayman" } },
  { k = "join",   n = 2, ep = { "Turncoat", "Many-Flags", "the Weathervane" } },
}
M.CRIME = { racket = "extortion", raid = "caravan robbery", murder = "murder" }

function M.log(msg)
  if M.nlog >= M.DEF.log_max then return end
  M.nlog = M.nlog + 1
  local ok, f = pcall(io.open, "C:/KenshiModMap/logs/outlaws.log", "a")
  if ok and f then f:write(os.date("%Y-%m-%d %H:%M:%S"), " ", tostring(msg), "\n"); f:close() end
  pcall(function() if KenshiLua and KenshiLua.log then KenshiLua.log(TAG .. tostring(msg)) end end)
end
function M.fail(where, err) M.off = true; M.log("disabled until restart in " .. where .. ": " .. tostring(err)) end
function M.cfg()
  local c = M.DEF
  local ok, p = pcall(function() return KMM_Conductor.cfg().params.outlaws end)
  if ok and type(p) == "table" then
    c = {}
    for k, v in pairs(M.DEF) do c[k] = v end
    for k, v in pairs(p) do c[k] = v end
  end
  return c
end
function M.pick(t) return t[math.random(1, #t)] end
function M.today(C)
  local ok, d = pcall(function() return getGameWorld():getTimeStamp_inGameHours():getTotalDays() end)
  if ok and type(d) == "number" then return math.floor(d) end
  local ok2, d2 = pcall(C.day)
  return ok2 and math.floor(d2 or 0) or 0
end
function M.hours(C)
  local ok, h = pcall(function() return getGameWorld():getTimeStamp_inGameHours():getTotalHours() end)
  if ok and type(h) == "number" then return h end
  return M.today(C) * 24
end

-- крэш-сторож нативного вызова (как KMM_Predators): lock до первого вызова в сессии; lock на старте -> .off навсегда
function M.probe_ok(x)
  local st = M.PROBE[x]
  if st == nil then
    local sd = M.cfg().sdir
    local lock, offp = sd .. "probe_" .. x .. ".lock", sd .. "probe_" .. x .. ".off"
    st = true
    pcall(function()
      local f = io.open(offp, "r")
      if f then f:close(); st = false; return end
      f = io.open(lock, "r")
      if f then
        f:close(); st = false
        local o = io.open(offp, "w"); if o then o:write("disabled: previous session crashed in ", x); o:close() end
        os.remove(lock)
        M.log("native method " .. x .. " DISABLED forever: previous session crashed during the call")
      end
    end)
    M.PROBE[x] = st
  end
  return st
end
function M.probe_call(x, fn)
  if not M.probe_ok(x) then return false end
  local lock = M.cfg().sdir .. "probe_" .. x .. ".lock"
  local first = not M.PROBE[x .. "#done"]
  if first then pcall(function() local f = io.open(lock, "w"); if f then f:write(tostring(os.time())); f:close() end end) end
  local ok, err = pcall(fn)
  if first then pcall(os.remove, lock); M.PROBE[x .. "#done"] = true end
  if not ok then M.log("native " .. x .. " error: " .. tostring(err)) end
  return ok
end

-- данные и состояние ------------------------------------------------------------------------------------------------------
function M.data(C)
  if M.D ~= nil then return M.D or nil end
  local d = C.read_json("outlaws.json", "C:/KenshiModMap/build/KMM_Conductor/outlaws.json")
  if type(d) ~= "table" or type(d.regions) ~= "table" then M.D = false; M.log("outlaws.json missing - module idle"); return nil end
  d.homes = {}
  local names = {}
  for nm in pairs(d.regions) do names[#names + 1] = nm end
  table.sort(names)
  for _, nm in ipairs(names) do
    local r = d.regions[nm]
    r.gangs = r.gangs or {}; r.towns = r.towns or {}; r.spots = r.spots or {}; r.adj = r.adj or {}
    if #r.gangs > 0 and (#r.towns > 0 or #r.spots > 0) then d.homes[#d.homes + 1] = nm end
  end
  local tr = C.read_json("traces.json", "C:/KenshiModMap/build/KMM_Conductor/traces.json")
  d.tr = (tr and tr.factions) or {}
  M.D = d
  return d
end
function M.O(S)
  S.ext = S.ext or {}
  local O = S.ext.outlaws
  if type(O) ~= "table" then O = { v = 1, nid = 1, L = {}, q = {}, day = nil }; S.ext.outlaws = O end
  O.L = O.L or {}; O.q = O.q or {}; O.nid = O.nid or 1; O.heat = O.heat or {}; O.hunt = O.hunt or {}
  return O
end
function M.list(O)
  local out = {}
  for _, o in pairs(O.L) do out[#out + 1] = o end
  table.sort(out, function(a, b) return a.i < b.i end)
  return out
end
function M.gname(D, fid) return (D.gangs and D.gangs[fid]) or "a gang" end
function M.law(fid)   -- правоохранители хозяина города: FACTION «legal system» (Faction.myLawEnforcementFaction через KMM_Traces)
  local T = rawget(_G, "KMM_Traces")
  local ok, b = pcall(function() return T.bounty() end)
  if ok and b and b.law_of then
    local ok2, lf = pcall(b.law_of, fid)
    if ok2 and lf then return lf end
  end
  return fid
end

-- рождение ------------------------------------------------------------------------------------------------------------------
function M.new_name(O)
  for _ = 1, 30 do
    local nm = M.pick(M.SYL_A) .. M.pick(M.SYL_B) .. M.pick(M.SYL_C) .. " " .. M.pick(M.EPI)
    local used = false
    for _, o in pairs(O.L) do if o.n == nm then used = true; break end end
    if not used then return nm end
  end
  return M.pick(M.SYL_A) .. M.pick(M.SYL_C) .. " " .. M.pick(M.EPI) .. " " .. O.nid
end
function M.spot(D, rg)   -- точка в регионе: город (окраина) или случайная клетка региона
  local r = D.regions[rg]
  if not r then return nil end
  if #r.towns > 0 and (math.random() < 0.6 or #r.spots == 0) then
    local t = M.pick(r.towns)
    local a = math.random() * 6.2832
    local d = math.random(1500, 4000)
    return t.x + math.cos(a) * d, t.z + math.sin(a) * d, t.sid
  end
  if #r.spots > 0 then local p = M.pick(r.spots); return p[1] + math.random(-400, 400), p[2] + math.random(-400, 400), nil end
  return nil
end
function M.local_homes(D)   -- родные регионы рядом с игроком (город региона ближе local_r): «местные» плакаты
  local T = rawget(_G, "KMM_Traces")
  if not (T and T.near) then return {} end
  local out = {}
  for _, nm in ipairs(D.homes) do
    for _, t in ipairs(D.regions[nm].towns) do if M.near(T, t.x, t.z, M.cfg().local_r) then out[#out + 1] = nm; break end end
  end
  return out
end
function M.born(C, O, D, day, rg, gang, heir_of)
  if not rg then
    if #D.homes == 0 then return nil end
    local loc = M.local_homes(D)
    local nloc = 0   -- сколько уже живёт рядом
    for _, o in pairs(O.L) do for _, nm in ipairs(loc) do if o.hr == nm then nloc = nloc + 1; break end end end
    if #loc > 0 and nloc < M.cfg().local_min and math.random() < M.cfg().local_p then rg = M.pick(loc) else rg = M.pick(D.homes) end
  end
  local r = D.regions[rg]
  if not (r and #r.gangs > 0) then return nil end
  gang = gang or r.gangs[math.min(#r.gangs, math.random(1, math.min(3, #r.gangs)))]
  local o = { i = O.nid, n = M.new_name(O), g = gang, hr = rg, r = rg, b = math.random(3, 9) * 100, bb = {}, cr = {}, t = 0,
              st = "a", since = day, sp = -1000, k = 0, ld = day }
  O.nid = O.nid + 1
  o.x, o.z, o.s = M.spot(D, rg)
  if not o.x then return nil end
  local lf = (r.towns[1] and M.law(r.towns[1].fid)) or gang
  o.bb[lf] = o.b; o.lf = lf
  O.L["o" .. o.i] = o
  local txt
  if heir_of then
    txt = string.format("%s, lieutenant of the late %s, now leads the %s in %s. A bounty of %d cats is posted.", o.n, heir_of, M.gname(D, gang), rg, o.b)
  else
    txt = string.format("A new name on the wanted posters of %s: %s of the %s, %d cats.", rg, o.n, M.gname(D, gang), o.b)
  end
  M.emit(C, D, o, "outlaw_new", txt)
  M.stats.born = M.stats.born + 1
  return o
end

-- события -------------------------------------------------------------------------------------------------------------------
function M.emit(C, D, o, typ, text, extra)
  local prio = M.PRIO[typ]   -- судьбоносные вести (гибель, тюрьма, найм, облава, новое имя) идут вне дневного лимита
  if not prio and M.DAY_EMITS >= (M.cfg().max_emits_day or 4) then return end
  if not prio then M.DAY_EMITS = M.DAY_EMITS + 1 end
  local ev = { type = typ, a = o.g, b = o.lf, town_sid = o.s, leader_name = o.n, region = o.r, bounty = o.b, text = text }
  if extra then for k, v in pairs(extra) do ev[k] = v end end
  pcall(C.emit, ev)
  M.log(string.format("[day %s] %s: %s", tostring(M.cur_day), typ, text))
end
function M.add_bounty(o, fid, amt)
  local lf = M.law(fid)
  if o.b > 30000 then amt = math.floor(amt * 30000 / o.b) end   -- выше 30 тыс. рост замедляется (потолок ~70 тыс., как у крупных ванильных)
  o.bb[lf] = (o.bb[lf] or 0) + amt
  o.b = o.b + amt
  if not M.b1_esc_now then o.ld = M.cur_day or o.ld; o.dn = (o.dn or 0) + 1 end   -- B1: последнее дело и число дел (рецидив)
  local best, bv = o.lf, -1
  for f, v in pairs(o.bb) do if v > bv then best, bv = f, v end end
  o.lf = best
  return lf
end
function M.tier_check(C, D, o, cfg)
  local nt = 0
  for i, th in ipairs(cfg.tier_b) do if o.b >= th then nt = i end end
  if nt > o.t then
    o.t = nt
    M.emit(C, D, o, "outlaw_rise", string.format("%s has grown bold: the %s now run with a bigger, better-armed crew. Bounty %d cats.", o.n, M.gname(D, o.g), o.b))
    M.stats.rise = M.stats.rise + 1
  end
end
function M.earn(C, D, o)   -- заслуженное прозвище: один раз за жизнь; живой отряд у игрока переименовывается сразу
  if o.ek or o.st ~= "a" then return false end
  local cr = o.cr or {}
  for _, e in ipairs(M.EARN) do
    if (cr[e.k] or 0) >= e.n and (not e.town or o.rtn) then
      local base = tostring(o.n):match("^(%S+)") or tostring(o.n)
      local ep, nn
      for _ = 1, 6 do   -- прозвище не должно совпасть с текущим именем (иначе «теперь зовут X» при том же X)
        ep = M.pick(e.ep)
        if e.town then ep = string.format(ep, o.rtn) end
        nn = base .. " " .. ep
        if nn ~= o.n then break end
      end
      if nn == o.n then return false end
      local old = o.n
      o.n, o.ek = nn, e.k
      local lv = M.live["o" .. o.i]
      if lv and lv.named then
        pcall(function() lv.pl:getSquadLeader():setName(nn) end)
        pcall(function() lv.pl:getActivePlatoon():setName(nn .. "'s gang") end)
      end
      M.emit(C, D, o, "outlaw_epithet", string.format("Nobody in %s calls %s that anymore. The name now is %s.", o.r, old, nn), { old_name = old, deed = e.k })
      M.stats.epithet = (M.stats.epithet or 0) + 1
      return true
    end
  end
  return false
end
function M.lean(cfg, o, x)   -- привычка: заслуженное прозвище тянет к своему делу (доля lean_p шагов)
  if not o.ek or math.random() >= (cfg.lean_p or 0.15) then return x end
  if o.ek == "racket" then return cfg.w_roam + 0.001
  elseif o.ek == "raid" or o.ek == "murder" then return cfg.w_roam + cfg.w_racket + 0.001 end
  return x   -- «Призрак»/«Беглец» — своя поблажка в justice/escape; «Перебежчик» — только имя
end
function M.cluster(D, o)   -- куда можно кочевать: родной регион и его соседи (климат банды)
  local h = D.regions[o.hr]
  local ok = { [o.hr] = true }
  if h then for _, a in ipairs(h.adj) do if D.regions[a] then ok[a] = true end end end
  return ok
end
function M.act(C, O, D, cfg, o, day)
  local x = M.lean(cfg, o, math.random())
  local r = D.regions[o.r] or D.regions[o.hr]
  if not r then o.r = o.hr; r = D.regions[o.hr]; if not r then return end end
  if x < cfg.w_roam then
    local nr = o.r
    if math.random() < cfg.adj_p then
      local okr = M.cluster(D, o)
      local cand = {}
      for _, a in ipairs(r.adj) do if okr[a] then cand[#cand + 1] = a end end
      if o.r ~= o.hr then cand[#cand + 1] = o.hr; cand[#cand + 1] = o.hr end   -- тянет домой
      if #cand > 0 then nr = M.pick(cand) end
    end
    local nx, nz, ns = M.spot(D, nr)
    if nx then
      local moved = nr ~= o.r
      o.r, o.x, o.z, o.s = nr, nx, nz, ns
      if moved and math.random() < 0.5 then
        M.emit(C, D, o, "outlaw_move", string.format("%s and the %s were seen moving into %s.", o.n, M.gname(D, o.g), nr))
      end
    end
    M.stats.roam = M.stats.roam + 1
  elseif x < cfg.w_roam + cfg.w_racket and #r.towns > 0 then
    local t
    if o.rt and math.random() < 0.7 then   -- рэкет — регулярная дань: чаще всего свой «подопечный» город
      for _, x2 in ipairs(r.towns) do if x2.sid == o.rt then t = x2; break end end
    end
    t = t or M.pick(r.towns)
    local newtown = o.rt ~= t.sid
    o.rt, o.rtn = t.sid, t.name
    if t.fid ~= o.g then
      local amt = math.random(2, 6) * 100 * (o.t + 1)
      M.add_bounty(o, t.fid, amt)
      o.cr.racket = (o.cr.racket or 0) + 1
      if C.stock_spend then   -- поборы — настоящий убыток склада города (KMM_Stock): роскошь и еда уходят банде
        pcall(C.stock_spend, t.sid, "lux", (cfg.racket_lux or 0.04) * (o.t + 1))
        pcall(C.stock_spend, t.sid, "food", (cfg.racket_food or 0.02) * (o.t + 1))
      end
      o.s, o.x, o.z = t.sid, t.x + math.random(-2500, 2500), t.z + math.random(-2500, 2500)
      O.heat[t.sid] = (O.heat[t.sid] or 0) + (o.ek == "racket" and 0.5 or 1)   -- «Хозяин» города: дань привычная, терпят дольше
      if O.heat[t.sid] >= cfg.manhunt_heat and not O.hunt[t.sid] then M.manhunt(C, O, D, cfg, t, o, day) end
      if newtown or o.t >= 2 or math.random() < 0.25 then M.emit(C, D, o, "outlaw_racket", string.format("%s of the %s is shaking down traders in %s. Bounty now %d cats.", o.n, M.gname(D, o.g), t.name, o.b),
             { town_sid = t.sid, town_name = t.name, b = t.fid }) end
      M.stats.racket = M.stats.racket + 1
    end
  elseif x < cfg.w_roam + cfg.w_racket + cfg.w_raid then
    local t = #r.towns > 0 and M.pick(r.towns) or nil
    local victim = t and t.fid or o.lf
    local amt = math.random(3, 8) * 100 * (o.t + 1)
    M.add_bounty(o, victim, amt)
    o.cr.raid = (o.cr.raid or 0) + 1
    if math.random() < 0.3 then o.cr.murder = (o.cr.murder or 0) + 1; M.add_bounty(o, victim, 500 * (o.t + 1)) end
    if o.t >= 1 and math.random() < 0.35 then M.emit(C, D, o, "outlaw_raid", string.format("A caravan was robbed on the roads of %s; witnesses name %s. Bounty now %d cats.", o.r, o.n, o.b),
           t and { town_sid = t.sid, town_name = t.name, b = t.fid } or nil) end
    M.stats.raid = M.stats.raid + 1
  elseif o.t >= 2 and x < cfg.w_roam + cfg.w_racket + cfg.w_raid + cfg.hire_p and M.hire(C, O, D, cfg, o, r, day) then
    return
  elseif x < cfg.w_roam + cfg.w_racket + cfg.w_raid + cfg.w_join then
    local cand = {}
    for _, g in ipairs(r.gangs) do if g ~= o.g then cand[#cand + 1] = g end end
    if #cand > 0 then
      local old = o.g
      o.g = M.pick(cand)
      o.cr.join = (o.cr.join or 0) + 1
      M.emit(C, D, o, "outlaw_join", string.format("%s has left the %s and joined the %s.", o.n, M.gname(D, old), M.gname(D, o.g)))
      M.stats.join = M.stats.join + 1
    end
  else
    o.b = math.floor(o.b * (1 - cfg.decay))   -- залёг на дно: память закона слабеет
    for f, v in pairs(o.bb) do o.bb[f] = math.floor(v * (1 - cfg.decay)) end
    if o.esc then o.esc = math.floor(o.esc * (1 - cfg.decay)) end
  end
  M.tier_check(C, D, o, cfg)
  M.earn(C, D, o)
end

-- ответ закона и найм ---------------------------------------------------------------------------------------------------------------
function M.manhunt(C, O, D, cfg, t, o, day)   -- город устал платить: его правоохранители объявляют облаву в регионе
  local lf = M.law(t.fid)
  O.hunt[t.sid] = { u = day + cfg.manhunt_days, r = o.r, lf = lf, x = t.x, z = t.z, tn = t.name, oi = o.i }
  O.heat[t.sid] = 0
  M.emit(C, D, o, "outlaw_manhunt", string.format("%s has had enough of %s: patrols of the %s are out hunting the gang in %s.", t.name, o.n,
         tostring(C.name and C.name(lf) or lf), o.r), { town_sid = t.sid, town_name = t.name, b = lf })
  M.stats.manhunt = (M.stats.manhunt or 0) + 1
end
function M.hunted(O, rg)   -- облава идёт в регионе?
  for _, h in pairs(O.hunt) do if h.r == rg then return true end end
  return false
end
function M.hire(C, O, D, cfg, o, r, day)   -- матёрый преступник нанимается к хозяину города региона, где его не ищут
  local F = rawget(_G, "KMM_Fates")
  if not (F and F.adopt) then return false end
  local cand = {}
  for _, t in ipairs(r.towns) do
    local lf = M.law(t.fid)
    if t.fid ~= o.g and not o.bb[lf] and not o.bb[t.fid] then cand[#cand + 1] = t end
  end
  if #cand == 0 then return false end
  local t = M.pick(cand)
  local ok, h = pcall(F.adopt, { n = o.n, f = t.fid, r = "mercenary", t = o.t, rep = -15, x = t.x, z = t.z, s = t.sid })
  if not (ok and h) then return false end
  M.emit(C, D, o, "outlaw_hired", string.format("%s, wanted for %d cats, has signed on as a mercenary captain with the %s in %s.", o.n, o.b,
         tostring(C.name and C.name(t.fid) or t.fid), t.name), { town_sid = t.sid, town_name = t.name, b = t.fid, status = "hired" })
  M.remove(O, o)
  M.queue(O, cfg, day, o)
  M.stats.hired = (M.stats.hired or 0) + 1
  return true
end

-- правосудие мира и замена ------------------------------------------------------------------------------------------------------
function M.remove(O, o) pcall(M.release, o); O.L["o" .. o.i] = nil; M.live["o" .. o.i] = nil end
function M.queue(O, cfg, day, o)
  local heir = math.random() < cfg.heir_p
  O.q[#O.q + 1] = { d = day + math.random(cfg.replace_d[1], cfg.replace_d[2]), r = heir and o.hr or nil, g = heir and o.g or nil,
                    h = heir and o.n or nil }
end
function M.die(C, O, D, cfg, o, day, how)
  M.emit(C, D, o, "outlaw_dead", string.format("%s of the %s %s. The %d-cat bounty is closed.", o.n, M.gname(D, o.g), how, o.b), { status = "dead" })
  if o.pg then local NM = rawget(_G, "KMM_Nemesis"); if NM and NM.on_dead then pcall(NM.on_dead, o, how) end end   -- NEMESIS: соперник погиб
  M.remove(O, o)
  M.queue(O, cfg, day, o)
  M.stats.dead = M.stats.dead + 1
end
function M.hunter(o)   -- охотник из KMM_Fates (наёмник в силе) забирает награду: репутация и шаг к повышению; имя идёт в слух
  if math.random() >= (M.cfg().hunter_p or 0.5) then return nil end
  local F = rawget(_G, "KMM_Fates")
  local ok, hs = pcall(function() return F and F.heroes() end)
  if not (ok and type(hs) == "table") then return nil end
  local cand = {}
  for _, h in ipairs(hs) do if h.r == "mercenary" and h.st == "a" and (h.t or 0) >= o.t - 1 then cand[#cand + 1] = h end end
  if #cand == 0 then return nil end
  local h = M.pick(cand)
  h.rep = math.min(100, (h.rep or 0) + 5 + 3 * o.t); h.w = (h.w or 0) + 1
  M.stats.hunted = (M.stats.hunted or 0) + 1
  return h.n
end
function M.justice(C, O, D, cfg, o, day)
  local p = math.min(cfg.justice_max, cfg.justice_base + o.b * cfg.justice_per) * (1 - 0.15 * o.t)
  if M.hunted(O, o.r) then p = p * cfg.manhunt_mult end
  if o.ek == "evade" then p = p * (cfg.ghost_mult or 0.6) end   -- «Призрак»: правосудию труднее
  if math.random() >= p then return false end
  if math.random() < cfg.jail_p then
    o.st = "j"; o.un = day + math.random(15, 45)
    pcall(M.b1_npc_caught, o)   -- B1: пойман — рост награды сбрасывается
    pcall(M.release, o)   -- S3: банда без главаря больше не постоянная — ядро уберёт её при выгрузке
    M.emit(C, D, o, "outlaw_jailed", string.format("%s was taken alive by bounty hunters near %s and handed to the law.", o.n, o.r), { status = "jailed" })
    M.stats.jail = M.stats.jail + 1
  else
    local hn = M.hunter(o)
    if hn then M.die(C, O, D, cfg, o, day, "was hunted down in " .. o.r .. " by " .. hn .. ", who collected the bounty")
    else
      M.die(C, O, D, cfg, o, day, M.pick({ "was hunted down by bounty hunters in " .. o.r, "was cut down by a town watch in " .. o.r,
                                           "was knifed by their own crew in " .. o.r }))
    end
  end
  return true
end
function M.day_step(C, O, D, day)
  local cfg = M.cfg()
  M.DAY_EMITS = 0; M.cur_day = day
  for k, v in pairs(O.heat) do v = v * 0.9; O.heat[k] = v >= 0.2 and v or nil end
  for k, h in pairs(O.hunt) do
    if day > h.u then
      O.hunt[k] = nil
      local ho = h.oi and O.L["o" .. h.oi]
      if ho and ho.st == "a" then ho.cr = ho.cr or {}; ho.cr.evade = (ho.cr.evade or 0) + 1; M.earn(C, D, ho) end   -- пережил облаву
    end
  end
  for _, o in ipairs(M.list(O)) do
    if O.L["o" .. o.i] then
      if o.st == "j" then
        if day >= (o.un or 0) then
          if math.random() < cfg.escape_p + (o.ek == "escape" and 0.2 or 0) then
            o.st = "a"; o.un = nil; o.b = o.b + 1000
            o.ld = day; o.dn = (o.dn or 0) + 1   -- B1: побег — новое дело, след снова свежий
            o.x, o.z, o.s = M.spot(D, o.hr); o.r = o.hr
            M.emit(C, D, o, "outlaw_escape", string.format("%s has escaped prison and is back in %s. Bounty raised to %d cats.", o.n, o.hr, o.b), { status = "escaped" })
            M.stats.escape = M.stats.escape + 1
            o.cr = o.cr or {}; o.cr.escape = (o.cr.escape or 0) + 1; M.earn(C, D, o)
          else
            M.remove(O, o); M.queue(O, cfg, day, o)
            M.log(string.format("%s executed in prison", o.n))
          end
        end
      elseif o.st == "a" and not M.live["o" .. o.i] and math.random() < cfg.step_p then
        if not M.justice(C, O, D, cfg, o, day) then M.act(C, O, D, cfg, o, day) end
      end
      if O.L["o" .. o.i] and o.st == "a" and not M.live["o" .. o.i] and not M.b1_off then   -- B1: скрылся — награда растёт
        local okb, eb = pcall(M.b1_npc_day, C, O, D, cfg, o, day)
        if not okb then M.b1_off = true; M.log("b1 disabled until restart (npc): " .. tostring(eb)) end
      end
    end
  end
  local keep = {}
  local n = 0; for _ in pairs(O.L) do n = n + 1 end
  for _, q in ipairs(O.q) do
    if day >= q.d and n < cfg.count then
      if M.born(C, O, D, day, q.r, q.g, q.h) then n = n + 1 end
    else keep[#keep + 1] = q end
  end
  O.q = keep
  local guard = 0
  while n + #O.q < cfg.count and guard < 30 do
    guard = guard + 1
    if M.born(C, O, D, day) then n = n + 1 end
  end
  M.stats.days = M.stats.days + 1
end

-- видимое ----------------------------------------------------------------------------------------------------------------------
function M.tier_sid(D, fid, tier)
  local e = D.tr[fid]
  if not (e and e.tiers) then return nil end
  for d = 0, 3 do
    for _, k in ipairs({ tier + d, tier - d }) do
      local sid = e.tiers["T" .. k]
      if k >= 0 and k <= 3 and sid then return sid end
    end
  end
end
function M.native_bounty(o, leader, adopted)   -- РОДНАЯ награда ядра: видна в окне персонажа, на неё идут стража/охотники, сдаётся по ванили
  if not M.cfg().native_bounty then return false end
  local fm = getGameWorld().factionMgr
  local b0 = M.engine_total(leader)
  if adopted and b0 == nil then   -- подхваченный отряд (награда могла лечь в прошлый раз), сумму ядра не прочитать: не удваивать
    M.log(string.format("native bounty skipped on %s: adopted squad, engine total unreadable", o.n)); return false
  end
  if b0 and b0 > 0 then   -- у главаря уже есть награда ядра (сейв, прошлый спавн): докладываем только разницу
    local diff = math.floor(o.b - b0)
    if diff < 100 then M.log(string.format("native bounty ok on %s: already in engine %s (ours %d)", o.n, tostring(b0), o.b)); return true end
    local fo = fm:getFactionByStringID(o.lf)
    local okc = fo and M.probe_call("bounty_add", function() leader.crimes:unfairAddToBounty(fo, diff) end)
    local b1 = M.engine_total(leader)
    M.log(string.format("native bounty %s on %s: top-up %d, engine total %s -> %s (ours %d)", M.verdict(okc and 1 or 0, b0, b1), o.n, diff,
          tostring(b0), tostring(b1), o.b))
    return okc and true or false
  end
  local n, tried = 0, 0
  for lf, amt in pairs(o.bb) do
    if amt >= 100 then
      tried = tried + 1
      local fo = fm:getFactionByStringID(lf)
      if fo and M.probe_call("bounty_add", function() leader.crimes:unfairAddToBounty(fo, math.floor(amt)) end) then n = n + 1 end
    end
  end
  local b1 = M.engine_total(leader)
  local okr, thr = pcall(function() return leader.crimes:getBountyRecognitionThreshold() end)
  M.log(string.format("native bounty %s on %s: %d of %d factions, engine total %s -> %s (ours %d, recognition %s)",
        M.verdict(n, b0, b1), o.n, n, tried, tostring(b0), tostring(b1), o.b, tostring(okr and thr)))
  return n > 0
end
function M.engine_total(leader)
  local ok, v = pcall(function() return leader.crimes:getTotalBounty() end)
  return ok and type(v) == "number" and v or nil
end
-- маркер для session_report: ok — ядро приняло (сумма выросла); FAIL — вызов упал/отключён/нет фракции или сумма не изменилась;
-- unverified — вызов прошёл, но сумму ядра прочитать нельзя
function M.verdict(n, b0, b1)
  if n == 0 then return "FAIL" end
  if not (b0 and b1) then return "unverified" end
  return b1 > b0 and "ok" or "FAIL"
end

-- Q2: дела мира -> ванильная награда ----------------------------------------------------------------------------------------
-- Шина KMM_Deeds (type="deed": kind, a — кто, b — кому, by_player/to_player, n, x/z — место). Тяжкое дело (убийство, казнь, плен)
-- банды разыскиваемого против фракции с законом поднимает его награду у правоохранителей пострадавшей (тот же o.bb, что и у рэкета);
-- если отряд главаря сейчас у игрока — прибавка сразу ложится в ядро (unfairAddToBounty), иначе — при следующем выходе банды.
-- Дедуп: одно дело (жертва, вид) на главаря в игровой день, не больше deed_day дел в день, потолок deed_cap. Дело NPC, не игрока.
function M.lawful(D, fid)   -- фракция с законом: хозяин города в outlaws.json или есть своя полиция (myLawEnforcementFaction)
  if not D.lawful then
    D.lawful = {}
    for _, r in pairs(D.regions) do for _, t in ipairs(r.towns or {}) do if t.fid then D.lawful[t.fid] = true end end end
  end
  return D.lawful[fid] == true or M.law(fid) ~= fid
end
function M.deed_who(O, cfg, ev)   -- чьё дело: живой отряд банды у игрока, иначе ближайший к месту разыскиваемый той же банды
  local best, bd
  for _, o in ipairs(M.list(O)) do
    if o.g == ev.a and o.st == "a" then
      local lv = M.live["o" .. o.i]
      if lv and lv.named then return o, lv end
      if ev.x and ev.z and o.x and o.z then
        local d = (o.x - ev.x) ^ 2 + (o.z - ev.z) ^ 2
        if d <= cfg.deed_r * cfg.deed_r and (not bd or d < bd) then best, bd = o, d end
      end
    end
  end
  return best, nil
end
function M.dstat(k) M.stats[k] = (M.stats[k] or 0) + 1 end
function M.on_deed(ev)
  if M.off or M.deed_off or type(ev) ~= "table" then return end
  local cfg = M.cfg()
  local base = M.DEED_B[ev.kind]
  if cfg.deed_bounty == false or not base or ev.by_player or ev.to_player or not (ev.a and ev.b) or ev.a == ev.b then return end
  local C = rawget(_G, "KMM_Conductor")
  local S = C and C.state and C.state()
  if type(S) ~= "table" or type(S.ext) ~= "table" or type(S.ext.outlaws) ~= "table" then return end
  local D = M.data(C)
  if not D then return end
  local O = M.O(S)
  local o, lv = M.deed_who(O, cfg, ev)
  if not o then return end
  if not M.lawful(D, ev.b) then M.dstat("deed_lawless"); return end
  local day = M.today(C)
  if type(o.dd) ~= "table" or o.dd.d ~= day then o.dd = { d = day, n = 0, k = {} } end
  local dk = tostring(ev.b) .. "|" .. ev.kind
  if o.dd.k[dk] then M.dstat("deed_dup"); return end
  if o.dd.n >= cfg.deed_day or o.b >= cfg.deed_cap then M.dstat("deed_capped"); return end
  o.dd.k[dk] = true; o.dd.n = o.dd.n + 1
  local amt = math.floor(base * (o.t + 1) * (1 + 0.25 * (math.min(math.max(tonumber(ev.n) or 1, 1), 5) - 1)))
  amt = math.max(0, math.min(amt, cfg.deed_cap - o.b))
  local b0 = o.b
  local lf = M.add_bounty(o, ev.b, amt)
  local inc = o.b - b0
  o.cr = o.cr or {}
  if ev.kind ~= "captured" then o.cr.murder = (o.cr.murder or 0) + 1 end   -- дела копят «Красные руки» (M.EARN)
  M.dstat("deed")
  local nat = "later"
  if lv and inc >= 1 and cfg.native_bounty then
    local okl, leader = pcall(function() return lv.pl:getSquadLeader() end)
    local fo
    pcall(function() fo = getGameWorld().factionMgr:getFactionByStringID(lf) end)
    if okl and leader and fo then
      local e0 = M.engine_total(leader)
      local okc = M.probe_call("bounty_add", function() leader.crimes:unfairAddToBounty(fo, math.floor(inc)) end)
      local e1 = M.engine_total(leader)
      nat = M.verdict(okc and 1 or 0, e0, e1) .. " " .. tostring(e0) .. "->" .. tostring(e1)
    else
      nat = "FAIL no leader/faction"
    end
  end
  M.log(string.format("deed bounty +%d on %s (%s %s, law %s): native %s", inc, o.n, ev.kind, tostring(ev.b), tostring(lf), nat))
  local vn = tostring(ev.b)
  pcall(function() local nm = C.name and C.name(ev.b); if nm then vn = nm end end)
  M.cur_day = day
  M.emit(C, D, o, "outlaw_deed", string.format("Witnesses%s name %s: the %s %s. Bounty now %d cats.",
         ev.town_name and (" near " .. ev.town_name) or "", o.n, M.gname(D, o.g), string.format(M.DEED_T[ev.kind], vn), o.b),
         { town_sid = ev.town_sid or o.s, town_name = ev.town_name, b = ev.b, deed = ev.kind })
  M.tier_check(C, D, o, cfg)
  M.earn(C, D, o)
end
function M.on_deed_g(ev)   -- ошибка выключает только связку дел, не модуль
  if type(ev) == "table" and ev.by_player and ev.witnessed == false then M.dstat("deed_unwitnessed"); return end   -- Y1: дело игрока без свидетелей - мир о нём не знает
  local ok, err = pcall(M.on_deed, ev)
  if not ok then M.deed_off = true; M.log("deed bounty disabled until restart: " .. tostring(err)) end
end
function M.hunt_goal(h, pls)   -- патрулю облавы — ванильная цель HUNT_BOUNTIES: цель он выбирает сам (findBounty, порог узнавания)
  if M.cfg().hunt_goal == false then return end
  local tgt
  local lv = M.live["o" .. tostring(h.oi)]
  if lv then pcall(function() tgt = lv.pl:getSquadLeader() end) end
  local n, m = 0, 0
  for _, pl in ipairs(pls or {}) do
    m = m + 1
    local ok, leader = pcall(function() return pl:getSquadLeader() end)
    if ok and leader and M.probe_call("hunt_goal", function() leader:addGoal(TaskType.HUNT_BOUNTIES, tgt) end) then n = n + 1 end
  end
  M.log(string.format("hunt goal HUNT_BOUNTIES %s: %d of %d patrols from %s%s", n > 0 and "ok" or "FAIL", n, m, tostring(h.tn),
        tgt and ", subject = live gang leader" or ""))
end
function M.dress(o, lv)
  local ok, leader = pcall(function() return lv.pl:getSquadLeader() end)
  if not (ok and leader) then return false end
  local ok2 = pcall(function() leader:setName(o.n) end)
  pcall(function() lv.pl:getActivePlatoon():setName(o.n .. "'s gang") end)
  if ok2 then
    lv.named = true
    pcall(M.native_bounty, o, leader, lv.adopted)
  end
  return ok2
end
-- S3: постоянный отряд ядра вместо временного спавна --------------------------------------------------------------------------
-- После спавна (заявка KMM_Traces) отряд делается постоянным: ядро хранит его в сейве игры (Faction.unloadedPlatoons) и ведёт вне
-- видимости по UnloadedPlatoonJob его пакета; миссию задаёт ванильный AI_PACKAGE. Запись помнит ключ платуна (o.pk) — повторная
-- материализация сначала ищет уже существующий отряд (ключ, иначе имя главаря у загруженных) и не плодит дубли.
function M.pkey(p) return p:getPlatoonStringID() end
function M.pis(p) return p:isPersistentSquad() end
function M.plead(p) return p:getSquadLeader() end
function M.pbb(p) return p:getBlackboard() end
function M.pact(p) return p:getActivePlatoon() end
function M.ppos(p) return p:getPosition() end
function M.pdead(p, loaded)   -- у выгруженного платуна персонажей нет: верим только флагу isDead (0 персонажей — не гибель)
  local okd, d = pcall(function() return p.isDead end)
  if okd and d == true then return true end
  if not loaded then return false end
  local okc, n = pcall(function() return p:getCharacterCount() end)
  return okc and n == 0
end
function M.mlog(o, msg)   -- маркер S3: outlaws.log, у соперника ещё и nemesis.log
  M.log(msg)
  if o and o.pg then local NM = rawget(_G, "KMM_Nemesis"); if NM and NM._N and NM._N.log then pcall(NM._N.log, msg) end end
end
function M.find_pl(o, keyonly)   -- (Platoon, загружен?) или nil; keyonly — без поиска по имени главаря (сироты)
  local fo
  pcall(function() fo = getGameWorld().factionMgr:getFactionByStringID(o.pf or o.g) end)
  if not fo then return nil end
  local cap = M.cfg().persist_scan or 1500
  for _, m in ipairs({ "getActivePlatoons", "getUnloadedPlatoons" }) do
    local ok, lst = pcall(function() return fo[m](fo) end)
    local n = 0
    if ok and lst then pcall(function() n = #lst end) end
    for i = 1, math.min(n, cap) do
      local p = lst[i]
      if p then
        local okk, k = pcall(M.pkey, p)
        if okk and k and k ~= "" and k == o.pk then return p, m == "getActivePlatoons" end
        if m == "getActivePlatoons" and not keyonly then   -- ключ сменился: главарь по имени (только у загруженных — у невыгруженных персонажей нет)
          local okl, leader = pcall(M.plead, p)
          local okn, nm = false, nil
          if okl and leader then okn, nm = pcall(function() return leader:getName() end) end
          if okn and nm == o.n and okk and type(k) == "string" and k ~= "" then
            o.pk = k
            return p, true
          end
        end
      end
    end
  end
  return nil
end
function M.orph(O) O.orph = O.orph or {}; return O.orph end   -- потерянные постоянные отряды: ключ ещё может всплыть в мире
function M.npersist(O, except)   -- постоянных сейчас: записи с ключом + сироты (их ещё держит сейв)
  local np = #M.orph(O)
  for _, x in pairs(O.L) do if x.pk and x ~= except then np = np + 1 end end
  return np
end
function M.mat(C, O, o, pl, kind)   -- временный спавн -> постоянный отряд + ванильный пакет миссии; при сбое — как раньше
  local cfg = M.cfg()
  if cfg.persist ~= false then
    local np = M.npersist(O, o)
    local why
    if np >= (cfg.persist_max or 12) then why = "cap " .. np
    elseif not M.probe_ok("persist") then why = "probe disabled"
    else
      local okk, k = pcall(M.pkey, pl)
      if not (okk and type(k) == "string" and k ~= "") then why = "no platoon key (could not find it again)"
      else
        M.probe_call("persist", function() pl:setPersistentSquad(true) end)
        local okv, v = pcall(M.pis, pl)
        if okv and v == true then
          o.pk, o.pf, o.pk_miss = k, o.g, nil
          M.mlog(o, string.format("persistent ok %s (%s, key %s): engine keeps the squad off-screen", o.n, tostring(o.g), o.pk))
        else
          why = "isPersistentSquad " .. tostring(v)
          pcall(function() pl:setPersistentSquad(false) end)   -- полупостоянный не оставлять
        end
      end
    end
    if why then M.mlog(o, string.format("persistent FAIL %s: %s - temporary squad as before", o.n, why)) end
    M.stats.persist = (M.stats.persist or 0) + (o.pk and 1 or 0)
  end
  if cfg.pkg ~= false then
    local sid = cfg["pkg_" .. kind]
    local gd, board
    if sid then pcall(function() gd = getGameWorld().gamedata:getData(sid, (itemType and itemType.AI_PACKAGE) or 72) end) end
    local okb, b = pcall(M.pbb, pl)
    if okb then board = b end
    if not gd then M.mlog(o, string.format("package FAIL %s %s on %s: no AI_PACKAGE data", kind, tostring(sid), o.n))
    elseif not board then M.mlog(o, string.format("package FAIL %s %s on %s: no blackboard", kind, sid, o.n))
    else
      local okc = M.probe_call("ai_package", function() board:replaceAIPackage(gd) end)
      local okn, nm = pcall(function() return board:getCurrentAIPackageName() end)
      M.mlog(o, string.format("package %s %s %s on %s (current %s)", okc and "ok" or "FAIL", kind, sid, o.n, tostring(okn and nm or "?")))
      if okc then M.stats.pkg = (M.stats.pkg or 0) + 1 end
    end
  end
end
function M.lose(C, O, o, why)   -- запись отпускает ключ; отряд, если всплывёт, отпустит сверка сирот
  local or_ = M.orph(O)
  or_[#or_ + 1] = { k = o.pk, f = o.pf or o.g, n = o.n, d = M.today(C) }
  M.mlog(o, string.format("persistent lost %s (key %s, %s): kept as orphan to release - temporary spawns again", o.n, tostring(o.pk), why))
  o.pk, o.pk_miss = nil, nil
end
function M.adopt(C, O, D, cfg, o)   -- сверка записи с её постоянным отрядом в мире
  local id = "o" .. o.i
  local p, loaded = M.find_pl(o)
  if not p then   -- один промах — не потеря (переход active<->unloaded, фракция не отдалась): lost после lost_miss промахов подряд
    o.pk_miss = (o.pk_miss or 0) + 1
    if o.pk_miss >= (cfg.lost_miss or 3) then M.lose(C, O, o, o.pk_miss .. " misses") end
    return
  end
  o.pk_miss = nil
  if M.pdead(p, loaded) then M.stats.slain = M.stats.slain + 1; M.die(C, O, D, cfg, o, M.today(C), "fell in a fight near " .. o.r); return end
  local okp, pos = pcall(M.ppos, p)
  if okp and pos then
    local okx, x, z = pcall(function() return pos.x, pos.z end)
    if okx and type(x) == "number" and type(z) == "number" then o.x, o.z = x, z end   -- где отряд на самом деле: ядро — источник правды
  end
  if not loaded then return end
  local lv = { pl = p, t = os.clock(), pk = true, adopted = true }
  M.live[id] = lv
  local named = M.dress(o, lv)   -- adopted: награда ядра только разницей (M.native_bounty); главарь ещё не загружен — доделает watch
  M.stats.adopt = (M.stats.adopt or 0) + 1
  M.mlog(o, string.format("persistent adopt %s: existing squad loaded near player, no new spawn", o.n))
  local day = M.today(C)
  if o.pg and named and o.pg.seen_day ~= day then   -- подхват — не новая встреча: возвращение соперника не чаще раза в игровой день
    o.pg.seen_day = day
    local okl, leader = pcall(M.plead, p)
    local NM = rawget(_G, "KMM_Nemesis")
    if okl and leader and NM and NM.on_spawn then pcall(NM.on_spawn, o, leader) end
  end
end
function M.orph_step(C, O, cfg)   -- одна сирота за проход: нашлась по ключу — отпустить; старше orph_days — забыть
  local or_ = M.orph(O)
  if #or_ == 0 then return false end
  local x = table.remove(or_, 1)
  local p = M.find_pl({ pk = x.k, pf = x.f, g = x.f, n = x.n }, true)
  if p then
    local ok = M.probe_call("persist", function() p:setPersistentSquad(false) end)
    M.log(string.format("persistent orphan released %s (key %s): %s", tostring(x.n), tostring(x.k), ok and "ok" or "FAIL"))
  elseif M.today(C) - (x.d or 0) > (cfg.orph_days or 30) then
    M.log(string.format("persistent orphan dropped %s (key %s): not seen for %d days", tostring(x.n), tostring(x.k), cfg.orph_days or 30))
  else
    or_[#or_ + 1] = x
  end
  return true
end
function M.vis_persist(C, O, D, cfg, T)   -- за тик сверяется не больше одной записи (ближние к игроку первыми), каждая не чаще adopt_s
  if cfg.persist == false then return end
  local now = os.clock()
  local pick, pnear
  for _, o in ipairs(M.list(O)) do
    local id = "o" .. o.i
    if o.pk and o.st == "a" and not M.live[id] and now - (M.adopt_t[id] or -1e9) >= (cfg.adopt_s or 60) then
      local nr = o.x and M.near(T, o.x, o.z, cfg.vis_r) or false
      if not pick or (nr and not pnear) then pick, pnear = o, nr end
      if pnear then break end
    end
  end
  if pick then M.adopt_t["o" .. pick.i] = now; M.adopt(C, O, D, cfg, pick)
  elseif now - (M.adopt_t["#orph"] or -1e9) >= (cfg.adopt_s or 60) then M.adopt_t["#orph"] = now; M.orph_step(C, O, cfg) end
end
function M.release(o)   -- главарь пал/в тюрьме/нанялся: отряд снова временный, ядро уберёт его при выгрузке
  if not o.pk then return end
  local p = M.find_pl(o)
  local key = o.pk
  if p then
    o.pk, o.pk_miss = nil, nil
    local ok = M.probe_call("persist", function() p:setPersistentSquad(false) end)
    M.mlog(o, string.format("persistent released %s (key %s): %s", o.n, tostring(key), ok and "ok" or "FAIL"))
  else   -- сейчас не найден: в сироты, отпустит orph_step, когда всплывёт
    local C = rawget(_G, "KMM_Conductor")
    local S = C and C.state and C.state()
    if type(S) == "table" then M.lose(C, M.O(S), o, "release while not found") else o.pk = nil end
  end
end
function M.near(T, x, z, r) local ok, v = pcall(T.near, x, z, r); return ok and v == true end
-- Y5/M6: соперник (o.pg - охота на игрока) недавно отошёл, оценив силы игрока (KMM_Nemesis): новый отряд охоты сразу не шлём.
-- Нет Nemesis или функции, ошибка - поведение прежнее.
function M.withdrew(o)
  if not o.pg then return false end
  local NM = rawget(_G, "KMM_Nemesis")
  local f = type(NM) == "table" and rawget(NM, "withdrew_recent")
  if type(f) ~= "function" then return false end
  local ok, r = pcall(f, o)
  if ok and r == true then M.dstat("vis_withdrew"); return true end
  return false
end
function M.vis(C, O, D, cfg, T)
  pcall(M.vis_persist, C, O, D, cfg, T)   -- S3: сперва — уже существующие постоянные отряды (без нового спавна)
  if M.pend and os.clock() - M.pend.t < cfg.pend_s then return end
  M.pend = nil
  local nl = 0; for _ in pairs(M.live) do nl = nl + 1 end
  if nl >= cfg.max_live then return end
  local hrs = M.hours(C)
  for _, o in ipairs(M.list(O)) do
    local id = "o" .. o.i
    if o.st == "a" and o.x and not o.pk and (hrs - (o.sp or -1000)) >= cfg.cd_h and not M.live[id] and M.near(T, o.x, o.z, cfg.vis_r)
       and not M.withdrew(o) then
      if math.random() < cfg.spawn_p then
        local sid = M.tier_sid(D, o.g, o.t)
        if sid then
          local tw
          if o.s then for _, t in ipairs((D.regions[o.r] or {}).towns or {}) do if t.sid == o.s then tw = t; break end end end
          o.sp = hrs
          local tx, tz = tw and tw.x or o.x, tw and tw.z or o.z
          if o.pg then   -- NEMESIS: соперник идёт к игроку, а не к городу
            local NM = rawget(_G, "KMM_Nemesis")
            local okp, px, pz = pcall(function() return NM._N.player_pos() end)
            if okp and px then tx, tz = px, pz end
          end
          local job = { tag = o.pg and "nemesis" or "outlaw", fid = o.g, sid = sid, n = 1, size = 2 + o.t, from_x = o.x, from_z = o.z,
                        to_x = tx, to_z = tz, to_fid = (not o.pg) and tw and tw.fid or nil,
                        target = o.pg and "player" or nil,   -- S3: соперник — AItarget = игрок (цель пакета охоты)
                        on_spawn = function(pls)
                          M.pend = nil
                          local pl = pls and pls[1]
                          if pl then
                            local lv = { pl = pl, t = os.clock() }
                            M.live[id] = lv
                            M.dress(o, lv)
                            M.stats.spawn = M.stats.spawn + 1
                            local okm, em = pcall(M.mat, C, O, o, pl, o.pg and "hunt" or (tw and "racket" or "roam"))
                            if not okm then M.mlog(o, "persistent FAIL " .. o.n .. ": " .. tostring(em)) end
                            lv.pk = o.pk and true or nil
                            if o.pg then
                              o.pg.seen_day = M.today(C)   -- встреча сегодня была: подхват того же отряда её не повторит
                              local NM = rawget(_G, "KMM_Nemesis")
                              local okl, leader = pcall(function() return pl:getSquadLeader() end)
                              if NM and NM.on_spawn and okl and leader then pcall(NM.on_spawn, o, leader) end
                            end
                            M.log(string.format("gang of %s (%s T%d, bounty %d) spawned near player", o.n, M.gname(D, o.g), o.t, o.b))
                          end
                        end }
          local okq, acc = pcall(T.request, job)
          if okq and acc then M.pend = { t = os.clock(), id = id } end
        end
        return
      end
    end
  end
end
function M.vis_hunt(C, O, D, cfg, T)   -- облава рядом с игроком: патруль закона идёт от города к логову банды
  if M.pend and os.clock() - M.pend.t < cfg.pend_s then return end
  for k, h in pairs(O.hunt) do
    if not h.sp and M.near(T, h.x, h.z, cfg.vis_r) then
      local o = O.L["o" .. tostring(h.oi)]
      local sid = M.tier_sid(D, h.lf, 1)
      h.sp = true
      if sid then
        local okq, acc = pcall(T.request, { tag = "manhunt", fid = h.lf, sid = sid, n = 1, size = 4, from_x = h.x, from_z = h.z,
                                            to_x = o and o.x or h.x, to_z = o and o.z or h.z,
                                            on_spawn = function(pls) pcall(M.hunt_goal, h, pls) end })
        if okq and acc then M.pend = { t = os.clock(), id = k }; M.stats.patrol = (M.stats.patrol or 0) + 1; M.log("manhunt patrol from " .. tostring(h.tn)) end
      end
      return
    end
  end
end
function M.watch(C, O, D)
  local cfg = M.cfg()
  for id, lv in pairs(M.live) do
    local o = O.L[id]
    if o and lv.pk and o.pk and os.clock() - lv.t > cfg.watch_s then   -- S3: постоянный отряд ещё загружен — держим; выгружен — сверка vis_persist
      local oka, ap = pcall(M.pact, lv.pl)
      if oka and ap then lv.t = os.clock() end
    end
    if not o or os.clock() - lv.t > cfg.watch_s then M.live[id] = nil
    else
      local ok, leader = pcall(function() return lv.pl:getSquadLeader() end)
      local gone = false
      if ok and leader then
        if not lv.named then M.dress(o, lv)
        else
          local okn, nm = pcall(function() return leader:getName() end)
          if okn and nm and nm ~= o.n then gone = true end
        end
        local okd, d = pcall(function() return leader:isDead() end)
        if okd and d then gone = true end
      end
      local okp, pd = pcall(function() return lv.pl.isDead end)
      if okp and pd == true then gone = true end
      if gone and lv.named then
        M.stats.slain = M.stats.slain + 1
        M.die(C, O, D, cfg, o, M.today(C), "fell in a fight near " .. o.r)
      end
    end
  end
end

-- X1: перехват пленника охотника ------------------------------------------------------------------------------------------------
-- Ваниль: охотник (цель HUNT_BOUNTIES, стража) несёт разыскиваемого живым к клетке (задача FIND_CAGE_AND_PUT_IN_IF_BOUNTY, на этом же
-- стоит условие диалога DC_CARRYING_BOUNTY_ALIVE). Мы только замечаем это у игрока и пускаем весть «охотник X несёт Y в Z». Решение
-- игрока: отбить и сдать самому (оплата ванильная: стойка наград/клетка), отпустить (ванильная память освобождённого) или пропустить.
-- Своих наград нет. Чтение по BindingsReference: поле Character.isCarryingSomething, метод getCarryingObject (hand по значению),
-- hand.getCharacter/toString, Character.crimes.getTotalBounty. Обход — снимок KMM_Gov (загруженные NPC), порциями по курсору;
-- без снимка — простой (своего обхода нет). Состояние только в сессии и только строки (ключ hand, имена, ключ платуна охотника):
-- указателей между тактами нет; охотник для памяти ищется заново в свежем снимке. Маркеры: captive scan/carried/taken/gone/memory.
function M.cap_st()
  local K = M.cap
  if not K then K = { cur = 1, t = -1e9, seen = {}, names = {}, took = {}, day = -1, n = 0 }; M.cap = K end
  return K
end
function M.cap_field(ch) return ch.isCarryingSomething end
function M.cap_who(ch)   -- кого несёт персонаж: (Character, ключ-строка hand или nil) или nil
  local h = ch:getCarryingObject()
  if not h then return nil end
  local cap = h:getCharacter()
  if not cap then return nil end
  local okk, k = pcall(function() return h:toString() end)
  return cap, (okk and type(k) == "string" and k ~= "") and k or nil
end
function M.cap_players(cfg)   -- персонажи игрока этого такта (не больше cap_pcs); указатели не сохраняются
  local out = {}
  pcall(function()
    for _, c in pairs(getPlayerInterface():getAllPlayerCharacters()) do
      if #out >= (cfg.cap_pcs or 16) then break end
      out[#out + 1] = c
    end
  end)
  return out
end
function M.cap_dest(D, hfid, x, z)   -- куда несут (?): ближайший город фракции охотника или её закона, иначе ближайший город
  local own, od, any, ad
  for _, r in pairs(D.regions) do
    for _, t in ipairs(r.towns or {}) do
      if t.x and t.z then
        local d = (t.x - x) ^ 2 + (t.z - z) ^ 2
        if not ad or d < ad then any, ad = t, d end
        if t.fid and (not od or d < od) and (t.fid == hfid or M.law(t.fid) == hfid) then own, od = t, d end
      end
    end
  end
  return own or any
end
function M.cap_fname(C, fid)
  local nm = tostring(fid)
  pcall(function() local v = C.name and C.name(fid); if v and v ~= "" then nm = v end end)
  return nm
end
function M.cap_outlaw(O, who)   -- пленник — наш разыскиваемый? (только для текста; судьбу записи не меняем: оплату и тюрьму ведёт ядро)
  for _, o in pairs(O.L) do if o.n == who and o.st == "a" then return o end end
  return nil
end
function M.cap_seen(C, O, D, cfg, K, r, day)
  local ch = rawget(r, "ch")
  local okc, cap, key = pcall(M.cap_who, ch)
  if not (okc and cap) then return end
  local okd, dead = pcall(function() return cap:isDead() end)
  if not okd or dead then return end   -- живым: мёртвое тело — не пленник (DC_CARRYING_BOUNTY_ALIVE)
  local okp, isp = pcall(function() return cap:isPlayerCharacter() end)
  if not okp or isp then return end    -- несут персонажа игрока — это охота на него (Traces BNT), не весть
  local okb, b = pcall(function() return cap.crimes:getTotalBounty() end)
  if not (okb and type(b) == "number" and b >= (cfg.cap_min_bounty or 1)) then return end
  local okn, who = pcall(function() return cap:getName() end)
  if not (okn and type(who) == "string" and who ~= "") then return end
  local cfid
  pcall(function() local f = cap:getFaction(); local gd = f and (f:getData() or f.data); cfid = gd and gd.stringID end)
  local hfid = rawget(r, "fid")
  if not hfid or hfid == cfid then return end   -- свои несут раненого — не охота
  local hk = key   -- строка hand пленника (toString); nil - hand не прочитался, сверка перехвата только по имени
  key = key or (who .. "|" .. tostring(cfid))
  local now = os.clock()
  local e = K.seen[key]
  if e then e.last = now; local pk = rawget(r, "pkey"); if pk and pk ~= "" then e.hpk = pk end; return end
  local nseen, oldest = 0, nil
  for k, v in pairs(K.seen) do nseen = nseen + 1; if not oldest or v.last < K.seen[oldest].last then oldest = k end end
  if nseen >= (cfg.cap_seen_max or 8) and oldest then K.seen[oldest] = nil end
  local hn = "A bounty hunter"
  pcall(function() local v = ch:getName(); if v and v ~= "" then hn = v end end)
  local x, z = rawget(r, "x"), rawget(r, "z")
  local t = M.cap_dest(D, hfid, x, z)
  e = { who = who, hk = hk, cf = cfid, hf = hfid, hn = hn, hpk = rawget(r, "pkey"), b = math.floor(b), t0 = now, last = now,
        town = t and t.name or "the nearest cage", tsid = t and t.sid }
  K.seen[key] = e
  local rep = K.names[who] ~= nil and day - K.names[who] <= 1   -- тот же пленник снова на плечах (уронили и подняли): весть уже была
  if rep or K.n >= (cfg.cap_day or 3) then
    M.dstat(rep and "cap_repeat" or "cap_capped")
    M.log(string.format("captive carried (no event, %s): %s by %s (%s), bounty %d", rep and "repeat" or "day cap", who, hn, hfid, e.b))
    return
  end
  K.n = K.n + 1; K.names[who] = day
  local o = M.cap_outlaw(O, who)
  local txt = string.format("%s of the %s carries %s alive toward %s. %d cats on that head, paid to whoever hands it in.",
                            hn, M.cap_fname(C, hfid), o and ("the wanted " .. who) or who, e.town, e.b)
  pcall(C.emit, { type = "outlaw_captive_carried", a = hfid, b = cfid, who = who, hunter = hn, town_name = e.town, town_sid = e.tsid,
                  x = t and t.x or x, z = t and t.z or z, bounty = e.b, oi = o and o.i or nil, text = txt })
  M.dstat("cap_carried")
  M.log(string.format("[day %s] captive carried: %s (%s, bounty %d%s) by %s (%s) toward %s", tostring(day), who, tostring(cfid), e.b,
        o and (", wanted o" .. o.i) or "", hn, hfid, e.town))
end
function M.cap_hunter(e)   -- охотник заново из свежего снимка (ключ платуна + имя): указатель живёт только в этом такте
  local G = rawget(_G, "KMM_Gov")
  if not (G and G.snapshot and e.hpk and e.hpk ~= "") then return nil end
  local ok, snap = pcall(G.snapshot)
  if not (ok and snap and snap.by_pkey) then return nil end
  for _, r in ipairs(snap.by_pkey[e.hpk] or {}) do
    local ch = rawget(r, "ch")
    local okn, nm = pcall(function() return ch:getName() end)
    if okn and nm == e.hn then
      local okd, d = pcall(function() return ch:isDead() end)
      if okd and not d then return ch end
    end
  end
  return nil
end
function M.cap_taken(C, K, cfg, e, pc)
  local pn = "someone"
  pcall(function() local v = pc:getName(); if v and v ~= "" then pn = v end end)
  local dup = K.took[e.who] == K.day   -- один пленник — одна весть в день (уронил и снова поднял — не второй перехват)
  K.took[e.who] = K.day
  M.log(string.format("captive taken: %s from %s (%s) by player %s%s", e.who, e.hn, tostring(e.hf), pn, dup and " (repeat, no event)" or ""))
  if dup then return end
  M.dstat("cap_taken")
  pcall(C.emit, { type = "outlaw_captive_taken", a = e.hf, b = e.cf, who = e.who, hunter = e.hn, town_name = e.town, town_sid = e.tsid,
                  by_player = true, bounty = e.b,
                  text = string.format("%s snatched %s from %s of the %s on the road to %s. The %d cats now go to whoever reaches a cage first.",
                                       pn, e.who, e.hn, M.cap_fname(C, e.hf), e.town, e.b) })
  if cfg.cap_memory == false then return end
  local NM = rawget(_G, "KMM_Nemesis")
  if not (NM and NM.remember) then return end
  local hch = M.cap_hunter(e)   -- родная память ядра: охотник помнит, что игрок увёл его добычу
  if hch then
    local okr = pcall(NM.remember, hch, "LT_STOLE_FROM_ME")
    M.log(string.format("captive memory: %s LT_STOLE_FROM_ME %s", e.hn, okr and "sent" or "FAIL"))
  else
    M.log(string.format("captive memory skipped: hunter %s not loaded or down/dead", e.hn))
  end
end
-- M2: перехват - тот же hand пленника (toString). По имени - только если hand не прочитался ни у охотника, ни у игрока:
-- родовое имя («Dust Bandit») у разных персонажей совпадает, и ложный перехват дал бы LT_STOLE_FROM_ME охотнику.
function M.cap_match(e, hk, nm)
  if e.hk ~= nil or hk ~= nil then return e.hk ~= nil and hk == e.hk end
  return nm ~= nil and nm == e.who
end
function M.cap_track(C, K, cfg, now)   -- отбил ли игрок: пленник теперь на плечах персонажа игрока (тот же hand)
  local held = {}   -- кого несут персонажи игрока в этом такте: { pc, ключ hand, имя } (один опрос на персонажа)
  for _, pc in ipairs(M.cap_players(cfg)) do
    local okc, cap, k2 = pcall(M.cap_who, pc)
    if okc and cap then
      local okn, nm = pcall(function() return cap:getName() end)
      held[#held + 1] = { pc, k2, okn and nm or nil }
    end
  end
  for key, e in pairs(K.seen) do
    if not e.took then
      for _, h in ipairs(held) do
        if M.cap_match(e, h[2], h[3]) then e.took = true; M.cap_taken(C, K, cfg, e, h[1]); break end
      end
    end
    if now - e.last > (cfg.cap_track_s or 1500) then
      if not e.took then M.log(string.format("captive gone: %s (hunter %s, %s) - caged, dropped or out of sight", e.who, e.hn, tostring(e.hf))) end
      K.seen[key] = nil
    end
  end
end
function M.cap_step(C, O, D, cfg)
  if cfg.cap == false then return end
  local K = M.cap_st()
  local now = os.clock()
  local day = M.today(C)
  if K.day ~= day then
    K.day, K.n = day, 0
    for k, d in pairs(K.names) do if day - d > 1 then K.names[k] = nil end end
    for k, d in pairs(K.took) do if d ~= day then K.took[k] = nil end end
  end
  if next(K.seen) ~= nil then M.cap_track(C, K, cfg, now) end
  if now - K.t < (cfg.cap_scan_s or 15) then return end
  K.t = now
  local G = rawget(_G, "KMM_Gov")
  local snap
  if G and G.snapshot then local ok, s = pcall(G.snapshot); if ok then snap = s end end
  if not (snap and snap.list) then
    if not K.nosnap then K.nosnap = true; M.log("captive scan idle: no KMM_Gov snapshot (no own walk)") end
    return
  end
  local pos = {}
  for _, pc in ipairs(M.cap_players(cfg)) do
    local okp, x, z = pcall(function() local p = pc:getPosition(); return p.x, p.z end)
    if okp and type(x) == "number" and type(z) == "number" then pos[#pos + 1] = { x, z } end
  end
  local list = snap.list
  local cnt = #list
  if #pos == 0 or cnt == 0 then return end
  if K.cur > cnt then K.cur = 1 end
  local r2 = (cfg.cap_r or 8000) ^ 2
  local n, fields, hits = 0, 0, 0
  for _ = 1, math.min(cnt, cfg.cap_chars or 400) do
    local r = list[K.cur]
    K.cur = K.cur % cnt + 1
    n = n + 1
    if r and not rawget(r, "dead") then
      local ok, v = pcall(M.cap_field, rawget(r, "ch"))
      if ok and v ~= nil then fields = fields + 1 end
      local x, z = rawget(r, "x"), rawget(r, "z")
      if ok and v == true and x and z then
        for _, p in ipairs(pos) do
          if (p[1] - x) ^ 2 + (p[2] - z) ^ 2 <= r2 then hits = hits + 1; M.cap_seen(C, O, D, cfg, K, r, day); break end
        end
      end
    end
  end
  if not K.probe then   -- один раз за сессию: читается ли поле вообще (проверка ✓код -> ✓игра)
    K.probe = true
    M.log(string.format("captive scan: %d of %d chars checked, carry field readable %d, carrying near player %d", n, cnt, fields, hits))
  end
end

-- B1 (2026-11-15) НАГРАДА ЗА ГОЛОВУ ГЛУБЖЕ: цена дела, вес жертвы, «пойман / не пойман». Всё — награда ядра (BountyManager, ✓код), своей валюты нет.
-- Ванильные суммы за вид преступления в данных не лежат (gamedata: только CHARACTER «bounty amount» у отдельных NPC), их считает ядро
-- (BountyManager.getBountyForCrime), поэтому цена правится в рантайме, а не потоком данных.
--  (а) колбэк BountyManager::notifyCrimeWitnessed(self, faction, againstWho, expiryTime, crimeType): self.me — преступник (?),
--      у персонажа игрока дело ставится в очередь (только строки и числа). Через b1_settle_s тик проверяет, что ядро САМО выставило
--      награду (getActualBounty у фракции _getBountyFaction(faction) выросла), и доплачивает разницу до цены дела:
--      b1_price[вид] x вес жертвы x рецидив минус ванильная сумма (unfairAddToBounty, крэш-сторож bounty_add). Ядро не дало — и мы нет.
--  (б) вес жертвы (hand.getCharacter): страж (isLawEnforcement) / уникальный, знать (isUnique) / торговец (isATrader) — множитель;
--      жертва из фракции без закона (банда из outlaws.json, нет города и полиции) — b1_w_lawless. Дверь/ящик (жертвы нет) — 1.
--  (в) раз в игровой день: персонаж игрока с наградой ядра, который скрылся (жив, не IN_PRISON, не в цепях, не похищен, не на плечах),
--      получает рост b1_rate (+рецидив, до b1_rate_max) не дольше b1_window дней после последнего дела, кап = честная награда x b1_cap_mult.
--      Пойман — рост сбрасывается; награды у ядра нет (выплатил, отсидел, помилован, истекла) — запись снимается.
--      NPC-разыскиваемые (o): тот же рост на o.b через M.add_bounty (в ядро ложится при выходе банды, M.native_bounty); тюрьма — сброс.
--  (г) пороги: игрок — C.emit outlaw_pc_wanted, NPC — outlaw_wanted_up (слухи: префикс outlaw_); NPC выше b1_hunt_at — облава закона
--      (M.manhunt: патруль с ванильной целью HUNT_BOUNTIES). Охотников на игрока шлёт KMM_Traces (bounty_hunt) по той же награде ядра.
-- Маркеры outlaws.log: «b1 hook», «b1 vanilla price», «b1 price ok/FAIL/skip», «b1 no engine bounty», «b1 grow ok/FAIL», «b1 caught»,
-- «b1 cleared», «b1 npc grow», «b1 npc caught», «b1 tier», «b1 manhunt».
M.B1_CRIME = { [1] = "enslaving", [2] = "lockpicking", [3] = "stealing", [4] = "murder", [5] = "assault", [6] = "assault_vip",
               [7] = "slave_freeing", [8] = "smuggling", [9] = "terrorism", [10] = "looting", [11] = "trespassing", [12] = "escape_prison",
               [13] = "fencing", [14] = "farm_eating", [15] = "kidnapping", [16] = "uniform_theft" }   -- CrimeEnum (EnumsReference)
M.b1 = { pend = {}, seen = {}, sec = -1, secn = 0, vb = {}, nlog = 0 }
function M.b1_stat(k, n) M.stats["b1_" .. k] = (M.stats["b1_" .. k] or 0) + (n or 1) end
function M.b1_hk(h)   -- ключ hand: toString() (✓игра у предметов; у персонажей стабильность между сессиями ?)
  if type(h) == "string" then return h end
  local ok, s = pcall(function() return h:toString() end)
  if ok and type(s) == "string" and s ~= "" then return s end
end
function M.b1_fsid(f)
  if not f then return nil end
  local gd = f:getData() or f.data
  return gd and gd.stringID
end
function M.b1_weight(cfg, D, who, vf)   -- вес жертвы и почему
  local okc, v = pcall(function() return who and who:getCharacter() end)
  local function yes(fn) local ok, r = pcall(fn); return ok and r == true end
  if okc and v then
    local w, why = 0, nil
    if yes(function() return v:isLawEnforcement() end) and cfg.b1_w_law > w then w, why = cfg.b1_w_law, "law" end
    if yes(function() return v:isUnique() end) and cfg.b1_w_unique > w then w, why = cfg.b1_w_unique, "unique" end
    if yes(function() return v:isATrader() end) and cfg.b1_w_trader > w then w, why = cfg.b1_w_trader, "trader" end
    if why then return w, why end
  end
  if vf and D and D.gangs and D.gangs[vf] and not M.lawful(D, vf) then return cfg.b1_w_lawless, "lawless" end
  if not (okc and v) then return 1, "none" end
  return 1, "common"
end
function M.b1_on_crime(bm, fac, who, expiry, crime)   -- колбэк ядра: дешёвые проверки, только запись в очередь
  if M.off or M.b1_off then return end
  local cfg = M.C1 or M.DEF
  if cfg.b1 == false then return end
  local c = tonumber(crime) or -1
  local cn = M.B1_CRIME[c]
  if not cn then return end
  local now = os.clock()
  local s = math.floor(now)
  if s ~= M.b1.sec then M.b1.sec, M.b1.secn = s, 0 end
  M.b1.secn = M.b1.secn + 1
  if M.b1.secn > cfg.b1_calls_s then M.b1_stat("flood"); return end
  local me = bm and bm.me
  if not (me and me:isPlayerCharacter()) then return end
  local pk = M.b1_hk(me:getHandle())
  if not pk then M.b1_stat("nokey"); return end
  local vf = M.b1_fsid(fac)
  local vk = (who and M.b1_hk(who)) or vf or "?"
  local dk = pk .. "|" .. c .. "|" .. vk
  local t0 = M.b1.seen[dk]
  if t0 and now - t0 < cfg.b1_dedup_s then M.b1_stat("dup"); return end
  if #M.b1.pend >= cfg.b1_pend_max then M.b1_stat("full"); return end
  M.b1.seen[dk] = now
  local lfo = fac
  pcall(function() lfo = bm:_getBountyFaction(fac) or fac end)
  local lf = M.b1_fsid(lfo) or vf
  if not lf then M.b1_stat("nofac"); return end
  local okb, b0 = pcall(function() return bm:getActualBounty(lfo) end)
  local D = M.D or nil
  local w, why = M.b1_weight(cfg, D, who, vf)
  local okn, nm = pcall(function() return me:getName() end)
  M.b1.pend[#M.b1.pend + 1] = { pk = pk, nm = okn and nm or "?", lf = lf, vf = vf, c = c, cn = cn, w = w, why = why,
                                b0 = okb and tonumber(b0) or nil, t = now }
  M.b1_stat("queued")
end
function M.b1_hook()
  M.b1_hooked = false
  if not (Events and Events.on) then return end
  local ok, err = pcall(Events.on, "BountyManager::notifyCrimeWitnessed", function(bm, fac, who, exp, cr)
    if M.off or M.b1_off then return end
    local okc, e = pcall(M.b1_on_crime, bm, fac, who, exp, cr)
    if not okc then M.b1_off = true; M.log("b1 disabled until restart (callback): " .. tostring(e)) end
  end)
  M.b1_hooked = ok
  M.log(ok and "b1 hook notifyCrimeWitnessed registered" or ("b1 hook FAIL: " .. tostring(err)))
end
function M.b1_pcs(cfg)   -- ключ hand -> персонаж игрока этого такта (указатели не сохраняются)
  local out, n = {}, 0
  pcall(function()
    for _, ch in pairs(getPlayerInterface():getAllPlayerCharacters()) do
      if n >= cfg.b1_pcs then break end
      local okh, h = pcall(function() return ch:getHandle() end)
      local k = okh and M.b1_hk(h)
      if k then out[k] = ch; n = n + 1 end
    end
  end)
  return out
end
function M.b1_actual(ch, lf)   -- (сумма ядра у фракции lf, Faction) или nil
  local fo
  pcall(function() fo = getGameWorld().factionMgr:getFactionByStringID(lf) end)
  if not fo then return nil end
  local ok, v = pcall(function() return ch.crimes:getActualBounty(fo) end)
  if ok and type(v) == "number" then return v, fo end
  return nil, fo
end
function M.b1_vanilla(ch, c)   -- ванильная сумма ядра за вид преступления (static getBountyForCrime), кэш; лог один раз на вид
  if M.b1.vb[c] ~= nil then return M.b1.vb[c] or nil end
  local ok, v = pcall(function() return ch.crimes:getBountyForCrime(c) end)
  M.b1.vb[c] = (ok and type(v) == "number") and v or false
  M.log(string.format("b1 vanilla price %s = %s", M.B1_CRIME[c] or tostring(c), ok and tostring(v) or ("unreadable: " .. tostring(v))))
  return M.b1.vb[c] or nil
end
function M.b1_add(ch, fo, amt)   -- unfairAddToBounty под крэш-сторожем Outlaws; -> ok, сумма до, сумма после
  local e0, e1
  pcall(function() e0 = ch.crimes:getActualBounty(fo) end)
  local okc = M.probe_call("bounty_add", function() ch.crimes:unfairAddToBounty(fo, math.floor(amt)) end)
  pcall(function() e1 = ch.crimes:getActualBounty(fo) end)
  return okc, e0, e1
end
function M.b1_rec(O, pk, lf, nm)
  O.pb = O.pb or {}
  local key = pk .. "|" .. lf
  local r = O.pb[key]
  if not r then
    local n = 0
    for _ in pairs(O.pb) do n = n + 1 end
    if n >= (M.C1 or M.DEF).b1_rec_max then return nil end
    r = { k = pk, lf = lf, nm = nm, base = 0, esc = 0, n = 0, last = 0, tr = 0 }
    O.pb[key] = r
  end
  if nm and nm ~= "?" then r.nm = nm end
  return r
end
function M.b1_tier(C, cfg, r, cur, pf)   -- порог награды игрока -> весть (слухи)
  local hit = 0
  for i, v in ipairs(cfg.b1_tiers or {}) do if cur >= v then hit = i end end
  if hit <= (r.tr or 0) then return end
  r.tr = hit
  local ln = r.lf
  pcall(function() local x = C.name and C.name(r.lf); if x then ln = x end end)
  M.log(string.format("b1 tier %d: %s wanted by %s for %d", hit, tostring(r.nm), tostring(r.lf), cur))
  M.b1_stat("tier")
  pcall(C.emit, { type = "outlaw_pc_wanted", a = pf, b = r.lf, by_player = true, bounty = cur, tier = hit, crime = r.cw, who = r.nm,
                  text = string.format("The %s have raised the price on %s: %d cats, dead or alive.", ln, tostring(r.nm), cur) })
end
function M.b1_pend_step(C, O, D, cfg, day, pcs)
  local now = os.clock()
  for k, t in pairs(M.b1.seen) do if now - t > 2 * cfg.b1_dedup_s then M.b1.seen[k] = nil end end
  if #M.b1.pend == 0 then return end
  local keep = {}
  local pf = C.cfg().player_faction
  for _, e in ipairs(M.b1.pend) do
    if now - e.t < cfg.b1_settle_s then keep[#keep + 1] = e
    else
      local ch = pcs[e.pk]
      local cur, fo
      if ch then cur, fo = M.b1_actual(ch, e.lf) end
      local r = O.pb and O.pb[e.pk .. "|" .. e.lf]
      local last = r and r.last or 0
      if cur and cur > 0 and (cur > (e.b0 or cur) or cur > last) then
        r = M.b1_rec(O, e.pk, e.lf, e.nm)
        if r then
          local vb = M.b1_vanilla(ch, e.c) or math.max(0, cur - math.max(e.b0 or 0, last))
          local recm = math.min(cfg.b1_recid_max, 1 + cfg.b1_recid * r.n)
          local price = tonumber((cfg.b1_price or {})[e.cn]) or 0
          local add = math.floor(price * e.w * recm - vb + 0.5)
          add = math.max(0, math.min(add, cfg.b1_add_max))
          local res, e1 = "skip", cur
          if add >= cfg.b1_min_add then
            local okc, a0, a1 = M.b1_add(ch, fo, add)
            res = M.verdict(okc and 1 or 0, a0, a1)
            e1 = tonumber(a1) or (cur + (okc and add or 0))
          end
          r.n = r.n + 1; r.ld = day; r.caught = nil
          if not r.cwp or price > r.cwp then r.cw, r.cwp = e.cn, price end
          r.base = math.max(1, e1 - (r.esc or 0)); r.last = e1
          M.b1_stat("price")
          M.log(string.format("b1 price %s: %s %s vs %s (victim %s x%.2f, deed #%d x%.2f) vanilla %d target %d add %d, engine %d -> %d",
                res, tostring(e.nm), e.cn, e.lf, e.why, e.w, r.n, recm, vb, math.floor(price * e.w * recm + 0.5), add, cur, e1))
          M.b1_tier(C, cfg, r, e1, pf)
        end
      elseif now - e.t > cfg.b1_pend_s then
        M.b1_stat("nobounty")
        M.log(string.format("b1 no engine bounty: %s %s vs %s (engine %s, before %s) - deed not punished by vanilla, no surcharge",
              tostring(e.nm), e.cn, e.lf, tostring(cur), tostring(e.b0)))
      else keep[#keep + 1] = e end
    end
  end
  M.b1.pend = keep
end
function M.b1_caught(ch)   -- пойман: в тюрьме ядра, в цепях, похищен, на чужих плечах или мёртв
  local function yes(fn) local ok, r = pcall(fn); return ok and r == true end
  local US = rawget(_G, "UseStuffState")
  local prison = (US and US.IN_PRISON) or 2
  if yes(function() return ch:isDead() end) then return "dead" end
  if yes(function() return ch.inSomething == prison end) then return "prison" end
  if yes(function() return ch.isChained == true end) then return "chained" end
  if yes(function() return ch:isKidnapped() end) then return "kidnapped" end
  if yes(function() return ch:isBeingCarried() end) then return "carried" end
end
function M.b1_pc_day(C, O, D, cfg, day, pcs)
  if not O.pb then return end
  local pf = C.cfg().player_faction
  local keys = {}
  for k in pairs(O.pb) do keys[#keys + 1] = k end
  table.sort(keys)
  for _, key in ipairs(keys) do
    local r = O.pb[key]
    local ch = pcs[r.k]
    if not ch then
      r.miss = (r.miss or 0) + 1
      if r.miss > cfg.b1_forget_d then O.pb[key] = nil; M.log("b1 forget " .. tostring(r.nm) .. " (character not found " .. r.miss .. " days)") end
    else
      r.miss = nil
      local cur, fo = M.b1_actual(ch, r.lf)
      if cur == nil then M.b1_stat("unread")
      elseif cur <= 0 then
        O.pb[key] = nil; M.b1_stat("cleared")
        M.log(string.format("b1 cleared: %s vs %s (paid, served, pardoned or expired; grown %d over %d deeds)", tostring(r.nm), r.lf, r.esc or 0, r.n or 0))
      else
        local why = M.b1_caught(ch)
        if why then
          if not r.caught then M.log(string.format("b1 caught (%s): %s vs %s, bounty %d, growth %d reset", why, tostring(r.nm), r.lf, cur, r.esc or 0)); M.b1_stat("caught") end
          r.caught, r.esc, r.base, r.last = why, 0, cur, cur
        else
          r.caught = nil
          if cur < (r.last or cur) * 0.8 then r.base, r.esc = cur, 0 end   -- ядро сняло часть (выплата, срок): новая точка отсчёта
          r.last = cur
          if day - (r.ld or day) <= cfg.b1_window then
            local rate = math.min(cfg.b1_rate_max, cfg.b1_rate + cfg.b1_rate_recid * math.max(0, (r.n or 1) - 1))
            local add = math.floor(math.min(cur * rate, math.max(1, r.base) * cfg.b1_cap_mult - cur))
            if add >= cfg.b1_min_add and fo then
              local okc, a0, a1 = M.b1_add(ch, fo, add)
              local e1 = tonumber(a1) or (cur + (okc and add or 0))
              if okc then r.esc = (r.esc or 0) + math.max(0, e1 - cur) end
              r.last = e1
              M.b1_stat("grow")
              M.log(string.format("b1 grow %s: %s vs %s +%d (%.0f%%/day, deeds %d, cap %d), engine %s -> %s", M.verdict(okc and 1 or 0, a0, a1),
                    tostring(r.nm), r.lf, add, rate * 100, r.n or 0, math.floor(math.max(1, r.base) * cfg.b1_cap_mult), tostring(a0), tostring(a1)))
              M.b1_tier(C, cfg, r, e1, pf)
            end
          end
        end
      end
    end
  end
end
function M.b1_step(C, O, D, cfg, day)
  if #M.b1.pend == 0 and O.pb_day == day then return end
  local pcs = M.b1_pcs(cfg)
  M.b1_pend_step(C, O, D, cfg, day, pcs)
  if O.pb_day ~= day then
    O.pb_day = day
    M.b1_pc_day(C, O, D, cfg, day, pcs)
  end
end
function M.b1_npc_caught(o)   -- NPC взят живым: рост награды снят
  local e = o.esc or 0
  if e <= 0 then return end
  local nb = math.max(1, o.b - e)
  local f = nb / math.max(1, o.b)
  for k, v in pairs(o.bb or {}) do o.bb[k] = math.floor(v * f) end
  M.log(string.format("b1 npc caught: %s, bounty %d -> %d (growth reset)", o.n, o.b, nb))
  o.b, o.esc, o.b1t = nb, 0, nil
end
function M.b1_npc_day(C, O, D, cfg, o, day)
  if cfg.b1_npc == false then return end
  if not o.lf or o.lf == o.g or (D.gangs and D.gangs[o.lf]) then return end   -- закона нет: расти некому
  if day - (o.ld or o.since or day) > cfg.b1_npc_window then return end      -- залёг давно: след остыл
  local rate = math.min(cfg.b1_npc_max, cfg.b1_npc_rate + cfg.b1_npc_recid * (o.dn or 0))
  local fair = math.max(1, o.b - (o.esc or 0))
  local add = math.floor(math.min(o.b * rate, fair * (cfg.b1_npc_cap or cfg.b1_cap_mult) - o.b))
  if add < cfg.b1_min_add then return end
  local b0 = o.b
  M.b1_esc_now = true
  local ok, err = pcall(M.add_bounty, o, o.lf, add)
  M.b1_esc_now = nil
  if not ok then error(err) end
  o.esc = (o.esc or 0) + (o.b - b0)
  M.b1_stat("npc_grow")
  if M.b1.nlog < 60 then M.b1.nlog = M.b1.nlog + 1; M.log(string.format("b1 npc grow: %s +%d (%.1f%%/day, deeds %d) -> %d", o.n, o.b - b0, rate * 100, o.dn or 0, o.b)) end
  local hit = 0
  for i, v in ipairs(cfg.b1_npc_tiers or {}) do if o.b >= v then hit = i end end
  if hit > (o.b1t or 0) then
    o.b1t = hit
    M.b1_stat("npc_tier")
    M.emit(C, D, o, "outlaw_wanted_up", string.format("Nobody has caught %s of the %s, and the price keeps climbing: %d cats now.", o.n, M.gname(D, o.g), o.b),
           { status = "wanted" })
  end
  if o.b >= cfg.b1_hunt_at and not o.b1h and not M.hunted(O, o.r) then
    local r = D.regions[o.r] or D.regions[o.hr]
    for _, t in ipairs((r and r.towns) or {}) do
      if t.fid and t.fid ~= o.g then
        o.b1h = true
        M.manhunt(C, O, D, cfg, t, o, day)
        M.log(string.format("b1 manhunt: %s at %d cats - law of %s goes hunting (HUNT_BOUNTIES patrol)", o.n, o.b, tostring(t.name)))
        break
      end
    end
  end
end

-- тик ----------------------------------------------------------------------------------------------------------------------------
function M.tick()
  if M.off then return end
  local now = os.clock()
  local cfg0 = M.cfg()
  if cfg0.enabled == false or now - M.last < (cfg0.tick_s or 9) then return end
  M.last = now
  local C = rawget(_G, "KMM_Conductor")
  if not (C and C.state and C.cfg and C.read_json and C.emit) then return end
  if M.sub_id == nil and C.subscribe then   -- Q2: подписка на шину дел (лениво: порядок загрузки модулей не важен)
    local oks, id = pcall(C.subscribe, "deed", M.on_deed_g)
    M.sub_id = oks and id or false
    M.log(oks and "deed bus subscribed" or ("deed bus subscribe failed: " .. tostring(id)))
  end
  local S = C.state()
  if type(S) ~= "table" or not S.F then return end
  if M.live_S ~= S then   -- S3/H3: загружен другой сейв (новая таблица состояния) — указатели Platoon прошлого мира не трогать
    if M.live_S ~= nil then M.log("world changed: live squads and adopt timers reset") end
    M.live, M.adopt_t, M.pend, M.live_S, M.cap = {}, {}, nil, S, nil
    M.b1.pend, M.b1.seen = {}, {}   -- B1: дела прошлого мира не доплачиваются
  end
  local day = M.today(C)
  if day <= 0 then return end
  local D = M.data(C)
  if not D then return end
  local O = M.O(S)
  if not O.day then O.day = day - 1 end
  if day > O.day then
    local steps = math.min(day - O.day, cfg0.max_catchup or 3)
    for i = 1, steps do M.day_step(C, O, D, O.day + i) end
    O.day = day
  end
  M.watch(C, O, D)
  if not M.cap_off then   -- X1: ошибка выключает только перехват пленников, не модуль
    local okc, ec = pcall(M.cap_step, C, O, D, cfg0)
    if not okc then M.cap_off = true; M.log("captive watch disabled until restart: " .. tostring(ec)) end
  end
  if cfg0.b1 ~= false and not M.b1_off then   -- B1: дела игрока -> цена по делу; раз в день — рост у скрывшихся
    M.C1 = cfg0
    if M.b1_hooked == nil then M.b1_hook() end
    local okb, eb = pcall(M.b1_step, C, O, D, cfg0, day)
    if not okb then M.b1_off = true; M.log("b1 disabled until restart: " .. tostring(eb)) end
  end
  local T = rawget(_G, "KMM_Traces")
  if T and T.request and T.near then M.vis(C, O, D, cfg0, T); M.vis_hunt(C, O, D, cfg0, T) end
end
M.stats = { days = 0, born = 0, rise = 0, roam = 0, racket = 0, raid = 0, join = 0, jail = 0, escape = 0, dead = 0, spawn = 0, slain = 0 }

function M.guarded()
  local ok, err = pcall(function()
    local G = rawget(_G, "KMM_Gov")
    if G and G.run then return G.run("outlaws", M.tick) end
    return M.tick()
  end)
  if not ok then M.fail("tick", err) end
end

KMM_Outlaws = {
  state = function() local C = rawget(_G, "KMM_Conductor"); local S = C and C.state and C.state(); return S and S.ext and S.ext.outlaws end,
  wanted = function() local C = rawget(_G, "KMM_Conductor"); local S = C and C.state and C.state(); return S and M.list(M.O(S)) or {} end,
  stats = function() return M.stats end,
  disabled = function() return M.off and { outlaws = true } or {} end,
  live = function() return M.live end,
  add_bounty = function(rec, victim_fid, amt) return M.add_bounty(rec, victim_fid, amt) end,   -- обёртки для KMM_Fates (без своей логики)
  native_bounty = function(rec, leader) return M.native_bounty(rec, leader) end,
  lawful = function(fid) local C = rawget(_G, "KMM_Conductor"); local D = C and M.data(C); return D and M.lawful(D, fid) or false end,
  _tick = function() M.last = -1000; M.tick() end,
  b1 = function() local C = rawget(_G, "KMM_Conductor"); local S = C and C.state and C.state(); return S and S.ext and S.ext.outlaws and S.ext.outlaws.pb end,
  _M = M,
}
if Events and Events.on then pcall(Events.on, "GameWorld::charsUpdate", M.guarded) end
