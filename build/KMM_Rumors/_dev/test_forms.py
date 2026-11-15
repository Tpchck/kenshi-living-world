"""Offline test KMM_Rumors B1 формы речи: у каждого типа ≥4 формы разной манеры; форма (тип#номер) не звучит дважды за 365 игровых дней,
через 366 — снова можно; все формы типа за год сказаны — берётся другое событие или мелочь города; бытовая болтовня повторяется свободно;
вес формы по роли рассказчика; учёт в сейве (старый сейв без поля читается), чистка старше года и потолок размера.
python -I -X utf8 tools/test/log_sandbox.py build/KMM_Rumors/_dev/test_forms.py -> OK."""
import ctypes, glob, os, re, tempfile

DLL = r"C:\Program Files (x86)\Steam\steamapps\workshop\content\233860\3817000612\lua51.dll"
B = r"C:\KenshiModMap\build"
TMP = tempfile.mkdtemp(prefix="kmm_forms_").replace("\\", "/")
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
run("math.randomseed(20261116)", "seed")
for _f in sorted(glob.glob(B + r"\KMM_Conductor\scripts\init\KMM_Conductor*.lua")):
    run(open(_f, encoding="utf-8").read(), os.path.basename(_f))
SRC = open(B + r"\KMM_Rumors\scripts\init\KMM_Rumors.lua", encoding="utf-8").read()
run(SRC, "KMM_Rumors.lua")
run(r'''
N, FAILS = 0, {}
function check(c, what) N = N + 1; if not c then FAILS[#FAILS + 1] = what end end
local C, R = KMM_Conductor, KMM_Rumors
local hs = Events.h["GameWorld::charsUpdate"]; Events.h["GameWorld::charsUpdate"] = { hs[#hs] }
C.reset()
local TI = C.cfg().town_info
local sids = {}; for sid in pairs(TI) do sids[#sids + 1] = sid end; table.sort(sids)
local A
for _, sa in ipairs(sids) do if TI[sa].x and TI[sa].kind == "city" then A = { sid = sa, x = TI[sa].x, z = TI[sa].z }; break end end
check(A, "town picked")
SAID = {}
local TOWNNAME = "TownA"
local town = { getName = function() return TOWNNAME end, getGameData = function() return { stringID = A.sid } end }
local pc = MKCH("PC1", "player", A.x, A.z, { player = true })
local bar = MKCH("Barman", "x", A.x + 100, A.z, {}); bar.data = { name = "barman" }
function bar:say(t) SAID[#SAID + 1] = t end
function bar:getCurrentTownLocation() return town end
function pc:getCurrentTownLocation() return town end
PCS = { pc }; CHARS = { pc, bar }
local function logtext() local f = io.open("C:/KenshiModMap/logs/rumors.log", "r"); if not f then return "" end; local s = f:read("*a"); f:close(); return s end
local function reset_state()
  R.told, R.townLastHour, R.heard, R.lastHours, R.townCount, R.smallHour = {}, {}, {}, nil, {}, {}
  R.visit, R.spk, R.noisyDay, R.lastTellClock, R.jq, R.jday, R.forms, R.formSkip = nil, nil, nil, nil, {}, { day = -1, n = 0 }, {}, nil
  SAID = {}
end
local function setevents(list) local S = C.state(); S.events = {}; for i, e in ipairs(list) do e.id = i; e.town_sid = e.town_sid or A.sid; S.events[#S.events + 1] = e end end
-- такт без окна города и потолка рассказчика: проверяем только годовой учёт форм
local function tick() CLOCK = CLOCK + 100; R.lastCheck = -1e9; R.townLastHour = {}; R.spk = nil; FIRE("GameWorld::charsUpdate", {}) end
local function at(day) DAYV = day end
local function formsOf(ty) local n = 0; for k in pairs(R.forms) do if k:sub(1, #ty + 1) == ty .. "#" then n = n + 1 end end; return n end
R.CFG.SMALLTALK_ON = false

-- 1. у каждого типа с шаблоном ≥4 разных форм; обёртка для готового текста ≥4; без иероглифов и без незаменённых %МЕТОК%
do
  local n, short = 0, {}
  local types = {}
  for k, v in pairs(R.T.en) do types[k] = v end
  check(next(types) ~= nil, "таблица форм доступна")
  for ty, pool in pairs(types) do
    if type(pool) == "table" and not ({ cats = 1, dirs = 1, hedge = 1, small = 1 })[ty] then
      n = n + 1
      local seen, dif = {}, 0
      for _, f in ipairs(pool) do if not seen[f] then seen[f] = true; dif = dif + 1 end end
      if dif < 4 then short[#short + 1] = ty .. ":" .. dif end
    end
  end
  table.sort(short)
  check(n >= 60 and #short == 0, "формы >= 4 у каждого типа (типов " .. n .. "): " .. table.concat(short, ","))
end
local ev0 = { leader = "Lady Sanda", town = "Bark", att = "Raiders", def = "Folk", cat = "food", text = "Somebody did something near Bark." }
local bad = {}
for ty, pool in pairs(R.T.en) do
  if type(pool) == "table" and not ({ cats = 1, dirs = 1, hedge = 1, small = 1, wrap = 1 })[ty] then
    for i = 1, #pool * 3 do
      R.forms = {}
      local e = {}; for k, v in pairs(ev0) do e[k] = v end; e.type = ty
      local s = R.fn.compose(e, 0, 1000, "n", 1, "default", 10)
      if not s or s:find("%", 1, true) then bad[#bad + 1] = ty .. "=" .. tostring(s) end
    end
  end
end
check(#bad == 0, "compose всех форм без остатков меток: " .. table.concat(bad, " | "))

-- 2. одна форма — не дважды за год: 4 события одного типа (4 формы) -> 4 разные формы, пятое молчит
reset_state()
local list = {}
for i = 1, 5 do list[#list + 1] = { type = "revolt", day = 100, attacker = "A" .. i, defender = "D" .. i, town_name = "Town" .. i } end
setevents(list)
at(100.2); for _ = 1, 7 do tick() end
check(#SAID == 4 and formsOf("revolt") == 4, "4 формы revolt за год, пятого нет: said=" .. #SAID .. " forms=" .. formsOf("revolt"))
local uniq = {}; for _, s in ipairs(SAID) do uniq[s] = true end
local nu = 0; for _ in pairs(uniq) do nu = nu + 1 end
check(nu == 4, "все 4 фразы разные")
check(logtext():find("reason=forms_used type=revolt", 1, true), "маркер skip reason=forms_used")
-- 3. через 364 дня ещё нельзя, через 366 — можно
at(100.2 + 364); tick()
check(#SAID == 4, "через 364 дня форма ещё занята")
-- исчерпание -> другое событие
setevents({ list[1], list[2], list[3], list[4], list[5], { type = "famine", day = 464, attacker = "Hungry", town_name = "Bread" } })
at(464.3); tick()
check(#SAID == 5 and SAID[5]:find("Bread", 1, true) or (SAID[5] and SAID[5]:find("Hungry", 1, true)), "формы revolt заняты — сказано другое событие: " .. tostring(SAID[5]))
setevents({ { type = "revolt", day = 466, attacker = "New", defender = "Old", town_name = "Fresh" } })
at(466.5); R.told = {}; tick()
check(#SAID == 6 and SAID[6]:find("Fresh", 1, true), "через 366 дней форма снова свободна: " .. tostring(SAID[6]))
-- 4. исчерпание -> мелочь города (новостей больше нет)
reset_state(); R.CFG.SMALLTALK_ON = true; TOWNNAME = "Exhausted"
for i = 1, 4 do R.forms["revolt#" .. i] = 500 end
setevents({ { type = "revolt", day = 500, attacker = "X", defender = "Y", town_name = "Z" } })
at(500.2); tick(); CLOCK = CLOCK + R.CFG.ENTRY_DELAY_SEC; tick()
check(#SAID == 1 and logtext():find("smalltalk town=Exhausted", 1, true), "формы заняты — мелочь города: " .. tostring(SAID[1]))
-- 5. готовый текст (fate_*): 4 формы-обёртки, пятое событие того же типа молчит
reset_state(); R.CFG.SMALLTALK_ON = false; TOWNNAME = "TownA"
list = {}
for i = 1, 5 do list[#list + 1] = { type = "fate_death", day = 600, text = "Hero" .. i .. " was killed near Bark." } end
setevents(list); at(600.2); for _ = 1, 7 do tick() end
check(#SAID == 4 and formsOf("fate_death") == 4, "fate_death: 4 обёртки за год: " .. #SAID)
local wrapped = false; for _, s in ipairs(SAID) do if s:find("Word on the road", 1, true) then wrapped = true end end
check(wrapped, "обёртка «Word on the road» встречается")

-- 6. бытовая болтовня повторяется свободно и в учёт форм не попадает
reset_state(); R.CFG.SMALLTALK_ON = true; setevents({})
local kinds = {}
for v = 1, 12 do
  TOWNNAME = "Chat" .. (v % 2)          -- два города по очереди, кулдаун SMALLTALK_CD_HOURS прошёл
  at(700 + v); tick(); CLOCK = CLOCK + R.CFG.ENTRY_DELAY_SEC; tick()
end
check(#SAID == 12 and next(R.forms) == nil, "12 реплик болтовни подряд, учёт форм пуст: " .. #SAID)
local rep = {}; local dup = false; for _, s in ipairs(SAID) do if rep[s] then dup = true end; rep[s] = true end
check(dup, "болтовня может повторяться")
local opts = R.fn.small(A.sid, A.x, A.z)
local ck = {}; for _, o in ipairs(opts) do ck[o[1]] = o[3] end
check(ck.chat_weather and (ck.chat_guard or ck.chat_tense), "болтовня по ситуации: погода, стража")
rawset(_G, "KMM_Stock", { level = function(sid, cat) if cat == "food" then return 0.1 end return 1 end })
opts = R.fn.small(A.sid, A.x, A.z); ck = {}; for _, o in ipairs(opts) do ck[o[1]] = o[3] end
check(ck.chat_hunger == 3 and ck.chat_prices == 2, "голод в городе -> болтовня о голоде и ценах с весом")
rawset(_G, "KMM_Stock", nil)
R.CFG.SMALLTALK_ON = false

-- 7. вес формы по роли: стражник чаще прямо (1) и грубо (3), бармен — слухом (2) и с оценкой (4)
local cnt = { guard = { 0, 0, 0, 0 }, barman = { 0, 0, 0, 0 } }
R.forms = {}
for _, role in ipairs({ "guard", "barman" }) do for _ = 1, 4000 do local i = R.formsfn.pick(4, "x", role, nil); cnt[role][i] = cnt[role][i] + 1 end end
check(cnt.guard[1] > cnt.guard[2] and cnt.guard[3] > cnt.guard[4] and cnt.barman[2] > cnt.barman[1] and cnt.barman[4] > cnt.barman[3],
      string.format("веса манер: guard %d/%d/%d/%d barman %d/%d/%d/%d", cnt.guard[1], cnt.guard[2], cnt.guard[3], cnt.guard[4], cnt.barman[1], cnt.barman[2], cnt.barman[3], cnt.barman[4]))
R.forms = { ["x#1"] = 10, ["x#2"] = 10, ["x#3"] = 10 }
check(R.formsfn.pick(4, "x", "guard", 11) == 4, "свободна только 4-я форма")
R.forms["x#4"] = 10
check(R.formsfn.pick(4, "x", "guard", 11) == nil and R.formsfn.pick(4, "x", "guard", 376) ~= nil, "все заняты -> nil; через 366 дней свободны")

-- 8. сейв: учёт пишется отдельным полем; старый сейв без поля читается; файл-копия
reset_state(); at(800)
R.forms = { ["raid#1"] = 799.5, ["fate_death#3"] = 790 }
R.told = {}
local gd = { sdata = {} }
FIRE("PlayerInterface::serialise", nil, gd)
check(type(gd.sdata.kmm_rumors_forms) == "string" and gd.sdata.kmm_rumors_forms:find("raid#1\t799.50", 1, true), "учёт форм в сейве: " .. tostring(gd.sdata.kmm_rumors_forms))
R.forms = {}
FIRE("PlayerInterface::loadFromSerialise", nil, gd)
check(R.forms["raid#1"] == 799.5 and R.forms["fate_death#3"] == 790, "учёт форм восстановлен")
FIRE("PlayerInterface::loadFromSerialise", nil, { sdata = { kmm_rumors_told = "1|TownA\n@2" } })
check(next(R.forms) == nil and R.told["1|TownA"] and R.heard["2"], "старый сейв без поля форм читается")
check(logtext():find("forms ledger loaded from save: 0", 1, true), "маркер forms ledger loaded")

-- 9. чистка: старше года — долой; потолок размера — остаются свежие
R.forms = { ["a#1"] = 100, ["b#1"] = 400, ["c#1"] = 466 }
R.formsfn.prune(466.5)
check(R.forms["a#1"] == nil and R.forms["b#1"] == 400 and R.forms["c#1"] == 466, "старше 365 дней удалено")
R.forms = {}
for i = 1, 2600 do R.forms["t" .. i .. "#1"] = 100 + i * 0.1 end
local cut = R.formsfn.prune(400)
local nk = 0; for _ in pairs(R.forms) do nk = nk + 1 end
check(nk == R.CFG.FORMS_MAX and cut == 600 and R.forms["t2600#1"] and not R.forms["t1#1"], "потолок: " .. nk .. " cut=" .. tostring(cut))
-- время назад (новый мир) — учёт сброшен
R.forms = { ["raid#1"] = 900 }; R.lastHours = 900 * 24; at(5); tick()
check(next(R.forms) == nil, "новый мир — учёт форм пуст")

io.write(string.format("checks=%d fails=%d\n", N, #FAILS))
for _, f in ipairs(FAILS) do io.write("FAIL: " .. f .. "\n") end
FAILED = #FAILS
''', "test")
run("if FAILED ~= 0 then error('forms test failed') end", "result")
print("OK")
