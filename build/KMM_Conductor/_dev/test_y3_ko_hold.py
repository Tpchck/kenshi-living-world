"""Офлайн-тест Y3 (пакет 7): окно побеждённого в KMM_Self — override MedicalSystem::canGetUpWakeUp на заглушках.
Кто победил — только Character.lastGuyWhoDefeatedMe (hand -> getCharacter); держим побеждённых игроком и в бою соперников Nemesis;
победитель жив и рядом, побеждённого видели стоящим в этом бою (свежесть); ключи — hand:toString(), не tostring(hand);
предел ko_hold_s (30) в реальных секундах при скорости 1× (игровые часы × getLengthOfHourInRealSeconds), первый скан не отпускает;
запасной предел реального времени в самом override;
обработчик есть только пока кого-то держим; ошибка -> все отпущены, обработчик снят, окно выключено. Сдавшиеся B3 не продлеваются.
python -I -X utf8 build/KMM_Conductor/_dev/test_y3_ko_hold.py -> ALL OK / FAIL, код 1 при провале."""
import ctypes
import re
import sys
import tempfile

DLL = r"C:\Program Files (x86)\Steam\steamapps\workshop\content\233860\3817000612\lua51.dll"
SELF = r"C:\KenshiModMap\build\KMM_Conductor\scripts\init\KMM_Self.lua"
FAILS = []


def check(c, m):
    print(("OK   " if c else "FAIL ") + m)
    if not c:
        FAILS.append(m)


def make_state():
    L = ctypes.CDLL(DLL)
    L.luaL_newstate.restype = ctypes.c_void_p
    for fn, at in [("luaL_openlibs", [ctypes.c_void_p]), ("luaL_loadstring", [ctypes.c_void_p, ctypes.c_char_p]),
                   ("lua_pcall", [ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int]),
                   ("lua_settop", [ctypes.c_void_p, ctypes.c_int]),
                   ("lua_getfield", [ctypes.c_void_p, ctypes.c_int, ctypes.c_char_p])]:
        getattr(L, fn).argtypes = at
    L.lua_tolstring.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p]
    L.lua_tolstring.restype = ctypes.c_char_p
    st = L.luaL_newstate()
    L.luaL_openlibs(st)

    def run(code, name="chunk"):
        if L.luaL_loadstring(st, code.encode("utf-8")) or L.lua_pcall(st, 0, 0, 0):
            msg = L.lua_tolstring(st, -1, None)
            raise RuntimeError(f"{name}: {msg.decode('utf-8', 'replace') if msg else '?'}")

    def get(var):
        run("__V = tostring(%s)" % var, "get")
        L.lua_getfield(st, -10002, b"__V")
        v = L.lua_tolstring(st, -1, None)
        L.lua_settop(st, -2)
        return v.decode("utf-8", "replace") if v else None
    return run, get


