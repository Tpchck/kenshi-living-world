# STATUS — сводка проекта (2026-11-15). Читать первым.

Kenshi 1.0.65 Steam + RE_Kenshi 0.3.5 + KenshiLua; плагин KMM_Native 2.4.0. mods.cfg: 663 мода (пишет только генератор). Установка 16.11 06:01 — последняя «новая игра».
История до 14.11: `docs/archive/STATUS_20261114.md`, решения: `docs/archive/DECISIONS_to_20261114.md`.

ХОТФИКС 2026-11-16 06:53: хищники выключены (краш в ZoneSmell), иконки >1024 px уменьшены; сейв совместим.
УСТАНОВЛЕНО 2026-11-16 06:01 (снимок backup/releases/20261116_060147_pre_install, mods.cfg бэкап 20261116_060153): вся пачка 15–16.11, два ревью, verify_all OK, тесты tools/streams OK. НУЖНА НОВАЯ ИГРА — В ПОСЛЕДНИЙ РАЗ; дальше только save-compatible правки. Старт один: Castaway.
21:26 установлено: один старт — Castaway (голый, 0 денег, навыки 1, голодный malnourished=true, Великая пустыня); Iron Wanderer выключен (fix.json test_start.enabled=false). Брейншторм: docs/brainstorm/B1–B4. Нужна новая игра.

## Как работаем
- Цель: цельная живая игра; игрок — щепка в море; геймплей из взаимодействия с живым миром; атмосфера > декор.
- Всё через ядро: справочник `docs/core/` (people, ai_squads, world, economy_player, data, ledger), очередь `docs/core/BACKLOG.md`.
- Сборка и установка: `python -I -X utf8 tools/build/kmm_build.py --write all --install` (сам гонит verify_all: lua_lint, api_audit, 104 теста). Игра должна быть закрыта.
- Чистка мусора: `python -I -X utf8 tools/cleanup_dev.py backup/archive/<имя>.zip` (эталоны *_pre_perf* сохраняются).
- После игровой сессии: `python -I -X utf8 tools/session_report.py` → logs/session_last.txt.
- Самопроверка (2026-11-16, не установлено, в игре не проверено): KMM_Probe.lua (KMM_Conductor) через ~20 с после появления персонажей и ещё раз через 5 мин проверяет вызовы движка (только чтение) → logs/probe.log `PROBE <имя> ok|fail|absent`; раздел «Самопроверка» в session_report; тест `_dev/test_probe.py`.

## Правда об игре
- Сыграно: 2 сессии 14.11 (~40 мин + 3 мин). Подтверждено игрой: сборка грузится, плагин стартует, сейв модели пишется, say() слышен (rumors.log), пополнение торговцев.
- Всё остальное — только офлайн-тесты на заглушках. Реестр вызовов ядра со статусом: `docs/core/ledger.md` (106 методов, след в игре у ~50).
- KMM_Gov троттлит тяжёлые модули (conductor/traces/stock/self > 0.6 мс) — проверить долю троттлинга в сессии.

## Установлено 2026-11-15 (пакет 1, в игре не проверено)
| что | маркер в логах |
|---|---|
| Пленник заковывается пленителем, проверка цепей через isChainedMode | debug.log `4a setChainedMode … owner=` |
| Ванильные кампании: видно ok/FAIL запуска | debug.log `campaign: triggerCampaign` |
| Самосохранение NPC решают люди, не вьючные звери; нокаут через knockoutForceTimer | debug.log `flee:` `fearless:` |
| Цены города: проба Town.tradeGoodsMults через isTown | debug.log `TGM probe OK/FAIL` |
| Руда: учтён труд в шахте (TaskType 189) | ore.log `NEW node`, `SKIP task=` |
| Память соперника — ванильная LT-память через плагин (весь отряд игрока) | nemesis.log `remember: LT_` / `remember: no native` |
| Хроника во вкладке сообщений | nemesis.log `chronicle: addMessage ok` |
| 5 бродячих отрядов модов получили фракцию (раньше не спавнились) | kenshi_info.log без `no faction for homeless squad` |
| Кривая опыта: против +20 по навыку 5× (ваниль 3×), против −20 0.33× | ощущение в бою; CONSTANTS в KMM_Fix |
| KMM_Deeds: шина дел мира из колбэка ядра affectRelations → слухи | deeds.log `first callback:`, `deed:` |

