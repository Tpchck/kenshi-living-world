# REVIEW batch5: Lua-модули перед установкой (2026-11-15)

Что сравнивалось: установленное `Kenshi\mods\KMM_*\scripts` (старое) и `build\KMM_*\scripts` (новое), diff без учёта CRLF.
Изменённые файлы: Traces, Conductor(.lua/Base/Econ/Sync/World), Fates, Nemesis, RelicRace, Rumors, kmm_diplo, kmm_town, kmm_tempo, kmm_elite(+data). Новый: KMM_RecruitRace.
Вызовы сверены с BindingsReference/CallbacksReference/EnumsReference. Все новые методы есть в биндингах: Blackboard:replaceAIPackage(GameData),
Platoon:set/isPersistentSquad, Faction:createNewEmptyActivePlatoon(GameData,bool,Vector3), Character:setFaction(Faction,ActivePlatoon),
ActivePlatoon.me, CharStats:getOverallSkillLevel_0_100, ProductionBuilding.productionState/consumptionItems, ConsumptionItem.amount/maxCapacity,
Building.productionMult, Platoon.traderInventoryRefreshTime(TimeOfDay).time, FactionWarMgr.activeCampaigns, CampaignInstance.uniqueID/currentPhase/manPowerLastCount.
Значения enum совпадают: AI_PACKAGE=72, SQUAD_TEMPLATE=52, BUILDING=0, PRODUCTION_STARVED=0/NORMAL=2, BF_MINE=1/27, BCTYPE_FARM=13, SlaveState NOT_SLAVE=0.
Новые Events.on: `PlayerInterface::recruit(self, character, isEditor)` и `GameWorld::charsUpdate`. Оба обёрнуты в guarded.
Итог: **крит 0 · высокая 4 · средняя 9**.

## Высокая

**H1. U2: исход рейда-кампании опрашивается раз в 5 игровых дней. Из-за этого второй рейд через Traces, а исход теряется.**
Где: KMM_Conductor_World.lua:1001 (`add("base_camp", …)` в `ws_phases`, `tick_days`=5) и KMM_Conductor_Sync.lua:224-266 (`base_poll`/`base_step`).
Сценарий: `base_try` вызывает кампанию в фазе acts. Первый `base_poll` происходит только на следующем тике мира, через 5 дней. Ванильный рейд
(сбор, штурм, победа или отход) обычно заканчивается раньше, и кампании уже нет в `activeCampaigns`. Тогда `st` остаётся "fired", условие `KC.DAY-R.day>bind_days(2)`
даёт "lost", и `base_fallback` шлёт `base_raid`: Traces ведёт ко **второму** рейду на базу, которую ядро уже разграбило. Если кампания успела привязаться,
фаза всё равно читается раз в 5 дней. RETREATING/VICTORY почти никогда не попадают в выборку, поэтому исход чаще всего "faded" (без последствий).
`R.present` тоже почти никогда не ставится.
Исправление: привязывать кампанию сразу в `base_try` (сравнить `camps_of` до и после `CA.fire`). `CA.base_step` вызывать из on_tick раз в ~30 с или раз в игровой час, а не из `ws_phases`.

**H2. U4: единицы `TimeOfDay.time` не проверены. Метка пишется в сейв раньше, чем проба их подтвердит.**
Где: kmm_tempo.lua:782-834 (`tod_get` читает сырое `.time`, `now` = `getTotalDays()*24` в часах; `tod_set` пишет `.time`).
Сценарий: если `.time` хранится в днях (у класса есть отдельные getTotalHours/getTotalDays), то `lo/hi` зажима теряют смысл. При m=0.25 получается
`new = t + 48` **дней**: лавки бедных городов не обновятся полтора месяца. Метка Platoon живёт в сейве, а откат возможен только при выключении блока и только у платунов из снимка.
Маркер `RESTOCK probe` пишется в том же такте, что и запись, поэтому проба ничего не предотвращает.
Исправление: читать `tod:getTotalHours()`, сдвигать `tod:addHours(d)`. Либо в первой сессии только логировать (probe), а писать после ✓игра.

