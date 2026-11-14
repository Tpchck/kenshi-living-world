# Вассалитет и союзы фракций (проект)

Статус: ПРЕДЛОЖЕНИЕ. Данные: `rules/vassals_proposal.json`, проверка: `python -I -X utf8 tools/vassals_audit.py` (имена сверяются с `build/KMM_Conductor/conductor.json`, города и владельцы с `data/registry.json`). Ничего в игре не подключено.

## 1. Что есть сейчас

Дирижёр уже умеет договоры, но стартовых договоров нет.

- Типы: nonaggression, trade, defense, military, vassal. Параметры: `tools/conductor/gen_conductor.py:64-68` (дубль в `rules/conductor.json:122-145`): сроки, `tribute_share` 0.08, `vassal_power_ratio` 2.5, `relation_on_sign`.
- Состояние: `fresh_state()` `KMM_Conductor.lua:218-237` создаёт `S.treaties = {}` и берёт `S.rel` из `factions[*].rel` (стартовые отношения из реестра v0, `gen_conductor.py:300-301`). Никакого сида договоров нет, всё рождается во время игры.
- API: `treaty_between` `:395`, `allies_of` `:400`, `sign(ttype,a,b,why)` `:407` (a = сюзерен, b = вассал), `break_treaty` `:419`, `treaties_review` `:594-608` (разрыв при `rel < break_rel`, по сроку), дань вассала `:569-572`.
- Единственная точка подписи вассалитета: действие alliance, `:2066-2075`. Вассал рождается только «из страха» (`ratio >= 2.5` и у цели ≤ 2 городов). Кандидатов на союз выбирает `:1871-1881` (`r >= 10`, общие враги).
- Влияние на мир: `ally_help` `:436-455` (оборона), `ally_joins` `:512-517`, `joint_allies` `:1955` (совместные рейды, только military).
- Игроку видно: `KMM_Traces.lua:1519-1529` (`g_tribute`: курьер-сборщик дани сюзерена к вассалу, берёт `C.tribute_pairs()` из `KMM_Conductor.lua:4649`), `KMM_Traces.lua:830` (караван при trade), диалоги `tools/streams/diplo.py:31-80` (fealty, submission, tribute).
- Рабы и чёрный рынок: роли в `gen_conductor.py:126-129` (`slavers`: Slave Traders, Hounds, Manhunters; `slave_markets`: United Cities, The Holy Nation; `anti_slavers`: Anti-Slavers; `drugs`, `drug_ban`: HN; `thieves`, `fences`). Лог. рабов: `KMM_Conductor.lua:2832-2858` (доход, `slave_raid`, `slaves_freed`). Контрабанда в Stock: `:1412-1422` (скупщики-fences берут запрещённое), `RB_CATS` `:1259` включает `drugs`, `ROLE` `:628`. Категории рабов в Stock нет, рабы идут только через `wealth` и события. В `tools/streams/economy.py` рабов нет.
- Шарды (расколы): `SHARDS` `gen_conductor.py:122`; спящие фракции: Rebel Swordsmen, Yabuta Outlaws, Slave Hunters, Free Traders, Iron Company, Red Hive, Twinblades.

Пробелы: нет стартового сида, нет запретов (подписать с кем угодно при `rel >= 10`, в том числе мятежнику с государством), у рынка нет «хабов» (только фракции).

## 2. Предложение (кратко)

В conductor.json 133 фракции (спящие и мод. включены). Все имена в JSON проверены аудитом.

Вассалы (a = сюзерен): 20 пар. Примеры:
- United Cities: Police, Bounty Hunters, Empire Peasants, Catun, Imperial Bank (клиент).
- Slave Traders: Manhunters, Slave Hunters (спящий осколок).
- Traders Guild: Trade Ninjas, Sultans Wares, Free Traders (спящий).
- The Holy Nation: Missionaries, Preacher Cult (клиент).
- Shek Kingdom: Kral's Chosen, Berserkers (клиент).
- Western Hive: Steel Raiders, Red Hive (спящий). Second Empire: Second Empire Exile, Skeleton Legion. Swampers: Swamp Ninjas. Oni: Lost Oni.
- Независимы: Tech Hunters (только союзы: Machinists, Desert Divers, Gunsmiths, Cannibal Hunters, Shem Residents), Dark Hive, Southern Hive.

