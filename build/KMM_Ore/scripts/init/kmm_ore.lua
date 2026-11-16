-- KMM_Ore v3 (2026-11-15) — рудные узлы игрока как часть жилы региона (docs/core/economy_player.md, раздел «Руда»).
--
-- v1 вешал хуки движка при загрузке скрипта (ProductionBuilding::_NV_operate, Building::_NV_onBuildingLoaded) — игра падала
-- сразу после загрузки сейва. v2/v3: при загрузке модуль только объявляет функции, таблицу KMM_Ore и один обработчик общего тика
-- GameWorld::charsUpdate; ни I/O, ни вызовов API игры. Конфиг и данные читаются лениво в первом тике, работа — после задержки.
--
-- Что считается (всё под pcall, ошибка отключает только свою часть до конца сессии, причина → logs/debug.log):
--   * труд персонажей игрока: действие → цель (subject, затем currentSubTarget) → здание → рудный шаблон; часы работы
--     списываются с запаса узла R («работо-часы»);
--   * автоматические буры игрока (шаблоны с auto в ore_templates.lua): скан зданий вокруг персонажей (getObjectsWithinSphere),
--     часы работы под питанием без шахтёра;
--   * приказ игрока на рудный узел (PlayerInterface::newPlayerTaskSelectedCharacters, подписка в первом рабочем тике):
--     TaskType приказа добавляется к рабочим задачам сессии (LEARN) — счёт не зависит от догадки о номере задачи;
--   * выход: _resourceMiningLevel = base * max(floor, (R/R0)^k) * жила региона; base — ванильный уровень при первом контакте,
--     жила региона = KMM_Conductor.region_ore (остаток мировых жил вокруг узла; NPC и игрок черпают её вместе);
--   * труд игрока × player_to_world списывается с ближайшей жилы мира порциями (KMM_Conductor.player_mined);
--   * состояние узлов — в состоянии дирижёра S.ore_nodes (пишется в сейв вместе с миром и откатывается с ним);
--     без дирижёра — файл logs/ore_nodes_<мир>.tsv (он же пишется всегда как запасной и для импорта);
--   * лог — logs/ore.log: active, NEW, MINE, AUTO, ORDER/LEARN, CHAIN (где обрывается цепочка), SKIP, DEPLETED.

local TAG = "[KMM_Ore] "
local VERSION = "v3"

local DEFAULTS = {
  ore_enabled = true, write_level = true, tick_source = "own",
  log_path = "C:/KenshiModMap/logs/ore.log", debug_log = "C:/KenshiModMap/logs/debug.log",
  state_path = "C:/KenshiModMap/logs/ore_nodes_%s.tsv", world_key = "conductor", state_in_save = true,
  start_delay_seconds = 8, start_delay_polls = 8, start_delay_hours = 0.05,
  poll_seconds = 1.0, chars_per_poll = 4, work_radius = 800, max_dt_hours = 2.0, work_task_types = { 87, 152, 189 },
  pretend_task_types = { 190, 221 }, subject_fields = { "subject", "currentSubTarget" }, diag_task_checks = 3,
  learn_orders = true, learn_max = 4,
  scan_enabled = true, scan_seconds = 30, scan_radius = 3000, scan_max_objects = 80, auto_rate = 1.0, auto_max_hours = 6,
  region_live = true, region_k = 1.0, region_floor = 0.2, region_refresh_hours = 6,
  feed_conductor = true, player_to_world = 0.25, feed_every_hours = 2, recent_days = 10,
  save_every_seconds = 60, log_every_hours = 6, diag_every_hours = 12,
  templates = {},
  classes = { surface = { R0 = 400, k = 1.5, floor = 0.02, regen_per_day = 0 }, mine = { R0 = 1200, k = 1.0, floor = 0.25, regen_per_day = 24 } },
}

local cfg            -- nil до первого тика
local TASKS, PRETEND, LEARNED = {}, {}, {}
local TPL, FUNCS = {}, {}   -- stringID -> { cls, res, auto } | false (не руда); stringID функциональности -> ресурс
local DISABLED = {}
local RT = {         -- состояние сессии (не сейва)
  t_poll = {}, ready = false, polls = 0, seen_clock = nil, seen_day = nil,
  world = nil, S = false, nodes = {}, view = {}, dirty = false, t_save = 0, rr = 0, char_day = {}, diag_task = {}, diag_tpl = {},
  feed = {}, feed_day = nil, t_scan = -1e9, scan_rr = 0, buf = nil, hooked = nil, order_seen = {},
  chain = {}, chain_keys = {}, chain_day = nil, src = "?",
  stats = { polls = 0, work_hours = 0, auto_hours = 0, writes = 0, nodes_new = 0, saves = 0, orders = 0, scans = 0, fed = 0 },
}