**H3. U3: ванильные данные построек остаются испорченными в сейве, если откатить их нечем (?).**
Где: kmm_town.lua:526-550 (`starve`: `amount=0`, `productionMult*=0.2`), :607 (`famine_enabled=false` сразу return), :460-472 (`U3.store` → `RT.fstore_local`).
Сценарии: (а) `famine_enabled` выключили в конфиге: загруженные остановленные постройки не откатываются, а записи висят в сейве вечно;
(б) нет дирижёра или `town_state()` вернул nil (`KC.S` ещё не готов): изъятое хранится только в памяти сессии, и после сейва и загрузки входы
обнулены без записи; (в) KMM_Town удалён. Если `Building.productionMult` сериализуется (?), ферма навсегда останется на ×0.2. Изъятые входы пропадут всегда.
Исправление: без слота дирижёра U3 не трогать (`fstore_local` убрать). При `famine_enabled==false` один раз пройти `RT.fh` и store текущего города через `U3.restore`.
`productionMult` не трогать (хватит state и входов) или проверить по `productionMult_baseData`.

**H4. U1: отряды, которые ведёт ядро, больше не деспавнятся и копятся у игрока.**
Где: KMM_Traces.lua:1880 (`arrived and t.nat`: зачёт без деспавна), а также `led` у беженцев/бродяг/гонцов/разведчиков/колонн (:695-830, :1265-1300, :1815).
Сценарий: игрок несколько игровых дней стоит в городе. Каждое прибытие (до `max_per_day`=8 в день) раньше деспавнилось вне видимости, теперь отряд остаётся
жить в загруженной зоне. Ядро убирает временный отряд только при выгрузке зоны, а лимиты Traces (`VLIVE` по ttl) реальное число живых не считают.
Через неделю у игрока десятки лишних отрядов, падает FPS. Плюс CORESYNC (M1 batch34) видит рост getFactionSize.
Исправление: у временных nat-отрядов (без ключа в `NAT.reg`) оставить прежний тихий деспавн после прибытия вне видимости, или считать живые по снимку в лимите.

## Средняя

**M1. U1: засада «выслеживание» без явной враждебности.** KMM_Traces.lua:1431-1433 → :1551.
`ordered = led` отключает `ch:attackTarget(...)`. Пакет «Assault target squad» враждебность не создаёт. Если фракции грабителя и каравана
нейтральны, засада дойдёт до каравана и встанет: не будет ни `waylay_repelled`, ни `caravan_lost`. Исправление: `ordered = nil` (attackTarget оставить поверх пакета).

**M2. U1: погибшие постоянные отряды занимают лимит 33 дня.** KMM_Traces.lua:507-512.
Караван ограбили, платун уничтожен, ключа нет ни в одном списке. Запись становится сиротой только через `persist_days+orph_days`=33 дня, и все это время она в `nat_persist_max`=4.
Пара разбитых караванов блокирует U1 на месяц, дальше всё идёт фолбэком. Исправление: если фракция найдена, а ключ не найден `lost_miss` раз подряд, удалять сразу.
Сироту держать только при «нет фракции» (или подписаться на `Faction::destroyPlatoon`).

**M3. U1/V1: отпуск выгруженного платуна (?).** KMM_Traces.lua:503, KMM_RecruitRace.lua:322/350.
`setPersistentSquad(false)` вызывается у платуна из `getUnloadedPlatoons`. Ядро проверяет постоянство при выгрузке (`reCheckPersistenceOnUnload`).
Уже выгруженный «временный» отряд может так и остаться в сейве: утечка без учёта, запись при этом уже удалена.
Исправление: отпускать только найденный в `getActivePlatoons`, выгруженный оставлять в реестре до загрузки.

**M4. U2: привязка к чужой кампании.** KMM_Conductor_Sync.lua:231.
`e.enemy == nil or e.enemy == pf`: если враг не прочитался, к рейду на базу привяжется любая новая кампания фракции, начатая в окне
(CA.try или KMM_Siege за те же 5 дней, см. H1). Исход осады чужого города будет засчитан как исход для базы игрока. Исправление: требовать `e.enemy == pf` (или привязку сразу после fire, H1).

**M5. U2: двойная запись в хронике и слухах.** KMM_Conductor_Sync.lua:220.
После `base_campaign` фолбэк шлёт ещё и `base_raid` (`fallback=true`). Шина Base:497 его пропускает, а Nemesis (CHRON_PLAYER) и Rumors нет:
две записи «идут на поселение». Исправление: в `base_fallback` добавить `quiet=true` и пропускать это в Nemesis/Rumors, или не задавать `text`.

