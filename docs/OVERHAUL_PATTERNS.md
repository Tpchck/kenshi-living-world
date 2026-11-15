# OVERHAUL_PATTERNS — приёмы крупных оверхолов как образец для KMM (2026-11-16)

Исследование только для чтения. Источник: 663 мода из `Kenshi\data\mods.cfg`, прочитанных `tools/kmod.py`; ваниль — gamedata.base + rebirth + Newwworld + Dialogue; перечисления — KenshiLua `docs/EnumsReference.md` (DialogConditionEnum, DialogActionEnum, EventTriggerEnum, TaskType, WarCampaignEnum); заголовок `tools/ref/KenshiLib/Include/kenshi/WorldEventStateQuery.h`; сейвы `%LOCALAPPDATA%\kenshi\save\*\quick.save`, лог `Kenshi\kenshi_info.log` от 15.11 21:19.
Метки: ✓данные — видно в записях модов; ✓сейв — видно в сейве; ✓код — есть в заголовке или биндинге; ✓игра — есть в логе игры; ? — вывод, не проверен.
Скрипты разбора лежат во временной папке (`jobs/67d29d63/tmp/research/*.py`), в проекте ничего не менялось, кроме этого файла.

## 0. Главное до чтения

1. World state не хранится как флаг и не пишется в сейв. `WORLD_EVENT_STATE` — это запрос: в нём «NPC is / NPC is NOT» (уникальный NPC: 0 мёртв, 1 жив/в порядке, 2 в плену), «player ally / player enemy» (отношение игрока с фракцией, v0=1 «да», 0 «нет») и флаг `player involvement`. Метки: ✓код (`WorldEventStateQuery::isTrue()`, поля uniqueNPCsAre/AreNot, isAllyOf/isEnemyOf, towns), ✓данные (152 ванильных записи, других полей нет), ✓сейв (в quick.save 0 записей WORLD_EVENT_STATE). В сейве лежат только входы: отношения фракций (`GAMESTATE_FACTION`: relationN/trustN по каждой фракции, 294 записи), состояние уникальных NPC и текущий вариант города (`GAMESTATE_TOWN.replacementTown` + `faction`, 569 записей; во всех просмотренных сейвах поле пустое).
   Отсюда вывод: Lua не может «выставить world state» средствами игры. Можно только поменять входы (отношения, жизнь NPC) или подменить ответ `isTrue` плагином. Это и делает наш `KMM_Native.ws_set` (C++-хук, ✓игра: «isTrue hook installed»).
2. Kaizo устроен ровно так, как предполагал владелец. 135 новых вариантов городов, 133 world state, 61 кампания, 115 пакетов ИИ, 2721 условие/эффект диалогов, и всё сцеплено ссылками без единой строки кода. Kaizo включает в себя Bandit Variety: 89 его world state имеют sid `*-Bandit Variety.mod`. Игра их принимает: в kenshi_info.log 8 предупреждений «modified by Kaizo does not exist», и все они касаются DIALOGUE_LINE, а не world state (✓игра).
3. Главный риск, найденный по ходу. `ws_set` подменяет общие world state. 45 состояний из `kmm_ws_lut.lua` читают не только варианты городов: на них ссылаются ещё 329 SQUAD_TEMPLATE, 249 DIALOGUE_LINE, 42 FACTION_CAMPAIGN и 15 DIALOGUE. Из них 226 ссылок ванильные, 91 — из KMM_Traces, 89 — из Kaizo (✓данные). Пример: ложное «Tengu is alive = false» выключит ванильные кампании `Empire Visit TaxMan` (все три) и `Empire Assault Tax Evasion (trigger)`. Подробно в §4.

## 1. Топ модов, работающих с ядром

Счёт — число записей каждого типа в файле мода, новых и изменённых вместе. «Ядро» = WS + DIALOGUE + DIALOGUE_PACKAGE + AI_PACKAGE + TOWN + SQUAD_TEMPLATE + FACTION + FACTION_CAMPAIGN; DIALOG_ACTION (атомы условий и эффектов) показан отдельно. TOWN/ws — города со ссылкой на world state (варианты-override и их базы). FAC/rel — фракции с изменёнными отношениями. WSref — прочие записи со ссылкой на world state. Поз. — номер в mods.cfg (0…662; KMM_* стоят на 641–662).

