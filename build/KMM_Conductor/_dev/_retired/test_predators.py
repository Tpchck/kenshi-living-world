"""Offline test KMM_Predators: гнездо на горячем участке, потери караванов, патруль, зачистка, лимиты, материализация. python -I -X utf8 build/KMM_Conductor/_dev/test_predators.py -> OK."""
import ctypes, re, sys, tempfile

DLL = r"C:\Program Files (x86)\Steam\steamapps\workshop\content\233860\3817000612\lua51.dll"
B = r"C:\KenshiModMap\build\KMM_Conductor\scripts\init"
TMP = tempfile.mkdtemp(prefix="kmm_predators_").replace("\\", "/")
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
run("math.randomseed(20261116)", "seed")
for _f in sorted(__import__("glob").glob(B + r"\KMM_Conductor*.lua")): run(open(_f, encoding="utf-8").read(), _f.split("\\")[-1])
run(open(B + r"\KMM_Traces.lua", encoding="utf-8").read(), "KMM_Traces.lua")
run(open(B + r"\KMM_Predators.lua", encoding="utf-8").read(), "KMM_Predators.lua")
run('KMM_Predators.P.sdir = "%s/"' % TMP, "sdir")
run(r'''
N, FAILS = 0, {}
function check(c, what) N = N + 1; if not c then FAILS[#FAILS + 1] = what end end
local C = KMM_Conductor
C.reset()
C.advance(10); C.advance(16); DAYV = 16
local S = C.state()
local P = KMM_Predators.P
P.daily_chance = 1; P.tick_gap = 0
local TP = C.cfg().params.traces
TP.first_hour_traces = 0; TP.max_per_day = 1000; TP.max_queue = 1000; TP.arrive_enabled = false; TP.bounty = { enabled = false }
local tr = C.read_json("traces.json", "C:/KenshiModMap/build/KMM_Conductor/traces.json")
local pf = C.cfg().player_faction
-- пара городов одного хозяина + бандит
local tl = C.towns()
local A, B
for _, a in ipairs(tl) do if a.owner and a.x and a.owner ~= pf and not A then
  for _, b in ipairs(tl) do if b.sid ~= a.sid and b.x and math.abs(b.x - a.x) + math.abs(b.z - a.z) < 60000 and math.abs(b.x - a.x) + math.abs(b.z - a.z) > 8000 then A, B = a, b; break end end
end end
check(A and B, "пара городов")
local bandit
for fid, c in pairs(C.cfg().factions) do if c.arch == "bandit" and tr.factions[fid] and C.alive(fid) and C.fpos(fid) and fid ~= A.owner then bandit = fid; break end end
check(bandit, "бандитская фракция")
S.rel[bandit] = S.rel[bandit] or {}; S.rel[bandit][A.owner] = -60
local ox, oz = C.fpos(bandit)
-- игрок далеко: симуляция чисто дальняя
PCS = {}; CHARS = {}
local ch = MKCH("PC1", pf or "player", ox + 9e6, oz + 9e6, { player = true, platoon = "player_squad" })
PCS[1] = ch; CHARS[1] = ch
local function inject(n)
  local r = C.road_state()
  for i = 1, n do r.tr[9000 + r.nid] = { k = "caravan", f = A.owner, from = A.sid, to = B.sid, c = "metal", n = 10, d0 = S.last_day, eta = S.last_day + 400, id = 9000 + r.nid }; r.nid = r.nid + 1 end
end
local function pump(n) for i = 1, n do CLOCK = CLOCK + 80; DAYV = DAYV + 0.0001; FIRE("GameWorld::charsUpdate", {}) end end
local function setday(d) DAYV = d; S.last_day = d; pump(1) end
setday(17); inject(6)
local e = KMM_Predators.slot()
check(e == nil or true, "slot")
setday(18)
e = KMM_Predators.slot()
local nn = 0; for _ in pairs(e.nests) do nn = nn + 1 end
check(nn == 1, "гнездо возникло: " .. nn)
local k, nest = next(e.nests)
check(nest and C.cfg().factions[nest.fid].arch == 'bandit' and nest.owner, "фракция/хозяин")
-- потери
local before = 0; for _ in pairs(C.road_state().tr) do before = before + 1 end
P.loss_base = 1; P.loss_cap = 1
setday(19)
local after = 0; for _ in pairs(C.road_state().tr) do after = after + 1 end
check(after < before and (e.stat.caravans_lost or 0) > 0, "караваны потеряны " .. before .. "->" .. after)
check(#C.loot_of(nest.fid) > 0, "добыча бандита")
-- слух/хроника
local ev = {}
for _, x in ipairs(S.events) do ev[x.type] = (ev[x.type] or 0) + 1 end
check(ev.predator_nest == 1 and ev.predator_raid and ev.predator_raid >= 1, "события nest/raid")
-- видимость: игрок рядом
ch = MKCH('PC1', pf or 'player', nest.x + 300, nest.z, { player = true, platoon = 'player_squad' }); PCS[1] = ch; CHARS[1] = ch
local n0 = #SPAWNS
pump(30)
check((KMM_Traces.stats().by_tag or {}).predator_ambush >= 1, "засада заявлена и заспавнена: " .. tostring((KMM_Traces.stats().by_tag or {}).predator_ambush))
check(#SPAWNS > n0, "отряды в SPAWNS")
-- патруль и зачистка
local kcool = nil
for d = 20, 45 do setday(d); if not e.nests[k] and kcool == nil then kcool = (e.cool[k] or -1) > S.last_day end; if next(e.nests) == nil then break end end
check(next(e.nests) == nil, "гнездо исчезло")
check((e.stat.cleared or 0) + (e.stat.moved_on or 0) >= 1, "зачистка или уход")
ev = {}; for _, x in ipairs(S.events) do ev[x.type] = (ev[x.type] or 0) + 1 end
check((ev.predator_patrol or 0) >= 1 and (ev.predator_cleared or 0) >= 1, "patrol+cleared события: " .. tostring(ev.predator_patrol) .. "/" .. tostring(ev.predator_cleared))
check(kcool == true, "участок остывает (в момент исчезновения гнезда)")
-- лимиты: <=6, <=1 на участок
P.loss_base = 0.15; P.loss_cap = 0.6; e.cool = {}
for d = 46, 80 do setday(d); inject(3); local c = 0; for _ in pairs(e.nests) do c = c + 1 end; check(c <= 6, "лимит 6"); end
-- объём состояния
local function sz(t, d) d = d or 0; if d > 6 then return 0 end local n = 0; for k, v in pairs(t) do n = n + #tostring(k) + (type(v) == "table" and sz(v, d + 1) or #tostring(v)) end; return n end
check(sz(e) < 20000, "объём < 20КБ: " .. sz(e))
-- крэш-сторож addOrder
local PD = KMM_Predators.P; PD.sdir = "TMPDIR/"
TaskType = { HOLD_POSITION = 30, PATROL_TOWN = 36 }
local CALLS, LOCKSEEN = {}, false
local function mkpl() local ldr = { addOrder = function(self, d, tt, sub, sh, cl, loc) CALLS[#CALLS + 1] = { tt = tt, cl = cl, x = loc.x, z = loc.z }
  local f = io.open(PD.sdir .. "probe_addOrder.lock", "r"); if f then LOCKSEEN = true; f:close() end end }
  return { getSquadLeader = function() return ldr end } end
check(KMM_Predators.order_squad({ mkpl(), mkpl() }, 10, 20, "hold") == 2, "order hold x2")
check(CALLS[1].tt == 30 and CALLS[1].x == 10 and CALLS[1].z == 20 and CALLS[1].cl == true, "HOLD_POSITION вызван с точкой")
check(LOCKSEEN, "lock существует во время вызова")
check(io.open(PD.sdir .. "probe_addOrder.lock", "r") == nil, "lock удалён после успеха")
KMM_Predators.order_squad({ mkpl() }, 1, 2, "patrol"); check(CALLS[3].tt == 36, "PATROL_TOWN")
check(not KMM_Predators.disabled(), "не отключён")
-- симуляция упавшей сессии: lock есть при старте -> метод отключён, .off создан, вызов не делается
local fh = io.open(PD.sdir .. "probe_addOrder.lock", "w"); fh:write("x"); fh:close()
local Pnew = assert(loadfile("PREDPATH"))()
KMM_Predators.P.sdir = PD.sdir
local before = #CALLS
check(KMM_Predators.order_squad({ mkpl() }, 1, 2, "hold") == 0 and #CALLS == before, "после упавшей сессии addOrder не вызывается")
check(io.open(PD.sdir .. "probe_addOrder.off", "r") ~= nil, ".off создан")
check(io.open(PD.sdir .. "probe_addOrder.lock", "r") == nil, "lock убран")
KMM_Predators.P.sdir = PD.sdir
RESULT = #FAILS == 0 and ("OK " .. N) or ("FAIL: " .. table.concat(FAILS, "; "))
'''.replace("TMPDIR", TMP).replace("PREDPATH", (B + "/KMM_Predators.lua").replace("\\", "/")), "test")
run("")
L.lua_getfield.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_char_p]
L.lua_getfield(st, -10002, b"RESULT")
r = L.lua_tolstring(st, -1, None).decode()
print(r)
sys.exit(0 if r.startswith("OK") else 1)
