"""Offline test KMM_Rumors NEWS: слухи с задержкой по расстоянию, крупные события быстрее, вестники (путники Traces) приносят вести сразу,
порядок ближние-первыми, обратная совместимость told-списка. python -I -X utf8 build/KMM_Rumors/_dev/test_news.py -> OK."""
import ctypes, re, sys, tempfile

DLL = r"C:\Program Files (x86)\Steam\steamapps\workshop\content\233860\3817000612\lua51.dll"
B = r"C:\KenshiModMap\build"
TMP = tempfile.mkdtemp(prefix="kmm_news_").replace("\\", "/")
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
for _f in sorted(__import__("glob").glob(B + r"\KMM_Conductor\scripts\init\KMM_Conductor*.lua")): run(open(_f, encoding="utf-8").read(), _f.split("\\")[-1])
run(open(B + r"\KMM_Rumors\scripts\init\KMM_Rumors.lua", encoding="utf-8").read(), "KMM_Rumors.lua")
run(r'''
N, FAILS = 0, {}
function check(c, what) N = N + 1; if not c then FAILS[#FAILS + 1] = what end end
local C, R = KMM_Conductor, KMM_Rumors
local hs = Events.h["GameWorld::charsUpdate"]; Events.h["GameWorld::charsUpdate"] = { hs[#hs] }   -- только тик Rumors: дирижёр не плодит свои события
C.reset()
R.CFG.SMALLTALK_ON = false   -- B1 V4 мелочь города проверяет test_visibility.py; здесь — только слухи
local TI = C.cfg().town_info
local function dist(a, b) return math.sqrt((a.x - b.x) ^ 2 + (a.z - b.z) ^ 2) end
-- игрок стоит в городе A; B близко (<12k, но >0), F далеко (>100k)
local A, Bn, Fr
local sids = {}; for sid in pairs(TI) do sids[#sids + 1] = sid end; table.sort(sids)   -- детерминированно: город A, у которого есть сосед 3–12k и дальний >110k
for _, sa in ipairs(sids) do
  local IA = TI[sa]
  if IA.x and IA.kind == "city" then
    local a0, b0, f0 = { sid = sa, x = IA.x, z = IA.z }, nil, nil
    for _, sid in ipairs(sids) do
      local I = TI[sid]
      if I.x and sid ~= sa then
        local d = dist(a0, I)
        if not b0 and d > 3000 and d < 12000 then b0 = { sid = sid, x = I.x, z = I.z, d = d } end
        if not f0 and d > 110000 then f0 = { sid = sid, x = I.x, z = I.z, d = d } end
      end
    end
    if b0 and f0 then A, Bn, Fr = a0, b0, f0; break end
  end
end
check(A and Bn and Fr, "towns picked")
SAID = {}
local town = { getName = function() return "TownA" end }
local pc = MKCH("PC1", "player", A.x, A.z, { player = true })
local npc = MKCH("Barman", "x", A.x + 100, A.z, {})
npc.data = { name = "barman" }
function npc:say(t) SAID[#SAID + 1] = t end
function pc:getCurrentTownLocation() return town end
function npc:getCurrentTownLocation() return town end
PCS = { pc }; CHARS = { pc, npc }

local function reset_state() R.told, R.townLastHour, R.heard, R.lastHours, R.forms = {}, {}, {}, nil, {}; SAID = {} end   -- forms: годовой учёт форм — свой у каждого сценария
local function setevents(list)
  local S = C.state(); S.events = {}
  for i, e in ipairs(list) do e.id = i; S.events[#S.events + 1] = e end
  R.lastCheck = -1e9
end
local function tick() CLOCK = CLOCK + 100; R.lastCheck = -1e9; FIRE("GameWorld::charsUpdate", {}) end
local function at(day) DAYV = day end

-- 0. параметры/калибровка
local dnear = R.news.delay({ type = "raid" }, Bn.x, Bn.z, A.x, A.z)
local dfar, dd = R.news.delay({ type = "raid" }, Fr.x, Fr.z, A.x, A.z)
local dbig = R.news.delay({ type = "faction_fell" }, Fr.x, Fr.z, A.x, A.z)
check(dnear > 0 and dnear < 1, "сосед < 1 дня: " .. dnear)
check(dfar > 5 and dfar <= R.CFG.NEWS_MAX_DAYS, "далёкое 5..7 дней: " .. dfar)
check(dbig < dfar, "крупное быстрее")
check(R.news.delay({ type = "raid" }, A.x, A.z, A.x, A.z) == 0, "в своём городе 0 дней")
local dnc = R.news.delay({ type = "raid" }, nil, nil, A.x, A.z)
check(dnc == R.CFG.NEWS_NOCOORD_DAYS, "без координат общая задержка")

-- 1. близкое доступно сразу (в тот же день, что и событие, плюс задержка в часах), далёкое — нет
reset_state()
setevents({ { type = "raid", day = 10, town_sid = A.sid, a = nil, b = nil, attacker = "Raiders", defender = "Folk", town_name = "Here" },
            { type = "raid", day = 10, town_sid = Fr.sid, attacker = "FarRaiders", defender = "FarFolk", town_name = "Faraway" } })
at(10.0); tick()
check(#SAID == 1 and SAID[1]:find("Raiders", 1, true), "близкое сказано сразу: " .. tostring(SAID[1]))
at(10.0 + 2.5); R.townLastHour = {}; tick()    -- далёкое ещё в пути (2.5 дня < 7)
check(#SAID == 1, "далёкое ещё не дошло через 2.5 дня")
at(10.0 + dfar - 0.2); R.townLastHour = {}; tick()
check(#SAID == 1, "далёкое не дошло за 0.2 дня до срока")
at(10.0 + dfar + 0.05); R.townLastHour = {}; tick()
check(#SAID == 2, "далёкое пришло через ~" .. dfar .. " дней")

-- 2. крупное событие идёт быстрее обычного на том же расстоянии
reset_state()
setevents({ { type = "faction_fell", day = 20, town_sid = Fr.sid, attacker = "Dead", defender = "", town_name = "Faraway" } })
at(20 + dbig - 0.1); tick(); check(#SAID == 0, "крупное: рано")
at(20 + dbig + 0.05); tick(); check(#SAID == 1 and dbig < dfar, "крупное: пришло раньше потолка")

-- 3. вестник: путник рядом с игроком из далёкого города -> новость сразу
reset_state()
setevents({ { type = "raid", day = 30, town_sid = Fr.sid, attacker = "FarRaiders", defender = "FarFolk", town_name = "Faraway" } })
at(30.05); tick(); check(#SAID == 0, "без вестника далёкое молчит")
TRAV = { { kind = "refugees", fid = "x", from = Fr.sid, to = A.sid, sx = Fr.x, sz = Fr.z, lx = A.x + 500, lz = A.z } }
rawset(_G, "KMM_Traces", { travelers = function() return TRAV end })
R.townLastHour = {}; tick()
check(#SAID == 1 and SAID[1]:find("FarRaiders", 1, true), "вестник принёс далёкую весть сразу: " .. tostring(SAID[1]))
check(SAID[1]:find("Newcomers", 1, true), "с пометкой путников")
check(R.heard["1"], "heard помечено")
-- вестник далеко от игрока — не считается
reset_state()
setevents({ { type = "raid", day = 40, town_sid = Fr.sid, attacker = "FarRaiders", defender = "FarFolk", town_name = "Faraway" } })
TRAV[1].lx = A.x + 50000
at(40.05); tick(); check(#SAID == 0 and not next(R.heard), "далёкий путник не вестник")
-- вестник из другого края: вести не про его место не приносит
TRAV[1].lx = A.x + 500; TRAV[1].from = A.sid; TRAV[1].sx = A.x; TRAV[1].sz = A.z
tick(); check(#SAID == 0, "путник из соседнего места не знает дальних новостей")
-- сломанный Traces не валит модуль
rawset(_G, "KMM_Traces", { travelers = function() error("boom") end })
tick(); check(not R.disabled, "ошибка travelers не отключает модуль")
rawset(_G, "KMM_Traces", nil)

-- 4. порядок: ближние раньше дальних (оба уже доступны)
reset_state()
setevents({ { type = "raid", day = 50, town_sid = Fr.sid, attacker = "FarRaiders", defender = "FarFolk", town_name = "Faraway" },
            { type = "raid", day = 50, town_sid = Bn.sid, attacker = "NearRaiders", defender = "NearFolk", town_name = "Nearby" } })
at(50 + 8); tick()
check(#SAID == 1 and SAID[1]:find("Near", 1, true), "ближнее первым: " .. tostring(SAID[1]))
R.townLastHour = {}; tick()
check(#SAID == 2 and SAID[2]:find("Far", 1, true), "потом дальнее")

-- 5. сейв: heard пишется отдельными строками "@id"; старый формат читается; повторная загрузка
reset_state()
R.told["1|TownA"] = true; R.heard["2"] = true   -- id есть в журнале дирижёра (раздел 4): сохранение чистит только исчезнувшие
local gd = { sdata = {} }
FIRE("PlayerInterface::serialise", nil, gd)
local blob = gd.sdata.kmm_rumors_told
check(blob and blob:find("@2", 1, true) and blob:find("1|TownA", 1, true), "сохранено в sdata")
R.told, R.heard = {}, {}
FIRE("PlayerInterface::loadFromSerialise", nil, gd)
check(R.told["1|TownA"] and R.heard["2"], "восстановлено")
R.told, R.heard = {}, {}
gd.sdata.kmm_rumors_told = "1|TownA\n2|TownB"      -- старый сейв без heard
FIRE("PlayerInterface::loadFromSerialise", nil, gd)
check(R.told["1|TownA"] and R.told["2|TownB"] and next(R.heard) == nil, "старый сейв читается")
check(not R.told["@2"], "heard не попал в told")

io.write(string.format("checks=%d fails=%d\n", N, #FAILS))
for _, f in ipairs(FAILS) do io.write("FAIL: " .. f .. "\n") end
FAILED = #FAILS
''', "test")
L.lua_getfield.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_char_p]
run("if FAILED ~= 0 then error('news test failed') end", "result")
print("OK")
