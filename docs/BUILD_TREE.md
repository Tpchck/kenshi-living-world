# BUILD_TREE — меню построек и дерево исследований (поток BUILD, 2026-11-16)

Файлы: генератор `tools/streams/build.py`, правила `rules/streams/build.json`, тест `tools/streams/test_build_menu.py`.
Поток идёт сразу после `tech` (`tools/build/kmm_build.py` DATA_STREAMS) и видит слитую цепочку ваниль → 663 мода → KMM_Tech.
Новых записей поток не создаёт: только дельты к существующим RESEARCH и BUILDING.

## Как игра решает, что видно в меню

- Постройка видна игроку, если её открывает изученное исследование (`RESEARCH.enable buildings`). Не открытые ни одним
  исследованием постройки (дома городов, NPC-мебель) в меню не попадают. ✓данные (ванильные NPC-постройки не в исследованиях),
  ✓код: `Research::isBuildingResearched` (Research.h:53).
- Пункт меню = вкладка `building category` + группа `building group`; варианты одной группы листаются стрелками
  (`BuildModeWindow::BuildingGroup`, `buildingTypePrev/Next`, gui/BuildModeWindow.h). Ваниль так держит Stone Mine I–VI, Camp Bed.
  Поля только для интерфейса (fcs.def: «category it is listed in»).
- Старт владельца Castaway (fix.json survival_start) не задаёт research. Как и у Rock Bottom, остаётся ванильный `_Default Start`
  (5359-gamedata.base). ? движок, по данным ванильных стартов.
- Исследование `blueprint only` без продавца чертежа не появляется (ванильный носитель знания: лавки, NPC).

## Правила (build.json)

| Код | Правило | Рычаг |
|---|---|---|
| D1 | Точный клон (всё совпадает, кроме имени, описания, раскладки, цены; функция по содержимому, instances тоже) — виден только канон | ссылка снимается из enable buildings; исследование клона получает канон |
| D2 | Почти-дубль — один пункт меню. Ключ: рабочая постройка (добыча, стол исследований, производство, генератор, кровать, тренировка, прилавок, верстак, печь, турель, батарея, ремонтная койка, ферма) — функция без меша; склад с лимитом — «что хранит»; декор, свет, мебель — набор мешей | `building group` (+ `building category`) |
| L | Раскладка модов «Buildings Category Tweaks - *» главнее: если последний писатель категории или группы — BCT, поле не меняем. Свободные варианты встают во вкладку и группу BCT | — |
| C | Сведение разнобойных вкладок: SC * → ванильные, 储具/Storage → STORAGE, Beekeeping, Cloaks, FIRELOCKS, =Trash= → FURNITURE - Trash, WH40k-вкладки и станки KMM_Tech → одна вкладка RELICS | `building category` |
| R1 | Одна постройка — одно исследование между разными семействами (ваниль = 4 ванильных файла). Остаётся самое раннее: старт → level → исследование мода постройки → ваниль. Внутри одного семейства дубли — замысел автора (Flour Storage в трёх ванильных), не трогаем | enable buildings |
| R2 | Тупик (нет содержимого, не предпосылка, не повышение уровня) прячется | `blueprint only` |
| R3 | `is level upgrade` только у ванильных Tech Level; у Sensible Training (Dodge/Martial Arts III) и Soulbody (SC Automatic Flour Grinding) снят — иначе поднимали уровень стола в обход книг | значение |
| R4 | Реликтовые: моды wh40k_imperial_forces, TEXT TEXTURE (40K Related Research), 40K Necrons, Death Korps of Krieg и категории /40K|WH40k|Necron/ → level 6, категория Relics, корни требуют Relic Studies (KMM_Tech). Бесплатные получают цену: Ancient Science Book ×6, Engineering Research ×4, 20000 | level, category, requirements, cost, money |
| R5 | Чужие технологии (Soulbody, кристаллы душ) — не раньше уровня 4 | level |
| R6 | level ≥ level предпосылок; потребитель энергии не раньше первого генератора. Уровни только поднимаются. Цель улучшения раньше базы ошибкой не считаем (ваниль строит её напрямую) | level |

## Итог по слитой цепочке (офлайн-прогон всех потоков в памяти)

| | было | стало |
|---|---|---|
| построек в меню (записей) | 5134 | 5126 (8 точных клонов скрыто) |
| пунктов меню (вкладка+группа) | 1583 | 1573 |
| вкладок | 83 | 53 |
| классов почти-дублей в разных пунктах | 452 нарушений категорий, 194 групп | 0 (257 классов сведены) |
| исключения раскладки BCT (дубль в двух закреплённых вкладках) | — | 10 (напр. Camp Storage в CAMPING и склады BSS в STORAGE - Old) |
| исследования ниже уровня предпосылки | 28 | 0 |
| модовые «повышения уровня» | 3 | 0 |
| реликтовые не за Relic Studies | 22 | 0 |
| перекрёстных ссылок исследований на одну постройку снято | — | 144 |
| исследований-тупиков спрятано | — | 1 (Primitive Tech, Less Early Raids: всё его уже даёт старт) |

Пунктов почти столько же: точные дубли и разбросанные варианты сведены (склады еды/руды из ванили, BSS, Soulbody, Forgotten
Buildings — в одном пункте), а витринное оружие Clutter перегруппировано из групп «по сорту» в группы «по оружию» (сорт листается
стрелками). Ванильные уровни сдвинулись только у двух исследований, которые Crafting Redux поставил за свои ступени
(Advanced Weapon Smithing → 4, Advanced Weapon Grades → 5): раньше их всё равно нельзя было изучить.

## Дерево по ступеням (уровень стола = ванильный Tech Level; число — достижимых исследований)

