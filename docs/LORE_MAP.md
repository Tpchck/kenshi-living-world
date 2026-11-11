# LORE_MAP — опорная карта ванильного лора (из данных, 2026-11-11)
Источник — только ванильная цепочка gamedata.base → Newwworld.mod → Dialogue.mod → rebirth.mod (порядок по зависимостям в заголовках), собрано `tools\fast\lore_map.py`. Без вики и без модов. Регион = список `biomes` у фракции (её территория). Лидеры = персонажи из условий world states, сменяющих владельцев городов. «НЕ (X жив)» = X мёртв или в плену.

Фракций с городами/лагерями: 48; базовых городов: 227; вариантов override: 121; world states: 152.

## Фракции
| Фракция | Города/лагеря | Регион (biomes) | Лидеры (из world states) | Override-вариантов | Союзы (≥50) | Вражда (≤−50) |
|---|---|---|---|---|---|---|
| United Cities | Bark, Brink, Farming Village, Heft, Clownsteady, Port South, Stoat, Abandoned Town (+15) | Heng, Stormgap Coast, The Great Desert | Emperor Tengu | 38 | Police +100, Traders Guild +100, Slave Traders +60 | The Holy Nation -100 |
| The Holy Nation | Blister Hill, Bad Teeth, Stack, Tiny Settlement, Rebirth, Holy Mines, Holy Farm, Holy Military Base (+8) | Arm of Okran, Okran's Gulf, Okran's Pride, Okran's Valley | High Inquisitor Seta, High Inquisitor Valtena, Holy Lord Phoenix | 29 | — | United Cities -100, Holy Nation Outlaws -100, Mongrel -100, Flotsam Ninjas -100, Shek Kingdom -100 |
| Slave Traders | Slave Farm, Port North, Slave Markets, Slaver Camp, Eyesocket, Stone Camp, Port South, Slave Farm South (+1) | — | — | 11 | Police +100, Traders Guild +100, Imperial Lords +100, United Cities +100, Manhunters +75 | Mongrel -100, Rebel Farmers -100, Anti-Slavers -100 |
| Tech Hunters | Flats Lagoon, Mourn, World's End, Waystation, Black Scratch, Waystation Ruins, Waystation Four, Expedition 5 (+1) | — | — | 0 | Machinists +100, Mongrel +100, Cannibal Hunters +100 | — |
| Cannibals | Cannibal Village 2, Cannibal Village, Suspicious Lab, Cannibal Capital, Cannibals, First Village, Cannibal Infestation | Cannibal Plains, Darkfinger | — | 0 | — | — |
| Shek Kingdom | Admag, Squin, Shek Ruins, Last Stand, Old Frontlines, The Great Fortress | Spider Plains, Stenn Desert | — | 5 | — | The Holy Nation -100 |
| Deadcat | Fishing Village, Gatherer Village, Old Village, Ghost Village, Horrible Ruin | — | — | 1 | — | Cannibals -100, Dust Bandits -50 |
| Swampers | Mud Town, Swamp Village, Shark, Grayflayer Village | — | — | 5 | — | — |
| Nomads | Settled Nomads, Goat Herder's Camp, Nomads, Settled Nomad Village | Bast, Dreg, Flats Lagoon, Heng | — | 1 | Western Hive +50, Empire Peasants +50 | — |
| Skeletons | Black Desert City, Burn's Tower, Drowned Ruins, Scraphouse | — | — | 0 | — | — |
| Western Hive | Hive Village, Western Hive, Distant Hive Village | Vain | The Queen | 4 | — | — |
| Empire Peasants | Vagrant Camp, Empire Village, Old Village | — | — | 0 | United Cities +100 | The Holy Nation -100 |
| Southern Hive | Southern Hive, Southern Hive Village, Hiver-Claimed Armoury | — | Queen of the South | 2 | — | Western Hive -100 |
| Flotsam Ninjas | Flotsam Village, Flotsam Safehouse, Scout Post | — | — | 1 | Deadcat +100 | The Holy Nation -100 |
| Dust Bandits | Dust Bandit Camp, Dust King Tower | Border Zone | — | 0 | — | United Cities -100, Police -100 |
| Traders Guild | Trader's Edge, Raided Caravan | Heng, The Great Desert | Lady Kana, Longen, Slave Market Master, Slave Master Grande, Slave Master Haga | 5 | Slave Traders +100, Police +100, United Cities +100 | — |
| Mercenary Guild | Mercenary base, Mercenary Camp | — | — | 0 | — | — |
| Cannibal Hunters | Camp- Cannibal Hunters, The Bastion | — | — | 0 | Tech Hunters +100 | Cannibals -100 |
| Skin Bandits | Skinhouse HQ, Skinhouse | — | Savant | 3 | Skeleton Legion +100 | Reavers -100, Crab Raiders -100, United Cities -100 |
| Black Dragon Ninjas | Tower Of Ninjas, Black Dragon Camp | — | — | 0 | — | White Eyebrow Clan -100 |
| Holy Nation Outlaws | The Hub, Rebel Base | — | — | 0 | — | The Holy Nation -100 |
| Rebel Farmers | Fort Simion, Raider Camp | — | — | 3 | Empire Peasants +100, Rebel Swordsmen +100 | — |
| Reavers | Reaver Camp, Ark | — | Valamon | 4 | — | Skeleton Bandits -100, Skin Bandits -100, Crab Raiders -100, United Cities -100 |
| Crab Raiders | Crab Village, Crab Town | — | Crab Queen | 3 | Crabs +100 | Skeleton Bandits -100, Reavers -100, United Cities -100 |
| Bloodraiders | Blood Bandit Camp | — | — | 0 | — | — |
| Bounty Hunters | Bounty Hunter Camp | — | — | 0 | Mercenary Police +100, Police +100, United Cities +60 | — |
| United Heroes League | Fort Mirage | — | — | 0 | — | Shek Kingdom -100, Western Hive -100 |
| Nameless | Your Outpost | — | — | 0 | — | Dust Bandits -100 |
| Sand ninjas | Cactus Den | — | — | 0 | — | — |
| Fisher | Dead Fishing Village | — | — | 0 | — | Dust Bandits -50 |
| Hounds | Rot | — | Big Grim | 1 | — | — |
| Stone Rats | Stone Rat Village | — | Big Al | 2 | — | — |
| Grayflayers | Smugglers Bar | — | Big Gray | 0 | — | — |
| Blackshifters | Secret Drug Farm | — | Big Darkbrow | 0 | — | — |
| Band of Bones | Exile Camp | — | Tora The Fearless | 0 | — | Bloodraiders -100, Holy Nation Outlaws -100, Old Machines -100, Police -100, Shek Kingdom -100 |
| Black Dog | Black Dog HQ | — | — | 0 | — | — |
| Anti-Slavers | Spring | — | — | 0 | Rebirth Slaves +100, Slaves +100, Empire Peasants +70, Flotsam Ninjas +70, Tech Hunters +70 | Cannibals -100, Dust Bandits -100, Manhunters -100, United Heroes League -100, Slave Hunters -100 |
| Preacher Cult | Cult Village | — | — | 1 | — | — |
| Mongrel | Mongrel | — | — | 0 | Tech Hunters +100 | The Holy Nation -100 |
| White Eyebrow Clan | White Eyebrow Camp | — | — | 0 | — | Black Dragon Ninjas -100 |
| Berserkers | Berserker Village | — | — | 0 | — | Bloodraiders -100, Holy Nation Outlaws -100, Old Machines -100, Police -100, Shek Kingdom -100 |
| Kral's Chosen | New Kralia | Spider Plains, Stenn Desert | Flying Bull | 1 | — | — |
| Swamp Ninjas | Swamp Ninja Base | South Wetlands | — | 0 | — | Red Sabres -100 |
| Red Sabres | Red Sabre Hideout | — | — | 0 | — | Swamp Ninjas -100 |
| Manhunters | Manhunter Base | — | — | 1 | Slave Traders +100 | — |
| Skeleton Bandits | Iron HQ | — | — | 2 | Skeleton Legion +100 | Reavers -100, Crab Raiders -100, United Cities -100 |
| Scavengers | Old Control Tower | — | — | 0 | — | — |
| The Gorrillo Bandits | The Old Prison | — | — | 0 | — | — |

