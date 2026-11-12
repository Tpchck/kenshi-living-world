// KMM_Native v2.4 (NATIVE2: + read-only faction_force; + tooltip compaction; + P4 LongTerm memory; + 2.4 salvage/butcher menu, salvage.cpp) - RE_Kenshi plugin.
//  * hooks WorldEventStateQuery::isTrue (via KenshiLib::AddHook) and applies per-stringID overrides set from Lua;
//  * exposes the Lua module "kmm_native" through the KenshiLua C++ Extension SDK.
// Rules: no exception crosses the DLL boundary, any init failure is logged and the plugin stays inert,
// the hook never touches Lua, the Lua functions only run on the Lua thread (they are called by Lua itself).
#define WIN32_LEAN_AND_MEAN
#ifndef _WIN32_WINNT
#define _WIN32_WINNT 0x0601
#endif
#include <windows.h>
#include <stdio.h>
#include <stdarg.h>
#include <stddef.h>
#include <string.h>
#include <string>
#include <vector>
#include <unordered_map>

#include "kenshi_decl.h"
#include "KenshiLua.h"
#include "tooltip_compact.h"
#include "salvage.h"

#define KMM_VERSION "2.4.0"
#define KMM_EXPECTED_GAME_VERSION "1.0.65"
#define GAMEDATA_STRINGID_OFFSET 0x58   // GameData::stringID (kenshi/GameData.h, std::string, VC10 x64 layout)
#define SID_MAX 255

// ---------------------------------------------------------------- logging
static void Log(const char* msg, bool isError)
{
    try
    {
        std::string s("KMM_Native: ");
        s += msg;
        if (isError) ErrorLog(s.c_str()); else DebugLog(s.c_str());
    }
    catch (...) {}
}
static void Logf(bool isError, const char* fmt, ...)
{
    char buf[512];
    va_list ap;
    va_start(ap, fmt);
    _vsnprintf_s(buf, sizeof(buf), _TRUNCATE, fmt, ap);
    va_end(ap);
    Log(buf, isError);
}
// salvage.cpp logs through here (salvage.h)
void KmmLog(bool isError, const char* fmt, ...)
{
    char buf[512];
    va_list ap;
    va_start(ap, fmt);
    _vsnprintf_s(buf, sizeof(buf), _TRUNCATE, fmt, ap);
    va_end(ap);
    Log(buf, isError);
}

// ---------------------------------------------------------------- state
namespace
{
    struct Tables
    {
        SRWLOCK lock;
        std::unordered_map<const void*, int> queryToId;   // WorldEventStateQuery* -> sid id
        std::unordered_map<std::string, int> sidToId;
        std::vector<signed char> ov;                      // per sid id: -1 none, 0 false, 1 true
    };

    Tables* g_t = NULL;                  // allocated once, never freed (no destructor order problems at exit)
    volatile LONG g_active = 0;          // number of active overrides; 0 -> hot path returns immediately
    volatile LONG g_hookInstalled = 0;   // isTrue hook installed
    volatile LONG g_getHookInstalled = 0;
    volatile LONG g_nHits = 0;           // overrides applied
    volatile LONG g_nUnmapped = 0;       // isTrue calls on queries we have no sid for (while overrides active)
    volatile LONG g_nMapped = 0;
    bool g_enabled = false;
    bool g_wsHook = false;
    bool g_luaRegistered = false;
    bool g_forceRead = false;            // NATIVE2: faction_force enabled (config + gates passed)
    bool g_uniqueSet = false;            // NATIVE2: config flag only; no verified registry write exists (see docs\PLUGIN.md)
    bool g_memory = false;               // P4: remember_lt / memory_lt enabled (config "native_memory", default true, + version gate)
    volatile LONG g_nRemembered = 0;     // LongTerm tags written
    volatile LONG g_memLoggedFirst = 0;

    bool (*g_isTrueOrig)(const void*) = NULL;
    void* (*g_getFromDataOrig)(void*) = NULL;

    struct SharedLock
    {
        explicit SharedLock(SRWLOCK* l) : l_(l) { AcquireSRWLockShared(l_); }
        ~SharedLock() { ReleaseSRWLockShared(l_); }
        SRWLOCK* l_;
    private:
        SharedLock(const SharedLock&); SharedLock& operator=(const SharedLock&);
    };
    struct ExclusiveLock
    {
        explicit ExclusiveLock(SRWLOCK* l) : l_(l) { AcquireSRWLockExclusive(l_); }
        ~ExclusiveLock() { ReleaseSRWLockExclusive(l_); }
        SRWLOCK* l_;
    private:
        ExclusiveLock(const ExclusiveLock&); ExclusiveLock& operator=(const ExclusiveLock&);
    };

    // id for a sid, creating it if needed. Caller holds the exclusive lock.
    int InternLocked(const std::string& sid)
    {
        std::unordered_map<std::string, int>::iterator it = g_t->sidToId.find(sid);
        if (it != g_t->sidToId.end()) return it->second;
        int id = (int)g_t->ov.size();
        g_t->ov.push_back(-1);
        g_t->sidToId.insert(std::make_pair(sid, id));
        return id;
    }
}

