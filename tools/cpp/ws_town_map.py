"""Офлайн-карта «город -> какие world state (WORLD_EVENT_STATE) включают его town override» для KMM_Native.

Читает ТОЛЬКО ванильные data\\*.base/.mod (VANILLA в tools/fast/ctx.py) и моды основы из mods.cfg
(tools/fast/out/final_lo.json -> "base"); WH-слой и KMM_* не берёт. Ничего не пишет, кроме rules/ws_town_map.json.

Модель Kenshi (fcs.def, [TOWN]): у базового города T есть ссылки «override town» -> города-замены O.
У O есть «world state» (WORLD_EVENT_STATE, v0: 1 = состояние должно быть истинным, 0 = ложным; условия связаны через AND)
и «faction» (новый владелец). Если условия O выполнены, город перезаселяется как O. O может иметь свой «override town» (цепочка).
Дирижёр, чтобы сменить владельца города T на фракцию F, находит override O с faction == F и вызывает
KMM_Native.ws_set(sid, want) для каждого world state из O.world_states (sid берётся отсюда, поле stringID записи).

python -I -X utf8 tools/cpp/ws_town_map.py [--out путь]
"""
import collections
import json
import os
import sys

ROOT = r"C:\KenshiModMap"
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, os.path.join(ROOT, "tools", "fast"))
import kmod  # noqa: E402
import ctx  # noqa: E402

OUT_DEFAULT = os.path.join(ROOT, "rules", "ws_town_map.json")
MAX_CHAIN = 8   # защита от циклов override -> override


def nm(M, sid):
    it = M.get(sid)
    return it.name if it is not None else None


def main():
    out_path = OUT_DEFAULT
    if "--out" in sys.argv:
        out_path = sys.argv[sys.argv.index("--out") + 1]
    lo, van, base, _wh = ctx.load(with_wh=False)
    bad = [(n, e) for n, m, e in van + base if m is None]
    M = {}
    for _n, m, _e in van + base:
        if m is not None:
            kmod.apply(M, m)

    def ws_refs(it):
        return [{"sid": r.target, "name": nm(M, r.target), "want": int(r.v0)} for r in it.refs.get("world state", [])
                if r.target in M and M[r.target].type_name == "WORLD_EVENT_STATE"]

    def fac(it):
        r = it.refs.get("faction", [])
        return (r[0].target, nm(M, r[0].target)) if r else (None, None)

    def overrides_of(t, seen, depth, path_states):
        """Все override-города под t (в глубину), с накопленными условиями цепочки."""
        res = []
        if depth >= MAX_CHAIN:
            return res
        for r in t.refs.get("override town", []):
            o = M.get(r.target)
            if o is None or o.type_name != "TOWN" or o.sid in seen:
                continue
            fsid, fname = fac(o)
            own = ws_refs(o)
            res.append({
                "town": o.sid, "name": o.name, "faction": fsid, "faction_name": fname,
                "depth": depth,
                "world_states": own,                       # AND-условия самого override
                "chain_states": path_states,               # условия вышестоящих override цепочки (если depth > 0)
            })
            res.extend(overrides_of(o, seen | {o.sid}, depth + 1, path_states + own))
        return res

    # override-города (на них ссылаются как на замену) — сами не являются «базовыми»
    referenced = {r.target for t in M.values() if t.type_name == "TOWN" for r in t.refs.get("override town", [])}
    towns = {}
    for t in M.values():
        if t.type_name != "TOWN" or not t.refs.get("override town") or t.sid in referenced:
            continue
        fsid, fname = fac(t)
        ovs = overrides_of(t, {t.sid}, 0, [])
        if ovs:
            towns[t.sid] = {"name": t.name, "faction": fsid, "faction_name": fname, "overrides": ovs}

    by_state = collections.defaultdict(lambda: {"name": None, "uses": []})
    for tsid, t in towns.items():
        for o in t["overrides"]:
            for w in o["world_states"]:
                e = by_state[w["sid"]]
                e["name"] = w["name"]
                e["uses"].append({"base_town": tsid, "base_name": t["name"], "override_town": o["town"], "override_name": o["name"],
                                  "want": w["want"], "new_owner": o["faction"], "new_owner_name": o["faction_name"],
                                  "other_states": [x["sid"] for x in o["world_states"] if x["sid"] != w["sid"]]})

    states = {}
    for sid in by_state:
        it = M[sid]
        states[sid] = {"name": it.name,
                       "player_involvement": bool(it.values.get("player involvement", False)),
                       "npc_is": [{"sid": r.target, "name": nm(M, r.target), "state": int(r.v0)} for r in it.refs.get("NPC is", [])],
                       "npc_is_not": [{"sid": r.target, "name": nm(M, r.target), "state": int(r.v0)} for r in it.refs.get("NPC is NOT", [])],
                       "town_okay": [{"sid": r.target, "name": nm(M, r.target), "okay": int(r.v0)} for r in it.refs.get("town okay", [])],
                       "player_ally": [r.target for r in it.refs.get("player ally", [])],
                       "player_enemy": [r.target for r in it.refs.get("player enemy", [])]}

    rep = {
        "_doc": "Сгенерировано tools/cpp/ws_town_map.py (ваниль + основа из mods.cfg, только чтение). towns[base_town_sid].overrides[*].world_states "
                "= AND-условия (want 1 = состояние должно быть истинным, 0 = ложным). by_state[ws_sid].uses = какие города включает состояние. "
                "states[ws_sid] = что состояние проверяет (NPC жив/мёртв/в плену, город цел). sid = stringID записи gamedata = ключ KMM_Native.ws_set.",
        "meta": {"mods_read": len([1 for _n, m, _e in van + base if m is not None]), "read_failures": [f"{n}: {e}" for n, e in bad[:20]],
                 "base_towns_with_overrides": len(towns), "overrides_total": sum(len(t["overrides"]) for t in towns.values()),
                 "world_states_used": len(by_state)},
        "towns": towns,
        "by_state": by_state,
        "states": states,
    }
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(rep, f, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    print(json.dumps(rep["meta"], ensure_ascii=False))
    print("->", out_path, os.path.getsize(out_path), "bytes")


if __name__ == "__main__":
    main()
