#!/usr/bin/env python
"""REGISTRY: единый реестр мира (фракции, расы, города, персонажи) + как слои KMM их касаются.
Только чтение. python -I -X utf8 tools\\registry.py  ->  data/registry.json + docs/REGISTRY.md
"""
import sys, os, json, glob, time, collections, re

ROOT = r"C:\KenshiModMap"
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, os.path.join(ROOT, "tools", "build"))
import kmm_build, kmod

T0 = time.time()
FT = {0: "NONE", 1: "LAW", 2: "MILITARY", 3: "TRADER", 4: "CIVILIAN", 5: "DIPLOMAT", 6: "SLAVE", 7: "SLAVER",
      8: "BANDIT", 9: "ADVENTURER"}


def jload(rel, default=None):
    p = os.path.join(ROOT, rel)
    for _ in range(2):
        try:
            with open(p, encoding="utf8") as f:
                return json.load(f)
        except FileNotFoundError:
            return default
        except Exception:
            time.sleep(1)
    return default


def creator(sid):
    return sid.split("-", 1)[1] if "-" in sid else "?"


ctx = kmm_build.Ctx()
M = ctx.M
nm = lambda s: (M[s].name if s in M else s)

# ---------- снимок «до» (apply мутирует записи на месте) ----------
FACT = ctx.all("FACTION")
fids = [x.sid for x in FACT]
fset = set(fids)
rel_before = {x.sid: {r.target: r.v0 for r in x.refs.get("relations", [])} for x in FACT}
fac_races = {x.sid: [(r.target, r.v0) for r in x.refs.get("races", [])] for x in FACT}
fac_vals = {x.sid: dict(x.values) for x in FACT}

CHARS = {x.sid: x for x in ctx.all("CHARACTER")}
SQ = {x.sid: x for x in ctx.all("SQUAD_TEMPLATE")}
SQ.update({x.sid: x for x in ctx.all("UNIQUE_SQUAD_TEMPLATE")})
TOWNS = {x.sid: x for x in ctx.all("TOWN")}


def is_unique(c):
    return bool(c.values.get("unique"))


# ---------- персонаж -> фракция ----------
votes = collections.defaultdict(collections.Counter)   # char -> Counter(fid)
src = {}
leader_cnt = collections.defaultdict(collections.Counter)  # fid -> Counter(char) в слоте leader
sq_fac = {}
for sid, s in SQ.items():
    fr = [r.target for r in s.refs.get("faction", []) if r.target in fset]
    if fr:
        sq_fac[sid] = fr[0]
        for cat in ("leader", "squad", "squad2", "choosefrom list"):
            for r in s.refs.get(cat, []):
                if r.target in CHARS:
                    votes[r.target][fr[0]] += 1
                    src.setdefault(r.target, "squad")
                    if cat == "leader":
                        leader_cnt[fr[0]][r.target] += 1
town_owner = {}
for sid, t in TOWNS.items():
    fr = [r.target for r in t.refs.get("faction", []) if r.target in fset]
    town_owner[sid] = fr[0] if fr else None
for sid, t in TOWNS.items():
    of = town_owner[sid]
    if not of:
        continue
    for cat in ("residents", "bar squads", "roaming squads"):
        for r in t.refs.get(cat, []):
            s = SQ.get(r.target)
            if not s:
                continue
            for c2 in ("leader", "squad", "squad2", "choosefrom list"):
                for rr in s.refs.get(c2, []):
                    if rr.target in CHARS and rr.target not in votes:
                        votes[rr.target][of] += 1
                        src.setdefault(rr.target, "town")
char_fac = {}
multi = {}
for c, cnt in votes.items():
    char_fac[c] = cnt.most_common(1)[0][0]
    if len(cnt) > 1:
        multi[c] = dict(cnt)
for c, ch in CHARS.items():
    if c in char_fac:
        continue
    fr = [r.target for r in ch.refs.get("faction", []) if r.target in fset]
    if fr:
        char_fac[c] = fr[0]
        src[c] = "character"
char_races = {c: [r.target for r in ch.refs.get("race", [])] for c, ch in CHARS.items()}

