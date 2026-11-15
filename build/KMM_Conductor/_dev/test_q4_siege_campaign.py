"""Offline test Q4: KMM_Siege на родной кампании движка (FactionWarMgr:triggerCampaign + CampaignInstance.currentPhase).
python -I -X utf8 build/KMM_Conductor/_dev/test_q4_siege_campaign.py -> OK N."""
import ctypes, re, sys, tempfile

DLL = r"C:\Program Files (x86)\Steam\steamapps\workshop\content\233860\3817000612\lua51.dll"
B = r"C:\KenshiModMap\build\KMM_Conductor\scripts\init"
TMP = tempfile.mkdtemp(prefix="kmm_q4_").replace("\\", "/")
L = ctypes.CDLL(DLL)
L.luaL_newstate.restype = ctypes.c_void_p
for fn, at in [("luaL_openlibs", [ctypes.c_void_p]), ("luaL_loadstring", [ctypes.c_void_p, ctypes.c_char_p]),
               ("lua_pcall", [ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int])]:
    getattr(L, fn).argtypes = at
L.lua_tolstring.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p]
L.lua_tolstring.restype = ctypes.c_char_p
L.lua_getfield.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_char_p]
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
run(open(B + r"\KMM_Siege.lua", encoding="utf-8").read(), "KMM_Siege.lua")
TEST = r'''
N, FAILS = 0, {}
function check(c, what) N = N + 1; if not c then FAILS[#FAILS + 1] = what end end
local C, SG, T = KMM_Conductor, KMM_Siege, KMM_Traces
C.reset()
local P = C.cfg().params
local TP = P.traces
TP.first_hour_traces = 0; TP.max_per_day = 1000; TP.max_queue = 1000; TP.arrive_enabled = false; TP.bounty = { enabled = false }
P.campaign.sdir = "TMPDIR/"
P.campaign.p_raid, P.campaign.p_capture = 0, 0          -- сам дирижёр в тесте кампаний не запускает
SG.cfg.log = "TMPDIR/siege.log"; SG.cfg.native_alarm = false
SG.cfg.start_chance = 0; SG.cfg.min_days = 3; SG.cfg.max_days = 3
local S = C.state()
local pf = C.cfg().player_faction
local D = C.read_json("campaigns.json", "C:/KenshiModMap/build/KMM_Conductor/campaigns.json")
local function usable(fid) local e = D.factions[fid]; if not e then return false end
  for _, k in ipairs({ "assault", "raid" }) do for _, sid in ipairs(e[k] or {}) do local c = D.campaigns[sid]; if c and c.ws == 0 and c.forces <= 30 then return true end end end end
-- B: >= 2 городов с координатами, TW не столица; A: есть родная кампания assault/raid
local A, Bf, TW
local towns = C.towns()
local ids = {}; for fid in pairs(S.F) do ids[#ids + 1] = fid end; table.sort(ids)
for _, fid in ipairs(ids) do
  local f = S.F[fid]
  if not Bf and f.alive and not f.player and fid ~= pf and C.fpos(fid) then
    local cap = C.cfg().factions[fid] and C.cfg().factions[fid].capital
    local l = {}; for _, t in ipairs(towns) do if t.owner == fid and t.kind == "city" and t.x then l[#l + 1] = t end end
    if #l >= 2 then for _, t in ipairs(l) do if t.sid ~= cap and not TW then TW = t end end; if TW then Bf = fid end end
  end
end
for _, fid in ipairs(ids) do local f = S.F[fid]; if not A and f.alive and not f.player and fid ~= pf and fid ~= Bf and C.fpos(fid) and usable(fid) then A = fid end end
check(A and Bf and TW, "test factions found")
-- движок: triggerCampaign кладёт CampaignInstance в activeCampaigns (если QUEUE_OK), фаза правится тестом
TRIG, UID, QUEUE_OK = {}, 100, true
local function wm(id) local f = FAC(id); f.warMgr.activeCampaigns = f.warMgr.activeCampaigns or {}; return f.warMgr end
local wa = wm(A); wm(Bf)
wa.triggerCampaign = function(self, target, gd, mn, mx, home, dup, tf)
  TRIG[#TRIG + 1] = { gd = gd, target = target, home = home, tf = tf }
  if QUEUE_OK then UID = UID + 1; local inst = { uniqueID = UID, enemy = FAC(Bf), currentPhase = 0, manPowerLastCount = 24 }; wa.activeCampaigns[#wa.activeCampaigns + 1] = inst; LAST = inst end
end
local function drop(inst) for i, v in ipairs(wa.activeCampaigns) do if v == inst then table.remove(wa.activeCampaigns, i); return end end end
REQ = {}
local treq = T.request
T.request = function(r) REQ[#REQ + 1] = r.tag; return treq(r) end
local function sreq() local n = 0; for _, t in ipairs(REQ) do if t == "siege_besiegers" or t == "siege_storm" or t == "siege_defenders" then n = n + 1 end end; return n end
local near = MKCH("PC1", pf or "player", TW.x + 500, TW.z + 500, { player = true, platoon = "player_squad" })
local far = MKCH("PC2", pf or "player", TW.x + 900000, TW.z, { player = true, platoon = "player_squad" })
PCS = { near }; CHARS = { near }
local function pump(n) for i = 1, n do CLOCK = CLOCK + 80; DAYV = DAYV + 0.02; FIRE("GameWorld::charsUpdate", {}) end end
local function nextday() DAYV = math.floor(DAYV) + 1.01; pump(2) end
local function evs(ty, f) local l = {}; for _, e in ipairs(S.events) do if e.type == ty and e.town_sid == TW.sid and (not f or f(e)) then l[#l + 1] = e end end; return l end
local function slog() local f = io.open("TMPDIR/siege.log", "r"); if not f then return "" end; local s = f:read("*a"); f:close(); return s end
local function reset_pair(sa)
  S.ncamp = nil; for _, f in pairs(S.F) do if f.towns then f.towns[TW.sid] = nil end end; S.F[Bf].towns[TW.sid] = true
  S.F[A].alive, S.F[Bf].alive = true, true
  S.F[A].strength = sa; S.F[Bf].strength = 200; C.add_rel(A, Bf, -80)
  local x = SG.state(); x.active = {}; x.cd = {}
  S.events = {}
end
local x = SG.state()
pump(3)
-- 1. VICTORY родной кампании -> город пал, хотя бросок силы дал бы отход (атакующий слабый)
reset_pair(1)
check(SG.begin_manual(A, Bf, TW.sid), "siege 1 started")
local s = SG.state().active[TW.sid]
local r0 = sreq()
nextday()
check(#TRIG == 1 and TRIG[1].tf == FAC(A) and TRIG[1].gd.t == 93 and TRIG[1].target and TRIG[1].home, "campaign fired via conductor path: " .. #TRIG)
check(s.nat == "bound" and s.cid == LAST.uniqueID, "bound to CampaignInstance: " .. tostring(s.nat))
check(S.ncamp and S.ncamp.f[A], "conductor world limits noted (CA.note)")
LAST.currentPhase = 1
for d = 1, 4 do C.add_rel(A, Bf, -80); S.F[A].strength = 1; nextday() end
check(SG.state().active[TW.sid] == s, "bound siege outlives day_end (no roll): " .. tostring(SG.state().active[TW.sid]))
check(sreq() == r0, "no own Traces squads while native campaign holds the field: " .. (sreq() - r0))
local pr = evs("siege_progress", function(e) return e.native end)
check(#pr >= 1 and pr[1].phase == "ASSAULTING", "progress carries campaign phase")
LAST.currentPhase = 3
pump(2)
local cap = evs("town_captured", function(e) return e.siege end)
check(#cap == 1, "VICTORY -> town_captured: " .. #cap)
check(SG.state().active[TW.sid] == nil, "siege 1 finished")
check(slog():find("outcome from campaign " .. TW.sid .. ": storm", 1, true), "log marker: outcome from campaign")
drop(LAST)
-- 2. RETREATING -> осада снята, хотя атакующий сильный
reset_pair(5000)
check(SG.begin_manual(A, Bf, TW.sid), "siege 2 started")
s = SG.state().active[TW.sid]
nextday()
check(s.nat == "bound", "siege 2 bound")
LAST.currentPhase = 2
pump(2)
check(#evs("siege_lifted", function(e) return e.native and e.why == "withdraw" end) == 1 and #evs("town_captured") == 0, "RETREATING -> lifted, no capture")
drop(LAST)
-- 3. кампания исчезла посреди штурма -> осада окончена (ended)
reset_pair(5000)
SG.begin_manual(A, Bf, TW.sid); s = SG.state().active[TW.sid]
nextday(); LAST.currentPhase = 1; pump(2); drop(LAST); pump(2)
check(#evs("siege_lifted", function(e) return e.why == "ended" end) == 1, "vanished campaign -> ended")
-- 4. VICTORY, исчезнув до опроса фазы -> по последней виденной фазе
reset_pair(1)
SG.begin_manual(A, Bf, TW.sid); s = SG.state().active[TW.sid]
nextday(); LAST.currentPhase = 3; pump(2)
check(#evs("town_captured", function(e) return e.siege end) == 1, "VICTORY seen -> captured")
drop(LAST)
-- 5. очередь не дала экземпляр -> через bind_days фолбэк на бросок, отряды Traces снова ставятся
reset_pair(5000); QUEUE_OK = false
local nt = #TRIG
SG.begin_manual(A, Bf, TW.sid); s = SG.state().active[TW.sid]
r0 = sreq()
for d = 1, 5 do C.add_rel(A, Bf, -80); S.F[A].strength = 5000; nextday() end
check(#TRIG == nt + 1, "fired once")
check(s.nat == "lost" and SG.state().active[TW.sid] == nil, "not started -> lost -> finished by roll: " .. tostring(s.nat))
check(slog():find("fallback roll " .. TW.sid, 1, true), "log marker: fallback roll")
check(sreq() > r0, "fallback: own Traces squads")
QUEUE_OK = true
-- 6. игрок далеко -> не запускаем, бросок с причиной
reset_pair(5000); PCS = { far }; CHARS = { far }
nt = #TRIG
SG.begin_manual(A, Bf, TW.sid); s = SG.state().active[TW.sid]
for d = 1, 5 do C.add_rel(A, Bf, -80); nextday() end
check(#TRIG == nt and s.nat == nil, "far from player: no campaign")
check(slog():find("(campaign: player far)", 1, true), "fallback reason logged")
PCS = { near }; CHARS = { near }
-- 7. ошибка движка при чтении activeCampaigns -> фолбэк, модуль жив
reset_pair(5000)
SG.begin_manual(A, Bf, TW.sid); s = SG.state().active[TW.sid]
local saved = wa.activeCampaigns
wa.activeCampaigns = setmetatable({}, { __len = function() error("boom") end })
nextday()
check(s.nat == "lost" and not SG.disabled(), "engine error -> lost, module alive: " .. tostring(s.nat))
wa.activeCampaigns = saved
for d = 1, 4 do nextday() end
check(SG.state().active[TW.sid] == nil, "error case finished by roll")
-- 8. дирижёр уже запустил кампанию (событие native=true) -> осада привязывается к ней без второго запуска
reset_pair(5000)
UID = UID + 1; local pre = { uniqueID = UID, enemy = FAC(Bf), currentPhase = 0 }; wa.activeCampaigns[#wa.activeCampaigns + 1] = pre
nt = #TRIG
SG.cfg.start_chance = 1
C.emit({ type = "attack_repelled", a = A, b = Bf, town_sid = TW.sid, town_name = TW.name, native = true, text = "t" })
SG.cfg.start_chance = 0
s = SG.state().active[TW.sid]
check(s and s.nat == "fired", "native attack -> siege waits for conductor's campaign")
pump(2)
check(s and s.nat == "bound" and s.cid == pre.uniqueID and #TRIG == nt, "bound to existing campaign, no second trigger")
-- 9. native=false -> старая модель целиком
reset_pair(5000); SG.cfg.native = false
nt = #TRIG
SG.begin_manual(A, Bf, TW.sid); s = SG.state().active[TW.sid]
for d = 1, 5 do C.add_rel(A, Bf, -80); S.F[A].strength = 5000; nextday() end
check(#TRIG == nt and SG.state().active[TW.sid] == nil, "native=false: roll only")
SG.cfg.native = true
check(#C.serialize() > 0, "serialize")
check(not SG.disabled(), "module not disabled")
RESULT = #FAILS == 0 and ("OK " .. N) or ("FAIL: " .. table.concat(FAILS, "; ") .. " | log: " .. slog():sub(-600))
'''
run(TEST.replace("TMPDIR", TMP), "test")
L.lua_getfield(st, -10002, b"RESULT")
r = L.lua_tolstring(st, -1, None).decode("utf-8", "replace")
print(r)
sys.exit(0 if r.startswith("OK") else 1)