STUBS = r'''
CLOCK = 100; os.clock = function() return CLOCK end
GH = 1000; SPEED = 1; NOTIME = false; CAPI = 0; DOWNAPI = {}; LH = 150; NOLH = false; TSN = 0
EVS = {}; RUNAWAY = {}; KO = {}
local plats = {}
function PLAT(key)
  local p = plats[key]
  if p then return p end
  p = { key = key }
  function p:getPlatoonStringID() return key end
  function p:getBlackboard() return { runAway = function() RUNAWAY[key] = (RUNAWAY[key] or 0) + 1 end } end
  function p:getSquadLeader() return p.leader end
  plats[key] = p
  return p
end
local function fac(name) return { getData = function() return { stringID = name, name = name } end } end
GONE = {}
function HAND(nm, c)
  -- tostring(hand) как у sol2: адрес новой копии (разный при каждом getHandle); стабильный ключ — hand:toString()
  return setmetatable({ nm = nm }, { __tostring = function() TSN = TSN + 1; return "userdata: 0x" .. TSN end,
    __index = { getCharacter = function() CAPI = CAPI + 1; if GONE[nm] then return nil end; return c end,
                toString = function() CAPI = CAPI + 1; return "h_" .. nm end } })
end
BY = {}
-- opt: down, combat, fac, leader, by (персонаж-победитель), dead, animal
function MK(nm, key, opt)
  opt = opt or {}
  local c = { O = opt, nm = nm }
  local pl = PLAT(key)
  function c:getPosition() return { x = opt.x or 100, y = 0, z = opt.z or 100 } end
  function c:isDead() return opt.dead or false end
  function c:isDown() CAPI = CAPI + 1; DOWNAPI[key] = (DOWNAPI[key] or 0) + 1; return opt.down or false end
  function c:isUnconcious() CAPI = CAPI + 1; DOWNAPI[key] = (DOWNAPI[key] or 0) + 1; return false end
  function c:isUnique() return false end
  function c:isPlayerCharacter() return opt.player or false end
  function c:isInCombatMode() if opt.combat ~= nil then return opt.combat end; return not opt.down end
  function c:getHandle() CAPI = CAPI + 1; return HAND(nm, c) end
  function c:getName() return nm end
  function c:getFaction() return fac(opt.fac or "Bandits") end
  function c:getPlatoon() return { me = pl } end
  function c:isAnimal() if opt.animal then return { animal = true } end return nil end
  function c:getRace() return { robot = false, data = { name = "Greenlander" } } end
  function c:getMedical() return { knockoutForceTimer = function(_, sec) KO[#KO + 1] = nm .. ":" .. tostring(sec); opt.down = true end } end
  function c:getInventory() return { getAllItems = function() return {} end } end
  if opt.by then c.lastGuyWhoDefeatedMe = HAND(opt.by.nm, opt.by) end
  if opt.leader then pl.leader = c end
  BY[nm] = c
  return c
end
-- MedicalSystem: поле me (обращение = вызов движка)
function MED(c, broken)
  return setmetatable({}, { __index = function(_, k) CAPI = CAPI + 1; if broken then error("me broken") end; if k == "me" then return c end end })
end
CHARS = {}
PC = MK("Hero", "player_squad", { player = true, fac = "player", x = 0, z = 0 })
OTHER_PC = PC
function getPlayerInterface() return { getAllPlayerCharacters = function() return { PC } end } end
function getGameWorld() return { getTimeStamp = function() return CLOCK end,
  getTimeStamp_inGameHours = function() if NOTIME then error("no time") end; return { getTotalHours = function() return GH end } end,
  getLengthOfHourInRealSeconds = function() if NOLH then error("unbound") end; return LH end,
  getCharacterUpdateList = function() local t = {}; for _, c in ipairs(CHARS) do t[c] = true end; return t end } end
HID, HANDLERS, ONS, OFFS = 0, {}, 0, 0
Events = {
  on = function(name, fn) HID = HID + 1; HANDLERS[HID] = { name = name, fn = fn }; if name == "MedicalSystem::canGetUpWakeUp" then ONS = ONS + 1 end; return HID end,
  off = function(id) if HANDLERS[id] then HANDLERS[id] = nil; OFFS = OFFS + 1 end end }
function OVR(med, dv)   -- как ядро: все обработчики override по очереди, первый не-nil
  for _, h in pairs(HANDLERS) do
    if h.name == "MedicalSystem::canGetUpWakeUp" then local v = h.fn(med, dv); if v ~= nil then return v end end
  end
  return nil
end
function NHOOK() local n = 0; for _, h in pairs(HANDLERS) do if h.name == "MedicalSystem::canGetUpWakeUp" then n = n + 1 end end; return n end
PARAMS = { enabled = true, scan_seconds = 3, cooldown_seconds = 60, faction_avoid = false, surrender_factions_ftype = {} }
STATE = {}
RIVALS = {}
KMM_Nemesis = { rivals = function() return RIVALS end }
KMM_Conductor = {
  cfg = function() return { params = { self = PARAMS, guard = { debug_log = "TMPDIR/debug.log" } }, factions = { Bandits = { ftype = 8 } }, player_faction = "player" } end,
  read_json = function() return { item_tiers = {} } end,
  emit = function(ev) EVS[#EVS + 1] = ev end,
  state = function() return STATE end,
}
function TICK(sec) sec = sec or 3; CLOCK = CLOCK + sec; GH = GH + sec * SPEED / LH; KMM_Self._tick() end   -- игровой час = LH реальных с при 1×
-- разогрев: лежащие по сценарию сначала стоят в бою (метка свежести KO.up), потом ложатся
function WARM() local d = {}; for _, c in ipairs(CHARS) do if c.O.down then d[#d + 1] = c; c.O.down = false end end; TICK(); for _, c in ipairs(d) do c.O.down = true end end
function KOS() return KMM_Self.ko() end
function HELD(nm) return KOS().hold["h_" .. nm] ~= nil end
function DIS() local d = {}; for k in pairs(KMM_Self.disabled()) do d[#d + 1] = k end; table.sort(d); return table.concat(d, ",") end
'''


