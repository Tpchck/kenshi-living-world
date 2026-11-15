-- KMM_Conductor v1 — дирижёр мира (KenshiModMap). Параметры и данные: conductor.json (tools/conductor/gen_conductor.py).
--
-- Абстрактный мир: у каждой фракции богатство, сила, территория (города по LORE_MAP), амбиция; реликтовые — focused/mobilized
-- (переход только по поводу из мира, возврат без повода). Раз в tick_days: экономика → режимы реликтовых → договоры →
-- действия фракций (utility: рейд, торговля, союз, вербовка, затаиться, захват города) → шина событий (страх, оппортунизм,
-- сближение против общего врага, обязательства союзников). Всё — в журнал (сейв) и chronicle.log.
-- Материализация в игре (всё под pcall, флаги в params.materialize):
--   отношения фракций → FactionRelations:setRelation;  смерть/плен лидера при загрузке зоны вне видимости игрока
--   (declareDead / setChainedMode) → дальше ванильный world state;  союзные отряды к игроку → RootObjectFactory:createRandomSquad;
--   экипировка по богатству фракции → createItem + Inventory:addItem/equipItem (data: wardrobe_tiers.json).
-- Контракт chronicle.log (RUMORS): UTF-8, строка на событие, TAB: game_day, event_id, event_type, town_sid, town_name,
--   faction_attacker, faction_defender, leader_sid, leader_name, status, text
--
-- Файлы (T1, 2026-11-15; лимит 200 локалей главного чанка снят): KMM_Conductor_Base / _Econ / _Sync / _World / _Runtime
-- и этот файл (конфиг, экспорт KMM_Conductor.*, регистрация событий). Бывшие top-level local — поля KC.<имя> общей
-- таблицы _G.KMM_C_INT (внутреннее, не API: внешним модулям — только KMM_Conductor.*). Новый общий символ: KC.<имя> = ...
-- в любой части. Каждая часть — функция KC._SEG.<имя>; KC._BOOT() выполняет их по KC._PARTS, когда загружены все файлы.

local KC = rawget(_G, "KMM_C_INT")   -- общее пространство имён частей дирижёра (бывшие локали главного чанка: KC.<имя>)
if type(KC) ~= "table" then KC = { _SEG = {} }; _G.KMM_C_INT = KC end
if KC._booted then KC._SEG, KC._booted = {}, false end   -- повторная загрузка скриптов: собрать части заново
KC._PARTS = { "Base", "Econ", "Sync", "World", "Runtime", "Main" }
function KC._BOOT()
  if KC._booted then return end
  for _, p in ipairs(KC._PARTS) do if not KC._SEG[p] then return end end
  KC._booted = true
  for _, p in ipairs(KC._PARTS) do KC._SEG[p]() end
end

