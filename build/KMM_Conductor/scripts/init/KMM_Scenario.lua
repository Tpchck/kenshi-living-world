-- KMM_Scenario (Z1, 2026-11-15): тестовые сценарии первой игровой сессии (новая игра, 30-60 мин).
-- Полностью инертен без файла C:/KenshiModMap/state/scenario.txt (та же папка state, что у recruitrace.off и крэш-сторожей):
--   файл читается один раз за сессию на первом такте; нет файла -> модуль выключен, ни одного вызова ядра и модулей.
-- Файл есть (пишут scenario_<имя>.bat в корне проекта, удаляет scenario_off.bat): имя сценария, один раз за мир
--   (метка S.ext.scenario.done[имя] в сейве дирижёра: повторная загрузка того же мира не повторяет), старт через ~15-20 с,
--   когда дирижёр поднял состояние и есть персонаж игрока. Сценарий = шаги; шаг ждёт своего условия (wait) до max секунд.
-- Механик своих нет: шаги только подталкивают существующие пути модулей (KMM_Traces.tgm, KMM_RecruitRace.pick/start,
--   C.camp().try, C.coresync, KMM_Nemesis._N.make, KMM_Outlaws._M/_tick, KMM_Stock.take, C._act raid_base) и читают их состояние.
-- Сценарии: probe (здоровье, первым), bar, rival, hunter, famine, raid. Деньги игроку - только в bar (до bar_money, лог).
-- Лог: C:/KenshiModMap/logs/scenario.log, строка на шаг: «ok|FAIL|skip <сценарий>.<шаг>: ...», «scenario <имя> start/done», «module <имя>: ...».
-- Каждый шаг под pcall: ошибка -> FAIL в лог, шаг пропущен, игра и остальные шаги не трогаются. Lua 5.1, всё - поля M.
local M = { off = false, name = nil, S = nil, run = nil, nlog = 0 }
M.P = {
  sdir = "C:/KenshiModMap/state/", file = "scenario.txt", log = "C:/KenshiModMap/logs/scenario.log", log_max = 600,
  start_s = 15,          -- секунд с первого такта до старта (мир и игрок загружаются)
  world_s = 5,           -- и ещё столько после появления состояния дирижёра (новая игра / загрузка)
  step_s = 2,            -- такт модуля
  per_tick = 2,          -- шагов за такт
  near = { 1800, 2600 }, -- запись соперника/банды ставится на таком расстоянии от игрока (спавн Traces - вне взгляда)
  rival_base = "Varn",   -- имя «побеждённого», из которого KMM_Nemesis делает соперника (как у сбежавшего врага)
  bar_money = 6000,      -- bar: довести деньги игрока до этой суммы (найм одного бар-рекрута), не больше
  bar_race_h = 6,        -- bar: гонка за рекрутом короче (игровых часов), чтобы увидеть исход за сессию
  bar_gate = 300,        -- bar: точка у ворот города (TownBase:getPositionOutsideTownGates)
  bar_towns = { "the hub", "squin", "stack", "admag", "shark", "mongrel", "world's end", "stoat", "heng", "sho-battai", "catun",
                "bark", "black scratch", "brink", "clownsteady", "spring", "bad teeth", "waystation", "blister hill", "flats lagoon" },
  probe_campaign = true, -- probe: одна родная кампания-рейд на город рядом с игроком через C.camp().try (проба triggerCampaign)
  camp_r = 15000,
}
M.MODS = { "KMM_Conductor", "KMM_Gov", "KMM_Native", "KMM_Traces", "KMM_Self", "KMM_Deeds", "KMM_Fates", "KMM_Outlaws", "KMM_Nemesis",
           "KMM_RecruitRace", "KMM_RelicRace", "KMM_Predators", "KMM_Herds", "KMM_Siege", "KMM_Veterans", "KMM_Stock", "KMM_Town",
           "KMM_Tempo", "KMM_Diplo", "KMM_Ore", "KMM_Rumors", "KMM_Elite" }

function M.log(msg)
  if M.nlog >= M.P.log_max then return end
  M.nlog = M.nlog + 1
  pcall(function()
    local fh = io.open(M.P.log, "a")
    if fh then fh:write(os.date("%Y-%m-%d %H:%M:%S"), " [KMM_Scenario] ", tostring(msg), "\n"); fh:close() end
  end)
end
function M.read_file()
  local ok, s = pcall(function()
    local fh = io.open(M.P.sdir .. M.P.file, "r")
    if not fh then return nil end
    local l = fh:read("*l"); fh:close()
    return l
  end)
  if not (ok and type(s) == "string") then return nil end
  s = s:lower():gsub("^%s+", ""):gsub("%s+$", "")
  if s == "" then return nil end
  if not M.SC[s] then M.log("unknown scenario '" .. s .. "' in state/scenario.txt: module idle"); return nil end
  return s
end

---------------------------------------------------------------------------------------------- помощники
function M.mod(n)
  local m = rawget(_G, n)
  if m == nil then local ok, v = pcall(function() return _G[n] end); if ok then m = v end end
  return m
