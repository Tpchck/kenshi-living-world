# BEHAVIOR — поток E (2026-11-11)
Цель (DESIGN.md «Сила и бедность фракций», CORE.md §5): слабые избегают сильных, но вражда по лору остаётся.
Файлы: `rules\streams\behavior.json`, `tools\streams\behavior.py` → `build\KMM_Behavior\KMM_Behavior.mod` (dry-run общего генератора: 0 ошибок, 0 конфликтов).

## Что сделано
coexistence больше нет (её убрал интегратор). Единственный рычаг уровня фракции, который движок понимает, — **пороги бегства** (`fcs.def` FACTION):
- `run away ratio of squad size` — отряд бежит, если от него осталось меньше этой доли;
- `run away ratio relative to enemy` — бежит, если не превосходит врага по численности в этом соотношении (2.0 = нужно 2:1);
- значение 0 — никогда не бежать.

41 бандитская фракция (OT_BANDIT, не `not real`) разбита на ярусы по лору. Значения только повышаем: смелее ванили никого не делаем.

| Ярус | Пороги (доля отряда / соотношение) | Фракции | Изменено |
|---|---|---|---|
| poor — рвань, голодные, дорожная шпана | 0.6 / 1.5 | Starving Bandits, Dust Bandits (+ Dust Raiders/Reapers/Lords/Union), Outlaw, Rebel Farmers, Rebel Swordsmen, Yabuta Outlaws, Empire Criminals, Gutters, Grass Pirates, Sysus Bandits, Cult of Goblin, Bloodraiders, Skull Collectors, Sailback Poachers, Lake Threshers | 19 |
| gang — организованные банды, ниндзя | 0.4 / 1.0 | Sand ninjas, Black Dragon Ninjas, White Eyebrow Clan, Swamp Ninjas, Red Sabres, Black Desert Ninjas, Skin Bandits, Gorrillo Bandits, Slave Hunters, Dark Reavers, Steel Raiders, Blood Wolves, Lost Oni (и все неперечисленные OT_BANDIT) | 13 |
| fanatic — бьются до конца по лору | без изменений | Berserkers, Lone Berserker, Kral's Chosen, Band of Bones, Crab Raiders, Reavers, Skeleton Bandits, Oni, The Hollow Feast | 0 |

У большинства бандитов в ванили было 0/0 («никогда не бежать») — отсюда и бойня на дорогах. Сильные (UC 0.4/0.6, Shek, Tech Hunters, Astartes, Necrons — 0/0, остатки Империума 0.2/0.4 в RELICS) не тронуты. `relations` не тронуты: голодные по-прежнему враждебны всем, просто разбегаются, если не имеют численного перевеса.

## Что смотрел и не стал делать
- **FACTION `AI Goals`** — ни одна фракция в сборке их не использует (у всех пусто). Как движок трактует цели на уровне фракции, не проверено; добавлять наугад (например, RUN_AWAY) рискованно — можно получить вечное бегство.
- **AI-пакеты отступления** уже есть в ванили: `Normal Raid Retreat [passive]`, `Loot food then run away`, `Leader flees while guards fight` (задачи RUN_AWAY / RUN_AWAY_HOMETOWN). Но назначаются они в SQUAD_TEMPLATE, а отряды принадлежат ECONOMY и RELICS. **Запрос интегратору:** если нужно сильнее, владельцы отрядов могут добавить бандитским рейд-отрядам `Normal Raid Retreat [passive]` вторым пакетом.

## Вне возможностей данных
- Пороги бегства считают **численность**, а не силу: оценки силы отряда или снаряжения противника перед боем движок через данные не даёт — это только плагин (KenshiLib C++, спайк 3).

## Как проверить в тесте
Голодные и пыльные бандиты, встретив равный по численности патруль UC, Holy Nation или Империума, должны отступать, а не нападать до последнего. Фанатики (Kral's Chosen, Berserkers) ведут себя как раньше.

## KMM_Traces: видимые события (visible)
KMM_Traces подписывается на шину дирижёра (`subscribe("*")`, под guard, не на старте) и материализует события рядом с игроком (город события <= 6000 от игрока):
`trade_for` / `treaty_signed` (trade) -> живой торговый отряд фракции (существующий торговый шаблон из `traces.json: live_caravans`, не в `dead_caravan_sids`, поэтому его гибель даёт `caravan_lost`), появляется на дороге между игроком и городом;
`refugees` -> бедный отряд фракции (шаблон `refugees`) у города, идёт прочь; `relic_salvage` -> боевой отряд фракции у ближайших руин (`sites` kind=ruins) или у города;
`smuggle_run` -> малый отряд самого бедного тира (T0) фракции у города (отдельного ванильного шаблона контрабандистов нет, пропущен).
Лимиты: очередь <= 16, события старше 10 игровых дней выбрасываются, дубль (тип+фракция+город) не чаще раза в 10 дней, <= 1 спавн на 60 с, <= 4 живых (TTL 900 с), общие min_gap/max_per_day Traces. Параметры `traces.visible_*` (radius, gap_seconds, max_live, ttl_seconds) необязательны.
Первая ошибка отключает только `visible` (причина в debug.log). Тест: `_dev/test_traces_visible.py`.
