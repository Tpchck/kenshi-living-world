# TECH — поток «путь к реликтам через технологии», 2026-11-12
Файлы: `rules\streams\tech.json`, `tools\streams\tech.py` → `build\KMM_Tech\KMM_Tech.mod`. Проверка: `python -I -X utf8 tools\streams\_tech_check.py` (≈10 с).
Основа: LATE_GAME.md §9 (реликты воспроизводимы на нужном техуровне), DESIGN.md «Доля божественного».

## 1. Аудит Crafting Redux (audit_mods.py + поля, офлайн)
| WS id | Файл | Заголовок | Записи | Что меняет в основе | Вердикт |
|---|---|---|---|---|---|
| 3585383286 | 2PN8CraftingReduxVanilla.mod | Armor Crafting Redux - Core | 59 новых (43 RESEARCH, 4 станка) | ничего | **включить** |
| 3585385588 | 2PN8CraftingResearchPatch.mod | Armor Crafting Redux - Research Fix | 4 дельты | ванильные Plate/Leather/Chain Armour Crafting, Clothing Manufacture: `time`, `cost` −1, `requirements` +1 (→ CR Core); другие моды эти поля не трогают | **включить** (после Core) |
| 3585385029 | 2PN8CraftingReduxOMO.mod | Armor Crafting Redux - OMO | 25 новых | ничего; ссылки на OMO'S ARMOUR (в основе) и CR Core | **включить** |
| 3585385287 | 2PN8CraftingReduxEVA.mod | Armor Crafting Redux - EVA | 46 новых, 41 дельта | заменяет исследования Expanded Vanilla Armor (в основе): `REMOVED` у 23 RESEARCH EVA, 2 VENDOR_LIST, 2 ITEM (Ancient Armor Parts, Holy Historical Book); снимает их из 3 SQUAD_TEMPLATE `vendors`, Hi tech junk `items`, диалога `give item`, `blueprints` 7 списков EVA | **включить** (после Core). Остаток: `eva holy book failsafe` ссылается на удалённую книгу — висячая ссылка в списке торговца, безвредно |
| 3585386517 | 2PN8WeaponSmithingCore.mod | Weapon Smithing Redux - Core | 50 новых | ничего | **включить** |
| 3585386805 | 2PN8WeaponSmithing.mod | Weapon Smithing Redux - Edge | 3 новых, 5 дельт | WEAPON_MANUFACTURER Homemade: `cut damage mod` (= значению weapons.mod), `weapon models` +1; RESEARCH Advanced Weapon Smithing / Advanced Weapon Grades / Edgewalkers: `time`, `repeat mult`, `cost`, `requirements` (аддитивно к weapons.mod) | **включить** (после WS Core) |
| 3589917614 | 2PN8RoboticsRedux.mod | Robotics Crafting Redux: Core | 8 новых, 10 дельт | `cost` +1 у 9 ванильных исследований конечностей (Radiant Robot Limbs тоже дописывает — списки сливаются), Skeleton Arms/Durable Arms `requirements`; VENDOR_LIST Robotics limb vendor (best) `blueprints` +8 | **включить** |
| 2760310007 | 2PN8RoboticsStorageAndLimbs.mod | Robotics Crafting Redux: Plus | 20 новых | ничего | **включить** (после Robotics Core) |
| 3592102980 | 2PN8CraftingReduxPlus.mod | Armor Crafting Redux - Fusion | 86 новых | **25 коллизий sid**: заглушки «MISSING MOD» поверх брони основы (Animation - Collection Pack, Side Quest, Rag Scarf, CBT): `mesh` = '', `value` = 0, статы по умолчанию → невидимая/нулевая броня (носят NPC гардероба) | **НЕ включать** |
| 1778901004 | RobolimbNPCs.mod | NPCs With Robotic Limbs | 9 дельт | дописывает отряды (hound hq, hive soldiers — также Kaizo, …) персонажами-дельтами без исходной записи; дубль 1785049811 NPCs Equip Robot Limbs (в основе) | **НЕ включать** (DECISIONS 2026-11-12) |

Все 10: отсутствующих зависимостей 0, битых ссылок 0, коллизий sid 0 (кроме Fusion), RACE/ANIMATION/скелетов/масок тела нет. Совместимость с 2PN8-модами основы (ShinobiTrader, Beds, Moisture Farming, Fishing, BackpackCraftingPlus, Slingbow, BuildingsCategoryMedical): общих записей и полей нет.
Пересечения с KMM_* по полям: 0 (Wardrobe меняет `clothing` у 4 списков торговцев, которые CR меняет по `blueprints`/`items`; Economy — `vendors refresh time` у Scraphouse, CR — `vendors`).

**Порядок в mods.cfg:** после Racial Diversity, перед KMM_Core (KMM_* видят записи CR в ctx, KMM_Tech ссылается на CR):
`2PN8CraftingReduxVanilla → 2PN8CraftingResearchPatch → 2PN8CraftingReduxOMO → 2PN8CraftingReduxEVA → 2PN8WeaponSmithingCore → 2PN8WeaponSmithing → 2PN8RoboticsRedux → 2PN8RoboticsStorageAndLimbs`.
Убрать из хвоста mods.cfg (добавил лаунчер): `RobolimbNPCs.mod`, `2PN8CraftingReduxPlus.mod`, а также `Deathstroke.mod` (исключён ранее: свои маски тела). В хвосте нет `KMM_Ore.mod` — проверить.

