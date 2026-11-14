# ИИ и отряды: как ванильный мир сам порождает и ведёт отряды (Kenshi 1.0.65)

Домен: пакеты ИИ, задачи, отряды, уникальные отряды, награды, зоны, спавн, world states, кампании.
Источники: `tools/ref/KenshiLib/Include/kenshi/**` (далее имя заголовка:строка), Lua-доки KenshiLua `...\3817000612\docs\`:
`B:n` = BindingsReference.md, `C:n` = CallbacksReference.md, `E:n` = EnumsReference.md. Статусы: ✓игра / ✓код / ?.
Оговорка: заголовки от 1.0.65, установлена 1.0.68 (docs/STATUS.md:55). Смещения полей могли сдвинуться, имена методов обычно те же.

## Сводная таблица

| Механика | Ядро (главная точка) | Lua | Наше использование | Статус |
|---|---|---|---|---|
| Отряд = Platoon (+ActivePlatoon, когда загружен, / UnloadedPlatoon, когда нет) | `Platoon.h:80-194` | да, B:10595, B:614 (UnloadedPlatoon только lightuserdata) | Traces, Nemesis, Fates и др. (`getSquadLeader`) | ✓код, ✓игра (спавн) |
| Создание отряда фабрикой | `RootObjectFactory::createRandomSquad` / `createRandomUnloadedSquad` (RootObjectFactory.h:48-49) | да, B:11961-11962 | Traces:244, Elite:148, Conductor:2577, Veterans | ✓игра (createRandomSquad) / ? (Unloaded) |
| Пустой отряд фракции | `Faction::createNewEmptyUnloadedPlatoon` / `createNewEmptyActivePlatoon` (Faction.h:73-74) | да, B:5673 | нет | ✓код |
| Свой спавн фракции по данным | `Faction::spawnSquadMissionsUpdate`, `_spawnASquad(listname, sizeMult)` (Faction.h:145-146) | нет (protected, не в B) | нет | ✓код |
| Уникальные отряды + процветание | `FactionUniqueSquadManager` (`Faction.diplomatMgr`), `ProsperityManager` (FactionUniqueSquadManager.h:12-72) | да, B:5978, B:11251 | нет | ✓код |
| Пакеты ИИ (миссия отряда) | `Blackboard` (AI/Blackboard.h:55-187), `AIPackage` (AI/AIPackage.h:50-113), 34 сигнала `BlackboardSignalFunctions` | да, B:2226, B:1143, E:181 | Self: только `runAway` | ✓код |
| Задачи и приказы персонажа | `Character::addGoal/addJob/addOrder/setDestination` (Character.h:409-483), `OrdersReceiver` (AI/AITaskSystem.h:86-174) | да, B:10252; колбэки C:85-90 | Predators:62 (`addOrder` PATROL_TOWN/HOLD_POSITION) | ✓код |
| Задачи отряда (squad jobs) | `Blackboard::addSquadJob` (AI/Blackboard.h:113) | да | нет | ✓код |
| GOAP-планировщик | `TaskRepertoire`, `TaskPathfinder`, `TaskData` (AI/TaskRepertoire.h, AI/TaskPathfinder.h, Tasker.h) | частично (TaskData-проверки не связаны, UnboundReference:517-528) | нет | ✓код |
| Поведение невыгруженных отрядов | `UnloadedPlatoonJob` (Enums.h:1203), `AIPackage.unloadedMode`, `Blackboard::getUnloadedPlatoonJob`, `FactionWarMgr::getMyUnloadedAI` | чтение да | нет | ✓код, сама логика ? |
| Кампании (рейды, атаки, защита, визиты торговцев) | `FactionWarMgr` (`Faction.warMgr`, FactionWarMgr.h:19-83), `CampaignData`/`CampaignInstance` (Campaign.h) | да, B:6023, B:2944, B:2993 | Conductor:2198/2306 (`triggerCampaign`), Siege:98 (`myTowns`) | ✓код, в игре не подтверждено |
| Награды за голову и преступления | `BountyManager` (`Character.crimes`, BountyManager.h:13-63), `Bounty`, `CrimeEnum` | да, B:2392; колбэк C:64 | Outlaws:510 (`unfairAddToBounty`), Traces:451-476 (опрос наград) | ✓код; запись награды под крэш-сторожем |
| Охота за головами | задачи `HUNT_BOUNTIES` (204), `FIND_CAGE_AND_PUT_IN_IF_BOUNTY`, `AI::findBounty` (AI/AI.h:403) | TaskType да, findBounty без связи с Lua | Traces BNT спавнит своих охотников | ✓код |
| Запах зоны | `ZoneSmell` (`ZoneMap.zoneSmell`, ZoneSmell.h:14-71), `HUNTING_BLOODSMELL` (176), `scoreHuntingBlood/Eggs` (AI/AI.h:593-595) | да, B:14957 | нет | ✓код |
| World states | `WorldEventStateQuery::isTrue`, `checkAllStatesInObject` (WorldEventStateQuery.h:16-58) | да, B:14616 | KMM_Native: хук `isTrue` + переопределения по stringID (kmm_native.cpp:2, 664-681; kmm_ws_lut.lua) | ✓код; хук в игре не подтверждён |
| Состояние, видимое другим ИИ | `StateBroadcastData` (StateBroadcastData.h:31-92) | да, B:12705 | нет | ✓код |
| Загрузка зон | `ZoneManager` (`GameWorld.zoneMgr`), `ZoneMap::isActive`, `Platoon::PLATOON_LOAD_DISTANCE` (Platoon.h:191) | да, B:14678, B:14799 | косвенно (`load_radius` 15000 в Conductor/Traces) | ✓код |

---

## 1. Отряд: Platoon, ActivePlatoon, UnloadedPlatoon

### Жизненный цикл отряда
Ваниль: каждый отряд — это `Platoon` фракции. Когда он в загруженной зоне, у него есть `activePlatoon` с живыми персонажами. Когда зона выгружена, у него `unloadedPlatoon`: сжатое состояние, которое движок двигает сам. Переход: `Faction::activatePlatoon/deactivatePlatoon` (Faction.h:141-142), `Platoon::activate/deactivate` (Platoon.h:146-147). Временные отряды (`_persistentSquad=false`) при выгрузке удаляются (`reCheckPersistenceOnUnload`, Platoon.h:179). Постоянные хранятся в сейве и живут дальше в `Faction.unloadedPlatoons` (Faction.h:153).
- Точки ядра: `Platoon::isPersistentSquad/setPersistentSquad` (Platoon.h:167-168), `isResidentSquad` (169), `squadType` SQ_RESIDENT/SQ_ROAMING (Enums.h:919), `hasNeverBeenActivated` (165), `messageOnActivation` CM_REFRESH/DECIMATE/DELETE/EMPTY (Platoon.h:12-19, 178), `canRefresh/regenerates` (98-99), `needsNewCharacters` (177), `isDead/imprisoned` (187-188), `malnourishedLevel` (164), `declareDead/undeclareDead` (148-149).
- Связи: `blackboard` (118), `hasCampaign()` (108), `isUnique()` → UniquePlatoon (119), `getOwnerships()` → дом, город, деньги, рабы (Platoon.h:32-78; `setHomeTown(TownBase*, SquadType)` :57), `getPatrolInfo/setupPatrolSettings(min,max)` (159-160), `get/setRoamingMapArea(AreaBiomeGroup*)` (161-162).
- ActivePlatoon: `getMemory()` → CharacterMemory отряда (Platoon.h:213), `teleport(pos)` (241), `setSquadLeader` (229), `isWholeSquadDown` (237), `currentGoal` (274), `refreshInventory` (232).
- Lua: Platoon да (B:10595: все поля RW, кроме `blackboard` R). ActivePlatoon да (B:614). `unloadedPlatoon`, `patrolSettings`, `currentSpawnArea` — только lightuserdata, полей не прочитать. Список отрядов фракции: `Faction:getActivePlatoons()/getUnloadedPlatoons()` (B:5673), это `lektor<Platoon*>` с индексами от 1 (ContainersReference:34). Позиция невыгруженного отряда: `Platoon` наследует RootObjectBase, у которого есть `getPosition()` ✓код (будет ли позиция актуальной у невыгруженного — ?).
- Колбэки: `Faction::createNewEmptyActivePlatoon` (C:92), `Faction::destroyPlatoon` (C:93), `ActivePlatoon::_NV_addActiveObject/_NV_removeObject` (C:60-61), `Platoon::taskIsComplete` (C:62), `Platoon::_NV_loadFromSerialise` (C:106), `Building::setResidentSquad` (C:80). Переопределение `Platoon::_CONSTRUCTOR` (C:730) позволяет подменить шаблон/позицию любого ванильного отряда при создании.
- Наше использование: `getSquadLeader` (Fates, Nemesis, Outlaws, Predators, RelicRace, Self), `declareDead` (Conductor:2486, Traces:654/1503, Tempo), `squadTemplate` (Gov, Traces, Elite). Плагин `faction_force` читает `activePlatoons/unloadedPlatoons` через SEH по смещениям (kmm_native.cpp:449-480), хотя в Lua те же списки доступны через биндинги.
- Рычаги для живого мира:
  1. Конкурента делать **постоянным** отрядом (`permanentsquad=true` в фабрике или `setPersistentSquad(true)`). Тогда движок хранит и двигает его вне видимости, и это настоящий отряд, а не наша запись. Цена: рост сейва, поведение невыгруженного отряда (?).
  2. Учёт «кто из конкурентов жив» вести по `Platoon.isDead/imprisoned/getCharacterCount()` на этом объекте вместо параллельных флагов.
  3. Через `messageOnActivation = CM_DECIMATE` можно оформить «отряд сильно потрепало, пока игрок не видел»: движок сам проредит его при загрузке (✓код, эффект ?).

### Создание отряда
Ваниль: фабрика `RootObjectFactory` (`GameWorld.theFactory`, GameWorld.h:100) собирает отряд из шаблона SQUAD_TEMPLATE: раса (`Faction::chooseARace`, это override C), снаряжение, размер × `sizeMultiplier`, дом, цель ИИ. Фракция спавнит сама по своим спискам (`_spawnASquad(listname, sizeMult)`, `spawnSquadMissionsUpdate`, Faction.h:145-146), города — жителей и «завсегдатаев бара» (`TownBase.residentsSpawned`, `Town:spawnTheBarFlies`, B:13428/13551). Биомы — бродячие отряды через `AreaSector`/`currentSpawnArea` (Platoon.h:181) и `ZoneManager::spawnChecksUpdateThreaded` (ZoneManager.h:348).
- Точки ядра: `createRandomSquad(faction, pos, homeTown, maxnum, home, squad, owner, maparea, _activePlatoon, permanentsquad, AItarget: hand, targetTown, sizeMultiplier, squadType, isJustARefresh)` и `createRandomUnloadedSquad(... без activePlatoon/sizeMult ...)` (RootObjectFactory.h:48-49). Также `Faction::createNewEmptyUnloadedPlatoon(template, pos, forceChars, persistent)`, `createPlatoonUnloaded/Auto` (Faction.h:73-77). Счётчики `Faction::getNumPlatoons(template, tempsOnly, hometown)` (117) и `countNumSquads` (82).
- Lua: да, B:11961-11962, B:5673. `AItarget` обязателен как настоящий hand (nil → ошибка, ✓игра, DECISIONS:139). Vector3 можно передать таблицей `{x,y,z}` ✓игра (Veterans:8).
- Наше использование: все появления у игрока идут через `KMM_Traces.spawn` (Traces:243-246) с `permanentsquad=false, squadType=2 (SQ_ROAMING)`, плюс `Elite:148` и `Conductor:2577` (союзники по договору). ✓игра: «trace column: Mongrel … at 4489 from player» (logs/debug.log, 2026-11-14).
- Рычаги:
  1. `createRandomUnloadedSquad(..., permanentsquad=true, AItarget, targetTown, SQ_ROAMING)` спавнит конкурента **вдали** от игрока. Он дойдёт сам (UPJOB_TRAVEL_TARGET), и не нужно материализовать его «рядом с игроком» (?: в игре не проверяли).
  2. Override `Platoon::_CONSTRUCTOR` / `Faction::chooseARace`: перекраивать **ванильные** спавны (бродячая банда региона превращается в банду конкурента с нужным шаблоном) вместо того, чтобы добавлять свои отряды поверх ванильных. Это ноль лишних спавнов. Цена: хук срабатывает на каждом спавне, нужен очень дешёвый фильтр.
  3. `getNumPlatoons(template)` даёт плотность конкурентов фракции прямо из движка (вместо счётчика S.ext).

---

## 2. Пакеты ИИ, миссии и задачи

### Blackboard и AIPackage (миссия отряда)
Ваниль: у каждого Platoon есть `Blackboard`. Это набор `AIPackage` по уровням приоритета (`packagesMain`). Активный пакет задаёт цель миссии (`missionTown/missionTarget/missionEmployer`), скорость, оценку врагов и нейтралов, поведение невыгруженного отряда (`unloadedMode`) и цепочку `leadsToPackage`. Пакеты задаются в данных (AI_PACKAGE в FCS) и приходят от шаблона отряда (`addPackages`), фракции (`addFallbackPackages`), кампании (`CampaignData.aiPackages[Phase]`) и контракта (наём, Contract.h).
- Точки ядра (AI/Blackboard.h): `createNewPackage(key, data, priority, giver)` :64, `addPackages(collection)` :88, `addFallbackPackages` :89, `replaceAIPackage(GameData*)` :90 (+ поле `replacementAIPackageSID` :63), `setContractJob(collection, giver)` :75 / `_setContractJob(pkg, hours, giver)` :65 / `endContractJob` :76, `getCurrentAIPackageName` :91, `getMissionTarget(who)` :126, `getMissionTown(fallbackHome)` :127, поля `targetTown` :122, `targetZoneHunting` (ZoneMap для охоты) :123, `moraleIsBroken` :132, `runAway()` :154, `getUnloadedPlatoonJob()` :115.
- Сигналы пакетов (`BlackboardSignalFunctions`, AI/Blackboard.h:17-53, E:181) показывают, что ваниль умеет делать сама: SIG_START_PATROL / _RUNNING, SIG_WANDERING_TOWN_TO_TOWN, SIG_HANG_OUT_AT_BAR, SIG_RAIDING_WEAK_VILLAGES, SIG_SLAVER_SHIP_TO_WORKCAMPS / _ANYWHERE_CLOSE, SIG_GATHER_UP_ALL_LOCAL_PRISONERS, SIG_DIPLOMAT_MISSION, SIG_BODYGUARD, SIG_DEFEAT_SQUAD, SIG_PASSING_BY_TOWN_ASSAULT, SIG_OCCUPY_CONQUERED_TOWN, WAR_GATHER_FORCES / WAR_ASSAULT_TOWN / WAR_BATTLE_MEETING, SIG_REFUGEE_DISBAND, SIG_DEFEND_PLAYER_TOWN_TIMED / _CAMPAIGN, SIG_TIMED_CONTRACT, каннибальские рейды с отходом к гнезду.
- Контракты (AI/Contract.h): `Contract_Timed`, `Contract_UntilOutOfDanger` (сопровождение до безопасности), `Contract_UntilExSlave`, `Contract_HiredAlly` (наёмник: предательство, продление), `Contract_DefendPlayerBase`; `Campaign_DefendPlayerBase` (Campaign.h:200).
- Lua: Blackboard да (B:2226: поля RW, методы выше), AIPackage да (B:1143), `Character:getBlackboard()` и `Platoon:getBlackboard()`. GameData пакета: `gw.gamedata:getData(sid, type)`, как у шаблонов отрядов.
- Наше использование: только `Blackboard:runAway()` (Self:194/285/289). Пакетов не назначаем нигде.
- Рычаги:
  1. После спавна конкурента вызывать `bb:replaceAIPackage(gd)` с ванильным пакетом (бродить от города к городу, отдыхать в баре, грабить слабые деревни). Тогда маршрутом, остановками и поведением вне экрана управляет движок, а не наш «путь» в Traces. Цена: нужен список AI_PACKAGE из данных (генератор); пакет может уйти на fallback фракции (?).
  2. `setContractJob(collection, giverHand)` даёт «временный союз/найм» в стиле ванили: конкурент сопровождает игрока N часов, потом уходит, предательство отслеживает движок (`contractJobWasBetrayal`). Это готовый механизм для «нанятого соперника».
  3. Читать `getCurrentAIPackageName()` и `moraleIsBroken` у отрядов рядом: события «банда бежит/сменила миссию» для хроники без своих эвристик.

### Задачи персонажа и отряда (TaskType, GOAP)
Ваниль: ИИ персонажа (`AI` → `AITaskSytem` : `OrdersReceiver`) выбирает цель (goal) по приоритетам из `goals[5]` и `squadAIPackage[5]` (AI/AITaskSystem.h:160-161), затем GOAP (`TaskPathfinder::solve`, AI/TaskPathfinder.h:52) строит цепочку действий по требованиям и результатам `TaskData` (Tasker.h:33-110). Приказы игрока — `orders`, работа — `jobs/permajobs`. Отряд раздаёт задачи через `Blackboard::addSquadJob(SquadMemberType, TaskType, subject, pri, weight, targeting, ending, start, end)` (AI/Blackboard.h:113), `addRequest` (:108) и списки `leaderJobs/squadJobs/signalJobs` (:159-162).
- Полезные TaskType (E:1025): MOVE_ON_FREE_WILL 1, ATTACK_ENEMIES 16, RAID_TOWN 18, PATROL 22, ATTACK_TOWN 23, WANDERER 24, MOVE_CUS_ORDERED 29, PATROL_TOWN 36, BODYGUARD 45, TRAVEL_TO_TARGET_TOWN 53 / _FAST 130, TOWN_STALKER 165, HUNTING_BLOODSMELL 176, HUNT_BOUNTIES 204, TRAVEL_TO_TARGET_PACKAGE 215, ASSAULT_FORTIFICATIONS_PREFER_GATES 270; ещё FIND_AND_KIDNAP, LOOT_THE_DEAD, HUNT_MY_THIEF, FIND_CAGE_AND_PUT_IN_IF_BOUNTY.
- Точки ядра: `Character::addGoal(t, subject)` :409, `addJob(t, subj, shift, addDontClear, loc)` :411, `addOrder(destBuilding, t, subj, shift, clear, loc)` :422, `setDestination(pos, shift)` :483 (Character.h); `AI::setAggressionLevel`, `setManuveringFreedomLevel` (HOLD_GROUND/STAY_CLOSE/ROAM_FAR), `setCenterOfMovement(Target)` (AI/AI.h:205-209).
- Lua: всё перечисленное есть (B:3277 и рядом, B:10252). Колбэки `Character::addGoal/addJob/addOrder/removeJob` (C:85-88). Проверки `TaskData::isResultsComplete` и поиск целей (`findTarget`) не связаны (UnboundReference:517-528).
- Наше использование: Predators:56-62 — `leader:addOrder(nil, PATROL_TOWN|HOLD_POSITION, nil, false, true, pos)` под крэш-сторожем. Цель засады задаётся через `AItarget` фабрики (STATUS:105).
- Рычаги:
  1. `addSquadJob` вместо `addOrder` на лидера: задача достаётся всему отряду, у неё есть время окончания (`endTime`) и событие конца (`TEE_REMOVE_WHOLE_SQUADS`). Это законный «наряд», а не приказ игрока (приказы игрока ИИ ставит выше всего и отпускает плохо, ?).
  2. Для засады у дороги: HOLD_POSITION + `setCenterOfMovement(pos)` + `ROAM_FAR/STAY_CLOSE` дают радиус, в котором банда держится сама.
  3. `HUNT_BOUNTIES` как goal (`addGoal`) охотнику-конкуренту: он будет искать цели с наградой ванильным `findBounty` (см. §4).

### Поведение невыгруженных отрядов
Ваниль: невыгруженный отряд не симулирует персонажей. Faction раз в тик вызывает `updateUnloadedPlatoons` (Faction.h:143) → `Platoon::periodicUpdate_unloaded` (Platoon.h:157). Поведение задаёт `UnloadedPlatoonJob` (Enums.h:1203): NONE, PATROL_TOWN, PATROL_SHORTRANGE, PATROL_LONGRANGE, GOHOME, TRAVEL_TARGET, TRAVEL_TARGET_FAST. Источник: активный пакет (`AIPackage.unloadedMode`), кампания (`CampaignInstance::getUnloadedPlatoonBehavior`, `travelSpeedUnloaded`) или `FactionWarMgr::getMyUnloadedAI`. При подходе игрока на `PLATOON_LOAD_DISTANCE` отряд загружается на текущей позиции.
- Lua: прочитать можно (`bb:getUnloadedPlatoonJob()`, `warMgr:getMyUnloadedAI(p)`, `Platoon.isDead/imprisoned/_characterCountCurrent/malnourishedLevel/squadTemplate`). Сам `UnloadedPlatoon` закрыт (lightuserdata). Колбэка на «невыгруженный отряд дошёл» нет. Есть `Platoon::taskIsComplete` (C:62), но для невыгруженных он ?.
- Наше использование: нет. Дальний мир целиком наш (S.roads.tr, S.ext.*).
- Рычаги:
  1. Вести конкурентов как постоянные невыгруженные отряды с UPJOB_TRAVEL_TARGET. Наш дирижёр меняет только цель (`AItarget/targetTown` при создании или пакет), а не позицию.
  2. Раз в игровой день сверять список `getUnloadedPlatoons()` нужных фракций с нашими записями (без SEH-плагина): сколько осталось, кто мёртв, кто в тюрьме.

---

## 3. Кампании (рейды на базу игрока, атаки на города)

### FactionWarMgr и CampaignInstance
Ваниль: у каждой фракции есть `warMgr` (Faction.h:133). Он хранит `possibleCampaigns` (CampaignData из FACTION_CAMPAIGN), очередь `campaignRequests` (время старта, цель, база, попытки сменить цель), `activeCampaigns`, карту `forces` (Platoon → кампания), `myTowns`, территории и запретные биомы (FactionWarMgr.h:28-80). Территориальные кампании запускаются сами (`triggersRandomly_territorial`, `triggerChancePerDay01`, диапазоны `triggerRangeNear/Furthest`, `triggerTargetTechLevel/Population`, Campaign.h:73-82). Это включая рейды на базу игрока по её размеру и технологиям, ?: точные условия в коде движка. Условие запуска — `worldStateRequirements` (WorldEventStateQueryList, :83). Силы собирают `getAllTheForces/_generateForcesForTown` из городов с населением (`getMyTownsWithEnoughFreePopulation`). Фазы кампании `Phase` (Campaign.h:15-23): GATHERING → ASSAULTING → RETREATING / VICTORY (+ ASSAULT_2_HAPPY/ANGRY для визитов с требованием). На каждую фазу свои пакеты для лидера и бойцов (`aiPackagesLeader/aiPackages[Phase]`, :108-109). Исход: `victoryTriggers/lossTriggers` (:110-111) запускают следующие кампании (цепочки). Виды кампаний (`WarCampaignEnum`): ASSAULT_TOWN, CONQUER_TOWN, DEFEND_TOWN, TRADER_VISIT. Прочее: `specificTargetCharacter/specificLeaderCharacter` (охота за конкретным персонажем, лидер — уникальный NPC), `canTalkToBeforeArrival`, `getDialogData(EventTriggerEnum)` (переговоры), `allyTriggers` (союзники присылают подмогу), `manPowerMin/Max/LastCount`, `hasSufficientManpower`, `timeWithNoEnemies`.
- Точки ядра: `triggerCampaign(target, CampaignData*, home)` → CampaignInstance (FactionWarMgr.h:43); `triggerCampaign(target, GameData*, minTime, maxTime, hometown, forceDuplicate, triggeringFaction)` (:44, в очередь); `triggerCampaign(FitnessSelector<CampaignTriggerData*>, ...)` (:45); `endCampaign` (:37), `getCurrentCampaign(Platoon*)` (:46), `areAnyHostileCampaignsRunning(playeronly)` (:36); `CampaignInstance::changePhase/currentPhase/victoryEvent/lossEvent/addToCampaign/removeFromCampaign/getTargetTown/_target/leader/membersInOrder` (Campaign.h:116-198); `Platoon::hasCampaign()` (Platoon.h:108).
- Lua: всё есть (B:6023, B:6072, B:2944, B:2993, B:3053; `Phase` E:447, `WarCampaignEnum` E:458). `campaignRequests` имеет тип `unknown` (B:6023), очередь не прочитать.
- Наше использование: Conductor `CA.try/CA.fire` (Conductor:2296-2380) запускает родную кампанию перегрузкой [2] **только если цель рядом с игроком** (`pick_town` в `load_radius`), с подкреплением союзника. `ore_campaign_try` (Conductor:2176-2200) работает так же. Siege читает `warMgr.myTowns` (Siege:98). Данные: campaigns.json (386 FACTION_CAMPAIGN, gen_campaigns.py; DECISIONS:229). В игре запуск не подтверждён (STATUS:13).
- Рычаги:
  1. Перегрузка [2] ставит кампанию в **очередь** (`minTime/maxTime`). Значит, её можно запускать и вдали от игрока, если ограничиться кампаниями с сильным маркером на карте (`markOnMap`). Это проверить первым в сессии: `#warMgr.activeCampaigns` до и после, затем `currentPhase`.
  2. Осаду (Siege) строить на фазах CampaignInstance: читать `currentPhase` и `manPowerLastCount` и вести по ним модель склада города, вместо своей шкалы 3–7 дней. Исход брать из `victoryEvent/lossEvent` (опросом `activeCampaigns`).
  3. Кампании с `specificTargetCharacter` = охота на конкретного персонажа. Это ванильный шаблон для «конкурент собрал банду и идёт за игроком/за другим искателем» (нужна запись FACTION_CAMPAIGN в данных; генератор).

