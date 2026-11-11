"""out/levers.json → docs/LEVERS.md"""
import json

r = json.load(open(r"C:\KenshiModMap\tools\fast\out\levers.json", encoding="utf-8"))
C = r["constants_changed"]
crow = "\n".join(f"| `{k}` | {v['vanilla']} | {v['final']} | {', '.join(v['mods'])} |" for k, v in C.items() if not k.startswith("nitoryu"))
nit = sum(1 for k in C if k.startswith("nitoryu"))
dust = r["dust"]
cfg = r["mod_configs"]
useful = ["Vital-Sense.mod", "StackSort.mod", "Organize-the-Crafting-Stations.mod", "Hidden-Faction-Relations.mod", "Return to Main Menu.mod",
          "KenshiExtensionPlugin.mod", "AttachmentOptimization.mod", "BetterPhysics.mod", "FallDamage.mod", "GatePushFix.mod", "RE_KeepInterior.mod",
          "Work for Cats - Get Hired at NPC Workbenches.mod", "Rent Hous in Your Town Mod.mod", "GuardBreakBash.mod", "Nitoryu.mod",
          "Metabolic Traversal.mod", "SquadAutonomy.mod", "FixShoppingWages.mod"]
mrow = "\n".join(f"| {m} | {', '.join('`' + x + '`' for x in cfg[m][:3])} |" for m in useful if m in cfg)
sp, ws, rel, tr = r["spawns"], r["world_states"], r["relations"], r["traders"]
dust_on = ", ".join(k for k, v in dust.items() if v == "1")
top_sp = ", ".join(f"{n} ({c}, сумма весов {w})" for n, c, w, a in sp["top"][:4])

md = f"""# LEVERS — карта рычагов сборки (2026-11-11, v0)
Что уже можно крутить без нового кода: где лежит, текущее значение, на что влияет. Данные — слитый контекст ваниль → основа (713) → WH (10) → KMM_Glue (`tools\\fast\\levers.py` → `out\\levers.json`).

## 1. Настройки игры (`Kenshi\\settings.cfg`, `kenshi.cfg`, меню Options)
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

## 2. RE_Kenshi (`Kenshi\\RE_Kenshi.ini`; Options → Mods → RE_Kenshi Settings)
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
- **Где конфиг:** в папке мода в Workshop — `steamapps\\workshop\\content\\233860\\3703458265\\`. Там `Dust.ini` (язык и версия), `effects\\<Эффект>.ini` (по файлу на эффект, ключ `Enabled=`), готовые пресеты в `presets\\…`, логи в `logs\\`. В игре меню открывается по **F11**. ⚠ Steam может перезаписать эти файлы при обновлении мода — свои значения лучше дублировать у себя.
- **Сейчас включены все {len(dust)} эффектов:** {dust_on}.
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
Изменено {len(C)} ключей, из них {nit} — настройки Nitoryu (`nitoryu …`, бой с двумя оружиями). Остальные:

| Константа | Ваниль | Сейчас | Мод |
|---|---|---|---|
{crow}

## 5. Опции модов основы (конфиги в их папках Workshop)
| Мод | Конфиг |
|---|---|
{mrow}

Kaizo кладёт рядом справки `town overrides.txt`, `world state changes.txt`, `faction specific changes.txt` — это готовая документация его world states (см. LORE_MAP.md).

## 6. Рычаги в данных (через kmod → KMM_Glue)
| Рычаг | Где | Сейчас | На что влияет |
|---|---|---|---|
| Веса спавнов | BIOME_GROUP `homeless spawns` (val0 = вес), `homeless spawn amount` | {sp['biomes']} биомов, {sp['entries']} записей; больше всего — {top_sp} | кто и как часто встречается в регионе; KMM_Glue добавил 11 записей весом 1–2 |
| World states | WORLD_EVENT_STATE + TOWN `override town` / `world state` | {ws['states']} состояний; {ws['towns_with_overrides']} городов с override, {ws['override_variants']} вариантов | смена владельца и состояния городов при смерти/плене лидеров (CORE.md §11) |
| Отношения фракций | FACTION `relations` (−100…100), `coexistence`, пороги бегства | {rel['factions']} фракций, {rel['relation_entries']} отношений (вражда ≤ −50: {rel['hostile(<=-50)']}, дружба ≥ 50: {rel['friendly(>=50)']}), coexistence {rel['coexistence_entries']} | кто на кого нападает; в KMM_Glue 41 слабая фракция ↔ 9 сильных |
| Деньги NPC | CHARACTER `money min/max`, `wages` | KMM_Glue поднял деньги ~1900 NPC по ролям (`rules\\glue_rules.json`) | лут, покупательная способность |
| Торговцы | SQUAD_TEMPLATE `is trader`, `vendor money`, `vendors refresh time`, `vendors fill total amount`; VENDOR_LIST | {tr['trader_squads']} торговых отрядов, {tr['vendor_lists']} списков; `vendor money`=0 (авто по списку) у {tr['vendor money'][0][1]}; обновление раз в 24 ч у {tr['refresh time'][0][1]} | ассортимент, деньги торговцев, оборот экономики |
| Цены | ITEMS_CULTURE (множители цен), `food crop` + глобальный множитель цен еды, `value` предметов | — | региональные цены (CORE.md §4) |
| Снаряжение по рангам | CHARACTER `clothing`/`weapons`/`weapon level`, `armour grade` | T0-варианты из KMM_Glue | уровни снаряжения (CORE.md §7) |
| Лимиты | CONSTANTS `max squad size` 50, `max squads` 20, `max faction size` 256 | см. §4 | потолки симуляции; вместе с Squad size multiplier задают нагрузку |
"""
open(r"C:\KenshiModMap\docs\LEVERS.md", "w", encoding="utf-8").write(md)
print("ok", len(md), [hex(ord(c)) for c in md if ord(c) < 32 and c != "\n"][:3])
