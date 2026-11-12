# DEDUP-ACT — журнал (2026-11-12)

Проверка перед отключением: офлайн по данным .mod (tools\kmod.py, скан docs\DEDUP.md): новые записи, перекрытие пар (запись, поле) более поздними модами (последний писатель не отключаемый мод), ссылки в dependencies/references, ресурсы в папке мода.

## Отключено (rules\excluded_mods.json, бэкап backupules\excluded_mods.json.20261112_pre_dedup)
- Better Storage System - Upgradeable Tiers: 0 новых записей, 344 из 344 пар перекрыты MEGA - Item Integration Patch - Upgradeable Tiers, ресурсов нет, ссылок нет.
- Sharper Blunts: 0 новых, 16 из 16 пар перекрыты Slightly Adjusted Blunt Weapons (грузится позже), на путь его мешей никто не ссылается.
- oni_revision: 0 новых, 17 из 17 пар перекрыты поздними модами, ресурсов и ссылок нет.
- 48 пустых разделителей автора (имена на «[»): 0 записей, только .mod/.img/.info, зависимостей и ссылок нет.

## Оставлено
- SCAR's pathfinding fix: единственная уникальная правка Nameless.road preference 0.1 (в базе 0.4), остальные 53 перекрыты. Не полный дубль.
- Yet More Idle Animations (3 версии): наборы новых ANIMATION не пересекаются по именам (146 / 25 / 2), это дополняющие друг друга паки, не версии.
- Xbow_Female_Fix и RadiantFacesHN: общие только 5 правок; у RadiantFacesHN 254 новых записи и 390 текстур, у Xbow 2 новые записи и скелеты. Не дубли.
- Slightly Adjusted Blunt Weapons: победитель пары.
- 12 из 13 «почти перекрытых» (Gambling Dice, HungerWars, Faction Caravans, Town of Shem, Kit's Weapon Pack, Believer + Book Craft, BBgoats worldadditions, Wandering Swordmen, Sugoi Nagai Katana, Wooden_staff, Modified Samurai Armor, Lolulile integration): несут новые записи (7–189), на них ссылаются KMM_*/MEGA-патчи, часть с мешами/текстурами.
- Sacred Trash player only: 0 записей, но не разделитель (есть зависимости) — не тронут.

## Проверка генератора (mods_cfg.py check, без записи)
Генератор: 786 -> 735 строк (-51). Порядок остальных не изменён, ошибок зависимостей/исключённых/ресурсов нет. Единственная ошибка режима check: «в живом mods.cfg лишние» — ожидаемо до установки интегратором.

## Прочее
- tools\dedup_report.py (≈7 с) подключён в docs\CHECKLIST.md необязательной строкой. Отчёт также нашёл кандидата UPK No Swamp Distant Towns (0 новых, всё перекрыто) — не проверялся глубже, не отключён.
- Скрипты проверки: temp\ dedup\q2..q6.py, apply.py, cmp.py.
