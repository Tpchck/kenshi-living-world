# BACKLOG — очередь разработки через ядро (сводит docs/core/*.md)
Обновлено 2026-11-15 (планировщик). Что установлено и маркеры — `docs/STATUS.md`, таблицы «Установлено».

## Сделано (установлено, в игре не проверено)
- Баги B1–B8 (homeless без фракции, rememberCharacter через плагин, knockoutForceTimer, isChainedMode/хозяин цепей, TGM isTown, бесстрашие по людям, руда TaskType, маркеры B8) — закрыты пакетом 1, см. STATUS «Установлено 2026-11-15 (пакет 1)».
- Пакет 1 (P1–P6): баги + кривая XP в CONSTANTS + шина KMM_Deeds из affectRelations — STATUS «пакет 1».
- Пакет 2 (Q1–Q5, R1–R5): соперники-искатели homeless, ванильные награды/HUNT_BOUNTIES, память/долг, осады кампаниями, RELSYNC, tradeGoodsMults, карта через слухи, касса = богатство, запах боя — STATUS «пакет 2 + R».
- Пакеты 3–4 (S2–S6, T1–T2): CORESYNC, постоянные отряды с ванильными пакетами ИИ, DIPLO_COND, общий такт, судьбы → награды, дирижёр в 6 частях — STATUS «пакеты 3–4».
- Пакет 5 (U1–U4, V1, W1): пакеты ИИ Traces, рейд на базу кампанией, STARVED построек, пополнение по жизни города, гонка за рекрутом, чистка мёртвого кода — STATUS «пакет 5».

## Пакет 6 — В РАБОТЕ (не планировать заново)
| id | файлы | что |
|---|---|---|
| X1 | KMM_Outlaws.lua | перехват пленника охотника (DC_CARRYING_BOUNTY_ALIVE, FIND_CAGE_AND_PUT_IN_IF_BOUNTY) |
| X2 | KMM_RecruitRace.lua | конкурент перекупает наёмников (setContractJob) и рабов на рынке |
| X3 | kmm_diplo.lua, tools/streams/diplo.py | поединок с лидером конкурента (DA_FLAG_TEMP_ENEMY), без войны фракций |
| X4 | KMM_RelicRace.lua, tools/streams/fix.py | конкуренты реально грабят руины, общий rival_tier |

