// KMM_Native 2.4 — "Salvage Parts" (downed skeletons, RaceData::robot) and "Butcher" (downed animals, Character::isAnimal)
// in the native right-click context menu. Same techniques as the workshop plugin HarvestOrgans (proven in the owner's game,
// 1.0.65): hook ContextMenu::showContextMenu, append a PanelEmpty slot + Kenshi_Button1 to ContextMenuGUI::optionsList with
// our own int userData marker, order the native kill task with PlayerInterface::newPlayerTaskSelectedCharacters, hand out
// items with RootObjectFactory::createItem + Inventory::addItem. Loot tables are data (rules\salvage.json), not code.
//
// Double hook: KenshiLib::AddHook = MinHook "multihook" (m417z) with a unique hook id per call (Functions.cpp:84-99), so
// several plugins may hook the same target; in the owner's game KillCounter, HarvestOrgans, QueenBirth and both Hive
// plugins already share GameWorld::_NV_mainLoop_GPUSensitiveStuff (RE_Kenshi_log.txt). Each detour calls the original
// first, so HarvestOrgans' entry and ours stack under each other (each places itself under the last child).
//
// Credit: no melee-hit hook. The player character who received the order (PlayerInterface::selectedCharacter at the click)
// gets the loot if the target dies within window_sec of unpaused time after the order and the orderer is then alive,
// conscious, in the player faction and within credit_radius of the body.
#define _CRT_SECURE_NO_WARNINGS
#pragma warning(push, 0)
#pragma warning(disable: 4251 4275 4482 4800 4996)
#include <kenshi/Globals.h>
#include <kenshi/GameWorld.h>
#include <kenshi/Inventory.h>
#include <kenshi/Item.h>
#include <kenshi/GameData.h>
#include <kenshi/RootObject.h>
#include <kenshi/Character.h>
#include <kenshi/RootObjectFactory.h>
#include <kenshi/GameDataManager.h>
#include <kenshi/PlayerInterface.h>
#include <kenshi/RaceData.h>
#include <kenshi/Faction.h>
#include <mygui/MyGUI.h>
#include <mygui/MyGUI_Gui.h>
#include <mygui/MyGUI_Button.h>
#include <mygui/MyGUI_TextBox.h>
#include <mygui/MyGUI_Delegate.h>
#include <mygui/common/baselayout/BaseLayout.h>
#include <ogre/OgreVector3.h>
#include <core/Functions.h>
#pragma warning(pop)

#define WIN32_LEAN_AND_MEAN
#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <windows.h>
#include <stdlib.h>
#include <math.h>
#include <string.h>
#include <string>
#include <vector>

#include "salvage.h"

// kenshi/gui/ContextMenu.h cannot be included next to PlayerInterface.h (both define ContextMenu); same layout as there.
class ContextMenuGUI : public wraps::BaseLayout, public Ogre::GeneralAllocatedObject
{
public:
    ContextMenuGUI();
    virtual ~ContextMenuGUI();
    MyGUI::Widget* getMainWidget() const;
    bool getVisible() const;
    void setVisible(bool visible);
    void show(const lektor<int>& ordersList, const std::string& _name, bool offset);
    void optionSelected(MyGUI::Widget* _sender, int _left, int _top, MyGUI::MouseButton _id);
    hand contextMenuTarget;                       // 0xA8
    std::string name;                             // 0xC8
    MyGUI::TextBox* nameText;                     // 0xF0
    MyGUI::Widget* optionsList;                   // 0xF8
    MyGUI::types::TCoord<int> optionCoords;       // 0x100
    MyGUI::types::TCoord<int> buttonCoords;       // 0x110
    MyGUI::types::TCoord<int> valueCoords;        // 0x120
};

