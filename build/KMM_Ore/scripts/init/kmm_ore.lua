-- KMM_Ore v2 (2026-11-12) — истощение рудных узлов игрока (LATE_GAME.md «Пик руды»), безопасный путь.
--
-- v1 вешал хуки движка при загрузке скрипта (ProductionBuilding::_NV_operate, Building::_NV_onBuildingLoaded) — игра падала
-- сразу после загрузки сейва. v2:
--   * при загрузке модуль только объявляет функции, таблицу KMM_Ore и один обработчик общего тика GameWorld::charsUpdate
--     (тот же, что у KMM_Conductor/KMM_Traces/KMM_Self/KMM_Rumors; новых хуков движка нет); ни I/O, ни вызовов API игры;
--   * конфиг читается лениво в первом тике; работа начинается только когда у игрока есть персонажи, после задержки
--     (реальные секунды + число опросов + сдвиг игрового времени);
--   * узлы не перехватываются, а опрашиваются: персонаж игрока → текущее действие → его цель (hand) → здание; если это рудный
--     узел из ore_config.templates и персонаж рядом — его игровые часы работы списываются с запаса узла R («работо-часы»);
--   * порции: chars_per_poll персонажей за опрос, опрос не чаще poll_seconds;
--   * выход: _resourceMiningLevel = base * max(floor, (R/R0)^k), base — ванильный уровень при первом контакте;
--   * запас нового поверхностного узла = R0 × остаток жил региона мира у дирижёра (KMM_Conductor.region_ore), труд игрока
--     списывается и с ближайшей жилы мира (KMM_Conductor.player_mined); всё под pcall, ошибка отключает только связь;
--   * состояние — файл на мир (ключ = семя мира дирижёра), лог — logs/ore.log;
--   * безотказность: любая ошибка Lua в тике отключает поток до конца сессии, причина → logs/debug.log; наружу не выходит.

local TAG = "[KMM_Ore] "
local VERSION = "v2"

local DEFAULTS = {
  ore_enabled = true, write_level = true, tick_source = "own",
  log_path = "C:/KenshiModMap/logs/ore.log", debug_log = "C:/KenshiModMap/logs/debug.log",
  state_path = "C:/KenshiModMap/logs/ore_nodes_%s.tsv", world_key = "conductor",
  start_delay_seconds = 8, start_delay_polls = 8, start_delay_hours = 0.05,
  poll_seconds = 1.0, chars_per_poll = 4, work_radius = 800, max_dt_hours = 2.0, work_task_types = { 87, 152, 189 },
  save_every_seconds = 60, log_every_hours = 6,
  feed_conductor = true, player_to_world = 0.25, region_min = 0.15,
  templates = { ["14521-rebirth.mod"] = "surface", ["42248-gamedata.base"] = "surface", ["42249-gamedata.base"] = "surface",
                ["99106-Boneyard Wolf.mod"] = "surface", ["99107-Boneyard Wolf.mod"] = "surface",
                ["2056-gamedata.base"] = "mine", ["2094-gamedata.base"] = "mine", ["2095-gamedata.base"] = "mine",
                ["2096-gamedata.base"] = "mine", ["2097-gamedata.base"] = "mine", ["2098-gamedata.base"] = "mine" },
  classes = { surface = { R0 = 400, k = 1.5, floor = 0.02, regen_per_day = 0 }, mine = { R0 = 1200, k = 1.0, floor = 0.25, regen_per_day = 24 } },
}

local cfg            -- nil до первого тика
local TASKS = {}     -- множество допустимых TaskType
local DISABLED = {}
local RT = {         -- состояние сессии (не сейва)
  t_poll = {}, ready = false, polls = 0, seen_clock = nil, seen_day = nil,
  world = nil, nodes = {}, dirty = false, t_save = 0, rr = 0, char_day = {}, diag_task = {}, diag_tpl = {},
  stats = { polls = 0, work_hours = 0, writes = 0, nodes_new = 0, saves = 0 },
}

