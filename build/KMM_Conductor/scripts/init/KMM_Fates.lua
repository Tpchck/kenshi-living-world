-- KMM_Fates — судьбы героев мира (2026-11-13, «Живой мир»).
-- Дирижёр ведёт 20-40 вымышленных «героев» (наёмник, главарь банды, капитан армии, охотник за реликтами, торговец): имя, фракция, роль, тир T0..T3,
-- место (город/лагерь), репутация. Раз в игровой день часть героев делает шаг судьбы по событиям дирижёра (победы фракции) и случайности:
-- повышение тира, свой лагерь, переход во фракцию, ранение, плен (рабство), гибель (заменяется новым героем). Каждое изменение — C.emit (хроника/слухи).
-- Видимое: игрок рядом с местом героя -> KMM_Traces.request: отряд фракции тира героя идёт в город героя; лидер отряда переименовывается в имя героя
-- (Character:setName, ActivePlatoon:setName из справочника). Гибель лидера (isDead / имя лидера сменилось) -> судьба героя + хроника.
-- Состояние: S.ext.fates (в сейве дирижёра, ленивое создание, ~10 КБ). Ничего не делает на старте; всё под pcall, при ошибке модуль выключается до перезапуска.
-- S6 (2026-11-15): связки с ядром и модулями. Тяжкие дела (шина KMM_Deeds: killed/executed/captured) отряда героя против фракции
-- с законом -> награда героя у правоохранителей жертвы (h.bb/h.b, механика KMM_Outlaws: add_bounty/lawful/law), на живом лидере —
-- сразу родная награда ядра (unfairAddToBounty под крэш-сторожем Outlaws probe_call), иначе — при выходе отряда (Outlaws native_bounty).
-- Награда тает и привлекает охотников (гибель/тюрьма). Повторная встреча с игроком -> родная долгая память лидера (KMM_Nemesis remember
-- -> KMM_Native.remember_lt). Жив ли фракция и враждебность к игроку читаются из ядра (C.alive, FactionRelations) с фолбэком.
-- Своё: h.bb/h.b (персонаж ядра существует только пока отряд у игрока), h.met (лидер каждый раз новый персонаж — память ядра не переживает спавн).
-- Лог: C:/KenshiModMap/logs/fates.log. Kenshi Lua 5.1; всё — поля таблицы M (лимит локалей).
local TAG = "[KMM_Fates] "
local M = { off = false, live = {}, wins = {}, subbed = false, last = -1000, pend = nil, nlog = 0, DAY_EMITS = 0 }

local DEF = {
  enabled = true,
  count = 28,            -- целевое число героев (20..40)
  tick_s = 8,            -- реальных секунд между тиками модуля
  step_p = 0.30,         -- доля героев, делающих шаг судьбы в игровой день
  max_catchup = 3,       -- не больше дней за один тик (загрузка сейва)
  max_emits_day = 5,     -- не больше событий-слухов за игровой день
  death_p = { 0.05, 0.04, 0.03, 0.02 },   -- гибель за шаг по тиру T0..T3
  capture_p = 0.03, wound_p = 0.12,
  vis_r = 25000,         -- игрок ближе этого к месту героя -> отряд героя может появиться
  cd_h = 48,             -- игровых часов между появлениями одного героя
  spawn_p = 0.5,         -- шанс появления на проверке (раз в tick_s), когда все условия выполнены
  max_live = 3,          -- одновременно наблюдаемых отрядов героев
  pend_s = 120,          -- сек ожидания спавна заявки
  watch_s = 1800,        -- сек наблюдения за отрядом героя
  log_max = 400,
  deed_bounty = true,    -- S6: дела героя -> награда
  deed_r = 30000,        -- дело приписывается герою фракции, чей дом ближе этого к месту дела (или живому отряду у игрока)
  deed_day = 2,          -- дел на героя в игровой день
  deeds_day = 6,         -- дел всех героев в игровой день
  deed_cap = 50000,      -- потолок награды героя
  bounty_decay = 0.01,   -- награда тает за день
  justice_per = 1 / 400000, justice_max = 0.04,   -- охотники: шанс за шаг судьбы от награды
  hostile_rel = -30,     -- отношение фракции героя к игроку в ядре не выше -> главарь идёт на игрока
  memory = true, mem_day = 4,   -- родная память лидера при повторной встрече; не больше записей в игровой день
}
local ROLES = { "mercenary", "bandit_chief", "army_captain", "relic_hunter", "trader" }
local ROLE_TITLE = { mercenary = "mercenary captain", bandit_chief = "bandit chief", army_captain = "army captain",
                     relic_hunter = "relic hunter", trader = "caravan master" }
