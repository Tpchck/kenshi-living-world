"""Офлайн-тест TOWNLIFE (Traces): постепенный приход в город первые 3 игровых дня района. Заглушки - как в test_traces_visible.py.
python -I -X utf8 build/KMM_Conductor/_dev/test_townlife_arrive.py -> «OK»."""
import re

src = open(r"C:\KenshiModMap\build\KMM_Conductor\_dev\test_traces_visible.py", encoding="utf-8").read()
head = src[:src.index("run(r'''\nN, FAILS")]
body = r"""run(r'''
N, FAILS = 0, {}
function check(c, what) N = N + 1; if not c then FAILS[#FAILS + 1] = what end end
function ticks(n) for i = 1, n do CLOCK = CLOCK + 1; DAYV = DAYV + 0.0005; FIRE("GameWorld::charsUpdate", {}) end end
local C = KMM_Conductor
C.reset()
C.cfg().params.traces.first_hour_traces = 0
local tr = C.read_json("traces.json", "C:/KenshiModMap/build/KMM_Conductor/traces.json")
local T, TX, TZ, OWN
for _, t in ipairs(C.towns()) do
  if t.kind == "city" and t.owner and tr.live_caravans[t.owner] and tr.factions[t.owner] and t.x then T, TX, TZ, OWN = t.sid, t.x, t.z, t.owner; break end
end
check(T ~= nil, "найден город-владелец для теста")
PCS = { MKCH("Nameless", C.cfg().player_faction or "player", TX + 3000, TZ, { player = true, platoon = "player_squad" }) }
CHARS = { PCS[1] }
local function arr() local n = 0; for k, v in pairs(KMM_Traces.stats().by_kind) do if k:sub(1, 7) == "arrive_" then n = n + v end end; return n end
ticks(10)
check(arr() == 0 or arr() == 1, "не пачкой на старте")
ticks(2000)
local a = arr()
check(a >= 2 and a <= (C.cfg().params.traces.arrive_max or 6), "постепенно, не более arrive_max: " .. a)
local k = KMM_Traces.stats().by_kind
check((k.arrive_vagrant or 0) >= 1 and ((k.arrive_trader or 0) + (k.arrive_caravan or 0)) >= 1, "бродяги и торговцы/караван")
for _, sp in ipairs(SPAWNS) do check(sp.sid ~= nil, "шаблон задан (без охраны/владельцев)") end
check(next(KMM_Traces.disabled()) == nil, "ничего не отключено")
-- по прошествии 3+ дней в том же районе новых приходов нет
DAYV = DAYV + 5; local b = arr(); ticks(2000)
check(arr() == b, "после arrive_days район не пополняется")
-- далеко от городов (>9000): ничего
PCS[1] = MKCH("Nameless", C.cfg().player_faction or "player", TX + 9000000, TZ, { player = true, platoon = "player_squad" }); CHARS[1] = PCS[1]
ticks(2000); check(arr() == b, "далеко от города: ничего (" .. arr() .. " vs " .. b .. ")")
-- сбой API отключает только arrive
PCS[1] = MKCH("Nameless", C.cfg().player_faction or "player", TX + 3000, TZ, { player = true, platoon = "player_squad" }); CHARS[1] = PCS[1]
CLOCK = CLOCK + 5000; FAIL_SPAWN = true; ticks(2000)
check(KMM_Traces.disabled().arrive == true or arr() == b, "сбой спавна: arrive отключён или район уже полон")
check(KMM_Traces.disabled().tick == nil and KMM_Traces.disabled().spawn == nil, "остальное живо")
print(N .. " checks, fails: " .. #FAILS)
for _, f in ipairs(FAILS) do print("FAIL " .. f) end
if #FAILS > 0 then error("FAILS " .. #FAILS) end
''', "tests")
print("OK")
"""
exec(compile(head + body, "test_townlife_arrive", "exec"))
