import sys, re, collections
sys.path.insert(0, r"C:\KenshiModMap\tools"); sys.path.insert(0, r"C:\KenshiModMap\tools\fast")
import kmod, ctx
lo, van, base, wh = ctx.load()
glue = kmod.read(r"C:\KenshiModMap\build\KMM_Glue\KMM_Glue.mod")
mods = base + wh + [("KMM_Glue.mod", glue, None)]
defined = set(); deleted = set()
for _, m, _ in van:
    defined |= {it.sid for it in m.items}
for n, m, _ in mods:
    for it in m.items:
        if it.values.get("DELETED") is True: deleted.add(it.sid)
        elif it.change == kmod.CHANGE_NEW: defined.add(it.sid)
log = open(r"C:\KenshiModMap\logs\run_2026-11-11_2126\kenshi_info.log", encoding="utf-8", errors="replace").read()
real = collections.Counter(re.findall(r"modified by (.+?) does not exist", log))
for name, rule in [("undefined", lambda s: s not in defined), ("undefined|deleted", lambda s: s not in defined or s in deleted)]:
    pred = collections.Counter()
    for n, m, _ in mods:
        for it in m.items:
            if it.change != kmod.CHANGE_NEW and it.values.get("DELETED") is not True and rule(it.sid): pred[n[:-4]] += 1
    keys = set(pred) | set(real)
    diff = {k: (pred[k], real[k]) for k in keys if pred[k] != real[k]}
    print(f"{name}: predicted {sum(pred.values())} vs log {sum(real.values())}; mods match {len(keys)-len(diff)}/{len(keys)}; worst {sorted(diff.items(), key=lambda x: -abs(x[1][0]-x[1][1]))[:6]}")
