"""Тест потока BUILD (tools/streams/build.py, rules/streams/build.json, docs/BUILD_TREE.md).

Проверяет итог (не порядок сортировки, всё на множествах):
  1. 0 дубликатов в меню игрока: точных клонов (clone_sig) видно не больше одного; почти-дубли (fold_key) сведены
     в один пункт, кроме пар, закреплённых раскладкой модов Buildings Category Tweaks (считаются отдельно);
  2. 0 построек раньше предпосылок: level исследования ≥ level предпосылок; потребитель энергии не раньше генератора;
     улучшение не раньше базы; реликтовые модовые технологии за Relic Studies; is level upgrade только ванильный;
     ручная/примитивная плавка не позже автоматики (граница с рудой);
  3. 0 тупиков: доступное, но недостижимое исследование; достижимое без содержимого и не предпосылка;
  4. города, лагеря, шаблоны NPC: ни одна постройка не пропала, её поля (кроме building category/group) и входящие
     ссылки не из RESEARCH не изменились.
Режимы:
  python -I -X utf8 tools/streams/test_build_menu.py          # заглушки (быстро, без данных)
  python -I -X utf8 tools/streams/test_build_menu.py --full   # слитый контекст + потоки tech и build в памяти (~1 мин),
      любая запись файла запрещена; плюс прогон build на перемешанном порядке записей — результат тот же.
check_all() можно звать из офлайн-обвязки после полного прогона потоков."""
import collections
import json
import os
import random
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
import build as B_  # noqa: E402
from kmod import Item, Ref, type_code  # noqa: E402

RULES = json.load(open(os.path.join(ROOT, "rules", "streams", "build.json"), encoding="utf-8"))
UI = set(B_.UI_FIELDS)


# --------------------------------------------------------------------------------------------- проверки итога
def snapshot(M):
    """Снимок построек и входящих ссылок (до потока build) для проверки 4."""
    bl = {sid: (it.name, {k: str(v) for k, v in it.values.items() if k not in UI},
                {k: sorted((r.target, r.v0, r.v1, r.v2) for r in v) for k, v in it.refs.items()})
          for sid, it in M.items() if it.type_name == "BUILDING"}
    inb = collections.Counter()
    for sid, it in M.items():
        if it.type_name == "RESEARCH":
            continue
        for cat, rs in it.refs.items():
            for r in rs:
                if r.target in bl:
                    inb[(sid, cat, r.target)] += 1
        for ins in it.instances:
            if ins.target in bl:
                inb[(sid, "instance", ins.target)] += 1
    return bl, inb


