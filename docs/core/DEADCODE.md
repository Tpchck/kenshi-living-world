# DEADCODE — аудит мёртвого и дублирующего кода (U5, 2026-11-15)

Только аудит, код не менялся. Источники: `build/KMM_*/scripts/**/*.lua`, `tools/streams/*.py`, `rules/*.json`, `tools/*.py`; тесты `build/*/_dev`.
Метод: скрипт-поиск определений функций и ссылок (с учётом тестов `_dev` и `tools/**`), сверка ключей `rules/conductor.json.params` с Lua,
grep флагов `= false`, «fallback/фолбэк/прежн/legacy», читателей rules/*.json, ссылок на tools/*.py из кода/bat/verify_all.
Объёмы примерные (±20%). Файлы пакета 5 в работе (Traces/U1, Conductor_Sync+Econ base_try/U2, kmm_town/U3, kmm_tempo/U4) —
находки в них удалять только после слияния соответствующей задачи.

## Не мёртвое (проверено, удалять нельзя)
- Модель дирижёра `S.rel` / `f.strength` (Conductor_Base:253-263, Econ) — это планировщик дальнего мира; RELSYNC/CORESYNC
  (Conductor_Sync:383-500, 559-748) сливают её с ядром, а не заменяют. Не дубль.
- Свой бросок кампаний/осад (Conductor_Sync `CA.try`:298+, KMM_Siege:407-416 «fallback roll») — основной путь для дальнего мира:
  кампании движка запускаются только рядом с игроком (`CA.near_player`, Siege:206, Sync `CA.pick_town`). Не фолбэк в чистом виде.
- Засады гнёзд KMM_Predators и стада/охотники KMM_Herds — свой спавн по необходимости (`_spawnASquad`/маршрута миграции в Lua нет, Predators:11, Herds:12).
- Свои награды KMM_Outlaws (`M.add_bounty`, :251) кормят хронику/слухи; родная награда добавочная.
- Экспорты «для офлайн-теста» в API (KMM_Conductor.lua:174-302, Traces:1940-1944, Nemesis:1657-1661, Gov:341-343, Herds:336-337,
  Siege:468, Diplo:792-796, Stock_model:614/716) — вызываются из `_dev/test_*.py`. Оставить.
- Уже исправлено (ревью/пакет 1): M5 `pl._persistentSquad` убран; B3 `unconcious` убран (Self:338); B2 Lua-`rememberCharacter` не зовётся (Nemesis:1535-1556).

## A. Можно удалить сразу (низкий риск)
| # | где (файл:строки) | почему мёртвое/дубль (доказательство) | ~строк | риск |
|---|---|---|---|---|
| A1 | build/KMM_Diplo/scripts/init/kmm_diplo.lua:412-460 (ветки после `if C.emit/C.add_rel/C.add_trust_one/C.player_sign/C.player_break then return …`) + :764 текст лога | «без патча дирижёра» — прямая запись `s.rel/s.treaties/dirty_rel` мимо дирижёра (своя модель отношений рядом с `KC.set_rel`→RELSYNC). Патч давно в KMM_Conductor.lua:85 (player_sign), :163-165 (add_rel/add_trust_one/emit), player_break есть → ветки не выполняются. Тест: убрать часть «без патча» в KMM_Diplo/_dev/test_diplo.py (до :220) | 35 | низкий |
| A2 | KMM_Conductor_Sync.lua:845-879 `KC.try_gear`, :926-933 `KC.gear_possible`, вызовы :963, :981, `KC.gear_done`:837 | `materialize.gear_enabled=false` (tools/conductor/gen_conductor.py:74), пути включения нет кроме правки JSON; тиры экипировки уже дают Wardrobe-поток и Traces (TIERS, Traces:10). Тест-блок test_perf2.py:376. `KC.wealth_shift` и `KC.TIERS` НЕ трогать (World:211, Runtime:276) | 50 | низкий |
| A3 | KMM_Conductor_Sync.lua:16-47 `KC.ore_campaign_try`, Base:376, Econ:1393; `params.links2.ore_campaign` (conductor.json:424-432, gen_conductor) | `enabled=false` с создания (LINKS2), не включался; тот же `triggerCampaign` уже идёт общим путём `CA.try` (enabled=true) и KMM_Siege. Тест test_links2.py:350-371 | 40 | низкий |
| A4 | KMM_Traces.lua:1894-1904 `g_ambient` + его вызов; ключ `roads.ambient` (Conductor.lua:60, gen_conductor) | `ambient=false` по умолчанию «не создаёт групп без повода» (_doc conductor.json:436), включения нет; противоречит «геймплей из повода». После U1 | 13 | низкий |
| A5 | tools/conductor/gen_conductor.py:45,47,62,71,72,95,98 → ключи params | Нет читателя ни в Lua, ни в тестах: `attacker_weight.town_strength`, `.min_strength`, `economy.income_per_town` (доход считается `income_city/holding`, Base:568), `relic.mobilize_triggers`, `materialize.apply_to_player_characters`, `materialize.relation_write_min_delta` (заменён `relsync.min_delta`), `player_base.join_raid_min_rel`, `traces.column_size` | 8 | низкий |
| A6 | kmm_elite.lua:278-279 (`P.legacy_spawn`), kmm_elite_data.lua:8, rules/streams/elite.json:152 | флаг `legacy_spawn=false`, нигде не включается; оставить только `legacy_if_no_native` (см. B5) | 3 | низкий |
| A7 | KMM_Rumors.lua:221-226 `local function loadTold` | 0 вызовов (grep); `R.told` восстанавливается из сейва (:771), файл told — только журнал (:14) | 6 | низкий |
| A8 | KMM_Conductor.lua:181 `phase_flush`; KMM_RelicRace.lua:297 `M._reset`; KMM_Traces.lua:1943 `_loot_scan` | экспорты без вызовов ни в коде, ни в тестах | 3 | низкий |
| A9 | KMM_Fates.lua:238-242 (`M.alive` ветка без `C.alive`), :303-307 (`M.bounty_add` фолбэк на `_M`), :406 (фолбэк `NM._N.remember`) | `C.alive` (Conductor.lua:169), `KMM_Outlaws.add_bounty` (:998), `KMM_Nemesis.remember` всегда экспортируются в той же сборке | 10 | низкий |
| A10 | tools/build/kmm_build.py:33 `("world", "KMM_World")` | нет tools/streams/world.py и rules/streams/world.json — запись молча пропускается (:154) | 1 | низкий |
| A11 | build/KMM_Conductor/_dev/gen_rules.py | v0-генератор conductor.json (11.11), заменён tools/conductor/gen_conductor.py; запуск ПЕРЕЗАПИШЕТ rules/conductor.json старой версией | 97 | низкий (снижает риск) |
| A12 | _dev-бэкапы без тестов: KMM_Conductor/_dev/KMM_Conductor_v0_backup.lua, KMM_Gov_pre_perf.lua.txt; KMM_Rumors/_dev/KMM_Rumors_pre_deed.lua.txt, KMM_Rumors_pre_perf.lua.txt; KMM_Ore/_dev/kmm_ore_v1_backup.lua.txt | ни один test_*.py их не читает (эталоны perf — только Conductor_pre_perf2/Self/Traces/Stock/Town/Elite/Gov_pre_t2). `*_pre_perf` защищён KEEP в cleanup_dev.py:8 → удалять вручную/в архив | ~2600 (текст) | низкий |
| A13 | tools/smoke.py:105-190 `smoke()`, `smoke_world()` | запуск игры отозван владельцем (шапка файла, память); остаётся `report()`/--report | 90 | низкий |
| A14 | tools/cults2.py, tools/cults3.py, tools/newmods_scan.py | разовые скрипты (exec cults.py / одноразовый скан), 0 ссылок из кода | 52 | низкий |
| A15 | tools/streams/_lore_check.py, _tech_check.py, _town_check.py | 0 ссылок из кода, не в verify_all/kmm_build; разовые проверки 12-13.11 (`_diplo_check` используется, `_diplo_dlg_check` свежий 15.11 — оставить) | 244 | низкий |
| A16 | rules/streams/palette_proposal.json (27 КБ), rules/vassals_proposal.json (15 КБ) | вывод аудитов (palette_audit.py/vassals_audit.py), сборкой не читаются; перенести в data/ или удалить | — | низкий |

Итого A: Lua ≈170 строк, Python ≈490 строк, + ≈2600 строк бэкапов в _dev, 2 JSON-предложения.

### A-доп. Архивировать (средний риск: разовые аудиты, выводы уже в docs)
tools/atlas_cleanup_inventory.py (535), engine_lookup.py (449, индекс data/engine_index.json вторичен к tools/ref по PROTOCOL),
junk_audit.py (354), slots_audit.py (168), gear_audit.py (99), lore_audit.py (84), engine_api_usage.py (66, дублирует tools/api_audit.py),
ward_share_eval.py (63), memwatch.py (39, нужен только при игре) — 0 ссылок из кода/verify_all. ≈1860 строк → zip через cleanup_dev.

## B. Удалить после игровой проверки (фолбэки к непроверенному ядру)
| # | где | фолбэк к чему | маркер-подтверждение (session_report) | ~строк |
|---|---|---|---|---|
| B1 | KMM_Herds.lua:226-260 (ветка «smell fallback spawn», :287) | запах ядра R4 (`Predators.smell`) | herds.log `smell took:` стабильно, `smell_fb`≈0 | 15 |
| B2 | KMM_Conductor_Sync.lua:395-400 `rs_fail` + абсолютная запись в `GL.rs_write` | RELSYNC запись дельтой (Q5) | debug.log `RELSYNC steps=` с `writes delta>0`, `mismatch=0` | 15 |
| B3 | KMM_Fates.lua:243-258 (`M.prel` фолбэк `C.rel`, правило `h.rep < 20`) | `FactionRelations:getFactionRelation` | fates.log `justice:` с источником core | 8 |
| B4 | KMM_Traces.lua:981-1005 (запись `priceMultWhenITrade` при `TGM.wok=false`) | `Town.tradeGoodsMults` (R1) | debug.log `TGM probe OK`, `TGM write OK` | 20 |
| B5 | kmm_elite.lua:54-79, 103-151, 188-222 (`try_spawn`, `spawn`, `null_hand`, `pick_point`, `elite_alive`) + `legacy_if_no_native` | ванильный UNIQUE_SQUAD через замок WES (`KMM_Native.ws_set`) | debug.log `elite … native gate open` | 95 |
| B6 | kmm_diplo.lua:236-245, 554-616, 704+ (жетоны посла, `DIPLO_COND fallback`) | перехват `_checkCondition` (S4) | debug.log `DIPLO_COND hook live`, нет `DIPLO_COND fallback` | ~60 |
| B7 | KMM_Conductor_Sync.lua:216-230 `CA.base_fallback` (+Econ:1440) | рейд на базу кампанией (U2) — частично: «player far» остаётся | log `base campaign`/фазы; только после слияния U2 | 15 |
| B8 | «прежний обход» без снимка Gov: Conductor_Sync:936-990, KMM_Rumors.lua:408+, kmm_stock.lua:429-450, kmm_town.lua:275-291 `scan_full`, kmm_elite.lua:105+ | `KMM_Gov.snapshot` (PERF2/T2) | `[KMM_Gov] summary` с hits, без `snapshot fail`; оставить 1 общий предохранитель в Gov | ~80 |
| B9 | KMM_Self.lua:372-390, kmm_stock.lua:737-750 (`stamp_mode` без `getTimeStamp`) | метка кадра движка; ветка нужна только офлайн-заглушкам | `[KMM_Gov] summary` в игре → перенести поведение в заглушки тестов | 20 |

Итого B ≈330 строк Lua.

## Порядок удаления
1. Сразу, без игры (одним пакетом, затем `kmm_build.py` = verify_all): A11 → A10 → A5 → A7/A8/A9 → A1 (+test_diplo) → A2 (+test_perf2) →
   A3 (+test_links2) → A6 → A13/A14/A15/A16 → A12 и A-доп. в zip (`tools/cleanup_dev.py`, KEEP не трогать для perf-эталонов).
2. После слияния U1: A4 (Traces). После U2/U3/U4 — повторный короткий аудит Sync/Econ/kmm_town/kmm_tempo (не проверялись: в работе).
3. После первой игровой сессии по маркерам: B2, B3, B4 (дешёвые) → B1 → B5, B6 (крупные) → B8, B9 → B7.
   Фолбэк удалять только при маркере успеха минимум в одной сессии и отсутствии маркера провала.
