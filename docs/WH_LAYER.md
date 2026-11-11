# WH_LAYER — WH-слой поверх основы (2026-11-11)
Инструменты: `tools\kmod.py` (чтение), `tools\fast\analyze.py`, `reassert.py`, `report_md.py`. Сырые данные: `tools\fast\out\wh_analysis.json`, `reassert.json`.

## Итог
- Сборка: ваниль (4) + основа (713 модов коллекции 2839009285) + WH-слой (10) + KMM_Glue. Все 727 чужих файлов прочитаны kmod и **побайтово** совпали при перезаписи.
- **Вредных конфликтов нет.** WH-моды не перетирают ни одного поля, которое основа меняет в ванильных записях; ссылок основы не удаляют; битых ссылок 0.
  Все пересечения — **дописывание в общие списки** (вендоры, крафт-станции, спавны биомов, типы оружия у производителей). Kenshi сливает такие списки по цели, значит, сохраняются вклады всех модов.
- **Одна реальная перезапись:** MEGA-патч `Pathfinding - Collection Pack` уже правит расы Necrons и Astartes (`pathfind acceleration` 20→24, `water avoidance` →9), но в официальном порядке он грузится раньше WH, и WH возвращают свои значения (8 значений, 4 расы). → **KMM_Glue выставляет значения основы обратно.**
- `Animation - Collection Pack` тоже заранее содержит эти 4 расы, но как заглушку с дефолтами FCS (`bleed rate 1.0`, `playable False`). WH её перекрывают — **так и должно быть**, возвращать не нужно. Её ссылки `animation files` при слиянии сохраняются, т.е. анимации из совместимости MEGA для Necrons/Mark-X работают.
- Коллизии sid (одна и та же «новая» запись в двух модах): только эти 4 расы (основа их ждёт) и служебная `9-mapdata` (ZONE_MAP: границы карты, одинаковая у 5 модов). Безвредно.
- Waaagh! = `OrcRaceReview.mod` — это и есть искомая базовая раса орков (CORE.md §10 закрыт).

## Порядок WH-слоя (после основы, перед KMM_Glue)
Imperial Forces → EN → Death Korps → Steel Legion → Waaagh! → EN → Necrons → EN → Mark-X → EN.
Каждый EN-перевод стоит **сразу после своего оригинала**: в заголовке перевода зависимость ровно от оригинала, внутри только изменения/переименования его записей (309/157/118/1841). Авторы: Waaagh! EN — «Load this patch below OrcRaceReview»; Imperial Forces EN — «install the localization mod above the original», в контексте «поверх оригинала» = грузить после него. У Necrons EN и Mark-X EN инструкций о порядке нет, решает зависимость в заголовке.
Chaos Demons не подключён (FAST_PLAN: отложен до RE_Kenshi).

