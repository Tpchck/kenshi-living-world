"""Генератор campaigns.json для KMM_Conductor (родные кампании движка FACTION_CAMPAIGN, FactionWarMgr:triggerCampaign).
Запуск: python -I -X utf8 tools/conductor/gen_campaigns.py   (грузит Ctx ~минуты; игру не трогает)
Данные (проверено по записям): у FACTION_CAMPAIGN нет явного типа ASSAULT/CONQUER/DEFEND и нет времени подготовки (minTime/maxTime
задаёт вызывающий). Есть: is hostile, target characters, territorial triggers, chance per day, range near/far, num forces, target tech level,
travel speed, refs pt1/pt2/retreat/victory AI (пакеты ИИ фаз), squads to use, world state, inherits from, loss/victory trigger.
Владельцы: FACTION.campaigns -> кампании (+ campaign.faction override).
Вид (kind) выводится из полей:
  reinforce — is hostile = false (подкрепление/защита: имя Ally/protect/defend или без признаков визита);
  visit     — is hostile = false и имя Visit/Merchant/Tax/Tribute/Trader/Caravan (визиты, не бой);
  hunt      — hostile + target characters (охота на персонажей игрока: нашей колонне не подходит);
  raid      — hostile, самозапуск (chance per day > 0) на территорию/город;
  assault   — hostile, без самозапуска (запуск диалогом/скриптом) — подходит для triggerCampaign по решению дирижёра.
Шаблоны 'BASE...' без владельца попадают в общий пул base."""
import collections
import json
import os
import re
import sys

sys.path.insert(0, r"C:\KenshiModMap\tools")
sys.path.insert(0, r"C:\KenshiModMap\tools\build")
ROOT = r"C:\KenshiModMap"
OUT = os.path.join(ROOT, "build", "KMM_Conductor", "campaigns.json")


VISIT = re.compile(r"visit|merchant|tax|tribute|trader|caravan|animals|pilgrim|refugee|festival", re.I)


def kind_of(v, name=""):
    if not v.get("is hostile"):
        return "visit" if VISIT.search(name) and not re.search(r"ally|protect|defen|reinforc", name, re.I) else "reinforce"
    if v.get("target characters"):
        return "hunt"
    if (v.get("chance per day") or 0) > 0:
        return "raid"
    return "assault"


def main():
    import kmm_build
    ctx = kmm_build.Ctx()
    M = ctx.M
    camps = {r.sid: r for r in M.values() if r.type_name == "FACTION_CAMPAIGN" and ctx.in_game(r.sid)}
    owners = collections.defaultdict(set)
    for r in M.values():
        if r.type_name == "FACTION" and ctx.in_game(r.sid):
            for x in r.refs.get("campaigns", []):
                if x.target in camps:
                    owners[x.target].add(r.sid)
    for c in camps.values():
        for x in c.refs.get("faction override", []):
            owners[c.sid].add(x.target)
    fname = {f.sid: f.name for f in M.values() if f.type_name == "FACTION"}

    def ai(c, k):
        t = c.refs.get(k, [])
        return M[t[0].target].name if t and t[0].target in M else None

    items = {}
    for sid, c in camps.items():
        v = c.values
        items[sid] = {"sid": sid, "name": c.name, "display": v.get("display name") or "", "kind": kind_of(v, c.name), "hostile": bool(v.get("is hostile")),
                      "forces": int(v.get("num forces") or 0), "chance_day": round(v.get("chance per day") or 0, 3),
                      "range": [int(v.get("range near") or 0), int(v.get("range far") or 0)], "tech": int(v.get("target tech level >=") or 0),
                      "pop_min": int(v.get("target population min") or 0), "territorial": bool(v.get("territorial triggers")),
                      "speed": [v.get("travel speed loaded"), v.get("travel speed unloaded")],
                      "squads": len(c.refs.get("squads to use", [])), "ws": len(c.refs.get("world state", [])),
                      "inherits": [x.target for x in c.refs.get("inherits from", [])], "ai_pt1": ai(c, "pt1 AI leader"), "ai_pt2": ai(c, "pt2 AI leader"),
                      "ai_victory": ai(c, "victory AI leader"), "mod": ctx.origin.get(sid) if hasattr(ctx, "origin") else None,
                      "owners": sorted(owners.get(sid, ()))}
    by_fac = {}
    for sid, it in items.items():
        for fid in it["owners"]:
            e = by_fac.setdefault(fid, {"name": fname.get(fid, fid), "assault": [], "raid": [], "hunt": [], "reinforce": [], "visit": []})
            e[it["kind"]].append(sid)
    for e in by_fac.values():
        for k in ("assault", "raid", "hunt", "reinforce", "visit"):
            e[k].sort(key=lambda s: (-items[s]["forces"], s))
    base = {k: sorted([s for s, i in items.items() if not i["owners"] and i["kind"] == k], key=lambda s: (-items[s]["forces"], s))
            for k in ("assault", "raid", "hunt", "reinforce", "visit")}
    # у кампаний нет заданного человеком типа 93: GameData.type FACTION_CAMPAIGN = 93 (NATIVE_MAP)
    out = {"_doc": "KMM_Conductor campaigns (tools/conductor/gen_campaigns.py). Не править руками.", "gd_type": 93, "campaigns": items,
           "factions": by_fac, "base": base}
    json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    kinds = collections.Counter(i["kind"] for i in items.values())
    print("campaigns", len(items), dict(kinds), "owned", sum(1 for i in items.values() if i["owners"]), "factions", len(by_fac))
    print("top factions", sorted(((len(sum((e[k] for k in ("assault", "raid", "reinforce")), [])), e["name"]) for e in by_fac.values()), reverse=True)[:10])
    print("base", {k: len(v) for k, v in base.items()})


if __name__ == "__main__":
    main()
