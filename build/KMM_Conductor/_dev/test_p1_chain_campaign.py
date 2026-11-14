"""Offline test P1: B4 хозяин оков (Character:setChainedMode(on, owner)) = пленитель, не сам пленник; самотест читает isChainedMode();
B8 маркер «campaign: triggerCampaign ok|FAIL» в debug.log для tools/session_report.py.
python -I -X utf8 build/KMM_Conductor/_dev/test_p1_chain_campaign.py -> OK."""
import ctypes, os, re, sys, tempfile

DLL = r"C:\Program Files (x86)\Steam\steamapps\workshop\content\233860\3817000612\lua51.dll"
B = r"C:\KenshiModMap\build\KMM_Conductor\scripts\init"
TMP = tempfile.mkdtemp(prefix="kmm_p1_").replace("\\", "/")
L = ctypes.CDLL(DLL)
L.luaL_newstate.restype = ctypes.c_void_p
for fn, at in [("luaL_openlibs", [ctypes.c_void_p]), ("luaL_loadstring", [ctypes.c_void_p, ctypes.c_char_p]),
               ("lua_pcall", [ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int])]:
    getattr(L, fn).argtypes = at
L.lua_tolstring.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p]
L.lua_tolstring.restype = ctypes.c_char_p
L.lua_getfield.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_char_p]
st = L.luaL_newstate()
L.luaL_openlibs(st)


def run(code, name="chunk"):
    if L.luaL_loadstring(st, code.encode("utf-8")) or L.lua_pcall(st, 0, 0, 0):
        msg = L.lua_tolstring(st, -1, None)
        raise RuntimeError(f"{name}: {msg.decode('utf-8', 'replace') if msg else '?'}")


rt = open(r"C:\KenshiModMap\tools\test\test_runtime.py", encoding="utf-8").read()
run(re.search(r"STUBS = r'''(.*?)'''", rt, re.S).group(1).replace("TMPDIR", TMP), "stubs")
run("math.randomseed(20261115)", "seed")
src = ""   # SRC ниже - весь текст дирижёра (главный файл + части)
for _f in sorted(__import__("glob").glob(B + r"\KMM_Conductor*.lua")):
    src += open(_f, encoding="utf-8").read() + "\n"
    run(open(_f, encoding="utf-8").read(), _f.split("\\")[-1])
TEST = r'''
N, FAILS = 0, {}
function check(c, what) N = N + 1; if not c then FAILS[#FAILS + 1] = what end end
local C = KMM_Conductor
C.reset()
local S = C.state()
local P = C.cfg().params
P.guard = P.guard or {}; P.guard.debug_log = "TMPDIR/debug.log"
-- B4: хозяин оков
local cap = MKCH("Captive", "victims", 1000, 1000, {})
local guard_far = MKCH("FarGuard", "captors", 9000, 1000, {})
local guard_near = MKCH("NearGuard", "captors", 1200, 1000, {})
local dead_g = MKCH("DeadGuard", "captors", 1010, 1000, {}); dead_g.dead = true
local other = MKCH("Other", "thirds", 1005, 1000, {})
local pc = MKCH("PC", "player", 1100, 1000, { player = true })
CHARS = { cap, guard_far, guard_near, dead_g, other, pc }
local h, tag = C.chain_owner(cap, "captors")
check(h == "h_NearGuard" and tag == "captor", "captor: nearest living captor-faction char: " .. tostring(h) .. " " .. tostring(tag))
h, tag = C.chain_owner(cap, "nobody_here", pc)
check(h == "h_PC" and tag == "prefer", "no captor loaded -> prefer (player in self-test): " .. tostring(h) .. " " .. tostring(tag))
function cap:getMySlaveOwner() return { null = false, setNull = function(s) s.null = true end } end
h, tag = C.chain_owner(cap, "nobody_here")
check(type(h) == "table" and h.null == true and tag == "none", "no captor, no prefer -> null hand copy: " .. tostring(tag))
cap.getMySlaveOwner = nil
h, tag = C.chain_owner(cap, nil)
check(h == "h_Captive" and tag == "self", "last resort: legacy self handle: " .. tostring(tag))
check(C.chain_owner(cap, "captors", nil, 100) == "h_Captive", "radius respected")
-- исходник: isChained() как метод больше не вызывается, а setChainedMode не получает ch:getHandle() пленника напрямую
check(not SRC:find(":isChained%(%)"), "no :isChained() method call")
check(SRC:find(":isChainedMode%(%)") ~= nil, "isChainedMode() used")
local direct = 0; for _ in SRC:gmatch("setChainedMode%(true, [%w%.]+:getHandle%(%)%)") do direct = direct + 1 end
check(direct == 1, "only the retry fallback chains to self handle: " .. direct)
-- B8: маркер в debug.log
local CA = C.camp()
P.campaign.sdir = "TMPDIR/"
CA.PROBE = {}
local fo = FAC("captors")
local okc = CA.probe_call("triggerCampaign", function() end, "native captors camp_x")
check(okc == true, "probe ok")
okc = CA.probe_call("triggerCampaign", function() error("engine says no") end, "native captors camp_y")
check(okc == false, "probe fail returns false")
CA.probe_call("RelationData", function() end)   -- без ctx — без строки
local f = io.open("TMPDIR/debug.log", "r"); local dbg = f and f:read("*a") or ""; if f then f:close() end
check(dbg:find("campaign: triggerCampaign ok native captors camp_x", 1, true) ~= nil, "ok marker in debug.log")
check(dbg:find("campaign: triggerCampaign FAIL native captors camp_y: ", 1, true) ~= nil and dbg:find("engine says no", 1, true) ~= nil, "FAIL marker with reason")
check(not dbg:find("RelationData ok", 1, true), "no marker without ctx")
DBGL = dbg:sub(-400)
RESULT = #FAILS == 0 and ("OK " .. N) or ("FAIL: " .. table.concat(FAILS, "; "))
'''
L.lua_pushstring.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
L.lua_setfield.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_char_p]
L.lua_pushstring(st, src.encode("utf-8"))
L.lua_setfield(st, -10002, b"SRC")
run(TEST.replace("TMPDIR", TMP), "test")
L.lua_getfield(st, -10002, b"RESULT")
r = L.lua_tolstring(st, -1, None).decode()
print(r)
if not r.startswith("OK"):
    L.lua_getfield(st, -10002, b"DBGL"); print(L.lua_tolstring(st, -1, None).decode("utf-8", "replace"))
# маркеры есть в списке session_report
sr = open(r"C:\KenshiModMap\tools\session_report.py", encoding="utf-8").read()
mk = all(m in sr for m in ("campaign: triggerCampaign ok", "campaign: triggerCampaign FAIL"))
print("session_report markers:", "OK" if mk else "MISSING")
sys.exit(0 if r.startswith("OK") and mk else 1)
