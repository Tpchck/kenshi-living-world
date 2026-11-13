"""Offline test KMM_Herds: дальний мир (40 дней: события, глат склада, объём состояния), материализация рядом с игроком (лимит 3, кулдаун), самоотключение. python -I -X utf8 build/KMM_Conductor/_dev/test_herds.py -> OK."""
import ctypes, re, sys, tempfile

DLL = r"C:\Program Files (x86)\Steam\steamapps\workshop\content\233860\3817000612\lua51.dll"
B = r"C:\KenshiModMap\build\KMM_Conductor\scripts\init"
TMP = tempfile.mkdtemp(prefix="kmm_herds_").replace("\\", "/")
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
for _f in sorted(__import__("glob").glob(B + r"\KMM_Conductor*.lua")): run(open(_f, encoding="utf-8").read(), _f.split("\\")[-1])
run(open(B + r"\KMM_Traces.lua", encoding="utf-8").read(), "KMM_Traces.lua")
run(open(B + r"\KMM_Herds.lua", encoding="utf-8").read(), "KMM_Herds.lua")
run(r'''
N, FAILS = 0, {}
function check(c, what) N = N + 1; if not c then FAILS[#FAILS + 1] = what end end
local C = KMM_Conductor
C.reset()
local TP = C.cfg().params.traces
TP.first_hour_traces = 0; TP.max_per_day = 1000; TP.max_queue = 1000; TP.arrive_enabled = false
TP.bounty = { enabled = false }
local H, T = KMM_Herds, KMM_Traces
local pf = C.cfg().player_faction
PCS = {}; CHARS = {}
local ch = MKCH("PC1", pf or "player", 0, 0, { player = true, platoon = "player_squad" })
PCS[1] = ch; CHARS[1] = ch
local function pump(n, dday) for i = 1, n do CLOCK = CLOCK + 80; DAYV = DAYV + (dday or 0.0001); FIRE("GameWorld::charsUpdate", {}) end end
-- 1. данные
local ok0 = pcall(function() H.tick() end)
DAYV = 5; pump(3)
local D = H.data()
check(D and #D.herds >= 6 and #D.herds <= 12, "herds 6..12: " .. tostring(D and #D.herds))
check(not H.disabled(), "not disabled after start")
local e = C.state().ext and C.state().ext.herds
check(e and e.h and next(e.h) ~= nil, "ext.herds created lazily")
-- 2. дальний мир: 40 дней, без игрока рядом; склад города
PCS[1].pos = nil
local function setpos(x, z) ch.getPosition = function() return { x = x, y = 0, z = z } end end
setpos(9e6, 9e6)
local stock = C.stock_state()
stock.towns = stock.towns or {}
for _, t in ipairs(C.towns()) do stock.towns[t.sid] = { q = { food = 8, lux = 8 }, tn = { food = 10, lux = 10 }, lv = { food = 0.8, lux = 0.8 } } end
local nstock = 0
for sid, s in pairs(stock and stock.towns or {}) do nstock = nstock + 1 end
local counts = {}
local before = #C.state().events
for d = 1, 40 do DAYV = 5 + d; pump(2, 0.0001) end
for i = before + 1, #C.state().events do local ev = C.state().events[i]; counts[ev.type] = (counts[ev.type] or 0) + 1 end
check((counts.herd_move or 0) >= 4, "herd_move events: " .. tostring(counts.herd_move))
check((counts.herd_pred or 0) >= 2, "herd_pred events: " .. tostring(counts.herd_pred))
check((counts.herd_hunt or 0) >= 1, "herd_hunt events: " .. tostring(counts.herd_hunt))
check(not H.disabled(), "not disabled after 40 days")
check(H.stats().glut >= 1 and (counts.herd_glut or 0) >= 1, "glut applied: " .. tostring(H.stats().glut))
local up, mx = 0, 0
for _, s2 in pairs(stock.towns) do if s2.q.food > 8.001 then up = up + 1 end; mx = math.max(mx, s2.lv.food or 0) end
check(up >= 1 and mx <= 1.601, "stock food raised in " .. up .. " towns, max lv " .. mx)   -- потолок herds — 1.6 нормы города (норма у городов разная)
local ser = C.serialize()
local es = C.state().ext.herds
local sz = #(function(v) local out = {}; local function w(x) if type(x) == "table" then for k, y in pairs(x) do out[#out + 1] = tostring(k); w(y) end else out[#out + 1] = tostring(x) end end; w(v); return table.concat(out) end)(es)
check(sz < 20000, "ext.herds size " .. sz)
check(type(ser) == "string" and ser:find("herds", 1, true), "ext.herds in serialized state")
-- 3. материализация: игрок на стаде первой группы
local h1 = D.herds[1]
-- остальные стада уводим далеко: на реальных регионах соседние стада могут оказаться в near_r от h1, проверяем одно стадо
for i = 2, #D.herds do for _, w in ipairs(D.herds[i].route) do w.x = w.x + 9e6 end end
local day = DAYV
local hx, hz = H.pos(h1.id, day)
setpos(hx, hz)
local n0 = #SPAWNS
local hb0 = (T.stats().by_tag or {}).herd or 0   -- стада у (0,0) могли выйти на игрока ещё в шаге 2 (реальные регионы)
local gl0 = H.stats().glut
for k = 1, 5 do pump(30, 0.00001) end
local got = {}
for i = n0 + 1, #SPAWNS do got[#got + 1] = SPAWNS[i].fid .. "|" .. tostring(SPAWNS[i].sid) end
check(#SPAWNS > n0, "spawned near player: " .. #SPAWNS - n0)
local ng = 0; for tg, n in pairs((KMM_Traces.stats().by_tag) or {}) do if tostring(tg):sub(1, 4) == "herd" then ng = ng + n end end
check(ng <= 3, "<= 3 herd groups at once: " .. ng .. " (spawn calls " .. (#SPAWNS - n0) .. ", incl. Traces own)")
local herd_ok = false
for i = n0 + 1, #SPAWNS do if SPAWNS[i].fid == D.species[h1.species].fid then herd_ok = true end end
check(herd_ok, "herd species squad spawned: " .. table.concat(got, ","))
check(((T.stats().by_tag or {}).herd or 0) - hb0 == 1, "by_tag herd +1: " .. tostring(((T.stats().by_tag or {}).herd or 0) - hb0))
-- кулдаун: ещё раз в тот же день ничего нового от этого же стада
local n1 = #SPAWNS
pump(40, 0.00001)
local again = 0
for i = n1 + 1, #SPAWNS do if SPAWNS[i].fid == D.species[h1.species].fid and (T.stats().by_tag or {}).herd - hb0 > 1 then again = again + 1 end end
check(((T.stats().by_tag or {}).herd or 0) - hb0 == 1, "cooldown: herd still +1: " .. tostring(((T.stats().by_tag or {}).herd or 0) - hb0))
check(#C.state().ext.herds.live <= 3, "live <= 3: " .. #C.state().ext.herds.live)
-- 4. самоотключение: сломанный Traces.request
local oldreq = T.request
T.request = function() error("boom") end
H.reset(); local e2 = C.state().ext.herds; e2.live = {}; e2.gcd = -1e9
for _, st in pairs(e2.h) do st.cd_herd = nil; st.cd_pred = nil; st.cd_hunt = nil end
pump(40, 0.00001)
check(H.disabled(), "self-disable on error")
T.request = oldreq
RESULT = #FAILS == 0 and ("OK " .. N .. " events=" .. (counts.herd_move or 0) .. "/" .. (counts.herd_pred or 0) .. "/" .. (counts.herd_hunt or 0) .. "/" .. (counts.herd_glut or 0) .. " glut=" .. tostring(gl0) .. " stocktowns=" .. nstock .. " size=" .. sz) or ("FAIL: " .. table.concat(FAILS, "; "))
''', "test")
run("")
L.lua_getfield.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_char_p]
L.lua_getfield(st, -10002, b"RESULT")
r = L.lua_tolstring(st, -1, None).decode()
print(r)
sys.exit(0 if r.startswith("OK") else 1)