## Паспорта
| Мод (WS id) | Файл | Записей | Новых | Изм. | Фракции / расы | Отряды | Старты | Пересечений с основой | Битых ссылок |
|---|---|---|---|---|---|---|---|---|---|
| Imperial Forces (3785967794) | `wh40k_imperial_forces.mod` | 574 | 566 | 8 | — (фракции нет) | 2 | Imperial Guard Expeditionary Platoon | 7 | 0 |
| Imperial Forces EN (3787053769) | `wh40k_imperial_forces_EN.mod` | 309 | 0 | 309 | — | 0 | — | 0 | 0 |
| Death Korps (2204309112) | `Death Korps of Krieg.mod` | 32 | 29 | 3 | — | 1 | Death Korps of Krieg Squad | 3 | 0 |
| Steel Legion Armoury (2614426282) | `Steel Legion Armor Mod.mod` | 41 | 37 | 4 | Steel Legion Screamer MkI | 2 | Steel Legion | 4 | 0 |
| Waaagh! (OrcRaceReview — база расы орков) (3835702545) | `OrcRaceReview.mod` | 205 | 196 | 9 | Greenskins; Orc | 14 | Wasteland Wanderers | 9 | 0 |
| Waaagh! EN (3836356922) | `OrcRaceReview_English.mod` | 157 | 0 | 157 | — | 0 | — | 0 | 0 |
| 40K Necrons (3595693319) | `40K Necrons.mod` | 170 | 165 | 5 | Space Necromancer; Space Necromancer - Sora Dynasty | 9 | Adventurers searching for rumors of the undead (Story Test) | 5 | 0 |
| 40K Necrons EN (3596387634) | `40K Necrons EN.mod` | 118 | 0 | 118 | — | 0 | — | 1 | 0 |
| 40k Mark-X (3475091710) | `TEXT TEXTURE.mod` | 2591 | 2555 | 36 | Astartes (Elite); Astartes (Special Gene Seed); Astartes (The Lost); Astartes Support Level 01; Astartes Support Level 02; Astartes Support Level 03; Astartes Support Level 04; Astartes survivors … | 94 | 40k Power Armor Test Start; Astartes Valley; Original Astartes Opening; U-Group's Unyielding Terminator Start | 36 | 0 |
| 40k Mark-X EN (3596387397) | `TEXT TEXTURE EN.mod` | 1841 | 0 | 1841 | — | 0 | — | 3 | 0 |

Где WH уже есть в мире без Glue: **Necrons** — спавны в биомах + свой город; **Mark-X** — 94 отряда, часть в спавнах 6 биомов и барах; **Waaagh!** — только свой город (бродячих банд нет); **Imperial Forces / Death Korps / Steel Legion** — только старты игрока, у отрядов нет фракции.

## Карта пересечений с основой (все — дописывание в списки)
**wh40k_imperial_forces.mod** — 7 записей:
- VENDOR_LIST «armour king» — ещё 27 модов основы; общие списки: clothing, containers
- VENDOR_LIST «weapon vendor skeleton city» — ещё 19 модов основы; общие списки: crossbows, weapons
- VENDOR_LIST «ancient lab» — ещё 8 модов основы; общие списки: clothing, items
- VENDOR_LIST «Hi tech junk» — ещё 6 модов основы; общие списки: items
- BUILDING_FUNCTIONALITY «medical crafting» — ещё 4 модов основы; общие списки: item crafts
- VENDOR_LIST «ancient lab ruins» — ещё 3 модов основы; общие списки: items
- VENDOR_LIST «ancient outpost» — ещё 1 модов основы; общие списки: items

**Death Korps of Krieg.mod** — 3 записей:
- BUILDING_FUNCTIONALITY «armour leather» — ещё 38 модов основы; общие списки: armour crafts
- BUILDING_FUNCTIONALITY «crossbow smith» — ещё 8 модов основы; общие списки: crossbow crafts
- RESEARCH «Gear Storage» — ещё 5 модов основы; общие списки: enable buildings

**Steel Legion Armor Mod.mod** — 4 записей:
- BUILDING_FUNCTIONALITY «armour plate» — ещё 49 модов основы; общие списки: armour crafts
- VENDOR_LIST «armour king» — ещё 27 модов основы; общие списки: clothing
- VENDOR_LIST «armor vendor mongrel» — ещё 24 модов основы; общие списки: armour blueprints
- RACE_GROUP «Skeleton» — ещё 8 модов основы; общие списки: races

**OrcRaceReview.mod** — 9 записей:
- BIOME_GROUP «Skinner's Roam» — ещё 35 модов основы; общие списки: homeless spawns
- WEAPON_MANUFACTURER «Homemade» — ещё 20 модов основы; общие списки: weapon types
- WEAPON_MANUFACTURER «Catun Scrapmaster» — ещё 18 модов основы; общие списки: weapon types
- WEAPON_MANUFACTURER «Edgewalkers» — ещё 18 модов основы; общие списки: weapon types
- WEAPON_MANUFACTURER «Skeleton Smiths» — ещё 17 модов основы; общие списки: weapon types
- WEAPON_MANUFACTURER «Ancient» — ещё 17 модов основы; общие списки: weapon types
- WEAPON_MANUFACTURER «Cross» — ещё 17 модов основы; общие списки: weapon types
- WEAPON_MANUFACTURER «Unknown» — ещё 16 модов основы; общие списки: weapon types
- WEAPON_MANUFACTURER «Truth Two-» — ещё 4 модов основы; общие списки: weapon types