## Установлено 2026-11-15 04:46 (пакет 2 + R, в игре не проверено)
| что | маркер в логах |
|---|---|
| Соперники-искатели: 23 бродячих отряда по тирам, ванильные патрули по карте + бары (Q1); вес по опасности биома (R5) | отчёт потоков fix/relics `rivals`, `rival_danger:*` |
| Дела разыскиваемых → ванильная награда, охотникам цель HUNT_BOUNTIES (Q2) | outlaws.log `native bounty ok/FAIL`, `deed bounty +`, `hunt goal` |
| Помощь фракции → память и долг; город помнит дела; ванильные реплики sendDialogEvent (Q3) | nemesis.log `deed_owed:`, `deed_town:`, `said_ev:` |
| Осады через кампании движка, исход по фазе (Q4) | siege.log, `fallback roll` |
| Отношения фракций сверяются с ядром, запись дельтой (Q5) | debug.log `RELSYNC` |
| Цены товаров города от склада через Town.tradeGoodsMults (R1) | debug.log `TGM write OK`, `TGM town` |
| Слух о месте открывает его на ванильной карте, разыскиваемый — на сутки (R2) | rumors.log `map place ok`, `map squad ok` |
| Касса торговца = богатство города (R3) | tempo.log `TILL town`, `TILL poor` |
| Бой/смерть оставляют ванильный запах — хищники ядра приходят сами (R4) | predators.log `smell:`, herds.log `smell took:` |

## Установлено 2026-11-15 05:46 (пакеты 3–4 + правки ревью REVIEW_batch34, в игре не проверено)
| что | маркер |
|---|---|
| Модель дирижёра сверяется с ядром: численность, процветание, владельцы городов; рост не раздувает силу, потери — только подтверждённые destroyPlatoon (S2) | debug.log `CORESYNC steps=` (guard credit/nohint/explained) |
| Банды и соперник — постоянные отряды движка с ванильными пакетами ИИ (рэкет/бродяги/охота на игрока); сироты отпускаются; без двойной награды (S3) | outlaws.log/nemesis.log `persistent ok`, `package ok` |
| Ванильные диалоги барменов/торговцев/стражи по состоянию мира (перехват условия), угроза соперника; фолбэк на жетоны (S4) | debug.log `DIPLO_COND hook live`, `DIPLO_WORLD` |
| Производительность: общий такт 3 с в Traces/Self/Stock, кэши (S5); снимок NPC 0.75 с, стоимость снимка отдельно (T2) | debug.log `[KMM_Gov] summary/modules` |
| Судьбы конкурентов → ванильная награда, слухи, память; одно дело — одна награда (S6) | fates.log `deed bounty +`, `justice:` |
| Дирижёр разбит на 6 частей KMM_Conductor_*.lua (T1), поведение без изменений | — |

## Установлено 2026-11-15 10:07 (пакет 5 + правки ревью REVIEW_batch5, 90 тестов, в игре не проверено)
| что | маркер |
|---|---|
| Отряды Traces у игрока получают ванильные пакеты ИИ; караван с грузом и беженцы — постоянные (≤4); временные убираются вне взгляда (U1) | debug.log `pkg ok`, `engine keeps the squad off-screen`, `slot freed` |
| Рейд на базу — родная кампания движка, исход repelled/sacked/unattended по фазе, опрос раз в 30 с; фолбэк — рейд Traces (U2) | debug.log `campaign: base outcome`, `-> Traces raid` |
| Голод города → ванильный STARVED у производственных построек, откат при изобилии/выключении; productionMult не трогается (U3) | stock.log `U3 starve`, `U3 restore` |
| Пополнение лавок сдвигается по жизни города через getTotalHours/addHours, после 3 правдоподобных чтений (U4) | tempo.log `RESTOCK armed`, `RESTOCK shift` |
| Гонка за рекрутом: лучший рекрут бара уходит к конкуренту (Drifters и др.) через 30–54 ч, если игрок не наймёт; слух recruit_taken (V1) | recruitrace.log `race start`, `recruit taken`, `setFaction ok/FAIL` |
| Мёртвый код удалён (~135 строк Lua), разовые скрипты в tools/archive, kmm_diplo пишет отношения только через дирижёра (W1) | — |

