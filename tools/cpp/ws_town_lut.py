"""LINKN: компактная Lua-таблица «город дирижёра -> варианты (владелец, условия world state)» для рантайма дирижёра.

Читает rules/ws_town_map.json (tools/cpp/ws_town_map.py) и rules/conductor.json, пишет
build/KMM_Conductor/scripts/modules/kmm_ws_lut.lua (НЕ scripts/init: на старте не грузится; дирижёр читает файл лениво при первой смене владельца).
Что считается офлайн:
  1. сопоставление: stringID города данных == town_sid в conductor.json town_info (CFG.town_info), владелец-фракция == fid дирижёра;
  2. условия варианта = chain_states + world_states (AND); противоречивая цепочка отбрасывается;
  3. x = какие ЕЩЁ города модели дирижёра переключит этот набор условий (полностью выполнены условия их варианта) и на какого владельца;
  4. риск: состояние про NPC (мёртв/в плену) требует «ложной смерти» - допустимо только для лидера города из conductor.json,
     которого дирижёр сам убил/пленил (d = [npc, kind]); для остальных NPC, состояний игрока (ally/enemy/involvement) и состояний
     без NPC-условий вариант рискованный (r=1) и не применяется; «NPC жив» для лидера дирижёра -> список a (не применять, если дирижёр его убил).
Формат (индексы 1-based): F = фракции, W = world state sid, N = NPC sid;
  T[town_sid] = { {o=<F>, c={W,want,...}, x={town_sid,<F>,...}, d={N,"k"|"c"|"x",...}, a={N,...}} или {o=<F>,r=1} (есть, но рискованно) }
python -I -X utf8 tools/cpp/ws_town_lut.py
"""
import collections
import json
import os

ROOT = r"C:\KenshiModMap"
MAP = os.path.join(ROOT, "rules", "ws_town_map.json")
CONF = os.path.join(ROOT, "rules", "conductor.json")
OUT = os.path.join(ROOT, "build", "KMM_Conductor", "scripts", "modules", "kmm_ws_lut.lua")
CAP_PER_OWNER = 3   # вариантов на пару (город, владелец)

# значения «NPC is»: 0 мёртв, 1 жив, 2 в плену (по именам состояний ванили: "... dead" = 0, "... okay" = 1)
DEAD, ALIVE, CAPT = 0, 1, 2


def lua_str(s):
    out = ['"']
    for ch in s:
        o = ord(ch)
        if ch == '"':
            out.append('\\"')
        elif ch == "\\":
            out.append("\\\\")
        elif o < 32 or o == 127:
            out.append("\\%03d" % o)
        else:
            out.append(ch)
    out.append('"')
    return "".join(out)


def ws_need(state, want):
    """world state с want -> (hard_risk, needs_dead[(npc, kind)], needs_alive[npc])."""
    clauses = []   # (npc, 'is'|'not', st)
    for x in state.get("npc_is", []):
        clauses.append((x["sid"], "is", x["state"]))
    for x in state.get("npc_is_not", []):
        clauses.append((x["sid"], "not", x["state"]))
    hard = bool(state.get("player_involvement") or state.get("player_ally") or state.get("player_enemy") or state.get("town_okay"))
    if not clauses:
        return True, [], []   # состояние без NPC-условий: смысл неизвестен
    dead, alive = [], []
    if want == 1:
        for npc, kind, st in clauses:
            if kind == "is":
                if st == ALIVE:
                    alive.append(npc)
                elif st == DEAD:
                    dead.append((npc, "k"))
                else:
                    dead.append((npc, "c"))
            elif st == ALIVE:   # NPC is NOT alive
                dead.append((npc, "x"))
    elif len(clauses) == 1:
        npc, kind, st = clauses[0]
        if kind == "is":
            if st == ALIVE:
                dead.append((npc, "x"))   # неверно, что жив
        elif st == DEAD:
            dead.append((npc, "k"))       # неверно, что НЕ мёртв
        elif st == CAPT:
            dead.append((npc, "c"))
    else:
        # ¬(A и B ...): если есть клауза «живого» типа, нарушенной может оказаться именно она -> неоднозначно
        for npc, kind, st in clauses:
            if (kind == "is" and st == ALIVE) or (kind == "not" and st in (DEAD, CAPT)):
                return True, [], []
    return hard, dead, alive


