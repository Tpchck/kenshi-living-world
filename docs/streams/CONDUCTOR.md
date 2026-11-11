# CONDUCTOR — поток A: дирижёр v0 на KenshiLua (2026-11-11)

## Статус
Готово и проверено офлайн. На LuaJIT из самого KenshiLua (`lua51.dll`) с заглушками API игры: компиляция проходит, 60 игровых дней дают 12 событий, 5 «лидер убит/пленён» материализуются при загрузке лидера, журнал проходит запись в сейв и чтение обратно, откат времени сбрасывает журнал. **В игре не проверялось.**

## Файлы (только мои)
| Файл | Что |
|---|---|
| `build\KMM_Conductor\scripts\init\KMM_Conductor.lua` | сам дирижёр (KenshiLua грузит `scripts\init\*.lua` активного мода при старте) |
| `build\KMM_Conductor\conductor.json` | копия правил для мода (Lua читает её, запасной путь — `C:/KenshiModMap/rules/conductor.json`) |
| `rules\conductor.json` | правила: `interval_days`=5, `first_event_after_days`=3, `outcome`, пути, 99 пар «город — лидер» |
| `build\KMM_Conductor\_dev\gen_rules.py` | генератор правил из ванильной цепочки (gamedata.base → Newwworld → Dialogue → rebirth) |
| `build\KMM_Conductor\_dev\test_conductor.py` | офлайн-тест на lua51.dll; логи перенаправляет во временную папку |

