import sys, re, collections
sys.path.insert(0, r"C:\KenshiModMap\tools"); sys.path.insert(0, r"C:\KenshiModMap\tools\fast")
import kmod, ctx
lo, van, base, wh = ctx.load()
log = open(r"C:\KenshiModMap\logs\run_2026-11-11_2126\kenshi_info.log", encoding="utf-8", errors="replace").read()
bad = re.findall(r"Item (.+?) \(([^()]+)\) modified by KMM_Glue does not exist", log)
badsids = {s for _, s in bad}
print("glue warned sids", len(badsids))
touch = collections.defaultdict(list)
for n, m, _ in van + base + wh:
    for it in m.items:
        if it.sid in badsids: touch[it.sid].append((n[:28], it.change, it.type_name, "DEL" if it.values.get("DELETED") else ""))
for s in list(badsids)[:8]: print(s, touch[s])
pat = collections.Counter(tuple(sorted({(c, d) for _, c, _, d in touch[s]})) for s in badsids)
print("patterns (change,del) in chain:", pat.most_common(6))
