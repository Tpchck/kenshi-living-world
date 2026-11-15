"""Offline test U1 (KMM_Traces): отряды Traces — родные отряды движка. Ванильный AI_PACKAGE под вид (Blackboard:replaceAIPackage),
постоянный отряд только для каравана с грузом / беженцев по плану (лимит nat_persist_max), отпуск по сроку, сироты, фолбэк на прежнее
(нет blackboard/ключа/isPersistentSquad -> временный отряд и свой деспавн), заявка T.request с пакетом по тегу до on_spawn.
python -I -X utf8 build/KMM_Conductor/_dev/test_u1_native.py -> OK."""
import ctypes
import re
import sys
import tempfile

DLL = r"C:\Program Files (x86)\Steam\steamapps\workshop\content\233860\3817000612\lua51.dll"
B = r"C:\KenshiModMap\build\KMM_Conductor\scripts\init"
TMP = tempfile.mkdtemp(prefix="kmm_u1_").replace("\\", "/")
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
stubs = re.search(r"STUBS = r'''(.*?)'''", rt, re.S).group(1).replace("TMPDIR", TMP)
run(stubs, "stubs")
run("math.randomseed(20261115)", "seed")
for _f in sorted(__import__("glob").glob(B + r"\KMM_Conductor*.lua")):
    run(open(_f, encoding="utf-8").read(), _f.split("\\")[-1])