local ROLE_W = { mercenary = 3, bandit_chief = 2, army_captain = 2, relic_hunter = 2, trader = 2 }
local SYL_A = { "Ha", "Ka", "Ro", "Va", "Tha", "Mo", "Ze", "Bru", "Sha", "Dro", "Ner", "Kel", "Jo", "Ur", "Ska", "Gru", "Ya", "Lo", "Ta", "Fen" }
local SYL_B = { "r", "rr", "n", "k", "l", "d", "m", "x", "th", "g" }
local SYL_C = { "a", "o", "u", "ek", "ar", "en", "ak", "ra", "is", "on" }
local EPI = { "Scar", "Ironhand", "Blackwater", "Deadeye", "Gutter", "Rustblade", "Longstride", "Ashfang", "Bonesaw", "Quickknife",
              "Stormhide", "Redsand", "Hollow", "Dustwalker", "Coldiron", "Skinner", "Burnt", "Oldmoon", "Halfhand", "Greycloak" }
local BANDITISH = { "bandit", "raider", "thie", "outlaw", "gang", "skin", "hungry", "rust", "cannibal", "pirate" }

function M.log(msg)
  if M.nlog >= DEF.log_max then return end
  M.nlog = M.nlog + 1
  local ok, f = pcall(io.open, "C:/KenshiModMap/logs/fates.log", "a")
  if ok and f then f:write(os.date("%Y-%m-%d %H:%M:%S"), " ", tostring(msg), "\n"); f:close() end
  pcall(function() if KenshiLua and KenshiLua.log then KenshiLua.log(TAG .. tostring(msg)) end end)
end
-- HEALTH (2026-11-15): отказы идут в реестр ядра KMM_Gov (ключи KMM_Fates.<механика>): пауза 1/5/30 мин и повтор вместо «до перезапуска».
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
function M.fail(where, err)
  local p = down(M, "off", "KMM_Fates.module", err)
  M.log((p and ("failed, retry in " .. p .. " s") or "disabled until restart") .. " in " .. where .. ": " .. tostring(err))
end
function M.cfg()
  local c = DEF
  local ok, p = pcall(function() return KMM_Conductor.cfg().params.fates end)
  if ok and type(p) == "table" then
    c = {}
    for k, v in pairs(DEF) do c[k] = v end
    for k, v in pairs(p) do c[k] = v end
  end
  return c
end
function M.rnd(a, b) return math.random(a, b) end
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

-- состояние -----------------------------------------------------------------------------------------------------------
function M.F(S)
  S.ext = S.ext or {}
  local F = S.ext.fates
  if type(F) ~= "table" then F = { v = 1, nid = 1, H = {}, day = nil }; S.ext.fates = F end
  F.H = F.H or {}; F.nid = F.nid or 1
  return F