KC._SEG.Main = function()
local guarded = KC.guarded   -- безотказность (часть Runtime); обработчики Events.on - guarded(...) (правило lua_lint)
---------------------------------------------------------------------------------------------- регистрация
KC.ROOT = KC.mod_root()
KC.CFG = KC.load_json("conductor.json", "C:/KenshiModMap/rules/conductor.json")
if KC.CFG and KC.CFG.params then
  KC.P = KC.CFG.params
  KC.P.contra = KC.P.contra or {   -- ЗАКОННОСТЬ товаров по фракциям (CONTRA): pat — Lua-паттерн по "fid имя"; <cat> = false (незаконно) | множитель спроса
    legal = { { pat = "Holy Nation", drugs = false },   -- Святая Нация: наркотики вне закона (болота и ниндзя возят тайком)
              { pat = "Shek", lux = 0.5 } },             -- шеки: роскошь не в чести
    inflow = 0.3, demand = 0.5, confiscate = 0.012, trig = 0.25, delivery = 0.5, cooldown = 45, gap = 8, price = 1.5,
    caught = 0.25, caught_rel = 4, gear_lo = 0.25, gear_hi = 0.5, gear_cooldown = 90,
  }
  KC.P.campaign = KC.P.campaign or {   -- NATIVE_MAP п.2/п.5: родные кампании движка и флаги RelationData (консервативно; enabled=false выключает)
    enabled = true, p_raid = 0.15, p_capture = 0.25, q_reinforce = 0.4, ally_rel = 30, fac_cooldown = 30, world_max = 3, world_days = 10, max_forces = 30,
    load_radius = 15000, min_time = 0, max_time = 0, relflags = true, war_rel = -60, war_days = 60, sdir = "C:/KenshiModMap/state/",
  }
  KC.P.links2 = KC.P.links2 or {   -- LINKS2: связки механик (подробности и числа - rules\conductor.json, params.links2)
    enabled = true,
    glut = { days = 40, raid_w = 0.7, price_days = 30, price_mult = 0.9 },
    shortage = { days = 40, trade_w = 1.0 },
    sacked = { unrest = 0.1, towns = 2, max_level = 0.6 },
    contra = { days = 60, raid_w = 0.8, hn_pat = "Holy Nation", rel_min = 2, rel_max = 5, branch_rel = 1.5, cooldown = 20 },
    chaos = { war_days = 60, famine_days = 120, contra_days = 120, intrigue_days = 120, min_score = 0.5, gods = {} },
    self = { events = { "self_retreat", "self_surrender_attempt" }, strength = 0.003, cap = 0.01, morale = 0.02, morale_max = 0.15, morale_floor = 0.3,
             morale_rec = 0.02, morale_pen = 0.15, surrender_w = 1.5 },
    profiles = {},
  }
  KC.L2.install()
  KC.P.roads = KC.P.roads or {   -- ROADS: путники и память дорог (значения по умолчанию; rules\conductor.json params.roads)
    enabled = true, refugees = true, caravans = true, wanderers = true, scouts = true, couriers = true, tribute = true, grid = true,
  }
  KC.P.famine = KC.P.famine or { enabled = true, below = 0.35, days = 6, cooldown = 30, max_groups = 2, chance = 0.5, share = 0.06, min_n = 4, friend_rel = 1, dest_food = 0.8 }   -- FAMINE: голод города -> беженцы
  KC.P.ws = KC.P.ws or { enabled = true }   -- LINKN: связка смены владельца города с вариантами через KMM_Native (lut_path - только для тестов)
  KC.P.rev2 = KC.P.rev2 or {   -- REV2: ревизия видения (см. docs\DECISIONS.md)
    betrayal_trust = -10, betrayal_ally_rel = -8,                     -- репутация предателя у соседей
    avoid_ratio = 0.4, avoid_revenge_days = 90, low_days = 40, low_tell_days = 120,        -- слабые избегают сильных
    joint_enabled = true, joint_chance = 0.4, joint_cooldown = 40, joint_min_power = 0.2, joint_max_rel = 20, joint_weight = 0.5,
    joint_cost = 0.4, joint_trust = 4, joint_loot = 0.25,            -- совместные рейды союзников
    base_def_gain = 6, base_def_cap = 40, base_repel_rel = 3, base_plunder = 0.1, base_plunder_cap = 20, base_unattended_rel = 2,
  }
  KC.TIERS = KC.load_json("wardrobe_tiers.json", "C:/KenshiModMap/data/wardrobe_tiers.json")
  KC.pairs_index()
  Events.on("GameWorld::charsUpdate", guarded("tick", function(...) if _G.KMM_Gov then return KMM_Gov.run("conductor", KC.on_tick, ...) else return KC.on_tick(...) end end))
  Events.on("PlayerInterface::serialise", guarded("save", KC.PST.on_serialise))
  Events.on("PlayerInterface::loadFromSerialise", guarded("load", KC.PST.on_load))
  Events.on("Character::_NV_hitByMeleeAttack", guarded("hit_hook", KC.on_hit))
  pcall(Events.on, "Faction::destroyPlatoon", guarded("coresync_hook", KC.GL.cs_on_destroy))   -- S2: подсказка сверке силы (нет колбэка - живём без неё)
  KC.log(string.format("v1 loaded: %d factions, %d town/leader pairs, gear tiers %s", KC.count(KC.CFG.factions), #(KC.CFG.towns or {}), KC.TIERS and "yes" or "no"))
else
  KC.log("no v1 config — conductor disabled")
end

KMM_Conductor = {   -- консоль KenshiLua (Ctrl+Shift+L) и офлайн-тест
-- >>> BEGIN KMM_Diplo patch
  player_sign = function(fid, ttype, why, player_is_suzerain)   -- договор фракции fid с игроком; vassal: сюзерен = fid, либо игрок
    local pf = KC.CFG.player_faction
    if not (KC.S and pf and KC.S.F[fid] and KC.S.F[pf]) then return nil end
    KC.DAY = math.max(KC.DAY, KC.S.last_day or KC.DAY)
    local ex = KC.treaty_between(fid, pf, ttype)
    if ex then ex.term = KC.DAY + (KC.P.treaties.term_days[ttype] or 360); return ex end
    if ttype == "vassal" and player_is_suzerain then return KC.sign(ttype, pf, fid, why) end
    return KC.sign(ttype, fid, pf, why)
  end,
  warlord_from = function(parent, who)   -- NEMESIS: выросший соперник игрока поднимает спящего варлорда из доли своей банды
    if not (KC.S and KC.S.F[parent] and KC.S.F[parent].alive) then return nil end
    for _, w in ipairs(KC.CFG.warlords or {}) do
      if KC.S.F[w] and not KC.S.F[w].alive and w ~= parent then
        local ok = KC.activate(w, parent, (KC.P.shards or {}).nemesis_share or 0.12)
        if ok then
          KC.S.stats.warlords = (KC.S.stats.warlords or 0) + 1
          KC.emit({ type = "warlord_rose", a = w, b = parent, nemesis = who,
                 text = string.format("%s, who survived the Nameless three times, rallied men of %s under the banner of %s.", tostring(who), KC.name(parent), KC.name(w)) })
          return w
        end
      end
    end
    return nil
  end,
  leader_fell = function(lsid, lname, how, by_player)   -- LEADERS: настоящий лидер из пар городов пал/закован в мире (KMM_Nemesis) -> модель узнаёт
    if not KC.S then return nil end
    for _, c in ipairs(KC.CFG.towns or {}) do
      if c.leader_sid and ((lsid and c.leader_sid == lsid) or (not lsid and lname and c.leader_name == lname)) then   -- имя — только без stringID («Elder», «Savant» не уникальны)
        if KC.S.resolved[c.leader_sid] or KC.S.pending[c.leader_sid] then return nil end   -- модель уже знает (или сама это материализует)
        local typ = (how == "captured") and "leader_captured" or "leader_killed"
        local own = (KC.S.F[c.defender_sid] and c.defender_sid) or nil
        local pf = KC.CFG.player_faction
        KC.S.resolved[c.leader_sid] = typ
        KC.S.stats.leaders_real = (KC.S.stats.leaders_real or 0) + 1
        local ev = KC.emit({ type = typ, a = (by_player and KC.S.F[pf]) and pf or nil, b = own, town_sid = c.town_sid, town_name = c.town_name,
                          leader_sid = c.leader_sid, leader_name = c.leader_name, status = "applied", real = true, by_player = by_player and true or false,
                          text = string.format("%s %s near %s%s.", c.leader_name, typ == "leader_killed" and "was killed" or "was taken in chains",
                                               c.town_name or "?", by_player and " by the Nameless" or "") })
        if own and KC.start_succession then KC.start_succession(own, c.leader_name .. (typ == "leader_killed" and " fell" or " was captured")) end
        if own and by_player and KC.S.F[pf] then   -- обида на игрока: мотив мести (цель revenge, рейд на базу «for revenge») — готовые механизмы модели
          local V = KC.S.F[own]; V.wronged = V.wronged or {}; V.wronged[pf] = KC.DAY
          KC.add_rel(own, pf, -(((KC.P.leaders or {}).player_rel) or 30))
        end
        return ev
      end
    end
    return nil
  end,
  player_break = function(fid, why, by_player)   -- разорвать все договоры fid ↔ игрок; by_player = измена игрока
    local pf = KC.CFG.player_faction
    if not (KC.S and pf) then return 0 end
    KC.DAY = math.max(KC.DAY, KC.S.last_day or KC.DAY)
    local n = 0
    for _, t in pairs(KC.S.treaties) do
      if t.active and ((t.a == fid and t.b == pf) or (t.a == pf and t.b == fid)) then KC.break_treaty(t, why, by_player and pf or nil); n = n + 1 end
    end
    return n
  end,
  -- захват конкретного города a у b (общий путь для act("capture") и KMM_Siege). opts: text, siege, str_a/str_b (множители силы), rel (дельта отношений).
  capture_town = function(a, b, town, opts)
    if not KC.S then return false end
    opts = opts or {}
    local f, O = KC.S.F[a], KC.S.F[b]
    if not (f and O and O.towns and O.towns[town]) or a == b then return false end
    if opts.str_a then f.strength = f.strength * opts.str_a end
    if opts.str_b then O.strength = O.strength * opts.str_b end
    if opts.rel then KC.add_rel(a, b, opts.rel) end
    O.towns[town] = nil; f.towns[town] = true
    f.unrest = f.unrest or {}
    f.unrest[town] = { level = 1.0, prev = b }
    KC.S.stats.captures = (KC.S.stats.captures or 0) + 1
    local tname = KC.TOWN_NAME[town] or town
    KC.DAY = math.max(KC.DAY, KC.S.last_day or KC.DAY)
    KC.emit({ type = "town_captured", a = a, b = b, town_sid = town, town_name = tname, siege = opts.siege, native = opts and opts.native,
           text = opts.text or string.format("%s seized %s from %s.", KC.name(a), tname, KC.name(b)) })
    KC.leader_outcome(town, a, b)
    return true
  end,
  add_rel = function(a, b, dv) if KC.S and KC.S.F[a] and KC.S.F[b] then KC.add_rel(a, b, dv) end end,
  add_trust_one = function(a, b, dv) if KC.S and KC.S.F[a] then KC.S.F[a].trust[b] = KC.clamp(KC.trust(a, b) + dv, -100, 100) end end,
  emit = function(ev) if KC.S then KC.DAY = math.max(KC.DAY, KC.S.last_day or KC.DAY); return KC.emit(ev) end end,
  power = function(fid) return KC.S and KC.power(fid) or 0 end,
-- <<< END KMM_Diplo patch
  -- REV2: затаившаяся фракция (патрули не выходят); исход рейда на базу от Traces
  low = function(fid) local f = KC.S and KC.S.F[fid]; return (f and f.low_until and (KC.S.last_day or KC.DAY) < f.low_until) and true or false end,
  alive = function(fid) local f = KC.S and KC.S.F[fid]; return (f and f.alive) and true or false end,
  base_result = function(kind, fid) if not KC.S then return false end; local ok, r = pcall(KC.base_result, kind, fid); if not ok then KC.guard_log("base_result: " .. tostring(r)); return false end; return r end,
  state = function() return KC.S end,
  self_chaining = function() return KC.GL.self_chain == true end,
  goals_pump = function(n) if KC.S then KC.GL.pump(n) end; return KC.GL.pending() end,   -- офлайн-тест/симуляция: порция очереди
  goals_drain = function() if KC.S then local n = 0; while KC.GL.pending() > 0 and n < 100 do KC.GL.pump(); n = n + 1 end end; return KC.GL.pending() end,
  fcities = function(fid) local f = KC.S and KC.S.F[fid]; return f and KC.ncities(f) or 0 end,
  phase_stats = function() local o = { pending = #KC.WS.q - KC.WS.i + 1, calls = KC.WS.calls, tmax = {} }; for k, v in pairs(KC.WS.tmax) do o.tmax[k] = v end; return o end,
  phase_timer = function(fn) KC.WS.timer = fn; KC.WS.tmax = {} end,
  phase_slice = function(x) KC.WS.slice = x end,
  advance_staged = function(day) if KC.S then KC.advance(day, true) end end,
  goal_mult = function(fid, a, o) local f = KC.S and KC.S.F[fid]; if not f then return 1 end; return KC.GL.mult(fid, f, a, o) end,
  goals_pending = function() return KC.GL.pending() end,
  goals_off = function() return KC.GL.off == true end,
  danger = function(sid) return KC.S and KC.S.danger and KC.GL.danger(sid) or 0 end,
  story_state = function() return KC.S and KC.S.story end,
  story_reset = function() KC.STORY.off = false; KC.story_restore(); KC.STORY.leaves, KC.STORY.paths = nil, nil end,   -- офлайн-тест
  ws_stats = function() return KC.WSL.stats and KC.WSL.stats() end,   -- LINKN: счётчики; final = статус городов с чужим владельцем (applied | причина пропуска | no_variant)
  ws_applied = function() return KC.WSL.applied and KC.WSL.applied() end,
  ws_inject = function(t) if KC.WSL.inject then KC.WSL.inject(t) end end,   -- офлайн-тест: подставить таблицу вариантов
  ws_reset = function() if KC.WSL.reset then KC.WSL.reset() end end,        -- офлайн-тест: как после перезапуска игры
  -- шина: подписка (см. notify у emit). pattern: "town_captured" | "stock_*" | "*"; fn(ev) — ev только читать
  subscribe = function(pattern, fn) return KC.subscribe(pattern, fn) end,
  unsubscribe = function(id) return KC.unsubscribe(id) end,
  -- склады и город: слоты в состоянии (сохраняются в сейв вместе с S); nil, пока мира нет
  stock_state = function() if KC.S then KC.ensure_slots(KC.S); return KC.S.stock end end,
  town_state = function() if KC.S then KC.ensure_slots(KC.S); return KC.S.town end end,
  day = function() return KC.S and math.max(KC.DAY, KC.S.last_day or 0) or (KC.game_day() or 0) end,
  towns = function()   -- все города и владения: { sid, name, kind, x, z, mine, owner (fid|nil), free, unrest, pop (из S.town[sid].pop, если есть) }
    local owner, unrest = {}, {}
    if KC.S then
      for fid, f in pairs(KC.S.F) do
        if f.alive then for t in pairs(f.towns) do owner[t] = fid; local u = f.unrest and f.unrest[t]; unrest[t] = u and u.level or 0 end end
      end
    end
    local out = {}
    for sid, i in pairs(KC.CFG.town_info or {}) do
      local tw = KC.S and KC.S.town and KC.S.town[sid]
      out[#out + 1] = { sid = sid, name = i.name or KC.TOWN_NAME[sid] or sid, kind = i.kind, x = i.x, z = i.z, mine = i.mine, owner = owner[sid],
                        free = (KC.S and KC.S.free and KC.S.free[sid]) and true or false, unrest = unrest[sid] or 0,
                        pop = type(tw) == "table" and tw.pop or nil, pop0 = type(tw) == "table" and tw.pop0 or nil,
                        lv = (KC.S and KC.S.stock and KC.S.stock.towns and KC.S.stock.towns[sid] and KC.S.stock.towns[sid].lv) or nil }   -- LINKS2: полки склада (доля нормы)
    end
    table.sort(out, function(p, q) return p.sid < q.sid end)
    return out
  end,
  -- LINKS2: склад -> элита (полка тратится при спавне), город <- население и беспорядки, бог хаоса по событию
  stock_spend = function(sid, cat, share)   -- списать долю нормы категории на складе города; возвращает списанное (0, если склада нет)
    local s = KC.S and KC.S.stock and KC.S.stock.towns and KC.S.stock.towns[sid]
    if not (s and s.q and s.tn and s.tn[cat] and s.q[cat]) then return 0 end
    local x = math.min(s.q[cat], s.tn[cat] * (tonumber(share) or 0))
    if x <= 0 then return 0 end
    s.q[cat] = s.q[cat] - x; s.lv = s.lv or {}; s.lv[cat] = s.q[cat] / s.tn[cat]
    return x
  end,
  town_mood = function(sid)   -- { pop, pop0, unrest (0..1.2), food (полка еды, доля нормы или nil), owner }
    if not KC.S then return nil end
    local tw = KC.S.town and KC.S.town[sid]
    local owner, un
    for fid, f in pairs(KC.S.F) do if f.alive and f.towns[sid] then owner = fid; un = f.unrest and f.unrest[sid] and f.unrest[sid].level or 0; break end end
    return { pop = type(tw) == "table" and tw.pop or nil, pop0 = type(tw) == "table" and tw.pop0 or nil, unrest = un or 0, food = KC.tlv(sid, "food"), owner = owner }
  end,
  chaos_squad = function(ev_id)   -- отряд Chaos Demons, выбранный для события chaos_incursion (nil: любой из traces.json)
    for i = #(KC.S and KC.S.events or {}), 1, -1 do local e = KC.S.events[i]; if e.id == ev_id then return e.squad, e.god, e.cause end end
  end,
  l2_state = function() return KC.S and KC.L2.state() end,
  camp = function() return KC.L2.camp end,   -- офлайн-тест: родные кампании (NATIVE_MAP п.2/п.5)
  act_test = function(fid, a, o) KC.act(fid, a, o) end,   -- офлайн-тест
  chain_owner = function(ch, fid, prefer, radius) return KC.GL.chain_owner(ch, fid, prefer, radius) end,   -- офлайн-тест B4: хозяин оков
  write_rel_test = function() KC.write_relations() end,
  coresync_test = function() KC.GL.cs_tick() end,   -- офлайн-тест S2
  coresync = function() return KC.GL.cs end,
  chaos_pick = function(fid) if KC.S then KC.DAY = math.max(KC.DAY, KC.S.last_day or KC.DAY); return KC.L2.pick(fid) end end,   -- бог, отряд, причина для кризисной фракции (офлайн-тест, консоль)
  advance = function(day) KC.advance(day) end,
  reset = function() KC.S = KC.fresh_state() end,
  serialize = function() return KC.S and KC.serialize(KC.S) end,
  choose = function(fid) return KC.choose_action(fid) end,
  _set = function(k, v) KC.P[k] = v end,          -- офлайн-тест и консоль: KMM_Conductor._set("test_mode", true)
  _test_tick = function() KC.test_tick() end,
  cities = function() local out = {}; for fid, f in pairs(KC.S.F) do if f.alive then out[fid] = KC.ncities(f) end end; return out end,
  set_base = function(x, z, value, defense) if KC.S then KC.S.base = KC.S.base or {}; local B = KC.S.base; B.known, B.x, B.z, B.value, B.defense = true, x, z, value, defense or B.defense or 30 end end,
  tier_shift = function(fid) return KC.TIER_SHIFT(fid) end,
  player_mined = function(amount, x, z) if KC.S then KC.PLAYER_MINED(amount, x, z) end end,
  region_ore = function(x, z) return KC.S and KC.REGION_ORE(x, z) or 1 end,
  fpos = function(fid) return KC.FPOS(fid) end,
  name = function(fid) return KC.name(fid) end,
  rel = function(a, b) return KC.S and KC.rel(a, b) or 0 end,
  disabled = function() return KC.DISABLED end,
  read_json = function(fname, fallback) return KC.load_json(fname, fallback) end,
  cfg = function() return KC.CFG end,
  guard_log = function(msg) KC.guard_log(msg) end,
  price_mult = function(fid)   -- цены у торговцев фракции: голод по металлу, голод, война, богатство (KMM_Traces)
    local f = KC.S and KC.S.F[fid]
    if not f then return 1 end
    local m = 1 + 0.25 * KC.clamp((f.stress or 0) - 1, 0, 1.6) + 0.2 * (f.hunger or 0) + ((KC.DAY - (f.last_war or -1000) < 20) and 0.08 or 0)
              - ((f.wealth > 2 * f.wealth0) and 0.08 or 0)
    m = m * (0.85 + 0.15 * (KC.S.metal_price or 1))
    local T = KC.P.traces or {}
    return KC.clamp(m, T.price_min or 0.8, T.price_max or 1.45)
  end,
  price_mult_town = function(fid, town_sid)   -- цена в городе: price_mult фракции x уровень склада (дефицит дороже, избыток дешевле)
    local m = KMM_Conductor.price_mult(fid)
    local ok, r = pcall(function()
      local L, T = KC.P.loop or {}, KC.P.traces or {}
      local sum, n = 0, 0
      for _, c in ipairs({ "food", "metal", "weapons" }) do local lv = KC.S and KC.tlv(town_sid, c); if lv then sum = sum + lv; n = n + 1 end end
      if n == 0 then return m end
      local avg = sum / n
      local x = (avg < 1) and (1 + (L.price_def or 0.3) * (1 - avg)) or (1 - math.min(L.price_glut_max or 0.2, (L.price_glut or 0.1) * (avg - 1)))
      local pu = KC.S and KC.S.l2 and KC.S.l2.price and KC.S.l2.price[town_sid]
      if pu and pu >= KC.DAY then x = x * (((KC.P.links2 or {}).glut or {}).price_mult or 0.9) end   -- LINKS2: перебор в городе - скидка у торговцев
      return KC.clamp(m * x, T.price_min or 0.8, T.price_max or 1.45)
    end)
    return ok and r or m
  end,
  know = function(fid) local f = KC.S and KC.S.F[fid]; return f and f.know end,
  -- ROBBERY: добыча фракции (категория cat в единицах склада, жертва victim_fid) → через robbery.sell_days сбыт в ближайшем союзном/нейтральном городе
  loot_add = function(fid, cat, n, victim)
    if not KC.S or KC.GL.h_live(KC.XDIS, "loot_add") then return false end
    KC.DAY = math.max(KC.DAY, KC.S.last_day or KC.DAY)
    local ok, r = pcall(KC.loot_add_impl, fid, cat, n, victim)
    if not ok then KC.GL.h_bad(KC.XDIS, "loot_add", "KMM_Conductor.loot_add", r, "loot_add", KC.guard_log); return false end
    KC.GL.h_done(KC.XDIS, "loot_add")
    return r
  end,
  loot_of = function(fid) local L = KC.S and KC.S.loot and KC.S.loot[fid]; local out = {}; for _, e in ipairs(L or {}) do out[#out + 1] = { c = e.c, n = e.n, day = e.day, b = e.b } end; return out end,
  waylay_ok = function(a, b) if not KC.S then return false end; KC.DAY = math.max(KC.DAY, KC.S.last_day or KC.DAY); local ok, r = pcall(KC.waylay_ok, a, b); return ok and r or false end,
  set_ambush_probe = function(fn) KC.AMB_PROBE = fn end,
  ambush_pending = function() local n = 0; for _ in pairs(KC.S and KC.S.ambush or {}) do n = n + 1 end; return n end,
  _ambush_expire = function() if KC.S then KC.DAY = math.max(KC.DAY, KC.S.last_day or KC.DAY); KC.ambush_expire() end end,
  _act = function(fid, a, o) if KC.S then KC.DAY = math.max(KC.DAY, KC.S.last_day or KC.DAY); KC.act(fid, a, o) end end,   -- офлайн-тест REV2
  _waylay = function(a, b) if KC.S then KC.DAY = math.max(KC.DAY, KC.S.last_day or KC.DAY); KC.waylay_do(a, b) end end,
  _loot_step = function() if KC.S then KC.DAY = math.max(KC.DAY, KC.S.last_day or KC.DAY); KC.loot_step() end end,
  -- ROADS: план пути, отправка (списание источника), прибытие (зачёт), память дорог игрока
  road_plan = function(kind, fid, o) if not (KC.S and KC.RDS.rd_on(kind == "caravan" and "caravans" or (kind == "wanderer" and "wanderers" or (kind == "courier" and "couriers" or "refugees")))) then return nil end; KC.DAY = math.max(KC.DAY, KC.S.last_day or KC.DAY); return KC.RDS.rsafe("plan", KC.RDS.road_plan_impl, kind, fid, o) end,
  road_depart = function(plan) if not KC.S then return nil end; KC.DAY = math.max(KC.DAY, KC.S.last_day or KC.DAY); return KC.RDS.rsafe("depart", KC.RDS.road_depart_impl, plan) end,
  road_claim = function(kind, fid, from) if not (KC.S and KC.RDS.rd_on("refugees")) then return nil end; KC.DAY = math.max(KC.DAY, KC.S.last_day or KC.DAY); return KC.RDS.rsafe("claim", KC.RDS.road_claim_impl, kind, fid, from) end,
  road_arrive = function(id, how) if not KC.S then return false end; KC.DAY = math.max(KC.DAY, KC.S.last_day or KC.DAY); return KC.RDS.rsafe("arrive", KC.RDS.rd_arrive, id, how or "visible") end,
  road_lost = function(id) if not KC.S then return false end; local r = KC.RDS.rd_slot(); if r.tr[id] then r.tr[id] = nil; KC.RDS.rd_stat("lost"); return true end; return false end,
  road_wanderer = function(fid) return KC.S and KC.RDS.rd_on("wanderers") and KC.RDS.rsafe("wanderer", KC.RDS.rd_wanderer_ok, fid) or false end,
  road_visit = function(x, z) if KC.S then KC.DAY = math.max(KC.DAY, KC.S.last_day or KC.DAY); KC.RDS.rsafe("visit", KC.RDS.road_visit_impl, x, z) end end,
  road_heat = function(x, z) return KC.S and KC.RDS.rd_on("grid") and KC.RDS.rsafe("heat", KC.RDS.road_heat_impl, x, z) or 0 end,
  road_route_heat = function(x1, z1, x2, z2) return KC.S and KC.RDS.rd_on("grid") and KC.RDS.rsafe("heat", KC.RDS.road_route_heat_impl, x1, z1, x2, z2) or 0 end,
  road_grid = function() return KC.S and KC.RDS.rsafe("grid", KC.RDS.road_grid_list) or {} end,
  road_state = function() return KC.S and KC.RDS.rd_slot() end,
  road_off = function() return KC.RDS.ROADS_OFF end,
  tribute_pairs = function()   -- активные вассалитеты: { suzerain, vassal } (DIPLO)
    local out = {}
    if KC.S then for _, t in pairs(KC.S.treaties) do if t.active and t.type == "vassal" and KC.S.F[t.a] and KC.S.F[t.b] and KC.S.F[t.a].alive and KC.S.F[t.b].alive then out[#out + 1] = { t.a, t.b } end end end
    table.sort(out, function(p, q) if p[1] ~= q[1] then return p[1] < q[1] end return p[2] < q[2] end)
    return out
  end,
  hit = function(fid) if KC.S then KC.DAY = KC.S.last_day; KC.emit({ type = "attack_on_player", a = fid, b = KC.CFG.player_faction, text = "test" }) end end,
}
_G.KMM_Conductor = KMM_Conductor   -- init-скрипты KenshiLua в своих песочницах: публикуем для Traces/Self/Ore/Diplo
end
KC._BOOT()
