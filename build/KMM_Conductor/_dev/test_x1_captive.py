"""X1 offline test KMM_Outlaws: hunter carries a wanted NPC alive near the player -> outlaw_captive_carried (once per captive,
day cap, filters: dead / no bounty / same faction / far / player captive); player carries the captive -> outlaw_captive_taken once +
KMM_Nemesis.remember(hunter re-found in a fresh KMM_Gov snapshot, LT_STOLE_FROM_ME); expiry -> captive gone; session state holds
only strings/numbers (no engine pointers between ticks); world change resets; scan is chunked (cap_chars per scan); error -> only X1 off.
python -I -X utf8 build/KMM_Conductor/_dev/test_x1_captive.py -> OK."""
import ctypes, re, sys, tempfile

DLL = r"C:\Program Files (x86)\Steam\steamapps\workshop\content\233860\3817000612\lua51.dll"
B = r"C:\KenshiModMap\build\KMM_Conductor\scripts\init"
TMP = tempfile.mkdtemp(prefix="kmm_x1_").replace("\\", "/")
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
run("math.randomseed(20261115)", "seed")
for _f in sorted(__import__("glob").glob(B + r"\KMM_Conductor*.lua")): run(open(_f, encoding="utf-8").read(), _f.split("\\")[-1])
run(open(B + r"\KMM_Gov.lua", encoding="utf-8").read(), "KMM_Gov.lua")
run(open(B + r"\KMM_Outlaws.lua", encoding="utf-8").read(), "KMM_Outlaws.lua")
run(r'''
N, FAILS = 0, {}
function check(c, what) N = N + 1; if not c then FAILS[#FAILS + 1] = what end end
local C = KMM_Conductor
C.reset()
local pf = C.cfg().player_faction or "player"
C.cfg().params.outlaws = { sdir = "TMPDIR/", spawn_p = 0, cap_scan_s = 15 }
local M = KMM_Outlaws._M
LOGS2 = {}
M.log = function(m) LOGS2[#LOGS2 + 1] = tostring(m) end
local function logged(s) for _, l in ipairs(LOGS2) do if l:find(s, 1, true) then return true end end; return false end
EV = {}
local emit0 = C.emit
C.emit = function(ev) if type(ev.type) == "string" and ev.type:find("^outlaw_captive") then EV[#EV + 1] = ev end; return emit0(ev) end
local function evs(t) local n = 0; for _, e in ipairs(EV) do if e.type == t then n = n + 1 end end; return n end
local function last(t) for i = #EV, 1, -1 do if EV[i].type == t then return EV[i] end end end
REM = {}
KMM_Nemesis = { remember = function(ch, tag) REM[#REM + 1] = { ch = ch, tag = tag } end }

-- пленник: NPC с наградой ядра; hand по значению (новая копия на каждый вызов), toString — ключ объекта
local function captive(nm, fid, bounty, opt)
  local c = MKCH(nm, fid, 0, 0, opt)
  c.crimes = { getTotalBounty = function() return bounty end }
  return c
end
local function hand_of(cap) return function() return { getCharacter = function() return cap end, toString = function() return "hand:" .. cap:getName() end } end end
local function hunter(nm, fid, x, z, cap, plat)
  local h = MKCH(nm, fid, x, z, { platoon = plat or ("hp_" .. nm) })
  h.isCarryingSomething = cap ~= nil
  if cap then h.getCarryingObject = hand_of(cap) end
  return h
end
local pc = MKCH("Nameless", pf, 0, 0, { player = true, platoon = "player_squad" })
PCS = { pc }
local Y = captive("Grax Bonecutter", "band_f", 3000)
local H = hunter("Hunter Kel", "hunters_f", 600, 0, Y, "hunt_sq1")
CHARS = { H, MKCH("idle", "town_f", 100, 0) }
local function tick(dt) DAYV = DAYV; CLOCK = CLOCK + (dt or 20); FIRE("GameWorld::charsUpdate", {}) end
DAYV = 3
tick()
check(evs("outlaw_captive_carried") == 1, "carried event emitted once")
local e = last("outlaw_captive_carried")
check(e and e.a == "hunters_f" and e.who == "Grax Bonecutter" and e.b == "band_f", "event fields a/who/b")
check(e and type(e.town_name) == "string" and e.town_name ~= "" and e.text and e.text:find("Grax Bonecutter", 1, true) and e.text:find("3000", 1, true), "town_name + text")
check(e and type(e.x) == "number" and type(e.z) == "number", "event has x/z for Rumors map hint")
check(e and (e.leader_name == nil or e.leader_name == ""), "no leader_name: Rumors mapSquad must not mark the outlaw gang")
check(logged("captive carried: Grax Bonecutter"), "marker captive carried")
check(logged("captive scan: "), "marker captive scan (probe once)")
for _ = 1, 4 do tick() end
check(evs("outlaw_captive_carried") == 1, "same captive: no second event")
-- нет указателей между тактами: только строки/числа/булевы
local bad = 0
for k, v in pairs(M.cap.seen) do
  if type(k) ~= "string" then bad = bad + 1 end
  for _, x in pairs(v) do if type(x) ~= "string" and type(x) ~= "number" and type(x) ~= "boolean" then bad = bad + 1 end end
end
check(bad == 0, "session state holds no engine objects")

-- фильтры
local D1 = captive("Dead Man", "band_f", 5000); D1.dead = true
local Z0 = captive("Clean Joe", "band_f", 0)
local SF = captive("Own Mate", "hunters_f", 2000)
local FAR = captive("Far Guy", "band_f", 2000)
local PCC = MKCH("Player Two", pf, 0, 0, { player = true }); PCC.crimes = { getTotalBounty = function() return 9000 end }
CHARS = { H, hunter("h2", "hunters_f", 500, 100, D1), hunter("h3", "hunters_f", 500, 200, Z0), hunter("h4", "hunters_f", 500, 300, SF),
          hunter("h5", "hunters_f", 30000, 0, FAR), hunter("h6", "hunters_f", 400, 0, PCC) }
tick(); tick()
check(evs("outlaw_captive_carried") == 1, "filters: dead / zero bounty / same faction / far / player captive -> no event")

-- дневной лимит cap_day=3: два новых пленника дают события, третий новый — уже нет
local c2, c3, c4 = captive("A2", "band_f", 1000), captive("A3", "band_f", 1000), captive("A4", "band_f", 1000)
CHARS = { H, hunter("k2", "hunters_f", 500, 0, c2), hunter("k3", "hunters_f", 500, 0, c3), hunter("k4", "hunters_f", 500, 0, c4) }
tick(); tick()
check(evs("outlaw_captive_carried") == 3, "day cap 3 events (got " .. evs("outlaw_captive_carried") .. ")")
check(logged("captive carried (no event, day cap)"), "day cap marker")

-- M2: игрок несёт другого персонажа с тем же родовым именем (другой hand) - не перехват, памяти нет
local Y2 = captive("Grax Bonecutter", "band_f", 100)
pc.getCarryingObject = function() return { getCharacter = function() return Y2 end, toString = function() return "hand:other" end } end
tick()
check(evs("outlaw_captive_taken") == 0 and #REM == 0, "same name, other hand -> no taken / no LT_STOLE_FROM_ME")
check(M.cap_match({ who = "X" }, nil, "X") and not M.cap_match({ who = "X", hk = "h1" }, nil, "X") and not M.cap_match({ who = "X" }, "h2", "X"), "name fallback only without hands")
pc.getCarryingObject = nil
-- игрок отбил: пленник на плечах персонажа игрока -> taken один раз + память охотника (охотник найден заново в свежем снимке)
H.isCarryingSomething = false; H.getCarryingObject = function() return { getCharacter = function() return nil end, toString = function() return "" end } end
CHARS = { H }
pc.getCarryingObject = hand_of(Y)
tick()
check(evs("outlaw_captive_taken") == 1, "taken event once")
local t = last("outlaw_captive_taken")
check(t and t.who == "Grax Bonecutter" and t.a == "hunters_f" and t.by_player == true and t.text:find("Nameless", 1, true), "taken fields + text")
check(#REM == 1 and REM[1].ch == H and REM[1].tag == "LT_STOLE_FROM_ME", "Nemesis.remember on hunter LT_STOLE_FROM_ME")
check(logged("captive taken: Grax Bonecutter") and logged("captive memory: Hunter Kel"), "markers taken + memory")
pc.getCarryingObject = function() return { getCharacter = function() return nil end } end
tick()
pc.getCarryingObject = hand_of(Y)
tick()
check(evs("outlaw_captive_taken") == 1 and #REM == 1, "drop and pick again: no second taken / memory")
-- охотник выгружен/мёртв -> память пропущена, событие есть
pc.getCarryingObject = hand_of(c2)
H.dead = true
CHARS = {}
tick()
check(evs("outlaw_captive_taken") == 2 and #REM == 1 and logged("captive memory skipped"), "hunter not in snapshot: taken, memory skipped")

-- срок слежения: запись уходит с маркером gone
pc.getCarryingObject = nil; PCS = { MKCH("Nameless", pf, 0, 0, { player = true, platoon = "player_squad" }) }
CLOCK = CLOCK + 2000; tick()
local left = 0; for _ in pairs(M.cap.seen) do left = left + 1 end
check(left == 0 and logged("captive gone: A3"), "expiry -> captive gone, seen emptied")

-- смена мира: сессионное состояние сбрасывается
M.cap.seen.zzz = { who = "x", last = CLOCK }
C.reset(); tick()
check(M.cap == nil or M.cap.seen.zzz == nil, "world change resets captive state")

-- порции: из 3000 загруженных за скан читается не больше cap_chars (400)
local reads = 0
local big = {}
for i = 1, 3000 do
  local c = MKCH("n" .. i, "town_f", 50, 0)
  setmetatable(c, { __index = function(_, k) if k == "isCarryingSomething" then reads = reads + 1; return false end end })
  big[i] = c
end
CHARS = big
CLOCK = CLOCK + 100; tick()
check(reads > 0 and reads <= 400, "chunked scan: field reads " .. reads .. " <= 400")
local cur = M.cap.cur
CLOCK = CLOCK + 100; tick()
check(M.cap.cur ~= cur, "cursor advances between scans")

-- без снимка Gov: простой, без ошибок; ошибка в шаге — выключается только X1
local snap0 = KMM_Gov.snapshot
KMM_Gov.snapshot = function() return nil end
M.cap.t = -1e9; CLOCK = CLOCK + 100; tick()
check(logged("captive scan idle") and not M.cap_off and not M.off, "no snapshot: idle, module alive")
KMM_Gov.snapshot = snap0
local st0 = M.cap_step
M.cap_step = function() error("boom") end
CLOCK = CLOCK + 100; tick()
check(M.cap_off == true and not M.off and logged("captive watch disabled"), "error disables only X1")
M.cap_step = st0
'''.replace("TMPDIR", TMP), "test")
run(r'''
local f = io.open("TMPDIR/x1_result.txt", "w")
f:write(N, "\n", table.concat(FAILS, "\n")); f:close()
'''.replace("TMPDIR", TMP), "dump")
res = open(TMP + "/x1_result.txt", encoding="utf-8").read().split("\n")
n, fails = int(res[0]), [x for x in res[1:] if x]
for x in fails:
    print("FAIL", x)
print(f"test_x1_captive: {n - len(fails)}/{n}")
print("OK" if not fails else "FAILED")
sys.exit(1 if fails else 0)