// layouts this file relies on, as annotated in the KenshiLib headers (1.0.65); a mismatch fails the build
#include <stddef.h>
typedef char chk_cm_options[(offsetof(ContextMenuGUI, optionsList) == 0xF8) ? 1 : -1];
typedef char chk_cm_optc[(offsetof(ContextMenuGUI, optionCoords) == 0x100) ? 1 : -1];
typedef char chk_cm_btnc[(offsetof(ContextMenuGUI, buttonCoords) == 0x110) ? 1 : -1];
typedef char chk_menu_gui[(offsetof(ContextMenu, menuGUI) == 0x48) ? 1 : -1];
typedef char chk_pi_menu[(offsetof(PlayerInterface, contextMenu) == 0x48) ? 1 : -1];
typedef char chk_pi_sel[(offsetof(PlayerInterface, selectedCharacter) == 0xF0) ? 1 : -1];
typedef char chk_gw_player[(offsetof(GameWorld, player) == 0x580) ? 1 : -1];
typedef char chk_gw_factory[(offsetof(GameWorld, theFactory) == 0x4A0) ? 1 : -1];
typedef char chk_gw_paused[(offsetof(GameWorld, paused) == 0x8B9) ? 1 : -1];
typedef char chk_gw_gamedata[(offsetof(GameWorld, gamedata) == 0x20) ? 1 : -1];
typedef char chk_ch_race[(offsetof(Character, myRace) == 0x2E0) ? 1 : -1];
typedef char chk_race_robot[(offsetof(RaceData, robot) == 0x7C) ? 1 : -1];
typedef char chk_race_data[(offsetof(RaceData, data) == 0x40) ? 1 : -1];
typedef char chk_gd_type[(offsetof(GameData, type) == 0x50) ? 1 : -1];
typedef char chk_gd_name[(offsetof(GameData, name) == 0x28) ? 1 : -1];

namespace
{
    enum { K_NONE = 0, K_ROBOT = 1, K_ANIMAL = 2 };
    const int MARK_BASE = 0x4B4D5300;             // "KMS" + kind; HarvestOrgans uses 0x800
    const char* const KIND_NAME[3] = { "none", "robot", "animal" };

    // ------------------------------------------------------------ minimal JSON (objects, arrays, strings, numbers, bools)
    struct JV
    {
        enum T { NUL, BOOL, NUM, STR, ARR, OBJ } t;
        double n;
        bool b;
        std::string s;
        std::vector<JV> a;            // ARR items / OBJ values
        std::vector<std::string> k;   // OBJ keys
        JV() : t(NUL), n(0), b(false) {}
        const JV* get(const char* key) const
        {
            if (t != OBJ) return NULL;
            for (size_t i = 0; i < k.size(); ++i) if (k[i] == key) return &a[i];
            return NULL;
        }
    };
    struct JP
    {
        const char* p; const char* e; std::string err;
        void ws() { while (p < e && (*p == ' ' || *p == '\t' || *p == '\r' || *p == '\n')) ++p; }
        bool fail(const char* m) { if (err.empty()) err = m; return false; }
        bool str(std::string& out)
        {
            if (p >= e || *p != '"') return fail("string expected");
            ++p;
            while (p < e && *p != '"')
            {
                char c = *p++;
                if (c != '\\') { out += c; continue; }
                if (p >= e) return fail("bad escape");
                char x = *p++;
                switch (x)
                {
                case 'n': out += '\n'; break;
                case 't': out += '\t'; break;
                case 'r': out += '\r'; break;
                case 'b': out += '\b'; break;
                case 'f': out += '\f'; break;
                case 'u':
                {
                    if (e - p < 4) return fail("bad \\u");
                    unsigned v = (unsigned)strtoul(std::string(p, 4).c_str(), NULL, 16);
                    p += 4;
                    if (v < 0x80) out += (char)v;
                    else if (v < 0x800) { out += (char)(0xC0 | (v >> 6)); out += (char)(0x80 | (v & 0x3F)); }
                    else { out += (char)(0xE0 | (v >> 12)); out += (char)(0x80 | ((v >> 6) & 0x3F)); out += (char)(0x80 | (v & 0x3F)); }
                    break;
                }
                default: out += x; break;
                }
            }
            if (p >= e) return fail("unterminated string");
            ++p;
            return true;
        }
        bool val(JV& v, int depth)
        {
            if (depth > 32) return fail("too deep");
            ws();
            if (p >= e) return fail("unexpected end");
            char c = *p;
            if (c == '{')
            {
                v.t = JV::OBJ; ++p; ws();
                if (p < e && *p == '}') { ++p; return true; }
                for (;;)
                {
                    ws();
                    std::string key;
                    if (!str(key)) return false;
                    ws();
                    if (p >= e || *p != ':') return fail("':' expected");
                    ++p;
                    v.k.push_back(key);
                    v.a.push_back(JV());
                    if (!val(v.a.back(), depth + 1)) return false;
                    ws();
                    if (p < e && *p == ',') { ++p; continue; }
                    if (p < e && *p == '}') { ++p; return true; }
                    return fail("',' or '}' expected");
                }
            }
            if (c == '[')
            {
                v.t = JV::ARR; ++p; ws();
                if (p < e && *p == ']') { ++p; return true; }
                for (;;)
                {
                    v.a.push_back(JV());
                    if (!val(v.a.back(), depth + 1)) return false;
                    ws();
                    if (p < e && *p == ',') { ++p; continue; }
                    if (p < e && *p == ']') { ++p; return true; }
                    return fail("',' or ']' expected");
                }
            }
            if (c == '"') { v.t = JV::STR; return str(v.s); }
            if (e - p >= 4 && strncmp(p, "true", 4) == 0) { v.t = JV::BOOL; v.b = true; p += 4; return true; }
            if (e - p >= 5 && strncmp(p, "false", 5) == 0) { v.t = JV::BOOL; v.b = false; p += 5; return true; }
            if (e - p >= 4 && strncmp(p, "null", 4) == 0) { v.t = JV::NUL; p += 4; return true; }
            const char* q = p;
            while (q < e && (strchr("+-.eE", *q) || (*q >= '0' && *q <= '9'))) ++q;
            if (q == p) return fail("unexpected character");
            v.t = JV::NUM;
            v.n = strtod(std::string(p, q).c_str(), NULL);
            p = q;
            return true;
        }
    };

