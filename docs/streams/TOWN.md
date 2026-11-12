# TOWN — «Город за работой» (2026-11-12)

Поток данных `tools\streams\town.py` + `rules\streams\town.json` → `build\KMM_Town\KMM_Town.mod`; Lua `build\KMM_Town\scripts\init\kmm_town.lua` + сгенерированные данные `scripts\kmm_town_data.lua` (как KMM_Diplo: данные и скрипты в одной папке).

## 1. Данные: расписания жителей
В ванили нет AI_SCHEDULE в работе (0 ссылок): расписание — это окна часов у целей AI_PACKAGE (`Leader/Squad/Squad2 AI Goals`: val0–val1 часы, val2 вес), пакет отряду даёт `SQUAD_TEMPLATE → AI packages` (val0 приоритет). Поэтому:
- **Новый AI_TASK** «KMM go to the bar and drink» (`GO_TO_THE_BAR_AND_DRINK` = 154; в ванили записи-задачи нет; «hang out in a bar» использует RELAX_IN_TOWN_PACKAGE).
- **21 новый AI_PACKAGE**: клон исходного пакета (все цели и addon-наследования остаются) + цели расписания из ванильных AI_TASK: работа у машин `AUTO_LABOURING_MINES` (5261), подмастерье у верстака `AUTO_LABOURING_MINES_PRETEND` (43932), склад `PUT_LOOT_IN_STORAGE` (5232), патруль `PATROL_TOWN` (965 / fluff 57336), покупки (969), «посидеть» `SIT_AROUND` (96454), сон `GO_HOME_AND_GO_TO_BED[_SECURE]` (3105 / 46053) + «проснуться при тревоге» (12607), бар (новый).
- Роли и варианты (по 2 на роль + доля отрядов остаётся ванильной; выбор — crc32(sid отряда)):
  | роль | исходные пакеты | варианты | отрядов изменено / ваниль |
  |---|---|---|---|
  | worker | working mines and farms, building resident workers2/guards1, worker fighter indie, Farmer village | early (смена 5–13, бар 16–21, сон 21–5) / late (12–20, бар 20–24, сон 0–8) | 34 / 18 |
  | craftsman | Shop-24hr, shop external, Shop, farm shop (только НЕ торговые отряды) | bench_day / bench_late (верстак, склад, бар) | 3 / 3 |
  | civilian | Civilian, stay in home relaxing | homebody / outgoing | 20 / 14 |
  | bar_regular | hang out in a bar | day_stroll / night_owl | 136 / 83 |
  | watch | patrol town 24hr | night_shift / day_shift (отдых: бар + сон) | 13 / 10 |
  | PCR | citizen lives, citizen patrolmen | family_day / family_evening; patrol_day / patrol_night | 4 / 0 |
  Итого **210 отрядов-жителей** (TOWN/FACTION residents и bar squads, их housemates) из ~640 городов/поселений данных. У «citizen lives» PCR не было сна, вожак патрулировал ночью — ночной патруль вожака убран, добавлены бар и сон (их дом — бар, кровати бара).
- Не трогаются: торговые/караванные (`is trader`, roaming squads — ECONOMY; так отсеяно 220 отрядов, в т.ч. почти все «Shop»), записи KMM_*, TOWN, FACTION, здания, мебель, BUILDING_FUNCTIONALITY, чужие town override.

**Изменяемые поля существующих записей:** только `SQUAD_TEMPLATE` категория ссылок `AI packages` (210 записей; исходный пакет → вариант с тем же приоритетом, удаление+добавление в одной дельте). Других потоков на этом поле этих записей нет (ECONOMY меняет его только у Town Thief — не житель-цель; проверка пересечений = 0).

## 2. «Склады ресурсов» кухонь и мастерских (приём LKO)
LKO на диске нет. По fcs.def/ванили: стол/плита/верстак берёт сырьё из мебели с `BUILDING_FUNCTIONALITY.function = BF_RESOURCE_STORAGE (2)` и `BUILDING.limit inventory` (ITEM) — так устроены «Food Store», «Storage: Iron Plates» и т.п. (общая функциональность `1518-gamedata.base`). Ящики городов — `BF_GENERAL_STORAGE (13)` (`2950-gamedata.base`, 383 здания: Small Crate, Barrel A, General Storage Chest…). Пометить их складом ресурсов данными можно только правкой ванильной мебели/функциональности (общие с игроком — изменят и его сундуки) или правкой интерьеров/планировок городов — **запрещено, не делал**. Поля, которые понадобились бы (НЕ меняю, интегратору на решение): `2950-gamedata.base` «function» 13→2 и/или `BUILDING` «limit inventory» конкретных ящиков. Рекомендую не делать. Замена: материальный поток ведёт Lua по складу города (п.3), «ящик мастерской» = инвентарь машины, у которой работает мастер. Рантайм-вариант (поля `Building.specialFunction/designation` RW в KenshiLua) не использован: не проверено, может попасть в сейв.

