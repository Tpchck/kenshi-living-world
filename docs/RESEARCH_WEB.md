# RESEARCH_WEB: Kenshi, веб-разведка (2026-11-14)

Метод: WebSearch/WebFetch, малый бюджет. Многие страницы дали 403/404/429 (Nexus, kenshi.wiki, Steam). Всё, чего нет в явном виде в источниках, помечено [НЕ ПРОВЕРЕНО] (из общих знаний, требует сверки по fcs.def или нашим .mod).

## 0. Что реально подтверждено

- RE_Kenshi: последний релиз v0.3.4 (Kenshi 1.0.65 и 1.0.68, Steam и GOG), плагины с 0.3.0. https://github.com/BFrizzleFoShizzle/RE_Kenshi/releases (уверенность высокая)
- Фичи RE_Kenshi (вики, версия страницы 0.2.18): EmergencySaves при краше (`EnableEmergencySaves` в RE_Kenshi.ini), `FixModListScroll`, переопределение лимитов мода из игры (attack slots, max squad size, max faction size, max squads, значения 1-1000; отряды больше 256 дают глюки UI), `IgnoreHash`, ускорение загрузки (heightmap, skip splash, mipmaps, PhysX cache), JSON-схема RE_Kenshi.json, file rebinding, soundbanks. https://github.com/BFrizzleFoShizzle/RE_Kenshi/wiki/RE_Kenshi-Features
- Для нас: лимит отрядов и фракций можно поднять из игры, если динамические отряды упираются в max squads. Это поле в UI, не в моде.
- KenshiLib_Examples (6 плагинов): HelloWorld, KillButton (MyGUI), Dialogue (новые dialogue conditions/effects + FCS-плагин Dialogue_FCS), WorldStates (целочисленные переменные в FCS, меняются диалоговыми событиями, проверяются world states, демонстрирует свои GameData-типы и сохранение состояния), PluginImport/PluginExport (PreloadPlugin), CharacterHighlight. Нужен RE_Kenshi >= 0.3.1; сборка только RELEASE (DEBUG сломан). https://github.com/BFrizzleFoShizzle/KenshiLib_Examples/
  - Для нас: пример WorldStates это эталон персистентных своих переменных в сейве (в духе "связывать ванильные механики"). Спавна и хуков в примерах нет.
- KenshiLib канонически: https://github.com/BFrizzleFoShizzle/KenshiLib (есть форки: https://codeberg.org/iam/KenshiLib, NuGet KenshiLib 1.0.1 https://packages.nuget.org/packages/KenshiLib/).
- KenshiLua (Nexus 2068): DLL с Lua-рантаймом, ~7000 биндингов KenshiLib, требует RE_Kenshi >= 0.3.3; документация в папке `./docs/` репозитория KenshiLua; примеры: Go Prone (callback), Crooked Dice (Lua в диалогах). https://www.nexusmods.com/kenshi/mods/2068 (прямой доступ дал 403; данные из поисковой выдачи). Воркшоп-страницу 3817000612 и BindingsReference/CallbacksReference поиск не нашёл: [НЕ ПРОВЕРЕНО], читать локально из папки мода.
- OpenConstructionSet (OCS): C# SDK, MIT, NuGet 4.1.0. Читает/правит/сохраняет .mod .info .base .save .zone .platoon .level; список активных модов и load order; ModDataContext объединяет несколько модов; есть пример патчера (SCAR pathfinding fix). Python-версии нет (только через pythonnet). https://github.com/lmaydev/OpenConstructionSet , https://www.nuget.org/packages/OpenConstructionSet/
  - Для нас: самый зрелый способ программно собирать итоговый мод-патч и анализировать load order; наш kmod.py читает сейвы, OCS можно использовать как эталон формата.
- Ванильное по баунти: кримы-баунти спадают со временем, если персонаж не "notorious"; баунти выше примерно 10000 делает ноториусом (не истекает). https://kenshi.fandom.com/wiki/Bounty (средняя уверенность, вики)

## 1. Семантика данных FCS (по большей части НЕ подтверждена вебом)

