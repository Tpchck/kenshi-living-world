-- KMM_RelicRace (2026-11-13): гонка за реликтами. Сильные фракции раз в несколько недель снаряжают экспедицию к реликтовому логову
-- (точки и вещи: relicrace.json <- tools/conductor/gen_relicrace.py). Дальний мир: идёт N дней, шанс успеха от тира реликта и силы фракции.
-- ЛУТ (X4, 2026-11-15; H4/M7 ревью batch6): реликт добывается «в безымянных руинах за логовом», вскрытие задевает и само логово: если игрок
-- придёт к нему в течение dug_ttl дней, а чемпион фракции (или её отряд у руин) загружен, лучшие стопки переносятся ему (перехват = добыча).
-- Ничего не уничтожается: только перенос получателю; получателя нет - ящики не трогаются. Ящики - только ничьи, не у базы игрока, только исходный лут.
-- Живые искатели Q1 (rivals.json <- tools/streams/fix.py) и отряды экспедиции у загруженных руин рядом с игроком переносят лучшие стопки
-- из ящиков руин в инвентарь своего лидера (removeItemDontDestroy_returnsItem + addItem): убил лидера - забрал. Только руины у игрока,
-- лимиты: site_cap стопок на руины за ruin_win дней, dig_take/live_take за вскрытие/разбор, session_max за сессию; проба «ruinloot probe ok/FAIL», крэш-сторож state/probe_rl_*.
-- Видимое: (1) отряд экспедиции сильного тира рядом с игроком (Traces.request, идёт к/от логова); (2) после успеха - «чемпион»: отряд, у лидера
-- которого в инвентаре и надета реальная реликтовая вещь (createItem+addItem+equipItem, как в Conductor try_gear); убил - забрал.
-- Лимиты: <=1 чемпион на фракцию, <=4 в мире, <=2 экспедиции одновременно, кулдауны. Состояние: S.ext.relicrace (мелкое, лениво).
-- Всё под pcall; ошибка -> модуль самоотключается до перезапуска (logs/relicrace.log). Lua 5.1.
local M = {}
local LOG = "C:/KenshiModMap/logs/relicrace.log"
local P = {
  check_s = 15, start_s = 45,
  first_gap = { 4, 12 }, gap = { 14, 28 },            -- дней до первой / между экспедициями (глобально)
  max_exp = 2, max_champ = 4, faction_cd = 60, site_cd = 120, relic_cd = 150,
  min_power = 60, ref2 = 150, ref3 = 300, speed = 9000, min_days = 5, max_days = 25,
  champ_days = 60, champ_spawn_cd = 3, champ_max_spawns = 3, champ_fail_max = 2,
  champ_reissue_max = 1, champ_reissue_days = 6,   -- реликт: 1 выдача + максимум 1 повторная (ссылка на лидера протухла), не раньше чем через N дней
  vis_r = 45000, vis_cd = 2, vis_chance = 0.5, loss = 0.04,
  -- X4 RUINLOOT: руины = sites из relicrace.json; радиусы в единицах мира (как vis_r)
  loot = true, loot_s = 30, ruin_near = 8000, ruin_r = 2500, ruin_max_obj = 80, ruin_max_bld = 12,
  live_take = 3, live_cd = 0.5, dig_take = 6, site_cap = 12, ruin_win = 30, dug_ttl = 40, session_max = 40, stash_max = 8, loot_give_max = 12,
  fp_box = 12, fp_sid = 8,   -- отпечаток исходного лута: ящиков на руины, sid на ящик (R.fp)
  sdir = "C:/KenshiModMap/state/",
}
M.P = P
M.off = false
M.rt = { champ = {}, loot = { n = 0, probe = {} } }     -- несохраняемые ссылки на лидеров чемпионов; loot: счётчик сессии и пробы X4
M.stats = { launched = 0, won = 0, lost = 0, seen = 0, champ_spawned = 0, champ_slain = 0, errors = 0 }
local D, RV, last_chk, started, last_day

local function log(msg)
  pcall(function() local f = io.open(LOG, "a"); if f then f:write(os.date("%Y-%m-%d %H:%M:%S"), " [KMM_RelicRace] ", tostring(msg), "\n"); f:close() end end)
end
local function C() return rawget(_G, "KMM_Conductor") end
local function T() return rawget(_G, "KMM_Traces") end
-- HEALTH (2026-11-15): отказы идут в реестр ядра KMM_Gov (ключи KMM_RelicRace.<механика>): пауза 1/5/30 мин и повтор вместо «до перезапуска».
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

local function st()   -- S.ext.relicrace, лениво; нет мира -> nil
  local c = C(); local S = c and c.state and c.state()
  if type(S) ~= "table" then return nil end
  S.ext = S.ext or {}
  local R = S.ext.relicrace
  if not R then
    R = { exp = {}, champ = {}, fcd = {}, scd = {}, taken = {}, n = 0, hist = {} }
    S.ext.relicrace = R
  end
  R.exp, R.champ, R.fcd, R.scd, R.taken, R.hist = R.exp or {}, R.champ or {}, R.fcd or {}, R.scd or {}, R.taken or {}, R.hist or {}
  R.n = R.n or 0
  R.ruin = R.ruin or {}
  return R, S