---------------------------------------------------------------------------------------------- лог и guard
local function append(path, line)
  local ok, f = pcall(io.open, path, "a")
  if ok and f then f:write(line, "\n"); f:close(); return true end
  return false
end
local function klog(msg)
  msg = TAG .. tostring(msg)
  if not (KenshiLua and pcall(function() KenshiLua.log(msg) end)) then print(msg) end
end
local function game_day()
  local ok, d = pcall(function() return getGameWorld():getTimeStamp_inGameHours():getTotalDays() end)
  if ok and type(d) == "number" then return d end
  return nil
end
local function olog(msg)
  append((cfg and cfg.log_path) or DEFAULTS.log_path,
    os.date("%Y-%m-%d %H:%M:%S") .. "\t" .. string.format("day %.2f", game_day() or -1) .. "\t" .. tostring(msg))
end
local function dlog(msg)
  append((cfg and cfg.debug_log) or DEFAULTS.debug_log, os.date("%Y-%m-%d %H:%M:%S") .. " [KMM_Ore] " .. tostring(msg))
  klog(msg)
end
local function guarded(nm, fn)
  return function(...)
    if DISABLED[nm] then return end
    local ok, err = pcall(fn, ...)
    if not ok then DISABLED[nm] = true; dlog(nm .. " disabled until restart: " .. tostring(err)) end
  end
end

---------------------------------------------------------------------------------------------- конфиг (лениво)
local function load_cfg()
  local c = {}
  for k, v in pairs(DEFAULTS) do c[k] = v end
  local ok, user = pcall(require, "ore_config")
  if ok and type(user) == "table" then for k, v in pairs(user) do c[k] = v end end
  cfg = c
  -- B7 (2026-11-15, EnumsReference TaskType): добыча = 87 OPERATE_MACHINERY, 152 OPERATE_AUTOMATIC_MACHINERY, 189 AUTO_LABOURING_MINES
  -- (труд в шахтах). 190 AUTO_LABOURING_MINES_PRETEND и 221 PRETEND_TO_OPERATE_MACHINERY — «изображать работу» без выработки: не считаем,
  -- но фиксируем в ore.log (SKIP task), если персонаж с ними стоит у рудного узла. Базовый список объединяется со списком ore_config.
  TASKS = {}
  for _, t in ipairs(DEFAULTS.work_task_types) do TASKS[t] = true end
  for _, t in ipairs(cfg.work_task_types or {}) do TASKS[t] = true end
  if not (ok and type(user) == "table") then klog("ore_config not loaded, defaults used: " .. tostring(user)) end
end

---------------------------------------------------------------------------------------------- состояние узлов (файл на мир)
local function world_key()
  if cfg.world_key == "global" then return "global" end
  if KMM_Conductor == nil then return "global" end          -- дирижёра нет вовсе — одно состояние
  local ok, k = pcall(function() local S = KMM_Conductor.state(); return S and S.seed and S.seed.r end)
  if ok and k then return "w" .. tostring(k) end
  return nil                                                 -- дирижёр есть, но мир ещё не готов — ждём
end
local function state_file() return string.format(cfg.state_path, RT.world or "global") end

local function load_state()
  local nodes, n = {}, 0
  local ok, f = pcall(io.open, state_file(), "r")
  if not (ok and f) then return nodes, 0 end
  for line in f:lines() do
    local key, cls, tpl, R, base, last_day, hours, R0 = line:match("^([^\t]+)\t([^\t]+)\t([^\t]+)\t([^\t]+)\t([^\t]+)\t([^\t]+)\t([^\t]+)\t([^\t\r]+)")
    if key and cfg.classes[cls] and tonumber(R) and tonumber(R0) then
      nodes[key] = { cls = cls, tpl = tpl, R = tonumber(R), base = tonumber(base) or -1, last_day = tonumber(last_day) or -1,
                     hours = tonumber(hours) or 0, R0 = tonumber(R0), logged_day = -1e9 }
      n = n + 1
    end
  end
  f:close()
  return nodes, n