# ---------- города ----------
cond = jload("build/KMM_Conductor/conductor.json") or jload("rules/conductor.json") or {}
outl = jload("build/KMM_Conductor/outlaws.json") or {}
herds = jload("build/KMM_Conductor/herds.json") or {}
tinfo = cond.get("town_info", {})
cfac = cond.get("factions", {})
cleanup = jload("rules/cleanup.json") or {}
camp_of = {c["camp"]: c for c in cleanup.get("camps", [])}
host_of = collections.defaultdict(list)
for c in cleanup.get("camps", []):
    host_of[c["host"]].append(c["camp"])
town_region, town_pos = {}, {}
for rg, rd in (outl.get("regions") or {}).items():
    for t in rd.get("towns", []):
        town_region[t["sid"]] = rg
        town_pos[t["sid"]] = (t.get("x"), t.get("z"))
for s, ti in tinfo.items():
    if ti.get("x") is not None:
        town_pos[s] = (ti["x"], ti["z"])
override_targets = set()
for t in TOWNS.values():
    for r in t.refs.get("override town", []):
        override_targets.add(r.target)
# town -> персонажи (через резидентов/бары)
town_chars = {}
for sid, t in TOWNS.items():
    cs = set()
    for cat in ("residents", "bar squads", "roaming squads"):
        for r in t.refs.get(cat, []):
            s = SQ.get(r.target)
            if s:
                for c2 in ("leader", "squad", "squad2", "choosefrom list"):
                    for rr in s.refs.get(c2, []):
                        if rr.target in CHARS:
                            cs.add(rr.target)
    town_chars[sid] = cs

# ---------- расы ----------
ra = jload("data/race_audit.json") or {}
race_rows = {r["sid"]: r for r in ra.get("rows", [])}
alive = collections.Counter()
for c, rs in char_races.items():
    for r in set(rs):
        alive[r] += 1
for sid, s in SQ.items():
    for r in s.refs.get("race override", []):
        alive[r.target] += 0
race_in_fac = collections.defaultdict(set)
for f, lst in fac_races.items():
    for r, w in lst:
        race_in_fac[r].add(f)

# ---------- гардероб / каталог ----------
ward = (jload("rules/streams/wardrobe.json") or {}).get("context", {}).get("lore_hard", {})
ward_tags = collections.defaultdict(list)
fname2ids = collections.defaultdict(list)
for f in fids:
    fname2ids[nm(f)].append(f)


def walk_ward(key, node):
    if isinstance(node, dict):
        if "factions" in node:
            fl = node["factions"]
            for n in (fl if isinstance(fl, (list, dict)) else []):
                ward_tags[n].append(key + (":" + node["id"] if "id" in node else ""))
        for k in ("char_factions",):
            if k in node and isinstance(node[k], list):
                for n in node[k]:
                    ward_tags[n].append(key + ":" + node.get("id", "") + "(char)")
    elif isinstance(node, list):
        if node and all(isinstance(x, str) for x in node):
            for n in node:
                ward_tags[n].append(key)
        else:
            for x in node:
                walk_ward(key, x)


for k, v in ward.items():
    walk_ward(k, v)
cat = (jload("data/catalog.json") or {}).get("items", [])
culture = collections.defaultdict(list)
wornby = collections.defaultdict(list)
for it in cat:
    o = it.get("origin", "")
    if o.startswith("culture:"):
        culture[o[8:]].append(it)
    for fn, n in (it.get("worn_by") or {}).items():
        wornby[fn].append((n, it))

# ---------- слои KMM ----------
layer_files = sorted(glob.glob(os.path.join(ROOT, "build", "KMM_*", "KMM_*.mod")))
layers = {}
for p in layer_files:
    name = os.path.basename(p)[:-4]
    mf = None
    for _ in range(2):
        try:
            mf = kmod.read(p)
            break
        except Exception:
            time.sleep(1)
    if mf is not None:
        layers[name] = mf
layer_sids = {n: set(i.sid for i in mf.items) for n, mf in layers.items()}
rel_changes = collections.defaultdict(lambda: collections.defaultdict(list))  # fid -> layer -> [(tgt,before,after)]
Mf = dict(M)
cur_rel = {f: dict(r) for f, r in rel_before.items()}
for name, mf in layers.items():
    if name == "KMM_Cleanup":
        continue
    kmod.apply(Mf, mf)
    for it in mf.items:
        if it.sid in fset and "relations" in it.refs:
            now = {r.target: r.v0 for r in Mf[it.sid].refs.get("relations", [])}
            old = cur_rel[it.sid]
            for t in set(now) | set(old):
                if now.get(t) != old.get(t):
                    rel_changes[it.sid][name].append((t, old.get(t), now.get(t)))
            cur_rel[it.sid] = now
