"""Покрытие API KenshiLua нашим Lua (офлайн, только чтение).
python -I -X utf8 tools/engine_api_usage.py [корень build] -> сводка по B (BindingsReference) и C (CallbacksReference).
Грубо: совпадение имён после '.'/':' (верхняя граница). Подробности и список целевых привязок: docs/ENGINE_MAP.md."""
import collections, glob, os, re, sys

DOCS = r"C:\Program Files (x86)\Steam\steamapps\workshop\content\233860\3817000612\docs"
ROOT = sys.argv[1] if len(sys.argv) > 1 else r"C:\KenshiModMap\build"
SKIP = re.compile(r"(GUI|Window|Screen|Panel|MyGUI|DataPanel|Layout|Widget|Tutorial|Anim|Render|Ogre|Havok|hk|Ak|Sound|Audio|Camera|Mesh|Shader|Particle|Entity|Effect|Weather|Water|ToolTip|Portrait|Button|Label|Icon|Menu|Options|Title|Splash|NavMesh|Physics|Thread|Paged|Forest|Light|Decal|Debug|Input|Key|OIS|Ribbon|Billboard|Cursor|Preview|Context|Font|Overlay|Skin|Terrain|Ragdoll|Bone|Skeleton|Collision|Path|Wind|Fog|Sky|Cloud|Movable|Scene|Node|Viewport|Texture|Material|Compositor|Timer|Mutex|Editor|Cache|Batcher|Vector|Quaternion|Matrix|AABB|Ray|Plane|Sphere|Color|Image|Sprite)", re.I)
GUI_CB = re.compile(r"(GUI|Window|Screen|Panel|DataPanel|Layout|MyGUI|Icon|Tab|Button|Options|Title|Splash|Context|Order(Cell|sItem|Data)|Inventory(Section|Icon|Layout)|Stat\b|Tutorial|Tooltip)")


def read(name):
    return open(os.path.join(DOCS, name), encoding="utf-8").read().split("\n")


def bindings():
    rows, cls, sec = collections.defaultdict(set), None, None
    for l in read("BindingsReference.md"):
        m = re.match(r"^## (.+)$", l)
        if m:
            cls = m.group(1).strip(); continue
        if l.startswith("### "):
            sec = l[4:].strip(); continue
        if cls and sec in ("Fields", "Methods") and l.startswith("| "):
            c = l.split("|")[1].strip()
            if c and c != "Lua Name" and not c.startswith("---"):
                rows[cls].add(re.sub(r" \[\d+\]$", "", c))
    return rows


def used_names():
    used = collections.Counter()
    for p in glob.glob(os.path.join(ROOT, "KMM_*", "scripts", "**", "*.lua"), recursive=True):
        s = re.sub(r"--[^\n]*", "", open(p, encoding="utf-8-sig", errors="replace").read())
        for m in re.finditer(r"[:.]\s*([A-Za-z_][A-Za-z0-9_]*)", s):
            used[m.group(1)] += 1
    return used


def main():
    rows, used = bindings(), used_names()
    allnames = set().union(*rows.values())
    rel = [c for c in rows if not SKIP.search(c)]
    relnames = set().union(*(rows[c] for c in rel))
    print(f"classes {len(rows)}, members {sum(map(len, rows.values()))}, distinct names {len(allnames)}")
    print(f"world-ish classes {len(rel)}, members {sum(len(rows[c]) for c in rel)}, distinct names {len(relnames)}")
    print(f"used names (upper bound): all {len(set(used) & allnames)}, world {len(set(used) & relnames)}")
    for c in ("Character", "AI", "CharStats", "Dialogue", "DialogLineData", "PlayerInterface", "GameWorld", "Faction", "FactionRelations", "Platoon", "Town", "TownBase", "Inventory", "MedicalSystem", "BountyManager"):
        if c in rows:
            print(f"  {c}: {len(rows[c] & set(used))}/{len(rows[c])}")
    C = read("CallbacksReference.md")
    notif = [re.match(r"\| `([^`]+)`", l).group(1) for l in C if re.match(r"\| `", l)]
    # таблицы: уведомления идут до заголовка 'Override Callbacks', перехваты после
    split = next(i for i, l in enumerate(C) if l.startswith("## Override Callbacks"))
    n1 = [re.match(r"\| `([^`]+)`", l).group(1) for l in C[:split] if re.match(r"\| `", l)]
    n2 = [re.match(r"\| `([^`]+)`", l).group(1) for l in C[split:] if re.match(r"\| `", l) and "Event Name" not in l]
    w1 = [e for e in n1 if not GUI_CB.search(e.split("::")[0])]
    w2 = [e for e in n2 if not GUI_CB.search(e.split("::")[0])]
    print(f"callbacks: notification {len(n1)} (world {len(w1)}), override {len(n2)} (world {len(w2)})")
    src = " ".join(open(p, encoding="utf-8-sig", errors="replace").read() for p in glob.glob(os.path.join(ROOT, "KMM_*", "scripts", "**", "*.lua"), recursive=True))
    ours = sorted(set(re.findall(r'Events\.on\(\s*"([^"]+)"', src)))
    print("callbacks used:", ours)


if __name__ == "__main__":
    main()