def check_all(M, origin, layers, rules=RULES, in_game=lambda s: True, base=None):
    out = collections.defaultdict(list)
    R, start, bp = B_.research_state(M, rules, in_game)
    req = {r: [x.target for x in it.refs.get("requirements", []) if x.target in R] for r, it in R.items()}
    bpo = {r: it.values.get("blueprint only") is True for r, it in R.items()}
    reach = B_.reachable(R, start, bp, lambda k: bpo[k], lambda k: req[k])
    Bs = {sid: it for sid, it in M.items() if it.type_name == "BUILDING" and in_game(sid)}
    menu = collections.defaultdict(set)
    for r in reach:
        for x in R[r].refs.get("enable buildings", []):
            if x.target in Bs:
                menu[x.target].add(r)
    lvl = {r: int(R[r].values.get("level", 1)) for r in R}

    def avail(b):
        return min((0 if r in start else lvl[r]) for r in menu[b])

    # 1. дубликаты
    up = {u.target for b in menu for u in Bs[b].refs.get("upgrades to", [])}
    cl = collections.defaultdict(list)
    for b in menu:
        cl[B_.clone_sig(M, Bs[b], rules)].append(b)
    for k, bs in cl.items():
        if len([b for b in bs if b not in up]) > 1:
            out["dup_clone"].append(sorted(bs))
    locked = B_.layout_writers(layers, rules["layout_mods_rx"])
    lc = lambda b: locked.get(b, {}).get("building category", False)   # noqa: E731
    lg = lambda b: locked.get(b, {}).get("building group", False)      # noqa: E731
    cat = lambda b: Bs[b].values.get("building category", "misc")       # noqa: E731
    grp = lambda b: Bs[b].values.get("building group") or ""            # noqa: E731
    ent = lambda b: (cat(b), grp(b) or "#" + b)                          # noqa: E731
    skip = set(rules["fold"]["skip_categories"])
    fc = collections.defaultdict(list)
    for b in menu:
        if cat(b) not in skip:
            k = B_.fold_key(M, Bs[b], rules)
            if k is not None:
                fc[k].append(b)
    for k, bs in fc.items():
        if len({ent(b) for b in bs}) < 2:
            continue
        lcs = {cat(b) for b in bs if lc(b)}
        if len(lcs) > 1:
            out["layout_exception"].append(sorted(bs)[:3])
        for b in bs:                                   # V2: свободная категория — среди закреплённых или общая
            if not lc(b) and ((lcs and cat(b) not in lcs) or (not lcs and len({cat(x) for x in bs}) > 1)):
                out["dup_fold_category"].append(b)
        for c in {cat(b) for b in bs}:                 # V1/V3: внутри категории свободные группы — одна (или закреплённая)
            mem = [b for b in bs if cat(b) == c]
            lgs = {grp(b) for b in mem if lg(b) and grp(b)}
            free = {ent(b) for b in mem if not lg(b)}
            if len(free) > 1 or (lgs and any(e[1] not in lgs for e in free)):
                out["dup_fold_group"].append(sorted(mem)[:4])

    # 2. предпосылки
    for r in reach:
        for q in req[r]:
            if lvl[r] < lvl[q]:
                out["level_below_requirement"].append((r, q))
    van = set(rules["vanilla_files"])
    for r, it in R.items():
        if it.values.get("is level upgrade") is True and origin.get(r) not in van:
            out["mod_level_upgrade"].append(r)
    if rules["prereq"].get("power"):
        gens = [avail(b) for b in menu if (Bs[b].values.get("power output") or 0) > 0]
        gl = min(gens) if gens else 99
        for b in menu:
            if (Bs[b].values.get("power output") or 0) < 0 and avail(b) < gl:
                out["power_before_generator"].append(b)
    if rules["prereq"].get("upgrades"):
        for a in menu:
            for u in Bs[a].refs.get("upgrades to", []):
                if u.target in menu and avail(u.target) < avail(a):
                    out["upgrade_before_base"].append((a, u.target))
    RL = rules["relic"]
    anchor = next((r for r, it in R.items() if it.name == RL["anchor"][1] and origin.get(r) == RL["anchor"][2]), None)
    if anchor is None:
        out["relic_anchor_missing"].append(RL["anchor"][1])
    else:
        rx = re.compile(RL["category_rx"])

        def needs(r, seen=()):
            return r == anchor or any(needs(q, seen + (r,)) for q in req[r] if q not in seen)
        for r, it in R.items():
            if origin.get(r) != RL["anchor"][2] and (origin.get(r) in set(RL["mods"]) or rx.search(str(it.values.get("category", "")))):
                if lvl[r] < RL["level"] or not needs(r):
                    out["relic_not_behind_studies"].append(r)
    OB = rules["ore_boundary"]
    man = [avail(b) for b in OB["manual_smelt"] if b in menu]
    auto = [avail(b) for b in OB["powered_smelt"] + OB["drills"] if b in menu]
    if not man:
        out["ore_no_manual_smelt"].append("manual")
    elif auto and min(man) > min(auto):
        out["ore_manual_after_auto"].append((min(man), min(auto)))

    # 3. тупики
    required = {q for r in reach for q in req[r]}
    for r, it in R.items():
        if r not in reach and not bpo[r] and r not in start:
            out["dead_unreachable"].append(r)
        if r in reach and r not in start and r not in required and it.values.get("is level upgrade") is not True:
            if not B_.has_content(it, {x.target for x in it.refs.get("enable buildings", []) if x.target in Bs}) and r not in bp:
                out["dead_empty"].append(r)

    # 4. города и шаблоны NPC
    if base is not None:
        bl, inb = base
        now_bl, now_inb = snapshot(M)
        for sid, v in bl.items():
            if sid not in now_bl:
                out["building_lost"].append(sid)
            elif now_bl[sid] != v:
                out["building_changed"].append(sid)
        if now_inb != inb:
            out["inbound_changed"].append(len(set(inb.items()) ^ set(now_inb.items())))
    stats = {"menu_buildings": len(menu), "menu_entries": len({ent(b) for b in menu}),
             "reachable_research": len(reach)}
    return out, stats


FAIL_KEYS = ("dup_clone", "dup_fold_category", "dup_fold_group", "level_below_requirement", "mod_level_upgrade",
             "power_before_generator", "upgrade_before_base", "relic_anchor_missing", "relic_not_behind_studies",
             "ore_no_manual_smelt", "ore_manual_after_auto", "dead_unreachable", "dead_empty",
             "building_lost", "building_changed", "inbound_changed")


