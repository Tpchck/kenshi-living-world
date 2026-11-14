# CLEANUP_PLAN — чистка карты (мод KMM_Cleanup, только для новой игры)

Генерируется tools\cleanup\build_cleanup.py из rules\cleanup.json (одобрено: удалять локацию вместе с постройками; хост выбирается по лору).
Что делает: отряды лагеря (уник, питомцы внутри отряда) переезжают в хост-город (bar squads v0=1, v1=100; если у хоста нет баров — residents (1, 2, 0) как у жителей лагерей); TOWN лагеря и его override-варианты получают REMOVED=true; здания лагеря удаляются из zone-файлов. Если фракция переезжающего отряда отличается от фракции хоста, она заменяется на фракцию хоста (иначе отряд воюет с жителями).

## MERGE: лагерь -> хост

| Лагерь (позиция; мод) | Хост (фракция) | Кто переезжает | Почему по лору | Как | Построек удаляется | Ближайшее чужое здание |
|---|---|---|---|---|---|---|
| Adidan's Tower (-16235, -24448; Bounties Galore.mod) | Smugglers Bar (Grayflayers) | Adidan (каннибал-отшельник) | Smugglers Bar (Grayflayers, публичный бар на краю закона): единственное нейтральное место, где изгой-каннибал не вызывает войны; рекрутируется в баре. | bar squads; фракция заменена на хостовую | 19 (до 1112 ед.) | 3005 ед. |
| Branding Camp (-103571, 35861; TEXT TEXTURE.mod) | Astartes outpost (Astartes survivors) | Black Shield - Brand Warrior | Astartes outpost (Astartes survivors, отношение к игроку +20): Black Shield — космодесант-отступник того же мира, убежище для своих. | bar squads | 4 (до 103 ед.) | 7941 ед. |
| Crab Sanctum (146607, 29378; Bounties Galore.mod) | Flats Lagoon (Tech Hunters) | Snip-Snap + краб | Flats Lagoon (Tech Hunters, публичный город): лагуна у воды — естественное место для крабовода; Crab Raiders враждебны игроку, поэтому не их города. | bar squads; фракция заменена на хостовую | 1 (до 452 ед.) | нет в 12000 ед. |
| Houndmaster's Den (-8860, -104001; Bounties Galore.mod) | кочует: Northern Coast (Holy Nation Outlaws) | Houndmaster + Bonedog + гончие | Разыскиваемый (награда Bounties Galore/мода): не сидит в логове и не в баре хоста, а родным кочевником ходит по своему региону от города к городу и бывает в барах (BIOME_GROUP.homeless spawns + AI «Wandering from town to town»/«hang out in a bar», как Poacher Kingpin в Heng). Убит — исчезает навсегда (уник); замену даёт KMM_Outlaws. Хост в записи — запасной. (решение 2026-11-14 по идее владельца о живых разыскиваемых) | в отряд Houndmaster, кочует: Northern Coast (баров нет) | 5 (до 299 ед.) | 11232 ед. |
| Silent Camp (28152, -143882; TEXT TEXTURE.mod) | Astartes outpost (Astartes survivors) | Grey Knight - Shield Terminator | Astartes outpost: Серый Рыцарь — охотник на хаос, как и Astartes survivors (ambition hunt_chaos). | bar squads; фракция заменена на хостовую | 5 (до 134 ед.) | 4615 ед. |
| Silent Camp (109608, 84210; TEXT TEXTURE.mod) | The Hub (Holy Nation Outlaws) | Midnight Lord - Karl | Разыскиваемый (награда Bounties Galore/мода): не сидит в логове и не в баре хоста, а родным кочевником ходит по своему региону от города к городу и бывает в барах (BIOME_GROUP.homeless spawns + AI «Wandering from town to town»/«hang out in a bar», как Poacher Kingpin в Heng). Убит — исчезает навсегда (уник); замену даёт KMM_Outlaws. Хост в записи — запасной. (решение 2026-11-14 по идее владельца о живых разыскиваемых) | bar squads | 2 (до 91 ед.) | 4007 ед. |
| Spider Den (-10096, 59520; Bounties Galore.mod) | Mud Town (Swampers) | Blaze + Blood Spider | Mud Town (Swampers, публичная деревня): болотные жители живут рядом с пауками и жуками, укротитель уместен. | bar squads | 9 (до 584 ед.) | 6995 ед. |
| Spider Workshop (-66476, -81321; Bounties Galore.mod) | World's End (Tech Hunters) | Sarin + Captcha + торговый отряд (3) | World's End (Tech Hunters, бар, машинисты уже живут): Spider Workshop — лавка Sarin (протезы); Errol's Workshop сам одинокая лавка и тоже переезжает сюда. Режим shop: уличный торговец в баре (образец Live Street). | bar squads; фракция заменена на хостовую | 6 (до 357 ед.) | 4811 ед. |
| Watcher's Camp (-105332, 55143; Bounties Galore.mod) | кочует: Watcher's Rim (Holy Nation Outlaws) | Watcher + Apprentice + собаки | Разыскиваемый (награда Bounties Galore/мода): не сидит в логове и не в баре хоста, а родным кочевником ходит по своему региону от города к городу и бывает в барах (BIOME_GROUP.homeless spawns + AI «Wandering from town to town»/«hang out in a bar», как Poacher Kingpin в Heng). Убит — исчезает навсегда (уник); замену даёт KMM_Outlaws. Хост в записи — запасной. (решение 2026-11-14 по идее владельца о живых разыскиваемых) | кочует: Watcher's Rim | 3 (до 183 ед.) | 5516 ед. |
| Wendigo's Hut (-19495, 101170; Bounties Galore.mod) | Rot (Hounds) | Wendigo (каннибал-вождь) | Rot (Hounds, публичная деревня дикарей, лидер Big Grim): дикая банда терпит каннибала; Adidan и Wendigo разведены по разным хостам. | bar squads; фракция заменена на хостовую | 19 (до 431 ед.) | нет в 12000 ед. |
| Witches' Huts (85330, 71767; Bounties Galore.mod) | Cult Village (Preacher Cult) | The Crone + 2 дочери (3 отряда) | Cult Village (Preacher Cult, публичная деревня): ведьмы среди сектантов — культ принимает ковен. | bar squads; фракция заменена на хостовую | 25 (до 405 ед.) | 5483 ед. |
| Taunt's Hideout (-53847, -24782; Bounties Galore.mod) | кочует: Okran's Gulf (The Holy Nation) | Taunt (гринлендер, Drifters) | Разыскиваемый (награда Bounties Galore/мода): не сидит в логове и не в баре хоста, а родным кочевником ходит по своему региону от города к городу и бывает в барах (BIOME_GROUP.homeless spawns + AI «Wandering from town to town»/«hang out in a bar», как Poacher Kingpin в Heng). Убит — исчезает навсегда (уник); замену даёт KMM_Outlaws. Хост в записи — запасной. (решение 2026-11-14 по идее владельца о живых разыскиваемых) | кочует: Okran's Gulf | 14 (до 366 ед.) | 5909 ед. |
| The White Wolf's Respite (-23367, -26948; GreatDirewolf.mod) | Busted Wall (The Holy Nation) | Seth + волчица Brooke | Busted Wall (Holy Nation, бар, 7.3 тыс.): ближайший публичный город людей; отряд без фракции — рекрут в баре вместе с волком. | residents (баров нет) | 5 (до 139 ед.) | 2945 ед. |
| Zander's Hideout (-1802, 26931; Bounties Galore.mod) | кочует: Shem (Shem Residents) | Zander + Band of Bones (4, шек) | Разыскиваемый (награда Bounties Galore/мода): не сидит в логове и не в баре хоста, а родным кочевником ходит по своему региону от города к городу и бывает в барах (BIOME_GROUP.homeless spawns + AI «Wandering from town to town»/«hang out in a bar», как Poacher Kingpin в Heng). Убит — исчезает навсегда (уник); замену даёт KMM_Outlaws. Хост в записи — запасной. (решение 2026-11-14 по идее владельца о живых разыскиваемых) | кочует: Shem | 3 (до 220 ед.) | 3386 ед. |
| Roadside Bakery (-43568, -37475; cook_set.mod) | Blister Hill (The Holy Nation) | Romi, Alan, Jakes — пекарня «Mostly Harmony» | Blister Hill (Holy Nation, 8.7 тыс.): одинокая пекарня той же фракции у дороги -> уличные пекари в городе; охрана не переезжает. | bar squads, не переезжает (охрана/прочее); фракция заменена на хостовую | 3 (до 266 ед.) | 7437 ед. |
| Dreg Gunworks (-97632, -38304; BlackPowder.mod) | Mongrel (Mongrel) | Dreg Gunsmith — оружейная Dreg Gunworks | Mongrel (15 тыс., осаждён туманниками): оружейнику место в городе, которому нужны стволы; охрана не переезжает. | bar squads; фракция заменена на хостовую | 5 (до 168 ед.) | 6794 ед. |
| Errol's Workshop (-51702, -86231; HeatCoilCleaver.mod) | World's End (Tech Hunters) | Errol — мастерская Errol's Workshop | World's End (Tech Hunters, 27 тыс.): технический город, машинисты уже живут; Errol торгует экспериментальным оружием из бара. | bar squads | 6 (до 290 ед.) | 5907 ед. |

