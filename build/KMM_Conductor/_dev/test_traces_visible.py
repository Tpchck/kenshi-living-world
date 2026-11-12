"""Офлайн-тест видимых событий KMM_Traces (trade_for/refugees/relic_salvage/smuggle_run → отряд рядом с игроком).
python -I -X utf8 build/KMM_Conductor/_dev/test_traces_visible.py → «OK n checks», код 1 при провале. Заглушки — из tools/test/test_runtime.py."""
import ctypes
import os
import re
import sys
import tempfile

DLL = r"C:\Program Files (x86)\Steam\steamapps\workshop\content\233860\3817000612\lua51.dll"
B = r"C:\KenshiModMap\build\KMM_Conductor\scripts\init"
TMP = tempfile.mkdtemp(prefix="kmm_vis_").replace("\\", "/")
L = ctypes.CDLL(DLL)
L.luaL_newstate.restype = ctypes.c_void_p
for fn, at in [("luaL_openlibs", [ctypes.c_void_p]), ("luaL_loadstring", [ctypes.c_void_p, ctypes.c_char_p]),
               ("lua_pcall", [ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int])]:
    getattr(L, fn).argtypes = at
L.lua_tolstring.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p]
L.lua_tolstring.restype = ctypes.c_char_p
st = L.luaL_newstate()
L.luaL_openlibs(st)


def run(code, name="chunk"):
    if L.luaL_loadstring(st, code.encode("utf-8")) or L.lua_pcall(st, 0, 0, 0):
        msg = L.lua_tolstring(st, -1, None)
        raise RuntimeError(f"{name}: {msg.decode('utf-8', 'replace') if msg else '?'}")