| # | мод (поз.) | ядро | WS | DLG | DPKG | DACT | AI_PKG | TOWN | TOWN/ws | SQUAD | FAC | FAC/rel | CAMP | WSref |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | Kaizo (475) | 1585 | 133 | 157 | 47 | 2721 | 115 | 330 | 232 | 685 | 57 | 26 | 61 | 205 |
| 2 | Unofficial Patches for Kenshi (36) | 645 | 4 | 225 | 3 | 138 | 30 | 212 | 6 | 74 | 43 | 35 | 54 | 11 |
| 3 | Band of Exiles (133) | 557 | 13 | 370 | 69 | 856 | 10 | 53 | 0 | 37 | 5 | 2 | 0 | 59 |
| 4 | Talkative Kenshi (48) | 407 | 10 | 138 | 46 | 1406 | 8 | 87 | 0 | 109 | 3 | 0 | 6 | 8 |
| 5 | RecruitPrisoners (123) | 360 | 0 | 80 | 42 | 578 | 0 | 0 | 0 | 233 | 4 | 0 | 1 | 14 |
| 6 | TEXT TEXTURE (595) | 346 | 13 | 120 | 47 | 320 | 5 | 25 | 8 | 95 | 26 | 13 | 15 | 38 |
| 7 | TK Clean Fix (49) | 314 | 0 | 35 | 89 | 557 | 8 | 87 | 0 | 88 | 1 | 0 | 6 | 4 |
| 8 | Side Quest (476) | 309 | 18 | 64 | 22 | 287 | 5 | 37 | 20 | 111 | 25 | 10 | 27 | 61 |
| 9 | Rusty Raiders FACTION (609) | 257 | 10 | 92 | 27 | 372 | 13 | 28 | 11 | 80 | 4 | 1 | 3 | 24 |
| 10 | Bounties Galore (232) | 233 | 10 | 86 | 24 | 463 | 5 | 37 | 5 | 62 | 7 | 5 | 2 | 44 |

Профильные моды, полезные как образцы приёмов (✓данные):
- Реакция мира репликами: Social lives (United Cities) ENG — 16 WS и 521 условие/эффект; Social Lives (Holy Nation) ENG — 12 WS.
- Звери по запаху крови: Symbiosis — 24 пакета ИИ, из них 6 с задачей HUNTING_BLOODSMELL. Также More Dogs и Iron_Hounds.
- Кампании: Leviathan Ronin (Reloaded) — 38 кампаний и 10 вариантов городов; Adventurers Guild - Extra Selection Criteria — 56 кампаний.
- Варианты городов: Holy Villages — 25 вариантов с world state.
- Отношения фракций: Faction Relations - Law and Order — 40 фракций с отношениями.
- Чисто разговорные: Strangers and Freaks, Weird recruit, Let's Talk — много DIALOGUE, но почти не трогают мир.

## 2. Каталог приёмов (как устроено в данных)

### П1. World state → вариант города → смена владельца и спавна
- База: в TOWN есть ссылка `override town` → список TOWN-вариантов. У каждого варианта свои `faction` (новый владелец), `residents` (SQUAD_TEMPLATE, v0 — число, v1 — ?), `bar squads` (v0 — число, v1 — шанс), `default resident`, `roaming squads` (v0 — вес), `loot spawn`, `type`, `residents override`, и ссылка `world state` на WORLD_EVENT_STATE с v0=1 «должно быть истинно» или v0=0 «должно быть ложно» (условия соединяются по И).
- Ванильный пример. `2608-gamedata.base` Admag (Shek) → `1533314-__world reactions Shek.mod` «Admag (override) Seto» (WS «Esata is alive»=1 и «Seto is not alive»=1; другие резиденты, свои bar squads) → `1533317-__world reactions Shek.mod` «Admag (override) esata dead»: владелец Berserkers, резиденты «_ruined empty building (NO SELL)» ×30, «hub squatters copy berserker» ×10, условие «Esata is alive»=0. Варианты цепляются: у варианта тоже есть `override town`.
- Kaizo. `5000277-Bandit Variety.mod` «Mongrel (override) deadhive overrun»: владелец Fogmen, резиденты «Fog hive ruins» ×12 и «Fog prince ruins», `roaming squads` «Fog hive roaming squad» вес 80, в баре наёмники. Условие — `5000276-Bandit Variety.mod` «Mongrel is overrun» = NPC is Arc мёртв (0), The Queen мёртв (0), NPC is NOT Seta «в порядке» (1). Всего у Kaizo 135 новых вариантов; владельцы: HN 18, UC 12, Shek 8, Empire Peasants 8, Cannibals 6, Abandoned Buildings 6, HN Outlaws 6 и другие. В 26 вариантах есть `roaming squads`: после смены владельца вокруг города бродят новые отряды. Из 90 новых WS у Kaizo: NPC is — 46, NPC is NOT — 27, player enemy — 15, player ally — 7.
- Bounties Galore использует тот же приём: «Squin (override) takeover / new leader / destroyed», «Barcrest (Override) Sysus Bandits are dead», «Gryfs Drug Farm (override) Gryf is fucking dead».
- Сейв: текущий вариант — строка `replacementTown` в GAMESTATE_TOWN (✓сейв, поле есть). Когда игра пересчитывает вариант (при выгрузке зоны города или по таймеру), не проверено (?).

