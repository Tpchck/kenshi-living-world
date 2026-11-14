"""Аудит палитры: сколько ярких перекрасок получают NPC, схемы цветов фракций, предложение лорной палитры.
Запуск: python -I -X utf8 tools/palette_audit.py   (только чтение; пишет data/palette_audit.json и data/palette_proposal.json)."""
import sys, re, json, colorsys, collections
sys.path.insert(0, r"C:\KenshiModMap\tools"); sys.path.insert(0, r"C:\KenshiModMap\tools\build")
import kmm_build, kmod

R = r"C:\KenshiModMap"
ctx = kmm_build.Ctx(); M = ctx.M
van = {n for n, _, _ in ctx.van}
CAT = {x["sid"]: x for x in json.load(open(R + r"\data\catalog.json", encoding="utf-8"))["items"]}
rules = json.load(open(R + r"\rules\streams\wardrobe.json", encoding="utf-8"))
dd = json.load(open(R + r"\rules\dedup_canonical.json", encoding="utf-8"))
FAMCOL, FAMKEY = {}, {}
for f in dd["families"]:
    for e in f["members"]:
        FAMCOL[e["sid"]] = e["color"]; FAMKEY[e["sid"]] = f["key"]
modof = lambda sid: sid.split("-", 1)[1] if "-" in sid else sid

DARK_W = r"black|dark|gr[ae]y|brown|rust|ash|ashen|charcoal|umber|soot|ebony|obsidian|shadow|night|dusk|coal|slate|iron|dirty|burnt|mud|dusty|cocoa|chocolate|maroon|burgundy|navy|midnight|sable|raven|onyx"
NEUT_W = r"undyed|leather|tan|sand|sandy|khaki|bone|natural|beige|cream|hide|fur|straw|linen|hemp|burlap|wool|silver|steel|metal|bronze|copper|camo|olive|moss|rags?"
BRIGHT_W = {"red": r"red|crimson|scarlet|ruby|vermilion", "yellow": r"yellow", "pink": r"pink|rose|magenta", "purple": r"purple|violet|lilac|royal",
            "blue": r"blue|azure|sapphire", "green": r"green|lime|emerald", "orange": r"orange", "white": r"white|ivory|snow",
            "gold": r"gold|golden", "cyan": r"cyan|teal|turquoise|aqua"}
NOISE = re.compile(r"red sabre?s?|red river|redlands|blue ?bird|whitebeard|green ?lander|white ?eye|gold ?ore", re.I)


def hexcls(v):
    r, g, b = (v >> 16) & 255, (v >> 8) & 255, v & 255
    h, s, val = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
    h *= 360
    if val < 0.38: return "dark", "dark"
    if s < 0.22: return ("dark", "grey") if val < 0.65 else ("neutral", "lightgrey/white")
    if (h < 50 or h >= 345) and val < 0.58: return "dark", "brown/rust"
    if 15 <= h <= 55 and s < 0.5: return "neutral", "tan"
    if s > 0.45 and val > 0.45:
        for lo, hi, n in ((0, 15, "red"), (15, 45, "orange"), (45, 70, "yellow"), (70, 170, "green"), (170, 200, "cyan"), (200, 260, "blue"), (260, 300, "purple"), (300, 345, "pink"), (345, 361, "red")):
            if lo <= h < hi: return "bright", n
    return "neutral", "muted"


def name_cls(name):
    n = NOISE.sub(" ", name)
    if re.search(r"\b(%s)\b" % DARK_W, n, re.I): return "dark", "name"
    for c, rx in BRIGHT_W.items():
        if re.search(r"\b(%s)\b" % rx, n, re.I): return "bright:" + c, "name"
    if re.search(r"\b(%s)\b" % NEUT_W, n, re.I): return "neutral", "name"
    if re.search(r"\bdyed\b|\(colou?red\)", n, re.I): return "bright:dyed", "name"
    return None, None


def cdhex(ref_t):
    c = M.get(ref_t)
    return c.values.get("color 1") if c is not None else None