end
local function save_state()
  local f = io.open(state_file(), "w")
  if not f then error("cannot write " .. state_file()) end
  for key, s in pairs(RT.nodes) do
    f:write(table.concat({ key, s.cls, s.tpl, string.format("%.3f", s.R), string.format("%.4f", s.base or -1),
      string.format("%.3f", s.last_day or -1), string.format("%.3f", s.hours or 0), string.format("%.1f", s.R0) }, "\t"), "\n")
  end
  f:close()
  RT.dirty = false
  RT.t_save = os.clock()
  RT.stats.saves = RT.stats.saves + 1
end
local g_save = guarded("save", save_state)

local function ensure_world()
  local key = world_key()
  if not key then return false end
  if key ~= RT.world then
    if RT.world and RT.dirty then g_save() end
    RT.world = key
    local n
    RT.nodes, n = load_state()
    RT.char_day = {}
    olog(string.format("KMM_Ore %s active: world=%s nodes in state=%d write_level=%s", VERSION, key, n, tostring(cfg.write_level)))
  end
  return true
end

---------------------------------------------------------------------------------------------- связь с дирижёром (необязательна)
local function link_fail(err) DISABLED.conductor_link = true; dlog("conductor_link disabled until restart: " .. tostring(err)) end
local function region_share(x, z)
  if not cfg.feed_conductor or DISABLED.conductor_link or not (KMM_Conductor and KMM_Conductor.region_ore) then return 1 end
  local ok, v = pcall(KMM_Conductor.region_ore, x, z)
  if not ok then link_fail(v); return 1 end
  return tonumber(v) or 1
end
local function feed_world(amount, x, z)
  if not cfg.feed_conductor or DISABLED.conductor_link or not (KMM_Conductor and KMM_Conductor.player_mined) then return end
  local ok, err = pcall(KMM_Conductor.player_mined, amount, x, z)
  if not ok then link_fail(err) end
end

---------------------------------------------------------------------------------------------- модель узла
local function coefficient(s)
  local c = cfg.classes[s.cls]
  return math.max(c.floor, (math.max(0, s.R) / s.R0) ^ c.k)
end
local function regen(s, day)
  local c = cfg.classes[s.cls]
  if s.last_day and s.last_day >= 0 and c.regen_per_day > 0 and day > s.last_day then
    s.R = math.min(s.R0, s.R + (day - s.last_day) * c.regen_per_day)
  end
  s.last_day = day
end
local function apply_level(pb, s)
  if not cfg.write_level or not s.base or s.base <= 0 then return nil end
  local target = s.base * coefficient(s)
  local cur = pb._resourceMiningLevel
  if type(cur) ~= "number" or math.abs(cur - target) > 1e-4 then
    pb._resourceMiningLevel = target
    RT.stats.writes = RT.stats.writes + 1
  end
  return target
end
-- Остаток залежи в названии узла (по итогам плейтеста 2026-11-13: жила вырабатывается непредсказуемо). Название видно
-- в панели, которая открывается по клику на залежь (там же работники и эффективность). Формат: «Iron [ore left 73%]».
-- Меняем только при сдвиге на >= 1 %; ошибка API (нет getName/setName) отключает только показ.
local function show_left(pb, s)
  if cfg.show_left == false or DISABLED.show_left then return end
  local pct = math.floor(math.max(0, s.R) / s.R0 * 100 + 0.5)
  if s.shown == pct then return end
  local ok, err = pcall(function()
    local nm = pb:getName()
    if type(nm) ~= "string" then return end
    local base = string.gsub(nm, " %[[^%]]*%]$", "")
    pb:setName(string.format("%s [%s %d%%]", base, cfg.left_label or "ore left", pct))
  end)
  if ok then s.shown = pct else DISABLED.show_left = true; dlog("show_left disabled until restart: " .. tostring(err)) end
