# JUNK_AUDIT — мусор от модов (генерируется tools\junk_audit.py, только чтение)

Метод и ограничения: см. докстринг скрипта. «Недостижима» = не найдена в графе порождения из ванили/корневых типов мира; нативные вызовы движка по имени не видны, поэтому перед резкой чисткой смотреть строку «Решение». Сейвы не сохраняем (новая игра).

Записей в цепочке: 147904, достижимых: 89177, игра отвергает (rejected): 311.

## 1. Недостижимые записи (создано модом, ни от чего не порождается)

| Тип | создано модами | недостижимо | топ модов-источников |
|---|---|---|---|
| DIALOGUE | 3826 | 1228 | Weird recruit.mod 191, Dialogue.mod 171, Strangers and Freaks.mod 140, Band of Exiles.mod 114, Radiant Ancient Hive.mod 65 |
| CHARACTER | 2424 | 896 | KMM_Traces.mod 625, rebirth.mod 29, Dialogue.mod 28, TEXT TEXTURE.mod 22, Rent Hous in Your Town Mod.mod 15 |
| SQUAD_TEMPLATE | 2670 | 834 | KMM_Traces.mod 527, rebirth.mod 49, Dialogue.mod 31, TEXT TEXTURE.mod 27, Rent Hous in Your Town Mod.mod 19 |
| DIALOGUE_PACKAGE | 788 | 214 | Dialogue.mod 35, Band of Exiles.mod 35, Strangers and Freaks.mod 19, TEXT TEXTURE.mod 13, Weird recruit.mod 12 |
| BUILDING | 4937 | 162 | Newwworld.mod 43, CBT Faction Furniture.mod 22, Soulbody.mod 16, Forgotten Buildings.mod 14, rebirth.mod 10 |
| ITEM | 1109 | 80 | Faction Caravans.mod 17, shoppingecon.mod 9, KMM_Diplo.mod 8, Newwworld.mod 7, rebirth.mod 5 |
| ARMOUR | 1593 | 53 | Vanguad_mercenares.mod 16, bull armor.mod 15, TEXT TEXTURE.mod 7, Wolf_Headgear.mod 4, ghillie_billie.mod 1 |
| FACTION | 211 | 46 | TEXT TEXTURE.mod 12, ChildrenOfKenshi.mod 7, MotokoTheHuntress.mod 5, Newwworld.mod 3, Rusty Raiders FACTION.mod 3 |
| VENDOR_LIST | 413 | 32 | Dialogue.mod 6, rebirth.mod 5, Expanded Vanilla Armor.mod 3, Soulbody.mod 3, Guild of Surgeons.mod 2 |
| RACE | 310 | 24 | Wolf_Headgear.mod 10, RadiantFaces.mod 3, Newwworld.mod 2, Animation - Collection Pack.mod 2, GreatDirewolf.mod 2 |
| ANIMAL_CHARACTER | 221 | 22 | Aminals.mod 4, GreatDirewolf.mod 3, Skimmer Broods.mod 2, Old_ironsides_merged.mod 2, Beak_Thing_Scarf.mod 2 |
| CONTAINER | 210 | 8 | Subspecies.mod 2, CBT Cozy Furniture.mod 2, GreatDirewolf.mod 1, Symbiosis.mod 1, HTT_Cloaks.mod 1 |
| WEAPON | 265 | 5 | Goat is strong animal.mod 1, Dark Hive.mod 1, Band of Exiles.mod 1, Iron Wasp.mod 1, KMM_Glue.mod 1 |
| HEAD | 1211 | 5 | RadiantFaces.mod 2, Tribal Hiver Face Paint.mod 1, Hivers - Collection Pack.mod 1, TEXT TEXTURE.mod 1 |
| MAP_ITEM | 49 | 3 | rebirth.mod 1, Dark Hive.mod 1, TEXT TEXTURE.mod 1 |
| CROSSBOW | 71 | 2 | KMM_Glue.mod 1, KMM_Wardrobe.mod 1 |

Заглушки отсутствующих модов (compat-патчи; создатель не в сборке): 32429 записей [('DIALOGUE_LINE', 9987), ('DIALOG_ACTION', 7163), ('ARMOUR', 5760), ('RACE', 1643)]; носители: Animation - Collection Pack.mod 7459, gamedata.base 4002, Dialogue.mod 3216, Kaizo.mod 3182, rebirth.mod 2263. В таблице выше они НЕ учтены.
Каталог гардероба: 2460, из них недостижимо в графе: 21 (если >0 — пулы не доходят до игры); модовых брони/оружия вне каталога и недостижимых: 39.

