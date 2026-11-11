"""Итоговый load order: официальный LO коллекции 2839009285 (только реально скачанные моды коллекции)
→ WH-слой (оригинал, затем EN) → KMM_Glue. Пишет out/final_lo.json."""
import json, os
OUT = os.path.join(os.path.dirname(__file__), "out")
W = "C:/Program Files (x86)/Steam/steamapps/workshop/content/233860/"
COLL = "2839009285"
# WH-слой из FAST_PLAN.md (Chaos Demons отложен до RE_Kenshi). Порядок: Империум → орки → некроны → Mark-X.
WH = [("3785967794", "Imperial Forces"), ("3787053769", "Imperial Forces EN"),
      ("2204309112", "Death Korps"), ("2614426282", "Steel Legion Armoury"),
      ("3835702545", "Waaagh! (OrcRaceReview — база расы орков)"), ("3836356922", "Waaagh! EN"),
      ("3595693319", "40K Necrons"), ("3596387634", "40K Necrons EN"),
      ("3475091710", "40k Mark-X"), ("3596387397", "40k Mark-X EN")]
# Доп. моды после WH-слоя (аудит tools/fast/audit_mods.py, 2026-11-11): волна 1 WARDROBE + культовые (docs/CULTS.md).
# Deathstroke 2206047200 исключён: свои дефолтные маски тела вместо Community Part Map.
EXTRA = [("3186440323", "Hell Bringer"), ("3183230127", "Hell Stalker"), ("3193127902", "Hell Buster"), ("3178870697", "Hell Hound"),
         ("3192272492", "Hell Pathfinder"), ("3174666919", "Hell Survivor"), ("3344149018", "Machinist armor"), ("3416362194", "Metro2033"),
         ("2980909939", "Got Gear?"), ("1897538943", "Mercenary Full Plate"), ("2982809131", "Saxon armour"), ("2456515727", "Bounty Hunter Armor"),
         ("2547875991", "Rusty Raiders"), ("3809464398", "TRASH"), ("2294747201", "Old Empire Enforcers"), ("1944912625", "Druid Helm"),
         ("2799955117", "Weapon - Grausam"), ("2044880405", "Weapon - BusterJitte"),
         ("1762149693", "Throes of Obedience"), ("3467763726", "Complex AI - Anti-Assassinate"), ("3550526654", "Settled Nomads Expanded V2"),
         ("2800302311", "KPM: Performance Particles"), ("1845960491", "Weapons look metallic"), ("3400528309", "Pretty Stuff"),
         ("3263005742", "Dropped in Style"),
         ("3821854793", "Chaos Demons"), ("3821856574", "Chaos Demons EN"), ("766462696", "Racial Diversity"),
         ("3653182101", "Populated Cities Redux"),   # аудит 2026-11-12: +16 записей, 9 TOWN/8 FACTION дописывают ссылки, 0 перезаписей основы
         # Crafting Redux (аудит TECH 2026-11-12, docs/streams/TECH.md): без CraftingReduxPlus (25 заглушек «MISSING MOD» поверх брони основы)
         ("3585383286", "Armor Crafting Redux - Core"), ("3585385588", "Armor Crafting Redux - Research Fix"), ("3585385029", "Armor Crafting Redux - OMO"),
         ("3585385287", "Armor Crafting Redux - EVA"), ("3585386517", "Weapon Smithing Redux - Core"), ("3585386805", "Weapon Smithing Redux - Edge"),
         ("3589917614", "Robotics Crafting Redux: Core"), ("2760310007", "Robotics Crafting Redux: Plus"),
         # огнестрел/аксессуары (аудит 2026-11-12, WARDROBE v3): плагин секций инвентаря (Nexus 1838, локальный) → фреймворк → стволы → одежда
         ("local:Extra Inventory Sections Plugin.mod", "Extra Inventory Sections (Nexus 1838)"),
         ("3606059222", "Cat-Lon's Gun Framework"), ("3606978260", "Muskets for Gun Framework"), ("2360832398", "The Shoddy Firearms Mod"),
         ("2180975180", "Muskets of Kenshi"), ("3387751018", "A Standalone Musket Mod"), ("3239840151", "Katanas and Firelocks CN"),
         ("3262178905", "Katanas and Firelocks EN"), ("3832765442", "Black Powder (RE_KENSHI)"),
         ("1942123109", "Poncho"), ("3778343242", "Barbarian's cloak and sack"), ("3698596380", "HTT Cloaks ReKenshi NECK"),
         # 2026-11-13 подписки владельца: Towns Expansion после CATO (его 14 общих зон с CATO выигрывают целиком — 6 городов TE), Mech-Husk (раса-животное + плагин AnimalArmor)
         ("3012631009", "Towns Expansion"), ("3820786403", "Mech-Husk Subjects")]
