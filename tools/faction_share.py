r"""Доли спавна по фракциям/архетипам по биомам: только ваниль vs итоговая цепочка (ctx.M + build\KMM_*\*.mod). Только чтение.
python tools\faction_share.py [--cache]  -> печать + data\faction_share.json
Спавн биома = BIOME_GROUP «homeless spawns» (отряды) и «nests» (логова/звери): вес v0 x размер отряда (как budget.spawn_share).
Логово (nests) = TOWN: вес x размеры отрядов residents/roaming/bar. Архетип фракции — behavior.archetype_of (rules\streams\behavior.json world_relations); fundamental type 0 / monster -> «fauna/monster»."""
import collections
import json
import os
import pickle
import sys

sys.path.insert(0, r"C:\KenshiModMap\tools")
sys.path.insert(0, r"C:\KenshiModMap\tools\build")
sys.path.insert(0, r"C:\KenshiModMap\tools\streams")
import kmod  # noqa: E402
import balance_lib  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
ROOT = r"C:\KenshiModMap"
VANILLA = ("gamedata.base", "rebirth.mod", "Newwworld.mod", "Dialogue.mod")
CACHE = os.path.join(ROOT, "state", "fs_cache.pkl")
DEL = 2147483647
SKIP_ARCH = ("monster",)


def squad_size(sq):
    return max(1, sum(max(r.v0, r.v1) for c in ("leader", "squad", "squad2") for r in sq.refs.get(c, [])))


def arch_name_old(f, wr):
    from behavior import archetype_of
    if f is None:
        return "none"
    if f.values.get("fundamental type", 4) == 0:
        return "fauna"
    a = archetype_of(f, None, wr)
    return "monster" if a == "monster" else (a or "notreal")


def extract(M, origin, wr):
    """компактные данные: биомы, шаблоны отрядов, фракции"""
    out = {"biomes": {}, "squads": {}, "towns": {}}
    fcache = {}
    for it in M.values():
        if it.type_name == "BIOME_GROUP":
            out["biomes"][it.sid] = {"name": it.name, "cats": {c: [(r.target, r.v0) for r in it.refs.get(c, []) if (r.v0, r.v1, r.v2) != (DEL,) * 3]
                                                              for c in ("nests", "homeless spawns")}}
    fac = {it.sid: it for it in M.values() if it.type_name == "FACTION"}
    for it in M.values():
        if it.type_name == "SQUAD_TEMPLATE":
            f = fac.get((it.refs.get("faction") or [None])[0].target) if it.refs.get("faction") else None
            out["squads"][it.sid] = {"name": it.name, "size": squad_size(it), "fac": f.name if f else None, "arch": balance_lib.squad_arch(M, it, wr, fcache),
                                     "origin": origin.get(it.sid, "KMM")}
        elif it.type_name == "TOWN":
            f = fac.get(it.refs["faction"][0].target) if it.refs.get("faction") else None
            pops = {}
            for c in ("residents", "roaming squads", "bar squads"):
                pops[c] = [(r.target, r.v0, r.v1) for r in it.refs.get(c, []) if (r.v0, r.v1, r.v2) != (DEL,) * 3]
            out["towns"][it.sid] = {"name": it.name, "fac": f.name if f else None, "pops": pops}
    uc = {}
    for sid in out["towns"]:
        out["towns"][sid]["units"] = [(a_, sz, "") for a_, sz in balance_lib.entry_units(M, sid, wr, fcache, uc)]
    return out


def load(use_cache):
    if use_cache and os.path.exists(CACHE):
        return pickle.load(open(CACHE, "rb"))
    import kmm_build
    ctx = kmm_build.Ctx()
    wr = json.load(open(ROOT + r"\rules\streams\behavior.json", encoding="utf-8"))["world_relations"]
    Mv = {}
    for n, m, _ in ctx.layers:
        if n in VANILLA:
            kmod.apply(Mv, m)
    ov = {}
    for n, m, _ in ctx.layers:
        if n in VANILLA:
            for it in m.items:
                ov.setdefault(it.sid, n)
    Mf = dict(ctx.M)
    for d in sorted(os.listdir(ROOT + r"\build")):
        p = os.path.join(ROOT, "build", d, d + ".mod")
        if d.startswith("KMM_") and os.path.exists(p):
            kmod.apply(Mf, kmod.read(p))
    res = {"vanilla": extract(Mv, ov, wr), "final": extract(Mf, ctx.origin, wr)}
    pickle.dump(res, open(CACHE, "wb"))
    return res


