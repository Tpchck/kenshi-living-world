-- KMM_Deeds — шина дел мира (P6, 2026-11-15). Мир реагирует на ДЕЛА, а не на броски кубика: ядро само зовёт
-- FactionRelations::affectRelations(self, otherFaction, eventType, multiplier) на каждый поступок (атака, победа, убийство,
-- казнь, помощь в бою, первая помощь, «отнёс в постель», плен), в том числе игрока (CallbacksReference CR:65, ✓код).
-- Смысл аргументов (по именам FactionEvent, K/FactionRelations.h:39-56, ✓код; направление ? до лога игры):
--   self.me — фракция, чьё отношение меняется («нас» в ATTACKED_US…) = b; otherFaction — кто это сделал = a.
-- Колбэк частый (бой толпы), поэтому в нём только счётчик в окне агрегата: пара (a, b, тон) -> число, сумма множителей,
-- самое тяжёлое дело. Раз в flush_s секунд (тик под KMM_Gov) окно сбрасывается в KMM_Conductor.emit одним событием на пару:
--   { type = "deed", kind, tone = "harm"|"help", a, b, by_player, to_player, n, w, counts, aggressive, x, z, town_sid, town_name, text }
-- Не дублирует дирижёра: простое нападение игрока на фракцию и фракции на игрока уже идут как player_raid / attack_on_player
-- (хук Character::_NV_hitByMeleeAttack), поэтому «attacked» с участием игрока не эмитится; у NPC «attacked» без исхода — мелкая
-- стычка, тоже только счётчик. Одно событие на (a, b, вид) в игровой день; потолки событий в день отдельно для NPC и игрока.
-- Координаты: колбэк позиций не даёт; бой идёт только в загруженной зоне, поэтому место = позиция персонажа игрока при сбросе (?).
-- Y1 (2026-11-15) СВИДЕТЕЛИ: дело игрока (by_player) помечается witnessed=true/false по ванильным сигналам, не по своей переменной:
--   1) колбэк BountyManager::notifyCrimeWitnessed(self, faction, againstWho, expiryTime, crimeType) (CallbacksReference, ✓код):
--      ядро зовёт его, когда преступление заметили; self.me — преступник (поле BountyManager.me ✓код; что это именно преступник — ?).
--      Если self.me — персонаж игрока, запоминаем время по фракции faction («кому»). Дело игрока против b в окне wit_s — видели (src=crime).
--   2) нет преступления (бой в пустоши, помощь) — осведомлённость ближайших живых NPC из снимка KMM_Gov:
--      Character.getSensoryData -> SensoryData.amIAwareOfThisGuy(игрок, wit_need_see) (SensoryData.h ✓код; смысл флага ?). Кто-то в сознании
--      знает — видели (src=sense); вокруг никого или никто не знает — не видели. Выжившие расскажут, перебитые до одного — нет.
--   Ни колбэка, ни снимка (или все вызовы упали) — witnessed=nil (как до Y1). Дело против игрока (to_player) — witnessed=true (его делали
--   сами NPC). NPC <-> NPC — поля нет. Невиданное дело тоже уходит в шину (Sync — подсказка пары, Predators — запах): фильтруют подписчики.
--   Невиданное дело без сигнала, случившееся меньше wit_hold_s назад, ждёт одно окно (свидетель может заметить чуть позже).
--   Отдельный ключ дедупликации (невиданное, потом увиденное в тот же день — два события). API: KMM_Deeds.crime_seen(fid, within_s).
-- Состояние: S.ext.deeds (сейв дирижёра, дни и дедупликация). Лог: C:/KenshiModMap/logs/deeds.log. Всё под pcall;
-- ошибка колбэка выключает только колбэк, ошибка тика — модуль до перезапуска. Kenshi Lua 5.1; всё — поля таблицы D.
local TAG = "[KMM_Deeds] "
local D = { off = false, hook_off = false, crime_off = false, hooked = false, crime = {}, ncrime_log = 0, last = -1000, last_flush = -1000, nlog = 0,
            agg = {}, nagg = 0, sec = -1, sec_n = 0, seen_first = false,
            st = { calls = 0, kept = 0, dropped = 0, unknown = 0, same = 0, emitted = 0, dup = 0, capped = 0, minor = 0, foreign = 0, flushes = 0,
                   crimes = 0, crime_pl = 0, wit_yes = 0, wit_no = 0, wit_nil = 0, held = 0, sense_err = 0 } }

