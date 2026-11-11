"""Какие ANIMATION_FILE в сборке содержат 'walk lower/upper', их порядок относительно OrcRaceReview и область (раса/глобально)."""
import os
import re
import sys

sys.path.insert(0, r"C:\KenshiModMap\tools")
sys.path.insert(0, r"C:\KenshiModMap\tools\fast")
import ctx  # noqa: E402
import kmod  # noqa: E402

lo, van, base, wh = ctx.load()
W = r"C:\Program Files (x86)\Steam\steamapps\workshop\content\233860"
dirs = {b["file"]: os.path.join(W, b["id"]) for b in lo["base"] + lo["wh"]}
NAMES = (b"walk lower\n", b"walk upper\n")


def has_anim(p):
    try:
        b = open(p, "rb").read()
    except OSError:
        return None
    return [n.decode().strip() for n in NAMES if n in b]


M = {}
for _, m, _ in van + base + wh:
    kmod.apply(M, m)
raceref = {x.target for r in M.values() if r.type_name in ("RACE", "CHARACTER", "ANIMAL_CHARACTER") for x in r.refs.get("animation files", [])}
order = [n for n, _, _ in van + base + wh]
orc_pos = order.index("OrcRaceReview.mod")
rows = []
for n, m, _ in base + wh:
    for it in m.items:
        if it.type_name != "ANIMATION_FILE" or it.change != 0:
            continue
        for k in ("male animation", "female animation"):
            p = it.values.get(k, "")
            if not p:
                continue
            rel = re.sub(r"^\.?[/\\]mods[/\\][^/\\]+[/\\]", "", p).replace("/", os.sep)
            h = has_anim(os.path.join(dirs.get(n, ""), rel))
            if h:
                rows.append((order.index(n), n, it.name, "race-specific" if it.sid in raceref else "GLOBAL", it.values.get("preprocess")))
                break
print("orc pos", orc_pos, "| ANIMATION_FILE with walk lower/upper:", len(rows))
for r in sorted(rows):
    print(f"  #{r[0]:<4} {'AFTER ORC' if r[0] > orc_pos else '':<9} {r[1][:34]:<34} {r[3]:<13} preprocess={r[4]} {r[2][:30]}")
