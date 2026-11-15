-- KMM_Ore v3 — параметры руды игрока (docs/core/economy_player.md, раздел «Руда»). Читается лениво, в первом рабочем тике.
-- Модель: yield = base * max(floor, (R/R0)^k) * жила региона. base — ванильный _resourceMiningLevel узла при первом контакте,
-- жила региона — KMM_Conductor.region_ore (остаток мировых жил вокруг узла, его вычерпывают и NPC, и игрок).
-- R и R0 — в «работо-часах»: часы, которые персонаж игрока проработал на узле (или автобур проработал под питанием).
-- Калибровка: поверхностная жила R0 = 400 работо-часов ≈ 17 игровых суток одного шахтёра или ≈ 3,5 суток бригады из 5.
return {
  ore_enabled = true,          -- главный выключатель потока (false — тик сразу выходит, ни одного вызова API и I/O)
  write_level = true,          -- false — только наблюдение и лог (узлы считаются, но _resourceMiningLevel не пишется)
  tick_source = "own",         -- "own": свой обработчик GameWorld::charsUpdate; "conductor": только по KMM_Ore.tick()

  log_path   = "C:/KenshiModMap/logs/ore.log",
  debug_log  = "C:/KenshiModMap/logs/debug.log",
  state_path = "C:/KenshiModMap/logs/ore_nodes_%s.tsv",   -- запасной файл (%s = ключ мира); основное состояние — в сейве
  world_key  = "conductor",    -- "conductor" (семя мира дирижёра) или "global" (одно состояние на все сейвы)
  state_in_save = true,        -- узлы в состоянии дирижёра (S.ore_nodes): сохраняются в сейв и откатываются вместе с миром

  -- ленивый старт: только когда у игрока есть персонажи, и только спустя задержку после их появления
  start_delay_seconds = 8,
  start_delay_polls   = 8,
  start_delay_hours   = 0.05,

  -- опрос персонажей
  poll_seconds   = 1.0,        -- опрос не чаще раза в N реальных секунд
  chars_per_poll = 4,          -- сколько персонажей игрока проверяется за один опрос (по кругу)
  work_radius    = 800,        -- персонаж дальше этого от узла — ещё идёт к нему, труд не считается
  max_dt_hours   = 2.0,        -- потолок труда за один опрос персонажа (пауза, сон, перемотка)
  work_task_types = { 87, 152, 189 },   -- TaskType: OPERATE_MACHINERY, OPERATE_AUTOMATIC_MACHINERY, AUTO_LABOURING_MINES
  pretend_task_types = { 190, 221 },     -- «изображать работу» — не считаются
  subject_fields = { "subject", "currentSubTarget" },   -- поля Tasker, где искать здание-цель
  learn_orders = true,         -- приказ игрока на рудный узел добавляет его TaskType к рабочим (подписка в первом рабочем тике)

  -- автоматические буры игрока (auto в ore_templates.lua): скан зданий вокруг персонажей
  scan_enabled = true, scan_seconds = 30, scan_radius = 3000, scan_max_objects = 80,
  auto_rate = 1.0,             -- работо-часов на час работы автобура под питанием
  auto_max_hours = 6,          -- потолок за один скан

  -- жила региона (KMM_Conductor.region_ore): множитель выхода max(region_floor, share^region_k), обновление раз в N игровых часов
  region_live = true, region_k = 1.0, region_floor = 0.2, region_refresh_hours = 6,

  save_every_seconds = 60,     -- файл не чаще (только если что-то изменилось)
  log_every_hours    = 6,      -- строка MINE/AUTO в ore.log на узел не чаще, чем раз в N игровых часов
  diag_every_hours   = 12,     -- строка CHAIN (где обрывается цепочка опроса) не чаще

  -- связь с дирижёром (всё под pcall; при ошибке отключается только связь)
  feed_conductor  = true,
  player_to_world = 0.25,      -- единиц руды мира дирижёра на работо-час игрока (с ближайшей жилы мира)
  feed_every_hours = 2,        -- труд уходит в мир порциями раз в N игровых часов
  recent_days = 10,            -- окно «недавней добычи» узла (сводка S.base.ore)

  -- шаблоны: основной список — ore_templates.lua (генератор _dev/gen_ore_templates.py по цепочке модов).
  -- Здесь — ручные правки поверх: ["sid"] = "surface" | "mine" | false (исключить).
  templates = {},

  classes = {
    -- поверхностная жила: конечный запас (работо-часы), не восстанавливается, почти «мёртвая» на floor
    surface = { R0 = 400,  k = 1.5, floor = 0.02, regen_per_day = 0 },
    -- рудник/бур: поток, восстанавливается (24/сутки = один шахтёр без потерь), никогда не ниже floor
    mine    = { R0 = 1200, k = 1.0, floor = 0.25, regen_per_day = 24 },
  },
}
