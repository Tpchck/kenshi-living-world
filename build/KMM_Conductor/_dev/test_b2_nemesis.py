"""Offline test B2 (KMM_Nemesis, 2026-11-15): нелинейная прокачка через встречи с соперниками — общие правила по состоянию игрока.
(1) N.worth/poor — только ванильные числа: деньги, цена вещей, награда ядра, численность, навык; деньги не читаются -> не «нищий».
(2) Y5 contempt: слабый нищий отряд — соперник не нападает (пакет «бродить», реплика, событие один раз в окне, регрупп);
    разбогател -> штурм; мститель презрения не знает.
(3) Ветка исхода: игрок лёг от руки бандита (ванильное Character.lastGuyWhoDefeatedMe) -> deed=beat, а не «fled from the Nameless»;
    обратная память без ударов игрока; игрок лёг от чужого -> без соперника; никто не ложился -> fled как раньше.
(4) Спираль: нищий слабый игрок — не больше weak_max_rivals живых соперников.
(5) Хроника: «ближние» типы рядом с игроком проходят, не больше chron_type_day одного типа в день, без повтора текста, дальние — нет.
python -I -X utf8 build/KMM_Conductor/_dev/test_b2_nemesis.py -> OK."""
import ctypes, re, sys, tempfile

DLL = r"C:\Program Files (x86)\Steam\steamapps\workshop\content\233860\3817000612\lua51.dll"
B = r"C:\KenshiModMap\build\KMM_Conductor\scripts\init"
TMP = tempfile.mkdtemp(prefix="kmm_b2n_").replace("\\", "/")
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
run(open(B + r"\KMM_Outlaws.lua", encoding="utf-8").read(), "KMM_Outlaws.lua")
run(open(B + r"\KMM_Nemesis.lua", encoding="utf-8").read(), "KMM_Nemesis.lua")
run(r'''
N, FAILS = 0, {}
function check(c, what) N = N + 1; if not c then FAILS[#FAILS + 1] = what end end
local C = KMM_Conductor
C.reset()
local pf = C.cfg().player_faction or "player"
C.cfg().params.outlaws = { watch_s = 1e9, sdir = "TMPDIR/", native_bounty = false }
C.cfg().params.nemesis = { say_delay_s = 1, ambient = false, banter = false, company = false, cooldown_days = 0, linger_s = 30,
                           rival_p_beat = 1, rival_p_fled = 1, rival_p_spared = 1, weak_rival_mult = 1, avenger_p = 0 }
local NM, NN = KMM_Nemesis, KMM_Nemesis._N
local LOG = {}
local log0 = NN.log
NN.log = function(m) LOG[#LOG + 1] = tostring(m); log0(m) end
local function logged(s) for _, l in ipairs(LOG) do if l:find(s, 1, true) then return true end end return false end
local S = C.state()
local OM = KMM_Outlaws._M
local roam_sid = OM.cfg().pkg_roam
KMM_Native = { has_memory = function() return true end, remember_lt = function(npc, who, tag) MEM[#MEM + 1] = tag; return true end }
MEM = {}
-- деньги ядра (Character:getMoney); nil = не читается
MONEY = 0
local D = OM.data(C)
local rgs = {}; for nm, r in pairs(D.regions) do if #r.towns > 0 and #r.gangs > 0 then rgs[#rgs + 1] = nm end end
table.sort(rgs)
local R = D.regions[rgs[1]]
local town, gang = R.towns[1], R.gangs[1]
local TX, TZ = town.x + 500, town.z + 500
local function item(v) return { getValueAll = function() return v end } end
local function player(n, opt)
  opt = opt or {}
  PCS = {}
  for i = 1, n do
    local c = MKCH("pc" .. i, pf, TX + i * 10, TZ, { player = true, platoon = "player_squad", items = opt.items })
    c.down = false
    function c:isDown() return self.down end
    c.crimes = { getTotalBounty = function() return opt.bounty or 0 end }
    function c:getMoney() if MONEY == nil then error("no money binding") end; return MONEY end
    c.hko = false; function c:getMedical() return { isHungerKO = function() return c.hko end } end
    function c:getStats() return { getOverallSkillLevel_0_100 = function() return opt.skill or 5 end } end
    c.app = opt.app or 10
    function c:getStateBroadcast() return { apparentStrength = self.app, actualStrength = self.app } end
    function c:getBlackboard() return { moraleIsBroken = false } end
    PCS[i] = c
  end
  CHARS = {}; for i, c in ipairs(PCS) do CHARS[i] = c end
  NN.wc = nil
  return PCS
end

-- (1) богатство по ванильным числам
player(1); MONEY = 0
local W = NM.worth()
check(W and W.poor == true and W.money == 0 and W.n == 1 and W.gear == 0, "naked broke loner is poor: " .. tostring(W and W.txt))
MONEY = 5000; NN.wc = nil
check(NM.poor() == false, "money -> not poor")
MONEY = 0; player(1, { items = { item(1800), item(900) } })
check(NM.poor() == false and NM.worth().gear == 2700, "gear value counts (getValueAll): " .. NM.worth().txt)
player(1, { bounty = 500 }); check(NM.poor() == false, "engine bounty -> not poor")
player(3); check(NM.poor() == false, "three of them -> not poor (squad)")
player(1, { skill = 40 }); check(NM.poor() == false, "skilled -> not poor")
player(1); MONEY = nil; NN.wc = nil
local pl0 = PLATOONS.player_squad.getOwnerships
PLATOONS.player_squad.getOwnerships = function() error("no platoon ownerships") end
check(NM.poor() == false and logged == logged, "money unreadable -> not poor (as before)")
PLATOONS.player_squad.getOwnerships = pl0
NN.wc = nil
check(NM.worth().money == 5000, "money fallback: platoon ownerships")
MONEY = 0; NN.wc = nil
-- цена вещей: getValueAll не читается -> getValueSingle x quantity; ничего -> worth_item_guess за вещь, маркер в логе
local function item1(v, q) return { quantity = q, getValueSingle = function() return v end } end
player(1, { items = { item1(400, 3) } }); LOG = {}
check(NM.worth().gear == 1200 and NM.worth().fb == "single" and logged("worth: item value fallback=single"), "fallback getValueSingle x quantity: " .. NM.worth().txt)
player(1, { items = { {}, {}, {}, {}, {}, {} } }); LOG = {}
check(NM.worth().gear == 3000 and NM.poor() == false and logged("fallback=guess"), "no value binding: 500 per item guess, six items -> not poor")
player(1)
-- конфиг: прокси на params (правка на месте видна сразу, запись уходит в params)
local PN = C.cfg().params.nemesis
PN.worth_money = 7; check(NN.cfg().worth_money == 7 and NN.cfg().max_rivals == NN.DEF.max_rivals, "cfg proxy: params value live, DEF fallback")
NN.cfg().worth_money = 9; check(PN.worth_money == 9, "cfg proxy write goes to params")
PN.worth_money = nil; check(NN.cfg().worth_money == NN.DEF.worth_money, "cfg proxy: removed key -> DEF")
local cnt = 0; local mt = getmetatable(NN.cfg()); check(mt and NN.cfg() == NN.cfg(), "cfg proxy reused between calls (no copy)")

-- (2) Y5 contempt
local PKG = {}
local RB = { moraleIsBroken = false }
function RB:replaceAIPackage(gd) PKG[#PKG + 1] = gd.stringID end
local lead = { size = 3 }
function lead:getName() return "Kadan Sandscar" end
function lead:getPosition() return { x = TX, y = 0, z = TZ } end
function lead:isDead() return false end
function lead:isDown() return false end
function lead:getBlackboard() return RB end
function lead:getStateBroadcast() return { actualStrength = 10, apparentStrength = 4 } end
function lead:getPlatoon() return { getSquadSize = function() return lead.size end } end
function lead:getSensoryData() return { canISeeThisGuy = function() return true end } end
local gw0 = getGameWorld
getGameWorld = function()
  local w = gw0()
  local base = w.getCharacterUpdateList
  w.getCharacterUpdateList = function(self)
    local set = base(self)
    setmetatable(set, { __index = { has = function(_, c) if c == lead then return true end; return rawget(set, c) == true end } })
    return set
  end
  return w
end
local nexti = 700
local function rival(deed)
  nexti = nexti + 1
  return { i = nexti, n = "Kadan Sandscar", st = "a", g = gang, t = 1, b = 1000, pg = { deed = deed or "beat", place = "Squin", met = 1, day = 0 } }
end
local function meet(o) PKG = {}; LOG = {}; NN.said = {}; NN.on_spawn(o, lead); NN.said = {}; return NN.appr["o" .. o.i] end
local function step() NN.appraise_step(C, S) end
local function nev(ty) local k = 0; for _, e in ipairs(S.events) do if e.type == ty then k = k + 1 end end; return k end
local function said_pool(pool) for _, s in ipairs(NN.said) do for _, l in ipairs(pool) do if s.line == l then return true end end end return false end
player(1); MONEY = 0
local o = rival("beat")
meet(o)
check(MEM[#MEM] == 8, "beat rival: core memory LT_SQUAD_LOST_TO_ME_ONCE (8), got " .. tostring(MEM[#MEM]))
local c0 = nev("nemesis_contempt")
step()
check(logged("-> contempt") and logged("worth: money=0") and PKG[1] == roam_sid, "poor weak loner: contempt with roam package")
check(said_pool(NN.SAY.appr_contempt) and nev("nemesis_contempt") == c0 + 1 and o.pg.wd_day ~= nil and o.pg.ct == 1, "contempt line, one event, regroup mark")
meet(o); step()
check(nev("nemesis_contempt") == c0 + 1 and o.pg.ct == 1 and said_pool(NN.SAY.appr_contempt), "same rival, same window: line again, no new event")
MONEY = 6000; NN.wc = nil
o = rival("beat"); meet(o); step()
check(logged("-> attack") and #PKG == 0, "player got rich: the same appraisal attacks")
MONEY = 0; NN.wc = nil
o = rival("avenger"); meet(o); step()
check(logged("-> attack") and not logged("-> contempt"), "avenger comes for blood, not loot: attacks a poor player")
player(1, { app = 40 }); o = rival("spared"); meet(o); step()
check(not logged("-> contempt") and logged("-> parley"), "poor but visibly strong: no contempt (ratio rule as before)")
local cc = C.cfg().params.nemesis; cc.appr_contempt = false; player(1); o = rival("beat"); meet(o); step(); cc.appr_contempt = nil
check(logged("-> attack"), "appr_contempt=false: as before")

-- (3) исход боя: кто кого уложил
local M, O, D2 = NN.outlaws()
local function bandit(nm, fid, dx)
  local v = MKCH(nm, fid, TX + (dx or 300), TZ, {})
  v.down = false
  function v:isDown() return self.down end
  v.combat = true; function v:isInCombatMode() return self.combat end
  return v
end
local function knock(pc, by)
  NN.beat_t = nil; NN.beat_scan(C, S)   -- видели стоящим
  pc.down = true
  pc.lastGuyWhoDefeatedMe = by and { getCharacter = function() return by end } or nil
  CLOCK = CLOCK + 4; NN.beat_t = nil; NN.beat_scan(C, S)
end
local function born_since(k0) local L2 = {}; local i = 0; for _, e in ipairs(S.events) do if e.type == "nemesis_born" then i = i + 1; if i > k0 then L2[#L2 + 1] = e end end end; return L2 end
local function settle() CLOCK = CLOCK + 60; NN.resolve(M, O, D2, C, S) end
player(1); MONEY = 0
local pc = PCS[1]
local b0 = nev("nemesis_born")
local v1 = bandit("Hungry Bandit", gang)
NM.on_player_hit(v1, pc); NM.on_player_hit(v1, pc)   -- игрок бил дважды, бандит стоял, игрок лёг от него
knock(pc, v1)
check(logged("beaten: pc1 went down to Hungry Bandit"), "beaten marker")
settle()
local nb = born_since(b0)
check(#nb == 1 and nb[1].deed == "beat" and not nb[1].text:find("fled", 1, true) and nb[1].text:find("beat the Nameless", 1, true),
      "winner on his feet -> deed=beat, not 'fled': " .. tostring(nb[1] and nb[1].text))
check(#NM.rivals() == 1 and NM.rivals()[1].pg.deed == "beat", "rival remembers the beating")
-- (4) спираль: нищему слабому — не больше одного соперника; без ударов игрока — тоже память (обратная), но лимит
pc.down = false
local v2 = bandit("Dust Bandit", gang, 400)
knock(pc, v2)
check(NN.cand[gang .. "|Dust Bandit"] and NN.cand[gang .. "|Dust Bandit"].beat and NN.cand[gang .. "|Dust Bandit"].hits == 0, "reverse memory without player hits: candidate made")
b0 = nev("nemesis_born")
settle()
check(#born_since(b0) == 0 and logged("nemesis_skip: Dust Bandit deed=beat rivals=1/1"), "poor weak player: rival cap 1")
MONEY = 8000; NN.wc = nil; pc.down = false
local v3 = bandit("Starving Bandit", gang, 500)
knock(pc, v3)
b0 = nev("nemesis_born")
settle()
nb = born_since(b0)
check(#nb == 1 and nb[1].deed == "beat", "richer player: cap back to max_rivals")
-- игрок лёг от чужого: кандидат стоял -> без соперника и без «fled»
MONEY = 8000; NN.wc = nil; pc.down = false
local other = nil; for _, g in ipairs(R.gangs) do if g ~= gang then other = other or g end end
other = other or "some_other_fid"
local v4 = bandit("Grim Raider", gang, 350)
NM.on_player_hit(v4, pc); NM.on_player_hit(v4, pc)
local w5 = bandit("Fogman", other, 320)
NN.cfg_cooldown = nil
knock(pc, w5)
check(NN.cand[gang .. "|Grim Raider"].plost == true and not NN.cand[gang .. "|Grim Raider"].beat, "other faction's win: candidate marked plost, not beat")
NN.cand[other .. "|Fogman"] = nil
b0 = nev("nemesis_born")
settle()
nb = born_since(b0)
check(#nb == 0, "player went down to someone else: no 'fled' rival for the one standing")
-- никто из своих не ложился: fled как раньше
pc.down = false
local v6 = bandit("Swift Raider", gang, 360)
NM.on_player_hit(v6, pc); NM.on_player_hit(v6, pc)
b0 = nev("nemesis_born")
NN.beat_t = nil; NN.beat_scan(C, S)
settle()
nb = born_since(b0)
check(#nb == 1 and nb[1].deed == "fled", "nobody of ours went down: fled as before")
-- победитель далеко / мёртв -> без памяти
pc.down = false
local v7 = bandit("Far Bandit", gang, 9000)
knock(pc, v7)
check(NN.cand[gang .. "|Far Bandit"] == nil and logged("winner unknown or gone"), "winner too far: no memory (stale field)")
-- устаревший победитель: рядом, но не в бою и не дрался с игроком -> без памяти
pc.down = false
local v8 = bandit("Idle Bandit", gang, 200); v8.combat = false
LOG = {}; knock(pc, v8)
check(NN.cand[gang .. "|Idle Bandit"] == nil and logged("stale winner Idle Bandit"), "stale winner (not fighting, no hits): no memory")
-- тот же, но игрок только что бил его -> свежий
pc.down = false
NM.on_player_hit(v8, pc)
knock(pc, v8)
check(NN.cand[gang .. "|Idle Bandit"] and NN.cand[gang .. "|Idle Bandit"].beat, "not fighting now, but traded blows just now: fresh")
NN.cand[gang .. "|Idle Bandit"] = nil
-- лёг от голода (MedicalSystem:isHungerKO) -> поле победителя старое
pc.down = false; pc.hko = true
local v9 = bandit("Hunger Bandit", gang, 210)
knock(pc, v9)
check(NN.cand[gang .. "|Hunger Bandit"] == nil, "hunger knockout: no winner")
pc.hko = false

-- (5) хроника: ближние типы
NN.chron_q = {}
local X = NN.state(S)
NN.chronicle(C, S)
local function em(ty, txt, far) C.emit({ type = ty, a = gang, b = gang, text = txt, x = far and TX + 90000 or TX + 100, z = TZ }) end
em("raid", "Raid one."); em("raid", "Raid one."); em("raid", "Raid two."); em("raid", "Raid three."); em("caravan_lost", "Caravan gone.", true)
em("loot_carried", "Loot moved.")
NN.chronicle(C, S)
local q = table.concat(NN.chron_q, "|")
check(q:find("Raid one.", 1, true) and q:find("Raid two.", 1, true) and not q:find("Raid three.", 1, true), "near raids pass, capped at 2 per type per day: " .. q)
local n1 = 0; for _ in q:gmatch("Raid one%.") do n1 = n1 + 1 end
check(n1 == 1, "same text once")
check(not q:find("Caravan gone.", 1, true) and not q:find("Loot moved.", 1, true), "far event and noise types skipped")
local rid; for _, e in ipairs(S.events) do if e.text == "Raid one." then rid = rid or e.id end end
local s0, q0 = NM.chronicled(rid)
check(s0 == false and q0 == true, "chronicled: queued, not yet sent")
MSGS = {}
ManagementScreen = { getSingleton = function() return { addMessage = function(_, o, l) MSGS[#MSGS + 1] = l end } end }
CLOCK = CLOCK + 100; NN.chronicle(C, S)
local s1, q1 = NM.chronicled(rid)
check(#MSGS == 1 and MSGS[1]:find("Raid one.", 1, true) and s1 == true and q1 == false, "chronicled: sent via addMessage")
check(NM.chronicled(-5) == false and NM.chronicled(nil) == false, "chronicled: unknown id -> false")
-- Rumors уже записал событие в журнал -> хроника Nemesis его пропускает
em("raid", "Raid four."); em("caravan_lost", "Caravan near.")
local cid; for _, e in ipairs(S.events) do if e.text == "Caravan near." then cid = e.id end end
CLOCK = CLOCK + 100; NN.chronicle(C, S)   -- в очередь (raid-лимит дня исчерпан: Raid four. не встаёт)
KMM_Rumors = { journaled = function(id) return id == cid end }
local m0 = #MSGS
for i = 1, 4 do CLOCK = CLOCK + 100; NN.chronicle(C, S) end
local dup = false; for i = m0 + 1, #MSGS do if MSGS[i]:find("Caravan near.", 1, true) then dup = true end end
check(not dup and NM.chronicled(cid) == true and logged("already in the journal via Rumors"), "journaled by Rumors: no second line")
KMM_Rumors = { journaled = function() error("boom") end }
em("caravan_lost", "Caravan two."); CLOCK = CLOCK + 100; NN.chronicle(C, S); CLOCK = CLOCK + 100; NN.chronicle(C, S)
local seen2 = false; for _, l in ipairs(MSGS) do if l:find("Caravan two.", 1, true) then seen2 = true end end
check(seen2, "Rumors.journaled error -> written as before")
KMM_Rumors = nil
ManagementScreen = nil
check(next(NM.disabled()) == nil and not NN.beat_off and not NN.appr_off, "nothing disabled")
RESULT = #FAILS == 0 and ("OK " .. N) or ("FAIL: " .. table.concat(FAILS, "; "))
'''.replace("TMPDIR", TMP), "test")
L.lua_getfield.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_char_p]
L.lua_getfield(st, -10002, b"RESULT")
r = L.lua_tolstring(st, -1, None).decode()
print(r)
sys.exit(0 if r.startswith("OK") else 1)