**40K Necrons.mod** — 5 записей:
- BUILDING_FUNCTIONALITY «armour plate» — ещё 49 модов основы; общие списки: armour crafts
- BIOME_GROUP «Sonorous Dark» — ещё 22 модов основы; общие списки: homeless spawns
- BUILDING_FUNCTIONALITY «robot limb smith» — ещё 13 модов основы; общие списки: robotics crafts
- SQUAD_TEMPLATE «Scraphouse» — ещё 6 модов основы; общие списки: vendors
- BUILDING_FUNCTIONALITY «robotics» — ещё 4 модов основы; общие списки: item crafts

**40K Necrons EN.mod** — 1 записей:
- RACE «Space Necromancer» — ещё 1 модов основы; общие списки: разные поля

**TEXT TEXTURE.mod** — 36 записей:
- BUILDING_FUNCTIONALITY «armour plate» — ещё 49 модов основы; общие списки: armour crafts, backpack crafts
- BIOME_GROUP «Border Zone» — ещё 39 модов основы; общие списки: homeless spawns
- BIOME_GROUP «Vain» — ещё 37 модов основы; общие списки: nests
- BIOME_GROUP «Shem» — ещё 36 модов основы; общие списки: homeless spawns
- BIOME_GROUP «Skinner's Roam» — ещё 35 модов основы; общие списки: homeless spawns
- BIOME_GROUP «Dreg» — ещё 34 модов основы; общие списки: nests
- BIOME_GROUP «Okran's Valley» — ещё 31 модов основы; общие списки: homeless spawns, nests
- BIOME_GROUP «Bonefields» — ещё 30 модов основы; общие списки: homeless spawns
- BIOME_GROUP «Flats Lagoon» — ещё 28 модов основы; общие списки: homeless spawns
- BIOME_GROUP «Bast» — ещё 27 модов основы; общие списки: homeless spawns, nests
- BIOME_GROUP «Cannibal Plains» — ещё 26 модов основы; общие списки: homeless spawns, nests
- BIOME_GROUP «Stobe's Gamble» — ещё 24 модов основы; общие списки: homeless spawns
- BIOME_GROUP «Okran's Pride» — ещё 24 модов основы; общие списки: homeless spawns
- BIOME_GROUP «Leviathan Coast» — ещё 24 модов основы; общие списки: homeless spawns, nests
- BIOME_GROUP «Hidden Forest» — ещё 23 модов основы; общие списки: homeless spawns, nests
- BIOME_GROUP «Sinkuun» — ещё 23 модов основы; общие списки: nests
- BIOME_GROUP «The Iron Trail» — ещё 22 модов основы; общие списки: homeless spawns, nests
- BIOME_GROUP «Northern Coast» — ещё 22 модов основы; общие списки: homeless spawns, nests
- BIOME_GROUP «Purple Sands» — ещё 22 модов основы; общие списки: homeless spawns, nests
- BIOME_GROUP «Fog Islands» — ещё 22 модов основы; общие списки: homeless spawns, nests
- BIOME_GROUP «Venge» — ещё 22 модов основы; общие списки: homeless spawns
- WEAPON_MANUFACTURER «Homemade» — ещё 20 модов основы; общие списки: weapon types
- TOWN «Flats Lagoon» — ещё 19 модов основы; общие списки: bar squads
- BIOME_GROUP «Burning Forest» — ещё 19 модов основы; общие списки: homeless spawns
- BIOME_GROUP «Darkfinger» — ещё 18 модов основы; общие списки: homeless spawns, nests
- BIOME_GROUP «High Bonefields» — ещё 18 модов основы; общие списки: homeless spawns
- BIOME_GROUP «Arm of Okran» — ещё 15 модов основы; общие списки: homeless spawns
- BIOME_GROUP «The Shrieking Forest» — ещё 15 модов основы; общие списки: homeless spawns
- BIOME_GROUP «Berserker Country» — ещё 15 модов основы; общие списки: homeless spawns, nests
- BIOME_GROUP «Sniper Valley» — ещё 12 модов основы; общие списки: homeless spawns
- FACTION «Starving Bandits» — ещё 11 модов основы; общие списки: разные поля
- SQUAD_TEMPLATE «Adventurer Lagoon Bar» — ещё 10 модов основы; общие списки: vendors
- BIOME_GROUP «Fishman Island» — ещё 10 модов основы; общие списки: homeless spawns, nests
- FACTION «Fogmen» — ещё 8 модов основы; общие списки: relations
- FACTION «Fishmen» — ещё 6 модов основы; общие списки: relations
- RACE_GROUP «Human» — ещё 4 модов основы; общие списки: races

