r"""ARMS: математика снаряжения. Аудит силы брони/оружия в единой шкале + план нормализации (общая библиотека для tools/streams/relics.py).
python -I -X utf8 tools\arms_audit.py  -> data\arms_audit.json
МОДЕЛЬ (допущения, в игре не проверялись; параметры — rules/streams/relics.json -> "arms"):
 * Из KenshiLib/CONSTANTS: 'damage resistance min/max' = -0.85/+0.85 — сопротивление зажато в ±0.85, т.е. минимум 15 % урона проходит всегда.
   Gear хранит cutResistance/bluntResistance/pierceResistance на предмет (формула сборки сопротивления в заголовках не раскрыта).
 * Сопротивление предмета R = base[material type] + def bonus (cut/blunt); pierce — R_cut * pierce def mult. Часть тела: сумма по предметам
   (покрытие part coverage/100 * R) * множитель грейда; бронебойность оружия вычитается из суммы до зажима;
   доля прошедшего урона = 1 - clamp(сумма - pen, 0, 0.85).
 * Части тела: 7 (голова, грудь, живот, 2 руки, 2 ноги), вес попадания равный.
 * base[] и grade_mult[] — предположения."""
import json
import re
import sys

ROOT = r"C:\KenshiModMap"
sys.path.insert(0, ROOT + r"\tools")
sys.path.insert(0, ROOT + r"\tools\build")
RULES = ROOT + r"\rules\streams\relics.json"
WARD = ROOT + r"\rules\streams\wardrobe.json"
MAIN = ("armour:hat", "armour:body", "armour:legs", "armour:boots")
TIERS = ("T0", "T1", "T2", "T3", "T4", "T5", "RELIC")
DMG_F = ("cut damage multiplier", "blunt damage multiplier", "pierce damage multiplier")


def num(i, k, d=0.0):
    v = i.values.get(k, d)
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else d


def cl(x, a=-0.85, b=0.85):
    return max(a, min(b, x))


def parts_cov(i):
    return {r.target: min(1.0, max(0.0, r.v0 / 100.0)) for r in i.refs.get("part coverage", [])}


def _g(i, vals):
    return lambda k, d=0.0: vals[k] if vals and k in vals else num(i, k, d)


def res(i, A, vals=None):
    g = _g(i, vals)
    m = int(num(i, "material type", 0))
    rc = A["base_cut"][m] + g("cut def bonus")
    rb = A["base_blunt"][m] + g("blunt def bonus")
    return rc, rb, rc * g("pierce def mult", 1.0)


def mobility_cost(i, vals=None):
    g = _g(i, vals)
    return (0.3 * max(0, 1 - g("dodge mult", 1.0)) + 0.3 * max(0, 1 - g("combat speed mult", 1.0)) + 0.2 * max(0, 1 - g("athletics mult", 1.0))
            + 0.1 * max(0, 1 - g("stealth mult", 1.0)) + 0.003 * min(80.0, g("weight kg", 0.0)))


def armour_score(i, A, vals=None, g=None):
    cov = sum(parts_cov(i).values())
    cap = A.get("cov_cap", {}).get(g)
    if cap:
        cov = min(cov, cap)
    rc, rb, rp = res(i, A, vals)
    return cov * (0.45 * rc + 0.45 * rb + 0.10 * rp) - 0.5 * mobility_cost(i, vals)


def weapon_score(i, vals=None):
    g = _g(i, vals)
    dmg = g(DMG_F[0]) + 0.8 * g(DMG_F[1]) + g(DMG_F[2])
    return dmg * (1 + max(-0.5, min(1.0, g("armour penetration")))) + 0.01 * g("attack mod")


def set_through(items, M, A, parts, grade, pen, vals_of=None):
    """(cut, blunt): средняя по 7 частям доля урона, проходящая сквозь набор предметов."""
    gm = A["grade_mult"][str(grade)]
    tc = tb = 0.0
    for p in parts:
        sc = sb = 0.0
        for sid in items:
            it = M[sid]
            c = parts_cov(it).get(p, 0.0)
            if c:
                rc, rb, _ = res(it, A, (vals_of or {}).get(sid))
                sc += c * rc
                sb += c * rb
        tc += 1 - cl(sc * gm - pen, 0.0)
        tb += 1 - cl(sb * gm - pen, 0.0)
    return tc / len(parts), tb / len(parts)


def load_rules():
    return json.load(open(RULES, encoding="utf-8"))["arms"]


def is_van(sid, org, A):
    return sid.endswith(tuple(A["vanilla_mods"])) or org in A["vanilla_mods"]


def _r3(x):
    return round(float(x), 3)