// ---------------------------------------------------------------- reading GameData::stringID safely
// std::string, VC10 x64: char buf[16] | char* ptr; size_t size (+16); size_t reserve (+24). Uses SEH, so no C++ objects here.
static bool ReadSid(const void* gd, char* out, size_t cap)
{
    __try
    {
        const char* base = (const char*)gd + GAMEDATA_STRINGID_OFFSET;
        size_t size = *(const size_t*)(base + 16);
        size_t res = *(const size_t*)(base + 24);
        if (res < 15 || size == 0 || size > res || size >= cap) return false;
        const char* p = (res >= 16) ? *(const char* const*)base : base;
        for (size_t i = 0; i < size; ++i)
        {
            unsigned char c = (unsigned char)p[i];
            if (c < 0x20) return false;
            out[i] = (char)c;
        }
        out[size] = 0;
        return true;
    }
    __except (EXCEPTION_EXECUTE_HANDLER)
    {
        return false;
    }
}

// ---------------------------------------------------------------- hooks
static void* getFromData_hook(void* d)
{
    void* q = g_getFromDataOrig ? g_getFromDataOrig(d) : NULL;
    if (!q || !d || !g_t) return q;
    try
    {
        {
            SharedLock sl(&g_t->lock);
            if (g_t->queryToId.find(q) != g_t->queryToId.end()) return q;   // already mapped (one query per GameData)
        }
        char buf[SID_MAX + 1];
        if (!ReadSid(d, buf, sizeof(buf))) return q;
        std::string sid(buf);
        ExclusiveLock el(&g_t->lock);
        int id = InternLocked(sid);
        if (g_t->queryToId.insert(std::make_pair((const void*)q, id)).second)
            InterlockedIncrement(&g_nMapped);
    }
    catch (...) {}
    return q;
}

static bool isTrue_hook(const void* self)
{
    bool r = g_isTrueOrig ? g_isTrueOrig(self) : false;
    if (g_active == 0 || !g_t) return r;   // hot path: nothing to override
    try
    {
        SharedLock sl(&g_t->lock);
        std::unordered_map<const void*, int>::const_iterator it = g_t->queryToId.find(self);
        if (it == g_t->queryToId.end())
        {
            InterlockedIncrement(&g_nUnmapped);
            return r;
        }
        signed char v = g_t->ov[(size_t)it->second];
        if (v >= 0)
        {
            InterlockedIncrement(&g_nHits);
            return v != 0;
        }
    }
    catch (...) {}
    return r;
}


// ---------------------------------------------------------------- TOOLTIP: compaction of per-race lines (v2.2)
// Hooks InventoryItemBase/Sword/Crossbow::getTooltipData1 (the functions that emit "Damage vs <race> +N%" lines and the
// "-Only for:" race list; found by their string references in kenshi_x64.exe 1.0.65). We call the original, then post-process
// the std::vector<StringPair> it filled. The vector is never reallocated: only strings of EXISTING elements are overwritten,
// then the trailing elements are destroyed (their two std::strings) and the end pointer is moved back.
// Every layout assumption is checked at runtime; on any doubt or exception the lines stay as the game made them,
// and the feature is switched off for the rest of the session.
namespace
{
    struct SPView                       // StringPair (kenshi/util/StringPair.h): vtable, s1 @0x8, s2 @0x30, val1 @0x58
    {
        void* vt;
        std::string s1;
        std::string s2;
        float val1;
    };
    struct VecView { SPView* first; SPView* last; SPView* end; };   // VC10 x64 std::vector: _Myfirst, _Mylast, _Myend (empty allocator)
    typedef char chk_sp_size[(sizeof(SPView) == 0x60) ? 1 : -1];
    typedef char chk_sp_s1[(offsetof(SPView, s1) == 0x8) ? 1 : -1];
    typedef char chk_sp_s2[(offsetof(SPView, s2) == 0x30) ? 1 : -1];
    typedef char chk_sp_v1[(offsetof(SPView, val1) == 0x58) ? 1 : -1];
    typedef char chk_str_size[(sizeof(std::string) == 40) ? 1 : -1];

    volatile LONG g_ttOff = 0;          // set once something looks wrong
    volatile LONG g_ttHooks = 0;        // installed hooks
    volatile LONG g_ttCompacted = 0;    // tooltips changed
    volatile LONG g_ttLoggedFirst = 0;
    bool g_ttWanted = true;             // config "tooltip_compact"
    const unsigned char* g_exeBase = NULL;
    size_t g_exeSize = 0;

    void (*g_tipOrigSword)(void*, void*) = NULL;
    void (*g_tipOrigXbow)(void*, void*) = NULL;
    void (*g_tipOrigBase)(void*, void*) = NULL;

    bool StrOk(const std::string& s)
    {
        const size_t* f = (const size_t*)&s;     // buf[16] | ptr ; size @16 ; reserve @24
        size_t size = f[2], res = f[3];
        return res >= 15 && res < (1u << 20) && size <= res && (res < 16 || f[0] != 0);
    }
    bool InExe(const void* p)
    {
        return g_exeBase && p >= (const void*)g_exeBase && p < (const void*)(g_exeBase + g_exeSize);
    }