def shares(d, cat_filter=None):
    """{biome: {arch: доля}}, мир {arch: доля}; вес = v0 x размер (для nests — v0 x размер тоже)"""
    per = {}
    for b in d["biomes"].values():
        acc = collections.Counter()
        for cat, rs in b["cats"].items():
            if cat_filter and cat not in cat_filter:
                continue
            for t, w in rs:
                if w <= 0:
                    continue
                if t in d["squads"]:
                    sq = d["squads"][t]
                    acc[sq["arch"]] += w * sq["size"]
                elif t in d["towns"]:
                    for a, sz, _o in d["towns"][t]["units"]:
                        acc[a] += w * sz
        if acc:
            per.setdefault(b["name"], collections.Counter()).update(acc)
    world = collections.Counter()
    for c in per.values():
        world.update(c)
    return per, world


GROUP = {"fauna": "wild", "monster": "wild", "none": "other", "notreal": "other"}


def grp(c):
    o = collections.Counter()
    for k, v in c.items():
        o[GROUP.get(k, k)] += v
    return o


def norm(c):
    s = sum(c.values()) or 1
    return {k: v / s for k, v in c.items()}


def main():
    res = load("--cache" in sys.argv)
    out = {}
    cat_ = None
    for cf in (("homeless spawns",), ("nests",)):
        out[cf[0]] = {}
        for variant in ("vanilla", "final"):
            d = res[variant]
            per, world = shares(d, cf)
            out[cf[0]][variant] = {"world": norm(grp(world)), "biomes": {b: norm(grp(c)) for b, c in per.items()}}
    out.update({"vanilla": out["homeless spawns"]["vanilla"], "final": out["homeless spawns"]["final"]})
    for cn in ("homeless spawns", "nests"):
        print(cn, "ваниль:", {k: round(v, 3) for k, v in sorted(out[cn]["vanilla"]["world"].items(), key=lambda x: -x[1])})
        print(cn, "итог  :", {k: round(v, 3) for k, v in sorted(out[cn]["final"]["world"].items(), key=lambda x: -x[1])})
    # отклонения: доля архетипа в биоме final vs vanilla (относительно)
    dev = []
    for b, cv in out["vanilla"]["biomes"].items():
        cf = out["final"]["biomes"].get(b, {})
        for a in set(cv) | set(cf):
            v, f = cv.get(a, 0), cf.get(a, 0)
            if max(v, f) < 0.03:
                continue
            ratio = (f / v) if v else 99.0
            if ratio > 1.5 or ratio < 1 / 1.5:
                dev.append({"biome": b, "arch": a, "vanilla": round(v, 3), "final": round(f, 3), "ratio": round(ratio, 2)})
    out["deviations"] = sorted(dev, key=lambda x: -abs(__import__("math").log(max(x["ratio"], 0.01))))
    # плотные биомы (>= 8 ванильных записей категории): сравнение осмысленно; допуск +-25 % (WH-архетипы — бюджет, не считаем)
    dense = {}
    for cn in ("homeless spawns", "nests"):
        nv = {b["name"]: len(b["cats"][cn]) for b in res["vanilla"]["biomes"].values()}
        bad, tot = [], 0
        for bn, cv in out[cn]["vanilla"]["biomes"].items():
            if nv.get(bn, 0) < 8:
                continue
            cf = out[cn]["final"]["biomes"].get(bn, {})
            for a in set(cv) | set(cf):
                if a in ("chaos", "xeno", "imperium"):
                    continue
                v_, f_ = cv.get(a, 0), cf.get(a, 0)
                if max(v_, f_) < 0.05:
                    continue
                tot += 1
                if not (0.75 <= (f_ / v_ if v_ else 99) <= 1.25):
                    bad.append({"biome": bn, "arch": a, "vanilla": round(v_, 3), "final": round(f_, 3)})
        dense[cn] = {"compared": tot, "outside_25pct": len(bad), "items": sorted(bad, key=lambda x: -abs(x["final"] - x["vanilla"]))[:30]}
    out["dense_biomes"] = dense
    for cn in dense:
        print("плотные биомы", cn, "сравнено", dense[cn]["compared"], "вне +-25%:", dense[cn]["outside_25pct"])
    json.dump(out, open(ROOT + r"\data\faction_share.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("мир ваниль:", {k: round(v, 3) for k, v in sorted(out["vanilla"]["world"].items(), key=lambda x: -x[1])})
    print("мир итог  :", {k: round(v, 3) for k, v in sorted(out["final"]["world"].items(), key=lambda x: -x[1])})
    print("отклонений биом/архетип >1.5x:", len(dev))
    for x in out["deviations"][:40]:
        print(" ", x)


if __name__ == "__main__":
    main()
