# RELICS — поток D (уровни снаряжения, реликты, остатки Империума), 2026-11-11
Файлы: `rules\streams\relics.json`, `tools\streams\relics.py` → `build\KMM_Relics\KMM_Relics.mod`. Сборка: `kmm_build.py --write relics` — **0 ошибок fcs.def, 0 конфликтов** с остальными потоками (core/economy/behavior). 353 записи: 167 новых, 186 дельт.

## Тиры (CORE.md §7) — нативный механизм Kenshi
Тир = клон персонажа с другим `armour grade` (качество брони 0…5) и `weapon level` (производитель оружия с диапазоном уровней моделей). Существующие CHARACTER не меняются (они у ECONOMY): военные отряды перенаправлены на клоны, уникальные NPC не клонируются (37 ссылок оставлены как есть).

| Тир | armour grade | weapon level (уровни моделей) | Смысл |
|---|---|---|---|
| T0 обноски | 0 | -Expired- (5–30) | ржавчина, хлам |
| T1 | 2 | Catun Scrapmaster (30–40) | рядовое снаряжение |
| T2 | 3 | Edgewalkers (70–80) | офицеры, элита |
| T3 реликт | 5 | Cross (100) | только лидеры реликтовых отрядов, лимит 6 на мир |

| Фракция | Рядовые | Лидер | Причина в лоре |
|---|---|---|---|
| Holy Nation, United Cities, Shek Kingdom, Tech Hunters | T1 | T2 | организованные армии/охотники |
| Western Hive, Southern Hive, Greenskins | T0 | T1 | бедность снаряжения / Вааагх-хлам |
| Astartes survivors, Lost Black Sanctuary, Death Watch, Grey Knight (Mark-X) | T2 | T3 (первые 6 отрядов), далее T2 | реликтовая элита |
| Остатки Империума (свой поток) | T1 + «worn kit» T0 (T0-предметы WH) | T2 | экспедиция без снабжения |

Итог: 174 военных отряда переведены на клоны (162 клона: T0 33, T1 68, T2 56, T3 5). Реликтовые лидеры (T3) — 5 отрядов Mark-X: Ultramarines Patrol Squad 01, Ultramarines Astartes Patrol, Extreme Warrior Patrol Team 02 (Veterans/Terminator), Extreme Warrior Firepower Tactical Squad. Отбор — военные (`NPC class` 1/2) не-торговые SQUAD_TEMPLATE с `faction` из списка.

## Что где спавнится
| Отряд | Где (`homeless spawns`, вес) |
|---|---|
| Imperial Remnant Patrol, Death Korps Remnant Patrol | Ashlands, Venge, Deadlands, Stobe's Gamble, Sonorous Dark, The Black Desert — вес 1 (раньше Border Zone/Okran's Pride/Heng/Ashlands) |
| Greenskin Warband | Stenn Desert, Spider Plains, Bonefields — вес 2 |
Патрули ходят ванильным AI «Patrol map (short range)» вокруг места спавна: они заняты опасными зонами, а не дорогами Border Zone.

## Ожидаемый эффект
Армии фракций различимы по качеству снаряжения; реликтовый T3 встречается только у считанных отрядов Astartes; Империум виден лишь в смертельно опасных регионах; T0-обноски ходят у бедных и (через ECONOMY) у бандитов-трофейщиков. Применяется к **новым спавнам** — существующие NPC в сейве сохраняют прежнее снаряжение (нужна новая игра или время на обновление населения).

## Запросы интегратору
- В существующую FACTION Greenskins добавляется ссылка `squads` → Greenskin Warband (наследие glue). FACTION принадлежит BEHAVIOR: если BEHAVIOR начнёт менять Greenskins, это место надо перенести в его поток.

## Вне движка
Цели «идти к конкретным руинам» данными не задаются — ванильные AI-пакеты патруля работают вокруг точки спавна, поэтому регион выбирается только спавном.

## 2026-11-11: тиры перенесены в WARDROBE
Клоны-тиры, перенаправление военных отрядов, T0-предметы WH и уровни качества (armour grade / weapon level) теперь генерирует поток G WARDROBE (решение, владение по полям). Здесь остались фракция Imperial Expedition Remnants, патрули в опасных зонах, Greenskin Warband и спавны: 14 записей.
