# REVIEW batch6: Lua-модули пакета 6 перед установкой (2026-11-15)

Что сравнивалось: установленное `Kenshi\mods\KMM_*` и `build\KMM_*`, diff без учёта CRLF. Изменены: KMM_Outlaws (X1), KMM_RecruitRace (X2),
kmm_diplo + kmm_diplo_data + KMM_Diplo.mod (X3), KMM_Conductor_Runtime (KC.duel), KMM_RelicRace (X4). Новый файл: KMM_Conductor/rivals.json.
Сверено с BindingsReference/CallbacksReference/EnumsReference и заголовками KenshiLib. Сигнатуры совпадают:
Character.isCarryingSomething (поле), getCarryingObject→hand, hand:getCharacter/toString, Blackboard:setContractJob(GameData, hand) /
_setContractJob(GameData, int, hand) / hasContractJob / getContractExpiryTime, Character:changeSlaveOwner(hand) / getMySlaveOwner / isSlave,
Character::setChainedMode (Notification, `(self, on, ownerHandle)`), Character:clearTempEnemyStatus(Character), Dialogue:addConversation(GameData, EventTriggerEnum),
Inventory:removeItemDontDestroy_returnsItem(it, n, bool) / addItem(it, n, bool, bool) / hasItem(Item) / removeItemAutoDestroy(it, n), Building:isAShop,
RootObjectBase:hasFaction. Enum: DA_ATTACK_CHASE_FOREVER=6, DA_FLAG_TEMP_ENEMY=21, EV_PLAYER_TALK_TO_ME=1, DIALOGUE=18, DIALOGUE_LINE=19, AI_PACKAGE=72,
IS_SLAVE=1, LT_FREED_ME=3, LT_STOLE_FROM_ME=4. Коды KMM_WORLD 31–33 не пересекаются с 1–24. Старые sid диалогов в данных не сдвинулись.
Итог: **крит 0 · высокая 5 · средняя 7**.

## Высокая

**H1. X3: после сбоя или смены мира посреди поединка фракция получает «амнистию» до перезапуска.** kmm_diplo.lua:624 (`spare_until = math.huge`), :566 и :681 (`X3.cur = nil` без сброса), :702 `X3.spared`, :925 guarded.
Сценарий: (а) игрок загрузил другой сейв посреди поединка. Тогда :681 или :566 обнуляет `X3.cur`, а `spare_fid/spare_until=∞` остаются;
(б) любая ошибка в `X3.step/finish` выключает `duel_step` (DISABLED), а `X3.cur` так и висит. В обоих случаях `KC.duel(fid)` (Runtime:402, :417) до конца
сессии возвращает true. Удары по любому NPC этой фракции не дают ни player_raid, ни attack_on_player, ни памяти Nemesis, договоры не рвутся. Это эксплойт и тихое отключение реакции ядра.
Исправление: при каждом сбросе `X3.cur` ставить `X3.spare_fid=nil`. В `on_start` вместо ∞ писать `spare_until=os.clock()+duel_timeout_s+duel_loot_s+duel_spare_s`.

**H2. X3: DA_ATTACK_CHASE_FOREVER и вражда отряда не снимаются, поединок не один на один (?).** diplo.py:552-553, kmm_diplo.lua:628-636 `X3.clear`.
Сценарий: ванильное «Attack, chase forever» работает на отряд говорящего, а цель погони живёт в AI отряда (и, видимо, в сейве). `clearTempEnemyStatus` снимает
тег ST_TEMPORARY_ENEMY только у самого лидера. Товарищи по отряду продолжают бой и погоню. Лидер очнулся: цель погони могла остаться, и бой начинается снова.
Через `duel_spare_s` их удары уже считаются attack_on_player и player_raid, что рвёт договоры (Diplo :874). В городе может вмешаться стража.
Исправление: в `X3.clear` пройти всех членов `d.npc:getPlatoon()` (clearTempEnemyStatus в обе стороны + `reThinkCurrentAIAction()`). Либо заменить CHASE_FOREVER
на DA_ATTACK_STAY_NEAR_HOME (55). В `on_ask` отказывать, если `pc:getCurrentTownLocation()~=nil`.

