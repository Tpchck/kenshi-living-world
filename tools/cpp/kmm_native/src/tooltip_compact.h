// Pure logic of the tooltip compaction (no Windows / game dependencies, compiled both into KMM_Native and into test_tooltip.exe).
// Input: tooltip lines (s1, s2, val1 bit pattern) as built by the game; output: the same list with long runs of per-race
// lines ("Damage vs <race>  +150%") merged into at most 3 lines of race families, and "Only for: a, b, c" lists
// de-duplicated by family. Nothing here touches memory it does not own.
#pragma once
#include <string>
#include <vector>
#include <stdint.h>
#include <string.h>

namespace kmmtip
{
    struct Line
    {
        std::string s1, s2;
        uint32_t vbits;       // bit pattern of StringPair::val1 (compared bitwise, no float semantics needed)
        Line() : vbits(0) {}
        Line(const std::string& a, const std::string& b, uint32_t v) : s1(a), s2(b), vbits(v) {}
    };

    enum { RUN_MIN = 4, MAX_OUT_LINES = 3, LINE_TARGET = 46, NAME_MAX = 48 };

    inline char Lc(char c) { return (c >= 'A' && c <= 'Z') ? (char)(c - 'A' + 'a') : c; }
    inline std::string Lower(const std::string& s) { std::string r(s); for (size_t i = 0; i < r.size(); ++i) r[i] = Lc(r[i]); return r; }
    inline bool Contains(const std::string& s, const char* what) { return Lower(s).find(what) != std::string::npos; }

    inline std::string Trim(const std::string& s)
    {
        size_t a = 0, b = s.size();
        while (a < b && (s[a] == ' ' || s[a] == '\t')) ++a;
        while (b > a && (s[b - 1] == ' ' || s[b - 1] == '\t')) --b;
        return s.substr(a, b - a);
    }

    // words that denote a variant (colour / tier / state), not the creature family
    inline bool IsVariantWord(const std::string& w)
    {
        static const char* const k[] = { "purple", "red", "blue", "green", "yellow", "orange", "black", "white", "pink", "grey", "gray",
                                         "brown", "cyan", "golden", "silver", "overlord", "mkii", "mk2", "mkiii", "mk3", "mk",
                                         "broken", "raw", "dyed", NULL };
        std::string l = Lower(w);
        size_t a = 0, b = l.size();
        while (a < b && (l[a] == '(' || l[a] == '[')) ++a;
        while (b > a && (l[b - 1] == ')' || l[b - 1] == ']' || l[b - 1] == ',')) --b;
        l = l.substr(a, b - a);
        for (int i = 0; k[i]; ++i) if (l == k[i]) return true;
        return false;
    }

    // "Raw Crystal Spider purple" -> "Crystal Spider"; "Broken Brewing Spider (MkII)" -> "Brewing Spider".
    // Never returns an empty string (falls back to the original name).
    inline std::string FamilyOf(const std::string& name)
    {
        std::string out;
        size_t i = 0, n = name.size();
        while (i < n)
        {
            while (i < n && name[i] == ' ') ++i;
            size_t j = i;
            while (j < n && name[j] != ' ') ++j;
            if (j > i)
            {
                std::string w = name.substr(i, j - i);
                if (!IsVariantWord(w)) { if (!out.empty()) out += ' '; out += w; }
            }
            i = j;
        }
        return out.empty() ? Trim(name) : out;
    }

    inline void AddUnique(std::vector<std::string>& v, const std::string& s)
    {
        for (size_t i = 0; i < v.size(); ++i) if (v[i] == s) return;
        v.push_back(s);
    }

    // greedy fill into at most MAX_OUT_LINES chunks joined by ", "
    inline void Chunk(const std::vector<std::string>& fam, size_t firstLineReserve, std::vector<std::string>& chunks)
    {
        chunks.clear();
        std::string cur;
        for (size_t i = 0; i < fam.size(); ++i)
        {
            size_t reserve = chunks.empty() ? firstLineReserve : 0;
            if (!cur.empty() && chunks.size() + 1 < (size_t)MAX_OUT_LINES && reserve + cur.size() + 2 + fam[i].size() > (size_t)LINE_TARGET)
            {
                chunks.push_back(cur);
                cur.clear();
            }
            if (!cur.empty()) cur += ", ";
            cur += fam[i];
        }
        if (!cur.empty()) chunks.push_back(cur);
    }

