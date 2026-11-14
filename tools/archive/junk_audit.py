r"""Аудит «мусора» от модов (только чтение): недостижимые записи, отладка/заглушки, битые ссылки, near-дубли, мёртвый груз.
python -I -X utf8 tools\junk_audit.py  -> data\junk_audit.json + docs\JUNK_AUDIT.md   (~1 мин)

Метод достижимости: граф ссылок итоговой цепочки (ctx.M + build\KMM_*\*.mod). Корни = записи ванили (gamedata.base) и
типы мира (TOWN, NEW_GAME_STARTOFF, BIOMES, BIOME_GROUP, FACTION_CAMPAIGN, RESEARCH, ...). Рёбра = любые ссылки КРОМЕ
условий/ограничений (races exclude, conditions, relations, ingredients, goes well with ...), то есть только «порождает/продаёт/
выдаёт/открывает». Запись, не достижимая из корней, в игре не появится (кроме ручной выдачи через консоль/ванильные движковые вызовы).
Это оценка, не истина: нативные движковые вызовы по имени не видны. Не пишет ничего, кроме data\junk_audit.json и docs\JUNK_AUDIT.md."""
import collections
import json
import os
import re
import sys

ROOT = r"C:\KenshiModMap"
sys.path[:0] = [ROOT + r"\tools", ROOT + r"\tools\build"]
import kmod  # noqa: E402
import kmm_build  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# категории ссылок, которые НЕ порождают цель (условия, запреты, связи, сырьё)
NOSPAWN = {"races exclude", "races", "overlap items", "goes well with", "goes badly with", "part coverage", "conditions",
           "is character", "my faction", "target faction", "in town of", "target race", "my race", "my subrace", "no target race",
           "target has item", "has package", "world state", "target carrying character", "NPC is", "NPC is NOT", "player ally",
           "player enemy", "trigger player ally", "loss trigger", "victory trigger", "relations", "coexistence", "no-go zones",
           "forbidden items", "illegal goods", "illegal buildings", "happy buildings", "ingredients", "inherits from", "inheritsFrom",
           "weapon level", "town okay", "faction relations", "change relations", "unlocks", "color", "material", "material female",
           "material match", "stats", "personality", "physics attachment", "race damage", "animation files", "combat anatomy",
           "special food", "hair colors", "hairstyles", "ambient sound", "sounds", "trade prices", "trade culture", "bounty factions",
           "AI contract", "shopping", "dialogue package player", "snaps to", "z incompatible parts", "interior mask", "wall subsections",
           "shares interiors with", "override town", "default resident"}
# типы-корни помимо ванили (мир/игрок сам их запускает)
ROOT_TYPES = {"TOWN", "NEW_GAME_STARTOFF", "BIOMES", "BIOME_GROUP", "FACTION_CAMPAIGN", "RESEARCH", "UNIQUE_SQUAD_TEMPLATE",
              "DIPLOMATIC_ASSAULTS", "SINGLE_DIPLOMATIC_ASSAULT", "ROAD", "ARTIFACTS", "ITEM_PLACEMENT_GROUP", "CONSTANTS",
              "FACTION_TEMPLATE", "WORLD_EVENT_STATE", "WEATHER", "SEASON", "FARM_DATA", "ZONE_MAP"}
CORE = {"gamedata.base", "rebirth.mod", "Newwworld.mod", "Dialogue.mod"}
VANILLA = "gamedata.base"
# типы, о которых имеет смысл говорить игроку
KEY_TYPES = ["ARMOUR", "WEAPON", "CROSSBOW", "ITEM", "CONTAINER", "MAP_ITEM", "CHARACTER", "SQUAD_TEMPLATE", "FACTION", "RACE",
             "DIALOGUE", "DIALOGUE_PACKAGE", "VENDOR_LIST", "BUILDING", "TOWN", "ANIMAL_CHARACTER", "RESEARCH", "HEAD"]
