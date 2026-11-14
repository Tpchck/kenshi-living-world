# Changelog

## 2026-11-14
- Map cleanup mod (`KMM_Cleanup`): dead and duplicate locations, lone shops become street traders.
- Herds on real regions from the game's biome map.
- Outlaws: rackets, raids on wanted gangs by law enforcement, bounty balance over two simulated years.
- Town trade price multipliers read from the engine.
- Test isolation: stubs no longer write into the real state folder; flaky tests rerun once.

## 2026-11-13
- `api_audit`: engine calls checked against signatures; `session_report` and `save_replay` for offline checks on real saves.
- Performance governor (`KMM_Gov`) with a shared character snapshot and per-module budgets.
- New modules: Tempo (fatigue, NPC hunger), Siege, RelicRace, Fates, Herds, Veterans, Elite, Atlas.
- Story acts on world state ("Twilight of Relics"), strongholds, faction goals, town life.
- Wardrobe lore rules: savages without helmets, ninja and samurai sets, pagan items only for tribes.
- Native plugin 2.2: compact tooltips.

## 2026-11-12
- Build pipeline: `kmm_build.py`, generated `mods.cfg` with dependency and order checks.
- Conductor v1–v4: faction state, event bus, utility actions, finite ore veins, succession crises, base raids, chaos cults.
- Stock: abstract town warehouses with eight goods categories, restocking traders.
- Ore v2, relic tech tree on Crafting Redux, native plugin toolchain (KenshiLib, VS2010 toolset).
- World state now persists in saves.

## 2026-11-11
- `.mod` reader/writer (`tools/kmod.py`) validated against `fcs.def`; first generated mod loads in FCS and in game.
- Mod collection as the base, catalog and audits of items, races and factions.
- First streams: conductor and rumors prototypes, glue rules.
