"""Offline test KMM_Nemesis debts: вылеченный/освобождённый игроком становится должником — приходит на помощь в бою (имя, реплика, родная память LT_MY_LIFESAVER/LT_FREED_ME) или разносит добрую молву; память мира об игроке — избитый и оставленный жить/сбежавший становится соперником с прозвищем встречи, мститель за убитого, преследование по регионам, встреча с репликой и родной памятью ядра, повторная пощада, гибель. python -I -X utf8 build/KMM_Conductor/_dev/test_nemesis.py -> OK."""
import ctypes, re, sys, tempfile

DLL = r"C:\Program Files (x86)\Steam\steamapps\workshop\content\233860\3817000612\lua51.dll"
B = r"C:\KenshiModMap\build\KMM_Conductor\scripts\init"
TMP = tempfile.mkdtemp(prefix="kmm_outlaws_").replace("\\", "/")
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
run(open(B + r"\KMM_Fates.lua", encoding="utf-8").read(), "KMM_Fates.lua")
run(open(B + r"\KMM_Outlaws.lua", encoding="utf-8").read(), "KMM_Outlaws.lua")
run(open(B + r"\KMM_Nemesis.lua", encoding="utf-8").read(), "KMM_Nemesis.lua")
run(r'''
N, FAILS = 0, {}
function check(c, what) N = N + 1; if not c then FAILS[#FAILS + 1] = what end end
local C = KMM_Conductor
C.reset()
local TP = C.cfg().params.traces
TP.first_hour_traces = 0; TP.max_per_day = 1000; TP.max_queue = 1000; TP.arrive_enabled = false
TP.bounty = { enabled = false }
local pf = C.cfg().player_faction
C.cfg().params.outlaws = { watch_s = 1e9, sdir = "TMPDIR/", spawn_p = 1, cd_h = 0, native_bounty = false }
C.cfg().params.nemesis = { rival_p_spared = 0, rival_p_fled = 0, avenger_p = 0, cooldown_days = 0, follow_p = 1, say_delay_s = 1, linger_s = 30 }
local O, T, NM = KMM_Outlaws, KMM_Traces, KMM_Nemesis
MADE = {}
local old = getGameWorld
getGameWorld = function()
  local w = old()
  w.theFactory.createRandomSquad = function(self, f, pos, ...)
    local leader = { name = "Some Raider", dead = false, said = {}, mem = {} }
    leader.crimes = { unfairAddToBounty = function() end, getTotalBounty = function() return 0 end }
    function leader:setName(n) self.name = n end
    function leader:getName() return self.name end
    function leader:isDead() return self.dead end
    function leader:isDown() return self.down or false end
    function leader:say(s) self.said[#self.said + 1] = s end
    function leader:rememberCharacter(who, tag) self.lua_mem = true end   -- P4: неоднозначный Lua-метод вызываться не должен
    function leader:getFaction() return FAC(f.id) end
    function leader:getPosition() return { x = pos.x, y = 0, z = pos.z } end
    local pl = { isDead = false }
    function pl:getSquadLeader() return leader end
    function pl:getActivePlatoon() return { setName = function() end } end
    MADE[#MADE + 1] = { pl = pl, leader = leader, x = pos.x, z = pos.z, fid = f.id }
    return pl
  end
  if not w.factionMgr then w.factionMgr = {} end
  if not w.factionMgr.getFactionByStringID then w.factionMgr.getFactionByStringID = function(self, sid) return { id = sid } end end
  return w
end
CharacterPerceptionTags_LongTerm = { LT_MY_LIFESAVER = 2, LT_FREED_ME = 3, LT_DEFEATED_MY_SQUAD_ONCE = 7, LT_KILLED_MY_FRIEND = 9 }
KMM_Native = { has_memory = function() return true end,   -- P4: долгая память ядра через плагин (remember_lt)
  remember_lt = function(npc, who, tag) npc.mem[#npc.mem + 1] = tag; return true end }
local function tick(day) DAYV = day; CLOCK = CLOCK + 100; FIRE("GameWorld::charsUpdate", {}) end
local function evs(ty) local n, last = 0, nil; for _, e in ipairs(C.state().events) do if e.type == ty then n = n + 1; last = e end end; return n, last end
local D = O._M.data(C)
local M = O._M
local S = C.state()
local rg, town
for nm, r in pairs(D.regions) do if #r.towns > 0 then rg, town = nm, r.towns[1]; break end end
-- должник: фракция с отрядом тира 1, враг (или нейтрал) нападающего банде
local dfid, gfid
for fid in pairs(S.F) do
  if fid ~= pf and M.tier_sid(D, fid, 1) then
    for _, r in pairs(D.regions) do for _, g in ipairs(r.gangs) do
      if not gfid and g ~= fid and S.F[g] then dfid, gfid = fid, g end
    end end
  end
  if gfid then break end
end
check(dfid and gfid, "debtor/attacker factions: " .. tostring(dfid) .. " / " .. tostring(gfid))
if C.rel(dfid, gfid) > 0 then C.add_rel(dfid, gfid, -200) end
if C.rel(dfid, pf) < 0 then C.add_rel(dfid, pf, 200) end
PCS = {}; CHARS = {}
local pc = MKCH("Beep", pf or "player", town.x + 500, town.z + 500, { player = true, platoon = "player_squad" })
PCS[1] = pc; CHARS[1] = pc
tick(500)
check(Events.h["CharStats::xpFirstAid"] and Events.h["CharStats::xpLockpicking"] and Events.h["Character::setChainedMode"], "debt hooks registered")
-- 1) лечение: копится, должник один раз
local w = MKCH("Wounded Drifter", dfid, town.x + 700, town.z + 700, {})
FIRE("CharStats::xpFirstAid", { me = w }, w, 50)           -- лечит не игрок
FIRE("CharStats::xpFirstAid", { me = pc }, pc, 50)         -- игрок лечит своего
check((evs("debt_made")) == 0, "no debt from non-player medic or own patient")
for i = 1, 3 do FIRE("CharStats::xpFirstAid", { me = pc }, w, 5) end
check((evs("debt_made")) == 0, "15 s of first aid: not yet")
for i = 1, 3 do FIRE("CharStats::xpFirstAid", { me = pc }, w, 5) end
local nm1, em1 = evs("debt_made")
check(nm1 == 1 and em1.deed == "healed", "healed debt made once: " .. nm1)
local dh = NM.debts()[dfid .. "|Wounded Drifter"]
local wt = NM._N.where(D, town.x + 700, town.z + 700)
check(dh and wt and dh.place == wt.name, "debt remembers nearest town: " .. tostring(dh and dh.place))
-- 2) оковы: снялись без взлома игроком — не долг; после взлома — долг
local s1 = MKCH("Chained One", dfid, town.x + 600, town.z + 600, {})
FIRE("Character::setChainedMode", s1, false)
check((evs("debt_made")) == 1, "unchained without player lockpick: no debt")
FIRE("CharStats::xpLockpicking", { me = pc }, 30, false)
FIRE("Character::setChainedMode", s1, false)
check((evs("debt_made")) == 1, "failed lockpick: no debt")
FIRE("CharStats::xpLockpicking", { me = pc }, 30, true)
CLOCK = CLOCK + 5
FIRE("Character::setChainedMode", s1, true)
check((evs("debt_made")) == 1, "chained (on=true): no debt")
FIRE("Character::setChainedMode", s1, false)
local nm2, em2 = evs("debt_made")
check(nm2 == 2 and em2.deed == "freed", "freed debt after player lockpick")
CLOCK = CLOCK + 100
FIRE("Character::setChainedMode", MKCH("Late One", dfid, town.x, town.z, {}), false)
check((evs("debt_made")) == 2, "lockpick window expired: no debt")
-- 3) не созрел: в тот же день помощи нет
check(not NM.on_player_attacked(gfid), "debt not ripe on the same day")
tick(501.5)
check(not NM.on_player_attacked(dfid), "debtor never helps against its own faction")
-- 4) напали на игрока — должник приходит
local m0 = #MADE
check(NM.on_player_attacked(gfid) == true, "debt squad requested")
local nr, er = evs("debt_repaid")
check(nr == 1, "debt_repaid emitted")
check(not NM.on_player_attacked(gfid), "cooldown: one help per help_cd_days")
local paidk, unpaid
for k, d in pairs(NM.debts()) do if d.paid then paidk = d else unpaid = d end end
local function mine() for i = #MADE, m0 + 1, -1 do if MADE[i].leader.name == paidk.n then return MADE[i] end end end
for i = 1, 40 do CLOCK = CLOCK + 80; tick(501.6); if mine() then break end end
local mk = mine()
check(mk and mk.fid == dfid, "debtor squad spawned with his name: " .. tostring(paidk and paidk.n))
for i = 1, 3 do CLOCK = CLOCK + 5; FIRE("GameWorld::charsUpdate", {}) end
check(mk and #mk.leader.said == 1 and mk.leader.said[1]:find(paidk.place, 1, true), "debtor names the place: " .. tostring(mk and mk.leader.said[1]))
check(mk and mk.leader.mem[1] == (paidk.deed == "freed" and 3 or 2) and not mk.leader.lua_mem, "native memory lifesaver/freed via plugin: " .. tostring(mk and mk.leader.mem[1]))
if mk then
do   -- P4: нет плагина -> Lua rememberCharacter не вызывается, маркер в лог
  local NN, KN0, log0, LG = KMM_Nemesis._N, KMM_Native, KMM_Nemesis._N.log, {}
  NN.log = function(m) LG[#LG + 1] = tostring(m) end; NN.mem_nonative = nil; KMM_Native = nil
  local n0 = #mk.leader.mem; NN.remember(mk.leader, "LT_MY_LIFESAVER")
  check(#mk.leader.mem == n0 and not mk.leader.lua_mem and LG[1] and LG[1]:find("remember: no native", 1, true), "no plugin: no Lua rememberCharacter, marker: " .. tostring(LG[1]))
  NN.log = log0; KMM_Native = KN0
end
end
-- 5) второй долг без боя — добрая молва
C.add_rel(dfid, pf, 20 - C.rel(dfid, pf))   -- середина шкалы: рост виден
local r0 = C.rel(dfid, pf)
for d = 502, 521 do tick(d) end
local nw, ew = evs("debt_word")
check(nw == 1 and ew.leader_name == unpaid.n, "unpaid debt turns into good word: " .. nw)
check(S.F[pf] and C.rel(dfid, pf) > r0, "debtor faction warms to the player: " .. r0 .. " -> " .. C.rel(dfid, pf))
for d = 522, 590 do tick(d) end
local left = 0; for _ in pairs(NM.debts()) do left = left + 1 end
check(left == 0, "paid debts pruned after 60 days: " .. left)
-- 6) колбэк с неожиданными аргументами: выключается только он
FIRE("CharStats::xpFirstAid", { me = pc }, w, "garbage", "x")   -- tonumber -> 0, без ошибки
local bad = setmetatable({}, { __index = function() error("bad userdata") end })
FIRE("Character::setChainedMode", bad, false)
FIRE("CharStats::xpLockpicking", bad, 1, true)
check(next(NM.disabled()) == nil, "nemesis still enabled after bad callback args")
RESULT = #FAILS == 0 and ("OK " .. N) or ("FAIL: " .. table.concat(FAILS, "; "))
'''.replace("TMPDIR", TMP), "test")
run("")
L.lua_getfield.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_char_p]
L.lua_getfield(st, -10002, b"RESULT")
r = L.lua_tolstring(st, -1, None).decode()
print(r)
sys.exit(0 if r.startswith("OK") else 1)
