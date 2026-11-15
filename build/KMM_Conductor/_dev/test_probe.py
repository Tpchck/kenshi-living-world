"""Офлайн-тест KMM_Probe (самопроверка модулей в игровой сессии, 2026-11-15) на общих заглушках tools/test/test_runtime.py.
(1) ждёт персонажей игрока и start_s; проход 1 — все пробы, по одной строке на пробу + summary; порции по кадрам (<= per_frame);
(2) строки формата «<дата время> PROBE <имя> ok|fail|absent <значение>», summary сходится со строками;
(3) смысл: деньги, цена вещей, победитель, update_list:has, шаблон отряда, руда/руины по скану, запах, журнал -> ok с числами;
(4) проба ничего не пишет: спавн/createItem/addItem/addMessage/addSmell/запись полей = 0, setRelation не растёт,
    модель дирижёра (serialize) та же, счётчик tier_pick Traces тот же, в чужие логи ничего не дописано;
(5) сбой одной пробы (getMoney, getCharacterUpdateList, getSingleton, getData=nil, пауза в реестре KMM_Gov) -> её fail, остальные ok, модуль жив;
(6) проход 2 через repeat_s — только warm-пробы, потом тишина; загрузка сейва -> снова проход 1;
(7) крэш-сторож: lock от «прошлой сессии» -> .off, проба пропущена с fail, lock снят.
python -I -X utf8 tools/test/log_sandbox.py test_probe.py (из build/KMM_Conductor/_dev) -> OK."""
import ctypes
import glob
import os
import re
import sys
import tempfile

DLL = r"C:\Program Files (x86)\Steam\steamapps\workshop\content\233860\3817000612\lua51.dll"
B = r"C:\KenshiModMap\build"
INIT = B + r"\KMM_Conductor\scripts\init"
TMP = tempfile.mkdtemp(prefix="kmm_probe_").replace("\\", "/")
L = ctypes.CDLL(DLL)
L.luaL_newstate.restype = ctypes.c_void_p
for fn, at in [("luaL_openlibs", [ctypes.c_void_p]), ("luaL_loadstring", [ctypes.c_void_p, ctypes.c_char_p]),
               ("lua_pcall", [ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int])]:
    getattr(L, fn).argtypes = at
L.lua_tolstring.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p]
L.lua_tolstring.restype = ctypes.c_char_p
L.lua_getfield.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_char_p]
L.lua_settop.argtypes = [ctypes.c_void_p, ctypes.c_int]
st = L.luaL_newstate()
L.luaL_openlibs(st)
FAILS = []


def run(code, name="chunk"):
    if L.luaL_loadstring(st, code.encode("utf-8")) or L.lua_pcall(st, 0, 0, 0):
        msg = L.lua_tolstring(st, -1, None)
        raise RuntimeError(f"{name}: {msg.decode('utf-8', 'replace') if msg else '?'}")


def val(expr):
    run(f"_V = tostring({expr})", "val")
    L.lua_getfield(st, -10002, b"_V")
    v = L.lua_tolstring(st, -1, None)
    L.lua_settop(st, -2)
    return v.decode("utf-8", "replace") if v else None


def check(c, msg):
    print(("OK   " if c else "FAIL ") + msg)
    if not c:
        FAILS.append(msg)


rt = open(r"C:\KenshiModMap\tools\test\test_runtime.py", encoding="utf-8").read()
run(re.search(r"STUBS = r'''(.*?)'''", rt, re.S).group(1).replace("TMPDIR", TMP), "stubs")
run("math.randomseed(20261115)", "seed")
for f in sorted(glob.glob(INIT + r"\KMM_Conductor*.lua")):
    run(open(f, encoding="utf-8").read(), os.path.basename(f))
for f in (INIT + r"\KMM_Gov.lua", INIT + r"\KMM_Traces.lua", INIT + r"\KMM_Outlaws.lua", INIT + r"\KMM_Nemesis.lua", B + r"\KMM_Rumors\scripts\init\KMM_Rumors.lua"):
    run(open(f, encoding="utf-8").read(), os.path.basename(f))

