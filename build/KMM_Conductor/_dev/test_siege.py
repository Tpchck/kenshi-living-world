"""Offline test: KMM_Siege. python -I -X utf8 build/KMM_Conductor/_dev/test_slavecar.py -> OK."""
import ctypes, re, sys, tempfile

DLL = r"C:\Program Files (x86)\Steam\steamapps\workshop\content\233860\3817000612\lua51.dll"
B = r"C:\KenshiModMap\build\KMM_Conductor\scripts\init"
TMP = tempfile.mkdtemp(prefix="kmm_siege_").replace("\\", "/")
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
run(open(B + r"\KMM_Siege.lua", encoding="utf-8").read(), "KMM_Siege.lua")
run(r'''
N, FAILS = 0, {}
function check(c, what) N = N + 1; if not c then FAILS[#FAILS + 1] = what end end
local C, SG, T = KMM_Conductor, KMM_Siege, KMM_Traces
C.reset()
local TP = C.cfg().params.traces
TP.first_hour_traces = 0; TP.max_per_day = 1000; TP.max_queue = 1000; TP.arrive_enabled = false
TP.bounty = { enabled = false }
local S = C.state()
local pf = C.cfg().player_faction
-- пара фракций: у b >= 2 города (один город с координатами), a с позицией
local A, B, TW
local towns = C.towns()
for fid, f in pairs(S.F) do
  if f.alive and not f.player and fid ~= pf and C.fpos(fid) and not B then
    local n, cap = 0, nil
    for _, t in ipairs(towns) do if t.owner == fid and t.kind == "city" and t.x then n = n + 1; cap = cap or t end end
    if n >= 2 then B = fid; TW = cap end
  end
end
for fid, f in pairs(S.F) do if f.alive and not f.player and fid ~= pf and fid ~= B and C.fpos(fid) and T.tier_pick(fid, 0) and T.tier_pick(B, 0) and not A then A = fid end end
check(A and B and TW, "pair found")
local bx, bz = TW.x, TW.z
PCS = {}; CHARS = {}
local ch = MKCH("PC1", pf or "player", bx + 500, bz + 500, { player = true, platoon = "player_squad" })
PCS[1] = ch; CHARS[1] = ch
local function pump(n) for i = 1, n do CLOCK = CLOCK + 80; DAYV = DAYV + 0.02; FIRE("GameWorld::charsUpdate", {}) end end
-- заглушка родного города: warMgr.myTowns у владельца, setAlarmState пишет в ALARM
ALARM = {}
TownAlarmState = { ALARM_NONE = 0, ALARM_INTRUDER = 1, ALARM_ESCAPE = 2, ALARM_ATTACK = 3 }
local gw0 = getGameWorld
getGameWorld = function()
  local g = gw0()
  local fm = g.factionMgr
  g.factionMgr = { getFactionByStringID = function(self, id)
    local f = fm.getFactionByStringID(fm, id)
    local ow = {}; for k, v in pairs(f) do ow[k] = v end
    ow.warMgr = { myTowns = { { data = { stringID = TW.sid }, setAlarmState = function(self, v) ALARM[#ALARM + 1] = v end } } }
    return ow
  end }
  return g
end
local sdir = "C:/KenshiModMap/state/"
os.remove(sdir .. "probe_setAlarmState.lock"); os.remove(sdir .. "probe_setAlarmState.off")
-- склад города
local st = C.stock_state(); st.towns = st.towns or {}
st.towns[TW.sid] = { q = { food = 100, med = 100, weapons = 100 }, tn = { food = 100, med = 100, weapons = 100 }, lv = { food = 1, med = 1, weapons = 1 }, siege = -1 }
S.F[A].strength = 5000; S.F[B].strength = 100
SG.cfg.start_chance = 1; SG.cfg.min_days = 3; SG.cfg.max_days = 3
C.add_rel(A, B, -60)
pump(3)
local ntypes = function(ty) local n = 0; for _, e in ipairs(S.events) do if e.type == ty then n = n + 1 end end; return n end
-- не осаждать города игрока / игрока
check(SG.begin_manual(A, pf, nil) == false or SG.begin_manual(A, pf, nil) == nil, "no siege on player faction")
S.ext = S.ext or {}
C.emit({ type = "attack_repelled", a = A, b = B, town_sid = TW.sid, town_name = TW.name, text = "t" })
local x = SG.state(); LOGS = {}
SG.cfg.start_chance = 0
check(x and x.active[TW.sid], "siege started: " .. tostring(SG.disabled()))
check(ntypes("siege_started") == 1, "siege_started event")
-- второй атакующий этой же осады / тот же город
check(not SG.begin_manual(A, B, TW.sid), "one siege per attacker")
-- 3 дня
local n0 = #SPAWNS
local food0 = st.towns[TW.sid].q.food
-- караван в осаждённый город разворачивается
local r = C.road_state()
r.tr = r.tr or {}; r.tr[999] = { id = 999, eta = 99, d0 = 0, k = "caravan", f = B, from = "other_town", to = TW.sid, c = "food", n = 5 }
for d = 1, 5 do C.add_rel(A, B, -80); S.F[A].strength = 5000; DAYV = math.floor(DAYV) + 1.01; pump(2) end
check(r.tr[999] == nil or r.tr[999].to == "other_town", "caravan turned back")
check(st.towns[TW.sid].q.food < food0, "food drained")
check(st.towns[TW.sid].siege >= 0, "stock siege flag set")
check(ntypes("siege_progress") >= 1, "progress event")
check(#ALARM >= 1 and ALARM[1] == 3, "native alarm ATTACK set while siege near player: " .. #ALARM)
check(ALARM[#ALARM] == 0, "alarm reset to NONE at end of siege")
local f = io.open(sdir .. "probe_setAlarmState.lock", "r"); check(f == nil, "probe lock removed after success"); if f then f:close() end
local storm = false; for _, e in ipairs(S.events) do if e.type == "town_captured" and e.siege and e.town_sid == TW.sid then storm = true end end
check(storm, "storm: town_captured by siege")
S.F[A].towns[TW.sid] = true; S.F[B].towns[TW.sid] = nil
check(x.active[TW.sid] == nil, "siege finished")
check((x.cd[TW.sid] or 0) > C.day(), "cooldown set")
check(#SPAWNS > n0, "visible squads spawned: " .. (#SPAWNS - n0))
pump(60)
local tags = T.stats().by_tag or {}
check((tags.siege_besiegers or 0) >= 1 and (tags.siege_defenders or 0) >= 1, "ext tags " .. (tags.siege_besiegers or 0) .. "/" .. (tags.siege_defenders or 0) .. " q=" .. #T.queue())
-- кулдаун: повторный старт на этом городе нельзя
S.F[A].towns[TW.sid] = nil; S.F[B].towns[TW.sid] = true
check(not SG.begin_manual(A, B, TW.sid), "cooldown blocks")
-- сериализация
check(#C.serialize() > 0, "serialize")
-- лимит 2 одновременно
x.cd = {}
local cnt = 0
for fid, f in pairs(S.F) do if f.alive and not f.player and fid ~= pf and fid ~= B and C.fpos(fid) and SG.begin_manual(fid, B, nil) then cnt = cnt + 1 end end
check(cnt <= 2, "max 2 sieges: " .. cnt)
-- крэш-сторож: lock прошлой сессии -> .off, нативный вызов не делается
do
  local fl = io.open(sdir .. "probe_setAlarmState.lock", "w"); fl:write("x"); fl:close()
  local src = io.open("C:/KenshiModMap/build/KMM_Conductor/scripts/init/KMM_Siege.lua"):read("*a")
  assert(loadstring(src))()   -- новая сессия: PROBE пуст
  x = SG.state(); x.active = {}; x.cd = {}
  local n0a = #ALARM
  local sx = { a = A, b = B, town = TW.sid, tname = TW.name, day0 = 0, day_end = 99, prog = -1, vis = -1 }
  x.active[TW.sid] = sx
  SG.alarm_pulse(os.clock() + 1000)
  check(#ALARM == n0a, "lock present -> native call skipped")
  local fo = io.open(sdir .. "probe_setAlarmState.off", "r"); check(fo ~= nil, ".off written"); if fo then fo:close() end
  os.remove(sdir .. "probe_setAlarmState.off"); os.remove(sdir .. "probe_setAlarmState.lock")
  x.active = {}
end
local ev = {}; for _, e in ipairs(S.events) do ev[#ev+1] = e.type .. "@" .. e.day end; RESULT = #FAILS == 0 and ("OK " .. N) or (table.concat(ev, ",") .. " active=" .. tostring(next(x.active)) .. " "  .. "dis=" .. tostring(SG.disabled()) .. " last=" .. tostring(x.last) .. " day=" .. tostring(C.day()) .. " FAIL: " .. table.concat(FAILS, "; "))
''', "test")
run("")
L.lua_getfield.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_char_p]
L.lua_getfield(st, -10002, b"RESULT")
r = L.lua_tolstring(st, -1, None).decode()
print(r)
sys.exit(0 if r.startswith("OK") else 1)