end
local function node_of(pb, tpl, cls, x, z, day)
  local key = string.format("%s@%d,%d", tpl, math.floor(x + 0.5), math.floor(z + 0.5))
  local s = RT.nodes[key]
  if s then return s, key end
  local lv = pb._resourceMiningLevel                         -- поле, не метод: без пересчёта движком
  local base = (type(lv) == "number" and lv > 0) and lv or -1
  local share = (cls == "surface") and math.max(cfg.region_min, math.min(1, region_share(x, z))) or 1
  local R0 = cfg.classes[cls].R0 * share
  s = { cls = cls, tpl = tpl, R = R0, R0 = R0, base = base, last_day = day, hours = 0, logged_day = -1e9 }
  RT.nodes[key] = s
  RT.dirty = true
  RT.stats.nodes_new = RT.stats.nodes_new + 1
  olog(string.format("NEW node %s class=%s base_level=%s R0=%.0f (region %.2f)", key, cls, tostring(base), R0, share))
  return s, key
end

---------------------------------------------------------------------------------------------- опрос персонажа
local function xz(v) if v then return v.x or v[1], v.z or v[3] end end
local function char_key(ch)
  local ok, k = pcall(function() return ch:getHandle():toString() end)
  if ok and type(k) == "string" and k ~= "" then return k end
  return tostring(ch)
end
-- рудный узел, на котором персонаж сейчас работает: pb, tpl, cls, x, z (или nil). Ошибки API не глотаются — их ловит guard.
local function work_of(ch)
  local body = ch:getBody()
  if not body then return nil end
  local act = body:getCurrentAction()
  if not act then return nil end
  local k = act:key()
  local counted = type(k) ~= "number" or TASKS[k]
  if not counted then   -- диагностика B7: чужая задача проверяется до 3 раз за сессию — не стоит ли персонаж с ней у рудного узла
    local n = RT.diag_task[k] or 0
    if n >= 3 then return nil end
    RT.diag_task[k] = n + 1
  end
  local h = act.subject
  if not h or not h:isValid() then return nil end
  local b = h:getBuilding()
  if not b then return nil end
  local pb = b:getProductionBuilding()
  if not pb then return nil end
  local gd = pb:getGameData()
  local tpl = gd and gd.stringID
  local cls = tpl and cfg.templates[tpl]
  if not cls then
    if counted and tpl and not RT.diag_tpl[tpl] then
      RT.diag_tpl[tpl] = true
      olog(string.format("SKIP template %s (%s) task=%s: production node not in ore_config.templates", tpl, tostring(gd.name), tostring(k)))
    end
    return nil
  end
  local bx, bz = xz(pb:getPosition())
  local cx, cz = xz(ch:getPosition())
  if not (bx and cx) then return nil end
  if (bx - cx) ^ 2 + (bz - cz) ^ 2 > cfg.work_radius ^ 2 then return nil end
  if not counted then
    RT.diag_task[k] = 3
    olog(string.format("SKIP task=%s at ore node %s: TaskType not in work_task_types (pretend/haul?)", tostring(k), tpl))
    return nil
  end
  return pb, tpl, cls, bx, bz
end

local function work(pb, tpl, cls, x, z, hours, day)
  local s, key = node_of(pb, tpl, cls, x, z, day)
  regen(s, day)
  if hours > 0 then
    s.R = s.R - hours
    s.hours = (s.hours or 0) + hours
    RT.dirty = true
    RT.stats.work_hours = RT.stats.work_hours + hours
    feed_world(hours * cfg.player_to_world, x, z)
  end
  local after = apply_level(pb, s)
  show_left(pb, s)
  if (day - (s.logged_day or -1e9)) * 24 >= cfg.log_every_hours then
    s.logged_day = day
    olog(string.format("MINE %s R=%.1f/%.0f coef=%.3f level=%s worked=%.1fh", key, s.R, s.R0, coefficient(s),
      after and string.format("%.3f", after) or "-", s.hours))
    if s.R <= 0 and cls == "surface" then olog("DEPLETED " .. key) end
  end
end