D.DEF = {
  enabled = true,
  tick_s = 2,            -- тик проверяет, пора ли сброс
  flush_s = 10,          -- окно агрегата, реальные секунды
  max_calls_s = 300,     -- колбэков в секунду сверх этого — только счётчик dropped
  max_keys = 64,         -- пар в одном окне
  npc_day = 8,           -- событий NPC <-> NPC в игровой день
  player_day = 16,       -- событий с участием игрока в игровой день
  known_only = true,     -- чужая сторона должна быть фракцией модели дирижёра (звери, мелочь — мимо)
  town_r = 6000,         -- ближе к городу — событие привязано к городу (town_sid/town_name для слухов)
  witness = true,        -- Y1: метка witnessed у дел игрока (false — поле не ставится, как до Y1)
  wit_s = 30,            -- преступление игрока, замеченное ядром, считается для дела не дольше, реальные секунды
  wit_pre_s = 5,         -- и не раньше начала дела минус столько
  wit_hold_s = 4,        -- дело без свидетеля моложе этого ждёт одно окно (колбэк свидетеля может прийти позже)
  wit_r = 3000,          -- радиус поиска возможных свидетелей вокруг места дела
  wit_max = 8,           -- не больше стольких NPC спросить (ближайшие)
  wit_pcs = 3,           -- о скольких персонажах игрока спрашивать
  wit_need_see = true,   -- второй аргумент amIAwareOfThisGuy (видит или слышит сейчас)
  log_max = 800,
  log = "C:/KenshiModMap/logs/deeds.log",
}
-- FactionEvent (K/FactionRelations.h:39-56, EnumsReference FactionRelations.FactionEvent): имя, тон, тяжесть, агрессивно
D.KIND = {
  [0] = { "attacked", "harm", 1, false }, [1] = { "attacked", "harm", 1, true },
  [2] = { "defeated", "harm", 2, false }, [3] = { "defeated", "harm", 2, true },
  [4] = { "killed", "harm", 5 }, [5] = { "killed", "harm", 3 }, [6] = { "executed", "harm", 6 },
  [7] = { "aided", "help", 3 }, [8] = { "first_aid", "help", 1 }, [9] = { "bed", "help", 2 },
  [10] = { "defeated_enemy", "help", 3 }, [11] = { "killed_enemy", "help", 4 }, [12] = { "captured", "harm", 4 },
}
D.SEV = {}
for _, k in pairs(D.KIND) do D.SEV[k[1]] = math.max(D.SEV[k[1]] or 0, k[3]) end
D.CRIME = { [1] = "enslaving", [2] = "lockpicking", [3] = "stealing", [4] = "murder", [5] = "assault", [6] = "assault_vip",
            [7] = "slave_freeing", [8] = "smuggling", [9] = "terrorism", [10] = "looting", [11] = "trespassing", [12] = "escape_prison",
            [13] = "fencing", [14] = "farm_eating", [15] = "kidnapping", [16] = "uniform_theft" }   -- CrimeEnum (EnumsReference)
D.TEXT = {
  attacked = "%s attacked %s", defeated = "%s beat down fighters of %s", killed = "%s killed people of %s",
  executed = "%s executed a prisoner of %s", captured = "%s took people of %s prisoner",
  aided = "%s fought beside %s", first_aid = "%s patched up the wounded of %s", bed = "%s carried the wounded of %s to safety",
  defeated_enemy = "%s beat down the enemies of %s", killed_enemy = "%s killed the enemies of %s",
}

