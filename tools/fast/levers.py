import sys, os, glob, json, collections, re
sys.path.insert(0, r"C:\KenshiModMap\tools"); sys.path.insert(0, r"C:\KenshiModMap\tools\fast")
import kmod, ctx
OUT = ctx.OUT
W = r"C:\Program Files (x86)\Steam\steamapps\workshop\content\233860"
lo, van, base, wh = ctx.load()
glue = kmod.read(r"C:\KenshiModMap\build\KMM_Glue\KMM_Glue.mod")
chain = van + base + wh + [("KMM_Glue.mod", glue, None)]
res = {}
# Dust effects
D = os.path.join(W, "3703458265", "effects")
res["dust"] = {os.path.basename(f)[:-4]: re.search(r"Enabled=(\d)", open(f, encoding="utf-8", errors="replace").read()).group(1) for f in glob.glob(D + "\*.ini")}
# конфиги модов (кроме RE_Kenshi.json, lang, логов)
cfgs = collections.defaultdict(list)
for b in lo["base"] + lo["wh"]:
    d = os.path.join(W, b["id"])
    for p in glob.glob(d + "\**\*", recursive=True):
        bn = os.path.basename(p).lower()
        if os.path.isfile(p) and bn.endswith((".ini", ".cfg", ".json", ".yml", ".yaml", ".toml", ".txt")) and bn != "re_kenshi.json" \
           and "\lang" not in p.lower() and "\logs" not in p.lower() and "locale" not in p.lower() and not bn.startswith(("readme", "license", "changelog", "third")) and "\effects" not in p.lower():
            cfgs[b["file"]].append(os.path.relpath(p, d))
res["mod_configs"] = {k: v[:6] for k, v in cfgs.items()}
# GLOBAL CONSTANTS: кто что меняет
M = {}; who = collections.defaultdict(list)
for n, m, _ in chain:
    for it in m.items:
        if it.type_name == "CONSTANTS":
            for k, v in it.values.items(): who[k].append((n, v))
    kmod.apply(M, m)
const = next(i for i in M.values() if i.type_name == "CONSTANTS")
base_c = {}
for _, m, _ in van:
    for it in m.items:
        if it.type_name == "CONSTANTS": base_c.update(it.values)
changed = {k: {"vanilla": base_c.get(k), "final": const.values.get(k), "mods": [x[0] for x in who[k] if x[0] not in ctx.VANILLA]}
           for k in const.values if any(x[0] not in ctx.VANILLA for x in who[k])}
res["constants_changed"] = changed
# спавны
bg = [i for i in M.values() if i.type_name == "BIOME_GROUP"]
res["spawns"] = {"biomes": len(bg), "entries": sum(len(b.refs.get("homeless spawns", [])) for b in bg),
                 "top": sorted([(b.name, len(b.refs.get("homeless spawns", [])), sum(r.v0 for r in b.refs.get("homeless spawns", [])), b.values.get("homeless spawn amount")) for b in bg], key=lambda x: -x[1])[:8]}
# world states / override towns
ws = [i for i in M.values() if i.type_name == "WORLD_EVENT_STATE"]
towns_ovr = [i for i in M.values() if i.type_name == "TOWN" and i.refs.get("override town")]
res["world_states"] = {"states": len(ws), "towns_with_overrides": len(towns_ovr), "override_variants": sum(len(t.refs["override town"]) for t in towns_ovr)}
# отношения
fac = [i for i in M.values() if i.type_name == "FACTION"]
rel = [(f.name, r.target, r.v0) for f in fac for r in f.refs.get("relations", [])]
res["relations"] = {"factions": len(fac), "relation_entries": len(rel), "hostile(<=-50)": sum(1 for x in rel if x[2] <= -50), "friendly(>=50)": sum(1 for x in rel if x[2] >= 50),
                    "coexistence_entries": sum(len(f.refs.get("coexistence", [])) for f in fac)}
# торговцы
sq = [i for i in M.values() if i.type_name == "SQUAD_TEMPLATE" and i.values.get("is trader")]
vl = [i for i in M.values() if i.type_name == "VENDOR_LIST"]
res["traders"] = {"trader_squads": len(sq), "vendor_lists": len(vl),
                  "vendor money": collections.Counter(i.values.get("vendor money") for i in sq).most_common(5),
                  "refresh time": collections.Counter(round(float(i.values.get("vendors refresh time", 24)), 1) for i in sq).most_common(5),
                  "fill total": collections.Counter(i.values.get("vendors fill total amount") for i in sq).most_common(5)}
json.dump(res, open(os.path.join(OUT, "levers.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
print(json.dumps({k: v for k, v in res.items() if k != "mod_configs"}, ensure_ascii=False, default=str)[:4000])
print("mods with configs:", len(cfgs)); [print("  ", k, v[:4]) for k, v in list(cfgs.items())[:40]]