Поиск не дал ни одной страницы с точным описанием; kenshi.wiki (Imports:Using_the_FCS, How_to_make_a_new_race, Why_load_order_matters) отдавали 404/403 на прямую загрузку. Ссылки для ручного чтения (существуют по выдаче поиска):
- https://kenshi.wiki/w/Forgotten_Construction_Set
- https://kenshi.wiki/w/Imports:Using_the_FCS
- https://www.kenshi.wiki/w/Imports:How_to_make_a_new_race
- https://kenshi.wiki/w/Imports:Why_load_order_matters_and_other_FAQ_about_using_mods
- Японская вики со списком типов объектов FCS: https://wiki3.jp/kenshijp/name/FCS
- Релиз-ноты GOG: "Added documentation for FCS", описания val0/1/2 стандартизированы в fcs.def: https://gogdb.org/product/1193046833/releasenotes . ВЫВОД: первоисточник для val0/val1/val2 это наш локальный `fcs.def` (искать описания reference-полей clothing/weapons). Приоритет 1.

Подтверждено слабо:
- Chance для оружия: у многих NPC несколько видов оружия, но они не появляются, потому что chance у всех = 0 (игра по умолчанию). Источник: описание мода https://www.nexusmods.com/kenshi/mods/526 (по выдаче; средняя). Практика: в CHARACTER weapons/clothing val1 = шанс (в процентах) [НЕ ПРОВЕРЕНО], сверять с fcs.def.

Рабочие гипотезы из общих знаний (все [НЕ ПРОВЕРЕНО], проверять по fcs.def и нескольким ванильным CHARACTER):
- clothing/armour в CHARACTER: ссылка на ARMOUR + chance; на каждый слот игра выбирает среди кандидатов, которые подходят слоту, по шансу. Слоты определяются самим предметом (section), а не ссылкой.
- FACTION "not real": фракция-контейнер для спавна/сквадов, не участвует в дипломатии и в UI отношений. Точный эффект на ИИ неизвестен.
- Отношения: FACTION relations перекрывают default relation; значения -100..100. Точный механизм охраны (crime, trespass, enemy classification) в вебе не найден.
- Подрасы и условия диалога: матчится по ссылке на RACE через "my race / target race" (подраса это отдельный RACE, не отдельное поле). Особенно важно для Shek/Hive: диалоги на базовую расу могут не срабатывать на подрасу.
- Зафиксированный пример проблем: сообщения "Missing race: Greelander" и голые NPC при неверном порядке загрузки (r/Kenshi, октябрь 2024): https://lr.in.psf.lt/r/Kenshi/comments/1g5bopy/missing_armor_mod_meshestexturesicons_and_missing

## 2. Миры, кампании, оверрайды городов

Веб-источников по механике переключения town variants и FACTION_CAMPAIGN не найдено.
- Mod "Living World" (Mad Scientist): world-state триггеры, города меняют владельца при гибели ключевых NPC, союзный игрок может влиять на победителя, больше баунти, охотники за головами. Новых фракций не добавляет. Совместим с Reactive World, но есть мелкие проблемы на севере карты; в комментариях сообщали краш в паре с Holy Nation Outlaws Extended. https://catalogue.smods.ru/archives/37197 , https://steamcommunity.com/sharedfiles/filedetails/comments/1470515023
  - Применение: разобрать его WORLD_STATE/TOWN/FACTION поля как образец смены владельца (локально, распаковав .mod через нашу утилиту).
- Нужно изучить его на уровне .mod, а не по описанию.

## 3. KenshiLua / RE_Kenshi / KenshiLib (API, ограничения)

- Нет подтверждённых веб-материалов по loadstring, сериализации, createRandomSquad, BountyManager. Всё это читать в `docs/` KenshiLua (локально, там BindingsReference/CallbacksReference).
- Персистентное состояние: образец через KenshiLib C++ это плагин WorldStates (см. п.0). Для Lua сохранение, вероятно, нужно вести через ванильные GameData/world state переменные [НЕ ПРОВЕРЕНО].
- Безопасный путь по ограничению риска: использовать события-колбэки (как Go Prone) вместо тяжёлых циклов в основном потоке.

## 4. Краши и порядок загрузки

