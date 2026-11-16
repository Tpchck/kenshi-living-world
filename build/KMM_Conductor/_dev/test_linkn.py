"""Офлайн-тест LINKN (2026-11-12): смена владельца города -> настоящий вариант через KMM_Native (фейковый плагин с записью вызовов).
Применение, отказ при конфликте, отказ рискованного, снятие со счётом ссылок, повторное применение после «загрузки», нет плагина,
самоотключение при сбое, лидер убит/не убит, реальная таблица modules/kmm_ws_lut.lua и реальный адаптер KMM_Native.lua.
python -I -X utf8 build/KMM_Conductor/_dev/test_linkn.py -> OK, код 1 при провале."""
import ctypes
import os
import re
import sys
import tempfile

DLL = r"C:\Program Files (x86)\Steam\steamapps\workshop\content\233860\3817000612\lua51.dll"
B = r"C:\KenshiModMap\build\KMM_Conductor\scripts\init"
LUT = r"C:\KenshiModMap\build\KMM_Conductor\scripts\modules\kmm_ws_lut.lua"
ADAPTER = r"C:\KenshiModMap\build\KMM_Native\scripts\init\KMM_Native.lua"
TMP = tempfile.mkdtemp(prefix="kmm_linkn_").replace("\\", "/")
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
run("ADAPTER_SRC = [==[" + open(ADAPTER, encoding="utf-8").read() + "]==]\nLUT_PATH = '" + LUT.replace("\\", "/") + "'", "paths")
run(r'''
N, FAILS = 0, {}
function check(c, what) N = N + 1; if not c then FAILS[#FAILS + 1] = what end end
local C = KMM_Conductor
local P = C.cfg().params
C._set("tick_days", 1e9); C._set("first_event_after_days", 1e9)
C.reset()

-- фейковый плагин с записью вызовов
NAT = { avail = true, calls = {}, st = {}, throw = false, failset = false }
local function ncount(prefix) local n = 0; for _, c in ipairs(NAT.calls) do if c:sub(1, #prefix) == prefix then n = n + 1 end end; return n end
local fake = setmetatable({}, { __index = function(_, k) if k == "available" then return NAT.avail end end })
function fake.ws_set(sid, v) if NAT.throw then error("boom") end; NAT.calls[#NAT.calls + 1] = "set:" .. sid .. ":" .. tostring(v); if NAT.failset then return false end; NAT.st[sid] = v; return true end
function fake.ws_clear(sid) NAT.calls[#NAT.calls + 1] = "clear:" .. sid; local had = NAT.st[sid] ~= nil; NAT.st[sid] = nil; return had end
function fake.ws_clear_all() NAT.calls[#NAT.calls + 1] = "clear_all"; NAT.st = {}; return 0 end
local function with_native(on) if on then KMM_Native = fake else KMM_Native = nil end end

-- события ws_*
EV = {}
C.subscribe("ws_*", function(e) EV[#EV + 1] = { t = e.type, town = e.town_sid, owner = e.owner, reason = e.reason } end)
local function evn(ty, town, reason) local n = 0; for _, e in ipairs(EV) do if e.t == ty and (not town or e.town == town) and (not reason or e.reason == reason) then n = n + 1 end end; return n end

-- города и фракции
local ORIG = {}
for fid, f in pairs(C.cfg().factions) do for _, t in ipairs(f.towns or {}) do ORIG[t] = fid end end
local S = C.state()
local cand = {}
for fid, f in pairs(S.F) do if f.alive and not f.player and not f.relic then cand[#cand + 1] = fid end end
table.sort(cand)
local X, Y, Zf = cand[1], cand[2], cand[3]
local ts = {}
for t in pairs(C.cfg().town_info) do if ORIG[t] and ORIG[t] ~= X and ORIG[t] ~= Y and ORIG[t] ~= Zf then ts[#ts + 1] = t end end
table.sort(ts)
check(#ts >= 8, "достаточно городов для теста")
local t1, t2, t3, t4, t5, t6, t7 = ts[1], ts[2], ts[3], ts[4], ts[5], ts[6], ts[7]
local function own(t, fid, free)
  S = C.state()
  for _, f in pairs(S.F) do f.towns[t] = nil end
  S.free[t] = free and true or nil
  if fid then S.F[fid].towns[t] = true end
end
local D = 0
local function step(n) D = D + (n or 1); C.advance(D) end
local function reset_all()
  EV = {}; NAT.calls = {}; NAT.st = {}; NAT.throw = false; NAT.failset = false; NAT.avail = true
  C.ws_reset(); C.reset(); S = C.state()
end
-- фикстура таблицы вариантов
local FIX = { v = 1, F = { X, Y, Zf }, W = { "wsA", "wsB", "wsC", "wsD" }, N = { "leaderL" }, T = {
  [t1] = { { o = 1, c = { 1, 1 } } },                       -- чистый: wsA=1 -> X
  [t6] = { { o = 1, c = { 1, 1 } } },                       -- делит wsA с t1 (счётчик ссылок)
  [t7] = { { o = 1, c = { 1, 0 } } },                       -- wsA=0: конфликт с t1
  [t2] = { { o = 1, c = { 2, 1 }, x = { t3, 2 } } },        -- задевает t3: нужен владелец Y
  [t3] = { { o = 2, c = { 2, 1 } } },                       -- wsB=1 -> Y (то же состояние переключает и t2)
  [t4] = { { o = 1, c = { 3, 1 }, d = { 1, "k" } } },       -- нужен убитым лидер L
  [t5] = { { o = 1, r = 1 } },                              -- рискованный
} }

-- 1) плагина нет: тихо, ничего не пишется
with_native(false); C.ws_inject(FIX); reset_all(); with_native(false)
own(t1, X); step()
check(#EV == 0 and #NAT.calls == 0, "нет плагина: событий ws_* и вызовов нет")
check(C.ws_stats().active == false and C.ws_stats().off == false, "нет плагина: подсистема неактивна, но не отключена")
step(); step()
check(#EV == 0, "нет плагина: и дальше тихо")
NAT.avail = false; with_native(true); reset_all(); C.ws_inject(FIX); with_native(true); NAT.avail = false
own(t1, X); step()
check(#EV == 0 and #NAT.calls == 0, "available=false: тихо")

-- 2) применение
NAT.avail = true; reset_all(); C.ws_inject(FIX); with_native(true)
step()   -- ленивый старт: ws_clear_all
check(ncount("clear_all") == 1, "после старта один ws_clear_all")
own(t1, X); C.emit({ type = "town_captured", a = X, town_sid = t1, town_name = "T1" }); step()
check(evn("ws_applied", t1) == 1, "town_captured -> ws_applied")
check(NAT.st.wsA == true, "wsA включён")
check(C.ws_applied()[t1] == X, "в реестре t1 -> X")
local e1; for _, e in ipairs(EV) do if e.t == "ws_applied" then e1 = e end end
check(e1 and e1.owner == X and e1.town == t1, "событие несёт town_sid и owner")
local s0 = C.ws_stats()
check(s0.changes == 1 and s0.applied == 1, "статистика: 1 смена, 1 применение")
-- без спама в журнал: ws_* не попадают в S.events
local nj = 0; for _, e in ipairs(C.state().events) do if e.type:sub(1, 3) == "ws_" then nj = nj + 1 end end
check(nj == 0, "ws_* не пишутся в журнал")

-- 3) счётчик ссылок: t6 тоже просит wsA; возврат t1 не снимает wsA
own(t6, X); step()
check(evn("ws_applied", t6) == 1 and ncount("set:wsA:true") == 2, "t6 применён (wsA установлен повторно)")
own(t1, ORIG[t1]); step()
check(evn("ws_cleared", t1) == 1, "возврат t1: ws_cleared")
check(NAT.st.wsA == true and ncount("clear:wsA") == 0, "wsA остаётся: его держит t6")
own(t6, ORIG[t6]); step()
check(NAT.st.wsA == nil and ncount("clear:wsA") == 1, "вернули и t6: wsA снят ровно один раз")

-- 4) конфликт: t1 держит wsA=1, t7 просит wsA=0
own(t1, X); step()
own(t7, X); step()
check(evn("ws_skip", t7, "ws_conflict") == 1, "конфликт ws -> ws_skip ws_conflict")
check(ncount("set:wsA:false") == 0, "конфликтное состояние не выставлено")
step(); step(); step()
check(evn("ws_skip", t7) == 1, "ws_skip не повторяется (без спама)")
own(t7, ORIG[t7]); own(t1, ORIG[t1]); step()

-- 5) задетый город: t2 требует, чтобы t3 принадлежал Y
own(t2, X); step()
check(evn("ws_skip", t2, "other_town") == 1 and NAT.st.wsB == nil, "t3 не у Y: ws_skip other_town, ничего не выставлено")
local ar = C.ws_stats().applied_retry
own(t3, Y); step()
check(evn("ws_applied", t3) == 1 and evn("ws_applied", t2) == 1, "t3 перешёл к Y: применены и t3, и отложенный t2")
check(C.ws_stats().applied_retry == ar + 1, "t2 применён повтором")
own(t3, Zf); step()   -- t3 ушёл к Z (вариантов нет): у t2 условие нарушено
check(evn("ws_cleared", t2) == 1 and C.ws_applied()[t2] == nil, "t3 у Z: вариант t2 снят (revalidate)")
check(NAT.st.wsB == nil, "wsB снят")
own(t2, ORIG[t2]); own(t3, ORIG[t3]); step()

-- 6) рискованный
own(t5, X); step()
check(evn("ws_skip", t5, "risky") == 1 and C.ws_applied()[t5] == nil, "рискованный вариант не применён, ws_skip risky")
own(t5, ORIG[t5]); step()

-- 7) лидер: нужен убитым L
own(t4, X); step()
check(evn("ws_skip", t4, "risky_npc") == 1 and NAT.st.wsC == nil, "лидер жив в модели: ws_skip risky_npc")
S = C.state(); S.resolved["leaderL"] = "leader_killed"
C.emit({ type = "leader_killed", a = X, b = Y, town_sid = t4, town_name = "T4", leader_sid = "leaderL", leader_name = "L" }); step()
check(evn("ws_applied", t4) == 1 and NAT.st.wsC == true, "лидер убит дирижёром: вариант применён")
S.resolved["leaderL"] = "leader_captured"; step(); step()
check(C.ws_applied()[t4] == nil and evn("ws_cleared", t4) == 1, "тип исхода не тот (пленён, нужна смерть): вариант снят")
S.resolved["leaderL"] = nil
own(t4, ORIG[t4]); step()

-- 8) «загрузка игры»: переопределения плагина не в сейве; смена S -> clear_all и пересчёт по текущим владельцам
reset_all(); C.ws_inject(FIX); with_native(true)
NAT.st["stale"] = true   -- осталось от прошлой сессии
S = C.state(); own(t1, X); own(t6, X)
step()
check(ncount("clear_all") == 1 and NAT.st.stale == nil, "после загрузки: ws_clear_all убрал чужие переопределения")
check(NAT.st.wsA == true and evn("ws_applied", t1) == 1 and evn("ws_applied", t6) == 1, "после загрузки: варианты применены по состоянию дирижёра")
-- ещё одна загрузка (новый S): всё заново, ссылки не накапливаются
C.reset(); S = C.state(); own(t1, X)
step()
check(ncount("clear_all") == 2, "вторая загрузка: ещё один ws_clear_all")
check(NAT.st.wsA == true and NAT.st.wsC == nil, "вторая загрузка: применён только t1")
own(t1, ORIG[t1]); step()
check(NAT.st.wsA == nil, "после второй загрузки возврат t1 снимает wsA (счётчик начат заново)")

-- 9) вольный город снимает вариант
reset_all(); C.ws_inject(FIX); with_native(true); step()
own(t1, X); step()
check(C.ws_applied()[t1] == X, "t1 применён")
own(t1, nil, true); step()
check(C.ws_applied()[t1] == nil and evn("ws_cleared", t1) == 1, "город стал вольным: вариант снят")

-- 10) самоотключение: сбой плагина не роняет остальное
reset_all(); C.ws_inject(FIX); with_native(true); step()
NAT.throw = true
own(t1, X)
local okadv = pcall(step)
check(okadv, "сбой плагина не пробрасывается наружу")
check(C.ws_stats().off == true, "подсистема самоотключилась")
NAT.throw = false
local ev0 = #EV
own(t6, X); step(); step()
check(#EV == ev0 and C.ws_stats().off == true, "после отключения тихо")
check(C.state().F[X].towns[t6] == true, "остальная логика дирижёра жива")
-- ws_set возвращает false трижды -> отключение
reset_all(); C.ws_inject(FIX); with_native(true); step()
NAT.failset = true
own(t1, X); own(t6, X); step(); step()
check(evn("ws_skip", t1, "native_fail") == 1, "ws_set=false: ws_skip native_fail")
for _, t in ipairs({ t2 }) do own(t, X) end
step(); step()
check(NAT.st.wsA == nil, "после отказа плагина ничего не осталось включённым")

-- 11) реальная таблица (2026-11-16: только свои WS, один WS на пару город->владелец): файл читается лениво, вариант применяется без условий о лидерах
reset_all(); with_native(true); P.ws.lut_path = LUT_PATH
step()
S = C.state()
local f = assert(loadfile(LUT_PATH)); local LU = f()
check(type(LU) == "table" and LU.v == 1 and LU.own == 1, "kmm_ws_lut.lua читается как чистые данные (own=1)")
local allown = true
for _, w in ipairs(LU.W) do local m = w:match("^%d+%-(KMM_[%w_]+)%.mod$"); if not m or m == "KMM_Merged" then allown = false end end
check(allown, "реальная таблица: все WS свои (<n>-KMM_*.mod)")
local pick, pv
for t, list in pairs(LU.T) do
  if C.cfg().town_info[t] then
    for _, v in ipairs(list) do
      if not v.r and not v.x and not v.d and #v.c == 2 and S.F[LU.F[v.o]] and S.F[LU.F[v.o]].alive and LU.F[v.o] ~= ORIG[t] then
        if not pick or t < pick then pick, pv = t, v end
      end
    end
  end
end
check(pick ~= nil, "в реальной таблице есть вариант для проверки")
if pick then
  local fid = LU.F[pv.o]
  own(pick, fid); step()
  check(evn("ws_applied", pick) == 1, "реальная таблица: смена владельца -> ws_applied (без ложной смерти лидера)")
  check(NAT.st[LU.W[pv.c[1]]] == true, "реальная таблица: выставлен свой WS варианта")
  local n = 0; for _ in pairs(NAT.st) do n = n + 1 end
  check(n == 1, "реальная таблица: выставлено ровно одно состояние")
  own(pick, ORIG[pick]); step()
  local left = 0; for _ in pairs(NAT.st) do left = left + 1 end
  check(left == 0, "реальная таблица: после возврата ничего не осталось включённым")
end

-- 12) реальный адаптер KMM_Native.lua поверх фейкового модуля kmm_native
package.loaded["kmm_native"] = { ws_hook_active = function() return true end, ws_set = function(s, v) NAT.calls[#NAT.calls + 1] = "mset:" .. s; NAT.st[s] = v; return true end,
  ws_clear = function(s) NAT.st[s] = nil; return true end, ws_clear_all = function() NAT.st = {}; return 0 end, ws_get = function() return nil end, ws_stats = function() return {} end, version = function() return "t" end }
reset_all(); KMM_Native = nil
assert(loadstring(ADAPTER_SRC, "@adapter"))()
check(KMM_Native and KMM_Native.available == true, "реальный адаптер: available=true")
local OWNW = "900001-KMM_Elite.mod"
C.ws_inject({ v = 1, F = { X }, W = { OWNW, "wsA" }, N = {}, T = { [t1] = { { o = 1, c = { 1, 1 } } }, [t6] = { { o = 1, c = { 2, 1 } } } } }); step()
own(t1, X); step()
check(evn("ws_applied", t1) == 1 and NAT.st[OWNW] == true and ncount("mset:" .. OWNW) == 1, "реальный адаптер: свой WS применён через ws_set")
own(t6, X); step()
check(ncount("mset:wsA") == 0 and NAT.st.wsA == nil and C.ws_applied()[t6] == nil, "реальный адаптер: чужой sid не доходит до плагина (белый список)")

local rf = io.open("TMPDIR/result.txt", "w"); rf:write(N .. " " .. #FAILS .. "|" .. table.concat(FAILS, "|")); rf:close()
'''.replace("TMPDIR", TMP), "test")
res = open(TMP + "/result.txt", encoding="utf-8").read().split("|")
n, nf = map(int, res[0].split())
print("LINKN: checks", n, "fails", nf)
for x in res[1:]:
    if x:
        print("FAIL:", x)
print("OK" if nf == 0 else "FAILED")
sys.exit(1 if nf else 0)