ITEM_TYPES = ["ARMOUR", "WEAPON", "CROSSBOW", "ITEM", "CONTAINER", "MAP_ITEM"]
JUNK_RX = re.compile(r"(?i)(\btest\b|\btesting\b|debug|(?<!training )dummy\b|placeholder|\bcopy\b|\btmp\b|\btemp\b|\bunused\b|\bdelete|\bdo not\b|"
                     r"\bxxx|#|\(test\)|\bwip\b|\bdupe\b|\bdup\b|--discard--)")


def creator(sid):
    return sid.split("-", 1)[1] if "-" in sid else sid


def load_after(ctx):
    M = dict(ctx.M)
    bd = ROOT + r"\build"
    kmm = set()
    for d in sorted(os.listdir(bd)):
        p = os.path.join(bd, d, d + ".mod")
        if d.startswith("KMM_") and os.path.exists(p):
            m = kmod.read(p)
            kmod.apply(M, m)
            for it in m.items:
                if not creator(it.sid).startswith("KMM_") and d != "KMM_Merged":
                    pass
            kmm |= {it.sid for it in m.items}
    return M, kmm


def reach(M, rejected):
    seen, st = set(), []
    for s, it in M.items():
        if s in rejected:
            continue
        if creator(s) == VANILLA or it.type_name in ROOT_TYPES:
            seen.add(s)
            st.append(s)
    while st:
        it = M[st.pop()]
        for cat, rs in it.refs.items():
            if cat in NOSPAWN:
                continue
            for r in rs:
                t = r.target
                if t in M and t not in seen and t not in rejected:
                    seen.add(t)
                    st.append(t)
    return seen


