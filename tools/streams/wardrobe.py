"""Поток G WARDROBE (rules/streams/wardrobe.json, модель — docs/streams/WARDROBE.md §3).

Пул фракции = своё производство (вещи её культуры по каталогу + неиспользуемые вещи по сродству стиля)
            + торговля с соседями (пулы фракций с отношением ≥ trade_min) + трофеи с врагов (≤ trophy_max)
            (+ самоделки у бедных). Тиры по статам (data/catalog.json), диапазон тиров — по богатству фракции.
Персонажам добавляются варианты в те слоты, что у них уже есть (силуэт сохраняется), веса — по классу богатства;
элите — 1–2 опознавательные вещи фракции (слот заменяется целиком); бандитам — реликт T3 с весом 1 (≈1:45000).
Поглощает поток D: уровни качества (armour grade / upgrade chance / weapon level), T0-предметы WH; трофеи бандитов из ECONOMY.
Поля (DECISIONS 2026-11-11): CHARACTER clothing/weapons/crossbows/weapon level/armour grade/armour upgrade chance;
VENDOR_LIST clothing. Только добавление — существующие варианты не удаляются (кроме слота опознавательной вещи элиты).
"""
import collections
import json
import random
import re
import zlib
from math import ceil as math_ceil

from kmod import F32, Ref

TIERS = ["T0", "T1", "T2", "T3"]


