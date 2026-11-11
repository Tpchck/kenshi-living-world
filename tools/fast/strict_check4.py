import sys, re, collections
sys.path.insert(0, r"C:\KenshiModMap\tools"); sys.path.insert(0, r"C:\KenshiModMap\tools\fast")
import kmod, ctx
lo, van, base, wh = ctx.load()
log = open(r"C:\KenshiModMap\logs\run_2026-11-11_2126\kenshi_info.log", encoding="utf-8", errors="replace").read()
badsids = set(re.findall(r"Item .+? \(([^()]+)\) modified by KMM_Glue does not exist", log))
tk = next(m for n, m, _ in base if n == "Talkative Kenshi.mod")
print("TK type", tk.ftype, "items", len(tk.items), "deps", tk.header.dependencies[:6], "refs", tk.header.references[:6])
new = [it for it in tk.items if it.change == 0]
bad = [it for it in new if it.sid in badsids]; good = [it for it in new if it.sid not in badsids]
print("TK new", len(new), "bad", len(bad), "ok", len(good))
f = lambda L: collections.Counter((it.type_name, len(it.values) > 0, it.sid.split("-", 1)[1] in [x[0] for x in base + van] or it.sid.split('-',1)[1] == 'Talkative Kenshi.mod') for it in L).most_common(6)
print("bad: (type, has values, sid-mod loaded)", f(bad)); print("ok :", f(good))
b = bad[0]; print("example", b.sid, b.name, "vals", list(b.values)[:6], "refs", {k: len(v) for k, v in b.refs.items()}, "save", b.save_data)
loaded = {x[0] for x in base + van}
allmods_newforeign = collections.Counter()
for n, m, _ in base:
    for it in m.items:
        if it.change == 0 and "-" in it.sid and it.sid.split("-", 1)[1] not in loaded and it.sid.split("-",1)[1] != n:
            allmods_newforeign[n] += 1
print("mods with NEW records whose sid-mod is not loaded:", allmods_newforeign.most_common(8))