    double Num(const JV* v, double def, double lo, double hi)
    {
        if (!v || v->t != JV::NUM) return def;
        double x = v->n;
        return x < lo ? lo : (x > hi ? hi : x);
    }
    std::string Lower(const std::string& s)
    {
        std::string r(s);
        for (size_t i = 0; i < r.size(); ++i) if (r[i] >= 'A' && r[i] <= 'Z') r[i] = (char)(r[i] - 'A' + 'a');
        return r;
    }

    // ------------------------------------------------------------ rules
    struct Entry { std::string sid; double weight; int mn, mx; GameData* gd; };
    struct Table { std::string match; std::vector<std::string> alts; int rolls; std::vector<Entry> items; };
    struct Section { bool on; int task; std::string taskName; std::string caption; Table def; std::vector<Table> races; };

    struct Pending
    {
        hand target, orderer;
        int kind, table;            // table: -1 default, else index into races
        double elapsed;             // unpaused seconds since the order
    };

    struct State
    {
        Section sec[3];                 // [K_ROBOT], [K_ANIMAL]
        double windowSec, radius;
        bool cfgOk, resolved, off;
        std::string offPath, rulesPath;
        hand menuTarget;
        int menuKind;
        hand menuOrderer;
        std::vector<Pending> pend;
        ULONGLONG lastMs;
        unsigned long long rng;
        State() : windowSec(60), radius(300), cfgOk(false), resolved(false), off(false), menuKind(0), lastMs(0), rng(88172645463325252ULL) {}
    };
    State* g_s = NULL;

    unsigned Rand32()
    {
        unsigned long long x = g_s->rng;   // xorshift64: our own stream, the game's rand() is untouched
        x ^= x << 13; x ^= x >> 7; x ^= x << 17;
        g_s->rng = x;
        return (unsigned)(x >> 32);
    }

    struct TaskName { const char* n; int v; };
    const TaskName TASKS[] = {
        { "KILL_CAGE_OCCUPANT", (int)KILL_CAGE_OCCUPANT },
        { "MELEE_ATTACK_ANIMAL", (int)MELEE_ATTACK_ANIMAL },
        { "MELEE_ATTACK", (int)MELEE_ATTACK },
        { "FOCUSED_MELEE_ATTACK", (int)FOCUSED_MELEE_ATTACK },
        { "UNPROVOKED_FOCUSED_MELEE_ATTACK", (int)UNPROVOKED_FOCUSED_MELEE_ATTACK },
    };

    bool ParseItems(const JV* arr, std::vector<Entry>& out, std::string& why)
    {
        if (!arr || arr->t != JV::ARR) { why = "items must be an array"; return false; }
        for (size_t i = 0; i < arr->a.size(); ++i)
        {
            const JV& it = arr->a[i];
            const JV* sid = it.get("sid");
            if (it.t != JV::OBJ || !sid || sid->t != JV::STR || sid->s.empty()) { why = "item without sid"; return false; }
            Entry en;
            en.sid = sid->s;
            en.weight = Num(it.get("weight"), 1, 0, 1e6);
            en.mn = (int)Num(it.get("min"), 1, 1, 50);
            en.mx = (int)Num(it.get("max"), en.mn, en.mn, 50);
            en.gd = NULL;
            if (en.weight > 0) out.push_back(en);
        }
        return true;
    }

    bool ParseTable(const JV& o, Table& t, const Table* fallback, std::string& why)
    {
        t.rolls = (int)Num(o.get("rolls"), fallback ? fallback->rolls : 1, 1, 10);
        const JV* items = o.get("items");
        if (items) { if (!ParseItems(items, t.items, why)) return false; }
        else if (fallback) t.items = fallback->items;
        if (t.items.empty()) { why = "empty item list"; return false; }
        return true;
    }

