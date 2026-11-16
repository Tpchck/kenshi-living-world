-- KMM_Probe (2026-11-15): самопроверка модулей в игре. СТРОГО только чтение.
-- Отдельных тестовых прогонов игры нет: начало каждой его сессии становится тестом. Через start_s секунд после того, как у игрока
-- появились персонажи (загрузка сейва или новая игра), модуль один раз проверяет вызовы движка, на которых стоят механики
-- сборки, и пишет по строке на пробу в logs/probe.log:
--   <дата время> PROBE <имя> ok|fail|absent <значение или причина>
--   <дата время> PROBE summary ok=N fail=M absent=K pass=P ms=<сумма> slow=<имя>:<мс>
-- Через repeat_s секунд второй проход — только пробы с warm (зависят от прогрева: окно сообщений, модель дирижёра, зоны,
-- самоотключения модулей). Дальше молчит до следующей загрузки (PlayerInterface::loadFromSerialise).
-- Что нельзя: спавн, createItem, addItem, addMessage, say, setRelation, запись полей движка, запись в сейв. Только чтение
-- и наличие методов (addMessage, addItem, addSmell — проверяется, что метод есть, сам он не вызывается).
-- Каждая проба под своим pcall: ошибка одной -> её строка «fail», остальные идут. Пробы идут порциями по кадрам
-- (per_frame штук или frame_ms мс на кадр), запись в лог — одна на кадр.
-- Крэш-сторож (pcall не ловит нативный краш): перед пробой с вызовами движка имя пишется в state/probe_kmmprobe.lock, после —
-- lock удаляется. Lock при старте = прошлая сессия упала в этой пробе -> state/probe_kmmprobe_<имя>.off, проба пропускается
-- навсегда (строка fail с причиной; удалить .off — проба снова включится). В сейв модуль ничего не пишет.
-- Разбор: tools/session_report.py, раздел «Самопроверка» (fail/absent, сравнение с прошлой сессией).

local P = {
  cfg = {
    start_s = 20,        -- сек реального времени после появления персонажей игрока до первого прохода
    repeat_s = 300,      -- сек после первого прохода до второго (warm)
    check_s = 1,         -- как часто в ожидании смотреть, есть ли персонажи игрока
    per_frame = 2,       -- проб за кадр не больше
    frame_ms = 3,        -- и не дольше (после первой пробы кадра)
    max_pcs = 8,         -- персонажей игрока на пробу
    max_items = 40,      -- вещей на пробу цены
    scan_r = 3000,       -- радиус скана зданий (руда, руины), как у KMM_Ore
    scan_max = 80,
    list_cap = 5000,     -- предел счёта getCharacterUpdateList
    log = "C:/KenshiModMap/logs/probe.log",
    sdir = "C:/KenshiModMap/state/",
  },
  phase = "wait", pass = 0, t_chk = -1e9, t_seen = nil, t_next = nil, q = nil, qi = 1,
  res = {}, cnt = nil, buf = {}, offc = {}, lock_checked = false, dead = false, loads = 0, scan = nil, ms = 0, slow = nil,
}

local function clean(s)
  s = string.gsub(tostring(s), "[\r\n\t]", " ")
  if #s > 220 then s = s:sub(1, 217) .. "..." end
  return s
end
local function stamp() return os.date("%Y-%m-%d %H:%M:%S") end
function P.flush()
  if #P.buf == 0 then return end
  local lines = table.concat(P.buf, "\n") .. "\n"
  P.buf = {}
  pcall(function()
    local fh = io.open(P.cfg.log, "a")
    if fh then fh:write(lines); fh:close() end
  end)