**H3. X3: разговор вызова у лидеров Mercenary Guild может перекрыть ванильный найм (?).** kmm_diplo.lua:577-590 (RF включает `1214-gamedata.base`), diplo.py:545 (`score bonus` 60).
Сценарий: X3.scan раздаёт EV_PLAYER_TALK_TO_ME-разговор с бонусом 60 каждому лидеру отряда rival-фракции в 6000 от игрока. Сюда попадают и барные
наёмники гильдии, и торговцы (`rec.trader` не исключён). Если ядро выбирает разговор с наибольшим счётом, то при `duel_open` (почти всегда true) игрок вместо
«нанять» видит вызов на поединок. Найм наёмников ломается. Если разговор пишется в сейв (Dialogue::save, см. M5), то навсегда.
Исправление: в скане пропускать `rec.trader`, `rec.town` и отряды без боевого шаблона Q1; бонус 0 (ниже ванильных); проверить в логе первого разговора.

**H4. X4: вскрытие логова безвозвратно уничтожает предметы, в том числе вещи, которые игрок спрятал в ящиках руин.** KMM_RelicRace.lua:384 (`removeItemAutoDestroy`), :388, :449, :505.
Сценарий: игрок оказался в 8000 от вскрытого логова. Тогда 6 самых дорогих стопок из любых не-магазинных и не-игроцких ящиков в 2500 уничтожаются целиком,
и это могут быть вещи, сложенные игроком в ящик руин. В stash попадает ≤8 записей по `min(q,5)` шт., чемпион получает ≤12 шт. Если экспедиция не выиграла, если чемпион уже
выходил (`issued>0`) или прошло `dug_ttl`, stash стирается (:505). Добыча пропадает в никуда. Плюс `ch.loot=nil` ставится даже при `give_loot`=0 (:247).
Исправление: не уничтожать, а переносить (removeItemDontDestroy) в инвентарь лидера экспедиции, если он загружен, иначе не трогать. Ящики брать только `not b:hasFaction()`,
только с вещами, sid которых есть в луте логова (fix.json treasure).

**H5. X2: changeSlaveOwner меняет хозяина, но раб остаётся в клетке лавки, и купить его больше нельзя.** KMM_RecruitRace.lua:621.
Сценарий: у раба из клетки торговца хозяином становится лидер бродячего отряда работорговцев. Перевода в отряд покупателя нет. Отряд уходит (или деспавнится, хендл
становится битым), а раб так и сидит в клетке: лавка его больше не продаёт, он ничей. Изменение навсегда в сейве, ≤1 раз в неделю.
Исправление: после подтверждения переводить раба в отряд покупателя (`setFaction(fac, buyer.ap)`, как V1) или брать только постоянные отряды-покупатели.
Либо выключить рычаг (`slave`), пока переноса нет.

## Средняя

**M1. X2 против U1/S3/Nemesis: контракт наёмников ставится на отряды с нашими пакетами.** KMM_RecruitRace.lua:507-515.
Фракция 1214 есть в rival-списке. Постоянные рекруты V1 (Wandering), охотники Nemesis/Outlaws и nat-отряды Traces этой фракции проходят фильтр (`not has_contract`, `not trader`).
Контракт Bodyguard на 48 ч перебивает охоту и маршрут. Исправление: пропускать `pl:isPersistentSquad()` и ключи из Traces NAT.reg/Outlaws live, брать только `rec.town` (бар).

**M2. X1: ложный «перехват» по имени + LT_STOLE_FROM_ME у стражника.** KMM_Outlaws.lua:1105, :1087.
`h[3] == e.who` срабатывает, когда игрок несёт любого персонажа с тем же родовым именем («Dust Bandit»). Тогда событие outlaw_captive_taken и родная долгая
память «украл у меня» у охотника (часто постоянный стражник) на всех персонажей игрока. Исправление: по имени сверять только при `key == nil`, иначе только по hand.

**M3. X2: двойная память и двойное событие при освобождении раба.** KMM_RecruitRace.lua:687-705 против KMM_Nemesis.lua:1445-1449 (`N.debt(ch,"freed")` → debt_made, позже LT_FREED_ME).
Взлом оков игроком даёт debt_made (Nemesis) и recruit_slave_freed: в хронике и слухах две записи. LT_FREED_ME пишется сразу и потом повторно при возврате долга.
Фолбэк «игрок в 400» засчитывает игроку и снятие оков самим хозяином. Исправление: при `N.lock_t` в окне не писать remember (это сделает Nemesis), фолбэк по дистанции убрать.