def scenario(setup, params="", warm=True):
    tmp = tempfile.mkdtemp(prefix="kmm_y3_").replace("\\", "/")
    run, get = make_state()
    run(STUBS.replace("TMPDIR", tmp), "stubs")
    run(open(SELF, encoding="utf-8").read(), "Self")
    run(params, "params")
    run(setup, "setup")
    run("WARM(); TICK()" if warm else "TICK()", "tick")
    return run, get, tmp


def log_of(tmp):
    try:
        return open(tmp + "/debug.log", encoding="utf-8").read()
    except OSError:
        return ""


# 1. Игрок уложил бандита: окно открыто, override держит только его и только когда ядро разрешает встать; горячий путь дешёвый.
run, get, tmp = scenario('''CHARS = { MK("b1", "bs"), MK("b2", "bs", { down = true, by = PC }) }''')
check(get("KOS().n") == "1" and get('HELD("b2")') == "true", "побеждённый игроком взят в окно (n=%s)" % get("KOS().n"))
check(get("ONS") == "1" and get("NHOOK()") == "1", "override зарегистрирован один раз (on=%s)" % get("ONS"))
check(get('OVR(MED(BY.b2), true)') == "false", "держим: ядро говорит «встать» -> false")
check(get('OVR(MED(BY.b2), false)') == "nil", "ядро и так держит -> nil (ваниль)")
check(get('OVR(MED(BY.b1), true)') == "nil", "чужой персонаж -> ванильный ответ")
run("CAPI = 0; OVR(MED(BY.b1), false); C0 = CAPI; CAPI = 0; OVR(MED(BY.b2), true); C1 = CAPI")
check(get("C0") == "0", "горячий путь при defaultVal=false: 0 вызовов движка (%s)" % get("C0"))
check(int(get("C1")) <= 3, "горячий путь удержания: ≤3 вызова (me, getHandle, хендл->строка) (%s)" % get("C1"))
check("KO hold: b2 (Bandits) by Hero why=player" in log_of(tmp), "маркер «KO hold:» в debug.log")
check(get("DIS()") in ("", None), "ничего не отключено (%s)" % get("DIS()"))