Региональные союзы: 36 пар (по реестру `allies_after` >= 30 плюс география), см. JSON.

Правила `never_ally` (запрет любого договора):
- Мятежники: Holy Nation Outlaws, Flotsam Ninjas, Mongrel против HN; Anti-Slavers против UC, Slave Traders, Manhunters, Slave Hunters; Rebel Farmers против UC и Slave Traders; Dark Reavers против Dark Hive; Band of Blades против Shek, HN, Slave Traders; спящие Rebel Swordsmen и Yabuta Outlaws против UC.
- `closure: true`: запрет распространяется на вассалов и договорных союзников стороны, против которой мятеж (Missionaries, Preacher Cult, Police, Bounty Hunters и т.д.). Проверять и живые `S.treaties`, и список.
- Войны государств: UC и HN, Shek и HN, Dark Hive и HN, Dark Hive и Southern Hive, Second Empire и UC/Traders Guild, Slave Traders и Mongrel, Berserkers и Slave Traders и др.
- Блоки: хаос (Daemons, Midnight Lord и др.) ни с кем; имперская группа ни с хаосом.
- Мосты-нейтралы: Adventurers Guild, Mercenary Guild, Shinobi Thieves дружат с обеими сторонами (аудит WARN про Adventurers Guild между Shek и HN). Им разрешены только nonaggression и trade, defense/military запрещены.

Чёрные рынки (`black_markets`, 12 хабов): города Slave Traders (Slave Farm, Slave Farm South, Port North, Port South, Eyesocket, Stone Camp, South Stone Camp); нейтральные базары Clownsteady и Catun (UC); Flats Lagoon (Tech Hunters, воры), Shark (Swampers, гашиш), Squin (Shek, краденое без рабов). У каждого хаба `goods`.
- Продавцы рабов: Slave Traders, Hounds, Manhunters, Slave Hunters, Dust Bandits, Starving Bandits, Reavers, Sysus Bandits, Skin Bandits, Bloodraiders, Black Dragon Ninjas, Dark Reavers, Outlaw.
- Покупатели рабов: United Cities, Traders Guild, Slave Traders, The Holy Nation, Second Empire. HN: роль slave_markets уже есть, гашиш HN напрямую не берёт (drug_ban).
- Запрещённые покупатели рабов: Anti-Slavers, Mongrel, Rebel Farmers, Holy Nation Outlaws, Flotsam Ninjas, Berserkers, Kral's Chosen.
- Принцип: сделка на хабе не требует договора. Она идёт, если пара продавец-покупатель не в `never_ally` (с closure) и `rel(buyer, hub_owner) >= -20`.

Решения по лору (спорные, поправить вручную): Shinobi Thieves в реестре союзны и HN, и HN Outlaws, поэтому они мост и не вассалы; Shek рабов не покупает; Slave Traders у UC союзник, а не вассал (чтобы не тянуть Anti-Slavers в конфликт с UC по вассальной ветке); Mongrel запрещён как покупатель (вражда со Slave Traders).

## 3. План внедрения (1-2 часа)

Шаг 1 (генератор, 20 мин). В `tools/conductor/gen_conductor.py` после блока roles (стр. 379-380) читать `rules/vassals_proposal.json`, резолвить имена в sid через `name_to_sid`/`by_name_real` (как у ролей) и класть в выход рядом с `roles` (стр. 395-397) ключи `seed_treaties` [{a, b, type, sleeper}], `never_ally` {pairs: [[sidA, sidB]]} (развёрнутые closure-пары уже в генераторе, Lua остаётся простым), `black_markets` [{town_sid, owner, goods}], `market_rules`. Дубли имён (Gunsmiths x2): брать фракцию с городами. Типы: vassal -> `vassal`, client -> `defense`, regional_allies -> `defense` (rel >= 40 из реестра -> `military`).

Шаг 2 (Lua, стартовый сид, 20 мин). В `fresh_state()` после `seed_world(s)` (`KMM_Conductor.lua:235`) добавить `seed_treaties(s)`: для каждой пары, у которой обе фракции в `s.F`, не спящие (спящих откладывать в `S.pending_seed[sid]`, подписывать в момент раскола рядом с `:2946`), вызвать внутреннюю подпись. `sign()` читает глобальный `S`, поэтому вызывать после присвоения `S` (в init, где вызывается fresh_state) либо дать `sign` параметр состояния. Сид должен срабатывать только на новой игре (`S.seeded`), чтобы не плодить договоры при загрузке сейва. Эмитировать `treaty_signed` с `why = "founding pact"`.

