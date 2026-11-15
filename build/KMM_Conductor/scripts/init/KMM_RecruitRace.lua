-- KMM_RecruitRace (V1, пакет 5, 2026-11-15): гонка за рекрутами, вариант A из docs/core/RECRUIT_RACE.md.
-- Игрок стоит в городе, рядом бар-рекрут (отряд из шаблона «Recruits list …», не уникальный, не раб, не игрок).
-- Лучший по навыку (CharStats:getOverallSkillLevel_0_100) получает таймер гонки в игровых часах, рекрут говорит мрачный намёк (say).
-- Игрок нанял его сам (Notify PlayerInterface::recruit или рекрут уже среди персонажей игрока): гонка снята, на шину recruit_kept.
-- Таймер истёк: рекрута забирают бродячие искатели (Drifters или другая rival-фракция Q1, которая есть рядом) —
--   Faction:createNewEmptyActivePlatoon(шаблон Drifter solo, permanent, pos) -> Character:setFaction(fac, ap) (проба: getFaction и ключ
--   платуна после вызова) -> Platoon:setPersistentSquad(true) -> Blackboard:replaceAIPackage(«Wandering from town to town»).
--   Отряд живёт в сейве игры, рекрута потом можно встретить в мире. На шину recruit_taken.
-- Проба setFaction: первый перенос в сессии под крэш-сторожем (state/probe_rr_*.lock/.off). Вызов упал/краш -> выключен навсегда
--   (state/recruitrace.off); вызов прошёл, но фракция не подтвердилась за confirm_n тактов -> выключен до перезапуска. Отряд создаётся
--   временным и делается постоянным только после подтверждения; отпуск постоянных — только загруженных (ревью batch5 M3/M8).
-- Ревью batch34 учтено: ключ платуна не прочитан -> отряд не делается постоянным (H2); потеря записи -> только после N промахов, в сироты,
--   сироты отпускаются setPersistentSquad(false) при находке (H2); указатели между тактами не хранятся, смена мира сбрасывает
--   рантайм (H3); нет фолбэка прямой записью поля _persistentSquad (M5); у выгруженного платуна гибель только по isDead (M4).
-- Лимиты: 1 гонка одновременно, ≤1 потеря в игровую неделю, ≤persist_max постоянных отрядов модуля (записи + сироты).
-- Состояние: S.ext.recruitrace (сейв дирижёра). Опрос раз в tick_s по снимку KMM_Gov.snapshot, выбор кандидата раз в pick_s.
-- Маркеры (logs/recruitrace.log): race start, recruit cancel by player, race lapsed, setFaction ok/FAIL, persistent ok/FAIL, package ok/FAIL,
--   recruit taken, orphan released/dropped, disabled.
-- X2 (пакет 6, блок «X2» ниже): merc hired / contract FAIL / merc contract ended / merc watch dropped; changeSlaveOwner called/ok/FAIL,
--   slave rumor, slave bought, slave scan, slave freed by player; lever <merc|slave> disabled.
--   Шина: recruit_merc_hired/_left, recruit_slave_eyed (по умолчанию), recruit_slave_bought/_freed (только при Q.slave_owner).
--   Всё под pcall; ошибка -> модуль выключается до перезапуска. Lua 5.1, всё полями M.
local M = { off = false, rt = {}, S = nil, PROBE = {}, tname = {}, stats = { races = 0, kept = 0, lapsed = 0, taken = 0, fail = 0, errors = 0 } }
M.P = {
  tick_s = 4, start_s = 30, pick_s = 20, house_s = 60,
  race_h = { 30, 54 },        -- игровых часов на решение игрока
  week_h = 168,               -- не больше одной потери в игровую неделю
  cd_h = 24, cd_kept_h = 48,  -- пауза после гонки (после найма игроком — дольше)
  near_r = 4000,              -- рекрут в баре рядом с игроком
  say_r = 2500,               -- намёк, только если игрок рядом
  rival_r = 40000,            -- rival-отряд, который «видел» рекрута
  min_skill = 8,
  confirm_n = 3,              -- тактов на подтверждение setFaction (фракция/ключ платуна могут обновиться не сразу)
  lapse_miss = 15,            -- опросов подряд без рекрута в снимке (игрок ушёл, бар выгружен) -> гонка снята
  factions = { "51707-rebirth.mod", "1233-gamedata.base", "14508-gamedata.base", "95512-rebirth.mod", "1214-gamedata.base" },
  tpl = "2206-gamedata.base", -- «Drifter solo» (SQUAD_TEMPLATE)
  pkg = "2675-gamedata.base", -- «Wandering from town to town» (AI_PACKAGE)
  persist_max = 6, lost_miss = 3, orph_days = 30, scan = 1500,
  sdir = "C:/KenshiModMap/state/",
  log = "C:/KenshiModMap/logs/recruitrace.log",
}
M.SAY_START = {
  "Drifters bought my drinks tonight. Hire me soon, or I walk with them.",
  "Some wanderers want my blade. They pay in a few days. Do you?",
  "Coin talks, boss. Theirs is already on the table.",
}
M.SAY_HALF = {
  "They leave soon. So do I, unless you pay.",
  "Last nights in this bar. Decide.",
}
M.SAY_TAKEN = "Too slow. I ride with the %s now."

function M.log(msg)
  pcall(function()
    local fh = io.open(M.P.log, "a")
    if fh then fh:write(os.date("%Y-%m-%d %H:%M:%S"), " [KMM_RecruitRace] ", tostring(msg), "\n"); fh:close() end
  end)
end
-- HEALTH (2026-11-15): отказы идут в реестр ядра KMM_Gov (ключи KMM_RecruitRace.<механика>): пауза 1/5/30 мин и повтор вместо «до перезапуска».
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
local function forever_(t, f, key, why, kind) t[f], t[f .. "_p"] = true, nil; h_off(key, why, kind) end
local function why_p(p) return p and ("failed, retry in " .. p .. " s") or "disabled until restart" end
-- forever: файл state/recruitrace.off (рычаг ядра setFaction упал — защита сейва от полупереноса рекрута, решение прежних ревью);
-- в реестре это off с reason "unsafe". Иначе — пауза реестра и повтор.
function M.disable(why, forever, offfile)
  if forever or offfile then
    forever_(M, "off", "KMM_RecruitRace.module", why, forever and "unsafe" or "offfile")
    M.log("disabled" .. (forever and " forever" or " (off file)") .. ": " .. tostring(why))
  else
    local p = down(M, "off", "KMM_RecruitRace.module", why)
    M.log((p and ("failed, retry in " .. p .. " s") or "disabled until restart") .. ": " .. tostring(why))
  end
  if forever then pcall(function() local fh = io.open(M.P.sdir .. "recruitrace.off", "w"); if fh then fh:write(tostring(why)); fh:close() end end) end
