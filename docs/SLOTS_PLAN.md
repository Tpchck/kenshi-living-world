# SLOTS_PLAN: перчатки, шарфы и мелкие слоты (аудит + план, 2026-11-14)

Только анализ. Данные: `data/slots_audit.json` (tools/slots_audit.py, ~10 с, читает KMM_*.mod из build/ только на чтение).
Продолжает DECISIONS «SLOTS: мелкие вещи в слоты Extra Inventory Sections (2026-11-12)» и пометку 2026-11-13 «клоны GLOVES убраны».
Нумерация slot: 3 hat, 4 eyes, 5 body, 6 legs, 8 shirt, 9 boots, 10 gloves, 11 neck, 12 backpack, 14 belt.

## 1. Сводка покрытия (после KMM_Wardrobe; «исп.» = надето у >=1 CHARACTER.clothing или в VENDOR_LIST.clothing)

| слот | вещей | исп. | T0 | T1 | T2 | T3 |
|---|---|---|---|---|---|---|
| hat | 552 | 511 | 136 | 284 | 116 | 16 |
| body | 525 | 493 | 145 | 252 | 115 | 13 |
| legs | 350 | 322 | 83 | 188 | 71 | 8 |
| belt | 232 | 215 | 51 | 138 | 42 | 1 |
| boots | 185 | 171 | 45 | 96 | 42 | 2 |
| shirt | 81 | 76 | 24 | 37 | 20 | 0 |
| backpack | 76 | см. ниже | 25 | 28 | 20 | 3 |
| neck (slot 11) | 34 | 33 | 17 | 10 | 7 | 0 |
| eyes (slot 4) | 10 | 9 | 7 | 3 | 0 | 0 |
| gloves (slot 10) | 0 | 0 | 0 | 0 | 0 | 0 |

