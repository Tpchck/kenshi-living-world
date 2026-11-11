"""Общие нормы для потоков (владелец — интегратор). Единственный источник норм денег — rules/streams/economy.json."""
import json

_ECON = r"C:\KenshiModMap\rules\streams\economy.json"
_mr = None


def money_norm(it):
    """Новые money min/max для персонажа по его NPC class (только повышение) или {} если менять не нужно."""
    global _mr
    if _mr is None:
        _mr = json.load(open(_ECON, encoding="utf-8"))["money_by_role"]
    rule = _mr.get(str(it.values.get("NPC class")))
    if not rule or it.values.get("slave", 0) or any(x.lower() in it.name.lower() for x in _mr["skip_name_contains"]):
        return {}
    cmin, cmax = int(it.values.get("money min", 0)), int(it.values.get("money max", 200))
    nmin, nmax = max(cmin, rule["min"]), max(cmax, rule["max"], rule["min"])
    return {"money min": nmin, "money max": nmax} if (nmin, nmax) != (cmin, cmax) else {}


def role_of(it):
    global _mr
    if _mr is None:
        money_norm(it)
    r = _mr.get(str(it.values.get("NPC class")))
    return r["role"] if r else None


def rival_tier(M, sq, tiers):
    """Тир силы отряда-соперника (RIVALS Q1, rules/streams/fix.json rivals.tiers): (weak|mid|strong, pw),
    pw = максимум combat stats среди CHARACTER лидера/членов (0 — статы не заданы)."""
    pw = max([M[r.target].values.get("combat stats", 0) or 0 for c in ("leader", "squad", "squad2")
              for r in sq.refs.get(c, []) if r.target in M and M[r.target].type_name == "CHARACTER"] or [0])
    return ("weak" if pw < tiers["weak_below"] else ("strong" if pw >= tiers["strong_from"] else "mid")), pw
