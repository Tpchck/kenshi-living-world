"""docs/LORE_MAP.md — опорная карта ванильного лора из данных (только ванильная цепочка, без вики)."""
import collections
import sys

sys.path.insert(0, r"C:\KenshiModMap\tools")
import kmod  # noqa: E402

D = "C:/Program Files (x86)/Steam/steamapps/common/Kenshi/data/"
CHAIN = ["gamedata.base", "Newwworld.mod", "Dialogue.mod", "rebirth.mod"]  # порядок по зависимостям в заголовках
M = kmod.load_chain([D + f for f in CHAIN])
T = lambda t: [i for i in M.values() if i.type_name == t]  # noqa: E731
nm = lambda s: M[s].name if s in M else "?"  # noqa: E731

towns = T("TOWN")
variant_sids = {r.target for t in towns for r in t.refs.get("override town", [])}
base_towns = [t for t in towns if t.sid not in variant_sids]
fac_of = lambda it: it.refs.get("faction", [None])[0].target if it.refs.get("faction") else None  # noqa: E731

# лидеры: персонажи из условий world states → их фракция через отряды
char_fac = {}
for sq in T("SQUAD_TEMPLATE") + T("UNIQUE_SQUAD_TEMPLATE"):
    f = fac_of(sq)
    if f:
        for cat in ("leader", "squad", "squad2"):
            for r in sq.refs.get(cat, []):
                char_fac.setdefault(r.target, f)
STATE = {1: "жив", 0: "мёртв", 2: "в плену"}
ws_info = {}
for w in T("WORLD_EVENT_STATE"):
    conds = []
    for cat, neg in (("NPC is", ""), ("NPC is NOT", "НЕ ")):
        for r in w.refs.get(cat, []):
            conds.append((r.target, f"{nm(r.target)} {neg}{STATE.get(r.v0, r.v0)}"))
    for cat, txt in (("town okay", "город цел"), ("player ally", "игрок — союзник"), ("player enemy", "игрок — враг")):
        for r in w.refs.get(cat, []):
            conds.append((None, f"{nm(r.target)}: {txt if r.v0 else 'НЕ ' + txt}"))
    ws_info[w.sid] = conds

# последствия: базовый город → вариант (плейтест) при условиях
consequences = collections.defaultdict(list)  # фракция-владелец базового города -> строки
leaders = collections.defaultdict(set)
for t in base_towns:
    owner = fac_of(t)
    for r in t.refs.get("override town", []):
        v = M.get(r.target)
        if not v:
            continue
        # val0 ссылки город→world state: 1 = состояние должно быть истинным, 0 = ложным (fcs.def)
        conds = [(cs, txt if w.v0 else f"НЕ ({txt})") for w in v.refs.get("world state", []) for cs, txt in ws_info.get(w.target, [])]
        for csid, _ in conds:
            if csid and char_fac.get(csid):
                leaders[char_fac[csid]].add(nm(csid))
        newowner = nm(fac_of(v)) if fac_of(v) else "—"
        consequences[owner].append(f"{t.name} → «{v.name}» (владелец: {newowner}) если {'; '.join(c for _, c in conds) or 'условие не задано'}")

facs = [f for f in T("FACTION") if not f.values.get("not real")]
towns_by = collections.defaultdict(list)
for t in base_towns:
    if fac_of(t):
        towns_by[fac_of(t)].append(t.name)
rows = []
for f in sorted(facs, key=lambda f: -len(towns_by.get(f.sid, []))):
    tw = towns_by.get(f.sid, [])
    if not tw and not consequences.get(f.sid):
        continue
    biomes = sorted({nm(r.target) for r in f.refs.get("biomes", [])})
    rel = f.refs.get("relations", [])
    allies = [f"{nm(r.target)} {r.v0:+d}" for r in sorted(rel, key=lambda r: -r.v0) if r.v0 >= 50][:5]
    enemies = [f"{nm(r.target)} {r.v0:+d}" for r in sorted(rel, key=lambda r: r.v0) if r.v0 <= -50][:5]
    rows.append((f, tw, biomes, sorted(leaders.get(f.sid, [])), len(consequences.get(f.sid, [])), allies, enemies))

L = ["# LORE_MAP — опорная карта ванильного лора (из данных, 2026-11-11)",
     "Источник — только ванильная цепочка gamedata.base → Newwworld.mod → Dialogue.mod → rebirth.mod (порядок по зависимостям в заголовках), "
     "собрано `tools\\fast\\lore_map.py`. Без вики и без модов. Регион = список `biomes` у фракции (её территория). "
     "Лидеры = персонажи из условий world states, сменяющих владельцев городов. «НЕ (X жив)» = X мёртв или в плену.", "",
     f"Фракций с городами/лагерями: {len(rows)}; базовых городов: {len(base_towns)}; вариантов override: {len(variant_sids)}; world states: {len(T('WORLD_EVENT_STATE'))}.", "",
     "## Фракции", "| Фракция | Города/лагеря | Регион (biomes) | Лидеры (из world states) | Override-вариантов | Союзы (≥50) | Вражда (≤−50) |",
     "|---|---|---|---|---|---|---|"]
for f, tw, b, ld, nc, al, en in rows:
    L.append(f"| {f.name} | {', '.join(tw[:8]) + (f' (+{len(tw) - 8})' if len(tw) > 8 else '') or '—'} | {', '.join(b[:4]) or '—'} | "
             f"{', '.join(ld[:5]) or '—'} | {nc} | {', '.join(al) or '—'} | {', '.join(en) or '—'} |")
L += ["", "## World states: что происходит со смертью/пленом лидеров (базовый город → вариант)"]
for f, *_ in rows:
    cs = consequences.get(f.sid)
    if cs:
        L.append(f"**{f.name}**")
        L += [f"- {c}" for c in cs[:12]] + ([f"- … ещё {len(cs) - 12}"] if len(cs) > 12 else [])
open(r"C:\KenshiModMap\docs\LORE_MAP.md", "w", encoding="utf-8").write("\n".join(L) + "\n")
print(len(rows), "factions;", sum(len(c) for c in consequences.values()), "consequences")