new_factions = [s for s, it in Mf.items() if it.type_name == "FACTION" and s not in fset]

# sid -> фракция для «касаний» слоёв
sid_fac = {}
for f in fids:
    sid_fac[f] = f
for s, f in town_owner.items():
    if f:
        sid_fac[s] = f
for s, f in sq_fac.items():
    sid_fac[s] = f
for c, f in char_fac.items():
    sid_fac[c] = f
touch = collections.defaultdict(collections.Counter)
for n, ss in layer_sids.items():
    for s in ss:
        f = sid_fac.get(s)
        if f:
            touch[f][n] += 1

# ---------- сборка записей фракций ----------
members = collections.defaultdict(list)
for c, f in char_fac.items():
    members[f].append(c)
ftowns = collections.defaultdict(list)
for s, f in town_owner.items():
    if f:
        ftowns[f].append(s)
gangs = outl.get("gangs", {})
fac_regions = collections.defaultdict(set)
for rg, rd in (outl.get("regions") or {}).items():
    for g in rd.get("gangs", []):
        fac_regions[g].add(rg)
    for t in rd.get("towns", []):
        if t.get("fid"):
            fac_regions[t["fid"]].add(rg)


def rel_top(rd, n=5):
    items = [(t, v) for t, v in rd.items() if t in fset and v is not None]
    al = sorted(items, key=lambda x: -x[1])[:n]
    en = sorted(items, key=lambda x: x[1])[:n]
    return ([{"sid": t, "name": nm(t), "v": v} for t, v in al if v > 0],
            [{"sid": t, "name": nm(t), "v": v} for t, v in en if v < 0])


def gear(name):
    cu = sorted(culture.get(name, []), key=lambda i: -(i.get("stat_score") or 0))[:5]
    wb = sorted(wornby.get(name, []), key=lambda x: -x[0])[:5]
    return ([{"name": i["name"], "tier": i.get("tier"), "type": i.get("type")} for i in cu],
            [{"name": i["name"], "n": n} for n, i in wb])


F = {}
for f in fids:
    it = M[f]
    name = it.name
    mem = members.get(f, [])
    uniq = [c for c in mem if is_unique(CHARS[c])]
    rc = collections.Counter()
    for c in mem:
        for r in set(char_races.get(c, [])):
            rc[nm(r)] += 1
    ts = []
    for s in ftowns.get(f, []):
        ti = tinfo.get(s, {})
        ts.append({"sid": s, "name": nm(s), "type": TOWNS[s].values.get("type"), "kind": ti.get("kind"),
                   "override": s in override_targets, "pos": town_pos.get(s), "region": town_region.get(s),
                   "camp": s in camp_of, "host_of_camps": len(host_of.get(s, [])), "in_conductor": s in tinfo})
    ab, eb = rel_top(rel_before[f])
    aa, ea = rel_top(cur_rel[f])
    cg, wg = gear(name)
    cf = cfac.get(f)
    ch = {}
    for lay, lst in rel_changes.get(f, {}).items():
        ch[lay] = [{"sid": t, "name": nm(t), "before": b, "after": a} for t, b, a in lst]
    F[f] = {
        "sid": f, "name": name, "creator": creator(f), "origin_last": ctx.origin.get(f),
        "hidden": bool(fac_vals[f].get("not real")), "ftype": FT.get(fac_vals[f].get("fundamental type"), "?"),
        "members": len(mem), "uniques": sorted(nm(c) for c in uniq),
        "leaders": [nm(c) for c, _ in leader_cnt[f].most_common(5) if is_unique(CHARS[c])] or
                   [nm(c) for c, _ in leader_cnt[f].most_common(3)],
        "faction_races": [{"name": nm(r), "w": w} for r, w in fac_races[f]],
        "char_races": dict(rc.most_common()),
        "towns": ts, "regions": sorted(fac_regions.get(f, [])),
        "allies_before": ab, "enemies_before": eb, "allies_after": aa, "enemies_after": ea,
        "kmm_relation_changes": ch,
        "conductor": ({k: cf.get(k) for k in ("arch", "wealth", "strength", "ambition", "relic", "capital", "town_names")}
                      if cf else None),
        "gear_culture": cg, "gear_worn": wg, "wardrobe_tags": sorted(set(ward_tags.get(name, []))),
        "outlaw_gang": gangs.get(f), "kmm_layers": dict(touch.get(f, {})),
        "cleanup_camp_towns": [t["name"] for t in ts if t["camp"]],
        "cleanup_hosts": [t["name"] for t in ts if t["host_of_camps"]],
    }

