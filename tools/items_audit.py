"""Аудит предметов итоговой цепочки кроме брони/оружия (ITEM, MAP_ITEM, CONTAINER) -> data/items_audit.json. Только чтение.
python -I -X utf8 tools\\items_audit.py   (Ctx грузится ~минуты). Поля: группы, цены, мёртвые, дубли, выбросы, проверка ассетов (как audit_classes A)."""
import collections
import glob
import json
import os
import statistics
import sys

sys.path[:0] = [r"C:\KenshiModMap\tools", r"C:\KenshiModMap\tools\build", r"C:\KenshiModMap\tools\streams", r"C:\KenshiModMap\tools\fast"]
import kmm_build  # noqa: E402
import _items  # noqa: E402

G = r"C:\Program Files (x86)\Steam\steamapps\common\Kenshi"
W = r"C:\Program Files (x86)\Steam\steamapps\workshop\content\233860"
ASSET_EXT = (".mesh", ".dds", ".png", ".tga", ".jpg")
OUT = r"C:\KenshiModMap\data\items_audit.json"


def asset_names():
    cfg = [l.strip() for l in open(G + r"\data\mods.cfg", encoding="utf-8", errors="replace") if l.strip()]
    dirs = {os.path.basename(p): os.path.dirname(p) for p in glob.glob(W + r"\*\*.mod") + glob.glob(G + r"\mods\*\*.mod")}
    roots = [G + r"\data"] + [dirs[m] for m in cfg if m in dirs]
    names = set()
    for r in set(roots):
        for _, _, fs in os.walk(r):
            names |= {f.lower() for f in fs}
    return names


def main():
    ctx = kmm_build.Ctx()
    rows = _items.build_rows(ctx)
    names = asset_names()
    for r in rows:
        it = ctx.M[r["sid"]]
        bad = []
        for k, v in it.values.items():
            if isinstance(v, str) and v.strip().lower().endswith(ASSET_EXT):
                n = v.replace("/", "\\").split("\\")[-1].strip().lower()
                if n and n not in names:
                    bad.append(f"{k}={n}")
        r["missing_assets"] = bad[:3]
    sc = _items.vanilla_scales(rows)
    for r in rows:
        s = sc.get(r["group"])
        r["ratio"] = round(r["vw"] / s["med_vw"], 2) if s and s["med_vw"] and r["value"] > 0 else None
        r["outlier"] = bool(s and s["n"] >= 3 and r["ratio"] is not None and not r["vanilla"] and (r["ratio"] > 3 or r["ratio"] < 1 / 3))
    # дубли: одинаковое имя в одной группе из разных записей
    d = collections.defaultdict(list)
    for r in rows:
        if r["group"] not in ("token",) and _items.norm_name(r["name"]):
            d[(r["group"], _items.norm_name(r["name"]))].append(r)
    dups = {f"{g}|{n}": [(x["sid"], x["mod"], x["value"], not x["missing_assets"], x["icon"]) for x in v] for (g, n), v in d.items() if len(v) > 1}
    groups = {}
    for g in sorted({r["group"] for r in rows}):
        rs = [r for r in rows if r["group"] == g]
        vals = sorted(r["value"] for r in rs if r["value"] > 0)
        groups[g] = {"count": len(rs), "vanilla": sum(r["vanilla"] for r in rs), "mods": len({r["mod"] for r in rs}),
                     "top_mods": collections.Counter(r["mod"] for r in rs).most_common(6),
                     "value0": sum(r["value"] <= 0 for r in rs), "value_med": statistics.median(vals) if vals else 0,
                     "value_p10_p90": [vals[len(vals) // 10], vals[len(vals) * 9 // 10]] if vals else [],
                     "weight_med": statistics.median(r["weight"] for r in rs), "vanilla_scale": sc.get(g),
                     "dead": sum(r["dead"] for r in rs), "dead_nonquest": sum(r["dead"] and not r["quest"] for r in rs),
                     "quest": sum(r["quest"] for r in rs), "outliers": sum(r["outlier"] for r in rs),
                     "missing_assets": sum(bool(r["missing_assets"]) for r in rs), "dup_groups": sum(1 for k in dups if k.startswith(g + "|"))}
    json.dump({"groups": groups, "dups": dups, "items": rows}, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    for g, v in groups.items():
        print(g, {k: v[k] for k in ("count", "vanilla", "mods", "value0", "value_med", "weight_med", "dead", "dead_nonquest", "quest", "outliers", "missing_assets", "dup_groups")})
    print("total", len(rows), "dup name groups", len(dups))


if __name__ == "__main__":
    main()