**M6. U3: указатель `RT.anchor` из прошлого мира.** kmm_town.lua:785 (запись), :679 → `U3.collect` → `anchor:getPosition()`.
Стадии цикла идут по одной за вызов тика, ветка стадий стоит раньше опроса (`pcs==0 → leave_town`). Если загрузить сейв посреди цикла,
первый тик выполнит `famine_stage` со старым Character*. Это access violation, и pcall его не ловит. Тот же класс уже был у `RT.sc`, U3 добавляет новый случай.
Исправление: в `famine_stage` брать свежего `player_chars()[1]`. При смене мира или `#pcs==0` сбрасывать `RT.stage`.

**M7. U3: подвоз сверх `maxCapacity` уничтожается.** kmm_town.lua:557-565.
`reassert` в каждом проходе переносит ванильный подвоз в `rec.a` с потолком `maxCapacity` и обнуляет вход. Всё сверх потолка исчезает,
пока постройка голодает (каждый цикл). Исправление: если `rec.a[i]` уже на потолке, вход не обнулять (оставить `amount`, держать только state).

**M8. V1: ложный провал пробы setFaction навсегда выключает модуль, рекрут остаётся в пустоте.** KMM_RecruitRace.lua:233-256.
(а) При `okp and pl` и `ap == nil` созданный постоянный (`permanent=true`) пустой платун не отпускается (:235-239).
(б) `ch:getPlatoon().me` сразу после `setFaction` может ещё указывать на старый отряд. Тогда `k2 ~= key`, `good=false`, `recruitrace.off` навсегда,
хотя фракция уже сменилась, а отряд сделан временным. Исправление: в (а) звать `pl:setPersistentSquad(false)`. Успех считать по `fid2 == race.fid`, ключ сверять в следующем такте.

**M9. U4: каждая новая сессия сдвигает метку заново, получается эксплойт обновления лавки.** kmm_tempo.lua:826-834.
`RS.pl` живёт только в сессии. После перезапуска игры и загрузки сейва уже сдвинутая метка сдвигается ещё раз. При m>1 `lo = min(t, now-2P)` позволяет
увести метку в прошлое, и лавка богатого города обновляется сразу на каждой загрузке. Исправление: сдвигать только «свежую» метку (|t-now| ≤ P)
или хранить `obs` по pkey в `C.state().ext`.

## Проверено, замечаний нет
- Дирижёр, удаление W1 (`try_gear`, `gear_possible`, `gear_day`): ссылок не осталось. `phase_flush`, `_loot_scan`, `M._reset` (RelicRace), `loadTold` (мёртвый код) нигде не используются.
- Base:497 `base_campaign`: шина как у `base_raid`. Traces:543 пропускает его по `native==true` (`nat` в Econ:1442 булево: `a and b and f()` берёт первое значение).
- `base_result("sacked")`: U, f, B, pf в области видимости. Без `nat` ветка недостижима.
- kmm_diplo W1: все используемые API дирижёра экспортируются (KMM_Conductor.lua:85/133/163-165). Без них init молча ждёт. Остаток `treaty_between` только читает.
- Fates `bounty_add`: глобал проверен в `M.OM()`. `C.alive` экспортируется всегда.
- Nemesis/Rumors: только whitelist и префиксы (`base_raid_`, `recruit_`). Elite: удалён `legacy_spawn`, логика упростилась корректно.
- U1: `NAT.reg` хранит строки-ключи в `C.state().ext`, указателей между тактами нет. `NAT.find` раз в 60 с (≤3000 pcall), допустимо.
  Порядок с заказчиками: пакет ставится до `on_spawn`/`NM.on_hunt`, свой пакет модуля ложится поверх. Outlaws S3 пакет на чужие отряды не ставит.
- V1: смена мира сбрасывает `M.rt`, указатели не хранятся, лимит постоянных учитывает сирот, лимит 1 потеря в неделю. Шаблон и пакет читаются через gamedata под pcall.
- Спам логов: U3 ≤200 строк за сессию, RESTOCK раз в сутки на город, NAT по событию. Полные обходы: U3 одна сфера ≤60 объектов за цикл, U4 ≤12 записей за 5 с.