Замечания.
- Перчаток в игре нет совсем: ARMOUR со slot=10 не существует ни в ванили, ни в модах. Единственные «перчатки» — наручи/кулаки в других слотах (см. п.3).
- neck = 34, но из них 23 — плащи (ванильный slot 11), настоящих шарфов/банданов только 11 (наши клоны из пояса: Bandana/Black/Red Bandana Small, Neck Rag, Neck Scarf, Neck Scarf [dyed], Rag Scarf x2, Drifter Goggles (neck), Square Goggles - Neck, Swamper's Tooth Necklace). T3 в шее/глазах нет вовсе, T2 в шее только плащи.
- eyes = 10 клонов очков/повязок (Tech Hunters/generic/selfmade), Святая Нация исключена по правилам. Нет T2, нет очков для пустынных.
- backpack: «исп.» по clothing = 0, потому что рюкзак ссылается через CHARACTER.backpack (448 ссылок), а не clothing. По этому аудиту рюкзаки не оценены (отдельный подсчёт, если потребуется).
- Происхождение: belt на 70 % generic (159 из 232) — своих культурных поясов почти нет (15).

## 2. Тонкие клетки (культура x слот, культуры >= 12 вещей, < 2 используемых вещей)

Полный список: `thin_cells` в JSON (155 клеток). Самые показательные (вещей в слоте / в культуре):

| культура | пустые слоты |
|---|---|
| Nomads (13) | boots 0, belt 0, neck 0, eyes 0 (платок-«шаль» есть, но как shirt) |
| Shinobi Thieves (17) | belt, neck, eyes; body 0 |
| Flotsam Ninjas (15) | belt, neck, eyes |
| Shek Kingdom (мало своих) | hat 2, body 0, belt 0, eyes 0 |
| Bounty Hunters (15) | boots, belt, shirt, neck, eyes; legs 1 |
| Tech Hunters (108) | shirt 0, neck 1, belt 5 |
| Traders Guild (12) | boots, belt, shirt, eyes |
| United Cities (61) | belt 0, eyes 0 |
| Mercenary Guild (13), Anti-Slavers (21) | belt, shirt, neck, eyes |
| Holy Nation (61) | eyes 0 (намеренно), belt 2, neck 2 |
| Cannibals (14), Swampers (24), Empire Peasants (16) | belt, shirt, neck, eyes |
| Hive (Western/Southern) | neck, eyes; boots по 1 (наголенники-обмотки) |

Нет перчаток ни у кого. «Нет перчаток для шеков», «нет шарфов пустынным кочевникам» — подтверждено: у Nomads/Shek/Dust Bandits/Sand ninjas нет ни одной вещи в neck и eyes. «Нет ниндзя-перчаток» — подтверждено: в ninja-культурах (Shinobi, Flotsam, Swamp, Sand, Black Dragon, Levi Ronin) нет ни одной вещи для рук; есть Ninja Tabi (boots), маски/капюшоны (hat), пояса только у Swamp Ninjas.

## 3. Кандидаты в мелкие слоты (уже существующие вещи, ещё не клонированные)

Список по именам, не-клонированные, из `small_candidates`:
- gloves/наручи: Cannibal Spiked Vambraces (body, надеты 22), Screeching Vambraces (16) и Moaning Vambraces (14) — Shrieking Bandits, Swamper's Bracers / with Necklace / Bark Bracers (cat's swamp armor), Surgical Undershirt w Gloves (shirt, 96 — медик; это текстура), Power Gauntlets Ultra Warrior/Deathwing/Space Wolf (belt; дикий меш кулака, WH — исключены правилами), Chainsaw Gauntlets, Lord's Mechanical Armguards (Necrons, belt).
- neck: Dust Leather Shawl / Animal Skin Shawl / Cloth Shawl (shirt, 45/44/34 + belt-варианты "(belt)" 61/59/54 — готовые «шали» именно под кочевников), Black Rag Cowl / Rag Cowl / Dyed Rag Cowl (body, selfmade, 50/50/36), Bonedog Mantle (hat), Clown Ruffle, Chef Neckerchief x3 (исключены решением), Imperial Prisoner Collar (hat, исключить), Bone Mantle орков (body, не трогать).
- eyes: Madman Glasses (belt, T1), Desert Mask with Glasses (belt, полумаска — исключена как маска), Visored Helmet семейство (визор — исключено), Leather Eyepatch / Tsuba Eyepatch (hat, selfmade, 34/27 надеты — на шлемовом меше).

Ключевой факт: у шалей уже есть варианты «(belt)» — меш подогнан под пояс, т.е. под клонирование в neck они подходят так же, как Bandana Small из Hats.mod.

## 4. Наборы (сеты)

Найдено 91 набор (префикс имени + мод, >= 3 основных слотов, >= 4 вещей). Полный список в JSON `sets`. Сеты без слота (нет boots/legs/hat): Hazmat/Riot (Driftmetal, нет сапог), Stickperson, Hive, Tsume, Talon, Chef, Surgeon's (нет сапог), Vanguard/Stormtrooper (нет штанов), Wanderer's/Swamper's (нет шлема).

Сломаны случайностью гардероба (носителей >= 20, доля носящих >= 2 слотов сета):
- Clown 1/98, Saxon (Saxon_merc) 0/87, Ronin (Custom Personal Armour) 4/100, Freelance Hunter 4/92, Valac's 1/29, Hell Buster/Survivor/Hound 0-3/24-77, Savage 2/51, Surgeon's 3/63, Wheatstraw 6/126, Holy (holy_lord_phoenix) 2/37, Raider 3/52, Grand Cannibal 6/79.
- WH-сеты: Midnight Lord 18/55 (33 %), World Eater 7/41, Man-Eating Shark 3/24, Ultramariner 10/19. Для силовой брони правило lore_hard.power_armor уже даёт полный сет у PA-фракций; остальной хаос/империал (не в списке factions) собираются случайно.
- Хорошо держатся: Farmers 41/46, Cannibal 43/129, Junk 45/232, Samurai gamedata 233/579 (40 %), Black Templar 9/9, Deathwatch 7/8.
- Ниндзя/самураи: «Samurai/Ronin/Blackened» из Azuchi (нет legs) собираются в 8-30 %; Samurai gamedata — в 40 %. Форма ninja/samurai (добавлена 2026-11-13) помогает только фракциям lore_hard.uniforms.

