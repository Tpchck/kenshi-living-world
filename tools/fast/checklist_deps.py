"""CHECKLIST п.2 и п.4: Required items модов из Steam + строки mods.cfg без мода на диске."""
import json, os, glob, urllib.request, urllib.parse
OUT = os.path.join(os.path.dirname(__file__), "out")
GAME = r"C:\Program Files (x86)\Steam\steamapps\common\Kenshi"
W = r"C:\Program Files (x86)\Steam\steamapps\workshop\content\233860"
cfg = [l for l in open(os.path.join(GAME, "data", "mods.cfg"), "rb").read().decode("utf-8").split("\r\n") if l]
on_disk = {}
for d in os.listdir(W):
    for f in glob.glob(os.path.join(W, d, "*.mod")): on_disk[os.path.basename(f)] = d
local = {os.path.basename(f) for f in glob.glob(os.path.join(GAME, "mods", "*", "*.mod"))}
missing = [l for l in cfg if l not in on_disk and l not in local]
ids = sorted({on_disk[l] for l in cfg if l in on_disk})
req = {}
for i in range(0, len(ids), 100):
    ch = ids[i:i + 100]; data = {"collectioncount": len(ch)}
    for k, x in enumerate(ch): data[f"publishedfileids[{k}]"] = x
    r = urllib.request.urlopen(urllib.request.Request("https://api.steampowered.com/ISteamRemoteStorage/GetCollectionDetails/v1/",
                               data=urllib.parse.urlencode(data).encode()), timeout=60)
    for c in json.load(r)["response"]["collectiondetails"]:
        req[c["publishedfileid"]] = [x["publishedfileid"] for x in c.get("children", [])]
have = set(ids)
need_missing = {k: [x for x in v if x not in have] for k, v in req.items() if any(x not in have for x in v)}
# имена недостающих
allmiss = sorted({x for v in need_missing.values() for x in v})
names = {}
if allmiss:
    data = {"itemcount": len(allmiss)}
    for k, x in enumerate(allmiss): data[f"publishedfileids[{k}]"] = x
    for d in json.load(urllib.request.urlopen(urllib.request.Request("https://api.steampowered.com/ISteamRemoteStorage/GetPublishedFileDetails/v1/",
                       data=urllib.parse.urlencode(data).encode()), timeout=60))["response"]["publishedfiledetails"]:
        names[d["publishedfileid"]] = d.get("title", "?")
pfd = json.load(open(os.path.join(OUT, "pfd_all.json"), encoding="utf-8"))
res = {"workshop_dirs": len(os.listdir(W)), "cfg_lines": len(cfg), "cfg_missing_on_disk": missing,
       "mods_with_required_items": sum(1 for v in req.values() if v),
       "required_missing": {k: [(x, names.get(x)) for x in v] for k, v in need_missing.items()}}
json.dump(res, open(os.path.join(OUT, "checklist_deps.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("workshop dirs", res["workshop_dirs"], "| cfg lines", len(cfg), "| missing on disk:", missing)
print("mods with Required items:", res["mods_with_required_items"], "| with unmet:", len(need_missing))
for k, v in need_missing.items():
    print(f"  {k} {pfd.get(k, {}).get('title', '?')[:50]} ← нужен: {[(x, names.get(x)) for x in v]}")