    // C++ objects live here, SEH lives in TipProcessSeh. Returns 1 changed, 0 untouched, -1 invalid layout / exception.
    int TipProcessInner(void* vecp)
    {
        try
        {
            VecView* v = (VecView*)vecp;
            if (!v->first || !v->last || !v->end) return 0;
            if (((uintptr_t)v->first & 7) || ((uintptr_t)v->last & 7) || ((uintptr_t)v->end & 7)) return -1;
            if (v->first > v->last || v->last > v->end) return -1;
            size_t bytes = (size_t)((const char*)v->last - (const char*)v->first);
            if (bytes % sizeof(SPView) != 0) return -1;
            size_t n = bytes / sizeof(SPView);
            if (n < (size_t)kmmtip::RUN_MIN) return 0;       // nothing to merge in short tooltips
            if (n > 2000) return -1;
            void* vt = v->first[0].vt;
            if (!InExe(vt)) return -1;                       // every StringPair vtable lives in the game executable
            std::vector<kmmtip::Line> in;
            in.reserve(n);
            for (size_t i = 0; i < n; ++i)
            {
                const SPView& e = v->first[i];
                if (e.vt != vt || !StrOk(e.s1) || !StrOk(e.s2)) return -1;
                uint32_t bits;
                memcpy(&bits, &e.val1, 4);
                in.push_back(kmmtip::Line(e.s1, e.s2, bits));
            }
            std::vector<kmmtip::Line> out;
            if (!kmmtip::Compact(in, out)) return 0;
            if (out.empty() || out.size() >= n) return 0;
            for (size_t i = 0; i < out.size(); ++i)          // overwrite existing elements (std::string assign, same CRT as the game)
            {
                SPView& e = v->first[i];
                e.s1 = out[i].s1;
                e.s2 = out[i].s2;
                memcpy(&e.val1, &out[i].vbits, 4);
            }
            for (size_t i = out.size(); i < n; ++i)          // destroy the surplus tail; StringPair owns nothing but the two strings
            {
                v->first[i].s1.~basic_string();
                v->first[i].s2.~basic_string();
            }
            v->last = v->first + out.size();
            return 1;
        }
        catch (...) { return -1; }
    }
    int TipProcessSeh(void* vecp)
    {
        __try { return TipProcessInner(vecp); }
        __except (EXCEPTION_EXECUTE_HANDLER) { return -1; }
    }
    void TipAfter(void* vecp)
    {
        if (g_ttOff || !vecp) return;
        int r = TipProcessSeh(vecp);
        if (r > 0)
        {
            InterlockedIncrement(&g_ttCompacted);
            if (InterlockedExchange(&g_ttLoggedFirst, 1) == 0) Log("tooltip compaction applied (first time)", false);
        }
        else if (r < 0)
        {
            if (InterlockedExchange(&g_ttOff, 1) == 0) Log("tooltip compaction: unexpected vector/string state or exception, feature disabled for this session", true);
        }
    }
    void tip_sword_hook(void* self, void* vec) { if (g_tipOrigSword) g_tipOrigSword(self, vec); TipAfter(vec); }
    void tip_xbow_hook(void* self, void* vec) { if (g_tipOrigXbow) g_tipOrigXbow(self, vec); TipAfter(vec); }
    void tip_base_hook(void* self, void* vec) { if (g_tipOrigBase) g_tipOrigBase(self, vec); TipAfter(vec); }
}

// ---------------------------------------------------------------- override table API (thread-safe)
static bool ws_set(const std::string& sid, bool value)
{
    if (!g_t || !g_hookInstalled || sid.empty() || sid.size() > SID_MAX) return false;
    try
    {
        ExclusiveLock el(&g_t->lock);
        int id = InternLocked(sid);
        if (g_t->ov[(size_t)id] < 0) InterlockedIncrement(&g_active);
        g_t->ov[(size_t)id] = value ? 1 : 0;
        return true;
    }
    catch (...) { return false; }
}

static bool ws_clear(const std::string& sid)
{
    if (!g_t) return false;
    try
    {
        ExclusiveLock el(&g_t->lock);
        std::unordered_map<std::string, int>::iterator it = g_t->sidToId.find(sid);
        if (it == g_t->sidToId.end() || g_t->ov[(size_t)it->second] < 0) return false;
        g_t->ov[(size_t)it->second] = -1;
        InterlockedDecrement(&g_active);
        return true;
    }
    catch (...) { return false; }
}

static int ws_clear_all()
{
    if (!g_t) return 0;
    try
    {
        ExclusiveLock el(&g_t->lock);
        int n = 0;
        for (size_t i = 0; i < g_t->ov.size(); ++i)
            if (g_t->ov[i] >= 0) { g_t->ov[i] = -1; ++n; }
        InterlockedExchange(&g_active, 0);
        return n;
    }
    catch (...) { return 0; }
}

// -1 none, 0 false, 1 true
static int ws_get(const std::string& sid)
{
    if (!g_t) return -1;
    try
    {
        SharedLock sl(&g_t->lock);
        std::unordered_map<std::string, int>::const_iterator it = g_t->sidToId.find(sid);
        return it == g_t->sidToId.end() ? -1 : (int)g_t->ov[(size_t)it->second];
    }
    catch (...) { return -1; }
}

// ---------------------------------------------------------------- Lua module (raw KenshiLua C ABI, runs on the Lua thread)
enum { LT_BOOLEAN = 1, LT_STRING = 4 };

static KenshiLua_ApiV1* Api() { return KenshiLua::Detail::GetApi(); }

// returns false if argument idx is not a string
static bool ArgString(KenshiLua_ApiV1* a, lua_State* L, int idx, std::string& out)
{
    if (a->type(L, idx) != LT_STRING) return false;
    size_t len = 0;
    const char* s = a->toLString(L, idx, &len);
    if (!s) return false;
    out.assign(s, len);
    return true;
}

