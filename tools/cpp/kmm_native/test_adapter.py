"""Offline test of KMM_Native.lua v2 adapter (lua51.dll from KenshiLua): no module, old module, fake v2 module, throwing module.
python -I -X utf8 tools/cpp/kmm_native/test_adapter.py -> OK, exit 1 on failure."""
import ctypes, sys
DLL = r"C:\Program Files (x86)\Steam\steamapps\workshop\content\233860\3817000612\lua51.dll"
AD = r"C:\KenshiModMap\build\KMM_Native\scripts\init\KMM_Native.lua"
L = ctypes.CDLL(DLL)
L.luaL_newstate.restype = ctypes.c_void_p
for fn, at in [("luaL_openlibs", [ctypes.c_void_p]), ("luaL_loadstring", [ctypes.c_void_p, ctypes.c_char_p]),
               ("lua_pcall", [ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int])]:
    getattr(L, fn).argtypes = at
L.lua_tolstring.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p]
L.lua_tolstring.restype = ctypes.c_char_p
fails = 0
def run(code):
    st = L.luaL_newstate(); L.luaL_openlibs(st)
    if L.luaL_loadstring(st, code.encode()) or L.lua_pcall(st, 0, 1, 0):
        return "ERR " + (L.lua_tolstring(st, -1, None) or b"?").decode()
    return (L.lua_tolstring(st, -1, None) or b"").decode()
src = open(AD, encoding="utf-8").read()
def case(name, setup, body, want):
    global fails
    code = "ADS=[==[" + src + "]==]\n" + setup + "\ndofile=nil\nlocal f=assert(loadstring(ADS)); f()\nlocal K=KMM_Native\n" + body
    got = run(code)
    ok = got == want
    print(("ok  " if ok else "FAIL"), name, "" if ok else f"got={got!r} want={want!r}")
    fails += 0 if ok else 1
probe = ("return tostring(K.getFactionForce('x'))..'|'..tostring(K.unique_set('n',0))..'|'..tostring(K.unique_get('n'))"
         "..'|'..tostring(K.orderSquad(1,'join',2))..'|'..tostring(K.available)..'|'..tostring(K.ws_set('7-KMM_Elite.mod',true))")
case("no module: all no-op", "package.loaded.kmm_native=nil", probe, "nil|false|nil|false|false|false")
case("old v1 module: new fns no-op", "package.loaded.kmm_native={ws_hook_active=function() return true end, ws_set=function() return true end}",
     probe, "nil|false|nil|false|true|true")
case("fake v2 module", "package.loaded.kmm_native={ws_hook_active=function() return true end, faction_force=function(s) return {squads=3,chars=9} end, unique_set=function() return true end, unique_get=function() return 1 end}",
     "local r=K.getFactionForce('f'); return r.squads..'|'..r.chars..'|'..tostring(K.unique_set('n',2))..'|'..tostring(K.unique_get('n'))..'|'..tostring(K.unique_set('n',7))",
     "3|9|true|1|false")
case("bad args", "package.loaded.kmm_native={faction_force=function() return {squads=1} end}",
     "return tostring(K.getFactionForce(5))..'|'..tostring(K.unique_set(1,1))..'|'..tostring(K.unique_get(nil))", "nil|false|nil")
case("throwing module disables adapter, no error", "package.loaded.kmm_native={faction_force=function() error('boom') end, ws_hook_active=function() return true end}",
     "local a=K.getFactionForce('f'); return tostring(a)..'|'..tostring(K.available)", "nil|false")
case("whitelist: only own KMM sids reach the module", "CALLS={}; package.loaded.kmm_native={ws_hook_active=function() return true end, ws_set=function(s) CALLS[#CALLS+1]=s; return true end, ws_clear=function(s) CALLS[#CALLS+1]=s; return true end}",
     "local r={K.ws_set('51751-Dialogue.mod',false), K.ws_set('1532623-__world reactions.mod',true), K.ws_set('5-KMM_Merged.mod',true), K.ws_set('x-KMM_Elite.mod',true), K.ws_clear('57392-rebirth.mod'), K.ws_set('900001-KMM_Elite.mod',true), K.ws_clear('900001-KMM_Elite.mod')}"
     " local o={} for i=1,7 do o[i]=tostring(r[i]) end return table.concat(o,',')..'|'..#CALLS..'|'..K.refused()..'|'..tostring(K.is_own_ws('6-KMM_Elite.mod'))",
     "false,false,false,false,false,true,true|2|5|true")
print("OK" if not fails else "FAILED", fails)
sys.exit(1 if fails else 0)
