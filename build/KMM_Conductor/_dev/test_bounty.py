"""Offline test: bounty -> hunters (reward present -> job after cooldown, none -> no job, limit, self-disable). python -I -X utf8 build/KMM_Conductor/_dev/test_bounty.py -> OK."""
import ctypes, re, sys, tempfile

DLL = r"C:\Program Files (x86)\Steam\steamapps\workshop\content\233860\3817000612\lua51.dll"
B = r"C:\KenshiModMap\build\KMM_Conductor\scripts\init"
TMP = tempfile.mkdtemp(prefix="kmm_bounty_").replace("\\", "/")
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
TP.first_hour_traces = 0; TP.max_per_day = 1000; TP.max_queue = 1000; TP.arrive_enabled = false
local tr = C.read_json("traces.json", "C:/KenshiModMap/build/KMM_Conductor/traces.json")
local pf = C.cfg().player_faction
local F
for fid, f in pairs(C.state().F) do if f.alive and not f.player and fid ~= pf and tr.factions[fid] and tr.factions[fid].tiers and next(tr.factions[fid].tiers) then F = fid; break end end
check(F, "faction found")
PCS = {}; CHARS = {}
local ch = MKCH("PC1", pf or "player", 1000, 1000, { player = true, platoon = "player_squad" })
local REW = {}   -- fid -> amount
ch.crimes = {
  _getHighestBountyFaction = function(self) local bf, ba; for f, a in pairs(REW) do if not ba or a > ba then bf, ba = f, a end end; return bf and FAC(bf) end,
  getActualBounty = function(self, fo) return REW[fo:getData().stringID] or 0 end,
}
PCS[1] = ch; CHARS[1] = ch
TP.bounty = { chance = 1.0, check_hours = 1, cooldown_hours = 10, threshold = 5000, max_active = 2 }
local T = KMM_Traces
local function adv(h) DAYV = DAYV + h / 24; C.state().last_day = (C.state().last_day or 0) + h / 24 end
local function pump(n) for i = 1, n do CLOCK = CLOCK + 1; FIRE("GameWorld::charsUpdate", {}) end end
local function count() local n = 0; for _, j in ipairs(T.queue()) do if j.kind == "bounty_hunt" then n = n + 1 end end; return n end
local function step() adv(2); CLOCK = CLOCK + 25; T.bounty().last_chk = nil; T.bounty().step() end
pump(3)
-- 1. наград нет -> нет работы
for i = 1, 3 do adv(2); T.bounty().step() end
check(count() == 0 and T.stats().by_kind.bounty_hunt == nil, "без награды охотников нет")
-- 2. награда ниже порога
REW[F] = 1000; adv(2); T.bounty().step(); check(count() == 0, "ниже порога нет")
-- 3. награда есть -> job
REW[F] = 30000; adv(2); T.bounty().step(); check(count() == 1, "награда -> job")
check(T.bounty().tier(30000) == 3 and T.bounty().tier(100) == 1 and T.bounty().tier(90000) == 4, "тиры по награде")
-- 4. кулдаун
adv(2); T.bounty().step(); check(count() == 1, "кулдаун держит")
-- 5. после кулдауна, но лимит (job в очереди + активные)
adv(12); T.bounty().step(); check(count() == 2, "после кулдауна второй job")
adv(12); T.bounty().step(); check(count() == 2, "лимит max_active")
-- 6. выполнение: спавн + emit
local n0 = #SPAWNS
local evs0 = #C.state().events
for i = 1, 200 do if count() == 0 then break end; CLOCK = CLOCK + 80; DAYV = DAYV + 0.0001; pump(1) end
check(#SPAWNS > n0, "охотники заспавнены")
local found = false
for _, ev in ipairs(C.state().events) do if ev.type == "bounty_hunters" and ev.fid == F then found = true end end
check(found, "хроника bounty_hunters")
-- 7. самоотключение при ошибке API
ch.crimes = { _getHighestBountyFaction = function() error("boom") end }
T.bounty().last_hunt = nil; T.bounty().act = {}
for i = 1, 3 do adv(2); T.bounty().step() end
check(not T.disabled().bounty, "ошибка чтения поглощается pcall на персонаже")
ch.crimes = nil
check(next(T.bounty().read()) == nil, "нет crimes -> пусто")
RESULT = #FAILS == 0 and ("OK " .. N) or ("FAIL: " .. table.concat(FAILS, "; "))
''', "test")
run("")
L.lua_getfield.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_char_p]
L.lua_getfield(st, -10002, b"RESULT")
r = L.lua_tolstring(st, -1, None).decode()
print(r)
sys.exit(0 if r.startswith("OK") else 1)