def main():
    ctx = kmm_build.Ctx()
    M, kmm_sids = load_after(ctx)
    rej = ctx.rejected
    R = reach(M, rej)
    # --- кто на что ссылается (для «чем держится»)
    inbound = collections.Counter()
    for it in M.values():
        for cat, rs in it.refs.items():
            if cat in NOSPAWN:
                continue
            for r in rs:
                inbound[r.target] += 1

    def own(it):  # запись создана модом (не ваниль, не rejected, не заглушка отсутствующего мода)
        c = creator(it.sid)
        return c != VANILLA and it.sid not in rej and it.sid not in phantom

    def mod_of(it):
        c = creator(it.sid)
        return c

    present = {n for n, _, _ in ctx.layers} | CORE
    present_cre = {creator(s) for s in M if creator(s) in present}
    phantom = {s for s, it in M.items() if creator(s) not in present and not creator(s).startswith("KMM_") and s not in rej}
    ph_type = collections.Counter(M[s].type_name for s in phantom)
    ph_carrier = collections.Counter(ctx.origin.get(s, "KMM/?") for s in phantom)
    ph_cre = collections.Counter(creator(s) for s in phantom)
    ph_reach = sum(1 for s in phantom if s in R)
    try:
        cat = json.load(open(ROOT + r"\data\catalog.json", encoding="utf-8"))["items"]
        cat_sids = {x["sid"] for x in cat}
    except Exception:
        cat_sids = set()
    out = {"counts": {"records": len(M), "reachable": len(R), "rejected_in_chain": sum(1 for s in M if s in rej)}}
    # 1. недостижимые по типам и модам
    unreach = {}
    mod_stats = collections.defaultdict(lambda: {"created": 0, "key_created": 0, "key_reached": 0, "reach_all": 0, "types": collections.Counter()})
    for s, it in M.items():
        if not own(it):
            continue
        c = mod_of(it)
        st = mod_stats[c]
        st["created"] += 1
        ok = s in R
        st["reach_all"] += ok
        if it.type_name in KEY_TYPES:
            st["key_created"] += 1
            st["key_reached"] += ok
            if not ok:
                st["types"][it.type_name] += 1
        if it.type_name in KEY_TYPES and not ok:
            u = unreach.setdefault(it.type_name, {"total_mod_created": 0, "unreachable": 0, "by_mod": collections.Counter(), "examples": []})
            u["unreachable"] += 1
            u["by_mod"][c] += 1
            if len(u["examples"]) < 12:
                u["examples"].append([it.sid, it.name])
    for s, it in M.items():
        if own(it) and it.type_name in unreach:
            unreach[it.type_name]["total_mod_created"] += 1
    for t, u in unreach.items():
        u["by_mod"] = u["by_mod"].most_common(15)
    out["unreachable"] = unreach
    out["phantom_stubs"] = {"total": len(phantom), "reachable": ph_reach, "by_type": ph_type.most_common(), "carriers": ph_carrier.most_common(10),
                            "missing_mods": ph_cre.most_common(12),
                            "examples": [[s, M[s].name, M[s].type_name] for s in list(phantom)[:10]]}
    out["catalog_vs_reach"] = {"catalog_items": len(cat_sids), "catalog_unreachable_in_graph": sum(1 for s in cat_sids if s in M and s not in R),
                               "catalog_unreach_examples": [[s, M[s].name] for s in cat_sids if s in M and s not in R][:10],
                               "mod_armour_weapon_unreachable_not_in_catalog": sum(1 for s, it in M.items() if own(it) and it.type_name in ("ARMOUR", "WEAPON", "CROSSBOW") and s not in R and s not in cat_sids)}
    # исключения-подозрения: недостижимые, но на них кто-то ссылается условием (диалог/фракция) -> не резать вслепую
    # 1b. фракции без членов и городов; расы без использования
    fac_mem = collections.Counter()
    for it in M.values():
        if it.sid in rej:
            continue
        if it.type_name in ("SQUAD_TEMPLATE", "TOWN", "CHARACTER", "ANIMAL_CHARACTER", "NEW_GAME_STARTOFF"):
            for r in it.refs.get("faction", []):
                fac_mem[r.target] += 1
        if it.type_name == "FACTION":
            for cat in ("squads", "residents", "bar squads"):
                for r in it.refs.get(cat, []):
                    fac_mem[it.sid] += 1
    empty_fac = [[f.sid, f.name] for f in M.values() if f.type_name == "FACTION" and own(f) and fac_mem[f.sid] == 0]
    out["empty_factions"] = {"count": len(empty_fac), "by_mod": collections.Counter(creator(s) for s, _ in empty_fac).most_common(12), "examples": empty_fac[:25]}
    race_use = collections.Counter()
    for it in M.values():
        if it.sid in rej:
            continue
        for cat, rs in it.refs.items():
            if it.type_name in ("CHARACTER", "ANIMAL_CHARACTER") and cat == "race":
                for r in rs:
                    race_use[r.target] += 1
            if it.type_name == "FACTION" and cat == "races":
                for r in rs:
                    race_use[r.target] += 1
            if it.type_name == "RACE_GROUP":
                for r in rs:
                    race_use[r.target] += 1
            if it.type_name == "NEW_GAME_STARTOFF" and cat == "force race":
                for r in rs:
                    race_use[r.target] += 1
    races = [r for r in M.values() if r.type_name == "RACE" and own(r)]
    race_dead = [[r.sid, r.name] for r in races if race_use[r.sid] == 0]
    race_dead_unreach = [x for x in race_dead if x[0] not in R]
    out["races"] = {"mod_created": len(races), "unused_by_characters_factions_groups": len(race_dead),
                    "unused_and_unreachable": len(race_dead_unreach),
                    "by_mod": collections.Counter(creator(s) for s, _ in race_dead_unreach).most_common(15), "examples": race_dead_unreach[:25]}
    try:
        ra = json.load(open(ROOT + r"\data\race_audit.json", encoding="utf-8"))
        out["races"]["race_audit_ref"] = {"rows": len(ra["rows"]), "dupe_groups": len(ra["dupes"])}
    except Exception:
        pass
    # 2. отладка/заглушки по именам
    junk = collections.defaultdict(list)
    for s, it in M.items():
        if not own(it) or it.type_name not in KEY_TYPES:
            continue
        nm = it.name or ""
        if nm and JUNK_RX.search(nm):
            junk[it.type_name].append([s, nm, s in R])
    out["junk_names"] = {t: {"count": len(v), "reachable": sum(x[2] for x in v), "by_mod": collections.Counter(creator(x[0]) for x in v).most_common(8),
                             "examples": v[:15]} for t, v in junk.items()}
    # 3. битые ссылки по модам (цель отсутствует в цепочке)
    broken = collections.Counter()
    broken_cat = collections.Counter()
    broken_ex = {}
    rejected_refs = collections.Counter()
    for s, it in M.items():
        if s in rej:
            continue
        c = creator(s)
        for cat, rs in it.refs.items():
            for r in rs:
                t = r.target
                if not t or t in ("", "0"):
                    continue
                if t not in M:
                    broken[c] += 1
                    broken_cat[(it.type_name, cat)] += 1
                    broken_ex.setdefault(c, [s, it.name, cat, t])
                elif t in rej:
                    rejected_refs[c] += 1
    out["broken_refs"] = {"total": sum(broken.values()), "by_mod": broken.most_common(20),
                          "by_type_cat": [[f"{a}.{b}", n] for (a, b), n in broken_cat.most_common(15)],
                          "examples": {k: broken_ex[k] for k, _ in broken.most_common(10)},
                          "to_game_rejected_total": sum(rejected_refs.values()), "to_game_rejected_by_mod": rejected_refs.most_common(10)}
    out["game_rejected"] = {"sids": len(rej), "by_mod": collections.Counter(creator(s) for s in rej).most_common(12)}
    # 4. near-дубли: фракции с одним именем; предметы с одним мешем/текстурой, разные имена, разные моды, не клоны dedup
    byname = collections.defaultdict(list)
    for f in M.values():
        if f.type_name == "FACTION" and f.sid not in rej and f.name:
            byname[f.name.strip().lower()].append(f)
    fdup = []
    for n, fs in byname.items():
        if len(fs) > 1:
            fdup.append({"name": fs[0].name, "n": len(fs), "recs": [[f.sid, creator(f.sid), fac_mem[f.sid]] for f in fs]})
    fdup.sort(key=lambda x: -x["n"])
    out["faction_same_name"] = {"groups": len(fdup), "extra": sum(x["n"] - 1 for x in fdup), "top": fdup[:20]}
    canon = {}
    try:
        dc = json.load(open(ROOT + r"\rules\dedup_canonical.json", encoding="utf-8"))
        canon = {"clone_groups": len(dc["clone_groups"]), "families": len(dc["families"])}
    except Exception:
        pass
    sig = collections.defaultdict(list)
    for it in M.values():
        if it.type_name in ("ARMOUR", "WEAPON", "CROSSBOW") and own(it) and it.sid not in rej:
            files = tuple(sorted(v.strip().lower() for k, v in it.values.items() if isinstance(v, str) and v.strip()
                                 and v.strip().lower().endswith((".mesh", ".dds", ".png", ".tga")) and "icon" not in k))
            if files:
                sig[(it.type_name, files)].append(it)
    near = []
    for (t, files), its in sig.items():
        names = {i.name.strip().lower() for i in its}
        mods = {creator(i.sid) for i in its}
        if len(its) > 1 and len(names) > 1 and len(mods) > 1:
            near.append({"type": t, "n": len(its), "mods": sorted(mods)[:5], "names": sorted({i.name for i in its})[:4],
                         "unreachable": sum(i.sid not in R for i in its)})
    near.sort(key=lambda x: -x["n"])
    out["near_dup_cross_mod_same_mesh"] = {"groups": len(near), "extra_records": sum(x["n"] - 1 for x in near), "dedup_canonical": canon, "top": near[:20]}
    # 5. мёртвый груз
    dead = []
    for c, st in mod_stats.items():
        if c in CORE or c.startswith("KMM_") or st["key_created"] < 1:
            continue
        frac = st["key_reached"] / st["key_created"]
        dead.append({"mod": c, "created": st["created"], "key_created": st["key_created"], "key_reached": st["key_reached"],
                     "reach_frac": round(frac, 3), "unreach_types": dict(st["types"].most_common(5))})
    d0 = sorted([d for d in dead if d["key_reached"] == 0], key=lambda d: -d["key_created"])
    d1 = sorted([d for d in dead if 0 < d["reach_frac"] < 0.3 and d["key_created"] >= 10], key=lambda d: d["reach_frac"])
    out["dead_weight_mods"] = {"zero_reachable_key": d0, "mostly_unreachable": d1[:40]}
    # моды вообще без созданных записей (только правки): отсылка к dedup_report
    out["total_unreachable_key"] = sum(u["unreachable"] for u in unreach.values())
    json.dump(out, open(ROOT + r"\data\junk_audit.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    write_md(out)
    print("unreachable:", {t: (u["unreachable"], u["total_mod_created"]) for t, u in unreach.items()})
    print("zero-reachable mods:", len(d0), "mostly unreachable:", len(d1), "broken refs:", out["broken_refs"]["total"])


def write_md(o):
    L = ["# JUNK_AUDIT — мусор от модов (генерируется tools\\junk_audit.py, только чтение)", "",
         "Метод и ограничения: см. докстринг скрипта. «Недостижима» = не найдена в графе порождения из ванили/корневых типов мира; "
         "нативные вызовы движка по имени не видны, поэтому перед резкой чисткой смотреть строку «Решение». Сейвы не сохраняем (новая игра).", "",
         f"Записей в цепочке: {o['counts']['records']}, достижимых: {o['counts']['reachable']}, игра отвергает (rejected): {o['counts']['rejected_in_chain']}.", "",
         "## 1. Недостижимые записи (создано модом, ни от чего не порождается)", "",
         "| Тип | создано модами | недостижимо | топ модов-источников |", "|---|---|---|---|"]
    for t, u in sorted(o["unreachable"].items(), key=lambda x: -x[1]["unreachable"]):
        L.append(f"| {t} | {u['total_mod_created']} | {u['unreachable']} | " + ", ".join(f"{m} {n}" for m, n in u["by_mod"][:5]) + " |")
    ph = o["phantom_stubs"]
    L += ["", f"Заглушки отсутствующих модов (compat-патчи; создатель не в сборке): {ph['total']} записей " + str(ph['by_type'][:4]) +
          "; носители: " + ", ".join(f"{m} {n}" for m, n in ph["carriers"][:5]) + ". В таблице выше они НЕ учтены.",
          f"Каталог гардероба: {o['catalog_vs_reach']['catalog_items']}, из них недостижимо в графе: {o['catalog_vs_reach']['catalog_unreachable_in_graph']} (если >0 — пулы не доходят до игры); "
          f"модовых брони/оружия вне каталога и недостижимых: {o['catalog_vs_reach']['mod_armour_weapon_unreachable_not_in_catalog']}.",
          "", f"Фракции без членов/городов/отрядов: {o['empty_factions']['count']} (топ: " + ", ".join(f"{m} {n}" for m, n in o["empty_factions"]["by_mod"][:6]) + ").",
          f"Модовые расы: {o['races']['mod_created']}, без персонажей/фракций/групп: {o['races']['unused_by_characters_factions_groups']}, из них недостижимых: {o['races']['unused_and_unreachable']} "
          f"(топ: " + ", ".join(f"{m} {n}" for m, n in o["races"]["by_mod"][:6]) + ").", "",
          "## 2. Отладка/заглушки по имени", "", "| Тип | записей | достижимых | моды |", "|---|---|---|---|"]
    for t, j in sorted(o["junk_names"].items(), key=lambda x: -x[1]["count"]):
        L.append(f"| {t} | {j['count']} | {j['reachable']} | " + ", ".join(f"{m} {n}" for m, n in j["by_mod"][:4]) + " |")
    L += ["", "Примеры (достижимые — самые заметные игроку):"]
    for t, j in o["junk_names"].items():
        ex = [e for e in j["examples"] if e[2]][:5]
        for e in ex:
            L.append(f"- {t}: {e[1]} ({e[0]})")
    b = o["broken_refs"]
    L += ["", "## 3. Битые ссылки и отвергнутые игрой записи", "", f"Ссылок на несуществующую запись: {b['total']}; на rejected: {b['to_game_rejected_total']}; rejected-sid всего: {o['game_rejected']['sids']}.",
          "Топ модов по битым: " + ", ".join(f"{m} {n}" for m, n in b["by_mod"][:10]), "По типам: " + ", ".join(f"{k} {n}" for k, n in b["by_type_cat"][:8]), "",
          "## 4. Near-дубли", "", f"Фракции с одинаковым именем: {o['faction_same_name']['groups']} групп (лишних {o['faction_same_name']['extra']}). Топ: " +
          ", ".join(f"{x['name']} x{x['n']}" for x in o["faction_same_name"]["top"][:10]),
          f"Предметы с одним мешем/текстурой, разными именами и разными модами: {o['near_dup_cross_mod_same_mesh']['groups']} групп, лишних {o['near_dup_cross_mod_same_mesh']['extra_records']} "
          f"(точные клоны внутри мода — в docs\\DEDUP.md). Топ: " + "; ".join(f"{x['names'][0]} x{x['n']}" for x in o["near_dup_cross_mod_same_mesh"]["top"][:8]) + ".", "",
          "## 5. Мёртвый груз: моды без единой достижимой ключевой записи", "", "| Мод | создано | ключевых | недостижимые типы |", "|---|---|---|---|"]
    for d in o["dead_weight_mods"]["zero_reachable_key"][:40]:
        L.append(f"| {d['mod']} | {d['created']} | {d['key_created']} | {d['unreach_types']} |")
    L += ["", "Почти целиком недостижимые (<30%, от 10 ключевых):", "", "| Мод | ключевых | достижимо | доля |", "|---|---|---|---|"]
    for d in o["dead_weight_mods"]["mostly_unreachable"][:25]:
        L.append(f"| {d['mod']} | {d['key_created']} | {d['key_reached']} | {d['reach_frac']} |")
    u = o["unreachable"]
    g = lambda t: u.get(t, {}).get("unreachable", 0)  # noqa: E731
    jn = o["junk_names"]
    L += ["", "## 6. Предложения (по заметности игроку)", "",
          "Механизмы: CUT = rules\excluded_mods.json (mods целиком / items поштучно), удаление sid в KMM_Cleanup/KMM_Fix, rejected-sid; "
          "REIMPL = поток wardrobe/economy (пулы, vendor lists, loot), KMM_Town; KEEP = оставить.", "",
          "| # | Действие | Объём | Механизм | Решение |", "|---|---|---|---|---|",
          f"| 1 | Достижимые отладочные записи (copy/test/debug/DISCARD/wip): CHARACTER {jn.get('CHARACTER', {}).get('reachable', 0)}, SQUAD_TEMPLATE {jn.get('SQUAD_TEMPLATE', {}).get('reachable', 0)}, ITEM {jn.get('ITEM', {}).get('reachable', 0)}, RESEARCH {jn.get('RESEARCH', {}).get('reachable', 0)} (\"sacred trash test research\", \"#MAGICAL CUBE TESTER\", \"skeleton debug\") | см. раздел 2 | удалить sid в KMM_Fix / items-исключения | CUT |",
          f"| 2 | Недостижимые диалоги: DIALOGUE {g('DIALOGUE')}, DIALOGUE_PACKAGE {g('DIALOGUE_PACKAGE')} (Weird recruit, Strangers and Freaks, Band of Exiles, Talkative Kenshi) | см. раздел 1 | отключить моды-доноры целиком, где достижимо <30% (раздел 5) | CUT мод / REIMPL привязкой к фракции |",
          f"| 3 | Недостижимые CHARACTER/SQUAD_TEMPLATE мод-создателей (кроме KMM_*): CHARACTER {g('CHARACTER')}, SQUAD {g('SQUAD_TEMPLATE')} | раздел 1 | вшить в бары/отряды фракций через KMM_Town (REIMPL), иначе вырезать; KMM_Traces — спавн из Lua, не трогать | REIMPL / KEEP |",
          f"| 4 | Модовые расы без носителей ({o['races']['unused_and_unreachable']}), особенно Wolf_Headgear (перекраски собак/раптоналов) | раздел 1 | исключить мод или слить с ванильной основой (race_audit.py) | CUT |",
          f"| 5 | Фракции без членов/городов: {o['empty_factions']['count']} (TEXT TEXTURE, ChildrenOfKenshi, MotokoTheHuntress, Rusty Raiders) | раздел 1 | исключить мод либо отдать фракции отряды | CUT |",
          f"| 6 | Заглушки отсутствующих модов: {ph['total']} записей, из них достижимых {ph['reachable']} (носители ACP, Kaizo, Social Lives, Talkative Kenshi) | раздел 1 | обновить rules\game_rejected_sids.json по свежему логу; проверить, нужны ли патчи-носители | CUT / проверка |",
          f"| 7 | Недостижимые BUILDING {g('BUILDING')} (Newwworld 43, CBT Faction Furniture, Forgotten Buildings) | раздел 1 | KEEP ядро Newwworld; CBT/Forgotten — исключить записи | CUT частично |",
          f"| 8 | Недостижимые ITEM {g('ITEM')} (Faction Caravans 17, shoppingecon 9) и ARMOUR {g('ARMOUR')}: Vanguad_mercenares, bull armor | раздел 1 | положить в vendor/wardrobe пулы культуры (Vanguad - наёмники Tech Hunters/United Cities; bull armor - Shek) либо исключить | REIMPL |",
          f"| 9 | Near-дубли брони между модами с тем же мешем: {o['near_dup_cross_mod_same_mesh']['groups']} групп, лишних {o['near_dup_cross_mod_same_mesh']['extra_records']} (Bandana Small x26) | раздел 4 | rules\dedup_canonical.json | CUT дубль |",
          f"| 10 | Фракции-двойники по имени ({o['faction_same_name']['groups']}): Holy Nation (cook_set), Second Empire/Drifters/Holy Nation Outlaws (Band of Exiles), Old Machines (HTDEnforcers) | раздел 4 | слить в ванильную через glue/редирект ссылок, либо переименовать | CUT |",
          "| 11 | Битые ссылки (11 штук, в диалогах MysteriousWanderer, Rusty Raiders, Dialogue (10)) | раздел 3 | почистить условия или отключить мод | CUT |",
          "| 12 | Мёртвый груз (0-1 достижимых ключевых записей): CATO V4, TK Clean Fix, RadiantHiveBirthing, DarkHiveBirthing, Dread Limbs, Goat is strong animal | раздел 5 | excluded_mods.json -> mods (проверить, что нет модов-зависимых) | CUT |",
          "| 13 | KMM_Traces: ~1150 CHARACTER/SQUAD недостижимы в графе: спавнятся из Lua по имени — не баг, но не видны статическому аудиту; проверить, что имена в Lua совпадают | раздел 1 | KEEP | KEEP |",
          "| 14 | Тренировочные манекены (Training Dummy, Drill Dummy) — легитимные постройки | раздел 2 | KEEP | KEEP |",
          "| 15 | Книги/записки на общем меше (ITEM ~450 в 2 группах) — безвредны | DEDUP.md | KEEP | KEEP |", ""]
    open(ROOT + r"\docs\JUNK_AUDIT.md", "w", encoding="utf-8").write("\n".join(L))


if __name__ == "__main__":
    main()
