r"""Аудит связности фракций: используемые отрядами/городами FACTION итоговой цепочки (ctx.M + build/KMM_*/*.mod).
Считает до (без KMM_*) и после (с KMM_*): число отношений, связь с ключевыми ванильными, изолированные, противоречия матрицы.
python toolsworld_audit.py  -> печать + data\world_audit.json (только чтение)"""
import collections
import json
import os
import sys

sys.path.insert(0, r"C:\KenshiModMap\tools")
sys.path.insert(0, r"C:\KenshiModMap\tools\build")
sys.path.insert(0, r"C:\KenshiModMap\tools\streams")
import kmod  # noqa: E402
import kmm_build  # noqa: E402
import behavior  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

KEY = ["The Holy Nation", "United Cities", "Shek Kingdom", "Traders Guild", "Tech Hunters", "Flotsam Ninjas", "Anti-Slavers",
       "Western Hive", "Southern Hive", "Dust Bandits", "Starving Bandits", "Cannibals", "Fogmen", "Skeleton Legion",
       "Second Empire", "Black Dragon Ninjas"]


def snapshot(M, origin, rejected, wr):
    fac = [f for f in M.values() if f.type_name == "FACTION" and f.sid not in rejected]
    used = set()
    for t in M.values():
        if t.type_name in ("SQUAD_TEMPLATE", "TOWN") and t.sid not in rejected:
            used.update(r.target for r in t.refs.get("faction", []))
    key_sids = {f.sid for f in fac if f.name in KEY}
    arch_map = {}
    rows, isolated, contra = [], [], []
    core = set(wr["core_origins"])
    mat = {}
    for k, v in wr["matrix"].items():
        a, b = k.split("|")
        mat[(a, b)] = mat[(b, a)] = v
    byid = {f.sid: f for f in fac}
    for f in fac:
        if f.sid not in used:
            continue
        a = behavior.archetype_of(f, origin, wr)
        arch_map[f.sid] = a
        rels = {r.target: r.v0 for r in f.refs.get("relations", [])}
        dflt = f.values.get("default relation", 0)
        keyn = sum(1 for t in rels if t in key_sids)
        part = bool(a) and a not in wr["skip_archetypes"] and f.values.get("fundamental type", 4) != 0
        row = {"name": f.name, "mod": origin.get(f.sid, "KMM"), "archetype": a, "participant": part,
               "relations": len(rels), "key_relations": keyn, "default_relation": dflt}
        rows.append(row)
        if part and keyn == 0 and dflt == 0:
            isolated.append(f.name + " [" + row["mod"] + "]")
        if part:
            for t, v in rels.items():
                g = byid.get(t)
                if g is None or g.sid not in used or arch_map.get(g.sid, behavior.archetype_of(g, origin, wr)) is None:
                    continue
                b = arch_map.get(g.sid) or behavior.archetype_of(g, origin, wr)
                m = mat.get((a, b))
                if m is None or (origin.get(f.sid) in core and origin.get(t) in core):
                    continue
                if (m <= -40 and v > -10) or (m >= 40 and v <= -40):
                    contra.append(f"{f.name} -> {g.name}: {v} (матрица {a}|{b} = {m})")
    return {"used_factions": len(rows), "participants": sum(r["participant"] for r in rows), "isolated": sorted(isolated),
            "contradictions": len(contra), "contradiction_samples": contra[:40],
            "by_archetype": dict(collections.Counter(r["archetype"] or "(не участвует)" for r in rows)),
            "zero_relations_participants": sorted(r["name"] for r in rows if r["participant"] and r["relations"] == 0)}, rows


def main():
    ctx = kmm_build.Ctx()
    wr = json.load(open(r"C:\KenshiModMap\rules\streams\behavior.json", encoding="utf-8"))["world_relations"]
    before, rows_b = snapshot(ctx.M, ctx.origin, ctx.rejected, wr)
    M = dict(ctx.M)
    origin = dict(ctx.origin)
    for d in sorted(os.listdir(r"C:\KenshiModMap\build")):
        p = os.path.join(r"C:\KenshiModMap\build", d, d + ".mod")
        if d.startswith("KMM_") and os.path.exists(p):
            m = kmod.read(p)
            kmod.apply(M, m)
            for it in m.items:
                origin.setdefault(it.sid, d)
    after, rows_a = snapshot(M, origin, ctx.rejected, wr)
    out = {"key_vanilla": KEY, "before_KMM": before, "after_KMM": after, "factions_after": rows_a}
    json.dump(out, open(r"C:\KenshiModMap\data\world_audit.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    for k, v in (("до KMM", before), ("после KMM", after)):
        print(f"{k}: используемых {v['used_factions']}, участвуют {v['participants']}, изолированных {len(v['isolated'])}, "
              f"без отношений {len(v['zero_relations_participants'])}, противоречий {v['contradictions']}")
    print("изолированные (после):", after["isolated"][:40])
    print("архетипы:", after["by_archetype"])


if __name__ == "__main__":
    main()
