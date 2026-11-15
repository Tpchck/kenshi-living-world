"""Offline test Y1 (KMM_Deeds, свидетели): дело игрока помечается witnessed по ванильным сигналам.
Колбэк BountyManager::notifyCrimeWitnessed (преступник — игрок) -> witnessed=true src=crime; без преступления — осведомлённость
ближайших NPC снимка KMM_Gov (SensoryData.amIAwareOfThisGuy) -> sense/none; без сигналов -> nil (как до Y1). Ожидание одного окна
для свежего невиданного дела, отдельная дедупликация, to_player=true, NPC без поля, attacked с игроком по-прежнему не выдаётся,
сбой колбэка свидетеля выключает только его, API crime_seen, цена проверки.
python -I -X utf8 build/KMM_Conductor/_dev/test_y1_witness.py -> OK."""
import ctypes, re, sys, tempfile, time

DLL = r"C:\Program Files (x86)\Steam\steamapps\workshop\content\233860\3817000612\lua51.dll"
B = r"C:\KenshiModMap\build\KMM_Conductor\scripts\init"
TMP = tempfile.mkdtemp(prefix="kmm_y1_").replace("\\", "/")
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
D = DD._D
local CFG = C.cfg()
PF = CFG.player_faction
local ks = {}
for fid in pairs(CFG.factions) do if fid ~= PF then ks[#ks + 1] = fid end end
table.sort(ks)
FA, FB, FX = ks[1], ks[2], ks[3]
local sids = {}
for sid, t in pairs(CFG.town_info) do if t.x then sids[#sids + 1] = sid end end
table.sort(sids)
T0 = CFG.town_info[sids[1]]
PX, PZ = T0.x + 50, T0.z
PCS = { MKCH("PC1", PF, PX, PZ, { player = true, platoon = "player_squad" }) }
CHARS = { PCS[1] }
GOT = {}
C.subscribe("deed", function(ev) GOT[#GOT + 1] = ev end)
DAYV = 10
ASKS = 0
-- NPC с ванильным «чувством»: aware — знает ли об игроке; need — что передал модуль вторым аргументом
function NPC(nm, fid, dx, opt)
  opt = opt or {}
  local c = MKCH(nm, fid, PX + dx, PZ, opt)
  c.getSensoryData = function()
    if opt.sense_err then error("no sensory data") end
    return { amIAwareOfThisGuy = function(self, who, need) ASKS = ASKS + 1; LAST_NEED = need; return opt.aware and who:isPlayerCharacter() or false end }
  end
  return c
end
function setnpcs(list) CHARS = { PCS[1] }; for _, c in ipairs(list) do CHARS[#CHARS + 1] = c end; KMM_Gov.snapshot_reset() end
function pump(n) for i = 1, n do CLOCK = CLOCK + 11; FIRE("GameWorld::charsUpdate", {}) end end
function REL(victim, doer, et, k) for i = 1, (k or 1) do FIRE("FactionRelations::affectRelations", { me = FAC(victim) }, FAC(doer), et, 1) end end
function CRIME(fid, crime, who) FIRE("BountyManager::notifyCrimeWitnessed", { me = who or PCS[1] }, fid and FAC(fid) or nil, { null = false }, 120, crime) end
function last() return GOT[#GOT] end
''', "setup")
run(r'''
-- 1. оба колбэка — из первого тика
check(Events.h["BountyManager::notifyCrimeWitnessed"] == nil, "no witness hook at load")
pump(1)
check(Events.h["BountyManager::notifyCrimeWitnessed"] and #Events.h["BountyManager::notifyCrimeWitnessed"] == 1, "witness hook registered on first tick")
check(Events.h["FactionRelations::affectRelations"] and #Events.h["FactionRelations::affectRelations"] == 1, "deeds hook still registered")
-- 2. стража заметила убийство игрока (CRIME_MURDER=4) против FB -> дело killed видели
CRIME(FB, 4)
check(D.st.crime_pl == 1 and DD.crime_seen(FB) == "murder", "crime recorded: " .. tostring(DD.crime_seen(FB)))
REL(FB, PF, 4, 2); pump(1)
local e = last()
check(#GOT == 1 and e.kind == "killed" and e.by_player and e.witnessed == true and e.witness_src == "crime" and e.crime == "murder",
      "crime -> witnessed: " .. tostring(e and e.witnessed) .. " " .. tostring(e and e.witness_src))
-- 3. преступление NPC (не игрок) — не в счёт
local npc = MKCH("thief", FX, PX + 10, PZ)
CRIME(FA, 3, npc)
check(D.st.crime_pl == 1 and D.st.crimes == 2 and DD.crime_seen(FA) == nil, "npc crime ignored")
-- 4. игрок бьёт FA в пустоте: вокруг никого -> не видели (дело в шине, witnessed=false)
setnpcs({})
REL(FA, PF, 2, 3); pump(1)
e = last()
check(#GOT == 2 and e.kind == "defeated" and e.witnessed == false and e.witness_src == "none", "nobody around -> unseen: " .. tostring(e.witnessed))
-- то же невиданное — дубль; увиденное в тот же день — новое событие (своя дедупликация)
REL(FA, PF, 2, 1); pump(1)
check(#GOT == 2 and DD.stats().dup >= 1, "unseen duplicate same day")
local wit = NPC("survivor", FA, 300, { aware = true })
setnpcs({ wit })
REL(FA, PF, 2, 1); pump(1)
e = last()
check(#GOT == 3 and e.witnessed == true and e.witness_src == "sense" and LAST_NEED == true, "survivor aware -> seen (sense), need=" .. tostring(LAST_NEED))
-- 5. рядом только без сознания / не знающие / дальше радиуса -> не видели; чужая фракция знает -> видели
DAYV = 11
setnpcs({ NPC("ko", FB, 100, { aware = true, down = true }), NPC("blind", FB, 200, { aware = false }), NPC("far", FX, 5000, { aware = true }) })
REL(FB, PF, 12, 1); pump(1)
e = last()
check(#GOT == 4 and e.kind == "captured" and e.witnessed == false, "down/unaware/far -> unseen: " .. tostring(e.witnessed))
setnpcs({ NPC("bystander", FX, 800, { aware = true }) })
REL(FB, PF, 4, 1); pump(1)
e = last()
check(#GOT == 5 and e.kind == "killed" and e.witnessed == true and e.witness_src == "sense", "third-party witness -> seen")
-- помощь игрока тоже помечается (спасённый знает)
setnpcs({ NPC("patient", FX, 50, { aware = true }) })
REL(FX, PF, 8, 1); pump(1)
e = last()
check(#GOT == 6 and e.tone == "help" and e.witnessed == true, "help deed witnessed")
-- 6. to_player — всегда true; NPC<->NPC — поля нет
REL(PF, FA, 4, 1); pump(1)
e = last()
check(#GOT == 7 and e.to_player and e.witnessed == true and e.witness_src == "to_player", "to_player witnessed")
REL(FB, FA, 4, 1); pump(1)
e = last()
check(#GOT == 8 and not e.by_player and not e.to_player and e.witnessed == nil and e.witness_src == nil, "npc deed: no witness field")
-- 7. DECISIONS: только нападение игрока не выдаётся, даже если стража заметила
CRIME(FA, 5)
REL(FA, PF, 1, 3); pump(1)
check(#GOT == 8, "player attacked-only still not emitted")
''', "flow")
run(r'''
-- 8. ожидание одного окна: свежее невиданное дело ждёт, поздний свидетель успевает
DAYV = 12
setnpcs({})
REL(FX, PF, 4, 1)
CLOCK = CLOCK + 1; DD._tick()
check(#GOT == 8 and D.st.held == 1 and DD.stats().pending == 1, "fresh unseen deed held one window: held=" .. D.st.held)
CRIME(FX, 4)
pump(1)
local e = last()
check(#GOT == 9 and e.witnessed == true and e.witness_src == "crime", "late crime witness counts after hold")
-- держится только одно окно
REL(FA, PF, 12, 1)
CLOCK = CLOCK + 1; DD._tick()
check(#GOT == 9 and D.st.held == 2, "held again (new deed)")
CLOCK = CLOCK + 1; DD._tick()
e = last()
check(#GOT == 10 and e.witnessed == false and e.kind == "captured", "hold only once: emitted unseen")
-- 9. старое преступление не в счёт
CRIME(FB, 4)
CLOCK = CLOCK + 40
check(DD.crime_seen(FB) == nil and DD.crime_seen(FB, 1000) == "murder", "crime_seen window")
REL(FB, PF, 6, 1); pump(1)
e = last()
check(#GOT == 11 and e.kind == "executed" and e.witnessed == false, "stale crime ignored: " .. tostring(e.witness_src))
-- фракция преступления не прочиталась -> считается для любой жертвы
CRIME(nil, 7)
REL(FA, PF, 11, 1); pump(1)
e = last()
check(#GOT == 12 and e.witnessed == true and e.crime == "slave_freeing", "unknown-faction crime matches: " .. tostring(e.crime))
''', "hold")
run(r'''
-- 10. фолбэк: нет снимка и нет преступления -> nil (как до Y1); все вызовы чувства упали -> nil
DAYV = 13
local snap0 = KMM_Gov.snapshot
KMM_Gov.snapshot = function() return nil end
REL(FB, PF, 4, 1); pump(1)
local e = last()
check(#GOT == 13 and e.witnessed == nil and e.witness_src == "nosignal", "no snapshot -> nil: " .. tostring(e.witnessed))
KMM_Gov.snapshot = snap0
setnpcs({ NPC("broken1", FA, 100, { sense_err = true }), NPC("broken2", FA, 200, { sense_err = true }) })
REL(FA, PF, 4, 1); pump(1)
e = last()
check(#GOT == 14 and e.witnessed == nil and D.st.sense_err >= 2, "sense errors -> nil")
-- нет персонажей игрока -> nil
local pcs0 = PCS
PCS = {}
setnpcs({ NPC("x", FA, 100, { aware = true }) })
REL(FX, PF, 2, 1); pump(1)
PCS = pcs0
e = last()
check(#GOT == 15 and e.witnessed == nil, "no player chars -> nil")
-- 11. witness=false в конфиге -> поля нет вовсе
D.DEF.witness = false
REL(FX, PF, 12, 1); pump(1)
e = last()
check(#GOT == 16 and e.witnessed == nil and e.witness_src == nil, "witness off -> no field")
D.DEF.witness = true
-- 12. сбой колбэка свидетеля выключает только его
local bad = { }
setmetatable(bad, { __index = function() error("bad bounty manager") end })
local okc = pcall(FIRE, "BountyManager::notifyCrimeWitnessed", bad, FAC(FA), {}, 1, 4)
check(okc and D.crime_off == false, "bad manager read inside pcall: not fatal")
local ci = D.CRIME
D.CRIME = nil   -- индексирование nil -> ошибка внутри колбэка
CRIME(FA, 4)
D.CRIME = ci
check(DD.disabled().deeds_witness == true and not DD.disabled().deeds_hook and not D.off, "witness hook error disables only it")
DAYV = 14
setnpcs({ NPC("seer", FX, 100, { aware = true }) })
REL(FX, PF, 4, 1); pump(1)
e = last()
check(#GOT == 17 and e.witnessed == true and e.witness_src == "sense", "deeds and sense keep working without witness hook: " .. #GOT .. " " .. tostring(e.kind) .. " " .. tostring(e.witnessed) .. " " .. tostring(e.witness_src) .. " cap=" .. DD.stats().capped .. " dup=" .. DD.stats().dup)
local lg = io.open("TMPDIR/deeds.log", "r"); local s = lg and lg:read("*a") or ""; if lg then lg:close() end
check(s:find("witness: notifyCrimeWitnessed hook registered", 1, true) and s:find("crime seen: 4 (murder) against " .. FB, 1, true)
      and s:find("witness: killed " .. PF .. ">" .. FB .. " seen src=crime crime=murder", 1, true)
      and s:find("unseen src=none", 1, true) and s:find("unknown src=nosignal", 1, true)
      and s:find("hook notifyCrimeWitnessed disabled until restart", 1, true), "log markers")
'''.replace("TMPDIR", TMP), "fallback")
# цена: 300 NPC вокруг (снимок прогрет), меряется только сброс Deeds, никто не знает -> не больше wit_max вопросов, время сброса
run(r'''
DAYV = 15
local list = {}
for i = 1, 300 do list[#list + 1] = NPC("n" .. i, FX, (i % 50) * 40, { aware = false }) end
setnpcs(list)
ASKS = 0
REL(FX, PF, 4, 1); CLOCK = CLOCK + 11
KMM_Gov.snapshot(5)   -- общий снимок в игре строят и другие модули (Gov вычитает его цену); здесь меряется только проверка свидетелей
''', "prep")
t0 = time.perf_counter()
run(r'''DD._tick()''', "flush")   # только сброс Deeds (charsUpdate гонял бы и такт дирижёра по 300 NPC)
flush_ms = (time.perf_counter() - t0) * 1000
run(r'''
local e = last()
check(e.witnessed == false and ASKS <= D.DEF.wit_max * D.DEF.wit_pcs, "sense capped: asks=" .. ASKS)
RESULT = #FAILS == 0 and ("OK " .. N .. " checks, deeds=" .. #GOT) or ("FAIL: " .. table.concat(FAILS, "; "))
''', "cost")
r = gstr("RESULT")
budget_ok = flush_ms < 5
print(r, f"| flush with 300 NPC {flush_ms:.2f} ms")
if not budget_ok:
    print("FAIL: cost over budget")
sys.exit(0 if r.startswith("OK") and budget_ok else 1)
