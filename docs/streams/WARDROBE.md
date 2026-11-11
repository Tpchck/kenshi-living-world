# WARDROBE — поток G: разведка и каталог (2026-11-11, без генерации)
Цель направления: **вписать WH в экономику Kenshi, а не WH в Kenshi.** Огромное разнообразие; одна и та же вещь в одинаковой комплектации встречается редко.
Генерацию не начинаю до «да» владельца.

## 1. Разведка: коллекция Grimdark War (169 модов, отобраны гардеробные)
Источник: Steam Web API (GetCollectionDetails + GetPublishedFileDetails, два пакетных запроса). Для модов на диске вещи посчитаны через kmod. Для остальных Web API число вещей не отдаёт, в описаниях его почти никто не пишет — точный счёт после подписки (`tools\fast\wardrobe_recon.py`).
Размер файла не равен памяти: Kenshi грузит меши и текстуры по мере появления в кадре. Бюджет **+2 ГБ к пику** (TEST_V0: 11 ГБ Private с RTGI; TEST_V1: 7.7 ГБ, короткая сессия) проверяем A/B-запуском после каждой волны.

### Волна 1 — рекомендую (≈1220 МБ новых файлов): лохмотья, мародёры, мрачная броня, Hell-серия, Machinist, Metro2033
| Мод | МБ | Подписчиков | На диске | Вещей (броня/оружие/арбалеты) | Слоты брони (код:шт) | Вещей на МБ |
|---|---|---|---|---|---|---|
| [Got Gear? Clothing/Armor Collection](https://steamcommunity.com/sharedfiles/filedetails/?id=2980909939) | 280 | 1586 | — | после подписки | — | — |
| [Mercenary Full Plate](https://steamcommunity.com/sharedfiles/filedetails/?id=1897538943) | 172 | 13306 | — | после подписки | — | — |
| [Sacred Trash](https://steamcommunity.com/sharedfiles/filedetails/?id=3556712059) | 144 | 15188 | да | 61 (61/0/0) | 3:29, 5:12, 14:10, 6:4 | 0.42 |
| [Metro2033](https://steamcommunity.com/sharedfiles/filedetails/?id=3416362194) | 114 | 2228 | — | после подписки | — | — |
| [Hell Bringer Armour](https://steamcommunity.com/sharedfiles/filedetails/?id=3186440323) | 72 | 2235 | — | после подписки | — | — |
| [Hell Stalker Armour](https://steamcommunity.com/sharedfiles/filedetails/?id=3183230127) | 72 | 2096 | — | после подписки | — | — |
| [Hell Buster Armour](https://steamcommunity.com/sharedfiles/filedetails/?id=3193127902) | 72 | 1776 | — | после подписки | — | — |
| [Hell Hound Armour](https://steamcommunity.com/sharedfiles/filedetails/?id=3178870697) | 72 | 2004 | — | после подписки | — | — |
| [Hell Pathfinder Armour](https://steamcommunity.com/sharedfiles/filedetails/?id=3192272492) | 71 | 1418 | — | после подписки | — | — |
| [Bounty Hunter Armor](https://steamcommunity.com/sharedfiles/filedetails/?id=2456515727) | 61 | 47566 | — | после подписки | — | — |
| [【2333】Machinist armor](https://steamcommunity.com/sharedfiles/filedetails/?id=3344149018) | 57 | 780 | — | после подписки | — | — |
| [Deathstroke - A Tier 4 Armour Mod](https://steamcommunity.com/sharedfiles/filedetails/?id=2206047200) | 54 | 1242 | — | после подписки | — | — |
| [Hell Survivor Armour](https://steamcommunity.com/sharedfiles/filedetails/?id=3174666919) | 51 | 2005 | — | после подписки | — | — |
| [Saxon armour](https://steamcommunity.com/sharedfiles/filedetails/?id=2982809131) | 24 | 1079 | — | после подписки | — | — |
| [TRASH (Мусор)](https://steamcommunity.com/sharedfiles/filedetails/?id=3809464398) | 22 | 213 | — | после подписки | — | — |
| [Old Empire Enforcers](https://steamcommunity.com/sharedfiles/filedetails/?id=2294747201) | 20 | 7285 | — | после подписки | — | — |
| [Rusty Raiders](https://steamcommunity.com/sharedfiles/filedetails/?id=2547875991) | 2 | 1155 | — | после подписки | — | — |
| [Druid Helm](https://steamcommunity.com/sharedfiles/filedetails/?id=1944912625) | 2 | 1092 | — | после подписки | — | — |
| [Weapon - Grausam](https://steamcommunity.com/sharedfiles/filedetails/?id=2799955117) | 1 | 644 | — | после подписки | — | — |
| [Weapon - BusterJitte](https://steamcommunity.com/sharedfiles/filedetails/?id=2044880405) | 1 | 1194 | — | после подписки | — | — |

### Волна 2 — после замера памяти (≈1778 МБ): тяжёлые 40k и большие паки
| Мод | МБ | Подписчиков | На диске | Вещей (броня/оружие/арбалеты) | Слоты брони (код:шт) | Вещей на МБ |
|---|---|---|---|---|---|---|
| [Driftmetal: Remnants (V2)](https://steamcommunity.com/sharedfiles/filedetails/?id=2882658082) | 705 | 30274 | — | после подписки | — | — |
| [Fox's Weapons Mod Set 2 -Vanguard Mercenaries-](https://steamcommunity.com/sharedfiles/filedetails/?id=2178681257) | 229 | 11727 | — | после подписки | — | — |
| [Warhammer 40K ARMOURY](https://steamcommunity.com/sharedfiles/filedetails/?id=3051565880) | 215 | 4776 | — | после подписки | — | — |
| [40K Emperor Armour](https://steamcommunity.com/sharedfiles/filedetails/?id=3661478266) | 191 | 3521 | — | после подписки | — | — |
| [Grigori](https://steamcommunity.com/sharedfiles/filedetails/?id=2706218807) | 147 | 17869 | — | после подписки | — | — |
| [Re Weapon](https://steamcommunity.com/sharedfiles/filedetails/?id=3477292843) | 83 | 3346 | — | после подписки | — | — |
| [The Juggernaut](https://steamcommunity.com/sharedfiles/filedetails/?id=1336829063) | 72 | 17849 | — | после подписки | — | — |
| [【2333】Crab Armor MKII 螃蟹甲MKII](https://steamcommunity.com/sharedfiles/filedetails/?id=3580093163) | 64 | 3276 | — | после подписки | — | — |
| [Cyberfang Katana](https://steamcommunity.com/sharedfiles/filedetails/?id=1926495956) | 38 | 16351 | — | после подписки | — | — |
| [Demilisher Skeleton Race +NewLimb NewArmor](https://steamcommunity.com/sharedfiles/filedetails/?id=3220461803) | 34 | 1619 | — | после подписки | — | — |

### Уже в сборке (для сравнения «вещей на МБ»)
| Мод | МБ | Подписчиков | На диске | Вещей (броня/оружие/арбалеты) | Слоты брони (код:шт) | Вещей на МБ |
|---|---|---|---|---|---|---|
| [(40k) Imperial Forces](https://steamcommunity.com/sharedfiles/filedetails/?id=3785967794) | 3066 | 851 | да | 232 (185/23/24) | 3:45, 5:38, 6:38, 9:38 | 0.08 |
| [40k Mark-X and More Ammor mod](https://steamcommunity.com/sharedfiles/filedetails/?id=3475091710) | 1897 | 13057 | да | 277 (238/32/7) | 3:61, 14:46, 5:45, 6:41 | 0.15 |
| [Waaagh!](https://steamcommunity.com/sharedfiles/filedetails/?id=3835702545) | 221 | 292 | да | 30 (25/5/0) | 5:8, 6:7, 9:6, 3:4 | 0.14 |
| [40K Necrons](https://steamcommunity.com/sharedfiles/filedetails/?id=3595693319) | 142 | 8781 | да | 16 (12/3/1) | 3:4, 5:3, 14:3, 6:2 | 0.11 |
| [Steel Legion Armoury](https://steamcommunity.com/sharedfiles/filedetails/?id=2614426282) | 96 | 1530 | да | 15 (15/0/0) | 5:8, 6:3, 8:2, 3:2 | 0.16 |
| [The Death Korps - A Warhammer 40k Mod](https://steamcommunity.com/sharedfiles/filedetails/?id=2204309112) | 34 | 3024 | да | 7 (5/1/1) | 3:2, 9:1, 5:1, 6:1 | 0.2 |

Наблюдение: Imperial Forces — 232 вещи на 3 ГБ (0.08 на МБ), Sacred Trash — 0.42 на МБ. Самое дешёвое разнообразие — **данные без новых моделей**: материалы, цвета, состояние и качество поверх существующих мешей (см. §3).

### Не берём (не гардероб или дорого на МБ)
- [More Limb replacement 140 types](https://steamcommunity.com/sharedfiles/filedetails/?id=3045283593) — конечности, отдельная тема
- [Ancient Empire Samurai (v2.1)](https://steamcommunity.com/sharedfiles/filedetails/?id=3224267935) — самураи — вне стиля grimdark
- [Weapon, CrossBow - PileBunker](https://steamcommunity.com/sharedfiles/filedetails/?id=2678787059) — одиночное оружие, тяжёлое на МБ
- [Backpack - CarrierShell-A](https://steamcommunity.com/sharedfiles/filedetails/?id=2001912981) — рюкзак
- [Weapon, CrossBow - Gatling gun](https://steamcommunity.com/sharedfiles/filedetails/?id=2805907981) — одиночное оружие, тяжёлое на МБ
- [Weapon, CrossBow - GaussRfle](https://steamcommunity.com/sharedfiles/filedetails/?id=1958713825) — одиночное оружие, тяжёлое на МБ
- [Bandits Expansion](https://steamcommunity.com/sharedfiles/filedetails/?id=1578969334) — фракции бандитов, не гардероб
- [Minor Factions Amplified](https://steamcommunity.com/sharedfiles/filedetails/?id=1578990167) — фракции, не гардероб
- [Wastelands](https://steamcommunity.com/sharedfiles/filedetails/?id=3089253212) — оверхол мира, не гардероб
- [ReBackpack](https://steamcommunity.com/sharedfiles/filedetails/?id=3473057404) — рюкзаки
- [Backpacks Expanded 2.0 (Quivers added!)](https://steamcommunity.com/sharedfiles/filedetails/?id=2117877487) — рюкзаки/колчаны

## 2. Каталог `data\catalog.json` (`tools\catalog.py`)
- В каталоге **2253 реальных вещей** с моделью (ARMOUR / WEAPON / CROSSBOW). Ваниль, основа, WH и KMM_Relics.
- Отброшено **4624 заглушек**: MEGA Animation - Collection Pack заранее объявляет вещи модов, которых нет в сборке.
- Поля каждой вещи: слот или категория, тир, происхождение, стиль, мод-источник, кто носит (фракции через отряды), где продаётся (VENDOR_LIST).
- **Тир** — перцентиль цены внутри слота или категории (средний ранг): T0 < 30 %, T1 < 70 %, T2 < 97 %, T3 — верхние 3 % (реликты). Итого: T1 1254, T2 484, T0 463, T3 52.
- **Происхождение:** culture 924, generic 617, imperial 444, selfmade 164, chaos 58, xenos 46.
  - Культуры по носителям: Tech Hunters 110, United Cities 77, The Holy Nation 72, Shrieking Bandits 51, Western Hive 39, Southern Hive 38, Anti-Slavers 29, Drifters 28, Swampers 24, Flotsam Ninjas 22, Cannibals 21, Adventurers Guild 19, Nomads 17, Slave Traders 16, Bounty Hunters 16, Shinobi Thieves 14, Fogmen 14, Empire Peasants 14, Crystal Relics 14, Shek Kingdom 13.
  - «generic» = никто из отрядов не носит, культура не определена.
- **Стиль** (по названию): plate 570, masked 370, power 249, rags 243, carapace 126, leather 82, chain 75, holy 71, tribal 62, cyber 49, scrap 35, xenos 34.
- **Ни на ком и нигде не продаются: 488 вещей.** Это готовый запас для гардероба без единого нового МБ.

| Слот / категория | T0 | T1 | T2 | T3 |
|---|---|---|---|---|
| armour:hat | 56 | 360 | 103 | 15 |
| armour:body | 132 | 253 | 110 | 11 |
| armour:legs | 69 | 188 | 70 | 7 |
| armour:belt | 56 | 127 | 56 | 2 |
| armour:boots | 22 | 126 | 20 | 7 |
| weapon:heavy | 22 | 26 | 18 | 0 |
| armour:shirt | 20 | 21 | 21 | 1 |
| crossbow | 17 | 31 | 13 | 0 |
| weapon:katana | 17 | 20 | 20 | 2 |
| weapon:turret | 12 | 26 | 13 | 3 |
| weapon:sabre | 11 | 26 | 15 | 1 |
| weapon:blunt | 16 | 20 | 15 | 1 |

Ограничение: тир по цене грубый, у модов цены разномасштабные. Перед генерацией нужен тир по статам (защита/урон, нормированные на слот).

## 3. Будущая модель гардероба (только описание)
1. **Пул фракции — взвешенная смесь из трёх источников:**
   - своё производство — вещи своей культуры, тиры по богатству фракции;
   - торговля с соседями — пулы соседей по LORE_MAP (союзы, общие регионы);
   - трофеи с врагов — пулы врагов по LORE_MAP (вражда ≤ −50).

   Веса зависят от богатства и положения фракции: бедные — больше трофеев и самоделок, богатые — больше своего.
2. **Элита:** 1–2 фиксированные опознавательные вещи (шлем или плащ, знак фракции). Остальное — из пула, чтобы два офицера не выглядели одинаково.
3. **Бандиты:** трофеи своего региона, самоделки (selfmade / scrap / rags) и реликт с шансом ~1 : 50000 на персонажа (T3 из каталога).
4. **Широкие диапазоны качества:** одна модель встречается в нескольких состояниях (T0–T2) — данные без новых мешей. Это главный источник «редко одинаковой комплектации».
5. **Торговцы региона** торгуют из тех же пулов (своё + соседи + трофеи), с наценкой на чужое. Экономика и гардероб — одна система.
6. **Тиры заранее сгенерированы** для каждой фракции (наборы T3→T0) под будущее переключение дирижёром по богатству: поднялась — следующий набор, обеднела — предыдущий.
7. **Поглощение потока D без дублей:** клоны-тиры RELICS (162 персонажа, T0-предметы WH) переходят в генератор WARDROBE. RELICS остаётся владельцем WH-фракций, патрулей и спавнов. Персонажей-клонов и их снаряжение строит WARDROBE из каталога, а не отдельными правилами. До переноса потоки не пересекаются.
8. **Технически:**
   - CHARACTER `clothing`/`weapons`/`crossbows` с весами (`val1` — шанс внутри слота) и `armour grade`, `weapon level` (производители — качество оружия);
   - FACTION `color` для цветовых вариаций;
   - VENDOR_LIST для торговцев.

   Владение записями — по DECISIONS: существующие CHARACTER у ECONOMY. Гардероб пойдёт через новые клоны и списки, либо после решения интегратора о передаче полей одежды WARDROBE.

## 4. Решения, нужные из игры
- Подписаться на волну 1? Список — §1, ссылки ведут на подписку.
- Делать ли тир по статам вместо цены перед генерацией?
- Как делить CHARACTER: поля одежды и оружия — WARDROBE, деньги — ECONOMY? Сейчас вся запись CHARACTER у ECONOMY, а генератор требует, чтобы одну запись менял один поток.

## 5. Генерация v1 (2026-11-11, по принятым решениям)
- **Тир по статам** (tools/catalog.py), цена — поправка 20 %.
  - Броня: тип материала (ткань / кожа / кольчуга / пластины) × покрытие частей тела × (1 + бонусы защиты) + вес (до 25 кг) + боевые бонусы − штраф подвижности.
  - Оружие: урон × (1 + бронебойность) + атака + вес.
  - Арбалет: урон × точность × скорострельность / перезарядка + дальность.
  - Каталог: 2250 вещей (без KMM_*), T0/T1/T2/T3 = 553/1140/511/46.
- **Владение по полям** (DECISIONS): генератор падает, только если два потока меняют одно поле одной записи.
- **KMM_Wardrobe** (`tools\streams\wardrobe.py`, `rules\streams\wardrobe.json`): 887 записей, fcs.def 0 ошибок, пересечений полей 0.
  - **845 персонажей**, фракция берётся из отряда или из города, где отряд живёт. В среднем +13.5 вариантов одежды на персонажа, варианты только в тех слотах, что у него уже есть — силуэт сохраняется.
  - Источники выбранных вариантов: своё производство 4474, торговля с соседями 2652, трофеи 2280, самоделки 421. Пропорции — по богатству фракции (`wealth.*.mix`).
  - **Элита:** 308 опознавательных вещей фракции. Слот заменяется целиком: у богатых — шлем и корпус, у остальных — шлем.
  - **Бандиты:** 160 персонажей с реликтом T3 весом 1 против вариантов весом 15000 — шанс ≈ 1:45000.
  - **Оружие:** 454 варианта из торговли и трофеев той же категории, 15 %.
  - **Качество:** шанс улучшения брони 15 / 10 / 5 по богатству плюс производитель оружия своего тира (бывшие уровни потока D).
  - **Торговцы:** 39 торговых списков одежды получили по 6 вещей из тех же пулов.
  - **Неиспользуемые вещи:** 390 из 497 распределены по сродству стиля, 345 реально попали к персонажам и торговцам. Всего задействовано 1257 разных вещей, 241 встречается ровно один раз.
- **Поглощение потока D без дублей.** Клоны-тиры (162 персонажа, перенаправление 174 военных отрядов), T0-предметы WH и уровни качества ушли из RELICS. Трофеи бандитов (поле clothing) ушли из ECONOMY. RELICS теперь 14 записей: фракция Империума, 3 отряда, спавны.
- **Тиры наперёд:** `data\wardrobe_tiers.json` — пулы 107 фракций по T0–T3 и слотам для будущего переключения дирижёром по богатству (пока только данные).
- **Настроить позже:**
  - **Перекос по частоте.** Отдельные вещи слишком частые — например, `23-AntiquityPack.mod` встречается 224 раза. Причина — маленький пул в некоторых слотах. Лечится лимитом повторов на вещь.
  - **Раса.** Если у персонажа раса не задана, берётся состав рас фракции. Вещи с ограничением `races` у смешанных фракций по этой причине отбрасываются.
- **Сейв:** нужна новая игра (тиры клонов и sid KMM_Relics изменились).
- **Волна 1:** подключу после «подписался»: повторю каталог, тиры и генерацию.

## 6. Волна 1 подключена (2026-11-11)
Аудит (`tools\fast\audit_mods.py`):
| Мод | МБ | Новых / правок | Перетирает значений основы | Совпадающих файлов | Решение |
|---|---|---|---|---|---|
| Hell Bringer | 72.0 | 6 / 1 | 0 () | 0 | принят |
| Hell Stalker | 71.9 | 8 / 1 | 0 () | 0 | принят |
| Hell Buster | 71.8 | 6 / 1 | 0 () | 0 | принят |
| Hell Hound | 71.5 | 8 / 1 | 0 () | 0 | принят |
| Hell Pathfinder | 71.4 | 6 / 1 | 0 () | 0 | принят |
| Hell Survivor | 50.9 | 8 / 2 | 0 () | 0 | принят |
| Machinists armor | 57.1 | 12 / 11 | 0 () | 0 | принят |
| Metro | 114.2 | 82 / 20 | 0 () | 0 | принят |
| GotGear_V1 | 280.4 | 75 / 2 | 0 () | 0 | принят |
| Mercenary Full Plate | 171.7 | 0 / 27 | 20 (Animation - Collection Pack.mod, YAKNM - Collection Pack.mod) | 0 | принят |
| Saxon_merc | 23.8 | 10 / 13 | 0 () | 0 | принят |
| Bounty Hunter Armor | 61.2 | 0 / 77 | 53 (Animation - Collection Pack.mod, YAKNM - Collection Pack.mod) | 0 | принят |
| Rusty Raiders FACTION | 2.2 | 0 / 2711 | 5 (RadiantFacesFixes.mod) | 12 | принят |
| =T= | 21.5 | 105 / 6 | 0 () | 0 | принят |
| HTDEnforcers | 19.9 | 0 / 333 | 82 (Animation - Collection Pack.mod) | 0 | принят |
| DruidHelm | 2.0 | 0 / 7 | 0 () | 0 | принят |
| Weapon2_Grausam | 1.4 | 2 / 9 | 0 () | 0 | принят |
| Weapon_Buster_Jitte | 0.7 | 0 / 13 | 0 () | 0 | принят |
| Deathstroke | 54.3 | 0 / 12 | 0 () | 14 | **исключён** |

- Перезаписи у Mercenary Full Plate, Bounty Hunter Armor и Old Empire Enforcers затрагивают только заглушки MEGA `Animation - Collection Pack` (пустые описания, иконки, дефолтные флаги) — так и должно быть. 40 «коллизий» Got Gear — те же заглушки.
- **Deathstroke исключён:** у него свои `Female/Male/HiverMask_Default.png`, отличные от Community Part Map. На CPM опирается вся основа (и патч Invisible Arms), поэтому подмена масок ломает скрытие частей тела под бронёй у всех.
- Rusty Raiders принят: 2711 правок, в основном диалоги. Перетирает 5 флагов `playable` у рас роботов (RadiantFacesFixes) — косметика выбора расы.
- В mods.cfg: после TEXT TEXTURE EN, перед KMM_*. Каталог: 2363 вещи (+112 из волны 1). TRASH и Old Empire Enforcers — предметы и фракции, не броня.

### Генерация v2: мягкий потолок повторов и расы
- Вес выбора вещи = 1 / (1 + (использований / 12)²). Если в слоте меньше 15 кандидатов (майки T0 и т. п.), тир расширяется на соседний.
- Отладочные вещи («#…», «test», «debug») исключены.
- Вещи с ограничением по расе:
  - явная раса персонажа — строгая проверка;
  - смесь рас фракции — вещь выдаётся, если её может носить хотя бы одна раса фракции; при спавне игра надевает только подходящее (как в ванильных смешанных списках, в игре не проверено).
  - Итого выдано: персонажам с явной расой — 1038, в смешанные фракции — 1266.
- Итог: 1601 разных вещей, 11114 размещений, медиана 4, максимум 85 (было 224). Из волны 1 разошлись 70 вещей из 112, из неиспользуемых — 449 из 561.

| Повторов | Вещь (топ-10) | Слот |
|---|---|---|
| 85 | Drifter's Leather Pants | armour:legs |
| 81 | Black Plate Jacket | armour:body |
| 69 | Old Gorillo Pelt | armour:shirt |
| 65 | Plated Longboots | armour:boots |
| 60 | Surgical Undershirt w Gloves | armour:shirt |
| 59 | ! Bard's shirt | armour:shirt |
| 58 | Bandana | armour:hat |
| 51 | Martial Artist Bindings | armour:shirt |
| 48 | Extreme Warrior - MKX Power Helmet | armour:hat |
| 46 | saxon shirt | armour:shirt |

## 9. Волна WARD (2026-11-12): покрытие, разнообразие, рюкзаки, лут, оружие
- Покрытие: 859 → 1157 CHARACTER (потолок мира: 1340 неуникальных гуманоидов с одеждой; остальные — уникальные/сюжетные, звери, скелеты/роботы, стартовые). 294 из 1157 — персонажи вне отрядов с фракцией (фракция из ссылки `faction`, иначе безфракционный общий пул). Пустые в ваниле слоты (шапка 40 %, майка 50 %, ботинки 35 %, пояс 30 %) получают варианты. WH-персонажи (452) — свой набор, без рюкзаков/лута/арбалетов.
- Разнообразие: 5 вариантов на слот (майка/пояс 4), жёсткий потолок 25 размещений на вещь (обход персонажей в случайном порядке), «Gorillo Pelt» как одна семья ≤ 30 суммарно. Мягкий вес культуры: own 35 %, остальное — общий пул яруса (common), торговля, трофеи. Накидки (cloak|cape|poncho|pelt|robe|…) ×1.8 в слотах майка/тело: 67 разных, максимум 25. Итог: максимум 25 (было 85), разных вещей 1636 (было 1601), размещений ≈ 18,3 тыс.
- Рюкзаки: каталог теперь включает CONTAINER slot 12 для людей (77 в каталоге, 36 небожественных; зверям, колчанам, кристаллам — нет). Поле CHARACTER `backpack` (ссылка предмет/1/шанс %/0), по NPC class: торговцы/лавочники/бандиты/авантюристы 50–55 %, охрана/армия 20 %. Выдано 541 персонажу (+274 имели свой).
- Лут: поле CHARACTER `inventory` (ITEM/1/шанс 40 %/0), 1–4 предмета 70 % персонажей по ярусу: бедные — хлам и еда, богатые — книги и роскошь; пул data/catalog_loot.json (138 предметов из белого списка модов, без квестовых/Crafting Redux/KMM_Tech/Relics).
- Оружие: 2–3 варианта ближнего боя (шанс 30), 50 % из соседних классов; без `weapon:turret`. Арбалеты/мушкеты — только по правилу владельца (`rules/streams/wardrobe.json` ranged): из 75 прошло 17 (лук/слингбоу/арбалет/гарпун/джезайл/двуствольный гарпун), 58 отсеяны (Metro.mod целиком — китайские названия и автоматы, 37 современные/энерго/автоматические, Soulbody).
- Поля владения: добавлены `backpack`, `inventory` (CHARACTER) — зафиксировать в DECISIONS.md; `crossbows` (CHARACTER) уже за WARDROBE.
