# PALETTE — убрать обилие перекраски (аудит 2026-11-14)

Скрипт: `python -I -X utf8 tools/palette_audit.py` (~11 с, только чтение). Выход: `data/palette_audit.json`, `rules/streams/palette_proposal.json`. Предложение НЕ применено.

## Цифры
- Каталог ARMOUR: тёмных 257, нейтральных 195, ярких 201, цвет не определён 1294 (имя без цвета, нет COLOR_DATA — считаем нейтральным).
- Выдачи NPC (ссылки clothing в build/KMM_Wardrobe): всего ~25 тыс.; ярких 1290 (5%), тёмных 2505, нейтральных 4126, неизвестных 17036.
- Яркие по цвету: dyed (без названия цвета) 487, white 241, red 193, yellow 179, purple 67, blue 37, cyan 36, orange 33, gold 13, green 4.
- Топ фракций по ярким выдачам: без фракции 229, Shrieking Bandits 119 (30% их выдач; все 19 NPC), Holy Nation 90, United Cities 88, Drifters 75, Shek 39, Mercenary Guild 33, Tech Hunters 31, Southern Hive 31, Adventurers Guild 28, Slave Traders 28, Swampers 27. Полный топ-30: `bright_by_faction_top30`.
- Топ модов: rebirth 291, ShriekingBandit_Expansion 179, gamedata.base 158, Dialogue.mod 102 (всё яркое), TEXT TEXTURE 92, Expanded Vanilla Armor 90, Billyro Masks 79, Newwworld 69, Azuchi 60, Sacred Trash 51.
- Фракции со схемой цвета: 72 из 285. Яркие схемы у ванильных: United Heroes League, Imperial Lords, Slave Traders, Free Traders, Western Hive, Red Sabres, Crab Raiders, Grass Pirates, Second Empire. У модовых: Oni, Dark Reavers, Red Hive, Levi Ronin, Final Enforcers, Rusty Raiders, Missionaries, Nagata/Tengu Ronin, Fish Isle, South Exiles (Tengu Ronin 25DABF бирюза и Missionaries белый/голубой — самые кричащие).
- Перекраска схемой фракции ("dont colorise"=False) считается отдельно (`scheme_bright_tinted_refs`): Shek 311, Slave Traders 198 ссылок. Ванильная механика, мы её не трогаем.

## Предложение (rules/streams/palette_proposal.json)
- `default_allowed`: dark, neutral.
- `faction_bright_ok`: Holy Nation и её отщепенцы — белый/золото/синий; Red Sabres — красный; Shek и Taste of Shek — красный/оранжевый; United Cities, Traders Guild, Trade Ninjas — красный/синий/золото; Swampers, Swamp Ninjas/Creatures/Things — зелёный. Остальным только тёмное и нейтральное. Розовый/фиолетовый/бирюзовый/жёлтый/"dyed" нигде не разрешены.
- `bright_item_sids_to_drop_from_pools`: 126 вещей (глобально выпадают из пулов).
- `bright_item_sids_faction_only`: 74 вещи, разрешены только фракциям из `allowed_factions`.
- `families_keep`: по каждому семейству перекрасок (dedup_canonical families) какие члены оставить; если все яркие, остаётся один.
- Оговорка: классификация по имени/семейству/hex; 1294 вещи без цвета проходят как нейтральные. Силы "Space Marine" (жёлтый по hex) в drop попадут автоматически.

## Как подключить в tools/streams/wardrobe.py (не правил)
1. В начале `build()` после `DP = rules.get("dedup_pools", {})` (~стр. 126) загрузить `PAL = json.load(open(r"C:/KenshiModMap/rules/streams/palette_proposal.json"))`; `DROP = set(PAL["bright_item_sids_to_drop_from_pools"])`; `FONLY = PAL["bright_item_sids_faction_only"]`.
2. Фильтр лежит в `coh(lst, fname)` (~стр. 262): все пулы фракции (`trade`, `common`) проходят через неё. Добавить в обе ветки (и в ветку `if not pr: return lst`) условие `pal_ok(y, fname)`:
   `pal_ok = lambda y: y["sid"] not in DROP and (y["sid"] not in FONLY or fname in FONLY[y["sid"]]["allowed_factions"])`.
3. В `pools(fname)` (~стр. 269) `own`, `trophy`, `selfmade` в `coh` не попадают — обернуть и их: `own: [y for y in own.get(fname, []) if pal_ok(y)]`, то же для `trophy`, `selfmade`. Свои вещи фракции (origin culture:<fname>) можно оставлять без фильтра: иначе Holy Nation потеряет каноничный белый.
4. Внутри семейств (`member_pick`, ~стр. 169) отдать приоритет членам из `families_keep[key]["keep"]`: исключить `drop`-sid из `m2` (если после фильтра пусто — вернуть исходный список).
5. Каталожный `own` строится выше; если нужен жёсткий результат — отфильтровать `cat` сразу после загрузки (стр. 26), но тогда пропадут и T0/слот-источники, поэтому фильтр в `coh()`/`pools()` предпочтительнее.
