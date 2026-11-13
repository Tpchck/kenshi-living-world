"""Offline test KMM_RelicRace: экспедиции, видимый отряд, чемпион с реликтом у лидера, лимиты, гибель чемпиона. python -I -X utf8 build/KMM_Conductor/_dev/test_relicrace.py -> OK."""
import ctypes, re, sys, tempfile

DLL = r"C:\Program Files (x86)\Steam\steamapps\workshop\content\233860\3817000612\lua51.dll"
B = r"C:\KenshiModMap\build\KMM_Conductor\scripts\init"
TMP = tempfile.mkdtemp(prefix="kmm_relicrace_").replace("\\", "/")
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
run(open(B + r"\KMM_RelicRace.lua", encoding="utf-8").read(), "KMM_RelicRace.lua")
run(r'''
N, FAILS = 0, {}
function check(c, what) N = N + 1; if not c then FAILS[#FAILS + 1] = what end end
local C, T, RR = KMM_Conductor, KMM_Traces, KMM_RelicRace
C.reset()
local TP = C.cfg().params.traces
TP.first_hour_traces = 0; TP.max_per_day = 1000; TP.max_queue = 1000; TP.arrive_enabled = false
TP.bounty = { enabled = false }
local P = RR.P
P.start_s = 0; P.check_s = 0; P.first_gap = { 0, 0 }; P.gap = { 2, 3 }; P.vis_chance = 1; P.vis_cd = 0; P.champ_spawn_cd = 1
P.ref2 = 1; P.ref3 = 1; P.vis_r = 400000; P.max_days = 8
P.sdir = "TMPSDIR/"   -- X4: файлы крэш-сторожа разбора руин - во временную папку
local S = C.state()
-- игрок рядом с самой сильной фракцией с позицией
local pf = C.cfg().player_faction
local best, bp = nil, -1
for fid, f in pairs(S.F) do if f.alive and not f.player and fid ~= pf and C.fpos(fid) and C.power(fid) > bp then best, bp = fid, C.power(fid) end end
local ox, oz = C.fpos(best)
PCS = {}; CHARS = {}
local ch = MKCH("PC1", pf or "player", ox + 500, oz + 500, { player = true, platoon = "player_squad" })
PCS[1] = ch; CHARS[1] = ch
-- платформа: createRandomSquad возвращает отряд с лидером, у которого видны addItem/equipItem
GIVEN, EQUIPPED = {}, {}
LEADER = { dead = false }
function LEADER:isDead() return self.dead end
function LEADER:getInventory() return { addItem = function(_, it) GIVEN[#GIVEN + 1] = it end, equipItem = function(_, it) EQUIPPED[#EQUIPPED + 1] = it end } end
local old = getGameWorld
getGameWorld = function()
  local w = old()
  local f0 = w.theFactory.createRandomSquad
  w.theFactory.createRandomSquad = function(...) f0(...); return { getSquadLeader = function() return LEADER end } end
  w.theFactory.createItem = function(_, gd) return { gd = gd } end
  return w
end
local function pump(n, dd) for i = 1, n do CLOCK = CLOCK + 80; DAYV = DAYV + (dd or 0.25); FIRE("GameWorld::charsUpdate", {}) end end
pump(4)
local evs = {}
C.subscribe("relic_*", function(ev) evs[ev.type] = (evs[ev.type] or 0) + 1 end)
local maxc, maxe, perfid, maxiss = 0, 0, true, 0
for i = 1, 700 do
  pump(1)
  local R = S.ext and S.ext.relicrace
  if R then
    local nc, ne = 0, 0
    for fid, ch in pairs(R.champ) do nc = nc + 1; maxiss = math.max(maxiss, ch.issued or 0) end
    for _ in pairs(R.exp) do ne = ne + 1 end
    maxc, maxe = math.max(maxc, nc), math.max(maxe, ne)
    if i == 500 and LEADER and next(R.champ) then LEADER.dead = true end
  end
end
local R = S.ext and S.ext.relicrace
check(R ~= nil, "S.ext.relicrace created")
check(RR.off == false, "module not disabled")
check(RR.stats.launched >= 2, "expeditions launched: " .. tostring(RR.stats.launched))
check((evs.relic_expedition or 0) >= 2 and (evs.relic_dig or 0) >= 1, "chronicle: launch+dig events")
check((T.stats().by_tag or {}).relic_exp and T.stats().by_tag.relic_exp >= 1, "visible expedition squad via Traces.request")
check(RR.stats.won >= 1 and (evs.relic_found or 0) >= 1, "success -> champion + relic_found: won=" .. tostring(RR.stats.won))
check((T.stats().by_tag or {}).relic_champ and T.stats().by_tag.relic_champ >= 1, "champion squad spawned")
check(#GIVEN >= 1 and #EQUIPPED >= 1, "relic given + equipped to leader: " .. #GIVEN .. "/" .. #EQUIPPED)
check(GIVEN[1] and GIVEN[1].gd and GIVEN[1].gd.stringID and GIVEN[1].gd.t ~= nil, "item created from gamedata sid with itemType")
check(maxc <= 4 and maxe <= P.max_exp, "limits champ<=4 exp<=2: " .. maxc .. "/" .. maxe)
check(RR.stats.champ_slain >= 1 and (evs.relic_champion_slain or 0) >= 1, "slain champion -> event")
check(maxiss >= 1 and maxiss <= 1 + P.champ_reissue_max, "relic issues per champion <= 1+reissue_max: " .. maxiss)
-- не более одного чемпиона на фракцию: ключ champ = fid уже уникален; проверка размера состояния
local function ser(v, d) if type(v) == "table" then local n = 2; for k, x in pairs(v) do n = n + #tostring(k) + 2 + ser(x) end return n end return #tostring(v) + 1 end
local sz = ser(R)
check(sz < 20000, "state size " .. sz)
-- сериализуемость
local okser = pcall(C.serialize)
check(okser, "conductor state serialisable")
RESULT = #FAILS == 0 and ("OK " .. N .. " launched=" .. RR.stats.launched .. " won=" .. RR.stats.won .. " lost=" .. RR.stats.lost .. " seen=" .. RR.stats.seen .. " champ=" .. RR.stats.champ_spawned .. " size=" .. sz) or ("FAIL: " .. table.concat(FAILS, "; "))
'''.replace("TMPSDIR", TMP), "test")
L.lua_getfield.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_char_p]
L.lua_getfield(st, -10002, b"RESULT")
r = L.lua_tolstring(st, -1, None).decode()
print(r)
sys.exit(0 if r.startswith("OK") else 1)