Пустой `KMM_Conductor.mod` для лаунчера создаёт интегратор: `kmm_build.py --write conductor`. Папку `_dev\` при установке можно не копировать, игре она не нужна.

## Как работает
1. **Кандидаты** (gen_rules.py): базовый город, у которого есть ванильный override-вариант с условием «лидер X НЕ жив» (ссылка город → world state с val0=0 на состояние «X is alive»). Атакующий — владелец варианта, если он враг владельца города (relations ≤ −50), иначе самый враждебный враг владельца. Получилось 99 пар, 31 лидер, 11 фракций-защитников (UC, Holy Nation, Shek, Slave Traders, Southern Hive, Reavers, Crab Raiders, Skin Bandits, Skeleton Bandits, Deadcat, Flotsam).
2. **Хроника:** тик `GameWorld::charsUpdate`, день — `getGameWorld():getTimeStamp_inGameHours():getTotalDays()`. Раз в `interval_days` выбирается случайная пара, у лидера которой ещё нет исхода. Шанс успеха: `p = clamp(base_success · (2·sA/(sA+sD))^k, min, max)`, где sA/sD — `factionMgr:getFactionByStringID(sid):getFactionSize()` (если недоступно — 1). Успех делится на «убит» и «пленён» по `capture_share` (0.4). Иначе — «атака отбита».
3. **Материализация:** «убит» и «пленён» ждут в `pending`. Раз в `scan_seconds` (и сразу после любого `Character::_NV_init`) просматривается `GameWorld:getCharacterUpdateList()`. Если `getGameData().stringID` загруженного персонажа совпал с лидером, применяется `declareDead()` или `setChainedMode(true, свой handle)`, затем `uniqueStateUpdate()`. Персонажей игрока не трогает (`apply_to_player_characters=false`). Дальше владельца меняет ванильный world state.
4. **Журнал между сейвами:** `PlayerInterface::serialise(self, gameData)` пишет состояние в `gameData.data_string["kmm_conductor_state"]`, `PlayerInterface::loadFromSerialise` читает. Нет ключа (старый сейв) или время пошло назад (новая игра) — новый журнал. Зеркало для диагностики — `C:\KenshiModMap\logs\conductor_state_last.lua`, при загрузке оно не используется.

## Контракт chronicle.log (для B RUMORS) — не менялся
`C:\KenshiModMap\logs\chronicle.log`, UTF-8, строка на событие, поля через TAB:
`game_day, event_id, event_type (attack_repelled|leader_killed|leader_captured|materialized), town_sid, town_name, faction_attacker, faction_defender, leader_sid, leader_name, status (pending|applied), text`.
`game_day` — дробное число с 2 знаками. Для `materialized` `event_id` = id исходного события, `status=applied`. Пример:
`3.00	1	leader_killed	18021-Newwworld.mod	Bad Teeth	Shek Kingdom	The Holy Nation	59164-Dialogue.mod	High Inquisitor Seta	pending	Word spreads that High Inquisitor Seta fell when Shek Kingdom struck at Bad Teeth.`
Файл общий для всех сейвов (только дописывается). Принадлежность событий конкретному сейву — в журнале внутри сейва.

## Ручной тест (сейв 24days_KMMTEST)
1. Интегратор ставит `KMM_Conductor` в `Kenshi\mods` и в mods.cfg (после KenshiLua, позиция среди модов не важна).
2. Загрузить `24days_KMMTEST`. В `steamapps\workshop\content\233860\3817000612\logs\KenshiLua.log` должны быть строки `[KMM_Conductor] config …: 99 enabled …`, `v0 loaded`, `no journal in this save — starting a new one`.
3. Промотать ≥3 игровых дня (скорость ×5/×100 из RE_Kenshi) → в `C:\KenshiModMap\logs\chronicle.log` появится первое событие, далее раз в 5 дней.
4. Сохранить и загрузить заново → в KenshiLua.log `journal loaded from save: N events …`. **Это ключевая проверка механизма сохранения.**
5. Материализацию проверить, подойдя к лидеру из строки `pending` (например, ближайший к игроку город из хроники). Или временно выставить `capture_share`/`interval_days` и использовать консоль KenshiLua (Ctrl+Shift+L): `KMM_Conductor.roll_now()`. Если глобал не виден из консоли из-за песочницы скриптов — ждать тика.

## Ограничения и непроверенное
- Вне загруженной зоны (лидер далеко от игрока) убить или пленить лидера нельзя: KenshiLua не даёт записать состояние уникального NPC, поэтому исход висит `pending`, пока игрок не окажется рядом.
- Не проверено в игре: (а) сохраняет ли игра свой ключ в `data_string` записи PlayerInterface (если нет — журнал живёт только до перезапуска, а из зеркала не восстанавливается); (б) делает ли `setChainedMode(true, свой handle)` NPC «IMPRISONED» для world state (если нет — поставить `capture_share: 0`, тогда все успехи станут убийствами); (в) когда игра пересчитывает override города — по наблюдению модов, при подгрузке города/зоны.
- Ванильные условия часто требуют смерти нескольких лидеров (например, Blister Hill → Flotsam: Phoenix, Seta и Valtena). Одно событие сдвигает мир на шаг, вариант срабатывает, только когда выполнено всё условие.
- `getFactionSize()` для фракций вне загруженной зоны может вернуть 0. Тогда используется 1, то есть шансы равные.

## v2 (2026-11-11, доделано интегратором)
- Интервал: 30 ± 10 игровых дней, равномерно (`interval.base_days/jitter_days`); первое событие на 10-й день. Пара «город — лидер» выбирается с весом `strength(атакующий)^exponent`; strength = `getFactionSize()` или число его городов в ванили × 10 (`attacker_weight`).
- Материализация только в окне `window_seconds` (15 с) после появления лидера в загруженных персонажах. Есть два триггера: колбэки `Character::_NV_init` и `_NV_loadFromSerialisePostCreationStage` и скан раз в 2 с.
- Дополнительное условие: лидер скрыт от игрока — `isOnScreen == false`, дальше `min_distance` (1500) от всех персонажей игрока, `lineOfSightCheck(pc) == 0` для тех, кто ближе `los_max_distance` (4000). Не успели в окне — ждём выгрузки и следующей загрузки.
- Не проверено в игре: значение `lineOfSightCheck` (0 = не видит — по документации не подтверждено), считается ли `setChainedMode` пленом для world state, сохраняется ли ключ в сейве.
- Офлайн-тест `_dev/test_conductor_v2.py`: 360 дней — 11 событий. Лидер на экране / вне окна / рядом с игроком — не применяется, при перезагрузке вдали — применяется. Состояние v2 несовместимо с v1 (VERSION=2 → новый журнал).

## v1 (2026-11-12) — живой мир: состояния, шина событий, utility-AI, договоры (интегратор)
Данные: `tools\conductor\gen_conductor.py` → `rules\conductor.json` (94 фракции: города по LORE_MAP, центры по координатам городов из leveldata ванили и модов, отношения, соседи по расстоянию, богатство и сила на старте, амбиции; 6 реликтовых; игрок «Nameless»; 99 пар «город — лидер»; все параметры — секция `params`).
Скрипт: `build\KMM_Conductor\scripts\init\KMM_Conductor.lua` (VERSION 3, состояние в сейве `data_string["kmm_conductor_state"]`).

**Модель**
- **Тик раз в 5 дней:**
  - экономика: доход городов и торговых договоров минус содержание силы (у мобилизованных ×3), дань вассалов;
  - режимы реликтовых;
  - пересмотр договоров: расхождение интересов, срок;
  - действия фракций с шансом 0.15.
- **Реликтовые** (Imperial Remnants, Astartes, Necrons, 3 фракции Хаоса).
  - focused — почти не действуют, города не захватывают.
  - mobilized (сила ×1.6, содержание ×3) — только по поводу извне:
    - на них напали (ответ на их собственную агрессию не считается);
    - потеря города;
    - угроза цели (Хаос рядом для охотников на Хаос);
    - кризис (распад союзника).
  - Без повода 60 дней — возврат в focused.
- **Шина событий.** Рейд, захват или нападение расходится к соседям (радиус 120 000):
  - страх: оборона стоит силы;
  - оппортунизм: ослабшую жертву бьют чаще 20 дней;
  - общий враг сближает.
- **Utility-выбор:** рейд, захват (сила ≥ 1.25 × защитника), торговля, союз, вербовка, затаиться. Веса — по амбиции (расширение / обогащение / выживание / месть / вера); «усталость от войны» 20 дней.
- **Договоры:** ненападение, торговля, оборонительный пакт, военный союз, вассалитет.
  - Заключаются из-за общего врага, выгоды или страха.
  - Рвутся при расхождении интересов или по сроку.
  - Обязательства: на союзника напали → помощь по силам (не чаще раза в 30 дней на договор), иначе — неисполнение и удар по доверию.
  - Измена ослабшему союзнику (3 %) надолго роняет доверие.
- **Игрок** — такая же сторона договоров. Союз ему предлагают фракции с отношением ≥ 40 при общем враге. Реальное нападение на игрока ловится колбэком `Character::_NV_hitByMeleeAttack`, после чего срабатывают обязательства союзников и отправка отряда.

**Материализация в игре** (всё под pcall, флаги в `params.materialize`; **ничего из этого в игре ещё не проверено**)
- **Отношения фракций:** `FactionRelations:setRelation` (обе стороны) — когда отношение меняется.
- **Лидеры:** смерть или плен — только в 15 с после появления лидера в загруженных персонажах и вне видимости игрока; дальше ванильный world state.
- **Союзный отряд к игроку:** `RootObjectFactory:createRandomSquad` рядом с персонажем игрока, цель — его handle (аргументы угаданы по документации).
- **Экипировка по богатству:** у загруженных неуникальных NPC вне видимости одна вещь из `wardrobe_tiers.json`, тир T1 ± 1 по богатству фракции к стартовому. Не больше 6 замен в день; при обеднении 35 % NPC её избегают — так сохранившаяся элита деградирует медленнее. Вызовы: `gamedata:getData` + `theFactory:createItem` + `Inventory:addItem/equipItem`.

**Тесты (офлайн, LuaJIT из KenshiLua)**
- `tools\conductor\test_player_ally.py`: на 25-й день UC заключает военный союз с игроком; нападение на игрока → `ally_help` + отправка отряда.
- `tools\conductor\sim_years.py 5 <seed>`: прогон на 5 лет — сводка ниже (seed 2026). Seeds 7 и 99 дают похожие числа.

**5 лет (seed 2026):** 1195 событий; рейдов 565, захватов городов 26.
- Выросли: Skin Bandits (3→4 городов), Astartes survivors (1→3 городов), The Holy Nation (35→55 городов), Dust Bandits (4→4 городов), Dark Reavers (5→5 городов).
- Пали: Skeleton Bandits, White Wolves, Greenskins, Rusty Raiders, Anti-Slavers. Лишились всех городов: Nameless, Guild of Surgeons, Space Necromancer - Sora Dynasty, Western Hive.
- Договоров заключено 182 (defense: a common enemy 7, trade: mutual gain 123, vassal: fear 3, nonaggression: a common enemy 38, military: a common enemy 11); активных к концу 71.
- Разорвано: term expired 81, unfulfilled obligation 6, seized an opportunity 13; предательств 19; помощь союзникам 131, отказов 8.
- Мобилизаций реликтовых 51: Space Necromancer - Sora Dynasty 16, Imperial Expedition Remnants 14, Astartes survivors 6, Lost Chaos Space Marines 5, World Devourer War Gang 6, Midnight Lord 4.
- Известный перекос: Holy Nation во всех прогонах растёт с 35 до ~55 городов — требует настройки (лимит экспансии или сопротивление).

## v1.1 — баланс против снежного кома и test_mode (2026-11-12)
- **Город ≠ владение.** TownType 2/5/6/7 → город (66), 0/1/3/4/9 → владение (фермы, аванпосты, лагеря). `town_info` и `capital` (город у центроида) — из `gen_conductor.py`. Доход: город 8, владение 2; потолок силы: город +10, владение +3.
- **Содержание городов** растёт с их числом (`city_upkeep_base × (1 + n × city_upkeep_scale)`) и расстоянием до столицы (`dist_upkeep` на 100 000 ед.). Город брать труднее (`unrest.city_capture_mult` 0.7).
- **Волнения.** Захваченный город получает unrest 1.0 (−0.02 за тик). Шанс мятежа = base × волнение × (1 + расстояние/100k) × (1 + 0.05·городов) × (1 − гарнизон). Мятеж возвращает город прежнему хозяину, а если тот погиб — город становится свободным (`S.free`, действие `capture_free`). Событие `revolt`.
- **Реликтовые:** сила не падает ниже `relic_floor` (0.5) × стартовой. Мобилизация их не добивает.
- **Прогон 5 лет** (сиды 2026/7/99): максимальная доля городов 23/24/21% (цель ≤ 25%), мятежей 21/10/15, захватов 26–36, все 6 реликтовых живы. Тренд: Святая Нация +1 город/год → на горизонте 10 лет проверить.
- **test_mode** (`params.test_mode`): один раз на мир (`S.test_done`), через 20 с после появления персонажей, шаги раз в 40 с: 1) setRelation с проверкой и возвратом, 2) createRandomSquad самой дружественной фракции у игрока, 3) смена вещи у ближайшего неуникального NPC, 4) setChainedMode и declareDead двух неуникальных NPC в радиусе 4000 (лидеры не трогаются), 5) форсированный major_event. Результат каждого pcall → `logs\debug.log`. Офлайн-проверка на заглушках: `tools/conductor/test_testmode.py`. **После теста флаг выключить.**

## v2 — шаг 1 офлайн-билда (2026-11-12)
Мир v2 в `KMM_Conductor.lua` (блок «мир v2»): `seed_world` (семя новой игры), `ore_step` (Пик руды), `flows_step` (наркотики, рабы, краденое, еда), `start_succession`/`succession_step`, `shards_step`/`REMNANTS` (осколки, варлорды), `chaos_step`, `free_step`; действия `raid_base`, `expedition`; события `player_raid`/`ally_joins`. Параметры — `rules\conductor.json` → params: seed, ore, flows, succession, shards, chaos, player_base, traces, self, guard.
Рантайм рядом: `KMM_Traces.lua` (следы у игрока, цены, база, первый час), `KMM_Self.lua` (бегство, сдача, избегание сильных). Тесты: `tools\conductor\sim_years.py 15 <seed>` (критерии живости), `tools\test\test_runtime.py` (заглушки игры, 14 проверок), `tools\conductor\test_testmode.py`.
Прогон 15 лет (сиды 2026/7/99): максимум доли городов 21 %; живых фракций к концу 68/72/75; расколов 20/27/10, варлордов 26/25/8, договоров 444/423/430, мятежей 155/94/130; рудный кризис на 4.0/4.6/4.4 году; захватов за последние 5 лет 54/30/70; все реликтовые живы.

## Шина подписчиков, слоты склада/города, lua_lint (2026-11-12, INTEG)
- **Подписка:** `KMM_Conductor.subscribe(pattern, fn) → id`, `KMM_Conductor.unsubscribe(id) → true|false`. `pattern` — точный `type`, префикс с `*` (`"stock_*"`, `"town_*"`) или `"*"`; `fn(ev)` вызывается из `emit` после хроники и внутренней шины, каждый под своим `pcall`. Первая ошибка отключает только этого подписчика (причина → `logs\debug.log`). Повторный emit изнутри подписчика раздаётся не глубже 4 уровней. `ev` только читать.
- Сюда подпишется будущий директор сценария. Для него есть кольцо `RECENT` из последних 64 событий: в сейв не пишется, никто его не читает.
- **emit:** `ev.type` обязателен (строка), иначе ошибка (её ловит guard вызывающего). События `stock_*`/`town_*` идут той же дорогой, что и все: `S.events` (300), `chronicle.log`, шина, подписчики.
- **Внимание:** у дирижёра есть свои `town_captured` и `town_rejoined`, и подписка `"town_*"` получит их тоже.
- **Состояние:** `S.stock = {}` и `S.town = {}` создаются в `fresh_state` и сохраняются в `sdata` вместе с `S`. Старое состояние (VERSION 4 без слотов) получает их при загрузке и в `advance` (`ensure_slots`).
- **API:**
  - `stock_state()` → `S.stock`;
  - `town_state()` → `S.town`;
  - `day()` → текущий день мира;
  - `towns()` → список `{sid, name, kind, x, z, mine, owner, free, unrest, pop}`, где `pop` берётся из `S.town[sid].pop`, если TOWN его пишет.
- `math.randomseed(os.time())` перенесён с верхнего уровня в первый тик.
- **Офлайн-прогон со складами:** `tools\conductor\sim_years.py 15 <seed> [--stub|--no-stock]`.
  - Модель берётся из `build\KMM_Stock\scripts\kmm_stock_model.lua`, если файла нет — заглушка `tools\conductor\stock_stub_model.lua`. `M.day` вызывается раз в игровой день; ошибка модели отключает склад до конца прогона.
  - Метрики в `out\sim_15y_<seed>[_stub|_nostock].json` → `stock`: запасы по категориям за год, доля городов в дефиците/переполнении (пороги модели `deficit`/`overflow` × T), топ городов и владельцев по запасу, `snowball`, `chronic_*`, металл вокруг рудного кризиса, число `stock_`/`town_`-событий и их доля в журнале.
- **Тесты:** `build\KMM_Conductor\_dev\test_conductor_bus.py` — 26 проверок (паттерны, отключение сломанного подписчика с записью в debug.log, отписка, петля, слоты в сейве, старое состояние, `towns()`/`day()`).
- **Линтер:** `tools\build\lua_lint.py` проверяет `build\KMM_*\scripts\**\*.lua`: синтаксис (lua51.dll), разрешённые `Events.on` на верхнем уровне, `guarded(…)` у каждого обработчика, нет `io.open`/`os.*` на верхнем уровне, нет `data_string`.

## CORE: петля склад->дирижёр, население, знание (stream CORE)
- Детерминизм: sim_years.py подменяет `pairs` на отсортированный (порядок хеша строк в LuaJIT менялся между запусками); в игре сид по-прежнему os.time().
- Склад публикует `s.lv[cat]` (доля нормы) и `s.tn[cat]` (норма). Дирижёр раз в тик считает f.lvl/f.food_def/f.metal_def (P.loop: def_below, food_mix 0.35, metal_mix 0.25) и подмешивает в hunger/stress.
- API: `KMM_Conductor.price_mult_town(fid, town_sid)`, `KMM_Conductor.know(fid)`. Действия trade_for / raid_surplus (P.loop: trade_for_w, raid_surplus_w, cooldown_days, surplus_lv, need_min, ship, raid_take). События: trade_for, raid_surplus, refugees{town_sid,town_name,n,a,why}, relic_salvage, relic_forge_known.
- Население S.town[sid].pop/pop0 (P.pop: grow, starve, sack_loss, cap, min_share); потребление склада масштабируется pop/pop0.
- Входящие от PLAYER: player_sold{town_sid,cat,n[,added=true если add уже вызван]}, caravan_lost{a,town_sid,to_sid,by}, player_relic_forge{item}.
- f.know (0..3, P.know) и f.relic_parts (= f.components): регенерация знанием, износ в mobilized, salvage; при parts < weak_below сила тает.
- Тест: build/KMM_Conductor/_dev/test_conductor_core.py.

## ROBBERY: засады, сбыт добычи, переодевание (2026-11-12)
- Действие `waylay` (дирижёр): A грабит путников B, если rel(A,B) <= P.robbery.rel_max (-15), нет договора, у A есть мотив (нужда: дефицит еды/металла, бедность, голод; жадность: enrichment/без городов; месть: B недавно била A — `f.wronged[B]`), кулдауны `cooldown` 14 д / `pair_cooldown` 50 д. Груз — доля `take` склада города B (не ниже `keep` нормы) → `S.loot[A]`; rel и trust падают. Событие `waylay {a, b, town_sid, town_name, cat, n, why}`.
- Сбыт: через `sell_days` запись добычи идёт в ближайший город владельца с rel >= 0 (или свой / скупщик ROLE.fences; незаконное для владельца — только у скупщиков). Склад города + n, богатство A + n*цена*sale_k, жертва охладевает к покупателю. Событие `loot_sold {a, b=жертва, owner, town_sid, town_name, cat, n, contra?}`. Нет города — после `max_age` добыча тает (`stats.loot_melted`).
- Броня/оружие добычи бедного грабителя (gear_shift < 0) на `keep_gear` оседает на нём; накопив `gear_need`, gear_shift -> 0 с паузой `gear_grace`.
- API: `KMM_Conductor.loot_add(fid, cat, n, victim_fid)`, `loot_of(fid)`, `waylay_ok(a, b)`; тест-крючки `_waylay`, `_loot_step`. Параметры — P.robbery (дефолты в Lua, `RB_DEF`).
- Рантайм KMM_Traces: до 12 отрядов в драке (чужие лежат рядом, не у игрока), опрос каждые 6 с; прирост инвентаря (категории по `KMM_Stock.item_cat`, иначе scrap/lux по цене) при уходе отряда -> `loot_add` + `loot_carried {a, b, n}` один раз. Лучшая броня/оружие (таблица `gear_scores.json` из `tools/conductor/gen_gear_scores.py`: sid -> [score, group, flags]) надевается (ratio 1.3, ≤2 за проход, ≤1 на NPC/60 с, не WH, Whistler Suit только Whistler); надетое не продаётся, снятое — добыча.
- Тесты: build/KMM_Conductor/_dev/test_robbery.py (49 проверок). Калибровка: tools/conductor/sim_years.py -> criteria.robbery.
