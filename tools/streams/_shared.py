"""Общие нормы для потоков (владелец — интегратор). Единственный источник норм денег — rules/streams/economy.json."""
import json
import re

_ECON = r"C:\KenshiModMap\rules\streams\economy.json"
_mr = None


def money_norm(it):
    """Новые money min/max для персонажа по его NPC class (только повышение) или {} если менять не нужно."""
    global _mr
    if _mr is None:
        _mr = json.load(open(_ECON, encoding="utf-8"))["money_by_role"]
    for cap in _mr.get("cap_by_name_rx", []):   # B4 Н10: голодные — пара монет (понижение, единственное исключение из «только повышаем»)
        if re.search(cap["rx"], it.name or "", re.I):
            want = {"money min": cap["min"], "money max": cap["max"]}
            cur = {"money min": int(it.values.get("money min", 0)), "money max": int(it.values.get("money max", 200))}
            return want if want != cur else {}
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


# --- география огнестрела (B4 Н9/И8; ручки: rules/streams/wardrobe.json context.firearms.geo) ----------------
class GunGeo:
    """Где делают стволы и как редеет огнестрел с расстоянием. Мастерские — из данных: города фракции с именем по geo.hub_faction_rx
    (Iron Hearth, Dreg Gunworks) и города, чьи лавки держат «оружейный» список (≥ hub_list_min ствола в crossbows, доля ≥ hub_list_share).
    Координаты — rules/conductor.json town_info (+ хост лагеря из rules/cleanup.json, + база для override-города)."""

    def __init__(self, ctx, geo, firearm_sids):
        import os
        root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.g, self.M, self.fire = geo, ctx.M, set(firearm_sids)
        ti = json.load(open(os.path.join(root, "rules", "conductor.json"), encoding="utf-8")).get("town_info", {})
        camps = {c["camp"]: c["host"] for c in json.load(open(os.path.join(root, "rules", "cleanup.json"), encoding="utf-8")).get("camps", [])}
        self.pos = {k: (v["x"], v["z"]) for k, v in ti.items() if v.get("x") is not None}
        for camp, host in camps.items():
            if camp not in self.pos and host in self.pos:
                self.pos[camp] = self.pos[host]
        for t in ctx.M.values():     # override-город живёт там же, где базовый
            if t.type_name == "TOWN" and t.sid not in self.pos:
                for r in t.refs.get("override town", []):
                    if r.target in self.pos:
                        self.pos[t.sid] = self.pos[r.target]
                        break
        self.towns = [t for t in ctx.all("TOWN")]
        self.hubs = {}    # sid -> (name, (x, z), почему)
        rx = re.compile(geo["hub_faction_rx"], re.I)
        for t in self.towns:
            fr = t.refs.get("faction")
            if t.sid in self.pos and fr and fr[0].target in ctx.M and rx.search(ctx.M[fr[0].target].name or ""):
                self.hubs[t.sid] = (t.name, self.pos[t.sid], "faction " + ctx.M[fr[0].target].name)
        self.gun_lists = {}
        for v in ctx.all("VENDOR_LIST"):
            cb = [r.target for r in v.refs.get("crossbows", [])]
            nf = sum(1 for x in cb if x in self.fire)
            if cb and nf >= geo["hub_list_min"] and nf / len(cb) >= geo["hub_list_share"]:
                self.gun_lists[v.sid] = (v.name, nf, len(cb))
        for t in self.towns:
            if t.sid in self.pos and t.sid not in self.hubs:
                for sq in self.town_squads(t):
                    hit = [r.target for r in sq.refs.get("vendors", []) if r.target in self.gun_lists]
                    if hit:
                        self.hubs[t.sid] = (t.name, self.pos[t.sid], "shop list " + self.gun_lists[hit[0]][0])
                        break

    def town_squads(self, t):
        return [self.M[r.target] for c in ("residents", "bar squads", "roaming squads") for r in t.refs.get(c, [])
                if r.target in self.M and self.M[r.target].type_name in ("SQUAD_TEMPLATE", "UNIQUE_SQUAD_TEMPLATE")]

    def dist(self, p):
        return min((((p[0] - h[1][0]) ** 2 + (p[1] - h[1][1]) ** 2) ** 0.5 for h in self.hubs.values()), default=1e9)

    def mult(self, p):
        """Множитель частоты огнестрела в точке p: near_boost у мастерской, 1.0 до near_r, линейно вниз до far_mult к far_r."""
        g, d = self.g, self.dist(p)
        if d <= g["boost_r"]:
            return g["near_boost"]
        k = max(0.0, min(1.0, (g["far_r"] - d) / (g["far_r"] - g["near_r"])))
        return g["far_mult"] + (1.0 - g["far_mult"]) * k

    def maps(self):
        """(char -> [pos]) и (vendor list -> [pos]) по городам: жители/бары/бродячие отряды и их лавки."""
        chars, lists = {}, {}
        for t in self.towns:
            p = self.pos.get(t.sid)
            if p is None:
                continue
            for sq in self.town_squads(t):
                for c in ("leader", "squad", "squad2"):
                    for r in sq.refs.get(c, []):
                        chars.setdefault(r.target, []).append(p)
                for r in sq.refs.get("vendors", []):
                    lists.setdefault(r.target, []).append(p)
        return chars, lists
