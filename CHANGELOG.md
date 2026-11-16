# Changelog

## 2026-11-16
- Predators module retired after a crash in the engine's smell zones; predator packs trailing herds are off too. Predators are vanilla nests and patrols again.
- Ore: veins deplete and regrow, factions short on metal look for new sites and take other factions' mines; tax collectors come for long mining on someone else's land.
- Firearms by region: guns show up where the lore puts them, prices follow.
- Inventory icons: oversized icons downscaled, icons moved by mod compilations relinked.
- Runtime modules publish themselves into the global table, so the self-check sees all of them.
- Build menu: a vanilla building keeps its own category when duplicates fold (plain campfire back under Camping).
- Fates: a hero dies only when the hero dies, not when the engine hands squad leadership to someone else.

## 2026-11-15
- Core-first course: every mechanic starts from an engine reference in `docs/core/` (people, AI squads, world, economy, data, call ledger).
- Deeds bus: kills, captures and rescues from the engine's relation callback feed rivals, town memory and bounties.
- Nemesis: a rival is born from a beating you survive; debts for first aid and freeing prisoners.
- Self-check module (`KMM_Probe`) runs read-only probes of engine calls at the start of every session.
- Survival start: naked in the desert, no money, skills at 1, hungry.
- Raids on the player's base become vanilla faction campaigns.

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