def build(ctx, s, rules):
    M = ctx.M
    cat = [x for x in json.load(open(rules["catalog"], encoding="utf-8"))["items"]
           if x["sid"] in M and M[x["sid"]].type_name == x["type"] and not re.search(r"-KMM_\w+\.mod$", x["sid"])
           and not re.search(r"^#|\btest(er|ing)?\b|debug|dummy item|placeholder", x["name"], re.I)]   # без отладочных вещей
    cat = [x for x in cat if not x.get("nonlatin")                                                # без английского имени — не берём
           and (x["type"] != "CROSSBOW" or x.get("ranged") == "allow" or x["origin"] in ("imperial", "chaos", "xenos"))]   # огнестрел — по правилу владельца
    # --- WARD_SHARE C: модовые ARMOUR без своего меша (mesh/mesh female пусты или .\data\...) выглядят как ваниль — из пулов кандидатов убираем.
    # Ваниль не трогаем; исключения: источники slots_ext и реликт бандитов (T3 в слоте bandit_relic).
    if rules.get("require_own_mesh"):
        van_names = {n for n, _, _ in ctx.van}
        sx_src = {i["sid"] for i in rules["slots_ext"]["items"]}
        br_ = rules["bandit_relic"]

        def own_mesh(it):   # свой облик: свой меш ИЛИ своя текстура (перекраска с новой текстурой видна глазом, 2026-11-13)
            for k, v in it.values.items():
                if not isinstance(v, str) or not v.strip():
                    continue
                vl = v.strip().lower().replace("/", "\\")
                if vl.startswith(".\\data\\") or vl.startswith("data\\"):
                    continue
                if k in ("mesh", "mesh female") or vl.endswith((".dds", ".png", ".tga", ".jpg")):
                    return True
            return False
        n0 = len(cat)
        cat = [x for x in cat if x["type"] != "ARMOUR" or ctx.origin.get(x["sid"]) in van_names or x["sid"] in sx_src
               or (x["tier"] == br_["tier"] and x["group"] == br_["slot"]) or own_mesh(M[x["sid"]])]
        s.report["no_own_mesh_excluded"] = n0 - len(cat)
    LOOT = json.load(open(r"C:\KenshiModMap\data\catalog_loot.json", encoding="utf-8"))["items"]
    LOOT = [x for x in LOOT if x["sid"] in M and M[x["sid"]].type_name == "ITEM"]
    CLOAK = re.compile(rules["cloak_rx"], re.I)
    slots = rules["slots"]
    # вещь-часть тела расы (rules/excluded_mods.json item_race_lock, напр. Whistler Suit): только персонажам с явной расой из списка
    LOCK = {x["sid"]: set(x["race_lock"]) for x in cat if x.get("race_lock")}

    # --- T0-предметы WH (из потока D) ----------------------------------------------------
    t0_items = []
    for spec in rules["t0"]["items"]:
        src = ctx.find(*spec["src"])
        vals = {}
        for k, mult in spec["mult"].items():
            v = src.values[k]
            vals[k] = int(round(v * mult)) if isinstance(v, int) and not isinstance(v, bool) else F32(v * mult)
        vals["description"] = (src.values.get("description", "") + " Worn trophy from a fallen expedition.").strip()
        it = s.new(src.type_name, src.name + spec["suffix"], template=src.sid, values=vals)
        grp = None
        grp = next((x["group"] for x in cat if x["sid"] == src.sid), None)
        t0_items.append({"sid": it.sid, "name": it.name, "group": grp, "tier": "T0", "origin": "imperial", "styles": ["scrap"],
                         "worn_by": {}, "sold_in": [], "type": it.type_name})
        s.report["t0_items"] += 1
    cat += t0_items

    # --- SLOTS: клоны мелких вещей в слоты Nexus 1838 (EYES=4, GLOVES=10, NECK=11); исходник не меняем, из наших пулов убираем ---------
    SX = dict(rules["slots_ext"])
    if SX.get("enabled", True) is False:   # рубильник rules/features.json: slots_ext=false -> клонов нет
        SX["items"] = []
    hum_rx, hum_deny = re.compile(SX["human_mesh_rx"], re.I), re.compile(SX["human_deny_rx"], re.I)
    HUMAN_RACES = [r.sid for r in ctx.all("RACE") if hum_rx.search(str(r.values.get("male mesh") or "")) and not hum_deny.search(r.name or "")]
    s.report["slotx_human_races"] = len(HUMAN_RACES)
    src_cat = {x["sid"]: x for x in cat}
    SRC_SIDS = {i["sid"] for i in SX["items"]}
    CLONES, clone_of, vendor_clone = [], {}, []
    for spec in SX["items"]:
        src = M.get(spec["sid"])
        if src is None or src.type_name != "ARMOUR" or spec["sid"] not in src_cat:
            s.report["slotx_missing_src"] += 1
            continue
        allow = [r.target for r in src.refs.get("races", [])]
        if allow:   # ограничение в данных исходника (автор мода) — сохраняем как есть
            races_ref = [Ref(t_, 0, 0, 0) for t_ in allow]
            rkind = "data"
        else:       # данных нет, мэш человеческий — только расы с человеческим телом
            races_ref = [Ref(t_, 0, 0, 0) for t_ in HUMAN_RACES]
            rkind = "human"
        it = s.new("ARMOUR", src.name, template=src.sid, values={"slot": SX["enum"][spec["group"]]})
        if races_ref:
            it.refs["races"] = races_ref
        so = src_cat[spec["sid"]]
        tier = so["tier"] if TIERS.index(so["tier"]) <= TIERS.index(SX["tier_max"]) else SX["tier_max"]
        ent = {**{k: v for k, v in so.items() if k not in ("sid", "group", "tier")}, "sid": it.sid, "group": spec["group"], "tier": tier,
               "slotx": True, "src": spec["sid"], "rkind": rkind}
        CLONES.append(ent)
        clone_of[it.sid] = spec["sid"]
        s.report[f"slotx_clone:{spec['group']}"] += 1
        s.report[f"slotx_races:{rkind}"] += 1
    cat = [x for x in cat if x["sid"] not in SRC_SIDS] + CLONES
    # те же лавки, что у исходника: в VENDOR_LIST, где продаётся исходник, добавляем клон (не более vendor_cap на вещь)
    vl_all = sorted((v for v in ctx.all("VENDOR_LIST") if v.refs.get("clothing")), key=lambda v: v.sid)
    vend_n = collections.Counter()
    for c_ in CLONES:
        for vl in vl_all:
            if vend_n[c_["sid"]] >= SX["vendor_cap"]:
                break
            for r in vl.refs["clothing"]:
                if r.target == c_["src"]:
                    vendor_clone.append((vl.sid, Ref(c_["sid"], r.v0, r.v1, r.v2)))
                    vend_n[c_["sid"]] += 1
                    break
    s.report["slotx_vendor_refs"] = len(vendor_clone)
    G = {x["sid"]: x["group"] for x in cat}

    # --- DEDUP-POOLS (rules/dedup_canonical.json, tools/dedup_canonical.py): точные клоны и перекраски = одна вещь в пуле -------------
    # BK: sid → ключ группы (счётчик повторов и вес выбора — на группу); внутри группы канон (клоны) или цвет (семейство).
    # slots_ext (CLONES) и их исходники в группы не входят. Чужие записи не меняем.
    DP = rules.get("dedup_pools", {})
    BK, CANON_OF, COLOR_OF = {}, {}, {}
    if DP.get("enabled"):
        dcan = json.load(open(DP["file"], encoding="utf-8"))
        in_cat = {x["sid"] for x in cat if not x.get("slotx")}
        for g_ in dcan["clone_groups"]:
            mem = [g_["canon"]] + g_["clones"]
            if g_["canon"] in in_cat:
                for m_ in mem:
                    if m_ in in_cat:
                        BK[m_] = "dg:" + g_["canon"]
                        CANON_OF[m_] = g_["canon"]
        for f_ in dcan["families"]:
            ents = [e for e in f_["members"] if e["sid"] in in_cat]
            if len(ents) < 2:
                continue
            for e in ents:
                COLOR_OF[e["sid"]] = e["color"]
                for m_, c_ in list(CANON_OF.items()) + [(e["sid"], e["sid"])]:
                    if c_ == e["sid"]:
                        BK[m_] = "df:" + f_["key"]
        s.report["dedup_clone_items"] = sum(1 for k in BK if k in CANON_OF and BK[k].startswith("dg:"))
        s.report["dedup_group_keys"] = len(set(BK.values()))
        s.report["dedup_family_items"] = sum(1 for v in BK.values() if v.startswith("df:"))
    CUR_FAC = [None]   # фракция текущего персонажа/лавки — для культурного выбора цвета внутри группы

    class GSet(set):
        """have: персонаж уже носит любую вещь группы → остальные вещи группы считаются «в наличии» (один цвет на персонажа)."""
        def __init__(self, it=()):
            super().__init__()
            for v in it:
                self.add(v)

        def add(self, v):
            set.add(self, v)
            if v in BK:
                set.add(self, BK[v])

        def __contains__(self, v):
            return set.__contains__(self, v) or (v in BK and set.__contains__(self, BK[v]))

    # PALETTE (2026-11-14, плейтест: «убрать обилие перекраски, мрачные тёмные оттенки, где уместно и у кого уместно»):
    # яркий цвет (по имени/hex, tools/palette_audit.py → data/palette_audit.json) в добавленных пулах — только фракциям, кому он по лору.
    PAL = rules.get("palette") or {}
    IC = {}
    if PAL.get("enabled"):
        try:
            IC = json.load(open(PAL["item_colors"], encoding="utf-8"))["item_colors"]
        except Exception:
            IC = {}

    def pal_ok(y, fname):
        c = IC.get(y["sid"])
        if not c or c[0] != "bright":
            return True
        return c[1] in PAL.get("faction_bright_ok", {}).get(fname or "", ())

    def member_pick(rng, members):
        """Внутри группы: клоны → канон; перекраски → вес 1, ×3 если цвет носит эта фракция по каталогу, × color_pref фракции."""
        m2 = [x for x in members if x["sid"] not in CANON_OF or CANON_OF[x["sid"]] == x["sid"]] or members
        if IC:
            m2 = [x for x in m2 if pal_ok(x, CUR_FAC[0])] or m2   # из перекрасок — уместный фракции цвет
        if len(m2) == 1:
            return m2[0]
        fn_ = CUR_FAC[0]
        cp = DP.get("color_pref", {}).get(fn_, {}) if fn_ else {}
        w_ = [(DP.get("worn_mult", 3.0) if fn_ and fn_ in x["worn_by"] else 1.0) * cp.get(COLOR_OF.get(x["sid"], ""), 1.0) for x in m2]
        return rng.choices(m2, weights=w_)[0]

    # --- фракции, богатство, отношения -----------------------------------------------------
    # «not real» в Kenshi лишь прячет фракцию из списков интерфейса (Cannibals, Fogmen, Shrieking Bandits, Skeleton Legion…) —
    # их отряды настоящие. До 2026-11-14 гардероб их выкидывал, и ~500 персонажей одевались как бесфракционные. Имя — за обычной записью.
    facs = {}
    for f in sorted(ctx.all("FACTION"), key=lambda f: bool(f.values.get("not real", False))):
        facs.setdefault(f.name, f)
    frule = {ctx.find(*f["faction"]).name: f for f in rules["factions"]}

    def wealth(fname):
        if fname is None:
            return "mid", "T0", "T1"
        f = frule.get(fname)
        if f:
            return {"T0": "poor", "T1": "mid"}.get(f["base"], "rich"), f["base"], f["leader"]
        if facs[fname].values.get("fundamental type") == 8:
            return "poor", "T0", "T1"
        return "mid", "T0", "T1"

    rel = collections.defaultdict(dict)
    for f in facs.values():
        for r in f.refs.get("relations", []):
            if r.target in M and M[r.target].name in facs:
                rel[f.name][M[r.target].name] = r.v0
                rel[M[r.target].name].setdefault(f.name, r.v0)   # отношения симметризуем для пулов

    # --- пулы: своё производство -------------------------------------------------------------
    own = collections.defaultdict(list)
    whmap = rules["wh_origin_factions"]
    poor_names = [n for n in facs if wealth(n)[0] == "poor"]
    unused_placed = 0
    for x in cat:
        if x["worn_by"]:
            for fn in x["worn_by"]:
                if fn in facs:
                    own[fn].append(x)
        org = x["origin"]
        targets = []
        if org == "imperial":
            targets = list(whmap["imperial"])   # копия: += ниже портил правило (2026-11-13: WH-экзотика у паладинов и бандитов)
        elif org == "chaos":
            targets = list(whmap["chaos"])
        elif org == "xenos":
            targets = list(whmap["xenos_necron"] if "Necron" in x.get("mod", "") or "40K Necrons" in x.get("mod", "") else whmap["xenos_orc"])
        if not x["worn_by"] and not x["sold_in"] and org not in ("imperial", "chaos", "xenos"):   # неиспользуемые вещи — по сродству стиля (экзотика — только своим)
            for st in x["styles"]:
                for t in rules["style_affinity"].get(st, []):
                    targets += poor_names if t == "poor" else [t]
            if targets:
                unused_placed += 1
        for t in set(targets):
            if t in facs and x not in own[t]:
                own[t].append(x)
    selfmade = [x for x in cat if x["origin"] == "selfmade"]
    generic = [x for x in cat if x["origin"] == "generic" and x["worn_by"] == {}]
    s.report["unused_items_placed"] = unused_placed

    # COHERENCE (2026-11-14, плейтест: Desert Divers без своей брони, ниндзя/самураи в чужом): профиль фракции = происхождения и
    # стили вещей, в которые её одели авторы (исходные clothing её персонажей). Общий пул и торговля — только из этих культур;
    # generic/selfmade — только при совпадении узкого стиля (широкий «plate» не считается).
    CO = rules.get("coherence", {})
    IDN = rules.get("identity", {})
    XCAT = {x["sid"]: x for x in json.load(open(rules["catalog"], encoding="utf-8"))["items"]}   # полный каталог: родные вещи без своего меша тоже узнаются
    FPROF = {}

    def fprof(fname):
        if fname in FPROF:
            return FPROF[fname]
        pr = None
        if fname is not None and CO.get("enabled"):
            orig, sty = {"culture:" + fname}, set()
            for csid, cfn in char_fac.items():
                if cfn != fname or csid not in M:
                    continue
                for r in M[csid].refs.get("clothing", []):
                    x = XCAT.get(r.target)
                    if x and x["type"] == "ARMOUR":
                        if x["origin"].startswith("culture:"):
                            orig.add(x["origin"])
                        sty.update(x["styles"])
            pr = {"orig": orig, "styles": sty - set(CO.get("broad_styles", []))}
        FPROF[fname] = pr
        return pr

    def coh(lst, fname):
        pr = fprof(fname)
        if not pr:
            return lst
        return [y for y in lst if y["origin"] in pr["orig"]
                or (y["origin"] in ("generic", "selfmade") and set(y["styles"]) & pr["styles"])]

    def pools(fname):
        tr = rules["relations"]
        trade = [y for o, v in rel[fname].items() if v >= tr["trade_min"] for y in own.get(o, [])] + generic
        trophy = [y for o, v in rel[fname].items() if v <= tr["trophy_max"] for y in own.get(o, [])]
        if wealth(fname)[0] == "poor":
            trophy += t0_items
        P_ = {"own": own.get(fname, []), "trade": coh(trade, fname), "trophy": trophy, "selfmade": selfmade, "common": coh(COMMON, fname)}
        if IC:
            for k_ in ("trade", "trophy", "selfmade", "common"):
                P_[k_] = [y for y in P_[k_] if pal_ok(y, fname)]
            # своё: яркое — только вещь культуры этой фракции (канон: белое HN, наряды Shrieking Bandits), не просто «кто-то носил»
            P_["own"] = [y for y in P_["own"] if pal_ok(y, fname) or y["origin"] == "culture:" + fname]
        return P_

    # --- кто носит: персонаж → фракция, лидер ли ---------------------------------------------------
    start_squads = {r.target for st in M.values() if st.type_name == "NEW_GAME_STARTOFF" for rs in st.refs.values() for r in rs}
    town_fac = {}   # отряд без своей фракции → фракция города, где он живёт/ходит
    for t in ctx.all("TOWN"):
        if t.refs.get("faction") and t.refs["faction"][0].target in M:
            for c in ("residents", "bar squads", "roaming squads"):
                for r in t.refs.get(c, []):
                    town_fac.setdefault(r.target, M[t.refs["faction"][0].target].name)
    char_fac, leaders, ranks = {}, set(), set()   # ranks: шаблон рядового — фиксированная элитная вещь досталась бы всем
    for sq in ctx.all("SQUAD_TEMPLATE") + ctx.all("UNIQUE_SQUAD_TEMPLATE"):
        if sq.sid in start_squads:
            continue
        if sq.refs.get("faction") and sq.refs["faction"][0].target in M:
            fn = M[sq.refs["faction"][0].target].name
        elif sq.sid in town_fac:
            fn = town_fac[sq.sid]
        else:
            continue
        if fn not in facs:
            continue
        for c in ("leader", "squad", "squad2") + tuple(rules.get("squad_ref_cats_extra", ())):   # WARD_SHARE B: «choosefrom list» (наёмники/рекруты)
            for r in sq.refs.get(c, []):
                char_fac.setdefault(r.target, fn)
                if c == "leader":
                    leaders.add(r.target)
                else:
                    ranks.add(r.target)
    leaders -= ranks   # 2026-11-15 плейтест: все туманники в одном Armoured Hood — общий шаблон лидера и рядовых

    # география огнестрела (B4 Н9/И8): множитель частоты ствола по расстоянию дома шаблона до ближайшей мастерской
    GEO_ = rules["context"]["firearms"].get("geo") or {}
    GG = None
    char_gmult, fac_gmult = {}, {}
    if GEO_.get("enabled"):
        from _shared import GunGeo
        GG = GunGeo(ctx, GEO_, [x["sid"] for x in cat if x["type"] == "CROSSBOW" and x.get("firearm")])
        _cpos, _ = GG.maps()
        char_gmult = {c_: sum(GG.mult(p_) for p_ in ps) / len(ps) for c_, ps in _cpos.items()}
        _fm = collections.defaultdict(list)
        for t_ in GG.towns:
            fr_ = t_.refs.get("faction")
            if fr_ and fr_[0].target in M and t_.sid in GG.pos:
                _fm[M[fr_[0].target].name].append(GG.mult(GG.pos[t_.sid]))
        fac_gmult = {k_: sum(v_) / len(v_) for k_, v_ in _fm.items()}
        s.report["geo_hubs"] = len(GG.hubs)
        s.report["geo_hub:" + "; ".join(sorted(h[0] for h in GG.hubs.values()))] = 1

    RACE_EXPLICIT = set()   # персонажи с явной расой (ref «race»): строгая проверка

    def race_set(ch, fname):
        if fname is None and not ch.refs.get("race"):
            return set()
        r = [x.target for x in ch.refs.get("race", [])]
        if r:
            RACE_EXPLICIT.add(ch.sid)
            return set(r)
        return {x.target for x in facs[fname].refs.get("races", [])}   # смесь рас фракции: раса выпадает при спавне

    restricted_given = collections.Counter()

    def race_ok(item_sid, races, explicit=True):
        """Явная раса — вещь должна ей подходить. Смесь рас фракции (раса неизвестна до спавна) — вещь годится,
        если её может носить хотя бы одна раса фракции: игра при спавне надевает только подходящее (как в ванильных
        смешанных списках). Так вещи с ограничением по расам не отбрасываются, а достаются подходящим расам."""
        if item_sid in LOCK:   # у вещи нет ограничения по расе в данных — игра надела бы её любому; даём только явной расе
            return explicit and bool(races) and races <= LOCK[item_sid]
        it = M.get(item_sid) or s.mb.items.get(item_sid)   # свои новые T0-предметы ещё не в контексте
        if it is None:
            return True
        allow = {x.target for x in it.refs.get("races", [])}
        deny = {x.target for x in it.refs.get("races exclude", [])}
        if not allow and not deny:
            return True
        if explicit:
            return bool(races) and (not allow or races <= allow) and not (races & deny)
        if not races:
            return False
        fit = (races & allow if allow else set(races)) - deny
        return bool(fit)

    FAMLIM = {"fam:gorillo_pelt": rules.get("family_cap", 30)}   # семейство «Gorillo Pelt» (6 окрасок одной накидки) считается как одна вещь

    # редкие семейства (rules rare_items): общий потолок размещений на всё семейство — владелец 2026-11-13: Hazards Shell слишком часто
    RARE = [(re.compile(r_["name_rx"], re.I), "rare:" + r_["id"], int(r_["cap"])) for r_ in rules.get("rare_items", [])]
    for _rx, _k, _cap in RARE:
        FAMLIM[_k] = _cap

    def UK(x):
        for _rx, _k, _cap in RARE:
            if _rx.search(x["name"]):
                return _k
        return "fam:gorillo_pelt" if "gorillo pelt" in x["name"].lower() else BK.get(x["sid"], x["sid"])

    LIM = lambda x: FAMLIM.get(UK(x), HARD)  # noqa: E731
    use = collections.Counter(vend_n)   # SLOTS: размещения клонов в лавках уже учтены. Мягкий потолок повторов: вес выбора убывает с числом использований; жёсткий — выше вещь не выдаётся
    use_w, use_x, use_b, use_l = (collections.Counter() for _ in range(4))   # оружие / арбалеты / рюкзаки / лут — свои счётчики
    CAP = rules.get("repeat_soft_cap", 20)
    HARD = rules.get("repeat_hard_cap", 25)

    def pick(rng, cand, hard=None, counter=None, cap=None, boost_cloak=False):
        counter = use if counter is None else counter
        cap = CAP if cap is None else cap
        if hard:
            cand = [c for c in cand if counter[UK(c)] < FAMLIM.get(UK(c), hard)]
        if not cand:
            return None
        if BK:   # группа = одна вещь: вес 1 на группу (не на запись), цвет/канон — внутри
            bk = {}
            for c in cand:
                bk.setdefault(UK(c), {}).setdefault(c["sid"], c)
            if any(len(v) > 1 for v in bk.values()):
                keys = list(bk)
                w = [(1.0 / (1.0 + (counter[k] / cap) ** 2)) * (rules["cloak_boost"] if boost_cloak and any(CLOAK.search(c["name"]) for c in bk[k].values()) else 1.0) for k in keys]
                k = rng.choices(keys, weights=w)[0]
                mem = list(bk[k].values())
                x = mem[0] if len(mem) == 1 else member_pick(rng, mem)
                counter[k] += 1
                return x
        w = [(1.0 / (1.0 + (counter[UK(c)] / cap) ** 2)) * (rules["cloak_boost"] if boost_cloak and CLOAK.search(c["name"]) else 1.0) for c in cand]
        x = rng.choices(cand, weights=w)[0]
        counter[UK(x)] += 1
        return x

    by_group = lambda lst, g, tiers: [x for x in lst if x["group"] == g and x["tier"] in tiers]  # noqa: E731

    def is_exotic(x):
        """«Божественное» (DESIGN.md): WH-происхождение или реликт = T3 без ванильной культуры (не элитная броня Holy Nation и т.п.)."""
        return x["origin"] in ("imperial", "chaos", "xenos") or (x["tier"] == "T3" and not x["origin"].startswith("culture:"))
    COMMON = [x for x in cat if x["type"] == "ARMOUR" and x["sid"] not in LOCK and not is_exotic(x) and x["group"] in slots]   # общий пул без привязки к фракции
    BP_OK = [x for x in cat if x["group"] == "armour:backpack" and not is_exotic(x) and x["sid"] not in LOCK]
    qlev = rules["quality_levels"]
    relic_pool = [x for x in cat if x["tier"] == rules["bandit_relic"]["tier"] and x["group"] == rules["bandit_relic"]["slot"] and x["sid"] not in LOCK]
    tiers_data = {}
    WH_NAMES = {n for v in whmap.values() for n in v}
    n_chars = 0
    pending, pending_v = [], []   # сначала план, потом бюджет происхождения, потом запись
    # персонажи вне отрядов с фракцией (жители, одиночки, шаблоны модов): своя фракция из ссылки «faction», иначе безфракционный «общий» гардероб (None)
    SKIP_NAME = re.compile(r"test|initialisation|generation_template|nobody|player|dummy|placeholder", re.I)
    SKIP_RACE = re.compile(r"skeleton|robot|machine|spider|animal|beast|crab|bull|dog|garru|raptor|leviathan|goat|bat\b", re.I)
    start_chars = {r.target for sq in M.values() if sq.sid in start_squads for c in ("leader", "squad", "squad2") for r in sq.refs.get(c, [])}
    fb = {}
    for ch in M.values():
        if ch.type_name != "CHARACTER" or ch.sid in char_fac or ch.sid in start_chars or not ch.refs.get("clothing") or SKIP_NAME.search(ch.name or ""):
            continue
        rn = " ".join(M[r.target].name for r in ch.refs.get("race", []) if r.target in M)
        if SKIP_RACE.search(rn):
            continue
        fr = ch.refs.get("faction", [])
        fn = M[fr[0].target].name if fr and fr[0].target in M and M[fr[0].target].name in facs else None
        fb[ch.sid] = fn
    s.report["fallback_candidates"] = len(fb)
    order = sorted(char_fac.items()) + sorted(fb.items())
    random.Random(rules["seed"]).shuffle(order)   # случайный обход: жёсткий потолок повторов не бьёт по поздним в алфавите
    OPS = rules["options_per_slot"]
    FILL = rules["fill_empty"]
    BPR = rules["backpack"]
    LT = rules["loot"]
    # Е3 ЛИЧНЫЕ ВЕЩИ: архетип фракции (тот же, что у матрицы отношений behavior.json) -> набор быта; заменяет часть общего лута, не сверху
    PB = LT.get("belongings") or {}
    WRB = json.load(open(r"C:\KenshiModMap\rules\streams\behavior.json", encoding="utf-8"))["world_relations"] if PB.get("enabled") else None
    FAC_N = {f.name: f for f in ctx.all("FACTION")} if PB.get("enabled") else {}
    ARCH = {}

    def belong_set(fname):
        if fname in ARCH:
            return ARCH[fname]
        key = None
        for k_, rx_ in PB.get("by_name_rx", []):
            if fname and re.search(rx_, fname, re.I):
                key = k_
                break
        if key is None and fname in FAC_N:
            n_, f_ = fname, FAC_N[fname]
            import behavior as _bh   # rules/culture.json archetype — выше override_by_name (тот же порядок, что в behavior.archetype_of)
            a_ = (_bh.culture().get("factions", {}).get(n_) or {}).get("archetype") or WRB["override_by_name"].get(n_)
            if a_ is None:
                a_ = next((a for a, names in WRB["archetype_by_name"].items() if n_ in names), None)
            if a_ is None:
                a_ = next((a for a, rx in WRB["archetype_regex"] if re.search(rx, n_)), None)
            if a_ is None and not f_.values.get("not real"):
                a_ = WRB["type_fallback"].get(str(f_.values.get("fundamental type", 4)), "settler")
            key = PB["by_arch"].get(a_ or "")
        items = []
        for it in PB["sets"].get(key, []) if key else []:
            sid = it["sid"]
            if sid in M and M[sid].type_name == "ITEM" and float(M[sid].values.get("value", 0) or 0) <= PB["value_cap"]:
                items.append(it)
        ARCH[fname] = (key, items)
        return ARCH[fname]
    WR = rules["weapons"]
    CX = rules["context"]
    stat = collections.Counter()
    # WARD_SHARE B: «unique» берём из ванильной цепочки (gamedata/Newwworld/Dialogue/rebirth), а не из итогового контекста: моды вроде
    # No_generic_recruits_now_unique / Kaizo ставят unique всем наёмникам и барменам — это не сюжетные персонажи с фиксированным видом.
    van_unique = {}
    if rules.get("unique_from_vanilla"):
        for _n, _m, _ in ctx.van:
            for it_ in _m.items:
                if it_.type_name == "CHARACTER" and "unique" in it_.values:
                    van_unique[it_.sid] = bool(it_.values["unique"])
    SVF = set((CX["lore_hard"].get("savage") or {}).get("factions", []))
    PA_FAC_N, PA_FAC_ALL = collections.Counter(), collections.Counter()
    # SET_PACKAGES (2026-11-14, docs/SLOTS_PLAN.md): Kenshi выбирает вещь в каждом слоте отдельно — комплекты рассыпаются.
    # Части персонажей выдаётся «пакет»: один комплект (префикс имени + мод), его вещь в слоте весит mult × остальных добавок,
    # родные вещи в этих слотах не поднимаются. Случайность остаётся: прочие варианты слота и оригиналы на месте.
    SP = rules.get("set_packages") or {}
    SETS = []
    if SP.get("enabled"):
        gen_tok = set(SP.get("generic_tokens", []))
        by_ = collections.defaultdict(list)
        for x in cat:
            if x["type"] != "ARMOUR":
                continue
            nm = x["name"]
            pre = nm.split(" - ")[0].strip() if " - " in nm else nm.split()[0]
            if pre.lower() in gen_tok or len(pre) < 3:
                continue
            by_[(pre, x["sid"].split("-", 1)[-1])].append(x)
        main_ = set(SP["main_slots"])
        for (pre, mod_), L_ in by_.items():
            sl_ = {x["group"] for x in L_}
            if len(sl_ & main_) >= SP.get("min_main_slots", 3):
                SETS.append({"key": pre + "|" + mod_, "items": L_, "slots": sl_})
        s.report["set_packages_sets"] = len(SETS)
    UNTOUCHED = set(rules.get("untouched_factions", []))   # 2026-11-15 плейтест: Soulbodies с рюкзаками и хламом — фракции со своим лором не одеваем
    for sid, fname in order:
        ch = M.get(sid)
        if fname in UNTOUCHED:
            s.report["untouched_faction_chars"] += 1
            continue
        if fname in SVF:
            s.report["savage_seen"] += 1
        if (ch is None or ch.type_name != "CHARACTER" or not ctx.in_game(sid)
                or (ch.values.get("unique") and (not rules.get("unique_from_vanilla") or van_unique.get(sid, True))) or ch.values.get("slave", 0)
                or ch.values.get("NPC class") == 6 or n_chars >= rules["max_characters"]):
            continue
        CUR_FAC[0] = fname
        cls, base_t, lead_t = wealth(fname)
        W = rules["wealth"][cls]
        is_leader = sid in leaders
        is_wh = fname in WH_NAMES
        bi, li = TIERS.index(base_t), TIERS.index(lead_t)
        tiers = TIERS[max(0, bi - 1):bi + 1] if not is_leader else TIERS[bi:li + 1]
        tiers = [t for t in tiers if t != "T3" or is_leader]
        rng = random.Random(rules["seed"] + zlib.crc32(sid.encode()))
        P = pools(fname)
        races = race_set(ch, fname)
        explicit = sid in RACE_EXPLICIT
        rok = lambda item_sid: race_ok(item_sid, races, explicit)  # noqa: E731
        SV = CX["lore_hard"].get("savage") or {}
        savage = fname in SV.get("factions", []) or bool(
            SV.get("char_name_rx") and re.search(SV["char_name_rx"], ch.name or "", re.I)
            and not re.search(SV.get("char_name_exclude_rx", "^$"), ch.name or "", re.I))
        PG = CX["lore_hard"].get("pagan") or {}
        pagan_allowed = (fname in PG.get("factions", []) or (PG.get("poor_ok") and cls == "poor"))
        def pg_ok(x):
            return pagan_allowed or not PG or not re.search(PG["name_rx"], x["name"], re.I)
        cname0 = ch.name or ""
        uni_by_name = False
        is_uniform = False
        if not savage:   # форма регулярной армии (rules lore_hard.uniforms): тот же замок культуры, свой стиль
            for U in CX["lore_hard"].get("uniforms", []):
                by_name = bool(U.get("char_name_rx") and re.search(U["char_name_rx"], cname0, re.I)
                               and not re.search(U.get("char_name_exclude_rx", "^$"), cname0, re.I)
                               and (not U.get("char_factions") or fname in U["char_factions"]))
                if fname in U.get("factions", []) or by_name:
                    SV, savage = U, True
                    is_uniform = True
                    uni_by_name = fname not in U.get("factions", [])   # форма по имени в чужой фракции: её worn_by не в счёт
                    s.report["uniform_chars:" + str(U.get("id") or fname)] += 1
                    break
        if savage:
            s.report["savage_chars"] += 1
            s.report["savage_fac:" + str(fname)] += 1
        # BALANCE: окно тиров снаряжения вокруг тира статов персонажа (rules stat_tiers); дикие/форма — без изменений
        STR = rules.get("stat_tiers") or {}
        st_i = None
        cap_i = bi
        if STR.get("enabled") and not savage:
            cs_ = int(ch.values.get("combat stats", 0) or 0)
            st_i = sum(cs_ >= b_ for b_ in STR["bounds"])
            hi0 = li if is_leader else bi
            hi = max(min(hi0, st_i + 1), min(st_i, hi0 + 1))
            lo = max(0, hi - 1) if not is_leader else max(0, min(bi, hi))
            new_t = [t_ for t_ in TIERS[lo:hi + 1] if t_ != "T3" or is_leader] or [TIERS[min(hi, 2)]]
            if new_t != tiers:
                stat["stat_tier_shift_up" if TIERS.index(new_t[-1]) > TIERS.index(tiers[-1]) else "stat_tier_shift_down" if TIERS.index(new_t[-1]) < TIERS.index(tiers[-1]) else "stat_tier_shift_same_top"] += 1
            tiers = new_t
            cap_i = min(bi, hi)
            stat["stat_tier_chars:T%d" % st_i] += 1
        def sav_ban(nm):   # шлем/металл у диких (владелец 2026-11-15): нельзя ни трофеем, ни «своим» по worn_by
            return bool(SV.get("ban_rx")) and bool(re.search(SV["ban_rx"], nm or "", re.I)) and not re.search(SV.get("ban_keep_rx", "^$"), nm or "", re.I)
        def sav_ok(x):
            if re.search(SV.get("exclude_rx", "^$"), x["name"], re.I) or sav_ban(x["name"]):
                return False
            return bool(re.search(SV["name_rx"], x["name"], re.I)) or (fname in x.get("worn_by", {}) and not uni_by_name)
        have = GSet(r.target for r in ch.refs.get("clothing", []))
        # Полный сет силовой брони (плейтест 2026-11-13: астартес «Man-eating shark» остались в частичных сетах):
        # персонажа, который в исходных данных носит силовую броню на теле, гардероб в слотах сета не трогает.
        PAX = CX["lore_hard"]["power_armor"]
        pa_char = any(G.get(r.target) == "armour:body" and r.target in M and re.search(PAX["name_rx"], M[r.target].name or "", re.I)
                      for r in ch.refs.get("clothing", []))
        SET_SLOTS = set(PAX.get("set_slots", ["armour:hat", "armour:body", "armour:legs", "armour:boots"]))
        if pa_char:
            s.report["pa_full_set_kept"] += 1
            PA_FAC_N[fname] += 1
        PA_FAC_ALL[fname] += 1
        groups_here = {G.get(r.target) for r in ch.refs.get("clothing", [])}
        add, dele = [], []
        spk = {}   # слот -> вещь комплекта
        if SETS and not pa_char and not savage and not is_wh and rng.random() < (SP["p_leader"] if is_leader else SP["p_by_class"].get(cls, 0)):
            okp = {y["sid"] for k_ in ("own", "trade", "common") for y in P[k_]}
            wide_ = set(TIERS[max(0, TIERS.index(tiers[0]) - 1):min(len(TIERS), TIERS.index(tiers[-1]) + 2)]) if tiers else set(TIERS)
            cands_ = []
            for st_ in SETS:
                its_ = [x for x in st_["items"] if x["sid"] in okp and x["tier"] in wide_ and rok(x["sid"]) and pg_ok(x) and not is_exotic(x)
                        and use[UK(x)] < LIM(x) and (not is_uniform or sav_ok(x))
                        and (x["origin"] == "culture:" + (fname or "") or coh([x], fname))   # комплект своей культуры, а не что пришло торговлей
                        and (not re.search(SP["profession_rx"], x["name"], re.I) or re.search(SP["profession_rx"], ch.name or "", re.I))]
                sc_ = SP.get("set_culture", {}).get(st_["key"].split("|")[0])
                if sc_ and fname not in sc_:
                    continue   # комплект чужого народа (хайверские «Stickperson» и т.п.)
                if any(x["origin"].startswith("culture:") and x["origin"] != "culture:" + (fname or "") for x in its_)                         and not any(x["origin"] == "culture:" + (fname or "") for x in its_):
                    continue   # культурный комплект — только своей фракции
                gs_ = {x["group"] for x in its_} & set(slots)
                if len(gs_ & set(SP["main_slots"])) >= SP.get("min_main_slots", 3):
                    own_ = sum(1 for x in its_ if x["origin"] == "culture:" + (fname or ""))
                    cands_.append((st_, its_, 1 + 3 * own_))
            if cands_:
                st_, its_, _ = rng.choices(cands_, weights=[c[2] for c in cands_])[0]
                for g_ in {x["group"] for x in its_}:
                    spk[g_] = rng.choice(sorted([x for x in its_ if x["group"] == g_], key=lambda x: x["sid"]))
                s.report["set_packages_chars"] += 1
                s.report["set_pkg:" + str(fname) + " <- " + st_["key"]] += 1
                s.report["set_packages_slots"] += len(spk)
        for g in slots:
            if pa_char:   # носитель силовой брони: экипировка автора мода целиком (пояс тоже: кандалы/шляпы им не к лицу)
                continue
            if g not in groups_here:
                if is_wh or rng.random() >= FILL.get(g, 0) * (SV.get("fill_mult", 1) if savage else 1):   # пустой в ваниле слот заполняем долей персонажей; у WH — свой набор; дикие реже (SAVAGE_BARE)
                    continue
                stat["slot_filled"] += 1
            fixed = is_leader and not savage and g in W["elite_fixed"] and fname not in WH_NAMES and g in groups_here   # у WH-элиты опознавательное уже своё (моды)
            if fixed:
                cand = [x for x in by_group(P["own"], g, TIERS) if rok(x["sid"]) and not is_exotic(x) and use[UK(x)] < LIM(x)]
                if cand:
                    best = max(cand, key=lambda x: (sum(x["worn_by"].values()), x["stat_score"] if "stat_score" in x else 0))
                    dele += [r.target for r in ch.refs.get("clothing", []) if G.get(r.target) == g
                             and r.target != best["sid"]]
                    add.append(Ref(best["sid"], 1, 100, 0))
                    use[UK(best)] += 1
                    s.report["elite_fixed"] += 1
                    continue
            for _ in range(OPS.get(g, OPS["default"])):
                src = rng.choices(list(W["mix"]), weights=list(W["mix"].values()))[0]
                cand = [x for x in by_group(P[src], g, tiers) if x["sid"] not in have and rok(x["sid"]) and use[UK(x)] < LIM(x) and (is_wh or not is_exotic(x)) and pg_ok(x)]
                if len(cand) < rules.get("min_pool", 15):   # маленький пул (майки T0 и т.п.): тир шире на соседний
                    wide = TIERS[max(0, TIERS.index(tiers[0]) - 1):min(len(TIERS), TIERS.index(tiers[-1]) + 2)] if tiers else TIERS
                    wide = [t for t in wide if t != "T3" or is_leader]
                    cand = [x for x in by_group(P[src], g, wide) if x["sid"] not in have and rok(x["sid"]) and use[UK(x)] < LIM(x) and (is_wh or not is_exotic(x)) and pg_ok(x)] or cand
                if not cand:
                    cand = [x for x in by_group(P["own"] + P["trade"] + P["common"], g, tiers) if x["sid"] not in have and rok(x["sid"]) and use[UK(x)] < LIM(x) and (is_wh or not is_exotic(x)) and pg_ok(x)]
                trophy = False
                if savage:
                    if rng.random() < SV.get("trophy", 0):
                        trophy = True   # мародёрка: трофеем можно и шлем/металл, но редко (trophy_share)
                    else:
                        cand = [x for x in cand if sav_ok(x)] or [x for x in by_group(P["own"] + P["trade"] + P["common"], g, TIERS[:bi + 2])
                                                               if x["sid"] not in have and rok(x["sid"]) and use[UK(x)] < LIM(x) and sav_ok(x) and (is_wh or not is_exotic(x))]
                if not cand:
                    continue
                x = pick(rng, cand, hard=HARD, boost_cloak=g in ("armour:shirt", "armour:body"))
                if x is None:
                    continue
                have.add(x["sid"])
                it_ = M.get(x["sid"])
                if it_ is not None and (it_.refs.get("races") or it_.refs.get("races exclude")):
                    restricted_given["explicit" if explicit else "faction_mix"] += 1
                w_sv = SV.get("weight", W["weight"]) if savage else W["weight"]   # SAVAGE_BARE: у диких вес как у ванильных костей/шкур, не 15000 бедного класса
                add.append(Ref(x["sid"], 1, max(1, int(w_sv * SV.get("trophy_share", 0.1))) if trophy else w_sv, 0))
                s.report[f"pick:{src}"] += 1
                if savage:
                    s.report["ctx:savage_trophy" if trophy else "ctx:savage_own"] += 1
        for g_, x in spk.items():   # SET_PACKAGES: вещь комплекта доминирует в своём слоте
            if x["sid"] in have:
                continue
            ow_ = sum(r.v1 for r in add if (G.get(r.target) == g_)) or W["weight"]
            have.add(x["sid"]); add.append(Ref(x["sid"], 1, max(1, int(ow_ * SP["mult"])), 0))
        # --- контекст v3 (rules context): лор, климат, ремесло, аксессуары ----------------------------
        cname = ch.name or ""
        def cx_add(g, rx, p, label, n=1):
            if pa_char:
                return
            if rng.random() >= p:
                return
            c_ = [x for x in P["own"] + P["trade"] + P["common"] if x["group"] == g and x["sid"] not in have and rok(x["sid"]) and not is_exotic(x)
                  and use[UK(x)] < LIM(x) and (rx is None or re.search(rx, x["name"], re.I)) and x["tier"] in TIERS[:cap_i + 2]
                  and (not savage or sav_ok(x)) and pg_ok(x)]
            for _ in range(n):
                x = pick(rng, list({c["sid"]: c for c in c_ if c["sid"] not in have}.values()), hard=HARD)
                if x:
                    have.add(x["sid"]); add.append(Ref(x["sid"], 1, W["weight"], 0)); s.report["ctx:" + label] += 1
        PA = CX["lore_hard"]["power_armor"]
        if fname in PA["factions"] and ch.refs.get("clothing") and not ch.values.get("unique") and not pa_char:
            if rng.random() < PA["share"]:
                org = PA["factions"][fname]
                pa = [x for x in cat if x["group"] == PA["slot"] and x["origin"] == org and re.search(PA["name_rx"], x["name"], re.I) and x["sid"] not in LOCK
                      and rok(x["sid"]) and use[UK(x)] < LIM(x)]
                pa_set_rx = PA.get("set_item_rx", PA["name_rx"])
                got_pa = []
                for _ in range(PA["options"]):
                    x = pick(rng, [y for y in pa if y["sid"] not in {z["sid"] for z in got_pa}], hard=HARD)
                    if x:
                        got_pa.append(x)
                if got_pa:
                    dele += [r.target for r in ch.refs["clothing"] if G.get(r.target) == PA["slot"] and r.target not in {z["sid"] for z in got_pa}]
                    add = [r for r in add if G.get(r.target) != PA["slot"]]
                    for x in got_pa:
                        have.add(x["sid"]); add.append(Ref(x["sid"], 1, 100, 0))
                    s.report["ctx:power_armor_chars"] += 1
                    # остальные слоты сета — того же ордена (префикс имени), иначе любой силовой предмет своего происхождения
                    pref = got_pa[0]["name"].split(" - ")[0].strip().lower()
                    for g2 in sorted(SET_SLOTS - {PA["slot"]}):
                        pool2 = [y for y in cat if y["group"] == g2 and y["origin"] == org and re.search(pa_set_rx, y["name"], re.I)
                                 and y["sid"] not in LOCK and rok(y["sid"])]
                        same = [y for y in pool2 if y["name"].split(" - ")[0].strip().lower() == pref]
                        y = pick(rng, same or pool2, hard=HARD)
                        if y is None:
                            continue
                        dele += [r.target for r in ch.refs["clothing"] if G.get(r.target) == g2 and r.target != y["sid"]]
                        add = [r for r in add if G.get(r.target) != g2]
                        have.add(y["sid"]); add.append(Ref(y["sid"], 1, 100, 0))
                        s.report["ctx:power_armor_set_piece"] += 1
        WE = CX["lore_hard"]["wear"]
        if t0_items and not pa_char and ch.refs.get("clothing") and rng.random() < WE["factions"].get(fname, WE["poor_default"] if cls == "poor" else 0):
            x = pick(rng, [y for y in t0_items if y["group"] == WE["slot"] and y["sid"] not in have and rok(y["sid"])] or [], hard=HARD)
            if x:
                have.add(x["sid"]); add.append(Ref(x["sid"], 1, W["weight"], 0)); s.report["ctx:rusty_t0"] += 1
        if not is_wh:
            for cn, cl in CX["climate"].items():
                k = cl["factions"].get(fname, 0.0) or (0.8 if re.search(cl["name_rx"], cname, re.I) else 0.0)
                for g in cl["slots"]:
                    if k:
                        cx_add(g, cl["item_rx"], cl["chance"] * k, "climate_" + cn)
            for b in CX["bias"]:
                if re.search(b["name_rx"], cname, re.I):
                    for g in b["slots"]:
                        cx_add(g, b["item_rx"], b["chance"], "bias_" + b["id"])
            AC = CX["accessories"]
            ncls_ = ch.values.get("NPC class")
            armed = ncls_ in WR["classes"] and bool(ch.refs.get("weapons"))
            if not is_leader and CLONES:
                ownset = {y["sid"] for y in P["own"] + P["trade"]}
                deny_f = SX["deny_by_faction"].get(fname)
                for g, ar in AC.items():
                    if not g.startswith("armour:"):
                        continue
                    pa_ = ar["base"]
                    if armed:
                        pa_ = max(pa_, ar.get("armed", 0))
                    if ar.get("role_rx") and re.search(ar["role_rx"], cname, re.I):
                        pa_ = max(pa_, ar["role"])
                    for cn, v in ar.get("climate", {}).items():
                        k = CX["climate"][cn]["factions"].get(fname, 0.0) or (0.8 if re.search(CX["climate"][cn]["name_rx"], cname, re.I) else 0.0)
                        pa_ = max(pa_, v * k)
                    if ar.get("name_rx") and re.search(ar["name_rx"], cname, re.I):
                        pa_ = max(pa_, ar["name_p"])
                    if rng.random() >= min(AC["cap"], pa_):
                        continue
                    c_ = [x for x in CLONES if x["group"] == g and x["sid"] not in have and rok(x["sid"]) and use[UK(x)] < LIM(x)
                          and not (deny_f and re.search(deny_f, x["name"], re.I))
                          and (cls == "poor" or x["sid"] in ownset or not re.search(SX["savage_rx"], x["name"], re.I))]
                    sub = [x for x in c_ if x["sid"] in ownset]
                    if sub and rng.random() < SX["own_first"]:
                        c_ = sub
                    if not c_:
                        continue
                    w_ = [(1.0 / (1.0 + (use[UK(x)] / CAP) ** 2)) * min([SX["weight_rx"][k] for k in SX["weight_rx"] if re.search(k, x["name"], re.I)] or [1.0]) for x in c_]
                    x = rng.choices(c_, weights=w_)[0]
                    use[UK(x)] += 1
                    have.add(x["sid"]); add.append(Ref(x["sid"], 1, W["weight"], 0))
                    s.report["ctx:acc_" + g.split(":")[1]] += 1
                    s.report["slotx_recv:" + x["name"]] += 1
                    if sid in RACE_EXPLICIT:
                        for rr in races:
                            s.report["slotx_race:" + (M[rr].name if rr in M else rr)] += 1
                    else:
                        s.report["slotx_faction_mix:" + str(fname)] += 1
        if cls == "poor" and not savage and not pa_char and relic_pool and rules["bandit_relic"]["slot"] in groups_here:
            x = pick(rng, [y for y in relic_pool if rok(y["sid"])] or relic_pool)
            if x["sid"] not in have:
                add.append(Ref(x["sid"], 1, rules["bandit_relic"]["weight"], 0))
                s.report["bandit_relic_options"] += 1
        # SAVAGE_BARE (владелец 2026-11-13: «туманники - одичавший улей, пул хороший, но одежда на них слишком часто»):
        # в слотах, пустых в ваниле, добавляем родной вариант Kenshi «[нет вещи]» (val1 < 0) с весом, дающим долю голых bare_share.
        if savage and SV.get("bare_share") and not pa_char:
            wsum = collections.Counter()
            for r_ in add:
                gg = G.get(r_.target)
                if gg and gg not in groups_here and r_.v0 > 0:
                    wsum[gg] += r_.v1
            for gg, ws in wsum.items():
                bs = SV["bare_share"]
                wn = max(1, int(round(ws * bs / max(0.01, 1 - bs))))
                cnone = [x for x in by_group(P["own"] + P["trade"] + P["common"], gg, TIERS) if x["sid"] not in have and rok(x["sid"])]
                if cnone:
                    x = cnone[0]
                    have.add(x["sid"]); add.append(Ref(x["sid"], -1, wn, 0))
                    s.report["savage_bare_slots"] += 1
        if savage and not pa_char:   # шлем/металл в исходных данных диких (чужие моды) -> вес трофея; v0 < 0 = родное «[нет вещи]», не трогаем
            got_ = {r_.target for r_ in add}
            for r_ in ch.refs.get("clothing", []):
                if r_.v0 > 0 and r_.target in M and sav_ban(M[r_.target].name) and r_.target not in dele and r_.target not in got_:
                    add.append(Ref(r_.target, r_.v0, max(1, min(r_.v1, int(SV.get("weight", 40) * SV.get("trophy_share", 0.1)))), r_.v2))
                    s.report["savage_banned_to_trophy"] += 1
        refs, dels, vals = {}, {}, {}
        if add:
            refs["clothing"] = add
        if dele:
            dels["clothing"] = dele
        ncls = ch.values.get("NPC class")
        # оружие: несколько вариантов ближнего боя, часть — из соседних классов (мир свободно миксует снаряжение)
        if ncls in WR["classes"] and ch.refs.get("weapons"):
            wcats = {G.get(r.target) for r in ch.refs["weapons"]} - {None}
            have_w = {r.target for r in ch.refs["weapons"]}
            n_opt = WR["add_options"] + (1 if rng.random() < WR["third_option_chance"] else 0)
            got = []
            for _ in range(n_opt):
                cats = set(wcats) if (wcats and rng.random() >= WR["cross_class_chance"]) else set(WR["melee_cats"])
                cand = [x for x in P["trade"] + P["trophy"] + P["own"] + P["common"] + selfmade if x["type"] == "WEAPON" and x["group"] in cats
                        and x["group"] != "weapon:turret" and x["tier"] in tiers and x["sid"] not in have_w and rok(x["sid"])]
                x = pick(rng, list({c["sid"]: c for c in cand}.values()), hard=WR["hard_cap"], counter=use_w, cap=15)
                if x is None:
                    continue
                have_w.add(x["sid"])
                got.append(Ref(x["sid"], 1, 0, WR["chance"]))
                s.report["weapon_options"] += 1
            if got:
                refs["weapons"] = got
                stat["weapon_chars"] += 1
        # арбалеты/мушкетоподобное — только разрешённые правилом владельца (rules ranged); у владельцев арбалетов — варианты, у части бойцов — новый
        if not is_wh:
            XB = WR["crossbow"]
            has_xb = bool(ch.refs.get("crossbows"))
            if has_xb or (ncls in WR["classes"] and ch.refs.get("weapons") and rng.random() < XB["new_share"]):
                have_x = {r.target for r in ch.refs.get("crossbows", [])}
                gotx = []
                for _ in range(XB["owner_add_options"] if has_xb else 1):
                    cand = [x for x in cat if x["type"] == "CROSSBOW" and x.get("ranged") == "allow" and not x.get("firearm") and not is_exotic(x) and x["sid"] not in have_x
                            and x["sid"] not in LOCK and rok(x["sid"])]
                    x = pick(rng, cand, hard=XB["hard_cap"], counter=use_x, cap=30)
                    if x is None:
                        continue
                    have_x.add(x["sid"])
                    gotx.append(Ref(x["sid"], 1, 0, XB["chance"]))
                if gotx:
                    refs["crossbows"] = gotx
                    stat["crossbow_chars"] += 1
        # огнестрел (порох): редкость по технологичности фракции, один ствол; не WH, не HN
        FX = CX["firearms"]
        if not is_wh and fname not in CX["lore_hard"]["no_firearms"]:
            tech = FX["tech"].get(fname, FX["tech_default"])
            pf = tech * FX["base"] * (FX["leader_mult"] if is_leader else 1) * (FX["vet_mult"] if re.search(FX["vet_rx"], cname, re.I) else 1)                 * (FX["hunter_mult"] if re.search(FX["hunter_rx"], cname, re.I) else 1)
            if GG is not None:
                gm_ = char_gmult.get(sid, fac_gmult.get(fname, GEO_["unknown_mult"]))
                pf *= gm_
                stat["geo_chars"] += 1
                stat["geo_mult_sum_x1000"] += int(gm_ * 1000)
            if ncls in WR["classes"] and rng.random() < min(FX["cap"], pf):
                have_f = {r.target for r in ch.refs.get("crossbows", [])} | {r.target for r in refs.get("crossbows", [])}
                cf = [x for x in cat if x["type"] == "CROSSBOW" and x.get("ranged") == "allow" and x.get("firearm") and x["origin"] not in ("imperial", "chaos", "xenos")
                      and not is_exotic(x) and x["sid"] not in have_f and x["sid"] not in LOCK and rok(x["sid"])]
                x = pick(rng, cf, hard=WR["crossbow"]["hard_cap"], counter=use_x, cap=30)
                if x:
                    refs.setdefault("crossbows", []).append(Ref(x["sid"], 1, 0, FX["chance"]))
                    stat["firearm_chars"] += 1
                    s.report["firearm_fac:" + str(fname)] += 1
        # рюкзак: поле CHARACTER «backpack» (CONTAINER slot 12, ссылка предмет/1/шанс %/0); у кого уже есть свой — не трогаем
        stat["wh_chars"] += is_wh
        stat["has_own_backpack"] += bool(ch.refs.get("backpack"))
        if not is_wh and not ch.refs.get("backpack") and BP_OK:
            stat["bp_eligible"] += 1
            ch_p = BPR["chance_by_role"].get(str(ncls), 35)
            if re.search(BPR["name_boost_rx"], ch.name or "", re.I):
                ch_p = max(ch_p, BPR["name_chance"])
            wide_t = {"poor": ["T0", "T1"], "mid": ["T0", "T1", "T2"], "rich": TIERS}[cls]
            cand = [x for x in BP_OK if x["tier"] in wide_t and rok(x["sid"])] or [x for x in BP_OK if rok(x["sid"])]
            n_bp = BPR["options"]
            bps = []
            for _ in range(n_bp):
                x = pick(rng, [c for c in cand if c["sid"] not in {b.target for b in bps}], counter=use_b, cap=60)
                if x:
                    bps.append(Ref(x["sid"], 1, int(round(ch_p / n_bp)), 0))
            if bps:
                refs["backpack"] = bps
                stat["backpack_chars"] += 1
                stat["backpack_p_sum"] += ch_p
        # хлам и лут: поле CHARACTER «inventory» (ITEM, количество 1, шанс %, 0) — по ярусу богатства
        # пустые карманы (B4 Н10/И9): голодные бандиты — без еды, роскоши и денег; только дешёвый хлам, своя еда/деньги шаблона снимаются
        EP = LT.get("empty_pockets") or {}
        starving = bool(EP.get("enabled")) and (bool(re.search(EP["faction_rx"], fname or "")) or bool(re.search(EP["name_rx"], cname, re.I)))
        if starving:
            ep_rx = re.compile(EP["strip_rx"], re.I)
            strip = [r.target for r in ch.refs.get("inventory", []) if r.target in M and ep_rx.search(M[r.target].name or "")]
            if strip:
                dels["inventory"] = strip
                s.report["empty_pockets_stripped"] += len(strip)
            s.report["empty_pockets_chars"] += 1
        if not is_wh and LOOT and rng.random() < LT["share"]:
            kw = EP["kinds"] if starving else LT["kinds_by_wealth"][cls]
            vcap = EP["value_cap"] if starving else LT["value_cap"][cls]
            have_i = {r.target for r in ch.refs.get("inventory", [])}
            gl = []
            for _ in range(rng.randint(*(EP["items"] if starving else LT["items"]))):
                kind = rng.choices(list(kw), weights=list(kw.values()))[0]
                cand = [x for x in LOOT if x["kind"] == kind and x["value"] <= vcap and x["sid"] not in have_i]
                x = pick(rng, cand, counter=use_l, cap=LT["cap_soft"]) if cand else None
                if x:
                    have_i.add(x["sid"])
                    gl.append(Ref(x["sid"], 1, LT["item_chance"], 0))
            if PB.get("enabled") and not starving:
                bkey, bset = belong_set(fname)
                if bset:
                    bl = []
                    for it in sorted(bset, key=lambda it_: -rng.random() ** (1.0 / max(1, it_["chance"]))):   # взвешенно по шансу: хлеб чаще письма
                        if len(bl) >= PB["max"]:
                            break
                        if it["sid"] not in have_i:
                            have_i.add(it["sid"])
                            bl.append(Ref(it["sid"], 1, int(it["chance"]), 0))
                    if bl:
                        gl = bl + gl[:max(0, LT["items"][1] - len(bl))]
                        stat["belong_chars"] += 1
                        stat["belong_items"] += len(bl)
                        s.report["belong:" + str(bkey)] += 1
            if gl:
                refs["inventory"] = gl
                stat["loot_chars"] += 1
                stat["loot_items"] += len(gl)
        # качество: шанс улучшения брони и производитель оружия своего тира
        if int(ch.values.get("armour upgrade chance", 5) or 0) < W["upgrade_chance"]:
            vals["armour upgrade chance"] = W["upgrade_chance"]
        wt_ = lead_t if is_leader else base_t
        if st_i is not None:
            wi_ = TIERS.index(wt_)
            wt_ = TIERS[max(min(wi_, st_i + 1), min(st_i, wi_ + 1))]
        wl = ctx.find(*qlev[wt_]["weapon level"])
        if ch.refs.get("weapon level") and wl.sid not in {r.target for r in ch.refs["weapon level"]}:
            refs["weapon level"] = [Ref(wl.sid, 30, 0, 0)]
        # форма/дикари: исходные вещи не своего стиля (их вписали чужие моды брони) — в слоте почти не выпадают (IDENTITY)
        unfit = set()
        if is_uniform and IDN.get("enabled"):
            for r in ch.refs.get("clothing", []):
                x_ = XCAT.get(r.target)
                if x_ and x_["group"] in slots and not sav_ok(x_):
                    unfit.add(r.target)
        if refs or dels or vals or unfit:
            pending.append({"sid": sid, "fac": fname, "vals": vals, "refs": refs, "dels": dels, "unfit": unfit, "setg": set(spk)})
            n_chars += 1
            if sid in fb:
                stat["fallback_chars"] += 1
    for k, v in stat.items():
        s.report["stat:" + k] = v
    s.report["characters"] = n_chars
    s.report["race_restricted_given_explicit"] = restricted_given["explicit"]
    s.report["race_restricted_given_faction_mix"] = restricted_given["faction_mix"]

    # --- уникальные персонажи: реликтовые сеты по лору (rules unique_relics / relic_tier, BALANCE 2026-11-13) --------------------
    UR = rules.get("unique_relics") or {}
    uq_rows, uq_skipped = [], []
    if UR.get("enabled"):
        RTS = {x["id"]: x for x in rules["relic_tier"]["sets"]}
        used_r = set()
        skip_nm = re.compile(UR["skip_name_rx"], re.I)
        by_name = [(re.compile(a, re.I), b.split("|")) for a, b in UR["by_name"]]
        skip_f = set(UR["skip_factions"])
        cands = []
        for ch in M.values():
            if ch.type_name != "CHARACTER" or not ch.values.get("unique") or not ctx.in_game(ch.sid) or ch.values.get("slave", 0) or ch.values.get("NPC class") == 6:
                continue
            cs_ = int(ch.values.get("combat stats", 0) or 0)
            bty = int(ch.values.get("bounty amount", 0) or 0)
            imp = float(ch.values.get("faction importance", 0) or 0)
            vanilla_u = van_unique.get(ch.sid) is True
            if not vanilla_u and not (cs_ >= UR["mod_min_cs"] and (bty >= UR["mod_min_bounty"] or imp >= UR["mod_min_imp"])):
                continue
            if skip_nm.search(ch.name or "") or SKIP_NAME.search(ch.name or ""):
                s.report["unique_skip:name"] += 1
                continue
            rn = " ".join(M[r.target].name for r in ch.refs.get("race", []) if r.target in M)
            if SKIP_RACE.search(rn):
                s.report["unique_skip:race"] += 1
                continue
            fn = char_fac.get(ch.sid)
            if fn is None:
                fr_ = ch.refs.get("faction", [])
                fn = M[fr_[0].target].name if fr_ and fr_[0].target in M else None
            if fn in skip_f or fn in SVF:
                s.report["unique_skip:faction_lore"] += 1
                continue
            lead = ch.sid in leaders
            score = lead * 20 + imp * 0.5 + bty / 2000 + cs_ * 0.3
            cands.append((score, ch, fn, lead, cs_, bty, imp))
        cands.sort(key=lambda x: (-x[0], x[1].sid))
        nset = nacc = 0
        for score, ch, fn, lead, cs_, bty, imp in cands:
            st_ = sum(cs_ >= b_ for b_ in rules["stat_tiers"]["bounds"])
            lvl = None
            if (lead or imp >= UR["set_imp"] or bty >= UR["set_bounty"]) and cs_ >= UR["set_min_cs"] and nset < UR["max_sets"]:
                lvl = "set"
            elif cs_ >= UR["accent_min_cs"] and (lead or bty >= UR["accent_bounty"] or imp >= UR["accent_imp"]) and nacc < UR["max_accents"]:
                lvl = "accent"
            if lvl is None:
                s.report["unique_skip:weak_or_minor"] += 1; uq_skipped.append([ch.name, fn, "weak_or_minor", cs_])
                continue
            styles = next((ids for rx_, ids in by_name if rx_.search(ch.name or "")), None) or UR["by_faction"].get(fn) or (UR.get("default_styles") if cs_ >= UR.get("default_min_cs", 999) else None)
            if not styles:
                s.report["unique_skip:no_style"] += 1; uq_skipped.append([ch.name, fn, "no_style", cs_])
                continue
            races = race_set(ch, fn)
            explicit_ = ch.sid in RACE_EXPLICIT
            got, got1 = [], []
            for sid_set in styles:
                if lvl == "set" or True:
                    pieces = []
                    for g, rx_ in RTS[sid_set]["slots"].items():
                        cc = [x for x in cat if x["group"] == g and x["sid"] not in used_r and x["sid"] not in LOCK and re.search(rx_, x["name"])
                              and TIERS.index(x["tier"]) <= st_ + 1 and race_ok(x["sid"], races, explicit_)]
                        if cc:
                            cc.sort(key=lambda x: (sum(x["worn_by"].values()), -x["stat_score"]))
                            pieces.append(cc[0])
                    if lvl == "accent" and pieces:
                        pieces = [next((p_ for p_ in pieces if p_["group"] == "armour:hat"), None) or next((p_ for p_ in pieces if p_["group"] == "armour:body"), pieces[0])]
                    if pieces and (lvl == "accent" or len(pieces) >= 2):
                        got = pieces
                        break
                    if pieces and not got1:
                        got1 = pieces   # сет не собрался (вещи розданы) — запасной вариант: одна вещь
            if not got and got1:
                got = [next((p_ for p_ in got1 if p_["group"] == "armour:hat"), None) or next((p_ for p_ in got1 if p_["group"] == "armour:body"), got1[0])]
                lvl = "accent"
            if not got:
                s.report["unique_skip:no_items"] += 1; uq_skipped.append([ch.name, fn, "no_items", cs_])
                continue
            adds, dels_ = [], []
            for p_ in got:
                used_r.add(p_["sid"])
                dels_ += [r.target for r in ch.refs.get("clothing", []) if G.get(r.target) == p_["group"] and r.target != p_["sid"]]
                adds.append(Ref(p_["sid"], 1, 100, 0))
            pending.append({"sid": ch.sid, "fac": fn, "vals": {}, "refs": {"clothing": adds}, "dels": {"clothing": dels_}, "unique": True})
            if lvl == "set":
                nset += 1
            else:
                nacc += 1
            s.report["unique_relic_chars"] += 1
            s.report["unique_relic_" + lvl] += 1
            s.report["unique_relic_items"] += len(got)
            uq_rows.append({"name": ch.name, "faction": fn, "level": lvl, "score": round(score, 1), "combat": cs_, "stat_tier": "T%d" % st_, "set": styles[0] if len(styles) == 1 else [x for x in styles if all(g in RTS[x]["slots"] for g in {p_["group"] for p_ in got})][:1],
                            "items": [p_["name"] for p_ in got]})
        s.report["unique_candidates"] = len(cands)
        json.dump({"_doc": "WARDROBE unique_relics: что получили уникальные (генерируется сборкой)", "count": len(uq_rows), "rows": uq_rows, "left_unchanged": uq_skipped},
                  open(r"C:\KenshiModMap\data\unique_relics.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # --- торговцы: те же пулы ---------------------------------------------------------------------
    vrule = rules["vendors"]
    done = set()
    for sq in ctx.all("SQUAD_TEMPLATE"):
        if not sq.values.get("is trader") or not sq.refs.get("faction") or sq.refs["faction"][0].target not in M:
            continue
        fn = M[sq.refs["faction"][0].target].name
        if fn not in facs:
            continue
        P = pools(fn)
        CUR_FAC[0] = fn
        cls, base_t, lead_t = wealth(fn)
        tiers = TIERS[:TIERS.index(lead_t) + 1]
        for vr in sq.refs.get("vendors", []):
            vl = M.get(vr.target)
            if vl is None or vl.sid in done or not vl.refs.get("clothing") or not ctx.in_game(vl.sid):
                continue
            done.add(vl.sid)
            rng = random.Random(rules["seed"] + zlib.crc32(vl.sid.encode()))
            have = {r.target for r in vl.refs["clothing"]}
            cand = [x for x in {y["sid"]: y for y in P["own"] + P["trade"] + P["common"]}.values()
                    if x["type"] == "ARMOUR" and x["group"] in slots and x["tier"] in tiers and x["sid"] not in have and x["sid"] not in LOCK]
            chosen = []
            gcount = collections.Counter(BK[r.target] for r in vl.refs["clothing"] if r.target in BK)   # лавка: ≤ vendor_group_max цветов группы (клоны — 1)
            for _ in range(min(vrule["clothing_items"], len(cand))):
                rest = [c for c in cand if c not in chosen and gcount[BK.get(c["sid"], "")] < (DP.get("vendor_family_max", 2) if BK.get(c["sid"], "").startswith("df:") else 1)
                        or c["sid"] not in BK and c not in chosen]
                x = pick(rng, rest, hard=rules["vendor_hard_cap"], boost_cloak=True) if rest else None
                if x is None:
                    break
                chosen.append(x)
                if x["sid"] in BK:
                    gcount[BK[x["sid"]]] += 1
            if chosen:
                pending_v.append({"sid": vl.sid, "fac": fn, "refs": {"clothing": [Ref(x["sid"], vrule["weight"], 0, 0) for x in chosen]}})
                s.report["vendor_lists"] += 1

    # --- бюджет происхождения (rules/budget.json): экзотика ≤ share_max всех выдач, в основном у своих фракций ---------
    bud = json.load(open(r"C:/KenshiModMap/rules/budget.json", encoding="utf-8"))
    XC = {x["sid"]: x for x in cat}
    exotic = lambda sid: sid in XC and is_exotic(XC[sid])  # noqa: E731
    wh_names = {n for v in whmap.values() for n in v}
    slots_all = []   # (запись, категория, ref, своя ли фракция, снимаемо ли)
    for rec in pending + pending_v:
        for c in ("clothing", "weapons"):
            for r in rec["refs"].get(c, []):
                if c == "clothing" and r.v1 == rules["bandit_relic"]["weight"]:
                    continue   # реликт бандитов: вес 1 против 15000 (~1:45000) — в бюджет выдач не входит, его доля ничтожна
                slots_all.append((rec, c, r, rec["fac"] in wh_names, r.v1 != 100))
    total = len(slots_all)
    ex = [x for x in slots_all if exotic(x[2].target)]
    cap = int(bud["share_max"] * total)
    rng_b = random.Random(rules["seed"])
    order = sorted([x for x in ex if not x[3] and x[4]], key=lambda _: rng_b.random()) + sorted([x for x in ex if x[3] and x[4]], key=lambda _: rng_b.random())
    removed = 0
    while len(ex) - removed > bud["share_max"] * (total - removed) and order:   # доля считается от выдач после подрезки
        rec, c, r, _, _ = order.pop(0)
        rec["refs"][c].remove(r)
        removed += 1
    ex_after = [x for x in slots_all if exotic(x[2].target) and x[2] in x[0]["refs"].get(x[1], [])]
    tot_after = total - removed
    s.report["exotic_share"] = round(len(ex_after) / max(1, tot_after), 4)
    s.report["exotic_own_share"] = round(sum(1 for x in ex_after if x[3]) / max(1, len(ex_after)), 3)
    s.report["exotic_removed_for_budget"] = removed
    s.report["placements"] = tot_after
    # --- WARD_SHARE A: ванильные ссылки clothing слота, где персонаж получил ≥ min_mods наших вариантов, перезаписываем (тот же target,
    # v1 меньше) — в Kenshi v1 = вес внутри слота. Не удаляем, вес не повышаем; суммарный вес ванили ≤ (1-share)/share от веса наших.
    RW = rules.get("vanilla_reweight", {})
    relic_w = rules["bandit_relic"]["weight"]

    # DISGUISE (2026-11-14): ванильная маскировка — одежда NPC с «wears uniform» клеймится как форма фракции. Ваниль ставит клеймо
    # большинству военных/стражи UC, HN, работорговцев, ниндзя; модовые персонажи тех же фракций его часто не получили — их броня
    # для маскировки бесполезна. Правило: (фракция, класс NPC), где у ванильных персонажей клеймо у большинства (а без ванильных —
    # у большинства модовых), — клеймо всем модовым персонажам этой пары. У клеймёных родной комплект плотнее (share_uniform).
    DG = rules.get("disguise") or {}
    uni = set()
    if DG.get("enabled"):
        van_n = {n for n, _, _ in ctx.van}
        grp_ = collections.defaultdict(lambda: [0, 0, 0, 0, []])   # van n, van uni, mod n, mod uni, mod sids
        for csid, cfn in char_fac.items():
            ch_ = M.get(csid)
            if ch_ is None or ch_.type_name != "CHARACTER" or not ctx.in_game(csid) or ch_.values.get("slave", 0):
                continue
            cls_ = ch_.values.get("NPC class")
            if cls_ in DG.get("skip_classes", []):
                continue
            a_ = grp_[(cfn, cls_)]
            u_ = bool(ch_.values.get("wears uniform"))
            if ctx.origin.get(csid) in van_n:
                a_[0] += 1; a_[1] += u_
            else:
                a_[2] += 1; a_[3] += u_
                if not u_ and not ch_.values.get("unique"):
                    a_[4].append(csid)
                if u_:
                    uni.add(csid)
            if u_:
                uni.add(csid)
        new_uni = set()
        for (cfn, cls_), a_ in grp_.items():
            ok_ = (a_[0] and a_[1] / a_[0] >= DG["min_share"]) or (not a_[0] and a_[2] >= 2 and a_[3] / a_[2] >= DG["min_share"])
            if ok_ and a_[4]:
                new_uni.update(a_[4])
                s.report["disguise_groups"] += 1
        uni |= new_uni
        s.report["disguise_new_uniform_chars"] = len(new_uni)
        seen_ = set()
        for rec in pending:
            seen_.add(rec["sid"])
            if rec["sid"] in new_uni:
                rec["vals"]["wears uniform"] = True
        for csid in sorted(new_uni - seen_):
            pending.append({"sid": csid, "fac": char_fac[csid], "vals": {"wears uniform": True}, "refs": {}, "dels": {}, "unfit": set()})

    def is_sig(sid_, fn_):   # опознавательная вещь фракции: её культуры или носят немногие, и она среди них
        x = XCAT.get(sid_)
        if not x or not fn_:
            return False
        return x["origin"] == "culture:" + fn_ or (fn_ in x["worn_by"] and len(x["worn_by"]) <= IDN.get("sig_max_wearers", 6))
    if RW.get("enabled") or IDN.get("enabled"):
        van_names_ = {n for n, _, _ in ctx.van}
        is_van = lambda sid_: ctx.origin.get(sid_) in van_names_  # noqa: E731
        G_all = {x["sid"]: x["group"] for x in json.load(open(rules["catalog"], encoding="utf-8"))["items"]}   # группа и у вещей, отсеянных из cat (не латиница и т.п.)
        for rec in pending:
            chs = M[rec["sid"]]
            add_ = rec["refs"].get("clothing", [])
            gone = set(rec["dels"].get("clothing", []))
            taken = {r.target for r in add_}
            out = []
            for g in slots:
                grp = lambda t_: G.get(t_) or G_all.get(t_)  # noqa: E731
                mods_ = [r for r in add_ if grp(r.target) == g and r.v1 != relic_w and r.v1 != 100 and not is_van(r.target)]   # 100 = опознавательные элиты/силовая броня
                van_old = [r for r in chs.refs.get("clothing", []) if grp(r.target) == g and r.target not in gone and r.target not in taken]
                van_new = [r for r in add_ if grp(r.target) == g and r.v1 != relic_w and r.v1 != 100 and is_van(r.target)]   # ванильные вещи, выбранные в пул
                neww = {}   # target -> новый вес исходной ссылки
                if RW.get("enabled") and len(mods_) >= RW["min_mods"] and (van_old or van_new):
                    nv = len(van_old) + len(van_new)
                    cap_tot = sum(r.v1 for r in mods_) * (1 - RW["mod_share"]) / RW["mod_share"]
                    per = max(1, min(RW["vanilla_weight"], int(cap_tot / nv)))
                    for r in van_old:
                        if r.v1 > per and not (IDN.get("enabled") and is_sig(r.target, rec["fac"])):   # родную фракционную вещь не занижаем
                            neww[r.target] = per
                    for r in van_new:
                        if r.v1 > per:
                            add_[add_.index(r)] = Ref(r.target, r.v0, per, r.v2)
                            s.report["vanilla_picks_reweighted"] += 1
                # IDENTITY (2026-11-14): исходные вещи персонажа (их выбрал автор) держат долю веса в слоте:
                # share_sig, если среди них есть опознавательная вещь фракции, иначе share_gen. Только повышение.
                unfit_ = rec.get("unfit") or set()
                for r in van_old:
                    if r.target in unfit_:
                        neww[r.target] = 1
                        s.report["identity_unfit_refs"] += 1
                    elif IC and not is_van(r.target) and not is_sig(r.target, rec["fac"]) and XCAT.get(r.target)                             and not pal_ok(XCAT[r.target], rec["fac"]):   # чужая яркая перекраска, вписанная модом брони
                        unfit_ = unfit_ | {r.target}
                        neww[r.target] = 1
                        s.report["palette_damped_refs"] += 1
                prot = [r for r in van_old if r.target not in unfit_ and (is_sig(r.target, rec["fac"]) or is_van(r.target))]   # защищаем опознавательное и базовое ванильное
                if IDN.get("enabled") and prot and g not in rec.get("setg", ()):   # слот комплекта: родное не поднимаем
                    add_w = sum(r.v1 for r in add_ if grp(r.target) == g and r.v1 != relic_w and r.v1 != 100)
                    add_w += sum(neww.get(r.target, r.v1) for r in van_old if r not in prot and r.target not in unfit_)   # чужие вписанные модами — в счёт «добавок»
                    cur = {r.target: neww.get(r.target, r.v1) for r in prot}
                    o_w = sum(max(1, v) for v in cur.values())
                    sig = any(is_sig(r.target, rec["fac"]) for r in prot)
                    S_ = IDN["share_sig"] if sig else IDN["share_gen"]
                    if sig and rec["sid"] in uni:
                        S_ = max(S_, DG.get("share_uniform", S_))   # клеймёная форма: родной комплект почти всегда
                    need = S_ / (1 - S_) * add_w
                    if add_w and o_w < need:
                        k_ = need / o_w
                        for t_, v in cur.items():
                            neww[t_] = int(math_ceil(max(1, v) * k_))
                        s.report["identity_raised_slots" + (":sig" if sig else ":gen")] += 1
                for r in van_old:
                    if r.target in neww and neww[r.target] != r.v1:
                        out.append(Ref(r.target, r.v0, neww[r.target], r.v2))
            if out:
                rec["rew"] = out
                s.report["vanilla_reweighted_refs"] += len(out)
                s.report["vanilla_reweighted_chars"] += 1
    for rec in pending:
        refs = {k: v for k, v in rec["refs"].items() if v}
        if rec.get("rew"):
            refs["clothing"] = refs.get("clothing", []) + rec["rew"]
        if refs or rec["dels"] or rec["vals"]:
            s.change(rec["sid"], values=rec["vals"], set_refs=refs, del_refs=rec["dels"])
    for rec in pending_v:
        if rec["refs"]["clothing"]:
            s.add_refs(rec["sid"], "clothing", rec["refs"]["clothing"])
    for vsid, vref in vendor_clone:   # SLOTS: клоны в тех же лавках, что исходники
        s.add_refs(vsid, "clothing", [vref])

    # --- статистика повторов по итоговым выдачам (после подрезки бюджетом)
    fin, fin_w, fin_bp, fin_loot, fin_xb = (collections.Counter() for _ in range(5))
    for rec in pending + pending_v:
        for r in rec["refs"].get("clothing", []):
            if r.v1 != rules["bandit_relic"]["weight"]:
                fin[r.target] += 1
        for r in rec["refs"].get("weapons", []):
            fin_w[r.target] += 1
        for r in rec["refs"].get("crossbows", []):
            fin_xb[r.target] += 1
        for r in rec["refs"].get("backpack", []):
            fin_bp[r.target] += 1
        for r in rec["refs"].get("inventory", []):
            fin_loot[r.target] += 1
    nm = {x["sid"]: (x["name"], x["group"]) for x in cat}
    cl = sorted(fin.values())
    bkey = lambda k: BK.get(k, k)  # noqa: E731
    fin_g = collections.Counter()
    for k, v in fin.items():
        fin_g[bkey(k)] += v
    nm_g = lambda k: (nm[k][0] if k in nm else (nm[k[3:]][0] if k[3:] in nm else k)) if True else k  # noqa: E731
    ACPM = "Animation - Collection Pack"
    xmod = {x["sid"]: x.get("mod", "") for x in cat}
    acp_n = sum(v for k, v in fin.items() if ACPM in xmod.get(k, "") or k.endswith("-" + ACPM + ".mod"))
    n_ch = max(1, len(pending))
    has = lambda c: sum(1 for rec in pending if rec["refs"].get(c))  # noqa: E731
    cloaks = {k: v for k, v in fin.items() if k in nm and CLOAK.search(nm[k][0]) and nm[k][1] in ("armour:shirt", "armour:body")}
    stats_out = {"top10": [[nm.get(k, (k, "?"))[0], nm.get(k, (k, "?"))[1], v] for k, v in fin.most_common(10)],
                 "max": cl[-1] if cl else 0, "median": cl[len(cl) // 2] if cl else 0, "distinct": len(fin), "placements": sum(fin.values()),
                 "characters": len(pending), "characters_fallback": stat["fallback_chars"], "vendor_lists": len(pending_v),
                 "share_with_backpack": round(has("backpack") / n_ch, 3), "backpack_expected_share": round(stat["backpack_p_sum"] / 100 / n_ch, 3),
                 "backpack_distinct": len(fin_bp), "backpack_max": max(fin_bp.values(), default=0),
                 "share_with_extra_weapon": round(has("weapons") / n_ch, 3), "weapon_distinct": len(fin_w), "weapon_max": max(fin_w.values(), default=0),
                 "share_with_crossbow_options": round(has("crossbows") / n_ch, 3), "crossbow_distinct": len(fin_xb), "crossbow_max": max(fin_xb.values(), default=0),
                 "share_with_loot": round(has("inventory") / n_ch, 3), "loot_distinct": len(fin_loot), "loot_max": max(fin_loot.values(), default=0),
                 "cloaks_distinct": len(cloaks), "cloaks_max": max(cloaks.values(), default=0),
                 "gorillo_pelt_total": sum(v for k, v in fin.items() if k in nm and "gorillo pelt" in nm[k][0].lower()),
                 "slots_filled_empty": stat["slot_filled"],
                 "distinct_groups": len(fin_g), "acp_share": round(acp_n / max(1, sum(fin.values())), 4),
                 "top10_groups": [[nm_g(k), v] for k, v in fin_g.most_common(10)], "dedup_enabled": bool(BK),
                 "dedup_group_max": max((v for k, v in fin_g.items() if k in set(BK.values())), default=0)}
    json.dump(stats_out, open(r"C:\KenshiModMap\data\wardrobe_repeat_stats.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    for k in ("max", "distinct", "share_with_backpack", "share_with_extra_weapon", "share_with_loot", "cloaks_max"):
        s.report["rs:" + k] = stats_out[k]

    # --- тиры наперёд (данные для будущего дирижёра: переключение по богатству) ------------------------
    for fn in facs:
        P = pools(fn)
        if not P["own"]:
            continue
        pa_fac = fn in CX["lore_hard"]["power_armor"]["factions"] or (PA_FAC_ALL[fn] and PA_FAC_N[fn] * 3 >= PA_FAC_ALL[fn])
        set_sl = set(CX["lore_hard"]["power_armor"].get("set_slots", ["armour:hat", "armour:body", "armour:legs", "armour:boots"]))
        if pa_fac:
            s.report["tiers_pa_factions"] += 1   # дирижёр (try_gear) не меняет им шлем/тело/ноги/сапоги — сет остаётся целым
        # 2026-11-13: паладины в силовой броне — try_gear дирижёра брал вещи отсюда, а тут была WH-экзотика (сотни шлемов
        # Империума у Святой Нации). Экзотика — только WH-фракциям; у фракций с замком культуры (дикие/форма) — только их стиль.
        LK = None
        for U in [CX["lore_hard"].get("savage") or {}] + CX["lore_hard"].get("uniforms", []):
            if fn in U.get("factions", []):
                LK = U
        def tier_ok(x):
            if x["sid"] in LOCK or (is_exotic(x) and fn not in WH_NAMES):
                s.report["tiers_exotic_blocked"] += 1
                return False
            if LK is not None:
                if re.search(LK.get("exclude_rx", "^$"), x["name"], re.I):
                    return False
                return bool(re.search(LK["name_rx"], x["name"], re.I)) or fn in x.get("worn_by", {})
            return True
        tiers_data[fn] = {t: {g: [x["sid"] for x in by_group(P["own"] + P["trade"], g, [t]) if tier_ok(x)][:40]
                              for g in slots if not (pa_fac and g in set_sl)} for t in TIERS}
    json.dump({"_doc": "WARDROBE: пулы фракций по тирам (своё+торговля), для будущего переключения дирижёром по богатству", "factions": tiers_data},
              open(r"C:\KenshiModMap\data\wardrobe_tiers.json", "w", encoding="utf-8"), ensure_ascii=False)
    s.report["factions_with_tiers"] = len(tiers_data)
