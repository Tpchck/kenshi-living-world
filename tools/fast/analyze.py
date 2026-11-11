"""Паспорта WH-модов и карта пересечений с основой (FAST_PLAN шаг 3). Итог: out/wh_analysis.json."""
import collections
import json
import os
import sys

sys.path.insert(0, r"C:\KenshiModMap\tools")
sys.path.insert(0, r"C:\KenshiModMap\tools\fast")
import kmod  # noqa: E402
import ctx  # noqa: E402

OUT = ctx.OUT
lo, van, base, wh = ctx.load()

# 0) round-trip всех файлов сборки
rt_bad = [n for n, m, e in van + base + wh if m is not None and
          kmod.write(m) != open(ctx.DATA + n if n in ctx.VANILLA else
                                next(x["path"] for x in lo["base"] + lo["wh"] if x["file"] == n), "rb").read()]

# 1) кто трогает каждую запись: sid -> [(слой, мод, change, ключи значений, категории ссылок)]
touch = collections.defaultdict(list)
origin = {}
for layer, group in (("vanilla", van), ("base", base), ("wh", wh)):
    for name, m, _ in group:
        for it in m.items:
            if (it.change == kmod.CHANGE_NEW or layer == "vanilla") and it.sid not in origin:
                origin[it.sid] = (layer, name)
            touch[it.sid].append((layer, name, it.change, set(it.values), set(it.refs)))

merged = {}
for _, m, _ in van + base + wh:
    kmod.apply(merged, m)

wh_names = [n for n, _, _ in wh]
wh_meta = {w["file"]: w for w in lo["wh"]}
passports, overlaps = [], []
for name, m, _ in wh:
    own_new = [it for it in m.items if it.change == kmod.CHANGE_NEW]
    changed = [it for it in m.items if it.change != kmod.CHANGE_NEW]
    by_type = collections.Counter(it.type_name for it in own_new)
    ch_by_src = collections.Counter(origin.get(it.sid, ("?", "?"))[0] if origin.get(it.sid, ("?",))[0] != "wh"
                                    else "wh:" + origin[it.sid][1] for it in changed)
    # новые записи с sid, уже существующим раньше (коллизия)
    collide = [it.sid for it in own_new if origin.get(it.sid, (None, name))[1] != name]
    # битые ссылки (цели нет в итоговом контексте)
    broken = collections.Counter()
    for it in m.items:
        for cat, refs in it.refs.items():
            for r in refs:
                if (r.v0, r.v1, r.v2) != kmod.DELETED_REF and r.target not in merged:
                    broken[(it.type_name, cat)] += 1
    # пересечения: изменённые записи, которые трогает и основа
    conf = []
    for it in changed:
        others = [t for t in touch[it.sid] if t[0] == "base" and t[2] != kmod.CHANGE_NEW]
        others_wh = [t for t in touch[it.sid] if t[0] == "wh" and t[1] != name and t[2] != kmod.CHANGE_NEW
                     and not t[1].startswith(name.replace(".mod", ""))]
        if not (others or others_wh):
            continue
        mine_v, mine_r = set(it.values), set(it.refs)
        for t in others + others_wh:
            kv, kr = mine_v & t[3], mine_r & t[4]
            conf.append({"sid": it.sid, "type": it.type_name, "name": merged.get(it.sid, it).name,
                         "other": t[1], "other_layer": t[0], "same_fields": sorted(kv), "same_ref_cats": sorted(kr)})
    overlaps += [dict(c, wh=name) for c in conf]
    passports.append({
        "file": name, "id": wh_meta[name]["id"], "title": wh_meta[name]["title"], "ftype": m.ftype,
        "deps": m.header.dependencies, "refs": m.header.references, "items": len(m.items),
        "new_by_type": dict(by_type.most_common()), "changed": len(changed), "changed_by_origin": dict(ch_by_src),
        "sid_collisions": collide, "broken_refs": {f"{a}/{b}": n for (a, b), n in broken.most_common()},
        "factions": [it.name for it in own_new if it.type_name == "FACTION"],
        "races": [it.name for it in own_new if it.type_name == "RACE"],
        "squads": len([1 for it in own_new if it.type_name == "SQUAD_TEMPLATE"]),
        "starts": [it.name for it in own_new if it.type_name == "NEW_GAME_STARTOFF"],
        "research": [it.name for it in own_new if it.type_name == "RESEARCH"][:8],
        "conflicts_with_base": len({c["sid"] for c in conf if c["other_layer"] == "base"}),
        "conflict_field_overlaps": sum(1 for c in conf if c["same_fields"] or c["same_ref_cats"]),
    })

res = {"roundtrip_failed": rt_bad, "files_checked": len(van) + len(base) + len(wh),
       "merged_records": len(merged), "passports": passports, "overlaps": overlaps}
json.dump(res, open(os.path.join(OUT, "wh_analysis.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("round-trip failures:", len(rt_bad), rt_bad[:5], "| merged records", len(merged))
for p in passports:
    print(f"{p['file']:<32} items={p['items']:<5} new={sum(p['new_by_type'].values()):<5} chg={p['changed']:<5} "
          f"origins={p['changed_by_origin']} collide={len(p['sid_collisions'])} broken={sum(p['broken_refs'].values())} "
          f"conflBase={p['conflicts_with_base']} fieldOverl={p['conflict_field_overlaps']}")
    print(f"    factions={p['factions']} races={p['races']} squads={p['squads']} starts={p['starts']}")
    if p["broken_refs"]: print("    broken:", p["broken_refs"])
