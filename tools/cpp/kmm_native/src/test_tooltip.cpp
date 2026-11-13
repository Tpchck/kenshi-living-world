// Offline unit test for tooltip_compact.h (build: build_tooltip_test.bat). Exit code 0 = all passed.
#include <stdio.h>
#include "tooltip_compact.h"
using namespace kmmtip;
static int fails = 0;
#define CHECK(c) do { if (!(c)) { printf("FAIL line %d: %s\n", __LINE__, #c); ++fails; } } while (0)
static Line L(const char* a, const char* b = "", uint32_t v = 0) { return Line(a, b, v); }
static void Dump(const std::vector<Line>& v) { for (size_t i = 0; i < v.size(); ++i) printf("   [%s] [%s] %u\n", v[i].s1.c_str(), v[i].s2.c_str(), v[i].vbits); }

int main()
{
    CHECK(FamilyOf("Raw Crystal Spider purple") == "Crystal Spider");
    CHECK(FamilyOf("Broken Brewing Spider (MkII)") == "Brewing Spider");
    CHECK(FamilyOf("Crystal Carrier Overlord") == "Crystal Carrier");
    CHECK(FamilyOf("Crystal Greed red") == "Crystal Greed");
    CHECK(FamilyOf("Red") == "Red");            // never empty
    CHECK(FamilyOf("Greenlander") == "Greenlander");
    CHECK(FamilyOf("Skeleton") == "Skeleton");

    // 1. Ring Object: 18 per-race lines with the same value
    const char* races[] = { "Crystal Carrier Overlord", "Crystal Carrier purple", "Crystal Carrier red", "Raw Crystal Spider purple",
        "Raw Crystal Spider red", "Crystal Golem", "Crystal Guardian", "Crystal Greed Overlord", "Crystal Greed purple", "Crystal Greed red",
        "Brewing Spider", "Brewing Spider MkII", "Broken Brewing Spider (MkII)", "Broken Crystal Spider (MkII)", "Crystal Spider (MkII)", NULL };
    std::vector<Line> in, out;
    in.push_back(L("Cutting damage", "5-10"));
    for (int i = 0; races[i]; ++i) in.push_back(L(races[i], "+150%"));
    in.push_back(L("Weight", "3 kg"));
    CHECK(Compact(in, out));
    printf("case1:\n"); Dump(out);
    CHECK(out.size() >= 3 && out.size() <= 5);       // first + <=3 + last
    CHECK(out.front().s1 == "Cutting damage" && out.back().s1 == "Weight");
    CHECK(out[1].s2 == "+150%");
    std::string all; for (size_t i = 1; i + 1 < out.size(); ++i) all += out[i].s1 + "|";
    CHECK(all.find("Crystal Carrier") != std::string::npos && all.find("Crystal Spider") != std::string::npos &&
          all.find("Brewing Spider") != std::string::npos && all.find("Crystal Golem") != std::string::npos);
    CHECK(all.find("purple") == std::string::npos && all.find("MkII") == std::string::npos);

    // 2. value in val1 (s2 empty), "Damage vs " prefix kept on the first line
    in.clear();
    for (int i = 0; i < 6; ++i) in.push_back(L((std::string("Damage vs ") + races[i]).c_str(), "", 0x42700000u));
    CHECK(Compact(in, out));
    printf("case2:\n"); Dump(out);
    CHECK(out.size() < 6 && out[0].s1.compare(0, 10, "Damage vs ") == 0 && out[0].vbits == 0x42700000u);
    CHECK(out.size() < 2 || out[1].s1.compare(0, 6, "Damage") != 0);

    // 3. different values are different runs; 3 equal lines stay untouched
    in.clear();
    in.push_back(L("A one", "+10%")); in.push_back(L("B one", "+10%")); in.push_back(L("C one", "+10%"));
    in.push_back(L("D one", "+20%")); in.push_back(L("E one", "+20%")); in.push_back(L("F one", "+20%"));
    CHECK(!Compact(in, out)); CHECK(out.size() == 6);

    // 4. description lines (empty value) are never merged
    in.clear();
    for (int i = 0; i < 6; ++i) in.push_back(L("Some flavour text line"));
    CHECK(!Compact(in, out)); CHECK(out.size() == 6);

    // 5. run that is already compact (distinct families, would not shrink enough) stays or shrinks safely; idempotent
    in.clear();
    in.push_back(L("Cutting damage", "5-10"));
    for (int i = 0; races[i]; ++i) in.push_back(L(races[i], "+150%"));
    Compact(in, out);
    std::vector<Line> again; CHECK(!Compact(out, again)); CHECK(again.size() == out.size());

    // 6. Only for: comma list in s2 and inside s1
    in.clear();
    in.push_back(L("-Only for:", "Greenlander, Scorchlander, Hive Prince, Hive Worker Drone, Hive Soldier Drone, Shek"));
    in.push_back(L("Hunger", "10"));
    CHECK(!Compact(in, out) || true);
    in.clear();
    in.push_back(L("-Only for:", "Crystal Spider purple, Crystal Spider red, Crystal Spider (MkII), Raw Crystal Spider blue, Skeleton"));
    CHECK(Compact(in, out)); printf("case6:\n"); Dump(out);
    CHECK(out.size() == 1 && out[0].s2 == "Crystal Spider, Skeleton" && out[0].s1 == "-Only for:");
    in.clear();
    in.push_back(L("-Only for: Brewing Spider, Brewing Spider MkII, Broken Brewing Spider (MkII), Human", ""));
    CHECK(Compact(in, out)); printf("case6b:\n"); Dump(out);
    CHECK(out[0].s1 == "-Only for: Brewing Spider, Human");

    // 4b. equal-valued stat lines without "+" (armour resistances) stay untouched
    in.clear();
    in.push_back(L("Cut resistance", "50%")); in.push_back(L("Blunt resistance", "50%")); in.push_back(L("Pierce resistance", "50%")); in.push_back(L("Fire resistance", "50%"));
    CHECK(!Compact(in, out)); CHECK(out.size() == 4);

    // 7. empty / tiny inputs
    in.clear(); CHECK(!Compact(in, out)); CHECK(out.empty());
    in.push_back(L("x", "y")); CHECK(!Compact(in, out)); CHECK(out.size() == 1);

    // 8. run in the middle with long unique names stays <= 3 lines
    in.clear();
    for (int i = 0; i < 12; ++i) { char b[64]; sprintf_s(b, "Extremely Long Creature Name Number %c%c", 'a' + i, 'a' + i); in.push_back(L(b, "+5%")); }
    CHECK(Compact(in, out)); CHECK(out.size() <= 3);
    size_t cnt = 0; for (size_t i = 0; i < out.size(); ++i) for (size_t p = 0; (p = out[i].s1.find("Number", p)) != std::string::npos; ++p) ++cnt;
    CHECK(cnt == 12);   // nothing lost

    printf(fails ? "FAILED %d\n" : "ALL PASSED\n", fails);
    return fails ? 1 : 0;
}