Фракции без членов/городов/отрядов: 40 (топ: TEXT TEXTURE.mod 11, ChildrenOfKenshi.mod 7, MotokoTheHuntress.mod 5, Newwworld.mod 3, Rusty Raiders FACTION.mod 3, rebirth.mod 2).
Модовые расы: 310, без персонажей/фракций/групп: 15, из них недостижимых: 15 (топ: Wolf_Headgear.mod 10, Animation - Collection Pack.mod 2, Newwworld.mod 1, Thrasher_Warbot.mod 1, Symbiosis.mod 1).

## 2. Отладка/заглушки по имени

| Тип | записей | достижимых | моды |
|---|---|---|---|
| SQUAD_TEMPLATE | 71 | 11 | TEXT TEXTURE.mod 15, Dialogue.mod 6, rebirth.mod 5, Animal Variations.mod 4 |
| CHARACTER | 48 | 11 | Dialogue.mod 4, TEXT TEXTURE.mod 4, LFW - INFINITE.mod 3, HeatCoilCleaver.mod 3 |
| DIALOGUE | 37 | 9 | Dialogue.mod 12, hippity hoppity you're now my property.mod 7, Holy Nation Brides.mod 3, Band of Exiles.mod 3 |
| DIALOGUE_PACKAGE | 15 | 3 | hippity hoppity you're now my property.mod 6, LorrMoreConversations.mod 2, Rusty Raiders FACTION.mod 2, Dialogue.mod 1 |
| ITEM | 8 | 5 | Companion Quest - Morse.mod 3, Band of Exiles.mod 1, ScarierSpiders.mod 1, BeakThingEggFoods.mod 1 |
| BUILDING | 6 | 3 | The Shoddy Firearm Mod.mod 3, Newwworld.mod 1, rebirth.mod 1, CBT Cozy Furniture.mod 1 |
| ARMOUR | 6 | 3 | Sacred Trash.mod 2, Newwworld.mod 1, Expanded Vanilla Armor.mod 1, Side Quest.mod 1 |
| VENDOR_LIST | 5 | 2 | rebirth.mod 1, Exile Camp Expanded.mod 1, Guild of Surgeons.mod 1, Soulbody.mod 1 |
| RACE | 3 | 1 | Animation - Collection Pack.mod 2, Rusty Raiders FACTION.mod 1 |
| FACTION | 3 | 0 | Band of Exiles.mod 1, HTT_Cloaks.mod 1, Kaizo.mod 1 |
| RESEARCH | 3 | 3 | Wooden Dexterity Training Dummy.mod 1, Expanded Vanilla Armor.mod 1, Sacred Trash.mod 1 |
| WEAPON | 1 | 1 | Animal Variations.mod 1 |
| ANIMAL_CHARACTER | 1 | 0 | Guild of Surgeons.mod 1 |
| CONTAINER | 1 | 0 | TEXT TEXTURE.mod 1 |

