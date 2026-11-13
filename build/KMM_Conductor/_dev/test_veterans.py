"""Offline test: KMM_Veterans. python -I -X utf8 build/KMM_Conductor/_dev/test_veterans.py -> OK."""
import ctypes, re, sys, tempfile

DLL = r"C:\Program Files (x86)\Steam\steamapps\workshop\content\233860\3817000612\lua51.dll"
B = r"C:\KenshiModMap\build\KMM_Conductor\scripts\init"
TMP = tempfile.mkdtemp(prefix="kmm_vet_").replace("\\", "/")
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
run(re.search(r"STUBS = r'''(.*?)'''", rt, re.S).group(1).replace("TMPDIR", TMP), "stubs")
run("math.randomseed(20261113)", "seed")
for _f in sorted(__import__("glob").glob(B + r"\KMM_Conductor*.lua")): run(open(_f, encoding="utf-8").read(), _f.split("\\")[-1])
run(open(B + r"\KMM_Traces.lua", encoding="utf-8").read(), "KMM_Traces.lua")
run(open(B + r"\KMM_Veterans.lua", encoding="utf-8").read(), "KMM_Veterans.lua")
run(r'''
N, FAILS = 0, {}
function check(c, what) N = N + 1; if not c then FAILS[#FAILS + 1] = what end end
local C, V, T = KMM_Conductor, KMM_Veterans, KMM_Traces
C.reset()
local TP = C.cfg().params.traces
TP.first_hour_traces = 0; TP.max_per_day = 1000; TP.max_queue = 1000; TP.arrive_enabled = false
TP.bounty = { enabled = false }
TP.ext_per_day = 100
local S = C.state()
local pf = C.cfg().player_faction
local TW
for _, t in ipairs(C.towns()) do
  if not TW and t.owner and t.owner ~= pf and t.x and T.tier_pick(t.owner, 0) then TW = t end
end
check(TW, "town found")
local bx, bz = TW.x, TW.z
PCS = {}; CHARS = {}
local ch = MKCH("PC1", pf or "player", bx + 500, bz + 500, { player = true, platoon = "player_squad" })
PCS[1] = ch; CHARS[1] = ch
local function pump(n) for i = 1, n do CLOCK = CLOCK + 80; DAYV = DAYV + 0.02; FIRE("GameWorld::charsUpdate", {}) end end
pump(2)
V.cfg.chance.raid = 1; V.cfg.leave_chance = 0; V.cfg.maim = false
local x = V.state()
check(x and next(x.towns) == nil, "empty pool")
-- бой -> пул
for i = 1, 10 do C.emit({ type = "raid", a = pf, b = TW.owner, town_sid = TW.sid, town_name = TW.name, text = "t" }) end
check(#x.towns[TW.sid] == V.cfg.pool_max, "pool capped: " .. tostring(x.towns[TW.sid] and #x.towns[TW.sid]))
-- город игрока не пополняется
check(V.add("no_such_town", "raid", 1) == false, "unknown town rejected")
local ev0 = 0; for _, e in ipairs(S.events) do if e.type == "veteran_settled" then ev0 = ev0 + 1 end end
check(ev0 == 1, "one settled rumor (gap): " .. ev0)
-- материализация
local n0 = #SPAWNS
DAYV = math.floor(DAYV) + 1.01; pump(3)
local tags = T.stats().by_tag or {}
pump(60)
tags = T.stats().by_tag or {}
check((tags.veteran or 0) == 1, "veteran group spawned: " .. tostring(tags.veteran) .. " dis=" .. tostring(V.disabled()))
check(#SPAWNS > n0, "spawns appeared")
-- лимит: не чаще 1 группы на город в 3 дня (по дням событий veteran_seen)
for d = 1, 10 do DAYV = DAYV + 1; pump(3); for i = 1, 3 do V.add(TW.sid, "raid", math.floor(C.day())) end end
local days = {}; for _, e in ipairs(S.events) do if e.type == "veteran_seen" and e.town_sid == TW.sid then days[#days + 1] = e.day end end
check(#days >= 2, "several groups over time: " .. #days)
local okgap = true; for i = 2, #days do if days[i] - days[i - 1] < 3 then okgap = false end end
check(okgap, "gap >= 3 days: " .. table.concat(days, ","))
-- старение
V.cfg.max_age = 5
for d = 1, 8 do DAYV = math.floor(DAYV) + 1.01; pump(3) end
check(x.towns[TW.sid] == nil, "pool aged out")
-- размер состояния
for i = 1, 6 do V.add(TW.sid, "raid", 1) end
local ser = C.serialize()
check(#ser > 0 and #(function() local t = {} for k,v in pairs(x.towns) do t[#t+1]=k end return table.concat(t) end)() > 0, "serialize")
check(#C.serialize() - #ser < 20000, "state small")
check(not V.disabled(), "not disabled")
local ev = {}; for _, e in ipairs(S.events) do ev[#ev+1] = e.type end
RESULT = #FAILS == 0 and ("OK " .. N) or (table.concat(ev, ",") .. " FAIL: " .. table.concat(FAILS, "; "))
''', "test")
run("")
L.lua_getfield.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_char_p]
L.lua_getfield(st, -10002, b"RESULT")
r = L.lua_tolstring(st, -1, None).decode()
print(r)
sys.exit(0 if r.startswith("OK") else 1)