end
local function guarded(nm, fn) return function(...) local ok, e = pcall(fn, ...); if not ok then M.disable(nm .. ": " .. tostring(e), false) end end end
function M.off_file()
  local ok, r = pcall(function() local fh = io.open(M.P.sdir .. "recruitrace.off", "r"); if fh then fh:close(); return true end; return false end)
  return ok and r
end

-- крэш-сторож нативного вызова: lock до первого вызова в сессии; lock на старте -> .off навсегда
function M.probe_ok(x)
  local st = M.PROBE[x]
  if st == nil then
    local lock, offp = M.P.sdir .. "probe_rr_" .. x .. ".lock", M.P.sdir .. "probe_rr_" .. x .. ".off"
    st = true
    pcall(function()
      local fh = io.open(offp, "r")
      if fh then fh:close(); st = false; return end
      fh = io.open(lock, "r")
      if fh then
        fh:close(); st = false
        local o = io.open(offp, "w"); if o then o:write("disabled: previous session crashed in ", x); o:close() end
        os.remove(lock)
        M.log("native " .. x .. " DISABLED forever: previous session crashed during the call")
      end
    end)
    M.PROBE[x] = st
  end
  return st
end
function M.probe_call(x, fn)
  if not M.probe_ok(x) then return false end
  local lock = M.P.sdir .. "probe_rr_" .. x .. ".lock"
  local first = not M.PROBE[x .. "#done"]
  if first then pcall(function() local fh = io.open(lock, "w"); if fh then fh:write(tostring(os.time())); fh:close() end end) end
  local ok, a = pcall(fn)
  if first then pcall(os.remove, lock); M.PROBE[x .. "#done"] = true end
  if not ok then M.log("native " .. x .. " error: " .. tostring(a)) end
  return ok, a
end

function M.C() return rawget(_G, "KMM_Conductor") end
function M.st(c)
  local S = c and c.state and c.state()
  if type(S) ~= "table" then return nil end
  S.ext = S.ext or {}
  local R = S.ext.recruitrace
  if type(R) ~= "table" then R = {}; S.ext.recruitrace = R end
  R.taken, R.orph = R.taken or {}, R.orph or {}
  return R, S
end
function M.hours(c)
  local ok, h = pcall(function() return getGameWorld():getTimeStamp_inGameHours():getTotalHours() end)
  if ok and type(h) == "number" then return h end
  local okd, d = pcall(c.day)
  return (okd and type(d) == "number") and d * 24 or nil
end
function M.rnd(r) return r[1] + math.random() * (r[2] - r[1]) end
function M.dist(ax, az, bx, bz) return math.sqrt((ax - bx) ^ 2 + (az - bz) ^ 2) end
function M.emit(c, ev) local ok, e = pcall(c.emit, ev); if not ok then M.log("emit: " .. tostring(e)) end end
function M.fname(c, fid) local ok, n = pcall(c.name, fid); return (ok and type(n) == "string" and n ~= "") and n or tostring(fid) end
function M.say(ch, line) local ok = pcall(function() ch:say(line) end); return ok end
-- ключ хендла: hand:toString() (✓игра, ledger ore/stock). tostring(hand) даёт адрес userdata, новый на каждый вызов (ревью batch6 M6),
--   поэтому ключ записи снимка rec.h (Gov, tostring) здесь не используется: ключ считается заново из rec.ch
function M.hk(hand)
  if hand == nil then return nil end
  local ok, s = pcall(function() return hand:toString() end)
  return (ok and type(s) == "string" and s ~= "") and s or nil
end
function M.chk(ch) local ok, hd = pcall(function() return ch:getHandle() end); return ok and M.hk(hd) or nil end

function M.player()   -- первая позиция игрока, его персонаж
  local ok, x, z, pc = pcall(function()
    for _, pc in pairs(getPlayerInterface():getAllPlayerCharacters()) do
      local p = pc:getPosition()
      if p then return p.x or p[1], p.z or p[3], pc end
    end
  end)
  if ok and x and z then return x, z, pc end
end
function M.player_has(h)   -- рекрут уже среди персонажей игрока (запасной путь отмены)
  local ok, r = pcall(function()
    for _, pc in pairs(getPlayerInterface():getAllPlayerCharacters()) do
      if M.chk(pc) == h then return true end
    end
    return false
  end)
  return ok and r
end

-- бар-рекрут: отряд из шаблона «Recruits list …» (данные ванили: 14 таких бар-отрядов; DC_IS_RECRUITABLE из Lua не читается)
function M.is_recruit_tpl(rec)
  local tsid = rec.tsid
  if not tsid then return false end
  local v = M.tname[tsid]
  if v == nil then
    local ok, nm = pcall(function() local pl = rec.pl; return pl and pl.squadTemplate and pl.squadTemplate.name end)
    nm = (ok and type(nm) == "string") and nm:lower() or ""
    v = nm:find("recruit", 1, true) ~= nil and not nm:find("prison", 1, true) and not nm:find("slave", 1, true)
    M.tname[tsid] = v
  end
  return v
end
function M.skill(ch)
  local ok, s = pcall(function() return ch:getStats():getOverallSkillLevel_0_100() end)
  return (ok and type(s) == "number") and s or nil
end
function M.rivalset()   -- уже у искателей (в т.ч. забранные нами) — не кандидаты
  if not M.RS then M.RS = {}; for _, fid in ipairs(M.P.factions) do M.RS[fid] = true end end
  return M.RS
end
function M.eligible(rec, pf)
  if rec.dead or (pf and rec.fid == pf) or M.rivalset()[rec.fid or ""] or not M.is_recruit_tpl(rec) then return false end
  if not rec.town or rec.down or rec.unique or rec.combat then return false end
  local ok, bad = pcall(function()
    local ch = rec.ch
    if ch:isPlayerCharacter() or ch:isUnique() then return true end
    local sl = ch:isSlave()
    return sl ~= nil and sl ~= 0 and sl ~= false
  end)
  return ok and not bad
end
function M.pick(snap, px, pz, pf)
  local best, bs
  for _, rec in ipairs(snap.list or {}) do
    if rec.x and M.dist(rec.x, rec.z, px, pz) <= M.P.near_r and M.eligible(rec, pf) then
      local s = M.skill(rec.ch)
      if s and s >= M.P.min_skill and (not bs or s > bs) then best, bs = rec, s end
    end
  end
  return best, bs
end
function M.rival(snap, px, pz)   -- rival-фракция: та, чей отряд рядом; иначе первая существующая из списка
  local set = {}
  for i, fid in ipairs(M.P.factions) do set[fid] = i end
  local bi, btsid
  for _, rec in ipairs(snap.list or {}) do
    local i = rec.fid and set[rec.fid]
    if i and (not bi or i < bi) and rec.x and M.dist(rec.x, rec.z, px, pz) <= M.P.rival_r then bi, btsid = i, rec.tsid end
  end
  if bi then return M.P.factions[bi], btsid end
  for _, fid in ipairs(M.P.factions) do
    local ok, fo = pcall(function() return getGameWorld().factionMgr:getFactionByStringID(fid) end)
    if ok and fo then return fid, nil end
  end