def item_color(sid):
    """(класс, цвет, источник). bright хранится как 'bright', цвет отдельно."""
    nm = CAT[sid]["name"] if sid in CAT else M[sid].name
    c, src = name_cls(nm)
    if c:
        return (c.split(":")[0], c.split(":")[1] if ":" in c else c, src)
    fc = FAMCOL.get(sid)
    if fc:
        c2, _ = name_cls(fc)
        if c2: return (c2.split(":")[0], c2.split(":")[1] if ":" in c2 else c2, "family")
        if fc in BRIGHT_W: return ("bright", fc, "family")
        if fc in ("black", "grey", "gray", "brown"): return ("dark", fc, "family")
    it = M.get(sid)
    if it is not None and it.refs.get("color"):
        h = cdhex(it.refs["color"][0].target)
        if h is not None:
            k, n = hexcls(h); return (k, n, "own_hex")
    return ("unknown", "", "")


# --- фракции и их схемы
facs = {}
for f in sorted(ctx.all("FACTION"), key=lambda f: bool(f.values.get("not real", False))):
    facs.setdefault(f.name, f)
frows = []
FHEX = {}
for fn, f in facs.items():
    h1 = h2 = None
    if f.refs.get("color"):
        c = M.get(f.refs["color"][0].target)
        if c is not None: h1, h2 = c.values.get("color 1"), c.values.get("color 2")
    vanilla = modof(f.sid) in van
    cls = cls2 = None
    if h1 is not None:
        k1, n1 = hexcls(h1); k2, n2 = hexcls(h2 if h2 is not None else h1)
        cls = (k1, n1); cls2 = (k2, n2)
    garish = bool(cls and (cls[0] == "bright" or cls2[0] == "bright"))
    FHEX[fn] = (h1, h2, cls, cls2)
    frows.append({"faction": fn, "sid": f.sid, "vanilla": vanilla, "color1": None if h1 is None else "#%06X" % h1, "color2": None if h2 is None else "#%06X" % h2,
                  "class1": cls, "class2": cls2, "garish": garish})

# --- персонаж -> фракция (как в wardrobe.py)
start_squads = {r.target for st in M.values() if st.type_name == "NEW_GAME_STARTOFF" for rs in st.refs.values() for r in rs}
town_fac = {}
for t in ctx.all("TOWN"):
    if t.refs.get("faction") and t.refs["faction"][0].target in M:
        for c in ("residents", "bar squads", "roaming squads"):
            for r in t.refs.get(c, []): town_fac.setdefault(r.target, M[t.refs["faction"][0].target].name)
char_fac = {}
for sq in ctx.all("SQUAD_TEMPLATE") + ctx.all("UNIQUE_SQUAD_TEMPLATE"):
    if sq.sid in start_squads: continue
    if sq.refs.get("faction") and sq.refs["faction"][0].target in M: fn = M[sq.refs["faction"][0].target].name
    elif sq.sid in town_fac: fn = town_fac[sq.sid]
    else: continue
    for c in ("leader", "squad", "squad2") + tuple(rules.get("squad_ref_cats_extra", ())):
        for r in sq.refs.get(c, []): char_fac.setdefault(r.target, fn)

# --- что реально получают NPC (собранный KMM_Wardrobe)
wm = kmod.read(R + r"\build\KMM_Wardrobe\KMM_Wardrobe.mod")
cache = {}
def ic(sid):
    if sid not in cache:
        cache[sid] = item_color(sid) if sid in M else ("unknown", "", "")
    return cache[sid]

def colorisable(sid):
    it = M.get(sid)
    return it is not None and it.type_name == "ARMOUR" and it.values.get("dont colorise") is False

tot = collections.Counter(); byfac = collections.defaultdict(collections.Counter); bymod = collections.defaultdict(collections.Counter)
tint_fac = collections.Counter(); colcount = collections.Counter(); npc_bright = collections.defaultdict(set); npc_all = collections.defaultdict(set)
for ch in wm.items:
    if ch.type_name != "CHARACTER": continue
    fn = char_fac.get(ch.sid, "(без фракции)")
    npc_all[fn].add(ch.sid)
    for r in ch.refs.get("clothing", []):
        k, col, _ = ic(r.target)
        tot[k] += 1; byfac[fn][k] += 1; bymod[modof(r.target)][k] += 1
        if k == "bright": colcount[col] += 1; npc_bright[fn].add(ch.sid)
        if colorisable(r.target) and fn in FHEX and FHEX[fn][2] and FHEX[fn][2][0] == "bright": tint_fac[fn] += 1

def top(d, n=30):
    return sorted(d.items(), key=lambda kv: -kv[1]["bright"])[:n]

