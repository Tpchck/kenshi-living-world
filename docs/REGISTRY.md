# REGISTRY - реестр мира

Генерация: `python -I -X utf8 tools\registry.py` (2026-11-14 14:22), только чтение. Полные данные: `data/registry.json`.
Слои и механики: [STATUS.md](STATUS.md), [MECHANICS.md](MECHANICS.md). Данные «до» = 662 мода без наших слоёв, «после» = с KMM-слоями (без Cleanup, он для новой игры).

## Сводка

| что | число |
|---|---|
| factions | 294 |
| hidden | 145 |
| characters | 2176 |
| uniques | 618 |
| assigned_chars | 1678 |
| towns | 933 |
| town_overrides | 362 |
| races | 1965 |
| races_alive | 125 |
| kmm_new_factions | 2 |
| layers | 21 |

Источник фракции персонажа: {'squad': 1295, 'town': 354, 'character': 29}.

### Слои KMM

| слой | записей | фракций | городов | персонажей |
|---|---|---|---|---|
| KMM_Atlas | 230 | 6 | 203 | 21 |
| KMM_Behavior | 144 | 143 | 0 | 0 |
| KMM_Cleanup | 52 | 0 | 33 | 0 |
| KMM_Conductor | 0 | 0 | 0 | 0 |
| KMM_Core | 4 | 0 | 0 | 0 |
| KMM_Diplo | 1140 | 0 | 0 | 159 |
| KMM_Economy | 2446 | 0 | 73 | 1775 |
| KMM_Elite | 288 | 2 | 0 | 0 |
| KMM_Fix | 729 | 0 | 83 | 0 |
| KMM_Glue | 1748 | 54 | 0 | 1674 |
| KMM_Merged | 3257 | 14 | 37 | 151 |
| KMM_Native | 0 | 0 | 0 | 0 |
| KMM_Ore | 0 | 0 | 0 | 0 |
| KMM_Relics | 726 | 1 | 0 | 0 |
| KMM_Rumors | 0 | 0 | 0 | 0 |
| KMM_Stock | 0 | 0 | 0 | 0 |
| KMM_Tech | 41 | 0 | 0 | 0 |
| KMM_Tempo | 0 | 0 | 0 | 0 |
| KMM_Town | 253 | 0 | 0 | 0 |
| KMM_Traces | 1152 | 0 | 0 | 0 |
| KMM_Wardrobe | 1409 | 0 | 0 | 1331 |

Новые фракции, созданные слоями: 1-KMM_Relics.mod (1-KMM_Relics.mod), 1-KMM_Glue.mod (1-KMM_Glue.mod)

## Пробелы

- **factions_no_chars**: 126
- **factions_no_towns**: 119
- **factions_empty**: 85
- **towns_no_owner**: 118
- **towns_no_owner_override**: 9
- **uniques_no_faction**: 47
- **chars_no_faction**: 498
- **chars_multi_faction**: 157
- **towns_not_in_conductor**: 201
- **conductor_towns_missing_in_game**: 0
- **conductor_factions_missing_in_game**: 1
- **gang_fids_missing**: 0

### Фракции с одинаковым именем

| имя | sid (создатель, перс./города) |
|---|---|
| Drifters | `51707-rebirth.mod` (155/2); `3144-Band of Exiles.mod` (2/0) |
| Gunsmiths | `5007395-The Shoddy Firearm Mod.mod` (3/1); `25-BlackPowder.mod` (2/1) |
| Gutters | `51812-rebirth.mod` (1/9); `5007474-Lovely Gutter.mod` (0/1) |
| Holy Nation Outlaws | `42022-rebirth.mod` (16/16); `6485-Band of Exiles.mod` (2/0) |
| Old Machines | `42085-rebirth.mod` (18/3); `5008655-HTDEnforcers.mod` (0/0) |
| Outlaw | `5442-gamedata.base` (35/4); `1535100-CanyonKillerBounty.mod` (1/0) |
| Second Empire | `49356-rebirth.mod` (13/25); `7993-Band of Exiles.mod` (1/0) |
| The Holy Nation | `1083-gamedata.base` (88/76); `352-cook_set.mod` (6/0) |
| White Wolves | `5007941-Edit Dogs.mod` (0/1); `2757668-GreatDirewolf.mod` (1/1) |

### Пустые фракции (0 персонажей и 0 городов)

| фракция | создатель | скрыта | тип | слои |
|---|---|---|---|---|
| Medics Guild (`1234-gamedata.base`) | gamedata.base |  | CIVILIAN | - |
| Mercenary Police (`1171-gamedata.base`) | gamedata.base |  | LAW | - |
| Imperial Lords (`1087-gamedata.base`) | gamedata.base |  | CIVILIAN | - |
| generation template (`GENERATION_TEMPLATE_FACTION`) | ? |  | CIVILIAN | - |
| Temple of truth (`1086-gamedata.base`) | gamedata.base |  | CIVILIAN | - |
| Fisher (`1209-gamedata.base`) | gamedata.base |  | CIVILIAN | - |
| Crimper (`65263-Newwworld.mod`) | Newwworld.mod | да | NONE | - |
| Skeleton MkII (`65268-Newwworld.mod`) | Newwworld.mod |  | ADVENTURER | - |
| Skeleton MkII Log Head (`66532-Newwworld.mod`) | Newwworld.mod |  | ADVENTURER | - |
| Skeleton MkII Screamer (`1533505-Newwworld.mod`) | Newwworld.mod |  | ADVENTURER | - |
| Okranites (`46241-Dialogue.mod`) | Dialogue.mod |  | CIVILIAN | - |
| Republic of Tertius (`15579-Dialogue.mod`) | Dialogue.mod |  | CIVILIAN | - |
| Broken Cities (`18897-rebirth.mod`) | rebirth.mod |  | CIVILIAN | - |
| The Old Empire (`14459-rebirth.mod`) | rebirth.mod | да | MILITARY | - |
| Gorillos (`51813-rebirth.mod`) | rebirth.mod | да | NONE | - |
| Megacity (`56101-rebirth.mod`) | rebirth.mod | да | BANDIT | - |
| The Public (`5032584-INTERACTIONS PLUS.mod`) | INTERACTIONS PLUS.mod | да | CIVILIAN | - |
| Natsuko Found (`5007930-ChildrenOfKenshi.mod`) | ChildrenOfKenshi.mod | да | SLAVE | - |
| Search for Natsuko (`5007981-ChildrenOfKenshi.mod`) | ChildrenOfKenshi.mod | да | SLAVE | - |
| Anti-Slavers want to recruit parent (`5008117-ChildrenOfKenshi.mod`) | ChildrenOfKenshi.mod | да | SLAVE | - |
| Natsuko Delivered (`5008135-ChildrenOfKenshi.mod`) | ChildrenOfKenshi.mod | да | SLAVE | - |
| Parent Delivered (`5008136-ChildrenOfKenshi.mod`) | ChildrenOfKenshi.mod | да | SLAVE | - |
| Lana Delivered (`5008197-ChildrenOfKenshi.mod`) | ChildrenOfKenshi.mod | да | SLAVE | - |
| Flotsam want to recruit parent (`5008141-ChildrenOfKenshi.mod`) | ChildrenOfKenshi.mod | да | SLAVE | - |
| BoR Test (`5979-Band of Exiles.mod`) | Band of Exiles.mod | да | ADVENTURER | - |
| FACTION (`380-Workshop Severin Instagram.mod`) | Workshop Severin Instagram.mod |  | CIVILIAN | - |
| Motoko visited Crab Raiders Settlement (`17-MotokoTheHuntress.mod`) | MotokoTheHuntress.mod | да | NONE | - |
| Motoko visited Deadcat Settlement (`18-MotokoTheHuntress.mod`) | MotokoTheHuntress.mod | да | NONE | - |
| Motoko visited Fishmen Settlement (`19-MotokoTheHuntress.mod`) | MotokoTheHuntress.mod | да | NONE | - |
| Motoko The Huntress (`763-MotokoTheHuntress.mod`) | MotokoTheHuntress.mod | да | NONE | - |
| Motoko Defects (`914-MotokoTheHuntress.mod`) | MotokoTheHuntress.mod | да | NONE | - |
| Goats (`10-Symbiosis.mod`) | Symbiosis.mod | да | CIVILIAN | - |
| Wild Bulls (`46-Symbiosis.mod`) | Symbiosis.mod | да | CIVILIAN | - |
| Deathclaws (`1535128-TIHYD_Zoo.mod`) | TIHYD_Zoo.mod | да | NONE | - |
| Striders (`1535105-TIHYD_Landstrider.mod`) | TIHYD_Landstrider.mod | да | NONE | - |
| Ogres (`1535447-Aminals.mod`) | Aminals.mod | да | SLAVER | - |
| Striped Hounds (`5007933-Edit Dogs.mod`) | Edit Dogs.mod | да | NONE | - |
| Boneyard Wolves (`5007981-Edit Dogs.mod`) | Edit Dogs.mod | да | NONE | - |
| Mech Life (`1533750-Mech-Leviathan.mod`) | Mech-Leviathan.mod | да | NONE | - |
| Pirate Boss captured (`15-Dread Pirate Roberts.mod`) | Dread Pirate Roberts.mod | да | CIVILIAN | - |
| Resort Island (`10-Resort Island.mod`) | Resort Island.mod | да | ADVENTURER | - |
| Rent Shinobi tracker (`89-Rent Hous in Your Town Mod.mod`) | Rent Hous in Your Town Mod.mod |  | CIVILIAN | - |
| Inaba Ronin (`5004570-Bandit Variety.mod`) | Bandit Variety.mod | да | ADVENTURER | - |
| Nagata Ronin (`5004571-Bandit Variety.mod`) | Bandit Variety.mod | да | ADVENTURER | - |
| Sanda Ronin (`5004572-Bandit Variety.mod`) | Bandit Variety.mod | да | ADVENTURER | - |
| Tengu Ronin (`5004540-Bandit Variety.mod`) | Bandit Variety.mod | да | ADVENTURER | - |
| Yoshinaga Ronin (`5004573-Bandit Variety.mod`) | Bandit Variety.mod | да | ADVENTURER | - |
| Chakkari (`5008101-Kaizo.mod`) | Kaizo.mod | да | SLAVER | - |
| The Holy Nation (postwar) (placeholder) (`5008718-Kaizo.mod`) | Kaizo.mod |  | CIVILIAN | - |
| Deadcat Refugees (`494-Great Frontiers - World Overhaul.mod`) | Great Frontiers - World Overhaul.mod |  | CIVILIAN | - |
| Dust Union (`177-Great Frontiers - World Overhaul.mod`) | Great Frontiers - World Overhaul.mod |  | BANDIT | KMM_Behavior,KMM_Glue |
| Empty Land (`515-Great Frontiers - World Overhaul.mod`) | Great Frontiers - World Overhaul.mod |  | CIVILIAN | - |
| trig1 (`262-Great Frontiers - World Overhaul.mod`) | Great Frontiers - World Overhaul.mod |  | CIVILIAN | - |
| trig2 (`263-Great Frontiers - World Overhaul.mod`) | Great Frontiers - World Overhaul.mod |  | CIVILIAN | - |
| trig3 (`301-Great Frontiers - World Overhaul.mod`) | Great Frontiers - World Overhaul.mod |  | CIVILIAN | - |
| Buckets of Rust (`13-Rust Bucket (Roaming Boss).mod`) | Rust Bucket (Roaming Boss).mod | да | MILITARY | - |
| Domesticated Crabs (`74-AnnexFishmanIsland.mod`) | AnnexFishmanIsland.mod | да | NONE | - |
| Taste of Gurgler (`5007468-Lovely Gutter.mod`) | Lovely Gutter.mod | да | CIVILIAN | - |
| Taste of Shek (`5007426-Lovely Gutter.mod`) | Lovely Gutter.mod | да | CIVILIAN | - |
| Taste of Hive (`5007425-Lovely Gutter.mod`) | Lovely Gutter.mod | да | CIVILIAN | - |
| Taste of Human (`5007424-Lovely Gutter.mod`) | Lovely Gutter.mod | да | CIVILIAN | - |
| Nutrition of Gutter (`5007450-Lovely Gutter.mod`) | Lovely Gutter.mod | да | CIVILIAN | - |
| Electromagnetic waves that Gutters hate (`5007496-Lovely Gutter.mod`) | Lovely Gutter.mod | да | CIVILIAN | - |
| Intelligence of Gutter (`5007453-Lovely Gutter.mod`) | Lovely Gutter.mod | да | CIVILIAN | - |
| Machine Oil (`5007532-Lovely Gutter.mod`) | Lovely Gutter.mod | да | CIVILIAN | - |
| Branding Curse (`1833-TEXT TEXTURE.mod`) | TEXT TEXTURE.mod |  | MILITARY | - |
| Khorasan strikes (`1991-TEXT TEXTURE.mod`) | TEXT TEXTURE.mod | да | MILITARY | - |
| Astartes Support Level 02 (`2307-TEXT TEXTURE.mod`) | TEXT TEXTURE.mod | да | MILITARY | - |
| Astartes Support Level 01 (`2309-TEXT TEXTURE.mod`) | TEXT TEXTURE.mod | да | MILITARY | - |
| Mission - Reconnaissance (`2362-TEXT TEXTURE.mod`) | TEXT TEXTURE.mod |  | CIVILIAN | - |
| Astartes Support Level 03 (`2486-TEXT TEXTURE.mod`) | TEXT TEXTURE.mod | да | MILITARY | - |
| Astartes Support Level 04 (`2488-TEXT TEXTURE.mod`) | TEXT TEXTURE.mod | да | MILITARY | - |
| Blood Sacrifice (`2817-TEXT TEXTURE.mod`) | TEXT TEXTURE.mod | да | MILITARY | - |
| World Eater Attack (`2842-TEXT TEXTURE.mod`) | TEXT TEXTURE.mod | да | MILITARY | - |
| World Eater Incident (`2921-TEXT TEXTURE.mod`) | TEXT TEXTURE.mod |  | MILITARY | - |
| Fear (`3701-TEXT TEXTURE.mod`) | TEXT TEXTURE.mod |  | MILITARY | - |
| 游骑兵 (`92-Metro.mod`) | Metro.mod |  | ADVENTURER | - |
| Cloud House (`5008815-Rusty Raiders FACTION.mod`) | Rusty Raiders FACTION.mod | да | CIVILIAN | - |
| Major Nails (`5008928-Rusty Raiders FACTION.mod`) | Rusty Raiders FACTION.mod | да | ADVENTURER | - |
| Stobe's Chosen (`5025461-Rusty Raiders FACTION.mod`) | Rusty Raiders FACTION.mod | да | ADVENTURER | - |
| Old Machines (`5008655-HTDEnforcers.mod`) | HTDEnforcers.mod | да | MILITARY | KMM_Behavior |
| Behemoth Remnants (`4998888-Throes of Obedience.mod`) | Throes of Obedience.mod | да | NONE | - |
| Daemons (`1000008-ChaosDaemonsStandalone.mod`) | ChaosDaemonsStandalone.mod | да | BANDIT | KMM_Behavior,KMM_Merged |
| 旧日实验体事件开启 (`97-KillerRobot.mod`) | KillerRobot.mod | да | CIVILIAN | - |
| 狼卫信息 (`298-KillerRobot.mod`) | KillerRobot.mod |  | CIVILIAN | - |

### Города без владельца (не override)

| город | sid | тип | регион |
|---|---|---|---|
| MARKER-Nest-Cower | `40594-Newwworld.mod` | 8 |  |
| nest spiders | `50322-rebirth.mod` | 0 |  |
| nestruin- holy outpost | `44887-rebirth.mod` | 1 |  |
| ruin warehouse | `44902-rebirth.mod` | 1 |  |
| nest armoury ruin | `49940-rebirth.mod` | 0 |  |
| nest library ruin | `49933-rebirth.mod` | 0 |  |
| ruin- fogman resident | `44898-rebirth.mod` | 0 |  |
| -nest housecamp | `44425-rebirth.mod` | 10 |  |
| floodland sword nest | `48706-rebirth.mod` | 0 |  |
| spider camp marker | `42025-rebirth.mod` | 8 |  |
| nest- shek military ruins | `51328-rebirth.mod` | 0 |  |
| nest- lab ruin | `51377-rebirth.mod` | 0 |  |
| nest- king gorillo | `62769-rebirth.mod` | 0 |  |
| housecamp raider | `95531-rebirth.mod` | 10 |  |
| nest trashed house | `96160-rebirth.mod` | 10 |  |
| nest housecamp fishman | `97660-rebirth.mod` | 10 |  |
| nest- lab ruin gurglers | `97663-rebirth.mod` | 0 |  |
| housecamp raider w/poles | `1531900-rebirth.mod` | 10 |  |
| nest spiders bones | `1533726-__world reactios swamp.mod` | 0 |  |
| Waystation [Tech Scribes] | `1541808-GenMod.mod` | 1 |  |
| The Hub (override) shek stage 1 | `1533754-Reactive World.mod` | 1 |  |
| The Hub (override) shek stage 2 Bandits | `1533755-Reactive World.mod` | 1 |  |
| The Hub (override) shek stage 3 | `1533765-Reactive World.mod` | 1 |  |
| The Hub (override) shek stage 2 HN | `1533764-Reactive World.mod` | 1 |  |
| Ghost Village (override) Deadcat CH FT | `4998344-Reactive World.mod` | 1 |  |
| Ghost Village (override) Deadcat CH WH | `4998345-Reactive World.mod` | 1 |  |
| Ghost Village (override) Deadcat FN FT | `4998346-Reactive World.mod` | 1 |  |
| Ghost Village (override) Deadcat FN WH | `4998347-Reactive World.mod` | 1 |  |
| Ghost Village (override) Deadcat Merc FT | `4998348-Reactive World.mod` | 1 |  |
| Ghost Village (override) Deadcat Merc WH | `4998349-Reactive World.mod` | 1 |  |
| Last Stand (override) Prosperous | `4999384-Reactive World.mod` | 1 |  |
| Drifter's Last (override) HR takeover | `2758523-Minor Factions Expansion.mod` | 1 |  |
| Ghost Village (Deadcatun override) | `1533842-Deadcat Extended.mod` | 1 |  |
| Kopek | `2757465-Hook Rebels.mod` | 1 |  |
| Kopek (Override) Hooch | `2757541-Hook Rebels.mod` | 1 |  |
| Mud Town (override) Blue Cleavers | `2760333-Minor Factions Expansion.mod` | 1 |  |
| Mud Town (override) Grayflayer | `2760332-Minor Factions Expansion.mod` | 1 |  |
| Mud Town (override) Hounds | `2760330-Minor Factions Expansion.mod` | 1 |  |
| Narko's Refuge | `2757341-Narko's Disciples.mod` | 1 |  |
| Narko's Spear (override) ND | `4999258-Minor Factions Expansion.mod` | 1 |  |
| Rot (override) | `2760342-Minor Factions Expansion.mod` | 1 |  |
| Rot (override) Grayflayers | `2760344-Minor Factions Expansion.mod` | 1 |  |
| Sakar | `2757481-Bele'coz.mod` | 1 |  |
| Sakar (override) Kraz | `2757530-Bele'coz.mod` | 1 |  |
| Shraff | `2757433-Dune Rebels.mod` | 1 |  |
| Shraff (override) Jeremiah | `2757549-Dune Rebels.mod` | 1 |  |
| The Hub (override) [harenga ded] | `2757461-The Hub Re-Established.mod` | 1 |  |
| The Hub (override) [seta ded] {esata alive} | `2757469-The Hub Re-Established.mod` | 1 |  |
| Tiny Settlement (Override) Marissa | `2757625-The Hub Re-Established.mod` | 1 |  |
| Waystation Highlander BZ HQ | `2759753-Minor Factions Expansion.mod` | 1 |  |
| Waystation Highlander HN Territory HQ | `2759754-Minor Factions Expansion.mod` | 1 |  |
| Waystation Highlander Shem | `2759751-Minor Factions Expansion.mod` | 1 |  |
| Last Stand (override) malnourished | `2760647-Shek Kingdom Expansion.mod` | 1 |  |
| Last Stand (override) prosperous | `2760646-Shek Kingdom Expansion.mod` | 1 |  |
| Squin (override) malnourished | `2760642-Shek Kingdom Expansion.mod` | 1 |  |
| Bast (override) strengthened | `2759690-UC Heightened.mod` | 1 |  |
| Drin (override) strengthened | `2759695-UC Heightened.mod` | 1 |  |
| Bad Teeth (override) malnourished | `2760635-HN Ascended.mod` | 1 |  |
| Blister Hill (override) malnourished | `2760638-HN Ascended.mod` | 1 |  |
| Stack (override) malnourished | `2760616-HN Ascended.mod` | 1 |  |
| Last Stand (override) Bele'coz | `5009250-Universal Wasteland Expansion.mod` | 1 |  |
| Last Stand (override) Bele'coz esata dead | `5009259-Universal Wasteland Expansion.mod` | 1 |  |
| Bad Teeth (override) half destroyed malnourished | `5009624-Universal Wasteland Expansion.mod` | 1 |  |
| Bad Teeth (override) takeover Bele'coz | `5009625-Universal Wasteland Expansion.mod` | 1 |  |
| Bad Teeth (override) takeover UC destroyed | `5009626-Universal Wasteland Expansion.mod` | 1 |  |
| Bast (override) EP | `5009631-Universal Wasteland Expansion.mod` | 1 |  |
| Drin (override) Bastards | `5009664-Universal Wasteland Expansion.mod` | 1 |  |
| Bast (override) HN | `5009666-Universal Wasteland Expansion.mod` | 1 |  |
| Stack (override) takeover Bele'coz | `5009676-Universal Wasteland Expansion.mod` | 1 |  |
| Drifter's Last (override) EP | `5009804-Universal Wasteland Expansion.mod` | 1 |  |
| Sho-Battai (override) DR | `5009805-Universal Wasteland Expansion.mod` | 1 |  |
| Waystation Highlander BZ HQ (override) HNO | `5010535-Universal Wasteland Expansion.mod` | 1 |  |
| Waystation Highlander BZ HQ (override) HN | `5010536-Universal Wasteland Expansion.mod` | 1 |  |
| Waystation Highlander BZ HQ (override) Drifters | `5010537-Universal Wasteland Expansion.mod` | 1 |  |
| Waystation Highlander HN Territory HQ (override) HN | `5010539-Universal Wasteland Expansion.mod` | 1 |  |
| Waystation Highlander HN Territory HQ (override) Flotsam | `5010540-Universal Wasteland Expansion.mod` | 1 |  |
| Waystation Highlander HN Territory HQ (override) Drifters | `5010542-Universal Wasteland Expansion.mod` | 1 |  |
| Waystation Highlander Shem (override) WEC | `5010543-Universal Wasteland Expansion.mod` | 1 |  |
| Waystation Highlander Shem (override) Nomads | `5010544-Universal Wasteland Expansion.mod` | 1 |  |
| World's End (override) HN | `5010922-Universal Wasteland Expansion.mod` | 1 |  |
| World's End (override) Flotsam | `5010924-Universal Wasteland Expansion.mod` | 1 |  |
| World's End (override) Deadcat | `5010925-Universal Wasteland Expansion.mod` | 1 |  |
| World's End (override) UC | `5010926-Universal Wasteland Expansion.mod` | 1 |  |
| World's End (override) Northern Hive | `5010927-Universal Wasteland Expansion.mod` | 1 |  |
| Flats Lagoon (override) UC | `5010929-Universal Wasteland Expansion.mod` | 1 |  |
| Flats Lagoon (override) AS | `5010930-Universal Wasteland Expansion.mod` | 1 |  |
| Flats Lagoon (override) ruins | `5010933-Universal Wasteland Expansion.mod` | 1 |  |
| Mourn (override) UC | `5010936-Universal Wasteland Expansion.mod` | 1 |  |
| Mourn (override) Southern Hive | `5010937-Universal Wasteland Expansion.mod` | 1 |  |
| Mourn (override) AS | `5010938-Universal Wasteland Expansion.mod` | 1 |  |
| Mourn (override) Scorched Ones | `5010939-Universal Wasteland Expansion.mod` | 1 |  |
| Black Scratch (override) UC | `5010941-Universal Wasteland Expansion.mod` | 1 |  |
| Black Scratch (override) Black Dog | `5010944-Universal Wasteland Expansion.mod` | 1 |  |
| Black Scratch (override) Preacher Cult | `5010945-Universal Wasteland Expansion.mod` | 1 |  |
| Black Scratch (override) Reavers | `5010946-Universal Wasteland Expansion.mod` | 1 |  |
| Black Scratch (override) Crab Raiders | `5010947-Universal Wasteland Expansion.mod` | 1 |  |
| Black Scratch (override) AS | `5010948-Universal Wasteland Expansion.mod` | 1 |  |
| The Hub [override] ruins | `5011017-Universal Wasteland Expansion.mod` | 1 |  |
| The Hub (override) [seta ded] {mukai alive} | `5011018-Universal Wasteland Expansion.mod` | 1 |  |
| Clownsteady (override) HR takeover | `5016481-Universal Wasteland Expansion.mod` | 1 |  |
| Drifter's Raceway | `5026607-Universal Wasteland Expansion.mod` | 1 |  |
| Waystation Ruins Venge (player override) | `5030304-Universal Wasteland Expansion.mod` | 1 |  |
| Waystation Ruins Stobe G (player override) | `5030316-Universal Wasteland Expansion.mod` | 1 |  |
| Victor's House (Abandoned) | `1051-Companion Quest - Morse.mod` | 9 |  |
| Strange Den | `5132036-Dark Hive.mod` | 9 |  |
| Poisonous Lab | `195-Animal Variations.mod` | 4 |  |
| Martyrs Pit | `1535496-Bounties Galore.mod` | 3 |  |
| Mysterious Tower | `39-Warrior Moon - Polearms Expansion.mod` | 10 |  |
| -nest housecamp reapers | `5004757-Bandit Variety.mod` | 10 |  |
| -nest housecamp fishman annex | `56-AnnexFishmanIsland.mod` | 10 |  |
| Branding Camp | `1724-TEXT TEXTURE.mod` | 4 |  |
| Backpack "Research Institute" | `2034-TEXT TEXTURE.mod` | 4 |  |
| "phantom" | `2664-TEXT TEXTURE.mod` | 4 |  |
| Silent Camp | `3198-TEXT TEXTURE.mod` | 4 |  |
| Silent Camp 01FA | `3835-TEXT TEXTURE.mod` | 4 |  |
| Obedience | `5008579-Rusty Raiders FACTION.mod` | 9 |  |
| Abandoned Farm House | `5008817-Rusty Raiders FACTION.mod` | 4 |  |
| 失控的武士实验室 | `178-KillerRobot.mod` | 4 |  |

### Уники без фракции

- Peace (`226-gamedata.base`)
- Garp (`223-gamedata.base`)
- Old Man Fisher (`2830-gamedata.base`)
- Crow Face (`51008-Newwworld.mod`)
- imprisoned skeleton recruit (`46229-Dialogue.mod`)
- Bluerain (`5007320-Radiant Ancient Hive.mod`)
- Akusa (`5011723-Radiant Ancient Hive.mod`)
- Lumion (`5011724-Radiant Ancient Hive.mod`)
- Xceio (`5011725-Radiant Ancient Hive.mod`)
- Jiyha (`5011726-Radiant Ancient Hive.mod`)
- Calir (`5011727-Radiant Ancient Hive.mod`)
- Neeroi (`5011728-Radiant Ancient Hive.mod`)
- Progenitor (`5007507-Hive Cybernetics.mod`)
- Dr. Rygel Zool (`5007359-The Eternal Laboratory.mod`)
- Sheeshy (`35-SheeshSkins x FemaleGreenlanderFace.mod`)
- Noble's Child (`1535111-Lore Starts.mod`)
- Madam Crimson (`8554-Band of Exiles.mod`)
- Razor (до изменения тела) это нето если смотриш! (`304-Workshop Severin Instagram.mod`)
- Zoo Runner (`1535101-TIHYD_Zoo.mod`)
- Compassion Bringer (`5007381-Blood Savior.mod`)
- Education Bringer (`5007403-Blood Savior.mod`)
- Salvation Bringer (`5007401-Blood Savior.mod`)
- Toleration Bringer (`5007402-Blood Savior.mod`)
- Cat-Lon helper (`170-Iron_Hounds.mod`)
- SethWeak Copy (`2757807-GreatDirewolf.mod`)
- Тору (`1057-social lives (United Cities).mod`)
- Vice-Commander Abraham (`1533393-Guild of Surgeons.mod`)
- _Bounty Test Char (`1535671-Bounties Galore.mod`)
- The Crimson Ronin (`53-Sacred Trash.mod`)
- Bounty Hunter (`01-Freelance Hunter.mod`)
- Inquisitor Zeno (`5000242-Bandit Variety.mod`)
- Kujang (`5007573-Kaizo.mod`)
- Salukat (`5007575-Kaizo.mod`)
- Alamang (`5007576-Kaizo.mod`)
- Nagamaki (`5007578-Kaizo.mod`)
- Kamayari (`5007579-Kaizo.mod`)
- Fauchard (`5007580-Kaizo.mod`)
- Sarissa (`5007581-Kaizo.mod`)
- Steel Legion (`5007431-Steel Legion Armor Mod.mod`)
- Skeleton Bandit (`5007450-Steel Legion Armor Mod.mod`)
- Grey Knight - Shield Terminator 2 (with Power Sword) (`952-TEXT TEXTURE.mod`)
- Black Shield - Brand Warrior (`1710-TEXT TEXTURE.mod`)
- Imperial Guard - Achilles Terminator (Black) (`1843-TEXT TEXTURE.mod`)
- Imperial Guard - Achilles Terminator (Gold) - No cloak, no crown (`1857-TEXT TEXTURE.mod`)
- Demon Phantom (`1858-TEXT TEXTURE.mod`)
- Khorne Resurrection - Case (`1873-TEXT TEXTURE.mod`)
- Midnight Lord - Karl's Replication Staining Test (`3838-TEXT TEXTURE.mod`)

## Расы

Всего 1965; в мире есть персонажи у 125. Ванильных: 54. Группы дублей из race_audit: 116.

### Ванильные и живые расы

| раса | ваниль | живых перс. | фракций | playable |
|---|---|---|---|---|
| Greenlander | да | 347 | 86 | True |
| Scorchlander | да | 237 | 75 | True |
| Shek | да | 160 | 74 | True |
| Hive Prince | да | 92 | 63 | True |
| Skeleton | да | 74 | 50 | True |
| Hive Soldier Drone | да | 62 | 60 | True |
| Hive Worker Drone | да | 57 | 48 | True |
| P4 Unit | да | 43 | 34 | True |
| Skeleton P4MkII | да | 33 | 29 | True |
| Cannibal | да | 31 | 1 | True |
| Screamer MkI | да | 27 | 2 | True |
| Hive Soldier Drone South Hive | да | 26 | 16 | False |
| Hive Prince South Hive | да | 23 | 16 | False |
| Hive Worker Drone South Hive | да | 20 | 18 | False |
| Skeleton No-Head MkII  | да | 19 | 0 | False |
| Skeleton Log-Head MKII | да | 18 | 3 | True |
| Soldierbot | да | 15 | 2 | True |
| Skeleton MKII Screamer | да | 14 | 2 | True |
| Deadhive Soldier | да | 9 | 0 | True |
| Deadhive Prince | да | 7 | 0 | True |
| Fishman | да | 6 | 1 | False |
| Flayed Man | да | 6 | 0 | True |
| Cannibal Skav | да | 5 | 1 | True |
| Deadhive Worker | да | 5 | 1 | True |
| Alpha Fishman | да | 3 | 0 | True |
| Hive Queen | да | 2 | 0 | True |
| Flayed Woman | да | 1 | 0 | True |
| Skimmer | да | 1 | 0 | False |
| Alpha Fishman | да | 1 | 0 | False |
| Garru | да | 0 | 0 | False |
| Cage Beast | да | 0 | 0 | False |
| Goat | да | 0 | 0 | False |
| Bull | да | 0 | 0 | False |
| Swamp Turtle | да | 0 | 0 | False |
| Beak Thing | да | 0 | 0 | False |
| Leviathan | да | 0 | 0 | False |
| Robot Spider Worker | да | 0 | 0 | False |
| Bonedog | да | 0 | 0 | False |
| Hive Tall Head | да | 0 | 0 | True |
| Crab | да | 0 | 0 | False |
| Big-Bones | да | 0 | 0 | False |
| ----edad | да | 0 | 0 | True |
| Crimper | да | 0 | 0 | False |
| Boneyard Wolf | да | 0 | 0 | False |
| Land Bat | да | 0 | 0 | False |
| Bull (domesticated) | да | 0 | 0 | False |
| Robot Guard Spider | да | 0 | 0 | False |
| Spider | да | 0 | 0 | False |
| River Raptor | да | 0 | 0 | False |
| Swamp Raptor | да | 0 | 0 | False |
| Gorillo | да | 0 | 0 | False |
| Small Spider | да | 0 | 0 | False |
| Black Gorillo | да | 0 | 0 | False |
| King Fishman | да | 0 | 0 | False |
| Dark Hive Worker Drone | Animation - Collection Pack.mod | 38 | 22 | True |
| Dark Hive Soldier Drone | Animation - Collection Pack.mod | 33 | 24 | True |
| Astartes (Elite) | Animation - Collection Pack.mod | 29 | 0 | True |
| Greenlander Child | Animation - Collection Pack.mod | 29 | 12 | True |
| Dark Hive Prince | Animation - Collection Pack.mod | 28 | 22 | True |
| Scorchlander Child | Animation - Collection Pack.mod | 23 | 10 | True |
| Dark Hive Praetorian | Animation - Collection Pack.mod | 19 | 7 | True |
| Astartes (The Lost) | Animation - Collection Pack.mod | 19 | 0 | True |
| Shek Child | Animation - Collection Pack.mod | 18 | 9 | True |
| Primordial Hive Praetorian | Animation - Collection Pack.mod | 13 | 0 | True |
| Astartes (Special Gene Seed) | Animation - Collection Pack.mod | 13 | 0 | True |
| Orc | OrcRaceReview.mod | 13 | 0 | True |
| Greenlander Soul | Animation - Collection Pack.mod | 12 | 4 | True |
| Soul Hive Worker | Animation - Collection Pack.mod | 12 | 4 | True |
| Shek Soul | Animation - Collection Pack.mod | 11 | 4 | True |
| Soul Hive Prince | Animation - Collection Pack.mod | 11 | 4 | True |
| Soul Hive Soldier Drone | Animation - Collection Pack.mod | 11 | 4 | True |
| Skeleton KLR-M MKII | Animation - Collection Pack.mod | 10 | 5 | True |
| Young Shek | Animation - Collection Pack.mod | 10 | 0 | True |
| Crystal Guardian Skeleton | Animation - Collection Pack.mod | 10 | 4 | True |
| Skeleton SL-M MKII | Animation - Collection Pack.mod | 9 | 6 | True |
| Enforcer | Animation - Collection Pack.mod | 9 | 10 | True |
| Skeleton ILA-M MKIII | Animation - Collection Pack.mod | 8 | 1 | True |
| Skeleton KLR-M MKI | Animation - Collection Pack.mod | 8 | 5 | True |
| Skeleton KLR-M MKIII | Animation - Collection Pack.mod | 8 | 3 | True |
| Skeleton ILA-M MKI | Animation - Collection Pack.mod | 8 | 6 | True |
| Skeleton ILA-M MKII | Animation - Collection Pack.mod | 8 | 6 | True |
| Skeleton SL-M MKI | Animation - Collection Pack.mod | 7 | 6 | True |
| Skeleton SL-M MKIII | Animation - Collection Pack.mod | 7 | 2 | True |
| Skeleton ST-M MKI | Animation - Collection Pack.mod | 7 | 5 | True |
| Skeleton ST-M MKII | Animation - Collection Pack.mod | 7 | 5 | True |
| Skeleton ST-M MKIII | Animation - Collection Pack.mod | 7 | 4 | True |
| Crystal Golem Skeleton | Animation - Collection Pack.mod | 7 | 2 | True |
| Primordial Hive Worker Drone | Animation - Collection Pack.mod | 6 | 0 | True |
| Hazards Unit | Animation - Collection Pack.mod | 6 | 6 | True |
| Hazards Unit Oni | Animation - Collection Pack.mod | 6 | 1 | False |
| Thrasher Servile | Animation - Collection Pack.mod | 6 | 1 | False |
| Cyborg - Deadhive Prince | Animation - Collection Pack.mod | 5 | 1 | True |
| Primordial Hive Soldier Drone | Animation - Collection Pack.mod | 5 | 0 | True |
| Skeleton No-Head MkI | Animation - Collection Pack.mod | 5 | 0 | False |

### Модовые расы с живыми персонажами (<5) и без - счётчик

Модовых 1911; живых 1-4: 56; ни одного живого: 1815; без основы (base): 211.

### Дубли рас (race_audit)

- 22 рас-близнецов: K-Unit, Skeleton KX-Unit, Soldierbot (black), Skeleton Log-Head MkII (black), Skeleton Lionhead MkI, Hive Soldier Scent ...
- 187 рас-близнецов: Worker Drone, Skeleton No-Head MkII (black), P4 Unit (black), Screamer MkI (black), Skeleton (black), Skeleton MkII Screamer (black) ...
- 18 рас-близнецов: Northern Hive Queen, Midland Hive Queen, South Hive Queen, Banished Hive Queen, Eastern Hive Queen, Azura Hive Queen ...
- 7 рас-близнецов: Leper, Leper Malenia, Greenlander JRPG, Greenlander Rider Test, Greenlander Crossed, Half Angel Greenlander DEVIANT ...
- 12 рас-близнецов: Buglander, Scorchlander jrpg, Dwarf, Greenscorcher, Emberbeard, Dwarf Earthlander ...
- 2 рас-близнецов: Alpha Fishman olive, Merman Fishman
- 2 рас-близнецов: Skeleton Scout XT-MkIII, Skeleton Scout XT-MkIII (black)
- 2 рас-близнецов: P2 Unit, P2 Unit (black)
- 2 рас-близнецов: Skeleton Lionhead XT-MkIV (black), Skeleton Lionhead XT-MkIV
- 21 рас-близнецов: Mechanical Hive Worker Drone, Mechanical Hive Worker Drone MkII, Beetle Hive Worker Drone C, Beetle Hive Worker Drone, Mechanical Hive Worker Drone, Boneman (Hive Worker) ...
- 19 рас-близнецов: Mechanical Hive Princess, Mechanical Hive Prince, Mechanical Hive Prince MkII, Beetle Hive Prince, Mechanical Hive Princess, Mechanical Hive Prince ...
- 28 рас-близнецов: Mechanical Hive Soldier Drone, Mechanical Hive Soldier Drone MkII, Stag Beetle Hive Soldier Drone, South Hive Soldier Drone drone copy, Mechanical Hive Soldier Drone, Southern Hive Soldier Scout ...
- 44 рас-близнецов: half-qilin, Shuujinko, Viera, Banished From Death, Joestar Family, JOJO 2 ...
- 3 рас-близнецов: Scorchlander Child, Scorchlander Child, Scorchlander (Child)
- 2 рас-близнецов: Shek Child, Shek (Child)
- 95 рас-близнецов: Dummy, High Arakkoa (Blue), High Arakkoa (Dark), Juggernaut, High Arakkoa (Red), High Arakkoa (White) ...
- 2 рас-близнецов: Pearl Hive Soldier Executor, Pearl Hive Soldier Drone
- 2 рас-близнецов: Crimper Skeleton, Crimper Skeleton Thrall
- 3 рас-близнецов: HK-47 Assassin Skeleton, Assassin Droid, Skeleton Deathmaster
- 2 рас-близнецов: Beetle Hive Queen, Visceral Hive Queen
- 5 рас-близнецов: Stag Beetle Deadhive Soldier Drone, God Deadhive Soldier, Demigod Deadhive Soldier, Deadhive Soldier Ronin, Deadhive Soldier Reinforced
- 6 рас-близнецов: Beetle Deadhive Prince, God Deadhive Prince, Demigod Deadhive Prince, Deadhive Prince Ronin, Deadhive Prince Reinforced, Deadhive Horned
- 6 рас-близнецов: Beetle Deadhive Worker Drone C, Beetle Deadhive Worker Drone, God Deadhive Worker, Demigod Deadhive Worker, Deadhive Worker Ronin, Deadhive Worker Reinforced
- 2 рас-близнецов: Handsome guy, Greenlander Force Sensitive
- 11 рас-близнецов: Cage Beast (brown), Cage Beast (brown) Domesticated, Cage Beast (darker), Cage Beast (darker) Domesticated, Cage Beast Domesticated, Cage Beast 02 ...
- 25 рас-близнецов: Black Gorillo (all hair), Black Gorillo (all hair) Domesticated, Black Gorillo (gray, black gorillo alt), Black Gorillo (gray, black gorillo alt) Domesticated, Gorillo (gray), Gorillo (red-brown) ...
- 48 рас-близнецов: Bonecat (black), Bonecat (brown), Bonecat (gray), Bonecat (tan), Bonedog (darkbrown), Bonedog (white) ...
- 25 рас-близнецов: Bull (brown), Bull (grey), Vainian Bull, Bastian Bull, Plainer Bull, Cavalry Vainian ...
- 10 рас-близнецов: Bull (domesticated) (brown), Bull (domesticated) (grey), Bull (domesticated) Black Angus, Bull Black Angus, Bull (domesticated)_02, Bull (domesticated)_03 ...
- 19 рас-близнецов: Swamp Raptor Domesticated (red), Swamp Raptor (black), Swamp Raptor (brown), Swamp Raptor (green), Swamp Raptor (red), Swamp Raptor Domesticated ...
- 19 рас-близнецов: Crab (blue), Crab (grey), Crab (olive-green), False Scorpion (brown), Crab (brown), False Scorpion (black) ...
- 11 рас-близнецов: Garru (brown), Garru (darker), Garru copy, Garru_03, Garru_02, Garru_04 ...
- 3 рас-близнецов: Small Spider Domesticated (black), Small Spider Domesticated (brown), Small Spider Domesticated
- 6 рас-близнецов: Crimper (black-grey), Crimper Salvaged, Crimper Salvaged (black-grey), Ash Crimper, Ash Nano Crimper, Crimper Pet
- 10 рас-близнецов: Goat (black), Goat (brown), Goat_03, Goat_04, Goat_02, Goat Pet ...
- 16 рас-близнецов: River Raptor (black), River Raptor (brown), River Raptor (green), River Raptor (red), River Raptor Domesticated, River Raptor Domesticated (black) ...
- 20 рас-близнецов: Robot Guard Spider (black-grey), Robot Guard Spider (black-grey) Domesticated, Robot Guard Spider (darker), Robot Guard Spider (darker) Domesticated, Robot Guard Spider Domesticated, Robot Spider Worker (black-grey) ...
- 15 рас-близнецов: Land Bat (grey), Land Bat (red-brown), Land Bat Domesticated, Land Bat Domesticated (grey), Land Bat Domesticated (red-brown), Land Bat Alpha ...
- 23 рас-близнецов: Spider (black-gray), Spider (darker brown), Spider Domesticated, Spider Domesticated (black), Spider Domesticated (brown), Small Spider (black) ...
- 11 рас-близнецов: Skimmer (green), Skimmer (green) Domesticated, Skimmer (red), Skimmer (red) Domesticated, Skimmer_02, Skimmer_03 ...
- 2 рас-близнецов: Old Knights Kenji, Old Knights Zagan
- 13 рас-близнецов: Leviathan Domesticated (darker brown), Leviathan Domesticated (black), Leviathan Domesticated, Leviathan, Leviathan, Leviathan ...
- 18 рас-близнецов: Beak Thing (red), Beak Thing (blue-purple), Beak Thing Domesticated (red), Beak Thing Domesticated (blue-purple), Beak Thing Domesticated, Zombified Beak Thing ...
- 3 рас-близнецов: Big-Bones (darker), Big Ash, Big Nano Ash
- 2 рас-близнецов: Walker, Doom Beast
- 4 рас-близнецов: Zombie Hive Worker, Zombie Mutated Brute (Hive Worker), Zombie Hulk (Hive Worker), Zombie Hulk Bogan (Hive Worker)
- 4 рас-близнецов: Zombified Human, Zombified Human Runner, Zombie, Zombie Human
- 4 рас-близнецов: Zombie Brute, Zombie Mutation Theta, Zombie Mutation Eta, Zombie Queen Mutation Delta
- 69 рас-близнецов: Greenlander, LA_WAR GENERAL Greenlander, LA_WAR Greenlander Easykill, LA_WAR DEAD SPAWN (Greenlander), Greenlander (IT-Z), The Struggler ...
- 133 рас-близнецов: Scorchlander, Desert Folk, Imperial Folk, LA_WAR GENERAL Scorchlander, LA_WAR DEAD SPAWN (Scorchlander), LA_WAR Scorchlander Easykill ...
- 28 рас-близнецов: Shek, LA_WAR DEAD SPAWN (Shek), Albino Shek, Shek Bluish, Qunari, Yautja ...
- 10 рас-близнецов: Hive Soldier Drone Eyegore, LA_WAR GENERAL Hive Soldier, LA_WAR DEAD SPAWN (Hive Soldier Drone), LA_WAR Hive Soldier Easykill, Hive Soldier Drone Scent, Hive Soldier Drone MC ...
- 3 рас-близнецов: Shek Rock type, Shek, Ancient Shek
- 4 рас-близнецов: Zombie Runner (Hive Prince), Zombie Hive Prince Mutation Beta, Zombie Hive Prince Runner, Eastern Hive Prince
- 8 рас-близнецов: Zombie Striker, ZOMBIE, ZOMBIE Rotten, Zombie Mutation Zeta, Zombie Mutation Epsilon, Zombie Mutation Gamma ...
- 2 рас-близнецов: Savage, Twi'lek
- 4 рас-близнецов: ZOMBIE Rotten Shek, Zombie Shek Commander, Zombie Shek, Ghoul Expired
- 5 рас-близнецов: B1 Battle Droid copy, B1 Battle Droid, Dark Trooper, Dark Trooper Type 2, Super Battle Droid
- 5 рас-близнецов: Zombie Infected Human (Male), Human Gunslinger, Human Pistoleer, Human Sniper, Bionic
- 4 рас-близнецов: AT-ST, Binary Load Lifter (green), Binary Load Lifter (orange), Mite Raknoid
- 11 рас-близнецов: Droideka Black, Droideka, Droideka Rogue, Droideka Security, Protocol Droid (Gold), Protocol Droid (Silver) ...
- 42 рас-близнецов: Chiss, Chiss Gunslinger, Chiss Pistoleer, Chiss Sniper, Kathunian Gunslinger, Kathunian Pistoleer ...
- 3 рас-близнецов: Hive Prince Gunslinger, Hive Prince Pistoleer, Hive Prince Sniper
- 3 рас-близнецов: Hive Soldier Drone Gunslinger, Hive Soldier Drone Pistoleer, Hive Soldier Drone Sniper
- 3 рас-близнецов: Hive Worker Gunslinger, Hive Worker Pistoleer, Hive Worker Sniper
- 5 рас-близнецов: Mon Calamari, Rodian Gunslinger, Twi'lek Sniper, Wookiee Sniper, Mon Calamari Force Sensitive
- 2 рас-близнецов: Rancor, Spined Rancor
- 3 рас-близнецов: Shek Gunslinger, Shek Pistoleer, Shek Sniper
- 5 рас-близнецов: Rictus, Infested Charger, Zanuka Hunter, Zanuka Proxy, Ratel Drone
- 6 рас-близнецов: Anakin & Obi Wan Race, Greenlander Jedi, Greenlander Jedi Padawan, Human Jedi, Human Jedi Padawan, Jedi Master Race
- 12 рас-близнецов: Chiss Jedi, Chiss Jedi copy, Chiss Jedi Padawan, Kathunian Jedi, Kathunian Jedi Padawan, Mon Calamari Jedi ...
- 3 рас-близнецов: Hive Prince Jedi, Hive Prince Jedi Padawan, Hive Prince Litos
- 2 рас-близнецов: Rattataki Jedi, Rattataki Jedi Padawan
- 2 рас-близнецов: Shek Jedi, Shek Jedi Padawan
- 2 рас-близнецов: Sion Race, Yoda
- 27 рас-близнецов: Trandoshan Jedi, Trandoshan Jedi Padawan, Twi'lek (style 2) Jedi Padawan, Twi'lek Jedi Padawan, Twi'lek Senna Jedi, Wookiee Jedi ...
- 6 рас-близнецов: Twi'lek Jedi, Evil Spirits, Skaven, Gnome, Rattataki, Gnome
- 3 рас-близнецов: LA_WAR GENERAL Shek (Mundo), LA_WAR GENERAL Shek, LA_WAR Shek Easykill
- 2 рас-близнецов: LA_WAR GENERAL Hive Prince, LA_WAR DEAD SPAWN (Hive Prince)
- 6 рас-близнецов: LA_WAR DEAD SPAWN (Hive Worker Drone), Hive Worker MC, Hive Worker Drone Hero, Hive Worker Drone Anti-Hero, Hive Worker Porter, @raid Hive Worker Drone
- 2 рас-близнецов: Grineer Thumper, Grineer Ogma
- 6 рас-близнецов: Infested Runner (humanoid), Infested Ancient (humanoid), AMBULAS, Techrot Runner (humanoid), Techrot Ancient (humanoid), Infested MOA
- 4 рас-близнецов: MOA, MOA MK 0, MOA MK I, MOA MK II
- 2 рас-близнецов: Greenlander Child, Greenlander (Child)
- 13 рас-близнецов: Swamp Turtle, Swamp Turtle, Swamp Turtle, Swamp Turtle Domesticated, Swamp Turtle Domesticated (brown-red), Swamp Turtle Domesticated (purplish-pink) ...
- 30 рас-близнецов: Gippsy, Cervulite, *New Chickens Brown, *New Chickens Brown F, *New Chickens Brown M, *New Chickens Brown Mottled Skin ...
- 2 рас-близнецов: Killer Machine, Death Machine
- 12 рас-близнецов: Succub, Dark Elf, Elf, High Elf, Succubus, Dark Elf ...
- 2 рас-близнецов: Shek Reddish, Shek Greenish
- 2 рас-близнецов: Hive Queen (Clean), South Hive Queen (Clean)
- 2 рас-близнецов: Xik-Nuh, Xik-Nai
- 7 рас-близнецов: Hive Prince MC, Hive Prince Enlightened, Hive Prince Genius, Bodhisattva Hive Prince, Hive Prince Hero, Hive Prince Anti-Hero ...
- 4 рас-близнецов: Skimmer, Skimmer, Skimmer, Alpha Skimmer
- 2 рас-близнецов: Grigori, Grigori II
- 2 рас-близнецов: Android Greenlander, Cybernetic Greenlander
- 2 рас-близнецов: South Hive Worker Drone Hero, South Hive Worker Drone Anti-Hero
- 2 рас-близнецов: South Hive Soldier Drone Hero, South Hive Soldier Drone Anti-Hero
- 2 рас-близнецов: South Hive Prince Hero, South Hive Prince Anti-Hero
- 2 рас-близнецов: Deadhive Worker Hero, Deadhive Worker Anti-Hero
- 2 рас-близнецов: Encroacher, Encroacher Carapace
- 3 рас-близнецов: Greenlander Sith, Greenlander Sith (Palpatine), Greenlander Jedi (Mace Wendu)
- 3 рас-близнецов: South Hive Scout Drone, Hive Scout Drone, Ashen Hive Scout
- 2 рас-близнецов: Carrier, Osprey
- 2 рас-близнецов: Albino Hive Praetorian, Albino Hive Praetorian
- 2 рас-близнецов: Northern Hive Praetorian, Northern Hive Praetorian
- 6 рас-близнецов: Vampiric Radroach, Rampaging Radroach, Molted Radroach, Glowing Radroach, Hardy Radroach, Radroach
- 3 рас-близнецов: Eastern Hive Behemoth, Southern Hive Behemoth, White Hive Behemoth
- 3 рас-близнецов: Northern Hive Behemoth, Northern Hive War King Behemoth, Ghoul Hive Behemoth
- 3 рас-близнецов: Eastern Hive King, Northern Hive King, Southern Hive King
- 3 рас-близнецов: Southern Worker Drone X, Southern Worker Drone Y, Southern Worker Drone Z
- 7 рас-близнецов: Ancient Executioner, Ancient Horror, Mist Ghoul ???, Ancient Strange Ghoul, Mist Executioner, Strange Ghoul ...
- 4 рас-близнецов: Ancient Fiend, Sprinter, Ancient Sprinter, Progenitor of Sprinters
- 3 рас-близнецов: Robot Butcher Spider (Small Hybrid Enforcer), Robot Butcher Spider (Hybrid Enforcer), Robot Butcher Spider
- 3 рас-близнецов: Natural Hive Queen, Southern Natural Queen, Natural Primordial Queen
- 3 рас-близнецов: Miraluka Gunslinger, Miraluka Pistoleer, Miraluka Sniper
- 5 рас-близнецов: Murloc toxic poison, Murloc mystic energy, Murloc forest nature, Murloc blue purple, Murloc

## Города

Первичные (не override) города; тип - число из TOWN.type, kind - из conductor.

| город | владелец | тип/kind | регион | в conductor | лагерь Cleanup | персон. |
|---|---|---|---|---|---|---|
| Ishijuku | Adventurers Guild | 1/holding | Border Zone | да |  | 22 |
| Shirokyo | Adventurers Guild | 2/city | Sinkuun | да |  | 27 |
| Ancient Labs | Ancient Ruins | 4/ |  |  |  | 0 |
| Ancient Tech Lab | Ancient Ruins | 4/ |  |  |  | 1 |
| Ashland Dome Ruin | Ancient Ruins | 4/ |  |  |  | 0 |
| Crumbling Labs | Ancient Ruins | 4/ |  |  |  | 0 |
| Dead Workshop | Ancient Ruins | 4/ |  |  |  | 1 |
| Deadland Workshop | Ancient Ruins | 4/ |  |  |  | 6 |
| Empty Lab | Ancient Ruins | 4/ |  |  |  | 0 |
| Infested Lab | Ancient Ruins | 4/ |  |  |  | 0 |
| Lab Ruin | Ancient Ruins | 4/ |  |  |  | 0 |
| Mountain Ruin | Ancient Ruins | 4/ |  |  |  | 0 |
| Post-Ancient Workshop | Ancient Ruins | 4/ |  |  |  | 0 |
| Post-Ancient Workshop | Ancient Ruins | 4/ |  |  |  | 0 |
| Reprogramming Workshop | Ancient Ruins | 4/ | Deadlands |  |  | 1 |
| Ruined Control Tower | Ancient Ruins | 4/ |  |  |  | 0 |
| Swamped Lab | Ancient Ruins | 4/ |  |  |  | 0 |
| Workshop Complex | Ancient Ruins | 4/ |  |  |  | 0 |
| Spring | Anti-Slavers | 2/city | Stobe's Gamble | да |  | 31 |
| Astartes outpost | Astartes survivors | 2/city | Flats Lagoon | да | хост 2 | 22 |
| Exile Camp | Band of Blades | 0/holding |  | да |  | 1 |
| Bone Band Camp | Band of Bones | 0/holding |  | да |  | 2 |
| Exile Camp | Band of Bones | 9/holding |  | да |  | 4 |
| Exile Camp | Band of Bones | 0/holding |  | да |  | 2 |
| Shek Ruins | Band of Bones | 4/holding | Stenn Desert | да |  | 1 |
| Zander's Hideout | Band of Bones | 9/ |  |  | лагерь->Sukui | 2 |
| Berserker Camp | Berserkers | 0/holding |  | да |  | 2 |
| Berserker Outpost | Berserkers | 9/holding | Purple Sands | да |  | 2 |
| Berserker Village | Berserkers | 1/holding | Spider Plains | да |  | 3 |
| Dave's House | Big Dave's Ninjas | 9/ |  |  |  | 4 |
| Cloud House | Black Desert Ninjas | 1/holding | Arm of Okran | да |  | 2 |
| Gas Grove | Black Desert Ninjas | 9/holding | The Black Desert | да |  | 2 |
| Hidden Camp | Black Desert Ninjas | 9/holding |  | да |  | 2 |
| Black Dog HQ | Black Dog | 9/holding |  | да |  | 2 |
| Black Dragon Camp | Black Dragon Ninjas | 0/holding |  | да |  | 3 |
| Black Dragon Camp | Black Dragon Ninjas | 0/holding |  | да |  | 3 |
| Black Dragon Camp (Phoenix killed) | Black Dragon Ninjas | 0/holding |  | да |  | 3 |
| Tower Of Ninjas | Black Dragon Ninjas | 9/holding | Border Zone | да |  | 5 |
| Gorillo Nest | Black Gorillos | 0/ |  |  |  | 0 |
| Secret Drug Farm | Blackshifters | 1/holding |  | да |  | 0 |
| Blood Butcher Camp | Blood Butcher Tribe | 0/ |  |  |  | 1 |
| Blood Butcher Camp | Blood Butcher Tribe | 0/ |  |  |  | 1 |
| Blood Butcher Village | Blood Butcher Tribe | 3/ |  |  |  | 1 |
| First Village | Blood Butcher Tribe | 3/ |  |  |  | 4 |
| Blood Spider Nest | Blood Spiders | 0/ |  |  |  | 0 |
| Tower of Spiders | Blood Spiders | 9/ |  |  |  | 1 |
| Den | Blood Wolves | 2/city |  | да |  | 2 |
| Blood Bandit Camp | Bloodraiders | 0/holding |  | да |  | 2 |
| Blood Bandit Camp HN | Bloodraiders | 0/holding |  | да |  | 2 |
| Blood Bandit Camp UC | Bloodraiders | 0/holding |  | да |  | 2 |
| Bog Dog Den | Bog Dogs | 0/ |  |  |  | 0 |
| Bone Jackal Den | Bone Jackals | 0/ |  |  |  | 0 |
| Boneyard Wolf Den | Bone Wolves | 0/ |  |  |  | 0 |
| Bounty Hunter Camp | Bounty Hunters | 0/holding |  | да |  | 1 |
| Camp- Cannibal Hunters | Cannibal Hunters | 0/holding |  | да |  | 2 |
| The Bastion | Cannibal Hunters | 6/city | Sinkuun | да |  | 6 |
| Abandoned altar | Cannibals | 1/ |  |  |  | 3 |
| Adidan's Tower | Cannibals | 9/ |  |  | лагерь->Smugglers Bar | 1 |
| Butcher's Lair | Cannibals | 3/ | Cannibal Plains |  |  | 3 |
| Cannibal Infestation | Cannibals | 0/ |  |  |  | 2 |
| Cannibal Village | Cannibals | 3/ |  |  |  | 7 |
| Cannibal Village 2 | Cannibals | 1/ |  |  |  | 6 |
| Khorne's corrupted cannibalistic lair | Cannibals | 0/ |  |  |  | 3 |
| Khorne's corrupted giant cannibalistic nest | Cannibals | 0/ |  |  |  | 2 |
| Khorne's corrupted paladin cannibalistic lair | Cannibals | 0/ |  |  |  | 3 |
| Lost Tower | Cannibals | 4/ |  |  |  | 3 |
| Painted Tribe Camp | Cannibals | 0/ |  |  |  | 5 |
| Shaman's Hideout | Cannibals | 3/ | Darkfinger |  |  | 6 |
| Wendigo's Hut | Cannibals | 9/ |  |  | лагерь->Rot | 1 |
| 屠夫的进食点 | Cannibals | 4/ |  |  |  | 2 |
| Carrion Crawler Nest | Carrion Crawlers | 0/ |  |  |  | 0 |
| Cannibal Capital | Charred Skull Tribe | 2/ | Cannibal Plains |  |  | 5 |
| Charred Skull Camp | Charred Skull Tribe | 0/ |  |  |  | 2 |
| Charred Skull Camp | Charred Skull Tribe | 0/ |  |  |  | 2 |
| Charred Skull Village | Charred Skull Tribe | 3/ |  |  |  | 6 |
| Chimpanzee Nest | Chimpanzees | 0/ |  |  |  | 0 |
| Crab Sanctum | Crab Raiders | 9/ |  |  | лагерь->Flats Lagoon | 2 |
| Crab Town | Crab Raiders | 2/city | The Pits East | да |  | 34 |
| Crab Village | Crab Raiders | 3/holding | Stobe's Garden | да |  | 7 |
| Dusty's Domain | Crab Raiders | 1/holding | The Pits East | да |  | 1 |
| Crab Nest | Crabs | 0/ |  |  |  | 0 |
| Crab Nest pit | Crabs | 0/ |  |  |  | 0 |
| Dwarf Crab nest | Crabs | 0/ |  |  |  | 0 |
| Lost Town | Crabs | 4/ |  |  |  | 0 |
| Seaweed Crab Nest | Crabs | 0/ |  |  |  | 0 |
| Spider Crab Nest | Crabs | 0/ |  |  |  | 0 |
| Crop Lice Nest | Crop Lice | 0/ |  |  |  | 0 |
| Strange Crystal 01 | Crystal Enemys | 9/ |  |  |  | 0 |
| Strange Crystal 02 | Crystal Enemys | 9/ |  |  |  | 1 |
| Strange Crystal 03 | Crystal Enemys | 9/ |  |  |  | 1 |
| Strange Crystal 04 | Crystal Enemys | 9/ |  |  |  | 1 |
| Strange Crystal 05 | Crystal Enemys | 9/ |  |  |  | 1 |
| Strange Crystal 06 | Crystal Enemys | 9/ |  |  |  | 0 |
| Crystal Deathyard | Crystal Hive | 0/ |  |  |  | 3 |
| Crystal ancient machine | Crystal Hive | 0/ |  |  |  | 0 |
| Crystal City | Crystal Relics | 2/city | The Crater | да |  | 7 |
| Fluorite | Cult of Fluorite | 2/city | Purple Sands | да |  | 3 |
| Goblin Camp | Cult of Goblin | 0/holding |  | да |  | 2 |
| Goblin's Hive | Cult of Goblin | 3/holding |  | да |  | 3 |
| The Eternal Laboratory | Cyborgs | 2/city |  | да |  | 0 |
| Strange Place | Dark Hive | 9/holding | The Iron Trail | да |  | 10 |
| Dark Reaver Camp | Dark Reavers | 0/holding |  | да |  | 2 |
| Dark Reaver Camp (BZ) | Dark Reavers | 0/holding |  | да |  | 2 |
| Dark Reaver Scout Camp | Dark Reavers | 0/holding |  | да |  | 2 |
| Dark Reaver Tower | Dark Reavers | 9/holding |  | да |  | 6 |
| Supply Warehouse | Dark Reavers | 9/holding | Vain | да |  | 4 |
| Fishing Village | Deadcat | 3/holding | Northern Coast | да |  | 32 |
| Gatherer Village | Deadcat | 3/holding | Dreg | да |  | 5 |
| Ghost Village | Deadcat | 3/holding | Northern Coast | да |  | 0 |
| Old Village | Deadcat | 4/holding |  | да |  | 0 |
| Refugee Camp | Deadcat | 0/holding |  | да |  | 2 |
| Death Watch landing point | Death Watch | 4/ |  |  |  | 3 |
| Dire Hyena Den | Dire Hyaenidae | 0/ |  |  |  | 0 |
| Houndmaster's Den | Drifters | 9/ |  |  | лагерь->Outlaws' Refuge | 1 |
| Taunt's Hideout | Drifters | 9/ |  |  | лагерь->Stack | 1 |
| Gryfs Drug Farm | Drug Peddlers | 3/holding | Vain | да |  | 43 |
| Dune Dog Den | Dune Dogs | 0/ |  |  |  | 0 |
| Dust Bandit Camp | Dust Bandits | 0/holding |  | да |  | 4 |
| Dust Bandit Camp | Dust Bandits | 0/holding |  | да |  | 3 |
| Dust Bandit Camp (HN) | Dust Bandits | 0/holding |  | да |  | 4 |
| Dust King Tower | Dust Bandits | 9/holding |  | да |  | 4 |
| Dust Hound Den | Dust Hounds | 0/ |  |  |  | 0 |
| Dust Lord Camp | Dust Lords | 0/holding |  | да |  | 2 |
| Dust Raider Camp | Dust Raiders | 0/holding |  | да |  | 2 |
| Dust Reaper Camp | Dust Reapers | 0/holding |  | да |  | 2 |
| Hideout of Wanted | Empire Criminals | 6/city | Howler Maze | да |  | 2 |
| Empire Village | Empire Peasants | 1/holding |  | да |  | 0 |
| Old Village | Empire Peasants | 4/holding |  | да |  | 1 |
| Vagrant Camp | Empire Peasants | 0/holding |  | да |  | 9 |
| Fell Hyena Den | Fell Hyaenidae | 0/ |  |  |  | 0 |
| Fiddler Crab Nest | Fiddler Crabs | 0/ |  |  |  | 0 |
| Airnagard | Final Enforcers | 6/city | Leviathan Coast | да |  | 5 |
| RETIRED Fish Isle (Annexed with Crab) | Fish Isle | 3/ |  |  |  | 0 |
| Fish Isle | Fishmen | 2/ |  |  |  | 5 |
| Gurgler Nest | Fishmen | 0/ |  |  |  | 4 |
| Island Lab | Fishmen | 4/ |  |  |  | 3 |
| Empty Ruins | Floodland Ruins | 4/ |  |  |  | 2 |
| Leaning Tower | Floodland Ruins | 4/ |  |  |  | 0 |
| Ruined Tower | Floodland Ruins | 4/ |  |  |  | 0 |
| Spider Workshop | Floodlands Skeletons | 9/ |  |  | лагерь->World's End | 2 |
| Flotsam Camp | Flotsam Ninjas | 0/holding |  | да |  | 4 |
| Flotsam Raid Camp | Flotsam Ninjas | 0/holding |  | да |  | 4 |
| Flotsam Safehouse | Flotsam Ninjas | 9/holding | Rebirth | да |  | 2 |
| Flotsam Village | Flotsam Ninjas | 3/holding | Hidden Forest | да |  | 12 |
| Flotsam War Camp | Flotsam Ninjas | 0/holding |  | да |  | 4 |
| Scout Post | Flotsam Ninjas | 9/holding | Cannibal Plains | да |  | 6 |
| Fog Fiend Hollow | Fog Fiends | 0/ |  |  |  | 0 |
| Fog Fiend Migratory Hollow | Fog Fiends | 0/ |  |  |  | 0 |
| Deadhive Overrun | Fogmen | 4/ | Okran's Gulf |  |  | 3 |
| Fog Deathyard | Fogmen | 0/ |  |  |  | 3 |
| Fog Deathyard Invasion | Fogmen | 0/ |  |  |  | 3 |
| Fogman Nest Invasion | Fogmen | 0/ |  |  |  | 3 |
| The Fog Kings Throne | Fogmen | 9/ | Fog Islands |  |  | 4 |
| Tower of Fog | Fogmen | 9/ | Vain |  |  | 2 |
| Gnawed Bone Camp | Gnawed Bone Tribe | 0/ |  |  |  | 1 |
| Gnawed Bone Camp | Gnawed Bone Tribe | 0/ |  |  |  | 1 |
| Gnawed Bone Village | Gnawed Bone Tribe | 3/ |  |  |  | 1 |
| Suspicious Lab | Gnawed Bone Tribe | 4/ | Floodlands |  |  | 5 |
| Golden Wolf Den | Golden Wolves | 0/ |  |  |  | 0 |
| Straw Bandit Camp | Grass Pirates | 0/holding |  | да |  | 2 |
| Grayflayer Village | Grayflayers | 3/holding | The Swamp | да |  | 14 |
| Smugglers Bar | Grayflayers | 9/holding | Shem | да | хост 1 | 46 |
| Great Maned Wolf Den | Great Maned Wolves | 0/ |  |  |  | 0 |
| Gork's Throne | Greenskins | 6/city | Skinner's Roam | да |  | 19 |
| Devil's Hideout | Grey Knight | 4/ |  |  |  | 1 |
| Silent Camp | Grey Knight | 4/ |  |  | лагерь->Astartes outpost | 1 |
| Grievewraith nest | Grievewraiths | 0/ |  |  |  | 0 |
| Infested Ruin | Grievewraiths | 4/ |  |  |  | 0 |
| Grievous Hyena Den | Grievous Hyaenidae | 0/ |  |  |  | 0 |
| Hope | Guild of Surgeons | 2/city | Stenn Desert | да |  | 28 |
| Leviathons Watch | Guild of Surgeons | 1/holding | Leviathan Coast | да |  | 11 |
| Redmans Tower | Guild of Surgeons | 1/holding | Bonefields | да |  | 7 |
| The Apothecary | Guild of Surgeons | 1/holding | Bast | да |  | 11 |
| Dreg Gunworks | Gunsmiths | 2/ |  |  | лагерь->Mongrel | 2 |
| Iron Hearth | Gunsmiths | 6/city | Sinkuun | да |  | 5 |
| Nest of Beak Things | Gutters | 0/ |  |  |  | 0 |
| Nest of Beak Things | Gutters | 0/ |  |  |  | 0 |
| Nest of Beak Things | Gutters | 0/ |  |  |  | 0 |
| Nest of Beak Things | Gutters | 0/ |  |  |  | 0 |
| Nest of Beak Things | Gutters | 0/ |  |  |  | 0 |
| Nest of Bush Things | Gutters | 0/ |  |  |  | 0 |
| Nest of Great Beak Things | Gutters | 0/ |  |  |  | 0 |
| Nest of Iridescent Beak Things | Gutters | 0/ |  |  |  | 0 |
| Strange Camp | Gutters | 9/ |  |  |  | 1 |
| Broadcast Camp | Hatred of intelligence | 4/holding |  | да |  | 5 |
| Chaotic and corrupted skinner's lair | Hatred of intelligence | 0/holding |  | да |  | 7 |
| Cage Beast | Herbivore | 0/ |  |  |  | 0 |
| Dragon's Den | Holy Nation Outlaws | 9/holding |  | да |  | 1 |
| Holy Outlaw Camp | Holy Nation Outlaws | 0/holding |  | да |  | 3 |
| Outlaws' Refuge | Holy Nation Outlaws | 3/holding | Sinkuun | да | хост 1 | 3 |
| The Hub | Holy Nation Outlaws | 2/city | Border Zone | да | хост 2 | 110 |
| Rot | Hounds | 3/holding | The Swamp | да | хост 1 | 12 |
| New Kralia | Kral's Chosen | 1/holding |  | да |  | 2 |
| Renegade Camp | Kral's Chosen | 0/holding |  | да |  | 1 |
| Land Bat Nest | Land Bat | 0/ |  |  |  | 0 |
| Hilt | Levi Ronin | 2/city | Leviathan Coast | да |  | 4 |
| Ronin Outpost | Levi Ronin | 1/holding |  | да |  | 5 |
| Swordsman's Hideout | Lone Berserker | 9/holding |  | да |  | 1 |
| The Collector's Nest | Lost Chaos Space Marines | 4/holding |  | да |  | 2 |
| Ruined Tower of Trial | Lost Oni | 1/holding |  | да |  | 1 |
| Errol's Workshop | Machinists | 4/ |  |  | лагерь->World's End | 2 |
| Man-eating Shark Outpost | Man-eating shark | 1/holding |  | да |  | 2 |
| Shark Hunt | Man-eating shark | 4/holding |  | да |  | 3 |
| Manhunter Base | Manhunters | 1/holding | The Hook | да |  | 3 |
| Mercenary Camp | Mercenary Guild | 0/holding |  | да |  | 4 |
| Mercenary base | Mercenary Guild | 1/holding |  | да |  | 0 |
| Human Research Institute | Midnight Lord | 1/holding |  | да |  | 8 |
| Mist Boneyard | Mist Creatures | 0/ |  |  |  | 3 |
| Tower of Mist | Mist Creatures | 4/ |  |  |  | 3 |
| Camp- Fog Hunters | Mongrel | 0/holding |  | да |  | 2 |
| Mongrel | Mongrel | 2/city | Fog Islands | да | хост 1 | 11 |
| Moss Crab Nest | Moss Crabs | 0/ |  |  |  | 0 |
| Mountain Wolf Den | Mountain Dogs | 0/ |  |  |  | 0 |
| Your Outpost | Nameless | 1/ |  |  |  | 0 |
| Fallen Tower | No Faction | 4/ |  |  |  | 0 |
| Nowhere | No Faction | 10/ |  |  |  | 0 |
| Goat Herder's Camp | Nomads | 0/holding |  | да |  | 1 |
| Goat Herder's Camp | Nomads | 0/holding |  | да |  | 1 |
| Nomads | Nomads | 0/holding |  | да |  | 2 |
| Settled Nomad Village | Nomads | 3/holding | Dreg | да |  | 5 |
| Settled Nomads | Nomads | 3/holding | Shem | да |  | 4 |
| Reapers Due | Old Machines | 1/ | Floodlands |  |  | 4 |
| Spider Factory | Old Machines | 4/ |  |  |  | 3 |
| Perdition | Oni | 7/city |  | да |  | 2 |
| Tower of Trial | Oni | 1/holding | Venge | да |  | 1 |
| Orion Crocuta Den | Orion Crocuta | 0/ |  |  |  | 0 |
| Meep Camp BD | Outlaw | 0/holding |  | да |  | 0 |
| Meep's Training Camp | Outlaw | 9/holding |  | да |  | 3 |
| Tower of the Wizard | Outlaw | 9/holding |  | да |  | 1 |
| Watcher's Camp | Outlaw | 9/ |  |  | лагерь->The Hub | 3 |
| Cult Village | Preacher Cult | 3/holding | Stormgap Coast | да | хост 1 | 6 |
| River Raptor Nest | Raptors | 0/ |  |  |  | 0 |
| Ark | Reavers | 1/holding | Stobe's Garden | да |  | 5 |
| Reaver Camp | Reavers | 1/holding |  | да |  | 4 |
| Reaver Camp | Reavers | 0/holding |  | да |  | 3 |
| Reaver Camp | Reavers | 0/holding |  | да |  | 3 |
| Reaver Camp | Reavers | 0/holding |  | да |  | 3 |
| Fort Simion | Rebel Farmers | 1/holding | Sinkuun | да |  | 6 |
| Raider Camp | Rebel Farmers | 0/holding |  | да |  | 6 |
| Red Sabre Camp | Red Sabres | 0/holding |  | да |  | 1 |
| Swamp Hideout | Red Sabres | 9/holding | The Swamp | да |  | 2 |
| Skel-Ape Nest | Robotic Wildlife | 0/ |  |  |  | 0 |
| Rust HQ | Rusty Raiders | 2/city | The Black Desert | да |  | 23 |
| Poacher Camp | Sailback Poachers | 0/holding |  | да |  | 3 |
| Cactus Den | Sand ninjas | 9/holding |  | да |  | 5 |
| Savannah Hound Den | Savannah Hounds | 0/ |  |  |  | 0 |
| Old Control Tower | Scavengers | 4/holding | Venge | да |  | 5 |
| Archive Town | Second Empire | 4/ |  |  |  | 0 |
| Armoury Ruin | Second Empire | 4/ |  |  |  | 0 |
| Ashland Dome I | Second Empire | 4/ | Ashlands |  |  | 2 |
| Ashland Dome II | Second Empire | 4/ | Ashlands |  |  | 2 |
| Ashland Dome III | Second Empire | 4/ |  |  |  | 2 |
| Ashland Dome IV | Second Empire | 4/ | Ashlands |  |  | 2 |
| Ashland Dome V | Second Empire | 4/ | Ashlands |  |  | 2 |
| Ashland Dome VI | Second Empire | 4/ | Ashlands |  |  | 3 |
| Ashland Outpost | Second Empire | 4/ |  |  |  | 1 |
| Dead Fishing Village | Second Empire | 3/ |  |  |  | 1 |
| Empty Ruin | Second Empire | 9/ |  |  |  | 0 |
| Legendary Katana Statue | Second Empire | 4/ |  |  |  | 0 |
| Library Ruins | Second Empire | 4/ |  |  |  | 0 |
| Looted Ruins | Second Empire | 4/ |  |  |  | 0 |
| Lost Armour Store | Second Empire | 4/ |  |  |  | 0 |
| Lost Armoury | Second Empire | 4/ |  |  |  | 0 |
| Lost Library | Second Empire | 4/ |  |  |  | 0 |
| Lost Library Outpost | Second Empire | 4/ |  |  |  | 0 |
| Mining Factory | Second Empire | 4/ | Leviathan Coast |  |  | 1 |
| Old Empire Supply Outpost | Second Empire | 4/ |  |  |  | 0 |
| Old Empire Watchtower | Second Empire | 4/ |  |  |  | 0 |
| Police Barracks | Second Empire | 4/ | The Pits |  |  | 1 |
| Skeleton Ronin's Tower | Second Empire | 9/ |  |  |  | 2 |
| The Forgotten Throne | Second Empire | 4/ |  |  |  | 1 |
| Cat-Lon's Exile | Second Empire Exile | 2/ |  |  |  | 2 |
| Admag | Shek Kingdom | 2/city | Stenn Desert | да |  | 27 |
| Last Stand | Shek Kingdom | 6/city | Spider Plains | да |  | 28 |
| Old Frontlines | Shek Kingdom | 4/holding |  | да |  | 0 |
| Shek Ranch | Shek Kingdom | 3/holding |  | да |  | 3 |
| Squin | Shek Kingdom | 2/city | Border Zone | да |  | 22 |
| The Great Fortress | Shek Kingdom | 6/city | Stenn Desert | да |  | 5 |
| Sukui | Shem Residents | 2/city | Shem | да | хост 1 | 23 |
| Rent Shinobi Post | Shinobi Thieves | 1/holding |  | да |  | 12 |
| Silver Wolf Den | Silver Wolves | 0/ |  |  |  | 0 |
| Iron HQ | Skeleton Bandits | 1/holding | The Crags | да |  | 2 |
| Sniper Tower | Skeleton Legion | 9/ |  |  |  | 1 |
| Sultan Outpost | Skeleton Sultans | 1/holding | The Black Desert | да |  | 4 |
| Black Desert City | Skeletons | 2/city | Deadlands | да |  | 22 |
| Burn's Tower | Skeletons | 4/holding |  | да |  | 1 |
| Drowned Ruins | Skeletons | 4/holding |  | да |  | 2 |
| Scraphouse | Skeletons | 9/holding | Deadlands | да |  | 3 |
| Skimmer Brood Nursery | Skimmers | 0/ |  |  |  | 0 |
| Skimmer Nest | Skimmers | 0/ |  |  |  | 0 |
| Skimmer Nursery | Skimmers | 0/ |  |  |  | 0 |
| Small Skimmer Nest | Skimmers | 0/ |  |  |  | 0 |
| Verdant Skimmer Nest Small | Skimmers | 0/ |  |  |  | 0 |
| Verdant Skimmer Nursery | Skimmers | 0/ |  |  |  | 0 |
| Horrible Ruin | Skin Bandits | 4/holding |  | да |  | 1 |
| Skinhouse | Skin Bandits | 1/holding | Sonorous Dark | да |  | 1 |
| Skinhouse HQ | Skin Bandits | 1/holding | Sonorous Dark | да |  | 3 |
| Skull Collectors | Skull Collectors | 0/holding |  | да |  | 1 |
| Skull Collectors Village | Skull Collectors | 3/holding |  | да |  | 3 |
| Eyesocket | Slave Traders | 5/city | Stormgap Coast | да |  | 25 |
| Port North | Slave Traders | 5/city |  | да |  | 15 |
| Port South | Slave Traders | 5/city | The Great Desert | да |  | 15 |
| Slave Farm | Slave Traders | 5/city | Heng | да |  | 10 |
| Slave Farm South | Slave Traders | 5/city | The Hook | да |  | 11 |
| Slave Markets | Slave Traders | 1/holding | South Wetlands | да |  | 23 |
| Slaver Camp | Slave Traders | 0/holding |  | да |  | 4 |
| Slaver Camp | Slave Traders | 0/holding |  | да |  | 4 |
| South Stone Camp | Slave Traders | 5/city | Heng | да |  | 12 |
| Stone Camp | Slave Traders | 5/city | The Great Desert | да |  | 12 |
| Slough Hyena Den | Slough Hyaenidae | 0/ |  |  |  | 0 |
| Crystal Spawn purple | Soulbodies | 0/ |  |  |  | 0 |
| Crystal Spawn red | Soulbodies | 0/ |  |  |  | 0 |
| Hiver-Claimed Armoury | Southern Hive | 4/holding | Greyshelf | да |  | 7 |
| Southern Hive | Southern Hive | 2/city | Royal Valley | да |  | 9 |
| Southern Hive Village | Southern Hive | 3/holding | Greyshelf | да |  | 5 |
| Tomb of the Dead | Space Necromancer - Sora Dynasty | 6/city | Sonorous Dark | да |  | 7 |
| Skin Spider Nest | Spiders | 0/ |  |  |  | 0 |
| Spider Den | Spiders | 9/ |  |  | лагерь->Mud Town | 1 |
| Spider Nest | Spiders | 0/ |  |  |  | 0 |
| Throne of the Bugmaster | Spiders | 9/ |  |  |  | 1 |
| Starving Bandit Camp | Starving Bandits | 0/holding |  | да |  | 2 |
| Noatun | Steel Raiders | 1/holding | Dreg | да |  | 9 |
| Stone Rat Village | Stone Rats | 3/holding | The Swamp | да |  | 11 |
| Raptor Island | Swamp Creatures | 9/ |  |  |  | 0 |
| Red Nest | Swamp Creatures | 0/ |  |  |  | 0 |
| Swamp Raptor Nest | Swamp Creatures | 0/ |  |  |  | 0 |
| nest- megaraptor | Swamp Creatures | 0/ |  |  |  | 0 |
| Swamp Ninja Ruins | Swamp Ninjas | 9/holding | The Swamp | да |  | 4 |
| Wetlands Hideout | Swamp Ninjas | 9/holding | South Wetlands | да |  | 4 |
| Nest of Beak Turtles | Swamp Things | 0/ |  |  |  | 0 |
| Mud Town | Swampers | 3/holding | The Swamp | да | хост 1 | 23 |
| Shark | Swampers | 2/city | The Swamp | да |  | 65 |
| Swamp Village | Swampers | 3/holding | The Swamp | да |  | 36 |
| Barcrest | Sysus Bandits | 1/holding | The Outlands | да |  | 7 |
| Black Scratch | Tech Hunters | 2/city | The Outlands | да |  | 74 |
| Expedition 4 | Tech Hunters | 4/holding |  | да |  | 1 |
| Expedition 5 | Tech Hunters | 4/holding |  | да |  | 0 |
| Flats Lagoon | Tech Hunters | 2/city | Flats Lagoon | да | хост 1 | 113 |
| Mourn | Tech Hunters | 2/city | Bonefields | да |  | 58 |
| Rogue | Tech Hunters | 2/city |  | да |  | 16 |
| Waystation | Tech Hunters | 1/holding | Stenn Desert | да |  | 68 |
| Waystation Four | Tech Hunters | 1/holding |  | да |  | 50 |
| Waystation Ruins | Tech Hunters | 1/holding | Stobe's Garden | да |  | 3 |
| World's End | Tech Hunters | 2/city | Arm of Okran | да | хост 2 | 105 |
| World's Ruin | Tech Hunters | 1/holding | Arm of Okran | да |  | 31 |
| The Old Prison | The Gorrillo Bandits | 4/holding |  | да |  | 2 |
| Old Wreckage | The Hollow Feast | 1/holding |  | да |  | 4 |
| Bad Teeth | The Holy Nation | 2/city | Okran's Pride | да |  | 11 |
| Bell Sow | The Holy Nation | 3/holding | Okran's Pride | да |  | 8 |
| Blister Hill | The Holy Nation | 2/city | Okran's Pride | да | хост 1 | 17 |
| Busted Wall | The Holy Nation | 5/city | Skinner's Roam | да | хост 1 | 3 |
| Cork  | The Holy Nation | 3/holding | Okran's Pride | да |  | 12 |
| Deadhive Overrun (override) HN | The Holy Nation | 4/holding |  | да |  | 8 |
| Holy Farm | The Holy Nation | 3/holding | Okran's Valley | да |  | 5 |
| Holy Farm | The Holy Nation | 4/holding | Okran's Valley | да |  | 1 |
| Holy Military Base | The Holy Nation | 6/city | Okran's Gulf | да |  | 13 |
| Holy Mine Ruin | The Holy Nation | 4/holding |  | да |  | 10 |
| Holy Mines | The Holy Nation | 3/holding | Skinner's Roam | да |  | 3 |
| Holy Training Camp | The Holy Nation | 0/holding |  | да |  | 4 |
| Holy War Camp (flotsam) | The Holy Nation | 0/holding |  | да |  | 4 |
| Meridin | The Holy Nation | 3/holding | Okran's Valley | да |  | 19 |
| Narko's Trap | The Holy Nation | 6/city |  | да |  | 9 |
| Okran's Fist | The Holy Nation | 6/city | Arm of Okran | да |  | 14 |
| Okran's Shield | The Holy Nation | 6/city |  | да |  | 12 |
| Pale Hill | The Holy Nation | 5/city | Okran's Gulf | да |  | 3 |
| Pilgrims Pass | The Holy Nation | 3/holding | Okran's Valley | да |  | 19 |
| Rebel Base (override) holy nation | The Holy Nation | 9/holding |  | да |  | 2 |
| Rebirth | The Holy Nation | 5/city | Rebirth | да |  | 17 |
| Redin | The Holy Nation | 3/holding | Okran's Pride | да |  | 7 |
| Roadside Bakery | The Holy Nation | 3/ |  |  | лагерь->Blister Hill | 6 |
| Ruined Farm | The Holy Nation | 9/holding |  | да |  | 0 |
| Ruined Holy Outpost | The Holy Nation | 4/holding | Border Zone | да |  | 0 |
| Ruined Mine  | The Holy Nation | 4/holding |  | да |  | 0 |
| Ruined Mine  | The Holy Nation | 4/holding |  | да |  | 0 |
| Salvation | The Holy Nation | 5/city | Skinner's Roam | да |  | 3 |
| Sinners Gulch | The Holy Nation | 5/city | Okran's Gulf | да |  | 3 |
| Stack | The Holy Nation | 2/city | Okran's Gulf | да | хост 1 | 13 |
| Taril | The Holy Nation | 3/holding | Okran's Pride | да |  | 19 |
| Tiny Settlement | The Holy Nation | 4/holding | Border Zone | да |  | 3 |
| Torn | The Holy Nation | 5/city | Skinner's Roam | да |  | 3 |
| Tyr's Outpost | The Holy Nation | 1/holding | Okran's Gulf | да |  | 3 |
| Watchtower | The Holy Nation | 9/holding |  | да |  | 3 |
| Black Sanctuary Camp | The Lost Black Sanctuary | 1/ |  |  |  | 8 |
| Skyscrap | The Syndicate | 1/holding | Border Zone | да |  | 13 |
| Drakken | The Wolven Order | 3/holding |  | да |  | 0 |
| Tower of Abuse | Thrall Masters | 4/ | Venge |  |  | 6 |
| Rebel Base | Trade Ninjas | 9/holding | Border Zone | да |  | 8 |
| Raided Caravan | Traders Guild | 0/holding |  | да |  | 0 |
| Resort Island | Traders Guild | 2/city | South Wetlands | да |  | 30 |
| Trader's Edge | Traders Guild | 1/holding | Heng | да |  | 27 |
| Dangerous Trap | Traitors | 4/ |  |  |  | 1 |
| Bone Fiend Hollow | Tyrants | 0/ |  |  |  | 0 |
| Bone Fiend Large | Tyrants | 0/ |  |  |  | 0 |
| Bone Fiend Small nest | Tyrants | 0/ |  |  |  | 0 |
| Large Bone Fiend Hollow | Tyrants | 0/ |  |  |  | 0 |
| Abandoned Town | United Cities | 4/holding |  | да |  | 2 |
| Bark | United Cities | 2/city | The Great Desert | да |  | 77 |
| Bast | United Cities | 4/holding | Bast | да |  | 21 |
| Brink | United Cities | 2/city | Stormgap Coast | да |  | 25 |
| Catun | United Cities | 2/city | Bonefields | да |  | 52 |
| Clownsteady | United Cities | 2/city | The Hook | да |  | 88 |
| Cuckold Grave | United Cities | 9/holding |  | да |  | 0 |
| Drifter's Last | United Cities | 2/city | The Hook | да |  | 47 |
| Drin | United Cities | 4/holding | Bast | да |  | 14 |
| Empire Mass Grave | United Cities | 9/holding |  | да |  | 0 |
| Endin | United Cities | 4/holding | Bast | да |  | 9 |
| Farm Ruin | United Cities | 4/holding |  | да |  | 0 |
| Farming Village | United Cities | 3/holding | The Outlands | да |  | 33 |
| Fishing Village | United Cities | 3/holding | The Outlands | да |  | 35 |
| Free Settlement | United Cities | 4/holding | Stobe's Gamble | да |  | 0 |
| Guard Outpost | United Cities | 9/holding |  | да |  | 5 |
| Hamlet | United Cities | 9/holding | Bast | да |  | 0 |
| Heft | United Cities | 2/city | The Great Desert | да |  | 49 |
| Heng | United Cities | 2/city | Heng | да |  | 119 |
| Military Outpost | United Cities | 6/city |  | да |  | 0 |
| Port South | United Cities | 2/city |  | да |  | 0 |
| Seaside Restaurant | United Cities | 1/holding | The Hook | да |  | 8 |
| Sho-Battai | United Cities | 2/city | The Great Desert | да |  | 42 |
| Ska | United Cities | 2/city |  | да |  | 1 |
| Stoat | United Cities | 2/city | The Great Desert | да |  | 36 |
| Tengu's Vault | United Cities | 7/city |  | да |  | 7 |
| Fort Mirage | United Heroes League | 1/holding |  | да |  | 2 |
| Vagrant Bandit Camp | Vagrants | 0/ |  |  |  | 1 |
| Verglas Crocuta Den | Verglas Crocuta | 0/ |  |  |  | 0 |
| Acid Wasp Nest | Wasps | 0/ |  |  |  | 0 |
| Waste Fiend Hollow | Waste Fiends | 0/ |  |  |  | 0 |
| Distant Hive Village | Western Hive | 3/holding | Sinkuun | да |  | 5 |
| Hive Village | Western Hive | 3/holding | Dreg | да |  | 5 |
| Western Hive | Western Hive | 3/holding | Vain | да |  | 9 |
| White Eyebrow Camp | White Eyebrow Clan | 0/holding |  | да |  | 2 |
| White Eyebrow Camp | White Eyebrow Clan | 0/holding |  | да |  | 2 |
| White Eyebrow Tower | White Eyebrow Clan | 9/holding |  | да |  | 4 |
| White Eyebrow Tower | White Eyebrow Clan | 9/holding | The Swamp | да |  | 2 |
| The White Wolf's Respite | White Wolves | 9/ |  |  | лагерь->Busted Wall | 1 |
| White Wolf Den | White Wolves | 0/ |  |  |  | 0 |
| Bone Fiend Hollow (defunct and broken) | Wildlife | 0/ |  |  |  | 0 |
| Breeder's Den | Wildlife | 9/ |  |  |  | 0 |
| Foulhound Den | Wildlife | 0/ |  |  |  | 0 |
| Large Bone Fiend Hollow (defunct and broken) | Wildlife | 0/ |  |  |  | 0 |
| Nest of Jarraffes | Wildlife | 0/ |  |  |  | 0 |
| Sailback Graveyard | Wildlife | 0/ |  |  |  | 0 |
| Sea Wolf Den | Wildlife | 0/ |  |  |  | 0 |
| Tower Of Goats | Wildlife | 9/ | Sinkuun |  |  | 1 |
| Western tyrant nest Goliath | Wildlife | 0/ |  |  |  | 0 |
| Winged Beak Ogre Lair | Wildlife | 9/ |  |  |  | 0 |
| eastern tyrant nest Goliath | Wildlife | 0/ |  |  |  | 0 |
| Witches' Huts | Witches | 9/ |  |  | лагерь->Cult Village | 3 |
| Bloodhound Den | Wolves | 0/ |  |  |  | 0 |
| The Black Hound's Den | Wolves | 4/ |  |  |  | 0 |
| Wolf Den | Wolves | 0/ |  |  |  | 0 |
| Blood Skull Altar | World Devourer War Gang | 1/holding |  | да |  | 16 |
| Imperial Guard's Hidden Residence | hermit | 4/ |  |  |  | 1 |
| "phantom" | - | 4/ |  |  |  | 1 |
| -nest housecamp | - | 10/ |  |  |  | 0 |
| -nest housecamp fishman annex | - | 10/ |  |  |  | 0 |
| -nest housecamp reapers | - | 10/ |  |  |  | 0 |
| Abandoned Farm House | - | 4/ |  |  |  | 0 |
| Backpack "Research Institute" | - | 4/holding |  | да |  | 1 |
| Bad Teeth (override) half destroyed malnourished | - | 1/ |  |  |  | 0 |
| Bad Teeth (override) malnourished | - | 1/ |  |  |  | 0 |
| Bad Teeth (override) takeover Bele'coz | - | 1/ |  |  |  | 0 |
| Bad Teeth (override) takeover UC destroyed | - | 1/ |  |  |  | 0 |
| Bast (override) EP | - | 1/ |  |  |  | 0 |
| Bast (override) HN | - | 1/ |  |  |  | 0 |
| Bast (override) strengthened | - | 1/ |  |  |  | 0 |
| Black Scratch (override) AS | - | 1/ |  |  |  | 0 |
| Black Scratch (override) Black Dog | - | 1/ |  |  |  | 0 |
| Black Scratch (override) Crab Raiders | - | 1/ |  |  |  | 0 |
| Black Scratch (override) Preacher Cult | - | 1/ |  |  |  | 0 |
| Black Scratch (override) Reavers | - | 1/ |  |  |  | 0 |
| Black Scratch (override) UC | - | 1/ |  |  |  | 0 |
| Blister Hill (override) malnourished | - | 1/ |  |  |  | 0 |
| Branding Camp | - | 4/ |  |  | лагерь->Astartes outpost | 1 |
| Clownsteady (override) HR takeover | - | 1/ |  |  |  | 0 |
| Drifter's Last (override) EP | - | 1/ |  |  |  | 0 |
| Drifter's Last (override) HR takeover | - | 1/ |  |  |  | 0 |
| Drifter's Raceway | - | 1/ |  |  |  | 0 |
| Drin (override) Bastards | - | 1/ |  |  |  | 0 |
| Drin (override) strengthened | - | 1/ |  |  |  | 0 |
| Flats Lagoon (override) AS | - | 1/ |  |  |  | 0 |
| Flats Lagoon (override) UC | - | 1/ |  |  |  | 0 |
| Flats Lagoon (override) ruins | - | 1/ |  |  |  | 0 |
| Ghost Village (Deadcatun override) | - | 1/ |  |  |  | 0 |
| Ghost Village (override) Deadcat CH FT | - | 1/ |  |  |  | 0 |
| Ghost Village (override) Deadcat CH WH | - | 1/ |  |  |  | 0 |
| Ghost Village (override) Deadcat FN FT | - | 1/ |  |  |  | 0 |
| Ghost Village (override) Deadcat FN WH | - | 1/ |  |  |  | 0 |
| Ghost Village (override) Deadcat Merc FT | - | 1/ |  |  |  | 0 |
| Ghost Village (override) Deadcat Merc WH | - | 1/ |  |  |  | 0 |
| Kopek | - | 1/ |  |  |  | 0 |
| Kopek (Override) Hooch | - | 1/ |  |  |  | 0 |
| Last Stand (override) Bele'coz | - | 1/ |  |  |  | 0 |
| Last Stand (override) Bele'coz esata dead | - | 1/ |  |  |  | 0 |
| Last Stand (override) Prosperous | - | 1/ |  |  |  | 0 |
| Last Stand (override) malnourished | - | 1/ |  |  |  | 0 |
| Last Stand (override) prosperous | - | 1/ |  |  |  | 0 |
| MARKER-Nest-Cower | - | 8/ |  |  |  | 0 |
| Martyrs Pit | - | 3/ |  |  |  | 0 |
| Mourn (override) AS | - | 1/ |  |  |  | 0 |
| Mourn (override) Scorched Ones | - | 1/ |  |  |  | 0 |
| Mourn (override) Southern Hive | - | 1/ |  |  |  | 0 |
| Mourn (override) UC | - | 1/ |  |  |  | 0 |
| Mud Town (override) Blue Cleavers | - | 1/ |  |  |  | 0 |
| Mud Town (override) Grayflayer | - | 1/ |  |  |  | 0 |
| Mud Town (override) Hounds | - | 1/ |  |  |  | 0 |
| Mysterious Tower | - | 10/ |  |  |  | 0 |
| Narko's Refuge | - | 1/ |  |  |  | 0 |
| Narko's Spear (override) ND | - | 1/ |  |  |  | 0 |
| Obedience | - | 9/ |  |  |  | 0 |
| Poisonous Lab | - | 4/ |  |  |  | 0 |
| Rot (override) | - | 1/ |  |  |  | 0 |
| Rot (override) Grayflayers | - | 1/ |  |  |  | 0 |
| Sakar | - | 1/ |  |  |  | 0 |
| Sakar (override) Kraz | - | 1/ |  |  |  | 0 |
| Sho-Battai (override) DR | - | 1/ |  |  |  | 0 |
| Shraff | - | 1/ |  |  |  | 0 |
| Shraff (override) Jeremiah | - | 1/ |  |  |  | 0 |
| Silent Camp | - | 4/ |  |  | лагерь->The Hub | 1 |
| Silent Camp 01FA | - | 4/ |  |  |  | 0 |
| Squin (override) malnourished | - | 1/ |  |  |  | 0 |
| Stack (override) malnourished | - | 1/ |  |  |  | 0 |
| Stack (override) takeover Bele'coz | - | 1/ |  |  |  | 0 |
| Strange Den | - | 9/ |  |  |  | 6 |
| The Hub (override) [harenga ded] | - | 1/ |  |  |  | 0 |
| The Hub (override) [seta ded] {esata alive} | - | 1/ |  |  |  | 0 |
| The Hub (override) [seta ded] {mukai alive} | - | 1/ |  |  |  | 0 |
| The Hub (override) shek stage 1 | - | 1/ |  |  |  | 0 |
| The Hub (override) shek stage 2 Bandits | - | 1/ |  |  |  | 0 |
| The Hub (override) shek stage 2 HN | - | 1/ |  |  |  | 0 |
| The Hub (override) shek stage 3 | - | 1/ |  |  |  | 0 |
| The Hub [override] ruins | - | 1/ |  |  |  | 0 |
| Tiny Settlement (Override) Marissa | - | 1/ |  |  |  | 0 |
| Victor's House (Abandoned) | - | 9/ |  |  |  | 0 |
| Waystation Highlander BZ HQ | - | 1/ |  |  |  | 0 |
| Waystation Highlander BZ HQ (override) Drifters | - | 1/ |  |  |  | 0 |
| Waystation Highlander BZ HQ (override) HN | - | 1/ |  |  |  | 0 |
| Waystation Highlander BZ HQ (override) HNO | - | 1/ |  |  |  | 0 |
| Waystation Highlander HN Territory HQ | - | 1/ |  |  |  | 0 |
| Waystation Highlander HN Territory HQ (override) Drifters | - | 1/ |  |  |  | 0 |
| Waystation Highlander HN Territory HQ (override) Flotsam | - | 1/ |  |  |  | 0 |
| Waystation Highlander HN Territory HQ (override) HN | - | 1/ |  |  |  | 0 |
| Waystation Highlander Shem | - | 1/ |  |  |  | 0 |
| Waystation Highlander Shem (override) Nomads | - | 1/ |  |  |  | 0 |
| Waystation Highlander Shem (override) WEC | - | 1/ |  |  |  | 0 |
| Waystation Ruins Stobe G (player override) | - | 1/ |  |  |  | 0 |
| Waystation Ruins Venge (player override) | - | 1/ |  |  |  | 0 |
| Waystation [Tech Scribes] | - | 1/ |  |  |  | 0 |
| World's End (override) Deadcat | - | 1/ |  |  |  | 0 |
| World's End (override) Flotsam | - | 1/ |  |  |  | 0 |
| World's End (override) HN | - | 1/ |  |  |  | 0 |
| World's End (override) Northern Hive | - | 1/ |  |  |  | 0 |
| World's End (override) UC | - | 1/ |  |  |  | 0 |
| floodland sword nest | - | 0/ |  |  |  | 0 |
| housecamp raider | - | 10/holding |  | да |  | 2 |
| housecamp raider w/poles | - | 10/holding |  | да |  | 2 |
| nest armoury ruin | - | 0/ |  |  |  | 0 |
| nest housecamp fishman | - | 10/ |  |  |  | 0 |
| nest library ruin | - | 0/ |  |  |  | 0 |
| nest spiders | - | 0/ |  |  |  | 0 |
| nest spiders bones | - | 0/ |  |  |  | 0 |
| nest trashed house | - | 10/ |  |  |  | 0 |
| nest- king gorillo | - | 0/ |  |  |  | 0 |
| nest- lab ruin | - | 0/ |  |  |  | 0 |
| nest- lab ruin gurglers | - | 0/ |  |  |  | 0 |
| nest- shek military ruins | - | 0/ |  |  |  | 0 |
| nestruin- holy outpost | - | 1/ |  |  |  | 0 |
| ruin warehouse | - | 1/ |  |  |  | 0 |
| ruin- fogman resident | - | 0/ |  |  |  | 0 |
| spider camp marker | - | 8/ |  |  |  | 0 |
| 失控的武士实验室 | - | 4/ |  |  |  | 2 |
| 实验体工厂遗迹 | 失控 | 1/holding |  | да |  | 2 |

## Фракции

### Drifters  `51707-rebirth.mod`
- создатель: rebirth.mod; тип: ADVENTURER; персонажей: 155, уников: 123
- уники: 8-Ball, Baap, Bad Tom, Bard, Beep, Beep Soul, Benny, Biggie, Blue Eyes, Boop, Chips, Cliff ...
- лидеры: Beep
- расы фракции: Greenlander(100), Hive Prince(10), Hive Soldier Drone(20), Hive Worker Drone(20), P4 Unit(1), Scorchlander(100); фактические: Greenlander 54, Scorchlander 30, Shek 17, Hive Prince 15, Dark Hive Worker Drone 12, Dark Hive Soldier Drone 11
- города (2): Houndmaster's Den[9], Taunt's Hideout[9]
- союзники после: Tech Hunters 100, Shinobi Thieves 100, Anti-Slavers 100, Holy Nation Outlaws 100, The Holy Nation 100; враги после: Daemons -80, Lost Chaos Space Marines -80, World Devourer War Gang -80, Midnight Lord -80, Hatred of intelligence -80
- KMM-отношения: KMM_Behavior: Bloodraiders None->-16, White Eyebrow Clan None->-8, Oni None->-14, Reavers None->-40 (+53)
- conductor: arch=settler, wealth=240, strength=119, ambition=survival, relic=None
- снаряжение: культура: This Machine, Tanegashima Pistol, Keratin Plate Jacket, Hazards Shell - 8-Ball [upper], Oldworld Bow MkIII; носят: Straw Hat 29, Halfpants (ragged) 26, Drifter's Leather Pants 22, Cargopants 21, Drifter's Leather Jacket 18
- гардероб: uniforms:samurai(char)
- Cleanup: лагеря ["Houndmaster's Den", "Taunt's Hideout"], хост []
- слои KMM: KMM_Atlas 2, KMM_Behavior 1, KMM_Cleanup 4, KMM_Economy 124, KMM_Fix 1, KMM_Glue 121, KMM_Merged 35, KMM_Town 31, KMM_Wardrobe 61

### Adventurers Guild  `1532719-Lore Friendly Recruitment - The Adventurer's Guild.mod`
- создатель: Lore Friendly Recruitment - The Adventurer's Guild.mod; тип: ADVENTURER; персонажей: 101, уников: 1
- уники: Hideyoshi
- лидеры: Onyx Adventurer, Adventurer Headhunter
- расы фракции: Greenlander(100); фактические: Greenlander 39, Scorchlander 37, Shek 20, Hive Prince 9, Hive Soldier Drone 9, Hive Worker Drone 8
- города (2): Ishijuku[holding], Shirokyo[city]
- регионы: Border Zone, Sinkuun
- союзники после: Traders Guild 50; враги после: Daemons -80, Lost Chaos Space Marines -80, World Devourer War Gang -80, Midnight Lord -80, Hatred of intelligence -80
- KMM-отношения: KMM_Behavior: Bloodraiders None->-20, Black Dragon Ninjas None->-7, White Eyebrow Clan None->-10, Oni None->-9 (+55)
- conductor: arch=settler, wealth=240, strength=119, ambition=survival, relic=None
- снаряжение: культура: Chainmail, Black Plate Jacket, Drifter's Leather Pants, Armoured Hood, Kusari Zukin; носят: Cargopants 130, Rag Shirt 130, Rag Loincloth 130, Halfpants (colored) 130, Katana 127
- слои KMM: KMM_Atlas 2, KMM_Behavior 1, KMM_Diplo 1, KMM_Economy 101, KMM_Glue 101, KMM_Town 1, KMM_Wardrobe 101

### United Cities  `defaultEmpireFactionSID`
- создатель: ?; тип: CIVILIAN; персонажей: 91, уников: 28
- уники: Arai, Blue, Cat, Catun Scrapmaster, Creepy Noble, Emperor Tengu, Eyegore, General Sonnenschein, General Tao, Genjo, Koin, Lady Merin ...
- лидеры: Samurai Sergeant, Tribute Prefect, Samurai Captain
- расы фракции: Greenlander(150), Scorchlander(150), Shek(50), Skeleton(1), Hive Soldier Drone(10), Hive Worker Drone(10); фактические: Greenlander 16, Scorchlander 15, Shek 6, Hive Prince 5, Hive Prince South Hive 3, Hive Worker Drone South Hive 2
- города (70): Bark[city], Brink[city], Farming Village[holding], Heft[city], Clownsteady[city], Port South[city], Stoat[city], Abandoned Town[holding], Catun[city], Heng[city], Tengu's Vault[city], Ska[city], Military Outpost[city], Hamlet[holding], Guard Outpost[holding], Farm Ruin[holding], Drifter's Last[city], Fishing Village[holding], Sho-Battai[city], Drin[holding], Endin[holding], Bast[holding], Sho-Battai (override) half destroyed[2], Free Settlement[holding], Bark (override) half destroyed[4], Brink 
- регионы: Bast, Bonefields, Heng, Stobe's Gamble, Stormgap Coast, The Great Desert, The Hook, The Outlands
- союзники после: Police 100, Traders Guild 100, Skeletons 100, Shinobi Thieves 100, Imperial Bank 100; враги после: The Holy Nation -100, Dark Reavers -100, Cannibals -90, Daemons -80, Lost Chaos Space Marines -80
- KMM-отношения: KMM_Behavior: Bloodraiders None->-60, White Eyebrow Clan None->-60, Oni None->-60, Reavers None->-70 (+61)
- conductor: arch=state, wealth=2400, strength=407, ambition=enrichment, relic=None
- снаряжение: культура: Hive Soldier Empire Samurai Armour, Samurai Armor - Superheavy, Reinforced Samurai Armor, Empire Reinforced Samurai Armour, Empire Heavy Samurai Armour; носят: Katana 163, Samurai Boots 153, Samurai Armour 136, Wakizashi 132, Leather Shirt 121
- гардероб: uniforms:samurai(char)
- слои KMM: KMM_Atlas 49, KMM_Behavior 1, KMM_Diplo 13, KMM_Economy 86, KMM_Elite 4, KMM_Fix 2, KMM_Glue 67, KMM_Merged 19, KMM_Town 4, KMM_Wardrobe 67

### The Holy Nation  `1083-gamedata.base`
- создатель: gamedata.base; тип: CIVILIAN; персонажей: 88, уников: 23
- уники: Ambiguous Skeleton, Bell Sow Priest, Brother Abelus, Brother Khlodar, Cork Priest, Glas, High Inquisitor, High Inquisitor Seta, High Inquisitor Valtena, High Overseer /PALADIN_NAME/, High Paladin Tyr, Holy Lord Phoenix ...
- лидеры: High Paladin, Inquisitor, Paladin
- расы фракции: Greenlander(100), Scorchlander(15); фактические: Greenlander 53, Scorchlander 28, Greenlander Child 3, Dead Greenlander 2, Human 1, Hive Soldier Drone 1
- города (76): Blister Hill[city], Bad Teeth[city], Stack[city], Tiny Settlement[holding], Rebirth[city], Holy Mines[holding], Holy Farm[holding], Holy Military Base[city], Holy Mine Ruin[holding], Okran's Fist[city], Ruined Holy Outpost[holding], Narko's Trap[city], Watchtower[holding], Okran's Shield[city], Holy Farm[holding], Ruined Farm[holding], Drin (override) partial rebuild HN[4], Bad Teeth (override) half destroyed[2], Blister Hill (override) destroyed[4], Holy Military Base (override) destroyed[4], O
- регионы: Arm of Okran, Border Zone, Okran's Gulf, Okran's Pride, Okran's Valley, Rebirth, Skinner's Roam
- союзники после: Adventurers Guild 100, The Holy Nation 100, Shinobi Thieves 100, Missionaries 30, Preacher Cult 28; враги после: Dark Hive -200, Dark Reavers -200, United Cities -100, Holy Nation Outlaws -100, Mongrel -100
- KMM-отношения: KMM_Behavior: Bloodraiders None->-70, White Eyebrow Clan None->-70, Oni None->-70, Reavers None->-80 (+58)
- conductor: arch=religion, wealth=3210, strength=515, ambition=faith, relic=None
- снаряжение: культура: Phoenix Plate, Holy Chest Plate - Heavy, Holy Plate Armor, Holy Chest Plate - Medium, Holy Lords Chainmail; носят: Stout Hessian Uniform 198, Plated Longboots 151, Holy Chest Plate 125, Bucket Zukin 118, Flared Helmet 117
- гардероб: no_firearms, uniforms:holy_nation
- Cleanup: лагеря ['Roadside Bakery'], хост ['Blister Hill', 'Stack', 'Busted Wall']
- слои KMM: KMM_Atlas 22, KMM_Behavior 1, KMM_Cleanup 3, KMM_Diplo 8, KMM_Economy 87, KMM_Elite 8, KMM_Fix 2, KMM_Glue 65, KMM_Merged 21, KMM_Town 1, KMM_Wardrobe 67

### Tech Hunters  `1233-gamedata.base`
- создатель: gamedata.base; тип: CIVILIAN; персонажей: 63, уников: 22
- уники: Archer, Bagu, Blast, Chad, Crumblejon, Daniel, Dr. Tefo, Enguito, Gilbert, Kani, Keiji, Knight ...
- лидеры: tech hunter shopkeeper, Tech Hunter Guard, Drifter
- расы фракции: Shek(75), Greenlander(75), Scorchlander(75), Skeleton(5), Hive Soldier Drone(25), Hive Prince(10); фактические: Greenlander 9, Skeleton 7, Hive Prince 7, Shek 6, Scorchlander 4, Primordial Hive Praetorian 2
- города (17): Flats Lagoon[city], Mourn[city], World's End[city], Waystation[holding], Black Scratch[city], Waystation Ruins[holding], Waystation Four[holding], Expedition 5[holding], Expedition 4[holding], Stoat (override) TH takeover[2], Rogue[city], Barcrest (Override) Sysus Bandits are dead[1], Narko's Trap (override) tech hunters[6], Suspicious Lab (override) tech hunters[4], Tower of Abuse (override) tech hunters[4], Old Control Tower (override) TH[4], World's Ruin[holding]
- регионы: Arm of Okran, Bonefields, Flats Lagoon, Stenn Desert, Stobe's Garden, The Outlands
- союзники после: Machinists 100, Mongrel 100, Cannibal Hunters 100, Holy Nation Outlaws 100, Desert Divers 100; враги после: Dark Reavers -100, Daemons -80, Lost Chaos Space Marines -80, World Devourer War Gang -80, Midnight Lord -80
- KMM-отношения: KMM_Behavior: Bloodraiders None->-60, White Eyebrow Clan None->-60, Oni None->-60, Reavers None->-70 (+62)
- conductor: arch=state, wealth=1050, strength=227, ambition=enrichment, relic=None
- снаряжение: культура: Combat Armor MkII - White, Combat Armor MkII - Black, Tsume Armor MkIV, Eagle's Cross, Mercenary Plate - Heavy; носят: Katana 76, Plated Longboots 74, Mercenary Leather Armour 72, Mercenary Plate 71, Hachigane 70
- Cleanup: лагеря [], хост ['Flats Lagoon', "World's End"]
- слои KMM: KMM_Atlas 9, KMM_Behavior 1, KMM_Cleanup 2, KMM_Diplo 7, KMM_Economy 61, KMM_Elite 1, KMM_Glue 37, KMM_Merged 14, KMM_Town 14, KMM_Wardrobe 44

### Rusty Raiders  `5007316-Rusty Raiders FACTION.mod`
- создатель: Rusty Raiders FACTION.mod; тип: ADVENTURER; персонажей: 41, уников: 28
- уники: Bolt, Bolt, Brain, Brain, Captain Screw, Captain Screw, Drill, Drill, Gears, Gears, Hash-bot, Kaius ...
- лидеры: Oily, Oily
- расы фракции: P4 Unit(100), Screamer MkI(100), Skeleton(100), Skeleton Log-Head MKII(100), Skeleton MKII Screamer(100), Skeleton P4MkII(100); фактические: Soldierbot 6, Skeleton P4MkII 5, P4 Unit 4, Skeleton 4, Screamer MkI 4, Skeleton MKII Screamer 2
- города (6): Rust HQ[city], Rust HQ (ally)[2], Cloud House (rusty)[3], Okran's Shield (override) Rust[6], Hidden Camp Rust[1], Hidden Camp Rustempty[1]
- регионы: Deadlands, Floodlands, Grey Desert, Iron Valleys, Skimsands, Sniper Valley, Stobe's Gamble, Stobe's Garden, The Black Desert, The Iron Trail
- союзники после: Skeletons 100, Dust Bandits 60; враги после: Skeleton Legion -100, Second Empire -100, Second Empire Exile -100, The Holy Nation -70, Cult of Fluorite -70
- KMM-отношения: KMM_Behavior: The Holy Nation None->-70, Dark Hive None->-8, Reavers None->-20, Lost Warrior None->-40 (+95)
- conductor: arch=bandit, wealth=150, strength=81, ambition=survival, relic=None
- снаряжение: культура: ban hammer; носят: Ancient Samurai Legplates 28, Armoured Rag Skirt (colored) 28, Long Cleaver 20, Small Backpack (colored) 18, Spring Bat 15
- банда outlaws: Rusty Raiders
- слои KMM: KMM_Atlas 1, KMM_Behavior 1, KMM_Diplo 1, KMM_Economy 44, KMM_Town 3, KMM_Wardrobe 12

### Shek Kingdom  `11624-Dialogue (10).mod`
- создатель: Dialogue (10).mod; тип: MILITARY; персонажей: 41, уников: 13
- уники: Bayan, Cydonia, Esata the Stone Golem, Finn, Hire me 700 Shek, Konkus, Mukai The Mountain, Oron, Rane The Giant, Seto, Sword for hire 10 Shek Kingdom, hire engineer shek ...
- лидеры: Hundred Guardian, Shek Warrior, Kamikaze
- расы фракции: Shek(100); фактические: Shek 35, Shek Child 3, Young Shek 1
- города (27): Admag[city], Squin[city], Last Stand[city], Old Frontlines[holding], The Great Fortress[city], Bad Teeth (override) shek takeover[2], Holy Mines (override) shek takeover[3], Okran's Shield (override) shek[6], Stack (override) shek takeover[2], Admag (override) esata dead[2], Admag (override) Seto[2], Squin (override) new leader[2], Exile Camp (Esata)[9], Exile Camp (Mukai)[9], Admag (override) ruined[4], Berserker Village (override)[1], New Kralia (override) kingdom[1], Okran's Shield (override)
- регионы: Border Zone, Spider Plains, Stenn Desert
- союзники после: Adventurers Guild 100, Shinobi Thieves 100, cloak shop(test) 25, Guild of Surgeons 24, Sultans Wares 21; враги после: The Holy Nation -100, Dark Reavers -100, Cannibals -90, Daemons -80, Lost Chaos Space Marines -80
- KMM-отношения: KMM_Behavior: Bloodraiders None->-60, White Eyebrow Clan None->-60, Oni None->-60, Reavers None->-70 (+62)
- conductor: arch=state, wealth=600, strength=149, ambition=survival, relic=None
- снаряжение: культура: Blackened Chainmail, Samurai Clothpants - Heavy, Cydonia's Cargopants, Cloak (SK), Blackened Chainmail Tagelmust; носят: Martial Artist Bindings 67, Plated Longboots 60, Samurai Legplates 58, Plank 58, Armoured Rags (colored) 39
- слои KMM: KMM_Atlas 9, KMM_Behavior 1, KMM_Diplo 4, KMM_Economy 31, KMM_Glue 29, KMM_Merged 8, KMM_Town 3, KMM_Wardrobe 34

### Skeletons  `42088-rebirth.mod`
- создатель: rebirth.mod; тип: ADVENTURER; персонажей: 36, уников: 10
- уники: Agnu, Armour King, Burn, Clutch, Dack, Drek, Quin, Sadneil, Xai-Xi, Zhànshì
- лидеры: Skeleton Doctor, Skeleton Drifter, Skeleton Variant01
- расы фракции: Skeleton(500), P4 Unit(100), Skeleton ILA-M MKI(4), Skeleton ILA-M MKII(4), Skeleton KLR-M MKI(4), Skeleton KLR-M MKII(3); фактические: Skeleton 11, P4 Unit 5, Skeleton SL-M MKIII 4, Skeleton ILA-M MKI 3, Skeleton SL-M MKII 3, Skeleton ILA-M MKIII 3
- города (4): Black Desert City[city], Burn's Tower[holding], Drowned Ruins[holding], Scraphouse[holding]
- регионы: Deadlands
- союзники после: United Cities 100, Nomadic Skeletons 60, Floodlands Skeletons 60, Old Machines 60, Cyborgs 60; враги после: The Holy Nation -100, Daemons -80, Cult of Fluorite -80, Lost Chaos Space Marines -80, World Devourer War Gang -80
- KMM-отношения: KMM_Behavior: Bloodraiders None->-25, White Eyebrow Clan None->-20, The Holy Nation None->-80, Oni None->-14 (+72)
- conductor: arch=robot, wealth=420, strength=127, ambition=survival, relic=None
- снаряжение: культура: Foreign Greatsword, Forgotten Sabre; носят: Cargopants 13, Sleeveless Longcoat 13, Ninja Gi 13, Longcoat 13, Tricorn Hat 13
- слои KMM: KMM_Atlas 1, KMM_Behavior 1, KMM_Diplo 2, KMM_Economy 35, KMM_Glue 31, KMM_Merged 6, KMM_Town 6, KMM_Wardrobe 28

### Outlaw  `5442-gamedata.base`
- создатель: gamedata.base; тип: BANDIT; персонажей: 35, уников: 24
- уники: Apprentice , Blender, Brutus, Espher, Gabal, Garret's slave, Gurobu, Gutworm, Hex, Joseph P. Notaskeleton, Lothar, Luquin ...
- лидеры: Razor, Gurobu, Meep
- расы фракции: Greenlander(100), Shek(20); фактические: Scorchlander 9, Greenlander 8, Shek 8, Hive Soldier Drone 5, Young Shek 4, Hive Worker Drone South Hive 4
- города (4): Meep Camp BD[holding], Meep's Training Camp[holding], Tower of the Wizard[holding], Watcher's Camp[9]
- регионы: Burning Forest, South Wetlands, Spider Plains, Stormgap Coast, Vain
- союзники после: Holy Nation Outlaws 100, Shinobi Thieves 100; враги после: United Cities -100, Police -100, Cult of Fluorite -70, Missionaries -70, The Holy Nation -70
- KMM-отношения: KMM_Behavior: The Holy Nation None->-70, Dark Hive None->-15, Reavers None->-20, Lost Warrior None->-35 (+96)
- conductor: arch=bandit, wealth=420, strength=99, ambition=enrichment, relic=None
- снаряжение: культура: Dead Sergeant`s pants, cast-off Razors, "Razor", Greatsword, Prisoner Shackles; носят: Prisoner Shackles 13, Hive Prisoner Shackles 2, Human Skin Suit 1, Human Skin 1, Ancient Samurai Boots 1
- банда outlaws: Outlaw
- Cleanup: лагеря ["Watcher's Camp"], хост []
- слои KMM: KMM_Behavior 1, KMM_Cleanup 2, KMM_Diplo 1, KMM_Economy 13, KMM_Elite 1, KMM_Fix 2, KMM_Glue 13, KMM_Merged 4, KMM_Wardrobe 1

### Traders Guild  `1088-gamedata.base`
- создатель: gamedata.base; тип: TRADER; персонажей: 34, уников: 16
- уники: Diseased Trader, Lady Kana, Longen, Slave Market Master, Slave Master Chago, Slave Master Grande, Slave Master Haga, Slave Master Ruben, Slave Master Wada, Slave Mistress Grace, Slave Mistress Ren, Yamdu ...
- лидеры: Longen
- расы фракции: Greenlander(70), Scorchlander(100), Shek(50), Hive Soldier Drone(25), Dark Hive Soldier Drone(4), Dark Hive Worker Drone(3); фактические: Scorchlander 6, Greenlander 5, Hive Prince 1, Shek 1
- города (9): Trader's Edge[holding], Raided Caravan[holding], Trader's Edge (override) destroyed[1], Trader's Edge (override) malnourished[1], Trader's Edge (override) malnourished 1[1], Resort Island[city], Resort Island (override) destroyed[2], Bast (override) TG[2], Port North (override) UC takeover[5]
- регионы: Heng, South Wetlands
- союзники после: Slave Traders 100, Police 100, United Cities 100, Holy Nation Outlaws 100, Shinobi Thieves 100; враги после: Daemons -80, Lost Chaos Space Marines -80, World Devourer War Gang -80, Midnight Lord -80, Hatred of intelligence -80
- KMM-отношения: KMM_Behavior: Bloodraiders None->-60, White Eyebrow Clan None->-60, Oni None->-60, Reavers None->-60 (+78)
- conductor: arch=trader, wealth=330, strength=131, ambition=enrichment, relic=None
- снаряжение: культура: Plate Jacket Heavy - Grey, Plate Jacket Medium - Grey, Cloak (UC Blue), Shopkeeper goods bag, Karuta Zukin (Fullface); носят: Samurai Boots 51, Katana 42, Samurai Clothpants 38, Chain Shirt 36, Samurai Legplates 35
- гардероб: uniforms:samurai(char)
- слои KMM: KMM_Atlas 4, KMM_Behavior 1, KMM_Diplo 9, KMM_Economy 47, KMM_Elite 2, KMM_Glue 24, KMM_Merged 16, KMM_Town 2, KMM_Wardrobe 19

### Western Hive  `18000-gamedata.base`
- создатель: gamedata.base; тип: MILITARY; персонажей: 32, уников: 5
- уники: Adeanis, Praetorian Overseer Stia, Royal Enforcer Yama, Royal Samurai Tobu, The Queen
- лидеры: Praetorian Overseer Stia
- расы фракции: Hive Soldier Drone(100), Hive Prince(5), Hive Worker Drone(100); фактические: Hive Soldier Drone 13, Hive Prince 9, Hive Worker Drone 7, Western Hive Praetorian 2, Hive Queen 1, Hive Prince Juvenile 1
- города (3): Hive Village[holding], Western Hive[holding], Distant Hive Village[holding]
- регионы: Dreg, Sinkuun, Vain
- союзники после: Adventurers Guild 100, Free Traders 28, Wandering Cloak Shop 25, Guild of Surgeons 25, Gunsmiths 25; враги после: Daemons -80, Lost Chaos Space Marines -80, World Devourer War Gang -80, Midnight Lord -80, Hatred of intelligence -80
- KMM-отношения: KMM_Behavior: Bloodraiders None->-60, White Eyebrow Clan None->-60, Oni None->-60, Reavers None->-70 (+65)
- conductor: arch=state, wealth=330, strength=105, ambition=survival, relic=None
- снаряжение: культура: Hive Soldier Samurai Armour, Western Hive Soldier Plate Armor, Stickman Shield, Beak Royal Armor, Western Hive Heavy Plate Armor; носят: Leather Hive Vest 46, Rag Loincloth (Dyed) 31, Crescent Glaive 31, Polearm 25, Western Hive Rag Skirt 25
- гардероб: uniforms:samurai(char)
- слои KMM: KMM_Atlas 1, KMM_Behavior 1, KMM_Diplo 5, KMM_Economy 39, KMM_Elite 5, KMM_Glue 28, KMM_Merged 3, KMM_Town 2, KMM_Wardrobe 28

### Guild of Surgeons  `1532969-Guild of Surgeons.mod`
- создатель: Guild of Surgeons.mod; тип: TRADER; персонажей: 27, уников: 11
- уники: Alistair, Commander Rein, Crank, Doctor Miss, Gunther, Joseph, Orion, Owl, Polter, Spiders, Squirrel
- лидеры: Joseph
- расы фракции: Greenlander(75), Hive Prince(5), Hive Soldier Drone(10), Hive Worker Drone(60), Scorchlander(70), Shek(76); фактические: Greenlander 7, Shek 6, Scorchlander 5, Hive Soldier Drone 4, Hive Prince 4, Skeleton 3
- города (4): Hope[city], The Apothecary[holding], Redmans Tower[holding], Leviathons Watch[holding]
- регионы: Bast, Bonefields, Leviathan Coast, Stenn Desert
- союзники после: Shek Kingdom 50, Traders Guild 50, Drug Peddlers 26, Gunsmiths 26, Wandering Cloak Shop 25; враги после: Band of Bones -100, Daemons -80, Lost Chaos Space Marines -80, World Devourer War Gang -80, Midnight Lord -80
- KMM-отношения: KMM_Behavior: Bloodraiders None->-60, White Eyebrow Clan None->-60, Oni None->-60, Reavers None->-60 (+70)
- conductor: arch=trader, wealth=420, strength=79, ambition=enrichment, relic=None
- снаряжение: культура: -; носят: Visored Helmet 7, Naginata 7, Halfpants [reinforced] 6, Medium backpack (colored) 6, Sleeveless Dustcoat 6
- слои KMM: KMM_Atlas 3, KMM_Behavior 1, KMM_Diplo 4, KMM_Economy 33, KMM_Elite 1, KMM_Glue 26, KMM_Town 1, KMM_Wardrobe 16

### Slave Traders  `1084-gamedata.base`
- создатель: gamedata.base; тип: SLAVER; персонажей: 25, уников: 4
- уники: Curious Kid, Garret, Slaver Rookie, Uncle Rukus
- лидеры: Slaver Boss, Slaver Caravan Boss, Slaver
- расы фракции: Greenlander(250), Hive Prince(10), Hive Soldier Drone(75), Scorchlander(100), Shek(100), Hive Worker Drone(20); фактические: Greenlander 5, Scorchlander 2, Scorchlander Child 1
- города (27): Slave Farm[city], Port North[city], Slave Markets[holding], Slaver Camp[holding], Eyesocket[city], Stone Camp[city], Port South[city], Eyesocket (override) destroyed[4], Port South (override) destroyed[4], Slave Farm (override) destroyed [4], Slave Farm S (override) destroyed[4], Slave Farm South[city], South Stone Camp[city], South Stone Camp (override) destroyed[4], Stone Camp (override) destroyed[4], Cult village (override) slaver takeover[5], Hive Village N (override) empty[4], Settled Nomad
- регионы: Heng, South Wetlands, Stormgap Coast, The Great Desert, The Hook
- союзники после: Police 100, Traders Guild 100, Imperial Lords 100, United Cities 100, Adventurers Guild 100; враги после: Mongrel -100, Rebel Farmers -100, Anti-Slavers -100, Cult of Fluorite -70, Missionaries -70
- KMM-отношения: KMM_Behavior: The Holy Nation None->-70, Dark Hive None->-8, Reavers None->-15, Lost Warrior None->-40 (+89)
- conductor: arch=bandit, wealth=960, strength=215, ambition=enrichment, relic=None
- снаряжение: культура: Mercenary Cuirass, Mercenary Legplates, Footman's Plated Hood, Visored Helmet, Footman's Helmet; носят: Dyed Turban 75, Mercenary Club 74, Leather Shirt 63, Longsword 59, Turban 58
- слои KMM: KMM_Atlas 6, KMM_Behavior 1, KMM_Diplo 1, KMM_Economy 41, KMM_Glue 18, KMM_Merged 10, KMM_Town 1, KMM_Wardrobe 21

### Astartes survivors  `1034-TEXT TEXTURE.mod`
- создатель: TEXT TEXTURE.mod; тип: MILITARY; персонажей: 24, уников: 5
- уники: Astartes correspondent, Deathwatch - Sinrata, Salamander-Kam, Ultra Warrior - Champion, Ultramariner - Quintus Proctor
- лидеры: Extreme Warrior - Terminator Assault Captain, New Extreme Warrior 001 Mercenary Commander, Super Veteran Extreme Warrior 002
- расы фракции: -; фактические: Astartes (Elite) 6, Astartes (The Lost) 4
- города (1): Astartes outpost[city]
- регионы: Flats Lagoon
- союзники после: Tech Hunters 100, The Lost Black Sanctuary 80, Death Watch 80, Grey Knight 80, Lost Warrior 80; враги после: United Cities -100, Lost Chaos Space Marines -100, Shek Kingdom -100, The Holy Nation -100, World Devourer War Gang -100
- KMM-отношения: KMM_Behavior: Bloodraiders None->-40, White Eyebrow Clan None->-47, Oni None->-37, Reavers None->-60 (+67) | KMM_Glue: 1-KMM_Glue.mod None->60
- conductor: arch=imperium, wealth=350, strength=109, ambition=faith, relic=hunt_chaos
- снаряжение: культура: -; носят: Ultramariner - MKX Power Armor 33, Extreme Warrior - MKX Power Combat Boots 33, Extreme Warrior - Power Backpack 28, Power armor liner 24, Standard equipment - chainsaw sword 24
- гардероб: power_armor
- Cleanup: лагеря [], хост ['Astartes outpost']
- слои KMM: KMM_Atlas 1, KMM_Behavior 1, KMM_Cleanup 1, KMM_Diplo 1, KMM_Economy 24, KMM_Glue 25, KMM_Wardrobe 19

### Cannibals  `518-gamedata.base`
- создатель: gamedata.base; тип: BANDIT; скрыта в UI (реальна в мире); персонажей: 24, уников: 6
- уники: Adidan, Baron Samedi, Crunch, Mighty Canhead, Thickbone the Fat, Wendigo
- лидеры: Strong cannibalistic servants, Лидери Отряда Канибалов Мясника, Cannibal Mancatcher
- расы фракции: Cannibal(60), Cannibal Skav(40); фактические: Cannibal 20, Cannibal Child 1, Cannibal Skav 1, Hive Worker Drone 1
- города (24): Cannibal Village 2[1], Cannibal Village[3], Painted Tribe Camp[0], _Cannibal Village (override)[3], Cannibal Infestation[0], Sho -Battai (override) cannibals[4], Okran's Fist (override) cannibals[4], Butcher's Lair[3], Adidan's Tower[9], Shaman's Hideout[3], Wendigo's Hut[9], Lost Tower[4], Bast (override) cannibals[4], Flotsam Safehouse (override) cannibals[9], Ghost Village (override) Cannibal takeover[3], Hamlet (override) cannibals[3], Rebirth (override) cannibals[4], Tower Of Goats (overrid
- регионы: Arm of Okran, Bast, Berserker Country, Cannibal Plains, Darkfinger, Dreg, Hidden Forest, Northern Coast, Okran's Valley, Purple Sands, The Great Desert, The Iron Trail, The Shrieking Forest
- союзники после: Crystal Enemys 100, Soulbodies 100, Skull Collectors 28, Fogmen 26, Kral's Chosen 25; враги после: The Holy Nation -100, Cannibal Hunters -100, The Holy Nation -100, Shek Kingdom -90, United Cities -90
- KMM-отношения: KMM_Behavior: Bloodraiders None->-25, White Eyebrow Clan None->-13, Reavers None->20, Lost Warrior None->-60 (+135) | KMM_Glue: 1-KMM_Glue.mod None->-100
- conductor: arch=savage, wealth=40, strength=28, ambition=expansion, relic=None
- снаряжение: культура: Cannibal Heavy Plate Armor, Cannibal Spiked Medium Plate Armor, Cannibal Medium Plate Armor, Cannibal Plate Leggings, Cannibal Plate Arms; носят: Flesh Cleaver 37, Spiked Club 26, Long Cleaver 21, Combat Cleaver 19, Scrap Iron Stick 18
- гардероб: pagan, savage
- банда outlaws: Cannibals
- Cleanup: лагеря ["Adidan's Tower", "Wendigo's Hut"], хост []
- слои KMM: KMM_Behavior 1, KMM_Cleanup 4, KMM_Diplo 1, KMM_Economy 22, KMM_Fix 3, KMM_Glue 21, KMM_Merged 1, KMM_Town 1, KMM_Wardrobe 17

### Southern Hive  `56777-Dialogue.mod`
- создатель: Dialogue.mod; тип: MILITARY; персонажей: 23, уников: 6
- уники: Droneguard Captain Yanshi, General Jaichong, Gunner Captain Qian, Hive Prince, Praetorian Executioner Tsep, Queen of the South
- лидеры: Queen of the South
- расы фракции: Hive Soldier Drone South Hive(100), Hive Prince South Hive(5), Hive Worker Drone South Hive(100); фактические: Hive Soldier Drone South Hive 8, Hive Prince South Hive 5, Hive Worker Drone South Hive 5, South Hive Praetorian 3, Hive Queen 1, South Hive Prince Juvenile 1
- города (8): Southern Hive[city], Southern Hive Village[holding], Hiver-Claimed Armoury[holding], Iron HQ (south hive takeover)[4], Reaver Camp (south hive takeover)[4], Skinhouse (south hive takeover)[4], Catun (override) south hive[2], The Old Prison (override) south hive[4]
- регионы: Greyshelf, Royal Valley
- союзники после: Robotic Wildlife 100, Gunsmiths 26, Free Traders 24, Drug Peddlers 23, Wandering Cloak Shop 20; враги после: Western Hive -100, Dark Hive -100, Daemons -80, Lost Chaos Space Marines -80, World Devourer War Gang -80
- KMM-отношения: KMM_Behavior: Reavers None->-70, Lost Warrior None->-2, Band of Bones None->-70, Blood Butcher Tribe None->-70 (+34)
- conductor: arch=state, wealth=330, strength=103, ambition=expansion, relic=None
- снаряжение: культура: Black Carapace Hive Soldier Plate Armor, Hiver Royal Guard Armor, Hive Soldier Plate Armor, Southern Hive Soldier Plate Armor, Black Carapace Hive Heavy Plate Armor ; носят: Hive Leg Plates 44, Hiver Chain Shirt 35, Southern Hive Ragpants - Light 35, Leather Hive Vest 31, Southern Hive Ragplate 31
- слои KMM: KMM_Atlas 2, KMM_Behavior 1, KMM_Diplo 6, KMM_Economy 25, KMM_Elite 4, KMM_Glue 23, KMM_Merged 1, KMM_Wardrobe 18

### Swampers  `41162-Dialogue.mod`
- создатель: Dialogue.mod; тип: CIVILIAN; персонажей: 22, уников: 6
- уники: Fuli, Hashish Dealer, Retired Slaver, Shady Crab Seller, Swamper Barman, Turtle Lady
- лидеры: Swamper Non-Gang, Swamp huckster, Skeleton Civilian
- расы фракции: Greenlander(400), Hive Prince(50), Hive Soldier Drone(50), Hive Worker Drone(50), Scorchlander(200), Shek(75); фактические: Scorchlander Child 2, Greenlander Child 1, Scorchlander 1, Hive Prince 1, P4 Unit 1, Greenlander 1
- города (6): Mud Town[holding], Swamp Village[holding], Shark[city], Grayflayer Village (override) swampers[3], Shark (override) all ded[2], Stone Rat Village (override) swampers[3]
- регионы: The Swamp
- союзники после: Holy Nation Outlaws 100, Shinobi Thieves 100, Hounds 7, Grayflayers 5, Stone Rats 1; враги после: Raptors -100, Spiders -100, Daemons -80, Lost Chaos Space Marines -80, World Devourer War Gang -80
- KMM-отношения: KMM_Behavior: Bloodraiders None->-13, White Eyebrow Clan None->-12, Oni None->-15, Reavers None->-47 (+54)
- conductor: arch=settler, wealth=330, strength=87, ambition=enrichment, relic=None
- снаряжение: культура: Bushcoat, Turtle Armour, Turtle Legplate, Cargopants [sneaky chain], Turtle Hat; носят: Rattan Hat 21, Worn-out Shorts 18, Rag Shirt 17, Rag Loincloth 17, Tooth Pick 14
- гардероб: pagan
- Cleanup: лагеря [], хост ['Mud Town']
- слои KMM: KMM_Atlas 5, KMM_Behavior 1, KMM_Cleanup 1, KMM_Economy 24, KMM_Glue 16, KMM_Merged 6, KMM_Town 1, KMM_Wardrobe 17

### Shrieking Bandits  `42235-rebirth.mod`
- создатель: rebirth.mod; тип: BANDIT; скрыта в UI (реальна в мире); персонажей: 19, уников: 0
- лидеры: Wise Babbler, Shrieking Bandit, Foolish Babbler
- расы фракции: Greenlander(100); фактические: -
- союзники после: Nomads 100, Soulbodies 100, Crystal Enemys 100; враги после: -
- снаряжение: культура: Red Howler Chest Plates, Yellow Howler Chest Plates, Moaning Plate Skirt , Foolish Babbler Plates , Wise Babbler Plates; носят: Tumourous Club 10, Beaked Cleaver 9, Disk Sabre 9, Light Body Wrap  5, Red Howler Chest Plates 5
- слои KMM: KMM_Economy 19, KMM_Glue 19, KMM_Wardrobe 19

### Skeleton Legion  `57737-rebirth.mod`
- создатель: rebirth.mod; тип: BANDIT; скрыта в UI (реальна в мире); персонажей: 19, уников: 4
- уники: Purge Unit 5, Purge Unit 8, Purge Unit 9, Stalker Unit
- лидеры: Stalker Unit, Purge Unit 5
- расы фракции: Skeleton Log-Head MKII(100); фактические: P4 Unit 4, Skeleton Log-Head MKII 2, Skeleton MKII Screamer 1, Hazards Unit No-Head 1, Skeleton No-Head MkII  1, Skeleton No-Head MkI 1
- города (2): Sniper Tower[9], Barrier Tower[6]
- союзники после: Second Empire 100, Second Empire Exile 100, Ancient Ruins 100, Old Machines 70, Skeleton Sultans 70; враги после: Daemons -80, The Holy Nation -80, Cult of Fluorite -80, Lost Chaos Space Marines -80, World Devourer War Gang -80
- KMM-отношения: KMM_Behavior: Bloodraiders None->-26, White Eyebrow Clan None->-20, The Holy Nation None->-80, Oni None->-20 (+72)
- conductor: arch=robot, wealth=40, strength=32, ambition=survival, relic=None
- снаряжение: культура: Ancient Reinfoced Samurai Armor, Ancient Samurai Armour, Ancient Samurai Legplates, Ruined Samurai Armour, Ruined Samurai Legplates; носят: Ancient Samurai Armour 29, Ancient Samurai Legplates 28, Ancient Samurai Boots 18, Ruined Samurai Armour 18, Ancient Reinfoced Samurai Armor 18
- слои KMM: KMM_Behavior 1, KMM_Diplo 2, KMM_Economy 19, KMM_Glue 19, KMM_Wardrobe 15

### Flotsam Ninjas  `49377-rebirth.mod`
- создатель: rebirth.mod; тип: SLAVER; персонажей: 18, уников: 9
- уники: Digna, Flotsam Recruit, Former Slave, Knife, Mani, Moll, Pia, Reva, Yayoi
- лидеры: Mani, Yayoi
- расы фракции: Greenlander(200), Scorchlander(100), Shek(15), Greenlander Child(0), Scorchlander Child(0), Shek Child(0); фактические: Scorchlander 6, Greenlander 6
- города (13): Flotsam Village[holding], Flotsam Safehouse[holding], Scout Post[holding], Blister Hill (override) prosperous[2], Rebirth (override) takeover[1], Flotsam Camp[holding], Flotsam Raid Camp[holding], Flotsam Safehouse (override) Trade Ninjas[9], Flotsam War Camp[holding], Okran's Fist (override) flotsam[6], Rebel Base (override) flotsam[9], Pilgrim Pass (override) Prosperous[3], Meridin (override) flotsam[6]
- регионы: Arm of Okran, Bast, Cannibal Plains, Hidden Forest, Northern Coast, Okran's Gulf, Okran's Pride, Okran's Valley, Rebirth
- союзники после: Deadcat 100, Holy Nation Outlaws 100, Shinobi Thieves 100, Traders Guild 13; враги после: The Holy Nation -100, Cannibals -100, Raptors -100, Gnawed Bone Tribe -100, Charred Skull Tribe -100
- KMM-отношения: KMM_Behavior: Bloodraiders None->-7, Black Dragon Ninjas None->-15, White Eyebrow Clan None->-15, Oni None->-9 (+49)
- conductor: arch=settler, wealth=600, strength=129, ambition=revenge, relic=None
- снаряжение: культура: Tooth Pick, Flotsam Armor - Medium, Ranger, Flotsam Armor - Light, Flotsam Legplates; носят: Ninjato 65, Wooden Sandals 63, Drifter's Boots 60, Ranger 56, Dark Leather Shirt 55
- гардероб: uniforms:ninja
- банда outlaws: Flotsam Ninjas
- слои KMM: KMM_Atlas 8, KMM_Behavior 1, KMM_Diplo 2, KMM_Economy 17, KMM_Glue 16, KMM_Merged 3, KMM_Town 2, KMM_Wardrobe 11

### Old Machines  `42085-rebirth.mod`
- создатель: rebirth.mod; тип: MILITARY; скрыта в UI (реальна в мире); персонажей: 18, уников: 4
- уники: Grim, Spider Foreman, Spider Foreman Apprentice, Subordinate Failure
- лидеры: Sniperbot, Broken Skeleton, Broken ILA-M
- расы фракции: -; фактические: Skeleton No-Head MkII  5, Screamer MkI 3, Skeleton Log-Head MKII 2, Soldierbot 2, Skeleton P4MkII 2, Thrasher 2
- города (3): Spider Factory[4], Mining Factory (Empty)[4], Reapers Due[1]
- регионы: Floodlands
- союзники после: Second Empire 100, Ancient Ruins 100, Second Empire Exile 100, Soulbodies 100, Crystal Enemys 100; враги после: Daemons -80, The Holy Nation -80, Cult of Fluorite -80, Lost Chaos Space Marines -80, World Devourer War Gang -80
- KMM-отношения: KMM_Behavior: Bloodraiders None->-12, White Eyebrow Clan None->-25, The Holy Nation None->-80, Reavers None->-30 (+69)
- conductor: arch=robot, wealth=40, strength=32, ambition=survival, relic=None
- снаряжение: культура: Thrasher Harpoon, Ghillie Suit (Thornbush), Ghillie Suit (Twiggy Grass), Ghillie Suit (Yellow Grass), Ghillie Suit (Bulb Grass); носят: Eagle's Cross 3, Thrasher Harpoon 3, Skeleton Cleaver 3, Ghillie Suit (Thornbush) 2, Ghillie Suit (Twiggy Grass) 2
- слои KMM: KMM_Behavior 1, KMM_Diplo 1, KMM_Economy 11, KMM_Fix 1, KMM_Glue 11, KMM_Wardrobe 14

### Empire Peasants  `51646-Dialogue.mod`
- создатель: Dialogue.mod; тип: CIVILIAN; персонажей: 17, уников: 4
- уники: Ells, Flats, Rumina, Town Eccentric
- лидеры: Ells, Flats
- расы фракции: Greenlander(100), Hive Prince(20), Hive Soldier Drone(200), Hive Worker Drone(400), Shek(100), Scorchlander(10); фактические: Shek 3, Greenlander 2, Scorchlander 2, Deadhive Soldier 1, Hive Prince 1, Hive Worker Drone 1
- города (27): Vagrant Camp[holding], Empire Village[holding], Old Village[holding], Bark (override prosperous)[2], Drin (override) peasants[2], Heft (override) peasants[2], Heng (override) prosperous[2], Sho-Battai (override) prosperous[2], Trader's Edge (override) [2], Bark (override prosperous) 2[2], Clownsteady (override) prosperous[2], Port North (override) farm town[2], Port South (override) farm town[2], Slave Market (override) peasants[1], Cult town (override) destroyed[3], Bast (override) destroyed[4]
- союзники после: United Cities 100, Holy Nation Outlaws 100, Sultans Wares 25, Traders Guild 24, Guild of Surgeons 24; враги после: The Holy Nation -100, Daemons -80, Lost Chaos Space Marines -80, World Devourer War Gang -80, Midnight Lord -80
- KMM-отношения: KMM_Behavior: Bloodraiders None->-60, White Eyebrow Clan None->-60, Oni None->-60, Reavers None->-70 (+65)
- conductor: arch=state, wealth=330, strength=91, ambition=survival, relic=None
- снаряжение: культура: City Jacket, Farmers Long Sleeve Shirt, Farmers Long Pants, Farmers Long Pants Geared, Farmers Sleeveless Shirt; носят: Halfpants (ragged) 25, White Vest 24, Farmers Grass Sandal 22, Farmers Long Sleeve Shirt 22, Farmers Half Pants 21
- слои KMM: KMM_Atlas 15, KMM_Behavior 1, KMM_Economy 15, KMM_Fix 1, KMM_Glue 12, KMM_Merged 4, KMM_Town 5, KMM_Wardrobe 12

### Free Traders  `1229-gamedata.base`
- создатель: gamedata.base; тип: CIVILIAN; персонажей: 17, уников: 3
- уники: Harmothoe, Mould, Rust
- лидеры: Harmothoe
- расы фракции: Greenlander(70), Scorchlander(100), Shek(50), Hive Soldier Drone(10), Hive Prince(1), Hive Worker Drone(5); фактические: Greenlander 2, P4 Unit 1, Deadhive Worker 1
- города (3): Holy Mines (override) free traders[4], Slave Farm S (override) farm town[2], Drifter's Last (override) prosperous[2]
- союзники после: Police 100, United Cities 100, Swampers 100, Shek Kingdom 100, Holy Nation Outlaws 100; враги после: Daemons -80, Lost Chaos Space Marines -80, World Devourer War Gang -80, Midnight Lord -80, Hatred of intelligence -80
- KMM-отношения: KMM_Behavior: Bloodraiders None->-60, White Eyebrow Clan None->-60, Oni None->-60, Reavers None->-60 (+80)
- conductor: arch=trader, wealth=40, strength=25, ambition=revenge, relic=None
- снаряжение: культура: Traders Backpack Large, Farmers Trade Pack; носят: Ringed Sabre 22, Mercenary Plate 19, Strips of fabric (colored) 19, Jitte 16, Mercenary Cuirass 14
- слои KMM: KMM_Atlas 1, KMM_Behavior 1, KMM_Economy 28, KMM_Elite 1, KMM_Glue 14, KMM_Merged 5, KMM_Town 1, KMM_Wardrobe 14

### Holy Nation Outlaws  `42022-rebirth.mod`
- создатель: rebirth.mod; тип: CIVILIAN; персонажей: 16, уников: 7
- уники: Leander, Melinda, Patchwork, Smirk, Sword for hire Shek Outcast, Tongs, West Dragon
- лидеры: West Dragon
- расы фракции: Greenlander(100), Scorchlander(25); фактические: Greenlander 5, Scorchlander 5, Greenlander Child 2, Shek Child 1, Scorchlander Child 1, Shek 1
- города (16): The Hub[city], Bad Teeth (override) destroyed[2], Blister Hill (override) takeover[4], Rebirth (override) destroyed[4], Stack (override) outlaws[2], Holy Outlaw Camp[holding], Dragon's Den[holding], Outlaws' Refuge[holding], Dust King Tower (override) Outlaw takeover[9], Okran's Fist (override) outlaws[3], Okran's Shield (override) outlaws[2], The Hub (override) reversion[2], Tiny Settlement (override) squatters[4], Watchtower (override) destroyed[9], Meridin (override) outlaws[6], Skyscrap (ove
- регионы: Arm of Okran, Bast, Border Zone, Cannibal Plains, Dreg, Floodlands, Fog Islands, Hidden Forest, Northern Coast, Okran's Gulf, Okran's Pride, Okran's Valley, Sinkuun, Skimsands, Skinner's Roam, Spine Canyon, Vain, Wend
- союзники после: Deadcat 100, Flotsam Ninjas 100, Free Traders 100, Machinists 100, Mongrel 100; враги после: The Holy Nation -100, Dark Reavers -100, The Syndicate -100, Daemons -80, Lost Chaos Space Marines -80
- KMM-отношения: KMM_Behavior: Bloodraiders None->-22, White Eyebrow Clan None->-21, Oni None->-12, Reavers None->-39 (+49)
- conductor: arch=settler, wealth=420, strength=97, ambition=revenge, relic=None
- снаряжение: культура: Melinda's Naginata, Dyed Trousers; носят: Stout Hessian Uniform 25, Cloth Shirt 23, Dyed Trousers 23, Iron Club 22, Combat Cleaver 21
- гардероб: no_firearms
- банда outlaws: Holy Nation Outlaws
- Cleanup: лагеря [], хост ['The Hub', "Outlaws' Refuge"]
- слои KMM: KMM_Atlas 9, KMM_Behavior 1, KMM_Cleanup 1, KMM_Diplo 2, KMM_Economy 13, KMM_Elite 1, KMM_Fix 1, KMM_Glue 11, KMM_Merged 1, KMM_Town 1, KMM_Wardrobe 7

### Anti-Slavers  `58229-Dialogue.mod`
- создатель: Dialogue.mod; тип: ADVENTURER; персонажей: 15, уников: 7
- уники: Bo, Former Slave, Grey, Jaegar, Tinfist, _Freedom_Fighter, 阿尔乔姆
- лидеры: Bo, Jaegar
- расы фракции: Greenlander(100), Hive Prince(50), Hive Soldier Drone(50), Hive Worker Drone(50), Scorchlander(100), Shek(100); фактические: Scorchlander 2, Greenlander 2, Skeleton 1, Hive Prince 1
- города (4): Spring[city], The Free City[2], Trader's Edge (override) prosperous[1], Resort Island (override) anti-slavers[2]
- регионы: Stobe's Gamble
- союзники после: Rebirth Slaves 100, Slaves 100, Holy Nation Outlaws 100, Empire Peasants 70, Flotsam Ninjas 70; враги после: Cannibals -100, Dust Bandits -100, Manhunters -100, United Heroes League -100, Slave Hunters -100
- KMM-отношения: KMM_Behavior: Bloodraiders None->-60, White Eyebrow Clan None->-60, Oni None->-60, Band of Bones None->-70 (+60)
- conductor: arch=state, wealth=150, strength=69, ambition=revenge, relic=None
- снаряжение: культура: Tanegashima Rifle, Talon Armor MkIV, Flotsam Armor - Heavy, Jacket, Martial Artist Breastplate; носят: Drifter's Boots 33, Drifter's Leather Pants 32, Hachigane 30, Side-Angle Hachigane 30, Straw Hat 30
- слои KMM: KMM_Atlas 4, KMM_Behavior 1, KMM_Diplo 2, KMM_Economy 9, KMM_Glue 8, KMM_Merged 5, KMM_Town 2, KMM_Wardrobe 8

### Dark Hive  `5007286-Dark Hive.mod`
- создатель: Dark Hive.mod; тип: ADVENTURER; персонажей: 15, уников: 12
- уники: Ceiza, Crom, Dark Praetorian Beek, Dark Praetorian Feep, Doctor, Fasthand, Hashish, Solza, The Dark Queen, The Old Dog, Warlord Vawl, Warmaster Honk
- лидеры: The Dark Queen, Hashish, Fasthand, Solza, Crom
- расы фракции: Dark Hive Prince(10), Dark Hive Soldier Drone(100), Dark Hive Worker Drone(100), Dark Hive Praetorian(2), Dark Hive Queen(1); фактические: Dark Hive Worker Drone 5, Dark Hive Praetorian 4, Dark Hive Prince 4, Dark Hive Soldier Drone 3, Dark Hive Queen 1
- города (1): Strange Place[holding]
- регионы: The Iron Trail
- союзники после: -; враги после: Fogmen -200, The Holy Nation -200, Cannibals -100, Southern Hive -100, Daemons -80
- KMM-отношения: KMM_Behavior: Bloodraiders None->-15, White Eyebrow Clan None->-14, Oni None->-22, Reavers None->-40 (+53)
- conductor: arch=settler, wealth=150, strength=43, ambition=survival, relic=None
- снаряжение: культура: Blackened Chain Hive Shirt, Rupture Blade; носят: Blackened Chain Hive Shirt 14, Small Thieves Backpack 4, Eagle's Cross 4, Unholy Chest Plate 2, Razor Topper 2
- слои KMM: KMM_Atlas 1, KMM_Behavior 1, KMM_Diplo 4, KMM_Economy 15, KMM_Elite 3, KMM_Glue 14, KMM_Town 1, KMM_Wardrobe 3

### Dark Reavers  `5131014-Dark Hive.mod`
- создатель: Dark Hive.mod; тип: BANDIT; персонажей: 15, уников: 2
- уники: Malza, Vex
- лидеры: Dark Reaver Elite, Dark Reaver Scout Leader, Dark Reaver Scout Leader
- расы фракции: Dark Hive Prince(35), Dark Hive Soldier Drone(70), Dark Hive Worker Drone(100), Dark Hive Praetorian(1), Greenlander(25), Scorchlander(25); фактические: Dark Hive Worker Drone 8, Dark Hive Soldier Drone 8, Greenlander 6, Scorchlander 6, Dark Hive Prince 5, Dark Hive Praetorian 1
- города (5): Dark Reaver Tower[holding], Dark Reaver Camp[holding], Dark Reaver Scout Camp[holding], Supply Warehouse[holding], Dark Reaver Camp (BZ)[holding]
- регионы: Burning Forest, Fog Islands, Grey Desert, Heng, Leviathan Coast, Obedience, Shem, Stenn Desert, The Eye, The Great Desert, Vain
- союзники после: Raptors 3; враги после: Dark Hive -100, The Holy Nation -100, Holy Nation Outlaws -100, Mongrel -100, Cannibals -100
- KMM-отношения: KMM_Behavior: The Holy Nation None->-70, Reavers None->-24, Lost Warrior None->-40, Band of Bones None->-20 (+90)
- conductor: arch=bandit, wealth=510, strength=87, ambition=enrichment, relic=None
- снаряжение: культура: Dark Samurai Armour, Dark Samurai Legplates; носят: Plated Drifter's Leather Pants 11, Leather Hive Vest 8, Blackened Chainmail Tagelmust 8, Fragment Cleaver 8, Fragment Polearm 8
- банда outlaws: Dark Reavers
- слои KMM: KMM_Behavior 1, KMM_Economy 15, KMM_Glue 16, KMM_Wardrobe 13

### Midnight Lord  `3152-TEXT TEXTURE.mod`
- создатель: TEXT TEXTURE.mod; тип: MILITARY; персонажей: 15, уников: 3
- уники: Midnight Lord - Apothecary Dacher, Midnight Lord - Karl, Midnight Lord - Zoran the Blasphemer
- лидеры: Midnight Lord - Zoran the Blasphemer, Midnight Lord - Karl
- расы фракции: -; фактические: Astartes (Special Gene Seed) 11, Flayed Man 4
- города (1): Human Research Institute[holding]
- союзники после: World Devourer War Gang 60, Daemons 60, Lost Chaos Space Marines 60, Hatred of intelligence 60; враги после: United Cities -100, Shek Kingdom -100, The Holy Nation -100, Nameless -100, Astartes survivors -100
- KMM-отношения: KMM_Behavior: Bloodraiders None->-36, White Eyebrow Clan None->-30, Reavers None->-50, Police None->-80 (+121) | KMM_Glue: 1-KMM_Glue.mod None->-100
- conductor: arch=chaos, wealth=350, strength=85, ambition=faith, relic=spread_chaos
- снаряжение: культура: -; носят: Midnight Lord - Power Leg Armor 9, Midnight Lord - Power Combat Boots 9, Elite Power Armor Liner 7, Midnight Lord - Power Armor (Molecular Rivets) 6, Midnight Lord - MK6 Power Helmet 5
- гардероб: power_armor
- слои KMM: KMM_Behavior 1, KMM_Diplo 3, KMM_Economy 11, KMM_Glue 12, KMM_Wardrobe 9

### Shinobi Thieves  `14491-rebirth.mod`
- создатель: rebirth.mod; тип: TRADER; персонажей: 15, уников: 0
- лидеры: Thief, Thief Boss, Shinobi Smuggler
- расы фракции: Greenlander(90), Hive Prince(30), Hive Soldier Drone(5), Hive Worker Drone(30), Scorchlander(200), Dark Hive Prince(9); фактические: Greenlander Child 1, Scorchlander Child 1
- города (2): Rent Shinobi Post[holding], Tower Of Ninjas (override) thieves[9]
- регионы: Bonefields, Flats Lagoon, Heng, Skimsands, Spider Plains, The Great Desert, The Hook, The Outlands, The Swamp
- союзники после: Holy Nation Outlaws 100, Bar Thugs 100, Blackshifters 100, Deadcat 100, Drifters 100; враги после: Police -70, Cult of Fluorite -70, Missionaries -70, The Holy Nation -70, Preacher Cult -70
- KMM-отношения: KMM_Behavior: The Holy Nation None->-70, Dark Hive None->-15, Reavers None->-20, Lost Warrior None->-41 (+77)
- conductor: arch=bandit, wealth=150, strength=61, ambition=enrichment, relic=None
- снаряжение: культура: Tsume Pants MkI, Clothpants - Heavy, Thieves Backpack, Ninja Clothpants, Small Thieves Backpack; носят: Ninjato 68, Martial Artist Bindings 57, Drifter's Boots 51, Turtleneck 51, Simple Katana 50
- гардероб: uniforms:ninja
- банда outlaws: Shinobi Thieves
- слои KMM: KMM_Atlas 2, KMM_Behavior 1, KMM_Economy 14, KMM_Glue 12, KMM_Merged 6, KMM_Town 1, KMM_Wardrobe 15

### Crab Raiders  `62806-rebirth.mod`
- создатель: rebirth.mod; тип: BANDIT; персонажей: 13, уников: 3
- уники: Crab Queen, Lobster, Snip-Snap
- лидеры: Crab Queen
- расы фракции: Scorchlander(100), Scorchlander Child(0), Skeleton(1); фактические: Scorchlander 3, Scorchlander Child 1
- города (7): Crab Village[holding], Crab Town[city], Ark (override) takover[1], Crab Village (override) destroyed[4], Dusty's Domain[holding], Dusty's Domain (ruined)[1], Crab Sanctum[9]
- регионы: Stobe's Garden, The Pits East
- союзники после: Crabs 100, Kral's Chosen 25, Band of Bones 25, Charred Skull Tribe 24, Berserkers 23; враги после: Skeleton Bandits -100, Reavers -100, United Cities -100, Skin Bandits -100, The Holy Nation -80
- KMM-отношения: KMM_Behavior: Bloodraiders None->-27, White Eyebrow Clan None->-18, Lost Warrior None->-60, Police None->-70 (+131)
- conductor: arch=savage, wealth=420, strength=103, ambition=enrichment, relic=None
- снаряжение: культура: Crab Armour, Crab Trousers, Crab Helmet, Elite Crab Helmet; носят: Naginata 31, Naginata Katana 29, Crab Helmet 25, Crab Shoes 25, Rusty Chain Shirt 24
- Cleanup: лагеря ['Crab Sanctum'], хост []
- слои KMM: KMM_Atlas 2, KMM_Behavior 1, KMM_Cleanup 2, KMM_Diplo 2, KMM_Economy 22, KMM_Elite 2, KMM_Fix 1, KMM_Glue 14, KMM_Merged 1, KMM_Town 3, KMM_Wardrobe 10

### Greenskins  `840011-OrcRaceReview.mod`
- создатель: OrcRaceReview.mod; тип: CIVILIAN; персонажей: 13, уников: 2
- уники: Grimgor, The Prophet
- лидеры: Orc Big 'Un
- расы фракции: -; фактические: Orc 12, Greenlander 1
- города (1): Gork's Throne[city]
- регионы: Skinner's Roam
- союзники после: -; враги после: The Holy Nation -100, Astartes survivors -100, The Lost Black Sanctuary -100, Death Watch -100, Grey Knight -100
- KMM-отношения: KMM_Behavior: Bloodraiders None->-30, White Eyebrow Clan None->-25, Reavers None->-20, Lost Warrior None->-100 (+134) | KMM_Glue: 1-KMM_Glue.mod None->-80
- conductor: arch=xeno, wealth=150, strength=33, ambition=expansion, relic=None
- снаряжение: культура: -; носят: Orc Tuskplate 4, Orc Riveted Waistguard 4, Orc Iron Shinguards 4, Knuckleguard Choppa 4, Tusk Captain's Plate 2
- банда outlaws: Greenskins
- слои KMM: KMM_Atlas 1, KMM_Behavior 1, KMM_Economy 14, KMM_Glue 14, KMM_Merged 17, KMM_Relics 1, KMM_Wardrobe 11

### Mercenary Guild  `1214-gamedata.base`
- создатель: gamedata.base; тип: MILITARY; персонажей: 13, уников: 1
- уники: Wrath
- лидеры: Mercenary Captain, Captain, Human Mercenary Captain
- расы фракции: Greenlander(100), Shek(60), Dark Hive Soldier Drone(5), Dark Hive Worker Drone(1), Dark Hive Prince(2), Hive Soldier Drone(60); фактические: Greenlander 4, Scorchlander 3, Enforcer 3, Hive Prince South Hive 1
- города (5): Mercenary base[holding], Mercenary Camp[holding], Manhunter Base (override)[4], Ruined Holy Outpost (override) mercenary[4], Settled Nomads (override) destroyed[1]
- союзники после: Holy Nation Outlaws 100, Shinobi Thieves 100, The Holy Nation 100, Shek Kingdom 100, United Cities 100; враги после: Daemons -80, Lost Chaos Space Marines -80, World Devourer War Gang -80, Midnight Lord -80, Hatred of intelligence -80
- KMM-отношения: KMM_Behavior: Bloodraiders None->-60, White Eyebrow Clan None->-60, Oni None->-60, Reavers None->-70 (+63)
- conductor: arch=state, wealth=240, strength=59, ambition=expansion, relic=None
- снаряжение: культура: Mercenary Dō Armour with Sleeves, BH (Heavy) Metal, Mercenary Dō Armour with Left Sleeve, Mercenary Dō Armour with Right Sleeve, Mercenary Dō Armour; носят: Mercenary Leather Armour 16, Mercenary Club 16, Mercenary Leg Plates Heavy 14, Mercenary Suneate Boots 14, BH (Heavy) Metal 12
- слои KMM: KMM_Atlas 2, KMM_Behavior 1, KMM_Diplo 1, KMM_Economy 13, KMM_Glue 12, KMM_Town 4, KMM_Wardrobe 12

### Second Empire  `49356-rebirth.mod`
- создатель: rebirth.mod; тип: CIVILIAN; скрыта в UI (реальна в мире); персонажей: 13, уников: 10
- уники: General Hat-12, General Jang, Head of Agriculture, Head of Technology, Immortal King, Mining Foreman, Rhinobot, Second Empire Ronin, Sovereign, Weapons Foreman
- лидеры: Sovereign, Second Empire Ronin
- расы фракции: -; фактические: Skeleton P4MkII 7, Skeleton Log-Head MKII 2, Skeleton 1, Greenlander 1, P4 Unit 1, Hazards Unit Oni 1
- города (25): Empty Ruin[9], Archive Town[4], Looted Ruins[4], Lost Armoury[4], Lost Library[4], Old Empire Watchtower[4], Armoury Ruin[4], Library Ruins[4], Lost Library Outpost[4], Old Empire Supply Outpost[4], Lost Armour Store[4], Ashland Dome III[4], Dead Fishing Village[3], Police Barracks[4], The Forgotten Throne[4], Ashland Dome I[4], Ashland Dome II[4], Ashland Dome IV[4], Looted Ruins (override) ruined[4], Mining Factory[4], Ashland Outpost[4], Skeleton Ronin's Tower[9], Legendary Katana Statue[4], 
- регионы: Ashlands, Leviathan Coast, The Pits
- союзники после: Old Machines 100, Skeleton Legion 100, Second Empire Exile 100, Ancient Ruins 100, Soulbodies 100; враги после: Daemons -80, Lost Chaos Space Marines -80, World Devourer War Gang -80, Midnight Lord -80, Hatred of intelligence -80
- KMM-отношения: KMM_Behavior: Bloodraiders None->-60, White Eyebrow Clan None->-60, Oni None->-60, Reavers None->-70 (+71)
- conductor: arch=state, wealth=90, strength=36, ambition=survival, relic=None
- снаряжение: культура: Industrial Blade, Norimitsu Odachi; носят: Ancient Samurai Legplates 3, Prisoner Shackles 1, Ancient Samurai Boots 1, Empire Samurai Armour 1, Ruined Samurai Armour 1
- слои KMM: KMM_Behavior 1, KMM_Diplo 2, KMM_Economy 15, KMM_Fix 15, KMM_Glue 11, KMM_Merged 2, KMM_Wardrobe 3

### Deadcat  `513-gamedata.base`
- создатель: gamedata.base; тип: CIVILIAN; персонажей: 12, уников: 5
- уники: Hikari, Horse, Mosswood, Soman, Suspicious Settler
- лидеры: Hikari, Mosswood
- расы фракции: Greenlander(100), Shek(50), Scorchlander(200), Hive Prince(10), Hive Prince South Hive(5), Hive Soldier Drone(20); фактические: Scorchlander 1, Cannibal Skav 1, Greenlander Child 1, Scorchlander Child 1, Greenlander 1, Shek 1
- города (8): Fishing Village[holding], Gatherer Village[holding], Old Village[holding], Ghost Village[holding], Cannibal Capital (override) Deadcat[2], Ghost Village (override) Deadcat[3], Refugee Camp[holding], Gatherer Village (Good Ending)[3]
- регионы: Dreg, Northern Coast
- союзники после: Holy Nation Outlaws 100, Shinobi Thieves 100, Empire Peasants 50, Cannibal Hunters 50, Tech Hunters 32; враги после: Cannibals -100, Grass Pirates -100, Gnawed Bone Tribe -100, Charred Skull Tribe -100, Blood Butcher Tribe -100
- KMM-отношения: KMM_Behavior: Bloodraiders None->-19, Black Dragon Ninjas None->-13, White Eyebrow Clan None->-15, Oni None->-15 (+48)
- conductor: arch=settler, wealth=510, strength=93, ambition=survival, relic=None
- снаряжение: культура: Farmer Machete, Farmer Axe, Farmers Pitchfork, Farmers Rake, Farmer Stick Scythe; носят: Hachigane 10, Side-Angle Hachigane 10, Leather Turtleneck 8, Swamp Ninja Mask 2, Barbed Harpoon 2
- слои KMM: KMM_Atlas 2, KMM_Behavior 1, KMM_Economy 14, KMM_Fix 1, KMM_Glue 10, KMM_Merged 1, KMM_Town 1, KMM_Wardrobe 7

### Mongrel  `18891-rebirth.mod`
- создатель: rebirth.mod; тип: ADVENTURER; персонажей: 12, уников: 5
- уники: Arc, Fogmen Hunter Rovan, Infinite Wingwang, Kaeru, Meipan
- лидеры: Arc, Kaeru
- расы фракции: Hive Prince(10), Greenlander(150), Shek(60), Skeleton(4), Hive Soldier Drone(60), Hive Worker Drone(30); фактические: Greenlander 4, Deadhive Soldier 1, Hive Prince 1
- города (2): Mongrel[city], Camp- Fog Hunters[holding]
- регионы: Fog Islands
- союзники после: Tech Hunters 100, Holy Nation Outlaws 100, Shinobi Thieves 100, Flotsam Ninjas 100, Drifters 100; враги после: The Holy Nation -100, Dark Reavers -100, Fogmen -100, Slave Traders -100, Daemons -80
- KMM-отношения: KMM_Behavior: Bloodraiders None->-15, White Eyebrow Clan None->-15, Oni None->-13, Reavers None->-40 (+50)
- conductor: arch=settler, wealth=240, strength=59, ambition=survival, relic=None
- снаряжение: культура: Undertaker's apron(hive), Undertaker's pants (Hive), Fog Mask (Mouth Only), Undertaker's Mask(prince), Mask Type III (Mouth Only); носят: Blackened Chain Shirt 12, Leather Hive Vest 8, Fog Mask 7, Padded Shirt 4, Northern Hood 4
- Cleanup: лагеря [], хост ['Mongrel']
- слои KMM: KMM_Atlas 2, KMM_Behavior 1, KMM_Cleanup 1, KMM_Diplo 2, KMM_Economy 11, KMM_Elite 1, KMM_Glue 10, KMM_Merged 1, KMM_Town 2, KMM_Wardrobe 7

### Shem Residents  `5007298-Town of Shem.mod`
- создатель: Town of Shem.mod; тип: CIVILIAN; персонажей: 12, уников: 0
- лидеры: Shem Caravan Leader, Shem Pacifier
- расы фракции: Greenlander(100), Scorchlander(30), Hive Worker Drone(40), Shek(20), Hive Soldier Drone(25), Hive Prince(5); фактические: Hive Worker Drone 1, Shek 1, Greenlander 1, Scorchlander 1
- города (1): Sukui[city]
- регионы: Shem
- союзники после: Guild of Surgeons 100, Nomads 75, Tech Hunters 70, Imperial Bank 28, The Holy Nation 20; враги после: Gutters -100, Daemons -80, Lost Chaos Space Marines -80, World Devourer War Gang -80, Midnight Lord -80
- KMM-отношения: KMM_Behavior: Bloodraiders None->-60, White Eyebrow Clan None->-60, Oni None->-60, Reavers None->-70 (+66)
- conductor: arch=state, wealth=150, strength=31, ambition=survival, relic=None
- снаряжение: культура: -; носят: White Plate Jacket 2, Thieves Backpack 1
- Cleanup: лагеря [], хост ['Sukui']
- слои KMM: KMM_Atlas 1, KMM_Behavior 1, KMM_Diplo 1, KMM_Economy 12, KMM_Glue 11, KMM_Town 1, KMM_Wardrobe 12

### Soulbodies  `5007288-Soulbody.mod`
- создатель: Soulbody.mod; тип: NONE; скрыта в UI (реальна в мире); персонажей: 12, уников: 0
- расы фракции: Soul Hive Prince(20), Soul Hive Soldier Drone(25), Soul Hive Worker(25), Greenlander Soul(100), Shek Soul(80); фактические: Greenlander Soul 10, Soul Hive Prince 9, Soul Hive Worker 9, Soul Hive Soldier Drone 9, Shek Soul 9
- города (2): Crystal Spawn purple[0], Crystal Spawn red[0]
- союзники после: Cannibals 100, Fishmen 100, Fogmen 100, Gutters 100, Old Machines 100; враги после: Crystal Hive -100, Broken Crystal Relics -100, Crystal Relics -100
- снаряжение: культура: Barrier to the soul, Crystal Shred Shooter High, Crystal Shred Shooter Low, Crystal Great Sword, Crystal Rose; носят: Crystal Great Sword 6, Crystal Rose 6, Crystal Shred Shooter High 4, Crystal Shred Shooter Low 4, Barrier to the soul 1
- слои KMM: KMM_Glue 1, KMM_Wardrobe 12

### Levi Ronin  `11-The Leviathan Ronin.mod`
- создатель: The Leviathan Ronin.mod; тип: CIVILIAN; персонажей: 11, уников: 3
- уники: Eisarn, Hairusa, Jean
- лидеры: Jean
- расы фракции: Greenlander(40), Scorchlander(40), Enforcer(5), Shek(15); фактические: Enforcer 2
- города (5): Hilt[city], Ronin Outpost[holding], Fluorite (Levi)[2], Airnagard (Levi)[6], Mining Factory (Levi)[4]
- регионы: Leviathan Coast
- союзники после: Cult of Fluorite 100, Shek Kingdom 100, Anti-Slavers 100, Flotsam Ninjas 100, Tech Hunters 100; враги после: United Cities -100, Traders Guild -100, Slave Hunters -100, Slave Traders -100, Manhunters -100
- KMM-отношения: KMM_Behavior: Bloodraiders None->-8, White Eyebrow Clan None->-19, Oni None->-7, Reavers None->-40 (+51)
- conductor: arch=settler, wealth=240, strength=63, ambition=survival, relic=None
- снаряжение: культура: Harpoon Gun, Heavy Samurai Armour, Scout Samurai Armour, Samurai Clothpants [sneaky chain], Kettle Bevor; носят: Casted Mace 34, Chainmail 26, Samurai Legplates 26, Kettle Bevor 16, Heavy Samurai Armour 16
- слои KMM: KMM_Atlas 2, KMM_Behavior 1, KMM_Diplo 1, KMM_Economy 5, KMM_Elite 1, KMM_Glue 2, KMM_Wardrobe 9

### No Faction  `nofac`
- создатель: ?; тип: NONE; скрыта в UI (реальна в мире); персонажей: 11, уников: 3
- уники: Aida, Gillda, Valda
- лидеры: Aida
- расы фракции: -; фактические: Hive Worker Drone 1, Greenlander 1, Scorchlander 1, Fishman 1
- города (7): Fallen Tower[4], Nowhere[10], Port North (override) destroyed[4], Noatun (over)[4], Fluorite (destroyed)[2], Hilt (destroyed)[2], Airnagard (destroyed)[2]
- союзники после: -; враги после: -
- снаряжение: культура: Hakama Trousers Blue Geared, Hakama Trousers Grey Geared, Hakama Trousers Yellow Geared; носят: Desert Ninja Rags  2, Skimmer Antennae Mask 2, Skimmer Armour 2, Skimmer Mask 2, Skimmer Pants 2
- слои KMM: KMM_Atlas 1, KMM_Economy 9, KMM_Fix 1, KMM_Glue 5, KMM_Merged 2, KMM_Wardrobe 8

### Nomads  `42097-rebirth.mod`
- создатель: rebirth.mod; тип: CIVILIAN; персонажей: 11, уников: 1
- уники: Goat Man
- лидеры: Nomad Animal Trader, Nomad, Nomad Animal Trader Town
- расы фракции: Greenlander(100), Scorchlander(20); фактические: Greenlander Child 1, Scorchlander Child 1, Scorchlander 1
- города (6): Settled Nomads[holding], Goat Herder's Camp[holding], Nomads[holding], Settled Nomad Village[holding], First Village (override) nomads[3], Goat Herder's Camp[holding]
- регионы: Dreg, Shem
- союзники после: Holy Nation Outlaws 100, Shinobi Thieves 100, The Holy Nation 100, Shek Kingdom 100, Mongrel 100; враги после: Cannibals -100, Gnawed Bone Tribe -100, Charred Skull Tribe -100, Blood Butcher Tribe -100, Daemons -80
- KMM-отношения: KMM_Behavior: Bloodraiders None->-15, White Eyebrow Clan None->-15, Oni None->-14, Reavers None->-42 (+51)
- conductor: arch=settler, wealth=510, strength=137, ambition=survival, relic=None
- снаряжение: культура: Dustcoat, Dust Leather Shawl, Animal Skin Shawl, Cloth Shawl, Garruhide Pants; носят: Rag Shirt 61, Stout Hessian 61, Cloth Shirt 61, Tagelmust 61, Staff 61
- гардероб: pagan
- слои KMM: KMM_Atlas 1, KMM_Behavior 1, KMM_Diplo 1, KMM_Economy 34, KMM_Glue 11, KMM_Town 2, KMM_Wardrobe 9

### Fogmen  `18893-rebirth.mod`
- создатель: rebirth.mod; тип: BANDIT; скрыта в UI (реальна в мире); персонажей: 10, уников: 4
- уники: Fog Brute, Fog Brute, Fog King, Fogmaster
- лидеры: Fog Brute, Fogmaster
- расы фракции: Deadhive Worker(100); фактические: Deadhive Soldier 4, Deadhive Prince 3, Deadhive Worker 2, Deadhive Praetorian 1
- города (17): Fog Deathyard[0], Deadhive Overrun[4], Tower of Fog[9], Fog Deathyard Invasion[0], Deadhive Overrun West (override)[4], Deadhive Overrun South (override)[4], Fogman Nest Invasion[0], Holy Military Base (override) Deadhive[4], Dark Reaver Tower (over fog 1)[9], Dark Reaver Tower (over fog 2)[9], Dark Reaver Tower (over fog 3)[9], The Fog Kings Throne[9], The Fog Kings Throne (override)[9], Mongrel (override) deadhive overrun[4], Dreg Villages (override) Deadhive[4], Pale Hill (override) deadhive[
- регионы: Fog Islands, Okran's Gulf, Vain
- союзники после: Tyrants 100, Soulbodies 100, Crystal Enemys 100, Mist Creatures 75, Berserkers 26; враги после: The Holy Nation -80, Cult of Fluorite -80, Missionaries -80, The Holy Nation -80, Preacher Cult -80
- KMM-отношения: KMM_Behavior: Bloodraiders None->-20, White Eyebrow Clan None->-19, Reavers None->20, Lost Warrior None->-60 (+135)
- conductor: arch=savage, wealth=40, strength=28, ambition=expansion, relic=None
- снаряжение: культура: Human Bone Armor, Bone Leggings, Bizarre Bone Sword, Human Rib Cage, Bizarre Bone Club; носят: Human Rib Cage 38, Bone Bundle 38, Scrap Iron Blade 30, Armoured Rag Skirt 25, Armoured Hood 25
- гардероб: pagan, savage
- слои KMM: KMM_Atlas 1, KMM_Behavior 1, KMM_Diplo 1, KMM_Economy 11, KMM_Fix 1, KMM_Glue 10, KMM_Wardrobe 6

### Crystal Relics  `5008121-Soulbody.mod`
- создатель: Soulbody.mod; тип: CIVILIAN; персонажей: 9, уников: 1
- уники: Crystal Seeker
- лидеры: Crystal Guardian, Crystal Guardian MkII, Crystal Guardian M
- расы фракции: Crystal Golem Skeleton(100), Crystal Guardian Skeleton(100), Soul Hive Prince(100), Soul Hive Soldier Drone(100), Soul Hive Worker(100), Greenlander Soul(100); фактические: Crystal Guardian Skeleton 5, Crystal Golem Skeleton 2, Crystal Guardian Skeleton M 1, Crystal Golem Skeleton M 1
- города (1): Crystal City[city]
- регионы: The Crater
- союзники после: Crystal Hive 2; враги после: Broken Crystal Relics -100, Soulbodies -100
- KMM-отношения: KMM_Behavior: Crystal Hive 0->2
- conductor: arch=settler, wealth=150, strength=37, ambition=survival, relic=None
- снаряжение: культура: SS-C Low, SS-C High, Soul Metal Crusher, Soul Great Sword, Soul Dual Cleaver; носят: Soul Blade Katana 5, Soul Long Baton 5, Soul Great Sword 5, Soul Blade Nodachi 5, Soul Dual Cleaver 5
- слои KMM: KMM_Behavior 1, KMM_Economy 3, KMM_Fix 5, KMM_Glue 2, KMM_Wardrobe 8

### The Lost Black Sanctuary  `227-TEXT TEXTURE.mod`
- создатель: TEXT TEXTURE.mod; тип: MILITARY; скрыта в UI (реальна в мире); персонажей: 9, уников: 3
- уники: Black Templar - Paladin Eckhart, Black Templar Mighty Man - Emperor Champion, Imperial Fist - Enmu
- лидеры: Black Templar - Paladin Eckhart
- расы фракции: -; фактические: Astartes (Elite) 2, Astartes (The Lost) 1
- города (1): Black Sanctuary Camp[1]
- союзники после: Astartes survivors 80, Death Watch 80, Grey Knight 80, Lost Warrior 80, Cult of Fluorite 18; враги после: Nameless -100, Lost Chaos Space Marines -100, United Cities -100, Shek Kingdom -100, The Holy Nation -100
- KMM-отношения: KMM_Behavior: Bloodraiders None->-40, White Eyebrow Clan None->-40, Reavers None->-60, Lost Warrior None->80 (+130)
- conductor: arch=imperium, wealth=60, strength=40, ambition=faith, relic=hunt_xenos
- снаряжение: культура: -; носят: Power armor liner 7, Vikulamu Expedition 7, Black Templar - Power Backpack 7, Black Templar - Power Armor 7, Black Templar - Power Combat Boots 6
- гардероб: power_armor
- слои KMM: KMM_Behavior 1, KMM_Diplo 2, KMM_Economy 9, KMM_Glue 10, KMM_Wardrobe 6

### Trade Ninjas  `40551-rebirth.mod`
- создатель: rebirth.mod; тип: TRADER; персонажей: 9, уников: 1
- уники: Beep trader
- лидеры: Beep trader
- расы фракции: Greenlander(400), Scorchlander(200), Hive Prince(25), Shek(150), Hive Prince South Hive(10), Hive Soldier Drone(40); фактические: Greenlander 2, Scorchlander 1, Hive Worker Drone 1
- города (1): Rebel Base[holding]
- регионы: Border Zone, Flats Lagoon
- союзники после: Holy Nation Outlaws 100, Shinobi Thieves 100, Traders Guild 33, Sultans Wares 32, United Heroes League 26; враги после: Daemons -80, Lost Chaos Space Marines -80, World Devourer War Gang -80, Midnight Lord -80, Hatred of intelligence -80
- KMM-отношения: KMM_Behavior: Bloodraiders None->-60, White Eyebrow Clan None->-60, Oni None->-60, Reavers None->-60 (+83)
- conductor: arch=trader, wealth=150, strength=55, ambition=enrichment, relic=None
- снаряжение: культура: Padded Shirt, Pointed Leather Boots, Tall Socks; носят: Dark Leather Shirt 13, Cargopants [sneaky chain] 11, Ninja Pants 11, Black Bandana 11, Northern Jacket 11
- гардероб: uniforms:ninja
- банда outlaws: Trade Ninjas
- слои KMM: KMM_Atlas 1, KMM_Behavior 1, KMM_Economy 14, KMM_Glue 6, KMM_Merged 6, KMM_Wardrobe 8

### Bar Thugs  `1534558-rebirth.mod`
- создатель: rebirth.mod; тип: ADVENTURER; скрыта в UI (реальна в мире); персонажей: 8, уников: 0
- расы фракции: -; фактические: Greenlander 1
- союзники после: Holy Nation Outlaws 100, Shinobi Thieves 100; враги после: The Holy Nation -70, Cult of Fluorite -70, Missionaries -70, The Holy Nation -70, Preacher Cult -70
- KMM-отношения: KMM_Behavior: The Holy Nation None->-70, Dark Hive None->-15, Reavers None->-20, Lost Warrior None->-40 (+98)
- conductor: arch=bandit, wealth=60, strength=34, ambition=enrichment, relic=None
- снаряжение: культура: -; носят: Unholy Bucket Zukin 2, Padded Shirt 2, Duster 2, Iron Dome 2, Wanderer's Tabard 1
- слои KMM: KMM_Behavior 1, KMM_Economy 6, KMM_Glue 6, KMM_Town 6, KMM_Wardrobe 8

### Drug Peddlers  `1536625-Bounties Galore.mod`
- создатель: Bounties Galore.mod; тип: TRADER; персонажей: 8, уников: 3
- уники: Gryf, Nyahn, Seraph
- лидеры: Gryf
- расы фракции: Greenlander(30), Hive Prince(5), Hive Soldier Drone(5), Hive Worker Drone(20), Scorchlander(25), Skeleton(5); фактические: Greenlander 4, Scorchlander 4, Hive Worker Drone 3, Shek 2, Skeleton 2, Hive Prince 2
- города (1): Gryfs Drug Farm[holding]
- регионы: Border Zone, Dreg, Flats Lagoon, South Wetlands, The Hook, The Swamp, Vain
- союзники после: Grayflayers 100, Tech Hunters 100, cloak shop(test) 32, Iron Company 27, Anti-Slavers 27; враги после: Daemons -80, Lost Chaos Space Marines -80, World Devourer War Gang -80, Midnight Lord -80, Hatred of intelligence -80
- KMM-отношения: KMM_Behavior: Bloodraiders None->-60, White Eyebrow Clan None->-60, Oni None->-60, Reavers None->-60 (+83)
- conductor: arch=trader, wealth=150, strength=41, ambition=enrichment, relic=None
- снаряжение: культура: Sickle; носят: Cargopants [sneaky chain] 10, Cargopants [reinforced] 10, Ashland Hat 2, Foreign Axe 2, Mercenary Dō Armour 1
- банда outlaws: Drug Peddlers
- слои KMM: KMM_Atlas 1, KMM_Behavior 1, KMM_Diplo 1, KMM_Economy 10, KMM_Elite 1, KMM_Glue 7, KMM_Town 1, KMM_Wardrobe 5

### Grayflayers  `48791-Dialogue.mod`
- создатель: Dialogue.mod; тип: CIVILIAN; персонажей: 8, уников: 3
- уники: Big Gray, Ilya, Kimura
- лидеры: Big Gray, Kimura
- расы фракции: Greenlander(100), Hive Prince(50), Shek(100), Scorchlander(100), Dark Hive Prince(25), Dark Hive Soldier Drone(15); фактические: Greenlander 4, Hive Prince 3, Shek 2, Scorchlander 2, Skeleton KLR-M MKII 1, P4 Unit 1
- города (7): Grayflayer Village[holding], Smugglers Bar[holding], Shark (override) Grayflayer[2], Red Sabre Hideout (override) grayflayers[9], Rot (override) grayflayers[3], Swamp Ninja Base (override) grayflayers[9], White Eyebrow Tower (override) Grayflayers[9]
- регионы: Shem, The Swamp
- союзники после: Swampers 100, Holy Nation Outlaws 100, Shinobi Thieves 100; враги после: Raptors -100, Spiders -100, Daemons -80, Lost Chaos Space Marines -80, World Devourer War Gang -80
- KMM-отношения: KMM_Behavior: Bloodraiders None->-7, Black Dragon Ninjas None->-15, White Eyebrow Clan None->-13, Oni None->-15 (+53)
- conductor: arch=settler, wealth=240, strength=61, ambition=survival, relic=None
- снаряжение: культура: Iron Hat with Hair, Tabi Boots, Desert Sabre; носят: Rattan Hat 22, Desert Sabre 21, Ninjato 19, Guardless Katana 18, Ninja Gi 16
- Cleanup: лагеря [], хост ['Smugglers Bar']
- слои KMM: KMM_Atlas 5, KMM_Behavior 1, KMM_Cleanup 1, KMM_Diplo 1, KMM_Economy 9, KMM_Elite 1, KMM_Glue 6, KMM_Wardrobe 5

### Machinists  `50358-rebirth.mod`
- создатель: rebirth.mod; тип: CIVILIAN; персонажей: 8, уников: 4
- уники: Errol, Finch, Iyo, The Lore Keeper
- лидеры: Finch
- расы фракции: Greenlander(100), Hive Prince(20), Scorchlander(100), Shek(5), Skeleton(10), Skeleton SL-M MKIII(20); фактические: Hive Prince 1, Shek 1, P4 Unit 1, Greenlander 1
- города (1): Errol's Workshop[4]
- союзники после: Tech Hunters 100, Holy Nation Outlaws 100, Desert Divers 100, Shinobi Thieves 100, Mercenary Guild 100; враги после: Daemons -80, Cult of Fluorite -80, Lost Chaos Space Marines -80, World Devourer War Gang -80, Missionaries -80
- KMM-отношения: KMM_Behavior: Bloodraiders None->-20, White Eyebrow Clan None->-15, The Holy Nation None->-80, Oni None->-24 (+71)
- conductor: arch=robot, wealth=150, strength=49, ambition=survival, relic=None
- снаряжение: культура: Ceremonial Greatblade; носят: Old World Raimant 8, Gi Pants 2, Monk Pants 1, Shopkeeper goods bag 1, Armoured Longcoat 1
- Cleanup: лагеря ["Errol's Workshop"], хост []
- слои KMM: KMM_Behavior 1, KMM_Cleanup 1, KMM_Diplo 3, KMM_Economy 11, KMM_Elite 1, KMM_Glue 6, KMM_Merged 1, KMM_Town 2, KMM_Wardrobe 4

### Mist Creatures  `1535107-Mist Ghouls.mod`
- создатель: Mist Ghouls.mod; тип: BANDIT; скрыта в UI (реальна в мире); персонажей: 8, уников: 3
- уники: Mad Cat-Lon, Mist Guardian Elite, Mother of the Mist
- лидеры: Mother of the Mist
- расы фракции: Zombie MistGhoul(100); фактические: Zombie MistHorror 3, Zombie MistGhoul 1, Zombie MistFiend 1, Hive Prince 1, Skeleton P4MkII 1, Zombie MistMother 1
- города (2): Mist Boneyard[0], Tower of Mist[4]
- союзники после: Tyrants 100, Fogmen 75; враги после: -
- снаряжение: культура: Iron Fortress Chestguard, Iron Fortress Waistguard, Twilight Cloak, Mother's Lament, Forked Cleaver; носят: Forked Cleaver 17, Flesh Cleaver 11, Moon Cleaver 5, Paladin's Heavy Hachigane 1, Holy Chest Plate 1
- слои KMM: KMM_Diplo 2, KMM_Economy 7, KMM_Elite 1, KMM_Glue 7, KMM_Wardrobe 4

### Poachers  `13-BBgoatsBeastforge_worldadditions.mod`
- создатель: BBgoatsBeastforge_worldadditions.mod; тип: CIVILIAN; персонажей: 8, уников: 0
- лидеры: Hunter Tracker, Hunter Tracker, Leviathan Hunter
- расы фракции: Shek(100), Greenlander(100), Scorchlander(100), Skeleton(5), Hive Soldier Drone(20), Hive Prince(10); фактические: -
- союзники после: Anti-Slavers 15; враги после: Daemons -80, Lost Chaos Space Marines -80, World Devourer War Gang -80, Midnight Lord -80, Hatred of intelligence -80
- KMM-отношения: KMM_Behavior: Bloodraiders None->-23, Black Dragon Ninjas None->-23, White Eyebrow Clan None->-15, Oni None->-10 (+54)
- conductor: arch=settler, wealth=50, strength=22, ambition=survival, relic=None
- снаряжение: культура: Leviathan Heavy Armour, Leviathan Legplates, Leviathan Helmet, Leviathan Boots; носят: Beakthing Legplates 2, Bonedog Armour 2, Bonedog Pants 2, Heavy Beakthing Plate 2, Light Beakthing Armour 2
- слои KMM: KMM_Behavior 1, KMM_Economy 8, KMM_Glue 8, KMM_Wardrobe 8

### Preacher Cult  `97072-Dialogue.mod`
- создатель: Dialogue.mod; тип: ADVENTURER; персонажей: 8, уников: 3
- уники: Moon Preacher, The High Preacher, The Preacher
- лидеры: Moon Knight
- расы фракции: -; фактические: Hive Prince 7, Scorchlander 6, Greenlander 5, Hive Soldier Drone 5
- города (5): Cult Village[holding], Farming Village (override) cult[3], Brink (override) Cultists[2], Cult Village (prosperous)[3], Farming Village (override) cult[3]
- регионы: Stormgap Coast
- союзники после: Cult of Fluorite 30, Missionaries 30, The Holy Nation 30, The Holy Nation 22; враги после: Grass Pirates -100, Daemons -90, Lost Chaos Space Marines -90, World Devourer War Gang -90, Midnight Lord -90
- KMM-отношения: KMM_Behavior: Bloodraiders None->-70, White Eyebrow Clan None->-70, The Holy Nation None->30, Oni None->-70 (+66)
- conductor: arch=religion, wealth=150, strength=33, ambition=survival, relic=None
- снаряжение: культура: White Plate Jacket, Mask of Crescence, Cultist's Zukin; носят: Rusty Chainmail 9, Moon Cleaver 9, Cultist's Zukin 9, Unholy Chest Plate 6, Hiver Chain Shirt 6
- гардероб: no_firearms
- Cleanup: лагеря [], хост ['Cult Village']
- слои KMM: KMM_Atlas 1, KMM_Behavior 1, KMM_Cleanup 1, KMM_Economy 8, KMM_Glue 8, KMM_Wardrobe 5

### Rebel Farmers  `54297-rebirth.mod`
- создатель: rebirth.mod; тип: BANDIT; персонажей: 8, уников: 1
- уники: Boss Simion
- лидеры: Outlaw Swordsman Captain, Outlaw Swordsman
- расы фракции: Greenlander(200), Hive Soldier Drone(10), Hive Worker Drone(30), Greenlander Child(0), Dark Hive Soldier Drone(25), Dark Hive Worker Drone(25); фактические: Greenlander Child 1, Greenlander 1
- города (4): Fort Simion[holding], Raider Camp[holding], First Village (override) Rebels[3], Port North (override) rebels[6]
- регионы: Sinkuun
- союзники после: Empire Peasants 100, Anti-Slavers 100, Rebel Swordsmen 100, Holy Nation Outlaws 100, Shinobi Thieves 100; враги после: Daemons -80, Lost Chaos Space Marines -80, World Devourer War Gang -80, Midnight Lord -80, Hatred of intelligence -80
- KMM-отношения: KMM_Behavior: Bloodraiders None->-15, White Eyebrow Clan None->-15, Oni None->-18, Reavers None->-40 (+67)
- conductor: arch=settler, wealth=240, strength=53, ambition=enrichment, relic=None
- снаряжение: культура: Wanderer's Tabard, Hakama Trousers Blue, Hakama Trousers Grey, Hakama Trousers Yellow, Wanderer's Straw Hat; носят: Rusted Hive Shirt 18, Wheatstraw Cape 18, Oni 12, Foreign Sabre 10, Wanderer's Straw Hat 10
- слои KMM: KMM_Atlas 2, KMM_Behavior 1, KMM_Diplo 1, KMM_Economy 8, KMM_Fix 1, KMM_Glue 9, KMM_Merged 1, KMM_Wardrobe 7

### Steel Raiders  `5131935-Dark Hive.mod`
- создатель: Dark Hive.mod; тип: BANDIT; персонажей: 8, уников: 2
- уники: Mr. Habu, The Heart of the Gate
- лидеры: Steel Raider Squire, Steel Mercenary Captain
- расы фракции: Dark Hive Prince(5), Dark Hive Soldier Drone(22), Dark Hive Worker Drone(13), Dark Hive Praetorian(1), Greenlander(100), Scorchlander(50); фактические: Dark Hive Soldier Drone 2, Shek 2, Dark Hive Prince 2, Greenlander 1, Scorchlander 1, Hive Worker Drone 1
- города (2): Noatun[holding], Dark Reaver Tower (over sr)[9]
- регионы: Dreg
- союзники после: Dust Bandits 60; враги после: Dark Reavers -100, The Holy Nation -70, Cult of Fluorite -70, Missionaries -70, The Holy Nation -70
- KMM-отношения: KMM_Behavior: The Holy Nation None->-70, Reavers None->-20, Lost Warrior None->-40, Band of Bones None->-20 (+99)
- conductor: arch=bandit, wealth=150, strength=31, ambition=enrichment, relic=None
- снаряжение: культура: Vanguard Swordspear, Plank Cleaver; носят: Plank Cleaver 4, Razor Topper 3, Rupture Blade 1, Vanguard Swordspear 1
- слои KMM: KMM_Atlas 4, KMM_Behavior 1, KMM_Diplo 1, KMM_Economy 8, KMM_Glue 9, KMM_Wardrobe 6

### World Devourer War Gang  `1892-TEXT TEXTURE.mod`
- создатель: TEXT TEXTURE.mod; тип: MILITARY; персонажей: 8, уников: 1
- уники: World Eater - Case
- лидеры: Devourer of Worlds - Berserker Vanguard, World Devourer - Berserker, Devourer of Worlds - Mad Berserker
- расы фракции: -; фактические: Astartes (Elite) 4, Astartes (The Lost) 3, Cannibal 1
- города (1): Blood Skull Altar[holding]
- регионы: Berserker Country, Cannibal Plains, Darkfinger, Fog Islands, Leviathan Coast, Purple Sands, The Iron Trail
- союзники после: Daemons 60, Lost Chaos Space Marines 60, Midnight Lord 60, Hatred of intelligence 60; враги после: United Cities -100, Shek Kingdom -100, The Holy Nation -100, Nameless -100, Astartes survivors -100
- KMM-отношения: KMM_Behavior: Bloodraiders None->-34, White Eyebrow Clan None->-36, Reavers None->-50, Police None->-80 (+121) | KMM_Glue: 1-KMM_Glue.mod None->-100
- conductor: arch=chaos, wealth=350, strength=87, ambition=faith, relic=spread_chaos
- снаряжение: культура: -; носят: World Devourer - Khorne Berserker Power Combat Boots 9, Butcher's Nail of the World Devourer 9, World Eater - Khorne Berserker Power Backpack 7, World Eater - Khorne Berserker Power Leg Armor 6, World Eater - Khorne Berserker Breathing Mask 6
- гардероб: power_armor
- банда outlaws: World Devourer War Gang
- слои KMM: KMM_Atlas 1, KMM_Behavior 1, KMM_Economy 8, KMM_Glue 8, KMM_Wardrobe 7

### Bounty Hunters  `14508-gamedata.base`
- создатель: gamedata.base; тип: ADVENTURER; персонажей: 7, уников: 2
- уники: Jon, Skeleton Bounty Hunter
- лидеры: Jon
- расы фракции: Greenlander(100), Hive Prince(10), Hive Soldier Drone(60), Hive Worker Drone(20), Scorchlander(50), Shek(100); фактические: Greenlander 3, Shek 1, Skeleton Log-Head MKII 1
- города (1): Bounty Hunter Camp[holding]
- союзники после: Mercenary Police 100, Police 100, United Cities 60, Imperial Bank 28, Guild of Surgeons 27; враги после: Daemons -80, Lost Chaos Space Marines -80, World Devourer War Gang -80, Midnight Lord -80, Hatred of intelligence -80
- KMM-отношения: KMM_Behavior: Bloodraiders None->-60, White Eyebrow Clan None->-60, Oni None->-60, Reavers None->-70 (+65)
- conductor: arch=state, wealth=150, strength=43, ambition=survival, relic=None
- снаряжение: культура: Police Jacket MkI - Grey, Iron Dome, Tsume Helmet MkII, Police Pants, Police Helmet; носят: Fog Mask 10, BH Boots 10, BH Clothpants 10, Plated Split-Toe Boots 10, Knapsack 10
- слои KMM: KMM_Behavior 1, KMM_Economy 3, KMM_Glue 1, KMM_Wardrobe 5

### Fishmen  `96359-rebirth.mod`
- создатель: rebirth.mod; тип: BANDIT; скрыта в UI (реальна в мире); персонажей: 7, уников: 1
- уники: King Gurgler
- лидеры: King Gurgler
- расы фракции: Fishman(100); фактические: Fishman 3, Alpha Fishman 3, Fishman Hatchling 1
- города (5): Fish Isle[2], Island Lab[4], Gurgler Nest[0], Catun (override) fishman takeover[2], Crab Town (override) Gurgler takeover[2]
- союзники после: Soulbodies 100, Crystal Enemys 100, Crab Raiders 24, Charred Skull Tribe 23, Fogmen 20; враги после: The Holy Nation -80, Cult of Fluorite -80, Missionaries -80, The Holy Nation -80, Preacher Cult -80
- KMM-отношения: KMM_Behavior: Bloodraiders None->-25, White Eyebrow Clan None->-14, Reavers None->19, Lost Warrior None->-60 (+133)
- conductor: arch=savage, wealth=40, strength=28, ambition=expansion, relic=None
- снаряжение: культура: King Gurgler Helmet, Fishnet Skirt, Fishman Armband, Gurgler Helmet, Fishman Leg Plates; носят: Fishman Armband 22, Fishman Leg Plates 22, Fishnet Cap 22, Fishnet Skirt 22, Samurai Helmet 6
- слои KMM: KMM_Atlas 1, KMM_Behavior 1, KMM_Diplo 1, KMM_Economy 7, KMM_Fix 1, KMM_Glue 7, KMM_Wardrobe 6

### Hounds  `48814-Dialogue.mod`
- создатель: Dialogue.mod; тип: CIVILIAN; персонажей: 7, уников: 2
- уники: Big Grim, Ears
- лидеры: Big Grim, Ears
- расы фракции: Greenlander(300), Hive Prince(25), Hive Soldier Drone(25), Hive Worker Drone(25), Scorchlander(100), Shek(100); фактические: Greenlander 1, Scorchlander 1, Skeleton 1
- города (5): Rot[holding], Stone Rat Village (override)[3], Grayflayer Village (override) hounds[3], Smugglers Bar (override) hounds[9], White Eyebrow Tower (override) Hounds[9]
- регионы: The Swamp
- союзники после: Swampers 100, Holy Nation Outlaws 100, Shinobi Thieves 100; враги после: Raptors -100, Spiders -100, Daemons -80, Lost Chaos Space Marines -80, World Devourer War Gang -80
- KMM-отношения: KMM_Behavior: Bloodraiders None->-7, Black Dragon Ninjas None->-15, White Eyebrow Clan None->-21, Oni None->-15 (+53)
- conductor: arch=settler, wealth=150, strength=47, ambition=survival, relic=None
- снаряжение: культура: Sleeveless Bushcoat, Halfpants [sneaky chain], Barbed Harpoon; носят: Leather Vest 19, Sleeveless Longcoat 18, Drifter's Leather Pants 18, Halfpants [sneaky chain] 16, Ringed Sabre 16
- Cleanup: лагеря [], хост ['Rot']
- слои KMM: KMM_Atlas 3, KMM_Behavior 1, KMM_Cleanup 1, KMM_Diplo 3, KMM_Economy 10, KMM_Elite 1, KMM_Glue 7, KMM_Merged 1, KMM_Town 1, KMM_Wardrobe 5

### Scavengers  `95512-rebirth.mod`
- создатель: rebirth.mod; тип: SLAVER; персонажей: 7, уников: 1
- уники: Gutterhead
- лидеры: Ransacker, Scavenger, Scavenger
- расы фракции: Greenlander(200), Hive Prince(25), Hive Soldier Drone(50), Hive Worker Drone(50), Scorchlander(150), Dark Hive Prince(4); фактические: Scorchlander 1, Hive Prince 1
- города (1): Old Control Tower[holding]
- регионы: Venge
- союзники после: -; враги после: The Holy Nation -70, Cult of Fluorite -70, Missionaries -70, The Holy Nation -70, Preacher Cult -70
- KMM-отношения: KMM_Behavior: The Holy Nation None->-70, Dark Hive None->-16, Reavers None->-20, Lost Warrior None->-40 (+101)
- conductor: arch=bandit, wealth=150, strength=37, ambition=enrichment, relic=None
- снаряжение: культура: Faded Robe, Scavenger's Can, Broken Cleaver, Scavenger's Katana, Basket Hat; носят: Armoured Rag Skirt 18, Scavenger's Can 18, Scavenger's Katana 18, Crab Shoes 15, Rusty Chain Shirt 14
- слои KMM: KMM_Behavior 1, KMM_Economy 10, KMM_Fix 1, KMM_Glue 7, KMM_Wardrobe 6

### Skeleton Bandits  `62792-rebirth.mod`
- создатель: rebirth.mod; тип: BANDIT; персонажей: 7, уников: 1
- уники: Elder
- лидеры: Upgraded Skeleton Bandit
- расы фракции: Greenlander(100); фактические: P4 Unit 1
- города (2): Iron HQ[holding], Iron HQ (destroyed)[4]
- регионы: Greenbeach, Stobe's Gamble, Stobe's Garden, The Crags, The Outlands, The Pits, The Pits East
- союзники после: -; враги после: Reavers -100, Crab Raiders -100, United Cities -100, Skin Bandits -100, The Holy Nation -70
- KMM-отношения: KMM_Behavior: The Holy Nation None->-70, Dark Hive None->-11, Lost Warrior None->-40, Band of Bones None->-20 (+97)
- conductor: arch=bandit, wealth=150, strength=35, ambition=enrichment, relic=None
- снаряжение: культура: Ancient Skeleton Log-Head Helm, Face of the Ancients, Head of the Ancients, Ancient Skeleton Gear Axe, Ancient Skeleton Cog Axe; носят: Rusty Chainmail 13, Head of the Ancients 13, Ancient Skeleton Cog Sabre 13, Ancient Samurai Legplates 10, Ancient Skeleton Log-Head Helm 10
- банда outlaws: Skeleton Bandits
- слои KMM: KMM_Atlas 1, KMM_Behavior 1, KMM_Diplo 1, KMM_Economy 10, KMM_Glue 8, KMM_Wardrobe 6

### Space Necromancer - Sora Dynasty  `61-40K Necrons.mod`
- создатель: 40K Necrons.mod; тип: MILITARY; персонажей: 7, уников: 1
- уники: Space Necromancer Lord - Kusobok
- лидеры: Space Necromancer - The Skinner, Necromancer's experimental slaves, Space Necromancer - Skinning Master
- расы фракции: -; фактические: Scorchlander 1, Greenlander 1, Space Necromancer 1
- города (1): Tomb of the Dead[city]
- регионы: Sonorous Dark
- союзники после: Skin Bandits 10; враги после: Second Empire -100, Skeletons -100, United Cities -100, Southern Hive -100, Fogmen -100
- KMM-отношения: KMM_Behavior: Bloodraiders None->-30, White Eyebrow Clan None->-26, Reavers None->-20, Lost Warrior None->-100 (+127) | KMM_Glue: 1-KMM_Glue.mod None->-100
- conductor: arch=xeno, wealth=350, strength=85, ambition=faith, relic=guard_tomb
- снаряжение: культура: -; носят: Human Skin Suit 5, Human Skin 5, Necromantic Experiment Body 3, Space Necromancer - Phase Claw 1, Space Necromancer - Phase Sword (Damaged) 1
- слои KMM: KMM_Behavior 1, KMM_Economy 8, KMM_Glue 8, KMM_Merged 13, KMM_Wardrobe 6

### Sysus Bandits  `1535736-Bounties Galore.mod`
- создатель: Bounties Galore.mod; тип: BANDIT; персонажей: 7, уников: 7
- уники: Alice, Asteria, Bersk, Cloud, Hudai, Orision, Putran'en
- лидеры: Hudai, Alice, Putran'en, Cloud, Orision
- расы фракции: -; фактические: Greenlander 3, Shek 1, Hive Worker Drone 1, Hive Soldier Drone 1, Scorchlander 1
- города (1): Barcrest[holding]
- регионы: The Outlands
- союзники после: Grass Pirates 50, Reavers 50, Shinobi Thieves 22; враги после: United Cities -100, Police -100, The Holy Nation -100, Cannibals -100, Anti-Slavers -100
- KMM-отношения: KMM_Behavior: The Holy Nation None->-70, Dark Hive None->-15, Lost Warrior None->-40, Band of Bones None->-20 (+94)
- conductor: arch=bandit, wealth=150, strength=41, ambition=enrichment, relic=None
- слои KMM: KMM_Behavior 1, KMM_Diplo 6, KMM_Economy 7, KMM_Fix 1, KMM_Glue 8, KMM_Town 1

### Vagrants  `96156-rebirth.mod`
- создатель: rebirth.mod; тип: BANDIT; скрыта в UI (реальна в мире); персонажей: 7, уников: 1
- уники: Raidriar
- лидеры: Raidriar
- расы фракции: Greenlander(200), Hive Prince(25), Hive Prince South Hive(15), Hive Soldier Drone(25), Hive Soldier Drone South Hive(15), Hive Worker Drone(25); фактические: Greenlander 3, Shek 2, Scorchlander 2, Scorchlander Child 1, Shek Child 1, Greenlander Child 1
- города (2): Ark (override) destroyed[1], Vagrant Bandit Camp[0]
- союзники после: Sultans Wares 16, Traders Guild 12, Imperial Bank 12, Gunsmiths 11, Drug Peddlers 10; враги после: Daemons -80, Lost Chaos Space Marines -80, World Devourer War Gang -80, Midnight Lord -80, Hatred of intelligence -80
- KMM-отношения: KMM_Behavior: Reavers None->-35, Band of Bones None->-40, Blood Butcher Tribe None->-40, Greenskins None->-29 (+29)
- conductor: arch=settler, wealth=50, strength=22, ambition=survival, relic=None
- снаряжение: культура: -; носят: Farmers Grass Sandal 8, Armoured Rag Skirt 7, Wheatstraw Cape 7, Rag Cowl 7, Ancient Samurai Helmet 5
- слои KMM: KMM_Behavior 1, KMM_Economy 7, KMM_Glue 6, KMM_Town 2, KMM_Wardrobe 6

### Black Desert Ninjas  `66292-rebirth.mod`
- создатель: rebirth.mod; тип: BANDIT; персонажей: 6, уников: 3
- уники: Ammonia, Grandmaster Zephyr, Styg
- лидеры: Ammonia, Styg, Grandmaster Zephyr
- расы фракции: Greenlander(100), Scorchlander(100), Hive Prince(25), Greenlander Child(0), Scorchlander Child(0), Dark Hive Prince(10); фактические: Scorchlander 3, Greenlander 2, Scorchlander Child 1, Hive Prince 1, Greenlander Child 1
- города (5): Gas Grove[holding], Gas Grove (dead)[9], Cloud House[holding], Hidden Camp[holding], Rust HQ (ninja)[2]
- регионы: Arm of Okran, Deadlands, Grey Desert, Iron Valleys, Skinner's Roam, The Black Desert
- союзники после: -; враги после: The Holy Nation -70, Cult of Fluorite -70, Missionaries -70, The Holy Nation -70, Preacher Cult -70
- KMM-отношения: KMM_Behavior: The Holy Nation None->-70, Dark Hive None->-15, Reavers None->-20, Lost Warrior None->-40 (+100)
- conductor: arch=bandit, wealth=330, strength=67, ambition=enrichment, relic=None
- снаряжение: культура: Mask Type III, Cloud Ninja Mask, Wire Gutter; носят: Dark Leather Shirt 12, Mask Type III 10, Ninja Mask 10, Small Backpack (colored) 9, Black Desert Rags 9
- гардероб: uniforms:ninja
- банда outlaws: Black Desert Ninjas
- слои KMM: KMM_Behavior 1, KMM_Diplo 3, KMM_Economy 7, KMM_Elite 2, KMM_Fix 1, KMM_Glue 5, KMM_Wardrobe 3

### Cannibal Hunters  `16855-gamedata.base`
- создатель: gamedata.base; тип: ADVENTURER; персонажей: 6, уников: 2
- уники: Cannibal Hunter Robun, Daiko
- лидеры: Cannibal Hunter Robun
- расы фракции: Greenlander(300), Shek(100), Scorchlander(150), Hive Soldier Drone(60), Hive Worker Drone(20), Hive Prince(10); фактические: Primordial Hive Soldier Drone 1
- города (7): Camp- Cannibal Hunters[holding], The Bastion[city], Flotsam Village (override) cannibal hunters[3], Guard Outpost (override) cannibal hunters[9], Okran's Fist (override) cannibal hunters[6], Tower Of Goats (override) cannibal hunters[9], Watchtower (override) cannibal hunters[9]
- регионы: Sinkuun
- союзники после: Tech Hunters 100, Desert Divers 100, Deadcat 100, Guild of Surgeons 21, Traders Guild 20; враги после: Cannibals -100, Blood Butcher Tribe -100, Charred Skull Tribe -100, Gnawed Bone Tribe -100, Fogmen -100
- KMM-отношения: KMM_Behavior: Bloodraiders None->-60, White Eyebrow Clan None->-60, Oni None->-60, Reavers None->-70 (+61)
- conductor: arch=state, wealth=240, strength=53, ambition=survival, relic=None
- снаряжение: культура: Blackened Chain Shirt, Plated Drifter's Leather Pants, Purifier; носят: Blackened Chain Shirt 21, Chain Shirt 21, Desert Sabre 20, Plated Drifter's Leather Pants 14, Armoured Dustcoat 14
- слои KMM: KMM_Atlas 2, KMM_Behavior 1, KMM_Diplo 2, KMM_Economy 8, KMM_Elite 1, KMM_Glue 6, KMM_Town 1, KMM_Wardrobe 4

### Clownsteaders  `5008123-Kaizo.mod`
- создатель: Kaizo.mod; тип: CIVILIAN; персонажей: 6, уников: 0
- лидеры: Clownsteader Captain
- расы фракции: Greenlander(150), Scorchlander(150), Shek(50), Skeleton(1), Hive Soldier Drone(2), Hive Worker Drone(10); фактические: -
- города (2): Clownsteady (override) free city[2], Slave Market (override) clownsteaders[1]
- союзники после: Police 100; враги после: The Holy Nation -100, United Cities -100, Daemons -80, Lost Chaos Space Marines -80, World Devourer War Gang -80
- KMM-отношения: KMM_Behavior: Bloodraiders None->-15, Black Dragon Ninjas None->-15, White Eyebrow Clan None->-15, Oni None->-8 (+54)
- conductor: arch=settler, wealth=50, strength=22, ambition=survival, relic=None
- снаряжение: культура: -; носят: Conscript Leather Armour 4
- слои KMM: KMM_Atlas 1, KMM_Behavior 1, KMM_Economy 5, KMM_Glue 5, KMM_Wardrobe 6

### Cult of Fluorite  `12-The Leviathan Ronin.mod`
- создатель: The Leviathan Ronin.mod; тип: CIVILIAN; персонажей: 6, уников: 1
- уники: Violet
- лидеры: Violet
- расы фракции: Greenlander(60), Scorchlander(35), Enforcer(5); фактические: Greenlander 1
- города (3): Fluorite[city], Hilt (Fluorite)[2], Airnagard (Fluorite)[6]
- регионы: Purple Sands
- союзники после: Levi Ronin 100, Missionaries 30, Preacher Cult 24; враги после: Shrieking Bandits -100, Gutters -100, Wolves -100, Cannibals -100, Berserkers -100
- KMM-отношения: KMM_Behavior: Bloodraiders None->-70, White Eyebrow Clan None->-70, The Holy Nation None->-29, Oni None->-70 (+60)
- conductor: arch=religion, wealth=150, strength=53, ambition=survival, relic=None
- снаряжение: культура: Spiked Sabre, Medium backpack (colored), Saw Naginata, Saw Katana; носят: Saw Katana 35, Armoured Rags (colored) 26, Armoured Rag Skirt (colored) 26, Dyed Turtleneck 22, Visored Helmet 13
- слои KMM: KMM_Atlas 3, KMM_Behavior 1, KMM_Diplo 1, KMM_Economy 12, KMM_Elite 1, KMM_Glue 6, KMM_Wardrobe 5

### Reavers  `62805-rebirth.mod`
- создатель: rebirth.mod; тип: BANDIT; персонажей: 6, уников: 2
- уники: Valamon, 流血掠夺者
- лидеры: Valamon, 流血掠夺者
- расы фракции: Greenlander(100), Shek(100), Scorchlander(75), Greenlander Child(0), Scorchlander Child(0), Shek Child(0); фактические: Shek 3, Greenlander 2, Scorchlander 2, Scorchlander Child 2, Shek Child 2, Greenlander Child 2
- города (12): Reaver Camp[holding], Ark[holding], Brink (override) takeover[2], Heng (override) [2], Okran's Shield (override) reavers[2], Crab Village (override) Reaver takeover[1], Reaver Camp (override) destroyed[4], Okran's Shield (override) shek to reavers[2], Reaver Camp[holding], Reaver Camp[holding], Reaver Camp[holding], Black Dog HQ (override) reavers[9]
- регионы: Greenbeach, Heng, Stobe's Garden, Stormgap Coast, The Crags, The Eye, The Outlands, The Pits East
- союзники после: Berserkers 25, Skull Collectors 25, Fogmen 20, Blood Butcher Tribe 20, Charred Skull Tribe 20; враги после: Skeleton Bandits -100, Skin Bandits -100, Crab Raiders -100, United Cities -100, Dust Reapers -100
- KMM-отношения: KMM_Behavior: Bloodraiders None->-22, White Eyebrow Clan None->-20, Lost Warrior None->-60, Police None->-70 (+128)
- conductor: arch=savage, wealth=510, strength=113, ambition=enrichment, relic=None
- снаряжение: культура: Spring Bat, Hack Stopper Jacket, Hack Stopper Pants, Large Backpack, Blood Mask; носят: Crab Shoes 43, Hack Stopper Pants 43, Strips of fabric (colored) 42, Hack Stopper Jacket 35, Plated Shortboots 34
- банда outlaws: Reavers
- слои KMM: KMM_Atlas 3, KMM_Behavior 1, KMM_Diplo 3, KMM_Economy 6, KMM_Elite 9, KMM_Fix 1, KMM_Glue 7, KMM_Town 1, KMM_Wardrobe 5

### Skeleton Sultans  `5008243-Sailback.mod`
- создатель: Sailback.mod; тип: TRADER; персонажей: 6, уников: 1
- уники: Sultan Shopkeep
- лидеры: Sultan Shopkeep
- расы фракции: Skeleton(100), P4 Unit(4), Greenlander(4), Scorchlander(4), Hive Soldier Drone(4); фактические: P4 Unit 4, Skeleton 4, Greenlander 1, Shek 1, Scorchlander 1
- города (1): Sultan Outpost[holding]
- регионы: The Black Desert
- союзники после: Skeleton Legion 70, Nomadic Skeletons 60, Floodlands Skeletons 60, Cyborgs 60, Old Machines 60; враги после: Daemons -80, The Holy Nation -80, Cult of Fluorite -80, Lost Chaos Space Marines -80, World Devourer War Gang -80
- KMM-отношения: KMM_Behavior: Bloodraiders None->-20, White Eyebrow Clan None->-23, The Holy Nation None->-80, Oni None->-21 (+75)
- conductor: arch=robot, wealth=150, strength=35, ambition=enrichment, relic=None
- снаряжение: культура: -; носят: Foreign Sabre 9, Noble's Trousers 3, Noble's Robe 3, Traders Backpack Medium 1, Thrasher Harpoon 1
- слои KMM: KMM_Behavior 1, KMM_Economy 9, KMM_Elite 1, KMM_Glue 6, KMM_Wardrobe 5

### Sultans Wares  `166-Thrasher Sultan Seller.mod`
- создатель: Thrasher Sultan Seller.mod; тип: SLAVE; персонажей: 6, уников: 0
- лидеры: Servile Thrasher
- расы фракции: Thrasher Servile(100); фактические: Thrasher Servile 6
- союзники после: Skeleton Sultans 55, Western Hive 50, Empire Peasants 50, Skeletons 50, Nomads 50; враги после: Daemons -80, Lost Chaos Space Marines -80, World Devourer War Gang -80, Midnight Lord -80, Hatred of intelligence -80
- KMM-отношения: KMM_Behavior: Bloodraiders None->-60, White Eyebrow Clan None->-60, Oni None->-60, Reavers None->-60 (+83)
- conductor: arch=trader, wealth=120, strength=20, ambition=enrichment, relic=None
- снаряжение: культура: -; носят: Thrasher Harpoon 2
- слои KMM: KMM_Behavior 1, KMM_Economy 8, KMM_Glue 6, KMM_Wardrobe 6

### Swamp Ninjas  `51638-rebirth.mod`
- создатель: rebirth.mod; тип: BANDIT; персонажей: 6, уников: 1
- уники: Shade
- лидеры: Swamp Ninja Chunin
- расы фракции: Greenlander(100), Scorchlander(100), Hive Prince(20), Greenlander Child(0), Scorchlander Child(0), Dark Hive Prince(7); фактические: Greenlander 3, Scorchlander 3, Scorchlander Child 1, Hive Prince 1, Greenlander Child 1
- города (6): Wetlands Hideout[holding], Stone Rat Village (takeover)[3], Swamp Ninja Ruins[holding], Red Sabre Hideout (override) ninjas[9], Rot (override) ninjas[3], Slave Markets (override) ninjas[1]
- регионы: South Wetlands, The Swamp
- союзники после: -; враги после: Red Sabres -100, Raptors -100, Spiders -100, The Holy Nation -70, Cult of Fluorite -70
- KMM-отношения: KMM_Behavior: The Holy Nation None->-70, Dark Hive None->-11, Reavers None->-26, Lost Warrior None->-37 (+96)
- conductor: arch=bandit, wealth=240, strength=47, ambition=enrichment, relic=None
- снаряжение: культура: Iron Hat (Swamp Mask), Decorated Swamp Mask, Swamp Ninja Mask, Swamp Ninja Mask (Mouth Only); носят: Swamp Ninja Mask 9, Swamp Ninja Rags 8, Iron Hat (Swamp Mask) 8, Dyed Rag Cowl 8, Swamp Ninja Mask (Mouth Only) 8
- гардероб: uniforms:ninja
- банда outlaws: Swamp Ninjas
- слои KMM: KMM_Behavior 1, KMM_Economy 8, KMM_Fix 4, KMM_Glue 7, KMM_Wardrobe 5

### The Holy Nation  `352-cook_set.mod`
- создатель: cook_set.mod; тип: CIVILIAN; скрыта в UI (реальна в мире); персонажей: 6, уников: 5
- уники: Alan, Comine, Jakes, Maurice, Romi
- лидеры: Romi
- расы фракции: -; фактические: Greenlander 5
- союзники после: The Holy Nation 100, Missionaries 30, Preacher Cult 28; враги после: Raptors -100, Cannibals -100, Daemons -90, Lost Chaos Space Marines -90, World Devourer War Gang -90
- KMM-отношения: KMM_Behavior: Bloodraiders None->-70, White Eyebrow Clan None->-70, Oni None->-70, Reavers None->-80 (+66)
- снаряжение: культура: Phoenix Plate, Holy Chest Plate - Heavy, Holy Plate Armor, Holy Chest Plate - Medium, Holy Lords Chainmail; носят: Stout Hessian Uniform 198, Plated Longboots 151, Holy Chest Plate 125, Bucket Zukin 118, Flared Helmet 117
- гардероб: no_firearms, uniforms:holy_nation
- слои KMM: KMM_Behavior 1, KMM_Cleanup 1, KMM_Economy 7, KMM_Glue 6, KMM_Merged 7, KMM_Wardrobe 1

### Thrall Masters  `97613-rebirth.mod`
- создатель: rebirth.mod; тип: BANDIT; скрыта в UI (реальна в мире); персонажей: 6, уников: 2
- уники: Ponk, Screamer the False
- расы фракции: -; фактические: Skeleton No-Head MkII  3, Skeleton No-Head MkI 2, Hazards Unit No-Head 1, Screamer MkI 1, Skeleton P4MkII 1
- города (1): Tower of Abuse[4]
- регионы: Venge
- союзники после: Skeleton Legion 50; враги после: -
- снаряжение: культура: Old Empire Club; носят: Ruined Samurai Armour 6, Old Empire Club 6, Ruined Samurai Legplates 3
- слои KMM: KMM_Economy 6, KMM_Fix 1, KMM_Glue 6, KMM_Wardrobe 4

### United Heroes League  `42264-gamedata.base`
- создатель: gamedata.base; тип: ADVENTURER; персонажей: 6, уников: 1
- уники: Lord Mirage
- лидеры: Lord Mirage
- расы фракции: Greenlander(100); фактические: -
- города (1): Fort Mirage[holding]
- союзники после: United Cities 100, Gunsmiths 28, cloak shop(test) 25, Traders Guild 20, Wandering Cloak Shop 20; враги после: Shek Kingdom -100, Western Hive -100, Daemons -80, Lost Chaos Space Marines -80, World Devourer War Gang -80
- KMM-отношения: KMM_Behavior: Bloodraiders None->-60, White Eyebrow Clan None->-60, Oni None->-60, Reavers None->-70 (+65)
- conductor: arch=state, wealth=150, strength=43, ambition=survival, relic=None
- снаряжение: культура: Noble's Robe - Ginge [sneaky chain], Tin Can - Padded, Tin Greatcan, Tin Can, Hero's Helm; носят: Dyed Turtleneck 16, Tin Can 15, Leather Armor - Heavy 14, Leather Armor - Medium 14, Tin Can - Padded 14
- слои KMM: KMM_Behavior 1, KMM_Diplo 1, KMM_Economy 6, KMM_Fix 1, KMM_Glue 6, KMM_Merged 1, KMM_Town 1, KMM_Wardrobe 6

### Ancient Ruins  `48671-rebirth.mod`
- создатель: rebirth.mod; тип: BANDIT; скрыта в UI (реальна в мире); персонажей: 5, уников: 1
- уники: General Screamer (The True)
- лидеры: General Screamer (The True)
- расы фракции: -; фактические: Skeleton MKII Screamer 2, Skeleton No-Head MkII  2, Screamer MkI 2, Skeleton Log-Head MkII Psychobot 1, Skeleton 1, P4 Unit 1
- города (16): Lab Ruin[4], Ancient Tech Lab[4], Post-Ancient Workshop[4], Empty Lab[4], Workshop Complex[4], Swamped Lab[4], Ancient Labs[4], Infested Lab[4], Deadland Workshop[4], Crumbling Labs[4], Dead Workshop[4], Reprogramming Workshop[4], Ruined Control Tower[4], Ashland Dome Ruin[4], Mountain Ruin[4], Post-Ancient Workshop[4]
- регионы: Deadlands
- союзники после: Old Machines 100, Skeleton Legion 100, Second Empire 100, Second Empire Exile 100; враги после: -
- слои KMM: KMM_Economy 3, KMM_Fix 10, KMM_Glue 3, KMM_Wardrobe 4

### Berserkers  `42257-rebirth.mod`
- создатель: rebirth.mod; тип: BANDIT; персонажей: 5, уников: 1
- уники: Ghost
- лидеры: Berserker, Indigo, Berserker Guardian
- расы фракции: Shek(100); фактические: Shek 2, Young Shek 1
- города (8): Berserker Village[holding], Squin (override) destroyed[4], Exile Camp (Berserkers)[9], Berserker Outpost[holding], Admag (override) berserkers[4], Berserker Camp[holding], New Kralia (override) berserkers[1], Shek Ruins (override) berserkers[4]
- регионы: Bast, Berserker Country, Cannibal Plains, Okran's Gulf, Purple Sands, Spider Plains, Stenn Desert
- союзники после: Charred Skull Tribe 28, Kral's Chosen 28, Fishmen 26, The Hollow Feast 24, Fogmen 20; враги после: Bloodraiders -100, Holy Nation Outlaws -100, Old Machines -100, Police -100, Slave Traders -100
- KMM-отношения: KMM_Behavior: White Eyebrow Clan None->-26, Reavers None->20, Lost Warrior None->-60, The Fallen Gang None->-26 (+126)
- conductor: arch=savage, wealth=330, strength=65, ambition=enrichment, relic=None
- снаряжение: культура: Bonedog Armour, Beakthing Legplates, Beakthing Plate Helmet, Light Beakthing Armour, Bonedog Pants; носят: Fragment Axe 13, Beakthing Legplates 10, Beakthing Plate Helmet 10, Bonedog Armour 10, Bonedog Pants 10
- гардероб: pagan
- банда outlaws: Berserkers
- слои KMM: KMM_Behavior 1, KMM_Economy 5, KMM_Fix 3, KMM_Glue 6, KMM_Wardrobe 4

### Black Dog  `56644-Dialogue.mod`
- создатель: Dialogue.mod; тип: ADVENTURER; персонажей: 5, уников: 2
- уники: Black Dog Boss, Black Dog Boss Secondary
- лидеры: Black Dog Boss, Black Dog Boss Secondary
- расы фракции: -; фактические: -
- города (2): Black Dog HQ[holding], Black Dog HQ (override) secondary[9]
- союзники после: -; враги после: The Holy Nation -70, Cult of Fluorite -70, Missionaries -70, The Holy Nation -70, Preacher Cult -70
- KMM-отношения: KMM_Behavior: The Holy Nation None->-70, Dark Hive None->-21, Reavers None->-12, Lost Warrior None->-40 (+100)
- conductor: arch=bandit, wealth=150, strength=35, ambition=survival, relic=None
- снаряжение: культура: Police Jacket MkII - Black, Plate Jacket Heavy - Black, Plate Jacket Medium - Black, Police Jacket MkI - Black, Police Boots - Black; носят: Black Plate Jacket 10, Police Jacket MkI - Black 4, Police Jacket MkII - Black 4, Plate Jacket Medium - Black 4, Police Boots - Black 4
- слои KMM: KMM_Behavior 1, KMM_Diplo 1, KMM_Fix 2, KMM_Glue 3, KMM_Town 1, KMM_Wardrobe 3

### Black Dragon Ninjas  `18007-rebirth.mod`
- создатель: rebirth.mod; тип: BANDIT; персонажей: 5, уников: 2
- уники: Buzan, Dimak
- лидеры: Black Dragon Jonin
- расы фракции: Greenlander(100), Hive Prince(30), Hive Soldier Drone(5), Hive Worker Drone(20), Scorchlander(60), Shek(30); фактические: Shek 1, Scorchlander 1
- города (7): Tower Of Ninjas[holding], Black Dragon Camp[holding], Black Dragon Camp[holding], Black Dragon Camp (Phoenix killed)[holding], Dust King Tower (override) Ninja takeover[9], Tiny Settlement (override) ninjas[4], White Eyebrow Tower (override) ninjas[9]
- регионы: Border Zone, Okran's Gulf, Okran's Pride, Okran's Valley, Shem, Skinner's Roam, Stobe's Garden, The Swamp
- союзники после: -; враги после: White Eyebrow Clan -100, Dust Bandits -100, The Holy Nation -70, Cult of Fluorite -70, Missionaries -70
- KMM-отношения: KMM_Behavior: The Holy Nation None->-70, Dark Hive None->-17, Reavers None->-19, Lost Warrior None->-32 (+100)
- conductor: arch=bandit, wealth=420, strength=81, ambition=enrichment, relic=None
- снаряжение: культура: Iron Hat - Heavy, Hooded Iron Hat, Hooded Rattan Hat; носят: Ninja Rags 27, Guardless Katana 27, Straw Sandals 20, Ninja Ragpants 20, Iron Hat - Heavy 20
- гардероб: uniforms:ninja
- банда outlaws: Black Dragon Ninjas
- слои KMM: KMM_Behavior 1, KMM_Economy 8, KMM_Glue 6, KMM_Wardrobe 3

### Dust Bandits  `200-gamedata.base`
- создатель: gamedata.base; тип: BANDIT; персонажей: 5, уников: 1
- уники: Dust King
- лидеры: Dust Boss
- расы фракции: Greenlander(350), Shek(150), Greenlander Child(0), Shek Child(0), Hive Soldier Drone(100), Scorchlander(60); фактические: Shek Child 1, Greenlander Child 1, Greenlander 1
- города (6): Dust Bandit Camp[holding], Dust King Tower[holding], Dust Bandit Camp[holding], The Hub (override) bandits[6], Tower Of Ninjas (override) Dust Bandits[9], Dust Bandit Camp (HN)[holding]
- регионы: Arm of Okran, Bonefields, Border Zone, Dreg, Okran's Gulf, Okran's Pride, Okran's Valley, Shem, Skinner's Roam, The Hook
- союзники после: Rusty Raiders 60, Steel Raiders 60; враги после: United Cities -100, Police -100, Dust Lords -100, Dust Raiders -100, Dust Reapers -100
- KMM-отношения: KMM_Behavior: The Holy Nation None->-70, Lost Warrior None->-40, Greenskins None->-30, Hatred of intelligence None->-28 (+45) | KMM_Glue: 1-KMM_Glue.mod None->-40
- conductor: arch=bandit, wealth=420, strength=85, ambition=enrichment, relic=None
- снаряжение: культура: Spiked Arnour, Dust Skirt, Spiked Helmet (Fullface), Spiked Helmet, Ashguard Straw Kasa; носят: Heart Protector 32, Spiked Club 32, Armoured Rag Skirt 31, Mercenary Club 28, Topper 28
- банда outlaws: Dust Bandits
- слои KMM: KMM_Atlas 1, KMM_Behavior 1, KMM_Diplo 1, KMM_Economy 8, KMM_Fix 1, KMM_Glue 6, KMM_Wardrobe 4

### Kral's Chosen  `51357-rebirth.mod`
- создатель: rebirth.mod; тип: BANDIT; персонажей: 5, уников: 3
- уники: Flying Bull, Kang, Ruka
- лидеры: Flying Bull
- расы фракции: Shek(100); фактические: Shek 5
- города (12): New Kralia[holding], Bad Teeth (override) kral takeover [2], Holy Mines (override) kral takeover[3], Stack (override) kral takeover[2], New Kralia (override) destroyed[4], Squin (override) takeover[2], Exile Camp (Kral's Chosen)[9], Admag (override) krals[2], Berserker Village (override) krals[1], Renegade Camp[holding], Shek Ruins (override) krals[4], Salvation (override) takeover 2[3]
- союзники после: Fogmen 20, Berserkers 20, Blood Butcher Tribe 20, Gnawed Bone Tribe 20, Skull Collectors 20; враги после: The Holy Nation -90, Cult of Fluorite -80, Missionaries -80, The Holy Nation -80, Preacher Cult -80
- KMM-отношения: KMM_Behavior: Bloodraiders None->-20, White Eyebrow Clan None->-23, Reavers None->20, Lost Warrior None->-60 (+134)
- conductor: arch=savage, wealth=240, strength=69, ambition=enrichment, relic=None
- снаряжение: культура: Barbaric Breastplate, Assassin's Plate, Barbaric Faulds, Bull Horn Axe, Turret Bat; носят: Martial Artist Bindings 19, Plank 18, Black Cloth Shirt 18, Barbaric Breastplate 18, Barbaric Faulds 18
- слои KMM: KMM_Atlas 4, KMM_Behavior 1, KMM_Diplo 1, KMM_Economy 7, KMM_Elite 1, KMM_Glue 6, KMM_Town 1, KMM_Wardrobe 2

### Oni  `5007306-Oni.mod`
- создатель: Oni.mod; тип: BANDIT; персонажей: 5, уников: 1
- уники: Blue Oni
- лидеры: Blue Oni
- расы фракции: -; фактические: Hazards Unit Oni 4, Hazards Unit No-Head 1
- города (2): Tower of Trial[holding], Perdition[city]
- регионы: Venge
- союзники после: Skeleton Legion 100, Thrall Masters 4; враги после: Reavers -100, Crab Raiders -100, United Cities -100, The Holy Nation -100, Cult of Fluorite -70
- KMM-отношения: KMM_Behavior: The Holy Nation None->-70, Dark Hive None->-21, Lost Warrior None->-40, Band of Bones None->-21 (+96)
- conductor: arch=bandit, wealth=240, strength=57, ambition=enrichment, relic=None
- снаряжение: культура: Hazards Shell [upper], Oni Hazards Shell [upper], Hazards Shell [lower], Oni Hazards Shell [lower]; носят: Oni Hazards Shell [lower] 11, Oni Hazards Shell [upper] 11, Hazards Shell [lower] 10, Hazards Shell [upper] 10
- слои KMM: KMM_Behavior 1, KMM_Diplo 1, KMM_Economy 5, KMM_Elite 1, KMM_Fix 1, KMM_Glue 6, KMM_Merged 1, KMM_Wardrobe 4

### Sand ninjas  `1085-gamedata.base`
- создатель: gamedata.base; тип: BANDIT; персонажей: 5, уников: 2
- уники: Jounin Gutworm, Sand Ninja Oni
- лидеры: Sand Ninja Oni
- расы фракции: Greenlander(100), Scorchlander(100), Greenlander Child(0), Scorchlander Child(0), Hive Prince(25), Hive Prince South Hive(10); фактические: Scorchlander 3, Greenlander 1, Greenlander Child 1, Scorchlander Child 1
- города (2): Cactus Den[holding], Cactus Den (Gutworm)[9]
- регионы: Heng, Spine Canyon, The Eye, The Great Desert
- союзники после: -; враги после: The Holy Nation -70, Cult of Fluorite -70, Missionaries -70, The Holy Nation -70, Preacher Cult -70
- KMM-отношения: KMM_Behavior: The Holy Nation None->-70, Dark Hive None->-21, Reavers None->-25, Lost Warrior None->-40 (+100)
- conductor: arch=bandit, wealth=150, strength=37, ambition=enrichment, relic=None
- снаряжение: культура: Skimmer Armour, Skimmer Pants, Skimmer Antennae Mask, Skimmer Mask, Hannya Mask; носят: Dark Leather Shirt 15, Assassin's Plate 11, Desert Ninja Rags  10, Skimmer Antennae Mask 10, Skimmer Armour 10
- гардероб: uniforms:ninja
- банда outlaws: Sand ninjas
- слои KMM: KMM_Atlas 2, KMM_Behavior 1, KMM_Diplo 1, KMM_Economy 5, KMM_Elite 2, KMM_Fix 2, KMM_Glue 6, KMM_Wardrobe 3

### Wildlife  `3943-gamedata.base`
- создатель: gamedata.base; тип: NONE; скрыта в UI (реальна в мире); персонажей: 5, уников: 2
- уники: Goat Man, Polpol
- лидеры: Polpol
- расы фракции: -; фактические: Dark Hive Worker Drone 4, Greenlander 1
- города (11): Tower Of Goats[9], Nest of Jarraffes[0], Winged Beak Ogre Lair[9], Sea Wolf Den[0], Foulhound Den[0], Bone Fiend Hollow (defunct and broken)[0], Large Bone Fiend Hollow (defunct and broken)[0], eastern tyrant nest Goliath[0], Western tyrant nest Goliath[0], Sailback Graveyard[0], Breeder's Den[9]
- регионы: Sinkuun
- союзники после: Herbivore 25, Goats 25, Wild Bulls 25; враги после: -
- снаряжение: культура: -; носят: Rupture Blade 1
- слои KMM: KMM_Economy 4, KMM_Glue 4, KMM_Wardrobe 3

### Band of Bones  `56595-Dialogue.mod`
- создатель: Dialogue.mod; тип: BANDIT; персонажей: 4, уников: 2
- уники: Tora The Fearless, Zander
- лидеры: Tora The Fearless, Zander
- расы фракции: Shek(100), Shek Child(0); фактические: Shek 4, Shek Child 1
- города (6): Exile Camp[holding], Shek Ruins[holding], Grayflayer Village (override) bandits[1], Zander's Hideout[9], Exile Camp[holding], Bone Band Camp[holding]
- регионы: Bonefields, Border Zone, High Bonefields, Shem, Shun, Spider Plains, Stenn Desert, The Hook, The Swamp
- союзники после: Charred Skull Tribe 26, The Hollow Feast 24, Cannibals 22, Crab Raiders 21, Berserkers 20; враги после: Bloodraiders -100, Holy Nation Outlaws -100, Old Machines -100, Police -100, Shek Kingdom -100
- KMM-отношения: KMM_Behavior: White Eyebrow Clan None->-20, Reavers None->13, Lost Warrior None->-60, The Fallen Gang None->-20 (+125)
- conductor: arch=savage, wealth=510, strength=93, ambition=enrichment, relic=None
- снаряжение: культура: Wooden Backpack; носят: Heart Protector 19, Mercenary Leather Armour 18, Armoured Hood 18, Martial Artist Bindings 18, Spiked Helmet 18
- гардероб: pagan
- банда outlaws: Band of Bones
- Cleanup: лагеря ["Zander's Hideout"], хост []
- слои KMM: KMM_Behavior 1, KMM_Cleanup 2, KMM_Diplo 2, KMM_Economy 7, KMM_Fix 1, KMM_Glue 5, KMM_Town 3, KMM_Wardrobe 2

### Big Dave's Ninjas  `917-Companion Quest - Morse.mod`
- создатель: Companion Quest - Morse.mod; тип: BANDIT; скрыта в UI (реальна в мире); персонажей: 4, уников: 1
- уники: Big Dave
- расы фракции: Greenlander(100), Scorchlander(100), Hive Prince(20); фактические: Scorchlander 1
- города (1): Dave's House[9]
- союзники после: Swamp Ninjas 35, Red Sabres 35, Wildlife 10, Victor's Hideout 5; враги после: Nameless -100
- гардероб: uniforms:ninja
- слои KMM: KMM_Economy 3, KMM_Fix 1, KMM_Glue 4, KMM_Wardrobe 3

### Blackshifters  `48743-Dialogue.mod`
- создатель: Dialogue.mod; тип: CIVILIAN; персонажей: 4, уников: 1
- уники: Big Darkbrow
- лидеры: Big Darkbrow
- расы фракции: Hive Prince(50), Hive Soldier Drone(200), Dark Hive Prince(15), Dark Hive Soldier Drone(40), Hive Worker Drone(100); фактические: Hive Prince 2
- города (7): Secret Drug Farm[holding], Shark (override) blackshifter[2], Red Sabre Hideout (override) blackshifters[9], Rot (override) blackshifters[3], Smugglers Bar (override) blackshifters[9], Swamp Ninja Base (override) blackshifters[9], White Eyebrow Tower (override) Blackshifters[9]
- союзники после: Swampers 100, Holy Nation Outlaws 100, Shinobi Thieves 100; враги после: Raptors -100, Spiders -100, Daemons -80, Lost Chaos Space Marines -80, World Devourer War Gang -80
- KMM-отношения: KMM_Behavior: Bloodraiders None->-19, Black Dragon Ninjas None->-15, White Eyebrow Clan None->-15, Oni None->-9 (+53)
- conductor: arch=settler, wealth=150, strength=45, ambition=survival, relic=None
- снаряжение: культура: -; носят: Drifter's Leather Jacket 14, Black Leather Armour 13, Black Leather Skirt 13, Strips of fabric (colored) 13, Great Ringed Sabre 13
- слои KMM: KMM_Atlas 4, KMM_Behavior 1, KMM_Diplo 2, KMM_Economy 5, KMM_Elite 1, KMM_Glue 3, KMM_Town 1, KMM_Wardrobe 3

### Broken Crystal Relics  `5008103-Soulbody.mod`
- создатель: Soulbody.mod; тип: NONE; скрыта в UI (реальна в мире); персонажей: 4, уников: 0
- лидеры: Broken Crystal Guardian, Broken Crystal Guardian MkII
- расы фракции: Crystal Guardian Skeleton(100), Crystal Golem Skeleton(100); фактические: Crystal Guardian Skeleton 2, Crystal Golem Skeleton 2
- союзники после: -; враги после: Soulbodies -100, Crystal Relics -100
- снаряжение: культура: Broken SS-C High, Broken SS-C Low; носят: Soul Blade Katana 4, Soul Long Baton 4, Soul Great Sword 4, Soul Blade Nodachi 4, Soul Dual Cleaver 4
- слои KMM: KMM_Fix 4, KMM_Wardrobe 4

### Charred Skull Tribe  `5000114-Bandit Variety.mod`
- создатель: Bandit Variety.mod; тип: BANDIT; скрыта в UI (реальна в мире); персонажей: 4, уников: 1
- уники: Cannibal Grand Wizard
- лидеры: Cannibal
- расы фракции: Cannibal Skullburner(70), Cannibal Nailbiter(30); фактические: Cannibal Skullburner 3, Cannibal Bloodspiller 1, Cannibal Nailbiter 1, Cannibal 1
- города (4): Cannibal Capital[2], Charred Skull Camp[0], Charred Skull Village[3], Charred Skull Camp[0]
- регионы: Cannibal Plains
- союзники после: Kral's Chosen 27, Skull Collectors 23, Gnawed Bone Tribe 21, Fogmen 20, Berserkers 20; враги после: The Holy Nation -80, Cult of Fluorite -80, Missionaries -80, The Holy Nation -80, Preacher Cult -80
- KMM-отношения: KMM_Behavior: Bloodraiders None->-25, White Eyebrow Clan None->-21, Reavers None->15, Lost Warrior None->-60 (+135)
- conductor: arch=savage, wealth=40, strength=28, ambition=expansion, relic=None
- снаряжение: культура: -; носят: Cannibal Bucket Helmet 6, Cannibal Left Plate Arm 6, Cannibal Right Plate Arm 6, Cannibal Shin Plates 6, Cannibal Spiked Vambraces 6
- слои KMM: KMM_Behavior 1, KMM_Diplo 1, KMM_Economy 6, KMM_Fix 1, KMM_Glue 4, KMM_Wardrobe 3

### Crystal Enemys  `5008475-Crystal City.mod`
- создатель: Crystal City.mod; тип: NONE; скрыта в UI (реальна в мире); персонажей: 4, уников: 4
- уники: CGo-01 Overlord, CGo-02 Overlord, CGu-01 Overlord, CGu-02 Overlord
- расы фракции: -; фактические: Crystal Guardian Skeleton 2, Crystal Golem Skeleton 2
- города (6): Strange Crystal 01[9], Strange Crystal 02[9], Strange Crystal 03[9], Strange Crystal 04[9], Strange Crystal 05[9], Strange Crystal 06[9]
- союзники после: Cannibals 100, Fishmen 100, Fogmen 100, Gutters 100, Old Machines 100; враги после: Nameless -100
- слои KMM: KMM_Economy 4, KMM_Glue 4

### Crystal Hive  `5008750-Soulbody.mod`
- создатель: Soulbody.mod; тип: BANDIT; скрыта в UI (реальна в мире); персонажей: 4, уников: 0
- лидеры: Crystal Hive, Crystal Prince, Crystal Heavy
- расы фракции: Crystal Hive Worker(100); фактические: Crystal Hive Soldier Drone 2, Crystal Hive Prince 1, Crystal Hive Worker 1
- города (2): Crystal Deathyard[0], Crystal ancient machine[0]
- союзники после: Crystal Enemys 100, Gutters 100, Old Machines 100, Second Empire 100, Second Empire Exile 100; враги после: Soulbodies -100
- снаряжение: культура: Flat Object, Bent Object, Long Object, Ring Object; носят: Bent Object 5, Long Object 1, Ring Object 1, Flat Object 1
- слои KMM: KMM_Economy 4, KMM_Fix 4, KMM_Glue 4, KMM_Wardrobe 4

### Dust Reapers  `5003624-Bandit Variety.mod`
- создатель: Bandit Variety.mod; тип: BANDIT; персонажей: 4, уников: 1
- уники: Chakkari
- лидеры: Dust Reaper
- расы фракции: Greenlander(200), Shek(5), Scorchlander(10); фактические: Scorchlander 1
- города (2): Dust Reaper Camp[holding], Ruined Holy Outpost (override) dust reapers[5]
- союзники после: -; враги после: Police -100, Dust Bandits -100, Dust Raiders -100, Dust Lords -100, Flotsam Ninjas -100
- KMM-отношения: KMM_Behavior: The Holy Nation None->-70, Lost Warrior None->-40, Greenskins None->-30, Hatred of intelligence None->-30 (+43)
- conductor: arch=bandit, wealth=150, strength=35, ambition=enrichment, relic=None
- слои KMM: KMM_Behavior 1, KMM_Economy 3, KMM_Glue 4, KMM_Wardrobe 2

### Man-eating shark  `1070-TEXT TEXTURE.mod`
- создатель: TEXT TEXTURE.mod; тип: MILITARY; персонажей: 4, уников: 2
- уники: Man-Eating Shark - Saraga, Taniwar the Man-Eating Shark
- расы фракции: -; фактические: Astartes (Elite) 2, Astartes (The Lost) 1, Astartes (Special Gene Seed) 1
- города (2): Man-eating Shark Outpost[holding], Shark Hunt[holding]
- союзники после: -; враги после: Lost Chaos Space Marines -100
- conductor: arch=savage, wealth=240, strength=39, ambition=expansion, relic=None
- слои KMM: KMM_Economy 4, KMM_Glue 4, KMM_Wardrobe 2

### Rebel Swordsmen  `1532900-__world reactions NE.mod`
- создатель: __world reactions NE.mod; тип: BANDIT; персонажей: 4, уников: 0
- лидеры: Rebel Captain, Vigilante Chief
- расы фракции: Scorchlander(200), Greenlander(200), Hive Soldier Drone(50), Hive Worker Drone(50), Dark Hive Soldier Drone(25), Dark Hive Worker Drone(25); фактические: -
- города (3): Fort Simion (override destroyed)[4], Raider Camp (override)[0], Guard Outpost (override) rebels[9]
- союзники после: Empire Peasants 100, Anti-Slavers 100, Rebel Farmers 100, Shinobi Thieves 100, Free Traders 100; враги после: United Cities -100, Daemons -80, Lost Chaos Space Marines -80, World Devourer War Gang -80, Midnight Lord -80
- KMM-отношения: KMM_Behavior: Bloodraiders None->-15, White Eyebrow Clan None->-15, Oni None->-15, Reavers None->-35 (+54)
- conductor: arch=settler, wealth=40, strength=25, ambition=revenge, relic=None
- снаряжение: культура: Rebel Samurai Armor, Plated Tabi Boots, Quarterstaff, Broad Sabre, Dirty Vest; носят: Horse Chopper 22, Oni 20, Broad Sabre 20, Mercenary Plate 18, Mercenary Cuirass 18
- слои KMM: KMM_Behavior 1, KMM_Economy 4, KMM_Glue 5, KMM_Town 1, KMM_Wardrobe 4

### Red Hive  `1535289-Guild of Surgeons.mod`
- создатель: Guild of Surgeons.mod; тип: MILITARY; персонажей: 4, уников: 2
- уники: Brute, Redman
- лидеры: Redman
- расы фракции: Hive Prince South Hive(100), Hive Soldier Drone South Hive(100), Hive Worker Drone South Hive(100); фактические: Hive Soldier Drone South Hive 3, Hive Prince South Hive 1, Greenlander 1, Shek 1, Scorchlander 1, Skeleton 1
- союзники после: Guild of Surgeons 100, cloak shop(test) 27, Gunsmiths 21, Sultans Wares 20, Imperial Bank 20; враги после: Daemons -80, Lost Chaos Space Marines -80, World Devourer War Gang -80, Midnight Lord -80, Hatred of intelligence -80
- KMM-отношения: KMM_Behavior: Bloodraiders None->-60, White Eyebrow Clan None->-60, Oni None->-60, Reavers None->-70 (+64)
- conductor: arch=state, wealth=40, strength=25, ambition=revenge, relic=None
- слои KMM: KMM_Behavior 1, KMM_Diplo 1, KMM_Economy 4, KMM_Glue 4, KMM_Wardrobe 2

### Sailback Poachers  `5008295-Sailback.mod`
- создатель: Sailback.mod; тип: BANDIT; персонажей: 4, уников: 1
- уники: Poacher Kingpin
- лидеры: Poacher Kingpin
- расы фракции: Greenlander(100); фактические: Greenlander 1
- города (1): Poacher Camp[holding]
- союзники после: -; враги после: Wildlife -100, The Holy Nation -70, Cult of Fluorite -70, Missionaries -70, The Holy Nation -70
- KMM-отношения: KMM_Behavior: The Holy Nation None->-70, Lost Warrior None->-40, Police 0->-60, Greenskins None->-22 (+45)
- conductor: arch=bandit, wealth=150, strength=33, ambition=enrichment, relic=None
- снаряжение: культура: -; носят: Holy Chest Plate 8, Small Thieves Backpack 2
- слои KMM: KMM_Behavior 1, KMM_Economy 4, KMM_Glue 5, KMM_Wardrobe 3

### Skull Collectors  `5007294-Skull Collectors.mod`
- создатель: Skull Collectors.mod; тип: BANDIT; персонажей: 4, уников: 2
- уники: Skull Collectors Guru, Skull Collectors Head
- лидеры: Skull collector
- расы фракции: -; фактические: Shek 3, Greenlander 1
- города (2): Skull Collectors Village[holding], Skull Collectors[holding]
- союзники после: Gnawed Bone Tribe 27, Kral's Chosen 26, Charred Skull Tribe 25, Lone Berserker 23, The Hollow Feast 22; враги после: The Holy Nation -80, Cult of Fluorite -80, Missionaries -80, The Holy Nation -80, Preacher Cult -80
- KMM-отношения: KMM_Behavior: Bloodraiders None->-25, White Eyebrow Clan None->-21, Reavers None->21, Lost Warrior None->-60 (+135)
- conductor: arch=savage, wealth=240, strength=45, ambition=enrichment, relic=None
- снаряжение: культура: -; носят: Kusari Zukin 4
- слои KMM: KMM_Behavior 1, KMM_Diplo 1, KMM_Economy 4, KMM_Glue 5, KMM_Wardrobe 2

### Starving Bandits  `1305-gamedata.base`
- создатель: gamedata.base; тип: BANDIT; персонажей: 4, уников: 0
- лидеры: Hungry bandit leader, Hungry bandit, /NAME/ /BANDIT_SURNAME/
- расы фракции: Greenlander(100), Scorchlander(40), Shek(15), Hive Soldier Drone(5), Hive Worker Drone(5), Hive Prince(2); фактические: Greenlander Child 1, Scorchlander Child 1
- города (1): Starving Bandit Camp[holding]
- регионы: Arm of Okran, Bast, Bonefields, Border Zone, Darkfinger, Dreg, Grey Desert, Heng, Northern Coast, Okran's Gulf, Okran's Pride, Okran's Valley, Shem, Shun, Skimsands, Skinner's Roam, South Wetlands, Spider Plains, The Eye, The Hook, Vain
- союзники после: Steel Raiders 6; враги после: The Holy Nation -70, Cult of Fluorite -70, Missionaries -70, The Holy Nation -70, Preacher Cult -70
- KMM-отношения: KMM_Behavior: The Holy Nation None->-70, Lost Warrior None->-46, Police None->-60, Greenskins None->-30 (+47)
- conductor: arch=bandit, wealth=150, strength=41, ambition=enrichment, relic=None
- снаряжение: культура: Wheatstraw Cape, Headsheet, Bent Horse Chopper, City Half Pants, Wheatstraw Sunhat; носят: Rag Loincloth 24, Iron Club 24, Rag Shirt 19, Horse Chopper 19, Scrap Iron Stick 18
- банда outlaws: Starving Bandits
- слои KMM: KMM_Behavior 1, KMM_Economy 4, KMM_Glue 5, KMM_Wardrobe 4

### The Black Butcher  `19-Side Quest - New Frontiers.mod`
- создатель: Side Quest - New Frontiers.mod; тип: MILITARY; скрыта в UI (реальна в мире); персонажей: 4, уников: 1
- уники: The Black Butcher
- лидеры: The Black Butcher
- расы фракции: -; фактические: Skeleton 2, Skeleton P4MkII 2, Skeleton MKII Screamer 2, Skeleton No-Head MkII  1, Cannibal 1
- союзники после: Ancient Ruins 100, Wildlife 100, Old Machines 100, The Old Empire 100, Fogmen 50; враги после: -
- снаряжение: культура: Helm of the Lost, Icon of the Lost; носят: Rags of the Butcher 2, Helm of the Lost 1, Icon of the Lost 1
- слои KMM: KMM_Economy 2, KMM_Elite 1, KMM_Glue 2, KMM_Wardrobe 3

### Twinblades  `48760-Dialogue.mod`
- создатель: Dialogue.mod; тип: CIVILIAN; персонажей: 4, уников: 3
- уники: "Four Teeth" Milton, 'Four-Teeth' Milton, Big Fang
- лидеры: Big Fang, "Four Teeth" Milton, 'Four-Teeth' Milton
- расы фракции: Scorchlander(100); фактические: Scorchlander 2, Greenlander 1
- города (2): Grayflayer Village (override) twinblades[3], Smugglers Bar (override) twinblades[9]
- союзники после: Swampers 100, Holy Nation Outlaws 100, Shinobi Thieves 100; враги после: Raptors -100, Daemons -80, Lost Chaos Space Marines -80, World Devourer War Gang -80, Midnight Lord -80
- KMM-отношения: KMM_Behavior: Bloodraiders None->-15, Black Dragon Ninjas None->-8, White Eyebrow Clan None->-15, Oni None->-15 (+53)
- conductor: arch=settler, wealth=40, strength=25, ambition=expansion, relic=None
- снаряжение: культура: -; носят: Armoured Face Plates 8
- слои KMM: KMM_Atlas 1, KMM_Behavior 1, KMM_Diplo 1, KMM_Economy 3, KMM_Elite 2, KMM_Glue 3, KMM_Town 2, KMM_Wardrobe 1

### Blood Butcher Tribe  `5000113-Bandit Variety.mod`
- создатель: Bandit Variety.mod; тип: BANDIT; скрыта в UI (реальна в мире); персонажей: 3, уников: 1
- уники: Meat Lord
- лидеры: Cannibal
- расы фракции: Cannibal Bloodspiller(100); фактические: Cannibal Bloodspiller 3, Cannibal 1
- города (4): First Village[3], Blood Butcher Camp[0], Blood Butcher Village[3], Blood Butcher Camp[0]
- союзники после: Cannibals 28, Skin Bandits 23, Fogmen 21, Charred Skull Tribe 20, Gnawed Bone Tribe 20; враги после: The Holy Nation -80, Cult of Fluorite -80, Missionaries -80, The Holy Nation -80, Preacher Cult -80
- KMM-отношения: KMM_Behavior: Bloodraiders None->-22, White Eyebrow Clan None->-13, Reavers None->20, Lost Warrior None->-60 (+135)
- conductor: arch=savage, wealth=40, strength=28, ambition=expansion, relic=None
- снаряжение: культура: -; носят: Cannibal Bucket Helmet 4, Cannibal Left Plate Arm 4, Cannibal Plate Arms 4, Cannibal Plate Leggings 4, Cannibal Plate Shoes 4
- слои KMM: KMM_Behavior 1, KMM_Diplo 1, KMM_Economy 3, KMM_Glue 3, KMM_Wardrobe 2

### Cult of Goblin  `1536411-Bounties Galore.mod`
- создатель: Bounties Galore.mod; тип: BANDIT; персонажей: 3, уников: 1
- уники: The Goblin
- лидеры: The Goblin
- расы фракции: -; фактические: Hive Prince 3, Hive Soldier Drone 2, Hive Worker Drone 2
- города (3): Goblin's Hive[holding], Goblin Camp[holding], Goblin camp (override)[0]
- союзники после: Grayflayers 100, Hounds 31, Stone Rats 29, Twinblades 10; враги после: The Holy Nation -70, Cult of Fluorite -70, Missionaries -70, The Holy Nation -70, Preacher Cult -70
- KMM-отношения: KMM_Behavior: The Holy Nation None->-70, Dark Hive None->-15, Police None->-60, Holy Nation Outlaws None->-22 (+61)
- conductor: arch=bandit, wealth=240, strength=49, ambition=enrichment, relic=None
- снаряжение: культура: Plate Jacket, Cargopants [padded], Fog Mask; носят: Halfpants [sneaky chain] 14, Plate Jacket 14, Cargopants [padded] 14, Drifter's Leather Jacket 14, Fog Mask 14
- слои KMM: KMM_Behavior 1, KMM_Diplo 1, KMM_Economy 3, KMM_Elite 1, KMM_Fix 1, KMM_Glue 4, KMM_Town 1, KMM_Wardrobe 2

### Cyber Punks  `64-Towns Expansion.mod`
- создатель: Towns Expansion.mod; тип: CIVILIAN; персонажей: 3, уников: 1
- уники: Quake
- лидеры: Quake, General Screamer (The True)
- расы фракции: -; фактические: Greenlander 2, Hive Worker Drone South Hive 2, Shek 2, Scorchlander 2, Hive Soldier Drone South Hive 2, Hive Soldier Drone 2
- союзники после: Tech Hunters 100, Machinists 100, Free Traders 100; враги после: Daemons -80, Lost Chaos Space Marines -80, World Devourer War Gang -80, Midnight Lord -80, Hatred of intelligence -80
- KMM-отношения: KMM_Behavior: Bloodraiders None->-16, Black Dragon Ninjas None->-15, White Eyebrow Clan None->-15, Oni None->-14 (+54)
- снаряжение: культура: Sleeveless Dustcoat, Falling Sun, Sandogasa; носят: Sleeveless Dustcoat 15, Oldworld Bow MkII 9, Oldworld Bow MkI 8, Sandogasa 8, Fog Mask 7
- слои KMM: KMM_Behavior 1, KMM_Economy 4, KMM_Elite 2, KMM_Town 5, KMM_Wardrobe 2

### Death Watch  `463-TEXT TEXTURE.mod`
- создатель: TEXT TEXTURE.mod; тип: MILITARY; скрыта в UI (реальна в мире); персонажей: 3, уников: 3
- уники: Death Watch - Thorfinn, Deathwatch - Black Shield, Deathwatch - Black Shield Captain
- расы фракции: -; фактические: Astartes (Elite) 3
- города (1): Death Watch landing point[4]
- союзники после: Astartes survivors 80, The Lost Black Sanctuary 80, Grey Knight 80, Lost Warrior 80; враги после: Lost Chaos Space Marines -100, United Cities -100, Shek Kingdom -100, The Holy Nation -100, Daemons -100
- KMM-отношения: KMM_Behavior: Bloodraiders None->-32, White Eyebrow Clan None->-42, Oni None->-40, Reavers None->-60 (+67) | KMM_Glue: 1-KMM_Glue.mod None->40
- conductor: arch=imperium, wealth=60, strength=40, ambition=faith, relic=hunt_xenos
- гардероб: power_armor
- слои KMM: KMM_Behavior 1, KMM_Economy 3, KMM_Glue 4

### Dust Lords  `5003626-Bandit Variety.mod`
- создатель: Bandit Variety.mod; тип: BANDIT; персонажей: 3, уников: 1
- уники: Lord Drek
- лидеры: /DUST_LORD_NAME/
- расы фракции: Greenlander(100), Shek(50); фактические: Shek 1
- города (4): Dust King Tower (override) dust lords[9], Dust Lord Camp[holding], Ruined Holy Outpost (override) dust lords[4], Tiny Settlement (override) dust lords[4]
- союзники после: -; враги после: United Cities -100, Police -100, Dust Bandits -100, Dust Raiders -100, Dust Reapers -100
- KMM-отношения: KMM_Behavior: The Holy Nation None->-70, Lost Warrior None->-40, Greenskins None->-30, Hatred of intelligence None->-30 (+43)
- conductor: arch=bandit, wealth=150, strength=33, ambition=enrichment, relic=None
- слои KMM: KMM_Behavior 1, KMM_Economy 3, KMM_Fix 1, KMM_Glue 4, KMM_Wardrobe 2

### Dust Raiders  `5003620-Bandit Variety.mod`
- создатель: Bandit Variety.mod; тип: BANDIT; персонажей: 3, уников: 1
- уники: Boss /SURNAME_COMMON/
- лидеры: /DUST_BOSS_NAME/
- расы фракции: Greenlander(100); фактические: -
- города (2): Dust Raider Camp[holding], Tiny Settlement (override) dust raiders[4]
- регионы: Border Zone
- союзники после: -; враги после: United Cities -100, Police -100, Dust Bandits -100, Dust Lords -100, Dust Reapers -100
- KMM-отношения: KMM_Behavior: The Holy Nation None->-70, Lost Warrior None->-40, Greenskins None->-30, Hatred of intelligence None->-30 (+43)
- conductor: arch=bandit, wealth=150, strength=31, ambition=enrichment, relic=None
- банда outlaws: Dust Raiders
- слои KMM: KMM_Behavior 1, KMM_Economy 3, KMM_Glue 4, KMM_Wardrobe 2

### Empire Criminals  `5132108-Dark Hive.mod`
- создатель: Dark Hive.mod; тип: BANDIT; персонажей: 3, уников: 2
- уники: Atoll, Kaz
- лидеры: Atoll, Kaz
- расы фракции: -; фактические: Dark Hive Soldier Drone 1, Greenlander 1, Shek 1, Dark Hive Prince 1
- города (1): Hideout of Wanted[city]
- регионы: Howler Maze
- союзники после: -; враги после: Police -100, Cult of Fluorite -70, Missionaries -70, The Holy Nation -70, Preacher Cult -70
- KMM-отношения: KMM_Behavior: The Holy Nation None->-70, Dark Hive None->-15, Reavers None->-20, Lost Warrior None->-40 (+98)
- conductor: arch=bandit, wealth=150, strength=31, ambition=enrichment, relic=None
- снаряжение: культура: Razor Topper; носят: Razor Topper 5
- слои KMM: KMM_Behavior 1, KMM_Diplo 2, KMM_Economy 3, KMM_Fix 1, KMM_Glue 4, KMM_Wardrobe 1

### Final Enforcers  `76-Leviathan Ronin (Reloaded).mod`
- создатель: Leviathan Ronin (Reloaded).mod; тип: MILITARY; персонажей: 3, уников: 1
- уники: Wulfs
- лидеры: Final Enforcer Heavy
- расы фракции: Enforcer(100); фактические: Enforcer 3
- города (2): Airnagard[city], Mining Factory (Enforcers)[4]
- регионы: Leviathan Coast
- союзники после: Second Empire 100, Second Empire Exile 100, Old Machines 100, Ancient Ruins 100, Skeleton Legion 100; враги после: The Holy Nation -100, United Cities -100, Slave Traders -100, Traders Guild -100, Cult of Fluorite -100
- KMM-отношения: KMM_Behavior: Bloodraiders None->-60, White Eyebrow Clan None->-60, Oni None->-60, Reavers None->-70 (+64)
- conductor: arch=state, wealth=150, strength=29, ambition=expansion, relic=None
- снаряжение: культура: -; носят: Kettle Helmet 3, Heavy Samurai Armour 2
- слои KMM: KMM_Atlas 1, KMM_Behavior 1, KMM_Diplo 1, KMM_Economy 3, KMM_Glue 3, KMM_Wardrobe 3

### Gnawed Bone Tribe  `5000115-Bandit Variety.mod`
- создатель: Bandit Variety.mod; тип: BANDIT; скрыта в UI (реальна в мире); персонажей: 3, уников: 1
- уники: Marrow Lord
- лидеры: Marrow Lord
- расы фракции: Cannibal Bonespitter(100); фактические: Cannibal Bonespitter 3
- города (5): Suspicious Lab[4], Gnawed Bone Camp[0], Gnawed Bone Village[3], Gnawed Bone Camp[0], Tower Of Goats (override) bone tribe[9]
- регионы: Floodlands
- союзники после: Blood Butcher Tribe 26, Cannibals 25, Fogmen 21, Berserkers 20, Charred Skull Tribe 20; враги после: The Holy Nation -80, Cult of Fluorite -80, Missionaries -80, The Holy Nation -80, Preacher Cult -80
- KMM-отношения: KMM_Behavior: Bloodraiders None->-20, White Eyebrow Clan None->-12, Reavers None->14, Lost Warrior None->-60 (+135)
- conductor: arch=savage, wealth=40, strength=28, ambition=expansion, relic=None
- снаряжение: культура: Cannibal Spiked Heavy Plate Armor, Black Body Wrap, Cannibal Punishment Sphere; носят: Cannibal Bucket Helmet 7, Cannibal Left Plate Arm 7, Cannibal Right Plate Arm 7, Cannibal Shin Plates 7, Cannibal Spiked Vambraces 7
- слои KMM: KMM_Behavior 1, KMM_Diplo 1, KMM_Economy 3, KMM_Fix 1, KMM_Glue 3, KMM_Wardrobe 2

### Grass Pirates  `96175-rebirth.mod`
- создатель: rebirth.mod; тип: BANDIT; персонажей: 3, уников: 0
- лидеры: Straw Lieutenant, Dread Pirate Roberts
- расы фракции: Greenlander(120), Shek(60), Scorchlander(120), Hive Prince(10), Hive Prince South Hive(10), Hive Soldier Drone(15); фактические: Greenlander 1, Shek 1, Scorchlander 1, Hive Prince South Hive 1, Hive Prince 1
- города (1): Straw Bandit Camp[holding]
- регионы: Stormgap Coast, The Eye, The Outlands
- союзники после: -; враги после: United Cities -100, Police -100, Preacher Cult -70, The Holy Nation -70, Cult of Fluorite -70
- KMM-отношения: KMM_Behavior: The Holy Nation None->-70, Dark Hive None->-8, Reavers None->-21, Lost Warrior None->-40 (+98)
- conductor: arch=bandit, wealth=150, strength=31, ambition=enrichment, relic=None
- снаряжение: культура: Grass Sabre, Pirate Sabre; носят: Straightblade 4, Grass Sabre 4, Light Sabre 2, Pirate Sabre 1
- банда outlaws: Grass Pirates
- слои KMM: KMM_Behavior 1, KMM_Economy 3, KMM_Glue 4, KMM_Wardrobe 3

### Gunsmiths  `5007395-The Shoddy Firearm Mod.mod`
- создатель: The Shoddy Firearm Mod.mod; тип: ADVENTURER; персонажей: 3, уников: 1
- уники: Head Gunsmith Kaine
- лидеры: Head Gunsmith Kaine
- расы фракции: -; фактические: -
- города (1): Iron Hearth[city]
- регионы: Sinkuun
- союзники после: Tech Hunters 100, Trade Ninjas 31, Sultans Wares 27, Traders Guild 25, Wandering Cloak Shop 25; враги после: Cannibals -100, Daemons -80, Lost Chaos Space Marines -80, World Devourer War Gang -80, Midnight Lord -80
- KMM-отношения: KMM_Behavior: Bloodraiders None->-60, White Eyebrow Clan None->-60, Oni None->-60, Reavers None->-60 (+82)
- conductor: arch=trader, wealth=150, strength=33, ambition=survival, relic=None
- снаряжение: культура: Blunderbuss, Marksman Musket, Cannibalhunter Musket, Flintlock Musket, Manhunter Musket; носят: Cannibalhunter Musket 3, Patchwork Armour Jacket 1, Patchwork Leather Pants 1, Patchwork Leather Shorts 1, Junk Yard Ronin Barracuda Helmet 1
- слои KMM: KMM_Behavior 1, KMM_Economy 5, KMM_Elite 1, KMM_Wardrobe 2

### Hatred of intelligence  `3603-TEXT TEXTURE.mod`
- создатель: TEXT TEXTURE.mod; тип: MILITARY; персонажей: 3, уников: 0
- лидеры: Wandering modified products
- расы фракции: -; фактические: Skeleton MKII Screamer 2, Cannibal 1
- города (2): Broadcast Camp[holding], Chaotic and corrupted skinner's lair[holding]
- союзники после: Daemons 60, Lost Chaos Space Marines 60, World Devourer War Gang 60, Midnight Lord 60; враги после: United Cities -100, Shek Kingdom -100, The Holy Nation -100, Nameless -100, Astartes survivors -100
- KMM-отношения: KMM_Behavior: Bloodraiders None->-36, White Eyebrow Clan None->-30, Reavers None->-50, Police None->-80 (+121)
- conductor: arch=chaos, wealth=240, strength=41, ambition=expansion, relic=None
- снаряжение: культура: -; носят: Fishman Armband 2, Fishman Leg Plates 2, Fishnet Cap 2, Fishnet Skirt 2, Samurai Helmet 1
- слои KMM: KMM_Behavior 1, KMM_Economy 2, KMM_Glue 2, KMM_Wardrobe 3

### Imperial Bank  `315-social lives (UC).mod`
- создатель: social lives (UC).mod; тип: TRADER; персонажей: 3, уников: 0
- лидеры: Administrator, The Debtor Hunter
- расы фракции: Greenlander(70), Hive Prince(50), Hive Soldier Drone(10), Scorchlander(100), Shek(30); фактические: Greenlander 3, Scorchlander 3, Hive Prince 2, Skeleton 1, Hive Soldier Drone 1, Shek 1
- союзники после: Traders Guild 100, United Cities 100, Police 100, United Heroes League 50, Bounty Hunters 50; враги после: Daemons -80, Lost Chaos Space Marines -80, World Devourer War Gang -80, Midnight Lord -80, Hatred of intelligence -80
- KMM-отношения: KMM_Behavior: Bloodraiders None->-60, White Eyebrow Clan None->-60, Oni None->-60, Reavers None->-60 (+79)
- conductor: arch=trader, wealth=120, strength=20, ambition=enrichment, relic=None
- снаряжение: культура: -; носят: Plate Jacket Medium - Grey 2, Plate Pants - Grey 2, Plate Jacket Heavy - Grey 2
- слои KMM: KMM_Behavior 1, KMM_Economy 3, KMM_Glue 2, KMM_Wardrobe 3

### Iron Company  `5004537-Bandit Variety.mod`
- создатель: Bandit Variety.mod; тип: MILITARY; персонажей: 3, уников: 0
- лидеры: Empire Mercenary Captain
- расы фракции: Greenlander(100), Shek(60), Hive Soldier Drone(20), Skeleton(2); фактические: Shek 1
- союзники после: Wandering Cloak Shop 24, Guild of Surgeons 22, Traders Guild 20, Free Traders 20, Sultans Wares 20; враги после: Daemons -80, Lost Chaos Space Marines -80, World Devourer War Gang -80, Midnight Lord -80, Hatred of intelligence -80
- KMM-отношения: KMM_Behavior: Bloodraiders None->-60, White Eyebrow Clan None->-60, Oni None->-60, Reavers None->-70 (+65)
- conductor: arch=state, wealth=40, strength=25, ambition=revenge, relic=None
- снаряжение: культура: -; носят: Samurai Armor - Superheavy 1, Samurai Armour - Light 1
- слои KMM: KMM_Atlas 2, KMM_Behavior 1, KMM_Economy 1, KMM_Glue 1, KMM_Wardrobe 3

### Lake Threshers  `53-Animal Variations.mod`
- создатель: Animal Variations.mod; тип: BANDIT; персонажей: 3, уников: 1
- уники: Big Skim
- расы фракции: Greenlander(100), Scorchlander(100), Shek(100), Hive Prince(25); фактические: Greenlander 1
- союзники после: Skimmers 100, Twinblades 7, Grayflayers 3, Wildlife 2; враги после: Swamp Ninjas -100, Red Sabres -100, Swampers -6, Blackshifters -3
- KMM-отношения: KMM_Behavior: Grayflayers 0->3, Wildlife 0->2, Twinblades 0->7, Swampers 0->-6 (+1)
- слои KMM: KMM_Behavior 1, KMM_Economy 3, KMM_Glue 4, KMM_Wardrobe 2

### Manhunters  `54587-rebirth.mod`
- создатель: rebirth.mod; тип: MILITARY; персонажей: 3, уников: 1
- уники: Manhunter Boss
- лидеры: Manhunter Boss
- расы фракции: Hive Soldier Drone(75), Scorchlander(100), Shek(100), Greenlander(100), Dark Hive Soldier Drone(20), Hive Prince(10); фактические: -
- города (1): Manhunter Base[holding]
- регионы: The Hook
- союзники после: Slave Traders 100, Free Traders 25, Imperial Bank 25, cloak shop(test) 23, Guild of Surgeons 21; враги после: Anti-Slavers -100, Daemons -80, Lost Chaos Space Marines -80, World Devourer War Gang -80, Midnight Lord -80
- KMM-отношения: KMM_Behavior: Bloodraiders None->-60, Oni None->-60, Reavers None->-70, Band of Bones None->-70 (+63)
- conductor: arch=state, wealth=150, strength=43, ambition=expansion, relic=None
- снаряжение: культура: -; носят: Masked Helmet 9, BH (Heavy) Leather 9, BH Boots 9, BH Clothpants 9, BH Leather Boots 9
- слои KMM: KMM_Behavior 1, KMM_Economy 7, KMM_Fix 1, KMM_Glue 3, KMM_Wardrobe 3

### Rebirth Slaves  `49392-rebirth.mod`
- создатель: rebirth.mod; тип: SLAVE; скрыта в UI (реальна в мире); персонажей: 3, уников: 1
- уники: Snitch
- расы фракции: Greenlander(100), Hive Prince(5), Scorchlander(50), Shek(500), Hive Soldier Drone(10), Hive Worker Drone(20); фактические: Shek Child 1, Greenlander Child 1, Scorchlander Child 1, Greenlander 1
- союзники после: -; враги после: -
- слои KMM: KMM_Merged 1

### Skin Bandits  `63028-Dialogue.mod`
- создатель: Dialogue.mod; тип: BANDIT; персонажей: 3, уников: 1
- уники: Savant
- лидеры: Savant
- расы фракции: Screamer MkI(25), P4 Unit(10); фактические: Scorchlander 1, Screamer MkI 1, P4 Unit 1
- города (5): Skinhouse HQ[holding], Horrible Ruin[holding], Skinhouse[holding], Skinhouse Lookout[7], Police Barracks (Skinhouse)[7]
- регионы: Bonefields, Sniper Valley, Sonorous Dark, Stobe's Garden, The Crags, The Pits
- союзники после: Band of Bones 26, Skull Collectors 25, Fogmen 20, Blood Butcher Tribe 20, Charred Skull Tribe 20; враги после: Reavers -100, Crab Raiders -100, United Cities -100, Skeleton Bandits -100, Skeleton Legion -100
- KMM-отношения: KMM_Behavior: Bloodraiders None->-12, White Eyebrow Clan None->-20, Lost Warrior None->-60, Police None->-70 (+132)
- conductor: arch=savage, wealth=330, strength=81, ambition=revenge, relic=None
- снаряжение: культура: Flesh Picker, Human Skin Suit, Human Skin, Scorchlander Skin, Scorchlander Skin Suit; носят: Human Skin Suit 17, Human Skin 14, Scorchlander Skin 14, Scorchlander Skin Suit 14, Flesh Picker 14
- гардероб: pagan
- банда outlaws: Skin Bandits
- слои KMM: KMM_Behavior 1, KMM_Economy 8, KMM_Elite 1, KMM_Fix 1, KMM_Glue 4, KMM_Wardrobe 2

### Spiders  `51331-rebirth.mod`
- создатель: rebirth.mod; тип: BANDIT; скрыта в UI (реальна в мире); персонажей: 3, уников: 2
- уники: Blaze, Bugmaster
- расы фракции: -; фактические: Greenlander 2, Hive Soldier Drone South Hive 1
- города (5): Throne of the Bugmaster[9], Skin Spider Nest[0], Exile Camp (Spiders)[9], Spider Den[9], Spider Nest[0]
- союзники после: Blood Spiders 100, Grievewraiths 100; враги после: -
- Cleanup: лагеря ['Spider Den'], хост []
- слои KMM: KMM_Cleanup 1, KMM_Diplo 1, KMM_Economy 2, KMM_Fix 1, KMM_Glue 2

### Stone Rats  `48753-Dialogue.mod`
- создатель: Dialogue.mod; тип: CIVILIAN; персонажей: 3, уников: 2
- уники: Big Al, Territorial Thug
- лидеры: Big Al
- расы фракции: Greenlander(100), Hive Prince(100), Scorchlander(100), Shek(100), Dark Hive Prince(23), Dark Hive Worker Drone(15); фактические: Shek 1
- города (1): Stone Rat Village[holding]
- регионы: The Swamp
- союзники после: Swampers 100, Holy Nation Outlaws 100, Shinobi Thieves 100; враги после: Raptors -100, Spiders -100, Daemons -80, Lost Chaos Space Marines -80, World Devourer War Gang -80
- KMM-отношения: KMM_Behavior: Bloodraiders None->-18, Black Dragon Ninjas None->-7, White Eyebrow Clan None->-15, Oni None->-15 (+53)
- conductor: arch=settler, wealth=150, strength=43, ambition=survival, relic=None
- снаряжение: культура: Cargopants [reinforced], Unholy Bucket Zukin; носят: Heart Protector 17, Mercenary Leather Armour 16, Spiked Helmet 16, Unholy Bucket Zukin 16, Leather Armor - Light 16
- слои KMM: KMM_Atlas 1, KMM_Behavior 1, KMM_Diplo 1, KMM_Economy 4, KMM_Glue 3, KMM_Town 1, KMM_Wardrobe 1

### Victor's Hideout  `981-Companion Quest - Morse.mod`
- создатель: Companion Quest - Morse.mod; тип: CIVILIAN; скрыта в UI (реальна в мире); персонажей: 3, уников: 1
- уники: Victor
- расы фракции: Greenlander(100), Scorchlander(100), Hive Prince(20); фактические: Greenlander 3, Scorchlander 2
- города (1): Victor's House[9]
- союзники после: Swamp Ninjas 35, Red Sabres 35, Wildlife 10, Big Dave's Ninjas 5; враги после: -
- слои KMM: KMM_Economy 2, KMM_Fix 1, KMM_Glue 2, KMM_Wardrobe 2

### White Eyebrow Clan  `18011-rebirth.mod`
- создатель: rebirth.mod; тип: BANDIT; персонажей: 3, уников: 1
- уники: White Eyebrow
- лидеры: White Eyebrow
- расы фракции: Scorchlander(90), Greenlander(10), Hive Soldier Drone(1), Shek(5); фактические: Scorchlander 1
- города (5): White Eyebrow Camp[holding], Tower Of Ninjas (override) White Eyebrows[9], White Eyebrow Camp[holding], White Eyebrow Tower[holding], White Eyebrow Tower[holding]
- регионы: The Swamp
- союзники после: Crystal Relics 4; враги после: Black Dragon Ninjas -100, United Cities -100, Dust Bandits -100, The Holy Nation -70, Cult of Fluorite -70
- KMM-отношения: KMM_Behavior: The Holy Nation None->-70, Dark Hive None->-15, Reavers None->-23, Lost Warrior None->-40 (+100)
- conductor: arch=bandit, wealth=420, strength=73, ambition=enrichment, relic=None
- снаряжение: культура: Gi Pants, Gi; носят: Gi Pants 12, Gi 12
- слои KMM: KMM_Behavior 1, KMM_Diplo 1, KMM_Economy 6, KMM_Elite 2, KMM_Glue 4, KMM_Wardrobe 2

### Witches  `1535868-Bounties Galore.mod`
- создатель: Bounties Galore.mod; тип: BANDIT; скрыта в UI (реальна в мире); персонажей: 3, уников: 3
- уники: Crone Eldest Daughter, Crone Youngest Daughter, The Crone
- лидеры: The Crone, Crone Eldest Daughter, Crone Youngest Daughter
- расы фракции: Greenlander(100); фактические: -
- города (1): Witches' Huts[9]
- союзники после: Fishmen 50, Crab Raiders 50; враги после: -
- снаряжение: культура: -; носят: Ninja Rags 5, Ashland Hat 2
- Cleanup: лагеря ["Witches' Huts"], хост []
- слои KMM: KMM_Cleanup 4, KMM_Diplo 1, KMM_Economy 3, KMM_Fix 1, KMM_Glue 3

### Blood Wolves  `39-Sacred Trash.mod`
- создатель: Sacred Trash.mod; тип: BANDIT; персонажей: 2, уников: 0
- расы фракции: Greenlander(100), Scorchlander(100), Hive Prince(10), Shek(15); фактические: -
- города (1): Den[city]
- союзники после: -; враги после: The Holy Nation -70, Cult of Fluorite -70, Missionaries -70, The Holy Nation -70, Preacher Cult -70
- KMM-отношения: KMM_Behavior: The Holy Nation None->-70, Dark Hive None->-15, Reavers None->-20, Lost Warrior None->-42 (+100)
- conductor: arch=bandit, wealth=150, strength=27, ambition=enrichment, relic=None
- слои KMM: KMM_Behavior 1, KMM_Economy 2, KMM_Glue 3, KMM_Wardrobe 1

### Bloodraiders  `16860-gamedata.base`
- создатель: gamedata.base; тип: BANDIT; персонажей: 2, уников: 0
- лидеры: Blood Boss
- расы фракции: Greenlander(160), Shek(80), Greenlander Child(0), Shek Child(0), Scorchlander(60), Hive Prince(10); фактические: Greenlander 1, Shek 1, Greenlander Child 1, Shek Child 1
- города (3): Blood Bandit Camp[holding], Blood Bandit Camp HN[holding], Blood Bandit Camp UC[holding]
- регионы: Arm of Okran, Grey Desert, Okran's Pride, Sinkuun, Skimsands, Spine Canyon, The Eye, The Great Desert
- союзники после: -; враги после: The Holy Nation -70, Cult of Fluorite -70, Missionaries -70, The Holy Nation -70, Preacher Cult -70
- KMM-отношения: KMM_Behavior: The Holy Nation None->-70, Dark Hive None->-14, Reavers None->-17, Lost Warrior None->-42 (+100)
- conductor: arch=bandit, wealth=510, strength=85, ambition=enrichment, relic=None
- снаряжение: культура: Bloodied Raider Plate, Bloodied Raider Helm, Blood Boss Mask, Blood Cleaver, Blood Sabre; носят: Hack Stopper Pants 10, Bloodied Raider Helm 10, Bloodied Raider Plate 10, Blood Cleaver 10, Flesh Cleaver 5
- гардероб: pagan
- банда outlaws: Bloodraiders
- слои KMM: KMM_Behavior 1, KMM_Economy 2, KMM_Glue 3, KMM_Wardrobe 2

### Drifters  `3144-Band of Exiles.mod`
- создатель: Band of Exiles.mod; тип: ADVENTURER; скрыта в UI (реальна в мире); персонажей: 2, уников: 2
- уники: Bishop, Estelle
- лидеры: Bishop, Estelle
- расы фракции: -; фактические: Greenlander 2
- союзники после: Tech Hunters 100, Shinobi Thieves 100, Anti-Slavers 100, Drifters 100; враги после: -
- снаряжение: культура: This Machine, Tanegashima Pistol, Keratin Plate Jacket, Hazards Shell - 8-Ball [upper], Oldworld Bow MkIII; носят: Straw Hat 29, Halfpants (ragged) 26, Drifter's Leather Pants 22, Cargopants 21, Drifter's Leather Jacket 18
- гардероб: uniforms:samurai(char)
- слои KMM: KMM_Economy 1, KMM_Glue 1, KMM_Town 1

### Fish Isle  `25-AnnexFishmanIsland.mod`
- создатель: AnnexFishmanIsland.mod; тип: NONE; скрыта в UI (реальна в мире); персонажей: 2, уников: 1
- уники: Ms. Salt
- лидеры: Ms. Salt
- расы фракции: Hive Worker Drone South Hive(100); фактические: Hive Soldier Drone South Hive 1
- города (3): Fish Isle (Annexed)[3], Island Lab (Annexed)[1], RETIRED Fish Isle (Annexed with Crab)[3]
- союзники после: Nameless 100, South Exiles 100; враги после: Fishmen -100, Crabs -100
- снаряжение: культура: -; носят: Blackened Chain Hive Shirt 5, Hiver Chain Shirt 4
- слои KMM: KMM_Wardrobe 1

### Grey Knight  `759-TEXT TEXTURE.mod`
- создатель: TEXT TEXTURE.mod; тип: MILITARY; скрыта в UI (реальна в мире); персонажей: 2, уников: 2
- уники: Grey Knight - Lord Garan Crow, Grey Knight - Shield Terminator
- лидеры: Grey Knight - Shield Terminator
- расы фракции: -; фактические: Astartes (Elite) 2
- города (2): Devil's Hideout[4], Silent Camp[4]
- союзники после: Astartes survivors 80, The Lost Black Sanctuary 80, Death Watch 80, Lost Warrior 80; враги после: Lost Chaos Space Marines -100, United Cities -100, Shek Kingdom -100, The Holy Nation -100, Daemons -100
- KMM-отношения: KMM_Behavior: Bloodraiders None->-39, White Eyebrow Clan None->-40, Oni None->-40, Reavers None->-60 (+67) | KMM_Glue: 1-KMM_Glue.mod None->40
- conductor: arch=imperium, wealth=60, strength=40, ambition=faith, relic=hunt_chaos
- снаряжение: культура: -; носят: Elite Power Armor Liner 1, Grey Knight - Holy Shield Terminator Precision Power Helmet 1, Grey Knight - Shield Terminator Advanced Power Armor 1, Grey Knight - Holy Shield Terminator Masterfully Crafted Power Leg Armor 1, Gray Knight - Holy Shield Terminator Precision Power Combat Boots 1
- гардероб: power_armor
- Cleanup: лагеря ['Silent Camp'], хост []
- слои KMM: KMM_Behavior 1, KMM_Cleanup 2, KMM_Diplo 1, KMM_Economy 2, KMM_Glue 3

### Gunsmiths  `25-BlackPowder.mod`
- создатель: BlackPowder.mod; тип: CIVILIAN; персонажей: 2, уников: 0
- лидеры: Dreg Gunsmith
- расы фракции: Shek(100), Greenlander(100), Scorchlander(100), Skeleton(5), Hive Soldier Drone(20), Hive Prince(10); фактические: -
- города (1): Dreg Gunworks[2]
- союзники после: Machinists 100, Mongrel 100, Cannibal Hunters 100, cloak shop(test) 33, Bounty Hunters 28; враги после: Daemons -80, Lost Chaos Space Marines -80, World Devourer War Gang -80, Midnight Lord -80, Hatred of intelligence -80
- KMM-отношения: KMM_Behavior: Bloodraiders None->-60, White Eyebrow Clan None->-60, Oni None->-60, Reavers None->-60 (+82)
- conductor: arch=trader, wealth=150, strength=29, ambition=survival, relic=None
- снаряжение: культура: Blunderbuss, Marksman Musket, Cannibalhunter Musket, Flintlock Musket, Manhunter Musket; носят: Cannibalhunter Musket 3, Patchwork Armour Jacket 1, Patchwork Leather Pants 1, Patchwork Leather Shorts 1, Junk Yard Ronin Barracuda Helmet 1
- Cleanup: лагеря ['Dreg Gunworks'], хост []
- слои KMM: KMM_Behavior 1, KMM_Cleanup 2, KMM_Economy 2, KMM_Wardrobe 2

### Holy Nation Outlaws  `6485-Band of Exiles.mod`
- создатель: Band of Exiles.mod; тип: BANDIT; скрыта в UI (реальна в мире); персонажей: 2, уников: 2
- уники: Bread, Hisham
- лидеры: Bread, Hisham
- расы фракции: -; фактические: Cannibal Skav 1, Greenlander 1
- союзники после: -; враги после: Daemons -80, Lost Chaos Space Marines -80, World Devourer War Gang -80, Midnight Lord -80, Hatred of intelligence -80
- KMM-отношения: KMM_Behavior: Bloodraiders None->-21, Black Dragon Ninjas None->-16, White Eyebrow Clan None->-15, Oni None->-15 (+54)
- снаряжение: культура: Melinda's Naginata, Dyed Trousers; носят: Stout Hessian Uniform 25, Cloth Shirt 23, Dyed Trousers 23, Iron Club 22, Combat Cleaver 21
- гардероб: no_firearms
- слои KMM: KMM_Behavior 1, KMM_Economy 1, KMM_Glue 1

### Lost Chaos Space Marines  `143-TEXT TEXTURE.mod`
- создатель: TEXT TEXTURE.mod; тип: CIVILIAN; персонажей: 2, уников: 1
- уники: Iron Warrior - Collector
- лидеры: Iron Warrior - Collector
- расы фракции: -; фактические: Astartes (Elite) 1, Astartes (The Lost) 1
- города (1): The Collector's Nest[holding]
- союзники после: Daemons 60, World Devourer War Gang 60, Midnight Lord 60, Hatred of intelligence 60; враги после: Nameless -100, Astartes survivors -100, The Lost Black Sanctuary -100, Death Watch -100, Grey Knight -100
- KMM-отношения: KMM_Behavior: Bloodraiders None->-32, White Eyebrow Clan None->-31, Reavers None->-50, Lost Warrior None->-100 (+134) | KMM_Glue: 1-KMM_Glue.mod None->-100
- conductor: arch=chaos, wealth=350, strength=79, ambition=faith, relic=spread_chaos
- снаряжение: культура: -; носят: Iron Warrior - Unyielding Terminator Helmet 1, Iron Warrior - Unyielding Terminator Power Armor 1, Iron Warrior - Unyielding Terminator Power Leg Armor 1, Collector's Unyielding Terminator Power Combat Boots 1, The Collector's Unyielding Terminator Power Armor 1
- гардероб: power_armor
- слои KMM: KMM_Behavior 1, KMM_Diplo 1, KMM_Economy 2, KMM_Glue 3, KMM_Wardrobe 1

### Missionaries  `220-Travelling Civilians.mod`
- создатель: Travelling Civilians.mod; тип: CIVILIAN; скрыта в UI (реальна в мире); персонажей: 2, уников: 0
- лидеры: Holy Missionary
- расы фракции: -; фактические: Greenlander 1
- союзники после: The Holy Nation 30, Cult of Fluorite 30, The Holy Nation 30, Preacher Cult 30; враги после: Daemons -90, Lost Chaos Space Marines -90, World Devourer War Gang -90, Midnight Lord -90, Hatred of intelligence -90
- KMM-отношения: KMM_Behavior: Bloodraiders None->-70, White Eyebrow Clan None->-70, The Holy Nation None->30, Oni None->-70 (+67)
- conductor: arch=religion, wealth=50, strength=26, ambition=faith, relic=None
- снаряжение: культура: -; носят: Monk Pants 1, Monk Robe 1
- слои KMM: KMM_Behavior 1, KMM_Economy 1, KMM_Glue 1, KMM_Wardrobe 2

### Nomadic Skeletons  `1535182-PAK_Unit.mod`
- создатель: PAK_Unit.mod; тип: CIVILIAN; персонажей: 2, уников: 0
- лидеры: Shepherd Trader
- расы фракции: Skeleton(100), P4 Unit(4); фактические: -
- союзники после: Floodlands Skeletons 60, Cyborgs 60, Skeleton Sultans 60, Old Machines 60, Machinists 60; враги после: Daemons -80, The Holy Nation -80, Cult of Fluorite -80, Lost Chaos Space Marines -80, World Devourer War Gang -80
- KMM-отношения: KMM_Behavior: Bloodraiders None->-20, White Eyebrow Clan None->-20, The Holy Nation None->-80, Oni None->-20 (+72)
- conductor: arch=robot, wealth=40, strength=32, ambition=survival, relic=None
- слои KMM: KMM_Behavior 1, KMM_Economy 3, KMM_Glue 2, KMM_Wardrobe 2

### Orphans  `1800-ChildrenOfKenshi.mod`
- создатель: ChildrenOfKenshi.mod; тип: CIVILIAN; скрыта в UI (реальна в мире); персонажей: 2, уников: 0
- лидеры: Orphan
- расы фракции: -; фактические: Shek Child 2, Greenlander Child 1, Scorchlander Child 1
- союзники после: Anti-Slavers 100, Flotsam Ninjas 100, Shinobi Thieves 100, Drifters 100, Tech Hunters 100; враги после: -
- снаряжение: культура: -; носят: Holy Servant Rags 4
- слои KMM: KMM_Atlas 1, KMM_Economy 2, KMM_Glue 2, KMM_Wardrobe 2

### Red Sabres  `51652-rebirth.mod`
- создатель: rebirth.mod; тип: BANDIT; персонажей: 2, уников: 1
- уники: Red Sabre Boss
- расы фракции: Greenlander(100), Scorchlander(100), Shek(100), Greenlander Child(0), Scorchlander Child(0), Shek Child(0); фактические: Greenlander 2, Shek 1, Scorchlander 1, Scorchlander Child 1, Shek Child 1, Greenlander Child 1
- города (3): Swamp Hideout[holding], Swamp Ninja Base (override) sabers[9], Red Sabre Camp[holding]
- регионы: The Swamp
- союзники после: Stone Rats 4, Grayflayers 1; враги после: Swamp Ninjas -100, Spiders -100, The Holy Nation -70, Cult of Fluorite -70, Missionaries -70
- KMM-отношения: KMM_Behavior: The Holy Nation None->-70, Dark Hive None->-9, Reavers None->-20, Lost Warrior None->-38 (+97)
- conductor: arch=bandit, wealth=240, strength=45, ambition=enrichment, relic=None
- снаряжение: культура: Armored Legwraps of Hive, Reverse Sabre; носят: Armored Rag Skirt - Heavy (colored) 3, Hive Soldier Armored rags 3, Armored Ragboots of Hive 3, Armored Legwraps of Hive 3, Rag Legwear of Hive 3
- слои KMM: KMM_Behavior 1, KMM_Diplo 1, KMM_Economy 2, KMM_Fix 1, KMM_Glue 3, KMM_Wardrobe 1

### Slaves  `57740-rebirth.mod`
- создатель: rebirth.mod; тип: SLAVE; скрыта в UI (реальна в мире); персонажей: 2, уников: 0
- лидеры: Escape slave Empire, Escaped Child Slave, Slave
- расы фракции: -; фактические: Greenlander 1, Scorchlander 1
- союзники после: -; враги после: -
- снаряжение: культура: -; носят: Rough Tunic 4, Prisoner Shackles 1
- слои KMM: KMM_Merged 1

### The Fallen Gang  `117-Towns Expansion.mod`
- создатель: Towns Expansion.mod; тип: BANDIT; персонажей: 2, уников: 1
- уники: Ludin
- лидеры: Ludin
- расы фракции: Greenlander(100); фактические: -
- союзники после: -; враги после: Shek Kingdom -100, The Syndicate -100, The Holy Nation -70, Cult of Fluorite -70, Missionaries -70
- KMM-отношения: KMM_Behavior: The Holy Nation None->-70, Dark Hive None->-15, Reavers None->-20, Lost Warrior None->-40 (+99)
- снаряжение: культура: Unholy Chest Plate; носят: Paladin's Heavy Hachigane 10, Paladin's Cross 10, Bucket Zukin 9, Unholy Chest Plate 9
- слои KMM: KMM_Behavior 1, KMM_Economy 3, KMM_Elite 1, KMM_Wardrobe 1

### The Gorrillo Bandits  `96261-rebirth.mod`
- создатель: rebirth.mod; тип: BANDIT; персонажей: 2, уников: 1
- уники: Gorrillo
- расы фракции: Greenlander(100), Scorchlander(100), Shek(100), Hazards Unit(3); фактические: Greenlander 1
- города (1): The Old Prison[holding]
- регионы: Bonefields, Flats Lagoon, High Bonefields
- союзники после: -; враги после: The Holy Nation -70, Cult of Fluorite -70, Missionaries -70, The Holy Nation -70, Preacher Cult -70
- KMM-отношения: KMM_Behavior: The Holy Nation None->-70, Dark Hive None->-15, Reavers None->-14, Lost Warrior None->-40 (+101)
- conductor: arch=bandit, wealth=150, strength=31, ambition=enrichment, relic=None
- банда outlaws: The Gorrillo Bandits
- слои KMM: KMM_Behavior 1, KMM_Economy 2, KMM_Fix 1, KMM_Glue 3, KMM_Wardrobe 1

### The Hollow Feast  `5007715-ChildrenOfKenshi.mod`
- создатель: ChildrenOfKenshi.mod; тип: BANDIT; персонажей: 2, уников: 1
- уники: The Mutilator
- лидеры: The Mutilator
- расы фракции: Greenlander(100), Hive Prince(5), Hive Soldier Drone(10), Hive Worker Drone(10), Scorchlander(100), Shek(50); фактические: Greenlander 1
- города (2): Old Wreckage[holding], Old Wreckage (STORY)[1]
- союзники после: Slave Hunters 75, Slave Traders 75, Crab Raiders 27, Berserkers 24, Charred Skull Tribe 24; враги после: Anti-Slavers -100, The Holy Nation -80, Cult of Fluorite -80, Missionaries -80, The Holy Nation -80
- KMM-отношения: KMM_Behavior: Bloodraiders None->-20, White Eyebrow Clan None->-20, Reavers None->20, Lost Warrior None->-60 (+132)
- conductor: arch=savage, wealth=150, strength=31, ambition=enrichment, relic=None
- снаряжение: культура: Mutilator Mask, Weird Coat, Mutilator Skirt, The Great Cleaver; носят: Mask Type III 5, Flesh Cleaver 5, Mutilator Skirt 1, The Great Cleaver 1, Mutilator Mask 1
- слои KMM: KMM_Behavior 1, KMM_Diplo 1, KMM_Economy 3, KMM_Glue 3, KMM_Wardrobe 1

### The Syndicate  `18-Towns Expansion.mod`
- создатель: Towns Expansion.mod; тип: BANDIT; персонажей: 2, уников: 1
- уники: Big Red
- лидеры: Big Red
- расы фракции: Hive Soldier Drone South Hive(10), Hive Worker Drone South Hive(10), Hive Prince South Hive(1); фактические: Hive Prince South Hive 1
- города (1): Skyscrap[holding]
- регионы: Border Zone
- союзники после: -; враги после: The Fallen Gang -100, Grayflayers -100, Holy Nation Outlaws -100, The Holy Nation -70, Cult of Fluorite -70
- KMM-отношения: KMM_Behavior: The Holy Nation None->-70, Dark Hive None->-15, Reavers None->-20, Lost Warrior None->-39 (+98)
- conductor: arch=bandit, wealth=150, strength=33, ambition=enrichment, relic=None
- снаряжение: культура: -; носят: Flesh Cleaver 6
- слои KMM: KMM_Atlas 1, KMM_Behavior 1, KMM_Economy 3, KMM_Elite 1, KMM_Wardrobe 1

### Wayfarers  `167-Travelling Civilians.mod`
- создатель: Travelling Civilians.mod; тип: CIVILIAN; скрыта в UI (реальна в мире); персонажей: 2, уников: 0
- лидеры: Crab Raider Wayfarer (Desert), Crab Raider Wayfarer (Holy Lands)
- расы фракции: -; фактические: -
- союзники после: -; враги после: -
- слои KMM: KMM_Economy 2, KMM_Glue 2, KMM_Wardrobe 2

### Yabuta Outlaws  `1532482-__May 18 2.mod`
- создатель: __May 18 2.mod; тип: BANDIT; персонажей: 2, уников: 1
- уники: Yabuta Chief
- лидеры: Yabuta Chief
- расы фракции: Greenlander(100), Shek(100), Hive Soldier Drone(30), Dark Hive Soldier Drone(8), Dark Hive Worker Drone(7), Dark Hive Prince(4); фактические: -
- города (2): Fort Yabuta[1], Stoat (override) Yabuta[4]
- регионы: Bast, Grey Desert, Heng, Sinkuun, Skimsands, The Great Desert, The Hook
- союзники после: -; враги после: The Holy Nation -70, Cult of Fluorite -70, Missionaries -70, The Holy Nation -70, Preacher Cult -70
- KMM-отношения: KMM_Behavior: The Holy Nation None->-70, Dark Hive None->-15, Reavers None->-15, Lost Warrior None->-42 (+101)
- conductor: arch=bandit, wealth=40, strength=25, ambition=revenge, relic=None
- снаряжение: культура: -; носят: Turtleneck 8, Bucket Zukin 7, Tin Can 7, Spiked Helmet (Fullface) 7, Unholy Bucket Zukin 7
- банда outlaws: Yabuta Outlaws
- слои KMM: KMM_Behavior 1, KMM_Economy 2, KMM_Elite 1, KMM_Fix 1, KMM_Glue 3, KMM_Town 2, KMM_Wardrobe 1

### 祭品  `180-KillerRobot.mod`
- создатель: KillerRobot.mod; тип: CIVILIAN; персонажей: 2, уников: 0
- лидеры: Cannibal Chief /CANNIBAL_NAME/, 待改造的囚犯, Samurai Captain
- расы фракции: -; фактические: Greenlander 1, Shek 1, Hive Worker Drone South Hive 1, Scorchlander 1, Hive Soldier Drone South Hive 1, Screamer MkI 1
- союзники после: cloak shop(test) 17, Free Traders 11, Sultans Wares 11, Traders Guild 10, Guild of Surgeons 10; враги после: Cannibals -200, Daemons -80, Lost Chaos Space Marines -80, World Devourer War Gang -80, Midnight Lord -80
- KMM-отношения: KMM_Behavior: Bloodraiders None->-19, White Eyebrow Clan None->-10, Oni None->-15, Reavers None->-40 (+70)
- снаряжение: культура: -; носят: Ronin Armour 3, Azuchi Blue Heavy Pants 3, Reinforced Samurai Hive Soldier Helmet 3, Samurai Helmet 2, Cannibal Plate Leggings 2
- слои KMM: KMM_Behavior 1, KMM_Economy 2, KMM_Wardrobe 2

### Band of Blades  `5003905-Bandit Variety.mod`
- создатель: Bandit Variety.mod; тип: ADVENTURER; персонажей: 1, уников: 0
- лидеры: Outcast Warrior, Guardian Outcast
- расы фракции: Shek(100); фактические: Shek 1
- города (1): Exile Camp[holding]
- регионы: Flats Lagoon, The Swamp
- союзники после: -; враги после: Bloodraiders -100, Shek Kingdom -100, Slave Traders -100, The Holy Nation -100, Dust Bandits -100
- KMM-отношения: KMM_Behavior: Black Dragon Ninjas None->-15, White Eyebrow Clan None->-15, Oni None->-8, Reavers None->-48 (+50)
- conductor: arch=settler, wealth=150, strength=33, ambition=survival, relic=None
- снаряжение: культура: -; носят: Moon Cleaver 6
- банда outlaws: Band of Blades
- слои KMM: KMM_Behavior 1, KMM_Economy 1, KMM_Glue 1, KMM_Town 1, KMM_Wardrobe 1

### Blood Spiders  `44-Symbiosis.mod`
- создатель: Symbiosis.mod; тип: BANDIT; скрыта в UI (реальна в мире); персонажей: 1, уников: 1
- уники: Mad Recluse
- расы фракции: -; фактические: Skeleton P4MkII 1
- города (3): Tower of Spiders[9], Rot (override) spiders[4], Blood Spider Nest[0]
- союзники после: Spiders 100, Grievewraiths 100; враги после: Bog Dogs -100
- слои KMM: KMM_Diplo 1, KMM_Economy 1, KMM_Glue 1

### Broken Ones  `64918-rebirth.mod`
- создатель: rebirth.mod; тип: BANDIT; скрыта в UI (реальна в мире); персонажей: 1, уников: 0
- расы фракции: Soldierbot(100); фактические: Soldierbot 1
- союзники после: -; враги после: -
- снаряжение: культура: -; носят: Old Empire Club 1, Kogatetsubo 1
- слои KMM: KMM_Economy 1, KMM_Glue 1, KMM_Wardrobe 1

### Catun  `5008721-Kaizo.mod`
- создатель: Kaizo.mod; тип: CIVILIAN; персонажей: 1, уников: 1
- уники: Scrapmaster Mori
- расы фракции: Greenlander(200), Scorchlander(150), Shek(25), Hive Soldier Drone(10), Hive Prince(10); фактические: -
- города (1): Catun (override) free city[2]
- союзники после: Slave Traders 50, Traders Guild 50, United Cities 50; враги после: Daemons -80, Lost Chaos Space Marines -80, World Devourer War Gang -80, Midnight Lord -80, Hatred of intelligence -80
- KMM-отношения: KMM_Behavior: Bloodraiders None->-15, Black Dragon Ninjas None->-15, White Eyebrow Clan None->-15, Oni None->-15 (+53)
- conductor: arch=settler, wealth=50, strength=22, ambition=survival, relic=None
- слои KMM: KMM_Atlas 1, KMM_Behavior 1, KMM_Diplo 1

### Desert Divers  `1535099-Desert divers.mod`
- создатель: Desert divers.mod; тип: ADVENTURER; персонажей: 1, уников: 0
- лидеры: Desert Diver
- расы фракции: Greenlander(100); фактические: -
- союзники после: Machinists 100, Mongrel 100, Cannibal Hunters 100, Tech Hunters 100, Anti-Slavers 9; враги после: Daemons -80, Lost Chaos Space Marines -80, World Devourer War Gang -80, Midnight Lord -80, Hatred of intelligence -80
- KMM-отношения: KMM_Behavior: Bloodraiders None->-15, Black Dragon Ninjas None->-10, White Eyebrow Clan None->-17, Oni None->-19 (+55)
- conductor: arch=settler, wealth=50, strength=22, ambition=survival, relic=None
- снаряжение: культура: -; носят: Crab Shoes 5, Crab Trousers 5, Crab Armour 5
- слои KMM: KMM_Behavior 1, KMM_Economy 3, KMM_Wardrobe 1

### Floodlands Skeletons  `1536037-Bounties Galore.mod`
- создатель: Bounties Galore.mod; тип: ADVENTURER; персонажей: 1, уников: 1
- уники: Sarin
- лидеры: Sarin
- расы фракции: Skeleton(100), P4 Unit(4); фактические: P4 Unit 1
- города (1): Spider Workshop[9]
- союзники после: Nomadic Skeletons 60, Old Machines 60, Skeletons 60, Cyborgs 60, Skeleton Sultans 60; враги после: Daemons -80, The Holy Nation -80, Cult of Fluorite -80, Lost Chaos Space Marines -80, World Devourer War Gang -80
- KMM-отношения: KMM_Behavior: Bloodraiders None->-18, White Eyebrow Clan None->-16, The Holy Nation None->-80, Oni None->-20 (+73)
- conductor: arch=robot, wealth=150, strength=29, ambition=survival, relic=None
- снаряжение: культура: Swordspear; носят: Flotsam Legplates 1, Combat Armor MkII - White 1, Combat Armor MkI - White 1, Combat Armor MkII - Black 1, Combat Armor MkI - Black 1
- Cleanup: лагеря ['Spider Workshop'], хост []
- слои KMM: KMM_Behavior 1, KMM_Cleanup 2, KMM_Economy 2, KMM_Elite 1, KMM_Glue 1

### Gutters  `51812-rebirth.mod`
- создатель: rebirth.mod; тип: NONE; скрыта в UI (реальна в мире); персонажей: 1, уников: 1
- уники: No-Face
- расы фракции: -; фактические: Greenlander 1
- города (9): Nest of Beak Things[0], Strange Camp[9], Nest of Iridescent Beak Things[0], Nest of Bush Things[0], Nest of Great Beak Things[0], Nest of Beak Things[0], Nest of Beak Things[0], Nest of Beak Things[0], Nest of Beak Things[0]
- союзники после: Gutters 100, Soulbodies 100, Crystal Enemys 100; враги после: Spiders -100, Blood Spiders -100
- слои KMM: KMM_Economy 1, KMM_Glue 1

### Lone Berserker  `5007308-Kit's Weapon Pack.mod`
- создатель: Kit's Weapon Pack.mod; тип: BANDIT; персонажей: 1, уников: 1
- уники: Foreign Swordsman
- лидеры: Foreign Swordsman
- расы фракции: -; фактические: Greenlander 1
- города (1): Swordsman's Hideout[holding]
- союзники после: Fogmen 25, Reavers 21, Berserkers 20, Blood Butcher Tribe 20, Charred Skull Tribe 20; враги после: Bloodraiders -100, Holy Nation Outlaws -100, Old Machines -100, Police -100, Slave Traders -100
- KMM-отношения: KMM_Behavior: White Eyebrow Clan None->-20, Reavers None->21, Lost Warrior None->-60, The Fallen Gang None->-26 (+128)
- conductor: arch=savage, wealth=150, strength=29, ambition=enrichment, relic=None
- снаряжение: культура: -; носят: Foreign Greatsword 1
- слои KMM: KMM_Behavior 1, KMM_Economy 1, KMM_Fix 1, KMM_Glue 2, KMM_Wardrobe 1

### Lost Oni  `5007931-Oni.mod`
- создатель: Oni.mod; тип: BANDIT; персонажей: 1, уников: 1
- уники: Long-Lost Oni
- лидеры: Long-Lost Oni
- расы фракции: Hazards Unit Oni(100); фактические: Hazards Unit Oni 1
- города (1): Ruined Tower of Trial[holding]
- союзники после: -; враги после: United Cities -100, Police -100, The Holy Nation -100, Oni -100, Cult of Fluorite -70
- KMM-отношения: KMM_Behavior: The Holy Nation None->-70, Dark Hive None->-20, Reavers None->-20, Band of Bones None->-21 (+97)
- conductor: arch=bandit, wealth=150, strength=29, ambition=enrichment, relic=None
- слои KMM: KMM_Behavior 1, KMM_Diplo 1, KMM_Economy 1, KMM_Glue 2

### Lost Warrior  `95-TEXT TEXTURE.mod`
- создатель: TEXT TEXTURE.mod; тип: MILITARY; персонажей: 1, уников: 0
- лидеры: Ultra Warrior 01
- расы фракции: -; фактические: Astartes (The Lost) 1
- союзники после: Astartes survivors 80, The Lost Black Sanctuary 80, Death Watch 80, Grey Knight 80; враги после: Daemons -100, Lost Chaos Space Marines -100, World Devourer War Gang -100, Midnight Lord -100, Hatred of intelligence -100
- KMM-отношения: KMM_Behavior: Bloodraiders None->-40, White Eyebrow Clan None->-39, Oni None->-39, Reavers None->-60 (+68)
- conductor: arch=imperium, wealth=60, strength=40, ambition=faith, relic=None
- снаряжение: культура: -; носят: Extreme Warrior - MKX Power Helmet 2, Ultramariner - MKX Power Armor 2, Extreme Warrior - MKX Power Combat Boots 2, Ultramariner - MKX Power Leg Armor 2, Extreme Warrior - Power Backpack 2
- слои KMM: KMM_Behavior 1, KMM_Economy 1, KMM_Glue 1, KMM_Wardrobe 1

### Nameless  `204-gamedata.base`
- создатель: gamedata.base; тип: ADVENTURER; персонажей: 1, уников: 0
- лидеры: Kumo
- расы фракции: -; фактические: Greenlander 1
- города (1): Your Outpost[1]
- союзники после: -; враги после: Daemons -80, Lost Chaos Space Marines -80, World Devourer War Gang -80, Midnight Lord -80, Hatred of intelligence -80
- KMM-отношения: KMM_Behavior: Bloodraiders None->-20, Black Dragon Ninjas None->-15, White Eyebrow Clan None->-15, Oni None->-13 (+54)
- conductor: arch=settler, wealth=50, strength=10, ambition=survival, relic=None
- слои KMM: KMM_Behavior 1

### Ohio  `60-Genzee.mod`
- создатель: Genzee.mod; тип: ADVENTURER; скрыта в UI (реальна в мире); персонажей: 1, уников: 1
- уники: Genzee
- лидеры: Genzee
- расы фракции: -; фактические: Screamer MkI 1
- союзники после: -; враги после: -
- слои KMM: KMM_Economy 1, KMM_Glue 1

### Outlaw  `1535100-CanyonKillerBounty.mod`
- создатель: CanyonKillerBounty.mod; тип: CIVILIAN; скрыта в UI (реальна в мире); персонажей: 1, уников: 1
- уники: Canyonlands Killer
- лидеры: Canyonlands Killer
- расы фракции: -; фактические: Scorchlander 1
- союзники после: -; враги после: -
- снаряжение: культура: Dead Sergeant`s pants, cast-off Razors, "Razor", Greatsword, Prisoner Shackles; носят: Prisoner Shackles 13, Hive Prisoner Shackles 2, Human Skin Suit 1, Human Skin 1, Ancient Samurai Boots 1

### Police  `2607-gamedata.base`
- создатель: gamedata.base; тип: LAW; персонажей: 1, уников: 0
- лидеры: Police Sergeant, Police Chief
- расы фракции: -; фактические: -
- союзники после: Slave Traders 100, United Cities 100, Traders Guild 100, Deadcat 100, Imperial Bank 100; враги после: Dust Bandits -100, Sand ninjas -100, Starving Bandits -100, Cannibals -100, Empire Criminals -100
- KMM-отношения: KMM_Behavior: Bloodraiders None->-60, White Eyebrow Clan None->-60, Oni None->-60, Reavers None->-70 (+57)
- conductor: arch=state, wealth=90, strength=36, ambition=survival, relic=None
- снаряжение: культура: -; носят: Heavy Jitte 6, Police Helmet 5, Empire Samurai Armour 4, Empire Heavy Samurai Armour 4, Empire Reinforced Samurai Armour 4
- гардероб: uniforms:samurai(char)
- слои KMM: KMM_Behavior 1, KMM_Wardrobe 1

### Researchers  `1996-TEXT TEXTURE.mod`
- создатель: TEXT TEXTURE.mod; тип: CIVILIAN; персонажей: 1, уников: 0
- лидеры: Backpack Scientist
- расы фракции: -; фактические: -
- союзники после: -; враги после: Daemons -80, Lost Chaos Space Marines -80, World Devourer War Gang -80, Midnight Lord -80, Hatred of intelligence -80
- KMM-отношения: KMM_Behavior: Bloodraiders None->-15, Black Dragon Ninjas None->-21, White Eyebrow Clan None->-15, Oni None->-21 (+54)
- conductor: arch=settler, wealth=150, strength=29, ambition=survival, relic=None
- снаряжение: культура: -; носят: Deathwatch - Damaged Power Backpack 1
- слои KMM: KMM_Behavior 1, KMM_Economy 1, KMM_Glue 1, KMM_Wardrobe 1

### Second Empire  `7993-Band of Exiles.mod`
- создатель: Band of Exiles.mod; тип: CIVILIAN; скрыта в UI (реальна в мире); персонажей: 1, уников: 1
- уники: Master Sarujan
- лидеры: Master Sarujan
- расы фракции: -; фактические: Skeleton Log-Head MKII 1
- союзники после: Drug Peddlers 27, Trade Ninjas 27, Sultans Wares 23, Traders Guild 20, Wandering Cloak Shop 20; враги после: Daemons -80, Lost Chaos Space Marines -80, World Devourer War Gang -80, Midnight Lord -80, Hatred of intelligence -80
- KMM-отношения: KMM_Behavior: Bloodraiders None->-60, White Eyebrow Clan None->-60, Oni None->-60, Reavers None->-70 (+65)
- снаряжение: культура: Industrial Blade, Norimitsu Odachi; носят: Ancient Samurai Legplates 3, Prisoner Shackles 1, Ancient Samurai Boots 1, Empire Samurai Armour 1, Ruined Samurai Armour 1
- слои KMM: KMM_Behavior 1

### Second Empire Exile  `1533874-rebirth.mod`
- создатель: rebirth.mod; тип: MILITARY; скрыта в UI (реальна в мире); персонажей: 1, уников: 0
- расы фракции: -; фактические: Skeleton No-Head MkII  1, Skeleton No-Head MkI 1
- города (1): Cat-Lon's Exile[2]
- союзники после: Old Machines 100, Skeleton Legion 100, Second Empire 100, Ancient Ruins 100, Soulbodies 100; враги после: Daemons -80, Lost Chaos Space Marines -80, World Devourer War Gang -80, Midnight Lord -80, Hatred of intelligence -80
- KMM-отношения: KMM_Behavior: Bloodraiders None->-60, White Eyebrow Clan None->-60, Oni None->-60, Reavers None->-70 (+65)
- conductor: arch=state, wealth=90, strength=36, ambition=survival, relic=None
- слои KMM: KMM_Behavior 1, KMM_Economy 1, KMM_Glue 1, KMM_Wardrobe 1

### Slave Hunters  `55101-rebirth.mod`
- создатель: rebirth.mod; тип: BANDIT; персонажей: 1, уников: 0
- расы фракции: Scorchlander(100), Shek(100), Greenlander(250), Hive Soldier Drone(75), Hive Worker Drone(20), Hive Prince(10); фактические: -
- союзники после: Shinobi Thieves 100, Slave Traders 75; враги после: Anti-Slavers -100, The Holy Nation -70, Cult of Fluorite -70, Missionaries -70, The Holy Nation -70
- KMM-отношения: KMM_Behavior: The Holy Nation None->-70, Dark Hive None->-21, Reavers None->-20, Lost Warrior None->-45 (+99)
- conductor: arch=bandit, wealth=40, strength=25, ambition=revenge, relic=None
- снаряжение: культура: -; носят: Police Helmet 2, Gi Pants 2, Chain Club 2
- слои KMM: KMM_Behavior 1, KMM_Economy 1, KMM_Glue 2, KMM_Wardrobe 1

### Slaves' Martyrs  `1535498-Bounties Galore.mod`
- создатель: Bounties Galore.mod; тип: ADVENTURER; персонажей: 1, уников: 1
- уники: Smokes -unfinished
- расы фракции: Greenlander(100), Hive Prince(100), Hive Worker Drone(100), Hive Soldier Drone(100), Scorchlander(100), Shek(100); фактические: Scorchlander 1
- союзники после: Rebirth Slaves 100, Slaves 100, Empire Peasants 70, Flotsam Ninjas 70, Tech Hunters 70; враги после: Cannibals -100, Dust Bandits -100, Manhunters -100, United Heroes League -100, United Cities -100
- KMM-отношения: KMM_Behavior: Swampers 20->14
- слои KMM: KMM_Behavior 1, KMM_Economy 1, KMM_Glue 1

### The Wolven Order  `2757843-GreatDirewolf.mod`
- создатель: GreatDirewolf.mod; тип: CIVILIAN; персонажей: 1, уников: 1
- уники: Zenith
- лидеры: Zenith
- расы фракции: -; фактические: Greenlander 1
- города (1): Drakken[holding]
- союзники после: -; враги после: Daemons -80, Lost Chaos Space Marines -80, World Devourer War Gang -80, Midnight Lord -80, Hatred of intelligence -80
- KMM-отношения: KMM_Behavior: Bloodraiders None->-11, Black Dragon Ninjas None->-15, White Eyebrow Clan None->-15, Oni None->-20 (+54)
- conductor: arch=settler, wealth=150, strength=29, ambition=survival, relic=None
- снаряжение: культура: Ronin Talons; носят: Ronin Talons 1
- слои KMM: KMM_Behavior 1, KMM_Diplo 1, KMM_Economy 1, KMM_Glue 1, KMM_Wardrobe 1

### Traitors  `5132544-Dark Hive.mod`
- создатель: Dark Hive.mod; тип: MILITARY; скрыта в UI (реальна в мире); персонажей: 1, уников: 1
- уники: Frauder
- лидеры: Frauder
- расы фракции: -; фактические: Dark Hive Worker Drone 1
- города (1): Dangerous Trap[4]
- союзники после: Dark Reavers 50; враги после: -
- снаряжение: культура: Dark Samurai Helmet; носят: Dark Samurai Helmet 1, Dark Samurai Legplates 1, Fragment Cleaver 1

### Wandering Cloak Shop  `122-HTT_Cloaks.mod`
- создатель: HTT_Cloaks.mod; тип: TRADER; персонажей: 1, уников: 0
- лидеры: Cloak Trader
- расы фракции: -; фактические: -
- союзники после: Gutters 50, Catun 17, Deadcat 17, Holy Nation Outlaws 16, Researchers 14; враги после: Daemons -80, Lost Chaos Space Marines -80, World Devourer War Gang -80, Midnight Lord -80, Hatred of intelligence -80
- KMM-отношения: KMM_Behavior: Bloodraiders None->-60, White Eyebrow Clan None->-60, The Holy Nation None->12, Dark Hive None->10 (+96)
- conductor: arch=trader, wealth=120, strength=20, ambition=enrichment, relic=None
- снаряжение: культура: Quality Fabric Cloak (colored); носят: Karuta Zukin 3, Large Backpack 3, Unholy Chest Plate 3, Quality Fabric Cloak (colored) 3
- слои KMM: KMM_Behavior 1, KMM_Economy 1, KMM_Glue 1, KMM_Wardrobe 1

### White Wolves  `2757668-GreatDirewolf.mod`
- создатель: GreatDirewolf.mod; тип: ADVENTURER; персонажей: 1, уников: 1
- уники: Seth
- расы фракции: -; фактические: -
- города (1): The White Wolf's Respite[9]
- союзники после: -; враги после: Dust Bandits -100, Daemons -80, Lost Chaos Space Marines -80, World Devourer War Gang -80, Midnight Lord -80
- KMM-отношения: KMM_Behavior: Bloodraiders None->-15, Black Dragon Ninjas None->-7, White Eyebrow Clan None->-9, Oni None->-15 (+53)
- conductor: arch=settler, wealth=150, strength=27, ambition=survival, relic=None
- Cleanup: лагеря ["The White Wolf's Respite"], хост []
- слои KMM: KMM_Behavior 1, KMM_Cleanup 1, KMM_Economy 1, KMM_Glue 1

### Wolves  `56128-rebirth.mod`
- создатель: rebirth.mod; тип: NONE; скрыта в UI (реальна в мире); персонажей: 1, уников: 0
- лидеры: Mad Cat-Lon
- расы фракции: -; фактические: Hive Worker Drone 1
- города (3): Wolf Den[0], Bloodhound Den[0], The Black Hound's Den[4]
- союзники после: Gorillos 100, Black Gorillos 100, Mountain Dogs 100; враги после: Blood Spiders -100, Goats -50
- снаряжение: культура: -; носят: Ancient Samurai Boots 1, Iron Fortress Chestguard 1, Iron Fortress Waistguard 1, Ruined Samurai Armour 1, Ruined Samurai Legplates 1
- слои KMM: KMM_Wardrobe 1

### cloak shop(test)  `69-HTT_Cloaks.mod`
- создатель: HTT_Cloaks.mod; тип: TRADER; персонажей: 1, уников: 0
- лидеры: *Test Shop
- расы фракции: -; фактические: -
- союзники после: Traders Guild 31, Imperial Bank 29, Red Hive 28, Trade Ninjas 28, Guild of Surgeons 27; враги после: Daemons -80, Lost Chaos Space Marines -80, World Devourer War Gang -80, Midnight Lord -80, Hatred of intelligence -80
- KMM-отношения: KMM_Behavior: Bloodraiders None->-60, White Eyebrow Clan None->-60, Oni None->-60, Reavers None->-60 (+84)
- снаряжение: культура: Cloak (Nameless); носят: Cloak (Nameless) 1
- слои KMM: KMM_Behavior 1, KMM_Wardrobe 1

### hermit  `1862-TEXT TEXTURE.mod`
- создатель: TEXT TEXTURE.mod; тип: MILITARY; скрыта в UI (реальна в мире); персонажей: 1, уников: 0
- лидеры: Imperial Guard - Lukes
- расы фракции: -; фактические: Astartes (Elite) 1
- города (1): Imperial Guard's Hidden Residence[4]
- союзники после: -; враги после: -
- снаряжение: культура: -; носят: Imperial Guard - Alarus Terminator Helmet (Gold) 1, Imperial Guard - Alarus Terminator Armor (Gold) 1, Imperial Guard - Alarus Terminator Leg Armor (Gold) 1, Imperial Guard - Alarus Terminator Power Boots (Gold) 1, Imperial Guards - Powered Axe and Halberd 1
- слои KMM: KMM_Economy 1, KMM_Glue 1, KMM_Wardrobe 1

### 失控  `225-KillerRobot.mod`
- создатель: KillerRobot.mod; тип: CIVILIAN; персонажей: 1, уников: 0
- лидеры: 终端机械师守卫
- расы фракции: -; фактические: Screamer MkI 1
- города (1): 实验体工厂遗迹[holding]
- союзники после: Free Traders 17, Gunsmiths 16, Trade Ninjas 13, Traders Guild 10, Wandering Cloak Shop 10; враги после: United Cities -200, Daemons -80, Lost Chaos Space Marines -80, World Devourer War Gang -80, Midnight Lord -80
- KMM-отношения: KMM_Behavior: Bloodraiders None->-15, White Eyebrow Clan None->-13, Oni None->-20, Reavers None->-47 (+71)
- conductor: arch=settler, wealth=150, strength=41, ambition=survival, relic=None
- снаряжение: культура: -; носят: Ancient Samurai Legplates 5, Ancient Samurai Armour 4, Exile Plank 4, Falling Sun 4
- слои KMM: KMM_Behavior 1, KMM_Economy 1, KMM_Wardrobe 1

### Abandoned Buildings  `5004374-Bandit Variety.mod`
- создатель: Bandit Variety.mod; тип: ADVENTURER; скрыта в UI (реальна в мире); персонажей: 0, уников: 0
- расы фракции: -; фактические: -
- города (14): Okran's Shield (override) destroyed[1], Burn's Tower (override)[1], Smugglers Bar (override) destroyed[1], Swamp Ninja Base (override) destroyed[1], Black Dog HQ (override) trashed[1], The Old Prison (override) abandoned[1], Tower Of Goats (override) abandoned[1], Adidan's Tower (Override) Ruined[9], Berserker Outpost (Override) Ruined[9], Crab Sanctum (Override) Ruined[9], Shaman's Hideout (Override) Ruined[3], Spider Den (Override) Ruined[9], Wendigo's Hut (Override) Ruined[9], Zander's Hideou
- союзники после: Nameless 100; враги после: -
- слои KMM: KMM_Cleanup 5

### Black Gorillos  `43-Symbiosis.mod`
- создатель: Symbiosis.mod; тип: NONE; скрыта в UI (реальна в мире); персонажей: 0, уников: 0
- расы фракции: -; фактические: -
- города (1): Gorillo Nest[0]
- союзники после: Wolves 100, Bone Wolves 100, Bone Jackals 100; враги после: Spiders -100, Gutters -100, Grievewraiths -100

### Bog Dogs  `5007934-Edit Dogs.mod`
- создатель: Edit Dogs.mod; тип: NONE; скрыта в UI (реальна в мире); персонажей: 0, уников: 0
- расы фракции: -; фактические: -
- города (1): Bog Dog Den[0]
- союзники после: Gorillos 100; враги после: Blood Spiders -100

### Bone Jackals  `5007935-Edit Dogs.mod`
- создатель: Edit Dogs.mod; тип: NONE; скрыта в UI (реальна в мире); персонажей: 0, уников: 0
- расы фракции: -; фактические: -
- города (1): Bone Jackal Den[0]
- союзники после: Black Gorillos 100, Gorillos 100; враги после: Goats -50

### Bone Wolves  `50-Symbiosis.mod`
- создатель: Symbiosis.mod; тип: NONE; скрыта в UI (реальна в мире); персонажей: 0, уников: 0
- расы фракции: -; фактические: -
- города (1): Boneyard Wolf Den[0]
- союзники после: Gorillos 100, Black Gorillos 100, Mountain Dogs 100; враги после: Blood Spiders -100, Spiders -100, Dire Hyaenidae -100, Fell Hyaenidae -100, Slough Hyaenidae -100

### Carrion Crawlers  `1535123-TIHYD_Carrion Crawlers.mod`
- создатель: TIHYD_Carrion Crawlers.mod; тип: NONE; скрыта в UI (реальна в мире); персонажей: 0, уников: 0
- расы фракции: -; фактические: -
- города (1): Carrion Crawler Nest[0]
- союзники после: -; враги после: Wolves -100

### Chimpanzees  `1535106-TIHYD_Zoo.mod`
- создатель: TIHYD_Zoo.mod; тип: NONE; скрыта в UI (реальна в мире); персонажей: 0, уников: 0
- расы фракции: -; фактические: -
- города (1): Chimpanzee Nest[0]
- союзники после: -; враги после: Raptors -100, Wildlife -100

### Crabs  `56108-rebirth.mod`
- создатель: rebirth.mod; тип: NONE; скрыта в UI (реальна в мире); персонажей: 0, уников: 0
- расы фракции: -; фактические: -
- города (6): Lost Town[4], Crab Nest[0], Seaweed Crab Nest[0], Spider Crab Nest[0], Dwarf Crab nest[0], Crab Nest pit[0]
- союзники после: Crab Raiders 100; враги после: -
- слои KMM: KMM_Economy 1

### Crop Lice  `1535116-TIHYD_Zoo.mod`
- создатель: TIHYD_Zoo.mod; тип: NONE; скрыта в UI (реальна в мире); персонажей: 0, уников: 0
- расы фракции: -; фактические: -
- города (1): Crop Lice Nest[0]
- союзники после: -; враги после: -

### Cyborgs  `5007351-The Eternal Laboratory.mod`
- создатель: The Eternal Laboratory.mod; тип: ADVENTURER; персонажей: 0, уников: 0
- расы фракции: Cyborg - Deadhive Prince(100), Cyborg - Deadhive Soldier(100), Cyborg - Deadhive Worker(100); фактические: -
- города (1): The Eternal Laboratory[city]
- союзники после: Tech Hunters 100, Skeletons 100, Nomadic Skeletons 60, Floodlands Skeletons 60, Old Machines 60; враги после: The Holy Nation -100, Daemons -80, Cult of Fluorite -80, Lost Chaos Space Marines -80, World Devourer War Gang -80
- KMM-отношения: KMM_Behavior: Bloodraiders None->-21, White Eyebrow Clan None->-14, The Holy Nation None->-80, Oni None->-20 (+71)
- conductor: arch=robot, wealth=150, strength=27, ambition=survival, relic=None
- слои KMM: KMM_Behavior 1, KMM_Fix 1

### Dire Hyaenidae  `5007273-Subspecies.mod`
- создатель: Subspecies.mod; тип: NONE; скрыта в UI (реальна в мире); персонажей: 0, уников: 0
- расы фракции: -; фактические: -
- города (1): Dire Hyena Den[0]
- союзники после: -; враги после: Wolves -100, Bone Wolves -100, Silver Wolves -100, Savannah Hounds -100

### Dune Dogs  `5007936-Edit Dogs.mod`
- создатель: Edit Dogs.mod; тип: NONE; скрыта в UI (реальна в мире); персонажей: 0, уников: 0
- расы фракции: -; фактические: -
- города (1): Dune Dog Den[0]
- союзники после: -; враги после: Goats -50

### Dust Hounds  `5007932-Edit Dogs.mod`
- создатель: Edit Dogs.mod; тип: NONE; скрыта в UI (реальна в мире); персонажей: 0, уников: 0
- расы фракции: -; фактические: -
- города (1): Dust Hound Den[0]
- союзники после: -; враги после: Goats -50

### Fell Hyaenidae  `29-Symbiosis - Hyaenidae.mod`
- создатель: Symbiosis - Hyaenidae.mod; тип: NONE; скрыта в UI (реальна в мире); персонажей: 0, уников: 0
- расы фракции: -; фактические: -
- города (1): Fell Hyena Den[0]
- союзники после: -; враги после: Wolves -100, Bone Wolves -100, Striped Hounds -100

### Fiddler Crabs  `1535113-TIHYD_Zoo.mod`
- создатель: TIHYD_Zoo.mod; тип: NONE; скрыта в UI (реальна в мире); персонажей: 0, уников: 0
- расы фракции: -; фактические: -
- города (1): Fiddler Crab Nest[0]
- союзники после: -; враги после: Gutters -100, Fogmen -50

### Floodland Ruins  `48708-rebirth.mod`
- создатель: rebirth.mod; тип: BANDIT; скрыта в UI (реальна в мире); персонажей: 0, уников: 0
- расы фракции: -; фактические: -
- города (3): Ruined Tower[4], Empty Ruins[4], Leaning Tower[4]
- союзники после: -; враги после: -

### Fog Fiends  `10-Symbiosis - Waste Fiends.mod`
- создатель: Symbiosis - Waste Fiends.mod; тип: NONE; скрыта в UI (реальна в мире); персонажей: 0, уников: 0
- расы фракции: -; фактические: -
- города (2): Fog Fiend Hollow[0], Fog Fiend Migratory Hollow[0]
- союзники после: -; враги после: Fogmen -100
- гардероб: pagan, savage

### Golden Wolves  `5007937-Edit Dogs.mod`
- создатель: Edit Dogs.mod; тип: NONE; скрыта в UI (реальна в мире); персонажей: 0, уников: 0
- расы фракции: -; фактические: -
- города (1): Golden Wolf Den[0]
- союзники после: -; враги после: Grievous Hyaenidae -100

### Great Maned Wolves  `5007938-Edit Dogs.mod`
- создатель: Edit Dogs.mod; тип: NONE; скрыта в UI (реальна в мире); персонажей: 0, уников: 0
- расы фракции: -; фактические: -
- города (1): Great Maned Wolf Den[0]
- союзники после: Gorillos 100; враги после: Fogmen -100, Grievous Hyaenidae -100

### Grievewraiths  `11-Symbiosis - Grievewraiths.mod`
- создатель: Symbiosis - Grievewraiths.mod; тип: BANDIT; скрыта в UI (реальна в мире); персонажей: 0, уников: 0
- расы фракции: -; фактические: -
- города (2): Grievewraith nest[0], Infested Ruin[4]
- союзники после: Blood Spiders 100, Spiders 100; враги после: -

### Grievous Hyaenidae  `28-Symbiosis - Hyaenidae.mod`
- создатель: Symbiosis - Hyaenidae.mod; тип: NONE; скрыта в UI (реальна в мире); персонажей: 0, уников: 0
- расы фракции: -; фактические: -
- города (1): Grievous Hyena Den[0]
- союзники после: -; враги после: Wolves -100, Bone Wolves -100, Skimmers -100, Golden Wolves -100, White Wolves -100

### Gutters  `5007474-Lovely Gutter.mod`
- создатель: Lovely Gutter.mod; тип: BANDIT; персонажей: 0, уников: 0
- расы фракции: -; фактические: -
- города (1): Nest of Beak Things[4]
- союзники после: Gutters 100; враги после: Spiders -100, The Holy Nation -70, Cult of Fluorite -70, Missionaries -70, The Holy Nation -70
- KMM-отношения: KMM_Behavior: The Holy Nation None->-70, Dark Hive None->-20, Reavers None->-20, Lost Warrior None->-40 (+100)
- conductor: arch=bandit, wealth=60, strength=34, ambition=enrichment, relic=None
- слои KMM: KMM_Behavior 1, KMM_Glue 1

### Herbivore  `40544-rebirth.mod`
- создатель: rebirth.mod; тип: CIVILIAN; скрыта в UI (реальна в мире); персонажей: 0, уников: 0
- расы фракции: -; фактические: -
- города (1): Cage Beast[0]
- союзники после: Goats 100, Wildlife 25, Wild Bulls 25; враги после: -

### Land Bat  `97574-Newwworld.mod`
- создатель: Newwworld.mod; тип: NONE; скрыта в UI (реальна в мире); персонажей: 0, уников: 0
- расы фракции: -; фактические: -
- города (1): Land Bat Nest[0]
- союзники после: -; враги после: Striped Hounds -100

### Moss Crabs  `10-Symbiosis - Moss Crabs.mod`
- создатель: Symbiosis - Moss Crabs.mod; тип: NONE; скрыта в UI (реальна в мире); персонажей: 0, уников: 0
- расы фракции: -; фактические: -
- города (1): Moss Crab Nest[0]
- союзники после: -; враги после: -

### Mountain Dogs  `346-Symbiosis.mod`
- создатель: Symbiosis.mod; тип: NONE; скрыта в UI (реальна в мире); персонажей: 0, уников: 0
- расы фракции: -; фактические: -
- города (1): Mountain Wolf Den[0]
- союзники после: Gorillos 100, Black Gorillos 100, Bone Wolves 100, Wolves 100, Golden Wolves 100; враги после: Blood Spiders -100, Goats -50

### Orion Crocuta  `5007286-Subspecies.mod`
- создатель: Subspecies.mod; тип: NONE; скрыта в UI (реальна в мире); персонажей: 0, уников: 0
- расы фракции: -; фактические: -
- города (1): Orion Crocuta Den[0]
- союзники после: Verglas Crocuta 100; враги после: Wolves -100, Herbivore -100, Bone Wolves -100, Dust Hounds -100, Striped Hounds -100

### Raptors  `58701-rebirth.mod`
- создатель: rebirth.mod; тип: NONE; скрыта в UI (реальна в мире); персонажей: 0, уников: 0
- расы фракции: -; фактические: -
- города (1): River Raptor Nest[0]
- союзники после: Crystal Enemys 100, Wildlife 25; враги после: -

### Robotic Wildlife  `1535131-TIHYD_Zoo.mod`
- создатель: TIHYD_Zoo.mod; тип: NONE; скрыта в UI (реальна в мире); персонажей: 0, уников: 0
- расы фракции: -; фактические: -
- города (1): Skel-Ape Nest[0]
- союзники после: Southern Hive 100; враги после: -

### Savannah Hounds  `5007939-Edit Dogs.mod`
- создатель: Edit Dogs.mod; тип: NONE; скрыта в UI (реальна в мире); персонажей: 0, уников: 0
- расы фракции: -; фактические: -
- города (1): Savannah Hound Den[0]
- союзники после: Dust Hounds 100, Wolves 100, Gorillos 100; враги после: Spiders -100, Blood Spiders -100, Dire Hyaenidae -100

### Silver Wolves  `5007940-Edit Dogs.mod`
- создатель: Edit Dogs.mod; тип: NONE; скрыта в UI (реальна в мире); персонажей: 0, уников: 0
- расы фракции: -; фактические: -
- города (1): Silver Wolf Den[0]
- союзники после: Gorillos 100; враги после: Dire Hyaenidae -100

### Skimmers  `56098-rebirth.mod`
- создатель: rebirth.mod; тип: NONE; скрыта в UI (реальна в мире); персонажей: 0, уников: 0
- расы фракции: -; фактические: -
- города (6): Skimmer Nest[0], Small Skimmer Nest[0], Verdant Skimmer Nest Small[0], Verdant Skimmer Nursery[0], Skimmer Nursery[0], Skimmer Brood Nursery[0]
- союзники после: -; враги после: -

### Slough Hyaenidae  `30-Symbiosis - Hyaenidae.mod`
- создатель: Symbiosis - Hyaenidae.mod; тип: NONE; скрыта в UI (реальна в мире); персонажей: 0, уников: 0
- расы фракции: -; фактические: -
- города (1): Slough Hyena Den[0]
- союзники после: -; враги после: Wolves -100, Bone Wolves -100, Blood Spiders -100

### South Exiles  `73-AnnexFishmanIsland.mod`
- создатель: AnnexFishmanIsland.mod; тип: NONE; скрыта в UI (реальна в мире); персонажей: 0, уников: 0
- расы фракции: Hive Worker Drone South Hive(100); фактические: -
- города (1): Island Lab (South Exiles)[1]
- союзники после: Fish Isle 100, Nameless 15; враги после: Fishmen -100, Crabs -100
- слои KMM: KMM_Fix 1

### Swamp Creatures  `51811-rebirth.mod`
- создатель: rebirth.mod; тип: NONE; скрыта в UI (реальна в мире); персонажей: 0, уников: 0
- расы фракции: -; фактические: -
- города (4): Raptor Island[9], Swamp Raptor Nest[0], nest- megaraptor[0], Red Nest[0]
- союзники после: -; враги после: -

### Swamp Things  `14-Symbiosis - Beak Turtles.mod`
- создатель: Symbiosis - Beak Turtles.mod; тип: NONE; скрыта в UI (реальна в мире); персонажей: 0, уников: 0
- расы фракции: -; фактические: -
- города (1): Nest of Beak Turtles[0]
- союзники после: -; враги после: Spiders -100, Blood Spiders -100

### Tyrants  `5007305-Waste Fiends - Creature mod.mod`
- создатель: Waste Fiends - Creature mod.mod; тип: NONE; скрыта в UI (реальна в мире); персонажей: 0, уников: 0
- расы фракции: -; фактические: -
- города (4): Bone Fiend Small nest[0], Bone Fiend Large[0], Bone Fiend Hollow[0], Large Bone Fiend Hollow[0]
- союзники после: Fogmen 100, Mist Creatures 100; враги после: -

### Verglas Crocuta  `13-Symbiosis - Hyaenidae.mod`
- создатель: Symbiosis - Hyaenidae.mod; тип: NONE; скрыта в UI (реальна в мире); персонажей: 0, уников: 0
- расы фракции: -; фактические: -
- города (1): Verglas Crocuta Den[0]
- союзники после: Orion Crocuta 100; враги после: Wolves -100, Herbivore -100, Bone Wolves -100, Striped Hounds -100

### Wasps  `1535102-TIHYD_Acid Wasp.mod`
- создатель: TIHYD_Acid Wasp.mod; тип: NONE; скрыта в UI (реальна в мире); персонажей: 0, уников: 0
- расы фракции: -; фактические: -
- города (1): Acid Wasp Nest[0]
- союзники после: -; враги после: Herbivore -100, Wildlife -100

### Waste Fiends  `73-Symbiosis - Waste Fiends.mod`
- создатель: Symbiosis - Waste Fiends.mod; тип: NONE; скрыта в UI (реальна в мире); персонажей: 0, уников: 0
- расы фракции: -; фактические: -
- города (1): Waste Fiend Hollow[0]
- союзники после: -; враги после: -

### White Wolves  `5007941-Edit Dogs.mod`
- создатель: Edit Dogs.mod; тип: NONE; скрыта в UI (реальна в мире); персонажей: 0, уников: 0
- расы фракции: -; фактические: -
- города (1): White Wolf Den[0]
- союзники после: -; враги после: Grievous Hyaenidae -100

