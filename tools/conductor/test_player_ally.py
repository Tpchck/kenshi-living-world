"""Сценарий: союз с игроком → нападение на игрока → союзник помогает (ally_help) и ставит отправку отряда (pending_dispatch)."""
import ctypes, tempfile
DLL = r"C:\Program Files (x86)\Steam\steamapps\workshop\content\233860\3817000612\lua51.dll"
SCRIPT = r"C:\KenshiModMap\build\KMM_Conductor\scripts\init\KMM_Conductor.lua"
TMP = tempfile.mkdtemp(prefix="kmm_pa_").replace("\\", "/")
L = ctypes.CDLL(DLL); L.luaL_newstate.restype = ctypes.c_void_p
for fn, at in [("luaL_openlibs", [ctypes.c_void_p]), ("luaL_loadstring", [ctypes.c_void_p, ctypes.c_char_p]), ("lua_pcall", [ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int])]:
    getattr(L, fn).argtypes = at
L.lua_tolstring.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p]; L.lua_tolstring.restype = ctypes.c_char_p
st = L.luaL_newstate(); L.luaL_openlibs(st)
def run(code, n):
    rc = L.luaL_loadstring(st, code.encode("utf-8")) or L.lua_pcall(st, 0, 0, 0)
    if rc: raise RuntimeError(n + ": " + L.lua_tolstring(st, -1, None).decode("utf-8", "replace"))
run(f'''local ro = io.open; io.open = function(p, m) p = tostring(p):gsub("^C:/KenshiModMap/logs/", "{TMP}/"); return ro(p, m) end
KenshiLua = {{ log = function() end }}; Events = {{ h = {{}} }}; function Events.on(n, f) Events.h[n] = f end
function getGameWorld() error("no game") end; function getPlayerInterface() error("no game") end''', "stubs")
for _f in sorted(__import__("glob").glob(SCRIPT.replace("KMM_Conductor.lua", "KMM_Conductor*.lua"))): run(open(_f, encoding="utf-8").read(), _f.split("\\")[-1])
run(r'''
math.randomseed(7)
KMM_Conductor.reset()
local S = KMM_Conductor.state()
local P = "204-gamedata.base"; local UC = "defaultEmpireFactionSID"
local enemy
for fid, v in pairs(S.rel[UC] or {}) do if v <= -50 and S.F[fid] and fid ~= P then enemy = fid; break end end
S.rel[P][UC], S.rel[UC][P] = 60, 60
S.rel[P][enemy], S.rel[enemy][P] = -80, -80
local signed
for d = 0, 2000 do
  KMM_Conductor.advance(d)
  for _, t in pairs(S.treaties) do if t.active and (t.a == P or t.b == P) then signed = t end end
  if signed then break end
end
assert(signed, "no treaty with player in 2000 days")
if signed.type == "trade" or signed.type == "nonaggression" then signed.type = "defense" end   -- для теста обязательств
KMM_Conductor.hit(enemy)
local helped = false
for _, e in ipairs(S.events) do if e.type == "ally_help" and e.b == P then helped = true end end
io.stdout:write(string.format("treaty with player: %s %s<->%s since day %.0f | ally_help to player: %s | pending_dispatch: %s%s",
  signed.type, signed.a, signed.b, signed.since, tostring(helped), tostring(S.pending_dispatch and S.pending_dispatch.ally), string.char(10)))
io.stdout:flush()
''', "scenario")