### П2. Spawn по world state (отряды появляются и исчезают по состоянию мира)
- В SQUAD_TEMPLATE есть ссылка `world state` (в ванили у 121 шаблона). Примеры из Kaizo: `1302-gamedata.base` «Dust Bandit squad» ← «dust king ALIVE»=1; `1309-gamedata.base` «Sand ninja cell» ← «Sand Ninja Oni is alive»=1; `8908-Dialogue.mod` «Holy Nation slave escapees» ← «Holy Nation devastated»=0.
- У нас: в KMM_Traces 154 шаблона с world state. Например, `27-KMM_Traces.mod` «KMM The Holy Nation T0 band» требует «Esata is alive»=0 и «holy phoenix okay»=1. Стоит проверить замысел: при живой Эсате эта банда не спавнится.

### П3. Кампании (FACTION_CAMPAIGN): рейды, месть, визиты, подмога союзников
- Поля: `key` (WarCampaignEnum: 0 ASSAULT_TOWN, 1 CONQUER, 2 DEFEND_TOWN, 3 TRADER_VISIT), `is hostile`, `target characters`, `territorial triggers` + `chance per day` + `range near/far` (запуск сам по территории), `repeat limit`, `num forces`, `travel speed`. Ссылки: `squads to use`, `special leader` (уникальный NPC во главе), `faction override`, `dialog announcement`, `world state` (условие запуска), `victory trigger` и `loss trigger` (следующая кампания; v0..v2 по смыслу — задержка мин./макс. в часах и шанс, ?), `trigger player ally`, ИИ по фазам (`pt1/pt2/retreat/victory AI leader/others`), `inherits from`.
- Месть (Kaizo). `5003846-Bandit Variety.mod` «Flotsam Assault Revenge Moll»: враждебная, территориальная, chance per day 1.0, repeat limit 99999, 30 бойцов «flotsam regulars», объявление «Flotsam announce revenge». WS: «Moll is not okay»=1 и «Mani is alive»=1. При поражении (`loss trigger` 100,240,100) запускается `5003852-…` «… (triggered)» с тем же условием — мстят, пока не победят. Похоже устроены «dust lord visit» (`5003879`, условие «Player Enemy of Dust Lords»=0, «Lord Drek is OK»=1; при победе повторяет себя) и «dust lord assault» (`5003895`, то же, но «enemy»=1): одна банда с разным поведением в зависимости от отношения к игроку.
- Подмога союзника (Kaizo, полностью данными). Ванильная враждебная `95532-Dialogue.mod` «Slave raid» имеет `trigger player ally` → «Ally Hounds (trigger) 3» и `5007584-Kaizo.mod` «Ally AS (trigger) generic». Устройство второй: key=2 (DEFEND_TOWN), не враждебная, без территориального запуска, faction override Anti-Slavers, special leader Jaegar/Grey, 5 бойцов «Anti slaver all strong small». WS: «Player is ally of Anti slavers (NOT farmers)»=1 и «Tinfist is not alive»=0. Наследует «BASE- Ally protect player». Пакеты ИИ по фазам видны в `5005343-Bandit Variety.mod` «BASE- Ally protect player relaxed»: pt1 «Military Assemble leader/forces», pt2 «campaign protect player base relaxed», отход «Casual Raid Retreat [passive]». В ванили так же: `59781-Dialogue.mod` «Shek 5 Invincible Enemy Hunt» → «Ally HN (trigger)».
- Список кампаний фракции — ссылка `campaigns` в FACTION. У Kaizo: Dust Lords → «dust lord visit», «dust lord assault»; Flotsam Ninjas → «Flotsam Assault Revenge Moll (+leader)».
- Lua-доступ: `FactionWarMgr:triggerCampaign` (3 перегрузки, BindingsReference:6058–6060, ✓код). Мы уже вызываем перегрузку [2] (Conductor CA.fire, Siege); в игре запуск не подтверждён (docs/core/ai_squads.md:100).

