-- KMM_Conductor_Runtime: part of KMM_Conductor (world conductor), run by KC._BOOT in KMM_Conductor.lua
-- Часть дирижёра мира (KMM_Conductor.lua собирает части и регистрирует события). 1-я строка ASCII: имя чанка в тестах.
-- Здесь: STORY (акты мира), test_mode, безотказность (guarded, debug.log), такт on_tick, удар on_hit, PERSIST (PST).
-- Код части выполняется не при загрузке файла, а в KC._BOOT() в порядке KC._PARTS (как шёл бы единый файл),
-- когда загружены все части — порядок загрузки файлов KenshiLua не важен.
local KC = rawget(_G, "KMM_C_INT")   -- общее пространство имён частей дирижёра (бывшие локали главного чанка: KC.<имя>)
if type(KC) ~= "table" then KC = { _SEG = {} }; _G.KMM_C_INT = KC end
if KC._booted then KC._SEG, KC._booted = {}, false end   -- повторная загрузка скриптов: собрать части заново
KC._SEG.Runtime = function()
---------------------------------------------------------------------------------------------- STORY (акты мира «Сумерки реликтов»)
-- Раз в игровой день: метрики мира -> текущий акт (переходы из params.story) -> параметры дирижёра = база x множители акта.
-- Без новых сущностей, без спавнов, без записи world state. Состояние акта - S.story (в сейве дирижёра). Ошибка: база восстанавливается,
-- блок отключается до перезапуска. Слух: событие story_<акт> в журнал (KMM_Rumors берёт шаблон по типу). Описание: docs\STORY.md
KC.STORY = { off = false, leaves = nil, paths = nil }
function KC.story_cfg() local c = KC.P and KC.P.story; if type(c) == "table" and c.enabled ~= false and type(c.acts) == "table" and c.acts[c.start or ""] then return c end end
function KC.story_index(c)   -- листья params (числа) по путям из mods всех актов; база снимается один раз, до любых изменений
  local leaves, paths, seen = {}, {}, {}
  for _, id in ipairs(KC.sorted_keys(c.acts)) do
    for _, m in ipairs(c.acts[id].mods or {}) do
      if not paths[m[1]] then
        local lst = {}
        paths[m[1]] = lst
        local node, parts = KC.P, {}
        for k in tostring(m[1]):gmatch("[^%.]+") do parts[#parts + 1] = k end
        for i = 1, #parts - 1 do node = type(node) == "table" and node[parts[i]] or nil end
        local last = parts[#parts]
        if type(node) == "table" and last then
          local keys = (last == "*") and KC.sorted_keys(node) or { last }
          for _, k in ipairs(keys) do
            if type(node[k]) == "number" then
              seen[node] = seen[node] or {}
              local lf = seen[node][k]
              if not lf then lf = { node, k, node[k] }; seen[node][k] = lf; leaves[#leaves + 1] = lf end
              lst[#lst + 1] = lf
            end
          end
        end
      end
    end
  end
  KC.STORY.leaves, KC.STORY.paths = leaves, paths
end
function KC.story_restore() if KC.STORY.leaves then for _, l in ipairs(KC.STORY.leaves) do l[1][l[2]] = l[3] end end end
function KC.story_metrics(c)
  local m = { year = (KC.DAY or 0) / 365, ore_crisis = KC.S.ore_crisis ~= nil, ore_fracture = KC.S.ore_crisis ~= nil and KC.S.ore_crisis.phase == "fracture",
              ore_stress = KC.S.ore_stress or 0, forged = KC.S.forge ~= nil }
  local kn, kc, cs, cc, heat = 0, 0, 0, 0, 0
  for _, fid in ipairs(KC.sorted_keys(KC.S.F)) do
    local f = KC.S.F[fid]
    if f.alive and not f.player then
      if f.know and KC.ntowns(f) > 0 then kn = kn + f.know; kc = kc + 1 end
      if f.relic then cs = cs + (f.components or 100); cc = cc + 1 end
      if (f.crisis or 0) >= (c.heat_ci or 2) then heat = heat + 1 end
    end
  end
  m.know = kc > 0 and kn / kc or 0; m.comp = cc > 0 and cs / cc or 100; m.heat = heat
  return m
end
function KC.story_cond(cd, m, st, shift)
  local hk = st.hk or 1
  if cd.y_ge and not (m.year >= cd.y_ge + shift) then return false end
  if cd.y_lt and not (m.year < cd.y_lt + shift) then return false end
  if cd.act_days_ge and not (KC.DAY - st.since >= cd.act_days_ge) then return false end
  if cd.ore_crisis ~= nil and cd.ore_crisis ~= m.ore_crisis then return false end
  if cd.ore_fracture ~= nil and cd.ore_fracture ~= m.ore_fracture then return false end
  if cd.forged ~= nil and cd.forged ~= m.forged then return false end
  if cd.ore_stress_ge and not (m.ore_stress >= cd.ore_stress_ge) then return false end
  if cd.know_ge and not (m.know >= cd.know_ge) then return false end
  if cd.comp_le and not (m.comp <= cd.comp_le) then return false end
  if cd.heat_ge and not (m.heat >= cd.heat_ge * hk) then return false end
  if cd.heat_le and not (m.heat <= cd.heat_le * hk) then return false end
  return true
end
function KC.story_apply(c, st)
  KC.story_restore()
  local kk = (st.k and st.k[st.act]) or 1
  for _, m in ipairs(c.acts[st.act].mods or {}) do
    local op, v = m[2], tonumber(m[3])
    if v then
      for _, l in ipairs(KC.STORY.paths[m[1]] or {}) do
        local b = l[1][l[2]]
        if op == "mul" then l[1][l[2]] = b * (1 + (v - 1) * kk)
        elseif op == "add" then l[1][l[2]] = b + v * kk
        elseif op == "set" then l[1][l[2]] = v end
      end
    end
  end
end
function KC.story_tick_impl(day)
  local c = KC.story_cfg()
  if not c then return end
  if not KC.STORY.leaves then KC.story_index(c) end
  local st = KC.S.story
  if type(st) ~= "table" or not c.acts[st.act or ""] then
    local Z = c.seed or {}
    local sy, sk = Z.shift_years or { -0.6, 0.8 }, Z.k or { 0.75, 1.3 }
    st = { act = c.start, since = day, shift = KC.rnd(sy[1], sy[2]), hk = KC.rnd((Z.heat_k or { 0.8, 1.25 })[1], (Z.heat_k or { 0.8, 1.25 })[2]), k = {}, hist = { { c.start, math.floor(day) } } }
    for _, id in ipairs(KC.sorted_keys(c.acts)) do st.k[id] = KC.rnd(sk[1], sk[2]) end
    KC.S.story = st
  end
  if math.floor(day) <= (st.last or -1) then return end
  st.last = math.floor(day)
  local m = KC.story_metrics(c)
  st.m = { y = math.floor(m.year * 100) / 100, stress = math.floor(m.ore_stress * 100) / 100, know = math.floor(m.know * 100) / 100, comp = math.floor(m.comp), heat = m.heat }
  if day - st.since >= (c.min_act_days or 120) then
    local list = c.acts[st.act].next or {}
    if c.final and c.final.to ~= st.act and c.acts[c.final.to] then
      list = {}; for _, t in ipairs(c.acts[st.act].next or {}) do list[#list + 1] = t end
      list[#list + 1] = { to = c.final.to, any = { { y_ge = c.final.y_ge } } }
    end
    for _, tr in ipairs(list) do
      local hit, seen = false, false
      for _, h in ipairs(st.hist) do if h[1] == tr.to then seen = true end end   -- акты не повторяются
      for _, cd in ipairs(seen and {} or tr.any or {}) do if KC.story_cond(cd, m, st, st.shift or 0) then hit = true; break end end
      if hit and c.acts[tr.to] then
        st.act, st.since = tr.to, day
        st.hist[#st.hist + 1] = { tr.to, math.floor(day) }
        KC.emit({ type = "story_" .. tr.to, text = string.format("The age turns: %s.", tostring(c.acts[tr.to].name)) })
        break
      end
    end
  end
  KC.story_apply(c, st)   -- каждый день заново от базы: идемпотентно, переживает загрузку сейва
end
KC.STORY.tick = function(day)
  if KC.STORY.off then return end
  local ok, err = pcall(KC.story_tick_impl, day)
  if not ok then
    KC.STORY.off = true
    pcall(KC.story_restore)
    KC.sub_log("story disabled until restart: " .. tostring(err))
  end
end

function KC.advance(day, staged)
  if not KC.S then KC.S = KC.fresh_state() end
  KC.ensure_slots(KC.S)
  if KC.S.last_day >= 0 and day + 0.5 < KC.S.last_day then
    KC.log(string.format("game time went back (%.2f < %.2f) — new world state", day, KC.S.last_day))
    KC.S = KC.fresh_state()
  end
  KC.S.last_day = day
  if not KC.S.next_tick then KC.S.next_tick = day + KC.P.tick_days end
  if not KC.S.next_event then KC.S.next_event = day + (KC.P.first_event_after_days or KC.next_interval()) end
  if not staged and #KC.WS.q > 0 then KC.ws_pump(true) end   -- синхронный режим: сначала доделать очередь игры
  while day >= KC.S.next_tick do KC.world_step(KC.S.next_tick, staged); KC.S.next_tick = KC.S.next_tick + KC.P.tick_days end
  if staged then KC.ws_pump(false) end
  if day >= KC.S.next_event then KC.major_event(day); KC.S.next_event = day + KC.next_interval() end
  KC.DAY = day
  KC.GL.pump()   -- GOALS: порция очереди (day_chunk-стиль)
  KC.STORY.tick(day)   -- STORY: акт мира раз в игровой день (свой pcall и самоотключение)
  if KC.WSL.tick then KC.WSL.tick() end   -- LINKN: сверка владельцев городов с вариантами (внутри свой pcall и самоотключение)
end

---------------------------------------------------------------------------------------------- test_mode
-- params.test_mode = true: один раз за мир (S.test_done) рядом с игроком по очереди, раз в ~40 с реального времени,
-- вызывает все угаданные действия и пишет результат каждого pcall в C:/KenshiModMap/logs/debug.log. После теста флаг выключается.
KC.DEBUG_LOG = "C:/KenshiModMap/logs/debug.log"
function KC.dlog(msg)
  local line = string.format("%s day=%.3f %s", os.date("%Y-%m-%d %H:%M:%S"), KC.DAY or -1, tostring(msg))
  KC.append_file(KC.DEBUG_LOG, line)
  KC.log("TEST " .. tostring(msg))
end
function KC.chname(ch) local ok, n = pcall(function() return ch:getName() end); if ok and n then return tostring(n) end; return "?" end
function KC.chfid(ch)
  local ok, fid = pcall(function() local f = ch:getFaction(); local gd = f and (f:getData() or f.data); return gd and gd.stringID end)
  return ok and fid or nil
end
-- B4: хозяин оков для Character:setChainedMode(on, owner: hand) (B:3481). Порядок: 1) ближайший (<= radius) живой загруженный персонаж
-- фракции-пленителя fid — ванильно, раб принадлежит пленителю; 2) prefer (персонаж, напр. игрок в самотесте); 3) пустой hand (копия
-- getMySlaveOwner + setNull, как в Traces/Elite) — «ничей пленник» (?: поведение движка не видели); 4) прежний вариант — сам персонаж.
-- Возвращает hand и метку (captor|prefer|none|self). Поле GL, не local — лимит 200.
KC.GL.chain_owner = function(ch, fid, prefer, radius)
  local best, bd
  if fid then
    pcall(function()
      local cx, cz = KC.xz(ch:getPosition())
      for c in pairs(getGameWorld():getCharacterUpdateList()) do
        if c ~= ch then
          local okc, d = pcall(function()
            if c:isDead() or c:isPlayerCharacter() or KC.chfid(c) ~= fid then return nil end
            local x, z = KC.xz(c:getPosition())
            return math.sqrt((x - cx) ^ 2 + (z - cz) ^ 2)
          end)
          if okc and d and d <= (radius or 3000) and (not bd or d < bd) then best, bd = c, d end
        end
      end
    end)
  end
  local okh, h
  if best then okh, h = pcall(function() return best:getHandle() end); if okh and h then return h, "captor" end end
  if prefer then okh, h = pcall(function() return prefer:getHandle() end); if okh and h then return h, "prefer" end end
  okh, h = pcall(function() local x = ch:getMySlaveOwner(); x:setNull(); return x end)
  if okh and h then return h, "none" end
  return ch:getHandle(), "self"
end
-- неуникальные живые NPC не игрока рядом с первым персонажем игрока, по возрастанию расстояния
function KC.nearby_npcs(maxd)
  local pcs = KC.player_chars(); local pc
  if pcs then pcall(function() for _, c in pairs(pcs) do pc = c; break end end) end
  if not pc then return {}, nil end
  local okp, px, pz = pcall(function() return KC.xz(pc:getPosition()) end)
  if not (okp and px) then return {}, pc end
  local out = {}
  local ok, set = pcall(function() return getGameWorld():getCharacterUpdateList() end)
  if not (ok and set) then return out, pc end
  pcall(function()
    for ch in pairs(set) do
      local okc, good, d = pcall(function()
        if ch:isPlayerCharacter() or ch:isUnique() or ch:isDead() then return false end
        local fid = KC.chfid(ch)
        if not fid or fid == KC.CFG.player_faction then return false end
        local x, z = KC.xz(ch:getPosition())
        return true, math.sqrt((x - px) ^ 2 + (z - pz) ^ 2)
      end)
      if okc and good and d <= maxd then out[#out + 1] = { ch = ch, d = d } end
    end
  end)
  table.sort(out, function(a, b) return a.d < b.d end)
  return out, pc
end

KC.TEST = { step = 0, next_at = nil, used = {} }
KC.test_steps = {
  function()   -- 1. отношения двух NPC-фракций: прочитать, сдвинуть на −7, прочитать, вернуть
    local a, b
    for _, pr in ipairs(KC.CFG.pairs or {}) do if KC.faction_obj(pr[1] or pr.a) and KC.faction_obj(pr[2] or pr.b) then a, b = pr[1] or pr.a, pr[2] or pr.b; break end end
    if not a then
      local ids = {}
      for fid, f in pairs(KC.S.F) do if not f.player and KC.faction_obj(fid) then ids[#ids + 1] = fid end end
      table.sort(ids); a, b = ids[1], ids[2]
    end
    if not (a and b) then KC.dlog("1 setRelation: SKIP no faction objects (factionMgr:getFactionByStringID failed)"); return end
    local fa, fb = KC.faction_obj(a), KC.faction_obj(b)
    local ok0, v0 = pcall(function() return fa.relations:getFactionRelation(fb) end)
    local ok1, e1 = pcall(function() fa.relations:setRelation(fb, (ok0 and v0 or 0) - 7) end)
    local ok2, v2 = pcall(function() return fa.relations:getFactionRelation(fb) end)
    local ok3, e3 = pcall(function() fa.relations:setRelation(fb, ok0 and v0 or 0) end)
    KC.dlog(string.format("1 setRelation %s->%s: read0 %s=%s | set(-7) %s %s | read1 %s=%s | restore %s %s => %s",
      KC.name(a), KC.name(b), tostring(ok0), tostring(v0), tostring(ok1), ok1 and "" or tostring(e1), tostring(ok2), tostring(v2),
      tostring(ok3), ok3 and "" or tostring(e3), (ok1 and ok2 and ok0 and v2 ~= v0) and "WORKS" or "CHECK"))
  end,
  function()   -- 2. союзный отряд рядом с игроком (дружественная NPC-фракция с лучшим отношением к игроку)
    local pcs = KC.player_chars(); local pc
    if pcs then pcall(function() for _, c in pairs(pcs) do pc = c; break end end) end
    if not pc then KC.dlog("2 createRandomSquad: SKIP no player character"); return end
    local best, bv
    for fid, f in pairs(KC.S.F) do
      if not f.player and f.alive and KC.faction_obj(fid) and KC.CFG.player_faction then
        local v = KC.rel(fid, KC.CFG.player_faction)
        if not bv or v > bv then best, bv = fid, v end
      end
    end
    local fobj = best and KC.faction_obj(best)
    if not fobj then KC.dlog("2 createRandomSquad: SKIP no faction object"); return end
    local okp, p = pcall(function() return pc:getPosition() end)
    if not (okp and p) then KC.dlog("2 createRandomSquad: SKIP no player position"); return end
    local x, z = KC.xz(p)
    -- 2026-11-15 игра: «bad argument #6 to 'createRandomSquad' (KenshiLua.GameData expected, got nil)» — шаблон отряда (squad: GameData,
    -- BindingsReference RootObjectFactory) nil не принимает. Шаблон берём как Traces: tier_pick(фракция) -> gamedata:getData(sid, 52 = SQUAD_TEMPLATE);
    -- нет шаблона -> SKIP (nil движку не отдаём), отказ движка -> строка в лог, остальные пробы и модуль работают дальше.
    local T, sid = rawget(_G, "KMM_Traces"), nil
    if T and T.tier_pick then local okt, s = pcall(T.tier_pick, best, 0); if okt and type(s) == "string" then sid = s end end
    if not sid then KC.dlog("2 createRandomSquad: SKIP no squad template for " .. tostring(best) .. " (KMM_Traces.tier_pick)"); return end
    local okg, gd = pcall(function() return getGameWorld().gamedata:getData(sid, 52) end)
    if not (okg and gd) then KC.dlog("2 createRandomSquad: SKIP squad template " .. sid .. " not in gamedata (" .. tostring(gd) .. ")"); return end
    local okh, h = pcall(function() return pc:getHandle() end)
    if not (okh and h) then KC.dlog("2 createRandomSquad: SKIP no player hand"); return end
    local tries = {
      { "table +800", function() return { x = x + 800, y = p.y or 0, z = z + 800 } end },
      { "player Vector3", function() return p end },
    }
    for _, t in ipairs(tries) do
      local ok, res = pcall(function()
        return getGameWorld().theFactory:createRandomSquad(fobj, t[2](), nil, 3, nil, gd, nil, nil, nil, false, h, nil, 1.0, 2, false)
      end)
      KC.dlog(string.format("2 createRandomSquad %s (%s, rel %s, squad %s) pos=%s: ok=%s result=%s", KC.name(best), best, tostring(bv), sid, t[1], tostring(ok), tostring(res)))
      if ok then KC.S.stats.dispatch = KC.S.stats.dispatch + 1; return end
      if tostring(res):find("bad argument", 1, true) then return end   -- неверный аргумент не зависит от точки: вторая попытка даст то же
    end
  end,
  function()   -- 3. смена вещи у ближайшего неуникального NPC (без проверки «не на экране» — нужно увидеть)
    local list = KC.nearby_npcs(4000)
    if #list == 0 then KC.dlog("3 gear: SKIP no non-unique NPC within 4000"); return end
    local ch = list[1].ch
    local fid = KC.chfid(ch)
    KC.TEST.used[tostring(ch)] = true
    local pools = KC.TIERS and KC.TIERS.factions and (KC.TIERS.factions[KC.name(fid)] or select(2, next(KC.TIERS.factions)))
    local sid
    if pools then
      for _, tier in ipairs({ "T2", "T1", "T3", "T0" }) do
        for _, lst in pairs(pools[tier] or {}) do if #lst > 0 then sid = lst[math.random(#lst)]; break end end
        if sid then break end
      end
    end
    if not sid then KC.dlog("3 gear: SKIP no item pool (wardrobe_tiers.json)"); return end
    local stage = "getData"
    local ok, err = pcall(function()
      local gw = getGameWorld()
      local gd = gw.gamedata:getData(sid, 3); if not gd then error("getData returned nil for " .. sid) end
      stage = "createItem"; local item = gw.theFactory:createItem(gd, nil, nil, nil, -1, nil); if not item then error("createItem nil") end
      stage = "addItem"; local inv = ch:getInventory(); inv:addItem(item, 1, false, true)
      stage = "equipItem"; inv:equipItem(item)
    end)
    KC.dlog(string.format("3 gear %s (%s, d=%.0f) item %s: ok=%s stage=%s %s", KC.chname(ch), KC.name(fid), list[1].d, sid, tostring(ok), stage, ok and "" or tostring(err)))
    if ok then KC.S.stats.gear = KC.S.stats.gear + 1 end
  end,
  function()   -- 4. плен (setChainedMode) одного и смерть (declareDead) другого тестового неуникального NPC — не лидера
    local list = KC.nearby_npcs(4000)
    local picked = {}
    for _, e in ipairs(list) do if not KC.TEST.used[tostring(e.ch)] then picked[#picked + 1] = e end; if #picked >= 2 then break end end
    if #picked == 0 then KC.dlog("4 capture/death: SKIP no unused non-unique NPC within 4000"); return end
    local e = picked[1]
    local pc, otag = nil, "?"
    pcall(function() for _, c in pairs(KC.player_chars() or {}) do pc = c; break end end)
    KC.GL.self_chain = true   -- самотест: хозяин = персонаж игрока (ванильный путь «игрок заковал»), не сам пленник
    local ok1, err1 = pcall(function() local oh; oh, otag = KC.GL.chain_owner(e.ch, nil, pc); e.ch:setChainedMode(true, oh) end)
    KC.GL.self_chain = false
    local okq, chained = pcall(function() return e.ch:isChainedMode() end)   -- BindingsReference стр. 3392 (метода isChained() нет; есть поле isChained, стр. 3105)
    local okf, fchained = pcall(function() return e.ch.isChained end)
    KC.dlog(string.format("4a setChainedMode %s (%s, d=%.0f) owner=%s: ok=%s %s | isChainedMode %s=%s field %s=%s", KC.chname(e.ch), KC.name(KC.chfid(e.ch)), e.d,
      tostring(otag), tostring(ok1), ok1 and "" or tostring(err1), tostring(okq), tostring(chained), tostring(okf), tostring(fchained)))
    local e2 = picked[2]
    if not e2 then KC.dlog("4b declareDead: SKIP only one candidate"); return end
    local ok2, err2 = pcall(function() e2.ch:declareDead() end)
    local okd, dead = pcall(function() return e2.ch:isDead() end)
    KC.dlog(string.format("4b declareDead %s (%s, d=%.0f): ok=%s %s | isDead %s=%s", KC.chname(e2.ch), KC.name(KC.chfid(e2.ch)), e2.d, tostring(ok2),
      ok2 and "" or tostring(err2), tostring(okd), tostring(dead)))
  end,
  function()   -- 5. форсированное событие хроники (major_event) — должно попасть в chronicle.log и слухи
    local n0 = #KC.S.events
    local ok, err = pcall(function() KC.major_event(KC.DAY) end)
    local ev = KC.S.events[#KC.S.events]
    KC.dlog(string.format("5 major_event: ok=%s %s new_events=%d last=%s", tostring(ok), ok and "" or tostring(err), #KC.S.events - n0,
      ev and (ev.type .. ": " .. tostring(ev.text)) or "none"))
  end,
}
function KC.test_tick()
  if not (KC.P.test_mode and KC.S) or KC.S.test_done then return end
  local pcs = KC.player_chars()
  local has = false
  if pcs then pcall(function() for _ in pairs(pcs) do has = true; break end end) end
  if not has then return end
  local now = os.clock()
  if not KC.TEST.next_at then
    KC.TEST.next_at = now + 20
    KC.dlog(string.format("=== test_mode start (VERSION %d, %d factions) ===", KC.VERSION, KC.count(KC.S.F)))
    return
  end
  if now < KC.TEST.next_at then return end
  KC.TEST.step = KC.TEST.step + 1
  local f = KC.test_steps[KC.TEST.step]
  if not f then KC.S.test_done = true; KC.dlog("=== test_mode done ==="); return end
  local ok, err = pcall(f)
  if not ok then KC.dlog(string.format("step %d CRASHED in Lua: %s", KC.TEST.step, tostring(err))) end
  KC.TEST.next_at = now + 40
end

-- безотказность: каждая рантайм-функция в pcall; при первой ошибке отключается до конца сессии, причина → logs/debug.log
KC.DISABLED = {}
function KC.guard_log(msg)
  KC.append_file((KC.P and KC.P.guard and KC.P.guard.debug_log) or "C:/KenshiModMap/logs/debug.log", os.date("%Y-%m-%d %H:%M:%S") .. " [KMM_Conductor] " .. msg)
  KC.log(msg)
end
function KC.guarded(nm, fn)
  return function(...)
    if KC.DISABLED[nm] then return end
    local ok, err = pcall(fn, ...)
    if not ok then KC.DISABLED[nm] = true; KC.guard_log(nm .. " disabled until restart: " .. tostring(err)) end
  end
end
KC.g_sim = KC.guarded("simulation", function(day) KC.advance(day, true) end)
KC.g_test = KC.guarded("test_mode", function() KC.test_tick() end)
KC.g_rel = KC.guarded("relations", function() KC.write_relations() end)
KC.g_dispatch = KC.guarded("dispatch", function() KC.try_dispatch() end)
KC.g_scan = KC.guarded("scan_loaded", function() KC.scan_loaded() end)
KC.rng_seeded = false
KC.PST = nil   -- PERSIST: таблица ниже; объявлена здесь, чтобы on_tick видел её как upvalue
function KC.on_tick()
  if not KC.CFG then return end
  if not KC.rng_seeded then KC.rng_seeded = true; if not ((KC.CFG.params and KC.CFG.params.rng_fixed) or rawget(_G, "KMM_TEST")) then math.randomseed(os.time()) end end   -- rng_fixed: офлайн-тесты держат своё зерно   -- не на верхнем уровне (lua_lint: top_io)
  local day = KC.game_day()
  if not day then return end
  if KC.PST.want_last then pcall(KC.PST.adopt_last, day) end
  KC.g_sim(day)
  if KC.DISABLED.simulation then return end
  if KC.P.test_mode then KC.g_test() end
  if KC.P.materialize.relations_enabled then KC.g_rel() end
  KC.GL.cs_tick()   -- S2: сила/богатство/города сверяются с ядром порциями
  KC.g_dispatch()
  local now = os.clock()
  if now - KC.last_scan >= 2 then KC.last_scan = now; KC.g_scan() end
  if KC.S and KC.S.bcamp and KC.L2.camp and KC.L2.camp.base_step and now - (KC.bcamp_t or -1e9) >= ((KC.P.player_base or {}).poll_seconds or 30) then   -- U2: фаза кампании рейда на базу (одна фракция, дёшево)
    KC.bcamp_t = now; KC.xsafe("base_camp", KC.L2.camp.base_step)
  end
end

-- реальное нападение на игрока: персонажа игрока бьёт NPC фракции X (не чаще раза в сутки на фракцию) → шина + обязательства союзников
KC.last_hit = {}
function KC.duel(fid)   -- X3: удар в честном поединке (kmm_diplo) — не нападение: ни player_raid/attack_on_player, ни памяти, ни крови
  local D = fid and rawget(_G, "KMM_Diplo")
  if not (D and D.duel_active and D.duel_until) then return false end
  local ok, v, u = pcall(function() return D.duel_active(fid), D.duel_until() end)
  if not (ok and v == true and type(u) == "number") then return false end
  local now = os.clock()   -- срок сверяем сами: амнистия только до конечного срока не дальше KC.DUEL_MAX_S (Diplo мог умереть с флагом)
  return u >= now and u - now <= KC.DUEL_MAX_S
end
KC.DUEL_MAX_S = 600   -- поединок Diplo: таймаут + грабёж + пощада (~345 с по умолчанию) с запасом
function KC.on_hit(self, _, _, attacker)
  if not (KC.S and KC.CFG.player_faction and KC.S.F[KC.CFG.player_faction]) then return end
  local okp, isp = pcall(function() return self:isPlayerCharacter() end)
  if okp and not isp and attacker then
    local oka, ap = pcall(function() return attacker:isPlayerCharacter() end)
    if oka and not ap and KC.PST and KC.PST.brawl then pcall(KC.PST.brawl, self, attacker) end   -- диагностика: кто кого бьёт (NPC против NPC)
    if oka and ap then
      local okv, vf = pcall(function() local f = self:getFaction(); local gd = f and (f:getData() or f.data); return gd and gd.stringID end)
      if okv and KC.duel(vf) then return end
      local NM = rawget(_G, "KMM_Nemesis"); if NM and NM.on_player_hit then pcall(NM.on_player_hit, self, attacker) end   -- память мира об игроке
      if okv and vf and KC.S.F[vf] and vf ~= KC.CFG.player_faction then
        local day = KC.game_day() or KC.DAY
        local key = "p|" .. vf
        if not KC.last_hit[key] or day - KC.last_hit[key] >= 1 then
          KC.last_hit[key] = day; KC.DAY = day
          KC.emit({ type = "player_raid", a = KC.CFG.player_faction, b = vf, text = string.format("The Nameless fought %s.", KC.name(vf)) })
        end
      end
    end
    return
  end
  if not (okp and isp) or not attacker then return end
  local okf, fid = pcall(function() local f = attacker:getFaction(); local gd = f and (f:getData() or f.data); return gd and gd.stringID end)
  if okf and KC.duel(fid) then return end
  if okf and fid and fid ~= KC.CFG.player_faction then local NM = rawget(_G, "KMM_Nemesis"); if NM and NM.on_player_attacked then pcall(NM.on_player_attacked, fid) end end   -- должник приходит на помощь
  if not (okf and fid and KC.S.F[fid]) or fid == KC.CFG.player_faction then return end
  local day = KC.game_day() or KC.DAY
  if KC.last_hit[fid] and day - KC.last_hit[fid] < 1 then return end
  KC.last_hit[fid] = day
  KC.DAY = day
  KC.emit({ type = "attack_on_player", a = fid, b = KC.CFG.player_faction, text = string.format("%s attacked the Nameless.", KC.name(fid)) })
end

-- PERSIST (2026-11-13): в игровой сессии 21:00:40 загрузка сейва дала «no v1 state», хотя ключ в quick.save есть
-- (600 КБ, офлайн loadstring читает его без ошибок). Поэтому: (1) три способа чтения sdata + диагностика в лог;
-- (2) запасная копия в файле по имени сейва (SaveManager) — читается, если из сейва достать не удалось.
KC.PST = { DIR = "C:/KenshiModMap/state/" }   -- (local объявлен перед on_tick) одна локаль: в главном чанке предел 200 локалей Lua 5.1
function KC.PST.save_ids()
  local ids = {}
  pcall(function()
    local sm = SaveManager and SaveManager.getSingleton and SaveManager.getSingleton()
    if not sm then return end
    for _, k in ipairs({ "name", "currentGame" }) do
      local okv, v = pcall(function() return sm[k] end)
      if okv and type(v) == "string" and v ~= "" then
        local id = v:gsub("[^%w%-_ ]", "_")
        if not ids[id] then ids[#ids + 1] = id; ids[id] = k end
      end
    end
  end)
  return ids
end
function KC.PST.sdata_get(gd, key)
  local how, v = nil, nil
  local ok1, a = pcall(function() return gd.sdata[key] end)
  if ok1 and type(a) == "string" and a ~= "" then return a, "index" end
  local ok2, t = pcall(function() return gd.sdata:toTable() end)
  if ok2 and type(t) == "table" and type(t[key]) == "string" then return t[key], "toTable" end
  pcall(function() for k, x in pairs(gd.sdata) do if k == key then v = x; how = "pairs" end end end)
  if type(v) == "string" and v ~= "" then return v, how end
  local diag = { "index=" .. type(a) }
  pcall(function() diag[#diag + 1] = "gd=" .. type(gd) .. " sdata=" .. type(gd.sdata) end)
  pcall(function() diag[#diag + 1] = "size=" .. tostring(gd.sdata:size()) end)
  pcall(function() diag[#diag + 1] = "has=" .. tostring(gd.sdata:has(key)) end)
  return nil, table.concat(diag, " ")
end
-- BRAWL (2026-11-14, плейтест: в Монгреле избили Guild of Surgeons и Iron Company — кто?): драки NPC с NPC пишутся в debug.log,
-- не чаще раза в 0.5 с и раза в игровой день на пару фракций. Только лог, на мир не влияет.
KC.PST.brawl_last, KC.PST.brawl_seen = 0, {}
function KC.PST.brawl(victim, attacker)
  local now = os.clock()
  if now - KC.PST.brawl_last < 0.5 then return end
  KC.PST.brawl_last = now
  local function fid(ch) local f = ch:getFaction(); local gd = f and (f:getData() or f.data); return gd and gd.stringID, gd and gd.name end
  local vf, vn = fid(victim)
  local af, an = fid(attacker)
  if not (vf and af) or vf == af then return end
  local day = math.floor(KC.game_day() or KC.DAY or 0)
  local key = af .. ">" .. vf
  if KC.PST.brawl_seen[key] == day then return end
  KC.PST.brawl_seen[key] = day
  local okx, x, z = pcall(function() return KC.xz(victim:getPosition()) end)
  local near = "?"
  if okx and x and KC.CFG.town_info then
    local bd
    for _, t in pairs(KC.CFG.town_info) do
      if t.x then local d = (t.x - x) ^ 2 + (t.z - z) ^ 2; if not bd or d < bd then bd, near = d, t.name end end
    end
  end
  local okr, r = pcall(function() return KC.rel(af, vf) end)
  KC.sub_log(string.format("brawl: %s hit %s near %s (model rel %s)", tostring(an), tostring(vn), tostring(near), tostring(okr and r or "?")))
end
function KC.PST.fp()   -- отпечаток партии: имена персонажей игрока (отсортированы); нужен, чтобы last.kmmstate не подхватил чужую партию
  local names = {}
  pcall(function()
    local pcs = getPlayerInterface():getAllPlayerCharacters()
    for _, pc in pairs(pcs) do local ok, n = pcall(function() return pc:getName() end); if ok and type(n) == "string" then names[#names + 1] = n end end
  end)
  table.sort(names)
  return names
end
function KC.PST.fp_match(a, b)   -- совпало >= половины имён меньшего списка (наём/гибель бойцов между сейвами не мешает)
  if type(a) ~= "table" or type(b) ~= "table" or #a == 0 or #b == 0 then return false end
  local set, hit = {}, 0
  for _, n in ipairs(a) do set[n] = true end
  for _, n in ipairs(b) do if set[n] then hit = hit + 1 end end
  return hit * 2 >= math.min(#a, #b)
end
-- PERSIST-2 (2026-11-14): если ни сейв, ни файл по имени сейва не дали состояние, на первом тике с персонажами игрока
-- пробуем state/last.kmmstate (последнее сохранение): берём, только если отпечаток партии совпал и состояние не «из будущего».
function KC.PST.adopt_last(day)
  if not KC.PST.want_last then return end
  local fp = KC.PST.fp()
  if #fp == 0 then return end   -- персонажи ещё не загружены: ждём следующий тик
  KC.PST.want_last = nil
  local fs = KC.read_file(KC.PST.DIR .. "last.kmmstate")
  local v = fs and KC.deserialize(fs) or nil
  if not (v and v.version == KC.VERSION) then KC.log("last.kmmstate: none or old version — keeping new world state"); return end
  if not KC.PST.fp_match(v.fp, fp) then KC.log("last.kmmstate: other playthrough (" .. table.concat(v.fp or {}, ",") .. ") — keeping new world state"); return end
  if day and (v.last_day or -1) > day + 0.5 then KC.log(string.format("last.kmmstate is from the future (day %.1f > %.1f) — keeping new world state", v.last_day or -1, day)); return end
  KC.S = v; KC.ensure_slots(KC.S)
  KC.log(string.format("world state loaded via last-file (fingerprint %d names): %d events, %d treaties", #fp, #KC.S.events, KC.count(KC.S.treaties)))
end
function KC.PST.on_serialise(_, gameData)
  if not KC.S then return end
  local fp = KC.PST.fp(); if #fp > 0 then KC.S.fp = fp end
  local okz, str = pcall(KC.serialize, KC.S)
  if not okz then KC.log("serialise failed: " .. tostring(str)); return end
  local ok, err = pcall(function() gameData.sdata[KC.STATE_KEY] = str end)
  if not ok then KC.log("serialise into save failed: " .. tostring(err)) end
  local ids, wrote = KC.PST.save_ids(), {}
  for _, id in ipairs(ids) do
    local okf, f = pcall(io.open, KC.PST.DIR .. id .. ".kmmstate", "w")
    if okf and f then pcall(function() f:write(str) end); f:close(); wrote[#wrote + 1] = ids[id] .. "=" .. id end
  end
  local okl, fl = pcall(io.open, KC.PST.DIR .. "last.kmmstate", "w")
  if okl and fl then pcall(function() fl:write(str) end); fl:close(); wrote[#wrote + 1] = "last" end
  KC.log(string.format("state saved: %d bytes, sdata=%s, files=[%s]", #str, ok and "ok" or "fail", table.concat(wrote, ", ")))
end
function KC.PST.on_load(_, gameData)
  local s, how = KC.PST.sdata_get(gameData, KC.STATE_KEY)
  local v = s and KC.deserialize(s) or nil
  if not v then
    local diag = how
    for _, id in ipairs(KC.PST.save_ids()) do
      local fs = KC.read_file(KC.PST.DIR .. id .. ".kmmstate")
      v = fs and KC.deserialize(fs) or nil
      if v then how = "file:" .. id; break end
    end
    if not v then how = "none (" .. tostring(diag) .. ")" end
  end
  if v and v.version == KC.VERSION then KC.S = v; KC.ensure_slots(KC.S); KC.log(string.format("world state loaded via %s: %d events, %d treaties", how, #KC.S.events, KC.count(KC.S.treaties)))
  else KC.S = KC.fresh_state(); KC.PST.want_last = true; KC.log("no v1 state in this save — new world state; " .. tostring(how)) end
end
end
if KC._BOOT then KC._BOOT() end