---

## 4. Награды за голову и охотники

### BountyManager и охотники
Ваниль: у каждого персонажа есть `crimes` (BountyManager, Character.h:209). Свидетель преступления вызывает `notifyCrimeWitnessed(faction, againstWho, expiry, CrimeEnum)`. Затем `assignBountyForCrimes(enforcer)` начисляет награду по `getBountyForCrime(c)` в `bounties[Faction]`. Награда истекает (`getBountyExpirationTime(amount)`), тюремный срок считается от суммы (`getPrisonSentenceInHours`). Другие видят награду только выше порога узнавания: `getPercievedBounty(whosLooking)` и `getBountyRecognitionThreshold()`, плюс `StateBroadcastData.looksLike_bounty` и маскировка (`disguiseFaction/disguiseBlown`). Стража, а также отряды с задачей `HUNT_BOUNTIES` (E:1025 = 204) через `AI::findBounty` (AI/AI.h:403) нападают, вяжут и сдают пленника в клетку (`FIND_CAGE_AND_PUT_IN_IF_BOUNTY`). Сдача игроком: `notifyPlayerClaimBounty`, флаг `bountyHasBeenClaimedOnce`. Пропуск: `giveAccessPass(faction, minutes)`.
- Точки ядра (BountyManager.h): `unfairAddToBounty(enforcer, amount)` :30, `clearBounty(enforcer)` :32, `getActualBounty(f)` :26, `getTotalBounty` :33, `_getHighestBountyFaction` :19, `setCrime` :40, `notifyStartPrisonSentence` :52, `hasAccessPass/giveAccessPass` :53-54; правоохранители: `Faction.myLawEnforcementFaction` / `getLawEnforcementFaction()` (Faction.h:123-125). `CrimeEnum` (Bounty.h:6-26).
- Lua: всё (B:2374, B:2392). Колбэк `BountyManager::notifyCrimeWitnessed` (C:64). Override `Bounty::_CONSTRUCTOR` (C:733).
- Наше использование: Outlaws:510 вешает ядровую награду на лидера разыскиваемого (`unfairAddToBounty`, крэш-сторож `probe_bounty_add`), Outlaws:513 читает `getTotalBounty`. Traces:451-499 (BNT) раз в 4 игровых часа опрашивает награды игрока и при сумме ≥5000 спавнит **своих** охотников от `myLawEnforcementFaction` (Traces:472-476, 600).
- Рычаги:
  1. Конкурентам-искателям вешать ядровую награду по их делам (убил каравана — `unfairAddToBounty` у фракции хозяина). Тогда их сами ловят стражи и ванильные охотники, а игрок может их сдать. Это нелинейная прокачка через встречи без новых переменных.
  2. Подписаться на `BountyManager::notifyCrimeWitnessed` (C:64) вместо опроса раз в 4 часа: это событие «игрок попался» для Nemesis/Traces. Новые хуки сначала только логировать (DECISIONS:146).
  3. Охотнику-конкуренту ставить `addGoal(HUNT_BOUNTIES)`. Цель он выбирает сам, с учётом порога узнавания и маскировки, и тогда маскировка игрока работает против наших охотников тоже.