Итого: 17 лагерей, 134 построек в 18 зонах. Выбор построек: instance'ы зон, впервые введённые модом-источником лагеря, в радиусе 2000 ед. от позиции лагеря; чужих зданий в этом радиусе нет (проверяется сборкой).

## REVIEW: рекомендации (в сборку НЕ входят)

| Локация | Рекомендация | Причина |
|---|---|---|
| Ark | оставить | база Reavers (15 жителей, Valamon — лидер из world states), на неё ссылается NEW_GAME_STARTOFF и карта. |
| Black Sanctuary Camp | оставить | база фракции The Lost Black Sanctuary: 35 зданий, гарнизон 8, закрытая; не лагерь-одиночка. |
| Death Watch landing point | оставить | 26 зданий, три рекрута и отряд из 3 — место крушения, а не лагерь; слияние оставит руины без смысла. Можно позже перенести рекрутов в Astartes outpost. |
| Gnawed Bone Camp | оставить | нет позиции в leveldata, появляется только как гнездо (SQUAD_TEMPLATE.nest) — на карте не мусорит. |
| Human Research Institute | оставить | штаб Midnight Lord: 56 жителей + 23 в баре при 1 здании; без него фракция теряет базу. |
| Man-eating Shark Outpost | оставить | 74 здания, форпост фракции Man-eating shark, закрытый; слияние снесло бы крупную постройку. |
| Old Wreckage | оставить | 45 зданий, сюжетная база The Hollow Feast с работорговым караваном. |
| Reapers Due | оставить | 61 член Old Machines в 3 зданиях — босс-локация охоты за головой; Grim не рекрутируется. |
| Roadside Bakery | слито (2026-11-14, режим shop -> Blister Hill) | 3 здания, рядом (8781 ед.) Blister Hill той же фракции Holy Nation; хост — Blister Hill. Романи (Romi) — слабый рекрут. |
| Ruined Tower of Trial | убрать | 1 здание, без уников; в 9155 ед. стоит основной Tower of Trial (Oni); отряд из трёх «imprisoned oni» можно не переносить. |
| Seaside Restaurant | оставить | 23 здания, торговый город United Cities (45 человек), функциональный. |
| Sultan Outpost | оставить | на него ссылается NEW_GAME_STARTOFF (старт новой игры), торговец-рекрут. |
| The Apothecary | оставить | 78 зданий, торговые отряды гильдии хирургов. |
| The Collector's Nest | оставить | 64 здания, закрытая база Lost Chaos Space Marines; рекрут есть, но место крупное. |
| World's Ruin | оставить | 464 здания, 14 отрядов — это город, не лагерь. |

## Как включить

1. rules\load_order.json: добавить "KMM_Cleanup" в список kmm после "KMM_Fix" (последним). Генератор mods_cfg берёт мод из build\KMM_Cleanup\KMM_Cleanup.mod.
2. Установка: kmm_build копирует только моды потоков из своего summary; папку build\KMM_Cleanup (с leveldata) нужно скопировать в Kenshi\mods\KMM_Cleanup тем же способом (добавить в список копирования установщика) — до этого мод в игру не попадает.
3. Включать только на новой игре: старый сейв хранит лагеря, их жителей и здания; REMOVED и удаление зданий поверх старого сейва дадут рассинхрон.
