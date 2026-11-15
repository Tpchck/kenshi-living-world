"""Offline test B1 (KMM_Outlaws): награда за голову глубже — через награду ядра (BountyManager).
Колбэк notifyCrimeWitnessed -> очередь -> доплата до цены дела только если ядро само выставило награду; вес жертвы (страж/уникальный/
торговец/без закона); рецидив; дедупликация свидетелей; рост у скрывшегося (<=10 %/день, кап x3, окно); пойман -> сброс; снята -> запись
удалена; порог -> outlaw_pc_wanted; NPC-разыскиваемый: рост, кап x2, тюрьма -> сброс, облава; сбой колбэка выключает только B1.
python -I -X utf8 build/KMM_Conductor/_dev/test_b1_bounty.py -> OK."""
import ctypes, re, sys, tempfile

DLL = r"C:\Program Files (x86)\Steam\steamapps\workshop\content\233860\3817000612\lua51.dll"
B = r"C:\KenshiModMap\build\KMM_Conductor\scripts\init"
TMP = tempfile.mkdtemp(prefix="kmm_b1_").replace("\\", "/")
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
for _f in sorted(__import__("glob").glob(B + r"\KMM_Conductor*.lua")): run(open(_f, encoding="utf-8").read(), _f.split("\\")[-1])
run(open(B + r"\KMM_Outlaws.lua", encoding="utf-8").read(), "KMM_Outlaws.lua")
run(r'''
N, FAILS = 0, {}
function check(c, what) N = N + 1; if not c then FAILS[#FAILS + 1] = what end end
local C = KMM_Conductor
C.reset()
C.cfg().params.outlaws = { watch_s = 1e9, sdir = "TMPDIR/", count = 0 }
local OL = KMM_Outlaws
local M = OL._M
local pf = C.cfg().player_faction or "player"
LAW = "law_police"; TOWNF = "town_owner"
VAN = { [4] = 2000, [3] = 200, [11] = 100, [15] = 1000 }   -- «ванильные» суммы ядра (static getBountyForCrime)
function MKBM(ch)
  local bm = { me = ch, bty = {}, adds = {} }
  function bm:getActualBounty(fo) return self.bty[fo.id] or 0 end
  function bm:unfairAddToBounty(fo, amt) self.adds[#self.adds + 1] = amt; self.bty[fo.id] = (self.bty[fo.id] or 0) + amt end
  function bm:_getBountyFaction(f) return FAC(LAW) end
  function bm:getBountyForCrime(c) return VAN[c] or 0 end
  ch.crimes = bm
  return bm
end
local pc = MKCH("PC1", pf, 0, 0, { player = true, platoon = "player_squad" })
function pc:isKidnapped() return false end
function pc:isBeingCarried() return false end
pc.inSomething = 0; pc.isChained = false
PCS = { pc }; CHARS = { pc }
local bm = MKBM(pc)
function VICTIM(key, fid, opt)
  opt = opt or {}
  local v = MKCH("V" .. key, fid, 0, 0, opt)
  function v:isLawEnforcement() return opt.law or false end
  function v:isATrader() return opt.trader or false end
  return { toString = function() return "hv_" .. key end, getCharacter = function() return v end }
end
-- преступление: колбэк ядра; vanilla — сколько ядро само добавит (после колбэка, как если бы вызов шёл до начисления)
function CRIME(fid, who, c, vanilla)
  FIRE("BountyManager::notifyCrimeWitnessed", bm, FAC(fid), who, 100, c)
  if vanilla and vanilla > 0 then bm.bty[LAW] = (bm.bty[LAW] or 0) + vanilla end
end
function STEP(dt) CLOCK = CLOCK + (dt or 5); M.C1 = M.cfg(); M.b1_step(C, M.O(C.state()), M.data(C), M.C1, DAYV) end
DAYV = 20
local D = M.data(C)
check(D ~= nil, "outlaws.json loaded")
-- 1. колбэк ставится из первого тика
check(Events.h["BountyManager::notifyCrimeWitnessed"] == nil, "no b1 hook at load")
CLOCK = CLOCK + 100; FIRE("GameWorld::charsUpdate", {})
check(Events.h["BountyManager::notifyCrimeWitnessed"] and #Events.h["BountyManager::notifyCrimeWitnessed"] == 1, "b1 hook registered on first tick")
FIRE("GameWorld::charsUpdate", {})
check(#Events.h["BountyManager::notifyCrimeWitnessed"] == 1, "b1 hook registered once")
-- 2. убийство стража: ядро дало 2000, доплата до 8000 x1.6 = 12800
local O = M.O(C.state())
O.pb_day = DAYV   -- рост в этот день не нужен
local guard = VICTIM("g1", TOWNF, { law = true })
CRIME(TOWNF, guard, 4, VAN[4])
for i = 1, 5 do CRIME(TOWNF, guard, 4, 0) end   -- свидетелей много: одно дело
check(#M.b1.pend == 1, "witnesses dedup: one queued, got " .. #M.b1.pend)
STEP(1)
check(#bm.adds == 0, "no surcharge before settle")
STEP(5)
check(bm.bty[LAW] == 12800, "murder of guard -> 8000 x1.6 total, got " .. tostring(bm.bty[LAW]))
local r = OL.b1()[ "h_PC1|" .. LAW ]
check(r and r.n == 1 and r.cw == "murder" and r.base == 12800, "record: one deed, worst murder, base")
check(M.b1.vb[4] == 2000, "vanilla price read from engine")
-- 3. кража у простого: 800 x1 x1.15 (рецидив) - 200
local b0 = bm.bty[LAW]
CRIME(TOWNF, VICTIM("c1", TOWNF), 3, VAN[3])
STEP(5)
local theft = bm.bty[LAW] - b0 - VAN[3]
check(theft == 720, "theft surcharge with recidivism, got " .. theft)
check(10800 > 720 * 5, "murder >> theft")
-- 4. ядро награды не дало (проникновение без последствий) -> доплаты нет, после b1_pend_s запись уходит
local n0 = #bm.adds
CRIME(TOWNF, nil, 11, 0)
STEP(5); STEP(100)
check(#bm.adds == n0 and #M.b1.pend == 0 and (M.stats.b1_nobounty or 0) == 1, "no engine bounty -> no surcharge, dropped")
-- 5. жертва из банды без закона: вес 0.25 -> доплаты нет (8000*0.25*1.3 < 2000)
local gang
for g in pairs(D.gangs or {}) do if not M.lawful(D, g) and (not gang or g < gang) then gang = g end end
check(gang ~= nil, "lawless gang found")
local w, why = M.b1_weight(M.cfg(), D, VICTIM("b1", gang), gang)
check(why == "lawless" and w == 0.25, "lawless victim weight")
local wt, wy = M.b1_weight(M.cfg(), D, VICTIM("t1", TOWNF, { trader = true, unique = true }), TOWNF)
check(wy == "unique" and wt == 1.5, "unique beats trader (max, not product)")
-- 6. скрылся: рост раз в день, <=10 %/день, кап x3 от честной, окно b1_window
r = OL.b1()["h_PC1|" .. LAW]
local base = r.base
local prev = bm.bty[LAW]
local maxrate = 0
for d = 1, 30 do
  DAYV = DAYV + 1; STEP(5)
  local cur = bm.bty[LAW]
  if prev > 0 then maxrate = math.max(maxrate, (cur - prev) / prev) end
  prev = cur
end
check(maxrate > 0.04 and maxrate <= 0.10 + 1e-9, "daily growth noticeable and <=10%, got " .. maxrate)
check(bm.bty[LAW] <= base * 3 + 1 and bm.bty[LAW] > base * 1.3, "capped at x3 of fair bounty, got " .. bm.bty[LAW] .. " base " .. base)
local after = bm.bty[LAW]
DAYV = DAYV + 1; STEP(5)
check(bm.bty[LAW] == after, "growth stops (cap or trail cold)")
check(DAYV - r.ld > M.cfg().b1_window, "window passed")
-- окно: новое дело -> рост снова; один раз в день
CRIME(TOWNF, VICTIM("c2", TOWNF), 3, VAN[3]); STEP(5)
r = OL.b1()["h_PC1|" .. LAW]
local g0 = bm.bty[LAW]
STEP(5)
check(bm.bty[LAW] == g0, "no second growth the same day")
-- 7. пойман: в тюрьме ядра -> рост сброшен и не идёт
r.esc = 500
pc.inSomething = 2
local c0 = bm.bty[LAW]
DAYV = DAYV + 1; STEP(5)
check(bm.bty[LAW] == c0 and r.esc == 0 and r.caught == "prison", "caught in prison -> growth reset")
pc.inSomething = 0
pc.isChained = true
DAYV = DAYV + 1; STEP(5)
check(bm.bty[LAW] == c0 and r.caught == "chained", "chained -> caught")
pc.isChained = false
-- 8. порог -> весть outlaw_pc_wanted
local nw = 0
for _, e in ipairs(C.state().events) do if e.type == "outlaw_pc_wanted" then nw = nw + 1 end end
check(nw >= 1, "tier event outlaw_pc_wanted emitted")
-- 9. награда снята ядром (выплата/срок/помилование) -> запись удалена
bm.bty[LAW] = 0
DAYV = DAYV + 1; STEP(5)
check(OL.b1()["h_PC1|" .. LAW] == nil and (M.stats.b1_cleared or 0) == 1, "cleared bounty -> record removed")
-- 10. NPC-разыскиваемый: рост, кап x2, тюрьма -> сброс
local lawf
for f in pairs(D.lawful or {}) do if not (D.gangs and D.gangs[f]) and (not lawf or f < lawf) then lawf = f end end
local rg = D.homes[1]
local o = { i = 900, n = "Test Outlaw", g = gang, hr = rg, r = rg, b = 6000, bb = { [lawf] = 6000 }, lf = lawf, cr = {}, t = 0, st = "a",
            since = DAYV, ld = DAYV, dn = 4 }
O.L["o900"] = o
M.cur_day = DAYV
local ob0 = o.b
for d = 1, 4 do M.b1_npc_day(C, O, D, M.cfg(), o, DAYV + d) end
check(o.b > ob0 and o.esc and o.esc > 0 and o.ld == DAYV, "npc grows while free, escalation not counted as a deed")
for d = 5, 6 do M.b1_npc_day(C, O, D, M.cfg(), o, DAYV + d) end
check(o.b <= 12000 + 1, "npc capped at x2, got " .. o.b)
local ob1 = o.b
M.b1_npc_day(C, O, D, M.cfg(), o, DAYV + 20)
check(o.b == ob1, "npc trail cold after window")
M.b1_npc_caught(o)
check(o.esc == 0 and math.abs(o.b - ob0) <= 1, "npc jailed -> growth removed, got " .. o.b)
local o2 = { i = 901, n = "Gang Wanted", g = gang, hr = rg, r = rg, b = 6000, bb = { [gang] = 6000 }, lf = gang, cr = {}, t = 0, st = "a", ld = DAYV }
M.b1_npc_day(C, O, D, M.cfg(), o2, DAYV + 1)
check(o2.b == 6000, "no law -> no growth")
-- облава: выше b1_hunt_at
O.hunt = {}
local o3 = { i = 902, n = "Big Wanted", g = gang, hr = rg, r = rg, b = 30000, bb = { [lawf] = 30000 }, lf = lawf, cr = {}, t = 0, st = "a", ld = DAYV, dn = 1 }
O.L["o902"] = o3
M.b1_npc_day(C, O, D, M.cfg(), o3, DAYV + 1)
local nh = 0; for _ in pairs(O.hunt) do nh = nh + 1 end
check((#(D.regions[rg].towns or {}) == 0) or (o3.b1h == true and nh == 1), "high bounty -> manhunt (HUNT_BOUNTIES patrol)")
O.L["o900"], O.L["o902"] = nil, nil
-- 11. сбой колбэка выключает только B1
local okw = pcall(FIRE, "BountyManager::notifyCrimeWitnessed", { me = { isPlayerCharacter = function() error("boom") end } }, FAC(TOWNF), nil, 1, 4)
check(okw and M.b1_off == true and not M.off, "callback error disables B1 only")
M.b1_off = false
-- 12. цена колбэка: чужое преступление
local npc = MKCH("N1", TOWNF, 0, 0)
local nbm = MKBM(npc)
local q0 = #M.b1.pend
for i = 1, 20000 do M.b1_on_crime(nbm, FAC(TOWNF), nil, 1, 4) end
check(#M.b1.pend == q0, "npc crimes not queued")
RESULT = #FAILS == 0 and ("OK " .. N) or ("FAIL: " .. table.concat(FAILS, "; "))
'''.replace("TMPDIR", TMP), "test")
L.lua_getfield(st, -10002, b"RESULT")
r = L.lua_tolstring(st, -1, None).decode()
print(r)
sys.exit(0 if r.startswith("OK") else 1)
