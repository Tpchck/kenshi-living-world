"""Офлайн-оценка доли модовых вещей у ванильных CHARACTER из SQUAD_TEMPLATE (WARD_SHARE).
python -I -X utf8 tools/ward_share_eval.py <KMM_Wardrobe.mod> [...ещё моды для сравнения]
Модовая вещь = sid не из ванильной цепочки; вес слота = v1 ссылки clothing; слот = поле «slot» вещи."""
import os, statistics, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))
import json
import kmod

CAT = {x["sid"]: x["group"] for x in json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "catalog.json"), encoding="utf-8"))["items"]}

K = r"C:\Program Files (x86)\Steam\steamapps\common\Kenshi\data"
VAN = [os.path.join(K, n) for n in ("gamedata.base", "rebirth.mod", "Newwworld.mod", "Dialogue.mod")]


def main(mods):
    van = kmod.load_chain([p for p in VAN if os.path.exists(p)])
    vset = set(van)
    sq = [i for i in van.values() if i.type_name == "SQUAD_TEMPLATE"]
    used = {r.target for s in sq for c in ("leader", "squad", "squad2") for r in s.refs.get(c, [])}
    chars = sorted(c for c in used if c in van and van[c].type_name == "CHARACTER" and van[c].refs.get("clothing"))
    print(f"ванильных CHARACTER в SQUAD_TEMPLATE с одеждой: {len(chars)}")
    for mp in mods:
        mod = kmod.read(mp)
        M = kmod.load_chain([]) 
        for k, v in van.items():
            M[k] = kmod._copy(v)
        kmod.apply(M, mod)
        touched = 0
        per_slot = {}
        p_any = []
        mods_sid = set()
        for c in chars:
            ch, ch0 = M[c], van[c]
            if {(r.target, r.v1) for r in ch.refs.get("clothing", [])} != {(r.target, r.v1) for r in ch0.refs.get("clothing", [])}:
                touched += 1
            sl = {}
            for r in ch.refs.get("clothing", []):
                it = M.get(r.target)
                s = CAT.get(r.target)
                if s is None and it is not None and it.type_name == "ARMOUR":
                    s = "slot%s" % it.values.get("slot")
                if s is None or (it is not None and it.type_name != "ARMOUR"):
                    continue
                d = sl.setdefault(s, [0, 0])
                d[0] += r.v1
                if r.target not in vset:
                    d[1] += r.v1
            pn = 1.0
            for s, (tot, mw) in sl.items():
                if tot > 0:
                    per_slot.setdefault(s, []).append(mw / tot)
                    pn *= 1 - mw / tot
            p_any.append(1 - pn)
        print(f"\n== {os.path.basename(os.path.dirname(mp))}  ({os.path.getsize(mp)} байт)")
        print(f"тронуто персонажей: {touched}/{len(chars)} = {touched/len(chars):.1%}")
        for s, v in sorted(per_slot.items(), key=lambda x: str(x[0])):
            print(f"  слот {s}: n={len(v)} медиана доли мод-веса={statistics.median(v):.0%}, среднее={statistics.mean(v):.0%}")
        print(f"P(>=1 мод-вещь)>90%: {sum(1 for p in p_any if p > .9)}/{len(chars)} = {sum(1 for p in p_any if p > .9)/len(chars):.1%}; медиана P={statistics.median(p_any):.0%}")
        tv = [x for x in per_slot.values()]
        print(f"среднее по тронутым слотам (вес>0 мода): {statistics.mean([y for v in tv for y in v if y > 0] or [0]):.0%}")


main(sys.argv[1:])
