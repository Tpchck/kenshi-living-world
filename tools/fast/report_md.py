import json, sys, pickle, collections
sys.path.insert(0, r"C:\KenshiModMap\tools"); sys.path.insert(0, r"C:\KenshiModMap\tools\fast")
import ctx
a = json.load(open(ctx.OUT + "/wh_analysis.json", encoding="utf-8"))
ra = json.load(open(ctx.OUT + "/reassert.json", encoding="utf-8"))
M = pickle.load(open(ctx.OUT + "/merged.pkl", "rb"))
nm = lambda s: M[s].name if s in M else s
L = []
L.append("| Мод (WS id) | Файл | Записей | Новых | Изм. | Фракции / расы | Отряды | Старты | Пересечений с основой | Битых ссылок |")
L.append("|---|---|---|---|---|---|---|---|---|---|")
for p in a["passports"]:
    fac = [nm(x) for x in []]
    newfac = [M[s].name for s in M if False]
    fr = ", ".join(p["factions"][:0])
    # имена фракций/рас — уже английские из слитого контекста
    fsids = [s for s, i in M.items() if i.type_name in ("FACTION", "RACE") and s.endswith(p["file"])]
    names = sorted({M[s].name for s in fsids})
    starts = sorted({M[s].name for s, i in M.items() if i.type_name == "NEW_GAME_STARTOFF" and s.endswith(p["file"])})
    L.append(f"| {p['title']} ({p['id']}) | `{p['file']}` | {p['items']} | {sum(p['new_by_type'].values())} | {p['changed']} | "
             f"{'; '.join(names[:8]) + (' …' if len(names) > 8 else '') or '—'} | {p['squads']} | {'; '.join(starts) or '—'} | "
             f"{p['conflicts_with_base']} | {sum(p['broken_refs'].values())} |")
open(ctx.OUT + "/wh_table.md", "w", encoding="utf-8").write("\n".join(L))
# пересечения: по WH-моду — какие записи и сколько модов основы
by = collections.defaultdict(lambda: collections.defaultdict(set))
cats = collections.defaultdict(set)
for o in a["overlaps"]:
    if o["other_layer"] != "base": continue
    by[o["wh"]][(o["type"], o["name"])].add(o["other"]); cats[(o["wh"], o["type"], o["name"])] |= set(o["same_ref_cats"])
O = []
for w, recs in by.items():
    O.append(f"**{w}** — {len(recs)} записей:")
    for (t, n), mods in sorted(recs.items(), key=lambda x: -len(x[1])):
        c = ", ".join(sorted(cats[(w, t, n)])) or "разные поля"
        O.append(f"- {t} «{n}» — ещё {len(mods)} модов основы; общие списки: {c}")
    O.append("")
open(ctx.OUT + "/wh_overlaps.md", "w", encoding="utf-8").write("\n".join(O))
print("\n".join(L)); print(len(O), "overlap lines")
