"""Offline test KMM_Deeds: колбэк FactionRelations::affectRelations -> агрегат -> событие deed в шине дирижёра.
Регистрация хука из первого тика, NPC<->NPC (самое тяжёлое дело, координаты и город), дедупликация в день, игрок (attacked не
дублирует player_raid, плен/помощь — да), чужие фракции мимо, потолки, флуд колбэка, цена вызова, самоотключение.
Y1: поле witnessed (подробно — test_y1_witness.py).
python -I -X utf8 build/KMM_Conductor/_dev/test_deeds.py -> OK."""
import ctypes, re, sys, tempfile, time

DLL = r"C:\Program Files (x86)\Steam\steamapps\workshop\content\233860\3817000612\lua51.dll"
B = r"C:\KenshiModMap\build\KMM_Conductor\scripts\init"
TMP = tempfile.mkdtemp(prefix="kmm_deeds_").replace("\\", "/")
L = ctypes.CDLL(DLL)
L.luaL_newstate.restype = ctypes.c_void_p
for fn, at in [("luaL_openlibs", [ctypes.c_void_p]), ("luaL_loadstring", [ctypes.c_void_p, ctypes.c_char_p]),
               ("lua_pcall", [ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int])]:
    getattr(L, fn).argtypes = at
L.lua_tolstring.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p]
L.lua_tolstring.restype = ctypes.c_char_p
L.lua_getfield.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_char_p]
L.lua_settop.argtypes = [ctypes.c_void_p, ctypes.c_int]
st = L.luaL_newstate()
L.luaL_openlibs(st)


def run(code, name="chunk"):
    if L.luaL_loadstring(st, code.encode("utf-8")) or L.lua_pcall(st, 0, 0, 0):
        msg = L.lua_tolstring(st, -1, None)
        raise RuntimeError(f"{name}: {msg.decode('utf-8', 'replace') if msg else '?'}")


def gstr(name):
    L.lua_getfield(st, -10002, name.encode())
    v = L.lua_tolstring(st, -1, None)
    L.lua_settop(st, 0)
    return v.decode("utf-8", "replace") if v else ""


