"""Свои WORLD_EVENT_STATE для смены владельцев городов (LINKN) — вызывается из потока elite (записи живут в KMM_Elite.mod).

Зачем (docs/OVERHAUL_PATTERNS.md §3, §4 п.2): KMM_Native.ws_set подменяет ответ WorldEventStateQuery::isTrue по stringID.
Раньше дирижёр подменял 45 ОБЩИХ состояний («Tengu is alive», «Esata is alive»...), их читают ваниль и Kaizo (кампании,
реплики, шаблоны) -> побочки. Теперь на каждую пару «город модели -> новый владелец» свой WS и свой TOWN-вариант:
  WS  «KMM town <город> -> <владелец>»: запрос всегда ложен сам по себе (противоречие «NPC is X alive» И «NPC is NOT X alive»
      на ванильном уникале rules.false_npc), истинен только через ws_set;
  TOWN клон лучшего существующего варианта этой пары (ваниль/основа/Kaizo): тот же владелец, жители, бар, roaming;
      свой «world state» = [наш WS = 1], без вложенных «override town»;
  базовому городу добавляется ссылка «override town» -> клон (только добавление).
Ванильные и Kaizo-записи на наши WS не ссылаются, ws_set общие состояния больше не трогает (белый список в KMM_Native.lua).

sid стабильны между сборками: номера берутся из реестра rules/ws_own_ids.json (только дописывать, ничего не удалять и
не перенумеровывать: сейв хранит sid варианта в GAMESTATE_TOWN.replacementTown). Пара без номера в реестре пропускается
(отчёт ws_own_unregistered); дописать номера:  python -I -X utf8 tools/streams/ws_own.py --register
Таблица для дирижёра пишется здесь же: build/KMM_Conductor/scripts/modules/kmm_ws_lut.lua (формат v=1, c={W,1})."""
import collections
import json
import os
import sys

ROOT = r"C:\KenshiModMap"
REG = os.path.join(ROOT, "rules", "ws_own_ids.json")
LUT_OUT = os.path.join(ROOT, "build", "KMM_Conductor", "scripts", "modules", "kmm_ws_lut.lua")
CONF = os.path.join(ROOT, "rules", "conductor.json")
MOD = "KMM_Elite.mod"
FIRST_ID = 900001
MAX_CHAIN = 8
POP = ("residents", "bar squads", "roaming squads")


def own_sid(n):
    return f"{int(n)}-{MOD}"


def is_own(sid):
    return isinstance(sid, str) and sid.endswith("-" + MOD) and sid.split("-", 1)[0].isdigit()


def false_refs(npc, extra_is=()):
    """Запрос, ложный при любом состоянии npc: «npc жив» И «npc НЕ жив». extra_is — доп. клаузы «NPC is» (замок Elite)."""
    from kmod import Ref
    return {"NPC is": [Ref(t, 1, 0, 0) for t in extra_is] + [Ref(npc, 1, 0, 0)], "NPC is NOT": [Ref(npc, 1, 0, 0)]}


def load_conf():
    cf = json.load(open(CONF, encoding="utf-8"))
    orig = {}
    for fid, f in cf["factions"].items():
        for t in f.get("towns", []):
            orig[t] = fid
    return cf["town_info"], cf["factions"], orig


def candidates(M, in_game, info, cfac, orig):
    """{"<город>|<владелец>": [sid варианта, ...]} лучшие первыми. Варианты — существующие TOWN под «override town»
    (в глубину), кроме наших собственных клонов; владелец — фракция модели дирижёра, не исходный владелец города."""
    out = collections.defaultdict(list)
    for bt in sorted(info):
        t = M.get(bt)
        if t is None or t.type_name != "TOWN":
            continue
        seen, found = {bt}, []

        def walk(node, depth):
            if depth >= MAX_CHAIN:
                return
            for r in node.refs.get("override town", []):
                o = M.get(r.target)
                if o is None or o.type_name != "TOWN" or o.sid in seen or is_own(o.sid):
                    continue
                seen.add(o.sid)
                found.append((o, depth))
                walk(o, depth + 1)
        walk(t, 0)
        for o, depth in found:
            fr = o.refs.get("faction")
            f = fr[0].target if fr else None
            if not f or f not in cfac or f == orig.get(bt) or not in_game(o.sid) or f not in M:
                continue
            pop = sum(len(o.refs.get(k, [])) for k in POP)
            key = (depth, 0 if pop else 1, len(o.refs.get("world state", [])), o.sid)
            out[f"{bt}|{f}"].append((key, o.sid))
    return {k: [sid for _, sid in sorted(v)] for k, v in out.items()}


def load_reg():
    if not os.path.isfile(REG):
        return {"pairs": {}, "next": FIRST_ID}
    return json.load(open(REG, encoding="utf-8"))


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