---

## 5. Уникальные отряды и процветание фракции

### FactionUniqueSquadManager и ProsperityManager
Ваниль: `Faction.diplomatMgr` (Faction.h:127) держит список уникальных шаблонов (`squads`: шаблон, `desiredNumberToHave`, `respawnTimer`, `existingSquadsList`). Раз в период `chooseRandomSquadToSpawn(time)` и `spawnNewUniqueSquad(template)` поддерживают численность. `endOfUniqueSquad` вызывается при гибели (FactionUniqueSquadManager.h:29-72). `ProsperityManager` хранит процветание фракции (`actualProsperity/maxProsperity`), его снижают `notifySquadDefeated(template)` и `notifySpecialNPCDead(npc)`. Множитель `getProsperityMultiplier()` (= `Faction::getProsperityMultiplier`, Faction.h:66), ?: судя по названию, влияет на размер и частоту спавна.
- Lua: да (B:5978, B:6005, B:11251), поле `Faction.diplomatMgr`. Override `FactionUniqueSquadManager::_CONSTRUCTOR` (C:763).
- Наше использование: нет. Elite спавнит UNIQUE_SQUAD_TEMPLATE своими данными (FACTION."special squads" + замок WORLD_EVENT_STATE, DECISIONS:231) и Lua-фабрикой (Elite:148).
- Рычаги:
  1. Каждая разбитая игроком банда → `prosperityMgr:notifySquadDefeated(template)`. Фракция беднеет по-ванильному, спавнит меньше. Это связка «встречи с конкурентами → облик мира» без S.F-богатства (?: нужно проверить, что дирижёр не пишет то же своим счётчиком).
  2. Именных конкурентов оформить как запись `squads` (желаемое число 1, `respawnTimer`): павший возвращается через ванильный таймер с новым лидером.
  3. Читать `UniqueSpawnData.currentNumber()/respawnTimer` для слухов («у Империи снова собрали отряд X»).

