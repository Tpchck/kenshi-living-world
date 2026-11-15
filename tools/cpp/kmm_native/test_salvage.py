"""Offline check of rules/salvage.json for KMM_Native 2.4 (Salvage Parts / Butcher). Reads data only, never the game.
python -I -X utf8 tools/cpp/kmm_native/test_salvage.py -> OK, exit 1 on failure.
Checks: same parse rules as salvage.cpp (sections, clamps), every sid is a vanilla ITEM in data/items_audit.json,
expected value per order stays under the cap, race rule order (first substring match wins) for the races in data/registry.json."""
import json, sys

ROOT = r"C:\KenshiModMap"
CAP = {"robot": 1500, "animal": 1500}          # cats per order, ~ one small vanilla carcass / robot death drop
CAP_RACE = 3500                                 # leviathan-size rules
TASKS = {"KILL_CAGE_OCCUPANT", "MELEE_ATTACK_ANIMAL", "MELEE_ATTACK", "FOCUSED_MELEE_ATTACK", "UNPROVOKED_FOCUSED_MELEE_ATTACK"}
fails = []


def check(cond, msg):
    if not cond:
        fails.append(msg)


rules = json.load(open(ROOT + r"\rules\salvage.json", encoding="utf-8"))
items = {x["sid"]: x for x in json.load(open(ROOT + r"\data\items_audit.json", encoding="utf-8"))["items"]}
races = json.load(open(ROOT + r"\data\registry.json", encoding="utf-8"))["races"]
check(5 <= rules.get("window_sec", 60) <= 600, "window_sec out of 5..600")


def table_ev(tab, name):
    tot = sum(max(0, e.get("weight", 1)) for e in tab["items"])
    ev = 0.0
    for e in tab["items"]:
        it = items.get(e["sid"])
        check(it is not None, f"{name}: sid {e['sid']} not in items_audit")
        if not it:
            continue
        check(it["type"] == "ITEM" and it["vanilla"], f"{name}: {e['sid']} is not a vanilla ITEM")
        check(e.get("name", it["name"]).split(" (")[0] == it["name"], f"{name}: {e['sid']} name {e.get('name')} != {it['name']}")
        mn = e.get("min", 1); mx = e.get("max", mn)
        check(1 <= mn <= mx <= 50, f"{name}: {e['sid']} min/max {mn}/{mx}")
        ev += e["weight"] / tot * (mn + mx) / 2 * it["value"]
    rolls = tab.get("rolls", 1)
    check(1 <= rolls <= 10, f"{name}: rolls {rolls}")
    return ev * rolls


for kind in ("robot", "animal"):
    sec = rules[kind]
    check(sec.get("task", "KILL_CAGE_OCCUPANT") in TASKS, f"{kind}: unknown task")
    check(bool(sec["items"]), f"{kind}: empty default items")
    ev = table_ev(sec, kind)
    print(f"{kind:6} default: rolls {sec['rolls']}, ~{ev:.0f} cats per order")
    check(ev <= CAP[kind], f"{kind}: default EV {ev:.0f} > cap {CAP[kind]}")
    for r in sec.get("races", []):
        tab = {"items": r.get("items", sec["items"]), "rolls": r.get("rolls", sec["rolls"])}
        ev = table_ev(tab, f"{kind}/{r['match']}")
        print(f"{kind:6} {r['match']:45} rolls {tab['rolls']}, ~{ev:.0f} cats")
        check(ev <= CAP_RACE, f"{kind}/{r['match']}: EV {ev:.0f} > cap {CAP_RACE}")
    # first-match order as in salvage.cpp PickTable
    alts = [[a.strip().lower() for a in r["match"].split("|") if a.strip()] for r in sec.get("races", [])]
    def pick(name):
        n = name.lower()
        for i, al in enumerate(alts):
            if any(a in n for a in al):
                return sec["races"][i]["match"]
        return "default"
    if kind == "animal":
        check(pick("Megacrab") == "megacrab", "megacrab must match before crab")
        check(pick("Leviathan") == "leviathan", "leviathan rule")
        check(pick("Goat") != "default" and pick("Bonedog") != "default", "goat/bonedog rules")
        sample = sorted({x["name"] for x in races if x.get("vanilla") and not x.get("robot") and not x.get("playable")})
    else:
        sample = sorted({x["name"] for x in races if x.get("vanilla") and x.get("robot")})
    hits = {}
    for n in sample:
        hits.setdefault(pick(n), []).append(n)
    print(f"{kind:6} vanilla races by rule: " + "; ".join(f"{k}={len(v)}" for k, v in sorted(hits.items())))

for f in fails:
    print("FAIL", f)
print("OK" if not fails else f"{len(fails)} failure(s)")
sys.exit(1 if fails else 0)