def lut_text(rows):
    """rows: {город: [(владелец, ws_sid), ...]} -> текст kmm_ws_lut.lua (v=1; дирижёр читает F/W/T, N пуст)."""
    fl, fi, wl, wi = [], {}, [], {}

    def idx(lst, d, v):
        if v not in d:
            lst.append(v)
            d[v] = len(lst)
        return d[v]
    body = []
    for bt in sorted(rows):
        parts = ["{o=%d,c={%d,1}}" % (idx(fl, fi, f), idx(wl, wi, w)) for f, w in sorted(rows[bt])]
        body.append("[%s]={%s}," % (lua_str(bt), ",".join(parts)))
    head = ["-- KMM_Conductor LINKN: сгенерировано tools/streams/ws_own.py (поток elite) из rules/ws_own_ids.json + rules/conductor.json. Не править руками.",
            "-- Только СВОИ world state (WORLD_EVENT_STATE из KMM_Elite.mod): одна пара город->владелец = один WS = один TOWN-вариант. Общие ванильные/Kaizo WS здесь не бывают.",
            "-- Чистые данные (return {...}); дирижёр читает файл лениво при первой смене владельца города."]
    txt = ["return {", "v=1,", "own=1,",
           "F={" + ",".join(lua_str(s) for s in fl) + "},",
           "W={" + ",".join(lua_str(s) for s in wl) + "},",
           "N={},", "T={"] + body + ["}", "}"]
    raw = ("\n".join(head + txt) + "\n").encode("utf-8")
    assert not any(b < 32 and b != 10 for b in raw), "control bytes in output"
    return raw


def build(ctx, s, R):
    """Записи в поток s (KMM_Elite). R = rules elite.json "own_ws"."""
    from kmod import Ref
    M = ctx.M
    if not R.get("enabled", True):
        return
    npc = R["false_npc"]
    if npc not in M or M[npc].type_name != "CHARACTER":
        raise KeyError(f"own_ws: false_npc {npc} не CHARACTER")
    info, cfac, orig = load_conf()
    cand = candidates(M, ctx.in_game, info, cfac, orig)
    reg = load_reg()
    pairs = reg.get("pairs", {})
    rows = collections.defaultdict(list)
    max_id = 0
    for key in sorted(pairs):
        e = pairs[key]
        bt, f = key.split("|", 1)
        max_id = max(max_id, int(e["ws"]), int(e["town"]))
        lst = cand.get(key)
        if not lst:
            s.report["ws_own_no_variant"] += 1   # вариант пропал из данных (обновление чужого мода): пара спит, номера за ней
            continue
        src = e.get("src") if e.get("src") in lst else lst[0]
        if src != e.get("src"):
            s.report["ws_own_src_changed"] += 1
        ws_sid, town_sid = own_sid(e["ws"]), own_sid(e["town"])
        ws = s.new("WORLD_EVENT_STATE", f"KMM town {M[bt].name} -> {M[f].name}", sid=ws_sid,
                   values={"notes": "KMM LINKN: own town-owner flag, true only via KMM_Native.ws_set", "player involvement": False})
        ws.refs.update(false_refs(npc))
        t = s.new("TOWN", M[src].name, template=src, sid=town_sid)
        t.refs.pop("override town", None)
        t.refs["world state"] = [Ref(ws_sid, 1, 0, 0)]
        s.add_refs(bt, "override town", [Ref(town_sid, 0, 0, 0)])
        rows[bt].append((f, ws_sid))
        s.report["ws_own_pairs"] += 1
    s.report["ws_own_unregistered"] += sum(1 for k in cand if k not in pairs)
    s.report["ws_own_towns"] = len(rows)
    if max_id:
        s.mb.last_id = max(s.mb.last_id, max_id)   # заголовок .mod: следующий номер выше занятых (последовательные sid потока уже выданы)
    raw = lut_text(rows)
    os.makedirs(os.path.dirname(LUT_OUT), exist_ok=True)
    with open(LUT_OUT, "wb") as fh:
        fh.write(raw)


def register():
    """Дописать в реестр номера для новых пар (старые не трогаются). Читает данные только для чтения."""
    for _p in ("build", "fast", ""):
        sys.path.insert(0, os.path.join(ROOT, "tools", _p))
    import kmm_build as kb
    ctx = kb.Ctx()
    info, cfac, orig = load_conf()
    cand = candidates(ctx.M, ctx.in_game, info, cfac, orig)
    reg = load_reg()
    reg.setdefault("pairs", {})
    nxt = int(reg.get("next", FIRST_ID))
    added = 0
    for key in sorted(cand):
        if key in reg["pairs"]:
            continue
        reg["pairs"][key] = {"ws": nxt, "town": nxt + 1, "src": cand[key][0]}
        nxt += 2
        added += 1
    reg["next"] = nxt
    reg["_doc"] = ("Реестр номеров своих WORLD_EVENT_STATE/TOWN для LINKN (tools/streams/ws_own.py). sid = <номер>-KMM_Elite.mod. "
                   "ТОЛЬКО ДОПИСЫВАТЬ: не удалять и не перенумеровывать (сейв хранит sid варианта в GAMESTATE_TOWN.replacementTown). "
                   "src — вариант-образец на момент регистрации (при пропаже берётся следующий лучший, номера остаются).")
    with open(REG, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(reg, fh, ensure_ascii=False, indent=1, sort_keys=True)
    print(json.dumps({"pairs_total": len(reg["pairs"]), "added": added, "next": nxt, "candidates": len(cand)}, ensure_ascii=False))


if __name__ == "__main__":
    if "--register" in sys.argv:
        register()
    else:
        print(__doc__)
