"""Offline test X3-hook: удары в честном поединке (KMM_Diplo.duel_active + конечный duel_until) не дают player_raid/attack_on_player и памяти Nemesis.
python -I -X utf8 build/KMM_Conductor/_dev/test_x3_hit_skip.py -> OK N."""
import ctypes, re, sys, tempfile, glob

DLL = r"C:\Program Files (x86)\Steam\steamapps\workshop\content\233860\3817000612\lua51.dll"
B = r"C:\KenshiModMap\build\KMM_Conductor\scripts\init"
TMP = tempfile.mkdtemp(prefix="kmm_x3h_").replace("\\", "/")
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
for _f in sorted(glob.glob(B + r"\KMM_Conductor*.lua")):
    run(open(_f, encoding="utf-8").read(), _f.split("\\")[-1])
TEST = r'''
N, FAILS = 0, {}
function check(c, what) N = N + 1; if not c then FAILS[#FAILS + 1] = what end end
local C = KMM_Conductor
C.reset()
local KC = KMM_C_INT
local pf = KC.CFG.player_faction
local vf; for fid in pairs(KC.S.F) do if fid ~= pf then vf = fid; break end end
check(pf ~= nil and vf ~= nil, "factions present")
local function ch(isp, fid)
  local f = { getData = function() return { stringID = fid } end }
  return { isPlayerCharacter = function() return isp end, getFaction = function() return f end }
end
local EV = {}
C.subscribe("player_raid", function(e) EV[#EV + 1] = e.type end)
C.subscribe("attack_on_player", function(e) EV[#EV + 1] = e.type end)
local hits = 0
KMM_Nemesis = { on_player_hit = function() hits = hits + 1 end, on_player_attacked = function() hits = hits + 1 end }
local DUEL = true
UNTIL = function() return os.clock() + 300 end
KMM_Diplo = { duel_active = function(fid) return DUEL and fid == vf end, duel_until = function() return UNTIL() end }
-- поединок: игрок бьёт лидера и лидер бьёт игрока
KC.last_hit = {}
KC.on_hit(ch(false, vf), nil, nil, ch(true, pf))
KC.on_hit(ch(true, pf), nil, nil, ch(false, vf))
check(#EV == 0, "duel hits emit nothing: " .. #EV)
check(hits == 0, "duel hits skip Nemesis: " .. hits)
-- не поединок: обычное поведение
DUEL = false; KC.last_hit = {}
KC.on_hit(ch(false, vf), nil, nil, ch(true, pf))
KC.on_hit(ch(true, pf), nil, nil, ch(false, vf))
check(#EV == 2, "normal hits emit raid+attack: " .. #EV)
check(hits == 2, "normal hits reach Nemesis: " .. hits)
-- Diplo без API / с ошибкой: обычное поведение, без падения
KMM_Diplo = { duel_active = function() error("boom") end }; EV = {}; KC.last_hit = {}
C.subscribe("player_raid", function(e) EV[#EV + 1] = e.type end)
KC.on_hit(ch(false, vf), nil, nil, ch(true, pf))
check(#EV >= 1, "diplo error -> normal path")
KMM_Diplo = nil
check(KC.duel(vf) == false, "no Diplo -> not a duel")
-- ревью batch6 H1: дирижёр сам сверяет срок амнистии (Diplo мог умереть с флагом)
KMM_Diplo = { duel_active = function() return true end, duel_until = function() return os.clock() + 120 end }
check(KC.duel(vf) == true, "finite amnesty -> duel")
KMM_Diplo.duel_until = function() return math.huge end
check(KC.duel(vf) == false, "endless amnesty -> not a duel")
KMM_Diplo.duel_until = function() return os.clock() - 1 end
check(KC.duel(vf) == false, "expired amnesty -> not a duel")
KMM_Diplo.duel_until = nil
check(KC.duel(vf) == false, "no duel_until -> not a duel")
KMM_Diplo = nil
'''
run(TEST.replace("TMPDIR", TMP), "test")
run("RES = N .. '|' .. table.concat(FAILS, ' ;; ')", "res")
run("io.write('')")
L.lua_getfield.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_char_p]
L.lua_getfield(st, -10002, b"RES")
res = L.lua_tolstring(st, -1, None).decode("utf-8")
n, fails = res.split("|", 1)
if fails:
    for f in fails.split(" ;; "):
        print("FAIL:", f)
    sys.exit(1)
print("OK", n)