- Общее правило вики: подписываться на все prerequisites; патчи совместимости грузить после патчируемых модов; графика/звук ниже. Источник: https://kenshi.wiki/w/Imports:Why_load_order_matters_and_other_FAQ_about_using_mods (по выдаче).
- Kenshi Fixer (Nexus): утилита диагностики и генерации fix-мода по активному load order. https://www.nexusmods.com/kenshi/articles/182 (по выдаче, уточнить).
- Удаление Zone Data (zone-файлы пересоздаются) помогает при поломках зон после смены модов: https://steamcommunity.com/workshop/filedetails/discussion/3211907381/6853996208331820875 (по выдаче; с учётом нашего save-safe режима только с согласия).
- Анимации на расах, отсутствие скелетов/мешей, Extra Inventory Sections: материалов в вебе не найдено [НЕ ПРОВЕРЕНО]. Практика: проверять наличие файлов, на которые ссылаются .mod, офлайн скриптом.
- Производительность 600+ модов: RE_Kenshi ускорение загрузки (п.0) и перенос лимитов отрядов.

## 5. Существующие моды для изучения

| Мод | Что делает | Ссылка |
|---|---|---|
| Living World | смена владельцев городов, баунти-хантеры | https://catalogue.smods.ru/archives/37197 |
| Reactive World | реакции мира, совместим с Living World | см. комментарии 1470515023 |
| Universal Wasteland Expansion | динамические события, захваты городов, крестовые походы, пересмотр фракций | https://www.nexusmods.com/kenshi/mods/1140 (по выдаче) |
| Holy Nation Outlaws Extended | изгои, выкуп баунти у pacifier | Steam changelog 1980348818 |
| More Bounties | постеры для лидеров малых банд | поиск |
| Bounty Hunting for Minor Factions | оплата баунти у фракций | поиск |
| Kenshi Virtual Simulation Engine | внешняя симуляция фоновых NPC | https://problemchild1500.itch.io/kenshi-virtual-simulation-engine |
| Kaizo | оверхол | поиск |

Механизмы (поля FCS) в вебе не описаны, требуется распаковка и чтение самих .mod. [НЕ ПРОВЕРЕНО] какие именно.

## 6. Инструменты

- OpenConstructionSet (C#, MIT): см. п.0.
- KenshiLib NuGet и Codeberg-форк: см. п.0.
- FCS extended (плагин, упомянут в README примеров, версия >= 1.0.3.0), нужен для кастомных FCS-плагинов.
- Альтернативных CLI для FCS и форматных ридеров сейвов (кроме нашего kmod.py) не найдено.

## Top 10 для нас

1. Прочитать локальный `fcs.def` по val0/val1/val2 для CHARACTER clothing/weapons; сверить с 5-10 ванильными NPC (самый дешёвый и надёжный источник). Высокая.
2. Прочитать `docs/` KenshiLua (BindingsReference/CallbacksReference): спавн отрядов, баунти, отношения; веб этого не даёт. Высокая.
3. Использовать пример WorldStates (KenshiLib_Examples) как шаблон персистентных переменных и привязки к ванильным world states. Высокая.
4. Распаковать "Living World" и "Universal Wasteland Expansion" и разобрать их WORLD_STATE/TOWN/FACTION поля как образец динамических войн/смены владельцев. Средняя.
5. Не ставить сочетания с известными конфликтами (Living World + Holy Nation Outlaws Extended) без теста на сейве-копии. Средняя.
6. Поднять лимиты max squads/faction size через RE_Kenshi UI, если динамические спавны упрутся в них (отряды >256 дают визуальные баги). Высокая.
7. Включить `EnableEmergencySaves` (по умолчанию) и FixModListScroll; для долгой загрузки 600+ модов использовать оптимизации RE_Kenshi. Высокая.
8. OCS (C#) как проверочный инструмент load order и сборки патчей; рассмотреть однократный скрипт валидации ссылок. Средняя.
9. Скрипт валидации офлайн: отсутствие рас ("Missing race"), мешей, скелетов, анимаций, ссылок на удалённые моды (симптом: голые NPC). Средняя.
10. Помнить про механику баунти: >~10000 делает ноториусом (не спадает); учитывать при выдаче баунти странникам-преступникам. Средняя.

Незакрытые вопросы (искать локально или у авторов): точный эффект "not real" и "fundamental type", правила агрессии охраны, матчинг подрас в диалогах, поведение FACTION_CAMPAIGN, loadstring/сериализация в KenshiLua, ARMOUR "races exclude".
