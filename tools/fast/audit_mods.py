"""Аудит модов-кандидатов перед включением в mods.cfg: паспорт, зависимости, битые ссылки, коллизии sid,
пересечения по полям с основой/WH и с нашими KMM_*, пересечения файлов (одинаковые относительные пути), размер.
python -I -X utf8 tools/fast/audit_mods.py <id,id,...> [out.json]
Кандидаты ставятся условно после WH-слоя и перед KMM_* (как в будущем mods.cfg)."""
import collections
import glob
import json
import os
import sys

sys.path.insert(0, r"C:\KenshiModMap\tools")
sys.path.insert(0, r"C:\KenshiModMap\tools\fast")
import ctx  # noqa: E402
import kmod  # noqa: E402

W = r"C:\Program Files (x86)\Steam\steamapps\workshop\content\233860"
ROOT = r"C:\KenshiModMap"
ids = sys.argv[1].split(",")
out_path = sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, "tools", "fast", "out", "audit.json")
lo, van, base, wh = ctx.load()
kmm = [(m + ".mod", kmod.read(os.path.join(ROOT, "build", m, m + ".mod")), None)
       for m in ["KMM_Core", "KMM_Relics", "KMM_Wardrobe", "KMM_Economy", "KMM_Behavior", "KMM_Traces", "KMM_Tech", "KMM_Diplo", "KMM_Fix"]
       if os.path.exists(os.path.join(ROOT, "build", m, m + ".mod"))]
cand = []
for i in ids:
    for f in glob.glob(os.path.join(W, i, "*.mod")):
        cand.append((os.path.basename(f), kmod.read(f), i))
prior = van + base + wh
names_loaded = {n for n, _, _ in prior} | {n for n, _, _ in cand}

# кто что трогает (поля) в основе/WH и в KMM
fields = collections.defaultdict(lambda: collections.defaultdict(set))   # sid -> field -> {mod}
setval = collections.defaultdict(dict)                                    # sid -> key -> (mod, value) последний
for n, m, _ in prior:
    for it in m.items:
        for k, v in it.values.items():
            fields[it.sid]["v:" + k].add(n); setval[it.sid][k] = (n, v)
        for c in it.refs:
            fields[it.sid]["r:" + c].add(n)
kfields = collections.defaultdict(lambda: collections.defaultdict(set))
for n, m, _ in kmm:
    for it in m.items:
        for k in it.values:
            kfields[it.sid]["v:" + k].add(n)
        for c in it.refs:
            kfields[it.sid]["r:" + c].add(n)
M = {}
for _, m, _ in prior + cand:
    kmod.apply(M, m)
defined_prior = {it.sid for _, m, _ in prior for it in m.items if it.change == kmod.CHANGE_NEW} | {it.sid for _, m, _ in van for it in m.items}

# файлы: относительные пути всех модов LO
file_owner = collections.defaultdict(list)
for b in lo["base"] + lo["wh"]:
    d = os.path.join(W, b["id"])
    for dp, _, fs in os.walk(d):
        for f in fs:
            if not f.endswith((".mod", ".info", ".img")):
                file_owner[os.path.relpath(os.path.join(dp, f), d).lower()].append(b["file"])

res = []
for n, m, wid in cand:
    d = os.path.join(W, wid)
    size = sum(os.path.getsize(os.path.join(dp, f)) for dp, _, fs in os.walk(d) for f in fs)
    new = [it for it in m.items if it.change == kmod.CHANGE_NEW]
    chg = [it for it in m.items if it.change != kmod.CHANGE_NEW]
    deps = [x for x in m.header.dependencies if x not in names_loaded]
    collide = [it.sid for it in new if it.sid in defined_prior]
    broken = collections.Counter()
    for it in m.items:
        for c, rs in it.refs.items():
            for r in rs:
                if (r.v0, r.v1, r.v2) != kmod.DELETED_REF and r.target not in M:
                    broken[(it.type_name, c)] += 1
    over_vals, over_mods, add_lists = [], collections.Counter(), 0
    for it in chg:
        for k, v in it.values.items():
            prev = setval[it.sid].get(k)
            if prev and prev[0] not in ctx.VANILLA and prev[1] != v:
                over_vals.append((it.type_name, M[it.sid].name if it.sid in M else it.sid, k, prev[0]))
                over_mods[prev[0]] += 1
        for c in it.refs:
            if fields[it.sid].get("r:" + c):
                add_lists += 1
    kmm_over = collections.Counter()
    for it in m.items:
        for k in it.values:
            for km in kfields[it.sid].get("v:" + k, ()):
                kmm_over[km] += 1
        for c in it.refs:
            for km in kfields[it.sid].get("r:" + c, ()):
                kmm_over[km] += 1
    files = [os.path.relpath(os.path.join(dp, f), d).lower() for dp, _, fs in os.walk(d) for f in fs if not f.endswith((".mod", ".info", ".img"))]
    file_clash = collections.Counter(o for f in files for o in file_owner.get(f, []))
    res.append({"id": wid, "file": n, "mb": round(size / 1e6, 1), "ftype": m.ftype, "items": len(m.items),
                "new_by_type": dict(collections.Counter(i.type_name for i in new).most_common(8)), "changed": len(chg),
                "changed_by_type": dict(collections.Counter(i.type_name for i in chg).most_common(6)),
                "deps": m.header.dependencies, "missing_deps": deps, "sid_collisions": len(collide), "broken_refs": {f"{a}/{b}": c for (a, b), c in broken.most_common(6)},
                "overwrites_base_values": len(over_vals), "overwritten_mods": dict(over_mods.most_common(6)), "overwrite_examples": over_vals[:6],
                "shared_ref_lists": add_lists, "touches_kmm_fields": dict(kmm_over), "file_clashes": dict(file_clash.most_common(6)),
                "armour": sum(1 for i in new if i.type_name == "ARMOUR"), "weapons": sum(1 for i in new if i.type_name in ("WEAPON", "CROSSBOW"))})
json.dump(res, open(out_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
for r in res:
    print(f"{r['id']} {r['file'][:30]:<30} {r['mb']:6.1f}MB new={sum(r['new_by_type'].values()):<4} chg={r['changed']:<4} arm={r['armour']:<3} wpn={r['weapons']:<3} "
          f"missdeps={r['missing_deps']} coll={r['sid_collisions']} broken={sum(r['broken_refs'].values())} overw={r['overwrites_base_values']} kmm={r['touches_kmm_fields']} files={sum(r['file_clashes'].values())}")
