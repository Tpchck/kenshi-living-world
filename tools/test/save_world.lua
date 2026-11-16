-- save_world.lua: мир-заглушка движка Kenshi/KenshiLua из НАСТОЯЩЕГО сейва (данные: глобальная WORLD, её кладёт save_replay.py).
-- Грузится после STUBS-подготовки в save_replay.py. Любое обращение к неизвестному полю заглушки пишется в UNKNOWN[класс.ключ][файл:строка].
-- ВЫДУМАНО (в сейве нет, помечено «INV»): деньги отрядов, unique, торговцы, голод по ходу времени, ход игрока, здания, рабочие, отношения фракций, город персонажа.
-- ИЗ СЕЙВА: имя, фракция (sid), раса, пол, позиция, голод/кровь/смерть/КО (MEDICAL_STATE), инвентарь (INVENTORY_ITEM_STATE: section, base data sid), отряд (имя файла), лидер.
UNKNOWN, CALLS = {}, {}
local function where(level)
  local i = debug.getinfo(level or 3, "Sl")
  return i and (tostring(i.short_src):gsub("^.*[/\\]build[/\\]", "") .. ":" .. tostring(i.currentline)) or "?"
end
local function note_unknown(cls, key)
  if type(key) ~= "string" then return end
  local w = where(4)
  if not (w:find("KMM_", 1, true) or w:find("kmm_", 1, true)) then return end
  local k = cls .. "." .. key
  local t = UNKNOWN[k]; if not t then t = {}; UNKNOWN[k] = t end
  t[w] = (t[w] or 0) + 1
end
-- класс: методы в таблице; чужое поле/метод -> лог. REFM (множество имён методов из BindingsReference) -> безвредный no-op (игра метод имеет, заглушка нет)
local function class(name, methods)
  methods.__index = nil
  return setmetatable({}, { __index = function(_, k) return methods[k] end }), methods
end
local function obj(cls, methods, fields)
  local o = fields or {}
  setmetatable(o, { __index = function(t, k)
    local m = methods[k]; if m ~= nil then return m end
    note_unknown(cls, k)
    if REFM and REFM[k] then return function() return nil end end
    return nil
  end, __name = cls })
  return o
end

-- ENGINE_LIST: userdata, pairs/ipairs/# работают, next() нет (как в KenshiLua)
do
  local rp, ri = pairs, ipairs
  pairs = function(t) local mt = type(t) == "userdata" and getmetatable(t); if mt and mt.__pairs then return mt.__pairs(t) end; return rp(t) end
  ipairs = function(t) local mt = type(t) == "userdata" and getmetatable(t); if mt and mt.__ipairs then return mt.__ipairs(t) end; return ri(t) end
  function ENGINE_LIST(t)
    local u = newproxy(true); local mt = getmetatable(u)
    mt.__index = function(_, k) return t[k] end
    mt.__len = function() return #t end
    mt.__pairs = function() return rp(t) end
    mt.__ipairs = function() return ri(t) end
    return u, t
  end