static int L_ws_set(lua_State* L)
{
    KenshiLua_ApiV1* a = Api();
    if (!a) return 0;
    try
    {
        std::string sid;
        bool ok = ArgString(a, L, 1, sid) && a->type(L, 2) == LT_BOOLEAN && ws_set(sid, a->toBoolean(L, 2) != 0);
        a->pushBoolean(L, ok ? 1 : 0);
    }
    catch (...) { a->pushBoolean(L, 0); }
    return 1;
}

static int L_ws_clear(lua_State* L)
{
    KenshiLua_ApiV1* a = Api();
    if (!a) return 0;
    try
    {
        std::string sid;
        a->pushBoolean(L, (ArgString(a, L, 1, sid) && ws_clear(sid)) ? 1 : 0);
    }
    catch (...) { a->pushBoolean(L, 0); }
    return 1;
}

static int L_ws_clear_all(lua_State* L)
{
    KenshiLua_ApiV1* a = Api();
    if (!a) return 0;
    a->pushInteger(L, (ptrdiff_t)ws_clear_all());
    return 1;
}

static int L_ws_get(lua_State* L)
{
    KenshiLua_ApiV1* a = Api();
    if (!a) return 0;
    try
    {
        std::string sid;
        int v = ArgString(a, L, 1, sid) ? ws_get(sid) : -1;
        if (v < 0) a->pushNil(L); else a->pushBoolean(L, v);
    }
    catch (...) { a->pushNil(L); }
    return 1;
}

static int L_ws_hook_active(lua_State* L)
{
    KenshiLua_ApiV1* a = Api();
    if (!a) return 0;
    a->pushBoolean(L, g_hookInstalled ? 1 : 0);
    return 1;
}

static void SetNum(KenshiLua_ApiV1* a, lua_State* L, const char* key, double v)
{
    a->pushNumber(L, v);
    a->setField(L, -2, key);
}

static int L_ws_stats(lua_State* L)
{
    KenshiLua_ApiV1* a = Api();
    if (!a) return 0;
    a->newTable(L);
    SetNum(a, L, "hooked", g_hookInstalled ? 1 : 0);
    SetNum(a, L, "get_hook", g_getHookInstalled ? 1 : 0);
    SetNum(a, L, "queries_mapped", (double)g_nMapped);
    SetNum(a, L, "overrides", (double)g_active);
    SetNum(a, L, "hits", (double)g_nHits);
    SetNum(a, L, "unmapped_calls", (double)g_nUnmapped);
    SetNum(a, L, "tooltip_hooks", (double)g_ttHooks);
    SetNum(a, L, "tooltip_compacted", (double)g_ttCompacted);
    SetNum(a, L, "tooltip_off", (double)g_ttOff);
    SetNum(a, L, "memory", g_memory ? 1 : 0);
    SetNum(a, L, "remembered", (double)g_nRemembered);
    return 1;
}

// ---------------------------------------------------------------- NATIVE2: faction force (read only, SEH)
struct ForceResult
{
    int ok;                       // 1 = faction found and lists read
    int activeSquads, activeChars, unloadedSquads, unloadedChars, deadSquads, imprisonedSquads;
};

// lektor<Platoon*> at faction+off -> sums platoon data. No C++ objects (SEH). Returns false on any fault or implausible data.
static bool ReadPlatoonList(const char* faction, size_t off, int* squads, int* chars, int* dead, int* prison)
{
    __try
    {
        const char* lk = faction + off;
        unsigned int count = *(const unsigned int*)(lk + KMM_LEKTOR_COUNT_OFF);
        const char* const* stuff = *(const char* const* const*)(lk + KMM_LEKTOR_STUFF_OFF);
        if (count == 0) return true;
        if (count > 20000 || !stuff) return false;
        for (unsigned int i = 0; i < count; ++i)
        {
            const char* p = stuff[i];
            if (!p || ((uintptr_t)p & 7) != 0) continue;
            bool isDead = *(const unsigned char*)(p + KMM_PLT_ISDEAD_OFF) != 0;
            bool isPrison = *(const unsigned char*)(p + KMM_PLT_IMPRISONED_OFF) != 0;
            int n = *(const int*)(p + KMM_PLT_CHARCOUNT_OFF);
            if (isDead) { ++*dead; continue; }
            if (isPrison) ++*prison;
            if (n < 0 || n > 1000) n = 0;
            ++*squads;
            *chars += n;
        }
        return true;
    }
    __except (EXCEPTION_EXECUTE_HANDLER)
    {
        return false;
    }
}

static Faction* FindFactionSeh(const std::string& sid)
{
    __try
    {
        if (!ou) return NULL;
        FactionManager* fm = *(FactionManager* const*)((const char*)ou + KMM_GW_FACTIONMGR_OFF);
        if (!fm) return NULL;
        return fm->getFactionByStringID(sid);
    }
    __except (EXCEPTION_EXECUTE_HANDLER)
    {
        return NULL;
    }
}

static bool FactionForce(const std::string& sid, ForceResult& r)
{
    memset(&r, 0, sizeof(r));
    if (!g_forceRead || sid.empty() || sid.size() > SID_MAX) return false;
    Faction* f = FindFactionSeh(sid);
    if (!f) return false;
    const char* fc = (const char*)f;
    int dead = 0, prison = 0;
    if (!ReadPlatoonList(fc, KMM_FAC_ACTIVE_OFF, &r.activeSquads, &r.activeChars, &dead, &prison)) return false;
    if (!ReadPlatoonList(fc, KMM_FAC_UNLOADED_OFF, &r.unloadedSquads, &r.unloadedChars, &dead, &prison)) return false;
    r.deadSquads = dead;
    r.imprisonedSquads = prison;
    r.ok = 1;
    return true;
}