Причина: гардероб добавляет варианты по каждому слоту независимо (options_per_slot 4-5), поэтому у персонажа с чужим шлемом сохраняется тело сета. Предложение: у шаблонов, которые уже носят >= 1 вещь «малого» сета (<= 15 вещей, один мод, один префикс), выбирать остальные слоты из того же сета с шансом 0.6 (см. 6.8 ниже).

## 5. План заполнения (по возрастанию стоимости)

(a) Реюз: добавить существующую вещь в пул/лавку (правка rules, без новых записей).
(b) Клон: ARMOUR-запись с другим slot, тот же меш/материал (паттерн slots_ext в tools/streams/wardrobe.py, ~стр. 76-125: новая запись по шаблону исходника, `slot` = 4/11, races = человеческое тело минус human_deny_rx, исходник вынимается из НАШИХ пулов, клон идёт в те же VENDOR_LIST (vendor_cap 8) и в context.accessories).
(c) Новая запись: копия записи с перекрашенной текстурой/другим именем/ценой (меш тот же).

Риски: меш, сделанный под пояс, прикрепляется к кости пояса; в шею он «сядет» ниже, чем шарф, если его не подогнать (в EIS слотах положение определяется плагином, подтвердит только игра). Меши чужого скелета дают растяжку на редких анимациях (tools/fast/mesh_skel.py проверяет вершинные веса против male/female_skeleton) — перед включением каждого нового клона прогонять `python -I -X utf8 tools/fast/mesh_skel.py <папка мода>`. Игру не запускать (правило) — рендер проверяется в игре.

## 6. Десять самых важных дыр и решение для каждой

