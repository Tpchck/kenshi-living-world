# ORE — поток F: истощение рудных узлов на KenshiLua (2026-11-11, v0)

## Вердикт
Перехват возможен частично: событие добычи и рычаг выхода в API есть. Прототип `build\KMM_Ore\` собран. Синтаксис проверен компиляцией через `lua51.dll` KenshiLua, в игре не запускался.
**Не хватает (одной строкой):** нет override-колбэка, который возвращает объём добычи, и нет per-instance хранилища у здания в сейве. Поэтому выход режется через поле `_resourceMiningLevel` (что оно реально влияет на выход — проверяет тест), а остаток узлов хранится в файле, а не в сейве.

## Что нашёл (KenshiLua docs, 3817000612\docs)
| Нужно | API | Тип |
|---|---|---|
| Событие добычи (игрок и NPC, шахта и дикий узел) | `ProductionBuilding::_NV_operate(self, worker: Character, amount: number)` | уведомление — менять `amount` нельзя, возврат `false` не останавливает движок (CallbacksReference: «does not interrupt C++ engine logic») |
| Рычаг выхода | `ProductionBuilding._resourceMiningLevel` (number, **RW**), `getMiningResourceLevel()`, `setupMiningResourceLevel()`, `getProductionMult()` | поле/методы |
| Повторное применение после загрузки зоны | `Building::_NV_onBuildingLoaded(self)` + `Building:getProductionBuilding()` | уведомление |
| Ключ узла | `RootObjectBase:getPosition()`, `getHandle()`, `getGameData().stringID` | методы |
| Время для восстановления | `getGameWorld():getTimeStamp_inGameHours():getTotalDays()` | метод |
| Хранение | `io.open` работает (им пользуется Children of Kenshi); `SaveManager.currentGame` (RW string), но `SaveManager.getSingleton()` в справочнике возвращает `void` — может не работать | файл |
| Override на объём выхода | **нет** (среди 212 override-колбэков нет ProductionBuilding/output) | — |

Ванильные данные (kmod, ванильная цепочка): дикий узел `Iron Rock` (FOLIAGE_BUILDING 14520 → BUILDING `14521-rebirth.mod`) — это то же производственное здание с функциональностью `Ore mine` (`world resource mining`=1, производит Raw Iron), что и шахты. Поэтому одно событие покрывает и ручную добычу у узла, и шахты игрока, и NPC.

## Прототип (`build\KMM_Ore\`)
- `scripts\init\kmm_ore.lua`: на каждое `_NV_operate` списывает `amount` с запаса узла R и ставит `_resourceMiningLevel = base · max(floor, (R/R0)^k)` (LATE_GAME.md: yield = y0·(R/R0)^k). `base` — ванильный уровень при первом контакте. Восстановление (`regen_per_day`) — только для рудников. После загрузки здания уровень выставляется заново. Все вызовы непроверенного API обёрнуты в pcall, ошибки пишутся в лог, игра не падает.
- `scripts\ore_config.lua`: шаблоны (только руда: Iron Rock, Iron/Copper Resource, Small Iron/Copper Resource из Boneyard Wolf — `surface`; Ore Mine I–III, Ore Drill I–III — `mine`), классы `surface` (R0 20000, k 1.5, floor 0, без восстановления) и `mine` (R0 60000, k 1.0, floor 0.25, +200/день). R0 — гипотезы: масштаб `amount` неизвестен, калибровать по логу.
- Лог: `C:\KenshiModMap\logs\ore.log` (NEW node, MINE раз в 200 операций с `amount`, R, коэффициентом и уровнем «до → после», DEPLETED, ERROR). Состояние: `C:\KenshiModMap\logs\ore_nodes_<сейв>.tsv` (или `_global`, если имя сейва недоступно).
- `.mod` для лаунчера создаёт генератор интегратора (`kmm_build.py`, Lua-поток `ore`).

## Тест (интегратору)
1. Поставить `KMM_Ore` (после KenshiLua в mods.cfg), загрузить сейв, покопать Iron Rock или дать поработать шахте 1–2 игровых дня.
2. В `ore.log`:
   - есть `KMM_Ore v0 loaded` и `save_key` (если `global` — `SaveManager` не отдал имя);
   - строки `MINE … level X -> Y` с Y < X — поле записывается;
   - главное: падает ли реальный выход Raw Iron на узле (сравнить скорость наполнения до/после или поставить R0 маленьким, например 50, чтобы узел «умер» за минуты).
3. Перезагрузить сейв — `nodes in state=N` > 0 и уровень после `onBuildingLoaded` снова пониженный.
Если выход не меняется — в API нет рабочего рычага, и тогда истощение возможно только C++-плагином (спайк 5 в CORE.md §12).

## Ограничения / риски
- Состояние в файле, а не в сейве: откат на старый сейв не откатывает истощение. Если `save_key` = global — одно состояние на все сейвы.
- `_resourceMiningLevel` может пересчитываться движком при каждом обновлении. Тогда эффект держится только между операциями — проверка по логу «до → после».
- Камень, вода, фермы не трогаются.

## v1 (2026-11-12, шаг 1 офлайн-билда)
Включён в mods.cfg. Обработчики под guard (ошибка → отключение до конца сессии, debug.log). Поверхностная жила не умирает в ноль (floor 0.02). Стартовый запас нового узла = R0 × остаток жил региона в мире дирижёра (`KMM_Conductor.region_ore`), добыча игрока × 0.05 списывается с ближайшей жилы мира (`player_mined`). Состояние узлов — `logs\ore_nodes_w<семя мира>.tsv` (новая игра — свои узлы). Абстрактная руда фракций, рудники, переплавка и кризис — в дирижёре (CONDUCTOR.md v2).

## v2 (2026-11-12) — руда заново, безопасный путь
**Почему падал v1 (вероятно; след падения не сохранился — `KenshiLua.log`/`RE_Kenshi_log.txt` перезаписаны следующими запусками, `ore.log` пуст).** v1 при загрузке скрипта вешал `Building::_NV_onBuildingLoaded` и `ProductionBuilding::_NV_operate`. Это перехваты внутренних функций движка; `onBuildingLoaded` вызывается на каждое здание во время загрузки сейва/зоны (вероятно, в потоке подгрузки), то есть Lua-VM входит из чужого потока параллельно с `charsUpdate` других скриптов. Такое падение нативное, `pcall` его не ловит. В обработчиках было и тяжёлое: файл состояния читался в первом вызове, `getMiningResourceLevel()` — метод с пересчётом движком.

**Что в v2** (`build\KMM_Ore\scripts\init\kmm_ore.lua`, `scripts\ore_config.lua`; v1 — `_dev\kmm_ore_v1_backup.lua.txt`):
- При загрузке скрипта только объявляются функции и таблица `KMM_Ore`, плюс один обработчик общего тика `GameWorld::charsUpdate` — того же, что у Conductor/Traces/Self/Rumors. Новых хуков движка нет. Ни I/O, ни вызовов API игры при загрузке (проверено тестом).
- Ленивый старт. Конфиг (`require "ore_config"`) читается в первом тике. Работа начинается, когда у игрока есть персонажи и прошли все три условия: ≥8 опросов подряд, ≥8 реальных секунд, ≥0,05 игрового часа (игра не на паузе). Если персонажи исчезли (загрузка другого сейва, меню), поток снова ждёт.
- Без перехвата добычи. Раз в `poll_seconds` по кругу проверяются `chars_per_poll` персонажей игрока: `ch:getBody():getCurrentAction()` (TaskType 87/152) → `.subject` (hand) → `getBuilding():getProductionBuilding()` → шаблон из `templates`, персонаж ближе `work_radius`. Его игровые часы с прошлого опроса (не больше `max_dt_hours`) списываются с запаса узла R. Единица R — «работо-час». Выход: `_resourceMiningLevel = base·max(floor,(R/R0)^k)`. `base` — значение поля при первом контакте (поле, а не метод), пишется только при изменении. `write_level=false` — режим «только наблюдение».
- Дирижёр: запас нового поверхностного узла = R0 × `KMM_Conductor.region_ore` (не ниже `region_min`). Труд игрока × `player_to_world` списывается с ближайшей жилы мира (`player_mined`). Ошибка связи отключает только связь.
- Guard: любая ошибка Lua в тике отключает поток до конца сессии, строка `[KMM_Ore] tick disabled until restart: …` пишется в `logs\debug.log`, исключение наружу не выходит. Ошибка `getPlayerInterface` в меню считается состоянием «не готов», а не сбоем.
- Состояние: `logs\ore_nodes_<w семя|global>.tsv` (сохраняется не чаще раза в `save_every_seconds` и при смене мира), лог — `logs\ore.log`. Консоль: `KMM_Ore.status()`, `KMM_Ore.save()`.
- Выключатели в `ore_config.lua`: `ore_enabled`, `write_level`, `feed_conductor`, `tick_source` (`own` | `conductor`), `world_key` (`conductor` | `global`). Калибровка: surface R0 400 работо-часов (k 1.5, floor 0.02), mine R0 1200 (+24/сутки, floor 0.25).
- `rules\streams\ore.json` не нужен: генератор для Lua-потоков читает только папку `build\KMM_Ore\scripts`, параметры лежат в `ore_config.lua`.

**Подключение.** В `mods.cfg` — после KenshiLua и после KMM_Conductor (порядок загрузки скриптов на работу не влияет: `KMM_Conductor` берётся лениво в тике). Строка в дирижёре не нужна. Если нужен единый тик (`tick_source = "conductor"`), в конец `on_tick` в `KMM_Conductor.lua` добавить: `if KMM_Ore and KMM_Ore.tick then KMM_Ore.tick() end`.

**Офлайн-проверки.** `python -I -X utf8 build\KMM_Ore\_dev\test_ore.py` (LuaJIT `lua51.dll` KenshiLua, заглушки API, <5 с): 12/12. Покрыто: синтаксис; загрузка без I/O и API; «сейв грузится, персонажей нет» — ничего не происходит; задержка старта; истощение, запись уровня и файла; фильтры (далеко / не та задача / не руда); порции; ошибка API → отключение и запись в debug.log без исключения; меню без интерфейса; ошибка дирижёра; `ore_enabled=false`; `tick_source=conductor`; смена мира и перезагрузка. `kmm_build.py --write ore` — без ошибок, `KMM_Ore.mod` записан.

**Риски.**
- Не проверено в игре: (1) `getCurrentAction().subject` у шахтёра указывает на здание узла, в том числе у FOLIAGE Iron Rock; (2) запись `_resourceMiningLevel` реально меняет выход (вопрос открыт с v0).
- Учитывается только труд персонажей игрока. Автоматические буры без рабочего и NPC-шахтёры не считаются (добыча мира — абстрактно в дирижёре).
- `world_key=conductor`: сейчас `KMM_Conductor` не пишет состояние в сейв (`data_string` = nil в KenshiLua.log). Значит, после каждой загрузки у мира новое семя, и узлы начинают с полного запаса. Пока это не исправлено, для переноса состояния между загрузками нужен `world_key="global"`.
- Если бинды вернут не nil, а «пустой» userdata для отсутствующего действия или здания, нативный вызов на нём pcall не поймает. Защиты: `h:isValid()` перед `getBuilding`, выключатель `ore_enabled`.