def plan(ctx, A=None):
    """{sid: {S0,S1,ch,x0,x1,t0,t1,info}} — нормализация значений существующих ARMOUR/WEAPON (только чтение ctx)."""
    A = A or load_rules()
    ward = json.load(open(WARD, encoding="utf-8"))
    RT = ward["relic_tier"]["sets"]
    pa_rx = re.compile(ward["context"]["lore_hard"]["power_armor"]["name_rx"] + "|" + A["pa_extra_rx"], re.I)
    cat = {x["sid"]: x for x in json.load(open(ROOT + r"\data\catalog.json", encoding="utf-8"))["items"]}
    M = ctx.M
    wh_mods = set(json.load(open(ROOT + r"\rules\budget.json", encoding="utf-8"))["wh_mods"])
    set_rx = [(s["id"], g, re.compile(rx, re.I)) for s in RT for g, rx in s["slots"].items()]
    rel_w = re.compile(A["relic_weapons_rx"], re.I)
    info = {}
    for sid, x in cat.items():
        it = M.get(sid)
        if it is None or x["type"] not in ("ARMOUR", "WEAPON"):
            continue
        if x["type"] == "ARMOUR" and x["group"] not in A["groups"]:
            continue
        org = ctx.origin.get(sid)
        row = {"name": x["name"], "type": x["type"], "group": x["group"], "mod": org, "van": is_van(sid, org, A),
               "wh": org in wh_mods or x["origin"].split(":")[0] in ("imperial", "chaos", "xenos"), "relic": False, "set": None}
        if x["type"] == "ARMOUR":
            for sid_set, g, rx in set_rx:
                if g == x["group"] and rx.search(x["name"] or ""):
                    row["relic"], row["set"] = True, sid_set
                    break
            if not row["relic"] and x["group"] in MAIN + ("armour:shirt",) and pa_rx.search(x["name"] or "") and not row["van"]:
                row["relic"], row["set"] = True, "power_armor"
        elif not row["van"] and rel_w.search(x["name"] or ""):
            row["relic"] = True
        info[sid] = row
    ceil, pen_ceil = {}, {}
    for sid, r in info.items():
        if r["van"]:
            i = M[sid]
            ceil.setdefault(r["group"], []).append(armour_score(i, A, None, r["group"]) if r["type"] == "ARMOUR" else weapon_score(i))
            if r["type"] == "WEAPON":
                pen_ceil[r["group"]] = max(pen_ceil.get(r["group"], -9), num(i, "armour penetration"))
    ceil = {g: max(v) for g, v in ceil.items()}
    mcap = {}
    for sid, r in info.items():
        if r["van"] and r["type"] == "ARMOUR":
            for k in A["mult_fields"]:
                mcap[k] = max(mcap.get(k, 1.0), num(M[sid], k, 1.0))
            for k in A["int_fields"]:
                mcap[k] = max(mcap.get(k, 0), num(M[sid], k, 0))
    xs = sorted(armour_score(M[s], A, None, r["group"]) / ceil[r["group"]] for s, r in info.items() if r["van"] and r["type"] == "ARMOUR" and ceil.get(r["group"], 0) > 0)
    wx = sorted(weapon_score(M[s]) / ceil[r["group"]] for s, r in info.items() if r["van"] and r["type"] == "WEAPON" and ceil.get(r["group"], 0) > 0)
    pcs = lambda arr, p: arr[min(len(arr) - 1, int(p * len(arr)))]
    bounds = [pcs(xs, p) for p in A["tier_percentiles"]]
    wb = [pcs(wx, p) for p in A["tier_percentiles_weapon"]]

    def tier(x, b):
        if x > A["ceil_slack"]:
            return "RELIC"
        for k, t in enumerate(b):
            if x < t:
                return TIERS[k]
        return "T5"
    out = {}
    for sid, r in info.items():
        i, g = M[sid], r["group"]
        if ceil.get(g, 0) <= 0:
            continue
        ch = {}
        if r["type"] == "ARMOUR":
            S0 = armour_score(i, A, None, g)
            if r["van"]:
                pass
            elif r["relic"]:
                tgt = A["relic_target"].get(g)
                if tgt:
                    m = int(num(i, "material type", 0))
                    for fld, base in (("cut def bonus", A["base_cut"][m]), ("blunt def bonus", A["base_blunt"][m])):
                        nv = _r3(max(num(i, fld), tgt - base))
                        if nv != _r3(num(i, fld)):
                            ch[fld] = nv
                    pm = max(num(i, "pierce def mult", 1.0), A["relic_pierce_mult"])
                    if pm != num(i, "pierce def mult", 1.0):
                        ch["pierce def mult"] = _r3(pm)
                    w = max(num(i, "weight kg"), A["relic_weight_min"].get(g, 0))
                    if w != num(i, "weight kg"):
                        ch["weight kg"] = _r3(w)
                    for k, cap in A["relic_mob_cap"].get(g, {}).items():
                        if num(i, k, 1.0) > cap:
                            ch[k] = cap
                    pr = max(num(i, "relative price mult", 1.0), A["relic_price_mult"].get(g, 1.0))
                    if pr != num(i, "relative price mult", 1.0):
                        ch["relative price mult"] = pr
            else:
                if S0 > ceil[g] * A["ceil_slack"]:
                    cb, bb = num(i, "cut def bonus"), num(i, "blunt def bonus")
                    lo = A["vanilla_bonus_floor"]
                    for _ in range(60):
                        sc = armour_score(i, A, {"cut def bonus": cb, "blunt def bonus": bb}, g)
                        if sc <= ceil[g] * A["tier_cap_frac"] or (cb <= lo and bb <= lo):
                            break
                        cb = max(lo, cb * 0.85) if cb > lo else cb
                        bb = max(lo, bb * 0.85) if bb > lo else bb
                    if _r3(cb) != _r3(num(i, "cut def bonus")):
                        ch["cut def bonus"] = _r3(cb)
                    if _r3(bb) != _r3(num(i, "blunt def bonus")):
                        ch["blunt def bonus"] = _r3(bb)
                    if num(i, "pierce def mult", 1.0) > A["pierce_mult_cap"]:
                        ch["pierce def mult"] = A["pierce_mult_cap"]
                for k in A["mult_fields"]:
                    if num(i, k, 1.0) > mcap[k] + 1e-6:
                        ch[k] = _r3(mcap[k])
                for k in A["int_fields"]:
                    if num(i, k, 0) > mcap[k]:
                        ch[k] = int(mcap[k])
                wmax = A["weight_cap"].get(g)
                if wmax and num(i, "weight kg") > wmax:
                    ch["weight kg"] = float(wmax)
            S1 = armour_score(i, A, ch, g)
        else:
            S0 = weapon_score(i)
            if r["van"]:
                pass
            elif r["relic"]:
                if num(i, "armour penetration") < A["relic_weapon_pen"]:
                    ch["armour penetration"] = A["relic_weapon_pen"]
                s1 = weapon_score(i, ch)
                need = ceil[g] * A["relic_weapon_floor"]
                if 0 < s1 < need:
                    k = need / s1
                    for f in DMG_F:
                        if num(i, f) > 0:
                            ch[f] = _r3(num(i, f) * k)
            else:
                pc_ = pen_ceil.get(g, 0.3)
                if num(i, "armour penetration") > pc_:
                    ch["armour penetration"] = pc_
                for f in DMG_F:
                    if num(i, f) > A["weapon_dmg_cap"]:
                        ch[f] = A["weapon_dmg_cap"]
                sc = weapon_score(i, ch)
                lim = ceil[g] * A["tier_cap_frac"]
                if sc > ceil[g] * A["ceil_slack"]:
                    k = lim / sc
                    for f in DMG_F:
                        v = ch.get(f, num(i, f))
                        if v > 0:
                            ch[f] = _r3(v * k)
            S1 = weapon_score(i, ch)
        b = bounds if r["type"] == "ARMOUR" else wb
        out[sid] = {"S0": S0, "S1": S1, "ch": ch, "x0": S0 / ceil[g], "x1": S1 / ceil[g], "info": r}
        out[sid]["t0"], out[sid]["t1"] = tier(out[sid]["x0"], b), tier(out[sid]["x1"], b)
    return {"plan": out, "mcap": mcap, "ceil": ceil, "bounds": bounds, "wbounds": wb, "pen_ceil": pen_ceil, "A": A}