---------------------------------------------------------------------------------------------- лог и guard
-- Только целый UTF-8 в логи: LuaJIT обрезает имя чанка в тексте ошибки ([string "-- KMM_Ore v3 — …"]) по байтам,
-- посреди кириллической буквы; битый байт ломает чтение лога (session_report, тесты). Невалидные байты → «?».
local function utf8_clean(s)
  s = tostring(s)
  if not s:find("[\128-\255]") then return s end
  local out, i, n = {}, 1, #s
  while i <= n do
    local c = s:byte(i)
    local len = c < 0x80 and 1 or (c >= 0xC2 and c <= 0xDF) and 2 or (c >= 0xE0 and c <= 0xEF) and 3 or (c >= 0xF0 and c <= 0xF4) and 4 or 0
    local good = len > 0 and i + len - 1 <= n
    for j = i + 1, i + len - 1 do
      if not good then break end
      local b = s:byte(j)
      if b < 0x80 or b > 0xBF then good = false end
    end
    if good then out[#out + 1] = s:sub(i, i + len - 1); i = i + len else out[#out + 1] = "?"; i = i + 1 end
  end
  return table.concat(out)
end
local function append(path, line)
  line = utf8_clean(line)
  local ok, f = pcall(io.open, path, "a")
  if ok and f then f:write(line, "\n"); f:close(); return true end
  return false
end
local function klog(msg)
  msg = utf8_clean(TAG .. tostring(msg))
  local kl = rawget(_G, "KenshiLua")
  if not (kl and pcall(function() kl.log(msg) end)) then print(msg) end
end
local function game_day()
  local ok, d = pcall(function() return rawget(_G, "getGameWorld")():getTimeStamp_inGameHours():getTotalDays() end)
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
local function conductor() return rawget(_G, "KMM_Conductor") end

---------------------------------------------------------------------------------------------- конфиг и шаблоны (лениво)
local function load_cfg()
  local c = {}
  for k, v in pairs(DEFAULTS) do c[k] = v end
  local ok, user = pcall(require, "ore_config")
  if ok and type(user) == "table" then for k, v in pairs(user) do c[k] = v end end
  cfg = c
  -- B7 (EnumsReference TaskType): 87 OPERATE_MACHINERY, 152 OPERATE_AUTOMATIC_MACHINERY, 189 AUTO_LABOURING_MINES — добыча;
  -- 190/221 — «изображать работу» без выработки: не считаем. Базовый список объединяется со списком ore_config.
  TASKS, PRETEND = {}, {}
  for _, t in ipairs(DEFAULTS.work_task_types) do TASKS[t] = true end
  for _, t in ipairs(cfg.work_task_types or {}) do TASKS[t] = true end
  for _, t in ipairs(cfg.pretend_task_types or DEFAULTS.pretend_task_types) do PRETEND[t] = true; TASKS[t] = nil end
  TPL, FUNCS = {}, {}
  local okt, gen = pcall(require, "ore_templates")   -- генератор _dev/gen_ore_templates.py: все рудные узлы и буры цепочки модов
  if okt and type(gen) == "table" then
    for sid, v in pairs(gen.templates or {}) do
      if type(v) == "table" then TPL[sid] = { cls = v[1], res = v[2], auto = v[3] == true } end
    end
    for sid, r in pairs(gen.funcs or {}) do FUNCS[sid] = r end
  else
    klog("ore_templates not loaded, ore_config.templates only: " .. tostring(gen))
  end
  for sid, cls in pairs(cfg.templates or {}) do   -- ручной список поверх: "surface" | "mine" | false (исключить)
    if cls == false then TPL[sid] = false
    elseif type(cls) == "string" then
      local t = TPL[sid] or {}
      t.cls = cls
      TPL[sid] = t
    end
  end
  if not (ok and type(user) == "table") then klog("ore_config not loaded, defaults used: " .. tostring(user)) end
end
local function count_tpl() local n = 0; for _, v in pairs(TPL) do if v then n = n + 1 end end; return n end

-- шаблон здания → (tpl, запись) | (tpl, nil) — не руда. Сначала таблица, затем запасной путь по функциональности шаблона.
local function classify(gd)
  local tpl = gd and gd.stringID
  if type(tpl) ~= "string" then return nil, nil end
  local t = TPL[tpl]
  if t == false then return tpl, nil end
  if t then
    if t.cls and cfg.classes[t.cls] then return tpl, t end
    return tpl, nil
  end
  if DISABLED.funcs or next(FUNCS) == nil then TPL[tpl] = false; return tpl, nil end
  local ok, res = pcall(function()
    local n = tonumber(gd:getListSize("functionality")) or 0
    for i = 0, math.min(n, 5) - 1 do   -- индексы 0..n-1: getFromList за концом списка — чтение мимо вектора в C++
      local f = gd:getFromList("functionality", i)
      if f and FUNCS[f] then return FUNCS[f] end
    end
    return nil
  end)
  if not ok then DISABLED.funcs = true; dlog("funcs fallback disabled until restart: " .. tostring(res)); TPL[tpl] = false; return tpl, nil end
  if not res then TPL[tpl] = false; return tpl, nil end
  local nm = string.lower(tostring(gd.name or ""))
  t = { cls = (nm:find("drill") or nm:find("mine")) and "mine" or "surface", res = res, auto = nm:find("auto") ~= nil }
  TPL[tpl] = t
  olog(string.format("LEARN template %s (%s) class=%s res=%s auto=%s: ore functionality, not in ore_templates", tpl, tostring(gd.name), t.cls, res, tostring(t.auto)))
  return tpl, t
end

---------------------------------------------------------------------------------------------- состояние узлов
-- запись узла (сериализуемая, лежит в S.ore_nodes дирижёра или в файле): cls, tpl, R, R0, base, last_day, hours, recent, res
-- вид узла (только сессия): RT.view[key] = { logged_day, shown, reg, reg_day, x, z, char_day, mach_day }
local function view(key) local v = RT.view[key]; if not v then v = {}; RT.view[key] = v end; return v end

local function world_key()
  if cfg.world_key == "global" then return "global" end
  local C = conductor()
  if C == nil then return "global" end                         -- дирижёра нет вовсе — одно состояние
  local ok, k = pcall(function() local S = C.state(); return S and S.seed and S.seed.r end)
  if ok and k then return "w" .. tostring(k) end
  return nil                                                 -- дирижёр есть, но мир ещё не готов — ждём
end
local function cstate()
  if cfg.state_in_save == false then return nil end
  local C = conductor()
  if not (C and C.state) then return nil end
  local ok, S = pcall(C.state)
  if ok and type(S) == "table" then return S end
  return nil
end
local function state_file() return string.format(cfg.state_path, RT.world or "global") end

local function load_file()
  local nodes, n = {}, 0
  local ok, f = pcall(io.open, state_file(), "r")
  if not (ok and f) then return nodes, 0 end
  for line in f:lines() do
    local key, cls, tpl, R, base, last_day, hours, R0, recent = line:match("^([^\t]+)\t([^\t]+)\t([^\t]+)\t([^\t]+)\t([^\t]+)\t([^\t]+)\t([^\t]+)\t([^\t\r]+)\t?([^\t\r]*)")
    if key and cfg.classes[cls] and tonumber(R) and tonumber(R0) then
      nodes[key] = { cls = cls, tpl = tpl, R = tonumber(R), base = tonumber(base) or -1, last_day = tonumber(last_day) or -1,
                     hours = tonumber(hours) or 0, R0 = tonumber(R0), recent = tonumber(recent) or 0 }
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
      string.format("%.3f", s.last_day or -1), string.format("%.3f", s.hours or 0), string.format("%.1f", s.R0),
      string.format("%.2f", s.recent or 0) }, "\t"), "\n")
  end
  f:close()
  RT.dirty = false
  RT.t_save = os.clock()
  RT.stats.saves = RT.stats.saves + 1
