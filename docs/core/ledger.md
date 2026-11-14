# LEDGER — мост «наш код ↔ ядро» (2026-11-15)

Аудит только чтением, игра не запускалась. Что сверял:
- код: `build/**/scripts/**/*.lua` (без `_dev`), `tools/cpp/kmm_native/src/kmm_native.cpp` + `kenshi_decl.h`;
- биндинги: `3817000612/docs/` (B = BindingsReference, C = CallbacksReference, U = UnboundReference, Cn = ContainersReference, D = DialogueScriptingBridge), строки `KenshiLua.dll`;
- заголовки: `tools/ref/KenshiLib/Include/kenshi`;
- следы в игре: `logs/*.log` (debug, stock, tempo, rumors, outlaws, fates, ore, nemesis, chronicle, session_last), `Kenshi/RE_Kenshi_log.txt`, `3817000612/logs/KenshiLua.log` (сессия 14.11 16:35).

Статусы:
- **✓игра**: в логе игры есть след успешного прохода этого кода (в скобках маркер);
- **✓игра\***: подтверждение есть только в записях проекта (DECISIONS/NATIVE_MAP), в сохранившихся логах его нет;
- **✓код**: есть в биндинге или заголовке, сигнатура совпадает;
- **?**: нет следа в игре или семантика неизвестна;
- **✗**: опровергнуто (ошибка в логе или нет в биндинге).

Счёт: 106 разных методов движка, 544 места вызова. Ещё 9 событий, 12 глобалов, около 35 полей и 18 точек KenshiLib в плагине (2.4: +5 строк salvage). По методам 49 из 106 имеют след в игре; события, глобалы, поля и плагин считаются отдельно в своих таблицах.
Как считал: скрипт-экстрактор во временной папке, regex `:имя(` + подсчёт аргументов. Поля и события сверены вручную. Совпадение по имени не гарантирует правильный класс получателя; где это важно, класс указан.

## 1. Вызовы движка

### 1.1 Глобалы и точки входа
| вызов | где у нас | Lua/плагин | сигнатура ок | игра |
|---|---|---|---|---|
| `getGameWorld()` ×58 | все модули | Lua (README, Cn:225) | ✓ | ✓игра |
| `getPlayerInterface()` ×32 | Conductor, Nemesis, Traces, Tempo… | Lua, **в B нет**, строка в DLL есть | ✓ | ✓игра (Envoy Seal, HUNGER calibrated) |
| `KenshiLua.log(s)` ×19 | Native, Rumors, Conductor | Lua | ✓ | ✓игра (строки [KMM_*] в KenshiLua.log) |
| `Events.on(name, fn)` / `Events.off(id)` | все модули | Lua (C:7-16) | ✓ | ✓игра |
| `lektor.new("RootObject*")`, `:clear()` | kmm_stock:378 | Lua (Cn) | ✓ | ✓игра (restock shop) |
| `require("kmm_native")` / `package.loadlib("KMM_Native.dll","luaopen_kmm_native")` | KMM_Native:26,33 | плагин (CppExtensionAPI) | ✓ | ? (модуль зарегистрирован, вызова из Lua в логе нет) |
| энум-глобалы `TaskType`, `MessageLogColor`, `CharacterPerceptionTags_LongTerm`, `itemType` | Predators:55, Nemesis:263,1324, Stock:381 (число 0) | Lua (EnumsReference) | ✓ | ? |
| `ManagementScreen.getSingleton()` → `:addMessage(owner,msg,color)` | KMM_Nemesis:258-264 | Lua B:9197, B:9183 (static) | ✓ | ? (строк «chronicle:» в nemesis.log нет) |
| `currentDialogue` / `currentDialogueLine` | kmm_diplo_line.lua:4 | Lua (D:160-167) | ✓ | ✓игра (Diplo `decision … trade → counter_l`, 12.11) |
| `kenshi.checkLuaScriptReferences()` | kmm_diplo:521-523 (ищет в kenshi/KenshiLua/Kenshi) | D:205 описывает глобал `kenshi` | — | ✗ глобала `kenshi` нет («attempt to index global 'kenshi'», 12.11); строка в DLL есть, но под другим именем |
| `getSharedKing()`, `getGlobalConstants()`, `getInputHandler()`, `getOptions()` | не используем | строки в KenshiLua.dll, в B **нет** | ? | ? Возможный путь к `SharedKing.townList`, проверить в игре |

### 1.2 События (Events.on)
| вызов | где у нас | Lua/плагин | сигнатура ок | игра |
|---|---|---|---|---|
| `GameWorld::charsUpdate` ×15 | все модули (тик) | C:29 `(self)` | ✓ | ✓игра |
| `PlayerInterface::serialise` ×2 | Conductor:4528, Rumors:582 | C:99 `(self, gameData)` | ✓ `(_, gd)` | ✓игра (Rumors: told list сохранён и прочитан) |
| `PlayerInterface::loadFromSerialise` ×2 | Conductor:4529, Rumors:594 | C:100 | ✓ | ✓игра (`told list loaded from save: N via toTable`) |
| `Character::_NV_hitByMeleeAttack` | Conductor:4530 | C:38 `(self,cutDir,damage,attacker,attack,comboID)` | ✓ `on_hit(self,_,_,attacker)` | ✓игра (`brawl: X hit Y`) |
| `CharStats::xpFirstAid` | Nemesis:1343 | C:50 `(self,patient,time,medicStat)` | ✓ | регистрация ✓игра (`debt hooks registered`), срабатывание ? |
| `CharStats::xpLockpicking` | Nemesis:1344 | C:56 `(self,lockLevel,success)` | ✓ | то же |
| `Character::setChainedMode` | Nemesis:1345 | C:96 `(self,on,ownerHandle)` | ✓ | то же; срабатывает и на наш вызов (флаг GL.self_chain) |
| `ForgottenGUI::showTradeWindow` | Nemesis:1346 | C:343 `(self,a:hand,b:hand,type)` | ✓ `(gui,a,b)`, a/b → `:getCharacter()` | то же |
| `MyGUI::Gui::eventFrameStart` | KMM_Native:136 (только смоук) | C:75 `(time)` | ✓ | ? (смоук отменён) |