def main():
    wm = json.load(open(MAP, encoding="utf-8"))
    cf = json.load(open(CONF, encoding="utf-8"))
    info = cf["town_info"]
    cfac = cf["factions"]
    leaders = {c["leader_sid"] for c in cf.get("towns", []) if c.get("enabled")}
    states = wm["states"]

    allv = collections.defaultdict(list)   # base_town -> [{owner, conds{ws:want}, depth}]
    dropped_contra = 0
    for bt, t in wm["towns"].items():
        for o in t["overrides"]:
            if not o.get("faction"):
                continue
            conds, bad = {}, False
            for w in o["chain_states"] + o["world_states"]:
                if conds.get(w["sid"], w["want"]) != w["want"]:
                    bad = True
                    break
                conds[w["sid"]] = w["want"]
            own = {w["sid"]: w["want"] for w in o["world_states"]}
            if bad or not conds:
                dropped_contra += 1
                conds = None
            # own - только условия самого override: для проверки «задетых» городов берём слабое (надмножество) условие, т.к. семантику цепочки в игре не проверить
            allv[bt].append({"owner": o["faction"], "conds": conds, "own": own, "depth": o["depth"]})

    fl, wl, nl = [], [], []
    fi, wi, ni = {}, {}, {}

    def idx(lst, d, v):
        if v not in d:
            lst.append(v)
            d[v] = len(lst)
        return d[v]

    T = {}
    stat = collections.Counter()
    towns_any, towns_clean, towns_cond = set(), set(), set()
    for bt in sorted(allv):
        if bt not in info:
            continue
        stat["map_towns_in_model"] += 1
        out = []
        for v in allv[bt]:
            if v["conds"] is None:
                continue
            if v["owner"] not in cfac:
                stat["variants_owner_not_in_model"] += 1
                continue
            stat["variants_total"] += 1
            C = v["conds"]
            hard, dead, alive = False, [], []
            for ws, want in C.items():
                st = states.get(ws)
                if st is None:
                    hard = True
                    continue
                h, d, a = ws_need(st, want)
                hard = hard or h
                dead += d
                alive += a
            if any(npc not in leaders for npc, _k in dead):
                hard = True
            if {n for n, _k in dead} & set(alive):
                hard = True
            alive = sorted({a for a in alive if a in leaders})
            x, ambiguous = {}, False
            for t2, vs2 in allv.items():
                if t2 == bt:
                    continue
                owners = {v2["owner"] for v2 in vs2 if v2["own"] and all(C.get(w) == c for w, c in v2["own"].items())}
                if t2 in info and owners:
                    if len(owners) > 1:
                        ambiguous = True
                    else:
                        x[t2] = next(iter(owners))
            for v2 in allv[bt]:   # другой вариант этого же города тоже полностью выполнен (не предок цепочки)
                if v2 is not v and v2["owner"] != v["owner"] and v2["depth"] >= v["depth"] and v2["own"] and all(C.get(w) == c for w, c in v2["own"].items()):
                    ambiguous = True
            if ambiguous:
                hard = True
                stat["variants_ambiguous"] += 1
            e = {"o": idx(fl, fi, v["owner"]), "hard": hard, "C": C, "x": x, "dead": sorted(set(dead)), "alive": alive}
            out.append(e)
            stat["variants_hard_risky" if hard else "variants_usable"] += 1
            if not hard:
                (towns_cond if e["dead"] else towns_clean).add(bt)
                towns_any.add(bt)
                stat["variants_with_other_towns" if x else "variants_only_this_town"] += 1
        out.sort(key=lambda e: (e["hard"], len(e["dead"]), len(e["x"]), len(e["C"])))
        keep, per, risk_seen = [], collections.Counter(), set()
        for e in out:
            if e["hard"]:
                if e["o"] not in risk_seen:
                    risk_seen.add(e["o"])
                    keep.append({"o": e["o"], "r": 1})
                continue
            if per[e["o"]] < CAP_PER_OWNER:
                per[e["o"]] += 1
                keep.append(e)
        usable = {e["o"] for e in keep if "r" not in e}
        keep = [e for e in keep if "r" not in e or e["o"] not in usable]
        keep.sort(key=lambda e: (("r" in e), len(e.get("dead", [])), len(e.get("x", {})), len(e.get("C", {}))))
        if keep:
            T[bt] = keep

    body = {}
    for bt, vs in T.items():
        row = []
        for e in vs:
            if "r" in e:
                row.append("{o=%d,r=1}" % e["o"])
                continue
            parts = ["o=%d" % e["o"]]
            c = []
            for ws, want in sorted(e["C"].items()):
                c += [str(idx(wl, wi, ws)), str(want)]
            parts.append("c={" + ",".join(c) + "}")
            if e["x"]:
                parts.append("x={" + ",".join("%s,%d" % (lua_str(t2), idx(fl, fi, ow)) for t2, ow in sorted(e["x"].items())) + "}")
            if e["dead"]:
                parts.append("d={" + ",".join('%d,"%s"' % (idx(nl, ni, n), k) for n, k in e["dead"]) + "}")
            if e["alive"]:
                parts.append("a={" + ",".join(str(idx(nl, ni, n)) for n in e["alive"]) + "}")
            row.append("{" + ",".join(parts) + "}")
        body[bt] = "{" + ",".join(row) + "}"
    head = ["-- KMM_Conductor LINKN: сгенерировано tools/cpp/ws_town_lut.py из rules/ws_town_map.json + rules/conductor.json. Не править руками.",
            "-- Чистые данные (return {...}); дирижёр читает файл лениво при первой смене владельца города, JSON в рантайме не парсится."]
    txt = ["return {", "v=1,",
           "F={" + ",".join(lua_str(s) for s in fl) + "},",
           "W={" + ",".join(lua_str(s) for s in wl) + "},",
           "N={" + ",".join(lua_str(s) for s in nl) + "},", "T={"]
    for bt in sorted(body):
        txt.append("[%s]=%s," % (lua_str(bt), body[bt]))
    txt += ["}", "}"]
    raw = ("\n".join(head + txt) + "\n").encode("utf-8")
    assert not any(b < 32 and b != 10 for b in raw), "control bytes in output"
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "wb") as f:
        f.write(raw)
    rep = dict(stat)
    rep.update({"model_towns": len(info), "lut_towns": len(T), "towns_with_usable_variant": len(towns_any),
                "towns_unconditional": len(towns_clean), "towns_with_leader_death_variant": len(towns_cond),
                "dropped_contradictory_chain": dropped_contra, "bytes": len(raw), "F": len(fl), "W": len(wl), "N": len(nl)})
    print(json.dumps(rep, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
