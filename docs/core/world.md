# world.md — МИР ядра Kenshi 1.0.65: фракции, отношения, войны, лидеры, города, постройки, время, погода

Домен: как ваниль хранит и меняет состояние фракций и городов. Цель: «живой мир» (захваты, войны, голод городов, реакция на игрока) должен идти через эти объекты, а не через параллельную модель дирижёра.
Пути: `K/` = `tools/ref/KenshiLib/Include/kenshi/`; `BR:n` = строка `BindingsReference.md`, `CR:n` = строка `CallbacksReference.md`, `UR:n` = строка `UnboundReference.md` (каталог `...\233860\3817000612\docs\`).
Статусы: ✓игра = видели в логе игры; ✓код = есть в заголовке или биндинге; ? = догадка о семантике (что движок делает внутри).
Доступ из Lua (✓код): `getGameWorld()` → `GameWorld`; `.factionMgr:getFactionByStringID(sid)` → `Faction`. Глобалы C++ `ou` (GameWorld), `con` (GlobalConstants), `shou` (SharedKing → `townList`), `options` (`K/Globals.h:29-36`) **из Lua недостижимы**: геттера нет, секция `Global` в BR:7215 пустая. Нужен плагин.

## Сводная таблица

| Механика | Где хранит ядро | Чтение / запись | Lua | Реакция ванили | Наше использование |
|---|---|---|---|---|---|
| Отношения фракций | `FactionRelations::_factionRelations` map<Faction*,RelationData> (`K/FactionRelations.h:105`) | `getFactionRelation`/`setRelation`/`affectRelations`/`declareWar` | да BR:5854 | ИИ решает, враг он или нет, через `isEnemy`/`isAlly` (?, порог неизвестен) | Conductor `set_rel`→`setRelation` (✓игра, проба), флаги `L2.camp.flags` |
| Флаги договора | `RelationData.alliance/peaceTreaty/war/coexists` (`:79-82`) | RW поля | да BR:5899 | ? (влияние на ИИ проверит только игра) | Conductor:2385-2408 |
| Репутация у игрока | `playerRank`, `globalReputationTrust/ForBadassery` (`:68,96-97`) | RW | да | ранг в диалогах (`checkStateCondition` `:104`) | нет |
| Событие отношения | `affectRelations(p, FactionEvent, mult)` (`:56`) | вызов + **колбэк** | да, CR:65 | ваниль сама зовёт это на атаку, убийство, лечение, плен | нет (колбэк не слушаем) |
| Войны и рейды | `FactionWarMgr` (`K/FactionWarMgr.h`): `possibleCampaigns`, `activeCampaigns`, `campaignRequests`, `nextUpdateTime` | `triggerCampaign` ×3, `endCampaign`, `periodicUpdate` | да BR:6023 | `periodicUpdate` сам запускает кампании по `CampaignData.triggerChancePerDay01` (?) | Conductor:2173-2380 (проба, за флагом) |
| Кампания | `CampaignInstance` (`K/Campaign.h:116`): фаза, лидер, цель, `homeTown` | `changePhase`, `victoryEvent`/`lossEvent` | да BR:2993 | победа или поражение запускает `victoryTriggers`/`lossTriggers` (`:110-111`), то есть цепочку | нет |
| Процветание фракции | `ProsperityManager` внутри `diplomatMgr` (`K/FactionUniqueSquadManager.h:12-27,46`) | `actualProsperity` RW, `notifySquadDefeated`, `getProsperityMultiplier` | да BR:11251 | разбитые отряды снижают процветание, оно влияет на спавн (?) | **нет** |
| Лидер | `FactionLeader` (`K/FactionLeader.h`): `worstEnemy`, `biomeTerritory` | `setNewLeader(Character*)` | да BR:5803 | цели миссий `getEnemyMissionTargetList` | смерть/плен через `declareDead` |
| Владение городом | `RootObjectBase::owner` (`K/RootObjectBase.h:72`), `FactionWarMgr.myTowns` (`:50`), `TownBase.factionsResidentHere` (`K/Town.h:262`) | `TownBase:setFaction(f, ap)` BR:13612 | да | ? (стража, лавки, ворота) | не пишем; вместо этого `ws_set` |
| Вариант города | `Town.replacementTown` (`K/Town.h:349`), `notifyRepopulation(GameData*)` (`:351`), условия `WorldEventStateQuery` (`K/WorldEventStateQuery.h`) | RW + хук `isTrue` | да BR:13435/13473/14616 | ваниль меняет город на вариант, когда выполнены условия world state | KMM_Native `ws_set` (хук `isTrue` ✓игра: «isTrue hook installed») |
| Тревога города | `TownBase.alarmState` (`K/Town.h:288`), enum `TownAlarmState` (`:12-18`) | `get/setAlarmState` (`:125-127`) | да BR:13665-66 | жители прячутся, стража выходит (?) | KMM_Siege:93-126 (импульс) |
| Жители и население | `TownBase.population`, `residentsSpawned`, `defaultResident` (`K/Town.h:261,312,314`) | `Faction:countPopulation(t)`, `getNumPlatoons`, `chooseResidents` | да (population = lightuserdata) | расселение по зданиям `chooseBuildingForResident` | нет |
| Склады и производство | `StorageBuilding::ConsumptionItem{amount,rate,maxCapacity}` (`K/Building/StorageBuilding.h:31-44`), `ProductionBuilding.productionState` STARVED/FULL/NORMAL/IMPOSSIBLE (`ProductionBuilding.h:62-67,134`) | `getConsumtionItems`, `isAnyInputsEmpty`, `getProductionMult` | да BR:12778/11139 | рабочий без входа простаивает | KMM_Town/Stock (свой склад S.stock) |
| Цены в городе | `Town.tradeGoodsMults` (`K/Town.h:475`), `Town.tradeCulture` → `TradeCulture.tradeGoodsMults/illegalItems` (`K/TradeCulture.h:13-17`) | RW map, `getLocalTradePriceMult` | да BR:13464/13487/13812 | окно торговли умножает цену (?) | Traces: свой `priceMultWhenITrade` (✓игра); TGM-проба только на чтение |
| Время | `GameWorld::getTimeStamp_inGameHours()` → `TimeOfDay.time` (часы) (`K/GameWorld.h:238`, `K/util/TimeOfDay.h`) | `getTotalDays/Hours`, `setGameSpeed` | да BR:7113/13219 | всё (голод, кампании, лечение) идёт по нему | ✓игра: `game_day()` Conductor:211 |
| Погода | `WeatherSystem::getInstance()` → `ActiveRegionWeather` → `weatherInstance` → `weather` (`K/Weather.h:201,214`) | читать; записи нет | да BR:14535/14584 | `Weather.affectCharactersType` (кислота, пыль, газ) бьёт по персонажам | нет |
| Глобальные множители | `GlobalConstants` (`K/GlobalConstants.h`), `GameplayOptions` (`K/GameplayOptions.h`) | RW поля | класс связан BR:7219/6912, экземпляр — нет | цены, XP, производство, лимиты отрядов | нет |

---

## 1. Фракции и отношения

### Отношения фракций (число + доверие + флаги)
Как в ванили: каждая фракция хранит `RelationData` к каждой другой: `relation` (float), `trustPositives/Negatives`, `percievedStrength`, bool `alliance/peaceTreaty/war/coexists`, `stateVariables` (map<string,int>, на них ссылаются условия диалогов). Без записи берётся `defaultFactionRelation`. ✓код
Точки ядра: `FactionRelations::getFactionRelation` (`K/FactionRelations.h:35`), `setRelation` (`:38`), `affectRelations(Faction*, float amount, float mult)` (`:58`), `affectTrust` (`:60`), `getRelationData` (`:98`), `isEnemy/isAlly/isCoexisting` (`:30,33,34`), `setEnemy` (vtbl 0x18), `declareWar` (`:64`), `setNoLongerEnemies` (`:62`), `update` (`:26`), `getRelationsData(map&)` (`:101`). `percievedStrength` (`:87`) — как фракция оценивает силу другой (?, кто его пишет — неизвестно).
Lua: да. `FactionRelations` BR:5854-5897, `RelationData` BR:5899-5921 (все поля RW).
Наше использование: Conductor `set_rel` → очередь `dirty_rel` → `setRelation` в обе стороны (Conductor:2413-2429); ✓игра: проба `setRelation` с откатом (Conductor:4185-4191). Флаги `alliance/peaceTreaty/war` и `declareWar/setNoLongerEnemies` пишутся по договорам дирижёра (Conductor:2385-2408).
Рычаги для живого мира:
- Сделать ядро **источником** чисел: в начале тика читать `getFactionRelation` (туда уже попали поступки игрока и драки NPC через `affectRelations`), а не только перезаписывать его из `S.rel`. Цена: дирижёр перестаёт затирать реакцию ванили, и нужна сверка диапазонов (у нас -100..100, у ядра ? — проверить в игре).
- Доверие: вместо `S.F[a].trust` писать `affectTrust(p, amount, mult)` и читать `trustPositives - trustNegatives`.
- `percievedStrength` читать как «страх» фракции в функции `power()`. Без записи.

### События, меняющие отношения (FactionEvent)
Как в ванили: боевые и социальные поступки идут через `affectRelations(p, FactionEvent, mult)`. Значения: ATTACKED_US_DEFENSIVELY 0, ATTACKED_US_AGGRESSIVELY, DEFEATED_ONE_OF_US_*, KILLED_ONE_OF_US_DIRECTLY 4, KILLED_ONE_OF_US_INDIRECTLY, EXECUTED_ONE_OF_US, AIDED_US_IN_BATTLE, FIRST_AIDED_US, TAKEN_TO_BED, DEFEATED_AN_ENEMY, KILLED_AN_ENEMY, CAPTURED_US 12. ✓код
Точки ядра: `K/FactionRelations.h:39-56`. Колбэк-уведомление `FactionRelations::affectRelations(self, otherFaction, eventType, multiplier)` CR:65 (только наблюдение: `false` гасит лишь следующие Lua-обработчики, движок не прерывает — CR:21).
Lua: да (вызов и колбэк).
Наше использование: нет.
Рычаги:
- **Подписаться на колбэк**: это готовая шина «кто кого обидел/спас» для всего мира, а не только для игрока. Отсюда питать месть, страх, сближение и слухи дирижёра вместо оценок. Цена: частые вызовы в бою, поэтому только копить счётчики, без тяжёлой логики.
- Наши события (освобождение рабов, помощь каравану) проводить через `affectRelations(p, AIDED_US_IN_BATTLE, k)`. Тогда ванильные пороги и UI отношений видят их как родные.
- Подавить событие из Lua нельзя (колбэк — наблюдатель). «Союзник не злится на случайный удар» делается обратной дельтой `affectRelations(p, +x, 1)` сразу после события.

### Репутация и ранг игрока
Как в ванили: `playerRank` (ранг игрока во фракции), `globalReputationTrust`, `globalReputationForBadassery`. Условия диалогов идут через `checkStateCondition(DialogConditionEnum, ComparisonEnum, val, yourFaction)`. ✓код
Точки ядра: `K/FactionRelations.h:68,96,97,104`; `FactionRelations::affectReputation(p, amount)` (`:66`).
Lua: да BR:5854+.
Наше использование: нет.
Рычаги: «слава» игрока за победы над конкурентами → `affectReputation` / `globalReputationForBadassery`. Ванильные диалоги сами начнут реагировать (нелинейная прокачка через встречи). Цена: семантика полей ? — сначала только читать в логе.

### Фракция: состав, отряды, закон, рабство
Как в ванили: `Faction` держит `activePlatoons`/`unloadedPlatoons`, `factionOwnerships` (деньги и имущество фракции), `myLawEnforcementFaction`, `_antiSlavery`, `tradeCulture`, `raceSelector`, `buildingSwaps`, `spawnTimeStamp`. Спавн своих отрядов идёт через `spawnSquadMissionsUpdate` и `_spawnASquad(listname, sizeMultiplier)`. ✓код
Точки ядра: `K/Faction.h`: `getFactionSize` (`:108`), `getActivePlatoons/getUnloadedPlatoons` (`:106-107`), `countPopulation(TownBase*)` (`:81`), `countNumSquads` (`:82`), `getNumPlatoons(template,tempsOnly,hometown)` (`:117`), `getProsperityMultiplier` (`:66`), `_spawnASquad` (`:146`, protected), `getLawEnforcementFaction` (`:125`), `factionOwnerships` (`:129`), `warMgr` (`:133`), `tradeCulture` (`:134`), `getBuildingReplacement` (`:132`). `FactionManager::getAllFactions` (`:194`), `areAnyHostileCampaignsRunning` (`:189`).
Lua: да BR:5673-5779. Колбэки: `Faction::createNewEmptyActivePlatoon` CR:92, `Faction::destroyPlatoon` CR:93, `PlayerInterface::encounterFaction` CR:94; override `Faction::getBuildingReplacement` CR:707, `Faction::chooseARace` (Override-секция CR:692+).
Наше использование: `myLawEnforcementFaction` (Traces:472-476, Outlaws:156); численность через KMM_Native `faction_force` (сырые смещения + SEH, `tools/cpp/kmm_native/src/kmm_native.cpp:487-536`).
Рычаги:
- `Faction:getFactionSize()` и `countPopulation(town)` взять как реальную «силу» вместо `S.F.strength` (дирижёр только подкручивает их через спавн/потери). `faction_force` в плагине нужен лишь для выгруженных отрядов — сначала проверить, не хватит ли Lua-метода.
- `Faction::destroyPlatoon` (CR:93) = отряд фракции уничтожен. Это настоящий сигнал потерь для страха, морали и мести (сейчас мораль идёт через свою модель Self).
- `_spawnASquad(listname, mult)`: ванильный спавн фракции с множителем размера. Можно «богатая фракция → крупнее отряды» без своего спавнера (protected, но в BR есть; ? — безопасность вызова).

### Процветание фракции (ProsperityManager) — неиспользуемый родной «показатель благополучия»
Как в ванили: в `Faction::diplomatMgr` (`FactionUniqueSquadManager`) живёт `ProsperityManager{ actualProsperity (double), maxProsperity }`. Его понижают `notifySquadDefeated(squadTemplate)` и `notifySpecialNPCDead(npc)`, а `update(time)` восстанавливает (?). Отсюда `Faction::getProsperityMultiplier()`. `FactionUniqueSquadManager` также ведёт уникальные отряды (`UniqueSpawnData{desiredNumberToHave, respawnTimer}`, `chooseRandomSquadToSpawn`, `spawnNewUniqueSquad`, `homeTown`). ✓код; влияние множителя на спавн и размер — ?
Точки ядра: `K/FactionUniqueSquadManager.h:12-27` (Prosperity), `:29-72` (UniqueSquad), `K/Faction.h:66,127`.
Lua: да BR:11251 (Prosperity), BR:5978-6021 (UniqueSquad, `respawnTimer` RW).
Наше использование: **нет**. Вместо этого дирижёр ведёт `wealth` и `strength` сам.
Рычаги:
- **Связать богатство дирижёра с `actualProsperity`**: голод, потеря городов и разбитые караваны → вызов `notifySquadDefeated` или прямое снижение `actualProsperity`. Ваниль сама сократит или ослабит спавн (именно связка ванильных механик).
- Читать `getProsperityMultiplier()` как вход для решений дирижёра (кто слаб — тот уязвим для нападения).
- `UniqueSpawnData.respawnTimer`: ускорить или замедлить возврат убитых уникальных отрядов по состоянию фракции.

### Лидер фракции
Как в ванили: `Faction::factionLeader` = `FactionLeader{ faction, biomeTerritory, worstEnemy }`, метод `setNewLeader(Character*)`. Цели миссий: `getEnemyMissionTargetList(out, mission)`. Смерть или плен уникальных NPC живёт в реестре world state и проверяется через `WorldEventStateQuery.uniqueNPCsAre` (DEAD/ALIVE/IMPRISONED). Записи реестра из Lua нет (подтверждено ранее, NATIVE_MAP п.17). ✓код
Точки ядра: `K/FactionLeader.h:17-22`; `K/WorldEventStateQuery.h:9-14,30-31`.
Lua: да BR:5803-5819 (`worstEnemy` RW).
Наше использование: смерть/плен лидера при загрузке зоны (`declareDead`/`setChainedMode`, Conductor), а исход — через `S.resolved` для LINKN.
Рычаги:
- `FactionLeader.worstEnemy`: писать главного врага по войне дирижёра. Ванильные миссии и кампании (?) нацелятся на него. Читать — узнать, кого ваниль сама считает главным врагом.
- `setNewLeader(char)` после гибели лидера: преемник вместо «обезглавленной» фракции (?: что меняет — проверит игра).

## 2. Войны, рейды, кампании

### FactionWarMgr — ванильный генератор войн
Как в ванили: у каждой фракции `warMgr` с `possibleCampaigns` (записи FACTION_CAMPAIGN, itemType 93), `activeCampaigns`, очередью `campaignRequests{timeToStart, data, target, homeBase, enemy, numAttempts}` и `nextUpdateTime`. `periodicUpdate` (?) бросает кости по `CampaignData.triggerChancePerDay01`, `triggerRangeNear/Furthest`, `triggerTargetPopulation/TechLevel`, `worldStateRequirements`, `repeatLimit`. Силы для кампании набираются из городов фракции (`_generateForcesForTown`, `getMyTownsWithEnoughFreePopulation`, `canGenerateThisManyForces`). ✓код
Точки ядра: `K/FactionWarMgr.h:41` periodicUpdate, `:43-45` triggerCampaign ×3, `:37` endCampaign, `:50-55` myTowns/forces/hiredForces/activeCampaigns/biomeTerritories/biomeNoGoZones, `:57` getNearestTown, `:59` getMyTownsWithEnoughFreePopulation, `:62` nextUpdateTime, `:78-80` campaignRequests/possibleCampaigns; `K/Campaign.h:60-112` CampaignData.
Lua: да BR:6023-6100. `triggerCampaign [2]`: `(target RootObjectBase, GameData, minTime, maxTime, hometown, forceDuplicate, triggeringFaction)`.
Наше использование: Conductor:2173-2380, LINKS2 «металлический голод → видимая кампания», только рядом с игроком (`probe_call`). В игре не подтверждено.
Рычаги:
- **Рейд и захват дирижёра = `triggerCampaign` с записью CONQUER_TOWN/ASSAULT_TOWN** вместо броска `math.random() < p` (Conductor:3700). Исход берётся из `CampaignInstance` (фаза VICTORY или уход). Цена: поведение в незагруженной зоне неизвестно (?), нужна игровая проверка.
- Читать `activeCampaigns` у всех фракций: это реальные войны ванили (Пыльные бандиты на Хабе и т.п.). Дирижёр должен знать о них и реагировать, а не жить в своей картине.
- `nextUpdateTime`/`campaignRequests`: отложить или ускорить следующую ванильную атаку по состоянию мира (голодная фракция атакует чаще).

### CampaignInstance — ход одной кампании
Как в ванили: фазы `Phase` GATHERING 0, ASSAULTING 1, RETREATING 2, VICTORY 3, ASSAULT_2_HAPPY 4, ASSAULT_2_ANGRY 5. Тип `WarCampaignEnum` ASSAULT_TOWN 0, CONQUER_TOWN 1, DEFEND_TOWN 2, TRADER_VISIT 3. Есть лидер, `homeTown`, `manPowerMin/Max/LastCount`, `timeWithNoEnemies`. `victoryEvent`/`lossEvent` запускают `victoryTriggers`/`lossTriggers` (FitnessSelector<CampaignTriggerData{what,minTime,maxTime,chance}>), то есть цепочку следующих кампаний. `CampaignData.factionOverride`, `allyTriggers`. ✓код
Точки ядра: `K/Campaign.h:15-23,41-47,49-56,116-196`; `changePhase` (`:138`), `currentPhase` (`:148`), `victoryEvent/lossEvent` (`:152-155`), `getTargetTown` (vtbl).
Lua: да BR:2944 (CampaignData), BR:2993 (CampaignInstance), BR:3053 (CampaignTriggerData). Колбэков на фазы нет (в CR не найдено).
Наше использование: нет.
Рычаги:
- Опрос `activeCampaigns[i].currentPhase` раз в тик: VICTORY по CONQUER_TOWN → событие `town_captured` дирижёра **из ядра**, а не из модели.
- `victoryTriggers`/`allyTriggers` в данных (FCS-поток): союзник по договору дирижёра шлёт свою кампанию следом. Связка через данные, без кода.

## 3. Города

### Владение городом и оккупация
Как в ванили: владелец — `RootObjectBase::owner` (`getFaction()`). Список городов фракции — `FactionWarMgr.myTowns`. Кто ещё живёт в городе — `TownBase.factionsResidentHere`. Оккупанты — `TownBase.occupiers` (`addOccupier/isOccupied`). У отряда — `Ownerships.occupiedTown`, `declareOccupiedTown(t)`, `getOccupiedTownFaction()`. ✓код
Точки ядра: `K/Town.h:161` TownBase::setFaction, `:262` factionsResidentHere, `:269-272` occupiers, `:179` hasResidentHQ; `K/Platoon.h:55-72` Ownerships (homeTown, occupiedTown, declareOccupiedTown); `TownList::getAllTownsOf(out, Faction*)` (`K/Town.h:537-538`, только через `shou`).
Lua: `TownBase:setFaction(faction, _a2)` BR:13612, `occupiers` RW BR:13581, `isOccupied` BR:13661, `Ownerships:declareOccupiedTown` BR:10358. `TownList` из Lua недостижим (нет пути к `SharedKing`).
Наше использование: владение только в модели (`S.F[].towns`). Видимость — через ws-варианты (ниже). Siege берёт объект города из `fo.warMgr.myTowns` (KMM_Siege:94-98).
Рычаги:
- Оккупация вместо смены владельца: отряд захватчика `declareOccupiedTown(t)` + `addOccupier`. Ваниль сама показывает «город под чужой силой» (?), и это обратимо, без переписывания города. Цена: проверка в игре.
- `TownBase:setFaction` — самый прямой рычаг, но высокий риск (лавки, стража, сейв). Только проба на одном городе.
- Читать `myTowns` (а через плагин `shou->townList`) как **истину** «чей город», сверять с `S.F[].towns` и чинить модель по ядру.

### Варианты города (override / replacement)
Как в ванили: город может иметь замену (`Town.replacementTown`, GameData TOWN). Её выбирает world state: записи WORLD_EVENT_STATE через `WorldEventStateQuery{uniqueNPCsAre/AreNot, towns (DEAD/ALIVE…), isAllyOf, isEnemyOf, playerInvolvement}::isTrue()`. Переход — `notifyRepopulation(newTowndata)`. Проверка, валиден ли старый дом отряда, — `isMyOldHomeTownStillValid`. ✓код
Точки ядра: `K/Town.h:349-353`; `K/WorldEventStateQuery.h:16-55`.
Lua: `replacementTown` RW BR:13435, `notifyRepopulation` BR:13473, `WorldEventStateQuery` BR:14616.
Наше использование: KMM_Native хукает `WorldEventStateQuery::isTrue` и отдаёт переопределения по stringID (`kmm_native.cpp:154, 296-347, 661-697`). ✓игра: «WorldEventStateQuery::isTrue hook installed» (logs/session_last.txt:19). Дирижёр включает варианты по смене владельцев (Conductor:3708-3850, LUT `kmm_ws_lut.lua`).
Рычаги:
- Путь через `isTrue` — правильный и родной (ваниль сама перестраивает город). Оставить.
- `towns` в WorldEventStateQuery (город «мёртв») + `TownBase:setDead()` (BR:13643): разрушение города одной записью вместо своих «руин». Цена: необратимо в сейве (?).

### Тревога города
Как в ванили: `TownAlarmState` ALARM_NONE 0, INTRUDER 1, ESCAPE 2, ATTACK 3. Хранится в `TownBase.alarmState`, у `Town` есть `AlarmManager* alarms` (класс без определения в заголовках). Ваниль сама сбрасывает тревогу (по наблюдениям Siege). ✓код
Точки ядра: `K/Town.h:12-18,125-127,210,288,443`.
Lua: `getAlarmState/setAlarmState` BR:13665-13666, `alarmState` RW BR:13577.
Наше использование: KMM_Siege:93-126 держит ALARM_ATTACK импульсом каждые `alarm_pulse` секунд, пока идёт осада.
Рычаги:
- ALARM_INTRUDER на вход игрока с высоким `bounty` или с запрещёнными предметами (`TradeCulture.isItemIllegal`): город реагирует на игрока родной механикой.
- ALARM_ESCAPE при побеге раба игрока или из тюрьмы города.

### Жители, население, расселение
Как в ванили: `TownBase.population` (BasePopulationManager — класс не описан). `residentsSpawned`/`_BarsOrSomething` = `ResidentData{data, buildingsGood/Bad, count, chance, priority}`. Есть `defaultResident`, `Town::chooseResidents/chooseBuildingForResident/spawnTheBarFlies`, `setZonePopulated`. Повторное заселение мира: `GameWorld::populateMapArea_nonPermanent(zone, howMany, rePopulationMode)`. Пауза случайных спавнов: `GameWorld.tempSpawnsDisableTimer`. ✓код
Точки ядра: `K/Town.h:247,261,295-314,346,367-371`; `K/GameWorld.h:63,124-125`; `Faction::countPopulation` (`K/Faction.h:81`).
Lua: `residentsSpawned` RW BR:13583, `population` lightuserdata BR:13559 (не разобрать), `tempSpawnsDisableTimer` RW BR:6979, `populateMapArea_nonPermanent` BR:7071, колбэк `Building::setResidentSquad` CR:80.
Наше использование: нет. Беженцы и голод — модель + видимый спавн Traces.
Рычаги:
- Голод города → уменьшить `ResidentData.count`/`chance` у жителей (меньше людей на улицах) и поднять у бродяг. Видимая пустота без своих спавнов. Цена: применяется при следующем расселении (?).
- `tempSpawnsDisableTimer` после большой битвы: округ «затихает», дороги пустеют. Дёшево и обратимо.
- Беженцы: `Ownerships:setHomeTown(t, SquadType)` (`K/Platoon.h:57`) у загруженного отряда вместо своей ROADS-записи.

### Склады, производство, турели, ворота, двери
Как в ванили: `StorageBuilding` хранит `ConsumptionItem{amount, rate, maxCapacity, item}` (вход и выход). `ProductionBuilding.productionState` (STARVED 0 / FULL 1 / NORMAL 2 / IMPOSSIBLE 3), `getProductionMult`, `getMiningResourceLevel`, `isAnyInputsEmpty`. Питание: `UseableStuff.powerOn/_isBroken/hungerRate`, город считает сеть (`Town::getTotalPower/getRequiredPower/isBatteryMode`). Турель: `TurretBuilding.gunClass`, `operate`, `calculatePowerMult`. Ворота: `GatewayBuilding`, `Town.gates`, `gatesAllClosed`. Двери: `DoorStuff` lock/unlock/open/close/broken, `gateCode`. Поломка: `Building::isBroken/setBroken`. Ваниль подменяет здания фракции через `Faction::BuildingSwaps`/`getBuildingReplacement`. ✓код
Точки ядра: `K/Building/StorageBuilding.h:31-92`; `ProductionBuilding.h:58-151`; `UseableStuff.h:26-175`; `TurretBuilding.h:7-73`; `GatewayBuilding.h:5-31`; `DoorStuff.h:10-123`; `Building.h:204-212,244,256,352-355`; `K/Town.h:212-218,426-439,458`.
Lua: да (BR:12778, 11139, 13924, 7136, 5557, 2442). Колбэки: `ProductionBuilding::_NV_operate` CR:138, `FarmBuilding::eat` CR:148, `TurretBuilding::_NV_operate` CR:149, `Building::_NV_setBroken` CR:98, `DoorStuff::lockDoor` CR:134, `Building::_NV_setFaction` CR:128, `Building::_NV_notifyEffect` (погода на здании) CR:132; override `Ownerships::canIUseThisBuilding` CR:702.
Наше использование: KMM_Stock наполняет инвентари лавок и складов (`Building:getInventory`/`addItem` ✓игра). KMM_Town ловит работу у машин через действие NPC и создаёт продукт в инвентаре машины.
Рычаги:
- Голод города через ядро: у загруженных ферм и производств городской фракции уменьшать `ConsumptionItem.amount` на входах. `productionState` сам станет STARVED, рабочие встанут, и это видно. Цена: только загруженные здания.
- Колбэк `ProductionBuilding::_NV_operate` вместо опроса действий NPC в KMM_Town (Town:1-20): точный сигнал «мастер работает», меньше сканирования.
- Осада: закрыть ворота и двери (`DoorStuff:lockDoor`, `gatesAllClosed`), турели питать только при тревоге (`switchPowerOn`). Город защищается родной механикой.

### Цены и законы города
Как в ванили: цена = база × `Town.tradeGoodsMults[item]` (`getLocalTradePriceMult`) × `TradeCulture` фракции (`getFactionTradeCultureMult`, `TradeCulture.tradeGoodsMults`) × глобальные `PRICE_*` (?, порядок неизвестен). Законы: `TradeCulture.illegalItems/forbiddenItems/illegalBuildings/happyBuildings`, `TownBase::isIllegal(Item*)`. ✓код
Точки ядра: `K/Town.h:153,376-377,474-475`; `K/TradeCulture.h:13-22`; `K/GlobalConstants.h:58-71`.
Lua: `tradeGoodsMults` RW BR:13464 (map GameData→float) и BR:13823, `getLocalTradePriceMult` BR:13487, `TradeCulture` BR:13812, `isIllegal` BR:13607. Override `Platoon::iBuyIllegalGoods` CR:701.
Наше использование: Traces ставит `Platoon.priceMultWhenITrade` каждому торговцу (Traces:768-775, ✓игра). TGM-проба чтения `tradeGoodsMults` пока не дошла до чтения («no home town», logs/debug.log).
Рычаги:
- **Дефицит склада KMM_Stock → `Town.tradeGoodsMults[itemData]`**: одна запись на город вместо множителя на каждого торговца. Её видят все лавки и окно торговли. Цена: индексирование userdata-мапы ключом GameData (проверить в игре).
- Война и оккупация → новый хозяин вносит товары в `illegalItems` (святые запрещают наркотики) — закон меняется вместе с властью.

### Руины: ящики и лут (X4, 2026-11-15)
Как в ванили: руины (лаборатории, купола, арсеналы, гробницы) — это TOWN с постройками-мебелью, у которых есть инвентарь-контейнер. Лут лежит в этих инвентарях, ванильные NPC с пакетом LOOTING его не уносят (?). Сам по себе он не пополняется (?).
Точки ядра: `GameWorld::getObjectsWithinSphere(lektor<RootObject*>&, Vector3, radius, itemType, max, skip)` (`K/GameWorld.h:119`); `hand::getBuilding()` (`K/util/hand.h:52`); `Building::getInventory` (`K/Building/Building.h:344`), `isFurniture` (`:305`), `getTown` (`:354`); `Inventory::isAContainer` (`K/Inventory.h:206`), `getAllItems` (`:227`), `removeItemDontDestroy_returnsItem` (`:172`), `removeItemAutoDestroy` (`:174`), `addItem(item, q, dropOnFail, destroyOnFail)` (`:149`); `Item::getValueAll` (`K/Item.h:46`), `isUnique` (`:79`), `getClassType` (`:115`). ✓код
Lua: да. BR:7053 (сфера; буфер передаётся первым аргументом, как в ContainersReference «Spatial Queries»), BR:7425 `Hand:getBuilding`, BR:2609 `Building:getInventory`, BR:8042/8082/8022/8023/8019/8072 (Inventory), BR:8304 `getValueAll`, BR:8276 `isUnique`, BR:8508 `Item:getClassType`, BR:10618 `Platoon.squadTemplate`. Позиция для сферы — Lua-таблица `{x,y,z}` (так Traces передаёт её в createRandomSquad, ✓игра).
Факт из игры: та же цепочка (сфера → `getBuilding` → `getInventory`, `addItem`/`removeItemAutoDestroy`) работает в KMM_Stock на лавках и складах городов (✓игра). На ящиках руин она ещё не запускалась, вызовы `removeItemDontDestroy_returnsItem` + `addItem` другому персонажу видели только в KMM_Town (?). Под вопросом: попадает ли мебель руин в сферу с типом BUILDING=0 (?); означает ли `quantity` в `addItem` для перенесённой целой стопки «вся стопка» (?).
Наше использование: KMM_RelicRace, блок RUINLOOT. Руинами считаются sites из relicrace.json, разбираются только ящики у руин в пределах `ruin_near` от игрока. (а) Живой отряд-искатель Q1 (его `squadTemplate` есть в `build/KMM_Conductor/rivals.json`, файл пишет `tools/streams/fix.py`) или отряд экспедиции к этим руинам, если он не в бою и на ногах, переносит 3 самые дорогие стопки в инвентарь лидера. Проба `ruinloot probe ok/FAIL: take`. (б) Если экспедиция RelicRace вскрыла руины, при первом приходе игрока в течение 40 дней 6 лучших стопок уничтожаются. Их sid записываются (≤8), и чемпион фракции получает эти вещи заново через createItem. Проба `ruinloot probe ok/FAIL: dig`. Уникальные вещи, ящики фракции игрока и лавки не трогаются. Лимиты: 12 стопок на руины за 30 дней, 40 за сессию. При FAIL или ошибке выключается только разбор руин, а крэш-сторож `state/probe_rl_*.lock` выключает его навсегда. Слухи идут с префиксом `relic_` (`relic_ruins_looting`, `relic_ruins_emptied`). Откат: вынесенное не возвращается, запись в сейв ограничена лимитами.
Рычаги для живого мира:
- Мародёры-конкуренты на руинах игрока решают его маршрут: спешить, перехватить вожака с добычей или идти к другим руинам. Цена: только загруженные руины. Выгруженные руины ядро не держит в памяти, поэтому для них работает только отложенный разбор (б).
- Если игра подтвердит, что мебель руин попадает в сферу, тот же проход может пополнять ящики дальних руин раз в сезон. Тогда руины становятся возобновляемым ресурсом, за который соперничают. Цена: рост сейва, нужна норма из списков лута TOWN.
- Как связать с ядром: вожак, который несёт добычу, может отдавать её `Inventory:getExcessLoot` в ближайшем городе своей фракции. Добыча превращается в товар лавок через KMM_Stock (?, семантика getExcessLoot не проверена).

### Руины: наполнение ящиков из TOWN «loot spawn» (L1, 2026-11-15)
Как в ванили: у TOWN есть ссылки `loot spawn` → VENDOR_LIST (val0..val1 — вероятно, min..max выборок на город (?); в списке `items` val0 — вес (?), плюс `items count`, `money item prob/min/max`). При заселении зоны город раскладывает выборки по своей мебели с инвентарём. Так сделаны 'bandit camp loot' 2..11 и 'nest loot items' (✓данные gamedata.base). Как именно идёт раскладка по ящикам, неизвестно (?). Складской BUILDING «Storage: X» имеет `functionality`=Resource storage, `limit inventory`→ITEM и `itemtype limit`, то есть принимает только свой материал (✓данные). Поэтому в такой ящик попадёт только подходящий предмет, если раскладка вообще учитывает фильтр (?).
Точки ядра: `Town::distributeArtifacts` (`K/Town.h:276`, protected), `Town.artifacts` (`:292`), `addArtifactItem` (`:246`), `spawnDebris(..., spawnItems)` (`:275`); `Inventory::fillFromVendorList(GameData*, Faction*)` (`K/Inventory.h:134-135`); фильтр склада `StorageBuilding::limitedByType`/`specialItemTypesOnly` (`K/Building/StorageBuilding.h:85-86`), `Inventory::isLimitedSlotCompatible` (`K/Inventory.h:75`); тип города `enum TownType` (`K/Town.h:24`: 0 nest … 4 ruins … 9 POI). ✓код
Lua: нет (только данные; заполнение делает движок).
Наше использование: `tools/streams/fix.py` `ruins_fill`, правила в `rules/streams/fix.json` treasure.ruins. Тип места определяется regex по имени TOWN и фракции. Списки «KMM Ruin Lab/Military/Village/Bandit/Junk» и общий «KMM Ruin Materials» (Iron Plates, Steel Bars, Building Material, Fabrics, Leather, Copper и т.п.) идут на склады. Военным точкам ещё добавляется ванильный 'Nest loot weapons low' [0,1]. Предметы дороже 1500 не берутся. Жители-бандиты или скелеты лут не отключают. Пропускаются города, тюрьмы и маркеры, места с баром или торговцами (в том числе с лавками фракции по умолчанию), гнёзда зверей, живые деревни и военные точки без слова руин в имени, а также поселения законных фракций, где есть жители. Если loot spawn уже есть: при сумме max ≥ 25 место пропускается, иначе получает добавку ×0.5. Сборка 2026-11-15 заполнила 201 TOWN: 161 полностью и 40 добавкой. Действует только в новых зонах или новой игре (?). Если зона уже заселена, её лут, видимо, сгенерирован один раз.
Рычаги для живого мира:
- Ящики руин стали источником сырья для ранней стройки. Конкуренты из RUINLOOT разбирают их, и игроку приходится решать, кто успеет первым. Цена: нет, это только данные.
- Если фильтр склада подтвердится в игре (Iron Plates окажутся в «Storage: Iron Plates» руин), стоит сузить Materials по виду складов в зоне. Цена: zone-файлы, отдельный проход.

## 4. Время, скорость, погода

### Время и день/ночь
Как в ванили: игровое время = `TimeOfDay.time` (часы, double) из `GameWorld::getTimeStamp_inGameHours()`. Есть `getTotalDays/Hours`, `addHours`, `timeOfDayHasPassed`. Длина часа — `getLengthOfHourInRealSeconds`. Скорость: `setGameSpeed(speed, click)`, `get/setFrameSpeedMultiplier`, `togglePause/isPaused`. Суточные дела — `GameWorld::dailyUpdates()` (?, что внутри — неизвестно). Свет в точке: `getLightLevel(pos, floor, inside)`. Час суток = `getTotalHours() % 24` (?, где полночь — проверить). ✓код / ✓игра (getTotalDays)
Точки ядра: `K/GameWorld.h:76,123,126-131,234-239`; `K/util/TimeOfDay.h:5-38`.
Lua: да BR:6972-7115, BR:13219-13250.
Наше использование: `game_day()` (Conductor:211, ✓игра), KMM_Tempo (игровое время, пауза).
Рычаги:
- Ночь (`getLightLevel` у города или час суток) → приоритет ночных рейдов, контрабанды и побегов дирижёра. Одно чтение, ванильная семантика света.
- `TimeOfDay` как тип для всех наших таймеров (кулдауны в часах игры) вместо своих счётчиков дней.

### Погода
Как в ванили: регионы (биомы) имеют `WeatherRegion{seasons, currentSeason, currentSeasonIndex/EndDay, weatherInstance}`. Экземпляр — `WeatherInstance{weather, strength, windSpeed, wetness}`. Сама погода — `Weather{affectCharactersType (WA_NONE 0, DUSTSTORM 1, ACID 2, BURNING 3, GAS 4, RAIN 5), affectCharactersStrength, wetness, dust}`. Глобально: `WeatherSystem{ActiveRegionWeather, currentRainValue, currentWindValue, globalWetness, heatHazeValue}`. Ветер в точке: `GameWorld::getWindSpeed(pos)`. ✓код. Записи погоды из Lua нет (`addWeatherEffect` требует userdata; слушатель `weatherUpdated` не связан, UR:384).
Точки ядра: `K/Weather.h:14-60,66-119,124-145,147-189,195-264`; `K/GameWorld.h:135`.
Lua: `WeatherSystem.getInstance()` BR:14584, поля RW BR:14535-14600, `Weather` BR:14402, `WeatherRegion` BR:14491, `Season` BR:12191; колбэк `Building::_NV_notifyEffect` CR:132.
Наше использование: нет.
Рычаги:
- Читать `ActiveRegionWeather.weatherInstance.weather.affectCharactersType` и `strength`: буря или кислота → караваны и рейды дирижёра в этом биоме ждут, цены на еду и лекарства растут (через `tradeGoodsMults`). Только чтение, низкий риск.
- `currentSeason`: сезонный ритм войн (кампании реже в сезон бурь) — данными, без записи.

## 5. Глобальные множители

### GlobalConstants (`con`) и GameplayOptions
Как в ванили: `GlobalConstants` — константы из записи настроек: цены `PRICE_GLOBAL_MULT`, `PRICE_*`, `TRADE_PROFIT_MARGINS`, `FOOD_PRICE_MULT`; опыт `EXPERIENCE_GAIN(_1/_99)`, `XP_*`, `EXPERIENCE_CURVE`, `SKILL_DIFFERENCE_XP_RATIO_MULT_*`; голод `STARVATION_TIME_HRS`, `BED_HUNGER_RATE`, `ENCUMBRANCE_HUNGER_RATE`; производство `PRODUCTION_MULTIPLIER`, `BUILD_SPEED_MULTIPLIER`, `RESEARCH_RATE`; лимиты `MAX_SQUAD_SIZE`, `MAX_SQUADS`, `MAX_FACTION_SIZE`; `PRISON_TIME_MULT`, `attackDiplomats`. `GameplayOptions` — опции новой игры: `deathFrequency`, `numNestsMult`, `productionSpeed`, `researchSpeed`, `buildingSpeed`, `hungerTime`, `globalDamageMultiplier`, `banditsLootPlayer`, `animalsEat`. ✓код
Точки ядра: `K/GlobalConstants.h:4-106`, глобал `con` (`K/Globals.h:30`); `K/GameplayOptions.h:5-24` (дубль в `K/SaveInfo.h:7-27`; живой экземпляр — только `SaveInfo.advanced` и `NewGameOptionsWindow::setOptions`, глобала нет; ?).
Lua: классы связаны (GlobalConstants BR:7219, поля RW; GameplayOptions BR:6912), но **экземпляр из Lua не получить**. Нужен плагин (`con->…`). Колбэк `NewGameOptionsWindow::setOptions` CR:397 даёт объект GameplayOptions только в меню новой игры.
Наше использование: нет.
Рычаги:
- Плагин: экспорт `con_get/con_set(name)` для 5–10 полей (`FOOD_PRICE_MULT`, `PRICE_GLOBAL_MULT`, `PRODUCTION_MULTIPLIER`, `PRISON_TIME_MULT`, `EXPERIENCE_GAIN`). Даёт мировые «эпохи»: голодный год (дороже еда), военное время (быстрее кузни). Цена: глобально для всего мира, не по городу. Записывать в сейв нельзя — переустанавливать при загрузке.
- `MAX_SQUAD_SIZE`/`MAX_FACTION_SIZE` — потолок, о который упирается ванильный спавн. Не трогать без нужды.

---

## Лучшие рычаги для живого мира (ранжировано: польза / цена)

1. **Колбэк `FactionRelations::affectRelations`** (CR:65): готовая шина «кто кого атаковал, убил, спас, пленил» по всему миру. Питает месть, страх, слухи и сближение дирижёра реальными поступками, в том числе игрока. Только слушать и копить, риск низкий.
2. **Читать отношения из ядра, а не только писать**: в начале тика `getFactionRelation` + `RelationData.trust*` → `S.rel/trust`, потом дельты дирижёра через `affectRelations(p, amount, mult)` вместо абсолютного `setRelation`. Ваниль и дирижёр перестают затирать друг друга.
3. **`FactionWarMgr:triggerCampaign` (CONQUER/ASSAULT_TOWN) + опрос `activeCampaigns[].currentPhase`** вместо броска кубика на захват: атака идёт реальными силами, исход берётся из VICTORY/RETREATING, цепочки — из `victoryTriggers`. Нужна игровая проверка выгруженной зоны.
4. **ProsperityManager ↔ богатство дирижёра**: голод, потеря городов и разбитые караваны → `notifySquadDefeated`/`actualProsperity`, решения дирижёра — по `getProsperityMultiplier`. Ваниль сама прореживает спавн бедной фракции.
5. **`Town.tradeGoodsMults` из склада KMM_Stock**: дефицит или избыток → один множитель на город, видимый всем лавкам. Заменяет поторговцевый `priceMultWhenITrade`.
6. **`Faction::destroyPlatoon` (CR:93) + `getFactionSize()/countPopulation()`** как реальная сила и потери вместо `S.F.strength`: мораль и страх по фактическим смертям.
7. **Голод города через `ConsumptionItem.amount` → `productionState=STARVED`** у загруженных ферм и производств + `ResidentData.count` (меньше жителей). Голод становится видимым ванильным простоем.
8. **Тревога и ворота**: `setAlarmState(INTRUDER/ESCAPE)` на преступника или беглеца, `lockDoor`/ворота при осаде (уже есть ATTACK-импульс в Siege — расширить).
9. **`FactionLeader.worstEnemy`**: синхронизировать с главным врагом дирижёра (и читать ванильный). Направляет ванильные миссии.
10. **Оккупация `Ownerships:declareOccupiedTown` + `TownBase.occupiers`** как мягкий захват до `ws_set`-варианта: обратимо, без переписывания города.
11. **Погода (чтение)**: `affectCharactersType/strength` активного региона → пауза караванов и рейдов, рост цен на еду и лекарства через п.5.
12. **Плагин `con_get/set`** для 5–10 глобальных множителей (эпохи мира: голодный год, военное время). Последним: глобально и только через C++.

## Что дирижёр моделирует сам, хотя ядро уже хранит или делает

- **Отношения `S.rel` (-100..100)** — ядро хранит `RelationData.relation` и само меняет его на поступки (`affectRelations`). Сейчас поток односторонний (модель → `setRelation`), реакция ванили затирается.
- **Доверие `S.F[].trust`** — в ядре есть `RelationData.trustPositives/trustNegatives` + `affectTrust`.
- **Договоры `S.treaties` (союз, мир, война)** — флаги `alliance/peaceTreaty/war/coexists` и `declareWar/setNoLongerEnemies` в ядре. Сейчас дублируются: модель главная, флаги — копия.
- **Сила `S.F[].strength` с регеном** — ядро знает реальную численность (`getFactionSize`, `activePlatoons/unloadedPlatoons`, `countPopulation`, `percievedStrength`), потери видны колбэком `Faction::destroyPlatoon`.
- **Богатство `S.F[].wealth` и бедность** — ядро: `ProsperityManager.actualProsperity/getProsperityMultiplier`, деньги фракции `factionOwnerships:getMoney()`.
- **Владение городами `S.F[].towns` из LORE_MAP** — ядро: `owner`/`getFaction()` города, `FactionWarMgr.myTowns`, `factionsResidentHere`, `occupiers`.
- **Исход рейда или захвата бросками (`attack_repelled` с вероятностью p, Conductor:3700)** — ядро: `CampaignInstance` (фазы, силы, VICTORY/loss, цепочки триггеров).
- **Самостоятельный выбор целей войны и частоты рейдов** — ядро: `CampaignData.triggerChancePerDay01/triggerRange*/worldStateRequirements`, `FactionWarMgr.periodicUpdate/campaignRequests`.
- **Списки соседей `CFG.factions[].near` и расстояний городов** — ядро: `FactionWarMgr.getNearestTown`, `biomeTerritories`, `FactionLeader.biomeTerritory` (а `TownList::getNearestInOrder` — через плагин).
- **Мораль от поражений (Self → `f.morale`)** — ядро: `ProsperityManager.notifySquadDefeated`, событие DEFEATED_ONE_OF_US в `affectRelations`.
- **Склад города и голод `S.stock`** — ядро: `StorageBuilding.ConsumptionItem.amount`, `ProductionBuilding.productionState` (STARVED), `Platoon.malnourishedLevel`. Модель склада для выгруженных городов оправдана (ядро считает только загруженные здания), но загруженные должны отражать её через ядро.
- **Цены торговцев `priceMultWhenITrade` по одному (Traces)** — ядро: `Town.tradeGoodsMults` + `TradeCulture` на город и фракцию.
- **Беженцы и переезды (ROADS-записи)** — ядро: `Ownerships:setHomeTown(t, SquadType)`, `Town.residentsSpawned`.
- **Главный враг фракции** (вывод из `rel`) — ядро: `FactionLeader.worstEnemy`.
- **Численность через `KMM_Native.faction_force` (сырые смещения)** — те же списки есть в Lua (`getActivePlatoons/getUnloadedPlatoons`, `getFactionSize`). Плагин оправдан только если Lua-доступ к выгруженным отрядам небезопасен (не доказано).

Оправданно своё (ядро рычага не даёт): долгая память событий и хроника; амбиции и «режимы» реликтовых фракций; экономика выгруженных городов (числа склада); видимость захвата через `isTrue`-хук (ядро даёт только условия world state, не «включить вариант»); реестр смерти лидеров, убитых вне видимости (записи реестра уникалов нет в Lua).