## World states: что происходит со смертью/пленом лидеров (базовый город → вариант)
**United Cities**
- Bark → «Bark (override prosperous)» (владелец: Empire Peasants) если НЕ (Emperor Tengu жив); НЕ (Lady Sanda жив)
- Bark → «Bark (override) half destroyed» (владелец: United Cities) если НЕ (Lady Sanda жив)
- Bark → «Bark (override) malnourished» (владелец: United Cities) если Lady Sanda жив; НЕ (Slave Master Wada жив); НЕ (Lady Kana жив)
- Bark → «Bark (override prosperous) 2» (владелец: Empire Peasants) если Emperor Tengu жив; НЕ (Lady Sanda жив); НЕ (Slave Master Wada жив); НЕ (Lady Kana жив)
- Brink → «Brink (override) takeover» (владелец: Reavers) если Lady Tsugi НЕ жив; Valamon жив
- Brink → «Brink (override) destroyed» (владелец: United Cities) если НЕ (Lady Tsugi жив); НЕ (Valamon жив)
- Brink → «Brink (override) malnourished» (владелец: United Cities) если НЕ (Slave Master Grande жив); Lady Tsugi жив
- Heft → «Heft (override)» (владелец: Empire Peasants) если НЕ (Emperor Tengu жив)
- Heft → «Heft (override) malnourished» (владелец: United Cities) если Emperor Tengu жив; НЕ (Slave Mistress Ren жив); НЕ (Slave Master Wada жив)
- Heft → «Heft (override) malnourished 2» (владелец: United Cities) если Emperor Tengu жив; НЕ (Slave Master Wada жив); НЕ (Longen жив)
- Heft → «Heft (override) malnourished 3» (владелец: United Cities) если Emperor Tengu жив; НЕ (Slave Master Wada жив); НЕ (Slave Master Ruben жив)
- Clownsteady → «Clownsteady (override) malnourished 1» (владелец: United Cities) если НЕ (Slave Mistress Grace жив)
- … ещё 26
**The Holy Nation**
- Blister Hill → «Blister Hill (override) prosperous» (владелец: Flotsam Ninjas) если НЕ (Holy Lord Phoenix жив); НЕ (High Inquisitor Seta жив); НЕ (High Inquisitor Valtena жив); Moll жив
- Blister Hill → «Blister Hill (override) destroyed» (владелец: The Holy Nation) если НЕ (Holy Lord Phoenix жив)
- Blister Hill → «Blister Hill (override) takeover» (владелец: Holy Nation Outlaws) если НЕ (Holy Lord Phoenix жив); НЕ (Moll жив); НЕ (High Inquisitor Valtena жив); НЕ (High Inquisitor Seta жив)
- Blister Hill → «Blister Hill (override) takeover UC» (владелец: United Cities) если НЕ (Holy Lord Phoenix жив); НЕ (Esata the Stone Golem жив); НЕ (High Inquisitor Valtena жив); НЕ (High Inquisitor Seta жив)
- Bad Teeth → «Bad Teeth (override) half destroyed» (владелец: The Holy Nation) если НЕ (Holy Lord Phoenix жив); High Inquisitor Seta жив
- Bad Teeth → «Bad Teeth (override) takeover» (владелец: Shek Kingdom) если Esata the Stone Golem жив; НЕ (High Inquisitor Seta жив)
- Bad Teeth → «Bad Teeth (override) takeover » (владелец: Kral's Chosen) если НЕ (Esata the Stone Golem жив); НЕ (High Inquisitor Seta жив); Flying Bull жив
- Bad Teeth → «Bad Teeth (override) destroyed» (владелец: The Holy Nation) если НЕ (Holy Lord Phoenix жив); НЕ (High Inquisitor Seta жив); НЕ (Esata the Stone Golem жив); НЕ (Flying Bull жив)
- Bad Teeth → «Bad Teeth (override) takeover UC» (владелец: United Cities) если НЕ (High Inquisitor Seta жив); НЕ (Esata the Stone Golem жив); Emperor Tengu жив; Longen жив; НЕ (High Inquisitor Valtena жив)
- Stack → «Stack (override) takeover» (владелец: Shek Kingdom) если НЕ (High Inquisitor Seta жив); Esata the Stone Golem жив
- Stack → «Stack (override) takeover » (владелец: Kral's Chosen) если НЕ (High Inquisitor Seta жив); НЕ (Esata the Stone Golem жив); Flying Bull жив
- Stack → «Stack (override) destroyed» (владелец: The Holy Nation) если НЕ (Holy Lord Phoenix жив); НЕ (High Inquisitor Seta жив); НЕ (Esata the Stone Golem жив); НЕ (Flying Bull жив)
- … ещё 17
**Slave Traders**
- Slave Farm → «Slave Farm (override) destroyed » (владелец: Slave Traders) если НЕ (Slave Mistress Ren жив)
- Port North → «Port North (override) destroyed» (владелец: Slave Traders) если НЕ (Lady Kana жив)
- Port North → «Port North (override) farm town» (владелец: Empire Peasants) если НЕ (Lord Nagata жив); НЕ (Lady Kana жив); НЕ (Emperor Tengu жив); Boss Simion жив
- Slave Markets → «Slave Market (override) destroyed» (владелец: Slave Traders) если НЕ (Slave Market Master жив)
- Eyesocket → «Eyesocket (override) destroyed» (владелец: Slave Traders) если НЕ (Slave Master Grande жив)
- Stone Camp → «Stone Camp (override) destroyed» (владелец: Slave Traders) если НЕ (Slave Master Haga жив)
- Port South → «Port South (override) destroyed» (владелец: Slave Traders) если НЕ (Slave Master Wada жив)
- Port South → «Port South (override) farm town» (владелец: Empire Peasants) если НЕ (Emperor Tengu жив); НЕ (Slave Master Wada жив); НЕ (Longen жив)
- Slave Farm South → «Slave Farm S (override) destroyed» (владелец: Slave Traders) если НЕ (Slave Mistress Grace жив)
- Slave Farm South → «Slave Farm S (override) farm town» (владелец: Free Traders) если НЕ (Slave Market Master жив); НЕ (Slave Mistress Grace жив)
- South Stone Camp → «South Stone Camp (override) destroyed» (владелец: Slave Traders) если НЕ (Slave Master Ruben жив)
**Shek Kingdom**
- Admag → «Admag (override) Seto» (владелец: Shek Kingdom) если Esata the Stone Golem жив; Seto НЕ жив
- Admag → «Admag (override) esata dead» (владелец: Berserkers) если НЕ (Esata the Stone Golem жив)
- Squin → «Squin (override) destroyed» (владелец: Berserkers) если НЕ (Esata the Stone Golem жив); НЕ (Flying Bull жив); НЕ (Mukai The Mountain жив)
- Squin → «Squin (override) new leader» (владелец: Shek Kingdom) если НЕ (Esata the Stone Golem жив)
- Squin → «Squin (override) takeover» (владелец: Kral's Chosen) если НЕ (Esata the Stone Golem жив); Flying Bull жив; НЕ (Mukai The Mountain жив)
**Deadcat**
- Fishing Village → «Fishing Village (override) slaver takeover» (владелец: Slave Traders) если НЕ (Tinfist жив); Longen жив; Emperor Tengu жив
**Swampers**
- Shark → «Shark (override) blackshifter» (владелец: Swampers) если Big Grim НЕ жив; Big Darkbrow жив
- Shark → «Shark (override) all ded» (владелец: Swampers) если НЕ (Big Darkbrow жив); НЕ (Big Gray жив); Big Grim НЕ жив
- Shark → «Shark (override) Grayflayer» (владелец: Swampers) если Big Grim НЕ жив; Big Gray жив; НЕ (Big Darkbrow жив)
- Grayflayer Village → «Grayflayer Village (override)» (владелец: Swampers) если НЕ (Big Gray жив)
- Grayflayer Village → «Grayflayer Village (override) takeover» (владелец: Band of Bones) если Tora The Fearless жив; НЕ (Big Gray жив); Big Grim НЕ жив
**Nomads**
- Settled Nomads → «Settled Nomads (override) empty» (владелец: Slave Traders) если НЕ (Tinfist жив); Longen жив
**Western Hive**
- Hive Village → «Deadhive Overrun West (override)» (владелец: Fogmen) если НЕ (The Queen жив)
- Western Hive → «Deadhive Overrun West (override)» (владелец: Fogmen) если НЕ (The Queen жив)
- Distant Hive Village → «Deadhive Overrun West (override)» (владелец: Fogmen) если НЕ (The Queen жив)
- Distant Hive Village → «Hive Village N (override) empty» (владелец: Slave Traders) если НЕ (Tinfist жив); Lady Kana жив
**Southern Hive**
- Southern Hive → «Deadhive Overrun South (override)» (владелец: Fogmen) если НЕ (Queen of the South жив)
- Southern Hive Village → «Deadhive Overrun South (override)» (владелец: Fogmen) если НЕ (Queen of the South жив)
**Flotsam Ninjas**
- Flotsam Village → «_Cannibal Village (override)» (владелец: Cannibals) если НЕ (Moll жив)
**Traders Guild**
- Trader's Edge → «Trader's Edge (override) prosperous» (владелец: Anti-Slavers) если НЕ (Longen жив); НЕ (Tinfist НЕ жив); НЕ (Emperor Tengu жив)
- Trader's Edge → «Trader's Edge (override) » (владелец: Empire Peasants) если НЕ (Longen жив); Tinfist НЕ жив; НЕ (Emperor Tengu жив)
- Trader's Edge → «Trader's Edge (override) destroyed» (владелец: Traders Guild) если НЕ (Longen жив); Emperor Tengu жив
- Trader's Edge → «Trader's Edge (override) malnourished» (владелец: Traders Guild) если Longen жив; НЕ (Slave Master Grande жив); НЕ (Slave Master Ruben жив); НЕ (Slave Mistress Ren жив)
- Trader's Edge → «Trader's Edge (override) malnourished 1» (владелец: Traders Guild) если НЕ (Longen жив); НЕ (Slave Master Grande жив); НЕ (Slave Master Ruben жив); НЕ (Slave Mistress Ren жив)
**Skin Bandits**
- Skinhouse HQ → «Skinhouse HQ (override) destroyed» (владелец: —) если НЕ (Savant жив)
- Skinhouse → «Skinhouse (override) destroyed» (владелец: —) если НЕ (Savant жив); НЕ (Queen of the South жив)
- Skinhouse → «Skinhouse (south hive takeover)» (владелец: Southern Hive) если НЕ (Savant жив); Queen of the South жив
**Rebel Farmers**
- Fort Simion → «Fort Yabuta» (владелец: Yabuta Outlaws) если Yabuta of the Sands жив; НЕ (Rebel Farmers: игрок — союзник)
- Fort Simion → «Fort Simion (override destroyed)» (владелец: Rebel Swordsmen) если НЕ (Emperor Tengu жив)
- Raider Camp → «Raider Camp (override)» (владелец: Rebel Swordsmen) если НЕ (Emperor Tengu жив)
**Reavers**
- Reaver Camp → «Reaver Camp (south hive takeover)» (владелец: Southern Hive) если Queen of the South жив; НЕ (Valamon жив)
- Reaver Camp → «Reaver Camp (override) destroyed» (владелец: Reavers) если НЕ (Valamon жив); НЕ (Queen of the South жив)
- Ark → «Ark (override) takover» (владелец: Crab Raiders) если НЕ (Valamon жив); Crab Queen жив
- Ark → «Ark (override) destroyed» (владелец: Vagrants) если НЕ (Valamon жив); НЕ (Crab Queen жив)
**Crab Raiders**
- Crab Village → «Crab Village (override) Reaver takeover» (владелец: Reavers) если НЕ (Crab Queen жив); Valamon жив
- Crab Village → «Crab Village (override) destroyed» (владелец: Crab Raiders) если НЕ (Crab Queen жив); НЕ (Valamon жив)
- Crab Town → «Crab Town (override) Gurgler takeover» (владелец: Fishmen) если НЕ (Crab Queen жив)
**Hounds**
- Rot → «Rot (override)» (владелец: Spiders) если Big Grim НЕ жив; НЕ (Big Darkbrow жив); НЕ (Big Gray жив)
**Stone Rats**
- Stone Rat Village → «Stone Rat Village (override)» (владелец: Hounds) если НЕ (Big Al жив); НЕ (Big Grim НЕ жив)
- Stone Rat Village → «Stone Rat Village (takeover)» (владелец: Swamp Ninjas) если Big Grim НЕ жив; НЕ (Big Al жив); Shade жив
**Preacher Cult**
- Cult Village → «Cult village (override) slaver takeover» (владелец: Slave Traders) если НЕ (Tinfist жив); Longen жив; Slave Master Grande жив
**Kral's Chosen**
- New Kralia → «New Kralia (override)» (владелец: Kral's Chosen) если НЕ (Flying Bull жив)
**Manhunters**
- Manhunter Base → «Manhunter Base (override)» (владелец: Mercenary Guild) если НЕ (Slave Market Master жив); НЕ (Slave Mistress Grace жив)
**Skeleton Bandits**
- Iron HQ → «Iron HQ (south hive takeover)» (владелец: Southern Hive) если НЕ (Elder жив); Queen of the South жив
- Iron HQ → «Iron HQ (destroyed)» (владелец: Skeleton Bandits) если НЕ (Queen of the South жив); НЕ (Elder жив)
