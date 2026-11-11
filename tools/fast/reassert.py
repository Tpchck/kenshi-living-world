"""Где WH-слой (грузится позже) перетирает значения, явно выставленные модами основы. → out/reassert.json"""
import json, sys, struct, collections
sys.path.insert(0, r"C:\KenshiModMap\tools"); sys.path.insert(0, r"C:\KenshiModMap\tools\fast")
import kmod, ctx
lo, van, base, wh = ctx.load()
f32 = lambda v: struct.unpack("<f", struct.pack("<f", v))[0] if isinstance(v, float) else v
mb = {}
for _, m, _ in van + base: kmod.apply(mb, m)
base_set = collections.defaultdict(dict)   # sid -> key -> (mod, value) последний мод основы, выставивший ключ
for n, m, _ in base:
    for it in m.items:
        for k, v in it.values.items(): base_set[it.sid][k] = (n, v)
mf = {s: kmod._copy(i) for s, i in mb.items()}
for _, m, _ in wh: kmod.apply(mf, m)
out = []
for sid, keys in base_set.items():
    if sid not in mf: continue
    for k, (n, v) in keys.items():
        nv = mf[sid].values.get(k)
        if nv is not None and f32(nv) != f32(v):
            who = [wn for wn, wm, _ in wh if any(it.sid == sid and k in it.values for it in wm.items)]
            out.append({"sid": sid, "type": mf[sid].type_name, "name": mf[sid].name, "key": k, "base_mod": n,
                        "base_value": v if not isinstance(v, tuple) else list(v), "wh_value": nv if not isinstance(nv, tuple) else list(nv), "wh_mod": who[-1] if who else "?"})
# удалённые WH ссылки, добавленные основой
dels = []
for n, m, _ in wh:
    for it in m.items:
        for cat, refs in it.refs.items():
            for r in refs:
                if (r.v0, r.v1, r.v2) == kmod.DELETED_REF and any(x.target == r.target for x in mb.get(it.sid, kmod.Item(0,0,"","")).refs.get(cat, [])):
                    dels.append({"wh": n, "sid": it.sid, "name": mf.get(it.sid, it).name, "cat": cat, "target": r.target})
json.dump({"values": out, "deleted_refs": dels}, open(ctx.OUT + "/reassert.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
print("WH overwrote base-set values:", len(out), "| WH deleted base refs:", len(dels))
c = collections.Counter((o["wh_mod"], o["base_mod"]) for o in out)
for (w, b), k in c.most_common(15): print(f"  {k:4} {w} ← перетирает {b}")
for o in out[:10]: print("   ", o["type"], o["name"], o["key"], o["base_value"], "→", o["wh_value"])
