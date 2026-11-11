import sys, re, collections
sys.path.insert(0, r"C:\KenshiModMap\tools"); sys.path.insert(0, r"C:\KenshiModMap\tools\fast")
import kmod, ctx
lo, van, base, wh = ctx.load()
glue = kmod.read(r"C:\KenshiModMap\build\KMM_Glue\KMM_Glue.mod")
mods = base + wh + [("KMM_Glue.mod", glue, None)]
loaded = {n for n, _, _ in van + mods}
log = open(r"C:\KenshiModMap\logs\run_2026-11-11_2126\kenshi_info.log", encoding="utf-8", errors="replace").read()
real = collections.Counter(re.findall(r"modified by (.+?) does not exist", log))
realsid = collections.defaultdict(set)
for name, sid, mod in re.findall(r"Item (.+?) \(([^()]+)\) modified by (.+?) does not exist", log): realsid[mod].add(sid)
sfx = lambda s: s.split("-", 1)[1] if re.match(r"^\d+-", s) else None
# H5: запись существует, если она есть в core или её создал NEW в моде, где суффикс sid загружен (или это сам мод)
exists = {it.sid for _, m, _ in van for it in m.items}
pred = collections.defaultdict(set)
for n, m, _ in mods:
    for it in m.items:
        if it.values.get("DELETED") is True: exists.discard(it.sid); continue
        sx = sfx(it.sid)
        foreign_unloaded = sx is not None and sx not in loaded
        if it.change == kmod.CHANGE_NEW:
            if not foreign_unloaded: exists.add(it.sid)
        elif it.sid not in exists:
            if foreign_unloaded or True: pred[n[:-4]].add(it.sid)
tot_p = sum(len(v) for v in pred.values())
hit = sum(len(pred[k] & realsid[k]) for k in realsid)
print(f"H5 sequential: predicted {tot_p}, log {sum(real.values())}, overlap {hit}")
for k in ["KMM_Glue", "Kaizo", "Social lives (United Cities) ENG", "TK Clean Fix"]:
    print(f"   {k}: pred {len(pred.get(k, ()))} log {len(realsid.get(k, ()))} overlap {len(pred.get(k, set()) & realsid.get(k, set()))}")
# only foreign-unloaded changes
pred2 = {k: {s for s in v if sfx(s) and sfx(s) not in loaded} for k, v in pred.items()}
print("H5 restricted to foreign-unloaded suffix:", sum(len(v) for v in pred2.values()), "overlap", sum(len(pred2.get(k, set()) & realsid[k]) for k in realsid))