function D.log(msg)
  if D.nlog >= D.DEF.log_max then return end
  D.nlog = D.nlog + 1
  local ok, f = pcall(io.open, D.DEF.log, "a")
  if ok and f then f:write(os.date("%Y-%m-%d %H:%M:%S"), " ", tostring(msg), "\n"); f:close() end
  pcall(function() if KenshiLua and KenshiLua.log then KenshiLua.log(TAG .. tostring(msg)) end end)
end
function D.fail(where, err) D.off = true; D.log("disabled until restart in " .. where .. ": " .. tostring(err)) end
function D.cfg()
  local c = D.DEF
  local ok, p = pcall(function() return KMM_Conductor.cfg().params.deeds end)
  if ok and type(p) == "table" then
    c = {}
    for k, v in pairs(D.DEF) do c[k] = v end
    for k, v in pairs(p) do c[k] = v end
  end
  return c
end
function D.fid(f)   -- Faction -> stringID, имя (как у дирижёра: getData() или поле data)
  if not f then return nil end
  local gd = f:getData() or f.data
  if not gd then return nil end
  return gd.stringID, gd.name
end
function D.fid_me(rels) return D.fid(rels and rels.me) end

-- колбэк ядра: только счётчик ----------------------------------------------------------------------------------------------
function D.on_rel(rels, other, et, mult)
  if D.off or D.hook_off then return end
  local st, c = D.st, D.C or D.DEF
  st.calls = st.calls + 1
  local now = os.clock()
  local s = math.floor(now)
  if s ~= D.sec then D.sec, D.sec_n = s, 0 end
  D.sec_n = D.sec_n + 1
  if D.sec_n > c.max_calls_s then st.dropped = st.dropped + 1; return end
  local k = D.KIND[tonumber(et) or -1]
  if not k then st.unknown = st.unknown + 1; return end
  local okb, b, bn = pcall(D.fid_me, rels)
  local oka, a, an = pcall(D.fid, other)
  if not (okb and oka and a and b) then st.unknown = st.unknown + 1; return end
  if a == b then st.same = st.same + 1; return end
  if not D.seen_first then
    D.seen_first = true
    D.log(string.format("first callback: event %s (%s) %s > %s mult %s", tostring(et), k[1], tostring(a), tostring(b), tostring(mult)))
  end
  local key = a .. "|" .. b .. "|" .. k[2]
  local r = D.agg[key]
  if not r then
    if D.nagg >= c.max_keys then st.dropped = st.dropped + 1; return end
    r = { a = a, b = b, an = an, bn = bn, tone = k[2], n = 0, w = 0, c = {}, t0 = now }
    D.agg[key] = r; D.nagg = D.nagg + 1
  end
  r.n = r.n + 1
  r.t1 = now
  r.w = r.w + math.abs(tonumber(mult) or 1)
  r.c[k[1]] = (r.c[k[1]] or 0) + 1
  if not r.top or k[3] > D.SEV[r.top] then r.top = k[1] end
  if k[4] then r.aggr = true end
  st.kept = st.kept + 1
end

-- Y1: колбэк свидетеля ядра — только отметка времени ------------------------------------------------------------------------
function D.on_crime(bm, fac, who, expiry, crime)
  if D.off or D.crime_off then return end
  local st = D.st
  st.crimes = st.crimes + 1
  local okp, isp = pcall(function() local me = bm and bm.me; return me and me:isPlayerCharacter() end)
  if not (okp and isp) then return end   -- чужие преступления — только счётчик
  local okf, sid = pcall(D.fid, fac)
  sid = (okf and sid) or "?"
  local e = D.crime[sid]
  if not e then e = {}; D.crime[sid] = e end
  e.t, e.c = os.clock(), tonumber(crime) or -1
  st.crime_pl = st.crime_pl + 1
  if D.ncrime_log < 40 then
    D.ncrime_log = D.ncrime_log + 1
    D.log(string.format("crime seen: %s (%s) against %s expiry %s", tostring(crime), D.CRIME[e.c] or "?", sid, tostring(expiry)))
  end
end
function D.crime_for(fid, since, now, c)   -- замеченное ядром преступление игрока против fid (или фракция не прочиталась) в окне
  for _, k in ipairs({ fid or "?", "?" }) do
    local e = D.crime[k]
    if e and e.t >= since and now - e.t <= c.wit_s then return e end
  end