### 1.3 Методы объектов (автоматически, по убыванию числа вызовов)
Колонка «Lua/плагин» показывает первые классы B с этим именем.
| вызов | где у нас | Lua/плагин | сигнатура ок | игра |
|---|---|---|---|---|
| `:getPosition()` ×46 | KMM_Conductor:2187,2273,2451…; KMM_Gov:106; KMM_Nemesis:347,593,610… … | Lua: AI, AbstractMovementBase, AnimationClass… | ✓ | ✓игра (brawl near/trace at N) |
| `:getAllPlayerCharacters()` ×30 | KMM_Conductor:2185,2270,2442…; KMM_Nemesis:346,355,577…; KMM_Self:209 … | Lua: PlayerInterface | ✓ | ✓игра (Envoy Seal, HUNGER calibrated) |
| `:getData()` ×27 | KMM_Conductor:2196,2303,2533…; KMM_Gov:112; KMM_Nemesis:484,802,1103 … | Lua: CampaignInstance, DialogDataManager, Faction… | ✓ | ✓игра (trace column (gamedata:getData), brawl (Faction:getData)) |
| `:getGameData()` ×23 | KMM_Conductor:2617,2636; KMM_Nemesis:561,579,711…; KMM_Self:166 … | Lua: DialogLineData, PreviewBuilding, RootObjectBase… | ✓ | ✓игра (restock (предметы), Self) |
| `:getInventory()` ×23 | KMM_Conductor:2535,4242; KMM_RelicRace:147; KMM_Self:164 … | Lua: Building, Character, ContainerItem… | ✓ | ✓игра (restock shop) |
| `:isDead()` ×23 | KMM_Conductor:2483,4162,4263; KMM_Fates:375; KMM_Gov:109 … | Lua: Character, MedicalSystem, MedicalSystem::HealthPartStatus… | ✓ | ✓игра (Gov snapshot → flee N/N down) |
| `:getHandle()` ×21 | KMM_Conductor:2487,2514,2578…; KMM_Gov:128; KMM_Self:63,214,249 … | Lua: AI, AITaskSytem, AbstractMovementBase… | ✓ | ✓игра (stock key, null_hand) |
| `:getName()` ×19 | KMM_Conductor:4144,4427; KMM_Fates:372; KMM_Nemesis:355,689,732… … | Lua: ActivePlatoon, CampaignInstance, CharBody… | ✓ | ✓игра (Rumors speaker=) |
| `:getFaction()` ×16 | KMM_Conductor:2642,4146,4341…; KMM_Gov:112; KMM_Nemesis:484,802,1103 … | Lua: AI, CharBody, DoorStuff… | ✓ | ✓игра (brawl (наследуется от RootObjectBase)) |
| `:getSquadLeader()` ×16 | KMM_Fates:315,367; KMM_Nemesis:810,849,973…; KMM_Outlaws:269,518,562… … | Lua: ActivePlatoon, Character, Platoon | ✓ | ? |
| `:getFactionByStringID()` ×15 | KMM_Conductor:2170,2192,2192…; KMM_Outlaws:509; KMM_Siege:97 … | Lua: FactionManager | ✓ | ✓игра (trace column) |
| `:getTimeStamp_inGameHours()` ×12 | KMM_Conductor:212; KMM_Fates:64,70; KMM_Nemesis:339,698 … | Lua: GameWorld | ✓ | ✓игра ([day N] в логах) |
| `:setName()` ×12 | KMM_Fates:317,318; KMM_Nemesis:851,973,1029…; KMM_Outlaws:269,270,520… … | Lua: ActivePlatoon, Character, Faction… | ✓ | ? |
| `:getCurrentTownLocation()` ×11 | KMM_Gov:130; KMM_Nemesis:561,578,610…; KMM_Rumors:392,441 … | Lua: Blackboard, Building, Character… | ✓ | ✓игра (restock trader in <город>) |
| `:getCharacterUpdateList()` ×10 | KMM_Conductor:2631,4157; KMM_Gov:143; KMM_Self:83 … | Lua: GameWorld | ✓ | ✓игра (Gov snapshot) |
| `:addItem()` ×9 | KMM_Conductor:2536,4242; KMM_RelicRace:148; kmm_diplo:210 … | Lua: Inventory, InventorySection, ShopTraderInventorySection… | ✓ | ✓игра (Envoy Seal, restock +N) |
| `:getPlatoon()` ×9 | KMM_Gov:116; KMM_Nemesis:810; KMM_Self:54 … | Lua: AI, CharBody, Character… | ✓ | ✓игра (squad key в flee/fearless) |
| `:isPlayerCharacter()` ×9 | KMM_Conductor:4162,4335,4337; KMM_Nemesis:480,1100; kmm_diplo:190 … | Lua: Character | ✓ | ✓игра (brawl) |
| `:getAllItems()` ×8 | KMM_Self:164; KMM_Traces:1234,1252; kmm_stock:286,343,582… … | Lua: Inventory | ✓ | ✓игра (restock) |
| `:getTotalDays()` ×8 | KMM_Conductor:212; KMM_Fates:64; KMM_Nemesis:339 … | Lua: TimeOfDay | ✓ | ✓игра ([day N]) |
| `:isDown()` ×8 | KMM_Gov:126; KMM_Nemesis:480,641,733…; KMM_Self:61 … | Lua: Character, PortraitData | ✓ | ✓игра (flee N/N down) |
| `:createItem()` ×7 | KMM_Conductor:2534,4241; KMM_RelicRace:145; kmm_diplo:208 … | Lua: RootObjectFactory | ✓ — hand-аргумент nil принимается (в отличие от createRandomSquad) | ✓игра (Envoy Seal, restock +N) |
| `:getNearestTown()` ×7 | KMM_Conductor:2195,2195,2352…; KMM_Traces:288; kmm_elite:155 | Lua: FactionWarMgr, TownList | ✓ — FactionWarMgr(p) 1 арг. — ок; TownList 5 арг. недостижим | ? |
| `:isUnique()` ×6 | KMM_Conductor:2517,4162; KMM_Gov:127; KMM_Self:62 … | Lua: Character, Platoon | ✓ | ? |
| `:declareDead()` ×5 | KMM_Conductor:2486,4262; KMM_Traces:654,1503; kmm_tempo:315 | Lua: Character, Platoon | ✓ | ? |
| `:getMedical()` ×5 | KMM_Nemesis:679; kmm_tempo:107,142,372… | Lua: Character | ✓ | ✓игра (HUNGER probe) |
| `:getOwnerships()` ×5 | KMM_Traces:282,743,787; kmm_diplo:231; kmm_tempo:525 | Lua: Blackboard, Character, Platoon… | ✓ | ? |
| `:getPlatoonStringID()` ×5 | KMM_Gov:120; KMM_Self:57; KMM_Traces:64,353 … | Lua: Platoon | ✓ | ✓игра (squad key Mongrel_24) |
| `:getTimeStamp()` ×5 | KMM_Gov:176; KMM_Self:78,96; KMM_Traces:86,105 | Lua: GameWorld | ✓ | ✓игра (Gov) |
| `:createRandomSquad()` ×4 | KMM_Conductor:2577,4216; KMM_Traces:244; kmm_elite:148 | Lua: RootObjectFactory | ✓ — AItarget=hand обязателен (null_hand) | ✓игра (trace column/band/caravan) |
| `:equipItem()` ×4 | KMM_Conductor:2537,4243; KMM_RelicRace:149; KMM_Traces:1282 | Lua: Character, ContainerItem, Inventory… | ✓ — Inventory:equipItem(item) 1 арг.; у Character — 2 арг. | ? |
| `:getActivePlatoon()` ×4 | KMM_Fates:318; KMM_Nemesis:1030; KMM_Outlaws:270,521 | Lua: Hand, Platoon, PlatoonHandleContainerList | ✓ | ? |
| `:getBuilding()` ×4 | kmm_ore:225; kmm_stock:204; kmm_town:250,331 | Lua: Hand, HandleManager, physHit | ✓ | ✓игра (restock shop) |
| `:getItem()` ×4 | kmm_diplo:206,215; kmm_town:373,405 | Lua: Hand, HandleManager, Inventory… | ✓ | ? |
| `:getStats()` ×4 | kmm_tempo:101,120,137… | Lua: Character | ✓ | ✓игра (Tempo min_speed_mult) |
| `:getTotalHours()` ×4 | KMM_Fates:70; KMM_Nemesis:698; KMM_Outlaws:85 … | Lua: TimeOfDay | ✓ | ? |
| `:setRelation()` ×4 | KMM_Conductor:2427,2428,4188… | Lua: FactionRelations | ✓ | ? |
| `:getBlackboard()` ×3 | KMM_Self:194,285,289 | Lua: AI, Character, Platoon | ✓ | ✓игра (flee:) |
| `:getBody()` ×3 | kmm_ore:217; kmm_town:245,245 | Lua: AppearanceBase, Character | ✓ | ? |
| `:getIsTrader()` ×3 | KMM_Gov:124; KMM_Traces:68; kmm_stock:465 | Lua: ActivePlatoon | ✓ | ✓игра (restock trader) |
| `:getMoney()` ×3 | KMM_Traces:792; kmm_diplo:231; kmm_tempo:527 | Lua: Character, ContainerItem, Inventory… | ✓ | ? |
| `:isAnimal()` ×3 | KMM_Self:133; kmm_town:267,290 | Lua: Character, CharacterAnimal | ✓ | ✓игра (fearless (animal)) |
| `:isInCombatMode()` ×3 | KMM_Gov:129; KMM_Self:64; kmm_town:255 | Lua: Character | ✓ | ✓игра (flee (g.combat)) |
| `:isUnconcious()` ×3 | KMM_Gov:126; KMM_Self:61; KMM_Traces:70 | Lua: Character, MedicalSystem, Platoon… | ✓ | ✓игра (flee down) |
| `:removeItemAutoDestroy()` ×3 | kmm_diplo:217; kmm_stock:321,349 | Lua: Inventory | ✓ | ✓игра (npc bought food) |
| `:runAway()` ×3 | KMM_Self:194,285,289 | Lua: Blackboard | ✓ | ✓игра (flee:) |
| `:say()` ×3 | KMM_Nemesis:1091; KMM_Rumors:494,628 | Lua: Character, Dialogue, RootObject | ✓ — Character:say(s) | ✓игра (Rumors say=ok ×16) |
| `:showPlayerAMessage_withLog()` ×3 | kmm_diplo:295; KMM_Rumors:500,629 | Lua: GameWorld | ✓ | ? |
| `:toString()` ×3 | kmm_ore:211; kmm_stock:205; kmm_town:211 | Lua: AnimationEvent, AnimationGroundEvent, AnimationSFXEvent… | ✓ | ✓игра (hand-ключи) |
| `:calculateHungerMult()` ×2 | kmm_tempo:101,440 | Lua: CharStats | ✓ | ✓игра (HUNGER probe magic=) |
| `:clear()` ×2 | kmm_stock:380,648 | Lua: CharacterStatsWindow, DatapanelGUI, FactionsScreen… | ✓ | ✓игра (lektor BUF:clear) |
| `:declareWar()` ×2 | KMM_Conductor:2407,2407 | Lua: FactionRelations | ✓ | ? |
| `:getCurrentAction()` ×2 | kmm_ore:219; kmm_town:245 | Lua: CharBody | ✓ | ? |
| `:getFactionRelation()` ×2 | KMM_Conductor:4187,4189 | Lua: FactionRelations, SensoryData | ✓ | ? |
| `:getObjectsWithinSphere()` ×2 | kmm_stock:381,649 | Lua: GameWorld | ✓ — док. B:7053 без out-параметра (5 арг.) — реальный вызов 6 арг. | ✓игра (restock shop (6 арг., out-lektor первым)) |
| `:getRace()` ×2 | KMM_Self:134; KMM_Traces:1241 | Lua: AppearanceBase, Character, RootObject | ✓ | ✓игра (fearless (race:…)) |
| `:getTown()` ×2 | kmm_stock:216,221 | Lua: Building, Hand, HandleManager… | ✓ | ✓игра (restock shop in Mongrel) |
| `:hasFaction()` ×2 | kmm_stock:399,656 | Lua: RootObjectBase | ✓ | ✓игра (restock shop) |
| `:hasRoomForItem()` ×2 | kmm_stock:273; kmm_tempo:307 | Lua: Character, Inventory, InventorySection… | ✓ | ? |
| `:isAShop()` ×2 | kmm_stock:404,654 | Lua: Building | ✓ | ✓игра (restock shop) |
| `:isValid()` ×2 | kmm_ore:224; kmm_town:250 | Lua: GameData, Hand, InventoryGUI::InventoryTradeData… | ✓ | ? |
| `:key()` ×2 | kmm_ore:221; kmm_town:246 | Lua: CampaignData, TaskMatch, Tasker | ✓ | ? |
| `:removeItemDontDestroy_returnsItem()` ×2 | kmm_town:376,407 | Lua: Inventory | ✓ | ✓игра (Town cycle hauled=1) |
| `:setChainedMode()` ×2 | KMM_Conductor:2487,4255 | Lua: Character | ✓ — owner = hand; у нас owner = сам персонаж | ? |
| `:setNoLongerEnemies()` ×2 | KMM_Conductor:2408,2408 | Lua: FactionRelations | ✓ | ? |
| `:setNull()` ×2 | KMM_Traces:229; kmm_elite:136 | Lua: AABB2D, Hand, TimeOfDay | ✓ | ? |
| `:toTable()` ×2 | KMM_Conductor:4387; KMM_Rumors:599 | контейнер | ✓ — метод контейнера (ContainersReference), sdata=unknown в B | ✓игра (Rumors «loaded … via toTable» (sdata)) |
| `:triggerCampaign()` ×2 | KMM_Conductor:2198,2306 | Lua: FactionWarMgr | ✓ — перегрузка [2] (7 арг.) | ? |
| `:_getHighestBountyFaction()` ×1 | KMM_Traces:460 | Lua: BountyManager | ✓ | ✓игра (trace bounty_hunt) |
| `:addMessage()` ×1 | KMM_Nemesis:264 | Lua: ManagementScreen, SaveFileSystem | ✓ — ManagementScreen.getSingleton():addMessage | ? |
| `:addMoney()` ×1 | kmm_tempo:528 | Lua: Ownerships | ✓ | ? |
| `:addOrder()` ×1 | KMM_Predators:62 | Lua: Character, OrdersReceiver | ✓ — Character:addOrder(dest,t,subject,shift,clear,loc) | ? |
| `:attackTarget()` ×1 | KMM_Traces:1179 | Lua: Character | ✓ | ? |
| `:getActualBounty()` ×1 | KMM_Traces:465 | Lua: BountyManager | ✓ | ✓игра (trace bounty_hunt) |
| `:getCharacter()` ×1 | KMM_Nemesis:553 | Lua: AI, AnimationClass, AnimationClassBase… | ✓ | ? |
| `:getCurrentWeatherAffectStatus()` ×1 | KMM_Traces:1084 | Lua: Character | ✓ | ? |
| `:getCurrentWeatherAffectStrength()` ×1 | KMM_Traces:1084 | Lua: Character | ✓ | ? |
| `:getMovementSpeed()` ×1 | kmm_tempo:94 | Lua: Character, RootObjectBase | ✓ | ? |
| `:getMovementSpeedInjuryMultiplier()` ×1 | kmm_tempo:107 | Lua: MedicalSystem | ✓ | ? |
| `:getMovementSpeedOrders()` ×1 | kmm_tempo:95 | Lua: Character | ✓ | ? |
| `:getNumItems()` ×1 | kmm_stock:570 | Lua: Inventory, InventorySection | ✓ | ✓игра (npc bought) |
| `:getOriginalGameData()` ×1 | kmm_town:206 | Lua: Town | ✓ | ? |
| `:getProductionBuilding()` ×1 | kmm_ore:227 | Lua: Building, ProductionBuilding | ✓ | ? |
| `:getRelationData()` ×1 | KMM_Conductor:2402 | Lua: FactionRelations | ✓ | ? |
| `:getSpeaker()` ×1 | kmm_diplo:370 | Lua: Dialogue | ✓ — Dialogue:getSpeaker(TalkerEnum,line,bool) | ? |
| `:getStringID()` ×1 | kmm_diplo:430 | Lua: DialogLineData | ✓ | ✓игра (Diplo decision (мост диалога)) |
| `:getTotalBounty()` ×1 | KMM_Outlaws:513 | Lua: BountyManager | ✓ | ? |
| `:getTotalWeight()` ×1 | kmm_tempo:104 | Lua: Inventory | ✓ | ? |
| `:getValueSingle()` ×1 | KMM_Traces:1225 | Lua: Armour, BlueprintItem, InventoryItemBase… | ✓ | ? |
| `:has()` ×1 | KMM_Conductor:4394 | контейнер | ✓ — метод контейнера (sdata) | ? |
| `:isAContainer()` ×1 | kmm_stock:404 | Lua: Inventory | ✓ | ? |
| `:isATrader()` ×1 | kmm_town:242 | Lua: Character | ✓ | ? |
| `:isChained()` ×1 | KMM_Conductor:4257 | **нет** | ✗ — МЕТОДА НЕТ: поле Character.isChained / isChainedMode() | ✗ |
| `:isResident()` ×1 | kmm_town:243 | Lua: Character | ✓ | ? |
| `:isTown()` ×1 | kmm_town:206 | Lua: TargetInfo, Town, TownBase | ✓ | ? |
| `:lineOfSightCheck()` ×1 | KMM_Conductor:2463 | Lua: Character | ✓ | ? |
| `:pointOfNoReturn()` ×1 | kmm_tempo:316 | Lua: MedicalSystem | ✓ | ? |
| `:refreshInventory()` ×1 | kmm_stock:514 | Lua: ActivePlatoon | ✓ | ? |
| `:rememberCharacter()` ×1 | KMM_Nemesis:1327 | Lua: Character | ✓ — 2 перегрузки по типу энума — см. баги | ? |
| `:sayALine()` ×1 | KMM_Nemesis:1092 | Lua: Character | ✓ | ? |
| `:setAlarmState()` ×1 | KMM_Siege:115 | Lua: TownBase | ✓ | ? |
| `:setHomeTown()` ×1 | KMM_Traces:282 | Lua: Ownerships | ✓ | ? |
| `:size()` ×1 | KMM_Conductor:4393 | контейнер | ✓ — метод контейнера (sdata) | ? |
| `:tryAddItem()` ×1 | kmm_town:334 | Lua: Inventory | ✓ | ✓игра (Town cycle crafted=N) |
| `:unfairAddToBounty()` ×1 | KMM_Outlaws:510 | Lua: BountyManager | ✓ | ? |
| `:uniqueStateUpdate()` ×1 | KMM_Conductor:2488 | Lua: Character | ✓ | ? |