**M4. X3: Character* поединка после загрузки сейва.** kmm_diplo.lua:678-697.
`d.world ~= S()` защищает, только если дирижёр уже сменил таблицу состояния. Если такт Diplo (раз в 1 с) идёт раньше, `down_of(d.npc)` читает освобождённую
память: это access violation, pcall его не ловит (класс batch5 M6). Исправление: в начале `X3.step` проверять, что `d.pc` есть в свежем `player_chars()` (сравнение указателей), иначе void.

**M5. X3: дубли addConversation.** kmm_diplo.lua:541 и :582, :521.
Один и тот же лидер получает разговор дважды за сессию: соперник Nemesis из rival-фракции идёт по ключу `nemesis|o<i>|pk` и по `q|<pkey>`. `X3.keys` живут
только в сессии, поэтому постоянные лидеры (S3, V1, Fates) получают разговор заново в каждой сессии. У Dialogue есть save/load (Dialogue.h:376), и если список
сериализуется (?), дубли копятся в сейве (как M3 batch34). Исправление: ключ по хендлу лидера `hstr(leader)` и хранить его в `DS().duel.offered` (сейв).

**M6. X2: `tostring(hand)` вместо `:toString()` для хендлов по значению (?).** KMM_RecruitRace.lua:594-596, :627-628, :665.
`getMySlaveOwner()` возвращает hand копией (Traces:265). Без `__tostring` у KenshiLua.hand строка содержит адрес userdata, который новый на каждый вызов. Тогда `ph[os_]`/`byh[os_]`
не совпадают никогда: рычаг молчит. Хуже, если совпадёт по одному пути и не совпадёт по другому: «owner not changed», хотя хозяин уже сменился, и раб остаётся без учёта.
✓игра есть только у `h:toString()` (ledger: ore/stock). Исправление: во всех ключах X2/X3 (и в Gov `h`) брать `:toString()`.

**M7. X4: проба take ложно падает на стопках, которые слились.** KMM_RelicRace.lua:378.
`addItem` для стопкуемых вещей сливает их с уже имеющейся стопкой, и объект `g` может быть удалён. Тогда `dest:hasItem(g)` = false → "lost" → `L.off`: живой разбор руин выключен
до перезапуска с первой же стопки. Исправление: сверять `dest:hasItem(gd, 1)` (перегрузка по GameData) или количество до и после.

## Замечания (не дефекты)
- KC.duel (Runtime:402/:417) пропускает удары по всей фракции дуэлянта, а не только по паре npc/pc. При H1-фиксе лучше сверять и `self/attacker == X3.cur.npc`.
- fix.py:528 `json.dump(..., open(dst, "w"))` без закрытия файла. В CPython файл закроется сам, но лучше `with`.
- rivals.json: «Ancient Adventurer», «Traveller», «Bounty hunters» отнесены к грабителям руин (по пакету LOOTING из данных), это решение данных, не кода.

## Проверено, замечаний нет
- X1: указателей между тактами нет (K.seen хранит строки, охотник ищется заново в снимке); смена мира сбрасывает `M.cap` (:1184); снимок без игроков (Gov:241);
  обход ≤400 записей раз в 15 с, трекинг ≤16 персонажей раз в такт; события не пересекаются с Traces BNT (персонаж игрока исключён); лог: одна строка на новый ключ.
- X2: события recruit_* есть в шаблонах Rumors; рычаги выключаются по отдельности, крэш-сторож probe_rr_*; `M.rt` сбрасывается при смене мира; хук setChainedMode один раз и guarded.
- X3: роли 1088/1089/1092/1093 в данных; WV-коды проверяет только горячий on_check без вызовов движка; события *_duel_* проходят префиксы Rumors и не матчатся
  картой отрядов (нет `leader`); Fates и Econ react_impl их не трогают.
- X4: снимок с ttl 4, сфера ≤80 объектов и ≤12 зданий раз в 30 с; `M.rt.S` сбрасывает champ при смене мира; лимиты site_cap/session_max; R.ruin чистится раз в день.
