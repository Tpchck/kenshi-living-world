-- KMM_Diplo — дипломатия игрока через диалоги (поток DIPLO, 2026-11-12).
-- Разговор «KMM Diplomacy» (данные KMM_Diplo.mod) есть у лидеров, дипломатов и главарей фракций и открыт, пока у
-- говорящего персонажа игрока «Envoy's Seal». Канал диалог → Lua: мост диалогов KenshiLua («run lua script» на репликах
-- → scripts/dialogue/kmm_diplo_line.lua → KMM_Diplo.on_line). Решение фракции — оценка интереса по состоянию дирижёра
-- (сила, отношения, доверие, угрозы, общий враг, голод/бедность, богатство игрока, текущие договоры, амбиция).
-- Ответ — следующей репликой: Lua выдаёт игроку жетон (accept / counter_s / counter_l / refuse), ответы фракции стоят на
-- условии «target has item». Если мост не сработал — NPC отвечает «изложите письменно» и даёт письмо-предмет; такт находит
-- письмо, решает, и ответ приходит сообщением + слухом (хроника дирижёра).
-- Договор заключает дирижёр (KMM_Conductor.player_sign/… — патч в docs/streams/DIPLO.md); без патча — тот же договор
-- пишется прямо в состояние дирижёра (запасной путь).
-- Безотказность: ленивый старт после появления персонажей игрока, хуков загрузки нет; каждая функция в pcall, первая
-- ошибка отключает только её до конца сессии, причина → C:/KenshiModMap/logs/debug.log.
-- S4 (условия мира): перехват Dialogue::_checkCondition (Override, регистрируется в init) отвечает на ОДНО зарезервированное
-- условие данных (DC_FACTION_VARIABLE «KMM_WORLD» = base+код) чтением таблицы WV[код] — O(1), без вызовов движка; всё прочее → nil
-- (ваниль). WV наполняет такт раз в world_refresh_seconds: город, где стоит отряд игрока (голод/изобилие склада, осада KMM_Stock,
-- беспорядки/опустение/хозяин из KMM_Conductor.town_mood и модели отношений), прозвище и соперники (KMM_Nemesis) — только чтение.
-- Коды разговора посланника (договор, дань, решение) ставит мост реплик — вместо жетонов, пока перехват жив; перехват молчит,
-- отключён или ответ по условию не прозвучал (реплика «изложите письменно») → прежние жетоны-предметы.
-- Соперникам (живые отряды KMM_Outlaws с pg) в рантайме добавляется разговор-угроза: Dialogue:addConversation(DIALOGUE, EV).
-- X3 (пакет 6, вызов на поединок): лидерам отрядов-конкурентов (главари KMM_Outlaws и соперники Nemesis, герои KMM_Fates, rival-отряды Q1
-- рядом с игроком по снимку KMM_Gov) в рантайме добавляется разговор вызова (EV_PLAYER_TALK_TO_ME), открыт по коду duel_open.
-- Ответ лидера (duel_accept / duel_refuse) решает Lua: кулдаун на лидера и трус (лидер намного слабее вызвавшего по общему навыку ядра).
-- Принятие — ванильные эффекты данных DA_FLAG_TEMP_ENEMY + DA_ATTACK_CHASE_FOREVER: временная вражда без войны фракций.
-- Такт (раз в секунду, только при активном поединке) смотрит isDead/isDown/isUnconcious лидера и вызвавшего: победа / убийство /
-- поражение / ничья / снят (таймаут, разошлись, указатель не читается). После исхода вражда снимается ванильным
-- Character:clearTempEnemyStatus в обе стороны (при поражении через duel_loot_s, чтобы победитель успел ограбить по-ванильному).
-- Рост навыка — ванильная кривая XP за разницу навыков во время боя (CONSTANTS, KMM_Fix), своей прокачки нет. Репутация — слух:
-- событие шины nemesis_duel_* / outlaw_duel_* / fate_duel_* (префиксы, которые читает KMM_Rumors). Пока идёт поединок и duel_spare_s
-- после, событие дирижёра player_raid против фракции лидера не рвёт договоры игрока. Маркеры: DUEL offer / ask / start / end / clear.
-- Ревью batch6 X3: амнистия фракции конечна (spare_until <= таймаут + грабёж + пощада) и снимается при любом сбросе поединка (X3.drop:
-- смена мира, загрузка сейва, ошибка такта); персонажи поединка — handle (hand:isValid/getCharacter перед каждым тактом); вражда
-- снимается со всего отряда лидера (снимок KMM_Gov по ключу платуна) + reThinkCurrentAIAction; в городе лидер отказывается;
-- Q1-отряды — только шаблоны rivals.json (не торговцы, не в городе, без Mercenary Guild); разговор — один на лидера (ключ hand:toString,
-- перед addConversation проверка Dialogue:getConversationList(EV).conversationChoices).

local TAG = "[KMM_Diplo] "
local ITEM_TYPE = 4          -- itemType.ITEM
local T_TARGET = 1           -- TalkerEnum.T_TARGET
local TREATY_OF = { nonaggression = "nonaggression", trade = "trade", fealty = "vassal", submission = "vassal" }
local TOKEN_KEYS = { "accept", "refuse", "counter_s", "counter_l", "liege_due", "vassal_due", "has_pact" }
local KIND_TEXT = { nonaggression = "non-aggression pact", trade = "trade agreement", alliance = "alliance", fealty = "oath of fealty",
                    submission = "demand of submission", tribute = "demand for tribute" }

local D, P, C, CFG            -- данные (kmm_diplo_data.lua), их params, API дирижёра, его конфиг
local DISABLED = {}
local CUR = nil               -- текущий разговор: { npc, pc, fid, at }
local PENDING = nil           -- последнее решение: { fid, kind, outcome, ttype, U, why, at }
local QUEUE = {}              -- подтверждённые исходы → применяются в такте
local GIVEN = {}              -- выданные жетоны: { pc, key, at }
local stats = { decisions = 0, applied = 0, letters = 0, tokens = 0, by_outcome = {} }
-- S4: перехват условий. WV[код] = true/false — единственное, что читает горячий путь.
local WV = {}
local HK = { on = false, live = false, reg = false, cond = -1, lo = 1, hi = 0, base = 0, n = 0, fail = 0, asked = {}, logged = {},
             calls = 0, cond_n = 0, ctype = nil, vtype = nil, stat_sig = nil, stat_t = -1e9,   -- B1: счётчики перехвата для debug.log
             sig = nil, town = nil, owner0 = nil, gd_rival = nil, rivals = {}, rival_n = 0, world = nil,
             stale = setmetatable({}, { __mode = "k" }) }
local CONV_CODES = { "has_pact", "liege_due", "vassal_due", "dec_accept", "dec_refuse", "dec_counter_s", "dec_counter_l" }
-- X3: поединок. dk: хендл лидера → запись; keys: ключи отрядов, которым разговор уже добавлен (за сессию); cur: активный поединок
local X3 = { dk = {}, keys = {}, cur = nil, ask = nil, world = nil, gd = nil, stale = HK.stale,   -- stale общий с разговором-угрозой: битый Platoon* не трогаем дважды
             spare_fid = nil, spare_until = -1, stats = { offers = 0, asks = 0, starts = 0, won = 0, lost = 0, void = 0, spared = 0 } }
local WORLD_CODES = { "town_hungry", "town_plenty", "town_siege", "town_unrest", "town_emptied", "owner_hostile", "owner_captured",
                      "player_title", "rival_alive", "rival_here" }

local function log(msg) msg = TAG .. tostring(msg); if not (KenshiLua and pcall(function() KenshiLua.log(msg) end)) then print(msg) end end
local function dlog(msg)
  local path = (P and P.debug_log) or "C:/KenshiModMap/logs/debug.log"
  local ok, f = pcall(io.open, path, "a")
  if ok and f then f:write(os.date("%Y-%m-%d %H:%M:%S"), " [KMM_Diplo] ", tostring(msg), "\n"); f:close() end
  log(msg)
end
local function guarded(nm, fn)
  return function(...)
    if DISABLED[nm] then return end
    local ok, r = pcall(fn, ...)
    if not ok then DISABLED[nm] = true; dlog(nm .. " disabled until restart: " .. tostring(r)); return nil end
    return r
  end
end
local function clamp(x, a, b) if x < a then return a elseif x > b then return b end return x end

