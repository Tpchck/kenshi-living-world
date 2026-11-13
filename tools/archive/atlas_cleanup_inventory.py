"""Инвентаризация «осознанной чистки карты» (ТОЛЬКО ЧТЕНИЕ: ничего не пишет, кроме data/atlas_cleanup.json).
По каждой TOWN итогового мира (ваниль + моды по mods.cfg): тип, владелец, координаты, отряды, уники и признак рекрута,
питомцы, торговцы, размер (здания в zone-файлах вокруг), расстояния до города и базы фракции, входящие ссылки,
класс KEEP / MERGE (+хост) / DROP / REVIEW с обоснованием.
python -I -X utf8 tools/atlas_cleanup_inventory.py [--pkl кэш.pkl] [--no-zones]
  --pkl: взять (M, origin, rejected) из pickle (быстро; формат как у ctx-кэша), иначе kmm_build.Ctx() (минуты).
  --no-zones: не читать зоны (размер = None).
Признак рекрута: уник (CHARACTER.unique) с пакетом диалога (dialogue package / dialog leader / dialog squad / dialogue),
в дереве реплик которого есть DIALOGUE с именем recruit|join|hire или реплика NPC с действием 3 либо 18
(18 = вступление в отряд игрока: 'Let's go', 'guess I'll join up'; 3 — 'Let me join you'; нумерация выведена эмпирически)."""
import collections
import json
import math
import os
import pickle
import re
import sys

ROOT = r"C:\KenshiModMap"
for _p in ("", "build", "fast"):
    _d = os.path.join(ROOT, "tools", _p)
    if _d not in sys.path:
        sys.path.insert(0, _d)
import kmod  # noqa: E402

OUT = os.path.join(ROOT, "data", "atlas_cleanup.json")
POP = ("residents", "roaming squads", "bar squads")
JOIN_ACTIONS = {18}          # сильный признак: «Let's go», «guess I'll join up»
JOIN_WEAK = {3}              # слабый: «Let me join you» (часто после спасения/поединка)
REC_NAME = re.compile(r"recruit|join", re.I)
HQ_NAME = re.compile(r"\bHQ\b|headquarter|\bbase\b|fortress|castle|citadel|\bkeep\b|stronghold|capital|monaster|temple|academy|palace|\bfort\b|bastion|\bhold\b|barracks", re.I)
MARKER = re.compile(r"marker|housecamp|^[-_]|\(DEFAULT\)|nest trashed|\bdummy\b|\btest\b", re.I)
PLAYER = re.compile(r"player|\bmy base\b|outpost \(player", re.I)
VANILLA = ("gamedata.base", "Newwworld.mod", "Dialogue.mod", "rebirth.mod", "Newwworld Plus.mod")
CITY_T = {2, 5}            # города (type 2, 5: порты/рабовладельческие), настоящие города
BASE_T = {6, 7}            # крепости/хранилища
TYPE_GUESS = {0: "лагерь/гнездо/логово", 1: "аванпост", 2: "город", 3: "деревня", 4: "руины", 5: "город-порт/крупный", 6: "крепость", 7: "хранилище",
              8: "маркер", 9: "укрытие/башня/малая база", 10: "housecamp (служебный)"}
FURN = re.compile(r"bed|table|chair|bench|lamp|light|torch|crate|barrel|shelf|rack|sign|banner|flag|stool|\bbox|cabinet|chest|cage|decor|rug|plant|tree|rock|"
                  r"bush|grass|fire|statue|sack|bucket|stove|anvil|forge|desk|counter|sofa|pillow|carpet|lantern|candle|skull|bones|corpse|cart|wagon|hay|pile|"
                  r"junk|rubble|debris|fountain|well\b|pole|chain|rope|pipe|wall|fence|gate|barrier|rampart|railing|stair|pillar|column|arch|bridge|ramp|farm|plot|field", re.I)
R_NEAR = 2500.0            # радиус подсчёта зданий вокруг центра города (ед. мира; дом ~500 ед.)
R_WIDE = 5000.0
FAR_HOST = 150000.0


