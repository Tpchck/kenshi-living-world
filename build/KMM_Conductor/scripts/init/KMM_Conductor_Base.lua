-- KMM_Conductor_Base: part of KMM_Conductor (world conductor), run by KC._BOOT in KMM_Conductor.lua
-- Часть дирижёра мира (KMM_Conductor.lua собирает части и регистрирует события). 1-я строка ASCII: имя чанка в тестах.
-- Здесь: утилиты, JSON и сериализация, файлы и конфиг, состояние мира, хроника и шина событий (emit/subscribe/bus),
-- договоры и обязательства, экономика и режимы реликтовых, индекс пар «город — лидер».
-- Код части выполняется не при загрузке файла, а в KC._BOOT() в порядке KC._PARTS (как шёл бы единый файл),
-- когда загружены все части — порядок загрузки файлов KenshiLua не важен.
local KC = rawget(_G, "KMM_C_INT")   -- общее пространство имён частей дирижёра (бывшие локали главного чанка: KC.<имя>)
if type(KC) ~= "table" then KC = { _SEG = {} }; _G.KMM_C_INT = KC end
if KC._booted then KC._SEG, KC._booted = {}, false end   -- повторная загрузка скриптов: собрать части заново
KC._SEG.Base = function()
KC.TAG = "[KMM_Conductor] "
KC.STATE_KEY = "kmm_conductor_state"
KC.VERSION = 4
KC.MAX_EVENTS = 300

function KC.log(msg)
  msg = KC.TAG .. tostring(msg)
  if not (KenshiLua and pcall(function() KenshiLua.log(msg) end)) then print(msg) end
end

