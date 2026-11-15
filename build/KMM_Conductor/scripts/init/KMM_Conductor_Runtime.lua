-- KMM_Conductor_Runtime: part of KMM_Conductor (world conductor), run by KC._BOOT in KMM_Conductor.lua
-- Часть дирижёра мира (KMM_Conductor.lua собирает части и регистрирует события). 1-я строка ASCII: имя чанка в тестах.
-- Здесь: STORY (акты мира), test_mode, безотказность (guarded, debug.log), такт on_tick, удар on_hit, PERSIST (PST).
-- Код части выполняется не при загрузке файла, а в KC._BOOT() в порядке KC._PARTS (как шёл бы единый файл),
-- когда загружены все части — порядок загрузки файлов KenshiLua не важен.
local KC = rawget(_G, "KMM_C_INT")   -- общее пространство имён частей дирижёра (бывшие локали главного чанка: KC.<имя>)
if type(KC) ~= "table" then KC = { _SEG = {} }; _G.KMM_C_INT = KC end
if KC._booted then KC._SEG, KC._booted = {}, false end   -- повторная загрузка скриптов: собрать части заново
KC._SEG.Runtime = function()
---------------------------------------------------------------------------------------------- STORY (обороты мира «Сумерки реликтов»)
-- Раз в игровой день: метрики мира -> фаза оборота (params.story.cycle) -> параметры дирижёра = база x множители фазы.
-- Оборот ~5 лет (4..6, от семени и пережитого): Тишина -> Охота -> кризис (Голод | Сумерки | Ночь, до двух подряд) ->
-- [Пепел после тяжёлого] -> Кузня -> снова Тишина. Финала нет. Ветви и сроки - от давления мира относительно его собственной
-- нормы (скользящие средние S.story.e), а не от абсолютных порогов: износ реликтов и рост знания не застревают через обороты;
-- прошлые обороты (S.story.cycles) гасят повтор того же кризиса и меняют восстановление. Без спавнов, без записи world state.
-- Состояние - S.story (сейв дирижёра): каждое поле читается с умолчанием (старые сейвы, будущие правки). Ошибка: база
-- восстанавливается, блок отключается до перезапуска. Слух: событие story_<фаза> в журнал (KMM_Rumors). Описание: docs\STORY.md
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
function KC.story_num(v, d) v = tonumber(v); if v == nil or v ~= v or v == math.huge or v == -math.huge then return d end; return v end
function KC.story_tab(v) if type(v) == "table" then return v end; return {} end
function KC.story_nrm(x, r)   -- линейно 0..1 на отрезке r = {a, b}, сверху до 1.5
  r = KC.story_tab(r)
  local a, b = KC.story_num(r[1], 0), KC.story_num(r[2], 1)
  return KC.clamp((x - a) / math.max(1e-6, b - a), 0, 1.5)
end
function KC.story_Y(c) return KC.story_tab(c.cycle) end
function KC.story_crises(c) local l = KC.story_Y(c).crises; if type(l) == "table" then return l end; return { "famine", "twilight", "night" } end
function KC.story_is_crisis(c, act) for _, a in ipairs(KC.story_crises(c)) do if a == act then return true end end; return false end
function KC.story_metrics(c)
  local oc = type(KC.S.ore_crisis) == "table" and KC.S.ore_crisis or nil
  local m = { year = (KC.DAY or 0) / 365, ore_crisis = KC.S.ore_crisis ~= nil, ore_fracture = oc ~= nil and oc.phase == "fracture",
              ore_stress = KC.story_num(KC.S.ore_stress, 0), ore_since = oc and KC.story_num(oc.since, nil) or nil,
              forged = KC.S.forge ~= nil, forge_day = type(KC.S.forge) == "table" and KC.story_num(KC.S.forge.day, nil) or nil }
  local kn, kc, cs, cc, heat, ns, cis = 0, 0, 0, 0, 0, 0, 0
  for _, fid in ipairs(KC.sorted_keys(KC.S.F)) do
    local f = KC.S.F[fid]
    if f.alive and not f.player then
      if f.know and KC.ntowns(f) > 0 then kn = kn + f.know; kc = kc + 1 end
      if f.relic then cs = cs + (f.components or 100); cc = cc + 1 end
      if f.crisis ~= nil then ns = ns + 1; cis = cis + KC.story_num(f.crisis, 0) end
      if (f.crisis or 0) >= (c.heat_ci or 2) then heat = heat + 1 end
    end
  end
  m.know = kc > 0 and kn / kc or 0; m.comp = cc > 0 and cs / cc or 100; m.heat = heat; m.hs = heat / math.max(1, ns); m.ci = cis / math.max(1, ns)
  return m
