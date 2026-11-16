-- KMM_Predators (2026-11-13): цикл «хищник-жертва» на дорогах. Горячий участок (караваны в пути + память дорог игрока) привлекает бандитов,
-- враждебных хозяину ближайшего города: на участке «гнездо» засады. Караваны (запись S.roads.tr, не видимые) через участок теряют груз
-- (C.road_lost + C.loot_add), хозяин города через несколько дней шлёт патруль-зачистку, гнездо исчезает, участок остывает, цикл идёт в другом месте.
-- Видимое: игрок рядом с гнездом -> KMM_Traces.request (засада бандитов, тир по силе гнезда); рядом при зачистке -> патруль хозяина.
-- Состояние: S.ext.predators = { v, last, nests = {[ключ участка] = {...}}, cool = {[ключ] = день}, hist = {...<=12}, stat = {} } (< 4 КБ).
-- Всё под pcall; ошибка -> модуль выключается до перезапуска. Старт ленивый, без работы на загрузке.
-- R4 (2026-11-15): ЗАПАХ ЗОНЫ ЯДРА. Бой/смерть рядом с игроком (шина дирижёра: deed из KMM_Deeds, player_raid, attack_on_player) и
-- разорённые караваны гнезда (игрок рядом) -> ZoneSmell:addSmell(SMELLMSG_BLOOD|CORPSE, ключ, точка) в зоне точки. Ванильные хищники и
-- падальщики с HUNTING_BLOODSMELL приходят сами, без нашего спавна. Ключ = объект Faction (живёт всю сессию; ключ карты сообщений void*),
-- запасной ключ = персонаж игрока. Через smell_ttl игровых дней источник снимается addSmell(SMELLMSG_NONE) (? семантика снятия).
-- Y4: засада держит участок всем отрядом ограниченное время через наряд ядра (Blackboard:addSquadJob + центр движения), потом ванильный пакет;
-- отказ ядра -> прежний addOrder (блок «НАРЯД ЗАСАДЫ» ниже).
-- Засада бандитов остаётся своим спавном: бандитский биомный спавн (_spawnASquad) в Lua недоступен. M.smell/M.smell_level отдаются KMM_Herds.
-- S1 (2026-11-15): запах — промах зоны в точке -> источник у игрока, выключение только если API ни разу не сработал; ЭХО ПАВШИХ (блок EC ниже).
local M = {}
local DISABLED = false
-- RETIRED (2026-11-16, owner: cut predators, vanilla patrols and nests hunt fine): crash 0xC0000005 in ZoneSmell::periodicUpdate
-- after our addSmell. Whole module is a no-op: no nests, ambushes, smell, soul echo, squad jobs. S.ext.predators stays in the save untouched.
local RETIRED = true
local LOGP = "C:/KenshiModMap/logs/predators.log"
local CFGP = { max_nests = 6, daily_chance = 0.4, hit_radius = 7000, vis_radius = 45000, bandit_range = 140000, rel_max = -10,
               patrol_min = 4, patrol_span = 4, patrol_days = 3, max_age = 22, cool_days = 14, max_per_fid = 2, vis_gap = 900, vis_per_day = 1, tick_gap = 5,
               loss_base = 0.15, loss_per_power = 0.12, loss_cap = 0.6, min_score = 1.0, cell_cool = 0.4, sdir = "C:/KenshiModMap/state/",
               smell = true, smell_r = 12000, smell_gap = 90, smell_day = 12, smell_ttl = 0.5, smell_max_src = 8, smell_cell = 16000,
               smell_aop_gap = 1800, smell_aop_poor_down = true,   -- кровь от нападения на игрока: пауза (реальные с) и не у лежащего нищего
               squadjob = true, hold_h = 6, hold_pp = 1, sq_max = 9, sq_scan = 800, sq_retry_s = 30, sq_grace_d = 3, sq_verify_h = 1, sq_drift_r = 3000 }
M.P = CFGP
local RT = {}      -- runtime: {[ключ] = os.clock последнего вызова Traces}
local STARTED = false

local function dlog(msg) pcall(function() local f = io.open(LOGP, "a"); if f then f:write(tostring(msg), "\n"); f:close() end end) end
-- HEALTH (2026-11-15): отказы идут в реестр ядра KMM_Gov (ключи KMM_Predators.module|smell|echo|squadjob|centermove): пауза 1/5/30 мин
-- и повтор вместо «до перезапуска». Навсегда — только нет API в движке (noapi) или крэш-сторож (crash). Без Gov — прежнее поведение.
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
local function wlog(what, p, err) dlog(what .. (p and (" failed, retry in " .. p .. " s: ") or " disabled until restart: ") .. tostring(err)) end
local MOD = { off = false }
local function is_off() if RETIRED then DISABLED = true; return true end; DISABLED = live(MOD, "off"); return DISABLED end
local function off(why) local p = down(MOD, "off", "KMM_Predators.module", why); DISABLED = true; wlog("predators", p, why) end
local function guarded(nm, fn) return function(...) if is_off() then return end; local ok, er = pcall(fn, ...); if not ok then off(nm .. ": " .. tostring(er)) end end end

-- крэш-сторож нативного вызова (pcall не ловит нативный краш): lock до вызова, удаляется после успеха.
-- Lock при старте = прошлая сессия упала на этом вызове -> метод отключён навсегда (.off).
local PROBE = {}
local function probe_ok(x)
  local st = PROBE[x]
  if st == nil then
    local sd = CFGP.sdir; local lock, offp = sd .. "probe_" .. x .. ".lock", CFGP.sdir .. "probe_" .. x .. ".off"
    st = true
    pcall(function()
      local f = io.open(offp, "r")
      if f then f:close(); st = false; return end
      f = io.open(lock, "r")
      if f then
        f:close(); st = false
        local o = io.open(offp, "w"); if o then o:write("disabled: previous session crashed in ", x); o:close() end
        os.remove(lock)
        dlog("native method " .. x .. " DISABLED forever: previous session crashed during the call (state/probe_" .. x .. ".off)")
      end
    end)
    PROBE[x] = st
  end
  return st
end
local function probe_call(x, fn)
  if not probe_ok(x) then return false end
  local lock = CFGP.sdir .. "probe_" .. x .. ".lock"
  local first = not PROBE[x .. "#done"]
  if first then pcall(function() local f = io.open(lock, "w"); if f then f:write(tostring(os.time())); f:close() end end) end
  local ok, er = pcall(fn)
  if first then pcall(os.remove, lock); PROBE[x .. "#done"] = true end
  return ok, er
end
-- приказ загруженному отряду: kind "hold" = HOLD_POSITION в точке, "patrol" = PATROL_TOWN у точки
local function order_squad(pls, x, z, kind)
  if not (rawget(_G, "TaskType") and pls) then return 0 end
  local tt = kind == "hold" and TaskType.HOLD_POSITION or TaskType.PATROL_TOWN
  if not tt then return 0 end
  local n = 0
  for _, pl in ipairs(pls) do
    local okl, leader = pcall(function() return pl:getSquadLeader() end)
    if okl and leader and type(leader) ~= "string" then
      if probe_call("addOrder", function() leader:addOrder(nil, tt, nil, false, true, { x = x, y = 0, z = z }) end) then n = n + 1 end
    end
  end
  return n
end
M.order_squad = order_squad
local function C_() return rawget(_G, "KMM_Conductor") end
local function T_() return rawget(_G, "KMM_Traces") end

-- R4: запах зоны -------------------------------------------------------------------------------------------------------------
-- SM: только рантайм (не в сейве): src = активные источники для снятия, last = {[ячейка|ключ] = os.clock}, st = счётчики для лога.
local SM = { off = false, sub = false, fails = 0, ok = 0, zl = 0, src = {}, last = {}, day = -1, n = 0, st = {} }
local MSG = { none = 0, corpse = 1, blood = 2 }   -- ZoneSmell.SmellMessageType (EnumsReference), если таблицы нет в _G
local function smsg(kind)
  local ok, v = pcall(function() return ZoneSmell.SmellMessageType["SMELLMSG_" .. kind:upper()] end)
  return (ok and type(v) == "number") and v or MSG[kind]
end
local function player_xyz()
  local ok, x, y, z, ch = pcall(function()
    for _, c in pairs(getPlayerInterface():getAllPlayerCharacters()) do
      local p = c:getPosition()
      if p then return p.x, p.y or 0, p.z, c end
    end
  end)
  if ok and x then return x, y, z, ch end