def sets_report(ctx, P, A):
    """«Палки против силовой брони»: наборы релик-сетов (hat+body+legs+boots), доля урона до/после, грейд 3 и 5."""
    M = ctx.M
    parts = [i.sid for i in M.values() if i.type_name == "LOCATIONAL_DAMAGE" and i.name in ("Head", "Chest", "Stomach", "Left Arm", "Right Arm", "Left Leg", "Right Leg")
             and i.sid.endswith(".quack")]
    plan_ = P["plan"]
    new = {s: v["ch"] for s, v in plan_.items() if v["ch"]}
    groups = {}
    for sid, v in plan_.items():
        r = v["info"]
        if r["type"] == "ARMOUR" and r["relic"] and r["group"] in MAIN:
            key = (r["set"], r["name"].split(" - ")[0] if " - " in r["name"] else r["set"])
            groups.setdefault(key, {}).setdefault(r["group"], []).append(sid)
    rows = []
    for key, d in groups.items():
        if "armour:body" not in d or "armour:legs" not in d:
            continue
        items = [max(d[g], key=lambda s: plan_[s]["S0"]) for g in MAIN if g in d]
        row = {"set": key[1], "kind": key[0], "slots": len(items)}
        for gn, gr in (("g1", 1), ("g3", 3), ("g5", 5)):
            for wn, (wc, wb_, pn) in A["scenarios"].items():
                b = set_through(items, M, A, parts, gr, pn)
                a = set_through(items, M, A, parts, gr, pn, new)
                pick = (lambda t: t[1]) if wb_ and not wc else (lambda t: t[0] if wc and not wb_ else 0.5 * (t[0] + t[1]))
                row[f"{wn}_{gn}"] = [round(pick(b), 3), round(pick(a), 3)]
        rows.append(row)
    van = {}
    for sid, v in plan_.items():
        r = v["info"]
        if r["van"] and r["type"] == "ARMOUR" and r["group"] in MAIN and (r["group"] not in van or v["S0"] > plan_[van[r["group"]]]["S0"]):
            van[r["group"]] = sid
    vrow = {"items": {g: plan_[s]["info"]["name"] for g, s in van.items()}, "parts": len(parts)}
    for gn, gr in (("g1", 1), ("g3", 3), ("g5", 5)):
        for wn, (wc, wb_, pn) in A["scenarios"].items():
            b = set_through(list(van.values()), M, A, parts, gr, pn)
            vrow[f"{wn}_{gn}"] = round((b[1] if wb_ and not wc else b[0] if wc and not wb_ else 0.5 * (b[0] + b[1])), 3)
    return rows, vrow


