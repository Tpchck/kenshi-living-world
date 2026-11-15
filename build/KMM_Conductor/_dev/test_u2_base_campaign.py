"""Offline test U2: рейд на базу игрока = родная кампания движка (CA.base_try/CA.base_step), исход из фазы CampaignInstance.
python -I -X utf8 build/KMM_Conductor/_dev/test_u2_base_campaign.py -> OK N."""
import ctypes, re, sys, tempfile

DLL = r"C:\Program Files (x86)\Steam\steamapps\workshop\content\233860\3817000612\lua51.dll"
B = r"C:\KenshiModMap\build\KMM_Conductor\scripts\init"
TMP = tempfile.mkdtemp(prefix="kmm_u2_").replace("\\", "/")
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
TEST = r'''
N, FAILS = 0, {}
function check(c, what) N = N + 1; if not c then FAILS[#FAILS + 1] = what end end
local C, T = KMM_Conductor, KMM_Traces
C.reset()
local P = C.cfg().params
P.campaign.sdir = "TMPDIR/"
P.campaign.p_raid, P.campaign.p_capture = 0, 0
P.guard = P.guard or {}; P.guard.debug_log = "TMPDIR/debug.log"
P.traces.first_hour_traces = 0
local S = C.state()
local pf = C.cfg().player_faction
local CA = C.camp()
local D = C.read_json("campaigns.json", "C:/KenshiModMap/build/KMM_Conductor/campaigns.json")
local function usable(fid) local e = D.factions[fid]; if not e then return false end
  for _, k in ipairs({ "raid", "assault" }) do for _, sid in ipairs(e[k] or {}) do local c = D.campaigns[sid]; if c and c.ws == 0 and c.forces <= 30 then return true end end end end
local ids = {}; for fid in pairs(S.F) do ids[#ids + 1] = fid end; table.sort(ids)
local A, Z
for _, fid in ipairs(ids) do local f = S.F[fid]
  if f.alive and not f.player and fid ~= pf and C.fpos(fid) then
    if not A and usable(fid) then A = fid elseif not Z and not D.factions[fid] then Z = fid end
  end
end
check(A, "attacker with FACTION_CAMPAIGN found")
local ax, az = C.fpos(A)
local BX, BZ = ax + 3000, az
C.set_base(BX, BZ, 100, 10)
TRIG, UID, QUEUE_OK = {}, 500, true
local fa = FAC(A); fa.warMgr.activeCampaigns = {}
local wa = fa.warMgr
wa.triggerCampaign = function(self, target, gd, mn, mx, home, dup, tf)
  TRIG[#TRIG + 1] = { gd = gd, target = target, home = home, tf = tf }
  if QUEUE_OK then UID = UID + 1; local inst = { uniqueID = UID, enemy = FAC(pf), currentPhase = 0, manPowerLastCount = 18 }; wa.activeCampaigns[#wa.activeCampaigns + 1] = inst; LAST = inst end
end
local function drop(inst) for i, v in ipairs(wa.activeCampaigns) do if v == inst then table.remove(wa.activeCampaigns, i); return end end end
local atbase = MKCH("PC1", pf, BX + 200, BZ, { player = true, platoon = "player_squad" })
local nearby = MKCH("PC2", pf, BX + 9000, BZ, { player = true, platoon = "player_squad" })   -- зона базы загружена, но у базы никого
local far = MKCH("PC3", pf, BX + 900000, BZ, { player = true, platoon = "player_squad" })
E0 = 0
local function evs(ty) local n = 0; for _, e in ipairs(S.events) do if e.id > E0 and e.type == ty and e.a == A then n = n + 1 end end; return n end
local function nbr() local n = 0; for _, j in ipairs(T.queue()) do if j.kind == "base_raid" then n = n + 1 end end; return n end
local function dlog() local f = io.open("TMPDIR/debug.log", "r"); if not f then return "" end; local s = f:read("*a"); f:close(); return s end
local function fresh() E0 = (#S.events > 0) and S.events[#S.events].id or 0; S.ncamp = nil; S.bcamp = nil; S.base.last_raid = nil; S.F[A].alive = true end
local function raid() C.act_test(A, "raid_base", "greed") end   -- без опроса: привязка должна случиться сразу в base_try
local function step(days) local R = S.bcamp; if R and days then R.day = R.day - days end; CA.base_step() end
-- 1. игрок у базы: кампания, без колонны Traces; VICTORY при игроке -> разграблена
fresh(); PCS = { atbase }; CHARS = { atbase }
local w0 = S.F[A].wealth
S.base.def_bonus, S.base.def_bonus_day = 8, 0
raid()
check(#TRIG == 1 and TRIG[1].tf == FAC(A) and TRIG[1].gd and TRIG[1].target and TRIG[1].home, "triggerCampaign via CA.fire: " .. #TRIG)
check(evs("base_campaign") == 1 and evs("base_raid") == 0, "event base_campaign (native), no base_raid")
local bc; for _, e in ipairs(S.events) do if e.type == "base_campaign" then bc = e end end
check(bc and bc.native == true and bc.campaign, "base_campaign native=true with campaign sid")
check(nbr() == 0 and bc and bc.type ~= "base_raid", "native base_campaign: Traces has no base_raid job (KMM_Traces.on_event skips native events)")
check(S.bcamp and S.bcamp.st == "bound" and S.bcamp.cid == LAST.uniqueID, "bound to CampaignInstance right after fire (no poll)")
check(S.ncamp and S.ncamp.f[A], "CA.note: world limits")
check(dlog():find("campaign: triggerCampaign ok base " .. A, 1, true), "marker campaign: triggerCampaign ok base")
LAST.currentPhase = 1; step()
check(S.bcamp and S.bcamp.present, "player at base during assault")
LAST.currentPhase = 3; step()
check(S.bcamp == nil and evs("base_raid_sacked") == 1, "VICTORY + player -> base_raid_sacked")
check(S.F[A].wealth > w0 and (S.base.def_bonus or 0) == 0, "plunder and defense bonus burned")
check(dlog():find("campaign: base outcome " .. A .. ": sacked (phase VICTORY)", 1, true), "marker outcome sacked")
drop(LAST)
-- 2. RETREATING -> отбит: бонус обороны растёт
fresh()
local d0 = C.state().base.def_bonus or 0
raid(); LAST.currentPhase = 1; step(); LAST.currentPhase = 2; step()
check(evs("base_raid_repelled") == 1 and (S.base.def_bonus or 0) > d0, "RETREATING -> repelled, defense bonus up")
drop(LAST)
-- 3. зона загружена, у базы никого; VICTORY -> никого не было (абстрактная добыча)
fresh(); PCS = { nearby }; CHARS = { nearby }
w0 = S.F[A].wealth
raid(); LAST.currentPhase = 1; step(); LAST.currentPhase = 3; step()
check(evs("base_raid_unattended") == 1 and evs("base_raid_sacked") == 0 and S.F[A].wealth > w0, "VICTORY, nobody home -> unattended")
drop(LAST)
-- 4. кампания исчезла посреди штурма, игрок у базы -> отбит
fresh(); PCS = { atbase }; CHARS = { atbase }
raid(); LAST.currentPhase = 1; step(); drop(LAST); step()
check(evs("base_raid_repelled") == 1 and S.bcamp == nil, "vanished mid-assault with player -> repelled")
-- 5. рассыпалась в GATHERING -> без исхода
fresh()
raid(); drop(LAST); step()
check(S.bcamp == nil and evs("base_raid_repelled") + evs("base_raid_unattended") + evs("base_raid_sacked") == 0, "faded while gathering: no outcome")
-- 6. очередь не дала экземпляр -> ни одного события, пока ждём; через bind_days единственное событие base_raid (Traces)
fresh(); QUEUE_OK = false
local nt = #TRIG
raid(); step(1)
check(S.bcamp and S.bcamp.st == "fired" and evs("base_campaign") + evs("base_raid") == 0, "waiting for instance, no announcement yet")
step(5)
check(#TRIG == nt + 1 and S.bcamp == nil and evs("base_raid") == 1 and evs("base_campaign") == 0, "never started -> one base_raid, no base_campaign")
-- 6b. экземпляр появился позже (очередь движка) -> привязка в опросе, одно событие base_campaign
fresh()
raid()
UID = UID + 1; LAST = { uniqueID = UID, enemy = FAC(pf), currentPhase = 0, manPowerLastCount = 12 }; wa.activeCampaigns[#wa.activeCampaigns + 1] = LAST
step()
check(S.bcamp and S.bcamp.st == "bound" and S.bcamp.cid == UID and evs("base_campaign") == 1 and evs("base_raid") == 0, "late instance bound by poll, one event")
drop(LAST); S.bcamp = nil
-- 6c. M4: новая кампания фракции против другого врага или с непрочитанным enemy - не наша
fresh()
raid()
local other = Z or ids[1]
UID = UID + 1; local foreign = { uniqueID = UID, enemy = FAC(other), currentPhase = 1 }; wa.activeCampaigns[#wa.activeCampaigns + 1] = foreign
UID = UID + 1; local noenemy = { uniqueID = UID, currentPhase = 1 }; wa.activeCampaigns[#wa.activeCampaigns + 1] = noenemy
step()
check(S.bcamp and S.bcamp.st == "fired" and S.bcamp.cid == nil, "foreign / enemy-less campaign not bound")
drop(foreign); drop(noenemy); S.bcamp = nil
QUEUE_OK = true
-- 7. игрок далеко -> кампании нет, старый путь base_raid
fresh(); PCS = { far }; CHARS = { far }
nt = #TRIG
raid()
check(#TRIG == nt and evs("base_raid") == 1 and evs("base_campaign") == 0 and S.bcamp == nil, "player far -> Traces base_raid")
check(dlog():find("not launched (player far)", 1, true), "fallback reason logged")
-- 8. ошибка движка при чтении activeCampaigns у привязанной кампании -> конец без второго рейда Traces, дирижёр жив
fresh(); PCS = { atbase }; CHARS = { atbase }
raid()
local saved = wa.activeCampaigns
wa.activeCampaigns = setmetatable({}, { __len = function() error("boom") end })
step()
check(S.bcamp == nil and evs("base_raid") == 0 and evs("base_campaign") == 1, "engine error after bind -> no fallback raid")
wa.activeCampaigns = saved; drop(LAST)
-- 8b. привязанная кампания висит дольше camp_max_days -> таймаут, без рейда Traces
fresh()
raid(); step(30)
check(S.bcamp == nil and evs("base_raid") == 0, "timeout after bind -> no fallback raid")
drop(LAST)
-- 8c. опрос из on_tick раз в poll_seconds реального времени (не раз в тик мира)
fresh()
raid()
CLOCK = CLOCK + 100; FIRE("GameWorld::charsUpdate", {})
LAST.currentPhase = 2
CLOCK = CLOCK + 5; FIRE("GameWorld::charsUpdate", {})
check(S.bcamp ~= nil and evs("base_raid_repelled") == 0, "on_tick: no poll before poll_seconds")
CLOCK = CLOCK + 30; FIRE("GameWorld::charsUpdate", {})
check(S.bcamp == nil and evs("base_raid_repelled") == 1, "on_tick: poll after poll_seconds -> repelled")
drop(LAST)
local wsn = {}; for _, e in ipairs(C.state() and KMM_C_INT.ws_phases(1) or {}) do wsn[e[1]] = true end
check(not wsn.base_camp, "base_camp no longer a world-tick phase")
-- 9. player_base.native=false -> только старый путь
fresh(); P.player_base.native = false
nt = #TRIG
raid()
check(#TRIG == nt and evs("base_raid") == 1, "native=false -> base_raid")
P.player_base.native = nil
-- 10. фракция без FACTION_CAMPAIGN -> base_raid
if Z then
  fresh(); S.F[Z].alive = true
  local n0 = #TRIG
  C.act_test(Z, "raid_base", "need")
  local n1 = 0; for _, e in ipairs(S.events) do if e.id > E0 and e.type == "base_raid" and e.a == Z then n1 = n1 + 1 end end
  check(n1 == 1 and #TRIG == n0, "no campaign data -> base_raid")
end
check(#C.serialize() > 0, "serialize")
check(next(C.disabled()) == nil, "conductor not disabled")
local function blog() local o = {}; for ln in dlog():gmatch("[^\n]+") do if ln:find("campaign: ", 1, true) and not ln:find("not launched", 1, true) then o[#o + 1] = ln:sub(21) end end; return table.concat(o, "\n") end
RESULT = #FAILS == 0 and ("OK " .. N) or ("FAIL: " .. table.concat(FAILS, "; ") .. " | log:\n" .. blog():sub(1, 3000))
'''
run(TEST.replace("TMPDIR", TMP), "test")
L.lua_getfield(st, -10002, b"RESULT")
r = L.lua_tolstring(st, -1, None).decode("utf-8", "replace")
print(r)
sys.exit(0 if r.startswith("OK") else 1)
