"""Какие моды из mods.cfg требуют RE_Kenshi / KenshiLib: описания Steam (GetPublishedFileDetails), названия, плагины в папках."""
import json, os, re, glob, urllib.request, urllib.parse
OUT = os.path.join(os.path.dirname(__file__), "out")
W = "C:/Program Files (x86)/Steam/steamapps/workshop/content/233860/"
lo = json.load(open(os.path.join(OUT, "final_lo.json"), encoding="utf-8"))
mods = lo["base"] + lo["wh"]
ids = [m["id"] for m in mods]
det = {}
for i in range(0, len(ids), 100):
    chunk = ids[i:i + 100]
    data = {"itemcount": len(chunk)}
    for k, x in enumerate(chunk): data[f"publishedfileids[{k}]"] = x
    req = urllib.request.Request("https://api.steampowered.com/ISteamRemoteStorage/GetPublishedFileDetails/v1/",
                                 data=urllib.parse.urlencode(data).encode())
    for d in json.load(urllib.request.urlopen(req, timeout=60))["response"]["publishedfiledetails"]:
        det[d["publishedfileid"]] = d
json.dump(det, open(os.path.join(OUT, "pfd_all.json"), "w", encoding="utf-8"), ensure_ascii=False)
RX = re.compile(r"re[_ ]?kenshi|kenshilib|kenshi ?lib\b|kenshilua|rek\b", re.I)
REQ = re.compile(r"requir|need|must|depend|necess|mandator|optional|necesit|нуж|обязат|требу|必须|需要|前置", re.I)
rows = []
for m in mods:
    d = det.get(m["id"], {}); desc = d.get("description", "") or ""; title = d.get("title", "") or ""
    folder = W + m["id"]
    plugin_files = [os.path.relpath(p, folder) for p in glob.glob(folder + "/**/*", recursive=True)
                    if os.path.isfile(p) and (p.lower().endswith((".dll", ".lua")) or os.path.basename(p).upper() == "RE_KENSHI.JSON")]
    hits = [l.strip() for l in desc.splitlines() if RX.search(l)]
    if not (hits or RX.search(title) or plugin_files):
        continue
    req_lines = [h for h in hits if REQ.search(h)]
    rows.append({"id": m["id"], "file": m["file"], "title": title, "title_hit": bool(RX.search(title)),
                 "plugins": plugin_files, "mentions": hits[:6], "requirement_lines": req_lines[:4],
                 "kenshilib": any(re.search(r"kenshilib|kenshi ?lib\b", h, re.I) for h in hits) or any("kenshilib" in p.lower() for p in plugin_files)})
json.dump(rows, open(os.path.join(OUT, "needs_rek.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("details fetched", len(det), "of", len(ids), "| candidates", len(rows))
for r in rows:
    print(f"\n== {r['id']} {r['file']} | {r['title']} | plugins={r['plugins'][:5]} | kenshilib={r['kenshilib']}")
    for h in r["mentions"][:5]: print("    ·", h[:220])