## 2. KMM_Tech — дерево «Relics» (15 новых записей, 0 изменений существующих)
Воспроизводится только имперская (человеческая) техника экспедиции из `data\catalog.json` (тиры гардероба); Хаос и ксенос — нет. Турели и «кулаки» исключены. Все исследования — стол уровня 6.

| Исследование | Требует | Цена | Открывает |
|---|---|---|---|
| Relic Studies | Tech Level 6 + Armor Crafting - Plate (CR; без CR — ванильный Plate Armour Crafting) | 5 Ancient Science Book, 5 Engineering Research, 10 000 c, 96 ч | — |
| Expedition Kit Patterns | Relic Studies | 6 Engineering, 1 AI Core, 20 000 c, 120 ч | броня T0–T1 (129), станок Relic Armoury |
| Forge-Pattern Armour | Expedition Kit | 6 книг, 2 AI Core, 40 000 c, 168 ч | броня T2 (203) |
| Relic Weapon Patterns | Expedition Kit + Masterwork Weapon Expertise (CR; иначе Advanced Weapon Grades) | 6 Engineering, 2 AI Core, 40 000 c, 168 ч | 37 видов оружия, 30 стрелковых, станок Relic Gunsmith |
| Cogitator Reconstruction | Forge-Pattern + Weapon Patterns + Edgewalkers Weapon Smithing (CR; иначе Edgewalkers) + Robotic Arms Redux (CR; иначе Robotics) | 4 AI Core, 4 Power Core, 10 книг, 80 000 c, 240 ч | предмет **Relic AI Core**, станок Cogitator Assembly Bench |
| Relic Reconstruction | Cogitator | **2 Relic AI Core**, 2 AI Core, 10 книг, 150 000 c, 336 ч | броня T3 (35), оружие T3 (2), станок Reliquary Forge |

- **Relic AI Core** (новый ITEM, шаблон — ванильный AI Core, цена 90 000): крафт на Cogitator Assembly Bench из 3 AI Core + 2 Power Core + 4 CPU Unit + 2 Ancient Science Book, 96 ч. Ванильный AI Core есть (43392-changes_otto.mod); в основе его уже можно крафтить (Craftable Ancient Tech, «AI Cores», ур. 6) — дефицит держится на цене, а не на невозможности.
- Станки (клоны ванильных Heavy Armour Smithy / Crossbow Crafting Bench / Robotics Bench, категория «CRAFTING - Relics»): Relic Armoury (T0–T2, 40 Iron Plates, 20 Steel Bars, 2 Power Core), Relic Gunsmith (все имперские стрелковые, 2 Power Core), Reliquary Forge (T3, **1 Relic AI Core** в стройке), Cogitator Assembly Bench (1 AI Core).
- Холодное WH-оружие после исследования куётся на любой кузнице (модель — станка, производитель — Homemade); броня и стрелковое — только на реликтовых станках.
- Бюджет 2 %: спавны и выдачи не меняются (поток не трогает отряды, персонажей, торговцев). Игрок производит поздно (стол VI, ≥ 4 ступени после Tech Level 6) и дорого (всего ≈ 18 AI Core с учётом 2 Relic AI Core и стройки, 340 000 c, ~47 игровых суток исследований).
- Опоры CR берутся из ctx, если CR там есть, иначе — ванильные (`anchors` в rules); отчёт `anchor_*_cr/_vanilla`.

## 3. Интеграция (делает интегратор)
- `tools\fast\lo.py` EXTRA, после `("766462696", "Racial Diversity")`:
  `("3585383286", "Armor Crafting Redux - Core"), ("3585385588", "Armor Crafting Redux - Research Fix"), ("3585385029", "Armor Crafting Redux - OMO"), ("3585385287", "Armor Crafting Redux - EVA"), ("3585386517", "Weapon Smithing Redux - Core"), ("3585386805", "Weapon Smithing Redux - Edge"), ("3589917614", "Robotics Crafting Redux: Core"), ("2760310007", "Robotics Crafting Redux: Plus")`
- `tools\build\kmm_build.py` DATA_STREAMS: вставить `("tech", "KMM_Tech")` между `("traces", "KMM_Traces")` и `("fix", "KMM_Fix")`.
- mods.cfg: `KMM_Tech.mod` после `KMM_Traces.mod` (после всех CR).
- После добавления CR в EXTRA гардероб/бюджет пересчитаются сами; CR не добавляет броню/оружие (Fusion исключён), каталог не меняется.

## 4. Проверки (офлайн)
`_tech_check.py`: два варианта ctx (как сейчас — ванильные опоры; с CR, как после EXTRA — опоры CR). Оба: 15 записей, изменений существующих 0, fcs.def ошибок 0 (6 предупреждений — унаследованные от ванильных шаблонов поля), битых ссылок 0, отвергнутых sid 0, round-trip байт в байт. Записан вариант с CR.

## 5. Риски
- Не проверено в игре: формат `ingredients` (×100) взят по образцу Craftable Ancient Tech; поведение станка с 332 вещами в `armour crafts` (у CR — десятки).
- Без CR в load order KMM_Tech зависит от 2PN8CraftingReduxVanilla/WeaponSmithingCore/RoboticsRedux (заголовок); при отказе от CR — пересобрать (опоры станут ванильными).
- CR EVA удаляет исследования EVA: рецепты брони EVA переходят на станки CR (так задумано автором).
