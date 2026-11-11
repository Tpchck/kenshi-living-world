# CULTS — культовые моды (2026-11-11), данные Steam Web API, tools\cults.py / cults2.py
Топ-3 актуальных коллекции (по избранному, обновлены за год): MEGA Kaizo/UWE+ 2822248814 (7283, 680 модов), Lore Friendly RPE 2983145281 (5634, 542), Vanilla Remastered 3276600292 (5076, 165). Наша основа MEGA Kaizo/Vanilla+ — 2272.
Смещение: UWE+ и наша основа — один автор (Anrhaa), его патчи пересекаются; Vanilla Remastered — независимая.
Итог: культовых (≥2 из 3) — 359, во всех трёх — 74; уже в нашей сборке — 329 (92%).
Не в сборке — 30, из них ~20 экосистема UWE (тотал-оверхол, отвергнут при выборе основы).
Кандидаты на рассмотрение (аудит до включения):
- Throes of Obedience 1762149693 — механики рабства (ванильный сеттинг)
- Complex AI - Anti-Assassinate 3467763726 — AI
- Settled Nomads Expanded V2 3550526654 — оседлые кочевники, живость мира
- KPM: Performance Particles 2800302311 — перф; проверить пересечение с Particles and foliage fix
- Визуал моделей (под направление WARDROBE, бюджет памяти): Weapons look metallic 1845960491, Pretty Stuff 3400528309, Dropped in Style 3263005742
- Отброшены: Blue Nebulosity (небо), все UWE-*, UPK No Stone Camp patch (нужен только с GenMod/UWE)

## Ознакомление: ещё 5 сборок (без культовых и без модов нашей сборки), tools\cults3.py
- Authentic Kenshi 3550504382 (2025-09, 177): ставка на Reactive World + экономика. Интересно: Racial Diversity 766462696 (смешанные расы у бандитов), NPCs With Robotic Limbs 1778901004, Trade Routes Intensified 1658170081.
- UWE/Kaizo/LF Merged 3211907381 (2025-05, 723): UWE-ветка. Интересно: Improve relationships by Healing 1950231883, NPC enjoys more shopping 1616010664.
- Buc Nasty's 1898460183 (2025-06, 368): QoL-тяжёлая, Living World. Интересно: Slopeless 1740462542 (стройка на склонах).
- Crafting Redux Series 3586168016 (2025-10, 11): модульный ребаланс крафта брони/оружия/роботехники с тирами через исследования — кандидат для пути «реликты воспроизводимы через технологии».
- Ultimate Kenshi Experience 2967435666 (2023, устарела): классика — Shops have more money 973017237, shops have more items + 937096807.
Наблюдение: Reactive World и Living World в нашей основе нет (там Kaizo) — с Kaizo они конфликтуют по world states, не брать.

## Аудит 7 кандидатов (2026-11-11, tools\fast\audit_mods.py → tools\fast\out\audit_wave1_cults.json)
Все 7 приняты и стоят в mods.cfg после WH-слоя (их зависимости — только ванильные файлы) и выше KMM_*. Плагинов RE_Kenshi нет. Битых ссылок, отсутствующих зависимостей и коллизий sid нет.
| Мод | МБ | Новых / правок | Перетирает значений основы | Совпадающих файлов | Битых ссылок | Решение | Суть |
|---|---|---|---|---|---|---|---|
| [Throes of Obedience](https://steamcommunity.com/sharedfiles/filedetails/?id=1762149693) | 4.0 | 0 / 23 | 0 | 0 | 0 | **принят** | механики рабства: 23 правки ванильных записей, перезаписей основы нет |
| [CAI Anti-Assassinate](https://steamcommunity.com/sharedfiles/filedetails/?id=3467763726) | 0.2 | 42 / 17 | 0 | 0 | 0 | **принят** | AI против убийств во сне: 42 новые записи (AI), 17 правок, чисто |
| [Settled Nomads Expanded V2](https://steamcommunity.com/sharedfiles/filedetails/?id=3550526654) | 0.6 | 15 / 5 | 0 | 15 | 0 | **принят** | новые поселения кочевников: 15 новых записей + leveldata в своей папке (совпадение имён с UPK/CATO — это поуровневые файлы, игра сливает их по модам) |
| [KPM_Performance_Particles](https://steamcommunity.com/sharedfiles/filedetails/?id=2800302311) | 9.0 | 0 / 0 | 0 | 0 | 0 | **принят** | KPM: 278 файлов particles, записей нет. «Particles and foliage fix» в сборке нет (не подписан) — оставляем KPM. С KPM_LEM (Lowpoly Environment Models, база) общих файлов 0 |
| [WeaponRetexMetalness](https://steamcommunity.com/sharedfiles/filedetails/?id=1845960491) | 31.6 | 0 / 15 | 1 | 0 | 0 | **принят** | ретекстур металла оружия: 15 правок MATERIAL_SPECS_WEAPON, перетирает 1 карту нормалей Side Quest |
| [Pretty Stuff](https://steamcommunity.com/sharedfiles/filedetails/?id=3400528309) | 46.8 | 9 / 71 | 2 | 1 | 0 | **принят** | модели предметов (ITEM), 9 новых + 71 правка; перетирает 2 поля Fog Prince Head (Fog Hunt) — визуальная замена |
| [Dropped in Style](https://steamcommunity.com/sharedfiles/filedetails/?id=3263005742) | 61.3 | 17 / 182 | 14 | 0 | 0 | **принят** | модели выброшенных вещей: 17 новых + 182 правки ground mesh; перетирает 10 ground mesh UPK и 4 Hivers — это и есть назначение мода |

- Бюджет памяти: три визуальных мода — 140 МБ файлов (вместе с волной 1 WARDROBE ≈1.3 ГБ при бюджете +2 ГБ), фактический прирост проверим замером на старте.
- С гардеробом не конфликтуют: меняют модели/текстуры/ground mesh предметов, а KMM_Wardrobe — только списки одежды персонажей и торговцев (разные поля).