# --------------------------------------------------------------------------------------------- заглушки
class Ctx:
    def __init__(self, items, origin, layers):
        self.M = {it.sid: it for it in items}
        self.origin = origin
        self.layers = layers

    def in_game(self, sid):
        return True


class Stream:
    def __init__(self, ctx):
        import kmod
        self.mb = kmod.ModBuilder("KMM_Build.mod", ctx.M)
        self.report = collections.Counter()
        self.ctx = ctx

    def change(self, sid, **k):
        return self.mb.change(sid, **k)

    def add_refs(self, sid, cat, refs):
        self.change(sid, set_refs={cat: refs})


def _it(t, sid, name, values=None, refs=None):
    it = Item(type_code(t), 0, name, sid, 0, dict(values or {}), {k: [Ref(*x) if isinstance(x, tuple) else Ref(x) for x in v] for k, v in (refs or {}).items()})
    return it


class _Mod:
    def __init__(self, items):
        self.items = items


def _world():
    bv = lambda cat, grp="", **kw: dict({"building category": cat, "building group": grp, "level": 1}, **kw)   # noqa: E731
    items = [
        _it("BUILDING_FUNCTIONALITY", "1-gamedata.base", "bed fn", {"function": 3}),
        _it("BUILDING_FUNCTIONALITY", "2-a.mod", "bed fn copy", {"function": 3, "string": "x"}),
        _it("BUILDING", "10-gamedata.base", "Bed", bv("INTERIOR"), {"functionality": ["1-gamedata.base"], "parts": ["p1"]}),
        _it("BUILDING", "11-a.mod", "Bed", bv("Furniture"), {"functionality": ["1-gamedata.base"], "parts": ["p1"]}),       # точный клон
        _it("BUILDING", "12-a.mod", "Fancy Bed", bv("SC INTERIOR"), {"functionality": ["2-a.mod"], "parts": ["p2"]}),      # почти-дубль
        _it("BUILDING", "13-gamedata.base", "Wind Generator", bv("POWER", **{"power output": 20}), {"parts": ["g"]}),
        _it("BUILDING", "14-gamedata.base", "Lamp", bv("LIGHTS", **{"power output": -5}), {"parts": ["l"]}),
        _it("BUILDING", "15-gamedata.base", "Primitive Smelter", bv("INDUSTRY"), {"parts": ["s"]}),
        _it("RESEARCH", "5359-gamedata.base", "_Default Start", {"level": 0, "blueprint only": True}, {"enable buildings": ["10-gamedata.base", "15-gamedata.base"]}),
        _it("RESEARCH", "20-gamedata.base", "Wind", {"level": 2}, {"enable buildings": ["13-gamedata.base"]}),
        _it("RESEARCH", "21-gamedata.base", "Lights", {"level": 1}, {"enable buildings": ["14-gamedata.base"]}),
        _it("RESEARCH", "22-a.mod", "Comfy", {"level": 1}, {"enable buildings": ["11-a.mod", "12-a.mod"]}),
        _it("RESEARCH", "23-a.mod", "Dodge III", {"level": 4, "is level upgrade": True}, {"enable item": ["x"]}),
        _it("RESEARCH", "24-a.mod", "Empty", {"level": 1}, {}),
        _it("RESEARCH", "14-KMM_Tech.mod", "Relic Studies", {"level": 6}, {"enable item": ["y"]}),
        _it("RESEARCH", "30-TEXT TEXTURE.mod", "Bolter", {"level": 1, "category": "40K Related Research"}, {"enable item": ["z"]}),
    ]
    origin = {it.sid: it.sid.split("-", 1)[1] for it in items}
    layers = [("gamedata.base", _Mod([]), None), ("a.mod", _Mod([]), None)]
    return items, origin, layers


def _rules():
    r = json.loads(json.dumps(RULES))
    r["ore_boundary"] = dict(r["ore_boundary"], manual_smelt=["15-gamedata.base"], powered_smelt=[], drills=[])
    return r


