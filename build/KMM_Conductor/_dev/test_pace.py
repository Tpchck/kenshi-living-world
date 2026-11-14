"""Offline test PACE (единый ритм видимого, KMM_Traces): приоритет сюжетного над фоновым, «давно не виденное» вперёд, пауза между враждебными встречами, EXT-лимит с поблажкой для редкого/засухи. python -I -X utf8 build/KMM_Conductor/_dev/test_pace.py -> OK."""
import ctypes, re, sys, tempfile

DLL = r"C:\Program Files (x86)\Steam\steamapps\workshop\content\233860\3817000612\lua51.dll"
B = r"C:\KenshiModMap\build\KMM_Conductor\scripts\init"
TMP = tempfile.mkdtemp(prefix="kmm_pace_").replace("\\", "/")
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
run(r'''
N, FAILS = 0, {}
function check(c, what) N = N + 1; if not c then FAILS[#FAILS + 1] = what end end
local C = KMM_Conductor
C.reset()
local TP = C.cfg().params.traces
TP.first_hour_traces = 0; TP.max_per_day = 1000; TP.max_queue = 30; TP.arrive_enabled = false; TP.bounty = { enabled = false }
TP.ext_per_day = 4; TP.ext_per_tag = 1; TP.hostile_gap_seconds = 240; TP.min_gap_seconds = 75; TP.stale_days = 3; TP.drought_seconds = 900
local pf = C.cfg().player_faction
local T = KMM_Traces
local tr = C.read_json("traces.json", "C:/KenshiModMap/build/KMM_Conductor/traces.json").factions
local FID; for fid, e in pairs(tr) do if e.tiers and e.tiers.T0 then FID = fid; break end end
PCS = {}; CHARS = {}
local pc = MKCH("PC1", pf or "player", 0, 0, { player = true, platoon = "player_squad" })
PCS[1] = pc; CHARS[1] = pc
local function pump(n, dt) for i = 1, n do CLOCK = CLOCK + (dt or 5); FIRE("GameWorld::charsUpdate", {}) end end
DAYV = 10; C.state().last_day = 10
pump(3)
local ORDER = {}
local function job(tag, extra)
  local j = { tag = tag, fid = FID, sid = tr[FID].tiers.T0, n = 1, size = 2, from_x = 2000, from_z = 2000, on_spawn = function() ORDER[#ORDER + 1] = tag end }
  if extra then for k, v in pairs(extra) do j[k] = v end end
  j.kind = "ext"; j.why = tag; j.ev = 0
  return j
end
-- 1) сюжетное раньше фонового, даже если фоновое пришло первым
T._enqueue(job("herd")); T._enqueue(job("outlaw"))
pump(40, 5)
check(ORDER[1] == "outlaw", "story before ambient: " .. tostring(ORDER[1]))
check(ORDER[2] == "herd", "ambient after: " .. tostring(ORDER[2]))
-- 2) давно не виденное вперёд (оба фоновые: herd только что был, refugees_x не было)
ORDER = {}
CLOCK = CLOCK + 600
T._enqueue(job("herd")); T._enqueue(job("caravan_x"))
pump(40, 5)
check(ORDER[1] == "caravan_x", "stale tag first: " .. tostring(ORDER[1]))
-- 3) пауза между враждебными: после outlaw засада ждёт, мирное проходит
ORDER = {}
CLOCK = CLOCK + 600
T._enqueue(job("outlaw"))
pump(20, 5)
check(ORDER[1] == "outlaw", "hostile #1 spawned")
T._enqueue(job("predator_ambush")); T._enqueue(job("herd"))
pump(24, 5)   -- 120 c: паузы min_gap хватает на мирное, но не на враждебное (240 c)
check(ORDER[2] == "herd" and ORDER[3] == nil, "ambient passes during hostile gap, ambush waits: " .. table.concat(ORDER, ","))
pump(30, 5)
check(ORDER[3] == "predator_ambush", "ambush after gap: " .. table.concat(ORDER, ","))
check((T.pace().waited_host or 0) > 0, "waited counter")
-- 4) EXT-лимит: 4 в день; сверх — только «давно не виденный» тег, до +2
DAYV = 20; C.state().last_day = 20
CLOCK = CLOCK + 2000; pump(2)
local function req(tag) return T.request(job(tag)) end
local acc = 0
for _, t in ipairs({ "a1", "a2", "a3", "a4" }) do if req(t) then acc = acc + 1 end end
check(acc == 4, "4 ext accepted: " .. acc)
pump(200, 5)
check(req("a1") == false, "same tag twice a day rejected")
T._enqueue(job("fresh")); pump(40, 5)   -- «fresh» виден сегодня (не через EXT)
check(req("fresh") == false, "5th, seen today -> rejected")
check(req("never_seen_1") == true, "5th, never seen -> allowed (rare bonus)")
check(req("never_seen_2") == true, "6th, never seen -> allowed")
check(req("never_seen_3") == false, "7th -> hard cap (ext_bonus 2)")
-- 5) счётчики классов
local n = T.pace().n
check((n.story or 0) >= 2 and (n.ambient or 0) >= 2 and (n.hostile or 0) >= 1, "class counters: s=" .. tostring(n.story) .. " a=" .. tostring(n.ambient) .. " h=" .. tostring(n.hostile))
check(next(T.disabled()) == nil, "nothing disabled")
-- PACE2: новые теги (соперник, охота, должник)
local c1, h1 = T.pace_class({ tag = "nemesis" }); check(c1 == "story" and h1, "nemesis: story, hostile")
local c2, h2 = T.pace_class({ kind = "bounty_hunt", why = "bounty" }); check(c2 == "story" and h2, "bounty hunt: story, hostile")
local c3 = T.pace_class({ tag = "debt" }); check(c3 == "critical", "debt: critical (helps in the fight now)")
RESULT = #FAILS == 0 and ("OK " .. N) or ("FAIL: " .. table.concat(FAILS, "; "))
'''.replace("TMPDIR", TMP), "test")
run("")
L.lua_getfield.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_char_p]
L.lua_getfield(st, -10002, b"RESULT")
r = L.lua_tolstring(st, -1, None).decode()
print(r)
sys.exit(0 if r.startswith("OK") else 1)
