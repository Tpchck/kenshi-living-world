"""Offline test X4 (KMM_RelicRace RUINLOOT): конкуренты реально опустошают ящики руин у игрока.
Живой искатель Q1 (шаблон из rivals.json) -> лучшие стопки в инвентарь лидера; вскрытие экспедицией -> стопки вынесены и уходят чемпиону;
лимиты (окно руин, сессия, кулдаун), пропуск ящиков игрока/лавок/уникальных, проба FAIL и крэш-сторож выключают разбор.
python -I -X utf8 build/KMM_Conductor/_dev/test_x4_loot.py -> OK."""
import ctypes, re, sys, tempfile

DLL = r"C:\Program Files (x86)\Steam\steamapps\workshop\content\233860\3817000612\lua51.dll"
B = r"C:\KenshiModMap\build\KMM_Conductor\scripts\init"
TMP = tempfile.mkdtemp(prefix="kmm_x4_").replace("\\", "/")
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
run(open(B + r"\KMM_RelicRace.lua", encoding="utf-8").read(), "KMM_RelicRace.lua")
run(r'''
N, FAILS = 0, {}
function check(c, what) N = N + 1; if not c then FAILS[#FAILS + 1] = what end end
local C, RR = KMM_Conductor, KMM_RelicRace
C.reset()
local P = RR.P
P.start_s = 0; P.check_s = 0; P.loot_s = 0; P.sdir = "TMP/"; P.first_gap = { 999, 999 }
LOGF = "TMP/relic_x4.log"
local function readf(p) local f = io.open(p, "r"); if not f then return "" end; local s = f:read("*a"); f:close(); return s end
-- журнал модуля: перехват io.open только для пути лога RelicRace
local io_open0 = io.open
io.open = function(p, m) if p == "C:/KenshiModMap/logs/relicrace.log" then p = LOGF end; return io_open0(p, m) end
local D = C.read_json("relicrace.json", "C:/KenshiModMap/build/KMM_Conductor/relicrace.json")
local RV = C.read_json("rivals.json", "C:/KenshiModMap/build/KMM_Conductor/rivals.json")
check(D and D.sites and #D.sites > 0, "relicrace.json sites")
check(RV and RV.prospectors and next(RV.prospectors), "rivals.json prospectors (fix.py)")
local site = D.sites[1]
local pros = next(RV.prospectors)
local pf = C.cfg().player_faction or "player"
do local S_ = C.state(); S_.F["town_f"] = S_.F["town_f"] or { alive = true, towns = { town_x = true } } end   -- bld_owner: чужое = фракция с городами в модели
-- игрок у руин
PCS = { MKCH("PC1", pf, site.x + 300, site.z, { player = true, platoon = "player_squad" }) }
CHARS = { PCS[1] }
-- ящики: предмет с ценой; инвентарь с переносом, слиянием стопок и подсчётом штук по GameData
local function ITEM(sid, q, v, uniq, stolen)
  local it = { quantity = q, isUnique = uniq or false, isEquipped = false, sid = sid }
  function it:getGameData() return { stringID = sid, type = 9 } end
  function it:getValueAll() return v * self.quantity end
  function it:getClassType() return 9 end
  function it:isStolen() return stolen or false end
  return it
end
function INV(items, opt)
  opt = opt or {}
  local inv = { items = items, container = opt.container ~= false }
  function inv:getAllItems() local o = {}; for i, x in ipairs(self.items) do o[i] = x end; return o end
  function inv:isAContainer() return self.container end
  local function rm(self, it) for i, x in ipairs(self.items) do if x == it then table.remove(self.items, i); return true end end end
  function inv:removeItemDontDestroy_returnsItem(it, q) if rm(self, it) then return it end end
  function inv:removeItemAutoDestroy(it, q) DESTROYED = (DESTROYED or 0) + 1; return rm(self, it) and true or false end
  function inv:addItem(it, q)
    if opt.full then return false end
    if opt.ghost then return true end   -- «принял» и потерял
    if opt.merge then for _, x in ipairs(self.items) do if x.sid == it.sid then x.quantity = x.quantity + it.quantity; it.quantity = 0; return true end end end
    self.items[#self.items + 1] = it; return true
  end
  function inv:countItems(gd)
    if opt.nocount then error("no countItems") end
    local n = 0; for _, x in ipairs(self.items) do if x.sid == gd.stringID then n = n + x.quantity end end; return n
  end
  function inv:hasItem(x, n)
    if opt.nocount then error("no hasItem") end
    if opt.ghost then return false end
    for _, y in ipairs(self.items) do if y == x or (x.stringID and y.sid == x.stringID) then return true end end; return false
  end
  return inv
end
local HN = 0
local function BLD(inv, opt)
  opt = opt or {}
  HN = HN + 1
  local hs = opt.h or ("bld" .. HN)
  local b = { inv = inv }
  function b:isAShop() return opt.shop or false end
  function b:hasFaction() return opt.fid ~= nil end
  function b:getFaction() return FAC(opt.fid) end
  function b:getInventory() return self.inv end
  return { getHandle = function() return { getBuilding = function() return b end, toString = function() return hs end } end }
end
local function fill(base)
  BOX = INV({ ITEM("junk", 10, 1), ITEM("gold", 1, 500), ITEM("book", 2, 200), ITEM("ai_core", 1, 9000, true), ITEM("med", 5, 30), ITEM("bolt", 20, 4) })
  BOX2 = INV({ ITEM("plate", 1, 800), ITEM("rice", 8, 2), ITEM("tool", 3, 60), ITEM("rope", 4, 10), ITEM("gem", 1, 300), ITEM("salt", 6, 3) })
  OWNED = INV({ ITEM("town_sword", 1, 5000) })
  SHOP = INV({ ITEM("shop_armor", 1, 7000) })
  OBJS = { BLD(BOX, { h = "box1" }), BLD(BOX2, { h = "box2" }), BLD(OWNED, { fid = "town_f", h = "owned" }), BLD(SHOP, { shop = true, h = "shop" }),
           BLD(INV({ ITEM("bed", 1, 9999) }, { container = false }), { h = "bed" }) }
  if base then OBJS[#OBJS + 1] = BLD(INV({ ITEM("my_sword", 1, 5000) }), { fid = pf, h = "pbase" }) end
end
local function fresh(base) fill(base); local r = C.state().ext.relicrace; if r then r.fp = nil end; RR.rt.loot.fp = nil end
fill()
SPH = 0
lektor = { new = function() local t = {}; function t:clear() for i = #self, 1, -1 do self[i] = nil end end; return t end }
local gw0 = getGameWorld
getGameWorld = function()
  local w = gw0()
  w.getObjectsWithinSphere = function(_, buf, pos, r, ty, maxn)
    SPH = SPH + 1
    if ty ~= 0 or type(pos) ~= "table" or not pos.x then error("bad sphere args") end
    if math.sqrt((pos.x - site.x) ^ 2 + (pos.z - site.z) ^ 2) <= r then for i, o in ipairs(OBJS) do if i <= maxn then buf[#buf + 1] = o end end end
  end
  w.theFactory.createItem = function(_, gd) return { gd = gd } end
  return w
end
-- снимок Gov: записи отрядов у руин
LEADER_INV = INV({})
LEADER = { dead = false }
function LEADER:isDead() return self.dead end
function LEADER:getInventory() return LEADER_INV end
local PL = { getSquadLeader = function() return LEADER end }
SNAP = { list = {} }
KMM_Gov = { snapshot = function() return SNAP end }
local function looter(tsid, opt) opt = opt or {}; return { x = site.x + 100, z = site.z + 50, fid = opt.fid or "drifters", dead = false, down = opt.down or false, combat = opt.combat or false, tsid = tsid, pl = PL } end
local evs = {}
C.subscribe("relic_*", function(ev) evs[ev.type] = (evs[ev.type] or 0) + 1 end)
local function tick() CLOCK = CLOCK + 100; C.state().last_day = DAYV; FIRE("GameWorld::charsUpdate", {}) end   -- день дирижёра = DAYV (офлайн)
local function R() return C.state().ext.relicrace end
local function has(inv, sid) for _, x in ipairs(inv.items) do if x.sid == sid then return true end end return false end
local function nbox() return #BOX.items + #BOX2.items end

-- 0. никого у руин: ничего не уносится, но ящики получают отпечаток исходного лута
tick(); tick()
check(RR.off == false and not RR.rt.loot.off, "module + loot alive")
check(nbox() == 12, "no looters -> boxes intact")
check(R().fp and R().fp[site.sid] and R().fp[site.sid].box1 and R().fp[site.sid].box1.gold == 1, "fingerprint of original loot recorded")
check(R().fp[site.sid].owned == nil and R().fp[site.sid].shop == nil, "owned/shop containers not fingerprinted")
-- 0б. игрок кладёт в ящик руин своё (новый sid, краденое, добавка к стопке): это не исходный лут
BOX.items[#BOX.items + 1] = ITEM("player_katana", 1, 20000)
BOX.items[#BOX.items + 1] = ITEM("stolen_gem", 1, 15000, false, true)
for _, x in ipairs(BOX2.items) do if x.sid == "tool" then x.quantity = 9 end end   -- стопка больше отпечатка
-- 1. искатель в бою или без сознания - не грабит
SNAP.list = { looter(pros, { combat = true }), looter(pros, { down = true }), looter("not_a_rival_tsid") }
tick()
check(#LEADER_INV.items == 0, "combat/down/non-rival squads do not loot")
-- 2. живой искатель Q1: 3 лучшие стопки исходного лута -> лидеру (перенос)
SNAP.list = { looter(pros) }
tick()
check(#LEADER_INV.items == 3, "live prospector moved live_take stacks: " .. #LEADER_INV.items)
check(has(LEADER_INV, "plate") and has(LEADER_INV, "gold") and has(LEADER_INV, "book"), "most valuable original stacks taken first")
check(has(BOX, "player_katana") and has(BOX, "stolen_gem"), "player-placed and stolen items untouched")
check(has(BOX, "ai_core"), "unique item untouched")
check(#OWNED.items == 1 and #SHOP.items == 1, "faction-owned container and shop untouched")
check((evs.relic_ruins_looting or 0) == 1, "rumor relic_ruins_looting emitted")
check(readf(LOGF):find("ruinloot probe ok: take", 1, true) ~= nil, "probe ok marker (take)")
check(readf(LOGF):find("ruinloot site ", 1, true) ~= nil, "site containers marker")
check(R().fp[site.sid].box1.gold == nil, "moved stack leaves the fingerprint")
-- 3. кулдаун живого разбора (тот же день) и окно руин
tick(); tick()
check(#LEADER_INV.items == 3, "live_cd: no second take the same day")
P.site_cap = 7
for d = 1, 8 do DAYV = DAYV + 1; tick() end
local u = R().ruin[site.sid]
check(u and u.n == #LEADER_INV.items and #LEADER_INV.items == 7, "more takes on later days, capped by site_cap: " .. tostring(u and u.n))
check(not has(LEADER_INV, "tool") and not has(LEADER_INV, "player_katana"), "grown stack / player item never taken")
P.site_cap = 12
check((evs.relic_ruins_looting or 0) == 1, "rumor once per window")
check((DESTROYED or 0) == 0, "nothing destroyed")
-- 4. вскрытие экспедицией без получателя: ничего не трогается
fresh(); SNAP.list = {}
DAYV = DAYV + P.ruin_win + 1
local day = C.day()
local fid
for f, ff in pairs(C.state().F) do if ff.alive and not ff.player and f ~= pf then fid = fid or f end end
local uu = RR.ruin(R(), site.sid, day); uu.dug, uu.dfid = day, fid
tick(); tick()
check(nbox() == 12 and not uu.done and (DESTROYED or 0) == 0, "dig without champion/expedition squad -> boxes untouched")
-- 4б. чемпион фракции загружен: лучшие стопки переносятся ему, без уничтожения
local CHI = INV({}); local CHL = { isDead = function() return false end, getInventory = function() return CHI end }
RR.rt.champ[fid] = { leader = CHL }
local O0 = OBJS; OBJS = {}; tick()
check(not uu.done and nbox() == 12, "dig waits until ruin boxes are loaded"); OBJS = O0
tick()
check(nbox() == 12 - P.dig_take and #CHI.items == P.dig_take, "dig moved dig_take stacks to champion: left " .. nbox() .. ", champ " .. #CHI.items)
check(uu.done and uu.stash == nil and (DESTROYED or 0) == 0, "dig: no stash, nothing destroyed")
check((evs.relic_ruins_emptied or 0) == 1, "rumor relic_ruins_emptied")
tick()
check(nbox() == 12 - P.dig_take, "dig applied once")
RR.rt.champ[fid] = nil
-- 4в. рядом база игрока: руины не трогаются ни вскрытием, ни живыми искателями
fresh(true); DAYV = DAYV + P.ruin_win + 1; R().ruin[site.sid] = nil
uu = RR.ruin(R(), site.sid, C.day()); uu.dug, uu.dfid = C.day(), fid
RR.rt.champ[fid] = { leader = CHL }; LEADER_INV = INV({}); SNAP.list = { looter(pros) }
tick(); DAYV = DAYV + 1; tick()
check(nbox() == 12 and #LEADER_INV.items == 0 and #CHI.items == P.dig_take, "player base nearby -> nothing taken")
RR.rt.champ[fid] = nil
-- старое сохранение: stash прежней версии -> чемпиону при победе, выдача лидеру при выходе
local rel = D.relics[1]
local rnd0 = math.random
math.random = function() return 0 end
uu.stash = { { s = "gold", t = 9, q = 1 }, { s = "book", t = 9, q = 2 } }
RR.finish(C, R(), C.state(), day, { id = 1, fid = fid, site = site.sid, sname = site.name, relic = rel.sid, p = 1 })
math.random = rnd0
local ch = R().champ[fid]
check(ch and ch.loot and #ch.loot == 2 and uu.stash == nil, "legacy stash -> champion loot on win")
local CL = INV({}); local cl = { getInventory = function() return CL end }
local made = RR.give_loot(cl, ch.loot)
check(made == 3 and CL.items[1].gd.stringID ~= nil, "champion leader gets legacy loot: " .. made)
R().champ[fid] = nil
-- 5. M7: стопка слилась с имеющейся у лидера - перенос подтверждён по числу штук, разбор жив
fresh(); RR.rt.loot.probe["take#ok"] = nil
LEADER_INV = INV({ ITEM("med", 2, 30), ITEM("gold", 3, 500) }, { merge = true })
SNAP.list = { looter(pros) }
DAYV = DAYV + P.ruin_win + 1; R().ruin[site.sid] = nil
tick()
check(not RR.rt.loot.off and readf(LOGF):find("ruinloot probe ok: take", 1, true) ~= nil, "merged stack -> verified by count, loot on")
local gq = 0; for _, x in ipairs(LEADER_INV.items) do if x.sid == "gold" then gq = gq + x.quantity end end
check(gq == 4 and not has(BOX, "gold"), "merged gold counted at recipient: " .. gq)
-- 5б. проверка не читается (нет countItems/hasItem): перенос засчитан, разбор не выключается
fresh(); LEADER_INV = INV({}, { nocount = true })
DAYV = DAYV + P.ruin_win + 1; R().ruin[site.sid] = nil
tick()
check(not RR.rt.loot.off and #LEADER_INV.items == 3 and readf(LOGF):find("unverified (count check), kept on", 1, true) ~= nil, "check failure keeps loot on")
-- 5в. предмета нет у лидера после addItem - проба FAIL выключает разбор до перезапуска
fresh(); RR.rt.loot.probe["take#ok"] = nil
LEADER_INV = INV({}, { ghost = true })
DAYV = DAYV + P.ruin_win + 1; R().ruin[site.sid] = nil
tick()
check(RR.rt.loot.off == true and readf(LOGF):find("ruinloot probe FAIL: take", 1, true) ~= nil, "probe FAIL -> loot off")
local nb = nbox()
DAYV = DAYV + 1; tick()
check(nbox() == nb, "after FAIL nothing more is taken")
check(RR.off == false, "FAIL disables only loot, not the module")
-- 6. крэш-сторож: lock прошлой сессии -> .off навсегда, ничего не трогаем
RR.rt.loot = { n = 0, probe = {} }
local f = io_open0("TMP/probe_rl_take.lock", "w"); f:write("1"); f:close()
fresh(); LEADER_INV = INV({}); DAYV = DAYV + P.ruin_win + 1; R().ruin[site.sid] = nil
tick()
check(#LEADER_INV.items == 0 and #BOX.items == 6, "crash guard blocks take")
check(io_open0("TMP/probe_rl_take.off", "r") ~= nil, "crash guard wrote .off")
os.remove("TMP/probe_rl_take.off")
-- 7. лимит сессии и дальний игрок
RR.rt.loot = { n = P.session_max, probe = {} }
fresh(); DAYV = DAYV + P.ruin_win + 1; R().ruin[site.sid] = nil
tick()
check(#LEADER_INV.items == 0, "session_max respected")
RR.rt.loot = { n = 0, probe = {} }
PCS[1] = MKCH("PC1", pf, site.x + P.ruin_near * 3, site.z + P.ruin_near * 3, { player = true, platoon = "player_squad" })
local sph0 = SPH
DAYV = DAYV + 1; tick()
check(SPH == sph0 and #LEADER_INV.items == 0, "far player -> no scan")
-- 8. смена мира сбрасывает указатели чемпионов
RR.rt.champ.x = { leader = {} }
C.reset(); tick()
check(next(RR.rt.champ) == nil, "world change clears leader refs")
check((DESTROYED or 0) == 0, "removeItemAutoDestroy never called")
-- 9. состояние мелкое и сериализуемо; протухшие записи чистятся
local Rr = R()
check(Rr and Rr.ruin, "ruin table in state")
local okser = pcall(C.serialize)
check(okser, "conductor state serialisable")
RESULT = #FAILS == 0 and ("OK " .. N .. " moved=" .. tostring(RR.stats.ruin_moved) .. " dug=" .. tostring(RR.stats.ruin_dug)) or ("FAIL: " .. table.concat(FAILS, "; "))
'''.replace("TMP", TMP), "test")
L.lua_getfield.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_char_p]
L.lua_getfield(st, -10002, b"RESULT")
r = L.lua_tolstring(st, -1, None).decode()
print(r)
sys.exit(0 if r.startswith("OK") else 1)