static int L_faction_force(lua_State* L)
{
    KenshiLua_ApiV1* a = Api();
    if (!a) return 0;
    try
    {
        std::string sid;
        ForceResult r;
        if (!ArgString(a, L, 1, sid) || !FactionForce(sid, r)) { a->pushNil(L); return 1; }
        a->newTable(L);
        SetNum(a, L, "squads", r.activeSquads + r.unloadedSquads);
        SetNum(a, L, "chars", r.activeChars + r.unloadedChars);
        SetNum(a, L, "active_squads", r.activeSquads);
        SetNum(a, L, "active_chars", r.activeChars);
        SetNum(a, L, "unloaded_squads", r.unloadedSquads);
        SetNum(a, L, "unloaded_chars", r.unloadedChars);
        SetNum(a, L, "dead_squads", r.deadSquads);
        SetNum(a, L, "imprisoned_squads", r.imprisonedSquads);
    }
    catch (...) { a->pushNil(L); }
    return 1;
}

// ---------------------------------------------------------------- P4 (B2): long-term memory (Character::rememberCharacter LT, RVA 0x6732A0)
// Lua passes Character userdata; the pointer is taken with testObject (never raises a Lua error) under the metatables a
// character can carry. CharacterHuman/CharacterAnimal derive only from Character (single inheritance) -> same pointer.
static const char* const CHAR_MT[] = { "KenshiLua.Character", "KenshiLua.CharacterHuman", "KenshiLua.CharacterAnimal" };

static Character* ArgCharacter(KenshiLua_ApiV1* a, lua_State* L, int idx)
{
    if (!a->testObject) return NULL;
    for (size_t i = 0; i < sizeof(CHAR_MT) / sizeof(CHAR_MT[0]); ++i)
    {
        void* p = a->testObject(L, idx, CHAR_MT[i]);
        if (p && ((uintptr_t)p & 7) == 0) return (Character*)p;
    }
    return NULL;
}

// no C++ objects here (SEH)
static bool RememberLtSeh(Character* self, Character* who, int tag)
{
    __try { self->rememberCharacter(who, (CharacterPerceptionTags_LongTerm)tag); return true; }
    __except (EXCEPTION_EXECUTE_HANDLER) { return false; }
}
static int MemoryLtSeh(Character* self, Character* who, int tag)   // 1 / 0, -1 fault
{
    __try { return self->getCharacterMemoryTag(who, (CharacterPerceptionTags_LongTerm)tag) ? 1 : 0; }
    __except (EXCEPTION_EXECUTE_HANDLER) { return -1; }
}

// common argument check: (npc, who, tag 1..LT_MAX-1). Returns NULL reason on success.
static const char* MemoryArgs(KenshiLua_ApiV1* a, lua_State* L, Character** self, Character** who, int* tag)
{
    if (!g_memory) return "disabled";
    *self = ArgCharacter(a, L, 1);
    *who = ArgCharacter(a, L, 2);
    if (!*self || !*who) return "not a character";
    if (*self == *who) return "same character";
    if (a->type(L, 3) != 3 /* LUA_TNUMBER */) return "tag not a number";
    double t = a->toNumber(L, 3);
    if (!(t >= (double)LT_MY_INTRUDER && t < (double)LT_MAX) || t != (double)(int)t) return "tag out of range";
    *tag = (int)t;
    return NULL;
}

// kmm_native.remember_lt(npc, who, tag) -> true | false, reason
static int L_remember_lt(lua_State* L)
{
    KenshiLua_ApiV1* a = Api();
    if (!a) return 0;
    try
    {
        Character* self = NULL; Character* who = NULL; int tag = 0;
        const char* why = MemoryArgs(a, L, &self, &who, &tag);
        if (!why && !RememberLtSeh(self, who, tag))
        {
            why = "fault";
            g_memory = false;   // an access violation means our assumptions are wrong: no more writes this session
            Log("remember_lt: access violation in rememberCharacter(LT), native memory disabled for this session", true);
        }
        if (!why)
        {
            InterlockedIncrement(&g_nRemembered);
            if (InterlockedExchange(&g_memLoggedFirst, 1) == 0) Logf(false, "remember_lt: first LongTerm tag %d written", tag);
            a->pushBoolean(L, 1);
            return 1;
        }
        a->pushBoolean(L, 0);
        a->pushString(L, why);
        return 2;
    }
    catch (...) { a->pushBoolean(L, 0); return 1; }
}

// kmm_native.memory_lt(npc, who, tag) -> true | false | nil, reason
static int L_memory_lt(lua_State* L)
{
    KenshiLua_ApiV1* a = Api();
    if (!a) return 0;
    try
    {
        Character* self = NULL; Character* who = NULL; int tag = 0;
        const char* why = MemoryArgs(a, L, &self, &who, &tag);
        int r = why ? -1 : MemoryLtSeh(self, who, tag);
        if (r >= 0) { a->pushBoolean(L, r); return 1; }
        a->pushNil(L);
        a->pushString(L, why ? why : "fault");
        return 2;
    }
    catch (...) { a->pushNil(L); return 1; }
}

