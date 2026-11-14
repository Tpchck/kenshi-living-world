"""Offline test Traces vfreed (slaves_freed -> колонна освобождённых + конвой). Основа — test_traces_visible.
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
-- slaves_freed рядом -> колонна освобождённых (refugees освободителя) + конвой T0, оба к городу освободителя
local n0 = #SPAWNS
C.emit({ type = "slaves_freed", a = OWN, b = OWN, town_sid = T, text = "test" })
ticks(5)
check(vs() == s0 + 1 and (KMM_Traces.stats().by_kind.vfreed or 0) == 1, "slaves_freed: один видимый спавн vfreed (" .. tostring(vs() - s0) .. ")")
local rsid = tr.factions[OWN] and tr.factions[OWN].refugees
local got_ref, got_esc = false, false
for k = n0 + 1, #SPAWNS do local sp = SPAWNS[k]; if sp.sid == rsid then got_ref = true elseif sp.sid then got_esc = true end end
check(got_ref, "колонна — шаблон refugees освободителя")
check(got_esc, "есть конвой (" .. tostring(#SPAWNS - n0) .. " спавнов)")
C.emit({ type = "slaves_freed", a = OWN, b = OWN, town_sid = T, text = "test2" })
ticks(5)
check((KMM_Traces.stats().by_kind.vfreed or 0) == 1, "лимит 60 с держит второй")
print(N .. " checks, fails: " .. #FAILS)
for _, f in ipairs(FAILS) do print("FAIL " .. f) end
if #FAILS > 0 then error("FAILS " .. #FAILS) end
''', "tests")
print("OK")