## Пакет 7 — очередь (после установки пакета 6)
Отбор: grep по build/*/scripts/init/*.lua 2026-11-15 — ни один рычаг ниже в коде не используется. Владение файлами не пересекается.
| id | цель (какое решение игрока меняется) | рычаг ядра (статус) | файлы | риск | маркер |
|---|---|---|---|---|---|
| Y1 | Свидетели: дело игрока становится слухом/наградой только если его видели — прятаться, бить без свидетелей, маскироваться | колбэк `BountyManager::notifyCrimeWitnessed` (C:64) ✓код; `SensoryData::amIAwareOfThisGuy(pc)` ✓код | KMM_Deeds.lua + тест | низкий: новый колбэк, сначала лог + emit с флагом witnessed | deeds.log `witness:` `crime seen` |
| Y2 | Разгром банд реально обескровливает фракцию (ваниль режет её спавн) — игрок выбирает, кого истощать | `ProsperityManager::notifySquadDefeated(template)` (BR:11251) ✓код, эффект ?; вызов на подтверждённом `Faction::destroyPlatoon` (уже в Sync) | KMM_Conductor_Sync.lua + тест | средний: смысл template ?, кап в сутки на фракцию | debug.log `PROSPERITY defeated` |
| Y3 | Побеждённый лежит, пока его не связали или не отпустили (с таймаутом): связать и сдать/продать, отпустить или добить; кто победил — из ядра | override `MedicalSystem::canGetUpWakeUp` (C:717) ✓код; `Character.lastGuyWhoDefeatedMe` (Character.h:550) ✓код | KMM_Self.lua + тест | средний: горячий override — только отмеченные KO в бою с игроком/конкурентом, кэш по handle, таймаут | debug.log `KO hold:` `KO release` |
| Y4 | Засады хищников держат участок дороги ограниченное время всем отрядом — игрок читает дорогу: ждать, обойти, прорваться | `Blackboard::addSquadJob(..., endTime, TEE_REMOVE_WHOLE_SQUADS)` + `AI:setCenterOfMovement/setManuveringFreedomLevel` ✓код; фолбэк — нынешний addOrder (Predators:68) | KMM_Predators.lua + тест | средний: методы без следа в игре | predators.log `squadjob ok/FAIL` |
| Y5 | Конкурент решает напасть/торговаться/уйти по видимой силе отряда игрока: сильный отряд отпугивает, одиночка провоцирует | `StateBroadcastData.apparentStrength/actualStrength` ✓код; `Blackboard.moraleIsBroken` ✓код; фолбэк — тиры | KMM_Nemesis.lua + тест | низкий: только чтение полей | nemesis.log `appraise: app=` |

## Пакет 8 — очередь (после пакета 7; Z1, Z3 расширяют X2)
| id | цель | рычаг ядра (статус) | файлы | риск | маркер |
|---|---|---|---|---|---|
| Z1 | Датчики дел: выкуп раба игроком → раб помнит (LT_FREED_ME), продажа людей → обида фракции проданного/аболиционистов; кража замечена → жертва помнит вора (LT_STOLE_FROM_ME) | notify `Character::changeSlaveOwner` ✓код; notify `Character::_NV_ImStealingDoYouNotice` (C:44) ✓код; запись памяти — экспорт Nemesis (плагин P4) | KMM_Deeds.lua + тест | низкий: только слушать, память через готовый путь | deeds.log `slave_owner:` `theft noticed:` |
| Z2 | Скупщики по состоянию мира: в осаждённом/голодном городе берут краденое и запрещёнку, в сытом — нет; кризис открывает рынок сбыта | override `Platoon::iBuyStolenGoods/iBuyIllegalGoods` ✓код; состояние города — склад Stock | kmm_stock.lua + тест | средний: частота override ? — кэш по городу, вернуть nil при сомнении | stock.log `FENCE town=` |
| Z3 | Гонка за рекрутом не обрывается при уходе игрока: исход по прошедшему времени при следующей загрузке города (мир живёт без игрока) — хвост STATUS | `getTotalHours` ✓код; `Character::setFaction` (проба V1) ✓код | KMM_RecruitRace.lua + тест | низкий | recruitrace.log `race resolved offline` |
| Z4 | Слава игрока за победы над именными конкурентами — ванильные диалоги и фракции реагируют на репутацию бойца | `FactionRelations::affectReputation(p, amount)` (FactionRelations.h:66) ✓код; `globalReputationForBadassery` ✓код, семантика ? — сначала чтение+лог, запись малыми дельтами с капом | KMM_Nemesis.lua + тест | средний: семантика полей ? | nemesis.log `fame: rep=` |
| Z5 | Характер после встречи: побитый игроком конкурент осторожнее (STUBBOURNESS↓), убийца злее (MURDEROUS↑) — следующая встреча идёт иначе | `CharStats.STUBBOURNESS/MURDEROUS` (CharStats.h:202-208) ✓код, сохранение в сейве ?; триггер — `lastGuyWhoDefeatedMe` | KMM_Fates.lua + тест | средний: перечитать на загрузке и залогировать, сохранилось ли | fates.log `temper: stub=` |

## Не взято и почему
- RECRUIT_RACE §3B (уникальные рекруты в дальнем мире) — по самому документу только после маркеров A из живой игры.
- DEADCODE §B — ждёт игровую проверку. `xpStat_eventBased` — нужен замер amount на NPC (игра). `ZoneMap:isActive` вместо радиуса 15000 — следующий кандидат (Conductor_Sync/Siege).
- Хвост KMM_Town (входы построек обнуляются при удалении мода) — мелкий, вне пакетов: kmm_town.lua, при выключении восстанавливать входы.

## Хвосты после ревью пакетов 6–7 (2026-11-15)
- KMM_Gov снимок: ключ `rec.h` строится через tostring(hand) — перевести на hand:toString() (подтверждён в игре); потребители: RecruitRace уже не использует.
- Освобождение раба из списка RecruitRace даёт два события (`debt_made` Nemesis + `recruit_slave_freed`) — Nemesis пропускать debt_made для R.slave.bought.
- Невольничий рынок (changeSlaveOwner) выключен: в ядре нет вывода из клетки; вернуться, если найдётся рычаг.