**TEXT TEXTURE EN.mod** — 3 записей:
- RACE «Astartes (The Lost)» — ещё 1 модов основы; общие списки: разные поля
- RACE «Astartes (Elite)» — ещё 1 модов основы; общие списки: разные поля
- RACE «Astartes (Special Gene Seed)» — ещё 1 модов основы; общие списки: разные поля

## KMM_Glue — что делает (`rules\glue_rules.json` → `tools\fast\gen_glue.py`)
| Блок | Что | Объём |
|---|---|---|
| Каты по ролям | `money min/max` по `NPC class` (CharacterTypeEnum из KenshiLib), только повышение; рабов и OT_NONE не трогаем | 1936 персонажей |
| Слабые избегают сильных | 41 фракция OT_BANDIT: пороги бегства ≥0.5 / ≥1.3; взаимное `coexistence` с 9 сильными (UC, Shek, Tech Hunters, Astartes ×4, Necrons, остатки Империума) | 41 + 9 фракций |
| Остатки Империума | новая фракция «Imperial Expedition Remnants» (каркас Manhunters, взаимные отношения: враги Greenskins/Necrons/Chaos/Cannibals, друзья Astartes); 2 патруля (Commissar+Guardsmen, Death Korps), спавн весом 1 в Border Zone, Okran's Pride, Heng, Ashlands | 1 фракция, 2 отряда |
| Варбанда орков | «Greenskin Warband» (Big 'Un + Bolt Boys + Wanderers, AI рейдеров Dust Bandits), спавн весом 2 в Stenn Desert, Spider Plains, Bonefields | 1 отряд |
| T0 | Guardsman Armor [T0 scavenged], Lasgun [T0 failing], Chainsword [T0 jammed] — те же модели, статы ×0.3–0.7; «worn kit»-бойцы во вторых половинах патрулей; 285 бандитов получают T0-броню в одежду с весом 3 | 3 предмета |
| Возврат значений основы | 8 значений Pathfinding pack | 4 расы |
Файл: 2023 записей (9 новых, 2014 дельт), 323 КБ, 166 зависимостей в заголовке. Валидация fcs.def: **0 ошибок**; 946 предупреждений, все про устаревшие поля, унаследованные от исходных записей.

## Риски и что смотреть в тесте
- Как `coexistence` работает для врагов, точно не известно (в fcs.def: «обычно не нападают на нейтралов без повода»), эффект может быть мягким.
- Каты: деньги вырастут у ~1900 NPC → лут богаче. Уровни задаются в `glue_rules.json`.
- Персонажи патрулей Империума взяты из стартовых отрядов игрока (Commissar, Guardsman, DK Soldier); как NPC они могут вести себя странно в диалогах.