Примеры (достижимые — самые заметные игроку):
- BUILDING: Drill Dummy MkI (5007317-The Shoddy Firearm Mod.mod)
- BUILDING: Drill Dummy MkII (5007318-The Shoddy Firearm Mod.mod)
- BUILDING: Drill Dummy MkIII (5007319-The Shoddy Firearm Mod.mod)
- ARMOUR: Black Rag Shirt copy (63234-Newwworld.mod)
- ARMOUR: aaClothpants UNUSED (219-Expanded Vanilla Armor.mod)
- ARMOUR: #MAGICAL CUBE TESTER (178-Sacred Trash.mod)
- DIALOGUE: Gate fee --Unfinished-- --DISCARD-- (9620-Dialogue.mod)
- DIALOGUE: Gate fee --Unfinished-- --DISCARD-- (7340-Dialogue.mod)
- DIALOGUE: delete (96978-Dialogue.mod)
- SQUAD_TEMPLATE: Gurgler town squad copy (96562-Dialogue.mod)
- SQUAD_TEMPLATE: hub squatters copy berserker (64223-rebirth.mod)
- SQUAD_TEMPLATE: Weird Test (5008588-Weird recruit.mod)
- CHARACTER: Wanderer copy (43985-rebirth.mod)
- CHARACTER: Wanderer copy (193-Animal Variations.mod)
- CHARACTER: SethWeak Copy (2757807-GreatDirewolf.mod)
- DIALOGUE_PACKAGE: nomads (wip) (4999505-hippity hoppity you're now my property.mod)
- DIALOGUE_PACKAGE: Brain Package copy (5007777-Rusty Raiders FACTION.mod)
- DIALOGUE_PACKAGE: Debug guide (5009496-Rusty Raiders FACTION.mod)
- VENDOR_LIST: medical supplies copy (1533679-Guild of Surgeons.mod)
- VENDOR_LIST: skin gear copy (5025523-Rusty Raiders FACTION.mod)
- RACE: skeleton debug (5025849-Rusty Raiders FACTION.mod)
- ITEM: #f3f6f4Modders Resource (1048-Companion Quest - Morse.mod)
- ITEM: #f3f6f4Dialogue Creation Tips (1049-Companion Quest - Morse.mod)
- ITEM: Activation Key #7279 (2758008-ScarierSpiders.mod)
- ITEM: Beak Thing Egg [Unused] (50606-BeakThingEggFoods.mod)
- ITEM: WANTED: The Red Bandit copy (1535131-Books+.mod)
- WEAPON: _duck type weapon copy (226-Animal Variations.mod)
- RESEARCH: Dexterity Training Wooden Dummy (1534076-Wooden Dexterity Training Dummy.mod)
- RESEARCH: Clothpants UNUSED (232-Expanded Vanilla Armor.mod)
- RESEARCH: !@# sacred trash test research 01 (177-Sacred Trash.mod)

## 3. Битые ссылки и отвергнутые игрой записи

Ссылок на несуществующую запись: 11; на rejected: 3; rejected-sid всего: 311.
Топ модов по битым: MysteriousWanderer.mod 5, Rusty Raiders FACTION.mod 3, Dialogue (10).mod 2, Dialogue.mod 1
По типам: DIALOGUE_LINE.target has item 5, DIALOGUE_LINE.lines 4, DIALOGUE_LINE.target race 2

## 4. Near-дубли

Фракции с одинаковым именем: 10 групп (лишних 10). Топ: The Holy Nation x2, Outlaw x2, Second Empire x2, Old Machines x2, Holy Nation Outlaws x2, Drifters x2, Gutters x2, White Wolves x2, Gunsmiths x2, Imperial Expedition Remnants x2
Предметы с одним мешем/текстурой, разными именами и разными модами: 56 групп, лишних 101 (точные клоны внутри мода — в docs\DEDUP.md). Топ: Bandana Small x26; Iron Black Carapace Hat x8; Black Rag Shirt x4; Ancient Praetorian Armour x4; Ancient Samurai Helmet Small x4; Medic helmet x4; Drifter's Goggles x4; Neck Scarf x4.

## 5. Мёртвый груз: моды без единой достижимой ключевой записи

| Мод | создано | ключевых | недостижимые типы |
|---|---|---|---|
| CATO V4.mod | 19 | 7 | {'BUILDING': 7} |
| TK Clean Fix.mod | 524 | 4 | {'DIALOGUE': 3, 'DIALOGUE_PACKAGE': 1} |
| RadiantHiveBirthing.mod | 4 | 4 | {'CHARACTER': 3, 'RACE': 1} |
| DarkHiveBirthing.mod | 7 | 3 | {'CHARACTER': 3} |
| Animation - Collection Pack.mod | 2 | 2 | {'RACE': 2} |
| Dread Limbs.mod | 7 | 2 | {'VENDOR_LIST': 2} |
| Goat is strong animal.mod | 6 | 1 | {'WEAPON': 1} |
| Unique Recruits Traditional Colors.mod | 54 | 1 | {'ARMOUR': 1} |
| Hivers - Collection Pack.mod | 1 | 1 | {'HEAD': 1} |

Почти целиком недостижимые (<30%, от 10 ключевых):

| Мод | ключевых | достижимо | доля |
|---|---|---|---|
| Wolf_Headgear.mod | 15 | 1 | 0.067 |
| Trecherous Southern Hive.mod | 13 | 1 | 0.077 |
| Talkative Kenshi.mod | 69 | 7 | 0.101 |
| shoppingecon.mod | 12 | 2 | 0.167 |
| Faction Caravans.mod | 41 | 9 | 0.22 |
| Holy Courtship.mod | 28 | 7 | 0.25 |
| Weird recruit.mod | 272 | 69 | 0.254 |
| Neep-a.mod | 28 | 8 | 0.286 |
| Danny Boy.mod | 48 | 14 | 0.292 |

## 6. Предложения (по заметности игроку)

Механизмы: CUT = rules\excluded_mods.json (mods целиком / items поштучно), удаление sid в KMM_Cleanup/KMM_Fix, rejected-sid; REIMPL = поток wardrobe/economy (пулы, vendor lists, loot), KMM_Town; KEEP = оставить.

| # | Действие | Объём | Механизм | Решение |
|---|---|---|---|---|
| 1 | Достижимые отладочные записи (copy/test/debug/DISCARD/wip): CHARACTER 11, SQUAD_TEMPLATE 11, ITEM 5, RESEARCH 3 ("sacred trash test research", "#MAGICAL CUBE TESTER", "skeleton debug") | см. раздел 2 | удалить sid в KMM_Fix / items-исключения | CUT |
| 2 | Недостижимые диалоги: DIALOGUE 1228, DIALOGUE_PACKAGE 214 (Weird recruit, Strangers and Freaks, Band of Exiles, Talkative Kenshi) | см. раздел 1 | отключить моды-доноры целиком, где достижимо <30% (раздел 5) | CUT мод / REIMPL привязкой к фракции |
| 3 | Недостижимые CHARACTER/SQUAD_TEMPLATE мод-создателей (кроме KMM_*): CHARACTER 896, SQUAD 834 | раздел 1 | вшить в бары/отряды фракций через KMM_Town (REIMPL), иначе вырезать; KMM_Traces — спавн из Lua, не трогать | REIMPL / KEEP |
| 4 | Модовые расы без носителей (15), особенно Wolf_Headgear (перекраски собак/раптоналов) | раздел 1 | исключить мод или слить с ванильной основой (race_audit.py) | CUT |
| 5 | Фракции без членов/городов: 40 (TEXT TEXTURE, ChildrenOfKenshi, MotokoTheHuntress, Rusty Raiders) | раздел 1 | исключить мод либо отдать фракции отряды | CUT |
| 6 | Заглушки отсутствующих модов: 32429 записей, из них достижимых 14399 (носители ACP, Kaizo, Social Lives, Talkative Kenshi) | раздел 1 | обновить rules\game_rejected_sids.json по свежему логу; проверить, нужны ли патчи-носители | CUT / проверка |
| 7 | Недостижимые BUILDING 162 (Newwworld 43, CBT Faction Furniture, Forgotten Buildings) | раздел 1 | KEEP ядро Newwworld; CBT/Forgotten — исключить записи | CUT частично |
| 8 | Недостижимые ITEM 80 (Faction Caravans 17, shoppingecon 9) и ARMOUR 53: Vanguad_mercenares, bull armor | раздел 1 | положить в vendor/wardrobe пулы культуры (Vanguad - наёмники Tech Hunters/United Cities; bull armor - Shek) либо исключить | REIMPL |
| 9 | Near-дубли брони между модами с тем же мешем: 56 групп, лишних 101 (Bandana Small x26) | раздел 4 | rules\dedup_canonical.json | CUT дубль |
| 10 | Фракции-двойники по имени (10): Holy Nation (cook_set), Second Empire/Drifters/Holy Nation Outlaws (Band of Exiles), Old Machines (HTDEnforcers) | раздел 4 | слить в ванильную через glue/редирект ссылок, либо переименовать | CUT |
| 11 | Битые ссылки (11 штук, в диалогах MysteriousWanderer, Rusty Raiders, Dialogue (10)) | раздел 3 | почистить условия или отключить мод | CUT |
| 12 | Мёртвый груз (0-1 достижимых ключевых записей): CATO V4, TK Clean Fix, RadiantHiveBirthing, DarkHiveBirthing, Dread Limbs, Goat is strong animal | раздел 5 | excluded_mods.json -> mods (проверить, что нет модов-зависимых) | CUT |
| 13 | KMM_Traces: ~1150 CHARACTER/SQUAD недостижимы в графе: спавнятся из Lua по имени — не баг, но не видны статическому аудиту; проверить, что имена в Lua совпадают | раздел 1 | KEEP | KEEP |
| 14 | Тренировочные манекены (Training Dummy, Drill Dummy) — легитимные постройки | раздел 2 | KEEP | KEEP |
| 15 | Книги/записки на общем меше (ITEM ~450 в 2 группах) — безвредны | DEDUP.md | KEEP | KEEP |