static int L_version(lua_State* L)
{
    KenshiLua_ApiV1* a = Api();
    if (!a) return 0;
    a->pushString(L, KMM_VERSION);
    return 1;
}

// Ð¡Ð¼Ð¾ÑƒÐº-Ñ‚ÐµÑÑ‚ (tools\smoke.py --world): Ð·Ð°Ð³Ñ€ÑƒÐ·Ð¸Ñ‚ÑŒ Ñ‚ÐµÑÑ‚Ð¾Ð²Ñ‹Ð¹ ÑÐµÐ¹Ð² Ð¸Ð· Ð³Ð»Ð°Ð²Ð½Ð¾Ð³Ð¾ Ð¼ÐµÐ½ÑŽ.
// Ð”Ð²Ð¾Ð¹Ð½Ð¾Ð¹ Ð·Ð°Ð¼Ð¾Ðº: Ñ€Ð°Ð±Ð¾Ñ‚Ð°ÐµÑ‚, Ñ‚Ð¾Ð»ÑŒÐºÐ¾ ÐµÑÐ»Ð¸ smoke.py Ð¿Ð¾Ð»Ð¾Ð¶Ð¸Ð» Ñ„Ð»Ð°Ð³-Ñ„Ð°Ð¹Ð»; Ð¸Ð½Ð°Ñ‡Ðµ Ð½Ð¸Ñ‡ÐµÐ³Ð¾ Ð½Ðµ Ð´ÐµÐ»Ð°ÐµÑ‚ (Ð² Ð¾Ð±Ñ‹Ñ‡Ð½Ð¾Ð¹ Ð¸Ð³Ñ€Ðµ Ð½Ðµ ÑÑ€Ð°Ð±Ð°Ñ‚Ñ‹Ð²Ð°ÐµÑ‚).
static int L_smoke_load(lua_State* L)
{
    KenshiLua_ApiV1* a = Api();
    if (!a) return 0;
    bool ok = false;
    try
    {
        std::string name;
        if (ArgString(a, L, 1, name) && !name.empty()
            && GetFileAttributesA("C:/KenshiModMap/logs/smoke_load.txt") != INVALID_FILE_ATTRIBUTES)
        {
            SaveManager* sm = SaveManager::getSingleton();
            if (sm) { Logf(false, "smoke: loading save '%s'", name.c_str()); sm->load(name); ok = true; }
        }
    }
    catch (...) { ok = false; }
    a->pushBoolean(L, ok ? 1 : 0);
    return 1;
}

static const KenshiLua_Reg g_funcs[] = {
    { "ws_set", L_ws_set },
    { "ws_clear", L_ws_clear },
    { "ws_clear_all", L_ws_clear_all },
    { "ws_get", L_ws_get },
    { "ws_hook_active", L_ws_hook_active },
    { "ws_stats", L_ws_stats },
    { "faction_force", L_faction_force },
    { "version", L_version },
    { "smoke_load", L_smoke_load },
    { "remember_lt", L_remember_lt },
    { "memory_lt", L_memory_lt },
    { NULL, NULL }
};

static int OpenModule(lua_State* L)
{
    KenshiLua_ApiV1* a = Api();
    if (!a) return 0;
    a->newTable(L);
    a->registerFunctions(L, g_funcs);
    return 1;
}

// For package.loadlib("KMM_Native.dll", "luaopen_kmm_native") when KenshiLua was not ready during startPlugin.
extern "C" __declspec(dllexport) int luaopen_kmm_native(lua_State* L)
{
    try { return OpenModule(L); }
    catch (...) { return 0; }
}

// ---------------------------------------------------------------- config
static std::string ModuleDir()
{
    HMODULE self = NULL;
    if (!GetModuleHandleExA(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS | GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT,
                            (LPCSTR)&luaopen_kmm_native, &self))
        return std::string();
    char path[MAX_PATH];
    DWORD n = GetModuleFileNameA(self, path, MAX_PATH);
    if (n == 0 || n >= MAX_PATH) return std::string();
    std::string p(path, n);
    size_t slash = p.find_last_of("\\/");
    return slash == std::string::npos ? std::string() : p.substr(0, slash);
}

static bool ReadSmallFile(const std::string& path, std::string& out)
{
    FILE* f = NULL;
    if (fopen_s(&f, path.c_str(), "rb") != 0 || !f) return false;
    char buf[1024];
    size_t n;
    out.clear();
    while ((n = fread(buf, 1, sizeof(buf), f)) > 0 && out.size() < 65536) out.append(buf, n);
    fclose(f);
    return true;
}

// value token after "key": ; empty if not found
static std::string JsonToken(const std::string& js, const char* key)
{
    std::string pat = std::string("\"") + key + "\"";
    size_t p = js.find(pat);
    if (p == std::string::npos) return std::string();
    p = js.find(':', p + pat.size());
    if (p == std::string::npos) return std::string();
    ++p;
    while (p < js.size() && (js[p] == ' ' || js[p] == '\t' || js[p] == '\r' || js[p] == '\n')) ++p;
    size_t e = p;
    if (p < js.size() && js[p] == '"')
    {
        e = js.find('"', p + 1);
        return e == std::string::npos ? std::string() : js.substr(p + 1, e - p - 1);
    }
    while (e < js.size() && js[e] != ',' && js[e] != '}' && js[e] != ' ' && js[e] != '\r' && js[e] != '\n' && js[e] != '\t') ++e;
    return js.substr(p, e - p);
}

