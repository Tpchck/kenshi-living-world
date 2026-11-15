# REVIEW batch7: Lua-модули перед установкой (2026-11-15)

Что сравнивалось: установленное `Kenshi\mods\KMM_*\scripts\init` (старое) и `build\KMM_*\scripts\init` (новое), diff без учёта CRLF.
Файлы: KMM_Deeds (Y1), KMM_Conductor_Sync (Y2), KMM_Self (Y3), KMM_Predators (Y4), KMM_Nemesis (Y5), KMM_Rumors.
Пакет 6 (Outlaws, RecruitRace, diplo, RelicRace, KC.duel) не разбирался.
Вызовы сверены с BindingsReference, CallbacksReference, EnumsReference, ContainersReference и заголовками KenshiLib.
Все методы и поля есть в биндингах: `BountyManager::notifyCrimeWitnessed(self, faction, againstWho, expiryTime, crimeType)` (Notification),
`BountyManager.me: Character` (BountyManager лежит в `Character::crimes`, значит me — преступник ✓код), `SensoryData:amIAwareOfThisGuy(Character, bool)`,
`canISeeThisGuy`, `MedicalSystem::canGetUpWakeUp(self, defaultVal) -> boolean` (Override), `MedicalSystem.me`, `Character.lastGuyWhoDefeatedMe/isChained`,
`Blackboard:addSquadJob` (9 аргументов, порядок совпадает с Blackboard.h:113), `clearAllTheJobs`, `squadJobs/squadJobs2/leaderJobs` (lektor, R, живая память движка),
`AI:setCenterOfMovement/setManuveringFreedomLevel`, `Faction.diplomatMgr` (указатель) → `prosperityMgr` → `notifySquadDefeated(GameData)`, `Platoon.squadTemplate`,
`StateBroadcastData.apparentStrength/actualStrength`, `Blackboard.moraleIsBroken`, `ActivePlatoon:getSquadSize`, `GameWorld:getCharacterUpdateList`.
Значения enum совпадают: SquadMemberType SQUAD_1=0/SQUAD_LEADER=2, TaskType.HOLD_POSITION=30, taskPriority.TP_URGENT=3, TaskEndEvent.TEE_REMOVE_WHOLE_SQUADS=2,
TaskTargetType SELF=1/LEADER=2, AIManuverabilityOrders STAY_CLOSE=1/ROAM_FAR=2, CrimeEnum 1..16 (D.CRIME).
Итог: **крит 0 · высокая 3 · средняя 8**.

## Высокая

**H1. Y3: окно побеждённого фактически не работает, потому что предел задан в игровых секундах.** KMM_Self.lua:389, :399.
Игровые часы Kenshi идут во много раз быстрее реальных (точный множитель через `getLengthOfHourInRealSeconds` не проверен (?), но он ≫1). 45 игровых секунд — это 1–2 реальные секунды.
Скан идёт раз в 3 реальные секунды, это ≥60 игровых секунд. Поэтому `KO.g_step` > `lim`, и `gnow - e.g0 + g_step >= lim` отпускает каждого удержанного уже на первом скане.
Окно получается не больше одного такта скана, примерно 3 с. Это меньше, чем нужно, чтобы связать или обыскать. Override при этом впустую ставится и снимается.
Исправление: считать предел в реальных секундах при скорости 1×: `(gnow-g0)/3600*getGameWorld():getLengthOfHourInRealSeconds()` (или os.clock с поправкой на `getGameSpeed`).
`g_step` переводить в те же единицы.

**H2. Y2: «подтверждённая потеря» не отличает гибель от выгрузки, и вред прогрессу ядра в сейве необратим.** KMM_Conductor_Sync.lua:802-812 (y2_note), :836, :857.
Сценарий: игрок уходит из зоны. Временные отряды фракции X выгружаются и уничтожаются. Колбэк `destroyPlatoon` срабатывает (сам код помечает «гибель или уход — ?»),
`getFactionSize` падает меньше чем на 50%, кредит своих спавнов исчерпан. Тогда `conf=true`, и все шаблоны из очереди (до `per_read`=2) уходят в `notifySquadDefeated`,
хотя никто не погиб. `ld` пишется, но не проверяется. Метод живёт в `FactionUniqueSquadManager` (там же учёт уникальных отрядов `squads/endOfUniqueSquad`).
Эффект не проверен (?). Если он уменьшает `actualProsperity` или помечает шаблон уничтоженным, это пишется в сейв через `ProsperityManager::save`, а отката нет.
Это до 12 вызовов в день просто за обычные переходы по карте. Есть и двойной счёт: если ваниль сама зовёт notify при разгроме раньше прошлого чтения, `vanilla_skip` его не видит.
Исправление: в `y2_note` ставить в очередь только `platoon.isDead == true` (или если все члены ActivePlatoon мертвы или лежат). Вызовов не больше, чем подтверждённых платунов (`min(#q, rl*size)`).

