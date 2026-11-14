# Е3 Личные вещи в сумках NPC: разведка (2026-11-14, только чтение)

## 1. Что уже есть в сборке
Механизм Е3 наполовину построен: поток wardrobe (tools/streams/wardrobe.py, правила rules/streams/wardrobe.json, раздел "loot") уже кладёт хлам в CHARACTER "inventory".
- Поле: CHARACTER.inventory, тип ссылки ITEM, значения (количество 1, шанс %, 0). Рюкзак: CHARACTER.backpack (CONTAINER slot 12, значение 1 = абсолютный шанс). Одежда, оружие: clothing, weapons (val2 = шанс). engine_lookup: "CHARACTER.inventory [] ITEM (1)"; у ANIMAL_CHARACTER inventory другой тип (VENDOR_LIST, val0 = шанс), его не трогаем.
- Параметры loot: share 0.95 шаблонов, 2-5 вещей, item_chance 60 %, cap_soft 90 (потолок размещений одной вещи), пул data/catalog_loot.json (138 вещей, kinds: junk 61, food 40, book 22, luxury 10, drug 5), фильтр bad_rx (квестовое, letter/note/map/contract, relic и т.д.), value_cap по ярусу богатства: poor 900, mid 2500, rich 6000.
- Выбор вида вещи идёт по ярусу богатства (poor/mid/rich), а не по фракции и биографии. Итог по wardrobe_repeat_stats: у 88.7 % шаблонов есть лут, 131 разная вещь, максимум 65 размещений одной вещи.
- Пробел Е3: нет привязки к архетипу ("у бандита самокрутки, у солдата паёк"), записки и письма отфильтрованы bad_rx, поэтому читаемого лута нет.