end
local function count(t) local n = 0; for _ in pairs(t) do n = n + 1 end; return n end
local function rnd(r) return r[1] + math.random() * (r[2] - r[1]) end
local function hist(R, s) R.hist[#R.hist + 1] = s; while #R.hist > 12 do table.remove(R.hist, 1) end end
local function emit(c, R, ev) local ok, e = pcall(c.emit, ev); if not ok then log("emit: " .. tostring(e)) end end
local function dist(ax, az, bx, bz) return math.sqrt((ax - bx) ^ 2 + (az - bz) ^ 2) end

local function data(c)
  if D == nil then
    D = c.read_json("relicrace.json", "C:/KenshiModMap/build/KMM_Conductor/relicrace.json") or false
    if D and not (D.sites and D.relics and #D.sites > 0 and #D.relics > 0) then D = false end
    if not D then log("relicrace.json missing/empty - module idle") end
  end
  return D
end

local function relic_by(sid) for _, r in ipairs(D.relics) do if r.sid == sid then return r end end end
local function relic_text(r) return (r.name and r.name ~= "") and ("«" .. r.name .. "»") or "реликтовое снаряжение" end

-- выбор реликта для логова: из пула группы логова, не «занятые» (на руках у чемпиона/игрока недавно); T3 реже
function M.pick_relic(R, day, site)
  local pool, wsum = {}, 0
  for _, r in ipairs(D.relics) do
    local ok = false
    for _, g in ipairs(r.g or {}) do if g == site.g then ok = true end end
    local tk = R.taken[r.sid]
    if ok and not (tk and day - tk < P.relic_cd) then
      local w = (r.tier >= 3) and 0.4 or 1.0
      pool[#pool + 1] = { r, w }; wsum = wsum + w
    end
  end
  if wsum <= 0 then return nil end
  local x = math.random() * wsum
  for _, e in ipairs(pool) do x = x - e[2]; if x <= 0 then return e[1] end end
  return pool[#pool][1]
end

function M.pick_faction(c, R, S, day)
  local cand = {}
  for fid, f in pairs(S.F) do
    if f.alive and not f.player and fid ~= c.cfg().player_faction and not R.champ[fid] and (R.fcd[fid] or -1) <= day
       and f.mode ~= "mobilized" and not c.low(fid) then
      local hx = c.fpos(fid)
      local busy = false
      for _, e in pairs(R.exp) do if e.fid == fid then busy = true end end
      local pw = c.power(fid)
      if hx and not busy and pw >= P.min_power then cand[#cand + 1] = { fid, pw + (f.wealth or 0) * 0.2, pw } end
    end
  end
  if #cand == 0 then return nil end
  table.sort(cand, function(a, b) if a[2] ~= b[2] then return a[2] > b[2] end return a[1] < b[1] end)
  local top = math.max(3, math.ceil(#cand / 3)); if top > #cand then top = #cand end
  local sum = 0
  for i = 1, top do sum = sum + cand[i][2] end
  local x = math.random() * sum
  for i = 1, top do x = x - cand[i][2]; if x <= 0 then return cand[i][1], cand[i][3] end end
  return cand[top][1], cand[top][3]
end

function M.launch(c, R, S, day)
  if count(R.exp) >= P.max_exp or count(R.champ) >= P.max_champ then return false end
  local fid, pw = M.pick_faction(c, R, S, day)
  if not fid then return false end
  local hx, hz = c.fpos(fid)
  local near = {}
  for _, s in ipairs(D.sites) do
    if (R.scd[s.sid] or -1) <= day then near[#near + 1] = { s, dist(hx, hz, s.x, s.z) } end
  end
  table.sort(near, function(a, b) return a[2] < b[2] end)
  for i = 1, math.min(#near, 6) do   -- один из ближайших свободных логов, у которого есть незанятый реликт
    local j = math.random(1, math.min(#near, 6))
    near[i], near[j] = near[j], near[i]
  end
  for i = 1, math.min(#near, 6) do
    local site, d = near[i][1], near[i][2]
    local rel = M.pick_relic(R, day, site)
    if rel then
      local days = math.max(P.min_days, math.min(P.max_days, math.ceil(d * 2 / P.speed)))
      local ref = rel.tier >= 3 and P.ref3 or P.ref2
      local p = math.max(0.08, math.min(0.85, 0.2 + 0.5 * math.min(1.2, pw / ref) - (rel.tier - 2) * 0.1))
      R.n = R.n + 1
      local e = { id = R.n, fid = fid, site = site.sid, sname = site.name, sx = site.x, sz = site.z, hx = hx, hz = hz, t0 = day, t1 = day + days,
                  relic = rel.sid, tier = rel.tier, p = p, dug = false, seen = false, lastvis = -99 }
      R.exp[tostring(e.id)] = e
      R.scd[site.sid] = day + P.site_cd
      R.fcd[fid] = day + P.faction_cd
      M.stats.launched = M.stats.launched + 1
      emit(c, R, { type = "relic_expedition", a = fid, text = string.format("%s снаряжает экспедицию к руинам у «%s» за реликтом (около %d дн.)", c.name(fid), site.name, days) })
      hist(R, string.format("%.0f launch %s -> %s p=%.2f", day, fid, site.name, p))
      return true
    end
  end
  return false
end

-- реликт -> лидеру (createItem + addItem + equipItem, как Conductor.try_gear); true при успехе выдачи
function M.give(leader, rel)
  local ok, err = pcall(function()
    local gw = getGameWorld()
    local gd = gw.gamedata:getData(rel.sid, rel.it)
    if not gd then error("getData nil " .. rel.sid) end
    local item = gw.theFactory:createItem(gd, nil, nil, nil, -1, nil)
    if not item then error("createItem nil") end
    local inv = leader:getInventory()
    inv:addItem(item, 1, false, true)
    pcall(function() inv:equipItem(item) end)   -- не получилось надеть - реликт всё равно в инвентаре (выпадет при смерти)
  end)
  if not ok then log("give " .. tostring(rel.sid) .. ": " .. tostring(err)) end
  return ok
end

function M.finish(c, R, S, day, e)
  R.exp[tostring(e.id)] = nil
  local rel = relic_by(e.relic)
  if rel and count(R.champ) < P.max_champ and not R.champ[e.fid] and c.alive(e.fid) and math.random() < e.p then
    R.champ[e.fid] = { relic = e.relic, since = day, untl = day + P.champ_days, spawns = 0, last = -99, fails = 0, site = e.sname, issued = 0 }
    R.taken[e.relic] = day
    local u = R.ruin[e.site]
    if u and u.stash and u.dfid == e.fid then R.champ[e.fid].loot = u.stash; u.stash = nil end   -- старые сейвы: вынесенное прежней версией несёт чемпион
    M.stats.won = M.stats.won + 1
    emit(c, R, { type = "relic_found", a = e.fid, text = string.format("Экспедиция %s вернулась с реликтом %s из безымянных руин за «%s»; он у лучшего бойца фракции", c.name(e.fid), relic_text(rel), e.sname) })
    hist(R, string.format("%.0f win %s %s", day, e.fid, e.relic))
  else
    local f = S.F[e.fid]
    if f and f.alive then f.strength = f.strength * (1 - P.loss) end
    M.stats.lost = M.stats.lost + 1
    emit(c, R, { type = "relic_lost", a = e.fid, text = string.format("Экспедиция %s к «%s» не вернулась; руины за ним остались при своих тайнах", c.name(e.fid), e.sname) })
    hist(R, string.format("%.0f lose %s", day, e.fid))
  end
end

-- точка на пути экспедиции (туда: дом -> логово до середины срока; обратно - наоборот)
local function path_pos(e, day)
  local half = (e.t1 - e.t0) / 2
  local u = (day - e.t0) / math.max(0.01, half)
  if u <= 1 then return e.hx + (e.sx - e.hx) * u, e.hz + (e.sz - e.hz) * u, "out" end
  u = math.min(1, u - 1)
  return e.sx + (e.hx - e.sx) * u, e.sz + (e.hz - e.sz) * u, "back"
end

function M.visible_exp(c, R, day, e)
  local tr = T()
  if not (tr and tr.request and tr.near and tr.tier_pick) then return end
  if day - e.lastvis < P.vis_cd or math.random() > P.vis_chance then return end
  local x, z, ph = path_pos(e, day)
  if not tr.near(x, z, P.vis_r) then return end
  local shift
  for _, sh in ipairs({ 2, 1, 0 }) do if tr.tier_pick(e.fid, sh) then shift = sh; break end end
  if not shift then return end
  e.lastvis = day
  local tx, tz = e.sx, e.sz
  if ph == "back" then tx, tz = e.hx, e.hz end
  local fx, fz = (ph == "back") and e.sx or e.hx, (ph == "back") and e.sz or e.hz
  local ok = tr.request({ tag = "relic_exp", fid = e.fid, shift = shift, n = 1, size = 4, from_x = fx, from_z = fz, to_fid = e.fid, to_x = tx, to_z = tz, target = "player" })
  if ok and not e.seen then
    e.seen = true; M.stats.seen = M.stats.seen + 1
    emit(c, R, { type = "relic_expedition_seen", a = e.fid, text = string.format("Отряд экспедиции %s за реликтом замечен на дороге (%s)", c.name(e.fid), ph == "out" and "к руинам" or "домой") })
  end
end

function M.visible_champ(c, R, day, fid, ch)
  local tr = T()
  local rt = M.rt.champ[fid]
  if rt and rt.leader then   -- жив ли уже выставленный лидер
    local ok, dead = pcall(function() return rt.leader:isDead() end)
    if ok and dead then
      local rel = relic_by(ch.relic)
      R.champ[fid] = nil; M.rt.champ[fid] = nil; R.fcd[fid] = day + P.faction_cd; M.stats.champ_slain = M.stats.champ_slain + 1
      emit(c, R, { type = "relic_champion_slain", a = fid, text = string.format("Чемпион %s пал; реликт %s достался тому, кто стоял над телом", c.name(fid), rel and relic_text(rel) or "") })
      hist(R, string.format("%.0f slain %s", day, fid))
      return
    elseif ok then return end
    M.rt.champ[fid] = nil   -- ссылка протухла (отряд выгружен): можно выставить снова в пределах лимита
  end
  if not (tr and tr.request and tr.near and tr.tier_pick) then return end
  if ch.spawns >= P.champ_max_spawns or day - ch.last < P.champ_spawn_cd or math.random() > 0.6 then return end
  -- реликт выдаётся при первом выставлении; повтор (лидер выгружен без подтверждённой смерти, живым найти нельзя - ссылки нет) - не чаще
  -- чем через champ_reissue_days после выдачи и не более champ_reissue_max раз; дальше чемпион больше не выходит (до конца срока). Убитый - снят выше.
  local issued = ch.issued or ((ch.spawns or 0) > 0 and 1 or 0)   -- старые сейвы: spawns>0 считаем выдачей
  if issued >= 1 + P.champ_reissue_max then return end
  if issued >= 1 and day - (ch.iday or ch.last or day) < P.champ_reissue_days then return end
  local hx, hz = c.fpos(fid)
  if not (hx and tr.near(hx, hz, P.vis_r)) then return end
  local shift
  for _, sh in ipairs({ 3, 2, 1, 0 }) do if tr.tier_pick(fid, sh) then shift = sh; break end end
  if not shift then return end
  local rel = relic_by(ch.relic)
  if not rel then R.champ[fid] = nil; return end
  local last0, sp0 = ch.last, ch.spawns
  ch.last = day; ch.spawns = ch.spawns + 1   -- считаем заявку, а не выдачу: очередь Traces асинхронна, дублей реликта не будет сверх лимита
  local okr, acc = pcall(tr.request, { tag = "relic_champ", fid = fid, shift = shift, n = 1, size = 3, from_x = hx, from_z = hz, to_fid = fid, to_x = hx, to_z = hz, target = "player",
    on_spawn = function(pls)
      local pl = pls and pls[1]
      local leader = pl and select(2, pcall(function() return pl:getSquadLeader() end))
      if not (leader and type(leader) ~= "string") then ch.fails = ch.fails + 1; return end
      if M.give(leader, rel) then
        if ch.loot and M.give_loot(leader, ch.loot) > 0 then ch.loot = nil end   -- старые сейвы: вынесенное прежней версией - один раз; не вышло - при повторной выдаче
        ch.issued = (ch.issued or 0) + 1; ch.iday = c.day and c.day() or ch.last
        if ch.issued > 1 then log("relic reissued " .. tostring(rel.sid) .. " fid=" .. tostring(fid) .. " (leader ref was lost)"); hist(R, "reissue " .. fid .. " " .. rel.sid) end
        M.stats.champ_spawned = M.stats.champ_spawned + 1
        M.rt.champ[fid] = { leader = leader }
        if not ch.seen then ch.seen = true; emit(c, R, { type = "relic_champion_seen", a = fid, text = string.format("Чемпион %s с реликтом %s замечен вдали от дома", c.name(fid), relic_text(rel)) }) end
      else ch.fails = ch.fails + 1 end
      if ch.fails >= P.champ_fail_max then ch.untl = 0 end   -- выдать не получается: свернуть чемпиона
    end })
  if not (okr and acc) then ch.last, ch.spawns = last0, sp0 end   -- бюджет/погода Traces отказали: заявка не ушла, попытка не тратится
end

---------------------------------------------------------------------------------------------- X4 RUINLOOT
function M.ruin(R, sid, day)   -- запись руин: окно лимита w/n, последний живой разбор lt, вскрытие экспедицией dug/dfid/done/stash
  local u = R.ruin[sid]
  if not u then u = { w = day, n = 0 }; R.ruin[sid] = u end
  if day - (u.w or day) >= P.ruin_win then u.w, u.n, u.told = day, 0, nil end
  return u
end

-- крэш-сторож нативного вызова (как RecruitRace): lock на время первого вызова в сессии; lock на старте -> .off навсегда
local function probe_ok(x)
  local L = M.rt.loot
  if L.probe[x] == nil then
    local st0 = true
    pcall(function()
      local offp, lock = P.sdir .. "probe_rl_" .. x .. ".off", P.sdir .. "probe_rl_" .. x .. ".lock"
      local fh = io.open(offp, "r")
      if fh then fh:close(); st0 = false; return end
      fh = io.open(lock, "r")
      if fh then
        fh:close(); st0 = false
        local o = io.open(offp, "w"); if o then o:write("disabled: previous session crashed in ", x); o:close() end
        os.remove(lock)
        log("ruinloot " .. x .. " DISABLED forever: previous session crashed during the call")
      end
    end)
    L.probe[x] = st0
  end
  return L.probe[x]
end
local function probe_call(x, fn)
  if not probe_ok(x) then return false, "probe off" end
  local L, lock = M.rt.loot, P.sdir .. "probe_rl_" .. x .. ".lock"
  local first = not L.probe[x .. "#done"]
  if first then pcall(function() local fh = io.open(lock, "w"); if fh then fh:write(tostring(os.time())); fh:close() end end) end
  local ok, a = pcall(fn)
  if first then pcall(os.remove, lock); L.probe[x .. "#done"] = true end
  return ok, a
end
local function verdict(x, ok, what)   -- маркер пробы: ok один раз за сессию; FAIL ставит разбор руин на паузу реестра (крэш-сторож — навсегда)
  local L = M.rt.loot
  if ok then
    h_ok("KMM_RelicRace.ruinloot")
    if not L.probe[x .. "#ok"] then L.probe[x .. "#ok"] = true; log("ruinloot probe ok: " .. x .. " " .. tostring(what)) end
  elseif not probe_ok(x) then
    forever(L, "off", "KMM_RelicRace.ruinloot", "crash lock state/probe_rl_" .. x .. ".off", "crash")
    log("ruinloot probe FAIL: " .. x .. " " .. tostring(what) .. " (crash lock: off)")
  else
    local p = down(L, "off", "KMM_RelicRace.ruinloot", x .. " " .. tostring(what))
    log("ruinloot probe FAIL: " .. x .. " " .. tostring(what) .. (p and (" (paused " .. p .. " s)") or ""))
  end
end

local function rivals(c)
  if RV == nil then
    RV = c.read_json("rivals.json", "C:/KenshiModMap/build/KMM_Conductor/rivals.json") or false
    if RV and type(RV.prospectors) ~= "table" then RV = false end
    if not RV then log("rivals.json missing - live ruin looting by Q1 prospectors off (expeditions still loot)") end
  end
  return RV
end

local function player_xyz()
  local ok, x, z, y = pcall(function()
    for _, pc in pairs(getPlayerInterface():getAllPlayerCharacters()) do
      local v = pc:getPosition(); return v.x, v.z, v.y
    end
  end)
  if ok and x and z then return x, z, y or 0 end
end

local BUF
local function raw_building(o) return o:getHandle():getBuilding() end
-- H4: кто хозяин здания у руин: "player" (база игрока рядом - руины не трогаем вовсе), true (у здания есть фракция - не руины), false (ничьё)
local function bld_owner(b, pf)
  if not b:hasFaction() then return false end
  local f = b:getFaction(); local gd = f and (f.data or f:getData())
  local fid = gd and gd.stringID
  if pf and fid == pf then return "player" end
  -- HEALTH/H4 (2026-11-15): правило ванили — поселение, к которому движок приписал здание (Building:getTown -> TownBase.townType,
  -- BindingsReference/EnumsReference TownType). TOWN_RUINS — добыча руин при любой фракции здания; город/деревня/аванпост/лагерь
  -- работорговцев/военный/тюрьма — чужая собственность. Нет поселения (или гнездо/точка интереса) — правило модели дирижёра ниже.
  local okt, tt = pcall(function() local t = b:getTown(); return t and t.townType end)
  if okt and type(tt) == "number" then
    local TT = rawget(_G, "TownType")
    local function e(n, d) local v = type(TT) == "table" and TT[n]; return type(v) == "number" and v or d end
    if tt == e("TOWN_RUINS", 4) then return false end
    if tt == e("TOWN_TOWN", 2) or tt == e("TOWN_VILLAGE", 3) or tt == e("TOWN_OUTPOST", 1) or tt == e("TOWN_SLAVE_CAMP", 5)
       or tt == e("TOWN_MILITARY", 6) or tt == e("TOWN_PRISON", 7) then return true end
  end
  -- 2026-11-15 игра: «free containers 0, owned buildings 123» — у зданий руин всегда есть фракция (бандиты/монстры/руинная).
  -- Чужая собственность — только у фракции, которая держит города в модели дирижёра; остальное — добыча руин.
  local okS, S = pcall(function() return KMM_Conductor.state() end)
  local F = okS and S and S.F and fid and S.F[fid]
  if F and type(F.towns) == "table" and next(F.towns) ~= nil then return true end
  return false
end
-- ящики руин у точки site: стопки { inv, it, gd, q, v, sid, t, h }, дорогие первыми; число ящиков; true - рядом здание игрока (ничего не брать).
-- H4 «лучше ничего, чем испортить»: берутся только ничьи (без фракции) не-магазинные контейнеры; не уникальное, не надетое, не краденое
-- (краденое - вещь игрока или чужая); и только то, что лежало в ящике, когда ящик впервые попал в скан (отпечаток R.fp[site][hand]:
-- sid -> штук, исходный лут руин): что игрок положил позже - другой sid или стопка больше отпечатка - не трогается. Только загруженные здания.
-- Ключ ящика - hand:toString() здания (стабильность между сессиями ?).
function M.ruin_items(c, site, py, R)
  if not BUF then BUF = lektor.new("RootObject*") end   -- один буфер на сессию (ContainersReference)
  BUF:clear()
  getGameWorld():getObjectsWithinSphere(BUF, { x = site.x, y = py or 0, z = site.z }, P.ruin_r, 0, P.ruin_max_obj, nil)   -- 0 = itemType.BUILDING
  local pf = c.cfg().player_faction
  R.fp = R.fp or {}
  local fpS = R.fp[site.sid] or {}
  R.fp[site.sid] = fpS
  local boxes, owned = {}, 0
  for _, o in ipairs(BUF) do
    local okb, b = pcall(raw_building, o)
    if okb and b then
      local okf, own = pcall(bld_owner, b, pf)
      if okf and own == "player" then return {}, 0, true end
      if okf and own == true then owned = owned + 1 end
      if okf and own == false and #boxes < P.ruin_max_bld then
        local oki, inv = pcall(function()
          if b:isAShop() then return nil end
          local i = b:getInventory()
          return (i and i:isAContainer()) and i or nil
        end)
        local okh, h = pcall(function() return o:getHandle():toString() end)
        if oki and inv and okh and type(h) == "string" and h ~= "" then boxes[#boxes + 1] = { inv, h } end
      end
    end
  end
  local out, nfp = {}, 0
  for _ in pairs(fpS) do nfp = nfp + 1 end
  for _, bx in ipairs(boxes) do
    local inv, h = bx[1], bx[2]
    pcall(function()
      local items = {}
      for _, it in ipairs(inv:getAllItems()) do
        if not it.isUnique and not it.isEquipped then
          local gd = it:getGameData()
          local q = tonumber(it.quantity) or 1
          local oks, stolen = pcall(function() return it:isStolen(true) end)
          if gd and q > 0 and oks and stolen == false then
            local okv, v = pcall(function() return it:getValueAll(false) end)
            local okt, t = pcall(function() return it:getClassType() end)
            items[#items + 1] = { inv = inv, it = it, gd = gd, q = q, v = okv and tonumber(v) or 0, sid = gd.stringID, t = (okt and t) or gd.type, h = h }
          end
        end
      end
      local fp = fpS[h]
      if fp == nil and nfp < P.fp_box then   -- первый взгляд на ящик: отпечаток исходного содержимого (дорогие sid, не больше fp_sid)
        table.sort(items, function(x, y) return x.v > y.v end)
        fp = {}
        local ns = 0
        for _, e in ipairs(items) do
          if fp[e.sid] then fp[e.sid] = fp[e.sid] + e.q elseif ns < P.fp_sid then fp[e.sid] = e.q; ns = ns + 1 end
        end
        fpS[h] = fp; nfp = nfp + 1
      end
      if fp then for _, e in ipairs(items) do local lim = fp[e.sid]; if lim and e.q <= lim then out[#out + 1] = e end end end
    end)
  end
  local L = M.rt.loot
  L.told = L.told or {}
  if not L.told[site.sid] and #boxes + owned > 0 then
    L.told[site.sid] = true
    log(string.format("ruinloot site %s: free containers %d, owned buildings %d (skipped), takeable stacks %d", tostring(site.name), #boxes, owned, #out))
  end
  table.sort(out, function(a, b) if a.v ~= b.v then return a.v > b.v end return tostring(a.sid) < tostring(b.sid) end)
  return out, #boxes, false
end

local function count_of(inv, gd)   -- штук sid у получателя (Inventory:countItems по GameData); nil - не прочиталось
  local ok, n = pcall(function() return inv:countItems(gd) end)
  if ok and type(n) == "number" then return n end
end
-- перенести n лучших стопок в Inventory получателя (лидер искателей/экспедиции или чемпион). Только перенос: removeItemDontDestroy_returnsItem
-- + addItem, без уничтожения; без получателя функция не зовётся. M7: перенос сверяется по числу штук у получателя (стопки сливаются,
-- объект g после addItem может исчезнуть); проверка не прочиталась - перенос засчитан с пометкой, разбор не выключается.
function M.take(cands, n, dest, u, fpS)
  local L, k = M.rt.loot, 0
  for i = 1, math.min(n, #cands) do
    if L.off or L.n >= P.session_max then break end
    local e = cands[i]
    local ok, res = probe_call("take", function()
      local okr, room = pcall(function() return dest:hasRoomForItem(e.gd) end)
      if okr and room == false then return "full" end
      local c0 = count_of(dest, e.gd)
      local g = e.inv:removeItemDontDestroy_returnsItem(e.it, e.q, false)
      if not g then error("removeItemDontDestroy_returnsItem nil") end
      if not dest:addItem(g, e.q, false, false) then
        e.inv:addItem(g, e.q, true, false)   -- не влезло получателю: назад в ящик (не влезло и туда - на землю у ящика, не в пустоту)
        return "full"
      end
      local c1 = count_of(dest, e.gd)
      if c0 and c1 then
        if c1 - c0 >= e.q then return "ok" end
        if c1 > c0 then return "part" end
      end
      local okh, has = pcall(function() return dest:hasItem(e.gd, 1) end)
      if okh and has == true then return (c0 and c1) and "part" or "ok" end
      if okh and has == false then return "lost" end
      return "unverified"
    end)
    if ok and res == "full" then break end
    if ok and (res == "part" or res == "unverified") then
      log("ruinloot take " .. tostring(e.sid) .. " x" .. e.q .. ": " .. res .. " (count check), kept on")
    else
      verdict("take", ok and res == "ok", tostring(e.sid) .. " x" .. e.q .. (ok and (res == "lost" and " not in recipient inventory after addItem" or "") or (" " .. tostring(res))))
    end
    if L.off then break end
    local f = fpS and fpS[e.h]
    if f and f[e.sid] then f[e.sid] = f[e.sid] - e.q; if f[e.sid] <= 0 then f[e.sid] = nil end end   -- унесённое из отпечатка: вернувшийся sid - уже не исходный лут
    k = k + 1; L.n = L.n + 1; u.n = (u.n or 0) + 1
    log(string.format("ruinloot moved %s x%d (v=%d)", tostring(e.sid), e.q, e.v or 0))
  end
  return k
end

-- старые сейвы: добыча, уже вынесенная прежней версией (stash/ch.loot), -> чемпиону (createItem по sid, как M.give; до loot_give_max штук)
function M.give_loot(leader, loot)
  local made = 0
  pcall(function()
    local gw, inv = getGameWorld(), leader:getInventory()
    for _, l in ipairs(loot) do
      for _ = 1, l.q or 1 do
        if made >= P.loot_give_max then return end
        local gd = gw.gamedata:getData(l.s, l.t)
        local item = gd and gw.theFactory:createItem(gd, nil, nil, nil, -1, nil)
        if item then inv:addItem(item, 1, false, true); made = made + 1 end
      end
    end
  end)
  if made > 0 then log("ruinloot champion carries " .. made .. " items from the lair") end
  return made
end

-- живой грабитель у руин: отряд искателей Q1 (шаблон из rivals.json) или отряд экспедиции к этим руинам; не в бою и на ногах.
-- only_fid: только отряд экспедиции этой фракции (получатель вскрытого логова)
function M.live_looter(R, site, snap, rv, only_fid)
  for _, r in ipairs(snap.list or {}) do
    if not r.dead and r.x and r.z and dist(r.x, r.z, site.x, site.z) <= P.ruin_r then
      local lab
      local pr = (not only_fid) and rv and r.tsid and rv.prospectors[r.tsid]
      if pr then lab = pr.name or "искатели" end
      if not lab and r.fid and (not only_fid or r.fid == only_fid) then for _, e in pairs(R.exp) do if e.fid == r.fid and e.site == site.sid then lab = "exp" end end end
      if lab and not r.down and not r.combat then
        local pl = r.pl
        local ok, ld, dead = pcall(function() local l = pl and pl:getSquadLeader(); return l, l and l:isDead() end)
        if ok and ld and not dead then return ld, r.fid, lab end
      end
    end
  end
end

-- лидер ещё в живом наборе движка (getCharacterUpdateList:has - без разыменования, как Nemesis); nil - проверить нечем
local function live_ref(ch)
  local ok, live = pcall(function() return getGameWorld():getCharacterUpdateList():has(ch) end)
  if ok and type(live) == "boolean" then return live end
end
-- H4: получатель вскрытого логова - загруженный живой чемпион фракции экспедиции или её отряд у этих руин; иначе nil (ничего не трогать)
function M.dig_dest(R, u, site)
  local rt = u.dfid and M.rt.champ[u.dfid]
  if rt and rt.leader and live_ref(rt.leader) ~= false then
    local ok, dead, inv = pcall(function() return rt.leader:isDead(), rt.leader:getInventory() end)
    if ok and not dead and inv then return inv, "champ" end
  end
  local g = rawget(_G, "KMM_Gov")
  if not (u.dfid and g and g.snapshot) then return nil end
  local oks, snap = pcall(g.snapshot, 4)
  if not (oks and type(snap) == "table") then return nil end
  local ld = M.live_looter(R, site, snap, nil, u.dfid)
  if not ld then return nil end
  local okd, inv = pcall(function() return ld:getInventory() end)
  if okd and inv then return inv, "exp" end
end

function M.loot_tick(c, R, day)
  local L = M.rt.loot
  local now = os.clock()
  if L.last and now - L.last >= 0 and now - L.last < P.loot_s then return end
  L.last = now
  if L.n >= P.session_max then return end
  local px, pz, py = player_xyz()
  if not px then return end
  local site, sd = nil, P.ruin_near
  for _, s in ipairs(D.sites) do local d = dist(px, pz, s.x, s.z); if d <= sd then site, sd = s, d end end
  if not site then return end
  L.fp = L.fp or {}
  if not L.fp[site.sid] then   -- первый подход игрока за сессию: отпечаток ящиков раньше, чем игрок до них дойдёт (ничего не берём)
    local _, nb0, pb0 = M.ruin_items(c, site, py, R)
    if nb0 > 0 or pb0 then L.fp[site.sid] = true end
  end
  local u = M.ruin(R, site.sid, day)
  local room = P.site_cap - (u.n or 0)
  if room <= 0 then return end
  if u.dug and not u.done and day - u.dug <= P.dug_ttl then   -- (а) экспедиция уже вскрыла логово: разбор один раз за вскрытие, только при получателе
    local dest, who = M.dig_dest(R, u, site)
    if not dest then return end   -- чемпиона/отряда экспедиции рядом нет: ничего не трогаем, повтор через loot_s
    local cands, nb, pbase = M.ruin_items(c, site, py, R)
    if pbase then u.done = true; return end
    if nb == 0 then return end   -- ящики руин ещё не загружены: повтор через loot_s
    u.done = true
    local k = M.take(cands, math.min(P.dig_take, room), dest, u, R.fp[site.sid])
    if k > 0 then
      M.stats.ruin_dug = (M.stats.ruin_dug or 0) + k
      emit(c, R, { type = "relic_ruins_emptied", a = u.dfid, text = string.format("В «%s» до тебя побывали люди %s: лучшее из ящиков унёс %s", site.name, c.name(u.dfid),
        who == "champ" and "их чемпион" or "их отряд") })
    end
    return
  end
  if day - (u.lt or -99) < P.live_cd then return end   -- (б) живые конкуренты у руин прямо сейчас
  local g = rawget(_G, "KMM_Gov")
  if not (g and g.snapshot) then return end
  local oks, snap = pcall(g.snapshot, 4)
  if not (oks and type(snap) == "table") then return end
  local ld, fid, lab = M.live_looter(R, site, snap, rivals(c))
  if not ld then return end
  u.lt = day
  local okd, dest = pcall(function() return ld:getInventory() end)
  if not (okd and dest) then return end
  local cands, _, pbase = M.ruin_items(c, site, py, R)
  if pbase then return end
  local k = M.take(cands, math.min(P.live_take, room), dest, u, R.fp[site.sid])
  if k > 0 then
    M.stats.ruin_moved = (M.stats.ruin_moved or 0) + k
    if not u.told then
      u.told = true
      local who = (lab == "exp") and ("экспедиция " .. c.name(fid)) or ("отряд искателей (" .. lab .. ")")
      emit(c, R, { type = "relic_ruins_looting", a = fid, text = string.format("У «%s» %s выносит добычу из ящиков руин: добро теперь у их вожака", site.name, who) })
    end
  end
end


function M.day_step(c, R, S, day)
  for k, e in pairs(R.exp) do
    if not c.alive(e.fid) then R.exp[k] = nil
    else
      if not e.dug and day >= (e.t0 + e.t1) / 2 then
        e.dug = true
        if P.loot then local u = M.ruin(R, e.site, day); u.dug, u.dfid, u.done, u.stash = day, e.fid, nil, nil end
        emit(c, R, { type = "relic_dig", a = e.fid, text = string.format("Люди %s вскрывают руины у «%s»: лучшее из тамошних ящиков скоро вынесут", c.name(e.fid), e.sname) })
      end
      if day >= e.t1 then M.finish(c, R, S, day, e) end
    end
  end
  for fid, ch in pairs(R.champ) do
    if day >= ch.untl or not c.alive(fid) then
      R.champ[fid] = nil; M.rt.champ[fid] = nil; R.fcd[fid] = day + P.faction_cd
      emit(c, R, { type = "relic_champion_gone", a = fid, text = string.format("Чемпион %s сложил оружие; реликт вернулся в казну", c.name(fid)) })
    end
  end
  local held = {}
  for _, ch in pairs(R.champ) do held[ch.relic] = true end
  for sid, d in pairs(R.taken) do if day - d >= P.relic_cd and not held[sid] then R.taken[sid] = nil end end
  for sid, u in pairs(R.ruin) do   -- X4: протухшее вскрытие и пустые окна не копятся в сейве
    if u.dug and day - u.dug > P.dug_ttl then u.dug, u.dfid, u.done, u.stash = nil, nil, nil, nil end
    if not u.dug and day - (u.w or day) >= P.ruin_win and day - (u.lt or -1e9) >= P.ruin_win then R.ruin[sid] = nil end
  end
  R.next_launch = R.next_launch or (day + rnd(P.first_gap))
  if day >= R.next_launch then
    if M.launch(c, R, S, day) then R.next_launch = day + rnd(P.gap) else R.next_launch = day + 3 end
  end
end

function M.tick()
  if live(M, "off") then return end
  local now = os.clock()
  if not started then started = now end
  if now - started < P.start_s or (last_chk and now - last_chk < P.check_s) then return end
  last_chk = now
  local c = C()
  if not (c and c.state and c.day) then return end
  local R, S = st()
  if not R or not data(c) then return end
  if M.rt.S ~= S then M.rt.S = S; M.rt.champ = {} end   -- другой мир (загрузка сейва): указатели прошлого мира не трогать (класс H3 batch34)
  local day = c.day()
  if type(day) ~= "number" then return end
  if last_day ~= math.floor(day) then last_day = math.floor(day); M.day_step(c, R, S, day) end
  if P.loot and not live(M.rt.loot, "off") then
    local okl, el = pcall(M.loot_tick, c, R, day)
    if not okl then log("ruinloot " .. why_p(down(M.rt.loot, "off", "KMM_RelicRace.ruinloot", el)) .. ": " .. tostring(el)) end
  end
  for _, e in pairs(R.exp) do M.visible_exp(c, R, day, e) end
  for fid, ch in pairs(R.champ) do M.visible_champ(c, R, day, fid, ch) end
end

M.run = function()
  local ok, err = pcall(M.tick)
  if not ok then
    M.stats.errors = M.stats.errors + 1
    log(why_p(down(M, "off", "KMM_RelicRace.module", err)) .. ": " .. tostring(err))
  elseif not M.off then h_ok("KMM_RelicRace.module") end
end

local function guarded(nm, fn) return function(...) local ok, e = pcall(fn, ...); if not ok then log(nm .. " " .. why_p(down(M, "off", "KMM_RelicRace.module", e)) .. ": " .. tostring(e)) end end end
if Events and Events.on then Events.on("GameWorld::charsUpdate", guarded("tick", function() M.run() end)) end
KMM_RelicRace = M

-- PUBLISH (2026-11-16): KenshiLua runs each init script in its own sandbox; a plain global stays inside it.
if KMM_RelicRace ~= nil then rawset(_G, "KMM_RelicRace", KMM_RelicRace) end