end
local g_save = guarded("save", save_state)
local function count(t) local k = 0; for _ in pairs(t) do k = k + 1 end; return k end

local flush_feed   -- ниже
local function ensure_world()
  local key = world_key()
  if not key then return false end
  local S = cstate() or false
  if key ~= RT.world or S ~= RT.S then
    if RT.world then flush_feed(true); if RT.dirty then g_save() end end
    RT.world, RT.S = key, S
    local src, n
    if S then   -- узлы живут в состоянии мира дирижёра: сохраняются в сейв и откатываются вместе с ним
      if type(S.ore_nodes) ~= "table" then
        local fn
        fn, n = load_file()
        S.ore_nodes = fn
        src = n > 0 and "file->save" or "save(new)"
      else
        src = "save"
      end
      RT.nodes = S.ore_nodes
      n = count(RT.nodes)
    else
      RT.nodes, n = load_file()
      src = "file"
    end
    RT.view, RT.char_day, RT.feed, RT.src = {}, {}, {}, src
    olog(string.format("KMM_Ore %s active: world=%s nodes in state=%d source=%s write_level=%s templates=%d", VERSION, key, n, src,
      tostring(cfg.write_level), count_tpl()))
  end
  return true
end

---------------------------------------------------------------------------------------------- связь с дирижёром (необязательна)
local function link_fail(err) DISABLED.conductor_link = true; dlog("conductor_link disabled until restart: " .. tostring(err)) end
local function region_share(x, z)
  local C = conductor()
  if not cfg.feed_conductor or DISABLED.conductor_link or not (C and C.region_ore) then return 1 end
  local ok, v = pcall(C.region_ore, x, z)
  if not ok then link_fail(v); return 1 end
  return tonumber(v) or 1