Известные хвосты: удаление KMM_Town при остановленной постройке оставит её входы обнулёнными в сейве; гонка рекрута обрывается, если игрок ушёл из города; DEADCODE.md раздел «после игровой проверки» ждёт сессию.

## Установлено 2026-11-15 17:24 (пакеты 6–7 + правки ревью REVIEW_batch6/7, 100 тестов, в игре не проверено)
| что | маркер |
|---|---|
| Охотник несёт пленника рядом с игроком → слух; отбить можно, сверка по handle (X1) | outlaws.log `outlaw_captive_carried`, `captive taken` |
| Конкурент перекупает свободных наёмников гильдии (контракт); невольничий рынок — только слух, смена хозяина выключена (X2) | recruitrace.log `merc hired`, `slave rumor` |
| Вызов лидера-конкурента на поединок репликой: не в городе, вражда снимается со всего отряда, удары поединка не рвут договоры (X3) | diplo `DUEL offer added`, `DUEL start/end/clear` |
| Конкуренты переносят лут из ничьих ящиков руин себе (перенос, не уничтожение; руины у базы игрока не трогаются) (X4) | relics `ruinloot probe`, `ruinloot moved` |
| Дела игрока без свидетелей не становятся слухами и памятью города (Y1) | deeds.log `witness:` |
| Подтверждённая гибель отряда снижает процветание фракции в ядре (проба с lock-файлом) (Y2) | debug.log `PROSPERITY probe/defeated`, `no effect`, `disabled forever` |
| Побеждённый рядом с игроком лежит ~30 реальных с — связать/обыскать (Y3) | debug.log `KO hold:`, `KO release:` |
| Засада держит участок нарядом ядра, подтверждение через час игры, снятие в сейве (Y4) | predators.log `squadjob ok/drift/release` |
| Соперник оценивает видимую силу отряда игрока: напасть/угрожать/уйти; повторный отход не спамит (Y5) | nemesis.log `appraise: app=` |

## Установлено 2026-11-15 20:05 (104 теста; снимок backup/releases/20261115_200457_pre_install, mods.cfg бэкап 20261115_200503). НУЖНА НОВАЯ ИГРА (Астартес, лут руин, Soulbodies)
- KMM_Scenario (Z1): тест-сценарии первой сессии по state\scenario.txt, bat-файлы scenario_*.bat, инструкция docs/TEST_SCENARIOS.md. Без файла инертен. Ставить при закрытой игре.

- По живой сессии 15.11 вечер: имена без меток [KMM T*] (traces.py); туманники без общего Armoured Hood (wardrobe.py: элита только у чистых лидеров, у диких — нет); следы «первого часа» отменяются, если игрок ушёл >20000 (Traces); Soulbodies ×0.3 в биомах + ванильный патруль + «эхо павших» ночью у мест бойни (relics.py, Predators); запах не выключается от промахов зоны; KO-перехват регистрируется при загрузке (в игре было asks=0).

- Также в этой установке: награда за голову B1 (Outlaws), лут руин L1 (201 TOWN), ордена Астартес A1 (docs/core/ASTARTES.md), craft/haul: полный инвентарь не ошибка; KC.try_dispatch через Traces.request; RelicRace: «чужие» здания — только у фракций с городами; Rumors: отсутствие ManagementScreen = промах, а не самоотключение карты.