def main():
    import kmm_build
    ctx = kmm_build.Ctx()
    A = load_rules()
    P = plan(ctx, A)
    plan_ = P["plan"]
    dist = {}
    for sid, v in plan_.items():
        r = v["info"]
        org = "relic" if r["relic"] else ("wh" if r["wh"] else ("vanilla" if r["van"] else "mod"))
        for k, t in (("before", v["t0"]), ("after", v["t1"])):
            d = dist.setdefault(r["type"], {}).setdefault(k, {}).setdefault(t, {})
            d[org] = d.get(org, 0) + 1
    changed = {s: v for s, v in plan_.items() if v["ch"]}
    outl = [{"sid": s, "name": v["info"]["name"], "mod": v["info"]["mod"], "type": v["info"]["type"], "group": v["info"]["group"],
             "x_before": round(v["x0"], 2), "x_after": round(v["x1"], 2), "relic": v["info"]["relic"], "ch": v["ch"]} for s, v in changed.items()]
    above = sorted([o for o in outl if not o["relic"]], key=lambda o: o["x_before"] - o["x_after"], reverse=True)
    relic_ch = [o for o in outl if o["relic"]]
    relic_weak = [{"name": v["info"]["name"], "group": v["info"]["group"], "x0": round(v["x0"], 2), "x1": round(v["x1"], 2)}
                  for v in plan_.values() if v["info"]["relic"] and v["x0"] < 1.0]
    rows, vrow = sets_report(ctx, P, A)
    rep = {"_doc": "ARMS audit (tools/arms_audit.py). x = score / ванильный потолок группы; RELIC = x>1. Модель — допущения в docstring.",
           "ceil": {g: round(c, 3) for g, c in P["ceil"].items()}, "tier_bounds_armour_x": [round(b, 3) for b in P["bounds"]],
           "tier_bounds_weapon_x": [round(b, 3) for b in P["wbounds"]], "pen_ceil": P["pen_ceil"],
           "distribution": dist, "n_changed": len(changed), "n_relic": sum(1 for v in plan_.values() if v["info"]["relic"]),
           "mods_above_ceiling_nonrelic": len(above), "relic_below_vanilla_top_before": len(relic_weak),
           "samples_nonrelic": above[:30], "samples_relic": relic_ch[:20], "relic_weak": relic_weak[:25],
           "sets": rows, "vanilla_top_set": vrow}
    json.dump(rep, open(ROOT + r"\data\arms_audit.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({k: rep[k] for k in ("ceil", "tier_bounds_armour_x", "tier_bounds_weapon_x", "n_changed", "n_relic", "mods_above_ceiling_nonrelic",
                                          "relic_below_vanilla_top_before", "vanilla_top_set")}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