def vanilla_sid(sid):
    return sid.rsplit("-", 1)[-1] in VANILLA if "-" in sid else True


def src_mod(sid):
    """Мод-автор записи по суффиксу sid (origin в Ctx — первый слой, где запись встречена; для слитых копий это Kaizo)."""
    return sid.split("-", 1)[1] if "-" in sid else "gamedata.base"


def load_world(pkl):
    if pkl:
        M, origin, rej = pickle.load(open(pkl, "rb"))
        return M, origin, rej
    import kmm_build as kb
    ctx = kb.Ctx()
    return ctx.M, ctx.origin, ctx.rejected


def scan_levels_and_zones(M, want_zones):
    """([слой]) → позиции TOWN из GAMESTATE_TOWN_INSTANCE_LIST и здания зон (итог по id инстанса, поздний слой побеждает)."""
    import glob
    import zone_fix
    import mods_cfg
    game = r"C:\Program Files (x86)\Steam\steamapps\common\Kenshi\data\newland"
    levels = [os.path.join(game, "leveldata.level")] + sorted(glob.glob(os.path.join(game, "leveldata", "*", "leveldata.level")))
    levels += [os.path.join(os.path.dirname(p), "leveldata", "leveldata.level") for n, p in mods_cfg.mod_paths().items()]
    pos, zones, nz = {}, {}, 0
    for lf in levels:     # порядок слоёв: ваниль → моды; поздний слой перезаписывает позицию
        if os.path.isfile(lf):
            try:
                for it in kmod.read(lf).items:
                    if it.type_name == "GAMESTATE_TOWN_INSTANCE_LIST":
                        for ins in it.instances:
                            if ins.target:
                                pos[ins.target] = (ins.pos[0], ins.pos[2])
            except Exception:
                pass
    if want_zones:
        for name, zs in zone_fix.layers():
            for z, f in zs.items():
                try:
                    m = kmod.read(f)
                except Exception:
                    continue
                zd = zones.setdefault(z, {})
                for it in m.items:
                    if it.type_name == "INSTANCE_COLLECTION":
                        for ins in it.instances:
                            zd[ins.id] = (ins.target, ins.pos[0], ins.pos[2]) if ins.target else None
                nz += 1
    blds = []
    for zd in zones.values():
        for v in zd.values():
            if v is None:
                continue
            t = M.get(v[0])
            if t is not None and t.type_name == "BUILDING":
                blds.append((v[1], v[2], bool(FURN.search(t.name or ""))))
    return pos, blds, nz


class Recruit:
    """Признак «уник рекрутируется» по диалогам."""

    def __init__(self, M):
        self.M = M
        self.pk = {}

    def _walk(self, sid, depth, seen, budget):
        """Реплики/диалоги → (имя_совпало, действие_найдено)."""
        M = self.M
        found = [False, False]   # [имя диалога, действие 18], далее возможная метка "weak" (действие 3)
        stack = [(sid, 0)]
        while stack and budget[0] > 0:
            s, d = stack.pop()
            if s in seen:
                continue
            seen.add(s)
            budget[0] -= 1
            it = M.get(s)
            if it is None:
                continue
            if it.type_name == "DIALOGUE" and REC_NAME.search(it.name or ""):
                found[0] = True
            for r in it.refs.get("effects", []) if it.type_name == "DIALOGUE_LINE" else []:
                a = M.get(r.target)
                if a is not None and it.values.get("speaker") == 0:
                    if a.values.get("action name") in JOIN_ACTIONS:
                        found[1] = True
                    elif a.values.get("action name") in JOIN_WEAK:
                        found.append("weak")
            if d < 14:
                for cat in ("dialogs", "lines"):     # inheritsFrom не идём: общие деревья («Npc TOUGH Merc») дают вступление после поединка у любого
                    for r in it.refs.get(cat, []):
                        stack.append((r.target, d + 1))
        return found

    def package(self, sid):
        if sid not in self.pk:
            self.pk[sid] = self._walk(sid, 0, set(), [1500])
        return self.pk[sid]

    def char(self, ch, extra=()):
        """(рекрут?, как) по CHARACTER + доп. диалоги отряда."""
        how = []
        pk = list(ch.refs.get("dialogue package", [])) + list(ch.refs.get("dialogue", []))
        for r in pk:
            pk_ = self.package(r.target)
            nm, ac = pk_[0], pk_[1]
            if nm:
                how.append("диалог-имя")
            if ac:
                how.append("действие вступления (18)")
            if not (nm or ac) and "weak" in pk_:
                how.append("слабый признак: действие 3")
        for sid in extra:
            nm, ac = self.package(sid)[:2]
            if nm:
                how.append("диалог отряда-имя")
            if ac:
                how.append("диалог отряда: вступление")
        return bool(how), sorted(set(how))