## 3. Lua: мастер → ящик → носильщик → лавка/караван
- Старт по схеме KMM_Ore v2: при загрузке только обработчик `GameWorld::charsUpdate`; ничего, пока нет персонажей игрока; задержка 10 с + 10 опросов + 0.05 игрового часа; данные/конфиг лениво.
- Опрос раз в 2 с, цикл цепочки раз в 30 с, только если персонаж игрока в известном городе (override-город → исходный sid). Скан ≤ 80 загруженных персонажей, в радиусе 2500 от персонажа игрока и в том же городе.
- Мастер = NPC с текущим действием работы у машины (AUTO_LABOURING_MINES[_PRETEND], OPERATE_*), машина из данных (208 машин → категория склада + продукт ITEM: еда, металл, медицина, наркотики, роскошь, скрап; оружие/броня — без материализации). Склад даёт 1 единицу (`level ≥ 0.25` и `take`) → предмет в инвентарь машины (или мастера); нет запаса → `town_shortage` (раз в 12 игровых часов на город/категорию).
- Носильщик = свободный NPC рядом: предмет из ящика к нему; через 40 с — лавочнику (житель-торговец) или каравану (торговец не житель, доля 0.35). Ходьбу не приказываем (это плагин) — видно по инвентарям.
- Лимиты: ≤ 3 мастера и ≤ 3 предмета за цикл, ≤ 2 носильщика одновременно, очередь ящика ≤ 6.
- События в шину `_G.KMM_Conductor.emit`: `town_craft`, `town_haul`, `town_delivered`, `town_caravan_loaded`, `town_shortage` (поля town_sid, town_name, cat, item, n, text).
- Guard на каждую функцию (`tick`, `find_town`, `scan`, `craft`, `haul`, `deliver`, связи `stock_link`, `conductor_link`): первая ошибка отключает только её, причина → `C:\KenshiModMap\logs\debug.log`. Своего сейва нет; счётчики — `S.town[town_sid].vis` через `KMM_Conductor.town_state()`.

## 4. Что нужно от других
- **Дирижёр (INTEG):** уже есть всё: `emit` с `town_*`, `subscribe("town_*")`, `town_state()`. Опционально — слухи/хроника по `town_caravan_loaded`/`town_shortage`.
- **STOCK:** опубликовать `_G.KMM_Stock = { level(town_sid, cat) → доля нормы или nil, take(town_sid, cat, n) → взято, add(town_sid, cat, n) }` поверх `S.stock` (то же, что `M.level/take/add` модели без аргумента stock). Категории: food, metal, weapons, armor, med, drugs, lux, scrap. Пока API нет — Lua тихо ждёт. Материализация списывает единицы склада (1 предмет = 1 единица) — производство остаётся за STOCK, двойного счёта нет.

## 5. Регистрация (делает интегратор)
- `tools\build\kmm_build.py` DATA_STREAMS: `("town", "KMM_Town")` после `("diplo", "KMM_Diplo")`, перед `("fix", "KMM_Fix")`.
- `rules\load_order.json` kmm: `"KMM_Town"` после `"KMM_Diplo"` (перед `KMM_Conductor`). Зависимости .mod: ваниль + моды отрядов, включая CitizensRedux.mod (EXTRA — выше KMM).

## 6. Проверки офлайн
- `python -I -X utf8 tools\streams\_town_check.py` (14 с): поверх всех текущих потоков данных — 232 записи (21 AI_PACKAGE, 1 AI_TASK, 210 изменённых SQUAD_TEMPLATE), 0 ошибок fcs.def, 0 float не-F32, 0 битых ссылок, 0 пересечений полей, изменения только «AI packages», round-trip ✓.
- `python -I -X utf8 build\KMM_Town\_dev\test_town.py` (<1 с, lua51.dll KenshiLua): 13/13 — синтаксис; загрузка без побочных эффектов; нет персонажей → ничего; ленивый старт и цепочка до лавки и каравана; лимит мастеров/носильщиков/очереди; без KMM_Stock тихо ждёт и оживает при появлении; ошибка API скана/склада отключает только своё + debug.log; вне города / дальние NPC / город без склада — ничего; shortage один раз.

## 7. Что покажет только игра
Выбор цели при равных весах и окнах через полночь у новых пакетов; работает ли `GO_TO_THE_BAR_AND_DRINK` у NPC-жителей (запись своя, ванильного аналога нет); идут ли bar-squads спать в кровати бара; работает ли PRETEND у подмастерьев на верстаках лавок; `getCurrentAction().subject` для машин, `Building:getInventory()` у машин, `isATrader/isResident` для отличия лавки от каравана, `Town:isTown():getOriginalGameData()`; видно ли игроку перемещение предметов без ходьбы.
