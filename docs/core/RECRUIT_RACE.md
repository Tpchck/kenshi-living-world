# RECRUIT_RACE — гонка за рекрутами (U6, пакет 5, 2026-11-15; исследование, код не менялся)

Цель: лучших рекрутов разбирают конкуренты-искатели. Не успел — встретишь рекрута позже в чужом отряде: переманишь, выкупишь или победишь.
Решение игрока, которое меняется: «копить деньги и идти в бар сейчас» против «идти в руины/качаться». Пропущенный рекрут не пропадает, он
становится встречей с конкурентом (рост через бой с сильным, P5 CONSTANTS).

## 1. Как ваниль даёт рекрутов (✓код = заголовок/биндинг/данные; данные — kmod-скан ванили gamedata+Newwworld+Dialogue+rebirth)
- **Бары.** TOWN `bar squads` (481 ссылка, 99 разных отрядов, из них 14 «Recruits list …») ✓код. Спавн при загрузке города: `Town::spawnTheBarFlies`
  (Town.h:369, Lua B:13483). Списки `TownBase.residentsSpawned_BarsOrSomething` (Town.h:313, RW B:13584): `ResidentData{data,count,chance,priority}` (Town.h:295-302).
  Бар-рекруты временные: они пересоздаются при каждой загрузке города и в сейве не живут (? по `_persistentSquad=false`, ai_squads.md).
- **Кого можно нанять.** 179 CHARACTER, у которых в `dialogue`/`dialogue package` есть реплика с DA_JOIN_SQUAD_WITH_EDIT(3)/DA_JOIN_SQUAD_FAST(18)/
  CHOOSE_RECRUITING(45). Из них 64 `unique` (Crumblejon, Soman, Reva, Pia, Griffin, Silvershade, Kang, Hamut, Ruka, Hobbs, «Sword for hire *»,
  «Skeleton recruit 2500 swamp», «imprisoned skeleton recruit» …) ✓код. В данных 149 условий DC_IS_RECRUITABLE(77). Семантика условия в ядре — ?.
- **Цена.** 250 реплик найма, у 74 условие DC_PLAYERMONEY(2) с порогом в v0 ссылки: 6000×27, 3000×25, 7500×11 … ✓код. Списание делает DA_TAKE_MONEY(8)
  (`DialogLineData::getMoneyCostForLine`, Dialogue.h:253). Цена статична.
- **Бродячие рекруты `[recruitable]`** есть только в модах (напр. V-One Squad, Old ironsides). В ванили таких homeless-отрядов 0 ✓код. B1 чинит их фракцию.
- **Рабы/пленные.** CHOOSE_SLAVES_BUYING(42)/SELLING(41), CHOOSE_PRISONER_BAIL(43) (Dialogue.h:74-83). Купленный раб входит в отряд игрока.
  Смена хозяина: `Character::changeSlaveOwner(hand)` (Character.h:602, B:3458, Notify C:95) ✓код.
- **ИИ сам рекрутов не нанимает.** TaskType RECRUIT_AT_JOBCENTER (Enums.h:334) и `AI::findGoodRecruitNode` (AI/AI.h:426) есть ✓код, но в данных они не
  используются, и смысл у них не наш (?). Значит, «конкурент нанял» в ваниле не бывает. Это делаем мы, через рычаги ядра ниже.