**H3. Y2: первый вызов `notifySquadDefeated` защищён только pcall, без крэш-замка.** KMM_Conductor_Sync.lua:857.
У RVA метода в заголовке 0x6B8D50 (и у notifySpecialNPCDead 0x7BF380) аномалия: все остальные методы класса лежат в 0x2DD000–0x2E0700, а заголовки сняты с 1.0.65 при игре 1.0.68.
Если в 1.0.68 метод уехал или привязан неверно, access violation pcall не поймает. Вызов идёт сам по себе на первой же потере (см. H2), и игра будет падать в каждой сессии.
Исправление: обернуть вызов в lock-файл как `probe_call` в Predators/Outlaws (`state/probe_prosperity.lock` → `.off`), первая сессия — только проба.

## Средняя

**M1. Y3: ключ удержания `tostring(hand)` может быть нестабилен (?).** KMM_Self.lua:289 (override), :426 (`k = r.h` из снимка), :562 (B3 `KO.forced`).
`getHandle()` возвращает hand по значению, каждый раз это новый userdata. Есть ли у `KenshiLua.hand` метаметод `__tostring`, в документации не сказано.
При дефолтном sol2 строка содержит адрес userdata, ключи не совпадут, override ничего не удержит (`asks=0`), а исключение сдавшихся B3 не сработает.
`:toString()` подтверждён в игре (ledger.md:101). Исправление: в override и в ko_step брать ключ как `me:getHandle():toString()` / `r.ch:getHandle():toString()`, а не `r.h`.

**M2. Y3: ложное удержание по устаревшему `lastGuyWhoDefeatedMe`.** KMM_Self.lua:353.
Поле хранит последнего победителя. Если NPC, которого игрок нокаутировал раньше, сейчас лёг от голода, зверя или в чужой стычке рядом, `ko_judge` всё равно вернёт "player".
Исправление: требовать, чтобы победитель был жив и находился в пределах `ko_hold_r` от жертвы, а запись `seen` для жертвы появилась впервые в этом бою (r.down сменился в окне боя).

**M3. Y4: наряды засады теряются без снятия, задачи остаются на доске.** KMM_Predators.lua:270 (потолок `sq_max` удаляет запись без release), :321 (смена мира), :327 (откат часов).
Кроме того, `SQ.live` живёт только в памяти. Если игрок сохранился во время засады и загрузился, или игра перезапущена, задачи `HOLD_POSITION` (Blackboard сериализует job-списки:
`_serialiseJobList`) и `STAY_CLOSE` остаются у отряда, а снимать их некому. Если окно h0..h1 — расписание по часам суток (?), отряд стоит у гнезда каждый день, пока живёт.
Исправление: при потолке звать `SQ.release(r,"cap")`. Хранить записи (строки key/fid/psid/till) в `C.state().ext.pred_sq` и снимать при первом нахождении после загрузки.

**M4. Y4: снятие неполное.** KMM_Predators.lua:299-306, :311-314.
Если `psid` не прочитался, задачи не чистятся вовсе («job left to end event»), а у HOLD_POSITION конца нет. `setCenterOfMovement` не возвращается.
`ROAM_FAR` ставится вслепую и может не совпадать с ванильным уровнем шаблона. Отряд остаётся привязан к точке гнезда.
Исправление: `clearAllTheJobs()` звать всегда (пакет при необходимости — `getCurrentPackage` на момент снятия). Перед STAY_CLOSE запоминать прежний уровень, если он читается, и возвращать его.

**M5. Y4: проба засчитывает регистрацию, а не работу задачи.** KMM_Predators.lua:241-256.
Единицы `startTime/endTime` под вопросом (?). Если задача добавлена, но не активна (не те единицы, h1<h0 через полночь), `n1>n0` даёт "ok".
Тогда фолбэк addOrder не ставится, и засада идёт по спавн-пакету к городу владельца, хотя раньше держала точку. Офлайн это не ловится.
Исправление: в первых сессиях ставить addOrder HOLD_POSITION вместе с нарядом. Либо через такт проверить `getCurrentAIPackageName` или позицию лидера и при уходе дать фолбэк.