---

## 6. Зоны, запах и загрузка

### ZoneSmell (кровь, трупы, яйца)
Ваниль: у каждой зоны есть `zoneSmell` (ZoneManager.h:246) с двумя запахами, `SMELL_BLOOD_AND_CORPSES` и `SMELL_EGG` (ZoneSmell.h:7-12). Трупы и кровь добавляют сообщения (`addSmell(SMELLMSG_CORPSE|BLOOD|EGG, key, pos)`), сила растёт и спадает (`increaseRate/decreaseRate`). Хищники с задачей `HUNTING_BLOODSMELL` (176) оценивают `scoreHuntingBlood/scoreHuntingEggs` (AI/AI.h:593-595) и идут к источнику (`getSmell(posInOut, type)`). Поле `Blackboard.targetZoneHunting` (AI/Blackboard.h:123) задаёт отряду зону охоты.
- Lua: да, B:14957 (`ZoneManager:getZoneMap(v)`, B:14756, `gw.zoneMgr`, B:7000). Особенность: в Lua `getSmell` возвращает Vector3 (позицию), а число силы теряется (?). Сила зоны берётся из `getGeneralSmellLevel(type)`. Ключ `addSmell` — userdata (lightuserdata любого объекта).
- Наше использование: нет. Herds/Predators считают свой «жар» участков.
- Рычаги:
  1. После боя или разорения каравана рядом с игроком вызывать `zs:addSmell(SMELLMSG_BLOOD, ключ, pos)`: ванильные хищники придут сами и съедят тела. Падальщики на месте битвы без нашего спавна.
  2. Herds/Predators: брать `getGeneralSmellLevel(SMELL_BLOOD_AND_CORPSES)` загруженных зон как вход «опасности» участка вместо своего счётчика.