---------------------------------------------------------------------------------------------- данные и дирижёр
local function load_data()
  local ok, d = pcall(require, "kmm_diplo_data")
  if ok and type(d) == "table" then return d end
  for _, p in ipairs({ "C:/Program Files (x86)/Steam/steamapps/common/Kenshi/mods/KMM_Diplo/scripts/kmm_diplo_data.lua",
                       "C:/KenshiModMap/build/KMM_Diplo/scripts/kmm_diplo_data.lua" }) do
    local f = loadfile(p)
    if f then local ok2, d2 = pcall(f); if ok2 and type(d2) == "table" then return d2 end end
  end
  return nil
end
local function conductor()
  local c = (_G and rawget(_G, "KMM_Conductor")) or KMM_Conductor
  if c and c.state and c.cfg then return c end
  return nil
end
local function S() return C and C.state() end
local function DS()   -- своё состояние внутри состояния дирижёра: едет в его сейве
  local s = S()
  if not s then return nil end
  s.diplo = s.diplo or { cool = {}, asked = {}, due = {}, last_ev = 0 }
  return s.diplo
end
local function PF() return CFG and CFG.player_faction end
local function fname(fid) local f = CFG and CFG.factions and CFG.factions[fid]; return f and f.name or tostring(fid) end
local function day() local s = S(); return (s and s.last_day and s.last_day >= 0) and s.last_day or 0 end

---------------------------------------------------------------------------------------------- чтение состояния
local function rel(s, a, b) return (s.rel[a] and s.rel[a][b]) or 0 end
local function trust(s, a, b) local f = s.F[a]; return (f and f.trust and f.trust[b]) or 0 end
local function power(s, cfg, fid)
  local f = s.F[fid]
  if not f or not f.alive then return 0 end
  local m = (f.mode == "mobilized") and ((cfg.params.relic or {}).mobilized_strength_mult or 1.6) or 1
  return (f.strength or 0) * m
end
local function treaty_between(s, a, b, ttype)
  for _, t in pairs(s.treaties) do
    if t.active and ((t.a == a and t.b == b) or (t.a == b and t.b == a)) and (not ttype or t.type == ttype) then return t end
  end
end
local function ntowns(f) local n = 0; for _ in pairs(f.towns or {}) do n = n + 1 end; return n end

