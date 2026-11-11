"""Разведка гардеробных модов коллекции Grimdark War (3658803602): размер, подписка, оценка числа вещей по описанию.
Для модов на диске — точный счёт ARMOUR/WEAPON/CROSSBOW через kmod. Итог: out/wardrobe_recon.json"""
import glob
import json
import os
import re
import sys

sys.path.insert(0, r"C:\KenshiModMap\tools")
import kmod  # noqa: E402

OUT = os.path.join(os.path.dirname(__file__), "out")
W = r"C:\Program Files (x86)\Steam\steamapps\workshop\content\233860"
d = {x["publishedfileid"]: x for x in json.load(open(os.path.join(OUT, "pfd_grimdark.json"), encoding="utf-8"))}
# гардероб: броня/одежда/оружие (исключены карты, звуки, расы-животные, интерфейс, world states)
KEYS = ["3785967794", "3475091710", "2882658082", "3045283593", "2980909939", "2178681257", "3051565880", "3661478266",
        "1897538943", "2706218807", "3556712059", "3595693319", "3224267935", "3416362194", "2614426282", "3477292843",
        "3186440323", "3183230127", "3193127902", "1336829063", "3178870697", "3192272492", "3580093163", "2456515727",
        "3344149018", "2206047200", "3174666919", "2678787059", "2001912981", "2805907981", "1958713825", "1926495956",
        "2204309112", "2982809131", "3809464398", "2294747201", "2547875991", "1944912625", "2799955117", "2044880405",
        "3835702545", "3220461803", "1578969334", "1578990167", "3089253212", "3473057404", "2117877487"]
NUM = re.compile(r"(\d{1,4})\s*\+?\s*(?:new\s+)?(armou?r\s*(?:pieces|sets|parts)?|weapons?|items?|sets?|helmets?|outfits?|clothes|pieces|variants|types|limbs?)", re.I)
rows = []
for i in KEYS:
    x = d.get(i)
    if not x:
        continue
    mb = int(x.get("file_size", 0) or 0) / 1e6
    on = os.path.isdir(os.path.join(W, i))
    exact = None
    slots = {}
    if on:
        cnt = {"ARMOUR": 0, "WEAPON": 0, "CROSSBOW": 0}
        for f in glob.glob(os.path.join(W, i, "*.mod")):
            for it in kmod.read(f).items:
                if it.change == 0 and it.type_name in cnt:
                    cnt[it.type_name] += 1
                    if it.type_name == "ARMOUR":
                        slots[it.values.get("slot")] = slots.get(it.values.get("slot"), 0) + 1
        exact = cnt
    desc = x.get("description", "") or ""
    hints = sorted({f"{n} {w.lower()}" for n, w in NUM.findall(desc) if 1 < int(n) < 3000})[:6]
    total = sum(exact.values()) if exact else None
    rows.append({"id": i, "title": x.get("title"), "mb": round(mb, 1), "subs": x.get("subscriptions"), "on_disk": on,
                 "exact_items": exact, "armour_slots": slots, "desc_hints": hints,
                 "items_per_mb": round(total / mb, 2) if total and mb else None,
                 "url": f"https://steamcommunity.com/sharedfiles/filedetails/?id={i}"})
json.dump(rows, open(os.path.join(OUT, "wardrobe_recon.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
for r in sorted(rows, key=lambda r: -r["mb"]):
    print(f"{r['id']} {r['mb']:7.1f}MB {'DISK' if r['on_disk'] else '    '} {str(r['exact_items'] or ''):<45} {r['items_per_mb'] or '':<6} {r['title'][:38]:<38} {r['desc_hints']}")