## 2. Рычаги
| рычаг | точка ядра | Lua | статус | в проекте |
|---|---|---|---|---|
| Перевести персонажа в чужой отряд | `Character::setFaction(Faction*, ActivePlatoon*)` Character.h:514 | B:3337; Notify `Character::_NV_setFaction` C:41 | ✓код, ни разу не звали | нет |
| Новый отряд фракции | `Faction::createNewEmptyActivePlatoon(tpl, permanent, pos)` Faction.h:74; `…UnloadedPlatoon` :73 | B:5724/5723 | ✓код | нет |
| Отряд живёт в сейве | `Platoon::setPersistentSquad` Platoon.h:168 | B:10678 | ✓код, ✓путь | Outlaws:735 (probe_call) |
| Сменить фракцию всего отряда | `Platoon::setFaction(Faction*)` Platoon.h:114 | B:10647 | ✓код; с выгруженным отрядом ? | нет |
| Миссия отряда-конкурента | `Blackboard::replaceAIPackage` | B:2286 | ✓код | Outlaws S3; rivals long-range clones в fix.py:468 |
| Игрок нанял (отмена гонки) | Notify `PlayerInterface::recruit(ch, isEditor)` PlayerInterface.h:116 | C:57 | ✓код | нет |
| Пришёл/ушёл из отряда | Notify `ActivePlatoon::_NV_addActiveObject/_NV_removeObject` | C:60 | ✓код | нет |
| Опознать рекрута | `RootObjectBase:getGameData().stringID`, `Character:isUnique()` Character.h:197 | B:6666, 3170 | ✓код | нет |
| Найм наёмника конкурентом | `Blackboard::setContractJob(pkg, giverHand)` | B:2278 | ✓код | нет |
| Реплика «выкуп/переманить» по миру | Override `Dialogue::_checkCondition` (DC_FACTION_VARIABLE «KMM_WORLD») | C | ✓код, хук есть | kmm_diplo.lua:13,285 |
| Конкуренты в барах | ванильный пакет «hang out in a bar» 14499 у 23 rival-отрядов | данные | ✓код (данные), в игре не проверено | fix.py rivals (Q1) |
| Сила рекрута/конкурента | `getOverallSkillLevel_0_100` | B:4067 | ✓код | Outlaws/Fates |
| Купить раба конкурентом | `changeSlaveOwner(rivalLeaderHandle)` | B:3458 | ✓код; как поведёт себя клетка лавки ? | Conductor (пленные) |

Нет рычага из Lua: держать бар-рекрута «занятым» в выгруженном городе. Бар-рекруты появляются только при загрузке города, поэтому дальний мир
ведём своей записью (S.ext.recruitrace), а она лишь решает, что произойдёт при следующей загрузке города (обоснование «своей переменной»).

## 3. Варианты реализации
### A. Гонка в баре загруженного города (рекомендуется первым)
- Генератор `tools/conductor/gen_recruits.py` (kmod, новый) пишет `build/KMM_Conductor/recruits.json`: sid CHARACTER рекрута → цена
  (DC_PLAYERMONEY v0), unique, тир. Белый список: «чистые» рекруты без квестов. Ruka, Dust King, Griffin и прочие сюжетные исключаются правилом.
- `KMM_RecruitRace.lua` (новый) на такте Gov (3 с), только у города, где стоит игрок:
  1) находит рекрута из списка и rival-отряд (фракции rivals из fix.json) в радиусе бара и заводит таймер на N игровых часов;
  2) Notify `PlayerInterface::recruit` по этому рекруту снимает таймер и даёт слух «перехватил у X»;
  3) таймер истёк: `ch:setFaction(rivalFaction, rivalAP)` под probe_call, затем `setPersistentSquad(true)` на отряде конкурента и `C.emit`
     с текстом «Tech Hunters hired Kang at the Squin bar». Запись в S.ext.recruitrace: имя, sid, навык, id отряда.
- Встреча позже: отряд постоянный, поэтому в мире ходит тот же персонаж. Конкурент ходит по карте ванильным long-range пакетом из Q1.
  Его можно найти слухом (R2: метка на карте).
- Чем игрок может вернуть рекрута (всё ванильным диалогом):
  а) выкуп: реплика с DC_PLAYERMONEY > цена×1.5, затем DA_TAKE_MONEY и DA_JOIN_SQUAD_FAST;
  б) переманить: та же реплика без денег, если лидер отряда в нокауте или мёртв (новый код KMM_WORLD в хуке Diplo);
  в) победить: XP за бой с сильным; выжившего можно взять в плен, продать работорговцам и выкупить в лавке рабов.
- Владение: KMM_RecruitRace.lua, `_dev/test_recruitrace.py`, gen_recruits.py, recruits.json. Diplo (kmm_diplo.lua, rules/streams/diplo.json)
  добавляет один код KMM_WORLD и реплику выкупа. Это владелец Diplo, по согласованию.
- Риски: (1) `Character::setFaction` в чужой ActivePlatoon ни разу не проверен (?): старый отряд может остаться пустым, бар-пакет может «держать»
  персонажа. Нужна проба на одном рекруте, маркер `setFaction ok/FAIL` и самоотключение. (2) DC_IS_RECRUITABLE после смены фракции (?):
  реплика найма может остаться и тогда, когда лидер жив. Тогда закрыть её условием KMM_WORLD. (3) Сейв новой игры не нужен, но
  перенос персонажа пишется в сейв навсегда.