### Загрузка зон и видимость
Ваниль: зоны (сетка 64×64, ZoneManager.h:423) активирует камера, персонаж игрока или город (`ZoneActivationType`, :80-85). Отряды загружаются на `Platoon::PLATOON_LOAD_DISTANCE` (Platoon.h:191). У загруженной зоны `isActive()` (ZoneManager.h:227).
- Lua: `ZoneManager:getZoneMap(pos)`, `ZoneMap:isActive()`, `getAllActiveZones` (через биндинг, B:14678). `_activate` не связан (UnboundReference:559).
- Наше использование: везде радиус `load_radius` 15000 (Conductor:2186, CA.pick_town).
- Рычаг: заменить эвристику радиуса на `zoneMgr:getZoneMap(pos):isActive()`. Это точнее, дешевле и совпадает с тем, когда движок реально видит отряды.

---

## 7. World states

### WorldEventStateQuery
Ваниль: WORLD_EVENT_STATE в данных задаёт условие: уникальные NPC живы/мертвы/в тюрьме (`uniqueNPCsAre/AreNot`), состояние городов (`towns`), союз или вражда с фракциями (`isAllyOf/isEnemyOf`), участие игрока (`playerInvolvement`) (WorldEventStateQuery.h:16-42). На эти условия завязаны кампании (`worldStateRequirements`), замены городов (Town overrides, `ZoneManager.updatedTownOverrides`), диалоги и спавн (`checkAllStatesInObject(obj, listname)`).
- Lua: да (B:14616, B:14641), `WorldEventStateQuery.getFromData(gd):isTrue()`. Override `_CONSTRUCTOR` (C:774).
- Наше использование: KMM_Native хукает `isTrue` и `getFromData` и переопределяет результат по stringID из Lua (kmm_native.cpp:2, 664-695). Таблица `kmm_ws_lut.lua` генерируется (tools/cpp/ws_town_lut.py) для смены владельцев городов. В игре хук не подтверждён (`ws_stats().hits`, STATUS:115).
- Рычаги:
  1. Гибель или пленение конкурента-уникала: ваниль сама переключит состояния (ALIVE/DEAD/IMPRISONED) и реакции городов, диалоги, кампании мести (`lossTriggers`). Значит, конкурентов лучше делать из уникальных NPC с записями WORLD_EVENT_STATE, а не из наших имён на временном лидере.
  2. Наш хук дать дирижёру как «рубильник сюжета»: состояние «Искатель X добыл реликт» гейтит ванильные кампании и диалоги.