---------------------------------------------------------------------------------------------- JSON (минимальный)
KC.json = {}
do
  local function skip(s, i) return s:find("[^ \t\r\n]", i) or #s + 1 end
  local esc = { ['"'] = '"', ["\\"] = "\\", ["/"] = "/", b = "\b", f = "\f", n = "\n", r = "\r", t = "\t" }
  local parse
  local function parse_string(s, i)
    local out, j = {}, i + 1
    while true do
      local c = s:sub(j, j)
      if c == "" then error("unterminated string") end
      if c == '"' then return table.concat(out), j + 1 end
      if c == "\\" then
        local e = s:sub(j + 1, j + 1)
        if e == "u" then
          local code = tonumber(s:sub(j + 2, j + 5), 16)
          if code < 0x80 then out[#out + 1] = string.char(code)
          elseif code < 0x800 then out[#out + 1] = string.char(0xC0 + math.floor(code / 64), 0x80 + code % 64)
          else out[#out + 1] = string.char(0xE0 + math.floor(code / 4096), 0x80 + math.floor(code / 64) % 64, 0x80 + code % 64) end
          j = j + 6
        else out[#out + 1] = esc[e] or e; j = j + 2 end
      else out[#out + 1] = c; j = j + 1 end
    end
  end
  parse = function(s, i)
    i = skip(s, i)
    local c = s:sub(i, i)
    if c == "{" then
      local t = {}
      i = skip(s, i + 1)
      if s:sub(i, i) == "}" then return t, i + 1 end
      while true do
        local k
        k, i = parse_string(s, skip(s, i))
        i = skip(s, i)
        if s:sub(i, i) ~= ":" then error("':' expected at " .. i) end
        t[k], i = parse(s, i + 1)
        i = skip(s, i)
        local d = s:sub(i, i)
        if d == "}" then return t, i + 1 end
        if d ~= "," then error("',' expected at " .. i) end
        i = i + 1
      end
    elseif c == "[" then
      local t = {}
      i = skip(s, i + 1)
      if s:sub(i, i) == "]" then return t, i + 1 end
      while true do
        t[#t + 1], i = parse(s, i)
        i = skip(s, i)
        local d = s:sub(i, i)
        if d == "]" then return t, i + 1 end
        if d ~= "," then error("',' expected at " .. i) end
        i = i + 1
      end
    elseif c == '"' then return parse_string(s, i)
    elseif s:sub(i, i + 3) == "true" then return true, i + 4
    elseif s:sub(i, i + 4) == "false" then return false, i + 5
    elseif s:sub(i, i + 3) == "null" then return nil, i + 4
    else
      local num = s:match("^-?%d+%.?%d*[eE]?[-+]?%d*", i)
      if not num or num == "" then error("bad json at " .. i) end
      return tonumber(num), i + #num
    end
  end
  function KC.json.decode(s) local v = parse(s, 1); return v end
end

---------------------------------------------------------------------------------------------- сериализация
function KC.ser(v, out)
  local t = type(v)
  if t == "table" then
    out[#out + 1] = "{"
    for k, x in pairs(v) do out[#out + 1] = "["; KC.ser(k, out); out[#out + 1] = "]="; KC.ser(x, out); out[#out + 1] = "," end
    out[#out + 1] = "}"
  elseif t == "string" then out[#out + 1] = string.format("%q", v)
  elseif t == "number" then out[#out + 1] = (v ~= v or v == math.huge or v == -math.huge) and "0" or string.format("%.6g", v)   -- без inf/nan
  elseif t == "boolean" then out[#out + 1] = tostring(v)
  else out[#out + 1] = "nil" end
end
function KC.serialize(v) local out = {}; KC.ser(v, out); return table.concat(out) end
function KC.deserialize(s)
  if type(s) ~= "string" or s == "" then return nil end
  -- PARSER (2026-11-13): в игре загрузка дала «none (index)» — строка из сейва прочитана, но loadstring её не превратил в таблицу
  -- (в KenshiLua loadstring, по-видимому, ограничен; офлайн та же строка грузится). Свой разбор формата ser() без loadstring.
  local pos, n = 1, #s
  local val
  local function num_at(i)
    local tok = s:match("^[%-%+%.%w#%(%)]+", i)
    if not tok then error("number at " .. i) end
    local v = tonumber(tok)
    if v == nil then v = (tok:find("INF") or tok:find("inf")) and (tok:sub(1, 1) == "-" and -math.huge or math.huge) or 0 end
    return v, i + #tok
  end
  local function str_at(i)   -- формат %q Lua 5.1: обратная косая + (косая, кавычка, перевод строки, r, ddd)
    local buf, j = {}, i + 1
    while true do
      local k = s:find('[\\"]', j)
      if not k then error("unterminated string at " .. i) end
      buf[#buf + 1] = s:sub(j, k - 1)
      if s:sub(k, k) == '"' then return table.concat(buf), k + 1 end
      local c = s:sub(k + 1, k + 1)
      if c == "\n" then buf[#buf + 1] = "\n"; j = k + 2
      elseif c == "r" then buf[#buf + 1] = "\r"; j = k + 2
      elseif c == "n" then buf[#buf + 1] = "\n"; j = k + 2
      elseif c:match("%d") then local d = s:match("^%d%d?%d?", k + 1); buf[#buf + 1] = string.char(tonumber(d)); j = k + 1 + #d
      else buf[#buf + 1] = c; j = k + 2 end
    end
  end
  val = function(i)
    local c = s:sub(i, i)
    if c == "{" then
      local t = {}
      i = i + 1
      while s:sub(i, i) == "[" do
        local k, v
        k, i = val(i + 1)
        if s:sub(i, i + 1) ~= "]=" then error("']=' expected at " .. i) end
        v, i = val(i + 2)
        if k ~= nil then t[k] = v end
        if s:sub(i, i) == "," then i = i + 1 end
      end
      if s:sub(i, i) ~= "}" then error("'}' expected at " .. i) end
      return t, i + 1
    elseif c == '"' then return str_at(i)
    elseif s:sub(i, i + 3) == "true" then return true, i + 4
    elseif s:sub(i, i + 4) == "false" then return false, i + 5
    elseif s:sub(i, i + 2) == "nil" then return nil, i + 3
    else return num_at(i) end
  end
  local okp, v = pcall(function() local r = val(pos); return r end)
  if okp and type(v) == "table" then return v end
  local perr = v
  local LS = rawget(_G, "loadstring") or rawget(_G, "load")
  local f, lerr = nil, "absent"
  if LS then local okc, f1, e1 = pcall(LS, "return " .. s, "@kmm_conductor_state"); if okc then f, lerr = f1, e1 else lerr = f1 end end
  if f then
    pcall(setfenv, f, {})
    local ok, lv = pcall(f)
    if ok and type(lv) == "table" then return lv end
  end
  KC.log(string.format("deserialize failed: len=%d head=%q parser=%s loadstring=%s", n, s:sub(1, 40), tostring(perr), tostring(lerr)))
  return nil
end

---------------------------------------------------------------------------------------------- файлы и конфиг
function KC.mod_root()
  local ok, chunk, msg = pcall(loadfile, "__kmm_conductor_probe__.lua")
  if not ok or chunk then return nil end
  local dir = tostring(msg):match("no file under%s+(.+)$")
  if not dir then return nil end
  dir = dir:gsub("\\", "/"):gsub("%s+$", ""):gsub("/+$", "")
  local root = dir:gsub("/scripts$", "")
  if root == dir then return nil end
  return root
end
function KC.read_file(path)
  local ok, f = pcall(io.open, path, "r")
  if not (ok and f) then return nil end
  local s = f:read("*a"); f:close(); return s
end
function KC.append_file(path, line)
  local ok, f = pcall(io.open, path, "a")
  if not (ok and f) then return false end
  f:write(line, "\n"); f:close(); return true
end

KC.CFG, KC.P, KC.ROOT, KC.TIERS = nil
function KC.load_json(fname, fallback)
  local cands = {}
  if KC.ROOT then cands[#cands + 1] = KC.ROOT .. "/" .. fname end
  cands[#cands + 1] = fallback
  for _, p in ipairs(cands) do
    local s = KC.read_file(p)
    if s then
      local ok, v = pcall(KC.json.decode, s)
      if ok and type(v) == "table" then return v, p end
      KC.log(p .. " unreadable: " .. tostring(v))
    end
  end
  return nil
end

---------------------------------------------------------------------------------------------- состояние
KC.S = nil
function KC.count(t) local n = 0; for _ in pairs(t) do n = n + 1 end; return n end
function KC.clamp(x, a, b) if x < a then return a elseif x > b then return b end return x end
function KC.game_day()
  local ok, d = pcall(function() return getGameWorld():getTimeStamp_inGameHours():getTotalDays() end)
  if ok and type(d) == "number" then return d end
  return nil
end

KC.seed_world = nil   -- семя мира (определяется в блоке «мир v2»)
function KC.fresh_state()
  local s = { version = KC.VERSION, last_day = -1, next_tick = nil, next_event = nil, next_id = 1, events = {}, pending = {}, resolved = {},
              F = {}, rel = {}, treaties = {}, next_tid = 1, dirty_rel = {}, free = {},
              stats = { signed = 0, signed_by = {}, broken = {}, mobilized = 0, captures = 0, raids = 0, fell = 0, betrayals = 0,
                        dispatch = 0, gear = 0, help = 0, failed_help = 0 },
              dispatch_day = -1, dispatch_today = 0,
              stock = {}, town = {}, loot = {} }   -- слоты KMM_Stock (склады городов) и KMM_Town (город за работой); пишут они сами
  for fid, f in pairs(KC.CFG.factions) do
    local towns = {}
    for _, t in ipairs(f.towns or {}) do towns[t] = true end
    s.F[fid] = { wealth = f.wealth, wealth0 = math.max(1, f.wealth), strength = f.strength, strength0 = f.strength, towns = towns,
                 towns0 = #(f.towns or {}), ambition = f.ambition, relic = f.relic, mode = f.relic and "focused" or nil, alive = true,
                 trigger_day = -1000, mode_since = 0, opp = {}, trust = {}, player = f.player, townless = f.townless, arch = f.arch }
    if f.sleeper then s.F[fid].alive = false; s.F[fid].sleeper = true end   -- спящий осколок: ждёт раскола/варлорда
    s.rel[fid] = {}
    for b, v in pairs(f.rel or {}) do s.rel[fid][b] = v end
  end
  if KC.seed_world then KC.seed_world(s) end
  if KC.CFG.vassals then   -- VASSALS: стартовые вассалы и региональные союзы по лору (rules/vassals.json); без всплеска отношений и событий
    for _, x in ipairs(KC.CFG.vassals.seed or {}) do
      local A, B = s.F[x.a], s.F[x.b]
      if A and B and A.alive and B.alive then
        local id = s.next_tid; s.next_tid = id + 1
        s.treaties[id] = { id = id, type = x.t, a = x.a, b = x.b, since = 0, term = 100000, active = true, why = x.why, seed = true }
        local fl = ({ vassal = 40, military = 40, defense = 30, nonaggression = 10, trade = 10 })[x.t] or 10   -- давняя присяга/союз: отношения и доверие
        for _, pr in ipairs({ { x.a, x.b }, { x.b, x.a } }) do
          s.rel[pr[1]] = s.rel[pr[1]] or {}
          s.rel[pr[1]][pr[2]] = math.max(s.rel[pr[1]][pr[2]] or 0, fl)
          s.F[pr[1]].trust[pr[2]] = math.max(s.F[pr[1]].trust[pr[2]] or 0, 40)
        end
        s.stats.seeded = (s.stats.seeded or 0) + 1
      end
    end
  end
  return s
end

function KC.name(fid) local f = KC.CFG.factions[fid]; return f and f.name or tostring(fid) end
function KC.rel(a, b) return (KC.S.rel[a] and KC.S.rel[a][b]) or 0 end
function KC.set_rel(a, b, v)
  v = KC.clamp(math.floor(v + 0.5), -100, 100)
  if not KC.S.rel[a] then KC.S.rel[a] = {} end
  if not KC.S.rel[b] then KC.S.rel[b] = {} end
  if KC.S.rel[a][b] ~= v or KC.S.rel[b][a] ~= v then
    KC.S.rel[a][b], KC.S.rel[b][a] = v, v
    KC.S.dirty_rel[a .. "|" .. b] = true
  end
end
function KC.add_rel(a, b, dv) KC.set_rel(a, b, KC.rel(a, b) + dv) end
function KC.trust(a, b) return (KC.S.F[a].trust[b] or 0) end
function KC.add_trust(a, b, dv)
  KC.S.F[a].trust[b] = KC.clamp((KC.S.F[a].trust[b] or 0) + dv, -100, 100)
  KC.S.F[b].trust[a] = KC.clamp((KC.S.F[b].trust[a] or 0) + dv, -100, 100)
end
function KC.ntowns(f) return KC.count(f.towns) end
-- город и владение (фермы/аванпосты/лагеря/башни): TownType из данных (gen_conductor.py -> town_info)
function KC.is_city(t) local i = KC.CFG.town_info and KC.CFG.town_info[t]; return i and i.kind == "city" end
function KC.ncities(f) local n = 0; for t in pairs(f.towns) do if KC.is_city(t) then n = n + 1 end end; return n end
function KC.town_dist(a, b)
  local A, B = KC.CFG.town_info and KC.CFG.town_info[a], KC.CFG.town_info and KC.CFG.town_info[b]
  if not (A and B and A.x and B.x) then return 0 end
  return math.sqrt((A.x - B.x) ^ 2 + (A.z - B.z) ^ 2)
end
function KC.capital(fid)
  local f = KC.S.F[fid]
  local c = KC.CFG.factions[fid] and KC.CFG.factions[fid].capital
  if c and f.towns[c] then return c end
  for t in pairs(f.towns) do if KC.is_city(t) then return t end end   -- столица потеряна: новая — любой оставшийся город
  return nil
end
function KC.power(fid)
  local f = KC.S.F[fid]
  if not f or not f.alive then return 0 end
  local mo = 1
  if f.morale and f.morale < 1 then mo = 1 - (((KC.P.links2 or {}).self or {}).morale_pen or 0.15) * (1 - f.morale) end   -- LINKS2: поражения отрядов (Self) слегка гасят боевой дух
  return f.strength * ((f.mode == "mobilized") and KC.P.relic.mobilized_strength_mult or 1) * mo
end
function KC.near(a, r)
  local out = {}
  local src = KC.CFG.factions[a] and KC.CFG.factions[a].near
  if (not src or #src == 0) and KC.S.F[a] and KC.S.F[a].proxy and KC.CFG.factions[KC.S.F[a].proxy] then src = KC.CFG.factions[KC.S.F[a].proxy].near end
  for _, e in ipairs(src or {}) do
    if e[2] <= r and KC.S.F[e[1]] and KC.S.F[e[1]].alive then out[#out + 1] = e[1] end
  end
  return out
end

---------------------------------------------------------------------------------------------- хроника и шина событий
KC.DAY = 0
KC.GL = {}   -- GOALS (цели фракций, роль оплотов): блок перед world_step
-- HEALTH (2026-11-15): отказы функций дирижёра идут в реестр KMM_Gov (ключ KMM_Conductor.<имя>): пауза 1/5/30 мин и повтор вместо
-- «до перезапуска». Флаг t[f] = true остаётся (его читают все, кто проверял его раньше); ключ паузы — в боковой таблице HPK (поля в t
-- не плодим: таблицы флагов перечисляют как «что выключено»). Точка входа зовёт h_live: пауза истекла -> флаг снят (nil), одна попытка;
-- h_done после успешной попытки сообщает реестру ok. Нет Gov — прежнее «до перезапуска».
KC.GL.HPK = setmetatable({}, { __mode = "k" })   -- [таблица флагов] = { [флаг] = ключ реестра }
KC.GL.HTR = setmetatable({}, { __mode = "k" })   -- [таблица флагов] = { [флаг] = ключ } — идёт попытка после паузы
function KC.GL.h_gov() local g = rawget(_G, "KMM_Gov"); if type(g) == "table" and type(g.h_fail) == "function" then return g end end
function KC.GL.h_up(key) local g = KC.GL.h_gov(); if not g then return true end; local ok, r = pcall(g.h_up, key); return (not ok) or r ~= false end
function KC.GL.h_ok(key) local g = KC.GL.h_gov(); if g then pcall(g.h_ok, key) end end
function KC.GL.h_fail(key, err) local g = KC.GL.h_gov(); if not g then return nil end; local ok, r = pcall(g.h_fail, key, err); if ok then return r end end
function KC.GL.h_off(key, why, kind) local g = KC.GL.h_gov(); if g and type(g.h_off) == "function" then pcall(g.h_off, key, why, kind) end end
function KC.GL.hside(T, t) local m = T[t]; if not m then m = {}; T[t] = m end; return m end
-- отказ: t[f] = true; пауза в реестре -> вернёт секунды паузы; иначе nil (до перезапуска)
function KC.GL.h_down(t, f, key, err)
  t[f] = true
  KC.GL.hside(KC.GL.HTR, t)[f] = nil
  local p = KC.GL.h_fail(key, err)
  KC.GL.hside(KC.GL.HPK, t)[f] = (type(p) == "number") and key or nil
  return (type(p) == "number") and p or nil
end
-- навсегда (нет API / крэш-сторож / вердикт): флаг без ключа паузы
function KC.GL.h_forever(t, f, key, why, kind)
  t[f] = true
  KC.GL.hside(KC.GL.HPK, t)[f] = nil; KC.GL.hside(KC.GL.HTR, t)[f] = nil
  KC.GL.h_off(key, why, kind)
end
-- точка входа: true = сейчас выключено; пауза истекла -> флаг снят, попытка
function KC.GL.h_live(t, f)
  if not t[f] then return false end
  local m = KC.GL.HPK[t]
  local key = m and m[f]
  if key and KC.GL.h_up(key) then t[f] = nil; m[f] = nil; KC.GL.hside(KC.GL.HTR, t)[f] = key; return false end
  return true
end
-- попытка после паузы прошла: ok в реестр (дёшево, если паузы не было)
function KC.GL.h_done(t, f)
  local m = KC.GL.HTR[t]
  local key = m and m[f]
  if key then m[f] = nil; KC.GL.h_ok(key) end
end
-- отказ с записью в лог: what — имя для строки; logf — функция лога
function KC.GL.h_bad(t, f, key, err, what, logf)
  local p = KC.GL.h_down(t, f, key, err)
  local msg = what .. (p and (" failed, retry in " .. p .. " s: ") or " disabled until restart: ") .. tostring(err)
  pcall(logf or function(m) _G.KMM_Conductor.guard_log(m) end, msg)
  return p
end
function KC.chronicle_line(ev)
  local f = { string.format("%.2f", ev.day or 0), tostring(ev.id), ev.type, ev.town_sid or "", ev.town_name or "",
              ev.a and KC.name(ev.a) or "", ev.b and KC.name(ev.b) or "", ev.leader_sid or "", ev.leader_name or "", ev.status or "applied", ev.text or "" }
  for i = 1, #f do f[i] = tostring(f[i]):gsub("[\t\r\n]", " ") end
  KC.append_file(KC.P.chronicle_path or "C:/KenshiModMap/logs/chronicle.log", table.concat(f, "\t"))
end

KC.bus = nil  -- forward
KC.REMNANTS, KC.start_succession = nil   -- forward (мир v2)

-- подписчики шины: KMM_Conductor.subscribe(pattern, fn) → id; pattern = точный type, префикс с «*» ("stock_*", "town_*") или "*".
-- Каждый подписчик вызывается под своим pcall: первая ошибка отключает только его (причина → logs/debug.log), emit не ломается.
-- Сюда подпишется директор сценария (будущее; сейчас его нет). Для него же кольцо RECENT последних событий — пока никто не читает.
KC.SUBS, KC.SUB_NEXT, KC.SUB_DEPTH = {}, 1, 0
KC.RECENT, KC.RECENT_MAX = {}, 64
function KC.sub_log(msg)
  local line = os.date("%Y-%m-%d %H:%M:%S") .. " [KMM_Conductor] " .. msg
  pcall(KC.append_file, (KC.P and KC.P.guard and KC.P.guard.debug_log) or "C:/KenshiModMap/logs/debug.log", line)
  KC.log(msg)
end
function KC.sub_match(pat, t)
  if pat == "*" then return true end
  if pat:sub(-1) == "*" then return t:sub(1, #pat - 1) == pat:sub(1, -2) end
  return pat == t
end
function KC.notify(ev)
  KC.RECENT[#KC.RECENT + 1] = ev
  if #KC.RECENT > KC.RECENT_MAX then table.remove(KC.RECENT, 1) end
  if KC.SUB_DEPTH >= 4 then return end   -- подписчик эмитит из подписчика: глубже 4 уровней не раздаём (защита от петли)
  KC.SUB_DEPTH = KC.SUB_DEPTH + 1
  local t = tostring(ev.type)
  for i = 1, #KC.SUBS do
    local s = KC.SUBS[i]
    if s and not KC.GL.h_live(s, "off") and KC.sub_match(s.pattern, t) then
      local ok, err = pcall(s.fn, ev)
      if not ok then KC.GL.h_bad(s, "off", "KMM_Conductor.sub:" .. tostring(s.pattern) .. "#" .. tostring(s.id), err, string.format("subscriber #%d (%s)", s.id, s.pattern), KC.sub_log)
      else KC.GL.h_done(s, "off") end
    end
  end
  KC.SUB_DEPTH = KC.SUB_DEPTH - 1
end
function KC.subscribe(pattern, fn)
  if type(pattern) ~= "string" or pattern == "" or type(fn) ~= "function" then error("subscribe(pattern:string, fn:function)", 2) end
  local id = KC.SUB_NEXT; KC.SUB_NEXT = KC.SUB_NEXT + 1
  KC.SUBS[#KC.SUBS + 1] = { id = id, pattern = pattern, fn = fn }
  return id
end
function KC.unsubscribe(id)
  for i = #KC.SUBS, 1, -1 do if KC.SUBS[i].id == id then table.remove(KC.SUBS, i); return true end end
  return false
end

-- REV2 (ревизия видения, 2026-11-12): репутация предателя, оппортунизм при распаде, осторожность слабых, совместные рейды, исход рейда на базу.
-- Параметры P.rev2 (значения по умолчанию заданы при регистрации); каждая связка в r2safe: первая ошибка отключает только её.
KC.REV2_OFF = {}
function KC.R2() return (KC.P and KC.P.rev2) or {} end
function KC.r2safe(nm, fn, ...)
  if KC.GL.h_live(KC.REV2_OFF, nm) then return nil end
  local ok, a, b = pcall(fn, ...)
  if not ok then KC.GL.h_bad(KC.REV2_OFF, nm, "KMM_Conductor.rev2_" .. nm, a, "rev2 " .. nm, KC.sub_log); return nil end
  KC.GL.h_done(KC.REV2_OFF, nm)
  return a, b
end

-- видимая цепочка KMM_Town (раз в 30 с в городе игрока): не пишем в журнал/хронику/сейв, иначе вытеснят войны и договоры
KC.EPHEMERAL = { town_craft = true, town_haul = true, town_delivered = true, town_caravan_loaded = true,
                    ws_applied = true, ws_cleared = true, ws_skip = true, town_alarm = true,
                    self_retreat = true, self_surrender_attempt = true,
                    traveler_arrived = true, raid_scout = true, courier = true,
                    goal_done = true, pilgrimage = true, stronghold_hire = true }   -- ROADS: путники, разведчики, гонцы   -- Self: частые события, только шина   -- ws_*: LINKN (шина и подписчики, без журнала)
KC.WSL = {}   -- LINKN: смена владельца города -> настоящий вариант города через KMM_Native (блок ниже, перед ensure_slots)
KC.WS_TRIG = { town_captured = true, revolt = true, town_rejoined = true, leader_killed = true, leader_captured = true }
KC.react_impl, KC.REACT_OFF = nil   -- реакции CORE (определены ниже)
KC.ore_campaign_try = nil   -- LINKS2: настоящая кампания ванильного ИИ за рудник (определена после faction_obj)
function KC.emit(ev)   -- ev.type обязателен; stock_*/town_* (KMM_Stock/KMM_Town) идут той же дорогой: журнал, chronicle.log, шина, подписчики
  if type(ev) ~= "table" or type(ev.type) ~= "string" then error("emit(ev): ev.type must be a string", 2) end
  ev.day = ev.day or KC.DAY
  local nc = KC.P._ncur   -- родная кампания запущена для этой пары в этот день: событие помечено native (колонна Traces не нужна)
  if nc and nc.day == KC.DAY and ev.a == nc.a and ev.b == nc.b and ev.native == nil then ev.native = true end
  ev.attacker, ev.defender = ev.a and KC.name(ev.a) or "", ev.b and KC.name(ev.b) or ""
  if KC.EPHEMERAL[ev.type] then KC.bus(ev); KC.notify(ev); return ev end   -- частые события видимой цепочки: только шина и подписчики
  ev.id = KC.S.next_id; KC.S.next_id = KC.S.next_id + 1
  KC.S.events[#KC.S.events + 1] = ev
  if #KC.S.events > KC.MAX_EVENTS then table.remove(KC.S.events, 1) end
  KC.chronicle_line(ev)
  KC.bus(ev)
  KC.notify(ev)
  KC.RX = KC.RX or {}   -- HEALTH: флаг реакций (KC.REACT_OFF зеркалит его для старых читателей)
  if KC.react_impl and not KC.GL.h_live(KC.RX, "off") then
    KC.REACT_OFF = nil
    local okr, er = pcall(KC.react_impl, ev)
    if not okr then KC.GL.h_bad(KC.RX, "off", "KMM_Conductor.react", er, "react"); KC.REACT_OFF = true
    else KC.GL.h_done(KC.RX, "off") end
  end
  if KC.WS_TRIG[ev.type] and KC.WSL.on_event then KC.WSL.on_event() end
  if KC.GL.hook then KC.GL.hook(ev) end   -- GOALS: опасность вокруг оплотов
  return ev
end

function KC.relic_trigger(fid, why)
  local f = KC.S.F[fid]
  if not (f and f.relic and f.alive) then return end
  -- ответ на их собственную агрессию — не повод (иначе мобилизация вечная); повод — то, что пришло извне
  if (why == "attacked" or why == "lost_town") and KC.DAY - (f.last_war or -1000) < (KC.P.relic.retaliation_days or 30) then return end
  f.trigger_day = KC.DAY; f.trigger_why = why
end

-- договоры ------------------------------------------------------------------------------
function KC.treaty_between(a, b, ttype)
  for _, t in pairs(KC.S.treaties) do
    if t.active and ((t.a == a and t.b == b) or (t.a == b and t.b == a)) and (not ttype or t.type == ttype) then return t end
  end
end
function KC.allies_of(fid, types)
  local out = {}
  for _, t in pairs(KC.S.treaties) do
    if t.active and types[t.type] and (t.a == fid or t.b == fid) then out[#out + 1] = { t = t, other = (t.a == fid) and t.b or t.a } end
  end
  return out
end
function KC.GL.banned(a, b)   -- VASSALS: жёсткий запрет договоров: мятежник ↔ государство, против которого восстал (и его вассалы/союзники), лорные войны, хаос
  local V = KC.CFG.vassals
  if not V or not a or not b then return false end
  if not KC.GL.NA then
    KC.GL.NA, KC.GL.NA_CL = {}, {}
    for _, p in ipairs(V.never_ally or {}) do KC.GL.NA[p[1] .. "|" .. p[2]] = true; KC.GL.NA[p[2] .. "|" .. p[1]] = true end
    for _, c in ipairs(V.closure or {}) do local st = {}; for _, x in ipairs(c.against or {}) do st[x] = true end; KC.GL.NA_CL[c.rebel] = st end
  end
  if KC.GL.NA[a .. "|" .. b] then return true end
  for _, pr in ipairs({ { a, b }, { b, a } }) do
    local cl = KC.GL.NA_CL[pr[1]]
    if cl then   -- живое замыкание: вторая сторона сейчас в военном/оборонном/вассальном договоре с врагом мятежника
      for _, t in pairs(KC.S.treaties) do
        if t.active and t.type ~= "trade" and t.type ~= "nonaggression" and (t.a == pr[2] or t.b == pr[2]) and cl[(t.a == pr[2]) and t.b or t.a] then return true end
      end
    end
  end
  return false
end
function KC.sign(ttype, a, b, why)
  if KC.GL.banned(a, b) then KC.S.stats.pact_blocked = (KC.S.stats.pact_blocked or 0) + 1; return nil end
  local T = KC.P.treaties
  local t = { id = KC.S.next_tid, type = ttype, a = a, b = b, since = KC.DAY, term = KC.DAY + (T.term_days[ttype] or 360), active = true, why = why }
  KC.S.next_tid = KC.S.next_tid + 1
  KC.S.treaties[t.id] = t
  KC.add_rel(a, b, T.relation_on_sign[ttype] or 10)
  KC.S.dirty_rel[a .. "|" .. b] = true   -- NATIVE_MAP п.5: флаги договора пишутся в RelationData
  KC.S.stats.signed = KC.S.stats.signed + 1
  KC.S.stats.signed_by[ttype .. ": " .. why] = (KC.S.stats.signed_by[ttype .. ": " .. why] or 0) + 1
  KC.emit({ type = "treaty_signed", a = a, b = b, treaty = ttype, text = string.format("%s and %s sealed a %s pact (%s).", KC.name(a), KC.name(b), ttype, why) })
  return t
end
function KC.break_treaty(t, why, betrayer)
  if not t.active then return end
  t.active = false
  KC.S.stats.broken[why] = (KC.S.stats.broken[why] or 0) + 1
  if betrayer then
    local other = (t.a == betrayer) and t.b or t.a
    KC.S.F[other].trust[betrayer] = KC.clamp(KC.trust(other, betrayer) + KC.P.treaties.trust_betrayal, -100, 100)
    KC.add_rel(t.a, t.b, KC.P.treaties.relation_on_betrayal)
    KC.S.stats.betrayals = KC.S.stats.betrayals + 1
    KC.emit({ type = "betrayal", a = betrayer, b = other, treaty = t.type, text = string.format("%s betrayed %s and broke their %s pact (%s).", KC.name(betrayer), KC.name(other), t.type, why) })
  else
    KC.emit({ type = "treaty_broken", a = t.a, b = t.b, treaty = t.type, text = string.format("The %s pact between %s and %s has ended (%s).", t.type, KC.name(t.a), KC.name(t.b), why) })
  end
end

-- обязательства: на союзника напали → помощь по силам и цене, иначе — неисполнение (доверие вниз, договор может рухнуть)
function KC.obligations(victim, attacker)
  for _, e in ipairs(KC.allies_of(victim, { defense = true, military = true, vassal = true })) do
    local t, ally = e.t, e.other
    if ally ~= attacker and KC.S.F[ally].alive and KC.DAY - (t.last_help or -1000) >= (KC.P.treaties.help_cooldown_days or 30) then
      t.last_help = KC.DAY
      local cost = KC.P.treaties.help_cost * KC.S.F[ally].strength
      local can = KC.power(ally) > 0.5 * KC.power(attacker) or KC.S.F[ally].wealth > 3 * cost
      if can and KC.rel(ally, attacker) < 30 then
        KC.S.F[ally].strength = KC.S.F[ally].strength - cost
        KC.S.F[victim].strength = KC.S.F[victim].strength + cost * 0.8
        KC.S.F[attacker].strength = KC.S.F[attacker].strength - cost * 0.5
        KC.add_trust(ally, victim, KC.P.treaties.trust_fulfilled)
        KC.add_rel(ally, attacker, -10)
        KC.S.stats.help = KC.S.stats.help + 1
        KC.emit({ type = "ally_help", a = ally, b = victim, text = string.format("%s honoured its pact and sent help to %s against %s.", KC.name(ally), KC.name(victim), KC.name(attacker)) })
        if KC.S.F[victim].player then KC.S.pending_dispatch = { ally = ally, enemy = attacker, why = "defend" } end
      else
        KC.S.stats.failed_help = KC.S.stats.failed_help + 1
        KC.S.F[victim].trust[ally] = KC.clamp(KC.trust(victim, ally) + KC.P.treaties.trust_unfulfilled, -100, 100)
        if KC.trust(victim, ally) < KC.P.treaties.min_trust and not (t.type == "vassal" and ally == t.b) then KC.break_treaty(t, "unfulfilled obligation", ally)   -- VASSALS: слабость вассала присягу не рвёт
        else KC.emit({ type = "ally_failed", a = ally, b = victim, text = string.format("%s did not come to the aid of %s.", KC.name(ally), KC.name(victim)) }) end
      end
    end
  end
end

KC.bus = function(ev)
  local B = KC.P.bus
  if ev.type == "raid" or ev.type == "town_captured" or ev.type == "attack_repelled" or ev.type == "leader_killed" or ev.type == "leader_captured"
     or ev.type == "attack_on_player" or ev.type == "base_raid" or ev.type == "base_campaign" or ev.type == "joint_raid" then   -- U2: base_campaign = рейд кампанией
    local att, vic = ev.a, ev.b
    if not (att and vic and KC.S.F[att] and KC.S.F[vic]) then return end
    KC.relic_trigger(vic, "attacked")
    if ev.type == "town_captured" then KC.relic_trigger(vic, "lost_town") end
    if ev.type ~= "attack_repelled" then KC.obligations(vic, att) end
    for _, f in ipairs(KC.near(vic, B.radius)) do
      if f ~= att and f ~= vic then
        local F = KC.S.F[f]
        if KC.power(f) < KC.power(att) and KC.rel(f, att) < 0 then F.strength = F.strength * (1 - B.fear_strength_cost) end   -- страх: оборона
        if KC.power(vic) < B.weak_ratio * KC.power(f) and KC.rel(f, vic) < 0 then F.opp[vic] = KC.DAY + B.opportunism_days end -- оппортунизм
        if KC.rel(f, att) <= -50 and KC.rel(vic, att) <= -50 then KC.add_rel(f, vic, B.common_enemy_rel) end                 -- общий враг
      end
    end
    local chaos = KC.CFG.factions[att] and KC.CFG.factions[att].relic == "spread_chaos"
    for fid, F in pairs(KC.S.F) do   -- реликтовые: угроза их цели
      if F.relic and F.alive and fid ~= att then
        if (F.relic == "hunt_chaos" and chaos) or (F.relic == "hunt_xenos" and KC.CFG.factions[att].relic == "guard_tomb") then KC.relic_trigger(fid, "goal_threat") end
      end
    end
  elseif ev.type == "betrayal" then   -- REV2: нарушитель договора теряет репутацию у соседей; союзники жертвы холоднее к нему
    KC.r2safe("betrayal_rep", function()
      local R, bt, vic = KC.R2(), ev.a, ev.b
      if not (bt and vic and KC.S.F[bt] and KC.S.F[vic]) then return end
      for _, f in ipairs(KC.near(bt, B.radius)) do
        local F = KC.S.F[f]
        if f ~= bt and f ~= vic and F.alive and not F.player then
          if KC.treaty_between(f, bt) or KC.rel(f, bt) > -50 then F.trust[bt] = KC.clamp(KC.trust(f, bt) + (R.betrayal_trust or -10), -100, 100) end
          if KC.treaty_between(f, vic) then KC.add_rel(f, bt, R.betrayal_ally_rel or -8) end
        end
      end
      KC.S.stats.rep_hits = (KC.S.stats.rep_hits or 0) + 1
    end)
  elseif ev.type == "revolt" or ev.type == "faction_split" or ev.type == "warlord_rose" or ev.type == "succession_crisis" then
    KC.r2safe("weak_opportunism", function()   -- REV2: распад державы — повод для недругов (оппортунизм, как после рейда)
      local vic = (ev.type == "succession_crisis") and ev.a or ev.b
      if not (vic and KC.S.F[vic] and KC.S.F[vic].alive) then return end
      for _, f in ipairs(KC.near(vic, B.radius)) do
        if f ~= vic and f ~= ev.a and not KC.S.F[f].player and KC.rel(f, vic) < 0 and KC.power(vic) < B.weak_ratio * 1.5 * KC.power(f) then
          KC.S.F[f].opp[vic] = KC.DAY + B.opportunism_days
        end
      end
    end)
  elseif ev.type == "chaos_cult" then
    for fid, F in pairs(KC.S.F) do if F.relic == "hunt_chaos" and F.alive then KC.relic_trigger(fid, "goal_threat") end end
  elseif ev.type == "player_raid" then
    -- союзники игрока присоединяются к его рейду, если выгодно (враждуют с целью и есть силы)
    local X = ev.b
    for _, e in ipairs(KC.allies_of(ev.a, { defense = true, military = true, vassal = true })) do
      local al = e.other
      if KC.S.F[al].alive and KC.rel(al, X) <= -30 and KC.power(al) > 0.3 * KC.power(X) and not KC.S.pending_dispatch then
        KC.S.pending_dispatch = { ally = al, enemy = X, why = "join raid" }
        KC.S.stats.joined = (KC.S.stats.joined or 0) + 1
        KC.emit({ type = "ally_joins", a = al, b = X, text = string.format("%s sent fighters to join the Nameless against %s.", KC.name(al), KC.name(X)) })
        break
      end
    end
  elseif ev.type == "faction_fell" then
    if KC.REMNANTS then KC.REMNANTS(ev.a) end
    for _, e in ipairs(KC.allies_of(ev.a, { defense = true, military = true, vassal = true, trade = true })) do KC.relic_trigger(e.other, "crisis") end
    for fid, F in pairs(KC.S.F) do if F.relic == "spread_chaos" then KC.relic_trigger(fid, "crisis") end end   -- распад кормит Хаос
  end
end

---------------------------------------------------------------------------------------------- экономика и режимы
function KC.economy()
  local E = KC.P.economy
  for fid, f in pairs(KC.S.F) do
    if f.alive and not f.player then
      local nc = KC.ncities(f)
      local nh = KC.ntowns(f) - nc
      local income = nc * (E.income_city or 8) + nh * (E.income_holding or 2) + (f.relic and (E.relic_income or 10) or 1)
      income = income + 2 * #KC.allies_of(fid, { trade = true })
      if f.townless then income = income + ((KC.P.goals or {}).camp_income or 3) + (f.founded or 0) * ((KC.P.goals or {}).found_income or 1.5) end   -- GOALS: лагерь кормит своих
      local upkeep = f.strength * E.upkeep_per_strength * ((f.mode == "mobilized") and E.mobilized_upkeep_mult or 1)
      -- против снежного кома: каждый город дороже, чем больше городов и чем дальше он от столицы
      local cap_t = KC.capital(fid)
      for t in pairs(f.towns) do
        if KC.is_city(t) then
          upkeep = upkeep + (E.city_upkeep_base or 2) * (1 + nc * (E.city_upkeep_scale or 0.08))
          if cap_t then upkeep = upkeep + (E.dist_upkeep or 3) * KC.town_dist(t, cap_t) / 100000 end
        end
      end
      f.wealth = f.wealth + income - upkeep
      if f.townless and f.wealth > ((KC.P.goals or {}).wealth_cap or 320) then f.wealth = (KC.P.goals or {}).wealth_cap or 320 end
      if f.wealth < E.min_wealth then f.strength = f.strength + f.wealth * 0.5; f.wealth = E.min_wealth end
      if f.relic then f.strength = math.max(f.strength, (E.relic_floor or 0.5) * f.strength0 * (((f.components or 100) < ((KC.P.know or {}).weak_below or 12)) and 0.3 or (((f.components or 100) < 30) and 0.6 or 1))) end   -- реликтовые малочисленны, но стойки
      local nt = KC.ntowns(f)
      if f.towns0 > 0 or nt > 0 then   -- подъём / упадок (для слухов): ±2 города от старта, объявляется один раз
        if nt >= f.towns0 + 2 and not f.rise_told then f.rise_told = true; KC.emit({ type = "faction_rise", a = fid, text = string.format("%s grows strong: %d towns now.", KC.name(fid), nt) }) end
        if nt <= f.towns0 - 2 and not f.decline_told then f.decline_told = true; KC.emit({ type = "faction_decline", a = fid, text = string.format("%s is losing ground: %d towns left.", KC.name(fid), nt) }) end
      end
      local cap = 15 + f.wealth * E.strength_per_wealth * 0.1 + KC.ncities(f) * 10 + (KC.ntowns(f) - KC.ncities(f)) * 3
      if f.metal_cap then cap = math.min(cap, math.max(15, f.metal_cap)) end   -- армию не вооружить без металла: спрос падает → равновесие
      f.strength = math.max(0, f.strength + E.strength_regen * (cap - f.strength))
      local broken_ = KC.ntowns(f) == 0 and f.towns0 > 0 and f.wealth < (E.collapse_wealth or 25) and f.strength < (E.collapse_share or 0.35) * f.strength0
      if f.townless and f.strength < ((KC.P.goals or {}).camp_floor or 0.4) * f.strength0 then f.strength = ((KC.P.goals or {}).camp_floor or 0.4) * f.strength0 end   -- GOALS: лагерь пополняется, бездомные не вымирают
      if (f.strength < E.collapse_strength or broken_) and KC.ntowns(f) == 0 and not f.relic and not f.townless then
        f.alive = false
        KC.S.stats.fell = KC.S.stats.fell + 1
        for _, t in pairs(KC.S.treaties) do if t.active and (t.a == fid or t.b == fid) then t.active = false end end
        KC.emit({ type = "faction_fell", a = fid, text = string.format("%s is no more: their last bands scattered.", KC.name(fid)) })
      end
    end
  end
  for _, t in pairs(KC.S.treaties) do   -- дань вассала
    if t.active and t.type == "vassal" and KC.S.F[t.a].alive and KC.S.F[t.b].alive then
      local d = KC.S.F[t.b].wealth * KC.P.treaties.tribute_share
      KC.S.F[t.b].wealth = KC.S.F[t.b].wealth - d
      KC.S.F[t.a].wealth = KC.S.F[t.a].wealth + d
    end
  end
end

function KC.relic_modes()
  local R = KC.P.relic
  for fid, f in pairs(KC.S.F) do
    if f.relic and f.alive then
      if f.mode == "focused" and KC.DAY - f.trigger_day <= R.trigger_memory_days then
        f.mode, f.mode_since = "mobilized", KC.DAY
        KC.S.stats.mobilized = KC.S.stats.mobilized + 1
        KC.emit({ type = "mobilized", a = fid, text = string.format("%s have mobilised (%s). Their warbands now walk openly.", KC.name(fid), f.trigger_why or "?") })
      elseif f.mode == "mobilized" and KC.DAY - f.trigger_day > R.demobilize_after_days then
        f.mode, f.mode_since = "focused", KC.DAY
        KC.emit({ type = "demobilized", a = fid, text = string.format("%s have withdrawn to their own concerns again.", KC.name(fid)) })
      end
    end
  end
end

function KC.treaties_review()
  local T = KC.P.treaties
  for id, t in pairs(KC.S.treaties) do   -- AUDIT-B: неактивные договоры старше года удаляются (иначе сейв растёт без предела)
    if not t.active then
      t.off = t.off or KC.DAY
      if KC.DAY - t.off > (T.prune_days or 360) then KC.S.treaties[id] = nil end
    end
  end
  for _, t in pairs(KC.S.treaties) do
    if t.active then
      if not (KC.S.F[t.a].alive and KC.S.F[t.b].alive) then t.active = false
      elseif KC.rel(t.a, t.b) < T.break_rel then KC.break_treaty(t, "interests diverged")
      elseif KC.DAY >= t.term then
        if KC.rel(t.a, t.b) >= 20 and KC.trust(t.a, t.b) >= 0 then t.term = KC.DAY + (T.term_days[t.type] or 360)
        else KC.break_treaty(t, "term expired") end
      end
    end
  end
  for _, f in pairs(KC.S.F) do   -- доверие медленно возвращается к нулю; недоверие уходит втрое медленнее
    for o, v in pairs(f.trust) do
      if v > 0 then f.trust[o] = math.max(0, v - T.trust_decay_per_tick) elseif v < 0 then f.trust[o] = math.min(0, v + T.trust_decay_per_tick * 0.3) end
    end
  end
end

---------------------------------------------------------------------------------------------- действия (utility)
KC.PAIRS_BY_TOWN = {}
KC.TOWN_NAME = {}
KC.ROLE, KC.SITE, KC.ORIG_OWNER = {}, {}, {}
KC.TOTAL_CITIES = 0
function KC.pairs_index()
  for _, I in pairs(KC.CFG.town_info or {}) do if I.kind == "city" then KC.TOTAL_CITIES = KC.TOTAL_CITIES + 1 end end
  for fid, f in pairs(KC.CFG.factions) do for _, t in ipairs(f.towns or {}) do KC.ORIG_OWNER[t] = fid end end
  for k, list in pairs(KC.CFG.roles or {}) do KC.ROLE[k] = {}; for _, fid in ipairs(list) do KC.ROLE[k][fid] = true end end
  for _, k in ipairs({ "drugs", "drug_ban", "slavers", "slave_markets", "anti_slavers", "thieves", "fences", "technopriests" }) do KC.ROLE[k] = KC.ROLE[k] or {} end
  for _, st in ipairs(KC.CFG.sites or {}) do KC.SITE[st.sid] = st end
  for _, c in ipairs(KC.CFG.towns or {}) do
    KC.TOWN_NAME[c.town_sid] = c.town_name
    if c.enabled then KC.PAIRS_BY_TOWN[c.town_sid] = KC.PAIRS_BY_TOWN[c.town_sid] or {}; table.insert(KC.PAIRS_BY_TOWN[c.town_sid], c) end
  end
  for _, f in pairs(KC.CFG.factions) do
    for i, t in ipairs(f.towns or {}) do KC.TOWN_NAME[t] = KC.TOWN_NAME[t] or (f.town_names or {})[i] end
  end
end

function KC.leader_outcome(town_sid, attacker, defender)
  local list = KC.PAIRS_BY_TOWN[town_sid]
  if not list then return false end
  for _, c in ipairs(list) do
    if not KC.S.resolved[c.leader_sid] and not KC.S.pending[c.leader_sid] then
      local typ = (math.random() < KC.P.outcome.capture_share) and "leader_captured" or "leader_killed"
      local ev = KC.emit({ type = typ, a = attacker, b = defender, town_sid = c.town_sid, town_name = c.town_name, leader_sid = c.leader_sid,
                        leader_name = c.leader_name, status = "pending",
                        text = string.format("Word spreads that %s %s when %s struck at %s.", c.leader_name,
                          typ == "leader_killed" and "fell" or "was taken prisoner", KC.name(attacker), c.town_name) })
      KC.S.pending[c.leader_sid] = ev.id
      if KC.start_succession then KC.start_succession(defender, c.leader_name .. (typ == "leader_killed" and " fell" or " was captured")) end
      return true
    end
  end
  return false
end

function KC.FPOS(fid)   -- центр фракции; у активированного осколка без своих городов — центр родителя
  local c = KC.CFG.factions[fid]
  if c and c.x then return c.x, c.z end
  local f = KC.S.F[fid]
  local pc = f and f.proxy and KC.CFG.factions[f.proxy]
  if pc and pc.x then return pc.x, pc.z end
  return nil
end
end
if KC._BOOT then KC._BOOT() end