end
function M.C() return M.mod("KMM_Conductor") end
function M.dist(ax, az, bx, bz) return math.sqrt((ax - bx) ^ 2 + (az - bz) ^ 2) end
function M.player()
  local ok, x, z, pc = pcall(function()
    for _, pc in pairs(getPlayerInterface():getAllPlayerCharacters()) do
      local p = pc:getPosition()
      if p then return p.x or p[1], p.z or p[3], pc end
    end
  end)
  if ok and type(x) == "number" and type(z) == "number" then return x, z, pc end
end
function M.hours()
  local ok, h = pcall(function() return getGameWorld():getTimeStamp_inGameHours():getTotalHours() end)
  return (ok and type(h) == "number") and h or nil
end
function M.town_name(pc)   -- имя города, где стоит персонаж, или nil
  local ok, n = pcall(function()
    local tw = pc:getCurrentTownLocation()
    if not tw then return nil end
    local okn, nm = pcall(function() return tw:getName() end)
    return (okn and type(nm) == "string" and nm ~= "") and nm or "a town"
  end)
  return ok and n or nil
end
function M.around(px, pz)
  local a = math.random() * 2 * math.pi
  local r = M.P.near[1] + math.random() * (M.P.near[2] - M.P.near[1])
  return px + r * math.cos(a), pz + r * math.sin(a)
end
function M.pref(name)
  local low = tostring(name or ""):lower()
  for _, w in ipairs(M.P.bar_towns) do if low:find(w, 1, true) then return true end end
  return false
end
function M.towns(C)
  local ok, l = pcall(C.towns)
  return (ok and type(l) == "table") and l or {}
end
function M.nearest_town(C, px, pz, ok_fn)
  local best, bd
  for _, t in ipairs(M.towns(C)) do
    if t.x and t.z and ok_fn(t) then
      local d = M.dist(px, pz, t.x, t.z)
      if not bd or d < bd then best, bd = t, d end
    end
  end
  return best, bd