## 2. Ванильные предметы (data/items_audit.json, data/catalog_loot.json)
Группы (все моды): food 131, drug 30, book 453, trinket 11, map 49, trade 383.
Еда (vanilla/rebirth/changes_otto): Bread 1946-gamedata.base (240), Rice Bowl 1016-gamedata.base (907), Potatoes 1960-gamedata.base (300), Dried Meat 42334-changes_otto.mod (160), Dried Fish 50518-Newwworld.mod (120), Chewsticks 43956-rebirth.mod (240), Dried Gristle Flaps 50568-rebirth.mod (40), Dustwich 43961-rebirth.mod (600), Meatwrap 43960-rebirth.mod (1500), Ration Pack 42337-changes_otto.mod (2400), Ancient Nutri-Rations 62173-rebirth.mod (2400), Water Jug 12617-nodes_otto.mod (50), Cooked Vegetables 43955 (907).
Из gastronom.mod дёшево: Smoked Fat 14-test.mod (150), Eye Soup 34 (150), Dried Cartilage 155 (150), Dried Ears 32 (400), Cheese 24 (250).
Пойло и дурь (type ITEM, группа drug): Grog 42311-changes_otto.mod (150), Sake 42310 (150), Bloodrum 43316-rebirth.mod (150), Cactus Rum 1015-gamedata.base (500), Hashish 1230-gamedata.base (800), Garru Dust 55-NewItemsGoR.mod (1000). Отдельных "самокруток" и табака в ванили нет; ближайшее: Hemp 1965 (100), Chewsticks.
Трофеи и мелочь: Raw Stone 1515 (60), Leather 2292 (400), Fabrics 584 (300), Lantern 5348 (200), Parchment 16856-nodes_otto1.mod (300), Cat-Lon Socks 59-NewItemsGoR.mod (1295), Cats 54546-Newwworld.mod (1) и String of Cats 54549 (10, группа trinket, но quest=True).
Книги и записки: ванильный Dialogue.mod даёт тип ITEM с текстом (читается как книга): письма (Letter From A Swamper I-V 49480.., Letter To Hash/Darkbrow/Moll, Letter Of Farewell 49493, Letter Of The Condemned, Suicide Note), дневники (Maril's Diary I-III 49199.., Captive's Journal I-IV), служебное (Memo From Big Grim 49478, Memo From Moll 49495, Ludin's Report I-III, Priest Varloo's Note 49786, Priest Tyluig's Note 49787, Holy Edict), священное (The Guiding Light I-VI 100-150, Scripture of Radiance I-V 150, Book Of Grace 50383, The Holy Crusade 49051), шековское (Kral's Last Stand, Way Of The Warrior, King Shager's Reign, Shager's Overthrow, 200), газеты (United Weekly I-VII 100, Revolution Weekly I-VII 100 из Books+), WANTED-листки (0-10), легенды (Legend of the Mist Ghoul и др., 0). Книги Books+.mod (Shek Diary 1535184, Trader's Mail I-IV 100, Poem of the Warrior). Часть писем в Dialogue.mod квестовая (quest=True: Letter From A Swamper II) и помечена как нужная диалогам, их не раздавать. Value у писем 0: безопасно для экономики, не продаются.
Карты (MAP_ITEM, rebirth.mod): Map of the Swamps 51404 (500), Map to Mongrel 44917 (500), Tech Hunter Library Map 51405 (100). Это уже не быт, а наводки; не включать в массовый лут.
Произвольный текст: ни у ITEM, ни у BOOK в engine_lookup нет поля текста в самом предмете (текст книги берётся из локали/диалогов мода Dialogue). Свой текст данными не сделать; только через Lua createItem (путь KMM_Stock) или новый мод-текст, что вне Е3-данных.

## 3. Шанс, количества, экономика
- Шанс: у CHARACTER inventory третье значение ссылки (item_chance) работает как абсолютный шанс на каждую вещь, как у weapons val2; в нашем пайплайне это 60 %. Количество всегда 1 в нашей генерации; мин/макс диапазона нет, разнообразие даёт число записей (2-5) и независимый шанс каждой. Значит "не у каждого бандита хлеб" решается шансом 15-40 % на запись, а не диапазоном.
- Лут с трупа и рюкзак: рюкзак уже ставится у 541+ NPC (BPR chance_by_role 20-55 %), вещи в inventory идут в карманы персонажа; при смерти попадают в лут.
- Экономика: реальный риск не цена, а объём. Дешёвая еда (до 300) безвредна, продаётся за копейки. Опасны вещи 1500+ (Meatwrap, Ration Pack 2400, Hashish 800 в числе, Western Mead 5000, Great White Claw 5000 в пуле luxury). Пул luxury с value_cap rich 6000 сам по себе эксплойт: убил охранника, продал вещь за тысячи. Предлагаю потолок 400 для любых личных вещей, 1000 только для элитных архетипов и шанс до 10 %.
- Книги дают небольшой доход (100-200), но Dialogue-письма value 0, поэтому они лучший "красивый и безопасный" лут.

## 4. Предложение по архетипам
Правило: цена вещи не выше потолка; шанс на запись; максимум 3 записи на шаблон.
- Бандит (Shrieking Bandits, Dust Bandits, Hungry Bandits): Dried Meat 42334 (25 %), Bread 1946 (20 %), Grog 42311 (30 %), Chewsticks 43956 (20 %), Hemp 1965 (10 %). Потолок 300. Редко (5 %): Letter From Bad Teeth или Note From Blue Eyes (Dialogue, value 0, не квестовые).
- Подполье (Shinobi Thieves, Slave Traders, Flotsam): Hashish 1230 (12 %, потолок 800 только здесь), Cactus Rum 1015 (20 %), Cheese 24-gastronom (15 %), Parchment 16856 (10 %), Letter To Hash 49477 (5 %).
- Солдат и стража (United Cities, Empire, Tech Hunters, Anti-Slavers): Ration Pack 42337 (15 %, 2400 -> потолок 400 не проходит, поэтому заменить на Dustwich 43961 (600, 10 %) или Bread 25 %), Dried Fish 50518 (20 %), Sake 42310 (15 %), United Weekly I-VII (Books+ / Dialogue, value 100, 10 %), Memo From Moll как редкая записка (3 %).
- Кочевник и бродяга (Nomads, Drifters, Traders): Water Jug 12617 (35 %), Bread 25 %, Potatoes 1960 (15 %), Dried Gristle Flaps 50568 (25 %), Trader's Mail I-IV (Books+, 100, 8 %).
- Святая нация: Bread 20 %, Rice Bowl 1016 (15 %), The Guiding Light I-VI (100, 20 %), Scripture of Radiance I-V (150, 10 %), Book Of Grace 50383 (5 %). Алкоголя нет (по лору).
- Шек: Rice Bowl 20 %, Sake 20 %, Dried Meat 15 %, Kral's Last Stand / Way Of The Warrior (200, 8 %), Shek Diary 1535184 (5 %).
- Каннибал и дикарь (Cannibals, Fogmen, Swampers): Dried Ears 32-gastronom (400, 15 %), Eye Soup 34 (150, 15 %), Smoked Fat 14-test.mod (150, 20 %), Dried Gristle Flaps 25 %, Letter From A Swamper I, III (Dialogue, 3 %), Captive's Journal I-IV (Dialogue, 3 %, мрачная находка). Без Bread.

## 5. Куда встраивать
- Прямо в tools/streams/wardrobe.py на месте блока "хлам и лут" (строки ~828-845): добавить в rules/streams/wardrobe.json секцию "loot.by_faction" (список {faction_rx или культура, items: [{sid, chance, cap}], max}) и применять после текущего случайного выбора, либо вместо него для фракций из списка. Фракция персонажа уже вычисляется через fprof(fname); культуры берутся из catalog (поле культуры по носителям).
- Параллельно закрыть пробел: убрать "note|letter" из bad_rx только для белого списка sid писем (не квестовых, quest=False в items_audit) и поставить для них отдельную группу "paper" в tools/catalog.py (catalog_loot.json), иначе письма не попадут в пул.
- Зависимости: KMM_Wardrobe уже владеет полями inventory/backpack (DECISIONS 2026-11-12), новых потоков не нужно. Lua KMM_Stock не нужен.

## 6. Риски
- Раздувание сейва: у 88.7 % шаблонов уже есть лут, каждая запись создаёт предметы при спавне; добавление ещё 1-3 записей на шаблон увеличит число предметов в мире примерно на 20-40 %. Лучше заменить часть общего лута архетипным, а не добавлять сверху (держать итоговое 2-5 записей).
- Эксплойт ценности: следить за потолком; не использовать luxury (Great White Claw 5000, Western Mead 5000) в массовых архетипных наборах.
- Квестовые/диалоговые письма (quest=True) могут ломать квестовую логику Dialogue.mod при раздаче; брать только quest=False.
- Тип quest=True у Cats, String of Cats, Hashish, Cactus Rum в items_audit: проверить, что флаг означает "участвует в квестах/рецептах", а не запрет; Hashish и Cactus Rum уже в пуле catalog_loot, значит запрета нет.
- Моды-источники лута уже в сборке: gastronom, Buzzing, Books+, Pizza_Time, NewItemsGoR, rebirth, changes_otto (они в mods белого списка loot). Отдельных модов "личных вещей" в docs/MODS_AUDIT.md и docs/DEDUP.md не найдено.
- Не проверено: фактическое игровое поведение шанса inventory (без запуска игры); подтвердить сейвом или логом после следующей сессии (playtest first).