# ---------- города (реестр) ----------
TW = []
for s, t in TOWNS.items():
    f = town_owner[s]
    ti = tinfo.get(s, {})
    TW.append({"sid": s, "name": t.name, "creator": creator(s), "owner": f, "owner_name": nm(f) if f else None,
               "type": t.values.get("type"), "kind": ti.get("kind"), "pos": town_pos.get(s),
               "region": town_region.get(s), "override": s in override_targets,
               "overrides": len(t.refs.get("override town", [])), "in_conductor": s in tinfo,
               "camp": s in camp_of, "camp_host": camp_of[s]["host"] if s in camp_of else None,
               "host_of": len(host_of.get(s, [])), "chars": len(town_chars[s])})

# ---------- расы (реестр) ----------
RC = []
for s, it in ((x.sid, x) for x in ctx.all("RACE")):
    r = race_rows.get(s, {})
    RC.append({"sid": s, "name": it.name, "mod": r.get("mod") or creator(s), "vanilla": r.get("vanilla"),
               "base": r.get("base"), "playable": r.get("playable"), "robot": r.get("robot"),
               "alive": alive.get(s, 0), "in_factions": len(race_in_fac.get(s, ())),
               "used_in": r.get("used_in")})
dupe_races = ra.get("dupes", [])

# ---------- дубликаты / пробелы ----------
by_name = collections.defaultdict(list)
for f in fids:
    by_name[F[f]["name"].strip().lower()].append(f)
dup_fac = {n: v for n, v in by_name.items() if len(v) > 1}
gaps = {
    "factions_no_chars": [f for f in fids if F[f]["members"] == 0],
    "factions_no_towns": [f for f in fids if not F[f]["towns"]],
    "factions_empty": [f for f in fids if F[f]["members"] == 0 and not F[f]["towns"]],
    "towns_no_owner": [t["sid"] for t in TW if not t["owner"] and not t["override"]],
    "towns_no_owner_override": [t["sid"] for t in TW if not t["owner"] and t["override"]],
    "uniques_no_faction": [c for c, ch in CHARS.items() if is_unique(ch) and c not in char_fac],
    "chars_no_faction": [c for c in CHARS if c not in char_fac],
    "chars_multi_faction": list(multi),
    "towns_not_in_conductor": [t["sid"] for t in TW if t["owner"] and not t["override"] and not t["in_conductor"]],
    "conductor_towns_missing_in_game": [s for s in tinfo if s not in TOWNS],
    "conductor_factions_missing_in_game": [s for s in cfac if s not in fset],
    "gang_fids_missing": [s for s in gangs if s not in fset],
}
layers_info = {n: {"items": len(mf.items), "factions": sum(1 for i in mf.items if i.sid in fset),
                   "towns": sum(1 for i in mf.items if i.sid in TOWNS),
                   "chars": sum(1 for i in mf.items if i.sid in CHARS)} for n, mf in layers.items()}

REG = {"generated": time.strftime("%Y-%m-%d %H:%M"),
       "counts": {"factions": len(fids), "hidden": sum(F[f]["hidden"] for f in fids), "characters": len(CHARS),
                  "uniques": sum(1 for c in CHARS.values() if is_unique(c)), "assigned_chars": len(char_fac),
                  "towns": len(TOWNS), "town_overrides": sum(t["override"] for t in TW),
                  "races": len(RC), "races_alive": sum(1 for r in RC if r["alive"]),
                  "kmm_new_factions": len(new_factions), "layers": len(layers)},
       "layers": layers_info, "kmm_new_factions": new_factions, "factions": F, "towns": TW, "races": RC,
       "race_dupes": dupe_races, "duplicate_factions": dup_fac, "gaps": gaps,
       "char_source": dict(collections.Counter(src.values()))}
