"""Тест паспорта культуры (rules/culture.json) в behavior: архетип выше ftype, only_vs, vs_archetype/vs_name, выравнивание
двойников; и потолок денег голодных (_shared.money_norm). Заглушки, без игры и без записи файлов.
python -I -X utf8 tools/streams/test_culture.py"""
import collections
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, ".."))
import behavior  # noqa: E402
import _shared  # noqa: E402
from kmod import Ref  # noqa: E402

WR = json.load(open(os.path.join(HERE, "..", "..", "rules", "streams", "behavior.json"), encoding="utf-8"))["world_relations"]
CULT = json.load(open(behavior.CULTURE_PATH, encoding="utf-8"))


class F:
    def __init__(self, sid, name, ft=4, rel=None, dflt=0, notreal=False):
        self.sid, self.name, self.type_name = sid, name, "FACTION"
        self.values = {"fundamental type": ft, "default relation": dflt, "not real": notreal}
        self.refs = {"relations": [Ref(t, v, 0, 0) for t, v in (rel or {}).items()]}


def test_archetype_from_culture():
    rc = F("225-KillerRobot.mod", "失控", ft=4, dflt=-100)
    assert behavior.archetype_of(rc, None, WR) == "robot"                 # было settler по ftype CIVILIAN
    nec = F("1-40K Necrons.mod", "Space Necromancer - Sora Dynasty")
    assert behavior.archetype_of(nec, None, WR) == "robot"                # было xeno
    assert behavior.archetype_of(F("2-x.mod", "Free Traders", ft=3), None, WR) != "robot"


def test_matrix_hn_imperium_matches_astartes():
    assert WR["matrix"]["religion|imperium"] < 0                          # docs/core/ASTARTES.md: HN -> ордена -10, не +10


def test_plan_only_vs_and_vs():
    fs = [F("225-KillerRobot.mod", "失控", dflt=-100), F("ft.mod", "Free Traders", ft=3), F("sk.mod", "Skeletons", ft=2),
          F("nec.mod", "Space Necromancer - Sora Dynasty"), F("th.mod", "Tech Hunters", ft=3), F("gs.mod", "Greenskins"),
          F("st.mod", "Slave Traders", ft=7), F("hn.mod", "The Holy Nation"), F("ier.mod", "Imperial Expedition Remnants"),
          F("db.mod", "Dust Bandits", ft=8)]
    wr = dict(WR, archetype_by_name=dict(WR["archetype_by_name"], robot=WR["archetype_by_name"]["robot"] + ["Skeletons"],
                                         underworld=WR["archetype_by_name"].get("underworld", []) + ["Slave Traders"]))
    plan, st, arch = behavior.plan_world_relations(fs, {}, {f.sid for f in fs}, wr, cult=CULT)
    rc = plan.get("225-KillerRobot.mod", {})
    assert rc.get("ft.mod") == -80 and plan["ft.mod"]["225-KillerRobot.mod"] == -80   # торговцы — враги, не +10
    assert rc.get("sk.mod") == 30                                                      # родня скелетов
    assert "db.mod" not in rc                                                          # only_vs: матрица robot|bandit не пишется
    assert plan["nec.mod"].get("th.mod") == -60 and plan["nec.mod"].get("sk.mod") == 20
    assert plan["nec.mod"].get("ier.mod") == -100
    assert plan["gs.mod"].get("st.mod") == 30                                          # у орков есть союзник
    assert plan["hn.mod"].get("ier.mod") == -10 and plan["ier.mod"].get("hn.mod") == -10


class Ctx:
    def __init__(self, facs, others=()):
        self.M = {f.sid: f for f in list(facs) + list(others)}
        self.van = [("gamedata.base", None, None)]

    def all(self, t):
        return [x for x in self.M.values() if x.type_name == t]

    def in_game(self, sid):
        return True


class Sq:
    def __init__(self, sid, fac):
        self.sid, self.type_name, self.name, self.values = sid, "SQUAD_TEMPLATE", sid, {}
        self.refs = {"faction": [Ref(fac, 0, 0, 0)]}


class S:
    def __init__(self):
        self.report = collections.Counter()
        self.ch = {}

    def change(self, sid, values=None, **k):
        self.ch[sid] = values
        return True


def test_align_twins():
    hn = F("1083-gamedata.base", "The Holy Nation", rel={"uc": -100, "shek": -100})
    hn2 = F("352-cook_set.mod", "The Holy Nation", rel={"Raptors": -100, "1083-gamedata.base": 100, "mong": 100}, notreal=True)
    uc = F("uc", "United Cities", rel={"1083-gamedata.base": -100})
    shek = F("shek", "Shek Kingdom", rel={"1083-gamedata.base": -100})
    mong = F("mong", "Mongrel", rel={"352-cook_set.mod": 50})
    om = F("42085-rebirth.mod", "Old Machines", ft=2, dflt=-100)
    om2 = F("5-HTDEnforcers.mod", "Old Machines", ft=2, dflt=0)
    ctx = Ctx([hn, hn2, uc, shek, mong, om, om2], [Sq("q1", "1083-gamedata.base"), Sq("q2", "42085-rebirth.mod")])
    plan, s = {}, S()
    behavior.align_twins(ctx, s, plan, CULT["twins"], WR["min_delta"])
    t = plan["352-cook_set.mod"]
    assert t["uc"] == -100 and t["shek"] == -100                       # пекарня HN воюет с UC и Shek как канон
    assert t.get("mong") == 0 and plan["mong"]["352-cook_set.mod"] == 0   # своя дружба двойника, которой нет у канона — снята
    assert plan["uc"]["352-cook_set.mod"] == -100 and plan["shek"]["352-cook_set.mod"] == -100
    assert s.ch["5-HTDEnforcers.mod"] == {"default relation": -100}      # default relation как у канона
    assert "1083-gamedata.base" not in s.ch


def test_twins_disabled():
    plan = {}
    behavior.align_twins(Ctx([F("a-gamedata.base", "X"), F("b-m.mod", "X", rel={"z": 50})]), S(), plan, {"enabled": False}, 15)
    assert plan == {}


class Ch:
    def __init__(self, name, cls, mn, mx):
        self.name, self.values = name, {"NPC class": cls, "money min": mn, "money max": mx}


def test_money_cap_starving():
    assert _shared.money_norm(Ch("Hungry bandit", 8, 0, 200)) == {"money min": 0, "money max": 15}
    assert _shared.money_norm(Ch("Hungry Child", 8, 0, 15)) == {}
    assert _shared.money_norm(Ch("Dust Bandit", 8, 0, 200))["money max"] >= 300   # обычные бандиты — как раньше


if __name__ == "__main__":
    n = 0
    for k, f in sorted(globals().items()):
        if k.startswith("test_") and callable(f):
            f()
            n += 1
    print(f"test_culture: OK ({n})")
