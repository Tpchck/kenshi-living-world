"""Offline test R4: запах зоны ядра (KMM_Predators.smell через ZoneSmell:addSmell) и хищники стад через запах с фолбэком (KMM_Herds).
Шина дирижёра deed/attack_on_player -> addSmell (тип, ключ Faction, точка), кулдаун, потолок дня, дальность, снятие (SMELLMSG_NONE),
крэш-сторож, самоотключение при сломанном API; Herds: запах -> ждём -> «took» без спавна / «no effect» -> фолбэк-спавн; без Predators -> фолбэк.
python -I -X utf8 build/KMM_Conductor/_dev/test_r4_smell.py -> OK."""
import ctypes, re, sys, tempfile

DLL = r"C:\Program Files (x86)\Steam\steamapps\workshop\content\233860\3817000612\lua51.dll"
B = r"C:\KenshiModMap\build\KMM_Conductor\scripts\init"
TMP = tempfile.mkdtemp(prefix="kmm_r4_").replace("\\", "/")
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
# свой стаб зоны: ZoneManager:getZoneMap(v).zoneSmell с addSmell/getGeneralSmellLevel
run(r'''
ZS_CALLS, ZS_LVL, ZS_RISE, ZS_FAIL, ZS_LOCK = {}, 0, 0.5, false, false
local zs = {}
function zs:addSmell(t, key, pos)
  if ZS_FAIL then error("bad argument #2 to 'addSmell' (userdata expected)") end
  local f = io.open("TMPDIR/probe_addSmell.lock", "r"); if f then ZS_LOCK = true; f:close() end
  ZS_CALLS[#ZS_CALLS + 1] = { t = t, key = key, x = pos.x, z = pos.z }
  if t ~= 0 then ZS_LVL = ZS_LVL + ZS_RISE end
end
function zs:getGeneralSmellLevel(t) return ZS_LVL end
local zm = { zoneSmell = zs }
local gw0 = getGameWorld
getGameWorld = function() local g = gw0(); g.zoneMgr = { getZoneMap = function(self, v) return zm end }; return g end
'''.replace("TMPDIR", TMP), "zone stub")
run("math.randomseed(20261115)", "seed")
for f in [p.split("\\")[-1] for p in sorted(__import__("glob").glob(B + r"\KMM_Conductor*.lua"))] + ["KMM_Traces.lua", "KMM_Predators.lua", "KMM_Herds.lua"]:
    run(open(B + "\\" + f, encoding="utf-8").read(), f)
