"""Генератор rules/dedup_canonical.json (DEDUP-POOLS, docs/journal/DEDUP_POOLS.md).
python -I -X utf8 tools/dedup_canonical.py
Берёт вещи каталога гардероба (data/catalog.json: ARMOUR и рюкзаки CONTAINER), читает итоговое состояние записей
цепочки модов (без KMM_*, порядок как у генератора mods.cfg) и строит:
  clone_groups: точные клоны (те же строки, числа и ссылки; имя/описание/цена/иконка не важны, как в dedup_report.py);
                canon = самое «чистое» имя (без скобок и цветовых пометок), остальные — clones.
  families:     семейства перекрасок: одинаковое имя без цветовой пометки в скобках (Name (Black)/(Blue)/[colored]/[dyed]),
                тот же тип и слот каталога; члены — представители клон-групп, у каждого color.
Чужие записи не меняются. Поток wardrobe считает группу/семейство одной вещью (вес 1)."""
import collections
import json
import os
import re
import sys

ROOT = r"C:\KenshiModMap"
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, os.path.join(ROOT, "tools", "build"))
sys.path.insert(0, os.path.join(ROOT, "tools", "fast"))
import kmod  # noqa: E402
import mods_cfg as M  # noqa: E402

OUT = os.path.join(ROOT, "rules", "dedup_canonical.json")
COLORS = ("black white gray grey red blue green yellow brown purple orange pink gold golden silver tan beige cyan teal navy crimson "
          "violet maroon olive khaki cream ivory bronze copper dark light pale pure bright").split()
TAGS = ("colored coloured dyed dyeable painted alt style variant recolor recolour color colour").split()
WORDS = set(COLORS) | set(TAGS)
PURE = set(COLORS) - set("dark light pale pure bright".split())
BR = re.compile(r"\s*[\(\[]([^\)\]]*)[\)\]]")


def split_name(name):
    """(базовое имя без цветовых пометок, цвет/пометка или '')."""
    tags = []

    def sub(m):
        words = re.findall(r"[a-z]+", m.group(1).lower())
        if words and all(w in WORDS for w in words):
            tags.append(" ".join(words))
            return ""
        return m.group(0)
    base = re.sub(r"\s+", " ", BR.sub(sub, name or "").strip())
    m = re.match(r"^(.+\S)\s+([A-Za-z]+)$", base)   # «SS Armor green»: цвет последним словом
    if m and m.group(2).lower() in PURE and not tags:
        base, tags = m.group(1), [m.group(2).lower()]
    return base.rstrip(" -").lower(), (tags[0] if tags else "")


def clean_rank(name, pos):
    base, tag = split_name(name)
    return (bool(re.search(r"[\(\[]", name or "")), bool(tag), len(name or ""), pos)


def main():
    cat = json.load(open(os.path.join(ROOT, "data", "catalog.json"), encoding="utf-8"))["items"]
    want = {x["sid"]: x for x in cat if x["type"] in ("ARMOUR", "CONTAINER")}
    lines = M.generate()
    paths = M.mod_paths()
    chain = [os.path.join(M.GAME, "data", c) for c in ("gamedata.base", "rebirth.mod", "Newwworld.mod", "Dialogue.mod")]
    chain += [paths[l] for l in lines if l in paths and not l.startswith("KMM_")]
    merged = kmod.load_chain(chain)
    sigs = collections.defaultdict(list)
    for pos, sid in enumerate(want):
        it = merged.get(sid)
        if it is None:
            continue
        v = it.values
        sig = (it.type_name,
               tuple(sorted((k, str(x).lower().replace("\\", "/")) for k, x in v.items()
                            if isinstance(x, str) and k not in ("description", "name", "class name") and x)),
               tuple(sorted((k, round(x, 3) if isinstance(x, float) else x) for k, x in v.items()
                            if isinstance(x, (int, float)) and not isinstance(x, bool) and k != "value" and "icon" not in k)),
               tuple(sorted((c, tuple(sorted(r.target for r in rs))) for c, rs in it.refs.items())))
        sigs[sig].append((sid, pos))
    clone_groups, canon_of = [], {}
    for lst in sigs.values():
        if len(lst) < 2:
            continue
        lst.sort(key=lambda t: clean_rank(want[t[0]]["name"], t[1]))
        canon = lst[0][0]
        clone_groups.append({"canon": canon, "name": want[canon]["name"], "clones": [t[0] for t in lst[1:]]})
        for t in lst[1:]:
            canon_of[t[0]] = canon
    clone_groups.sort(key=lambda g: g["canon"])
    # семейства: сущности = представители (канон клон-группы либо одиночная вещь)
    ents = [sid for sid in want if sid not in canon_of and sid in merged]
    fam = collections.defaultdict(list)
    for sid in ents:
        x = want[sid]
        base, tag = split_name(x["name"])
        if base:
            fam[(x["type"], x["group"], base)].append((sid, tag))
    families = []
    for (t, g, base), mem in sorted(fam.items()):
        if len(mem) < 2 or not any(tag for _, tag in mem):
            continue
        families.append({"key": f"{g}|{base}", "members": [{"sid": s, "color": tag} for s, tag in sorted(mem)]})
    out = {"_doc": "Генерируется tools/dedup_canonical.py (не править руками). clone_groups: точные клоны, поток wardrobe берёт canon; "
                   "families: перекраски, поток считает семейство одной вещью (вес 1), цвет выбирает внутри.",
           "stats": {"catalog_items": len(want), "clone_groups": len(clone_groups), "clones": len(canon_of),
                     "families": len(families), "family_members": sum(len(f["members"]) for f in families)},
           "clone_groups": clone_groups, "families": families}
    json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    print(out["stats"])
    big = sorted(clone_groups, key=lambda g: -len(g["clones"]))[:8]
    print("крупнейшие клон-группы:", [(g["name"], len(g["clones"]) + 1) for g in big])
    print("крупнейшие семейства:", [(f["key"], len(f["members"])) for f in sorted(families, key=lambda f: -len(f["members"]))[:8]])


if __name__ == "__main__":
    main()
