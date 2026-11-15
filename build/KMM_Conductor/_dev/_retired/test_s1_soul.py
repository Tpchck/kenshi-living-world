"""Offline test S1: эхо павших (KMM_Predators EC) и починка запаха R4.
Запах: точка в незагруженной зоне -> источник у игрока; промахи зоны после первого успеха запах не выключают; без единого успеха
три промаха -> «smell api unavailable» (как раньше). Эхо: смерти с шины (deed killed, ev.n) копятся по ячейке; днём ничего; ночью
(часы ядра getTimeStamp_inGameHours) у места с >= echo_n смертями, игрок в 2000..5000 -> одна заявка Traces tag=soul_echo
(fid Soulbodies, шаблон Faint, n=1, size 3, со стороны места); on_spawn -> событие predator_soul_echo с текстом слуха и городом;
место раз, живая группа <= 1, за ночь <= 2, новая ночь — снова; игрок вплотную/далеко — нет; эхо считает смерти и при выключенном
запахе; фракции нет -> «soul echo off», заявок нет; ошибка шага выключает только эхо.
python -I -X utf8 build/KMM_Conductor/_dev/test_s1_soul.py -> OK."""
import ctypes, re, sys, tempfile, glob

DLL = r"C:\Program Files (x86)\Steam\steamapps\workshop\content\233860\3817000612\lua51.dll"
B = r"C:\KenshiModMap\build\KMM_Conductor\scripts\init"
TMP = tempfile.mkdtemp(prefix="kmm_s1_").replace("\\", "/")
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
run(r'''
ZS_CALLS, ZS_LVL = {}, 0
ZONE_NIL = function(v) return false end   -- true -> getZoneMap(v) = nil (зона не загружена)
NO_FAC = {}                               -- fid -> factionMgr вернёт nil (мод выключен)
local zs = {}
function zs:addSmell(t, key, pos) ZS_CALLS[#ZS_CALLS + 1] = { t = t, key = key, x = pos.x, z = pos.z }; if t ~= 0 then ZS_LVL = ZS_LVL + 0.5 end end
function zs:getGeneralSmellLevel(t) return ZS_LVL end
local zm = { zoneSmell = zs }
local gw0 = getGameWorld
getGameWorld = function()
  local g = gw0()
  g.zoneMgr = { getZoneMap = function(self, v) if ZONE_NIL(v) then return nil end; return zm end, isZoneLoadedT = function(self, v) return not ZONE_NIL(v) end }
  local fm = g.factionMgr
  g.factionMgr = { getFactionByStringID = function(self, id) if NO_FAC[id] then return nil end; return fm:getFactionByStringID(id) end }
  return g
end
'''.replace("TMPDIR", TMP), "zone stub")
run("math.randomseed(20261115)", "seed")
for f in [p.split("\\")[-1] for p in sorted(glob.glob(B + r"\KMM_Conductor*.lua"))] + ["KMM_Traces.lua", "KMM_Predators.lua"]:
    run(open(B + "\\" + f, encoding="utf-8").read(), f)