// ---------------------------------------------------------------- init
// ÐÐ´Ñ€ÐµÑ Ð¾Ð±ÑÐ·Ð°Ð½ Ð»ÐµÐ¶Ð°Ñ‚ÑŒ Ð²Ð½ÑƒÑ‚Ñ€Ð¸ KenshiLib.dll, Ð¸Ð½Ð°Ñ‡Ðµ GetRealAddress Ð¿Ð°Ð´Ð°ÐµÑ‚ Ð½Ð° assert (Ð° Ð½Ðµ Ð²Ð¾Ð·Ð²Ñ€Ð°Ñ‰Ð°ÐµÑ‚ 0).
static bool InKenshiLib(const void* p)
{
    HMODULE m = GetModuleHandleA("KenshiLib.dll");
    if (!m || !p) return false;
    const unsigned char* base = (const unsigned char*)m;
    const IMAGE_DOS_HEADER* dos = (const IMAGE_DOS_HEADER*)base;
    if (dos->e_magic != IMAGE_DOS_SIGNATURE) return false;
    const IMAGE_NT_HEADERS* nt = (const IMAGE_NT_HEADERS*)(base + dos->e_lfanew);
    const unsigned char* q = (const unsigned char*)p;
    return q >= base && q < base + nt->OptionalHeader.SizeOfImage;
}

static bool InstallWsHook()
{
    // member function pointers -> addresses of the KenshiLib import thunks, translated by GetRealAddress
    bool (WorldEventStateQuery::*pIsTrue)() const = &WorldEventStateQuery::isTrue;
    WorldEventStateQuery* (*pGet)(GameData*) = &WorldEventStateQuery::getFromData;
    if (sizeof(pIsTrue) != sizeof(void*)) { Log("unexpected member pointer size", true); return false; }
    void* isTrueThunk = NULL;
    memcpy(&isTrueThunk, &pIsTrue, sizeof(void*));
    if (!InKenshiLib(isTrueThunk) || !InKenshiLib((void*)pGet))
    {
        Logf(true, "function address outside KenshiLib.dll (isTrue %p, getFromData %p), ws hook skipped", isTrueThunk, (void*)pGet);
        return false;
    }
    intptr_t isTrueReal = KenshiLib::GetRealAddress(isTrueThunk);
    intptr_t getReal = KenshiLib::GetRealAddress((void*)pGet);
    if (!isTrueReal || !getReal) { Log("GetRealAddress returned 0, ws hook skipped", true); return false; }

    g_t = new Tables();
    InitializeSRWLock(&g_t->lock);

    // getFromData first: maps query -> GameData stringID (WorldEventStateQuery does not store it)
    if (KenshiLib::AddHook((void*)getReal, (void*)&getFromData_hook, (void**)&g_getFromDataOrig) != KenshiLib::SUCCESS || !g_getFromDataOrig)
    {
        Log("AddHook(getFromData) failed, ws hook skipped", true);
        g_getFromDataOrig = NULL;
        return false;
    }
    InterlockedExchange(&g_getHookInstalled, 1);
    if (KenshiLib::AddHook((void*)isTrueReal, (void*)&isTrue_hook, (void**)&g_isTrueOrig) != KenshiLib::SUCCESS || !g_isTrueOrig)
    {
        // getFromData hook stays (a pass-through that only records sids); overrides stay disabled
        Log("AddHook(isTrue) failed, overrides disabled", true);
        g_isTrueOrig = NULL;
        return false;
    }
    InterlockedExchange(&g_hookInstalled, 1);
    return true;
}


// exported by name from KenshiLib.dll (see tools\cpp\lib\KenshiLib.def); the _NV_ body lives at the same address as the virtual
static const char TIP_SYM_TAIL[] = "QEAAXAEAV?$vector@VStringPair@@V?$STLAllocator@VStringPair@@V?$CategorisedAllocPolicy@$0A@@Ogre@@@Ogre@@@std@@@Z";
static bool InstallTipHook(const char* cls, void* detour, void** orig)
{
    HMODULE kl = GetModuleHandleA("KenshiLib.dll");
    if (!kl) return false;
    std::string sym = std::string("?_NV_getTooltipData1@") + cls + "@@" + TIP_SYM_TAIL;
    void* p = (void*)GetProcAddress(kl, sym.c_str());
    if (!p || !InKenshiLib(p)) { Logf(true, "tooltip: %s::getTooltipData1 export not found, hook skipped", cls); return false; }
    intptr_t real = KenshiLib::GetRealAddress(p);
    if (!real) { Logf(true, "tooltip: GetRealAddress(%s) returned 0, hook skipped", cls); return false; }
    if (KenshiLib::AddHook((void*)real, detour, orig) != KenshiLib::SUCCESS || !*orig)
    {
        Logf(true, "tooltip: AddHook(%s) failed", cls);
        *orig = NULL;
        return false;
    }
    InterlockedIncrement(&g_ttHooks);
    return true;
}

