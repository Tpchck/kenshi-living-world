"""Общая логика ITEMS-блока ECONOMY (не поток): классификация предметов, ванильные шкалы цен, мёртвые предметы, дубли.
Используют tools/items_audit.py (аудит -> data/items_audit.json) и tools/streams/economy.py (правка цен/пулов)."""
import collections
import re
import statistics

VANILLA = ("gamedata.base", "Newwworld.mod", "Dialogue.mod", "rebirth.mod")
ITEM_TYPES = ("ITEM", "MAP_ITEM", "CONTAINER")
# (тип записи, категория ссылки) -> «пассивные» ссылки: предмет от них не появляется в мире
PASSIVE = {("BUILDING", "limit inventory"), ("RESEARCH", "cost"), ("ITEM", "ingredients"), ("CROSSBOW", "ingredients"),
           ("BUILDING_FUNCTIONALITY", "consumes"), ("BUILDING_FUNCTIONALITY", "special tool"), ("RESEARCH", "blueprint item")}
PASSIVE_TYPES = {"ITEMS_CULTURE", "DIALOGUE_LINE", "DIALOG_ACTION", "DIALOGUE", "CROSSBOW", "WEAPON", "ARMOUR"}
QUEST_TYPES = {"DIALOGUE_LINE", "DIALOG_ACTION", "DIALOGUE", "FACTION_CAMPAIGN", "WORLD_EVENT_STATE", "ARTIFACTS"}
BOOK_RX = re.compile(r"\b(book|tome|codex|manual|notebook|journal|diary|letter|note|notes|scroll|ledger|logbook|grimoire|scripture|poster|report|"
                     r"records?|legends?|treatise|testament|chronicle|pamphlet|primer|lexicanum)s?\b", re.I)
NOT_BOOK_RX = re.compile(r"cover|empty|bookmark|shelf|case|stand|binding|ink|paper\b|pen\b|craft|make book", re.I)
BOOK_FN = 13
SKIP_RX = re.compile(r"^_|dummy|shopping token|test\b|^\s*$", re.I)


def group_of(it):
    t = it.type_name
    if t == "MAP_ITEM":
        return "map"
    if t == "CONTAINER":
        return "container"
    nm = it.name or ""
    fn = it.values.get("item function", 0)
    if SKIP_RX.search(nm) or fn in (4, 5, 6):
        return "token"
    if fn == BOOK_FN:
        return "book"
    if fn == 11:
        return "blueprint"
    if fn in (1, 2, 10):
        return "medical"
    if fn == 12:
        return "repair"
    if fn == 8:
        return "drug"
    if fn == 3:
        return "food"
    if fn == 15:
        return "organic"
    if fn == 14:
        return "trinket"
    if fn == 17:
        return "limb"
    if fn == 16:
        return "ammo"
    if fn == 7:
        return "material"
    if fn == 9:
        return "tool"
    if BOOK_RX.search(nm) and not NOT_BOOK_RX.search(nm):
        return "book"
    return "trade" if it.values.get("trade item") else "misc"


def vw(it):
    """цена за кг (вес с нижней границей 0.2 — иначе невесомые вещи дают бессмысленный выброс)"""
    v = it.values.get("value", 0)
    w = max(float(it.values.get("weight kg", 1.0) or 0), 0.2)
    if it.type_name == "CONTAINER":   # у рюкзаков цена — за ёмкость
        w = max(1.0, float(it.values.get("storage size width", 1) or 1) * float(it.values.get("storage size height", 1) or 1) / 10.0)
    return v / w if isinstance(v, (int, float)) else 0.0


def referrers(M):
    """sid предмета -> Counter{(тип, категория)}"""
    tg = {i.sid for i in M.values() if i.type_name in ITEM_TYPES}
    out = collections.defaultdict(collections.Counter)
    for r in M.values():
        for cat, rs in r.refs.items():
            for x in rs:
                if x.target in tg:
                    out[x.target][(r.type_name, cat)] += 1
    return out


def is_quest(it, refs):
    if any(t in QUEST_TYPES for (t, c) in refs):
        return True
    v = it.values
    if v.get("persistent") or v.get("artifact"):
        return True
    # предмет лежит только в инвентаре конкретных персонажей — квестовая/уникальная вещь NPC
    act = [k for k in refs if k not in PASSIVE and k[0] not in PASSIVE_TYPES]
    return bool(act) and all(k == ("CHARACTER", "inventory") for k in act)


def is_dead(refs):
    return not any(k not in PASSIVE and k[0] not in PASSIVE_TYPES for k in refs)


def norm_name(n):
    return re.sub(r"[^a-z0-9]+", " ", (n or "").lower()).strip()


def vanilla_scales(rows):
    """группа -> (медиана цена/кг ваниль, p10 value, p90 value, n)"""
    by = collections.defaultdict(list)
    for r in rows:
        if r["vanilla"] and r["value"] > 0 and r["group"] not in ("token",):
            by[r["group"]].append(r)
    out = {}
    for g, rs in by.items():
        vals = sorted(x["value"] for x in rs)
        out[g] = {"n": len(rs), "med_vw": statistics.median(x["vw"] for x in rs), "med_value": statistics.median(vals),
                  "p10": vals[int(len(vals) * 0.1)], "p90": vals[min(len(vals) - 1, int(len(vals) * 0.9))]}
    return out


def build_rows(ctx):
    M = ctx.M
    refs = referrers(M)
    rows = []
    for it in M.values():
        if it.type_name not in ITEM_TYPES or not ctx.in_game(it.sid) or it.values.get("REMOVED"):
            continue
        o = ctx.origin.get(it.sid, "?")
        rf = refs.get(it.sid, collections.Counter())
        v = it.values.get("value", 0)
        rows.append({"sid": it.sid, "name": it.name, "mod": o, "vanilla": o in VANILLA, "type": it.type_name, "group": group_of(it),
                     "value": v if isinstance(v, int) else int(v), "weight": round(float(it.values.get("weight kg", 0) or 0), 3),
                     "vw": round(vw(it), 2), "quest": is_quest(it, rf), "dead": is_dead(rf),
                     "refs": sorted(f"{t}.{c}={n}" for (t, c), n in rf.items()) if rf else [],
                     "icon": bool(it.values.get("icon")) or bool(it.values.get("auto icon image")),
                     "text": ((it.name or "") + " " + str(it.values.get("description", "")))[:400]})
    return rows