with open(os.path.join(ROOT, "data", "registry.json"), "w", encoding="utf8") as fh:
    json.dump(REG, fh, ensure_ascii=False, indent=1, default=list)

# ---------- Markdown ----------
L = []
w = L.append
c = REG["counts"]
w("# REGISTRY - реестр мира\n")
w(f"Генерация: `python -I -X utf8 tools\\registry.py` ({REG['generated']}), только чтение. Полные данные: `data/registry.json`.")
w("Слои и механики: [STATUS.md](STATUS.md), [MECHANICS.md](MECHANICS.md). Данные «до» = 662 мода без наших слоёв, «после» = с KMM-слоями (без Cleanup, он для новой игры).\n")
w("## Сводка\n")
w("| что | число |\n|---|---|")
for k, v in c.items():
    w(f"| {k} | {v} |")
w(f"\nИсточник фракции персонажа: {REG['char_source']}.\n")
w("### Слои KMM\n")
w("| слой | записей | фракций | городов | персонажей |\n|---|---|---|---|---|")
for n, d in layers_info.items():
    w(f"| {n} | {d['items']} | {d['factions']} | {d['towns']} | {d['chars']} |")
if new_factions:
    w("\nНовые фракции, созданные слоями: " + ", ".join(f"{nm(s)} ({s})" for s in new_factions))
w("\n## Пробелы\n")
for k, v in gaps.items():
    w(f"- **{k}**: {len(v)}")
w("\n### Фракции с одинаковым именем\n")
w("| имя | sid (создатель, перс./города) |\n|---|---|")
for n, v in sorted(dup_fac.items()):
    w(f"| {F[v[0]]['name']} | " + "; ".join(f"`{s}` ({F[s]['members']}/{len(F[s]['towns'])})" for s in v) + " |")
w("\n### Пустые фракции (0 персонажей и 0 городов)\n")
w("| фракция | создатель | скрыта | тип | слои |\n|---|---|---|---|---|")
for f in gaps["factions_empty"]:
    x = F[f]
    w(f"| {x['name']} (`{f}`) | {x['creator']} | {'да' if x['hidden'] else ''} | {x['ftype']} | {','.join(x['kmm_layers']) or '-'} |")
w("\n### Города без владельца (не override)\n")
w("| город | sid | тип | регион |\n|---|---|---|---|")
for s in gaps["towns_no_owner"][:200]:
    t = next(t for t in TW if t["sid"] == s)
    w(f"| {t['name']} | `{s}` | {t['type']} | {t['region'] or ''} |")
if len(gaps["towns_no_owner"]) > 200:
    w(f"... и ещё {len(gaps['towns_no_owner']) - 200} (см. JSON)")
w("\n### Уники без фракции\n")
for s in gaps["uniques_no_faction"][:150]:
    w(f"- {nm(s)} (`{s}`)")
if len(gaps["uniques_no_faction"]) > 150:
    w(f"- ... ещё {len(gaps['uniques_no_faction']) - 150}")
w("\n## Расы\n")
w(f"Всего {len(RC)}; в мире есть персонажи у {c['races_alive']}. Ванильных: {sum(1 for r in RC if r['vanilla'])}. Группы дублей из race_audit: {len(dupe_races)}.\n")
w("### Ванильные и живые расы\n")
w("| раса | ваниль | живых перс. | фракций | playable |\n|---|---|---|---|---|")
for r in sorted(RC, key=lambda r: (-bool(r["vanilla"]), -r["alive"])):
    if r["vanilla"] or r["alive"] >= 5:
        w(f"| {r['name']} | {'да' if r['vanilla'] else r['mod']} | {r['alive']} | {r['in_factions']} | {r['playable']} |")
w("\n### Модовые расы с живыми персонажами (<5) и без - счётчик\n")
mr = [r for r in RC if not r["vanilla"]]
w(f"Модовых {len(mr)}; живых 1-4: {sum(1 for r in mr if 0 < r['alive'] < 5)}; ни одного живого: {sum(1 for r in mr if r['alive'] == 0)}; без основы (base): {sum(1 for r in mr if not r['base'])}.")
w("\n### Дубли рас (race_audit)\n")
for g in dupe_races:
    if isinstance(g, list) and g and isinstance(g[0], list):
        w(f"- {len(g)} рас-близнецов: " + ", ".join(x[1] for x in g[:6]) + (" ..." if len(g) > 6 else ""))
    else:
        w("- " + str(g)[:200])
