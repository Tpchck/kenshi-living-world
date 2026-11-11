import json, sys
sys.path.insert(0, r"C:\KenshiModMap\tools"); sys.path.insert(0, r"C:\KenshiModMap\tools\fast")
import kmod, ctx
a = json.load(open(ctx.OUT + "/wh_analysis.json", encoding="utf-8"))
real = [o for o in a["overlaps"] if o["same_fields"]]
print("value-field overwrites:", len(real))
for o in real[:30]: print("  ", o["wh"], "|", o["type"], o["name"], "|", o["other"], o["same_fields"][:6])
lo, van, base, wh = ctx.load()
allm = van + base + wh
for sid in ["9-mapdata", "11-40K Necrons.mod", "139-TEXT TEXTURE.mod"]:
    print("==", sid)
    for n, m, _ in allm:
        for it in m.items:
            if it.sid == sid: print(f"   {n[:34]:<34} change={it.change} vals={list(it.values)[:8]} refs={list(it.refs)} inst={len(it.instances)}")