end
-- труд копится по узлу и уходит в мир порциями (раз в feed_every_hours игровых часов, при смене мира и сохранении)
flush_feed = function(force)
  local C = conductor()
  local day = game_day()
  if not force and RT.feed_day and day and (day - RT.feed_day) * 24 < cfg.feed_every_hours then return end
  RT.feed_day = day
  if not next(RT.feed) then return end
  local batch = RT.feed
  RT.feed = {}
  if not cfg.feed_conductor or DISABLED.conductor_link or not (C and C.player_mined) then return end
  for _, e in pairs(batch) do
    local ok, err = pcall(C.player_mined, e.a, e.x, e.z)
    if not ok then link_fail(err); return end
    RT.stats.fed = RT.stats.fed + e.a
  end
end
local function feed_world(key, amount, x, z)
  local e = RT.feed[key]
  if not e then e = { a = 0, x = x, z = z }; RT.feed[key] = e end
  e.a = e.a + amount
end

---------------------------------------------------------------------------------------------- модель узла
local function region_factor(key, s, day)
  if not cfg.region_live then return 1 end
  local v = view(key)
  if v.reg and v.reg_day and (day - v.reg_day) * 24 < cfg.region_refresh_hours then return v.reg end
  if not v.x then return v.reg or 1 end
  local share = math.max(0, math.min(1, region_share(v.x, v.z)))
  v.reg, v.reg_day = math.max(cfg.region_floor, share ^ cfg.region_k), day
  return v.reg
end
local function coefficient(s, reg)
  local c = cfg.classes[s.cls]
  return math.max(c.floor, (math.max(0, s.R) / s.R0) ^ c.k) * (reg or 1)
end
local function regen(s, day)
  local c = cfg.classes[s.cls]
  if s.last_day and s.last_day >= 0 and c.regen_per_day > 0 and day > s.last_day then
    s.R = math.min(s.R0, s.R + (day - s.last_day) * c.regen_per_day)
  end
  if s.last_day and s.last_day >= 0 and day > s.last_day then
    s.recent = (s.recent or 0) * math.exp(-(day - s.last_day) / cfg.recent_days)
  end
  s.last_day = day
end
local function apply_level(pb, s, reg)
  if not cfg.write_level or not s.base or s.base <= 0 then return nil end
  local target = s.base * coefficient(s, reg)
  local cur = pb._resourceMiningLevel
  if type(cur) ~= "number" or math.abs(cur - target) > 1e-4 then
    pb._resourceMiningLevel = target
    RT.stats.writes = RT.stats.writes + 1
  end
  return target
