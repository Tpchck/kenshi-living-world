"""Офлайн-тест ROBBERY: waylay (мотив/отношения/договор), сбыт добычи (союзный/нейтральный город, незаконное), рантайм KMM_Traces (лут, экипировка, лимиты).
python -I -X utf8 build/KMM_Conductor/_dev/test_robbery.py -> OK, код 1 при провале."""
import ctypes
import os
import re
import sys
import tempfile

DLL = r"C:\Program Files (x86)\Steam\steamapps\workshop\content\233860\3817000612\lua51.dll"
B = r"C:\KenshiModMap\build\KMM_Conductor\scripts\init"
TMP = tempfile.mkdtemp(prefix="kmm_rob_").replace("\\", "/")
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
for _f in sorted(__import__("glob").glob(B + r"\KMM_Conductor*.lua")): run(open(_f, encoding="utf-8").read(), _f.split("\\")[-1])
run(open(B + r"\KMM_Traces.lua", encoding="utf-8").read(), "KMM_Traces.lua")
run(r'''
N, FAILS = 0, {}
function check(c, what) N = N + 1; if not c then FAILS[#FAILS + 1] = what end end
function ticks(n) for i = 1, n do CLOCK = CLOCK + 1; DAYV = DAYV + 0.001; FIRE("GameWorld::charsUpdate", {}) end end
local C = KMM_Conductor
C.reset()
local S = C.state()
local P = C.cfg().params
P.robbery = P.robbery or {}; P.robbery.drug_pull = 0; P.robbery.thief_pull = 0; P.robbery.gear_pull = 0   -- тест выбирает категорию детерминированно
math.random = function(n) if n then return 1 end; return 0.01 end   -- детерминизм: засада всегда удаётся
local function evcount(ty) local n = 0; for _, e in ipairs(C.state().events) do if e.type == ty then n = n + 1 end end; return n end
local A, B, Cc, D
local ids = {}
for k in pairs(S.F) do ids[#ids + 1] = k end
table.sort(ids)
for _, fid in ipairs(ids) do
  local f = S.F[fid]
  local nt = 0; for _ in pairs(f.towns) do nt = nt + 1 end
  if f.alive and not f.player and not f.relic and nt > 0 then
    if not A then A = fid elseif not B then B = fid elseif not Cc then Cc = fid elseif not D then D = fid end
  end
end
check(A and B and Cc and D, "четыре фракции с городами")
local function setrel(a, b, v) S.rel[a] = S.rel[a] or {}; S.rel[b] = S.rel[b] or {}; S.rel[a][b] = v; S.rel[b][a] = v end
local function stock_for(fid, q)
  S.stock.towns = S.stock.towns or {}
  for t in pairs(S.F[fid].towns) do
    local s = { owner = fid, q = {}, tn = {}, lv = {}, city = true, siege = -1 }
    for _, c in ipairs({ "food", "metal", "weapons", "armor", "med", "drugs", "lux", "scrap" }) do s.q[c] = q; s.tn[c] = 100; s.lv[c] = q / 100 end
    S.stock.towns[t] = s
  end
end
S.stock.towns = {}
stock_for(B, 150)
S.last_day = 100
S.F[A].wealth = 1; S.F[A].wealth0 = 500   -- нужда: бедность
-- 1) мотив только при низких отношениях и без договора
setrel(A, B, 0)
check(C.waylay_ok(A, B) == false, "rel=0: засады нет")
setrel(A, B, -30)
check(C.waylay_ok(A, B) == true, "rel=-30, нужда, нет договора: засада возможна")
S.treaties[900] = { active = true, type = "nonaggression", a = A, b = B, term = 99999 }
check(C.waylay_ok(A, B) == false, "договор ненападения: засады нет")
S.treaties[900].active = false
S.treaties[901] = { active = true, type = "defense", a = B, b = A, term = 99999 }
check(C.waylay_ok(A, B) == false, "союзный договор: засады нет")
S.treaties[901].active = false
S.F[A].wealth = S.F[A].wealth0 * 2; S.F[A].ambition = "survival"; S.F[A].food_def = 0; S.F[A].metal_def = 0
check(C.waylay_ok(A, B) == false, "нет мотива (богата, не жадная, нет обиды): засады нет")
S.F[A].wronged = { [B] = S.last_day - 5 }
check(C.waylay_ok(A, B) == true, "месть за недавнее: засада возможна")
S.F[A].wealth = 1; S.F[A].wronged = nil
-- 2) эффект
local r0 = C.rel(A, B)
C._waylay(A, B)
check(evcount("waylay") == 1, "waylay: одно событие")
local ev; for _, e in ipairs(S.events) do if e.type == "waylay" then ev = e end end
check(ev and ev.a == A and ev.b == B and ev.cat and ev.n and ev.n >= 1 and ev.town_sid, "поля waylay: a b town_sid cat n")
check(C.rel(A, B) < r0, "отношения упали")
local lt = C.loot_of(A)
check(#lt == 1 and lt[1].c == ev.cat and lt[1].b == B and lt[1].n == ev.n, "добыча записана")
check(S.stock.towns[ev.town_sid].q[ev.cat] < 150, "склад источника уменьшился")
check(not C.waylay_ok(A, B), "кулдаун после засады")
-- 3) сбыт: город союзного/нейтрального владельца, не враждебного
local wA = S.F[A].wealth
for t in pairs(S.F[A].towns) do S.stock.towns[t] = nil end
stock_for(Cc, 20); stock_for(D, 20)
setrel(A, Cc, 40); setrel(A, D, -50)
S.last_day = S.last_day + 20
local before = {}; for t, s in pairs(S.stock.towns) do before[t] = s.q[ev.cat] end
C._loot_step()
local sold; for _, e in ipairs(S.events) do if e.type == "loot_sold" then sold = e end end
check(sold ~= nil, "loot_sold эмитирован")
check(sold and sold.a == A and sold.town_sid and sold.town_name and sold.cat == ev.cat and sold.n >= 1 and sold.b == B, "поля loot_sold: a b town_sid town_name cat n")
check(sold and S.F[Cc].towns[sold.town_sid] ~= nil, "продано в городе союзника, а не врага")
check(sold and before[sold.town_sid] and S.stock.towns[sold.town_sid].q[ev.cat] > before[sold.town_sid], "склад города вырос")
check(S.F[A].wealth > wA, "богатство грабителя выросло")
check(#C.loot_of(A) == 0, "добыча израсходована")
-- нейтральный (rel 0..19)
setrel(A, Cc, 5); C.loot_add(A, "food", 10, B); S.last_day = S.last_day + 20
for t in pairs(S.F[D].towns) do S.stock.towns[t] = nil end
C._loot_step()
check(S.stats.loot_sold_neutral == 1, "сбыт в нейтральном городе засчитан")
-- 4) все враждебны -> ждём, потом тает
setrel(A, Cc, -50)
C.loot_add(A, "food", 10, B); S.last_day = S.last_day + 20
local e0 = evcount("loot_sold"); C._loot_step()
check(evcount("loot_sold") == e0 and #C.loot_of(A) == 1, "врагу не продаём, ждём")
S.last_day = S.last_day + 200; C._loot_step()
check(#C.loot_of(A) == 0 and (S.stats.loot_melted or 0) >= 1, "добыча растаяла")
-- 5) незаконное: Святая Нация не берёт наркотики
local HN
for _, fid in ipairs(ids) do if C.name(fid):find("Holy Nation") and next(S.F[fid].towns) then HN = fid end end
if HN and HN ~= A then
  S.stock.towns = {}; stock_for(HN, 20); setrel(A, HN, 30)
  C.loot_add(A, "drugs", 10, B); S.last_day = S.last_day + 20
  e0 = evcount("loot_sold"); C._loot_step()
  check(evcount("loot_sold") == e0, "незаконное (drugs) в городе Святой Нации не продаётся")
  C.loot_add(A, "food", 10, B); S.last_day = S.last_day + 20; C._loot_step()
  check(evcount("loot_sold") == e0 + 1, "законное там же продаётся")
else check(false, "нет Holy Nation в конфиге") end
-- 6) API: мусор отвергается
check(C.loot_add("nonexistent", "food", 5, B) == false and C.loot_add(A, "bogus", 5, B) == false and C.loot_add(A, "food", -1, B) == false, "loot_add: мусор отвергается")
-- 7) смягчение gear_shift
S.stock.towns = {}; stock_for(B, 150)
S.F[A].gear_shift = -1; S.F[A].gear_loot = 0
local g0 = S.stats.gear_loot or 0
for i = 1, 8 do
  S.F[A].last_waylay = nil; S.F[A].way_pair = nil
  for t in pairs(S.F[B].towns) do
    for _, c in ipairs({ "food", "metal", "weapons", "med", "lux", "drugs" }) do S.stock.towns[t].q[c] = 0; S.stock.towns[t].lv[c] = 0 end
    S.stock.towns[t].q.armor = 400; S.stock.towns[t].lv.armor = 4
  end
  C._waylay(A, B)
end
check((S.stats.gear_loot or 0) > g0 and (S.F[A].gear_shift or 0) == 0, "броня из добычи смягчила gear_shift до 0 (" .. tostring(S.stats.gear_loot) .. ")")
check((S.F[A].gear_grace or 0) > S.last_day, "grace против немедленного отката")

---------------------------------------------------------------- РАНТАЙМ
local PF = C.cfg().player_faction or "player"
DAYV = math.max(DAYV, S.last_day + 10)   -- время мира не идёт назад (иначе дирижёр сбросит состояние)
S = C.state()
function ITEM(sid, ty, opt)
  opt = opt or {}
  local it = { quantity = opt.q or 1, isEquipped = opt.eq or false, val = opt.val or 10 }
  it.getGameData = function() return { stringID = sid, type = ty or 4 } end
  it.getValueSingle = function(self, isPlayer) return it.val end   -- как в игре: у Item нет getValue
  return it
end
function MKL(nm, fid, x, z, platoon, items, opt)
  opt = opt or {}
  local c = MKCH(nm, fid, x, z, { platoon = platoon, down = opt.down })
  local inv = { getAllItems = function() return items end, addItem = function() end,
                equipItem = function(self, it)
                  for _, o in ipairs(items) do if o.isEquipped and o.grp == it.grp then o.isEquipped = false end end
                  it.isEquipped = true; return true
                end }
  c.getInventory = function() return inv end
  c.getRace = function() return { name = opt.race or "Greenlander" } end
  c.inv = inv
  return c
end
local FA, FB = ids[1], ids[2]
PCS = { MKCH("Nameless", PF, 0, 0, { player = true, platoon = "player_squad" }) }
CHARS = { PCS[1] }
ticks(8)
-- а) драка вдали от игрока: отряд FA, рядом лежит чужой (FB)
local loot_items = { ITEM("food_a", 4) }
local m1 = MKL("raider1", FA, 3000, 0, "raiders", loot_items)
local victim = MKL("victim1", FB, 3200, 0, "vic", {}, { down = true })
CHARS = { PCS[1], m1, victim }
ticks(8)
check(next((KMM_Traces.loot_state())) ~= nil, "отряд в драке отслеживается")
ticks(8)
check(evcount("loot_carried") == 0, "пока отряд рядом — события нет")
table.insert(loot_items, ITEM("lux_a", 4, { val = 900 })); table.insert(loot_items, ITEM("junk_a", 4, { val = 5 })); table.insert(loot_items, ITEM("junk_b", 4, { val = 5 }))
ticks(8)
CHARS = { PCS[1], victim }   -- отряд ушёл из радиуса
ticks(14)
check(evcount("loot_carried") == 1, "loot_carried один раз (" .. evcount("loot_carried") .. ")")
local lc; for _, e in ipairs(C.state().events) do if e.type == "loot_carried" then lc = e end end
check(lc and lc.a == FA and lc.b == FB and lc.n == 3, "поля loot_carried: a b n=3 (" .. tostring(lc and lc.n) .. ")")
local tot, haslux = 0, false
for _, e in ipairs(C.loot_of(FA)) do tot = tot + e.n; if e.c == "lux" then haslux = true end; check(e.b == FB, "жертва в добыче") end
check(tot == 3 and haslux, "добыча по категориям: lux + scrap (" .. tot .. ")")
ticks(30)
check(evcount("loot_carried") == 1, "повторно не эмитируется")
-- б) драка у игрока — не наше дело
local m2 = MKL("raider2", FA, 500, 0, "raiders2", { ITEM("x", 4) })
local v2 = MKL("victim2", FB, 700, 0, "vic2", {}, { down = true })
CHARS = { PCS[1], m2, v2 }
ticks(10)
check(KMM_Traces.loot_state().raiders2 == nil, "драка рядом с игроком не отслеживается")
-- в) лимит 12 отрядов
CHARS = { PCS[1] }
for i = 1, 15 do CHARS[#CHARS + 1] = MKL("r" .. i, FA, 3000 + i * 10, 500, "sq" .. i, { ITEM("a" .. i, 4) }) end
CHARS[#CHARS + 1] = MKL("vv", FB, 3000, 500, "vvp", {}, { down = true })
ticks(8)
local n = 0; for _ in pairs((KMM_Traces.loot_state())) do n = n + 1 end
check(n <= 12 and n >= 1, "не более 12 отслеживаемых (" .. n .. ")")

---------------------------------------------------------------- ЭКИПИРОВКА
local lo_sid, hi_sid, wh_sid, wl_sid = "39-cats civilian cloth overhual.mod", "438-Expanded Vanilla Armor.mod", "146-astramilitarumkit.mod", "10-Lolu_Whistler Suit.mod"
local function body(sid, g) local it = ITEM(sid, 3); it.grp = g or "armour:body"; return it end
local function fresh() local worn = body(lo_sid); worn.isEquipped = true; return worn, body(hi_sid) end
local worn, new = fresh()
local ch = MKL("eq1", FA, 3000, 0, "eqp", { worn, new })
local ok, ncat, ocat = KMM_Traces._equip(ch, ch.inv, 1000, "heq1")
check(ok == true and new.isEquipped and not worn.isEquipped, "лучшая броня надета, старая снята")
check(ncat == "armor" and ocat == "armor", "категории переодевания armor/armor")
worn, new = fresh(); ch = MKL("eq1", FA, 3000, 0, "eqp", { worn, new })
check(KMM_Traces._equip(ch, ch.inv, 1030, "heq1") == false and not new.isEquipped, "<=1 переодевание на NPC в 60 с")
check(KMM_Traces._equip(ch, ch.inv, 1100, "heq1") == true, "через 60 с можно снова")
local w2 = body(hi_sid); w2.isEquipped = true; local n2 = body(lo_sid)
local ch2 = MKL("eq2", FA, 3000, 0, "eqp2", { w2, n2 })
check(KMM_Traces._equip(ch2, ch2.inv, 2000, "heq2") == false and w2.isEquipped and not n2.isEquipped, "худшая броня не надевается")
local w3 = body(wh_sid); w3.isEquipped = true; local n3 = body(hi_sid)
local ch3 = MKL("eq3", FA, 3000, 0, "eqp3", { w3, n3 })
check(KMM_Traces._equip(ch3, ch3.inv, 3000, "heq3") == false, "WH-персонаж не переодевается")
local w4 = body(lo_sid); w4.isEquipped = true; local n4 = body(wl_sid, "armour:shirt")
local ch4 = MKL("eq4", FA, 3000, 0, "eqp4", { w4, n4 })
check(KMM_Traces._equip(ch4, ch4.inv, 4000, "heq4") == false and not n4.isEquipped, "Whistler Suit не надевается не-Whistler")
local w5 = body(lo_sid); w5.isEquipped = true; local n5 = body(wl_sid, "armour:shirt")
local ch5 = MKL("eq5", FA, 3000, 0, "eqp5", { w5, n5 }, { race = "Whistler" })
check(KMM_Traces._equip(ch5, ch5.inv, 5000, "heq5") == true, "Whistler Suit надевает Whistler")
-- <=2 переодеваний за проход (четыре бойца одного отряда получили броню)
local grp = {}
CHARS = { PCS[1] }
for i = 1, 4 do
  local items = { ITEM("base" .. i, 4) }
  local c = MKL("g" .. i, FA, 3000 + i * 5, 800, "gsq", items)
  c.items = items; grp[#grp + 1] = c; CHARS[#CHARS + 1] = c
end
CHARS[#CHARS + 1] = MKL("vg", FB, 3000, 800, "vgp", {}, { down = true })
CLOCK = CLOCK + 100
ticks(7)
local eq0 = select(2, KMM_Traces.loot_state()).equipped
for _, c in ipairs(grp) do
  local w = body(lo_sid); w.isEquipped = true
  table.insert(c.items, w); table.insert(c.items, body(hi_sid))
end
CLOCK = CLOCK + 100
ticks(7)
local eqd = select(2, KMM_Traces.loot_state()).equipped - eq0
check(eqd >= 1 and eqd <= 2, "не более 2 переодеваний за проход (" .. eqd .. ")")

---------------------------------------------------------------- ЗАЩИТА
check(KMM_Traces.disabled().loot_scan == nil and KMM_Traces.disabled().loot_equip == nil, "до сбоя ничего не отключено")
local old_gw = getGameWorld
getGameWorld = function()
  local g = old_gw()
  g.getCharacterUpdateList = function() error("boom") end
  return g
end
CLOCK = CLOCK + 100
ticks(8)
getGameWorld = old_gw
local d = KMM_Traces.disabled()
check(d.loot_scan == true, "сбой API отключил loot_scan")
check(d.tick == nil and d.spawn == nil and d.events == nil and d.loot_equip == nil, "остальные функции Traces живы")
-- killer в caravan_lost -> wronged жертвы (мотив мести)
do
  local S2 = C.state()
  S2.F[B].wronged = nil
  C.emit({ type = "caravan_lost", a = B, killer = A, by = "other" })
  check(S2.F[B].wronged and S2.F[B].wronged[A], "caravan_lost с killer: жертва помнит обидчика (wronged)")
  S2.F[A].wronged = nil
  C.emit({ type = "caravan_lost", a = B, by = "other" })
  check(not S2.F[A].wronged and not S2.F[B].wronged[B], "caravan_lost без killer: wronged не меняется")
  C.emit({ type = "caravan_lost", a = B, killer = B, by = "other" })
  check(not S2.F[B].wronged[B], "killer == жертва игнорируется")
end
print(N .. " checks, fails: " .. #FAILS)
for _, f in ipairs(FAILS) do print("FAIL " .. f) end
if #FAILS > 0 then error("FAILS " .. #FAILS) end
''', "tests")
print("OK")
