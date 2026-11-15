# ЭКОНОМИКА И ИГРОК — справочник ядра (Kenshi 1.0.65)

Домен: предметы, цены, торговцы, деньги, наём, рабство в торговле, исследования, диалоги, каналы сообщений, карта, сохранение.
Цель: чтобы игрок чувствовал живой мир через **ванильные** окна (торговля, диалог, журнал, карта), а не через надстройки.

Обозначения: `kenshi/X.h:N` = `tools/ref/KenshiLib/Include/kenshi/X.h`, строка N; `B:N` = BindingsReference.md, строка N; `C:Имя` = событие из CallbacksReference.md (Notify = наблюдатель, Override = перехват, вернул не-nil → значение подменено).
Статусы: ✓игра (видели в логе игры) · ✓код (есть в заголовке/биндинге) · ? (догадка).
Источники проверены 2026-11-15: заголовки, BindingsReference/CallbacksReference/EnumsReference/DialogueScriptingBridge/InGameGUI (KenshiLua 3817000612), build/KMM_*, tools/streams/economy.py, diplo.py, logs/*.log.

## Сводная таблица

| Механика | Ядро (главная точка) | Lua | Перехват | Наше | Статус |
|---|---|---|---|---|---|
| Базовая цена предмета | `InventoryItemBase::getValueSingle(isPlayer)` kenshi/Item.h:44 | да B:8303 | **Override** C:InventoryItemBase::getValueSingle | Traces читает | ✓код |
| Наценка торговца/культуры | `Town::getLocalTradePriceMult` / `getFactionTradeCultureMult` kenshi/Town.h:376-377, `Platoon.priceMultWhenITrade` kenshi/Platoon.h:109 | да B:13487-88, B:10612 RW | нет | Traces пишет priceMultWhenITrade | ✓код (эффект в окне ?) |
| Таблицы цен по товарам | `Town.tradeGoodsMults` kenshi/Town.h:475, `TradeCulture.tradeGoodsMults` kenshi/TradeCulture.h:19 | да (RW map) | нет | проба TGM в Traces | ? (чтение из Lua не подтверждено) |
| Запрещённое/краденое | `TradeCulture::isItemIllegal` kenshi/TradeCulture.h:21, `Platoon::iBuyStolenGoods/iBuyIllegalGoods` kenshi/Platoon.h:112-113, `Item::isStolen` kenshi/Item.h:85 | да | **Override** iBuyStolenGoods / iBuyIllegalGoods | нет (economy.py: fences в данных) | ✓код |
| Ассортимент и пополнение | `ActivePlatoon::refreshInventory(firstTime)` kenshi/Platoon.h:232, `Platoon.traderInventoryRefreshTime` :190, `ShopTrader` kenshi/ShopTrader.h | да B:659-660, B:10632 | Override C:ShopTrader::_CONSTRUCTOR | KMM_Stock (restock), economy.py vendor_turnover | ✓игра (stock.log «TRADE restock trader in Mongrel») |
| Деньги | `Ownerships` money/getMoney/addMoney (B:10326-10349), `Inventory::getMoney/takeMoney` kenshi/Inventory.h:212-213 | да | Notify C:Character::_NV_takeMoney | Tempo money_min, Diplo читает | ✓код |
| Окно торговли | `ForgottenGUI::showTradeWindow(a,b,TradeWindowType)` kenshi/gui/ForgottenGUI.h:96 | да B:6529 | Notify C:ForgottenGUI::_showTradeWindow, showTraderInventory; **Override** C:Inventory::buyItem | Nemesis: торговец говорит о рынке | ✓код |
| Наём в барах | `Town::spawnTheBarFlies` kenshi/Town.h:369; диалоги CHOOSE_RECRUITING / DA_JOIN_SQUAD_* kenshi/Dialogue.h:36,51,78 | да B:13483 | Notify C:PlayerInterface::recruit | нет (Veterans: вербовка из Lua небезопасна) | ✓код |
| Наёмники по контракту | `Blackboard::setContractJob` kenshi/AI/Blackboard.h:75, `Contract_HiredAlly` kenshi/AI/Contract.h:63 | да B:2278 | — | нет | ✓код |
| Рынок рабов/пленных | DA CHOOSE_SLAVES_SELLING/BUYING, CHOOSE_PRISONER_BAIL, DA_PLAYER_SELL_PRISONERS kenshi/Dialogue.h:74-83; `CharacterTradingWindow` kenshi/gui/CharacterTradingWindow.h:9 | частично | Notify C:Character::changeSlaveOwner | нет | ✓код (цена раба ?) |
| Исследования | `Research` kenshi/Research.h:25, `PlayerInterface.technology` kenshi/PlayerInterface.h:185 | да B:10712 | Notify ManagementScreen::research* | tech.py (дерево Relics, данные) | ✓код |
| Диалог: условия | `Dialogue::_checkCondition` kenshi/Dialogue.h:369, `DialogConditionEnum` (80 условий) | да | **Override** C:Dialogue::_checkCondition | нет | ✓код |
| Диалог: события/запуск | `Dialogue::sendEvent` :351, `runCustomDialog` :353, `addConversation` :346, `makeAnnouncement` :359 | да B:5405-5417 | **Override** sendEvent / startConversation / startPlayerConversation | нет | ✓код |
| Диалог: Lua на реплике | «run lua script» → `Dialogue::_doActions` kenshi/Dialogue.h:404 (DialogueScriptBridge) | да | Notify C:Dialogue::_doActions | KMM_Diplo | ✓игра (лог KMM_Diplo: строки DialogueScriptBridge) |
| Реплика-пузырь | `Character::say` kenshi/Character.h:361, `sayALine` :486 | да B:3243, B:3322 | Notify C:Character::_NV_say | Rumors, Nemesis | ✓игра (rumors.log say=ok ×16) |
| Память NPC об игроке | `Character::rememberCharacter(who, LT_*)` kenshi/Character.h:544, `getCharacterMemoryTag` :545 | да B:3450, B:3466 | — | Nemesis (probe_call) | ✓код |
| Сообщение вверху экрана / журнал | `GameWorld::showPlayerAMessage(_withLog)` kenshi/GameWorld.h:148-149 | да B:7090 | — | Diplo, Rumors | ✓код |
| Вкладка сообщений (лог) | `ManagementScreen::addMessage(owner,msg,MessageLogColor)` kenshi/gui/ManagementScreen.h:110, `getSingleton` :87 | да B:9183 | Notify C:ManagementScreen::addMessage | Nemesis-хроника | ✓код |
| Плавающая метка | `ForgottenGUI::createScreenLabel` kenshi/gui/ForgottenGUI.h:206, `ScreenLabel::setTracking` kenshi/gui/ScreenLabel.h | да B:6513 | Notify | нет | ✓код (экземпляр ForgottenGUI из Lua ?) |
| Карта: города | `TownBase::setDiscovered/setRecentlyDiscovered/setExplored` kenshi/Town.h:224-234 | да B:13640-45 | — | нет | ✓код |
| Карта: отряды/маркер | `ManagementScreen::addSquadToMap(Platoon)` kenshi/gui/ManagementScreen.h:108, `MapScreen::setMovementMarker` kenshi/gui/MapScreen.h:67 | да B:9176 | Notify MapScreen::* | нет | ✓код |
| Сохранение своих данных | Notify C:PlayerInterface::serialise / loadFromSerialise (kenshi/PlayerInterface.h:180-181) + поле `GameData.sdata` (B:6672) | да | Notify | Conductor, Rumors (+ файлы .kmmstate) | ✓код |

---

## 1. Предметы и цены

### Базовая цена предмета
Ваниль: цена = поле `value` из FCS × качество/материал/производитель (`manufacturerData`, `materialData`, `quality` kenshi/Item.h:65-74), у оружия и брони свои формулы. `isPlayer` разделяет «цена для игрока» и «для NPC». Точная формула закрыта (?).
· Точки ядра: `InventoryItemBase::getValueSingle(bool isPlayer)` kenshi/Item.h:44 (virtual; переопределения `Weapon` kenshi/Gear.h:47, `Armour` kenshi/Gear.h:166, `BlueprintItem` kenshi/Item.h:370, `MapItem` :397, `MoneyItem` :427), `getValueAll` :46, `getAvgPrice` :43, `getMaxAffordableNum(cash, isPlayer)` :48, `merchantPriceMod()` :92 (protected), `getTooltipTradeValue` :91.
· Lua: да — `getValueSingle` B:8303, `getAvgPrice` B:8302, `merchantPriceMod` B:8315. **Override** `C:InventoryItemBase::getValueSingle(self, isPlayer, defaultVal) -> integer` (хук на `Inventory::getBaseValueSingle`).
· Наше: KMM_Traces читает `getValueSingle(false)` (KMM_Traces.lua:1225); economy.py правит `value` в данных (выбросы цен, книги).
· Рычаги: (1) Override getValueSingle — единственный способ сделать цену **этого предмета в этом городе сейчас** видимой прямо в окне торговли и подсказке: дефицит склада KMM_Stock, реликт, найденный соперником, трофей с известного Nemesis. Цена — вызов очень частый (каждая ячейка окна): только кэш-таблица по `GameData`, без обхода мира. (2) `isPlayer=true` ветка — наценка «чужаку» по отношениям фракции торговца (ваниль отношения в цену не включает — ?).

### Наценка города, культуры и торговца
Ваниль: у фракции есть `TradeCulture` (kenshi/Faction.h:134) — запреты, «счастливые» здания, множители по товарам; у города своя копия `Town.tradeCulture` kenshi/Town.h:474 и `tradeGoodsMults` :475; у отряда-торговца общий множитель `priceMultWhenITrade` kenshi/Platoon.h:109.
· Точки ядра: `Town::getLocalTradePriceMult(GameData*)` kenshi/Town.h:376, `Town::getFactionTradeCultureMult(GameData*)` :377, `TradeCulture::getTradePriceMultiplier/hasTradePriceMultiplier` kenshi/TradeCulture.h:22-23, `TradeCulture::setupTradeCulture(GameData*)` :11.
· Lua: да — B:13487-13488, `tradeCulture` RW B:13452 (Town) / B:5692 (Faction), `Platoon.priceMultWhenITrade` RW B:10612, `TradeCulture.tradeGoodsMults` RW (map GameData→float).
· Наше: KMM_Traces `prices()` ставит `priceMultWhenITrade = orig × C.price_mult_town(fid, tsid)` (KMM_Traces.lua:768-775) ✓код; проба чтения `Town.tradeGoodsMults` (TGM) в игре не дошла до чтения («no home town / error before read», debug.log 2026-11-14) — ?.
· Рычаги: (1) Перенести нашу «полку» с общего `priceMultWhenITrade` (один множитель на всё) на `Town.tradeGoodsMults[item]` — тогда дорожает именно еда в голодном городе, а не весь ассортимент; сначала доказать запись в map из Lua (проба на одном городе). (2) Захват города (Conductor) → новому хозяину `tradeCulture` его фракции: иные запреты и цены видны сразу при торговле — «город сменил хозяина» без единого нашего окна. Цена: правка общей структуры фракции → затрагивает все её города; копировать в `Town.tradeCulture`, не в `Faction`.

### Запрещённое, краденое, контрабанда
Ваниль: `illegalItems`/`forbiddenItems` культуры (kenshi/TradeCulture.h:15-18) → стража ищет; краденое помечено `properOwner` (kenshi/Item.h:94) и `isStolen` :85; скупщики — отряды с `_iBuyStolenGoods`/`_iBuyIllegalGoods` (kenshi/Platoon.h:110-111). Продажа формы фракции её же торговцу — проверка `sellingUniformDetectionCheck` kenshi/Character.h:265; `smugglingTradeCheck` :267.
· Lua: `_iBuyStolenGoods` RW B:10613; **Override** `C:Platoon::iBuyStolenGoods(self, item, defaultVal)`, `C:Platoon::iBuyIllegalGoods(self, defaultVal)`; Notify `C:Character::_NV_smugglingTradeCheck`, `C:Item::_NV_notifyTheftFrom(self, victim)`; `TownBase:isIllegal(item)` B:13607.
· Наше: economy.py — воры/скупщики («fences») в данных SQUAD_TEMPLATE; рантайма нет.
· Рычаги: (1) Override iBuyStolenGoods от состояния мира: в осаждённом/захваченном городе или при голоде торговцы «закрывают глаза» — игрок узнаёт о кризисе по тому, что краденое вдруг принимают. (2) Notify notifyTheftFrom → кража у фракции идёт в шину Conductor (отношения, слух, охотник за головами) — кража становится событием мира.

---

## 2. Торговцы: ассортимент, пополнение, деньги

### Ассортимент и пополнение
Ваниль: SQUAD_TEMPLATE `is trader` + VENDOR_LIST; раз в `vendors refresh time` часов `ActivePlatoon::refreshInventory` перегенерирует товар; лавки-здания (`ShopTrader` — «торговец» внутри здания, kenshi/ShopTrader.h:11, инвентарь :55, `updateInventory` :53) и `ShopTraderInventory::updateInventory` kenshi/ShopTraderInventory.h:31.
· Точки ядра: `ActivePlatoon::refreshInventory(bool firstTime)` kenshi/Platoon.h:232, `_forceRefreshInventory` :233, `getHasVendorList/getHasSpecialItemsList` :245-246, `setupTraderBuildings` :247, `Platoon.traderInventoryRefreshTime` :190, `canRefresh` :98, `regenerates` :99; `Character::isATrader` kenshi/Character.h:383.
· Lua: да — B:659-670, B:10609 `canRefresh`, B:10632 `traderInventoryRefreshTime` (TimeOfDay); **Override** `C:ShopTrader::_CONSTRUCTOR(self, character, defaultVal)`.
· Наше: KMM_Stock — родной `refreshInventory(false)` под крэш-сторожем + своя раздача/снятие товара со склада города (kmm_stock.lua:24, 513) ✓игра; economy.py `vendor_turnover` (refresh чаще) — данные.
· Рычаги: (1) Сдвиг `traderInventoryRefreshTime` вместо своей раздачи: пришёл караван (Conductor) → ассортимент обновляется **ванильным** генератором сейчас; разорили караван → не обновляется неделю (`canRefresh=false`). Ваниль делает работу, мы управляем только временем. (2) Подмена VENDOR_LIST по владельцу города (данные, поток economy) — захваченный город торгует товаром нового хозяина.

### Деньги
Ваниль: деньги отряда в `Ownerships.money` (общая касса отряда/игрока); торговец платит из своей кассы, поэтому «у торговца кончились деньги» — ванильное ограничение продаж игрока. `MoneyItem` kenshi/Item.h:423 — монеты-предмет.
· Точки ядра: `Platoon::getMoney/addMoney/setMoney` kenshi/Platoon.h:47-49, `takeMoneyByForce` :45, `Inventory::getMoney/takeMoney` kenshi/Inventory.h:212-213, `ShopTrader::takeMoney/getMoney` kenshi/ShopTrader.h:22-24, `Character::takeMoney/getMoney` kenshi/Character.h:203-205.
· Lua: `getOwnerships():getMoney/addMoney/setMoney/takeMoney` (B:10326-10349, Ownerships); Notify `C:Character::_NV_takeMoney(self, amount)`.
· Наше: KMM_Tempo `money_min` (касса торговцев/уникальных не ниже порога, раз в сутки, kmm_tempo.lua:527-528); KMM_Diplo читает деньги игрока.
· Рычаги: (1) Касса торговца = богатство города: склад/торговые договоры Conductor поднимают кассу, рейд/осада опустошают — игрок видит экономику мира по цифре денег в окне торговли, и это реально ограничивает продажу добычи. Заменяет «подкачку до минимума» в Tempo. (2) Notify `_NV_takeMoney` → траты игрока (взятки, выкуп, наём) как события для слухов.

### Окно торговли
Ваниль: `ForgottenGUI::showTradeWindow(hand a, hand b, TradeWindowType)` kenshi/gui/ForgottenGUI.h:96; типы TW_MONEY_TRADING/TW_LOOTING/TW_AUTO :27-32; `showTraderInventory(owner)` :99; покупка — `Inventory::buyItem(item, sendingTo)` kenshi/Inventory.h:214; итог сделки — `InventoryGUI::TradeResult::showMessage`.
· Lua: B:6529, B:6520; Notify `C:ForgottenGUI::_showTradeWindow(self, a, b, tradeType)`, `C:ForgottenGUI::showTraderInventory(self, owner, result)`, `C:InventoryGUI::TradeResult::showMessage`; **Override** `C:Inventory::buyItem(self, item, sendingTo) -> Item`.
· Наше: KMM_Nemesis — при открытии торговли торговец роняет реплику о складе/рынке (KMM_Nemesis.lua:97, 1346) ✓код.
· Рычаги: (1) Override `buyItem` — покупка уникального предмета (реликт, трофей Nemesis) как событие мира: соперник узнаёт, кто купил. Риск: перехват на пути денег — только наблюдение (вернуть nil), никогда не подменять предмет. (2) При открытии окна — 1 реплика торговца из реального состояния (уже есть) + `ManagementScreen:addMessage` с ценами соседнего города («в Сквине соль дороже») — торговые маршруты для игрока.

---

## 3. Наём, контракты, рабство

### Наём в барах
Ваниль: TOWN `bar squads` → `Town::spawnTheBarFlies()` kenshi/Town.h:369 при загрузке города (`townLoadedEvent` :371, `chooseResidents` :368); рекрут — диалог: условие `DC_IS_RECRUITABLE` (77), `DC_PLAYERMONEY` (2), действия `DA_TAKE_MONEY` (8) + `DA_JOIN_SQUAD_WITH_EDIT/DA_JOIN_SQUAD_FAST` kenshi/Dialogue.h:36,51 или окно выбора `CHOOSE_RECRUITING` :78. Стоимость = значение DA_TAKE_MONEY на реплике (`DialogLineData::getMoneyCostForLine` :253) — статично в данных.
· Lua: `Town:spawnTheBarFlies()` B:13483; `PlayerInterface:recruit(character, editor)` B:10829-10830 (kenshi/PlayerInterface.h:115-116); Notify `C:PlayerInterface::recruit(self, character, isEditor)`.
· Наше: town.py трогает только ссылки у bar squads; KMM_Veterans: прямая вербовка из Lua отклонена (меняет владение отряда без диалога).
· Рычаги: (1) Бар как отражение мира: выжившие из разорённого города / ветераны проигравшей фракции появляются среди bar flies (подмена squad в `bar squads` потоком town + `spawnTheBarFlies` при следующей загрузке) — игрок встречает людей из событий мира и нанимает их ванильным диалогом. (2) Цена найма от состояния: `run lua script` на реплике найма → доплата/скидка через `Ownerships:takeMoney` (известный соперник берёт дороже); ванильная стоимость в данных остаётся базой. (3) Notify recruit → «кого нанял игрок» в шину слухов.

### Наёмники по контракту
Ваниль: `CHOOSE_HIRING_CONTRACT` kenshi/Dialogue.h:79 → `Blackboard::setContractJob(package, giver)` kenshi/AI/Blackboard.h:75, срок `contractExpiryTime` :165, предательство `contractJobNotifyBetrayal` :139; классы `Contract_Timed/HiredAlly/DefendPlayerBase/UntilExSlave` kenshi/AI/Contract.h; события `EV_CONTRACT_JOB_ENDED` (30), `EV_BETRAYAL` (31); условие `DC_HAS_AI_CONTRACT` (78).
· Lua: `setContractJob` B:2278; классы контрактов в биндингах (оглавление).
· Наше: нет.
· Рычаги: (1) Наёмник, которого игрок предал/бросил, становится соперником (Nemesis) — событие EV_BETRAYAL уже ванильное; нужно только слушать его через Override `sendEvent` (смотреть `what`, вернуть nil).

### Рабство в торговле
Ваниль: продажа/покупка людей идёт через диалог (CHOOSE_SLAVES_SELLING/BUYING, CHOOSE_PRISONER_BAIL, DA_PLAYER_SELL_PRISONERS, CHOOSE_ANIMALS_BUYING, DA_ENSLAVE_TARGETS_CARRIED_PERSON, DA_FREE_TARGET_SLAVE, DA_REMOVE_SLAVE_STATUS kenshi/Dialogue.h:73-86) и окно `CharacterTradingWindow` kenshi/gui/CharacterTradingWindow.h:9 (`Instance` :20, `currentTotalText` :29). Владелец — `Character::changeSlaveOwner` kenshi/Character.h:602, `isSlave` :601, `Ownerships.slaves` kenshi/Platoon.h:52; фракции-аболиционисты `Faction::isAntiSlavery` kenshi/Faction.h:122. События: EV_INTRODUCING_NEW_SLAVE (35), EV_SLAVE_DELIVERY (39), EV_BOUGHT_ME_FROM_SLAVERY (51). Формула цены раба в заголовках не видна (?).
· Lua: `isSlave` B:3395, `changeSlaveOwner` B:3458, `isAntiSlavery` B:5762, `CharacterTradingWindow` (show/isVisible/update/close); Notify `C:Character::changeSlaveOwner`.
· Наше: нет.
· Рычаги: (1) Поставка невольничьих рынков = пленные из боёв мира (Conductor-рейды) — уже через `changeSlaveOwner`, без своих счётчиков; игрок видит в окне продажи знакомых (бывших соперников). (2) Notify changeSlaveOwner → продажа игроком пленного из фракции X → отношения/слух у X и у аболиционистов.

---

## 4. Исследования

### Исследования и артефакты
Ваниль: очередь `Research::current` kenshi/Research.h:89, скорость от столов/исследователей (`getCurrentResearchRate` :59, `researchDeskLevel` :96), цена — предметы-артефакты (`ResearchItem::getCostItem/Quantity` :17-18, `hasArtifact` :75, `payCosts` :55); артефакты помечены `InventoryItemBase::isResearchArtifact` kenshi/Item.h:62; диапазон ценности артефактов в лут-ящиках города `Town::getItemArtifactsMin/MaxValue` kenshi/Town.h:238-244. Условие диалога `DC_PLAYER_TECH_LEVEL` (12).
· Точки ядра: `startResearch` :47, `completeResearch` :51, `progressResearch(amount)` :62, `isFinished` :52, `checkRequirements` :64, `serialise/load` :60-61; доступ `PlayerInterface.technology` kenshi/PlayerInterface.h:185.
· Lua: `getPlayerInterface().technology` B:10712; все методы Research в биндингах; `isResearchArtifact` B:8311; Notify `ManagementScreen::researchRemoved/refreshResearchList/...`.
· Наше: tech.py — дерево «Relics» (только данные).
· Рычаги: (1) Артефакты как добыча гонки: соперники (RelicRace/Nemesis) забирают книги/ядра из руин раньше игрока → игрок покупает их втридорога у торговца или отбивает у соперника; ваниль сама решает, что с ними делать в столе исследований. (2) `progressResearch` за пленного учёного/прочитанную записку — малыми долями, как «узнал от»; не `completeResearch` (ломает прогрессию). (3) Линии с `DC_PLAYER_TECH_LEVEL` — NPC реагируют на технологичность игрока (данные, без Lua).

---

## 5. Диалоги

### Устройство реплики
Ваниль: DIALOGUE → дерево `DialogLineData` kenshi/Dialogue.h:149: условия `DialogCondition{key, compareBy, who, value}` :159-166, действия `DialogAction{key, value}` :153-158, флаги цели/личности :175-178, раса/фракция/город/предмет :180-195, состояние мира `worldState` (WorldEventStateQueryList) :196, `campaignTriggers` :179, `givesItem` :183, `factionRelationEffects` :237, шансы `chancePermanent/Temporary` :217-218, повтор `dialogRepeatMinTimeInHours` :221, `onceOnly` :208, блокировки `locks/unlocks_*` :226-228, `crowdTrigger` :229, перебивка игроком `playerInterruptionDialog` :238.
Состояние мира для реплик — `WorldEventStateQuery` kenshi/WorldEventStateQuery.h:16: уникальные NPC DEAD/ALIVE/IMPRISONED, города, союз/война, участие игрока.
Условия (DialogConditionEnum, 80): ключевые для живого мира — DC_RELATIONS 1, DC_PLAYERMONEY 2, DC_REPUTATION 3, DC_FACTION_VARIABLE 6, DC_PLAYER_TECH_LEVEL 12, DC_MET_TARGET_BEFORE 20, DC_HAS_TAG 23, DC_BOUNTY_AMOUNT_PERCEIVED 40, DC_I_LOVE_THIS_GUY 52, DC_I_HATE_THIS_GUY 53, DC_I_SHOULD_SCREW_THIS_GUY_OVER 54, DC_STARVING 71, DC_TOWN_LEVEL_CURRENT_LOCATION 73, DC_IS_RECRUITABLE 77.
Действия (DialogActionEnum kenshi/Dialogue.h:31-93): торговля DA_TRADE, деньги DA_TAKE/GIVE_MONEY, отношения DA_AFFECT_RELATIONS/REPUTATION, война DA_DECLARE_WAR/END_WAR, наём, рабство, награды DA_ASSIGN_BOUNTY/CLEAR_BOUNTY, память DA_REMEMBER_CHARACTER, DA_LOCK_THIS_DIALOG, фазы кампаний.
· Наше: diplo.py — свой DIALOGUE с DC_PLAYERMONEY, DA_TAKE/GIVE_MONEY, жетонами «target has item».

### Условия реплик из скрипта
· Точка ядра: `Dialogue::_checkCondition(cond, compareBy, val, target, actualTarget)` kenshi/Dialogue.h:369.
· Lua: **Override** `C:Dialogue::_checkCondition(self, conditionName, compareBy, val, target, actualConversationTarget, defaultVal) -> boolean`.
· Наше: нет (Diplo обходится жетонами-предметами).
· Рычаги: (1) Резервное условие (например DC_FACTION_VARIABLE с кодом val ≥ 9000; в ванили его сравнение с `RelationData.stateVariables` kenshi/FactionRelations.h:90, из Lua не связано) → Lua отвечает «правда/ложь» по состоянию Conductor/Nemesis. Тогда **обычные FCS-реплики** («Ты тот, кто сжёг Мусорный город?», «Склад пуст, торговать нечем») включаются миром, без жетонов в инвентаре. Цена: вызов на каждую проверку реплики у каждого говорящего — только O(1) по таблице, все прочие коды вернуть nil. (2) Заменить жетоны Diplo на это условие (меньше предметов-костылей).

### Запуск и подмена разговоров
· Точки ядра: `Dialogue::sendEvent(who, EventTriggerEnum)` kenshi/Dialogue.h:351, `sendEventOverride(who, what, forceRepeat)` :350, `runCustomDialog(GameData*)` :353, `scoreCustomDialog` :354, `makeAnnouncement(GameData*)` :359, `addConversation(con, EventTriggerEnum)` :346, `addDialoguePackage` :345, `clearConversationList` :347, `setLineLocked(line, on)` :338, `say(text, line)` :367, `insertWordSwaps` :333, `endDialogue` :361; доступ `Character.dialogue` kenshi/Character.h:487. Отдельно `PlayerInterface::triggerAreaArrivalDialogue(area)` kenshi/PlayerInterface.h:126.
EventTriggerEnum (75): EV_PLAYER_TALK_TO_ME 1, EV_ANNOUNCEMENT 2, EV_I_SEE_NEUTRAL_SQUAD 3, EV_BAR_TALK 12, EV_I_DEFEATED_SQUAD 15, EV_CONTRACT_JOB_ENDED 30, EV_BETRAYAL 31, EV_BOUNTY_SPOTTED 44, EV_ENTER_BIOME 48, EV_ENTER_TOWN 49, EV_SQUAD_BROKEN 50, EV_I_SEE_ENEMY_PLAYER 66, EV_I_SEE_ALLY_PLAYER 67, EV_I_SEE_PLAYER_NICE_BUILDING 72, EV_TAKEN_OVER_PLAYER_TOWN 73, EV_CROWD_TRIGGERED 74.
· Lua: B:5398-5417; **Override** `C:Dialogue::sendEvent(self, who, what, defaultVal)`, `C:Dialogue::startConversation(self, target, talk, ev, force, defaultVal)`, `C:Dialogue::startPlayerConversation(self, target, talk, defaultVal)`; Notify `C:Dialogue::say`, `C:Dialogue::_doActions`, `C:Dialogue::_endPlayerConversation`, `C:Dialogue::endDialogue`.
· Наше: нет (Rumors/Nemesis говорят мимо системы диалогов через `Character:say`).
· Рычаги: (1) `addConversation(<DIALOGUE из нашего .mod>, EV_I_SEE_NEUTRAL_SQUAD)` конкретному сопернику в рантайме + `sendEvent(pc, EV_I_SEE_NEUTRAL_SQUAD)` при встрече → он говорит FCS-репликой с условиями, переменными (word swaps), действиями (DA_AFFECT_RELATIONS, DA_ATTACK_CHASE_FOREVER) — встреча с конкурентом становится настоящим ванильным диалогом. (2) `addConversation(..., EV_PLAYER_TALK_TO_ME)` торговцу/бармену: разговор «о новостях», ветка которого выбирается `_checkCondition` из шага выше. (3) Override `sendEvent` — только наблюдать ванильные события (EV_I_DEFEATED_SQUAD, EV_BETRAYAL, EV_BOUGHT_ME_FROM_SLAVERY) как источники фактов для мира; не подавлять.

### Lua на реплике (мост диалогов)
Ваниль+KenshiLua: на DIALOGUE_LINE ссылка «run lua script» → LUA_SCRIPT (тип 322, поле `file`) → при `Dialogue::_doActions` выполняется `scripts/dialogue/*.lua` с глобалами `currentDialogue`, `currentDialogueLine` (DialogueScriptingBridge.md). Нужен FCS Extended (или генератор kmod, как у нас).
· Lua: да. В скрипте доступны `currentDialogue.me`, `getConversationTarget()`, `npcReplyText` (RW B:5376), `say(text, line)`.
· Наше: KMM_Diplo — `scripts/dialogue/kmm_diplo_line.lua` → `KMM_Diplo.on_line` ✓игра.
· Рычаги: (1) Эффекты реплик, которых нет в DialogActionEnum (сдвиг склада, выдача слуха, метка на карте, доплата за наём) — через одну общую точку, как Diplo. (2) Динамический текст ответа: `DialogueWindow:setNPCText` (B:5551) / `Dialogue:say(text, line)` из скрипта реплики — ?; проверить на одной реплике, иначе текст в данных + word swap.

### Реплика-пузырь и память NPC
· Точки ядра: `Character::say(s)` kenshi/Character.h:361, `say_WithARepeatLimiter` :359, `sayALine(line, force)` :486; `DialogueSpeechBubble(shout, important)` kenshi/Dialogue.h:101. Память: `Character::rememberCharacter(who, CharacterPerceptionTags_LongTerm)` kenshi/Character.h:544, `getCharacterMemoryTag` :545; теги LT_MY_LIFESAVER, LT_FREED_ME, LT_STOLE_FROM_ME, LT_MY_CAPTOR, LT_DEFEATED_MY_SQUAD_ONCE, LT_SQUAD_LOST_TO_ME_ONCE, LT_KILLED_MY_FRIEND, LT_I_SCREWED_THIS_GUY (kenshi/Character.h:87-101).
· Lua: B:3243, B:3322, B:3449-3450, B:3466-3467; Notify `C:Character::_NV_say`.
· Наше: Rumors (`speaker:say`, rumors.log say=ok) ✓игра; Nemesis `leader:say`, `rememberCharacter(pc, tag)` (KMM_Nemesis.lua:1091, 1327) ✓код.
· Рычаги: (1) Ванильная память вместо нашей: LT_DEFEATED_MY_SQUAD_ONCE / LT_SQUAD_LOST_TO_ME_ONCE ставить соперникам после реальных встреч, а их реплики выбирать ванильными условиями (DC_MET_TARGET_BEFORE, DC_I_HATE_THIS_GUY; связь DC_HAS_TAG ↔ LT-теги — ?). Хранится в памяти отряда (`ActivePlatoon::getMemory` kenshi/Platoon.h:213, сохраняется с отрядом — ?).

---

## 6. Каналы сообщений, интерфейс, карта

### Сообщения игроку
· `GameWorld::showPlayerAMessage(msg, queued)` kenshi/GameWorld.h:149 — строка вверху экрана; `showPlayerAMessage_withLog` :148 — плюс запись в журнал; `sysMessage(SysMessage)` :192 (SysMessageEnum + target/from, :175-183). Lua B:7090. Наше: Diplo (kmm_diplo.lua:295), Rumors (:500) ✓код (в Rumors помечено «не проверено»).
· `ManagementScreen::addMessage(owner, message, MessageLogColor)` kenshi/gui/ManagementScreen.h:110, `getSingleton()` :87, цвета ML_NORMAL/ML_PLAYER/ML_SYSTEM :20-24. Lua B:9183. Наше: хроника KMM_Nemesis (очередь, интервал, KMM_Nemesis.lua:255-268) ✓код.
· `ForgottenGUI::createScreenLabel(text, colour, LabelSize, RisingSpeed)` kenshi/gui/ForgottenGUI.h:206 → `ScreenLabel` (`setTracking(handle, offset)`, RS_STOPPED…RS_FAST, LS_SMALL…LS_LARGE kenshi/gui/ScreenLabel.h:35-47) — всплывающий текст над персонажем; `createFloatingLabel` :189; `messageBox(title, msg, btn, modal, cb)` :70 (модальное окно — не использовать, ломает темп); `showPauseMessage` :60. Lua B:6513; получение экземпляра ForgottenGUI — ? (глобал `gui` в Globals.h, из Lua — через self колбэка `ForgottenGUI::*`).
· Рычаги: (1) Иерархия каналов «как в ванили»: важное о самом игроке → `showPlayerAMessage_withLog`; фон мира → вкладка сообщений `addMessage` (ML_NORMAL, owner = фракция); рядом — только голосом NPC (`say`). Никаких модальных окон. (2) ScreenLabel с трекингом над соперником при первом опознании («Урках Коллекционер») — ванильный вид, как подписи урона.

### Карта
Ваниль: города открываются по дальности (`TownBase::withinDiscoveryRange` kenshi/Town.h:152), флаги `discovered/recentlyDiscovered` :281-283, маркер `getMapMarker` :447; карта — `MapScreen` kenshi/gui/MapScreen.h:13 (маркеры городов :102, персонажей :104, `addSquad/removeSquad` :64-65, `setMovementMarker(pos, time)` :67, `getMarkerColor` :86), доступ через `ManagementScreen.mapScreen` kenshi/gui/ManagementScreen.h:129 и `addSquadToMap/removeSquadFromMap` :108-109, `refreshMap` :105.
· Lua: `setDiscovered/setRecentlyDiscovered/setExplored` B:13640-13645; `addSquadToMap` B:9176; MapScreen методы в биндингах; Notify `C:MapScreen::getMarkerColor(who, result)`.
· Наше: нет.
· Рычаги: (1) Слух открывает место: NPC рассказал о лагере/руине/городе → `setDiscovered(true)` + `setRecentlyDiscovered(true)` — ванильный «новый» маркер; знание мира приходит от людей, а не от карты-подсказки. Цена: необратимо для игрока (снимать нельзя по смыслу). (2) Заказ на голову/известный соперник → `addSquadToMap(его Platoon)` на время (снять `removeSquadFromMap`) — охота через ванильную карту. (3) `setMovementMarker` — разовая точка «здесь видели караван» (временная).

### Экран фракций и окно отряда
`FactionsScreen` (kenshi/gui/FactionsScreen.h) сам показывает отношения из `FactionRelations`; `SquadManagementScreen` — отряды. Рычаг: ничего не рисовать — все наши изменения отношений делать через `FactionRelations` (домен дипломатии), и игрок увидит их в ванильном окне.

---

## 7. Сохранение собственных данных

### Сейв
Ваниль: `SaveManager::save(name, autosave)` kenshi/SaveManager.h:33 → объекты пишут себя через `serialise/loadFromSerialise` и `GameSaveState` (kenshi/GameSaveState.h:11: `states`, `createState/getState(itemType)`); игрок — `PlayerInterface::serialise/loadFromSerialise(GameData*)` kenshi/PlayerInterface.h:180-181; диалоги — `Dialogue::save/load` kenshi/Dialogue.h:376-377 (блокировки реплик персонажа), глобально `DialogDataManager::save/load` :440-441 (onceOnly/lastTimeSaid); исследования `Research::serialise/load` kenshi/Research.h:60-61.
· Lua: Notify `C:PlayerInterface::serialise(self, gameData)` / `loadFromSerialise`, а также `Character/Building/Platoon/Town::_NV_loadFromSerialise`; поле KenshiLua `GameData.sdata` (B:6672, строковое хранилище); `SaveManager.getSingleton()` (`getCurrentGame` — имя сейва).
· Наше: Conductor — `gameData.sdata[STATE_KEY] = serialize(S)` + зеркала `*.kmmstate` и `last.kmmstate` (KMM_Conductor.lua:4454-4468); Rumors — список рассказанного (KMM_Rumors.lua:582). ✓код (раньше писали в несуществующее `data_string`, STATUS.md:70).
· Рычаги: (1) Что можно — держать в ванильном состоянии, которое игра сохраняет сама: память NPC (`rememberCharacter`), блокировки реплик (`setLineLocked`, сохраняется в `Dialogue::save` — ?), отношения, `discovered` городов, деньги касс, исследования. Наш `sdata` — только для того, чего в ядре нет (модель склада, хроника). (2) Не вызывать `SaveManager:save` из скриптов.

---

## Лучшие рычаги для живого мира (ранжировано)

1. **`Dialogue::_checkCondition` (Override) + обычные FCS-реплики.** Состояние мира (Conductor/Nemesis/Stock) включает ванильные строки у торговцев, барменов, стражи и соперников. Игрок слышит мир в ванильном окне диалога. Вместо жетонов-предметов. Цена: горячий путь, только O(1) по таблице и одно зарезервированное условие.
2. **`addConversation` + `sendEvent` соперникам.** Встреча с конкурентом становится настоящим диалогом с ванильными действиями: угрозой, войной, погоней, данью. Это прямой путь к «прокачке через встречи». Опора на ✓игра-мост Diplo.
3. **Override `InventoryItemBase::getValueSingle` / `Town.tradeGoodsMults`.** Дефицит и избыток видны по цене конкретного товара в окне торговли, а не общим множителем `priceMultWhenITrade`. Сначала проба записи в map, если не выйдет — Override с кэшем.
4. **Касса торговца = богатство города** (`Ownerships` money). Рейды и договоры меняют деньги торговцев. Игрок упирается в ванильное «у него нет денег», когда пытается сбыть добычу в разорённом городе. Заменяет подкачку в Tempo.
5. **Карта через слухи: `setDiscovered/setRecentlyDiscovered`, `addSquadToMap`.** Люди рассказывают о местах и целях, и это появляется на ванильной карте. Охота за головами идёт через карту.
6. **Ванильная память NPC (`rememberCharacter` LT_*) + условия DC_MET_TARGET_BEFORE / DC_I_HATE_THIS_GUY.** Соперник помнит поражение, и это хранится в сейве силами игры, а не в нашей переменной.
7. **Пополнение через `traderInventoryRefreshTime` / `canRefresh`.** Ваниль сама генерирует товар, мы двигаем только время: пришёл караван — сразу обновил лавку, разорили — лавка пустеет. Меньше своей раздачи в Stock.
8. **Бар как отражение событий (`bar squads` + `spawnTheBarFlies`).** Выжившие и ветераны из реальных битв мира нанимаются ванильным диалогом. Цену найма можно править скриптом реплики.
9. **Невольничий рынок из пленных мира (`changeSlaveOwner`, CHOOSE_SLAVES_*).** Слушаем, кто кого продал. Аболиционисты и фракция проданного реагируют через отношения.
10. **Краденое по состоянию мира (Override `iBuyStolenGoods`/`iBuyIllegalGoods`, Notify `notifyTheftFrom`).** Кризис в городе виден по поведению скупщиков. Кража становится событием для фракции.
11. **Иерархия каналов без модальных окон.** Своё — `showPlayerAMessage_withLog`, мир — `ManagementScreen:addMessage`, рядом — `say`, опознание — `ScreenLabel` с трекингом.
12. **Артефакты исследований как добыча гонки** (`isResearchArtifact`, лут руин, `progressResearch` малыми долями). Соперники опережают игрока у руин, а ваниль сама решает, что делать с найденным.

---

## 8. Руда (ORE3, 2026-11-15)

### Схема одной строкой
Жила региона (модель дирижёра `S.ore[город]`: R, R0) ← черпают фракции (`ore_step`, по нужде металла) и игрок (`KMM_Ore` → `player_mined`) → остаток жил региона (`region_ore`) задаёт выход узлов игрока (`_resourceMiningLevel`, подпись «ore left … vein …») → нехватка металла фракций = `f.stress` → `ore_stress`, `metal_price` (цены торговцев через Traces `price_mult` ✓игра), рейды по нужде (`raid_base` «need»), рудный кризис и излом (сюжет) → брошенные жилы медленно восстанавливаются (`vein_regen_per_year`). Добыча игрока на чужой земле злит владельца жилы (`ore_claim` → отношения → RELSYNC в ванильные отношения фракций).

### Что было в игре до ORE3 (аудит по logs/ и сейвам)
- `ore.log` во всех 12 сессиях — только строка `active … nodes in state=0`. Сессии — новые игры (ключ мира каждый раз новый, день старта 1.42, максимум ~12 дней). В последнем сейве (KMM_New_test9) у фракции игрока 204-gamedata.base нет ни одного здания (разбор zone/*.zone через kmod). Ни ошибки, ни строки SKIP: цепочка опроса ни разу не дошла до рудного шаблона. Вывод: признаков добычи игроком в этих сессиях нет (?), но модуль и не смог бы увидеть часть добычи:
  - автоматические буры (Ore Drill III Automated, SC Auto…) работают без шахтёра — опрос персонажей их не видит;
  - список шаблонов был ручным: не было буров Copper drill.mod и Soulbody (14 шаблонов);
  - цель бралась только из `Tasker.subject` (без `currentSubTarget`); диагностики до стадии шаблона не было;
  - `getGameData/getPosition/getName` вызывались у `ProductionBuilding`; в игре проверены только у `Building` (KMM_Town/KMM_Stock ✓игра);
  - состояние узлов — файл на семя мира, не сейв: откат на старый сейв не откатывал узлы.
- Модель дирижёра работала (✓игра: в state/*.kmmstate есть `ore_stress`, `ore_share`, `metal_price`; 255 жил, 35 рудников), но `stats.player_mined` = nil во всех сейвах — добыча игрока в мир не попадала ни разу.

### Механики ORE3 (реализовано, офлайн-проверено)
| Что | Где | Ванильный рычаг | Статус |
|---|---|---|---|
| Шаблоны рудных узлов и машин всей цепочки модов (30: 5 природных, 25 шахт/буров, 9 автоматических) | `build/KMM_Ore/scripts/ore_templates.lua` (генератор `_dev/gen_ore_templates.py`: BUILDING_FUNCTIONALITY «world resource mining» 1/3) | данные игры | ✓код |
| Запасная классификация в игре по функциональности шаблона | `GameData:getFromList("functionality", i)` B:6652 | — | ✓код (LEARN template в логе) |
| Труд персонажа: действие → `subject`/`currentSubTarget` → `Building` → шаблон | kmm_ore.lua `work_of` | `CharBody:getCurrentAction`, `Tasker.subject/currentSubTarget` B:12994 | ✓код (у NPC эта цепочка ✓игра в KMM_Town) |
| Приказ игрока на рудный узел учит TaskType (LEARN, ≤4) | подписка в первом рабочем тике | Notify `PlayerInterface::newPlayerTaskSelectedCharacters` (CallbacksReference) | ✓код |
| Автобуры игрока: скан зданий вокруг персонажа раз в 30 с, часы под питанием при `productionState` NORMAL | kmm_ore.lua `scan` | `getObjectsWithinSphere` (✓игра в KMM_Stock), `Building:isPowerOn/isBroken/isThePlayer`, `ProductionBuilding.productionState` | ✓код |
| Выход узла = base·max(floor,(R/R0)^k)·max(0.2, доля жил региона) | `apply_level` | `ProductionBuilding._resourceMiningLevel` RW | ? (влияет ли поле на выход — не проверено с v0) |
| Подпись узла «Iron [ore left 73% vein 40%]» | `show_left` | `RootObjectBase:getName/setName` у Building | ✓код |
| Узлы в состоянии мира `S.ore_nodes` (в сейве, откат вместе с сейвом); старый сейв — импорт из `logs/ore_nodes_<мир>.tsv` | `ensure_world` | `PlayerInterface::serialise` дирижёра | ✓код |
| Труд → жила мира порциями раз в 2 игровых часа | `flush_feed` → `KMM_Conductor.player_mined` | — | ✓код |
| Жила, из которой за тик не черпали, восстанавливается 1,5 % R0 в год | `KC.ore_regen` (World.lua), `params.ore.vein_regen_per_year` | — (модель) | ✓код |
| Владелец жилы и добыча игрока: каждые 3 % R0 (не чаще 20 дней) отношение −1.5·(1+стресс металла ≤2), пол −30; договор — без претензии; событие `ore_claim` | `KC.ore_claim`, `params.ore.claim` | отношения фракций → RELSYNC (✓игра RELSYNC ×49) | ✓код |
| Сводка рудного хозяйства игрока `S.base.ore = {active, recent, auto, x, z, day}` (только при известной базе) | `summary` | — (контракт для читателей) | ✓код, читателей пока нет |

Проверки: `build/KMM_Ore/_dev/test_ore.py` 21/21, `test_ore_world.py` 21 проверка, `build/KMM_Conductor/_dev/test_story.py`, `test_conductor.py`, `test_conductor_core.py` — зелёные; `tools/api_audit.py` — по kmm_ore.lua неизвестных методов и нарушений сигнатур нет. Прогон 8 лет (копия sim_years.py): семя 2026 — без восстановления кризис на дне 2260, с 1,5 %/год — на дне 2495; семя 7 с 1,5 %/год — день 2115. Кризис и излом остаются, цикл сюжета сохраняется.

### Маркеры ore.log для session_report
`KMM_Ore v3 active: … source=save|save(new)|file->save|file` · `order hook ok` · `ORDER task=N node=SID …` · `LEARN task=N` · `LEARN template SID` · `NEW node` · `MINE` (персонаж) · `AUTO` (автобур) · `CHAIN ok=… far=… not_ore=… no_target=… task_other=… tasks=87:5,…` (раз в 12 игровых часов: где обрывается цепочка) · `DEPLETED` · `scan unavailable` · в debug.log `[KMM_Ore] <часть> disabled until restart`. Шина: событие `ore_claim` (chronicle.log).

### Отложено (L) — порядок внедрения
1. **Рудник игрока как цель войск в «Железном голоде»** (KMM_Conductor_Econ.lua `raid_base`, владелец Econ): если `S.base.ore.active > 0` и `f.stress > player_base.need_stress`, мотив «ore» (вес × min(2, recent/24)) и точка цели `S.base.ore.x/z` вместо дома. Для родной кампании (`CA.base_try`, Sync) — `getNearestTown` от точки рудника. Сначала маркер `raid_base why=ore` в логе, потом вес акта.
2. **Налог владельца ванильной кампанией** (Sync, владелец Sync/campaigns): `ore_claim` при отношении ≤ −15 запускает «visit»-кампанию владельца (у UC/Traders Guild это ванильные TaxMan: 61061-Dialogue.mod, 61568-Dialogue.mod в campaigns.json) через `CA.fire`, не чаще 60 дней. Тогда «требует долю» = ванильный сборщик у ворот.
3. **Богатство аутпоста для бандитов** (KMM_Traces `base_track`, KMM_Nemesis `worth`): `B.value += S.base.ore.recent/4 + 10·S.base.ore.auto`; `N.worth` — то же слагаемое в `gear`, чтобы богатый рудник снимал «poor/contempt».
4. **Цена руды и слитков по городам** (Traces TGM, владелец Traces): `Town.tradeGoodsMults[Raw Iron 1866 / Raw Copper 42158 / Iron Plates 42159 / Copper Alloy 42160] = clamp(metal_price · (1 + 0.5·metal_def города), 0.7, 2.5)`. Запись TGM из Lua в игре идёт (debug.log 2026-11-15: `TGM probe OK … newidx=true`, `TGM town … writes=110`), но **видна ли новая цена в открытом окне торговли без перезагрузки сейва — не проверено**.
   Ограничение (поиск по сети 2026-11-16): автор экономического мода пишет, что ванильные цены у него менялись только после перезагрузки сейва; модов с истощением руды и живыми ценами в Кенши не нашлось. У нас это касается двух путей: `tradeGoodsMults` (Traces TGM) и `Platoon.priceMultWhenITrade` (Traces фолбэк). Если окно торговли кэширует цены (вероятно, при создании торговца или `refreshInventory`), рудный кризис в ценах будет виден с запозданием: после пополнения ассортимента или перезагрузки, но не мгновенно. Для руды это допустимо: `metal_price` меняется раз в тик дирижёра (5 дней), а не за минуты. Остальная реакция мира от этого не зависит: рейды, отношения, `ore_claim`, слухи и выход узлов.
   Шаг владельца (в STATUS): в одной сессии записать цену Raw Iron у торговца, дождаться строки `TGM town <город>` в debug.log с другим `metal=`, открыть окно снова без перезагрузки. Если цена не изменилась, Traces должен после записи TGM вызывать `ActivePlatoon::refreshInventory(false)` (B:659) у торговцев города, не чаще раза за тик дирижёра.
5. **Слухи** (KMM_Rumors, шаблон `ore_claim`): en «%A% says the Nameless dig its iron near %TOWN%. They want their cut.» / ru «%A% считает железо, что Безымянные копают у %TOWN%. Хотят свою долю.».
6. **NPC-шахтёры загруженных городов** (KMM_Town): их труд у рудных узлов (те же шаблоны) списывать с жилы города (`player_mined`-подобный вызов `region_mined(fid, …)`), чтобы видимая работа и модель совпадали.
7. **Проверка рычага выхода**: в живой игре сравнить скорость наполнения Raw Iron при `write_level=true/false` (маркеры MINE с level). Если поле не влияет — выход резать плагином KMM_Native (`ProductionBuilding::getMiningResourceLevel` hook), остальное ORE3 остаётся.