    // prefix shared by all names that mentions "vs" (e.g. "Damage vs "); empty if none
    inline std::string CommonVsPrefix(const std::vector<Line>& in, size_t a, size_t b)
    {
        const std::string& f = in[a].s1;
        size_t n = f.size();
        for (size_t i = a + 1; i < b; ++i)
        {
            const std::string& s = in[i].s1;
            size_t k = 0;
            while (k < n && k < s.size() && f[k] == s[k]) ++k;
            n = k;
        }
        while (n > 0 && f[n - 1] != ' ') --n;      // whole words only, keep the trailing space
        if (n == 0) return std::string();
        std::string p = f.substr(0, n);
        std::string l = " " + Lower(p);
        if (l.find(" vs ") == std::string::npos && l.find(" vs. ") == std::string::npos) return std::string();
        for (size_t i = a; i < b; ++i) if (in[i].s1.size() <= n) return std::string();   // nothing left after the prefix
        return p;
    }

    inline bool SameKey(const Line& x, const Line& y) { return x.s2 == y.s2 && x.vbits == y.vbits; }

    // a run candidate: short name, and a value somewhere (s2 text or non-zero val1), so plain description lines are never merged
    inline bool RunCandidate(const Line& l)
    {
        if (l.s1.empty() || l.s1.size() > (size_t)NAME_MAX) return false;
        if (l.s1.find(':') != std::string::npos) return false;
        for (size_t i = 0; i < l.s1.size(); ++i) if (l.s1[i] >= '0' && l.s1[i] <= '9') return false;   // stat lines, not creature names
        return !l.s2.empty() || l.vbits != 0;
    }

    // "Only for: a, b, c": rewrites the list part in place. Returns true if changed.
    inline bool CompactOnlyFor(Line& l)
    {
        std::string* label = NULL;
        std::string* listField = NULL;
        std::string head;                     // text kept before the list inside the same field
        if (Contains(l.s1, "only for")) label = &l.s1; else if (Contains(l.s2, "only for")) label = &l.s2; else return false;
        std::string* other = (label == &l.s1) ? &l.s2 : &l.s1;
        size_t colon = label->find(':');
        size_t offs = 0;
        if (colon != std::string::npos && label->find(',', colon) != std::string::npos) { listField = label; offs = colon + 1; head = label->substr(0, offs); }
        else if (other->find(',') != std::string::npos) listField = other;
        else return false;
        std::string list = listField->substr(offs);
        std::vector<std::string> toks;
        size_t i = 0;
        while (i <= list.size())
        {
            size_t j = list.find(',', i);
            if (j == std::string::npos) j = list.size();
            std::string t = Trim(list.substr(i, j - i));
            if (!t.empty()) toks.push_back(t);
            i = j + 1;
        }
        if (toks.size() < (size_t)RUN_MIN) return false;
        std::vector<std::string> fam;
        for (size_t k = 0; k < toks.size(); ++k) AddUnique(fam, FamilyOf(toks[k]));
        if (fam.size() >= toks.size()) return false;
        std::string joined;
        for (size_t k = 0; k < fam.size(); ++k) { if (k) joined += ", "; joined += fam[k]; }
        *listField = head + (offs ? " " : "") + joined;
        return true;
    }

    // Returns true when `out` differs from `in`. `out` always holds a complete valid list (a copy of `in` when nothing changed).
    inline bool Compact(const std::vector<Line>& in, std::vector<Line>& out)
    {
        out.clear();
        bool changed = false;
        size_t i = 0, n = in.size();
        while (i < n)
        {
            size_t j = i + 1;
            if (RunCandidate(in[i]))
                while (j < n && RunCandidate(in[j]) && SameKey(in[i], in[j])) ++j;
            if (j - i >= (size_t)RUN_MIN)
            {
                std::string prefix = CommonVsPrefix(in, i, j);
                // only race-damage-like runs: a "+N%" bonus text, or a "... vs <race>" name with the value in val1;
                // armour resistances, weapon stats etc. with equal values must stay untouched
                bool plus = !in[i].s2.empty() && in[i].s2[0] == '+';
                if (!plus && !(in[i].s2.empty() && !prefix.empty())) { out.push_back(in[i]); ++i; continue; }
                std::vector<std::string> fam;
                for (size_t k = i; k < j; ++k) AddUnique(fam, FamilyOf(in[k].s1.substr(prefix.size())));
                std::vector<std::string> chunks;
                Chunk(fam, prefix.size(), chunks);
                if (!chunks.empty() && chunks.size() < j - i)
                {
                    for (size_t c = 0; c < chunks.size(); ++c)
                        out.push_back(Line(c == 0 ? prefix + chunks[c] : chunks[c], in[i].s2, in[i].vbits));
                    changed = true;
                    i = j;
                    continue;
                }
            }
            Line l(in[i]);
            if (CompactOnlyFor(l)) changed = true;
            out.push_back(l);
            ++i;
        }
        return changed;
    }
}
