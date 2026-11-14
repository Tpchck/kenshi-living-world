"""Проверка слоёв KMM_*: отряд (SQUAD_TEMPLATE), которому разные слои добавляют разные фракции, — у отряда окажется две фракции,
игра возьмёт одну наугад (баг Mongrel 2026-11-14: KMM_Cleanup ставил Mongrel, поток fix — копию Gunsmiths).
python -I -X utf8 tools/check_layer_factions.py -> OK / список конфликтов, код 1."""
import collections, glob, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))
import kmod
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
add = collections.defaultdict(dict)   # sid -> {layer: {factions}}
for p in sorted(glob.glob(os.path.join(ROOT, "build", "KMM_*", "*.mod"))):
    layer = os.path.basename(p)
    try:
        m = kmod.read(p)
    except Exception as e:
        print("не читается", layer, e); continue
    for it in m.items:
        if it.type_name in ("SQUAD_TEMPLATE", "CHARACTER") and it.refs.get("faction"):
            add[it.sid][layer] = {x.target for x in it.refs["faction"] if x.v0 is not None}
bad = []
for sid, per in add.items():
    fs = set().union(*per.values())
    if len(per) > 1 and len(fs) > 1:
        bad.append((sid, {k: sorted(v) for k, v in per.items()}))
for b in bad:
    print("КОНФЛИКТ", b)
print("OK" if not bad else f"конфликтов: {len(bad)}")
sys.exit(1 if bad else 0)
