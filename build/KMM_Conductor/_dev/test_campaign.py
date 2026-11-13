"""Offline test: native FACTION_CAMPAIGN (triggerCampaign), limits, crash guard lock/off, RelationData flags.
python -I -X utf8 build/KMM_Conductor/_dev/test_campaign.py -> OK."""
import ctypes, re, sys, tempfile

DLL = r"C:\Program Files (x86)\Steam\steamapps\workshop\content\233860\3817000612\lua51.dll"
B = r"C:\KenshiModMap\build\KMM_Conductor\scripts\init"
TMP = tempfile.mkdtemp(prefix="kmm_campaign_").replace("\\", "/")
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
TEST = r'''
N, FAILS = 0, {}
function check(c, what) N = N + 1; if not c then FAILS[#FAILS + 1] = what end end
local C = KMM_Conductor
C.reset()
local S = C.state()
local P = C.cfg().params
P.materialize.relations_enabled = true
local CA = C.camp()
local D = C.read_json("campaigns.json", "C:/KenshiModMap/build/KMM_Conductor/campaigns.json")
check(D and D.factions, "campaigns.json loads")
P.campaign.sdir = "TMPDIR/"
P.campaign.p_raid, P.campaign.p_capture, P.campaign.q_reinforce = 1, 1, 1
local TI = C.cfg().town_info
TRIG, RD, WARS, NOWAR = {}, {}, {}, {}
local function PF(id)
  local f = FAC(id)
  if not f._p then
    f._p = true
    f.warMgr.triggerCampaign = function(self, target, gd, mn, mx, home, dup, tf) TRIG[#TRIG + 1] = { f = id, target = target, gd = gd, mn = mn, mx = mx, home = home, dup = dup, tf = tf } end
    f.relations.getRelationData = function(self, o) RD[id .. ">" .. o.id] = RD[id .. ">" .. o.id] or {}; return RD[id .. ">" .. o.id] end
    f.relations.declareWar = function(self, o) WARS[#WARS + 1] = id .. ">" .. o.id end
    f.relations.setNoLongerEnemies = function(self, o) NOWAR[#NOWAR + 1] = id .. ">" .. o.id end
  end
  return f
end
local function first_town(fid) local l = {}; for t in pairs(S.F[fid].towns) do if TI[t] and TI[t].x then l[#l + 1] = t end end; table.sort(l); return l[1] end
local ATT, VIC, ALLY
local function usable(fid, ks) for _, k in ipairs(ks) do for _, sid in ipairs(D.factions[fid][k]) do local c = D.campaigns[sid]; if c.ws == 0 and c.forces <= 30 then return true end end end end
local ids = {}; for fid in pairs(D.factions) do ids[#ids + 1] = fid end; table.sort(ids)
for _, fid in ipairs(ids) do
  local e, f = D.factions[fid], S.F[fid]
  if f and f.alive and not f.player and first_town(fid) then
    if not ATT and usable(fid, { "raid", "assault" }) then ATT = fid
    elseif not ALLY and usable(fid, { "reinforce" }) then ALLY = fid end
  end
end
for fid, f in pairs(S.F) do if not VIC and f.alive and not f.player and fid ~= ATT and fid ~= ALLY and first_town(fid) then VIC = fid end end
check(ATT and VIC and ALLY, "test factions found")
for _, id in ipairs({ ATT, VIC, ALLY }) do PF(id) end
local vt = first_town(VIC)
S.F[VIC].towns = { [vt] = true }
S.rel[ATT][VIC], S.rel[VIC][ATT] = -40, -40
S.treaties = {}
-- 1. игрок далеко: кампания не запускается (незагруженная зона)
local far = MKCH("PC1", "player", TI[vt].x + 900000, TI[vt].z, { player = true, platoon = "player_squad" }); PCS = { far }; CHARS = { far }
C.act_test(ATT, "raid", VIC)
check(#TRIG == 0, "no campaign when target zone is far from player")
-- 2. игрок рядом: родная кампания + native=true, правильные аргументы
local near = MKCH("PC2", "player", TI[vt].x + 500, TI[vt].z, { player = true, platoon = "player_squad" }); PCS = { near }; CHARS = { near }
S.treaties[900] = { id = 900, type = "defense", a = VIC, b = ALLY, since = 0, term = 99999, active = true, why = "test" }
S.rel[VIC][ALLY], S.rel[ALLY][VIC] = 60, 60
local ev0 = #S.events
C.act_test(ATT, "raid", VIC)
check(#TRIG == 2, "attack + ally reinforce launched: " .. #TRIG)
local t1, t2 = TRIG[1], TRIG[2]
local okset = {}; for _, k in ipairs({ "raid", "assault" }) do for _, s in ipairs(D.factions[ATT][k]) do okset[s] = true end end
check(t1 and t1.f == ATT and okset[t1.gd.stringID] and t1.gd.t == 93, "attacker own campaign sid, type 93")
check(t1 and t1.mn == 0 and t1.mx == 0 and t1.dup == false and t1.tf == FAC(ATT) and t1.home and t1.target, "args: minTime/maxTime/forceDuplicate/triggeringFaction/home/target")
local rset = {}; for _, s in ipairs(D.factions[ALLY].reinforce) do rset[s] = true end
check(t2 and t2.f == ALLY and rset[t2.gd.stringID] and t2.tf == FAC(ALLY), "ally reinforce campaign")
local nat, outcome = 0, false
for i = ev0 + 1, #S.events do local e = S.events[i]; if e.native then nat = nat + 1 end; if e.type == "raid" or e.type == "attack_repelled" then outcome = e.native == true end end
check(nat >= 3 and outcome, "events flagged native=true (campaign, reinforce, raid outcome): " .. nat)
check(S.stats.native_campaigns == 1 and S.stats.native_reinforce == 1, "stats")
local lf = io.open("TMPDIR/probe_triggerCampaign.lock", "r"); check(lf == nil, "lock removed after first successful call"); if lf then lf:close() end
-- 3. лимиты
C.act_test(ATT, "raid", VIC)
check(#TRIG == 2, "faction cooldown blocks second campaign")
S.ncamp = { f = {}, d = { 0, 0, 0 } }
C.act_test(ATT, "raid", VIC)
check(#TRIG == 2, "world cap blocks campaign")
S.ncamp = nil
-- 4. enabled=false
P.campaign.enabled = false; C.act_test(ATT, "raid", VIC); check(#TRIG == 2, "enabled=false"); P.campaign.enabled = true
-- 5. договор между сторонами блокирует
S.treaties[901] = { id = 901, type = "nonaggression", a = ATT, b = VIC, since = 0, term = 99999, active = true, why = "t" }
C.act_test(ATT, "raid", VIC); check(#TRIG == 2, "treaty blocks"); S.treaties[901] = nil
-- 6. capture
P.campaign.q_reinforce = 0
C.act_test(ATT, "capture", VIC)
check(#TRIG == 3 and TRIG[3].f == ATT, "capture launches campaign: " .. #TRIG)
-- 7. крэш-сторож: lock при старте -> .off навсегда
S.F[VIC].towns = { [vt] = true }   -- capture мог забрать город в модели
CA.PROBE = {}
local lk = io.open("TMPDIR/probe_triggerCampaign.lock", "w"); lk:write("x"); lk:close()
S.ncamp = nil
C.act_test(ATT, "raid", VIC)
check(#TRIG == 3, "lock at start disables triggerCampaign")
DBG7 = tostring(CA.OFF) .. " probe=" .. tostring(CA.PROBE.triggerCampaign) .. " cd=" .. tostring(S.ncamp and S.ncamp.f[ATT]) .. " lastwar=" .. tostring(S.F[ATT].camp_day)
local of = io.open("TMPDIR/probe_triggerCampaign.off", "r"); check(of ~= nil, ".off written"); if of then of:close() end
local lk2 = io.open("TMPDIR/probe_triggerCampaign.lock", "r"); check(lk2 == nil, "lock cleared after off"); if lk2 then lk2:close() end
CA.PROBE = {}; S.ncamp = nil
C.act_test(ATT, "raid", VIC)
check(#TRIG == 3, ".off persists across sessions")
-- 8. флаги RelationData
local A, B = ATT, ALLY
S.dirty_rel = {}; S.treaties = {}
S.treaties[910] = { id = 910, type = "defense", a = A, b = B, since = 0, term = 99999, active = true, why = "t" }
S.dirty_rel[A .. "|" .. B] = true
C.write_rel_test()
local rd = RD[A .. ">" .. B]
check(rd and rd.alliance == true and rd.peaceTreaty == false and rd.war == false, "alliance flag set")
S.treaties = {}; S.treaties[911] = { id = 911, type = "trade", a = A, b = B, since = 0, term = 99999, active = true, why = "t" }
S.dirty_rel[A .. "|" .. B] = true; C.write_rel_test()
check(RD[A .. ">" .. B].alliance == false and RD[A .. ">" .. B].peaceTreaty == true, "peaceTreaty flag set")
S.treaties = {}; S.rel[A][B], S.rel[B][A] = -80, -80; S.F[A].last_war = 0
S.dirty_rel[A .. "|" .. B] = true; C.write_rel_test()
check(RD[A .. ">" .. B].war == true and #WARS == 2, "war flag + declareWar both sides: " .. #WARS)
S.dirty_rel[A .. "|" .. B] = true; C.write_rel_test()
check(#WARS == 2, "declareWar not repeated")
S.rel[A][B], S.rel[B][A] = 10, 10
S.dirty_rel[A .. "|" .. B] = true; C.write_rel_test()
check(RD[A .. ">" .. B].war == false and #NOWAR == 2, "peace: setNoLongerEnemies: " .. #NOWAR)
-- 9. COHAB (баг Mongrel): соседи по городу — в движке не ниже 0 и без войны, даже если модель их поссорила
C.cfg().cohab = { { A, B } }
S.rel[A][B], S.rel[B][A] = -80, -80
local w9 = #WARS
S.dirty_rel[A .. "|" .. B] = true; C.write_rel_test()
check(#WARS == w9 and RD[A .. ">" .. B].war == false, "cohab: no war written to the engine")
local fo = FAC(A); check(fo.rel and (fo.rel[B] or 0) >= 0, "cohab: engine relation floored at 0: " .. tostring(fo.rel and fo.rel[B]))
C.cfg().cohab = nil
S.dirty_rel[A .. "|" .. B] = true; C.write_rel_test()
check((FAC(A).rel[B] or 0) == -80, "not neighbours: model value written as is")
DBGL = DBG7 .. (LOGS or ""):sub(-300)
RESULT = #FAILS == 0 and ("OK " .. N) or ("FAIL: " .. table.concat(FAILS, "; "))
'''
run(TEST.replace("TMPDIR", TMP), "test")
run("")
L.lua_getfield.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_char_p]
L.lua_getfield(st, -10002, b"RESULT")
r = L.lua_tolstring(st, -1, None).decode()
print(r)
if not r.startswith("OK"):
    L.lua_getfield(st, -10002, b"DBGL"); print(L.lua_tolstring(st, -1, None).decode())
sys.exit(0 if r.startswith("OK") else 1)