run('KMM_Predators.P.sdir = "%s/"' % TMP, "sdir")
run(r'''
N, FAILS = 0, {}
function check(c, what) N = N + 1; if not c then FAILS[#FAILS + 1] = what end end
local C, Pr, H, T = KMM_Conductor, KMM_Predators, KMM_Herds, KMM_Traces
C.reset()
C.advance(10); C.advance(16); DAYV = 16
local P = Pr.P
P.tick_gap = 0; P.daily_chance = 0
local TP = C.cfg().params.traces
TP.first_hour_traces = 0; TP.max_per_day = 1000; TP.max_queue = 1000; TP.arrive_enabled = false; TP.bounty = { enabled = false }
local pf = C.cfg().player_faction
local PX, PZ = 100000, 100000
PCS = {}; CHARS = {}
local ch = MKCH("PC1", pf or "player", PX, PZ, { player = true, platoon = "player_squad" })
PCS[1] = ch; CHARS[1] = ch
local function setpos(x, z) ch.getPosition = function() return { x = x, y = 5, z = z } end end
local function pump(n) for i = 1, n do CLOCK = CLOCK + 10; DAYV = DAYV + 0.00001; FIRE("GameWorld::charsUpdate", {}) end end
local function rd(p) local f = io.open(p, "r"); if not f then return "" end local s = f:read("*a"); f:close(); return s end
pump(1)
check(Pr.sm.sub == true, "шина подписана лениво")
check(rd("TMPDIR/predators.log"):find("smell bus subscribed: 3/3", 1, true), "маркер smell bus subscribed")
-- 1. смерть рядом с игроком -> CORPSE, ключ = Faction проигравшего, точка = место
C.emit({ type = "deed", kind = "killed", tone = "harm", a = "fA", b = "fB", n = 1, x = PX + 50, z = PZ, text = "test killed" })
check(#ZS_CALLS == 1, "addSmell вызван: " .. #ZS_CALLS)
local c1 = ZS_CALLS[1] or {}
check(c1.t == 1 and c1.key == FAC("fB") and c1.x == PX + 50 and c1.z == PZ, "CORPSE, ключ Faction(b), точка")
check(ZS_LOCK and io.open("TMPDIR/probe_addSmell.lock", "r") == nil, "крэш-сторож: lock во время вызова, удалён после")
-- 2. повтор в той же ячейке с тем же ключом -> кулдаун
C.emit({ type = "deed", kind = "executed", tone = "harm", a = "fA", b = "fB", n = 1, x = PX, z = PZ, text = "t" })
check(#ZS_CALLS == 1 and (Pr.sm.st.gap or 0) >= 1, "кулдаун ячейки")
-- 3. нападение на игрока без координат -> BLOOD у игрока, ключ Faction нападавшего
C.emit({ type = "attack_on_player", a = "fC", b = pf, text = "t" })
local c2 = ZS_CALLS[2] or {}
check(#ZS_CALLS == 2 and c2.t == 2 and c2.key == FAC("fC") and c2.x == PX, "BLOOD у игрока: " .. #ZS_CALLS)
-- 4. мелкая стычка (attacked) и далёкое место -> без запаха
C.emit({ type = "deed", kind = "attacked", tone = "harm", a = "fA", b = "fD", n = 1, x = PX, z = PZ, text = "t" })
C.emit({ type = "deed", kind = "killed", tone = "harm", a = "fA", b = "fE", n = 1, x = PX + 50000, z = PZ, text = "t" })
check(#ZS_CALLS == 2 and (Pr.sm.st.far or 0) >= 1, "attacked/далеко -> нет запаха")
local lg = rd("TMPDIR/predators.log")
check(lg:find("smell: corpse deed:killed", 1, true) and lg:find("smell: blood attack_on_player", 1, true), "маркеры smell: в логе")
-- 4b. B2: кровь от нападения на игрока — не ловушка: пауза smell_aop_gap на все фракции, нищий лежащий не приманивает
local n4 = #ZS_CALLS
C.emit({ type = "attack_on_player", a = "fH", b = pf, text = "t" })
check(#ZS_CALLS == n4 and (Pr.sm.st.aop_skip or 0) == 1, "второе нападение в паузе: без запаха")
CLOCK = CLOCK + 1801
local NM0 = rawget(_G, "KMM_Nemesis")
KMM_Nemesis = { poor = function() return true end }
ch.isDown = function() return true end
C.emit({ type = "attack_on_player", a = "fI", b = pf, text = "t" })
check(#ZS_CALLS == n4 and (Pr.sm.st.aop_skip or 0) == 2 and rd("TMPDIR/predators.log"):find("poor and down", 1, true), "нищий лежит: без запаха")
KMM_Nemesis = { poor = function() return false end }
C.emit({ type = "attack_on_player", a = "fI", b = pf, text = "t" })
check(#ZS_CALLS == n4 + 1, "не нищий (лежит, но есть что взять): запах как раньше")
ch.isDown = function() return false end
KMM_Nemesis = NM0
for k in pairs(Pr.sm.src) do if Pr.sm.src[k].why == "attack_on_player" and k:find("fI", 1, true) then Pr.sm.src[k] = nil; table.remove(ZS_CALLS) end end
-- 5. снятие источников через smell_ttl игровых дней
DAYV = DAYV + 0.6; pump(1)
local nn = 0; for _, c in ipairs(ZS_CALLS) do if c.t == 0 then nn = nn + 1 end end
check(nn == 2 and next(Pr.sm.src) == nil, "снятие SMELLMSG_NONE x2: " .. nn)
check(rd("TMPDIR/predators.log"):find("smell retract", 1, true), "маркер smell retract")
-- 6. потолок дня
P.smell_day = 1; Pr.sm.n = 0; Pr.sm.day = -1
C.emit({ type = "deed", kind = "killed", tone = "harm", a = "fA", b = "fF", n = 1, x = PX, z = PZ, text = "t" })
C.emit({ type = "deed", kind = "killed", tone = "harm", a = "fA", b = "fG", n = 1, x = PX, z = PZ, text = "t" })
check((Pr.sm.st.capped or 0) >= 1, "потолок дня")
P.smell_day = 12
-- 7. запах у гнезда с разорёнными караванами (игрок рядом)
local e = Pr.slot()
e.nests["zz|zy"] = { a = "zz", b = "zy", x = PX + 100, z = PZ, fid = "fN", owner = "fO", power = 1, born = math.floor(DAYV), loot = 10, raids = 1, pw = 99 }
local k0 = #ZS_CALLS
pump(1)
local cn = ZS_CALLS[#ZS_CALLS] or {}
check(#ZS_CALLS == k0 + 1 and cn.t == 1 and cn.key == FAC("fN") and (e.stat.smell_nest or 0) == 1, "гнездо пахнет трупами (CORPSE, ключ банды)")
pump(1)
check(#ZS_CALLS == k0 + 1, "гнездо: раз в день")
e.nests["zz|zy"] = nil
-- 8. Herds: хищники следа через запах
H.reset(); H._daily(DAYV)
local D = H.data()
local h1 = D.herds[1]
for i = 2, #D.herds do for _, w in ipairs(D.herds[i].route) do w.x = w.x + 9e6 end end
local hp = D.herds[1].pred and D.species[D.herds[1].pred]
check(hp ~= nil, "у первого стада есть хищник")
local eh = C.state().ext.herds
local function prep() local day = DAYV; local s1 = eh.h[h1.id]; s1.cd_herd = day; s1.cd_hunt = day; s1.cd_pred = nil; eh.live = {}; eh.gcd = -1e9; return day end
local day = prep()
local px, pz = H.pos(h1.id, day - D.P.pred_delay)
setpos(px, pz)
Pr.sm.last = {}; Pr.sm.n = 0
local tp0 = (T.stats().by_tag or {}).herd_pred or 0
k0 = #ZS_CALLS
H._materialize(day)
check(#ZS_CALLS == k0 + 1 and ZS_CALLS[#ZS_CALLS].t == 1 and H.pend()[h1.id], "Herds: запах туши у следа, ожидание")
check(((T.stats().by_tag or {}).herd_pred or 0) == tp0, "Herds: без спавна сразу")
CLOCK = CLOCK + 10; H._materialize(day)
check(H.pend()[h1.id] and #ZS_CALLS == k0 + 1, "Herds: ждём проверки")
CLOCK = CLOCK + 61; H._materialize(day)
check(H.stats().smell_took == 1 and eh.h[h1.id].cd_pred == day and ((T.stats().by_tag or {}).herd_pred or 0) == tp0, "Herds: took -> без спавна, кулдаун")
check(rd("TMPDIR/herds.log"):find("smell took:", 1, true), "маркер smell took")
-- 9. ядро не дало эффекта -> фолбэк-спавн
day = prep(); ZS_RISE = 0; Pr.sm.last = {}
H._materialize(day)
check(H.pend()[h1.id], "Herds: запах снова поставлен")
CLOCK = CLOCK + 61; H._materialize(day)
check(H.stats().smell_fb == 1 and #eh.live >= 1, "Herds: фолбэк-спавн: fb=" .. H.stats().smell_fb)
check(rd("TMPDIR/herds.log"):find("smell fallback spawn: .-no effect"), "маркер smell fallback spawn (no effect)")
-- 10. API запаха сломан -> Predators выключает запах, Herds сразу фолбэк
ZS_FAIL = true; ZS_RISE = 0.5
for i = 1, 3 do Pr.sm.last = {}; C.emit({ type = "deed", kind = "killed", tone = "harm", a = "fA", b = "fX" .. i, n = 1, x = px, z = pz, text = "t" }) end
check(Pr.sm.off == true and (rd("TMPDIR/predators.log"):find("smell disabled until restart", 1, true) or rd("TMPDIR/predators.log"):find("smell failed, retry in", 1, true)), "отказ addSmell: запах выключен (без Gov до перезапуска, с Gov пауза) + маркер")
check(not Pr.disabled(), "модуль Predators жив")
local treq, NREQ = T.request, 0; T.request = function(j) NREQ = NREQ + 1; return true end   -- лимиты Traces тут не проверяем
day = prep(); local fb0 = H.stats().smell_fb
H._materialize(day)
check(H.stats().smell_fb == fb0 + 1 and not H.pend()[h1.id], "Herds: запах off -> фолбэк сразу")
-- 11. без KMM_Predators -> фолбэк (старое поведение)
local keep = KMM_Predators; KMM_Predators = nil
day = prep(); fb0 = H.stats().smell_fb
H._materialize(day)
check(H.stats().smell_fb == fb0 + 1, "Herds: без Predators -> фолбэк")
KMM_Predators = keep; T.request = treq
check(NREQ == 2, "Herds: фолбэк-заявки в Traces: " .. NREQ)
check(not H.disabled(), "Herds не отключён")
RESULT = #FAILS == 0 and ("OK " .. N) or ("FAIL: " .. table.concat(FAILS, "; "))
'''.replace("TMPDIR", TMP), "test")
L.lua_getfield.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_char_p]
L.lua_getfield(st, -10002, b"RESULT")
r = L.lua_tolstring(st, -1, None).decode()
print(r)
sys.exit(0 if r.startswith("OK") else 1)