end
function M.hero_list(F)
  local out = {}
  for k, h in pairs(F.H) do out[#out + 1] = h end
  table.sort(out, function(a, b) return a.i < b.i end)
  return out
end

-- мир: города, фракции -------------------------------------------------------------------------------------------------
function M.world(C, S, day)
  local W = M.W
  if W and W.day == day and W.S == S then return W end
  W = { day = day, S = S, towns = {}, by = {}, own = {}, cand = {} }
  for _, t in ipairs(C.towns() or {}) do
    if t.x and t.z then
      W.towns[#W.towns + 1] = t; W.by[t.sid] = t
      if t.owner then W.own[t.owner] = W.own[t.owner] or {}; table.insert(W.own[t.owner], t) end
    end
  end
  local tr = C.read_json("traces.json", "C:/KenshiModMap/build/KMM_Conductor/traces.json")
  W.tr = (tr and tr.factions) or {}
  local pf = C.cfg().player_faction
  for fid, f in pairs(S.F or {}) do
    local e = W.tr[fid]
    if f.alive and not f.player and not f.sleeper and fid ~= pf and e and e.tiers and next(e.tiers) and (W.own[fid] or C.fpos(fid)) then
      W.cand[#W.cand + 1] = fid
    end
  end
  table.sort(W.cand)
  M.W = W
  return W
end
function M.tname(W, h)
  local t = h.s and W.by[h.s]
  return t and t.name or "the wastes"
end
function M.faction_pick(C, W, role, not_fid)
  local best, tot = {}, 0
  for _, fid in ipairs(W.cand) do
    if fid ~= not_fid then
      local nm = string.lower(tostring(C.name(fid) or ""))
      local w = 1
      local owns = W.own[fid] ~= nil
      if role == "bandit_chief" then
        local b = false
        for _, k in ipairs(BANDITISH) do if nm:find(k, 1, true) then b = true; break end end
        w = b and 5 or (owns and 0.3 or 2)
      elseif role == "army_captain" or role == "trader" then
        w = owns and 4 or 0.3
      end
      best[#best + 1] = { fid, w }; tot = tot + w
    end
  end
  if tot <= 0 then return nil end
  local r = math.random() * tot
  for _, p in ipairs(best) do r = r - p[2]; if r <= 0 then return p[1] end end
  return best[#best][1]
end
function M.place(C, W, h)   -- город героя: свой город фракции, иначе ближайший к позиции фракции
  local own = W.own[h.f]
  local t
  if own and #own > 0 then t = M.pick(own)
  else
    local fx, fz = C.fpos(h.f)
    local bd
    if fx then for _, x in ipairs(W.towns) do local d = (x.x - fx) ^ 2 + (x.z - fz) ^ 2; if not bd or d < bd then bd, t = d, x end end end
  end
  if t then h.s, h.x, h.z = t.sid, t.x + math.random(-400, 400), t.z + math.random(-400, 400); h.camp = nil
  else local fx, fz = C.fpos(h.f); h.s, h.x, h.z = nil, fx, fz end
end
function M.new_name(F)
  for _ = 1, 30 do
    local nm = M.pick(SYL_A) .. M.pick(SYL_B) .. M.pick(SYL_C) .. " " .. M.pick(EPI)
    local used = false
    for _, h in pairs(F.H) do if h.n == nm then used = true; break end end
    if not used then return nm end
  end
  return M.pick(SYL_A) .. M.pick(SYL_C) .. " " .. M.pick(EPI) .. F.nid
end
function M.pick_role()
  local tot = 0
  for _, r in ipairs(ROLES) do tot = tot + ROLE_W[r] end
  local x = math.random() * tot
  for _, r in ipairs(ROLES) do x = x - ROLE_W[r]; if x <= 0 then return r end end
  return "mercenary"
end
function M.new_hero(C, F, W, day, tier)
  local role = M.pick_role()
  local fid = M.faction_pick(C, W, role)
  if not fid then return nil end
  if not tier then
    local r = math.random()
    tier = r < 0.6 and 0 or (r < 0.9 and 1 or (r < 0.98 and 2 or 3))
  end
  local h = { i = F.nid, n = M.new_name(F), f = fid, r = role, t = tier, rep = math.random(-10, 20), w = 0, st = "a", since = day, sp = -1000 }
  F.nid = F.nid + 1
  F.H["h" .. h.i] = h
  M.place(C, W, h)
  if role == "bandit_chief" and tier >= 2 then M.camp(h, W) end
  return h
end
function M.camp(h, W)
  local t = h.s and W.by[h.s]
  if not t then return false end
  local a = math.random() * 6.2832
  local d = math.random(4000, 8000)
  h.x, h.z, h.camp = t.x + math.cos(a) * d, t.z + math.sin(a) * d, true
  return true
end

-- события ---------------------------------------------------------------------------------------------------------------
function M.emit(C, W, h, typ, text, extra)
  if M.DAY_EMITS >= (M.cfg().max_emits_day or 5) then return end
  M.DAY_EMITS = M.DAY_EMITS + 1
  local ev = { type = typ, a = h.f, town_sid = h.s, town_name = M.tname(W, h), leader_name = h.n, status = h.st, text = text }
  if extra then for k, v in pairs(extra) do ev[k] = v end end
  pcall(C.emit, ev)
  M.log(string.format("[day %s] %s: %s", tostring(M.W and M.W.day), typ, text))
end
function M.sub(C)
  if M.subbed then return end
  M.subbed = true
  pcall(function()
    C.subscribe("*", function(ev)
      local t = ev.type
      if (t == "town_captured" or t == "raid" or t == "joint_raid" or t == "military") and ev.a then
        M.wins[ev.a] = math.min(5, (M.wins[ev.a] or 0) + 1)
      elseif t == "deed" then M.on_deed_g(ev) end
    end)
  end)
end

-- S6: ядро и модули -----------------------------------------------------------------------------------------------------
function M.stat(k) M.stats[k] = (M.stats[k] or 0) + 1 end
function M.OM()   -- механика награды KMM_Outlaws (add_bounty, lawful, probe_call, native_bounty): переиспользуем, не дублируем
  local O = rawget(_G, "KMM_Outlaws")
  local OM = type(O) == "table" and O._M
  if type(OM) == "table" and OM.add_bounty and OM.probe_call and OM.DEED_B and not OM.off then return OM end
  if not M.om_warn then M.om_warn = true; M.log("bounty link idle: KMM_Outlaws mechanics missing or disabled") end
  return nil
end
function M.alive(C, S, fid)   -- ядро дирижёра (C.alive экспортируется всегда)
  local ok, v = pcall(C.alive, fid)
  return ok and v == true
end
function M.prel(C, fid)   -- отношение фракции героя к игроку: FactionRelations ядра, фолбэк — модель дирижёра (C.rel), иначе nil
  local pf = C.cfg().player_faction
  if not pf then return nil end
  local ok, v = pcall(function()
    local fm = getGameWorld().factionMgr
    return fm:getFactionByStringID(fid).relations:getFactionRelation(fm:getFactionByStringID(pf))
  end)
  if ok and type(v) == "number" and v == v then return v, "core" end
  if C.rel then local ok2, r = pcall(C.rel, fid, pf); if ok2 and type(r) == "number" then return r, "model" end end
  return nil
end
function M.hostile(C, cfg, h)   -- главарь идёт на игрока: фракция враждебна в ядре; без ядра — прежнее правило по славе
  if h.r ~= "bandit_chief" then return false end
  local r = M.prel(C, h.f)
  if r ~= nil then return r <= (cfg.hostile_rel or -30) end
  return h.rep < 20
end
function M.deed_who(cfg, F, ev)   -- чьё дело: живой названный отряд фракции у игрока, иначе ближайший к месту герой фракции
  local best, bd
  for _, h in ipairs(M.hero_list(F)) do
    if h.f == ev.a and h.st == "a" then
      local lv = M.live["h" .. h.i]
      if lv and lv.named then return h, lv end
      if ev.x and ev.z and h.x and h.z then
        local d = (h.x - ev.x) ^ 2 + (h.z - ev.z) ^ 2
        if d <= cfg.deed_r * cfg.deed_r and (not bd or d < bd) then best, bd = h, d end
      end
    end
  end
  return best, nil
end
function M.outlaw_owns(C, S, ev)   -- одно дело — одна награда: то же правило приписывания, что у KMM_Outlaws (deed_who: живая банда
  -- или ближайший разыскиваемый фракции в deed_r); если Outlaws берёт дело себе — Fates его не трогает
  local O = rawget(_G, "KMM_Outlaws")
  local OM = type(O) == "table" and O._M
  if type(OM) ~= "table" or OM.off or OM.deed_off or not (OM.deed_who and OM.O and OM.cfg) then return false end
  local ok, r = pcall(function()
    local oc = OM.cfg()
    if oc.deed_bounty == false or not (OM.DEED_B and OM.DEED_B[ev.kind]) then return false end
    if type(S.ext.outlaws) ~= "table" or not OM.data(C) then return false end
    return OM.deed_who(OM.O(S), oc, ev) ~= nil
  end)
  return ok and r == true
end
function M.lawful(C, OM, W, fid)   -- публичный KMM_Outlaws.lawful; без данных Outlaws — города фракции / своя полиция
  local O = rawget(_G, "KMM_Outlaws")
  if type(O) == "table" and O.lawful then
    local ok, v = pcall(O.lawful, fid)
    if ok and v == true then return true end
    local okd, D = pcall(OM.data, C)
    if ok and okd and D then return false end
  end
  return W.own[fid] ~= nil or (OM.law and OM.law(fid) ~= fid)
end
function M.sync_S(S)   -- другой сейв/мир: указатели Platoon прошлого мира недействительны
  if M.live_S ~= S then
    if M.live_S ~= nil and next(M.live) then M.log("world changed: live squads dropped") end
    M.live_S = S; M.live = {}; M.pend = nil; M.W = nil
  end
end
function M.bounty_add(OM, h, fid, amt)   -- публичный KMM_Outlaws.add_bounty (M.OM() уже проверил модуль)
  return rawget(_G, "KMM_Outlaws").add_bounty(h, fid, amt)
end
function M.on_deed(ev)
  if live(M, "off") or live(M, "deed_off") or type(ev) ~= "table" then return end
  local cfg = M.cfg()
  if cfg.deed_bounty == false or ev.by_player or ev.to_player or not (ev.a and ev.b) or ev.a == ev.b then return end
  local C = rawget(_G, "KMM_Conductor")
  local S = C and C.state and C.state()
  if type(S) ~= "table" or type(S.ext) ~= "table" or type(S.ext.fates) ~= "table" then return end
  local OM = M.OM()
  if not (OM and OM.DEED_B[ev.kind]) then return end
  M.sync_S(S)
  if M.outlaw_owns(C, S, ev) then M.stat("deed_outlaw"); return end
  local F = M.F(S)
  local h, lv = M.deed_who(cfg, F, ev)
  if not h then return end
  local day = M.today(C)
  local W = M.world(C, S, F.day or day)
  if not M.lawful(C, OM, W, ev.b) then M.stat("deed_lawless"); return end
  if M.deed_d ~= day then M.deed_d = day; M.deed_n = 0 end
  if type(h.dd) ~= "table" or h.dd.d ~= day then h.dd = { d = day, n = 0, k = {} } end
  local dk = tostring(ev.b) .. "|" .. ev.kind
  if h.dd.k[dk] then M.stat("deed_dup"); return end
  h.b = h.b or 0; h.bb = h.bb or {}
  if h.dd.n >= cfg.deed_day or M.deed_n >= cfg.deeds_day or h.b >= cfg.deed_cap then M.stat("deed_capped"); return end
  h.dd.k[dk] = true; h.dd.n = h.dd.n + 1; M.deed_n = M.deed_n + 1
  local amt = math.floor(OM.DEED_B[ev.kind] * (h.t + 1) * (1 + 0.25 * (math.min(math.max(tonumber(ev.n) or 1, 1), 5) - 1)))
  amt = math.max(0, math.min(amt, cfg.deed_cap - h.b))
  local b0 = h.b
  local lf = M.bounty_add(OM, h, ev.b, amt)
  local inc = h.b - b0
  h.rep = math.max(-100, h.rep - 3)
  M.stat("deed")
  local nat = "later"
  if lv and inc >= 1 then
    local ocfg = OM.cfg and OM.cfg() or {}
    local okl, leader = pcall(function() return lv.pl:getSquadLeader() end)
    local fo
    pcall(function() fo = getGameWorld().factionMgr:getFactionByStringID(lf) end)
    if ocfg.native_bounty == false then nat = "off"
    elseif okl and leader and fo then
      local e0 = OM.engine_total(leader)
      local okc = OM.probe_call("bounty_add", function() leader.crimes:unfairAddToBounty(fo, math.floor(inc)) end)
      local e1 = OM.engine_total(leader)
      nat = OM.verdict(okc and 1 or 0, e0, e1) .. " " .. tostring(e0) .. "->" .. tostring(e1)
    else nat = "FAIL no leader/faction" end
  end
  M.log(string.format("deed bounty +%d on %s (%s %s, law %s): native %s", inc, h.n, ev.kind, tostring(ev.b), tostring(lf), nat))
  local vn = tostring(C.name(ev.b) or ev.b)
  local tmpl = (OM.DEED_T and OM.DEED_T[ev.kind]) or "wronged %s"
  M.emit(C, W, h, "fate_deed", string.format("Witnesses%s name %s, %s of %s: %s. The law wants %d cats for him.",
         ev.town_name and (" near " .. ev.town_name) or "", h.n, ROLE_TITLE[h.r], tostring(C.name(h.f)), string.format(tmpl, vn), h.b),
         { b = ev.b, deed = ev.kind, bounty = h.b, status = "wanted", town_sid = ev.town_sid or h.s, town_name = ev.town_name or M.tname(W, h) })
end
function M.on_deed_g(ev)   -- ошибка выключает только связку дел, не модуль и не подписку побед
  if type(ev) == "table" and ev.by_player and ev.witnessed == false then M.stat("deed_unwitnessed"); return end   -- Y1: дело игрока без свидетелей - мир о нём не знает
  local ok, err = pcall(M.on_deed, ev)
  if not ok then M.log("deed bounty " .. why_p(down(M, "deed_off", "KMM_Fates.deed_bounty", err)) .. ": " .. tostring(err)) end
end
function M.bounty_day(cfg, h)   -- награда тает (как у Outlaws «на дне»)
  if not (h.b and h.b > 0 and h.bb) then return end
  local tot = 0
  for f, v in pairs(h.bb) do
    v = math.floor(v * (1 - (cfg.bounty_decay or 0.01)))
    if v < 100 then h.bb[f] = nil else h.bb[f] = v; tot = tot + v end
  end
  h.b = tot
  if tot <= 0 then h.b, h.bb, h.lf = nil, nil, nil end
end
function M.justice(C, F, W, cfg, h, day)   -- охотники за головами ядра идут на награду: гибель или тюрьма (награда закрыта)
  if not (h.b and h.b > 0) then return false end
  if math.random() >= math.min(cfg.justice_max, h.b * cfg.justice_per) then return false end
  M.stat("justice")
  if math.random() < 0.5 then M.die(C, F, W, h, day, "was hunted down by bounty hunters"); return true end
  h.st = "e"; h.un = day + math.random(15, 40)
  M.emit(C, W, h, "fate_jailed", string.format("%s was taken alive by bounty hunters near %s; the %d-cat bounty is paid.", h.n, M.tname(W, h), h.b),
         { status = "jailed", bounty = h.b })
  M.log(string.format("justice: %s jailed, bounty %d closed", h.n, h.b))
  h.b, h.bb, h.lf = nil, nil, nil
  return true
end
function M.on_meet(C, cfg, h, lv)   -- отряд героя у игрока: родная награда ядра + родная память лидера при повторной встрече
  local okl, leader = pcall(function() return lv.pl:getSquadLeader() end)
  if not (okl and leader) then return end
  if h.b and h.b > 0 and h.bb then
    local OM = M.OM()
    local O = rawget(_G, "KMM_Outlaws")
    local nb = (type(O) == "table" and O.native_bounty) or (OM and OM.native_bounty)
    if OM and nb then
      local e0 = OM.engine_total and OM.engine_total(leader)
      local ok, r = pcall(nb, h, leader)
      local e1 = OM.engine_total and OM.engine_total(leader)
      M.log(string.format("native bounty %s on %s: ours %d, engine %s -> %s", (ok and r) and OM.verdict(1, e0, e1) or "FAIL", h.n, h.b, tostring(e0), tostring(e1)))
    end
  end
  h.met = (h.met or 0) + 1
  if cfg.memory == false or h.met < 2 then return end
  local day = M.today(C)
  if M.mem_d ~= day then M.mem_d = day; M.mem_n = 0 end
  if M.mem_n >= (cfg.mem_day or 4) then M.stat("mem_capped"); return end
  local NM = rawget(_G, "KMM_Nemesis")
  local rem = type(NM) == "table" and NM.remember   -- публичный экспорт KMM_Nemesis
  local tag = lv.hostile and "LT_MY_INTRUDER" or "LT_FRIENDLY_AQUAINTANCE"   -- враг помнит чужака, остальные — знакомого
  if type(rem) ~= "function" then
    if not M.mem_warn then M.mem_warn = true; M.log("memory link idle: KMM_Nemesis remember missing") end
    return
  end
  M.mem_n = M.mem_n + 1
  local ok, err = pcall(rem, leader, tag)
  M.stat("memory")
  M.log(string.format("memory %s for %s (meeting #%d): %s", tag, h.n, h.met, ok and "sent" or ("error " .. tostring(err))))
end

-- шаг судьбы -------------------------------------------------------------------------------------------------------------
function M.remove(F, h) F.H["h" .. h.i] = nil; M.live["h" .. h.i] = nil end
function M.die(C, F, W, h, day, how)
  local fn = C.name(h.f)
  local bt = (h.b and h.b > 0) and string.format(" The %d-cat bounty is closed.", h.b) or ""
  M.emit(C, W, h, "fate_death", string.format("%s, %s of %s, %s near %s.%s", h.n, ROLE_TITLE[h.r], fn, how, M.tname(W, h), bt),
         { status = "dead", bounty = h.b })
  M.remove(F, h)
  M.new_hero(C, F, W, day, math.random() < 0.85 and 0 or 1)   -- замена: новое имя поднимается на место павшего
  M.stats.deaths = M.stats.deaths + 1
end
function M.promote(C, F, W, h)
  h.t = h.t + 1; h.w = 0; h.rep = math.min(100, h.rep + 10)
  M.emit(C, W, h, "fate_rise", string.format("%s, %s of %s, has risen in rank after victories near %s.", h.n, ROLE_TITLE[h.r], C.name(h.f), M.tname(W, h)),
         { status = "rise" })
  M.stats.rise = M.stats.rise + 1
end
function M.defect(C, F, W, h, why)
  local nf = M.faction_pick(C, W, h.r, h.f)
  if not nf then return false end
  local old = h.f
  h.f = nf; h.camp = nil; h.rep = h.rep - 5
  M.place(C, W, h)
  M.emit(C, W, h, "fate_defect", string.format("%s, once of %s, now serves %s.", h.n, C.name(old), C.name(nf)), { b = old, status = why or "defect" })
  M.stats.defect = M.stats.defect + 1
  return true
end
function M.fate(C, F, W, cfg, h, day)
  local S = C.state()
  if not M.alive(C, S, h.f) then M.defect(C, F, W, h, "fall"); return end
  if M.justice(C, F, W, cfg, h, day) then return end
  local bonus = M.wins[h.f] or 0
  if bonus > 0 and math.random() < 0.5 then M.wins[h.f] = bonus - 1; h.w = h.w + 1 end   -- победа фракции по событиям дирижёра
  local r = math.random()
  local pd = (cfg.death_p[h.t + 1] or 0.03)
  if r < pd then M.die(C, F, W, h, day, "was killed in battle"); return end
  if r < pd + cfg.capture_p then
    h.st = "e"; h.un = day + math.random(15, 40)
    M.emit(C, W, h, "fate_enslaved", string.format("%s was taken by slavers near %s.", h.n, M.tname(W, h)), { status = "enslaved" })
    M.stats.slave = M.stats.slave + 1
    return
  end
  if r < pd + cfg.capture_p + cfg.wound_p then
    h.st = "w"; h.un = day + math.random(3, 8)
    if h.t >= 1 then M.emit(C, W, h, "fate_wounded", string.format("%s was badly wounded near %s.", h.n, M.tname(W, h)), { status = "wounded" }) end
    M.stats.wound = M.stats.wound + 1
    return
  end
  h.w = h.w + 1; h.rep = math.min(100, h.rep + 2)
  if h.w >= 3 + 2 * h.t and h.t < 3 then M.promote(C, F, W, h); return end
  local q = math.random()
  if h.r == "bandit_chief" and h.t >= 1 and not h.camp and h.w >= 2 and q < 0.3 then
    if M.camp(h, W) then
      M.emit(C, W, h, "fate_gang", string.format("%s has taken command of a gang near %s.", h.n, M.tname(W, h)), { status = "gang" })
      M.stats.camp = M.stats.camp + 1
    end
  elseif h.r == "mercenary" and q < 0.08 then M.defect(C, F, W, h, "hire")
  elseif h.r == "relic_hunter" and q < 0.06 then
    h.rep = math.min(100, h.rep + 8)
    M.emit(C, W, h, "fate_relic", string.format("%s returned from the ruins near %s with a relic.", h.n, M.tname(W, h)), { status = "relic" })
  elseif h.r == "trader" and q < 0.06 then
    h.rep = math.min(100, h.rep + 3)
    M.emit(C, W, h, "fate_trade", string.format("%s the caravan master grew rich on the roads near %s.", h.n, M.tname(W, h)), { status = "trade" })
  elseif q > 0.9 and not h.camp then M.place(C, W, h) end   -- перебрался в другой город (тихо)
end
function M.day_step(C, F, day)
  local S = C.state()
  local cfg = M.cfg()
  local W = M.world(C, S, day)
  M.DAY_EMITS = 0
  local list = M.hero_list(F)
  for _, h in ipairs(list) do
    if F.H["h" .. h.i] then
      M.bounty_day(cfg, h)
      if h.st == "w" and day >= (h.un or 0) then h.st = "a"; h.un = nil
      elseif h.st == "e" and day >= (h.un or 0) then
        h.st = "a"; h.un = nil; h.rep = math.min(100, h.rep + 5)
        M.emit(C, W, h, "fate_escape", string.format("%s escaped slavery and is back near %s.", h.n, M.tname(W, h)), { status = "escaped" })
      elseif h.st == "a" and math.random() < cfg.step_p then M.fate(C, F, W, cfg, h, day) end
    end
  end
  local want = math.max(20, math.min(40, math.floor(cfg.count)))
  local n = 0; for _ in pairs(F.H) do n = n + 1 end
  local guard = 0
  while n < want and guard < 50 do
    guard = guard + 1
    if M.new_hero(C, F, W, day) then n = n + 1 end
  end
  M.stats.days = M.stats.days + 1
end

-- видимое -------------------------------------------------------------------------------------------------------------
function M.tier_sid(W, fid, tier)
  local e = W.tr[fid]
  if not (e and e.tiers) then return nil end
  for d = 0, 3 do
    for _, k in ipairs({ tier - d, tier + d }) do
      local sid = e.tiers["T" .. k]
      if k >= 0 and k <= 3 and sid then return sid end
    end
  end
end
function M.rename(h, lv)
  local ok, leader = pcall(function() return lv.pl:getSquadLeader() end)
  if not (ok and leader) then return false end
  local ok2 = pcall(function() leader:setName(h.n) end)
  pcall(function() lv.pl:getActivePlatoon():setName(h.n) end)
  if ok2 then lv.named = true end
  return ok2
end
function M.near(T, x, z, r)   -- Traces ленив: до его первого тика P = nil и near бросает ошибку - это не повод отключаться
  local ok, v = pcall(T.near, x, z, r)
  return ok and v == true
end
function M.vis(C, F, W, cfg, T)
  if M.pend and os.clock() - M.pend.t < cfg.pend_s then return end
  M.pend = nil
  local nl = 0; for _ in pairs(M.live) do nl = nl + 1 end
  if nl >= cfg.max_live then return end
  local hrs = M.hours(C)
  for _, h in ipairs(M.hero_list(F)) do
    if h.st == "a" and h.x and h.z and (hrs - (h.sp or -1000)) >= cfg.cd_h and not M.live["h" .. h.i] and M.near(T, h.x, h.z, cfg.vis_r) then
      if math.random() < cfg.spawn_p then
        local sid = M.tier_sid(W, h.f, h.t)
        if sid then
          local t = h.s and W.by[h.s]
          local id = "h" .. h.i
          local hostile = M.hostile(C, cfg, h)
          local S0 = M.live_S
          h.sp = hrs
          local job = { tag = "fate", fid = h.f, sid = sid, n = 1, size = 3 + h.t, from_x = h.x, from_z = h.z, to_fid = h.f,
                        to_x = t and t.x or h.x, to_z = t and t.z or h.z,
                        target = hostile and "player" or nil,
                        on_spawn = function(pls)
                          if M.live_S ~= S0 then return end   -- заявка из прошлого мира/сейва
                          M.pend = nil
                          local pl = pls and pls[1]
                          if pl then
                            local lv = { pl = pl, t = os.clock(), hostile = hostile }
                            M.live[id] = lv
                            M.rename(h, lv)
                            local okm, em = pcall(M.on_meet, C, cfg, h, lv)
                            if not okm then M.log("meet link error: " .. tostring(em)) end
                            M.stats.spawn = M.stats.spawn + 1
                            M.log(string.format("squad of %s (%s T%d) spawned near player", h.n, h.r, h.t))
                          end
                        end }
          local okq, acc = pcall(T.request, job)
          if okq and acc then M.pend = { t = os.clock(), id = id } end
        end
        return   -- одна заявка за тик
      end
    end
  end
end
function M.watch(C, F, W)
  for id, lv in pairs(M.live) do
    local h = F.H[id]
    if not h or os.clock() - lv.t > M.cfg().watch_s then M.live[id] = nil
    else
      local ok, leader = pcall(function() return lv.pl:getSquadLeader() end)
      local dead = false
      if ok and leader then
        if not lv.named then M.rename(h, lv)
        else
          local okn, nm = pcall(function() return leader:getName() end)
          if okn and nm and nm ~= h.n then dead = true end   -- лидером стал другой: герой выбыл
        end
        local okd, d = pcall(function() return leader:isDead() end)
        if okd and d then dead = true end
      end
      local okp, pd = pcall(function() return lv.pl.isDead end)
      if okp and pd == true then dead = true end
      if dead and lv.named then
        M.stats.slain = M.stats.slain + 1
        M.die(C, F, W, h, M.today(C), "was cut down with his band")
      end
    end
  end
end

-- тик -------------------------------------------------------------------------------------------------------------------
function M.tick()
  if live(M, "off") then return end
  local now = os.clock()
  local cfg0 = M.cfg()
  if cfg0.enabled == false or now - M.last < (cfg0.tick_s or 8) then return end
  M.last = now
  local C = rawget(_G, "KMM_Conductor")
  if not (C and C.state and C.cfg and C.towns) then return end
  local S = C.state()
  if type(S) ~= "table" or not S.F then return end
  M.sync_S(S)
  local day = M.today(C)
  if day <= 0 then return end
  M.sub(C)
  local F = M.F(S)
  if not F.day then F.day = day - 1 end
  if day > F.day then
    local steps = math.min(day - F.day, cfg0.max_catchup or 3)
    for i = 1, steps do M.day_step(C, F, F.day + i) end
    F.day = day
  end
  local W = M.world(C, S, F.day)
  M.watch(C, F, W)
  local T = rawget(_G, "KMM_Traces")
  if T and T.request and T.near then M.vis(C, F, W, cfg0, T) end
end
M.stats = { days = 0, rise = 0, defect = 0, slave = 0, wound = 0, camp = 0, deaths = 0, spawn = 0, slain = 0 }

local function guarded()
  local ok, err = pcall(function()
    local G = rawget(_G, "KMM_Gov")
    if G and G.run then return G.run("fates", M.tick) end
    return M.tick()
  end)
  if not ok then M.fail("tick", err) else h_ok("KMM_Fates.module") end
end
M.guarded = guarded

KMM_Fates = {
  state = function() local C = rawget(_G, "KMM_Conductor"); local S = C and C.state and C.state(); return S and S.ext and S.ext.fates end,
  heroes = function() local C = rawget(_G, "KMM_Conductor"); local S = C and C.state and C.state(); return S and M.hero_list(M.F(S)) or {} end,
  stats = function() return M.stats end,
  disabled = function() return M.off and { fates = true } or {} end,
  live = function() return M.live end,
  _tick = function() M.last = -1000; M.tick() end,
  -- принять героя со стороны (KMM_Outlaws: матёрый преступник нанялся во фракцию). o = { n, f, r, t, rep, x, z, s }; -> герой или nil
  adopt = function(o)
    if M.off or type(o) ~= "table" or not (o.n and o.f) then return nil end
    local C = rawget(_G, "KMM_Conductor"); local S = C and C.state and C.state()
    if type(S) ~= "table" then return nil end
    local F = M.F(S)
    for _, h in pairs(F.H) do if h.n == o.n then return nil end end
    local day = M.today(C)
    local h = { i = F.nid, n = o.n, f = o.f, r = ROLE_TITLE[o.r or ""] and o.r or "mercenary", t = math.max(0, math.min(3, o.t or 1)),
                rep = o.rep or -10, w = 0, st = "a", since = day, sp = -1000, x = o.x, z = o.z, s = o.s }
    F.nid = F.nid + 1
    F.H["h" .. h.i] = h
    if not h.x then local ok, W = pcall(M.world, C, S, day); if ok and W then M.place(C, W, h) end end
    return h
  end,
  _M = M,
}
if Events and Events.on then pcall(Events.on, "GameWorld::charsUpdate", guarded) end

-- PUBLISH (2026-11-16): KenshiLua runs each init script in its own sandbox; a plain global stays inside it.
if KMM_Fates ~= nil then rawset(_G, "KMM_Fates", KMM_Fates) end