end
function KC.story_press(c, st, m)   -- давление ветвей (0..~2) относительно нормы мира: e = скользящие средние за ~1.5 года
  local PR, e, cur = KC.story_tab(KC.story_Y(c).pressure), KC.story_tab(st.e), KC.story_tab(st.cur)
  local F, T, N = KC.story_tab(PR.famine), KC.story_tab(PR.twilight), KC.story_tab(PR.night)
  local p = {}
  p.famine = KC.story_nrm(m.ore_stress / math.max(KC.story_num(F.floor, 0.5), KC.story_num(e.stress, m.ore_stress)), F.ratio or { 1, 1.5 })
  if m.ore_since and m.ore_since >= KC.story_num(cur.d0, math.huge) and (KC.DAY or 0) - m.ore_since <= KC.story_num(F.fresh_days, 365) then
    p.famine = p.famine + KC.story_num(F.fresh, 0.8)   -- рудный кризис начался в этом обороте
  end
  p.twilight = KC.story_nrm(KC.story_num(e.comp, m.comp) - m.comp, T.lag or { 1.5, 7 })   -- износ быстрее обычного (отставание от средней)
  local hk = KC.story_num(st.hk, 1)   -- рост «жара» над средней: число держав в кризисе и средний индекс кризиса (непрерывный)
  p.night = math.max(KC.story_nrm((m.heat - KC.story_num(e.heat, m.heat)) / hk, N.rise or { 0, 2.5 }),
                     KC.story_nrm((KC.story_num(m.ci, 0) - KC.story_num(e.ci, m.ci or 0)) / hk, N.ci_rise or { 0.05, 0.4 }))
            + KC.story_num(N.share_w, 0.3) * KC.story_nrm(m.hs or 0, N.share or { 0.15, 0.45 })
  return p
end
function KC.story_ema(c, st, m, day)
  local e = KC.story_tab(st.e); st.e = e
  local dt = math.max(0, day - KC.story_num(e.d, day))
  local a = 1 - math.exp(-dt / math.max(30, KC.story_num(KC.story_Y(c).ema_days, 540)))
  local x = { stress = m.ore_stress, comp = m.comp, heat = m.heat, know = m.know, ci = KC.story_num(m.ci, 0) }
  for _, k in ipairs({ "stress", "comp", "heat", "know", "ci" }) do
    local v = KC.story_num(e[k], nil)
    if v == nil then e[k] = x[k] else e[k] = v + (x[k] - v) * a end
  end
  e.d = day