### П4. Диалог с условием → реплика, смена отношений, запуск кампании
- Как устроено. DIALOGUE_PACKAGE.`dialogs` → DIALOGUE (v0 = событие EventTriggerEnum). DIALOGUE → `lines` → DIALOGUE_LINE (дерево). На DIALOGUE и DIALOGUE_LINE висят:
  - `conditions` → DIALOG_ACTION с `condition name` (DialogConditionEnum), `who` (TalkerEnum: 0 я, 1 собеседник), `compare by` (0 равно, 1 меньше, 2 больше), `tag`; значение сравнения — v0 ссылки;
  - `world state` (v0 1/0);
  - `effects` → DIALOG_ACTION с `action name` (DialogActionEnum), значение — v0 ссылки;
  - прямые ссылки-эффекты: `change relations` (FACTION, v0 = сдвиг), `trigger campaign`, `change AI`, `set AI package`, `give item`, `unlocks/locks`;
  - фильтры: `my faction`, `target faction`, `in town of`, `is character`, `my race`, `has package`.
- Отношения (ваниль). `51005-Dialogue.mod` «I swear my allegiance to the Phoenix!»: change relations HN +75 и Flotsam −75. `57391-Dialogue.mod` (Эсата): HN −10, эффект DA_AFFECT_RELATIONS 50 + DA_LOCK_THIS_DIALOG, условие WS «Bugmaster is not okay (player)»=1.
- Реакция на союзника или врага (Kaizo). `5000642-Bandit Variety.mod` «You speak blasphemy, heretic…» выходит только если ложны все три WS: «Player is ally of Flotsam», «Player is ally of Shek Kingdom», «Player is enemy of Holy Nation». `5000712-…` «you're with those cultists?»: my faction=HN и WS «Player is ally of HN Outlaws»=1.
- Диалог запускает кампанию (Kaizo). `5005341-Bandit Variety.mod` «Divine blessings to you.»: WS «Player is ally of HN»=1, `trigger campaign` «HN Visit Prayer ally» (150,160,100), эффект DA_ASSAULT_PHASE.
- Мелкие сдвиги отношений (Kaizo/BV). `4999172` «Beggars aren't welcome here.»: условие DC_IN_A_PLAYER_TOWN, эффект DA_AFFECT_RELATIONS −3. `4999244`: DC_IS_OUTNUMBERED → DA_GO_HOME + отношения −1.
- Условия по отношениям: DC_RELATIONS (1, сравнение со значением), DC_IS_ALLY (24), DC_IS_ENEMY (25), DC_I_LOVE/HATE_THIS_GUY (52/53). Kaizo часто правит ванильные строки, удаляя условие ссылкой со значениями 2147483647 (маркер удаления ссылки), например `3588-dialogue-01.mod`.
- DC_FACTION_VARIABLE (6) в ванили проверяет переменные фракции (`stringvar` = 'raid1', 'taxman', 'state', 'phase'; 9 записей). Действия, которое ставит такую переменную, в DialogActionEnum нет. Наш kmm_diplo перехватывает это условие («KMM_WORLD») Lua-колбэком на каждую проверку. ✓код, в игре — `DIPLO_COND hook live`.

### П5. Пакеты ИИ: патруль, поиск, похищение, сопровождение
- AI_PACKAGE → `Leader AI Goals`, `Squad AI Goals`, `Squad2 AI Goals`, `Slave AI Goals` → AI_TASK (`enum` = TaskType, `targeting`, `classification`). v0..v2 ссылки — по смыслу часы начала/конца и приоритет (?). Также `inherits from`, `clears existing jobs`, `contract end talk passive` (диалог в конце контракта).
- `5004120-Bandit Variety.mod` «Kidnapper patrol map (short range)»: лидер — ATTACK_ENEMIES, PATROL, PROTECT_ALLIES, FIND_CAGE_AND_PUT_IN; отряд — FOLLOW_SQUADLEADER, FINAL_KIDNAPPER_CAGE_JOB.
- `5009238-Kaizo.mod` «Escort Outlaws»: FOLLOW_PLAYER_ORDER (targeting 3 = цель миссии), PROTECT_OWN_SQUAD, LOOT_THE_DEAD; по окончании контракта — диалог «Escort Outlaws Finished Job».
- `5005198-Kaizo.mod` «Patrol between towns --EXPERIMENTAL--»: PATROL + BODYGUARD + наследование «-addon loot stuff (new)».
- Хищники (ваниль). `5007-gamedata.base` «Blood Hunter nocturnal» и `96238-rebirth.mod` «Blood Hunter day»: Patrol, «attack enemies and neutrals», «Smell Hunter» = HUNTING_BLOODSMELL (0,23,4). Их используют 77 шаблонов: ванильные волки, Symbiosis (36 записей), More Dogs (22), TIHYD_Zoo, Iron_Hounds. В SQUAD_TEMPLATE есть числовое поле `blood smell mult`.