w("\n## Города\n")
w("Первичные (не override) города; тип - число из TOWN.type, kind - из conductor.\n")
w("| город | владелец | тип/kind | регион | в conductor | лагерь Cleanup | персон. |\n|---|---|---|---|---|---|---|")
for t in sorted(TW, key=lambda t: (t["owner_name"] or "~", t["name"])):
    if t["override"]:
        continue
    cp = ("лагерь->" + nm(t["camp_host"])) if t["camp"] else ("хост " + str(t["host_of"]) if t["host_of"] else "")
    w(f"| {t['name']} | {t['owner_name'] or '-'} | {t['type']}/{t['kind'] or ''} | {t['region'] or ''} | {'да' if t['in_conductor'] else ''} | {cp} | {t['chars']} |")
w("\n## Фракции\n")
act = [f for f in fids if f not in gaps["factions_empty"]]
act.sort(key=lambda f: (-F[f]["members"], F[f]["name"]))
fmt = lambda lst: ", ".join(f"{x['name']} {x['v']}" for x in lst) or "-"
for f in act:
    x = F[f]
    w(f"### {x['name']}  `{f}`")
    w(f"- создатель: {x['creator']}; тип: {x['ftype']}{'; скрыта в UI (реальна в мире)' if x['hidden'] else ''}; персонажей: {x['members']}, уников: {len(x['uniques'])}")
    if x["uniques"]:
        w(f"- уники: {', '.join(x['uniques'][:12])}{' ...' if len(x['uniques']) > 12 else ''}")
    if x["leaders"]:
        w(f"- лидеры: {', '.join(x['leaders'])}")
    fr = ", ".join(f"{r['name']}({r['w']})" for r in x["faction_races"][:6]) or "-"
    cr = ", ".join(f"{k} {v}" for k, v in list(x["char_races"].items())[:6]) or "-"
    w(f"- расы фракции: {fr}; фактические: {cr}")
    if x["towns"]:
        tl = ", ".join(f"{t['name']}[{t['kind'] or t['type']}]" for t in x["towns"])
        w(f"- города ({len(x['towns'])}): {tl[:500]}")
    if x["regions"]:
        w(f"- регионы: {', '.join(x['regions'])}")
    w(f"- союзники после: {fmt(x['allies_after'])}; враги после: {fmt(x['enemies_after'])}")
    if x["kmm_relation_changes"]:
        s = []
        for lay, lst in x["kmm_relation_changes"].items():
            s.append(f"{lay}: " + ", ".join(f"{d['name']} {d['before']}->{d['after']}" for d in lst[:4]) + (f" (+{len(lst) - 4})" if len(lst) > 4 else ""))
        w("- KMM-отношения: " + " | ".join(s))
    if x["conductor"]:
        d = x["conductor"]
        w(f"- conductor: arch={d['arch']}, wealth={d['wealth']}, strength={d['strength']}, ambition={d['ambition']}, relic={d['relic']}")
    if x["gear_culture"] or x["gear_worn"]:
        w(f"- снаряжение: культура: {', '.join(g['name'] for g in x['gear_culture']) or '-'}; носят: {', '.join(g['name'] + ' ' + str(g['n']) for g in x['gear_worn']) or '-'}")
    if x["wardrobe_tags"]:
        w(f"- гардероб: {', '.join(x['wardrobe_tags'])}")
    if x["outlaw_gang"]:
        w(f"- банда outlaws: {x['outlaw_gang']}")
    if x["cleanup_camp_towns"] or x["cleanup_hosts"]:
        w(f"- Cleanup: лагеря {x['cleanup_camp_towns']}, хост {x['cleanup_hosts']}")
    if x["kmm_layers"]:
        w(f"- слои KMM: {', '.join(f'{k} {v}' for k, v in x['kmm_layers'].items())}")
    w("")
with open(os.path.join(ROOT, "docs", "REGISTRY.md"), "w", encoding="utf8") as fh:
    fh.write("\n".join(L) + "\n")
print("OK", round(time.time() - T0, 1), "s;", len(L), "lines;", c)
for k, v in gaps.items():
    print(k, len(v))
print("dups", len(dup_fac), "layers", list(layers))