# 2. Таймаут в реальных секундах при 1× (игровые часы × длина часа): первый скан не отпускает; окно 22.5..30 с; при ускорении — то же
#    в пересчёте на 1× (реальных секунд меньше); потом отпуск, обработчик снят, повторно не берём.
for speed in (1, 3, 5):
    run, get, tmp = scenario('''SPEED = %d; CHARS = { MK("b1", "bs"), MK("b2", "bs", { down = true, by = PC }) }''' % speed)
    run("TICK()")
    check(get('HELD("b2")') == "true", "скорость %d: первый скан после взятия не отпускает (H1)" % speed)
    run("G0 = GH; C0 = CLOCK - 3; for i = 1, 40 do if not HELD('b2') then break end; TICK() end; HELDS = (GH - G0) * LH + 3 * SPEED; REAL = CLOCK - C0")
    held, real = float(get("HELDS")), float(get("REAL"))
    check(get('HELD("b2")') == "false" and 22 <= held <= 30.5, "скорость %d: отпущен по таймауту, держали %.1f с при 1× (22..30), реальных %.0f" % (speed, held, real))
    m = re.search(r"KO release: b2 why=timeout held=(\d+)s", log_of(tmp))
    check(bool(m) and 20 <= int(m.group(1)) <= 30, "скорость %d: маркер «KO release: ... why=timeout» (%s)" % (speed, m and m.group(0)))
    check("game hour = 150.0 real s" in log_of(tmp), "скорость %d: длина часа из ядра в debug.log" % speed)
    run("TICK(); TICK()")
    check(get("NHOOK()") == "1" and get("OFFS") == "0", "скорость %d: override с загрузки остаётся, когда держать некого (off=%s)" % (speed, get("OFFS")))   # 2026-11-15: регистрация при загрузке
    check(get('HELD("b2")') == "false" and get("ONS") == "1", "скорость %d: тот же персонаж не берётся снова" % speed)
    check(get('OVR(MED(BY.b2), true)') == "nil", "скорость %d: после отпуска — ваниль" % speed)

# 2b. Длины часа нет -> окно по реальным часам (os.clock), те же 22..30 с.
run, get, tmp = scenario('''NOLH = true; SPEED = 3; CHARS = { MK("b1", "bs"), MK("b2", "bs", { down = true, by = PC }) }''')
run("C0 = CLOCK; for i = 1, 40 do if not HELD('b2') then break end; TICK() end; REAL = CLOCK - C0")
real = float(get("REAL"))
check("window on real clock" in log_of(tmp) and 22 <= real <= 33, "без длины часа: окно по os.clock, %.0f реальных с" % real)

# 2c. Свежесть (M2): побеждённого не видели стоящим в бою / победитель мёртв / победитель далеко -> не держим.
run, get, tmp = scenario('''CHARS = { MK("b1", "bs"), MK("b2", "bs", { down = true, by = PC }) }''', warm=False)
check(get("KOS().n") == "0" and get("ONS") == "1", "лёг до боя (старый победитель в поле ядра): не держим")
run, get, tmp = scenario('''local dead = MK("Hero2", "player_squad", { player = true, fac = "player", dead = true })
CHARS = { MK("b1", "bs"), MK("b2", "bs", { down = true, by = dead }) }''')
check(get("KOS().n") == "0", "победитель мёртв: не держим")
run, get, tmp = scenario('''local far = MK("Hero3", "player_squad", { player = true, fac = "player", x = 9000, z = 9000 })
CHARS = { MK("b1", "bs"), MK("b2", "bs", { down = true, by = far }) }''')
check(get("KOS().n") == "0", "победитель далеко от побеждённого: не держим")
check(get("TSN") == "0", "tostring(hand) не используется как ключ (%s)" % get("TSN"))

# 3. Победитель не игрок и не соперник / победителя нет -> окно не открывается, обработчик не регистрируется.
run, get, tmp = scenario('''local npc = MK("thug", "other", { fac = "Guards" })
CHARS = { MK("b1", "bs"), MK("b2", "bs", { down = true, by = npc }), MK("b3", "bs", { down = true }) }''')
check(get("KOS().n") == "0" and get("ONS") == "1", "чужая победа / без победителя: не держим, override не ставится")

# 4. Бой соперников при игроке: победитель или побеждённый — из отряда соперника Nemesis (o.pk).
run, get, tmp = scenario('''RIVALS = { { pk = "rsq", n = "Gor" } }
local gor = MK("Gor", "rsq")
CHARS = { gor, MK("t1", "town", { fac = "Guards" }), MK("t2", "town", { fac = "Guards", down = true, by = gor }),
          MK("r2", "rsq", { down = true, by = BY.t1 or MK("t9", "town2", { fac = "Guards" }) }) }''')
check(get('HELD("t2")') == "true" and get('HELD("r2")') == "true", "соперник победил / соперник побеждён — оба в окне")
lg = log_of(tmp)
check("why=rival_win" in lg and "why=rival_down" in lg, "причины rival_win и rival_down в логе")