### 1.4 Поля движка (чтение/запись)
| вызов | где у нас | Lua/плагин | сигнатура ок | игра |
|---|---|---|---|---|
| `GameWorld.factionMgr` / `.gamedata` / `.theFactory` | Conductor:2170,2196,2534; Traces:237-245 | B (GameWorld) | ✓ | ✓игра (trace column) |
| `Faction.data` (через `f:getData() or f.data`) | Conductor:4404, Self:146 | B | ✓ | ✓игра (brawl, fearless faction) |
| `Faction.warMgr` → `getNearestTown`, `.myTowns` | Conductor:2195,2352; Siege:98; Traces:288; Elite:155 | B: FactionWarMgr, `myTowns` lektor<TownBase*> RW | ✓ | ? |
| `Faction.relations` → `setRelation/declareWar/getRelationData` | Conductor:2399-2427 | B:5884-5894 | ✓ | ✓игра\* (NATIVE_MAP: «проба Conductor:3903-3910»), в логах нет |
| `RelationData.alliance/peaceTreaty/war` (запись) | Conductor:2403 | B:5899 bool RW | ✓ | ? |
| `Faction.myLawEnforcementFaction` | Traces:476 | B Faction | ✓ | ? |
| `Character.crimes` (BountyManager) | Traces:458, Outlaws:510,513 | B Character | ✓ | ✓игра (чтение: `trace bounty_hunt`) |
| `Character.isOnScreen` | Conductor:2448 | B bool RW | ✓ | ? |
| `Character.medical` (`m.knockoutTimer`, `m.unconcious` — запись) | Self:278-280 | B: MedicalSystem RW; в заголовке **по значению** (Character.h:706) | ? | ? (см. баги) |
| `MedicalSystem.hunger/fed` (через `getMedical()`) | Tempo:437-559, Conductor:1330 | B:9382-83 RW | ✓ | ✓игра (`HUNGER probe: hunger=… fed=…`) |
| `CharStats.moveSpeed` RW | Tempo:121-137 | B CharStats number RW | ✓ | ✓игра (`min_speed_mult=0.88`) |
| `Platoon.speedOverride` RW (MoveSpeed) | Tempo:202-214 (с проверкой записи) | B Platoon | ✓ | ✓игра (`npc_set=…`) |
| `Platoon.priceMultWhenITrade` RW | Traces:768-775 | B:10612 | ✓ | ✓игра (код дошёл до TGM-пробы сразу после записи) |
| `Platoon.squadTemplate.stringID`, `Platoon.isDead`, `ActivePlatoon.me`, `.isPlayer` | Gov:118-125, Fates:378, Outlaws:609, Elite:122, Tempo:167 | B | ✓ | ✓игра для `ap.me` (Gov-снимок); остальное ? |
| `Ownerships._homeTown` (TownBase) | Traces:743,788 | B Ownerships RW | ✓ | ? (`TGM probe: no home town / error before read` ×2) |
| `Town.tradeGoodsMults` | Traces:747 | B: только у **Town** (и TradeCulture), у TownBase нет | ✗ получатель: в коде TownBase | ? |
| `ProductionBuilding._resourceMiningLevel` RW | kmm_ore:170-196 | B number RW | ✓ | ? (ore.log: `nodes in state=0` во всех 11 сессиях) |
| `InventoryItemBase.quantity/isEquipped` | Stock:287-348, Traces:1236-1257 | B | ✓ | ✓игра (restock) |
| `GameData.stringID/.name` | везде | B:6666 | ✓ | ✓игра |
| `GameData.sdata[key]` (запись/чтение), `sdata:toTable()` | Conductor:4385-4459, Rumors:587-599 | B:6672 тип `unknown`; методы контейнера (Cn) | ✓ | ✓игра (Rumors), у Conductor надёжность ? |
| `GameData.data_string` | (удалено, линтер запрещает) | нет поля | ✗ | ✗ (`attempt to index field 'data_string'`, 12.11) |
| `RaceData.robot`, `race.data.name` | Self:135-137 | B RaceData | ✓ | ✓игра (`fearless … (robot)`, `(race:…)`) |
| `Tasker.subject` (hand) | kmm_ore:223, kmm_town:249 | B Tasker/TaskRequest | ✓ | ? |
| `Dialogue.me` | kmm_diplo:368 | B Dialogue | ✓ | ✓игра (Diplo decision) |
| `CharStats.me` (в колбэке xpFirstAid) | Nemesis:1134+ | B:709 | ✓ | ? |