end
function KC.story_maxp(c, p) local mx = 0; for _, a in ipairs(KC.story_crises(c)) do mx = math.max(mx, KC.story_num(p[a], 0)) end; return mx end
function KC.story_pick(c, st, p, excl)   -- ветвь кризиса: давление x шум оборота x штраф за тот же кризис в прошлых оборотах
  local Y, cur, cyc = KC.story_Y(c), KC.story_tab(st.cur), KC.story_tab(st.cycles)
  local rep = KC.story_tab(Y.repeat_penalty)
  local best, bs
  for _, br in ipairs(KC.story_crises(c)) do
    local skip = false
    for _, a in ipairs(KC.story_tab(excl)) do if a == br then skip = true end end
    if not skip and c.acts[br] then
      local s = (KC.story_num(p[br], 0) + KC.story_num(Y.pick_base, 0.2)) * KC.story_num(KC.story_tab(cur.nz)[br], 1)   -- base: при равном затишье решают шум и история
      for i = 1, #rep do
        local r = cyc[#cyc + 1 - i]
        if type(r) == "table" then for _, a in ipairs(KC.story_tab(r.cr)) do if a == br then s = s * KC.story_num(rep[i], 1); break end end end
      end
      if not bs or s > bs then best, bs = br, s end
    end
  end
  return best, bs or 0
end
function KC.story_len(c, st)   -- длина оборота в днях: years x семя кампании + след прошлого кризиса + разброс, в пределах min..max
  local Y = KC.story_Y(c)
  local y = KC.story_num(Y.years, 5) * KC.story_num(st.ck, 1)
  local cyc = KC.story_tab(st.cycles)
  local last = cyc[#cyc]
  if type(last) == "table" then for _, a in ipairs(KC.story_tab(last.cr)) do y = y + KC.story_num(KC.story_tab(KC.story_tab(Y.after)[a]).years, 0) end end
  local j = KC.story_num(Y.jitter_years, 0.35)
  y = y + KC.rnd(-j, j)
  return math.floor(365 * KC.clamp(y, KC.story_num(Y.min_years, 4), KC.story_num(Y.max_years, 6)))
end
function KC.story_mods(cur, t)   -- t = { share = {фаза = x}, k = {фаза = x} }: доли срока и сила фаз этого оборота
  t = KC.story_tab(t)
  for _, key in ipairs({ "share", "k" }) do
    local dst = (key == "share") and cur.sh or cur.kx
    for _, a in ipairs(KC.sorted_keys(KC.story_tab(t[key]))) do dst[a] = KC.story_num(dst[a], 1) * KC.story_num(t[key][a], 1) end
  end
end
function KC.story_target(c, st, act, day)   -- плановый срок фазы (дни) от длины оборота
  local Y, cur = KC.story_Y(c), st.cur
  local sh, L, mind = KC.story_tab(Y.share), KC.story_num(cur.L, 1825), KC.story_num(c.min_act_days, 120)
  if KC.story_is_crisis(c, act) then
    return math.max(mind, KC.story_num(sh.crisis, 0.34) * L * KC.story_num(cur.sh.crisis, 1) - KC.story_num(cur.cd, 0))
  end
  local nom = KC.story_num(sh[act], 0.15) * L * KC.story_num(cur.sh[act], 1)
  if act == (Y.recover or "forge") then return KC.clamp(KC.story_num(cur.d0, day) + L - day, 0.5 * nom, 2 * nom) end
  return math.max(mind, nom)
end
function KC.story_newcycle(c, st, day, m)
  local Y, old = KC.story_Y(c), st.cur
  if type(old) == "table" then
    st.cycles[#st.cycles + 1] = { n = KC.story_num(old.n, 0), d0 = math.floor(KC.story_num(old.d0, day)), len = math.floor(day - KC.story_num(old.d0, day)),
                                  path = KC.story_tab(old.path), cr = KC.story_tab(old.cr) }
    while #st.cycles > KC.story_num(Y.keep_cycles, 12) do table.remove(st.cycles, 1) end
  end
  local cur = { n = (type(old) == "table" and KC.story_num(old.n, 0) or 0) + 1, d0 = day, path = {}, cr = {}, kx = {}, sh = {}, nz = {}, cd = 0,
                b = { stress = m.ore_stress, comp = m.comp, heat = m.heat, know = m.know } }
  st.cur = cur
  cur.L = KC.story_len(c, st)
  local nz = KC.story_tab(Y.noise)
  for _, br in ipairs(KC.story_crises(c)) do cur.nz[br] = KC.rnd(KC.story_num(nz[1], 1), KC.story_num(nz[2], 1)) end
  local last = st.cycles[#st.cycles]   -- восстановление после пережитого: доли и сила фаз нового оборота
  if cur.n == 1 then KC.story_mods(cur, Y.first) end   -- первый оборот кампании: длиннее начальная тишина
  if type(last) == "table" then for _, a in ipairs(KC.story_tab(last.cr)) do KC.story_mods(cur, KC.story_tab(KC.story_tab(Y.after)[a]).next) end end
  return cur
end
function KC.story_migrate(c, st, day)   -- состояние без оборота (сейв до циклов): оборот восстанавливается из hist
  local i0 = nil
  local n = 0
  for i, h in ipairs(st.hist) do if type(h) == "table" and h[1] == c.start then i0 = i; n = n + 1 end end
  local cur = { n = math.max(1, n), d0 = KC.story_num(st.since, day), path = {}, cr = {}, kx = {}, sh = {}, nz = {}, cd = 0 }
  if i0 then
    cur.d0 = KC.story_num(st.hist[i0][2], cur.d0)
    for i = i0, #st.hist do
      local a = type(st.hist[i]) == "table" and st.hist[i][1]
      if a then cur.path[#cur.path + 1] = a; if KC.story_is_crisis(c, a) then cur.cr[#cur.cr + 1] = a end end
    end
  else cur.path[1] = st.act end
  if cur.n == 1 then KC.story_mods(cur, KC.story_Y(c).first) end   -- первый оборот кампании: длиннее начальная тишина
  return cur
end
function KC.story_state(c, day)   -- S.story: создать или дочитать (любое поле может отсутствовать или быть старого вида)
  local st = KC.S.story
  if type(st) ~= "table" then st = {}; KC.S.story = st end
  local Y, Z = KC.story_Y(c), KC.story_tab(c.seed)
  if type(st.hist) ~= "table" then st.hist = {} end
  if type(st.k) ~= "table" then st.k = {} end
  if type(st.cycles) ~= "table" then st.cycles = {} end
  local sk = KC.story_tab(Z.k)
  for _, id in ipairs(KC.sorted_keys(c.acts)) do if KC.story_num(st.k[id], nil) == nil then st.k[id] = KC.rnd(KC.story_num(sk[1], 1), KC.story_num(sk[2], 1)) end end
  if KC.story_num(st.hk, nil) == nil then local h = KC.story_tab(Z.heat_k); st.hk = KC.rnd(KC.story_num(h[1], 1), KC.story_num(h[2], 1)) end
  if KC.story_num(st.ck, nil) == nil then local q = KC.story_tab(Y.campaign_k); st.ck = KC.rnd(KC.story_num(q[1], 1), KC.story_num(q[2], 1)) end
  local n0 = nil
  if type(st.act) ~= "string" or not c.acts[st.act] then   -- нет фазы или её убрали из params: новый оборот с начала
    n0 = type(st.cur) == "table" and KC.story_num(st.cur.n, nil) or nil
    st.act, st.since, st.pt, st.cur = c.start, day, nil, nil
    st.hist[#st.hist + 1] = { c.start, math.floor(day) }
  end
  st.since = KC.story_num(st.since, day)
  if type(st.cur) ~= "table" then
    st.cur = KC.story_migrate(c, st, day)
    if n0 then st.cur.n = n0 + 1 end
  end
  local cur = st.cur
  cur.n, cur.d0, cur.cd = KC.story_num(cur.n, 1), KC.story_num(cur.d0, st.since), KC.story_num(cur.cd, 0)
  for _, k in ipairs({ "path", "cr", "kx", "sh", "nz" }) do if type(cur[k]) ~= "table" then cur[k] = {} end end
  if KC.story_num(cur.L, nil) == nil then cur.L = KC.story_len(c, st) end
  if KC.story_num(st.pt, nil) == nil then st.pt = KC.story_target(c, st, st.act, st.since) end
  return st
end
function KC.story_next(c, st, m, p, day)   -- следующая фаза или nil
  local Y, cur, act = KC.story_Y(c), st.cur, st.act
  local ad, el, pt = day - st.since, day - cur.d0, KC.story_num(st.pt, 365)
  if ad < KC.story_num(c.min_act_days, 120) then return nil end
  local rise, after, rec = Y.rise or "scramble", Y.after_act or "ashes", Y.recover or "forge"
  local Lmin, Lmax = 365 * KC.story_num(Y.min_years, 4), 365 * KC.story_num(Y.max_years, 6)
  if act == rec then   -- Кузня закрывает оборот: не раньше min_years, не позже max_years
    local FW = KC.story_tab(Y.recover_window)
    if el < Lmin then return nil end
    if el >= Lmax or ad >= KC.story_num(FW[2], 1.2) * pt then return c.start end
    if ad >= KC.story_num(FW[1], 0.85) * pt and KC.story_maxp(c, p) <= KC.story_num(Y.calm, 0.6) then return c.start end
    return nil
  end
  local fnom = KC.story_num(KC.story_tab(Y.share)[rec], 0.17) * KC.story_num(cur.L, 1825)
  if el >= Lmax - KC.story_num(Y.recover_min, 0.5) * fnom and c.acts[rec] then return rec end   -- поздно: сразу к Кузне
  local W = KC.story_tab(Y.window)
  if ad < KC.story_num(W[1], 0.6) * pt then return nil end
  local hi = ad >= KC.story_num(W[2], 1.5) * pt
  if act == c.start then
    if hi or (m.forge_day and m.forge_day >= cur.d0) or KC.story_maxp(c, p) >= KC.story_num(Y.restless, 0.6) then return rise end
  elseif act == rise then
    local best, bs = KC.story_pick(c, st, p, nil)
    if best and (hi or bs >= KC.story_num(Y.pick, 1)) then return best end
    if hi then return rec end
  elseif KC.story_is_crisis(c, act) then
    local bud = KC.story_num(KC.story_tab(Y.share).crisis, 0.34) * KC.story_num(cur.L, 1825) * KC.story_num(cur.sh.crisis, 1)
    if #cur.cr < KC.story_num(Y.max_crises, 2) and cur.cd + ad < KC.story_num(Y.esc_frac, 0.55) * bud then
      local best, bs = KC.story_pick(c, st, p, cur.cr)
      if best and bs >= KC.story_num(Y.escalate, 1.1) then return best end
    end
    if hi or KC.story_num(p[act], 0) <= KC.story_num(Y.recede, 0.6) * KC.story_num(st.pe, 0) then
      local H, heavy = KC.story_tab(Y.heavy), #cur.cr >= KC.story_num(KC.story_tab(Y.heavy).count_ge, 2)
      for _, a in ipairs(KC.story_tab(H.crises)) do for _, b in ipairs(cur.cr) do if a == b then heavy = true end end end
      if KC.story_maxp(c, p) >= KC.story_num(H.p_ge, 1.1) then heavy = true end
      return (heavy and c.acts[after]) and after or rec
    end
  elseif act == after then
    if hi or KC.story_maxp(c, p) <= KC.story_num(Y.calm, 0.6) then return rec end
  elseif hi then return rec end   -- фаза без роли (новая в будущих params): по сроку к Кузне
  return nil
end
function KC.story_enter(c, st, to, day, m, p)
  local Y, cur = KC.story_Y(c), st.cur
  if KC.story_is_crisis(c, st.act) then cur.cd = cur.cd + (day - st.since) end
  if to == c.start then cur = KC.story_newcycle(c, st, day, m) end
  if KC.story_is_crisis(c, to) then cur.cr[#cur.cr + 1] = to; KC.story_mods(cur, KC.story_tab(KC.story_tab(Y.after)[to]).same) end
  cur.path[#cur.path + 1] = to
  st.act, st.since, st.pe = to, day, KC.story_num(p[to], 0)
  if to == (Y.recover or "forge") then   -- знание, набранное за оборот, делает Кузню сильнее
    local g = (m.know - KC.story_num(KC.story_tab(cur.b).know, m.know)) * KC.story_num(Y.know_k, 0.5)
    cur.kx[to] = KC.story_num(cur.kx[to], 1) * (1 + KC.clamp(g, 0, KC.story_num(Y.know_cap, 0.3)))
  end
  st.pt = KC.story_target(c, st, to, day)
  st.hist[#st.hist + 1] = { to, math.floor(day) }
  while #st.hist > KC.story_num(Y.keep_hist, 60) do table.remove(st.hist, 1) end
  KC.emit({ type = "story_" .. to, cycle = cur.n, text = string.format("The age turns: %s.", tostring(c.acts[to].name)) })
end
function KC.story_apply(c, st)
  KC.story_restore()
  local kk = KC.clamp(KC.story_num(st.k[st.act], 1) * KC.story_num(KC.story_tab(KC.story_tab(st.cur).kx)[st.act], 1), 0.4, 1.6)
  for _, m in ipairs(c.acts[st.act].mods or {}) do
    local op, v = m[2], tonumber(m[3])
    if v then
      for _, l in ipairs(KC.STORY.paths[m[1]] or {}) do
        local b = l[1][l[2]]
        if op == "mul" then l[1][l[2]] = math.max(0, b * (1 + (v - 1) * kk))
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
  local st = KC.story_state(c, day)
  if math.floor(day) <= KC.story_num(st.last, -1) then return end
  st.last = math.floor(day)
  local m = KC.story_metrics(c)
  local p = KC.story_press(c, st, m)
  KC.story_ema(c, st, m, day)
  local r2 = function(x) return math.floor(KC.story_num(x, 0) * 100 + 0.5) / 100 end
  st.m = { y = r2(m.year), stress = r2(m.ore_stress), know = r2(m.know), comp = math.floor(m.comp), heat = m.heat,
           pf = r2(p.famine), pt = r2(p.twilight), pn = r2(p.night), ci = r2(m.ci), cyc = st.cur.n }
  local to = KC.story_next(c, st, m, p, day)
  if to and c.acts[to] then KC.story_enter(c, st, to, day, m, p) end
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
