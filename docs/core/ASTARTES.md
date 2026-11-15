# ASTARTES — ордена космодесанта в живом мире (A1, 2026-11-15)
Источник: 40k Mark-X `TEXT TEXTURE.mod` (WS 3475091710) + EN-перевод 3596387397; чтение `tools/kmod.py`. Реализация: `tools/streams/relics.py:_astartes_chapters` + `rules/streams/relics.json` «astartes_chapters»; разговоры `tools/streams/diplo.py:astartes_build` + `rules/streams/diplo.json` «astartes_orders»; дирижёр `tools/conductor/gen_conductor.py` (CHAPTERS из relics.json); тест `build/KMM_Relics/_dev/test_a1_astartes.py`. **Нужна новая игра.**

## Реестр (до A1)
**Фракции мода:** Astartes survivors (1034, лоялисты-Ультрамарины, город Astartes outpost), The Lost Black Sanctuary (227, Чёрные Храмовники), Death Watch (463), Grey Knight (759), Lost Warrior (95, стартовая), Astartes Support Level 01–04 (скрытые, для кампаний поддержки игрока); хаос: Lost Chaos Space Marines (143, Iron Warriors «Collector»), World Devourer War Gang (World Eaters), Midnight Lord (Night Lords), Hatred of intelligence, Man-eating shark (еретики-терминаторы). Расы: Astartes (The Lost) 139, Astartes (Elite) 401, Astartes (Special Gene Seed).
**Откуда лагеря ✓код:** TOWN мода с отрядами в bar squads/residents, стоят без дела и без понятных диалогов (китайские пакеты): Astartes outpost 1033 (Flats Lagoon; 7 bar squads + Ultramarines Gatekeeper; сюда же KMM_Cleanup свозил Branding Camp 1724 и Silent Camp 947), Black Sanctuary Camp 424 (Gut), Death Watch landing point 462 (Howler Maze), Devil's Hideout 758 (Leviathan Coast, Grey Knight), Silent Camp 947 (Sinkuun, Grey Knight), Branding Camp 1724 (Spider Plains, Black Shield). Хаос: The Collector's Nest 794 (Okran's Gulf), Blood Skull Altar/Skull Sentinel (Berserker Country), Human Research Institute (Cheaters Run), Broadcast Camp (Fishman Island) — остаются (враги орденов).
**Случайные спавны ✓код:** homeless spawns мода — Ultramarines Patrol 01 (Stobe's Gamble, Burning Forest, Venge, Shem, Bonefields, Flats Lagoon ×5, High Bonefields), Extreme Warrior Patrol 02 (Shrieking Forest, Flats Lagoon), Ultramarines patrol (World Eater core: Berserker Country, Purple Sands); relics.arms переносил их в relic_biomes (по 3 записи в каждый) — всего 30 записей, все сняты.
**Ордена с экипировкой (броня/персонажи):** Ультрамарины (Ultramariner/Ultra Warrior/Extreme Warrior/Ultramarines — 20+ вещей, 15 персонажей), Space Wolves (сет терминатора + перчатки, 4 персонажа), Dark Angels (Deathwing терминаторы, 4), Black Templars (Black Templar/Black Sanctuary, 9 персонажей), Imperial Fists (3 вещи, уник Enmu), Salamanders (7 вещей, Kam-уник + Dolon), Deathwatch (15, 4 уника), Grey Knights (8, 3 уника). Хаос: Midnight Lord 33, World Eater 15, Iron Warriors 4, Man-Eating Shark 7.
**Опасные биомы с агрессивным климатом ✓код (SEASON→WEATHER):** Sonorous Dark (Heavy_Rain sonorous acid), Ashlands (Ash-Flakes), Cheaters Run / Forbidden Isle (random acid: Heavy_Rain ACID), Burning Forest (acid forest), The Black Desert (poison gas), Deadlands (Heavy_Rain deadlands GAS), Venge (venge beams), Stobe's Gamble/Sniper Valley (Volcano ash). Все, кроме Cheaters Run, — в arms.relic_biomes.

## Ордена (дизайн = реализация)
| орден (FACTION) | регион | враги рядом | глава (уник) | цель дирижёра |
|---|---|---|---|---|
| Ultramarines (Adeptus Astartes) | Cheaters Run | Night Lords (Human Research Institute), Skin Bandits | Chapter Master Aurelian Varro (клон Quintus Proctor) | hunt_chaos |
| Space Wolves (Adeptus Astartes) | Sonorous Dark + Ashlands | Necrons (Tomb of the Dead), Skinhouse | Wolf Lord Ragnvald Frostfang | hunt_xenos |
| Dark Angels (Adeptus Astartes) | The Black Desert + Deadlands | Rusty Raiders, Black Desert Ninjas, Sailback | Master Zadkiel of the Deathwing | hunt_chaos |
| Black Templars (Adeptus Astartes) | Venge | Oni (Perdition), Thrall Masters | High Marshal Gerold Vane (клон Eckhart) | hunt_chaos |

**Иерархия:** глава (unique, faction importance 100) → капитан (Captain / Wolf Guard Battle Leader / Dark Angels Captain / Castellan) → сержант (Sergeant / Pack Leader / Deathwing Sergeant / Sword Brother) → братья (Battle-Brother, Veteran, Terminator, Deathwing Knight, Initiate). Ранги — клоны CHARACTER мода (броня и оружие своего ордена, раса Astartes, если у исходника не было; имя записи = звание, named=false ?).
**Отряды (SQUAD_TEMPLATE, AI «Patrol map (short range)», не заходят в города):** командный отряд главы (unique-лидер, спавн 1–2), ударный отряд капитана, патруль сержанта; приданные уники мода: Grey Knights Purgation Squad (Garan Crow + 2 Shield Terminator) — с Ультрамаринами, Deathwatch Kill-Team (Black Shield Captain, Thorfinn, Black Shield) — с Волками; Black Shield - Brand Warrior — во внутреннем круге Тёмных Ангелов; Emperor's Champion + Imperial Fist Enmu — свита Верховного маршала. Спавн — только homeless spawns биомов своего региона (веса 1–10, всего 20 записей, масса ~150 при общей ~215000; доля WH в спавнах 1.49 % ≤ 2 %).
**Отношения (FACTION, своя запись):** база Astartes survivors + UC/HN/Shek −10 (после дрожания семени −18…−2, не вражда), Tech Hunters +30, игрок +5, Black Desert Skeletons −5; ордена между собой и с Death Watch/Grey Knight/IER/Lost Black Sanctuary/Astartes survivors +80; хаос, некроны, орки, Hatred of intelligence, Daemons −100; каннибалы, туманники, рыбаки, Skin Bandits, Man-eating shark −60. Недостающие пары дописывает behavior.world_relations по архетипу imperium (имя содержит «Astartes»): бандиты −40, дикари −60, роботы −20; государства −5 не пишутся (|−5−(−5)| < min_delta).
**Минилор:** у FACTION нет поля description в fcs.def ✓код — лор живёт в разговоре: DIALOGUE «KMM Order: <орден>» (PLAYER_TALK_TO_ME через CHARACTER «dialogue», условие my faction = орден): приветствие → кто вы → чего ищете (цель главы) → враги веры (угроза еретикам, «города равнин не трогаем — пока») → прощание; у всех 29 членов отрядов орденов. Глава может стать посланником KMM Diplomacy (envoys p3: уник-лидер отряда).
**Миницели (дирижёр, без новых механик):** орден = реликтовая фракция (RELIC: hunt_chaos/hunt_xenos → mode focused/mobilized, relic_trigger на действия хаоса/некронов), архетип imperium (GOALSET: hunt — рейды/захват ближайших врагов по rel/near, scavenge — экспедиции к руинам, survive), амбиция faith, лагерь модели — руина своего региона (Horrible Ruin, Ashland Dome Ruin, Gas Grove, Ruined Control Tower), сила 71–73, богатство 260; рост силы — ванильные recruit/raid_gain цели hunt.

## Что убрано (обратимо)
- TOWN REMOVED=true (флаг FCS, так rebirth.mod убирает 89 TOWN ✓код): 1033, 424, 462, 758, 947, 1724 — `remove_camps`; вернуть = убрать sid из списка. Здания лагерей остаются пустыми (сносит только KMM_Cleanup по rules/cleanup.json — чужое владение, ?).
- homeless spawns/nests всех отрядов фракции Astartes survivors (30 записей) — `remove_spawn_factions`.
- gen_conductor: снятые лагеря не владения (Astartes survivors без города, x=None).

## Точки ядра / рычаги
### Бродячие отряды региона
Ваниль: BIOME_GROUP.homeless spawns (вес, шаблон) — движок спавнит отряд шаблона в биоме ✓код (fix.homeless_faction: без фракции не спавнит). Lua: нет. Наше: relics.py. Рычаги: веса по ролям в json; второй регион — строка в spawns; рост силы ордена → вес (через дирижёр, ?).
### Отношения фракций
Ваниль: FACTION.relations ✓код. Lua: дирижёр materialize пишет дельты ✓код (KMM_Conductor_Sync). Рычаги: relations_override; союз с игроком через KMM Diplomacy.
### Иерархия и наследование
Ваниль: unique CHARACTER не возрождается ✓код (?) — смерть главы = орден без главы. Рычаг: inheritance дирижёра (осколки/наследование) — ордена туда не включены (следующий шаг).

## ? (не проверено в игре)
- Отряды без поля дома реально бродят по своему биому с «Patrol map (short range)» и не уходят в чужие (как Imperial Remnant Patrol).
- named=false: в игре показывается имя записи («Ultramarines Sergeant»), а не случайное.
- Порог вражды Kenshi для −10…−18 к UC/HN/Shek — нападений нет (ожидание: вражда от ≈−50).
- Salamanders (Kam, Dolon) без ордена: два бойца — мало для фракции; кандидат в 5-й орден. Гардероб добавляет братьям запасное оружие (как всем Astartes) — вес 1 против своего.
