"""Аудит локаций (TOWN) итоговой цепочки модов + потоков KMM: пустышки, битые ссылки, дубли имён. Только чтение.
python tools\\town_audit.py  -> печать + data\\town_audit.json"""
import collections
import json
import os
import sys

sys.path.insert(0, r"C:\KenshiModMap\tools")
sys.path.insert(0, r"C:\KenshiModMap\tools\build")
import kmod  # noqa: E402
import kmm_build  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

POP = ("residents", "roaming squads", "bar squads")


def main():
    ctx = kmm_build.Ctx()
    M = dict(ctx.M)
    for d in sorted(os.listdir(r"C:\KenshiModMap\build")):
        p = os.path.join(r"C:\KenshiModMap\build", d, d + ".mod")
        if d.startswith("KMM_") and os.path.exists(p):
            kmod.apply(M, kmod.read(p))
    towns = [t for t in M.values() if t.type_name == "TOWN" and t.sid not in ctx.rejected]
    overrides = {r.target for t in towns for r in t.refs.get("override town", [])}
    out = {"total": len(towns), "empty": [], "broken_refs": [], "dup_names": [], "no_faction": []}
    names = collections.Counter(t.name for t in towns)
    for t in towns:
        is_override = t.sid in overrides or "(override)" in (t.name or "").lower()
        bad = [(k, r.target) for k, v in t.refs.items() for r in v if r.target not in M and r.v0 != 2147483647]
        if bad:
            out["broken_refs"].append({"sid": t.sid, "name": t.name, "mod": ctx.origin.get(t.sid, "KMM"), "refs": bad[:6]})
        pop = sum(len(t.refs.get(k, [])) for k in POP)
        if not pop and not t.refs.get("loot spawn") and not is_override and not t.refs.get("override town"):
            out["empty"].append({"sid": t.sid, "name": t.name, "mod": ctx.origin.get(t.sid, "KMM"), "refs": sorted(t.refs)})
        if not t.refs.get("faction") and pop:
            out["no_faction"].append({"sid": t.sid, "name": t.name, "mod": ctx.origin.get(t.sid, "KMM")})
    out["dup_names"] = sorted(n for n, c in names.items() if c > 1 and n and "(override)" not in n.lower())
    json.dump(out, open(r"C:\KenshiModMap\data\town_audit.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"локаций: {out['total']}, пустых: {len(out['empty'])}, с битыми ссылками: {len(out['broken_refs'])}, "
          f"без фракции (с населением): {len(out['no_faction'])}, дублей имён: {len(out['dup_names'])}")
    by_mod = collections.Counter(e["mod"] for e in out["empty"])
    print("пустые по модам:", by_mod.most_common(12))
    for e in out["broken_refs"][:10]:
        print("  битые:", e["name"], e["mod"], e["refs"][:3])


if __name__ == "__main__":
    main()
