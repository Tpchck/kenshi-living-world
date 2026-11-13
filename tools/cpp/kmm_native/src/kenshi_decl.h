// Minimal declarations of the KenshiLib exports used by KMM_Native.
// Signatures mirror tools/ref/KenshiLib/Include (checked against the mangled names in tools/cpp/lib/KenshiLib.def),
// so this file needs neither Boost nor Ogre headers. If a signature changes, the link step fails (unresolved external).
#pragma once
#include <string>
#include <stdint.h>

// C4251: same warning as in KenshiLib's own Kenshi.h (std::string member in an imported class); layout is what matters
#pragma warning(disable: 4251)
#define KLIB_IMPORT __declspec(dllimport)

// Debug.h
KLIB_IMPORT void DebugLog(const char* message);   // ?DebugLog@@YAXPEBD@Z
KLIB_IMPORT void ErrorLog(const char* message);   // ?ErrorLog@@YAXPEBD@Z

// core/Functions.h
namespace KenshiLib
{
    KLIB_IMPORT intptr_t GetRealAddress(void* fun);
    enum HookStatus { SUCCESS, FAIL };
    KLIB_IMPORT HookStatus AddHook(void* target, void* detour, void** original);

    // kenshi/Kenshi.h (copied layout: enum + std::string, all members inline except ctor/dtor/copy that KenshiLib exports)
    class KLIB_IMPORT BinaryVersion
    {
    public:
        enum KenshiPlatform { GOG, STEAM, UNKNOWN };
        BinaryVersion(KenshiPlatform platform, std::string version) : platform(platform), version(version) {}
        KenshiPlatform GetPlatform() { return platform; }
        std::string GetVersion() { return version; }
    private:
        KenshiPlatform platform;
        std::string version;
    };
    KLIB_IMPORT BinaryVersion GetKenshiVersion();
}

// kenshi/WorldEventStateQuery.h. KLIB_IMPORT обязателен: без dllimport &func = локальный thunk плагина (jmp [IAT]),
// а GetRealAddress принимает только адреса внутри KenshiLib.dll -> assert и краш (смоук 2026-11-12)
class GameData;
class KLIB_IMPORT WorldEventStateQuery
{
public:
    static WorldEventStateQuery* getFromData(GameData* d);   // RVA 0x9A7DC0 (1.0.65)
    bool isTrue() const;                                     // RVA 0x9A6650 (1.0.65)
};

// NATIVE2: read-only access to the faction/platoon registry (kenshi/GameWorld.h, Faction.h, Platoon.h; layouts checked by build_verify.bat)
class GameWorld;
class Faction;
KLIB_IMPORT extern GameWorld* ou;   // ?ou@@3PEAVGameWorld@@EA, the game world singleton
#define KMM_GW_FACTIONMGR_OFF   0x4A8   // GameWorld::factionMgr
#define KMM_FAC_ACTIVE_OFF      0x208   // Faction::activePlatoons   (lektor<Platoon*>)
#define KMM_FAC_UNLOADED_OFF    0x220   // Faction::unloadedPlatoons (lektor<Platoon*>)
#define KMM_LEKTOR_COUNT_OFF    8       // lektor<T>::count (uint32)
#define KMM_LEKTOR_STUFF_OFF    16      // lektor<T>::stuff (T*)
#define KMM_PLT_CHARCOUNT_OFF   0xA0    // Platoon::_characterCountCurrent (int)
#define KMM_PLT_ISDEAD_OFF      0x1F0   // Platoon::isDead (bool)
#define KMM_PLT_IMPRISONED_OFF  0x1F1   // Platoon::imprisoned (bool)
// kenshi/SaveManager.h — только для смоук-теста (загрузка тестового сейва до мира), см. L_smoke_load
class KLIB_IMPORT SaveManager
{
public:
    static SaveManager* getSingleton();          // RVA 0x37D7E0 (1.0.65)
    void load(const std::string& name);          // RVA 0x47AD00 (1.0.65): то же, что выбор сейва в меню загрузки
};

class KLIB_IMPORT FactionManager
{
public:
    Faction* getFactionByStringID(const std::string& sid);   // RVA 0x2E7570 (1.0.65)
};

// P4 (B2): long-term character memory, kenshi/Character.h:87-101 (enum) and :544-545 (methods).
// Only the LongTerm overloads are declared, so the call is never ambiguous (Lua binding has both overloads with int enums).
// Mangled: ?rememberCharacter@Character@@QEAAXPEAV1@W4CharacterPerceptionTags_LongTerm@@@Z,
//          ?getCharacterMemoryTag@Character@@QEAA_NPEAV1@W4CharacterPerceptionTags_LongTerm@@@Z (KenshiLib.def)
enum CharacterPerceptionTags_LongTerm
{
    LT_NONE,
    LT_MY_INTRUDER,
    LT_MY_LIFESAVER,
    LT_FREED_ME,
    LT_STOLE_FROM_ME,
    LT_MY_CAPTOR,
    LT_FRIENDLY_AQUAINTANCE,
    LT_DEFEATED_MY_SQUAD_ONCE,
    LT_SQUAD_LOST_TO_ME_ONCE,
    LT_KILLED_MY_FRIEND,
    LT_I_SCREWED_THIS_GUY,
    LT_MAX
};
class KLIB_IMPORT Character
{
public:
    void rememberCharacter(Character* who, CharacterPerceptionTags_LongTerm mem);      // RVA 0x6732A0 (1.0.65)
    bool getCharacterMemoryTag(Character* who, CharacterPerceptionTags_LongTerm mem);  // RVA 0x6745F0 (1.0.65)
};