### B. Уникальные рекруты в дальнем мире (через Fates, после A)
- Герой Fates с ролью mercenary или relic hunter выбирает город уникального рекрута из белого списка как цель судьбы. Через N дней, если игрок
  не нанял рекрута (Notify recruit или проверка фракции при загрузке города), при следующей загрузке города рекрут переходит в новый отряд:
  `createNewEmptyActivePlatoon(шаблон героя, permanent=true, pos)` → `setFaction` → `replaceAIPackage` (roam long range).
  Лидер отряда переименовывается в имя героя (как в Fates). Хроника: «Pia left Mongrel with the crew of Rakor the Knife».
- Владение: KMM_Fates.lua (владелец Fates) плюс общий с A модуль переноса. Риск выше: уникальные персонажи бывают в квестах и в town residents
  (`residentsSpawned`). Как ведёт себя `Platoon::setFaction` у выгруженного отряда — ?. Поэтому только загруженный город и только белый список.
### C. Только данные, без переноса (страховка, если в A провалится проба)
- rival-отряды в fix.json rivals получают в `choosefrom list` тех же CHARACTER-рекрутов («Sword for hire *», скелеты-рекруты), а в бар-списках
  у TOWN `bar squads` (town.py) снижается chance у тех же шаблонов. Рекрутов в баре становится меньше, у конкурентов они появляются.
  Выкуп — реплика по A(а). Риск низкий, но гонки по-настоящему нет: это иллюзия, и игрок не встретит именно своего рекрута.
- Владение: fix.py/fix.json (rivals), town.py. Конфликт полей: `bar squads` принадлежит town.py, и chance правит только он.

## 4. Другие рычаги «встреч с конкурентами» для нелинейного роста (в BACKLOG их нет)
1. **Перехват пленника охотника.** Охотник несёт разыскиваемого живым: DC_CARRYING_BOUNTY_ALIVE(4), задача FIND_CAGE_AND_PUT_IN_IF_BOUNTY ✓код.
   Игрок может отбить пленника и сдать сам, ванильная оплата уйдёт ему. Нужен слух «охотник X ведёт Y в Z», остальное есть в Traces BNT и Outlaws.
2. **Конкурент перекупил наёмников.** `setContractJob(pkg, rivalLeaderHandle)` на отряд гильдии наёмников ✓код. Игрок встретит конкурента с охраной,
   а наёмники уйдут сами по контракту: окно для атаки. Предательство отслеживает ядро (EV_BETRAYAL, economy_player.md).
3. **Невольничий рынок наперегонки.** Конкурент-работорговец покупает в загруженной лавке самого сильного раба (`changeSlaveOwner` ✓код,
   поведение клетки ?). Если игрок освободит раба позже, ядро запомнит это (LT_FREED_ME, через плагин P4), а ванильная реплика ex-slave
   («Sword for hire ex-slave») позволит его нанять.
4. **Вызов на поединок без войны фракций.** Реплика лидеру-сопернику DA_FLAG_TEMP_ENEMY(21) ✓код (данные). Бой идёт один на один до нокаута,
   XP за сильного (P5). Что временный враг не добивает противника — ?. «Додзё/турниров» в ядре нет. Площадку под это не делаем:
   по правилу «без декора» берём только этот диалоговый поединок.
5. **Реликты/руины.** KMM_RelicRace уже есть, его лут условный. Новое: rival-отряды с пакетом LOOTING (fix.py Q1) реально опустошают ящики руин,
   если руины загружены рядом с игроком. Чтение и запись инвентаря контейнера из Lua — ?, нужна проверка по биндингам.

## 5. Рекомендация
Начать с A, в одном загруженном городе. Первым делом проба `Character::setFaction` с маркерами `recruitrace: setFaction ok/FAIL` и
`recruit cancel by player`. Выкуп — одна реплика через существующий хук Diplo. B делать только после маркеров A из живой игры. C держать
запасным, если проба A провалится. Из §4 самый дешёвый — №1 (перехват пленника): его рычаги почти все уже в Traces и Outlaws.
Новая игра для A не нужна: перенос касается только бар-рекрутов, которые и так создаются заново.