end
function M.pf(C) local ok, pf = pcall(function() return C.cfg().player_faction end); return ok and pf or nil end
function M.nums(t)   -- ненулевые числа таблицы статистики: «a=1 b=2» (до 8)
  if type(t) ~= "table" then return "" end
  local ks = {}
  for k, v in pairs(t) do if type(v) == "number" and v ~= 0 then ks[#ks + 1] = tostring(k) end end
  table.sort(ks)
  local out = {}
  for i = 1, math.min(8, #ks) do out[#out + 1] = ks[i] .. "=" .. string.format("%.4g", t[ks[i]]) end
  return #out > 0 and (" [" .. table.concat(out, " ") .. "]") or ""
end
function M.flags(v, out, pre)
  if v == true then out[#out + 1] = pre
  elseif type(v) == "table" then
    for k, x in pairs(v) do if x then out[#out + 1] = (pre ~= "" and (pre .. ".") or "") .. tostring(k) end end
  end
end

---------------------------------------------------------------------------------------------- сводка модулей (stats/disabled)
M.EXTRA = {
  KMM_Conductor = function(m, off)
    local ok, R = pcall(m.coresync); if ok and type(R) == "table" and R.off then off[#off + 1] = "coresync" end
    local okc, CA = pcall(m.camp)
    if okc and type(CA) == "table" then
      if CA.OFF then off[#off + 1] = "campaign" end
      if CA.PROBE and CA.PROBE["triggerCampaign"] == false then off[#off + 1] = "triggerCampaign" end
    end
  end,
  KMM_Nemesis = function(m, off)
    for _, f in ipairs({ "hook_off", "town_talk_off", "ambient_off", "greet_off", "chronicle_off", "deeds_off", "appraise_off" }) do
      if type(m[f]) == "function" then
        local ok, v = pcall(m[f])
        if ok and (v == true or (type(v) == "table" and next(v) ~= nil)) then M.flags(v, off, f) end
      end
    end
  end,
  KMM_Outlaws = function(m, off) local X = rawget(m, "_M"); if type(X) == "table" and X.cap_off then off[#off + 1] = "captive_watch" end end,
  KMM_RecruitRace = function(m, off) local X = rawget(m, "X"); if type(X) == "table" then M.flags(X.off, off, "lever") end end,
  KMM_RelicRace = function(m, off) local L = type(m.rt) == "table" and m.rt.loot; if type(L) == "table" and L.off then off[#off + 1] = "ruinloot" end end,
}
function M.mod_line(n)
  local m = M.mod(n)
  if type(m) ~= "table" then return n .. ": absent (not loaded or not published to _G)" end
  local off = {}
  if rawget(m, "off") == true then off[#off + 1] = "off" end
  for _, f in ipairs({ "disabled", "_disabled", "DISABLED" }) do
    local v = rawget(m, f)
    if type(v) == "function" then
      local ok, r = pcall(v)
      if ok then M.flags(r, off, "") else off[#off + 1] = f .. "() error" end
    elseif v ~= nil then M.flags(v, off, "") end
  end
  if M.EXTRA[n] then pcall(M.EXTRA[n], m, off) end
  local st = rawget(m, "stats")
  if type(st) == "function" then local ok, r = pcall(st); st = ok and r or nil end
  table.sort(off)
  return string.format("%s: %s%s", n, #off == 0 and "alive" or ("OFF " .. table.concat(off, ",")), M.nums(st))
end
function M.s_summary(C, S, s)
  local alive, offn, absent = 0, 0, 0
  for _, n in ipairs(M.MODS) do
    local line = M.mod_line(n)
    M.log("module " .. line)
    if line:find(": absent", 1, true) then absent = absent + 1 elseif line:find(": OFF", 1, true) then offn = offn + 1 else alive = alive + 1 end
  end
  return offn == 0 and "ok" or "fail", string.format("%s: alive=%d with_off_flags=%d absent=%d (lines 'module ...' above)", s.k, alive, offn, absent)
end

---------------------------------------------------------------------------------------------- probe
function M.s_tgm(C, S, s)
  local T = M.mod("KMM_Traces")
  local G = type(T) == "table" and rawget(T, "tgm")
  if type(G) ~= "table" or type(G.probe) ~= "function" then return "skip", "KMM_Traces.tgm unavailable" end
  if G.done then return G.ok and "ok" or "fail", string.format("already probed this session: ok=%s tries=%s", tostring(G.ok), tostring(G.tries)) end
  local _, _, pc = M.player()
  if not pc then return "wait", "no player character" end
  local tn = M.town_name(pc)
  if not tn then return "wait", "player is not in a town: walk into any town with traders" end
  local okp, ap = pcall(function() return pc:getPlatoon() end)
  local okr, good, res = pcall(G.probe, okp and ap or nil, pc)
  if not okr then return "fail", "TGM probe error: " .. tostring(good) end
  return good and "ok" or "fail", string.format("TGM probe in %s: %s (debug.log TGM probe OK/FAIL)", tn, tostring(res))
end
function M.s_restock(C, S, s)
  local T = M.mod("KMM_Tempo")
  local RS = type(T) == "table" and rawget(T, "_restock")
  if type(RS) ~= "table" then return "skip", "KMM_Tempo._restock unavailable" end
  local D = rawget(T, "_disabled")
  local off = type(D) == "table" and (D.restock or D.all)
  local n = 0; for _ in pairs(type(RS.pl) == "table" and RS.pl or {}) do n = n + 1 end
  return off and "fail" or "ok", string.format("RESTOCK reads=%s armed=%s errs=%s tracked_platoons=%d disabled=%s (reads come by themselves near traders; tempo.log RESTOCK probe/armed)",
    tostring(RS.reads), tostring(RS.armed), tostring(RS.errs), n, tostring(off and true or false))
end
function M.s_coresync(C, S, s)
  if type(C.coresync) ~= "function" then return "skip", "C.coresync unavailable" end
  local ok0, R0 = pcall(C.coresync)
  local st0 = ok0 and type(R0) == "table" and R0.steps or nil
  if type(C.coresync_test) == "function" then pcall(C.coresync_test) end
  local ok1, R = pcall(C.coresync)
  if not (ok1 and type(R) == "table") then return "fail", "coresync state unreadable" end
  return R.off and "fail" or "ok", string.format("CORESYNC steps %s -> %s off=%s (marker CORESYNC steps= in debug.log at step 5)", tostring(st0), tostring(R.steps), tostring(R.off and true or false))
end
function M.s_campaign(C, S, s)
  local okc, CA = pcall(C.camp)
  if not (okc and type(CA) == "table" and CA.try and CA.pick and CA.limits_ok and CA.CP) then return "skip", "C.camp() unavailable" end
  if CA.OFF then return "fail", "native campaigns are off (CA.OFF)" end
  local PR = type(CA.PROBE) == "table" and CA.PROBE or {}
  if PR["triggerCampaign"] == false then return "fail", "triggerCampaign disabled (crash lock state/probe_triggerCampaign.off)" end
  if PR["triggerCampaign#done"] then return "ok", "triggerCampaign already called this session (debug.log campaign: triggerCampaign ok/FAIL)" end
  if not M.P.probe_campaign then return "skip", "probe_campaign = false" end
  local px, pz = M.player()
  if not px then return "wait", "no player" end
  local pf = M.pf(C)
  local t, d = M.nearest_town(C, px, pz, function(x) return x.owner and x.owner ~= pf end)
  if not (t and d <= M.P.camp_r) then return "wait", "no owned town within 15 km of the player" end
  local okd, D = pcall(CA.data)
  if not (okd and type(D) == "table" and type(D.factions) == "table") then return "skip", "no FACTION_CAMPAIGN data" end
  local fid, rel
  for f, F in pairs(S.F or {}) do
    if type(F) == "table" and F.alive and not F.player and not F.relic and f ~= t.owner and f ~= pf and D.factions[f] then
      local okr, r = pcall(C.rel, f, t.owner)
      if okr and type(r) == "number" and r < 0 and (not rel or r < rel) and CA.pick(f, { "raid" }, (CA.CP().max_forces or 30)) and CA.limits_ok(f) then fid, rel = f, r end
    end
  end
  if not fid then return "skip", "no hostile faction with a raid campaign against " .. tostring(t.name) end
  -- путь дирижёра CA.try (лимиты, договоры, выбор кампании, подкрепления, хроника); только его бросок p_raid снят на этот вызов
  local G = CA.CP()
  local p0 = G.p_raid
  G.p_raid = 1
  local okt, res = pcall(CA.try, fid, t.owner, "raid", t.sid)
  G.p_raid = p0
  if not okt then return "fail", "CA.try error: " .. tostring(res) end
  local called = PR["triggerCampaign#done"] and true or false
  return res and "ok" or "fail", string.format("raid campaign %s -> %s (%s, rel %d, %.1f km): launched=%s called=%s (debug.log campaign: triggerCampaign ok/FAIL)",
    tostring(fid), tostring(t.owner), tostring(t.name), rel, d / 1000, tostring(res and true or false), tostring(called))
end
-- гонка за рекрутом путём KMM_RecruitRace (pick/start); mode "probe": срок сейчас (следующий такт модуля переносит рекрута - проба setFaction),
-- "bar": срок bar_race_h игровых часов (успеть нанять или увидеть recruit taken)
function M.recruit(C, mode)
  local RR = M.mod("KMM_RecruitRace")
  if type(RR) ~= "table" or type(RR.st) ~= "function" or type(RR.pick) ~= "function" or type(RR.start) ~= "function" then return "skip", "KMM_RecruitRace unavailable" end
  if RR.off then return "fail", "KMM_RecruitRace is off (recruitrace.log: disabled)" end
  local R = RR.st(C)
  if not R then return "wait", "recruit race state not ready" end
  if R.pend then return "ok", "transfer already pending: " .. tostring(R.pend.name) end
  local h = M.hours()
  if not h then return "wait", "no game hours" end
  if not R.race then
    local px, pz, pc = M.player()
    local tn = pc and M.town_name(pc)
    if not tn then return "wait", "player is not in a town with a bar" end
    local G = M.mod("KMM_Gov")
    local oks, snap = pcall(function() return G.snapshot(2.0) end)
    if not (oks and type(snap) == "table") then return "wait", "no KMM_Gov snapshot" end
    local rec, sk = RR.pick(snap, px, pz, M.pf(C))
    if not rec then return "wait", "no hireable bar recruit near the player in " .. tn end
    RR.start(C, R, rec, sk, h, snap, px, pz)
    if not R.race then return "wait", "race not started (no rival faction or platoon key)" end
  end
  local t1 = (mode == "probe") and h or (h + M.P.bar_race_h)
  if (R.race.t1 or 0) > t1 then R.race.t1 = t1 end
  return "ok", string.format("race for %s in %s, rival %s, taken in %.1f game h unless hired (recruitrace.log: race start / recruit cancel by player / setFaction ok)",
    tostring(R.race.name), tostring(R.race.town), tostring(R.race.fid), R.race.t1 - h)
end
function M.s_recruit_probe(C) return M.recruit(C, "probe") end
function M.s_prosperity(C)
  local ok, R = pcall(C.coresync)
  local ys = ok and type(R) == "table" and R.ys
  if type(ys) ~= "table" then return "skip", "no Y2 state" end
  return "ok", string.format("PROSPERITY read only (calls follow a confirmed squad loss): probed=%s calls=%s measured=%s eff=%s off=%s",
    tostring(ys.probed or false), tostring(ys.calls), tostring(ys.mcalls), tostring(ys.eff), tostring(ys.off or false))
end
function M.s_ruinloot()
  local RL = M.mod("KMM_RelicRace")
  local L = type(RL) == "table" and type(RL.rt) == "table" and RL.rt.loot
  if type(L) ~= "table" then return "skip", "KMM_RelicRace.rt.loot unavailable" end
  local pr = {}
  for k, v in pairs(type(L.probe) == "table" and L.probe or {}) do pr[#pr + 1] = tostring(k) .. "=" .. tostring(v) end
  table.sort(pr)
  return (RL.off or L.off) and "fail" or "ok", string.format("ruinloot read only: moved_this_session=%s off=%s module_off=%s probes={%s}",
    tostring(L.n), tostring(L.off or false), tostring(RL.off or false), table.concat(pr, " "))
end

---------------------------------------------------------------------------------------------- bar
function M.s_money(C)
  local _, _, pc = M.player()
  if not pc then return "wait", "no player" end
  local own = pc:getOwnerships()
  local m0 = own:getMoney()
  if type(m0) ~= "number" then return "fail", "getMoney returned " .. tostring(m0) end
  local need = math.floor(M.P.bar_money - m0)
  if need <= 0 then return "ok", string.format("player has %d cats: nothing added", m0) end
  own:addMoney(need)
  local m1 = own:getMoney()
  return (m1 == m0 + need) and "ok" or "fail", string.format("money %d -> %s (+%d, bar scenario only: enough to hire one bar recruit)", m0, tostring(m1), need)
end
function M.s_teleport(C, S, s)
  local px, pz, pc = M.player()
  if not pc then return "wait", "no player" end
  local here = M.town_name(pc)
  if here and M.pref(here) then return "ok", "already in " .. here .. ": no teleport" end
  local pf = M.pf(C)
  local t, d = M.nearest_town(C, px, pz, function(x) return x.kind == "city" and x.owner and x.owner ~= pf and M.pref(x.name) end)
  if not t then t, d = M.nearest_town(C, px, pz, function(x) return x.kind == "city" and x.owner and x.owner ~= pf end) end
  if not t then return "fail", "no town in conductor towns" end
  local dir = string.format("%s is %.1f km away (dx %+.1f km, dz %+.1f km)", tostring(t.name), d / 1000, (t.x - px) / 1000, (t.z - pz) / 1000)
  local fo = getGameWorld().factionMgr:getFactionByStringID(t.owner)
  local tw = fo and fo.warMgr and fo.warMgr:getNearestTown({ x = t.x, y = 0, z = t.z })
  if not tw then return "fail", "no TownBase from the owner's war manager; walk there yourself: " .. dir end
  local okg, pos = pcall(function() return tw:getPositionOutsideTownGates(M.P.bar_gate) end)
  if not (okg and pos and pos.x) then pos = tw:getPosition() end
  if not (pos and pos.x and M.dist(pos.x, pos.z, t.x, t.z) <= 5000) then return "fail", "town position not found; walk there yourself: " .. dir end
  local ap = pc:getPlatoon()
  ap:teleport(pos)
  M.run.ctx.tp = { x = pos.x, z = pos.z, name = t.name, dir = dir }
  return "ok", string.format("ActivePlatoon teleport called (? not yet seen in game) to the gates of %s (%.0f %.0f): %s", tostring(t.name), pos.x, pos.z, dir)
end
function M.s_arrive(C, S, s)
  local tp = M.run.ctx.tp
  if not tp then return "skip", "no teleport this run" end
  local px, pz = M.player()
  if not px then return "wait", "no player" end
  local d = M.dist(px, pz, tp.x, tp.z)
  if d <= 3000 then return "ok", string.format("teleport confirmed: player %.0f m from the gates of %s; go into the bar", d, tostring(tp.name)) end
  return "wait", string.format("player %.0f m from the target: %s", d, tp.dir)
end
function M.s_recruit_bar(C) return M.recruit(C, "bar") end

---------------------------------------------------------------------------------------------- rival / hunter (KMM_Nemesis + KMM_Outlaws)
function M.ol()   -- M(_M Outlaws), O, D через тот же путь, что у KMM_Nemesis (N.outlaws)
  local NM = M.mod("KMM_Nemesis")
  local N = type(NM) == "table" and rawget(NM, "_N")
  if type(N) == "table" and type(N.outlaws) == "function" then
    local X, O, D = N.outlaws()
    if X then return X, O, D, N end
  end
  local OL = M.mod("KMM_Outlaws")
  local X = type(OL) == "table" and rawget(OL, "_M")
  local C = M.C()
  if not (type(X) == "table" and C and C.state) then return nil end
  local S = C.state()
  if type(S) ~= "table" then return nil end
  local D = X.data(C)
  if not D then return nil end
  return X, X.O(S), D, N
end
function M.ol_off()
  local OL = M.mod("KMM_Outlaws")
  if type(OL) ~= "table" or type(OL._tick) ~= "function" then return "KMM_Outlaws unavailable" end
  local ok, d = pcall(OL.disabled)
  if ok and type(d) == "table" and next(d) ~= nil then return "KMM_Outlaws is off (outlaws.log)" end
  return nil
end
function M.place(o)
  local px, pz = M.player()
  if not px then return nil end
  o.x, o.z = M.around(px, pz)
  o.sp = -1000
  return M.dist(px, pz, o.x, o.z)
end
function M.s_rival(C, S, s)
  local why = M.ol_off(); if why then return "skip", why end
  local X, O, D, N = M.ol()
  if not X then return "skip", "outlaws data unavailable" end
  local o, how
  for _, r in ipairs(X.list(O)) do if r.st == "a" and r.pg and not r.pk then o, how = r, "existing rival"; break end end
  if not o then
    if not (N and type(N.make) == "function") then return "skip", "KMM_Nemesis._N.make unavailable" end
    local px, pz = M.player()
    if not px then return "wait", "no player" end
    local x, z = M.around(px, pz)
    o = N.make(X, O, D, C, S, { n = M.P.rival_base, x = x, z = z, lead = true }, "fled")
    if not o then return "fail", "KMM_Nemesis did not make a rival (cap, cooldown or no region near the player)" end
    how = "new rival via KMM_Nemesis (deed fled)"
  end
  local d = M.place(o)
  M.run.ctx.rival = o.i
  return "ok", string.format("%s %s (T%s, gang %s) placed %.0f m from the player: KMM_Outlaws spawns it via Traces.request", how, tostring(o.n), tostring(o.t), tostring(o.g), d or -1)
end
function M.s_outlaw(key)   -- разыскиваемый (не соперник) с наибольшей наградой - к игроку
  return function(C, S, s)
    local why = M.ol_off(); if why then return "skip", why end
    local X, O = M.ol()
    if not X then return "skip", "outlaws data unavailable" end
    local o
    for _, r in ipairs(X.list(O)) do
      if r.st == "a" and not r.pg and not r.pk and r.i ~= M.run.ctx.rival and (not o or (r.b or 0) > (o.b or 0)) then o = r end
    end
    if not o then return "wait", "no free wanted outlaw record" end
    local d = M.place(o)
    M.run.ctx[key] = o.i
    return "ok", string.format("wanted %s (T%s, bounty %s, gang %s) placed %.0f m from the player", tostring(o.n), tostring(o.t), tostring(o.b), tostring(o.g), d or -1)
  end
end
function M.s_spawn(key)   -- ждать спавна записи: ход видимости KMM_Outlaws сейчас (его vis -> Traces.request), запись держится у игрока
  return function(C, S, s)
    local oi = M.run.ctx[key]
    if not oi then return "skip", "no record placed" end
    local OL = M.mod("KMM_Outlaws")
    local X, O = M.ol()
    if not X then return "fail", "outlaws data gone" end
    local o = O.L["o" .. tostring(oi)]
    if not (o and o.st == "a") then return "fail", "record is gone (dead or jailed)" end
    local okl, live = pcall(OL.live)
    if okl and type(live) == "table" and live["o" .. tostring(oi)] then
      return "ok", string.format("%s spawned near the player (outlaws.log gang of ... spawned; diplo DUEL offer added%s)", tostring(o.n), o.pg and "; nemesis.log appraise: app=" or "")
    end
    if o.pk then return "ok", tostring(o.n) .. " is already a persistent squad: the engine walks it to the player" end
    local px, pz = M.player()
    if px and (not o.x or M.dist(px, pz, o.x, o.z) > 4000) then M.place(o) end
    if X.pend == nil then o.sp = -1000 end   -- заявка отклонена (буря, лимит): кулдаун записи не держит повтор
    pcall(OL._tick)
    return "wait", "waiting for KMM_Traces to spawn " .. tostring(o.n) .. " out of sight"
  end
end
function M.s_manhunt(C, S, s)
  local why = M.ol_off(); if why then return "skip", why end
  local X, O, D = M.ol()
  if not X then return "skip", "outlaws data unavailable" end
  local oi = M.run.ctx.hunted
  local o = oi and O.L["o" .. tostring(oi)]
  if not (o and o.st == "a") then return "fail", "no hunted outlaw" end
  local OL = M.mod("KMM_Outlaws")
  local okl, live = pcall(OL.live)
  if not (o.pk or (okl and type(live) == "table" and live["o" .. tostring(oi)])) then return "wait", "gang of " .. tostring(o.n) .. " not spawned yet" end
  local px, pz = M.player()
  if not px then return "wait", "no player" end
  local t, bd
  for _, r in pairs(D.regions or {}) do
    for _, tw in ipairs(r.towns or {}) do
      if tw.fid and tw.x then local d = M.dist(px, pz, tw.x, tw.z); if not bd or d < bd then t, bd = tw, d end end
    end
  end
  if not t then return "fail", "no lawful town in outlaws.json" end
  if not O.hunt[t.sid] then X.manhunt(C, O, D, X.cfg(), t, o, X.today(C)) end
  local h = O.hunt[t.sid]
  if not h then return "fail", "manhunt not created" end
  h.oi, h.sp = o.i, nil
  local vr = (X.cfg().vis_r or 22000) * 0.8
  if bd > vr then h.x, h.z = M.around(px, pz) end   -- патруль выходит рядом с игроком, а не из далёкого города
  M.run.ctx.hunt, M.run.ctx.patrol0 = t.sid, (X.stats and X.stats.patrol) or 0
  return "ok", string.format("manhunt of %s from %s (%.1f km, law %s) against %s", tostring(t.name), tostring(t.name), bd / 1000, tostring(h.lf), tostring(o.n))
end
function M.s_patrol(C, S, s)
  local X, O = M.ol()
  local k = M.run.ctx.hunt
  local h = X and k and O.hunt[k]
  if not h then return "fail", "manhunt record is gone" end
  local n = (X.stats and X.stats.patrol) or 0
  if h.sp and n > (M.run.ctx.patrol0 or 0) then return "ok", "manhunt patrol requested (outlaws.log manhunt patrol from / hunt goal HUNT_BOUNTIES; later captive * if they carry him)" end
  if h.sp then h.sp = nil end   -- заявка отклонена: снова в очередь
  pcall(M.mod("KMM_Outlaws")._tick)
  return "wait", "waiting for the manhunt patrol request"
end

---------------------------------------------------------------------------------------------- famine / raid
function M.s_famine(C, S, s)
  local K = M.mod("KMM_Stock")
  if type(K) ~= "table" or type(K.take) ~= "function" then return "skip", "KMM_Stock unavailable" end
  local okr, ready = pcall(K.ready)
  if not (okr and ready) then return "wait", "KMM_Stock not ready" end
  local px, pz, pc = M.player()
  if not px then return "wait", "no player" end
  local sid, how = M.run.ctx.fsid, M.run.ctx.fhow
  if not sid then
    local okt, ts = pcall(K.town_of, pc)
    if okt and ts then sid, how = ts, "player's town"
    else
      local t, d = M.nearest_town(C, px, pz, function(x) local ok, st = pcall(K.stock, x.sid); return x.kind == "city" and ok and st ~= nil end)
      if not t then return "wait", "no town with a KMM_Stock shelf" end
      sid, how = t.sid, string.format("nearest town %s, %.1f km", tostring(t.name), d / 1000)
    end
    M.run.ctx.fsid, M.run.ctx.fhow = sid, how
  end
  local st = K.stock(sid)
  if not (st and st.q) then return "wait", "no shelf for " .. tostring(sid) end
  local q = st.q.food or 0
  local lv0 = K.level(sid, "food")
  local took = (q > 0) and K.take(sid, "food", q) or 0
  local lv1 = K.level(sid, "food")
  return "ok", string.format("food shelf of %s (%s): %.1f units taken, level %s -> %s (stock.log U3 starve; prices: debug.log TGM town; rollback by KMM_Town when the shelf refills)",
    tostring(sid), tostring(how), took, tostring(lv0), tostring(lv1))
end
function M.s_raid(C, S, s)
  local B = S.base
  if not (type(B) == "table" and B.known and B.x) then return "wait", "no base (нет базы): own a building and stand by it" end
  local pf = M.pf(C)
  local okc, CA = pcall(C.camp)
  local okd, D = false, nil
  if okc and type(CA) == "table" and CA.data then okd, D = pcall(CA.data) end
  local camp = okd and type(D) == "table" and type(D.factions) == "table" and D.factions or {}
  local best, bs, brel, bdist
  for f, F in pairs(S.F or {}) do
    if type(F) == "table" and F.alive and not F.player and not F.relic and f ~= pf then
      local okp, fx, fz = pcall(C.fpos, f)
      if okp and fx then
        local okr, r = pcall(C.rel, f, pf)
        r = (okr and type(r) == "number") and r or 0
        local d = M.dist(fx, fz, B.x, B.z)
        local sc = (camp[f] and 1000 or 0) - r - d / 1000
        if not bs or sc > bs then best, bs, brel, bdist = f, sc, r, d end
      end
    end
  end
  if not best then return "fail", "no faction to raid the base" end
  C._act(best, "raid_base", "greed")
  local nat = type(S.bcamp) == "table" and S.bcamp.fid == best
  return "ok", string.format("raid_base by %s (rel %d, %.1f km from the base): %s", tostring(best), brel, bdist / 1000,
    nat and "native campaign fired (debug.log campaign: base bound / base outcome)" or "no native campaign -> Traces base_raid (debug.log -> Traces raid)")
end

---------------------------------------------------------------------------------------------- сценарии
M.SC = {
  probe = function() return {
    { k = "modules", at = 0, fn = M.s_summary },
    { k = "coresync", at = 2, fn = M.s_coresync },
    { k = "restock", at = 2, fn = M.s_restock },
    { k = "prosperity", at = 4, fn = M.s_prosperity },
    { k = "ruinloot", at = 4, fn = M.s_ruinloot },
    { k = "tgm", at = 6, max = 1200, every = 10, fn = M.s_tgm },
    { k = "recruit", at = 8, max = 1200, every = 10, fn = M.s_recruit_probe },
    { k = "campaign", at = 10, max = 600, every = 15, fn = M.s_campaign },
    { k = "restock_later", at = 240, fn = M.s_restock },
    { k = "modules_later", at = 300, fn = M.s_summary },
  } end,
  bar = function() return {
    { k = "money", at = 0, fn = M.s_money },
    { k = "teleport", at = 1, fn = M.s_teleport },
    { k = "arrive", at = 12, max = 300, every = 10, fn = M.s_arrive },
    { k = "race", at = 20, max = 1200, every = 10, fn = M.s_recruit_bar },
  } end,
  rival = function() return {
    { k = "rival", at = 0, max = 120, every = 10, fn = M.s_rival },
    { k = "rival_spawn", at = 2, max = 600, every = 10, fn = M.s_spawn("rival") },
    { k = "outlaw", at = 150, max = 300, every = 10, fn = M.s_outlaw("gang") },
    { k = "outlaw_spawn", at = 152, max = 600, every = 10, fn = M.s_spawn("gang") },
  } end,
  hunter = function() return {
    { k = "wanted", at = 0, max = 300, every = 10, fn = M.s_outlaw("hunted") },
    { k = "wanted_spawn", at = 2, max = 600, every = 10, fn = M.s_spawn("hunted") },
    { k = "manhunt", at = 4, max = 900, every = 10, fn = M.s_manhunt },
    { k = "patrol", at = 6, max = 900, every = 10, fn = M.s_patrol },
  } end,
  famine = function() return {
    { k = "shelf", at = 0, max = 600, every = 10, fn = M.s_famine },
    { k = "shelf_again", at = 300, max = 600, every = 10, fn = M.s_famine },
  } end,
  raid = function() return {
    { k = "raid", at = 0, max = 1800, every = 15, fn = M.s_raid },
  } end,
}

---------------------------------------------------------------------------------------------- такт
function M.begin(C, S, now)
  if now - (M.wait0 or now) < M.P.world_s then return end
  if not M.player() then return end
  S.ext = S.ext or {}
  local X = S.ext.scenario
  if type(X) ~= "table" then X = {}; S.ext.scenario = X end
  X.done = type(X.done) == "table" and X.done or {}
  if X.done[M.name] then
    M.run = { done = true }
    M.log(string.format("scenario %s already ran in this world (game hour %s): skipped", M.name, tostring(X.done[M.name])))
    return
  end
  X.done[M.name] = M.hours() or 0
  X.last = M.name
  local okb, steps = pcall(M.SC[M.name])
  if not (okb and type(steps) == "table") then M.run = { done = true }; M.log("scenario " .. M.name .. " build error: " .. tostring(steps)); return end
  M.run = { t0 = now, steps = steps, ctx = {}, n = { ok = 0, fail = 0, skip = 0 } }
  M.log(string.format("scenario %s start: %d steps (game hour %.1f)", M.name, #steps, X.done[M.name]))
end
function M.res(s, st, msg)
  M.run.n[st] = (M.run.n[st] or 0) + 1
  M.log(string.format("%s %s.%s: %s", st == "fail" and "FAIL" or st, M.name, s.k, tostring(msg)))
end
function M.advance(C, S, now)
  local R = M.run
  local el = now - R.t0
  local n, left = 0, 0
  for _, s in ipairs(R.steps) do
    if not s.st then
      left = left + 1
      if el >= (s.at or 0) and now - (s.tl or -1e9) >= (s.every or 0) and n < M.P.per_tick then
        n = n + 1
        s.tl, s.tries = now, (s.tries or 0) + 1
        local ok, st, msg = pcall(s.fn, C, S, s)
        if not ok then s.st = "fail"; M.res(s, "fail", "error: " .. tostring(st))
        elseif st == "wait" then
          if s.tries == 1 then M.log(string.format("wait %s.%s: %s", M.name, s.k, tostring(msg))) end
          if el - (s.at or 0) >= (s.max or 0) then s.st = "fail"; M.res(s, "fail", "timeout after " .. s.tries .. " tries: " .. tostring(msg)) end
        else
          s.st = (st == "fail" or st == "skip") and st or "ok"
          M.res(s, s.st, msg)
        end
        if s.st then left = left - 1 end
      end
    end
  end
  if left == 0 then
    R.done = true
    M.log(string.format("scenario %s done: ok=%d fail=%d skip=%d", M.name, R.n.ok or 0, R.n.fail or 0, R.n.skip or 0))
  end
end
-- HEALTH: ошибка такта -> пауза реестра KMM_Gov (ключ KMM_Scenario.module) и повтор; без Gov - до перезапуска. M.off без ключа паузы
-- (нет файла сценария: инертен) остаётся навсегда.
local function h_gov() local g = rawget(_G, "KMM_Gov"); if type(g) == "table" and type(g.h_fail) == "function" then return g end end
local HKEY = "KMM_Scenario.module"
local function h_live()
  if not M.off then return false end
  if M.hpause then
    local g = h_gov()
    local ok, up = pcall(g and g.h_up or function() return true end, HKEY)
    if (not ok) or up ~= false then M.off, M.hpause, M.hretry = false, nil, true; return false end
  end
  return true
end
function M.tick()
  if h_live() then return end
  local now = os.clock()
  M.t0 = M.t0 or now
  if now - (M.last or -1e9) < M.P.step_s then return end
  M.last = now
  if M.name == nil then
    M.name = M.read_file() or false
    if not M.name then M.off = true; return end   -- нет файла: инертен до конца сессии
    M.log("scenario file: " .. M.name)
  end
  if now - M.t0 < M.P.start_s then return end
  local C = M.C()
  if not (type(C) == "table" and C.state) then return end
  local okS, S = pcall(C.state)
  if not (okS and type(S) == "table") then return end
  if M.S ~= S then   -- новая игра / загрузка: рантайм прошлого мира не трогать
    if M.S ~= nil then M.log("world changed: scenario runtime reset") end
    M.S, M.run, M.wait0 = S, nil, now
  end
  if not M.run then return M.begin(C, S, now) end
  if M.run.done then return end
  M.advance(C, S, now)
end
local function guarded(fn)   -- ошибка такта выключает только этот модуль
  return function(...)
    local ok, err = pcall(fn, ...)
    if not ok then
      M.off, M.hpause, M.hretry = true, nil, nil
      local g, p = h_gov(), nil
      if g then local okf, r = pcall(g.h_fail, HKEY, err); if okf and type(r) == "number" then p = r end end
      M.hpause = p and true or nil
      M.log(p and ("failed, retry in " .. p .. " s: " .. tostring(err)) or ("disabled until restart: " .. tostring(err)))
    elseif M.hretry then
      M.hretry = nil
      local g = h_gov(); if g then pcall(g.h_ok, HKEY) end
    end
  end
end
function M.stats() return { n = M.nlog, name = M.name or nil } end
function M.disabled() return M.off and M.name and { scenario = true } or {} end
function M._reset() M.off, M.name, M.S, M.run, M.nlog, M.t0, M.last, M.wait0 = false, nil, nil, nil, 0, nil, nil, nil end

if Events and Events.on then pcall(function() Events.on("GameWorld::charsUpdate", guarded(M.tick)) end) end
KMM_Scenario = M
rawset(_G, "KMM_Scenario", M)