local function player_chars()
  local ok, list = pcall(function()
    local pi = getPlayerInterface()
    if not pi then return nil end
    local all = pi:getAllPlayerCharacters()
    if not all then return nil end
    local out = {}
    for _, c in pairs(all) do if c then out[#out + 1] = c end end
    return out
  end)
  if ok then return list end
  return nil   -- главное меню / загрузка: интерфейса игрока ещё нет — это «не готов», не ошибка
end

local function step(pcs, day)
  local n = #pcs
  for _ = 1, math.min(n, cfg.chars_per_poll) do
    RT.rr = RT.rr % n + 1
    local ch = pcs[RT.rr]
    local ck = char_key(ch)
    local last = RT.char_day[ck]
    RT.char_day[ck] = day
    local pb, tpl, cls, x, z = work_of(ch)
    if pb then
      local hours = (last and day > last) and math.min(cfg.max_dt_hours, (day - last) * 24) or 0
      work(pb, tpl, cls, x, z, hours, day)
    end
  end
end

---------------------------------------------------------------------------------------------- тик
local function reset_ready()
  RT.ready, RT.polls, RT.seen_clock, RT.seen_day = false, 0, nil, nil
  RT.char_day = {}
end

local function tick(from_conductor)
  local src = from_conductor and "conductor" or "own"
  local t = os.clock()
  if t - (RT.t_poll[src] or -1e9) < ((cfg and cfg.poll_seconds) or 1) then return end
  RT.t_poll[src] = t
  if not cfg then load_cfg() end
  if not cfg.ore_enabled then return end
  if cfg.tick_source == "conductor" and not from_conductor then return end
  local pcs = player_chars()
  if not pcs or #pcs == 0 then if RT.ready or RT.seen_clock then reset_ready() end; return end
  local day = game_day()
  if not day then return end
  if not RT.ready then   -- ленивый старт: персонажи есть уже N опросов, M секунд и игровое время пошло
    RT.polls = RT.polls + 1
    if not RT.seen_clock then RT.seen_clock, RT.seen_day = t, day; return end
    if RT.polls < cfg.start_delay_polls or t - RT.seen_clock < cfg.start_delay_seconds
       or (day - RT.seen_day) * 24 < cfg.start_delay_hours then return end
    RT.ready = true
    RT.char_day = {}
  end
  if not ensure_world() then return end
  RT.stats.polls = RT.stats.polls + 1
  step(pcs, day)
  if RT.dirty and t - RT.t_save >= cfg.save_every_seconds then g_save() end
end
local g_tick = guarded("tick", tick)

---------------------------------------------------------------------------------------------- регистрация: только общий тик
KMM_Ore = KMM_Ore or {}
KMM_Ore.version = VERSION
KMM_Ore.tick = function() g_tick(true) end            -- для вызова из тика дирижёра (cfg.tick_source = "conductor")
KMM_Ore.disabled = function() return DISABLED end
KMM_Ore.stats = function() return RT.stats end
KMM_Ore.nodes = function() return RT.nodes end
KMM_Ore.status = function()
  return string.format("%s enabled=%s ready=%s world=%s nodes=%d polls=%d work=%.1fh writes=%d disabled=%s", VERSION,
    tostring(cfg and cfg.ore_enabled), tostring(RT.ready), tostring(RT.world), (function() local k = 0; for _ in pairs(RT.nodes) do k = k + 1 end; return k end)(),
    RT.stats.polls, RT.stats.work_hours, RT.stats.writes, (function() local t = {}; for k in pairs(DISABLED) do t[#t + 1] = k end; return table.concat(t, ",") end)())
end
KMM_Ore.save = function() if RT.dirty and RT.world then g_save() end end
KMM_Ore._rt = RT

if KMM_Ore._handler and Events and Events.off then pcall(Events.off, KMM_Ore._handler) end   -- перезагрузка скрипта не дублирует
if Events and Events.on then KMM_Ore._handler = Events.on("GameWorld::charsUpdate", guarded("tick_hook", function() if _G.KMM_Gov then return KMM_Gov.run("ore", g_tick, false) else return g_tick(false) end end)) end
