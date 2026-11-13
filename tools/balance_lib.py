"""Общие функции баланса спавна (tools\faction_share.py и поток relics): архетип отряда, размер, звери."""
import re

DEL = 2147483647


def squad_size(sq):
    return max(1, sum(max(r.v0, r.v1) for c in ("leader", "squad", "squad2") for r in sq.refs.get(c, [])))


def fac_arch(f, wr):
    """архетип фракции для баланса: как behavior.archetype_of, но «not real» не выбрасывает (дрифтеры, рабы -> по типу)"""
    if f is None:
        return "other"
    n = f.name
    if n in wr["override_by_name"]:
        return wr["override_by_name"][n]
    for a, names in wr["archetype_by_name"].items():
        if n in names:
            return a
    for a, rx in wr["archetype_regex"]:
        if re.search(rx, n):
            return a
    return wr["type_fallback"].get(str(f.values.get("fundamental type", 4)), "settler")


def is_wild_char(M, ch, fac):
    """зверь: раса без одежды/шляп («no shirts» и «no hats») либо фракция fundamental type 0"""
    rs = [M[r.target] for r in ch.refs.get("race", []) if r.target in M]
    if rs:
        return all(r.values.get("no shirts") and r.values.get("no hats") for r in rs)
    return fac is not None and fac.values.get("fundamental type", 4) == 0


def squad_arch(M, sq, wr, fcache):
    """архетип отряда: wild (звери/монстры) | архетип фракции"""
    fr = sq.refs.get("faction")
    f = M.get(fr[0].target) if fr else None
    chars = [M.get(r.target) for c in ("leader", "squad", "squad2") for r in sq.refs.get(c, [])]
    chars = [c for c in chars if c is not None and c.type_name == "CHARACTER"]
    if f is not None and f.values.get("fundamental type", 4) == 0:
        return "wild"
    if chars and sum(is_wild_char(M, c, f) for c in chars) * 2 > len(chars):
        return "wild"
    key = f.sid if f is not None else None
    if key not in fcache:
        a = fac_arch(f, wr)
        fcache[key] = "wild" if a == "monster" else a
    return fcache[key]


def entry_units(M, target, wr, fcache, ucache):
    """[(архетип, размер)] для цели ссылки биома: отряд -> один блок; TOWN (логово) -> отряды residents/roaming/bar"""
    if target in ucache:
        return ucache[target]
    t = M.get(target)
    out = []
    if t is not None and t.type_name == "SQUAD_TEMPLATE":
        out = [(squad_arch(M, t, wr, fcache), squad_size(t))]
    elif t is not None and t.type_name == "TOWN":
        for c in ("residents", "roaming squads", "bar squads"):
            for r in t.refs.get(c, []):
                q = M.get(r.target)
                if q is not None and q.type_name == "SQUAD_TEMPLATE" and (r.v0, r.v1, r.v2) != (DEL,) * 3:
                    out.append((squad_arch(M, q, wr, fcache), squad_size(q)))
    ucache[target] = out
    return out