### П6. Награды за голову и охотники (ванильный механизм целиком в данных)
- Награда: в CHARACTER поля `bounty amount`, `bounty amount fuzz`, `bounty chance`, `assigns bounties`, ссылка `bounty factions`; в FACTION — `offers bounties` (в ванили Police, UC, HN, Shek). За преступление награду назначает реплика стражи с эффектом DA_ASSIGN_BOUNTY (32), например `2355-gamedata.base` (v0=2000). Снятие и оплата — DA_CLEAR_BOUNTY (49), DA_PAY_BOUNTY (10).
- Охотник: `5337-gamedata.base` «Bounty hunters wandering between towns» (фракция Bounty Hunters) с пакетами «hang out in a bar» и «Wandering from town to town» (WANDERING_TRADER). Ищет не ИИ: реакцию даёт диалог на событие EV_BOUNTY_SPOTTED (44). Пример `18322-Dialogue.mod` «TOUGH bounty hunter»: условия DC_BOUNTY_AMOUNT_ACTUAL собеседника больше 35000, оба не в плену, не в бою, цель не KO и т.п. Строки → `18340` «…Today you're going to jail!» с эффектом DA_ATTACK_CHASE_FOREVER. Так же устроены 18 привязок EV_BOUNTY_SPOTTED: стража, Shop Guard, вигиланты, Eyegore.
- Стража арестовывает задачей HUNT_BOUNTIES в «addon- law enforcement» (`18887-rebirth.mod`) и ещё 18 пакетах, всего 84 шаблона.

### П7. Караваны, визиты, патрули
- Караван — шаблон с пакетом WANDERING_TRADER (ванильные «Wandering from town to town», «noble procession») плюс `roaming squads` в TOWN/FACTION. Визит в город игрока — кампания key=3 TRADER_VISIT или не враждебная с announcement (у Kaizo «Merchant visit (Catun)», «Merchant ninja traders»).
- Беженцы и бродяги после падения города — `roaming squads` варианта города (П1). У Kaizo это делают 26 вариантов, есть пакет «homeless town vagrants- civil war».

### П8. Реплики-новости горожан (слухи данными)
- Social lives (UC). `1478-social lives (United Cities).mod` «The swamp robber Big Fang has been killed…» — WS «Big Fang мёртв»=1; `1479-…` «A Big Gray has been killed…» — WS «Big Gray is alive»=0. События пакетов: EV_PLAYER_TALK_TO_ME 23, EV_I_SEE_NEUTRAL_SQUAD 16, EV_I_SEE_ALLY_PLAYER 11, EV_I_SEE_ENEMY_PLAYER 7. Talkative Kenshi строит реплики на EV_GIVE_UP_CHASE 27, EV_I_SEE_ENEMY_PLAYER 25, EV_I_SEE_ALLY_PLAYER 19, EV_ENTER_TOWN 6.

## 3. Наши механики → приём → вариант

Варианты: «данные» — Lua не нужен; «гибрид» — данные исполняют, Lua только переключает вход (флаг через `ws_set` на нашем собственном WS, отношение или запуск кампании); «Lua» — оставить как есть.
Способ поднять флаг для гибрида:
- (а) `KMM_Native.ws_set(<наш WS>)`. C++-хук работает (✓игра), ответ выдаёт движок без Lua на каждой проверке. В сейв не пишется: после загрузки Lua ставит заново (так уже сделано в LINKN).
- (б) Скрытая «фракция-флаг» и WS «player ally/enemy» к ней; Lua меняет отношение игрока с ней. Хранится в сейве (GAMESTATE_FACTION, ✓сейв). Порог «ally» и видимость фракции в окне отношений не проверены (?). В сборке есть Hidden-Faction-Relations.mod, его роль не разбиралась. По PROTOCOL это параллельная переменная, причину нужно записать.
- (в) Наш WS всегда должен иметь «ложное по умолчанию» условие в данных. Пустой запрос, вероятно, истинен (?).

