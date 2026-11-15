"""Offline test B2 (KMM_Traces, 2026-11-15): общие правила по состоянию игрока, без привязки к типу старта.
(1) PACE: враждебная пауза по умолчанию 600 с; свой игрока лежит (isDown/isUnconcious) -> враждебные ждут hostile_after_ko_seconds
    после того, как его последний раз видели лежащим; мирные идут.
(2) Ворота силы и богатства: задание poor_gate ждёт, пока KMM_Nemesis.poor() = true; отряд разбогател -> идёт; срок вышел -> отменено.
(3) Первый час: порядок «караван -> беженцы -> колонна -> отряд», отряд фракции за воротами богатства.
(4) Подписи отрядов по сути (ActivePlatoon:setName), грязные имена мест не попадают; вестник говорит одну строку, когда игрок рядом;
    нет проверки живого набора -> вестники выключены, подписи остаются.
python -I -X utf8 build/KMM_Conductor/_dev/test_b2_traces.py -> OK."""
import ctypes, re, sys, tempfile

DLL = r"C:\Program Files (x86)\Steam\steamapps\workshop\content\233860\3817000612\lua51.dll"
B = r"C:\KenshiModMap\build\KMM_Conductor\scripts\init"
TMP = tempfile.mkdtemp(prefix="kmm_b2t_").replace("\\", "/")
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
run("math.randomseed(20261115)", "seed")
for _f in sorted(__import__("glob").glob(B + r"\KMM_Conductor*.lua")): run(open(_f, encoding="utf-8").read(), _f.split("\\")[-1])
run(open(B + r"\KMM_Traces.lua", encoding="utf-8").read(), "KMM_Traces.lua")
run(r'''
N, FAILS = 0, {}
function check(c, what) N = N + 1; if not c then FAILS[#FAILS + 1] = what end end
local C = KMM_Conductor
C.reset()
local S = C.state()
local TP = C.cfg().params.traces
TP.first_hour_traces = 4; TP.first_hour_gap_seconds = 420; TP.max_per_day = 1000; TP.max_queue = 30; TP.arrive_enabled = false
TP.bounty = { enabled = false }; TP.hostile_gap_seconds = nil; TP.hostile_after_ko_seconds = nil; TP.first_hour_drift = 1e9
POOR = true
KMM_Nemesis = { poor = function() return POOR end }
-- спавн: платун с подписью и вожаком
NAMED, LEADERS = {}, {}
HAS = true
local gw0 = getGameWorld
getGameWorld = function()
  local w = gw0()
  local base = w.theFactory.createRandomSquad
  w.theFactory.createRandomSquad = function(self, f, pos, ...)
    base(self, f, pos, ...)
    local leader = MKCH("Lead" .. #SPAWNS, f.id, pos.x, pos.z, {})
    leader.said = {}; function leader:say(s) self.said[#self.said + 1] = s end
    LEADERS[#LEADERS + 1] = leader; CHARS[#CHARS + 1] = leader
    local pl = { k = #SPAWNS }
    function pl:getActivePlatoon() return { setName = function(_, n) NAMED[#NAMED + 1] = n; pl.name = n end } end
    function pl:getSquadLeader() return leader end
    function pl:getOwnerships() return { setHomeTown = function() end } end
    function pl:getPlatoonStringID() return "tp" .. pl.k end
    function pl:getBlackboard() return { replaceAIPackage = function() end } end
    return pl
  end
  local ul = w.getCharacterUpdateList
  w.getCharacterUpdateList = function(selfw)
    local set = ul(selfw)
    if HAS then setmetatable(set, { __index = { has = function(_, c) return rawget(set, c) == true end } }) end
    return set
  end
  return w
end
local tr = C.read_json("traces.json", "C:/KenshiModMap/build/KMM_Conductor/traces.json")
local fk = {}; for fid in pairs(tr.factions) do fk[#fk + 1] = fid end; table.sort(fk)
local best, bn
for _, fid in ipairs(fk) do   -- точка, у которой в радиусе больше всего фракций со следами (есть из чего строить первый час)
  local x, z = C.fpos(fid)
  if x and S.F[fid] and S.F[fid].alive then
    local n = 0
    for _, g in ipairs(fk) do local gx, gz = C.fpos(g); if gx and S.F[g] and S.F[g].alive and (gx - x) ^ 2 + (gz - z) ^ 2 < 70000 ^ 2 then n = n + 1 end end
    if not bn or n > bn then best, bn = fid, n end
  end
end
local PX, PZ = C.fpos(best)
local pf = C.cfg().player_faction or "player"
local pc = MKCH("Nameless", pf, PX, PZ, { player = true, platoon = "player_squad" })
pc.down = false; function pc:isDown() return self.down end
PCS = { pc }; CHARS = { pc }
S.last_day = 1; DAYV = 1
local T, PACE = KMM_Traces, KMM_Traces._pace
local function pump(n, dt) for i = 1, n do CLOCK = CLOCK + (dt or 5); FIRE("GameWorld::charsUpdate", {}) end end
pump(1)
-- (3) первый час: порядок и ворота
local Q = T.queue()
local kinds, band = {}, nil
local tq = {}; for _, j in ipairs(Q) do if j.why and j.why:find("first hour", 1, true) then tq[#tq + 1] = j end end
table.sort(tq, function(a, b) return a.at < b.at end)
for _, j in ipairs(tq) do kinds[#kinds + 1] = j.kind; if j.kind == "band" then band = j end end
local ks = table.concat(kinds, ",")
check(#tq >= 2, "first hour scheduled: " .. ks)
local pos = {}; for i, k in ipairs(kinds) do pos[k] = pos[k] or i end
check((not pos.caravan or pos.caravan == 1) and (not pos.column or not pos.refugees or pos.refugees < pos.column), "order caravan -> refugees -> column: " .. ks)
check(band and pos.band == #kinds and band.poor_gate == true and band.pg_until ~= nil, "faction band last and behind the wealth gate: " .. ks)
-- прогнать первый час: нищему отряд не приходит, остальное приходит
pump(2 * 60 * 4, 5)
local left = {}; for _, j in ipairs(Q) do left[#left + 1] = j.kind end
check(band and #left >= 1 and left[#left] == "band" and (T.pace().waited_poor or 0) > 0, "poor weak squad: band waits, others came: left=" .. table.concat(left, ","))
local nb0 = T.stats().by_kind.band or 0
POOR = false
pump(40, 5)
check((T.stats().by_kind.band or 0) == nb0 + 1, "squad got rich: band comes")
check(NAMED[#NAMED] and NAMED[#NAMED]:find(" band", 1, true), "band squad labelled: " .. tostring(NAMED[#NAMED]))
-- срок ворот вышел, а отряд всё так же нищ -> отменено
POOR = true
T._enqueue({ kind = "band", fid = best, n = 1, why = "gate test", poor_gate = true, pg_until = CLOCK + 10 })
pump(20, 5)
local still = false; for _, j in ipairs(Q) do if j.why == "gate test" then still = true end end
check(not still and (T.stats().skipped_poor or 0) == 1, "gate expired while poor: trace dropped")
-- (1) пауза: по умолчанию 600 с, KO
PACE.last_host = CLOCK
check(PACE.blocked({ tag = "outlaw" }, CLOCK + 500) == true and PACE.blocked({ tag = "outlaw" }, CLOCK + 601) == false, "default hostile gap 600 s")
PACE.last_host = -1e9
pc.down = true
PACE.ko_step(CLOCK)
check(PACE.blocked({ tag = "predator_ambush" }, CLOCK + 10) == true and PACE.blocked({ tag = "herd" }, CLOCK + 10) == false, "player down: hostile waits, ambient passes")
pc.down = false
check(PACE.ko_step(CLOCK + 100) == false and PACE.blocked({ tag = "nemesis" }, CLOCK + 250) == true, "got up: still a breather after the knockout")
check(PACE.blocked({ tag = "nemesis" }, CLOCK + 301) == false, "after hostile_after_ko_seconds: allowed")
check(PACE.blocked({ tag = "base_raid" }, CLOCK + 10) == false, "critical never waits")
-- (4) подписи и вестник
check(PACE.clean("Stack") == "Stack" and PACE.clean("失控的武士实验室") == nil and PACE.clean("Large Bone Fiend Hollow (defunct and broken) 103") == nil, "dirty place names rejected")
local pl = getGameWorld().theFactory:createRandomSquad(FAC(best), { x = PX + 2000, y = 0, z = PZ }, nil, 4, nil, { stringID = "tsq" }, nil, nil, nil, false, {}, nil, 1.0, 2, false)
PACE.HER = {}
PACE.label(pl, "refugees", best, { town = "Stack", ev = 77 })
check(pl.name == "Refugees from Stack" and #PACE.HER == 1, "refugees labelled with town, herald queued: " .. tostring(pl.name))
local ld = pl:getSquadLeader()
PACE.herald_step(PX, PZ, CLOCK)
check(#ld.said == 0 and #PACE.HER == 1, "far: herald waits")
ld.getPosition = function() return { x = PX + 300, y = 0, z = PZ } end
PACE.herald_step(PX, PZ, CLOCK + 1)
check(#ld.said == 1 and #PACE.HER == 0, "near: herald says one line: " .. tostring(ld.said[1]))
PACE.herald_step(PX, PZ, CLOCK + 2)
check(#ld.said == 1, "only once")
local pl2 = getGameWorld().theFactory:createRandomSquad(FAC(best), { x = PX + 2000, y = 0, z = PZ }, nil, 4, nil, { stringID = "tsq" }, nil, nil, nil, false, {}, nil, 1.0, 2, false)
PACE.label(pl2, "refugees", best, { town = nil })
check(pl2.name:find(" refugees", 1, true) and PACE.HER[1] and not PACE.HER[1].line:find("%s", 1, true), "no town: faction refugees, line without a place")
PACE.HER[1].t1 = CLOCK - 1; PACE.herald_step(PX, PZ, CLOCK)
check(#PACE.HER == 0, "herald expires")
local pl3 = getGameWorld().theFactory:createRandomSquad(FAC(best), { x = PX + 2000, y = 0, z = PZ }, nil, 4, nil, { stringID = "tsq" }, nil, nil, nil, false, {}, nil, 1.0, 2, false)
PACE.label(pl3, "column", best, { enemy = best })
HAS = false
PACE.herald_step(PX, PZ, CLOCK)
check(PACE.her_off == true and #PACE.HER == 0, "no liveness check: heralds off")
local pl4 = getGameWorld().theFactory:createRandomSquad(FAC(best), { x = PX + 2000, y = 0, z = PZ }, nil, 4, nil, { stringID = "tsq" }, nil, nil, nil, false, {}, nil, 1.0, 2, false)
PACE.label(pl4, "courier", best)
check(pl4.name and pl4.name:find(" courier", 1, true) and #PACE.HER == 0, "names stay when heralds are off")
local bad = { getActivePlatoon = function() error("no platoon") end }
PACE.label(bad, "band", best)
check((T.stats().name_fail or 0) >= 1, "setName failure counted, no error")
-- нет шаблона отряда (gamedata:getData -> nil): охота и отряд не считаются пришедшими, вести «bounty_hunters» нет
POOR = false; PACE.last_host = -1e9; pc.down = false; PACE.ko_t = nil
NOTPL = true
local gw1 = getGameWorld
getGameWorld = function() local w = gw1(); if NOTPL then w.gamedata = { getData = function() return nil end } end; return w end
local nt0, bn0 = T.stats().no_template or 0, T.bounty().n
local ev0 = #S.events
local hb0 = T.stats().by_kind.bounty_hunt or 0
T._enqueue({ kind = "bounty_hunt", fid = best, amount = 5000, why = "tpl test" })
T._enqueue({ kind = "band", fid = best, n = 1, why = "tpl test" })
pump(60, 5)
local bh = false; for i = ev0 + 1, #S.events do if S.events[i].type == "bounty_hunters" then bh = true end end
check((T.stats().no_template or 0) > nt0, "no template counted: " .. tostring(T.stats().no_template))
check(not bh and T.bounty().n == bn0 and (T.stats().by_kind.bounty_hunt or 0) == hb0, "no template: no hunters event, no hunt counted")
NOTPL = false; getGameWorld = gw1
check(next(T.disabled()) == nil, "nothing disabled: " .. (next(T.disabled()) or ""))
RESULT = #FAILS == 0 and ("OK " .. N) or ("FAIL: " .. table.concat(FAILS, "; "))
'''.replace("TMPDIR", TMP), "test")
L.lua_getfield.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_char_p]
L.lua_getfield(st, -10002, b"RESULT")
r = L.lua_tolstring(st, -1, None).decode()
print(r)
sys.exit(0 if r.startswith("OK") else 1)