rt = open(r"C:\KenshiModMap\tools\test\test_runtime.py", encoding="utf-8").read()
stubs = re.search(r"STUBS = r'''(.*?)'''", rt, re.S).group(1).replace("TMPDIR", TMP)
run(stubs, "stubs")
for _f in sorted(__import__("glob").glob(B + r"\KMM_Conductor*.lua")): run(open(_f, encoding="utf-8").read(), _f.split("\\")[-1])
run(open(B + r"\KMM_Traces.lua", encoding="utf-8").read(), "KMM_Traces.lua")
run(r'''
N, FAILS = 0, {}
function check(c, what) N = N + 1; if not c then FAILS[#FAILS + 1] = what end end
function ticks(n) for i = 1, n do CLOCK = CLOCK + 1; DAYV = DAYV + 0.001; FIRE("GameWorld::charsUpdate", {}) end end
function vs() local t = 0; for k, v in pairs(KMM_Traces.stats().by_kind) do if k:sub(1, 1) == "v" then t = t + v end end; return t end
local C = KMM_Conductor
C.reset()
if C.cfg().vassals then C.cfg().vassals.markets = {} end
for k, t in pairs(C.state().treaties or {}) do if t.seed then C.state().treaties[k] = nil end end   -- и стартовые присяги   -- VASSALS: сделки чёрных рынков (свои караваны) проверяет test_vassals.py
C.cfg().params.traces.first_hour_traces = 0; C.cfg().params.traces.arrive_enabled = false
local tr = C.read_json("traces.json", "C:/KenshiModMap/build/KMM_Conductor/traces.json")
check(next(tr.live_caravans or {}) ~= nil, "traces.json: live_caravans есть")
-- город с фракцией, у которой есть живой караван и беженцы
local T, TX, TZ, OWN
for sid, I in pairs(C.cfg().town_info) do
  for fid, f in pairs(C.state().F) do
    if f.alive and f.towns[sid] and tr.live_caravans[fid] and tr.factions[fid] and tr.factions[fid].refugees and I.x then T, TX, TZ, OWN = sid, I.x, I.z, fid end
  end
  if T then break end
end
check(T ~= nil, "найден город для теста")
PCS = { MKCH("Nameless", C.cfg().player_faction or "player", TX + 2500, TZ, { player = true, platoon = "player_squad" }) }
CHARS = { PCS[1] }
ticks(5)   -- инициализация, подписка
local s0 = vs()
-- 1) событие рядом → один спавн
C.emit({ type = "trade_for", a = OWN, b = OWN, town_sid = T, town_name = "T", cat = "food" })
ticks(3)
check(vs() == s0 + 1, "trade_for рядом: один спавн (" .. tostring(vs() - s0) .. ")")
check(KMM_Traces.stats().by_kind.vcaravan == 1, "тип vcaravan")
local sp = SPAWNS[#SPAWNS]
check(sp and sp.sid == tr.live_caravans[OWN], "шаблон — живой караван фракции")
check(not (tr.dead and false) and tr.live_caravans[OWN] ~= nil, "наш караван не из dead_caravan_sids")
local isdead = false; for _, d in ipairs(tr.dead_caravan_sids) do if d == tr.live_caravans[OWN] then isdead = true end end
check(not isdead, "живой караван не в dead_caravan_sids (caravan_lost работает)")
-- 2) дубль не спавнится; лимит 60 с
C.emit({ type = "trade_for", a = OWN, b = OWN, town_sid = T, town_name = "T", cat = "food" })
C.emit({ type = "refugees", a = OWN, town_sid = T, town_name = "T", n = 5, why = "famine" })
ticks(5)
check(vs() == s0 + 1, "лимит: не чаще 1 на 60 с (в паузе)")
ticks(100)
check(vs() == s0 + 2 and KMM_Traces.stats().by_kind.vrefugees == 1, "refugees после паузы; дубль trade_for не спавнится")
-- 4) smuggle_run и relic_salvage
C.emit({ type = "smuggle_run", a = OWN, town_sid = T, town_name = "T", cat = "x" })
ticks(100)
check(KMM_Traces.stats().by_kind.vsmuggle == 1, "smuggle_run: T0-отряд")
C.emit({ type = "relic_salvage", a = OWN, town_sid = T, town_name = "T" })
ticks(100)
check(KMM_Traces.stats().by_kind.vexpedition == 1, "relic_salvage: отряд у города/руин")
-- 5) лимит живых 4
C.cfg().town_info.fake1 = { x = TX + 100, z = TZ }; C.cfg().town_info.fake2 = { x = TX + 200, z = TZ }
C.emit({ type = "trade_for", a = OWN, b = OWN, town_sid = "fake1", town_name = "T2", cat = "ore" })
C.emit({ type = "refugees", a = OWN, town_sid = "fake2", town_name = "T2", n = 3, why = "z" })
ticks(200)
check(vs() == s0 + 4, "не более 4 живых наших отрядов (" .. tostring(vs() - s0) .. ")")
-- 6) далеко → ничего
PCS[1] = MKCH("Nameless", C.cfg().player_faction or "player", TX + 90000, TZ, { player = true, platoon = "player_squad" }); CHARS[1] = PCS[1]
local s1 = vs()
C.emit({ type = "refugees", a = OWN, town_sid = T, town_name = "Far", n = 3, why = "x" })
ticks(100)
check(vs() == s1, "далеко: ничего")
-- 7) персонажей нет → ничего и без ошибок
PCS = {}; CHARS = {}
C.emit({ type = "refugees", a = OWN, town_sid = T, town_name = "None", n = 3, why = "y" })
ticks(100)
check(vs() == s1 and next(KMM_Traces.disabled()) == nil, "персонажей нет: ничего, ничего не отключено")
-- 8) сбой API отключает только visible
PCS = { MKCH("Nameless", C.cfg().player_faction or "player", TX + 2500, TZ, { player = true, platoon = "player_squad" }) }; CHARS = { PCS[1] }
CLOCK = CLOCK + 2000   -- TTL живых истёк
FAIL_SPAWN = true
C.emit({ type = "trade_for", a = OWN, b = OWN, town_sid = "fake1", town_name = "T3", cat = "x" })
ticks(100)
local d = KMM_Traces.disabled()
check(d.visible == true, "сбой спавна отключил visible")
check(d.tick == nil and d.spawn == nil and d.caravan_lost == nil and d.events == nil, "остальные функции живы")
FAIL_SPAWN = false
print(N .. " checks, fails: " .. #FAILS)
for _, f in ipairs(FAILS) do print("FAIL " .. f) end
if #FAILS > 0 then error("FAILS " .. #FAILS) end
''', "tests")
print("OK")
