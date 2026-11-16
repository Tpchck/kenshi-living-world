-- KMM_Conductor_Sync: part of KMM_Conductor (world conductor), run by KC._BOOT in KMM_Conductor.lua
-- Часть дирижёра мира (KMM_Conductor.lua собирает части и регистрирует события). 1-я строка ASCII: имя чанка в тестах.
-- Здесь: связь с ядром: материализация в игре, кампании ванильного ИИ (L2.camp), RELSYNC (GL.rs_*), CORESYNC (GL.cs_*),
-- запись отношений, смерть/плен лидеров вне видимости, союзные отряды, scan_loaded.
-- Код части выполняется не при загрузке файла, а в KC._BOOT() в порядке KC._PARTS (как шёл бы единый файл),
-- когда загружены все части — порядок загрузки файлов KenshiLua не важен.
local KC = rawget(_G, "KMM_C_INT")   -- общее пространство имён частей дирижёра (бывшие локали главного чанка: KC.<имя>)
if type(KC) ~= "table" then KC = { _SEG = {} }; _G.KMM_C_INT = KC end
if KC._booted then KC._SEG, KC._booted = {}, false end   -- повторная загрузка скриптов: собрать части заново
KC._SEG.Sync = function()
---------------------------------------------------------------------------------------------- материализация в игре
function KC.faction_obj(fid)
  local ok, f = pcall(function() return getGameWorld().factionMgr:getFactionByStringID(fid) end)
  return ok and f or nil
end
-- LINKS2: металлический голод -> видимая кампания FactionWarMgr:triggerCampaign (есть в BindingsReference KenshiLua). Только если включена флагом
-- params.links2.ore_campaign.enabled и задана кампания (FACTION_CAMPAIGN), цель - рудный узел дирижёра, рядом с ним есть персонаж игрока
-- (зона загружена) и обе фракции есть в игре; <= 1 кампании на фракцию за cooldown_days; вне договоров. Иначе остаётся абстрактная хроника.
KC.ore_campaign_try = function(fid, o, town)
  local G = KC.L2.P().ore_campaign or {}
  if not (G.enabled and G.campaign) then return false end
  local f = KC.S.F[fid]
  if not f or KC.DAY - (f.camp_day or -1000) < (G.cooldown_days or 60) then return false end
  if not (KC.S.ore and KC.S.ore[town]) or KC.treaty_between(fid, o) then return false end
  local I = KC.CFG.town_info[town]
  if not (I and I.x) then return false end
  local near = false
  local okc, pcs = pcall(function() return getPlayerInterface():getAllPlayerCharacters() end)
  for _, c in pairs(okc and pcs or {}) do
    local okp, px, pz = pcall(function() local p = c:getPosition(); return p.x or p[1], p.z or p[3] end)
    if okp and px and pz and math.sqrt((px - I.x) ^ 2 + (pz - I.z) ^ 2) <= (G.load_radius or 15000) then near = true; break end
  end
  if not near then return false end
  local gw = getGameWorld()
  local fo, oo = gw.factionMgr:getFactionByStringID(fid), gw.factionMgr:getFactionByStringID(o)
  if not (fo and fo.warMgr and oo and oo.warMgr) then return false end
  local pos = { x = I.x, y = 0, z = I.z }
  local target, home = oo.warMgr:getNearestTown(pos), fo.warMgr:getNearestTown(pos)
  local gd = gw.gamedata:getData(G.campaign, G.campaign_type or 93)
  if not (target and home and gd) then return false end
  if not KC.L2.camp.probe_call("triggerCampaign", function() fo.warMgr:triggerCampaign(target, gd, G.min_time or 0, G.max_time or 0, home, false, fo) end,
    "ore " .. tostring(fid) .. "->" .. tostring(o) .. " " .. tostring(G.campaign) .. " at " .. tostring(town)) then return false end
  f.camp_day = KC.DAY
  KC.S.stats.ore_campaigns = (KC.S.stats.ore_campaigns or 0) + 1
  KC.emit({ type = "ore_campaign", a = fid, b = o, town_sid = town, town_name = KC.TOWN_NAME[town] or town,
         text = string.format("%s marched on the mines of %s: iron is worth the blood.", KC.name(fid), KC.TOWN_NAME[town] or town) })
  return true
end
-- NATIVE_MAP п.2/п.5: родные кампании движка (FACTION_CAMPAIGN) по решению дирижёра и родные флаги RelationData. Всё полями L2.camp (лимит 200 локалей).
-- Данные: campaigns.json (tools/conductor/gen_campaigns.py): у фракции-владельца списки assault/raid/reinforce. Нативные вызовы под крэш-сторожем:
-- до первого вызова сессии пишется state/probe_<имя>.lock, после успеха удаляется; lock при старте = крэш -> state/probe_<имя>.off, метод выключен навсегда.
-- Событие, для которого запущена родная кампания, получает native=true (колонну Traces для него ставить не нужно).
do
local CA = {}
KC.L2.camp = CA
CA.PROBE = {}
function CA.CP() return KC.P.campaign or {} end
function CA.off_now() return KC.GL.h_live(CA, "OFF") end   -- HEALTH: пауза реестра истекла -> снова в работе
function CA.log(msg) pcall(function() _G.KMM_Conductor.guard_log("campaign: " .. tostring(msg)) end) end
function CA.probe_ok(x)
  local st = CA.PROBE[x]
  if st == nil then
    local sd = CA.CP().sdir or "C:/KenshiModMap/state/"
    local lock, offp = sd .. "probe_" .. x .. ".lock", sd .. "probe_" .. x .. ".off"
    st = true
    pcall(function()
      local f = io.open(offp, "r")
      if f then f:close(); st = false; return end
      f = io.open(lock, "r")
      if f then
        f:close(); st = false
        local o = io.open(offp, "w"); if o then o:write("disabled: previous session crashed in ", x, "\n"); o:close() end
        os.remove(lock)
        CA.log("native method " .. x .. " DISABLED forever: previous session crashed during the call (state/probe_" .. x .. ".off)")
      end
    end)
    CA.PROBE[x] = st
  end
  return st
end
function CA.probe_call(x, fn, ctx)   -- ctx: строка -> одна строка лога «campaign: <x> ok|FAIL <ctx>» (B8, маркер session_report)
  if not CA.probe_ok(x) then return false end
  local lock = (CA.CP().sdir or "C:/KenshiModMap/state/") .. "probe_" .. x .. ".lock"
  local first = not CA.PROBE[x .. "#done"]
  if first then pcall(function() local f = io.open(lock, "w"); if f then f:write(tostring(os.time())); f:close() end end) end
  local ok, er = pcall(fn)
  if first then
    pcall(os.remove, lock); CA.PROBE[x .. "#done"] = true   -- Lua-ошибка не крэш: lock снимаем (нативный крэш lock оставит)
    if not ok then CA.log(x .. " first call failed (lua error): " .. tostring(er)) end
  end
  if ctx then CA.log(x .. (ok and " ok " or " FAIL ") .. tostring(ctx) .. (ok and "" or (": " .. tostring(er)))) end
  return ok, er
end
function CA.data()
  if CA.D == nil then
    local ok, d = pcall(KC.load_json, "campaigns.json", "C:/KenshiModMap/build/KMM_Conductor/campaigns.json")
    CA.D = (ok and type(d) == "table" and type(d.factions) == "table" and type(d.campaigns) == "table") and d or false
    if not CA.D then CA.log("campaigns.json missing/invalid - native campaigns idle") end
  end
  return CA.D
