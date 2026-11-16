-- KMM_Veterans - ветераны боёв (2026-11-13, "живой мир"). Связка Медицина/травмы: часть выживших после боёв дирижёра остаётся в городе.
-- Дальний мир: S.ext.veterans (пул по городам: <= pool_max записей на город, старение/уход). Старые сейвы создают слот лениво.
-- Видимое: игрок рядом с городом с ветеранами -> KMM_Traces.request (1 отряд, 1..2 бойца фракции-хозяина, тег "veteran");
--   <= 1 группа на город в vis_gap дней. Слух: C.emit veteran_settled / veteran_seen (текст en): "In the bar of X sit veterans of ...".
-- Увечья (2026-11-13, родной путь): рантайм-вызовов amputate/setLimb НЕТ. Калеки = шаблон отряда с отрицательным значением конечности
--   у CHARACTER в FCS (напр. -150 у человека - конечность отсутствует с рождения). Шаблоны кладёт генератор в traces.json как
--   factions[fid].veteran = "<sid отряда>"; request идёт с sid=этот шаблон, иначе откат на tier_pick (целые ветераны).
--   Примечание: Vector3 из Lua можно передать таблицей {x=,y=,z=} (createRandomSquad в Traces так работает) - прежнее "не создать" неверно.
-- Вербовка: безопасного способа нет (Player:recruit без диалога меняет владение отряда) - не делаем.
-- Безотказность: всё под pcall, первая ошибка отключает модуль до перезапуска (logs/veterans.log). Работы на старте нет.
local M = rawget(_G, "KMM_Veterans") or {}
_G.KMM_Veterans = M
M.cfg = M.cfg or {
  enabled = true, pool_max = 6, max_age = 45, leave_chance = 0.04,   -- уход ветерана в сутки (на запись)
  vis_gap = 3, vis_radius = 70000, group_max = 2, tick_gap = 5, emit_gap = 8, max_emits_day = 2,
  maim = true, maim_chance = 0.5,   -- maim: брать шаблон-калеку (factions[fid].veteran), если он есть в traces.json
  chance = { raid = 0.5, attack_repelled = 0.6, town_captured = 0.8, siege_lifted = 0.6, siege_progress = 0.15, predator_raid = 0.35, predator_cleared = 0.5, fate_wounded = 0.25 },
  log = "C:/KenshiModMap/logs/veterans.log",
}
local CF = M.cfg
local OFF, SUB, LASTCLK = false, nil, 0
M.stats = M.stats or { added = 0, groups = 0, aged = 0, maimed = 0 }

local function log(msg)
  pcall(function()
    local f = io.open(CF.log, "a")
    if f then f:write(os.date("%Y-%m-%d %H:%M:%S"), " [KMM_Veterans] ", tostring(msg), "\n"); f:close() end
  end)
end
local function C() return rawget(_G, "KMM_Conductor") end
-- HEALTH (2026-11-15): отказы идут в реестр ядра KMM_Gov (ключи KMM_Veterans.<механика>): пауза 1/5/30 мин и повтор вместо «до перезапуска».
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
local ST = { off = false }   -- HEALTH: OFF = ST.off (пауза реестра или навсегда без Gov)
local function is_off() OFF = live(ST, "off"); return OFF end
local function mod_fail(nm, e) local p = down(ST, "off", "KMM_Veterans.module", e); OFF = true; log(nm .. " " .. why_p(p) .. ": " .. tostring(e)) end
local function guard(nm, fn, ...)
  if is_off() then return nil end
  local ok, a, b = pcall(fn, ...)
  if not ok then mod_fail(nm, a); return nil end
  h_ok("KMM_Veterans.module")
  return a, b
end

function M.slot()
  local c = C(); local S = c and c.state and c.state()
  if not S then return nil end
  S.ext = S.ext or {}
  local x = S.ext.veterans
  if type(x) ~= "table" then x = { v = 1, towns = {}, vis = {}, em = {}, emd = { -1, 0 }, last = -1, n = 0 }; S.ext.veterans = x end
  x.towns = x.towns or {}; x.vis = x.vis or {}; x.em = x.em or {}; x.emd = x.emd or { -1, 0 }
  return x
end
function M.state() return M.slot() end
function M.disabled() return is_off() end

local function tinfo(sid)
  for _, t in ipairs(C().towns()) do if t.sid == sid then return t end end
end
local KIND = { raid = "a raid", attack_repelled = "a repelled attack", town_captured = "the fall of the town", siege_lifted = "the siege",
               siege_progress = "the siege", predator_raid = "a beast raid", predator_cleared = "the beast hunt", fate_wounded = "a bloody skirmish" }

