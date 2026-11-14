# ENGINE_MAP — карта API KenshiLua для системы «némesis / память игрока» (2026-11-14)

Источник: `C:\Program Files (x86)\Steam\steamapps\workshop\content\233860\3817000612\docs\` (далее B = BindingsReference.md, C = CallbacksReference.md, D = DialogueScriptingBridge.md, E = EnumsReference.md, U = UnboundReference.md, X = CppExtensionAPI.md). Числа после файла — номера строк. Всё по документации; в игре проверено только то, что помечено «у нас в деле». Игру не запускали.

Правила линтера (`tools/build/lua_lint.py`): `Events.on` вне функции — только для `GameWorld::charsUpdate`, `PlayerInterface::serialise`, `PlayerInterface::loadFromSerialise`, `Character::_NV_hitByMeleeAttack`, `MyGUI::Gui::eventFrameStart`; второй аргумент каждого `Events.on` обязан быть `guarded(...)`; `io.open`/`os.*` на верхнем уровне запрещены (кроме KMM_Native.lua); `data_string` запрещён. Новые события регистрируем либо внутри функции (из первого тика), либо добавляем в `ALLOWED_TOP_EVENTS`.

Общее по колбэкам (C:5-22): два вида. Notification — `Events.on(name, fn(self, ...))`, `return false` гасит остальные Lua-обработчики, движок не прерывает. Override — если handler вернул значение нужного типа, движок берёт его вместо своего (nil = оставить `defaultVal`). `Events.off(id)` снимает. Указатели из колбэка не хранить (объект может умереть), хранить `hand`/ID.

---

## 1. Детект поступков игрока

Префикс `_NV_` = «non-virtual»: хук на невиртуальное тело виртуального метода. Документация это не объясняет (в C нет описания) — это вывод по имени и по тому, что у `CharacterAnimal` есть собственные `_NV_*` (C:156-168). Риск: хук может не сработать, если конкретный подкласс переопределил метод. У нас в деле проверен только `Character::_NV_hitByMeleeAttack` (KMM_Conductor.lua:4521).

| Поступок | Событие (C, строка) | Сигнатура | Заметки/риск |
|---|---|---|---|
| Нокаут | `MedicalSystem::knockout` (C:91) | `function(self: MedicalSystem, skill: number)` | `self.me` = Character (B MedicalSystem поле `me`). Срабатывает при уходе в KO любой причины (в т.ч. голод). Кто ударил — не передаётся: брать `me.lastGuyWhoDefeatedMe` (B:3065 раздел Character, поле, hand) и последний `attacker` из hitByMelee. Опрос: `Character:isUnconcious()` (B:3308), `MedicalSystem.unconcious/knockoutTimer`, `isLiterallyUnconciousNotPretending()`. |
| Удар (замах/попал) | `Character::_NV_hitByMeleeAttack` (C:38) | `function(self, cutDir, damage: Damages, attacker: Character, attack: CombatTechniqueData, comboID)` | Только ближний бой; стрельба арбалетом не ловится (есть `Character:iShotYou(attacker, poon, onPurpose)` B, но колбэка нет). Частый — тяжёлый handler недопустим. |
| Смерть | `Character::declareDead` (C:30) | `function(self: Character)` | Убийцу не даёт: читать `self.lastGuyWhoDefeatedMe` (hand→`:getCharacter()`, B Hand:7408) внутри handler. Также `self.crimes` (BountyManager, B:3065). Анимал/люди — один колбэк? У `CharacterAnimal` отдельного нет. |
| Становится без сознания / встаёт | `MedicalSystem::knockout`, `Dialogue` события `EV_GET_UP_PEACE/FIGHT` (E:1478) | — | Выход из KO колбэком не ловится: опрашивать `isUnconcious()` в `charsUpdate` для помеченных. Override `MedicalSystem::canGetUpWakeUp(self, defaultVal)->boolean` (C:717) позволяет держать лежать/будить. |
| Кража/ограбление | `Character::_NV_ImStealingDoYouNotice` (C:44) `function(self, stealFrom: RootObject, item: Item)`; `Item::_NV_notifyTheftFrom` (C:63) `function(self, victim: RootObject)`; override `Character::_NV_isItOkForMeToLoot(self, victim, item, defaultVal)->boolean` (C:696) | | Первый = «вор проверяет, заметили ли»; второй = факт кражи, victim может быть контейнером (RootObject). Лутание лежащего: `EV_LOOTING_WEAPON_ONLY/EVERYTHING` (E:1478+, диалоговые). Обмен с инвентарём: `Inventory::_NV__sectionAddItemCallback/_RemoveItemCallback(self, item)` (C:113-114) — шумные. Преступление и свидетель: `BountyManager::notifyCrimeWitnessed(self, faction, againstWho: hand, expiryTime, crimeType)` (C:64; `CrimeEnum` E:295: ENSLAVING=1, STEALING=3, MURDER=4, ASSAULT=5, ASSAULT_VIP=6, SLAVE_FREEING=7, LOOTING=10, KIDNAPPING=15 …) — лучший «свидетель», даёт фракцию-свидетеля и жертву. |
| Рабство: порабощение/освобождение | `Character::changeSlaveOwner` (C:95) `function(self, newOwnerHandle: hand)`; `Character::setChainedMode` (C:96) `function(self, on: boolean, ownerHandle: hand)` | | Опрос: `Character:isSlave()->SlaveStateEnum` (B:3395; E:1016: NOT_SLAVE 0, IS_SLAVE 1, ESCAPING_SLAVE 2, EX_SLAVE 3), `isChainedMode()`, `getMySlaveOwner()`. Освобождение: `LT_FREED_ME`, `CRIME_SLAVE_FREEING`. Сами эти методы мы вызываем (setChainedMode ×10) — своя запись из Lua тоже триггерит хук. |
| Рекрут | `PlayerInterface::recruit` (C:57) `function(self, character: Character, isEditor: boolean)` | | Уход из отряда (бросил): `ActivePlatoon::_NV_removeObject(self, character)` (C:61) + `ActivePlatoon::_NV_addActiveObject(self, character)` (C:60); `Character::_NV_setFaction(self, faction, platoon)` (C:41) — смена фракции (рекрут/увольнение/вербовка). |
| Пленники (клетка/кол) | `Character::setPrisonMode(on, h: UseableStuff)` (B:3389) — колбэка нет; `Platoon.imprisoned` (поле), `Character:isPrisonerFreeToGo()` (B:3355), `isKidnapped()` | | Событий для клетки нет: опрос в тике. Диалоговые события: `EV_UNLOCK_MY_CAGE_OR_SHACKLES`, `EV_PRISONER_FREE_TO_GO`, `EV_BOUGHT_ME_FROM_SLAVERY`, `EV_RECAPTURED_A_SLAVE` (E:1478+). `DialogConditionEnum` DC_IS_IMPRISONED/DC_IMPRISONED_BY_TARGET (E:1559). |
| Лечение игроком | `CharStats::xpFirstAid` (C:50) `function(self: CharStats, patient: Character, time, medicStat)` | | `self.me` = лекарь (B CharStats поле `me`), `patient` = пациент. Срабатывает каждый тик ухода (xp), не «один раз». Диалоговые события: `EV_HEALING_OTHER_START/FINISHED`, `EV_BEING_HEALED_START/FINISHED` (E). Дедуплицировать по паре (лекарь,пациент) и времени. |
| Подбор/переноска тел | `Character::pickupObject(self, who)` (C:34), `Character::getPickedUp(self, byWhom)` (C:35) | | Нужны для «понёс тело/добил/продал». |
| Диалог старт/конец | `DialogueWindow::show(self, dialogue: Dialogue)` (C:67), `Dialogue::say(self, line: DialogLineData)`, `Dialogue::_doActions(self, line)`, `Dialogue::endDialogue(self, definitelyTheEnd)`, `Dialogue::_endPlayerConversation(self, finished)`, `Dialogue::stopEvent(self, what: EventTriggerEnum)` (C:67-72, say=69, endDialogue=70); override `Dialogue::startConversation(self, target, talk, ev, force, defaultVal)->boolean` (C:709), `Dialogue::startPlayerConversation(self, target, talk, defaultVal)` (C:710), `Dialogue::sendEvent(self, who, what, defaultVal)` (C:711) | | `Dialogue.me` = говорящий, `conversationTarget` (hand), `currentLine`, `currentConversationType`. `startConversation`/`sendEvent` позволяют ЗАБЛОКИРОВАТЬ (return false) или заменить событие. |
| Отряд появился/пропал | `PlayerInterface::createSquad(self, newSquad: ActivePlatoon)` (C:79, только игрока); `Faction::createNewEmptyActivePlatoon(self, platoon)` (C:92); `Faction::destroyPlatoon(self, platoon)` (C:93); `ActivePlatoon::_NV_addActiveObject/_removeObject` (C:60-61); `MapScreen::addSquad/removeSquad` (GUI); `Building::setResidentSquad(self, platoon)` | | Для ВСЕХ отрядов мира «загружен/выгружен» одним событием нет. Override-конструкторы `Platoon::_CONSTRUCTOR(self, faction, squadTemplate, platoonState, position, persistent, defaultVal)->Platoon` (C:730), `ActivePlatoon::_CONSTRUCTOR` (C:731) — это ПЕРЕХВАТ создания (можно подменить), не просто уведомление; опасно. |
| Персонаж загружен/создан | `Character::_NV_init(self)` (C:46); `Character::_NV_loadFromSerialise(self, saveState: GameSaveState)` и `…PostCreationStage` (C:102-103); у нас в KMM_Conductor `_dev` бэкапе уже использовались (_dev/KMM_Conductor_v0_backup.lua:433-434) | | Выгрузки персонажа колбэком нет (искать `unload`: только `Platoon::_checkForUniqueCharactersOnUnload` как метод в B, не колбэк). Эмулировать: помеченные `hand`, пропавшие из `getCharacterUpdateList()` (B:7056). Не хранить `self` между тиками. |
| Фракционные отношения | `FactionRelations::affectRelations(self, otherFaction, eventType: integer, multiplier)` (C:65); `FactionRelations.FactionEvent` (E:1773: ATTACKED_US_*, DEFEATED_ONE_OF_US_*, KILLED_ONE_OF_US_DIRECTLY/INDIRECTLY, EXECUTED_ONE_OF_US, AIDED_US_IN_BATTLE, FIRST_AIDED_US, TAKEN_TO_BED, CAPTURED_US) | | Единый поток «что игрок сделал фракции», включая убийства, лечение, захват. Лучшая точка для town-level памяти. |
| Первая встреча с фракцией | `PlayerInterface::encounterFaction(self, faction)` (C:94) | | Один раз за фракцию. |
| Деньги | `Character::_NV_takeMoney(self, amount)` (C:36) | | Любое изменение денег, шумно. |
| Речь NPC | `Character::_NV_say(self, message)` (C:33) | | «Notes: return false suppresses remaining handlers» (C:1501). Это перехват реплики (в т.ч. нашей) — не использовать как детект. |
| Здания/города | `Building::_NV_setFaction`, `Building::_NV_onBuildingLoaded`, `Town::_NV_loadFromSerialise`, `Platoon::_NV_loadFromSerialise` (C:84-107) | | Для памяти городов. |

Чего НЕТ колбэком: убийство «кто кого» (только через `lastGuyWhoDefeatedMe`), пощада/«оставил в живых» (выводить: KO + атакующий — игрок + через N часов жив), выгрузка персонажа/отряда, клетка/кол, выстрел из арбалета, конец KO.

---

## 2. Идентификация NPC между загрузками

Что есть (все доступны из Lua):

- `RootObject.handle` / `Character:getHandle()` (B:11780+), тип `hand` (B:7408): `toString()`, `fromString(str)`, `getCharacter()`, `getPlatoon()`, `getTown()`, `isValid()`, `isNull()`. Хэндл — runtime-значение движка; сохраняется в сейвах движком через `GameData:storeHandle(h, name, redirect)` / `getHandle(name)` (B:6652+). Что строка `toString()` стабильна между загрузками — в документации НЕ сказано, считать непроверенным.
- `RootObject:getInstanceID()` -> `InstanceID{uid: string, baseIndex, modIndex, modified}` (B:11799, B:7893). `GameSaveState.instanceID: string` (B:6939+) — тот же идентификатор в сейве. Это единственный постоянный идентификатор экземпляра; `_NV_loadFromSerialisePostCreationStage(self, saveState)` даёт `saveState.instanceID` — точка «узнал своего».
- `Character:getIDForMemoryTagging()` -> `hand` (B:3360) — ваниль использует для долговременной памяти.
- `RootObject.data` / `getGameData()` -> `GameData`: `.name`, `.stringID` (шаблон персонажа; у уникальных NPC = личность, у случайных — общий шаблон «Bandit»; B:6652).
- `Platoon.stringID`, `Platoon:getPlatoonStringID()` (B:10650), `Character:getPlatoon()`, `ActivePlatoon.squadleader`, `Platoon:getSquadLeader_theRealOne()`.
- Имя: `Character:getName()` (B:3457), `setName(name)` (B:3297-3298), `getDisplayName()` (B:2984). `setName` на персонаже у нас уже используется ×10.
- Память ванили: `Character:rememberCharacter(who, mem)` (B:3450, два перегруза `CharacterPerceptionTags_ShortTerm`/`_LongTerm`), `getCharacterMemoryTag(who, mem)` (B:3466), `haveMetBefore(c)` (B:3359), `lastSeenInHoursAgo(c)` (B:3358). `LT_*` (E:519): `LT_MY_INTRUDER 1, LT_MY_LIFESAVER 2, LT_FREED_ME 3, LT_STOLE_FROM_ME 4, LT_MY_CAPTOR 5, LT_FRIENDLY_AQUAINTANCE 6, LT_DEFEATED_MY_SQUAD_ONCE 7, LT_SQUAD_LOST_TO_ME_ONCE 8, LT_KILLED_MY_FRIEND 9, LT_I_SCREWED_THIS_GUY 10`. Это ровно наши категории памяти в ванильном виде. Вердикты: `ILoveThisGuyBecauseOfStuffThatHappened(who)` (B:3265), `IHateThisGuyBecauseOfStuffThatHappened` (B:3266), `shouldIHelpThisGuy` (B:3263), `shouldIScrewThisGuyOver` (B:3264). Диалоговые условия `DC_I_LOVE_THIS_GUY`/`DC_I_HATE_THIS_GUY`/`DC_I_SHOULD_HELP_THIS_GUY`/`DC_I_SHOULD_SCREW_THIS_GUY_OVER`/`DC_HAS_TAG`/`DC_MET_TARGET_BEFORE` (E:1559) читают тот же слой. Memory живёт в `Character._myMemory` (lightuserdata, B:3065), живёт ли она в сейве — ваниль сохраняет (иначе не работало бы в игре), но по доке не подтверждено.

Как найти заново, когда загружен: перебрать `getGameWorld():getCharacterUpdateList()` (B:7056; у нас ×13) и сравнить `getInstanceID().uid`, либо `getCharactersWithinSphere(pos, farR, nearR, always, maxFar, maxNear, skip)` (B:7054) вокруг игрока. Для незагруженных — найти нельзя (подтверждено в docs/KENSHILUA_API.md): «только загруженные»; можно ждать `_NV_init`/`_NV_loadFromSerialisePostCreationStage` и сверять с таблицей помеченных. Активировать всё принудительно (`FactionManager:activateUnloadedPlatoons()`) — тяжело, не делать.

Рекомендация идентификатора: запись нéмезиса = `{uid=InstanceID.uid, tpl=data.stringID, name, platoon=Platoon.stringID, faction=stringID, deed, place, day}`; сверка по uid, запасная — tpl+platoon, запасная — имя. Но случайный разбойник из роуминг-отряда может навсегда исчезнуть (отряд растворился) — тогда «возвращение» делаем созданием НОВОГО персонажа из шаблона с тем же именем (см. п.3).

---

## 3. Как заставлять мир действовать

| Что | API | Заметки |
|---|---|---|
| Создать отряд рядом | `getGameWorld().theFactory:createRandomSquad(faction, position, homeTown, maxnum, home, squad: GameData, ownr, maparea, _activePlatoon, permanentsquad, AItarget: hand, targetTown, sizeMultiplier, squadType, isJustARefresh) -> Platoon` (B:11961) | Уже используем (KMM_Conductor.lua:2572: `…(fobj, spawn, nil, n, nil, nil, nil, nil, nil, false, pc:getHandle(), nil, 1.0, 2, false)` — отряд идёт на игрока: `AItarget`=хэндл игрока, `squadType=2`=SQ_ROAMING, E:1682). Параметр `squad` = `SQUAD_TEMPLATE` GameData (itemType 52) — можно подставить конкретный шаблон (напр. «охотники за головами»). Это даёт группу, а не конкретную личность. |
| Создать одного | `theFactory:createRandomCharacter(faction, position, owner: RootObjectContainer, characterTemplate: GameData, home: Building, age) -> RootObject` (B:11952); `theFactory:create(data, position, isFromActiveLevelMod, owner: Faction, rotation, callbackObject, certainContainer, state, invisible, homeBuilding, age) -> RootObjectBase` (B:11939) | Для немезиса: `characterTemplate` = тот же `GameData` (character), потом `setName`, `setFaction`, оборудование. Внешность оригинала: `Character:getAppearanceData() -> GameDataCopyStandalone` / `setAppearanceData(data)` (B:3317-3318) — можно скопировать лицо при возвращении, пока оригинал загружен; в сейв Lua это не положить (userdata). Не пробовали. |
| Создать предмет/дать | `theFactory:createItem(gd, handle, weaponMesh, matData, levelOverride, flagUniform) -> Item` (B:11957; у нас так: KMM_Conductor.lua:2529), `Character:giveItem(item, dropOnFail, destroyOnFail)` (B:3246), `Inventory:addItem(item, quantity, dropOnFail, destroyOnFail)` | Деньги: `Character:takeMoney(n: integer) -> boolean` (B:3174; принимает ли отрицательное n — не проверено) и `Inventory:takeMoney(val)`; отдельного `giveMoney` нет. Подарок-«благодарность» = createItem + giveItem. |
| Переименовать | `Character:setName(name)` (B:3297), `RootObject:setName` | Имя рисуется в нейм-теге (`setNameTagVisible(value)`, B:3298). Эпитет: «Имя «Кривой»». Проверять, что имя не ломает привязку диалогов (диалоги идут по GameData, не по имени). |
| Приказы ИИ | `Character:addJob(t: TaskType, subject: RootObject, shift, addDontClear, location: Vector3)` (B:3277), `addGoal(t, subject)`, `addOrder(dest: Building, t, subject, shift, clear, location)` (B), `setDestination(pos, shift)` (B:3319), `attackTarget(who: Character)` (B:3328), `removeJob`, `clearAllAIGoals()`, `reThinkCurrentAIAction()`; `TaskType` (E:1025+): `MELEE_ATTACK=4`, `CHOOSE_ENEMY_AND_ATTACK=9`, `ATTACK_ENEMIES=16`, `STAY_CLOSE_TO_TARGET=31`, `RUN_AWAY=35`, `CHASE=46`, `FOLLOW_PLAYER_ORDER=44`, `BODYGUARD=45`, `GET_NEAR_TO=40`, `TRAVEL_TO_TARGET_TOWN=53`, `DEFEAT_SQUAD=101`, `FIND_AND_RESCUE=105`, `LOOT_TARGET=26`, `FIRST_AID_ORDER=25` | `attackTarget` и `addJob(CHASE/MELEE_ATTACK)` у нас в деле лишь в виде `attackTarget` ×2. Для отряда: `ActivePlatoon.currentGoal: Tasker`, `Platoon:reprocessTask(t)`; в `createRandomSquad` цель задаётся аргументом `AItarget` (hand). Отряды NPC игроком не управляются; задачи живого персонажа ИИ может «перебить» сам. |
| Фракция/отношения | `Character:setFaction(faction, activePlatoon)` (B:3337), `faction.relations:setRelation(who, setTo)` (B:5887), `affectRelations(p, e: FactionEvent, mult)` / `(p, amount, mult)` (B:5888), `affectReputation(p, amount)` (B:5893), `affectTrust`, `declareWar(p)` (B:5892), `setNoLongerEnemies`; на персонаже: `clearTempEnemyStatus`, `rememberCharacter(who, LT_*)` | `setRelation` у нас ×7. Временные союзники/враги также через диалоговые действия `DA_FLAG_TEMP_ALLY/ENEMY` (E:671). Фракция по имени: `FactionManager:getFactionByStringID(sid)` (B:5842), `getFactionByName` (B:5841), `getAllFactions` (B:5852). Игрок: `getGameWorld().player:getFaction()` (B:PlayerInterface). |
| Заставить говорить | `Character:say(s)` (B:3244; у нас ×3), `Character:sayALine(line: string, force: boolean)` (B:3322), `say_WithARepeatLimiter(s)`, `Character:sendDialogEvent(target, what: EventTriggerEnum)` (B:3321), `sendDialogEventOverride(target, what, forceRepeat)` | `say`/`sayALine` — произвольная строка в речевом пузыре, БЕЗ диалогового окна: самый дешёвый способ «NPC вспомнил поступок». Кириллица/шрифт — проверять. |
| Динамический диалог | см. п. «Диалоги» ниже | |
| Уведомление игроку | `getGameWorld():showPlayerAMessage(message, queued)`, `showPlayerAMessage_withLog(message, queued)` (B:7090; у нас ×4), `showPlayerAMessageD`, `playNotification(sound)` (B:7093), `GameWorld:sysMessage(m: SysMessage)` (B), `getGameWorld()…` плавающая метка `ForgottenGUI:createScreenLabel(text, textSize, risingSpeed)` (B:6513), `createScreenLabelD(text, time)`, MyGUI-окна (MyGUIReference.md) | `showPlayerAMessage_withLog` — сообщение сверху + в журнал. Для «слух о вас» — хватает. |
| Телепорт/позиция | `Character:teleport(moveBy[, rot])` (B:3459; `moveBy` — смещение, а не координата), `relocationTeleport(moveBy)`, `getPosition()`, `GameWorld:findValidSpawnPos(pos, centerArea)` (B:7014) | Для спавна «рядом, но не в кадре» уже есть наш код (KMM_Conductor ~2540-2570). |

### Диалоги (DialogueScriptingBridge, D)

- Lua из диалога: только через FCS Extended: в строке диалога ссылка «run lua script» на объект `LUA_SCRIPT` (itemType 322, E:859), у которого поле `file` = путь внутри `scripts/` мода (D:39-47, 57-89). Скрипт получает глобалы `currentDialogue: Dialogue` и `currentDialogueLine: DialogLineData` на время выполнения, потом nil (D:160-167, 228). Вызывается из `Dialogue::_doActions` (D:9) — то есть Lua выполняет ЭФФЕКТЫ (действия) строки. Требует, чтобы строки были в `.mod` (редактирование FCS-базы, наш пайплайн собирает моды — нужно проверить, умеет ли генератор писать ссылки типа 322; в D указан только путь через FCS Extended GUI).
- Динамические условия: override `Dialogue::_checkCondition(self, conditionName: DialogConditionEnum, compareBy: ComparisonEnum, val, target: Character, actualConversationTarget: Character, defaultVal) -> boolean` (C:708) — можно подменить ответ на любое стандартное условие (напр. `DC_HAS_TAG`, `DC_MET_TARGET_BEFORE`, `DC_REPUTATION`, `DC_RELATIONS`, `DC_PERSONALITY_TAG`), то есть прицепить собственную логику «помнит ли он обиду». Новые значения `DialogConditionEnum` Lua не добавит — переиспользуем существующие условия, чья ванильная семантика нам не нужна в данной строке, либо хук на `Dialogue::startConversation` (C:709).
- Динамический текст: `Dialogue:say(_text: string, line: DialogLineData)` (B:5453, перегрузка [2] — свой текст вместо текста строки), `DialogueWindow:setNPCText(text)` (B:5551; колбэк `DialogueWindow::setNPCText` C:535 — после установки), поле `Dialogue.npcReplyText` (B:5376, RW), `Dialogue:getWordSwap(key, target, a3, line) -> string` (B:5392; WORD_SWAP — шаблонные подстановки в FCS, значения подменяются `Dialogue::getWordSwap`? — отдельного колбэка нет, значение берётся в движке). Практичный путь: на `Dialogue::say`/`DialogueWindow::show` проверить `dialogue.me`/`conversationTarget` и, если это наш помеченный NPC, вызвать `window:setNPCText(строка_с_делом_и_местом)`. Ответы игрока (`setResponses`) — `lightuserdata`, Lua не умеет собирать кнопки (C:3831: «responses is borrowed lightuserdata»); значит варианты ответа остаются FCS-ные.
- `Dialogue:runCustomDialog(dialog: GameData)` (B:5411) и `makeAnnouncement(dat: GameData)` (B:5417) запускают заранее существующий GameData-диалог. Создать диалог «на лету» через `GameDataContainer:createNewData(type, forceID, name)` (B:6762+ раздел) теоретически можно (`itemType.DIALOGUE=18`, `DIALOGUE_LINE=19`) — НЕ проверено, риск сейва.
- `EventTriggerEnum` (E:1478) — наборы «барков» (`EV_BETRAYAL`, `EV_BOUNTY_SPOTTED`, `EV_ESCAPED_EX_SLAVE_SPOTTED`, `EV_ENTER_TOWN` …). `Character:sendDialogEvent(target, EV_*)` заставит ванильную реплику; у нас для памяти можно переиспользовать `EV_BOUNTY_SPOTTED` (охранник узнал) и т.п. + `setNPCText` для подмены строки.

---

## 4. Хранение данных

- Сейв-хранилище мира: `gameData.sdata[KEY] = string` в обработчике `PlayerInterface::serialise(self, gameData: GameData)` и чтение в `PlayerInterface::loadFromSerialise(self, gameData)` (C:99-100). Тип поля `sdata` в B — `unknown` (B:6652+ GameData), на деле строковая карта.
- У нас: KMM_Conductor пишет `gameData.sdata[STATE_KEY] = serialize(S)` (KMM_Conductor.lua:4450), читает тремя способами и имеет резервную копию в файл `C:/KenshiModMap/state/<имя сейва>.kmmstate` + `last.kmmstate` (4356-4475). Записано: «в сессии 2026-11-13 21:00:40 загрузка сейва дала no v1 state, хотя ключ в quick.save есть (600 КБ)» — то есть чтение `sdata` в игре ненадёжно; для Rumors то же (`KMM_Rumors.lua:587-609`, файл `.rumors`). Имя сейва для файла: `SaveManager.getSingleton().name/currentGame` (B:12068).
- Резерв: любой Lua в `serialise` может писать файлы (`io.open` в функции, не на верхнем уровне).
- Данные на отдельном персонаже: ванильные — память `LT_*`, имя, `Character:serialise(container, refList, offset) -> GameSaveState` и хуки `Character::_NV_serialise(self, container: GameDataContainer, refList: GameData)` (C:101) / `_NV_loadFromSerialise(self, saveState)` (C:102) — теоретически можно дописать своё состояние в `GameSaveState.states` (`createState(type)/addState/getState`, B:6939+), но: ключ-ограничения типа состояний, риск ломать сейв, непроверено. Основной путь — таблица в `sdata` мира, ключ = `InstanceID.uid`.
- Ограничения Lua в KenshiLua: у каждого скрипта своя песочница, общее — через `_G.X = _G.X or {}` (D:124-125); `require`/`dofile` в пределах `scripts/` мода (D:130-156); у нас лимит 200 локалей на главный чанк (KMM_Conductor.lua:4358).

---

## 5. 25 непользуемых привязок/колбэков с наибольшим эффектом «живости»

1. `FactionRelations::affectRelations` (C:65) — единый поток событий «что игрок сделал фракции»: города/охрана запоминают подвиги, источник «славы/позора».
2. `BountyManager::notifyCrimeWitnessed` (C:64) — свидетель + жертва + тип преступления: привязывает дело к месту и фракции.
3. `MedicalSystem::knockout` (C:91) — момент нокаута, вход в «пощадил/оставил».
4. `Character::changeSlaveOwner` / `setChainedMode` (C:95-96) — порабощение/освобождение для `LT_FREED_ME`/`LT_MY_CAPTOR`.
5. `Character:rememberCharacter(who, LT_*)` + `getCharacterMemoryTag` (B:3450, 3466) — ванильная долговременная память: помечаем «его обидели»/«спас», остальное делают ванильные реплики и ИИ.
6. `Character:ILoveThisGuyBecauseOfStuffThatHappened` / `IHateThisGuy…` / `shouldIHelpThisGuy` (B:3263-3266) — готовые вердикты: решить, придёт ли друг на помощь/враг на месть.
7. `Dialogue::_checkCondition` override (C:708) — подмена условий диалога («помнит ли»), основа диалогов с учётом дела.
8. `DialogueWindow:setNPCText` / `Dialogue:say(text, line)` (B:5551, 5453) — строка с делом и местом.
9. `Character:sayALine(line, force)` (B:3322) — NPC вслух вспоминает дело без окна диалога.
10. `Dialogue::startConversation` override (C:709) — заблокировать/подменить диалог для особых NPC (охранник не говорит с известным убийцей).
11. `Item::_NV_notifyTheftFrom` + `Character::_NV_ImStealingDoYouNotice` (C:63, 44) — кражи как поступок.
12. `Character::_NV_isItOkForMeToLoot` override (C:696) — NPC-мародёры отказываются грабить «друзей»/грабят «должников».
13. `Platoon::iBuyStolenGoods` / `iBuyIllegalGoods` override (C:700-701) — торговцы берут/не берут краденое от «известных».
14. `InventoryItemBase::getValueSingle(isPlayer, defaultVal)` override (C:705) — цены от репутации города.
15. `Faction::chooseARace(character, squadTemplate, defaultVal)` override (C:706) — состав спавна в зависимости от памяти (нарративные патрули).
16. `CharStats::getStat(statType, unmodified, defaultVal)` override (C:699) — «закалённый» нéмезис: эпитет даёт прибавку статов (одна точка, шумно — только для помеченных).
17. `MedicalSystem::canGetUpWakeUp` override (C:717) — лежащий противник не встаёт/встаёт позже; скрипты «оставили умирать».
18. `PlayerInterface::encounterFaction` (C:94) — первая встреча фракции: рассылка слухов.
19. `Character::_NV_setFaction` (C:41) — вербовка/увольнение: «бросил рекрута», бывшие товарищи.
20. `ActivePlatoon::_NV_removeObject` (C:61) — выбытие из отряда игрока (брошенный компаньон).
21. `Platoon::_CONSTRUCTOR` override (C:730) / `createRandomSquad.squad` — подмена состава отряда на «отряд мстителей» без спавна поверх.
22. `Character::_NV_loadFromSerialisePostCreationStage` (C:103) — «узнал своего» по `saveState.instanceID`; ожидающий нéмезис получает приказ при появлении.
23. `GameWorld:getCharactersWithinSphere` + `Character:getCurrentTownLocation` (B:7054, 3242) — «кто видит игрока в городе» для реакции охраны/лавочников.
24. `TownBase.alarmState` (B:13551+) и `Town:getAlarmMgr` — тревога города как следствие дурной славы; чтение/запись состояния.
25. `BountyManager:unfairAddToBounty(enforcer, amount)` / `clearBounty` / `getPercievedBounty(whosLooking)` (B:2423-2429) — слава/позор как награда за голову; охотники за головами получают цель.

Запасные: `Character:getKidnappingChance(victim)` (B:3260), `isPrisonerFreeToGo` (B:3355), `lastSeenInHoursAgo` (B:3358), `haveMetBefore` (B:3359), `Character:separateIntoMyOwnSquad(permanent)` (B:3205), `Character:getAppearanceData/setAppearanceData` (B:3317-3318), `Dialogue:runCustomDialog` (B:5411), `EventTriggerEnum` бары, `GameWorld:getTimeStamp_inGameHours` (B:7113, у нас в деле).

---

## 6. Оценка покрытия

Считал скриптом `tools/engine_api_usage.py` по B и по нашему Lua (`build/KMM_*/scripts/**/*.lua`). Метод грубый: по совпадению имён после `.`/`:`, это верхняя граница (имена вроде `getName`, `update` считаются, даже если вызваны не у этого класса).

| Метрика | Значение |
|---|---|
| Классов в B | 419; членов (поля+методы) 9108; различных имён 7006 |
| Классы, относящиеся к миру (без GUI/анимации/рендера/Havok/звука/MyGUI и т.п., эвристика по имени) | 233 класса, 6119 членов, 4802 различных имён (67% всех членов; число зависит от эвристики, `tools/engine_api_usage.py`) |
| Из них мы используем (по имени, верхняя граница) | 238 имён = ~5% от мира, ~3,4% от всех 7006. По вашей оценке ~117 из ~4245 = 2,8%; обе оценки согласуются: реально 2,5-5% |
| Лучшее покрытие по классам | RootObjectBase 17/29, Inventory 16/74, Platoon 16/83, GameWorld 12/125, MedicalSystem 13/103, Ownerships 10/32 |
| Почти не тронуты | Character 50/401, AI 11/402, CharStats 6/234, Dialogue 7/96, DialogLineData 6/71, PlayerInterface 5/124, FactionManager 1/20, ZoneManager 0/80, CharacterHuman 0/8 |
| Колбэки | 663 notification + 212 override = 875. Из них не-GUI по имени класса: 132 notification + 113 override (в сумме ~245 «мировых», ~28%). Мы используем 4 (1,6% от мировых, 0,5% от всех). |

Вывод: мировая симуляция в KenshiLua покрыта нами на несколько процентов; для задачи «память игрока» нужны не десятки, а около 10-15 привязок (раздел 5, п. 1-12, 22, 25): они уже есть в доке, но не использованы.

---

## Риски и ограничения (коротко)

1. Невыгруженных NPC изменить нельзя (docs/KENSHILUA_API.md). Нéмезис «возвращается» либо если остался загруженным/встретился, либо создаётся заново из шаблона с тем же именем.
2. `sdata` в игре читался ненадёжно (запись 2026-11-13) — держать резервную копию в файле.
3. `_NV_`-хуки не описаны в доках; подтверждено в игре только `hitByMeleeAttack`. Новые хуки сначала логировать, не навешивать логику.
4. Динамический текст: можно подменить реплику NPC (`setNPCText`, `say(text,line)`); варианты ответов игрока Lua не строит.
5. Кириллица в `say/sayALine/setNPCText` и именах — не проверена шрифтом игры.
6. Колбэки `_CONSTRUCTOR` — это override, который может подменить создаваемый объект: не трогать без нужды.
7. Любой handler на частых событиях (`hitByMeleeAttack`, `_NV_takeMoney`, `xpFirstAid`, Inventory callbacks) должен быть O(1) и в `guarded`.