# 5. Отпуск: связан (isChained), добит, встал сам, игрок ушёл, пропал из мира.
for why, act in (("tied", "BY.b2.isChained = true"), ("dead", "BY.b2.O.dead = true"), ("up", "BY.b2.O.down = false"),
                 ("left", "PC.O.x = 90000"), ("gone", "GONE.b2 = true")):
    run, get, tmp = scenario('''CHARS = { MK("b1", "bs"), MK("b2", "bs", { down = true, by = PC }) }''')
    run(act + "; TICK()")
    check(get('HELD("b2")') == "false" and ("KO release: b2 why=" + why) in log_of(tmp), "отпуск why=%s" % why)

# 6. Ошибка в override: ванильный ответ, все отпущены, окно выключено, обработчик снят в следующем такте, скан жив.
run, get, tmp = scenario('''CHARS = { MK("b1", "bs"), MK("b2", "bs", { down = true, by = PC }) }''')
check(get('OVR(MED(BY.b2, true), true)') == "nil", "сломанный MedicalSystem: override вернул nil (ваниль)")
check(get("KOS().off") == "true" and get("KOS().n") == "0" and "ko_override" in get("DIS()"), "окно выключено, удерживаемые отпущены (%s)" % get("DIS()"))
run("TICK()")
check(get("NHOOK()") == "0", "override снят в такте")
check("scan" not in get("DIS()"), "скан Self не отключён")
lg = log_of(tmp)
check("KO hold disabled until restart" in lg and "why=off" in lg, "причина и отпуск в debug.log")
run('CHARS[#CHARS + 1] = MK("b3", "bs", { down = true, by = PC }); TICK()')
check(get("KOS().n") == "0" and get("ONS") == "1", "после выключения новых удержаний нет")

# 7. Нет игрового времени -> окна нет (без таймаута в игровых секундах не держим).
run, get, tmp = scenario('''NOTIME = true; CHARS = { MK("b1", "bs"), MK("b2", "bs", { down = true, by = PC }) }''')
check(get("KOS().n") == "0" and get("ONS") == "1" and "no game time" in log_of(tmp), "без игрового времени окно не открывается")

# 8. Потолок ko_hold_max (по умолчанию 6).
run, get, tmp = scenario('''CHARS = { MK("s0", "big") }
for i = 1, 10 do CHARS[#CHARS + 1] = MK("d" .. i, "big", { down = true, by = PC }) end''')
check(get("KOS().n") == "6", "не больше 6 разом (n=%s)" % get("KOS().n"))

# 9. B3: сдавшиеся через knockoutForceTimer окно побеждённого не получают (даже с победителем-игроком в поле ядра).
run, get, tmp = scenario('''CHARS = { MK("b1", "b", { down = true, leader = true, by = PC }), MK("b2", "b", { down = true, by = PC }),
  MK("b3", "b", { down = true, by = PC }), MK("b4", "b", { down = true, by = PC }), MK("b5", "b", { by = PC }) }''',
                         'PARAMS.surrender_mode = "knockout"; PARAMS.surrender_factions_ftype = { 8 }')
check(get("table.concat(KO, ',')") == "b5:25", "B3: сдача-нокаут как раньше (%s)" % get("table.concat(KO, ',')"))
run("TICK()")
check(get('HELD("b5")') == "false", "сдавшийся b5 не продлён окном Y3")
check(get('HELD("b2")') == "true", "побеждённые игроком из того же отряда — в окне")

# 10. Запасной предел реального времени: скан встал — override сам перестаёт держать.
run, get, tmp = scenario('''CHARS = { MK("b1", "bs"), MK("b2", "bs", { down = true, by = PC }) }''')
run("CLOCK = CLOCK + 100")
check(get('OVR(MED(BY.b2), true)') == "nil", "после ko_hard_real_s override отдаёт ваниль без скана")

