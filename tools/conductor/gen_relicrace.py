"""RELICRACE: точки (логова реликтов из fix.json treasure.edge_lairs: сайты и города conductor.json с координатами) и реликтовые вещи по тирам
(data/catalog.json, только чтение) -> build/KMM_Conductor/relicrace.json. python -I -X utf8 tools/conductor/gen_relicrace.py"""
import json
import os
import re
import sys

ROOT = r"C:\KenshiModMap"
sys.path.insert(0, os.path.join(ROOT, "tools"))
import kmod  # noqa: E402

fx = json.load(open(os.path.join(ROOT, "rules", "streams", "fix.json"), encoding="utf-8"))
EL = fx["treasure"]["edge_lairs"]
cat = {i["sid"]: i for i in json.load(open(os.path.join(ROOT, "data", "catalog.json"), encoding="utf-8"))["items"]}
cd = json.load(open(os.path.join(ROOT, "build", "KMM_Conductor", "conductor.json"), encoding="utf-8"))
pts = {}
for s in cd.get("sites", []):
    pts[s["sid"]] = (s["name"], s["x"], s["z"])
for sid, t in cd.get("town_info", {}).items():
    if t.get("x") is not None and t.get("z") is not None:
        pts.setdefault(sid, (t["name"], t["x"], t["z"]))
sites, relics = [], {}
for g in EL["groups"]:
    rx = re.compile(g["name_rx"], re.I)
    gi = [i for i in g["items"] if i in cat and cat[i]["type"] in ("WEAPON", "CROSSBOW", "ARMOUR", "CONTAINER")]
    for sid in sorted(pts):
        nm, x, z = pts[sid]
        if rx.search(nm) and "override" not in nm.lower():
            sites.append({"sid": sid, "name": nm, "x": x, "z": z, "g": g["id"]})
    for i in gi:
        c = cat[i]
        r = relics.setdefault(i, {"sid": i, "name": c["name"] if c["name"].isascii() else "", "cat": c["type"], "it": kmod.type_code(c["type"]),
                                  "tier": int(c.get("tier", "T2")[1:]), "g": []})
        r["g"].append(g["id"])
out = {"_doc": "RELICRACE (gen_relicrace.py): sites — логова (точки направления экспедиций), relics — реликтовые вещи (it = код itemType для gamedata:getData, tier 2/3).",
       "sites": sites, "relics": sorted(relics.values(), key=lambda r: r["sid"])}
dst = os.path.join(ROOT, "build", "KMM_Conductor", "relicrace.json")
json.dump(out, open(dst, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
print(len(sites), "sites,", len(out["relics"]), "relics ->", dst, os.path.getsize(dst), "bytes")