static void InstallTooltipHooks()
{
    HMODULE exe = GetModuleHandleA(NULL);
    const IMAGE_DOS_HEADER* dos = (const IMAGE_DOS_HEADER*)exe;
    if (!exe || dos->e_magic != IMAGE_DOS_SIGNATURE) { Log("tooltip: cannot read exe image, compaction off", true); return; }
    const IMAGE_NT_HEADERS* nt = (const IMAGE_NT_HEADERS*)((const unsigned char*)exe + dos->e_lfanew);
    g_exeBase = (const unsigned char*)exe;
    g_exeSize = nt->OptionalHeader.SizeOfImage;
    if (!GetModuleHandleA("msvcr100.dll")) { Log("tooltip: msvcr100.dll not loaded in the process (CRT differs from the game), compaction off", true); return; }
    bool a = InstallTipHook("InventoryItemBase", (void*)&tip_base_hook, (void**)&g_tipOrigBase);
    bool b = InstallTipHook("Sword", (void*)&tip_sword_hook, (void**)&g_tipOrigSword);
    bool c = InstallTipHook("Crossbow", (void*)&tip_xbow_hook, (void**)&g_tipOrigXbow);
    Logf(false, "tooltip compaction hooks: InventoryItemBase=%d Sword=%d Crossbow=%d", a ? 1 : 0, b ? 1 : 0, c ? 1 : 0);
}

static void StartPluginImpl()
{
    Log("starting v" KMM_VERSION, false);

    std::string dir = ModuleDir();
    std::string js;
    if (dir.empty() || !ReadSmallFile(dir + "\\kmm_native.json", js))
    {
        Log("kmm_native.json not found next to the DLL, plugin disabled", true);
        return;
    }
    std::string en = JsonToken(js, "enabled");
    std::string ws = JsonToken(js, "ws_hook");
    std::string gv = JsonToken(js, "game_version");
    g_enabled = (en == "true");
    g_wsHook = (ws == "true");
    std::string ff = JsonToken(js, "faction_force");
    std::string us = JsonToken(js, "unique_set");
    bool wantForce = (ff != "false");     // default true
    g_ttWanted = (JsonToken(js, "tooltip_compact") != "false");   // default true
    g_uniqueSet = (us == "true");         // default false
    if (gv.empty()) gv = KMM_EXPECTED_GAME_VERSION;
    if (!g_enabled) { Log("enabled=false (or unreadable) in kmm_native.json, nothing hooked", false); return; }

    // game version gate: the KenshiLib RVAs we rely on are for this exact version
    try
    {
        KenshiLib::BinaryVersion v = KenshiLib::GetKenshiVersion();
        std::string ver = v.GetVersion();
        Logf(false, "game version reported by KenshiLib: %s (expected %s)", ver.c_str(), gv.c_str());
        if (v.GetPlatform() == KenshiLib::BinaryVersion::UNKNOWN || ver != gv)
        {
            Log("unknown game version, nothing hooked", true);
            return;
        }
    }
    catch (...) { Log("version check threw, nothing hooked", true); return; }

    // 2.4: "Salvage Parts" / "Butcher" context-menu entries (salvage.cpp). Independent of KenshiLua; rules are data.
    if (JsonToken(js, "salvage") != "false")
    {
        std::string rules = JsonToken(js, "salvage_rules");
        std::string off = JsonToken(js, "salvage_off");
        if (rules.empty()) rules = "C:/KenshiModMap/rules/salvage.json";
        if (off.empty()) off = "C:/KenshiModMap/state/salvage.off";
        Salvage_Install(rules.c_str(), off.c_str());
    }
    else Log("salvage=false in kmm_native.json, salvage menu not installed", false);

    // KenshiLua must be loaded with a compatible ABI, otherwise nobody could ever set an override
    if (!GetModuleHandleA("KenshiLua.dll"))
    {
        Log("KenshiLua.dll is not loaded, nothing hooked", true);
        return;
    }
    KenshiLua::Detail::GetApi();   // negotiates ABI and fills the status
    if (KenshiLua::Detail::GetLastStatus() == KENSHILUA_STATUS_UNSUPPORTED_VERSION)
    {
        Log("KenshiLua SDK ABI not supported, nothing hooked", true);
        return;
    }

    g_forceRead = wantForce;
    g_memory = (JsonToken(js, "native_memory") != "false");   // default true
    Logf(false, "native_memory (remember_lt/memory_lt) %s", g_memory ? "on" : "off");
    if (g_uniqueSet) Log("unique_set=true requested, but no verified unique-NPC state write exists in this version; ignored", true);

    if (g_wsHook)
    {
        if (InstallWsHook()) Log("WorldEventStateQuery::isTrue hook installed", false);
    }
    else Log("ws_hook=false, hook not installed", false);

    if (g_ttWanted) InstallTooltipHooks();
    else Log("tooltip_compact=false, tooltip hooks not installed", false);

    if (KenshiLua::IsAvailable())
    {
        std::string err;
        if (KenshiLua::RegisterModule("kmm_native", OpenModule, &err) == KenshiLua::STATUS_OK)
        {
            g_luaRegistered = true;
            Log("Lua module kmm_native registered", false);
        }
        else
            Logf(true, "RegisterModule failed: %s (Lua adapter falls back to package.loadlib)", err.c_str());
    }
    else
        Log("KenshiLua not initialized yet; Lua adapter will load the module via package.loadlib", false);
}

// RE_Kenshi looks this symbol up by its C++ mangled name ?startPlugin@@YAXXZ.
__declspec(dllexport) void startPlugin()
{
    try { StartPluginImpl(); }
    catch (...) { Log("exception during startPlugin, plugin inert", true); }
}

BOOL APIENTRY DllMain(HMODULE, DWORD, LPVOID) { return TRUE; }