    bool ParseSection(const JV* s, Section& sec, const char* defCaption, std::string& why)
    {
        sec.on = false;
        if (!s || s->t != JV::OBJ) { why = "section missing"; return false; }
        const JV* en = s->get("enabled");
        if (en && en->t == JV::BOOL && !en->b) { why = "enabled=false"; return true; }
        const JV* cap = s->get("caption");
        sec.caption = (cap && cap->t == JV::STR && !cap->s.empty()) ? cap->s : defCaption;
        const JV* tk = s->get("task");
        sec.taskName = (tk && tk->t == JV::STR) ? tk->s : "KILL_CAGE_OCCUPANT";
        sec.task = -1;
        for (size_t i = 0; i < sizeof(TASKS) / sizeof(TASKS[0]); ++i) if (sec.taskName == TASKS[i].n) sec.task = TASKS[i].v;
        if (sec.task < 0) { KmmLog(true, "salvage: unknown task '%s', using KILL_CAGE_OCCUPANT", sec.taskName.c_str()); sec.task = (int)KILL_CAGE_OCCUPANT; sec.taskName = "KILL_CAGE_OCCUPANT"; }
        if (!ParseTable(*s, sec.def, NULL, why)) return false;
        const JV* races = s->get("races");
        if (races && races->t == JV::ARR)
        {
            for (size_t i = 0; i < races->a.size(); ++i)
            {
                const JV& r = races->a[i];
                const JV* m = r.get("match");
                if (r.t != JV::OBJ || !m || m->t != JV::STR || m->s.empty()) { why = "race rule without match"; return false; }
                Table t;
                t.match = m->s;
                std::string ml = Lower(m->s), cur;
                for (size_t j = 0; j <= ml.size(); ++j)
                {
                    if (j == ml.size() || ml[j] == '|') { if (!cur.empty()) t.alts.push_back(cur); cur.clear(); }
                    else if (ml[j] != ' ' || !cur.empty()) cur += ml[j];
                }
                while (!t.alts.empty() && !t.alts.back().empty() && t.alts.back()[t.alts.back().size() - 1] == ' ') t.alts.back().erase(t.alts.back().size() - 1);
                if (!ParseTable(r, t, &sec.def, why)) { why = "race '" + m->s + "': " + why; return false; }
                sec.races.push_back(t);
            }
        }
        sec.on = true;
        return true;
    }

    bool LoadRules(const std::string& path, std::string& why)
    {
        FILE* f = fopen(path.c_str(), "rb");
        if (!f) { why = "file not readable"; return false; }
        std::string js;
        char buf[4096];
        size_t n;
        while ((n = fread(buf, 1, sizeof(buf), f)) > 0 && js.size() < (1u << 20)) js.append(buf, n);
        fclose(f);
        if (js.size() >= 3 && (unsigned char)js[0] == 0xEF && (unsigned char)js[1] == 0xBB && (unsigned char)js[2] == 0xBF) js.erase(0, 3);
        JV root;
        JP jp;
        jp.p = js.data(); jp.e = js.data() + js.size();
        if (!jp.val(root, 0)) { why = "json: " + jp.err; return false; }
        if (root.t != JV::OBJ) { why = "json root is not an object"; return false; }
        g_s->windowSec = Num(root.get("window_sec"), 60, 5, 600);
        g_s->radius = Num(root.get("credit_radius"), 300, 10, 100000);
        std::string w1, w2;
        bool a = ParseSection(root.get("robot"), g_s->sec[K_ROBOT], "Salvage Parts", w1);
        bool b = ParseSection(root.get("animal"), g_s->sec[K_ANIMAL], "Butcher", w2);
        if (!a) { g_s->sec[K_ROBOT].on = false; KmmLog(true, "salvage: robot section invalid (%s), Salvage Parts off", w1.c_str()); }
        if (!b) { g_s->sec[K_ANIMAL].on = false; KmmLog(true, "salvage: animal section invalid (%s), Butcher off", w2.c_str()); }
        if (!g_s->sec[K_ROBOT].on && !g_s->sec[K_ANIMAL].on) { why = "no usable section"; return false; }
        return true;
    }

