# ЛЮДИ: персонаж, статы, тело, медицина, бой, восприятие (ядро Kenshi 1.0.65)

Домен: `Character` / `CharacterHuman` / `CharacterAnimal`, `CharStats`, `CharBody`, `MedicalSystem`, `Damages`, `combat/*`, `SensoryData`, `CharMovement`, `RaceData`, `GlobalConstants` (числа XP и медицины).
Ссылки: `Файл.h:N` — строка заголовка в `tools/ref/KenshiLib/Include/kenshi/`; `B:N` — BindingsReference.md, `C:N` — CallbacksReference.md, `E:N` — EnumsReference.md (каталог `...\workshop\content\233860\3817000612\docs\`). RVA взяты из комментариев заголовков, это цели для `KenshiLib::AddHook` в `tools/cpp/kmm_native`.
Статусы: ✓код — есть в заголовке или биндинге; ? — догадка или поведение не проверено. **✓игра в этом домене пока нет ни одного факта**: ни один вызов ниже не видели в логе живой игры.
Lua: все энумы — обычные целые числа (B:11). Перегрузки помечены `[1]`/`[2]`. Если у перегрузок одинаковое число аргументов, выбор по типу энума невозможен (см. «Память»).

## Сводная таблица

| механика | Lua | плагин | наше использование |
|---|---|---|---|
| Значение стата: чтение/запись | `CharStats` поля RW (B:3932), `getStat`, `getStatRef` (B:4168) | — | Tempo: `moveSpeed`, `calculateHungerMult` |
| Перехват значения стата | override `CharStats::getStat` (C:699) | `getStat` 0x883310 | нет |
| Начислить XP по-ванильному | `xpStat_eventBased(st, amount)` B:4073, `xpGeneral`, `xpTraining`, `xpMelee` | — | нет |
| Узнать о росте XP | notify: `xpStat_eventBased`, `xpDodgeEvent`, `xpFirstAid`, `xpStealth`, `xpRunning`, `xpLockpicking`, `xpEngineering`, `xpToughness_*` (C:50–77) | `xpMelee`, `xpGeneral`, `xpTraining`, `xpMassCombat`, `xpStat_timeBased` (только хук) | Nemesis: `xpFirstAid`, `xpLockpicking` |
| Числа XP и медицины (EXPERIENCE_*, XP_HIT_*, KNOCKOUT_*) | тип `GlobalConstants` RW (B:7219); как получить экземпляр — ? | `con` (Globals.h:30) | нет (Tempo ссылается на FCS CONSTANTS) |
| Голод | `MedicalSystem.hunger/fed` RW, `isHungerKO`, `calculateHungerMult` | — | Tempo (hunger/fed), Conductor, Nemesis, Siege |
| Еда | notify `Character::eatItem` (C:37), override `Inventory::getBestFoodItem` | — | Tempo (eatItem) |
| Кровь, раны, части тела | `blood`, `getPart[1..3]` → `HealthPartStatus` (flesh, bandaging RW) | `addWound`, `applyDamage`, `getHealthStatModifier` | Tempo (`blood`) |
| Нокаут, бессознание | `knockout(skill01)` B:9441, `knockoutForceTimer` B:9442, поля `knockoutTimer`, `unconcious`; notify `knockout` (C:91); override `canGetUpWakeUp` (C:717) | — | Self: пишет `knockoutTimer` + `unconcious` напрямую |
| Смерть | `isDead`, `declareDead`; notify `Character::declareDead` (C:30) | — | Conductor, Traces, Tempo и ещё 10 модулей (`isDead`) |
| Увечья, протезы | `amputate`, `crushLimb`, `getLimbState` (возвращает void — сломан), notify `amputate` | `setRobotLimbItem` | Veterans: только через шаблоны FCS, рантайм-вызовов нет |
| Лечение | `applyFirstAid/applyDoctoring/applyRigging` — **в биндинге без аргументов, void** (B:9486) | 0x64D080 / 0x649280 | нет |
| Бой: состояние, цель | `isInCombatMode`, `getAttackTarget`, `attackTarget`, `endCombatMode`, `getCombatClass` | `CombatClassAI::chooseAttackTarget` 0x666760 | Gov, Self, Town (`isInCombatMode`), Traces (`attackTarget`) |
| Удар по персонажу | notify `Character::_NV_hitByMeleeAttack` (C:38) | `hitByMeleeAttack` 0x438D70, `iShotYou` 0x439510 | Conductor hit_hook, Nemesis |
| Выбор приёма | override `CharStats::chooseAttack` (C:698) | — | нет |
| Восприятие | `getSensoryData()` → `SensoryData` (B:12281), `SeenSomeone` | `SpottingPeopleMgr` | нет |
| Кража, скупка | notify `_NV_ImStealingDoYouNotice` (C:44), `_NV_smugglingTradeCheck`; override `getFencingSuccessChance`, `_NV_isItOkForMeToLoot`, `Platoon::iBuyStolenGoods` | — | нет |
| Преступление замечено | notify `BountyManager::notifyCrimeWitnessed` (C:64) | — | Deeds (свидетели Y1), Outlaws B1 (цена дела, рост награды) |
| Цепи, рабство, тюрьма | `setChainedMode` B:3481, `changeSlaveOwner` B:3458, `isSlave`, `setPrisonMode`; notify `setChainedMode` (C:96), `changeSlaveOwner` | — | Conductor/Nemesis (`setChainedMode`), Tempo/Elite/Traces (`getMySlaveOwner`, `isSlave`) |
| Память о персонаже | `rememberCharacter[1/2]` B:3449–3450, `getCharacterMemoryTag[1/2]` B:3466–3467 — **перегрузки неразличимы** | 0x673D20 (ST) / 0x6732A0 (LT) | Nemesis `N.remember` под probe_call |
| Встречались ли | `haveMetBefore` B:3359, `lastSeenInHoursAgo` B:3358 | — | нет |
| Реплики | `say`, `say_WithARepeatLimiter`, `sayALine(line, force)` B:3322, `sendDialogEvent` B:3321; notify `_NV_say` (C:33) | — | Nemesis (`sayALine`) |
| Условия диалога | override `Dialogue::_checkCondition` (C:708) | — | нет |
| Раса | `RaceData` RW (B:11273): healRate, bleedRate, hungerRate, statMods | — | Self, Traces (`getRace`) |
| Скорость | `CharStats.moveSpeed`, `CharMovement:setMaxSpeed`; override `CharMovement::isRunning/isRunningAway` | — | Tempo (`moveSpeed`) |

---

## A. Статы и прокачка

### Хранилище статов
Каждый навык хранится как float-поле `CharStats`. Эффективное значение = база × множители: раса (`RaceData::getStatMod`, `statMods`), здоровье/голод/темнота/погода/протезы/снаряжение (`MedicalSystem::getHealthStatModifier`) и бонусы снаряжения.
- Точки ядра: поля `_strength, _dexterity, _toughness, perception, _athletics, medic, massCombat, stealth, thieving, lockpicking, assassin, … polearms` (CharStats.h:91–135); `getStat(what, unmodified)` CharStats.h:81 0x883310; `getStatRef` :80; `getStatMultiplier` :83; `getOverallSkillLevel_0_100` :79 0x8838A0; `setEquipmentStatBonuses` :78; `Character::recalculateTotalEquipmentSkillBonus` Character.h:635; `MedicalSystem::getHealthStatModifier(stat, _hunger, _wounds, _darkness, robotParts, weather, gear)` MedicalSystem.h:218 0x645060 (в Lua нет).
- Энум `StatsEnumerated` (E:1407): STAT_STRENGTH=1 … STAT_SMITHING_BOW=38. Значения ≥40 — «производные» (`_KnockoutTime=50`, `_MaxRunSpeed=53`, `_Mining=61`, `_BuildingRate=59` …): что их можно читать через `getStat`, ✓код; что они двигают — ?.
- Lua: да, все поля RW (B:3932), override `CharStats::getStat(statType, unmodified, defaultVal) -> number` (C:699). `xp` и `freeAttributePoints` (CharStats.h:268–269) — ? похоже на рудименты, очков атрибутов в Kenshi нет.
- Наше использование: Tempo пишет `moveSpeed` и читает `calculateHungerMult`. Сами навыки не трогаем.
- Рычаги: (1) override `getStat` даёт ситуативный стат без записи в сейв (страх перед немезисом: −защита, только когда цель — он). Это горячий путь, нужен кэш и быстрый выход. (2) Запись в поле навыка остаётся в сейве навсегда, поэтому только как награда за событие, а не как бафф.

### XP-ядро (как растёт навык)
Все пути XP сходятся в несколько функций кластера 0x8C46D0–0x8C5C30. Прирост убывает с уровнем: пара `EXPERIENCE_GAIN_1/_99` + `EXPERIENCE_CURVE` (GlobalConstants.h:86–92). В боевом XP учитывается разница навыков с противником: `SKILL_DIFFERENCE_XP_RATIO_MULT_BONUS/PENALTY` (:49–50) и `getSkillDifferenceRatio(mine, his)` CharStats.h:189 0x8C47F0.
- Точки ядра: `xpStat_eventBased(st, amount)` CharStats.h:88 0x8C5B60 — разовый прирост; `xpStat_timeBased(st)` :87 0x8C5AA0; `xpGeneral(time, mult, what)` :224 0x8C4C80 — ? его вызывают рабочие навыки (труд, ферма, кухня, кузня, наука); `xpTraining(time, mult, &stat, upperLimit, what)` :223 0x8C4D40 — тренажёры с потолком `upperLimit`.
- Lua: вызывать можно всё; в Lua `xpTraining` возвращает новое значение вместо ссылки (B:4178). Notify есть только у `xpStat_eventBased(statType, amount)` (C:76). У `xpGeneral`/`xpTraining`/`xpStat_timeBased` колбэков нет, их ловит только плагин.
- Наше использование: нет.
- Рычаги: (1) `xpStat_eventBased(st, amount)` из Lua — ванильная награда «за встречу» с родной кривой убывания. Смысл `amount` (сырые очки XP или доля уровня) — ?, сначала проверить на одном NPC: стат до и после. (2) Хук плагина на `xpTraining` (×0.5) и `xpMelee` (×1.5 против именных соперников). Тогда прокачка через встречи выгоднее манекена; цена — 2 detour-а.

### Боевой XP
- `xpMelee(DeadTimeState what, Character* target, const Damages&)` CharStats.h:209 0x8C51D0. Исход удара `DeadTimeState`: ATTACK_HIT, ATTACK_WAS_BLOCKED, BLOCKED_IT, WAS_HIT, ATTACK_MISSED … (:190–199). Веса `XP_HIT_THEM`, `XP_HIT_ME`, `XP_BLOCKED_THEM`, `XP_BLOCKED_ME` (GlobalConstants.h:51–54). Растут атака/защита/оружейный навык, сила получает `_StrengthXPRateCombat` и `weaponWeightXPMult` (:258, `calculateWeaponWeightXPMult` :243).
- `xpDodgeEvent(enemySkill, successful)` :89 0x8C4BB0 — уклонение зависит от навыка врага. Notify (C:77).
- `xpMassCombat()` :220 0x8C46D0 — ? растёт, когда атакующих несколько (`getAllAttackersCount`).
- Lua: вызвать `xpMelee` можно (B:4171), колбэка нет.
- Наше использование: нет.
- Рычаги: **сильный противник сам даёт больше XP** (skill difference). Значит, нелинейный рост через конкурентов уже есть в ядре. Наша часть — выставлять игроку соперников чуть сильнее его (по `getOverallSkillLevel_0_100`), а не плодить свой XP.

### Тело: сила, ловкость, живучесть, атлетика
- `xpToughness_RagdollEvent/GetUpEvent/PunchSomething(mat)` CharStats.h:210–212 (notify C:52–54). Множитель `MedicalSystem::getToughnessXpBonus` MedicalSystem.h:216 0x8C4790 — ? чем сильнее ранен, тем больше XP. Константа `XP_TOUGHNESS`.
- `xpRunning(time, speed)` :214 (notify), `calculateAthleticsXPMult(speed)` :225, `calculateStrengthXPMultFromWalking` :226 — сила растёт от ходьбы с перегрузом (`STRENGTH_XP_RATE_FROM_WALKING`, `ENCUMBRANCE_BASE`).
- Lua: да. Наше использование: нет.
- Рычаги: торговый караван с тяжёлым грузом уже качает силу (ваниль). Связать вес груза с маршрутами экономики — без своего кода XP.

### Медик, вор, скрытность, работа
- `xpFirstAid(patient, time, medicStat)` CharStats.h:213 0x8C4980, веса `XP_MEDIC_1/_99`, `XP_FIRSTAID` (GlobalConstants.h:37–38, 55). Notify (C:50).
- `xpStealth(time, enemiesAbout, seen, isMoving)` :215 — XP идёт только если рядом враги. `xpStealthHearCheckEvent(enemiesAbout, trespassing, seen)` :216 — бонус за проникновение. `stealthXPTooManyCooksPenalty` :219 — штраф, если крадутся многие. Notify `xpStealth`.
- `xpLockpicking(lockLevel, success)` :222 (notify), `xpEngineering(time)` :221 (notify). Шанс взлома — `Character::getLockpickChance(DoorLock*)` Character.h:394, минимум `LOCKPICK_CHANCE_MINIMUM`.
- Воровство: прямого `xpThieving` нет. ? растёт через `xpStat_eventBased(STAT_THIEVING)` при краже.
- Наше использование: Nemesis слушает `xpFirstAid` (вылечил чужого → долг) и `xpLockpicking` (освободил → долг).
- Рычаги: notify-колбэки `xpFirstAid`/`xpStealth`/`xpLockpicking` — дешёвый датчик «что персонаж реально сделал». На них вешать память мира (LT_MY_LIFESAVER и т. п.), а не собственный счётчик.

### Личность (AI-характер)
- `warriorSpirit, derivedSpirit, aggression, goodness, evilness` CharStats.h:167–171; `STUBBOURNESS, PROFESSIONALNESS, HOLDING_POSITION, IMMEDIACY, IMMEDIACY_MAX_RANGE, MANLINESS, MURDEROUS` :202–208.
- Lua: RW. Остаются ли в сейве — ? (часть, видимо, берётся из GameData при init).
- Наше использование: `aggression` в Conductor и Diplo — это поле фракции/данных, не `CharStats` (?).
- Рычаги: проигравший ветеран становится осторожнее (`STUBBOURNESS↓`), убийца — `MURDEROUS↑`. Дешёвая запись на загруженном NPC; сначала проверить сохранение в сейве.

## B. Тело и медицина

### Части тела и раны
`MedicalSystem::status/anatomy` — набор `HealthPartStatus` (голова, торс, руки, ноги). У части есть `flesh` (здоровье), `fleshStun`, `bandaging`, `juryRigging`, `wearDamage` (у роботов), `_maxHealth`, `HPMult`, флаги `fatal/collapses/selfHealing`.
- Точки ядра: MedicalSystem.h:128–178; `getPart(limb|index|type,side)` :180–182; `addWound(...)` :193 и `applyDamage(part, dmg, …)` :299 — в Lua нет; `getWorstDamage`, `worstDamage` :222; `getOverallHealthRating` :264; `isProbablyDying` :262; `scoreFirstAidNeed` :118.
- Lua: `getPart[1..3]` (B:~9480), поля части RW (B:9490). `addWound` в UnboundReference.
- Наше использование: нет.
- Рычаги: шрам или старая рана как след встречи (`flesh` ниже максимума у ветерана при спавне) — ванильный вид «он уже бывал в бою».

### Кровь
- `blood`, `getMaxBlood`, `currentBleedRate`, `extraBloodLossFromBodyparts`, `pointOfCollapseBloodloss`, `isInBloodlossTrauma`, `bloodlossUpdate` (MedicalSystem.h:200–203, 212, 270, 297). Раса: `bleedRate`, `healRate`, `originalBloodMin/Max` (RaceData.h:34–37). Константы `BLEED_RATE_MULTIPLIER`, `BLOOD_RECOVERY_RATE`, `BLEED_CLOT_RATE`.
- Lua: да (RW). Наше использование: Tempo читает `blood`.
- Рычаги: потеря крови уже выводит из боя. Связывать с «кто перевязал» через `xpFirstAid`, без своих HP.

### Голод
- `hunger`, `fed`, `isFed`, `isReallyHungry`, `isHungerKO`, `lastHungerKO`, `pointOfNoReturn_Hunger01(mult)` (в Lua нет), `getHungerSpeedModifier` (MedicalSystem.h:196–198, 214–217, 259). `CharStats::calculateHungerMult` CharStats.h:240 (нагрузка, бег, работа на станке `currentOperatingMachineHungerRate` :249). `Character::foodUpdate/eatItem/wantsToEatNow/amSomeoneWhoNeedsToEatToLive/getMagicHungerSetting` Character.h:316–318, 456–460. Настройки: `GameplayOptions.hungerTime`, `getStarvationTimeInHours`; константы `STARVATION_TIME_HRS`, `BED_HUNGER_RATE`, `ENCUMBRANCE_HUNGER_RATE`, `FED_RECOVERY_RATE_MULT`, `FOOD_QUALITY_MULT`. Раса: `hungerRate`, `specialFoods`, `canEat` (в Lua `canEat` есть, B:11273).
- Голод снижает статы через `getHealthStatModifier(_hunger=true)` (✓код по сигнатуре, сила эффекта — ?). Голодный обморок — `isHungerKO`.
- Направление шкалы `hunger` (убывает от 300?) — ?; Tempo это проверяет зондом.
- Lua: да; notify `Character::eatItem(food, inv)` (C:37), override `Inventory::getBestFoodItem(race)`.
- Наше использование: Tempo (NPC-голод, кормление, рабы), Conductor/Nemesis/Siege читают `hunger`.
- Рычаги: дефицит еды в мире → голодные NPC слабее (ваниль), ослабевшие банды сдаются или нанимаются. Не вводить свою «сытость».

### Нокаут, сон, бессознание
- `knockout(float skill01)` MedicalSystem.h:210 0x644200; `knockoutForceTimer(seconds)` :211; `startKnockoutTimer` :209; поля `knockoutTimer`, `nextKOTime`, `unconcious`, `sub50KO`, `crippled`, `dead` (:208, 285–291); `canGetUpWakeUp` :265; `reassessCollapseMode(medic, agony)` :253; `getCollapseStage` :238 (COLLAPSE_NONE/BUT_NO_RAGDOLL/KO). Константы `KNOCKOUT_MULT_1/_99`, `KNOCKOUT_BASE_TIME`, `TOUGHNESS_KO_POINT_MIN/MAX`.
- `Character::isUnconcious` (учитывает притворство) и `isLiterallyUnconciousNotPretending` Character.h:463–465; `ProneState` PS_NORMAL / PS_STAYING_LOW / PS_CRIPPLED / **PS_PLAYING_DEAD** / PS_KO (:53–60), `setProneState` :471; `isDown`, `isItSafeToGetUp`, `isCurrentlyGettingUp`, `playerWantsMeToGetUp`.
- Сон: `setBedMode(on, UseableStuff*)` :593, `restedState`, `isFullyRested` (MedicalSystem.h:120, 225), `BODYPART_HEAL_RATE_MULT_RESTING`.
- Lua: да; notify `MedicalSystem::knockout(skill)` (C:91); override `MedicalSystem::canGetUpWakeUp(defaultVal) -> boolean` (C:717).
- Наше использование: KMM_Self («сдача = нокаут») пишет `knockoutTimer=25` и `unconcious=true` напрямую.
- Рычаги: (1) вместо записи флага вызывать `knockoutForceTimer(sec)`: метод ядра сам пройдёт путь коллапса и рэгдолла. Прямая запись `unconcious` может разойтись с анимацией — ?. (2) Override `canGetUpWakeUp` = «пленник не встаёт, пока его не связали или не отпустили» — мост к рабству. (3) `PS_PLAYING_DEAD` — ванильное «притвориться мёртвым», готовая форма отступления.

### Смерть
- `Character::declareDead` Character.h:406 0x7A4FA0; `isDead`; `MedicalSystem::dead`; `pointOfNoReturn`; `dropGearOnDeath(vampiric)` :257; `bodyDecayTimer` :162; `lastGuyWhoDefeatedMe` :550 (hand).
- Lua: да; notify `Character::declareDead(self)` (C:30).
- Наше использование: Conductor, Traces, Tempo — `declareDead`; `isDead` — почти все модули.
- Рычаги: `lastGuyWhoDefeatedMe` — родное «кто меня победил», без нашей таблицы. Читать на KO или в declareDead и отдавать в Nemesis и слухи.

### Увечья и протезы
- `LimbState` ORIGINAL / STUMP / REPLACED / CRUSHED (MedicalSystem.h:14–20); `amputate(limb, createSeveredItem, force)` :124; `crushLimb` :125; `hasFreshlySeveredALimb` :258; `isUselessNoLimbGuy` :126; `getMissingArmPenaltyMult` :220; `hasAnArmToFightWith`, `canIkick`, `isRightArmOk/isLeftArmOk`; `RobotLimbs` (:44–74); `setRobotLimbItem` :185; `_getRoboticsStatMult` :219.
- Lua: `amputate`, `crushLimb` (B:9432) — да; `getLimbState` в биндинге возвращает void (сломан, ?); notify `MedicalSystem::amputate(limb, createSeveredItem, forceVector)` (C:66).
- Наше использование: Veterans — калеки только через шаблоны FCS (осознанный выбор).
- Рычаги: notify `amputate` = событие «потерял руку в бою с X» → память и слух. Подписка на событие безопаснее, чем самим вызывать `amputate`.

### Лечение
- `applyFirstAid(skill, equipment, frameTIME, who)` MedicalSystem.h:250 0x64D080; `applyDoctoring` :251; `applyRigging` :252; `drainMedkit` :298; `CharStats::getMaxHealAmount(equipment, bed, isRobot)` CharStats.h:155; `Character::healCompletely` Character.h:180; `RaceData.firstAidSkill`; константы `MEDIC_SPEED_MULT`, `MEDKIT_DRAIN_1/_99`, `BODYPART_HEAL_RATE_MULT`, `DEGENERATION_MULT_1/_99`; `GameplayOptions.difficultHealing`.
- Lua: в биндинге `applyFirstAid/applyDoctoring/applyRigging` без аргументов и void (B:9486–9488) — вызывать нельзя (?). `healCompletely` — да.
- Наше использование: нет.
- Рычаги: лечение видно через notify `xpFirstAid(patient, …)` и диалоговые события EV_HEALING_OTHER_*/EV_BEING_HEALED_* (E: EventTriggerEnum 18–21) — их и использовать.

### Среда и звери
- `gettingEaten(amount, vampire)`, `gettingAcidRain/AcidWater/AcidFeet/Gassed/Windyface/Burnt` MedicalSystem.h:243–249; погода `getWeatherStatPenalty*`; `RaceData.weatherImmunities`. Notify `Character::_NV_gettingEaten(amount, eater)` (C:39).
- Наше использование: нет. Рычаг: «его съели звери» — notify для слухов и Predators.

## C. Бой

### Состояния и режимы
- `swordStateEnum` (E:1700): CHOP_WEAPON, BLOCK, REACTION_BLOCK, STARTUP_STATE, DECISION, CIRCLE_MENACINGLY, WAIT_MENACINGLY, HESITATE, STUMBLE, COMBAT_FINISHED, TARGET_PATHFINDING*. `CombatClass::getCombatState` combat/CombatClass.h:68, `combatModeActive` :165, `getTimeSinceLastCombatModeInHours` :138, `readyToFinishCombatMode` :137.
- Режимы `CharStats`: `_defensiveMode`, `rangedMode`, `tauntMode`, `_holdPositionMode`, `passiveCombatMode`, `holdLocation` (CharStats.h:156–165). Приказы — `Character::setStandingOrder` (notify `_NV_setStandingOrder`).
- `Character::isInCombatMode(melee, ranged)` Character.h:533, `isLiterallyUnderMeleeAttackRightNowForSure` :535, `endCombatMode` :427, `_isEngagedWithAPlayer` :388.
- Lua: да. Наше использование: Gov/Self/Town — `isInCombatMode`.

### Кто кого бьёт (выбор цели)
- `CombatClassAI::chooseAttackTarget` CombatClass.h:313 0x666760; `getBiggestThreat(list, minThreshold)` :220; `whoAttacksYouOrMe(who, chance, &ret)` :311; `gotMoreImportantThingsToDoThanFightingYou` :315; `focusedTarget`, `reFocusableMode` :296–297; слоты атаки `AttackSlotManager` (до 5, `MAX_NUM_ATTACK_SLOTS`) :96–133; `getAttackers`, `getNumOpponents`, `areYouFightingAndInNeedOfHelp` :86–89; `getTotalRelativeStrengthOfAttackers` :89. Дальний бой: `RangedCombatClass::chooseNewTarget` 0x436D50, `scoreTarget(who, rangeMult)` 0x4355F0, `takeTheShotCheck`.
- `Character::attackTarget(who)` Character.h:496; `getAttackTarget` :532; `getAllAttackers/Count` :555–556; `areYouGonnaGetMe(who)` :554.
- Lua: `chooseAttackTarget`, `hasFreeAttackSlot`, `getNumAttackSlots` в биндинге нет (только плагин); `whoAttacksYouOrMe`, `attackTarget` — да.
- Наше использование: Traces — `attackTarget` (натравить отряд).
- Рычаги: хук `chooseAttackTarget` («немезис бьёт именно игрока, а не первого встречного») — дорого, только плагин. Дешёвая замена: `attackTarget(pc)` на лидере, это уже есть в Traces.

### Агрессия, враг/союзник
- `attackingYou(attacker, so, doAwarenessCheck)` Character.h:500 0x5C8B10 — ? сообщает «на тебя напали» и запускает реакцию; `iShotYou(attacker, harpoon, onPurpose)` :501; `notifyTheCampaignOfAnAttack` :497; `iShouldntAggravateThisTarget` :498; `isEnemy/isAlly(who, factorInDisguises)` :624–626; `getIntendedAggression` :444; `clearTempEnemyStatus` :541.
- Lua: да. Колбэка на `attackingYou` нет.
- Рычаги: `isEnemy(who, true)` учитывает маскировку — проверять им, а не отношениями фракций.

### Урон, блок, уклонение
- `Damages` {cut, blunt, pierce, extraStun, bleedMult, armourPenetration} Damages.h:18–23; `getTotalAttackDamageFor(target)` CharStats.h:186; бонусы `bonusHumans/Animals/Robots/bonusRaces/bonusArmourPenetration` :276–281; `calculateDodgeChance(versus, stumbling)` :250; `_calculateBlockChance(versus)` :262; `getAttackSuccessChanceSkill` :236; `calculateToughnessDamageResistanceMult` :179; `calculateStumbleThresholdDamageAmount` :77; `Character::_startStumble` :506. Константы `ATTACK_CHANCE_SKILL_DIFFERENCE_FACTOR`, `BASE_BLOCK_CHANCE`, `DAMAGE_RESISTANCE_MIN/MAX`, `GameplayOptions.globalDamageMultiplier`.
- Выбор приёма: `chooseAttack(range, reach, last, stationary)` :173 0x886880 (override C:698); `chooseBlock` :175; `CombatTechniqueData` (minSkill/maxSkill/maxEncumbrance) combat/CombatTechniqueData.h:40–43.
- Lua: notify `Character::_NV_hitByMeleeAttack(cutDir, damage: Damages, attacker, attack, comboID)` (C:38). Меняет ли запись в `damage` внутри notify реальный урон — ?.
- Наше использование: Conductor (hit_hook: кто кого ударил → исход боя), Nemesis.
- Рычаги: hit_hook уже даёт пары «атакующий → жертва». Это сырьё для `rememberCharacter` и для поиска соперника по силе.

### Отступление и сдача
- Ядро персонажа: `isFleeing` Character.h:385; `CharMovement::isRunning/isRunningAway(from)` CharMovement.h:385–386 (override в Lua); `PS_PLAYING_DEAD`; `separateIntoMyOwnSquad(permanent)` :256. Отдельной функции «сдаться» у `Character` нет (✓код: в заголовках не найдено): сдача сделана диалогом и AI — `DA_RUN_AWAY=34`, `DA_KNOCKOUT=58`, `SURRENDER_NON_HUMANS=47`, `DA_PLAYER_SURRENDER_MEMBER_DIFFERENT_RACE=51` (E: DialogActionEnum), отряд — `Blackboard:runAway()`.
- Наше использование: Self — `runAway` и нокаут.
- Рычаги: сдача через диалог с `DA_KNOCKOUT` + `EV_I_DEFEATED_SQUAD=15` — родная форма с репликой, без ручной записи флагов.

## D. Восприятие и скрытность

### Что видит персонаж
- `SensoryData` (`Character::getSensoryData`): `seen` map hand→`SeenSomeone` {lastPosition, lastSeenTime, percievedFaction, percievedSlave, FOVScore, canSee, canHear, alarmState, type: TagsClass<SenseType>} (SensoryData.h:40–60, 115). Итератор `getIterator(tagsAny, tagsNOT)` :116 с битами `SenseType` (SENSE_ENEMY, SENSE_KO, SENSE_DEAD, SENSE_SLAVE, SENSE_ESCAPED_SLAVE, SENSE_PLAYER, SENSE_CRAWLING, SENSE_CARRIED …, :18–36). Запросы `canISeeThisGuy`, `canIHearThisGuy`, `amIAwareOfThisGuy(who, needToSeeOrHear)`, `getLastKnownPositionOf`, `getDataFor` :120–124; `getVisionRange(inTown)` :112; угроза `totalThreatLevelPersonal/Allies`, `numEnemies`, `numNeutrals`, `nearestEnemy` :104, 133–137; `noticeThisPerson(c, alarmed)` :145; `assessCrimes`, `assessKidnapping`, `isIntruder_*`, `isEscapee` :152–153, 197–200; `notifyCriminalThreat` :126.
- `Character`: `getLightLevel`, `getPerceptionMult` :252, `lineOfSightCheck(who)` :251, `getCurrentNoiseRange` :185, `stealthMode`, `stealthUnseen`, `whoSeesMeSneaking` (map hand→WhoSeesMe {seeState, progressOfMaybe}) :296, `notifyICanSeeYouSneaking` :254; раса `visionMultiplier`.
- Lua: да (B:12281, B:12213); `SpottingPeopleMgr` внутри не открыт.
- Наше использование: нет.
- Рычаги: (1) **свидетели**: слух о деле игрока рождается только у тех, кто `amIAwareOfThisGuy(pc)` в момент дела. Атмосфера без всезнающего мира, дёшево. (2) `alarmState`/`threats` — кто уже встревожен.

### Кража, скупка, мародёрство
- `ImStealingDoYouNotice(stealFrom, item)` Character.h:260 0x7935B0; `getStealingSuccessChance(stealFrom, item, victimOut)` :269 (в Lua без victimOut); `getFencingSuccessChance(item, thief)` :262; `stolenGoodsDetectionCheck`, `sellingUniformDetectionCheck`, `smugglingTradeCheck` :263–267; `isItOkForMeToLoot` :258; `crimes: BountyManager` :209.
- Lua: notify `_NV_ImStealingDoYouNotice` (C:44), `_NV_smugglingTradeCheck`; override `getFencingSuccessChance`, `_NV_isItOkForMeToLoot`, `Platoon::iBuyStolenGoods/iBuyIllegalGoods`; notify `BountyManager::notifyCrimeWitnessed(faction, againstWho, expiryTime, crimeType)` (C:64).
- Наше использование: награда — см. «Награда за голову» (B1); сама кража — нет.
- Рычаги: (1) notify `ImStealingDoYouNotice` → `rememberCharacter(thief, LT_STOLE_FROM_ME)` у жертвы = ванильная обида. (2) override `iBuyStolenGoods` по городу/фракции — скупщики как часть экономики.

### Нокаут-удар, похищение, взлом
- `getStealthKOChance(victim, factors)` Character.h:390 0x883B40; `getKidnappingChance(victim)` :391; `getKidnappingEscapeChance_skill/_strength(captor)` :392–393; `getLockpickChance(DoorLock*)` :394 (в Lua аргумент — userdata).
- Lua: да, только вызовы (перехвата нет).
- Рычаги: шанс побега пленника считает ядро — по нему решать, «сбежал ли» наш пленник в дальнем мире, без своей формулы.

### Маскировка
- `wearingUniformOf(f)` :646, `getUniformColorScheme`, `DisguiseGUIFeedback` (DGF_SAME_FACTION / MY_SLAVE / I_HATE_YOU) :275–283, `SensoryData::disguiseMods` :151. Рычаг: форма фракции как пропуск — ваниль, не трогать.

### Награда за голову
- Ваниль: у каждого персонажа `Character.crimes: BountyManager` (Character.h:209). Награда — по фракции: `bounties` map Faction*→`Bounty` {amount, crimes — битмаска CrimeEnum, bountyHasBeenClaimedOnce, bountyAssignmentStartedTime} (Bounty.h:28–40). Замеченное преступление → `notifyCrimeWitnessed(against, againstWho, expiry, CrimeEnum)`; сумму за вид считает ядро: static `getBountyForCrime(c)`, срок `getBountyExpirationTime(bounty)`, тюрьма `getPrisonSentenceInHours(bounty)` (BountyManager.h:96–98). **В данных сумм за вид нет** (gamedata.base: только CHARACTER «bounty amount/fuzz/chance», «assigns bounties» у 13 NPC и FACTION «offers bounties»; CONSTANTS — лишь «prison time», `PRISON_TIME_MULT`), поэтому цену правим в рантайме.
- CrimeEnum (Bounty.h:6–26, EnumsReference `CrimeEnum`): 1 ENSLAVING, 2 LOCKPICKING, 3 STEALING, 4 MURDER, 5 ASSAULT, 6 ASSAULT_VIP, 7 SLAVE_FREEING, 8 SMUGGLING, 9 TERRORISM, 10 LOOTING, 11 TRESSPASSING, 12 ESCAPE_PRISON, 13 FENCING, 14 FARM_EATING, 15 KIDNAPPING, 16 UNIFORM_THEFT.
- Точки ядра (BountyManager.h, все ✓код и в BindingsReference): чтение `getActualBounty(f)` :66, `getTotalBounty()` :73, `getPercievedBounty(whosLooking)` :65, `_getBountyFaction(f)` (кто держит награду за фракцию) :58, `_getHighestBountyFaction()` :59, `getBountyRecognitionThreshold()` :71; запись `unfairAddToBounty(enforcer, amount)` :70, `assignBountyForCrimes(enforcer)` :69, `setCrime(crime, against, hand)` :80; снятие `clearBounty(enforcer)` :72 (выплата/помилование — диалог DA_PAY_BOUNTY / DA_CLEAR_BOUNTY, Dialogue.h:43/:82), `notifyPlayerClaimBounty` :67, `bountyAlreadyBeenClaimedByPlayer` :68; тюрьма `notifyStartPrisonSentence(law)` :92, поля `prisonSentenceBeganTime/ToServe` :88–89, `committingCrime`, `crimeAgainstFaction`, `crimeAgainst` :83–86; пропуск `hasAccessPass/giveAccessPass` :93–94.
- Пойман / свободен (Character.h): `inSomething == IN_PRISON` (UseStuffState=2) :590, `isPrisonerFreeToGo()` :540, `setPrisonMode` :592, `isChained` :594, `isKidnapped()` :461, `isBeingCarried()` :616; AI `iAmImprisoned/targetIsImprisoned/targetIsArrested` (AI.h:297, :368–369), охота `findBounty` (AI.h:403), задача `HUNT_BOUNTIES`; вес жертвы — `isLawEnforcement()` :188, `canAssignBounties()` :189, `isUnique()` :197, `isATrader()` :383; hand `getCharacter()/toString()`.
- Lua: да (BindingsReference BountyManager/Bounty; колбэк CallbacksReference C:64). Перехвата начисления нет (override не дан) — только доплата `unfairAddToBounty` после того, как ядро само назначило награду.
- ?: `self.me` в колбэке — преступник (не свидетель); колбэк вызывается до или после начисления (код принимает оба: рост от суммы в момент колбэка или от прошлой); `getBountyForCrime` как метод экземпляра из Lua; сбрасывает ли `unfairAddToBounty` срок истечения; стабильность `hand:toString()` персонажа между сессиями; можно ли обходить `bounties` (map с ключом Faction*) из Lua — не используется.
- Наше использование: KMM_Traces (BNT: награда игрока → охотники `bounty_hunt`), KMM_Outlaws (родная награда главарям `native_bounty`, Q2 дела банд, **B1**), KMM_Fates (`deed bounty`), KMM_Deeds (Y1: колбэк как свидетель).
- **B1 (KMM_Outlaws, 2026-11-15):** (а) цена дела: дело игрока из колбэка ждёт 3 с; если ядро выставило награду (getActualBounty у `_getBountyFaction` выросла) — доплата до `b1_price` (убийство 8000, терроризм 5000, похищение/порабощение 4000, побег 3500, нападение на VIP 3000, освобождение раба 2000, нападение 1500, кража 800, взлом 700, мародёрство/форма 600, проникновение 300) × вес жертвы × рецидив (+15 %/дело, до ×1.6) минус ванильная сумма, ≤15000 за дело; ядро не дало — нет и доплаты. (б) вес: страж ×1.6, уникальный ×1.5, торговец ×1.3 (берётся max), жертва из банды без закона ×0.25. (в) скрылся (жив, не в тюрьме/цепях/похищен/на плечах): раз в игровой день +5 % (+1 %/дело сверх первого, ≤10 %), кап ×3 честной награды, только 12 дней после последнего дела; пойман — рост сброшен; награды у ядра нет — запись снята. NPC-разыскиваемые: +1.5 % (+0.2 %/дело, ≤4 %), кап ×2, 6 дней, тюрьма — сброс. (г) пороги 5k/15k/40k → `outlaw_pc_wanted`; NPC 10k/25k/50k → `outlaw_wanted_up`; NPC ≥25k → облава (`M.manhunt`, патруль с HUNT_BOUNTIES). Параметры `b1_*` — M.DEF, переопределение `params.outlaws` в conductor.json. Тест `_dev/test_b1_bounty.py`.
- Рычаги для живого мира: (1) рост награды кормит уже существующих охотников Traces/облавы — мир сам приходит за должником; (2) `getPercievedBounty(whosLooking)` + маскировка — «узнали в лицо» как условие слуха (не сделано); (3) `giveAccessPass` — купленный пропуск как альтернатива выплате (не сделано).

## E. Плен, цепи, рабство (на уровне персонажа)

- `setChainedMode(on, owner)` Character.h:597 0x32E0E0; `isChained`, `slaveOwner` :594–595; `getChainedModeShackles` :599; `changeSlaveOwner(newOwner)` :602; `isSlave() -> SlaveStateEnum` :601 (NOT_SLAVE / IS_SLAVE / ESCAPING_SLAVE / EX_SLAVE, E:1016); `isMySlave`, `isMyFactionsSlave` :603–604; `setSlaveAIJob(on)` :596; `runSlaveAnim/endSlaveAnim` :608–609; `CharacterHuman::shaveHead` CharacterHuman.h:42.
- Тюрьма: `setPrisonMode(on, UseableStuff*)` :592; `inSomething` (IN_NOTHING / IN_BED / IN_PRISON) :124–129, 590; `isPrisonerFreeToGo` :540; `isKidnapped` :461; `PRISON_TIME_MULT`. Переноска: `pickupObject`, `getPickedUp`, `isBeingCarried`, `dropCarriedObject` :611–621.
- Lua: да; notify `setChainedMode(on, ownerHandle)` (C:96), `changeSlaveOwner(newOwnerHandle)`, `pickupObject(who)`, `getPickedUp(byWhom)`.
- Диалог: DC_IS_SLAVE=59, DC_IS_ESCAPED_SLAVE=62, DC_WEARING_LOCKED_SHACKLES=64, DC_IS_IN_LOCKED_CAGE=63, DC_IMPRISONED_BY_TARGET=7; DA_TAG_ESCAPED_SLAVE=25, DA_FREE_TARGET_SLAVE=26, DA_REMOVE_SLAVE_STATUS=53, DA_ENSLAVE_TARGETS_CARRIED_PERSON=40; EV_BOUGHT_ME_FROM_SLAVERY=51, EV_SLAVE_ESCAPE_OPPORTUNITY_*=54–55.
- Наше использование: Conductor и Nemesis (`setChainedMode`; Nemesis слушает его как «освободил»), Tempo/Elite/Traces (`getMySlaveOwner`, `isSlave`).
- Рычаги: notify `changeSlaveOwner` = продажа или выкуп → память (`LT_FREED_ME` при выкупе игроком) и цена в экономике.

## F. Память и отношения

### Краткая и долгая память
- Энумы: `CharacterPerceptionTags_ShortTerm` ST_NONE=0, ST_INTRUDER=1, ST_AGGRESSOR=2, ST_TEMPORARY_ALLY=3, ST_TEMPORARY_ENEMY=4, ST_PRISONER=5, ST_HAS_BEEN_LOOTED=6, ST_CRIMINAL=7 (Character.h:75–85, E:506). `CharacterPerceptionTags_LongTerm` LT_NONE=0, LT_MY_INTRUDER=1, LT_MY_LIFESAVER=2, LT_FREED_ME=3, LT_STOLE_FROM_ME=4, LT_MY_CAPTOR=5, LT_FRIENDLY_AQUAINTANCE=6, LT_DEFEATED_MY_SQUAD_ONCE=7, LT_SQUAD_LOST_TO_ME_ONCE=8, LT_KILLED_MY_FRIEND=9, LT_I_SCREWED_THIS_GUY=10 (:87–101, E:519).
- Точки ядра: `rememberCharacter(who, ST)` Character.h:543 0x673D20; `rememberCharacter(who, LT)` :544 0x6732A0; `getCharacterMemoryTag(who, LT)` :545 0x6745F0; `(who, ST)` :546 0x6781E0; `conglomerateTagsFor(who)` :539 (битовая маска); `haveMetBefore` :548; `lastSeenInHoursAgo` :547; `_myMemory: CharacterMemory*` :538; `getIDForMemoryTagging` :549.
- Выводы ядра из памяти: `ILoveThisGuyBecauseOfStuffThatHappened`, `IHateThisGuyBecauseOfStuffThatHappened`, `shouldIHelpThisGuy`, `shouldIScrewThisGuyOver` :395–398, `getRoughLevel` :399. Их читают диалоги: DC_I_LOVE_THIS_GUY=52, DC_I_HATE_THIS_GUY=53, DC_I_SHOULD_SCREW_THIS_GUY_OVER=54, DC_I_SHOULD_HELP_THIS_GUY=55, DC_HAS_TAG=23, DC_MET_TARGET_BEFORE=20, DC_TARGET_LAST_SEEN_X_HOURS_AGO=18. Записывает диалог действием **DA_REMEMBER_CHARACTER=19** (и DA_FLAG_TEMP_ALLY/ENEMY=20/21).
- Lua: `rememberCharacter[1]`(ST) и `[2]`(LT) (B:3449–3450); `getCharacterMemoryTag[1]`(LT) и `[2]`(ST) (B:3466–3467). Энумы в Lua — числа, обе перегрузки принимают (Character, integer), так что **по типу перегрузку не выбрать**. Если побеждает `[1]`, вызов `rememberCharacter(pc, LT_x)` запишет ST с тем же номером: LT_DEFEATED_MY_SQUAD_ONCE(7)→ST_CRIMINAL, LT_MY_CAPTOR(5)→ST_PRISONER, LT_FREED_ME(3)→ST_TEMPORARY_ALLY, LT_MY_LIFESAVER(2)→ST_AGGRESSOR, LT_KILLED_MY_FRIEND(9) — вне ST. Так это или нет — ?. Чтение `getCharacterMemoryTag` перепутано зеркально: `[1]` = LT.
- Наше использование: Nemesis `N.remember` → `leader:rememberCharacter(pc, LT_*)` под `probe_call` (KMM_Nemesis.lua:1320–1330).
- Рычаги: (1) Надёжная запись: функция плагина `kmm_native.remember_lt(charHandle, whoHandle, tag)` с прямым вызовом 0x6732A0, либо строка FCS-диалога с `DA_REMEMBER_CHARACTER`. (2) Офлайн-проверку можно сделать, не играя: после сессии прочитать сейв kmm.py — какой тег реально лёг в память. (3) Все ванильные реплики «ты спас мне жизнь / ты мой враг» оживут сами, нужна только правильная метка.

## G. Реплики

- `say(s)` Character.h:361, `say_WithARepeatLimiter(s)` :359, `sayALine(line, force)` :486 — облачко над головой; `sendDialogEvent(target, EventTriggerEnum)` :485 и `sendDialogEventOverride(target, what, forceRepeat)` :484 — запускают ванильную ветку диалога по событию; `canSpeakNormally` :198, `willTalkToEnemies` :489, `hasDialogue` :488, `dialogue: Dialogue*` :487.
- Lua: да; notify `Character::_NV_say(message)` (C:33), `Dialogue::say(dialogLine)`, `Dialogue::_doActions(dialogLine)`; override `Dialogue::_checkCondition(cond, cmp, val, target, convTarget, defaultVal)` (C:708), `Dialogue::sendEvent(who, what, defaultVal)`, `startConversation`.
- Наше использование: Nemesis — `sayALine` с задержкой.
- Рычаги: (1) `sendDialogEvent(pc, EV_I_DEFEATED_SQUAD)` и др. — реплика из ванильных данных на нужном языке, без английских строк в Lua. (2) override `_checkCondition(DC_I_HATE_THIS_GUY)` = «true для немезиса» — ванильные реплики вражды начинают звучать.

## H. Раса, возраст, тело

- `RaceData` (RaceData.h:15–64): runSpeedMin/MaxSkill, healRate, bleedRate, hungerRate, visionMultiplier, swimSpeed, walkSpeed, robot, vampiric, extraAttackSlots, firstAidSkill, statMods, weatherImmunities, specialFoods; `getStatMod(stat)` 0x65CE70, `canEat`, `isRelatedRace`.
- Lua: поля RW (B:11273). **Это общий объект на всю расу**: запись меняет всех её представителей.
- Возраст: `getAge/getAge0to1/setAge` Character.h:511–522 (у зверей — `lifespanInDays`, `age`). Внешность (`Appearance*`) на геймплей не влияет, кроме `isFemale`, `isHeadShaven`.
- Наше использование: Self, Traces — `getRace` для проверок.
- Рычаги: не трогать на лету (затронет весь мир). Различия рас задавать в FCS-данных.

## I. Движение (игровые эффекты)
- `CharStats.moveSpeed`, `athleticsMultiplier`, `encumbranceMult`, `getMaxRunSpeed`, `calculateMaxStealthSpeed`, `calculateSwimSpeed` (CharStats.h:29, 233–261); `CharMovement::setMaxSpeed/getMaxSpeed/getCurrentSpeed/setDesiredSpeed` CharMovement.h:155–168; `MedicalSystem::getMovementSpeedInjuryMultiplier` :240; `getHungerSpeedModifier` :217.
- Lua: да; override `CharMovement::isRunning`, `isRunningAway`.
- Наше использование: Tempo — `moveSpeed` (усталость).

## J. Колбэки домена (полный список)

Notify (отменить действие ядра нельзя; `return false` только гасит следующие Lua-обработчики):
`Character::declareDead()`, `_NV_select/_NV_unselect()`, `_NV_say(message)`, `pickupObject(who)`, `getPickedUp(byWhom)`, `_NV_takeMoney(amount)`, `eatItem(foodItem, inventory)`, `_NV_hitByMeleeAttack(cutDir, damage, attacker, attack, comboID)`, `_NV_gettingEaten(amount, eater)`, `_NV_setStandingOrder(orderID, enabled)`, `_NV_setFaction(faction, platoon)`, `_NV_equipItem/_NV_unequipItem(section, item)`, `_NV_ImStealingDoYouNotice(stealFrom, item)`, `_NV_smugglingTradeCheck(item, who)`, `_NV_init()`, `addGoal(taskType, subject)`, `addJob(...)`, `addOrder(...)`, `removeJob(taskType)`, `changeSlaveOwner(newOwnerHandle)`, `setChainedMode(on, ownerHandle)`, `_NV_serialise/_NV_loadFromSerialise/_NV_loadFromSerialisePostCreationStage`.
`CharStats::xpRunning(time, speed)`, `xpFirstAid(patient, time, medicStat)`, `xpStealth(time, enemiesAbout, seen, isMoving)`, `xpToughness_GetUpEvent()`, `xpToughness_RagdollEvent()`, `xpToughness_PunchSomething(mat)`, `xpEngineering(time)`, `xpLockpicking(lockLevel, success)`, `xpStat_eventBased(statType, amount)`, `xpDodgeEvent(enemySkill, successful)`, `setHoldLocation(v)`, `clearHoldLocation()`.
`MedicalSystem::knockout(skill)`, `MedicalSystem::amputate(limb, createSeveredItem, forceVector)`; `BountyManager::notifyCrimeWitnessed(faction, againstWho, expiryTime, crimeType)`; `Dialogue::say/_doActions(dialogLine)`, `endDialogue`, `stopEvent(what)`; `CharacterAnimal::_NV_*` (periodicUpdate, foodUpdate, setAge, giveBirth …).
Override (возврат не-nil заменяет значение ядра):
`CharStats::getStat(statType, unmodified, defaultVal) -> number`, `CharStats::chooseAttack(range, reach, last, stationary, default) -> CombatTechniqueData`, `MedicalSystem::canGetUpWakeUp(defaultVal) -> boolean`, `Character::_NV_isItOkForMeToLoot(victim, item, default) -> boolean`, `Character::getFencingSuccessChance(item, thief, default) -> number`, `CharMovement::isRunning(default)`, `isRunningAway(from, default) -> boolean`, `Inventory::getBestFoodItem(race) -> Item`, `Platoon::iBuyStolenGoods(item, default)`, `iBuyIllegalGoods(default)`, `Dialogue::_checkCondition(...)`, `startConversation(...)`, `startPlayerConversation(...)`, `sendEvent(who, what, default) -> boolean`, `CharacterAnimal::_NV_getHPMultiplier/getAge*/getSmellHuntingThreshold*`.
**Колбэков нет** (только хук плагина): `xpMelee`, `xpGeneral`, `xpTraining`, `xpMassCombat`, `xpStat_timeBased`, `attackingYou`, `iShotYou`, `rememberCharacter`, `setPrisonMode`, `applyFirstAid`, `chooseAttackTarget`, `noticeThisPerson`, `assessCrimes`.

---

## Лучшие рычаги для живого мира и нелинейной прокачки
(от ценного и дешёвого к дорогому)

1. **Соперник чуть сильнее игрока = ванильный ускоренный рост.** `xpMelee` и `xpDodgeEvent` уже умножают XP на разницу навыков (`getSkillDifferenceRatio`, `SKILL_DIFFERENCE_XP_RATIO_MULT_BONUS`). Подбирать спавн именных конкурентов (Outlaws/Nemesis) по `getOverallSkillLevel_0_100` игрока +10..20 — прокачка через встречи без строчки своего XP. Цена: правка подбора отряда. ✓код, эффект ?.
2. **Числа XP через FCS CONSTANTS** (`GlobalConstants::setup(GameData*)`): поднять `SKILL_DIFFERENCE_XP_RATIO_MULT_BONUS` и `XP_HIT_*`, не трогая тренажёрный путь. Бой с сильным выгоднее манекена. Цена: только данные генератора. ✓код (поля), имя записи ? — сверить с FCS.
3. **Память ядра вместо своих таблиц: `rememberCharacter` LT_* + ванильные DC_I_LOVE/HATE/HAS_TAG.** Надо снять неоднозначность перегрузки: функция в kmm_native (0x6732A0) или FCS-строка с `DA_REMEMBER_CHARACTER`. После этого все ванильные реплики благодарности и мести работают сами. Цена: одна функция плагина. Высокая ценность.
4. **Датчики дел из notify-колбэков:** `xpFirstAid` (вылечил), `_NV_ImStealingDoYouNotice` (украл), `xpLockpicking` (взломал/освободил), `setChainedMode`/`changeSlaveOwner` (пленил/продал/выкупил), `amputate`, `declareDead` + `lastGuyWhoDefeatedMe`. Всё уже в Lua; Nemesis использует два. Дальше — одна шина «деяние → память → слух». Дёшево.
5. **Свидетели:** слух и награда за голову только от тех, кто `SensoryData:amIAwareOfThisGuy(pc)` в момент дела (плюс `notifyCrimeWitnessed`). Мир осознан, но не всезнающ. Дёшево (Lua, только загруженные NPC).
6. **Начисление XP за «работу в мире» — `xpStat_eventBased(st, amount)`:** вернул долг, довёл караван, выжил в осаде → небольшой ванильный прирост нужного навыка с родной кривой убывания. Сначала один замер `amount` на NPC (стат до/после в сейве). Дёшево.
7. **Плен и сдача через ядро:** заменить в Self запись `unconcious=true` на `knockoutForceTimer(sec)`; override `canGetUpWakeUp` — «побеждённый лежит, пока его не связали или не отпустили». Получается цепочка сдача → плен → рабство на ванильных механиках. Средняя цена.
8. **Ванильные реплики вместо своих строк:** `sendDialogEvent(pc, EV_I_DEFEATED_SQUAD / EV_BOUGHT_ME_FROM_SLAVERY …)` и override `Dialogue::_checkCondition` (DC_I_HATE_THIS_GUY → true для немезиса). Локализация и озвучка из данных игры. Дёшево, но частота `_checkCondition` — ?.
9. **Голод как сила мира:** голодные NPC слабее (`getHealthStatModifier(_hunger)`), падают в обморок (`isHungerKO`). Tempo уже управляет `hunger/fed` — связать дефицит еды в экономике с силой банд и их готовностью сдаться. Цена: связка, без новых полей.
10. **Ситуативный стат через override `getStat`:** страх перед тем, кто уже побеждал (`getCharacterMemoryTag(LT_DEFEATED_MY_SQUAD_ONCE)`), −5..10 к защите только в бою с ним. Сильно, но горячий путь: кэш по handle, быстрый выход. Средняя/высокая цена.
11. **Перевес встреч над гриндом в плагине:** хук `xpTraining` (×0.5) и `xpMelee` (×1.2..1.5 против именных). Только если пункта 2 окажется мало. Дорого (2 detour-а, риск версии).
12. **Не делать:** запись полей `RaceData` на лету (меняет всю расу), прямые `applyFirstAid/getLimbState` из Lua (биндинг без аргументов или void), `chooseAttackTarget` без нужды — `attackTarget(pc)` уже есть.
