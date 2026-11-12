"""Разбор последнего сейва владельца (только чтение): что реально надето на NPC — ваниль / модовое (новый меш) / модовое с ванильным мешем.
python tools\\save_report.py [имя_папки_сейва]   (по умолчанию самый свежий в %LOCALAPPDATA%\\kenshi\\save, кроме KMM_SMOKE). До ~15 с."""
import collections
import glob
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kmod  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

G = r"C:\Program Files (x86)\Steam\steamapps\common\Kenshi"
W = r"C:\Program Files (x86)\Steam\steamapps\workshop\content\233860"
SAVES = os.path.expandvars(r"%LOCALAPPDATA%\kenshi\save")
WORN = ("legs", "shirt", "boots", "armour", "head", "belt", "eyes_belts", "neck")


def latest_save():
    ds = [d for d in glob.glob(SAVES + r"\*") if os.path.isdir(d + r"\platoon") and os.path.basename(d) != "KMM_SMOKE"
          and os.listdir(d + r"\platoon")]
    return max(ds, key=os.path.getmtime) if ds else None


def main():
    d = os.path.join(SAVES, sys.argv[1]) if len(sys.argv) > 1 else latest_save()
    if not d:
        print("сейвов нет"); return
    V = kmod.load_chain([G + r"\data\gamedata.base", G + r"\data\rebirth.mod", G + r"\data\Newwworld.mod", G + r"\data\Dialogue.mod"])
    src = {}
    for p in glob.glob(W + r"\*\*.mod") + glob.glob(G + r"\mods\*\*.mod"):
        src.setdefault(os.path.basename(p), p)
    merged = kmod.read(G + r"\mods\KMM_Merged\KMM_Merged.mod").by_sid() if os.path.exists(G + r"\mods\KMM_Merged\KMM_Merged.mod") else {}
    worn, owners = collections.Counter(), collections.defaultdict(list)
    sec = collections.defaultdict(collections.Counter)
    for p in glob.glob(d + r"\platoon\*"):
        try:
            items = kmod.read(p).items
        except Exception:
            continue
        for it in items:
            if it.type_name == "INVENTORY_ITEM_STATE" and it.values.get("section") in WORN:
                b = it.values.get("base data sid", "")
                if b:
                    worn[b] += 1
                    owners[(p, it.values.get("ownedbyCS"), it.values.get("ownedbyS"), it.values.get("ownedbyI"))].append(b in V)
                    sec[it.values["section"]]["vanilla" if b in V else "mod"] += 1
    cache, res = {}, collections.Counter()
    for s, n in worn.items():
        if s in V:
            res["ваниль"] += n; continue
        it = merged.get(s)
        if it is None:
            p = src.get(s.split("-", 1)[-1])
            if p:
                if p not in cache:
                    cache[p] = kmod.read(p).by_sid()
                it = cache[p].get(s)
        if it is None:
            res["мод (источник не найден)"] += n; continue
        ms = [str(v).lower() for k, v in it.values.items() if "mesh" in k.lower() and str(v).strip()]
        res["мод, новый меш" if any("mods" in m or "workshop" in m for m in ms) else "мод, ванильный меш"] += n
    t = sum(res.values()) or 1
    print(f"сейв: {d}  ({len(owners)} владельцев вещей, {t} надетых вещей)")
    for k, v in res.most_common():
        print(f"  {k:28s} {v:5d}  {100 * v // t}%")
    print("  по слотам (доля модовых): " + ", ".join(f"{s} {c['mod'] * 100 // max(1, c['mod'] + c['vanilla'])}%" for s, c in sorted(sec.items())))
    full = sum(1 for l in owners.values() if all(l))
    print(f"  NPC целиком в ванили: {full} из {len(owners)} ({100 * full // max(1, len(owners))}%)")


if __name__ == "__main__":
    main()