# 11. Смена мира (другой сейв): все отпущены.
run, get, tmp = scenario('''CHARS = { MK("b1", "bs"), MK("b2", "bs", { down = true, by = PC }) }''')
run("STATE = {}; TICK()")
check("KO release: b2 why=world" in log_of(tmp), "смена мира: прежние удержания отпущены why=world")

# 12. Свой (фракция игрока) не держится; посторонний отряд без боя не опрашивается (0 вызовов isDown).
run, get, tmp = scenario('''RIVALS = { { pk = "rsq" } }; local gor = MK("Gor", "rsq")
CHARS = { gor, MK("p2", "player_squad", { fac = "player", down = true, by = gor }),
          MK("v1", "village", { fac = "Villagers", combat = false }), MK("v2", "village", { fac = "Villagers", down = true, combat = false, by = PC }) }''')
check(get('HELD("p2")') == "false", "персонаж фракции игрока не держится")
check(get('HELD("v2")') == "false" and get("DOWNAPI.village") == "nil", "отряд без боя: не кандидат, isDown не зовётся (%s)" % get("DOWNAPI.village"))

# 13. Весь отряд лёг: окно держится по метке боя (ko_fight_window_s), позже — уже не кандидаты.
run, get, tmp = scenario('''CHARS = { MK("w1", "ws"), MK("w2", "ws") }''')
run("BY.w1.O.down = true; BY.w1.lastGuyWhoDefeatedMe = HAND('Hero', PC); BY.w2.O.down = true; TICK()")
check(get('HELD("w1")') == "true", "отряд лёг целиком — побеждённый в окне по недавней метке боя")
run("for i = 1, 15 do TICK() end; BY.w2.lastGuyWhoDefeatedMe = HAND('Hero', PC); TICK()")
check(get('HELD("w2")') == "false", "после окна боя отряд больше не кандидат")

# 14. ko_hold = false: ничего не регистрируется.
run, get, tmp = scenario('''CHARS = { MK("b1", "bs"), MK("b2", "bs", { down = true, by = PC }) }''', "PARAMS.ko_hold = false")
check(get("KOS().n") == "0" and get("ONS") == "1", "ko_hold=false: окно выключено")

# 15. Скан Self отключился с удерживаемыми: такт выключает окно и снимает override.
run, get, tmp = scenario('''CHARS = { MK("b1", "bs"), MK("b2", "bs", { down = true, by = PC }) }''')
run("KMM_Self.disabled().scan = true; TICK()")
check(get("KOS().off") == "true" and get("NHOOK()") == "0" and get("KOS().n") == "0", "скан выключен -> окно выключено, override снят")

# 16. S1: одно удержание на персонажа за бой — даже если запись seen пропала (прочистка/сбой), повтор не раньше ko_once_s (120 с);
#     в строке «KO hold:» хвост ключа (одноимённые различимы); одна строка на удержание.
run, get, tmp = scenario('''CHARS = { MK("b1", "bs"), MK("b2", "bs", { down = true, by = PC }) }''')
check("key=h_b2" in log_of(tmp), "в строке KO hold есть key=<ключ hand:toString()>")
run("for i = 1, 40 do if not HELD('b2') then break end; TICK() end; KOS().seen = {}; KOS().up['h_b2'] = CLOCK; TICK(); KOS().up['h_b2'] = CLOCK; TICK()")
check(get('HELD("b2")') == "false", "S1: после отпуска тот же персонаж не взят снова в пределах 120 с (seen очищен)")
check(log_of(tmp).count("KO hold: b2 ") == 1, "S1: одна строка KO hold на персонажа за бой (%d)" % log_of(tmp).count("KO hold: b2 "))
run("CLOCK = CLOCK + 130; KOS().seen = {}; BY.b2.O.down = false; TICK(); BY.b2.O.down = true; TICK()")
check(get('HELD("b2")') == "true" and log_of(tmp).count("KO hold: b2 ") == 2, "S1: новый бой после 120 с — новое удержание")

print("\nFAIL: %d" % len(FAILS) if FAILS else "\nALL OK")
sys.exit(1 if FAILS else 0)