    // ------------------------------------------------------------ SEH-guarded engine reads (no C++ objects with destructors here)
    GameData* ItemDataSeh(const std::string* sid)
    {
        __try
        {
            if (!ou) return NULL;
            GameData* d = ou->gamedata.getData(*sid);
            return (d && d->type == ITEM) ? d : NULL;
        }
        __except (EXCEPTION_EXECUTE_HANDLER) { return NULL; }
    }
    Faction* PlayerFactionSeh()
    {
        __try { return (ou && ou->player) ? ou->player->getFaction() : NULL; }
        __except (EXCEPTION_EXECUTE_HANDLER) { return NULL; }
    }
    Character* CharOfSeh(RootObject* what)
    {
        __try { hand h(what); return h.getCharacter(); }
        __except (EXCEPTION_EXECUTE_HANDLER) { return NULL; }
    }
    Character* HandCharSeh(const hand* h)
    {
        __try { return h->getCharacter(); }
        __except (EXCEPTION_EXECUTE_HANDLER) { return NULL; }
    }
    // downed (KO, not dead), not ours: K_ROBOT for robot races (robot spiders included), K_ANIMAL for other animals; -1 fault
    int ClassifySeh(Character* c, Faction* pf)
    {
        __try
        {
            if (!c || c->isDead() || !c->isUnconcious()) return K_NONE;
            if (pf && c->getFaction() == pf) return K_NONE;   // never offer a kill order on our own squad or pack animals
            RaceData* r = c->myRace;
            if (r && r->robot) return K_ROBOT;
            if (c->isAnimal()) return K_ANIMAL;
            return K_NONE;
        }
        __except (EXCEPTION_EXECUTE_HANDLER) { return -1; }
    }
    const std::string* RaceNameSeh(Character* c)
    {
        __try { return (c && c->myRace && c->myRace->data) ? &c->myRace->data->name : NULL; }
        __except (EXCEPTION_EXECUTE_HANDLER) { return NULL; }
    }
    Character* SelectedSeh(Faction* pf)
    {
        __try
        {
            if (!ou || !ou->player || !pf) return NULL;
            Character* s = ou->player->selectedCharacter.getCharacter();
            if (!s || s->isDead() || s->isUnconcious() || s->getFaction() != pf) return NULL;
            return s;
        }
        __except (EXCEPTION_EXECUTE_HANDLER) { return NULL; }
    }
    bool OrderSeh(int task, Character* target)
    {
        __try
        {
            hand h(target);
            ou->player->newPlayerTaskSelectedCharacters((TaskType)task, h, NULL, Ogre::Vector3::ZERO, false);
            return true;
        }
        __except (EXCEPTION_EXECUTE_HANDLER) { return false; }
    }
    bool PausedSeh()
    {
        __try { return ou && ou->paused; }
        __except (EXCEPTION_EXECUTE_HANDLER) { return false; }
    }
    int DeadSeh(Character* c)   // 1 dead, 0 alive, -1 fault
    {
        __try { return c->isDead() ? 1 : 0; }
        __except (EXCEPTION_EXECUTE_HANDLER) { return -1; }
    }
    // 0 ok; 1 orderer gone; 2 orderer dead/down; 3 not player faction; 4 too far; -1 fault
    int CreditSeh(Character* who, Character* body, Faction* pf, double r2, float* dist2)
    {
        __try
        {
            if (!who) return 1;
            if (who->isDead() || who->isUnconcious()) return 2;
            if (!pf || who->getFaction() != pf) return 3;
            Ogre::Vector3 a = who->getPosition();
            Ogre::Vector3 b = body->getPosition();
            *dist2 = a.squaredDistance(b);
            return (*dist2 > r2) ? 4 : 0;
        }
        __except (EXCEPTION_EXECUTE_HANDLER) { return -1; }
    }
    bool GiveOneSeh(Character* who, GameData* d)
    {
        __try
        {
            if (!ou || !ou->theFactory) return false;
            Inventory* inv = who->getInventory();
            if (!inv) return false;
            Item* it = ou->theFactory->createItem(d, hand(), NULL, NULL, 0, NULL);
            if (!it) return false;
            inv->addItem(it, 1, true, false);   // dropOnFail: a full inventory drops the part at the orderer's feet
            return true;
        }
        __except (EXCEPTION_EXECUTE_HANDLER) { return false; }
    }

    // ------------------------------------------------------------ logic
    bool OffSwitch()
    {
        bool off = GetFileAttributesA(g_s->offPath.c_str()) != INVALID_FILE_ATTRIBUTES;
        if (off != g_s->off)
        {
            g_s->off = off;
            KmmLog(false, off ? "salvage: off (%s present)" : "salvage: on (%s removed)", g_s->offPath.c_str());
        }
        return off;
    }

