# PERF фаза 1 — журнал (2026-11-12)

## Что сделано
- KMM_Gov.snapshot(ttl): один обход getCharacterUpdateList на окно, общий для модулей. Запись rec: ch, x, z, fid, dead, ap, pl (ap.me), pkey (ключ платуна или ""); лениво по первому обращению: trader, tsid, down, unique, h, combat, town. Игроки в снимок не входят. Индекс snap.by_pkey. Снимок возвращает nil при любой ошибке (пауза fail_pause = 20 с), nil при enabled=false.
- Конфиг: KMM_Gov.cfg.snap = { enabled = true, ttl = 2.0, max_chars = 3000, fail_pause = 20 }. Параметры потребителей: params.traces.snap_ttl (по умолчанию 4 с), params.traces.price_seconds (20 с, было 10), params.self.snap_ttl (3.5 с), params.self.emit_events (true).
- Отладка: KMM_Gov.snapshot_stats() (builds/hits/fails/skipped/chars/last_err), KMM_Gov.snapshot_reset().
- Фолбэк обязателен: Traces и Self при отсутствии Gov или ошибке Gov.snapshot строят тот же формат записей собственным обходом (own_snapshot, кэш на ttl). Rumors при любой неудаче снимка идёт прежним циклом.
- KMM_Traces: kill_dead_caravans, lost_scan, prices, amb_scan, br_scan, loot_scan читают снимок. Окно lost/amb/br — один снимок (scan_window) и общий kinfo по платунам для amb и br. prices: один раз на платун (раньше на каждого персонажа), период 20 с. lost_scan: дальше lost_radius + lost_killer_radius персонажи отбрасываются сразу (они ни жертва, ни убийца). Ошибка API по-прежнему отключает только caravan_lost (тест Stock это проверяет).
- KMM_Self: scan читает снимок; вожак платуна определяется одним вызовом на платун.
- KMM_Rumors: findSpeaker берёт снимок (ttl 5 с), проверяет isDead выбранного в момент выбора.
- KMM_Ore: обхода NPC в модуле нет (только getAllPlayerCharacters), менять нечего.
- Не тронуто по поручению: KMM_Stock, KMM_Town, kmm_elite.lua, KMM_Conductor.lua (фаза 2).

## События шины от KMM_Self (только эмит; подписчиков нет)
Эмит через _G.KMM_Conductor.emit под pcall; params.self.emit_events=false выключает.
- self_retreat: a (fid отряда), b (fid врага, только why=faction_avoid), squad (ключ платуна), why ("flee" | "avoid" | "faction_avoid"), n (бойцов), down (лежат), loss (доля лежащих), x, z; для avoid player_tier (средний тир игрока); для faction_avoid pa, pb (сила фракций по оценке дирижёра).
- self_surrender_attempt: a, squad, mode ("runaway" | "knockout"), n, down, loss, leader_down=true, x, z.
- Нужно от фазы 2 (KMM_Conductor.lua, правит другой разработчик): добавить self_retreat и self_surrender_attempt в таблицу EPHEMERAL. Пока их там нет, эмит идёт обычной дорогой: журнал событий, chronicle.log, шина. Частота низкая (кулдаун 60 с на отряд), но по замыслу они должны быть без журнала. Поля ev.attacker/defender дирижёр дописывает сам.

## Замер (test_perf.py, N=200 NPC, окно 10 с, Traces + Self, 20 окон)
Вариант | вызовов API на окно | обходов списка на окно | Lua мс на окно
- до (резервные копии *_pre_perf): 15160 | 9.9 | 2.3-2.6
- после, с Gov: 4415 | 2.0 | 1.55
- после, без Gov (собственный обход): 6479 | 3.6 | 1.55
- после, Gov.snapshot сломан: 6479 | 3.6 | 2.5
Итого с Gov: вызовов API 0.29 от прежнего (минус 71 %), обходов 0.2 от прежнего. Время в заглушке — только Lua без стоимости движка; в игре вызовы API дороже, чем в заглушке, так что выигрыш по времени там больше.
Эквивалентность: во всех вариантах одинаково: runAway 4, caravan_lost 10, функции не отключаются.

## Что подтвердит только игра
- Реальная стоимость вызова API персонажа и снижение кадра/пика Gov (до и после).
- Что getIsTrader на обёртке платуна (ch:getPlatoon()) работает как в старом коде; что isDown/isUnconcious/getCurrentTownLocation доступны (лениво, при ошибке поле = false).
- Что устаревание снимка до 3.5-4 с не ломает бегство/сдачу и потерю каравана на практике.
- Что события self_* доходят до шины (после правки EPHEMERAL в фазе 2).

## Замечания
- tools\build\test_conflict.py падал и до PERF (сборка остановлена: 1 ошибка) — к этой задаче не относится.
- Единый диспетчер тика (пункт 15 аудита) не делался: нужен Gov.every, а Conductor/Stock/Town/Elite в фазе 2.