### 1.5 Плагин KMM_Native → KenshiLib (C++)
| вызов | где у нас | Lua/плагин | сигнатура ок | игра |
|---|---|---|---|---|
| `DebugLog/ErrorLog` | kmm_native.cpp:29-40 | Debug.h | ✓ (mangled в kenshi_decl.h) | ✓игра (строки `KMM_Native:` в RE_Kenshi_log) |
| `KenshiLib::GetKenshiVersion()` / `BinaryVersion` | cpp:764 | Kenshi.h | ✓ | ✓игра (`1.0.65 (expected 1.0.65)`) |
| `GetRealAddress` + `AddHook(WorldEventStateQuery::getFromData 0x9A7DC0, ::isTrue 0x9A6650)` | cpp:663-694 | WorldEventStateQuery.h:36,38 | ✓ (verify_headers.cpp) | ✓игра (`isTrue hook installed`) |
| `AddHook(_NV_getTooltipData1)` для InventoryItemBase/Sword/Crossbow (GetProcAddress по mangled-имени) | cpp:704-718 | Item.h:38,288… | ✓ | ✓игра (`tooltip compaction hooks: …=1`) |
| `KenshiLua::RegisterModule("kmm_native")`, `GetApi` | cpp:781-803 | KenshiLua.h (CppExtensionAPI) | ✓ | ✓игра (`Lua module kmm_native registered`) |
| `ou` + смещения: GameWorld.factionMgr 0x4A8, Faction.activePlatoons 0x208 / unloadedPlatoons 0x220, lektor count +8 / stuff +16, Platoon._characterCountCurrent 0xA0 / isDead 0x1F0 / imprisoned 0x1F1 | kenshi_decl.h:47-56, cpp:450-520 | GameWorld.h:101, Faction.h:152-153, Platoon.h:92,187,188, Globals.h:29 | ✓ (совпадают, есть static_assert в verify_headers) | ? (`faction_force` никто не вызывает) |
| `FactionManager::getFactionByStringID` (RVA 0x2E7570) | cpp:494 | Faction.h:184 | ✓ | ? |
| `SaveManager::getSingleton` / `load(const std::string&)` | cpp:562-563 (только смоук) | SaveManager.h:26,35 | ✓ | ? |
| `GameData::stringID` по смещению 0x58 | cpp:24 | GameData.h:92 | ✓ | ? (счётчик hits в лог не пишется) |
| Lua-экспорт `ws_set/ws_clear/ws_clear_all/ws_get/ws_hook_active/ws_stats/faction_force/version/smoke_load` | cpp:571-582 ↔ KMM_Native.lua:59-117; вызывают Conductor:3843,3931, Elite:229-245 | плагин | ✓ (string, bool) | ? |
| `KMM_Native.unique_set/unique_get` | KMM_Native.lua:92-106 | **нет в g_funcs** | ✗ | всегда false/nil (сейчас не вызываются) |
| `KMM_Native.orderSquad` | KMM_Native.lua:108 | заглушка | — | всегда false |
| 2.4 `AddHook(ContextMenu::showContextMenu 0x7A5960)` + `AddHook(GameWorld::_NV_mainLoop_GPUSensitiveStuff 0x7877A0)`, цель по mangled-имени из KenshiLib.dll (GetProcAddress) | salvage.cpp:697-730 | PlayerInterface.h:40, GameWorld.h:196; Functions.cpp:84 (multihook, id на вызов) | ✓ (сборка, static_assert смещений) | ? (тот же приём у HarvestOrgans ✓игра; mainLoop делят 5 плагинов в RE_Kenshi_log) |
| 2.4 `ContextMenuGUI.optionsList 0xF8 / optionCoords 0x100 / buttonCoords 0x110`, `getMainWidget`, MyGUI `createWidget<PanelEmpty/Kenshi_Button1>`, userData-маркер 0x4B4D5301/02 | salvage.cpp:539-570 | gui/ContextMenu.h:20-29 | ✓ (static_assert) | ? (приём HarvestOrgans ✓игра) |
| 2.4 `Character::isDead/isUnconcious/isAnimal/myRace(0x2E0)→RaceData::robot(0x7C)/data(0x40)`, `getFaction`, `PlayerInterface::getFaction/selectedCharacter(0xF0)` | salvage.cpp:387-414 | Character.h:199,465,561,614; RaceData.h:31,48; PlayerInterface.h:111,190 | ✓ (static_assert) | ? |
| 2.4 `PlayerInterface::newPlayerTaskSelectedCharacters(KILL_CAGE_OCCUPANT, hand, NULL, Vector3::ZERO, false)` | salvage.cpp:416 | PlayerInterface.h:159, Enums.h:413 | ✓ | ? для роботов/животных (для людей ✓игра у HarvestOrgans `ordered KILL_CAGE_OCCUPANT`); запасной `task` в salvage.json: MELEE_ATTACK_ANIMAL (Enums.h:506) |
| 2.4 `GameDataManager::getData(sid)` + `type==ITEM`, `RootObjectFactory::createItem(gd, hand(), NULL, NULL, 0, NULL)`, `Inventory::addItem(it,1,true,false)`, `getPosition`, `GameWorld::paused(0x8B9)` | salvage.cpp:361,426-465 | GameDataManager.h:27, RootObjectFactory.h:39, Inventory.h:149, GameWorld.h:242 | ✓ | ? (createItem/addItem ✓игра у HarvestOrgans) |

