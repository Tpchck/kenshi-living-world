# REVIEW batch34 — Lua-модули перед установкой (2026-11-15)

Сравнение: установлено `Kenshi\mods\KMM_*\scripts` (старое) ↔ `build\KMM_*\scripts` (новое). KMM_Gov не ревьюился.
Метод: diff по файлам (CRLF игнорируется); для дирижёра — токенный diff монолита против склейки частей
(Base, Econ, Sync, World, Runtime, Main) со снятым префиксом `KC.`; статический список GGET/GSET через байткод LuaJIT
(lua51.dll из KenshiLua, jit.util); сверка вызовов с BindingsReference/CallbacksReference.
Итог: **крит 0 · высокая 4 · средняя 5**.

## Дирижёр: разбиение на 6 частей — дефектов не найдено
- Токенный diff: кроме обвязки `KC._SEG.<часть> = function() … end` + `KC._BOOT()`, отличия только новые S2 (CORESYNC в Sync,
  `KC.GL.cs_tick()` в on_tick, `pcall(Events.on, "Faction::destroyPlatoon", guarded(...))`, `coresync*` в API). Ничего не потеряно.
- Глобалы (байткод): единственная запись — `KMM_Conductor` в Main (сразу публикуется через `_G.KMM_Conductor`); чтение только
  стандартных имён и API движка. Голых имён бывших локалей (которые в песочнице другой части были бы nil) нет.
- Все `KC.<имя>`, которые читаются, где-то присваиваются. Затенений (локаль/параметр с именем поля KC, ошибочно переписанный в `KC.x`) нет.
- Порядок: forward-объявления `KC.x = nil` стоят в Base и перекрываются определениями в более поздних частях (Econ/Sync/World/Runtime);
  код уровня части, который выполняется при BOOT (`KC.GL.rs_st0()`, `KC.subscribe("deed")`, `KC.guarded(...)` в Runtime:360, `KC.GL.arch = KC.garch`),
  ссылается только на то, что уже определено. `local guarded = KC.guarded` в Main — Runtime выполняется раньше. Ок.
- Загрузка: KMM_Conductor.lua (`.` < `_`) идёт первым, BOOT срабатывает на последней части; другие модули берут `KMM_Conductor` лениво
  (`rawget(_G, ...)` в такте) — доступа до BOOT нет. Events.on все в guarded; destroyPlatoon — есть в CallbacksReference, сигнатура `(self: Faction, platoon)`.
- Замечание (не дефект): `KC._BOOT` вызывает `KC._SEG[p]()` без pcall; ошибка в любой части при BOOT оставит `KMM_Conductor` неопубликованным
  (как и у монолита). При горячей перезагрузке одного файла части `_SEG` сбрасывается и BOOT больше не сработает (старые обработчики живут) — только для разработки.

## Высокая

**H1. Двойная родная награда у подхваченного постоянного отряда.** KMM_Outlaws.lua:771-779 (adopt) + :893 (watch).
Сценарий: постоянная банда грузится в зоне игрока; в кадре adopt `getSquadLeader()` ещё nil (зона догружается) → `lv.named` не ставится →
через ≤9 с watch видит `not lv.named` и зовёт `M.dress` → `native_bounty` добавляет ВЕСЬ `o.bb` к лидеру, у которого награда ядра уже лежит
в сейве с прошлого спавна. Каждая такая перезагрузка удваивает награду в окне персонажа.
Исправление: в adopt ставить `lv.adopted = true`; в watch для `lv.pk/adopted` вместо `M.dress` — переименование + `M.top_up` (только разница).

**H2. Осиротевшие постоянные отряды (S3 плодит дубли).** KMM_Outlaws.lua:721, :757-761, :708-709.
Сценарий: (а) ключ платуна не прочитан → `o.pk = "?"`, find_pl по ключу его никогда не найдёт; (б) отряд не найден однократно (фракция не
отдалась, отряд за пределом `persist_scan`=600 в списке, переход active↔unloaded, состояние дирижёра взято из `last.kmmstate`/файла, а не из сейва) →
`persistent lost`, `o.pk = nil` БЕЗ `setPersistentSquad(false)` → `vis` спавнит нового и делает его постоянным; старый живёт в сейве вечно.
`persist_max` считает только записи с pk, сироты не считаются — рост без потолка за долгую игру.
Исправление: при отказе ключа — не делать отряд постоянным (сразу `setPersistentSquad(false)`); «lost» — только после N промахов подряд (`o.pk_miss`),
и потолок по фактическим постоянным отрядам фракции (подсчёт `isPersistentSquad` с именем банды), а не по записям.

**H3. Указатели Platoon переживают загрузку другого сейва.** KMM_Outlaws.lua:16/880-886 (M.live), kmm_diplo.lua:367-368 (rival_talk), KMM_Fates.lua:548-553.
Сценарий: игрок загружает другой сейв без перезапуска игры. `M.live` (pl = Platoon* прошлого мира) не сбрасывается; ключи `"o<i>"` совпадают
с записями нового состояния → watch зовёт `lv.pl:getActivePlatoon()`/`getSquadLeader()` по освобождённой памяти; для `lv.pk` S3 продлевает `lv.t`
бесконечно, пока мусор возвращает не-nil. pcall не ловит access violation → возможен вылет. Diplo каждые 4 с читает тот же `live` и зовёт
`lv.pl:getSquadLeader()` (даже без pcall). Было и до S3 (окно watch_s=30 мин), S3 делает окно бесконечным.
Исправление: запоминать `M.live_S = C.state()` и при смене таблицы состояния очищать `M.live`/`M.adopt_t` (так же в Fates); в Diplo — `HK.rivals = {}` там же.

