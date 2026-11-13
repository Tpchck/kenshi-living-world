"""Offline test погоды в KMM_Traces: плохая погода -> arrive ускоряется, ext режется, после бури волна; нет API -> без эффекта.
python -I -X utf8 build/KMM_Conductor/_dev/test_weather.py -> OK."""
src = open(r"C:\KenshiModMap\build\KMM_Conductor\_dev\test_townlife_arrive.py", encoding="utf-8").read()
head = src[:src.index('exec(compile')]
head_py = open(r"C:\KenshiModMap\build\KMM_Conductor\_dev\test_traces_visible.py", encoding="utf-8").read()
head_py = head_py[:head_py.index("run(r'''\nN, FAILS")]
body = r"""run(r'''
N, FAILS = 0, {}
function check(c, what) N = N + 1; if not c then FAILS[#FAILS + 1] = what end end
function ticks(n) for i = 1, n do CLOCK = CLOCK + 1; DAYV = DAYV + 0.0005; FIRE("GameWorld::charsUpdate", {}) end end
local C = KMM_Conductor
C.reset()
C.cfg().params.traces.first_hour_traces = 0
local tr = C.read_json("traces.json", "C:/KenshiModMap/build/KMM_Conductor/traces.json")
local TX, TZ
for _, t in ipairs(C.towns()) do
  if t.kind == "city" and t.owner and tr.live_caravans[t.owner] and tr.factions[t.owner] and t.x then TX, TZ = t.x, t.z; break end
end
local pc = MKCH("Nameless", C.cfg().player_faction or "player", TX + 3000, TZ, { player = true, platoon = "player_squad" })
local W, WS = 0, 0.8
function pc:getCurrentWeatherAffectStatus() return W end
function pc:getCurrentWeatherAffectStrength() return WS end
PCS = { pc }; CHARS = { pc }
ticks(3)
check(KMM_Traces.weather().bad == false, "ясно: не плохая")
W = 1; ticks(10)
check(KMM_Traces.weather().bad == true, "пыльная буря сильная: плохая")
WS = 0.1; CLOCK = CLOCK + 10; ticks(3); check(KMM_Traces.weather().bad == false, "слабая: не плохая")
WS = 0.8; W = 5; CLOCK = CLOCK + 10; ticks(3); check(KMM_Traces.weather().bad == false, "обычный дождь: не плохая")
-- буря: ext режется
W = 2; CLOCK = CLOCK + 10; ticks(3)
local rej = 0
KMM_Traces.stats().wx_skipped = 0
for i = 1, 40 do CLOCK = CLOCK + 10; KMM_Traces.request({ tag = "t" .. i, fid = C.cfg().player_faction or "player", n = 1 }) end
check((KMM_Traces.stats().wx_skipped or 0) >= 15, "буря режет ext: " .. tostring(KMM_Traces.stats().wx_skipped))
-- конец бури: волна
W = 0; CLOCK = CLOCK + 10; ticks(3)
local w = KMM_Traces.weather()
check(w.bad == false and w.n_wave >= 1, "волна после бури зафиксирована")
-- нет API у персонажа: не падает
pc.getCurrentWeatherAffectStatus = nil; CLOCK = CLOCK + 10; ticks(5)
check(KMM_Traces.weather().bad == false and next(KMM_Traces.disabled()) == nil, "нет API: без эффекта, модуль жив")
print(N .. " checks, fails: " .. #FAILS)
for _, f in ipairs(FAILS) do print("FAIL " .. f) end
if #FAILS > 0 then error("FAILS " .. #FAILS) end
''', "tests")
print("OK")
"""
exec(compile(head_py + body, "test_weather", "exec"))