end
-- Остаток залежи в названии узла (по итогам плейтеста 2026-11-13): «Iron [ore left 73%]», при выработанной жиле региона —
-- «Iron [ore left 73% vein 40%]». Меняем только при сдвиге на >= 1 %; ошибка API (нет getName/setName) отключает только показ.
local function show_left(b, key, s, reg)
  if cfg.show_left == false or DISABLED.show_left then return end
  local v = view(key)
  local pct = math.floor(math.max(0, s.R) / s.R0 * 100 + 0.5)
  local vp = (reg and reg < 0.95) and math.floor(reg * 100 + 0.5) or nil
  local tag = pct * 1000 + (vp or 999)
  if v.shown == tag then return end
  local ok, err = pcall(function()
    local nm = b:getName()
    if type(nm) ~= "string" then return end
    local base = string.gsub(nm, " %[[^%]]*%]$", "")
    local extra = vp and string.format(" %s %d%%", cfg.vein_label or "vein", vp) or ""
    b:setName(string.format("%s [%s %d%%%s]", base, cfg.left_label or "ore left", pct, extra))
  end)
  if ok then v.shown = tag else DISABLED.show_left = true; dlog("show_left disabled until restart: " .. tostring(err)) end
end
local function node_of(pb, tpl, t, x, z, day)
  local key = string.format("%s@%d,%d", tpl, math.floor(x + 0.5), math.floor(z + 0.5))
  local v = view(key)
  v.x, v.z = x, z
  local s = RT.nodes[key]
  if s then return s, key end
  local lv = pb._resourceMiningLevel                         -- поле, не метод: без пересчёта движком
  local base = (type(lv) == "number" and lv > 0) and lv or -1
  local R0 = cfg.classes[t.cls].R0
  if cfg.region_scale_r0 and t.cls == "surface" then R0 = R0 * math.max(cfg.region_min or 0.15, math.min(1, region_share(x, z))) end
  s = { cls = t.cls, tpl = tpl, res = t.res, R = R0, R0 = R0, base = base, last_day = day, hours = 0, recent = 0 }
  RT.nodes[key] = s
  RT.dirty = true
  RT.stats.nodes_new = RT.stats.nodes_new + 1
  olog(string.format("NEW node %s class=%s res=%s auto=%s base_level=%s R0=%.0f", key, t.cls, tostring(t.res), tostring(t.auto), tostring(base), R0))
  return s, key
end

-- труд на узле: hours списываются с R (source = "char" | "auto"), уровень и подпись обновляются
local function work(b, pb, tpl, t, x, z, hours, day, source)
  local s, key = node_of(pb, tpl, t, x, z, day)
  regen(s, day)
  local v = view(key)
  if hours > 0 then
    s.R = s.R - hours
    s.hours = (s.hours or 0) + hours
    s.recent = (s.recent or 0) + hours
    RT.dirty = true
    if source == "auto" then RT.stats.auto_hours = RT.stats.auto_hours + hours else RT.stats.work_hours = RT.stats.work_hours + hours end
    feed_world(key, hours * cfg.player_to_world, x, z)
  end
  if source == "char" then v.char_day = day end
  local reg = region_factor(key, s, day)
  local after = apply_level(pb, s, reg)
  show_left(b, key, s, reg)
  if (day - (v.logged_day or -1e9)) * 24 >= cfg.log_every_hours then
    v.logged_day = day
    olog(string.format("%s %s R=%.1f/%.0f coef=%.3f vein=%.2f level=%s worked=%.1fh", source == "auto" and "AUTO" or "MINE", key, s.R, s.R0,
      coefficient(s, reg), reg, after and string.format("%.3f", after) or "-", s.hours))
    if s.R <= 0 and s.cls == "surface" then olog("DEPLETED " .. key) end
  end
  return s, key
end

---------------------------------------------------------------------------------------------- опрос персонажа
local function xz(v) if v then return v.x or v[1], v.z or v[3] end end
local function char_key(ch)
  local ok, k = pcall(function() return ch:getHandle():toString() end)
  if ok and type(k) == "string" and k ~= "" then return k end
  return nil
end
local function chain_note(stage, k)
  RT.chain[stage] = (RT.chain[stage] or 0) + 1
  if k ~= nil and count(RT.chain_keys) < 12 then RT.chain_keys[k] = (RT.chain_keys[k] or 0) + 1
  elseif k ~= nil and RT.chain_keys[k] then RT.chain_keys[k] = RT.chain_keys[k] + 1 end
end
-- цель действия: здание по subject, иначе по currentSubTarget (Tasker, BindingsReference)
local function target_building(act)
  for _, f in ipairs(cfg.subject_fields) do
    local h = act[f]
    if h and h:isValid() then
      local b = h:getBuilding()
      if b then return b, f end
    end
  end
  return nil