end
function CA.pick(fid, kinds, maxf)   -- sid кампании фракции нужного вида (без world state, не больше maxf бойцов)
  local D = CA.data()
  local e = D and D.factions[fid]
  if not e then return nil end
  for _, k in ipairs(kinds) do
    local l = {}
    for _, sid in ipairs(e[k] or {}) do
      local c = D.campaigns[sid]
      if c and (c.forces or 0) <= maxf and (c.ws or 0) == 0 then l[#l + 1] = sid end
    end
    if #l > 0 then return l[math.random(#l)], k end
  end
end
function CA.near_player(x, z, r)
  local ok, pcs = pcall(function() return getPlayerInterface():getAllPlayerCharacters() end)
  local best
  for _, c in pairs(ok and pcs or {}) do
    local okp, px, pz = pcall(function() local p = c:getPosition(); return p.x or p[1], p.z or p[3] end)
    if okp and px and pz then
      local d = math.sqrt((px - x) ^ 2 + (pz - z) ^ 2)
      if d <= r and (not best or d < best) then best = d end
    end
  end
  return best
end
function CA.limits_ok(fid)
  local G = CA.CP()
  local N = KC.S.ncamp
  if not N then return true end
  if KC.DAY - (N.f[fid] or -1e9) < (G.fac_cooldown or 30) then return false end
  local n = 0
  for _, d in ipairs(N.d) do if KC.DAY - d < (G.world_days or 10) then n = n + 1 end end
  return n < (G.world_max or 3)
end
function CA.note(fid)
  KC.S.ncamp = KC.S.ncamp or { f = {}, d = {} }
  local N = KC.S.ncamp
  N.f[fid] = KC.DAY
  N.d[#N.d + 1] = KC.DAY
  while #N.d > 12 do table.remove(N.d, 1) end
end
-- запуск одной родной кампании фракции fid на город target (объект движка), дом home; false при любом сбое
function CA.fire(fid, sid, target, home, tag)   -- tag: подпись в маркере «campaign: triggerCampaign ok|FAIL <tag> fid sid» (по умолчанию native)
  local gw = getGameWorld()
  local fo = gw.factionMgr:getFactionByStringID(fid)
  local D = CA.data()
  if not (fo and fo.warMgr and target and sid) then return false end
  local gd = gw.gamedata:getData(sid, (D and D.gd_type) or 93)
  if not gd then return false end
  local G = CA.CP()
  return CA.probe_call("triggerCampaign", function() fo.warMgr:triggerCampaign(target, gd, G.min_time or 0, G.max_time or 0, home or target, false, fo) end,
    (tag or "native") .. " " .. tostring(fid) .. " " .. tostring(sid))
end
-- U2: фазы CampaignInstance::currentPhase (Campaign.h, enum Phase; как в KMM_Siege.PH) и чтение FactionWarMgr.activeCampaigns
CA.PH = { GATHERING = 0, ASSAULTING = 1, RETREATING = 2, VICTORY = 3, ASSAULT_2_HAPPY = 4, ASSAULT_2_ANGRY = 5 }
CA.PHN = {}; for k, v in pairs(CA.PH) do CA.PHN[v] = k end
function CA.phase_num(v)
  if type(v) == "number" then return v end
  local n = tonumber(v)
  if n then return n end
  local E = rawget(_G, "Phase")
  if type(E) == "table" then for k, ev in pairs(E) do if ev == v and CA.PH[k] then return CA.PH[k] end end end
end
function CA.camps_of(fid)   -- { {id, ph, enemy, mp}... } активные кампании фракции (lektor: # и индекс); ошибка движка - наверх
  local fo = getGameWorld().factionMgr:getFactionByStringID(fid)
  local l = fo and fo.warMgr and fo.warMgr.activeCampaigns
  local out = {}
  if not l then return out end
  for i = 1, #l do
    local inst = l[i]
    if inst then
      local en = inst.enemy
      out[#out + 1] = { id = inst.uniqueID, ph = CA.phase_num(inst.currentPhase), enemy = en and ((en.data and en.data.stringID) or en.id), mp = inst.manPowerLastCount }
    end
  end
  return out
end
-- U2: рейд на базу игрока = родная кампания движка (путь CA.pick/CA.fire/CA.note, как CA.try и осады KMM_Siege).
-- Запуск только рядом с игроком (зона базы загружена); цель - ближайший к базе город фракции игрока в FactionWarMgr игрока (? игра: поведение
-- getNearestTown для аванпоста игрока не видели). Привязка к CampaignInstance сразу после fire (новый id в activeCampaigns, enemy строго = игрок),
-- иначе - в опросе. Опрос CA.base_step из on_tick раз в player_base.poll_seconds (~30 с реального времени), дни - игровые (KC.game_day):
--   RETREATING -> repelled; VICTORY/ASSAULT_2_HAPPY -> sacked (игрок был у базы) | unattended (никого не было); кампания исчезла посреди штурма ->
--   repelled/unattended по присутствию; исчезла в GATHERING -> рейд рассыпался, без исхода.
-- Одно событие на рейд: base_campaign при привязке; кампания так и не появилась за bind_days -> base_raid (старый путь Traces). Если кампания
-- была привязана, рейда Traces не будет никогда (сбой движка/таймаут - просто конец без исхода). Состояние S.bcamp (в сейве).
function CA.blog(msg) CA.log("base " .. tostring(msg)) end
function CA.today() return KC.game_day() or KC.DAY end
function CA.base_text(fid, why)
  return string.format("%s are marching on the Nameless settlement (%s).", KC.name(fid),
    why == "need" and "they are desperate" or why == "revenge" and "for revenge" or "for its riches")
end
function CA.base_bind(R, list)   -- новая кампания фракции против игрока (не из pre); true = привязана, событие base_campaign
  local pf = KC.CFG.player_faction
  local pre = {}; for _, id in ipairs(R.pre or {}) do pre[id] = true end
  for _, e in ipairs(list) do
    if e.id and not pre[e.id] and e.enemy == pf then
      R.st, R.cid, R.ph, R.mp, R.pre = "bound", e.id, e.ph, e.mp, nil
      CA.blog(string.format("bound %s id=%s phase=%s men=%s", R.fid, tostring(e.id), tostring(CA.PHN[e.ph or -1] or e.ph), tostring(e.mp)))
      KC.emit({ type = "base_campaign", a = R.fid, b = pf, why = R.why, native = true, campaign = R.sid, text = CA.base_text(R.fid, R.why) })
      return true
    end
  end
  return false
end
function CA.base_try(fid, why)   -- true = кампания запущена (событие даст привязка или фолбэк); false = звать старый путь base_raid
  local G, PB = CA.CP(), KC.P.player_base or {}
  local B, pf = KC.S.base, KC.CFG.player_faction
  if PB.native == false or G.enabled == false or CA.off_now() or CA.PROBE["triggerCampaign"] == false then return false, "native off" end
  if not (B and B.x and pf and KC.S.F[fid]) or KC.S.bcamp then return false, "busy or no base" end
  local ok, res, rw = pcall(function()
    if not CA.near_player(B.x, B.z, G.load_radius or 15000) then return false, "player far" end   -- незагруженная зона: поведение очереди не проверено
    if not CA.limits_ok(fid) then return false, "campaign limits" end
    local D = CA.data()
    if not (D and D.factions[fid]) then return false, "no FACTION_CAMPAIGN" end
    local sid = CA.pick(fid, { "raid", "assault" }, G.max_forces or 30)
    if not sid then return false, "no usable campaign" end
    local gw = getGameWorld()
    local fo, po = gw.factionMgr:getFactionByStringID(fid), gw.factionMgr:getFactionByStringID(pf)
    if not (fo and fo.warMgr and po and po.warMgr) then return false, "no warMgr" end
    local target = po.warMgr:getNearestTown({ x = B.x, y = 0, z = B.z })
    local home = fo.warMgr:getNearestTown(CA.home_pos(fid, B.x, B.z))
    if not (target and home) then return false, "no target/home town" end
    local pre = {}
    for _, e in ipairs(CA.camps_of(fid)) do if e.id then pre[#pre + 1] = e.id end end
    if not CA.fire(fid, sid, target, home, "base") then return false, "triggerCampaign failed" end
    CA.note(fid)
    local R = { fid = fid, sid = sid, why = why, day = CA.today(), st = "fired", pre = pre }
    KC.S.bcamp = R
    KC.S.stats.base_campaigns = (KC.S.stats.base_campaigns or 0) + 1
    CA.blog(string.format("fired %s %s day %s (%s)", tostring(fid), tostring(sid), tostring(R.day), tostring(why)))
    local okb, er = pcall(function() CA.base_bind(R, CA.camps_of(fid)) end)   -- сразу: ванильный рейд может кончиться раньше следующего опроса
    if not okb then CA.blog("bind error (poll will retry): " .. tostring(er)) end
    return true
  end)
  if not ok then CA.blog("launch error -> Traces raid: " .. tostring(res)); return false, "engine error" end
  if not res then CA.blog("not launched (" .. tostring(rw) .. ") -> Traces raid " .. tostring(fid)) end
  return res and true or false, rw
end
function CA.base_end(R, why, raid)   -- конец без исхода; raid = кампания так и не появилась -> единственное событие рейда base_raid (Traces)
  KC.S.bcamp = nil
  if raid and R.st == "fired" and KC.S.F[R.fid] and KC.S.F[R.fid].alive then
    CA.blog("lost " .. tostring(R.fid) .. " (" .. tostring(why) .. ") -> Traces raid")
    KC.emit({ type = "base_raid", a = R.fid, b = KC.CFG.player_faction, why = R.why, text = CA.base_text(R.fid, R.why) })
  else
    CA.blog("ended " .. tostring(R.fid) .. " (" .. tostring(why) .. "), no Traces raid")
  end
end
function CA.base_poll(R)   -- исход по фазе или nil (ждём)
  local PH, PB, B = CA.PH, KC.P.player_base or {}, KC.S.base
  local list = CA.camps_of(R.fid)
  if R.st == "fired" and not CA.base_bind(R, list) then
    if CA.today() - R.day > (PB.bind_days or 2) then return "lost" end
    return nil
  end
  local here = B and B.x and CA.near_player(B.x, B.z, PB.present_radius or 4000)
  local cur
  for _, e in ipairs(list) do if e.id == R.cid then cur = e; break end end
  if cur then
    if cur.ph ~= R.ph then CA.blog(string.format("phase %s %s -> %s men=%s", R.fid, tostring(CA.PHN[R.ph or -1] or R.ph), tostring(CA.PHN[cur.ph or -1] or cur.ph), tostring(cur.mp))) end
    R.ph, R.mp = cur.ph, cur.mp
  end
  if here and R.ph and R.ph ~= PH.GATHERING then R.present = true end   -- игрок был у базы во время штурма
  local ph = R.ph
  if ph == PH.RETREATING then return "repelled" end
  if ph == PH.VICTORY or ph == PH.ASSAULT_2_HAPPY then return R.present and "sacked" or "unattended" end
  if not cur then   -- endCampaign посреди штурма (люди кончились) или до него
    if ph == PH.ASSAULTING or ph == PH.ASSAULT_2_ANGRY then return R.present and "repelled" or "unattended" end
    return "faded"
  end
  if CA.today() - R.day > (PB.camp_max_days or 20) then return "timeout" end
  return nil
end
function CA.base_step()
  local R = KC.S and KC.S.bcamp
  if not R then return end
  local ok, how = pcall(CA.base_poll, R)
  if not ok then CA.base_end(R, "engine error: " .. tostring(how), false); return end
  if not how then return end
  if how == "lost" then CA.base_end(R, "campaign never started", true); return end
  KC.S.bcamp = nil
  CA.blog(string.format("outcome %s: %s (phase %s)", tostring(R.fid), how, tostring(CA.PHN[R.ph or -1] or R.ph)))
  if how == "repelled" or how == "sacked" or how == "unattended" then KC.base_result(how, R.fid, true) end
end
-- ближайший к игроку город цели в радиусе загруженной зоны (raid) либо заданный (capture); возвращает sid, x, z
function CA.pick_town(o, town)
  local R = CA.CP().load_radius or 15000
  local best, bd, bx, bz
  local list = {}
  if town then list[1] = town else for t in pairs(KC.S.F[o].towns) do list[#list + 1] = t end; table.sort(list) end
  for _, t in ipairs(list) do
    local I = KC.CFG.town_info and KC.CFG.town_info[t]
    if I and I.x then
      local d = CA.near_player(I.x, I.z, R)
      if d and (not bd or d < bd) then best, bd, bx, bz = t, d, I.x, I.z end
    end
  end
  return best, bx, bz
end
function CA.home_pos(fid, bx, bz)   -- свой город фракции, ближайший к цели
  local best, hx, hz
  for t in pairs(KC.S.F[fid].towns or {}) do
    local I = KC.CFG.town_info and KC.CFG.town_info[t]
    if I and I.x then
      local d = (I.x - bx) ^ 2 + (I.z - bz) ^ 2
      if not best or d < best then best, hx, hz = d, I.x, I.z end
    end
  end
  return { x = hx or bx, y = 0, z = hz or bz }
end
-- решение дирижёра: фракция fid бьёт по o (a = "raid" | "capture"); true = родная кампания запущена
function CA.try(fid, o, a, town)
  local G = CA.CP()
  if G.enabled == false or CA.off_now() or not KC.S.F[fid] or not KC.S.F[o] then return false end
  if CA.PROBE["triggerCampaign"] == false then return false end
  if (KC.S.F[fid].camp_day or -1000) == KC.DAY then return false end   -- ore_campaign сегодня уже запускал
  if KC.treaty_between(fid, o) or not CA.limits_ok(fid) then return false end
  local ok, res = pcall(function()
    if not CA.data() then return false end
    local t, tx, tz = CA.pick_town(o, town)
    if not t then return false end   -- незагруженная зона: поведение triggerCampaign неизвестно - только рядом с игроком
    if not CA.data().factions[fid] then return false end
    if math.random() >= ((a == "capture") and (G.p_capture or 0.25) or (G.p_raid or 0.15)) then return false end   -- бросок только когда запуск возможен (без игрока RNG симуляции не трогаем)
    local sid, kind = CA.pick(fid, a == "capture" and { "assault", "raid" } or { "raid", "assault" }, G.max_forces or 30)
    if not sid then return false end
    local gw = getGameWorld()
    local fo, oo = gw.factionMgr:getFactionByStringID(fid), gw.factionMgr:getFactionByStringID(o)
    if not (fo and fo.warMgr and oo and oo.warMgr) then return false end
    local target = oo.warMgr:getNearestTown({ x = tx, y = 0, z = tz })
    local home = fo.warMgr:getNearestTown(CA.home_pos(fid, tx, tz))
    if not (target and home) then return false end
    if not CA.fire(fid, sid, target, home) then return false end
    CA.note(fid)
    KC.S.stats.native_campaigns = (KC.S.stats.native_campaigns or 0) + 1
    KC.P._ncur = { a = fid, b = o, day = KC.DAY }
    KC.emit({ type = "native_campaign", a = fid, b = o, town_sid = t, town_name = KC.TOWN_NAME[t] or t, campaign = sid, kind = kind, native = true,
           text = string.format("%s marched on %s (%s).", KC.name(fid), KC.TOWN_NAME[t] or t, KC.name(o)) })
    -- подкрепление: союзник цели с вероятностью q шлёт родную кампанию помощи на тот же город
    local allies = KC.allies_of(o, { defense = true, military = true, vassal = true })
    table.sort(allies, function(x, y) return x.other < y.other end)
    for _, e in ipairs(allies) do
      local al = e.other
      if al ~= fid and KC.S.F[al] and KC.S.F[al].alive and not KC.S.F[al].player and KC.rel(al, o) >= (G.ally_rel or 30) and CA.limits_ok(al)
         and math.random() < (G.q_reinforce or 0.4) then
        local rs = CA.pick(al, { "reinforce" }, G.max_forces or 30)
        local ho = rs and gw.factionMgr:getFactionByStringID(al)
        local home2 = ho and ho.warMgr and ho.warMgr:getNearestTown(CA.home_pos(al, tx, tz))
        if rs and home2 and CA.fire(al, rs, target, home2) then
          CA.note(al)
          KC.S.stats.native_reinforce = (KC.S.stats.native_reinforce or 0) + 1
          KC.emit({ type = "native_reinforce", a = al, b = o, lead = fid, town_sid = t, town_name = KC.TOWN_NAME[t] or t, campaign = rs, native = true,
                 text = string.format("%s sent men to help %s hold %s.", KC.name(al), KC.name(o), KC.TOWN_NAME[t] or t) })
          break
        end
      end
    end
    return true
  end)
  if not ok then
    local p = KC.GL.h_down(CA, "OFF", "KMM_Conductor.campaign", res)
    CA.log(p and ("native campaigns failed, retry in " .. p .. " s: " .. tostring(res)) or ("native campaigns disabled until restart: " .. tostring(res)))
    return false
  end
  KC.GL.h_ok("KMM_Conductor.campaign")
  return res and true or false
end
-- родные флаги RelationData по договорам/войне дирижёра (alliance/peaceTreaty/war); declareWar / setNoLongerEnemies при смене состояния
function CA.flags(a, b, fa, fb, v)
  local G = CA.CP()
  if G.relflags == false or KC.GL.h_live(CA, "RELOFF") then return end
  local al = KC.treaty_between(a, b, "defense") or KC.treaty_between(a, b, "military") or KC.treaty_between(a, b, "vassal")
  local pe = KC.treaty_between(a, b, "nonaggression") or KC.treaty_between(a, b, "trade")
  local fa_, fb_ = KC.S.F[a], KC.S.F[b]
  local recent = fa_ and fb_ and (KC.DAY - (fa_.last_war or -1e9) < (G.war_days or 60) or KC.DAY - (fb_.last_war or -1e9) < (G.war_days or 60))
  local war = (not al and not pe and recent and v <= (G.war_rel or -60)) and true or false   -- только реальная война дирижёра, не стартовая вражда
  KC.S.relflag = KC.S.relflag or {}
  local key = a < b and (a .. "|" .. b) or (b .. "|" .. a)
  local code = (al and 1 or 0) + (pe and 2 or 0) + (war and 4 or 0)
  if KC.S.relflag[key] == code or (KC.S.relflag[key] == nil and code == 0) then return end
  local was = KC.S.relflag[key] or 0
  if type(fa.relations.getRelationData) ~= "function" then return end   -- нет метода (заглушка/другая версия): флаги не пишем, без шума
  local ok = CA.probe_call("RelationData", function()
    for _, p in ipairs({ { fa, fb }, { fb, fa } }) do
      local rd = p[1].relations:getRelationData(p[2])
      if rd then rd.alliance, rd.peaceTreaty, rd.war = al and true or false, pe and true or false, war end
    end
  end)
  if not ok then
    if not CA.probe_ok("RelationData") then KC.GL.h_forever(CA, "RELOFF", "KMM_Conductor.relflags", "crash lock state/probe_RelationData.off", "crash"); CA.log("RelationData flags disabled (crash lock)"); return end
    local p = KC.GL.h_down(CA, "RELOFF", "KMM_Conductor.relflags", "RelationData write failed")
    CA.log(p and ("RelationData flags failed, retry in " .. p .. " s") or "RelationData flags disabled until restart"); return
  end
  KC.GL.h_ok("KMM_Conductor.relflags")
  if war and was < 4 then CA.probe_call("declareWar", function() fa.relations:declareWar(fb); fb.relations:declareWar(fa) end)
  elseif not war and was >= 4 then CA.probe_call("setNoLongerEnemies", function() fa.relations:setNoLongerEnemies(fb); fb.relations:setNoLongerEnemies(fa) end) end
  KC.S.relflag[key] = code
end
end
-- Q5 (2026-11-15): отношения живут в ядре. Ядро само двигает RelationData.relation на дела (атака, убийство, лечение, плен -
-- колбэк FactionRelations::affectRelations), в каждую сторону своё число; модель S.rel симметрична и целочисленна.
--   GL.rs.seen["a>b"] (на сессию) - что ядро держало при нашем последнем чтении/записи. Разница с getFactionRelation = ванильная
--     дельта: вливается в модель (без dirty_rel - ядро её уже знает), а не затирается. Пары сверяются по кругу, пары игрока чаще.
--   S.relq["a|b"] (a<b, в сейве) - цель модели (с полом COHAB), с которой ядро уже согласовано. Своё изменение дирижёр отдаёт ядру
--     дельтой: setRelation(текущее + (цель - relq)). Первая запись пары (relq нет) - абсолютная, как до Q5 (семя мира, лор).
--   Шина deed (KMM_Deeds) - только подсказка «пару тронули, прочти сейчас»: число берётся из ядра, дело не считается дважды.
--   Ядра нет (офлайн, нет getFactionRelation) - чтение даёт nil и запись идёт абсолютной; ошибка - GL.rs.off до перезапуска.
-- Параметры (необязательно) P.materialize.relsync = { enabled, every_s, batch, player, hot, min_delta, div, mark_every }.
-- HEALTH (2026-11-15): отказы связок ядра — в реестр KMM_Gov через KC.GL.h_down/h_live/h_forever (Base, блок GOALS): пауза и повтор.
KC.GL.rs = { seen = {}, hot = {}, nhot = 0, i = 1, j = 2, pj = 0, last = -1e9, steps = 0 }
function KC.GL.rs_st0()
  KC.GL.rs.st = { scan = 0, merged = 0, sum = 0, big = 0, div = 0, maxdiv = 0, maxk = "-", dwr = 0, awr = 0, wrmis = 0, hint = 0 }
end
KC.GL.rs_st0()
function KC.GL.rs_cfg()
  local m = KC.P and KC.P.materialize
  return (m and type(m.relsync) == "table") and m.relsync or {}
end
function KC.GL.rs_log(msg)
  pcall(KC.append_file, (KC.P and KC.P.guard and KC.P.guard.debug_log) or "C:/KenshiModMap/logs/debug.log", os.date("%Y-%m-%d %H:%M:%S") .. " [KMM_Conductor] " .. msg)
  KC.log(msg)
end
function KC.GL.rs_fail(err)
  local p = KC.GL.h_down(KC.GL.rs, "off", "KMM_Conductor.relsync", err)
  if p then KC.GL.rs_log("relsync failed, retry in " .. p .. " s (relations written as absolute values meanwhile): " .. tostring(err))
  else KC.GL.rs_log("relsync disabled until restart (relations written as absolute values): " .. tostring(err)) end
end
function KC.GL.rs_key(a, b) if a < b then return a .. "|" .. b end return b .. "|" .. a end
function KC.GL.rs_target(a, b, v)   -- COHAB (баг Mongrel 14.11): соседи по городу в движке не враги — иначе стража и лавки дерутся в городе
  if v < 0 then
    if KC.GL.cohab == nil or KC.GL.cohab_src ~= KC.CFG.cohab then KC.GL.cohab_src = KC.CFG.cohab; KC.GL.cohab = {}; for _, pr in ipairs(KC.CFG.cohab or {}) do KC.GL.cohab[pr[1] .. "|" .. pr[2]] = true; KC.GL.cohab[pr[2] .. "|" .. pr[1]] = true end end
    if KC.GL.cohab[a .. "|" .. b] then return 0, true end
  end
  return v, false
end
function KC.GL.rs_get(fa, fb)
  local ok, v = pcall(function() return fa.relations:getFactionRelation(fb) end)
  if ok and type(v) == "number" and v == v then return v end
  return nil
end
function KC.GL.rs_fresh()   -- другой мир/сейв: числа ядра прошлого мира не сравнивать
  local R = KC.GL.rs
  if R.for_S ~= KC.S then R.for_S = KC.S; R.seen = {}; R.hot = {}; R.nhot = 0; R.ids = nil end
end
-- пара: прочесть ядро в обе стороны, влить ванильную дельту в модель; вернуть cur_ab, cur_ba (nil - ядра нет)
function KC.GL.rs_sync(a, b, fa, fb)
  local R, c = KC.GL.rs, KC.GL.rs_cfg()
  KC.GL.rs_fresh()
  local cab, cba = KC.GL.rs_get(fa, fb), KC.GL.rs_get(fb, fa)
  if not (cab and cba) then return nil end
  R.st.scan = R.st.scan + 1
  local kab, kba = a .. ">" .. b, b .. ">" .. a
  local sab, sba = R.seen[kab], R.seen[kba]
  local k = KC.GL.rs_key(a, b)
  if KC.S.relq and KC.S.relq[k] then   -- расхождение модели и ядра (только согласованные пары)
    local T = KC.GL.rs_target(a, b, KC.rel(a, b))
    local dv = math.max(math.abs(cab - T), math.abs(cba - T))
    if dv >= (c.div or 5) then R.st.div = R.st.div + 1 end
    if dv > R.st.maxdiv then R.st.maxdiv = dv; R.st.maxk = kab end
  end
  if not (sab and sba) then R.seen[kab], R.seen[kba] = cab, cba; return cab, cba end
  local dab, dba = cab - sab, cba - sba
  local d = (math.abs(dab) >= math.abs(dba)) and dab or dba   -- ведущая сторона: модель одна на пару
  if math.abs(d) < (c.min_delta or 1) then return cab, cba end   -- мелочь копится в ядре до целого
  local m = d >= 0 and math.floor(d + 0.5) or -math.floor(-d + 0.5)
  local old = KC.rel(a, b)
  local nv = KC.clamp(old + m, -100, 100)
  KC.S.rel[a] = KC.S.rel[a] or {}; KC.S.rel[b] = KC.S.rel[b] or {}
  KC.S.rel[a][b], KC.S.rel[b][a] = nv, nv
  if KC.S.relq and KC.S.relq[k] then KC.S.relq[k] = KC.S.relq[k] + (nv - old) end   -- база согласования сдвигается вместе с ядром
  R.seen[kab], R.seen[kba] = cab, cba
  R.st.merged = R.st.merged + 1; R.st.sum = R.st.sum + math.abs(d)
  if math.abs(d) >= 20 then R.st.big = R.st.big + 1 end
  KC.S.stats.rel_merged = (KC.S.stats.rel_merged or 0) + 1
  if not R.first then
    R.first = true
    KC.GL.rs_log(string.format("RELSYNC first merge: %s core %.2f->%.2f (%s %.2f->%.2f) model %d->%d", kab, sab, cab, kba, sba, cba, old, nv))
  end
  return cab, cba
end
function KC.GL.rs_after(a, b, fa, fb, nab, nba)   -- читаем записанное назад: что ядро реально держит (диапазон/обрезка ядра - ?)
  local R = KC.GL.rs
  local rab, rba = KC.GL.rs_get(fa, fb), KC.GL.rs_get(fb, fa)
  if (rab and math.abs(rab - nab) > 0.01) or (rba and math.abs(rba - nba) > 0.01) then
    R.st.wrmis = R.st.wrmis + 1
    if not R.mis1 then R.mis1 = true; KC.GL.rs_log(string.format("RELSYNC write mismatch: %s>%s set %.2f read %s", a, b, nab, tostring(rab))) end
  end
  R.seen[a .. ">" .. b] = rab or nab; R.seen[b .. ">" .. a] = rba or nba
end
-- запись пары из очереди dirty_rel: дельтой к ядру, если пара уже согласована; иначе абсолютная (как до Q5)
function KC.GL.rs_write(a, b, fa, fb)
  local R = KC.GL.rs
  local cab, cba
  if not R.off and KC.GL.rs_cfg().enabled ~= false then
    local ok, x, y = pcall(KC.GL.rs_sync, a, b, fa, fb)
    if ok then cab, cba = x, y else KC.GL.rs_fail(x) end
  end
  local v, fl = KC.GL.rs_target(a, b, KC.rel(a, b))
  if fl then KC.S.stats.cohab_floor = (KC.S.stats.cohab_floor or 0) + 1 end
  KC.S.relq = KC.S.relq or {}
  local k = KC.GL.rs_key(a, b)
  local q = KC.S.relq[k]
  if cab and cba and q and not R.off then
    local dm = v - q
    local nab, nba = KC.clamp(cab + dm, -100, 100), KC.clamp(cba + dm, -100, 100)
    if fl then nab, nba = math.max(nab, 0), math.max(nba, 0) end
    fa.relations:setRelation(fb, nab)
    fb.relations:setRelation(fa, nba)
    R.st.dwr = R.st.dwr + 1
    if not pcall(KC.GL.rs_after, a, b, fa, fb, nab, nba) then R.seen[a .. ">" .. b], R.seen[b .. ">" .. a] = nil, nil end
  else
    fa.relations:setRelation(fb, v)
    fb.relations:setRelation(fa, v)
    R.st.awr = R.st.awr + 1
    if cab and cba and not R.off and not pcall(KC.GL.rs_after, a, b, fa, fb, v, v) then R.seen[a .. ">" .. b], R.seen[b .. ">" .. a] = nil, nil end
  end
  KC.S.relq[k] = v
  return v
end
function KC.GL.rs_mark()
  local R, s = KC.GL.rs, KC.GL.rs.st
  KC.GL.rs_log(string.format("RELSYNC steps=%d scanned=%d merged=%d sum=%.1f big=%d diverged=%d maxdiv=%.1f at %s writes delta=%d abs=%d mismatch=%d hints=%d aligned=%d",
    R.steps, s.scan, s.merged, s.sum, s.big, s.div, s.maxdiv, s.maxk, s.dwr, s.awr, s.wrmis, s.hint, KC.count(KC.S.relq or {})))
  KC.GL.rs_st0()
end
-- сверка по кругу: подсказки шины, затем пары игрока, затем все пары; раз в every_s секунд
function KC.GL.rs_step()
  local R, c = KC.GL.rs, KC.GL.rs_cfg()
  if R.off or c.enabled == false then return end
  local now = os.clock()
  if now - R.last < (c.every_s or 2) then return end
  R.last = now
  KC.GL.rs_fresh()
  if not R.ids then
    R.ids = {}; for fid in pairs(KC.S.F) do R.ids[#R.ids + 1] = fid end
    table.sort(R.ids); R.i, R.j, R.pj = 1, 2, 0
  end
  local ids, n = R.ids, #R.ids
  if n < 2 then return end
  local FO = {}
  local function fo(id) local f = FO[id]; if f == nil then f = KC.faction_obj(id) or false; FO[id] = f end; return f or nil end
  local function one(a, b)
    if not (a and b) or a == b or not (KC.S.F[a] and KC.S.F[b]) then return end
    local fa, fb = fo(a), fo(b)
    if fa and fb then KC.GL.rs_sync(a, b, fa, fb) end
  end
  local k = 0
  for key in pairs(R.hot) do
    R.hot[key] = nil; R.nhot = R.nhot - 1
    local a, b = key:match("^(.-)|(.*)$"); one(a, b)
    k = k + 1; if k >= (c.hot or 16) then break end
  end
  local pf = KC.CFG.player_faction
  if pf and KC.S.F[pf] then for _ = 1, (c.player or 8) do R.pj = R.pj % n + 1; one(pf, ids[R.pj]) end end
  for _ = 1, (c.batch or 24) do
    one(ids[R.i], ids[R.j])
    R.j = R.j + 1
    if R.j > n then R.i = R.i + 1; if R.i >= n then R.i = 1 end; R.j = R.i + 1 end
  end
  R.steps = R.steps + 1
  if R.steps == 5 or R.steps % (c.mark_every or 60) == 0 then KC.GL.rs_mark() end
end
KC.subscribe("deed", function(ev)   -- подсказка: ядро только что тронуло пару (KMM_Deeds видит affectRelations)
  local R = KC.GL.rs
  if R.off or not KC.S or type(ev) ~= "table" then return end
  local a, b = ev.a, ev.b
  if not (a and b and a ~= b and KC.S.F[a] and KC.S.F[b]) then return end
  local k = KC.GL.rs_key(a, b)
  if not R.hot[k] and R.nhot < 64 then R.hot[k] = true; R.nhot = R.nhot + 1; R.st.hint = R.st.hint + 1 end
end)
-- S2 (2026-11-15): сила, богатство и владение городами сверяются с ядром (подход Q5: читать порциями, вливать дельту).
--   Сила: Faction:getFactionSize() (запасной счёт - #getActivePlatoons + #getUnloadedPlatoons, он не зависит от загрузки зоны).
--     Первое чтение за сессию - семя; дальше относительная дельта численности вливается в S.F[].strength с весом w_str и
--     потолком cap_str за чтение. Скачок больше jump (загрузка/выгрузка зоны или иная семантика счёта - ?) не вливается: новое семя.
--     Колбэк Faction::destroyPlatoon - только подсказка «прочти фракцию сейчас» и счётчик: число берётся из getFactionSize,
--     потеря не считается дважды.
--     Ревью M1 (двойной счёт, дрейф вверх): (1) рост численности не вливается (w_up=0): ванильный респаун и наши спавны
--     (Traces/Outlaws/Fates/dispatch) из ядра неотличимы, сила растёт регеном модели; рост копится в кредит R.cr, и падение
--     сначала гасит его (свой отряд пришёл и ушёл/погиб - сеть ноль). (2) Падение вливается только при подсказке destroyPlatoon
--     с прошлого чтения (need_hint; без неё - выгрузка зоны/уход). (3) Окно объяснённых потерь R.ex: насколько модель сама уронила
--     силу событиями (засада, KMM_Self, рейд) с прошлого чтения, затухает ex_keep за чтение; вливается только остаток сверх него.
--   Богатство: Faction:getProsperityMultiplier() (ванильное процветание; разбитые отряды его снижают). Относительная дельта
--     множителя вливается в S.F[].wealth (w_wealth, cap_wealth). Абсолют не пишется: шкалы модели и ядра разные (?), только лог расхождения.
--   Города: FactionWarMgr.myTowns фракции - кому город принадлежит в ядре; сверка с S.F[].towns, расхождение - в лог (модель не чинится).
--   Ядра нет (офлайн, методов нет) - чтения дают nil, модель живёт сама. Ошибка в логике - GL.cs.off до перезапуска.
-- Параметры (необязательно) P.materialize.coresync = { enabled, every_s, batch, hot, w_str, cap_str, jump, floor, src,
--   w_up, need_hint, ex_keep, w_wealth, cap_wealth, min_pm, pdiv, towns, tbatch, tmax, pop, tlog_max, mark_every }.
KC.GL.cs = { seen = {}, pm = {}, hot = {}, nhot = 0, hit = {}, cr = {}, ex = {}, sv = {}, tlog = {}, ntlog = 0, i = 0, ti = 0, last = -1e9, steps = 0 }
function KC.GL.cs_st0()
  KC.GL.cs.st = { read = 0, sm = 0, up = 0, down = 0, ssum = 0, jump = 0, lost = 0, hot = 0, size = 0, plat = 0,
               pread = 0, pm = 0, pmsum = 0, wm = 0, wsum = 0, pdiv = 0, tf = 0, tchk = 0, tok = 0, tdiv = 0, pop = 0,
               credit = 0, nohint = 0, explained = 0 }
end
KC.GL.cs_st0()
function KC.GL.cs_cfg()
  local m = KC.P and KC.P.materialize
  return (m and type(m.coresync) == "table") and m.coresync or {}
end
function KC.GL.cs_fail(err)
  local p = KC.GL.h_down(KC.GL.cs, "off", "KMM_Conductor.coresync", err)
  if p then KC.GL.rs_log("CORESYNC failed, retry in " .. p .. " s (model runs on its own meanwhile): " .. tostring(err))
  else KC.GL.rs_log("CORESYNC disabled until restart (model runs on its own): " .. tostring(err)) end
end
function KC.GL.cs_fresh()   -- другой мир/сейв: числа ядра прошлого мира не сравнивать
  local R = KC.GL.cs
  if R.for_S ~= KC.S then R.for_S = KC.S; R.seen = {}; R.pm = {}; R.hot = {}; R.nhot = 0; R.hit = {}; R.cr = {}; R.ex = {}; R.sv = {}; R.tlog = {}; R.ntlog = 0; R.ids = nil; R.y = nil end
end
function KC.GL.cs_num(fn)
  local ok, v = pcall(fn)
  if ok and type(v) == "number" and v == v then return v end
  return nil
end
-- численность фракции в ядре: значение для сверки, getFactionSize, число отрядов (nil - нет)
function KC.GL.cs_size(fo, src)
  local plat = KC.GL.cs_num(function() return #fo:getActivePlatoons() + #fo:getUnloadedPlatoons() end)
  local size = KC.GL.cs_num(function() return fo:getFactionSize() end)
  if src == "platoons" then return plat, size, plat end
  return size or plat, size, plat
end
function KC.GL.cs_one(fid)
  local f = KC.S.F[fid]
  if not (f and f.alive) or f.player then return end
  local fo = KC.faction_obj(fid)
  if not fo then return end
  local R, c, st = KC.GL.cs, KC.GL.cs_cfg(), KC.GL.cs.st
  local v, size, plat = KC.GL.cs_size(fo, c.src)
  local conf = false
  if size then st.size = st.size + size end
  if plat then st.plat = st.plat + plat end
  if v then
    st.read = st.read + 1
    local old = R.seen[fid]
    R.seen[fid] = v
    local hint = R.hit[fid]; R.hit[fid] = nil
    local ex, sv = (R.ex[fid] or 0) * (c.ex_keep or 0.5), R.sv[fid]
    if sv and sv > 0 and f.strength < sv then ex = ex + (sv - f.strength) / sv end   -- модель сама уронила силу с прошлого чтения
    if old and v ~= old then
      local base = math.max(old, c.floor or 8)
      local r = (v - old) / base
      if math.abs(r) > (c.jump or 0.5) then
        st.jump = st.jump + 1
        if not R.jump1 then R.jump1 = true; KC.GL.rs_log(string.format("CORESYNC strength jump reseed: %s core %d->%d", fid, old, v)) end
      else
        local s0, un = f.strength, 0
        if v > old then
          R.cr[fid] = (R.cr[fid] or 0) + (v - old)
          un = r * (c.w_up or 0)
        else
          local cr = R.cr[fid] or 0
          local use = math.min(cr, old - v)
          R.cr[fid] = cr - use; st.credit = st.credit + use
          local rl = (old - v - use) / base
          if rl > 0 then
            if not hint and c.need_hint ~= false then st.nohint = st.nohint + 1
            else
              conf = true   -- Y2: потеря подтверждена (подсказка destroyPlatoon + падение сверх кредита своих спавнов)
              un = -math.max(0, rl - ex) * (c.w_str or 0.5)
              ex = math.max(0, ex - rl)
              if un == 0 then st.explained = st.explained + 1 end
            end
          end
        end
        if un ~= 0 then
          local cap = c.cap_str or 0.1
          f.strength = math.max(0, s0 * (1 + KC.clamp(un, -cap, cap)))
          st.sm = st.sm + 1; st.ssum = st.ssum + math.abs(f.strength - s0)
          if un > 0 then st.up = st.up + 1 else st.down = st.down + 1 end
          KC.S.stats.str_merged = (KC.S.stats.str_merged or 0) + 1
          if not R.first then
            R.first = true
            KC.GL.rs_log(string.format("CORESYNC first strength merge: %s core %d->%d model %.1f->%.1f", fid, old, v, s0, f.strength))
          end
        end
      end
    end
    R.ex[fid] = ex; R.sv[fid] = f.strength
  end
  KC.GL.y2_apply(fid, fo, conf)   -- до чтения процветания: эффект вызова ядра попадёт в богатство этим же чтением (один раз)
  local pm = KC.GL.cs_num(function() return fo:getProsperityMultiplier() end)
  if pm and pm > 0 then
    st.pread = st.pread + 1; st.pmsum = st.pmsum + pm
    local old = R.pm[fid]
    R.pm[fid] = pm
    if old and old > 0 then
      local r = pm / old - 1
      if math.abs(r) >= (c.min_pm or 0.01) then
        local cap = c.cap_wealth or 0.08
        local w0 = f.wealth
        f.wealth = math.max(0, w0 * (1 + KC.clamp(r * (c.w_wealth or 0.5), -cap, cap)))
        st.wm = st.wm + 1; st.wsum = st.wsum + math.abs(f.wealth - w0)
        KC.S.stats.wealth_merged = (KC.S.stats.wealth_merged or 0) + 1
        if not R.pfirst then
          R.pfirst = true
          KC.GL.rs_log(string.format("CORESYNC first prosperity merge: %s core %.3f->%.3f wealth %.1f->%.1f", fid, old, pm, w0, f.wealth))
        end
      end
    end
    if math.abs(f.wealth / math.max(1, f.wealth0 or 1) - pm) >= (c.pdiv or 0.5) then st.pdiv = st.pdiv + 1 end   -- сравнимость шкал - ?
  end
end
-- владение: города, которые ядро числит за фракцией (FactionWarMgr.myTowns), против модели S.F[].towns
function KC.GL.cs_towns(fid)
  local fo = KC.faction_obj(fid)
  if not fo then return end
  local R, c, st = KC.GL.cs, KC.GL.cs_cfg(), KC.GL.cs.st
  local okl, list = pcall(function() return fo.warMgr and fo.warMgr.myTowns end)
  if not (okl and list) then return end
  local nl = KC.GL.cs_num(function() return #list end)
  if not nl then return end
  st.tf = st.tf + 1
  for i = 1, math.min(nl, c.tmax or 16) do
    local okt, t, sid = pcall(function() local t = list[i]; local gd = t and (t.data or t:getGameData()); return t, gd and gd.stringID end)
    if okt and sid and KC.CFG.town_info and KC.CFG.town_info[sid] then
      st.tchk = st.tchk + 1
      local m = KC.owner_of(sid)
      if m == fid then st.tok = st.tok + 1
      else
        st.tdiv = st.tdiv + 1
        if R.tlog[sid] ~= fid and R.ntlog < (c.tlog_max or 8) then
          R.tlog[sid] = fid; R.ntlog = R.ntlog + 1
          KC.S.stats.town_owner_div = (KC.S.stats.town_owner_div or 0) + 1
          KC.GL.rs_log(string.format("CORESYNC town owner differs: %s core=%s model=%s", sid, fid, tostring(m)))
        end
      end
      if c.pop ~= false then
        local p = KC.GL.cs_num(function() return fo:countPopulation(t) end)
        if p then st.pop = st.pop + p end
      end
    end
  end
end
function KC.GL.cs_mark()
  local R, s = KC.GL.cs, KC.GL.cs.st
  KC.GL.rs_log(string.format("CORESYNC steps=%d str read=%d merged=%d up=%d down=%d sum=%.1f jumps=%d lost=%d hot=%d size=%d plat=%d"
    .. " | prosp read=%d merged=%d sum=%.1f avg=%.3f div=%d | towns fac=%d checked=%d agree=%d diverged=%d pop=%d",
    R.steps, s.read, s.sm, s.up, s.down, s.ssum, s.jump, s.lost, s.hot, s.size, s.plat,
    s.pread, s.wm, s.wsum, s.pread > 0 and s.pmsum / s.pread or 0, s.pdiv, s.tf, s.tchk, s.tok, s.tdiv, s.pop)
    .. string.format(" | guard credit=%d nohint=%d explained=%d", s.credit, s.nohint, s.explained)
    .. KC.GL.y2_mark())
  KC.GL.cs_st0()
end
-- раз в every_s секунд: подсказки destroyPlatoon, затем batch фракций по кругу и tbatch фракций для городов
function KC.GL.cs_step()
  local R, c = KC.GL.cs, KC.GL.cs_cfg()
  if R.off or c.enabled == false or not KC.S then return end
  local now = os.clock()
  if now - R.last < (c.every_s or 3) then return end
  R.last = now
  KC.GL.cs_fresh()
  if not R.ids then
    R.ids = {}; for fid in pairs(KC.S.F) do R.ids[#R.ids + 1] = fid end
    table.sort(R.ids); R.i, R.ti = 0, 0
  end
  local ids, n = R.ids, #R.ids
  if n == 0 then return end
  local k = 0
  for fid in pairs(R.hot) do
    R.hot[fid] = nil; R.nhot = R.nhot - 1
    KC.GL.cs_one(fid)
    k = k + 1; if k >= (c.hot or 4) then break end
  end
  for _ = 1, math.min(c.batch or 4, n) do R.i = R.i % n + 1; KC.GL.cs_one(ids[R.i]) end
  if c.towns ~= false then for _ = 1, math.min(c.tbatch or 1, n) do R.ti = R.ti % n + 1; KC.GL.cs_towns(ids[R.ti]) end end
  R.steps = R.steps + 1
  if R.steps == 5 or R.steps % (c.mark_every or 40) == 0 then KC.GL.cs_mark() end
end
function KC.GL.cs_tick()
  if KC.GL.h_live(KC.GL.cs, "off") then return end
  local ok, err = pcall(KC.GL.cs_step)
  if not ok then KC.GL.cs_fail(err) else KC.GL.h_ok("KMM_Conductor.coresync") end
end
function KC.GL.cs_on_destroy(self, platoon)   -- Faction::destroyPlatoon: отряд фракции уничтожен (гибель или уход - ?), прочесть фракцию раньше
  local R = KC.GL.cs
  if R.off or not KC.S then return end
  local ok, fid = pcall(function() local gd = self:getData() or self.data; return gd and gd.stringID end)
  if not (ok and fid and KC.S.F[fid]) then return end
  R.st.lost = R.st.lost + 1
  R.hit[fid] = true
  pcall(KC.GL.y2_note, fid, platoon)   -- Y2: запомнить шаблон отряда до подтверждения потери (ошибка не трогает подсказку)
  if not R.hot[fid] and R.nhot < 16 then R.hot[fid] = true; R.nhot = R.nhot + 1; R.st.hot = R.st.hot + 1 end
end
-- Y2 (2026-11-15): разгром отрядов обескровливает фракцию в ядре. Решение игрока: кого истощать (банды у базы, работорговцы, конкуренты).
--   Рычаг: Faction.diplomatMgr (FactionUniqueSquadManager) -> prosperityMgr:notifySquadDefeated(squadTemplate) (✓код, эффект ?).
--   Когда: только на ПОДТВЕРЖДЁННОЙ потере S2 - подсказка destroyPlatoon + падение численности сверх кредита своих спавнов в cs_one
--     (уход/выгрузка, скачок зоны, гибель собственного спавна, погашенная кредитом, - не зовут). В очередь идёт только Platoon.isDead == true
--     (Platoon.h, ✓код): destroyPlatoon срабатывает и на выгрузке временных отрядов при уходе игрока из зоны - такие не считаются.
--     Число вызовов за чтение не больше числа подтверждённо погибших платунов в очереди.
--   Крэш-сторож: RVA notifySquadDefeated в заголовке вне диапазона класса (?), вызов идёт через KC.L2.camp.probe_call("prosperity")
--     (state/probe_prosperity.lock на первом вызове сессии; lock при старте = прошлая сессия упала -> .off, Y2 выключен навсегда). Шаблон берётся из Platoon.squadTemplate
--     в колбэке (GameData шаблона - статические данные игры), очередь по фракции чистится на каждом чтении и при смене мира.
--   Двойной счёт: Y2 НЕ пишет S.F (ни strength, ни wealth). Сила уже уменьшается веткой S2 по getFactionSize; богатство модели меняется
--     только через чтение процветания CORESYNC в том же cs_one сразу после вызова (дельта getProsperityMultiplier, cap_wealth) - один раз.
--     Если с прошлого чтения процветание ядра уже упало само (ваниль, возможно, сама зовёт notify на гибель отряда - ?), вызов пропускается.
--   Лимиты: per_read за чтение фракции, per_fac_day на фракцию и per_day всего за игровой день. Проба: первый вызов - "probe ok/FAIL".
--     Ошибка вызова - Y2 выключен до перезапуска (сверка живёт). Нет эффекта за noeff_n измеренных вызовов - вызовы прекращаются.
-- Параметры (необязательно) P.materialize.prosperity = { enabled, per_read, per_fac_day, per_day, qmax, noeff_n, eps, vanilla_skip, eps_van }.
KC.GL.cs.ys = { calls = 0, mcalls = 0, eff = 0 }
function KC.GL.y2_st0()
  KC.GL.cs.ys.st = { call = 0, eff = 0, late = 0, skip = 0, cap = 0, van = 0, nomgr = 0, notpl = 0, unl = 0 }
end
KC.GL.y2_st0()
function KC.GL.y2_cfg()
  local m = KC.P and KC.P.materialize
  return (m and type(m.prosperity) == "table") and m.prosperity or {}
end
function KC.GL.y2_fail(what, err, forever)   -- forever: крэш-сторож (.off) — навсегда; иначе пауза реестра и повтор
  local ys = KC.GL.cs.ys
  if forever then
    KC.GL.h_forever(ys, "off", "KMM_Conductor.prosperity", tostring(what) .. ": " .. tostring(err), "crash")
    KC.GL.rs_log("PROSPERITY " .. what .. " (Y2 off, coresync goes on): " .. tostring(err))
    return
  end
  local p = KC.GL.h_down(ys, "off", "KMM_Conductor.prosperity", err)
  if p then KC.GL.rs_log("PROSPERITY " .. what .. " (Y2 paused, retry in " .. p .. " s, coresync goes on): " .. tostring(err))
  else KC.GL.rs_log("PROSPERITY " .. what .. " (Y2 off until restart, coresync goes on): " .. tostring(err)) end
end
function KC.GL.y2_n3(x) return x and string.format("%.4f", x) or "?" end
-- множитель процветания фракции и actualProsperity менеджера (nil - не прочлось)
function KC.GL.y2_pm(fo)
  local pm = KC.GL.cs_num(function() return fo:getProsperityMultiplier() end)
  local ap = KC.GL.cs_num(function() return fo.diplomatMgr.prosperityMgr.actualProsperity end)
  return pm, ap
end
function KC.GL.y2_drop(a0, a1, b0, b1, eps)
  return (a0 and a1 and a1 < a0 - eps) or (b0 and b1 and b1 < b0 - eps) or false
end
-- колбэк destroyPlatoon: шаблон отряда в очередь фракции (вызов ядра - только после подтверждения в cs_one)
function KC.GL.y2_note(fid, platoon)
  local ys, c = KC.GL.cs.ys, KC.GL.y2_cfg()
  if ys.off or c.enabled == false or not platoon then return end
  local okd, dead = pcall(function() return platoon.isDead end)
  if not (okd and dead == true) then ys.st.unl = ys.st.unl + 1; return end   -- выгрузка/уход, а не гибель - ядро не трогаем
  local tpl = platoon.squadTemplate
  if not tpl then ys.st.notpl = ys.st.notpl + 1; return end
  local oks, sid = pcall(function() return tpl.stringID end)
  local okl, ap = pcall(function() return platoon:getActivePlatoon() end)
  local R = KC.GL.cs
  R.y = R.y or { q = {}, fd = {}, chk = {}, day = -1, nd = 0 }
  local q = R.y.q[fid] or {}
  R.y.q[fid] = q
  if #q < (c.qmax or 4) then q[#q + 1] = { tpl = tpl, sid = tostring(oks and sid or "?"), ld = okl and ap ~= nil } end
end
function KC.GL.y2_do(fid, fo, conf)
  local R, ys, c = KC.GL.cs, KC.GL.cs.ys, KC.GL.y2_cfg()
  local W = R.y
  if not W then return end
  local eps = c.eps or 1e-6
  local ck = W.chk[fid]
  if ck then   -- отложенная проверка: эффект мог прийти не сразу, а через update ядра (?)
    W.chk[fid] = nil
    local pm, ap = KC.GL.y2_pm(fo)
    if not ck.hit and KC.GL.y2_drop(ck.pm, pm, ck.ap, ap, eps) then ys.eff = ys.eff + 1; ys.st.late = ys.st.late + 1 end
    if ys.eff == 0 and ys.mcalls >= (c.noeff_n or 6) then
      KC.GL.h_forever(ys, "off", "KMM_Conductor.prosperity", "no effect after " .. ys.mcalls .. " measured calls", "noeffect")
      KC.GL.rs_log(string.format("PROSPERITY no effect after %d measured calls (template outside faction list, copied manager or effect elsewhere - ?):"
        .. " calls stopped, wealth follows core prosperity via CORESYNC", ys.mcalls))
      return
    end
  end
  local q = W.q[fid]
  if not q then return end
  W.q[fid] = nil
  if c.enabled == false then return end
  if not conf then ys.st.skip = ys.st.skip + #q; return end
  local day = math.floor(math.max(KC.DAY or 0, (KC.S and KC.S.last_day) or 0))
  if W.day ~= day then W.day = day; W.nd = 0; W.fd = {} end
  local CA = KC.L2.camp
  if not CA.probe_ok("prosperity") then KC.GL.y2_fail("disabled forever (crash lock state/probe_prosperity.off)", "previous session crashed", true); return end
  local mgr = fo.diplomatMgr
  local pmg = mgr and mgr.prosperityMgr
  if not pmg then ys.st.nomgr = ys.st.nomgr + #q; return end
  local pm0, ap0 = KC.GL.y2_pm(fo)
  local last = R.pm[fid]
  if c.vanilla_skip ~= false and pm0 and last and pm0 < last - (c.eps_van or 0.005) then
    ys.st.van = ys.st.van + #q
    if not ys.van1 then
      ys.van1 = true
      KC.GL.rs_log(string.format("PROSPERITY vanilla already dropped: %s pm %.4f->%.4f since last read, notify skipped", fid, last, pm0))
    end
    return
  end
  local pmS, apS, n, hit = pm0, ap0, 0, false
  for _, e in ipairs(q) do
    local fd = W.fd[fid] or 0
    if n >= (c.per_read or 2) or fd >= (c.per_fac_day or 3) or W.nd >= (c.per_day or 12) then ys.st.cap = ys.st.cap + 1
    else
      local okc, err = CA.probe_call("prosperity", function() pmg:notifySquadDefeated(e.tpl) end)
      if not okc then KC.GL.y2_fail(ys.probed and "call failed" or "probe FAIL", err, not CA.probe_ok("prosperity")); ys.probed = true; return end
      n = n + 1; W.fd[fid] = fd + 1; W.nd = W.nd + 1
      ys.calls = ys.calls + 1; ys.st.call = ys.st.call + 1
      local pm1, ap1 = KC.GL.y2_pm(fo)
      if pm1 or ap1 then ys.mcalls = ys.mcalls + 1 end
      local h = KC.GL.y2_drop(pm0, pm1, ap0, ap1, eps)
      if h then hit = true; ys.eff = ys.eff + 1; ys.st.eff = ys.st.eff + 1 end
      local msg = string.format("%s tpl=%s loaded=%s pm %s->%s act %s->%s fac %d/%d day %d/%d", fid, e.sid, tostring(e.ld),
        KC.GL.y2_n3(pm0), KC.GL.y2_n3(pm1), KC.GL.y2_n3(ap0), KC.GL.y2_n3(ap1), fd + 1, c.per_fac_day or 3, W.nd, c.per_day or 12)
      if not ys.probed then ys.probed = true; KC.GL.rs_log("PROSPERITY probe ok: " .. msg) end
      KC.GL.rs_log("PROSPERITY defeated: " .. msg)
      pm0, ap0 = pm1 or pm0, ap1 or ap0
    end
  end
  if n > 0 then W.chk[fid] = { pm = pmS, ap = apS, hit = hit } end
end
function KC.GL.y2_apply(fid, fo, conf)
  if KC.GL.h_live(KC.GL.cs.ys, "off") then return end
  local ok, err = pcall(KC.GL.y2_do, fid, fo, conf)
  if not ok then KC.GL.y2_fail("failed", err) end
end
function KC.GL.y2_mark()
  local ok, s = pcall(function()
    local ys, t = KC.GL.cs.ys, KC.GL.cs.ys.st
    local r = string.format(" | defeat calls=%d eff=%d late=%d skip=%d cap=%d vanilla=%d nomgr=%d notpl=%d unload=%d%s",
      t.call, t.eff, t.late, t.skip, t.cap, t.van, t.nomgr, t.notpl, t.unl, ys.off and " off" or "")
    KC.GL.y2_st0()
    return r
  end)
  return ok and s or ""
end
function KC.write_relations()
  if not KC.P.materialize.relations_enabled then KC.S.dirty_rel = {}; return end
  if not KC.GL.h_live(KC.GL.rs, "off") then local ok, err = pcall(KC.GL.rs_step); if not ok then KC.GL.rs_fail(err) else KC.GL.h_ok("KMM_Conductor.relsync") end end
  if next(KC.S.dirty_rel) == nil then return end   -- PERF2: очередь пуста (почти всегда) - ни подсчёта, ни обхода
  local nd = 0; for _ in pairs(KC.S.dirty_rel) do nd = nd + 1; if nd > 2000 then KC.S.dirty_rel = {}; break end end   -- AUDIT-B: потолок очереди
  local n = 0
  for key in pairs(KC.S.dirty_rel) do
    local a, b = key:match("^(.-)|(.*)$")
    KC.S.dirty_rel[key] = nil
    local fa, fb = KC.faction_obj(a), KC.faction_obj(b)
    if fa and fb then
      local v = KC.GL.rs_write(a, b, fa, fb)
      if KC.L2.camp and KC.L2.camp.flags then pcall(KC.L2.camp.flags, a, b, fa, fb, v) end   -- NATIVE_MAP п.5: alliance/peaceTreaty/war + declareWar
    end
    n = n + 1
    if n >= 40 then break end
  end
end

function KC.xz(v)
  if not v then return nil end
  local ok, x, z = pcall(function() return v.x or v[1], v.z or v[3] end)
  if ok and x and z then return x, z end
end
function KC.player_chars()
  local ok, pcs = pcall(function() return getPlayerInterface():getAllPlayerCharacters() end)
  return ok and pcs or nil
end
function KC.hidden_from_player(ch)
  local m = KC.P.materialize
  if m.use_on_screen ~= false then
    local ok, on = pcall(function() return ch.isOnScreen end)
    if not ok or on then return false end
  end
  local okp, lx, lz = pcall(function() return KC.xz(ch:getPosition()) end)
  if not (okp and lx) then return false end
  local pcs = KC.player_chars()
  if not pcs then return false end
  local hidden = true
  pcall(function()
    for _, pc in pairs(pcs) do
      local okx, px, pz = pcall(function() return KC.xz(pc:getPosition()) end)
      if okx and px then
        local d = math.sqrt((px - lx) ^ 2 + (pz - lz) ^ 2)
        if d < (m.min_distance or 1500) then hidden = false; return end
        if m.use_line_of_sight ~= false and d < (m.los_max_distance or 4000) then
          local okl, los = pcall(function() return ch:lineOfSightCheck(pc) end)
          if not okl or (los and los ~= 0) then hidden = false; return end
        end
      end
    end
  end)
  return hidden
end

KC.appeared = {}
-- GL.self_chain: дирижёр сам заковывает (материализация/самотест): Character::setChainedMode — не плен игрока (Nemesis пропускает); поле, не local — лимит 200 локалов чанка
function KC.try_materialize(ch, sid)
  local id = KC.S.pending[sid]
  if not id then return end
  local t0 = KC.appeared[sid]
  if not t0 or os.clock() - t0 > (KC.P.materialize.window_seconds or 15) then return end   -- только момент загрузки зоны
  if not KC.hidden_from_player(ch) then return end
  local ev
  for i = #KC.S.events, 1, -1 do if KC.S.events[i].id == id then ev = KC.S.events[i]; break end end
  if not ev then KC.S.pending[sid] = nil; return end
  local okd, dead = pcall(function() return ch:isDead() end)
  local applied, how = false, ""
  if okd and dead then applied, how = true, "already dead"
  elseif ev.type == "leader_killed" then applied = pcall(function() ch:declareDead() end); how = "declareDead"
  else
    local otag = "?"   -- хозяин оков = пленитель (фракция-атакующий ev.a), не сам пленник; отказ движка -> прежний вариант (сам)
    KC.GL.self_chain = true
    applied = pcall(function() local oh; oh, otag = KC.GL.chain_owner(ch, ev.a); ch:setChainedMode(true, oh) end)
    if not applied and otag ~= "self" then otag = "self(retry)"; applied = pcall(function() ch:setChainedMode(true, ch:getHandle()) end) end
    KC.GL.self_chain = false; how = "setChainedMode owner=" .. otag
  end
  pcall(function() ch:uniqueStateUpdate() end)
  if not applied then error("materialize failed for " .. tostring(ev.leader_name) .. " (" .. how .. ")") end
  KC.S.pending[sid] = nil
  KC.S.resolved[sid] = ev.type
  ev.status = "applied"
  KC.emit({ type = "materialized", a = ev.a, b = ev.b, town_sid = ev.town_sid, town_name = ev.town_name, leader_sid = ev.leader_sid, leader_name = ev.leader_name,
         text = string.format("%s: what was rumoured at %s has come to pass (%s).", ev.leader_name, ev.town_name or "?", how) })
end

-- сдвиг богатства фракции (-1/0/+1) по отношению к стартовому (World, Runtime)
function KC.wealth_shift(fid)
  local f = KC.S.F[fid]
  if not f then return 0 end
  local r = f.wealth / f.wealth0
  if r < 0.5 then return -1 elseif r > 1.6 then return 1 end
  return 0
end

-- союзный отряд к игроку (обязательство договора): отряд через спавн Traces рядом с персонажем игрока, цель — он сам.
-- HEALTH (2026-11-15): ошибка -> реестр KMM_Gov (KMM_Conductor.dispatch): пауза 1/5/30 мин, обязательство остаётся в очереди;
-- наружу (KC.guarded дирижёра, «до перезапуска») ошибка уходит только без Gov.
function KC.try_dispatch()
  local key = "KMM_Conductor.dispatch"
  if not KC.GL.h_up(key) then return end
  local d0 = KC.S and KC.S.pending_dispatch
  local ok, err = pcall(KC.try_dispatch_impl)
  if ok then if d0 then KC.GL.h_ok(key) end; return end
  if KC.S and KC.S.pending_dispatch == nil then KC.S.pending_dispatch = d0 end
  local p = KC.GL.h_fail(key, err)
  if type(p) ~= "number" then error(err, 0) end
  pcall(KC.guard_log, "dispatch failed, retry in " .. p .. " s: " .. tostring(err))
end
function KC.try_dispatch_impl()
  local d = KC.S.pending_dispatch
  if not (d and KC.P.materialize.dispatch_enabled) then return end
  if KC.S.dispatch_day ~= math.floor(KC.DAY) then KC.S.dispatch_day, KC.S.dispatch_today = math.floor(KC.DAY), 0 end
  if KC.S.dispatch_today >= KC.P.materialize.dispatch_max_per_day then return end
  KC.S.pending_dispatch = nil
  local pcs = KC.player_chars()
  local pc
  if pcs then for _, c in pairs(pcs) do pc = c; break end end
  local fobj = KC.faction_obj(d.ally)
  if not (pc and fobj) then return end
  -- вне видимости: до каждого персонажа игрока >= unseen_min (3500), до ближайшего <= unseen_max (6000); нет точки - отложить на потом
  local mn, mx = KC.P.materialize.unseen_min or 3500, KC.P.materialize.unseen_max or 6000
  local pts = {}
  pcall(function() for _, c in pairs(pcs) do local cx, cz = KC.xz(c:getPosition()); if cx then pts[#pts + 1] = { cx, cz } end end end)
  local px0, pz0 = KC.xz(pc:getPosition())
  local sx, sz
  for i = 1, 8 do
    local a0, r0 = math.random() * 2 * math.pi, mn + 150 + math.random() * math.max(1, mx - mn - 300)
    local anc = pts[((i - 1) % math.max(1, #pts)) + 1] or { px0, pz0 }
    local x1, z1 = anc[1] + r0 * math.cos(a0), anc[2] + r0 * math.sin(a0)
    local good, near = #pts > 0, nil
    for _, q in ipairs(pts) do
      local d = math.sqrt((x1 - q[1]) ^ 2 + (z1 - q[2]) ^ 2)
      if d < mn then good = false end
      if not near or d < near then near = d end
    end
    if good and near <= mx then sx, sz = x1, z1; break end
  end
  if not sx then KC.S.pending_dispatch = d; KC.S.dispatch_unseen_wait = (KC.S.dispatch_unseen_wait or 0) + 1; return end
  -- 2026-11-15 игра: «bad argument #6 to createRandomSquad» — шаблон отряда nil не принимается. Отряд союзника — через общий спавн
  -- Traces (шаблон по тиру фракции, точка вне видимости, лимиты); без Traces — прежний путь не пробуем, день не тратим.
  local T = rawget(_G, "KMM_Traces")
  if not (T and T.request) then return end
  local ok, err = pcall(function()
    local acc = T.request({ tag = "ally_dispatch", fid = d.ally, n = 1, size = KC.P.materialize.dispatch_squad_size, target = "player",
                            from_x = sx, from_z = sz })
    if not acc then error("traces request rejected (limits)") end
  end)
  if not ok then KC.S.pending_dispatch = d; return end   -- лимиты Traces: повтор позже, не ошибка
  KC.S.dispatch_today = KC.S.dispatch_today + 1
  if ok then KC.S.stats.dispatch = KC.S.stats.dispatch + 1 end
  pcall(KC.emit, { type = "ally_dispatch", a = d.ally, b = KC.CFG.player_faction, status = ok and "applied" or "failed",   -- squad already sent: a chronicle error must not resend it
         text = string.format("%s sent fighters toward your people (%s).", tostring(KC.name(d.ally)), tostring(d.why)) })
end

KC.last_scan = 0
function KC.scan_loaded()
  -- PERF2: общий снимок KMM_Gov (фракция персонажа уже в записи); getGameData читаем, только если есть что материализовать;
  -- без Gov / при ошибке снимка - прежний обход. Порядок обхода и условия те же.
  local g = rawget(_G, "KMM_Gov")
  local snap
  if g and g.snapshot and KC.P.scan_snapshot ~= false then
    local oks, sn = pcall(g.snapshot, KC.P.scan_snap_ttl or 4)   -- 4 с как у Traces: меньший ttl одного модуля учащает общую перестройку снимка
    if oks and type(sn) == "table" and sn.list then snap = sn end
  end
  if snap then
    local now, seen = os.clock(), {}
    if next(KC.S.pending) == nil then
      for sid in pairs(KC.appeared) do if not seen[sid] then KC.appeared[sid] = nil end end
      return
    end
    pcall(function()
      for _, r in ipairs(snap.list) do
        local ch = r.ch
        local okg, sid = pcall(function() local gd = ch:getGameData(); return gd and gd.stringID end)
        if okg and sid and KC.S.pending[sid] then
          seen[sid] = true
          if not KC.appeared[sid] then KC.appeared[sid] = now end
          KC.try_materialize(ch, sid)
        end
      end
    end)
    for sid in pairs(KC.appeared) do if not seen[sid] then KC.appeared[sid] = nil end end
    return
  end
  local ok, set = pcall(function() return getGameWorld():getCharacterUpdateList() end)
  if not (ok and set) then return end
  local now, seen = os.clock(), {}
  pcall(function()
    for ch in pairs(set) do
      local okg, sid = pcall(function() local gd = ch:getGameData(); return gd and gd.stringID end)
      if okg and sid and KC.S.pending[sid] then
        seen[sid] = true
        if not KC.appeared[sid] then KC.appeared[sid] = now end
        KC.try_materialize(ch, sid)
      end
    end
  end)
  for sid in pairs(KC.appeared) do if not seen[sid] then KC.appeared[sid] = nil end end
end
end
if KC._BOOT then KC._BOOT() end