# мир и шпионы записи: всё, что проба не должна вызывать или писать, увеличивает WR.n
run(r'''
WR = { n = 0, what = {} }
local function W(what) WR.n = WR.n + 1; WR.what[#WR.what + 1] = what end
local function ro(t, nm) return setmetatable({}, { __index = t, __newindex = function(_, k) W(nm .. "." .. tostring(k)) end }) end
FAULT = {}
local C = KMM_Conductor
C.reset()
local S = C.state()
local fk = {}; for fid, f in pairs(S.F) do if f.alive and not f.player then fk[#fk + 1] = fid end end; table.sort(fk)
FID = fk[1]
local pf = C.cfg().player_faction or "player"
local function item(v) return ro({ getValueAll = function(self, isp) return v end, quantity = 1 }, "item") end
local function inv(items)
  return ro({ getAllItems = function() return ENGINE_LIST(items) end,
              addItem = function() W("addItem") end, tryAddItem = function() W("tryAddItem") end,
              getItem = function() W("getItem") end, removeItemDontDestroy_returnsItem = function() W("removeItem") end,
              isAContainer = function() return false end }, "inv")
end
BANDIT = MKCH("Bandit Boss", FID, 100, 100, {})
local function pc(nm, money, items, hungry)
  local c = MKCH(nm, pf, 0, 0, { player = true, platoon = "player_squad" })
  c.getCarryingObject = function() return { setNull = function() end } end
  c.getMoney = function() if FAULT.money then error("no money binding") end; return money end
  c.getPlatoon = function() return { me = { getOwnerships = function() if FAULT.money then error("no ownerships") end; return { getMoney = function() return money end } end } } end
  local med = ro({ isReallyHungry = function() return hungry end, isHungerKO = function() return false end, hunger = hungry and 150 or 300 }, "med")
  c.getMedical = function() return med end
  c.crimes = ro({ getTotalBounty = function() return 250 end, _getHighestBountyFaction = function() return FAC(FID) end }, "crimes")
  c.lastGuyWhoDefeatedMe = ro({ isNull = function() return false end, getCharacter = function() return BANDIT end }, "hand")
  local iv = inv(items)
  c.getInventory = function() return iv end
  return ro(c, "pc")
end
PCS = {}
-- проба ждёт персонажей игрока: сначала их нет
MS_OBJ = ro({ addMessage = function() W("addMessage") end }, "ms")
ManagementScreen = { getSingleton = function() if FAULT.ms then error("no window") end; return MS_OBJ end }
MessageLogColor = { ML_NORMAL = 0, ML_SYSTEM = 2 }
SmellType = { SMELL_BLOOD_AND_CORPSES = 1 }
ZS = ro({ addSmell = function() W("addSmell") end, getGeneralSmellLevel = function(self, t) return 0.5 end }, "zs")
ZMGR = ro({ getZoneMap = function(self, p) if type(p) ~= "table" or not p.x then error("bad pos") end; return ro({ zoneSmell = ZS }, "zm") end,
            isZoneLoadedT = function() return true end }, "zmgr")
local function bld(sid, fac, shop, cont, mining)
  local pb = mining and ro({ _resourceMiningLevel = mining }, "pb") or nil
  local b = ro({ getProductionBuilding = function() return pb end, hasFaction = function() return fac end, isAShop = function() return shop end,
                 getInventory = function() return ro({ isAContainer = function() return cont end, addItem = function() W("addItem") end }, "binv") end,
                 getGameData = function() return { stringID = sid } end, getPosition = function() return { x = 0, y = 0, z = 0 } end }, "bld")
  return ro({ getHandle = function() return { getBuilding = function() return b end } end }, "obj")
end
OBJS = { bld("ore_iron_node", false, false, false, 0.8), bld("ruin_crate", false, false, true), bld("shop", true, true, true), bld("house", true, false, false),
         bld("farm", true, false, false, 0) }
BUFS = 0
lektor = { new = function(t) BUFS = BUFS + 1; local b = {}; function b:clear() for i = #self, 1, -1 do self[i] = nil end end; return b end }
local set = newproxy(true)
do local mt = getmetatable(set)
  mt.__index = { has = function(self, c) return c == PCS[1] or c == PCS[2] end }
  mt.__pairs = function() local t = {}; for _, c in ipairs(PCS) do t[c] = true end; t[BANDIT] = true; return next, t, nil end
end
local gw0 = getGameWorld
getGameWorld = function()
  local w = gw0()
  local f0 = w.theFactory
  w.theFactory = { createItem = function() W("createItem"); return {} end, createRandomSquad = function(...) W("createRandomSquad"); return f0.createRandomSquad(...) end }
  w.getCharacterUpdateList = function() if FAULT.ulist then error("update list boom") end; return set end
  w.getObjectsWithinSphere = function(self, buf, pos, r, ty, mx, skip) for i, o in ipairs(OBJS) do if i <= mx then buf[#buf + 1] = o end end end
  w.zoneMgr = ZMGR
  local gd0 = w.gamedata
  w.gamedata = { getData = function(self, sid, t) if FAULT.gd then return nil end; return gd0:getData(sid, t) end }
  return setmetatable({}, { __index = w, __newindex = function(_, k) W("gw." .. tostring(k)) end })
end
KMM_Ore = { status = function() return "v3 stub nodes=1" end, disabled = function() return {} end }
-- журнал: два события дирижёра, одно рассказано слухом
local e1 = C.emit({ type = "probe_test", a = FID, text = "one" })
local e2 = C.emit({ type = "probe_test", a = FID, text = "two" })
KMM_Rumors.told[tostring(e1.id) .. "|Town"] = true
KMM_Nemesis._N.state(S)   -- слот Nemesis в модели создаёт сам Nemesis на своём такте; проба его не создаёт
MKPCS = function() PCS = { pc("Nameless", 1234, { item(100), item(50) }, false), pc("Beep", 1234, {}, true) } end
''', "world")