by_fac_out = [{"faction": f, "bright": c["bright"], "dark": c["dark"], "neutral": c["neutral"], "unknown": c["unknown"], "npcs": len(npc_all[f]),
               "npcs_with_bright": len(npc_bright[f]), "bright_share": round(c["bright"] / max(1, sum(c.values())), 3),
               "scheme_bright_tinted_refs": tint_fac[f]} for f, c in top(byfac)]
by_mod_out = [{"mod": m, "bright": c["bright"], "dark": c["dark"], "neutral": c["neutral"], "unknown": c["unknown"]} for m, c in top(bymod)]

# --- классификация каталога
cat_cls = collections.Counter(); cat_items = {}
for sid, x in CAT.items():
    if x["type"] != "ARMOUR": continue
    k, col, src = item_color(sid) if sid in M else ("unknown", "", "")
    cat_items[sid] = [k, col, src]; cat_cls[k] += 1
fam_stat = collections.Counter(src for k, c, src in cat_items.values() if k == "bright")

# --- предложение
ALLOW = [  # (regex по имени фракции, цвета)
    (r"holy nation|paladin|holy", ["white", "gold", "blue"]), (r"red sabre", ["red"]), (r"shek", ["red", "orange"]),
    (r"united cities|traders? guild|noble|trade ?ninja", ["red", "blue", "gold"]), (r"southern (?!hive)|swamp", ["green"]),
    (r"shinobi|ninja", []), (r"anti-slavers|slave|free", [])]
allow = {}
for fn in facs:
    cols = []
    for rx, cs in ALLOW:
        if re.search(rx, fn, re.I): cols = sorted(set(cols) | set(cs))
    if cols: allow[fn] = cols
allowed_any = {c for cs in allow.values() for c in cs}
drop, fonly = [], {}
for sid, (k, col, src) in cat_items.items():
    if k != "bright": continue
    if col not in allowed_any or col == "dyed": drop.append(sid)
    else: fonly[sid] = {"color": col, "allowed_factions": [f for f, cs in allow.items() if col in cs]}
# семейства: оставить минимум один тёмный/нейтральный вариант, иначе канон (первый) — не терять вещь
fam_keep = {}
fams = collections.defaultdict(list)
for sid in cat_items:
    if sid in FAMKEY: fams[FAMKEY[sid]].append(sid)
dropset = set(drop)
for key, mem in fams.items():
    good = [s for s in mem if cat_items[s][0] in ("dark", "neutral", "unknown")]
    if good: fam_keep[key] = {"keep": good, "drop": [s for s in mem if s in dropset]}
    else:
        keep = sorted(mem)[0]; fam_keep[key] = {"keep": [keep], "drop": [s for s in mem if s in dropset and s != keep], "note": "все варианты яркие: оставлен один"}
        dropset.discard(keep)
drop = sorted(dropset)
prop = {"_doc": "Лорная палитра (предложение, не применено). Подключение: docs/PALETTE.md. Источник: tools/palette_audit.py",
        "default_allowed": ["dark", "neutral"], "faction_bright_ok": allow, "families_keep": fam_keep,
        "bright_item_sids_to_drop_from_pools": drop, "bright_item_sids_faction_only": fonly}
json.dump(prop, open(R + r"\data\palette_proposal.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
out = {"catalog_armour_classes": dict(cat_cls), "bright_source": dict(fam_stat), "npc_refs_total": dict(tot), "bright_colors_worn": dict(colcount.most_common()),
       "bright_by_faction_top30": by_fac_out, "bright_by_mod_top30": by_mod_out,
       "factions": sorted(frows, key=lambda r: (not r["vanilla"], r["faction"])), "garish_mod_factions": [r["faction"] for r in frows if r["garish"] and not r["vanilla"]],
       "garish_vanilla_factions": [r["faction"] for r in frows if r["garish"] and r["vanilla"]],
       "drop_count": len(drop), "faction_only_count": len(fonly), "item_colors": cat_items}
json.dump(out, open(R + r"\data\palette_audit.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("catalog armour", dict(cat_cls)); print("npc refs", dict(tot)); print("colors", dict(colcount.most_common()))
print("drop", len(drop), "fonly", len(fonly)); print("garish mod factions", len(out["garish_mod_factions"]), "vanilla", out["garish_vanilla_factions"])
for r in by_fac_out[:12]: print(r)
for r in by_mod_out[:10]: print(r)
