# LEVERS — карта рычагов сборки (2026-11-11, v0)
Что уже можно крутить без нового кода: где лежит, текущее значение, на что влияет. Данные — слитый контекст ваниль → основа (713) → WH (10) → KMM_Glue (`tools\fast\levers.py` → `out\levers.json`).

## 1. Настройки игры (`Kenshi\settings.cfg`, `kenshi.cfg`, меню Options)
| Параметр | Сейчас | Влияет на |
|---|---|---|
| `Squad size multiplier` / `Global population multiplier` | 1 / 1 | размер отрядов и население мира — главный рычаг нагрузки CPU/RAM |
| `raidSizeMult` / `raidFrequencyMult` / `attacks` | 1 / 1 / 2 | размер и частота рейдов на базу игрока |
| `npc range` / `objects view range` / `view distance` | 3250 / 3000 / 5000 | дальность симуляции и отрисовки NPC/объектов (перф) |
| `shadow mode` / `shadow quality` / `water reflection` | 0 / 0 / 0 | выставлено по рекомендации автора коллекции |
| `generate distant towns` / `distant town range` | 0 / 6 | дальние силуэты городов |
| `texture resolution gimping` / `FXAA` / `HeatHaze` | 1 / 1 / 1 | текстуры понижены; FXAA и марево включены |
| `Video Mode` (`kenshi.cfg`) / `VSync` | 1680×1050 (в логе окно 1920×1080) / No | разрешение рендера |
| `Auto save time` | 10 мин | автосейвы |

## 2. RE_Kenshi (`Kenshi\RE_Kenshi.ini`; Options → Mods → RE_Kenshi Settings)
| Параметр | Сейчас | Влияет на |
|---|---|---|
| `HeightmapMode` | 0 = VANILLA (-1 AUTO, 1 COMPRESSED, 2 FAST_UNCOMPRESSED) | как требует автор коллекции; Heightmap Fix подменяет `fullmap.tif/.cif` |
| `MaxSquadSize` / `MaxSquads` / `MaxFactionSize` / `AttackSlots` (+`…Override`) | −1, Override=true | −1 = значения из GLOBAL CONSTANTS (их подняла основа, см. §4) |
| `CacheShaders`, `CachePhysXColliders`, `SkipUnusedMipReads`, `SkipSplashScreens` | true | скорость загрузки |
| `FixRNG` | true | исправленный ГСЧ |
| `EnableEmergencySaves` | true | аварийный сейв при краше |
| `UseCustomGameSpeeds` / `GameSpeeds` | true / 1, 5, 100, 200, 20 | скорости времени (100/200 пригодятся для прогона мира без игрока) |
| `IgnoreHash` | false | не трогать |