end
function P.emit(name, st, val)
  P.buf[#P.buf + 1] = stamp() .. " PROBE " .. name .. " " .. st .. " " .. clean(val)
end
local function guarded(nm, fn)
  return function(...)
    if P.dead then return end
    local ok, err = pcall(fn, ...)
    if not ok then
      P.dead = true
      P.emit("internal", "fail", nm .. ": " .. tostring(err) .. " -> probe module off until restart")
      P.flush()
    end
  end
end

---------------------------------------------------------------------------------------------- помощники чтения
-- живые персонажи игрока (свежий список на каждую пробу: указатели между кадрами не храним)
local function pcs(max)
  local out = {}
  for _, c in pairs(getPlayerInterface():getAllPlayerCharacters()) do
    if #out >= (max or P.cfg.max_pcs) then break end
    local okd, dead = pcall(function() return c:isDead() end)
    if okd and dead == false then out[#out + 1] = c end
  end
  return out
end
local function first_pc() return pcs(1)[1] end
local function xyz(c)
  local p = c:getPosition()
  return { x = p.x, y = p.y, z = p.z }
end
local function mod(name) local m = rawget(_G, name); return type(m) == "table" and m or nil end
local function num(v) return type(v) == "number" and v or nil end

-- скан зданий у персонажа игрока (один на проход; хранятся только числа и строки, буфер очищается сразу)
function P.do_scan()
  if P.scan and P.scan.pass == P.pass then return P.scan end
  local lk = rawget(_G, "lektor")
  if not (lk and lk.new) then P.scan = { pass = P.pass, absent = "no lektor in _G (getObjectsWithinSphere needs a lektor buffer)" }; return P.scan end
  local pc = first_pc()
  if not pc then P.scan = { pass = P.pass, absent = "no player character" }; return P.scan end
  if not P.lbuf then P.lbuf = lk.new("RootObject*") end   -- один буфер на сессию (ContainersReference)
  local S = { pass = P.pass, n = 0, prod = 0, mining = 0, tpl = {}, fac = 0, nofac = 0, cont = 0, cont_free = 0, shops = 0, errs = 0 }
  local buf = P.lbuf
  buf:clear()
  local ok, err = pcall(function()
    -- 6 аргументов, как KMM_Ore/KMM_RelicRace: первый — выходной буфер, в BindingsReference пропущен (ledger 2.1 п.9, ✓игра)
    getGameWorld():getObjectsWithinSphere(buf, pc:getPosition(), P.cfg.scan_r, 0, P.cfg.scan_max, nil)   -- 0 = itemType.BUILDING
    for _, o in ipairs(buf) do
      local okb, b = pcall(function() return o:getHandle():getBuilding() end)
      if okb and b then
        S.n = S.n + 1
        local okp, pb = pcall(function() return b:getProductionBuilding() end)
        if okp and pb then
          S.prod = S.prod + 1
          local okl, lv = pcall(function() return pb._resourceMiningLevel end)   -- поле, только чтение
          if okl and num(lv) and lv > 0 then
            S.mining = S.mining + 1
            if #S.tpl < 3 then
              local okg, sid = pcall(function() return b:getGameData().stringID end)
              if okg and type(sid) == "string" then S.tpl[#S.tpl + 1] = sid end
            end
          end
        end
        local okf, hf = pcall(function() return b:hasFaction() end)
        if okf and hf == true then S.fac = S.fac + 1 elseif okf and hf == false then S.nofac = S.nofac + 1 else S.errs = S.errs + 1 end
        local oks, shop = pcall(function() return b:isAShop() end)
        if oks and shop == true then S.shops = S.shops + 1 end
        local oki, cont = pcall(function() local inv = b:getInventory(); return inv and inv:isAContainer() end)
        if oki and cont == true and not (oks and shop == true) then
          S.cont = S.cont + 1
          if okf and hf == false then S.cont_free = S.cont_free + 1 end
        end
      end
    end
  end)
  buf:clear()
  if not ok then S.err = tostring(err) end
  P.scan = S
  return S
end

---------------------------------------------------------------------------------------------- пробы
-- { имя, функция -> (ok|fail|absent, значение), warm = второй проход тоже, lock = крэш-сторож (вызовы движка) }
local PROBES = {}
local function add(name, fn, warm, lock) PROBES[#PROBES + 1] = { name = name, fn = fn, warm = warm and true or false, lock = lock ~= false } end

-- все механики: список персонажей игрока (getAllPlayerCharacters, isDead, getName)
add("players", function()
  local n, alive, nm = 0, 0, nil
  for _, c in pairs(getPlayerInterface():getAllPlayerCharacters()) do
    n = n + 1
    if n <= P.cfg.max_pcs then
      local okd, dead = pcall(function() return c:isDead() end)
      if okd and dead == false then
        alive = alive + 1
        if not nm then local okn, s = pcall(function() return c:getName() end); nm = okn and s or nil end
      end
    end
  end
  if n == 0 then return "fail", "getAllPlayerCharacters() is empty" end
  return "ok", string.format("n=%d alive=%d first=%s", n, alive, tostring(nm))
end)

-- Nemesis.worth / contempt / Traces ворота «нищий»: деньги ядра (Character:getMoney, запас Ownerships платуна)
add("money", function()
  local pc = first_pc()
  if not pc then return "absent", "no live player character" end
  local okc, cm = pcall(function() return pc:getMoney() end)
  local okp, pm = pcall(function() return pc:getPlatoon().me:getOwnerships():getMoney() end)
  local own = (okp and num(pm)) and tostring(pm) or ("n/a: " .. tostring(pm))
  if okc and num(cm) then return "ok", string.format("money=%d via=Character:getMoney ownerships=%s", cm, own) end
  if okp and num(pm) then return "ok", string.format("money=%d via=Ownerships (Character:getMoney: %s)", pm, tostring(cm)) end
  return "fail", "Character:getMoney: " .. tostring(cm) .. "; Ownerships:getMoney: " .. tostring(pm)
end)

-- Nemesis.worth: цена вещей своих (InventoryItemBase:getValueAll, запас getValueSingle x quantity)
add("item_value", function()
  local n, all, single, sum, err = 0, 0, 0, 0, nil
  for _, pc in ipairs(pcs()) do
    if n >= P.cfg.max_items then break end
    local ok, e = pcall(function()
      for _, it in ipairs(pc:getInventory():getAllItems()) do
        if n >= P.cfg.max_items then break end
        n = n + 1
        local okv, v = pcall(function() return it:getValueAll(false) end)
        if okv and num(v) then all = all + 1; sum = sum + v
        else
          err = err or tostring(v)
          local oks, s = pcall(function() return it:getValueSingle(false) * (tonumber(it.quantity) or 1) end)
          if oks and num(s) then single = single + 1; sum = sum + s end
        end
      end
    end)
    if not ok then err = err or tostring(e) end
  end
  if n == 0 then return err and "fail" or "absent", err and ("inventory unreadable: " .. err) or "no items on player characters" end
  local txt = string.format("items=%d getValueAll=%d getValueSingle=%d gear=%d", n, all, single, math.floor(sum))
  if all == n then return "ok", txt end
  if all + single == n then return "ok", txt .. " (fallback single: " .. tostring(err) .. ")" end
  return "fail", txt .. " unread=" .. (n - all - single) .. ": " .. tostring(err)
end)

-- сам Nemesis.worth (то, что видят contempt, Traces и Predators)
add("nemesis_worth", function()
  local NM = mod("KMM_Nemesis")
  if not (NM and type(NM.worth) == "function") then return "absent", "KMM_Nemesis.worth missing" end
  local C = mod("KMM_Conductor")
  local S = C and C.state and C.state()
  -- worth() читает прозвище из слота Nemesis в модели дирижёра и создаёт слот, если его нет: до первого такта Nemesis не зовём
  if not (type(S) == "table" and type(S.ext) == "table" and S.ext.nemesis ~= nil) then return "absent", "Nemesis state slot not created yet" end
  local W = NM.worth()
  if type(W) ~= "table" then return "fail", "worth() returned nil (error inside N.worth)" end
  if W.money == nil then return "fail", "money unread: " .. tostring(W.txt) end
  return "ok", tostring(W.txt)
end, true)

-- хроника Nemesis и журнал Rumors: ManagementScreen.getSingleton() и наличие addMessage (сам addMessage не вызывается)
add("management_screen", function()
  local MS = rawget(_G, "ManagementScreen")
  if MS == nil then return "absent", "no ManagementScreen class in _G" end
  local ms = MS.getSingleton()
  if not ms then return "fail", "ManagementScreen.getSingleton() = nil (window not created)" end
  local am = ms.addMessage
  local col = rawget(_G, "MessageLogColor")
  local okc, c0 = pcall(function() return col and col.ML_NORMAL end)
  if am == nil then return "fail", "singleton ok, addMessage missing" end
  return "ok", "singleton ok, addMessage=" .. type(am) .. " MessageLogColor=" .. ((okc and c0 ~= nil) and "yes" or "no")
end, true)

-- Nemesis обратная память «кто тебя уложил»: поле Character.lastGuyWhoDefeatedMe (hand) -> getCharacter
add("defeated_by", function()
  local read, set, who, err = 0, 0, nil, nil
  for _, pc in ipairs(pcs()) do
    local okw, hd = pcall(function() return pc.lastGuyWhoDefeatedMe end)
    local werr = (not okw) and hd or nil   -- при ошибке pcall здесь текст ошибки, а не hand
    if okw then
      read = read + 1
      if hd ~= nil then
        local okn, isn = pcall(function() return hd:isNull() end)
        if okn and isn == false then
          set = set + 1
          if not who then
            local okc, nm = pcall(function() local ch = hd:getCharacter(); return ch and ch:getName() end)
            who = okc and nm or nil
          end
        elseif not okn then err = err or tostring(isn) end
      end
    else err = err or tostring(werr) end
  end
  if read == 0 then return err and "fail" or "absent", err or "no live player character" end
  return "ok", string.format("read=%d set=%d who=%s%s", read, set, tostring(who or "-"), err and (" note: " .. err) or "")
end)

-- голод: Outlaws (вес кражи голодным), Nemesis (лёг от голода), Self: MedicalSystem isReallyHungry/isHungerKO/hunger
add("medical", function()
  local n, hungry, hko, hmin, miss = 0, 0, 0, nil, {}
  for _, pc in ipairs(pcs()) do
    local okm, med = pcall(function() return pc:getMedical() end)
    if okm and med then
      n = n + 1
      local ok1, v1 = pcall(function() return med:isReallyHungry() end)
      if ok1 and type(v1) == "boolean" then if v1 then hungry = hungry + 1 end else miss.isReallyHungry = tostring(v1) end
      local ok2, v2 = pcall(function() return med:isHungerKO() end)
      if ok2 and type(v2) == "boolean" then if v2 then hko = hko + 1 end else miss.isHungerKO = tostring(v2) end
      local ok3, v3 = pcall(function() return med.hunger end)
      if ok3 and num(v3) then hmin = math.min(hmin or v3, v3) else miss.hunger = tostring(v3) end
    else miss.getMedical = tostring(med) end
  end
  local keys = {}
  for k, v in pairs(miss) do keys[#keys + 1] = k .. "(" .. v .. ")" end
  table.sort(keys)
  if n == 0 then return next(miss) and "fail" or "absent", next(miss) and table.concat(keys, " ") or "no live player character" end
  local txt = string.format("n=%d reallyHungry=%d hungerKO=%d hunger_min=%s", n, hungry, hko, hmin and string.format("%.0f", hmin) or "?")
  if #keys > 0 then return "fail", txt .. " unread: " .. table.concat(keys, " ") end
  return "ok", txt
end)

-- Self/Gov/Town/Nemesis: Character:isInCombatMode(melee, ranged)
add("combat_mode", function()
  local n, inc, err = 0, 0, nil
  for _, pc in ipairs(pcs()) do
    local ok, v = pcall(function() return pc:isInCombatMode(true, true) end)
    if ok and v ~= nil then n = n + 1; if v then inc = inc + 1 end else err = err or tostring(v) end
  end
  if n == 0 then return err and "fail" or "absent", err or "no live player character" end
  return "ok", string.format("n=%d in_combat=%d", n, inc)
end)

-- Traces/Sync/Outlaws спавн: шаблон отряда KMM_Traces.tier_pick -> gamedata:getData(sid, SQUAD_TEMPLATE); createRandomSquad НЕ зовётся
add("squad_template", function()
  local T, C = mod("KMM_Traces"), mod("KMM_Conductor")
  if not (T and type(T.tier_pick) == "function") then return "absent", "KMM_Traces.tier_pick missing" end
  local S = C and C.state and C.state()
  if type(S) ~= "table" or type(S.F) ~= "table" then return "absent", "conductor state not loaded" end
  local ids = {}
  for fid, f in pairs(S.F) do if type(f) == "table" and f.alive and not f.player then ids[#ids + 1] = tostring(fid) end end
  table.sort(ids)
  local ts = type(T.tier_stats) == "function" and T.tier_stats() or nil
  local p0 = type(ts) == "table" and ts.picks or nil
  local picked = {}
  for _, fid in ipairs(ids) do
    if #picked >= 3 then break end
    local oks, sid, tier = pcall(T.tier_pick, fid, 0)
    if oks and type(sid) == "string" and sid ~= "" then picked[#picked + 1] = { fid, sid, tostring(tier) } end
  end
  if p0 then ts.picks = p0 end   -- счётчик выборов Traces пробой не сдвигается
  if #picked == 0 then return "fail", "tier_pick gave no squad sid for " .. #ids .. " live factions" end
  local gd0 = getGameWorld().gamedata
  local good, bad = {}, {}
  for _, e in ipairs(picked) do
    local okd, gd = pcall(function() return gd0:getData(e[2], 52) end)   -- 52 = itemType.SQUAD_TEMPLATE (как Traces)
    if okd and gd ~= nil then good[#good + 1] = e[1] .. ":" .. e[3] .. ":" .. e[2]
    else bad[#bad + 1] = e[1] .. ":" .. e[2] .. (okd and "=nil" or ("=" .. tostring(gd))) end
  end
  if #bad > 0 then return "fail", "getData(sid, 52) nil -> createRandomSquad would get nil #6: " .. table.concat(bad, ",") .. (#good > 0 and (" ok: " .. table.concat(good, ",")) or "") end
  return "ok", "templates found: " .. table.concat(good, ",")
end, true)

-- Gov снимок, Nemesis/RelicRace «главарь ещё жив»: getCharacterUpdateList и :has (без разыменования)
add("update_list", function()
  local set = getGameWorld():getCharacterUpdateList()
  if set == nil then return "fail", "getCharacterUpdateList() = nil" end
  local n = 0
  for _ in pairs(set) do n = n + 1; if n >= P.cfg.list_cap then break end end
  local pc = first_pc()
  if not pc then return "ok", string.format("n=%d has=not checked (no live player character)", n) end
  local okh, has = pcall(function() return set:has(pc) end)
  if not okh then return "fail", string.format("n=%d has(): %s", n, tostring(has)) end
  if has ~= true then return "fail", string.format("n=%d has(player)=%s (expected true)", n, tostring(has)) end
  return "ok", string.format("n=%d has(player)=true", n)
end, true)

-- Nemesis.worth, Traces охотники за наградой: Character.crimes (BountyManager) getTotalBounty, _getHighestBountyFaction
add("bounty", function()
  local n, total, hi, err = 0, 0, nil, nil
  for _, pc in ipairs(pcs()) do
    local okb, b = pcall(function() local bm = pc.crimes; return bm:getTotalBounty() end)
    if okb and num(b) then
      n = n + 1; total = total + b
      if b > 0 and not hi then
        local okf, fid = pcall(function()
          local bm = pc.crimes
          local hf = bm:_getHighestBountyFaction()
          local gd = hf and (hf.data or hf:getData())
          return gd and gd.stringID
        end)
        hi = okf and fid or ("? " .. tostring(fid))
      end
    else err = err or tostring(b) end
  end
  if n == 0 then return err and "fail" or "absent", err or "no live player character" end
  return "ok", string.format("n=%d total=%d highest=%s", n, total, tostring(hi or "-"))
end)

-- все модули: игровое время getTimeStamp_inGameHours():getTotalDays()
add("game_time", function()
  local tod = getGameWorld():getTimeStamp_inGameHours()
  local d = tod:getTotalDays()
  if not num(d) then return "fail", "getTotalDays() = " .. type(d) end
  return "ok", string.format("days=%.2f", d)
end)

-- модель дирижёра поднята из сейва/новой игры
add("world_model", function()
  local C = mod("KMM_Conductor")
  if not (C and C.state) then return "absent", "KMM_Conductor missing" end
  local S = C.state()
  if type(S) ~= "table" or type(S.F) ~= "table" then return "fail", "KMM_Conductor.state() not loaded" end
  local n, alive = 0, 0
  for _, f in pairs(S.F) do n = n + 1; if type(f) == "table" and f.alive then alive = alive + 1 end end
  return "ok", string.format("factions=%d alive=%d day=%s events=%d", n, alive, tostring(C.day and C.day() or S.last_day), #(S.events or {}))
end, true, false)

-- KMM_Ore: что видит движок — производственные здания с _resourceMiningLevel у персонажа игрока (без записи)
add("ore_nodes", function()
  local S = P.do_scan()
  if S.absent then return "absent", S.absent end
  if S.err then return "fail", "getObjectsWithinSphere scan: " .. S.err end
  return "ok", string.format("buildings=%d production=%d mining=%d tpl=%s r=%d", S.n, S.prod, S.mining, #S.tpl > 0 and table.concat(S.tpl, ",") or "-", P.cfg.scan_r)
end, true)

-- статус модуля руды (его файлы ведёт отдельный поток: только чтение KMM_Ore.status под pcall)
add("ore_module", function()
  local O = mod("KMM_Ore")
  if not O then return "absent", "KMM_Ore not loaded" end
  if type(O.status) ~= "function" then return "absent", "KMM_Ore.status missing" end
  return "ok", tostring(O.status())
end, true, false)

-- RelicRace разбор руин («free containers 0, owned 123»): здания у игрока с фракцией/без, контейнеры не-лавки
add("ruin_containers", function()
  local S = P.do_scan()
  if S.absent then return "absent", S.absent end
  if S.err then return "fail", "getObjectsWithinSphere scan: " .. S.err end
  return "ok", string.format("buildings=%d faction=%d no_faction=%d containers=%d free_containers=%d shops=%d%s", S.n, S.fac, S.nofac, S.cont, S.cont_free, S.shops,
    S.errs > 0 and (" hasFaction_err=" .. S.errs) or "")
end, true)

-- Predators/Herds запах: GameWorld.zoneMgr:getZoneMap(точка игрока) -> ZoneMap.zoneSmell, getGeneralSmellLevel; addSmell — только наличие
add("smell", function()
  local pc = first_pc()
  if not pc then return "absent", "no live player character" end
  local zmgr = getGameWorld().zoneMgr
  if zmgr == nil then return "fail", "GameWorld.zoneMgr = nil" end
  local p = xyz(pc)
  local zm = zmgr:getZoneMap(p)
  if zm == nil then
    local okl, ld = pcall(function() return zmgr:isZoneLoadedT(p) end)
    return "fail", "getZoneMap(player pos) = nil, zone loaded=" .. (okl and tostring(ld) or "?")
  end
  local zs = zm.zoneSmell
  if zs == nil then return "fail", "ZoneMap.zoneSmell = nil at the player" end
  local st = rawget(_G, "SmellType")
  local okt, ty = pcall(function() return st and st.SMELL_BLOOD_AND_CORPSES end)
  local okv, lv = pcall(function() return zs:getGeneralSmellLevel((okt and ty) or 1) end)
  local has_add = zs.addSmell ~= nil
  local txt = string.format("zoneSmell ok addSmell=%s level=%s", has_add and "yes" or "MISSING", (okv and num(lv)) and string.format("%.2f", lv) or ("? " .. tostring(lv)))
  if not has_add then return "fail", txt end
  return "ok", txt
end, true)

-- KMM_Town ремесло/носильщики («carrier addItem failed»): API инвентаря и фабрики есть (ничего не вызывается)
add("carrier_api", function()
  local pc = first_pc()
  if not pc then return "absent", "no live player character" end
  local inv = pc:getInventory()
  if inv == nil then return "fail", "Character:getInventory() = nil" end
  local miss = {}
  for _, k in ipairs({ "addItem", "tryAddItem", "getItem", "removeItemDontDestroy_returnsItem", "getAllItems" }) do
    local okk, v = pcall(function() return inv[k] end)
    if not (okk and v ~= nil) then miss[#miss + 1] = "Inventory." .. k end
  end
  local okf, cf = pcall(function() local fa = getGameWorld().theFactory; return fa and fa.createItem end)
  if not (okf and cf ~= nil) then miss[#miss + 1] = "theFactory.createItem" end
  local TW = mod("KMM_Town")
  local tst = ""
  if TW and type(TW.status) == "function" then local oks, s = pcall(TW.status); tst = " town: " .. (oks and tostring(s) or ("status error " .. tostring(s))) end
  if #miss > 0 then return "fail", "missing " .. table.concat(miss, ",") .. tst end
  return "ok", "Inventory addItem/tryAddItem/getItem/removeItemDontDestroy_returnsItem present, createItem present (not called)" .. tst
end, true)

-- журнал дирижёра за последние сутки игры и сколько из них ушло в слухи (KMM_Rumors: say/merged)
add("journal", function()
  local C = mod("KMM_Conductor")
  local S = C and C.state and C.state()
  if type(S) ~= "table" then return "absent", "conductor state not loaded" end
  local day = num(C.day and C.day()) or num(S.last_day) or 0
  local R = mod("KMM_Rumors")
  local idx
  if R and type(R.fn) == "table" and type(R.fn.told) == "function" then local okt, t = pcall(R.fn.told); idx = okt and type(t) == "table" and t or nil end
  local n, told, all = 0, 0, 0
  for _, ev in ipairs(S.events or {}) do
    all = all + 1
    if type(ev) == "table" and num(ev.day) and ev.day >= day - 1 then
      n = n + 1
      local v = idx and idx[tostring(ev.id)]
      if v == "say" or v == "merged" then told = told + 1 end
    end
  end
  local jn = (R and type(R.vstat) == "table") and R.vstat.journal or nil
  return "ok", string.format("day=%.1f events_24h=%d rumored=%s total=%d rumors_journal=%s", day, n, idx and tostring(told) or "n/a (no KMM_Rumors)", all, tostring(jn or "n/a"))
end, true, false)

-- реестр здоровья механик ядра (KMM_Gov.health_list: пауза/повтор вместо «выкл до перезапуска»): сколько механик, какие не ok и почему
add("health_registry", function()
  local G = mod("KMM_Gov")
  if not (G and type(G.health_list) == "function") then return "absent", "KMM_Gov.health_list missing (no health registry)" end
  local list = G.health_list()
  if type(list) ~= "table" then return "fail", "health_list() returned " .. type(list) end
  local n, cnt, bad = 0, { ok = 0, pause = 0, retry = 0, off = 0 }, {}
  for _, r in ipairs(list) do
    if type(r) == "table" then
      n = n + 1
      local s = tostring(r.state)
      cnt[s] = (cnt[s] or 0) + 1
      if s ~= "ok" and #bad < 6 then
        bad[#bad + 1] = string.format("%s=%s(%s, fails=%s): %s", tostring(r.key), s, tostring(r.reason or "-"), tostring(r.total or r.fails or 0), clean(r.err or "-"):sub(1, 60))
      end
    end
  end
  local txt = string.format("mechanics=%d ok=%d pause=%d retry=%d off=%d", n, cnt.ok, cnt.pause, cnt.retry, cnt.off)
  if cnt.off > 0 or cnt.pause > 0 then return "fail", txt .. " | " .. table.concat(bad, "; ") end
  if #bad > 0 then return "ok", txt .. " | " .. table.concat(bad, "; ") end
  return "ok", txt
end, true, false)

-- живы ли модули: глобал, disabled(), флаги *off* (самоотключение ошибкой), причина, если модуль её хранит
local MODS = { "KMM_Conductor", "KMM_Gov", "KMM_Traces", "KMM_Self", "KMM_Nemesis", "KMM_Outlaws", "KMM_Fates", "KMM_Deeds", "KMM_Predators",
               "KMM_Herds", "KMM_RelicRace", "KMM_RecruitRace", "KMM_Siege", "KMM_Veterans", "KMM_Rumors", "KMM_Diplo", "KMM_Town",
               "KMM_Stock", "KMM_Tempo", "KMM_Elite", "KMM_Native", "KMM_Ore" }
local function off_flags(m)
  local out, seen = {}, {}
  local function put(s) if not seen[s] then seen[s] = true; out[#out + 1] = s end end
  if type(m.disabled) == "function" then
    local d = m.disabled()
    if type(d) == "table" then
      for k, v in pairs(d) do if v then put(tostring(k) .. (type(v) == "string" and ("(" .. v .. ")") or "")) end end
    elseif d == true then put("disabled")
    elseif type(d) == "string" and d ~= "" then put("disabled(" .. d .. ")") end
  elseif m.disabled == true then put("disabled") end
  for _, inner in ipairs({ m, rawget(m, "_M"), rawget(m, "_N"), rawget(m, "_D") }) do
    if type(inner) == "table" then
      for k, v in pairs(inner) do
        if type(k) == "string" and v == true and (k == "off" or k:sub(-4) == "_off" or k:sub(-3) == "Off") then put(k) end
        if type(k) == "string" and k == "last_err" and type(v) == "string" then put("last_err(" .. v .. ")") end
      end
    end
  end
  table.sort(out)
  return out
end
for _, name in ipairs(MODS) do
  add("mod_" .. name:gsub("^KMM_", ""), function()
    local m = rawget(_G, name)
    if m == nil then return "absent", "not loaded (no global " .. name .. ")" end
    if type(m) ~= "table" then return "fail", "global " .. name .. " is " .. type(m) end
    if rawget(m, "retired") == true then return "ok", "retired by design" end
    local off = off_flags(m)
    if #off > 0 then return "fail", "self-disabled: " .. table.concat(off, ",") end
    return "ok", "loaded, nothing disabled"
  end, true, false)
end

---------------------------------------------------------------------------------------------- крэш-сторож
local function lock_path() return P.cfg.sdir .. "probe_kmmprobe.lock" end
local function off_path(name) return P.cfg.sdir .. "probe_kmmprobe_" .. name .. ".off" end
function P.check_lock()   -- один раз за сессию: lock от прошлой сессии = она упала в этой пробе
  if P.lock_checked then return end
  P.lock_checked = true
  pcall(function()
    local fh = io.open(lock_path(), "r")
    if not fh then return end
    local name = (fh:read("*l") or ""):match("^%s*([%w_]+)") or "?"
    fh:close()
    local o = io.open(off_path(name), "w")
    if o then o:write("disabled: previous session crashed during probe ", name); o:close() end
    os.remove(lock_path())
    P.offc[name] = true
  end)
end
function P.is_off(name)
  local v = P.offc[name]
  if v == nil then
    v = false
    pcall(function() local fh = io.open(off_path(name), "r"); if fh then fh:close(); v = true end end)
    P.offc[name] = v
  end
  return v
end

---------------------------------------------------------------------------------------------- исполнение
function P.run_one(pr)
  if pr.lock and P.is_off(pr.name) then
    P.emit(pr.name, "fail", "skipped: the game crashed during this probe in an earlier session (state/probe_kmmprobe_" .. pr.name .. ".off; delete it to retry)")
    P.cnt.fail = P.cnt.fail + 1; P.res[pr.name] = "fail"
    return
  end
  if pr.lock then pcall(function() local fh = io.open(lock_path(), "w"); if fh then fh:write(pr.name); fh:close() end end) end
  local t0 = os.clock()
  local ok, st, val = pcall(pr.fn)
  local dt = (os.clock() - t0) * 1000
  if pr.lock then pcall(os.remove, lock_path()) end
  if not ok then st, val = "fail", "error: " .. tostring(st)
  elseif st ~= "ok" and st ~= "fail" and st ~= "absent" then st, val = "fail", "probe returned " .. tostring(st) end
  if val == nil then val = "-" end
  P.emit(pr.name, st, val)
  P.cnt[st] = P.cnt[st] + 1
  P.res[pr.name] = st
  P.ms = P.ms + dt
  if not P.slow or dt > P.slow[2] then P.slow = { pr.name, dt } end
end
function P.start_pass(n)
  P.check_lock()
  P.pass = n
  P.q, P.qi = {}, 1
  for _, pr in ipairs(PROBES) do if n == 1 or pr.warm then P.q[#P.q + 1] = pr end end
  P.cnt = { ok = 0, fail = 0, absent = 0 }
  P.ms, P.slow, P.scan = 0, nil, nil
  P.phase = "run"
end
function P.step()   -- порция проб на этот кадр
  local t0 = os.clock()
  local k = 0
  while P.qi <= #P.q do
    P.run_one(P.q[P.qi])
    P.qi = P.qi + 1
    k = k + 1
    if k >= P.cfg.per_frame or (os.clock() - t0) * 1000 >= P.cfg.frame_ms then break end
  end
  if P.qi > #P.q then
    P.buf[#P.buf + 1] = string.format("%s PROBE summary ok=%d fail=%d absent=%d pass=%d ms=%.1f slow=%s", stamp(), P.cnt.ok, P.cnt.fail, P.cnt.absent,
      P.pass, P.ms, P.slow and string.format("%s:%.1f", P.slow[1], P.slow[2]) or "-")
    P.q = nil
    if P.pass == 1 then P.phase, P.t_next = "between", os.clock() + P.cfg.repeat_s else P.phase = "done" end
  end
  P.flush()
end
function P.tick()
  local ph = P.phase
  if ph == "done" then return end
  if ph == "run" then return P.step() end
  local now = os.clock()
  if ph == "between" then
    if now >= P.t_next then P.start_pass(2); P.step() end
    return
  end
  if ph == "wait" then
    if now - P.t_chk < P.cfg.check_s then return end
    P.t_chk = now
    local okp, pc = pcall(first_pc)
    if okp and pc then P.phase, P.t_seen = "delay", now end
    return
  end
  if ph == "delay" and now - P.t_seen >= P.cfg.start_s then P.start_pass(1); P.step() end
end
function P.on_load()   -- загрузка сейва: заново ждать персонажей, два прохода
  P.loads = P.loads + 1
  P.phase, P.pass, P.q, P.t_chk, P.t_seen, P.t_next, P.scan, P.buf = "wait", 0, nil, -1e9, nil, nil, nil, {}
end

KMM_Probe = {
  cfg = function() return P.cfg end,
  results = function() return P.res end,          -- имя -> ok|fail|absent (последний проход)
  phase = function() return P.phase, P.pass end,
  names = function() local o = {}; for i, pr in ipairs(PROBES) do o[i] = pr.name end; return o end,
  disabled = function() return P.dead and { probe = true } or {} end,
  _P = P,
  _probes = PROBES,
}

if rawget(_G, "Events") and Events.on then
  Events.on("GameWorld::charsUpdate", guarded("tick", function() P.tick() end))
  Events.on("PlayerInterface::loadFromSerialise", guarded("load", function() P.on_load() end))
end

-- PUBLISH (2026-11-16): KenshiLua runs each init script in its own sandbox; a plain global stays inside it.
if KMM_Probe ~= nil then rawset(_G, "KMM_Probe", KMM_Probe) end