run('KMM_Predators.P.sdir = "%s/"' % TMP, "sdir")
run(r'''
N, FAILS = 0, {}
function check(c, what) N = N + 1; if not c then FAILS[#FAILS + 1] = what end end
local C, Pr, T = KMM_Conductor, KMM_Predators, KMM_Traces
C.reset()
C.advance(10); C.advance(16); DAYV = 16.5
local P = Pr.P
P.tick_gap = 0; P.daily_chance = 0
local pf = C.cfg().player_faction
local PX, PZ = 100000, 100000
PCS = {}; CHARS = {}
local ch = MKCH("PC1", pf or "player", PX, PZ, { player = true, platoon = "player_squad" })
PCS[1] = ch; CHARS[1] = ch
local function setpos(x, z) ch.getPosition = function() return { x = x, y = 5, z = z } end end
local function pump(n) for i = 1, (n or 1) do CLOCK = CLOCK + 10; DAYV = DAYV + 0.00001; FIRE("GameWorld::charsUpdate", {}) end end
local function rd(p) local f = io.open(p, "r"); if not f then return "" end local s = f:read("*a"); f:close(); return s end
local function lg() return rd("TMPDIR/predators.log") end
local function kill(x, z, n, b) C.emit({ type = "deed", kind = "killed", tone = "harm", a = "fA", b = b or "fB", n = n or 1, x = x, z = z, text = "t" }) end
local REQ = {}
local treq = T.request
T.request = function(j) REQ[#REQ + 1] = j; return true end
local EVS = {}
C.subscribe("predator_soul_echo", function(ev) EVS[#EVS + 1] = ev end)
pump(1)
-- A. запах: точка в незагруженной зоне -> источник у игрока
ZONE_NIL = function(v) return v.x ~= PX end
kill(PX + 50, PZ, 1, "fS1")
local c1 = ZS_CALLS[1] or {}
check(#ZS_CALLS == 1 and c1.x == PX and c1.z == PZ, "A: зона точки не загружена -> addSmell у игрока (" .. #ZS_CALLS .. ")")
check(lg():find("smell zone miss (no zone map)", 1, true) and lg():find("-> source at the player", 1, true), "A: маркер smell zone miss -> at the player")
check(lg():find("smell api ok:", 1, true) and Pr.sm.ok == 1, "A: маркер smell api ok (первый источник)")
-- B. после успеха промахи зоны (и у игрока тоже) запах не выключают
ZONE_NIL = function(v) return true end
for i = 1, 4 do Pr.sm.last = {}; kill(PX, PZ, 1, "fM" .. i) end
check(Pr.sm.off == false and (Pr.sm.st.miss or 0) >= 4, "B: 4 промаха после успеха -> запах жив (miss=" .. tostring(Pr.sm.st.miss) .. ")")
check(not lg():find("smell api unavailable", 1, true), "B: без «smell api unavailable»")
-- C. без единого успеха — три промаха выключают запах (как раньше), эхо при этом продолжает считать смерти
Pr.sm.ok = 0; Pr.sm.fails = 0
for i = 1, 3 do Pr.sm.last = {}; kill(PX, PZ, 1, "fN" .. i) end
check(Pr.sm.off == true and lg():find("smell api unavailable (zoneMgr/zoneSmell): no zone map", 1, true), "C: API ни разу не сработал -> smell off + маркер")
ZONE_NIL = function(v) return false end
-- D. эхо: смерти у места SX (игрок в 3000), днём — ничего
local e = Pr.slot()
e.echo = nil
local SX, SZ = PX + 3000, PZ
kill(SX, SZ, 2, "fE1"); kill(SX + 100, SZ, 2, "fE2")
local s = e.echo
local tot = 0; for _, c in pairs(s.c) do for _, r in ipairs(c.h) do tot = tot + r.n end end
check(tot == 4, "D: смерти посчитаны при выключенном запахе: " .. tot)
check(lg():find("soul echo: death killed x2", 1, true), "D: маркер soul echo: death")
DAYV = math.floor(DAYV) + 0.5; pump(2)   -- полдень
check(#REQ == 0, "D: днём заявок нет: " .. #REQ)
-- E. ночь: одна заявка, параметры
DAYV = math.floor(DAYV) + 0.9; pump(1)   -- 21.6 ч
local j = REQ[1] or {}
check(#REQ == 1 and j.tag == "soul_echo" and j.fid == "5007288-Soulbody.mod" and j.sid == "5007709-Soulbody.mod" and j.n == 1 and j.size == 3,
      "E: ночью заявка soul_echo (fid/sid/n/size): " .. #REQ .. " " .. tostring(j.sid))
check(j.from_x and math.abs(j.from_x - SX) <= 100 and j.on_spawn ~= nil, "E: со стороны места бойни, on_spawn есть")
check(lg():find("soul echo ready: faction 5007288-Soulbody.mod", 1, true) and lg():find("soul echo request: 5007709", 1, true), "E: маркеры ready/request")
pump(3)
check(#REQ == 1, "E: ожидание спавна — второй заявки нет")
-- F. спавн: событие слуха с городом, приказ, живая группа
local pl = { getSquadLeader = function() return nil end, getPlatoonStringID = function() return "soul_pl_1" end }
j.on_spawn({ pl })
local ev = EVS[1] or {}
check(#EVS == 1 and type(ev.text) == "string" and (ev.text:lower():find("pale", 1, true) or ev.text:lower():find("glowing", 1, true)) ~= nil, "F:событие predator_soul_echo с текстом слуха")
check(ev.x == j.from_x and ev.a == "5007288-Soulbody.mod" and (ev.town_name == nil or ev.text:find(ev.town_name, 1, true)), "F: место и город в событии")
check(lg():find("soul echo spawned: 1 squad(s) [soul_pl_1]", 1, true) and (e.stat.soul_echo or 0) == 1, "F: маркер soul echo spawned + stat")
-- G. второе место той же ночью: живая группа (отряд находится) держит лимит 1
FAC("5007288-Soulbody.mod").getActivePlatoons = function() return { pl } end
local S2X = PX - 3500
kill(S2X, PZ, 4, "fG1")
CLOCK = CLOCK + 700; pump(1)
check(#REQ == 1, "G: живая группа есть -> новой заявки нет: " .. #REQ)
-- H. группа пропала -> второе место той же ночью
FAC("5007288-Soulbody.mod").getActivePlatoons = function() return {} end
CLOCK = CLOCK + 700; pump(1)
check(#REQ == 2 and math.abs((REQ[2] or {}).from_x - S2X) <= 100, "H: группы нет -> заявка ко второму месту: " .. #REQ)
REQ[2].on_spawn({})
-- I. третье место той же ночью: потолок 2 за ночь
FAC("5007288-Soulbody.mod").getActivePlatoons = function() return {} end
P.echo_live_d = 0.0001
kill(PX, PZ + 4000, 4, "fI1")
CLOCK = CLOCK + 700; pump(1)
check(#REQ == 2, "I: потолок 2 за ночь: " .. #REQ)
-- J. новая ночь: место 3 снова можно; первое место отмечено (раз на место)
DAYV = math.floor(DAYV) + 1.9; kill(PX, PZ + 4000, 4, "fJ1"); kill(SX, SZ, 4, "fJ2")
CLOCK = CLOCK + 700; pump(1)
local j3 = REQ[3] or {}
check(#REQ == 3 and math.abs((j3.from_z or 0) - (PZ + 4000)) <= 100, "J: новая ночь -> заявка к новому месту, не к отмеченному: " .. #REQ)
if j3.on_spawn then j3.on_spawn({}) end
-- K. кольцо: игрок вплотную или далеко — нет
CLOCK = CLOCK + 700
s.nn = 0; s.done = {}; e.echo.c = {}
kill(PX + 500, PZ, 4, "fK1"); kill(PX + 9000, PZ, 4, "fK2")
pump(1)
check(#REQ == 3, "K: место ближе 2000 / дальше 5000 -> нет: " .. #REQ)
-- L. Traces отказал -> повтор через минуту, не через echo_gap
e.echo.c = {}; kill(SX, SZ, 4, "fL1")
T.request = function(jj) REQ[#REQ + 1] = jj; return false end
CLOCK = CLOCK + 700; pump(1)
local nf = #REQ
CLOCK = CLOCK + 65; pump(1)
check(#REQ == nf + 1, "L: отказ Traces -> повтор через минуту")
T.request = function(jj) REQ[#REQ + 1] = jj; return true end
-- M. фракции нет в игре -> тихо выключено
local EC = Pr.ec
EC.ready, EC.chk, EC.chk_t, EC.last = false, 0, -1e9, -1e9
NO_FAC["5007288-Soulbody.mod"] = true
s.nn = 0; s.done = {}; e.echo.c = {}; kill(SX, SZ, 4, "fM1")
local n0 = #REQ
for i = 1, 4 do CLOCK = CLOCK + 70; pump(1) end
check(EC.off == true and #REQ == n0 and lg():find("soul echo off: 5007288-Soulbody.mod not in game", 1, true), "M: фракции нет -> soul echo off, заявок нет")
check(not Pr.disabled(), "M: модуль Predators жив")
-- N. ошибка шага выключает только эхо
EC.off, EC.ready = false, true; NO_FAC = {}
local tr = T.request; T.request = function() error("boom") end
s.nn = 0; s.done = {}; e.echo.c = {}; kill(SX, SZ, 4, "fN1")
CLOCK = CLOCK + 700; pump(1)
check(EC.off == true and lg():find("soul echo disabled until restart", 1, true) and not Pr.disabled(), "N: ошибка эха -> только эхо выключено")
T.request = treq
-- O. реальный Traces принимает заявку (очередь EXT)
check(treq({ tag = "soul_echo", fid = "5007288-Soulbody.mod", sid = "5007709-Soulbody.mod", n = 1, size = 3, from_x = SX, from_z = SZ }) == true, "O: KMM_Traces.request принимает soul_echo")
local sz = 0; for _ in pairs(e.echo.c) do sz = sz + 1 end
check(sz <= P.echo_cells, "размер состояния ограничен")
RESULT = #FAILS == 0 and ("OK " .. N) or ("FAIL: " .. table.concat(FAILS, "; "))
'''.replace("TMPDIR", TMP), "test")
L.lua_getfield.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_char_p]
L.lua_getfield(st, -10002, b"RESULT")
r = L.lua_tolstring(st, -1, None).decode()
print(r)
sys.exit(0 if r.startswith("OK") else 1)