- **Ступень 0. Голый в пустыне** (старт, 19): Small Shack, Small Research Bench, Stone Mine, Manual Stone Processor, Torch Post,
  Camp Bed, Vegetable Farm; модовые лагерные: Primitive Shack/Stone Mine/Stone Processor/**Primitive Iron Refinery** (Less Early
  Raids), костры, тайник, сиденья и укрытия (Sensible Nomadism), погребения (Tombs), каменные кучки для пращи, походные койки.
  Руда — ручная добыча с природных узлов (Iron/Copper Resource, Iron Rock): строить не нужно.
- **Ступень 1. Ферма, быт, ручное производство** (уровень 1, 246): фермы, склады, кухня, ткань, кожа, **Iron Plates** (Manual
  Iron Refinery и Iron Refinery I–III), ветряк и топливный генератор, простые стены, кровати, Basic Weapon Smithing.
  Выход — Tech Level 2 (книги ×6).
- **Ступень 2. Ремесло и оружие** (уровень 2, 288): кожаная броня, болты, перегонка, переплавка, медицина. Выход — Tech Level 3 (книги ×10).
- **Ступень 3. Руда машинами, сталь, тяжёлая броня** (уровень 3, 286): **Ore Drill**, Steel Bars, Plate Armour, Electrical
  Crafting, батареи. Выход — Tech Level 4 (Ancient Science Book ×4: руины и Tech Hunters).
- **Ступень 4. Знание древних** (уровни 4–5, 194+83): Semi-/Fully Automatic Ore Drill, Copper Alloys, Iron Plates 5 (Refinery IV),
  гидропоника, роботехника; чужие технологии Soulbody (SC-буры, SC-плавильни, SC-склады) — отсюда. Выход — Tech Level 6 (AI Core ×2).
- **Ступень 5. Ядра ИИ** (уровень 6, 108 вместе с реликтами): мастерская выделка (Crafting Redux), скелетные конечности, Hive Cybernetics.
- **Ступень 6. Реликты**: Relic Studies → Expedition Kit → Forge-Pattern Armour / Relic Weapon Patterns → Cogitator Reconstruction →
  Relic Reconstruction → Relic Foundry Rites (KMM_Tech, вершина — ковка реликтов). За Relic Studies: WH40k Imperial Forces,
  Death Korps of Krieg, 40K Related Research (TEXT TEXTURE; цена — найденные чертежи), Necron research. Вкладка меню RELICS.

## Граница с рудой (KMM_Ore, ore_templates.lua)

Место в дереве (sid построек добычи и плавки; выход и истощение — у потока руды):
- старт: 13-Less Early Raids.mod Primitive Iron Refinery (ручная);
- уровень 1, Iron Plates: 47237-rebirth.mod Manual Iron Refinery; 42167/42168/42169-gamedata.base Iron Refinery I–III (энергия);
- уровень 3, Ore Drill: 2096-gamedata.base Ore Drill, 56977-Copper drill.mod Copper Ore Drill; Steel Bars: 5007282-Weapon Craft Training.mod Iron Beating Station;
- уровень 4: 2097 Ore Drill II, 56978 Copper Ore Drill II (Semi-Automatic), 50018-rebirth.mod Copper Alloy Bench, SC Iron/Copper Ore Drill 5008195–198/5008204–207, SC Iron Refinery 5008231/234–236;
- уровень 5: 2098 Ore Drill III (Automated), 56979 Copper Ore Drill III, 1532831-rebirth.mod Iron Refinery IV, SC Auto Drill 5008199–202/5008208–211, SC Iron Refinery II 5008237–240.
- Ore Mine I–III (2056/2094/2095) игрок не строит: исследование Ore Mining снято самой ванилью (rebirth.mod REMOVED); не возвращаем.
- Тест держит: ручная/примитивная плавка не позже автоматики. Варианты цветов SC сведены в один пункт; sid целы.

## Совместимость с сейвом (одна долгая кампания)

Сейв хранит изученные исследования и поставленные постройки по sid. Поток BUILD своих записей не создаёт, поэтому его sid не плывут.

Безопасно после старта кампании:
- менять `building category` / `building group` (только интерфейс), правила D2/C/L;
- добавлять постройки в исследования, добавлять новые исследования (в KMM_Tech — только в КОНЕЦ списков `buildings` и `research`);
- поднимать level, цену, добавлять предпосылки ещё не изученным исследованиям (изученное не откатывается);
- скрывать постройку из меню (уже поставленные стоят; новые не построить).

Небезопасно:
- удалять или переименовывать sid записей RESEARCH/BUILDING; вставлять или переставлять узлы в середине `tech.json` (ModBuilder
  раздаёт sid KMM_Tech по порядку: сдвиг поменяет смысл уже изученных sid);
- снимать постройку из исследования, которое игрок уже изучил, если другой путь к ней не открыт — она пропадёт из меню;
- менять `is level upgrade` у ванильных Tech Level и уровень стола у уже изученных ступеней;
- выключать KMM_Tech при изученных реликтовых исследованиях (их sid исчезнут из данных).

## Проверка

- `python -I -X utf8 tools/streams/test_build_menu.py` — заглушки; `--full` — слитый контекст, потоки tech+build в памяти, запись файлов
  запрещена; второй прогон build на перемешанном порядке записей даёт тот же мод.
- Полная цепочка всех потоков — офлайн-обвязкой с перенаправлением записи (как в отчёте задачи); конфликтов полей с другими потоками 0;
  fcsdef-ошибок 0, битых ссылок 0, round-trip .mod совпадает.
- Подключение к mods.cfg: в `rules/load_order.json` (список `kmm`) нужен `KMM_Build` после `KMM_Tech` — шаг интегратора.
