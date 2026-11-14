"""Проверка data/vassals_proposal.json: имена против conductor.json и конфликты never_ally.
Запуск: python -I -X utf8 tools/vassals_audit.py"""
import json, os, itertools
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = json.load(open(os.path.join(ROOT, "data", "vassals_proposal.json"), encoding="utf-8"))
C = json.load(open(os.path.join(ROOT, "build", "KMM_Conductor", "conductor.json"), encoding="utf-8"))
reg = json.load(open(os.path.join(ROOT, "data", "registry.json"), encoding="utf-8"))
names = {f["name"] for f in C["factions"].values()}
towns = {t["name"]: t for t in (reg["towns"] if isinstance(reg["towns"], list) else reg["towns"].values())}
err = []

def chk(n, where):
    if n not in names:
        err.append(f"нет в conductor: {n!r} ({where})")

names_used = []
for v in P["vassals"]:
    chk(v["vassal"], "vassal"); chk(v["overlord"], "overlord")
for r in P["regional_allies"]:
    chk(r["a"], "ally"); chk(r["b"], "ally")
N = P["never_ally"]
for r in N["rebels"]:
    chk(r["rebel"], "rebel")
    for x in r["against"]: chk(x, "rebel.against")
for w in N["state_wars"]:
    chk(w["a"], "war"); chk(w["b"], "war")
for b in N["blocs"]:
    for x in b["members"] + b["never_with"]: chk(x, "bloc")
for h in P["black_markets"]:
    t = towns.get(h["hub"])
    if not t: err.append(f"нет города {h['hub']}")
    elif t["owner_name"] != h["owner"]: err.append(f"{h['hub']}: владелец {t['owner_name']} != {h['owner']}")
M = P["market_rules"]
for k in ("sellers", "buyers", "buyer_forbidden"):
    for g, lst in M[k].items():
        for x in lst: chk(x, f"market.{k}.{g}")

# граф запретов
ban = set()
def add(a, b): ban.add(frozenset((a, b)))
treaty = [(v["overlord"], v["vassal"]) for v in P["vassals"]] + [(r["a"], r["b"]) for r in P["regional_allies"]]
adj = {}
for a, b in treaty:
    adj.setdefault(a, set()).add(b); adj.setdefault(b, set()).add(a)
for r in N["rebels"]:
    for s in r["against"]:
        add(r["rebel"], s)
        if r["closure"]:
            for z in adj.get(s, ()): add(r["rebel"], z)
for w in N["state_wars"]: add(w["a"], w["b"])
for b in N["blocs"]:
    for m in b["members"]:
        for o in b["never_with"]: add(m, o)
    for m, o in itertools.combinations(b["members"], 2): ban.discard(frozenset((m, o)))
for a, b in treaty:
    if frozenset((a, b)) in ban: err.append(f"КОНФЛИКТ договор против запрета: {a} - {b}")
# транзитивно: A(vassal/ally) B, B ally C, запрет A-C допустим, но показываем как предупреждение
warn = []
for a in adj:
    for b in adj[a]:
        for c in adj[b]:
            if c != a and frozenset((a, c)) in ban and a < c:
                warn.append(f"через {b}: {a} .. {c} (запрет, нужен closure-check)")
print("фракций в conductor:", len(names), "| вассалов:", len(P["vassals"]), "| союзов:", len(P["regional_allies"]), "| запретов:", len(ban))
for e in err: print("ERR", e)
for w in warn: print("WARN", w)
print("OK" if not err else f"ошибок: {len(err)}")
