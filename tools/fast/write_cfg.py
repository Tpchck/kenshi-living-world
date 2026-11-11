"""Пишет Kenshi/data/mods.cfg: основа (официальный LO) → WH-слой → KMM_Glue. Бэкап оригинала — C:/KenshiModMap/backup."""
import json, os
OUT = os.path.join(os.path.dirname(__file__), "out")
CFG = r"C:\Program Files (x86)\Steam\steamapps\common\Kenshi\data\mods.cfg"
assert os.path.exists(r"C:\KenshiModMap\backup\mods.cfg.2026-11-11.orig"), "нет бэкапа"
lo = json.load(open(os.path.join(OUT, "final_lo.json"), encoding="utf-8"))
lines = [b["file"] for b in lo["base"]] + [w["file"] for w in lo["wh"]] + [lo["glue"]]
assert len(lines) == len(set(lines))
open(CFG, "w", encoding="utf-8", newline="").write("".join(l + "\r\n" for l in lines))
open(os.path.join(OUT, "mods.cfg.written"), "w", encoding="utf-8", newline="").write("".join(l + "\r\n" for l in lines))
print("mods.cfg:", len(lines), "строк; первые:", lines[:3], "последние:", lines[-12:])