1. Перчаток нет вообще; секцию gloves плагин у NPC не наполняет (сейв 2026-11-13). Решение (a/b): не возвращать клоны slot 10 для NPC. Дать «наручи» как belt-вещь: Vambraces (Cannibal/Shrieking), Swamper's Bracers уже в body — оставить; для лавок: клоны наручей в gloves-слот только в VENDOR_LIST (игрок вручную надевает; проверить на сейве, ложится ли в секцию). Ниндзя «kote»/шеки «cloth wraps» — вариант (c): перекраска Vambraces (мех/шипы убрать нельзя без меша, поэтому только Light Body Wrap/Dark Body Wrap из shirt как «обмотки рук», Shrieking Bandits, уже есть).
2. Шарфы для пустынных (Nomads/Shek/Dust Bandits/Sand ninjas) — 0. Решение (b): клонировать «Dust Leather Shawl (belt)», «Animal Skin Shawl (belt)», «Cloth Shawl (belt)» (надеты 61/59/54, продаются в 6 лавках) в neck; origin culture Nomads -> Shek/Dust Bandits по сходству climate: desert. Лор: шаль кочевников, T0-T1, лавки «Nomad *». Риск: меш уже «belt» — ок как у Bandana Small.
3. Ниндзя-шея (Shinobi Thieves, Flotsam, Swamp, Sand, Black Dragon): 0 neck/eyes/belt. Решение (b): клон Ninja Hood/Black Bandana (hat T0, надето 26-60) -> в neck НЕ делать (дубль головы). Лучше (a): Bandana Small (neck, T0) в аксессуарный пул ninja-фракций с весом 0.5 и Rag Scarf (colored) для Shinobi Thieves; для «черного шарфа» (c) — Black Bandana Small перекрасить в тёмно-красный (Flotsam) переименованием и ценой.
4. Очки только у Tech Hunters/generic, ни одной вещи для Nomads/Shek/Dust Bandits (песчаные бури). Решение (a): в context.accessories добавить Ashlander Stormgoggles / Small и Square Goggles Small в пулы Nomads, Shek, Dust Bandits, Sand ninjas, Traders Guild (лавки уже продают Traders — исходный текст «стандарт Traders Guild»). Ноль новых записей.
5. T2/T3 в neck и eyes пусты. Решение (c): 2-3 «элитных» шарфа T2 (Holy Lord's Cloak уже T2; для UC/Shek — Emperor-стиль перекраской Neck Scarf [dyed], цена x4, имя «Silk Scarf»), и 2 очков T2 (Ashlander Stormgoggles с лучшей защитой). Лавки: «armour shek» / UC. Риск: цена/статы по шкале группы, не выходить за T2.
6. Нет сапог: Nomads, Traders Guild, Bounty Hunters, Hive (по 1 обмотке), у сетов Hazmat/Riot/Tsume/Talon/Hive. Решение (a): пулы сапог по сродству стиля (generic boots T0/T1, 96 вещей) в fill_empty armour:boots 0.35 -> поднять до 0.6 для этих фракций; никаких новых вещей.
7. Нет поясов у UC/Mercenary/Anti-Slavers/Traders/Cannibals/Swampers: 159 из 232 поясов generic. Решение (a): fill_empty armour:belt 0.3 -> 0.5 для городских фракций, очки/шарфы клонов вынимают пояс, поэтому освобождённый слот надо возвращать generic-поясами.
8. Сеты ломаются случайностью (Saxon 0/87, Clown 1/98, Ronin 4/100, Freelance 4/92, Holy phoenix 2/37, Midnight Lord 18/55). Решение (a) в wardrobe.py: «пакеты сета» — если выбрана вещь сета из <= 15 вещей одного мода, остальные слоты подтягиваются из того же сета с шансом 0.6 (аналог power_armor.set_slots, но мягкий). Сеты без слота (Hazmat, Riot, Hive, Tsume, Talon: нет сапог; Vanguard: нет штанов) закрывать generic-слотом по стилю.
9. Перчатки/наручи для Shrieking Bandits/Cannibals/Swampers уже есть (Vambraces), но лежат в body — занимают тело. Решение (b): клон Vambraces/Bracers в belt-слот (меш-наручи, как Power Gauntlets) для дикарей: тело остаётся торсом. Лор: Babbler/Howler (Shrieking), каннибалы; savage_rx оставляет только своей культуре. Риск: меш-наручи привязаны к рукам; на body-скелете ок, в belt-слоте положение проверит игра; mesh_skel обязателен.
10. Шеки: культура Shek Kingdom: hat 2, body 0, belt 0, eyes 0, neck 1 (Cloak SK + Square Goggles - Neck с расой Shek). Решение (a)+(c): Shek получают Cloth Shawl/Rag Scarf (шеки носят платки, лор — воины с повязками), «воинская повязка» как перекраска Red Bandana Small (имя «Shek Warband», T1), лавки «armour shek». Это одновременно ответ на «перчатки шеков»: у них сохраняются кисти без вещей (раса Shek не носит человеческие перчатки), дыру закрывает шея.

## 7. Порядок работ (когда разрешено править)

1. Только правила (a): accessories-пулы очков/шарфов для desert/ninja, fill_empty belt/boots — безопасны для сейва (save-safe), без новых sid.
2. Клоны (b): 3 шали, 1 набор наручей в belt для дикарей — новые sid в KMM_Wardrobe; проверить mesh_skel, vendor_cap, races; бэкапы wardrobe.json/py по образцу *_pre_slots.
3. Новые записи (c) T2 и «пакеты сетов» — после результата плейтест по шее/очкам (видны ли в игре).

Не делать без согласия: удаление sid, зоны, правки текущего прохождения (save-safe режим).
