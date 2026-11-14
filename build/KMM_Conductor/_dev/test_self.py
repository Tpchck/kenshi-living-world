"""Офлайн-тест KMM_Self (P2: B6 + B3) на заглушках, без дирижёра.
B6: бой и «бесстрашие» оценивают гуманоиды отряда (вьючный зверь не решает и не считается); B6/B3: «сдача-нокаут» идёт
через ch:getMedical():knockoutForceTimer(sec), без прямой записи полей; при ошибке API — самоотключение knockout и откат к runAway.
python -I -X utf8 build/KMM_Conductor/_dev/test_self.py -> OK / FAIL, код 1 при провале."""
import ctypes
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
EVS = {}; RUNAWAY = {}; KO = {}; MEDW = 0
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
-- opt: animal, down, robot, race, leader, broken_med, fac
function MK(nm, key, opt)
  opt = opt or {}
  local c = {}
  local pl = PLAT(key)
  local med = setmetatable({}, { __newindex = function(t, k, v) MEDW = MEDW + 1; rawset(t, k, v) end })
  med.knockoutForceTimer = function(self, sec) KO[#KO + 1] = nm .. ":" .. tostring(sec) end
  MEDW = 0
  function c:getPosition() return { x = 100, y = 0, z = 100 } end
  function c:isDead() return false end
  function c:isDown() return opt.down or false end
  function c:isUnconcious() return false end
  function c:isUnique() return false end
  function c:isPlayerCharacter() return false end
  function c:isInCombatMode() return true end
  function c:getHandle() return "h_" .. nm end
  function c:getFaction() return fac(opt.fac or "Bandits") end
  function c:getPlatoon() return { me = pl } end
  function c:isAnimal() if opt.animal then return { animal = true } end return nil end
  function c:getRace() return { robot = opt.robot or false, data = { name = opt.race or (opt.animal and "Pack Bull" or "Greenlander") } } end
  function c:getMedical() if opt.broken_med then error("getMedical broken") end return med end
  c.medical = med
  function c:getInventory() return { getAllItems = function() return {} end } end
  if opt.leader then pl.leader = c end
  return c
end
CHARS = {}
local PC = { getPosition = function() return { x = 0, y = 0, z = 0 } end, getHandle = function() return "pc" end,
             getInventory = function() return { getAllItems = function() return {} end } end }
function getPlayerInterface() return { getAllPlayerCharacters = function() return { PC } end } end
function getGameWorld() return { getTimeStamp = function() return CLOCK end,
  getCharacterUpdateList = function() local t = {}; for _, c in ipairs(CHARS) do t[c] = true end; return t end } end
Events = { on = function() end }
PARAMS = { enabled = true, scan_seconds = 3, cooldown_seconds = 60, faction_avoid = false }
KMM_Conductor = {
  cfg = function() return { params = { self = PARAMS, guard = { debug_log = "TMPDIR/debug.log" } }, factions = { Bandits = { ftype = 8 } }, player_faction = "player" } end,
  read_json = function() return { item_tiers = {} } end,
  emit = function(ev) EVS[#EVS + 1] = ev end,
}
function TICK() CLOCK = CLOCK + 5; KMM_Self._tick() end
function EV(key) for _, e in ipairs(EVS) do if e.squad == key then return e.type .. ":" .. tostring(e.why or e.mode) .. ":" .. e.n .. ":" .. e.down end end return "none" end
function DIS() local d = {}; for k in pairs(KMM_Self.disabled()) do d[#d + 1] = k end; table.sort(d); return table.concat(d, ",") end
'''


def scenario(setup, params=""):
    tmp = tempfile.mkdtemp(prefix="kmm_self_").replace("\\", "/")
    run, get = make_state()
    run(STUBS.replace("TMPDIR", tmp), "stubs")
    run(open(SELF, encoding="utf-8").read(), "Self")
    run(params, "params")
    run(setup, "setup")
    run("TICK()", "tick")
    return run, get, tmp


# 1. Вьючный бык первым в отряде + 4 человека, трое лежат: раньше «(animal) - no retreat», теперь отряд бежит, считаются только люди.
run, get, tmp = scenario('''
CHARS = { MK("bull", "hn", { animal = true }), MK("p1", "hn", { down = true, leader = true }), MK("p2", "hn", { down = true }),
          MK("p3", "hn", { down = true }), MK("p4", "hn") }''', 'PARAMS.surrender_factions_ftype = {}')
check(get("RUNAWAY.hn") == "1", "B6: бык не блокирует отход людей (runAway=%s)" % get("RUNAWAY.hn"))
check(get('EV("hn")') == "self_retreat:flee:4:3", "B6: потери по людям 3/4, зверь не в счёте (%s)" % get('EV("hn")'))
check(get("DIS()") in ("", None), "ничего не отключено (%s)" % get("DIS()"))

# 2. Стая из одних животных — по-прежнему «без страха».
run, get, tmp = scenario('''
CHARS = { MK("r1", "pack", { animal = true, down = true }), MK("r2", "pack", { animal = true, down = true }), MK("r3", "pack", { animal = true }) }''')
check(get("RUNAWAY.pack") == "nil" and get('EV("pack")') == "none", "стая животных без приказов отхода")
log = open(tmp + "/debug.log", encoding="utf-8").read()
check("fearless: squad pack (animal)" in log, "лог: стая помечена (animal)")

# 3. Роботов среди людей большинство (3/4) — без страха; меньшинство (1/4) — отряд боится и бежит.
run, get, tmp = scenario('''
CHARS = { MK("s1", "sk", { robot = true, down = true }), MK("s2", "sk", { robot = true, down = true }), MK("s3", "sk", { robot = true }), MK("s4", "sk", { down = true }),
          MK("m1", "mx", { robot = true, down = true }), MK("m2", "mx", { down = true }), MK("m3", "mx"), MK("m4", "mx", { down = true }) }''',
                         'PARAMS.surrender_factions_ftype = {}')
check(get("RUNAWAY.sk") == "nil", "большинство роботов — без страха")
check(get("RUNAWAY.mx") == "1", "один робот не решает за людей — отход")

# 4. Сдача-нокаут: ванильный knockoutForceTimer через getMedical(), только стоящим людям, поля medical не пишутся.
run, get, tmp = scenario('''
MEDW = 0
CHARS = { MK("ox", "b", { animal = true }), MK("b1", "b", { down = true, leader = true }), MK("b2", "b", { down = true }),
          MK("b3", "b", { down = true }), MK("b4", "b", { down = true }), MK("b5", "b") }''', 'PARAMS.surrender_mode = "knockout"')
check(get("table.concat(KO, ',')") == "b5:25", "B3: knockoutForceTimer(25) только стоящему человеку (%s)" % get("table.concat(KO, ',')"))
check(get("MEDW") == "0", "B3/B6: прямых записей в поля medical нет (%s)" % get("MEDW"))
check(get('EV("b")') == "self_surrender_attempt:knockout:5:4", "событие сдачи-нокаута по людям (%s)" % get('EV("b")'))
check(get("RUNAWAY.b") == "nil", "при нокауте runAway не отдан")

# 5. getMedical падает: knockout самоотключается, сдача откатывается в runAway, scan жив.
run, get, tmp = scenario('''
CHARS = { MK("c1", "c", { down = true, leader = true }), MK("c2", "c", { down = true }), MK("c3", "c", { down = true }),
          MK("c4", "c", { down = true }), MK("c5", "c", { broken_med = true }) }''', 'PARAMS.surrender_mode = "knockout"')
check(get("DIS()") == "knockout", "сломанный getMedical: отключён только knockout (%s)" % get("DIS()"))
check(get('EV("c")') == "self_surrender_attempt:runaway:5:4" and get("RUNAWAY.c") == "1", "откат сдачи в runAway (%s)" % get('EV("c")'))
log = open(tmp + "/debug.log", encoding="utf-8").read()
check("knockout disabled until restart" in log, "причина отключения в debug.log")

print("\nFAIL: %d" % len(FAILS) if FAILS else "\nALL OK")
sys.exit(1 if FAILS else 0)