## 2. Сводный реестр фактов

Сведено из ENGINE_MAP, ENGINE_MANUAL, NATIVE_MAP, ENGINE_FINDINGS_20261114, LEVERS, MECHANICS, MECHANICS_AUDIT, NEEDS_REKENSHI и KENSHILUA_API. Дубли объединены. Если статус изменён, это сказано в скобках. Номера B/C — строки документации.

### 2.1 Среда и Lua-слой
1. Скрипты `<мод>/scripts/init/*.lua` грузятся при старте, лог пишется в `3817000612/logs/KenshiLua.log`. **✓игра**
2. Песочница своя у каждого скрипта, общие данные через `_G`, `require` работает в пределах `scripts/` мода (D:124-156). **✓игра** (kmm_ws_lut, *_data)
3. `loadstring` ограничен, поэтому состояние читаем своим парсером. **✓игра\*** (DECISIONS 13.11)
4. `io.open` пишет файлы (хроника, debug.log). **✓игра** (KENSHILUA_API «не проверено» устарело)
5. Контейнеры движка — это userdata. `next()` на них падает: **✗** (Tempo `next … got userdata`, 13.11). `pairs`/`ipairs`/`#`/`toTable` работают: **✓игра**. Контейнер нельзя создавать в каждом тике (Cn).
6. Lua-таблица `{x,y,z}` принимается как Vector3: **✓игра** для createRandomSquad. Для `addOrder`/`amputate` — ? (Predators под крэш-сторожем, следа нет).
7. `hand` нельзя заменять на nil в createRandomSquad: **✗ nil** («KenshiLua.hand expected», 12.11). Пустой hand делаем `setNull()` на копии из `getCarryingObject`/`getMySlaveOwner`: **✓игра**. В `createItem` hand=nil проходит: **✓игра**.
8. Методы предка доступны у потомка (например, `RootObjectBase:getFaction` у Character): **✓игра** (brawl). Значит, TownBase:getGameData тоже должен работать: **✓код**.
9. В B у методов с выходным параметром по ссылке этот параметр пропущен: `getObjectsWithinSphere` в B:7053 описан с 5 аргументами, реальный вызов `(out, pos, r, type, max, skip)` с 6. **✓игра**
10. У `GameData.sdata` в B тип `unknown`. На деле это строковая карта: `sdata[k]=s`, `sdata[k]`, `:toTable()`. **✓игра** (Rumors). Чтение состояния Conductor однажды вернуло пустоту (13.11), поэтому файл-резерв `state/*.kmmstate` оставлен. Надёжность для Conductor — ?.
11. Поля `GameData.data_string` нет. **✗** (из-за этого 12.11 мир не сохранялся)
12. Глобала `kenshi` (D:205) в игре нет. **✗** Сам мост «run lua script» работает: **✓игра**.
13. Глобалы C++ `shou/con/gui/options` в документации Lua не описаны. В KenshiLua.dll есть строки `getSharedKing/getGlobalConstants/getOptions/getInputHandler` — **?** (вывод ENGINE_MANUAL/NATIVE_MAP «SharedKing из Lua недостижим» понижен до ?).
14. `Events.on`: notification-колбэк, `return false` гасит только Lua-обработчики. Override-колбэк: значение не-nil подменяет результат движка (C:5-22). Указатели из колбэка между тиками не хранить, хранить hand/sid. **✓код**
15. `_NV_*` — хуки на невиртуальное тело метода. Подтверждён только `_NV_hitByMeleeAttack`. **✓игра** (остальные ?)