end
-- S1: путь ✓код GameWorld.zoneMgr (ZoneManager) -> getZoneMap(Vector3) (ZoneManager.h, RVA 0x291160) -> ZoneMap.zoneSmell (ZoneSmell*);
-- ✓игра: 4 источника в сессии 2026-11-15 (predators.log). nil = в точке нет загруженной зоны (или у неё нет ZoneSmell) — это не поломка API.
local function zone_smell(x, y, z)
  local zm = getGameWorld().zoneMgr:getZoneMap({ x = x, y = y, z = z })
  if not zm then return nil, "no zone map" end
  local zs = zm.zoneSmell
  if not zs then return nil, "zone without ZoneSmell" end
  return zs
end
-- HEALTH: зона камеры/игрока ядра (ZoneManager:getCurrentZoneMap, BindingsReference ZoneManager) — последний запасной путь, когда
-- getZoneMap(Vector3) у точки и у игрока дал nil (лог «smell api unavailable ... nil»: зона не найдена, а не поломка API)
local function cur_zone_smell()
  local zm = getGameWorld().zoneMgr:getCurrentZoneMap()
  if not zm then return nil, "no current zone" end
  local zs = zm.zoneSmell
  if not zs then return nil, "current zone without ZoneSmell" end
  return zs
end
-- есть ли API запаха в движке: nil = есть; строка = чего нет (тогда навсегда, noapi)
local function smell_api_missing()
  local ok, why = pcall(function()
    local gw = getGameWorld()
    local zm = gw and gw.zoneMgr
    if not zm then return "GameWorld.zoneMgr" end
    if type(zm.getZoneMap) ~= "function" then return "ZoneManager:getZoneMap" end
    return nil
  end)
  if not ok then return nil end   -- ошибка проверки — не доказательство отсутствия
  return why
end
local function zone_loaded(x, y, z)
  local ok, v = pcall(function() return getGameWorld().zoneMgr:isZoneLoadedT({ x = x, y = y, z = z }) end)
  if ok then return tostring(v) end
  return "?"
end
local function level_of(zs)   -- getGeneralSmellLevel(SMELL_BLOOD_AND_CORPSES) или nil
  local ok, v = pcall(function()
    local t = 1
    pcall(function() t = SmellType.SMELL_BLOOD_AND_CORPSES or 1 end)
    return zs:getGeneralSmellLevel(t)
  end)
  if ok and type(v) == "number" then return v end
end
local function smell_level(x, z)
  local _, py = player_xyz()
  local ok, zs = pcall(zone_smell, x, py or 0, z)
  if ok and zs then return level_of(zs) end
end
local function fobj(fid)
  if not fid then return nil end
  local ok, f = pcall(function() return getGameWorld().factionMgr:getFactionByStringID(fid) end)
  if ok and f and type(f) ~= "string" then return f end
end
function M.smell_retract(ck)
  local s = SM.src[ck]; if not s then return false end
  if RETIRED then SM.src[ck] = nil; return false end
  SM.src[ck] = nil
  local okz, zs = pcall(zone_smell, s.x, s.y, s.z)
  if not (okz and zs) then return false end
  local ok, er = probe_call("addSmellNone", function() zs:addSmell(smsg("none"), s.key, { x = s.x, y = s.y, z = s.z }) end)
  SM.st.retract = (SM.st.retract or 0) + 1
  local lv = level_of(zs)
  dlog(string.format("smell retract %s (%s) lvl=%s %s", ck, tostring(s.why), lv and string.format("%.3f", lv) or "?",
       ok and "ok" or ("failed: " .. tostring(er or "probe off"))))
  return ok
end
-- smell(x, z, kind "blood"|"corpse", key_fid, why) -> ok, lvl0 (уровень зоны до), причина отказа
local function smell(x, z, kind, key_fid, why)
  if is_off() or live(SM, "off") or CFGP.smell == false then return false, nil, "off" end
  local C = C_(); if not (C and C.day) then return false, nil, "no conductor" end
  local px, py, pz, pch = player_xyz()
  if not px then return false, nil, "no player" end
  x, z = x or px, z or pz
  if math.sqrt((x - px) ^ 2 + (z - pz) ^ 2) > CFGP.smell_r then SM.st.far = (SM.st.far or 0) + 1; return false, nil, "far" end
  local day = math.floor(C.day())
  if SM.day ~= day then SM.day, SM.n = day, 0 end
  if SM.n >= CFGP.smell_day then SM.st.capped = (SM.st.capped or 0) + 1; return false, nil, "day cap" end
  local ck = math.floor(x / CFGP.smell_cell) .. ":" .. math.floor(z / CFGP.smell_cell) .. "|" .. tostring(key_fid or "pc")
  local now = os.clock()
  if SM.last[ck] and now - SM.last[ck] < CFGP.smell_gap then SM.st.gap = (SM.st.gap or 0) + 1; return false, nil, "gap" end
  -- S1: точка в незагруженной зоне -> запах у игрока (его зона загружена; событие и так в smell_r от него). Промах зоны выключает запах,
  -- только пока API ни разу не сработал (SM.ok == 0): прежде три промаха за сессию выключали работающий запах навсегда (лог 2026-11-15).
  local okz, zs, zw = pcall(zone_smell, x, py, z)
  if not (okz and zs) and (x ~= px or z ~= pz) then
    local ok2, zs2, zw2 = pcall(zone_smell, px, py, pz)
    if ok2 and zs2 then
      SM.st.at_pc = (SM.st.at_pc or 0) + 1
      if SM.zl < 6 then SM.zl = SM.zl + 1; dlog(string.format("smell zone miss (%s) at %d,%d loaded=%s -> source at the player", okz and tostring(zw) or tostring(zs), math.floor(x), math.floor(z), zone_loaded(x, py, z))) end
      x, z, okz, zs = px, pz, true, zs2
    elseif ok2 then zw = zw2 or zw end
  end
  if not (okz and zs) then   -- HEALTH: третий путь — текущая зона ядра
    local ok3, zs3 = pcall(cur_zone_smell)
    if ok3 and zs3 then
      SM.st.at_cur = (SM.st.at_cur or 0) + 1
      if SM.zl < 6 then SM.zl = SM.zl + 1; dlog(string.format("smell zone miss at %d,%d and at the player -> source in the current zone (getCurrentZoneMap)", math.floor(x), math.floor(z))) end
      x, z, okz, zs = px, pz, true, zs3
    end
  end
  if not (okz and zs) then
    local why = okz and tostring(zw) or ("error " .. tostring(zs))
    SM.st.miss = (SM.st.miss or 0) + 1
    if SM.zl < 6 then SM.zl = SM.zl + 1; dlog(string.format("smell zone miss (%s) at %d,%d loaded=%s, player zone too -> skipped (ok so far %d)", why, math.floor(x), math.floor(z), zone_loaded(x, py, z), SM.ok)) end
    -- HEALTH: промах зоны — не отказ (зона не загружена); навсегда только если API запаха нет в движке
    local miss = smell_api_missing()
    if miss then
      forever(SM, "off", "KMM_Predators.smell", "no " .. miss, "noapi")
      dlog("smell api unavailable (" .. miss .. " missing in the engine) -> smell off, fallbacks only")
    end
    return false, nil, "no zone"
  end
  local pos = { x = x, y = py, z = z }
  local lvl0 = level_of(zs)
  local mt = smsg(kind)
  local key = fobj(key_fid) or pch
  local okf, hasf = pcall(function() return type(zs.addSmell) == "function" end)
  if okf and hasf == false then
    forever(SM, "off", "KMM_Predators.smell", "no ZoneSmell:addSmell", "noapi")
    dlog("smell api unavailable: ZoneSmell:addSmell missing in the engine -> smell off, fallbacks only")
    return false, lvl0, "api"
  end
  local ok, er = probe_call("addSmell", function() zs:addSmell(mt, key, pos) end)
  if not ok and key ~= pch and pch and probe_ok("addSmell") then
    key = pch; ok, er = probe_call("addSmell", function() zs:addSmell(mt, key, pos) end)
  end
  if not ok then
    SM.fails = SM.fails + 1
    dlog("smell addSmell failed (" .. tostring(why) .. "): " .. tostring(er or "probe off"))
    if not probe_ok("addSmell") then
      forever(SM, "off", "KMM_Predators.smell", "crash lock state/probe_addSmell.off", "crash")
      dlog("smell api unavailable: addSmell crash lock -> smell off, fallbacks only")
    else
      local p = down(SM, "off", "KMM_Predators.smell", er)
      wlog("smell", p, er)
    end
    return false, lvl0, "api"
  end
  SM.last[ck] = now; SM.n = SM.n + 1; SM.st[kind] = (SM.st[kind] or 0) + 1
  SM.ok = SM.ok + 1
  h_ok("KMM_Predators.smell")
  if SM.ok == 1 then dlog("smell api ok: GameWorld.zoneMgr getZoneMap -> ZoneMap.zoneSmell addSmell (first source this session)") end
  if SM.src[ck] then SM.src[ck].d = C.day() else SM.src[ck] = { key = key, x = x, y = py, z = z, d = C.day(), why = why } end
  local ns, od = 0, nil
  for k2, v in pairs(SM.src) do ns = ns + 1; if k2 ~= ck and (not od or v.d < SM.src[od].d) then od = k2 end end
  if ns > CFGP.smell_max_src and od then M.smell_retract(od) end   -- лишний старейший источник снимаем сразу
  dlog(string.format("smell: %s %s at %d,%d key=%s lvl0=%s", kind, tostring(why), math.floor(x), math.floor(z), tostring(key_fid or "pc"),
       lvl0 and string.format("%.3f", lvl0) or "?"))
  return true, lvl0