GLUE = "KMM_Glue.mod"
EXCLUDED = json.load(open(os.path.join(os.path.dirname(__file__), "..", "..", "rules", "excluded_mods.json"), encoding="utf-8"))["mods"]   # исключённые по аудиту/багам


def build():
    scan = {}   # живой скан Workshop (кэш workshop_scan.json устаревал после подписок)
    for d in sorted(os.listdir(W)):
        fs = sorted(f for f in os.listdir(W + d) if f.endswith(".mod")) if os.path.isdir(W + d) else []
        if fs:
            scan[d] = fs
    json.dump({"by_id": scan}, open(os.path.join(OUT, "workshop_scan.json"), "w", encoding="utf-8"), ensure_ascii=False)
    coll = [c["publishedfileid"] for c in json.load(open(os.path.join(OUT, f"coll_{COLL}.json")))["response"]["collectiondetails"][0]["children"]]
    lo = json.load(open(os.path.join(OUT, "lo_official.json"), encoding="utf-8"))
    by_file = {f: i for i, fs in scan.items() for f in fs}
    collset = set(coll)
    base, skipped = [], []
    for line in lo:
        if not line.endswith(".mod"):
            skipped.append((line, "не мод (заголовок в тексте автора)")); continue
        wid = by_file.get(line)
        if wid is None:
            skipped.append((line, "нет в Workshop (Nexus/не подписан)")); continue
        if wid not in collset:
            skipped.append((line, f"{wid} не входит в коллекцию")); continue
        if line in EXCLUDED:
            skipped.append((line, "исключён: " + EXCLUDED[line][:80])); continue
        base.append({"file": line, "id": wid, "path": W + wid + "/" + line})
    in_lo = {b["id"] for b in base}
    coll_not_in_lo = [c for c in coll if c in scan and c not in in_lo]
    wh = [{"file": scan[i][0], "id": i, "title": t, "path": W + i + "/" + scan[i][0]} for i, t in WH]
    LOC = json.load(open(os.path.join(os.path.dirname(__file__), "..", "..", "rules", "local_mods.json"), encoding="utf-8"))["mods"]
    GM = "C:/Program Files (x86)/Steam/steamapps/common/Kenshi/mods/"
    extra = [({"file": i[6:], "id": i, "title": t, "path": GM + LOC[i[6:]] + "/" + i[6:]} if i.startswith("local:") else
              {"file": scan[i][0], "id": i, "title": t, "path": W + i + "/" + scan[i][0]}) for i, t in EXTRA]
    assert not [x["file"] for x in wh + extra if x["file"] in EXCLUDED], "исключённый мод в WH/EXTRA"
    res = {"base": base, "wh": wh, "extra": extra, "glue": GLUE, "skipped_lo_lines": skipped,
           "collection_missing_on_disk": [c for c in coll if c not in scan],
           "collection_not_in_lo": coll_not_in_lo,
           "unused_subs": sorted(set(scan) - collset - {i for i, _ in WH} - {i for i, _ in EXTRA})}
    json.dump(res, open(os.path.join(OUT, "final_lo.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return res


if __name__ == "__main__":
    r = build()
    print("base", len(r["base"]), "wh", len(r["wh"]), "skipped", r["skipped_lo_lines"],
          "coll missing", r["collection_missing_on_disk"], "coll not in LO", r["collection_not_in_lo"], "unused", r["unused_subs"])