### StateBroadcastData (что видят другие ИИ)
Ваниль: каждый персонаж публикует состояние: `apparentStrength/actualStrength`, `distress`, `intendsToAttack`, `combatTargetsFaction`, `looksLike_bounty/intruder/escapedSlave`, маскировку, `myPersonality` (PT_HONORABLE, TRAITOROUS, BRAVE, FEARFUL…), `isAggressor` (StateBroadcastData.h:31-92). Другие ИИ решают по нему, напасть или помочь.
- Lua: да, B:12705 (`Character:getStateBroadcast()`, `Platoon:getStateBroadcast()`).
- Наше использование: нет.
- Рычаг: `apparentStrength` отряда игрока против силы конкурента → решение конкурента «нападать / торговаться / обойти» в нашем ИИ встречи берём из ванильной оценки, а не из своих тиров.

---

## Лучшие рычаги для живого мира (ранжировано)

1. **Конкуренты как постоянные невыгруженные отряды.** `createRandomUnloadedSquad(..., permanentsquad=true, AItarget, targetTown, SQ_ROAMING)` или `Platoon:setPersistentSquad(true)` после спавна. Движок хранит их в `Faction.unloadedPlatoons`, двигает по `UnloadedPlatoonJob` и загружает там, где они реально есть. Убирает материализацию «рядом с игроком» и параллельные записи. Статус ✓код, поведение ?. Цена: сейв, лимит ≤10–15 штук.
2. **Миссию задаёт ванильный пакет ИИ.** `Blackboard:replaceAIPackage(gd)` / `setContractJob` с AI_PACKAGE из данных (бродить от города к городу, бар, рейд слабых деревень, сопровождение). Маршрут, отдых, поведение вне экрана и бегство ведёт ядро. Нужен генератор списка пакетов. ✓код.
3. **Все крупные атаки через `FactionWarMgr:triggerCampaign`,** включая дальние (перегрузка [2] с очередью) и осады через фазы `CampaignInstance` (`currentPhase`, `manPowerLastCount`, victory/loss). Первая проверка в сессии: рост `#activeCampaigns`. ✓код, в игре не подтверждено.
4. **Ядровые награды на конкурентов** (`unfairAddToBounty` за их дела) + `addGoal(HUNT_BOUNTIES)` охотникам. Стража, охотники и сдача в клетку ванильные; маскировка и порог узнавания работают сами. ✓код (Outlaws уже на этом пути).
5. **События вместо опросов:** `BountyManager::notifyCrimeWitnessed` (C:64), `Faction::destroyPlatoon` (C:93), `Platoon::taskIsComplete` (C:62), `ActivePlatoon::_NV_add/removeObject` (C:60-61). Это дешевле опроса в Traces/Nemesis, и реакция мгновенная. Сначала только лог.
6. **Перекраивать ванильные спавны, а не добавлять свои:** override `Platoon::_CONSTRUCTOR` / `Faction::chooseARace` (C:730). Бродячая банда региона становится бандой конкурента. Ноль лишних отрядов. Цена: дешёвый фильтр в горячем хуке.
7. **Процветание фракции от встреч:** `prosperityMgr:notifySquadDefeated(template)` при разгроме банды. Фракция слабеет по-ванильному (`getProsperityMultiplier`). Связывает бои игрока с обликом мира. ✓код, эффект ?.
8. **Запах боя:** `zoneSmell:addSmell(SMELLMSG_BLOOD/CORPSE, key, pos)` на месте схваток и разорённых караванов. Ванильные хищники приходят сами. Вход «опасности» для Herds/Predators: `getGeneralSmellLevel`. ✓код.
9. **Уникальные конкуренты + world states.** Именные искатели как уникальные NPC/отряды (`FactionUniqueSquadManager`: желаемое число, `respawnTimer`). Их смерть или плен меняет WORLD_EVENT_STATE, и на это сами реагируют диалоги, кампании мести и города. Наш хук `isTrue` (KMM_Native) работает как рубильник сюжета. ✓код.
10. **Наряд отряду вместо приказа лидеру:** `Blackboard:addSquadJob(..., endTime, TEE_REMOVE_WHOLE_SQUADS)` + `AI:setCenterOfMovement/setManuveringFreedomLevel` для засад и патрулей (вместо `addOrder` в Predators). ✓код.
11. **Видимость по ядру:** `zoneMgr:getZoneMap(pos):isActive()` вместо радиуса 15000. ✓код.
12. **Оценка силы из ядра:** `StateBroadcastData.apparentStrength` и `Blackboard.moraleIsBroken` для решения конкурента напасть, торговаться или отступить. ✓код.