| механика | приём из оверхолов | вариант | выигрыш | риск |
|---|---|---|---|---|
| Смена владельцев городов (LINKN, Conductor_World) | П1 + П2 | гибрид, уже частично. Перейти со 45 общих WS на свои: по паре «город → владелец» свой WS и свой TOWN-вариант (faction, residents, bar squads, roaming squads), Lua зовёт `ws_set` только на свои sid | убирает побочки на 329 шаблонов, 249 строк, 42 кампании; 189 «рискованных» вариантов из LUT (r=1) становятся применимы, потому что «ложная смерть» NPC больше не нужна | нужна новая игра (новые TOWN-варианты). Порядок выбора, если истинны сразу два варианта (наш и Kaizo), неизвестен (?): в наш вариант добавить условия «WS Kaizo = 0». `replacementTown` пишется в сейв, а наш флаг нет: после загрузки до повторного `ws_set` город может откатиться (?) |
| Беженцы и колонны (Traces) | П1 `roaming squads` варианта, П7, П2 | гибрид: колонна беженцев = `roaming squads` варианта павшего города, караван = WANDERING_TRADER + `roaming squads`. Lua только у игрока (подписи, вестники) | меньше `createRandomSquad` и слотов (≤4), отряды живут по правилам движка вне экрана | спавн по roaming — фоновый, точного «колонна сейчас у игрока» не даёт; оставить Lua-заказ только для сцен у игрока |
| Соперники и месть (Nemesis) | П3 «Revenge Moll»: special leader + loss trigger на себя; П5 пакеты | гибрид: соперник — уникальный CHARACTER-лидер в SQUAD_TEMPLATE; месть — кампания с `special leader`, `target characters`, WS «соперник жив» + наш флаг «игрок его победил». Lua решает когда и зовёт `triggerCampaign` [2]; память LT, appraise, «кто тебя уложил» остаются в Lua | движение отряда, сбор, отход, повтор после поражения делает движок; сохраняется в сейве как кампания (?) | триггер кампании в игре ещё не подтверждён (ai_squads.md:100); кампания идёт на город или базу, на одиночного игрока в поле — только `target characters` (поведение не проверено, ?) |
| Охотники за головами (Outlaws/B1) | П6 целиком | данные + минимальный Lua: охотники — шаблоны с WANDERING_TRADER (как 5337) в `roaming squads` фракций; нападение — диалоги на EV_BOUNTY_SPOTTED с порогами DC_BOUNTY_AMOUNT_ACTUAL → DA_ATTACK_CHASE_FOREVER. Lua только ставит награду («native bounty») | весь цикл «увидел — заговорил — погнался» нативный и проверен игроками; HUNT_BOUNTIES работает у стражи (84 шаблона) | у охотника в ванили пакеты «--Needs fixes--» (так в именах); Kaizo и другие моды правят ванильные строки охотников. Свои диалоги лучше добавлять в свой пакет, а не править ванильные |
| Запах крови и звери (Predators/Herds) | П5 HUNTING_BLOODSMELL, поле `blood smell mult` | в основном данные: хищникам — пакеты Blood Hunter (Symbiosis уже даёт 36), настройка `blood smell mult`. Lua `ZoneSmell:addSmell` оставить усилителем у мест бойни | меньше Lua на такте; хищники приходят сами | конфликт с Symbiosis/More Dogs при правке их пакетов: только добавлять свои ссылки, не менять чужие |
| Слухи и реплики горожан (Rumors) | П8 Social lives, П4 | гибрид: постоянные реакции (смена владельца, фаза STORY, игрок в розыске, игрок союзник X) — DIALOGUE в своём DIALOGUE_PACKAGE на EV_I_SEE_NEUTRAL_SQUAD / EV_PLAYER_TALK_TO_ME / EV_ENTER_TOWN с WS-условием. Конкретные имена и события — Lua (низкий приоритет по HANDOFF) | `say` и журнал не нужны для фона; реплики переживают отказ Lua | текст статичен (подстановки только /YOURNAME/ и подобные); нужна привязка пакетов к горожанам — правка чужих шаблонов (merge по ссылкам) |
| Дипломатия (kmm_diplo) | П4: `change relations`, DA_AFFECT_RELATIONS, DA_TAKE_MONEY, DC_RELATIONS/IS_ALLY, WS | гибрид: перехват DC_FACTION_VARIABLE (Lua-колбэк на каждую проверку условия) заменить ссылками `world state` на свои WS, которые поднимает `ws_set` (проверку делает C++), и DC_RELATIONS. Деньги и отношения — эффектами реплик, а не Lua | убирает самый горячий Lua-путь (колбэк на каждую реплику каждого говорящего) | поединок X3 и запись отношений через дирижёр (RELSYNC) остаются в Lua |
| Отправка союзников (KC.try_dispatch → Traces.request) | П3 «trigger player ally» + «Ally … (trigger)» key=2, «BASE- Ally protect player» | данные целиком: на враждебные кампании против игрока добавить `trigger player ally` → наши «Ally <фракция> (trigger)» с WS «Player is ally of <фракция>»=1; плюс реплика в баре или у лидера с `trigger campaign` (как 5005341) | Lua-спавн не нужен; ИИ по фазам ванильный; так Kaizo уже работает для AS/Hounds/CH/HN | ссылки на кампании Kaizo только добавлять: merge по цели сохраняет его списки (?, если игра сливает refs как kmod.apply) |
| Акты и обороты сюжета (STORY) | П1/П2/П3/П8 по флагу фазы | гибрид: расчёт фаз остаётся в Lua (множители параметров); на смене фазы Lua поднимает 1 из 7 флагов (способ б — переживает сейв), а данные дают видимое: кампании «Food raid» на Железном голоде, варианты баров и лавок, реплики | мир показывает фазу, даже если Lua упал после переключения | 7 новых WS/фракций-флагов; «Пепельная эпоха» и подобные фазы кладут ещё варианты городов — риск двух истинных вариантов (см. первую строку) |
| Руда (KMM_Ore) | прямого аналога нет. Ближайшее — варианты лавок (`residents`, vendors) по флагу «рудный кризис» | Lua (метрики ore_stress/crisis/fracture читает STORY); видимую часть кризиса можно отдать вариантам лавок по флагу | — | в игре модуль ничего не делал («nodes in state=0», HANDOFF), сначала починить |