- 20:44 доустановка: дикие без шлемов/металла как своей одежды — только редкий трофей и одна вещь у следов T2/T3; племена каннибалов Bandit Variety больше не в Holy Order/Stickperson.
- 21:09: второй старт «Castaway» (rules/streams/fix.json survival_start): Великая пустыня 57024,-52416, навыки 1, одна набедренная повязка, 0 денег; старт «KMM Test: Iron Wanderer» оставлен.
- KMM_Native 2.4.0 (N1): ПКМ по лежащему без сознания скелету — «Salvage Parts», по животному — «Butcher»; приказ KILL_CAGE_OCCUPANT, добыча из rules\salvage.json получившему приказ (смерть ≤60 с, жив, фракция игрока, ≤ credit_radius). Рубильник state\salvage.off. DLL в build\KMM_Native, тест `tools/cpp/kmm_native/test_salvage.py`. Ставить `kmm_build.py --write all --install` при закрытой игре.

| что | маркер в RE_Kenshi_log.txt |
|---|---|
| Salvage/Butcher: хуки и правила | `salvage: hooks installed`, `salvage: cfg loaded N/M items` |
| Пункт меню появился / приказ / добыча | `salvage: menu robot/animal`, `salvage: ordered`, `salvage: awarded <sid> x<n>`, `salvage: no credit (…)` |

- A1 ордена космодесанта (docs/core/ASTARTES.md): лагеря Mark-X сняты (6 TOWN REMOVED, 30 спавнов Astartes survivors), 4 фракции-ордена (Ultramarines — Cheaters Run, Space Wolves — Sonorous Dark+Ashlands, Dark Angels — Black Desert+Deadlands, Black Templars — Venge) с главой-уником, капитанами, сержантами; бродячие отряды только в своём регионе; разговор «KMM Order» у всех членов; в дирижёре — реликтовые imperium. Тест `build/KMM_Relics/_dev/test_a1_astartes.py`. **Нужна новая игра.** Маркера в логе нет (данные): подтверждение — встреча отряда ордена в его регионе и разговор.

## Ждёт владельца
- A1: в новой игре найти отряд ордена в его регионе (напр. Venge — Black Templars), поговорить (ветка «Who are you?»); проверить, что не нападают на караваны UC/HN; пустые здания снятых лагерей — снести через rules/cleanup.json (KMM_Cleanup), если мешают.
- N1: в игре проверить, что KILL_CAGE_OCCUPANT добивает лежащего скелета и животное (если боец не бьёт — в salvage.json `task`: MELEE_ATTACK_ANIMAL / FOCUSED_MELEE_ATTACK, без пересборки); по `no credit (orderer too far: X > 300)` откалибровать credit_radius (единицы мира ?).
- Игровая сессия (разрешено пропускать; когда будет — `tools/session_report.py`).
- git вместо папок бэкапов (коммиты — только по явному решению).

## Первая игровая сессия — чек-лист (НОВАЯ игра, 30–60 мин)
1. 0 ошибок Lua; доля `throttle` в debug.log; нет `disabled forever`/`off until restart`.
2. Драка с главарём/соперником: реплики над головой, `remember: LT_` в nemesis.log; побеждённый лежит ~30 с (`KO hold:`).
3. Голодный и сытый город: разные цены (`TGM probe`), остановка ферм (`U3 starve`).
4. Бар: гонка за рекрутом (`race start`); у лидера-конкурента — реплика вызова на поединок (`DUEL offer added`).
5. Бродяги-искатели на дорогах и руинах; бой с сильным — заметно быстрее рост навыка.
6. Рейд на базу (`campaign: base outcome`); deeds.log: направление a/b в `first callback:`.
После сессии: `python -I -X utf8 tools/session_report.py` → logs/session_last.txt.

## Откат
`rollback.bat` (снимок перед каждой установкой, хранятся 3 последних), `safe_mode.bat` (выключить все KMM_*), бэкапы mods.cfg — backup/cfg.