### 2.2 Мир, время, фракции, города
16. Время: `getGameWorld():getTimeStamp_inGameHours():getTotalDays()` **✓игра**; `getTotalHours()` **✓код** (у Outlaws есть запасной путь через дни, поэтому след не доказывает).
17. `gw.factionMgr:getFactionByStringID(sid)` **✓игра**; `getAllFactions/getFactionByName` **✓код**.
18. У Faction нет `getGameData`: **✗** (лог 12.11). Правильно `f:getData()` или `f.data`: **✓игра**.
19. `gw.gamedata:getData(sid, itemType)` **✓игра**. `createNewData/addNewData` **✓код**, ?.
20. `theFactory:createRandomSquad` (15 аргументов: …, AItarget hand, targetTown, sizeMult, squadType, isJustARefresh) **✓игра**. При nil в №12 и №15 — **✗** (12.11).
21. `createRandomUnloadedSquad`, `Faction:createNewEmptyUnloadedPlatoon` **✓код**, не вызывали — ?.
22. Города фракции: `FactionWarMgr.myTowns`, `getNearestTown(pos)` **✓код**, ? в игре. `TownList` (getTownBySID) из Lua недостижим — ? (п.13).
23. Смена владельца: `TownBase:setFaction(faction, activePlatoon)` **✓код**, ?. Владелец пишется в сейв навсегда. Сейчас владение ведёт модель + `KMM_Native.ws_set`.
24. Кампании: `FactionWarMgr:triggerCampaign` [2] (7 аргументов), `itemType.FACTION_CAMPAIGN=93`, Phase/WarCampaignEnum **✓код**. Вызов CA.try под probe — следа в игре нет, ?. Записи NATIVE_MAP/MECHANICS_AUDIT «S+игра частично» не подтверждены логом.
25. Отношения: `relations:setRelation(f, v)` **✓игра\***; `getRelationData` → `alliance/peaceTreaty/war/coexists` RW, `declareWar`, `setNoLongerEnemies` **✓код**, ?. Каскад `declareWar` на союзников — ?.
26. `FactionRelations::affectRelations` и `BountyManager::notifyCrimeWitnessed` — лучшие точки «что игрок сделал фракции» (C:64-65). Не используем. **✓код**
27. Награды: чтение `Character.crimes:_getHighestBountyFaction()/getActualBounty(f)` **✓игра**. Запись `unfairAddToBounty(faction, amount)` **✓код**, ? (в session_report «родная награда на главаре: 0»).
28. Тревога города: `TownBase:setAlarmState/alarmState` **✓код**, ? (Siege:115).
29. `Town.tradeGoodsMults` есть только у `Town`, у `TownBase` нет. `Ownerships._homeTown` возвращает TownBase, сначала нужен `:isTown()`. **✓код**, в игре ✗ (проба TGM 2 раза без данных).