run(open(B + r"\KMM_Traces.lua", encoding="utf-8").read(), "KMM_Traces.lua")
run(r'''
TMPD = "''' + TMP + r'''"
N, FAILS = 0, {}
local function MAIN()
function check(c, what) N = N + 1; if not c then FAILS[#FAILS + 1] = what; print("FAIL " .. what) end end
function ticks(n) for i = 1, n do CLOCK = CLOCK + 1; DAYV = DAYV + 0.0005; FIRE("GameWorld::charsUpdate", {}) end end
local function pump(n) for _ = 1, n do CLOCK = CLOCK + 100; ticks(2) end end
local C = KMM_Conductor
local function skeys(t) local k = {}; for x in pairs(t) do k[#k + 1] = x end; table.sort(k); return k end
C.reset()
local CF = C.cfg().params
CF.guard.debug_log = TMPD .. "/debug.log"
local TP = CF.traces
TP.first_hour_traces = 0; TP.arrive_enabled = false; TP.max_per_day = 1000; TP.max_queue = 1000; TP.wx_enabled = false
if CF.roads then CF.roads.ambient = false; CF.roads.scouts = false; CF.roads.max_live = 1000 end
local function dbg() local f = io.open(TMPD .. "/debug.log", "r"); if not f then return "" end; local s = f:read("*a"); f:close(); return s end
local function cnt(s, pat) local n = 0; for _ in s:gmatch(pat) do n = n + 1 end; return n end

-- движок: богатый платун (blackboard с пакетом, постоянный флаг), списки платунов фракции
local tr = C.read_json("traces.json", "C:/KenshiModMap/build/KMM_Conductor/traces.json")
SP, SPC, UNL = {}, {}, {}
BB_FAIL, KEYFAIL, PERSIST_LIE, PLAIN = false, false, false, false
local function rich(key)
  local p = PLATOON(key)
  p.bb = { name = "template" }
  function p.bb:replaceAIPackage(gd) if BB_FAIL then error("engine refused package") end; self.pkg = gd.stringID; self.pkt = gd.t; self.name = "pkg " .. gd.stringID end
  function p.bb:getCurrentAIPackageName() return self.name end
  function p:getBlackboard() return p.bb end
  p.persist, p.nset = false, 0
  function p:setPersistentSquad(v) p.persist = v; p.nset = p.nset + 1 end
  function p:isPersistentSquad() if PERSIST_LIE then return false end; return p.persist end
  if KEYFAIL then function p:getPlatoonStringID() return "" end end
  return p
end
local gw0 = getGameWorld
function getGameWorld()
  local g = gw0(); local orig = g.theFactory.createRandomSquad
  g.theFactory.createRandomSquad = function(self, f, pos, home, maxnum, b, gd, o, m, ap, perm, target, ttown, mult, sqt, rf)
    orig(self, f, pos, home, maxnum, b, gd, o, m, ap, perm, target, ttown, mult, sqt, rf)
    local n = #SPAWNS
    if PLAIN then return { spawned = true } end   -- прежняя заглушка: ни blackboard, ни ключа
    local pl = rich("u" .. n)
    SP[n] = { pl = pl, perm = perm, ttown = ttown, target = target, fid = f.id }
    local ch = MKCH("um" .. n, f.id, pos.x, pos.z, { platoon = "u" .. n })
    CHARS[#CHARS + 1] = ch; SPC[n] = ch
    return pl
  end
  return g
end

-- город, фракция с тирами/беженцами/живым караваном и враг
local T, TX, TZ, F, E
for _, sid in ipairs(skeys(C.cfg().town_info)) do
  local I = C.cfg().town_info[sid]
  for _, fid in ipairs(skeys(C.state().F)) do
    local f = C.state().F[fid]
    if not T and f.alive and not f.player and f.towns[sid] and I.x and tr.live_caravans[fid] and tr.factions[fid] and tr.factions[fid].refugees
       and next(tr.factions[fid].tiers or {}) then T, TX, TZ, F = sid, I.x, I.z, fid end
  end
end
for _, fid in ipairs(skeys(C.state().F)) do local f = C.state().F[fid]; if not E and f.alive and not f.player and fid ~= F then E = fid end end
check(T and F and E, "найдены город, фракция и враг")
local function plist(loaded) local o = {}; for _, k in ipairs(skeys(PLATOONS)) do local p = PLATOONS[k]; if p.persist and (p.loaded or false) == loaded then o[#o + 1] = p end end; return o end
for _, id in ipairs({ F, E }) do local fo = FAC(id); fo.getActivePlatoons = function() return plist(true) end; fo.getUnloadedPlatoons = function() return plist(false) end end
PCS = { MKCH("Nameless", C.cfg().player_faction or "player", TX + 2500, TZ, { player = true, platoon = "player_squad" }) }
CHARS = { PCS[1] }
ticks(5)
local NT = KMM_Traces
local function nat() local n, L = NT.native(); return n, L end

-- 1) колонна на врага: пакет «travel to target town», цель-город фабрики; не постоянная
local s0 = #SPAWNS
NT._enqueue({ kind = "column", fid = F, enemy = E, ev = 1, tx = TX, tz = TZ, why = "raid" })
pump(3)
check(#SPAWNS >= s0 + 2, "колонна заспавнена (" .. (#SPAWNS - s0) .. ")")
local c1 = SP[s0 + 1]
check(c1 and c1.pl.bb.pkg == "14545-gamedata.base" and c1.pl.bb.pkt == 72, "колонна: ванильный AI_PACKAGE travel to target town (тип 72)")
check(c1 and c1.ttown ~= nil and c1.perm == false, "колонна: цель-город у фабрики, временный отряд")
check(c1 and c1.pl.nset == 0, "колонна не делается постоянной")
local n1 = nat()
check(n1.pkg >= 2 and n1.persist == 0, "счётчик пакетов (" .. n1.pkg .. ")")
check(dbg():find("native column " .. F .. ": pkg ok 14545-gamedata.base (current pkg 14545-gamedata.base)", 1, true), "маркер native column в debug.log")

-- 2) караван по плану дорог: пакет шаблона сохраняется, отряд постоянный, ключ в реестре сейва
local rp0, rd0, ra0 = C.road_plan, C.road_depart, C.road_arrive
local ARRIVED = {}
C.road_plan = function(kind, fid, opt) if kind == "caravan" or (kind == "courier" and COURIER_ON) then return { fid = F, from = T, to = T, id = nil } end; return rp0(kind, fid, opt) end
C.road_depart = function(plan) return "rid" .. #SPAWNS end
C.road_arrive = function(id, how) ARRIVED[#ARRIVED + 1] = id end
local s1 = #SPAWNS
NT._enqueue({ kind = "trader", why = "ambient", ev = 0 })
pump(2)
local k1 = SP[s1 + 1]
check(k1 and k1.pl.bb.pkg == nil, "караван: свой ванильный пакет торговца не заменён")
check(k1 and k1.pl.persist == true, "караван: постоянный отряд ядра")
local _, L1 = nat()
check(#L1 == 1 and L1[1].k == "u" .. (s1 + 1) and L1[1].f == F and L1[1].kind == "caravan", "реестр: ключ платуна, фракция, вид")
check(C.state().ext.traces_nat.L == L1, "реестр живёт в состоянии дирижёра (сейв)")
local tv; for _, t in ipairs(NT.travelers()) do if t.key == "u" .. (s1 + 1) then tv = t end end
check(tv and tv.nat == true, "путник помечен: ведёт ядро")
check(dbg():find("native caravan " .. F .. ": persistent ok key u" .. (s1 + 1) .. " (1/4)", 1, true), "маркер persistent ok")

-- 3) прибытие ведомого ядром: зачёт без своего деспавна
if tv then
  local pos = SPC[s1 + 1]:getPosition(); tv.tx, tv.tz = pos.x, pos.z
  pump(2)
  check(not SPC[s1 + 1]:isDead(), "прибыл: не убит нашим деспавном (ведёт ядро)")
  check(#ARRIVED >= 1, "прибыл: числа зачтены в дирижёре")
  check(nat().arrive >= 1, "счётчик arrive")
end

-- 4) лимит постоянных: persist_max
TP.nat_persist_max = 2
NT._enqueue({ kind = "trader", why = "ambient", ev = 0 }); pump(2)
NT._enqueue({ kind = "trader", why = "ambient", ev = 0 }); pump(2)
local _, L2 = nat()
check(#L2 == 2, "лимит постоянных соблюдён (" .. #L2 .. ")")
check(SP[#SPAWNS].pl.persist == false and dbg():find("persistent FAIL cap 2 - temporary squad as before", 1, true), "сверх лимита: временный отряд + маркер")
local tl; for _, t in ipairs(NT.travelers()) do if t.key == "u" .. #SPAWNS then tl = t end end
check(tl and not tl.nat, "сверх лимита: путник на прежнем деспавне")
TP.nat_persist_max = 10

-- 5) ключ не прочитан -> не постоянный (setPersistentSquad не звали); isPersistentSquad ложь -> флаг снят
KEYFAIL = true
NT._enqueue({ kind = "trader", why = "ambient", ev = 0 }); pump(2)
KEYFAIL = false
check(SP[#SPAWNS].pl.nset == 0 and dbg():find("persistent FAIL no platoon key", 1, true), "нет ключа: отряд не делается постоянным")
PERSIST_LIE = true
NT._enqueue({ kind = "trader", why = "ambient", ev = 0 }); pump(2)
PERSIST_LIE = false
local pl5 = SP[#SPAWNS].pl
check(pl5.persist == false and pl5.nset == 2 and dbg():find("persistent FAIL isPersistentSquad false", 1, true), "isPersistentSquad ложь: полупостоянный снят")
local _, L5 = nat(); check(#L5 == 2, "реестр не пополнился сбоями (" .. #L5 .. ")")
C.road_plan, C.road_depart, C.road_arrive = rp0, rd0, ra0

-- 5b) H4: временный отряд под пакетом ядра после прибытия вне видимости убирается, как раньше (не копится у игрока)
local s5 = #SPAWNS
COURIER_ON = true
NT._enqueue({ kind = "courier", fid = F, why = "tribute", ev = 0 }); pump(2)
COURIER_ON = false
local cc = SP[s5 + 1]
check(cc and cc.pl.bb.pkg == "14545-gamedata.base" and cc.pl.persist == false, "гонец: пакет ядра, временный")
local tc; for _, t in ipairs(NT.travelers()) do if t.key == "u" .. (s5 + 1) then tc = t end end
if tc then
  local pos = SPC[s5 + 1]:getPosition(); tc.tx, tc.tz = pos.x, pos.z
  local na = NT.stats().arrived or 0
  pump(2)
  check(SPC[s5 + 1]:isDead() and (NT.stats().arrived or 0) > na, "временный под пакетом: прибыл вне видимости -> тихий деспавн + зачёт")
else check(false, "гонец числится путником") end

-- 6) фолбэк: движок отверг пакет / нет blackboard -> прежнее поведение, маркер FAIL
BB_FAIL = true
local s6 = #SPAWNS
NT._enqueue({ kind = "garrison", fid = F, ev = 2, tx = TX, tz = TZ, why = "revolt" }); pump(2)
BB_FAIL = false
check(#SPAWNS > s6 and SP[s6 + 1].pl.bb.pkg == nil and dbg():find("native garrison " .. F .. ": pkg FAIL 14545-gamedata.base: replaceAIPackage failed - template package as before", 1, true), "пакет отвергнут: маркер FAIL, пакет шаблона")
PLAIN = true
local f0 = nat().pkg_fail
NT._enqueue({ kind = "column", fid = F, enemy = E, ev = 3, tx = TX, tz = TZ, why = "raid" }); pump(2)
PLAIN = false
check(nat().pkg_fail >= f0 + 2 and dbg():find("pkg FAIL 14545-gamedata.base: no blackboard", 1, true), "прежняя заглушка без blackboard: FAIL, спавн не сломан")
check(next(NT.disabled()) == nil, "ни одна функция Traces не выключилась")

-- 7) рейд на базу и охотники: пакет «Assault target squad» с целью-персонажем игрока
local s7 = #SPAWNS
C.state().base = nil
NT._enqueue({ kind = "base_raid", fid = E, enemy = "player", ev = 4, tx = TX, tz = TZ, why = "base_raid", day = 0 }); pump(3)
local b7 = SP[s7 + 1]
check(b7 and b7.pl.bb.pkg == "2957-gamedata.base" and b7.target ~= nil, "рейд на базу: Assault target squad, AItarget = игрок")

-- 8) заявка T.request: пакет по тегу ставится до on_spawn (заказчик может поставить свой поверх)
local seen
local okr = NT.request({ tag = "siege_besiegers", fid = F, shift = 0, n = 1, size = 3, to_fid = E, to_x = TX, to_z = TZ,
                         on_spawn = function(pls) seen = pls[1] and pls[1].bb and pls[1].bb.pkg end })
pump(3)
check(okr and seen == "14545-gamedata.base", "T.request siege_besiegers: travel to target town до on_spawn (" .. tostring(seen) .. ")")
local seen2
NT.request({ tag = "veteran", fid = F, shift = 0, n = 1, size = 2, to_fid = F, to_x = TX, to_z = TZ, on_spawn = function(pls) seen2 = pls[1] and pls[1].bb and (pls[1].bb.pkg or "none") end })
pump(3)
check(seen2 == "none", "T.request без пакета по тегу: пакет шаблона (" .. tostring(seen2) .. ")")

-- 8b) живые временные под пакетом ядра у игрока считаются по снимку: при nat_live_max новых некритичных спавнов нет
pump(1)
local _, _, _, alive = NT.native()
check((alive or 0) >= 2, "живые временные под пакетом у игрока посчитаны (" .. tostring(alive) .. ")")
TP.nat_live_max = alive
local s8 = #SPAWNS
NT._enqueue({ kind = "column", fid = F, enemy = E, ev = 9, tx = TX, tz = TZ, why = "raid" }); pump(3)
check(#SPAWNS == s8, "лимит живых: колонна ждёт в очереди")
TP.nat_live_max = 100; pump(3)
check(#SPAWNS > s8, "лимит снят: колонна вышла")

-- 9) реестр: до срока держит; срок вышел — отпуск только загруженного; погиб/исчез — место сразу; сирота — только без списков фракции
local _, L9 = nat()
check(#L9 == 2, "в реестре 2 постоянных (" .. #L9 .. ")")
local x1, x2 = L9[1], L9[2]
local p1, p2 = PLATOONS[x1.k], PLATOONS[x2.k]
NT._native_step(); NT._native_step()
check(#L9 == 2 and p1.persist and p2.persist, "до срока не отпускаются (выгружены, живы)")
local S = C.state(); S.last_day = (S.last_day or 0) + 4
NT._native_step()
check(p1.persist == true and #L9 == 2 and L9[2].k == x1.k and L9[2].due and dbg():find("native release caravan key " .. x1.k .. " deferred", 1, true), "срок вышел, но выгружен: не отпускается, ждёт подгрузки")
p1.loaded = true
NT._native_step(); NT._native_step()
check(p1.persist == false and #L9 == 1 and dbg():find("native release caravan key " .. x1.k .. " after", 1, true), "подгрузился: отпущен (снова временный)")
p2.isDead = true
NT._native_step()
check(#L9 == 0 and dbg():find("squad is dead - slot freed", 1, true), "погиб: место в лимите сразу свободно")
local R = C.state().ext.traces_nat
R.L[1] = { k = "ghost1", f = F, kind = "caravan", d = S.last_day }
local fe = FAC(E); fe.getActivePlatoons = function() error("no lists") end; fe.getUnloadedPlatoons = function() error("no lists") end
R.L[2] = { k = "ghost2", f = E, kind = "refugees", d = S.last_day }
for _ = 1, 6 do NT._native_step() end
check(#R.L == 1 and R.L[1].k == "ghost2" and dbg():find("native lost caravan key ghost1", 1, true), "фракция есть, ключа нет 3 раза: место сразу свободно")
S.last_day = S.last_day + 40
NT._native_step()
check(#R.L == 0 and dbg():find("native orphan dropped refugees key ghost2", 1, true), "списки фракции недоступны: сирота до orph_days")
NT._native_step(); check(true, "пустой реестр: шаг без ошибки")

-- 10) смена мира: реестр — в новом состоянии, старые ключи не тянутся
C.reset()
local _, L10 = nat()
check(#L10 == 0, "новое состояние дирижёра: реестр пуст")
check(next(NT.disabled()) == nil, "Traces жив после всех сценариев")
local log = dbg()
check(cnt(log, "native ") >= 10, "маркеры native в debug.log (" .. cnt(log, "native ") .. ")")
print(N .. " checks, fails: " .. #FAILS)
for _, f in ipairs(FAILS) do print("FAIL " .. f) end
if #FAILS > 0 then error("FAILS " .. #FAILS) end
end
local okm, em = xpcall(MAIN, debug.traceback)
if not okm then error(em, 0) end
''', "test")
print("OK")
