"""Offline test KMM_Outlaws: far simulation (roam within home cluster, racket, bounty growth, justice, replacement), materialization near player, rename, native bounty, death. python -I -X utf8 build/KMM_Conductor/_dev/test_outlaws.py -> OK."""
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
run(r'''
N, FAILS = 0, {}
function check(c, what) N = N + 1; if not c then FAILS[#FAILS + 1] = what end end
local C = KMM_Conductor
C.reset()
local TP = C.cfg().params.traces
TP.first_hour_traces = 0; TP.max_per_day = 1000; TP.max_queue = 1000; TP.arrive_enabled = false
TP.bounty = { enabled = false }
local pf = C.cfg().player_faction
C.cfg().params.outlaws = { watch_s = 1e9, sdir = "TMPDIR/" }
local O, T = KMM_Outlaws, KMM_Traces
MADE = {}
local old = getGameWorld
getGameWorld = function()
  local w = old()
  local orig = w.theFactory.createRandomSquad
  w.theFactory.createRandomSquad = function(self, f, pos, ...)
    local r = orig(self, f, pos, ...)
    local leader = { name = "Nameless Raider", dead = false, bty = {} }
    leader.crimes = { unfairAddToBounty = function(self2, fo, amt) leader.bty[#leader.bty + 1] = { fo, amt } end,
                      getTotalBounty = function(self2) local s = 0; for _, b in ipairs(leader.bty) do s = s + b[2] end; return s end }
    function leader:setName(n) self.name = n end
    function leader:getName() return self.name end
    function leader:isDead() return self.dead end
    local pl = { isDead = false }
    function pl:getSquadLeader() return leader end
    function pl:getActivePlatoon() return { setName = function() end } end
    MADE[#MADE + 1] = { pl = pl, leader = leader, x = pos.x, z = pos.z, fid = f.id }
    return pl
  end
  if not w.factionMgr then w.factionMgr = {} end
  if not w.factionMgr.getFactionByStringID then w.factionMgr.getFactionByStringID = function(self, sid) return { id = sid } end end
  return w
end
PCS = {}; CHARS = {}
local pc = MKCH("PC1", pf or "player", 0, 0, { player = true, platoon = "player_squad" })
PCS[1] = pc; CHARS[1] = pc
local function tick(day) DAYV = day; CLOCK = CLOCK + 100; FIRE("GameWorld::charsUpdate", {}) end
local function evcount(prefix) local n = 0; for _, e in ipairs(C.state().events) do if tostring(e.type):sub(1, #prefix) == prefix then n = n + 1 end end; return n end
local function nw() local n = 0; for _ in pairs(O.state().L) do n = n + 1 end; return n end
local function ser(t, d)
  d = d or 0; if type(t) ~= "table" then return tostring(t) end
  local o = {}; for k, v in pairs(t) do o[#o + 1] = tostring(k) .. "=" .. ser(v, d + 1) end; return "{" .. table.concat(o, ",") .. "}"
end
local D = O._M.data(C)
check(D and #D.homes >= 5, "outlaws.json loaded, homes: " .. tostring(D and #D.homes))
OEV = {}
ADOPTED = 0
local _ad = KMM_Fates.adopt
KMM_Fates.adopt = function(o) local h = _ad(o); if h and h.n == o.n and h.r == "mercenary" then ADOPTED = ADOPTED + 1 end; return h end
C.subscribe("*", function(ev) if tostring(ev.type):sub(1, 7) == "outlaw_" then OEV[#OEV + 1] = ev end end)
-- 1) посев
tick(500)
check(O.state() and nw() == 10, "seeded 10 outlaws: " .. tostring(O.state() and nw()))
local okf = true
for _, o in ipairs(O.wanted()) do if not (o.n and o.g and o.hr and o.r and o.x and o.b and o.b > 0 and o.lf and D.regions[o.hr]) then okf = false end end
check(okf, "outlaw fields complete")
local homegang = true
for _, o in ipairs(O.wanted()) do local ok = false; for _, g in ipairs(D.regions[o.hr].gangs) do if g == o.g then ok = true end end; if not ok then homegang = false end end
check(homegang, "gang is native to home region at birth")
-- 2) 300 дней мира
local strays = 0
for d = 501, 800 do
  tick(d)
  for _, o in ipairs(O.wanted()) do if not O._M.cluster(D, o)[o.r] then strays = strays + 1 end end
end
check(next(O.disabled()) == nil, "still enabled after 300 days")
check(strays == 0, "nobody roams outside home+adjacent regions: " .. strays)
local st = O.stats()
check(st.racket > 0 and st.raid > 0 and st.roam > 0, "racket/raid/roam happened: " .. st.racket .. "/" .. st.raid .. "/" .. st.roam)
check(st.dead > 0 and st.born > 10, "world justice kills and replacements: dead=" .. st.dead .. " born=" .. st.born)
check(st.jail > 0, "someone jailed: " .. st.jail)
check((st.hunted or 0) > 0, "Fates mercenary collected a bounty: " .. tostring(st.hunted))
local hev = false; for _, e in ipairs(OEV) do if e.type == "outlaw_dead" and tostring(e.text):find("collected the bounty", 1, true) then hev = true end end
check(hev, "hunter named in outlaw_dead rumor")
check(st.rise > 0, "someone rose in tier: " .. st.rise)
check(nw() + #O.state().q >= 10 and nw() <= 10, "roster kept at 10 (incl. queue): " .. nw() .. "+" .. #O.state().q)
check(#OEV >= 10, "outlaw_* events: " .. #OEV)
local tys = {}; for _, e in ipairs(OEV) do tys[e.type] = (tys[e.type] or 0) + 1 end
check((tys.outlaw_manhunt or 0) > 0 and (st.manhunt or 0) > 0, "manhunt happened: " .. tostring(st.manhunt))
-- найм ветерана вероятностный, а ход симуляции зависит от os.clock-троттлинга: проверяем инвариант, а не факт найма
if (st.hired or 0) > 0 then
  check((tys.outlaw_hired or 0) > 0, "a veteran outlaw hired into a faction: " .. tostring(st.hired))
  check(ADOPTED == st.hired, "hired outlaw became a Fates hero: " .. ADOPTED)
else
  print("NOTE: no veteran hired in this run (probabilistic)")
  check(ADOPTED == 0, "no hire -> no Fates adoption: " .. ADOPTED)
end
local ev; for i = #C.state().events, 1, -1 do local e = C.state().events[i]; if tostring(e.type):sub(1, 7) == "outlaw_" then ev = e; break end end
check(ev and ev.text and #ev.text > 10 and ev.leader_name, "event has text + leader_name")
check((st.epithet or 0) > 0 and (tys.outlaw_epithet or 0) > 0, "earned epithets: " .. tostring(st.epithet))
local epok = true; for _, e in ipairs(OEV) do if e.type == "outlaw_epithet" and not (e.old_name and e.leader_name ~= e.old_name and e.leader_name:match("^%S+") == e.old_name:match("^%S+")) then epok = false end end
check(epok, "epithet keeps the given name, changes the nickname")
local seen = {}; local dupe = false; for _, o in ipairs(O.wanted()) do if seen[o.n] then dupe = true end; seen[o.n] = true end
check(not dupe, "no duplicate names on the roster")
local sz = #ser(O.state())
check(sz < 12000, "state size < 12KB: " .. sz)
-- 3) материализация у игрока + родная награда
local ws = O.wanted()
local hero
for _, o in ipairs(ws) do if o.st == "a" then hero = o; break end end
for _, o in ipairs(ws) do if o ~= hero then o.x = (o.x or 0) + 9e6 end end
hero.sp = -1000
O._M.live = {}; O._M.pend = nil
PCS = {}; CHARS = {}
pc = MKCH("PC1", pf or "player", hero.x + 300, hero.z + 300, { player = true, platoon = "player_squad" })
PCS[1] = pc; CHARS[1] = pc
local base = (T.stats().by_tag or {}).outlaw or 0
local function on() return ((T.stats().by_tag or {}).outlaw or 0) - base end
local function mine() for i = #MADE, 1, -1 do local m = MADE[i]; if m.leader.name == hero.n then return m end end end
for i = 1, 40 do tick(800); if on() > 0 then break end; CLOCK = CLOCK + 80 end
for i = 1, 40 do CLOCK = CLOCK + 80; FIRE("GameWorld::charsUpdate", {}) end
check(on() == 1, "outlaw gang requested once: " .. on())
local made = mine()
check(made ~= nil, "leader renamed to " .. hero.n)
check(made and #made.leader.bty >= 1 and made.leader.crimes:getTotalBounty() >= 100, "native bounty applied: " .. tostring(made and #made.leader.bty))
-- 3b) заслуженное прозвище у живого отряда: имя главаря меняется сразу, гибелью это не считается
local ns0 = O.stats().slain
hero.ek = nil; hero.cr = hero.cr or {}; hero.cr.escape = 1
local oldn = hero.n
check(O._M.earn(C, D, hero) and hero.n ~= oldn, "epithet earned: " .. oldn .. " -> " .. hero.n)
check(made and made.leader.name == hero.n, "live leader renamed in place: " .. tostring(made and made.leader.name))
for i = 1, 5 do CLOCK = CLOCK + 80; FIRE("GameWorld::charsUpdate", {}) end
check(O.stats().slain == ns0 and O.state().L["o" .. hero.i], "rename is not a death")
-- 4) гибель
local nd = O.stats().slain
if not made then made = { leader = {} } end
made.leader.dead = true
for i = 1, 5 do CLOCK = CLOCK + 80; FIRE("GameWorld::charsUpdate", {}) end
check(O.stats().slain == nd + 1, "slain recorded")
check(not O.state().L["o" .. hero.i], "outlaw removed after leader death")
check(#O.state().q >= 1, "replacement queued")
-- 5) облава рядом с игроком -> патруль закона
local lawf; for fid, e in pairs(D.tr) do if e.tiers and e.tiers.T1 then lawf = fid; break end end
O.state().hunt = { test = { u = 99999, r = "x", lf = lawf, x = hero.x + 200, z = hero.z + 200, tn = "Testtown", oi = -1 } }
O._M.pend = nil
local mb = (T.stats().by_tag or {}).manhunt or 0
for i = 1, 30 do CLOCK = CLOCK + 80; FIRE("GameWorld::charsUpdate", {}) end
check(((T.stats().by_tag or {}).manhunt or 0) == mb + 1, "manhunt patrol requested once near player")
-- 6) Y5/M6: соперник недавно отошёл -> отряд охоты не шлём (без Nemesis/функции/при ошибке - как раньше); Y1: дело игрока без свидетелей
local Mo = O._M
local nm0 = rawget(_G, "KMM_Nemesis")
local rec = { pg = {} }
KMM_Nemesis = { withdrew_recent = function(x) return x == rec end }
check(Mo.withdrew(rec) == true and Mo.withdrew({ pg = {} }) == false and Mo.withdrew({}) == false, "withdrew: only that rival")
KMM_Nemesis = { withdrew_recent = function() error("x") end }
check(Mo.withdrew(rec) == false, "withdrew error -> old behaviour")
KMM_Nemesis = {}
check(Mo.withdrew(rec) == false, "no withdrew_recent -> old behaviour")
KMM_Nemesis = nm0
local d0 = Mo.stats.deed_unwitnessed or 0
Mo.on_deed_g({ type = "deed", kind = "killed", by_player = true, witnessed = false, a = "x", b = "y" })
check((Mo.stats.deed_unwitnessed or 0) == d0 + 1 and not Mo.deed_off, "unwitnessed player deed skipped")
RESULT = #FAILS == 0 and ("OK " .. N) or ("FAIL: " .. table.concat(FAILS, "; "))
'''.replace("TMPDIR", TMP), "test")
run("")
L.lua_getfield.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_char_p]
L.lua_getfield(st, -10002, b"RESULT")
r = L.lua_tolstring(st, -1, None).decode()
print(r)
sys.exit(0 if r.startswith("OK") else 1)