nh0 = int(val('#(Events.h["GameWorld::charsUpdate"] or {})'))
nl0 = int(val('#(Events.h["PlayerInterface::loadFromSerialise"] or {})'))
run(open(INIT + r"\KMM_Probe.lua", encoding="utf-8").read(), "KMM_Probe.lua")
check(int(val('#Events.h["GameWorld::charsUpdate"]')) == nh0 + 1 and int(val('#Events.h["PlayerInterface::loadFromSerialise"]')) == nl0 + 1,
      "KMM_Probe: один обработчик charsUpdate и один loadFromSerialise")
run(f'''PH = Events.h["GameWorld::charsUpdate"][{nh0 + 1}]; LH = Events.h["PlayerInterface::loadFromSerialise"][{nl0 + 1}]
function PTICK(n, dt) for i = 1, n do CLOCK = CLOCK + (dt or 0.016); PH({{}}) end end
local cfg = KMM_Probe.cfg(); cfg.start_s, cfg.repeat_s, cfg.per_frame = 20, 300, 2
SER0 = KMM_Conductor.serialize(); SETREL0, SPAWNS0 = SETREL, #SPAWNS
local ts = KMM_Traces.tier_stats(); PICKS0 = ts and ts.picks''', "probe handles")

LOG = os.path.join(TMP, "probe.log")
LINE = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} PROBE (\S+) (ok|fail|absent) (.+)$")
SUMM = re.compile(r"PROBE summary ok=(\d+) fail=(\d+) absent=(\d+) pass=(\d+)")


def log_lines():
    try:
        return open(LOG, encoding="utf-8").read().splitlines()
    except OSError:
        return []


def passes(lines):
    """[(строки проб, summary-строка)] по порядку."""
    out, cur = [], []
    for l in lines:
        if " PROBE summary " in l:
            out.append((cur, l)); cur = []
        else:
            cur.append(l)
    return out


def others_snapshot():
    snap = {}
    for p in glob.glob(TMP + "/*"):
        b = os.path.basename(p)
        if b != "probe.log" and not b.startswith("probe_kmmprobe"):
            snap[b] = os.path.getsize(p)
    return snap


NAMES = val('table.concat(KMM_Probe.names(), " ")').split()
check(len(NAMES) >= 25 and len(set(NAMES)) == len(NAMES), f"проб {len(NAMES)}, имена уникальны")
for need in ("money", "item_value", "management_screen", "defeated_by", "medical", "combat_mode", "squad_template", "update_list", "bounty",
             "ore_nodes", "ore_module", "ruin_containers", "smell", "carrier_api", "journal", "mod_Nemesis", "mod_Traces", "mod_Rumors",
             "mod_Outlaws", "mod_Predators", "mod_Diplo", "health_registry"):
    check(need in NAMES, f"проба {need} есть")