end
KMM_TEST = true
local real_open = io.open
io.open = function(p, m) p = tostring(p):gsub("^C:/KenshiModMap/logs/", TMP .. "/"):gsub("^C:/KenshiModMap/state/", TMP .. "/"); return real_open(p, m) end
local __rr = os.remove; os.remove = function(p) p = tostring(p):gsub("^C:/KenshiModMap/state/", TMP .. "/"); return __rr(p) end
LOGS = {}
KenshiLua = { log = function(s) LOGS[#LOGS + 1] = s end }
Events = { h = {} }
function Events.on(n, f) Events.h[n] = Events.h[n] or {}; table.insert(Events.h[n], f); return n .. "#" .. #Events.h[n] end
function Events.off(id) end
EVENT_ERRORS = {}
function FIRE(n, ...)
  for _, f in ipairs(Events.h[n] or {}) do
    local ok, err = xpcall(f, debug.traceback, ...)
    if not ok then EVENT_ERRORS[#EVENT_ERRORS + 1] = tostring(err) end
  end
end
CLOCK, DAYV, FRAME = 0, 800.0, 0     -- DAYV: игровые сутки (INV: 800 - выше порога Elite min_years*360; реальный день из сейва не читаем)
os.clock = function() return CLOCK end
-- lektor.new("RootObject*"): буфер-контейнер движка (userdata)
lektor = { new = function()
  local u, t = ENGINE_LIST({})
  local mt = getmetatable(u)
  local fill = {}
  mt.__index = function(_, k)
    if k == "clear" then return function() for i = #t, 1, -1 do t[i] = nil end end end
    if k == "push_back" then return function(_, v) t[#t + 1] = v end end
    if type(k) == "number" then return t[k] end
    note_unknown("lektor", k); return nil
  end
  u_t = t; LEKTOR = LEKTOR or {}; LEKTOR[u] = t
  return u
end }

------------------------------------------------------------------ данные мира
local CHARS, PCS, PLAT, FACS, TOWNS, TOWN_LIST, BUILDINGS = {}, {}, {}, {}, {}, {}, {}
local WORLDDAYS_START = DAYV
SETREL, RUNAWAY, SPAWNS, CREATED, FAIL_SPAWN = 0, 0, {}, 0, false
local stats = { declared_dead = 0, added = 0, removed = 0, msgs = 0, spawn_calls = 0 }
WSTATS = stats

local Faction_m = {}
function FAC(id)
  if not FACS[id] then
    local f = { id = id }
    f.rel = {}
    local rl = {}
    function rl:setRelation(o, v) SETREL = SETREL + 1; f.rel[o.id] = v end
    function rl:getFactionRelation(o) return f.rel[o.id] or 0 end
    f.relations = obj("FactionRelations", rl)
    f.data = { stringID = id, name = (WORLD.fnames or {})[id] or id }
    local wm = {}
    function wm:getNearestTown(p)
      local best, bd
      for _, t in ipairs(TOWN_LIST) do local d = (t.x - p.x) ^ 2 + (t.z - p.z) ^ 2; if not bd or d < bd then best, bd = t, d end end
      return best and best.obj
    end
    function wm:triggerCampaign() end
    f.warMgr = obj("FactionWarMgr", wm)
    FACS[id] = obj("Faction", {
      getData = function() return f.data end, getName = function() return f.data.name end,
      getFactionRelation = nil }, nil)
    -- у Faction нет getGameData (как в игре) — поэтому методы кладём вручную
    local F = FACS[id]
    rawset(F, "id", id); rawset(F, "relations", f.relations); rawset(F, "data", f.data); rawset(F, "warMgr", f.warMgr)
  end
  return FACS[id]
end

-- города из конфигурации дирижёра (позиции реальные, из town_info)
for _, t in ipairs(WORLD.towns or {}) do
  local rec = { sid = t.sid, x = t.x, z = t.z, name = t.name }
  local gd = { stringID = t.sid, name = t.name }
  local T
  T = obj("Town", {
    getName = function() return t.name end, getPosition = function() return { x = t.x, y = 0, z = t.z } end,
    getData = function() return gd end, getGameData = function() return gd end, getOriginalGameData = function() return gd end,
    isTown = function() return T end, data = gd,
  })
  rawset(T, "data", gd)
  rec.obj = T
  TOWNS[t.sid] = rec; TOWN_LIST[#TOWN_LIST + 1] = rec
end
local function nearest_town(x, z, maxd)
  local best, bd
  for _, t in ipairs(TOWN_LIST) do local d = (t.x - x) ^ 2 + (t.z - z) ^ 2; if not bd or d < bd then best, bd = t, d end end
  if best and bd <= (maxd or 1500) ^ 2 then return best end
end

-- предметы / инвентарь
local ITEMSEC = { main = false, backpack_attach = false }
local function mkitem(sid, qty, sec)
  local it
  it = obj("Item", {
    getGameData = function() return it.data end,
    getValueSingle = function() return 100 end,
    isFood = function() return false end,
    getName = function() return sid end,
  }, { quantity = qty or 1, isEquipped = (ITEMSEC[sec or "main"] ~= false) and sec ~= nil and sec ~= "main", section = sec })
  rawset(it, "data", { stringID = sid })
  return it
end
local function mkinv(owner, items, cap)
  local inv = { items = items or {} }
  local function dolist() return ENGINE_LIST(inv.items) end
  local m = {}
  function m:getAllItems() return (dolist()) end
  function m:getNumItems() return #inv.items end
  function m:hasRoomForItem() return #inv.items < (cap or 60) end
  function m:addItem(it, q, a, b) if #inv.items >= (cap or 60) and not (a == false) then return false end; inv.items[#inv.items + 1] = it; stats.added = stats.added + 1; return true end
  function m:tryAddItem(it, q) if #inv.items >= (cap or 60) then return false end; inv.items[#inv.items + 1] = it; stats.added = stats.added + 1; return true end
  function m:getItem(gd) for _, it in ipairs(inv.items) do if it.data == gd or (gd and it.data.stringID == gd.stringID) then return it end end; return nil end
  function m:removeItemAutoDestroy(it, n) for i, x in ipairs(inv.items) do if x == it then table.remove(inv.items, i); stats.removed = stats.removed + 1; return true end end; return false end
  function m:removeItemDontDestroy_returnsItem(it, n, c) for i, x in ipairs(inv.items) do if x == it then table.remove(inv.items, i); stats.removed = stats.removed + 1; return x end end; return nil end
  function m:equipItem() return true end
  function m:getTotalWeight() return #inv.items * 1.5 end
  function m:isAContainer() return true end
  return obj("Inventory", m, { _items = inv.items })
end

-- отряд: ActivePlatoon (getPlatoon()) с .me = Platoon
local function mkplat(key, fid, trader)
  if PLAT[key] then return PLAT[key] end
  local p = { key = key, speedOverride = 1, priceMultWhenITrade = 1.0, squadTemplate = { stringID = "tpl_" .. key } }
  local me = obj("Platoon", {
    getPlatoonStringID = function() return key end,
    getBlackboard = function() return obj("Blackboard", { runAway = function() RUNAWAY = RUNAWAY + 1 end }) end,   -- INV: движок AIs не моделируем
    getSquadLeader = function() return p.leader end,
    getOwnerships = function() return obj("Ownerships", { _homeTown = TOWN_LIST[1] and TOWN_LIST[1].obj, getMoney = function() return p.money end,
      addMoney = function(_, v) p.money = p.money + v end, setMoney = function(_, v) p.money = v end }) end,   -- setMoney: BindingsReference Ownerships (✓игра: TILL lowered 15.11)
  }, p)
  local ap = obj("ActivePlatoon", { getIsTrader = function() return trader end }, { me = me, isPlayer = false })
  rawset(ap, "me", me)
  p.money = 1500 + (#key * 37) % 3500   -- INV
  p.ap = ap
  PLAT[key] = ap
  return ap
end

local function mkchar(rec, idx)
  local c = { dead = rec.dead or false, rec = rec, x = rec.x, y = rec.y, z = rec.z, hunger = (rec.hung or 3.0) * 100, blood = rec.blood or 100,
              ko = rec.ko or 0, player = rec.player or false, items = {}, chained = false }
  local ap = mkplat(rec.plat, rec.f, rec.trader)
  if rec.player then ap.isPlayer = true; rawset(ap, "isPlayer", true) end
  c.ap = ap
  local inv = mkinv(c, c.items, 400)
  for _, it in ipairs(rec.items or {}) do c.items[#c.items + 1] = mkitem(it[1], it[3], it[2]) end
  local med
  local m = {}
  med = obj("MedicalSystem", { pointOfNoReturn = function() return 40 end,
    getMovementSpeedInjuryMultiplier = function() return 1.0 end }, { hunger = c.hunger, blood = c.blood, knockoutTimer = c.ko, unconcious = false })
  local stt = obj("CharStats", { calculateHungerMult = function() return 1.0 end }, { moveSpeed = 10.0 })
  local own = obj("Ownerships", { getMoney = function() return c.money or 300 end, addMoney = function(_, v) c.money = (c.money or 300) + v end,
                                   setMoney = function(_, v) c.money = v end })   -- без setMoney REFM давал тихий no-op: Tempo видел «запись не применилась»
  c.med = med
  local race = obj("RaceData", {}, { robot = (rec.racen or ""):lower():find("bot") ~= nil, data = { stringID = rec.race, name = rec.racen or rec.race } })   -- как в справочнике: RaceData.data/.robot, без name/getName
  local self
  local M = {
    getName = function() return rec.n end,
    getFaction = function() return FAC(rec.f) end,
    getPosition = function() return { x = c.x, y = c.y, z = c.z } end,
    isPlayerCharacter = function() return c.player end,
    isUnique = function() return rec.unique or false end,
    isDead = function() return c.dead end,
    isDown = function() return c.ko > 0 end,
    isUnconcious = function() return c.ko > 0 end,
    isInCombatMode = function() return c.combat or false end,
    say = function() return true end,
    getHandle = function() return c.handle end,
    declareDead = function() c.dead = true; stats.declared_dead = stats.declared_dead + 1 end,
    setChainedMode = function(_, on) c.chained = on end,
    isChained = function() return c.chained end,
    getPlatoon = function() return c.ap end,
    getGameData = function() return { stringID = "char_" .. tostring(rec.i) } end,
    getInventory = function() return inv end,
    getCurrentTownLocation = function() local t = nearest_town(c.x, c.z, 900); return t and t.obj or nil end,   -- INV: ближайший город <900
    getStats = function() return stt end,
    getMedical = function() return med end,
    getRace = function() return race end,
    getMagicHungerSetting = function() return 1.0 end,
    getOwnerships = function() return own end,
    isAnimal = function() return rec.animal or false end,
    getMovementSpeed = function() return 10 end,
    getMovementSpeedOrders = function() return 1 end,
    amSomeoneWhoNeedsToEatToLive = function() return true end,
    isSlave = function() return 0 end,
    getMySlaveOwner = function() return nil end,
    getNumFoodItems = function() return 0 end,
    eatItem = function() return false end,
    getCarryingObject = function() local h = { null = false }; function h:setNull() self.null = true end; function h:isNull() return self.null end; return h end,
    isATrader = function() return rec.trader or false end,
    isResident = function() return rec.resident or false end,
    getBody = function() return c.body end,
    uniqueStateUpdate = function() end,
    lineOfSightCheck = function() return true end,
    attackTarget = function() end,
  }
  self = obj("Character", M)
  c.handle = obj("hand", { toString = function() return "h" .. rec.i end, getBuilding = function() return nil end, isValid = function() return not c.dead end },
                 {})
  setmetatable(c.handle, getmetatable(c.handle)); rawset(c.handle, "__id", rec.i)
  -- tostring(handle) в Gov: как в игре - строка
  getmetatable(c.handle).__tostring = function() return "h" .. rec.i end
  c.obj = self
  rawset(self, "medical", med)
  rawset(self, "_c", c)
  return self
end

local PLAYER_CHARS
local function build_world()
  for i, rec in ipairs(WORLD.chars) do
    rec.i = i
    local ch = mkchar(rec, i)
    CHARS[#CHARS + 1] = ch
    if rec.player then PCS[#PCS + 1] = ch end
  end
  PLAYER_CHARS = PCS
end
build_world()

------------------------------------------------------------------ здания (INV): в каждом городе лавка + склад; шахта у первого персонажа игрока; мастерские
local function mkbuilding(tsid, kind, x, z, fid, inv_items)
  local T = TOWNS[tsid]
  local inv = mkinv(nil, inv_items or {}, 40)
  local b
  local hd = obj("hand", { toString = function() return "b_" .. kind .. "_" .. tsid end, isValid = function() return true end, getBuilding = function() return b end })
  b = obj("Building", {
    isAShop = function() return kind == "shop" end, getInventory = function() return inv end, hasFaction = function() return fid ~= nil end,
    getFaction = function() return fid and FAC(fid) end, getTown = function() return T and T.obj end,
    getHandle = function() return hd end, getPosition = function() return { x = x, y = 0, z = z } end,
    getGameData = function() return { stringID = "bld_" .. kind } end, getName = function() return kind end,
    isAContainer = function() return true end,
  })
  rawset(hd, "_b", b)
  BUILDINGS[#BUILDINGS + 1] = { b = b, x = x, z = z }
  return b
end
local fid_of_town = {}
if WORLD.town_fid then fid_of_town = WORLD.town_fid end
for _, t in ipairs(TOWN_LIST) do
  local f = fid_of_town[t.sid]
  local shop_items = {}
  for k = 1, 6 do shop_items[#shop_items + 1] = mkitem(((WORLD.shop_items or {})[(k + #t.sid) % math.max(1, #(WORLD.shop_items or {})) + 1]) or "135-gastronom.mod", 1, "main") end
  mkbuilding(t.sid, "shop", t.x + 30, t.z, f, shop_items)
  mkbuilding(t.sid, "storage", t.x - 30, t.z, f, {})
end

-- рабочие места: действие персонажа (task) -> subject handle -> building -> production building (INV)
local function workplace(tpl, x, z, tsid)
  local pb
  local hb
  pb = obj("ProductionBuilding", {
    getGameData = function() return { stringID = tpl } end, getPosition = function() return { x = x, y = 0, z = z } end,
    getName = function() return pb._name end, setName = function(_, n) pb._name = n end,
    getInventory = function() return mkinv(nil, {}, 40) end, getTown = function() return TOWNS[tsid] and TOWNS[tsid].obj end,
  }, { _name = "Workplace", _resourceMiningLevel = 10.0 })
  hb = obj("Building", { getProductionBuilding = function() return pb end, getGameData = function() return { stringID = tpl } end,
    getInventory = function() return mkinv(nil, {}, 40) end, getPosition = function() return { x = x, y = 0, z = z } end })
  local subj = obj("hand", { isValid = function() return true end, getBuilding = function() return hb end, toString = function() return "w_" .. tpl end })
  return subj
end
function ASSIGN_WORK(ch, tpl, key, tsid)
  local c = ch._c
  local x, z = c.x, c.z
  local subj = workplace(tpl, x + 20, z, tsid)
  local act = obj("Action", { key = function() return key end }, { subject = subj })
  c.body = obj("Body", { getCurrentAction = function() return act end })
end

------------------------------------------------------------------ глобальные функции движка
local function recompute_loaded(radius)
  local px, pz
  for _, p in ipairs(PCS) do local c = p._c; if not c.dead then px, pz = c.x, c.z; break end end
  LOADED = {}
  local r2 = radius * radius
  for _, ch in ipairs(CHARS) do
    local c = ch._c
    if not c.dead and (c.player or (px and (c.x - px) ^ 2 + (c.z - pz) ^ 2 <= r2)) then LOADED[#LOADED + 1] = ch end
  end
  LOADED_SET = {}
  for _, ch in ipairs(LOADED) do LOADED_SET[ch] = true end
end
LOADED, LOADED_SET = {}, {}
RECOMPUTE = recompute_loaded

function getPlayerInterface()
  return obj("PlayerInterface", {
    getAllPlayerCharacters = function() local live = {}; for _, p in ipairs(PCS) do if not p._c.dead then live[#live + 1] = p end end; return (ENGINE_LIST(live)) end,
    getOwnerships = function() return obj("Ownerships", { getMoney = function() return 12000 end, addMoney = function() end, setMoney = function() end }) end,
  })
end

local TIME = obj("TimeOfDay", { getTotalDays = function() return DAYV end, getTotalHours = function() return DAYV * 24 end })
local GW
local gdcache = {}
GW = obj("GameWorld", {
  getCharacterUpdateList = function() local s = {}; for ch in pairs(LOADED_SET) do if not ch._c.dead then s[ch] = true end end; return s end,   -- как в test_runtime: таблица ключей
  getTimeStamp_inGameHours = function() return TIME end,
  getTimeStamp = function() return FRAME end,     -- INV: число-метка кадра (в игре тип не подтверждён)
  showPlayerAMessage_withLog = function() stats.msgs = stats.msgs + 1 end,
  getObjectsWithinSphere = function(self, buf, pos, r, ty, maxn, ex)
    local t = LEKTOR[buf]
    local n = 0
    for _, B in ipairs(BUILDINGS) do
      if (B.x - pos.x) ^ 2 + (B.z - pos.z) ^ 2 <= r * r then n = n + 1; if maxn and n > maxn then break end; t[#t + 1] = B.b:getHandle() and B.b end
    end
  end,
  setGameSpeed = function() end,
}, { })
rawset(GW, "factionMgr", obj("FactionManager", { getFactionByStringID = function(_, id) return FAC(id) end,
  getAllFactions = function() local l = {}; for id in pairs(FACS) do l[#l + 1] = FACS[id] end; return (ENGINE_LIST(l)) end }))
rawset(GW, "gamedata", obj("GameData", { getData = function(_, sid, ty) if not gdcache[sid] then gdcache[sid] = { stringID = sid, t = ty } end; return gdcache[sid] end }))
rawset(GW, "theFactory", obj("Factory", {
  createItem = function(_, gd) CREATED = CREATED + 1; return mkitem(gd and gd.stringID or "?", 1, "main") end,
  createRandomSquad = function(self, f, pos, home, maxnum, b, gd, o, m, ap, perm, target, ttown, mult, sqtype, refresh)
    stats.spawn_calls = stats.spawn_calls + 1
    if FAIL_SPAWN then error("engine refused squad") end
    -- как в игре (лог 2026-11-15): шаблон отряда squad: GameData nil не принимает (#6 при вызове через ':'), число maxnum по значению тоже
    if gd == nil then error("bad argument #6 to 'createRandomSquad' (KenshiLua.GameData expected, got nil)") end
    if type(gd) ~= "table" and type(gd) ~= "userdata" then error("bad argument #6 to 'createRandomSquad' (KenshiLua.GameData expected, got " .. type(gd) .. ")") end
    if type(maxnum) ~= "number" then error("bad argument #4 to 'createRandomSquad' (number expected, got " .. type(maxnum) .. ")") end
    if target == nil then error("bad argument #12 to 'spawn' (KenshiLua.hand expected, got nil)") end
    if type(mult) ~= "number" then error("bad argument #14 (number expected)") end
    if type(sqtype) ~= "number" then error("bad argument #15 to 'spawn' (number expected, got nil)") end
    if type(pos) ~= "table" or not pos.x then error("bad pos") end
    SPAWNS[#SPAWNS + 1] = { fid = f and f.id, x = pos.x, z = pos.z, n = maxnum }
    return { spawned = true }
  end }))
function getGameWorld() return GW end

------------------------------------------------------------------ симулятор времени (INV: игрок идёт по городам, NPC стоят, голод падает)
CHARS_PUB, PCS_PUB, nearest_town_pub, TOWN_LIST_PUB = CHARS, PCS, nearest_town, TOWN_LIST
REAL_CLOCK = REAL_CLOCK or nil
local route, ri, SPEED = {}, 1, 2500
function PLAN_ROUTE()
  local p = PCS[1]; if not p then return end
  local x, z = p._c.x, p._c.z
  local left = {}
  for _, t in ipairs(TOWN_LIST) do   -- только города с заселённой округой (иначе игрок уходит в пустоту: loaded=1)
    local n = 0
    for _, ch in ipairs(CHARS) do local c = ch._c; if (c.x - t.x) ^ 2 + (c.z - t.z) ^ 2 <= LOAD_RADIUS ^ 2 then n = n + 1 end end
    if n >= 80 then left[#left + 1] = t end
  end
  if #left == 0 then for _, t in ipairs(TOWN_LIST) do left[#left + 1] = t end end
  while #left > 0 do
    local bi, bd
    for i, t in ipairs(left) do local d = (t.x - x) ^ 2 + (t.z - z) ^ 2; if not bd or d < bd then bi, bd = i, d end end
    local t = table.remove(left, bi); route[#route + 1] = t; x, z = t.x, t.z
  end
end
HUNGER_RATE = 20       -- INV: единиц hunger/сутки у загруженных NPC
LOAD_RADIUS = 7000
function SIM(ticks, dt, dday)
  for _ = 1, ticks do
    CLOCK = CLOCK + dt; DAYV = DAYV + dday; FRAME = FRAME + 1
    if FRAME % 30 == 1 then
      local p = PCS[1]
      if p and not p._c.dead and route[ri] then
        local c, t = p._c, route[ri]
        local dx, dz = t.x - c.x, t.z - c.z
        local d = math.sqrt(dx * dx + dz * dz)
        local step = SPEED * dday * 30
        if d <= step then c.x, c.z = t.x, t.z; ri = ri % #route + 1 else c.x, c.z = c.x + dx / d * step, c.z + dz / d * step end
        for _, q in ipairs(PCS) do q._c.x, q._c.z = c.x, c.z end
        PLAYER_STEPS = (PLAYER_STEPS or 0) + 1
        if ORE_REASSIGN then ORE_REASSIGN(p) end
      end
      RECOMPUTE(LOAD_RADIUS)
      -- INV: стычки рядом с игроком (бой, часть отряда лежит) - для самосохранения/следов; раз в ~4 игровых часа, на ~2 часа
      if COMBAT and FRAME >= COMBAT.untilf then for _, ch in ipairs(COMBAT.list) do ch._c.combat = false; ch._c.ko = 0 end; COMBAT = nil end
      if not COMBAT and FRAME % 120 == 1 and p then
        local byp = {}
        for _, ch in ipairs(LOADED) do local c = ch._c
          if not c.player and not c.dead and (c.x - p._c.x) ^ 2 + (c.z - p._c.z) ^ 2 <= 3500 ^ 2 then byp[c.rec.plat] = byp[c.rec.plat] or {}; table.insert(byp[c.rec.plat], ch) end end
        for _, l in pairs(byp) do
          if #l >= 3 then
            COMBAT = { list = l, untilf = FRAME + 60 }
            for i, ch in ipairs(l) do ch._c.combat = true; if i > 1 then ch._c.ko = 30 end end
            COMBATS = (COMBATS or 0) + 1
            break
          end
        end
      end
      for _, ch in ipairs(LOADED) do local c = ch._c; if not c.player then c.med.hunger = math.max(0, c.med.hunger - HUNGER_RATE * dday * 30) end end
    end
    FIRE("GameWorld::charsUpdate", {})
  end
end
-- размер таблиц, достижимых из KMM_* (для поиска роста): число записей, обход с лимитом
function DEEPSIZE(root, cap)
  local seen, n = {}, 0
  local function walk(t, d)
    if seen[t] or n > cap or d > 6 then return end
    seen[t] = true
    for k, v in next, t do
      n = n + 1
      if type(v) == "table" then walk(v, d + 1) end
    end
  end
  if type(root) == "table" then walk(root, 0) end
  return n
end
