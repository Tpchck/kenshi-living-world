import sys, re, collections
sys.path.insert(0, r"C:\KenshiModMap\tools"); sys.path.insert(0, r"C:\KenshiModMap\tools\fast")
import kmod, ctx
lo, van, base, wh = ctx.load()
glue = kmod.read(r"C:\KenshiModMap\build\KMM_Glue\KMM_Glue.mod")
M = {}
for _, m, _ in van: kmod.apply(M, m)
pred = collections.Counter()
for n, m, _ in base + wh + [("KMM_Glue.mod", glue, None)]:
    for s in kmod.apply(M, m, strict=True): pred[n[:-4]] += 1
log = open(r"C:\KenshiModMap\logs\run_2026-11-11_2126\kenshi_info.log", encoding="utf-8", errors="replace").read()
real = collections.Counter(re.findall(r"modified by (.+?) does not exist", log))
keys = set(pred) | set(real)
diff = {k: (pred[k], real[k]) for k in keys if pred[k] != real[k]}
print("predicted total", sum(pred.values()), "log total", sum(real.values()), "| mods matching", len(keys) - len(diff), "of", len(keys))
print("mismatches:", sorted(diff.items(), key=lambda x: -abs(x[1][0]-x[1][1]))[:10])
