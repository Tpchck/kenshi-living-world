"""ROBBERY: компактная таблица sid -> [stat_score, group, flags] из data/catalog.json (только чтение) -> build/KMM_Conductor/gear_scores.json.
flags: 1 = WH (imperial/chaos/xenos), 2 = расовый замок (Whistler). KMM_Traces сравнивает добытую броню/оружие с надетым по этому score.
python -I -X utf8 tools/conductor/gen_gear_scores.py"""
import json
import os

ROOT = r"C:\KenshiModMap"
cat = json.load(open(os.path.join(ROOT, "data", "catalog.json"), encoding="utf-8"))["items"]
out = {}
for it in cat:
    if it["type"] not in ("ARMOUR", "WEAPON", "CROSSBOW") or "stat_score" not in it:
        continue
    flags = (1 if it.get("origin") in ("imperial", "chaos", "xenos") else 0) | (2 if "whistler" in it.get("name", "").lower() else 0)
    out[it["sid"]] = [round(it["stat_score"], 2), it["group"], flags]
dst = os.path.join(ROOT, "build", "KMM_Conductor", "gear_scores.json")
json.dump({"s": out}, open(dst, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
print(len(out), "items ->", dst, os.path.getsize(dst), "bytes")
