"""Offline test KMM_Rumors B1 (видимость): глобальная память рассказанного (V2), несколько слухов за окно города,
приоритет свежим/крупным, журнал услышанного (V3), мелочь города при входе (V4), чистые имена (V6), слияние шума loot_carried/deed,
метрика VISIBILITY. python -I -X utf8 build/KMM_Rumors/_dev/test_visibility.py -> OK."""
import ctypes, glob, os, re, tempfile

DLL = r"C:\Program Files (x86)\Steam\steamapps\workshop\content\233860\3817000612\lua51.dll"
B = r"C:\KenshiModMap\build"
TMP = tempfile.mkdtemp(prefix="kmm_vis_").replace("\\", "/")
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
for _f in sorted(glob.glob(B + r"\KMM_Conductor\scripts\init\KMM_Conductor*.lua")):
    run(open(_f, encoding="utf-8").read(), os.path.basename(_f))
run(open(B + r"\KMM_Rumors\scripts\init\KMM_Rumors.lua", encoding="utf-8").read(), "KMM_Rumors.lua")
run(r'''
N, FAILS = 0, {}
function check(c, what) N = N + 1; if not c then FAILS[#FAILS + 1] = what end end
local C, R = KMM_Conductor, KMM_Rumors
local hs = Events.h["GameWorld::charsUpdate"]; Events.h["GameWorld::charsUpdate"] = { hs[#hs] }   -- только тик Rumors
C.reset()
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

-- журнал: окно управления с addMessage
MSGS = {}
MS = { addMessage = function(self, owner, msg, col) MSGS[#MSGS + 1] = { owner = owner, msg = msg, col = col } end,
       addSquadToMap = function() end, removeSquadFromMap = function() end }
ManagementScreen = { getSingleton = function() return MS end }
MessageLogColor = { ML_NORMAL = 0, ML_PLAYER = 1, ML_SYSTEM = 2 }

SAID = {}
local TOWNNAME = "TownA"
local town = { getName = function() return TOWNNAME end, getGameData = function() return { stringID = A.sid } end }
local pc = MKCH("PC1", "player", A.x, A.z, { player = true })
local function npc(name, tmpl, dx)
  local c = MKCH(name, "x", A.x + dx, A.z, {})
  c.data = { name = tmpl }
  function c:say(t) SAID[#SAID + 1] = { who = name, text = t } end
  function c:getCurrentTownLocation() return town end
  return c
end
local bar, trd = npc("Barman", "barman", 100), npc("Trader", "trader", 200)
function pc:getCurrentTownLocation() return town end
PCS = { pc }; CHARS = { pc, bar, trd }

local function logtext() local f = io.open("C:/KenshiModMap/logs/rumors.log", "r"); if not f then return "" end; local s = f:read("*a"); f:close(); return s end
local function reset_state()
  R.told, R.townLastHour, R.heard, R.lastHours, R.townCount, R.smallHour = {}, {}, {}, nil, {}, {}
  R.visit, R.spk, R.noisyDay, R.lastTellClock, R.jq, R.jday, R.forms = nil, nil, nil, nil, {}, { day = -1, n = 0 }, {}
  SAID, MSGS = {}, {}
end
local function setevents(list)
  local S = C.state(); S.events = {}
  for i, e in ipairs(list) do e.id = i; S.events[#S.events + 1] = e end
end
local function tick() CLOCK = CLOCK + 100; R.lastCheck = -1e9; FIRE("GameWorld::charsUpdate", {}) end
local function at(day) DAYV = day end
local function text(i) return SAID[i] and SAID[i].text or "" end
local function anyCJK()
  for _, s in ipairs(SAID) do for i = 1, #s.text do if s.text:byte(i) >= 0xE3 and s.text:byte(i) <= 0xEF then return s.text end end end
  for _, m in ipairs(MSGS) do for i = 1, #m.msg do if m.msg:byte(i) >= 0xE3 and m.msg:byte(i) <= 0xEF then return m.msg end end end
  return nil
end
local ev = function(t) t.town_sid = t.town_sid or A.sid; t.town_name = t.town_name or "HomeTown"; return t end   -- в своём городе: задержка 0

-- 1. несколько слухов за окно: до MAX_PER_TOWN, разные рассказчики, потом окно закрыто до TOWN_COOLDOWN_HOURS
reset_state()
setevents({ ev{ type = "raid", day = 10, attacker = "R1", defender = "F1" }, ev{ type = "raid", day = 10, attacker = "R2", defender = "F2" },
            ev{ type = "raid", day = 10, attacker = "R3", defender = "F3" }, ev{ type = "raid", day = 10, attacker = "R4", defender = "F4" } })
at(11.5); tick(); tick(); tick(); tick()
check(#SAID == R.CFG.MAX_PER_TOWN, "за окно MAX_PER_TOWN слухов: " .. #SAID)
check(SAID[1] and SAID[2] and SAID[1].who ~= SAID[2].who, "второй слух — другой рассказчик: " .. tostring(SAID[1] and SAID[1].who) .. "/" .. tostring(SAID[2] and SAID[2].who))
local seen = {}
for _, s in ipairs(SAID) do local k = s.text:match("R%d") or "?"; seen[k] = (seen[k] or 0) + 1 end
local dup = false; for _, n in pairs(seen) do if n > 1 then dup = true end end
check(not dup, "без повторов в окне")
at(11.5 + (R.CFG.TOWN_COOLDOWN_HOURS + 0.5) / 24); tick()
check(#SAID == 4, "после окна — четвёртый: " .. #SAID)

-- 2. глобальная память: в другом городе то же не пересказывают, пока есть нерассказанное
reset_state()
setevents({ ev{ type = "raid", day = 20, attacker = "Old", defender = "F" }, ev{ type = "raid", day = 20, attacker = "Newer", defender = "F" } })
at(20.2); tick()
check(#SAID == 1, "сказан один")
local first = text(1)
TOWNNAME = "TownB"; tick()
check(#SAID == 2 and text(2) ~= first, "в другом городе — другое событие: " .. text(2))
TOWNNAME = "TownC"; R.townLastHour = {}; tick()
check(#SAID == 2 or (SAID[3] and not SAID[3].text:find("Old", 1, true) and not SAID[3].text:find("Newer", 1, true)), "рассказанное не повторяется в третьем городе")
TOWNNAME = "TownA"

-- 3. приоритет: свежее крупное раньше старого обычного; близость — тай-брейк
reset_state()
setevents({ ev{ type = "raid", day = 28, attacker = "Stale", defender = "F" }, ev{ type = "town_captured", day = 30.4, attacker = "Conq", defender = "Lost" } })
at(30.5); tick()
check(text(1):find("Conq", 1, true), "свежее крупное первым: " .. text(1))

-- 4. журнал: каждый сказанный слух — строка во вкладке сообщений, коротко, с днём и городом
check(#MSGS == 1 and MSGS[1].msg:find("^Day 30, TownA: ") and MSGS[1].owner == SAID[1].who and MSGS[1].col == 0,
      "журнал: " .. tostring(MSGS[1] and MSGS[1].msg) .. " owner=" .. tostring(MSGS[1] and MSGS[1].owner))
check(logtext():find("journal: addMessage ok", 1, true), "маркер journal: addMessage ok")
R.CFG.JOURNAL_MAX_DAY = 1
setevents({ ev{ type = "raid", day = 30.4, attacker = "A1", defender = "F" }, ev{ type = "raid", day = 30.4, attacker = "A2", defender = "F" } })
reset_state(); tick(); tick()
check(#SAID == 2 and #MSGS == 1, "суточный потолок журнала: said=" .. #SAID .. " msgs=" .. #MSGS)
R.CFG.JOURNAL_MAX_DAY = 15
-- окна ещё нет: строка ждёт и уходит позже
reset_state(); ManagementScreen = { getSingleton = function() return nil end }
setevents({ ev{ type = "raid", day = 31, attacker = "Q1", defender = "F" } }); at(31.2); tick()
check(#SAID == 1 and #MSGS == 0 and #R.jq == 1, "без окна — в очереди")
ManagementScreen = { getSingleton = function() return MS end }; tick()
check(#MSGS == 1 and #R.jq == 0, "окно появилось — строка ушла")
-- ошибка addMessage выключает только журнал
reset_state(); local MS0 = MS
MS = { addMessage = function() error("engine boom") end }
setevents({ ev{ type = "raid", day = 32, attacker = "E1", defender = "F" }, ev{ type = "raid", day = 32, attacker = "E2", defender = "F" } }); at(32.2); tick(); tick()
check(#SAID == 2 and R.journalOff and not R.disabled, "ошибка журнала: слухи идут, журнал выключен")
MS = MS0; R.journalOff = nil

-- 5. чистые имена: никаких иероглифов, служебные хвосты убраны
reset_state()
setevents({ ev{ type = "raid", day = 40, attacker = "Raiders", defender = "Folk", town_name = "\229\164\177\230\142\167\231\154\132\230\173\166\229\163\171" },
            ev{ type = "herd_move", day = 40, text = "leviathans herds are leaving South Stone Camp for \229\164\177\230\142\167\231\154\132\230\173\166\229\163\171\229\174\158\233\170\140\229\174\164." },
            ev{ type = "attack_repelled", day = 40, attacker = "X", defender = "Y", town_name = "Large Bone Fiend Hollow (defunct and broken) 103" } })
at(40.3); tick(); tick(); tick()
check(#SAID == 3, "три слуха: " .. #SAID)
check(anyCJK() == nil, "нет иероглифов: " .. tostring(anyCJK()))
local all = ""; for _, s in ipairs(SAID) do all = all .. s.text .. "\n" end
check(all:find("a place to the", 1, true) or all:find("somewhere out in the wastes", 1, true), "описание места вместо иероглифов: " .. all)
check(all:find("Leviathans herds", 1, true), "первая буква заглавная")
check(not all:find("defunct", 1, true) and not all:find(" 103", 1, true) and all:find("Large Bone Fiend Hollow", 1, true), "служебный хвост убран: " .. all)
local cn = R.clean.name("Abc \230\173\166 (x)", "FALLBACK"); check(cn == "FALLBACK", "грязное имя -> fallback")
check(R.clean.name("Squin", "F") == "Squin", "чистое имя как есть")
TOWNNAME = "Hub (defunct) 7"; reset_state(); setevents({ ev{ type = "raid", day = 41, attacker = "H", defender = "F" } }); at(41.2); tick()
check(MSGS[1] and MSGS[1].msg:find("^Day 41, Hub: "), "журнал: чистое имя города: " .. tostring(MSGS[1] and MSGS[1].msg))
TOWNNAME = "\230\173\166\229\163\171"; reset_state(); setevents({ ev{ type = "raid", day = 42, attacker = "H2", defender = "F" } }); at(42.2); tick()
check(MSGS[1] and MSGS[1].msg:find("^Day 42: "), "журнал: грязный город без имени: " .. tostring(MSGS[1] and MSGS[1].msg))
TOWNNAME = "TownA"

-- 6. шум: loot_carried одной пары за сутки — один слух (остальные слиты), потолок в сутки; deed — потолок 2
reset_state()
local list = {}
for i = 1, 5 do list[#list + 1] = { type = "loot_carried", day = 50 + i * 0.01, attacker = "Mongrel", defender = "Fogmen", text = "A band of Mongrel hauls plunder from a fight and heads for a market." } end
list[#list + 1] = { type = "loot_carried", day = 50.0, attacker = "Shinobi", defender = "Fogmen", text = "A band of Shinobi hauls plunder." }
for i = 1, 4 do list[#list + 1] = { type = "deed", kind = "killed", day = 50.1, attacker = "D" .. i, defender = "V", text = "D" .. i .. " killed people of V." } end
setevents(list)
at(51.3); for _ = 1, 8 do tick() end   -- без координат: общая задержка NEWS_NOCOORD_DAYS
local nl, nd, merged = 0, 0, false
for _, s in ipairs(SAID) do
  if s.text:find("plunder", 1, true) or s.text:find("loot", 1, true) then nl = nl + 1; if s.text:find("not for the first time", 1, true) then merged = true end end
  if s.text:find("killed people", 1, true) then nd = nd + 1 end
end
check(nl == 1, "loot_carried: один слух в сутки: " .. nl)
check(merged, "слитый слух с хвостом про повтор")
check(nd == 2, "deed: потолок 2 в сутки: " .. nd)
check(logtext():find("merge kind=loot_carried n=5", 1, true), "маркер merge kind=loot_carried n=5")
local idx = R.fn.told(); local nm = 0; for _, v in pairs(idx) do if v == "merged" then nm = nm + 1 end end
check(nm == 4, "4 слитых помечены рассказанными: " .. nm)

-- 7. метрика видимости
local v = R.visibility()
check(v.events == 10 and v.shown == #SAID and v.merged == 4, string.format("visibility events=%d shown=%d merged=%d", v.events, v.shown, v.merged))
check(v.by.loot_carried.t == 6 and v.by.loot_carried.s == 5 and v.by.deed.t == 4 and v.by.deed.s == 2, "по типам")
R.fn.vislog(true)
local line; for l in logtext():gmatch("VISIBILITY day=%d+ events=10 [^\n]*") do line = l end   -- последняя строка
check(line and line:find("shown=" .. #SAID, 1, true) and line:find("merged=4", 1, true) and line:find("pct=", 1, true), "строка VISIBILITY: " .. tostring(line))
local tl = line and line:match("types=(%S+)") or ""
local got = {}; for ty, s, t in tl:gmatch("([%w_]+):(%d+)/(%d+)") do got[ty] = s .. "/" .. t end
check(got.loot_carried == "5/6" and got.deed == "2/4", "types в строке: " .. tl)
local gd = { sdata = {} }; FIRE("PlayerInterface::serialise", nil, gd)
local nvis = 0; for _ in logtext():gmatch("VISIBILITY day=") do nvis = nvis + 1 end
check(nvis >= 2, "VISIBILITY на сохранении")

-- 8. мелочь города (V4): новостей нет — после задержки житель говорит о местном; раз за визит
reset_state(); setevents({})
TOWNNAME = "QuietTown"
at(60); tick()
check(#SAID == 0, "сразу после входа молчит")
CLOCK = CLOCK + R.CFG.ENTRY_DELAY_SEC; tick()
check(#SAID == 1 and logtext():find("smalltalk town=QuietTown kind=", 1, true), "мелочь при входе: " .. text(1))
tick(); tick()
check(#SAID == 1, "раз за визит")
check(#MSGS == 0, "мелочь в журнал не пишется")
-- с моделью: полка еды пустая -> «дорого»
rawset(_G, "KMM_Stock", { level = function(sid, cat) if cat == "food" then return 0.1 end return 1.0 end })
TOWNNAME = "HungryTown"; R.smallLast = nil
at(61); tick(); CLOCK = CLOCK + R.CFG.ENTRY_DELAY_SEC
local opts = R.fn.small(A.sid, A.x, A.z)
local hasLow = false; for _, o in ipairs(opts) do if o[1] == "stock_low" and o[2]:find("food", 1, true) then hasLow = true end end
check(hasLow, "варианты: дефицит еды")
-- разыскиваемый рядом
rawset(_G, "KMM_Outlaws", { wanted = function() return { { i = 1, n = "Grim Jaw", st = "a", x = A.x + 3000, z = A.z, b = 700 }, { i = 2, n = "Far One", st = "a", x = A.x + 900000, z = A.z, b = 100 } } end })
opts = R.fn.small(A.sid, A.x, A.z)
local ol; for _, o in ipairs(opts) do if o[1] == "outlaw" then ol = o[2] end end
check(ol and ol:find("Grim Jaw", 1, true) and ol:find("700", 1, true) and not ol:find("Far One", 1, true), "разыскиваемый рядом: " .. tostring(ol))
rawset(_G, "KMM_Outlaws", { wanted = function() return { { i = 3, n = "\230\173\166\229\163\171", st = "a", x = A.x, z = A.z, b = 1 } } end })
opts = R.fn.small(A.sid, A.x, A.z)
local cjk = false; for _, o in ipairs(opts) do if o[1] == "outlaw" then cjk = true end end
check(not cjk, "грязное имя разыскиваемого не выводится")
tick()
check(#SAID == 2, "в новом городе мелочь сказана: " .. #SAID)
-- в визите был слух — мелочи нет
reset_state(); TOWNNAME = "NewsTown"; setevents({ ev{ type = "raid", day = 70, attacker = "Z", defender = "F" } }); at(70.2); tick()
CLOCK = CLOCK + R.CFG.ENTRY_DELAY_SEC; tick(); tick()
check(#SAID == 1 and not logtext():find("smalltalk town=NewsTown", 1, true), "был слух — мелочь не нужна")
-- ошибка модели не роняет модуль
rawset(_G, "KMM_Stock", { level = function() error("stock boom") end })
reset_state(); TOWNNAME = "BrokenTown"; setevents({}); tick(); CLOCK = CLOCK + R.CFG.ENTRY_DELAY_SEC; tick()
check(not R.disabled and #SAID == 1, "сломанный Stock: мелочь всё равно, модуль жив")
rawset(_G, "KMM_Stock", nil); rawset(_G, "KMM_Outlaws", nil)

-- 8b. приветствие Nemesis: уже сказал — мелочи нет; ещё ждёт — мелочь ждёт; сломанная функция — как без неё
GS, GP = true, false
rawset(_G, "KMM_Nemesis", { greet_said = function(sid) GSID = sid; return GS, GP end })
reset_state(); TOWNNAME = "GreetTown"; setevents({}); at(90); tick(); CLOCK = CLOCK + R.CFG.ENTRY_DELAY_SEC; tick(); tick()
check(#SAID == 0 and GSID == A.sid and logtext():find("smalltalk skip town=GreetTown reason=greet_said", 1, true), "greet сказал — мелочи нет")
GS, GP = false, true
reset_state(); TOWNNAME = "PendTown"; at(91); tick(); CLOCK = CLOCK + R.CFG.ENTRY_DELAY_SEC; tick(); tick()
check(#SAID == 0, "greet ещё может прозвучать — ждём")
GP = false; tick()
check(#SAID == 1 and logtext():find("smalltalk town=PendTown", 1, true), "greet промолчал — мелочь сказана")
rawset(_G, "KMM_Nemesis", { greet_said = function() error("nemesis boom") end })
reset_state(); TOWNNAME = "ErrTown"; at(92); tick(); CLOCK = CLOCK + R.CFG.ENTRY_DELAY_SEC; tick()
check(#SAID == 1 and not R.disabled, "ошибка greet_said — как раньше")
rawset(_G, "KMM_Nemesis", nil)

-- 8c. соперник: nemesis_contempt / nemesis_beat_again — свои тексты, не чаще слуха в сутки на вид
reset_state(); TOWNNAME = "TownA"
setevents({ ev{ type = "nemesis_contempt", day = 95, leader_name = "Tamu Grin", attacker = "Dust Bandits", defender = "Law", text = "Tamu Grin found the Nameless with empty pockets." },
            ev{ type = "nemesis_beat_again", day = 95, leader_name = "Tamu Grin", attacker = "Dust Bandits", defender = "Law", won = 2, text = "Tamu Grin beat the Nameless again." },
            ev{ type = "nemesis_beat_again", day = 95.1, leader_name = "Boda Widow", attacker = "Sand Ninjas", defender = "Law", won = 3, text = "Boda Widow beat the Nameless again." } })
at(95.3); for _ = 1, 5 do tick() end
local ti = R.fn.told()   -- по id: 1 — contempt, 2 и 3 — beat_again (формы разные, смотрим, что сказано)
local nc = (ti["1"] == "say") and 1 or 0
local nb = ((ti["2"] == "say") and 1 or 0) + ((ti["3"] == "say") and 1 or 0)
check(nc == 1 and nb == 1, string.format("contempt=%d beat_again=%d (потолок 1 в сутки)", nc, nb))
local named = false; for _, s in ipairs(SAID) do if s.text:find("Tamu Grin", 1, true) or s.text:find("Boda Widow", 1, true) then named = true end end
check(named and anyCJK() == nil, "имя соперника в слухе")
check(R.fn.tellable({ type = "nemesis_contempt" }) and R.fn.tellable({ type = "nemesis_beat_again" }), "типы с шаблоном")

-- 9. старый сейв ("id|town") читается: событие считается рассказанным везде
reset_state()
gd = { sdata = { kmm_rumors_told = "1|SomeOtherTown" } }
FIRE("PlayerInterface::loadFromSerialise", nil, gd)
TOWNNAME = "TownA"; setevents({ ev{ type = "raid", day = 80, attacker = "Saved", defender = "F" }, ev{ type = "raid", day = 80, attacker = "Fresh", defender = "F" } })
at(80.2); tick()
check(#SAID == 1 and text(1):find("Fresh", 1, true), "старый ключ id|town — глобально рассказано: " .. text(1))

-- 9b. чистка памяти рассказанного: исчезнувшие из журнала, старше TOLD_KEEP_DAYS, сверх TOLD_MAX; старый формат цел
reset_state(); TOWNNAME = "TownA"
setevents({ ev{ type = "raid", day = 100, attacker = "K1", defender = "F" }, ev{ type = "raid", day = 300, attacker = "K2", defender = "F" },
            ev{ type = "raid", day = 300, attacker = "K3", defender = "F" }, ev{ type = "raid", day = 300, attacker = "K4", defender = "F" } })
at(300.2); tick()   -- журнал дирижёра прочитан
R.told = { ["1|OldTown"] = true, ["2|TownA"] = true, ["3|=TownA"] = true, ["99|Gone"] = true }
R.heard = { ["4"] = true, ["98"] = true }
local nrm = R.prune(300.2)
check(not R.told["99|Gone"] and not R.heard["98"], "событий нет в журнале — удалены")
check(not R.told["1|OldTown"], "старше TOLD_KEEP_DAYS — удалено")
check(R.told["2|TownA"] and R.told["3|=TownA"] and R.heard["4"], "живые записи (и слитые, и heard) целы")
check(nrm == 3 and logtext():find("told prune: removed=3 gone=2 old=1 cap=0", 1, true), "маркер told prune: " .. tostring(nrm))
R.CFG.TOLD_MAX = 2
R.prune(300.2)
local nk = 0; for _ in pairs(R.told) do nk = nk + 1 end; for _ in pairs(R.heard) do nk = nk + 1 end
check(nk == 2 and not R.told["2|TownA"] and R.heard["4"], "потолок: остаются самые новые id")
R.CFG.TOLD_MAX = 3000
-- на сохранении — тоже; источник не дирижёр — не трогаем
R.told = { ["2|TownA"] = true, ["77|Gone"] = true }; R.heard = {}
local gd2 = { sdata = {} }; FIRE("PlayerInterface::serialise", nil, gd2)
check(gd2.sdata.kmm_rumors_told == "2|TownA", "в сейв — только нужное: " .. tostring(gd2.sdata.kmm_rumors_told))
local src = R.src; R.src = "file"; R.told = { ["77|Gone"] = true }
check(R.prune(300.2) == 0 and R.told["77|Gone"], "источник-файл: чистки нет")
R.src = src

-- 9c. хроника Nemesis уже записала событие — журнал слухов его не дублирует
reset_state(); TOWNNAME = "TownA"
rawset(_G, "KMM_Nemesis", { chronicled = function(id) ASKED = id; return id == 1 end })
setevents({ ev{ type = "raid", day = 310, attacker = "C1", defender = "F" }, ev{ type = "raid", day = 310, attacker = "C2", defender = "F" } })
at(310.2); tick(); tick()
check(#SAID == 2 and #MSGS == 1 and not MSGS[1].msg:find("C1", 1, true) and logtext():find("journal skip event=1 reason=chronicled", 1, true),
      "chronicled -> без дубля: msgs=" .. #MSGS)
check(R.journaled("2") and not R.journaled("1"), "KMM_Rumors.journaled")
rawset(_G, "KMM_Nemesis", { chronicled = function() error("nemesis boom") end })
reset_state(); setevents({ ev{ type = "raid", day = 311, attacker = "C3", defender = "F" } }); at(311.2); tick()
check(#MSGS == 1 and not R.journalOff, "ошибка chronicled — как раньше")
rawset(_G, "KMM_Nemesis", nil)

-- 9d. обороты сюжета: у всех story_* есть тексты; story_quiet без номера оборота; новый оборот (новый id) звучит снова
for _, ty in ipairs({ "story_scramble", "story_famine", "story_twilight", "story_night", "story_forge", "story_ashes", "story_quiet" }) do
  local s0 = R.fn.tellable({ type = ty }) and R.fn.compose({ type = ty, leader = "", town = "", att = "", def = "", text = "" }, 0, nil, nil)
  check(type(s0) == "string" and #s0 > 10 and not s0:find("%d"), "story текст: " .. ty .. " -> " .. tostring(s0))
end
reset_state(); TOWNNAME = "TownA"
setevents({ { type = "story_quiet", day = 320, cycle = 3, text = "" }, { type = "story_ashes", day = 320, cycle = 3, text = "" } })
at(321.5); tick(); tick()
check(#SAID == 2 and not text(1):find("3", 1, true) and not text(2):find("3", 1, true), "story_quiet/ashes сказаны, без номера оборота: " .. text(1) .. " | " .. text(2))
setevents({ { type = "story_quiet", day = 320, cycle = 3, text = "" }, { type = "story_ashes", day = 320, cycle = 3, text = "" },
            { type = "story_quiet", day = 330, cycle = 4, text = "" } })
at(331.5); R.townLastHour = {}; tick()
check(#SAID == 3 and #text(3) > 10 and not text(3):find("%d"), "новый оборот — тишина снова: " .. text(3))

-- 10. переопределение чисел из правил дирижёра
R.cfgApplied = nil
local P = C.cfg().params; local save = P.rumors
P.rumors = { MAX_PER_TOWN = 5, NOISY = { deed = { cap = 4, weight = 0.5 } }, BOGUS = 1 }
CLOCK = CLOCK + 100; R.lastCheck = -1e9; FIRE("GameWorld::charsUpdate", {})
check(R.CFG.MAX_PER_TOWN == 5 and R.CFG.NOISY.deed.cap == 4 and R.CFG.NOISY.loot_carried and R.CFG.BOGUS == nil, "params.rumors переопределяет CFG")
P.rumors = save

io.write(string.format("checks=%d fails=%d\n", N, #FAILS))
for _, f in ipairs(FAILS) do io.write("FAIL: " .. f .. "\n") end
FAILED = #FAILS
''', "test")
run("if FAILED ~= 0 then error('visibility test failed') end", "result")
print("OK")