## 3. Dust (рендер-плагин, #24 в mods.cfg)
- **Где конфиг:** в папке мода в Workshop — `steamapps\workshop\content\233860\3703458265\`. Там `Dust.ini` (язык и версия), `effects\<Эффект>.ini` (по файлу на эффект, ключ `Enabled=`), готовые пресеты в `presets\…`, логи в `logs\`. В игре меню открывается по **F11**. ⚠ Steam может перезаписать эти файлы при обновлении мода — свои значения лучше дублировать у себя.
- **Сейчас включены все 16 эффектов:** Bloom, ChromaticAberration, Clarity, Deband, DOF, FilmGrain, Kuwahara, Letterbox, LUT, Outline, RTGI, Shadows, SMAA, SSAO, SSIL, Vignette.
- **Влияние на производительность, от тяжёлого к лёгкому:**

| Эффект | Ключевые параметры (сейчас) | Комментарий |
|---|---|---|
| RTGI | `ResolutionScale=50`, `RaysPerPixel=3`, `RaySteps=16`, `DenoiseSteps=4` | автор: «Very expensive — for high-end GPUs». На GTX 1650 — первый кандидат на `Enabled=0` или на облегчение (RaysPerPixel 1, RaySteps 8, ResolutionScale 33) |
| SSIL | `Directions=4`, `Steps=3` | непрямой свет в экранном пространстве, средне-тяжёлый; без RTGI частично его заменяет |
| Shadows | `Resolution=3`, `Range=6000`, `PCSS=1` | мягкие тени PCSS дорогие. В игре тени выключены (`shadow mode=0`) — надо проверить, работает ли эффект вообще |
| SSAO | `Samples=4`, `Steps=4` | умеренно |
| DOF | `BlurDownscale=2`, `AutoFocus=1` | умеренно; чистая эстетика |
| Bloom, SMAA, Clarity, LUT, Deband, Vignette | — | лёгкие |
| Kuwahara, Outline, Letterbox, FilmGrain, ChromaticAberration | — | лёгкие, но это стилизация «ради визуала» (DESIGN.md) — кандидаты на выключение |
| Апскейлер | DLSS: `NGX init failed` (у GTX 1650 нет тензорных ядер) | DLL FSR есть, режим выбирается в F11 |

- Пик памяти в тесте: 7.1 ГБ Working Set / 11 ГБ Private (TEST_V0.md). Вклад Dust (буферы RTGI/SSIL на полном разрешении) измерим A/B-запуском.

## 4. GLOBAL CONSTANTS (запись CONSTANTS) — что изменила основа
Изменено 164 ключей, из них 139 — настройки Nitoryu (`nitoryu …`, бой с двумя оружиями). Остальные:

| Константа | Ваниль | Сейчас | Мод |
|---|---|---|---|
| `attack chance factor` | 0.05000000074505806 | 0.07500000298023224 | Combat Tweaks.mod |
| `base block chance` | 70.0 | 85.0 | Combat Tweaks.mod |
| `bleeding clot rate` | 0.008500000461935997 | 0.005249999929219484 | Combat Tweaks.mod |
| `block chance increase per 10levels` | 12.0 | 5.0 | Combat Tweaks.mod |
| `blunt permanent organ damage` | 0.0 | 0.125 | Combat Tweaks.mod |
| `bodypart degeneration rate` | 1.5 | 2.0250000953674316 | Combat Tweaks.mod |
| `carry person weight` | 30.0 | 80.0 | Combat Tweaks.mod |
| `damage resistance max` | 0.6499999761581421 | 0.8500000238418579 | Combat Tweaks.mod |
| `damage resistance min` | -0.6499999761581421 | -0.8500000238418579 | Combat Tweaks.mod |
| `exposure max` | 1.2000000476837158 | 1.5499999523162842 | MoodShadows.mod |
| `exposure min` | 0.800000011920929 | 1.0 | MoodShadows.mod |
| `extra blood loss from bodyparts` | 1.0 | 1.5 | Combat Tweaks.mod |
| `immediate blood loss` | 0.20000000298023224 | 0.3499999940395355 | Combat Tweaks.mod |
| `medkit drain 1` | 20.0 | 36.0 | Combat Tweaks.mod |
| `min dismantle materials percentage` | 60.0 | 100.0 | MEGA - Item Integration Patch.mod |
| `minimum lockpick chance` | 5.0 | 0.0 | CrunkTweakCompilation.mod |
| `night darkness` | 0.3499999940395355 | 0.41999998688697815 | MoodShadows.mod |
| `skill diff xp 0x penalty` | 25.0 | 50.0 | Weaklings give XP.mod |
| `unarmed damage mult` | 0.800000011920929 | 0.550000011920929 | Great Anims Mod.mod |
| `XP rate medic 1` | 15.0 | 20.0 | Combat Tweaks.mod |
| `max faction size` | 30 | 256 | CrunkTweakCompilation.mod |
| `max num attack slots` | 1 | 5 | Combat Tweaks.mod |
| `max squad size` | 20 | 50 | CrunkTweakCompilation.mod |
| `max squads` | 10 | 20 | CrunkTweakCompilation.mod |
| `stumble damage max` | 80 | 120 | Combat Tweaks.mod |

## 5. Опции модов основы (конфиги в их папках Workshop)
| Мод | Конфиг |
|---|---|
| Vital-Sense.mod | `mod-config.defaults.json`, `mod-config.json` |
| StackSort.mod | `StackSort.cfg` |
| Organize-the-Crafting-Stations.mod | `mod-config.defaults.json`, `mod-config.json` |
| Hidden-Faction-Relations.mod | `mod-config.json` |
| Return to Main Menu.mod | `ReturnToMainMenu.ini` |
| KenshiExtensionPlugin.mod | `kep_core_settings.json`, `plugin\kep_settings.json` |
| AttachmentOptimization.mod | `dll\AttachmentOptimization\mod-config.json` |
| BetterPhysics.mod | `BetterPhysics_Config.txt` |
| FallDamage.mod | `FallDamage_Config.txt` |
| GatePushFix.mod | `GatePushFix.ini` |
| RE_KeepInterior.mod | `InteriorClearButton.ini` |
| Work for Cats - Get Hired at NPC Workbenches.mod | `SHA256.json`, `WorkForCats.ini`, `Source\WorkForCats.ini` |
| Rent Hous in Your Town Mod.mod | `manifest.json`, `RentTowerRuntime.ini` |
| GuardBreakBash.mod | `GuardBreakBash.ini` |
| Nitoryu.mod | `Nitoryu.ini` |
| Metabolic Traversal.mod | `config.json` |
| SquadAutonomy.mod | `SquadAutonomy.cfg` |
| FixShoppingWages.mod | `mod-config.json` |

Kaizo кладёт рядом справки `town overrides.txt`, `world state changes.txt`, `faction specific changes.txt` — это готовая документация его world states (см. LORE_MAP.md).

## 6. Рычаги в данных (через kmod → KMM_Glue)
| Рычаг | Где | Сейчас | На что влияет |
|---|---|---|---|
| Веса спавнов | BIOME_GROUP `homeless spawns` (val0 = вес), `homeless spawn amount` | 77 биомов, 2879 записей; больше всего — The Great Desert (113, сумма весов 798), Heng (98, сумма весов 746), The Hook (94, сумма весов 2367), Border Zone (84, сумма весов 192) | кто и как часто встречается в регионе; KMM_Glue добавил 11 записей весом 1–2 |
| World states | WORLD_EVENT_STATE + TOWN `override town` / `world state` | 478 состояний; 353 городов с override, 773 вариантов | смена владельца и состояния городов при смерти/плене лидеров (CORE.md §11) |
| Отношения фракций | FACTION `relations` (−100…100), `coexistence`, пороги бегства | 278 фракций, 1168 отношений (вражда ≤ −50: 453, дружба ≥ 50: 456), coexistence 1825 | кто на кого нападает; в KMM_Glue 41 слабая фракция ↔ 9 сильных |
| Деньги NPC | CHARACTER `money min/max`, `wages` | KMM_Glue поднял деньги ~1900 NPC по ролям (`rules\glue_rules.json`) | лут, покупательная способность |
| Торговцы | SQUAD_TEMPLATE `is trader`, `vendor money`, `vendors refresh time`, `vendors fill total amount`; VENDOR_LIST | 425 торговых отрядов, 446 списков; `vendor money`=0 (авто по списку) у 359; обновление раз в 24 ч у 330 | ассортимент, деньги торговцев, оборот экономики |
| Цены | ITEMS_CULTURE (множители цен), `food crop` + глобальный множитель цен еды, `value` предметов | — | региональные цены (CORE.md §4) |
| Снаряжение по рангам | CHARACTER `clothing`/`weapons`/`weapon level`, `armour grade` | T0-варианты из KMM_Glue | уровни снаряжения (CORE.md §7) |
| Лимиты | CONSTANTS `max squad size` 50, `max squads` 20, `max faction size` 256 | см. §4 | потолки симуляции; вместе с Squad size multiplier задают нагрузку |