## 4. Конфликты KMM_* с Kaizo

Порядок: Kaizo — 475, KMM_* — 641–662 (KMM_Merged 641 … KMM_Cleanup 662). Поле значения перезаписывает тот, кто позже; ссылки сливаются по цели (так работает `kmod.apply`, совпадение с игрой проверено по kenshi_info.log 11.11 для пропуска несуществующих записей). Значит, при пересечении побеждают KMM.

1. World state, правка записей. Ни один KMM_* не меняет WS, которые правит Kaizo. Свои WS есть у KMM_Elite (2: «KMM Elite open …») и KMM_Merged (8 перенесённых из Hiver Expansion, Hiver Expansion Assault Sequence Fix, OrcRaceReview). ✓данные.
2. World state, подмена в рантайме (главный конфликт). `ws_set` форсирует 45 общих WS: «Esata is alive», «Tengu is alive», «holy phoenix okay», «dust king ALIVE», «Moll is ok», «Tinfist is alive» и другие. Ни у одного нет `player involvement`. Их читают кампании Kaizo и ванили: «dustbandit Invasion with demands» ← «dust king ALIVE», «Empire Visit TaxMan» ×3 и «Empire Assault Tax Evasion» ← «Tengu is alive», «Kidnap - Southern Hive Sacrifice» ← «south hive queen okay». Всего потребителей: Kaizo 89, KMM_Traces 91, ваниль 226, Social Lives HN 31, MysteriousWanderer 27, Social lives UC 24 и т.д. Пока LUT пускает только «ложную смерть» лидера, которого дирижёр сам убил (флаг d), это даже согласовано: мир ведёт себя так, будто лидер мёртв. Но настоящий NPC стоит живой, а реплики-новости и кампании мести срабатывают. Решение — свои WS (§3, строка 1).
3. Варианты городов. KMM_* не трогают у городов Kaizo ссылки `override town`, `world state`, `faction`. Пересечения по другим полям:
   - KMM_Atlas — 110 TOWN (bar squads, residents);
   - KMM_Fix — 84 (loot spawn);
   - KMM_Economy — 21 (residents, roaming squads);
   - KMM_Cleanup — 8 (bar squads);
   - KMM_Merged — 7 (distant mesh).

   Это добавки, цепочку Kaizo они не ломают. Цепочки Kaizo правят и чужие поздние моды:
   - Side Quest (476) — 3 ссылки `override town` и 3 `world state`;
   - Rusty Raiders (609) — 4 `world state` и 1 `override town`;
   - MEGA Item Integration Patch — 1;
   - Unofficial Patches (36, до Kaizo) — 2 (Kaizo их перекрывает).