**H4. Одно дело → две награды (Outlaws + Fates).** KMM_Fates.lua:274-279 (outlaw_owns) против KMM_Outlaws.lua deed_who (≈:569-582).
Сценарий: дело `deed` фракции X. Outlaws отдаёт его ближайшему разыскиваемому X в радиусе 30 км (даже без живого отряда), Fates — ближайшему
герою X в том же радиусе. `outlaw_owns` проверяет только ЖИВУЮ названную банду, поэтому при отсутствии живой банды награду получают оба
(две записи в хронике, у живого героя — ещё и родная награда ядра). Исправление: в Fates звать `OM.deed_who(OM.O(S), OM.cfg(), ev)` и уходить, если он вернул запись.

## Средняя

**M1. CORESYNC: двойной счёт и дрейф силы.** KMM_Conductor_Sync.lua:476-497 (вливание дельты getFactionSize в `f.strength`).
Сценарий: живой бой у игрока уже снижает силу через события (Econ:850-855 `waylay_repelled`, Econ:949-961 `l2_selfhit`, `base_result`),
а гибель тех же NPC даёт падение getFactionSize → вторая дельта в той же цепочке. Наши спавны (Traces/Outlaws/Fates/dispatch, постоянные S3)
поднимают размер фракции → модельная сила растёт от собственных спавнов; загрузка/выгрузка зоны <50% (`jump`) вливается как реальная.
Исправление: вливать только падения с подсказкой destroyPlatoon (hot) и вычитать отряды, заспавненные модулями; либо `src="platoons"` и `w_str` ниже для роста.

**M2. Повторная «встреча» соперника при каждом adopt.** KMM_Outlaws.lua:781-784 → KMM_Nemesis.lua:1128-1143.
Сценарий: постоянный отряд-соперник с пакетом охоты то грузится, то выгружается у игрока → каждый adopt зовёт `NM.on_spawn`: `X.met++`,
событие `nemesis_return` в хронику, реплика, повторная запись родной памяти. Исправление: в adopt звать on_spawn не чаще раза в игровой день на запись (`o.pg.seen_day`).

**M3. Дубли разговора-угрозы у постоянного главаря.** kmm_diplo.lua:367-376.
Сценарий: `HK.rivals` слабый по таблице `lv`, а Outlaws создаёт новую `lv` при каждом adopt/сессии → `Dialogue:addConversation` повторно добавляет
тот же разговор тому же персонажу (если ядро не дедуплицирует и разговоры живут в сейве — копятся). Исправление: ключ — `o.n`/`o.pk` (строка), а не `lv`.

**M4. Ложная гибель невыгруженной банды (?).** KMM_Outlaws.lua:666-671, вызов :763 для отряда из `getUnloadedPlatoons`.
Сценарий: у выгруженного платуна персонажей нет; если `getCharacterCount()` для него вернёт 0 (не проверено, ?), adopt объявит главаря
погибшим («fell in a fight») при первом же сверочном проходе. Исправление: для `loaded == false` проверять только `p.isDead`.

**M5. Фолбэк `pl._persistentSquad = true` в обход движка (?).** KMM_Outlaws.lua:714-718.
Сценарий: если `setPersistentSquad(true)` не сработал, прямая запись поля ставит флаг без регистрации/учёта ядра (файл платуна, списки фракции) →
отряд может сериализоваться наполовину или некорректно выгружаться. Исправление: убрать фолбэк (FAIL → временный отряд) или передавать
`permanentsquad = true` в `createRandomSquad` (Traces:284, аргумент уже есть в биндинге).

## Проверено, замечаний нет
- kmm_diplo S4: `Dialogue::_checkCondition` — Override, сигнатура `(self, conditionName, compareBy, val, target, actual, defaultVal)` совпадает с `on_check(_, cname, _, val)`;
  nil вне диапазона кодов → ваниль; `DC_FACTION_VARIABLE=6`, `EV_I_SEE_ENEMY_PLAYER=66`, `itemType.DIALOGUE=18` по EnumsReference; регистрация один раз, guarded.
- KMM_Traces/KMM_Self/kmm_stock S5 (такт снимка, кэш PKC/PKT по ключу платуна ≤2000, ленивые тиры Self) — корректно; `pkey` в записи снимка = `getPlatoonStringID`, как прежний ключ Stock.
- KMM_Fates S6: биндинги `FactionRelations:getFactionRelation(Faction)`, `BountyManager:unfairAddToBounty` есть; вызовы под pcall/probe_call; `fate_deed` не зацикливает шину.
- Outlaws S3: `setPersistentSquad/isPersistentSquad/getPlatoonStringID/getBlackboard`, `Blackboard:replaceAIPackage/getCurrentAIPackageName`, `Faction:getActivePlatoons/getUnloadedPlatoons` есть в биндингах.
  `Platoon:getPosition` (:765) — только через базовый RootObjectBase; если sol2 не отдаёт базу, `o.x/o.z` не обновятся (регион соперника в Nemesis:1093 стоит на месте) — не вредно.
- Производительность: find_pl ≤1200 платунов с pcall на adopt, не чаще 1 записи за такт Outlaws (9 с) — допустимо; CORESYNC ≤9 фракций раз в 3 с.