rt = open(r"C:\KenshiModMap\tools\test\test_runtime.py", encoding="utf-8").read()
run(re.search(r"STUBS = r'''(.*?)'''", rt, re.S).group(1).replace("TMPDIR", TMP), "stubs")
run("math.randomseed(20261115)", "seed")
for _f in sorted(__import__("glob").glob(B + r"\KMM_Conductor*.lua")): run(open(_f, encoding="utf-8").read(), _f.split("\\")[-1])
run(open(B + r"\KMM_Gov.lua", encoding="utf-8").read(), "KMM_Gov.lua")
run(open(B + r"\KMM_Deeds.lua", encoding="utf-8").read(), "KMM_Deeds.lua")
run(r'''
N, FAILS = 0, {}
function check(c, what) N = N + 1; if not c then FAILS[#FAILS + 1] = what end end
C = KMM_Conductor
C.reset()
DD = KMM_Deeds
local CFG = C.cfg()
PF = CFG.player_faction
local ks = {}
for fid in pairs(CFG.factions) do if fid ~= PF then ks[#ks + 1] = fid end end
table.sort(ks)
FA, FB, FX = ks[1], ks[2], ks[3]
-- игрок стоит в городе (первый по sid с координатами)
local sids = {}
for sid, t in pairs(CFG.town_info) do if t.x then sids[#sids + 1] = sid end end
table.sort(sids)
TSID = sids[1]
local T0 = CFG.town_info[TSID]
PCS = { MKCH("PC1", PF, T0.x + 50, T0.z, { player = true, platoon = "player_squad" }) }; CHARS = { PCS[1] }
GOT = {}
C.subscribe("deed", function(ev) GOT[#GOT + 1] = ev end)
DAYV = 10
function pump(n) for i = 1, n do CLOCK = CLOCK + 11; FIRE("GameWorld::charsUpdate", {}) end end
function REL(victim, doer, et, k, mult) for i = 1, (k or 1) do FIRE("FactionRelations::affectRelations", { me = FAC(victim) }, FAC(doer), et, mult or 1) end end
function deeds_in_state() local n = 0; for _, e in ipairs(C.state().events) do if e.type == "deed" then n = n + 1 end end; return n end
''', "setup")
run(r'''
-- 1. хук регистрируется из первого тика, не при загрузке
check(Events.h["FactionRelations::affectRelations"] == nil, "no hook at load")
pump(1)
check(Events.h["FactionRelations::affectRelations"] and #Events.h["FactionRelations::affectRelations"] == 1, "hook registered on first tick")
pump(1)
check(#Events.h["FactionRelations::affectRelations"] == 1, "hook registered once")
-- 2. NPC <-> NPC: FA напал (1) x5 и убил (4) x2 людей FB -> одно событие deed, kind killed, у города игрока
REL(FB, FA, 1, 5, 0.5); REL(FB, FA, 4, 2)
check(#GOT == 0, "no emit inside callback")
pump(1)
local e = GOT[1]
check(#GOT == 1, "one deed after flush: " .. #GOT)
check(e and e.kind == "killed" and e.tone == "harm" and e.a == FA and e.b == FB, "kind/a/b: " .. tostring(e and e.kind) .. " " .. tostring(e and e.a))
check(e and e.n == 7 and e.w == 4.5 and e.aggressive == true and e.counts == "attacked:5 killed:2", "n/w/counts: " .. tostring(e and e.n) .. " " .. tostring(e and e.w) .. " " .. tostring(e and e.counts))
check(e and not e.by_player and not e.to_player and e.witnessed == nil, "npc deed (no witness field, Y1)")
check(e and e.x and e.z and e.town_sid == TSID and e.town_name and e.text:find(e.town_name, 1, true), "place: " .. tostring(e and e.town_sid) .. " " .. tostring(e and e.text))
check(e and e.text:find(C.name(FA), 1, true) and e.text:find(C.name(FB), 1, true), "text names: " .. tostring(e and e.text))
check(e and e.id and deeds_in_state() == 1 and e.attacker == C.name(FA), "in conductor journal (S.events) with attacker name")
-- 3. то же в тот же день — дубль; другой вид дела — новое; новый день — снова
REL(FB, FA, 4, 3); pump(1)
check(#GOT == 1 and DD.stats().dup == 1, "same day same kind deduped")
REL(FB, FA, 12, 1); pump(1)
check(#GOT == 2 and GOT[2].kind == "captured", "other kind same day -> new event")
DAYV = 11; REL(FB, FA, 4, 1); pump(1)
check(#GOT == 3 and GOT[3].kind == "killed", "next day -> new event")
-- 4. помощь — отдельный тон той же пары
REL(FB, FA, 7, 2); REL(FB, FA, 8, 1); pump(1)
check(#GOT == 4 and GOT[4].tone == "help" and GOT[4].kind == "aided" and GOT[4].text:find("fought beside", 1, true), "help deed: " .. tostring(GOT[4] and GOT[4].kind))
-- 5. только стычка (attacked) у NPC — счётчик, без события
local m0 = DD.stats().minor
REL(FX, FA, 0, 4); pump(1)
check(#GOT == 4 and DD.stats().minor == m0 + 1, "npc attacked-only skipped")
-- 6. игрок: нападение — уже player_raid дирижёра (не дублируем); плен — событие by_player
REL(FB, PF, 1, 3); pump(1)
check(#GOT == 4, "player attacked-only not emitted (player_raid covers it)")
REL(FB, PF, 12, 1); REL(FB, PF, 1, 2); pump(1)
local p = GOT[5]
check(p and p.by_player == true and p.kind == "captured" and p.a == PF and p.b == FB and p.text:find("^The Nameless took people of"), "player capture: " .. tostring(p and p.text))
check(p and p.witnessed == false and p.witness_src == "none", "Y1: nobody around the player -> unseen: " .. tostring(p and p.witnessed))
-- NPC помог игроку: to_player
REL(PF, FX, 7, 1); pump(1)
local q = GOT[6]
check(q and q.to_player == true and q.kind == "aided" and q.a == FX and q.b == PF and q.text:find("the Nameless", 1, true), "to_player aid: " .. tostring(q and q.text))
check(q and q.witnessed == true, "Y1: to_player witnessed")
-- 7. фракции вне модели дирижёра — мимо
local f0 = DD.stats().foreign
REL("zz-unknown.mod", FA, 4, 2); pump(1)
check(#GOT == 6 and DD.stats().foreign == f0 + 1, "foreign faction skipped")
-- 8. мусор в аргументах: нет фракции / неизвестный код / та же фракция — без ошибок
FIRE("FactionRelations::affectRelations", {}, FAC(FA), 4, 1)
FIRE("FactionRelations::affectRelations", nil, nil, nil, nil)
FIRE("FactionRelations::affectRelations", { me = { getData = function() error("bad faction") end } }, FAC(FA), 4, 1)
REL(FA, FA, 4, 1); REL(FB, FA, 99, 1)
pump(1)
check(#GOT == 6 and DD.stats().unknown >= 4 and DD.stats().same >= 1, "garbage args tolerated: unknown=" .. DD.stats().unknown)
check(next(DD.disabled()) == nil, "not disabled by garbage")
''', "flow")
run(r'''
-- 9. потолок NPC в день и флуд колбэка
DAYV = 20
local ks = {}
for fid in pairs(C.cfg().factions) do if fid ~= PF then ks[#ks + 1] = fid end end
table.sort(ks)
local g0 = #GOT
for i = 1, 20 do REL(ks[i + 3], ks[i + 4], 4, 1) end
pump(1)
check(#GOT - g0 == 8 and DD.stats().capped >= 12, "npc_day cap 8: " .. (#GOT - g0) .. " capped " .. DD.stats().capped)
local d0, k0 = DD.stats().dropped, DD.stats().kept
CLOCK = CLOCK + 0.5   -- одна секунда os.clock
for i = 1, 1000 do REL(ks[(i % 90) + 1], ks[((i * 7) % 90) + 2], 4, 1) end
check(DD.stats().kept - k0 <= 300 and DD.stats().dropped - d0 >= 700, "flood capped per second: kept " .. (DD.stats().kept - k0) .. " dropped " .. (DD.stats().dropped - d0))
check(DD.stats().pending <= 64, "window keys capped: " .. DD.stats().pending)
pump(1)
check(DD.stats().pending == 0, "window flushed")
-- состояние в сейве маленькое
local X = DD.today()
local nseen = 0; for _ in pairs(X.seen) do nseen = nseen + 1 end
check(nseen <= 8 + 16 and type(C.serialize()) == "string" and C.serialize():find("deeds", 1, true), "ext.deeds in save, seen " .. nseen)
''', "caps")
# цена колбэка: 20000 вызовов (без сброса) в реальном времени
run(r'''CLOCK = CLOCK + 100; DD._D.C = nil; DD._D.DEF.max_calls_s = 1e9''', "prep")
t0 = time.perf_counter()
run(r'''for i = 1, 20000 do REL(FB, FA, 4, 1) end''', "cost")
per_call_us = (time.perf_counter() - t0) / 20000 * 1e6
run(r'''DD._D.DEF.max_calls_s = 300''', "restore")
t0 = time.perf_counter()
run(r'''pump(1)''', "flush")
flush_ms = (time.perf_counter() - t0) * 1000
run(r'''
-- 10. сбой колбэка выключает только колбэк; сбой тика — модуль
local D = DD._D
local k4 = D.KIND[4]
D.KIND[4] = { "killed", "harm", nil }   -- сравнение с nil -> ошибка в колбэке
REL(FB, FA, 6, 1); REL(FB, FA, 4, 1)
check(DD.disabled().deeds_hook == true and not D.off, "hook error disables hook only")
D.KIND[4] = k4
D.agg, D.nagg = {}, 0
local g0 = #GOT
REL(FB, FA, 6, 1); pump(1)
check(#GOT == g0, "hook stays off until restart")
D.hook_off = false
local cfg0 = C.cfg
C.cfg = function() error("boom") end
REL(FB, FA, 6, 1); pump(1)
C.cfg = cfg0
check(D.off == true and DD.disabled().deeds == true, "tick error disables module")
local lg = io.open("TMPDIR/deeds.log", "r"); local s = lg and lg:read("*a") or ""; if lg then lg:close() end
check(s:find("affectRelations hook registered", 1, true) and s:find("witness: notifyCrimeWitnessed hook registered", 1, true) and s:find("first callback:", 1, true) and s:find("deed: killed", 1, true)
      and (s:find("disabled until restart", 1, true) or s:find("failed, retry in", 1, true)), "log markers")
RESULT = #FAILS == 0 and ("OK " .. N .. " checks, deeds=" .. #GOT) or ("FAIL: " .. table.concat(FAILS, "; "))
'''.replace("TMPDIR", TMP), "disable")
r = gstr("RESULT")
budget_ok = per_call_us < 30 and flush_ms < 15
print(r, f"| callback {per_call_us:.1f} us/call, flush {flush_ms:.2f} ms")
if not budget_ok:
    print("FAIL: cost over budget")
sys.exit(0 if r.startswith("OK") and budget_ok else 1)
