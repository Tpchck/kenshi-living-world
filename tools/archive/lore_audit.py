r"""Аудит лора (только чтение): уникальные персонажи (ваниль и моды), фракции, города, диалоги; модовые фракции и их «ванильный родитель».
python -I -X utf8 tools\lore_audit.py -> data\lore_audit.json  (загрузка Ctx — минуты)"""
import collections, json, os, re, sys
ROOT = r"C:\KenshiModMap"
for sub in ("tools", r"tools\build", r"tools\streams"):
    sys.path.insert(0, os.path.join(ROOT, sub))
import kmm_build  # noqa: E402
import behavior  # noqa: E402

CORE = ("gamedata.base", "rebirth.mod", "Newwworld.mod", "Dialogue.mod")
# ветви: регулярка имени модовой фракции -> ванильный родитель (по архетипу/региону; проверяется на реальных именах)
BRANCH = [
    (r"paladin|templar|crusader|holy|inquisit|order of|temple|church|cathedr|faith|sacred|monk|priest", "The Holy Nation"),
    (r"merchant|trading|trade house|guild|caravan|bank|market|company", "Traders Guild"),
    (r"samurai|shogun|ronin|ninja|shinobi|sabre|sabres|clan", "Black Dragon Ninjas"),
    (r"bandit|raider|thief|thieves|outlaw|gang|pirate|marauder", "Dust Bandits"),
    (r"empire|imperial|legion|kingdom|royal|republic|nation|city|cities|watch|guard|police|military", "United Cities"),
    (r"hive|drone|insect|bug|queen", "Western Hive"),
    (r"skeleton|machine|robot|android|cyber|golem|construct", "Skeleton Legion"),
    (r"tribe|savage|cannibal|beast|berserk|horde|hunter", "Cannibals"),
]


def main():
    ctx = kmm_build.Ctx()
    M, O = ctx.M, ctx.origin
    wr = json.load(open(os.path.join(ROOT, "rules", "streams", "behavior.json"), encoding="utf-8"))["world_relations"]
    fname = lambda sid: M[sid].name if sid in M else ""
    squad = collections.defaultdict(list)
    for q in ctx.all("SQUAD_TEMPLATE"):
        fr = q.refs.get("faction") or []
        if not fr:
            continue
        for cat in ("leader", "squad", "squad2", "squad3"):
            for r in q.refs.get(cat, []):
                squad[r.target].append((fr[0].target, cat))
    towns = collections.defaultdict(list)
    for t in ctx.all("TOWN"):
        for r in t.refs.get("faction", []):
            towns[r.target].append(t.name)
    # дом уникального: город, где он лидер/в отряде не определить надёжно -> по ссылке 'leader' в TOWN при наличии
    tleader = collections.defaultdict(list)
    for t in ctx.all("TOWN"):
        for r in t.refs.get("leader", []) if "leader" in t.refs else []:
            tleader[r.target].append(t.name)
    uniq = []
    for ch in ctx.all("CHARACTER"):
        v = ch.values
        if not v.get("unique"):
            continue
        fr = ch.refs.get("faction") or []
        f = fr[0].target if fr else None
        if not f:
            ld = [a for a, c in squad.get(ch.sid, []) if c == "leader"]
            f = ld[0] if ld else (squad[ch.sid][0][0] if squad.get(ch.sid) else None)
        dl = [M[r.target].name if r.target in M else r.target for r in ch.refs.get("dialogue", [])]
        pk = [M[r.target].name if r.target in M else r.target for r in ch.refs.get("dialogue package", [])]
        uniq.append(dict(sid=ch.sid, name=ch.name, origin=O.get(ch.sid), faction=fname(f) if f else None, cls=v.get("NPC class"),
                         dialogue=dl, package=pk, towns=tleader.get(ch.sid, []), vanilla=O.get(ch.sid, "") in CORE))
    facs = []
    used = set()
    for q in ctx.all("SQUAD_TEMPLATE"):
        used.update(r.target for r in q.refs.get("faction", []))
    for t in ctx.all("TOWN"):
        used.update(r.target for r in t.refs.get("faction", []))
    for f in ctx.all("FACTION"):
        if f.sid not in used:
            continue
        arch = behavior.archetype_of(f, O.get(f.sid), wr)
        mod = O.get(f.sid)
        parent = None
        if mod not in CORE and arch not in ("monster", None):
            for rx, p in BRANCH:
                if re.search(rx, f.name, re.I):
                    parent = p
                    break
        facs.append(dict(sid=f.sid, name=f.name, origin=mod, archetype=arch, towns=len(towns.get(f.sid, [])),
                         parent_guess=parent, units=sum(1 for u in uniq if u["faction"] == f.name)))
    out = dict(unique=uniq, factions=facs)
    json.dump(out, open(os.path.join(ROOT, "data", "lore_audit.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("unique", len(uniq), "vanilla", sum(u["vanilla"] for u in uniq), "factions", len(facs), "branch guesses", sum(1 for f in facs if f["parent_guess"]))


main()