def main():
    pkl = sys.argv[sys.argv.index("--pkl") + 1] if "--pkl" in sys.argv else None
    want_zones = "--no-zones" not in sys.argv
    M, origin, rej = load_world(pkl)
    towns_all = [t for t in M.values() if t.type_name == "TOWN" and t.sid not in rej]
    variant = {r.target for t in towns_all for r in t.refs.get("override town", [])}
    base_of = collections.defaultdict(list)          # база → её варианты (override)
    # у базы в refs перечислены её override-варианты (см. Black Dog HQ); вариант ссылается на соседние варианты
    for t in towns_all:
        if t.sid not in variant:
            for r in t.refs.get("override town", []):
                base_of[t.sid].append(r.target)

    pos, blds, nz = scan_levels_and_zones(M, want_zones)

    # обратный индекс ссылок
    TS = {t.sid for t in towns_all}
    rev = collections.defaultdict(list)
    for it in M.values():
        for cat, rs in it.refs.items():
            for r in rs:
                if r.target in TS and it.sid != r.target:
                    rev[r.target].append((it.type_name, cat, it.sid))
    nest_of = collections.defaultdict(list)       # TOWN → [(группа биома, вес)] : процедурные «гнёзда/лагеря» (крестики на карте)
    for it in M.values():
        if it.type_name in ("BIOME_GROUP", "BIOMES"):
            for r in it.refs.get("nests", []):
                if r.target in TS:
                    nest_of[r.target].append((it.name, r.v0))
    texts = {}
    for sub in ("rules", "data"):
        for dp, _, fs in os.walk(os.path.join(ROOT, sub)):
            if "_bak" in dp or "backup" in dp:
                continue
            for f in fs:
                if f.endswith(".json") and f not in ("atlas_cleanup.json",) and os.path.getsize(os.path.join(dp, f)) < 6_000_000:
                    try:
                        texts[os.path.relpath(os.path.join(dp, f), ROOT)] = open(os.path.join(dp, f), encoding="utf-8", errors="replace").read()
                    except OSError:
                        pass
    try:
        cond = json.load(open(os.path.join(ROOT, "build", "KMM_Conductor", "conductor.json"), encoding="utf-8"))
    except Exception:
        cond = {"town_info": {}, "sites": []}
    ti, sites = cond.get("town_info", {}), {s["sid"]: s for s in cond.get("sites", [])}

    rc = Recruit(M)
    fac_real = lambda f: f is not None and not M[f.target].values.get("not real") if f is not None and f.target in M else False  # noqa: E731
    fname = lambda sid: (M[sid].name if sid in M else sid)  # noqa: E731

    def town_fac(t):
        fr = t.refs.get("faction")
        return fr[0].target if fr and fr[0].target in M else None

    def real_fac(sid):
        return sid is not None and sid in M and not M[sid].values.get("not real")

    # --- кандидаты и пулы хостов
    def alive(t):
        return not t.values.get("REMOVED") and t.sid not in variant and t.sid in pos

    pool = []
    for t in towns_all:
        if not alive(t):
            continue
        ty = t.values.get("type")
        f = town_fac(t)
        if not real_fac(f):
            continue
        if ty in CITY_T or ty in BASE_T or (ty in (1, 3, 9) and HQ_NAME.search(t.name or "")) or (ty == 2):
            if sum(len(t.refs.get(k, [])) for k in POP) >= 1 and not MARKER.search(t.name or ""):
                pool.append(t)
    pool_by_fac = collections.defaultdict(list)
    for t in pool:
        pool_by_fac[town_fac(t)].append(t)

    def dist(a, b):
        return math.hypot(pos[a][0] - pos[b][0], pos[a][1] - pos[b][1])

    def nearest(sid, cands, k=1, excl=()):
        c = sorted(((dist(sid, x.sid), x) for x in cands if x.sid != sid and x.sid not in excl), key=lambda p: p[0])
        return c[:k]

    def count_blds(sid):
        x0, z0 = pos[sid]
        a = b = fa = 0
        for x, z, furn in blds:
            dx = x - x0
            if dx > R_WIDE or dx < -R_WIDE:
                continue
            d = math.hypot(dx, z - z0)
            if d <= R_WIDE:
                b += 1
                if not furn:
                    fa += 1
                if d <= R_NEAR:
                    a += 1
        return a, b, fa

    def squad_info(q, chance):
        info = {"sid": q.sid, "name": q.name, "chance": chance, "mod": src_mod(q.sid), "uniques": [], "pets": [], "vendors": [], "members": 0,
                "faction": fname(q.refs["faction"][0].target) if q.refs.get("faction") else None,
                "faction_sid": q.refs["faction"][0].target if q.refs.get("faction") else None,
                "trader": bool(q.values.get("is trader"))}
        dlg = [r.target for r in q.refs.get("dialog leader", []) + q.refs.get("dialog squad", [])]
        for cat in ("leader", "squad", "squad2"):
            for r in q.refs.get(cat, []):
                ch = M.get(r.target)
                if ch is None or ch.type_name != "CHARACTER":
                    continue
                info["members"] += max(1, r.v0) if isinstance(r.v0, int) and 0 < r.v0 < 50 else 1
                if ch.values.get("unique"):
                    ok, how = rc.char(ch, ())
                    info["uniques"].append({"sid": ch.sid, "name": ch.name, "recruit": ok, "strong": any(not h.startswith("слабый") for h in how), "how": how, "mod": src_mod(ch.sid)})
                if ch.values.get("is trader"):
                    info["trader"] = True
        for cat in ("animals", "animals2"):
            for r in q.refs.get(cat, []):
                a = M.get(r.target)
                if a is not None:
                    pdlg = [x.target for x in q.refs.get("dialog animal", [])]
                    ok, how = rc.char(a, pdlg)
                    info["pets"].append({"sid": a.sid, "name": a.name, "recruit": ok, "how": how, "has_dialog_animal": bool(pdlg)})
        for r in q.refs.get("vendors", []):
            v = M.get(r.target)
            if v is not None:
                info["vendors"].append(v.name)
        return info

    records, skipped = [], collections.Counter()
    for t in towns_all:
        if t.values.get("REMOVED"):
            skipped["REMOVED"] += 1
            continue
        if t.sid in variant:
            skipped["override-вариант (учтён в базе)"] += 1
            continue
        nm = t.name or ""
        if MARKER.search(nm) or t.values.get("type") in (8, 10):
            skipped["служебный маркер"] += 1
            continue
        if PLAYER.search(nm):
            skipped["город игрока"] += 1
            continue
        if t.sid not in pos and t.sid not in nest_of:
            skipped["не размещён и не в списках nests биомов (в мире не появляется)"] += 1
            continue
        records.append(t)

    out = []
    for t in records:
        nm = t.name or ""
        ty = t.values.get("type")
        fsid = town_fac(t)
        sq = []
        for cat in POP:
            for r in t.refs.get(cat, []):
                q = M.get(r.target)
                if q is not None and q.type_name == "SQUAD_TEMPLATE":
                    si = squad_info(q, r.v1 if isinstance(r.v1, int) else None)
                    si["kind"] = cat
                    sq.append(si)
        for vs in base_of.get(t.sid, []):          # отряды вариантов (override) — как «возможные»
            v = M.get(vs)
            if v is None:
                continue
            have = {s["sid"] for s in sq}
            for cat in POP:
                for r in v.refs.get(cat, []):
                    q = M.get(r.target)
                    if q is not None and q.type_name == "SQUAD_TEMPLATE" and q.sid not in have:
                        si = squad_info(q, r.v1 if isinstance(r.v1, int) else None)
                        si["kind"] = cat + " (из override)"
                        sq.append(si)
                        have.add(q.sid)
        uniques = [u for s in sq for u in s["uniques"]]
        pets = [p for s in sq for p in s["pets"]]
        vendors = sorted({v for s in sq for v in s["vendors"]})
        traders = [s for s in sq if s["trader"] or s["vendors"]]
        n_loot = len(t.refs.get("loot spawn", []))
        b_near, b_wide, b_solid = (count_blds(t.sid) if (want_zones and t.sid in pos) else (None, None, None))
        # расстояния
        cands = [x for x in pool if x.values.get("type") in CITY_T and x.sid != t.sid]
        nc = nearest(t.sid, cands, 1) if t.sid in pos else []
        d_city = {"sid": nc[0][1].sid, "name": nc[0][1].name, "dist": round(nc[0][0])} if nc else None
        fac_base = None
        if real_fac(fsid) and t.sid in pos:
            nb = nearest(t.sid, pool_by_fac.get(fsid, []), 1)
            if nb:
                fac_base = {"sid": nb[0][1].sid, "name": nb[0][1].name, "dist": round(nb[0][0])}
        inc = rev.get(t.sid, [])
        inc_vars = set(base_of.get(t.sid, []))
        for vs in inc_vars:
            inc = inc + rev.get(vs, [])
        inc_ext = [x for x in inc if x[0] not in ("TOWN", "BIOME_GROUP", "BIOMES")]
        inc_cnt = collections.Counter(f"{a}.{b}" for a, b, _ in inc_ext)
        in_rules = sorted(k for k, v in texts.items() if t.sid in v)
        site = sites.get(t.sid)
        tinfo = ti.get(t.sid)
        rec = {
            "sid": t.sid, "name": nm, "mod": src_mod(t.sid), "vanilla": vanilla_sid(t.sid),
            "type": ty, "type_guess": TYPE_GUESS.get(ty, "?"), "public": bool(t.values.get("is public")),
            "owner": fname(fsid) if fsid else None, "owner_sid": fsid, "owner_real": real_fac(fsid),
            "x": round(pos[t.sid][0]) if t.sid in pos else None, "z": round(pos[t.sid][1]) if t.sid in pos else None,
            "placement": "fixed (leveldata)" if t.sid in pos else "procedural nest (BIOME_GROUP nests)",
            "nest_groups": sorted(nest_of.get(t.sid, []), key=lambda p: -p[1])[:8], "nest_weight_total": sum(w for _, w in nest_of.get(t.sid, [])),
            "overrides": len(base_of.get(t.sid, [])),
            "squads": [{k: s[k] for k in ("sid", "name", "kind", "chance", "faction", "members", "trader")} for s in sq],
            "n_squads": len(sq), "members_est": sum(s["members"] for s in sq),
            "uniques": uniques, "pets": pets, "vendors": vendors, "n_trader_squads": len(traders), "loot_spawn": n_loot,
            "buildings_2500": b_near, "buildings_5000": b_wide, "buildings_solid_5000": b_solid,
            "nearest_city": d_city, "nearest_faction_base": fac_base,
            "incoming": dict(inc_cnt), "incoming_n": len(inc_ext),
            "in_rules_files": in_rules[:6], "conductor_site": site["kind"] if site else None, "conductor_holding": tinfo["kind"] if tinfo else None,
        }
        out.append(rec)

    # --- классификация
    def has_story_link(r):
        bad = {"FACTION_CAMPAIGN", "NEW_GAME_STARTOFF", "QUEST", "WORLD_STATE", "DIALOG_ACTION", "DIALOGUE", "DIALOGUE_LINE", "AI_TASK", "SQUAD_TEMPLATE"}
        return [k for k in r["incoming"] if k.split(".")[0] in bad or "story" in k.lower()]

    def hq_rank(x):
        return (bool(HQ_NAME.search(x.name or "")) + (x.values.get("type") in BASE_T), sum(len(x.refs.get(k, [])) for k in POP))

    def pick_host(r, need_neutral=False):
        """Хост: та же фракция (лор) — ближайший город/база; для процедурных гнёзд без координат — главный (HQ/самый населённый) город фракции.
        Иначе ближайший публичный город (нейтральность/близость)."""
        sid = r["sid"]
        fixed = sid in pos
        fs = {s["faction_sid"] for s in sq_of[sid] if s["faction_sid"] and real_fac(s["faction_sid"])} | ({r["owner_sid"]} if r["owner_real"] else set())
        best = None
        for f in fs:
            pl = pool_by_fac.get(f, [])
            if not pl:
                continue
            if fixed:
                c = nearest(sid, pl, 1)
                cand = (c[0][0], c[0][1]) if c else None
            else:
                h = max(pl, key=hq_rank)
                cand = (None, h)
            if cand and (best is None or (cand[0] is not None and (best[0] is None or cand[0] < best[0]))):
                best = (cand[0], cand[1], "лор: фракция отряда/владельца (%s)" % fname(f))
        if best and (best[0] is None or best[0] <= FAR_HOST) and not need_neutral:
            return best
        pubc = [x for x in pool if x.values.get("type") in CITY_T and x.values.get("is public")]
        if fixed:
            c = nearest(sid, pubc, 1)
            if c:
                if best and best[0] <= c[0][0] * 2.5 and not need_neutral:
                    return best
                return (c[0][0], c[0][1], "нейтральность/близость: ближайший публичный город")
        elif pubc:
            return (None, max(pubc, key=hq_rank), "нейтральность: крупный публичный город (у гнезда нет координат)")
        return best

    sq_of = {}
    for r, t in zip(out, records):
        sq_of[r["sid"]] = []
        for cat in POP:
            for rr in t.refs.get(cat, []):
                q = M.get(rr.target)
                if q is not None and q.type_name == "SQUAD_TEMPLATE" and q.refs.get("faction"):
                    sq_of[r["sid"]].append({"faction_sid": q.refs["faction"][0].target})

    LOOTISH = re.compile(r"loot|junk|ancient|nest|spawn", re.I)

    def shop_like(r):
        return any(not LOOTISH.search(v) for v in r["vendors"])

    cnt = collections.Counter()
    for r in out:
        ty, nm = r["type"], r["name"]
        rec_un = [u for u in r["uniques"] if u["recruit"] and (u["strong"] or r["pets"])]   # слабый признак (действие 3) годится только вместе с питомцем
        weak_un = [u for u in r["uniques"] if u["recruit"] and not u["strong"] and not r["pets"]]
        story = has_story_link(r)
        small = r["buildings_2500"] is None or r["buildings_2500"] <= 8
        heavy = r["n_squads"] >= 4 or r["members_est"] >= 8
        why, cls, host = [], "REVIEW", None
        if ty in CITY_T or ty in BASE_T:
            cls = "KEEP"
            why.append("город/крепость/хранилище (type %s)" % ty)
        elif HQ_NAME.search(nm) and r["owner_real"]:
            cls = "KEEP"
            why.append("база/штаб фракции %s по имени" % r["owner"])
        elif r["conductor_site"] and not (not r["vanilla"] and rec_un and not heavy and not story):
            cls = "KEEP"
            why.append("лорная точка конструктора (%s)" % r["conductor_site"])
        elif ty == 3:
            if r["vanilla"] or heavy or (r["buildings_2500"] or 0) > 8:
                cls = "KEEP"
                why.append("деревня%s" % (" (ваниль)" if r["vanilla"] else ", обжита"))
            else:
                cls = "REVIEW"
                why.append("малая модовая деревня: решить вручную")
        elif r["vanilla"] and (story or r["in_rules_files"] and r["in_rules_files"] != ["data/atlas_report.json"]):
            cls = "KEEP"
            why.append("ванильное, есть сюжетные/правила-ссылки: %s" % (story[:3] or r["in_rules_files"][:2]))
        elif r["vanilla"]:
            if rec_un and (small or r["buildings_2500"] is None) and not heavy:
                cls = "REVIEW"
                why.append("ванильное малое место с рекрутом %s: консервативно REVIEW" % ", ".join(u["name"] for u in rec_un))
            elif ty in (4, 9) or r["loot_spawn"]:
                cls = "KEEP"
                why.append("ванильные руины/логово/укрытие%s" % (" с лутом" if r["loot_spawn"] else ""))
            elif heavy or r["n_squads"]:
                cls = "KEEP"
                why.append("ванильная обжитая локация")
            else:
                cls = "REVIEW"
                why.append("ванильное пустое: REVIEW")
        else:
            # --- модовые
            if story:
                cls = "REVIEW"
                why.append("модовая, но есть входящие ссылки: %s" % story[:3])
            elif rec_un and not heavy and (r["buildings_2500"] or 0) > 25:
                cls = "REVIEW"
                why.append("рекрут (%s), но крупное место (%d зданий в %d ед.) — решить вручную" % (", ".join(u["name"] for u in rec_un), r["buildings_2500"], R_NEAR))
            elif rec_un and not heavy:
                cls = "MERGE"
                why.append("рекрутируемый уник (%s)%s" % (", ".join(u["name"] for u in rec_un), " + питомец" if r["pets"] else ""))
                host = pick_host(r)
            elif r["n_trader_squads"] and r["public"] and shop_like(r) and not heavy and ty in (0, 1, 3, 9) and r["n_squads"] <= 3 and (r["buildings_2500"] or 0) <= 25:
                cls = "MERGE"
                why.append("одиночная модовая лавка/торговец (%s)" % ", ".join(r["vendors"][:3] or ["is trader"]))
                host = pick_host(r, need_neutral=True)
            elif r["n_squads"] == 0 and not r["loot_spawn"] and not r["incoming_n"]:   # пустая модовая локация
                cls = "DROP"
                why.append("пусто: нет отрядов, лута и входящих ссылок")
            elif ty == 0 and r["n_squads"] and not r["uniques"]:
                cls = "KEEP"
                why.append("логово/лагерь/гнездо с обитателями (бой, лут, экология); ценного для переноса нет")
            elif ty in (4, 9, 0) and (r["loot_spawn"] or heavy):
                cls = "KEEP"
                why.append("логово/руины с лутом или охраной")
            elif r["uniques"] and not rec_un:
                cls = "REVIEW"
                why.append("есть уник без сильного признака рекрута (%s): %s" % ("слабый: действие 3" if weak_un else "нет", ", ".join(u["name"] for u in r["uniques"][:3])))
            elif heavy:
                cls = "KEEP"
                why.append("населённое место мода (отрядов %d)" % r["n_squads"])
            else:
                cls = "REVIEW"
                why.append("модовая малая локация без явной ценности/цели")
        if host:
            d, h, hw = host
            r["merge_host"] = {"sid": h.sid, "name": h.name, "owner": fname(town_fac(h)), "dist": round(d) if d is not None else None, "far": bool(d and d > FAR_HOST), "why": hw}
            r["move"] = {"uniques": [u["name"] for u in rec_un], "pets": [p["name"] for p in r["pets"]],
                         "vendor_squads": [s["name"] for s in r["squads"] if s["trader"]],
                         "all_squads": [s["name"] for s in r["squads"]]}
        r["class"], r["why"] = cls, "; ".join(why)
        cnt[cls] += 1

    summary = {"counts": dict(cnt), "skipped": dict(skipped), "towns_total": len(towns_all), "analysed": len(out),
               "zone_files": nz, "buildings_indexed": len(blds), "positions": len(pos),
               "recruit_signal": "dialogue name /recruit|join|hire/ либо реплика NPC с действием 3/18",
               "units": "world units (дом ~500)", "type_guess_note": "TYPE_GUESS выведен по именам, не из fcs.def"}
    json.dump({"summary": summary, "towns": sorted(out, key=lambda r: (r["class"], r["name"]))}, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(summary, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