4. Отношения фракций. KMM_Behavior (648) задаёт отношения 148 фракциям. С Kaizo совпадают 11 пар, и во всех значения разные, побеждает KMM. Примеры (ваниль → Kaizo → KMM):
   - Shinobi Thieves ↔ Police: 0 → −5 → −70;
   - White Eyebrow Clan ↔ Anti-Slavers: — → +25 → −60;
   - Nameless (игрок) ↔ Dust Bandits: −100 → −10 → −15;
   - Clownsteaders ↔ Traders Guild: — → −20 → −12.

   Отношения игрока прямо питают WS «player ally/enemy», на которых стоят кампании и реплики Kaizo, так что правка Nameless меняет, когда Kaizo считает игрока союзником или врагом. Оговорка: в сейве отношения лежат в GAMESTATE_FACTION (✓сейв), поэтому данные FACTION, скорее всего, действуют только при новой игре (?).
5. Пакеты ИИ. KMM_Town заменяет пакет на свой клон с расписанием у 28 шаблонов, где пакет задавал Kaizo. Пример: «deadcat civilian nofish» — пакет Kaizo «worker fighter indie resident» удалён маркером, вместо него «KMM worker fighter indie resident [worker:early]». Побеждает KMM. Клон снят с итогового слияния на момент сборки: при обновлении Kaizo изменения его пакета не дойдут (?).
6. Шаблоны отрядов. KMM_Economy меняет у 128 шаблонов, которые трогал Kaizo, поле `vendors refresh time`; Kaizo это поле не меняет, конфликта значений нет. KMM_Elite — 32 шаблона (`squad`/`squad2`). KMM_Merged переносит 23 ссылки `world state` на строках, общих с Kaizo (DIALOGUE_LINE 1844/1835 «caught a bounty» и др.).
7. Чего не проверял: CHARACTER, BUILDING, ITEM не сканировались. Пересечения по уникальным NPC (от них зависят WS) остаются открытыми.

## 5. Пять самых выгодных переводов (по порядку)

1. Свои WS и свои варианты городов для смены владельцев. Самый большой выигрыш при малой цене: механизм `ws_set` уже работает в игре. Убирает побочки на ~635 ссылок (329+249+42+15, из них 91 — наши Traces), открывает 189 «рискованных» вариантов, даёт беженцев через `roaming squads`. Делать до последней «нужна новая игра».
2. Отправка союзников — полностью данными по образцу Kaizo: `trigger player ally` → «Ally X (trigger)» key=2, «BASE- Ally protect player», WS «Player is ally of X», плюс реплика `trigger campaign`. Lua не нужен вообще; приём проверен игроками Kaizo.
3. Охотники за головами — ванильный цикл П6: бродячие охотники, EV_BOUNTY_SPOTTED, порог награды, DA_ATTACK_CHASE_FOREVER. Lua только ставит награду. Нативная погоня и поиск вместо Lua-пакетов HUNT_BOUNTIES на временных отрядах.
4. Дипломатия: перехват DC_FACTION_VARIABLE заменить на `world state` с собственными WS (`ws_set`) + DC_RELATIONS/DC_IS_ALLY, эффекты отношений и денег — в репликах. Убирает Lua-колбэк с горячего пути диалогов.
5. Месть соперника кампанией (П3 «Revenge Moll»: special leader, loss trigger на себя, WS «соперник жив» и флаг). Решение «когда» остаётся за Lua через `triggerCampaign`. Сначала нужен маркер `campaign: triggerCampaign` ok из живой сессии.

Рядом и дёшево: флаги фаз STORY и рудного кризиса → реплики-новости (П8) и варианты лавок. Хищникам — только проверить, что пакеты Blood Hunter стоят у наших и модовых хищников; Lua-запах оставить усилителем.

Общие риски перевода: всё, что добавляет TOWN-варианты и кампании, требует новой игры; добавлять это стоит в последнюю такую установку. Удалять записи после неё нельзя: сейв ссылается на sid варианта через `replacementTown` (?). Правки чужих записей (Kaizo, Symbiosis) — только добавлением ссылок, без замены значений.