# (1) нет персонажей -> ничего; персонажи появились -> ждём start_s
snap0 = others_snapshot()
run("PTICK(200, 0.5)", "no players")
check(not log_lines(), "без персонажей игрока проба молчит")
run("MKPCS(); PTICK(30, 0.5)", "players, before start_s")
check(not log_lines(), "персонажи есть, но start_s не прошло — молчит")
run("for i = 1, 40 do PTICK(1, 0.5); local fh = io.open('C:/KenshiModMap/logs/probe.log', 'r'); if fh then fh:close(); break end end", "start pass 1, first frame")
first = log_lines()
check(1 <= len(first) <= 2, f"первый кадр прохода: не больше per_frame=2 строк ({len(first)})")
run("PTICK(60, 0.016)", "finish pass 1")
P = passes(log_lines())
check(len(P) == 1, f"проход 1 завершён summary ({len(P)})")
body, summ = P[0] if P else ([], "")
bad = [l for l in body if not LINE.match(l)]
check(not bad, f"формат строк PROBE <имя> ok|fail|absent <значение> ({bad[:2]})")
got = {LINE.match(l).group(1): (LINE.match(l).group(2), LINE.match(l).group(3)) for l in body if LINE.match(l)}
check(sorted(got) == sorted(NAMES) and len(body) == len(NAMES), f"проход 1: каждая проба ровно одной строкой ({len(body)} строк, {len(NAMES)} проб)")
m = SUMM.search(summ)
cnt = {s: sum(1 for v in got.values() if v[0] == s) for s in ("ok", "fail", "absent")}
check(bool(m) and (int(m.group(1)), int(m.group(2)), int(m.group(3))) == (cnt["ok"], cnt["fail"], cnt["absent"]) and m.group(4) == "1",
      f"summary сходится со строками: {summ[20:]} vs {cnt}")
fails1 = {k: v for k, v in got.items() if v[0] == "fail"}
check(not fails1, f"чистый мир: ни одного fail ({fails1})")


def st_of(name, rx=None):
    s, v = got.get(name, ("?", ""))
    return s == "ok" and (rx is None or re.search(rx, v) is not None), f"{name}: {s} {v}"


for name, rx in [("players", r"n=2 alive=2"), ("money", r"money=1234 via=Character:getMoney"), ("item_value", r"items=2 getValueAll=2 .*gear=150"),
                 ("nemesis_worth", r"money=1234"), ("management_screen", r"addMessage=function"), ("defeated_by", r"set=2 who=Bandit Boss"),
                 ("medical", r"n=2 reallyHungry=1 hungerKO=0"), ("combat_mode", r"n=2 in_combat=0"), ("squad_template", r"templates found: \S+"),
                 ("update_list", r"n=3 has\(player\)=true"), ("bounty", r"total=500 highest=" + re.escape(val("FID"))), ("game_time", r"days="),
                 ("world_model", r"alive=\d+"), ("ore_nodes", r"buildings=5 production=2 mining=1 tpl=ore_iron_node"),
                 ("ore_module", r"v3 stub"), ("ruin_containers", r"faction=3 no_faction=2 containers=1 free_containers=1 shops=1"),
                 ("smell", r"addSmell=yes level=0\.50"), ("carrier_api", r"present"), ("journal", r"events_24h=\d+ rumored=1"),
                 ("mod_Nemesis", r"nothing disabled"), ("mod_Traces", r"nothing disabled"), ("health_registry", r"mechanics=\d+ ok=\d+ pause=0 retry=0 off=0"),
                 ("mod_Gov", r"nothing disabled")]:
    ok, what = st_of(name, rx)
    check(ok, "смысл: " + what[:170])
check(got.get("mod_Diplo", ("",))[0] == "absent" and got.get("mod_Predators", ("",))[0] == "absent", "не загруженный модуль -> absent")

# (4) ничего не записано
check(val("WR.n") == "0", f"проба ничего не вызвала и не записала в мир: {val('table.concat(WR.what, \",\")')}")
check(val("SETREL == SETREL0 and #SPAWNS == SPAWNS0") == "true", "ни setRelation, ни спавна")
_same = val("KMM_Conductor.serialize() == SER0") == "true"
if not _same:
    a, b = val("SER0"), val("KMM_Conductor.serialize()")
    i = next((k for k in range(min(len(a), len(b))) if a[k] != b[k]), min(len(a), len(b)))
    print("  diff at", i, repr(a[max(0, i - 80):i + 80]), "||", repr(b[max(0, i - 80):i + 80]))