### 2.3 Отряды, приказы, ИИ
30. `Platoon:getBlackboard():runAway()` **✓игра**.
31. Приказы: `Character:addOrder(dest, TaskType, subject, shift, clear, loc)` и `OrdersReceiver:addOrder(TaskType, hand, loc, clearOld, shift)` (порядок shift/clear обратный) **✓код**. Наш Predators — ?. `STAND_STILL` в TaskType нет: **✗** (NATIVE_MAP п.4). Методы `getFirstOrder/clearOrders` принадлежат OrdersReceiver, а не Ownerships: **✗** старой записи.
32. `Ownerships:setHomeTown(TownBase, SquadType)` **✓код**, ?; `Ownerships:addMoney` **✓игра\*** (Tempo:528).
33. Создать Tasker/AIPackage из Lua нельзя (конструкторов нет). **✓код**
34. Выгруженные отряды ведёт движок по UnloadedPlatoonJob. Реестра состояния уникальных NPC (жив/плен) нет ни в Lua, ни в заголовках. **✓код** (отрицательный факт)
35. `ActivePlatoon:getIsTrader()` **✓игра**; `refreshInventory(bool)`, `Platoon.traderInventoryRefreshTime` **✓код**, ?.
36. `Platoon.speedOverride` и `CharStats.moveSpeed` пишутся и читаются обратно. **✓игра**
37. `Platoon.priceMultWhenITrade` RW **✓игра**.

### 2.4 Персонажи, медицина, инвентарь, речь
38. `isDead/isDown/isUnconcious/isInCombatMode/isPlayerCharacter/isAnimal/getRace` **✓игра**. `isUnique`, `uniqueStateUpdate` **✓код**, ?.
39. `declareDead()`, `setChainedMode(on, ownerHand)` **✓код**, ?. Наш вызов setChainedMode сам вызывает колбэк `Character::setChainedMode` **✓код** (DECISIONS). Метода `isChained()` **нет**, есть поле `isChained` и метод `isChainedMode()`.
40. Голод: `getMedical().hunger/fed` RW **✓игра**. Шкала примерно до 300 (`full=300`). Направление в 3 калибровках падает, в 1 растёт — **?**, калибровка нужна каждую сессию.
41. `Character.medical` хранится по значению (Character.h:706), `getMedical()` возвращает указатель (Character.h:528). Для записи надёжнее `getMedical()`. **✓код**
42. Инвентарь: `createItem(gd, nil, nil, nil, -1, nil)` + `addItem(item, 1, false, true)`, `getAllItems()` (возвращает lektor), `removeItemAutoDestroy`, `removeItemDontDestroy_returnsItem`, `tryAddItem`, `getNumItems` **✓игра**. `equipItem` у Inventory — 1 аргумент, у Character — 2 (`section, item`). **✓код**
43. `getObjectsWithinSphere` возвращает RootObject. У RootObject нет `isAShop`: **✗** (12.11). Через `getHandle():getBuilding()` — **✓игра**.
44. Речь: `Character:say(s)` без ошибки **✓игра**, виден ли пузырь — ?. Запасные `sayALine(line, force)`, `say_WithARepeatLimiter`, `sendDialogEvent(target, EV_*)` **✓код**.
45. Память ванили: `rememberCharacter(who, tag)` имеет 2 перегрузки (ShortTerm/LongTerm), выбор при целом числе — **?** (см. баги). `getCharacterMemoryTag`, `ILoveThisGuy…/IHateThisGuy…` **✓код**.
46. Рабство: `isSlave()` возвращает SlaveStateEnum. `setSlaveState` и `isSlaveOf` принадлежат `StateBroadcastData` (`ch.stateBroadcast`), а не Character: **✗** записи NATIVE_MAP п.9 (исправлено в её §5).
47. Конечности: `MedicalSystem:amputate(RobotLimbs::Limb, bool, Vector3)` **✓код**, ?. Путь через данные: `CHARACTER."starting health"` → LOCATIONAL_DAMAGE val0 < −100 = ампутация **✓код** (fcs.def; используют Veterans).
48. Погода: `Character:getCurrentWeatherAffectStatus/Strength` **✓код**, ? (Traces). Путь `WeatherSystem.getInstance().ActiveRegionWeather.weatherInstance.weather.affectCharactersType` **✓код**, ?. Писать погоду нельзя.
49. Журнал игрока: `ManagementScreen.getSingleton():addMessage(owner, msg, MessageLogColor)` **✓код**, ?. `showPlayerAMessage_withLog(msg, queued)` **✓код**, ?. `ForgottenGUI:messageBox` не привязан (U:340). **✗** из Lua

### 2.5 Диалог
50. Мост FCS «run lua script» (тип 322) даёт глобалы `currentDialogue`/`currentDialogueLine`, `line:getStringID()`, `dlg.me` **✓игра**. `dlg:getSpeaker(TalkerEnum, line, bool)` **✓код**, ?.
51. Override `Dialogue::_checkCondition/startConversation/sendEvent` и `DialogueWindow:setNPCText` — путь к динамическим условиям и тексту **✓код**. Кнопки ответов Lua не строит (C:3831). **✗**