## Где мы дублируем ваниль

- **KMM_Traces** (`build/KMM_Conductor/scripts/init/KMM_Traces.lua`): дорожная модель S.roads.tr (караваны, бродяги, курьеры «в пути» как числа) и материализация временных отрядов (`permanentsquad=false`, Traces:243-246) повторяют невыгруженные отряды движка + `UnloadedPlatoonJob` TRAVEL_TARGET + ванильные пакеты WANDERING_TRADER и SIG_WANDERING_TOWN_TO_TOWN. Разорённый караван (Traces:630-632, 654) — свой аналог боя невыгруженных отрядов.
- **KMM_Traces, BNT** (Traces:451-499, 600): свои охотники за головой игрока по опросу наград ≥5000 повторяют ванильных охотников (`HUNT_BOUNTIES`, `AI::findBounty`, `getPercievedBounty` с порогом узнавания).
- **KMM_Siege** (`.../KMM_Siege.lua`): своя осада 3–7 дней, штурм и исход, спавн осаждающих и защитников через `Traces.request` (Siege:211-213). Это повторяет фазы `CampaignInstance` (GATHERING/ASSAULTING/RETREATING/VICTORY), `victoryTriggers/lossTriggers` и `allyTriggers`.
- **KMM_Conductor** (`.../KMM_Conductor.lua`): абстрактные рейды и захваты вдали от игрока. Родная кампания запускается только у игрока (`CA.try`, Conductor:2338-2345), всё остальное — своя модель поверх `FactionWarMgr`.
- **KMM_Outlaws** (`.../KMM_Outlaws.lua`): свой список разыскиваемых, кочёвка по региону, рост тира, шанс гибели от охотников, замена павшего. Это повторяет ванильных NPC с наградой, охотников и респаун уникальных отрядов (`FactionUniqueSquadManager.respawnTimer`). Частично связано: награда идёт в ядро (Outlaws:510).
- **KMM_Nemesis** (`.../KMM_Nemesis.lua`): своя память об избитых и сбежавших и преследование игрока. Повторяет `CharacterMemory` отряда (`ActivePlatoon::getMemory`, Platoon.h:213; `Character::rememberCharacter`, Character.h:543-544) и постоянный отряд с целью. Сам учёт ударов через хук оправдан.
- **KMM_Predators** (`.../KMM_Predators.lua`): гнёзда засад с «жаром» дорог и патруль-зачистка через `addOrder` на лидера (Predators:56-62). Повторяет бродячие банды биомов (спавн `AreaSector` / `_spawnASquad`), пакет SIG_RAIDING_WEAK_VILLAGES, патрули `setupPatrolSettings` / UPJOB_PATROL_* и `addSquadJob`.
- **KMM_Herds** (`.../KMM_Herds.lua`): свои маршруты стад и хищники по следу. Повторяет биомные спавны животных и привлечение по запаху (`ZoneSmell` + `HUNTING_BLOODSMELL`).
- **KMM_Elite** (`build/KMM_Elite/scripts/init/kmm_elite.lua:148`): Lua-спавн уникальных отрядов фабрикой параллельно ванильному `FactionUniqueSquadManager::spawnNewUniqueSquad` (`Faction.diplomatMgr`).
- **KMM_Native faction_force** (`tools/cpp/kmm_native/src/kmm_native.cpp:449-480`): чтение `activePlatoons/unloadedPlatoons` по смещениям через SEH. В Lua есть `Faction:getActivePlatoons/getUnloadedPlatoons` + `Platoon.isDead/imprisoned/getCharacterCount()` (B:5673, B:10595). Это дубль, если итерация lektor<Platoon*> работает в игре (?, проверить одной строкой лога). Смещения из 1.0.65, а игра 1.0.68.
- **Радиус загрузки 15000** (Conductor:2186, CA.pick_town, Traces): своя эвристика вместо `ZoneMap:isActive()` / `PLATOON_LOAD_DISTANCE`.