end
function M.find(snap, race)   -- запись рекрута в свежем снимке по ключу платуна и хендлу (указатели между тактами не храним)
  local b = snap.by_pkey and snap.by_pkey[race.pkey]
  for _, rec in ipairs(b or {}) do if M.chk(rec.ch) == race.h then return rec end end
  return nil
end

function M.start(c, R, rec, skill, hours, snap, px, pz)
  local fid, tsid = M.rival(snap, px, pz)
  if not fid then R.next_h = hours + M.P.cd_h; return end
  local okn, nm = pcall(function() return rec.ch:getName() end)
  local okt, tn = pcall(function() return rec.town:getName() end)
  local h = M.chk(rec.ch)
  if not (h and rec.pkey and rec.pkey ~= "") then return end
  local t1 = hours + M.rnd(M.P.race_h)
  local week = (R.last_take_h or -1e9) + M.P.week_h
  if t1 < week then t1 = week end
  R.race = { h = h, pkey = rec.pkey, name = okn and nm or "a sellsword", skill = math.floor(skill + 0.5), fid = fid, rtsid = tsid,
             town = (okt and type(tn) == "string" and tn ~= "") and tn or "the town", t0 = hours, t1 = t1, half = false, miss = 0 }
  M.stats.races = M.stats.races + 1
  M.log(string.format("race start %s (skill %d) in %s: %s will take him in %.0f h", R.race.name, R.race.skill, R.race.town, fid, t1 - hours))
  M.say(rec.ch, M.SAY_START[math.random(1, #M.SAY_START)])
end
function M.finish(R, hours, cd, why)
  R.race = nil
  R.next_h = hours + cd
  M.log(why)
end

-- перенос рекрута к rival-фракции, шаг 1: новый ВРЕМЕННЫЙ отряд + setFaction (первая попытка сессии = проба под крэш-сторожем).
-- Вызов упал/сторож -> выключение навсегда. Вызов прошёл -> подтверждение в следующих тактах (M.confirm): фракция и ключ платуна
-- могут обновиться не сразу. Постоянным отряд делается только после подтверждения; при провале пустой временный отряд отпускается.
function M.take(c, R, rec, hours)
  local race = R.race
  local ch = rec.ch
  local okd, dead = pcall(function() return ch:isDead() or ch:isPlayerCharacter() end)
  if not okd or dead then return M.finish(R, hours, M.P.cd_h, "race lapsed: recruit dead or not takeable") end
  local gw = getGameWorld()
  local fo = gw.factionMgr:getFactionByStringID(race.fid)
  if not fo then return M.finish(R, hours, M.P.cd_h, "race lapsed: faction " .. tostring(race.fid) .. " not found") end
  local tpl = gw.gamedata:getData(M.P.tpl, (itemType and itemType.SQUAD_TEMPLATE) or 52)
  if not tpl and race.rtsid then tpl = gw.gamedata:getData(race.rtsid, (itemType and itemType.SQUAD_TEMPLATE) or 52) end
  if not tpl then return M.finish(R, hours, M.P.cd_h, "race lapsed: no squad template") end
  local pos = ch:getPosition()
  local okp, pl = M.probe_call("platoon", function() return fo:createNewEmptyActivePlatoon(tpl, false, pos) end)
  local ap = okp and pl and select(2, pcall(function() return pl:getActivePlatoon() end))
  if not (okp and pl and ap and type(ap) ~= "string") then
    if okp and pl then pcall(function() pl:setPersistentSquad(false) end) end
    M.stats.fail = M.stats.fail + 1
    M.log(string.format("setFaction FAIL %s: no new platoon (%s)", race.name, tostring(pl)))
    R.race = nil
    R.next_h = hours + M.P.cd_h
    return M.disable("createNewEmptyActivePlatoon " .. (okp and "returned no platoon" or "call failed"), not okp)
  end
  local okk, key = pcall(function() return pl:getPlatoonStringID() end)
  key = (okk and type(key) == "string" and key ~= "") and key or nil
  local okc = M.probe_call("setfaction", function() ch:setFaction(fo, ap) end)
  if not okc then
    pcall(function() pl:setPersistentSquad(false) end)
    M.stats.fail = M.stats.fail + 1
    M.log(string.format("setFaction FAIL %s -> %s: call failed", race.name, race.fid))
    R.race = nil
    return M.disable("setFaction call failed", true)
  end
  local okv, fid2 = pcall(function() local f = ch:getFaction(); local gd = f and (f:getData() or f.data); return gd and gd.stringID end)
  R.pend = { h = race.h, key = key, okey = race.pkey, fid = race.fid, name = race.name, skill = race.skill, town = race.town,
             fidok = okv and fid2 == race.fid, tries = 0 }
  R.race = nil
  M.log(string.format("setFaction called %s -> %s (platoon %s, faction now %s): confirming", race.name, race.fid, tostring(key), tostring(fid2)))
end
-- шаг 2: подтверждение по свежему снимку (указатели прошлого такта не используются)
function M.confirm(c, R, snap, hours)
  local pd = R.pend
  pd.tries = pd.tries + 1
  local rec
  for _, k in ipairs({ pd.key or "", pd.okey or "" }) do
    for _, r in ipairs((snap and snap.by_pkey and snap.by_pkey[k]) or {}) do if M.chk(r.ch) == pd.h then rec = r end end
    if rec then break end
  end
  local fidok = rec and rec.fid == pd.fid
  if fidok then pd.fidok = true end
  if fidok and pd.key and rec.pkey == pd.key then return M.finalize(c, R, rec, hours, true) end
  if pd.tries < M.P.confirm_n then return end
  if pd.fidok then return M.finalize(c, R, rec, hours, false) end
  M.stats.fail = M.stats.fail + 1
  M.log(string.format("setFaction FAIL %s -> %s: faction not confirmed after %d checks", pd.name, pd.fid, pd.tries))
  local p, loaded = M.find_pl(pd.fid, pd.key)
  if p and loaded then pcall(function() p:setPersistentSquad(false) end) end
  R.pend = nil
  R.next_h = hours + M.P.cd_h
  return M.disable("setFaction not confirmed", false)
end
-- шаг 3: постоянный отряд (живёт в сейве игры) + пакет; без подтверждённого ключа или сверх потолка — временный (H2)
function M.finalize(c, R, rec, hours, keyok)
  local pd = R.pend
  R.pend = nil
  M.log(string.format("setFaction ok %s -> %s (platoon %s%s)", pd.name, pd.fid, tostring(pd.key), keyok and "" or ", key unconfirmed"))
  local pl, loaded
  if keyok then pl, loaded = M.find_pl(pd.fid, pd.key) end
  if pl and not loaded then pl = nil end
  local pk
  local np = #R.orph
  for _, t in ipairs(R.taken) do if t.pk then np = np + 1 end end
  if not pl or np >= M.P.persist_max then
    M.log(string.format("persistent FAIL %s: %s - temporary squad", pd.name, pl and ("cap " .. np) or "platoon not confirmed/loaded"))
  else
    M.probe_call("persist", function() pl:setPersistentSquad(true) end)
    local okv1, v1 = pcall(function() return pl:isPersistentSquad() end)
    if okv1 and v1 == true then pk = pd.key; M.log(string.format("persistent ok %s (key %s)", pd.name, pd.key))
    else
      pcall(function() pl:setPersistentSquad(false) end)
      M.log(string.format("persistent FAIL %s: isPersistentSquad %s - temporary squad", pd.name, tostring(v1)))
    end
  end
  local gd
  pcall(function() gd = getGameWorld().gamedata:getData(M.P.pkg, (itemType and itemType.AI_PACKAGE) or 72) end)
  local okb, board = false, nil
  if pl then okb, board = pcall(function() return pl:getBlackboard() end) end
  if gd and okb and board then
    local okr = M.probe_call("pkg", function() board:replaceAIPackage(gd) end)
    M.log(string.format("package %s %s on %s", okr and "ok" or "FAIL", M.P.pkg, pd.name))
  else M.log(string.format("package FAIL %s on %s: %s", M.P.pkg, pd.name, not gd and "no AI_PACKAGE data" or (pl and "no blackboard" or "platoon not found"))) end
  local fname = M.fname(c, pd.fid)
  if rec then M.say(rec.ch, string.format(M.SAY_TAKEN, fname)) end
  local okd2, day = pcall(c.day)
  R.taken[#R.taken + 1] = { n = pd.name, s = pd.skill, f = pd.fid, pk = pk, d = okd2 and day or 0, town = pd.town }
  while #R.taken > M.P.persist_max do
    local old = table.remove(R.taken, 1)
    if old.pk then R.orph[#R.orph + 1] = { k = old.pk, f = old.f, n = old.n, d = old.d } end
  end
  R.last_take_h = hours
  R.next_h = hours + M.P.cd_h
  M.stats.taken = M.stats.taken + 1
  M.log(string.format("recruit taken %s (skill %d) by %s at %s", pd.name, pd.skill or 0, pd.fid, pd.town))
  M.emit(c, { type = "recruit_taken", a = pd.fid, who = pd.name, town_name = pd.town,
              text = string.format("%s hired %s, a sellsword from the bar in %s, before anyone else paid.", fname, pd.name, pd.town) })
end

-- уборка постоянных отрядов модуля: одна запись за проход
function M.find_pl(fid, key)
  local fo
  pcall(function() fo = getGameWorld().factionMgr:getFactionByStringID(fid) end)
  if not (fo and key) then return nil end
  for _, m in ipairs({ "getActivePlatoons", "getUnloadedPlatoons" }) do
    local ok, lst = pcall(function() return fo[m](fo) end)
    local n = 0
    if ok and lst then pcall(function() n = #lst end) end
    for i = 1, math.min(n, M.P.scan) do
      local p = lst[i]
      local okk, k = pcall(function() return p:getPlatoonStringID() end)
      if okk and k == key then return p, m == "getActivePlatoons" end
    end
  end
  return nil
end
function M.house(c, R)
  local okd, day = pcall(c.day)
  day = okd and day or 0
  if #R.orph > 0 then
    local x = table.remove(R.orph, 1)
    local p, loaded = M.find_pl(x.f, x.k)
    if p and loaded then   -- отпускать только загруженный: выгруженный «временный» мог бы остаться в сейве (ревью batch5 M3)
      local ok = M.probe_call("persist", function() p:setPersistentSquad(false) end)
      M.log(string.format("orphan released %s (key %s): %s", tostring(x.n), tostring(x.k), ok and "ok" or "FAIL"))
    elseif p then x.d = day; R.orph[#R.orph + 1] = x   -- найден выгруженным: ждём подгрузки
    elseif day - (x.d or 0) > M.P.orph_days then
      M.log(string.format("orphan dropped %s (key %s): not seen for %d days", tostring(x.n), tostring(x.k), M.P.orph_days))
    else R.orph[#R.orph + 1] = x end
    return
  end
  R.hi = ((R.hi or 0) % math.max(1, #R.taken)) + 1
  local t = R.taken[R.hi]
  if not (t and t.pk) then return end
  local p, loaded = M.find_pl(t.f, t.pk)
  if not p then
    t.miss = (t.miss or 0) + 1
    if t.miss >= M.P.lost_miss then
      R.orph[#R.orph + 1] = { k = t.pk, f = t.f, n = t.n, d = day }
      M.log(string.format("persistent lost %s (key %s): orphan to release", t.n, t.pk))
      t.pk, t.miss = nil, nil
    end
    return
  end
  t.miss = nil
  local okd2, isd = pcall(function() return p.isDead end)
  local gone = okd2 and isd == true
  if not gone and loaded then   -- у выгруженного персонажей нет: 0 — не гибель (M4)
    local okc, n = pcall(function() return p:getCharacterCount() end)
    gone = okc and n == 0
  end
  if gone and not loaded then t.gone = true; return end   -- выгруженный не отпускаем: дождаться подгрузки
  if gone then
    local ok = M.probe_call("persist", function() p:setPersistentSquad(false) end)
    M.log(string.format("persistent released %s (key %s, squad gone): %s", t.n, t.pk, ok and "ok" or "FAIL"))
    t.pk = nil
  end
end

function M.on_recruit(_, character)
  local race = M.R and M.R.race
  if not (race and character) then return end
  local h = M.chk(character)
  if h and h == race.h then M.rt.cancel = h end
end
function M.hook()
  if M.hooked ~= nil then return end
  M.hooked = false
  local ok, e = pcall(function()
    if Events and Events.on then
      Events.on("PlayerInterface::recruit", guarded("recruit", M.on_recruit))
      M.hooked = true
    end
  end)
  M.log(ok and M.hooked and "recruit hook ok" or ("recruit hook unavailable (" .. tostring(e) .. "), fallback: player roster check"))
  pcall(function() Events.on("Character::setChainedMode", guarded("chained", function(ch, on) M.on_chained(ch, on) end)) end)
end

-- ===== X2 (пакет 6): ещё два рычага конкуренции за людей, docs/core/RECRUIT_RACE.md §4 п.2 и п.3 =====
-- merc: rival-отряд рядом с игроком нанимает отряд Mercenary Guild. Вызов Blackboard:setContractJob(реплика найма, хендл лидера),
--   реплика берётся ванильная («Two days [4000 cats]»: AI contract -> пакет Bodyguard, 48 ч). Если контракт не появился,
--   второй путь: Blackboard:_setContractJob(Bodyguard, 48, хендл). Проверка сразу: hasContractJob(). Кончился контракт -> наёмники
--   уходят (ядро), модуль пишет recruit_merc_left: окно для атаки.
--   Наёмник — только «свободный» отряд гильдии в городе (бар): не постоянный (Platoon:isPersistentSquad) и не из реестров наших модулей
--   (V1 taken/orph, Traces NAT reg/tmp, Outlaws L/orph по ключу платуна; лидеры Outlaws/Nemesis по имени) — ревью batch6 M1.
-- slave: игрок в городе, рядом раб (isSlave == IS_SLAVE), хозяин которого торговец или работорговец (лавка), рядом работорговец-конкурент
--   (Slave Traders / Slave Hunters, другой отряд). ПО УМОЛЧАНИЮ (Q.slave_owner = false) — только слух recruit_slave_eyed, хозяин не меняется.
--   Причина (ревью batch6 H5): changeSlaveOwner меняет хозяина, но раб остаётся в клетке лавки; вывести из клетки и перевести в отряд
--   покупателя в BindingsReference нечем (нет вызова «выйти из клетки», только AI-оценки cage-задач), а отряд потом уходит/деспавнится —
--   раб ничей и непродаваемый навсегда в сейве. Лучше ничего не менять. Q.slave_owner = true — старый путь: changeSlaveOwner(хендл лидера),
--   проверка getMySlaveOwner сразу и ещё confirm_n тактов, recruit_slave_bought. Освобождение такого раба взломом игрока
--   (окно KMM_Nemesis lock_t) -> recruit_slave_freed; родную память LT_FREED_ME пишет только Nemesis (долг «freed», ревью batch6 M3).
-- Каждый рычаг: не чаще раза в игровую неделю, только рядом с игроком, свой отказ: вызов упал -> выключен навсегда
--   (state/recruitrace_<рычаг>.off), результат не подтвердился -> до перезапуска. Указатели между тактами не хранятся (только строки),
--   постоянные отряды не создаются и не отпускаются.
M.Q = {
  pick_s = 20, week_h = 168, cd_h = 24,
  near_r = 5000, pair_r = 6000,            -- конкурент и наёмники рядом с игроком; наёмники рядом с конкурентом
  merc_fid = "1214-gamedata.base",          -- Mercenary Guild
  merc_line = "5079-gamedata.base",         -- DIALOGUE_LINE найма: AI contract 5090 (Bodyguard), 48 ч
  merc_pkg = "5090-gamedata.base", merc_h = 48, grace_h = 24,
  slavers = { "1084-gamedata.base", "55101-rebirth.mod" },   -- Slave Traders, Slave Hunters
  slave_r = 4000, buyer_r = 8000, min_skill = 8, confirm_n = 3, bought_max = 8, free_s = 25, find_r = 1500,
  slave_owner = false,   -- H5: смена хозяина раба выключена (раб остаётся в клетке); false -> только слух recruit_slave_eyed
}
M.X = { off = {}, ff = {} }
M.SAY_MERC = "The guild walks with me now. Try your luck."
M.SAY_SOLD = "Sold again. New chains, same weight."

function M.lever_ok(nm)
  local pk = M.X.off_p and M.X.off_p[nm]
  if M.X.off[nm] and pk and h_up(pk) then M.X.off[nm], M.X.off_p[nm] = nil, nil end   -- HEALTH: пауза рычага истекла
  if M.X.off[nm] then return false end
  if M.X.ff[nm] == nil then
    M.X.ff[nm] = false
    pcall(function() local fh = io.open(M.P.sdir .. "recruitrace_" .. nm .. ".off", "r"); if fh then fh:close(); M.X.ff[nm] = true end end)
    if M.X.ff[nm] then M.X.off[nm] = "off file"; M.log("lever " .. nm .. " off: state/recruitrace_" .. nm .. ".off present") end
  end
  return not M.X.off[nm]
end
function M.lever_off(nm, why, forever)
  M.X.off[nm] = why
  M.X.off_p = M.X.off_p or {}
  local key, p = "KMM_RecruitRace.lever_" .. nm, nil
  if forever then M.X.off_p[nm] = nil; h_off(key, why, "unsafe")
  else
    local t = {}; p = down(t, "x", key, why)
    M.X.off_p[nm] = p and key or nil
  end
  M.log("lever " .. nm .. (p and (" failed, retry in " .. p .. " s") or (" disabled" .. (forever and " forever" or " until restart"))) .. ": " .. tostring(why))
  if forever then pcall(function() local fh = io.open(M.P.sdir .. "recruitrace_" .. nm .. ".off", "w"); if fh then fh:write(tostring(why)); fh:close() end end) end
end
function M.probe_kill(x, why)   -- одна ветка вызова больше не пробуется (рычаг может жить другой веткой)
  M.PROBE[x] = false
  pcall(function() local fh = io.open(M.P.sdir .. "probe_rr_" .. x .. ".off", "w"); if fh then fh:write(tostring(why)); fh:close() end end)
end
function M.has_contract(board) local ok, v = pcall(function() return board:hasContractJob() end); return ok and v == true end
function M.is_slave1(st) return st == 1 or (SlaveStateEnum ~= nil and st == SlaveStateEnum.IS_SLAVE) end
function M.town_of(pc) local ok, n = pcall(function() return pc:getCurrentTownLocation():getName() end); return (ok and type(n) == "string" and n ~= "") and n or "the road" end
function M.pfac(c) local ok, pf = pcall(function() return c.cfg().player_faction end); return ok and pf or nil end
function M.lead(rec)   -- лидер отряда записи: Character, хендл (userdata), хендл-строка, имя; nil если мёртв/игрок/раб
  local ok, leader, hand, hs, nm = pcall(function()
    local ch = rec.pl:getSquadLeader()
    if not ch or ch:isDead() or ch:isPlayerCharacter() or M.is_slave1(ch:isSlave()) then return nil end
    local hd = ch:getHandle()
    return ch, hd, M.hk(hd), ch:getName()
  end)
  if ok and leader and hand and hs then return leader, hand, hs, nm end
end

function M.x2(c, R, snap, hours, now)
  R.merc = type(R.merc) == "table" and R.merc or {}
  R.slave = type(R.slave) == "table" and R.slave or {}
  R.slave.bought = R.slave.bought or {}
  local function run(nm, fn, ...)
    local ok, e = pcall(fn, ...)
    if not ok then M.stats.errors = M.stats.errors + 1; M.rt.spend = (nm ~= "slave") and M.rt.spend or nil; M.lever_off(nm, "error: " .. tostring(e), false) end
  end
  if M.rt.spend and M.lever_ok("slave") then run("slave", M.slave_confirm, c, R, snap, hours) end
  if now - (M.rt.x2 or -1e9) < M.Q.pick_s then return end
  M.rt.x2 = now
  local px, pz, pc = M.player()
  if not px then return end
  if M.lever_ok("merc") then
    if R.merc.act then run("merc", M.merc_watch, c, R, snap, hours)
    elseif hours >= (R.merc.next_h or -1e9) then run("merc", M.merc_try, c, R, snap, hours, px, pz, pc) end
  end
  if M.lever_ok("slave") and not M.rt.spend and hours >= (R.slave.next_h or -1e9) then run("slave", M.slave_try, c, R, snap, hours, px, pz, pc) end
end

-- M1: отряды, которые уже ведут наши модули — ключи платунов и имена лидеров из публичных реестров (только строки, указатели не читаются)
function M.busy(R)
  local B = { k = {}, n = {} }
  local function key(v) if type(v) == "string" and v ~= "" then B.k[v] = true end end
  local function name(v) if type(v) == "string" and v ~= "" then B.n[v] = true end end
  for _, t in ipairs(R.taken or {}) do key(t.pk) end
  for _, t in ipairs(R.orph or {}) do key(t.k) end
  pcall(function()
    local T = rawget(_G, "KMM_Traces")
    local _, reg, _, _, tmp = T.native()
    for _, x in ipairs(reg or {}) do key(x.k) end
    for _, x in ipairs(tmp or {}) do key(x.k) end
  end)
  pcall(function()
    local O = rawget(_G, "KMM_Outlaws").state()
    for _, o in pairs(O.L or {}) do key(o.pk); name(o.n) end
    for _, x in ipairs(O.orph or {}) do key(x.k) end
  end)
  pcall(function() for _, h in pairs(rawget(_G, "KMM_Nemesis").hunters()) do name(h.n) end end)
  return B
end
function M.free_merc(rec, B)   -- свободный наёмник гильдии: не в реестрах, не постоянный, лидер не наш именной
  if B.k[rec.pkey] then return false end
  local okp, per = pcall(function() return rec.pl:isPersistentSquad() end)
  if not okp or per == true then return false end
  if next(B.n) then
    local okn, nm = pcall(function() return rec.pl:getSquadLeader():getName() end)
    if not okn or B.n[nm or ""] then return false end
  end
  return true
end

-- п.2: конкурент перекупил наёмников
function M.merc_try(c, R, snap, hours, px, pz, pc)
  local Q, pf = M.Q, M.pfac(c)
  local rset = {}
  for _, fid in ipairs(M.P.factions) do if fid ~= Q.merc_fid then rset[fid] = true end end
  local riv, rd
  for _, rec in ipairs(snap.list or {}) do
    if rec.x and rset[rec.fid or ""] and rec.fid ~= pf and not rec.dead and rec.pkey ~= "" then
      local d = M.dist(rec.x, rec.z, px, pz)
      if d <= Q.near_r and (not rd or d < rd) and not rec.down and not rec.combat then riv, rd = rec, d end
    end
  end
  if not riv then return end
  local leader, hand, lh, ln = M.lead(riv)
  if not leader then return end
  local merc, md, seen, busy = nil, nil, {}, nil
  for _, rec in ipairs(snap.list) do
    if rec.x and rec.fid == Q.merc_fid and rec.pkey ~= "" and rec.pkey ~= riv.pkey and not seen[rec.pkey] and not rec.dead then
      seen[rec.pkey] = true
      local d = M.dist(rec.x, rec.z, riv.x, riv.z)
      if d <= Q.pair_r and M.dist(rec.x, rec.z, px, pz) <= Q.near_r and (not md or d < md) and not rec.combat and not rec.trader and rec.town then
        busy = busy or M.busy(R)
        if M.free_merc(rec, busy) then
          local okb, board = pcall(function() return rec.pl:getBlackboard() end)
          if okb and board and not M.has_contract(board) then merc, md = rec, d end
        end
      end
    end
  end
  if not merc then return end
  local okb, board = pcall(function() return merc.pl:getBlackboard() end)
  if not (okb and board) then return end
  local gw = getGameWorld()
  local line, pkg
  pcall(function() line = gw.gamedata:getData(Q.merc_line, (itemType and itemType.DIALOGUE_LINE) or 19) end)
  local via
  if line then
    local okc = M.probe_call("contract", function() board:setContractJob(line, hand) end)
    if okc and M.has_contract(board) then via = "setContractJob"
    elseif not okc and M.PROBE.contract ~= false then M.probe_kill("contract", "setContractJob call failed") end
  end
  if not via then
    pcall(function() pkg = gw.gamedata:getData(Q.merc_pkg, (itemType and itemType.AI_PACKAGE) or 72) end)
    if pkg then
      local okc2 = M.probe_call("contract2", function() board:_setContractJob(pkg, Q.merc_h, hand) end)
      if okc2 and M.has_contract(board) then via = "_setContractJob"
      elseif not okc2 and M.PROBE.contract2 ~= false then M.probe_kill("contract2", "_setContractJob call failed") end
    end
  end
  if not via then
    M.stats.fail = M.stats.fail + 1
    M.log(string.format("contract FAIL %s <- squad %s: %s", tostring(ln), merc.pkey, (line or pkg) and "no contract after calls" or "no contract data"))
    if M.PROBE.contract == false and M.PROBE.contract2 == false then return M.lever_off("merc", "both contract calls failed", true) end
    R.merc.next_h = hours + Q.cd_h
    return M.lever_off("merc", "contract not confirmed", false)
  end
  local th = Q.merc_h
  pcall(function() local e = board:getContractExpiryTime():getTotalHours() - hours; if e > 0 and e < 1000 then th = e end end)
  local tn = M.town_of(pc)
  R.merc.act = { mk = merc.pkey, lh = lh, ln = ln, rf = riv.fid, t_end = hours + th, town = tn }
  R.merc.next_h = hours + Q.week_h
  M.stats.merc = (M.stats.merc or 0) + 1
  M.log(string.format("merc hired %s (%s) <- guild squad %s via %s, contract %.0f h near %s", tostring(ln), riv.fid, merc.pkey, via, th, tn))
  M.say(leader, M.SAY_MERC)
  M.emit(c, { type = "recruit_merc_hired", a = riv.fid, b = Q.merc_fid, leader_name = ln, town_name = tn,
              text = string.format("%s of the %s hired Mercenary Guild blades near %s. Strike when the contract runs out.", tostring(ln), M.fname(c, riv.fid), tn) })
end
function M.merc_watch(c, R, snap, hours)
  local a = R.merc.act
  local b = snap.by_pkey and snap.by_pkey[a.mk]
  local rec = b and b[1]
  if rec then
    local okb, board = pcall(function() return rec.pl:getBlackboard() end)
    if okb and board and not M.has_contract(board) then
      R.merc.act = nil
      M.log(string.format("merc contract ended %s: guild squad %s left (window open)", tostring(a.ln), a.mk))
      M.emit(c, { type = "recruit_merc_left", a = a.rf, b = M.Q.merc_fid, leader_name = a.ln, town_name = a.town,
                  text = string.format("The hired blades left %s of the %s. The contract ran out.", tostring(a.ln), M.fname(c, a.rf)) })
    end
    return
  end
  if hours > (a.t_end or 0) + M.Q.grace_h then R.merc.act = nil; M.log("merc watch dropped " .. tostring(a.ln) .. ": guild squad not loaded") end
end

-- п.3: невольничий рынок наперегонки
function M.slave_try(c, R, snap, hours, px, pz, pc)
  local Q, pf = M.Q, M.pfac(c)
  local okt, intown = pcall(function() return pc:getCurrentTownLocation() ~= nil end)
  if not (okt and intown) then return end
  local sset = {}
  for _, f in ipairs(Q.slavers) do sset[f] = true end
  local ph = {}
  pcall(function() for _, p in pairs(getPlayerInterface():getAllPlayerCharacters()) do local k = M.chk(p); if k then ph[k] = true end end end)
  local near, byh = {}, nil
  for _, rec in ipairs(snap.list or {}) do
    if rec.x and not rec.dead and M.dist(rec.x, rec.z, px, pz) <= Q.buyer_r then near[#near + 1] = rec end
  end
  local function owner_rec(os_)   -- хозяин раба: торговец/работорговец среди загруженных рядом (ключи считаются один раз за проход)
    if not byh then
      byh = {}
      for _, r in ipairs(near) do
        if r.trader or sset[r.fid or ""] then local h = M.chk(r.ch); if h then byh[h] = r end end
      end
    end
    return byh[os_]
  end
  local best, bs, bown, bok, nsl = nil, nil, nil, nil, 0
  for _, rec in ipairs(near) do
    if rec.town and rec.fid ~= pf and M.dist(rec.x, rec.z, px, pz) <= Q.slave_r and not rec.unique then
      local ok, st, own = pcall(function() local ch = rec.ch; return ch:isSlave(), ch:getMySlaveOwner() end)
      if ok and M.is_slave1(st) and own ~= nil then
        nsl = nsl + 1
        local os_ = M.hk(own)
        local o = os_ and not ph[os_] and owner_rec(os_)
        if o then
          local s = M.skill(rec.ch)
          if s and s >= Q.min_skill and (not bs or s > bs) then best, bs, bown, bok = rec, s, o, os_ end
        end
      end
    end
  end
  if not best then
    if nsl > 0 and not M.X.diag then M.X.diag = true; M.log(string.format("slave scan: %d slaves near, none owned by a loaded trader/slaver (owner hand ?)", nsl)) end
    return
  end
  local buyer, bd, leader, hand, lh, ln
  for _, rec in ipairs(near) do
    if sset[rec.fid or ""] and rec.pkey ~= "" and rec.pkey ~= bown.pkey and rec.pkey ~= best.pkey and not rec.trader and not rec.combat and not rec.down then
      local d = M.dist(rec.x, rec.z, best.x, best.z)
      if not bd or d < bd then
        local l1, h1, s1, n1 = M.lead(rec)
        if l1 and s1 ~= bok then buyer, bd, leader, hand, lh, ln = rec, d, l1, h1, s1, n1 end
      end
    end
  end
  if not buyer then return end
  local okn, sn = pcall(function() return best.ch:getName() end)
  sn = (okn and type(sn) == "string" and sn ~= "") and sn or "a slave"
  local tn = M.town_of(pc)
  if not Q.slave_owner then   -- H5: только слух, хозяин и клетка не трогаются
    R.slave.next_h = hours + Q.week_h
    M.stats.slave_rumor = (M.stats.slave_rumor or 0) + 1
    M.log(string.format("slave rumor %s (skill %d): %s of %s eyes the cages of %s (owner unchanged: slave_owner off)",
          sn, math.floor(bs + 0.5), tostring(ln), buyer.fid, tn))
    M.emit(c, { type = "recruit_slave_eyed", a = buyer.fid, b = bown.fid, leader_name = sn, town_name = tn,
                text = string.format("The %s have their eye on %s, the strongest in the cages of %s. They will come back with coin.", M.fname(c, buyer.fid), sn, tn) })
    return
  end
  local bh = M.chk(best.ch)
  if not bh then return end
  local okc = M.probe_call("slaveowner", function() best.ch:changeSlaveOwner(hand) end)
  if not okc then
    M.stats.fail = M.stats.fail + 1
    M.log(string.format("changeSlaveOwner FAIL %s -> %s: call failed", sn, buyer.fid))
    return M.lever_off("slave", "changeSlaveOwner call failed", true)
  end
  local okv, now_own = pcall(function() return M.hk(best.ch:getMySlaveOwner()) end)
  if not (okv and now_own == lh) then
    M.stats.fail = M.stats.fail + 1
    M.log(string.format("changeSlaveOwner FAIL %s -> %s: owner is %s", sn, buyer.fid, tostring(now_own)))
    R.slave.next_h = hours + Q.cd_h
    return M.lever_off("slave", "owner not changed", false)
  end
  M.rt.spend = { h = bh, pkey = best.pkey, x = best.x, z = best.z, lh = lh, ln = ln, n = sn, s = math.floor(bs + 0.5),
                 bf = buyer.fid, of = bown.fid, town = tn, tries = 0, seen = 0 }
  M.log(string.format("changeSlaveOwner called %s (skill %d) -> %s of %s: confirming", sn, M.rt.spend.s, tostring(ln), buyer.fid))
end
function M.find_h(snap, sp)   -- запись по хендлу: сначала платун, затем поиск рядом с прошлой точкой
  for _, r in ipairs((snap.by_pkey and snap.by_pkey[sp.pkey]) or {}) do if M.chk(r.ch) == sp.h then return r end end
  for _, r in ipairs(snap.list or {}) do
    if r.x and M.dist(r.x, r.z, sp.x, sp.z) <= M.Q.find_r and M.chk(r.ch) == sp.h then return r end
  end
end
function M.slave_confirm(c, R, snap, hours)
  local sp = M.rt.spend
  sp.tries = sp.tries + 1
  local rec = snap and M.find_h(snap, sp)
  if rec then
    local ok, o = pcall(function() return M.hk(rec.ch:getMySlaveOwner()) end)
    if ok and o ~= sp.lh then
      M.rt.spend = nil
      M.stats.fail = M.stats.fail + 1
      M.log(string.format("changeSlaveOwner FAIL %s: owner reverted to %s (cage keeps the slave?)", sp.n, tostring(o)))
      R.slave.next_h = hours + M.Q.cd_h
      return M.lever_off("slave", "owner reverted", false)
    end
    if ok then sp.seen = sp.seen + 1 end
  end
  if sp.tries < M.Q.confirm_n then return end
  M.rt.spend = nil
  M.log(string.format("changeSlaveOwner ok %s -> %s (seen %d/%d)", sp.n, tostring(sp.ln), sp.seen, sp.tries))
  if rec then M.say(rec.ch, M.SAY_SOLD) end
  local lst = R.slave.bought
  local okd, day = pcall(c.day)
  lst[#lst + 1] = { h = sp.h, n = sp.n, f = sp.bf, ln = sp.ln, d = okd and day or 0, town = sp.town }
  while #lst > M.Q.bought_max do table.remove(lst, 1) end
  R.slave.next_h = hours + M.Q.week_h
  M.stats.slave = (M.stats.slave or 0) + 1
  M.log(string.format("slave bought %s (skill %d) by %s at %s", sp.n, sp.s, sp.bf, sp.town))
  M.emit(c, { type = "recruit_slave_bought", a = sp.bf, b = sp.of, leader_name = sp.n, town_name = sp.town,
              text = string.format("The %s bought %s, the strongest in the cages of %s, before anyone else paid.", M.fname(c, sp.bf), sp.n, sp.town) })
end
function M.freed_by_player()   -- только взлом оков игроком (окно KMM_Nemesis lock_t); фолбэк «игрок рядом» убран (ревью batch6 M3)
  local NM = rawget(_G, "KMM_Nemesis")
  local okl, lt = pcall(function() local N = NM and NM._N; return N and N.lock_t and os.clock() - N.lock_t <= ((N.cfg and N.cfg().lockpick_window) or M.Q.free_s) end)
  return okl and lt and true or false
end
function M.on_chained(ch, on)   -- оковы сняты взломом игрока у проданного нами раба -> слух; память LT_FREED_ME пишет только Nemesis (долг)
  if M.off or on ~= false then return end
  local lst = M.R and M.R.slave and M.R.slave.bought
  if not (lst and #lst > 0) then return end
  local h = M.chk(ch)
  if not h then return end
  for i, b in ipairs(lst) do
    if b.h == h then
      if not M.freed_by_player() then return end
      table.remove(lst, i)
      M.stats.freed = (M.stats.freed or 0) + 1
      M.log(string.format("slave freed by player %s (sold to %s): memory via Nemesis debt", b.n, tostring(b.f)))
      local C = M.C()
      if C and C.emit then
        M.emit(C, { type = "recruit_slave_freed", a = b.f, leader_name = b.n, town_name = b.town,
                    text = string.format("%s, bought by the %s, walks free. Someone broke the chains.", b.n, M.fname(C, b.f)) })
      end
      return
    end
  end
end

function M.tick()
  if live(M, "off") then return end
  local now = os.clock()
  M.t0 = M.t0 or now
  if now - M.t0 < M.P.start_s or now - (M.last or -1e9) < M.P.tick_s then return end
  M.last = now
  if M.off_file() then return M.disable("state/recruitrace.off present", false, true) end
  local c = M.C()
  if not (c and c.state and c.emit and c.day) then return end
  local R, S = M.st(c)
  if not R then return end
  if M.S ~= S then   -- другой сейв: рантайм прошлого мира не трогать
    if M.S ~= nil then M.log("world changed: runtime reset") end
    M.S, M.rt = S, {}
    if R.pend then M.log("pending transfer dropped (loaded from save): " .. tostring(R.pend.name)); R.pend = nil end
  end
  M.R = R
  M.hook()
  local hours = M.hours(c)
  if not hours then return end
  if now - (M.rt.house or -1e9) >= M.P.house_s then M.rt.house = now; M.house(c, R) end
  local G = rawget(_G, "KMM_Gov")
  local snap = G and G.snapshot and G.snapshot(2.0)
  if snap then M.x2(c, R, snap, hours, now) end
  if R.pend then return M.confirm(c, R, snap, hours) end
  local race = R.race
  if race then
    if M.rt.cancel == race.h or M.player_has(race.h) then
      M.stats.kept = M.stats.kept + 1
      M.emit(c, { type = "recruit_kept", a = race.fid, who = race.name, town_name = race.town,
                  text = string.format("Someone outbid the %s for %s at the bar in %s.", M.fname(c, race.fid), race.name, race.town) })
      M.rt.cancel = nil
      return M.finish(R, hours, M.P.cd_kept_h, "recruit cancel by player " .. race.name)
    end
    if not snap then return end
    local rec = M.find(snap, race)
    if not rec or rec.dead then
      race.miss = (race.miss or 0) + 1
      if race.miss >= M.P.lapse_miss or (rec and rec.dead) then
        M.stats.lapsed = M.stats.lapsed + 1
        return M.finish(R, hours, M.P.cd_h, "race lapsed: recruit unloaded or dead " .. race.name)
      end
      return
    end
    race.miss = 0
    if hours >= race.t1 then
      if hours - (R.last_take_h or -1e9) < M.P.week_h then race.t1 = (R.last_take_h or 0) + M.P.week_h; return end
      if rec.down or rec.combat then return end
      return M.take(c, R, rec, hours)
    end
    if not race.half and hours >= (race.t0 + race.t1) / 2 then
      local px, pz = M.player()
      if px and rec.x and M.dist(px, pz, rec.x, rec.z) <= M.P.say_r then
        race.half = true
        M.say(rec.ch, M.SAY_HALF[math.random(1, #M.SAY_HALF)])
      end
    end
    return
  end
  if hours < (R.next_h or -1e9) or hours < (R.last_take_h or -1e9) + M.P.week_h - M.P.race_h[2] then return end
  if not snap or now - (M.rt.pick or -1e9) < M.P.pick_s then return end
  M.rt.pick = now
  local px, pz, pc = M.player()
  if not px then return end
  local okt, intown = pcall(function() return pc:getCurrentTownLocation() ~= nil end)
  if not (okt and intown) then return end
  local okf, pf = pcall(function() return c.cfg().player_faction end)
  local rec, skill = M.pick(snap, px, pz, okf and pf or nil)
  if rec then M.start(c, R, rec, skill, hours, snap, px, pz) end
end

function M.run()
  local ok, err = pcall(function()
    local G = rawget(_G, "KMM_Gov")
    if G and G.run then return G.run("recruitrace", M.tick) end
    return M.tick()
  end)
  if not ok then M.stats.errors = M.stats.errors + 1; M.disable("tick: " .. tostring(err), false)
  elseif not M.off then h_ok("KMM_RecruitRace.module") end
end
function M._reset() M.off, M.rt, M.S, M.R, M.PROBE, M.tname, M.t0, M.last, M.hooked, M.X = false, {}, nil, nil, {}, {}, nil, nil, nil, { off = {}, ff = {} } end

if Events and Events.on then pcall(function() Events.on("GameWorld::charsUpdate", guarded("tick", M.run)) end) end
KMM_RecruitRace = M