check(_same, "модель дирижёра (то, что идёт в сейв) не изменилась")
check(val("KMM_Traces.tier_stats().picks == PICKS0") == "true", "счётчик tier_pick Traces не сдвинут пробой")
check(others_snapshot() == snap0, "в чужие логи и state проба ничего не дописала")
check(val("BUFS") == "1", "один lektor-буфер на сессию")

# (6) проход 2 через repeat_s: только warm, затем тишина
run("PTICK(100, 1.0)", "before repeat")
check(len(passes(log_lines())) == 1, "до repeat_s второго прохода нет")
run("PTICK(260, 1.0); PTICK(60, 0.016)", "pass 2")
P = passes(log_lines())
check(len(P) == 2 and "pass=2" in P[-1][1], f"проход 2 через repeat_s ({len(P)})")
warm = val('(function() local o = {} for _, p in ipairs(KMM_Probe._probes) do if p.warm then o[#o + 1] = p.name end end return table.concat(o, " ") end)()').split()
n2 = [LINE.match(l).group(1) for l in (P[-1][0] if P else []) if LINE.match(l)]
check(sorted(n2) == sorted(warm) and "money" not in n2 and "management_screen" in n2, f"проход 2 — только warm ({len(n2)} из {len(NAMES)})")
run("PTICK(2000, 1.0)", "silence")
check(len(passes(log_lines())) == 2, "после второго прохода молчит до загрузки")

# (5) сбой одной пробы не мешает остальным; загрузка сейва -> снова проход 1
run('KMM_Gov.h_fail("KMM_Town.haul", "carrier addItem failed"); FAULT.money = true; FAULT.ulist = true; FAULT.ms = true; FAULT.gd = true; LH(nil, nil); PTICK(30, 1.0); PTICK(80, 0.016)', "faults")
P = passes(log_lines())
check(len(P) == 3 and "pass=1" in P[-1][1], "загрузка сейва -> новый проход 1")
got3 = {LINE.match(l).group(1): (LINE.match(l).group(2), LINE.match(l).group(3)) for l in (P[-1][0] if P else []) if LINE.match(l)}
for name, rx in [("money", r"no money binding"), ("update_list", r"update list boom"), ("management_screen", r"no window"),
                 ("squad_template", r"createRandomSquad would get nil #6"), ("health_registry", r"pause=1 .*KMM_Town\.haul=pause\(error.*carrier addItem failed")]:
    s, v = got3.get(name, ("?", ""))
    check(s == "fail" and re.search(rx, v) is not None, f"сбой -> fail с причиной: {name} {s} {v[:120]}")
okn = [k for k, v in got3.items() if v[0] == "ok"]
check(got3.get("nemesis_worth", ("",))[0] == "fail", "Nemesis.worth без денег ядра -> fail (money unread)")
check(len(got3) == len(NAMES) and len(okn) == cnt["ok"] - 6, f"остальные пробы ok ({len(okn)} = {cnt['ok']} - 6)")
check(val("next(KMM_Probe.disabled())") == "nil", "модуль пробы жив после сбоев")
check(val("WR.n") == "0", "и при сбоях ничего не записано")

# (7) крэш-сторож: lock «прошлой сессии»
open(os.path.join(TMP, "probe_kmmprobe.lock"), "w").write("smell")
run('FAULT = {}; KMM_Probe._P.lock_checked = false; KMM_Probe._P.offc = {}; LH(nil, nil); PTICK(30, 1.0); PTICK(80, 0.016)', "crash guard")
P = passes(log_lines())
got4 = {LINE.match(l).group(1): (LINE.match(l).group(2), LINE.match(l).group(3)) for l in (P[-1][0] if P else []) if LINE.match(l)}
s, v = got4.get("smell", ("?", ""))
check(s == "fail" and "crashed" in v and "probe_kmmprobe_smell.off" in v, f"lock -> проба пропущена с fail: {s} {v[:110]}")
check(os.path.exists(os.path.join(TMP, "probe_kmmprobe_smell.off")) and not os.path.exists(os.path.join(TMP, "probe_kmmprobe.lock")),
      "lock -> state/probe_kmmprobe_smell.off, lock снят")
check(got4.get("ore_nodes", ("",))[0] == "ok" and got4.get("money", ("",))[0] == "ok", "остальные пробы идут")

print("FAILS:", len(FAILS))
print("OK" if not FAILS else "FAIL")
sys.exit(1 if FAILS else 0)