    void ResolveOnce()
    {
        if (g_s->resolved) return;
        g_s->resolved = true;
        int ok = 0, all = 0;
        for (int k = K_ROBOT; k <= K_ANIMAL; ++k)
        {
            Section& s = g_s->sec[k];
            if (!s.on) continue;
            std::vector<Table*> tabs(1, &s.def);
            for (size_t i = 0; i < s.races.size(); ++i) tabs.push_back(&s.races[i]);
            for (size_t t = 0; t < tabs.size(); ++t)
            {
                std::vector<Entry>& v = tabs[t]->items;
                for (size_t i = 0; i < v.size();)
                {
                    ++all;
                    v[i].gd = ItemDataSeh(&v[i].sid);
                    if (v[i].gd) { ++ok; ++i; continue; }
                    KmmLog(true, "salvage: %s item %s is not loaded ITEM data, entry skipped", KIND_NAME[k], v[i].sid.c_str());
                    v.erase(v.begin() + i);
                }
            }
            if (s.def.items.empty()) { s.on = false; KmmLog(true, "salvage: %s default table empty after sid check, menu item off", KIND_NAME[k]); }
        }
        KmmLog(false, "salvage: cfg loaded %d/%d items (robot %s, animal %s, window %.0fs, radius %.0f)", ok, all,
               g_s->sec[K_ROBOT].on ? "on" : "off", g_s->sec[K_ANIMAL].on ? "on" : "off", g_s->windowSec, g_s->radius);
    }

    int PickTable(const Section& s, const std::string& raceLower)
    {
        for (size_t i = 0; i < s.races.size(); ++i)
            for (size_t j = 0; j < s.races[i].alts.size(); ++j)
                if (raceLower.find(s.races[i].alts[j]) != std::string::npos) return (int)i;
        return -1;
    }

    std::string RaceName(Character* c)
    {
        const std::string* p = RaceNameSeh(c);
        try { return p ? *p : std::string("?"); }
        catch (...) { return std::string("?"); }
    }

    void OnOptionClick(MyGUI::Widget* sender, int, int, MyGUI::MouseButton);

    bool HasMarker(MyGUI::Widget* list)
    {
        for (size_t i = 0; i < list->getChildCount(); ++i)
        {
            MyGUI::Widget* slot = list->getChildAt(i);
            if (!slot) continue;
            for (size_t j = 0; j < slot->getChildCount(); ++j)
            {
                int* m = slot->getChildAt(j)->getUserData<int>(false);
                if (m && (*m & ~0xFF) == MARK_BASE) return true;
            }
        }
        return false;
    }

    bool AddOption(ContextMenuGUI* gui, int kind)
    {
        if (!gui) return false;
        MyGUI::Widget* list = gui->optionsList;
        MyGUI::Widget* main = gui->getMainWidget();
        if (!list || !main || HasMarker(list)) return false;
        int w = gui->optionCoords.width > 0 ? gui->optionCoords.width : list->getWidth();
        int h = gui->optionCoords.height;
        if (h < 5 || h > 80) h = 26;
        int y = 0;
        size_t n = list->getChildCount();
        if (n > 0)
        {
            MyGUI::Widget* last = list->getChildAt(n - 1);
            if (last) y = last->getTop() + last->getHeight() + 2;
        }
        MyGUI::Widget* slot = list->createWidget<MyGUI::Widget>("PanelEmpty", gui->optionCoords.left, y, w, h, MyGUI::Align::Default, "");
        if (!slot) return false;
        MyGUI::Button* btn = slot->createWidget<MyGUI::Button>("Kenshi_Button1", gui->buttonCoords.left, gui->buttonCoords.top,
                                                               gui->buttonCoords.width, gui->buttonCoords.height, MyGUI::Align::Default, "");
        if (!btn) return false;
        btn->setCaption(g_s->sec[kind].caption);
        btn->setTextAlign(MyGUI::Align::Center);
        btn->setUserData(MARK_BASE + kind);
        btn->eventMouseButtonReleased += MyGUI::newDelegate(OnOptionClick);   // fresh button: += is the non-deprecated form of =
        btn->setEnabled(true);
        int grow = list->getAbsoluteRect().top + y + h - main->getAbsoluteRect().bottom + 4;
        if (grow > 0) main->setSize(main->getWidth(), main->getHeight() + grow);
        return true;
    }

    void OnMenu(ContextMenu* self, RootObject* what)
    {
        g_s->menuTarget.setNull();
        g_s->menuKind = K_NONE;
        if (OffSwitch()) return;
        Character* tgt = CharOfSeh(what);
        if (!tgt) return;
        Faction* pf = PlayerFactionSeh();
        int kind = ClassifySeh(tgt, pf);
        if (kind <= K_NONE) return;
        ResolveOnce();
        if (!g_s->sec[kind].on) return;
        Character* sel = SelectedSeh(pf);
        if (!sel) return;
        if (!AddOption(self->menuGUI, kind)) return;
        g_s->menuTarget = hand(tgt);
        g_s->menuOrderer = hand(sel);
        g_s->menuKind = kind;
        KmmLog(false, "salvage: menu %s (race %s)", KIND_NAME[kind], RaceName(tgt).c_str());
    }

