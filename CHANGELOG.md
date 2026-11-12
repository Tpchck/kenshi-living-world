# Changelog

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