end
-- рудный узел, на котором персонаж сейчас работает: w | nil, стадия обрыва. Ошибки API не глотаются — их ловит guard тика.
local function work_of(ch)
  if type(ch.getBody) ~= "function" then return nil, "no_body" end   -- не персонаж с телом (у Character getBody есть: BindingsReference)
  local body = ch:getBody()
  if not body then return nil, "no_body" end
  local act = body:getCurrentAction()
  if not act then return nil, "idle" end
  local k = act:key()
  local counted = type(k) ~= "number" or ((TASKS[k] or LEARNED[k]) and not PRETEND[k])
  if not counted then   -- чужая задача проверяется до diag_task_checks раз за сессию — не стоит ли персонаж с ней у рудного узла
    local n = RT.diag_task[k] or 0
    if n >= cfg.diag_task_checks then return nil, "task_other", k end
    RT.diag_task[k] = n + 1
  end
  local b = target_building(act)
  if not b then return nil, counted and "no_target" or "task_other", k end
  local pb = b:getProductionBuilding()
  if not pb then return nil, counted and "not_production" or "task_other", k end
  local gd = b:getGameData()
  local tpl, t = classify(gd)
  if not t then
    if counted and tpl and not RT.diag_tpl[tpl] then
      RT.diag_tpl[tpl] = true
      olog(string.format("SKIP template %s (%s) task=%s: production node not in ore_templates", tpl, tostring(gd and gd.name), tostring(k)))
    end
    return nil, counted and "not_ore" or "task_other", k
  end
  local bx, bz = xz(b:getPosition())
  local cx, cz = xz(ch:getPosition())
  if not (bx and cx) then return nil, "no_pos", k end
  if (bx - cx) ^ 2 + (bz - cz) ^ 2 > cfg.work_radius ^ 2 then return nil, "far", k end
  if not counted then
    RT.diag_task[k] = cfg.diag_task_checks
    olog(string.format("SKIP task=%s at ore node %s: TaskType not counted (pretend/haul?)", tostring(k), tpl))
    return nil, "task_other", k
  end
  return { b = b, pb = pb, tpl = tpl, t = t, x = bx, z = bz }, "ok", k
end

local function step(pcs, day)
  local n = #pcs
  for _ = 1, math.min(n, cfg.chars_per_poll) do
    RT.rr = RT.rr % n + 1
    local ch = pcs[RT.rr]
    local ck = char_key(ch) or ("#" .. RT.rr)
    local last = RT.char_day[ck]
    RT.char_day[ck] = day
    local w, stage, k = work_of(ch)
    chain_note(stage, k)
    if w then
      local hours = (last and day > last) and math.min(cfg.max_dt_hours, (day - last) * 24) or 0
      work(w.b, w.pb, w.tpl, w.t, w.x, w.z, hours, day, "char")
    end
  end
end