end
local function smell_age(C)
  local d = C.day()
  local old = {}
  for ck, s in pairs(SM.src) do if d - s.d >= CFGP.smell_ttl or d < s.d then old[#old + 1] = ck end end
  for _, ck in ipairs(old) do M.smell_retract(ck) end
end
-- шина дирижёра -> запах: бой и смерть рядом с игроком (KMM_Deeds даёт x/z = позиция игрока; без координат — тоже игрок)
local SMELL_KIND = { killed = "corpse", executed = "corpse", killed_enemy = "corpse", defeated = "blood", defeated_enemy = "blood", captured = "blood" }
-- число из rules/conductor.json params.predators, иначе CFGP
function M.pp(k)
  local C = C_()
  local ok, v = pcall(function() return C.cfg().params.predators[k] end)
  if ok and v ~= nil then return v end
  return CFGP[k]
end
-- кровь от нападения НА игрока: не ловушка для избитого. Не чаще smell_aop_gap реальных секунд (на все фракции), и не пока свой игрока
-- лежит, а отряд нищ и слаб (KMM_Nemesis.poor — ванильные числа: деньги, цена вещей, награда, прозвище, численность, навык).
function M.aop_ok()
  local now = os.clock()
  local t = SM.aop_t
  if t and now >= t and now - t < M.pp("smell_aop_gap") then return false, "aop gap" end
  if M.pp("smell_aop_poor_down") ~= false then
    local NM = rawget(_G, "KMM_Nemesis")
    local okp, poor = false, false
    if NM and NM.poor then okp, poor = pcall(NM.poor) end
    if okp and poor == true then
      local down = false
      pcall(function()
        for _, c in pairs(getPlayerInterface():getAllPlayerCharacters()) do
          local ok, d = pcall(function() return c:isDown() or c:isUnconcious() end)
          if ok and d == true then down = true; break end
        end
      end)
      if down then return false, "poor and down" end
    end
  end
  SM.aop_t = now
  return true
end
function M.on_bus(ev)
  if type(ev) ~= "table" then return end
  local kind, key
  if ev.type == "deed" then kind, key = SMELL_KIND[ev.kind], ev.b
  elseif ev.type == "player_raid" then kind, key = "blood", ev.b
  elseif ev.type == "attack_on_player" then
    local ok, why = M.aop_ok()
    if not ok then
      SM.st.aop_skip = (SM.st.aop_skip or 0) + 1
      if (SM.st.aop_skip or 0) <= 20 then dlog("smell skipped (attack_on_player): " .. tostring(why)) end
      return
    end
    kind, key = "blood", ev.a
  end
  if not kind then return end
  SM.st.bus = (SM.st.bus or 0) + 1
  smell(ev.x, ev.z, kind, key, ev.type .. (ev.kind and (":" .. ev.kind) or ""))
end
local EC   -- S1 эхо павших (ниже): счёт смертей по месту — с той же шины, независимо от запаха
local function on_bus_g(ev)   -- ошибка выключает только свою связку (запах или эхо), не модуль
  if is_off() then return end
  if EC and not live(EC, "off") then
    local oke, ee = pcall(EC.note, ev)
    if not oke then wlog("soul echo", down(EC, "off", "KMM_Predators.echo", ee), ee) end
  end
  if live(SM, "off") then return end
  local ok, er = pcall(M.on_bus, ev)
  if not ok then wlog("smell link", down(SM, "off", "KMM_Predators.smell", er), er) end
end
local function smell_subscribe(C)
  if SM.sub or not C.subscribe then return end
  SM.sub = true
  local n = 0
  for _, pat in ipairs({ "deed", "player_raid", "attack_on_player" }) do
    if pcall(C.subscribe, pat, on_bus_g) then n = n + 1 end
  end
  dlog("smell bus subscribed: " .. n .. "/3 (deed, player_raid, attack_on_player)")
end
M.smell, M.smell_level, M.sm = smell, smell_level, SM

-- Y4 (2026-11-15): НАРЯД ЗАСАДЫ ЧЕРЕЗ ЯДРО. Заспавненная засада держит участок дороги всем отрядом ограниченное время:
-- Blackboard:addSquadJob(SQUAD_LEADER и SQUAD_1, HOLD_POSITION, хендл лидера, TP_URGENT, 1, TARGET_SELF/TARGET_LEADER, TEE_REMOVE_WHOLE_SQUADS,
-- час начала, час конца) + у лидера AI:setCenterOfMovement(точка гнезда) и setManuveringFreedomLevel(STAY_CLOSE).
-- Реестр нарядов (ревью batch7 M3) — в сейве: C.state().ext.pred_sq = { { k = ключ платуна, f = fid, p = пакет, t0, till, x, z, cm, cx/cy/cz, mv }, ... }
-- (строки и числа, без указателей между тактами). Задачи доски движок пишет в сейв (Blackboard::_serialiseJobList), поэтому наряд снимается
-- всегда: срок (hold_h + hold_pp*power игровых часов), потолок sq_max, откат часов; записи из сейва (после загрузки или смены мира) — при первом
-- нахождении отряда. Отряд не найден (выгружен) — повтор раз в sq_retry_s, пока не прошло sq_grace_d дней после срока.
-- Снятие (M4): clearAllTheJobs всегда; replaceAIPackage(пакет при спавне, иначе текущий на момент снятия); лидеру — прежние центр движения и
-- уровень свободы (AI.centerOfMovement / AI.ordersMovement, прочитаны до наряда), не прочитались — центр у лидера и ROAM_FAR.
-- Проба (M5): регистрация (задач на доске больше) -> «squadjob registered»; не выросло или вызов упал -> «squadjob FAIL», наряд выключен до
-- перезапуска, засада по-старому (addOrder HOLD_POSITION). Работа: через sq_verify_h часов лидер не дальше sq_drift_r от точки -> «squadjob ok»,
-- ушёл -> «squadjob drift» и addOrder этому отряду; два ухода без подтверждённой работы -> наряд выключен до перезапуска.
-- Дела игрока без свидетелей (deed.witnessed == false, Y1) засаду не вызывают: засада идёт только от гнезда (visible), запах — физический след.
-- ? единицы startTime/endTime (берём час суток 0..23, как расписание задач пакета FCS); ? стабильность ключа платуна через сохранение;
-- ? участники кроме лидера держатся у центра через наряд отряда (перечислить их из Lua нельзя: characterHandles - lightuserdata).
local SQ = { off = false, cm_off = false, tick_off = false, live = {}, S = nil,
             fresh = setmetatable({}, { __mode = "k" }), try = setmetatable({}, { __mode = "k" }), vt = setmetatable({}, { __mode = "k" }),
             st = { reg = 0, work = 0, drift = 0, fail = 0, skip = 0, fb = 0, rel = 0, gone = 0, drop = 0, load = 0 } }
local function enum(path, nm, dflt)   -- значение enum из таблиц KenshiLua (EnumsReference) или запасное число
  local ok, v = pcall(function() local t = _G; for part in path:gmatch("[^.]+") do t = t[part] end; return t[nm] end)
  return (ok and type(v) == "number") and v or dflt
end
local function sq_jobs(board)   -- число задач отряда на доске или nil (поля не читаются)
  local ok, n = pcall(function() return #board.squadJobs + #board.squadJobs2 + #board.leaderJobs end)
  if ok and type(n) == "number" then return n end
end
-- реестр текущего мира; новая таблица C.state() (загрузка/смена мира) -> её записи из сейва «не свои»: снимаются при первом нахождении
local function sq_list(C)
  local S = C.state(); if not S then return nil end
  S.ext = S.ext or {}
  if SQ.S ~= S then
    SQ.S = S; SQ.fresh, SQ.try, SQ.vt = setmetatable({}, { __mode = "k" }), setmetatable({}, { __mode = "k" }), setmetatable({}, { __mode = "k" })
    local q, ok = S.ext.pred_sq, {}
    if type(q) == "table" then
      for _, r in ipairs(q) do
        if type(r) == "table" and type(r.k) == "string" and type(r.t0) == "number" and type(r.till) == "number" then ok[#ok + 1] = r end
      end
    end
    S.ext.pred_sq = ok
    if #ok > 0 then dlog(string.format("squadjob: world loaded with %d holds from the save -> release when each squad is found", #ok)) end
  end
  if type(S.ext.pred_sq) ~= "table" then S.ext.pred_sq = {} end
  SQ.live = S.ext.pred_sq
  return SQ.live
end
local function sq_find(fid, key)   -- загруженный платун фракции по ключу (≤ sq_scan) или nil
  local fo = fobj(fid); if not fo then return nil end
  local ok, lst = pcall(function() return fo:getActivePlatoons() end)
  if not (ok and lst) then return nil end
  local n = 0
  pcall(function() n = #lst end)
  for i = 1, math.min(n, CFGP.sq_scan or 800) do
    local okp, pl = pcall(function() return lst[i] end)
    if okp and pl then
      local okk, k = pcall(function() return pl:getPlatoonStringID() end)
      if okk and k == key then return pl end
    end
  end
end
local function leader_ai(pl)   -- лидер и его AI (или nil)
  local okl, leader = pcall(function() return pl:getSquadLeader() end)
  if not (okl and leader and type(leader) ~= "string") then return nil end
  local oka, ai = pcall(function() return leader:getAI() end)
  if oka and ai and type(ai) ~= "string" then return leader, ai end
  return leader, nil
end
-- снять наряд с загруженного отряда: true; отряд не найден -> false (вызовов движка нет)
function SQ.release(r, why)
  local pl = sq_find(r.f, r.k)
  if not pl then return false end
  local parts = {}
  local okb, board = pcall(function() return pl:getBlackboard() end)
  if okb and board and type(board) ~= "string" then
    local okc = probe_call("clearJobs", function() board:clearAllTheJobs() end)
    parts[#parts + 1] = "jobs " .. (okc and "cleared" or "FAIL")
    local gd, src
    if r.p then
      pcall(function() gd = getGameWorld().gamedata:getData(r.p, enum("itemType", "AI_PACKAGE", 72)) end)
      src = r.p
    end
    if not gd then
      pcall(function() gd = board:getCurrentPackage().packageData end)
      src = "current" .. (r.p and (" (" .. r.p .. " no data)") or "")
    end
    if gd and type(gd) ~= "string" then
      local okr = probe_call("pred_pkg", function() board:replaceAIPackage(gd) end)
      parts[#parts + 1] = "pkg " .. src .. (okr and " ok" or " FAIL")
    else parts[#parts + 1] = "pkg unknown" end
  else parts[#parts + 1] = "no blackboard" end
  if r.cm and not live(SQ, "cm_off") then
    local leader, ai = leader_ai(pl)
    if ai then
      local cen, how
      if type(r.cx) == "number" and type(r.cz) == "number" then cen, how = { x = r.cx, y = r.cy or 0, z = r.cz }, "saved"
      else
        pcall(function() local p = leader:getPosition(); if p and p.x then cen = { x = p.x, y = p.y or 0, z = p.z } end end)
        how = cen and "leader" or "?"
      end
      local mv = (type(r.mv) == "number") and r.mv or enum("AI.AIManuverabilityOrders", "ROAM_FAR", 2)
      local okf = probe_call("centerMove", function()
        if cen then ai:setCenterOfMovement(cen) end
        ai:setManuveringFreedomLevel(mv)
      end)
      parts[#parts + 1] = string.format("center %s move %d%s %s", how, mv, type(r.mv) == "number" and "" or " (ROAM_FAR)", okf and "ok" or "FAIL")
    else parts[#parts + 1] = "center: no ai" end
  end
  SQ.st.rel = SQ.st.rel + 1
  dlog(string.format("squadjob release key=%s (%s): %s", r.k, why, table.concat(parts, "; ")))
  return true
end
-- -> "ok" | "skip" (отряд не готов: фолбэк без отключения) | "fail" (API: наряд выключен до перезапуска), причина
function SQ.hold(pl, x, z, hours, fid, C)
  if live(SQ, "off") or CFGP.squadjob == false then return "skip", "off" end
  local okl, leader = pcall(function() return pl:getSquadLeader() end)
  if not (okl and leader and type(leader) ~= "string") then return "skip", "no leader" end
  local okb, board = pcall(function() return pl:getBlackboard() end)
  if not (okb and board and type(board) ~= "string") then return "skip", "no blackboard" end
  local okk, key = pcall(function() return pl:getPlatoonStringID() end)
  if not (okk and type(key) == "string" and key ~= "") then return "skip", "no platoon key" end
  local okh, h = pcall(function() return leader:getHandle() end)
  if not (okh and h) then return "skip", "no leader handle" end
  local list = sq_list(C); if not list then return "skip", "no state" end
  local psid
  pcall(function() local s = board:getCurrentPackage().packageData.stringID; if type(s) == "string" and s ~= "" then psid = s end end)
  local y = 0
  pcall(function() y = leader:getPosition().y or 0 end)
  local _, ai = leader_ai(pl)
  local cx, cy, cz, mv   -- прежнее движение лидера (до наряда) — для снятия
  if ai then
    pcall(function() local c = ai.centerOfMovement; if c and type(c.x) == "number" and type(c.z) == "number" then cx, cy, cz = c.x, c.y or 0, c.z end end)
    pcall(function() local m = ai.ordersMovement; if type(m) == "number" then mv = m end end)
  end
  local d = C.day()
  local h0 = math.floor((d % 1) * 24) % 24
  local h1 = (h0 + math.max(1, math.ceil(hours))) % 24
  local n0 = sq_jobs(board)
  local tt, pri, tee = enum("TaskType", "HOLD_POSITION", 30), enum("taskPriority", "TP_URGENT", 3), enum("TaskEndEvent", "TEE_REMOVE_WHOLE_SQUADS", 2)
  local ok, er = probe_call("squadJob", function()
    board:addSquadJob(enum("SquadMemberType", "SQUAD_LEADER", 2), tt, h, pri, 1.0, enum("TaskTargetType", "TARGET_SELF", 1), tee, h0, h1)
    board:addSquadJob(enum("SquadMemberType", "SQUAD_1", 0), tt, h, pri, 1.0, enum("TaskTargetType", "TARGET_LEADER", 2), tee, h0, h1)
  end)
  local n1 = ok and sq_jobs(board) or nil
  if not ok or (n0 and n1 and n1 <= n0) then
    SQ.st.fail = SQ.st.fail + 1
    local why = ok and string.format("jobs on board %d -> %d (not registered)", n0, n1) or tostring(er or "probe off (state/probe_squadJob.off)")
    local p
    if not probe_ok("squadJob") then forever(SQ, "off", "KMM_Predators.squadjob", why, "crash") else p = down(SQ, "off", "KMM_Predators.squadjob", why) end
    dlog(string.format("squadjob FAIL key=%s fid=%s: %s -> squad jobs %s, addOrder fallback", key, tostring(fid), why,
         p and ("paused " .. p .. " s") or "off until restart"))
    return "fail", why
  end
  h_ok("KMM_Predators.squadjob")
  local cm = "off"
  if not live(SQ, "cm_off") then
    if ai then
      local okc, ec = probe_call("centerMove", function()
        ai:setCenterOfMovement({ x = x, y = y, z = z })
        ai:setManuveringFreedomLevel(enum("AI.AIManuverabilityOrders", "STAY_CLOSE", 1))
      end)
      if okc then cm = "ok"; h_ok("KMM_Predators.centermove")
      else
        if probe_ok("centerMove") then down(SQ, "cm_off", "KMM_Predators.centermove", ec)
        else forever(SQ, "cm_off", "KMM_Predators.centermove", "crash lock state/probe_centerMove.off", "crash") end
        cm = "FAIL " .. tostring(ec or "probe off")
      end
    else cm = "no ai" end
  end
  local r = { k = key, f = fid, p = psid, t0 = d, till = d + hours / 24, x = x, z = z, cm = (cm == "ok") or nil, cx = cx, cy = cy, cz = cz, mv = mv }
  list[#list + 1] = r; SQ.fresh[r] = true
  while #list > (CFGP.sq_max or 9) do   -- потолок: старейший наряд снимается, а не забывается
    local old = table.remove(list, 1); SQ.st.drop = SQ.st.drop + 1
    if not SQ.release(old, "cap") then dlog("squadjob: cap " .. tostring(CFGP.sq_max) .. ", squad " .. tostring(old.k) .. " not loaded - hold left to its end hour") end
  end
  SQ.st.reg = SQ.st.reg + 1
  dlog(string.format("squadjob registered key=%s fid=%s hold=%.1fh hours %d-%d jobs=%s->%s center=%s prev=%s pkg=%s", key, tostring(fid), hours, h0, h1,
       tostring(n0 or "?"), tostring(n1 or "?"), cm, (cx and string.format("%d,%d", math.floor(cx), math.floor(cz)) or "?") .. "/" .. tostring(mv or "?"),
       tostring(psid or "?")))
  return "ok"
end
-- проверка работы: лидер у точки через sq_verify_h часов -> «ok»; ушёл -> addOrder (фолбэк) этому отряду
local function sq_verify(r, pl, d)
  local leader = leader_ai(pl)
  local x, z
  if leader then pcall(function() local p = leader:getPosition(); x, z = p.x, p.z end) end
  if type(x) ~= "number" or type(z) ~= "number" then return end
  local dd = math.sqrt((x - r.x) ^ 2 + (z - r.z) ^ 2)
  local hh = (d - r.t0) * 24
  if dd <= (CFGP.sq_drift_r or 3000) then
    r.v = "ok"; SQ.st.work = SQ.st.work + 1
    dlog(string.format("squadjob ok key=%s fid=%s: leader %.0f from the point after %.1fh (job holds)", r.k, tostring(r.f), dd, hh))
  else
    r.v = "drift"; SQ.st.drift = SQ.st.drift + 1
    local n = order_squad({ pl }, r.x, r.z, "hold"); SQ.st.fb = SQ.st.fb + 1
    dlog(string.format("squadjob drift key=%s fid=%s: leader %.0f from the point after %.1fh -> addOrder HOLD_POSITION %d/1", r.k, tostring(r.f), dd, hh, n))
    if SQ.st.drift >= 2 and SQ.st.work == 0 and not SQ.off then
      local why = "jobs register but do not hold (" .. SQ.st.drift .. " drifts, 0 ok)"
      local p = down(SQ, "off", "KMM_Predators.squadjob", why)
      dlog("squadjob: " .. why .. " -> squad jobs " .. (p and ("paused " .. p .. " s") or "off until restart") .. ", addOrder")
    end
  end
end
function SQ.tick(C)
  local list = sq_list(C)
  if not list or #list == 0 then return end
  local d, now, keep = C.day(), os.clock(), {}
  local gap, grace = CFGP.sq_retry_s or 30, CFGP.sq_grace_d or 3
  for _, r in ipairs(list) do
    local fresh, drop = SQ.fresh[r], false
    local t = SQ.try[r]   -- повтор снятия (отряд не найден) не чаще gap
    local due = not t or now - t >= gap or now < t
    local why = fresh and "time" or "load"
    if d < r.t0 then   -- откат часов: снять сейчас, не нашли — забыть
      drop = true; SQ.st.drop = SQ.st.drop + 1
      if not SQ.release(r, "clock") then dlog("squadjob: clock went back, squad " .. r.k .. " not loaded - hold dropped") end
    elseif d >= r.till or not fresh then
      if due then
        SQ.try[r] = now
        if SQ.release(r, why) then
          drop = true; if not fresh then SQ.st.load = SQ.st.load + 1 end
        elseif d > r.till + grace then
          drop = true; SQ.st.gone = SQ.st.gone + 1
          dlog(string.format("squadjob release key=%s (%s): squad gone (unloaded/dead) %d days past the end, nothing to undo", r.k, why, grace))
        elseif not r.w then
          r.w = true
          dlog(string.format("squadjob release key=%s (%s): squad not loaded - retry when found, until day %.1f", r.k, why, r.till + grace))
        end
      end
    elseif not r.v and d >= r.t0 + (CFGP.sq_verify_h or 1) / 24 and (not SQ.vt[r] or now - SQ.vt[r] >= gap or now < SQ.vt[r]) then
      SQ.vt[r] = now
      local pl = sq_find(r.f, r.k)
      if pl then sq_verify(r, pl, d) end
    end
    if not drop then keep[#keep + 1] = r end
  end
  for i = #list, 1, -1 do list[i] = nil end
  for i, r in ipairs(keep) do list[i] = r end
end
-- on_spawn засады: наряд ядра каждому отряду, кто не принял - старый приказ addOrder
function M.ambush_hold(pls, x, z, hours, fid)
  local C = C_(); if not (C and C.day and C.state) then return order_squad(pls, x, z, "hold") end
  local fb, why = {}, nil
  for _, pl in ipairs(pls or {}) do
    local okc, res, w = pcall(SQ.hold, pl, x, z, hours, fid, C)
    if not okc then
      SQ.st.fail = SQ.st.fail + 1
      local p = down(SQ, "off", "KMM_Predators.squadjob", res)
      dlog("squadjob FAIL (error): " .. tostring(res) .. " -> squad jobs " .. (p and ("paused " .. p .. " s") or "off until restart")); res, w = "fail", res
    end
    if res ~= "ok" then fb[#fb + 1] = pl; why = w; if res == "skip" then SQ.st.skip = SQ.st.skip + 1 end end
  end
  if #fb > 0 then
    local n = order_squad(fb, x, z, "hold")
    SQ.st.fb = SQ.st.fb + #fb
    dlog(string.format("squadjob fallback addOrder %d/%d squads (%s)", n, #fb, tostring(why)))
  end
end
M.sq = SQ

local function slot(C)
  local S = C.state(); if not S then return nil end
  S.ext = S.ext or {}
  local e = S.ext.predators
  if type(e) ~= "table" then e = {}; S.ext.predators = e end
  e.v = e.v or 1; e.last = e.last or -1; e.nests = type(e.nests) == "table" and e.nests or {}
  e.cool = type(e.cool) == "table" and e.cool or {}; e.hist = type(e.hist) == "table" and e.hist or {}
  e.stat = type(e.stat) == "table" and e.stat or {}
  return e
end
local function stat(e, k, n) e.stat[k] = (e.stat[k] or 0) + (n or 1) end
local function hist(e, day, kind, text) e.hist[#e.hist + 1] = { d = math.floor(day), k = kind, t = text }; while #e.hist > 12 do table.remove(e.hist, 1) end end
local function dist(ax, az, bx, bz) return math.sqrt((ax - bx) ^ 2 + (az - bz) ^ 2) end
local function seg_dist(px, pz, ax, az, bx, bz)
  local dx, dz = bx - ax, bz - az
  local l2 = dx * dx + dz * dz
  local t = l2 > 0 and math.max(0, math.min(1, ((px - ax) * dx + (pz - az) * dz) / l2)) or 0
  return dist(px, pz, ax + dx * t, az + dz * t)
end
local function ncount(t) local n = 0; for _ in pairs(t) do n = n + 1 end; return n end
local function key_of(a, b) if a > b then a, b = b, a end return a .. "|" .. b end

local function towns_map(C)
  local m, list = {}, C.towns() or {}
  for _, t in ipairs(list) do if t.x and t.z then m[t.sid] = t end end
  return m, list
end
local function nearest_town(list, x, z, owned)
  local best, bd
  for _, t in ipairs(list) do
    if t.x and (not owned or t.owner) then local d = dist(x, z, t.x, t.z); if not bd or d < bd then best, bd = t, d end end
  end
  return best, bd
end

local TRF
local function traces_json(C)
  if TRF == nil then TRF = C.read_json("traces.json", "C:/KenshiModMap/build/KMM_Conductor/traces.json") or false end
  return TRF
end

-- кандидаты участков: пары городов; score = число караванов в пути + тепло маршрута
local function candidates(C, e, tm, list)
  local out, seen = {}, {}
  local function add(a, b, sc)
    if a == b or not (tm[a] and tm[b]) then return end
    local k = key_of(a, b)
    if e.nests[k] or (e.cool[k] and e.cool[k] > C.day()) then return end
    local o = seen[k]
    if o then o.score = o.score + sc; return end
    o = { key = k, a = a, b = b, score = sc }; seen[k] = o; out[#out + 1] = o
  end
  local rs = C.road_state and C.road_state()
  for _, tr in pairs(rs and rs.tr or {}) do
    if tr.k == "caravan" and tr.from and tr.to and not tr.vis and tm[tr.from] and tm[tr.to] then
      add(tr.from, tr.to, 1 + C.road_route_heat(tm[tr.from].x, tm[tr.from].z, tm[tr.to].x, tm[tr.to].z) * 0.25)
    end
  end
  local cell = ((C.cfg().params or {}).roads or {}).cell or 8000
  local g = C.road_grid() or {}
  for i = 1, math.min(3, #g) do
    local cx, cz = tostring(g[i].key):match("^(-?%d+):(-?%d+)$")
    if cx and g[i].w >= 1.5 then
      local x, z = (tonumber(cx) + 0.5) * cell, (tonumber(cz) + 0.5) * cell
      local best, second
      for _, t in ipairs(list) do
        if t.x then
          local d = dist(x, z, t.x, t.z)
          if not best or d < best.d then second = best; best = { t = t, d = d } elseif not second or d < second.d then second = { t = t, d = d } end
        end
      end
      if best and second then add(best.t.sid, second.t.sid, g[i].w * 0.3) end
    end
  end
  table.sort(out, function(p, q) if p.score ~= q.score then return p.score > q.score end return p.key < q.key end)
  return out
end

local function pick_bandit(C, e, nx, nz, owner)
  local tr = traces_json(C); if not tr then return nil end
  local per = {}
  for _, n in pairs(e.nests) do per[n.fid] = (per[n.fid] or 0) + 1 end
  local best, bd
  for fid, c in pairs(C.cfg().factions or {}) do
    if c.arch == "bandit" and tr.factions[fid] and C.alive(fid) and fid ~= owner and (per[fid] or 0) < CFGP.max_per_fid and C.rel(fid, owner) <= CFGP.rel_max then
      local fx, fz = C.fpos(fid)
      if fx then local d = dist(fx, fz, nx, nz); if d <= CFGP.bandit_range and (not bd or d < bd or (d == bd and fid < best)) then best, bd = fid, d end end
    end
  end
  return best
end

local function found(C, e, day, tm, list)
  if ncount(e.nests) >= CFGP.max_nests then return end
  if math.random() >= CFGP.daily_chance then return end
  for _, c in ipairs(candidates(C, e, tm, list)) do
    if c.score < CFGP.min_score then break end
    local A, B = tm[c.a], tm[c.b]
    local f = 0.35 + math.random() * 0.3
    local nx, nz = A.x + (B.x - A.x) * f, A.z + (B.z - A.z) * f
    local near = (dist(nx, nz, A.x, A.z) <= dist(nx, nz, B.x, B.z)) and A or B
    local owner = near.owner
    local bf = owner and pick_bandit(C, e, nx, nz, owner)
    if bf then
      e.nests[c.key] = { a = c.a, b = c.b, x = nx, z = nz, fid = bf, owner = owner, power = 1, born = day, loot = 0, raids = 0,
                         pw = CFGP.patrol_min + math.floor(math.random() * CFGP.patrol_span) }
      stat(e, "nests")
      local txt = string.format("A band of %s has taken the road between %s and %s.", C.name(bf), A.name or A.sid, B.name or B.sid)
      hist(e, day, "nest", txt)
      C.emit({ type = "predator_nest", a = bf, b = owner, town_sid = near.sid, town_name = near.name, text = txt })
      return
    end
  end
end

local function raids(C, e, n, day, tm)
  local rs = C.road_state(); if not rs then return end
  local A, B = tm[n.a], tm[n.b]; if not (A and B) then return end
  local ids = {}
  for id, tr in pairs(rs.tr or {}) do
    if tr.k == "caravan" and not tr.vis and tr.f ~= n.fid and tm[tr.from] and tm[tr.to] then
      local f, t = tm[tr.from], tm[tr.to]
      if seg_dist(n.x, n.z, f.x, f.z, t.x, t.z) <= CFGP.hit_radius then ids[#ids + 1] = id end
    end
  end
  table.sort(ids)
  for _, id in ipairs(ids) do
    local tr = rs.tr[id]
    local p = math.min(CFGP.loss_cap, CFGP.loss_base + CFGP.loss_per_power * n.power)
    if tr and math.random() < p then
      local cat, cnt, victim = tr.c, tr.n or 0, tr.f
      if C.road_lost(id) then
        if cat and cnt > 0 then pcall(C.loot_add, n.fid, cat, cnt, victim) end
        n.loot = n.loot + cnt; n.raids = n.raids + 1; n.power = math.min(4, n.power + 0.25)
        stat(e, "caravans_lost"); stat(e, "cargo_lost", cnt)
        if not n.said or day - n.said >= 3 then
          n.said = day
          local txt = string.format("%s ambush caravans between %s and %s.", C.name(n.fid), A.name or n.a, B.name or n.b)
          C.emit({ type = "predator_raid", a = n.fid, b = victim, town_sid = n.a, town_name = A.name, cat = cat, n = cnt, text = txt })
        end
      end
    end
  end
end

local function cool_grid(C, n)
  pcall(function()
    local rs = C.road_state(); local cell = ((C.cfg().params or {}).roads or {}).cell or 8000
    local k = math.floor(n.x / cell) .. ":" .. math.floor(n.z / cell)
    local g = rs and rs.grid and rs.grid[k]
    if g and g.w then g.w = g.w * CFGP.cell_cool end
  end)
end

local function finish(C, e, k, n, day, tm, how)
  e.nests[k] = nil
  e.cool[k] = day + CFGP.cool_days
  cool_grid(C, n)
  local A, B = tm[n.a], tm[n.b]
  local an, bn = (A and A.name) or n.a, (B and B.name) or n.b
  local txt
  if how == "cleared" then
    stat(e, "cleared")
    txt = string.format("The patrol of %s cleared the road between %s and %s of %s.", C.name(n.owner), an, bn, C.name(n.fid))
    hist(e, day, "cleared", txt)
    C.emit({ type = "predator_cleared", a = n.owner, b = n.fid, town_sid = n.a, town_name = an, text = txt })
  else
    stat(e, "moved_on")
    txt = string.format("%s moved on from the road between %s and %s.", C.name(n.fid), an, bn)
    hist(e, day, "moved", txt)
    C.emit({ type = "predator_gone", a = n.fid, b = n.owner, town_sid = n.a, town_name = an, text = txt })
  end
  -- cooldown grid keys cleanup
  for ck, cv in pairs(e.cool) do if cv < day - 1 then e.cool[ck] = nil end end
end

local function step_day(C, e, day)
  local tm, list = towns_map(C)
  local keys = {}
  for k in pairs(e.nests) do keys[#keys + 1] = k end
  table.sort(keys)
  for _, k in ipairs(keys) do
    local n = e.nests[k]
    if not (C.alive(n.fid)) then finish(C, e, k, n, day, tm, "gone")
    else
      raids(C, e, n, day, tm)
      local age = day - n.born
      if not n.patrol and age >= n.pw and n.owner and C.alive(n.owner) then
        n.patrol = day
        local txt = string.format("%s sends a patrol to clear the road between %s and %s.", C.name(n.owner), (tm[n.a] or {}).name or n.a, (tm[n.b] or {}).name or n.b)
        hist(e, day, "patrol", txt)
        C.emit({ type = "predator_patrol", a = n.owner, b = n.fid, town_sid = n.a, town_name = (tm[n.a] or {}).name, text = txt })
      end
      if n.patrol and day - n.patrol >= CFGP.patrol_days then
        if math.random() < math.max(0.35, 0.9 - 0.15 * n.power) then finish(C, e, k, n, day, tm, "cleared")
        else n.patrol = nil; n.pw = age + 2 + math.floor(math.random() * 3); n.power = math.min(4, n.power + 0.5); stat(e, "patrol_failed") end
      elseif age >= CFGP.max_age then finish(C, e, k, n, day, tm, "gone") end
    end
  end
  found(C, e, day, tm, list)
end

local function visible(C, e)
  local T = T_(); if not T or not T.request or not T.near then return end
  local now = os.clock()
  local tm, list = towns_map(C)
  for k, n in pairs(e.nests) do
    if (n.raids or 0) > 0 and T.near(n.x, n.z, CFGP.smell_r) then   -- R4: разорённые караваны пахнут трупами -> падальщики ядра
      local sk = "s" .. k .. "#" .. math.floor(C.day())
      if not RT[sk] then RT[sk] = 1; if smell(n.x, n.z, "corpse", n.fid, "nest " .. k) then stat(e, "smell_nest") end end
    end
    if T.near(n.x, n.z, CFGP.vis_radius) then
      local pat = n.patrol and C.alive(n.owner)
      local rk = (pat and "p" or "a") .. k
      local dk = rk .. "#" .. math.floor(C.day())
      if (not RT[rk] or now - RT[rk] >= CFGP.vis_gap) and (RT[dk] or 0) < CFGP.vis_per_day then
        RT[rk] = now; RT[dk] = (RT[dk] or 0) + 1
        for kk in pairs(RT) do if type(kk) == "string" and kk:find("#", 1, true) and not kk:find("#" .. math.floor(C.day()), 1, true) then RT[kk] = nil end end
        local ok
        if pat then
          local ot = nearest_town(list, n.x, n.z, true)
          ok = T.request({ tag = "predator_patrol", fid = n.owner, shift = 0, n = 1, size = 4, from_x = ot and ot.x or n.x, from_z = ot and ot.z or n.z,
                           to_fid = n.owner, to_x = n.x, to_z = n.z,
                           on_spawn = function(pls) order_squad(pls, n.x, n.z, "patrol") end })
        else
          local sh = (n.power >= 3 and 1) or (n.power >= 2 and 0) or -1
          ok = T.request({ tag = "predator_ambush", fid = n.fid, shift = sh, n = math.min(3, 1 + math.floor(n.power / 2)), size = math.min(6, 3 + math.floor(n.power)),
                           from_x = n.x, from_z = n.z, to_fid = n.owner, to_x = n.x, to_z = n.z,
                           on_spawn = function(pls) M.ambush_hold(pls, n.x, n.z, CFGP.hold_h + CFGP.hold_pp * (n.power or 1), n.fid) end })
        end
        if ok then stat(e, pat and "vis_patrol" or "vis_ambush") end
        return
      end
    end
  end
end

-- S1 (2026-11-15): ЭХО ПАВШИХ. Soulbodies (Soul World) — не случайный спавн биома (поток relics режет их веса x0.3), а эхо боя:
-- смерти с шины (deed killed/executed/killed_enemy, ev.n, точка ev.x/z = игрок) копятся по ячейке echo_cell за последние echo_win
-- игровых дней; ночью (час суток ядра: GameWorld:getTimeStamp_inGameHours():getTotalHours() mod 24, ✓код GameWorld.h) у места с
-- >= echo_n смертями (ячейка и соседние), когда игрок в echo_rmin..echo_rmax от него, — одна заявка KMM_Traces.request(tag "soul_echo",
-- слабый шаблон Faint/Weak, n=1, малый размер, со стороны места) и приказ ядра PATROL_TOWN у места: бродят среди мёртвых. Место — раз в
-- echo_site_cool дней; живых групп <= echo_live (запись живёт echo_live_d дня или пока отряд находится), за ночь <= echo_night_max,
-- между заявками echo_gap реальных секунд. Отряд временный: убирает ядро при выгрузке, как прочие заявки Traces (утром не гонится ?).
-- Фракции нет в игре (мод выключен) — тихо выключено (одна строка лога). Событие predator_soul_echo -> слухи (Rumors). Наград и вражды нет.
-- Состояние: S.ext.predators.echo = { c = {[ячейка] = {x, z, h = {{d, n}...}}} (<= echo_cells), done = {[ячейка] = день}, nk, nn, live = {{k, d}} }.
-- Маркеры predators.log: «soul echo: death», «soul echo request», «soul echo spawned», «soul echo off».
EC = { off = false, chk = 0, chk_t = -1e9, ready = false, last = -1e9, pend = nil, n_note = 0 }
for k, v in pairs({ echo = true, echo_fid = "5007288-Soulbody.mod", echo_sids = { "5007709-Soulbody.mod", "5007715-Soulbody.mod" }, echo_cell = 1500,
                    echo_win = 1.0, echo_n = 4, echo_h0 = 20, echo_h1 = 5, echo_rmin = 2000, echo_rmax = 5000, echo_size = 3, echo_gap = 600,
                    echo_night_max = 2, echo_live = 1, echo_live_d = 0.4, echo_pend_s = 300, echo_site_cool = 3, echo_cells = 12 }) do
  if CFGP[k] == nil then CFGP[k] = v end
end
EC.KIND = { killed = true, executed = true, killed_enemy = true }
EC.TXT = { "People avoid the field near %s after dark. Something pale walks among the dead.",
           "Near %s the dead do not lie quiet. Pale shapes were seen where the blood was spilled.",
           "Travellers swear glowing figures stood over the bodies near %s. Nobody went back to look." }
function EC.slot(e)
  local s = e.echo
  if type(s) ~= "table" then s = {}; e.echo = s end
  s.c = type(s.c) == "table" and s.c or {}; s.done = type(s.done) == "table" and s.done or {}
  s.live = type(s.live) == "table" and s.live or {}; s.nk = s.nk or -1; s.nn = s.nn or 0
  return s
end
function EC.cell(x, z) local c = CFGP.echo_cell; return math.floor(x / c), math.floor(z / c) end
function EC.note(ev)
  if CFGP.echo == false or type(ev) ~= "table" or ev.type ~= "deed" or not EC.KIND[ev.kind] then return end
  local C = C_(); if not (C and C.day and C.state and C.state()) then return end
  local e = slot(C); if not e then return end
  local x, z = ev.x, ev.z
  if not (x and z) then local px, _, pz = player_xyz(); x, z = px, pz end
  if not (x and z) then return end
  local s, d = EC.slot(e), C.day()
  local cx, cz = EC.cell(x, z)
  local k = cx .. ":" .. cz
  local c = s.c[k]
  if not c then
    local n, od = 0, nil
    for k2, v in pairs(s.c) do n = n + 1; local t = v.h[#v.h] and v.h[#v.h].d or -1e9; if not od or t < od[2] then od = { k2, t } end end
    if n >= CFGP.echo_cells and od then s.c[od[1]] = nil end
    c = { h = {} }; s.c[k] = c
  end
  c.x, c.z = x, z
  local n = math.max(1, math.floor(tonumber(ev.n) or 1))
  c.h[#c.h + 1] = { d = d, n = n }
  while #c.h > 16 do table.remove(c.h, 1) end
  EC.n_note = EC.n_note + 1
  if EC.n_note <= 40 then dlog(string.format("soul echo: death %s x%d at %d,%d cell %s", tostring(ev.kind), n, math.floor(x), math.floor(z), k)) end
end
function EC.hours(C)   -- игровые часы ядра (иначе день дирижёра x24)
  local ok, h = pcall(function() return getGameWorld():getTimeStamp_inGameHours():getTotalHours() end)
  if ok and type(h) == "number" then return h end
  return C.day() * 24
end
function EC.check(C, now)   -- фракция и шаблоны в игре? true / false (выключить) / nil (повторить позже)
  if EC.ready then return true end
  if now - EC.chk_t < 60 and now >= EC.chk_t then return nil end
  EC.chk_t = now; EC.chk = EC.chk + 1
  local f = fobj(CFGP.echo_fid)
  local sids = {}
  if f then
    for _, sid in ipairs(CFGP.echo_sids or {}) do
      local ok, gd = pcall(function() return getGameWorld().gamedata:getData(sid, enum("itemType", "SQUAD_TEMPLATE", 52)) end)
      if ok and gd and type(gd) ~= "string" then sids[#sids + 1] = sid end
    end
  end
  if f and #sids > 0 then
    EC.ready, EC.sids = true, sids
    dlog(string.format("soul echo ready: faction %s, %d templates", tostring(CFGP.echo_fid), #sids))
    return true
  end
  if EC.chk >= 3 then
    forever(EC, "off", "KMM_Predators.echo", tostring(CFGP.echo_fid) .. " not in game data", "noapi")
    dlog(string.format("soul echo off: %s not in game (faction %s, templates %d) - no echoes", tostring(CFGP.echo_fid), f and "ok" or "missing", #sids))
    return false
  end
end
function EC.alive(s, d, now)   -- живые группы эха: запись моложе echo_live_d и отряд находится (или ключ не прочитан); ожидание спавна
  local keep, n = {}, 0
  for _, r in ipairs(s.live) do
    if type(r) == "table" and type(r.d) == "number" and d - r.d < CFGP.echo_live_d and d >= r.d then
      if not r.k or sq_find(CFGP.echo_fid, r.k) then keep[#keep + 1] = r; n = n + 1 end
    end
  end
  s.live = keep
  if EC.pend and now - EC.pend < CFGP.echo_pend_s and now >= EC.pend then n = n + 1 else EC.pend = nil end
  return n
end
function EC.spawned(pls, site)
  EC.pend = nil
  local C = C_(); local e = C and slot(C); if not e then return end
  local s, d = EC.slot(e), C.day()
  local n = order_squad(pls, site.x, site.z, "patrol")
  local keys = {}
  for _, pl in ipairs(pls or {}) do
    local ok, k = pcall(function() return pl:getPlatoonStringID() end)
    s.live[#s.live + 1] = { k = (ok and type(k) == "string" and k ~= "") and k or nil, d = d }
    keys[#keys + 1] = ok and tostring(k) or "?"
  end
  while #s.live > 4 do table.remove(s.live, 1) end
  local _, list = towns_map(C)
  local t = nearest_town(list, site.x, site.z)
  local where = (t and (t.name or t.sid)) or "the old battlefield"
  local txt = string.format(EC.TXT[math.random(#EC.TXT)], where)
  stat(e, "soul_echo"); hist(e, d, "soul_echo", txt)
  C.emit({ type = "predator_soul_echo", a = CFGP.echo_fid, x = site.x, z = site.z, n = site.n, town_sid = t and t.sid, town_name = t and t.name, text = txt })
  dlog(string.format("soul echo spawned: %d squad(s) [%s] at %d,%d (%d dead) order %d/%d near %s", #(pls or {}), table.concat(keys, ","),
       math.floor(site.x), math.floor(site.z), site.n, n, #(pls or {}), where))
end
function EC.step(C, e)
  if live(EC, "off") or CFGP.echo == false then return end
  local T = T_(); if not (T and T.request) then return end
  local s, d, now = EC.slot(e), C.day(), os.clock()
  -- старые смерти и отметки мест
  for k, c in pairs(s.c) do
    local h = {}
    for _, r in ipairs(c.h or {}) do if type(r) == "table" and type(r.d) == "number" and d - r.d <= CFGP.echo_win and d >= r.d then h[#h + 1] = r end end
    if #h == 0 then s.c[k] = nil else c.h = h end
  end
  for k, dd in pairs(s.done) do if type(dd) ~= "number" or d - dd > CFGP.echo_site_cool or d < dd then s.done[k] = nil end end
  if not next(s.c) then return end
  local hh = EC.hours(C)
  local hr = hh % 24
  if not (hr >= CFGP.echo_h0 or hr < CFGP.echo_h1) then return end
  local nk = math.floor((hh - CFGP.echo_h1) / 24)   -- 20:00 дня d и 03:00 дня d+1 — одна ночь
  if s.nk ~= nk then s.nk, s.nn = nk, 0 end
  if s.nn >= CFGP.echo_night_max or (now - EC.last < CFGP.echo_gap and now >= EC.last) then return end
  local okc = EC.check(C, now); if not okc then return end
  local px, _, pz = player_xyz(); if not px then return end
  -- место: ячейка + соседние, сумма смертей >= echo_n, место не отмечено, игрок в кольце
  local best
  for k, c in pairs(s.c) do
    local cx, cz = k:match("^(-?%d+):(-?%d+)$")
    cx, cz = tonumber(cx), tonumber(cz)
    if cx and c.x then
      local sum, used = 0, false
      for ix = cx - 1, cx + 1 do
        for iz = cz - 1, cz + 1 do
          local kk = ix .. ":" .. iz
          if s.done[kk] then used = true end
          for _, r in ipairs((s.c[kk] or {}).h or {}) do sum = sum + (r.n or 1) end
        end
      end
      local dd = dist(px, pz, c.x, c.z)
      if not used and sum >= CFGP.echo_n and dd >= CFGP.echo_rmin and dd <= CFGP.echo_rmax and (not best or sum > best.n or (sum == best.n and k < best.k)) then
        best = { k = k, x = c.x, z = c.z, n = sum, dd = dd }
      end
    end
  end
  if not best then return end
  if EC.alive(s, d, now) >= CFGP.echo_live then return end
  local sid = EC.sids[(best.n >= 2 * CFGP.echo_n and #EC.sids >= 2) and 2 or 1]
  local site = best
  EC.last = now
  local ok = T.request({ tag = "soul_echo", fid = CFGP.echo_fid, sid = sid, n = 1, size = CFGP.echo_size, from_x = site.x, from_z = site.z,
                         on_spawn = function(pls) EC.spawned(pls, site) end })
  if ok then
    s.done[site.k] = d; s.nn = s.nn + 1; EC.pend = now; stat(e, "soul_echo_req")
    dlog(string.format("soul echo request: %s at %d,%d (%d dead, player %.0f away, hour %.1f, night %d/%d)", sid, math.floor(site.x), math.floor(site.z),
         site.n, site.dd, hr, s.nn, CFGP.echo_night_max))
  else
    EC.last = now - CFGP.echo_gap + 60   -- Traces отказал (лимиты/буря): повтор через минуту
    stat(e, "soul_echo_busy")
  end
end
M.ec = EC

local LASTT = -1000
local function tick()
  if is_off() then return end
  local now = os.clock()
  if now - LASTT < CFGP.tick_gap then return end
  LASTT = now
  local ok, err = pcall(function()
    local C = C_(); if not (C and C.state and C.state() and C.day and C.road_state) then return end
    local e = slot(C); if not e then return end
    local d = C.day()
    local di = math.floor(d)
    if e.last < 0 then e.last = di end
    if di > e.last then
      local from = (di - e.last > 3) and di or e.last + 1
      for day = from, di do step_day(C, e, day) end
      e.last = di
    elseif di < e.last then e.last = di end
    smell_subscribe(C)
    if next(SM.src) then smell_age(C) end
    if not live(SQ, "tick_off") then   -- Y4: снять истёкшие наряды и наряды из сейва; ошибка ставит на паузу только наряды (записи остаются в сейве)
      local oks, es = pcall(SQ.tick, C)
      if not oks then
        local p = down(SQ, "tick_off", "KMM_Predators.squadjob_tick", es); down(SQ, "off", "KMM_Predators.squadjob", es)
        dlog("squadjob FAIL (tick): " .. tostring(es) .. " -> squad jobs " .. (p and ("paused " .. p .. " s") or "off until restart"))
      end
    end
    visible(C, e)
    if not live(EC, "off") then   -- S1: ошибка ставит на паузу только эхо
      local oke, ee = pcall(EC.step, C, e)
      if not oke then wlog("soul echo", down(EC, "off", "KMM_Predators.echo", ee), ee) end
    end
  end)
  if not ok then off(err) else h_ok("KMM_Predators.module") end
end
M.tick = tick
M.step = function(day) local C = C_(); local e = C and slot(C); if e then step_day(C, e, day or C.day()) end end   -- офлайн-тест
M.slot = function() local C = C_(); return C and slot(C) end
M.disabled = function() return RETIRED or DISABLED end
M.retired = RETIRED
M.rt = RT

if RETIRED then DISABLED = true; dlog("predators: retired (2026-11-16) - module off, vanilla predators only") end
if not RETIRED and rawget(_G, "Events") and Events.on and not STARTED then
  STARTED = true
  Events.on("GameWorld::charsUpdate", guarded("predators", function(...) tick() end))
end
KMM_Predators = M

-- PUBLISH (2026-11-16): KenshiLua runs each init script in its own sandbox; a plain global stays inside it.
if KMM_Predators ~= nil then rawset(_G, "KMM_Predators", KMM_Predators) end
