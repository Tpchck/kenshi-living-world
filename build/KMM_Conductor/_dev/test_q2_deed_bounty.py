"""Q2 offline test KMM_Outlaws: deeds bus (type="deed") -> vanilla bounty on the wanted leader (o.bb + unfairAddToBounty on the live
leader), dedup / day cap / ceiling / lawless and by_player skipped, outlaw_deed rumor, markers; manhunt patrol gets addGoal(HUNT_BOUNTIES).
python -I -X utf8 build/KMM_Conductor/_dev/test_q2_deed_bounty.py -> OK."""
import ctypes, re, sys, tempfile

DLL = r"C:\Program Files (x86)\Steam\steamapps\workshop\content\233860\3817000612\lua51.dll"
B = r"C:\KenshiModMap\build\KMM_Conductor\scripts\init"
TMP = tempfile.mkdtemp(prefix="kmm_q2_").replace("\\", "/")
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
run(open(B + r"\KMM_Traces.lua", encoding="utf-8").read(), "KMM_Traces.lua")
run(open(B + r"\KMM_Fates.lua", encoding="utf-8").read(), "KMM_Fates.lua")
run(open(B + r"\KMM_Outlaws.lua", encoding="utf-8").read(), "KMM_Outlaws.lua")
run(r'''
N, FAILS = 0, {}
function check(c, what) N = N + 1; if not c then FAILS[#FAILS + 1] = what end end
TaskType = TaskType or {}
TaskType.HUNT_BOUNTIES = TaskType.HUNT_BOUNTIES or 204
local C = KMM_Conductor
C.reset()
local TP = C.cfg().params.traces
TP.first_hour_traces = 0; TP.max_per_day = 1000; TP.max_queue = 1000; TP.arrive_enabled = false
TP.bounty = { enabled = false }
TP.wx_ext_reject = 0; TP.ext_per_day = 1000; TP.ext_per_tag = 1000   -- без случайных отказов EXT (буря/лимиты) — иначе тест плавает
local pf = C.cfg().player_faction or "player"
C.cfg().params.outlaws = { watch_s = 1e9, sdir = "TMPDIR/", max_live = 10, cd_h = 0 }   -- заявка первого тика (другое имя, тот же тег) не должна занимать лимит живых и блокировать повтор
local O, T = KMM_Outlaws, KMM_Traces
local M = O._M
LOGS = {}
M.log = function(m) LOGS[#LOGS + 1] = tostring(m) end
local function logged(s) for _, l in ipairs(LOGS) do if l:find(s, 1, true) then return true end end; return false end
MADE = {}
local old = getGameWorld
getGameWorld = function()
  local w = old()
  local orig = w.theFactory.createRandomSquad
  w.theFactory.createRandomSquad = function(self, f, pos, ...)
    local r = orig(self, f, pos, ...)
    local leader = { name = "Nameless Raider", dead = false, bty = {}, goals = {} }
    leader.crimes = { unfairAddToBounty = function(self2, fo, amt) leader.bty[#leader.bty + 1] = { fo, amt } end,
                      getTotalBounty = function(self2) local s = 0; for _, b in ipairs(leader.bty) do s = s + b[2] end; return s end,
                      getBountyRecognitionThreshold = function() return 500 end }
    function leader:setName(n) self.name = n end
    function leader:getName() return self.name end
    function leader:isDead() return self.dead end
    function leader:addGoal(t, subj) self.goals[#self.goals + 1] = { t, subj } end
    local pl = { isDead = false }
    function pl:getSquadLeader() return leader end
    function pl:getActivePlatoon() return { setName = function() end } end
    MADE[#MADE + 1] = { pl = pl, leader = leader, fid = f.id }
    return pl
  end
  if not w.factionMgr then w.factionMgr = {} end
  if not w.factionMgr.getFactionByStringID then w.factionMgr.getFactionByStringID = function(self, sid) return { id = sid } end end
  return w
end
PCS = {}; CHARS = {}
local pc = MKCH("PC1", pf, 0, 0, { player = true, platoon = "player_squad" })
PCS[1] = pc; CHARS[1] = pc
local function tick(day) DAYV = day; CLOCK = CLOCK + 100; FIRE("GameWorld::charsUpdate", {}) end
OEV = {}
C.subscribe("outlaw_*", function(ev) OEV[#OEV + 1] = ev end)
tick(500)
local D = M.data(C)
check(M.sub_id and M.sub_id ~= false, "deed bus subscribed: " .. tostring(M.sub_id))
check(logged("deed bus subscribed"), "marker: deed bus subscribed")
-- живой главарь у игрока
local hero; for _, o in ipairs(O.wanted()) do if o.st == "a" and #((D.regions[o.r] or {}).towns or {}) > 0 and M.tier_sid(D, o.g, o.t) then hero = o; break end end
check(hero ~= nil, "outlaw with a town region")
for _, o in ipairs(O.wanted()) do if o ~= hero then o.x = (o.x or 0) + 9e6 end end
hero.sp = -1000; M.live = {}; M.pend = nil
PCS = {}; CHARS = {}
pc = MKCH("PC1", pf, hero.x + 300, hero.z + 300, { player = true, platoon = "player_squad" })
PCS[1] = pc; CHARS[1] = pc
local function shove() for _, o in ipairs(O.wanted()) do if o ~= hero and (o.x or 0) < 5e6 then o.x = (o.x or 0) + 9e6 end end end   -- новые имена (рождённые в тиках) — тоже прочь от игрока
for i = 1, 40 do shove(); tick(500); if M.live["o" .. hero.i] then break end; CLOCK = CLOCK + 80 end
local lv = M.live["o" .. hero.i]
check(lv and lv.named, "hero gang live and named")
local made; for i = #MADE, 1, -1 do if MADE[i].leader.name == hero.n then made = MADE[i]; break end end
check(made ~= nil, "leader found")
check(logged("native bounty ok on"), "marker: native bounty ok on spawn")
local victim
for _, t in ipairs(D.regions[hero.r].towns) do if t.fid ~= hero.g then victim = t.fid; break end end
check(victim and M.lawful(D, victim), "victim is lawful town owner: " .. tostring(victim))
local function deed(kind, extra)
  local ev = { type = "deed", kind = kind, tone = "harm", a = hero.g, b = victim, n = 1, x = hero.x + 300, z = hero.z + 300, town_name = "Testtown" }
  if extra then for k, v in pairs(extra) do ev[k] = v end end
  C.emit(ev)
end
local b0, nb0, ev0 = hero.b, #made.leader.bty, #OEV
deed("killed")
check(hero.b > b0, "killed raises bounty: " .. b0 .. " -> " .. hero.b)
check(#made.leader.bty == nb0 + 1 and made.leader.bty[#made.leader.bty][2] == hero.b - b0, "native unfairAddToBounty with the increment")
local lf = M.law(victim)
check(made.leader.bty[#made.leader.bty][1].id == lf, "bounty from victim's law faction")
local de; for i = ev0 + 1, #OEV do if OEV[i].type == "outlaw_deed" then de = OEV[i] end end
check(de and de.deed == "killed" and de.b == victim and tostring(de.text):find(hero.n, 1, true), "outlaw_deed rumor emitted")
check(logged("deed bounty +") and logged("native ok"), "marker: deed bounty + native ok")
check((hero.cr.murder or 0) >= 1, "murder counted toward epithet")
local b1 = hero.b
deed("killed")
check(hero.b == b1 and (O.stats().deed_dup or 0) == 1, "same deed same day deduped")
deed("killed", { by_player = true }); deed("killed", { to_player = true })
check(hero.b == b1, "player deeds ignored")
deed("aided")
check(hero.b == b1, "help deeds ignored")
deed("executed")
local b2 = hero.b
check(b2 > b1, "executed raises bounty")
deed("captured")
check(hero.b == b2 and (O.stats().deed_capped or 0) >= 1, "day cap (deed_day=2)")
-- новый день: потолок
DAYV = 501
hero.b = 69950
deed("captured")
check(hero.b <= 70000 and hero.b > 69950, "ceiling deed_cap holds: " .. hero.b)
deed("killed")
check(hero.b <= 70000, "at ceiling no growth")
-- беззаконная жертва
DAYV = 502
local lawless
for fid in pairs(D.gangs or {}) do if not M.lawful(D, fid) and fid ~= hero.g then lawless = fid; break end end
if lawless then
  local bl = hero.b
  hero.b = 1000; bl = hero.b
  local sv = victim; victim = lawless
  deed("killed")
  victim = sv
  check(hero.b == bl and (O.stats().deed_lawless or 0) >= 1, "lawless victim gives no bounty")
end
-- не живой, далеко от места: не приписывается
M.live = {}
local far = hero; local bf = far.b
C.emit({ type = "deed", kind = "killed", a = hero.g, b = victim, n = 1, x = hero.x + 9e6, z = hero.z + 9e6 })
check(far.b == bf, "far, not live outlaw not blamed")
-- не живой, рядом: награда растёт в o.bb (ядро — при выходе банды)
DAYV = 503
C.emit({ type = "deed", kind = "killed", a = hero.g, b = victim, n = 1, x = hero.x + 100, z = hero.z + 100 })
check(hero.b > bf and logged("native later"), "near, not live: bounty grows, native later")
check(next(O.disabled()) == nil and not M.deed_off, "module and deed link still enabled")
-- облава: патрулю ванильная цель HUNT_BOUNTIES
local lawf; for fid, e in pairs(D.tr) do if e.tiers and e.tiers.T1 then lawf = fid; break end end
O.state().hunt = { test = { u = 99999, r = "x", lf = lawf, x = hero.x + 200, z = hero.z + 200, tn = "Testtown", oi = -1 } }
M.pend = nil
local nm0 = #MADE
for i = 1, 30 do CLOCK = CLOCK + 80; FIRE("GameWorld::charsUpdate", {}) end
local goal
for i = nm0 + 1, #MADE do for _, g in ipairs(MADE[i].leader.goals) do if g[1] == 204 then goal = true end end end
check(goal, "manhunt patrol got addGoal(HUNT_BOUNTIES)")
check(logged("hunt goal HUNT_BOUNTIES ok"), "marker: hunt goal ok")
RESULT = #FAILS == 0 and ("OK " .. N) or ("FAIL: " .. table.concat(FAILS, "; "))
'''.replace("TMPDIR", TMP), "test")
L.lua_getfield.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_char_p]
L.lua_getfield(st, -10002, b"RESULT")
r = L.lua_tolstring(st, -1, None).decode()
print(r)
sys.exit(0 if r.startswith("OK") else 1)
