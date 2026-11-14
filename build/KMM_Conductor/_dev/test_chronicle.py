"""Offline test KMM_Nemesis chronicle: крупные события хроники дирижёра -> журнал сообщений (ManagementScreen.getSingleton():addMessage); история при загрузке не вываливается, мелочь не идёт, пауза chron_gap_s, без окна — ждёт, ошибка addMessage выключает только хронику. Ниже — шапка из test_banter: свой из отряда игрока коротко отзывается о деле (соперник, должник, охотник, лидер), с паузой, только живой; память мира об игроке — избитый и оставленный жить/сбежавший становится соперником с прозвищем встречи, мститель за убитого, преследование по регионам, встреча с репликой и родной памятью ядра, повторная пощада, гибель. python -I -X utf8 build/KMM_Conductor/_dev/test_nemesis.py -> OK."""
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
C.cfg().params.nemesis = { rival_p_spared = 1, rival_p_fled = 0, avenger_p = 1, cooldown_days = 0, follow_p = 1, say_delay_s = 1, linger_s = 30 }
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
    function leader:rememberCharacter(who, tag) self.mem[#self.mem + 1] = tag end
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
CharacterPerceptionTags_LongTerm = { LT_DEFEATED_MY_SQUAD_ONCE = 7, LT_KILLED_MY_FRIEND = 9 }
local function tick(day) DAYV = day; CLOCK = CLOCK + 100; FIRE("GameWorld::charsUpdate", {}) end
local function evs(ty) local n, last = 0, nil; for _, e in ipairs(C.state().events) do if e.type == ty then n = n + 1; last = e end end; return n, last end
local D = O._M.data(C)
local rg, town
for nm, r in pairs(D.regions) do if #r.towns > 0 then rg, town = nm, r.towns[1]; break end end
local function mate(nm, opt)
  local c = MKCH(nm, pf or "player", town.x + 500, town.z + 500, opt or { player = true, platoon = "player_squad" })
  c.said = {}; function c:say(s) self.said[#self.said + 1] = s end
  return c
end

C.cfg().params.nemesis.ambient = false; C.cfg().params.nemesis.greet = false
local MSGS, MSOK, MSBAD = {}, true, false
local MSO = { addMessage = function(self, owner, msg, col) if MSBAD then error("bad call") end; MSGS[#MSGS + 1] = { owner, msg, col } end }
ManagementScreen = { getSingleton = function() return MSOK and MSO or nil end }
MessageLogColor = { ML_NORMAL = 0, ML_PLAYER = 1, ML_SYSTEM = 2 }
local TI = C.cfg().town_info or {}
local tsid, I; for k, v in pairs(TI) do if v.x then tsid, I = k, v; break end end
local farsid; for k, v in pairs(TI) do if v.x and (v.x - I.x) ^ 2 + (v.z - I.z) ^ 2 > 20000 ^ 2 then farsid = k; break end end
local pc = MKCH("Beep", pf or "player", I.x + 100, I.z + 100, { player = true, platoon = "player_squad" })
PCS = { pc }; CHARS = { pc }
local function fire(dt) CLOCK = CLOCK + dt; FIRE("GameWorld::charsUpdate", {}) end
local function msg_has(sub) for _, m in ipairs(MSGS) do if m[2]:find(sub, 1, true) then return true end end return false end
C.emit({ type = "town_captured", text = "OLD history line." })
tick(500)
fire(5)
check(not msg_has("OLD history"), "first load: history is not dumped")
local base = #MSGS
C.emit({ type = "town_captured", town_sid = tsid, text = "Shek Kingdom took Squin." })
C.emit({ type = "town_captured", town_sid = farsid, text = "Far away town fell." })
C.emit({ type = "raid", text = "Dust Bandits raided someone." })
C.emit({ type = "treaty_signed", a = pf, text = "A and B sealed a pact." })
fire(20)
check(#MSGS == base + 1 and msg_has("took Squin") and MSGS[#MSGS][1] == "Chronicle" and MSGS[#MSGS][3] == 2, "major event -> message log, system colour")
check(MSGS[#MSGS][2]:find("^Day %d+%. "), "line starts with game day")
fire(3)
check(#MSGS == base + 1, "gap between lines")
fire(20)
check(#MSGS == base + 2 and msg_has("sealed a pact"), "second major event after the gap")
check(not msg_has("raided someone"), "minor event (raid) not posted")
check(not msg_has("Far away town"), "distant event: left to Rumors (news travels), not posted")
MSOK = false
C.emit({ type = "revolt", town_sid = tsid, text = "Rebels rose in Stack." })
fire(20); fire(20)
check(not msg_has("Rebels rose"), "no window yet: line waits")
MSOK = true; fire(20)
check(msg_has("Rebels rose"), "window appears: waiting line posted")
MSBAD = true
C.emit({ type = "famine", town_sid = tsid, text = "Famine in the Hub." })
fire(20)
check(NM.chronicle_off() == true, "addMessage error: chronicle off")
check(next(NM.disabled()) == nil, "nemesis itself still enabled")
RESULT = #FAILS == 0 and ("OK " .. N) or ("FAIL: " .. table.concat(FAILS, "; "))
'''.replace("TMPDIR", TMP), "test")
run("")
L.lua_getfield.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_char_p]
L.lua_getfield(st, -10002, b"RESULT")
r = L.lua_tolstring(st, -1, None).decode()
print(r)
sys.exit(0 if r.startswith("OK") else 1)
