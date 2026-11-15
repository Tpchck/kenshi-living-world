"""Offline test KMM_Rumors R2 (слух — наводка на карте): сказанный слух о месте открывает город на ванильной карте
(setDiscovered + setRecentlyDiscovered), уже открытое не тратит лимит, дневной лимит, точка боя (x/z), далёкий/искажённый слух
ничего не открывает, разыскиваемый с живым отрядом — addSquadToMap на срок и removeSquadFromMap, ушедший отряд не трогаем,
ошибка движка выключает только карту. python -I -X utf8 build/KMM_Rumors/_dev/test_r2_map.py -> OK."""
import ctypes, re, sys, tempfile

DLL = r"C:\Program Files (x86)\Steam\steamapps\workshop\content\233860\3817000612\lua51.dll"
B = r"C:\KenshiModMap\build"
TMP = tempfile.mkdtemp(prefix="kmm_r2_").replace("\\", "/")
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
for _f in sorted(__import__("glob").glob(B + r"\KMM_Conductor\scripts\init\KMM_Conductor*.lua")): run(open(_f, encoding="utf-8").read(), _f.split("\\")[-1])
run(open(B + r"\KMM_Rumors\scripts\init\KMM_Rumors.lua", encoding="utf-8").read(), "KMM_Rumors.lua")
run(r'''
N, FAILS = 0, {}
function check(c, what) N = N + 1; if not c then FAILS[#FAILS + 1] = what end end
local C, R = KMM_Conductor, KMM_Rumors
local hs = Events.h["GameWorld::charsUpdate"]; Events.h["GameWorld::charsUpdate"] = { hs[#hs] }
C.reset()
R.CFG.SMALLTALK_ON = false   -- B1 V4 мелочь города проверяет test_visibility.py; здесь — только слухи
local TI = C.cfg().town_info
local sids = {}; for sid in pairs(TI) do sids[#sids + 1] = sid end; table.sort(sids)
local A, Bn
for _, sa in ipairs(sids) do
  local IA = TI[sa]
  if IA.x and IA.kind == "city" then
    for _, sb in ipairs(sids) do
      local I = TI[sb]
      if I.x and sb ~= sa then
        local d = math.sqrt((I.x - IA.x) ^ 2 + (I.z - IA.z) ^ 2)
        if d > 3000 and d < 12000 then A, Bn = { sid = sa, x = IA.x, z = IA.z }, { sid = sb, x = I.x, z = I.z }; break end
      end
    end
    if A then break end
  end
end
check(A and Bn, "towns picked")
-- города ядра: TownBase-заглушки с флагами карты; warMgr любой фракции отдаёт ближайший из них
PLACES = {}
local function mktown(name, x, z, disc)
  local t = { name = name, x = x, z = z, disc = disc, rec = false }
  function t:getPosition() return { x = self.x, y = 0, z = self.z } end
  function t:getName() return self.name end
  function t:isDiscovered() return self.disc end
  function t:setDiscovered(v) if SETDISC_FAIL then error("engine boom") end; self.disc = v end
  function t:setRecentlyDiscovered(v) self.rec = v end
  PLACES[#PLACES + 1] = t
  return t
end
local WM = { getNearestTown = function(self, p)
  local best, bd
  for _, t in ipairs(PLACES) do local d = (t.x - p.x) ^ 2 + (t.z - p.z) ^ 2; if not bd or d < bd then best, bd = t, d end end
  return best
end }
local FAC0 = FAC
FAC = function(id) local f = FAC0(id); f.warMgr = WM; return f end
local TA = mktown("HomeTown", A.x, A.z, true)
local TB = mktown("NearTown", Bn.x, Bn.z, false)
-- окно управления и разыскиваемые
ADDS, REMS = 0, 0
MS = { addSquadToMap = function(self, p) ADDS = ADDS + 1; p.onmap = true end, removeSquadFromMap = function(self, p) REMS = REMS + 1; p.onmap = false end }
ManagementScreen = { getSingleton = function() return MS end }
local PL = { key = "gang1" }
OUTL = { { i = 7, n = "Grim Jaw", pg = { base = "Hungry Bandit", aka = { "Old Jaw" } } } }
LIVE = { o7 = { pl = PL } }
rawset(_G, "KMM_Outlaws", { wanted = function() return OUTL end, live = function() return LIVE end })

SAID = {}
local town = { getName = function() return "TownA" end }
local pc = MKCH("PC1", "player", A.x, A.z, { player = true })
local npc = MKCH("Barman", "x", A.x + 100, A.z, {})
npc.data = { name = "barman" }
function npc:say(t) SAID[#SAID + 1] = t end
function pc:getCurrentTownLocation() return town end
function npc:getCurrentTownLocation() return town end
PCS = { pc }; CHARS = { pc, npc }

local function logtext() local f = io.open("C:/KenshiModMap/logs/rumors.log", "r"); if not f then return "" end; local s = f:read("*a"); f:close(); return s end
local function count(pat) local n = 0; for _ in logtext():gmatch(pat) do n = n + 1 end; return n end
local function has(s) return logtext():find(s, 1, true) ~= nil end
local function reset_state() R.told, R.townLastHour, R.heard, R.lastHours = {}, {}, {}, nil; SAID = {} end
local function setevents(list)
  local S = C.state(); S.events = {}
  for i, e in ipairs(list) do e.id = i; S.events[#S.events + 1] = e end
end
local function tick() CLOCK = CLOCK + 100; R.lastCheck = -1e9; R.townLastHour = {}; FIRE("GameWorld::charsUpdate", {}) end
local function at(day) DAYV = day end
R.CFG.MAP.MAX_PLACES_DAY = 1

-- 1. слух о соседнем городе: открыт на карте, маркер «новое место»
reset_state()
setevents({ { type = "attack_repelled", day = 10, town_sid = Bn.sid, b = "FB", a = "FA", attacker = "Raiders", defender = "Folk", town_name = "NearTown" } })
at(11); tick()
check(#SAID == 1, "слух сказан")
check(TB.disc == true and TB.rec == true, "город открыт + recentlyDiscovered")
check(has("map place ok event=1 type=attack_repelled place=NearTown"), "маркер map place ok")
check(R.map.places == 1, "счётчик дня 1")

-- 2. уже открытый город: без вызовов, лимит не тратится
reset_state(); R.map.places = 0
setevents({ { type = "famine", day = 12, town_sid = A.sid, a = "FA", attacker = "Folk", town_name = "HomeTown" } })
at(12.2); tick()
check(#SAID == 1 and has("map place known event=1 type=famine place=HomeTown"), "known: " .. tostring(SAID[1]))
check(R.map.places == 0, "known не тратит лимит")

-- 3. точка x/z (руина), дневной лимит, на следующий день — снова можно
local TC = mktown("RuinC", Bn.x + 600, Bn.z + 8000, false)
local TD = mktown("CampD", Bn.x - 600, Bn.z - 8000, false)
reset_state()
setevents({ { type = "ruin_expedition", day = 20, b = "FR", attacker = "Diggers", town_name = "RuinC", x = TC.x, z = TC.z } })
at(21); tick()
check(TC.disc == true, "руина по точке x/z открыта")
reset_state()
setevents({ { type = "raid", day = 19.5, b = "FD", attacker = "Thugs", defender = "Folk", town_name = "CampD", x = TD.x, z = TD.z } })
at(21.3); tick()
check(#SAID == 1 and TD.disc == false and has("map place limit event=1 place=CampD"), "лимит дня держит")
reset_state()
setevents({ { type = "raid", day = 19.5, b = "FD", attacker = "Thugs", defender = "Folk", town_name = "CampD", x = TD.x, z = TD.z } })
at(22.1); tick()
check(TD.disc == true, "новый день — лимит сброшен")

-- 4. место далеко от любого известного города -> miss no_town; событие без места -> miss no_xz
reset_state()
setevents({ { type = "raid", day = 30, b = "FB", attacker = "X", defender = "Y", x = A.x + 40000, z = A.z } })
at(33); tick()
check(#SAID == 1 and has("map place miss event=1 type=raid reason=no_town"), "далеко от городов: no_town")
reset_state()
setevents({ { type = "ore_crisis", day = 34 } })
at(36); tick()
check(#SAID == 1 and has("reason=no_xz"), "без места: no_xz")

-- 5. искажённый слух (бандит, уровень 2) ничего не открывает
local TE = mktown("LairE", Bn.x + 5000, Bn.z, false)
npc.data.name = "bandit"
reset_state()
setevents({ { type = "raid", day = 40, b = "FE", attacker = "Beasts", defender = "Folk", town_name = "LairE", x = TE.x, z = TE.z } })
at(41.5); tick()
check(#SAID == 1 and TE.disc == false and has("reason=vague level=2"), "искажённый слух: карта не трогается")
npc.data.name = "barman"

-- 6. разыскиваемый с живым отрядом рядом -> отряд на карте; срок -> снят; ушедший не трогаем
reset_state()
setevents({ { type = "outlaw_racket", day = 50, town_sid = A.sid, a = "Gang", b = "Law", leader_name = "Old Jaw", text = "Old Jaw shakes down traders." } })
at(51); tick()
check(#SAID == 1 and ADDS == 1 and PL.onmap == true, "addSquadToMap по прозвищу")
check(has("map squad ok event=1 type=outlaw_racket name=Old Jaw hours=24"), "маркер map squad ok")
at(51.5); tick()
check(PL.onmap == true and REMS == 0, "до срока на карте")
at(52.1); tick()
check(PL.onmap == false and REMS == 1 and has("map squad off name=Old Jaw remove=ok"), "срок вышел — removeSquadFromMap")
reset_state(); LIVE = {}
setevents({ { type = "outlaw_move", day = 60, town_sid = A.sid, leader_name = "Grim Jaw", text = "Grim Jaw moved in." } })
at(61); tick()
check(ADDS == 1 and has("name=Grim Jaw reason=not_live"), "не рядом: not_live")
reset_state()
setevents({ { type = "nemesis_trail", day = 62, town_sid = A.sid, leader_name = "Nobody Known", text = "Nobody Known asks after you." } })
at(63); tick()
check(has("name=Nobody Known reason=no_record"), "нет записи: no_record")
reset_state(); LIVE = { o7 = { pl = PL } }
setevents({ { type = "nemesis_dead", day = 64, town_sid = A.sid, leader_name = "Grim Jaw", status = "dead", text = "Grim Jaw is dead." } })
at(65); tick()
check(ADDS == 1, "мёртвый не на карте")
reset_state()
setevents({ { type = "outlaw_rise", day = 66, town_sid = A.sid, leader_name = "Grim Jaw", text = "Grim Jaw grows bold." } })
at(67); tick()
check(ADDS == 2, "снова на карте")
LIVE = {}
at(68.2); tick()
check(REMS == 1 and has("map squad gone name=Grim Jaw") and next(R.map.live) == nil, "ушедший отряд не трогаем")

-- 7. ошибка движка выключает только карту; слухи идут дальше
local TF = mktown("FortF", Bn.x, Bn.z + 5000, false)
SETDISC_FAIL = true
reset_state()
setevents({ { type = "raid", day = 70, b = "FF", attacker = "A", defender = "B", town_name = "FortF", x = TF.x, z = TF.z } })
at(71); tick()
check(#SAID == 1 and R.map.off == true and not R.disabled, "ошибка -> карта выключена, модуль жив")
check(has("map disabled until restart in place"), "маркер map disabled")
SETDISC_FAIL = false
reset_state()
setevents({ { type = "raid", day = 72, b = "FF", attacker = "A", defender = "B", town_name = "FortF", x = TF.x, z = TF.z } })
at(73); tick()
check(#SAID == 1 and TF.disc == false, "после выключения карта не трогается, слух сказан")
check(R.status():find("map_off=true", 1, true), "status: " .. R.status())

io.write(string.format("checks=%d fails=%d\n", N, #FAILS))
for _, f in ipairs(FAILS) do io.write("FAIL: " .. f .. "\n") end
FAILED = #FAILS
''', "test")
run("if FAILED ~= 0 then error('r2 map test failed') end", "result")
print("OK")
