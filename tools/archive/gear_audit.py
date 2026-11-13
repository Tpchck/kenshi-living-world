r"""Аудит рассинхрона тира снаряжения и статов NPC (BALANCE). Только чтение.
python tools\gear_audit.py [--cache]  -> печать + data\gear_audit.json
Тир статов — по CHARACTER «combat stats» (ванильные ориентиры: голодный бандит 5-20, охрана 25-40, элита 45-65, боссы 70+):
T0 <22, T1 22-44, T2 45-69, T3 >=70. Тир снаряжения — среднее (по весу v1 в слоте) тиров ARMOUR из data\catalog.json по слотам
hat/body/legs/boots/shirt. Рассинхрон: |снаряжение - статы| >= 1.5 (т.е. 2+ тира). Намеренные исключения (дикари, силовая броня,
уникальные) считаются отдельно."""
import collections
import json
import os
import pickle
import re
import sys

sys.path.insert(0, r"C:\KenshiModMap\tools")
sys.path.insert(0, r"C:\KenshiModMap\tools\build")
import kmod  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
ROOT = r"C:\KenshiModMap"
CACHE = os.path.join(ROOT, "state", "gear_cache.pkl")
SLOTS = ("armour:hat", "armour:body", "armour:legs", "armour:boots", "armour:shirt")
T = {"T0": 0, "T1": 1, "T2": 2, "T3": 3}


def stat_tier(c):
    cs = int(c.values.get("combat stats", 0) or 0)
    return 0 if cs < 22 else 1 if cs < 45 else 2 if cs < 70 else 3


def equip_tier(clothing, cat):
    per = {}
    for sid, w in clothing:
        x = cat.get(sid)
        if x and x["group"] in SLOTS:
            per.setdefault(x["group"], []).append((T[x["tier"]], max(1, w)))
    if not per:
        return None
    return sum(sum(t * w for t, w in v) / sum(w for _, w in v) for v in per.values()) / len(per)


def chars_of(M, ctx_origin=None):
    out = {}
    for c in M.values():
        if c.type_name == "CHARACTER" and c.refs.get("clothing"):
            out[c.sid] = (c.name, stat_tier(c), bool(c.values.get("unique")), [(r.target, r.v1) for r in c.refs["clothing"]],
                          M[c.refs["faction"][0].target].name if c.refs.get("faction") and c.refs["faction"][0].target in M else None)
    return out


def audit(chars, cat, savage_fac, pa_rx):
    res = collections.Counter()
    bad = []
    for sid, (name, st, uniq, cl, fac) in chars.items():
        et = equip_tier(cl, cat)
        if et is None:
            continue
        res["chars"] += 1
        d = et - min(st, 2)   # T3 — реликты, массовая экипировка ограничена T2
        if abs(d) < 1.5:
            continue
        intended = uniq or "[KMM" in (name or "") or fac in savage_fac or re.search(r"skeleton|robot|bot|machine|drone|golem|variant0|mk\s?ii", name or "", re.I) or any(re.search(pa_rx, (cat.get(s, {}).get("name") or ""), re.I) for s, _ in cl if cat.get(s, {}).get("group") == "armour:body")
        res["intended" if intended else ("too_strong" if d > 0 else "too_weak")] += 1
        if not intended and len(bad) < 40:
            bad.append((name, fac, st, round(et, 2)))
    res["desync"] = res["too_strong"] + res["too_weak"]
    return dict(res), bad


def main():
    if "--cache" in sys.argv and os.path.exists(CACHE):
        data = pickle.load(open(CACHE, "rb"))
    else:
        import kmm_build
        ctx = kmm_build.Ctx()
        data = {"mods": chars_of(ctx.M)}
        Mf = dict(ctx.M)
        for d in sorted(os.listdir(ROOT + r"\build")):
            p = os.path.join(ROOT, "build", d, d + ".mod")
            if d.startswith("KMM_") and os.path.exists(p):
                kmod.apply(Mf, kmod.read(p))
        data["kmm"] = chars_of(Mf)
        pickle.dump(data, open(CACHE, "wb"))
    cat = {x["sid"]: x for x in json.load(open(ROOT + r"\data\catalog.json", encoding="utf-8"))["items"]}
    wr = json.load(open(ROOT + r"\rules\streams\wardrobe.json", encoding="utf-8"))
    sav = set(wr["context"]["lore_hard"]["savage"]["factions"])
    pa_rx = wr["context"]["lore_hard"]["power_armor"]["name_rx"]
    out = {}
    for k in ("mods", "kmm"):
        out[k], bad = audit(data[k], cat, sav, pa_rx)
        out[k + "_samples"] = bad
        print(k, out[k])
    json.dump(out, open(ROOT + r"\data\gear_audit.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
