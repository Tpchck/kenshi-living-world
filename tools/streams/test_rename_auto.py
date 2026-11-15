"""Тест fix.rename_auto (B4 Н1/Н2): видимые имена без нелатиницы и франшиз. Заглушки контекста, без игры и без записи файлов.
python -I -X utf8 tools/streams/test_rename_auto.py"""
import collections
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, ".."))
import fix  # noqa: E402

RULES = json.load(open(os.path.join(HERE, "..", "..", "rules", "streams", "fix.json"), encoding="utf-8"))
RA = RULES["junk_unlink"]["rename_auto"]


class It:
    def __init__(self, sid, t, name, values=None):
        self.sid, self.type_name, self.name, self.values, self.refs = sid, t, name, dict(values or {}), {}


class Mod:
    def __init__(self, items):
        self.items = items


class Ctx:
    def __init__(self, layers, origin=None):
        self.layers = [(n, Mod(items), None) for n, items in layers]
        self.M = {}
        for _, m, _ in self.layers:
            for it in m.items:
                self.M[it.sid] = it
        self.origin = origin or {}

    def in_game(self, sid):
        return not sid.startswith("rej")


class S:
    def __init__(self):
        self.report = collections.Counter()
        self.ch = {}

    def change(self, sid, rename=None, values=None, **k):
        self.ch[sid] = (rename, values)
        return True


def run(ctx, ra=RA):
    s = S()
    fix.rename_auto(ctx, s, ra)
    return s


def test_flag():
    assert fix.is_nonlatin("失控") and fix.is_nonlatin("Шлем Улья") and fix.is_nonlatin("Hemo‑dogs")
    assert not fix.is_nonlatin("Holy Nation") and not fix.is_nonlatin("Café")


def test_dict_restore_strip_left():
    van = [It("1-gamedata.base", "BUILDING", "Medicrate"), It("2-a.mod", "FACTION", "Ohio")]
    over = [It("1-gamedata.base", "BUILDING", "医疗板条箱"), It("3-k.mod", "FACTION", "失控"),
            It("4-m.mod", "ARMOUR", "猎兵兜帽Hunting Hood"), It("5-k.mod", "ITEM", "完全未知"),
            It("6-k.mod", "SQUAD_TEMPLATE", "游荡小队"), It("rej-7.mod", "FACTION", "祭品"),
            It("8-w.mod", "ARMOUR", "Savlar Hemo‑dogs boots"), It("9-x.mod", "CHARACTER", "终端机械师守卫")]
    ctx = Ctx([("gamedata.base", van), ("x.mod", over)], origin={"9-x.mod": "KMM_Traces.mod"})
    s = run(ctx)
    assert s.ch["1-gamedata.base"][0] == "Medicrate", s.ch          # нелатиницу поставил чужой мод поверх — вернуть имя нижнего слоя
    assert s.ch["3-k.mod"][0] == "Rogue Constructs"                 # словарь
    assert s.ch["2-a.mod"][0] == "Wanderers of the Waste"           # франшиза латиницей — тоже словарь
    assert s.ch["4-m.mod"][0] == "Hunting Hood"                     # латинская часть смешанного имени
    assert s.ch["8-w.mod"][0] == "Savlar Hemo-dogs boots"           # типографика
    assert s.ch["9-x.mod"][0] == "Terminal Mechanic Guard"          # копии своих потоков (Traces) тоже
    assert "6-k.mod" not in s.ch and "rej-7.mod" not in s.ch        # невидимый тип и отвергнутая игрой запись не трогаются
    assert s.report["nonlatin_left:ITEM|完全未知"] == 1 and "5-k.mod" not in s.ch


def test_dict_sid_description():
    ctx = Ctx([("TIHYD_Zoo.mod", [It("5000410-TIHYD_Zoo.mod", "ITEM", "Deathclaw"), It("1-TIHYD.mod", "ANIMAL_CHARACTER", "Deathclaw")])])
    s = run(ctx)
    assert s.ch["5000410-TIHYD_Zoo.mod"] == ("Clawbeast Claw", {"description": "The severed claw from a clawbeast."})
    assert s.ch["1-TIHYD.mod"][0] == "Clawbeast"


def test_dictionary_is_clean():
    vals = [v for k, v in RA["dict"].items() if not k.startswith("_")]
    vals += [v if isinstance(v, str) else v["name"] for k, v in RA["dict_sid"].items() if not k.startswith("_")]
    bad = [v for v in vals if fix.is_nonlatin(v) or not v.strip()]
    assert not bad, bad
    franchise = ("deathclaw", "ohio", "genzee", "metro", "artyom", "ak-2012")
    assert not [v for v in vals if any(w in v.lower() for w in franchise)]
    assert all(fix.latin_name(v, RA["punct"]) is None or not fix.is_nonlatin(fix.latin_name(v, RA["punct"])) for v in vals)


def test_descriptions():
    ctx = Ctx([("m.mod", [It("1-m.mod", "ARMOUR", "Hunting Hood", {"description": "猎兵兜帽，适合沙漠"}),
                          It("2-m.mod", "ITEM", "Notes", {"description": "Old notes — it’s torn"}),
                          It("3-m.mod", "ITEM", "Plain", {"description": "plain text"})])])
    s = run(ctx)
    assert s.ch["1-m.mod"] == (None, {"description": ""})                    # иероглифы без английского — пусто
    assert "2-m.mod" not in s.ch                                             # одна типографика в описании — не трогаем
    assert "3-m.mod" not in s.ch


def test_disabled():
    ctx = Ctx([("k.mod", [It("3-k.mod", "FACTION", "失控")])])
    assert not run(ctx, dict(RA, enabled=False)).ch


if __name__ == "__main__":
    n = 0
    for k, f in sorted(globals().items()):
        if k.startswith("test_") and callable(f):
            f()
            n += 1
    print(f"test_rename_auto: OK ({n})")