    void StartOrder(int kind)
    {
        if (kind != g_s->menuKind || kind <= K_NONE) return;
        Character* tgt = HandCharSeh(&g_s->menuTarget);
        Faction* pf = PlayerFactionSeh();
        if (!tgt || ClassifySeh(tgt, pf) != kind) { KmmLog(false, "salvage: no credit (target no longer downed at click)"); return; }
        Character* sel = SelectedSeh(pf);
        if (!sel) { KmmLog(false, "salvage: no credit (no conscious selected player character at click)"); return; }
        const Section& s = g_s->sec[kind];
        std::string race = RaceName(tgt);
        int table = PickTable(s, Lower(race));
        if (!OrderSeh(s.task, tgt)) { KmmLog(true, "salvage: newPlayerTaskSelectedCharacters faulted, no order"); return; }
        Pending p;
        p.target = hand(tgt);
        p.orderer = hand(sel);
        p.kind = kind;
        p.table = table;
        p.elapsed = 0;
        for (size_t i = 0; i < g_s->pend.size(); ++i)
            if (g_s->pend[i].target == p.target) { g_s->pend.erase(g_s->pend.begin() + i); break; }
        if (g_s->pend.size() >= 16) g_s->pend.erase(g_s->pend.begin());
        g_s->pend.push_back(p);
        KmmLog(false, "salvage: ordered %s %s on race %s (table %s)", KIND_NAME[kind], s.taskName.c_str(), race.c_str(),
               table < 0 ? "default" : s.races[table].match.c_str());
    }

    void OnOptionClick(MyGUI::Widget* sender, int, int, MyGUI::MouseButton)
    {
        try
        {
            int* m = sender ? sender->getUserData<int>(false) : NULL;
            if (m && (*m & ~0xFF) == MARK_BASE) StartOrder(*m & 0xFF);
        }
        catch (...) { KmmLog(true, "salvage: exception in menu click"); }
        if (ou && ou->player) ou->player->contextMenu.showContextMenu(false, NULL);   // close like a normal option
    }

    void Award(const Pending& p, Character* who)
    {
        const Section& s = g_s->sec[p.kind];
        const Table& t = (p.table >= 0 && p.table < (int)s.races.size() && !s.races[p.table].items.empty()) ? s.races[p.table] : s.def;
        if (t.items.empty()) { KmmLog(false, "salvage: no credit (empty table)"); return; }
        double total = 0;
        for (size_t i = 0; i < t.items.size(); ++i) total += t.items[i].weight;
        std::vector<int> qty(t.items.size(), 0);
        for (int r = 0; r < t.rolls; ++r)
        {
            double x = (Rand32() / 4294967296.0) * total;
            size_t i = 0;
            for (; i + 1 < t.items.size(); ++i) { if (x < t.items[i].weight) break; x -= t.items[i].weight; }
            const Entry& e = t.items[i];
            qty[i] += e.mn + (int)(Rand32() % (unsigned)(e.mx - e.mn + 1));
        }
        for (size_t i = 0; i < t.items.size(); ++i)
        {
            if (qty[i] <= 0) continue;
            int given = 0;
            for (int k = 0; k < qty[i]; ++k) if (GiveOneSeh(who, t.items[i].gd)) ++given;
            if (given > 0) KmmLog(false, "salvage: awarded %s x%d (%s)", t.items[i].sid.c_str(), given, KIND_NAME[p.kind]);
            if (given < qty[i]) KmmLog(true, "salvage: createItem/addItem refused %d of %d %s", qty[i] - given, qty[i], t.items[i].sid.c_str());
        }
    }