### 2.6 Плагин (C++)
52. `GetRealAddress/AddHook` принимают только адреса внутри KenshiLib.dll. Без `dllimport` адрес указывает на локальный thunk, отсюда assert и краш. **✓игра\*** (смоук 12.11)
53. Хуки isTrue/getFromData и tooltip ставятся, проверка версии 1.0.65 проходит. **✓игра**
54. Смещения полей для `faction_force` сверены с заголовками и static_assert. Но `faction_force` никто не вызывает (REV2 п.3 «реализован» — функция-сирота). ?
55. Сделать «состояние уника без загрузки зоны» нельзя, пока не разобран isTrue 0x9A6650. ?
56. Двойной хук одной цели разрешён: `KenshiLib::AddHook` = MinHook multihook (m417z), каждому вызову свой id (Functions.cpp:84-99) **✓код**; в игре `_NV_mainLoop_GPUSensitiveStuff` хукают KillCounter, HarvestOrgans, QueenBirth, 2× HiveBirthing, `_NV_hitByMeleeAttack` — KillCounter и HarvestOrgans **✓игра** (RE_Kenshi_log, без ошибок). Каждый детур сначала зовёт оригинал → пункты меню разных плагинов встают друг под другом.
57. Классы в заголовках KenshiLib не `dllimport`; `&Class::method` без LTCG даёт локальный thunk → адрес для хука берём `GetProcAddress(KenshiLib.dll, mangled)` (как tooltip). **✓код**

### 2.7 Устаревшее и опровергнутое в старых документах
- KENSHILUA_API: «Дирижёр v0 на KenshiLua не собирается» — устарело, дирижёр сделан моделью + материализацией. «Писать файл не проверено» — ✓игра. «Глобального перечня городов нет» — частично: есть `FactionWarMgr.myTowns`.
- ENGINE_MAP §6: «используем 4 колбэка» — сейчас 9. §4: «sdata в игре ненадёжно» — для Rumors ✓игра, для Conductor ?.
- ENGINE_MANUAL §0: «SharedKing недостижим» → ? (п.13). «`gw.zoneMgr` ✓ чтение», «Погода S», «Сейв S» — следов в игре нет, ?.
- NATIVE_MAP п.10: «setName S+игра (Ore v2)» — в ore.log узлов 0 за 11 сессий, понижено до ?. П.4, п.9, STAND_STILL — ✗ (см. 31, 46).
- NATIVE_MAP п.5, MECHANICS_AUDIT: «setRelation S+игра» — ✓игра\*, в сохранившихся логах нет.
- ENGINE_FINDINGS «ошибок в сигнатурах не найдено» — верно по числу аргументов, но перегрузка rememberCharacter не решена (баг №1).
- MECHANICS «Голод не проверен в игре» — устарело, ✓игра (tempo.log 13-14.11). «Фракции/кампании/награды в игре не проверено» — по-прежнему ?.
- MECHANICS_AUDIT «Traces цены → перейти на Town.tradeGoodsMults» — в текущем виде недостижимо (п.29).
- LEVERS и NEEDS_REKENSHI — данные, конфиги и список модов. Это не вызовы ядра, в реестр не вошли. Из NEEDS_REKENSHI REV2 актуально: setTownOwner, setFactionActive, plunderPlayerBase, applyAbstractLosses не реализованы; orderSquad — заглушка.

## 3. Вероятные тихие баги
Все вызовы под pcall/probe_call, поэтому ошибка не видна: модуль молча выключается или получает nil.

1. **`rememberCharacter` выбирает не ту перегрузку.** KMM_Nemesis.lua:1327 (тег берётся в :1324). B:3449-3450: две перегрузки отличаются только типом энума, а мы передаём целое `CharacterPerceptionTags_LongTerm[...]`. Если биндинг возьмёт [1] ShortTerm, LT_DEFEATED_MY_SQUAD_ONCE=7 запишется как ST_CRIMINAL, а LT_FREED_ME=3 — как ST_TEMPORARY_ALLY. Ошибки не будет, память получится неверной. Проверка: после вызова прочитать `getCharacterMemoryTag(pc, tag)`.
2. **Метода `isChained()` нет.** KMM_Conductor.lua:4257. Есть поле `isChained` (B:3105) и метод `isChainedMode()` (B:3392). Проба 4a всегда пишет `isChained false=…`.
3. **TGM-проба читает не тот класс.** KMM_Traces.lua:743-747. `_homeTown` имеет тип TownBase, а `tradeGoodsMults` есть только у Town. К тому же проба одна на сессию (`TGM.done`) и берёт первого торговца. Лог дважды: `no home town / error before read`. Нужно `t:isTown()`, и пробу повторять до первого города.
4. **Отряд со зверем считается бесстрашным целиком.** KMM_Self.lua:128-153. Кэш `FEAR[key]` ставится по одному персонажу. В debug.log: `The Holy Nation_N (animal)`, `Bounty Hunters_N (animal)`, `Free Traders (animal)` — вьючное животное делает людей отряда «не бегущими».
5. **Ore ни разу не увидел работу.** kmm_ore.lua:216-229. Цепочка `getBody():getCurrentAction():key()/subject → getBuilding():getProductionBuilding()`; ore.log: `nodes in state=0` во всех 11 сессиях. Подозреваю, что NPC в городах работают как TaskType 221 PRETEND_TO_OPERATE_MACHINERY, а не 87/152 (ore_config.lua:27), или что `key()` не число. Это догадка.
6. **Запись в копию MedicalSystem.** KMM_Self.lua:278-280. `ch.medical` — член по значению (Character.h:706), поэтому `knockoutTimer/unconcious` могут записаться в копию. Нужен `ch:getMedical()` (указатель). Срабатывает только при `surrender_mode="knockout"`.
7. **Пленник прикован к самому себе.** KMM_Conductor.lua:2487 и :4255: `setChainedMode(true, ch:getHandle())`, хозяином становится сам пленник. Поведение движка неизвестно (побег, «чей раб»). Плюс вызов запускает наш же колбэк Nemesis; флаг GL.self_chain это прикрывает.
8. **Нативные записи без следа в игре.** KMM_Outlaws.lua:510 `crimes:unfairAddToBounty` (session_report: «родная награда на главаре: 0»), KMM_Nemesis.lua:258-264 `ManagementScreen.getSingleton():addMessage` (строк `chronicle:` нет), KMM_Conductor.lua:2198/2306 `triggerCampaign`. Все три под probe/pcall: если они молча падают, видимый мир не получает своих эффектов.

Мелкое:
- KMM_Native.lua:92-106 `unique_set/unique_get` нет в DLL (g_funcs, cpp:571), всегда false/nil.
- `faction_force` без вызывающих.
- kmm_diplo.lua:521 ищет `checkLuaScriptReferences` не там.
- KMM_Nemesis.lua:561,579,711 `t:getGameData() or t.data`: `or` не спасает, если метода нет; по п.8 метод должен быть.
