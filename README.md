# Kenshi: Living World

A single-player overhaul for Kenshi 1.0.65 (Steam) that turns a large mod collection into one coherent game where the world keeps moving without the player.

Factions grow, starve, go to war, lose leaders and split. Towns trade, run out of food and change hands. Ore veins run dry, so factions go looking for new ones and take other people's mines. Bounty hunters, rivals, refugees and caravans show up near you because something happened in the world, not because a timer fired. The player is a speck in that sea, and progression comes from running into all of it.

## Idea

- **Deepen vanilla, don't replace it.** Everything goes through the engine's own systems: campaigns, squad AI packages, bounties, relations, hunger, town ownership, trader stock. A new variable appears only when the engine gives no lever.
- **One game, not a pile of mods.** About 660 Workshop mods go through an offline pipeline that dedups items and buildings, fixes broken data and assets, dresses NPCs by culture and region, and writes a generated load order. Source mods are never edited.
- **Information travels.** The world reaches the player through rumors, traces and what NPCs know about their own role. Nothing is announced globally.
- **Save-safe.** One long campaign. State lives next to the save and only grows in compatible ways.

## How it works

```
Workshop mods ──► tools/ (Python) ──► build/KMM_* ──► Kenshi/mods + generated mods.cfg
                  read .mod data,     data mods +
                  audit, generate     Lua runtime
```

- **Offline layer** (`tools/`, `rules/`): reads FCS `.mod` data with an in-house reader/writer (`tools/kmod.py`), runs audits and generates the `KMM_*` data mods from rules in `rules/streams/*.json`.
- **Runtime layer** (`build/*/scripts`): Lua modules on KenshiLua. `KMM_Conductor` is the world model (factions, towns, economy, wars, story acts). Satellite modules materialize it near the player.
- **Native layer** (`tools/cpp/kmm_native`): an RE_Kenshi plugin on KenshiLib for the hooks Lua can't reach (context menus, squad orders, tooltips, world states).

## Modules

| Module | What it does |
|---|---|
| Conductor | World model: faction state, goals, sieges, captures, succession crises, ore economy, event bus |
| Traces | Turns world events into squads near the player: refugees, patrols, raiders, caravans |
| Rumors | Delayed news by distance; NPCs talk about what they could know |
| Stock / Town | Town warehouses, production, famine, trader restock and prices |
| Ore | Finite veins with regrowth; player and NPC mining from one pool |
| Fates / Nemesis / Outlaws | Named heroes, personal rivals, wanted gangs with real bounties |
| Herds / Tempo | Animal migrations; hunger and fatigue tied to vanilla timers |
| Diplo | Treaties, tribute and envoys through dialogue |
| Wardrobe / Relics / Tech | NPC gear by culture, region and tier; relic loot and crafting tree |
| Fix / Build / Atlas / Cleanup | Data fixes, build menu and research tree, town factions, map cleanup |

## Build

Requirements: Kenshi 1.0.65 (Steam), RE_Kenshi 0.3.5, KenshiLua, Python 3.12+.

```
python -I -X utf8 tools/build/kmm_build.py --write all            # generate build/
python -I -X utf8 tools/build/kmm_build.py --write all --install  # + verify_all, install, mods.cfg
python -I -X utf8 tools/session_report.py                         # read logs and the last save after playing
```

The install step runs `tools/verify_all.py` (Lua lint, engine API audit, ~110 offline tests on engine stubs) and refuses to install on failure. The game must be closed.

## Repository

- `tools/` — pipeline, audits, offline tests, save replay
- `rules/` — every tunable: load order, streams, conductor parameters
- `build/` — module sources (Lua, configs, tests in `_dev/`); `.mod` files are generated
- `docs/` — design notes and engine reference (in Russian); start with `docs/STATUS.md` and `docs/core/`

Third-party code (KenshiLib, RE_Kenshi, Boost) and generated data are not included.
