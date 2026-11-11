-- KMM_Ore v2 — параметры истощения руды (поток ORE). Читается лениво, в первом рабочем тике (не при загрузке скрипта).
-- Модель LATE_GAME.md: yield = y0 * (R/R0)^k. y0 = ванильный _resourceMiningLevel узла при первом контакте.
-- v2 не вешает хуки движка: опрашивает персонажей игрока в тике и считает «труд» — игровые часы, которые персонаж
-- провёл, работая на узле (текущее действие → его цель → здание узла). Поэтому R и R0 — в «работо-часах».
-- Калибровка: поверхностная жила R0 = 400 работо-часов ≈ 17 игровых суток одного шахтёра или ≈ 3,5 суток бригады из 5.
return {
  ore_enabled = true,          -- главный выключатель потока (false — тик сразу выходит, ни одного вызова API и I/O)
  write_level = true,          -- false — только наблюдение и лог (узлы считаются, но _resourceMiningLevel не пишется)
  tick_source = "own",         -- "own": свой обработчик GameWorld::charsUpdate (как KMM_Traces); "conductor": работать
                               --   только по вызову KMM_Ore.tick() из тика дирижёра (свой обработчик сразу выходит)

  log_path   = "C:/KenshiModMap/logs/ore.log",
  debug_log  = "C:/KenshiModMap/logs/debug.log",
  state_path = "C:/KenshiModMap/logs/ore_nodes_%s.tsv",   -- %s = ключ мира (семя дирижёра из сейва, иначе "global")
  world_key  = "conductor",    -- "conductor" (семя мира дирижёра) или "global" (одно состояние на все сейвы)

  -- ленивый старт: только когда у игрока есть персонажи, и только спустя задержку после их появления
  start_delay_seconds = 8,     -- реальные секунды с персонажами на карте
  start_delay_polls   = 8,     -- и не меньше стольких опросов подряд с непустым отрядом
  start_delay_hours   = 0.05,  -- и игровое время сдвинулось хотя бы на столько часов (игра не на паузе после загрузки)

  -- порции
  poll_seconds   = 1.0,        -- опрос не чаще раза в N реальных секунд
  chars_per_poll = 4,          -- сколько персонажей игрока проверяется за один опрос (по кругу)
  work_radius    = 800,        -- персонаж дальше этого от узла — ещё идёт к нему, труд не считается
  max_dt_hours   = 2.0,        -- потолок труда за один опрос персонажа (пауза, сон, перемотка)
  work_task_types = { 87, 152, 189 }, -- TaskType.OPERATE_MACHINERY, OPERATE_AUTOMATIC_MACHINERY (если key() не число — фильтр только по шаблону)

  save_every_seconds = 60,     -- состояние на диск не чаще (только если что-то изменилось)
  log_every_hours    = 6,      -- строка MINE в ore.log на узел не чаще, чем раз в N игровых часов

  -- связь с дирижёром (всё под pcall; при ошибке отключается только связь)
  feed_conductor  = true,
  player_to_world = 0.25,      -- единиц руды мира дирижёра на работо-час игрока (с ближайшей жилы мира)
  region_min      = 0.15,      -- стартовый запас нового узла не ниже этой доли R0, даже в выработанном регионе

  -- шаблоны зданий (stringID) → класс. Только руда (железо, медь); камень и фермы не трогаем.
  templates = {
    ["14521-rebirth.mod"]       = "surface", -- Iron Rock (FOLIAGE-узел)
    ["42248-gamedata.base"]     = "surface", -- Iron Resource
    ["42249-gamedata.base"]     = "surface", -- Copper Resource
    ["99106-Boneyard Wolf.mod"] = "surface", -- Small Copper Resource (мод основы)
    ["99107-Boneyard Wolf.mod"] = "surface", -- Small Iron Resource (мод основы)
    ["2056-gamedata.base"] = "mine", ["2094-gamedata.base"] = "mine", ["2095-gamedata.base"] = "mine", -- Ore Mine I–III
    ["2096-gamedata.base"] = "mine", ["2097-gamedata.base"] = "mine", ["2098-gamedata.base"] = "mine", -- Ore Drill I–III
  },

  classes = {
    -- поверхностная жила: конечный запас (работо-часы), не восстанавливается, почти «мёртвая» на floor
    surface = { R0 = 400,  k = 1.5, floor = 0.02, regen_per_day = 0 },
    -- рудник: поток, восстанавливается (24/сутки = один шахтёр без потерь), никогда не ниже floor
    mine    = { R0 = 1200, k = 1.0, floor = 0.25, regen_per_day = 24 },
  },
}