def test_stub_build_then_check():
    import kmod
    items, origin, layers = _world()
    ctx = Ctx(items, origin, layers)
    rules = _rules()
    before, _ = check_all(ctx.M, origin, layers, rules)
    assert before["dup_clone"] and before["power_before_generator"] and before["mod_level_upgrade"]
    assert before["relic_not_behind_studies"] and before["dead_empty"]
    base = snapshot(ctx.M)
    s = Stream(ctx)
    B_.build(ctx, s, rules)
    kmod.apply(ctx.M, s.mb.build())
    after, stats = check_all(ctx.M, origin, layers, rules, base=base)
    bad = {k: after[k] for k in FAIL_KEYS if after.get(k)}
    assert not bad, bad
    assert ctx.M["12-a.mod"].values["building category"] == "INTERIOR"          # SC INTERIOR → INTERIOR, к ванильной кровати
    assert ctx.M["12-a.mod"].values["building group"] == ctx.M["10-gamedata.base"].values["building group"] == "Bed"
    assert ctx.M["21-gamedata.base"].values["level"] == 2                         # лампа не раньше ветряка
    assert ctx.M["30-TEXT TEXTURE.mod"].values["level"] == 6
    assert "11-a.mod" in ctx.M                                                    # записи не удаляются


def test_stub_order_independent():
    import kmod
    res = []
    for seed in (1, 2, 3):
        items, origin, layers = _world()
        random.Random(seed).shuffle(items)
        ctx = Ctx(items, origin, layers)
        s = Stream(ctx)
        B_.build(ctx, s, _rules())
        m = s.mb.build()
        res.append(sorted((it.sid, sorted((k, str(v)) for k, v in it.values.items()),
                           sorted((k, sorted((r.target, r.v0, r.v1, r.v2) for r in v)) for k, v in it.refs.items())) for it in m.items))
        assert kmod.write(m)
    assert res[0] == res[1] == res[2]


# --------------------------------------------------------------------------------------------- полный режим
def _guard_writes():
    """Полный режим не пишет ничего: любая запись/удаление/перенос файла — исключение."""
    import builtins
    import io
    import shutil
    _open = builtins.open

    def ro_open(f, mode="r", *a, **k):
        if any(c in mode for c in "wax+"):
            raise RuntimeError(f"test_build_menu: запись запрещена ({f})")
        return _open(f, mode, *a, **k)
    builtins.open = io.open = ro_open

    def deny(*a, **k):
        raise RuntimeError("test_build_menu: файловая операция запрещена")
    for n in ("remove", "unlink", "rename", "replace", "rmdir", "makedirs", "mkdir"):
        setattr(os, n, deny)
    for n in ("rmtree", "copy", "copy2", "copyfile", "copytree", "move"):
        setattr(shutil, n, deny)


def full():
    _guard_writes()
    sys.path.insert(0, os.path.join(ROOT, "tools", "build"))
    import kmm_build
    import kmod
    ctx = kmm_build.Ctx()
    rp = lambda n: json.load(open(os.path.join(ROOT, "rules", "streams", n + ".json"), encoding="utf-8"))   # noqa: E731
    import tech
    st = kmm_build.Stream("tech", "KMM_Tech", ctx)
    tech.build(ctx, st, rp("tech"))
    m = st.mb.build()
    kmod.apply(ctx.M, m)
    for it in m.items:
        ctx.origin.setdefault(it.sid, "KMM_Tech.mod")
    ctx._reindex()
    before, st0 = check_all(ctx.M, ctx.origin, ctx.layers, RULES, ctx.in_game)
    base = snapshot(ctx.M)
    outs = []
    for seed in (None, 7):
        M0 = ctx.M
        if seed is not None:
            ks = list(M0)
            random.Random(seed).shuffle(ks)
            ctx.M = {k: M0[k] for k in ks}
        s = kmm_build.Stream("build", "KMM_Build", ctx)
        B_.build(ctx, s, RULES)
        mm = s.mb.build()
        outs.append(sorted((it.sid, sorted((k, str(v)) for k, v in it.values.items()),
                            sorted((k, sorted((r.target, r.v0, r.v1, r.v2) for r in v)) for k, v in it.refs.items())) for it in mm.items))
        ctx.M = M0
        if seed is None:
            mod = mm
            rep = dict(s.report)
    assert outs[0] == outs[1], "результат зависит от порядка записей"
    kmod.apply(ctx.M, mod)
    after, st1 = check_all(ctx.M, ctx.origin, ctx.layers, RULES, ctx.in_game, base=base)
    print("ДО  :", st0, {k: len(v) for k, v in before.items()})
    print("ПОСЛЕ:", st1, {k: len(v) for k, v in after.items()})
    print("отчёт потока:", rep)
    bad = {k: after[k][:5] for k in FAIL_KEYS if after.get(k)}
    print("FAIL" if bad else "OK", bad if bad else "")
    return not bad


if __name__ == "__main__":
    test_stub_build_then_check()
    test_stub_order_independent()
    print("заглушки: OK")
    if "--full" in sys.argv:
        sys.exit(0 if full() else 1)