end
function D.sense(c, pf, px, pz)   -- true/false: кто-то живой рядом осведомлён об игроке; nil — проверить нечем
  if not px then return nil end
  local G = rawget(_G, "KMM_Gov")
  local okS, snap = pcall(function() return G and G.snapshot and G.snapshot(5) end)
  if not (okS and type(snap) == "table" and snap.list) then return nil end
  local pcs = {}
  pcall(function()
    for _, ch in pairs(getPlayerInterface():getAllPlayerCharacters()) do
      if #pcs >= c.wit_pcs then break end
      local okd, dead = pcall(function() return ch:isDead() end)
      if okd and not dead then pcs[#pcs + 1] = ch end
    end
  end)
  if #pcs == 0 then return nil end
  local cand, r2 = {}, c.wit_r * c.wit_r
  for _, r in ipairs(snap.list) do
    if r.fid ~= pf and not r.dead and r.x then
      local d2 = (r.x - px) ^ 2 + (r.z - pz) ^ 2
      if d2 < r2 then cand[#cand + 1] = { d2, r.ch } end
    end
  end
  if #cand == 0 then return false, 0, 0 end
  table.sort(cand, function(u, v) return u[1] < v[1] end)
  local asked, errs, need = 0, 0, c.wit_need_see ~= false
  for i = 1, math.min(#cand, c.wit_max) do
    local ch = cand[i][2]
    local ok, aw = pcall(function()
      if ch:isDead() or ch:isDown() then return nil end
      local sd = ch:getSensoryData()
      for _, pc in ipairs(pcs) do if sd:amIAwareOfThisGuy(pc, need) then return true end end
      return false
    end)
    if not ok then errs = errs + 1
    elseif aw ~= nil then
      asked = asked + 1
      if aw then return true, asked, #cand end
    end
  end
  D.st.sense_err = D.st.sense_err + errs
  if asked == 0 and errs > 0 then return nil end   -- ни один вызов не прошёл: сигнала нет
  return false, asked, #cand
end
function D.witness(c, r, pf, px, pz, now)   -- -> witnessed (true/false/nil), источник, запись преступления
  local e = D.crime_for(r.b, (r.t0 or now) - c.wit_pre_s, now, c)
  if e then return true, "crime", e end
  local w, asked, nc = D.sense(c, pf, px, pz)
  if w == nil then return nil, "nosignal" end
  return w, (w and "sense" or "none") .. " " .. tostring(asked) .. "/" .. tostring(nc)
end

-- сброс окна в шину --------------------------------------------------------------------------------------------------------
function D.state(S)
  S.ext = S.ext or {}
  local X = S.ext.deeds
  if type(X) ~= "table" then X = { v = 1, day = -1, seen = {}, npc = 0, pl = 0, tot = 0 }; S.ext.deeds = X end
  return X
end
function D.day(C)
  local ok, d = pcall(function() return getGameWorld():getTimeStamp_inGameHours():getTotalDays() end)
  if ok and type(d) == "number" then return d end
  local okc, cd = pcall(C.day)
  return okc and tonumber(cd) or 0
end
function D.player_pos()
  local ok, x, z = pcall(function()
    for _, ch in pairs(getPlayerInterface():getAllPlayerCharacters()) do
      local p = ch:getPosition()
      if p then return p.x, p.z end
    end
  end)
  if ok then return x, z end
end
function D.town_near(CFG, x, z, r)
  if not (x and CFG and CFG.town_info) then return nil end
  local best, bd = nil, r * r
  for sid, t in pairs(CFG.town_info) do
    if t.x then
      local d = (t.x - x) ^ 2 + (t.z - z) ^ 2
      if d < bd or (d == bd and best and sid < best) then best, bd = sid, d end
    end
  end
  return best, best and (CFG.town_info[best].name or best)
end
function D.flush(C, S, c)
  if D.nagg == 0 then return end
  local agg = D.agg
  D.agg, D.nagg = {}, 0
  D.st.flushes = D.st.flushes + 1
  local X = D.state(S)
  local day = math.floor(D.day(C))
  if X.day ~= day then X.day, X.seen, X.npc, X.pl = day, {}, 0, 0 end
  local CFG = C.cfg()
  local pf, known = CFG.player_faction, CFG.factions or {}
  local keys = {}
  for k in pairs(agg) do keys[#keys + 1] = k end
  table.sort(keys)   -- детерминизм (тест, потолки в день)
  local px, pz
  local now = os.clock()
  for sid, e in pairs(D.crime) do if now - e.t > 2 * c.wit_s then D.crime[sid] = nil end end
  for _, key in ipairs(keys) do
    local r = agg[key]
    local bp, tp = r.a == pf, r.b == pf
    local player = bp or tp
    local wit, wsrc, wcr
    if bp and c.witness ~= false and r.top ~= "attacked" and not (c.known_only and not known[r.b]) then
      if not px then px, pz = D.player_pos() end
      wit, wsrc, wcr = D.witness(c, r, pf, px, pz, now)
    elseif tp and c.witness ~= false then
      wit, wsrc = true, "to_player"
    end
    if wit == false and not r.held and now - (r.t1 or now) < c.wit_hold_s and D.nagg < c.max_keys then
      r.held = true   -- свидетель мог заметить чуть позже: одно окно ожидания, потолки и дедупликация не тронуты
      D.agg[key] = r; D.nagg = D.nagg + 1
      D.st.held = D.st.held + 1
    elseif r.top == "attacked" then
      D.st.minor = D.st.minor + 1   -- игрок: уже player_raid / attack_on_player; NPC: стычка без исхода
    elseif c.known_only and not ((bp or known[r.a]) and (tp or known[r.b])) then
      D.st.foreign = D.st.foreign + 1
    else
      local dk = r.a .. "|" .. r.b .. "|" .. r.top .. (wit == false and "|unseen" or "")
      if X.seen[dk] then
        D.st.dup = D.st.dup + 1
      elseif (player and X.pl >= c.player_day) or (not player and X.npc >= c.npc_day) then
        D.st.capped = D.st.capped + 1
      else
        X.seen[dk] = true
        if player then X.pl = X.pl + 1 else X.npc = X.npc + 1 end
        X.tot = (X.tot or 0) + 1
        if not px then px, pz = D.player_pos() end
        local tsid, tname = D.town_near(CFG, px, pz, c.town_r)
        local function nm(fid, en)
          if fid == pf then return "the Nameless" end
          local okn, n = pcall(C.name, fid)
          if okn and n and n ~= fid then return n end
          return en or tostring(fid)
        end
        local an, bn = nm(r.a, r.an), nm(r.b, r.bn)
        local text = string.format(D.TEXT[r.top] or "%s and %s clashed", an, bn)
        text = text:sub(1, 1):upper() .. text:sub(2) .. (tname and (" near " .. tname) or "") .. "."
        local cs = {}
        for kk, v in pairs(r.c) do cs[#cs + 1] = kk .. ":" .. v end
        table.sort(cs)
        local ev = { type = "deed", kind = r.top, tone = r.tone, a = r.a, b = r.b, by_player = bp or nil, to_player = tp or nil,
                     n = r.n, w = math.floor(r.w * 100 + 0.5) / 100, counts = table.concat(cs, " "), aggressive = r.aggr,
                     x = px, z = pz, town_sid = tsid, town_name = tname, text = text,
                     witnessed = wit, witness_src = wsrc and wsrc:match("^%S+") or nil, crime = wcr and D.CRIME[wcr.c] or nil }
        local oke, ee = pcall(C.emit, ev)
        if oke then
          D.st.emitted = D.st.emitted + 1
          D.log(string.format("deed: %s %s %s>%s n=%d %s", r.top, bp and "by_player" or (tp and "to_player" or "npc"), r.a, r.b, r.n, text))
          if bp then
            local sk = wit == true and "wit_yes" or (wit == false and "wit_no" or "wit_nil")
            D.st[sk] = D.st[sk] + 1
            D.log(string.format("witness: %s %s>%s %s src=%s%s", r.top, r.a, r.b, wit == true and "seen" or (wit == false and "unseen" or "unknown"),
                                tostring(wsrc), wcr and (" crime=" .. (D.CRIME[wcr.c] or tostring(wcr.c))) or ""))
          end
        else
          D.log("emit failed: " .. tostring(ee))
        end
      end
    end
  end
end

-- регистрация и тик ---------------------------------------------------------------------------------------------------------
local function guarded(name, fn, flag)   -- сбой колбэка ядра выключает только его (флаг D[flag]); сбой тика — весь модуль
  return function(...)
    if D.off then return end
    if flag and D[flag] then return end
    local ok, err = pcall(fn, ...)
    if not ok then
      if not flag then D.fail(name, err)
      else D[flag] = true; D.log("hook " .. name .. " disabled until restart: " .. tostring(err)) end
    end
  end
end
function D.hooks()   -- колбэк ядра регистрируется из первого тика (не при загрузке файла)
  if D.hooked or not (Events and Events.on) then return end
  D.hooked = true
  local ok, err = pcall(function()
    Events.on("FactionRelations::affectRelations", guarded("affectRelations", function(rels, other, et, mult) D.on_rel(rels, other, et, mult) end, "hook_off"))
  end)
  D.log(ok and "affectRelations hook registered" or ("hook registration failed: " .. tostring(err)))
  local okw, errw = pcall(function()   -- Y1: свидетель преступления (ванильный механизм розыска)
    Events.on("BountyManager::notifyCrimeWitnessed", guarded("notifyCrimeWitnessed", function(bm, fac, who, exp, cr) D.on_crime(bm, fac, who, exp, cr) end, "crime_off"))
  end)
  if not okw then D.crime_off = true end
  D.log(okw and "witness: notifyCrimeWitnessed hook registered" or ("witness: hook registration failed: " .. tostring(errw)))
end
function D.tick()
  if D.off then return end
  local c = D.cfg()
  D.C = c
  if c.enabled == false or os.clock() - D.last < c.tick_s then return end
  D.last = os.clock()
  if not D.hooked then D.hooks() end
  if os.clock() - D.last_flush < c.flush_s then return end
  D.last_flush = os.clock()
  local C = rawget(_G, "KMM_Conductor")
  local S = C and C.state and C.state()
  if type(S) ~= "table" then D.agg, D.nagg = {}, 0; return end   -- мира ещё нет: окно не копим
  D.flush(C, S, c)
end
function D.gov_tick()
  local G = rawget(_G, "KMM_Gov")
  if G and G.run then return G.run("deeds", D.tick) end
  return D.tick()
end

KMM_Deeds = {
  stats = function() local o = {}; for k, v in pairs(D.st) do o[k] = v end; o.pending = D.nagg; return o end,
  disabled = function()
    if D.off then return { deeds = true } end
    local o = {}
    if D.hook_off then o.deeds_hook = true end
    if D.crime_off then o.deeds_witness = true end
    return o
  end,
  crime_seen = function(fid, within_s)   -- Y1: ядро заметило преступление игрока против fid за within_s секунд -> имя преступления или nil
    local e = fid and D.crime[fid]
    if e and os.clock() - e.t <= (tonumber(within_s) or D.DEF.wit_s) then return D.CRIME[e.c] or tostring(e.c) end
  end,
  today = function() local C = rawget(_G, "KMM_Conductor"); local S = C and C.state and C.state(); return S and D.state(S) end,
  on_rel = function(rels, other, et, mult) return D.on_rel(rels, other, et, mult) end,   -- офлайн-тест
  on_crime = function(bm, fac, who, exp, cr) return D.on_crime(bm, fac, who, exp, cr) end,   -- офлайн-тест
  _tick = function() D.last, D.last_flush = -1000, -1000; D.tick() end,
  _D = D,
}
if Events and Events.on then pcall(function() Events.on("GameWorld::charsUpdate", guarded("tick", function() D.gov_tick() end)) end) end