    void Tick()
    {
        ULONGLONG now = GetTickCount64();
        double dt = g_s->lastMs ? (double)(now - g_s->lastMs) / 1000.0 : 0.0;
        if (dt > 1.0) dt = 1.0;                 // loading screens and hitches do not eat the window
        g_s->lastMs = now;
        if (PausedSeh()) dt = 0;
        Faction* pf = NULL;
        bool pfRead = false;
        for (size_t i = 0; i < g_s->pend.size();)
        {
            Pending& p = g_s->pend[i];
            p.elapsed += dt;
            Character* body = HandCharSeh(&p.target);
            const char* why = NULL;
            char buf[96];
            int dead = body ? DeadSeh(body) : -1;
            if (dead < 0) why = "target gone";
            else if (dead == 1)
            {
                if (!pfRead) { pf = PlayerFactionSeh(); pfRead = true; }
                float d2 = 0;
                Character* who = HandCharSeh(&p.orderer);
                int c = CreditSeh(who, body, pf, g_s->radius * g_s->radius, &d2);
                if (c == 0) Award(p, who);
                else if (c == 1) why = "orderer gone";
                else if (c == 2) why = "orderer dead or down";
                else if (c == 3) why = "orderer not in player faction";
                else if (c == 4) { _snprintf_s(buf, sizeof(buf), _TRUNCATE, "orderer too far: %.0f > %.0f", sqrt((double)d2), g_s->radius); why = buf; }
                else why = "fault";
            }
            else if (p.elapsed > g_s->windowSec) why = "target still alive after window";
            else { ++i; continue; }
            if (why) KmmLog(false, "salvage: no credit (%s, %s)", why, KIND_NAME[p.kind]);
            g_s->pend.erase(g_s->pend.begin() + i);
        }
        if (g_s->pend.empty()) g_s->lastMs = 0;
    }

    // ------------------------------------------------------------ hooks
    void (*g_showOrig)(ContextMenu*, bool, RootObject*) = NULL;
    void (*g_loopOrig)(GameWorld*, float) = NULL;

    void show_hook(ContextMenu* self, bool on, RootObject* what)
    {
        if (g_showOrig) g_showOrig(self, on, what);
        if (!g_s || !g_s->cfgOk) return;
        try
        {
            if (on && what && self) OnMenu(self, what);
        }
        catch (...) { KmmLog(true, "salvage: exception while building the menu entry"); }
    }

    void loop_hook(GameWorld* gw, float t)
    {
        if (g_loopOrig) g_loopOrig(gw, t);
        if (!g_s || g_s->pend.empty()) return;
        try { Tick(); }
        catch (...) { g_s->pend.clear(); KmmLog(true, "salvage: exception in tick, pending orders dropped"); }
    }

    // hook targets are taken by mangled name from KenshiLib.dll (its stubs), like the tooltip hooks: GetRealAddress only
    // accepts addresses inside KenshiLib.dll, and these classes are not dllimport in the headers
    bool Hook(const char* sym, void* detour, void** orig)
    {
        HMODULE kl = GetModuleHandleA("KenshiLib.dll");
        void* p = kl ? (void*)GetProcAddress(kl, sym) : NULL;
        if (!p) { KmmLog(true, "salvage: export %s not found", sym); return false; }
        intptr_t real = KenshiLib::GetRealAddress(p);
        if (!real) { KmmLog(true, "salvage: GetRealAddress(%s) returned 0", sym); return false; }
        if (KenshiLib::AddHook((void*)real, detour, orig) != KenshiLib::SUCCESS || !*orig) { *orig = NULL; KmmLog(true, "salvage: AddHook(%s) failed", sym); return false; }
        return true;
    }
}

void Salvage_Install(const char* rulesPath, const char* offPath)
{
    try
    {
        g_s = new State();
        g_s->rulesPath = rulesPath ? rulesPath : "";
        g_s->offPath = offPath ? offPath : "";
        g_s->rng ^= (unsigned long long)GetTickCount64() * 2654435761ULL;
        std::string why;
        if (!LoadRules(g_s->rulesPath, why))
        {
            KmmLog(true, "salvage: rules %s missing or invalid (%s), menu items disabled", g_s->rulesPath.c_str(), why.c_str());
            return;
        }
        g_s->cfgOk = true;
        g_s->off = GetFileAttributesA(g_s->offPath.c_str()) != INVALID_FILE_ATTRIBUTES;
        // the loop hook goes first: a menu entry without the tick would order kills that never pay out
        if (!Hook("?_NV_mainLoop_GPUSensitiveStuff@GameWorld@@QEAAXM@Z", (void*)&loop_hook, (void**)&g_loopOrig)) { g_s->cfgOk = false; return; }
        if (!Hook("?showContextMenu@ContextMenu@@QEAAX_NPEAVRootObject@@@Z", (void*)&show_hook, (void**)&g_showOrig)) { g_s->cfgOk = false; return; }
        KmmLog(false, "salvage: hooks installed (showContextMenu, mainLoop), rules parsed: robot %s, animal %s%s",
               g_s->sec[K_ROBOT].on ? "on" : "off", g_s->sec[K_ANIMAL].on ? "on" : "off", g_s->off ? "; off-switch present" : "");
    }
    catch (...)
    {
        if (g_s) g_s->cfgOk = false;
        KmmLog(true, "salvage: exception during install, menu items disabled");
    }
}