-- раз в diag_every_hours: где обрывается цепочка «персонаж → действие → здание → рудный узел» (маркер CHAIN для session_report)
local function chain_report(day)
  if not RT.chain_day then RT.chain_day = day; return end
  if (day - RT.chain_day) * 24 < cfg.diag_every_hours then return end
  RT.chain_day = day
  if not next(RT.chain) then return end
  local order = { "ok", "far", "not_ore", "not_production", "no_target", "task_other", "idle", "no_body", "no_pos" }
  local parts = {}
  for _, st in ipairs(order) do if RT.chain[st] then parts[#parts + 1] = st .. "=" .. RT.chain[st] end end
  local ks = {}
  for kk, c in pairs(RT.chain_keys) do ks[#ks + 1] = { tostring(kk), c } end
  table.sort(ks, function(a, b) if a[2] ~= b[2] then return a[2] > b[2] end; return a[1] < b[1] end)
  local kt = {}
  for i = 1, math.min(6, #ks) do kt[#kt + 1] = ks[i][1] .. ":" .. ks[i][2] end
  local lt = {}
  for kk in pairs(LEARNED) do lt[#lt + 1] = tostring(kk) end
  table.sort(lt)
  olog(string.format("CHAIN %s tasks=%s learned=%s nodes=%d machines_seen=%d", table.concat(parts, " "), table.concat(kt, ","),
    #lt > 0 and table.concat(lt, ",") or "-", count(RT.nodes), RT.stats.machines or 0))
  RT.chain, RT.chain_keys = {}, {}
end

---------------------------------------------------------------------------------------------- приказы игрока (LEARN)
local function on_order(_, task_type, target)
  if not (cfg and RT.ready) or DISABLED.order then return end
  if not (target and target:isValid()) then return end
  local b = target:getBuilding()
  if not b then return end
  local pb = b:getProductionBuilding()
  if not pb then return end
  local tpl, t = classify(b:getGameData())
  if not t then return end
  RT.stats.orders = RT.stats.orders + 1
  local tk = tonumber(task_type)
  if tk and not TASKS[tk] and not PRETEND[tk] and not LEARNED[tk] and count(LEARNED) < cfg.learn_max then
    LEARNED[tk] = true
    olog(string.format("LEARN task=%d from player order at ore node %s (class=%s res=%s)", tk, tpl, t.cls, tostring(t.res)))
  end
  local ok_key = tostring(tk) .. "|" .. tpl
  if not RT.order_seen[ok_key] then
    RT.order_seen[ok_key] = true
    olog(string.format("ORDER task=%s node=%s class=%s res=%s counted=%s", tostring(task_type), tpl, t.cls, tostring(t.res),
      tostring(tk ~= nil and (TASKS[tk] or LEARNED[tk]) == true)))
  end
end
local function hook_orders()
  if RT.hooked ~= nil or not cfg.learn_orders then return end
  RT.hooked = false
  local ev = rawget(_G, "Events")
  local ok, e = pcall(function()
    if ev and ev.on then
      KMM_Ore._order_handler = ev.on("PlayerInterface::newPlayerTaskSelectedCharacters", guarded("order", on_order))
      RT.hooked = true
    end
  end)
  olog(ok and RT.hooked and "order hook ok" or ("order hook unavailable (" .. tostring(e) .. "): task types from ore_config only"))
end

---------------------------------------------------------------------------------------------- скан машин игрока (автобуры)
local function is_player_building(b, pf)
  if b:isThePlayer() then return true end
  if not pf then return false end
  local ok, sid = pcall(function() local f = b:getFaction(); local g = f and f.data; return g and g.stringID end)
  return ok and sid == pf
end
local function player_faction()
  local C = conductor()
  if not (C and C.cfg) then return nil end
  local ok, v = pcall(C.cfg)
  return ok and type(v) == "table" and v.player_faction or nil
end
local function raw_building(o) return o:getHandle():getBuilding() end
local function scan(pcs, day)
  if not cfg.scan_enabled then return end
  local t = os.clock()
  if t - RT.t_scan < cfg.scan_seconds then return end
  RT.t_scan = t
  local gw = rawget(_G, "getGameWorld") and getGameWorld()
  local lk = rawget(_G, "lektor")
  if not (gw and lk and lk.new) then DISABLED.scan = true; olog("scan unavailable: no lektor/getObjectsWithinSphere, automatic drills not counted"); return end
  if not RT.buf then RT.buf = lk.new("RootObject*") end   -- один буфер на сессию (ContainersReference)
  RT.scan_rr = RT.scan_rr % #pcs + 1
  local pc = pcs[RT.scan_rr]
  RT.buf:clear()
  -- буфер первым аргументом — та же форма, что в KMM_Stock и ContainersReference «Spatial Queries» (в игре работает у KMM_Stock)
  getGameWorld():getObjectsWithinSphere(RT.buf, pc:getPosition(), cfg.scan_radius, 0, cfg.scan_max_objects, nil)   -- 0 = itemType.BUILDING
  RT.stats.scans = RT.stats.scans + 1
  local pf, seen = player_faction(), 0
  for _, o in ipairs(RT.buf) do
    local okb, b = pcall(raw_building, o)
    local pb = okb and b and b:getProductionBuilding()
    if pb then
      local tpl, tt = classify(b:getGameData())
      if tt then
        local bx, bz = xz(b:getPosition())
        if bx then
          local key = string.format("%s@%d,%d", tpl, math.floor(bx + 0.5), math.floor(bz + 0.5))
          local s = RT.nodes[key]
          local mine_owned = tt.auto and is_player_building(b, pf)
          if mine_owned then
            seen = seen + 1
            local v = view(key)
            local hours = 0
            local running = b:isPowerOn() and not b:isBroken() and pb.productionState == 2   -- ProductionState NORMAL
            if v.mach_day and day > v.mach_day and running and not (v.char_day and v.char_day >= v.mach_day) then
              hours = math.min(cfg.auto_max_hours, (day - v.mach_day) * 24) * cfg.auto_rate
            end
            v.mach_day = day
            work(b, pb, tpl, tt, bx, bz, hours, day, "auto")
          elseif s then   -- известный узел: уровень заново после подгрузки зоны (движок мог пересчитать поле)
            view(key).x, view(key).z = bx, bz
            regen(s, day)
            local reg = region_factor(key, s, day)
            apply_level(pb, s, reg)
            show_left(b, key, s, reg)
          end
        end
      end
    end
  end
  RT.stats.machines = seen
end
local g_scan = guarded("scan", scan)

-- сводка рудного хозяйства игрока в состоянии дирижёра: S.base.ore (только если база уже известна; читатели — см. economy_player.md)
local function summary(day)
  if cfg.summary_to_conductor == false or not RT.S or type(RT.S.base) ~= "table" then return end
  local active, recent, bx, bz, best = 0, 0, nil, nil, -1
  for key, s in pairs(RT.nodes) do
    local r = (s.recent or 0) * math.exp(-math.max(0, day - (s.last_day or day)) / cfg.recent_days)
    if r > 0.5 then
      active = active + 1
      recent = recent + r
      if r > best then
        best = r
        local x, z = key:match("@(%-?%d+),(%-?%d+)$")
        bx, bz = tonumber(x), tonumber(z)
      end
    end
  end
  RT.S.base.ore = { active = active, recent = math.floor(recent * 10 + 0.5) / 10, auto = RT.stats.machines or 0, x = bx, z = bz, day = math.floor(day * 100) / 100 }
end
local g_summary = guarded("summary", summary)

---------------------------------------------------------------------------------------------- тик
local function reset_ready()
  RT.ready, RT.polls, RT.seen_clock, RT.seen_day = false, 0, nil, nil
  RT.char_day = {}
end

local function player_chars()
  local ok, list = pcall(function()
    local gpi = rawget(_G, "getPlayerInterface")
    local pi = gpi and gpi()
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
  hook_orders()
  RT.stats.polls = RT.stats.polls + 1
  step(pcs, day)
  if not DISABLED.scan then g_scan(pcs, day) end
  flush_feed(false)
  chain_report(day)
  if RT.dirty and t - RT.t_save >= cfg.save_every_seconds then g_save(); g_summary(day) end
end
local g_tick = guarded("tick", tick)

---------------------------------------------------------------------------------------------- регистрация: только общий тик
KMM_Ore = KMM_Ore or {}
KMM_Ore.version = VERSION
KMM_Ore.tick = function() g_tick(true) end            -- для вызова из тика дирижёра (cfg.tick_source = "conductor")
KMM_Ore.disabled = function() return DISABLED end
KMM_Ore.stats = function() return RT.stats end
KMM_Ore.nodes = function() return RT.nodes end
KMM_Ore.learned = function() return LEARNED end
KMM_Ore.status = function()
  local d = {}
  for k in pairs(DISABLED) do d[#d + 1] = k end
  table.sort(d)
  return string.format("%s enabled=%s ready=%s world=%s src=%s nodes=%d polls=%d work=%.1fh auto=%.1fh writes=%d orders=%d disabled=%s", VERSION,
    tostring(cfg and cfg.ore_enabled), tostring(RT.ready), tostring(RT.world), tostring(RT.src), count(RT.nodes),
    RT.stats.polls, RT.stats.work_hours, RT.stats.auto_hours, RT.stats.writes, RT.stats.orders, table.concat(d, ","))
end
KMM_Ore.save = function() if RT.world then pcall(flush_feed, true); if RT.dirty then g_save() end end end
KMM_Ore._rt = RT

local EV = rawget(_G, "Events")
if KMM_Ore._handler and EV and EV.off then pcall(EV.off, KMM_Ore._handler) end   -- перезагрузка скрипта не дублирует
if KMM_Ore._order_handler and EV and EV.off then pcall(EV.off, KMM_Ore._order_handler); KMM_Ore._order_handler = nil end
if EV and EV.on then
  KMM_Ore._handler = EV.on("GameWorld::charsUpdate", guarded("tick_hook", function()
    local gov = rawget(_G, "KMM_Gov")
    if gov then return gov.run("ore", g_tick, false) else return g_tick(false) end
  end))
end