---------------------------------------------------------------------------------------------- оценка интереса (чистая функция)
-- ctx = { pf, nchars, money, day, asked = n запросов этого вида в кулдауне, jitter = число }
local function evaluate(s, cfg, prm, fid, kind, ctx)
  local pf = ctx.pf
  local F = s.F[fid]
  if not (F and F.alive) or fid == pf or not s.F[pf] then return "refuse", -1, "no such power", nil end
  local r, tr = rel(s, fid, pf), trust(s, fid, pf)
  local fp = power(s, cfg, fid)
  local pp = math.max(power(s, cfg, pf), (ctx.nchars or 1) * (prm.player_power_per_char or 4))
  local ratio = fp / math.max(1, pp)
  local radius = ((cfg.params.bus or {}).radius or 120000) * 1.5
  local thr = 0
  for _, e in ipairs((cfg.factions[fid] or {}).near or {}) do
    local o = e[1]
    if e[2] <= radius and o ~= pf and s.F[o] and s.F[o].alive and rel(s, fid, o) <= -30 and power(s, cfg, o) > fp then
      thr = thr + power(s, cfg, o) / math.max(1, fp)
    end
  end
  local ncommon, conflict = 0, 0
  for x, X in pairs(s.F) do
    if X.alive and x ~= fid and x ~= pf and rel(s, fid, x) <= -50 and rel(s, pf, x) <= -50 then ncommon = ncommon + 1 end
  end
  for _, t in pairs(s.treaties) do   -- союз/пакт/вассалитет фракции с врагом игрока
    if t.active and (t.type == "defense" or t.type == "military" or t.type == "vassal") and (t.a == fid or t.b == fid) then
      local o = (t.a == fid) and t.b or t.a
      if o ~= pf and rel(s, pf, o) <= -50 then conflict = 1 end
    end
  end
  local amb = F.relic and "faith" or (F.ambition or "survival")
  local R, T = r / 100, tr / 100
  local x = {
    rel = R, trust = T,
    weak = clamp((1 / math.max(0.01, ratio) - 1) / 2, 0, 1),     -- они слабее игрока
    strong = clamp((ratio - 1) / 3, 0, 1),                         -- они сильнее
    threat = clamp(thr / 3, 0, 1),
    common = math.min(1, ncommon / 2),
    poor = clamp(1 - (F.wealth or 0) / math.max(1, F.wealth0 or 1), 0, 1),
    hungry = clamp(F.hunger or 0, 0, 1),
    metal = clamp((F.stress or 0) - 1, 0, 1),
    richp = clamp((ctx.money or 0) / (prm.rich_player_cats or 20000), 0, 1),
    crisis = F.succession and 1 or 0,
    aggressive = (amb == "expansion" or amb == "revenge") and 1 or 0,
    greedy = (amb == "enrichment" or amb == "expansion") and 1 or 0,
    focus = (F.relic and F.mode ~= "mobilized") and 1 or 0,
    relic = F.relic and 1 or 0,
    conflict = conflict,
  }
  local W, base
  if kind == "nonaggression" then
    base = 0.30 - ((r <= -60) and 0.25 or 0)
    W = { rel = 0.35, trust = 0.20, threat = 0.30, weak = 0.30, common = 0.15, crisis = 0.15, strong = -0.25 * (0.5 + 0.5 * x.aggressive) }
  elseif kind == "trade" then
    base = 0.25 + ((amb == "enrichment") and 0.15 or 0) - ((r <= -30) and 0.5 or 0)
    W = { rel = 0.30, trust = 0.15, poor = 0.25, hungry = 0.25, metal = 0.15, richp = 0.25, focus = -0.20 }
  elseif kind == "alliance" then
    base = -0.15 - ((r < 10) and 0.40 or 0)
    W = { rel = 0.45, trust = 0.25, common = 0.40, threat = 0.25, weak = 0.10, conflict = -0.40, focus = -0.25 }
  elseif kind == "fealty" then         -- игрок просится в вассалы
    base = 0.10
    W = { rel = 0.25, trust = 0.15, strong = 0.35, greedy = 0.15, weak = -0.30, conflict = -0.30 }
  elseif kind == "submission" then     -- игрок требует покорности
    base = -0.45 - ((ntowns(F) > (prm.max_towns_submit or 2)) and 0.5 or 0)
    W = { weak = 0.85, threat = 0.35, rel = 0.15, crisis = 0.15, aggressive = -0.25, relic = -0.35 }
  elseif kind == "tribute" then        -- разовая дань игроку
    base = -0.35 - 0.20 * math.max(0, -R)
    W = { weak = 0.80, threat = 0.25, crisis = 0.10, poor = -0.25, aggressive = -0.20 }
  else
    return "refuse", -1, "unknown proposal", nil
  end
  local U, parts = base, {}
  for k, w in pairs(W) do
    local c = w * (x[k] or 0)
    U = U + c
    if c ~= 0 then parts[#parts + 1] = { k, c } end
  end
  U = U - (prm.pester_penalty or 0.12) * (ctx.asked or 0) + (ctx.jitter or 0)
  table.sort(parts, function(a, b) if math.abs(a[2]) ~= math.abs(b[2]) then return math.abs(a[2]) > math.abs(b[2]) end return a[1] < b[1] end)
  local why = {}
  for i = 1, math.min(3, #parts) do why[#why + 1] = string.format("%s%+.2f", parts[i][1], parts[i][2]) end
  why = table.concat(why, " ")
  local ttype = TREATY_OF[kind]
  if kind == "alliance" then ttype = (r >= 40) and "military" or "defense" end
  if ttype then   -- уже есть такой договор — подтверждаем (продление срока)
    local t = treaty_between(s, fid, pf, ttype)
    if t and (kind ~= "fealty" or t.a == fid) and (kind ~= "submission" or t.a == pf) then return "accept", U, "already bound", ttype end
  end
  if U >= (prm.accept or 0.55) then return "accept", U, why, ttype end
  if (D and D.counter_kinds or {})[kind] and U >= (prm.counter or 0.32) then
    local tier = ((prm.accept or 0.55) - U <= (prm.counter_large_gap or 0.12)) and "counter_s" or "counter_l"
    return tier, U, why, ttype
  end
  return "refuse", U, why, ttype
end

---------------------------------------------------------------------------------------------- движок игры: персонажи и предметы
local function player_chars()
  local out = {}
  pcall(function() for _, c in pairs(getPlayerInterface():getAllPlayerCharacters()) do out[#out + 1] = c end end)
  return out
end
local function is_player(ch) local ok, v = pcall(function() return ch:isPlayerCharacter() end); return ok and v end
local function fid_of(ch)
  local f = ch:getFaction(); local gd = f and (f:getData() or f.data)
  return gd and gd.stringID
end
local function sid_of(ch) local gd = ch:getGameData(); return gd and gd.stringID end
local function pos(ch) local p = ch:getPosition(); return p.x or p[1], p.z or p[3] end
local function dist(a, b) local ax, az = pos(a); local bx, bz = pos(b); return math.sqrt((ax - bx) ^ 2 + (az - bz) ^ 2) end
local GD = {}
local function gd_item(sid)
  if not GD[sid] then
    GD[sid] = getGameWorld().gamedata:getData(sid, ITEM_TYPE)
    if not GD[sid] then error("getData(ITEM) nil for " .. tostring(sid)) end
  end
  return GD[sid]
end
local function has_item(ch, sid) return ch:getInventory():getItem(gd_item(sid)) ~= nil end
local function give_item(ch, sid)
  local item = getGameWorld().theFactory:createItem(gd_item(sid), nil, nil, nil, -1, nil)
  if not item then error("createItem nil for " .. sid) end
  return ch:getInventory():addItem(item, 1, false, true)
end
local function take_item(ch, sid)
  local inv, n = ch:getInventory(), 0
  for _ = 1, 5 do
    local it = inv:getItem(gd_item(sid))
    if not it then break end
    inv:removeItemAutoDestroy(it, 1); n = n + 1
  end
  return n
end
local function clear_tokens(ch)
  for _, k in ipairs(TOKEN_KEYS) do take_item(ch, D.items[k]) end
end
local function give_token(ch, key)
  give_item(ch, D.items[key])
  GIVEN[#GIVEN + 1] = { pc = ch, key = key, at = os.clock() }
  stats.tokens = stats.tokens + 1
end
-- деньги игрока: у PlayerInterface нет getOwnerships (BindingsReference) — берём у живого персонажа игрока:
-- Character:getOwnerships():getMoney(), затем Character:getMoney(), затем Platoon:getOwnerships() его платуна (как KMM_Nemesis.worth)
local function player_money()
  for _, pc in ipairs(player_chars()) do
    local okd, dead = pcall(function() return pc:isDead() end)
    if not (okd and dead == true) then
      for _, get in ipairs({ function() return pc:getOwnerships():getMoney() end, function() return pc:getMoney() end,
                             function() return pc:getPlatoon().me:getOwnerships():getMoney() end }) do
        local ok, m = pcall(get)
        if ok and type(m) == "number" and m == m then return m end
      end
    end
  end
  return 0
end

---------------------------------------------------------------------------------------------- S4: условия мира
local DIALOGUE_TYPE = 18     -- itemType.DIALOGUE
local function code_of(name) return D and D.world and D.world.codes and D.world.codes[name] end
local function wset(name, v) local c = code_of(name); if c then WV[c] = v and true or false end end
local function cond_mode() return HK.on and HK.live and not DISABLED.cond and HK.fail < ((P and P.cond_fail_max) or 1) end
local function conv_clear(dec_only)
  for _, k in ipairs(CONV_CODES) do if not dec_only or k:sub(1, 4) == "dec_" then wset(k, false) end end
end
local function code_name(c)
  for k, v in pairs((D and D.world and D.world.codes) or {}) do if v == c then return k end end
  return "?"
end

-- горячий путь (каждая проверка условия у каждого говорящего): только сравнения и чтение WV, без вызовов движка
local function on_check(_, cname, _, val)
  HK.live = true
  HK.calls = HK.calls + 1
  if type(cname) ~= "number" then   -- биндинги обещают целое (BindingsReference «Enums»); иначе — запомнить тип для отчёта и попробовать число
    HK.ctype = HK.ctype or type(cname)
    cname = tonumber(cname)
  end
  if type(val) ~= "number" then HK.vtype = HK.vtype or type(val); val = tonumber(val) end
  if cname == HK.cond then HK.cond_n = HK.cond_n + 1 end   -- условие DC_FACTION_VARIABLE вообще проверяется (любое значение)
  if cname ~= HK.cond or type(val) ~= "number" or val < HK.lo or val > HK.hi then return nil end
  local c = val - HK.base
  HK.n = HK.n + 1
  if HK.asked[c] == nil then HK.asked[c] = (WV[c] == true) end
  return WV[c] == true
end

local function hook_register()   -- из init: таблица кодов из данных, перехват — один раз за сессию
  local w = D.world
  if not (w and w.codes and w.cond and w.base) or P.world_conditions == false then return end
  local mx = 0
  for _, c in pairs(w.codes) do if c > mx then mx = c end end
  HK.cond, HK.base, HK.lo, HK.hi = w.cond, w.base, w.base + 1, w.base + mx
  HK.owner0 = {}
  for fid, f in pairs(CFG.factions or {}) do
    for k, v in pairs(f.towns or {}) do HK.owner0[(type(k) == "number") and v or k] = fid end
  end
  HK.on = true
  if not HK.reg and Events and Events.on then
    Events.on("Dialogue::_checkCondition", guarded("cond", on_check))
    HK.reg = true
    dlog(string.format("DIPLO_COND hook registered: condition %d, codes %d..%d", HK.cond, HK.lo, HK.hi))
  end
end

local function player_town()
  local pcs = player_chars()
  for i = 1, math.min(#pcs, 8) do
    local ok, t = pcall(function() local tw = pcs[i]:getCurrentTownLocation(); local gd = tw and (tw:getGameData() or tw.data); return gd and gd.stringID end)
    if ok and t then return t end
  end
  return nil
end

local function world_refresh()   -- раз в world_refresh_seconds: состояние мира → WV (только чтение чужих модулей)
  if not HK.on then return end
  local s, pf = S(), PF()
  if not (s and pf) then return end
  local f = {}
  local tsid = player_town()
  if tsid then
    local mood = {}
    if C.town_mood then local ok, m = pcall(C.town_mood, tsid); if ok and type(m) == "table" then mood = m end end
    local food, siege = mood.food, false
    local K = rawget(_G, "KMM_Stock")
    if type(K) == "table" then
      if K.stock then local ok, st = pcall(K.stock, tsid); if ok and type(st) == "table" then siege = st.siege and true or false end end
      if food == nil and K.level then local ok, v = pcall(K.level, tsid, "food"); if ok and type(v) == "number" then food = v end end
    end
    if type(food) == "number" and food == food then
      f.town_hungry = food < (P.hungry_food or 0.5)
      f.town_plenty = food >= (P.plenty_food or 1.6)
    end
    f.town_siege = siege
    f.town_unrest = (tonumber(mood.unrest) or 0) >= (P.unrest_level or 0.5)
    if type(mood.pop) == "number" and type(mood.pop0) == "number" and mood.pop0 > 0 then f.town_emptied = mood.pop / mood.pop0 < (P.emptied_pop or 0.6) end
    local owner = mood.owner
    if owner and owner ~= pf then
      local r = (C.rel and C.rel(owner, pf)) or rel(s, owner, pf)
      f.owner_hostile = r <= (P.hostile_rel or -40)
    end
    local o0 = HK.owner0 and HK.owner0[tsid]
    f.owner_captured = owner ~= nil and o0 ~= nil and owner ~= o0
  end
  local NM = rawget(_G, "KMM_Nemesis")
  if type(NM) == "table" then
    if NM.player_title then local ok, t = pcall(NM.player_title); f.player_title = ok and t ~= nil and t ~= false end
    if NM.rivals then
      local ok, rv = pcall(NM.rivals)
      if ok and type(rv) == "table" then
        f.rival_alive = #rv > 0
        if tsid then for _, o in ipairs(rv) do if o.s == tsid then f.rival_here = true; break end end end
      end
    end
  end
  wset("duel_open", X3.cur == nil and P.duel ~= false and not DISABLED.duel_step)
  local on = {}
  for _, k in ipairs(WORLD_CODES) do wset(k, f[k]); if f[k] then on[#on + 1] = k end end
  local sig = tostring(tsid) .. "|" .. table.concat(on, ",")
  if sig ~= HK.sig then
    HK.sig = sig
    local ti = tsid and CFG.town_info and CFG.town_info[tsid]
    -- B1: в debug.log (dlog), а не только в KenshiLua.log: тот перезаписывается при каждом запуске игры, и session_report его не читает
    dlog(string.format("DIPLO_WORLD town=%s flags=%s", tsid and ((ti and ti.name) or tsid) or "none", (#on > 0) and table.concat(on, ",") or "-"))
  end
  if HK.live and not HK.logged.live then HK.logged.live = true; dlog("DIPLO_COND hook live: reserved world codes answered by table; envoy tokens off") end
  for c, a in pairs(HK.asked) do
    if not HK.logged[c] then HK.logged[c] = true; dlog(string.format("DIPLO_COND asked %s (code %d) -> %s", code_name(c), c, tostring(a))) end
  end
  -- B1: счётчики перехвата — отличить «условие мира не доходит до проверки» (reserved=0 при calls>0) от «тип аргумента не тот»
  local nowS = os.clock()
  local ssig = string.format("%d|%d|%s|%s", HK.cond_n > 0 and 1 or 0, HK.n > 0 and 1 or 0, tostring(HK.ctype), tostring(HK.vtype))
  if HK.live and (ssig ~= HK.stat_sig or nowS - HK.stat_t >= ((P and P.cond_stats_seconds) or 600)) then
    HK.stat_sig, HK.stat_t = ssig, nowS
    local na = 0; for _ in pairs(HK.asked) do na = na + 1 end
    dlog(string.format("DIPLO_COND stats: calls=%d cond6=%d reserved=%d asked_codes=%d cname_type=%s val_type=%s", HK.calls, HK.cond_n, HK.n, na,
      HK.ctype or "number", HK.vtype or "number"))
  end
  local now = os.clock()   -- коды разговора не переживают разговор
  if PENDING and now - PENDING.at > (P.token_ttl_seconds or 90) then conv_clear(true) end
  if CUR and now - CUR.at > 600 then conv_clear(); CUR = nil end
end

local function rival_talk()   -- живой отряд соперника → его главарю ванильный разговор-угроза (FCS-реплики с условиями мира)
  local w = D.world
  if not (HK.on and w and w.rival_dialogue) then return end
  local O_ = rawget(_G, "KMM_Outlaws")
  if not (type(O_) == "table" and O_.live and O_.state) then return end
  local okl, live = pcall(O_.live)
  local oks, O = pcall(O_.state)
  if not (okl and oks and type(live) == "table" and type(O) == "table" and type(O.L) == "table") then return end
  local s = S()
  if HK.world ~= s then   -- загружен другой мир: отряды прошлого (их Platoon* — освобождённая память) больше не трогаем
    if HK.world ~= nil then
      for _, lv in pairs(live) do if type(lv) == "table" then HK.stale[lv] = true end end
      log("DIPLO_RIVAL world changed: rival talk keys reset")
    end
    HK.world, HK.rivals, HK.gd_rival = s, {}, nil
  end
  for id, lv in pairs(live) do
    local o = O.L[id]
    if o and o.pg and o.st == "a" and type(lv) == "table" and lv.pl and not HK.stale[lv] then
      local key = tostring(id) .. "|" .. tostring(o.pk or o.n)   -- стабильный ключ записи, а не таблица lv (новая при каждом подхвате)
      if not HK.rivals[key] then
        local okg, leader = pcall(function() return lv.pl:getSquadLeader() end)
        if not okg then HK.stale[lv] = true; log("DIPLO_RIVAL skip " .. tostring(o.n) .. ": " .. tostring(leader))
        elseif leader then
          if not HK.gd_rival then
            HK.gd_rival = getGameWorld().gamedata:getData(w.rival_dialogue, DIALOGUE_TYPE)
            if not HK.gd_rival then error("getData(DIALOGUE) nil for " .. tostring(w.rival_dialogue)) end
          end
          local oka, err = pcall(function()
            local dl = leader.dialogue
            for _, e in ipairs(w.rival_events or { 66 }) do dl:addConversation(HK.gd_rival, e) end
          end)
          HK.rivals[key] = true   -- и при ошибке: не повторять каждые 4 с
          if oka then
            HK.rival_n = HK.rival_n + 1
            log(string.format("DIPLO_RIVAL threat talk added: %s", tostring(o.n)))
          else
            log("DIPLO_RIVAL addConversation failed for " .. tostring(o.n) .. ": " .. tostring(err))
          end
        end
      end
    end
  end
end

---------------------------------------------------------------------------------------------- применение исходов (через дирижёр)
-- все записи — через API дирижёра (KMM_Conductor.lua: emit/add_rel/add_trust_one/player_sign/player_break); без него init() не стартует
local function emit(ev) return C.emit(ev) end   -- шина, хроника → слухи
local function add_rel(a, b, dv) return C.add_rel(a, b, dv) end
local function add_trust(a, b, dv) return C.add_trust_one(a, b, dv) end   -- одностороннее: как a доверяет b
local function sign(fid, ttype, why, player_is_suzerain) return C.player_sign(fid, ttype, why, player_is_suzerain) end
local function break_all(fid, why, by_player) return C.player_break(fid, why, by_player) end
local function message(text) pcall(function() getGameWorld():showPlayerAMessage_withLog(text, true) end); log("message: " .. text) end

local function apply(q)
  local pf, ds = PF(), DS()
  local fid, kind, out = q.fid, q.kind, q.outcome
  if not (fid and pf and S().F[fid]) then return end
  local key = fid .. "|" .. tostring(kind)
  local wealth_k = (P.cats_per_wealth or 100)
  stats.applied = stats.applied + 1
  stats.by_outcome[out] = (stats.by_outcome[out] or 0) + 1
  if (out == "accept" or out == "paid") and (TREATY_OF[kind] or kind == "alliance") then
    local ttype = q.ttype or TREATY_OF[kind] or "defense"
    local t = sign(fid, ttype, out == "paid" and "terms paid by the envoy" or "envoy of the Nameless", kind == "submission")
    if t and ttype == "vassal" then ds.due[t.id] = { next = day() + (P.tribute_period_days or 30) } end
    if out == "paid" then
      add_rel(fid, pf, P.rel_on_paid_counter or 5)
      S().F[fid].wealth = (S().F[fid].wealth or 0) + (q.cats or 0) / wealth_k
    end
    ds.asked[key] = nil
    message(string.format("%s agreed to the %s.", fname(fid), KIND_TEXT[kind] or kind))
  elseif out == "accept" and kind == "tribute" then
    local amount = (D.money.demand_tribute or 0) / wealth_k
    local F = S().F[fid]
    F.wealth = math.max(0, (F.wealth or 0) - amount)
    if S().F[pf] then S().F[pf].wealth = (S().F[pf].wealth or 0) + amount end
    add_rel(fid, pf, P.rel_on_accept_demand or -5)
    add_trust(fid, pf, P.trust_on_accept_demand or -10)
    ds.cool[key] = day()
    emit({ type = "tribute_paid", a = fid, b = pf, text = string.format("%s paid tribute to the Nameless rather than fight.", fname(fid)) })
  elseif out == "refuse" or out == "declined" then
    ds.cool[key] = day()
    ds.asked[key] = (ds.asked[key] or 0) + 1
    if out == "refuse" and (kind == "submission" or kind == "tribute") then add_rel(fid, pf, P.rel_on_refuse_demand or -10) end
    if out == "refuse" and q.async then message(string.format("%s rejected your %s.", fname(fid), KIND_TEXT[kind] or kind)) end
  elseif out == "counter_s" or out == "counter_l" then   -- только асинхронно (письмо): платить — у посланника, через разговор
    ds.cool[key] = nil
    message(string.format("%s answered your %s: it can be done, for %d cats. Speak to their envoy again.", fname(fid), KIND_TEXT[kind] or kind,
      out == "counter_s" and D.money.counter_small or D.money.counter_large))
  elseif out == "paid" and kind == "liege_tribute" then
    local t = treaty_between(S(), fid, pf, "vassal")
    if t then ds.due[t.id] = { next = day() + (P.tribute_period_days or 30) } end
    add_rel(fid, pf, P.rel_on_tribute_paid or 3)
    add_trust(fid, pf, P.trust_on_tribute_paid or 5)
    S().F[fid].wealth = (S().F[fid].wealth or 0) + (q.cats or 0) / wealth_k
  elseif out == "collected" and kind == "vassal_tribute" then
    local t = treaty_between(S(), fid, pf, "vassal")
    if t then ds.due[t.id] = { next = day() + (P.tribute_period_days or 30) } end
    local F = S().F[fid]
    F.wealth = math.max(0, (F.wealth or 0) - (q.cats or 0) / wealth_k)
  elseif out == "renounce" then
    local n = break_all(fid, "renounced by the Nameless", false)
    if n > 0 then add_trust(fid, pf, P.trust_on_renounce or -20); add_rel(fid, pf, -10) end
    message(string.format("You renounced %d pact(s) with %s.", n, fname(fid)))
  end
end

---------------------------------------------------------------------------------------------- решение по предложению
local function decide(fid, kind)
  local s, ds = S(), DS()
  if not (s and ds) then return "refuse", -1, "conductor not ready", nil end
  local key = fid .. "|" .. kind
  local asked = 0
  if ds.cool[key] and day() - ds.cool[key] < (P.refuse_cooldown_days or 10) then asked = (ds.asked[key] or 1) end
  local nchars = #player_chars()
  local j = (P.jitter or 0) > 0 and (math.random() * 2 - 1) * P.jitter or 0
  local out, U, why, ttype = evaluate(s, CFG, P, fid, kind, { pf = PF(), nchars = math.max(1, nchars), money = player_money(), day = day(), asked = asked, jitter = j })
  stats.decisions = stats.decisions + 1
  dlog(string.format("decision %s (%s) %s → %s U=%.2f [%s]", fname(fid), tostring(fid), kind, out, U, why))
  return out, U, why, ttype
end

---------------------------------------------------------------------------------------------- X3: вызов на поединок
local function hstr(ch) local ok, h = pcall(function() local hd = ch:getHandle(); return hd and hd:toString() end); return (ok and type(h) == "string") and h or nil end
local function handle_of(ch) local ok, h = pcall(function() return ch:getHandle() end); return ok and h or nil end
local function fresh(hd) local ok, c = pcall(function() if hd and hd:isValid() then return hd:getCharacter() end end); return ok and c or nil end
local function pkey_of(ch)   -- ключ платуна (как f_plat в KMM_Gov): по нему отряд лидера ищется в свежем снимке
  local ok, k = pcall(function() local ap = ch:getPlatoon(); local me = ap and (ap.me or ap); return me and me:getPlatoonStringID() end)
  return (ok and type(k) == "string" and k ~= "") and k or nil
end
local function in_town(ch) local ok, t = pcall(function() return ch:getCurrentTownLocation() end); return ok and t ~= nil end
local function down_of(ch)   -- nil — стоит; "down" — нокаут; "dead"; "gone" — указатель не читается
  local ok, v = pcall(function()
    if ch:isDead() then return "dead" end
    if ch:isDown() or ch:isUnconcious() then return "down" end
    return false
  end)
  if not ok then return "gone" end
  return v or nil
end
local function skill_of(ch) local ok, v = pcall(function() return ch:getStats():getOverallSkillLevel_0_100() end); return (ok and type(v) == "number") and v or nil end
local function name_of(ch) local ok, v = pcall(function() return ch:getName() end); return (ok and type(v) == "string" and v ~= "") and v or nil end
local function duel_ds() local ds = DS(); if not ds then return nil end; ds.duel = ds.duel or { cd = {} }; return ds.duel end
local function duel_codes_clear() wset("duel_accept", false); wset("duel_refuse", false) end

function X3.drop(why)   -- любой сброс поединка: вместе с ним снимается и амнистия фракции (KC.duel больше не пропускает удары)
  if X3.cur and why then log("DUEL dropped: " .. why) end
  X3.cur, X3.ask, X3.spare_fid, X3.spare_until = nil, nil, nil, -1
end

function X3.has_conv(dl, e)   -- разговор вызова уже в списке события (добавлен в этой сессии или пришёл из сейва)
  local lst = dl:getConversationList(e)
  if not lst then return false end
  local sid = X3.gd.stringID
  for _, ln in ipairs(lst.conversationChoices) do
    local g = ln and ln.data
    if g ~= nil and (g == X3.gd or (sid ~= nil and g.stringID == sid)) then return true end
  end
  return false
end

function X3.offer(leader, key, rec)   -- разговор вызова лидеру: один ключ на лидера (hand:toString), без дублей в списке разговоров
  X3.keys[key] = true
  local h = hstr(leader)
  if not h or X3.dk[h] then return end
  if not X3.gd then
    X3.gd = getGameWorld().gamedata:getData(D.world.duel_dialogue, DIALOGUE_TYPE)
    if not X3.gd then error("getData(DIALOGUE) nil for " .. tostring(D.world.duel_dialogue)) end
  end
  local added = 0
  local ok, err = pcall(function()
    local dl = leader.dialogue
    for _, e in ipairs(D.world.duel_events or { 1 }) do
      if not X3.has_conv(dl, e) then dl:addConversation(X3.gd, e); added = added + 1 end
    end
  end)
  if ok then
    rec.key = h
    X3.dk[h] = rec
    if added > 0 then
      X3.stats.offers = X3.stats.offers + 1
      log(string.format("DUEL offer added: %s (%s)", tostring(rec.n), rec.src))
    else
      log(string.format("DUEL offer kept: %s (%s) already has it", tostring(rec.n), rec.src))
    end
  else
    log("DUEL addConversation failed for " .. tostring(rec.n) .. ": " .. tostring(err))
  end
end

function X3.live_scan(mod, tbl, src_of)   -- живые отряды модуля (Outlaws/Fates): главарь → разговор вызова
  local okl, live = pcall(mod.live)
  local oks, St = pcall(mod.state)
  if not (okl and oks and type(live) == "table" and type(St) == "table" and type(St[tbl]) == "table") then return end
  for id, lv in pairs(live) do
    local r = St[tbl][id]
    if r and r.st == "a" and type(lv) == "table" and lv.pl and not X3.stale[lv] then
      local src = src_of(r)
      local key = src .. "|" .. tostring(id) .. "|" .. tostring(r.pk or r.n)   -- стабильный ключ записи, не таблица lv
      if not X3.keys[key] then
        local okg, leader = pcall(function() return lv.pl:getSquadLeader() end)
        if not okg then X3.stale[lv] = true
        elseif leader then X3.offer(leader, key, { src = src, n = r.n }) end
      end
    end
  end
end

function X3.scan()   -- раз в world_refresh_seconds: кому добавить вызов
  local w = D.world
  if not (HK.on and w and w.duel_dialogue and P.duel ~= false) then return end
  local s = S()
  local O_, F_ = rawget(_G, "KMM_Outlaws"), rawget(_G, "KMM_Fates")
  if X3.world ~= s then   -- другой мир: указатели прошлого не трогаем, ключи и поединок сбрасываются
    if X3.world ~= nil then
      for _, M_ in ipairs({ O_, F_ }) do
        if type(M_) == "table" and M_.live then
          local ok, lv = pcall(M_.live)
          if ok and type(lv) == "table" then for _, x in pairs(lv) do if type(x) == "table" then X3.stale[x] = true end end end
        end
      end
      log("DUEL world changed: offers and duel reset")
    end
    X3.drop("world changed")
    X3.world, X3.keys, X3.dk = s, {}, {}
  end
  if type(O_) == "table" and O_.live and O_.state then X3.live_scan(O_, "L", function(o) return o.pg and "nemesis" or "outlaw" end) end
  if type(F_) == "table" and F_.live and F_.state then X3.live_scan(F_, "H", function() return "fate" end) end
  local G = rawget(_G, "KMM_Gov")
  local RF = D.duel and D.duel.rival_factions
  if not (type(G) == "table" and G.snapshot) then return end
  if X3.rv == nil then   -- реестр отрядов-искателей Q1 (rivals.json дирижёра): только эти шаблоны, не бар/торговцы/наёмники гильдии
    local okr, rv = pcall(function() return C.read_json and C.read_json("rivals.json", "C:/KenshiModMap/build/KMM_Conductor/rivals.json") end)
    X3.rv = (okr and type(rv) == "table" and type(rv.prospectors) == "table") and rv.prospectors or false
    if not X3.rv then log("DUEL rivals.json unavailable: Q1 squads by duel.rival_factions only") end
  end
  if not X3.rf then X3.rf = {}; for _, f in ipairs(type(RF) == "table" and RF or {}) do X3.rf[f] = true end end
  local okn, snap = pcall(G.snapshot, P.world_refresh_seconds or 4)
  if not (okn and type(snap) == "table" and type(snap.list) == "table") then return end
  local pc = player_chars()[1]
  if not pc then return end
  local okp, px, pz = pcall(pos, pc)
  if not (okp and px) then return end
  local r2, n = (P.duel_scan_r or 6000) ^ 2, 0
  for _, rec in ipairs(snap.list) do
    local key = "q|" .. tostring(rec.pkey)
    if rec.pkey and rec.pkey ~= "" and rec.x and not rec.dead and not X3.keys[key] and (rec.x - px) ^ 2 + (rec.z - pz) ^ 2 <= r2
       and ((X3.rv and X3.rv[rec.tsid or ""]) or (not X3.rv and rec.fid and X3.rf[rec.fid])) then
      X3.keys[key] = true
      if not (rec.trader or rec.town) then   -- торговцы и отряды в городе (бар, найм) вызова не получают
        local okg, leader = pcall(function() return rec.pl:getSquadLeader() end)
        if okg and leader then X3.offer(leader, key, { src = "fate", n = name_of(leader) or "a drifter" }) end
      end
      n = n + 1
      if n >= (P.duel_scan_max or 4) then break end
    end
  end
end

function X3.on_ask(npc, pc)   -- игрок бросил вызов: лидер решает (кулдаун, трус), ответ — репликой по условию
  duel_codes_clear()
  local rec = npc and X3.dk[hstr(npc) or ""]
  local dd, why = duel_ds(), nil
  local sl, sp = npc and skill_of(npc), pc and skill_of(pc)
  local diff = (sl and sp) and (sl - sp) or 0
  if not (rec and pc and dd) then why = "unknown leader"
  elseif X3.cur then why = "duel already on"
  elseif DISABLED.duel_step then why = "duel off"
  elseif in_town(pc) or in_town(npc) then why = "in town"   -- стража и город вмешаются: поединок только в поле
  elseif dd.cd[rec.key] and day() - dd.cd[rec.key] < (P.duel_cd_days or 3) then why = "cooldown"
  elseif diff < -(P.duel_coward_gap or 15) then why = "coward" end
  X3.stats.asks = X3.stats.asks + 1
  if why then
    wset("duel_refuse", true); X3.ask = nil
  else
    wset("duel_accept", true)
    X3.ask = { npc = npc, pc = pc, rec = rec, diff = diff, at = os.clock() }
  end
  log(string.format("DUEL ask %s (%s): diff %+.0f -> %s", tostring(rec and rec.n), tostring(rec and rec.src), diff, why and ("refuse, " .. why) or "accept"))
end

function X3.on_start(npc, pc)   -- лидер принял: временная вражда уже поставлена эффектом реплики (данные)
  local a = X3.ask
  duel_codes_clear(); X3.ask = nil
  if not (a and os.clock() - a.at <= (P.duel_ask_ttl_s or 60)) then log("DUEL start without ask: ignored"); return end
  npc, pc = npc or a.npc, pc or a.pc
  local okf, fid = pcall(fid_of, npc)
  X3.cur = { npc = npc, pc = pc, hn = handle_of(npc), hp = handle_of(pc), pk = pkey_of(npc), rec = a.rec, diff = a.diff, t0 = os.clock(),
             fid = okf and fid or nil, world = S() }
  wset("duel_open", false)
  local dd = duel_ds(); if dd then dd.cd[a.rec.key] = day() end
  X3.stats.starts = X3.stats.starts + 1
  X3.spare_fid = X3.cur.fid   -- амнистия конечна: поединок не дольше таймаута, потом грабёж и пощада
  X3.spare_until = os.clock() + (P.duel_timeout_s or 240) + (P.duel_loot_s or 45) + (P.duel_spare_s or 60)
  log(string.format("DUEL start: %s (%s, faction %s), skill diff %+.0f", tostring(a.rec.n), a.rec.src, tostring(X3.cur.fid), a.diff))
end

function X3.clear(d)   -- снять временную вражду ванильно со всего отряда лидера: clearTempEnemyStatus в обе стороны + reThinkCurrentAIAction
  local squad, seen = {}, {}
  local function add(c) if c and not seen[c] then seen[c] = true; squad[#squad + 1] = c end end
  add(d.npc)   -- свежий указатель этого такта (X3.step), nil — лидер не читается
  local G = rawget(_G, "KMM_Gov")
  if d.pk and type(G) == "table" and G.snapshot then   -- товарищи по отряду: только из свежего снимка (живой набор движка)
    local ok, snap = pcall(G.snapshot, P.world_refresh_seconds or 4)
    local b = ok and type(snap) == "table" and type(snap.by_pkey) == "table" and snap.by_pkey[d.pk]
    if type(b) == "table" then for _, r in ipairs(b) do add(rawget(r, "ch")) end end
  end
  local n, m = 0, 0
  for _, pc in ipairs(player_chars()) do
    for _, c in ipairs(squad) do
      if pcall(function() c:clearTempEnemyStatus(pc) end) and c == d.npc then n = n + 1 end
      pcall(function() pc:clearTempEnemyStatus(c) end)
    end
  end
  for _, c in ipairs(squad) do if pcall(function() c:reThinkCurrentAIAction() end) then m = m + 1 end end   -- погоня/бой по новой оценке
  X3.spare_until = os.clock() + (P.duel_spare_s or 60)
  log(string.format("DUEL clear: temp enemy status cleared for %d player characters, squad %d, rethink %d (%s)", n, #squad, m, tostring(d.rec.n)))
end

X3.PFX = { nemesis = "nemesis_duel_", outlaw = "outlaw_duel_", fate = "fate_duel_" }
function X3.finish(d, outcome)
  local now = os.clock()
  local okx, x, z = pcall(pos, d.npc)
  if not okx then x, z = nil, nil end
  local helpers = 0
  if outcome == "won" or outcome == "won_kill" then
    for _, c in ipairs(player_chars()) do
      if c ~= d.pc and not down_of(c) then local ok, dd = pcall(dist, c, d.npc); if ok and dd <= (P.duel_help_r or 800) then helpers = helpers + 1 end end
    end
  end
  local tsid = player_town()
  local ti = tsid and CFG.town_info and CFG.town_info[tsid]
  local near = (ti and ti.name) and (" near " .. ti.name) or ""
  local n, strong = tostring(d.rec.n), (d.diff or 0) >= (P.duel_strong_diff or 8)
  local text, key
  if outcome == "won" then
    key = "won"
    text = string.format("The Nameless challenged %s to a duel%s and put them in the dirt%s.", n, near,
      helpers > 0 and ", though not alone: their crew joined in" or (strong and (", though " .. n .. " was the better fighter") or ", one on one"))
  elseif outcome == "won_kill" then
    key = "won"
    text = string.format("The Nameless challenged %s to a duel%s and killed them.", n, near)
  elseif outcome == "lost" then
    key = "lost"
    text = string.format("%s took up the challenge of the Nameless%s and left them in the dirt, purse emptied.", n, near)
  end
  if key then
    X3.stats[key] = X3.stats[key] + 1
    emit({ type = (X3.PFX[d.rec.src] or "fate_duel_") .. key, a = PF(), b = d.fid, by_player = true, x = x, z = z, leader_name = n,
           status = outcome, strong = strong and helpers == 0 or nil, text = text })
    message(text)
  else
    X3.stats.void = X3.stats.void + 1
  end
  log(string.format("DUEL end: %s (%s) -> %s (diff %+.0f, helpers %d, %.0f s)", n, tostring(d.rec.src), outcome, d.diff or 0, helpers, now - d.t0))
  if outcome == "lost" then d.phase, d.t_end = "loot", now + (P.duel_loot_s or 45)   -- ванильное ограбление победителем, потом мир
  else X3.clear(d); X3.cur = nil end
end

function X3.step()   -- раз в секунду, только при активном поединке
  local d = X3.cur
  if not d then return end
  if d.world ~= S() then X3.drop("world changed"); return end
  local now = os.clock()
  d.npc, d.pc = fresh(d.hn), fresh(d.hp)   -- указатель прошлого такта не разыменовываем: только свежий из handle
  if d.phase == "loot" then
    if now >= d.t_end then X3.clear(d); X3.cur = nil end
    return
  end
  local ln, pn = "gone", "gone"
  if d.npc then ln = down_of(d.npc) end
  if d.pc then pn = down_of(d.pc) end
  local out
  if ln == "gone" or pn == "gone" then out = "void"
  elseif ln == "dead" then out = "won_kill"
  elseif ln and pn then out = "draw"
  elseif ln then out = "won"
  elseif pn then out = "lost"
  elseif now - d.t0 > (P.duel_timeout_s or 240) then out = "void"
  else
    local ok, dd = pcall(dist, d.npc, d.pc)
    if not ok or dd > (P.duel_leash or 6000) then out = "void" end
  end
  if out then X3.finish(d, out) end
end

function X3.spared(fid)   -- player_raid против фракции лидера во время поединка и вскоре после — не измена
  local now = os.clock()
  return fid ~= nil and fid == X3.spare_fid and now <= X3.spare_until and X3.spare_until - now <= X3.spare_max()
end
function X3.spare_max() local p = P or {}; return (p.duel_timeout_s or 240) + (p.duel_loot_s or 45) + (p.duel_spare_s or 60) + 5 end

---------------------------------------------------------------------------------------------- мост диалога
local function resolve_speakers(dlg, line)
  local oka, a = pcall(function() return dlg.me end)
  if not oka then a = nil end
  local okb, b = pcall(function() return dlg:getSpeaker(T_TARGET, line, false) end)
  if not okb then b = nil end
  local npc, pc
  if a and is_player(a) then pc, npc = a, b else npc, pc = a, b end
  if pc and not is_player(pc) then pc = nil end
  if npc and is_player(npc) then npc = nil end
  if CUR and os.clock() - CUR.at < 600 then npc = npc or CUR.npc; pc = pc or CUR.pc end
  if not pc and npc then   -- ближайший персонаж игрока к собеседнику
    local best, bd = nil, nil
    for _, c in ipairs(player_chars()) do local d = dist(c, npc); if not bd or d < bd then best, bd = c, d end end
    pc = best
  end
  return npc, pc
end

local function on_open(dlg, line)
  local npc, pc = resolve_speakers(dlg, line)
  if not (npc and pc) then error("open: speakers not resolved") end
  local fid = fid_of(npc)
  CUR = { npc = npc, pc = pc, fid = fid, at = os.clock(), tok = not cond_mode() }
  clear_tokens(pc)
  conv_clear()
  local s, pf, ds = S(), PF(), DS()
  if not (s and fid and pf and ds) then return end
  local d = day()
  for _, t in pairs(s.treaties) do
    if t.active and ((t.a == fid and t.b == pf) or (t.a == pf and t.b == fid)) then
      if not CUR.tok then wset("has_pact", true)
      elseif not has_item(pc, D.items.has_pact) then give_token(pc, "has_pact") end
      if t.type == "vassal" then
        local due = ds.due[t.id]
        if not due then due = { next = (t.since or d) + (P.tribute_period_days or 30) }; ds.due[t.id] = due end
        if d >= due.next then
          local key = (t.b == pf) and "liege_due" or "vassal_due"
          if CUR.tok then give_token(pc, key) else wset(key, true) end
        end
      end
    end
  end
end

local function on_propose(dlg, line, kind)
  local npc, pc = resolve_speakers(dlg, line)
  local fid = (npc and fid_of(npc)) or (CUR and CUR.fid)
  if not (pc and fid) then error("propose: no faction/player character") end
  local out, U, why, ttype = decide(fid, kind)
  PENDING = { fid = fid, kind = kind, outcome = out, ttype = ttype, U = U, why = why, at = os.clock(), tok = not cond_mode() }
  conv_clear(true)
  if PENDING.tok then
    for _, k in ipairs({ "accept", "refuse", "counter_s", "counter_l" }) do take_item(pc, D.items[k]) end
    give_token(pc, out)
  else
    wset("dec_" .. out, true)   -- ответ фракции включает её реплику-«близнеца» через перехват условий
    stats.by_cond = (stats.by_cond or 0) + 1
  end
end

local function on_commit(dlg, line, meta)
  local npc, pc = resolve_speakers(dlg, line)
  local fid = (npc and fid_of(npc)) or (CUR and CUR.fid)
  local q = { fid = fid, kind = meta.kind, outcome = meta.outcome, tier = meta.tier, cats = meta.cats }
  if PENDING and PENDING.fid == fid and PENDING.kind == meta.kind then q.ttype = PENDING.ttype end
  QUEUE[#QUEUE + 1] = q
  local due_kind = meta.kind == "liege_tribute" or meta.kind == "vassal_tribute" or meta.kind == "renounce"
  conv_clear(true)
  if due_kind then wset("liege_due", false); wset("vassal_due", false); wset("has_pact", false) end
  if PENDING and not PENDING.tok then PENDING.at = -1e9 end
  local tok = (PENDING and PENDING.tok) or (CUR and CUR.tok) or not cond_mode()
  if pc and tok then for _, k in ipairs({ "accept", "refuse", "counter_s", "counter_l" }) do take_item(pc, D.items[k]) end end
  if pc and tok and due_kind then
    take_item(pc, D.items.liege_due); take_item(pc, D.items.vassal_due); take_item(pc, D.items.has_pact)
  end
end

local function on_deferred(m)   -- «изложите письменно»: при ответе по условию это значит, что близнец не прозвучал → назад к жетонам
  if PENDING and not PENDING.tok and os.clock() - PENDING.at < 120 then
    HK.fail = HK.fail + 1
    dlog(string.format("DIPLO_COND fallback: reply by condition not shown (%s, %s) -> envoy tokens again this session", tostring(m.kind), tostring(PENDING.outcome)))
  end
end

local g_line = guarded("dialogue", function(dlg, line)
  if not (D and C) then return end
  local sid = line:getStringID()
  local m = D.lines[sid]
  if not m then return end
  if m.role == "open" then on_open(dlg, line)
  elseif m.role == "propose" then on_propose(dlg, line, m.kind)
  elseif m.role == "commit" then on_commit(dlg, line, m)
  elseif m.role == "deferred" then on_deferred(m)
  elseif m.role == "close" then local _, pc = resolve_speakers(dlg, line); conv_clear(); if pc then clear_tokens(pc) end; CUR = nil
  elseif m.role == "duel_ask" then X3.on_ask(resolve_speakers(dlg, line))
  elseif m.role == "duel_start" then X3.on_start(resolve_speakers(dlg, line))
  elseif m.role == "duel_refused" then duel_codes_clear(); X3.ask = nil end
end)

---------------------------------------------------------------------------------------------- такт
local function letters_scan()   -- запасной канал: письмо-предмет у персонажа игрока → решение → сообщение/слух
  local pcs = player_chars()
  if #pcs == 0 then return end
  local loaded
  for kind, isid in pairs(D.letters) do
    for _, pc in ipairs(pcs) do
      if has_item(pc, isid) then
        take_item(pc, isid)
        stats.letters = stats.letters + 1
        if not loaded then
          loaded = {}
          pcall(function() for ch in pairs(getGameWorld():getCharacterUpdateList()) do loaded[#loaded + 1] = ch end end)
        end
        local best, bd, bfid
        for _, ch in ipairs(loaded) do   -- посланник рядом: сначала прикреплённые персонажи, иначе любой NPC фракции дирижёра
          local okc, fid, d, env = pcall(function()
            if is_player(ch) then return nil end
            local f = fid_of(ch)
            if not (f and S().F[f]) or f == PF() then return nil end
            return f, dist(ch, pc), D.envoys[sid_of(ch) or ""] ~= nil
          end)
          if okc and fid and d <= (P.envoy_radius or 1500) then
            local score = d - (env and 100000 or 0)
            if not bd or score < bd then best, bd, bfid = ch, score, fid end
          end
        end
        if bfid and kind == "tribute" then   -- деньги по письму не передать: требования дани — только лично
          message(string.format("%s will not answer a demand for tribute by letter. Make it to their face.", fname(bfid)))
        elseif bfid then
          local out, U, why, ttype = decide(bfid, kind)
          apply({ fid = bfid, kind = kind, outcome = out, ttype = ttype, async = true })
          if out == "accept" then emit({ type = "diplo_answer", a = bfid, b = PF(), text = string.format("%s answered the Nameless: yes to the %s.", fname(bfid), KIND_TEXT[kind] or kind) }) end
        else
          message("Your sealed terms found no envoy nearby. Speak to a lord or envoy of a faction.")
        end
      end
    end
  end
end

local function dues_step()   -- дань вассалитета: просрочка игроком-вассалом бьёт по отношениям/доверию, потом разрыв
  local s, pf, ds = S(), PF(), DS()
  if not (s and pf and ds) then return end
  local d = day()
  for _, t in pairs(s.treaties) do
    if t.active and t.type == "vassal" and t.b == pf then
      local due = ds.due[t.id]
      if not due then ds.due[t.id] = { next = (t.since or d) + (P.tribute_period_days or 30) }
      elseif d >= due.next + (P.tribute_grace_days or 20) then
        due.next = d + (P.tribute_period_days or 30)
        add_rel(t.a, pf, P.rel_on_tribute_missed or -10)
        add_trust(t.a, pf, P.trust_on_tribute_missed or -20)
        if trust(s, t.a, pf) < (CFG.params.treaties.min_trust or -20) then break_all(t.a, "tribute unpaid", true)
        else emit({ type = "tribute_missed", a = pf, b = t.a, text = string.format("The Nameless failed to pay their tribute to %s.", fname(t.a)) }) end
      end
    end
  end
end

local function betrayal_watch()   -- игрок напал на партнёра по договору (событие дирижёра player_raid) → игрок нарушил договор
  local s, pf, ds = S(), PF(), DS()
  if not (s and pf and ds) then return end
  local last = s.events[#s.events]
  if not ds.last_ev or ds.last_ev == 0 then ds.last_ev = last and last.id or -1; return end   -- старые события — не повод
  for _, ev in ipairs(s.events) do
    if ev.id > ds.last_ev then
      ds.last_ev = ev.id
      if ev.type == "player_raid" and ev.b and X3.spared(ev.b) then
        X3.stats.spared = X3.stats.spared + 1
        log("DUEL spared: fight with " .. fname(ev.b) .. " was a duel, pacts kept")
      elseif ev.type == "player_raid" and ev.b and treaty_between(s, ev.b, pf) then break_all(ev.b, "the Nameless attacked their partner", true) end
    end
  end
end

local function token_sweep()   -- жетоны не должны пережить разговор
  local now, keep = os.clock(), {}
  for _, g in ipairs(GIVEN) do
    if now - g.at >= (P.token_ttl_seconds or 90) then pcall(take_item, g.pc, D.items[g.key]) else keep[#keep + 1] = g end
  end
  GIVEN = keep
end

local function selfcheck()   -- один раз: видит ли KenshiLua наши «run lua script» (диагностика моста) → debug.log
  -- в документации глобал kenshi, в игре его нет (лог 2026-11-12) — ищем функцию в известных таблицах, иначе тихо пропускаем
  local fn
  for _, t in ipairs({ rawget(_G, "kenshi"), rawget(_G, "KenshiLua"), rawget(_G, "Kenshi") }) do
    if type(t) == "table" and type(t.checkLuaScriptReferences) == "function" then fn = t.checkLuaScriptReferences; break end
  end
  if not fn then dlog("bridge selfcheck skipped: checkLuaScriptReferences not exposed (bridge itself works: DialogueScriptBridge lines in KenshiLua.log)"); return end
  local ok, rep = pcall(fn)
  if ok and rep then
    local n = 0
    for l in tostring(rep):gmatch("[^\n]+") do if l:find("KMM_Diplo", 1, true) or l:find("kmm_diplo", 1, true) then n = n + 1 end end
    dlog(string.format("bridge selfcheck: %d report lines mention KMM_Diplo (0 = мост не видит наши реплики → работает только запасной канал писем)", n))
  else
    dlog("bridge selfcheck unavailable: " .. tostring(rep))
  end
end

local function give_seal()
  if P.give_seal == false then return end
  local pcs = player_chars()
  for _, pc in ipairs(pcs) do if has_item(pc, D.items.seal) then return end end
  if pcs[1] then give_item(pcs[1], D.items.seal); dlog("Envoy's Seal given to the first player character") end
end

local g_apply = guarded("apply", function() while #QUEUE > 0 do apply(table.remove(QUEUE, 1)) end end)
local g_letters = guarded("letters", letters_scan)
local g_dues = guarded("dues", dues_step)
local g_watch = guarded("betrayal_watch", betrayal_watch)
local g_sweep = guarded("tokens", token_sweep)
local g_self = guarded("selfcheck", selfcheck)
local g_seal = guarded("seal", give_seal)
local g_hook = guarded("cond_init", hook_register)
local g_world = guarded("world", world_refresh)
local g_rival = guarded("rival_talk", rival_talk)
local g_dscan = guarded("duel_scan", function() X3.scan() end)
local g_dstep = guarded("duel_step", function()   -- ошибка такта: поединок и амнистия сброшены, такт выключен
  local ok, err = pcall(X3.step)
  if not ok then X3.drop("step error"); error(err, 0) end
end)

local seen_at, ready, t_fast, t_letters, t_slow, t_world = nil, false, 0, 0, 0, 0
local function init()
  if ready then return true end
  if #player_chars() == 0 then seen_at = nil; return false end   -- ленивый старт: только после появления персонажей игрока
  local now = os.clock()
  seen_at = seen_at or now
  P = P or { start_delay_seconds = 5 }
  if now - seen_at < (P.start_delay_seconds or 5) then return false end
  C = conductor()
  if not (C and C.emit and C.add_rel and C.add_trust_one and C.player_sign and C.player_break) then return false end   -- API дирижёра обязателен
  CFG = C.cfg()
  if not (CFG and CFG.params and CFG.player_faction) then return false end
  D = load_data()
  if not D then error("kmm_diplo_data.lua not found") end
  P = D.params or {}
  ready = true
  local n = 0; for _ in pairs(D.envoys or {}) do n = n + 1 end
  dlog(string.format("started: %d envoys, conductor API with player_sign", n))
  g_self()
  g_seal()
  g_hook()
  return true
end
local g_init = guarded("init", init)

local function tick()
  if not g_init() then return end
  local now = os.clock()
  if now - t_fast >= 1 then t_fast = now; g_apply(); if X3.cur then g_dstep() end end
  if now - t_letters >= (P.letter_scan_seconds or 3) then t_letters = now; g_letters() end
  if now - t_slow >= 5 then t_slow = now; g_dues(); g_watch(); g_sweep() end
  if now - t_world >= (P.world_refresh_seconds or 4) then t_world = now; g_world(); g_rival(); g_dscan() end
end

if Events and Events.on then Events.on("GameWorld::charsUpdate", guarded("tick", function(...) if _G.KMM_Gov then return KMM_Gov.run("diplo", tick, ...) else return tick(...) end end)) end
-- загружен сейв: поединок, амнистия и разговоры прошлого мира забыты до следующего скана (handle/указатели прошлого не трогаем)
if Events and Events.on then Events.on("PlayerInterface::loadFromSerialise", guarded("duel_load", function() X3.drop("save loaded"); X3.keys, X3.dk = {}, {} end)) end

local API = {
  on_line = function(dlg, line) g_line(dlg, line) end,
  evaluate = evaluate,                      -- чистая оценка (офлайн-тесты, консоль)
  decide = function(fid, kind) return decide(fid, kind) end,
  queue = function() return QUEUE end,
  stats = function() return stats end,
  disabled = function() return DISABLED end,
  ready = function() return ready end,
  _tick = function() tick() end,
  _set_data = function(d) D = d; P = d.params or P end,
  _money = function() return player_money() end,   -- офлайн-тест: деньги игрока через персонажа
  world = function() return WV end,            -- S4: флаги условий мира (код → bool), только читать
  hook = function() return HK end,             -- S4: состояние перехвата (live, n, fail, asked)
  cond_mode = function() return cond_mode() end,
  _check = function(...) return on_check(...) end,   -- офлайн-тест горячего пути
  duel = function() return X3.cur end,                     -- X3: активный поединок { npc, pc, rec = { n, src, key }, fid, diff, t0 } или nil
  duel_active = function(fid) return X3.spared(fid) end,   -- X3: бой с этой фракцией сейчас поединок (для дирижёра: не считать нападением)
  duel_until = function() return X3.spare_until end,       -- X3: до какого os.clock действует амнистия (-1 — нет); дирижёр сверяет срок сам
  duel_stats = function() return X3.stats end,
}
KMM_Diplo = API
if _G then _G.KMM_Diplo = API end
