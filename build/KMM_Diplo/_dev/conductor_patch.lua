-- KMM_Diplo → патч дирижёра (применяет интегратор). Файл: build/KMM_Conductor/scripts/init/KMM_Conductor.lua.
-- (1) Вставить блок ниже ВНУТРЬ таблицы `KMM_Conductor = {` (например, сразу после строки `KMM_Conductor = {   -- консоль …`).
--     Это публичные обёртки над локальными sign/break_treaty/add_rel/emit/power — договоры игрока по диалогу идут
--     через ту же механику, что и договоры ИИ (шина, хроника → слухи, обязательства, сроки, доверие).
-- (2) После закрывающей `}` таблицы добавить строку `_G.KMM_Conductor = KMM_Conductor`.
--     По docs KenshiLua (DialogueScriptingBridge.md) каждый init-скрипт — своя песочница: простое присваивание глобала
--     не видно другим скриптам. Без этой строки KMM_Traces/KMM_Self/KMM_Diplo не находят дирижёр.
-- Без патча KMM_Diplo работает по запасному пути (пишет договор прямо в состояние дирижёра, событие — в журнал и хронику,
-- но без шины событий). Проверка: build/KMM_Diplo/_dev/test_diplo.py компилирует дирижёр с этим патчем.
-- >>> BEGIN KMM_Diplo patch
  player_sign = function(fid, ttype, why, player_is_suzerain)   -- договор фракции fid с игроком; vassal: сюзерен = fid, либо игрок
    local pf = CFG.player_faction
    if not (S and pf and S.F[fid] and S.F[pf]) then return nil end
    DAY = math.max(DAY, S.last_day or DAY)
    local ex = treaty_between(fid, pf, ttype)
    if ex then ex.term = DAY + (P.treaties.term_days[ttype] or 360); return ex end
    if ttype == "vassal" and player_is_suzerain then return sign(ttype, pf, fid, why) end
    return sign(ttype, fid, pf, why)
  end,
  player_break = function(fid, why, by_player)   -- разорвать все договоры fid ↔ игрок; by_player = измена игрока
    local pf = CFG.player_faction
    if not (S and pf) then return 0 end
    DAY = math.max(DAY, S.last_day or DAY)
    local n = 0
    for _, t in pairs(S.treaties) do
      if t.active and ((t.a == fid and t.b == pf) or (t.a == pf and t.b == fid)) then break_treaty(t, why, by_player and pf or nil); n = n + 1 end
    end
    return n
  end,
  add_rel = function(a, b, dv) if S and S.F[a] and S.F[b] then add_rel(a, b, dv) end end,
  add_trust_one = function(a, b, dv) if S and S.F[a] then S.F[a].trust[b] = clamp(trust(a, b) + dv, -100, 100) end end,
  emit = function(ev) if S then DAY = math.max(DAY, S.last_day or DAY); return emit(ev) end end,
  power = function(fid) return S and power(fid) or 0 end,
-- <<< END KMM_Diplo patch