**M6. Y5: отход временного соперника ничего не значит, и «nemesis_withdrew» повторяется.** KMM_Nemesis.lua:1321, :1251.
`wd_day` читает только Nemesis, а Outlaws.vis по нему не ждёт. Временный соперник уходит, а следующий спавн Outlaws сразу приводит новый отряд с пакетом охоты.
Оценка с тем же соотношением снова даёт withdraw, новое событие уходит в хронику и слухи, растёт `o.pg.wd`. Исправление: в Outlaws.vis пропускать запись,
если `o.pg.wd_day` моложе `appr_regroup_days`, или экспортировать `NM.can_hunt(o)`.

**M7. Y5: постоянный соперник может навсегда остаться на «бродить».** KMM_Nemesis.lua:1820-1825 (regroup под `not N.appr_off`), :1247-1249.
Пакет «roam» пишется постоянному отряду (S3) в сейв. Если после этого оценка выключится (`appr_off` после ошибки `appraise_step` или `appr_live==nil`), `regroup_day`
не вызывается, и охота не вернётся никогда. Исправление: регрупп держать под отдельным флагом (выключать только при его собственной ошибке) и звать даже при `appraise=false`.

**M8. Y1 действует наполовину: подписчики вне пакета не фильтруют `witnessed==false`.** KMM_Outlaws.lua:649, KMM_Fates.lua:357, KMM_Predators.lua:185.
Тихое убийство без свидетелей не становится слухом (Rumors) и не запоминается городом (Nemesis), но мститель или банда, награда Fates и запах для Predators появляются как раньше.
Мир реагирует противоречиво. Исправление (владельцам пакета 6): в `on_deed_g` делать `if ev.by_player and ev.witnessed == false then return end`. Для Predators это уместно оставить.

## Проверено, замечаний нет
- Y3 override: регистрация через `Events.on` только при первом удержании, снятие `Events.off(id)` в такте charsUpdate (не изнутри override). Возврат `false` = «не встаёт», `nil` = ваниль
  (CallbacksReference: учитывается любое не-nil значение того же типа). При `defaultVal=false` или пустой таблице выходим сразу. Ошибка → guarded возвращает nil,
  `ko_fail` отпускает всех. `hard` по os.clock — страховка, если скан встанет. Хендлы между тактами (`e.hd:getCharacter()`) безопасны, смена мира сбрасывает записи.
  Стоимость: обработчик стоит только во время удержания (после H1 — до 45 с реальных).
- Y3 и B3: сдавшиеся через `knockoutForceTimer` помечаются в `KO.forced` на 120 с. Это работает, если ключ стабилен (M1).
- Y1: колбэк только ставит отметку времени (дёшево). Снимок Gov проверяется через `has()`, поэтому указатели `r.ch` в `D.sense` проверены в этом кадре. Логи ограничены `log_max`/`ncrime_log`=40.
  Мелочь: `D.witness` считается до проверки dup/cap (лишний проход по снимку на ключ). Это не дефект.
- Rumors: пропуск `deed` с `witnessed==false` в readConductor корректен, остальные события не затронуты. Nemesis `deed_by_player` выходит раньше записи долга и неблагодарности.
- Y2: двойного счёта с S2 по силе нет (Y2 не пишет S.F). Богатство меняется одним чтением процветания сразу после вызова. Очередь сбрасывается при смене мира (`R.y=nil`).
  Потолки 2/3/12 и автоотключение после 6 измеренных вызовов без эффекта на месте. Ошибка выключает только Y2.
- Y5: `leader` держится между тактами, но перед каждым обращением проверяется `getCharacterUpdateList():has` (без разыменования). Если этой проверки нет, оценка выключается.
  Пакеты ставятся через `probe_call` Outlaws. Остаётся теоретический ABA (память удалённого персонажа занял новый). Гонок пакетов с Traces U1 и Predators нет: теги nemesis и predator_ambush не получают NAT-пакет, release Predators трогает только свои ключи.
- Спам: KO-логи ≤300, squadjob — по событию, PROSPERITY ≤12 в день, appraise — по встрече. Полных обходов в горячих путях нет.