Шаг 3 (Lua, запрет, 20 мин). Ввести `NEVER = {}` (симметричный набор из `CFG.never_ally.pairs`, заполнить в `pairs_index` `:624`, рядом с ROLE) и `local function banned(a,b)`. Подключить:
- `sign()` `:407`: первой строкой `if banned(a,b) then return nil end` (общий забор для всех путей);
- кандидаты `:1871`: `and not banned(fid, o)`; `:1870` для trade тоже;
- `:2066` действие alliance: ранний return при `banned`;
- динамический closure: `local function banned_via(a,b)`: для каждого `e` из `allies_of(b, {defense,military,vassal})` проверять `NEVER` с `a` (покрывает союзы, возникшие после старта; список статики уже развёрнут генератором);
- диалоги игрока `diplo.py` не трогаем: запрет только для ИИ-ИИ; игрок может союзничать с кем угодно, но rel с врагами союзника падает (уже есть `add_rel(ally, attacker, -10)` `:447`).
Мосты-нейтралы: в `banned` не включать, но в `sign` для `ttype` defense/military проверять `BRIDGE[a] or BRIDGE[b]` и отказывать.

Шаг 4 (рынки рабов и грязных товаров, 30 мин). В цикле slavers `KMM_Conductor.lua:2833-2858`: заменить поиск `market` (`:2837`) на поиск хаба из `CFG.black_markets` с `goods` содержащим slaves, где владелец не в `banned` с продавцом. Добавить сделку: с шансом `FL.slave_sale_chance` выбрать покупателя из `market_rules.buyers.slaves`, у которого `rel(buyer, hub_owner) >= -20`, нет `banned(seller, buyer)` и покупатель жив; `buyer.wealth -= price; seller.wealth += price`; `rel(seller, buyer) += 1` (без договора); эмитить `slave_caravan_sold`. Аналогично drugs/stolen: уже есть `contra` в `:1412-1422` (fences), расширить `fence` на продавцов из `market_rules.sellers.stolen`.
Новые события (`emit`, `KMM_Conductor.lua:364`): `slave_caravan_sold` {a=seller, b=buyer, town_sid, goods}, `black_market_deal` {a, b, town_sid, goods}, `pact_blocked` {a, b, why} (редкий, для лога, не слух), `vassal_garrison` (см. ниже). Добавить их в списки слухов/подписчиков: `KMM_Traces.lua:376` (таблица видов для слухов), `KMM_Conductor.lua:357` (список событий шины), текст на английском в `emit.text`.

Шаг 5 (ощутимость для игрока, 20 мин). Уже есть дань-курьеры `KMM_Traces.lua:1519`: достаточно, чтобы сид давал вассальные пары, и сборщик начнёт ходить. Добавить: (а) гарнизон сюзерена: при `ally_help`/`base_raid` на вассала сюзерен шлёт отряд (`S.pending_dispatch`, `:450`); (б) совместный патруль: `joint_allies` `:1955` расширить на `vassal` (сейчас только military); (в) слух `slave_caravan_sold` превращать в видимый караван с конвоем по `KMM_Traces` (по образцу `treaty trade -> vcaravan`, `:830`) между хабом и городом покупателя; (г) у вассальных городов `town_info` метка `liege` для UI/слухов («Police patrol under United Cities banner»).

Шаг 6 (проверка, 10 мин). `python -I -X utf8 tools/vassals_audit.py` (имена и конфликты); офлайн-симулятор `tools/conductor` (sim 5y): смотреть `signed_by` на «founding pact», `pact_blocked` и отсутствие договоров мятежник-государство (скрипт: пройти по `S.treaties` и проверить `NEVER`). Игру не запускать.

Риски: стартовое сидирование сразу меняет `rel` через `relation_on_sign` (+20..+40): ограничить `seed_rel_cap` или подписывать без `add_rel` (флаг `silent`). Спящие осколки подписывать только при пробуждении. Пересечения реестр vs предложение: Shinobi Thieves (союз HN + HN Outlaws) намеренно исключён из вассальных пар.
