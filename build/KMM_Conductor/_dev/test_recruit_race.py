"""Offline test KMM_RecruitRace (V1): выбор бар-рекрута, намёки, перенос к rival-фракции (setFaction + постоянный отряд + пакет),
отмена наймом игрока (хук и запасной путь), лимит недели, провал пробы -> самоотключение, крэш-сторож, промахи, сироты, смена мира.
Стабы — свои (без дирижёра). python -I -X utf8 build/KMM_Conductor/_dev/test_recruit_race.py -> OK."""
import ctypes, os, sys, tempfile

DLL = r"C:\Program Files (x86)\Steam\steamapps\workshop\content\233860\3817000612\lua51.dll"
MOD = r"C:\KenshiModMap\build\KMM_Conductor\scripts\init\KMM_RecruitRace.lua"
TMP = tempfile.mkdtemp(prefix="kmm_rrace_").replace("\\", "/") + "/"
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
    code = code.replace('"TMP"', '"' + TMP + '"')
    if L.luaL_loadstring(st, code.encode("utf-8")) or L.lua_pcall(st, 0, 0, 0):
        msg = L.lua_tolstring(st, -1, None)
        raise RuntimeError(f"{name}: {msg.decode('utf-8', 'replace') if msg else '?'}")


STUBS = r'''
math.randomseed(20261115)
EV = {}
Events = { on = function(name, fn) EV[name] = fn; return #name end }
itemType = { SQUAD_TEMPLATE = 52, AI_PACKAGE = 72 }
HOURS = 100
EVENTS = {}
NPK = 0
FAIL_SETFACTION = false
-- платуны и фракции
function MKPL(fac, key)
  NPK = NPK + 1
  local pl = { key = key or ("PK" .. NPK), persistent = false, chars = {}, fac = fac, isDead = false, pkg = nil }
  pl.ap = { me = pl }
  pl.getPlatoonStringID = function(self) return self.key end
  pl.isPersistentSquad = function(self) return self.persistent end
  pl.setPersistentSquad = function(self, on) self.persistent = on end
  pl.getActivePlatoon = function(self) return self.ap end
  pl.getBlackboard = function(self) return { replaceAIPackage = function(_, gd) self.pkg = gd end } end
  pl.getCharacterCount = function(self) local n = 0; for _ in pairs(self.chars) do n = n + 1 end; return n end
  return pl
end
FACS = {}
function MKFAC(id)
  local f = { id = id, active = {}, unloaded = {} }
  f.getData = function(self) return { stringID = self.id } end
  f.getActivePlatoons = function(self) return self.active end
  f.getUnloadedPlatoons = function(self) return self.unloaded end
  f.createNewEmptyActivePlatoon = function(self, tpl, perm, pos)
    local pl = MKPL(self); pl.tpl = tpl; pl.permanent = perm; self.active[#self.active + 1] = pl; LAST_PL = pl; return pl
  end
  FACS[id] = f
  return f
end
DRIFT = MKFAC("51707-rebirth.mod"); MKFAC("1233-gamedata.base"); MKFAC("BAR"); MKFAC("PF")
GD = { ["2206-gamedata.base"] = { stringID = "2206-gamedata.base" }, ["2675-gamedata.base"] = { stringID = "2675-gamedata.base" } }
WORLD = {
  getTimeStamp_inGameHours = function() return { getTotalHours = function() return HOURS end } end,
  factionMgr = { getFactionByStringID = function(_, id) return FACS[id] end },
  gamedata = { getData = function(_, sid, t) return GD[sid] end },
}
function getGameWorld() return WORLD end
-- персонажи
-- M6: хендл по значению — новый userdata-объект на каждый вызов; ключ только через :toString(), tostring() — адрес (как в игре)
HMT = { __index = { toString = function(self) return self.s end } }
function HND(s) if s == nil then return nil end; return setmetatable({ s = s }, HMT) end
CHARS = {}
TOWN = { getName = function() return "Squin" end }
function MKCH(o)
  local ch = { name = o.name, h = o.h, fac = FACS[o.fac or "BAR"], x = o.x or 0, z = o.z or 0, dead = false, skill = o.skill or 30,
               unique = o.unique or false, slave = o.slave or 0, player = false, said = {}, tname = o.tname or "Recruits list", town = (o.town ~= false) and TOWN or false,
               down = false, combat = false }
  ch.pl = MKPL(ch.fac, o.pkey); ch.pl.squadTemplate = { name = ch.tname }; ch.ap = ch.pl.ap; ch.pl.chars[ch] = true
  ch.getName = function(self) return self.name end
  ch.getHandle = function(self) return HND(self.h) end
  ch.isDead = function(self) return self.dead end
  ch.isPlayerCharacter = function(self) return self.player end
  ch.isUnique = function(self) return self.unique end
  ch.isSlave = function(self) return self.slave end
  ch.getStats = function(self) return { getOverallSkillLevel_0_100 = function() return self.skill end } end
  ch.say = function(self, s) self.said[#self.said + 1] = s end
  ch.getPosition = function(self) return { x = self.x, y = 0, z = self.z } end
  ch.getFaction = function(self) return self.fac end
  ch.getPlatoon = function(self) return self.ap end
  ch.setFaction = function(self, f, ap)
    if SF_THROW then error("setFaction boom") end
    if FAIL_SETFACTION then return end
    self.fac = f
    if DELAY_AP then return end
    if self.ap and self.ap.me then self.ap.me.chars[self] = nil end
    self.ap = ap; ap.me.chars[self] = true
  end
  CHARS[#CHARS + 1] = ch
  return ch
end
-- игрок
PC = { player = true, h = "PC1", intown = true }
PC.getPosition = function(self) return { x = 100, y = 0, z = 100 } end
PC.getCurrentTownLocation = function(self) if self.intown then return TOWN end return nil end
PC.getHandle = function(self) return HND(self.h) end
PCS = { PC }
function getPlayerInterface() return { getAllPlayerCharacters = function() return PCS end } end
-- снимок Gov
SNAP_ERR = false
KMM_Gov = { run = function(name, fn, ...) return fn(...) end, snapshot = function()
  if SNAP_ERR then error("snapshot boom") end
  local list, by = {}, {}
  for _, ch in ipairs(CHARS) do
    if not ch.player then
      local fd = ch.fac and ch.fac:getData()
      local r = { ch = ch, x = ch.x, z = ch.z, fid = fd and fd.stringID, dead = ch.dead, pkey = ch.ap.me.key, tsid = "T:" .. ch.tname, pl = ch.ap.me,
                  town = ch.town, down = ch.down, unique = ch.unique, h = tostring(HND(ch.h)), combat = ch.combat }
      list[#list + 1] = r
      by[r.pkey] = by[r.pkey] or {}; table.insert(by[r.pkey], r)
    end
  end
  return { list = list, by_pkey = by, n = #list }
end }
-- дирижёр
S = { ext = {} }
KMM_Conductor = { state = function() return S end, emit = function(ev) EVENTS[#EVENTS + 1] = ev end, day = function() return HOURS / 24 end,
  name = function(fid) if fid == "51707-rebirth.mod" then return "Drifters" end return fid end, cfg = function() return { player_faction = "PF" } end }
N, FAILS = 0, {}
function check(c, what) N = N + 1; if not c then FAILS[#FAILS + 1] = what end end
function readlog() local f = io.open(TMP .. "recruitrace.log", "r"); if not f then return "" end; local s = f:read("*a"); f:close(); return s end
function has(s, pat) return s:find(pat, 1, true) ~= nil end
function evn(t) local n = 0; for _, e in ipairs(EVENTS) do if e.type == t then n = n + 1 end end; return n end
'''.replace("TMP .. ", f'"{TMP}" .. ')
run(STUBS, "stubs")
run(open(MOD, encoding="utf-8").read(), "KMM_RecruitRace.lua")
run(r'''
local M = KMM_RecruitRace
local P = M.P
P.log = "TMP" .. "recruitrace.log"; P.sdir = "TMP"
P.start_s, P.tick_s, P.pick_s, P.house_s = 0, 0, 0, 0
local tick = function() M.last = nil; M.rt.pick = nil; M.rt.house = nil; EV["GameWorld::charsUpdate"]() end
check(EV["GameWorld::charsUpdate"] ~= nil, "charsUpdate registered (guarded)")
-- кандидаты: лучший по навыку среди допустимых
local a = MKCH({ name = "Weak", h = "H1", skill = 20, x = 200, z = 200 })
local b = MKCH({ name = "Kang", h = "H2", skill = 40, x = 300, z = 100 })
MKCH({ name = "Ruka", h = "H3", skill = 90, unique = true, x = 100, z = 300 })
MKCH({ name = "Slave", h = "H4", skill = 80, slave = 1, x = 100, z = 200 })
MKCH({ name = "Drunk", h = "H5", skill = 99, tname = "Bar flies", x = 150, z = 150 })
MKCH({ name = "Far", h = "H6", skill = 95, x = 90000, z = 90000 })
MKCH({ name = "Mine", h = "H7", skill = 97, fac = "PF", x = 120, z = 120 })
MKCH({ name = "NoTown", h = "H8", skill = 96, town = false, x = 130, z = 130 })
MKCH({ name = "Jail", h = "H9", skill = 98, tname = "Recruits list imprisoned", x = 130, z = 130 })
tick()
local R = S.ext.recruitrace
check(R and R.race and R.race.h == "H2", "race on best eligible recruit (got " .. tostring(R and R.race and R.race.name) .. ")")
check(#b.said == 1 and not has(b.said[1], "%"), "start hint said by recruit")
check(R.race.fid == "51707-rebirth.mod", "rival = Drifters")
check(has(readlog(), "race start Kang"), "marker race start")
check(EV["PlayerInterface::recruit"] ~= nil and M.hooked == true, "recruit hook registered lazily")
-- только одна гонка
local r1 = R.race; tick(); check(R.race == r1, "one race at a time")
-- намёк на середине срока
HOURS = (R.race.t0 + R.race.t1) / 2 + 0.1; tick()
check(#b.said == 2 and R.race.half, "half-time hint")
tick(); check(#b.said == 2, "half hint once")
-- истечение -> перенос
DELAY_AP = true   -- ключ платуна обновляется не сразу (ревью batch5 M8б): не провал, а подтверждение позже
HOURS = R.race.t1 + 0.1; tick()
check(R.pend and R.race == nil and not has(readlog(), "setFaction ok") and not has(readlog(), "setFaction FAIL"), "setFaction pending confirmation")
check(LAST_PL.permanent == false and LAST_PL.persistent == false, "new platoon temporary until confirmed")
tick(); check(R.pend and R.pend.tries == 1 and M.off == false, "key not yet updated: still pending, module on")
DELAY_AP = false; b.ap.me.chars[b] = nil; b.ap = LAST_PL.ap; LAST_PL.chars[b] = true
tick()
local log = readlog()
check(has(log, "setFaction ok Kang") and R.pend == nil, "marker setFaction ok after confirmation")
check(b.fac == DRIFT and b.ap.me == LAST_PL, "recruit moved to Drifters platoon")
check(LAST_PL.persistent and has(log, "persistent ok Kang"), "squad persistent after confirmation")
check(LAST_PL.pkg and LAST_PL.pkg.stringID == "2675-gamedata.base" and has(log, "package ok"), "wandering package set")
check(evn("recruit_taken") == 1 and has(EVENTS[#EVENTS].text, "Drifters hired Kang") and has(EVENTS[#EVENTS].text, "Squin"), "recruit_taken event with text")
check(has(b.said[#b.said], "Drifters"), "taken line said")
check(R.race == nil and #R.taken == 1 and R.taken[1].pk == LAST_PL.key and R.last_take_h, "taken record with key")
-- лимит недели: новая гонка не раньше last_take + week - race_h[2]
local lt = R.last_take_h
HOURS = lt + 30; tick(); check(R.race == nil, "no race right after loss (cooldown/week)")
HOURS = lt + P.week_h - P.race_h[2] + 1; tick()
check(R.race and R.race.h == "H1" and R.race.t1 >= lt + P.week_h, "next race allowed, ends no earlier than a week after loss")
-- отмена наймом игрока (хук)
EV["PlayerInterface::recruit"](nil, a, false); tick()
check(R.race == nil and evn("recruit_kept") == 1 and has(readlog(), "recruit cancel by player Weak"), "cancel by player via hook")
-- запасной путь: рекрут уже среди персонажей игрока
R.next_h = nil; R.last_take_h = -1e9; HOURS = HOURS + 1; tick()
check(R.race and R.race.h == "H1", "race again on Weak")
a.player = true; PCS[2] = a; tick()
check(R.race == nil and evn("recruit_kept") == 2, "cancel by roster fallback")
PCS[2] = nil; a.player = false; a.dead = true
-- забранный рекрут (уже у искателей) кандидатом не становится
R.next_h = nil; R.last_take_h = -1e9; HOURS = HOURS + 1; tick()
check(R.race == nil, "taken recruit (rival faction) not raced again")
-- промахи: рекрут выгружен -> гонка снята
local c = MKCH({ name = "Gone", h = "H10", skill = 50, x = 110, z = 110 })
R.next_h = nil; tick()
check(R.race and R.race.h == "H10", "race on Gone")
for i, ch in ipairs(CHARS) do if ch == c then table.remove(CHARS, i) end end
for i = 1, P.lapse_miss do tick() end
check(R.race == nil and has(readlog(), "race lapsed"), "race lapsed after misses")
-- сироты: переполнение persist_max -> старейший в сироты, уборка отпускает его
R.taken = {}
for i = 1, P.persist_max do local pl = MKPL(DRIFT, "OLD" .. i); pl.persistent = true; pl.chars[{}] = true; DRIFT.active[#DRIFT.active + 1] = pl; R.taken[i] = { n = "old" .. i, f = DRIFT.id, pk = "OLD" .. i, d = 1 } end
local d = MKCH({ name = "Eighth", h = "H11", skill = 60, x = 105, z = 105 })
R.next_h = nil; R.last_take_h = -1e9; tick()
HOURS = R.race.t1 + 1; tick(); tick()
check(has(readlog(), "persistent FAIL Eighth: cap"), "cap: new squad stays temporary")
check(#R.taken == P.persist_max and #R.orph == 1 and R.orph[1].k == "OLD1", "oldest moved to orphans")
local old1; for i, p in ipairs(DRIFT.active) do if p.key == "OLD1" then old1 = p; table.remove(DRIFT.active, i); break end end
DRIFT.unloaded[1] = old1; tick()
check(#R.orph == 1 and old1.persistent == true, "unloaded orphan not released (waits for load)")
DRIFT.unloaded = {}; DRIFT.active[#DRIFT.active + 1] = old1; tick()
check(#R.orph == 0 and old1.persistent == false and has(readlog(), "orphan released old1"), "orphan released")
-- сгинувший отряд записи -> отпущен
local t2 = R.taken[1]; local p2
for _, p in ipairs(DRIFT.active) do if p.key == t2.pk then p2 = p end end
p2.chars = {}; R.hi = 0; tick()
check(t2.pk == nil and p2.persistent == false, "empty loaded squad released")
local t3 = R.taken[2]; local p3
for i, p in ipairs(DRIFT.active) do if p.key == t3.pk then p3 = p; table.remove(DRIFT.active, i); break end end
p3.isDead = true; DRIFT.unloaded[1] = p3; R.hi = 1; tick()
check(t3.pk ~= nil and t3.gone and p3.persistent == true, "dead unloaded squad deferred until load")
DRIFT.unloaded = {}
-- смена мира
local S_old = S; S = { ext = {} }; tick()
check(has(readlog(), "world changed"), "world change resets runtime")
S = S_old
-- ошибка такта -> самоотключение
SNAP_ERR = true; R.next_h = nil; R.last_take_h = -1e9; tick(); SNAP_ERR = false
check(M.off == true and has(readlog(), "disabled until restart"), "error disables module")
-- фракция не подтвердилась (вызов прошёл) -> выключен до перезапуска, не навсегда; пустой отряд временный
M._reset(); S = { ext = {} }; FAIL_SETFACTION = true
local e = MKCH({ name = "Probe", h = "H12", skill = 70, x = 101, z = 101 })
tick()
HOURS = S.ext.recruitrace.race.t1 + 1; tick()
for i = 1, P.confirm_n do tick() end
check(has(readlog(), "setFaction FAIL Probe -> 51707-rebirth.mod: faction not confirmed") and M.off == true, "unconfirmed setFaction disables until restart")
check(LAST_PL.persistent == false and LAST_PL.permanent == false and e.fac ~= DRIFT, "failed probe leaves no persistent squad")
local f = io.open("TMP" .. "recruitrace.off", "r"); check(f == nil, "no permanent off flag for unconfirmed result"); if f then f:close() end
M._reset(); tick(); check(M.off == false, "module back after restart")
FAIL_SETFACTION = false
-- сохранённая незавершённая передача из сейва -> сбрасывается, не считается провалом
S = { ext = { recruitrace = { pend = { h = "OLDH", fid = "51707-rebirth.mod", name = "Ghost", tries = 0 } } } }; M._reset(); tick()
check(S.ext.recruitrace.pend == nil and M.off == false and has(readlog(), "pending transfer dropped"), "stale pending from save dropped")
-- вызов setFaction упал -> выключен навсегда
M._reset(); S = { ext = {} }; SF_THROW = true; e.dead = false
tick(); HOURS = S.ext.recruitrace.race.t1 + 1; tick()
check(has(readlog(), "setFaction FAIL Probe -> 51707-rebirth.mod: call failed") and M.off == true, "failed call disables")
check(LAST_PL.persistent == false, "failed call: platoon not persistent")
f = io.open("TMP" .. "recruitrace.off", "r"); check(f ~= nil, "off flag written for failed call"); if f then f:close() end
M._reset(); tick(); check(M.off == true, "off flag keeps module disabled")
os.remove("TMP" .. "recruitrace.off"); SF_THROW = false
-- крэш-сторож: lock прошлой сессии -> вызов выключен навсегда
M._reset(); S = { ext = {} }
local lf = io.open("TMP" .. "probe_rr_setfaction.lock", "w"); lf:write("1"); lf:close()
tick(); HOURS = S.ext.recruitrace.race.t1 + 1; tick()
check(M.off == true and has(readlog(), "native setfaction DISABLED forever"), "crash guard")
''', "test")
run(r'''
if #FAILS > 0 then error("FAIL " .. #FAILS .. "/" .. N .. ":\n  " .. table.concat(FAILS, "\n  ")) end
print("checks " .. N)
''', "result")
print("OK test_recruit_race")
