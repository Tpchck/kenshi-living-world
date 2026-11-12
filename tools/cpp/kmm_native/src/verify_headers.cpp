// Build-time check: our minimal declarations match the real KenshiLib headers (needs Boost, see build_verify.bat).
#define protected public
#define private public
#include <kenshi/GameData.h>
#include <kenshi/WorldEventStateQuery.h>
#include <kenshi/Kenshi.h>
#include <kenshi/Faction.h>
#include <kenshi/Platoon.h>
#include <kenshi/GameWorld.h>
#include <stddef.h>
typedef char assert_stringID_offset[(offsetof(GameData, stringID) == 0x58) ? 1 : -1];
typedef char assert_string_size[(sizeof(std::string) == 40) ? 1 : -1];
// layouts read by the NATIVE2 faction force code (kenshi_decl.h / kmm_native.cpp)
typedef char assert_lektor_size[(sizeof(lektor<Platoon*>) == 0x18) ? 1 : -1];
typedef char assert_lektor_count[(offsetof(lektor<Platoon*>, count) == KMM_LEKTOR_COUNT_OFF) ? 1 : -1];
typedef char assert_lektor_stuff[(offsetof(lektor<Platoon*>, stuff) == KMM_LEKTOR_STUFF_OFF) ? 1 : -1];
typedef char assert_fac_active[(offsetof(Faction, activePlatoons) == 0x208) ? 1 : -1];
typedef char assert_fac_unloaded[(offsetof(Faction, unloadedPlatoons) == 0x220) ? 1 : -1];
typedef char assert_plt_count[(offsetof(Platoon, _characterCountCurrent) == 0xA0) ? 1 : -1];
typedef char assert_plt_dead[(offsetof(Platoon, isDead) == 0x1F0) ? 1 : -1];
typedef char assert_plt_prison[(offsetof(Platoon, imprisoned) == 0x1F1) ? 1 : -1];
typedef char assert_gw_fm[(offsetof(GameWorld, factionMgr) == 0x4A8) ? 1 : -1];
bool (WorldEventStateQuery::*vIsTrue)() const = &WorldEventStateQuery::isTrue;
WorldEventStateQuery* (*vGet)(GameData*) = &WorldEventStateQuery::getFromData;
KenshiLib::BinaryVersion (*vVer)() = &KenshiLib::GetKenshiVersion;
Faction* (FactionManager::*vFbs)(const std::string&) = &FactionManager::getFactionByStringID;
