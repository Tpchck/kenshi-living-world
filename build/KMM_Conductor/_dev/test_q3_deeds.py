"""Offline test Q3: KMM_Nemesis — потребитель шины дел ядра (KMM_Deeds, type="deed"). Фракция помогла игроку -> родная память помощника (LT_FRIENDLY_AQUAINTANCE через KMM_Native), реплика, долг игрока или возврат долга перед ним; игрок навредил хозяину города -> город помнит (greet раз, town_talk не повторяет); неблагодарность; ванильные реплики sendDialogEvent с фолбэком на свою строку. python -I -X utf8 build/KMM_Conductor/_dev/test_q3_deeds.py -> OK."""
import ctypes, re, sys, tempfile

DLL = r"C:\Program Files (x86)\Steam\steamapps\workshop\content\233860\3817000612\lua51.dll"
B = r"C:\KenshiModMap\build\KMM_Conductor\scripts\init"
TMP = tempfile.mkdtemp(prefix="kmm_outlaws_").replace("\\", "/")
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
run(open(B + r"\KMM_Fates.lua", encoding="utf-8").read(), "KMM_Fates.lua")
run(open(B + r"\KMM_Outlaws.lua", encoding="utf-8").read(), "KMM_Outlaws.lua")
run(open(B + r"\KMM_Nemesis.lua", encoding="utf-8").read(), "KMM_Nemesis.lua")
run(r'''
N, FAILS = 0, {}
function check(c, what) N = N + 1; if not c then FAILS[#FAILS + 1] = what end end
local C = KMM_Conductor
C.reset()
local pf = C.cfg().player_faction
C.cfg().params.outlaws = { watch_s = 1e9, sdir = "TMPDIR/", spawn_p = 1, cd_h = 0, native_bounty = false }
C.cfg().params.nemesis = { say_delay_s = 1, ambient = false, help_min_days = 1 }
local NM = KMM_Nemesis
local NN = NM._N
local LOG = {}
local log0 = NN.log
NN.log = function(m) LOG[#LOG + 1] = tostring(m); log0(m) end
local function logged(s) for _, l in ipairs(LOG) do if l:find(s, 1, true) then return true end end return false end
local MEM = {}
KMM_Native = { has_memory = function() return true end, remember_lt = function(npc, who, tag) MEM[#MEM + 1] = { npc = npc, tag = tag }; return true end }
local S = C.state()
local tsid, owner, I
for _, t in ipairs(C.towns()) do if t.owner and t.owner ~= pf and t.x then tsid, owner, I = t.sid, t.owner, t; break end end
check(tsid ~= nil, "a town with a non-player owner")
local other; for fid in pairs(S.F) do if fid ~= owner and fid ~= pf then other = fid; break end end
local TOWNOBJ = { getGameData = function() return { stringID = tsid } end }
local INTOWN = false
local pc = MKCH("Beep", pf or "player", I.x + 100, I.z + 100, { player = true, platoon = "player_squad" })
pc.said = {}; function pc:say(s) self.said[#self.said + 1] = s end
function pc:getCurrentTownLocation() return INTOWN and TOWNOBJ or nil end
PCS = { pc }; CHARS = { pc }
local function npc(nm, fid, dx)
  local c = MKCH(nm, fid, I.x + 100 + dx, I.z + 100, {})
  c.said = {}; function c:say(s) self.said[#self.said + 1] = s end
  return { ch = c, x = I.x + 100 + dx, z = I.z + 100, dead = false, town = true, fid = fid }
end
local guard, helper = npc("Gate Guard", owner, 300), npc("Shek Scout", other, 200)
local LIST = { guard, helper }
KMM_Gov = { snapshot = function() return { list = LIST } end }
local mood0 = C.town_mood
C.town_mood = function(sid) return { owner = owner, unrest = 0, pop = 100, pop0 = 100 } end
local REL0 = C.rel; C.rel = function() return 0 end
local DAY = 500
local function fire(dt) CLOCK = CLOCK + dt; FIRE("GameWorld::charsUpdate", {}) end
DAYV = DAY; fire(100)
check(logged("deeds: subscribed to deed bus"), "subscribed to the deed bus from the tick")
local function deed(t) t.type = "deed"; t.x = t.x or I.x + 100; t.z = t.z or I.z + 100; C.emit(t) end
local function flush() CLOCK = CLOCK + 5; NN.flush_said() end

-- (1) фракция помогла игроку, долга перед игроком нет -> игрок должен, помощник помнит и говорит
deed({ kind = "aided", tone = "help", a = other, b = pf, to_player = true, town_sid = tsid, town_name = "Town" })
flush()
local o = NM.owe()[other]
check(o and o.n == 1 and o.kind == "aided", "player owes the helping faction")
check(#MEM == 1 and MEM[1].npc == helper.ch and MEM[1].tag == 6, "helper remembers the player: LT_FRIENDLY_AQUAINTANCE=6 via native")
local hl = helper.ch.said[1]
local inset = false; for _, l in ipairs(NN.SAY.aid_owe) do if l == hl then inset = true end end
check(inset and logged("aid_said: ") and logged("deed_owed: "), "helper line from aid_owe: " .. tostring(hl))
deed({ kind = "killed_enemy", tone = "help", a = other, b = pf, to_player = true })
flush()
check(NM.owe()[other].n == 2 and #helper.ch.said == 1 and #MEM == 1, "second help same day: counted, no repeat line/memory")
local nd = 0; for _, d in ipairs(NM.deeds()) do if d.k == "deed_owed" then nd = nd + 1 end end
check(nd == 1, "owed deed recorded once for the town to remember")

-- (1b) у фракции уже есть долг перед игроком -> вернула его делом
local X = NN.state(S)
X.debts = { [owner .. "|Kog"] = { n = "Kog", orig = "Kog", fid = owner, deed = "healed", place = "Squin", day = DAY - 3 } }
local nr = #S.events
deed({ kind = "first_aid", tone = "help", a = owner, b = pf, to_player = true })
flush()
local rep; for i = nr + 1, #S.events do if S.events[i].type == "debt_repaid" then rep = S.events[i] end end
check(X.debts[owner .. "|Kog"].paid == DAY and rep and rep.via == "first_aid", "existing debt repaid by the deed")
check(guard.ch.said[1] and guard.ch.said[1]:find("Kog", 1, true) and NM.owe()[owner] == nil, "debtor faction says aid_even, player owes nothing: " .. tostring(guard.ch.said[1]))

-- (2) игрок убил людей хозяина города -> город помнит: greet раз, town_talk не повторяет
deed({ kind = "killed", tone = "harm", a = pf, b = owner, by_player = true, town_sid = tsid, town_name = "Town" })
local dk; for _, d in ipairs(NM.deeds()) do if d.k == "deed_killed" then dk = d end end
check(dk and dk.gk == "killed" and dk.fid == owner and dk.tsid == tsid and logged("deed_town: killed"), "town deed recorded")
deed({ kind = "defeated", tone = "harm", a = pf, b = "nobody_owns_this", by_player = true, town_sid = tsid })
local bad = false; for _, d in ipairs(NM.deeds()) do if d.fid == "nobody_owns_this" then bad = true end end
check(not bad, "harm against a non-owner faction: town does not record it")
local ng = #guard.ch.said
INTOWN = false; fire(5); DAY = DAY + 1; DAYV = DAY; fire(100); INTOWN = true; fire(5); fire(30); fire(5); fire(5)
local gl = guard.ch.said[#guard.ch.said]
local ing = false; for _, l in ipairs(NN.GREET.deed.killed) do if l == gl then ing = true end end
check(#guard.ch.said == ng + 1 and ing and dk.said == DAY, "greet: owner's resident names the killing: " .. tostring(gl))
for i = 1, 6 do fire(130) end
local ndk = 0
for _, l in ipairs(guard.ch.said) do for _, f in ipairs(NN.TALK.deed_killed) do if l == string.format(f, C.name(owner)) then ndk = ndk + 1 end end end
check(ndk == 0, "town_talk does not repeat the deed greet already told")

-- (3) неблагодарность: ударил фракцию, которой должен
check(NM.owe()[other] ~= nil, "still owes the helper faction")
deed({ kind = "defeated", tone = "harm", a = pf, b = other, by_player = true })
local di; for _, d in ipairs(NM.deeds()) do if d.k == "deed_ingrate" then di = d end end
check(NM.owe()[other] == nil and di and logged("deed_ingrate: "), "ingratitude recorded, debt dropped")
X.owe = { [other] = { fid = other, day = DAY, n = 1 } }
deed({ kind = "first_aid", tone = "help", a = pf, b = other, by_player = true })
check(NM.owe()[other] == nil and logged("deed_owed_repaid"), "player repaid by helping back")
X.owe = { [other] = { fid = other, day = DAY - 40, n = 1 } }
NN.owe_day(S, DAY); check(NM.owe()[other] == nil, "old debt forgotten")

-- (4) ванильные реплики: sendDialogEvent -> true / false / ошибка
local sp = npc("Rival", other, 50).ch
local SENT = {}
function sp:sendDialogEvent(tgt, what) SENT[#SENT + 1] = { tgt, what }; return self.ans end
sp.ans = true
NN.said[#NN.said + 1] = { leader = sp, line = "own line", t = CLOCK, ev = "EV_BOUNTY_SPOTTED" }
flush()
check(#SENT == 1 and SENT[1][1] == pc and SENT[1][2] == 44 and #sp.said == 0 and logged("said_ev: EV_BOUNTY_SPOTTED"), "vanilla line used, own line not said")
sp.ans = false
NN.said[#NN.said + 1] = { leader = sp, line = "own line", t = CLOCK, ev = "EV_I_SEE_ENEMY_PLAYER" }
flush()
check(#SENT == 2 and sp.said[1] == "own line" and logged("not answered by dialogue package"), "vanilla not answered -> own line")
function sp:sendDialogEvent() error("boom") end
for i = 1, 4 do NN.said[#NN.said + 1] = { leader = sp, line = "own " .. i, t = CLOCK, ev = "EV_I_SEE_ENEMY_PLAYER" }; flush() end
check(#sp.said == 5 and logged("own lines only until restart") and (NN.ev_fail or 0) == 3, "errors -> own lines, vanilla path off after the cap")
NN.ev_fail = 0
local o2 = { n = "Kadan Sandscar", pg = { deed = "spared", place = "Squin", met = 1 } }
local cnt = #NN.said
NN.on_spawn(o2, sp)
check(NN.said[cnt + 1] and NN.said[cnt + 1].ev == nil, "first meeting after the deed: own contextual line")
local cnt2 = #NN.said
NN.on_spawn(o2, sp)
local rep; for i = cnt2 + 1, #NN.said do if NN.said[i].leader == sp then rep = NN.said[i] end end   -- реплика банды игрока (banter) может встать следом
check(rep and rep.ev == "EV_I_SEE_ENEMY_PLAYER", "repeat meeting: vanilla enemy line")
o2.pg.met = 2; NN.on_spawn(o2, sp)
check(NN.said[#NN.said].ev == nil, "new deed (spared again): own line once more")
NN.said = {}

-- (4b) Y1: witnessed == false -> ни памяти города, ни неблагодарности; true -> как раньше
local function ndeeds(k) local n = 0; for _, d in ipairs(NM.deeds()) do if d.k == k then n = n + 1 end end; return n end
local nk0 = ndeeds("deed_killed")
deed({ kind = "killed", tone = "harm", a = pf, b = owner, by_player = true, town_sid = tsid, town_name = "Town", witnessed = false })
check(ndeeds("deed_killed") == nk0 and logged("deed_unseen: killed"), "unwitnessed harm: town does not remember")
X.owe = { [other] = { fid = other, day = DAY, n = 1 } }
local ni0 = ndeeds("deed_ingrate")
deed({ kind = "defeated", tone = "harm", a = pf, b = other, by_player = true, witnessed = false })
check(ndeeds("deed_ingrate") == ni0 and NM.owe()[other] ~= nil, "unwitnessed harm to a helper: no ingrate, debt stays")
deed({ kind = "defeated", tone = "harm", a = pf, b = other, by_player = true, witnessed = true })
check(ndeeds("deed_ingrate") == ni0 + 1 and NM.owe()[other] == nil, "witnessed harm to a helper: ingrate as before")
deed({ kind = "killed", tone = "harm", a = pf, b = owner, by_player = true, town_sid = tsid, town_name = "Town", witnessed = true })
check(ndeeds("deed_killed") == nk0 + 1, "witnessed harm: town remembers as before")
X.owe = nil

-- (5) ошибка в потребителе выключает только его
local nmf = NN.fname; NN.fname = function() error("x") end
deed({ kind = "killed", tone = "harm", a = pf, b = owner, by_player = true, town_sid = tsid })
NN.fname = nmf
check(NM.deeds_off() == true and logged("deeds disabled until restart"), "consumer error disables only the deed consumer")
check(next(NM.disabled()) == nil, "nemesis still enabled")
C.town_mood, C.rel = mood0, REL0
RESULT = #FAILS == 0 and ("OK " .. N) or ("FAIL: " .. table.concat(FAILS, "; "))
'''.replace("TMPDIR", TMP), "test")
run("")
L.lua_getfield.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_char_p]
L.lua_getfield(st, -10002, b"RESULT")
r = L.lua_tolstring(st, -1, None).decode()
print(r)
sys.exit(0 if r.startswith("OK") else 1)
