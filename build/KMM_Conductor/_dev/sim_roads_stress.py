"""Стресс-прогон ROADS на основе tools/conductor/sim_years.py (сам файл не меняется): каждый игровой день в журнал дорог отправляется до 3 караванов
(избыток -> дефицит) и 1 бродяга, как если бы игрок всё время стоял рядом с дорогами. Проверяется, что перенос чисел не ломает критерии мира.
python -I -X utf8 build/KMM_Conductor/_dev/sim_roads_stress.py [years] [seed]  -> tools/conductor/out/sim_<y>y_<seed>_roadstress.json"""
import sys

SRC = open(r"C:\KenshiModMap\tools\conductor\sim_years.py", encoding="utf-8").read()
a = "  KMM_Conductor.advance(d)\n"
assert SRC.count(a) == 1
driver = a + """  do
    local RP, RDp = KMM_Conductor.road_plan, KMM_Conductor.road_depart
    for i = 1, 3 do local pl = RP("caravan", nil, nil); if pl then RDp(pl) end end
    local pw = RP("wanderer", nil, nil); if pw then RDp(pw) end
  end
"""
SRC = SRC.replace(a, driver)
b = "ws = KMM_Conductor.ws_stats() }})"
assert SRC.count(b) == 1
SRC = SRC.replace(b, "ws = KMM_Conductor.ws_stats(), roads = KMM_Conductor.road_state().st }})")
c = 'SUFFIX = "_nostock" if MODEL is None'
assert SRC.count(c) == 1
SRC = SRC.replace(c, 'summary["roads"] = RAW.get("roads")\n' + c)
d = 'if "--ws" in sys.argv:\n    SUFFIX += "_ws"'
assert SRC.count(d) == 1
SRC = SRC.replace(d, 'SUFFIX += "_roadstress"\n' + d)
sys.argv[0] = r"C:\KenshiModMap\tools\conductor\sim_years.py"
exec(compile(SRC, sys.argv[0], "exec"), {"__name__": "__main__", "__file__": sys.argv[0]})