-- запись ветерана в пул города (только дальний мир)
function M.add(sid, kind, day)
  local c, x = C(), M.slot()
  if not (x and sid and c) then return false end
  local t = tinfo(sid)
  if not (t and t.x and t.owner and t.owner ~= c.cfg().player_faction) then return false end
  local p = x.towns[sid]
  if not p then p = {}; x.towns[sid] = p end
  if #p >= CF.pool_max then table.remove(p, 1) end
  p[#p + 1] = { d = day, k = kind, w = (math.random() < CF.maim_chance) and 1 or 0 }
  x.n = (x.n or 0) + 1; M.stats.added = M.stats.added + 1
  if x.emd[1] ~= day then x.emd = { day, 0 } end
  if (x.em[sid] or -99) + CF.emit_gap <= day and x.emd[2] < CF.max_emits_day then
    x.em[sid] = day; x.emd[2] = x.emd[2] + 1
    c.emit({ type = "veteran_settled", fid = t.owner, town_sid = sid, town_name = t.name,
             text = string.format("In the bar of %s sit veterans of %s. Some of them will not fight again.", t.name, KIND[kind] or "old battles") })
  end
  return true
end

local function on_event(ev)
  if is_off() or not CF.enabled or not (ev and ev.type) then return end
  local c = C(); if not c then return end
  local p = CF.chance[ev.type]
  if not p or not ev.town_sid or math.random() > p then return end
  guard("add", M.add, ev.town_sid, ev.type, math.floor(c.day() or 0))
end

local TRF
local function veteran_sid(fid)
  if not CF.maim then return nil end
  if TRF == nil then TRF = (C().read_json and C().read_json("traces.json", "C:/KenshiModMap/build/KMM_Conductor/traces.json")) or false end
  local f = TRF and TRF.factions and TRF.factions[fid]
  local sid = f and f.veteran
  if type(sid) == "string" and sid ~= "" then return sid end
end

local function materialize(sid, p, t, day, x)
  local T = rawget(_G, "KMM_Traces"); local c = C()
  local n = math.min(CF.group_max, #p)
  local wounded = 0
  for i = 1, n do wounded = wounded + (p[i].w or 0) end
  local vs = (wounded > 0) and veteran_sid(t.owner) or nil
  if vs then M.stats.maimed = M.stats.maimed + 1 end
  local ok = T.request({ tag = "veteran", fid = t.owner, sid = vs, shift = 0, n = 1, size = n, from_x = t.x, from_z = t.z,
                         to_fid = t.owner, to_x = t.x, to_z = t.z })
  if ok then
    x.vis[sid] = day; M.stats.groups = M.stats.groups + 1
    c.emit({ type = "veteran_seen", fid = t.owner, town_sid = sid, town_name = t.name,
             text = string.format("Old soldiers loiter near the gates of %s, trading war stories.", t.name) })
  end
  return ok
end

function M.daily(day)
  local x = M.slot(); local c = C()
  if not x then return end
  local keys = {}
  for key in pairs(x.towns) do keys[#keys + 1] = key end
  table.sort(keys)
  for _, sid in ipairs(keys) do
    local p = x.towns[sid]
    for i = #p, 1, -1 do   -- старение/уход
      if day - (p[i].d or day) > CF.max_age or math.random() < CF.leave_chance then table.remove(p, i); M.stats.aged = M.stats.aged + 1 end
    end
    if #p == 0 then x.towns[sid] = nil
    else
      local T = rawget(_G, "KMM_Traces")
      local t = tinfo(sid)
      if T and T.request and T.near and t and t.x and t.owner and t.owner ~= c.cfg().player_faction
         and (x.vis[sid] or -99) + CF.vis_gap <= day and T.near(t.x, t.z, CF.vis_radius) then
        materialize(sid, p, t, day, x)
      end
    end
  end
  x.last = day
end

local function tick()
  if is_off() or not CF.enabled then return end
  local c = C()
  if not (c and c.state and c.state() and c.subscribe) then return end
  if not SUB then
    SUB = {}
    for ty in pairs(CF.chance) do SUB[#SUB + 1] = c.subscribe(ty, on_event) end
  end
  local day = math.floor(c.day() or 0)
  local x = M.slot()
  if x and day > x.last then M.daily(day) end
end

M._tick = function() guard("tick", tick) end

if rawget(_G, "Events") and Events.on and not M._hooked then
  M._hooked = true
  local function guarded(fn) return function(...) local ok, e = pcall(fn, ...); if not ok then mod_fail("handler", e) end end end
  Events.on("GameWorld::charsUpdate", guarded(function()
    local now = os.clock()
    if now - LASTCLK < CF.tick_gap then return end
    LASTCLK = now
    M._tick()
  end))
end
